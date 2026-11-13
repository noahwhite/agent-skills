"""SKL-162: engineering-workflow selects exactly one run path (spike, no-deployment or deployed) in step 1."""

import hashlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "engineering-workflow" / "SKILL.md"


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def step_one_lines() -> list[str]:
    return section(SKILL.read_text(), "1. Triage the story").splitlines()


# Each normative sentence of the step 1 path selection, pinned whole on its own line, so a
# deleted or reworded sentence fails exactly one test id.
PINS = {
    "triage-item": '7. Select the run\'s path as "Select the path" below states, before any later step runs.',
    "subsection": "### Select the path",
    "three-paths": "A run follows exactly one path: `spike`, `no-deployment` or `deployed`.",
    "brief-governs": (
        "When a brief states the path, that path governs: no ask case applies and you never reselect it."
    ),
    "select-before-later-steps": (
        "When no brief states a path, select exactly one path before any later step runs."
    ),
    "ask-intro": "Ask the user for the path, and run no later step until answered, in exactly these cases:",
    "ask-environments-absent": "- `profile.environments` is absent (an absent key is never read as `[]`);",
    "ask-no-integration-entry": (
        "- `profile.environments` is non-empty and no entry's `branch` equals `profile.git.integration_branch`;"
    ),
    "ask-spike-title-no-label": (
        "- the story title starts with `[Spike]` and the story lacks the spike label "
        "(including when `profile.tracker.labels.spike` is unset);"
    ),
    "ask-spike-label-no-title": (
        "- the story carries the spike label and its title does not start with `[Spike]`."
    ),
    "ask-precedence": "An ask case takes precedence over the selection conditions below.",
    "ask-answer-is-path": (
        "The answer is one of `spike`, `no-deployment` or `deployed`, and it is the path: "
        "it replaces the selection below."
    ),
    "no-inference": "Never infer a path from prose, and ask nothing else about the path.",
    "select-intro": "Otherwise select:",
    "select-spike": (
        "- `spike` when the story carries the label named by `profile.tracker.labels.spike`, looked up on the "
        "story's team under the differing-team rule in [references/linear.md](references/linear.md) "
        '"Team resolution";'
    ),
    "select-no-deployment": (
        "- otherwise `no-deployment` when `profile.environments` is present and is `[]`;"
    ),
    "select-deployed": (
        "- otherwise `deployed` when `profile.environments` has an entry whose `branch` equals "
        "`profile.git.integration_branch`."
    ),
    "path-governs-run": "The selected path governs the whole run.",
}


@pytest.mark.parametrize("pin", list(PINS.values()), ids=list(PINS))
def test_step_one_pins_path_selection_sentence(pin: str) -> None:
    assert pin in step_one_lines(), f"step 1 must read the pinned sentence exactly: {pin}"


ASK_CASES = ("ask-environments-absent", "ask-no-integration-entry", "ask-spike-title-no-label", "ask-spike-label-no-title")
SELECTIONS = ("select-spike", "select-no-deployment", "select-deployed")


def block_after(lines: list[str], intro: str) -> list[str]:
    """The bullet lines that directly follow ``intro``, after one optional blank line."""
    start = lines.index(intro) + 1
    if start < len(lines) and not lines[start].strip():
        start += 1
    block = []
    for line in lines[start:]:
        if not line.startswith("- "):
            break
        block.append(line)
    return block


def test_ask_cases_are_exactly_the_four_named_cases() -> None:
    lines = step_one_lines()
    assert block_after(lines, PINS["ask-intro"]) == [PINS[key] for key in ASK_CASES]


def test_selection_conditions_are_ordered_spike_then_no_deployment_then_deployed() -> None:
    lines = step_one_lines()
    assert block_after(lines, PINS["select-intro"]) == [PINS[key] for key in SELECTIONS]


def test_ask_cases_come_before_the_selection_they_take_precedence_over() -> None:
    lines = step_one_lines()
    assert lines.index(PINS["ask-intro"]) < lines.index(PINS["ask-precedence"]) < lines.index(PINS["select-intro"])


TRACKER_FALLBACK = "If the tracker cannot be updated, stop and say the transition was not performed; never claim it was."
SUBSECTION_ORDER = (
    "subsection",
    "three-paths",
    "brief-governs",
    "select-before-later-steps",
    "ask-intro",
    *ASK_CASES,
    "ask-precedence",
    "ask-answer-is-path",
    "no-inference",
    "select-intro",
    *SELECTIONS,
    "path-governs-run",
)


def test_subsection_directly_follows_the_tracker_fallback_paragraph() -> None:
    lines = step_one_lines()
    assert lines.index(PINS["subsection"]) == lines.index(TRACKER_FALLBACK) + 2


def test_subsection_holds_only_the_pinned_sentences_in_order() -> None:
    lines = step_one_lines()
    body = [line for line in lines[lines.index(PINS["subsection"]):] if line.strip()]
    assert body == [PINS[key] for key in SUBSECTION_ORDER]


# AC3: the path selection lives in step 1 only; no pinned sentence appears in any later step.
@pytest.mark.parametrize("key", list(PINS), ids=list(PINS))
def test_path_selection_sentence_appears_only_in_step_one(key: str) -> None:
    lines = SKILL.read_text().splitlines()
    assert lines.count(PINS[key]) == 1, f"{key} must appear exactly once in the skill"


# AC3: the text of steps 2 to 12 ("## 2. Plan slices" up to "## Operational rules") is unchanged
# from the base commit 7ae1b94. A story in scope to change those steps updates this digest.
STEPS_TWO_TO_TWELVE_SHA256 = "a36c006733b7b3bc23d65530faee575a02b5e59c1b8c68d48d7657fcf639f2c3"


def test_steps_two_to_twelve_are_unchanged() -> None:
    text = SKILL.read_text()
    start = text.index("\n## 2. Plan slices\n") + 1
    end = text.index("\n## Operational rules\n") + 1
    assert hashlib.sha256(text[start:end].encode()).hexdigest() == STEPS_TWO_TO_TWELVE_SHA256
