#!/usr/bin/env python3
"""List the recorded runs for promptfoo, then write compare.md from what promptfoo reported.

  compare.py tests WORK    write WORK/tests.csv, one row per suite run record the replay can
                           use, and WORK/probes.csv, the three provider probes
  compare.py report WORK   read promptfoo's JSON output and the provider's log under WORK, then
                           write compare.md and provider-contract/envelope.json beside this file

`report` exits 1 when a replayed run or a probe did not land on the promptfoo outcome the
mapping table gives it, when a replayed grade differs from the recorded one, or when either
file it writes differs from the one that was there. compare.md is written either way and
names each mismatch. It carries run ids, verdicts and counts only, never grader output or
call text, and nothing that changes between two runs on the same commit.

Both commands exit 1 with one line on stderr, and write nothing, when the evals directory
has uncommitted changes, when a record is not one the suite wrote, or when promptfoo's
export is not the one this report was written against (a result per test index, a known
`failureReason`, a provider envelope of four arguments).
"""

import csv
import json
import pathlib
import sys

import records

# Every outcome token suite.py can record (OUTCOMES, plus `error` for any other status), the
# promptfoo outcome a provider that keeps run.sh's exit statuses gives it, and the kind of
# answer provider.py logs for it.
MAPPING = {"pass": "PASS", "fail": "FAIL", "void": "ERROR", "error": "ERROR"}
KIND = {"pass": "replayed", "fail": "replayed", "void": "void record", "error": "broken record"}
# Each probe: its id, what the provider does, its exit status on the first eval and on the
# --retry-errors pass, and promptfoo's outcome after each.
PROBES = (
    ("probe:void", "exits 2 on every call", [2, 2], ("ERROR", "ERROR")),
    ("probe:exit-3", "exits 3 on every call", [3, 3], ("ERROR", "ERROR")),
    ("probe:void-once:{run_id}", "exits 2 on the first call, then replays the run", [2, 0], ("ERROR", "PASS")),
)


class ContractChange(Exception):
    """promptfoo's output is not what this report was written against."""


def plan() -> tuple[dict[str, dict], dict[str, str]]:
    """Every suite run record of the case by run id, and why each graded one the replay
    leaves out cannot be graded again."""
    changed = records.uncommitted()
    if changed:
        raise records.Unusable(f"the evals directory has uncommitted changes ({', '.join(changed[:3])}), "
                               "so a replay would be of no commit")
    runs = {run_id: records.load(run_id) for run_id in records.run_ids()}
    left_out = {}
    for run_id, record in runs.items():
        if record["outcome"] in records.GRADED:
            why = records.not_replayable(run_id, record)
            if why:
                left_out[run_id] = why
            else:
                records.grades_to_take(record)
    return runs, left_out


def history() -> list[tuple[str, str, str, str]]:
    """The runs of the records that predate the runner: file, run, expectation, grade."""
    rows = []
    for calls in sorted(records.RESULTS.glob("*-calls.jsonl")):
        if (records.RESULTS / f"{calls.name.removesuffix('-calls.jsonl')}.json").exists():
            continue
        for number, line in enumerate(calls.read_text().splitlines(), 1):
            try:
                entry = json.loads(line) if line.strip() else {}
            except ValueError as error:
                raise records.Unusable(f"{calls.name} line {number} is not JSON: {error}") from None
            if isinstance(entry, dict) and "grade" in entry:
                rows.append((calls.name, entry.get("run", "-"), entry.get("expectation", "-"), entry["grade"]))
    for prose in sorted(records.RESULTS.glob("*.md")):
        if not (records.RESULTS / f"{prose.stem}-calls.jsonl").exists():
            rows.append((prose.name, "-", "-", "in prose only"))
    return rows


def write_tests(work: pathlib.Path) -> None:
    runs, left_out = plan()
    ids = [run_id for run_id in runs if run_id not in left_out]
    # The void-once probe replays the first record that passed, so its outcome after the
    # retry is PASS whatever records are added later.
    target = next((run_id for run_id in ids if runs[run_id]["outcome"] == "pass"), None)
    if target is None:
        raise records.Unusable("no suite run record with outcome pass can be replayed, and the void-once probe needs one")
    for name, rows in (("tests.csv", ids), ("probes.csv", [probe[0].format(run_id=target) for probe in PROBES])):
        with (work / name).open("w", newline="") as out:
            csv.writer(out).writerows([["run_id"], *([row] for row in rows)])


def listed(path: pathlib.Path) -> list[str]:
    with path.open(newline="") as rows:
        return [row["run_id"] for row in csv.DictReader(rows)]


