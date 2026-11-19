"""SKL-164, SKL-338: the shared eval suite runner (scripts/run-suite.sh) and the case contract."""

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
EVALS_PARTS = ("skills", "story-to-done", "evals")
# The one shared runner: its shell entry point and the module behind it.
RUNNER_FILES = ("scripts/run-suite.sh", "scripts/eval_suite.py")
# The repository files the runner needs besides its own: it normalises records against the
# leak scan's patterns.
SUPPORT_FILES = ("scripts/leak_scan.py", "scripts/leak-patterns.txt")

_spec = importlib.util.spec_from_file_location("eval_suite", ROOT / "scripts" / "eval_suite.py")
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
# still exits 1, so its grades contradict its status; two-pass writes two passing grades and exits 0.
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
if [ "$scenario" = both-pass ] || [ "$scenario" = two-pass ]; then
  printf 'ok   the further check\nPASS\n' > "$run/grader-extra-output.txt"
fi
if [ "$scenario" = extra-once ] && [ "${run##*-}" = 1 ]; then
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
# and is void, as a real run.sh voids an agent that changed it; record-once, mode-once and perm-once do
# the same to the committed record STUB_RECORD names, by its content, its executable bit or a
# permission git ignores, relink-once points that record's symlink at STUB_TARGET, and locked-once
# makes an unreadable record writable and overwrites it. It writes its run directory into
# the call, so the record shows whether the runner normalised the path, and the CANARY or EVAL_CANARY variable
# into evidence.json, so the record shows what environment it got. evidence.json holds its run directory
# after an escaped newline, as messages.json holds a path that starts a line, and for pass also behind
# \/ escapes, a JSON spelling that only a decoded string literal shows as the path, and behind a raw é,
# a non-ASCII letter that must not hide a root. EVAL_AGENT_CMD passes
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
  pass|two-grades|further-only|late-fail|both-pass|extra-once|two-pass) action=pass ;;
  fail) action=stop ;;
  void-once) [ "$count" -gt 1 ] || exit 3; action=pass ;;
  void-thrice) [ "$count" -gt 3 ] || exit 3; action=pass ;;
  void-always) exit 3 ;;
  hang) sleep 30; action=pass ;;
  bad-bytes) action=pass ;;
  dirty-once) [ "$count" -gt 1 ] || { echo dirt > "$checkout/dirt.txt"; exit 3; }; action=pass ;;
  record-once) [ "$count" -gt 1 ] || { echo overwritten > "$STUB_RECORD"; exit 3; }; action=pass ;;
  mode-once) [ "$count" -gt 1 ] || { chmod 700 "$STUB_RECORD"; exit 3; }; action=pass ;;
  perm-once) [ "$count" -gt 1 ] || { chmod 600 "$STUB_RECORD"; exit 3; }; action=pass ;;
  relink-once) [ "$count" -gt 1 ] || { ln -sfn "$STUB_TARGET" "$STUB_RECORD"; exit 3; }; action=pass ;;
  locked-once) [ "$count" -gt 1 ] || { chmod 200 "$STUB_RECORD"; echo overwritten > "$STUB_RECORD"; exit 3; }; action=pass ;;
esac
printf '{"action": "%s", "run_dir": "%s", "id": "%s"}\n' "$action" "$run" "$STUB_UUID" > "$run/actions.jsonl"
if [ "$scenario" = bad-bytes ]; then printf '\xff\n' >> "$run/actions.jsonl"; fi
escaped=""
if [ "$scenario" = pass ]; then escaped=", \"escaped\": \"${run//\//\\/}\", \"accented\": \"é$run\""; fi
printf '{"seen_in": "\\n%s"%s, "canary": "%s"}\n' "$run" "$escaped" "${CANARY-${EVAL_CANARY-unset}}" \
  > "$run/evidence.json"
