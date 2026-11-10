"""The persisted dossier sizes are rendered as one log, `dossier-sizes.md`, in the run directory.

SKL-241. The log is rebuilt from the `<phase>.dossier` sidecars (SKL-89) after every completed
sidecar write and after every removal by `begin_phase` (its `invalidate_downstream` discards
included, whether or not a sidecar was present) or by the `dossier` command's exit trap. It lists
sweep, hunt and arbitrate in that order: `<phase>: <bytes> bytes` and the sidecar's `excluded` lines
for a phase with a sidecar, `<phase>: not run` for one without, `sweep: absent (--no-sweep)` when the
invocation sets `--no-sweep`, and `total: <bytes> bytes` once every phase not disabled has a sidecar.
`paths` prints its absolute path as a final `dossier_sizes <path>` line. The log is never a demanded
artefact, never enters the binding or a stamp, and a failure to write it only warns.

Every test seeds a base commit and a head commit and reviews the head against its base, on both
flows: `run`, and `dossier` followed by `record`.
"""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "adversarial-review-pipeline" / "scripts" / "run-adversarial-pipeline.sh"
BASE_REF = "base"
PHASES = ("sweep", "hunt", "arbitrate")
FLOWS = ("run", "dossier")

# Host git configuration and repository-locating variables never reach a fixture.
GIT_ISOLATION = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
GIT_LOCATORS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
                "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_EXTERNAL_DIFF")


def isolated_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("ADVERSARIAL_") and k not in GIT_LOCATORS}
    return {**env, **GIT_ISOLATION}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, env=isolated_env(),
    ).stdout.strip()


def make_repo(tmp_path: Path, base: dict[str, str], head: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "agent-skills@example.com")
    git(repo, "config", "user.name", "agent-skills")
    git(repo, "config", "commit.gpgsign", "false")
    git(repo, "config", "tag.gpgsign", "false")
    for files, message in ((base, "base"), (head, "head")):
        for rel, content in files.items():
            path = repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", message)
        if message == "base":
            git(repo, "tag", BASE_REF)
    return repo


def run_script(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=120,
    )


def make_gate(tmp_path: Path, repo: Path) -> dict:
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    (tmp_path / "runtime-tmp").mkdir()
    env = {**isolated_env(), "TMPDIR": str(tmp_path / "runtime-tmp")}
    spec = tmp_path / "spec.md"
    spec.write_text("Story SKL-241: dossier size log.\n")
    g = {"repo": repo, "scratch": scratch, "env": env, "spec": spec, "tmp": tmp_path}
    preflight = run_script("preflight", "--repo", str(repo), "--base", BASE_REF, "--test-cmd", "true",
                           "--scratch", str(scratch), env=env)
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    return g


@pytest.fixture
def gate(tmp_path):
    repo = make_repo(tmp_path, {"app.py": "def total(items):\n    return sum(items)\n"},
                     {"app.py": "def total(items):\n    return sum(i for i in items if i > 0)\n"})
    return make_gate(tmp_path, repo)


@pytest.fixture
def excluding_gate(tmp_path):
    """A repository whose sweep and hunt dossiers exclude paths, one of them needing an escape."""
    repo = make_repo(
        tmp_path,
        {"app.py": "x = 1\n",
         ".gitattributes": "gen/** linguist-generated\n",
         ".adversarial-exclude": "fixtures/*\n"},
        {"app.py": "x = 2\n",
         "gen/out.txt": "generated\n",
         'fixtures/q"uote.json': "{}\n"},
    )
    return make_gate(tmp_path, repo)


def common(g: dict) -> list[str]:
    return ["--repo", str(g["repo"]), "--base", BASE_REF, "--spec", str(g["spec"]),
            "--scratch", str(g["scratch"])]


def paths_output(g: dict) -> list[str]:
    listed = run_script("paths", "--repo", str(g["repo"]), "--base", BASE_REF, env=g["env"])
    assert listed.returncode == 0, listed.stdout + listed.stderr
    return listed.stdout.splitlines()


def artifact_paths(g: dict) -> dict[str, Path]:
    return {name: Path(path) for name, _, path in
            (line.partition(" ") for line in paths_output(g)) if path}


def run_dir(g: dict) -> Path:
    return artifact_paths(g)["run"]


def size_log(g: dict) -> Path:
    return run_dir(g) / "dossier-sizes.md"


def line_value(text: str, prefix: str) -> str:
    lines = [line for line in text.splitlines() if line.startswith(prefix)]
    assert len(lines) == 1, f"expected exactly one {prefix!r} line, got {lines}"
    return lines[0][len(prefix):]


