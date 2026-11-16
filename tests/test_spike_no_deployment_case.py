"""The spike-no-deployment eval case: its grader, its runtime, its run.sh and its recorded results."""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
CASE = ROOT / "skills" / "story-to-done" / "evals" / "spike-no-deployment"
FIXTURES = CASE / "grader-fixtures"
SCENARIOS = ("spike", "no-deployment", "deployed", "conflict", "direct-entry")
# The deployed scenario's fixtures are graded on its path grade; its control grade passes at both commits.
EXPECTATION = {**{scenario: scenario for scenario in SCENARIOS}, "deployed": "deployed-path"}


def grade(run_dir: Path, expectation: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(CASE / "grader.py"), "--run-dir", str(run_dir),
                           "--expectation", expectation], capture_output=True, text=True)


def case_yaml() -> dict:
    return yaml.safe_load((CASE / "case.yaml").read_text())


def copied(tmp_path: Path, scenario: str, name: str = "keeping") -> Path:
    run = tmp_path / f"{scenario}-{name}"
    shutil.copytree(FIXTURES / scenario / name, run)
    return run


def messages(run: Path) -> list[dict]:
    return json.loads((run / "messages.json").read_text())["messages"]


def write_messages(run: Path, kept: list[dict]) -> None:
    (run / "messages.json").write_text(json.dumps({"messages": kept}))


def calls(run: Path) -> list[dict]:
    return [json.loads(line) for line in (run / "actions.jsonl").read_text().splitlines() if line.strip()]


def write_calls(run: Path, recorded: list[dict]) -> None:
    (run / "actions.jsonl").write_text("".join(json.dumps(call) + "\n" for call in recorded))


def failed(result: subprocess.CompletedProcess[str]) -> list[str]:
    assert result.returncode == 1, result.stdout + result.stderr
    return [line for line in result.stdout.splitlines() if line.startswith("FAIL ")]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_the_grader_passes_each_keeping_fixture(scenario: str) -> None:
    result = grade(FIXTURES / scenario / "keeping", EXPECTATION[scenario])
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().splitlines()[-1:] == ["PASS"]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_the_grader_fails_each_baseline_fixture(scenario: str) -> None:
    assert failed(grade(FIXTURES / scenario / "breaking-baseline", EXPECTATION[scenario]))


@pytest.mark.parametrize("name", ["keeping", "breaking-baseline"])
def test_the_deployed_control_passes_at_both_commits(name: str) -> None:
    assert grade(FIXTURES / "deployed" / name, "deployed").returncode == 0


@pytest.mark.parametrize("expectation", sorted(set(EXPECTATION.values()) | {"deployed"}))
def test_the_grader_voids_a_run_with_no_call_record(tmp_path: Path, expectation: str) -> None:
    assert grade(tmp_path, expectation).returncode == 2


@pytest.mark.parametrize("scenario", ["spike", "no-deployment", "deployed", "direct-entry", "conflict"])
def test_the_grader_fails_a_run_that_never_ran_the_selector(tmp_path: Path, scenario: str) -> None:
    run = copied(tmp_path, scenario)
    (run / "selector.jsonl").unlink()
    assert any("select-path.py" in line for line in failed(grade(run, EXPECTATION[scenario])))


def test_the_grader_fails_a_selector_run_that_printed_another_path(tmp_path: Path) -> None:
    run = copied(tmp_path, "no-deployment")
    entry = json.loads((run / "selector.jsonl").read_text())
    (run / "selector.jsonl").write_text(json.dumps({**entry, "stdout": "spike\n"}) + "\n")
    assert any("select-path.py" in line for line in failed(grade(run, "no-deployment")))


def test_the_grader_fails_a_selector_run_after_the_first_message(tmp_path: Path) -> None:
    run = copied(tmp_path, "spike")
    entry = json.loads((run / "selector.jsonl").read_text())
    (run / "selector.jsonl").write_text(json.dumps({**entry, "at": "2999-01-01T00:00:00Z"}) + "\n")
    assert any("select-path.py" in line for line in failed(grade(run, "spike")))