cp "$run/evidence.json" "$STUB_STATE/evidence-$scenario.json"
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
    reference = yaml.safe_load((REFERENCE_CASE / "case.yaml").read_text(encoding="utf-8"))
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
    for name in (*RUNNER_FILES, *SUPPORT_FILES):
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
    agent.write_text(STUB_AGENT, encoding="utf-8")
    agent.chmod(0o755)
    state = tmp_path / "state"
    state.mkdir()
    env = {**os.environ, "EVAL_AGENT_CMD": f"{agent} --model stub/agent-model#high", "STUB_STATE": str(state),
           "STUB_UUID": STUB_UUID, "EVAL_PASS_ENV": "STUB_STATE STUB_UUID", "TMPDIR": str(tmp_path)}
    # CI's private leak patterns must not redact the stub's own strings.
    for name in ("EVAL_TIMEOUT", "EVAL_GRADING_MARGIN", "LEAK_DENYLIST", "LEAK_DENYLIST_FILE", "CANARY", "EVAL_CANARY"):
        env.pop(name, None)

    def run_at(at: Path | str, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["bash", str(harness / "scripts" / "run-suite.sh"), str(at), *args],
                              capture_output=True, text=True,
                              env={**env, **extra})

    def run(*args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        return run_at(evals, *args, **extra)

    def recommit(*scenarios: str) -> str:
        set_scenarios(evals / "stub", scenarios)
        return commit_all(harness)

    return {"run": run, "run_at": run_at, "evals": evals, "harness": harness, "checkout": checkout, "state": state,
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

    summary = (suite["evals"] / "results" / "suite-lab-1.md").read_text(encoding="utf-8")
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
    attempts = {name: int((suite["state"] / name).read_text(encoding="utf-8")) for name in STUB_SCENARIOS}
    assert attempts == {"pass": 2, "fail": 2, "void-once": 3, "void-always": 4}
    assert "checkout-only" not in summary, "cases are listed from the harness checkout, never CHECKOUT"
    assert not (suite["state"] / "checkout-only").exists()


def test_a_graded_run_on_the_last_allowed_attempt_counts(suite) -> None:
    suite["recommit"]("void-thrice")
    result = suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1, result.stderr
    rows = summary_rows((suite["evals"] / "results" / "suite-lab-1.md").read_text(encoding="utf-8"))
    assert rows["void-thrice"][6:8] == ["1", "1"], "attempt 4 of 2×2 is graded and counted"
    assert int((suite["state"] / "void-thrice").read_text(encoding="utf-8")) == 4


def test_every_attempt_writes_a_run_record_and_a_call_record_named_for_it(suite) -> None:
    suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1")
    results = suite["evals"] / "stub" / "results"
    sha, harness_sha = suite["checkout_sha"], suite["harness_sha"]
    expected = {f"lab-1-{scenario}-{sha}-harness-{harness_sha}-{attempt}{suffix}"
                for scenario, count in (("pass", 2), ("fail", 2), ("void-once", 3), ("void-always", 4))
                for attempt in range(1, count + 1) for suffix in (".json", "-calls.jsonl")}
    assert {path.name for path in results.iterdir()} - {".keep"} == expected

    void = json.loads((results / f"lab-1-void-once-{sha}-harness-{harness_sha}-1.json").read_text(encoding="utf-8"))
    assert void["outcome"] == "void" and void["void_reason"] == "run.sh exited 2: void"
    assert void["calls_record"] == "absent", "a void attempt that recorded no calls says so"
    graded = json.loads((results / f"lab-1-void-once-{sha}-harness-{harness_sha}-2.json").read_text(encoding="utf-8"))
    assert graded["outcome"] == "pass" and graded["void_reason"] is None
    assert graded["grades"]["grader-output.txt"][-1] == "PASS"
    assert graded["verdicts"] == {"void-once": "pass"}
    assert graded["model"] == "stub/agent-model" and graded["reasoning_effort"] == "high"
    assert graded["agent_command"] == "{tmpdir}/agent --model stub/agent-model#high"
    assert json.loads(graded["grader_inputs"]["evidence.json"]) == {"seen_in": "\n{run_dir}", "canary": "unset"}, \
        "a run-directory file the grader names is kept with the record"
    assert graded["grader_inputs"]["nested/kept.md"] == "kept\n", "a relative path the grader names is kept too"
    calls = (results / f"lab-1-pass-{sha}-harness-{harness_sha}-1-calls.jsonl").read_text(encoding="utf-8")
    assert json.loads(calls)["action"] == "pass"


def decoded_strings(text: str):
    """Yield text and, wherever it is JSON or JSON Lines, every key and string it holds, decoded
    recursively, each distinct string once."""
    seen, pending = set(), [text]
    while pending:
        string = pending.pop()
        if string in seen:
            continue
        seen.add(string)
        yield string
        lines = string.splitlines()
        documents = []
        for chunk in [string] + (lines if len(lines) > 1 else []):
            try:
                documents.append(json.loads(chunk))
            except ValueError:
                continue
        while documents:
            value = documents.pop()
            if isinstance(value, dict):
                pending.extend(value.keys())
                documents.extend(value.values())
            elif isinstance(value, list):
                documents.extend(value)
            elif isinstance(value, str):
                pending.append(value)


def test_run_directories_sit_outside_both_checkouts_and_never_reach_a_record(suite) -> None:
    suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", "stub")
    run_dirs = (suite["state"] / "run-dirs").read_text(encoding="utf-8").split()
    assert run_dirs
    for run_dir in run_dirs:
        real = Path(run_dir).resolve()
        for checkout in (suite["harness"], suite["checkout"]):
            assert checkout.resolve() not in real.parents, run_dir
    for record in (suite["evals"] / "stub" / "results").iterdir():
        text = record.read_text(encoding="utf-8")
        for run_dir in run_dirs:
            assert run_dir not in text, record.name
        assert STUB_UUID not in text, "a UUID shape is normalised"
        # Every string a record holds, at any depth and decoded again wherever it is JSON text
        # itself (a grader input such as evidence.json), holds no run directory.
        for string in decoded_strings(text):
            for run_dir in run_dirs:
                assert run_dir not in string, f"{record.name} holds a run directory"
    calls = next((suite["evals"] / "stub" / "results").glob("*-pass-*-calls.jsonl")).read_text(encoding="utf-8")
    assert json.loads(calls)["run_dir"] == "{run_dir}"
    # The agent wrote its run directory behind \/ escapes, which only the decoded pass redacts, and
    # behind a raw é, which only the ASCII left boundary lets either pass redact.
    written = (suite["state"] / "evidence-pass.json").read_text(encoding="utf-8")
    assert f'"escaped": "{run_dirs[0]}"'.replace("/", "\\/") in written, written
    assert f'"accented": "é{run_dirs[0]}"' in written, written
    # No grader input of any run record holds a run directory once its JSON content is decoded.
    for path in (suite["evals"] / "stub" / "results").glob("*[0-9].json"):
        for name, content in json.loads(path.read_text(encoding="utf-8", errors="replace"))["grader_inputs"].items():
            for string in decoded_strings(content):
                for run_dir in run_dirs:
                    assert run_dir not in string, f"{path.name} {name} holds a run directory"
    records = list((suite["evals"] / "stub" / "results").glob("*-pass-*-1.json"))
    assert len(records) == 1, "the pass scenario wrote one run record"
    record = json.loads(records[0].read_text(encoding="utf-8"))
    evidence = json.loads(record["grader_inputs"]["evidence.json"])
    assert evidence["escaped"] == "{run_dir}"
    assert evidence["accented"] == "é{run_dir}"


def test_the_normaliser_rewrites_paths_and_leak_shapes_and_keeps_the_rest() -> None:
    normalise = SUITE.Normaliser(SUITE.leak_patterns(), ["sk-passed-credential", "short"],
                                 run_dir=Path("/scratch/run-1"), home=Path("/home/u"))
    text = (f"/scratch/run-1/a.json /home/u/x /home/u2/y /srv/home/u/z /opt/demo/local {STUB_ADDRESS} "
            "https://github.com/a/b skills/story-to-done {run_dir}/kept key=sk-passed-credential short")
    assert normalise(text) == ("{run_dir}/a.json {home}/x {path} {path} {path} {redacted} "
                               "https://github.com/a/b skills/story-to-done {run_dir}/kept key={redacted} short")


# A message as the record holds it: messages.json serialises a newline as the two characters
# backslash and n, so a path that starts a line follows a word character. Each case is the
# message before and after normalising, with real control characters that json.dumps escapes.
RUN_ROOT, HOME_ROOT, OTHER = "/scratch/run-1", "/scratch/home-1", "/srv/home/user"
BOUNDARIES = {"newline": "\n", "tab": "\t", "return": "\r", "backspace": "\b", "formfeed": "\f",
              "u-escape-digit": "\x01", "u-escape-letter": "\x7f\xff", "u-escape-e-acute": "\xe9", "space": "see ",
              # Nothing before the path: it follows the raw quote that opens the serialised string.
              "string-quote": "", "escaped-quote": 'see "', "word-then-newline": "x\n", "return-newline": "\r\n",
              "newline-newline": "\n\n", "tab-newline": "\t\n",
              # Over-redaction by design: a message that quotes an escape is redacted like the escape.
              "quoted-escape": "\\n"}
KEPT = {"url": "https://host", "relative": "a/b/c", "word": "prefix", "bare-n": "n", "newline-then-word": "\nx",
        "newline-then-url": "\nhttps://host", "short-hex": "\\u12"}
NORMALISED_MESSAGES = (
    [pytest.param(f"{before}{RUN_ROOT}/a.json", f"{before}{{run_dir}}/a.json", True, id=f"run-root-{name}")
     for name, before in BOUNDARIES.items()]
    + [pytest.param(f"{before}{OTHER}/notes.txt", f"{before}{{path}}", True, id=f"other-{name}")
       for name, before in BOUNDARIES.items()]
    + [pytest.param(f"{before}{HOME_ROOT}/x", f"{before}{{home}}/x", True, id=f"home-root-{name}")
       for name, before in BOUNDARIES.items()]
    + [pytest.param(f"{RUN_ROOT}/a.json", "{run_dir}/a.json", False, id="run-root-start-of-string"),
       pytest.param(f"{OTHER}/notes.txt", "{path}", False, id="other-start-of-string"),
       pytest.param(f"\n{RUN_ROOT}", "\n{run_dir}", True, id="run-root-bare-after-newline"),
       # A root is replaced only whole, so a longer name falls through to the absolute-path rewrite.
       pytest.param(f"\n{RUN_ROOT}.json", "\n{path}", True, id="run-root-extended-name"),
       pytest.param(f"\n{RUN_ROOT}/a.json\n{OTHER} {OTHER}/b", "\n{run_dir}/a.json\n{path} {path}", True,
                    id="two-paths-after-newline"),
       pytest.param(OTHER, "{path}", True, id="other-standalone"),
       # json.dumps writes lowercase hex, so another writer's uppercase \uXXXX is given as serialised text.
       pytest.param(f'["\\u00FF{RUN_ROOT}/a.json"]', '["\\u00FF{run_dir}/a.json"]', False,
                    id="run-root-u-escape-upper-hex"),
       pytest.param(f'["\\u00FF{OTHER}/notes.txt"]', '["\\u00FF{path}"]', False, id="other-u-escape-upper-hex")]
    + [pytest.param(f"{before}{RUN_ROOT}/a.json", f"{before}{RUN_ROOT}/a.json", True, id=f"run-root-kept-{name}")
       for name, before in KEPT.items() if name != "relative"]
    + [pytest.param(f"{before}{OTHER}", f"{before}{OTHER}", True, id=f"other-kept-{name}")
       for name, before in KEPT.items() if name != "relative"]
    + [pytest.param("a/b/c", "a/b/c", True, id="kept-relative"),
       pytest.param("\na/b/c", "\na/b/c", True, id="kept-relative-after-newline")]
)


@pytest.mark.parametrize("message, expected, serialise", NORMALISED_MESSAGES)
def test_the_normaliser_rewrites_a_path_after_each_boundary_in_a_serialised_message(
        message: str, expected: str, serialise: bool) -> None:
    normalise = SUITE.Normaliser(SUITE.leak_patterns(), run_dir=Path(RUN_ROOT), home=Path(HOME_ROOT))
    if serialise:
        text, wanted = (json.dumps([{"role": "assistant", "content": value}]) for value in (message, expected))
    else:
        text, wanted = message, expected
    assert not any(ord(char) < 0x20 for char in text), "the escape is characters, not a control character"
    assert normalise(text) == wanted
    assert normalise(wanted) == wanted, "a normalised record is left as it is"


# SKL-318: a known root inside a JSON string literal is redacted whatever JSON spelling the
# literal gives it, because the Normaliser decodes each literal. Each set holds one synthetic root
# per placeholder; the non-ASCII set lets a root itself be spelled as raw UTF-8 or as \uXXXX.
ASCII_ROOTS = {"run_dir": RUN_ROOT, "home": HOME_ROOT, "tmp": "/scratch/tmp-1", "tmpdir": "/scratch/tmpdir-1"}
NON_ASCII_ROOTS = {"run_dir": "/scratch/r\u00fcn-1", "home": "/scratch/h\u00f4me-1",
                   "tmp": "/scratch/tmp-\u00f8", "tmpdir": "/scratch/tmpd\u00edr-1"}
DECODED_TAILS = {"file": "/a.json", "spaced": "/My Notes/a b.txt"}


def every_char_escaped(root: str) -> str:
    return "".join(f"\\u{ord(char):04x}" for char in root)


# Each form spells a literal holding a root and a tail; the guard forms redact at 57807ed already.
DECODED_FORMS = {
    "ascii": {
        "solidus": ("must-fail", lambda root, tail: json.dumps(root + tail).replace("/", "\\/")),
        "u-escape": ("must-fail", lambda root, tail: '"' + every_char_escaped(root) + tail + '"'),
        "combined": ("must-fail", lambda root, tail: '"' + "\\/".join(every_char_escaped(part)
                                                                     for part in root.split("/"))
                     + tail.replace("/", "\\/") + '"'),
    },
    "non-ascii": {
        "raw-utf8": ("guard", lambda root, tail: json.dumps(root + tail, ensure_ascii=False)),
        "solidus": ("must-fail", lambda root, tail: json.dumps(root + tail, ensure_ascii=False).replace("/", "\\/")),
        "u-escape": ("must-fail", lambda root, tail: json.dumps(root + tail)),
        "combined": ("must-fail", lambda root, tail: json.dumps(root + tail).replace("/", "\\/")),
    },
}


def in_message(literal: str) -> str:
    return '[{"role": "assistant", "content": ' + literal + "}]"


DECODED_LITERALS = (
    [pytest.param(roots, in_message(spell(root, tail)), in_message(json.dumps(f"{{{name}}}{tail}")),
                  id=f"{label}-{roots}-{name}-{form}-{tail_name}")
     for roots, forms in DECODED_FORMS.items()
     for form, (label, spell) in forms.items()
     for name, root in (ASCII_ROOTS if roots == "ascii" else NON_ASCII_ROOTS).items()
     for tail_name, tail in DECODED_TAILS.items()]
    + [
        # A literal whose value holds a lone surrogate is re-encoded with \uXXXX escapes, so the
        # record still encodes as UTF-8: one literal all ASCII, one that also holds a raw é.
        pytest.param("ascii", in_message('"\\ud800 \\/scratch\\/run-1\\/a.json"'),
                     in_message('"\\ud800 {run_dir}/a.json"'), id="must-fail-lone-surrogate-ascii-with-root"),
        pytest.param("ascii", in_message('"\u00e9\\ud800 \\/scratch\\/run-1\\/a.json"'),
                     in_message('"\\u00e9\\ud800 {run_dir}/a.json"'),
                     id="must-fail-lone-surrogate-raw-e-acute-with-root"),
        # A changed literal is the only one re-encoded: the unchanged literal keeps its spelling.
        pytest.param("ascii", '{"a" :"\\/scratch\\/run-1",  "b": "\\u00E9\\/srv"}',
                     '{"a" :"{run_dir}",  "b": "\\u00E9\\/srv"}', id="must-fail-only-the-changed-literal"),
        pytest.param("ascii", '{"a": "\\/scratch\\/run-1"}\n{"b": "\\/scratch\\/home-1\\/x"}\n',
                     '{"a": "{run_dir}"}\n{"b": "{home}/x"}\n', id="must-fail-json-lines"),
        pytest.param("ascii", 'stderr: wrote "\\/scratch\\/run-1\\/a.json" and stopped',
                     'stderr: wrote "{run_dir}/a.json" and stopped', id="must-fail-literal-in-prose"),
        # A root after an escaped letter is found in the literal as written, and one behind \/ in
        # the decoded value; the changed literal is not all ASCII, so it is re-encoded as raw UTF-8.
        pytest.param("ascii", in_message('"é\\u00e9/scratch/run-1/a \\/scratch\\/home-1\\/b"'),
                     in_message('"éé{run_dir}/a {home}/b"'),
                     id="must-fail-root-after-an-escaped-letter-in-a-raw-utf8-literal"),
        # A root in an object key is redacted like one in a value.
        pytest.param("ascii", '{"\\/scratch\\/run-1\\/a": 1}', '{"{run_dir}/a": 1}', id="must-fail-root-in-an-object-key"),
        # One slash spelled \/ and the rest plain: the written-form pass alone would leave \{run_dir}.
        pytest.param("ascii", '{"k": "\\/scratch/run-1/a"}', '{"k": "{run_dir}/a"}', id="must-fail-mixed-slash-spellings"),
        # A root extended into a longer name is not the root, so it becomes {path} as when plain.
        pytest.param("ascii", '{"k": "\\/scratch\\/run-1.json", "h": "\\/scratch\\/home-1-x\\/b"}',
                     '{"k": "{path}", "h": "{path}"}', id="must-fail-root-extended-into-a-longer-name"),
        # An unclosed quote opens no literal, and a closed literal after its line still redacts.
        pytest.param("ascii", 'x "\\"\\"\\/scratch\\/run-1\nnext "\\/scratch\\/run-1\\/a"',
                     'x "\\"\\"\\/scratch\\/run-1\nnext "{run_dir}/a"', id="must-fail-unclosed-quote-then-a-literal"),
        # A name that only starts like a root, and a quote no literal closes, keep every byte.
        pytest.param("ascii", 'he wrote " then "\\/scratch\\/run-10\\/a" and "\\/scratch\\/run-1x"',
                     'he wrote " then "\\/scratch\\/run-10\\/a" and "\\/scratch\\/run-1x"',
                     id="guard-root-prefix-and-unmatched-quote"),
        # A text with no known root keeps every byte: spacing, key order, escapes and raw UTF-8.
        pytest.param("ascii", '{"b" : "caf\u00e9 \\u00E9 \\/srv\\/x \\ud800",\n  "a": [1, "\\"q\\""]}',
                     '{"b" : "caf\u00e9 \\u00E9 \\/srv\\/x \\ud800",\n  "a": [1, "\\"q\\""]}', id="guard-no-known-root"),
        # A literal that does not decode is left to the text pass.
        pytest.param("ascii", in_message('"\\q /scratch/run-1/a.json"'), in_message('"\\q {run_dir}/a.json"'),
                     id="guard-literal-that-does-not-decode"),
    ]
)


@pytest.mark.parametrize("roots, text, expected", DECODED_LITERALS)
def test_the_normaliser_decodes_each_string_literal_before_redacting_known_roots(
        roots: str, text: str, expected: str) -> None:
    paths = ASCII_ROOTS if roots == "ascii" else NON_ASCII_ROOTS
    normalise = SUITE.Normaliser(SUITE.leak_patterns(), **{name: Path(root) for name, root in paths.items()})
    result = normalise(text)
    assert result == expected
    assert normalise(result) == result, "a normalised record is left as it is"
    result.encode("utf-8")  # a record is written as UTF-8


# SKL-319: only an ASCII letter, digit, _, . or - directly before a known root keeps it whole. Each
# case is a message and its normalised form, spelled as decoded text, as a raw UTF-8 JSON literal
# and as a JSON literal with \uXXXX escapes; a label per form says whether it redacts at 57807ed
# already (guard) or not (must-fail). A form with no label is not part of the case.
def left_boundary_forms(name: str, message: str, expected, labels: dict):
    spelled = {"decoded": lambda text: text,
               "raw-utf8": lambda text: in_message(json.dumps(text, ensure_ascii=False)),
               "u-escape": lambda text: in_message(json.dumps(text)),
               # \/ hides the root from the text pass, so only the decoded pass can replace it; the
               # changed literal is re-encoded as raw UTF-8 with plain solidi.
               "solidus": lambda text: in_message(json.dumps(text, ensure_ascii=False).replace("/", "\\/"))}
    for form, label in labels.items():
        wanted = (expected[form] if isinstance(expected, dict)
                  else spelled["raw-utf8" if form == "solidus" else form](expected))
        yield pytest.param(spelled[form](message), wanted, id=f"{label}-{name}-{form}")


ALL_GUARD = {"decoded": "guard", "raw-utf8": "guard", "u-escape": "guard"}
# A raw non-ASCII character ahead of a root blocked it at 57807ed only where it is a word character.
WORD_BEFORE_ROOT = {"decoded": "must-fail", "raw-utf8": "must-fail", "u-escape": "guard", "solidus": "must-fail"}
LEFT_BOUNDARY = [
    *left_boundary_forms("e-acute-run-root", f"é{RUN_ROOT}/a.json", "é{run_dir}/a.json", WORD_BEFORE_ROOT),
    *left_boundary_forms("cjk-home-root", f"中{HOME_ROOT}/x", "中{home}/x", WORD_BEFORE_ROOT),
    *[case for key in ("tmp", "tmpdir") for before, letter in {"é": "e-acute", "中": "cjk"}.items()
      for case in left_boundary_forms(f"{letter}-{key}-root", f"{before}{ASCII_ROOTS[key]}/x",
                                      f"{before}{{{key}}}/x", WORD_BEFORE_ROOT)],
    *left_boundary_forms("arrow-run-root", f"→{RUN_ROOT}/a.json", "→{run_dir}/a.json", ALL_GUARD),
    *[case for control, before in {"newline": "\n", "tab": "\t", "return": "\r", "backspace": "\b",
                                   "formfeed": "\f"}.items()
      for case in left_boundary_forms(f"{control}-run-root", f"{before}{RUN_ROOT}/a.json",
                                      f"{before}{{run_dir}}/a.json", {"decoded": "guard"})],
    *[case for name, before in {"letter": "x", "digit": "7", "underscore": "_", "dot": ".", "hyphen": "-"}.items()
      for case in left_boundary_forms(f"ascii-{name}-keeps-run-root", f"{before}{RUN_ROOT}/a.json",
                                      f"{before}{RUN_ROOT}/a.json", ALL_GUARD)],
    *left_boundary_forms("cafe-then-home-root", f"/café{HOME_ROOT}", "/café{home}", WORD_BEFORE_ROOT),
    *left_boundary_forms("e-acute-run-root-spaced-tail", f"é{RUN_ROOT}/My Notes/a b.txt",
                         "é{run_dir}/My Notes/a b.txt", WORD_BEFORE_ROOT),
    *left_boundary_forms("cafe-generic-path", "/café/srv/x",
                         {"decoded": "{path}", "raw-utf8": in_message('"{path}"'),
                          "u-escape": in_message('"/caf\\u00e9{path}"')}, ALL_GUARD),
    *left_boundary_forms("e-acute-generic-path", "é/srv/x",
                         {"decoded": "é/srv/x", "raw-utf8": in_message('"é/srv/x"'),
                          "u-escape": in_message('"\\u00e9{path}"')}, ALL_GUARD),
]


@pytest.mark.parametrize("text, expected", LEFT_BOUNDARY)
def test_only_an_ascii_word_character_before_a_known_root_keeps_it(text: str, expected: str) -> None:
    normalise = SUITE.Normaliser(SUITE.leak_patterns(), **{key: Path(root) for key, root in ASCII_ROOTS.items()})
    result = normalise(text)
    assert result == expected
    assert normalise(result) == result, "a normalised record is left as it is"


def test_a_record_with_bytes_that_are_not_utf8_is_still_written(suite) -> None:
    suite["recommit"]("bad-bytes")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1, "the stub grader cannot parse the bad line, a graded fail\n" + result.stderr
    assert "Traceback" not in result.stderr, result.stderr
    results = suite["evals"] / "stub" / "results"
    calls = next(results.glob("*-bad-bytes-*-calls.jsonl")).read_text(encoding="utf-8")
    assert "�" in calls
    assert list(results.glob("lab-1-bad-bytes-*-1.json")), "the attempt record is written"
    assert (suite["evals"] / "results" / "suite-lab-1.md").is_file(), "the suite writes its summary"


def test_a_scenario_graded_twice_reports_each_grade(suite) -> None:
    suite["recommit"]("two-grades")
    result = suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1, "a failing further grade fails the suite\n" + result.stderr
    assert "failing graded runs for: stub two-grades-extra" in result.stderr, result.stderr
    summary = (suite["evals"] / "results" / "suite-lab-1.md").read_text(encoding="utf-8")
    rows, at = summary_rows(summary), columns(summary)
    assert rows["two-grades"][at["k"]] == "2", "the scenario's own grade counts its own verdict"
    assert rows["two-grades-extra"][at["k"]] == "0" and rows["two-grades-extra"][at["n"]] == "2"
    assert rows["two-grades-extra"][at["Role"]] == "discriminating (further grade of two-grades)"


def test_a_further_grade_without_the_scenarios_own_grade_stops_the_suite(suite) -> None:
    suite["recommit"]("further-only")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1 and "no own verdict" in result.stderr, result.stderr
    record = json.loads(next((suite["evals"] / "stub" / "results").glob("*-further-only-*.json")).read_text(encoding="utf-8"))
    assert record["outcome"] == "error" and record["verdicts"] == {}


def test_a_single_grade_follows_the_exit_status(suite) -> None:
    suite["recommit"]("late-fail")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1, "a graded fail fails the suite\n" + result.stderr
    summary = (suite["evals"] / "results" / "suite-lab-1.md").read_text(encoding="utf-8")
    rows, at = summary_rows(summary), columns(summary)
    assert rows["late-fail"][at["n"]] == "1" and rows["late-fail"][at["k"]] == "0"
    record = json.loads(next((suite["evals"] / "stub" / "results").glob("*-late-fail-*.json")).read_text(encoding="utf-8"))
    assert record["outcome"] == "fail" and record["verdicts"] == {"late-fail": "fail"}


def test_grades_that_contradict_the_exit_status_stop_the_suite(suite) -> None:
    suite["recommit"]("both-pass")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1 and "contradict" in result.stderr, result.stderr
    record = json.loads(next((suite["evals"] / "stub" / "results").glob("*-both-pass-*.json")).read_text(encoding="utf-8"))
    assert record["outcome"] == "error" and record["verdicts"] == {}


def test_a_verdict_line_that_redaction_rewrites_keeps_its_verdict(suite) -> None:
    suite["recommit"]("two-pass")
    env = {"CANARY": "the recorded call\nPASS", "EVAL_PASS_ENV": "STUB_STATE STUB_UUID CANARY"}
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", **env)
    assert result.returncode == 0, result.stderr
    record = json.loads(next((suite["evals"] / "stub" / "results").glob("*-two-pass-*.json")).read_text(encoding="utf-8"))
    assert record["outcome"] == "pass" and record["grades"]["grader-output.txt"][-1] == "ok   {redacted}"
    assert record["verdicts"] == {"two-pass": "pass", "two-pass-extra": "pass"}
    (suite["evals"] / "results" / "suite-lab-1.md").unlink()
    resumed = suite["run"]("--runs", "1", "--resume", str(suite["checkout"]), "lab-1", **env)
    assert resumed.returncode == 0, resumed.stderr


def test_a_grade_set_that_changes_between_attempts_stops_the_suite(suite) -> None:
    suite["recommit"]("extra-once")
    result = suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1 and "every graded attempt must write the same grades" in result.stderr, result.stderr
    record = json.loads(next((suite["evals"] / "stub" / "results").glob("*-extra-once-*-2.json")).read_text(encoding="utf-8"))
    assert record["outcome"] == "error"
    assert not (suite["evals"] / "results" / "suite-lab-1.md").exists()


def test_an_attempt_that_changes_a_checkout_stops_the_suite(suite) -> None:
    suite["recommit"]("dirty-once")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1 and "after an attempt of this run changed it" in result.stderr, result.stderr
    assert int((suite["state"] / "dirty-once").read_text(encoding="utf-8")) == 1, "no attempt runs against the changed checkout"
    assert not (suite["evals"] / "results" / "suite-lab-1.md").exists()


# A committed record the run started with, clean or with an unstaged modification, is allowed;
# an attempt that then changes its content or mode changed the harness, so the suite stops.
@pytest.mark.parametrize("scenario, edited_first", [("record-once", False), ("record-once", True),
                                                     ("mode-once", False), ("perm-once", False),
                                                     pytest.param("locked-once", False, marks=pytest.mark.skipif(
                                                         os.geteuid() == 0, reason="root reads through mode 000"))])
def test_an_attempt_that_changes_a_committed_record_stops_the_suite(suite, scenario: str, edited_first: bool) -> None:
    suite["recommit"](scenario)
    record = suite["evals"] / "results" / "suite-a.md"
    record.parent.mkdir(exist_ok=True)
    record.write_text("a record\n")
    commit_all(suite["harness"])
    if edited_first:
        record.write_text("edited before the run\n")
    if scenario == "locked-once":
        record.chmod(0o000)  # unreadable when the run starts, a permission git ignores
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", STUB_RECORD=str(record),
                          EVAL_PASS_ENV="STUB_STATE STUB_UUID STUB_RECORD")
    assert result.returncode == 1, result.stderr
    assert ("committed records an attempt of this run changed (skills/story-to-done/evals/results/suite-a.md)"
            in result.stderr), result.stderr
    assert int((suite["state"] / scenario).read_text(encoding="utf-8")) == 1, "no attempt runs against the changed record"
    assert not (suite["evals"] / "results" / "suite-lab-1.md").exists()


def test_an_attempt_that_retargets_a_record_symlink_stops_the_suite(suite) -> None:
    """A record symlink already retargeted before the run, pointed by an attempt at another file
    with the same content, is still a change: the snapshot holds the link, not what it reaches."""
    suite["recommit"]("relink-once")
    results = suite["evals"] / "results"
    results.mkdir(exist_ok=True)
    for name in ("one.txt", "two.txt", "three.txt"):
        (suite["harness"] / name).write_text("same\n")
    record = results / "suite-a.md"
    record.symlink_to(suite["harness"] / "one.txt")
    commit_all(suite["harness"])
    record.unlink()
    record.symlink_to(suite["harness"] / "two.txt")
    assert first_porcelain_entry(suite["harness"]) == " M skills/story-to-done/evals/results/suite-a.md"
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", STUB_RECORD=str(record),
                          STUB_TARGET=str(suite["harness"] / "three.txt"),
                          EVAL_PASS_ENV="STUB_STATE STUB_UUID STUB_RECORD STUB_TARGET")
    assert result.returncode == 1, result.stderr
    assert ("committed records an attempt of this run changed (skills/story-to-done/evals/results/suite-a.md)"
            in result.stderr), result.stderr
    assert not (suite["evals"] / "results" / "suite-lab-1.md").exists()


