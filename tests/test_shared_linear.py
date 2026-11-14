"""Contract checks for shared/linear.md: estimate reads and team resolution."""

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
SHARED_LINEAR = ROOT / "shared" / "linear.md"
VENDORED_LINEAR = sorted((ROOT / "skills").glob("*/references/linear.md"))


def spaced(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def section(text: str, heading: str) -> str:
    assert f"\n## {heading}\n" in text, f"missing section: {heading}"
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def test_estimate_read_paths_and_cli_display_limitations() -> None:
    text = SHARED_LINEAR.read_text()
    estimation = text.split("## Estimation and slicing\n", 1)[1].split("\n## ", 1)[0]
    lines = {line.strip().removeprefix("- ") for line in estimation.splitlines()}
    expected = {
        "`linear issue view --json` omits `estimate`, as it omits relations, "
        "even when the issue carries one, and the plain view prints no estimate line.",
        "Read an estimate with `linear api 'query { issue(id: \"ABC-123\") { estimate } }'`, "
        "or through the Linear MCP `get_issue` with the `estimate` field.",
        "The team issue list renders it in its estimate column, "
        "which is a display path, not a read path for a script.",
    }
    assert expected <= lines, f"missing estimate-read guidance: {expected - lines}"


# --- SKL-204: the invoked issue key decides the team; the profile's team is the fallback only ---------

INTRO_TEAM = (
    "The team for an operation on or for an issue named by key is that key's prefix, "
    "and `profile.tracker.team_key` is the team only when no issue is named (Team resolution, below)."
)
NAMED_ISSUE_TEAM = (
    "For any operation on or for an issue the caller named by key, the team is that key's prefix "
    "(`ABC` in `ABC-123`): the CLI `--team` takes the prefix on a command that accepts `--team` "
    "(a command addressed by the issue key, such as `linear issue view <key>`, takes the key and no `--team`), "
    "and MCP calls take the team name resolved "
    "from that key (the team in the team list, `linear team list` or the Linear MCP list_teams tool, "
    "whose key matches the prefix), never `profile.tracker.team_name`."
)
FAILED_RESOLUTION = "A failed resolution stops the step and asks."
PROFILE_FALLBACK = (
    "`profile.tracker.team_key` and `profile.tracker.team_name` apply only to operations that name no issue "
    "and follow no invoked key: standalone filing, listing or searching the backlog."
)
DIFFERING_TEAM = (
    "Differing team: when the named issue's team differs from `profile.tracker.team_key`, each profile state "
    "or label name (including `profile.tracker.states.ready` and `profile.tracker.states.backlog`, and the "
    "labels on split siblings) is used only after it is confirmed on that team with `linear team states <KEY>` "
    "and `linear label list --team <KEY>` (whose listing includes the workspace labels), where `<KEY>` is the team key, the issue key's prefix; use the "
    "Linear MCP list_issue_statuses and list_issue_labels tools if the CLI fails."
)
DIFFERING_TEAM_STOP = (
    "A missing name, an unknown team or a failed listing stops the step before any write and asks; "
    "no other name is substituted."
)
FILING_ON_BEHALF = (
    "Filing or searching on behalf of a named issue (a split sibling of it, a backlog or epic search for it) "
    "uses that issue's team (Team resolution); the profile's team applies only when no issue is named."
)
MCP_TEAM = (
    "Tools take `team` as the team name and the CLI takes `--team` with the team key, both resolved as "
    "Team resolution states: from the named issue's key, else `profile.tracker.team_name` and "
    "`profile.tracker.team_key`."
)
BACKLOG_SEARCH = (
    "Search the team backlog and existing epics before creating (`linear issue query --search <term> --team <KEY>` "
    "for issues and `linear project list --team <KEY>` for epics, with `<KEY>` the team key from Team resolution, "
    "or the Linear MCP server's list_issues and list_projects tools with a filter); the issue may already exist."
)
OLD_BACKLOG_SEARCH = "`linear issue list` with a query"
OLD_MCP_TEAM = "the CLI takes `--team` with `profile.tracker.team_key`."
OLD_INTRO_TEAM = "The team is `profile.tracker.team_key`;"


@pytest.mark.parametrize("path", [SHARED_LINEAR, *VENDORED_LINEAR], ids=lambda p: str(p.relative_to(ROOT)))
def test_named_issue_key_decides_the_team(path: Path) -> None:
    text = path.read_text()
    flat = spaced(text)
    assert OLD_INTRO_TEAM not in flat, "the intro still makes the profile's team key the team for everything"
    assert OLD_MCP_TEAM not in flat, "the MCP fallback still ties the CLI team to the profile's team key"
    assert INTRO_TEAM in flat
    resolution = spaced(section(text, "Team resolution"))
    for sentence in (NAMED_ISSUE_TEAM, FAILED_RESOLUTION, PROFILE_FALLBACK, DIFFERING_TEAM, DIFFERING_TEAM_STOP):
        assert sentence in resolution, sentence
    filing = spaced(section(text, "Filing issues"))
    assert FILING_ON_BEHALF in filing
    assert BACKLOG_SEARCH in filing, "the backlog search does not name a command that searches a team"
    assert OLD_BACKLOG_SEARCH not in flat, "`linear issue list` has no query option"
    assert MCP_TEAM in spaced(section(text, "Linear MCP fallback"))


# --- SKL-230: one split rule for refinement, filing and triage; re-split with no escalation exit ------

# Owner decision (SKL-230): pin only the split rule, whitespace-normalised, as two whole top-level bullets, plus the
# unchanged close-time bullet. A line added inside a pinned bullet, or a pinned bullet nested under another, fails;
# sibling bullets elsewhere in the section (such as SKL-239's, which may sit between the two) and a rewrap pass.
SPLIT_BULLET = " ".join(
    (
        "- ⛔ Split a story whose estimate is above `profile.refinement.point_cap` or is 8 or more, without asking, "
        "before it is assigned or work is delegated, and present the slices.",
        "This is one split rule for an estimate recorded at refinement and for one made outside a ceremony, "
        "at filing or triage.",
        "Keep the original issue for the core slice, create siblings for the rest, and wire blocked-by or related "
        "edges.",
    )
)
# SKL-305: a slice adds no scope, and its criteria map back to the story it is split from before any estimate.
NO_SCOPE_GROWTH = (
    "No slice grows scope: a slice carries only the acceptance criteria, scope and evidence of the story it is split "
    "from, and adds no criterion, evidence pass, fixture, test obligation or behaviour that story does not already "
    "contain.",
    "The split comment maps every slice criterion to exactly one criterion of the story it is split from, and so on "
    "back to the whole story; several slice criteria may map to one criterion of that story (rung 3).",
    "The mapping check runs in each split round before any slice is pointed: each slice criterion with no "
    "counterpart and each evidence pass, fixture, test obligation or behaviour a slice adds beyond the story it is "
    "split from are all named in one `needs input` message, and the round stops before any slice is pointed, so no "
    "check that needs a slice value runs.",
)
# SKL-304 replaced the re-split bullet: at most two split rounds, and SKL-230's never-escalate rule is superseded.
RESPLIT_BULLET = " ".join(
    (
        "- ⛔ Split a resulting slice that still meets that trigger again, for at most two split rounds: split round 1 "
        "splits the whole story and split round 2 splits the round-1 slices that still meet it.",
        "This bound supersedes the never-escalate rule of SKL-230.",
        "Each resulting slice gets its own estimate, made the way the story's was (at refinement, filing or triage), "
        "before it is tested against that trigger.",
        "A slice that cannot be estimated is recorded as unpointed and reported as `needs input` to the owner, "
        "naming the story and the slice, and also the derived values when a refinement voter round produced them, "
        "as the unpointed variance stop in story-refinement's Split rule does.",
        "Split along the first boundary that applies, in this order:",
        "1. the planned PR or slice boundary;",
        "2. an acceptance criterion;",
        "3. where one acceptance criterion alone still meets the trigger, that criterion is rewritten at "
        "refinement or triage into narrower observable criteria (by artifact, case or environment) that keep the "
        "same coverage, and the slice is split along them;",
        "4. the smallest outcome that can be reviewed, merged and verified on its own, including enabling work "
        "such as interface or schema first and behaviour second.",
        "No rung discards scope, delegates an oversize slice or hands one to the owner as an estimate.",
        *NO_SCOPE_GROWTH,
    )
)
# SKL-305: a slice's recorded value is its lower consensus value, and the lower-consensus band governs.
LOWER_CONSENSUS_SUMS = (
    "A slice's recorded value is the lower value of a within-one-step consensus (story-refinement Split rule), so "
    "each sum is formed from the lower-consensus values, and when the lower and the higher sums fall in different "
    "bands the lower-consensus band governs.",
    "Every band stop or warning names the sum both ways (with each slice's lower and with its higher consensus "
    "value, the two values a within-one-step consensus spans, which are one value otherwise), the band of each sum, "
    "both bounds (1.0 times and 1.5 times the base) and the round.",
)
# SKL-305: the checks run in a fixed order and a round reports all its failures, and all its warnings, together.
CHECK_ORDER = (
    "The checks run in the order listed, the round cap after split round 2 only, and every applicable check runs "
    "before any stop is enforced: all failures of the round are reported in one `needs input` message and all its "
    "warnings in one split-comment entry, which a round that stops also carries in that message and posts with the "
    "split comment once the owner answers.",
    "A round-1 slice that still meets the split trigger goes to split round 2.",
    "In round 1 the only parent is the original story, so the per-parent band is the whole-story band and is "
    "recorded once.",
)
SPLIT_BOUNDS_BULLET = " ".join(
    (
        "- ⛔ Bound every split of an estimated story made under the two bullets above (the Bug and Investigation "
        "split below gives no slice a point value, so these checks never run on it): after each split round, and "
        "before any further split round, slice record or tracker write for the slices, run these checks:",
        "1. Per-parent bound: each slice's recorded value is strictly below the recorded value of the story it is "
        "split from, where a round-1 parent's value is the recorded whole-story estimate and a round-2 parent's value "
        "is its round-1 recorded value; the slices of one parent are compared to that parent as a set by the bands "
        "below on their sum, and a slice at or above its parent stops with `needs input` naming the parent, the "
        "slice, both values and the band.",
        "2. Whole-story sum: the sum of the recorded values of the current leaf slices (a slice that is split again "
        "is replaced by its sub-slices) is compared to the original whole-story recorded estimate by the bands below.",
        "3. Round cap: a slice that still meets the split trigger after split round 2 stops with `needs input` naming "
        "the slices and their values, before a third split is made, and no third-round split, estimate, record or "
        "tracker write happens.",
        "The bands compare a sum to its base (the parent's value in check 1, the original whole-story recorded "
        "estimate in check 2): above 1.5 times the base stops with `needs input`; above 1.0 times and up to and "
        "including 1.5 times proceeds with a warning in the split comment that a human reads at triage; at or below "
        "1.0 times proceeds with no flag.",
        *LOWER_CONSENSUS_SUMS,
        *CHECK_ORDER,
        "When the original whole-story recorded estimate is the highest value of the step sequence for "
        "`profile.tracker.estimate_scale` (story-refinement Step 4 item 1), every stop and warning whose base is that "
        "estimate states that the base is saturated and that the 1.0 and 1.5 bounds computed from it are lower "
        "bounds on the true size.",
        "A stop holds every further split round, record and tracker write for the slices until the owner answers; a "
        "split that completes within two rounds with no stop proceeds unchanged.",
        "A round with a leaf slice recorded as unpointed still runs the per-parent bound and the round cap on each "
        "recorded slice value, which stop as above, and every per-parent sum whose slices all have recorded values.",
        "For the whole-story sum and the sum of each parent with an unpointed slice, the sum of the recorded values "
        "is a lower bound on the true sum: a lower bound above 1.5 times the base stops as above with band stop, and "
        "otherwise that comparison is pending, because a warning or no flag can still change once the slice is "
        "valued.",
        "A stop in such a round routes as any stop, and its message names each unpointed slice; with no stop, the "
        "split comment records the pending comparisons beside that slice's `needs input`, and they run, with the "
        "per-parent bound and the round cap of each unpointed slice, once the owner's answer gives every leaf slice "
        "a recorded value, before any further split round, record or tracker write for the slices.",
        "Worked examples are in the Split bounds section of the story-refinement skill's refinement record reference.",
    )
)
CLOSE_TIME = "- ⛔ Never split an issue at close time to carve off unfinished work; that is status laundering."
# SKL-307: every pointing round after the first gives each slice voter the prior rounds by its brief.
PRIOR_ROUND_CONTEXT = (
    "Every pointing round after a story's first, a slice estimate in either split round, gives each voter in its "
    "slice brief, as text, the prior-round context: the parent's recorded value and the three voter values of the "
    "parent's round, the ledger, and the recorded rationales of the whole-story round and of the slice's ancestor "
    "rounds only, never a voided vote or rationale, a ground the story-refinement Step 4 basis review challenged, or a "
    "sibling slice's value or rationale.",
    "The brief states the per-parent bound only in the Slice brief template's fixed sentence, as a bound and never as "
    "a value to score.",
    "Slice voters still run in newly created contexts, so the prior rounds reach them by the brief and never by "
    "session reuse, and the values of the same round, the sibling slices' and the round's other voters', stay hidden "
    "until every vote of the round is recorded.",
    "The facilitator records each slice brief verbatim in the slice's pointing record.",
)
# SKL-306: a shared unknown is priced once, in a ledger every whole-story pointing round records.
LEDGER_BULLET = " ".join(
    (
        "- ⛔ Price a shared unknown once, in the priced shared-unknown ledger that every whole-story pointing round "
        "records (story-refinement Steps 3 and 4).",
        "Each voter lists, with its value, the unknowns behind that value with a point price each and the remainder, "
        "its non-unknown complexity; the prices plus the remainder sum exactly to the voter's value (in a re-vote, the "
        "highest value of its accepted set), and a rationale whose prices plus remainder differ from its value is "
        "off-basis.",
        "After the consensus check, once story-refinement Step 4 has recorded the estimate or the unpointed variance "
        "stop, the facilitator records one ledger in the pointing record from the rationales that stand: it merges "
        "unknowns that voters named differently and records each merge, takes one price per voter for each merged "
        "unknown (the voter's lowest, when it listed that unknown more than once), and prices each unknown at "
        "the median of the prices of the voters who listed it, the lower of the two prices when two listed it, or the "
        "sole price when one did.",
        "Ledger prices are not rounded; the ledger total is recorded beside the whole-story value and is not "
        "reconciled to slice values, and a slice value is a vote on the step sequence.",
        "A ledger from a saturated whole-story value (the highest value of the step sequence, as the bullet above "
        "states) carries the saturation note, that its prices are lower bounds on the true size, and is not adjusted.",
        "Each unknown has exactly one owner slice, the slice whose work resolves it, else the core slice, assigned "
        "when the split is drafted; an unsplit story records the ledger without owners, and a slice that is split "
        "again reassigns its owned unknowns to its sub-slices by the same rule, recorded in the split comment of split "
        "round 2, from which each sub-slice brief takes its owners.",
        "An unknown that a blocker story's work resolves is owned by that blocker story and is priced in no slice.",
        "Every slice brief, the pointing prompt of a slice estimate, carries the ledger with its prices and owners, "
        "and when the whole-story value is saturated it states that the ledger prices are lower bounds.",
        *PRIOR_ROUND_CONTEXT,
        "A slice voter never re-prices an unknown: its rationale states the ledger price of each unknown its slice "
        "owns plus its own non-unknown complexity.",
        "A slice rationale that omits an unknown its slice owns, re-prices an unknown, prices one the ledger does not "
        "carry, or names one the ledger assigns elsewhere is off-basis: the "
        "story-refinement Step 4 basis review re-runs that vote once on its existing terms, and a second miss is "
        "recorded.",
        "Worked examples are in the Slice brief section of the story-refinement skill's refinement record reference.",
    )
)
# The SKL-230 sentences SKL-304 removes, split so a repository search for them finds no literal copy here.
STALE_SPLIT_SENTENCES = (
    "the split repeats until " + "no slice meets the split trigger",
    "There is no escalation exit " + "for an oversize slice",
    "as many rounds as it takes, " + "until no slice meets it; there is no escalation exit",
)


def top_level_bullets(section_text: str) -> list[str]:
    """The section's top-level bullets, each whitespace-normalised.

    An indented or blank line belongs to the bullet above; any other line (a heading, a paragraph) ends it.
    """
    bullets: list[str] = []
    open_bullet = False
    for line in section_text.splitlines():
        if line.startswith("- "):
            bullets.append(line)
            open_bullet = True
        elif open_bullet and (not line.strip() or line[0].isspace()):
            bullets[-1] += "\n" + line
        else:
            open_bullet = False
    return [spaced(bullet) for bullet in bullets]


@pytest.mark.parametrize("path", [SHARED_LINEAR, *VENDORED_LINEAR], ids=lambda p: str(p.relative_to(ROOT)))
def test_one_split_rule_resplits_in_boundary_order_within_the_split_bounds(path: Path) -> None:
    bullets = top_level_bullets(section(path.read_text(), "Estimation and slicing"))
    for bullet in (SPLIT_BULLET, RESPLIT_BULLET, SPLIT_BOUNDS_BULLET, CLOSE_TIME):
        assert bullet in bullets, f"Estimation and slicing has no top-level bullet equal to: {bullet[:60]}"
    order = [bullets.index(b) for b in (SPLIT_BULLET, RESPLIT_BULLET, SPLIT_BOUNDS_BULLET, CLOSE_TIME)]
    assert order == sorted(order), "the split, re-split, split-bounds and close-time bullets are out of order"


@pytest.mark.parametrize("path", [SHARED_LINEAR, *VENDORED_LINEAR], ids=lambda p: str(p.relative_to(ROOT)))
def test_superseded_never_escalate_sentences_are_gone(path: Path) -> None:
    flat = spaced(path.read_text())
    for sentence in STALE_SPLIT_SENTENCES:
        assert sentence not in flat, f"{path.relative_to(ROOT)} still carries the superseded sentence: {sentence}"


@pytest.mark.parametrize("path", [SHARED_LINEAR, *VENDORED_LINEAR], ids=lambda p: str(p.relative_to(ROOT)))
def test_ledger_bullet_follows_the_split_bounds(path: Path) -> None:
    bullets = top_level_bullets(section(path.read_text(), "Estimation and slicing"))
    assert LEDGER_BULLET in bullets, "Estimation and slicing has no top-level priced shared-unknown ledger bullet"
    assert bullets.index(LEDGER_BULLET) == bullets.index(SPLIT_BOUNDS_BULLET) + 1


def test_vendored_linear_copies_are_found() -> None:
    assert VENDORED_LINEAR, "no skill vendors references/linear.md; the copy checks above would be vacuous"
