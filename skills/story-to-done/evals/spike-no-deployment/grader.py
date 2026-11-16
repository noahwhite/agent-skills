#!/usr/bin/env python3
"""Grade one run of the spike-no-deployment case from its tool-call record.

Reads only the run's `actions.jsonl`, the story-runtime call record, `messages.json`, the text
each recorded send carried under the id its call names, `selector.jsonl`, the record of each run
of the path selector, and the coordinator's checklist file, `workspace/coordinator-todo.md`; never
the agent's prose. Prints one line per check and ends with PASS or FAIL.

  grader.py --run-dir DIR --expectation EXPECTATION

EXPECTATION is a scenario name, or deployed-path, the deployed scenario's path grade. The deployed
grade is the control alone, which both commits must pass; it carries no path check. run.sh always
grades a deployed run as deployed-path too, which adds the selector run and `path: deployed` in
each brief and in the checklist, and the run passes only when both grades pass.

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
# The line the path selector prints for each graded expectation's story and profile.
SELECTED = {"spike": "spike", "no-deployment": "no-deployment", "deployed-path": "deployed",
            "direct-entry": "no-deployment", "conflict": "ask: spike-title-without-label"}
EXPECTATIONS = ["conflict", "deployed", "deployed-path", "direct-entry", "no-deployment", "spike"]
STORY = "ABC-123"
# The environment the deployed scenario's profile and handback name, the commit the no-deployment
# and direct-entry step 12 notes name, and the deliverable the spike's step 12 note links.
ENVIRONMENT = "dev"
MERGED_COMMIT = "4e1c2a9b7d3f5e6a8c0b1d2e3f4a5b6c7d8e9f01"
DELIVERABLE = "https://docs.example.com/abc-123/yaml-parser-comparison"
# The skill each role's brief tells it to load, at both commits.
ROLE_SKILL = {"engineer": "engineering-workflow", "qa": "qa-verification"}
CHECKLIST = "workspace/coordinator-todo.md"
SELECTOR_LOG = "selector.jsonl"
SENDS = {"user-message": "user", "engineer-launch": "engineer", "qa-launch": "qa"}
ACTIONS = {*SENDS, "tracker-read", "read"}
FIELDS = {"action", "at", "message_id", "label", "path", "served"}
PATH_LINE = re.compile(r"path:\s*(\S+)")
FENCE = re.compile(r"(`{3,}|~{3,})")
NEGATION = re.compile(r"\b(?:no|not|none|without|never)\b(?!-)|n't\b", re.IGNORECASE)
# A clause ends at a line break or at punctuation followed by white space, so a URL or a dotted
# name stays inside its clause.
CLAUSE_END = re.compile(r"\n|[.;,!?](?=\s|$)")
# A name inside a URL, a path, an email address or a dotted host name is not named on its own.
BEFORE = r"(?<![A-Za-z0-9_\-/.@])"
AFTER = r"(?![A-Za-z0-9_\-/@]|\.[A-Za-z0-9])"
STAMP = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")


class Unreadable(Exception):
    """The record is not one the runtime writes, so the run cannot be graded."""


def whole_number(value: object) -> bool:
    return type(value) is int and value >= 0


def scenario_of(expectation: str) -> str:
    return "deployed" if expectation == "deployed-path" else expectation


def word(name: str, text: str) -> bool:
    """Whether the text names the name on its own: not inside a longer token, a URL, a path, an
    email address or a dotted host name."""
    return re.search(BEFORE + re.escape(name) + AFTER, text) is not None


def naming_clauses(names, text: str) -> list[str]:
    """The clauses of the text that name it; `names` says whether a clause does."""
    return [clause for clause in CLAUSE_END.split(text) if names(clause)]


def affirms(names, text: str) -> bool:
    """Whether a clause of the text names it and denies nothing."""
    return any(not NEGATION.search(clause) for clause in naming_clauses(names, text))


def affirms_only(names, text: str) -> bool:
    """Whether the text names it and no clause that names it denies anything."""
    named = naming_clauses(names, text)
    return bool(named) and not any(NEGATION.search(clause) for clause in named)


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
    if sorted(store) != list(range(1, len(store) + 1)):
        raise Unreadable(f"messages.json holds the ids {sorted(store)}, not 1 to {len(store)} as the runtime assigns them")
    return store


def calls(run_dir: pathlib.Path) -> list[dict]:
    try:
        lines = (run_dir / "actions.jsonl").read_text().splitlines()
        recorded = [json.loads(line) for line in lines if line.strip()]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Unreadable(f"actions.jsonl is not readable JSON lines: {error}") from error
    for call in recorded:
        if (not isinstance(call, dict) or not set(call) <= FIELDS or not isinstance(call.get("action"), str)
                or call["action"] not in ACTIONS or not isinstance(call.get("at"), str)
                or not STAMP.fullmatch(call["at"])):
            raise Unreadable(f"actions.jsonl holds a call the runtime does not write: {call!r}")
    return recorded


def selector_runs(run_dir: pathlib.Path) -> list[dict]:
    """Every recorded run of the path selector, in order; none when the run never ran it."""
    path = run_dir / SELECTOR_LOG
    if not path.exists():
        return []
    try:
        runs = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Unreadable(f"{SELECTOR_LOG} is not readable JSON lines: {error}") from error
    for run in runs:
        if (not isinstance(run, dict) or set(run) != {"at", "argv", "stdout"} or not isinstance(run["at"], str)
                or not STAMP.fullmatch(run["at"]) or not isinstance(run["stdout"], str)
                or not isinstance(run["argv"], list) or not all(isinstance(arg, str) for arg in run["argv"])):
            raise Unreadable(f"{SELECTOR_LOG} holds a line the selector hook does not write: {run!r}")
    return runs


def sends(run_dir: pathlib.Path, scenario: str) -> tuple[list[dict], list[dict]]:
    """Every recorded call, and every recorded send in order with the text its message id names,
    after checking the calls are a sequence the runtime writes: each send names its own message,
    every kept message is named by one send, and only the first senior-engineer launch of a
    scenario with a handback is served it."""
    store = message_store(run_dir)
    recorded = calls(run_dir)
    found, served = [], 0
    for call in recorded:
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
    if store:
        raise Unreadable(f"messages.json keeps the messages {sorted(store)}, which no recorded call sent")
    return recorded, found


def outside_fences(text: str) -> list[str]:
    """The text's lines outside fenced code blocks and quotations."""
    kept, fence = [], None
    for line in text.splitlines():
        stripped = line.strip()
        if fence is not None:
            if stripped.startswith(fence) and not stripped[len(fence):].strip(fence[0]).strip():
                fence = None
            continue
        if match := FENCE.match(stripped):
            fence = match.group(1)
            continue
        if not stripped.startswith(">"):
            kept.append(stripped)
    return kept


