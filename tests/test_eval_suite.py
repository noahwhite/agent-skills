"""SKL-164: the story-to-done eval suite runner and the case contract."""

import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "skills" / "story-to-done" / "evals"
REFERENCE_CASE = EVALS / "qa-unfinished-own-steps"
HARNESS_FILES = ("run-suite.sh", "suite.py")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "agent-skills@example.com")
    git(repo, "config", "user.name", "agent-skills")
    git(repo, "config", "commit.gpgsign", "false")  # an inherited signing config must not break the fixture


def commit_all(repo: Path) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "fixture")
    return git(repo, "rev-parse", "--short=7", "HEAD")


# The stub case: its run.sh hands the scenario and run directory to EVAL_AGENT_CMD and grades
# what the stub agent recorded, so the agent's exit status decides pass (0), graded fail (1)
# or void (2), the same contract the real case's run.sh keeps.
STUB_RUN = r"""#!/usr/bin/env bash
set -euo pipefail
checkout="$1"; scenario="$2"; run="$3"
mkdir -p "$run"
status=0
$EVAL_AGENT_CMD "$checkout" "$scenario" "$run" || status=$?
if [ "$status" -ne 0 ]; then
  echo "HARNESS: the agent command exited $status; nothing was graded." >&2
  exit 2
fi
python3 "$(dirname "$0")/grader.py" "$run" | tee "$run/grader-output.txt"
"""

STUB_GRADER = r"""#!/usr/bin/env python3
import json, pathlib, sys
run = pathlib.Path(sys.argv[1])
calls = [json.loads(line) for line in (run / "actions.jsonl").read_text().splitlines()]
ok = calls and calls[-1]["action"] == "pass"
print("ok   the recorded call" if ok else "FAIL the recorded call")
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
"""

# The stub agent: pass and fail record one call; void-once is void on its first attempt only;
# void-always is void every time. It writes its run directory into the call, so the record shows
# whether the runner normalised the path.
STUB_AGENT = r"""#!/usr/bin/env bash
set -euo pipefail
checkout="$1"; scenario="$2"; run="$3"
state="$STUB_STATE/$scenario"
count=$(( $(cat "$state" 2>/dev/null || echo 0) + 1 ))
echo "$count" > "$state"
echo "$run" >> "$STUB_STATE/run-dirs"
case "$scenario" in
  pass) action=pass ;;
  fail) action=stop ;;
  void-once) [ "$count" -gt 1 ] || exit 3; action=pass ;;
  void-always) exit 3 ;;
esac
printf '{"action": "%s", "run_dir": "%s", "id": "00000000-1111-2222-3333-444444444444"}\n' "$action" "$run" > "$run/actions.jsonl"
"""

STUB_SCENARIOS = ("pass", "fail", "void-once", "void-always")


def stub_case(case_dir: Path, scenarios=STUB_SCENARIOS) -> None:
    (case_dir / "results").mkdir(parents=True)
    (case_dir / "results" / ".keep").write_text("")
    for name in scenarios:
        (case_dir / "scenarios" / name).mkdir(parents=True)
        (case_dir / "scenarios" / name / "scenario.md").write_text(f"{name}\n")
    reference = yaml.safe_load((REFERENCE_CASE / "case.yaml").read_text())
    case = {key: reference[key] for key in reference}
    case.update(case=case_dir.name, kind="discriminating",
                runtime={"command": "stub", "model": "stub/model-1", "reasoning_effort": "low"},
                scenarios=[{"name": name, "expectation": name, "baseline": "-", "candidate": "-",
                            **({"control": "a control"} if name == "fail" else {})} for name in scenarios])
    (case_dir / "case.yaml").write_text(yaml.safe_dump(case, sort_keys=False))
    (case_dir / "prompt.md").write_text("stub prompt\n")
    for name, text in (("run.sh", STUB_RUN), ("grader.py", STUB_GRADER)):
        (case_dir / name).write_text(text)
        (case_dir / name).chmod(0o755)


