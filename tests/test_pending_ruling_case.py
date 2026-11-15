"""The pending-ruling-not-sent-to-engineer eval case: its grader and the files its agent reads."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CASE = ROOT / "skills" / "story-to-done" / "evals" / "pending-ruling-not-sent-to-engineer"
FIXTURES = CASE / "grader-fixtures"
SCENARIOS = ("split-verdict", "plain-failure")
BANNED = re.compile(r"pending (?:owner )?ruling", re.IGNORECASE)


def grade(run_dir: Path, expectation: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CASE / "grader.py"), "--run-dir", str(run_dir),
                           "--expectation", expectation], capture_output=True, text=True)


def fixtures(prefix: str) -> list[tuple[str, Path]]:
    return [(scenario, path) for scenario in SCENARIOS
            for path in sorted((FIXTURES / scenario).glob(f"{prefix}*")) if path.is_dir()]


def test_every_scenario_has_a_breaking_and_a_keeping_fixture() -> None:
    for scenario in SCENARIOS:
        assert any(path for name, path in fixtures("breaking-") if name == scenario), scenario
        assert any(path for name, path in fixtures("keeping") if name == scenario), scenario


@pytest.mark.parametrize(("scenario", "fixture"), fixtures("breaking-"), ids=lambda value: getattr(value, "name", value))
def test_the_grader_fails_each_breaking_fixture(scenario: str, fixture: Path) -> None:
    result = grade(fixture, scenario)
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout.strip().splitlines()[-1] == "FAIL"


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


def agent_read_files(case_dir: Path) -> list[Path]:
    """The case-authored files the agent reads, which must not name the status or the party."""
    return [case_dir / "prompt.md", case_dir / "rerun.md",
            *sorted(case_dir.glob("scenarios/*/scenario.md")), *sorted(case_dir.glob("runtime/*.md"))]


def banned_phrases(files: list[Path]) -> list[str]:
    return [f"{path.relative_to(path.parents[0])}: {match.group(0)!r}"
            for path in files for match in BANNED.finditer(path.read_text())]


def test_no_file_the_agent_reads_names_the_banned_phrases() -> None:
    files = agent_read_files(CASE)
    assert len(files) == 2 + len(SCENARIOS) + 1
    assert banned_phrases(files) == []


@pytest.mark.parametrize("phrase", ["pending owner ruling", "Pending Ruling", "PENDING OWNER RULING"])
@pytest.mark.parametrize("target", ["prompt.md", "rerun.md", "scenarios/split-verdict/scenario.md",
                                    "runtime/story-runtime.md"])
def test_the_phrase_scan_catches_a_banned_phrase(tmp_path: Path, phrase: str, target: str) -> None:
    for path in agent_read_files(CASE):
        copy = tmp_path / path.relative_to(CASE)
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_text(path.read_text())
    assert banned_phrases(agent_read_files(tmp_path)) == []
    with (tmp_path / target).open("a") as handle:
        handle.write(f"\nThe item is {phrase}.\n")
    assert banned_phrases(agent_read_files(tmp_path)) != []
