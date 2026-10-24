"""The todo-tracking capability requires a list update inside every step."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TODO = ROOT / "shared" / "todo-tracking.md"
MANIFEST = json.loads((ROOT / "skills.json").read_text())
COPIES = sorted((ROOT / "skills").glob("*/references/todo-tracking.md"))
SEED_LABEL_RE = re.compile(r"^- \*\*(.+?):\*\*", re.MULTILINE)

UPDATE_RULE = "Update the list before you move on."
SAME_STEP_RULE = (
    "Mark the finished item completed and put the next item in progress as soon as that step's "
    "outcome is observed, before starting the next step."
)
NO_BATCHING_RULE = (
    "Batching those two updates, or leaving a stale in-progress item while the next step runs, "
    "is forbidden."
)
ONE_IN_PROGRESS_RULE = (
    "Exactly one item is in progress whenever a next item exists; when none does, none is."
)
DISCOVERY_RULE = (
    "A new finding, remediation round, blocker, or follow-up gets an item when it is discovered, "
    "before that step starts."
)
OBSERVED_RULE = "An item is completed only when its outcome was observed"
FINAL_REPORT_RULE = (
    "Write the final report only after every item is completed or explicitly noted as not done."
)
SEED_PREAMBLE = (
    "Every seed list below carries one rule: update the list after each step's outcome, before "
    "the next step starts."
)
RETIRED_RULE = "Mark it completed the moment it is done, never in a batch at the end."


def rules(text: str) -> dict[int, str]:
    """The numbered rules of the capability file, each as the whole of its text."""
    found: dict[int, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        head = line.split(" ", 1)[0].removesuffix(".")
        if line[:1].isdigit() and head.isdigit() and ". " in line[:5]:
            current = found.setdefault(int(head), [])
            current.append(line.split(". ", 1)[1])
        elif current is not None and line.startswith("   "):
            current.append(line.strip())
        else:
            current = None
    return {number: "\n".join(parts) for number, parts in found.items()}


def test_rule_three_requires_the_update_in_the_same_step() -> None:
    rule = rules(TODO.read_text())[3]
    for sentence in (UPDATE_RULE, SAME_STEP_RULE, NO_BATCHING_RULE, ONE_IN_PROGRESS_RULE):
        assert sentence in rule, sentence


def test_retired_rule_three_sentence_is_gone() -> None:
    assert RETIRED_RULE not in TODO.read_text()


def test_rule_four_carries_the_discovery_sentence() -> None:
    rule = rules(TODO.read_text())[4]
    assert DISCOVERY_RULE in rule
    assert "Do not delete items that turned out unnecessary" in rule
    assert "or drop them only if they were never started" in rule


def test_rules_five_and_six_are_unchanged() -> None:
    text = TODO.read_text()
    numbered = rules(text)
    assert OBSERVED_RULE in numbered[5]
    assert FINAL_REPORT_RULE in numbered[6]


def test_seed_lists_state_the_rule_they_carry() -> None:
    text = TODO.read_text()
    seed_lists = text.split("## Seed lists", 1)[1].split("\n## ", 1)[0]
    assert SEED_PREAMBLE in seed_lists


def test_every_composing_skill_has_a_seed_label() -> None:
    labels = [label for label in SEED_LABEL_RE.findall(TODO.read_text())]
    composing = [name for name, caps in MANIFEST["skills"].items() if "todo-tracking" in caps]
    assert len(composing) == 11
    for name in composing:
        assert any(name in label for label in labels), name


def test_all_seventeen_bundles_carry_the_file() -> None:
    assert len(COPIES) == 17


@pytest.mark.parametrize("copy", COPIES, ids=lambda path: path.parent.parent.name)
def test_every_vendored_copy_carries_the_rules(copy: Path) -> None:
    text = copy.read_text()
    for sentence in (
        UPDATE_RULE,
        SAME_STEP_RULE,
        NO_BATCHING_RULE,
        ONE_IN_PROGRESS_RULE,
        DISCOVERY_RULE,
        SEED_PREAMBLE,
        FINAL_REPORT_RULE,
    ):
        assert sentence in text, sentence
    assert RETIRED_RULE not in text