def test_a_record_symlink_whose_target_is_not_utf8_does_not_block_a_run(suite) -> None:
    suite["recommit"]("pass")
    results = suite["evals"] / "results"
    results.mkdir(exist_ok=True)
    os.symlink(b"target-\xff", os.fsencode(results / "suite-a.md"))
    commit_all(suite["harness"])
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1")
    assert result.returncode == 0, result.stderr


# A record swapped between its lstat and its read: the read follows no symlink and never blocks
# on a FIFO, whatever kind the earlier lstat reported.
def test_reading_a_swapped_record_follows_no_link_and_never_blocks(tmp_path: Path) -> None:
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    link = tmp_path / "link"
    link.symlink_to(fifo)
    regular = stat.S_IFREG | 0o644
    with pytest.raises(OSError):
        SUITE.held_by(os.fsencode(link), regular)
    assert SUITE.held_by(os.fsencode(fifo), regular) == b""


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
        record = json.loads(next(results.glob(f"{label}-pass-*.json")).read_text(encoding="utf-8"))
        assert json.loads(record["grader_inputs"]["evidence.json"])["canary"] == seen, label
    assert all(canary not in path.read_text(encoding="utf-8") for path in results.iterdir())


def test_a_passed_value_too_short_to_redact_is_refused(suite) -> None:
    suite["recommit"]("pass")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", CANARY="abc123",
                          EVAL_PASS_ENV="STUB_STATE STUB_UUID CANARY")
    assert result.returncode == 2 and "shorter than 8 characters" in result.stderr, result.stderr
    assert "abc123" not in result.stderr
    assert not (suite["state"] / "pass").exists(), "nothing ran"