# The fake agent records the dossier path it was handed and writes a minimal accepted report.
AGENT = (
    's="$ADVERSARIAL_SESSION_SCRATCH/seen-$PHASE_NAME"; mkdir -p "$s"; '
    'printf "%s" {prompt_file} > "$s/path"; '
    'printf "REVIEW-RAN: yes\\nreport\\n" > {output_file}'
)


def run_phase(g: dict, phase: str, *extra: str, env: dict[str, str] | None = None):
    return run_script("run", phase, *common(g), "--agent-cmd", AGENT, *extra,
                      env={**(env or g["env"]), "PHASE_NAME": phase})


def record(g: dict, phase: str, *extra: str) -> subprocess.CompletedProcess:
    artifact_paths(g)[phase].write_text(f"REVIEW-RAN: yes\n{phase} report\n")
    return run_script("record", phase, "--repo", str(g["repo"]), "--base", BASE_REF,
                      "--spec", str(g["spec"]), *extra, env=g["env"])


def cleanup(g: dict, checkout: Path) -> None:
    result = run_script("cleanup", str(checkout), "--repo", str(g["repo"]), env=g["env"])
    assert result.returncode == 0, result.stdout + result.stderr


def complete(g: dict, flow: str, phase: str, *extra: str) -> int:
    """Runs the phase to acceptance on the given flow and returns its dossier's size in bytes."""
    if flow == "run":
        result = run_phase(g, phase, *extra)
        assert result.returncode == 0, result.stdout + result.stderr
        dossier = Path((g["scratch"] / f"seen-{phase}" / "path").read_text())
    else:
        result = run_script("dossier", phase, *common(g), *extra, env=g["env"])
        assert result.returncode == 0, result.stdout + result.stderr
        dossier = Path(result.stdout.strip().splitlines()[-1])
        recorded = record(g, phase, *extra)
        assert recorded.returncode == 0, recorded.stdout + recorded.stderr
        cleanup(g, Path(line_value(result.stderr, "CHECKOUT: ")))
    return len(dossier.read_bytes())


def warnings(result: subprocess.CompletedProcess) -> list[str]:
    return [line for line in result.stderr.splitlines() if line.startswith("WARNING:")]


# --- the log's lines on both flows -------------------------------------------------------------------

@pytest.mark.parametrize("flow", FLOWS)
def test_after_the_sweep(gate, flow):
    sweep = complete(gate, flow, "sweep")
    assert size_log(gate).read_text() == (
        f"sweep: {sweep} bytes\n"
        "hunt: not run\n"
        "arbitrate: not run\n")


@pytest.mark.parametrize("flow", FLOWS)
def test_after_the_sweep_and_the_hunt(gate, flow):
    sweep = complete(gate, flow, "sweep")
    hunt = complete(gate, flow, "hunt")
    assert size_log(gate).read_text() == (
        f"sweep: {sweep} bytes\n"
        f"hunt: {hunt} bytes\n"
        "arbitrate: not run\n")


@pytest.mark.parametrize("flow", FLOWS)
def test_every_phase_run_prints_the_total(gate, flow):
    sizes = {phase: complete(gate, flow, phase) for phase in PHASES}
    assert size_log(gate).read_text() == (
        f"sweep: {sizes['sweep']} bytes\n"
        f"hunt: {sizes['hunt']} bytes\n"
        f"arbitrate: {sizes['arbitrate']} bytes\n"
        f"total: {sum(sizes.values())} bytes\n")


@pytest.mark.parametrize("flow", FLOWS)
def test_after_a_no_sweep_hunt_and_arbitrate(gate, flow):
    hunt = complete(gate, flow, "hunt", "--no-sweep")
    assert size_log(gate).read_text() == (
        "sweep: absent (--no-sweep)\n"
        f"hunt: {hunt} bytes\n"
        "arbitrate: not run\n")
    arbitrate = complete(gate, flow, "arbitrate", "--no-sweep")
    assert size_log(gate).read_text() == (
        "sweep: absent (--no-sweep)\n"
        f"hunt: {hunt} bytes\n"
        f"arbitrate: {arbitrate} bytes\n"
        f"total: {hunt + arbitrate} bytes\n")


