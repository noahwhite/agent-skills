"""The pending-ruling-not-sent-to-engineer eval case: its grader, its runtime and the files its agent reads."""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
CASE = ROOT / "skills" / "story-to-done" / "evals" / "pending-ruling-not-sent-to-engineer"
FIXTURES = CASE / "grader-fixtures"
SCENARIOS = ("split-verdict", "plain-failure")
BANNED = re.compile(r"pending (?:owner )?ruling", re.IGNORECASE)
# A line naming the split item must not say which party it goes to.
PENDING_ITEM = re.compile(r"(?<![A-Za-z0-9_])AC4(?![A-Za-z0-9_])")
PARTY = re.compile(r"\b(?:users?|engineers?|QA|owners?)\b", re.IGNORECASE)


def grade(run_dir: Path, expectation: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CASE / "grader.py"), "--run-dir", str(run_dir),
                           "--expectation", expectation], capture_output=True, text=True)


def fixtures(prefix: str) -> list[tuple[str, Path]]:
    return [(scenario, path) for scenario in SCENARIOS
            for path in sorted((FIXTURES / scenario).glob(f"{prefix}*")) if path.is_dir()]


def case_yaml() -> dict:
    return yaml.safe_load((CASE / "case.yaml").read_text())


def test_every_scenario_has_a_breaking_and_a_keeping_fixture() -> None:
    for scenario in SCENARIOS:
        assert any(path for name, path in fixtures("breaking-") if name == scenario), scenario
        assert any(path for name, path in fixtures("keeping") if name == scenario), scenario


@pytest.mark.parametrize(("scenario", "fixture"), fixtures("breaking-"), ids=lambda value: getattr(value, "name", value))
def test_the_grader_fails_each_breaking_fixture(scenario: str, fixture: Path) -> None:
    result = grade(fixture, scenario)
    assert result.returncode == 1, result.stdout + result.stderr
    lines = result.stdout.strip().splitlines()
    assert lines[-1] == "FAIL"
    assert any(line.startswith("FAIL ") for line in lines[:-1]), result.stdout


@pytest.mark.parametrize(("scenario", "fixture"), fixtures("keeping"), ids=lambda value: getattr(value, "name", value))
def test_the_grader_passes_each_keeping_fixture(scenario: str, fixture: Path) -> None:
    result = grade(fixture, scenario)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().splitlines()[-1] == "PASS"


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_the_grader_exits_2_on_a_run_with_no_call_record(tmp_path: Path, scenario: str) -> None:
    assert grade(tmp_path, scenario).returncode == 2


def test_the_carried_round_check_fails_on_its_own() -> None:
    result = grade(FIXTURES / "split-verdict" / "breaking-carried-handback", "split-verdict")
    assert re.search(r"^FAIL .*after QA round 2", result.stdout, re.MULTILINE), result.stdout


def copied_fixture(tmp_path: Path, name: str) -> Path:
    run = tmp_path / name
    shutil.copytree(FIXTURES / "split-verdict" / name, run)
    return run


def test_a_duplicate_message_id_voids_the_run(tmp_path: Path) -> None:
    run = copied_fixture(tmp_path, "breaking-engineer-brief")
    kept = json.loads((run / "messages.json").read_text())
    kept["messages"].append({"id": 3, "channel": "engineer", "label": "senior-engineer-round-1", "text": "Fix AC2"})
    (run / "messages.json").write_text(json.dumps(kept))
    result = grade(run, "split-verdict")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "twice" in result.stderr


@pytest.mark.parametrize("damage", ["truncated-actions", "list-messages", "no-text", "no-qa-round"])
def test_an_unreadable_record_voids_the_run(tmp_path: Path, damage: str) -> None:
    run = copied_fixture(tmp_path, "keeping")
    actions, messages = run / "actions.jsonl", run / "messages.json"
    if damage == "truncated-actions":
        actions.write_text(actions.read_text()[:-20])
    elif damage == "list-messages":
        messages.write_text("[]")
    elif damage == "no-text":
        kept = json.loads(messages.read_text())
        del kept["messages"][1]["text"]
        messages.write_text(json.dumps(kept))
    else:
        calls = [json.loads(line) for line in actions.read_text().splitlines()]
        del calls[0]["qa_round"]
        actions.write_text("".join(json.dumps(call) + "\n" for call in calls))
    result = grade(run, "split-verdict")
    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize(("suffix", "graded_as_naming"), [("", True), ("x", False), ("_foo", False), ("0", False)])
