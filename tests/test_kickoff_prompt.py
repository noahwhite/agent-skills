"""Contract checks for the story-to-done kickoff prompt asset (SKL-389)."""

import re
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "story-to-done"
ASSET = SKILL_DIR / "assets" / "kickoff-prompt.md"
SKILL = SKILL_DIR / "SKILL.md"

CADENCE_MINUTES = 12

CALLER_LINE = "Start the session in Lite mode where the session offers one, then paste the block below."
POINTER = "assets/kickoff-prompt.md"

# The asset is exactly the caller line, blank space, and one fenced block: a CommonMark fence
# (three or more backticks or tildes) with an optional info string, closed by the same fence.
ASSET_SHAPE = re.compile(
    rf"\A{re.escape(CALLER_LINE)}\n+(?P<fence>(?P<marker>`|~)\2{{2,}})[^\n]*\n"
    r"(?P<block>.+?)\n(?P=fence)\n*\Z",
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
# What a CommonMark reader sees for the sentence: inline code loses its backticks.
POINTER_PROSE = " ".join(POINTER_SENTENCE.replace("`", "").split())


def flat(text: str) -> str:
    return " ".join(text.split())


def shape_match(text: str) -> re.Match[str] | None:
    return ASSET_SHAPE.match(text)


def asset_block() -> str:
    match = shape_match(ASSET.read_text(encoding="utf-8"))
    assert match, "the asset must be the caller line, blank space, and one fenced block"
    block = match.group("block")
    assert match.group("fence") not in block, "the paste block must hold no fence of its own"
    return block


MARKDOWN = MarkdownIt("commonmark")
STEP_HEADING = re.compile(r"^[1-5]\. ")


def rendered_paragraphs(text: str) -> list[tuple[int, str]]:
    """Each paragraph as a CommonMark reader sees it, with its starting line number.

    Only text and inline-code children count: an HTML comment or a link title is not
    something a reader sees, so a sentence hidden there is not carried prose.
    """
    tokens = MARKDOWN.parse(text)
    paragraphs: list[tuple[int, str]] = []
    for index, token in enumerate(tokens):
        if token.type == "inline" and tokens[index - 1].type == "paragraph_open":
            visible = "".join(
                child.content
                for child in token.children or []
                if child.type in {"text", "code_inline"}
            )
            paragraphs.append((token.map[0] if token.map else -1, visible))
    return paragraphs


def placement_problems(text: str) -> list[str]:
    """Reasons SKILL.md breaks AC2's placement rule, judged on the rendered CommonMark text.

    The pointer must be exactly one paragraph of visible prose, the asset path must appear
    once in that prose, and the sentence must sit outside the step 1 to step 5 sections. A
    sentence the reader only sees as code, a comment or a link title counts as absent.
    """
    tokens = MARKDOWN.parse(text)
    paragraphs = rendered_paragraphs(text)
    pointer_lines = [line for line, visible in paragraphs if POINTER_PROSE in flat(visible)]
    path_count = sum(visible.count(POINTER) for _, visible in paragraphs)
    step_ranges: list[tuple[int, int]] = []
    pending_step: int | None = None
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h2" and token.level == 0:
            if pending_step is not None:
                step_ranges.append((pending_step, token.map[0]))
                pending_step = None
            content = tokens[index + 1].content if tokens[index + 1].type == "inline" else ""
            if STEP_HEADING.match(content):
                pending_step = token.map[0]
    if pending_step is not None:
        step_ranges.append((pending_step, len(text.splitlines())))
    problems: list[str] = []
    if len(pointer_lines) != 1:
        problems.append(
            "the kickoff pointer must be exactly one paragraph of visible prose "
            f"(found {len(pointer_lines)} paragraphs carrying it)"
        )
    if path_count != 1:
        problems.append(f"the asset path must appear once in visible prose (found {path_count})")
    for line in pointer_lines:
        if any(start <= line < end for start, end in step_ranges):
            problems.append(
                "the kickoff pointer must sit outside the step 1 to step 5 sections "
                f"(line {line + 1})"
            )
    return problems


def test_caller_line_is_the_first_line_and_sits_outside_the_block() -> None:
    text = ASSET.read_text(encoding="utf-8")
    assert text.splitlines()[0] == CALLER_LINE
    assert text.count(CALLER_LINE) == 1


def test_the_asset_is_the_caller_line_and_exactly_one_block() -> None:
    match = shape_match(ASSET.read_text(encoding="utf-8"))
    assert match, "the asset must be the caller line, blank space, and one fenced block"
    text = ASSET.read_text(encoding="utf-8")
    assert len(re.findall(r"^(?:`{3,}|~{3,})", text, re.MULTILINE)) == 2, (
        "one opening fence and one closing fence"
    )
    assert text.rstrip().endswith(match.group("fence")), "the fenced block must close the asset"


def test_the_block_respects_the_line_and_word_ceilings() -> None:
    block = asset_block()
    assert len(block.splitlines()) <= 5
    assert len(block.split()) <= 80


def test_the_block_is_exactly_the_required_instructions_in_order() -> None:
    expected = " ".join((CADENCE_SENTENCE, DEFAULT_SENTENCE, SCOPE_SENTENCE, DEADLINE_SENTENCE))
    assert flat(asset_block()) == flat(expected)


def test_the_cadence_figure_is_pinned_both_ways() -> None:
    assert CADENCE_MINUTES == 12
    assert f"{CADENCE_MINUTES}-minute" in asset_block()
    assert "12-minute" in asset_block()


def test_the_skill_points_at_the_asset_and_states_the_default_outside_the_steps() -> None:
    text = SKILL.read_text(encoding="utf-8")
    tokens = MARKDOWN.parse(text)
    step_headings = [
        index
        for index, token in enumerate(tokens)
        if token.type == "heading_open"
        and token.tag == "h2"
        and token.level == 0
        and tokens[index + 1].type == "inline"
        and STEP_HEADING.match(tokens[index + 1].content)
    ]
    assert len(step_headings) == 5, "all five step sections must be recognised before placement is tested"
    assert placement_problems(text) == []


def test_the_shape_guard_accepts_a_fence_with_an_info_string() -> None:
    text = ASSET.read_text(encoding="utf-8")
    mutated = text.replace("\n```\n", "\n```text\n", 1)
    assert mutated != text
    assert shape_match(mutated), "AC1 allows one fenced block; an info string does not change it"


def test_the_placement_guard_rejects_an_indented_code_block() -> None:
    text = SKILL.read_text(encoding="utf-8")
    mutated = text.replace(POINTER_SENTENCE, f"    {POINTER_SENTENCE}")
    assert placement_problems(mutated), "a four-space-indented pointer renders as code, not prose"


def test_the_placement_guard_rejects_a_pointer_hidden_in_a_mismatched_fence() -> None:
    text = SKILL.read_text(encoding="utf-8")
    mutated = text.replace(POINTER_SENTENCE, "") + f"\n~~~\n{POINTER_SENTENCE}\n```\n"
    assert placement_problems(mutated), "a tilde fence is not closed by a backtick fence"


def test_the_placement_guard_rejects_a_sentence_hidden_in_a_comment() -> None:
    text = SKILL.read_text(encoding="utf-8")
    mutated = text.replace(POINTER_SENTENCE, f"See <!-- {POINTER_SENTENCE} --> the prompt.")
    assert placement_problems(mutated), "an HTML comment is not carried prose"


def test_the_placement_guard_rejects_a_sentence_hidden_in_a_link_title() -> None:
    text = SKILL.read_text(encoding="utf-8")
    mutated = text.replace(POINTER_SENTENCE, f'[Kickoff](https://example.com "{POINTER_SENTENCE}")')
    assert placement_problems(mutated), "a link title is not carried prose"


def test_the_placement_guard_rejects_a_decoded_duplicate_pointer() -> None:
    text = SKILL.read_text(encoding="utf-8")
    mutated = text.replace("## Metrics\n", "Also see assets/kickoff-prompt&#46;md.\n\n## Metrics\n")
    assert mutated != text
    assert placement_problems(mutated), "an entity-decoded second pointer is still visible prose"
