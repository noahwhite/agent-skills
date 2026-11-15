#!/usr/bin/env python3
"""promptfoo script provider: rebuild one recorded run of qa-unfinished-own-steps for grading.

promptfoo's `exec:` provider runs this as

  provider.py PROMPT OPTIONS_JSON CONTEXT_JSON

PROMPT is a run id: the file stem of a run record under the case's `results/`. The provider
never starts an agent and never calls a model. It rebuilds the run directory the case's
`run.sh` graded, from what the suite committed: the scenario's fixtures, the record's
`grader_inputs`, and the tool-call record as `actions.jsonl`. It prints one JSON line naming
that directory and the grades to take, which `grade.py` hands to the case's `grader.py`.

Exit status follows the case's `run.sh`: 0 for a run rebuilt for grading, 2 for a void run
(a record whose outcome is void, or a run id with no usable record), and the recorded status
for a broken attempt. promptfoo reads any non-zero status as a provider error.

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
import re
import shutil
import sys

POC = pathlib.Path(__file__).resolve().parent
ROOT = POC.parents[2]
CASE = ROOT / "skills" / "story-to-done" / "evals" / "qa-unfinished-own-steps"
RESULTS = CASE / "results"
RUN_ID = re.compile(r"[A-Za-z0-9._-]+")
# The suite's grade file names (suite.py GRADE_FILE): grader-output.txt is the scenario's own
# grade and grader-<g>-output.txt a further grade named <scenario>-<g>.
GRADE_FILE = re.compile(r"grader(?:-(?P<grade>[A-Za-z0-9._-]+))?-output\.txt")
VOID, BROKEN = 2, 3


def shape(value: object) -> object:
    """The structure of a JSON value with every scalar replaced by its type name."""
    if isinstance(value, dict):
        return {key: shape(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [shape(value[0])] if value else []
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
        "working_directory": os.path.relpath(os.getcwd(), ROOT),
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


def stop(status: int, why: str) -> None:
    print(f"provider.py: {why}", file=sys.stderr)
    sys.exit(status)


def rebuild(run_id: str, work: pathlib.Path) -> dict:
    """Rebuild the run directory of one record and name the grades its run.sh took."""
    if not RUN_ID.fullmatch(run_id):
        stop(VOID, "the run id is not a record file stem")
    record_path = RESULTS / f"{run_id}.json"
    if not record_path.is_file():
        stop(VOID, f"no run record {run_id}.json")
    record = json.loads(record_path.read_text())
    if record["outcome"] == "void":
        stop(VOID, f"the recorded run is void: {record['void_reason']}")
    if record["outcome"] not in ("pass", "fail"):
        code = record["exit_code"]
        stop(code if isinstance(code, int) and code > VOID else BROKEN, "the recorded attempt is broken")
    scenario = CASE / "scenarios" / record["scenario"]
    run = work / "runs" / run_id
    shutil.rmtree(run, ignore_errors=True)
    run.mkdir(parents=True)
    # What run.sh copies in before the agent starts, less the prompt and the stub runtime,
    # which the grader never reads.
    shutil.copy(scenario / "qa-round-1.json", run)
    shutil.copytree(scenario / "checklists", run, dirs_exist_ok=True)
    # What the run left for the grader, as the suite recorded it.
    for name, text in record["grader_inputs"].items():
        target = (run / name).resolve()
        if run.resolve() not in target.parents:
            stop(VOID, f"the record names a grader input outside its run directory: {name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    if record["calls_record"] != "absent":
        shutil.copy(RESULTS / f"{run_id}-calls.jsonl", run / "actions.jsonl")
    grades = []
    for file_name in sorted(record["grades"], key=lambda name: (name != "grader-output.txt", name)):
        grade = GRADE_FILE.fullmatch(file_name)["grade"]
        grades.append({"expectation": record["scenario"] + (f"-{grade}" if grade else ""), "file": file_name})
    return {"run_id": run_id, "run_dir": f"runs/{run_id}", "grades": grades}


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        stop(VOID, "usage: provider.py PROMPT OPTIONS_JSON CONTEXT_JSON")
    work = pathlib.Path(os.environ.get("SKL312_WORK") or stop(VOID, "SKL312_WORK is not set"))
    prompt = argv[1]
    envelopes = work / "envelopes"
    envelopes.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", prompt)
    (envelopes / f"{name}.json").write_text(json.dumps(envelope(argv), indent=2) + "\n")
    if prompt == "probe:void":
        stop(VOID, "probe: a void run")
    if prompt == "probe:exit-3":
        stop(BROKEN, "probe: a status the case contract does not define")
    if prompt.startswith("probe:void-once:"):
        marker = work / "probes" / "void-once"
        if not marker.exists():
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("the first call was void\n")
            stop(VOID, "probe: void on the first call")
        prompt = prompt.removeprefix("probe:void-once:")
    print(json.dumps(rebuild(prompt, work)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
