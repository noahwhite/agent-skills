"""Lean acceptance criteria: the filing rule in shared/linear.md and the user-story template.

Rule lines are pinned inside the "Acceptance criteria and scope" section with their bullet prefix, and
template lines under their own heading inside the fenced template. HTML comments are stripped from the
whole file before any section, fence or heading is located, and fenced examples are stripped from the
shared rules too, so text hidden in a comment or a fence, or moved outside its section, does not satisfy
a pin.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SHARED_LINEAR = ROOT / "shared" / "linear.md"
USER_STORY_SKILL = ROOT / "skills" / "linear-user-story" / "SKILL.md"
NO_VERIFICATION_SKILLS = (
    ROOT / "skills" / "linear-bug" / "SKILL.md",
    ROOT / "skills" / "linear-spike" / "SKILL.md",
)

RULE_LINES = (
    "- An acceptance criterion that needs behavioural evidence has one artifact that proves it and one command, "
    "run or record that produces that artifact, and that artifact must be producible in one pass by one role.",
    "  A user story names that artifact and that command, run or record in its Verification section, never "
    "inside the criterion; a Bug or a Spike, whose template has no Verification section, names both inside the "
    "criterion.",
    "- Write each acceptance criterion as one rule with one observable outcome: one sentence that states the state "
    "or behaviour reached, never how to reach it.",
    "  Use at most 25 words per criterion, counting the proving artifact and command a Bug or a Spike names "
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

VERIFICATION_HEADING = "**🔎 Verification**"
PROOF_LINE = (
    "* [The one artifact that proves each criterion that needs behavioural evidence, and the single run or "
    "record that produces it]"
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
    (VERIFICATION_HEADING, (PROOF_LINE, "* Evidence follows the Definition of Done")),
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


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def scope_section(text: str) -> list[str]:
    """Visible lines of the shared section, with HTML comments and fenced examples removed first."""
    visible = re.sub(r"(```|~~~).*?\1", "", strip_comments(text), flags=re.DOTALL)
    marker = "\n## Acceptance criteria and scope\n"
    assert marker in visible, "missing section: Acceptance criteria and scope"
    return visible.split(marker, 1)[1].split("\n## ", 1)[0].splitlines()


def template_block(text: str) -> str:
    """The fenced template of a filing skill, located after HTML comments are removed."""
    visible = strip_comments(text)
    start = visible.index("```markdown\n") + len("```markdown\n")
    return visible[start : visible.index("\n```", start)]


def template_section(text: str, heading: str) -> list[str]:
    """Lines under one bold heading of the template, up to the next bold heading or horizontal rule."""
    lines = template_block(text).splitlines()
    assert lines.count(heading) == 1, f"expected exactly one template heading {heading}"
    body = []
    for line in lines[lines.index(heading) + 1 :]:
        if line.startswith("**") or line.strip() == "---":
            break
        body.append(line)
    return body


def rules_prose(text: str) -> list[str]:
    visible = strip_comments(text)
    return visible[: visible.index("## Template (the description)")].splitlines()


@pytest.mark.parametrize("pinned", RULE_LINES)
def test_scope_section_carries_each_lean_rule_line(pinned: str) -> None:
    assert scope_section(SHARED_LINEAR.read_text()).count(pinned) == 1


@pytest.mark.parametrize("heading,pinned", TEMPLATE_CASES)
def test_template_carries_each_lean_line_under_its_heading(heading: str, pinned: str) -> None:
    assert template_section(USER_STORY_SKILL.read_text(), heading).count(pinned) == 1


@pytest.mark.parametrize("pinned", SKILL_RULE_LINES)
def test_user_story_rules_prose_points_at_the_lean_section(pinned: str) -> None:
    assert rules_prose(USER_STORY_SKILL.read_text()).count(pinned) == 1


def test_description_lists_the_verification_section() -> None:
    front_matter = USER_STORY_SKILL.read_text().split("\n---\n", 1)[0]
    assert "Additional Context / Verification / Definition of Ready" in " ".join(front_matter.split())


@pytest.mark.parametrize("removed", REMOVED_TEMPLATE_LINES)
def test_template_drops_the_vague_placeholders(removed: str) -> None:
    assert removed not in USER_STORY_SKILL.read_text().splitlines()


@pytest.mark.parametrize("path", NO_VERIFICATION_SKILLS, ids=lambda path: path.parent.name)
def test_bug_and_spike_templates_have_no_verification_section(path: Path) -> None:
    """The shared rule keeps a Bug's or a Spike's proof inside the criterion because of this absence."""
    assert "Verification" not in template_block(path.read_text())


def test_a_commented_out_template_satisfies_no_pin() -> None:
    text = USER_STORY_SKILL.read_text()
    start = text.index("```markdown\n")
    end = text.index("\n```", start) + len("\n```")
    hidden = f"{text[:start]}<!--\n{text[start:end]}\n-->{text[end:]}"
    with pytest.raises(ValueError):
        template_section(hidden, VERIFICATION_HEADING)


def test_a_line_under_an_inserted_heading_is_not_credited_to_the_previous_one() -> None:
    text = USER_STORY_SKILL.read_text()
    assert text.count(PROOF_LINE) == 1
    moved = text.replace(PROOF_LINE, f"**Review Notes**\n{PROOF_LINE}")
    assert PROOF_LINE not in template_section(moved, VERIFICATION_HEADING)


def test_a_fenced_rule_line_is_not_credited_to_the_section() -> None:
    text = SHARED_LINEAR.read_text()
    pinned = RULE_LINES[2]
    assert text.count(pinned + "\n") == 1
    fenced = text.replace(pinned + "\n", f"```\n{pinned}\n```\n")
    assert pinned not in scope_section(fenced)
