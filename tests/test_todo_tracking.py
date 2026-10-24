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
ONE_IN_PROGRESS_RULE = (
    "Exactly one item is in progress whenever a next item exists; when none does, none is."
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
FINISH_RULE = (
    "**Finish the list before reporting.**\n"
    "Write the final report only after every item is completed or explicitly noted as not done."
)
SEED_PREAMBLE = (
    "Every seed list below carries one rule: update the list after each step's outcome, before "
    "the next step starts."
)
FINAL_REPORT_RULE = (
    "Write the final report only after every item is completed or explicitly noted as not done."
)
RETIRED_RULES = (
    "Exactly one item in progress at a time.",
    "Mark it completed the moment it is done, never in a batch at the end.",
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
            current = found[int(head.group(1))] = [head.group(2)]
        elif current is not None and line.startswith("   "):
            current.append(line.strip())
        else:
            current = None
    return {number: "\n".join(parts) for number, parts in found.items()}


def sentences(rule: str) -> list[str]:
    """The rule's sentences in order, with its bold lead-in folded into the first."""
    flat = " ".join(rule.replace("**", "").split())
    return [part.strip().removesuffix(".") + "." for part in flat.split(". ") if part.strip()]


def test_rule_three_requires_the_update_in_the_same_step() -> None:
    assert sentences(rules(TODO.read_text())[3]) == [
        UPDATE_RULE,
        SAME_STEP_RULE,
        NO_BATCHING_RULE,
        ONE_IN_PROGRESS_RULE,
    ]


def test_rule_four_carries_the_discovery_sentence() -> None:
    assert sentences(rules(TODO.read_text())[4]) == [GROW_RULE, DISCOVERY_RULE, KEEP_UNNEEDED_RULE]


def test_rules_five_and_six_are_unchanged() -> None:
    numbered = rules(TODO.read_text())
    assert numbered[5] == OBSERVED_RULE
    assert numbered[6] == FINISH_RULE
    assert FINAL_REPORT_RULE in numbered[6]


def test_the_retired_rule_three_text_is_gone() -> None:
    text = TODO.read_text()
    for retired in RETIRED_RULES:
        assert retired not in text, retired


def test_seed_lists_state_the_rule_they_carry() -> None:
    assert SEED_PREAMBLE in section(TODO.read_text(), "## Seed lists")


def test_every_composing_skill_has_a_seed_entry() -> None:
    labels = [label for label, _ in SEED_BULLET_RE.findall(section(TODO.read_text(), "## Seed lists"))]
    composing = [name for name, caps in MANIFEST["skills"].items() if "todo-tracking" in caps]
    assert len(composing) == 11
    for name in composing:
        assert any(name in label for label in labels), name


def test_the_staff_personas_share_one_seed_entry() -> None:
    labels = [label for label, _ in SEED_BULLET_RE.findall(section(TODO.read_text(), "## Seed lists"))]
    assert "persona-staff-engineer and persona-staff-devops" in labels


def test_the_file_reaches_all_seventeen_bundles() -> None:
    composing = [name for name, caps in MANIFEST["skills"].items() if "todo-tracking" in caps]
    expected = sorted(composing + RUNTIME_BUNDLES)
    assert len(expected) == 17
    assert [copy.parent.parent.name for copy in COPIES] == expected


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
    for retired in RETIRED_RULES:
        assert retired not in text, retired
