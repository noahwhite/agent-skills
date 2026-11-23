"""Lean acceptance criteria: the filing rule in shared/linear.md and the user-story template.

Rule lines are pinned inside the "Acceptance criteria and scope" section with their bullet prefix, and
template lines under their own heading inside the fenced template. HTML comments are stripped first, so
text hidden in a comment or moved outside its section does not satisfy a pin.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SHARED_LINEAR = ROOT / "shared" / "linear.md"
USER_STORY_SKILL = ROOT / "skills" / "linear-user-story" / "SKILL.md"

RULE_LINES = (
    "- An acceptance criterion that needs behavioural evidence has one artifact that proves it and one command, "
    "run or record that produces that artifact, and that artifact must be producible in one pass by one role.",
    "  A user story names that artifact and that command, run or record in its Verification section, never "
    "inside the criterion; a Bug or a Spike, whose template has no Verification section, names both inside the "
    "criterion.",
    "- Write each acceptance criterion as one rule with one observable outcome: one sentence that states the state "
    "or behaviour reached, never how to reach it.",
    "  Use at most 25 words per criterion, not counting the proving artifact and command a Bug or a Spike names "
    "in it; no source sets a word limit, so this is house style.",
    '  A criterion never joins two outcomes with "and".',
    "  Aim for 3 to 5 criteria per story, a common practitioner rule of thumb and not a standard; more criteria, "
    "or two independently deliverable outcomes, means rewrite the criteria or split the story.",
    "- Keep these out of the criteria: commands and flags, script and file names, polling intervals and window "
    "sizes, execution order, who merges, and how evidence is posted.",
    "  The engineer decides them; the one exception is the proving artifact and command a Bug or a Spike names "
    "in its criterion, as the evidence rule above states.",
    "  Where a user story needs them recorded, a runbook or test plan linked in its Additional Context holds them.",
    "  Evidence conventions live once in the Definition of Done, never in a criterion.",
    '- Required failure behaviour is its own criterion, for example "a rolled-back tenant returns to held".',
    "  Restoration steps, notifications and diagnostics belong in the runbook.",
    "  When building the failure path is major work, it is its own story.",
    "- Use Given/When/Then for event-driven behaviour and a plain rule for an invariant, a threshold or a "
    "configuration state.",
    "  A constraint the owner imposes, such as an excluded host or a tenant that stays held, is a short fact in a "
    "criterion or, in a user story, in Additional Context, never a procedure.",
)

TEMPLATE_SECTIONS = (
    (
        "**✅ Acceptance Criteria**",
        (
            "- [ ] [System or component] reaches [target state or metric] under [condition]",
            "- [ ] Given [precondition], when [event], then [one observable outcome]",
            "- [ ] On [failure condition], [system] [observable abort or recovery state]",
        ),
    ),
    (
        "**📝 Additional Context**",
        (
            "* Constraints: [Owner-imposed facts, such as an excluded host]",
            "* Runbook or test plan: [Link, where execution detail is needed]",
        ),
    ),
    (
        "**🔎 Verification**",
        (
            "* [The one artifact that proves each criterion that needs behavioural evidence, and the single run or "
            "record that produces it]",
            "* Evidence follows the Definition of Done",
        ),
    ),
)
TEMPLATE_CASES = tuple(
    pytest.param(heading, line, id=f"{heading.split()[-1].strip('*')}-{index}")
    for heading, pinned in TEMPLATE_SECTIONS
    for index, line in enumerate(pinned)
)

SKILL_RULE_LINES = (
    "  Write them lean, as that section states: one rule and one observable outcome each, at most 25 words, and "
    "none of the execution detail that section keeps out of a criterion.",
    "  Link any runbook or test plan under Additional Context, and name the proving artifact and the command, run "
    "or record that produces it under Verification.",
)
REMOVED_TEMPLATE_LINES = ("- [ ] Clear, testable criteria", "- [ ] Use Given/When/Then format if applicable")


def visible_lines(text: str) -> list[str]:
    """The lines of text with every HTML comment removed."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).splitlines()


def scope_section() -> list[str]:
    text = SHARED_LINEAR.read_text()
    marker = "\n## Acceptance criteria and scope\n"
    assert marker in text, "missing section: Acceptance criteria and scope"
    return visible_lines(text.split(marker, 1)[1].split("\n## ", 1)[0])


def template_block() -> str:
    text = USER_STORY_SKILL.read_text()
    start = text.index("```markdown\n") + len("```markdown\n")
    return text[start : text.index("\n```", start)]


def template_section(heading: str) -> list[str]:
    """The visible lines under one bold heading of the template, up to the next horizontal rule."""
    lines = visible_lines(template_block())
    assert lines.count(heading) == 1, f"expected exactly one template heading {heading}"
    body = lines[lines.index(heading) + 1 :]
    return body[: body.index("---")] if "---" in body else body


def rules_prose() -> list[str]:
    text = USER_STORY_SKILL.read_text()
    return visible_lines(text[: text.index("## Template (the description)")])


@pytest.mark.parametrize("pinned", RULE_LINES)
def test_scope_section_carries_each_lean_rule_line(pinned: str) -> None:
    assert scope_section().count(pinned) == 1


@pytest.mark.parametrize("heading,pinned", TEMPLATE_CASES)
def test_template_carries_each_lean_line_under_its_heading(heading: str, pinned: str) -> None:
    assert template_section(heading).count(pinned) == 1


@pytest.mark.parametrize("pinned", SKILL_RULE_LINES)
def test_user_story_rules_prose_points_at_the_lean_section(pinned: str) -> None:
    assert rules_prose().count(pinned) == 1


def test_description_lists_the_verification_section() -> None:
    front_matter = USER_STORY_SKILL.read_text().split("\n---\n", 1)[0]
    assert "Additional Context / Verification / Definition of Ready" in " ".join(front_matter.split())


@pytest.mark.parametrize("removed", REMOVED_TEMPLATE_LINES)
def test_template_drops_the_vague_placeholders(removed: str) -> None:
    assert removed not in USER_STORY_SKILL.read_text().splitlines()
