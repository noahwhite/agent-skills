"""Contract checks for the story-to-done skill."""

import json
import os
import re
import shutil
import signal
import subprocess
import time
from decimal import Decimal
from pathlib import Path

import pytest

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
# SKL-95: the closing-report summary. SKL-96 adds the engineer and QA launch rows, the extras, the
# metrics-file location, and the brief independence rules; posting stays out until SKL-94.
METRICS_ON_SCOPE = (
    "With `metrics` on, this skill posts no summary comment; this sentence overrides every posting rule in "
    "`references/metrics.md`."
)
METRICS_LOCATION = (
    "- **Location:** the coordinator keeps every figure in its one metrics file, the `<metrics file>` below, "
    "in the session scratch directory, outside every role subdirectory."
)
METRICS_NEVER_NAMED = "- **Never named:** the metrics file is never named in a brief."
METRICS_TIMED_LAUNCHES = (
    "- **Timed launches:** time each senior engineer launch and each QA round, taking the start immediately "
    "before the launch and the end when it returns, and record it as one row in launch order under a "
    "label unique within the invocation, with its runtime, model, effort, duration, tokens, and tool "
    "calls as `references/metrics.md` defines; `not "
    "reported` stands for any figure the runtime does not return, and a resumed role's cumulative figure is "
    "marked `cumulative`."
)
METRICS_LAUNCH_POINTS = (
    "The senior engineer's timed launches are the first launch in step 2 and each resume or re-spawn in "
    "step 4, and each QA round is one launch in step 3."
)
METRICS_EXTRAS = (
    "- **Extras:** take each `story-to-done` extra at the step that observes it: **Start** from the step 1 "
    "state read and whether step 2 ran; **PRs merged** from every step 2, step 3, and step 4 read of a "
    "merged PR's head and merge commit; **Time to deployment review** from the recorded invocation start "
    "to the read-back that confirms the deployment-review state; **QA rounds** at each spawn in step 3, "
    "each with its **duration** from that round's launch row; **Failed items** from the step 4 read of "
    "each QA round's outcome, in round order; **Fix rounds** from the step 4 branch that hands the failed "
    "items back; and **End state** at the closing report."
)
METRICS_BRIEF_EXCLUSION = (
    "- **Independence:** no senior engineer or QA brief carries this invocation's figures or another role's "
    "figures from this invocation, including in a later round or a re-spawn."
)
METRICS_STEP0 = (
    "With `metrics` on, seed one more item: collect the metrics figures and give the summary in the closing "
    "report."
)
METRICS_NOTHING_BEFORE_START = (
    "With `metrics` on, launch no command before the start form, not even to read a file or list a directory."
)
METRICS_START = (
    "With `metrics` on, the first command launched, before step 0, is this start form, which records "
    "`invocation_start` and makes its `metrics.txt` the `<metrics file>` of every later launch, with the "
    "scratch-directory creation from `references/runtimes.md`, or `scratch='<directory you were handed>'` when "
    "you were handed one, in place of `<scratch creation>`:"
)
METRICS_START_BLOCK = [
    "```sh",
    "s=$(date -u +%s.%N); <scratch creation>",
    "printf 'start %s start\\nend %s start\\n' \"$s\" \"$(date -u +%s.%N)\" >> \"$scratch/metrics.txt\"",
    "```",
]
METRICS_COMMAND_ROWS = (
    "From then on, record a row for each command the coordinator launches, in launch order, with its usage "
    "figures recorded under `references/metrics.md` and `not reported` for any usage the runtime does not return."
)
METRICS_WRAPPER_INTRO = (
    "Launch every later command other than the end form below in this wrapper, with the command in place of "
    "`<command>`, a label unique within the invocation and without a single quote in place of `<row label>`, and "
    "the absolute path of that `metrics.txt` in place of `<metrics file>`:"
)
METRICS_WRAPPER_BLOCK = [
    "```sh",
    "f='<metrics file>'; printf 'start %s %s\\n' \"$(date -u +%s.%N)\" '<row label>' >> \"$f\"; (",
    "<command>",
    "); rc=$?; printf 'end %s %s\\n' \"$(date -u +%s.%N)\" '<row label>' >> \"$f\"; (exit $rc)",
    "```",
]
SUMMARY_SCRIPT = ROOT / "skills" / "story-to-done" / "scripts" / "metrics-summary.sh"
METRICS_END_LAUNCH = "sh '<skill dir>/scripts/metrics-summary.sh' '<metrics file>'"
METRICS_ROLE_ROW = (
    "Record a role row with two commands of its own: immediately before the launch, `f='<metrics file>'; printf "
    "'start %s %s\\t<runtime>\\t<model>\\t<effort>\\n' \"$(date -u +%s.%N)\" '<row label>' >> \"$f\"`, and when it "
    "returns, `f='<metrics file>'; printf 'end %s %s\\t<tokens>\\t<tool calls><cumulative>\\n' \"$(date -u "
    "+%s.%N)\" '<row label>' >> \"$f\"`, where `<cumulative>` is `\\tcumulative` when the figures are cumulative over "
    "earlier launches and empty otherwise, and `<tokens>` and `<tool calls>` are `not reported` for a figure the "
    "runtime does not return; these two commands are the row's own timestamps and get no row of their own."
)
METRICS_EXTRAS_RECORD = (
    "Record each extra as one `extra <slug>\\t<value>` line in the metrics file: the slugs are `qa-rounds`, "
    "`failed-items`, `fix-rounds`, `prs-merged`, `start`, `time-to-deployment-review`, `qa-round-durations` and "
    "`end-state`, a per-round value is written in round order as `round 1: <value>; round 2: <value>` with a `;` "
    "inside a value written as `\\;`, and the extra lines get no row of their own."
)
METRICS_END_INTRO = (
    f"Immediately before the closing report, the last launch is the end form `{METRICS_END_LAUNCH}`, where "
    "`<skill dir>` is the absolute directory your runtime loaded this skill from; it records `invocation_end` and "
    "prints the summary's table, the recorded extras and Totals from the metrics file."
)
METRICS_END_VERBATIM = (
    "The summary in the closing report is the template's heading line, a blank line, and then the end form's output "
    "copied verbatim: no line is added, reworded, or left out, and no duration, timestamp, or total is recomputed or "
    "converted."
)
METRICS_KILLED = (
    "If a command is killed before it writes its `end` line, the coordinator's very next launch, made as "
    "soon as the kill is reported, is a wrapped command whose `<command>` is `printf 'end %s %s\\n' "
    "\"$(date -u +%s.%N)\" '<killed row label>' >> '<metrics file>'`, and the recovery command gets a row "
    "of its own."
)
METRICS_CLOSING_REPORT = (
    "Give the summary, in the template `references/metrics.md` defines, in the closing report of every end "
    "state: Done, or any stop, including a stop before step 0 or before any senior engineer or QA agent is spawned."
)
METRICS_NO_LAUNCHES = (
    "The summary reads `no launches` only when the coordinator launched no role and no command; otherwise it "
    "has one row for each launch in launch order, the elapsed wall-clock, and the end state or stop reason."
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
    METRICS_LOCATION,
    METRICS_NEVER_NAMED,
    METRICS_TIMED_LAUNCHES,
    "  " + METRICS_LAUNCH_POINTS,
    METRICS_EXTRAS,
    METRICS_BRIEF_EXCLUSION,
    METRICS_NOTHING_BEFORE_START,
    METRICS_START,
    *[line for line in METRICS_START_BLOCK if METRICS_WORDS.search(line)],
    METRICS_COMMAND_ROWS,
    METRICS_WRAPPER_INTRO,
    *[line for line in METRICS_WRAPPER_BLOCK if METRICS_WORDS.search(line)],
    METRICS_KILLED,
    METRICS_ROLE_ROW,
    METRICS_EXTRAS_RECORD,
    METRICS_END_INTRO,
    METRICS_END_VERBATIM,
    METRICS_CLOSING_REPORT,
    METRICS_NO_LAUNCHES,
    METRICS_ON_SCOPE,
    METRICS_NO_TRACKER_WRITE,
    METRICS_NO_SECRETS,
    "Report the story identifier, its final state, the four resolved model and effort values and the "
    "`metrics: on|off` line, each PR, the number of QA rounds with the items fixed in each, where QA recorded "
    "its evidence, and any incidental defects left open.",
]
METRICS_LINES.insert(-1, METRICS_STEP0)


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
    base = tmp_path / "base"
    script = f"scratch_base='{quoted(base)}'\n" + start_form(runtimes_scratch_creation())
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
    handed = tmp_path / "not a directory"
    handed.write_text("")
    script = start_form(f"scratch='{quoted(handed)}'")
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    assert "metrics.txt" in result.stderr, "the start row's write is what fails"
    assert result.returncode != 0, "a start form that writes no start row must exit non-zero"