def brief_paths(text: str) -> list[str]:
    """The values of the brief's path lines: a line outside code blocks and quotations whose whole
    text, trimmed, is `path: <value>`."""
    return [match.group(1) for line in outside_fences(text) if (match := PATH_LINE.fullmatch(line))]


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
               for token in re.findall(BEFORE + r"[0-9a-fA-F]{7,40}" + AFTER, text))


def names_deliverable(text: str) -> bool:
    """Whether the text names the deliverable link, not a longer link that starts with it."""
    return re.search(re.escape(DELIVERABLE) + r"(?![A-Za-z0-9_\-/?#=&]|\.[A-Za-z0-9])", text) is not None


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


def order_checks(recorded: list[dict], sent: list[dict]) -> list[tuple[bool, str]]:
    """The story was read on the tracker before anything was sent."""
    first = next((index for index, call in enumerate(recorded) if call["action"] in SENDS), len(recorded))
    read = any(call["action"] == "tracker-read" for call in recorded[:first])
    return [(read, "the story was read on the tracker before the first message" if sent
             else "the story was read on the tracker")]


def selector_checks(expectation: str, runs: list[dict], sent: list[dict]) -> list[tuple[bool, str]]:
    """The path selector ran and printed this story's line before anything was sent."""
    first = sent[0]["at"] if sent else None
    line = SELECTED[expectation]
    selected = [run for run in runs if run["stdout"].strip() == line and (first is None or run["at"] <= first)]
    return [(bool(selected), f"select-path.py printed `{line}` before the first message"
             + ("" if selected else f" (it ran {len(runs)} time(s), printing {[run['stdout'].strip() for run in runs]})"))]


