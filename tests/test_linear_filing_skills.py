"""Contract checks for the team rows of the linear-* filing skills and the epic's one-team rule (SKL-204)."""

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
FILING_SKILLS = ("linear-bug", "linear-epic", "linear-investigation", "linear-spike", "linear-user-story")
EPIC = ROOT / "skills" / "linear-epic" / "SKILL.md"

TEAM_KEY_ROW = (
    "| `ABC` (team key, for the CLI) | the prefix of the named issue's key when a caller supplies one "
    "(Team resolution in [references/linear.md](references/linear.md)), else `profile.tracker.team_key` |"
)
TEAM_NAME_ROW = (
    "| team name (for the MCP server) | the name of that issue's team, resolved from its key, when a caller "
    "supplies a named issue, else `profile.tracker.team_name` |"
)
CLI_TEAM_COMMENT = "# ABC = the team key from Profile values (the CLI resolves the key, not the team name)"
MCP_ISSUE_TEAM = "`team` = the team name from Profile values"
MCP_EPIC_TEAM = "`addTeams` = [the team name from Profile values]"

EPIC_SEARCH = (
    "- **Search first:** run `linear project list --team ABC`, with `ABC` from Profile values (the named issue's "
    "team when a caller supplies one, else `profile.tracker.team_key`); the epic may already exist under a sibling name."
)
EPIC_ONE_TEAM = "- **One team:** an epic belongs to exactly one team, the `ABC` team, and never spans teams."
CROSS_TEAM_PHRASES = ("cross-team", "spans teams", "span teams", "multiple teams", "across teams")


def skill_text(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text()


@pytest.mark.parametrize("name", FILING_SKILLS)
def test_team_rows_take_a_named_issue_team_and_otherwise_keep_the_profile(name: str) -> None:
    lines = skill_text(name).splitlines()
    assert TEAM_KEY_ROW in lines, f"{name} lacks the named-issue team key row"
    assert TEAM_NAME_ROW in lines, f"{name} lacks the named-issue team name row"
    assert "| `ABC` (team key, for the CLI) | `profile.tracker.team_key` |" not in lines
    assert "| team name (for the MCP server) | `profile.tracker.team_name` |" not in lines


@pytest.mark.parametrize("name", FILING_SKILLS)
def test_cli_and_mcp_steps_read_the_team_from_the_profile_values_table(name: str) -> None:
    text = skill_text(name)
    assert "# ABC = profile.tracker.team_key" not in text
    assert "`team` = `profile.tracker.team_name`" not in text
    assert "[`profile.tracker.team_name`]" not in text
    assert CLI_TEAM_COMMENT in text, f"{name} CLI step does not read the team from Profile values"
    mcp_team = MCP_EPIC_TEAM if name == "linear-epic" else MCP_ISSUE_TEAM
    assert mcp_team in text, f"{name} MCP step does not read the team from Profile values"


def test_epic_search_is_scoped_to_one_team() -> None:
    lines = EPIC.read_text().splitlines()
    assert EPIC_SEARCH in lines
    assert "- **Search first:** run `linear project list`; the epic may already exist under a sibling name." not in lines


def test_epic_belongs_to_exactly_one_team() -> None:
    text = EPIC.read_text()
    assert EPIC_ONE_TEAM in text.splitlines()
    assert "setTeams" not in text, "the MCP step still offers replacing the team set"


def test_no_skill_or_shared_file_implies_a_cross_team_epic() -> None:
    paths = [ROOT / "shared" / "linear.md", *sorted((ROOT / "skills").glob("*/SKILL.md"))]
    for path in paths:
        text = path.read_text().lower().replace("never spans teams", "")
        for phrase in CROSS_TEAM_PHRASES:
            assert phrase not in text, f"{path.relative_to(ROOT)} implies a cross-team epic: {phrase!r}"