def test_each_coordinator_command_gets_a_row_with_its_usage() -> None:
    assert METRICS_COMMAND_ROWS in metrics_body()


# SKL-96: the engineer and QA launch rows, the extras' collection points, the metrics-file location,
# the never-named statement, and the brief independence rules.


def test_engineer_and_qa_launches_are_timed_and_recorded_as_one_row_each() -> None:
    body = metrics_body()
    assert METRICS_TIMED_LAUNCHES in body, "the launch timing and its row figures are not stated"
    assert METRICS_LAUNCH_POINTS in body, "which launches are rows is not stated"


def test_each_story_to_done_extra_is_taken_at_the_step_that_observes_it() -> None:
    assert METRICS_EXTRAS in metrics_body(), "an extra's collection point is missing"


def test_the_metrics_file_lives_in_the_session_scratch_directory_outside_every_role_subdirectory() -> None:
    assert METRICS_LOCATION in metrics_body()


def test_the_metrics_file_is_never_named_in_a_brief() -> None:
    assert METRICS_NEVER_NAMED in metrics_body()


# A brief leak can be phrased without the word `metrics`, so the two brief sections are scanned for the
# vocabulary a cost figure or a comparison with another launch would use.
BRIEF_LEAK = re.compile(
    r"metric|figure|token|tool.call|wall-clock|duration|elapsed|usage|summar|total|cost|switch"
    r"|\btim(?:e|ing|er|estamp)\w*|\bhow long\b|\btook\b|\bprevious\b"
    r"|\bclock\b|latency|closing report|tracker write",
    re.IGNORECASE,
)


