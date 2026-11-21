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

RUN_SENTENCE = "Run story-to-done for <story-id>."
CADENCE_SENTENCE = (
    f"Batch your waits; make one progress check per {CADENCE_MINUTES}-minute window, not several."
)
DEFAULT_SENTENCE = "This is the default cadence for such a story."
# One shared phrase so the asset's definition and the skill's default statement cannot drift apart.
ROLE_REQUIREMENT = "a senior engineer and at least one QA agent"
SCOPE_SENTENCE = (
    f"An orchestration-heavy story is a run of this skill that spawns {ROLE_REQUIREMENT}; the poll "
    "covers routine checks where a role runs in the background, so handle a handback without "
    "waiting for the next routine poll."
)
DEADLINE_SENTENCE = "The wait bounds and deadlines in references/interim-handbacks.md are unchanged."
EXPECTED_BLOCK = "\n".join(
    (RUN_SENTENCE, CADENCE_SENTENCE, DEFAULT_SENTENCE, SCOPE_SENTENCE, DEADLINE_SENTENCE)
)

POINTER_SENTENCE = (
    f"For an orchestration-heavy run - one that spawns {ROLE_REQUIREMENT} - Lite mode plus the "
    f"{CADENCE_MINUTES}-minute batched-poll cadence is the default, and `assets/kickoff-prompt.md` "
    "holds the caller prompt that starts it."
)
# What a CommonMark reader sees for the sentence: inline code loses its backticks.
POINTER_PROSE = " ".join(POINTER_SENTENCE.replace("`", "").split())

MARKDOWN = MarkdownIt("commonmark")
STEP_HEADING = re.compile(r"^[1-5]\. ")


def flat(text: str) -> str:
    return " ".join(text.split())


def visible_text(token) -> str:
    """The text of an inline token as a reader sees it.

    Text and inline code count; a soft or hard line break becomes one space, so a rewrapped
    sentence still reads as one sentence. An HTML comment or a link attribute is invisible.
    """
    parts = []
    for child in token.children or []:
        if child.type in {"text", "code_inline"}:
            parts.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            parts.append(" ")
    return "".join(parts)


def rendered_inlines(text: str) -> list[tuple[int, str]]:
    """Every inline run a CommonMark reader sees, with its starting source line."""
    return [
        (token.map[0] if token.map else -1, visible_text(token))
        for token in MARKDOWN.parse(text)
        if token.type == "inline"
    ]


def asset_document(
    block: str = EXPECTED_BLOCK,
    *,
    info: str = "",
    opener: str = "```",
    closer: str | None = None,
) -> str:
    """A minimal kickoff asset fixture; independent of the shipped file."""
    closing = opener if closer is None else closer
    return f"{CALLER_LINE}\n\n{opener}{info}\n{block}\n{closing}\n"


def shape_problems(text: str) -> list[str]:
    """Reasons an asset text is not one caller paragraph followed by one closed fenced block.

    The block is judged by CommonMark's own tokenizer, so an info string, an indented fence
    and a longer closing fence are all accepted, while an opener CommonMark reads as prose or
    a fence that is never closed is rejected.
    """
    tokens = MARKDOWN.parse(text)
    if [token.type for token in tokens] != ["paragraph_open", "inline", "paragraph_close", "fence"]:
        return ["the asset must be one caller paragraph followed by exactly one fenced block"]
    problems = []
    if flat(tokens[1].content) != CALLER_LINE:
        problems.append("the caller line must be the asset's only paragraph")
    fence = tokens[3]
    closed = bool(fence.map) and fence.map[1] - fence.map[0] >= 2
    closing = text.splitlines()[fence.map[1] - 1] if closed else ""
    if not closed or not re.fullmatch(
        rf" {{0,3}}{re.escape(fence.markup[0])}{{{len(fence.markup)},}}[ \t]*", closing
    ):
        problems.append("the fenced block must be closed by a fence at least as long as its opener")
    return problems


def asset_block(text: str | None = None) -> str:
    """The pasted block exactly as fenced, trailing blank lines included."""
    text = ASSET.read_text(encoding="utf-8") if text is None else text
    assert shape_problems(text) == [], shape_problems(text)
    return MARKDOWN.parse(text)[3].content


def step_ranges(text: str) -> list[tuple[int, int]]:
    """Source line spans of the step 1 to step 5 sections."""
    tokens = MARKDOWN.parse(text)
    ranges: list[tuple[int, int]] = []
    pending: int | None = None
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h2" and token.level == 0:
            if pending is not None:
                ranges.append((pending, token.map[0]))
                pending = None
            content = tokens[index + 1].content if tokens[index + 1].type == "inline" else ""
            if STEP_HEADING.match(content):
                pending = token.map[0]
    if pending is not None:
        ranges.append((pending, len(text.splitlines())))
    return ranges


