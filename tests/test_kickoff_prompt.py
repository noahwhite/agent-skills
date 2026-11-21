"""Contract checks for the story-to-done kickoff prompt asset (SKL-389)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "story-to-done"
ASSET = SKILL_DIR / "assets" / "kickoff-prompt.md"
SKILL = SKILL_DIR / "SKILL.md"

CADENCE_MINUTES = 12

CALLER_LINE = "Start the session in Lite mode where the session offers one, then paste the block below."
POINTER = "assets/kickoff-prompt.md"

# The asset is exactly the caller line, blank space, and one fence with no info string.
ASSET_SHAPE = re.compile(
    rf"\A{re.escape(CALLER_LINE)}\n+```\n(?P<block>.+?)\n```\n*\Z",
    re.DOTALL,
)

CADENCE_SENTENCE = (
    "For this story-to-done run, make one progress check per "
    f"{CADENCE_MINUTES}-minute window instead of several inside it, and batch your waits."
)
DEFAULT_SENTENCE = "This is the default cadence for such a story."
SCOPE_SENTENCE = (
    "An orchestration-heavy story is a run of this skill that spawns a senior engineer and at "
    "least one QA agent; the poll covers routine checks where a role runs in the background, so "
    "handle a handback without waiting for the next routine poll."
)
DEADLINE_SENTENCE = "The deadlines in references/interim-handbacks.md are unchanged."

POINTER_SENTENCE = (
    "For an orchestration-heavy run - one that spawns a senior engineer and at least one QA agent - "
    f"Lite mode plus the {CADENCE_MINUTES}-minute batched-poll cadence is the default, and "
    "`assets/kickoff-prompt.md` holds the caller prompt that starts it."
)

def asset_block() -> str:
    match = ASSET_SHAPE.match(ASSET.read_text(encoding="utf-8"))
    assert match, "the asset must be the caller line, blank space, and one bare fenced block"
    block = match.group("block")
    assert "```" not in block, "the paste block must hold no fence of its own"
    return block


def flat(text: str) -> str:
    return " ".join(text.split())


def prose_lines(lines: list[str]) -> set[int]:
    """The indexes of the lines an agent reads as instructions: not in a fence, not in a comment."""
    prose: set[int] = set()
    fenced = False
    commented = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if fenced:
            if stripped.startswith(("```", "~~~")):
                fenced = False
            continue
        if not commented and stripped.startswith(("```", "~~~")):
            fenced = True
            continue
        visible = ""
        rest = line
        while rest:
            if commented:
                end = rest.find("-->")
                if end < 0:
                    rest = ""
                else:
                    rest = rest[end + 3:]
                    commented = False
            else:
                start = rest.find("<!--")
                if start < 0:
                    visible += rest
                    rest = ""
                else:
                    visible += rest[:start]
                    rest = rest[start + 4:]
                    commented = True
        if visible.strip():
            prose.add(index)
    return prose


def step_sections(text: str) -> list[str]:
    headings = list(re.finditer(r"^## .*$", text, re.MULTILINE))
    sections = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        if re.match(r"^## [1-5]\. ", heading.group(0)):
            sections.append(text[heading.end():end])
    return sections


def test_caller_line_is_the_first_line_and_sits_outside_the_block() -> None:
    text = ASSET.read_text(encoding="utf-8")
    assert text.splitlines()[0] == CALLER_LINE
    assert text.count(CALLER_LINE) == 1


def test_the_asset_is_the_caller_line_and_exactly_one_block() -> None:
    text = ASSET.read_text(encoding="utf-8")
    assert asset_block()
    assert len(re.findall(r"^```", text, re.MULTILINE)) == 2, "one opening fence and one closing fence"
    assert text.rstrip().endswith("```"), "the fenced block must close the asset"


def test_the_block_respects_the_line_and_word_ceilings() -> None:
    block = asset_block()
    assert len(block.splitlines()) <= 5
    assert len(block.split()) <= 80


def test_the_block_is_exactly_the_required_instructions_in_order() -> None:
    expected = " ".join((CADENCE_SENTENCE, DEFAULT_SENTENCE, SCOPE_SENTENCE, DEADLINE_SENTENCE))
    assert flat(asset_block()) == flat(expected)


def test_the_skill_points_at_the_asset_and_states_the_default_outside_the_steps() -> None:
    lines = SKILL.read_text(encoding="utf-8").splitlines()
    text = "\n".join(lines)
    prose = prose_lines(lines)
    sections = step_sections(text)
    assert len(sections) == 5, "all five step sections must be recognised before placement is tested"
    pointer_lines = [index for index, line in enumerate(lines) if POINTER in line]
    assert len(pointer_lines) == 1, "the pointer sentence must be stated exactly once"
    assert pointer_lines[0] in prose, "the pointer must be operative prose, not a comment or a fenced example"
    assert all(POINTER not in section for section in sections), (
        "the kickoff pointer must sit outside the step 1 to step 5 sections"
    )
    assert POINTER_SENTENCE in flat(text)