def test_no_engineer_or_qa_brief_carries_metrics_or_another_roles_figures() -> None:
    assert METRICS_BRIEF_EXCLUSION in metrics_body()
    text = SKILL.read_text()
    for heading in ("2. Senior engineer: implement to deployment review", "3. QA agent: verify the deployed story"):
        offenders = [line for line in section(text, heading).splitlines() if BRIEF_LEAK.search(line)]
        assert not offenders, f"{heading} carries metrics or another launch's figures into the brief: {offenders}"


def test_step_0_seeds_a_collect_metrics_item_only_when_the_switch_is_on() -> None:
    body = " ".join(section(SKILL.read_text(), "0. Track everything on a todo list").split())
    assert METRICS_STEP0 in body, "step 0 does not seed the collect metrics item"
    assert body.index("Seed it with at least") < body.index(METRICS_STEP0), (
        "the collect metrics item must follow the shared seed sentence as an on-only sentence of its own"
    )
    assert METRICS_STEP0.startswith("With `metrics` on, "), "the seed item must apply only when the switch is on"


def test_step_0_adds_no_unconditional_collect_metrics_instruction() -> None:
    body = " ".join(section(SKILL.read_text(), "0. Track everything on a todo list").split())
    assert METRICS_STEP0 in body
    rest = " ".join(body.replace(METRICS_STEP0, "").split()).lower()
    for phrase in ("metric", "seed the same", "same item", " off "):
        assert phrase not in rest, f"step 0 adds an unconditional collect-metrics instruction: {phrase!r}"


