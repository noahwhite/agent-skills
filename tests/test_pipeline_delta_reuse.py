"""SKL-411: the pre-PR gate re-gates on a delta base and reuses an identical tree.

AC1 delta base (--base at the last accepted head, or --delta resolving it from the run store),
AC2 tree identity and reuse of an accepted sweep/hunt, AC3 the reuse reporting and the exit-13
rules, AC4 the stand-in-agent tests (including the hostile git config), and AC7 deterministic
dossier input.

Every test drives the real script with fake agents in a throwaway repository, following
tests/test_pipeline_failfast.py.
"""

import hashlib
import os
import re
import shlex
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "adversarial-review-pipeline" / "scripts" / "run-adversarial-pipeline.sh"
GOLDEN = ROOT / "tests" / "fixtures" / "delta_reuse" / "sweep-dossier.normalized.golden"

SPEC_TEXT = (
    "SKL-411 test spec - not real data\n\n"
    "A re-gate reviews only the delta since the last accepted head.\n"
)


# --- Throwaway repository and environment ---------------------------------------------------------

def _git(repo: Path, env: dict[str, str], *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


def fixed_env(tmp_path: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    """A deterministic environment: no user or system git config, fixed identity and dates."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("ADVERSARIAL_", "GIT_"))}
    runtime_tmp = tmp_path / "runtime-tmp"
    runtime_tmp.mkdir(parents=True, exist_ok=True)
    env.update({
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Fixture Author",
        "GIT_AUTHOR_EMAIL": "fixture@example.com",
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+0000",
        "GIT_COMMITTER_NAME": "Fixture Author",
        "GIT_COMMITTER_EMAIL": "fixture@example.com",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+0000",
        "COLUMNS": "80",
        "LC_ALL": "C",
        "TZ": "UTC",
        "TMPDIR": str(runtime_tmp),
    })
    env.update(extra or {})
    return env


def make_repo(tmp_path: Path, env: dict[str, str], name: str = "repo") -> tuple[Path, str]:
    """A repository with a `base` commit holding `tracked.txt` = one and a head commit holding two."""
    repo = tmp_path / name
    repo.mkdir()
    _git(repo, env, "init", "-q", "--initial-branch=main")
    _git(repo, env, "config", "core.autocrlf", "false")
    _git(repo, env, "config", "commit.gpgsign", "false")
    (repo / "tracked.txt").write_text("one\n")
    _git(repo, env, "add", "-A")
    _git(repo, env, "commit", "-q", "-m", "base")
    _git(repo, env, "tag", "base")
    (repo / "tracked.txt").write_text("two\n")
    _git(repo, env, "add", "-A")
    _git(repo, env, "commit", "-q", "-m", "head")
    return repo, _git(repo, env, "rev-parse", "base^{commit}")


def commit_change(repo: Path, env: dict[str, str], body: str, path: str = "tracked.txt") -> str:
    (repo / path).write_text(body)
    _git(repo, env, "add", "-A")
    _git(repo, env, "commit", "-q", "-m", "change")
    return _git(repo, env, "rev-parse", "HEAD")


def commit_empty(repo: Path, env: dict[str, str]) -> str:
    """A new head with the same tree: a reuse source at the identical tree."""
    _git(repo, env, "commit", "-q", "--allow-empty", "-m", "same tree")
    return _git(repo, env, "rev-parse", "HEAD")


def run_script(*args: str, env: dict[str, str], timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True,
                          env=env, cwd=str(ROOT), timeout=timeout)


def report_agent(marker: Path, text: str = "REVIEW-RAN: yes\nreport\n") -> str:
    """Writes the report and records that it ran, so a reuse that skipped it is observable."""
    return (f'touch {shlex.quote(str(marker))}; '
            f'printf %s {shlex.quote(text)} > {{output_file}}')


def capturing_agent(marker: Path, copy: Path, text: str = "REVIEW-RAN: yes\nreport\n") -> str:
    return (f'touch {shlex.quote(str(marker))}; cat > {shlex.quote(str(copy))}; '
            f'printf %s {shlex.quote(text)} > {{output_file}}')


class Gate:
    def __init__(self, repo: Path, scratch: Path, env: dict[str, str], spec: Path):
        self.repo = repo
        self.scratch = scratch
        self.env = env
        self.spec = spec

    def _base_args(self, base: str | None, delta: bool) -> list[str]:
        return ["--delta"] if delta else ["--base", base]

    def preflight(self, base: str | None = "base", delta: bool = False,
                  story_base: str | None = None) -> subprocess.CompletedProcess:
        args = ["preflight", "--full-suite", "off", "--repo", str(self.repo), "--spec", str(self.spec),
                "--scratch", str(self.scratch), *self._base_args(base, delta)]
        if story_base:
            args += ["--story-base", story_base]
        return run_script(*args, env=self.env)

    def run_phase(self, phase: str, agent: str, base: str | None = "base", delta: bool = False,
                  extra: tuple[str, ...] = (), story_base: str | None = None) -> subprocess.CompletedProcess:
        args = ["run", phase, "--repo", str(self.repo), "--scratch", str(self.scratch),
                "--agent-cmd", agent, "--model", "test/model", "--spec", str(self.spec)]
        if phase == "arbitrate":
            args += ["--agent", "Test Arbiter"]
        if story_base:
            args += ["--story-base", story_base]
        args += list(extra)
        args += self._base_args(base, delta)
        return run_script(*args, env=self.env)

    def paths(self, base: str | None = "base", delta: bool = False) -> subprocess.CompletedProcess:
        return run_script("paths", "--repo", str(self.repo), "--spec", str(self.spec),
                          *self._base_args(base, delta), env=self.env)

    def run_dir(self, base: str | None = "base", delta: bool = False) -> Path:
        listed = self.paths(base, delta)
        assert listed.returncode == 0, listed.stdout + listed.stderr
        return Path(next(line.split(" ", 1)[1] for line in listed.stdout.splitlines()
                         if line.startswith("run ")))

    def artifacts(self, base: str | None = "base", delta: bool = False) -> dict[str, Path]:
        listed = self.paths(base, delta)
        assert listed.returncode == 0, listed.stdout + listed.stderr
        out = {}
        for line in listed.stdout.splitlines():
            name, _, path = line.partition(" ")
            if path:
                out[name] = Path(path)
        return out

    def accept_full_run(self, base: str = "base", delta: bool = False) -> Path:
        result = self.preflight(base, delta)
        assert result.returncode == 0, result.stdout + result.stderr
        for phase in ("sweep", "hunt"):
            result = self.run_phase(phase, report_agent(self.scratch / f"producing-{phase}.launched"),
                                    base, delta)
            assert result.returncode == 0, result.stdout + result.stderr
        result = self.run_phase("arbitrate", report_agent(self.scratch / "producing-arbitrate.launched"),
                                base, delta)
        assert result.returncode == 0, result.stdout + result.stderr
        return self.run_dir(base, delta)


@pytest.fixture
def gate(tmp_path):
    env = fixed_env(tmp_path)
    repo, _ = make_repo(tmp_path, env)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    return Gate(repo, scratch, env, tmp_path / "spec.txt")


def write_spec(gate: Gate, text: str = SPEC_TEXT) -> None:
    gate.spec.write_text(text)


def tree_identity(gate: Gate, base_ref: str, head_ref: str) -> str:
    env = gate.env
    merge_base = _git(gate.repo, env, "merge-base", base_ref, head_ref)
    merge_tree = _git(gate.repo, env, "rev-parse", f"{merge_base}^{{tree}}")
    head_tree = _git(gate.repo, env, "rev-parse", f"{head_ref}^{{tree}}")
    spec_sha = hashlib.sha256(gate.spec.read_bytes()).hexdigest()
    return f"{merge_tree}-{head_tree}-{spec_sha}"


def one_reuse_line(stderr: str) -> str:
    lines = [line for line in stderr.splitlines() if line.startswith("reuse: ")]
    assert len(lines) == 1, f"expected exactly one reuse line, got {lines}\n{stderr}"
    return lines[0]


def reuse_line(stderr: str) -> str:
    return one_reuse_line(stderr)


# --- AC1: delta base ------------------------------------------------------------------------------

def test_delta_exits_12_with_the_exact_message_and_creates_no_run(gate):
    write_spec(gate)
    result = gate.paths(delta=True)
    assert result.returncode == 12, result.stdout + result.stderr
    assert ("--delta found no accepted run whose head is an ancestor of HEAD and whose spec "
            "matches; pass --base <head> instead") in result.stderr, result.stderr
    out_base = Path(_git(gate.repo, gate.env, "rev-parse", "--path-format=absolute",
                         "--git-path", "adversarial-pipeline"))
    runs = out_base / "runs"
    assert not runs.exists() or not any(runs.iterdir()), list(runs.iterdir()) if runs.exists() else []


def test_delta_resolves_the_maximally_descendant_accepted_head(gate):
    write_spec(gate)
    first = gate.accept_full_run("base")
    head_b = _git(gate.repo, gate.env, "rev-parse", "HEAD")
    # A second accepted run based at the first accepted head, then a new head.
    head_d = commit_change(gate.repo, gate.env, "three\n")
    second = Gate(gate.repo, gate.scratch, gate.env, gate.spec)
    second_run = second.accept_full_run(head_b)
    commit_change(gate.repo, gate.env, "four\n")
    listed = gate.paths(delta=True)
    assert listed.returncode == 0, listed.stdout + listed.stderr
    base_sha, head_sha = head_d, _git(gate.repo, gate.env, "rev-parse", "HEAD")
    run = next(line.split(" ", 1)[1] for line in listed.stdout.splitlines() if line.startswith("run "))
    assert Path(run).name == f"{base_sha}-{head_sha}", run
    assert Path(first).name != Path(second_run).name


def test_delta_ignores_an_accepted_run_for_a_different_spec(gate):
    write_spec(gate, "spec one\n")
    gate.accept_full_run("base")
    write_spec(gate, "spec two\n")
    commit_change(gate.repo, gate.env, "three\n")
    result = gate.paths(delta=True)
    assert result.returncode == 12, result.stdout + result.stderr


def test_a_delta_dossier_names_both_bases_and_reviews_only_the_delta_range(gate):
    write_spec(gate)
    first = gate.accept_full_run("base")
    base_a = _git(gate.repo, gate.env, "rev-parse", "base^{commit}")
    head_b = _git(gate.repo, gate.env, "rev-parse", "HEAD")
    head_c = commit_change(gate.repo, gate.env, "three\n")
    # preflight at the new head resolves the delta base from the store.
    result = gate.preflight(delta=True)
    assert result.returncode == 0, result.stdout + result.stderr
    copy = gate.scratch / "sweep-dossier-copy.md"
    result = gate.run_phase("sweep", capturing_agent(gate.scratch / "sweep.launched", copy),
                            delta=True)
    assert result.returncode == 0, result.stdout + result.stderr
    dossier = copy.read_text()
    assert f"BASE: {head_b} {head_b}" in dossier, dossier
    assert f"STORY-BASE: base {base_a}" in dossier, dossier
    assert f"DELTA-BASE: {head_b} {head_b}" in dossier, dossier
    assert f"REVIEWED RANGE: {head_b}...{head_c}" in dossier, dossier
    diff = dossier.split("===== DIFF (", 1)[1]
    assert "-two" in diff and "+three" in diff and "-one" not in diff, diff
    # The first gate's run is the source of the story base, not a delta run itself.
    first_dossier = (first / "phase1-sweep.md").read_text()
    assert "STORY-BASE:" not in first_dossier, first_dossier


def test_a_base_at_an_accepted_head_inherits_the_story_base(gate):
    write_spec(gate)
    gate.accept_full_run("base")
    base_a = _git(gate.repo, gate.env, "rev-parse", "base^{commit}")
    head_b = _git(gate.repo, gate.env, "rev-parse", "HEAD")
    head_c = commit_change(gate.repo, gate.env, "three\n")
    result = gate.preflight(base=head_b)
    assert result.returncode == 0, result.stdout + result.stderr
    copy = gate.scratch / "sweep-dossier-copy.md"
    result = gate.run_phase("sweep", capturing_agent(gate.scratch / "sweep.launched", copy),
                            base=head_b)
    assert result.returncode == 0, result.stdout + result.stderr
    dossier = copy.read_text()
    assert f"STORY-BASE: base {base_a}" in dossier, dossier
    assert f"DELTA-BASE: {head_b} {head_b}" in dossier, dossier
    assert f"REVIEWED RANGE: {head_b}...{head_c}" in dossier, dossier


# --- AC2 / AC3: identity, reuse, reporting, and the exit-13 rules ---------------------------------

def test_an_identical_tree_reuses_sweep_without_launching(gate):
    write_spec(gate)
    producing = gate.accept_full_run("base")
    producing_name = producing.name
    commit_empty(gate.repo, gate.env)
    identity = tree_identity(gate, "base", "HEAD")
    result = gate.preflight()
    assert result.returncode == 0, result.stdout + result.stderr
    marker = gate.scratch / "reuse-sweep.launched"
    result = gate.run_phase("sweep", report_agent(marker))
    assert result.returncode == 0, result.stdout + result.stderr
    assert not marker.exists(), "the sweep agent was launched for an identical tree"
    line = reuse_line(result.stderr)
    assert line == f"reuse: hit {identity} from run {producing_name}", line
    artifacts = gate.artifacts()
    assert artifacts["sweep"].read_bytes() == (producing / "phase1-sweep.md").read_bytes()
    stamp = Path(f"{artifacts['sweep']}.stamp").read_text()
    assert f"reused={identity}\n" in stamp, stamp
    assert f"reused_run={producing_name}\n" in stamp, stamp
    listed = gate.paths().stdout
    assert f"reused sweep {identity} {producing_name}\n" in listed, listed
    assert re.search(r"^reuse_hits 1$", listed, re.M), listed


def test_a_one_byte_difference_does_not_reuse(gate):
    write_spec(gate)
    gate.accept_full_run("base")
    commit_change(gate.repo, gate.env, "twO\n")
    result = gate.preflight()
    assert result.returncode == 0, result.stdout + result.stderr
    marker = gate.scratch / "reuse-sweep.launched"
    result = gate.run_phase("sweep", report_agent(marker))
    assert result.returncode == 0, result.stdout + result.stderr
    assert marker.exists(), "the sweep agent was not launched for a changed tree"
    assert reuse_line(result.stderr).startswith("reuse: miss reason="), result.stderr
    assert Path(f"{gate.artifacts()['sweep']}.stamp").read_text().find("reused=") == -1


def test_reuse_refuses_at_exit_13_when_the_producing_run_no_longer_accepts(gate):
    write_spec(gate)
    producing = gate.accept_full_run("base")
    (producing / "phase0-preflight.md.stamp").unlink()
    commit_empty(gate.repo, gate.env)
    result = gate.preflight()
    assert result.returncode == 0, result.stdout + result.stderr
    result = gate.run_phase("sweep", report_agent(gate.scratch / "reuse-sweep.launched"))
    assert result.returncode == 13, result.stdout + result.stderr
    assert "reuse: miss reason=acceptance lapsed" in result.stderr, result.stderr
    assert "sweep" in result.stderr and producing.name in result.stderr, result.stderr


def test_reuse_covers_hunt_but_not_preflight_or_arbitrate(gate):
    write_spec(gate)
    producing = gate.accept_full_run("base")
    commit_empty(gate.repo, gate.env)
    identity = tree_identity(gate, "base", "HEAD")
    pre = gate.preflight()
    assert "reuse: miss reason=no accepted run" in pre.stderr, pre.stderr
    first = gate.run_phase("sweep", report_agent(gate.scratch / "reuse-sweep.launched"))
    assert reuse_line(first.stderr).startswith("reuse: hit "), first.stderr
    hunt_marker = gate.scratch / "reuse-hunt.launched"
    hunt = gate.run_phase("hunt", report_agent(hunt_marker))
    assert hunt.returncode == 0, hunt.stdout + hunt.stderr
    assert not hunt_marker.exists(), "the hunt agent was launched for an identical tree"
    assert reuse_line(hunt.stderr) == f"reuse: hit {identity} from run {producing.name}"
    arb_marker = gate.scratch / "reuse-arbitrate.launched"
    arb = gate.run_phase("arbitrate", report_agent(arb_marker, "REVIEW-RAN: yes\nverdict\n"))
    assert arb.returncode == 0, arb.stdout + arb.stderr
    assert arb_marker.exists(), "arbitrate was reused; it must always launch"
    assert one_reuse_line(arb.stderr) == "reuse: miss reason=no accepted run", arb.stderr


def test_every_phase_prints_exactly_one_reuse_line(gate):
    write_spec(gate)
    gate.accept_full_run("base")
    commit_change(gate.repo, gate.env, "three\n")
    pre = gate.preflight()
    assert pre.returncode == 0, pre.stdout + pre.stderr
    assert len([line for line in pre.stderr.splitlines() if line.startswith("reuse: ")]) == 1, pre.stderr
    sweep = gate.run_phase("sweep", report_agent(gate.scratch / "reuse-sweep.launched"))
    assert sweep.returncode == 0, sweep.stdout + sweep.stderr
    assert len([line for line in sweep.stderr.splitlines() if line.startswith("reuse: ")]) == 1, sweep.stderr


# --- Remediation of the pre-PR gate round 1 -------------------------------------------------------

def test_delta_at_an_accepted_current_head_names_the_existing_run(gate):
    """An already accepted HEAD resolves to its own run, never an empty H-H successor."""
    write_spec(gate)
    producing = gate.accept_full_run("base")
    first = gate.paths(delta=True)
    assert first.returncode == 0, first.stdout + first.stderr
    run = next(line.split(" ", 1)[1] for line in first.stdout.splitlines() if line.startswith("run "))
    assert Path(run) == producing
    again = gate.paths(delta=True)
    assert again.returncode == 0, again.stdout + again.stderr
    assert again.stdout == first.stdout


def test_delta_honours_an_explicit_story_base(gate):
    """--delta must not overwrite an explicit --story-base with the inherited one."""
    write_spec(gate)
    gate.accept_full_run("base")
    head_b = _git(gate.repo, gate.env, "rev-parse", "HEAD")
    commit_change(gate.repo, gate.env, "three\n")
    # The inherited story base is `base` (A); name the delta base itself instead, so a delta header
    # would only appear if the inherited value won.
    pre = gate.preflight(delta=True, story_base=head_b)
    assert pre.returncode == 0, pre.stdout + pre.stderr
    copy = gate.scratch / "sweep-dossier-copy.md"
    sweep = gate.run_phase("sweep", capturing_agent(gate.scratch / "reuse-sweep.launched", copy),
                           delta=True, story_base=head_b)
    assert sweep.returncode == 0, sweep.stdout + sweep.stderr
    dossier = copy.read_text()
    assert "STORY-BASE:" not in dossier, dossier
    assert f"BASE: {head_b} {head_b}" in dossier, dossier


def test_a_base_older_than_the_previous_accepted_head_reviews_that_range(gate):
    write_spec(gate)
    gate.accept_full_run("base")
    base_a = _git(gate.repo, gate.env, "rev-parse", "base^{commit}")
    head_b = _git(gate.repo, gate.env, "rev-parse", "HEAD")
    commit_change(gate.repo, gate.env, "three\n")
    Gate(gate.repo, gate.scratch, gate.env, gate.spec).accept_full_run(head_b)
    head_e = commit_change(gate.repo, gate.env, "four\n")
    pre = gate.preflight(base=head_b)
    assert pre.returncode == 0, pre.stdout + pre.stderr
    copy = gate.scratch / "sweep-dossier-copy.md"
    sweep = gate.run_phase("sweep", capturing_agent(gate.scratch / "reuse-sweep.launched", copy),
                           base=head_b)
    assert sweep.returncode == 0, sweep.stdout + sweep.stderr
    dossier = copy.read_text()
    assert f"STORY-BASE: base {base_a}" in dossier, dossier
    assert f"DELTA-BASE: {head_b} {head_b}" in dossier, dossier
    assert f"REVIEWED RANGE: {head_b}...{head_e}" in dossier, dossier


def test_the_miss_reasons_identity_mismatch_and_spec_mismatch_are_reported(gate):
    write_spec(gate, "spec one\n")
    gate.accept_full_run("base")
    # A one-byte change is an identity mismatch.
    commit_change(gate.repo, gate.env, "twO\n")
    assert gate.preflight().returncode == 0
    sweep = gate.run_phase("sweep", report_agent(gate.scratch / "reuse-sweep.launched"))
    assert sweep.returncode == 0, sweep.stdout + sweep.stderr
    assert reuse_line(sweep.stderr) == "reuse: miss reason=identity mismatch", sweep.stderr
    # The same tree with a different spec is a spec mismatch.
    commit_empty(gate.repo, gate.env)
    write_spec(gate, "spec two\n")
    assert gate.preflight().returncode == 0
    sweep = gate.run_phase("sweep", report_agent(gate.scratch / "reuse-sweep-2.launched"))
    assert sweep.returncode == 0, sweep.stdout + sweep.stderr
    assert reuse_line(sweep.stderr) == "reuse: miss reason=spec mismatch", sweep.stderr


def test_a_hit_refused_by_a_missing_local_preflight_is_not_counted(gate):
    write_spec(gate)
    gate.accept_full_run("base")
    commit_empty(gate.repo, gate.env)
    result = gate.run_phase("sweep", report_agent(gate.scratch / "reuse-sweep.launched"))
    assert result.returncode == 13, result.stdout + result.stderr
    assert "reuse: hit" not in result.stderr, result.stderr
    listed = gate.paths().stdout
    assert "reuse_hits 0" in listed, listed
    assert "reused sweep" not in listed, listed


def test_a_no_sweep_hunt_is_not_reused_into_a_sweep_run(gate):
    write_spec(gate)
    assert gate.preflight().returncode == 0
    assert gate.run_phase("hunt", report_agent(gate.scratch / "producing-hunt.launched"),
                          extra=("--no-sweep",)).returncode == 0
    assert gate.run_phase("arbitrate",
                          report_agent(gate.scratch / "producing-arbitrate.launched",
                                       "REVIEW-RAN: yes\nverdict\n"),
                          extra=("--no-sweep",)).returncode == 0
    commit_empty(gate.repo, gate.env)
    assert gate.preflight().returncode == 0
    sweep = gate.run_phase("sweep", report_agent(gate.scratch / "reuse-sweep.launched"))
    assert sweep.returncode == 0, sweep.stdout + sweep.stderr
    hunt_marker = gate.scratch / "reuse-hunt.launched"
    hunt = gate.run_phase("hunt", report_agent(hunt_marker))
    assert hunt.returncode == 0, hunt.stdout + hunt.stderr
    assert hunt_marker.exists(), "a no-sweep hunt was reused into a sweep run"
    assert reuse_line(hunt.stderr).startswith("reuse: miss reason="), hunt.stderr


def test_a_reused_phase_refuses_when_its_producer_lapses(gate):
    write_spec(gate)
    producing = gate.accept_full_run("base")
    commit_empty(gate.repo, gate.env)
    assert gate.preflight().returncode == 0
    assert gate.run_phase("sweep", report_agent(gate.scratch / "reuse-sweep.launched")).returncode == 0
    assert gate.run_phase("hunt", report_agent(gate.scratch / "reuse-hunt.launched")).returncode == 0
    (producing / "phase0-preflight.md.stamp").unlink()
    result = gate.run_phase("arbitrate",
                            report_agent(gate.scratch / "reuse-arbitrate.launched",
                                         "REVIEW-RAN: yes\nverdict\n"))
    assert result.returncode == 13, result.stdout + result.stderr
    assert producing.name in result.stderr, result.stderr


def test_a_reused_phase_refuses_when_the_producer_arbitration_lapses(gate):
    write_spec(gate)
    producing = gate.accept_full_run("base")
    commit_empty(gate.repo, gate.env)
    assert gate.preflight().returncode == 0
    assert gate.run_phase("sweep", report_agent(gate.scratch / "reuse-sweep.launched")).returncode == 0
    assert gate.run_phase("hunt", report_agent(gate.scratch / "reuse-hunt.launched")).returncode == 0
    # Only the producer's arbitration is lost; its phases and preflight still accept.
    (producing / "phase3-arbitration.md.stamp").unlink()
    result = gate.run_phase("arbitrate",
                            report_agent(gate.scratch / "reuse-arbitrate.launched",
                                         "REVIEW-RAN: yes\nverdict\n"))
    assert result.returncode == 13, result.stdout + result.stderr
    assert producing.name in result.stderr, result.stderr


def test_a_fresh_run_reports_four_reuse_misses(gate):
    write_spec(gate)
    assert gate.preflight().returncode == 0
    assert gate.run_phase("sweep", report_agent(gate.scratch / "fresh-sweep.launched")).returncode == 0
    assert gate.run_phase("hunt", report_agent(gate.scratch / "fresh-hunt.launched")).returncode == 0
    assert gate.run_phase("arbitrate", report_agent(gate.scratch / "fresh-arbitrate.launched",
                                                    "REVIEW-RAN: yes\nverdict\n")).returncode == 0
    listed = gate.paths().stdout
    assert "reuse_hits 0" in listed, listed
    assert "reuse_misses 4" in listed, listed


def test_a_conflicting_explicit_story_base_is_refused(gate):
    write_spec(gate)
    gate.accept_full_run("base")
    head_b = _git(gate.repo, gate.env, "rev-parse", "HEAD")
    result = gate.preflight(story_base=head_b)
    assert result.returncode == 12, result.stdout + result.stderr
    assert "already records story base" in result.stderr, result.stderr


def make_repo_with_mid(tmp_path, env, name="repo"):
    repo = tmp_path / name
    repo.mkdir()
    _git(repo, env, "init", "-q", "--initial-branch=main")
    _git(repo, env, "config", "core.autocrlf", "false")
    _git(repo, env, "config", "commit.gpgsign", "false")
    (repo / "tracked.txt").write_text("one\n")
    _git(repo, env, "add", "-A")
    _git(repo, env, "commit", "-q", "-m", "a")
    _git(repo, env, "tag", "base")
    (repo / "mid.txt").write_text("mid\n")
    _git(repo, env, "add", "-A")
    _git(repo, env, "commit", "-q", "-m", "x")
    mid = _git(repo, env, "rev-parse", "HEAD")
    (repo / "tracked.txt").write_text("two\n")
    _git(repo, env, "add", "-A")
    _git(repo, env, "commit", "-q", "-m", "b")
    return repo, mid


def test_delta_with_two_accepted_bases_at_one_head_uses_the_tie_break(tmp_path):
    env = fixed_env(tmp_path)
    repo, mid = make_repo_with_mid(tmp_path, env)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    spec = tmp_path / "spec.txt"
    spec.write_text(SPEC_TEXT)
    gate = Gate(repo, scratch, env, spec)
    first = gate.accept_full_run("base")
    second = Gate(repo, scratch, env, spec).accept_full_run(mid)
    commit_change(repo, env, "three\n")
    listed = gate.paths(delta=True)
    assert listed.returncode == 0, listed.stdout + listed.stderr
    run = next(line.split(" ", 1)[1] for line in listed.stdout.splitlines()
               if line.startswith("run "))
    # Both accepted runs share head B, so the delta base is B whichever run the tie-break names.
    base = Path(run).name.split("-")[0]
    assert base == Path(first).name.split("-")[1] == Path(second).name.split("-")[1], run


def test_a_producer_whose_arbitrate_was_rerun_still_counts_as_lapsed(gate):
    """The append-only acceptance log survives a destructive arbitrate re-run (round 3 High)."""
    write_spec(gate)
    producing = gate.accept_full_run("base")
    failed = gate.run_phase("arbitrate", report_agent(gate.scratch / "repeat-arbitrate.launched",
                                                      "not a review\n"))
    assert failed.returncode != 0, failed.stdout + failed.stderr
    assert (producing / "arbitrate.accepted.log").exists()
    assert not (producing / "phase3-arbitration.md.stamp").exists()
    commit_empty(gate.repo, gate.env)
    assert gate.preflight().returncode == 0
    result = gate.run_phase("sweep", report_agent(gate.scratch / "reuse-sweep.launched"))
    assert result.returncode == 13, result.stdout + result.stderr
    assert "reuse: miss reason=acceptance lapsed" in result.stderr, result.stderr
    assert producing.name in result.stderr, result.stderr


def test_a_producer_whose_preflight_was_rerun_still_counts_as_lapsed(gate):
    """A preflight re-run discards the live model stamps; the acceptance log still proves a lapse."""
    write_spec(gate)
    producing = gate.accept_full_run("base")
    assert gate.preflight().returncode == 0
    assert not (producing / "phase3-arbitration.md.stamp").exists()
    assert (producing / "arbitrate.accepted.log").exists()
    commit_empty(gate.repo, gate.env)
    assert gate.preflight().returncode == 0
    result = gate.run_phase("sweep", report_agent(gate.scratch / "reuse-sweep.launched"))
    assert result.returncode == 13, result.stdout + result.stderr
    assert "reuse: miss reason=acceptance lapsed" in result.stderr, result.stderr
    assert producing.name in result.stderr, result.stderr


def test_delta_and_base_together_are_a_usage_error(gate):
    result = run_script(
        "preflight", "--repo", str(gate.repo), "--base", "base", "--delta",
        "--full-suite", "off", "--scratch", str(gate.scratch), env=gate.env,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "do not also pass --base" in result.stderr, result.stderr


def test_sweep_with_no_sweep_is_a_usage_error(gate):
    write_spec(gate)
    result = gate.run_phase("sweep", report_agent(gate.scratch / "sweep.launched"),
                            extra=("--no-sweep",))
    assert result.returncode == 2, result.stdout + result.stderr
    assert "cannot run with --no-sweep" in result.stderr, result.stderr


def test_a_story_base_that_is_not_an_ancestor_is_refused(gate):
    write_spec(gate)
    _git(gate.repo, gate.env, "checkout", "-q", "base")
    _git(gate.repo, gate.env, "commit", "-q", "--allow-empty", "-m", "sibling")
    sibling = _git(gate.repo, gate.env, "rev-parse", "HEAD")
    _git(gate.repo, gate.env, "checkout", "-q", "-")
    result = gate.preflight(story_base=sibling)
    assert result.returncode == 12, result.stdout + result.stderr
    assert "is not an ancestor of HEAD" in result.stderr, result.stderr


def test_a_producer_that_depends_on_this_run_is_not_reused(gate):
    """Rerunning a run must not reuse a producer whose chain reaches that same run."""
    write_spec(gate)
    producing = gate.accept_full_run("base")
    commit_empty(gate.repo, gate.env)
    assert gate.preflight().returncode == 0
    assert gate.run_phase("sweep", report_agent(gate.scratch / "q-sweep.launched")).returncode == 0
    assert gate.run_phase("hunt", report_agent(gate.scratch / "q-hunt.launched")).returncode == 0
    assert gate.run_phase("arbitrate", report_agent(gate.scratch / "q-arbitrate.launched",
                                                    "REVIEW-RAN: yes\nverdict\n")).returncode == 0
    # The later run depends on the earlier one, so rerunning the earlier run must not reuse it.
    _git(gate.repo, gate.env, "checkout", "-q", producing.name.split("-")[1])
    marker = gate.scratch / "rerun-sweep.launched"
    result = gate.run_phase("sweep", report_agent(marker))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "reuse: hit" not in result.stderr, result.stderr
    assert marker.exists(), "the rerun did not launch a fresh sweep"


def test_a_live_stamp_for_another_spec_does_not_hide_the_recorded_lapse(gate):
    """A producer accepted for this spec and later re-stamped for another spec must refuse, not launch."""
    write_spec(gate, "spec one\n")
    producing = gate.accept_full_run("base")
    # Re-stamp the producer's live chain with a different spec.
    write_spec(gate, "spec two\n")
    assert gate.preflight().returncode == 0
    assert gate.run_phase("sweep", report_agent(gate.scratch / "other-spec-sweep.launched")).returncode == 0
    commit_empty(gate.repo, gate.env)
    write_spec(gate, "spec one\n")
    assert gate.preflight().returncode == 0
    result = gate.run_phase("sweep", report_agent(gate.scratch / "reuse-sweep.launched"))
    assert result.returncode == 13, result.stdout + result.stderr
    assert "reuse: miss reason=acceptance lapsed" in result.stderr, result.stderr
    assert producing.name in result.stderr, result.stderr


def test_a_producer_accepted_for_another_spec_does_not_block_a_fresh_sweep(gate):
    """An acceptance for spec A must not be borrowed as a lapse for spec B on the same trees."""
    write_spec(gate, "spec one\n")
    gate.accept_full_run("base")
    write_spec(gate, "spec two\n")
    commit_empty(gate.repo, gate.env)
    assert gate.preflight().returncode == 0
    marker = gate.scratch / "reuse-sweep.launched"
    result = gate.run_phase("sweep", report_agent(marker))
    assert result.returncode == 0, result.stdout + result.stderr
    assert marker.exists(), "a producer accepted for another spec blocked a fresh sweep"
    assert "acceptance lapsed" not in result.stderr, result.stderr


def test_delta_breaks_a_divergent_maximal_tie_on_committer_date(tmp_path):
    env = fixed_env(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, env, "init", "-q", "--initial-branch=main")
    _git(repo, env, "config", "core.autocrlf", "false")
    _git(repo, env, "config", "commit.gpgsign", "false")
    (repo / "tracked.txt").write_text("root\n")
    _git(repo, env, "add", "-A")
    _git(repo, env, "commit", "-q", "-m", "a")
    _git(repo, env, "tag", "base")
    _git(repo, env, "checkout", "-q", "-b", "side1")
    (repo / "tracked.txt").write_text("p1\n")
    _git(repo, env, "add", "-A")
    _git(repo, env, "commit", "-q", "-m", "p1")
    p1 = _git(repo, env, "rev-parse", "HEAD")
    _git(repo, env, "checkout", "-q", "base")
    _git(repo, env, "checkout", "-q", "-b", "side2")
    (repo / "extra.txt").write_text("p2\n")
    _git(repo, env, "add", "-A")
    later = {**env, "GIT_COMMITTER_DATE": "2026-01-02T00:00:00+0000"}
    subprocess.run(["git", "commit", "-q", "-m", "p2"], cwd=repo, env=later, check=True)
    p2 = _git(repo, env, "rev-parse", "HEAD")
    _git(repo, env, "checkout", "-q", "side2")
    _git(repo, env, "merge", "-q", "--no-ff", "-m", "merge", "side1")
    merge = _git(repo, env, "rev-parse", "HEAD")
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    spec = tmp_path / "spec.txt"
    spec.write_text(SPEC_TEXT)
    # Accept a run at each divergent head, then ask for the delta at the merge.
    for head in (p1, p2):
        _git(repo, env, "checkout", "-q", head)
        assert Gate(repo, scratch, env, spec).accept_full_run("base").name.endswith(head)
    _git(repo, env, "checkout", "-q", merge)
    listed = Gate(repo, scratch, env, spec).paths(delta=True)
    assert listed.returncode == 0, listed.stdout + listed.stderr
    run = next(line.split(" ", 1)[1] for line in listed.stdout.splitlines()
               if line.startswith("run "))
    assert Path(run).name.split("-")[0] == p2, f"expected the later committer date {p2}, got {run}"


def test_a_never_accepted_attempt_at_a_shared_head_does_not_block_reuse(tmp_path):
    env = fixed_env(tmp_path)
    repo, mid = make_repo_with_mid(tmp_path, env)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    spec = tmp_path / "spec.txt"
    spec.write_text(SPEC_TEXT)
    gate = Gate(repo, scratch, env, spec)
    gate.accept_full_run("base")                       # A-B accepted, retains a round at B
    # X-B runs its sweep and hunt but its arbitration fails, so it was never accepted.
    assert gate.preflight(mid).returncode == 0
    assert gate.run_phase("sweep", report_agent(scratch / "failed-sweep.launched"), base=mid).returncode == 0
    assert gate.run_phase("hunt", report_agent(scratch / "failed-hunt.launched"), base=mid).returncode == 0
    failed = gate.run_phase("arbitrate", report_agent(scratch / "failed-arbitrate.launched",
                                                      "not a review\n"), base=mid)
    assert failed.returncode != 0, failed.stdout + failed.stderr
    # A new head with X-B's tree identity must launch fresh, not treat X-B as lapsed.
    commit_empty(repo, env)
    assert gate.preflight(mid).returncode == 0
    marker = scratch / "fresh-sweep.launched"
    sweep = gate.run_phase("sweep", report_agent(marker), base=mid)
    assert sweep.returncode == 0, sweep.stdout + sweep.stderr
    assert marker.exists(), "a never-accepted attempt blocked a fresh sweep"
    assert reuse_line(sweep.stderr) == "reuse: miss reason=no accepted run", sweep.stderr


def test_a_two_hop_reuse_chain_follows_provenance(gate):
    write_spec(gate)
    producer = gate.accept_full_run("base")
    commit_empty(gate.repo, gate.env)
    assert gate.preflight().returncode == 0
    assert gate.run_phase("sweep", report_agent(gate.scratch / "q-sweep.launched")).returncode == 0
    assert gate.run_phase("hunt", report_agent(gate.scratch / "q-hunt.launched")).returncode == 0
    assert gate.run_phase("arbitrate", report_agent(gate.scratch / "q-arbitrate.launched",
                                                    "REVIEW-RAN: yes\nverdict\n")).returncode == 0
    middle = gate.run_dir()
    commit_empty(gate.repo, gate.env)
    assert gate.preflight().returncode == 0
    assert gate.run_phase("sweep", report_agent(gate.scratch / "r-sweep.launched")).returncode == 0
    assert gate.run_phase("hunt", report_agent(gate.scratch / "r-hunt.launched")).returncode == 0
    second = gate.run_dir()
    assert (middle / "sweep.reuse").read_text().splitlines()[1] == f"run={producer.name}"
    assert (second / "sweep.reuse").read_text().splitlines()[1] == f"run={middle.name}"
    # Breaking the far end of the chain breaks the consumer's provenance.
    (producer / "phase0-preflight.md.stamp").unlink()
    result = gate.run_phase("arbitrate", report_agent(gate.scratch / "r-arbitrate.launched",
                                                      "REVIEW-RAN: yes\nverdict\n"))
    assert result.returncode == 13, result.stdout + result.stderr
    assert middle.name in result.stderr, result.stderr


# --- AC7 / AC4: deterministic dossier input -------------------------------------------------------

def sweep_dossier_bytes(gate: Gate) -> bytes:
    result = gate.preflight()
    assert result.returncode == 0, result.stdout + result.stderr
    copy = gate.scratch / "dossier-default.md"
    result = gate.run_phase("sweep", capturing_agent(gate.scratch / "sweep.launched", copy))
    assert result.returncode == 0, result.stdout + result.stderr
    return copy.read_bytes()


def test_hostile_git_config_leaves_the_dossier_and_identity_unchanged(tmp_path):
    default_env = fixed_env(tmp_path / "default")
    hostile_env = fixed_env(tmp_path / "hostile")
    config = tmp_path / "hostile.gitconfig"
    # diff.quotePath is the key the story names; core.quotePath is the key git actually reads.
    config.write_text(
        "[diff]\n\talgorithm = patience\n\tnoprefix = true\n\tquotePath = false\n\tcontext = 5\n"
        "[core]\n\tquotePath = false\n\tabbrev = 40\n"
    )
    hostile_env["GIT_CONFIG_GLOBAL"] = str(config)

    def add_unicode(repo: Path, env: dict[str, str]) -> None:
        (repo / "café.txt").write_text("accented\n")
        _git(repo, env, "add", "-A")
        _git(repo, env, "commit", "-q", "-m", "unicode path")

    def build(env: dict[str, str], root: Path) -> Gate:
        root.mkdir()
        repo, _ = make_repo(root, env)
        add_unicode(repo, env)
        scratch = root / "session-scratch"
        scratch.mkdir()
        spec = root / "spec.txt"
        spec.write_text(SPEC_TEXT)
        return Gate(repo, scratch, env, spec)

    default_gate = build(default_env, tmp_path / "default" / "run")
    hostile_gate = build(hostile_env, tmp_path / "hostile" / "run")
    default_bytes = sweep_dossier_bytes(default_gate)
    hostile_bytes = sweep_dossier_bytes(hostile_gate)

    def normalize(gate: Gate, text: bytes) -> bytes:
        # The checkout path is inside the session scratch, so replace the longer value first.
        checkout = next(line[len("CHECKOUT: "):].encode() for line in text.decode().splitlines()
                        if line.startswith("CHECKOUT: "))
        out = text.replace(checkout, b"<CHECKOUT>")
        out = out.replace(str(gate.scratch).encode(), b"<SESSION-SCRATCH>")
        for ref in ("base^{commit}", "HEAD"):
            sha = _git(gate.repo, gate.env, "rev-parse", ref).encode()
            out = out.replace(sha, b"<COMMIT>")
        return out

    assert normalize(default_gate, default_bytes) == normalize(hostile_gate, hostile_bytes)
    # And the tree identity the reuse fires on is unchanged under the hostile config.
    assert tree_identity(default_gate, "base", "HEAD") == tree_identity(hostile_gate, "base", "HEAD")


def test_hostile_git_config_still_reuses_the_identical_tree(tmp_path):
    hostile_env = fixed_env(tmp_path)
    config = tmp_path / "hostile.gitconfig"
    config.write_text(
        "[diff]\n\talgorithm = patience\n\tnoprefix = true\n\tquotePath = false\n\tcontext = 5\n"
        "[core]\n\tquotePath = false\n\tabbrev = 40\n"
    )
    hostile_env["GIT_CONFIG_GLOBAL"] = str(config)
    repo, _ = make_repo(tmp_path, hostile_env)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    spec = tmp_path / "spec.txt"
    spec.write_text(SPEC_TEXT)
    gate = Gate(repo, scratch, hostile_env, spec)
    producing = gate.accept_full_run("base")
    commit_empty(repo, hostile_env)
    identity = tree_identity(gate, "base", "HEAD")
    result = gate.preflight()
    assert result.returncode == 0, result.stdout + result.stderr
    marker = scratch / "sweep.launched"
    result = gate.run_phase("sweep", report_agent(marker))
    assert result.returncode == 0, result.stdout + result.stderr
    assert not marker.exists(), "hostile diff config stopped the identical-tree reuse"
    assert reuse_line(result.stderr) == f"reuse: hit {identity} from run {producing.name}"


# --- AC4: the non-delta path is byte-identical to the pre-change script ---------------------------

APP_BASE = (
    "def total(items):\n    ans = 0\n    for item in items:\n        ans += item\n"
    "    return ans\n\n\ndef label(x):\n    return 'value: ' + str(x)\n"
)
APP_HEAD = (
    "def total(items):\n    ans = 0\n    for item in items:\n        ans += item\n"
    "    return ans\n\n\ndef label(x):\n    return f'value: {x}'\n\n\ndef mean(items):\n"
    "    return total(items) / len(items)\n"
)


def test_the_non_delta_sweep_dossier_is_byte_identical_to_the_pre_change_script(tmp_path):
    # GOLDEN was captured from the pre-change script at origin/main 554ddb6, before this change:
    # the same deterministic repository, `preflight --full-suite off` then `dossier sweep`, with the
    # checkout/scratch paths and commit ids normalized. It is not regenerated from this script.
    env = fixed_env(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, env, "init", "-q", "--initial-branch=main")
    _git(repo, env, "config", "core.autocrlf", "false")
    _git(repo, env, "config", "commit.gpgsign", "false")
    (repo / "app.py").write_text(APP_BASE)
    (repo / "notes.md").write_text("# Notes\n\nBase notes.\n")
    _git(repo, env, "add", "-A")
    _git(repo, env, "commit", "-q", "-m", "base")
    _git(repo, env, "tag", "base")
    (repo / "app.py").write_text(APP_HEAD)
    (repo / "extra.txt").write_text("extra line\n")
    _git(repo, env, "add", "-A")
    _git(repo, env, "commit", "-q", "-m", "head")
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    spec = tmp_path / "spec.txt"
    spec.write_text(
        "SKL-411 deterministic dossier fixture - not real data\n\n"
        "Acceptance: the dossier is byte-identical for the same head on any machine.\n"
    )
    result = run_script("preflight", "--full-suite", "off", "--repo", str(repo), "--base", "base",
                        "--test-cmd", "true", "--scratch", str(scratch), env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    result = run_script("dossier", "sweep", "--repo", str(repo), "--base", "base",
                        "--spec", str(spec), "--scratch", str(scratch), env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    dossier = Path(result.stdout.strip().splitlines()[-1])
    checkout = next(line[len("CHECKOUT: "):] for line in result.stderr.splitlines()
                    if line.startswith("CHECKOUT: "))
    normalized = dossier.read_bytes()
    normalized = normalized.replace(checkout.encode(), b"<CHECKOUT>")
    normalized = normalized.replace(str(dossier.parent).encode(), b"<RUN-SCRATCH>")
    normalized = normalized.replace(str(scratch).encode(), b"<SESSION-SCRATCH>")
    base_sha = _git(repo, env, "rev-parse", "base^{commit}")
    head_sha = _git(repo, env, "rev-parse", "HEAD")
    commit_placeholder = "<COMMIT-ID" + "-" * 29 + ">"
    normalized = normalized.replace(base_sha.encode(), commit_placeholder.encode())
    normalized = normalized.replace(head_sha.encode(), commit_placeholder.encode())
    assert normalized == GOLDEN.read_bytes(), (
        "the non-delta sweep dossier changed from the pre-change script; diff:\n"
        + normalized.decode(errors="replace")
    )
