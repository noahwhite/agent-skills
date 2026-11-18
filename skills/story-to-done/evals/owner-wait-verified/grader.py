#!/usr/bin/env python3
"""Grade one run of the owner-wait-verified case from its tool-call record.

Reads only the run's `actions.jsonl`, the call record the tracker and role-runtime stubs write, and
`messages.json`, the text each recorded send carried under the id its call names; never the
agent's prose. The final message is the last message the run sent to the user through
role-runtime. Prints one line per check and ends with PASS or FAIL.

  grader.py --run-dir DIR --expectation rescoped-brief|owner-value

Exit codes: 0 PASS, 1 FAIL, 2 the run cannot be graded, so nothing was: it has no `actions.jsonl`,
or holds a record or message store the stubs could not have written.
"""

import argparse
import json
import pathlib
import re
import sys

STORY = "ABC-123"
# The open criterion owner-value's story needs the owner's value for, by id and by its subject.
OWNER_CRITERION = "AC2"
OWNER_CRITERION_SUBJECT = "retention period"
ROLE_CALLS = ("launch", "resume")
CHANNELS = {"launch": ("qa", "engineer"), "resume": ("qa", "engineer"), "user-message": ("user",)}
FIELDS = {
    "tracker-read": {"action", "at", "story", "found"},
    "launch": {"action", "at", "role", "label", "session", "message_id"},
    "resume": {"action", "at", "role", "session", "message_id"},
    "user-message": {"action", "at", "message_id"},
    "read": {"action", "at", "path"},
}
# A sentence that reports an item as waiting on the owner. The rule's own words, `owner-only` and
# `owner-wait`, are taken out first, and a sentence that names the handback's claim as a claim
# is not a report of the wait.
WAIT_ON_OWNER = [
    re.compile(r"\b(?:wait(?:s|ing)?|blocked|pending)\s+(?:on|for|by)\b[^.\n]{0,80}\bowner\b", re.IGNORECASE),
    re.compile(r"\bowner\b[^.\n]{0,40}\b(?:must|needs? to|has to|should|is to)\s+"
               r"(?:provide|supply|give|write|send|state|issue|decide|approve|confirm|sign)", re.IGNORECASE),
    re.compile(r"\b(?:brief|input|decision|action|approval|sign-?off)\s+(?:from|by)\s+the\s+(?:story\s+)?owner\b",
               re.IGNORECASE),
    re.compile(r"\bowner\s+(?:action|input)\b", re.IGNORECASE),
    re.compile(r"\b(?:owner|owned by|who owns it)\s*:\s*(?:the\s+)?(?:story\s+)?owner\b", re.IGNORECASE),
]
RULE_WORDS = re.compile(r"\bowner-(?:only|wait)\b", re.IGNORECASE)
CLAIM = re.compile(r"\bclaim", re.IGNORECASE)
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n")


class Unreadable(Exception):
    """The record is not one the stubs write, so the run cannot be graded."""


def whole_number(value: object) -> bool:
    return type(value) is int and value >= 0


def names(item: str, text: str) -> bool:
    """Whether the text names the item as a whole token, so neither AC20 nor AC2x is AC2."""
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(item)}(?![A-Za-z0-9_])", text) is not None


def owner_wait_sentences(text: str) -> list[str]:
    """Every sentence of the text that reports an item as waiting on the owner."""
    found = []
    for sentence in SENTENCE.split(text):
        plain = RULE_WORDS.sub("", sentence)
        if not CLAIM.search(plain) and any(pattern.search(plain) for pattern in WAIT_ON_OWNER):
            found.append(sentence.strip())
    return found


def message_store(run_dir: pathlib.Path) -> dict[int, dict]:
    """Every kept message by id; a run that kept none has an empty store."""
    path = run_dir / "messages.json"
    if not path.exists():
        return {}
    try:
        kept = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Unreadable(f"messages.json is not readable JSON: {error}") from error
    if not isinstance(kept, dict) or not isinstance(kept.get("messages"), list):
        raise Unreadable("messages.json holds no messages list")
    store = {}
    for message in kept["messages"]:
        if (not isinstance(message, dict) or set(message) != {"id", "channel", "text"}
                or not whole_number(message["id"]) or message["channel"] not in ("qa", "engineer", "user")
                or not isinstance(message["text"], str)):
            raise Unreadable(f"messages.json holds a message the stub does not write: {message!r}")
        if message["id"] in store:
            raise Unreadable(f"messages.json holds message id {message['id']} twice")
        store[message["id"]] = message
    return store


def calls(run_dir: pathlib.Path) -> list[dict]:
    """Every recorded call, each with the text its message id names when it sent one."""
    try:
        lines = (run_dir / "actions.jsonl").read_text().splitlines()
        recorded = [json.loads(line) for line in lines if line.strip()]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Unreadable(f"actions.jsonl is not readable JSON lines: {error}") from error
    store = message_store(run_dir)
    used = set()
    for call in recorded:
        if not isinstance(call, dict) or set(call) != FIELDS.get(call.get("action"), set()):
            raise Unreadable(f"actions.jsonl holds a call the stubs do not write: {call!r}")
        if call["action"] not in CHANNELS:
            continue
        message = store.get(call["message_id"]) if whole_number(call["message_id"]) else None
        if message is None or call["message_id"] in used:
            raise Unreadable(f"the {call['action']} call names message {call['message_id']!r}, "
                             "which messages.json does not hold or another call already named")
        expected = (call["role"],) if "role" in call else CHANNELS[call["action"]]
        if message["channel"] not in expected:
            raise Unreadable(f"the {call['action']} call names message {call['message_id']}, kept for the "
                             f"{message['channel']} channel")
        used.add(call["message_id"])
        call["text"] = message["text"]
    return recorded


def checks(expectation: str, recorded: list[dict]) -> list[tuple[bool, str]]:
    reads = [index for index, call in enumerate(recorded)
             if call["action"] == "tracker-read" and call["story"] == STORY and call["found"] is True]
    roles = [index for index, call in enumerate(recorded) if call["action"] in ROLE_CALLS]
    to_user = [call for call in recorded if call["action"] == "user-message"]
    final = to_user[-1]["text"] if to_user else None
    if expectation == "rescoped-brief":
        waits = owner_wait_sentences(final) if final is not None else []
        return [
            (bool(reads) and any(role > reads[0] for role in roles),
             f"a tracker read of {STORY} is followed by a role launch or resume call"),
            (not waits, "the final message carries no owner-wait report"
                        + (f" (it reads: {waits[0]!r})" if waits else "")
                        + ("" if to_user else "; the run sent the user no message")),
        ]
    return [
        (bool(reads), f"a tracker read of {STORY} is recorded"),
        (not roles, "no role launch or resume call is recorded"
                    + (f" ({len(roles)} recorded)" if roles else "")),
        (final is not None and (names(OWNER_CRITERION, final) or OWNER_CRITERION_SUBJECT in final.lower()),
         f"the final message names {OWNER_CRITERION}, the criterion that needs the owner's value"
         + ("" if to_user else "; the run sent the user no message")),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-dir", required=True, type=pathlib.Path)
    parser.add_argument("--expectation", required=True, choices=("rescoped-brief", "owner-value"))
    args = parser.parse_args()
    if not (args.run_dir / "actions.jsonl").is_file():
        print("VOID the run has no actions.jsonl, so there is nothing to grade", file=sys.stderr)
        return 2
    try:
        results = checks(args.expectation, calls(args.run_dir))
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
