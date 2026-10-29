"""Every phase dossier names its own throwaway checkout and base, and the arbiter reads the diff there.

SKL-86. The arbitrate dossier carries no unified diff: it carries the story, the diffstat, both
phase reports, the base ref and head SHA, and the arbiter's checkout on a `CHECKOUT: ` line. Every
dossier - sweep, hunt and arbitrate, on the `run` and the `dossier` flows - states the absolute
path of that phase's checkout on a `CHECKOUT: ` line and the base on a `BASE: <ref> <sha>` line,
and the checkout exists before the dossier is written. A dossier that cannot be written leaves no
registered checkout behind on either flow.

Every test seeds a two-commit repository and reviews the head against its base commit, so the
dossiers carry a real diff (never `--base HEAD`).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "adversarial-review-pipeline"
SCRIPT = SKILL_DIR / "scripts" / "run-adversarial-pipeline.sh"
SKILL_MD = SKILL_DIR / "SKILL.md"
PHASES = ("sweep", "hunt", "arbitrate")
BASE_REF = "base"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
    ).stdout.strip()


def make_two_commit_repo(tmp_path: Path) -> tuple[Path, str, str]:
    """A base commit (tagged `base`) and a head commit that changes code, so the diff is real."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "agent-skills@example.com")
    git(repo, "config", "user.name", "agent-skills")
    git(repo, "config", "commit.gpgsign", "false")  # an inherited signing config must not break the fixture
    git(repo, "config", "tag.gpgsign", "false")
    (repo / "app.py").write_text("def total(items):\n    return sum(items)\n")
    git(repo, "add", "app.py")
    git(repo, "commit", "-qm", "base")
    git(repo, "tag", BASE_REF)
    (repo / "app.py").write_text(
        "def total(items):\n    return sum(i for i in items if i > 0)  # SKL86-HEAD-CHANGE\n"
    )
    git(repo, "add", "app.py")
    git(repo, "commit", "-qm", "head")
    return repo, git(repo, "rev-parse", f"{BASE_REF}^{{commit}}"), git(repo, "rev-parse", "HEAD")


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("ADVERSARIAL_")}
    return {**env, **(extra or {})}


def run_script(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=120,
    )


@pytest.fixture
def gate(tmp_path):
    repo, base_sha, head_sha = make_two_commit_repo(tmp_path)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    (tmp_path / "runtime-tmp").mkdir()
    env = clean_env({"TMPDIR": str(tmp_path / "runtime-tmp")})
    spec = tmp_path / "spec.md"
    spec.write_text("Story SKL-86: the total ignores negative items.\n")
    preflight = run_script(
        "preflight", "--repo", str(repo), "--base", BASE_REF, "--test-cmd", "true",
        "--scratch", str(scratch), env=env,
    )
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    return {"repo": repo, "base": base_sha, "head": head_sha, "scratch": scratch,
            "env": env, "spec": spec, "tmp": tmp_path}


def common(g: dict) -> list[str]:
    return ["--repo", str(g["repo"]), "--base", BASE_REF, "--spec", str(g["spec"]),
            "--scratch", str(g["scratch"])]


def artifact_paths(g: dict) -> dict[str, Path]:
    listed = run_script("paths", "--repo", str(g["repo"]), "--base", BASE_REF, env=g["env"])
    assert listed.returncode == 0, listed.stdout + listed.stderr
    return {name: Path(path) for name, _, path in
            (line.partition(" ") for line in listed.stdout.splitlines()) if path}


def line_value(text: str, prefix: str) -> str:
    """The value of the one line that begins with `prefix`; exactly one such line must exist."""
    lines = [line for line in text.splitlines() if line.startswith(prefix)]
    assert len(lines) == 1, f"expected exactly one {prefix!r} line, got {lines}"
    return lines[0][len(prefix):]


def registered_worktrees(repo: Path) -> list[str]:
    out = git(repo, "worktree", "list", "--porcelain")
    return [line.removeprefix("worktree ") for line in out.splitlines() if line.startswith("worktree ")]


def registry_lines(repo: Path) -> list[str]:
    registry = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path",
                        "adversarial-pipeline")) / "checkouts.registry"
    return [line for line in registry.read_text().splitlines() if line] if registry.exists() else []


