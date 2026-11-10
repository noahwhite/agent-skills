"""The todo-tracking capability requires a list update inside every step."""

import json
import re
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TODO = ROOT / "shared" / "todo-tracking.md"
MANIFEST = json.loads((ROOT / "skills.json").read_text())
COPIES = sorted((ROOT / "skills").glob("*/references/todo-tracking.md"))
SEED_BULLET_RE = re.compile(r"^- \*\*(.+?):\*\* (\S.*)$", re.MULTILINE)
# The bundles that carry the file through shared/runtimes.md rather than the manifest.
RUNTIME_BUNDLES = [
    "adversarial-review-pipeline",
    "linear-bug",
    "linear-epic",
    "linear-investigation",
    "linear-spike",
    "linear-user-story",
]

UPDATE_RULE = "Update the list before you move on."
SAME_STEP_RULE = (
    "Mark the finished item completed and put the next item in progress as soon as that step's "
    "outcome is observed, before starting the next step."
)
NO_BATCHING_RULE = (
    "Batching those two updates, or leaving a stale in-progress item while the next step runs, "
    "is forbidden."
)
GROW_RULE = "Grow the list as work appears."
DISCOVERY_RULE = (
    "A new finding, remediation round, blocker, or follow-up gets an item when it is discovered, "
    "before that step starts."
)
KEEP_UNNEEDED_RULE = (
    "Do not delete items that turned out unnecessary; mark them completed with a short note, or "
    "drop them only if they were never started."
)
OBSERVED_RULE = (
    "**An item is completed only when its outcome was observed** (test output seen, run concluded, "
    "state read back), not when the command was issued."
)
SEED_PREAMBLE = (
    "Every seed list below carries one rule: update the list after each step's outcome, before "
    "the next step starts."
)
RETIRED_RULES = (
    "Exactly one item in progress at a time.",
    "Mark it completed the moment it is done, never in a batch at the end.",
    # SKL-246: replaced by the parallel-delegation exception, the closing rule and binding seed lists.
    "Exactly one item is in progress whenever a next item exists; when none does, none is.",
    "Write the final report only after every item is completed or explicitly noted as not done.",
    "Starting points only; split further as the task demands.",
)

# SKL-246 guard: one short key phrase per rule, in the section that carries it, so deleting any
# single rule fails the guard while rewording around the phrase does not. The rule number pins
# where a Rules phrase lives; the seed-list phrase has no number.
RULE_KEY_PHRASES = {
    "seed-list granularity": ("## Seed lists", None, "minimum granularity"),
    "unknown-count rounds": ("## Seed lists", None, "each further round or re-run gets its item"),
    "transition": ("## Rules", 4, "never mark completed an item that was never in progress"),
    "parallel-delegation exception": ("## Rules", 5, "in progress together from launch until each result is read"),
    "add-an-item": ("## Rules", 6, "add an item for it and mark it in progress"),
    "sequential pause": ("## Rules", 6, "return it to pending"),
    "closing": ("## Rules", 8, "named as not done with the reason"),
}

# SKL-246 guard on list-creation order. The scope is the skill text from its title to the end of
# the section that creates the list, so Arguments, Read first and Metrics are covered too.
LIST_CREATION_SECTIONS = {
    "story-to-done": "## 0. Track everything on a todo list",
    "story-refinement": "## Read first",
}
CREATE_PHRASE = "create the todo list"
FIRST_ACTION_PHRASE = "as your first action"
BEFORE_READS_RE = re.compile(
    r"before (?:you read|reading) any reference,? (?:the )?profile,? or (?:an )?overlay"
)
# A read instruction: a read verb (not passive) in the same clause as a reference, the profile or
# an overlay. Nouns alone ("the profile may be incomplete") are not reads.
READ_VERB_RE = re.compile(r"(?<!\bis )(?<!\bare )(?<!\bbe )\b(?:read|reading|open|load|consult|map|find)\b")
READ_TARGET_RE = re.compile(r"references/|\breferences?\b|\bthe profile\b|\boverlays?\b")
NEGATED_READ_RE = re.compile(
    r"\b(?:not|never|no)\s+(?:even\s+)?(?:\w+\s+)?(?:read|open|load)\b|\b(?:read|open|load)\s+no\b"
)
AFTER_LIST_RE = re.compile(
    r"after step 0 creates the todo list|after the todo list is created|after (?:you )?creat(?:e|ing) the todo list"
)
BEFORE_LIST_RE = re.compile(
    r"before (?:step 0 creates|creating|you create|the todo list)"
)
REFINEMENT_CARVE_OUT = (
    "The only actions before it are the two that Arguments orders before the todo list: resolving the "
    "arguments and, when Arguments calls for it, the `invocation_start` timestamp command."
)