def test_every_launch_runs_in_the_start_form_or_the_timing_wrapper() -> None:
    body = metrics_body()
    assert METRICS_WRAPPER_INTRO in body
    assert METRICS_END_INTRO in body
    assert METRICS_END_VERBATIM in body
    assert METRICS_KILLED in body


def skill_wrapper() -> str:
    blocks = metrics_blocks()
    assert len(blocks) == 2, "the Metrics section gives exactly the start form and one wrapper"
    assert blocks[1] == METRICS_WRAPPER_BLOCK, "the timing wrapper must be the pinned block"
    return "\n".join(blocks[1][1:-1])


def wrapper_script(record: Path, command: str, label: str, quote: bool = False) -> str:
    script = skill_wrapper().replace("<command>", command, 1)
    return script.replace("<row label>", label).replace("<metrics file>", quoted(record) if quote else str(record))


def run_wrapper(record: Path, command: str, label: str = "probe") -> int:
    return subprocess.run(["bash", "-c", wrapper_script(record, command, label)]).returncode


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
    record = tmp_path / "metrics.txt"
    for count, (command, status) in enumerate(cases, start=1):
        assert run_wrapper(record, command) == status, f"{command} must keep exit status {status}"
        assert [kind for kind, _, _ in read_rows(record)][-2:] == ["start", "end"], f"{command}: both lines"
        assert len(read_rows(record)) == 2 * count


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


def test_a_failed_metrics_write_shows_an_error_and_keeps_the_exit_status(tmp_path: Path) -> None:
    blocker = tmp_path / "not a directory"
    blocker.write_text("")
    record = blocker / "metrics.txt"
    for command, status in (("true", 0), ("exit 4", 4)):
        script = wrapper_script(record, command, "probe")
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        assert result.returncode == status, f"{command}: the wrapper keeps the command's exit status"
        errors = [line for line in result.stderr.splitlines() if str(record) in line]
        assert len(errors) == 2, f"{command}: the failed start and end writes each show an error naming the file"


def test_the_metrics_section_says_how_a_role_row_is_recorded() -> None:
    body = metrics_body()
    assert METRICS_ROLE_ROW in body, "the role row's own start and end lines are not stated"
    assert METRICS_EXTRAS_RECORD in body, "the extras' recording lines are not stated"


def test_the_end_form_runs_the_summary_script() -> None:
    assert METRICS_END_INTRO in metrics_body()
    assert SUMMARY_SCRIPT.is_file(), "the end form's script must ship with the skill"


def end_form(record: Path) -> str:
    skill_dir = quoted(SUMMARY_SCRIPT.parent.parent)
    return METRICS_END_LAUNCH.replace("<skill dir>", skill_dir).replace("<metrics file>", quoted(record))


AWKS = sorted({os.path.realpath(path) for name in ("awk", "gawk", "mawk", "nawk") if (path := shutil.which(name))})