# The fake agent snapshots what it was handed at delivery: the dossier, whether the advertised
# checkout existed, where it was run, and that checkout's HEAD and detached state.
OBSERVER_AGENT = (
    'd={prompt_file}; s="$ADVERSARIAL_SESSION_SCRATCH/seen-$PHASE_NAME"; mkdir -p "$s"; '
    'cp "$d" "$s/dossier.md"; '
    'c="$(sed -n "s/^CHECKOUT: //p" "$d")"; '
    '{ printf "REVIEW-RAN: yes\\n"; '
    'if [ -n "$c" ] && [ -d "$c" ]; then echo "exists=yes"; else echo "exists=no"; fi; '
    'echo "pwd=$(pwd -P)"; echo "checkout_arg=$(cd {checkout} && pwd -P)"; '
    'echo "advertised=$(cd "$c" 2>/dev/null && pwd -P)"; '
    'echo "head=$(git -C "$c" rev-parse HEAD 2>/dev/null)"; '
    'if git -C "$c" symbolic-ref -q HEAD >/dev/null; then echo "detached=no"; else echo "detached=yes"; fi; '
    '} > {output_file}'
)


def run_phase(g: dict, phase: str, *extra: str) -> subprocess.CompletedProcess:
    env = {**g["env"], "PHASE_NAME": phase}
    return run_script("run", phase, *common(g), "--agent-cmd", OBSERVER_AGENT, *extra, env=env)


def run_all_phases(g: dict) -> dict[str, tuple[str, dict[str, str]]]:
    """Runs sweep, hunt and arbitrate; returns each phase's dossier text and the agent's observations."""
    seen = {}
    paths = artifact_paths(g)
    for phase in PHASES:
        result = run_phase(g, phase)
        assert result.returncode == 0, result.stdout + result.stderr
        report = paths[phase].read_text()
        observed = dict(line.split("=", 1) for line in report.splitlines()[1:])
        dossier = (g["scratch"] / f"seen-{phase}" / "dossier.md").read_text()
        seen[phase] = (dossier, observed)
    return seen


def dossier_phase(g: dict, phase: str) -> tuple[Path, Path, subprocess.CompletedProcess]:
    """`dossier <phase>`: returns the dossier path (stdout) and the checkout path (stderr)."""
    result = run_script("dossier", phase, *common(g), env=g["env"])
    assert result.returncode == 0, result.stdout + result.stderr
    dossier = Path(result.stdout.strip().splitlines()[-1])
    checkout = Path(line_value(result.stderr, "CHECKOUT: "))
    return dossier, checkout, result


def record_phase(g: dict, phase: str) -> None:
    artifact_paths(g)[phase].write_text(f"REVIEW-RAN: yes\n{phase} report\n")
    recorded = run_script("record", phase, "--repo", str(g["repo"]), "--base", BASE_REF,
                          "--spec", str(g["spec"]), env=g["env"])
    assert recorded.returncode == 0, recorded.stdout + recorded.stderr


# --- the arbitrate dossier carries no diff; sweep and hunt still do --------------------------------

def test_the_arbitrate_dossier_carries_no_diff_while_sweep_and_hunt_still_do(gate):
    seen = run_all_phases(gate)
    for phase in ("sweep", "hunt"):
        dossier = seen[phase][0]
        assert "===== DIFF (" in dossier, f"the {phase} dossier lost its embedded diff"
        assert "diff --git a/app.py b/app.py" in dossier, dossier
        assert "SKL86-HEAD-CHANGE" in dossier, f"the {phase} dossier does not show the change"
    arbitrate = seen["arbitrate"][0]
    assert "===== DIFF" not in arbitrate, "the arbitrate dossier still carries a diff section"
    assert "diff --git" not in arbitrate and "SKL86-HEAD-CHANGE" not in arbitrate, \
        "the arbitrate dossier still embeds unified-diff text"
    # what the arbiter still receives
    assert "Story SKL-86" in arbitrate, "the arbitrate dossier lost the story"
    assert "app.py | " in arbitrate, "the arbitrate dossier lost the diffstat"
    assert "===== PHASE 1 (sweep candidates) =====" in arbitrate
    assert "===== PHASE 2 (empirical results) =====" in arbitrate
    assert line_value(arbitrate, "HEAD: ") == gate["head"]


