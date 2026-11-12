"""SKL-164: the story-to-done eval suite runner and the case contract."""

import importlib.util
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
# The repository files the runner needs besides its own: it normalises records against the
# leak scan's patterns.
SUPPORT_FILES = ("scripts/leak_scan.py", "scripts/leak-patterns.txt")

_spec = importlib.util.spec_from_file_location("eval_suite", EVALS / "suite.py")
SUITE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SUITE)


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
# or void (2), the same contract the real case's run.sh keeps. The broken scenario exits 5,
# a status the contract does not define, and two-grades writes a second, failing grade.
# late-fail grades PASS and then fails a later check; both-pass writes two passing grades and
# still exits 1, so its grades contradict its status.
STUB_RUN = r"""#!/usr/bin/env bash
set -euo pipefail
checkout="$1"; scenario="$2"; run="$3"
mkdir -p "$run"
if [ "$scenario" = broken ]; then
  echo "run.sh: the stub is broken on purpose" >&2
  exit 5
fi
status=0
$EVAL_AGENT_CMD "$checkout" "$scenario" "$run" || status=$?
if [ "$status" -ne 0 ]; then
  echo "agent noise that is no reason" >&2
  echo "HARNESS: the agent command exited $status; nothing was graded." >&2
  exit 2
fi
if [ "$scenario" = two-grades ] || [ "$scenario" = further-only ]; then
  printf 'FAIL the further check\nFAIL\n' > "$run/grader-extra-output.txt"
fi
if [ "$scenario" = both-pass ]; then
  printf 'ok   the further check\nPASS\n' > "$run/grader-extra-output.txt"
fi
if [ "$scenario" = further-only ]; then
  exit 1
fi
python3 "$(dirname "$0")/grader.py" "$run" | tee "$run/grader-output.txt"
# Like the real case's new-round, a failing further grade fails the run's exit status.
case "$scenario" in
  two-grades|late-fail|both-pass) exit 1 ;;
esac
"""

STUB_GRADER = r"""#!/usr/bin/env python3
import json, pathlib, sys
run = pathlib.Path(sys.argv[1])
NESTED = "nested/kept.md"
calls = [json.loads(line) for line in (run / "actions.jsonl").read_text(errors="replace").splitlines()]
ok = calls and calls[-1]["action"] == "pass" and (run / "evidence.json").is_file()
print("ok   the recorded call" if ok else "FAIL the recorded call")
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
"""

# The stub agent: pass and fail record one call; void-once is void on its first attempt only,
# void-thrice on its first three; void-always is void every time; hang outlives any deadline;
# bad-bytes records a byte that is not UTF-8; dirty-once changes CHECKOUT on its first attempt
# and is void, as a real run.sh voids an agent that changed it. It writes its run directory into
# the call, so the record shows whether the runner normalised the path, and the CANARY or EVAL_CANARY variable
# into evidence.json, so the record shows what environment it got. EVAL_AGENT_CMD passes
# --model MODEL first, as a real agent command names its model.
STUB_AGENT = r"""#!/usr/bin/env bash
set -euo pipefail
shift 2
checkout="$1"; scenario="$2"; run="$3"
state="$STUB_STATE/$scenario"
count=$(( $(cat "$state" 2>/dev/null || echo 0) + 1 ))
echo "$count" > "$state"
echo "$run" >> "$STUB_STATE/run-dirs"
case "$scenario" in
  pass|two-grades|further-only|late-fail|both-pass) action=pass ;;
  fail) action=stop ;;
  void-once) [ "$count" -gt 1 ] || exit 3; action=pass ;;
  void-thrice) [ "$count" -gt 3 ] || exit 3; action=pass ;;
  void-always) exit 3 ;;
  hang) sleep 30; action=pass ;;
  bad-bytes) action=pass ;;
  dirty-once) [ "$count" -gt 1 ] || { echo dirt > "$checkout/dirt.txt"; exit 3; }; action=pass ;;
esac
printf '{"action": "%s", "run_dir": "%s", "id": "%s"}\n' "$action" "$run" "$STUB_UUID" > "$run/actions.jsonl"
if [ "$scenario" = bad-bytes ]; then printf '\xff\n' >> "$run/actions.jsonl"; fi
printf '{"seen_in": "%s", "canary": "%s"}\n' "$run" "${CANARY-${EVAL_CANARY-unset}}" > "$run/evidence.json"
mkdir -p "$run/nested"
echo kept > "$run/nested/kept.md"
"""