def html_text(content: str) -> str:
    """The text nodes of a raw HTML fragment: comments and tags both removed."""
    without_comments = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    return re.sub(r"<[^>]*>", "", without_comments)


def visible_mentions(text: str) -> int:
    """Occurrences of the asset path in anything a reader sees.

    Prose, code blocks, rendered image alt text and non-comment raw HTML count; HTML comments,
    link destinations and link titles do not.
    """
    count = 0
    for token in MARKDOWN.parse(text):
        if token.type == "inline":
            count += visible_text(token).count(POINTER)
            for child in token.children or []:
                if child.type == "image":
                    alt = "".join(
                        part.content
                        for part in (child.children or [])
                        if part.type in {"text", "code_inline"}
                    )
                    count += alt.count(POINTER)
                elif child.type == "html_inline":
                    count += html_text(child.content).count(POINTER)
        elif token.type in {"fence", "code_block"}:
            count += token.content.count(POINTER)
        elif token.type == "html_block":
            count += html_text(token.content).count(POINTER)
    return count


def placement_problems(text: str) -> list[str]:
    """Reasons SKILL.md breaks AC2's placement rule, judged on what a CommonMark reader sees.

    The pointer must be exactly one paragraph of visible prose, the asset path must be named
    once in visible text, and the sentence must sit outside the step 1 to step 5 sections.
    """
    tokens = MARKDOWN.parse(text)
    paragraphs = [
        (token.map[0] if token.map else -1, visible_text(token))
        for index, token in enumerate(tokens)
        if token.type == "inline" and tokens[index - 1].type == "paragraph_open"
    ]
    pointer_lines = [line for line, visible in paragraphs if POINTER_PROSE in flat(visible)]
    path_count = visible_mentions(text)
    problems: list[str] = []
    if len(pointer_lines) != 1:
        problems.append(
            "the kickoff pointer must be exactly one paragraph of visible prose "
            f"(found {len(pointer_lines)} paragraphs carrying it)"
        )
    if path_count != 1:
        problems.append(f"the asset path must appear once in visible text (found {path_count})")
    for line in pointer_lines:
        if any(start <= line < end for start, end in step_ranges(text)):
            problems.append(
                "the kickoff pointer must sit outside the step 1 to step 5 sections "
                f"(line {line + 1})"
            )
    return problems


def skill_document(pointer: str = POINTER_SENTENCE) -> str:
    """A minimal SKILL.md fixture whose five step sections carry no pointer."""
    steps = "\n\n".join(f"## {number}. Step {number}\n\nStep {number} body." for number in range(1, 6))
    return f"# Title\n\n## Kickoff prompt\n\n{pointer}\n\n{steps}\n"


def test_caller_line_is_the_first_line_and_sits_outside_the_block() -> None:
    text = ASSET.read_text(encoding="utf-8")
    assert text.splitlines()[0] == CALLER_LINE
    assert text.count(CALLER_LINE) == 1


def test_the_asset_is_the_caller_line_and_exactly_one_block() -> None:
    assert shape_problems(ASSET.read_text(encoding="utf-8")) == []


def test_the_block_respects_the_line_and_word_ceilings() -> None:
    block = asset_block()
    assert len(block.splitlines()) <= 5
    assert len(block.split()) <= 80


def test_the_block_is_exactly_the_required_instructions_in_order() -> None:
    assert flat(asset_block()) == flat(EXPECTED_BLOCK)


def test_the_cadence_figure_is_pinned_both_ways() -> None:
    assert CADENCE_MINUTES == 12
    assert f"{CADENCE_MINUTES}-minute" in asset_block()
    assert "12-minute" in asset_block()


def test_the_shape_guard_accepts_a_fence_with_an_info_string() -> None:
    assert shape_problems(asset_document(info="text")) == []


def test_the_shape_guard_accepts_a_longer_closing_fence() -> None:
    assert shape_problems(asset_document(closer="````")) == []


def test_the_shape_guard_rejects_an_unclosed_fence() -> None:
    unclosed = f"{CALLER_LINE}\n\n```\n{EXPECTED_BLOCK}\n"
    assert shape_problems(unclosed)


def test_the_shape_guard_rejects_trailing_text_outside_the_block() -> None:
    assert shape_problems(asset_document() + "Trailing prose.\n")


def test_the_shape_guard_rejects_an_opener_commonmark_reads_as_prose() -> None:
    assert shape_problems(asset_document(info="a`b"))


