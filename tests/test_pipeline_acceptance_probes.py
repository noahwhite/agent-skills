"""The sweep and hunt dossiers make every acceptance rule a behavioural probe (SKL-404 AC9).

The gate's sweep and hunt phases must enumerate every explicitly stated behavioural rule in the
story's acceptance criteria and exercise each one against the reviewed head, reporting it PASSED or
FAILED, rather than judging it from the diff or the documentation alone. A rule the code asserts,
documents or claims but does not enforce is an enforcement finding at blocking severity, never a
low-severity documentation finding.

The prompt text the gate writes is the mechanism, so these tests read the dossiers the script writes
for both phases (on the `run` and the `dossier` flows) and assert the requirement, its escalation
severity, and its scope bound: the arbitrate dossier carries none of it.

Every test seeds a two-commit repository and reviews the head against its base commit, so the
dossiers carry a real diff.
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
BASE_REF = "base"
BLOCK = "===== ACCEPTANCE RULES ARE BEHAVIOURAL PROBES ====="
CRITERIA = "===== STORY / ACCEPTANCE CRITERIA"
AC1 = "AC1 Shard invocation, unsharded by default."

# Host git configuration and repository-locating variables never reach this module's fixture: a
# developer's signing, hooks or diff settings must not decide it, and an exported GIT_DIR or
# GIT_WORK_TREE must never redirect its commits into another repository.
GIT_ISOLATION = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
GIT_LOCATORS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
                "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_EXTERNAL_DIFF")


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("ADVERSARIAL_") and not k.startswith("GIT_CONFIG")
           and k not in GIT_LOCATORS}
    return {**env, **GIT_ISOLATION, **(extra or {})}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, env=clean_env(),
    ).stdout.strip()


def make_two_commit_repo(tmp_path: Path) -> Path:
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
        "def total(items):\n    return sum(i for i in items if i > 0)  # SKL404-HEAD-CHANGE\n"
    )
    git(repo, "add", "app.py")
    git(repo, "commit", "-qm", "head")
    return repo


def run_script(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=120,
    )


@pytest.fixture
def gate(tmp_path):
    repo = make_two_commit_repo(tmp_path)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    (tmp_path / "runtime-tmp").mkdir()
    env = clean_env({"TMPDIR": str(tmp_path / "runtime-tmp")})
    spec = tmp_path / "spec.md"
    spec.write_text(
        "Story SKL-404: shard the pre-PR hunt.\n\n"
        f"{AC1} `run hunt` accepts `--shard K/N`; `--shard 0/2` is a usage error at exit 2.\n"
    )
    preflight = run_script(
        "preflight", "--full-suite", "on", "--repo", str(repo), "--base", BASE_REF, "--test-cmd", "true",
        "--scratch", str(scratch), env=env,
    )
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    return {"repo": repo, "scratch": scratch, "env": env, "spec": spec, "tmp": tmp_path}


def common(g: dict) -> list[str]:
    return ["--repo", str(g["repo"]), "--base", BASE_REF, "--spec", str(g["spec"]),
            "--scratch", str(g["scratch"])]


# The fake agent snapshots the dossier it was handed, keyed by phase.
OBSERVER_AGENT = (
    's="$ADVERSARIAL_SESSION_SCRATCH/seen-$PHASE_NAME"; mkdir -p "$s"; '
    'cp {prompt_file} "$s/dossier.md"; '
    '{ printf "REVIEW-RAN: yes\\n"; echo "ok"; } > {output_file}'
)


def run_dossier(g: dict, phase: str) -> str:
    """The dossier text the `run <phase>` flow hands its agent."""
    env = {**g["env"], "PHASE_NAME": phase}
    result = run_script("run", phase, *common(g), "--agent-cmd", OBSERVER_AGENT, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    return (g["scratch"] / f"seen-{phase}" / "dossier.md").read_text()


PHASES = ("sweep", "hunt", "arbitrate")


def advance(g: dict, phase: str) -> None:
    """Run and accept every phase before `phase`: each later phase requires its predecessors."""
    for prior in PHASES[:PHASES.index(phase)]:
        run_dossier(g, prior)


def dossier_flow(g: dict, phase: str) -> tuple[str, str]:
    """The dossier text and its checkout path from the `dossier <phase>` flow."""
    advance(g, phase)
    result = run_script("dossier", phase, *common(g), env=g["env"])
    assert result.returncode == 0, result.stdout + result.stderr
    dossier = Path(result.stdout.strip().splitlines()[-1]).read_text()
    checkout = [line[len("CHECKOUT: "):] for line in result.stderr.splitlines()
                if line.startswith("CHECKOUT: ")][0]
    return dossier, checkout


def probe_block(dossier: str) -> str:
    """The probe block plus the phase's own sentence, whitespace-normalised."""
    assert BLOCK in dossier, f"the dossier has no {BLOCK!r} block"
    after = dossier.split(BLOCK, 1)[1]
    return " ".join(after.split("\n\n", 1)[0].split())


def sentences(text: str) -> list[str]:
    return [part for part in re.split(r"(?<=\.)\s+", text) if part]


# --- both phases carry the probe requirement -----------------------------------------------------

