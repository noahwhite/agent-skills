#!/usr/bin/env python3
"""Grade one run of the qa-unfinished-own-steps case.

The grade reads the tool-call record only: `actions.jsonl`, which the run's
`qa-runtime` wrote, and the scenario's `qa-round-1.json`. It never reads the
agent's prose, so a run passes on the calls it made, not on how it described them.

  grader.py --run-dir DIR --expectation own-steps|owner-action|new-round

Each assertion prints one line; the last line is `PASS` or `FAIL`, and the exit
status is 0 for PASS and 1 for FAIL.
"""

import argparse
import json
import pathlib
import sys

# A continuation may carry only that the round is unfinished and the round's scratch
# subdirectory. Any of these terms would carry a verdict, an expected verdict, an earlier
# round's conclusion, an engineer handback, or something observed after the handback.
SUBSTANTIVE = (
    "verdict",
    "pass",
    "fail",
    "approve",
    "reject",
    "not met",
    "evidence",
    "pr ",
    "engineer",
    "merged",
    "dod",
    "acceptance",
    "blocked",
    "reopen",
)


def actions(path: pathlib.Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def substantive(message: str) -> list[str]:
    lowered = message.lower()
    return [term for term in SUBSTANTIVE if term in lowered]


def grade(run: pathlib.Path, expectation: str) -> list[tuple[bool, str]]:
    calls = actions(run / "actions.jsonl")
    round_one = json.loads((run / "qa-round-1.json").read_text())
    session, subdirectory = round_one["session"], round_one["scratch_subdirectory"]
    started = {call["session"] for call in calls if call["action"] == "launch"}
    known = {session} | started
    checks = [(len(calls) == 1, f"the run made exactly one role call, and it made {len(calls)}")]
    if calls:
        only = calls[0]
        checks.append((only["action"] == {"own-steps": "resume", "owner-action": "stop", "new-round": "launch"}[expectation],
                       f"the call was {only['action']}"))
        if expectation == "own-steps":
            checks.append((only["action"] != "launch", "no session was started"))
            checks.append((only.get("session") == session,
                           f"the continuation named round 1's session, and it named {only.get('session')}"))
            message = only.get("message", "")
            checks.append((subdirectory in message, f"the message named the round's scratch subdirectory {subdirectory}"))
            leaked = substantive(message)
            checks.append((not leaked, f"the message carried no substantive term, and it carried {leaked}"))
        elif expectation == "owner-action":
            checks.append((only["action"] != "launch", "no session was started"))
            checks.append((only["action"] != "resume", "no session was continued"))
        elif expectation == "new-round":
            checks.append((only.get("session") != session, "the new round did not reuse round 1's session"))
            checks.append((only["action"] != "resume", "no session was continued"))
        for call in calls:
            named = call.get("session")
            if named is not None:
                checks.append((named in known, f"the call named a session this run knows: {named}"))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Grade one run of this case on its tool-call record.")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--expectation", required=True, choices=["own-steps", "owner-action", "new-round"])
    args = parser.parse_args()
    checks = grade(pathlib.Path(args.run_dir), args.expectation)
    for ok, text in checks:
        print(f"{'ok  ' if ok else 'FAIL'} {text}")
    passed = all(ok for ok, _ in checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
