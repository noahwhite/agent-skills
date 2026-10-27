"""The shared run-metrics reference and the runtime usage map (SKL-44).

Each test pins an exact sentence or table-header fragment, so deleting the guarded phrase
from the source file fails the named test.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "shared" / "metrics.md"


def metrics_text() -> str:
    assert METRICS.is_file(), "shared/metrics.md is missing"
    return METRICS.read_text()


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
TEMPLATE = [
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
    pytest.param(
        "With no launches, the table is replaced by the line `no launches` and each total reads "
        "`not applicable`.",
        id="template-no-launches",
    ),
]


def test_metrics_reference_exists():
    assert METRICS.is_file()


def test_one_row_per_launch_the_poster_spawns():
    assert_states(metrics_text(), ROW_SCOPE)


def test_round_counters_are_listed_separately():
    assert_states(metrics_text(), ROUND_COUNTERS)


@pytest.mark.parametrize("phrase", ROW_FIELDS)
def test_row_field(phrase):
    assert_states(metrics_text(), phrase)


def test_row_fields_are_in_order():
    text = flat(metrics_text())
    positions = [text.index(flat(p.values[0])) for p in ROW_FIELDS if p.id != "runtime-is-data"]
    assert positions == sorted(positions)


@pytest.mark.parametrize("phrase", FIGURE_RULES)
def test_figure_rule(phrase):
    assert_states(metrics_text(), phrase)


@pytest.mark.parametrize("phrase", REFINEMENT_EXTRAS)
def test_story_refinement_extra(phrase):
    assert_states(metrics_text(), phrase)


@pytest.mark.parametrize("phrase", STORY_TO_DONE_EXTRAS)
def test_story_to_done_extra(phrase):
    assert_states(metrics_text(), phrase)


@pytest.mark.parametrize("phrase", TEMPLATE)
def test_summary_template(phrase):
    assert_states(metrics_text(), phrase)


# A2: independence and posting rules.
INDEPENDENCE_AND_POSTING = [
    pytest.param(
        "Collected figures live only in one metrics file inside the session's one scratch "
        "directory (the Scratch files rule in `references/runtimes.md`), outside every per-story "
        "or per-role subdirectory a voter, engineer, or QA writes into.",
        id="scratch-location",
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
        "The coordinator posts its own comment as the coordinator's only tracker write of the "
        "invocation; the delegated engineer and QA make their own writes.",
        id="story-to-done-only-tracker-write",
    ),
    pytest.param("The coordinator never sets the story state.", id="story-to-done-never-sets-state"),
]


@pytest.mark.parametrize("phrase", INDEPENDENCE_AND_POSTING)
def test_independence_and_posting_rule(phrase):
    assert_states(metrics_text(), phrase)


def test_template_has_no_path_placeholder():
    template = metrics_text().split("```text", 1)[1].split("```", 1)[0]
    assert "path" not in template.lower() and "dir" not in template.lower(), template


# A3: registered in the shared index only.
README = ROOT / "shared" / "README.md"
README_ROW = "| `metrics.md` | Run metrics: what a run collects, the summary template, and the independence and posting rules. |"
README_INTRO = "A capability listed here may wait for a later slice to compose it."


def test_shared_readme_lists_metrics():
    assert README_ROW in README.read_text().splitlines()


def test_shared_readme_intro_allows_an_uncomposed_capability():
    assert_states(README.read_text(), README_INTRO)

