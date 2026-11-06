"""Contract checks for the linear-user-story filing skill's team rows (SKL-204)."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "linear-user-story" / "SKILL.md"

TEAM_KEY_ROW = (
    "| `ABC` (team key, for the CLI) | the prefix of the named issue's key when a caller supplies one "
    "(Team resolution in [references/linear.md](references/linear.md)), else `profile.tracker.team_key` |"
)
TEAM_NAME_ROW = (
    "| team name (for the MCP server) | the name of that issue's team, resolved from its key, when a caller "
    "supplies a named issue, else `profile.tracker.team_name` |"
)


def test_team_rows_take_a_named_issue_team_and_otherwise_keep_the_profile() -> None:
    lines = SKILL.read_text().splitlines()
    assert TEAM_KEY_ROW in lines
    assert TEAM_NAME_ROW in lines
    assert "| `ABC` (team key, for the CLI) | `profile.tracker.team_key` |" not in lines


def test_cli_and_mcp_steps_read_the_team_from_the_profile_values_table() -> None:
    text = SKILL.read_text()
    assert "# ABC = profile.tracker.team_key" not in text
    assert "`team` = `profile.tracker.team_name`" not in text
    assert "# ABC = the team key from Profile values (the CLI resolves the key, not the team name)" in text
    assert "`team` = the team name from Profile values" in text
