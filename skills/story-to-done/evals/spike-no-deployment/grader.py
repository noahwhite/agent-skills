#!/usr/bin/env python3
"""Grade one run of the spike-no-deployment case from its tool-call record.

Reads only the run's `actions.jsonl`, the story-runtime call record, `messages.json`, the text
each recorded send carried under the id its call names, and the coordinator's checklist file,
`workspace/coordinator-todo.md`; never the agent's prose. Prints one line per check and ends with
PASS or FAIL.

  grader.py --run-dir DIR --expectation EXPECTATION

EXPECTATION is a scenario name, or deployed-path, the deployed scenario's path grade.

Exit codes: 0 PASS, 1 FAIL, 2 the run cannot be graded, so nothing was: it has no `actions.jsonl`,
or holds a record or message store the runtime could not have written.
"""

import argparse
import json
import pathlib
import re
import sys

# The handback each scenario's story.json serves to its first senior-engineer launch, if any.
SERVES = {"spike": "engineer-handback.md", "no-deployment": "engineer-handback.md",
          "deployed": "engineer-handback.md", "conflict": None, "direct-entry": None}
# The path each expectation is graded on, in the briefs and in the coordinator's checklist.
PATHS = {"spike": "spike", "no-deployment": "no-deployment", "deployed-path": "deployed",
         "direct-entry": "no-deployment", "conflict": "unresolved"}
EXPECTATIONS = ["conflict", "deployed", "deployed-path", "direct-entry", "no-deployment", "spike"]
# The environment the deployed scenario's handback names, and the commit direct-entry's step 12 note names.
ENVIRONMENT = "dev"
MERGED_COMMIT = "4e1c2a9b7d3f5e6a8c0b1d2e3f4a5b6c7d8e9f01"
CHECKLIST = "workspace/coordinator-todo.md"
SENDS = {"user-message": "user", "engineer-launch": "engineer", "qa-launch": "qa"}
ACTIONS = {*SENDS, "tracker-read", "read"}
FIELDS = {"action", "at", "message_id", "label", "path", "served"}
PATH_LINE = re.compile(r"path:\s*(\S+)")


class Unreadable(Exception):
    """The record is not one the runtime writes, so the run cannot be graded."""


def whole_number(value: object) -> bool:
    return type(value) is int and value >= 0


def scenario_of(expectation: str) -> str:
    return "deployed" if expectation == "deployed-path" else expectation


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
        if (not isinstance(message, dict) or set(message) != {"id", "channel", "label", "text"}
                or not whole_number(message["id"]) or message["channel"] not in SENDS.values()
                or not isinstance(message["text"], str) or not isinstance(message["label"], (str, type(None)))):
            raise Unreadable(f"messages.json holds a message the runtime does not write: {message!r}")
        if message["id"] in store:
            raise Unreadable(f"messages.json holds message id {message['id']} twice")
        store[message["id"]] = message
    return store


def calls(run_dir: pathlib.Path) -> list[dict]:
    try:
        lines = (run_dir / "actions.jsonl").read_text().splitlines()
        recorded = [json.loads(line) for line in lines if line.strip()]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Unreadable(f"actions.jsonl is not readable JSON lines: {error}") from error
    for call in recorded:
        if (not isinstance(call, dict) or not set(call) <= FIELDS or not isinstance(call.get("action"), str)
                or call["action"] not in ACTIONS):
            raise Unreadable(f"actions.jsonl holds a call the runtime does not write: {call!r}")
    return recorded


def sends(run_dir: pathlib.Path, scenario: str) -> list[dict]:
    """Every recorded send, in order, with the text its message id names, after checking the calls
    are a sequence the runtime writes: no two sends name one message, and only the first
    senior-engineer launch of a scenario with a handback is served it."""
    store = message_store(run_dir)
    found, served = [], 0
    for call in calls(run_dir):
        if "served" in call:
            if call["action"] != "engineer-launch" or served or call["served"] != SERVES[scenario]:
                raise Unreadable(f"a {call['action']} call serves {call['served']!r}, which the {scenario} "
                                 "scenario does not serve then")
            served += 1
        elif call["action"] == "engineer-launch" and SERVES[scenario] and not served:
            raise Unreadable(f"the first senior-engineer launch of {scenario} was not served its handback")
        if call["action"] not in SENDS:
            continue
        message_id = call.get("message_id")
        message = store.pop(message_id, None) if whole_number(message_id) else None
        if message is None:
            raise Unreadable(f"the {call['action']} call names message {message_id!r}, "
                             "which messages.json does not hold or another call already named")
        if message["channel"] != SENDS[call["action"]]:
            raise Unreadable(f"the {call['action']} call names message {message_id}, kept for the "
                             f"{message['channel']} channel")
        found.append({**call, "to": SENDS[call["action"]], "text": message["text"], "after_handback": served > 0})
    return found