def brief_checks(briefs: list[dict]) -> list[tuple[bool, str]]:
    """Each role brief names the story and the skill its role loads, each in a clause that denies
    nothing. A brief's rules may also name the skill in a clause that denies something, such as a
    step the role never does, so other clauses are not held to it."""
    return [(affirms(lambda clause: word(STORY, clause), brief["text"])
             and affirms(lambda clause, skill=ROLE_SKILL[brief["to"]]: word(skill, clause), brief["text"]),
             f"the {brief['to']} brief, message {brief['message_id']}, names {STORY} and {ROLE_SKILL[brief['to']]}, "
             "each in a clause that denies nothing")
            for brief in briefs]


def launch_checks(engineer: list[dict], qa: list[dict], engineers: int) -> list[tuple[bool, str]]:
    return [(len(engineer) == engineers, f"{engineers} senior-engineer session(s) were started ({len(engineer)} were)"),
            (len(qa) == 1, f"one QA session was started ({len(qa)} were)")]


def target_checks(expectation: str, qa: list[dict]) -> list[tuple[bool, str]]:
    """The QA brief names what QA verifies on the scenario's path, and no clause naming it denies
    anything."""
    if expectation in ("deployed", "deployed-path"):
        names, target = (lambda clause: word(ENVIRONMENT, clause)), f"the environment {ENVIRONMENT}"
    elif expectation == "spike":
        names, target = names_deliverable, f"the deliverable {DELIVERABLE}"
    else:
        names, target = names_merged_commit, f"the merged commit {MERGED_COMMIT[:7]}"
    return [(affirms_only(names, brief["text"]), f"the QA brief, message {brief['message_id']}, names {target}, "
             "and no clause naming it denies anything") for brief in qa]


def checks(expectation: str, run_dir: pathlib.Path, recorded: list[dict], sent: list[dict]) -> list[tuple[bool, str]]:
    to = {party: [send for send in sent if send["to"] == party] for party in SENDS.values()}
    engineer, qa, user = to["engineer"], to["qa"], to["user"]
    results = order_checks(recorded, sent)
    if expectation != "deployed":
        results += selector_checks(expectation, selector_runs(run_dir), sent)
    if expectation == "conflict":
        first = user[0]["text"] if user else ""
        named = [path for path in ("spike", "no-deployment", "deployed") if word(path, first)]
        return results + [
            (bool(user), "a message went to the user"),
            (len(named) == 3, "the first message to the user names the three paths, spike, no-deployment and deployed"
             + ("" if len(named) == 3 else f" (it names {named})")),
            (not engineer and not qa, "no senior-engineer or QA session was started"
             + (f" ({len(engineer)} senior-engineer, {len(qa)} QA)" if engineer or qa else "")),
            *path_checks(run_dir, PATHS[expectation], [])]
    results.append((not user, "no message went to the user" + (f" ({len(user)} did)" if user else "")))
    if expectation == "direct-entry":
        return (results + launch_checks(engineer, qa, 0) + brief_checks(qa) + target_checks(expectation, qa)
                + path_checks(run_dir, PATHS[expectation], qa))
    after = [brief for brief in qa if brief["after_handback"]]
    results += launch_checks(engineer, qa, 1)
    results.append((bool(after) and len(after) == len(qa), "the QA session was started only after the senior engineer handed back"))
    results += brief_checks(engineer + qa) + target_checks(expectation, qa)
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
        recorded, sent = sends(args.run_dir, scenario_of(args.expectation))
        results = checks(args.expectation, args.run_dir, recorded, sent)
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