def run_end_form(record: Path, awk: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "awk-bin"
    bin_dir.mkdir(exist_ok=True)
    link = bin_dir / "awk"
    link.unlink(missing_ok=True)
    link.symlink_to(awk)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    return subprocess.run(["bash", "-c", end_form(record)], capture_output=True, text=True, env=env)


def recorded(record: Path) -> dict[tuple[str, str], str]:
    rows = {}
    for line in record.read_text().splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3 and parts[0] in ("start", "end"):
            rows[(parts[0], parts[2].split("\t", 1)[0])] = parts[1]
    return rows


def seconds(start: str, end: str) -> str:
    return f"{Decimal(end) - Decimal(start):.9f}s"


def expected_summary(rows: list[tuple[str, str]], start: str, end: str, elapsed: str) -> str:
    table = [
        "| Role | Runtime | Model | Effort | Duration | Tokens | Tool calls |",
        "|---|---|---|---|---|---|---|",
        *[f"| {label} | command | not set | not set | {duration} | not reported | not reported |" for label, duration in rows],
    ]
    totals = [
        "Totals",
        f"- Elapsed wall-clock: {elapsed} ({start} to {end})",
        f"- Tokens: not reported [partial: {len(rows)} not reported, 0 cumulative]",
        f"- Tool calls: not reported [partial: {len(rows)} not reported, 0 cumulative]",
    ]
    return "\n".join([*table, "", *totals]) + "\n"


@pytest.mark.parametrize("awk", AWKS)
def test_the_end_form_times_itself_last_and_prints_the_summary(tmp_path: Path, awk: str) -> None:
    handed = tmp_path / "team's session"
    handed.mkdir()
    subprocess.run(["bash", "-c", start_form(f"scratch='{quoted(handed)}'")], check=True)
    record = handed / "metrics.txt"
    for label in ("read story state", "probe"):
        assert subprocess.run(["bash", "-c", wrapper_script(record, "sleep 0.1", label, quote=True)]).returncode == 0
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    stamps = recorded(record)
    assert [(kind, label) for kind, _, label in read_rows(record)][-2:] == [("start", "end"), ("end", "end")]
    labels = ("start", "read story state", "probe", "end")
    rows = [(label, seconds(stamps["start", label], stamps["end", label])) for label in labels]
    assert all(Decimal(duration[:-1]) > 0 for _, duration in rows), "every row has distinct start and end timestamps"
    start, end = stamps["start", "start"], stamps["end", "end"]
    assert result.stdout == expected_summary(rows, start, end, seconds(start, end)), (
        "the end form prints every row, the exact elapsed, the recorded timestamps, and the partial note"
    )


@pytest.mark.parametrize("awk", AWKS)
def test_the_end_form_names_lost_rows(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(
        "start 1793218210.722929459 start\n"
        "end 1793218211.000000001 start\n"
        "start 1793218212.5 killed\n"
    )
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    stamps = recorded(record)
    end = stamps["end", "end"]
    rows = [("start", "0.277070542s"), ("killed", "lost"), ("end", seconds(stamps["start", "end"], end))]
    assert result.stdout == expected_summary(rows, "1793218210.722929459", end, seconds("1793218210.722929459", end))


@pytest.mark.parametrize("awk", AWKS)
def test_a_run_that_stops_after_the_start_form_has_two_rows(tmp_path: Path, awk: str) -> None:
    subprocess.run(["bash", "-c", start_form(f"scratch='{quoted(tmp_path)}'")], check=True)
    record = tmp_path / "metrics.txt"
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    stamps = recorded(record)
    rows = [(label, seconds(stamps["start", label], stamps["end", label])) for label in ("start", "end")]
    start, end = stamps["start", "start"], stamps["end", "end"]
    assert result.stdout == expected_summary(rows, start, end, seconds(start, end))


# SKL-96 round 2: a role launch's row carries its runtime, model and effort on its start line and its usage on
# its end line, the extras are recorded as `extra` lines, and the end form prints both.

EXTRA_LABELS = {
    "qa-rounds": "QA rounds",
    "failed-items": "Failed items",
    "fix-rounds": "Fix rounds",
    "prs-merged": "PRs merged",
    "start": "Start",
    "time-to-deployment-review": "Time to deployment review",
    "qa-round-durations": "QA round durations",
    "end-state": "End state",
}


def row_line(kind: str, stamp: str, label: str, *fields: str) -> str:
    line = f"{kind} {stamp} {label}"
    return (f"{line}\t" + "\t".join(fields) if fields else line) + "\n"


def role_start(stamp: str, label: str, runtime: str, model: str, effort: str) -> str:
    return row_line("start", stamp, label, runtime, model, effort)


def role_end(stamp: str, label: str, tokens: str, calls: str, cumulative: bool = False) -> str:
    return row_line("end", stamp, label, tokens, calls, *(["cumulative"] if cumulative else []))


def extra_line(slug: str, value: str) -> str:
    return f"extra {slug}\t{value}\n"


def summary(rows: list[tuple[str, ...]], totals: tuple[str, str], start: str, end: str, elapsed: str,
            extras: list[tuple[str, str]] | None = None) -> str:
    table = [
        "| Role | Runtime | Model | Effort | Duration | Tokens | Tool calls |",
        "|---|---|---|---|---|---|---|",
        *["| " + " | ".join(row) + " |" for row in rows],
    ]
    lines = [*table, ""]
    for slug, value in extras or []:
        lines.append(f"{EXTRA_LABELS[slug]}: {value}")
    if extras:
        lines.append("")
    lines.extend([
        "Totals",
        f"- Elapsed wall-clock: {elapsed} ({start} to {end})",
        f"- Tokens: {totals[0]}",
        f"- Tool calls: {totals[1]}",
    ])
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("awk", AWKS)
def test_a_role_row_carries_its_runtime_model_effort_and_usage(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(
        "start 1793218210.500000000 start\nend 1793218210.600000000 start\n"
        + role_start("1793218300.000000000", "senior-engineer-1", "opencode", "deepseek/deepseek-v4-pro", "high")
        + role_end("1793218900.000000000", "senior-engineer-1", "120000", "41")
        + role_start("1793219000.000000000", "qa-agent-round-1", "opencode", "deepseek/deepseek-flash", "high")
        + role_end("1793219200.000000000", "qa-agent-round-1", "not reported", "not reported")
    )
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    end = recorded(record)["end", "end"]
    rows = [
        ("start", "command", "not set", "not set", "0.100000000s", "not reported", "not reported"),
        ("senior-engineer-1", "opencode", "deepseek/deepseek-v4-pro", "high", "600.000000000s", "120000", "41"),
        ("qa-agent-round-1", "opencode", "deepseek/deepseek-flash", "high", "200.000000000s", "not reported", "not reported"),
        ("end", "command", "not set", "not set", seconds(recorded(record)["start", "end"], end), "not reported", "not reported"),
    ]
    totals = ("120000 [partial: 3 not reported, 0 cumulative]", "41 [partial: 3 not reported, 0 cumulative]")
    assert result.stdout == summary(rows, totals, "1793218210.500000000", end, seconds("1793218210.500000000", end))


@pytest.mark.parametrize("awk", AWKS)
def test_a_cumulative_role_row_is_marked_and_excluded_from_the_totals(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(
        "start 1793218210.500000000 start\nend 1793218210.600000000 start\n"
        + role_start("1793218300.000000000", "senior-engineer-1", "opencode", "deepseek/deepseek-v4-pro", "high")
        + role_end("1793218900.000000000", "senior-engineer-1", "120000", "41")
        + role_start("1793219000.000000000", "senior-engineer-1-resumed", "opencode", "deepseek/deepseek-v4-pro", "high")
        + role_end("1793219100.000000000", "senior-engineer-1-resumed", "260000", "55", cumulative=True)
    )
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    stamps = recorded(record)
    end = stamps["end", "end"]
    rows = [
        ("start", "command", "not set", "not set", "0.100000000s", "not reported", "not reported"),
        ("senior-engineer-1", "opencode", "deepseek/deepseek-v4-pro", "high", "600.000000000s", "120000", "41"),
        ("senior-engineer-1-resumed", "opencode", "deepseek/deepseek-v4-pro", "high", "100.000000000s", "260000 cumulative", "55 cumulative"),
        ("end", "command", "not set", "not set", seconds(stamps["start", "end"], end), "not reported", "not reported"),
    ]
    totals = ("120000 [partial: 2 not reported, 1 cumulative]", "41 [partial: 2 not reported, 1 cumulative]")
    assert result.stdout == summary(rows, totals, "1793218210.500000000", end, seconds("1793218210.500000000", end))


@pytest.mark.parametrize("awk", AWKS)
def test_the_recorded_extras_print_one_line_each_in_the_reference_order(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    values = {
        "qa-rounds": "2",
        "failed-items": "round 1: 2; round 2: 0",
        "fix-rounds": "1",
        "prs-merged": "2",
        "start": "In Progress, implementation ran",
        "time-to-deployment-review": "1h 12m",
        "qa-round-durations": "round 1: 200.000000000s; round 2: 90.000000000s",
        "end-state": "In Deployment Review",
    }
    record.write_text(
        "start 1793218210.500000000 start\nend 1793218210.600000000 start\n"
        + "".join(extra_line(slug, values[slug]) for slug in reversed(list(EXTRA_LABELS)))
    )
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    stamps = recorded(record)
    end = stamps["end", "end"]
    rows = [
        ("start", "command", "not set", "not set", "0.100000000s", "not reported", "not reported"),
        ("end", "command", "not set", "not set", seconds(stamps["start", "end"], end), "not reported", "not reported"),
    ]
    totals = ("not reported [partial: 2 not reported, 0 cumulative]",) * 2
    extras = [(slug, values[slug]) for slug in EXTRA_LABELS]
    assert result.stdout == summary(rows, totals, "1793218210.500000000", end, seconds("1793218210.500000000", end), extras)


@pytest.mark.parametrize("awk", AWKS)
def test_an_extra_value_keeps_its_escaping_and_its_unknown_slugs_print_nothing(tmp_path: Path, awk: str) -> None:
    record = tmp_path / "metrics.txt"
    record.write_text(
        "start 1793218210.500000000 start\n"
        + extra_line("failed-items", "round 1: a\\;b")
        + extra_line("unknown-slug", "never printed")
    )
    result = run_end_form(record, awk, tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    assert "Failed items: round 1: a\\;b\n" in result.stdout
    assert "unknown-slug" not in result.stdout and "never printed" not in result.stdout


def end_form_program() -> str:
    script = SUMMARY_SCRIPT.read_text()
    return script[script.index("awk '") + 5 : script.rindex("' \"$1\"")]


def test_the_end_form_works_out_durations_exactly() -> None:
    assert AWKS, "no awk to run the end form with"
    stamps = "start 1793218198.999999999 start\nend 1793218200.000000001 start\nstart 1793218225.1 end\nend 1793218225.2 end\n"
    rows = [("start", "1.000000002s"), ("end", "0.100000000s")]
    expected = expected_summary(rows, "1793218198.999999999", "1793218225.2", "26.200000001s")
    for awk in AWKS:
        result = subprocess.run([awk, end_form_program()], input=stamps, capture_output=True, text=True, check=True)
        assert result.stdout == expected, awk


def test_an_end_form_that_cannot_record_its_row_fails(tmp_path: Path) -> None:
    blocker = tmp_path / "not a directory"
    blocker.write_text("")
    read_only = tmp_path / "metrics.txt"
    read_only.write_text("start 1793218198.0 start\nend 1793218199.0 start\n")
    read_only.chmod(0o444)
    for record in (blocker / "metrics.txt", read_only):
        result = subprocess.run(["bash", "-c", end_form(record)], capture_output=True, text=True)
        assert "metrics.txt" in result.stderr and result.stdout == "", "a failed end form prints no summary"
        assert result.returncode != 0, "an end form that writes no row must exit non-zero"


def test_a_killed_command_keeps_its_start_line(tmp_path: Path) -> None:
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
    assert [(kind, label) for kind, _, label in read_rows(record)] == [
        ("start", "killed"), ("start", "recovery"), ("end", "killed"), ("end", "recovery")
    ], "the recovery writes the killed row's end line and gets a row of its own"


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