def test_the_recorded_model_is_normalised(suite) -> None:
    suite["recommit"]("pass")
    agent = suite["env"]["EVAL_AGENT_CMD"].split()[0]
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1",
                          EVAL_AGENT_CMD=f"{agent} --model {STUB_ADDRESS}/m#high")
    assert result.returncode == 0, result.stderr
    record = json.loads(next((suite["evals"] / "stub" / "results").glob("lab-1-pass-*.json")).read_text(encoding="utf-8"))
    assert STUB_ADDRESS not in record["model"] and "{redacted}" in record["model"]
    assert STUB_ADDRESS not in (suite["evals"] / "results" / "suite-lab-1.md").read_text(encoding="utf-8")


def test_an_attempt_past_its_deadline_is_void(suite) -> None:
    suite["recommit"]("hang")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", EVAL_TIMEOUT="1", EVAL_GRADING_MARGIN="1")
    assert result.returncode == 1, result.stderr
    rows = summary_rows((suite["evals"] / "results" / "suite-lab-1.md").read_text(encoding="utf-8"))
    assert rows["hang"][6] == "0" and rows["hang"][10] == "2"
    assert "did not finish within 2 seconds" in rows["hang"][11]


def test_an_undefined_exit_status_stops_the_suite(suite) -> None:
    suite["recommit"]("broken", "pass")
    result = suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1")
    assert result.returncode == 1 and "a status the case contract does not define" in result.stderr, result.stderr
    records = list((suite["evals"] / "stub" / "results").glob("*-broken-*.json"))
    assert len(records) == 1, "the broken attempt is recorded once and never retried"
    assert json.loads(records[0].read_text(encoding="utf-8"))["outcome"] == "error"
    assert not (suite["state"] / "pass").exists(), "nothing runs after a broken attempt"
    assert not (suite["evals"] / "results" / "suite-lab-1.md").exists()