@pytest.mark.parametrize("wrapper", ["```\n{line}\n```", "~~~text\n{line}\n~~~", "> {line}"])
def test_a_path_line_in_a_code_block_or_quotation_does_not_count(tmp_path: Path, wrapper: str) -> None:
    run = copied(tmp_path, "no-deployment")
    kept = messages(run)
    for message in kept:
        message["text"] = message["text"].replace("path: no-deployment", wrapper.format(line="path: no-deployment"))
    write_messages(run, kept)
    assert any("path line" in line for line in failed(grade(run, "no-deployment")))


def test_the_deployed_control_fails_a_second_engineer_launch(tmp_path: Path) -> None:
    run = copied(tmp_path, "deployed")
    kept, recorded = messages(run), calls(run)
    kept.append({"id": len(kept) + 1, "channel": "engineer", "label": "senior-engineer-2", "text": kept[0]["text"]})
    recorded.append({"action": "engineer-launch", "at": recorded[-1]["at"], "label": "senior-engineer-2",
                     "message_id": len(kept)})
    write_messages(run, kept)
    write_calls(run, recorded)
    assert any("senior-engineer session" in line for line in failed(grade(run, "deployed")))


def test_the_deployed_control_fails_a_brief_with_no_story(tmp_path: Path) -> None:
    run = copied(tmp_path, "deployed")
    kept = messages(run)
    kept[-1]["text"] = kept[-1]["text"].replace("ABC-123", "the story")
    write_messages(run, kept)
    assert any("names ABC-123" in line for line in failed(grade(run, "deployed")))


@pytest.mark.parametrize("denial", ["Do not verify on dev.", "There is no dev environment.", "dev isn't deployed."])
def test_a_qa_brief_that_denies_the_environment_fails(tmp_path: Path, denial: str) -> None:
    run = copied(tmp_path, "deployed")
    kept = messages(run)
    qa = next(message for message in kept if message["channel"] == "qa")
    qa["text"] = "\n".join(denial if re.search(r"(?<![A-Za-z0-9_-])dev(?![A-Za-z0-9_-])", line) else line
                           for line in qa["text"].splitlines())
    write_messages(run, kept)
    assert any("environment dev" in line for line in failed(grade(run, "deployed")))


def edit_brief(run: Path, channel: str, edit) -> None:
    kept = messages(run)
    for message in kept:
        if message["channel"] == channel:
            message["text"] = edit(message["text"])
    write_messages(run, kept)


def test_the_deployed_path_grade_holds_every_control_check_and_the_path_lines() -> None:
    run = FIXTURES / "deployed" / "keeping"
    control = grade(run, "deployed").stdout.splitlines()[:-1]
    path = grade(run, "deployed-path").stdout.splitlines()[:-1]
    assert control and set(control) <= set(path)
    assert sum("`path: deployed`" in line for line in path) == 3


def test_deployed_briefs_without_a_path_line_pass_the_control_and_fail_the_path_grade(tmp_path: Path) -> None:
    run = copied(tmp_path, "deployed")
    for channel in ("engineer", "qa"):
        edit_brief(run, channel, lambda text: text.replace("path: deployed\n", ""))
    assert grade(run, "deployed").returncode == 0
    assert sum("path line" in line for line in failed(grade(run, "deployed-path"))) == 2


@pytest.mark.parametrize("environment", ["Environment under test: dev; no production changes.",
                                         "Environment under test: dev, not production."])
def test_a_denial_in_another_clause_keeps_the_environment(tmp_path: Path, environment: str) -> None:
    run = copied(tmp_path, "deployed")
    edit_brief(run, "qa", lambda text: text.replace("Environment under test: dev.", environment))
    assert grade(run, "deployed").returncode == 0


@pytest.mark.parametrize("edit", [
    lambda text: text + "\nVerify on production, not the dev environment.\n",
    lambda text: text.replace("Environment under test: dev.", "Health check: https://dev.example.com/health."),
    lambda text: text.replace("Environment under test: dev.", "Environment under test: dev.example.com."),
])
def test_a_qa_brief_that_denies_or_only_hosts_the_environment_fails(tmp_path: Path, edit) -> None:
    run = copied(tmp_path, "deployed")
    edit_brief(run, "qa", edit)
    assert any("environment dev" in line for line in failed(grade(run, "deployed")))