def test_the_shape_guard_rejects_an_opener_at_end_of_file() -> None:
    assert shape_problems(f"{CALLER_LINE}\n\n```\n")


def test_the_shape_guard_rejects_an_indented_closing_fence() -> None:
    assert shape_problems(asset_document(closer="    ```"))


def test_the_ceiling_counts_blank_block_lines() -> None:
    five = asset_document(block="one\ntwo\nthree\nfour\nfive")
    six = asset_document(block="one\ntwo\nthree\nfour\nfive\n")
    assert len(asset_block(five).splitlines()) == 5
    assert len(asset_block(six).splitlines()) == 6


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


def test_the_placement_guard_accepts_a_rewrapped_pointer() -> None:
    wrapped = POINTER_SENTENCE.replace("Lite mode", "\nLite mode")
    assert wrapped != POINTER_SENTENCE
    assert placement_problems(skill_document(wrapped)) == []


def test_the_placement_guard_rejects_a_pointer_inside_a_step_section() -> None:
    text = skill_document()
    heading = "## 2. Step 2\n"
    mutated = text.replace(heading, f"{heading}\n{POINTER_SENTENCE}\n")
    assert mutated != text
    problems = placement_problems(mutated)
    assert any("outside the step 1 to step 5 sections" in problem for problem in problems), problems


def test_the_placement_guard_rejects_an_indented_code_block() -> None:
    problems = placement_problems(skill_document(f"    {POINTER_SENTENCE}"))
    assert any("exactly one paragraph of visible prose (found 0" in problem for problem in problems)


def test_the_placement_guard_rejects_a_pointer_hidden_in_a_mismatched_fence() -> None:
    hidden = f"~~~\n{POINTER_SENTENCE}\n```"
    problems = placement_problems(skill_document(hidden))
    assert any("exactly one paragraph of visible prose (found 0" in problem for problem in problems)


def test_the_placement_guard_rejects_a_sentence_hidden_in_a_comment() -> None:
    problems = placement_problems(skill_document(f"<!-- {POINTER_SENTENCE} -->"))
    assert any("exactly one paragraph of visible prose (found 0" in problem for problem in problems)


def test_the_placement_guard_rejects_a_sentence_hidden_in_a_link_title() -> None:
    hidden = f'[Kickoff](https://example.com "{POINTER_SENTENCE}")'
    problems = placement_problems(skill_document(hidden))
    assert any("exactly one paragraph of visible prose (found 0" in problem for problem in problems)


def test_the_placement_guard_rejects_a_decoded_duplicate_pointer() -> None:
    duplicated = f"{POINTER_SENTENCE}\n\nAlso see assets/kickoff-prompt&#46;md."
    problems = placement_problems(skill_document(duplicated))
    assert any("must appear once in visible text (found 2" in problem for problem in problems)


def test_the_placement_guard_counts_a_pointer_in_a_heading() -> None:
    text = skill_document().replace("## Kickoff prompt", f"## Kickoff prompt and {POINTER}")
    problems = placement_problems(text)
    assert any("must appear once in visible text (found 2" in problem for problem in problems)


def test_the_placement_guard_counts_a_pointer_in_a_fenced_example() -> None:
    duplicated = f"{POINTER_SENTENCE}\n\n```\nAlso see {POINTER}.\n```"
    problems = placement_problems(skill_document(duplicated))
    assert any("must appear once in visible text (found 2" in problem for problem in problems)


def test_the_placement_guard_counts_a_pointer_in_an_image_alt() -> None:
    duplicated = f"{POINTER_SENTENCE}\n\n![{POINTER}](image.png)"
    problems = placement_problems(skill_document(duplicated))
    assert any("must appear once in visible text (found 2" in problem for problem in problems)


def test_the_placement_guard_counts_a_pointer_in_visible_html() -> None:
    duplicated = f"{POINTER_SENTENCE}\n\n<div>Also see {POINTER}.</div>"
    problems = placement_problems(skill_document(duplicated))
    assert any("must appear once in visible text (found 2" in problem for problem in problems)


def test_the_placement_guard_ignores_a_path_in_an_image_link_destination() -> None:
    text = skill_document(f"{POINTER_SENTENCE}\n\n![see [the prompt]({POINTER})](image.png)")
    assert placement_problems(text) == []


def test_the_placement_guard_ignores_a_path_in_a_raw_html_attribute() -> None:
    text = skill_document(f'{POINTER_SENTENCE}\n\nSee <a href="{POINTER}">the prompt</a>.')
    assert placement_problems(text) == []
