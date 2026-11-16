#!/usr/bin/env python3
"""List the recorded runs for promptfoo, then write compare.md from what promptfoo reported.

  compare.py tests WORK    write WORK/tests.csv, one row per suite run record the replay can
                           use, and WORK/probes.csv, the three provider probes
  compare.py report WORK   read promptfoo's JSON output and the provider's log under WORK, then
                           write compare.md and provider-contract/envelope.json beside this file

`report` exits 1 when a replayed run or a probe did not land on the promptfoo outcome the
mapping table gives it, when a replayed grade differs from the recorded one, or when either
file it writes differs from the one that was there or was not there. compare.md is written
either way and names each mismatch. It carries run ids, verdicts and counts only, never
grader output or call text, and nothing that changes between two runs on the same commit.

Both commands exit 1 with one line on stderr, and write nothing, when the evals directory
has uncommitted changes, when a record is not one the suite wrote, or when what promptfoo and
the provider left is not what this report was written against: a result per test index, a
known `failureReason`, the script provider and the `python` assertion alone with no token and
no cost counted, a provider log of statuses and kinds, a provider envelope of four arguments.
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
# What an eval that calls no model names in its export: the provider promptfooconfig.yaml
# configures, a local script, and the one assertion type, which runs grade.py.
PROVIDER = "exec: python3 provider.py"
ASSERTS = {"python"}
# The two lists `tests` writes for promptfoo: the run ids, then the probe ids.
LISTS = ("tests.csv", "probes.csv")
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


def listing(runs: dict[str, dict], left_out: dict[str, str]) -> tuple[list[str], list[str]]:
    """The run ids and the probe ids the replay lists for promptfoo, in order."""
    ids = [run_id for run_id in runs if run_id not in left_out]
    # The void-once probe replays the first record that passed, so its outcome after the
    # retry is PASS whatever records are added later.
    target = next((run_id for run_id in ids if runs[run_id]["outcome"] == "pass"), None)
    if target is None:
        raise records.Unusable("no suite run record with outcome pass can be replayed, and the void-once probe needs one")
    return ids, [probe[0].format(run_id=target) for probe in PROBES]


def history() -> tuple[list[tuple[str, object, object, object]], list[str]]:
    """The records that predate the runner: each grade line of a call file (file, run,
    expectation, grade), and the records kept in prose only."""
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
    prose = [path.name for path in sorted(records.RESULTS.glob("*.md"))
             if not (records.RESULTS / f"{path.stem}-calls.jsonl").exists()]
    return rows, prose


def row(*cells: object) -> str:
    """One markdown table row; a `|` or a line break in a value cannot split it."""
    return "| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ") for cell in cells) + " |"


def write_tests(work: pathlib.Path) -> None:
    for name, ids in zip(LISTS, listing(*plan())):
        with (work / name).open("w", newline="") as out:
            csv.writer(out).writerows([["run_id"], *([run_id] for run_id in ids)])


def listed(path: pathlib.Path) -> list[str]:
    try:
        with path.open(newline="") as lines:
            return [line["run_id"] for line in csv.DictReader(lines)]
    except (OSError, ValueError, KeyError, csv.Error) as error:
        raise ContractChange(f"{path.name} is not a list this replay wrote: {error!r}") from None


def outcomes(path: pathlib.Path, ids: list[str]) -> tuple[str, dict[str, dict]]:
    """The promptfoo version one export names, and its result per listed id.

    Results are matched by test index: the export redacts a variable value it takes for a
    credential, and a run id is one, so the id is not readable from the result itself. The
    export must hold exactly one result for each index, and must be of an eval that called no
    model: the script provider and the `python` assertion alone, no token and no cost counted.
    """
    try:
        export = json.loads(path.read_text())
        results = export["results"]["results"]
        indices = sorted(result["testIdx"] for result in results)
        providers = [provider["id"] for provider in export["config"]["providers"]]
        asserts = {check["type"] for check in export["config"]["defaultTest"]["assert"]}
        tokens = export["results"]["stats"]["tokenUsage"]["total"]
        costs = [result.get("cost") or 0 for result in results]
        version = str(export["metadata"]["promptfooVersion"])
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        raise ContractChange(f"{path.name} is not the export this report reads: {error!r}") from None
    if indices != list(range(len(ids))):
        raise ContractChange(f"{path.name} holds results for test indices {indices}, "
                             f"not exactly one for each of the {len(ids)} listed ids")
    model = [what for what, differs in (
        (f"providers {providers!r}", providers != [PROVIDER]),
        (f"assertion types {sorted(map(str, asserts))}", asserts != ASSERTS),
        (f"a token count of {tokens!r}", tokens != 0),
        ("a result with a cost", any(costs)),
    ) if differs]
    if model:
        raise ContractChange(f"{path.name} is not of an eval that called no model: it names {', '.join(model)}")
    return version, {ids[result["testIdx"]]: result for result in results}


def verdict(result: dict) -> str:
    """promptfoo's outcome for one result: failureReason 0 is none, 1 an assertion, 2 an error."""
    state = (result.get("success"), result.get("failureReason"))
    known = {(True, 0): "PASS", (False, 1): "FAIL", (False, 2): "ERROR"}
    if state not in known:
        raise ContractChange(f"a result has success {state[0]!r} with failureReason {state[1]!r}, which the mapping does not know")
    return known[state]