def test_the_arbitrate_dossier_keeps_the_absent_sweep_placeholder_under_no_sweep(gate):
    for phase in ("hunt", "arbitrate"):
        result = run_phase(gate, phase, "--no-sweep")
        assert result.returncode == 0, result.stdout + result.stderr
    arbitrate = (gate["scratch"] / "seen-arbitrate" / "dossier.md").read_text()
    assert "===== PHASE 1 (sweep candidates) =====\n(sweep not configured)\n" in arbitrate, arbitrate
    assert "===== DIFF" not in arbitrate


def test_the_arbitrate_preamble_offers_a_checkout_instead_of_an_inline_diff(gate):
    for phase in ("hunt", "arbitrate"):
        assert run_phase(gate, phase, "--no-sweep").returncode == 0
    arbitrate = (gate["scratch"] / "seen-arbitrate" / "dossier.md").read_text()
    preamble = arbitrate.split("===== ", 1)[0]
    assert not re.search(r"You get the diff\b(?!stat)", preamble), \
        "the preamble still claims the diff is inline"
    assert "read the diff and both phase" not in " ".join(preamble.split())
    assert "diffstat" in preamble and "checkout" in preamble.lower(), preamble
    attest = next(line for line in preamble.splitlines() if "'REVIEW-RAN: yes' when" in line)
    attest_block = preamble[preamble.index(attest):]
    for needed in ("diffstat", "both phase", "CHECKOUT: "):
        assert needed in attest_block.split("'REVIEW-RAN: no", 1)[0], \
            f"REVIEW-RAN: yes is not conditional on {needed!r}: {attest_block}"


def test_the_arbitration_report_layout_is_unchanged(gate):
    for phase in ("hunt", "arbitrate"):
        assert run_phase(gate, phase, "--no-sweep").returncode == 0
    arbitrate = (gate["scratch"] / "seen-arbitrate" / "dossier.md").read_text()
    layout = (
        "### Critical vulnerabilities and breaking bugs\n"
        "(Only items validated by Phase-2 execution or confirmed by your reasoning.)\n"
        "* **File/Line:** path/to/file.ext:line\n"
        "* **The bug:** concise description.\n"
        "* **Empirical evidence:** failing test log or exact logic trace.\n"
        "* **Remediation:** suggested patch.\n"
        "\n"
        "### Optimizations and code smells\n"
        "(Lower-priority cleanups, performance, architectural adjustments.)\n"
        "\n"
        "### Verified safe modules\n"
        "(The parts of the diff that were attacked and stood up, and the categories found clean.)\n"
    )
    assert layout in arbitrate, "the arbitration report's Markdown layout changed"


# --- CHECKOUT: and BASE: in every dossier, on both flows --------------------------------------------

def test_every_run_dossier_names_its_checkout_and_base(gate):
    seen = run_all_phases(gate)
    for phase in PHASES:
        dossier, observed = seen[phase]
        checkout = line_value(dossier, "CHECKOUT: ")
        assert Path(checkout).is_absolute(), f"{phase}: the checkout path is not absolute: {checkout}"
        assert line_value(dossier, "BASE: ") == f"{BASE_REF} {gate['base']}", phase


def test_every_run_checkout_exists_at_delivery_detached_at_head_and_is_the_one_used(gate):
    seen = run_all_phases(gate)
    used = set()
    for phase in PHASES:
        dossier, observed = seen[phase]
        checkout = line_value(dossier, "CHECKOUT: ")
        assert observed["exists"] == "yes", f"{phase}: the advertised checkout did not exist at delivery"
        assert observed["advertised"] == observed["pwd"] == observed["checkout_arg"], \
            f"{phase}: the advertised checkout is not the one the agent ran in: {observed}"
        assert observed["advertised"] == str(Path(checkout).resolve())
        assert observed["head"] == gate["head"], f"{phase}: the checkout is not at the reviewed head"
        assert observed["detached"] == "yes", f"{phase}: the checkout is not detached"
        used.add(checkout)
        assert not Path(checkout).exists(), f"{phase}: the run left its checkout behind"
    assert len(used) == 3, "the phases shared one checkout"