STUB_SCENARIOS = ("pass", "fail", "void-once", "void-always")
# Built from parts so this file carries no UUID or address shape for the leak scan to flag.
STUB_UUID = "-".join(("0" * 8, "1" * 4, "2" * 4, "3" * 4, "4" * 12))
STUB_ADDRESS = "ops" + "@" + "corp.test"


def stub_case(case_dir: Path, scenarios=STUB_SCENARIOS) -> None:
    (case_dir / "results").mkdir(parents=True)
    (case_dir / "results" / ".keep").write_text("")
    for name in scenarios:
        (case_dir / "scenarios" / name).mkdir(parents=True, exist_ok=True)
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


def set_scenarios(case_dir: Path, scenarios) -> None:
    shutil.rmtree(case_dir)
    stub_case(case_dir, scenarios)


@pytest.fixture
def suite(tmp_path: Path):
    """A temporary harness checkout holding the runner and the stub case, a separate skill
    checkout, and the stub agent, so the test never writes into this repository."""
    harness = tmp_path / "harness"
    evals = harness / "skills" / "story-to-done" / "evals"
    evals.mkdir(parents=True)
    init_repo(harness)
    for path in [*EVALS.glob("*.py"), *EVALS.glob("*.sh")]:
        shutil.copy2(path, evals / path.name)
    for name in SUPPORT_FILES:
        (harness / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, harness / name)
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
    env = {**os.environ, "EVAL_AGENT_CMD": f"{agent} --model stub/agent-model#high", "STUB_STATE": str(state),
           "STUB_UUID": STUB_UUID, "EVAL_PASS_ENV": "STUB_STATE STUB_UUID", "TMPDIR": str(tmp_path)}
    # CI's private leak patterns must not redact the stub's own strings.
    for name in ("EVAL_TIMEOUT", "EVAL_GRADING_MARGIN", "LEAK_DENYLIST", "LEAK_DENYLIST_FILE", "CANARY", "EVAL_CANARY"):
        env.pop(name, None)

    def run(*args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["bash", str(evals / "run-suite.sh"), *args], capture_output=True, text=True,
                              env={**env, **extra})

    def recommit(*scenarios: str) -> str:
        set_scenarios(evals / "stub", scenarios)
        return commit_all(harness)

    return {"run": run, "evals": evals, "harness": harness, "checkout": checkout, "state": state,
            "harness_sha": harness_sha, "checkout_sha": checkout_sha, "env": env, "recommit": recommit}


def summary_rows(text: str) -> dict[str, list[str]]:
    rows = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("|") and cells[0] not in ("Scenario", "---"):
            rows[cells[0]] = cells
    return rows


def columns(text: str) -> dict[str, int]:
    header = next(line for line in text.splitlines() if line.startswith("| Scenario"))
    names = [cell.strip() for cell in header.strip().strip("|").split("|")]
    return {name: index for index, name in enumerate(names)}


