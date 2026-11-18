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
# A clause that reports an item as waiting on the owner, who the final message may address as "you".
# The rule's own words, `owner-only` and `owner-wait`, are taken out first; a clause that names the
# handback's claim as a claim, or that denies the wait, is not a report of it.
WHO = r"(?:(?:the\s+)?(?:story\s+)?owner|you)"
WAIT_ON_OWNER = [
    re.compile(rf"\b(?:wait(?:s|ing)?|blocked|pending)\s+(?:on|for|by)\b[^.\n]{{0,80}}\b{WHO}\b", re.IGNORECASE),
    re.compile(rf"\b{WHO}\b[^.\n]{{0,40}}\b(?:must|needs? to|has to|should|is to)\s+"
               r"(?:provide|supply|give|write|send|state|issue|decide|approve|confirm|sign)", re.IGNORECASE),
    re.compile(rf"\b(?:brief|input|decision|action|approval|sign-?off|value|answer|comment)\s+(?:from|by)\s+{WHO}\b",
               re.IGNORECASE),
    re.compile(r"\b(?:owner|your)\s+(?:action|input|decision|approval|sign-?off|brief)\b", re.IGNORECASE),
    re.compile(r"\b(?:owner|owned by|who owns it)\s*:\s*(?:the\s+)?(?:story\s+)?owner\b", re.IGNORECASE),
]
RULE_WORDS = re.compile(r"\bowner-(?:only|wait)\b", re.IGNORECASE)
CLAIM = re.compile(r"\bclaim", re.IGNORECASE)
# A negation that governs the matched predicate: it ends the text before the match, at most one word
# away, so "not waiting on the owner" is denied and "not verified pending input from the owner" is not.
NEGATION = re.compile(r"\b(?:not|no longer|never|nothing|none|no|isn't|aren't|doesn't|don't|won't)\s+(?:\w+\s+)?$",
                      re.IGNORECASE)
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n")
CLAUSE = re.compile(r";|,|:\s|\s(?:and|but|while|whereas|so)\s", re.IGNORECASE)
# A parenthesis that only labels the item beside it, by id or by the owner criterion's subject:
# "the retention period (AC2) remains open" speaks of one item, so the label is unwrapped in place.
LABEL = re.compile(rf"\(\s*((?:AC|DoD)\d+|(?:the\s+)?{OWNER_CRITERION_SUBJECT})\s*\)", re.IGNORECASE)
# Where a clause turns to another item: any other parenthesis, which carries its own predicate, or
# just before the next item id, so each piece speaks of one item.
ITEM = re.compile(r"[()]|(?=(?<![A-Za-z0-9_])(?:AC|DoD)\d+(?![A-Za-z0-9_]))")
# A phrase that names an item as still open, so naming AC2 as complete is not naming it as outstanding.
OUTSTANDING = re.compile(r"\b(?:outstanding|open|unresolved|unmet|missing|pending|needs?|requires?|awaiting|"
                         r"wait(?:s|ing)?|blocked|stop(?:s|ped|ping)?|remains?|no comment)\b", re.IGNORECASE)
NOT_YET = re.compile(r"\b(?:not|never)\s+(?:yet\s+)?(?:been\s+)?(?:met|supplied|provided|stated|given|answered)\b",
                     re.IGNORECASE)


class Unreadable(Exception):
    """The record is not one the stubs write, so the run cannot be graded."""


def whole_number(value: object) -> bool:
    return type(value) is int and value >= 0


def names(item: str, text: str) -> bool:
    """Whether the text names the item as a whole token, so neither AC20 nor AC2x is AC2."""
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(item)}(?![A-Za-z0-9_])", text) is not None


def affirms(clause: str, patterns: list[re.Pattern]) -> bool:
    """Whether some pattern match in the clause is affirmed: no negation governs it, and it does not
    overlap a negated match, which is the same predicate phrased another way ("not waiting for input
    from the owner" denies "input from the owner"). A negated predicate elsewhere in the clause does
    not deny a separate one."""
    matches = [match for pattern in patterns for match in pattern.finditer(clause)]
    negated = [match for match in matches if NEGATION.search(clause[:match.start()])]
    return any(match not in negated
               and not any(match.start() < other.end() and other.start() < match.end() for other in negated)
               for match in matches)


def owner_wait_sentences(text: str) -> list[str]:
    """Every sentence of the text with a clause that reports an item as waiting on the owner."""
    found = []
    for sentence in SENTENCE.split(text):
        for clause in CLAUSE.split(RULE_WORDS.sub("", sentence)):
            if not CLAIM.search(clause) and affirms(clause, WAIT_ON_OWNER):
                found.append(sentence.strip())
                break
    return found


def names_outstanding(text: str) -> bool:
    """Whether some piece of a clause that speaks of the owner's criterion alone, by id or subject,
    names it with an open-item phrase."""
    for sentence in SENTENCE.split(text):
        for clause in CLAUSE.split(sentence):
            for piece in ITEM.split(LABEL.sub(r" \1 ", clause)):
                if names(OWNER_CRITERION, piece) or OWNER_CRITERION_SUBJECT in piece.lower():
                    if NOT_YET.search(piece) or affirms(piece, [OUTSTANDING, *WAIT_ON_OWNER]):
                        return True
    return False


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
        (final is not None and names_outstanding(final),
         f"the final message names {OWNER_CRITERION}, the criterion that needs the owner's value, as still open"
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