def section(text: str, heading: str) -> str:
    """The body of one `## ` section, without its heading or the next heading."""
    assert f"\n{heading}\n" in text, f"missing the {heading} section"
    return text.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0]


def rules(text: str) -> dict[int, str]:
    """The numbered rules of the Rules section, keyed by their number."""
    found: dict[int, list[str]] = {}
    current: list[str] | None = None
    for line in section(text, "## Rules").splitlines():
        head = re.match(r"^(\d+)\. (.*)$", line)
        if head:
            number = int(head.group(1))
            assert number not in found, f"rule {number} is defined twice"
            current = found[number] = [head.group(2)]
        elif current is not None and line.startswith("   "):
            current.append(line.strip())
        else:
            current = None
    return {number: "\n".join(parts) for number, parts in found.items()}


def sentences(rule: str) -> list[str]:
    """The rule's sentences in order, with its bold lead-in folded into the first."""
    joined = " ".join(rule.replace("**", "").split())
    return [part.strip().removesuffix(".") + "." for part in joined.split(". ") if part.strip()]


def flat(text: str) -> str:
    return " ".join(text.split())


def missing_rules(text: str) -> list[str]:
    """The SKL-246 rules whose key phrase is absent from the section, or numbered rule, that carries it."""
    numbered = rules(text)
    missing = []
    for name, (heading, number, phrase) in RULE_KEY_PHRASES.items():
        body = section(text, heading) if number is None else numbered.get(number, "")
        if phrase not in flat(body):
            missing.append(name)
    return missing


def without_sentence(text: str, phrase: str) -> str:
    """The text with the one sentence carrying the phrase removed, however its lines are wrapped."""
    words = r"\s+".join(map(re.escape, phrase.split()))
    sentence = rf"[^.#]*{words}[^.#]*\."
    mutated, count = re.subn(rf"^{sentence}[ \t]*\n|(?<=\. ){sentence}", "", text, flags=re.MULTILINE)
    assert count == 1, f"{phrase!r} must sit in exactly one sentence"
    return mutated


def rewrapped(text: str, width: int) -> str:
    """The text with every non-heading line refilled to the width, keeping list indentation."""
    out = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            out.append(line)
            continue
        lead = re.match(r"^(\s*(?:\d+\. |- )?)", line).group(1)
        out.append(textwrap.fill(line, width, subsequent_indent=" " * len(lead), break_long_words=False))
    return "\n".join(out) + "\n"


def creation_scope(text: str, heading: str) -> tuple[str, str]:
    """The skill text from its title up to the list-creation section, and that section itself."""
    title = text.index("\n# ")
    start = text.index(f"\n{heading}\n")
    end = text.find("\n## ", start + 1)
    return text[title:start], text[start:] if end == -1 else text[start:end]


def clauses(block: str) -> list[str]:
    """Lowercased clauses, split at sentence, semicolon and colon ends, with headings and quotes dropped."""
    block = re.sub(r"^#.*$", ".", block, flags=re.MULTILINE)
    block = re.sub(r'"[^"\n]*"', '""', block)
    return [part for part in re.split(r"(?<=[.;:])\s+", flat(block).lower()) if part.strip(". ")]


def is_read(clause: str) -> bool:
    return bool(READ_VERB_RE.search(clause) and READ_TARGET_RE.search(clause) and not NEGATED_READ_RE.search(clause))


def list_creation_order_faults(text: str, heading: str) -> list[str]:
    """Why the skill does not create its list before every reference, profile or overlay read."""
    before, body = creation_scope(text, heading)
    earlier, own = clauses(before), clauses(body)
    index = next((i for i, clause in enumerate(own) if CREATE_PHRASE in clause), None)
    if index is None:
        return ["no list-creation instruction"]
    create = own[index]
    faults = []
    if FIRST_ACTION_PHRASE not in create:
        faults.append("list creation is not the first action")
    if not BEFORE_READS_RE.search(create):
        faults.append("the list-creation instruction does not say it comes before every read")
    if READ_VERB_RE.search(create[: create.index(CREATE_PHRASE)]):
        faults.append(f"the list-creation instruction orders a read first: {create!r}")
    for clause in earlier + own[:index]:
        if is_read(clause) and not AFTER_LIST_RE.search(clause):
            faults.append(f"a read is ordered before list creation: {clause!r}")
    for clause in earlier + own[:index] + own[index + 1:]:
        if is_read(clause) and BEFORE_LIST_RE.search(clause):
            faults.append(f"a read is ordered before list creation: {clause!r}")
    return faults