@pytest.mark.parametrize("edit", [
    lambda text: text.replace("ABC-123", "https://example.com/ABC-123"),
    lambda text: text.replace("ABC-123", "ops@ABC-123"),
    lambda text: text.replace("Load and follow the `qa-verification` skill", "Do not load the `qa-verification` skill")
    .replace("that `qa-verification` defines", "that QA defines"),
])
def test_a_brief_that_names_its_story_or_skill_only_in_a_url_or_a_denial_fails(tmp_path: Path, edit) -> None:
    run = copied(tmp_path, "deployed")
    edit_brief(run, "qa", edit)
    assert any("the qa brief" in line and "names ABC-123" in line for line in failed(grade(run, "deployed")))


DELIVERABLE = "https://docs.example.com/abc-123/yaml-parser-comparison"
COMMIT = "4e1c2a9b7d3f5e6a8c0b1d2e3f4a5b6c7d8e9f01"


@pytest.mark.parametrize(("scenario", "old", "new"), [
    ("spike", DELIVERABLE, f"(do not verify {DELIVERABLE})"),
    ("spike", DELIVERABLE, f"{DELIVERABLE}-draft"),
    ("no-deployment", COMMIT, f"https://example.com/{COMMIT}"),
    ("no-deployment", COMMIT, f"(do not use {COMMIT})"),
    ("direct-entry", COMMIT, f"https://example.com/commit/{COMMIT[:7]}"),
])
def test_a_qa_brief_that_names_its_target_only_in_a_denial_or_a_longer_url_fails(
        tmp_path: Path, scenario: str, old: str, new: str) -> None:
    run = copied(tmp_path, scenario)
    edit_brief(run, "qa", lambda text: text.replace(old, new))
    assert any("the QA brief" in line for line in failed(grade(run, scenario)))


@pytest.mark.parametrize("scenario", ["spike", "no-deployment", "direct-entry", "conflict"])
def test_a_run_that_read_no_story_before_sending_fails(tmp_path: Path, scenario: str) -> None:
    run = copied(tmp_path, scenario)
    write_calls(run, [call for call in calls(run) if call["action"] != "tracker-read"])
    assert any("read on the tracker" in line for line in failed(grade(run, EXPECTATION[scenario])))


@pytest.mark.parametrize("scenario", ["spike", "no-deployment", "deployed", "direct-entry"])
def test_a_user_message_on_a_resolved_path_fails(tmp_path: Path, scenario: str) -> None:
    run = copied(tmp_path, scenario)
    kept, recorded = messages(run), calls(run)
    kept.append({"id": len(kept) + 1, "channel": "user", "label": None, "text": "Done."})
    recorded.append({"action": "user-message", "at": recorded[-1]["at"], "message_id": len(kept)})
    write_messages(run, kept)
    write_calls(run, recorded)
    assert any("message went to the user" in line for line in failed(grade(run, EXPECTATION[scenario])))


def test_a_conflict_message_that_names_no_choice_fails(tmp_path: Path) -> None:
    run = copied(tmp_path, "conflict")
    kept = messages(run)
    kept[0]["text"] = "Story ABC-123 is blocked; please advise."
    write_messages(run, kept)
    assert any("names the three paths" in line for line in failed(grade(run, "conflict")))


def test_an_unreadable_selector_record_voids_the_run(tmp_path: Path) -> None:
    run = copied(tmp_path, "spike")
    (run / "selector.jsonl").write_text('{"argv": "x"}\n')
    result = grade(run, "spike")
    assert result.returncode == 2 and result.stdout == "", result.stdout + result.stderr


def runtime_workspace(tmp_path: Path, scenario: str) -> Path:
    """A run directory as run.sh lays it out, with the scenario directory written into the runtime copy."""
    work = tmp_path / "run" / "workspace"
    work.mkdir(parents=True)
    source = (CASE / "runtime" / "story-runtime").read_text()
    (work / "story-runtime").write_text(
        source.replace("\nSCENARIO_DIR = None\n", f"\nSCENARIO_DIR = {str(CASE / 'scenarios' / scenario)!r}\n"))
    return work


def runtime(work: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(work / "story-runtime"), *args], cwd=work,
                          capture_output=True, text=True)


def test_the_runtime_reads_its_scenario_from_its_own_copy(tmp_path: Path) -> None:
    work = runtime_workspace(tmp_path, "spike")
    (work.parent / "scenario-path").write_text(f"{CASE / 'scenarios' / 'deployed'}\n")
    result = runtime(work, "tracker-read")
    assert result.returncode == 0, result.stderr
    assert "[Spike]" in result.stdout


