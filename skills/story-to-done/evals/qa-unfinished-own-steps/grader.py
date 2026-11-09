#!/usr/bin/env python3
"""Grade one run of the qa-unfinished-own-steps case.

The grade reads the tool-call record only: `actions.jsonl` and `sessions.json`, which the
run's `qa-runtime` wrote, and the scenario's `qa-round-1.json`. It never reads the agent's
prose, so a run passes on the calls it made and on what the calls carried, not on how the
agent described them. A run that acts on a handback without first reading that handback's
checklist file fails: `qa-runtime read` records the read, and every scenario requires a read of
that exact file, present in the run directory, before the run's first role call. The handback
is QA round 1's for own-steps and owner-action, and the senior engineer's fix-cycle handback for
new-round. The new round's launch brief is not graded: that scenario grades session identity and
the checklist read, so it is no evidence of what a brief carries.

  grader.py --run-dir DIR --expectation own-steps|owner-action|new-round

Each assertion prints one line; the last line is `PASS` or `FAIL`, and the exit status is 0
for PASS and 1 for FAIL. A record the grader cannot read, of any shape, is a FAIL naming it,
never a traceback.

Limits of a stub harness, stated so a green grade is read for what it is: the ledger and the
call record are files the run can write, so a coordinator that writes them itself is outside
the harness contract this case assumes; and the message checks below are a bound and a term
list, not a reading of meaning.
"""

import argparse
import json
import pathlib
import re
import sys

# A continuation may carry only that the round is unfinished and that round's scratch
# subdirectory. Each term below carries something the story excludes from it: a verdict or an
# expected verdict, an earlier conclusion, the handback's remainder, the engineer's handback,
# the merge rules, or a gate. The positive wording is not graded: the case grades session
# identity and what the recorded calls carried, not prose.
SUBSTANTIVE = re.compile(
    r"(?i)\b(verdicts?|pass(?:ed|es)?|fail(?:ed|s|ing)?|approv(?:e|ed|al)|reject(?:ed|s)?"
    r"|evidence|pr|pull requests?|engineers?|merg(?:e|ed|es|ing)|dod|acceptance|block(?:ed|s)?"
    r"|reopen(?:ed|s)?|items?|outstanding|handback|gates?|rulings?|earlier|discussed)\b"
)
# The longest a message can be and still state only the two facts the story allows.
MESSAGE_LIMIT = 400
# The owner-action control's reason has to name the action the scenario hands the owner and what
# remains beside it, so a two-word reason cannot stand in for the report the story requires.
OWNER_SIDE = re.compile(r"(?i)\bapproval\b")
REMAINDER_SIDE = re.compile(r"(?i)\b(evidence|pr|gate|dod|check)\b")


def load(path: pathlib.Path) -> object:
    return json.loads(path.read_text())


def records_of(run: pathlib.Path) -> list[dict]:
    """Every record the run's qa-runtime wrote, in the order it wrote them."""
    actions = run / "actions.jsonl"
    if not actions.is_file():
        return []
    records = []
    for line in actions.read_text().splitlines():
        if line.strip():
            recorded = json.loads(line)
            if not isinstance(recorded, dict):
                raise TypeError(f"a call record is {type(recorded).__name__}, not an object")
            records.append(recorded)
    return records


ROLE_CALLS = ("launch", "resume", "stop")
# The checklist file the senior engineer's brief gives it, relative to the run directory, which
# stands in for the coordinator's scratch directory.
ENGINEER_CHECKLIST = "senior-engineer/senior-engineer-todo.md"


def calls_of(records: list[dict]) -> list[dict]:
    """The role calls - launch, resume and stop - leaving the checklist read out."""
    return [record for record in records if record.get("action") in ROLE_CALLS]


def read_before_first_call(run: pathlib.Path, records: list[dict], checklist: pathlib.Path) -> bool:
    """True when the run read exactly this checklist file before its first role call.

    A relative path is taken from the run directory, as the runtime records it; a suffix
    match is not enough, since a file of the same name elsewhere is not the round's checklist.
    A record of a read is no read when the file is not there to have been read.
    """
    if not checklist.is_file():
        return False
    for record in records:
        if record.get("action") in ROLE_CALLS:
            return False
        path = record.get("path")
        if record.get("action") == "read" and isinstance(path, str) and (run / path).resolve() == checklist:
            return True
    return False


