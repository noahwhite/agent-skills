"""SKL-410: every brief constraint is scoped to its role and quoted from the skill that states it.

The brief-authoring section of `skills/story-to-done/SKILL.md` states that a brief constrains only
the agent it is written for, that a prohibition names the actor it binds and the skill text it
comes from, that a role brief names what the role may do as well as what it may not, that the
completion tick is the product owner's acceptance record, and that a conflict between a brief and
its role's skill is a finding rather than a judgement call.
Each rule sentence is pinned verbatim here, and none of them carries a line number: the `path:line`
citations sit in separate sentences, so an edit above a cited line cannot break a pin.
Every citation in the section is a quotation resolved against the line it names, from the skill of
the role that holds the permission, and the tick permission stays pinned in `skills/qa-verification/SKILL.md`.
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
# takes its facts from the story and the run, and quotes each boundary it carries.
AC1 = (
    "A brief constrains only the agent it is written for.",
    "A constraint taken from the coordinator's own persona is never restated as a rule for a role.",
    "Any boundary carried into a brief is quoted from its source with `path:line` rather than paraphrased.",
    "Its facts come from the story and the run, never from a role's skill.",
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

# Every citation in the section has the form `"<quoted wording>" at `<path>:<line>``; a double-quoted
# quotation can carry the code spans its source line contains.
CITATION = re.compile(r'"([^"]+)" at `([^`]+\.md):(\d+)`')
# A citation token in any shape, backticked or not; each occurrence must belong to a parsed quotation.
CITATION_TOKEN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.md:\d+")

# Each permission the section grants, with the quote and the file that states it for that role,
# plus the actor-and-text pair AC2's example names. The file is the skill of the role the brief is
# written for, never the coordinator's own copy.
REQUIRED_CITATIONS = (
    ("skills/qa-verification/SKILL.md", TICK_SENTENCE),
    (
        "skills/qa-verification/references/linear.md",
        "Ticking the Acceptance Criteria and Definition of Done checkboxes in the description is the "
        "completion record.",
    ),
    (
        "skills/engineering-workflow/references/linear.md",
        "Move an issue to in progress the moment its branch is created, before writing code.",
    ),
    (
        "skills/qa-verification/references/linear.md",
        "Once every AC and DoD item is ticked and verified in the environment, move the issue to done.",
    ),
    (
        "skills/engineering-workflow/references/github.md",
        "Open a PR only once the branch is cleanly based on its target.",
    ),
    (
        "skills/qa-verification/SKILL.md",
        "Ship it through the normal branch and PR flow in `references/github.md`, signed when "
        "`profile.git.signed_commits` is true, and verify the signature after pushing.",
    ),
    (
        "skills/qa-verification/SKILL.md",
        "If `profile.qa.evidence_dir` is unset, the project does not keep in-repo evidence; skip this "
        "step and say so in the report.",
    ),
    ("skills/engineering-workflow/SKILL.md", "Post the review of record on the PR as one PR review"),
    ("skills/qa-verification/SKILL.md", "post the review of record on the PR"),
    # AC2's example: the actor and the prohibition, both on the cited line.
    ("skills/engineering-workflow/references/linear.md", "An implementing engineer"),
    ("skills/engineering-workflow/references/linear.md", "never rewords an AC"),
)


def citations() -> list[tuple[str, str, str]]:
    return CITATION.findall(body())


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


def test_every_citation_occurrence_is_a_parsed_quotation() -> None:
    """Each `path:line` occurrence, in any shape, must sit inside its own parsed quotation."""
    text = body()
    tokens = [match.group(0) for match in CITATION_TOKEN.finditer(text)]
    parsed = [f"{match.group(2)}:{match.group(3)}" for match in CITATION.finditer(text)]
    assert parsed, "the section cites nothing"
    assert sorted(tokens) == sorted(parsed), (
        f"citation tokens without their own quotation: {sorted(tokens)} vs {sorted(parsed)}"
    )


def test_every_citation_names_the_line_that_carries_its_quotation() -> None:
    root = ROOT.resolve()
    problems = []
    for quote, path, number in citations():
        target = (ROOT / path).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            problems.append(f"{path} is not a file of this repository")
            continue
        lines = target.read_text(encoding="utf-8").splitlines()
        at = int(number)
        if not 1 <= at <= len(lines) or quote not in lines[at - 1]:
            problems.append(f"{path}:{number} does not carry {quote!r}")
    assert not problems, problems


def test_each_permission_is_quoted_from_the_receiving_roles_skill() -> None:
    """The section's citations are exactly the required ones: no missing, no extra, no duplicate."""
    found = sorted((path, quote) for quote, path, _ in citations())
    assert found == sorted(REQUIRED_CITATIONS), (
        f"missing: {sorted(set(REQUIRED_CITATIONS) - set(found))}; "
        f"unexpected: {sorted(set(found) - set(REQUIRED_CITATIONS))}"
    )


def test_no_citation_quotes_a_degenerate_fragment() -> None:
    """A truncated quotation must fail loudly rather than resolve against one character."""
    for quote, path, number in citations():
        assert len(quote) >= 8 and " " in quote, f"{path}:{number} quotes a degenerate fragment: {quote!r}"


def test_the_ac2_actor_and_prohibition_come_from_one_line() -> None:
    """The admissibility example's actor and text are one source line; a different rule cannot supply one."""
    by_quote = {quote: (path, number) for quote, path, number in citations()}
    actor, prohibition = "An implementing engineer", "never rewords an AC"
    assert actor in by_quote and prohibition in by_quote, by_quote
    assert by_quote[actor] == by_quote[prohibition], (
        f"the actor and the prohibition cite different lines: {by_quote[actor]} vs {by_quote[prohibition]}"
    )


def test_the_tick_permission_is_still_in_the_qa_skill_and_quoted_into_the_section() -> None:
    assert TICK_SENTENCE in flat(QA_SKILL.read_text(encoding="utf-8")), (
        f"{QA_SKILL.relative_to(ROOT)} no longer states: {TICK_SENTENCE}"
    )
    assert TICK_SENTENCE in body(), f"{SECTION!r} must quote the tick permission verbatim"