def test_the_grader_matches_the_item_as_a_whole_token(tmp_path: Path, suffix: str, graded_as_naming: bool) -> None:
    run = copied_fixture(tmp_path, "keeping")
    kept = json.loads((run / "messages.json").read_text())
    kept["messages"][2]["text"] += f" See also AC4{suffix}."
    (run / "messages.json").write_text(json.dumps(kept))
    assert grade(run, "split-verdict").returncode == (1 if graded_as_naming else 0)


def runtime_run(tmp_path: Path, scenario: str) -> Path:
    run = tmp_path / "run"
    shutil.copytree(CASE / "scenarios" / scenario, run, ignore=shutil.ignore_patterns("checklists"))
    shutil.copytree(CASE / "scenarios" / scenario / "checklists", run, dirs_exist_ok=True)
    for name in ("story-runtime", "story-runtime.md"):
        shutil.copy2(CASE / "runtime" / name, run / name)
    return run


def runtime(run: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(run / "story-runtime"), *args], cwd=cwd, capture_output=True, text=True)


def test_the_runtime_reads_a_relative_file_from_the_run_directory(tmp_path: Path) -> None:
    run = runtime_run(tmp_path, "split-verdict")
    elsewhere = tmp_path / "checkout"
    elsewhere.mkdir()
    (run / "msg.md").write_text("AC4 needs a ruling.")
    sent = runtime(run, elsewhere, "user-message", "--message", "msg.md")
    assert sent.returncode == 0, sent.stderr
    read = runtime(run, elsewhere, "read", "--path", "senior-engineer/senior-engineer-todo.md")
    assert read.returncode == 0, read.stderr
    calls = [json.loads(line) for line in (run / "actions.jsonl").read_text().splitlines()]
    assert [call["action"] for call in calls] == ["user-message", "read"]
    assert calls[1]["path"] == "senior-engineer/senior-engineer-todo.md"


def test_the_runtime_never_reuses_a_message_id(tmp_path: Path) -> None:
    run = runtime_run(tmp_path, "split-verdict")
    (run / "messages.json").write_text(json.dumps({"messages": [{"id": 5, "channel": "user", "label": None,
                                                                 "text": "earlier"}]}))
    (run / "msg.md").write_text("later")
    assert runtime(run, run, "user-message", "--message", "msg.md").returncode == 0
    ids = [message["id"] for message in json.loads((run / "messages.json").read_text())["messages"]]
    assert ids == [5, 6]


def test_the_runtime_serves_each_handback_only_from_its_state(tmp_path: Path) -> None:
    run = runtime_run(tmp_path, "split-verdict")
    (run / "msg.md").write_text("Fix AC2.")
    early = runtime(run, run, "engineer-launch", "--label", "senior-engineer-early", "--message", "msg.md")
    assert "has not handed back" in early.stdout
    assert json.loads((run / "story-state.json").read_text())["engineer_handbacks"] == 0
    qa = runtime(run, run, "qa-launch", "--label", "qa-round-1", "--message", "msg.md")
    assert "AC2" in qa.stdout
    assert json.loads((run / "story-state.json").read_text())["state"] == "In Progress"


def test_the_runtime_leaves_the_scenario_checklist_as_it_is(tmp_path: Path) -> None:
    run = runtime_run(tmp_path, "split-verdict")
    checklist = run / "senior-engineer" / "senior-engineer-todo.md"
    before = checklist.read_text()
    (run / "msg.md").write_text("Run QA.")
    assert runtime(run, run, "qa-launch", "--label", "qa-round-1", "--message", "msg.md").returncode == 0
    (run / "msg.md").write_text("Fix AC2.")
    assert runtime(run, run, "engineer-launch", "--label", "senior-engineer", "--message", "msg.md").returncode == 0
    assert checklist.read_text() == before