@pytest.mark.parametrize("phase", ["sweep", "hunt"])
def test_the_phase_dossier_makes_every_acceptance_rule_a_probe(gate, phase):
    advance(gate, phase)
    dossier = run_dossier(gate, phase)
    block = probe_block(dossier)
    # the criteria themselves are in the dossier, so there is something to enumerate
    assert AC1 in " ".join(dossier.split()), f"the {phase} dossier lost the acceptance criteria"
    # the block points at "the acceptance criteria below", so it must precede them
    assert dossier.index(BLOCK) < dossier.index(CRITERIA), \
        f"the {phase} probe block no longer precedes the criteria it refers to"
    assert "Every explicitly stated behavioural rule in the acceptance criteria" in block, block
    assert "each command, flag, argument, sequence, exit code, file name and state change" in block, block
    assert "exercise each one against the reviewed head by running the command or sequence the rule names" \
        in block, block
    assert "report it PASSED or FAILED with the command you ran and what you observed" in block, block
    assert "Never pass a rule from reading the diff or the documentation alone" in block, block
    # the report's probe line format is part of the requirement, in both phases
    assert "RULE <n> | PASSED or FAILED | the rule in one line | the command you ran | what you observed" \
        in " ".join(dossier.split()), f"the {phase} dossier lost its probe-line format"


@pytest.mark.parametrize("phase", ["sweep", "hunt"])
def test_a_documented_but_unenforced_rule_is_escalated_not_filed_as_documentation(gate, phase):
    advance(gate, phase)
    block = probe_block(run_dossier(gate, phase))
    assert "A rule the code asserts, documents or claims but does not enforce is an ENFORCEMENT finding" \
        in block, block
    assert "at blocking severity (High or Critical)" in block, block
    # the documentation route exists only as a prohibition
    mentioning = [s for s in sentences(block) if "documentation finding" in s or "documentation" in s]
    assert mentioning, f"the {phase} block says nothing about the documentation route: {block}"
    for sentence in mentioning:
        assert "never" in sentence.lower(), \
            f"the {phase} block allows a documentation finding: {sentence}"


def test_the_sweep_exercises_a_write_producing_rule_on_a_copy(gate):
    block = probe_block(run_dossier(gate, "sweep"))
    assert "Your checkout is read-only: change no file in it, but run every rule's command" in block, block
    assert "a copy of the reviewed checkout you make in your own directory under the session scratch directory" \
        in block, block
    assert "Report FAILED only for a rule the reviewed head fails" in block, block
    assert "when a rule cannot be exercised at all, say that separately with the reason" in block, block


def test_the_hunt_exercises_every_rule_in_its_throwaway_checkout(gate):
    advance(gate, "hunt")
    block = probe_block(run_dossier(gate, "hunt"))
    assert "Mutate and revert inside your throwaway checkout as needed to exercise each rule" in block, block
    assert "RULE <n> | PASSED or FAILED" in block, block


# --- the `dossier` flow writes the same prompt text ----------------------------------------------

@pytest.mark.parametrize("phase", ["sweep", "hunt"])
def test_the_dossier_flow_carries_the_probe_block(gate, phase):
    dossier, checkout = dossier_flow(gate, phase)
    assert "Every explicitly stated behavioural rule" in probe_block(dossier)
    assert "never a low-severity documentation finding" in probe_block(dossier)
    assert dossier.index(BLOCK) < dossier.index(CRITERIA)
    cleaned = run_script("cleanup", checkout, "--repo", str(gate["repo"]), env=gate["env"])
    assert cleaned.returncode == 0, cleaned.stdout + cleaned.stderr


# --- scope: the arbitrate dossier carries none of it ---------------------------------------------

def test_the_arbitrate_dossier_carries_no_probe_block(gate):
    advance(gate, "arbitrate")
    dossier = run_dossier(gate, "arbitrate")
    assert BLOCK not in dossier, "the arbitrate dossier carries the sweep-and-hunt probe block"
    assert "ENFORCEMENT finding" not in dossier
    # the arbitrate phase still receives both phase reports, so it still sees their answers
    assert "===== PHASE 1 (sweep candidates) =====" in dossier
    assert "===== PHASE 2 (empirical results) =====" in dossier


# --- the skill states the rule for both phases ---------------------------------------------------

def skill_sections() -> dict[str, str]:
    text = SKILL_MD.read_text()
    first = text.index("## Phase 1: sweep")
    second = text.index("## Phase 2: verify and hunt")
    third = text.index("## Phase 3: arbitration")
    return {"sweep": text[first:second], "hunt": text[second:third]}


@pytest.mark.parametrize("phase", ["sweep", "hunt"])
def test_the_skill_states_the_probe_rule_for_both_phases(phase):
    section = " ".join(skill_sections()[phase].split())
    assert "ACCEPTANCE RULES ARE BEHAVIOURAL PROBES" in section, \
        f"the {phase} section does not state the probe rule"
    # the obligation itself, not only the topic: enumerate, exercise by running, report PASSED or FAILED
    if phase == "sweep":
        assert "is enumerated and exercised against the reviewed head by running the command or" in section, section
        assert "reported PASSED or FAILED with the command and the observation" in section, section
    else:
        assert "exercises each one in its throwaway checkout with the command or sequence the rule names" \
            in section, section
        assert "reports each PASSED or FAILED with the command and the observation after its findings" \
            in section, section


def test_the_skill_states_the_enforcement_escalation():
    section = " ".join(skill_sections()["sweep"].split())
    assert "enforcement finding at blocking severity" in section, section
    assert "never a low-severity documentation finding" in section, section
