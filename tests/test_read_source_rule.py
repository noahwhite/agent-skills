"""SKL-232 K4: the read-before-asserting rule has one home in shared/engineering-practice.md.

These checks catch honest mistakes (a duplicated heading, a restated sentence, a dropped link,
a stale copy); they do not try to defeat deliberate evasion such as hiding text in HTML.
"""

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
SKILLS = ROOT / "skills"
HOME = SHARED / "engineering-practice.md"
HEADING = re.compile(r"^##[ \t]+Read the source before asserting[ \t]*$", re.MULTILINE | re.IGNORECASE)
ANCHOR_LINK = "](#read-the-source-before-asserting)"
PAYLOAD_BULLET = "Never guess an external API's payload shape"

# The section's distinctive sentences (K1 to K3), as they read after whitespace is collapsed.
DISTINCTIVE = (
    "read the authoritative source for that kind of fact: the error and logs, live state, `--help`,"
    " or the registry or provider API.",
    "Quote the real error instead of paraphrasing it, leaving out any secret value it carries,"
    " and prove the before-state before claiming a change fixed it.",
    "Check every fact, capability, and \"because X\" justification before stating it.",
    "A clearly labelled hypothesis may be stated; check its factual premises before any action relies on it.",
    "When a claim cannot be checked, say you do not know, or name what you could not check;"
    " never write a plausible sentence in its place.",
    "Carry that unverified label into the PR description or handback.",
    "Pick the option that is correct and robust, not the one with least effort or cost.",
    "\"Follow-up\", \"good enough\", \"probably fine\", \"out of scope\", and \"low value\" are not reasons to skip"
    " work that the Definition of Done, an acceptance criterion, or a rule calls for.",
    "Work that cannot be completed is reported as incomplete with its blocker, never claimed done.",
)


def norm(raw: str) -> str:
    """Whitespace collapsed and curly quotes straightened, so a reflow still matches."""
    return " ".join(raw.translate(str.maketrans("“”‘’", "\"\"''")).split())


def text(path: Path) -> str:
    return norm(path.read_text(encoding="utf-8"))


def generated_copies() -> list[Path]:
    """Where scripts/vendor_shared.py writes engineering-practice.md."""
    spec = importlib.util.spec_from_file_location("vendor_shared", ROOT / "scripts" / "vendor_shared.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return sorted(p for p in module.expected() if p.name == HOME.name)


def test_the_heading_occurs_exactly_once_across_shared() -> None:
    counts = {p.name: len(HEADING.findall(p.read_text(encoding="utf-8"))) for p in sorted(SHARED.glob("*.md"))}
    assert counts.get(HOME.name) == 1 and sum(counts.values()) == 1, counts


def test_the_payload_shape_bullet_links_to_the_anchor() -> None:
    """The bullet with its continuation lines, normalized, so a reflowed link still counts."""
    blocks = [norm(b) for b in re.split(r"\n(?=- |#)", HOME.read_text(encoding="utf-8"))]
    hits = [b for b in blocks if PAYLOAD_BULLET in b]
    assert len(hits) == 1, hits
    assert ANCHOR_LINK in hits[0], hits[0]


def test_no_distinctive_sentence_is_restated_elsewhere() -> None:
    home = text(HOME)
    others = sorted({*SHARED.glob("*.md"), *SKILLS.glob("*/SKILL.md")} - {HOME})
    assert others, "no other shared or skill Markdown found"
    texts = {p: text(p) for p in others}
    for sentence in DISTINCTIVE:
        assert home.count(sentence) == 1, f"not once in the home: {sentence}"
        for path, body in texts.items():
            assert sentence not in body, f"restated in {path.relative_to(ROOT)}: {sentence}"


def test_the_anchor_resolves_in_every_generated_copy() -> None:
    copies = generated_copies()
    assert copies, "vendor_shared.py vendors engineering-practice.md nowhere"
    for copy in copies:
        assert copy.exists(), f"missing copy, rerun scripts/vendor_shared.py: {copy.relative_to(ROOT)}"
        body = copy.read_text(encoding="utf-8")
        assert len(HEADING.findall(body)) == 1, f"anchor does not resolve once in {copy.relative_to(ROOT)}"
        assert ANCHOR_LINK in body, f"payload-shape link missing in {copy.relative_to(ROOT)}"