@pytest.fixture
def suite(tmp_path: Path):
    """A temporary harness checkout holding the runner and the stub case, a separate skill
    checkout, and the stub agent, so the test never writes into this repository."""
    harness = tmp_path / "harness"
    evals = harness / "skills" / "story-to-done" / "evals"
    evals.mkdir(parents=True)
    init_repo(harness)
    for name in HARNESS_FILES:
        shutil.copy2(EVALS / name, evals / name)
    stub_case(evals / "stub")
    harness_sha = commit_all(harness)

    checkout = tmp_path / "checkout"
    init_repo(checkout)
    # A case that exists only in CHECKOUT: the runner must never list it.
    stub_case(checkout / "skills" / "story-to-done" / "evals" / "checkout-only", scenarios=("pass",))
    checkout_sha = commit_all(checkout)

    agent = tmp_path / "agent"
    agent.write_text(STUB_AGENT)
    agent.chmod(0o755)
    state = tmp_path / "state"
    state.mkdir()
    env = {**os.environ, "EVAL_AGENT_CMD": str(agent), "STUB_STATE": str(state), "TMPDIR": str(tmp_path)}

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["bash", str(evals / "run-suite.sh"), *args], capture_output=True, text=True, env=env)

    return {"run": run, "evals": evals, "harness": harness, "checkout": checkout, "state": state,
            "harness_sha": harness_sha, "checkout_sha": checkout_sha}


def summary_rows(text: str) -> dict[str, list[str]]:
    rows = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("|") and cells[0] in STUB_SCENARIOS:
            rows[cells[0]] = cells
    return rows


def test_the_runner_counts_pass_fail_void_and_exhausted_void_retries(suite) -> None:
    result = suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1, "a scenario short of N graded runs fails the suite\n" + result.stderr

    summary = (suite["evals"] / "results" / "suite-lab-1.md").read_text()
    assert "k/n × (1 - k/n)" in summary, "the summary states the variance formula"
    rows = summary_rows(summary)
    header = next(line for line in summary.splitlines() if line.startswith("| Scenario"))
    columns = [cell.strip() for cell in header.strip().strip("|").split("|")]
    at = {name: columns.index(name) for name in ("n", "k", "Pass rate k/n", "Variance", "Voids", "Void reasons",
                                                 "Skill commit", "Harness commit", "Model", "Reasoning effort",
                                                 "Role")}

    def cell(scenario: str, column: str) -> str:
        return rows[scenario][at[column]]

    assert set(rows) == set(STUB_SCENARIOS)
    expected = {  # scenario: (n, k, pass rate, variance, voids)
        "pass": ("2", "2", "1.000", "0.000", "0"),
        "fail": ("2", "0", "0.000", "0.000", "0"),
        "void-once": ("2", "2", "1.000", "0.000", "1"),
        "void-always": ("0", "0", "n/a", "n/a", "4"),
    }
    for scenario, (n, k, rate, variance, voids) in expected.items():
        assert (cell(scenario, "n"), cell(scenario, "k"), cell(scenario, "Voids")) == (n, k, voids), scenario
        assert cell(scenario, "Pass rate k/n").endswith(rate), scenario
        assert cell(scenario, "Variance") == variance, scenario
        assert cell(scenario, "Skill commit") == suite["checkout_sha"]
        assert cell(scenario, "Harness commit") == suite["harness_sha"]
        assert cell(scenario, "Model") == "stub/model-1"
        assert cell(scenario, "Reasoning effort") == "low"
    assert cell("fail", "Role") == "control (regression pin)"
    assert cell("pass", "Role") == "discriminating"
    assert "the agent command exited 3" in cell("void-always", "Void reasons")
    assert cell("pass", "Void reasons") == "none"

    # Retries stop at 2×N attempts, and a void-once scenario needs exactly one retry.
    attempts = {name: int((suite["state"] / name).read_text()) for name in STUB_SCENARIOS}
    assert attempts == {"pass": 2, "fail": 2, "void-once": 3, "void-always": 4}
    assert "checkout-only" not in summary, "cases are listed from the harness checkout, never CHECKOUT"
    assert not (suite["state"] / "checkout-only").exists()