def test_every_dossier_flow_dossier_names_its_checkout_and_base(gate):
    for phase in PHASES:
        dossier, checkout, _ = dossier_phase(gate, phase)
        text = dossier.read_text()
        assert line_value(text, "CHECKOUT: ") == str(checkout), \
            f"{phase}: the dossier's checkout is not the one the command printed"
        assert checkout.is_absolute(), checkout
        assert line_value(text, "BASE: ") == f"{BASE_REF} {gate['base']}", phase
        if phase == "arbitrate":
            assert "===== DIFF" not in text and "diff --git" not in text
        else:
            assert "diff --git a/app.py b/app.py" in text
        record_phase(gate, phase)
        cleanup = run_script("cleanup", str(checkout), "--repo", str(gate["repo"]), env=gate["env"])
        assert cleanup.returncode == 0, cleanup.stdout + cleanup.stderr
        assert not checkout.exists()


def test_every_dossier_flow_checkout_exists_detached_at_head_and_is_registered(gate):
    for phase in PHASES:
        _, checkout, _ = dossier_phase(gate, phase)
        assert checkout.is_dir(), f"{phase}: the advertised checkout does not exist"
        assert git(checkout, "rev-parse", "HEAD") == gate["head"], phase
        detached = subprocess.run(["git", "symbolic-ref", "-q", "HEAD"], cwd=checkout,
                                  capture_output=True)
        assert detached.returncode != 0, f"{phase}: the checkout is on a branch, not detached"
        assert str(checkout) in registry_lines(gate["repo"]), f"{phase}: the checkout is not registered"
        assert str(checkout) in registered_worktrees(gate["repo"])
        record_phase(gate, phase)


# --- a dossier that cannot be written leaves no checkout behind ------------------------------------

def failing_git_env(g: dict, args: str) -> dict[str, str]:
    """A git that fails (exit 3) when called with exactly `args` first, and is real git otherwise."""
    fakebin = g["tmp"] / "fakebin"
    fakebin.mkdir(exist_ok=True)
    wrapper = fakebin / "git"
    real_git = subprocess.run(["bash", "-c", "command -v git"], capture_output=True,
                              text=True, check=True).stdout.strip()
    first, second = args.split()
    wrapper.write_text(
        "#!/usr/bin/env bash\n"
        f'if [ "$1" = {first} ] && [ "$2" = {second} ]; then echo "{args} refused" >&2; exit 3; fi\n'
        f'exec "{real_git}" "$@"\n'
    )
    wrapper.chmod(0o755)
    return {**g["env"], "PATH": f"{fakebin}:{g['env']['PATH']}"}


def failing_diffstat_env(g: dict) -> dict[str, str]:
    """A git that fails the dossier's diffstat, so the dossier write fails after the checkout exists."""
    return failing_git_env(g, "diff --stat")


def assert_phase_never_started(g: dict, phase: str) -> None:
    """No launch, binding or primary fingerprint survives, and no partial dossier is left to mislead."""
    run_dir = artifact_paths(g)[phase].parent
    left = [name for name in (f"{phase}.launch", f"{phase}.binding", f"{phase}.primary")
            if (run_dir / name).exists()]
    assert left == [], f"the failed {phase} phase left {left} in {run_dir}"
    assert not list(g["scratch"].rglob(f"{phase}-dossier.md")), f"a partial {phase} dossier was left"


def assert_no_checkout_left(g: dict) -> None:
    assert registry_lines(g["repo"]) == [], "a checkout is still registered after the failed write"
    assert registered_worktrees(g["repo"]) == [str(g["repo"].resolve())], \
        "git still lists a throwaway worktree after the failed write"
    assert not list(g["scratch"].rglob("head-*")), "a checkout directory was left on disk"


def test_a_failed_dossier_write_on_run_removes_its_checkout(gate):
    env = {**failing_diffstat_env(gate), "PHASE_NAME": "sweep"}
    result = run_script("run", "sweep", *common(gate), "--agent-cmd", OBSERVER_AGENT, env=env)
    assert result.returncode != 0, result.stdout + result.stderr
    assert not (gate["scratch"] / "seen-sweep").exists(), "the agent ran on a dossier that failed"
    assert "could not write the sweep dossier" in result.stderr, result.stderr
    assert_no_checkout_left(gate)
    assert_phase_never_started(gate, "sweep")
    assert not Path(f"{artifact_paths(gate)['sweep']}.stamp").exists()


def test_a_failed_dossier_write_on_the_dossier_command_removes_its_checkout(gate):
    result = run_script("dossier", "sweep", *common(gate), env=failing_diffstat_env(gate))
    assert result.returncode != 0, result.stdout + result.stderr
    assert "could not write the sweep dossier" in result.stderr, result.stderr
    assert_no_checkout_left(gate)
    record = run_script("record", "sweep", "--repo", str(gate["repo"]), "--base", BASE_REF,
                        "--spec", str(gate["spec"]), env=gate["env"])
    assert record.returncode != 0, "a failed dossier write left a launch that record could accept"
    assert_phase_never_started(gate, "sweep")