def test_the_runner_counts_pass_fail_void_and_exhausted_void_retries(suite) -> None:
    result = suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1, "a scenario short of N graded runs fails the suite\n" + result.stderr

    summary = (suite["evals"] / "results" / "suite-lab-1.md").read_text()
    assert "k/n × (1 - k/n)" in summary, "the summary states the variance formula"
    assert "Scenarios short of N graded runs: stub void-always." in summary
    rows, at = summary_rows(summary), columns(summary)

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
        assert cell(scenario, "Model") == "stub/agent-model", "the model is the one the agent command names"
        assert cell(scenario, "Reasoning effort") == "high", "the effort is the model's #variant"
    assert cell("fail", "Role") == "control (regression pin)"
    assert cell("pass", "Role") == "discriminating"
    for attempt in range(1, 5):
        assert f"attempt {attempt}: run.sh exited 2: void" in cell("void-always", "Void reasons")
    assert "noise" not in summary and "HARNESS" not in summary, "a void reason is classified, never run.sh's text"
    assert "HARNESS: the agent command exited 3" in result.stderr, "the operator sees run.sh's stated reason"
    assert "noise" not in result.stderr
    assert cell("pass", "Void reasons") == "none"

    # Retries stop at 2×N attempts, and a void-once scenario needs exactly one retry.
    attempts = {name: int((suite["state"] / name).read_text()) for name in STUB_SCENARIOS}
    assert attempts == {"pass": 2, "fail": 2, "void-once": 3, "void-always": 4}
    assert "checkout-only" not in summary, "cases are listed from the harness checkout, never CHECKOUT"
    assert not (suite["state"] / "checkout-only").exists()


def test_a_graded_run_on_the_last_allowed_attempt_counts(suite) -> None:
    suite["recommit"]("void-thrice")
    result = suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1, result.stderr
    rows = summary_rows((suite["evals"] / "results" / "suite-lab-1.md").read_text())
    assert rows["void-thrice"][6:8] == ["1", "1"], "attempt 4 of 2×2 is graded and counted"
    assert int((suite["state"] / "void-thrice").read_text()) == 4


def test_every_attempt_writes_a_run_record_and_a_call_record_named_for_it(suite) -> None:
    suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1")
    results = suite["evals"] / "stub" / "results"
    sha, harness_sha = suite["checkout_sha"], suite["harness_sha"]
    expected = {f"lab-1-{scenario}-{sha}-harness-{harness_sha}-{attempt}{suffix}"
                for scenario, count in (("pass", 2), ("fail", 2), ("void-once", 3), ("void-always", 4))
                for attempt in range(1, count + 1) for suffix in (".json", "-calls.jsonl")}
    assert {path.name for path in results.iterdir()} - {".keep"} == expected

    void = json.loads((results / f"lab-1-void-once-{sha}-harness-{harness_sha}-1.json").read_text())
    assert void["outcome"] == "void" and void["void_reason"] == "run.sh exited 2: void"
    assert void["calls_record"] == "absent", "a void attempt that recorded no calls says so"
    graded = json.loads((results / f"lab-1-void-once-{sha}-harness-{harness_sha}-2.json").read_text())
    assert graded["outcome"] == "pass" and graded["void_reason"] is None
    assert graded["grades"]["grader-output.txt"][-1] == "PASS"
    assert graded["verdicts"] == {"void-once": "pass"}
    assert graded["model"] == "stub/agent-model" and graded["reasoning_effort"] == "high"
    assert graded["agent_command"] == "{tmpdir}/agent --model stub/agent-model#high"
    assert json.loads(graded["grader_inputs"]["evidence.json"]) == {"seen_in": "{run_dir}", "canary": "unset"}, \
        "a run-directory file the grader names is kept with the record"
    assert graded["grader_inputs"]["nested/kept.md"] == "kept\n", "a relative path the grader names is kept too"
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
        assert STUB_UUID not in text, "a UUID shape is normalised"
    calls = next((suite["evals"] / "stub" / "results").glob("*-pass-*-calls.jsonl")).read_text()
    assert json.loads(calls)["run_dir"] == "{run_dir}"


def test_the_normaliser_rewrites_paths_and_leak_shapes_and_keeps_the_rest() -> None:
    normalise = SUITE.Normaliser(SUITE.leak_patterns(), ["sk-passed-credential", "short"],
                                 run_dir=Path("/scratch/run-1"), home=Path("/home/u"))
    text = (f"/scratch/run-1/a.json /home/u/x /home/u2/y /srv/home/u/z /opt/demo/local {STUB_ADDRESS} "
            "https://github.com/a/b skills/story-to-done {run_dir}/kept key=sk-passed-credential short")
    assert normalise(text) == ("{run_dir}/a.json {home}/x {path} {path} {path} {redacted} "
                               "https://github.com/a/b skills/story-to-done {run_dir}/kept key={redacted} short")