def named_scores(result: dict) -> dict:
    scores = result.get("namedScores") or {}
    if not isinstance(scores, dict):
        raise ContractChange("a result's namedScores is not a mapping of grade names to scores")
    return scores


def calls(work: pathlib.Path, prompt: str) -> list[tuple[int, str]]:
    """The exit status and kind of answer provider.py logged for each call with one prompt."""
    path = work / "provider-log" / f"{records.file_name(prompt)}.jsonl"
    if not path.is_file():
        return []
    try:
        return [(entry["status"], entry["kind"]) for entry in map(json.loads, path.read_text().splitlines())]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ContractChange(f"the provider's log {path.name} is not one provider.py wrote: {error!r}") from None


def logged(answers: list[tuple[int, str]]) -> str:
    return ", ".join(f"`{kind}` with exit status {status}" for status, kind in answers) or "no answer"


def envelope_of(work: pathlib.Path, run_id: str) -> str:
    """The envelope provider.py wrote for one run id."""
    try:
        return (work / "envelopes" / f"{records.file_name(run_id)}.json").read_text()
    except (OSError, ValueError) as error:
        raise ContractChange(f"the provider left no envelope for {run_id}: {type(error).__name__}") from None


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


def text_of(path: pathlib.Path) -> str | None:
    """A file's text, or None when there is no such file to read as text."""
    try:
        return path.read_text()
    except (OSError, ValueError):
        return None


def replayed_lines(work: pathlib.Path, run_id: str, file_name: str) -> list[str] | None:
    text = text_of(work / "runs" / run_id / file_name)
    return None if text is None else text.splitlines()


