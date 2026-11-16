"""Behavioural tests for skills/story-to-done/scripts/qa-round-cap.py (SKL-284).

The script runs through its CLI with a stub `linear` first on PATH; no test reaches a live service.
The stub serves a synthetic `linear issue view <KEY> --json` payload built from
tests/fixtures/qa_round_cap/issues.json and records every argv it is called with.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "story-to-done" / "scripts" / "qa-round-cap.py"
FIXTURES = ROOT / "tests" / "fixtures" / "qa_round_cap"
COMMENTS = json.loads((FIXTURES / "issues.json").read_text())["comments"]
QA_SKILL = ROOT / "skills" / "qa-verification" / "SKILL.md"
STD_SKILL = ROOT / "skills" / "story-to-done" / "SKILL.md"

KEY = "ABC-123"
IN_PROGRESS = "In Progress"
SENTINEL = "sentinel-token-value-for-qa-round-cap-tests"

STUB = """#!{python}
import json, os, sys
with open(os.environ["QA_STUB_LOG"], "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
args = sys.argv[1:]
if len(args) != 4 or args[0:2] != ["issue", "view"] or args[3] != "--json":
    sys.stderr.write("stub: unexpected call\\n")
    sys.exit(64)
mode = os.environ.get("QA_STUB_MODE", "ok")
if mode == "fail":
    sys.stderr.write("stub: tracker unavailable\\n")
    sys.exit(1)
if mode == "garbage":
    sys.stdout.write("this is not json\\n")
    sys.exit(0)
with open(os.environ["QA_STUB_ISSUE"]) as issue:
    sys.stdout.write(issue.read())
"""


class Harness:
    def __init__(self, tmp_path: Path) -> None:
        self.bin = tmp_path / "bin"
        self.bin.mkdir()
        stub = self.bin / "linear"
        stub.write_text(STUB.format(python=sys.executable))
        stub.chmod(0o755)
        self.state_dir = tmp_path / "scratch"
        self.state_dir.mkdir()
        self.issue = tmp_path / "issue.json"
        self.log = tmp_path / "linear-calls.jsonl"
        self.log.write_text("")
        self.mode = "ok"
        self.extra_env: dict[str, str] = {}
        self.serve(IN_PROGRESS, [])

    @property
    def state_file(self) -> Path:
        return self.state_dir / "qa-round-cap" / f"{KEY}.json"

    def serve(self, state: str, comment_names: list[str]) -> None:
        nodes = [COMMENTS[name] for name in comment_names]
        nodes.sort(key=lambda node: node["createdAt"], reverse=True)
        payload = {"identifier": KEY, "state": {"name": state}, "comments": {"nodes": nodes}}
        self.issue.write_text(json.dumps(payload))

    def run(self, *args: str) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env.update(
            PATH=f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}",
            QA_STUB_LOG=str(self.log),
            QA_STUB_ISSUE=str(self.issue),
            QA_STUB_MODE=self.mode,
        )
        env.update(self.extra_env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, timeout=60
        )

    def arm(self, cap: str = "2") -> subprocess.CompletedProcess:
        return self.run(
            "arm", "--story", KEY, "--cap", cap, "--in-progress", IN_PROGRESS, "--state-dir", str(self.state_dir)
        )

    def record(self) -> subprocess.CompletedProcess:
        return self.run("record", "--story", KEY, "--state-dir", str(self.state_dir))

    def rearm(self, rounds: str) -> subprocess.CompletedProcess:
        return self.run("rearm", "--story", KEY, "--additional-rounds", rounds, "--state-dir", str(self.state_dir))

    def calls(self) -> list[list[str]]:
        return [json.loads(line) for line in self.log.read_text().splitlines() if line]


@pytest.fixture
def h(tmp_path: Path) -> Harness:
    return Harness(tmp_path)


def ok(result: subprocess.CompletedProcess) -> str:
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    lines = result.stdout.splitlines()
    assert len(lines) == 1, result.stdout
    return lines[0]


def failed(result: subprocess.CompletedProcess, code: int) -> str:
    assert result.returncode == code, (result.returncode, result.stdout, result.stderr)
    assert result.stdout == ""
    lines = result.stderr.splitlines()
    assert len(lines) == 1, f"a non-zero exit prints exactly one stderr line: {result.stderr!r}"
    return lines[0]


# AC1: the interface.


def test_help_names_the_four_subcommands_and_the_exit_codes(h: Harness) -> None:
    result = h.run("--help")
    assert result.returncode == 0
    for name in ("validate", "arm", "record", "rearm"):
        assert re.search(rf"^\s+{name}\b", result.stdout, re.MULTILINE), name
    for code in ("0", "1", "2", "3"):
        assert re.search(rf"^\s+{code}\s", result.stdout, re.MULTILINE), code


@pytest.mark.parametrize("argv", [[], ["stop"], ["frobnicate", "--story", KEY]])
def test_a_missing_or_unknown_subcommand_exits_2_with_one_line(h: Harness, argv: list[str]) -> None:
    failed(h.run(*argv), 2)


def test_an_unknown_option_exits_2_with_one_line_and_leaves_the_state_unchanged(h: Harness) -> None:
    ok(h.arm())
    before = h.state_file.read_bytes()
    failed(h.run("record", "--story", KEY, "--state-dir", str(h.state_dir), "--bogus"), 2)
    assert h.state_file.read_bytes() == before


@pytest.mark.parametrize("subcommand", ["arm", "record", "rearm"])
def test_every_subcommand_but_validate_requires_the_state_dir(h: Harness, subcommand: str) -> None:
    args = {"arm": ["--cap", "2", "--in-progress", IN_PROGRESS], "record": [], "rearm": ["--additional-rounds", "1"]}
    failed(h.run(subcommand, "--story", KEY, *args[subcommand]), 2)


# AC2: validate.


@pytest.mark.parametrize("value", ["1", "3", "12", "100"])
def test_validate_prints_a_positive_integer(h: Harness, value: str) -> None:
    assert ok(h.run("validate", f"qa-round-cap={value}")) == value


@pytest.mark.parametrize(
    "token",
    [
        "qa-round-cap=0",
        "qa-round-cap=-1",
        "qa-round-cap=1.5",
        "qa-round-cap=three",
        "qa-round-cap=",
        "qa-round-cap=03",
        "qa-round-cap= 3",
        "3",
        "qa-round-cap",
        "cap=3",
    ],
)
def test_validate_rejects_anything_but_a_positive_integer_with_exit_2(h: Harness, token: str) -> None:
    failed(h.run("validate", token), 2)


# AC3: arm.


def test_arm_writes_a_new_count_with_a_16_hex_count_id(h: Harness) -> None:
    assert ok(h.arm("3")) == "round=0 cap=3 reached=no"
    state = json.loads(h.state_file.read_text())
    assert re.fullmatch(r"[0-9a-f]{16}", state["count_id"])
    assert state["cap"] == 3
    assert state["rounds"] == []
    assert sorted(p.name for p in h.state_file.parent.iterdir()) == [f"{KEY}.json"], "no temp file is left behind"


def test_arm_again_starts_a_new_count(h: Harness) -> None:
    ok(h.arm())
    h.serve(IN_PROGRESS, ["qa-1"])
    assert ok(h.record()) == "round=1 cap=2 reached=no"
    first = json.loads(h.state_file.read_text())["count_id"]
    assert ok(h.arm()) == "round=0 cap=2 reached=no"
    state = json.loads(h.state_file.read_text())
    assert state["count_id"] != first
    assert state["rounds"] == []


def test_arm_makes_no_tracker_call(h: Harness) -> None:
    ok(h.arm())
    assert h.calls() == []


@pytest.mark.parametrize(
    "args",
    [
        ["--story", KEY, "--cap", "0", "--in-progress", IN_PROGRESS],
        ["--story", KEY, "--cap", "two", "--in-progress", IN_PROGRESS],
        ["--story", "../escape", "--cap", "2", "--in-progress", IN_PROGRESS],
        ["--story", "abc-123", "--cap", "2", "--in-progress", IN_PROGRESS],
        ["--story", KEY, "--cap", "2", "--in-progress", ""],
        ["--story", KEY, "--cap", "2"],
    ],
)
def test_arm_rejects_an_invalid_argument_and_writes_nothing(h: Harness, args: list[str]) -> None:
    failed(h.run("arm", *args, "--state-dir", str(h.state_dir)), 2)
    assert not (h.state_dir / "qa-round-cap").exists()


def test_arm_rejects_a_state_dir_that_does_not_exist(h: Harness) -> None:
    missing = h.state_dir / "missing"
    failed(h.run("arm", "--story", KEY, "--cap", "2", "--in-progress", IN_PROGRESS, "--state-dir", str(missing)), 2)
    assert not missing.exists()


def test_a_failed_arm_leaves_an_existing_count_unchanged(h: Harness) -> None:
    ok(h.arm())
    before = h.state_file.read_bytes()
    failed(h.arm("0"), 2)
    assert h.state_file.read_bytes() == before


# AC4: record.


def test_record_with_no_qa_evidence_comment_after_arm_counts_nothing(h: Harness) -> None:
    ok(h.arm())
    h.serve(IN_PROGRESS, ["old-qa", "stamp"])
    assert ok(h.record()) == "round=0 cap=2 reached=no"
    assert json.loads(h.state_file.read_text())["rounds"] == []


def test_record_counts_a_round_and_reaches_the_cap(h: Harness) -> None:
    ok(h.arm())
    h.serve(IN_PROGRESS, ["old-qa", "stamp", "qa-1"])
    assert ok(h.record()) == "round=1 cap=2 reached=no"
    h.serve(IN_PROGRESS, ["old-qa", "stamp", "qa-1", "qa-2"])
    assert ok(h.record()) == "round=2 cap=2 reached=yes"
    rounds = json.loads(h.state_file.read_text())["rounds"]
    assert [r["comment_id"] for r in rounds] == ["comment-qa-1", "comment-qa-2"]


def test_record_with_no_new_qa_evidence_comment_prints_the_unchanged_line(h: Harness) -> None:
    ok(h.arm())
    h.serve(IN_PROGRESS, ["qa-1"])
    assert ok(h.record()) == "round=1 cap=2 reached=no"
    before = h.state_file.read_bytes()
    assert ok(h.record()) == "round=1 cap=2 reached=no"
    assert h.state_file.read_bytes() == before


def test_only_a_comment_whose_first_line_is_the_marker_counts(h: Harness) -> None:
    ok(h.arm())
    h.serve(IN_PROGRESS, ["marker-not-first", "marker-suffix"])
    assert ok(h.record()) == "round=0 cap=2 reached=no"


def test_the_newest_qa_evidence_comment_since_the_last_round_is_the_round(h: Harness) -> None:
    ok(h.arm())
    h.serve(IN_PROGRESS, ["qa-1", "qa-1-later"])
    assert ok(h.record()) == "round=1 cap=2 reached=no"
    assert json.loads(h.state_file.read_text())["rounds"][0]["comment_id"] == "comment-qa-1-later"
    assert ok(h.record()) == "round=1 cap=2 reached=no", "an older comment never counts after a newer one"


@pytest.mark.parametrize("state", ["In Deployment Review", "Done", "Blocked"])
def test_record_outside_in_progress_exits_3_and_records_nothing(h: Harness, state: str) -> None:
    ok(h.arm())
    h.serve(state, ["qa-1"])
    before = h.state_file.read_bytes()
    assert failed(h.record(), 3) == f"state={state}"
    assert h.state_file.read_bytes() == before


def test_record_before_arm_exits_1(h: Harness) -> None:
    failed(h.record(), 1)
    assert not h.state_file.exists()


def test_record_rejects_a_corrupt_state_file(h: Harness) -> None:
    ok(h.arm())
    h.state_file.write_text("{not json")
    failed(h.record(), 1)
    assert h.state_file.read_text() == "{not json"


# AC5: rearm.


def test_rearm_sets_the_cap_to_the_counted_rounds_plus_n_and_rounds_run_on(h: Harness) -> None:
    ok(h.arm())
    h.serve(IN_PROGRESS, ["qa-1"])
    ok(h.record())
    h.serve(IN_PROGRESS, ["qa-1", "qa-2"])
    assert ok(h.record()) == "round=2 cap=2 reached=yes"
    assert ok(h.rearm("1")) == f"state={IN_PROGRESS}"
    state = json.loads(h.state_file.read_text())
    assert state["cap"] == 3
    assert len(state["rounds"]) == 2
    assert ok(h.record()) == "round=2 cap=3 reached=no"
    h.serve(IN_PROGRESS, ["qa-1", "qa-2", "qa-3"])
    assert ok(h.record()) == "round=3 cap=3 reached=yes"


@pytest.mark.parametrize("state", ["Done", "In Deployment Review", "Blocked"])
def test_rearm_outside_in_progress_exits_3_with_the_state_and_writes_nothing(h: Harness, state: str) -> None:
    ok(h.arm())
    h.serve(state, [])
    before = h.state_file.read_bytes()
    assert failed(h.rearm("2"), 3) == f"state={state}"
    assert h.state_file.read_bytes() == before


@pytest.mark.parametrize("rounds", ["0", "-1", "1.5", "x", ""])
def test_rearm_validates_n_as_validate_does(h: Harness, rounds: str) -> None:
    ok(h.arm())
    before = h.state_file.read_bytes()
    failed(h.rearm(rounds), 2)
    assert h.state_file.read_bytes() == before
    assert h.calls() == [], "an invalid N is refused before any tracker read"


def test_rearm_before_arm_exits_1(h: Harness) -> None:
    failed(h.rearm("1"), 1)
    assert not h.state_file.exists()


# AC6: failure, credentials and no writes.


@pytest.mark.parametrize("mode", ["fail", "garbage"])
@pytest.mark.parametrize("subcommand", ["record", "rearm"])
def test_a_failed_tracker_read_exits_1_and_keeps_the_round_history(h: Harness, mode: str, subcommand: str) -> None:
    ok(h.arm())
    h.serve(IN_PROGRESS, ["qa-1"])
    ok(h.record())
    before = h.state_file.read_bytes()
    h.mode = mode
    result = h.record() if subcommand == "record" else h.rearm("1")
    failed(result, 1)
    assert h.state_file.read_bytes() == before
    assert "tracker unavailable" not in result.stderr, "the tracker's own output is not relayed"


def test_a_payload_without_a_state_name_exits_1(h: Harness) -> None:
    ok(h.arm())
    h.issue.write_text(json.dumps({"identifier": KEY, "comments": {"nodes": []}}))
    failed(h.record(), 1)


def test_no_token_reaches_argv_state_stdout_stderr_or_fixtures(h: Harness) -> None:
    h.extra_env = {"LINEAR_API_KEY": SENTINEL, "GITHUB_TOKEN": SENTINEL}
    outputs = [h.arm(), h.run("validate", "qa-round-cap=2")]
    h.serve(IN_PROGRESS, ["qa-1"])
    outputs.append(h.record())
    outputs.append(h.rearm("1"))
    h.mode = "fail"
    outputs.append(h.record())
    for result in outputs:
        assert SENTINEL not in result.stdout + result.stderr
    assert SENTINEL not in h.log.read_text()
    assert SENTINEL not in h.state_file.read_text()
    for fixture in FIXTURES.rglob("*"):
        if fixture.is_file():
            assert SENTINEL not in fixture.read_text()


def test_a_full_arm_record_rearm_sequence_makes_no_mutating_call(h: Harness) -> None:
    ok(h.arm())
    h.serve(IN_PROGRESS, ["qa-1"])
    ok(h.record())
    ok(h.rearm("2"))
    h.serve(IN_PROGRESS, ["qa-1", "qa-2"])
    ok(h.record())
    calls = h.calls()
    assert calls, "the sequence reads the tracker"
    assert all(call == ["issue", "view", KEY, "--json"] for call in calls), calls


# AC7: the QA evidence marker is the parser contract.

MARKER_LINE = re.compile(r"first line is exactly `([^`]+)`")


def test_qa_verification_requires_the_qa_evidence_first_line() -> None:
    section = QA_SKILL.read_text().split("## 4. Adjudicate and record", 1)[1].split("\n## ", 1)[0]
    markers = MARKER_LINE.findall(section)
    assert markers == ["## QA evidence"], markers


def test_a_comment_starting_with_the_qa_verification_marker_is_a_round(h: Harness) -> None:
    (marker,) = MARKER_LINE.findall(QA_SKILL.read_text())
    ok(h.arm())
    h.issue.write_text(
        json.dumps(
            {
                "identifier": KEY,
                "state": {"name": IN_PROGRESS},
                "comments": {
                    "nodes": [{"id": "comment-pinned", "body": marker + "\n\nbody", "createdAt": "2099-02-01T00:00:00.000Z"}]
                },
            }
        )
    )
    assert ok(h.record()) == "round=1 cap=2 reached=no"


# AC8: the skill calls the script, each invocation one simple command with literal values.

INVOCATION = "python3 <skill dir>/scripts/qa-round-cap.py"


def in_progress_bullet() -> str:
    text = STD_SKILL.read_text()
    start = text.index("- **`profile.tracker.states.in_progress`:**")
    end = text.index("\n- **", start + 1)
    return " ".join(text[start:end].split())


def test_the_arguments_entry_calls_validate() -> None:
    text = STD_SKILL.read_text()
    arguments = text.split("## Arguments", 1)[1].split("\n## ", 1)[0]
    assert f"`{INVOCATION} validate qa-round-cap=<n>`" in arguments


def test_the_in_progress_bullet_calls_arm_record_and_rearm() -> None:
    bullet = in_progress_bullet()
    for call in (
        "arm --story <STORY_ID> --cap <n> --in-progress '<profile.tracker.states.in_progress>' --state-dir <scratch>",
        "record --story <STORY_ID> --state-dir <scratch>",
        "rearm --story <STORY_ID> --additional-rounds <N> --state-dir <scratch>",
    ):
        assert f"`{INVOCATION} {call}`" in bullet, call
    calls = re.findall(r"`" + re.escape(INVOCATION) + r" ([^`]*)`", bullet)
    assert len(calls) == 3, calls
    for call in calls:
        for forbidden in ("$(", "`", "&&", "|", ";", "=", "\\"):
            assert forbidden not in call, (forbidden, call)
    assert "relaying its stdout line, never a tracker payload" in bullet