def test_a_record_with_bytes_that_are_not_utf8_is_still_written(suite) -> None:
    suite["recommit"]("bad-bytes")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1")
    assert result.returncode == 0, result.stderr
    calls = next((suite["evals"] / "stub" / "results").glob("*-bad-bytes-*-calls.jsonl")).read_text()
    assert "�" in calls


def test_a_scenario_graded_twice_reports_each_grade(suite) -> None:
    suite["recommit"]("two-grades")
    result = suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1")
    assert result.returncode == 0, result.stderr
    summary = (suite["evals"] / "results" / "suite-lab-1.md").read_text()
    rows, at = summary_rows(summary), columns(summary)
    assert rows["two-grades"][at["k"]] == "2", "the scenario's own grade counts its own verdict"
    assert rows["two-grades-extra"][at["k"]] == "0" and rows["two-grades-extra"][at["n"]] == "2"
    assert rows["two-grades-extra"][at["Role"]] == "discriminating (further grade of two-grades)"


def test_a_further_grade_without_the_scenarios_own_grade_stops_the_suite(suite) -> None:
    suite["recommit"]("further-only")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1 and "no own verdict" in result.stderr, result.stderr
    record = json.loads(next((suite["evals"] / "stub" / "results").glob("*-further-only-*.json")).read_text())
    assert record["outcome"] == "error" and record["verdicts"] == {}


def test_a_single_grade_follows_the_exit_status(suite) -> None:
    suite["recommit"]("late-fail")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1")
    assert result.returncode == 0, result.stderr
    summary = (suite["evals"] / "results" / "suite-lab-1.md").read_text()
    rows, at = summary_rows(summary), columns(summary)
    assert rows["late-fail"][at["n"]] == "1" and rows["late-fail"][at["k"]] == "0"
    record = json.loads(next((suite["evals"] / "stub" / "results").glob("*-late-fail-*.json")).read_text())
    assert record["outcome"] == "fail" and record["verdicts"] == {"late-fail": "fail"}


def test_grades_that_contradict_the_exit_status_stop_the_suite(suite) -> None:
    suite["recommit"]("both-pass")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1 and "contradict" in result.stderr, result.stderr
    record = json.loads(next((suite["evals"] / "stub" / "results").glob("*-both-pass-*.json")).read_text())
    assert record["outcome"] == "error" and record["verdicts"] == {}


def test_an_attempt_that_changes_a_checkout_stops_the_suite(suite) -> None:
    suite["recommit"]("dirty-once")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1 and "after an attempt of this run changed it" in result.stderr, result.stderr
    assert int((suite["state"] / "dirty-once").read_text()) == 1, "no attempt runs against the changed checkout"
    assert not (suite["evals"] / "results" / "suite-lab-1.md").exists()


@pytest.mark.parametrize("name", ["CANARY", "EVAL_CANARY"])
def test_the_agent_gets_only_the_base_environment_and_the_variables_passed(suite, name) -> None:
    suite["recommit"]("pass")
    canary = "fake-canary-credential"
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", **{name: canary})
    assert result.returncode == 0, result.stderr
    passed = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-2", **{name: canary},
                          EVAL_PASS_ENV=f"STUB_STATE STUB_UUID {name}")
    assert passed.returncode == 0, passed.stderr
    results = suite["evals"] / "stub" / "results"
    for label, seen in (("lab-1", "unset"), ("lab-2", "{redacted}")):
        record = json.loads(next(results.glob(f"{label}-pass-*.json")).read_text())
        assert json.loads(record["grader_inputs"]["evidence.json"])["canary"] == seen, label
    assert all(canary not in path.read_text() for path in results.iterdir())


