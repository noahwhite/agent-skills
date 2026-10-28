"""Contract checks for the story-to-done skill."""

import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "story-to-done" / "SKILL.md"
MANIFEST = json.loads((ROOT / "skills.json").read_text())


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def test_skill_file_exists() -> None:
    assert SKILL.is_file(), f"missing {SKILL.relative_to(ROOT)}"


def test_manifest_registers_skill() -> None:
    required = {"todo-tracking", "linear", "code-review", "secrets"}
    assert required <= set(MANIFEST["skills"]["story-to-done"])


def test_todo_tracking_has_seed_entry() -> None:
    text = (ROOT / "shared" / "todo-tracking.md").read_text()
    assert "- **story-to-done:**" in text


def test_readme_lists_skill_in_table() -> None:
    row = "| [`story-to-done`](skills/story-to-done/SKILL.md) |"
    in_fence = False
    in_skills = False
    found = False
    for line in (ROOT / "README.md").read_text().splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if line.startswith("## "):
            in_skills = line.strip() == "## Skills"
            continue
        if in_skills and not in_fence and line.startswith(row):
            found = True
    assert found, "missing story-to-done row from the README Skills table"


def test_skill_links_to_required_references() -> None:
    text = SKILL.read_text()
    for name in ("profile", "runtimes", "todo-tracking", "linear", "code-review", "secrets", "metrics"):
        assert f"](references/{name}.md)" in text, name


def test_arguments_table_pins_each_default() -> None:
    body = section(SKILL.read_text(), "Arguments")
    for row in (
        "| `engineer-model` | the senior engineer's model | Sonnet 5.5 (`claude-sonnet-5-5`) |",
        "| `engineer-effort` | the senior engineer's reasoning effort | `high` |",
        "| `qa-model` | the QA agent's model | Opus 5.5 (`claude-opus-5-5`) |",
        "| `qa-effort` | the QA agent's reasoning effort | `high` |",
    ):
        assert row in body, f"defaults table missing: {row}"
    for phrase in (
        "`STORY_ID` is required",
        "never guess a story number",
        "An argument left out takes its default.",
        "`low`, `medium`, `high`, `xhigh`, or `max`",
        "never substitute another model or level",
    ):
        assert phrase in body, f"arguments missing: {phrase}"


def test_senior_engineer_uses_its_model_and_engineering_workflow() -> None:
    body = section(SKILL.read_text(), "2. Senior engineer: implement to deployment review")
    for phrase in (
        "Spawn a clean, neutral subagent",
        "on `engineer-model` at `engineer-effort`",
        "load and follow `engineering-workflow`",
        "`profile.tracker.states.in_deployment_review`",
        "This skill assigns merge approval to no manager",
        "read the story yourself and confirm",
    ):
        assert phrase in body, f"step 2 missing: {phrase}"


def test_each_qa_round_is_a_new_agent_with_a_minimal_brief() -> None:
    body = section(SKILL.read_text(), "3. QA agent: verify the deployed story")
    for phrase in (
        "Spawn a new clean, neutral subagent on `qa-model` at `qa-effort` for every QA round",
        "never resume an earlier QA agent",
        "load and follow `qa-verification`",
        "Never give it the senior engineer's handback beyond the environment",
        "an earlier round's verdicts",
        "the verdict you expect",
    ):
        assert phrase in body, f"step 3 missing: {phrase}"


def state_bullets(body: str) -> dict[str, str]:
    """Map each `- **<label>:**` bullet in a section to its text, continuation lines included."""
    bullets: dict[str, str] = {}
    label = None
    for line in body.splitlines():
        match = re.match(r"^- \*\*(.+?):\*\*", line)
        if match:
            label = match.group(1)
            assert label not in bullets, f"duplicate bullet: {label}"
            bullets[label] = line
        elif label and line.startswith("  "):
            bullets[label] += "\n" + line
        else:
            label = None
    return bullets


def in_order(text: str, *phrases: str) -> bool:
    positions = [text.find(phrase) for phrase in phrases]
    return -1 not in positions and positions == sorted(positions)