def test_the_runner_refuses_to_overwrite_and_exits_2(suite) -> None:
    first = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", "stub")
    summary = suite["evals"] / "results" / "suite-lab-1.md"
    before = summary.read_text(encoding="utf-8")
    again = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", "stub")
    assert first.returncode == 1 and again.returncode == 2, again.stderr
    assert summary.read_text(encoding="utf-8") == before
    assert (suite["state"] / "pass").read_text(encoding="utf-8").strip() == "1", "nothing ran before the refusal"

    summary.unlink()
    record_clash = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1", "stub")
    assert record_clash.returncode == 2, "an existing run record is never overwritten"
    assert "exists" in record_clash.stderr


def test_resume_continues_an_interrupted_run_from_its_records(suite) -> None:
    first = suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1", "stub")
    summary = suite["evals"] / "results" / "suite-lab-1.md"
    before = summary.read_text(encoding="utf-8")
    summary.unlink()  # as if the run had stopped before its summary
    records = sorted(path.name for path in (suite["evals"] / "stub" / "results").iterdir())
    resumed = suite["run"]("--runs", "2", "--resume", str(suite["checkout"]), "lab-1", "stub")
    assert (first.returncode, resumed.returncode) == (1, 1), resumed.stderr
    assert summary.read_text(encoding="utf-8") == before, "the resumed summary counts the existing records"
    assert sorted(path.name for path in (suite["evals"] / "stub" / "results").iterdir()) == records
    assert int((suite["state"] / "pass").read_text(encoding="utf-8")) == 2, "no attempt with a record runs again"


@pytest.mark.parametrize("change", ["model", "broken", "outcome", "verdicts", "exit-code-type", "grade-line-type",
                                    "fewer-runs"])
