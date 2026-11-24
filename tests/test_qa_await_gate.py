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
GATE_COMMANDS = (
    "  These two launches are the gate commands; shadow adjudicators and optional reviewers stay "
    "non-blocking, as `references/code-review.md` defines."
)
BACKGROUNDED = (
    "  A gate command the runtime moves to the background is still running: wait for it to exit "
    "and read its report before the run continues."
)
BOUNDED_WAIT = (
    "  Launch each gate command with its report going to a named scratch file, and wait by short "
    "foreground checks that each return at once, of the command's exit status and that file (or of "
    "the runtime's completion notification for a background subagent), repeated until the command "
    "exits; a command killed after its timeout has exited and takes the incomplete stop below."
)
NO_END_WHILE_OUTSTANDING = (
    "  A run never ends while a gate step it launched is still outstanding, and no stop is lawful "
    "while a gate command it launched is still running, so a closing message that the review or "
    "the adjudication is still running never ends a run."
)
CONSUME = (
    "  Once every gate command has exited, the run reads each report and carries on to the bullets "
    "below - acting on what the adjudicator rules valid, posting the review of record, the merge guard "
    "and the merge - and then to the closing decision in step 6."
)
INCOMPLETE_STOP = (
    "  When a gate command has exited or could not be launched, and the gate still cannot finish - the command exited "
    "unsuccessfully, was killed after exceeding a timeout, or left a missing or empty report, or the "
    "gate needs an owner action or an access grant the run cannot supply itself - the run stops and "
    "reports itself incomplete with the completion summary's incomplete line: it names the "
    "unfinished gate step, the reason, and who owns the next action, and never claims successful "
    "completion."
)
AWAIT_BODY = (
    AWAIT_HEAD,
    FOREGROUND,
    GATE_COMMANDS,
    BACKGROUNDED,
    BOUNDED_WAIT,
    NO_END_WHILE_OUTSTANDING,
    CONSUME,
    INCOMPLETE_STOP,
)
NEVER_MERGE_HEAD = "- **Never merge the evidence PR before its review of record is complete at the current head.**"
FIX_HEAD = "- Fix what the adjudicator rules valid"
MERGE_HEAD = "- Merge only on the exact final head"

INCOMPLETE_LINE = (
    "A run that stops with a gate step still unfinished (the incomplete stop or a blocked merge in "
    "step 5) opens its report with the incomplete line `QA incomplete: <unfinished gate step> "
    "- <reason> - next action: <owner>`, so it never reads as a finished round."
)

SEED_GATE_ITEMS = (
    "each gate step of the evidence PR as its own item when `profile.qa.evidence_dir` is set (the "
    "reviewer, the adjudicator, the posted review of record, the merge guard and the merge)"
)
SEED_NOT_FINISHED = (
    "When the evidence PR exists, a round is not finished while any gate item is unticked, except "
    "the merge guard and the merge when `profile.review.merge_owner` is `human`, which the run hands "
    "to the owner."
)
SEED_CLOSE = "the closing status decision"


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def step_5_lines() -> list[str]:
    return section(SKILL.read_text(encoding="utf-8"), STEP_5).splitlines()


def qa_seed(text: str) -> str:
    seed = [line for line in section(text, "Seed lists").splitlines() if line.startswith("- **qa-verification:**")]
    assert len(seed) == 1, seed
    return seed[0]


def test_step_5_launches_the_gate_in_the_foreground() -> None:
    assert FOREGROUND in step_5_lines()


def test_step_5_names_the_gate_commands_and_keeps_shadows_non_blocking() -> None:
    assert GATE_COMMANDS in step_5_lines()


def test_step_5_waits_for_a_backgrounded_gate_command_and_reads_its_report() -> None:
    assert BACKGROUNDED in step_5_lines()


def test_step_5_forbids_ending_while_a_gate_step_is_outstanding() -> None:
    assert NO_END_WHILE_OUTSTANDING in step_5_lines()


def test_step_5_bounds_the_wait_with_short_foreground_checks() -> None:
    assert BOUNDED_WAIT in step_5_lines()


def test_step_5_consumes_each_report_and_carries_on_to_the_close() -> None:
    assert CONSUME in step_5_lines()


def test_step_5_stops_incomplete_once_the_gate_cannot_finish() -> None:
    assert INCOMPLETE_STOP in step_5_lines()


def test_step_5_await_bullet_body_is_exact_and_ordered() -> None:
    lines = step_5_lines()
    assert lines.count(AWAIT_HEAD) == 1, "the await bullet must appear exactly once in step 5"
    start = lines.index(AWAIT_HEAD)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("- ")), len(lines))
    assert tuple(line for line in lines[start:end] if line.strip()) == AWAIT_BODY


def test_await_bullet_precedes_the_fix_and_merge_bullets() -> None:
    lines = step_5_lines()
    never_merge = next((i for i, line in enumerate(lines) if line == NEVER_MERGE_HEAD), -1)
    fix = next((i for i, line in enumerate(lines) if line.startswith(FIX_HEAD)), -1)
    merge = next((i for i, line in enumerate(lines) if line.startswith(MERGE_HEAD)), -1)
    assert never_merge != -1, f"step 5 has no bullet {NEVER_MERGE_HEAD!r}"
    assert fix != -1, f"step 5 has no bullet starting {FIX_HEAD!r}"
    assert merge != -1, f"step 5 has no bullet starting {MERGE_HEAD!r}"
    assert never_merge < lines.index(AWAIT_HEAD) < fix < merge


def test_completion_summary_carries_the_incomplete_line() -> None:
    assert INCOMPLETE_LINE in section(SKILL.read_text(encoding="utf-8"), "Completion summary").splitlines()


def test_qa_seed_makes_each_gate_step_its_own_item() -> None:
    assert SEED_GATE_ITEMS in qa_seed(TODO.read_text(encoding="utf-8"))


def test_qa_seed_states_a_round_is_not_finished_with_a_gate_item_unticked() -> None:
    assert SEED_NOT_FINISHED in qa_seed(TODO.read_text(encoding="utf-8"))


def test_qa_seed_lists_the_gate_items_before_the_closing_decision() -> None:
    seed = qa_seed(TODO.read_text(encoding="utf-8"))
    assert SEED_CLOSE in seed
    assert seed.index(SEED_GATE_ITEMS) < seed.index(SEED_CLOSE)


def test_every_vendored_todo_copy_carries_the_qa_gate_seed() -> None:
    assert COPIES
    for copy in COPIES:
        seed = qa_seed(copy.read_text(encoding="utf-8"))
        assert SEED_GATE_ITEMS in seed, copy
        assert SEED_NOT_FINISHED in seed, copy