def test_qa_outcome_has_one_branch_per_state() -> None:
    bullets = state_bullets(section(SKILL.read_text(), "4. Act on the QA outcome"))
    assert set(bullets) == {
        "`profile.tracker.states.done`",
        "`profile.tracker.states.in_progress`",
        "`profile.tracker.states.in_deployment_review`",
        "`profile.tracker.states.blocked`",
        "Any other state",
    }
    assert "report it and stop" in bullets["Any other state"]
    assert "report the blocking story and stop" in bullets["`profile.tracker.states.blocked`"]
    assert in_order(
        bullets["`profile.tracker.states.in_deployment_review`"],
        "QA is not finished",
        "Report exactly what remains and who owns it, and stop",
    )


def test_done_branch_checks_the_completion_record() -> None:
    done = state_bullets(section(SKILL.read_text(), "4. Act on the QA outcome"))[
        "`profile.tracker.states.done`"
    ]
    assert in_order(
        done,
        "confirm the completion record before you accept it",
        "every AC and DoD box is ticked",
        "QA's handback rules every item verified",
        "when `profile.qa.evidence_dir` is set, the evidence PR is merged",
        "go to step 5",
        "report the mismatch and stop",
    )
    close_out = section(SKILL.read_text(), "5. Close out")
    assert "with the completion record step 4 checks" in close_out


def test_failed_items_go_back_to_the_engineer_before_qa_reruns() -> None:
    reopened = state_bullets(section(SKILL.read_text(), "4. Act on the QA outcome"))[
        "`profile.tracker.states.in_progress`"
    ]
    assert in_order(
        reopened,
        "Those failed items are the issues to fix.",
        "Hand them back to the senior engineer",
        "add each failed item as QA recorded it",
        "fix them through `engineering-workflow` on this story",
        "Confirm that state as step 2 does",
        "run step 3 again with a new QA agent",
    )


def test_disputes_and_incidentals_are_not_ruled_in_the_loop() -> None:
    body = section(SKILL.read_text(), "4. Act on the QA outcome")
    assert "do not relay its argument to a QA agent and do not rule on it yourself" in body
    assert "are not fixed in this loop" in body


def test_orchestrator_never_sets_the_story_state() -> None:
    text = SKILL.read_text()
    phrases = (
        "move the story",
        "move it to",
        "set the story",
        "mark the story",
        "mark it done",
        "transition the story",
        "update the story",
        "update the issue",
        "update the status",
        "status to",
    )
    for heading in (
        "0. Track everything on a todo list",
        "1. Read the story and pick the starting point",
        "2. Senior engineer: implement to deployment review",
        "3. QA agent: verify the deployed story",
        "4. Act on the QA outcome",
        "5. Close out",
    ):
        body = section(text, heading).lower()
        for phrase in phrases:
            assert phrase not in body, f"{heading} tells the orchestrator to set the state: {phrase}"


def test_only_qa_moves_the_story_to_done() -> None:
    body = section(SKILL.read_text(), "Boundaries")
    assert "Only a QA agent's closing decision moves the story to Done" in body
    assert "never mark it done yourself, and never on merge alone" in body


def test_runtimes_maps_reasoning_effort() -> None:
    text = (ROOT / "shared" / "runtimes.md").read_text()
    assert "| Choose a subagent's reasoning effort | `effort` parameter" in text
    assert "provider/model#variant" in text
    assert "V1" in text and "`variant:`" in text
    assert "never substitute another level" in text
    assert "`CLAUDE_CODE_EFFORT_LEVEL` overrides every subagent's effort" in text
    assert "`CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is an on/off flag" in text
    assert "a subagent runs on `CLAUDE_CODE_SUBAGENT_MODEL`, or on the main session's model" in text
    assert "if it differs from the effort a skill asks for, stop and say so" in text
    assert "if that model differs from the one a skill asks for, stop and say so" in text
    assert in_order(
        text,
        "a fork and a skill that runs in a subagent with `model: inherit` still run on the main session's model",
        "the built-in Explore subagent runs on its own listed model when only the flag is set",
        "never use one of these for a model-pinned role",
    )


def test_resumed_story_names_the_qa_environment() -> None:
    body = section(SKILL.read_text(), "3. QA agent: verify the deployed story")
    assert "When step 2 did not run in this engagement" in body
    assert "leave it out so `qa-verification` picks its default" in body


def test_both_roles_get_nesting_or_shell_launched_reviews() -> None:
    body = section(SKILL.read_text(), "2. Senior engineer: implement to deployment review")
    assert in_order(
        body,
        "so does the QA agent in step 3",
        "give both delegated agents nesting per that runtime map",
        "launch their review roles as shell commands",
        "does not fit this skill",
        "If neither works, stop and say so.",
    )


