#!/usr/bin/env python3
"""List the recorded runs for promptfoo, then write compare.md from what promptfoo reported.

  compare.py tests WORK    write WORK/tests.csv, one row per suite run record of the case, and
                           WORK/probes.csv, the three provider probes
  compare.py report WORK   read promptfoo's JSON output under WORK, then write compare.md and
                           provider-contract/envelope.json beside this file

`report` exits 1 when a replayed run or a probe did not land on the promptfoo outcome the
mapping table gives its recorded outcome, or when a replayed grade differs from the recorded
one. compare.md is written either way and names each mismatch. It carries run ids, verdicts
and counts only, never grader output or call text, and nothing that changes between two runs
on the same commit.
"""

import csv
import json
import pathlib
import shutil
import subprocess
import sys

POC = pathlib.Path(__file__).resolve().parent
ROOT = POC.parents[2]
EVALS = ROOT / "skills" / "story-to-done" / "evals"
RESULTS = EVALS / "qa-unfinished-own-steps" / "results"
# Every outcome token suite.py can record (OUTCOMES, plus `error` for any other status), and
# the promptfoo outcome a provider that keeps run.sh's exit statuses gives it.
MAPPING = {"pass": "PASS", "fail": "FAIL", "void": "ERROR", "error": "ERROR"}
PROBES = ("probe:void", "probe:exit-3", "probe:void-once:{run_id}")


def records() -> dict[str, dict]:
    """The suite's run records of the case, by run id (the record's file stem)."""
    return {path.stem: json.loads(path.read_text()) for path in sorted(RESULTS.glob("*.json"))}


def history() -> list[tuple[str, str, str, str]]:
    """The runs of the records that predate the runner: file, run, expectation, grade."""
    rows = []
    for calls in sorted(RESULTS.glob("*-calls.jsonl")):
        if (RESULTS / f"{calls.name.removesuffix('-calls.jsonl')}.json").exists():
            continue
        for line in calls.read_text().splitlines():
            entry = json.loads(line) if line.strip() else {}
            if "grade" in entry:
                rows.append((calls.name, entry["run"], entry.get("expectation", "-"), entry["grade"]))
    for prose in sorted(RESULTS.glob("*.md")):
        if not (RESULTS / f"{prose.stem}-calls.jsonl").exists():
            rows.append((prose.name, "-", "-", "in prose only"))
    return rows


def write_tests(work: pathlib.Path) -> None:
    run_ids = list(records())
    for name, rows in (("tests.csv", run_ids), ("probes.csv", [probe.format(run_id=run_ids[0]) for probe in PROBES])):
        with (work / name).open("w", newline="") as out:
            csv.writer(out).writerows([["run_id"], *([row] for row in rows)])


def listed(path: pathlib.Path) -> list[str]:
    with path.open(newline="") as rows:
        return [row["run_id"] for row in csv.DictReader(rows)]


def outcomes(path: pathlib.Path, ids: list[str]) -> tuple[dict, dict[str, dict]]:
    """promptfoo's export and its result per listed id.

    Results are matched by test index: the export redacts a variable value it takes for a
    credential, and a run id is one, so the id is not readable from the result itself.
    """
    export = json.loads(path.read_text())
    by_index = {result["testIdx"]: result for result in export["results"]["results"]}
    if sorted(by_index) != list(range(len(ids))):
        sys.exit(f"compare.py: {path.name} holds results for tests {sorted(by_index)}, not one per listed id")
    return export, {run_id: by_index[index] for index, run_id in enumerate(ids)}


def verdict(result: dict) -> str:
    """promptfoo's outcome for one result: failureReason 0 is none, 1 an assertion, 2 an error."""
    if result["success"]:
        return "PASS"
    return {1: "FAIL", 2: "ERROR"}.get(result["failureReason"], f"unknown ({result['failureReason']})")


def grades(scores: dict) -> str:
    return ", ".join(f"{name}: {'pass' if score == 1 else 'fail'}" for name, score in scores.items()) or "none"


