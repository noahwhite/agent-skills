"""Contract checks for the story-to-done skill."""

import json
import re
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
    assert "(the step 5 report, or the report made at a stop in steps 1 to 4)" in body
    assert "Write the four resolved values at the top of your todo list and in the final report" not in body
    close_out = " ".join(section(SKILL.read_text(), "5. Close out").split())
    assert "the four resolved model and effort values and the `metrics: on|off` line" in close_out


METRICS_OPENING = "Only when `metrics` is on, read [references/metrics.md](references/metrics.md)"
METRICS_ON_SCOPE = (
    "With `metrics` on, this skill does not yet take any figure, write a metrics file, add totals to a report, "
    "or post a summary, and this sentence overrides the reference's collection, totals, and posting rules: "
    "the run adds only the `metrics: on` line, and the coordinator makes no tracker write."
)


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


# Every line of the skill that touches metrics, pinned exactly: adding, extending, or rewording
# metrics content anywhere (Arguments and Metrics included) fails until it is pinned here.
METRICS_WORDS = re.compile(r"metric|figure|token|tool.call|wall-clock|duration|usage|summar|total|cost|switch|\btim(?:e|es|ed|ing|estamps?)\b|elapsed|clock|latency", re.IGNORECASE)
METRICS_LINES = [
    METRICS_ROW,
    '- `metrics` is given as `metrics=on` or `metrics=off`, or in plain words: "with metrics" and "metrics on" '
    'mean on, "without metrics" and "metrics off" mean off; ask the user about any other phrasing about metrics; '
    "never guess.",
    "- Resolve `metrics` before step 0 creates the todo list; it sets no model or effort.",
    "- " + OFF_PATH,
    "- " + METRICS_LINE_SENTENCE + " (the step 5 report, or the report made at a stop in steps 1 to 4).",
    "## Metrics",
    METRICS_OPENING + " once the story ID is known: it is the single home for what a `story-to-done` run "
    "collects and reports, and this file does not restate it.",
    METRICS_ON_SCOPE,
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


def test_readme_row_names_the_metrics_switch_and_its_default() -> None:
    row = next(
        line
        for line in (ROOT / "README.md").read_text().splitlines()
        if line.startswith("| [`story-to-done`](skills/story-to-done/SKILL.md) |")
    )
    assert "a `metrics` switch, `off` by default" in row
