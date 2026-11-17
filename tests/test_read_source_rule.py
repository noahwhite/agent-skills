"""SKL-232: the read-before-asserting rule has one home in shared/engineering-practice.md."""

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
SKILLS = ROOT / "skills"
HOME = SHARED / "engineering-practice.md"
TITLE = "Read the source before asserting"
ANCHOR = "#read-the-source-before-asserting"
PREVIOUS = "Do not hide failures"
DIAGNOSE_ANCHOR = "#diagnose-before-you-touch-code"
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
HEADING_LINE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t#]*$")

# Every K1-K3 obligation, each by a sentence or clause; each must sit in the section and nowhere else.
DISTINCTIVE = (
    "Before theorizing, asserting, acting, filing, or writing a fact into code, a comment, a commit message, or a handback",
    "read the authoritative source for that kind of fact",
    "Quote the real error instead of paraphrasing it, and prove the before-state before claiming a change fixed it.",
    "Check every fact, capability, and \"because X\" justification before stating it.",
    "A clearly labelled hypothesis may be stated; check its factual premises before any action relies on it.",
    "say you do not know, or name what you could not check",
    "Carry that unverified label into the PR description or handback.",
    "Pick the option that is correct and robust, not the one with least effort or cost.",
    "\"Follow-up\", \"good enough\", \"probably fine\", \"out of scope\", and \"low value\" are not reasons to skip work",
    "Work that cannot be completed is reported as incomplete with its blocker, never claimed done.",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def norm(text: str) -> str:
    """Whitespace collapsed and curly quotes straightened, so a reflow is not a content change."""
    return " ".join(text.translate(str.maketrans("“”‘’", "\"\"''")).split())


def unfenced_lines(text: str, where: str) -> list[str]:
    """The lines outside ``` and ~~~ fences, fenced lines blanked; an unclosed fence fails."""
    out, fence = [], None
    for line in text.splitlines():
        m = FENCE_OPEN.match(line)
        if fence is None and m:
            fence = m.group(1)
            out.append("")
        elif fence is not None:
            if re.match(r"^ {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*$", line):
                fence = None
            out.append("")
        else:
            out.append(line)
    assert fence is None, f"unclosed code fence in {where}"
    return out


def headings(text: str, where: str) -> list[tuple[int, str, int]]:
    """(level, normalized title, line index) of every heading outside a fence."""
    out = []
    for i, line in enumerate(unfenced_lines(text, where)):
        m = HEADING_LINE.match(line)
        if m:
            out.append((len(m.group(1)), norm(m.group(2)).casefold(), i))
    return out


def slugs(text: str, where: str) -> list[str]:
    """GitHub-style anchors of the headings outside fences, one per heading."""
    return ["#" + re.sub(r"[^\w\- ]", "", title).replace(" ", "-") for _, title, _ in headings(text, where)]


def section(text: str, title: str, where: str) -> str:
    """The body of the one level-2 section named title, outside fences."""
    lines = unfenced_lines(text, where)
    h2 = [(t, i) for level, t, i in headings(text, where) if level == 2]
    hits = [k for k, (t, _) in enumerate(h2) if t == title.casefold()]
    assert len(hits) == 1, f"expected one '## {title}' in {where}, got {len(hits)}"
    start = h2[hits[0]][1] + 1
    end = h2[hits[0] + 1][1] if hits[0] + 1 < len(h2) else len(lines)
    return "\n".join(lines[start:end])


def payload_bullet(text: str) -> str | None:
    items = re.split(r"\n(?=- )", section(text, "Test-driven development", HOME.name))
    hits = [item for item in items if "Never guess an external API's payload shape" in item]
    return hits[0] if len(hits) == 1 else None


def vendored_copies() -> dict[Path, str]:
    """The engineering-practice copies scripts/vendor_shared.py would write, with their content."""
    spec = importlib.util.spec_from_file_location("vendor_shared", ROOT / "scripts" / "vendor_shared.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {p: body for p, body in module.expected().items() if p.name == HOME.name}


def test_the_heading_occurs_exactly_once_across_shared() -> None:
    target = norm(TITLE).casefold()
    counts = {
        str(p.relative_to(SHARED)): sum(t == target for _, t, _ in headings(read(p), p.name))
        for p in sorted(SHARED.rglob("*.md"))
    }
    assert sum(counts.values()) == 1 and counts.get(HOME.name) == 1, counts


def test_the_section_follows_do_not_hide_failures() -> None:
    h2 = [t for level, t, _ in headings(read(HOME), HOME.name) if level == 2]
    k = h2.index(TITLE.casefold())
    assert k > 0 and h2[k - 1] == PREVIOUS.casefold(), h2


def test_the_payload_shape_bullet_links_to_the_anchor() -> None:
    bullet = payload_bullet(read(HOME))
    assert bullet is not None, "expected one payload-shape bullet under Test-driven development"
    assert f"[{TITLE}]({ANCHOR})" in bullet


def test_the_section_cross_references_diagnosis_and_the_target_resolves() -> None:
    home = read(HOME)
    assert f"]({DIAGNOSE_ANCHOR})" in section(home, TITLE, HOME.name)
    assert DIAGNOSE_ANCHOR in slugs(home, HOME.name)


def test_the_distinctive_sentences_live_only_in_the_section() -> None:
    home = read(HOME)
    body = norm(section(home, TITLE, HOME.name))
    copies = set(vendored_copies())
    others = sorted(
        p for p in (*SHARED.rglob("*.md"), *SKILLS.rglob("*.md")) if p != HOME and p not in copies
    )
    assert others, "no other shared or skill Markdown found"
    texts = {p: norm(read(p)) for p in others}
    for sentence in map(norm, DISTINCTIVE):
        assert body.count(sentence) == 1, f"not once in the section: {sentence}"
        assert norm(home).count(sentence) == 1, f"repeated elsewhere in the home: {sentence}"
        for path, text in texts.items():
            assert sentence not in text, f"restated in {path.relative_to(ROOT)}: {sentence}"


def test_every_generated_copy_exists_is_current_and_resolves_both_anchors() -> None:
    expected = vendored_copies()
    assert expected, "vendor_shared.py vendors engineering-practice.md nowhere"
    assert set(SKILLS.glob(f"*/references/{HOME.name}")) == set(expected)
    for copy, body in sorted(expected.items()):
        where = str(copy.relative_to(ROOT))
        text = read(copy)
        assert text == body, f"stale copy, rerun scripts/vendor_shared.py: {where}"
        anchors = slugs(text, where)
        assert anchors.count(ANCHOR) == 1, f"'{TITLE}' anchor does not resolve once in {where}"
        assert DIAGNOSE_ANCHOR in anchors, f"diagnosis anchor does not resolve in {where}"
        assert f"[{TITLE}]({ANCHOR})" in text, f"no link to the anchor in {where}"