def test_resume_refuses_records_it_cannot_count(suite, change: str) -> None:
    suite["recommit"]("pass")
    suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1")
    summary = suite["evals"] / "results" / "suite-lab-1.md"
    summary.unlink()
    extra, runs = {}, "2"
    record_path = next((suite["evals"] / "stub" / "results").glob("lab-1-pass-*-1.json"))
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if change == "model":
        extra["EVAL_AGENT_CMD"] = suite["env"]["EVAL_AGENT_CMD"].replace("agent-model", "other-model")
    elif change == "broken":
        record_path.write_text(json.dumps({**record, "outcome": "error"}))
    elif change == "outcome":
        record_path.write_text(json.dumps({**record, "outcome": "fail", "verdicts": {"pass": "fail"}}))
    elif change == "verdicts":
        record_path.write_text(json.dumps({**record, "verdicts": {"pass": "pass", "pass-extra": "pass"}}))
    elif change == "exit-code-type":
        record_path.write_text(json.dumps({**record, "exit_code": [0]}))
    elif change == "grade-line-type":
        record_path.write_text(json.dumps({**record, "grades": {"grader-output.txt": [1]}}))
    else:
        runs = "1"
    resumed = suite["run"]("--runs", runs, "--resume", str(suite["checkout"]), "lab-1", **extra)
    assert resumed.returncode == 2, resumed.stderr
    assert int((suite["state"] / "pass").read_text(encoding="utf-8")) == 2, "nothing ran"
    assert not summary.exists()


@pytest.mark.parametrize("args", [
    ["--runs", "0", "CHECKOUT", "lab"],
    ["CHECKOUT", "bad/label"],
    ["CHECKOUT", "lab", "no-such-case"],
    ["CHECKOUT", "lab", "checkout-only"],
    ["CHECKOUT", "lab", "stub", "stub"],
    ["NOT-A-DIR", "lab"],
    ["EVALS=NOT-A-DIR", "CHECKOUT", "lab"],
])
def test_the_runner_refuses_bad_arguments(suite, args) -> None:
    args = [str(suite["checkout"]) if arg == "CHECKOUT" else arg for arg in args]
    if args[0].startswith("EVALS="):
        result = suite["run_at"](args[0][6:], *args[1:])
        assert "EVALS NOT-A-DIR is not a directory" in result.stderr, result.stderr
    else:
        result = suite["run"](*args)
    assert result.returncode == 2, result.stderr
    assert not (suite["state"] / "pass").exists(), "nothing ran"


@pytest.mark.parametrize("mode", [["--list"], ["--runs", "1", "CHECKOUT", "lab"]])
@pytest.mark.parametrize("at", ["skills/story-to-done", "skills", ".", "skills/story-to-done/evals/stub"])
def test_evals_must_be_a_skills_evals_directory_of_the_harness(suite, at: str, mode) -> None:
    suite["recommit"]("pass")
    args = [str(suite["checkout"]) if arg == "CHECKOUT" else arg for arg in mode]
    result = suite["run_at"](suite["harness"] / at, *args)
    assert result.returncode == 2 and "skills/<skill>/evals" in result.stderr, result.stderr
    assert result.stdout == "", "nothing listed"
    assert not (suite["state"] / "pass").exists(), "nothing ran"


def test_evals_of_another_checkout_than_the_runners_is_refused(suite) -> None:
    """The harness commit a record names must be the checkout whose runner ran."""
    suite["recommit"]("pass")
    foreign = suite["checkout"] / "skills" / "story-to-done" / "evals"
    result = suite["run_at"](foreign, "--runs", "1", str(suite["checkout"]), "lab")
    assert result.returncode == 2 and "not in the checkout holding this runner" in result.stderr, result.stderr
    assert not (suite["state"] / "pass").exists(), "nothing ran"
    assert not (foreign / "results").exists(), "nothing written"


@pytest.mark.parametrize("skill", ["other-skill", "café", "odd\rskill"])
def test_the_runner_runs_a_second_skills_suite_twice(suite, skill: str) -> None:
    evals = suite["harness"] / "skills" / skill / "evals"
    stub_case(evals / "stub", scenarios=("pass",))
    commit_all(suite["harness"])
    for label in ("lab-1", "lab-2"):
        result = suite["run_at"](evals, "--runs", "1", str(suite["checkout"]), label)
        assert result.returncode == 0, result.stderr
        assert (evals / "results" / f"suite-{label}.md").is_file()


def test_list_skips_a_case_yaml_that_is_not_a_file(suite) -> None:
    (suite["evals"] / "phantom" / "case.yaml").mkdir(parents=True)
    result = suite["run"]("--list")
    assert (result.returncode, result.stdout) == (0, "stub\n"), result.stderr


@pytest.mark.parametrize("mode", ["list", "run"])
def test_an_evals_directory_with_no_case_is_refused_and_writes_nothing(suite, mode: str) -> None:
    empty = suite["harness"] / "skills" / "empty" / "evals"
    empty.mkdir(parents=True)
    (empty / "README.md").write_text("no case yet\n", encoding="utf-8")
    commit_all(suite["harness"])
    args = ["--list"] if mode == "list" else ["--runs", "1", str(suite["checkout"]), "lab"]
    result = suite["run_at"](empty, *args)
    assert result.returncode == 2 and "no case" in result.stderr, result.stderr
    assert result.stdout == "", "an empty suite lists nothing"
    assert not (empty / "results").exists(), "an empty suite writes no summary"


@pytest.mark.parametrize("mode", ["list", "run"])
def test_a_case_directory_the_runner_cannot_run_is_refused_before_listing(suite, mode: str) -> None:
    """--list and a run refuse the same case names, so a listed case is one the suite can run."""
    stub_case(suite["evals"] / "case with spaces")
    commit_all(suite["harness"])
    args = ["--list"] if mode == "list" else ["--runs", "1", str(suite["checkout"]), "lab"]
    result = suite["run"](*args)
    assert result.returncode == 2 and "case with spaces" in result.stderr, result.stderr
    assert result.stdout == "", "nothing is listed"
    assert not (suite["state"] / "pass").exists(), "nothing ran"


@pytest.mark.parametrize("sibling", ["case with spaces", "results"])
def test_a_named_case_runs_beside_a_sibling_the_runner_cannot_run(suite, sibling: str) -> None:
    """Naming the cases checks only those, so a bad sibling does not block a named run."""
    suite["recommit"]("pass")
    stub_case(suite["evals"] / sibling)
    commit_all(suite["harness"])
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab", "stub")
    assert result.returncode == 0, result.stderr


def test_a_case_directory_named_results_is_refused(suite) -> None:
    """evals/results/ holds the suite's summaries, so a case there would read as records."""
    stub_case(suite["evals"] / "results")
    commit_all(suite["harness"])
    result = suite["run"]("--list")
    assert result.returncode == 2 and "'results'" in result.stderr, result.stderr


def test_the_runner_wrapper_works_through_a_symlink(suite, tmp_path: Path) -> None:
    link = tmp_path / "linked-run-suite.sh"
    link.symlink_to(suite["harness"] / "scripts" / "run-suite.sh")
    result = subprocess.run(["bash", str(link), str(suite["evals"]), "--list"], capture_output=True, text=True,
                            env=suite["env"])
    assert (result.returncode, result.stdout) == (0, "stub\n"), result.stderr


def test_the_runner_wrapper_needs_no_readlink_f(suite, tmp_path: Path) -> None:
    """A readlink without -f, as on BSD, still follows a chain of relative links to the runner."""
    shims = tmp_path / "shims"
    shims.mkdir()
    real = shutil.which("readlink")
    shim = shims / "readlink"
    shim.write_text(f'#!/bin/sh\nfor arg; do [ "$arg" = -f ] && {{ echo "readlink: illegal option -- f" >&2; exit 1; }}; done\n'
                    f'exec {real} "$@"\n')
    shim.chmod(0o755)
    links = tmp_path / "links"
    links.mkdir()
    (links / "inner.sh").symlink_to(os.path.relpath(suite["harness"] / "scripts" / "run-suite.sh", links))
    (tmp_path / "outer.sh").symlink_to("links/inner.sh")
    env = {**suite["env"], "PATH": f"{shims}{os.pathsep}{suite['env']['PATH']}"}
    result = subprocess.run(["bash", str(tmp_path / "outer.sh"), str(suite["evals"]), "--list"], capture_output=True,
                            text=True, env=env)
    assert (result.returncode, result.stdout) == (0, "stub\n"), result.stderr


@pytest.mark.parametrize("where", ["harness", "checkout"])
def test_another_skills_uncommitted_record_is_a_change_like_any_other(suite, where: str) -> None:
    suite["recommit"]("pass")
    other = suite[where] / "skills" / "other" / "evals" / "results"
    other.mkdir(parents=True)
    (other / "suite-earlier.md").write_text("an earlier run of another skill\n", encoding="utf-8")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab")
    assert result.returncode == 2, result.stderr
    assert refused_paths(result.stderr) == "skills/other/evals/results/suite-earlier.md"
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
    ("skills/other-skill/evals/results/suite-a.md", False),
    ("skills/other-skill/evals/case/results/a.json", False),
    ("other/story-to-done/evals/results/a.md", False),
    ("results/a.md", False),
    ("case/results/a.json", False),
])
def test_only_the_suites_own_outputs_count_as_records(path: str, expected: bool) -> None:
    assert SUITE.is_record(path, EVALS_PARTS) is expected