def test_the_runtime_source_names_no_scenario(tmp_path: Path) -> None:
    work = tmp_path / "workspace"
    work.mkdir()
    shutil.copy2(CASE / "runtime" / "story-runtime", work)
    result = runtime(work, "tracker-read")
    assert result.returncode != 0 and "harness error" in result.stderr
    assert not (tmp_path / "actions.jsonl").exists()


def run_sh(tmp_path: Path, scenario: str, agent: str) -> subprocess.CompletedProcess[str]:
    script = tmp_path / "agent.sh"
    script.write_text(agent)
    return subprocess.run(["bash", str(CASE / "run.sh"), str(ROOT), scenario, str(tmp_path / "run")], cwd=tmp_path,
                          capture_output=True, text=True,
                          env={"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin", "EVAL_AGENT_CMD": f"bash {script}"})


SELECTING_AGENT = """\
set -eu
work="$(dirname "$2")"
"$work/story-runtime" tracker-read > /dev/null
python3 "$PWD/skills/story-to-done/scripts/select-path.py" '--title=[Spike] X' --label Spike > /dev/null
"""


def test_run_sh_records_each_selector_run(tmp_path: Path) -> None:
    result = run_sh(tmp_path, "spike", SELECTING_AGENT)
    assert result.returncode == 1, result.stdout + result.stderr
    entries = [json.loads(line) for line in (tmp_path / "run" / "selector.jsonl").read_text().splitlines()]
    assert [(entry["argv"][:1], entry["stdout"]) for entry in entries] == [(["--title=[Spike] X"], "spike\n")]
    assert "PASS select-path.py printed `spike`" in result.stdout


def test_run_sh_grades_a_deployed_run_on_its_path_grade_too(tmp_path: Path) -> None:
    result = run_sh(tmp_path, "deployed", SELECTING_AGENT)
    assert result.returncode == 1, result.stdout + result.stderr
    assert (tmp_path / "run" / "grader-output.txt").is_file()
    assert "`path: deployed`" in (tmp_path / "run" / "grader-path-output.txt").read_text()


@pytest.mark.parametrize("target", ["workspace/story-runtime", "workspace/profile.yaml", "selector-hook/sitecustomize.py"])
def test_run_sh_voids_a_run_that_changed_what_it_was_given(tmp_path: Path, target: str) -> None:
    agent = SELECTING_AGENT + f'printf "\\n# changed\\n" >> "$(dirname "$work")/{target}"\n'
    result = run_sh(tmp_path, "spike", agent)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "changed the case or the runtime" in result.stderr
    assert not (tmp_path / "run" / "grader-output.txt").exists()


def test_run_sh_normalizes_the_signing_key_name_before_grading(tmp_path: Path) -> None:
    name = "user." + "signingkey"
    agent = SELECTING_AGENT + f'printf "never pass -c {name}, or a gpg setting\\n" > "$work/brief.md"\n' \
        '"$work/story-runtime" engineer-launch --label senior-engineer --message brief.md > /dev/null\n'
    result = run_sh(tmp_path, "spike", agent)
    assert result.returncode == 1, result.stdout + result.stderr
    text = (tmp_path / "run" / "messages.json").read_text()
    assert name not in text and "user.{signingkey}" in text


def test_case_yaml_is_a_discriminating_case_on_every_scenario() -> None:
    case = case_yaml()
    assert case["kind"] == "discriminating"
    assert {scenario["name"] for scenario in case["scenarios"]} == set(SCENARIOS)


@pytest.mark.parametrize("version", ["baseline", "candidate"])
def test_the_results_grade_every_scenario_at_both_commits(version: str) -> None:
    case = case_yaml()
    commit = case[version]["commit"][:7]
    graded = {}
    for path in (CASE / "results").glob(f"*-{version}-{commit}-*.json"):
        record = json.loads(path.read_text())
        if record["outcome"] != "void":
            scenario = next(name for name in SCENARIOS if f"-{name}-{commit}-" in path.name)
            graded[scenario] = graded.get(scenario, 0) + 1
    assert graded == {scenario: 3 for scenario in SCENARIOS}
