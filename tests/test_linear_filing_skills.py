"""Contract checks for the team rows of the linear-* filing skills and the epic's one-team rule (SKL-204)."""

import re
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

# A sentence about an epic (or project) and teams that uses one of these words puts an epic in more than one
# team, unless it is negated or states the one-team rule.
MULTI_TEAM_WORDS = re.compile(
    r"\bspan|cross[- ]team|multi[- ]team|multiple teams|several teams|more than one team|\bother teams?\b"
    r"|another team|across teams|two teams|both teams|setTeams",
    re.IGNORECASE,
)
ONE_TEAM_WORDS = re.compile(r"\bnever\b|\bnot\b|n't\b|\bno\b|\bexactly one team\b", re.IGNORECASE)
EPIC_WORDS = re.compile(r"\bepics?\b|\bprojects?\b", re.IGNORECASE)
TEAM_WORDS = re.compile(r"\bteams?\b|setTeams", re.IGNORECASE)
SENTENCE = re.compile(r"[^.\n]+")


def skill_text(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text()


def epic_multi_team_sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in SENTENCE.findall(text)
        if EPIC_WORDS.search(sentence)
        and TEAM_WORDS.search(sentence)
        and MULTI_TEAM_WORDS.search(sentence)
        and not ONE_TEAM_WORDS.search(sentence)
    ]


@pytest.mark.parametrize("name", FILING_SKILLS)
def test_team_rows_take_a_named_issue_team_and_otherwise_keep_the_profile(name: str) -> None:
    lines = skill_text(name).splitlines()
    assert TEAM_KEY_ROW in lines, f"{name} lacks the named-issue team key row"
    assert TEAM_NAME_ROW in lines, f"{name} lacks the named-issue team name row"
    assert "| `ABC` (team key, for the CLI) | `profile.tracker.team_key` |" not in lines
    assert "| team name (for the MCP server) | `profile.tracker.team_name` |" not in lines
    assert "| Placeholder | Value |" in lines, f"{name} table header still reads as profile keys only"
    assert "| Placeholder | Profile key |" not in lines


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
    assert "| **Extra Large (XL)** | Cross-team" not in text, "the XL size row still describes a cross-team epic"


def test_no_skill_or_shared_file_implies_a_cross_team_epic() -> None:
    paths = [*sorted((ROOT / "shared").glob("*.md")), *sorted((ROOT / "skills").rglob("*.md"))]
    for path in paths:
        hits = epic_multi_team_sentences(path.read_text())
        assert not hits, f"{path.relative_to(ROOT)} implies an epic in more than one team: {hits}"


@pytest.mark.parametrize(
    ("sentence", "flagged"),
    [
        ("An epic can span other teams.", True),
        ("Attach the project to another team too.", True),
        ("Cross-team epics are sized XL.", True),
        ("Attach the epic's teams through setTeams.", True),
        ("An epic can belong to two teams.", True),
        ("An epic does not span teams.", False),
        ("An epic belongs to exactly one team, the `ABC` team, and never spans teams.", False),
        ("Cross-team collaboration can help diagnose the bug.", False),
    ],
)
def test_the_multi_team_scan_flags_only_multi_team_epics(sentence: str, flagged: bool) -> None:
    assert bool(epic_multi_team_sentences(sentence)) is flagged