def test_every_attempt_writes_a_run_record_and_a_call_record_named_for_it(suite) -> None:
    suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1")
    results = suite["evals"] / "stub" / "results"
    sha, harness_sha = suite["checkout_sha"], suite["harness_sha"]
    expected = {f"lab-1-{scenario}-{sha}-harness-{harness_sha}-{attempt}{suffix}"
                for scenario, count in (("pass", 2), ("fail", 2), ("void-once", 3), ("void-always", 4))
                for attempt in range(1, count + 1) for suffix in (".json", "-calls.jsonl")}
    assert {path.name for path in results.iterdir()} - {".keep"} == expected

    void = json.loads((results / f"lab-1-void-once-{sha}-harness-{harness_sha}-1.json").read_text())
    assert void["outcome"] == "void" and "exited 3" in void["void_reason"]
    graded = json.loads((results / f"lab-1-void-once-{sha}-harness-{harness_sha}-2.json").read_text())
    assert graded["outcome"] == "pass" and graded["void_reason"] is None
    assert graded["grades"]["grader-output.txt"][-1] == "PASS"
    calls = (results / f"lab-1-pass-{sha}-harness-{harness_sha}-1-calls.jsonl").read_text()
    assert json.loads(calls)["action"] == "pass"


def test_run_directories_sit_outside_both_checkouts_and_never_reach_a_record(suite) -> None:
    suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", "stub")
    run_dirs = (suite["state"] / "run-dirs").read_text().split()
    assert run_dirs
    for run_dir in run_dirs:
        real = Path(run_dir).resolve()
        for checkout in (suite["harness"], suite["checkout"]):
            assert checkout.resolve() not in real.parents, run_dir
    for record in (suite["evals"] / "stub" / "results").iterdir():
        text = record.read_text()
        for run_dir in run_dirs:
            assert run_dir not in text, record.name
        assert "00000000-1111-2222-3333-444444444444" not in text, "a UUID shape is normalised"
    calls = next((suite["evals"] / "stub" / "results").glob("*-pass-*-calls.jsonl")).read_text()
    assert json.loads(calls)["run_dir"] == "{run_dir}"


def test_the_runner_refuses_to_overwrite_and_exits_2(suite) -> None:
    first = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", "stub")
    summary = suite["evals"] / "results" / "suite-lab-1.md"
    before = summary.read_text()
    again = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", "stub")
    assert first.returncode == 1 and again.returncode == 2, again.stderr
    assert summary.read_text() == before
    assert (suite["state"] / "pass").read_text().strip() == "1", "nothing ran before the refusal"

    summary.unlink()
    record_clash = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", "stub")
    assert record_clash.returncode == 2, "an existing run record is never overwritten"
    assert "exists" in record_clash.stderr


@pytest.mark.parametrize("args", [
    ["--runs", "0", "CHECKOUT", "lab"],
    ["CHECKOUT", "bad/label"],
    ["CHECKOUT", "lab", "no-such-case"],
    ["CHECKOUT", "lab", "checkout-only"],
    ["NOT-A-DIR", "lab"],
])
def test_the_runner_refuses_bad_arguments(suite, args) -> None:
    args = [str(suite["checkout"]) if arg == "CHECKOUT" else arg for arg in args]
    result = suite["run"](*args)
    assert result.returncode == 2, result.stderr
    assert not (suite["state"] / "pass").exists(), "nothing ran"


def test_a_run_with_every_scenario_graded_exits_0(suite) -> None:
    stub = suite["evals"] / "stub"
    shutil.rmtree(stub / "scenarios" / "void-always")
    case = yaml.safe_load((stub / "case.yaml").read_text())
    case["scenarios"] = [s for s in case["scenarios"] if s["name"] != "void-always"]
    (stub / "case.yaml").write_text(yaml.safe_dump(case, sort_keys=False))
    commit_all(suite["harness"])
    result = suite["run"]("--runs", "3", str(suite["checkout"]), "lab-3", "stub")
    assert result.returncode == 0, result.stderr


# --- AC3: the case contract -------------------------------------------------------------------

REQUIRED_FIELDS = set(yaml.safe_load((REFERENCE_CASE / "case.yaml").read_text())) | {"kind"}