def test_the_recorded_model_is_normalised(suite) -> None:
    suite["recommit"]("pass")
    agent = suite["env"]["EVAL_AGENT_CMD"].split()[0]
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1",
                          EVAL_AGENT_CMD=f"{agent} --model {STUB_ADDRESS}/m#high")
    assert result.returncode == 0, result.stderr
    record = json.loads(next((suite["evals"] / "stub" / "results").glob("lab-1-pass-*.json")).read_text())
    assert STUB_ADDRESS not in record["model"] and "{redacted}" in record["model"]
    assert STUB_ADDRESS not in (suite["evals"] / "results" / "suite-lab-1.md").read_text()


def test_an_attempt_past_its_deadline_is_void(suite) -> None:
    suite["recommit"]("hang")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", EVAL_TIMEOUT="1", EVAL_GRADING_MARGIN="1")
    assert result.returncode == 1, result.stderr
    rows = summary_rows((suite["evals"] / "results" / "suite-lab-1.md").read_text())
    assert rows["hang"][6] == "0" and rows["hang"][10] == "2"
    assert "did not finish within 2 seconds" in rows["hang"][11]


def test_an_undefined_exit_status_stops_the_suite(suite) -> None:
    suite["recommit"]("broken", "pass")
    result = suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1 and "a status the case contract does not define" in result.stderr, result.stderr
    records = list((suite["evals"] / "stub" / "results").glob("*-broken-*.json"))
    assert len(records) == 1, "the broken attempt is recorded once and never retried"
    assert json.loads(records[0].read_text())["outcome"] == "error"
    assert not (suite["state"] / "pass").exists(), "nothing runs after a broken attempt"
    assert not (suite["evals"] / "results" / "suite-lab-1.md").exists()


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


def test_resume_continues_an_interrupted_run_from_its_records(suite) -> None:
    first = suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1", "stub")
    summary = suite["evals"] / "results" / "suite-lab-1.md"
    before = summary.read_text()
    summary.unlink()  # as if the run had stopped before its summary
    records = sorted(path.name for path in (suite["evals"] / "stub" / "results").iterdir())
    resumed = suite["run"]("--runs", "2", "--resume", str(suite["checkout"]), "lab-1", "stub")
    assert (first.returncode, resumed.returncode) == (1, 1), resumed.stderr
    assert summary.read_text() == before, "the resumed summary counts the existing records"
    assert sorted(path.name for path in (suite["evals"] / "stub" / "results").iterdir()) == records
    assert int((suite["state"] / "pass").read_text()) == 2, "no attempt with a record runs again"


@pytest.mark.parametrize("change", ["model", "broken"])
def test_resume_refuses_records_it_cannot_count(suite, change: str) -> None:
    suite["recommit"]("pass")
    suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1")
    (suite["evals"] / "results" / "suite-lab-1.md").unlink()
    extra = {}
    if change == "model":
        extra["EVAL_AGENT_CMD"] = suite["env"]["EVAL_AGENT_CMD"].replace("agent-model", "other-model")
    else:
        record_path = next((suite["evals"] / "stub" / "results").glob("lab-1-pass-*-1.json"))
        record = json.loads(record_path.read_text())
        record_path.write_text(json.dumps({**record, "outcome": "error"}))
    resumed = suite["run"]("--runs", "2", "--resume", str(suite["checkout"]), "lab-1", **extra)
    assert resumed.returncode == 2, resumed.stderr
    assert int((suite["state"] / "pass").read_text()) == 2, "nothing ran"


@pytest.mark.parametrize("args", [
    ["--runs", "0", "CHECKOUT", "lab"],
    ["CHECKOUT", "bad/label"],
    ["CHECKOUT", "lab", "no-such-case"],
    ["CHECKOUT", "lab", "checkout-only"],
    ["CHECKOUT", "lab", "stub", "stub"],
    ["NOT-A-DIR", "lab"],
])
def test_the_runner_refuses_bad_arguments(suite, args) -> None:
    args = [str(suite["checkout"]) if arg == "CHECKOUT" else arg for arg in args]
    result = suite["run"](*args)
    assert result.returncode == 2, result.stderr
    assert not (suite["state"] / "pass").exists(), "nothing ran"