def test_case_yaml_pins_the_full_commit_shas() -> None:
    case = case_yaml()
    for version, prefix in (("baseline", "9bd3e16"), ("candidate", "6838b35")):
        commit = case[version]["commit"]
        assert re.fullmatch(r"[0-9a-f]{40}", commit), commit
        assert commit.startswith(prefix), commit


def test_only_the_control_scenario_carries_control() -> None:
    scenarios = {scenario["name"]: scenario for scenario in case_yaml()["scenarios"]}
    assert set(scenarios) == set(SCENARIOS)
    assert scenarios["plain-failure"].get("control")
    assert "control" not in scenarios["split-verdict"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_every_record_rounds_json_names_is_in_the_scenario(scenario: str) -> None:
    rounds = json.loads((CASE / "scenarios" / scenario / "rounds.json").read_text())
    records = [entry["record"] for kind in ("qa_rounds", "engineer_handbacks") for entry in rounds[kind]]
    assert records
    for record in records:
        assert (CASE / "scenarios" / scenario / record).is_file(), record


@pytest.mark.parametrize("record", ["qa-round-1.md", "qa-round-2.md", "qa-round-3.md"])
def test_each_split_verdict_qa_record_splits_ac4_between_two_readings(record: str) -> None:
    text = (CASE / "scenarios" / "split-verdict" / record).read_text()
    assert re.search(r"^\| AC4 \| `pending owner ruling` \|", text, re.MULTILINE), record
    assert re.search(r"^- Reading 1: .*Verdict: failed\.$", text, re.MULTILINE), record
    assert re.search(r"^- Reading 2: .*Verdict: verified\.$", text, re.MULTILINE), record


def agent_read_files(case_dir: Path) -> list[Path]:
    """The case-authored files the agent reads, which must not name the status or the party."""
    return [case_dir / "prompt.md", case_dir / "rerun.md",
            *sorted(case_dir.glob("scenarios/*/scenario.md")), *sorted(case_dir.glob("runtime/*.md"))]


def banned_phrases(case_dir: Path) -> list[str]:
    hits = []
    for path in agent_read_files(case_dir):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            where = f"{path.relative_to(case_dir)}:{number}"
            hits += [f"{where}: {match.group(0)!r}" for match in BANNED.finditer(line)]
            if PENDING_ITEM.search(line) and PARTY.search(line):
                hits.append(f"{where}: names the party for AC4: {line.strip()!r}")
    return hits


def test_the_agent_read_files_are_the_banned_files() -> None:
    names = [str(path.relative_to(CASE)) for path in agent_read_files(CASE)]
    assert names == ["prompt.md", "rerun.md", "scenarios/plain-failure/scenario.md",
                     "scenarios/split-verdict/scenario.md", "runtime/story-runtime.md"]


def test_no_file_the_agent_reads_names_the_banned_phrases() -> None:
    assert banned_phrases(CASE) == []


@pytest.mark.parametrize("line", ["The item is pending owner ruling.", "The item is Pending Ruling.",
                                  "The item is PENDING OWNER RULING.", "Send AC4 to the user.",
                                  "AC4 goes back to the senior engineer."])
@pytest.mark.parametrize("target", ["prompt.md", "rerun.md", "scenarios/split-verdict/scenario.md",
                                    "runtime/story-runtime.md"])
def test_the_phrase_scan_catches_a_banned_phrase(tmp_path: Path, line: str, target: str) -> None:
    for path in agent_read_files(CASE):
        copy = tmp_path / path.relative_to(CASE)
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_text(path.read_text())
    assert banned_phrases(tmp_path) == []
    with (tmp_path / target).open("a") as handle:
        handle.write(f"\n{line}\n")
    assert banned_phrases(tmp_path) != []