def brief_paths(text: str) -> list[str]:
    """The values of the brief's path lines: a line whose whole text, trimmed, is `path: <value>`."""
    return [match.group(1) for line in text.splitlines() if (match := PATH_LINE.fullmatch(line.strip()))]


def checklist_paths(run_dir: pathlib.Path) -> list[str] | None:
    """The values of the checklist's path lines, lenient about list markers, check boxes and
    emphasis; None when the run left no readable checklist."""
    try:
        text = (run_dir / CHECKLIST).read_text()
    except (OSError, UnicodeDecodeError):
        return None
    found = []
    for line in text.splitlines():
        line = re.sub(r"[`*_]", "", line).strip()
        line = re.sub(r"^(?:[-+]\s+)?(?:\[[ xX]\]\s*)?", "", line).strip().rstrip(".")
        if match := PATH_LINE.fullmatch(line):
            found.append(match.group(1))
    return found


def names_merged_commit(text: str) -> bool:
    """Whether the text names the merged commit, in full or by a prefix of at least 7 characters."""
    return any(MERGED_COMMIT.startswith(token.lower())
               for token in re.findall(r"(?<![0-9A-Za-z])[0-9a-fA-F]{7,40}(?![0-9A-Za-z])", text))


def path_checks(run_dir: pathlib.Path, path: str, briefs: list[dict]) -> list[tuple[bool, str]]:
    results = []
    for brief in briefs:
        found = brief_paths(brief["text"])
        results.append((found == [path], f"the {brief['to']} brief, message {brief['message_id']}, carries exactly "
                                         f"one path line, `path: {path}`" + (f" (it carries {found})" if found != [path] else "")))
    listed = checklist_paths(run_dir)
    passed = listed is not None and set(listed) == {path}
    results.append((passed, f"the coordinator checklist carries the line `path: {path}` and no other path line"
                    + ("" if passed else " (there is no checklist)" if listed is None else f" (it carries {listed})")))
    return results


def checks(expectation: str, run_dir: pathlib.Path, sent: list[dict]) -> list[tuple[bool, str]]:
    to = {party: [send for send in sent if send["to"] == party] for party in SENDS.values()}
    engineer, qa = to["engineer"], to["qa"]
    if expectation == "conflict":
        return [(bool(to["user"]), "a message went to the user"),
                (not engineer and not qa, "no senior-engineer or QA session was started"
                 + (f" ({len(engineer)} senior-engineer, {len(qa)} QA)" if engineer or qa else "")),
                *path_checks(run_dir, PATHS[expectation], [])]
    if expectation == "direct-entry":
        return [(not engineer, "no senior-engineer session was started"),
                (bool(qa), "a QA session was started"),
                *[(names_merged_commit(brief["text"]), f"the QA brief, message {brief['message_id']}, names the merged "
                                                        f"commit {MERGED_COMMIT[:7]}") for brief in qa],
                *path_checks(run_dir, PATHS[expectation], qa)]
    after = [brief for brief in qa if brief["after_handback"]]
    results = [(bool(engineer), "a senior-engineer session was started"),
               (bool(after) and len(after) == len(qa), "a QA session was started, and only after the senior engineer handed back")]
    if expectation in ("deployed", "deployed-path"):
        results += [(re.search(rf"(?<![A-Za-z0-9_-]){ENVIRONMENT}(?![A-Za-z0-9_-])", brief["text"]) is not None,
                     f"the QA brief, message {brief['message_id']}, names the environment {ENVIRONMENT}") for brief in qa]
    if expectation == "deployed":
        return results
    return results + path_checks(run_dir, PATHS[expectation], engineer + qa)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-dir", required=True, type=pathlib.Path)
    parser.add_argument("--expectation", required=True, choices=EXPECTATIONS)
    args = parser.parse_args()
    if not (args.run_dir / "actions.jsonl").is_file():
        print("VOID the run has no actions.jsonl, so there is nothing to grade", file=sys.stderr)
        return 2
    try:
        results = checks(args.expectation, args.run_dir, sends(args.run_dir, scenario_of(args.expectation)))
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
