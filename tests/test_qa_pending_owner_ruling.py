"""Pins for the qa-verification pending owner ruling (SKL-156): steps 4 and 6."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "qa-verification" / "SKILL.md"

STEP_4 = "4. Adjudicate and record"
STEP_6 = "6. Decide status"

# Step 4: the verdict, the qualifying test and the record.
STEP_4_LINES = (
    "1. Map every AC and DoD item to its evidence with a verdict: verified, failed, correct by design, "
    "out of scope (naming the owning story), not covered, or `pending owner ruling`.",
    "2. **Pending owner ruling.**",
    "   Record an item as `pending owner ruling` only when two or more readings of the item's quoted AC or DoD "
    "text give different verdicts on the same evidence.",
    "   Missing evidence, access or execution alone does not qualify.",
    "   An item that fails under every reading is a failure, and an item met under every reading is verified.",
    "   The record goes in the QA evidence comment on the story (item 5) and gives the item, its quoted text, "
    "each reading with the verdict and the evidence under it, and the product owner as its owner.",
    "   Post a concise QA evidence comment on the story: build SHA, environment, fixtures used, per-item verdict, "
    "each pending owner ruling record (item 2), and any gaps.",
)

# Step 4: cross-references to the renumbered items 4 (evidence page) and 5 (tracker).
STEP_4_CROSS_REFERENCE_LINES = (
    "   The hosted-page link is for the user's review only; it never goes into the tracker (item 5).",
    "   Also attach the evidence page as a local file when item 4 built one and it is self-contained "
    "(screenshots inlined); otherwise skip it, since the attached screenshots and assertion output are the record.",
)

# Exact bodies: a line added inside these blocks (for example a contradicting exception) fails the pin.
STEP_4_ITEM_2_BODY = (
    "2. **Pending owner ruling.**",
    STEP_4_LINES[2],
    STEP_4_LINES[3],
    STEP_4_LINES[4],
    STEP_4_LINES[5],
)

# Step 6: routing with pending items outstanding.
STEP_6_ROUTING_LINES = (
    "  With only `pending owner ruling` items outstanding and no failed item, QA is not finished and the story "
    "stays here; the QA evidence comment names each pending item, its owner and the ruling it waits on.",
    "- Once QA is finished, the story ends in exactly one state; a failed item finishes QA even while other "
    "items are `pending owner ruling`:",
    "    Items also `pending owner ruling` are listed apart in the QA evidence comment as not for the engineer.",
    "    Write no deployment-review AC amendment for a pending item.",
)

# Step 6: how a ruling reaches QA, and the done guard.
STEP_6_RULING_LINES = (
    "- **A ruling reaches QA only as the product owner's dated AC amendment on the tracker.**",
    "  After that amendment, a new QA round (a new QA agent on an unchanged brief) verifies the amended item "
    "against the amended text with fresh evidence.",
    "    Never mark done on an AC amendment alone, and never while any item is still `pending owner ruling`.",
)

STEP_6_DONE_BODY = (
    "  - **`profile.tracker.states.done`**: every AC and DoD item is verified as met, and the evidence PR is "
    "merged (when in-repo evidence is kept).",
    "    Tick the boxes you verified.",
    "    Never mark done on merge alone, and never split or reword a story to close it.",
    STEP_6_RULING_LINES[2],
)

STEP_6_IN_PROGRESS_BODY = (
    "  - **`profile.tracker.states.in_progress`**: an item failed because the delivered work did not meet it.",
    "    Reopen this story per `references/linear.md`, amend the AC with a dated deployment-review note, and hand "
    "the fix to `engineering-workflow`; never file a new bug for it.",
    STEP_6_ROUTING_LINES[2],
    STEP_6_ROUTING_LINES[3],
)


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def lines_of(heading: str) -> list[str]:
    return section(SKILL.read_text(), heading).splitlines()


def block(lines: list[str], first: str, is_next: "re.Pattern[str]") -> tuple[str, ...]:
    """The lines from `first` up to the next line matching `is_next`, blank lines dropped."""
    start = lines.index(first)
    end = next((i for i in range(start + 1, len(lines)) if is_next.match(lines[i])), len(lines))
    return tuple(line for line in lines[start:end] if line.strip())


NUMBERED_ITEM = re.compile(r"^\d+\. ")
STATE_BULLET = re.compile(r"^ {0,2}- ")


def test_step_4_pins_the_pending_owner_ruling_verdict_test_and_record() -> None:
    lines = lines_of(STEP_4)
    for pin in STEP_4_LINES:
        assert pin in lines, f"step 4 is missing the pinned line: {pin}"


def test_step_4_states_the_qualifying_test_before_the_record_and_the_comment() -> None:
    lines = lines_of(STEP_4)
    positions = [lines.index(pin) for pin in STEP_4_LINES]
    assert positions == sorted(positions), "step 4 pending owner ruling lines are out of order"


def test_step_4_items_stay_numbered_one_to_five() -> None:
    numbers = [m.group(1) for m in (re.match(r"^(\d+)\. ", line) for line in lines_of(STEP_4)) if m]
    assert numbers == ["1", "2", "3", "4", "5"], numbers


def test_step_6_pins_the_routing_of_pending_items() -> None:
    lines = lines_of(STEP_6)
    for pin in STEP_6_ROUTING_LINES:
        assert pin in lines, f"step 6 is missing the pinned line: {pin}"


def test_step_6_pending_only_line_sits_in_the_not_finished_bullet() -> None:
    lines = lines_of(STEP_6)
    not_finished = lines.index("- **QA not finished: stay in `profile.tracker.states.in_deployment_review`.**")
    pending_only = lines.index(STEP_6_ROUTING_LINES[0])
    next_bullet = next(i for i in range(not_finished + 1, len(lines)) if lines[i].startswith("- "))
    assert not_finished < pending_only < next_bullet


def test_step_6_mixed_outcome_lines_sit_in_the_in_progress_bullet() -> None:
    lines = lines_of(STEP_6)
    in_progress = next(i for i, l in enumerate(lines) if l.startswith("  - **`profile.tracker.states.in_progress`**"))
    blocked = next(i for i, l in enumerate(lines) if l.startswith("  - **`profile.tracker.states.blocked`**"))
    for pin in STEP_6_ROUTING_LINES[2:]:
        assert in_progress < lines.index(pin) < blocked, f"not in the in_progress bullet: {pin}"


def test_step_6_pins_the_ruling_path_and_the_done_guard() -> None:
    lines = lines_of(STEP_6)
    for pin in STEP_6_RULING_LINES:
        assert pin in lines, f"step 6 is missing the pinned line: {pin}"


def test_step_6_done_guard_sits_in_the_done_bullet() -> None:
    lines = lines_of(STEP_6)
    done = next(i for i, l in enumerate(lines) if l.startswith("  - **`profile.tracker.states.done`**"))
    in_progress = next(i for i, l in enumerate(lines) if l.startswith("  - **`profile.tracker.states.in_progress`**"))
    assert done < lines.index(STEP_6_RULING_LINES[2]) < in_progress


def test_step_4_cross_references_name_the_renumbered_items() -> None:
    lines = lines_of(STEP_4)
    for pin in STEP_4_CROSS_REFERENCE_LINES:
        assert pin in lines, f"step 4 is missing the pinned line: {pin}"


def test_step_4_item_2_body_is_exactly_the_qualifying_test_and_record() -> None:
    assert block(lines_of(STEP_4), STEP_4_ITEM_2_BODY[0], NUMBERED_ITEM) == STEP_4_ITEM_2_BODY


def test_step_6_done_bullet_body_is_exact() -> None:
    assert block(lines_of(STEP_6), STEP_6_DONE_BODY[0], STATE_BULLET) == STEP_6_DONE_BODY


def test_step_6_in_progress_bullet_body_is_exact() -> None:
    assert block(lines_of(STEP_6), STEP_6_IN_PROGRESS_BODY[0], STATE_BULLET) == STEP_6_IN_PROGRESS_BODY
