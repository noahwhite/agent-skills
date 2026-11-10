"""The todo-tracking capability requires a list update inside every step."""

import json
import re
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
TRANSITION_HEADING = "Move every item through in progress."
TRANSITION_RULE = (
    "Mark an item in progress before its first tool call and completed as soon as its work is done; "
    "never mark completed an item that was never in progress."
)
PARALLEL_HEADING = "One item in progress, except parallel delegations."
PARALLEL_RULE = (
    "One item is in progress at a time for sequential work; when one step launches several "
    "delegations in parallel, each delegation has its own item, and those items are in progress "
    "together from launch until each result is read."
)
GROW_RULE = "Grow the list as work appears."
ADD_ITEM_RULE = (
    "Before starting any work that has no item (a further round or re-run, a follow-up request, a "
    "fix found along the way), add an item for it and mark it in progress."
)
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
CLOSING_RULE = (
    "Before the final report, every item is completed, or is left open and named as not done with "
    "the reason."
)
FINISH_RULE = "**Finish the list before reporting.**\n" + CLOSING_RULE
SEED_GRANULARITY_RULE = (
    "The seed lists are the minimum granularity: one item per unit they name, never merged into "
    "phase items, and split further as the task demands."
)
SEED_UNKNOWN_COUNT_RULE = (
    "Where a count is not known up front, each further round or re-run gets its item when it starts."
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
# single rule fails the guard while rewording around the phrase does not.
RULE_KEY_PHRASES = {
    "seed-list granularity": ("## Seed lists", "minimum granularity"),
    "add-an-item": ("## Rules", "add an item for it and mark it in progress"),
    "transition": ("## Rules", "never mark completed an item that was never in progress"),
    "parallel-delegation exception": ("## Rules", "in progress together from launch until each result is read"),
    "closing": ("## Rules", "named as not done with the reason"),
}
# SKL-246 guard: the list-creation instruction and the clause that puts it before every read.
CREATE_PHRASE = "create the todo list"
BEFORE_READS_PHRASE = "before you read any reference, the profile, or an overlay"
# Any of these, before the creation instruction, means the section orders a read first.
READ_MARKERS = ("references/", "profile", "overlay")
LIST_CREATION_SECTIONS = {
    "story-to-done": "0. Track everything on a todo list",
    "story-refinement": "Read first",
}


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
    flat = " ".join(rule.replace("**", "").split())
    return [part.strip().removesuffix(".") + "." for part in flat.split(". ") if part.strip()]


def flat(text: str) -> str:
    return " ".join(text.split())


def missing_rules(text: str) -> list[str]:
    """The SKL-246 rules whose key phrase is absent from the section that must carry it."""
    return [
        name for name, (heading, phrase) in RULE_KEY_PHRASES.items()
        if phrase not in flat(section(text, heading))
    ]


def list_creation_order_faults(body: str) -> list[str]:
    """Why a section does not put list creation before every reference, profile or overlay read."""
    text = flat(body).lower()
    create = text.find(CREATE_PHRASE)
    if create == -1:
        return ["no list-creation instruction"]
    faults = []
    if BEFORE_READS_PHRASE not in text[create:]:
        faults.append("the list-creation instruction does not say it comes before every read")
    earlier = [marker for marker in READ_MARKERS if marker in text[:create]]
    if earlier:
        faults.append(f"a read is ordered before list creation: {earlier}")
    return faults


def test_rule_three_requires_the_update_in_the_same_step() -> None:
    assert sentences(rules(TODO.read_text())[3]) == [
        UPDATE_RULE,
        SAME_STEP_RULE,
        NO_BATCHING_RULE,
    ]


def test_rule_four_is_the_transition_rule() -> None:
    assert rules(TODO.read_text())[4] == f"**{TRANSITION_HEADING}**\n{TRANSITION_RULE}"


def test_rule_five_is_the_parallel_delegation_exception() -> None:
    assert rules(TODO.read_text())[5] == f"**{PARALLEL_HEADING}**\n{PARALLEL_RULE}"


def test_rule_six_carries_the_add_an_item_and_discovery_sentences() -> None:
    assert sentences(rules(TODO.read_text())[6]) == [
        GROW_RULE,
        ADD_ITEM_RULE,
        DISCOVERY_RULE,
        KEEP_UNNEEDED_RULE,
    ]


def test_rules_seven_and_eight_are_the_observed_and_closing_rules() -> None:
    numbered = rules(TODO.read_text())
    assert sorted(numbered) == list(range(1, 9))
    assert numbered[7] == OBSERVED_RULE
    assert numbered[8] == FINISH_RULE


def test_the_retired_rule_text_is_gone() -> None:
    text = TODO.read_text()
    for retired in RETIRED_RULES:
        assert retired not in text, retired


def test_seed_lists_state_the_rule_they_carry() -> None:
    assert SEED_PREAMBLE in section(TODO.read_text(), "## Seed lists")


def test_seed_lists_are_binding_minimum_granularity() -> None:
    body = section(TODO.read_text(), "## Seed lists")
    assert SEED_GRANULARITY_RULE in body
    assert SEED_UNKNOWN_COUNT_RULE in body


def test_every_skl_246_rule_is_present() -> None:
    assert missing_rules(TODO.read_text()) == []


@pytest.mark.parametrize("rule", list(RULE_KEY_PHRASES))
def test_deleting_any_one_rule_fails_the_guard(rule: str) -> None:
    """Mutation proof: drop each rule's line from the real file and the guard names that rule."""
    phrase = RULE_KEY_PHRASES[rule][1]
    lines = TODO.read_text().splitlines(keepends=True)
    assert sum(phrase in line for line in lines) == 1, f"{rule}: the key phrase must sit on one line"
    mutated = "".join(line for line in lines if phrase not in line)
    assert missing_rules(mutated) == [rule]


@pytest.mark.parametrize("skill", list(LIST_CREATION_SECTIONS))
def test_list_creation_precedes_every_read(skill: str) -> None:
    text = (ROOT / "skills" / skill / "SKILL.md").read_text()
    assert list_creation_order_faults(section(text, "## " + LIST_CREATION_SECTIONS[skill])) == []


@pytest.mark.parametrize("skill", list(LIST_CREATION_SECTIONS))
def test_reordering_list_creation_after_a_read_fails_the_guard(skill: str) -> None:
    """Mutation proof: move the creation sentence to the end of its section and the guard fails."""
    body = section((ROOT / "skills" / skill / "SKILL.md").read_text(), "## " + LIST_CREATION_SECTIONS[skill])
    lines = body.splitlines()
    index = next(i for i, line in enumerate(lines) if CREATE_PHRASE in line.lower())
    reordered = lines[:index] + lines[index + 1:] + [lines[index]]
    assert list_creation_order_faults("\n".join(reordered))


def test_the_retired_read_first_ordering_fails_the_guard() -> None:
    """The pre-SKL-246 wording, which created the list after the profile read, fails the guard."""
    retired = (
        "Once the story ID is known and the profile is read, create the todo list per "
        "`references/todo-tracking.md`."
    )
    assert list_creation_order_faults(retired)


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
        TRANSITION_RULE,
        PARALLEL_RULE,
        ADD_ITEM_RULE,
        DISCOVERY_RULE,
        SEED_GRANULARITY_RULE,
        SEED_UNKNOWN_COUNT_RULE,
        SEED_PREAMBLE,
        CLOSING_RULE,
    ):
        assert sentence in flat(text), sentence
    for retired in RETIRED_RULES:
        assert retired not in text, retired
    assert missing_rules(text) == []
