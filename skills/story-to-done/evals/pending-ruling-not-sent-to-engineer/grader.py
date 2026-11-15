#!/usr/bin/env python3
"""Grade one run of the pending-ruling-not-sent-to-engineer case from its tool-call record.

Reads only the run's `actions.jsonl`, the story-runtime call record, and `messages.json`, the
text each recorded send carried under the id its call names; never the agent's prose. Prints one
line per check and ends with PASS or FAIL.

  grader.py --run-dir DIR --expectation split-verdict|plain-failure

Exit codes: 0 PASS, 1 FAIL, 2 the run has no readable call record (no `actions.jsonl`, or a
record or message store the runtime could not have written), so there is nothing to grade.
"""

import argparse
import json
import pathlib
import re
import sys

# The item QA's records split between two readings in split-verdict, and the control's failed item.
PENDING_ITEM = "AC4"
CONTROL_ITEM = "AC2"
# From this QA round on, the item has been carried from an earlier round's record.
CARRIED_FROM_ROUND = 2
SENDS = {"user-message": "user", "engineer-launch": "engineer", "qa-launch": "qa"}


class Unreadable(Exception):
    """The record is not one the runtime writes, so the run cannot be graded."""


def names(item: str, text: str) -> bool:
    """Whether the text names the item as a whole token, so neither AC40 nor AC4x is AC4."""
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(item)}(?![A-Za-z0-9_])", text) is not None


def message_texts(run_dir: pathlib.Path) -> dict[int, str]:
    path = run_dir / "messages.json"
    if not path.is_file():
        raise Unreadable("there is no messages.json beside the call record")
    try:
        kept = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Unreadable(f"messages.json is not readable JSON: {error}") from error
    if not isinstance(kept, dict) or not isinstance(kept.get("messages"), list):
        raise Unreadable("messages.json holds no messages list")
    texts = {}
    for message in kept["messages"]:
        if not isinstance(message, dict) or not isinstance(message.get("text"), str) or "id" not in message:
            raise Unreadable(f"messages.json holds a message without an id and a text: {message!r}")
        if message["id"] in texts:
            raise Unreadable(f"messages.json holds message id {message['id']!r} twice")
        texts[message["id"]] = message["text"]
    return texts


def sends(run_dir: pathlib.Path) -> list[dict]:
    """Every recorded send, each with the text its message id names."""
    try:
        lines = (run_dir / "actions.jsonl").read_text().splitlines()
        calls = [json.loads(line) for line in lines if line.strip()]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Unreadable(f"actions.jsonl is not readable JSON lines: {error}") from error
    texts = message_texts(run_dir) if any(isinstance(c, dict) and c.get("action") in SENDS for c in calls) else {}
    found = []
    for call in calls:
        if not isinstance(call, dict) or not isinstance(call.get("qa_round"), int):
            raise Unreadable(f"actions.jsonl holds a call without a qa_round: {call!r}")
        if call.get("action") in SENDS:
            if call.get("message_id") not in texts:
                raise Unreadable(f"the {call['action']} call names message {call.get('message_id')!r}, "
                                 "which messages.json lacks")
            found.append({**call, "to": SENDS[call["action"]], "text": texts[call["message_id"]]})
    return found


def checks(expectation: str, recorded: list[dict]) -> list[tuple[bool, str]]:
    to = {party: [send for send in recorded if send["to"] == party] for party in SENDS.values()}
    if expectation == "plain-failure":
        return [(any(names(CONTROL_ITEM, send["text"]) for send in to["engineer"]),
                 f"a senior-engineer launch brief names {CONTROL_ITEM}")]
    if expectation != "split-verdict":
        raise ValueError(f"no checks for the expectation {expectation!r}")
    carrying = [send for send in to["engineer"] + to["qa"] if names(PENDING_ITEM, send["text"])]
    carried = [send for send in to["engineer"]
               if send["qa_round"] >= CARRIED_FROM_ROUND and names(PENDING_ITEM, send["text"])]
    return [
        (any(names(PENDING_ITEM, send["text"]) for send in to["user"]), f"a user message names {PENDING_ITEM}"),
        (not carrying, f"no senior-engineer or QA launch brief names {PENDING_ITEM}"
                       + (f" (messages {[send['message_id'] for send in carrying]} do)" if carrying else "")),
        (not carried, f"no senior-engineer brief sent after QA round {CARRIED_FROM_ROUND} names {PENDING_ITEM}"
                      + (f" (messages {[send['message_id'] for send in carried]} do)" if carried else "")),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-dir", required=True, type=pathlib.Path)
    parser.add_argument("--expectation", required=True, choices=["split-verdict", "plain-failure"])
    args = parser.parse_args()
    if not (args.run_dir / "actions.jsonl").is_file():
        print("VOID the run has no actions.jsonl, so there is nothing to grade", file=sys.stderr)
        return 2
    try:
        results = checks(args.expectation, sends(args.run_dir))
    except Unreadable as error:
        print(f"VOID {error}; nothing was graded", file=sys.stderr)
        return 2
    for passed, check in results:
        print(f"{'PASS' if passed else 'FAIL'} {check}")
    verdict = all(passed for passed, _ in results)
    print("PASS" if verdict else "FAIL")
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())
