"""The shared run-metrics reference and the runtime usage map (SKL-44).

Each test pins an exact sentence or table-header fragment, so deleting the guarded phrase
from the source file fails the named test.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "shared" / "metrics.md"


def metrics_text() -> str:
    assert METRICS.is_file(), "shared/metrics.md is missing"
    return METRICS.read_text()


def metrics_prose() -> str:
    """The file without its fenced blocks, so a rule moved into an example no longer counts."""
    return re.sub(r"```.*?```", "", metrics_text(), flags=re.S)


def template_block() -> str:
    text = metrics_text()
    assert text.count("```text") == 1, "expected exactly one summary template block"
    return text.split("```text", 1)[1].split("```", 1)[0]


def flat(text: str) -> str:
    """Join wrapped lines so a pinned sentence matches across a line break."""
    return " ".join(text.split())


def assert_states(text: str, phrase: str) -> None:
    assert flat(phrase) in flat(text), f"missing: {phrase}"


# A1: what is collected, per launch.
ROW_SCOPE = (
    "Record one row per subagent or command launch that the facilitator or coordinator itself "
    "spawns, including each re-launch and the tracker-write preflight where the skill has one."
)
ROUND_COUNTERS = "Round counters are not rows; they are listed separately under the extras below."
USAGE_SOURCE = (
    "What each runtime's usage report returns is in the \"Read a subagent's usage (duration, "
    "tokens, tool calls)\" row of `references/runtimes.md`, and for a shell-launched agent in its "
    "\"Usage from shell-launched agents\" rule."
)
FIELD_MARKERS = ["Role", "Runtime", "Model", "Effort", "Duration", "Tokens", "Tool calls"]
ROW_FIELDS = [
    pytest.param("1. **Role:** the role the launch filled.", id="role"),
    pytest.param(
        "2. **Runtime:** the role's configured `runtime` value; for a `story-to-done` role, the "
        "session runtime it was launched on, since that skill's arguments set only model and effort.",
        id="runtime",
    ),
    pytest.param(
        "The runtime is recorded as a data value; this file names no runtime's tools or paths.",
        id="runtime-is-data",
    ),
    pytest.param("3. **Model:** the model the launch ran on.", id="model"),
    pytest.param(
        "4. **Effort:** the reasoning effort the launch ran at, or `not set` where the role has none.",
        id="effort-not-set",
    ),
    pytest.param(
        "5. **Duration:** the wall-clock duration the facilitator or coordinator measures from "
        "timestamps it takes immediately before the launch and after the launch returns.",
        id="duration",
    ),
    pytest.param(
        "6. **Tokens:** the token count the runtime's usage report returns for that launch.",
        id="token-count",
    ),
    pytest.param(
        "7. **Tool calls:** the tool-call count the runtime's usage report returns for that launch.",
        id="tool-call-count",
    ),
]
FIGURE_RULES = [
    pytest.param(
        "Roles spawned inside a delegated role get no row; their usage counts only if the "
        "parent's figure is stated to include it.",
        id="nested-role-no-row",
    ),
    pytest.param(
        "A figure the runtime does not return is `not reported`; it is never estimated or inferred.",
        id="not-reported",
    ),
    pytest.param("A resumed role's figures are recorded as returned.", id="resumed-as-returned"),
    pytest.param(
        "A figure that is cumulative over earlier launches is marked `cumulative` in its row and "
        "is excluded from the run total unless the runtime separately reports a launch-scoped figure.",
        id="cumulative",
    ),
    pytest.param(
        "The elapsed wall-clock from the invocation's start to its end.", id="total-elapsed"
    ),
    pytest.param(
        "Per figure (tokens and tool calls), the sum of the launch-scoped figures that were reported.",
        id="total-sum",
    ),
    pytest.param(
        "A total is labelled `partial`, with the count of launches not reported and the count "
        "excluded as `cumulative`, only when either count is non-zero.",
        id="partial-non-zero",
    ),
    pytest.param(
        "An invocation that performs no launch states `no launches`, the end state or stop reason, "
        "and `not applicable` for every per-figure total.",
        id="no-launches",
    ),
]
REFINEMENT_EXTRAS = [
    pytest.param("- **Accept rounds:** the number of accept rounds run.", id="accept-rounds"),
    pytest.param(
        "- **Pointing rounds:** one per blind value collection: Step 3, the Step 3 re-run after a "
        "Step 4 re-refine, each split slice estimate under the Split rule, and each anchoring "
        "recovery re-run.",
        id="pointing-rounds",
    ),
    pytest.param(
        "- **Re-votes:** one per Step 4 re-vote, including the re-vote after a re-refine's Step 3 re-run.",
        id="re-votes",
    ),
    pytest.param("- **Re-refine:** whether re-refine ran.", id="re-refine"),
    pytest.param("- **Anchoring events:** the number of anchoring events.", id="anchoring-events"),
    pytest.param(
        "- **Outcome:** the consensus value or size, unpointed, split with the slice count, or the "
        "stop reason, including `needs input` on a denied tracker write.",
        id="outcome",
    ),
    pytest.param(
        "- **Denied tracker writes fallback:** whether the denied tracker writes fallback was used.",
        id="fallback-used",
    ),
]
STORY_TO_DONE_EXTRAS = [
    pytest.param("- **QA rounds:** the number of QA rounds.", id="qa-rounds"),
    pytest.param("- **Failed items:** the failed items per QA round.", id="failed-items"),
    pytest.param("- **Fix rounds:** the number of fix rounds.", id="fix-rounds"),
    pytest.param("- **PRs merged:** the number of PRs merged.", id="prs-merged"),
    pytest.param(
        "- **Start:** the state found at the start, and whether the implementation step ran.",
        id="start-state",
    ),
    pytest.param(
        "- **Time to deployment review:** from the invocation's start to the coordinator's "
        "read-back confirming `profile.tracker.states.in_deployment_review`; `not applicable` when "
        "the implementation step did not run or the story never reached that state.",
        id="time-to-deployment-review",
    ),
    pytest.param(
        "- **QA round durations:** each QA round's duration, which is its launch row's duration.",
        id="qa-round-duration",
    ),
    pytest.param("- **End state:** Done or the stop reason.", id="end-state"),
]
TEMPLATE_BLOCK = [
    pytest.param(
        "Run metrics: <skill> <story key> - <end state or stop reason>", id="heading-line"
    ),
    pytest.param(
        "| Role | Runtime | Model | Effort | Duration | Tokens | Tool calls |", id="row-header"
    ),
    pytest.param("<one line per extra of this skill: name: value>", id="extra-lines"),
    pytest.param("- Elapsed wall-clock: <elapsed>", id="totals-elapsed"),
    pytest.param("- Tokens: <sum> [partial: <n> not reported, <n> cumulative]", id="totals-tokens"),
    pytest.param(
        "- Tool calls: <sum> [partial: <n> not reported, <n> cumulative]", id="totals-tool-calls"
    ),
    pytest.param("Totals", id="totals-heading"),
]
TEMPLATE_PLACEHOLDERS = {
    "<skill>", "<story key>", "<end state or stop reason>", "<role>", "<runtime>", "<model>",
    "<effort or not set>", "<duration>", "<tokens>", "<tool calls>",
    "<one line per extra of this skill: name: value>", "<elapsed>", "<sum>", "<n>",
}
TEMPLATE_PROSE = [
    pytest.param(
        "The heading line names the skill, the story key, and the invocation's end state or stop "
        "reason.",
        id="template-heading-rule",
    ),
    pytest.param(
        "Each launch gets one table row with the fields in the order above; a figure cell holds "
        "the number, `not reported`, or the number followed by `cumulative`.",
        id="template-row-per-launch",
    ),
    pytest.param(
        "Rows are listed in launch order, so the n-th row for a role is that role's n-th launch.",
        id="template-launch-order",
    ),
    pytest.param(
        "In a cell value, a `|` is written as `\\|` and a line break as a space.",
        id="template-cell-escaping",
    ),
    pytest.param(
        "With no launches, the table is replaced by the line `no launches`, the elapsed wall-clock "
        "is still given, and each per-figure total reads `not applicable`.",
        id="template-no-launches",
    ),
]


def test_metrics_reference_exists():
    assert METRICS.is_file()


def test_one_row_per_launch_the_poster_spawns():
    assert_states(metrics_prose(), ROW_SCOPE)


def test_round_counters_are_listed_separately():
    assert_states(metrics_prose(), ROUND_COUNTERS)


def test_usage_source_names_the_row_and_the_shell_launched_rule():
    assert_states(metrics_prose(), USAGE_SOURCE)


@pytest.mark.parametrize("phrase", ROW_FIELDS)
def test_row_field(phrase):
    assert_states(metrics_prose(), phrase)


def test_row_fields_are_in_order():
    text = metrics_prose()
    positions = []
    for number, name in enumerate(FIELD_MARKERS, start=1):
        marker = f"{number}. **{name}:**"
        assert text.count(marker) == 1, f"expected exactly one {marker!r}"
        positions.append(text.index(marker))
    assert positions == sorted(positions)


@pytest.mark.parametrize("phrase", FIGURE_RULES)
def test_figure_rule(phrase):
    assert_states(metrics_prose(), phrase)


@pytest.mark.parametrize("phrase", REFINEMENT_EXTRAS)
def test_story_refinement_extra(phrase):
    assert_states(metrics_prose(), phrase)


@pytest.mark.parametrize("phrase", STORY_TO_DONE_EXTRAS)
def test_story_to_done_extra(phrase):
    assert_states(metrics_prose(), phrase)


@pytest.mark.parametrize("phrase", TEMPLATE_BLOCK)
def test_summary_template(phrase):
    assert phrase in template_block().splitlines(), f"missing template line: {phrase}"


def test_summary_template_uses_only_the_listed_placeholders():
    assert set(re.findall(r"<[^<>]+>", template_block())) == TEMPLATE_PLACEHOLDERS
    for placeholder in TEMPLATE_PLACEHOLDERS:
        assert not re.search(r"path|dir|scratch|session|file", placeholder), placeholder


@pytest.mark.parametrize("phrase", TEMPLATE_PROSE)
def test_summary_template_rule(phrase):
    assert_states(metrics_prose(), phrase)


# A2: independence and posting rules.
INDEPENDENCE_AND_POSTING = [
    pytest.param(
        "Collected figures live only in one metrics file in the session's one scratch directory "
        "(the Scratch files rule in `references/runtimes.md`).",
        id="scratch-location",
    ),
    pytest.param(
        "Every skill passes each voter, engineer, and QA only its own per-role or per-story "
        "subdirectory of that directory, never the directory itself and never another role's "
        "files, so that no voter is handed another voter's votes or inputs.",
        id="own-subdirectory-only",
    ),
    pytest.param(
        "The poster the consuming skill names writes the metrics file and posts the summary: the "
        "facilitator for `story-refinement`, the coordinator for `story-to-done`.",
        id="writer-and-poster",
    ),
    pytest.param("The metrics file is never named in any brief.", id="never-named-in-a-brief"),
    pytest.param(
        "No brief and no voter-visible record contains this invocation's metrics or another "
        "role's figures from this invocation, other than the summary comment this invocation "
        "posts at its end.",
        id="independence-exclusion",
    ),
    pytest.param(
        "A summary comment an earlier invocation posted on the story is not a breach.",
        id="earlier-summary-not-a-breach",
    ),
    pytest.param(
        "Subject to the ordering below, the summary is posted at the end of every invocation that "
        "reaches a permitted post, as one comment on the story, read back, and repeated in the "
        "closing report (the facilitator's closing message where the skill has no report).",
        id="posting-and-read-back",
    ),
    pytest.param(
        "A resumed run is a new invocation and posts its own comment, except a resume in the same "
        "session after the owner authorizes the denied tracker writes fallback, which is the same "
        "invocation.",
        id="resumed-run",
    ),
    pytest.param(
        "Whenever the invocation ends before a post is permitted, the totals and the stop reason "
        "go in the closing report and no post is attempted.",
        id="closing-report",
    ),
    pytest.param(
        "If the post is denied or unavailable, the summary goes in the closing report with the "
        "denied write named, and no other tool or server is tried.",
        id="denied-write",
    ),
    pytest.param(
        "While a tracker write is denied and the owner has not authorized the denied tracker "
        "writes fallback, no post is attempted.",
        id="fallback-condition",
    ),
    pytest.param(
        "The comment contains no secrets and no local or scratch paths.", id="no-path-no-secret"
    ),
    pytest.param("The template has no placeholder for a path.", id="template-no-path"),
    pytest.param(
        "The comment is posted only when no further voter round will run in this invocation, "
        "after the pointing, unpointed, or split record and every slice re-estimate.",
        id="refinement-order-after-record",
    ),
    pytest.param(
        "On a stop before such a record exists, the comment is posted only after the three Stage 1 "
        "voter inputs are recorded and every voter context launched in the round that stopped "
        "has finished or stopped.",
        id="refinement-order-early-stop",
    ),
    pytest.param(
        "The comment is never posted while an anchoring recovery re-vote is still to run in this "
        "invocation.",
        id="refinement-order-anchoring",
    ),
    pytest.param(
        "The coordinator makes no tracker write other than its summary comment: the delegated "
        "engineer and QA make their own writes, and failed QA items reach the engineer in the "
        "hand-back brief, never as a coordinator tracker write.",
        id="story-to-done-only-tracker-write",
    ),
    pytest.param("The coordinator never sets the story state.", id="story-to-done-never-sets-state"),
]


@pytest.mark.parametrize("phrase", INDEPENDENCE_AND_POSTING)
def test_independence_and_posting_rule(phrase):
    assert_states(metrics_prose(), phrase)


# A3: registered in the shared index only.
README = ROOT / "shared" / "README.md"
README_ROW_START = "| `metrics.md` |"
README_ROW_DESCRIPTION = (
    "Run metrics: what a run collects, the summary template, and the independence and posting rules."
)
README_INTRO = "A capability listed here may wait for a later slice to compose it."


def files_table() -> list[str]:
    lines = README.read_text().splitlines()
    start = lines.index("| File | Capability |")
    end = start
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    return lines[start:end]


def test_shared_readme_lists_metrics():
    assert README.read_text().count(README_ROW_START) == 1, "expected exactly one metrics row"
    rows = [line for line in files_table() if line.startswith(README_ROW_START)]
    assert len(rows) == 1, "the metrics row is not in the Files table"
    assert rows[0].count("|") == 3 and rows[0].split("|")[2].strip() == README_ROW_DESCRIPTION, rows[0]


def test_shared_readme_intro_allows_an_uncomposed_capability():
    assert_states(README.read_text(), README_INTRO)


# A4: the runtime usage map.
RUNTIMES = ROOT / "shared" / "runtimes.md"
USAGE_ROW = "| Read a subagent's usage (duration, tokens, tool calls) |"
USAGE_BULLET = "- **Usage from shell-launched agents.**"
SCRATCH_BULLET = "- **Scratch files.**"
OTHER_AGENTS = (
    "Pass every other subagent and shell-launched agent you start the session's directory or a "
    "directory inside it."
)
EXAMPLE_HANDOFF = (
    "# per session. Pass each voter, engineer, or QA only its own subdirectory of the printed path,\n"
    "  # and every other subagent and shell-launched agent the printed path or a directory inside it."
)
RULES_HEADING = "## Rules that follow from the map\n"
OWN_SUBDIRECTORY = (
    "A skill passes each voter, engineer, or QA only its own subdirectory of the session "
    "directory, never the session directory itself and never another role's files, so that no "
    "voter is handed another voter's votes or inputs."
)
V1_INTRO = (
    "OpenCode V1 guidance is legacy, untested; a V1 observation recorded with its version in a "
    "cell is an observation, not V1 guidance."
)


def capability_table() -> list[str]:
    lines = RUNTIMES.read_text().splitlines()
    start = lines.index("| Capability | Claude Code | OpenCode (version-qualified) |")
    end = start
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    return lines[start:end]


def usage_row() -> str:
    assert RUNTIMES.read_text().count(USAGE_ROW) == 1, "expected exactly one usage row"
    rows = [line for line in capability_table() if line.startswith(USAGE_ROW)]
    assert len(rows) == 1, "the usage row is not in the capability table"
    return rows[0]


def rules_section() -> str:
    text = RUNTIMES.read_text()
    assert text.count(RULES_HEADING) == 1, RULES_HEADING
    rest = text[text.index(RULES_HEADING) + len(RULES_HEADING):]
    return rest[:rest.find("\n## ")] if "\n## " in rest else rest


def rule_bullet(start: str) -> str:
    assert RUNTIMES.read_text().count(start) == 1, f"expected exactly one {start!r} bullet"
    text = rules_section()
    assert start in text, f"{start!r} is not under {RULES_HEADING.strip()!r}"
    rest = text[text.index(start):]
    end = len(rest)
    for marker in ("\n- **", "\n## "):
        found = rest.find(marker, 1)
        if found != -1:
            end = min(end, found)
    return rest[:end]


def usage_bullet() -> str:
    return rule_bullet(USAGE_BULLET)


def test_scratch_files_rule_passes_each_role_only_its_own_subdirectory():
    assert_states(rule_bullet(SCRATCH_BULLET), OWN_SUBDIRECTORY)


def test_scratch_files_rule_no_longer_passes_the_session_directory():
    # Join wrapped lines of the shell example's comments so a rewrapped sentence is still found.
    bullet = flat(re.sub(r"\n\s*#\s*", " ", rule_bullet(SCRATCH_BULLET))).lower()
    for removed in (
        "pass the session's directory to every subagent",
        "pass the printed path to every subagent",
    ):
        assert removed not in bullet, removed


def test_scratch_files_rule_passes_every_other_agent_the_session_directory():
    assert_states(rule_bullet(SCRATCH_BULLET), OTHER_AGENTS)


def test_scratch_files_example_hands_each_role_only_its_own_subdirectory():
    assert EXAMPLE_HANDOFF in rule_bullet(SCRATCH_BULLET)


def test_runtime_map_intro_separates_v1_observations_from_v1_guidance():
    assert_states(RUNTIMES.read_text().split("\n|", 1)[0], V1_INTRO)


def row_cells(row: str) -> list[str]:
    """The cells of a Markdown table row, split on unescaped pipes."""
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", row)[1:-1]]


def test_runtime_map_has_one_usage_row_with_two_cells():
    cells = row_cells(usage_row())
    assert len(cells) == 3 and all(cells), "the row needs a Claude Code cell and an OpenCode cell"


def test_usage_row_claude_code_cell_is_version_qualified():
    claude_cell = row_cells(usage_row())[1]
    assert_states(claude_cell, "Observed on 2.1.312:")


def test_usage_row_opencode_cell_names_each_version_line():
    opencode_cell = row_cells(usage_row())[2]
    assert_states(opencode_cell, "V2 (2.1.2): `not observed`, not run.")
    assert_states(opencode_cell, "V1 (legacy, not V2 guidance), observed on 1.19.3:")


def test_usage_bullet_states_codex_observations_with_version():
    assert_states(usage_bullet(), "For `runtime: codex`, observed on codex-cli 0.163.0:")


def test_usage_bullet_marks_other_codex_versions_not_observed():
    assert_states(usage_bullet(), "Any other codex version is `not observed` until it is run.")


def test_usage_bullet_states_command_has_no_common_contract():
    assert_states(
        usage_bullet(),
        "For `runtime: command`, arbitrary `command` programs have no common usage contract.",
    )


def test_usage_bullet_distinguishes_not_observed_from_not_reported():
    assert_states(
        usage_bullet(),
        "`not observed` means the runtime or version line was not run; `not reported` means it "
        "ran and returned no figure.",
    )


def test_usage_row_and_bullet_name_the_metrics_reference_in_prose_only():
    for text in (usage_row(), usage_bullet()):
        assert "metrics.md" not in text, text
        assert "the run metrics reference" in text.lower(), text