def contract_errors(case_dir: Path, tracked_mode) -> list[str]:
    """Every way a case directory breaks the contract SKL-164 AC3 states."""
    errors = []
    try:
        case = yaml.safe_load((case_dir / "case.yaml").read_text())
    except (OSError, yaml.YAMLError) as error:
        return [f"case.yaml unreadable: {error}"]
    if not isinstance(case, dict):
        return ["case.yaml is not a mapping"]
    missing = REQUIRED_FIELDS - set(case)
    if missing:
        errors.append(f"case.yaml lacks {sorted(missing)}")
    if case.get("kind") not in ("discriminating", "regression-pin"):
        errors.append(f"kind is {case.get('kind')!r}")
    for name in ("prompt.md", "grader.py", "run.sh"):
        if not (case_dir / name).is_file():
            errors.append(f"no {name}")
    if (case_dir / "run.sh").is_file() and tracked_mode(case_dir / "run.sh") != "100755":
        errors.append("run.sh is not mode 100755")
    if not (case_dir / "results").is_dir():
        errors.append("no results/")
    for scenario in case.get("scenarios") or []:
        name = scenario.get("name") if isinstance(scenario, dict) else None
        if not name or not (case_dir / "scenarios" / name).is_dir():
            errors.append(f"no fixtures for scenario {name!r}")
    grader = (case_dir / "grader.py").read_text() if (case_dir / "grader.py").is_file() else ""
    if "actions.jsonl" not in grader:
        errors.append("the grader does not read the tool-call record actions.jsonl")
    if "agent-output" in grader:
        errors.append("the grader reads the agent's prose")
    return errors


def git_mode(path: Path) -> str:
    entry = git(ROOT, "ls-files", "-s", "--", str(path.relative_to(ROOT)))
    return entry.split()[0] if entry else "untracked"


def file_mode(path: Path) -> str:
    return "100755" if path.stat().st_mode & stat.S_IXUSR else "100644"


CASES = sorted(path.parent for path in EVALS.glob("*/case.yaml"))


def test_the_suite_has_cases() -> None:
    assert REFERENCE_CASE in CASES


@pytest.mark.parametrize("case_dir", CASES, ids=lambda path: path.name)
def test_every_case_directory_keeps_the_contract(case_dir: Path) -> None:
    assert contract_errors(case_dir, git_mode) == []


@pytest.mark.parametrize("breakage", [
    "no-kind", "bad-kind", "no-prompt", "no-grader", "no-run", "run-not-executable",
    "no-results", "no-fixture", "prose-grader", "missing-field",
])
def test_the_contract_check_catches_each_breakage(tmp_path: Path, breakage: str) -> None:
    case_dir = tmp_path / "case"
    stub_case(case_dir)
    assert contract_errors(case_dir, file_mode) == [], "the stub case keeps the contract"
    case = yaml.safe_load((case_dir / "case.yaml").read_text())
    if breakage == "no-kind":
        del case["kind"]
    elif breakage == "bad-kind":
        case["kind"] = "tabletop"
    elif breakage == "missing-field":
        del case["graded_on"]
    elif breakage == "no-prompt":
        (case_dir / "prompt.md").unlink()
    elif breakage == "no-grader":
        (case_dir / "grader.py").unlink()
    elif breakage == "no-run":
        (case_dir / "run.sh").unlink()
    elif breakage == "run-not-executable":
        (case_dir / "run.sh").chmod(0o644)
    elif breakage == "no-results":
        shutil.rmtree(case_dir / "results")
    elif breakage == "no-fixture":
        shutil.rmtree(case_dir / "scenarios" / "fail")
    elif breakage == "prose-grader":
        (case_dir / "grader.py").write_text("open('agent-output.txt').read()\n")
    (case_dir / "case.yaml").write_text(yaml.safe_dump(case, sort_keys=False))
    assert contract_errors(case_dir, file_mode) != []


def test_the_folded_case_is_discriminating_on_skl_159s_merge_commit() -> None:
    case = yaml.safe_load((REFERENCE_CASE / "case.yaml").read_text())
    assert case["kind"] == "discriminating"
    assert case["baseline"]["commit"] == "7a6cb17"
    assert case["candidate"]["commit"] == "4f0eb79"
    assert re.search(r"SKL-164 owns the suite harness, the README and the repeat-run machinery", case["split"])
