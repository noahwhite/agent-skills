"""SKL-232: the read-before-asserting rule has one home in shared/engineering-practice.md."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
SKILLS = ROOT / "skills"
HOME = SHARED / "engineering-practice.md"
HEADING = "## Read the source before asserting"
ANCHOR = "#read-the-source-before-asserting"
FENCE = re.compile(r"^```.*?^```[^\n]*$", re.MULTILINE | re.DOTALL)

# One distinctive sentence or clause each from K1, K2 and K3; none may be restated elsewhere.
DISTINCTIVE = (
    "read the authoritative source for that kind of fact",
    "Quote the real error instead of paraphrasing it, and prove the before-state before claiming a change fixed it.",
    "Check every fact, capability, and \"because X\" justification before stating it.",
    "say you do not know, or name what you could not check",
    "Pick the option that is correct and robust, not the one with least effort or cost.",
    "Work that cannot be completed is reported as incomplete with its blocker, never claimed done.",
)


def slugs(text: str) -> set[str]:
    """GitHub-style anchors of the headings outside fenced code blocks."""
    unfenced = FENCE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    out = set()
    for m in re.finditer(r"^#{1,6} (.+)$", unfenced, re.MULTILINE):
        title = re.sub(r"[^\w\- ]", "", m.group(1).strip().lower())
        out.add("#" + title.replace(" ", "-"))
    return out


def payload_bullet(text: str) -> str:
    items = re.split(r"\n(?=- )", text.split("\n## Test-driven development\n", 1)[1].split("\n## ", 1)[0])
    hits = [item for item in items if "Never guess an external API's payload shape" in item]
    assert len(hits) == 1, f"expected one payload-shape bullet under Test-driven development, got {len(hits)}"
    return hits[0]


def test_the_heading_occurs_exactly_once_across_shared() -> None:
    counts = {p.name: p.read_text().splitlines().count(HEADING) for p in sorted(SHARED.glob("*.md"))}
    assert sum(counts.values()) == 1 and counts[HOME.name] == 1, counts


def test_the_payload_shape_bullet_links_to_the_anchor() -> None:
    assert f"]({ANCHOR})" in payload_bullet(HOME.read_text())


def test_the_distinctive_sentences_live_only_in_the_home() -> None:
    home = HOME.read_text()
    others = [p for p in SHARED.glob("*.md") if p != HOME] + sorted(SKILLS.glob("*/SKILL.md"))
    assert others, "no other shared file or SKILL.md found"
    for sentence in DISTINCTIVE:
        assert home.count(sentence) == 1, f"not once in the home: {sentence}"
        for path in others:
            assert sentence not in path.read_text(), f"restated in {path.relative_to(ROOT)}: {sentence}"


def test_the_anchor_resolves_in_every_generated_copy() -> None:
    copies = sorted(SKILLS.glob("*/references/engineering-practice.md"))
    assert copies, "no generated references/engineering-practice.md found"
    for copy in copies:
        text = copy.read_text()
        assert f"]({ANCHOR})" in text, f"no link to the anchor in {copy.relative_to(ROOT)}"
        assert ANCHOR in slugs(text), f"anchor does not resolve in {copy.relative_to(ROOT)}"