@pytest.mark.parametrize("flow", FLOWS)
def test_a_no_sweep_invocation_ignores_an_existing_sweep_sidecar(gate, flow):
    complete(gate, flow, "sweep")
    assert (run_dir(gate) / "sweep.dossier").is_file()
    hunt = complete(gate, flow, "hunt", "--no-sweep")
    arbitrate = complete(gate, flow, "arbitrate", "--no-sweep")
    assert (run_dir(gate) / "sweep.dossier").is_file(), "the sweep sidecar should still be there"
    assert size_log(gate).read_text() == (
        "sweep: absent (--no-sweep)\n"
        f"hunt: {hunt} bytes\n"
        f"arbitrate: {arbitrate} bytes\n"
        f"total: {hunt + arbitrate} bytes\n")


@pytest.mark.parametrize("flow", FLOWS)
def test_after_a_sweep_rerun_discards_the_hunt_and_arbitrate(gate, flow):
    for phase in PHASES:
        complete(gate, flow, phase)
    assert size_log(gate).read_text().endswith(" bytes\n") and "total: " in size_log(gate).read_text()
    sweep = complete(gate, flow, "sweep")
    assert size_log(gate).read_text() == (
        f"sweep: {sweep} bytes\n"
        "hunt: not run\n"
        "arbitrate: not run\n")


@pytest.mark.parametrize("flow", FLOWS)
def test_excluded_lines_follow_their_phase_in_sidecar_order(excluding_gate, flow):
    g = excluding_gate
    sizes = {phase: complete(g, flow, phase) for phase in PHASES}
    excluded = ('excluded "fixtures/q\\"uote.json" reason=glob:fixtures/*\n'
                "excluded gen/out.txt reason=linguist-generated\n")
    for phase in ("sweep", "hunt"):
        side = (run_dir(g) / f"{phase}.dossier").read_text()
        assert side.endswith(excluded), side
    assert size_log(g).read_text() == (
        f"sweep: {sizes['sweep']} bytes\n" + excluded
        + f"hunt: {sizes['hunt']} bytes\n" + excluded
        + f"arbitrate: {sizes['arbitrate']} bytes\n"
        f"total: {sum(sizes.values())} bytes\n")


@pytest.mark.parametrize("flow", FLOWS)
def test_a_removal_that_finds_no_sidecar_still_rebuilds_the_log(gate, flow):
    """A hunt whose dossier write fails removes no sidecar (none exists), yet the log is rebuilt."""
    sweep = complete(gate, flow, "sweep")
    size_log(gate).write_text("stale\n")
    real_git = subprocess.run(["bash", "-c", "command -v git"], capture_output=True,
                              text=True, check=True).stdout.strip()
    fakebin = gate["tmp"] / "fakebin-git"
    fakebin.mkdir()
    (fakebin / "git").write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = diff ] && [ "$2" = --stat ]; then echo refused >&2; exit 3; fi\n'
        f'exec "{real_git}" "$@"\n')
    (fakebin / "git").chmod(0o755)
    env = {**gate["env"], "PATH": f"{fakebin}:{gate['env']['PATH']}"}
    if flow == "run":
        result = run_phase(gate, "hunt", env=env)
    else:
        result = run_script("dossier", "hunt", *common(gate), env=env)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "could not write the hunt dossier" in result.stderr, result.stderr
    assert size_log(gate).read_text() == (
        f"sweep: {sweep} bytes\n"
        "hunt: not run\n"
        "arbitrate: not run\n")


def test_a_sidecar_the_dossier_exit_trap_removes_leaves_the_log(gate):
    """With stdout closed the dossier and its sidecar are written, then the exit trap undoes both."""
    sweep = complete(gate, "dossier", "sweep")
    result = subprocess.run(
        ["bash", "-c", 'exec >&-; exec bash "$0" "$@"', str(SCRIPT), "dossier", "hunt", *common(gate)],
        stderr=subprocess.PIPE, text=True, env=gate["env"], cwd=str(ROOT), timeout=120,
    )
    assert result.returncode != 0, result.stderr
    assert "could not write the hunt dossier" in result.stderr, result.stderr
    assert not (run_dir(gate) / "hunt.dossier").exists()
    assert size_log(gate).read_text() == (
        f"sweep: {sweep} bytes\n"
        "hunt: not run\n"
        "arbitrate: not run\n")


# --- the paths line ----------------------------------------------------------------------------------