@pytest.mark.parametrize("evals_parts", [(), ("evals",), ("skills", "x", "y", "evals")])
def test_no_path_is_a_record_of_a_misplaced_evals_directory(evals_parts) -> None:
    assert SUITE.is_record("results/a.md", evals_parts) is False
    assert SUITE.is_record("skills/x/y/evals/results/a.md", evals_parts) is False


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


@pytest.mark.parametrize("where", ["harness", "checkout"])
def test_a_path_that_is_not_utf8_is_refused_as_a_change(suite, where: str) -> None:
    """A file name git prints as bytes that are not UTF-8 is still a change the run refuses."""
    (suite[where] / os.fsdecode(b"bad-\xff.md")).write_text("new\n")
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab")
    assert result.returncode == 2 and "uncommitted changes" in result.stderr, result.stderr
    assert "Traceback" not in result.stderr, result.stderr
    assert not (suite["state"] / "pass").exists(), "nothing ran"


def test_uncommitted_records_do_not_block_a_later_run(suite) -> None:
    suite["recommit"]("pass")
    assert suite["run"]("--runs", "1", str(suite["checkout"]), "lab-1").returncode == 0
    assert git(suite["harness"], "status", "--porcelain", "--untracked-files=all"), "the records are untracked"
    second = suite["run"]("--runs", "1", str(suite["checkout"]), "lab-2")
    assert second.returncode == 0, second.stderr


def first_porcelain_entry(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
                          check=True, capture_output=True, text=True).stdout.splitlines()[0]


def refused_paths(stderr: str) -> str:
    match = re.search(r"has uncommitted changes \((.*)\), so its commit", stderr)
    assert match, stderr
    return match.group(1)


# SKL-289: each change is the first `git status --porcelain` entry, so a blank index column at the
# start of the output shows whether the refusal still names the whole path.
@pytest.mark.parametrize("change, entry, named", [
    ("unstaged", " M README.md", "README.md"),
    ("staged", "M  README.md", "README.md"),
    ("untracked", "?? NEW.md", "NEW.md"),
    ("renamed", "R  README.md -> MOVED.md", "README.md -> MOVED.md"),
])
@pytest.mark.parametrize("where, role", [("harness", "harness"), ("checkout", "skill")])
def test_the_refusal_names_the_first_changed_path_whole(suite, where: str, role: str, change: str, entry: str,
                                                        named: str) -> None:
    repo = suite[where]
    git(repo, "config", "status.renames", "true")  # the porcelain rename shape this test asserts
    (repo / "README.md").write_text("readme\n")
    commit_all(repo)
    if change == "unstaged":
        (repo / "README.md").write_text("")
    elif change == "staged":
        (repo / "README.md").write_text("")
        git(repo, "add", "README.md")
    elif change == "untracked":
        (repo / "NEW.md").write_text("new\n")
    else:
        git(repo, "mv", "README.md", "MOVED.md")
    assert first_porcelain_entry(repo) == entry
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "repro3")
    assert result.returncode == 2, result.stderr
    assert f"the {role} checkout" in result.stderr, result.stderr
    assert refused_paths(result.stderr) == named
    assert not (suite["state"] / "pass").exists(), "nothing ran"


def commit_a_record(suite) -> Path:
    suite["recommit"]("pass")
    record = suite["evals"] / "results" / "suite-a.md"
    record.parent.mkdir(exist_ok=True)
    record.write_text("a record\n")
    commit_all(suite["harness"])
    record.write_text("a changed record\n")
    return record


def test_a_tracked_record_with_an_unstaged_change_does_not_block_a_run(suite) -> None:
    commit_a_record(suite)
    assert first_porcelain_entry(suite["harness"]) == " M skills/story-to-done/evals/results/suite-a.md"
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab")
    assert result.returncode == 0, result.stderr


def test_a_changed_record_does_not_hide_another_change(suite) -> None:
    (suite["harness"] / "README.md").write_text("readme\n")
    commit_a_record(suite)
    (suite["harness"] / "README.md").write_text("")
    assert first_porcelain_entry(suite["harness"]) == " M README.md"
    assert "results/suite-a.md" in git(suite["harness"], "status", "--porcelain"), "the record is changed too"
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab")
    assert result.returncode == 2, result.stderr
    assert refused_paths(result.stderr) == "README.md"
    assert not (suite["state"] / "pass").exists(), "nothing ran"


def test_a_changed_record_first_does_not_hide_a_later_change(suite) -> None:
    commit_a_record(suite)
    (suite["harness"] / "zzz.md").write_text("new\n")
    assert first_porcelain_entry(suite["harness"]) == " M skills/story-to-done/evals/results/suite-a.md"
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab")
    assert result.returncode == 2, result.stderr
    assert refused_paths(result.stderr) == "zzz.md"
    assert not (suite["state"] / "pass").exists(), "nothing ran"


def make_record_conflict(harness: Path, record: Path) -> None:
    git(harness, "checkout", "-q", "--", str(record))
    base = git(harness, "rev-parse", "--abbrev-ref", "HEAD")
    git(harness, "checkout", "-q", "-b", "other")
    record.write_text("other\n")
    commit_all(harness)
    git(harness, "checkout", "-q", base)
    record.write_text("ours\n")
    commit_all(harness)
    subprocess.run(["git", "-C", str(harness), "merge", "-q", "other"], capture_output=True, text=True)


RECORD = "skills/story-to-done/evals/results/suite-a.md"


# Only an untracked record or one with an unstaged modification is the suite's own output; any
# other state on a record path is a change the harness commit would not describe.
@pytest.mark.parametrize("state, entry, named", [
    ("staged", f"M  {RECORD}", RECORD),
    ("deleted", f" D {RECORD}", RECORD),
    ("renamed-out", f"R  {RECORD} -> Makefile", f"{RECORD} -> Makefile"),
    ("unmerged", f"UU {RECORD}", RECORD),
])
def test_a_record_in_any_other_state_is_refused(suite, state: str, entry: str, named: str) -> None:
    harness = suite["harness"]
    git(harness, "config", "status.renames", "true")  # the porcelain rename shape this test asserts
    record = commit_a_record(suite)
    if state == "staged":
        git(harness, "add", str(record))
    elif state == "deleted":
        record.unlink()
    elif state == "renamed-out":
        git(harness, "checkout", "-q", "--", str(record))
        git(harness, "mv", str(record), "Makefile")
    else:
        make_record_conflict(harness, record)
    assert first_porcelain_entry(harness) == entry
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab")
    assert result.returncode == 2, result.stderr
    assert refused_paths(result.stderr) == named
    assert not (suite["state"] / "pass").exists(), "nothing ran"


def test_a_run_directory_inside_a_checkout_is_refused(suite) -> None:
    inside = suite["checkout"] / ".git" / "scratch"
    inside.mkdir()
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab", TMPDIR=str(inside))
    assert result.returncode == 2 and "set TMPDIR outside both checkouts" in result.stderr, result.stderr
    assert not (suite["state"] / "pass").exists(), "nothing ran"


@pytest.mark.parametrize("scenarios", [None, []])
def test_a_case_without_scenarios_is_refused(suite, scenarios) -> None:
    case_file = suite["evals"] / "stub" / "case.yaml"
    case = yaml.safe_load(case_file.read_text(encoding="utf-8"))
    if scenarios is None:
        del case["scenarios"]
    else:
        case["scenarios"] = scenarios
    case_file.write_text(yaml.safe_dump(case, sort_keys=False))
    commit_all(suite["harness"])
    result = suite["run"]("--runs", "1", str(suite["checkout"]), "lab")
    assert result.returncode == 2 and "names no scenarios" in result.stderr, result.stderr


def test_a_run_with_every_scenario_graded_and_passing_exits_0(suite) -> None:
    suite["recommit"]("pass", "void-once")
    result = suite["run"]("--runs", "3", str(suite["checkout"]), "lab-3", "stub")
    assert result.returncode == 0, result.stderr


