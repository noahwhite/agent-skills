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
    "(`ABC` in `ABC-123`): the CLI `--team` takes the prefix, and MCP calls take the team name resolved "
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
    "and `linear label list --team <KEY>`, where `<KEY>` is the team key, the issue key's prefix; use the "
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
    assert FILING_ON_BEHALF in spaced(section(text, "Filing issues"))
    assert MCP_TEAM in spaced(section(text, "Linear MCP fallback"))


def test_vendored_linear_copies_are_found() -> None:
    assert VENDORED_LINEAR, "no skill vendors references/linear.md; the copy checks above would be vacuous"