def test_nesting_guidance_stays_runtime_neutral() -> None:
    body = SKILL.read_text().split("\n---\n", 1)[1]
    assert "subagent_depth" not in body
    assert "grant `task`" not in body
    assert "On opencode" not in body


# SKL-48: the `metrics` switch, its off path, and its wiring.

METRICS_ROW = "| `metrics` | whether the run collects and reports run metrics | `off` |"
METRICS_LINE_SENTENCE = (
    "Write the four resolved model and effort values and the `metrics: on|off` line at the top of "
    "your todo list and in the closing report of every end state"
)


def test_arguments_table_adds_the_metrics_switch_off_by_default() -> None:
    body = section(SKILL.read_text(), "Arguments")
    assert METRICS_ROW in body, "arguments table missing the metrics row and its off default"
    assert "Five arguments are optional" in body
    assert "Four arguments are optional" not in body


def test_metrics_switch_plain_words_are_mapped_or_asked() -> None:
    body = " ".join(section(SKILL.read_text(), "Arguments").split())
    for phrase in (
        "`metrics` is given as `metrics=on` or `metrics=off`",
        '"with metrics" and "metrics on" mean on',
        '"without metrics" and "metrics off" mean off',
        "ask the user about any other phrasing about metrics; never guess",
        "Resolve `metrics` before step 0 creates the todo list; it sets no model or effort.",
    ):
        assert phrase in body, f"arguments missing: {phrase}"


def test_metrics_line_goes_in_the_todo_list_and_every_closing_report() -> None:
    body = " ".join(section(SKILL.read_text(), "Arguments").split())
    assert METRICS_LINE_SENTENCE in body
    assert "(the step 5 report, or the report made at any stop, including one before step 0)" in body
    assert "Write the four resolved values at the top of your todo list and in the final report" not in body
    close_out = " ".join(section(SKILL.read_text(), "5. Close out").split())
    assert "the four resolved model and effort values and the `metrics: on|off` line" in close_out