def test_a_failing_case_exits_non_zero_and_still_writes_its_summary(suite) -> None:
    """SKL-338 AC3: every scenario reaches N graded runs, but one case fails a run, so the
    suite exits 1; the summary is still written, and stderr names the failing scenario."""
    suite["recommit"]("pass", "fail")
    result = suite["run"]("--runs", "2", str(suite["checkout"]), "lab-1", "stub")
    assert result.returncode == 1, result.stderr
    assert "failing graded runs for: stub fail" in result.stderr, result.stderr
    rows = summary_rows((suite["evals"] / "results" / "suite-lab-1.md").read_text(encoding="utf-8"))
    assert rows["fail"][6:8] == ["2", "0"] and rows["pass"][6:8] == ["2", "2"]


def test_list_prints_the_cases_of_the_evals_directory_and_runs_nothing(suite) -> None:
    suite["recommit"]("pass")
    other = suite["evals"] / "other"
    stub_case(other, scenarios=("pass",))
    commit_all(suite["harness"])
    result = suite["run"]("--list")
    assert (result.returncode, result.stdout) == (0, "other\nstub\n"), result.stderr
    assert not (suite["state"] / "pass").exists(), "nothing ran"
    assert git(suite["harness"], "status", "--porcelain", "--untracked-files=all", "--ignored") == "", \
        "--list writes nothing"


@pytest.mark.parametrize("args", [["--list", "CHECKOUT"], ["--list", "--runs", "2"], ["--list", "--resume"]])
def test_list_takes_no_run_arguments(suite, args) -> None:
    args = [str(suite["checkout"]) if arg == "CHECKOUT" else arg for arg in args]
    result = suite["run"](*args)
    assert result.returncode == 2, result.stderr


# The cases story-to-done ships; a case removed or added changes this list on purpose.
STORY_TO_DONE_CASES = ["owner-wait-verified", "pending-ruling-not-sent-to-engineer", "qa-unfinished-own-steps"]


def test_the_story_to_done_evals_list_every_case_through_the_shared_runner() -> None:
    """The documented command, run from the repository root with the relative EVALS path."""
    result = subprocess.run(["bash", "scripts/run-suite.sh", "skills/story-to-done/evals", "--list"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == STORY_TO_DONE_CASES


def test_the_runner_lives_once_under_scripts() -> None:
    copies = sorted(str(path.relative_to(ROOT)) for name in ("run-suite.sh", "suite.py", "eval_suite.py")
                    for path in (ROOT / "skills").rglob(name))
    assert copies == [], "no skill keeps its own copy of the suite runner"
    assert all((ROOT / name).is_file() for name in RUNNER_FILES)


# --- AC3: the case contract -------------------------------------------------------------------

# Fixed here, not read from a case under test, so dropping a field from any case.yaml fails.
REQUIRED_FIELDS = {
    "baseline", "candidate", "case", "graded_on", "kind", "not_graded_on", "purpose", "runtime",
    "scenarios", "skill", "split",
}
# File names that hold the agent's prose rather than its tool calls: named for agent output, a
# transcript, a stream or a response, or a plain-text or log file, which no call record is.
PROSE = re.compile(r"(?i)agent[-_]?output|transcript|stdout|stderr|response|\.(?:txt|log)$")
# A file run.sh redirects command output into, such as the agent's output.
REDIRECT = re.compile(r'>\s*"?\$\{?run\}?/([^"\s;|&]+)')


def contract_errors(case_dir: Path, tracked_mode) -> list[str]:
    """Every way a case directory breaks the contract SKL-164 AC3 states."""
    errors = []
    if not SUITE.is_case_name(case_dir.name):
        errors.append(f"case directory {case_dir.name!r} is not a name the runner runs")
    try:
        case = yaml.safe_load((case_dir / "case.yaml").read_text(encoding="utf-8"))
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
        # The runner takes only names that match NAME, so a name like ../results is no fixture.
        if not SUITE.NAME.fullmatch(str(name or "")) or not (case_dir / "scenarios" / name).is_dir():
            errors.append(f"no fixtures for scenario {name!r}")
    named = [scenario.get("name") for scenario in scenarios if isinstance(scenario, dict)] \
        if isinstance(scenarios, list) else []
    if len(set(map(str, named))) != len(named):
        errors.append("case.yaml names a scenario more than once")
    names = SUITE.grader_names(case_dir / "grader.py") if (case_dir / "grader.py").is_file() else set()
    if not any("actions.jsonl" in name for name in names):
        errors.append("the grader does not read the tool-call record actions.jsonl")
    # Only strings shaped as file names count, so a grader's own messages may say "transcript".
    files = {name for name in names if SUITE.RELATIVE_FILE.fullmatch(name)}
    written = set(REDIRECT.findall((case_dir / "run.sh").read_text(encoding="utf-8"))) if (case_dir / "run.sh").is_file() else set()
    prose = sorted(name for name in files if PROSE.search(name) or name in written)
    if prose:
        errors.append(f"the grader reads the agent's prose: {prose}")
    return errors


def git_mode(path: Path) -> str:
    entry = git(ROOT, "ls-files", "-s", "--", str(path.relative_to(ROOT)))
    return entry.split()[0] if entry else "untracked"


def file_mode(path: Path) -> str:
    return "100755" if path.stat().st_mode & stat.S_IXUSR else "100644"


def discover_cases(root: Path) -> list[Path]:
    """Every case directory of every skill: skills/*/evals/*/case.yaml (SKL-338 AC4)."""
    return sorted(path.parent for path in root.glob("skills/*/evals/*/case.yaml"))


CASES = discover_cases(ROOT)


def test_the_suite_has_cases() -> None:
    assert REFERENCE_CASE in CASES


@pytest.mark.parametrize("case_dir", CASES, ids=lambda path: str(path.relative_to(ROOT / "skills")))
def test_every_case_directory_keeps_the_contract(case_dir: Path) -> None:
    assert contract_errors(case_dir, git_mode) == []


def test_a_case_of_any_skill_missing_its_grader_fails_the_contract(tmp_path: Path) -> None:
    """A case under another skill's evals/ is discovered, and one missing grader.py fails."""
    kept = tmp_path / "skills" / "some-skill" / "evals" / "kept-case"
    broken = tmp_path / "skills" / "other-skill" / "evals" / "broken-case"
    stub_case(kept)
    stub_case(broken)
    (broken / "grader.py").unlink()
    assert discover_cases(tmp_path) == [broken, kept]
    assert contract_errors(kept, file_mode) == []
    assert "no grader.py" in contract_errors(broken, file_mode)


@pytest.mark.parametrize("breakage", [
    "no-kind", "bad-kind", "no-prompt", "no-grader", "no-run", "run-not-executable",
    "no-results", "no-fixture", "prose-grader", "prose-beside-calls", "missing-field", "no-scenarios",
    "prose-stdout", "prose-log", "prose-response", "prose-redirected", "scenario-outside-scenarios",
    "duplicate-scenario",
])
def test_the_contract_check_catches_each_breakage(tmp_path: Path, breakage: str) -> None:
    case_dir = tmp_path / "case"
    stub_case(case_dir)
    assert contract_errors(case_dir, file_mode) == [], "the stub case keeps the contract"
    case = yaml.safe_load((case_dir / "case.yaml").read_text(encoding="utf-8"))
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
    elif breakage == "scenario-outside-scenarios":
        # scenarios/../results is the case's results/ directory, so it exists but is no fixture.
        case["scenarios"][0]["name"] = "../results"
    elif breakage == "duplicate-scenario":
        case["scenarios"].append(dict(case["scenarios"][0]))
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


@pytest.mark.parametrize("name", ["case with spaces", "results"])
def test_a_case_directory_name_the_runner_refuses_fails_the_contract(tmp_path: Path, name: str) -> None:
    case_dir = tmp_path / name
    stub_case(case_dir)
    assert any("case directory" in error for error in contract_errors(case_dir, file_mode))


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
    case = yaml.safe_load((REFERENCE_CASE / "case.yaml").read_text(encoding="utf-8"))
    assert case["kind"] == "discriminating"
    assert case["baseline"]["commit"] == "7a6cb17"
    assert case["candidate"]["commit"] == "4f0eb79"
    assert re.search(r"SKL-164 owns the suite harness, the README and the repeat-run machinery", case["split"])