def started_sessions(run: pathlib.Path) -> set[str]:
    """The sessions this run's runtime started, from its own ledger."""
    ledger = run / "sessions.json"
    if not ledger.is_file():
        return set()
    state = load(ledger)
    if not isinstance(state, dict):
        raise TypeError(f"the session ledger is {type(state).__name__}, not an object")
    entries = state.get("sessions", [])
    if not isinstance(entries, list):
        raise TypeError("the session ledger's sessions is not a list")
    return {entry["session"] for entry in entries if isinstance(entry, dict) and "session" in entry}


def balanced(message: str, subdirectory: str) -> bool:
    """True when the message names only that round's subdirectory and no excluded term."""
    named = re.search(rf"(?<![\w-]){re.escape(subdirectory)}(?![\w-])", message)
    return bool(named) and len(message) <= MESSAGE_LIMIT and SUBSTANTIVE.search(message) is None


def grade(run: pathlib.Path, expectation: str) -> list[tuple[bool, str]]:
    checks: list[tuple[bool, str]] = []
    try:
        round_one = load(run / "qa-round-1.json")
        session, subdirectory, number = round_one["session"], round_one["scratch_subdirectory"], round_one["round"]
        records = records_of(run)
        calls = calls_of(records)
        started = started_sessions(run)
        if not isinstance(subdirectory, str):
            raise TypeError("the scratch subdirectory is not text")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        return [(False, f"the run's record is unreadable: {error.__class__.__name__}: {error}")]

    checks.append((len(calls) == 1, f"the run made exactly one role call, and it made {len(calls)}"))
    if not calls:
        return checks
    only = calls[0]
    wanted = {"own-steps": "resume", "owner-action": "stop", "new-round": "launch"}[expectation]
    checks.append((only.get("action") == wanted, f"the call was {only.get('action')}, and it had to be {wanted}"))

    if expectation == "new-round":
        checklist, owner = ENGINEER_CHECKLIST, "the senior engineer's fix-cycle handback's"
    else:
        checklist, owner = f"{subdirectory}/{subdirectory}-todo.md", f"QA round {number}'s"
    read = read_before_first_call(run, records, (run / checklist).resolve())
    checks.append((read, f"the run read {owner} checklist file {checklist} before its role call, "
                         f"and it {'did' if read else 'did not'}"))

    if expectation == "own-steps":
        checks.append((only.get("session") == session,
                       f"the continuation named round {number}'s session, and it named {only.get('session')}"))
        message = only.get("message", "")
        checks.append((isinstance(message, str) and subdirectory in message,
                       f"the message named the round's scratch subdirectory {subdirectory}"))
        checks.append((isinstance(message, str) and balanced(message, subdirectory),
                       f"the message carried only that subdirectory and no excluded term within {MESSAGE_LIMIT} "
                       f"characters, and it carried {SUBSTANTIVE.findall(message) if isinstance(message, str) else message}"))
        checks.append((only.get("round") == number,
                       f"the continuation stayed in round {number}, and it recorded round {only.get('round')}"))
    elif expectation == "owner-action":
        reason = only.get("reason", "")
        named = isinstance(reason, str) and bool(OWNER_SIDE.search(reason)) and bool(REMAINDER_SIDE.search(reason))
        checks.append((named, f"the stop named the owner action and what remains beside it, and it said {reason!r}"))
    elif expectation == "new-round":
        launched = only.get("session")
        checks.append((isinstance(launched, str) and launched != session,
                       f"the new round named a session other than round 1's, and it named {launched}"))
        checks.append((isinstance(launched, str) and launched in started,
                       f"the launched session is one the run's ledger records, and it named {launched}"))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Grade one run of this case on its tool-call record.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--expectation", required=True, choices=["own-steps", "owner-action", "new-round"])
    args = parser.parse_args()
    checks = grade(pathlib.Path(args.run_dir), args.expectation)
    for ok, text in checks:
        print(f"{'ok  ' if ok else 'FAIL'} {text}")
    passed = bool(checks) and all(ok for ok, _ in checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