METRICS_OPENING = "Only when `metrics` is on, read [references/metrics.md](references/metrics.md)"
# SKL-95: the closing-report summary; SKL-96 adds the engineer and QA launch rows and the extras.
METRICS_ON_SCOPE = (
    "With `metrics` on, this skill does not yet record a row for a senior engineer or QA launch or record the "
    "`story-to-done` extras, and it posts no summary comment; this sentence overrides the reference's collection "
    "rules for those rows and extras and all of its posting rules."
)
METRICS_START = (
    "With `metrics` on, once `metrics` resolves to on and before step 0, the first launch creates the session's "
    "scratch directory in this start form, with the scratch-directory creation from `references/runtimes.md`, or "
    "`scratch='<directory you were handed>'` when you were handed one, in place of `<scratch creation>`:"
)
METRICS_START_BLOCK = [
    "```sh",
    "s=$(date -u +%s.%N)",
    "<scratch creation>",
    "printf 'start %s start\\nend %s start\\n' \"$s\" \"$(date -u +%s.%N)\" >> \"$scratch/metrics.txt\"",
    "```",
]
METRICS_START_RULE = (
    "Its start timestamp is the invocation's start, its row, labelled `start`, is the first in the table, the "
    "elapsed wall-clock runs from that timestamp to the closing report, and `metrics.txt` in that directory is "
    "the `<metrics file>` of every later launch."
)
METRICS_START_FAILED = (
    "A start form that exits non-zero has not recorded the `start` row, so the coordinator stops with that as the "
    "stop reason."
)
METRICS_QUOTED_PATHS = (
    "Every path placed inside single quotes in the start form, the wrapper, or the recovery command has each of "
    "its own single quotes written as `'\\''`."
)
METRICS_COMMAND_ROWS = (
    "From then on, record a row for each command the coordinator launches, in launch order, with its usage "
    "figures recorded under `references/metrics.md` and `not reported` for any usage the runtime does not return."
)
METRICS_WRAPPER_INTRO = (
    "Launch every later command in this wrapper, with the command's own lines in place of "
    "`<command>`, a label unique within the invocation and without a single quote or a line break in place of "
    "`<row label>`, and the absolute path of that `metrics.txt` in place of `<metrics file>`:"
)
METRICS_WRAPPER_BLOCK = [
    "```sh",
    "f='<metrics file>'; o=$-; set +e; s=$(date -u +%s.%N); printf 'start %s %s\\n' \"$s\" '<row label>' >> \"$f\"; ( case $o in *e*) set -e;; esac",
    "<command>",
    "); rc=$?; printf 'end %s %s\\n' \"$(date -u +%s.%N)\" '<row label>' >> \"$f\"; case $o in *e*) set -e;; esac; (exit $rc)",
    "```",
]
METRICS_WRAPPER_RULE = (
    "The command runs in a subshell, so its assignments, function definitions, `cd`, `exec`, traps and `PATH` "
    "changes cannot move the wrapper's timestamps, and the wrapper keeps both the command's exit status and an "
    "inherited `set -e`; apart from the recovery command below, a command never writes to the metrics file."
)
METRICS_DURATION = (
    "A command's duration is its `end` timestamp minus its `start` timestamp, and the rows are reported in "
    "start-timestamp order."
)
METRICS_KILLED = (
    "If a command is killed before it writes its `end` line, the coordinator's very next launch, made as soon as "
    "the kill is reported and even when no other launch would follow, is a wrapped command whose `<command>` is "
    "`printf 'end %s %s\\n' \"$(date -u +%s.%N)\" '<killed row label>' >> '<metrics file>'`, for a label that "
    "has a `start` line and no `end` line; that end timestamp is taken after the killed launch returned, and the "
    "recovery command gets a row of its own."
)
METRICS_NEVER_UNTIMED = (
    "Never launch a command outside the start form or the wrapper, never reuse one timestamp as both its start and its end, and never "
    "report a command's duration as `not reported`."
)
METRICS_CLOSING_REPORT = (
    "Give the summary, in the template `references/metrics.md` defines, in the closing report of every end "
    "state: Done, or any stop, including a stop before step 0 or before any senior engineer or QA agent is spawned."
)
METRICS_NO_LAUNCHES = (
    "The summary reads `no launches` only when the coordinator launched no role and no command; otherwise it "
    "has a row for each coordinator-launched command in launch order, the elapsed wall-clock, and the end "
    "state or stop reason."
)
METRICS_NO_TRACKER_WRITE = "The coordinator makes no tracker write and never sets the story state."
METRICS_NO_SECRETS = "The closing report contains no secrets and no local or scratch paths."


def test_manifest_appends_metrics_to_story_to_done() -> None:
    entry = MANIFEST["skills"]["story-to-done"]
    assert entry.count("metrics") == 1, "story-to-done must list metrics exactly once"
    assert entry.index("metrics") == entry.index("secrets") + 1, "metrics is appended after secrets"


def test_vendored_metrics_reference_carries_the_not_reported_rule() -> None:
    vendored = ROOT / "skills" / "story-to-done" / "references" / "metrics.md"
    assert vendored.is_file(), "run scripts/vendor_shared.py to vendor references/metrics.md"
    assert "A figure the runtime does not return is `not reported`; it is never estimated or inferred." in (
        vendored.read_text()
    )


def test_metrics_section_opens_on_only_and_links_the_reference() -> None:
    text = SKILL.read_text()
    body = section(text, "Metrics").strip()
    assert body.startswith(METRICS_OPENING), "the Metrics section must open with its on-only condition"
    assert METRICS_ON_SCOPE in body, "the Metrics section must keep the on path to the metrics line"
    assert "](references/metrics.md)" not in section(text, "Read first")


OFF_PATH = (
    "With `metrics` off or omitted, read no metrics reference, collect no figure, create no metrics file, "
    "post no metrics comment, and add no metrics content to any brief, report, todo list, or tracker write, "
    "other than the `metrics: off` line."
)