def outcomes(path: pathlib.Path, ids: list[str]) -> tuple[dict, dict[str, dict]]:
    """promptfoo's export and its result per listed id.

    Results are matched by test index: the export redacts a variable value it takes for a
    credential, and a run id is one, so the id is not readable from the result itself. The
    export must hold exactly one result for each index.
    """
    try:
        export = json.loads(path.read_text())
        results = export["results"]["results"]
        indices = sorted(result["testIdx"] for result in results)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ContractChange(f"{path.name} is not the export this report reads: {error!r}") from None
    if indices != list(range(len(ids))):
        raise ContractChange(f"{path.name} holds results for test indices {indices}, "
                             f"not exactly one for each of the {len(ids)} listed ids")
    return export, {ids[result["testIdx"]]: result for result in results}


def verdict(result: dict) -> str:
    """promptfoo's outcome for one result: failureReason 0 is none, 1 an assertion, 2 an error."""
    state = (result.get("success"), result.get("failureReason"))
    known = {(True, 0): "PASS", (False, 1): "FAIL", (False, 2): "ERROR"}
    if state not in known:
        raise ContractChange(f"a result has success {state[0]!r} with failureReason {state[1]!r}, which the mapping does not know")
    return known[state]


def calls(work: pathlib.Path, prompt: str) -> list[tuple[int, str]]:
    """The exit status and kind of answer provider.py logged for each call with one prompt."""
    path = work / "provider-log" / f"{records.file_name(prompt)}.jsonl"
    if not path.is_file():
        return []
    return [(entry["status"], entry["kind"]) for entry in map(json.loads, path.read_text().splitlines())]


def environment_names(envelope: str) -> list[str]:
    """The environment variable names in one provider envelope, once it is seen to be one."""
    try:
        seen = json.loads(envelope)
        whole = ([argument["index"] for argument in seen["argv"]] == [0, 1, 2, 3]
                 and all(isinstance(seen["argv"][index]["json_shape"], dict) for index in (2, 3))
                 and "SKL312_WORK" in seen["environment_variable_names"])
    except (ValueError, KeyError, TypeError, IndexError):
        whole = False
    if not whole:
        raise ContractChange("the provider envelope does not hold four arguments, two of them JSON documents, "
                             "and the environment variable names")
    return seen["environment_variable_names"]


def grades(scores: dict) -> str:
    return ", ".join(f"{name}: {'pass' if score == 1 else 'fail'}" for name, score in scores.items()) or "none"


def replayed_lines(work: pathlib.Path, run_id: str, file_name: str) -> list[str] | None:
    path = work / "runs" / run_id / file_name
    return path.read_text().splitlines() if path.is_file() else None