def test_paths_prints_the_log_as_a_final_added_line(gate):
    lines = paths_output(gate)
    run = Path(lines[0].split(" ", 1)[1])
    assert run.is_absolute(), lines
    assert [line.split(" ", 1)[0] for line in lines] == [
        "run", "preflight", "suite_log", "sweep", "hunt", "arbitrate", "dossier_sizes"], lines
    assert lines[1:6] == [
        f"preflight {run}/phase0-preflight.md",
        f"suite_log {run}/phase0-suite.log",
        f"sweep {run}/phase1-sweep.md",
        f"hunt {run}/phase2-hunt.md",
        f"arbitrate {run}/phase3-arbitration.md",
    ], lines
    assert lines[6] == f"dossier_sizes {run}/dossier-sizes.md", lines


# --- invocations refused before begin_phase leave the log unchanged ------------------------------------

def test_a_dossier_refused_by_its_predecessor_check_leaves_the_log_unchanged(gate):
    complete(gate, "dossier", "sweep")
    before = size_log(gate).read_bytes()
    os.utime(size_log(gate), (1, 1))
    refused = run_script("dossier", "arbitrate", *common(gate), env=gate["env"])
    assert refused.returncode == 13, refused.stdout + refused.stderr
    assert size_log(gate).read_bytes() == before
    assert size_log(gate).stat().st_mtime == 1, "the refused invocation rewrote the log"


def test_a_run_refused_for_a_missing_agent_cmd_leaves_the_log_unchanged(gate):
    complete(gate, "run", "sweep")
    before = size_log(gate).read_bytes()
    os.utime(size_log(gate), (1, 1))
    refused = run_script("run", "hunt", *common(gate), env=gate["env"])
    assert refused.returncode == 2, refused.stdout + refused.stderr
    assert "--agent-cmd" in refused.stderr, refused.stderr
    assert size_log(gate).read_bytes() == before
    assert size_log(gate).stat().st_mtime == 1, "the refused invocation rewrote the log"


# --- a log that cannot be written only warns ----------------------------------------------------------

@pytest.mark.parametrize("flow", FLOWS)
def test_a_log_write_failure_warns_and_changes_no_outcome(gate, flow):
    blocker = size_log(gate)
    blocker.unlink(missing_ok=True)   # the preflight's discards already wrote it
    blocker.mkdir()
    (blocker / "keep").write_text("a directory in the log's place cannot be replaced\n")
    if flow == "run":
        result = run_phase(gate, "sweep")
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stderr.splitlines()[-1].endswith(" exit=0"), result.stderr
    else:
        result = run_script("dossier", "sweep", *common(gate), env=gate["env"])
        assert result.returncode == 0, result.stdout + result.stderr
        assert Path(result.stdout.strip().splitlines()[-1]).is_file()
        recorded = record(gate, "sweep")
        assert recorded.returncode == 0, recorded.stdout + recorded.stderr
        cleanup(gate, Path(line_value(result.stderr, "CHECKOUT: ")))
    found = warnings(result)
    assert len(found) == 1 and "dossier-sizes.md" in found[0], result.stderr
    assert (run_dir(gate) / "sweep.dossier").is_file(), "the sidecar write must be unaffected"
    assert blocker.is_dir()
    assert sorted(p.name for p in run_dir(gate).iterdir() if "dossier-sizes.md.tmp" in p.name) == []
    # the sweep stays accepted: the hunt starts from it
    blocker.joinpath("keep").unlink()
    blocker.rmdir()
    hunt = complete(gate, flow, "hunt")
    assert f"hunt: {hunt} bytes\n" in size_log(gate).read_text()


# --- the log never enters the binding or the acceptance ------------------------------------------------

@pytest.mark.parametrize("flow", FLOWS)
def test_the_log_alone_changes_neither_the_binding_nor_acceptance(gate, flow):
    for phase in PHASES:
        complete(gate, flow, phase)
    binding = (run_dir(gate) / "arbitrate.binding").read_text()
    stamps = {phase: Path(f"{artifact_paths(gate)[phase]}.stamp").read_text() for phase in PHASES}
    size_log(gate).write_text("tampered\n")
    complete(gate, flow, "arbitrate")
    assert (run_dir(gate) / "arbitrate.binding").read_text() == binding
    assert {phase: Path(f"{artifact_paths(gate)[phase]}.stamp").read_text()
            for phase in PHASES} == stamps
    size_log(gate).unlink()
    if flow == "dossier":
        recorded = record(gate, "arbitrate")
        assert recorded.returncode == 0, recorded.stdout + recorded.stderr
    else:
        complete(gate, flow, "arbitrate")
    for phase in PHASES:
        assert "dossier-sizes" not in Path(f"{artifact_paths(gate)[phase]}.stamp").read_text()
