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

FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.MULTILINE | re.DOTALL)


def step_sections(text: str) -> list[str]:
    headings = list(re.finditer(r"^## .*$", text, re.MULTILINE))
    sections = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        if re.match(r"^## [1-5]\. ", heading.group(0)):
            sections.append(text[heading.end():end])
    return sections


def test_caller_line_is_the_first_line_and_sits_outside_the_block() -> None:
    text = ASSET.read_text()
    assert text.splitlines()[0] == CALLER_LINE
    assert text.count(CALLER_LINE) == 1


def test_the_asset_holds_exactly_one_fenced_block_at_the_end() -> None:
    text = ASSET.read_text()
    blocks = FENCE.findall(text)
    assert len(blocks) == 1, "the asset must hold exactly one fenced paste block"
    assert text.rstrip().endswith("```"), "the fenced block must close the asset"
    assert FENCE.search(text).start() > text.index(CALLER_LINE), "the caller line precedes the block"


def test_the_block_respects_the_line_and_word_ceilings() -> None:
    block = FENCE.findall(ASSET.read_text())[0]
    lines = block.splitlines()
    assert len([line for line in lines if line.strip()]) <= 5
    assert len(lines) <= 5
    assert len(block.split()) <= 80


def test_the_block_carries_the_required_literals_and_instructions() -> None:
    asset = ASSET.read_text()
    block = FENCE.findall(asset)[0]
    assert "Lite mode" in asset
    assert f"{CADENCE_MINUTES}-minute" in block
    assert str(CADENCE_MINUTES) == "12"
    assert "This is the default cadence for such a story." in block
    assert "one progress check per 12-minute window" in block
    assert "instead of several inside it" in block
    assert "batch your waits" in block
    assert "orchestration-heavy" in block
    assert "senior engineer" in block
    assert "QA agent" in block
    assert "where a role runs in the background" in block
    assert "references/interim-handbacks.md" in block
    assert "unchanged" in block


def test_the_skill_points_at_the_asset_and_states_the_default_outside_the_steps() -> None:
    text = SKILL.read_text()
    assert text.count(POINTER) == 1
    assert any(POINTER in section for section in step_sections(text)) is False, (
        "the kickoff pointer must sit outside the step 1 to step 5 sections"
    )
    pointer_lines = [line for line in text.splitlines() if POINTER in line]
    assert len(pointer_lines) == 1
    pointer = pointer_lines[0]
    assert "Lite mode" in pointer
    assert f"{CADENCE_MINUTES}-minute" in pointer
    assert "batched-poll cadence" in pointer
    assert "default" in pointer
    assert len(re.findall(r"\.(?=\s|$)", pointer)) == 1, "the pointer must be exactly one sentence"
