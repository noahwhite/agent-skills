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
GROW_RULE = "Grow the list as work appears."
DISCOVERY_RULE = (
    "A new finding, remediation round, blocker, or follow-up gets an item when it is discovered, "
    "before that step starts."
)
KEEP_UNNEEDED_RULE = (
    "Do not delete items that turned out unnecessary: mark one that was started completed with a "
    "short note, and drop one only if it was never started."
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

# SKL-246 guard: one short key phrase per rule the story adds to shared/todo-tracking.md.
RULE_KEY_PHRASES = {
    "seed-list granularity": "The seed lists are the minimum granularity",
    "add-an-item": "add an item for it and mark it in progress",
    "transition": "never mark completed an item that was never in progress",
    "parallel-delegation exception": "those items are in progress together",
    "closing": "named as not done with the reason",
}

# SKL-246 guard: list creation precedes the first reference, profile or overlay read in these
# sections. Every such read goes through a `references/` file, so its first mention is the anchor.
LIST_CREATION_SECTIONS = {
    "story-to-done": "## 0. Track everything on a todo list",
    "story-refinement": "## Read first",
}
CREATE_SENTENCE = "Create the todo list as your first action, before you read any reference, the profile, or an overlay."
FIRST_READ = "references/"


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


def missing_rules(text: str) -> list[str]:
    """The SKL-246 rules whose key phrase the text no longer carries."""
    return [rule for rule, phrase in RULE_KEY_PHRASES.items() if phrase not in text]


def without_line(text: str, phrase: str) -> str:
    """The text with the one line that carries the phrase deleted."""
    lines = text.splitlines(keepends=True)
    hits = [line for line in lines if phrase in line]
    assert len(hits) == 1, phrase
    return "".join(line for line in lines if phrase not in line)


def list_created_first(text: str, heading: str) -> bool:
    """The creation sentence comes before the section's first `references/` read."""
    body = section(text, heading)
    create = body.find(CREATE_SENTENCE)
    read = body.find(FIRST_READ)
    return create != -1 and read != -1 and create < read


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
    mutated = without_line(TODO.read_text(), RULE_KEY_PHRASES[rule])
    assert missing_rules(mutated) == [rule]


@pytest.mark.parametrize("skill", list(LIST_CREATION_SECTIONS))
def test_list_creation_precedes_the_first_read(skill: str) -> None:
    assert list_created_first(skill_text(skill), LIST_CREATION_SECTIONS[skill])


@pytest.mark.parametrize("skill", list(LIST_CREATION_SECTIONS))
def test_reordering_list_creation_after_the_first_read_fails_the_guard(skill: str) -> None:
    text = skill_text(skill)
    heading = LIST_CREATION_SECTIONS[skill]
    lines = section(text, heading).splitlines(keepends=True)
    creation = next(line for line in lines if CREATE_SENTENCE in line)
    rest = [line for line in lines if line is not creation]
    read_at = next(index for index, line in enumerate(rest) if FIRST_READ in line)
    reordered = "".join(rest[: read_at + 1] + [creation] + rest[read_at + 1 :])
    mutated = text.replace(section(text, heading), reordered, 1)
    assert not list_created_first(mutated, heading)


@pytest.mark.parametrize("skill", list(LIST_CREATION_SECTIONS))
def test_deleting_list_creation_fails_the_guard(skill: str) -> None:
    mutated = without_line(skill_text(skill), CREATE_SENTENCE)
    assert not list_created_first(mutated, LIST_CREATION_SECTIONS[skill])


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
        assert sentence in text, sentence
    for retired in RETIRED_RULES:
        assert retired not in text, retired
    assert missing_rules(text) == []
