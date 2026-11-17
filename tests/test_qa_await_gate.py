"""Pins for the qa-verification await-the-gate rule (SKL-182): step 5 and the todo seed list."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "qa-verification" / "SKILL.md"
TODO = ROOT / "shared" / "todo-tracking.md"
COPIES = sorted((ROOT / "skills").glob("*/references/todo-tracking.md"))

STEP_5 = "5. Check the evidence into the repository"

AWAIT_HEAD = "- **Await the gate.**"
FOREGROUND = (
    "  Launch the reviewer and the adjudicator in the foreground where the runtime supports it, "
    "so each stays awaitable until it exits."
)
BACKGROUNDED = (
    "  A gate command the runtime moves to the background is still running: wait for it to exit "
    "and read its report before the run continues."
)
NO_END_WHILE_OUTSTANDING = (
    "  A run never ends while a gate step it launched is still outstanding, and no stop is lawful "
    "while a gate command it launched is still running, so a closing message that the review or "
    "the adjudication is still running never ends a run."
)
CONSUME = (
    "  Once every gate command has exited, the run reads each report and carries on to the review "
    "of record, the merge guard and the closing decision in step 6."
)
INCOMPLETE_STOP = (
    "  When a gate command exited unsuccessfully or was killed after exceeding a timeout, or the "
    "gate needs an owner action or an access grant the run cannot supply itself, the run stops and "
    "reports itself incomplete: it names the unfinished gate step, the reason, and who owns the "
    "next action, and never claims successful completion."
)
AWAIT_BODY = (AWAIT_HEAD, FOREGROUND, BACKGROUNDED, NO_END_WHILE_OUTSTANDING, CONSUME, INCOMPLETE_STOP)

SEED_GATE_ITEMS = (
    "each gate step of the evidence PR as its own item (the reviewer, the adjudicator, the posted "
    "review of record, the merge guard and the merge)"
)
SEED_NOT_FINISHED = "A round is not finished while any gate item is unticked."


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def step_5_lines() -> list[str]:
    return section(SKILL.read_text(), STEP_5).splitlines()


def qa_seed(text: str) -> str:
    seed = [line for line in section(text, "Seed lists").splitlines() if line.startswith("- **qa-verification:**")]
    assert len(seed) == 1, seed
    return seed[0]


def test_step_5_launches_the_gate_in_the_foreground() -> None:
    assert FOREGROUND in step_5_lines()


def test_step_5_waits_for_a_backgrounded_gate_command_and_reads_its_report() -> None:
    assert BACKGROUNDED in step_5_lines()


def test_step_5_forbids_ending_while_a_gate_step_is_outstanding() -> None:
    assert NO_END_WHILE_OUTSTANDING in step_5_lines()


def test_step_5_consumes_each_report_and_carries_on_to_the_close() -> None:
    assert CONSUME in step_5_lines()


def test_step_5_stops_incomplete_once_the_gate_cannot_finish() -> None:
    assert INCOMPLETE_STOP in step_5_lines()


def test_step_5_await_bullet_body_is_exact_and_ordered() -> None:
    lines = step_5_lines()
    start = lines.index(AWAIT_HEAD)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("- ")), len(lines))
    assert tuple(line for line in lines[start:end] if line.strip()) == AWAIT_BODY


def test_await_bullet_precedes_the_merge_bullet() -> None:
    lines = step_5_lines()
    merge = next(i for i, line in enumerate(lines) if line.startswith("- Merge only on the exact final head"))
    assert lines.index(AWAIT_HEAD) < merge


def test_qa_seed_makes_each_gate_step_its_own_item() -> None:
    assert SEED_GATE_ITEMS in qa_seed(TODO.read_text())


def test_qa_seed_states_a_round_is_not_finished_with_a_gate_item_unticked() -> None:
    assert SEED_NOT_FINISHED in qa_seed(TODO.read_text())


def test_every_vendored_todo_copy_carries_the_qa_gate_seed() -> None:
    assert COPIES
    for copy in COPIES:
        seed = qa_seed(copy.read_text())
        assert SEED_GATE_ITEMS in seed, copy
        assert SEED_NOT_FINISHED in seed, copy
