"""Contract checks for the story-to-done kickoff prompt asset (SKL-389)."""

import re
from html.parser import HTMLParser
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
    f"{CADENCE_MINUTES}-minute batched-poll cadence is the default, and "
    f"[{POINTER}]({POINTER}) holds the caller prompt that starts it."
)
# What a CommonMark reader sees for the sentence: a link renders as its text.
POINTER_PROSE = " ".join(
    POINTER_SENTENCE.replace(f"[{POINTER}]({POINTER})", POINTER).split()
)

MARKDOWN = MarkdownIt("commonmark")
STEP_HEADING = re.compile(r"^[1-5]\. ")


def flat(text: str) -> str:
    return " ".join(text.split())


def _feed_children(parser: "_TextExtractor", children) -> None:
    """Feed inline children to a shared extractor, following an image's alt text recursively."""
    for child in children or []:
        if child.type in {"text", "code_inline"}:
            parser.handle_data(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            parser.handle_data(" ")
        elif child.type == "image":
            _feed_children(parser, child.children)
        elif child.type == "html_inline":
            parser.feed(child.content)


def _feed_inline(parser: "_TextExtractor", token) -> None:
    """Feed one inline token to a shared extractor, so hidden state spans the document."""
    _feed_children(parser, token.children)


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


# Raw HTML tags that start a new block (and so separate text); every other tag is inline.
BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "dd", "details", "div", "dl", "dt",
    "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr",
    "li", "main", "nav", "ol", "p", "pre", "section", "summary", "table", "tbody", "td", "tfoot",
    "th", "thead", "tr", "ul",
}
# Void elements never open a subtree, so a hidden attribute on one hides nothing after it.
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source",
    "track", "wbr",
}
# Elements whose contents a reader never sees.
HIDDEN_TAGS = {"script", "style", "template"}