# Every line of the skill that touches metrics, the closing report, or a tracker write, pinned exactly: adding, extending, or rewording
# metrics content anywhere (Arguments and Metrics included) fails until it is pinned here.
METRICS_WORDS = re.compile(r"metric|figure|token|tool.call|wall-clock|duration|usage|summar|total|cost|switch|\btim(?:e|ing|er|estamp)\w*|elapsed|clock|latency|closing report|tracker write", re.IGNORECASE)
METRICS_LINES = [
    METRICS_ROW,
    '- `metrics` is given as `metrics=on` or `metrics=off`, or in plain words: "with metrics" and "metrics on" '
    'mean on, "without metrics" and "metrics off" mean off; ask the user about any other phrasing about metrics; '
    "never guess.",
    "- Resolve `metrics` before step 0 creates the todo list; it sets no model or effort.",
    "- " + OFF_PATH,
    "- " + METRICS_LINE_SENTENCE + " (the step 5 report, or the report made at any stop, including one before step 0).",
    "## Metrics",
    METRICS_OPENING + " once the story ID is known: it is the single home for what a `story-to-done` run "
    "collects and reports, and this file does not restate it.",
    METRICS_START,
    *[line for line in METRICS_START_BLOCK if METRICS_WORDS.search(line)],
    METRICS_START_RULE,
    METRICS_COMMAND_ROWS,
    METRICS_WRAPPER_INTRO,
    *[line for line in METRICS_WRAPPER_BLOCK if METRICS_WORDS.search(line)],
    METRICS_WRAPPER_RULE,
    METRICS_DURATION,
    METRICS_KILLED,
    METRICS_NEVER_UNTIMED,
    METRICS_CLOSING_REPORT,
    METRICS_NO_LAUNCHES,
    METRICS_ON_SCOPE,
    METRICS_NO_TRACKER_WRITE,
    METRICS_NO_SECRETS,
    "Report the story identifier, its final state, the four resolved model and effort values and the "
    "`metrics: on|off` line, each PR, the number of QA rounds with the items fixed in each, where QA recorded "
    "its evidence, and any incidental defects left open.",
]


def test_metrics_off_changes_nothing_but_the_metrics_line() -> None:
    text = SKILL.read_text()
    assert OFF_PATH in " ".join(section(text, "Arguments").split())
    body = text.split("\n---\n", 1)[1]
    found = [line for line in body.splitlines() if METRICS_WORDS.search(line)]
    assert found == METRICS_LINES, "metrics content outside the pinned switch, line, and on-only lines"
    assert not METRICS_WORDS.search(text.split("\n---\n", 1)[0]), "the front matter adds metrics content"


def test_arguments_prose_count_matches_the_table() -> None:
    body = section(SKILL.read_text(), "Arguments")
    rows = [line for line in body.splitlines() if line.startswith("| `")]
    assert len(rows) == 5 and "Five arguments are optional" in body


def readme_row() -> str:
    rows = [
        line
        for line in (ROOT / "README.md").read_text().splitlines()
        if line.startswith("| [`story-to-done`](skills/story-to-done/SKILL.md) |")
    ]
    assert rows, "README Skills table is missing the story-to-done row"
    return rows[0]


def test_readme_row_names_the_metrics_switch_and_its_default() -> None:
    row = readme_row()
    assert "a `metrics` switch, `off` by default" in row


def metrics_body() -> str:
    return " ".join(section(SKILL.read_text(), "Metrics").split())


def test_metrics_start_is_timestamped_when_the_switch_resolves() -> None:
    body = metrics_body()
    assert METRICS_START in body
    assert METRICS_START_RULE in body


def metrics_blocks() -> list[list[str]]:
    lines = section(SKILL.read_text(), "Metrics").splitlines()
    fences = [i for i, line in enumerate(lines) if line.startswith("```")]
    return [lines[a : b + 1] for a, b in zip(fences[::2], fences[1::2])]


def runtimes_scratch_creation() -> str:
    text = (ROOT / "skills" / "story-to-done" / "references" / "runtimes.md").read_text()
    blocks = re.findall(r"```bash\n(.*?)```", text, re.DOTALL)
    creation = [block for block in blocks if 'scratch="$(mktemp -d' in block]
    assert len(creation) == 1, "references/runtimes.md must give exactly one scratch-directory creation"
    return "\n".join(line.strip() for line in creation[0].splitlines())


def start_form(creation: str) -> str:
    blocks = metrics_blocks()
    assert blocks[0] == METRICS_START_BLOCK, "the start form must be the first pinned block"
    return "\n".join(blocks[0][1:-1]).replace("<scratch creation>", creation)


