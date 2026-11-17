"""SKL-232: the read-before-asserting rule has one home in shared/engineering-practice.md.

Markdown is read as CommonMark renders it (markdown-it-py), so code, HTML comments and HTML
blocks hide what they hide on the rendered page, and nothing else does.
"""

import importlib.util
import re
from dataclasses import dataclass, field
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
SKILLS = ROOT / "skills"
HOME = SHARED / "engineering-practice.md"
TITLE = "Read the source before asserting"
ANCHOR = "#read-the-source-before-asserting"
PREVIOUS = "Do not hide failures"
DIAGNOSE_ANCHOR = "#diagnose-before-you-touch-code"
MARKDOWN = MarkdownIt("commonmark")

# The section's rendered bullets, exactly: K1 to K3, nothing hidden, appended or dropped.
BULLETS = (
    "Before theorizing, asserting, acting, filing, or writing a fact into code, a comment, a commit message,"
    " or a handback, read the authoritative source for that kind of fact: the error and logs, live state,"
    " --help, or the registry or provider API.",
    "Quote the real error instead of paraphrasing it, and prove the before-state before claiming a change fixed it.",
    "Check every fact, capability, and \"because X\" justification before stating it.",
    "A clearly labelled hypothesis may be stated; check its factual premises before any action relies on it.",
    "For a bug or failure, Diagnose before you touch code applies as well.",
    "⛔ When a claim cannot be checked, say you do not know, or name what you could not check;"
    " never write a plausible sentence in its place. Carry that unverified label into the PR description or handback.",
    "Pick the option that is correct and robust, not the one with least effort or cost.",
    "⛔ \"Follow-up\", \"good enough\", \"probably fine\", \"out of scope\", and \"low value\" are not reasons to skip"
    " work that the Definition of Done, an acceptance criterion, or a rule calls for. Work that cannot be completed"
    " is reported as incomplete with its blocker, never claimed done.",
)


def norm(text: str) -> str:
    """Whitespace collapsed and curly quotes straightened, so a reflow is not a content change."""
    return " ".join(text.translate(str.maketrans("“”‘’", "\"\"''")).split())


@dataclass
class Section:
    level: int
    title: str
    bullets: list[str] = field(default_factory=list)  # rendered text of each top-level list item
    links: list[list[str]] = field(default_factory=list)  # 'text -> href' links of each top-level list item


@dataclass
class Doc:
    sections: list[Section]
    text: str  # all rendered prose, normalized

    def h2(self, title: str) -> list[Section]:
        return [s for s in self.sections if s.level == 2 and s.title.casefold() == title.casefold()]

    def slugs(self) -> list[str]:
        """GitHub-style anchors, with its -1, -2 suffixes for repeated headings."""
        seen: dict[str, int] = {}
        out = []
        for s in self.sections:
            base = "#" + re.sub(r"[^\w\- ]", "", s.title.lower()).replace(" ", "-")
            n = seen.get(base, 0)
            seen[base] = n + 1
            out.append(base if n == 0 else f"{base}-{n}")
        return out


def rendered(inline) -> tuple[str, list[str]]:
    """The visible text of an inline token (raw HTML dropped) and its links as 'text -> href'."""
    parts, links, link = [], [], None
    for child in inline.children or []:
        if child.type in ("text", "code_inline"):
            parts.append(child.content)
            if link is not None:
                link[0].append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
        elif child.type == "link_open":
            link = ([], child.attrGet("href"))
        elif child.type == "link_close" and link is not None:
            links.append(f"{norm(''.join(link[0]))} -> {link[1]}")
            link = None
    return norm("".join(parts)), links


def parse(path: Path) -> Doc:
    tokens = MARKDOWN.parse(path.read_text(encoding="utf-8"))
    sections = [Section(0, "")]
    prose, depth, item = [], 0, None
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open":
            sections.append(Section(int(tok.tag[1]), rendered(tokens[i + 1])[0]))
        elif tok.type in ("bullet_list_open", "ordered_list_open"):
            depth += 1
        elif tok.type in ("bullet_list_close", "ordered_list_close"):
            depth -= 1
        elif tok.type == "list_item_open" and depth == 1:
            item = ([], [])
        elif tok.type == "list_item_close" and depth == 1:
            sections[-1].bullets.append(norm(" ".join(item[0])))
            sections[-1].links.append(item[1])
            item = None
        elif tok.type == "inline":
            text, links = rendered(tok)
            prose.append(text)
            if item is not None:
                item[0].append(text)
                item[1].extend(links)
    return Doc(sections, norm(" ".join(prose)))