def report(work: pathlib.Path, out: pathlib.Path = records.POC) -> int:
    runs, left_out = plan()
    ids = listed(work / "tests.csv")
    if not ids or ids != [run_id for run_id in runs if run_id not in left_out]:
        raise records.Unusable("the records the replay can use are not the ones it listed for promptfoo")
    export, results = outcomes(work / "results.json", ids)
    probe_ids = listed(work / "probes.csv")
    _, first = outcomes(work / "probes-first.json", probe_ids)
    _, retried = outcomes(work / "probes.json", probe_ids)
    try:
        stats, version = export["results"]["stats"]["tokenUsage"]["total"], export["metadata"]["promptfooVersion"]
        providers = ", ".join(f"`{provider['id']}`" for provider in export["config"]["providers"])
        asserts = ", ".join(sorted({f"`{check['type']}`" for check in export["config"]["defaultTest"]["assert"]}))
    except (KeyError, TypeError) as error:
        raise ContractChange(f"results.json lacks a field this report reads: {error!r}") from None
    commit = records.git("log", "-1", "--format=%H", "--", str(records.EVALS)).stdout.strip()

    table, mismatches, counts, grade_count = [], [], {}, 0
    for run_id, record in runs.items():
        outcome, expected = record["outcome"], MAPPING[record["outcome"]]
        counts[outcome] = counts.get(outcome, 0) + 1
        recorded = {name: 1 if mark == "pass" else 0 for name, mark in record["verdicts"].items()}
        grade_count += len(recorded)
        was = f"{outcome} ({grades(recorded)})"
        if run_id in left_out:
            table.append(f"| `{run_id}` | {was} | not replayed | {expected} | - | - | no parity claimed |")
            continue
        result = results[run_id]
        got, scores = verdict(result), result.get("namedScores") or {}
        marks = ", ".join(f"`{mark}`" for mark in records.placeholders(run_id, record)) or "none"
        why = [f"the recorded outcome maps to {expected} and promptfoo reported {got}"] if got != expected else []
        kinds = [kind for _, kind in calls(work, run_id)]
        if kinds != [KIND[outcome]]:
            why.append(f"the provider's log holds {', '.join(kinds) or 'no answer'} for this run, not one `{KIND[outcome]}`")
        output = "-"
        if outcome in records.GRADED:
            why += [f"grade {name}: recorded {'pass' if score else 'fail'}, replayed "
                    f"{ {1: 'pass', 0: 'fail'}.get(scores.get(name), 'not taken') }"
                    for name, score in recorded.items() if scores.get(name) != score]
            differ = [name for name, lines in record["grades"].items()
                      if not records.same_lines(lines, replayed_lines(work, run_id, name))]
            why += [f"`{name}`: the replayed grader output differs from the recorded lines" for name in differ]
            output = "differ" if differ else "identical"
            if set(scores) - set(recorded):
                why.append("promptfoo reports a grade the record does not name")
        elif scores:
            why.append("promptfoo reports grades for a run the suite did not grade")
        if why and got == "ERROR" and expected != "ERROR":
            why.append("the error text is in the kept work directory's results.json")
        if why and marks != "none":
            why.append(f"the record's grader inputs carry {marks}, so a difference may come from the record")
        table.append(f"| `{run_id}` | {was} | {got} ({grades(scores)}) | {expected} | {output} | {marks} | {'NO' if why else 'yes'} |")
        if why:
            mismatches.append(f"| `{run_id}` | {was} | {got} ({grades(scores)}) | {'; '.join(why)} |")

    probes, landed = [], 0
    for probe, (_, does, statuses, wanted) in zip(probe_ids, PROBES, strict=True):
        seen = (verdict(first[probe]), verdict(retried[probe]))
        logged = [status for status, _ in calls(work, probe)]
        mapped = seen == wanted and logged == statuses
        landed += mapped
        probes.append(f"| `{probe}` | {does} | {', '.join(map(str, logged)) or 'none'} | {seen[0]} | {seen[1]} | {'yes' if mapped else 'NO'} |")

    graded = sum(counts.get(token, 0) for token in records.GRADED)
    old = history()
    cost = sum(result.get("cost") or 0 for result in results.values())
    envelope = (work / "envelopes" / f"{records.file_name(ids[0])}.json").read_text()
    names = ", ".join(f"`{name}`" for name in environment_names(envelope))
    lines = [
        "# SKL-312 replay comparison: qa-unfinished-own-steps",
        "",
        "Written by `bash spikes/SKL-312/poc/run.sh`; never edited by hand.",
        "It holds run ids, verdicts and counts only.",
        "",
        f"- promptfoo version: {version}",
        f"- Commit of `skills/story-to-done/evals/` replayed (the last commit that changed it; nothing under it was uncommitted): `{commit}`",
        f"- Suite run records: {len(runs)}, of which graded: {graded}, replayed: {len(ids)}",
        f"- Replayed runs that match their recorded verdict: {len(ids) - len(mismatches)} of {len(ids)}",
        f"- Mapping probes that landed as mapped: {landed} of {len(probes)}",
        f"- Recorded runs listed and not replayed: {len(left_out)} suite run records and {len(old)} runs in records "
        "that predate the runner (see the last section); no parity is claimed for them",
        "",
        "## Zero model API calls",
        "",
        f"- Providers in the eval, from promptfoo's export: {providers}, a local script.",
        f"- Assertion types in the eval: {asserts}, none model-graded.",
        f"- promptfoo's own count for the eval: {stats} tokens, cost {cost}.",
        "- `run.sh` starts promptfoo with `env -i`, so no provider credential reaches it.",
        f"  The variable names the provider script saw: {names}.",
        "",
        "## Replayed runs",
        "",
        "One row per suite run record under `skills/story-to-done/evals/qa-unfinished-own-steps/results/`.",
        "The recorded verdict is the record's `outcome` and, in brackets, each grade `grader.py` gave when the suite ran.",
        "The promptfoo verdict is what promptfoo reported after `grade.py` ran the committed `grader.py` on the rebuilt run.",
        "The mapped outcome is the promptfoo outcome the mapping table gives the recorded outcome.",
        "Grader output compares each rebuilt grade file with the lines the record kept, a placeholder the suite wrote standing for any text.",
        "Placeholders names each kind the suite wrote into the grader inputs or the call record; the replay grades that text as committed.",
        "",
        "| Run id | `grader.py` verdict (recorded) | promptfoo verdict | Mapped outcome | Grader output | Placeholders | Match |",
        "|---|---|---|---|---|---|---|",
        *table,
        "",
        "## Mismatches",
        "",
        *(["| Run id | Recorded | promptfoo | Explanation |", "|---|---|---|---|", *mismatches] if mismatches else ["None."]),
        "",
        "## Verdict mapping",
        "",
        "Every token `suite.py` can record, and the behaviour it attaches to a void run.",
        "",
        "| Harness token | The harness emits it when | promptfoo outcome | Observed here |",
        "|---|---|---|---|",
        f"| `pass` (outcome) | `run.sh` exits 0 | PASS: `success` true, `failureReason` 0 | {counts.get('pass', 0)} recorded runs |",
        f"| `fail` (outcome) | `run.sh` exits 1 | FAIL: `success` false, `failureReason` 1 (assertion) | {counts.get('fail', 0)} recorded runs |",
        f"| `pass` or `fail` (a grade in `verdicts`) | a grade file ends in `PASS` or not | named score 1 or 0 under the grade's name | {grade_count} recorded grades |",
        f"| `void` (outcome) | `run.sh` exits 2, or the attempt passes its deadline | ERROR: `success` false, `failureReason` 2, counted under `errors` | {counts.get('void', 0)} recorded runs; `probe:void` for exit 2; the deadline is not exercised |",
        f"| `error` (outcome) | any other exit status, or grade files that contradict it; the suite stops | ERROR, the same outcome as `void`, and the eval goes on | {counts.get('error', 0)} recorded runs; `probe:exit-3` |",
        "| retry (behaviour) | a void attempt is run again until the scenario has N graded runs or 2N attempts | none: `promptfoo eval --retry-errors` runs the ERROR rows of the latest eval again, once per invocation | `probe:void-once` |",
        "",
        "## Mapping probes",
        "",
        "No committed record is void or broken, so three provider probes exercise those exit statuses.",
        "They replay no case content and are not recorded runs.",
        "The exit statuses are the ones the provider logged, one per call: the first eval, then `promptfoo eval --retry-errors` on that eval.",
        "The two outcome columns are promptfoo's after each.",
        "",
        "| Probe | The provider | Exit statuses logged | promptfoo outcome | After `--retry-errors` | As mapped |",
        "|---|---|---|---|---|---|",
        *probes,
        "",
        "## Unmapped tokens (blockers)",
        "",
        "- retry: promptfoo has no rule that runs a void attempt again until N graded runs with a cap of 2N attempts.",
        "  `--retry-errors` is one more pass over the ERROR rows per invocation, so the count and the cap stay with a wrapper.",
        "",
        "## Tokens mapped with a loss (blockers)",
        "",
        "- `error`: it has a promptfoo outcome, ERROR, and `void` has the same one, so a broken attempt and a void run cannot be told apart in the result, and the eval does not stop.",
        "  Telling them apart, and stopping without a summary, stays with a wrapper that reads the provider's exit status.",
        "",
        "## Recorded runs not replayed",
        "",
        "### Suite run records",
        "",
        *(["| Run id | Why it is not replayed |", "|---|---|", *(f"| `{run_id}` | {why} |" for run_id, why in left_out.items())]
          if left_out else ["None."]),
        "",
        "### Records that predate the suite runner",
        "",
        "The eval README keeps these records as history.",
        "A file holds several runs as call lines and one grade line each, with no run record: no scenario name, no grader inputs and no session ledger.",
        "Each grade came from the grader at that file's own commit, not the current one.",
        "Replaying them would compare two graders, so they are listed and not replayed.",
        "",
        "| Record | Run | Expectation | Recorded grade |",
        "|---|---|---|---|",
        *(f"| `{name}` | {run} | {expectation} | {grade} |" for name, run, expectation, grade in old),
    ]
    written = {out / "compare.md": "\n".join(lines) + "\n", out / "provider-contract" / "envelope.json": envelope}
    changed = [path.name for path, text in written.items() if path.is_file() and path.read_text() != text]
    for path, text in written.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    if changed:
        print(f"compare.py: {' and '.join(changed)} changed from the file that was there; "
              "read the difference, commit it and run again", file=sys.stderr)
    return 0 if not mismatches and landed == len(probes) and not changed else 1


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in ("tests", "report"):
        sys.exit("usage: compare.py tests|report WORK")
    try:
        if argv[1] == "tests":
            write_tests(pathlib.Path(argv[2]))
            return 0
        return report(pathlib.Path(argv[2]))
    except (records.Unusable, ContractChange) as why:
        print(f"compare.py: {why}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