def test_the_start_form_creates_the_scratch_directory_and_times_itself(tmp_path: Path) -> None:
    body = metrics_body()
    assert METRICS_START_FAILED in body
    assert METRICS_QUOTED_PATHS in body
    base = tmp_path / "base"
    script = f"scratch_base='{base}'\n" + start_form(runtimes_scratch_creation())
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True)
    assert len(result.stdout.splitlines()) == 1, "the start form prints the scratch path once"
    scratch = Path(result.stdout.strip())
    assert scratch.parent == base and scratch.is_dir(), "the start form creates the scratch directory"
    rows = read_rows(scratch / "metrics.txt")
    assert [(kind, label) for kind, _, label in rows] == [("start", "start"), ("end", "start")]
    assert rows[1][1] >= rows[0][1] > 1_000_000_000, "the start row has its own ordered start and end timestamps"


def quoted(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def test_a_handed_directory_with_a_single_quote_is_timed(tmp_path: Path) -> None:
    handed = tmp_path / "team's work"
    handed.mkdir()
    subprocess.run(["bash", "-c", start_form(f"scratch='{quoted(handed)}'")], check=True)
    record = handed / "metrics.txt"
    assert subprocess.run(["bash", "-c", wrapper_script(record, "true", "probe", quote=True)]).returncode == 0
    assert [(kind, label) for kind, _, label in read_rows(record)] == [
        ("start", "start"), ("end", "start"), ("start", "probe"), ("end", "probe")
    ]


def test_a_start_form_that_cannot_record_its_row_fails(tmp_path: Path) -> None:
    handed = tmp_path / "read-only"
    handed.mkdir()
    handed.chmod(0o500)
    try:
        result = subprocess.run(["bash", "-c", start_form(f"scratch='{handed}'")], capture_output=True)
    finally:
        handed.chmod(0o700)
    assert result.returncode != 0, "a start form that writes no start row must exit non-zero"


def test_each_coordinator_command_gets_a_row_with_its_usage() -> None:
    assert METRICS_COMMAND_ROWS in metrics_body()


def test_every_launch_runs_in_the_start_form_or_the_timing_wrapper() -> None:
    body = metrics_body()
    assert METRICS_WRAPPER_INTRO in body
    assert METRICS_WRAPPER_RULE in body
    assert METRICS_DURATION in body
    assert METRICS_KILLED in body
    assert METRICS_NEVER_UNTIMED in body


def skill_wrapper() -> str:
    blocks = metrics_blocks()
    assert len(blocks) == 2, "the Metrics section must give exactly the start form and one timing wrapper"
    assert blocks[1] == METRICS_WRAPPER_BLOCK, "the timing wrapper must be the pinned block"
    return "\n".join(blocks[1][1:-1])


def wrapper_script(record: Path, command: str, label: str, quote: bool = False) -> str:
    script = skill_wrapper().replace("<command>", command, 1)
    return script.replace("<row label>", label).replace("<metrics file>", quoted(record) if quote else str(record))


def run_wrapper(record: Path, command: str, label: str = "probe", errexit: bool = False) -> int:
    flags = ["-e"] if errexit else []
    return subprocess.run(["bash", *flags, "-c", wrapper_script(record, command, label)]).returncode


def read_rows(record: Path) -> list[tuple[str, float, str]]:
    rows = [line.split(" ", 2) for line in record.read_text().splitlines()]
    return [(kind, float(stamp), label) for kind, stamp, label in rows]


def test_the_timing_wrapper_takes_distinct_start_and_end_timestamps_around_the_command(tmp_path: Path) -> None:
    record = tmp_path / "metrics.txt"
    for label in ("start command", "probe"):
        assert run_wrapper(record, "sleep 0.2", label) == 0
    rows = read_rows(record)
    assert [(kind, label) for kind, _, label in rows] == [
        ("start", "start command"), ("end", "start command"), ("start", "probe"), ("end", "probe")
    ], "each launch writes a start line before its command and an end line after it"
    for (_, start, _), (_, end, _) in (rows[0:2], rows[2:4]):
        assert end - start >= 0.2, "the start and end timestamps must bracket the command"


def test_the_timing_wrapper_keeps_the_command_exit_status(tmp_path: Path) -> None:
    cases = (("true", 0), ("false", 1), ("sh -c 'exit 7'", 7), ("exit 3", 3), ("set -e; false; true", 1))
    for errexit in (False, True):
        record = tmp_path / f"errexit-{errexit}.txt"
        for count, (command, status) in enumerate(cases, start=1):
            assert run_wrapper(record, command, errexit=errexit) == status, f"{command} must keep exit status {status}"
            assert [kind for kind, _, _ in read_rows(record)][-2:] == ["start", "end"], f"{command}: both lines"
            assert len(read_rows(record)) == 2 * count


def test_the_wrapper_keeps_an_inherited_errexit(tmp_path: Path) -> None:
    marker = tmp_path / "continued"
    assert run_wrapper(tmp_path / "metrics.txt", f"false; touch '{marker}'", errexit=True) == 1
    assert not marker.exists(), "a command run under an inherited set -e stops at its first failure"


def test_no_command_can_lose_or_corrupt_its_row(tmp_path: Path) -> None:
    (tmp_path / "a b").mkdir()
    record = tmp_path / "a b" / "metrics.txt"
    commands = [
        "true # a trailing comment",
        "true;",
        "sleep 0.1 & wait",
        "s=0; f=/dev/null; rc=0",
        "date() { printf 0; }; printf() { :; }",
        "PATH=/nonexistent",
        "exec true",
        "cd /",
        "trap 'exit 9' EXIT",
    ]
    for count, command in enumerate(commands, start=1):
        run_wrapper(record, command, "row $(printf injected) <command>")
        rows = read_rows(record)
        assert len(rows) == 2 * count, f"{command}: one start and one end line per launch"
        (start_kind, start, start_label), (end_kind, end, end_label) = rows[-2:]
        assert (start_kind, end_kind) == ("start", "end"), f"{command}: start line, then end line"
        assert start_label == end_label == "row $(printf injected) <command>", f"{command}: the label is literal"
        assert end >= start > 1_000_000_000, f"{command}: both timestamps are real and ordered"


def test_a_killed_command_keeps_its_start_line_and_the_recovery_writes_its_end(tmp_path: Path) -> None:
    record = tmp_path / "metrics.txt"
    process = subprocess.Popen(["bash", "-c", wrapper_script(record, "sleep 30", "killed")], start_new_session=True)
    deadline = time.monotonic() + 10
    while not (record.exists() and record.read_text().endswith("\n")) and time.monotonic() < deadline:
        time.sleep(0.05)
    os.killpg(process.pid, signal.SIGKILL)
    process.wait()
    assert [kind for kind, _, _ in read_rows(record)] == ["start"], "the start line is written before the command"
    recoveries = re.findall(r"`(printf 'end [^`]*)`", metrics_body())
    assert len(recoveries) == 1, "the Metrics section must give exactly one recovery command"
    recovery = recoveries[0].replace("<killed row label>", "killed").replace("<metrics file>", str(record))
    assert run_wrapper(record, recovery, "recovery") == 0
    rows = read_rows(record)
    assert [(kind, label) for kind, _, label in rows] == [
        ("start", "killed"), ("start", "recovery"), ("end", "killed"), ("end", "recovery")
    ], "the recovery writes the killed row's end line and gets a row of its own"
    assert rows[2][1] >= rows[0][1], "the killed row's end follows its start"


def test_closing_report_of_every_end_state_gives_the_summary_in_the_template() -> None:
    assert METRICS_CLOSING_REPORT in metrics_body()


def test_summary_reads_no_launches_only_without_any_launch() -> None:
    assert METRICS_NO_LAUNCHES in metrics_body()


def test_metrics_make_no_tracker_write() -> None:
    body = metrics_body()
    assert METRICS_NO_TRACKER_WRITE in body
    assert METRICS_ON_SCOPE in body


def test_closing_report_carries_no_secrets_or_paths() -> None:
    assert METRICS_NO_SECRETS in metrics_body()


def test_readme_row_says_the_summary_is_given_in_the_closing_report() -> None:
    row = readme_row()
    assert "a `metrics` switch, `off` by default, turns on run metrics, with the run summary given in the closing report" in row


POST_WORDS = re.compile(r"\bpost(?:s|ed|ing)?\b|\bcomments?\b", re.IGNORECASE)


def test_no_line_tells_the_coordinator_to_post_or_comment() -> None:
    body = SKILL.read_text().split("\n---\n", 1)[1]
    allowed = {"- " + OFF_PATH, METRICS_ON_SCOPE}
    merge_rule = "needs a delta review posted before merging"
    for line in body.splitlines():
        if line in allowed:
            continue
        assert not POST_WORDS.search(line.replace(merge_rule, "")), (
            f"a line tells the coordinator to post or comment: {line}"
        )