def the_section(doc: Doc, where: str) -> Section:
    hits = doc.h2(TITLE)
    assert len(hits) == 1, f"expected one '## {TITLE}' in {where}, got {len(hits)}"
    return hits[0]


def vendored_copies() -> dict[Path, str]:
    """The engineering-practice copies scripts/vendor_shared.py would write, with their content."""
    spec = importlib.util.spec_from_file_location("vendor_shared", ROOT / "scripts" / "vendor_shared.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {p: body for p, body in module.expected().items() if p.name == HOME.name}


def test_the_heading_occurs_exactly_once_across_shared() -> None:
    target = norm(TITLE).casefold()
    counts = {
        str(p.relative_to(SHARED)): sum(s.title.casefold() == target for s in parse(p).sections)
        for p in sorted(SHARED.rglob("*.md"))
    }
    assert sum(counts.values()) == 1 and counts.get(HOME.name) == 1, counts


def test_the_section_follows_do_not_hide_failures() -> None:
    h2 = [s.title.casefold() for s in parse(HOME).sections if s.level == 2]
    k = h2.index(TITLE.casefold())
    assert k > 0 and h2[k - 1] == PREVIOUS.casefold(), h2


def test_the_section_renders_exactly_the_rule() -> None:
    section = the_section(parse(HOME), HOME.name)
    assert section.bullets == [norm(b) for b in BULLETS]


def test_the_payload_shape_bullet_links_to_the_anchor() -> None:
    (tdd,) = parse(HOME).h2("Test-driven development")
    hits = [k for k, b in enumerate(tdd.bullets) if "Never guess an external API's payload shape" in b]
    assert len(hits) == 1, f"expected one payload-shape bullet under Test-driven development, got {len(hits)}"
    assert f"{TITLE} -> {ANCHOR}" in tdd.links[hits[0]], tdd.links[hits[0]]


def test_the_section_cross_references_diagnosis_and_the_target_resolves() -> None:
    doc = parse(HOME)
    links = [link for item in the_section(doc, HOME.name).links for link in item]
    assert f"Diagnose before you touch code -> {DIAGNOSE_ANCHOR}" in links, links
    assert DIAGNOSE_ANCHOR in doc.slugs()


def test_no_sentence_of_the_rule_is_restated_elsewhere() -> None:
    sentences = [s for b in BULLETS for s in re.split(r"(?<=[.;:])\s+", norm(b)) if len(s.split()) >= 6]
    home = parse(HOME).text
    copies = set(vendored_copies())
    others = sorted(
        p for p in (*SHARED.rglob("*.md"), *SKILLS.rglob("*.md")) if p != HOME and p not in copies
    )
    assert others, "no other shared or skill Markdown found"
    texts = {p: parse(p).text for p in others}
    for sentence in sentences:
        assert home.count(sentence) == 1, f"not once in the home: {sentence}"
        for path, text in texts.items():
            assert sentence not in text, f"restated in {path.relative_to(ROOT)}: {sentence}"


def test_every_generated_copy_exists_is_current_and_resolves_both_anchors() -> None:
    expected = vendored_copies()
    assert expected, "vendor_shared.py vendors engineering-practice.md nowhere"
    assert set(SKILLS.glob(f"*/references/{HOME.name}")) == set(expected)
    for copy, body in sorted(expected.items()):
        where = str(copy.relative_to(ROOT))
        assert copy.read_text(encoding="utf-8") == body, f"stale copy, rerun scripts/vendor_shared.py: {where}"
        doc = parse(copy)
        assert the_section(doc, where).bullets == [norm(b) for b in BULLETS], where
        anchors = doc.slugs()
        assert anchors.count(ANCHOR) == 1, f"'{TITLE}' anchor does not resolve once in {where}"
        assert DIAGNOSE_ANCHOR in anchors, f"diagnosis anchor does not resolve in {where}"