def skill_text(skill: str) -> str:
    return (ROOT / "skills" / skill / "SKILL.md").read_text()


def test_rule_three_requires_the_update_in_the_same_step() -> None:
    assert sentences(rules(TODO.read_text())[3]) == [
        UPDATE_RULE,
        SAME_STEP_RULE,
        NO_BATCHING_RULE,
    ]


def test_rule_six_keeps_the_grow_discovery_and_keep_sentences() -> None:
    six = sentences(rules(TODO.read_text())[6])
    assert six[0] == GROW_RULE
    assert DISCOVERY_RULE in six
    assert KEEP_UNNEEDED_RULE in six


def test_rules_one_to_eight_with_the_observed_rule_seventh() -> None:
    numbered = rules(TODO.read_text())
    assert sorted(numbered) == list(range(1, 9))
    assert numbered[7] == OBSERVED_RULE


def test_the_retired_rule_text_is_gone() -> None:
    text = TODO.read_text()
    for retired in RETIRED_RULES:
        assert retired not in text, retired


def test_seed_lists_state_the_rule_they_carry() -> None:
    assert SEED_PREAMBLE in section(TODO.read_text(), "## Seed lists")


def test_every_skl_246_rule_is_present() -> None:
    assert missing_rules(TODO.read_text()) == []


@pytest.mark.parametrize("rule", list(RULE_KEY_PHRASES))
def test_deleting_any_one_rule_fails_the_guard(rule: str) -> None:
    """Mutation proof: drop the sentence carrying each rule from the real file and the guard names that rule."""
    assert missing_rules(without_sentence(TODO.read_text(), RULE_KEY_PHRASES[rule][2])) == [rule]


@pytest.mark.parametrize("width", [40, 200])
def test_rewrapping_the_rules_keeps_the_guard_green(width: int) -> None:
    assert missing_rules(rewrapped(TODO.read_text(), width)) == []


@pytest.mark.parametrize("skill", list(LIST_CREATION_SECTIONS))
def test_list_creation_precedes_every_read(skill: str) -> None:
    assert list_creation_order_faults(skill_text(skill), LIST_CREATION_SECTIONS[skill]) == []


def mutated_skill(skill: str, old: str, new: str) -> str:
    text = skill_text(skill)
    assert text.count(old) == 1, old
    return text.replace(old, new)


@pytest.mark.parametrize("skill", list(LIST_CREATION_SECTIONS))
def test_reordering_list_creation_after_a_read_fails_the_guard(skill: str) -> None:
    """Mutation proof: move the creation sentence to the end of its section and the guard fails."""
    heading = LIST_CREATION_SECTIONS[skill]
    text = skill_text(skill)
    _, body = creation_scope(text, heading)
    lines = body.splitlines()
    index = next(i for i, line in enumerate(lines) if CREATE_PHRASE in line.lower())
    reordered = "\n".join(lines[:index] + lines[index + 1:] + [lines[index]])
    assert list_creation_order_faults(text.replace(body, reordered), heading)


@pytest.mark.parametrize("skill", list(LIST_CREATION_SECTIONS))
def test_a_reference_read_in_arguments_fails_the_guard(skill: str) -> None:
    """Mutation proof: a runtimes lookup ordered in Arguments, above the list, fails the guard."""
    text = mutated_skill(
        skill, "## Arguments\n\n", "## Arguments\n\n- Map each model to your runtime with `references/runtimes.md`.\n"
    )
    assert list_creation_order_faults(text, LIST_CREATION_SECTIONS[skill])


def test_the_retired_metrics_read_trigger_fails_the_guard() -> None:
    """Mutation proof: the pre-gate story-to-done Metrics trigger read a reference before step 0."""
    text = mutated_skill("story-to-done", "right after step 0 creates the todo list:", "once the story ID is known:")
    assert list_creation_order_faults(text, LIST_CREATION_SECTIONS["story-to-done"])


@pytest.mark.parametrize("skill", list(LIST_CREATION_SECTIONS))
def test_a_contradicting_read_after_creation_fails_the_guard(skill: str) -> None:
    """Mutation proof: a later sentence that orders a read before the list fails the guard."""
    heading = LIST_CREATION_SECTIONS[skill]
    text = skill_text(skill)
    _, body = creation_scope(text, heading)
    mutated = text.replace(body, body.rstrip("\n") + "\nRead `references/profile.md` before creating the todo list.\n")
    assert list_creation_order_faults(mutated, heading)