def build(work: pathlib.Path) -> tuple[str, str, bool]:
    """compare.md and envelope.json as this replay gives them, and whether every replayed run
    and every probe landed as mapped."""
    runs, left_out = plan()
    ids, probe_ids = listing(runs, left_out)
    for name, wanted in zip(LISTS, (ids, probe_ids)):
        if listed(work / name) != wanted:
            raise records.Unusable(f"{name} is not the list the replay writes from the records as they are now")
    version, results = outcomes(work / "results.json", ids)
    _, first = outcomes(work / "probes-first.json", probe_ids)
    _, retried = outcomes(work / "probes.json", probe_ids)
    commit = records.git("log", "-1", "--format=%H", "--", str(records.EVALS)).stdout.strip()

    table, mismatches, counts, grade_count = [], [], {}, 0
    for run_id, record in runs.items():
        outcome, expected = record["outcome"], MAPPING[record["outcome"]]
        counts[outcome] = counts.get(outcome, 0) + 1
        recorded = {name: 1 if mark == "pass" else 0 for name, mark in record["verdicts"].items()}
        grade_count += len(recorded)
        was = f"{outcome} ({grades(recorded)})"
        if run_id in left_out:
            table.append(row(f"`{run_id}`", was, "not replayed", expected, "-", "-", "no parity claimed"))
            continue
        result = results[run_id]
        got, scores = verdict(result), named_scores(result)
        marks = ", ".join(f"`{mark}`" for mark in records.placeholders(run_id, record)) or "none"
        why = [f"the recorded outcome maps to {expected} and promptfoo reported {got}"] if got != expected else []
        answers, wanted = calls(work, run_id), records.provider_answer(record)
        if answers != [wanted]:
            why.append(f"the provider's log holds {logged(answers)} for this run, not one {logged([wanted])}")
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
        table.append(row(f"`{run_id}`", was, f"{got} ({grades(scores)})", expected, output, marks, "NO" if why else "yes"))
        if why:
            mismatches.append(row(f"`{run_id}`", was, f"{got} ({grades(scores)})", "; ".join(why)))

    probes, landed = [], 0
    for probe, (_, does, statuses, wanted) in zip(probe_ids, PROBES):
        seen = (verdict(first[probe]), verdict(retried[probe]))
        exits = [status for status, _ in calls(work, probe)]
        mapped = seen == wanted and exits == statuses
        landed += mapped
        probes.append(row(f"`{probe}`", does, ", ".join(map(str, exits)) or "none", seen[0], seen[1], "yes" if mapped else "NO"))

    graded = sum(counts.get(token, 0) for token in records.GRADED)
    old, prose = history()
    old_runs = len({(name, str(run)) for name, run, _, _ in old})
    harness = ", ".join(f"`{commit}`" for commit in sorted({runs[run_id]["harness_commit"] for run_id in ids}))
    envelope = envelope_of(work, ids[0])
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
        f"- Recorded runs listed and not replayed: {len(left_out)} suite run records, and from before the runner "
        f"{old_runs} runs with {len(old)} grade lines in call records and {len(prose)} kept in prose only "
        "(see the last section); no parity is claimed for them",
        "",
        "## Zero model API calls",
        "",
        "The report is written only when promptfoo's export of each of the three evals (the replay, the probes, the probes retried) says all of this.",
        "",
        f"- The only provider: `{PROVIDER}`, the script in this directory.",
        "- The only assertion type: `python`, which runs `grade.py` and is not model-graded.",
        "- promptfoo's own count: 0 tokens, and no result with a cost.",
        "- `run.sh` starts promptfoo with `env -i`, so no provider credential reaches it.",
        f"  The variable names the provider script saw: {names}.",
        "",
        "## Replayed runs",
        "",
        "One row per suite run record under `skills/story-to-done/evals/qa-unfinished-own-steps/results/`.",
        "The recorded verdict is the record's `outcome` and, in brackets, each grade `grader.py` gave when the suite ran.",
        "The promptfoo verdict is what promptfoo reported after `grade.py` ran the committed `grader.py` on the rebuilt run.",
        "The mapped outcome is the promptfoo outcome the mapping table gives the recorded outcome.",
        "Grader output compares each rebuilt grade file with the lines the record kept: `identical` is line for line, with a placeholder the suite wrote standing for any text.",
        "The verdict is checked apart from that text, grade by grade.",
        "Placeholders names each kind the suite wrote into the grader inputs or the call record; the replay grades that text as committed.",
        "",
        "The grader and the scenario fixtures a run is graded with are the committed ones.",
        f"A record names the harness commit it was graded at and carries no hash of the grader or the fixtures; the replayed records name {harness}.",
        "The replay compares the grader and the fixtures with the commit that added the record and, where the clone holds it, with that harness commit, and lists a record as not replayed when either differs.",
        "A harness commit of a squash-merged branch is on no branch, so a clone holds it only once it is fetched by id.",
        "Without it the match is with the tree at the commit that added the record, which is then taken, not shown, to be the tree the suite graded with.",
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
        *(["| Run id | Why it is not replayed |", "|---|---|", *(row(f"`{run_id}`", why) for run_id, why in left_out.items())]
          if left_out else ["None."]),
        "",
        "### Records that predate the suite runner",
        "",
        "The eval README keeps these records as history.",
        "A call file holds several runs as call lines and one grade line for each expectation a run was graded on, with no run record: no scenario name, no grader inputs and no session ledger.",
        "Each grade came from the grader at that file's own commit, not the current one.",
        "Replaying them would compare two graders, so they are listed and not replayed.",
        "",
        "| Record | Run | Expectation | Recorded grade |",
        "|---|---|---|---|",
        *(row(f"`{name}`", run, expectation, grade) for name, run, expectation, grade in old),
        *(row(f"`{name}`", "-", "-", "in prose only") for name in prose),
    ]
    return "\n".join(lines) + "\n", envelope, not mismatches and landed == len(probes)


def report(work: pathlib.Path, out: pathlib.Path = records.POC) -> int:
    text, envelope, mapped = build(work)
    written = {out / "compare.md": text, out / "provider-contract" / "envelope.json": envelope}
    changed = [path.name for path, new in written.items() if text_of(path) != new]
    for path, new in written.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new)
    if changed:
        print(f"compare.py: {' and '.join(changed)} was not there or held other text; "
              "read the difference, commit it and run again", file=sys.stderr)
    return 0 if mapped and not changed else 1


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
