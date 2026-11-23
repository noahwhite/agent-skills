"""Lean acceptance criteria: the filing rule in shared/linear.md and the user-story template.

Each pinned sentence is matched per source line, so deleting any one fails exactly one test.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SHARED_LINEAR = ROOT / "shared" / "linear.md"
USER_STORY_SKILL = ROOT / "skills" / "linear-user-story" / "SKILL.md"

RULE_LINES = (
    "- Write each acceptance criterion as one rule with one observable outcome: one sentence that states the state "
    "or behaviour reached, never how to reach it.",
    "  Aim for at most 25 words per criterion and treat more than 40 as a trigger to rewrite it; no source sets a "
    "word limit, so this is house style.",
    '  A criterion never joins two outcomes with "and".',
    "  Aim for 3 to 5 criteria per story, a common practitioner rule of thumb and not a standard; more criteria, "
    "or two independently deliverable outcomes, means rewrite the criteria or split the story.",
    "- Keep these out of the criteria: commands and flags, script and file names, polling intervals and window "
    "sizes, execution order, who merges, and how evidence is posted.",
    "  Evidence conventions live once in the Definition of Done, never in a criterion.",
    '- Required failure behaviour is its own criterion, for example "a rolled-back tenant returns to held".',
    "  Restoration steps, notifications and diagnostics belong in the runbook.",
    "- Use Given/When/Then for event-driven behaviour and a plain rule for an invariant, a threshold or a "
    "configuration state.",
)

TEMPLATE_LINES = (
    "<!-- 3 to 5 criteria, one rule and one observable outcome each, at most 25 words, no commands, steps, "
    "window values or evidence instructions -->",
    "- [ ] [System or component] reaches [target state or metric] under [condition]",
    "- [ ] Given [precondition], when [event], then [one observable outcome]",
    "- [ ] On [failure condition], [system] [observable abort or recovery state]",
    "* Runbook or test plan: [Link, where execution detail is needed]",
    "**🔎 Verification**",
    "* Evidence follows the Definition of Done",
)

SKILL_RULE_LINE = (
    "  Write them lean as that section states: 3 to 5 per story, one rule and one observable outcome each, at "
    "most 25 words, with no command, step, window value or evidence instruction inside a criterion."
)
REMOVED_TEMPLATE_LINES = ("- [ ] Clear, testable criteria", "- [ ] Use Given/When/Then format if applicable")


def lines(path: Path) -> list[str]:
    return path.read_text().splitlines()


@pytest.mark.parametrize("pinned", RULE_LINES)
def test_shared_linear_carries_each_lean_rule_line(pinned: str) -> None:
    assert pinned in lines(SHARED_LINEAR)


@pytest.mark.parametrize("pinned", TEMPLATE_LINES)
def test_user_story_template_carries_each_lean_line(pinned: str) -> None:
    assert pinned in lines(USER_STORY_SKILL)


def test_user_story_rules_point_at_the_lean_section() -> None:
    assert SKILL_RULE_LINE in lines(USER_STORY_SKILL)


@pytest.mark.parametrize("removed", REMOVED_TEMPLATE_LINES)
def test_user_story_template_drops_the_vague_placeholders(removed: str) -> None:
    assert removed not in lines(USER_STORY_SKILL)