@pytest.mark.parametrize("skill", list(LIST_CREATION_SECTIONS))
def test_a_read_folded_into_the_creation_sentence_fails_the_guard(skill: str) -> None:
    text = mutated_skill(skill, "Create the todo list as your first action", "Read first, then create the todo list as your first action")
    assert list_creation_order_faults(text, LIST_CREATION_SECTIONS[skill])


@pytest.mark.parametrize("skill", list(LIST_CREATION_SECTIONS))
def test_creation_that_is_not_the_first_action_fails_the_guard(skill: str) -> None:
    text = mutated_skill(skill, "as your first action", "right after the actions Arguments orders before it")
    assert list_creation_order_faults(text, LIST_CREATION_SECTIONS[skill])


def test_the_retired_read_first_ordering_fails_the_guard() -> None:
    """The pre-SKL-246 wording, which created the list after the profile read, fails the guard."""
    heading = LIST_CREATION_SECTIONS["story-to-done"]
    text = skill_text("story-to-done")
    create = next(line for line in creation_scope(text, heading)[1].splitlines() if CREATE_PHRASE in line.lower())
    retired = "Once the story ID is known and the profile is read, create the todo list per `references/todo-tracking.md`."
    assert list_creation_order_faults(text.replace(create, retired), heading)


@pytest.mark.parametrize("skill", list(LIST_CREATION_SECTIONS))
def test_equivalent_wording_keeps_the_guard_green(skill: str) -> None:
    text = mutated_skill(
        skill,
        "before you read any reference, the profile, or an overlay",
        "before reading any reference, profile, or overlay",
    )
    assert list_creation_order_faults(text, LIST_CREATION_SECTIONS[skill]) == []


@pytest.mark.parametrize("skill", list(LIST_CREATION_SECTIONS))
def test_a_profile_mention_that_is_not_a_read_keeps_the_guard_green(skill: str) -> None:
    text = mutated_skill(skill, "Create the todo list as your first action", "The profile may be incomplete.\nCreate the todo list as your first action")
    assert list_creation_order_faults(text, LIST_CREATION_SECTIONS[skill]) == []


def test_story_refinement_names_its_only_pre_list_actions() -> None:
    """The refinement carve-out is deliberate: Arguments orders exactly two actions before the list."""
    text = skill_text("story-refinement")
    assert REFINEMENT_CARVE_OUT in flat(section(text, "## Read first"))
    arguments = [clause for clause in clauses(section(text, "## Arguments")) if "before the todo list" in clause]
    assert len(arguments) == 2, arguments


def test_every_composing_skill_has_a_seed_entry() -> None:
    labels = [label for label, _ in SEED_BULLET_RE.findall(section(TODO.read_text(), "## Seed lists"))]
    composing = [name for name, caps in MANIFEST["skills"].items() if "todo-tracking" in caps]
    assert len(composing) == 12
    for name in composing:
        assert any(name in label for label in labels), name


def test_the_staff_personas_share_one_seed_entry() -> None:
    labels = [label for label, _ in SEED_BULLET_RE.findall(section(TODO.read_text(), "## Seed lists"))]
    assert "persona-staff-engineer and persona-staff-devops" in labels


def test_the_file_reaches_all_eighteen_bundles() -> None:
    composing = [name for name, caps in MANIFEST["skills"].items() if "todo-tracking" in caps]
    expected = sorted(composing + RUNTIME_BUNDLES)
    assert len(expected) == 18
    assert [copy.parent.parent.name for copy in COPIES] == expected


def test_story_refinement_seed_sets_priority_before_the_tracker_writes() -> None:
    """SKL-215: the priority item sits immediately before the PO tracker-write item."""
    seed = next((line for line in section(TODO.read_text(), "## Seed lists").splitlines()
                 if line.startswith("- **story-refinement:**")), None)
    assert seed is not None, "the Seed lists section has no story-refinement entry"
    assert (
        "set priority (the PO's decision, the comparison it rests on, and the read-back), "
        "each PO tracker write and read-back"
    ) in seed


@pytest.mark.parametrize("copy", COPIES, ids=lambda path: path.parent.parent.name)
def test_every_vendored_copy_carries_the_rules(copy: Path) -> None:
    text = copy.read_text()
    for sentence in (
        UPDATE_RULE,
        SAME_STEP_RULE,
        NO_BATCHING_RULE,
        DISCOVERY_RULE,
        SEED_PREAMBLE,
    ):
        assert sentence in flat(text), sentence
    for retired in RETIRED_RULES:
        assert retired not in text, retired
    assert missing_rules(text) == []