def replayed_lines(work: pathlib.Path, run_id: str, file_name: str) -> list[str] | None:
    path = work / "runs" / run_id / file_name
    return path.read_text().splitlines() if path.is_file() else None


def report(work: pathlib.Path) -> int:
    runs = records()
    export, results = outcomes(work / "results.json", listed(work / "tests.csv"))
    probe_ids = listed(work / "probes.csv")
    _, first = outcomes(work / "probes-first.json", probe_ids)
    _, retried = outcomes(work / "probes.json", probe_ids)
    stats = export["results"]["stats"]
    commit = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%H", "--", str(EVALS.relative_to(ROOT))],
                            capture_output=True, text=True).stdout.strip() or "unknown (not a git checkout)"

    table, mismatches, counts, grade_count = [], [], {}, 0
    for run_id, record in runs.items():
        result, expected = results[run_id], MAPPING[record["outcome"]]
        got = verdict(result)
        counts[record["outcome"]] = counts.get(record["outcome"], 0) + 1
        recorded = {name: 1 if mark == "pass" else 0 for name, mark in record["verdicts"].items()}
        grade_count += len(recorded)
        same_lines = all(replayed_lines(work, run_id, name) == lines for name, lines in record["grades"].items())
        match = got == expected and (got == "ERROR" or (result["namedScores"] == recorded and same_lines))
        table.append(f"| `{run_id}` | {record['outcome']} ({grades(recorded)}) | {got} ({grades(result['namedScores'])}) "
                     f"| {expected} | {'identical' if same_lines else 'differ'} | {'yes' if match else 'NO'} |")
        if not match:
            why = [f"the recorded outcome maps to {expected} and promptfoo reported {got}"] if got != expected else []
            if got == "ERROR":
                why.append("promptfoo reported a provider or assertion error, whose text is in the kept work directory's results.json")
            else:
                why += [f"grade {name}: recorded {'pass' if score else 'fail'}, replayed "
                        f"{ {1: 'pass', 0: 'fail'}.get(result['namedScores'].get(name), 'not taken') }"
                        for name, score in recorded.items() if result["namedScores"].get(name) != score]
                why += [f"`{name}`: the replayed grader output differs from the recorded lines"
                        for name, lines in record["grades"].items() if replayed_lines(work, run_id, name) != lines]
            mismatches.append(f"| `{run_id}` | {record['outcome']} ({grades(recorded)}) | {got} ({grades(result['namedScores'])}) "
                              f"| {'; '.join(why)} |")

    target = probe_ids[2].removeprefix("probe:void-once:")
    wanted = {probe_ids[0]: ("ERROR", "ERROR"), probe_ids[1]: ("ERROR", "ERROR"),
              probe_ids[2]: ("ERROR", MAPPING[runs[target]["outcome"]])}
    probes, probes_ok = [], True
    for probe, exits in zip(probe_ids, ("2 every call", "3 every call", "2 on the first call, then replays the run")):
        seen = (verdict(first[probe]), verdict(retried[probe]))
        probes_ok = probes_ok and seen == wanted[probe]
        probes.append(f"| `{probe}` | {exits} | {seen[0]} | {seen[1]} | {'yes' if seen == wanted[probe] else 'NO'} |")

    graded = sum(counts.get(token, 0) for token in ("pass", "fail"))
    old = history()
    providers = ", ".join(f"`{provider['id']}`" for provider in export["config"]["providers"])
    asserts = ", ".join(sorted({f"`{check['type']}`" for check in export["config"]["defaultTest"]["assert"]}))
    cost = sum(result.get("cost") or 0 for result in results.values())
    envelope = work / "envelopes" / f"{next(iter(runs))}.json"
    names = ", ".join(f"`{name}`" for name in json.loads(envelope.read_text())["environment_variable_names"])
    lines = [
        "# SKL-312 replay comparison: qa-unfinished-own-steps",
        "",
        "Written by `bash spikes/SKL-312/poc/run.sh`; never edited by hand.",
        "It holds run ids, verdicts and counts only.",
        "",
        f"- promptfoo version: {export['metadata']['promptfooVersion']}",
        f"- Commit of `skills/story-to-done/evals/` replayed (the last commit that changed it): `{commit}`",
        f"- Suite run records replayed: {len(runs)}, of which graded: {graded}",
        f"- Replayed runs that match their recorded verdict: {len(runs) - len(mismatches)} of {len(runs)}",
        f"- Recorded runs listed and not replayed: {len(old)} (see the last section); no parity is claimed for them",
        "",
        "## Zero model API calls",
        "",
        f"- Providers in the eval, from promptfoo's export: {providers}, a local script.",
        f"- Assertion types in the eval: {asserts}, none model-graded.",
        f"- promptfoo's own count for the eval: {stats['tokenUsage']['total']} tokens, cost {cost}.",
        "- `run.sh` starts promptfoo with `env -i`, so no provider credential reaches it.",
        f"  The variable names the provider script saw: {names}.",
        "",
        "## Replayed runs",
        "",
        "One row per suite run record under `skills/story-to-done/evals/qa-unfinished-own-steps/results/`.",
        "The recorded verdict is the record's `outcome` and, in brackets, each grade `grader.py` gave when the suite ran.",
        "The promptfoo verdict is what promptfoo reported after `grade.py` ran the committed `grader.py` on the rebuilt run.",
        "The mapped outcome is the promptfoo outcome the mapping table gives the recorded outcome.",
        "Grader output compares each rebuilt grade file with the lines the record kept.",
        "",
        "| Run id | `grader.py` verdict (recorded) | promptfoo verdict | Mapped outcome | Grader output | Match |",
        "|---|---|---|---|---|---|",
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
        "| retry (behaviour) | a void attempt is run again until the scenario has N graded runs or 2N attempts | `promptfoo eval --retry-errors` runs the ERROR rows of the latest eval again, once per invocation | `probe:void-once` |",
        "",
        "## Mapping probes",
        "",
        "No committed record is void or broken, so three provider probes exercise those exit statuses.",
        "They replay no case content and are not recorded runs.",
        "The first column of outcomes is from one eval of the probes, the second from `promptfoo eval --retry-errors` on that eval.",
        "",
        "| Probe | Provider exit status | promptfoo outcome | After `--retry-errors` | As mapped |",
        "|---|---|---|---|---|",
        *probes,
        "",
        "## Unmapped tokens (blockers)",
        "",
        "- `error`: promptfoo has one ERROR outcome, so a broken attempt and a void run land on the same outcome and the eval does not stop.",
        "  Telling them apart, and stopping without a summary, stays with a wrapper that reads the provider's exit status.",
        "- retry: promptfoo has no rule that runs a void attempt again until N graded runs with a cap of 2N attempts.",
        "  `--retry-errors` is one more pass over the ERROR rows per invocation, so the count and the cap stay with a wrapper.",
        "",
        "## Recorded runs not replayed",
        "",
        "These records predate the suite runner, and the eval README keeps them as history.",
        "A file holds several runs as call lines and one grade line each, with no run record: no scenario name, no grader inputs and no session ledger.",
        "Each grade came from the grader at that file's own commit, not the current one.",
        "Replaying them would compare two graders, so they are listed and not replayed.",
        "",
        "| Record | Run | Expectation | Recorded grade |",
        "|---|---|---|---|",
        *(f"| `{name}` | {run} | {expectation} | {grade} |" for name, run, expectation, grade in old),
    ]
    (POC / "compare.md").write_text("\n".join(lines) + "\n")
    (POC / "provider-contract").mkdir(exist_ok=True)
    shutil.copy(envelope, POC / "provider-contract" / "envelope.json")
    return 0 if not mismatches and probes_ok else 1


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in ("tests", "report"):
        sys.exit("usage: compare.py tests|report WORK")
    work = pathlib.Path(argv[2])
    if argv[1] == "tests":
        write_tests(work)
        return 0
    return report(work)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