@pytest.mark.parametrize("command", ["/bin/true", ""])
def test_an_agent_command_that_names_no_model_is_refused(suite, command: str) -> None:
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab", EVAL_AGENT_CMD=command)
    assert result.returncode == 2 and "--model" in result.stderr, result.stderr
    assert not (suite["state"] / "pass").exists(), "nothing ran"


@pytest.mark.parametrize("setting", [{"EVAL_TIMEOUT": "abc"}, {"EVAL_GRADING_MARGIN": "-5"},
                                     {"EVAL_PASS_ENV": "NOT-A-NAME"}])
def test_bad_settings_are_refused(suite, setting: dict) -> None:
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab", **setting)
    assert result.returncode == 2 and "Traceback" not in result.stderr, result.stderr
    assert not (suite["state"] / "pass").exists(), "nothing ran"


def test_a_case_naming_a_scenario_twice_is_refused(suite) -> None:
    suite["recommit"]("pass", "pass")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab")
    assert result.returncode == 2 and "more than once" in result.stderr, result.stderr


@pytest.mark.parametrize("path, expected", [
    ("skills/story-to-done/evals/results/suite-a.md", True),
    ("skills/story-to-done/evals/case/results/a.json", True),
    ("skills/story-to-done/results/a.md", False),
    ("skills/story-to-done/evals/case/results/deep/a.json", False),
    ("results/a.md", False),
])
def test_only_the_suites_own_outputs_count_as_records(path: str, expected: bool) -> None:
    assert SUITE.is_record(path) is expected


@pytest.mark.parametrize("change", ["tracked", "untracked"])
@pytest.mark.parametrize("where", ["harness", "checkout"])
def test_a_checkout_with_changes_is_refused(suite, where: str, change: str) -> None:
    repo = suite[where]
    if change == "tracked":
        (repo / "skills" / "story-to-done" / "evals" / ("stub" if where == "harness" else "checkout-only")
         / "prompt.md").write_text("changed\n")
    else:
        (repo / "skills" / "story-to-done" / "new-file.md").write_text("new\n")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab")
    assert result.returncode == 2 and "uncommitted changes" in result.stderr, result.stderr
    assert not (suite["state"] / "pass").exists(), "nothing ran"


def test_uncommitted_records_do_not_block_a_later_run(suite) -> None:
    suite["recommit"]("pass")
    assert suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1").returncode == 0
    assert git(suite["harness"], "status", "--porcelain", "--untracked-files=all"), "the records are untracked"
    second = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-2")
    assert second.returncode == 0, second.stderr


def test_a_run_directory_inside_a_checkout_is_refused(suite) -> None:
    inside = suite["checkout"] / ".git" / "scratch"
    inside.mkdir()
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab", TMPDIR=str(inside))
    assert result.returncode == 2 and "set TMPDIR outside both checkouts" in result.stderr, result.stderr
    assert not (suite["state"] / "pass").exists(), "nothing ran"


@pytest.mark.parametrize("scenarios", [None, []])
def test_a_case_without_scenarios_is_refused(suite, scenarios) -> None:
    case_file = suite["evals"] / "stub" / "case.yaml"
    case = yaml.safe_load(case_file.read_text())
    if scenarios is None:
        del case["scenarios"]
    else:
        case["scenarios"] = scenarios
    case_file.write_text(yaml.safe_dump(case, sort_keys=False))
    commit_all(suite["harness"])
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab")
    assert result.returncode == 2 and "names no scenarios" in result.stderr, result.stderr


def test_a_run_with_every_scenario_graded_exits_0(suite) -> None:
    suite["recommit"]("pass", "fail", "void-once")
    result = suite["run"]("--runs", "3", str(suite["checkout"]), "lab-3", "stub")
    assert result.returncode == 0, result.stderr


# --- AC3: the case contract -------------------------------------------------------------------