class _TextExtractor(HTMLParser):
    """The text a reader sees in a raw HTML fragment.

    Adjacent inline tags concatenate without a space, block tags separate text, character
    references are decoded, an image's alt text counts, and comments, script, style, template
    contents and any hidden subtree are left out.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.open_tags: list[tuple[str, bool]] = []

    @property
    def hidden(self) -> bool:
        return any(hidden for _, hidden in self.open_tags)

    def _separate(self) -> None:
        if self.parts and not self.parts[-1].endswith(" "):
            self.parts.append(" ")

    def _start(self, tag: str, attrs) -> None:
        hides = tag in HIDDEN_TAGS or any(name == "hidden" for name, _ in attrs)
        if tag not in VOID_TAGS:
            self.open_tags.append((tag, self.hidden or hides))
        if self.hidden or (hides and tag in VOID_TAGS):
            return
        if tag == "img":
            alt = dict(attrs).get("alt")
            if alt:
                self.parts.append(alt)
        elif tag in BLOCK_TAGS:
            self._separate()

    def handle_starttag(self, tag: str, attrs) -> None:
        self._start(tag, attrs)

    def handle_startendtag(self, tag: str, attrs) -> None:
        # HTML ignores a self-closing slash on a non-void element, so it opens a subtree.
        self._start(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.open_tags) - 1, -1, -1):
            if self.open_tags[index][0] == tag:
                del self.open_tags[index:]
                break
        if self.hidden:
            return
        if tag in BLOCK_TAGS:
            self._separate()

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def without_frontmatter(text: str) -> str:
    """The text with any leading YAML frontmatter blanked out, line numbers preserved."""
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        return text
    for index in range(1, len(lines)):
        if lines[index].rstrip() in {"---", "..."}:
            return "\n".join([""] * (index + 1) + lines[index + 1:])
    return text


def scan_document(text: str) -> tuple[list[tuple[int, str, str]], int]:
    """The top-level paragraphs a reader sees and the asset-path count, in one pass.

    A single extractor spans the whole document, so a raw HTML element that opens and closes
    around a paragraph hides that paragraph, and a hidden element hides everything it contains.
    Each paragraph is (source line, visible text, Markdown source); a paragraph inside a hidden
    subtree has empty text, so it never counts as the pointer and never contributes to the path
    count. Occurrences are counted per Markdown block, so text from separate blocks is never
    spliced into one path.
    """
    parser = _TextExtractor()
    paragraphs: list[tuple[int, str, str]] = []
    count = 0
    pending_line: int | None = None
    for token in MARKDOWN.parse(text):
        if token.type == "paragraph_open":
            pending_line = token.map[0] if token.map else -1
        elif token.type == "inline":
            start = len(parser.parts)
            _feed_inline(parser, token)
            visible = "".join(parser.parts[start:])
            count += visible.count(POINTER)
            if pending_line is not None:
                paragraphs.append((pending_line, visible, token.content))
                pending_line = None
        elif token.type in {"fence", "code_block"}:
            if not parser.hidden:
                count += token.content.count(POINTER)
        elif token.type == "html_block":
            start = len(parser.parts)
            parser.feed(token.content)
            count += "".join(parser.parts[start:]).count(POINTER)
    return paragraphs, count


def pointer_link_targets(source: str) -> list[str]:
    """Destinations of Markdown links in a paragraph whose visible label is the asset path."""
    targets: list[str] = []
    for token in MARKDOWN.parse(source):
        if token.type != "inline":
            continue
        children = token.children or []
        for index, child in enumerate(children):
            if child.type != "link_open":
                continue
            label: list[str] = []
            depth = 0
            for inner in children[index + 1:]:
                if inner.type == "link_open":
                    depth += 1
                elif inner.type == "link_close":
                    if depth == 0:
                        break
                    depth -= 1
                elif inner.type in {"text", "code_inline"}:
                    label.append(inner.content)
            if "".join(label) == POINTER:
                targets.append(child.attrGet("href") or "")
    return targets


def placement_problems(text: str) -> list[str]:
    """Reasons SKILL.md breaks AC2's placement rule, judged on what a CommonMark reader sees.

    The pointer must be exactly one paragraph of visible prose, the asset path must be named once
    in visible text, and the sentence must sit outside the step 1 to step 5 sections. YAML
    frontmatter is metadata, not prose, so a sentence only there does not count, and neither does
    one inside a hidden HTML subtree. A link labelled with the asset path must also target it.
    """
    text = without_frontmatter(text)
    paragraphs, path_count = scan_document(text)
    pointer_lines = [line for line, visible, _ in paragraphs if POINTER_PROSE in flat(visible)]
    exact = [(line, source) for line, visible, source in paragraphs if flat(visible) == POINTER_PROSE]
    problems: list[str] = []
    if len(pointer_lines) != 1:
        problems.append(
            "the kickoff pointer must be exactly one paragraph of visible prose "
            f"(found {len(pointer_lines)} paragraphs carrying it)"
        )
    elif len(exact) != 1:
        problems.append("the pointer paragraph must be exactly the one sentence")
    elif pointer_link_targets(exact[0][1]) != [POINTER]:
        problems.append("the pointer link must target the asset path itself")
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


def test_the_placement_guard_ignores_a_pointer_in_a_raw_html_href() -> None:
    text = skill_document(f'{POINTER_SENTENCE}\n\nSee <a href="{POINTER}">the prompt</a>.')
    assert placement_problems(text) == []


def test_the_placement_guard_decodes_a_pointer_in_visible_html() -> None:
    duplicated = f"{POINTER_SENTENCE}\n\n<div>Also see assets/kickoff-prompt&#46;md.</div>"
    problems = placement_problems(skill_document(duplicated))
    assert any("must appear once in visible text (found 2" in problem for problem in problems)


def test_the_placement_guard_counts_a_pointer_split_across_inline_html() -> None:
    duplicated = f"{POINTER_SENTENCE}\n\n<div><span>assets/kickoff-prompt</span>.md</div>"
    problems = placement_problems(skill_document(duplicated))
    assert any("must appear once in visible text (found 2" in problem for problem in problems)


def test_the_placement_guard_ignores_a_pointer_inside_script_or_style() -> None:
    for tag in ("script", "style"):
        text = skill_document(f"{POINTER_SENTENCE}\n\n<{tag}>{POINTER}</{tag}>")
        assert placement_problems(text) == []


def test_the_placement_guard_rejects_a_contradictory_pointer_paragraph() -> None:
    pointer = f"{POINTER_SENTENCE} Ignore the default and poll continuously."
    problems = placement_problems(skill_document(pointer))
    assert any("must be exactly the one sentence" in problem for problem in problems)


def test_the_placement_guard_rejects_a_pointer_only_in_frontmatter() -> None:
    text = (
        "---\n"
        "name: fixture\n"
        "description: >-\n"
        f"  {POINTER_SENTENCE}\n"
        "---\n"
        "\n"
        "# Title\n"
        "\n"
        "## Kickoff prompt\n"
        "\n"
        "No pointer in the body.\n"
    )
    problems = placement_problems(text)
    assert any("exactly one paragraph of visible prose (found 0" in problem for problem in problems), problems
    assert any("must appear once in visible text (found 0" in problem for problem in problems), problems


def test_the_placement_guard_reads_an_indented_marker_in_frontmatter_as_metadata() -> None:
    frontmatter = (
        "---\n"
        "name: fixture\n"
        "description: >-\n"
        "  First line.\n"
        "  ---\n"
        f"  Also see {POINTER} in metadata.\n"
        "---\n"
        "\n"
    )
    assert placement_problems(frontmatter + skill_document()) == []


def test_the_placement_guard_counts_a_pointer_in_a_raw_html_image_alt() -> None:
    duplicated = f'{POINTER_SENTENCE}\n\nSee <img alt="{POINTER}">.'
    problems = placement_problems(skill_document(duplicated))
    assert any("must appear once in visible text (found 2" in problem for problem in problems)


def test_the_placement_guard_ignores_a_pointer_inside_a_template() -> None:
    text = skill_document(f"{POINTER_SENTENCE}\n\n<template>{POINTER}</template>")
    assert placement_problems(text) == []


def test_the_placement_guard_ignores_a_pointer_in_a_hidden_subtree() -> None:
    text = skill_document(f"{POINTER_SENTENCE}\n\n<div hidden>{POINTER}</div>")
    assert placement_problems(text) == []


def test_the_placement_guard_does_not_join_a_path_across_a_details_boundary() -> None:
    split = "assets/kickoff-prompt"
    text = skill_document(f"{POINTER_SENTENCE}\n\n<details>{split}</details>.md")
    assert placement_problems(text) == []


def test_the_placement_guard_rejects_a_pointer_wrapped_in_a_hidden_block() -> None:
    hidden = f"<div hidden>\n\n{POINTER_SENTENCE}\n\n</div>"
    problems = placement_problems(skill_document(hidden))
    assert any("exactly one paragraph of visible prose (found 0" in problem for problem in problems), problems


def test_the_placement_guard_ignores_a_hidden_image_alt() -> None:
    pointer = f'{POINTER_SENTENCE} <img hidden alt="{POINTER}">'
    assert placement_problems(skill_document(pointer)) == []


def test_the_placement_guard_does_not_join_a_path_across_paragraphs() -> None:
    split = "assets/kickoff-prompt"
    text = skill_document(f"{POINTER_SENTENCE}\n\n{split}\n\n.md")
    assert placement_problems(text) == []


def test_the_placement_guard_keeps_an_outer_hidden_block_hidden_after_an_inner_one_closes() -> None:
    hidden = (
        f"<div hidden>\n\n<div>\n\n{POINTER_SENTENCE}\n\n</div>\n\n"
        f"{POINTER_SENTENCE}\n\n</div>"
    )
    problems = placement_problems(skill_document(hidden))
    assert any("exactly one paragraph of visible prose (found 0" in problem for problem in problems), problems


def test_the_placement_guard_counts_a_pointer_in_an_image_alt_html_image() -> None:
    duplicated = f'{POINTER_SENTENCE}\n\n![outer <img alt="{POINTER}">](outer.png)'
    problems = placement_problems(skill_document(duplicated))
    assert any("must appear once in visible text (found 2" in problem for problem in problems), problems


def test_the_placement_guard_counts_a_pointer_in_a_nested_image_alt() -> None:
    duplicated = f"{POINTER_SENTENCE}\n\n![outer ![inner {POINTER}](inner.png)](outer.png)"
    problems = placement_problems(skill_document(duplicated))
    assert any("must appear once in visible text (found 2" in problem for problem in problems), problems


def test_the_placement_guard_rejects_a_pointer_linked_to_another_file() -> None:
    pointer = POINTER_SENTENCE.replace(f"]({POINTER})", "](references/interim-handbacks.md)")
    assert pointer != POINTER_SENTENCE
    problems = placement_problems(skill_document(pointer))
    assert any("must target the asset path itself" in problem for problem in problems), problems
