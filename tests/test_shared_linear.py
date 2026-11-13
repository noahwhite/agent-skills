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

# The split rule runs from its first bullet to the end of the section, verbatim: any sentence added inside it,
# an owner hand-off, a stop condition or an approval of an oversize slice, fails the exact match.
SPLIT_RULE_FIRST_LINE = (
    "- ⛔ Split a story whose estimate is above `profile.refinement.point_cap` or is 8 or more, without asking, "
    "before it is assigned or work is delegated, and present the slices."
)
SPLIT_RULE_BLOCK = "\n".join(
    (
        SPLIT_RULE_FIRST_LINE,
        "  This is one split rule for an estimate recorded at refinement and for one made outside a ceremony, "
        "at filing or triage.",
        "  Keep the original issue for the core slice, create siblings for the rest, and wire blocked-by or related "
        "edges.",
        "- ⛔ Split every resulting slice that still meets that trigger again, as many rounds as it takes, "
        "until no slice meets it; there is no escalation exit.",
        "  Split along the first boundary that applies, in this order:",
        "  1. the planned PR or slice boundary;",
        "  2. an acceptance criterion;",
        "  3. where one acceptance criterion alone still meets the trigger, that criterion is rewritten at "
        "refinement or triage into narrower observable criteria (by artifact, case or environment) that keep the "
        "same coverage, and the slice is split along them;",
        "  4. the smallest outcome that can be reviewed, merged and verified on its own, including enabling work "
        "such as interface or schema first and behaviour second.",
        "",
        "  No rung discards scope, delegates an oversize slice or hands one to the owner as an estimate.",
        "- ⛔ Never split an issue at close time to carve off unfinished work; that is status laundering.",
    )
)


@pytest.mark.parametrize("path", [SHARED_LINEAR, *VENDORED_LINEAR], ids=lambda p: str(p.relative_to(ROOT)))
def test_one_split_rule_resplits_in_boundary_order_with_no_escalation_exit(path: Path) -> None:
    estimation = section(path.read_text(), "Estimation and slicing")
    start = estimation.find(SPLIT_RULE_FIRST_LINE)
    assert start != -1, "Estimation and slicing has no split rule bullet"
    assert estimation[start:].strip() == SPLIT_RULE_BLOCK, "the split rule differs from the SKL-230 rule"
    mentions = re.findall(r"escalat\w*", estimation, re.IGNORECASE)
    expected = re.findall(r"no escalation exit", estimation, re.IGNORECASE)
    assert len(mentions) == len(expected), f"an escalation mention other than 'no escalation exit' remains: {mentions}"


def test_vendored_linear_copies_are_found() -> None:
    assert VENDORED_LINEAR, "no skill vendors references/linear.md; the copy checks above would be vacuous"