def test_a_failed_checkout_on_the_dossier_command_leaves_no_launch(gate):
    result = run_script("dossier", "sweep", *common(gate), env=failing_git_env(gate, "worktree add"))
    assert result.returncode != 0, result.stdout + result.stderr
    assert "could not create the throwaway checkout" in result.stderr, result.stderr
    assert_no_checkout_left(gate)
    assert_phase_never_started(gate, "sweep")


def test_a_checkout_that_cannot_be_registered_is_never_advertised(gate):
    """A checkout 'cleanup' would refuse (not in the registry) is removed, and the dossier fails."""
    registry = Path(git(gate["repo"], "rev-parse", "--path-format=absolute", "--git-path",
                        "adversarial-pipeline")) / "checkouts.registry"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.mkdir()  # the append to the registry fails
    result = run_script("dossier", "sweep", *common(gate), env=gate["env"])
    assert result.returncode != 0, result.stdout + result.stderr
    assert "CHECKOUT: " not in result.stderr, result.stderr
    assert registered_worktrees(gate["repo"]) == [str(gate["repo"].resolve())], \
        "an unregistered throwaway worktree was left behind"
    assert not list(gate["scratch"].rglob("head-*")), "a checkout directory was left on disk"
    assert_phase_never_started(gate, "sweep")


def test_a_dossier_path_that_cannot_be_delivered_leaves_no_checkout(gate):
    """With stdout closed the caller never learns the dossier path, so nothing may be left behind."""
    result = subprocess.run(
        ["bash", "-c", 'exec >&-; exec bash "$0" "$@"', str(SCRIPT), "dossier", "sweep", *common(gate)],
        capture_output=False, stderr=subprocess.PIPE, text=True, env=gate["env"], cwd=str(ROOT),
        timeout=120,
    )
    assert result.returncode != 0, result.stderr
    assert_no_checkout_left(gate)
    assert_phase_never_started(gate, "sweep")


def test_the_run_header_names_the_first_markers_as_authoritative(gate):
    """A spec or phase report may quote marker lines; the header says which ones count."""
    gate["spec"].write_text("Story text quoting a marker:\nCHECKOUT: /elsewhere\n")
    dossier, checkout, _ = dossier_phase(gate, "sweep")
    text = dossier.read_text()
    header = next(line for line in text.splitlines() if line.startswith("===== RUN"))
    assert "first" in header and "CHECKOUT:" in header, header
    first = next(line for line in text.splitlines() if line.startswith("CHECKOUT: "))
    assert first == f"CHECKOUT: {checkout}", first


# --- SKILL.md no longer claims every dossier holds the whole diff ----------------------------------

def skill_text() -> str:
    return SKILL_MD.read_text()


def test_the_skill_description_and_roles_table_make_no_whole_diff_claim():
    text = skill_text()
    assert "whole-diff" not in text, "the description still promises a whole-diff sweep"
    sweep_row = next(line for line in text.splitlines() if line.startswith("| 1 Sweep |"))
    assert "whole diff" not in sweep_row, sweep_row
    assert "diffstat" in sweep_row, sweep_row
    arbitrate_row = next(line for line in text.splitlines() if line.startswith("| 3 Arbitrate |"))
    assert "checkout" in arbitrate_row, arbitrate_row


def test_the_subagent_flow_uses_the_checkout_the_dossier_command_creates():
    text = skill_text()
    flow = text[text.index("- A subagent runtime"):text.index("Never put the dossier's contents in argv")]
    assert "checkout --base" not in flow, "the subagent flow still makes a separate checkout"
    assert "CHECKOUT: " in flow and "stderr" in flow, flow
    assert "cleanup" in flow, flow
    assert "read-only" in flow, flow


def test_the_argv_rule_is_justified_by_the_dossiers_that_still_embed_a_diff():
    text = skill_text()
    rule = next(line for line in text.splitlines()
                if line.startswith("Never put the dossier's contents in argv"))
    assert "128 KiB" in rule
    assert "sweep" in rule and "hunt" in rule, rule
    assert "a real diff exceeds" not in rule, rule
