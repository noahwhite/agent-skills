"""SKL-410: every brief constraint is scoped to its role and quoted from the skill that states it.

The brief-authoring section of `skills/story-to-done/SKILL.md` states that a brief constrains only
the agent it is written for, that a prohibition names the actor it binds and the skill text it
comes from, that a role brief names what the role may do as well as what it may not, that the
completion tick is the product owner's acceptance record, and that a conflict between a brief and
its role's skill is a finding rather than a judgement call.
Each rule sentence is pinned verbatim here, and none of them carries a line number: the `path:line`
citations sit in separate sentences, so an edit above a cited line cannot break a pin.
The tick permission the section quotes stays pinned in `skills/qa-verification/SKILL.md`.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "story-to-done" / "SKILL.md"
QA_SKILL = ROOT / "skills" / "qa-verification" / "SKILL.md"
SECTION = "Brief authoring"
TICK_SENTENCE = "Tick the boxes you verified."


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def flat(text: str) -> str:
    return " ".join(text.split())


def body() -> str:
    return flat(section(SKILL.read_text(encoding="utf-8"), SECTION))


# AC1: a brief constrains only its own role, never restates the coordinator's persona as a rule,
# and quotes each boundary it carries rather than paraphrasing it.
AC1 = (
    "A brief constrains only the agent it is written for.",
    "A constraint taken from the coordinator's own persona is never restated as a rule for a role.",
    "Any boundary carried into a brief is quoted from its source with `path:line` rather than paraphrased.",
)

# AC2: the test the SKL-389 stall exposed. The first example is admissible only as a label for a
# source that names its actor and its text; the second is not, because ticking a box edits DoD text.
AC2 = (
    "A prohibition is admissible only when it names the actor it binds and the skill text it comes from.",
    '"Never reword an acceptance criterion" labels the admissible case, because its source names the '
    'actor it binds and the text it forbids; "never edit the DoD text" is not admissible, because '
    "ticking a box edits DoD text.",
)

# AC3: a role brief names permissions beside prohibitions, and each one is quoted from the receiving
# role's skill with its citation. The role-specific quotations live outside the pins, below.
AC3 = (
    "Every role brief names what the role may do as well as what it may not: it ticks the boxes it "
    "verified, moves the states its skill assigns, opens its own PR, and posts the review of record.",
    "Each permission is quoted from the skill of the role the brief is written for, with its `path:line`.",
)

# AC4: the tick is the product owner's acceptance record, delegated and never removed.
AC4 = (
    "The completion tick is the product owner's acceptance record, and the current skills delegate it "
    "to the agent that observed the behaviour, so a brief may qualify the tick but may never remove "
    "the permission.",
    "This changes no ownership: the product owner remains the authority on criteria, scope, estimates "
    "and closure.",
)

# AC5: a brief that contradicts its role's skill is a finding the owner rules on.
AC5 = (
    "A role that finds a brief contradicting its skill reports the conflict and stops.",
    "The coordinator escalates it to the owner, and neither resolves it silently in either direction.",
)

PINS = {"AC1": AC1, "AC2": AC2, "AC3": AC3, "AC4": AC4, "AC5": AC5}


def test_the_brief_authoring_section_occurs_once() -> None:
    headings = re.findall(rf"^## {re.escape(SECTION)}\s*$", SKILL.read_text(encoding="utf-8"), re.MULTILINE)
    assert len(headings) == 1, f"expected one {SECTION!r} section, found {len(headings)}"


@pytest.mark.parametrize("ac", sorted(PINS))
def test_each_rule_sentence_is_pinned_verbatim_in_the_section(ac: str) -> None:
    text = body()
    for sentence in PINS[ac]:
        assert sentence in text, f"{ac}: missing or reworded in {SECTION!r}: {sentence}"


@pytest.mark.parametrize("ac", sorted(PINS))
def test_each_rule_sentence_appears_exactly_once_in_the_skill(ac: str) -> None:
    text = flat(SKILL.read_text(encoding="utf-8"))
    for sentence in PINS[ac]:
        assert text.count(sentence) == 1, f"{ac}: stated {text.count(sentence)} times: {sentence}"


@pytest.mark.parametrize("ac", sorted(PINS))
def test_no_pinned_rule_sentence_carries_a_line_number(ac: str) -> None:
    """A pin must survive an edit above the line a citation names, so a citation is never pinned."""
    for sentence in PINS[ac]:
        assert not re.search(r"\.md:\d+|\bline \d+\b", sentence, re.IGNORECASE), (
            f"{ac}: pinned with a line number: {sentence}"
        )


# Every citation in the section has the form `<quoted wording>` at `<path>:<line>`. Resolving each one
# from the prose keeps the citation honest without hard-coding a line number in this test: an edit
# above a cited line moves the wording, this test fails, and the number is corrected in the prose.
CITATION = re.compile(r"`([^`]+)` at `([^`]+\.md):(\d+)`")


def test_every_citation_names_the_line_that_carries_its_quotation() -> None:
    citations = CITATION.findall(body())
    assert len(citations) >= 6, f"too few citations to be the section's set: {citations}"
    problems = []
    for quote, path, number in citations:
        lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
        at = int(number)
        if not 1 <= at <= len(lines) or quote not in lines[at - 1]:
            problems.append(f"{path}:{number} does not carry {quote!r}")
    assert not problems, problems


def test_the_section_quotes_the_two_files_ac3_names() -> None:
    text = body()
    for path in ("skills/qa-verification/SKILL.md", "skills/story-to-done/references/linear.md"):
        assert re.search(re.escape(path) + r":\d+", text), f"no `{path}:<line>` citation in {SECTION!r}"


def test_the_tick_permission_is_still_in_the_qa_skill_and_quoted_into_the_section() -> None:
    assert TICK_SENTENCE in flat(QA_SKILL.read_text(encoding="utf-8")), (
        f"{QA_SKILL.relative_to(ROOT)} no longer states: {TICK_SENTENCE}"
    )
    assert TICK_SENTENCE in body(), f"{SECTION!r} must quote the tick permission verbatim"