REQUIRED_FIELDS = set(yaml.safe_load((REFERENCE_CASE / "case.yaml").read_text())) | {"kind"}
# File names that hold the agent's prose rather than its tool calls: named for agent output, a
# transcript, a stream or a response, or a plain-text or log file, which no call record is.
PROSE = re.compile(r"(?i)agent[-_]?output|transcript|stdout|stderr|response|\.(?:txt|log)$")
# A file run.sh redirects command output into, such as the agent's output.
REDIRECT = re.compile(r'>\s*"?\$\{?run\}?/([^"\s;|&]+)')


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
    if (case_dir / "run.sh").is_file() and (mode := tracked_mode(case_dir / "run.sh")) != "100755":
        errors.append(f"run.sh is {mode}, not mode 100755")
    if not (case_dir / "results").is_dir():
        errors.append("no results/")
    scenarios = case.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        errors.append("case.yaml names no scenarios")
    for scenario in scenarios if isinstance(scenarios, list) else []:
        name = scenario.get("name") if isinstance(scenario, dict) else None
        if not name or not (case_dir / "scenarios" / name).is_dir():
            errors.append(f"no fixtures for scenario {name!r}")
    names = SUITE.grader_names(case_dir / "grader.py") if (case_dir / "grader.py").is_file() else set()
    if not any("actions.jsonl" in name for name in names):
        errors.append("the grader does not read the tool-call record actions.jsonl")
    # Only strings shaped as file names count, so a grader's own messages may say "transcript".
    files = {name for name in names if SUITE.RELATIVE_FILE.fullmatch(name)}
    written = set(REDIRECT.findall((case_dir / "run.sh").read_text())) if (case_dir / "run.sh").is_file() else set()
    prose = sorted(name for name in files if PROSE.search(name) or name in written)
    if prose:
        errors.append(f"the grader reads the agent's prose: {prose}")
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
    "no-results", "no-fixture", "prose-grader", "prose-beside-calls", "missing-field", "no-scenarios",
    "prose-stdout", "prose-log", "prose-response", "prose-redirected",
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
    elif breakage == "no-scenarios":
        case["scenarios"] = []
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
    elif breakage == "prose-beside-calls":
        (case_dir / "grader.py").write_text("open('actions.jsonl').read()\nopen('transcript.txt').read()\n")
    elif breakage.startswith("prose-") and breakage != "prose-grader":
        read = {"prose-stdout": "stdout.txt", "prose-log": "agent.log", "prose-response": "response.md",
                "prose-redirected": "said.md"}[breakage]
        (case_dir / "grader.py").write_text(f"open('actions.jsonl').read()\nopen('{read}').read()\n")
        with (case_dir / "run.sh").open("a") as run_sh:
            run_sh.write('echo said > "$run/said.md"\n')
    (case_dir / "case.yaml").write_text(yaml.safe_dump(case, sort_keys=False))
    assert contract_errors(case_dir, file_mode) != []


def test_a_grader_docstring_is_not_a_file_it_reads(tmp_path: Path) -> None:
    grader = tmp_path / "grader.py"
    grader.write_text('"""Never reads the transcript."""\nopen("actions.jsonl")\n')
    assert SUITE.grader_names(grader) == {"actions.jsonl"}


def test_a_grader_message_that_says_transcript_keeps_the_contract(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    stub_case(case_dir)
    (case_dir / "grader.py").write_text("open('actions.jsonl').read()\nprint('FAIL the transcript says nothing')\n")
    assert contract_errors(case_dir, file_mode) == []


def test_the_folded_case_is_discriminating_on_skl_159s_merge_commit() -> None:
    case = yaml.safe_load((REFERENCE_CASE / "case.yaml").read_text())
    assert case["kind"] == "discriminating"
    assert case["baseline"]["commit"] == "7a6cb17"
    assert case["candidate"]["commit"] == "4f0eb79"
    assert re.search(r"SKL-164 owns the suite harness, the README and the repeat-run machinery", case["split"])
