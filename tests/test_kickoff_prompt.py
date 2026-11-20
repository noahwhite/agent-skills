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

COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def asset_block() -> str:
    match = ASSET_SHAPE.match(ASSET.read_text(encoding="utf-8"))
    assert match, "the asset must be the caller line, blank space, and one bare fenced block"
    block = match.group("block")
    assert "```" not in block, "the paste block must hold no fence of its own"
    return block


def visible(text: str) -> str:
    return COMMENT.sub("", text)


def flat(text: str) -> str:
    return " ".join(text.split())


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


def test_the_block_carries_the_required_clauses_affirmatively() -> None:
    block = flat(asset_block())
    assert CADENCE_SENTENCE in block
    assert DEFAULT_SENTENCE in block
    assert SCOPE_SENTENCE in block
    assert DEADLINE_SENTENCE in block


def test_the_skill_points_at_the_asset_and_states_the_default_outside_the_steps() -> None:
    raw = SKILL.read_text(encoding="utf-8")
    text = visible(raw)
    sections = step_sections(text)
    assert len(sections) == 5, "all five step sections must be recognised before placement is tested"
    assert raw.count(POINTER) == 1, "the pointer must not be hidden in a comment or repeated"
    assert all(POINTER not in section for section in sections), (
        "the kickoff pointer must sit outside the step 1 to step 5 sections"
    )
    assert POINTER_SENTENCE in flat(text)
