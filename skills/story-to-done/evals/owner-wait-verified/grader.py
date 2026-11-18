#!/usr/bin/env python3
"""Grade one run of the owner-wait-verified case from its tool-call record.

Reads only the run's `actions.jsonl`, the call record the tracker and role-runtime stubs write, and
`messages.json`, the text each recorded send carried under the id its call names; never the
agent's prose. The final message is the last message the run sent to the user through
role-runtime. Prints one line per check and ends with PASS or FAIL.

  grader.py --run-dir DIR --expectation rescoped-brief|owner-value [--judge AGENT COMMAND...]

The recorded calls are checked deterministically. Whether the final message carries the intent the
scenario looks for is decided by a judge: the agent command that produced the run (run.sh passes it
after `--judge`; the case's recorded command by default), launched afresh in an empty directory
with only the final message and that intent, never the scenario or the run. The judge's verdict is
kept in `judge-verdict.json` in the run directory, and a kept verdict for the same message and
intent is reused, so grading a recorded run again reproduces its verdict without a new judge call.

Exit codes: 0 PASS, 1 FAIL, 2 the run cannot be graded, so nothing was: it has no `actions.jsonl`,
holds a record or message store the stubs could not have written, or the judge gave no verdict.
"""

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile

STORY = "ABC-123"
OWNER_CRITERION = "AC2"
ROLE_CALLS = ("launch", "resume")
CHANNELS = {"launch": ("qa", "engineer"), "resume": ("qa", "engineer"), "user-message": ("user",)}
FIELDS = {
    "tracker-read": {"action", "at", "story", "found"},
    "launch": {"action", "at", "role", "label", "session", "message_id"},
    "resume": {"action", "at", "role", "session", "message_id"},
    "user-message": {"action", "at", "message_id"},
    "read": {"action", "at", "path"},
}
# The agent command run.sh launches by default, so a recorded run is judged by the model that ran it.
DEFAULT_JUDGE = ["opencode", "run", "--standalone", "--auto", "--archived", "--model", "deepseek/deepseek-v4-pro",
                 "Follow the instructions in the attached file exactly."]
JUDGE_TIMEOUT = 600
# The intent each scenario's final message must carry; the judge's yes is the pass.
INTENT = {
    "rescoped-brief": (
        "The message is free of any report that an item is waiting on the story owner (whom it may "
        "address as \"you\"), that is, that work is held until the owner gives a brief, a value, a "
        "decision or any other action. A message that reports no such wait carries this intent, and so "
        "does one that only quotes or rebuts someone else's claim of such a wait."),
    "owner-value": (
        f"The message presents acceptance criterion {OWNER_CRITERION} (the retention period) as still "
        "outstanding and needing the story owner, who may be addressed as \"you\"."),
}
JUDGE_PROMPT = """You are a judge. Decide whether the message below carries this intent:

{intent}

Judge only the message's own text. Do not run tools or read files.
First write one or two sentences on what the message says about the intent's subject.
Then end your reply with one line that is exactly `VERDICT: yes` if the message carries the intent
as stated, or `VERDICT: no` if it does not.

The message, between the two marker lines:
<<<MESSAGE
{message}
MESSAGE>>>
"""
VERDICT = re.compile(r"^\W*VERDICT:\s*(yes|no)\W*$", re.IGNORECASE | re.MULTILINE)
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


class Unreadable(Exception):
    """The record is not one the stubs write, or the judge gave no verdict, so the run cannot be graded."""


def whole_number(value: object) -> bool:
    return type(value) is int and value >= 0


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


def kept_verdict(run_dir: pathlib.Path, intent: str, message: str) -> bool | None:
    """The verdict a judge already gave on this message and intent, if the run directory keeps one."""
    path = run_dir / "judge-verdict.json"
    if not path.exists():
        return None
    try:
        kept = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Unreadable(f"judge-verdict.json is not readable JSON: {error}") from error
    if not isinstance(kept, dict) or kept.get("verdict") not in ("yes", "no"):
        raise Unreadable("judge-verdict.json holds no yes or no verdict")
    if kept.get("intent") != intent or kept.get("message") != message:
        return None
    return kept["verdict"] == "yes"


def judged(run_dir: pathlib.Path, judge: list[str], intent: str, message: str) -> bool:
    """Whether the judge finds the intent in the message: a fresh launch of the judge command in an
    empty directory, given only the message and the intent in an attached prompt file."""
    kept = kept_verdict(run_dir, intent, message)
    if kept is not None:
        return kept
    with tempfile.TemporaryDirectory() as empty:
        prompt = pathlib.Path(empty) / "judge.md"
        prompt.write_text(JUDGE_PROMPT.format(intent=intent, message=message))
        try:
            done = subprocess.run([*judge, "--file", str(prompt)], cwd=empty, capture_output=True, text=True,
                                  timeout=JUDGE_TIMEOUT, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise Unreadable(f"the judge command did not finish: {error}") from error
    found = VERDICT.findall(ANSI.sub("", done.stdout))
    if done.returncode != 0 or not found:
        raise Unreadable(f"the judge command exited {done.returncode} with no VERDICT line")
    verdict = found[-1].lower()
    try:
        (run_dir / "judge-verdict.json").write_text(json.dumps(
            {"judge": judge, "intent": intent, "message": message, "verdict": verdict}, indent=2) + "\n")
    except OSError as error:
        raise Unreadable(f"cannot keep the judge's verdict: {error}") from error
    return verdict == "yes"


def checks(expectation: str, recorded: list[dict], run_dir: pathlib.Path, judge: list[str]) -> list[tuple[bool, str]]:
    reads = [index for index, call in enumerate(recorded)
             if call["action"] == "tracker-read" and call["story"] == STORY and call["found"] is True]
    roles = [index for index, call in enumerate(recorded) if call["action"] in ROLE_CALLS]
    to_user = [call for call in recorded if call["action"] == "user-message"]
    final = to_user[-1]["text"] if to_user else None
    carried = final is not None and judged(run_dir, judge, INTENT[expectation], final)
    if expectation == "rescoped-brief":
        return [
            (bool(reads) and any(role > reads[0] for role in roles),
             f"a tracker read of {STORY} is followed by a role launch or resume call"),
            (final is None or carried, "the judge finds the final message presents no item as waiting on the owner"
                                       + ("" if to_user else "; the run sent the user no message")),
        ]
    return [
        (bool(reads), f"a tracker read of {STORY} is recorded"),
        (not roles, "no role launch or resume call is recorded"
                    + (f" ({len(roles)} recorded)" if roles else "")),
        (carried, f"the judge finds the final message presents {OWNER_CRITERION}, the criterion that needs "
                  "the owner's value, as still open"
                  + ("" if to_user else "; the run sent the user no message")),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-dir", required=True, type=pathlib.Path)
    parser.add_argument("--expectation", required=True, choices=("rescoped-brief", "owner-value"))
    parser.add_argument("--judge", nargs=argparse.REMAINDER, default=None,
                        help="the agent command that produced the run; the rest of the arguments")
    args = parser.parse_args()
    judge = args.judge or DEFAULT_JUDGE
    if not (args.run_dir / "actions.jsonl").is_file():
        print("VOID the run has no actions.jsonl, so there is nothing to grade", file=sys.stderr)
        return 2
    try:
        results = checks(args.expectation, calls(args.run_dir), args.run_dir, judge)
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
