#!/usr/bin/env python3
"""promptfoo script provider: rebuild one recorded run of qa-unfinished-own-steps for grading.

promptfoo's `exec:` provider runs this as

  provider.py PROMPT OPTIONS_JSON CONTEXT_JSON

PROMPT is a run id: the file stem of a run record under the case's `results/`. The provider
never starts an agent and never calls a model. It rebuilds the run directory the case's
`run.sh` graded, from what the suite committed: the scenario's fixtures, the record's
`grader_inputs`, and the tool-call record as `actions.jsonl`. It prints one JSON line naming
that directory and the grades to take, which `grade.py` hands to the case's `grader.py`.

Exit status follows the case's `run.sh` where the record has one: 0 for a run rebuilt for
grading, 2 for a record whose outcome is void, and the recorded status (3 when it is not
usable) for a broken attempt. Anything the provider cannot replay exits 64, a status the case
contract does not use: a run id with no record, a malformed record, a missing call record, a
record the suite redacted, a case that changed after the record's harness commit, or an evals
directory with uncommitted changes. promptfoo reads every non-zero status as a provider
error, so the provider also appends its status and what kind of answer it was to
`$SKL312_WORK/provider-log/`, where `compare.py` reads which of them it was.

Every invocation also writes what it was called with (argument roles and JSON shapes,
environment variable names, never a value) under `$SKL312_WORK/envelopes/`, from which
`compare.py` keeps one as `provider-contract/envelope.json`.

Three probe ids exercise the statuses no committed record has. They replay no case content:
`probe:void` exits 2, `probe:exit-3` exits 3, and `probe:void-once:<run id>` exits 2 the
first time it is called in a work directory and replays that run id after that.
"""

import json
import os
import pathlib
import shutil
import sys

import records

VOID, BROKEN, UNUSABLE = 2, 3, 64


def shape(value: object) -> object:
    """The structure of a JSON value with every scalar replaced by its type name; a list keeps
    each distinct shape among its elements, in first-seen order."""
    if isinstance(value, dict):
        return {key: shape(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        shapes = []
        for item in map(shape, value):
            if item not in shapes:
                shapes.append(item)
        return shapes
    return {str: "string", bool: "boolean", int: "number", float: "number", type(None): "null"}[type(value)]


def envelope(argv: list[str]) -> dict:
    """What promptfoo handed this process, with names and shapes only."""
    def parsed(text: str) -> object:
        try:
            return shape(json.loads(text))
        except ValueError:
            return "not JSON"

    return {
        "provider_id": "exec: python3 provider.py",
        "working_directory": os.path.relpath(os.getcwd(), records.ROOT),
        "argv": [
            {"index": 0, "role": "script path, as the provider id names it", "value": argv[0]},
            {"index": 1, "role": "rendered prompt (here the run id)", "value": argv[1]},
            {"index": 2, "role": "provider options, one JSON document", "json_shape": parsed(argv[2])},
            {"index": 3, "role": "call context, one JSON document", "json_shape": parsed(argv[3])},
        ],
        "stdin": "closed by promptfoo before the script reads it",
        "stdout": "the whole of stdout, trimmed, is the provider output",
        "exit_status": "non-zero is a provider error; stderr with empty stdout is one too",
        "environment_variable_names": sorted(os.environ),
    }


def rebuild(run_id: str, work: pathlib.Path) -> tuple[int, str, str]:
    """Rebuild the run directory of one record. Returns the exit status, the kind of answer,
    and the JSON line for stdout or the reason for stderr."""
    record = records.load(run_id)
    if record["outcome"] == "void":
        return VOID, "void record", f"the recorded run is void: {record.get('void_reason')}"
    if record["outcome"] == "error":
        code = record.get("exit_code")
        return (code if type(code) is int and code > VOID and code != UNUSABLE else BROKEN,
                "broken record", "the recorded attempt is broken")
    changed = records.uncommitted()
    if changed:
        raise records.Unusable(f"the evals directory has uncommitted changes ({', '.join(changed[:3])})")
    why = records.not_replayable(run_id, record)
    if why:
        raise records.Unusable(why)
    grades, calls = records.grades_to_take(record), records.calls_text(run_id, record)
    scenario = records.CASE / "scenarios" / record["scenario"]
    run = work / "runs" / run_id
    shutil.rmtree(run, ignore_errors=True)
    run.mkdir(parents=True)
    # What run.sh copies in before the agent starts, less the prompt and the stub runtime,
    # which the grader never reads. not_replayable() showed they are the record's own.
    try:
        shutil.copy(scenario / "qa-round-1.json", run)
        shutil.copytree(scenario / "checklists", run, dirs_exist_ok=True)
    except OSError as error:
        raise records.Unusable(f"scenario {record['scenario']} lacks a fixture: {error}") from None
    # What the run left for the grader, as the suite recorded it.
    for name, text in record["grader_inputs"].items():
        target = (run / name).resolve()
        if run.resolve() not in target.parents:
            raise records.Unusable(f"the record names a grader input outside its run directory: {name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    if calls is not None:
        (run / "actions.jsonl").write_text(calls)
    return 0, "replayed", json.dumps({"run_id": run_id, "run_dir": f"runs/{run_id}", "grades": grades})


def answer(prompt: str, work: pathlib.Path) -> tuple[int, str, str]:
    if prompt == "probe:void":
        return VOID, "probe", "probe: a void run"
    if prompt == "probe:exit-3":
        return BROKEN, "probe", "probe: a status the case contract does not define"
    if prompt.startswith("probe:void-once:"):
        marker = work / "probes" / "void-once"
        if not marker.exists():
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("the first call was void\n")
            return VOID, "probe", "probe: void on the first call"
        prompt = prompt.removeprefix("probe:void-once:")
    try:
        return rebuild(prompt, work)
    except records.Unusable as why:
        return UNUSABLE, "unusable", str(why)


def main(argv: list[str]) -> int:
    if len(argv) != 4 or not os.environ.get("SKL312_WORK"):
        print("provider.py: usage: SKL312_WORK=DIR provider.py PROMPT OPTIONS_JSON CONTEXT_JSON", file=sys.stderr)
        return UNUSABLE
    work, name = pathlib.Path(os.environ["SKL312_WORK"]), records.file_name(argv[1])
    for directory in ("envelopes", "provider-log"):
        (work / directory).mkdir(parents=True, exist_ok=True)
    (work / "envelopes" / f"{name}.json").write_text(json.dumps(envelope(argv), indent=2) + "\n")
    status, kind, text = answer(argv[1], work)
    with (work / "provider-log" / f"{name}.jsonl").open("a") as log:
        log.write(json.dumps({"status": status, "kind": kind}) + "\n")
    print(text if status == 0 else f"provider.py: {text}", file=sys.stdout if status == 0 else sys.stderr)
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv))
