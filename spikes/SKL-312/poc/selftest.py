#!/usr/bin/env python3
"""Check the replay's own checks, without promptfoo, Node or the network.

  python3 spikes/SKL-312/poc/selftest.py

It does what promptfoo does in `run.sh` (call provider.py per run id, hand its output to
grade.py, write an export) in this process, then:

- writes the report from that replay and requires it to be the committed compare.md, apart
  from the two lines that name promptfoo's version and its environment, and requires the
  committed envelope.json to be an envelope of the first replayed run with the variable names
  the committed compare.md lists;
- requires `report` to exit 1 when a file it writes was not there or held other text;
- breaks one thing at a time, in the export, the provider's log, the lists or a copy of the
  records, and requires the report to refuse it or to exit 1;
- requires the rules that read history (a changed case, a shallow clone) and the way grade.py
  reads the grader to hold.

It does not run `run.sh`, so the prerequisites, the install, promptfoo itself and its export
are checked only by running that command. The repository's test job collects `tests/` only,
and the spike keeps every tracked change under `spikes/SKL-312/`, so this file is run by hand:
it exits 0 when every check holds and 1, naming the check, when one does not. It writes under
a temporary directory only.
"""

import contextlib
import copy
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import compare
import grade
import provider
import records

NOT_PROMPTFOO = ("- promptfoo version:", "  The variable names the provider script saw:")


def call(prompt: str, index: int) -> dict:
    """One test as promptfoo runs it: the provider, then the assertion when it exited 0."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        status = provider.main(["provider.py", prompt, "{}", "{}"])
    if status:
        return {"testIdx": index, "success": False, "failureReason": 2, "namedScores": {}, "cost": 0}
    graded = grade.get_assert(out.getvalue(), {})
    return {"testIdx": index, "success": graded["pass"], "failureReason": 0 if graded["pass"] else 1,
            "namedScores": graded["namedScores"], "cost": 0}


def export(results: list[dict]) -> dict:
    return {"metadata": {"promptfooVersion": "selftest"},
            "config": {"providers": [{"id": "exec: python3 provider.py"}], "defaultTest": {"assert": [{"type": "python"}]}},
            "results": {"stats": {"tokenUsage": {"total": 0}}, "results": results}}


def replay(work: pathlib.Path) -> pathlib.Path:
    """The whole of run.sh's replay into a new work directory: the runs, then the probes twice."""
    work.mkdir()
    os.environ["SKL312_WORK"] = str(work)
    compare.write_tests(work)
    runs = [call(run_id, index) for index, run_id in enumerate(compare.listed(work / "tests.csv"))]
    (work / "results.json").write_text(json.dumps(export(runs)))
    probes = compare.listed(work / "probes.csv")
    first = [call(probe, index) for index, probe in enumerate(probes)]
    (work / "probes-first.json").write_text(json.dumps(export(first)))
    # --retry-errors runs the ERROR rows of the eval again.
    retried = [call(probes[result["testIdx"]], result["testIdx"]) if result["failureReason"] == 2 else result for result in first]
    (work / "probes.json").write_text(json.dumps(export(retried)))
    return work


def report(work: pathlib.Path) -> tuple[object, str]:
    """What `compare.py report` makes of a work directory, whatever files were there before:
    0 or 1 as every run and probe landed as mapped or not, or the refusal's name, and the
    compare.md it gives."""
    try:
        text, _, mapped = compare.build(work)
    except (records.Unusable, compare.ContractChange) as refusal:
        return type(refusal).__name__, ""
    return (0 if mapped else 1), text


def edit_json(path: pathlib.Path, change) -> None:
    document = json.loads(path.read_text())
    change(document)
    path.write_text(json.dumps(document, indent=2) + "\n")


def main() -> int:
    failed = []

    def check(name: str, holds: bool) -> None:
        print(f"{'ok  ' if holds else 'FAIL'} {name}")
        if not holds:
            failed.append(name)

    with tempfile.TemporaryDirectory(prefix="skl312-selftest.") as scratch:
        scratch = pathlib.Path(scratch)
        base = replay(scratch / "base")
        status, written = report(base)
        committed = (records.POC / "compare.md").read_text()
        kept = lambda text: [line for line in text.splitlines() if not line.startswith(NOT_PROMPTFOO)]  # noqa: E731
        check("the replay without promptfoo exits 0", status == 0)
        check("its compare.md is the committed one", kept(written) == kept(committed))
        first_id = compare.listed(base / "tests.csv")[0]

        def committed_envelope() -> bool:
            envelope = (records.POC / "provider-contract" / "envelope.json").read_text()
            try:
                names = compare.environment_names(envelope)
            except compare.ContractChange:
                return False
            listed = NOT_PROMPTFOO[1] + " " + ", ".join(f"`{name}`" for name in names) + "."
            return json.loads(envelope)["argv"][1].get("value") == first_id and listed in committed.splitlines()

        check("the committed envelope.json is the first replayed run's, with the variable names compare.md lists",
              committed_envelope())

        out = scratch / "out"

        def written_again() -> int:
            with contextlib.redirect_stderr(io.StringIO()):
                return compare.report(base, out)

        check("a report whose two files were not there exits 1", written_again() == 1)
        check("the same report again exits 0", written_again() == 0)
        for name in ("compare.md", "provider-contract/envelope.json"):
            (out / name).unlink()
            check(f"a report whose {name} was deleted exits 1", written_again() == 1)
            (out / name).write_text((out / name).read_text() + "\n")
            check(f"a report whose {name} held other text exits 1", written_again() == 1)

        def broken_export(name: str, file_name: str, change, wanted: object) -> None:
            """One change to a copy of the replay's work directory."""
            work = scratch / f"work-{len(list(scratch.iterdir()))}"
            shutil.copytree(base, work)
            if file_name.endswith(".json"):
                edit_json(work / file_name, change)
            else:
                change(work / file_name)
            check(name, report(work)[0] == wanted)

        results = lambda document: document["results"]["results"]  # noqa: E731
        broken_export("a second result for one test index is refused", "results.json",
                      lambda document: results(document).append(copy.deepcopy(results(document)[0])), "ContractChange")
        broken_export("a missing result is refused", "results.json",
                      lambda document: results(document).pop(), "ContractChange")
        broken_export("an unknown failureReason is refused", "results.json",
                      lambda document: results(document)[0].update(failureReason=3), "ContractChange")
        broken_export("a promptfoo outcome that is not the mapped one is a mismatch", "results.json",
                      lambda document: results(document)[0].update(
                          success=not results(document)[0]["success"], failureReason=int(results(document)[0]["success"])), 1)
        broken_export("a graded run reported as an error is a mismatch", "results.json",
                      lambda document: results(document)[0].update(success=False, failureReason=2, namedScores={}), 1)
        broken_export("a grade promptfoo flipped is a mismatch", "results.json",
                      lambda document: results(document)[0].update(namedScores={name: 1 - score for name, score in results(document)[0]["namedScores"].items()}), 1)
        broken_export("a grade promptfoo reports and the record does not name is a mismatch", "results.json",
                      lambda document: results(document)[0]["namedScores"].update(extra=1), 1)
        broken_export("a replayed grade file with other text is a mismatch", f"runs/{first_id}/grader-output.txt",
                      lambda path: path.write_text("another line\n" + path.read_text()), 1)
        broken_export("an envelope without the arguments is refused", f"envelopes/{records.file_name(first_id)}.json",
                      lambda document: document.clear(), "ContractChange")
        broken_export("a probe that did not land as mapped fails the report", "probes.json",
                      lambda document: results(document)[0].update(success=True, failureReason=0), 1)
        broken_export("a probe whose logged exit status is not the mapped one fails the report", "provider-log/probe_void.jsonl",
                      lambda path: path.write_text(json.dumps({"status": 64, "kind": "unusable"}) + "\n" + path.read_text()), 1)
        broken_export("an export that names another provider is refused", "results.json",
                      lambda document: document["config"]["providers"][0].update(id="synthetic-remote-model"), "ContractChange")
        broken_export("an export with a second assertion type is refused", "results.json",
                      lambda document: document["config"]["defaultTest"]["assert"].append({"type": "llm-rubric"}), "ContractChange")
        broken_export("an export that counts tokens is refused", "results.json",
                      lambda document: document["results"]["stats"]["tokenUsage"].update(total=123), "ContractChange")
        broken_export("an export with a result that has a cost is refused", "results.json",
                      lambda document: results(document)[0].update(cost=5), "ContractChange")
        broken_export("a probe export that names another provider is refused", "probes-first.json",
                      lambda document: document["config"]["providers"][0].update(id="synthetic-remote-model"), "ContractChange")
        broken_export("a retried probe export that counts tokens is refused", "probes.json",
                      lambda document: document["results"]["stats"]["tokenUsage"].update(total=123), "ContractChange")
        log = f"provider-log/{records.file_name(first_id)}.jsonl"
        broken_export("a replayed run the provider logged with another exit status is a mismatch", log,
                      lambda path: path.write_text(json.dumps({"status": 64, "kind": "replayed"}) + "\n"), 1)
        broken_export("a provider log line that is not JSON is refused", log,
                      lambda path: path.write_text("{\n"), "ContractChange")
        broken_export("a missing envelope is refused", "envelopes",
                      lambda path: (path / f"{records.file_name(first_id)}.json").unlink(), "ContractChange")
        broken_export("a probe list that is not the one the replay writes is refused", "probes.csv",
                      lambda path: path.write_text("run_id\nprobe:void\n"), "Unusable")

        def broken_records(name: str, change, wanted: object, then=None) -> None:
            """One change to a copy of the records, replayed again from the start."""
            number = len(list(scratch.iterdir()))
            copied = scratch / f"records-{number}"
            shutil.copytree(records.RESULTS, copied)
            saved = records.RESULTS, records.added_in
            # The copy is outside the checkout, so the commit that added each record is HEAD's.
            records.RESULTS, records.added_in = copied, lambda run_id: "HEAD"
            try:
                change(copied)
                try:
                    with contextlib.redirect_stderr(io.StringIO()):
                        work = replay(scratch / f"work-{number}")
                except records.Unusable:
                    got, text = "Unusable", ""
                else:
                    if then:
                        then(work)
                    got, text = report(work)
            finally:
                records.RESULTS, records.added_in = saved
            check(name, got == wanted[0] and wanted[1] in text if isinstance(wanted, tuple) else got == wanted)

        record = lambda copied, change: edit_json(copied / f"{first_id}.json", change)  # noqa: E731
        graded = "grader-output.txt"
        broken_records("a recorded verdict that is not the replayed one is a mismatch",
                       lambda copied: record(copied, lambda r: r.update(
                           outcome="fail" if r["outcome"] == "pass" else "pass",
                           verdicts={name: "fail" if mark == "pass" else "pass" for name, mark in r["verdicts"].items()})), 1)
        broken_records("a recorded grade line the suite redacted still matches",
                       lambda copied: record(copied, lambda r: r["grades"][graded].__setitem__(0, "{redacted}")), 0)
        broken_records("a recorded grade line with other text is a mismatch",
                       lambda copied: record(copied, lambda r: r["grades"][graded].__setitem__(0, "another line")), 1)
        broken_records("a record whose grader input the suite redacted is listed, not replayed",
                       lambda copied: record(copied, lambda r: r["grader_inputs"].update({next(iter(r["grader_inputs"])): "{redacted}"})),
                       (0, f"| `{first_id}` | the suite redacted text the grader reads"))
        broken_records("a void record lands on ERROR through the provider's void status",
                       lambda copied: record(copied, lambda r: r.update(outcome="void", verdicts={}, grades={})), 0)
        broken_records("a void record the provider could not use is a mismatch",
                       lambda copied: record(copied, lambda r: r.update(outcome="void", verdicts={}, grades={})), 1,
                       then=lambda work: (work / "provider-log" / f"{records.file_name(first_id)}.jsonl").write_text(
                           json.dumps({"status": 64, "kind": "unusable"}) + "\n"))
        broken_records("a void record promptfoo reports grades for is a mismatch",
                       lambda copied: record(copied, lambda r: r.update(outcome="void", verdicts={}, grades={})), 1,
                       then=lambda work: edit_json(work / "results.json", lambda document: results(document)[0].update(namedScores={"extra": 1})))
        broken_records("a broken record lands on ERROR through the provider's own status",
                       lambda copied: record(copied, lambda r: r.update(outcome="error", verdicts={}, grades={})), 0)
        broken_records("a record that is not JSON is refused",
                       lambda copied: (copied / f"{first_id}.json").write_text("{"), "Unusable")
        broken_records("a record without its call record is refused",
                       lambda copied: (copied / f"{first_id}-calls.jsonl").unlink(), "Unusable")
        broken_records("a grade file the suite does not name is refused",
                       lambda copied: record(copied, lambda r: r["grades"].update({"other.txt": ["PASS"]})), "Unusable")
        broken_records("a record whose grade files are not its verdicts is refused",
                       lambda copied: record(copied, lambda r: r["verdicts"].update(extra="pass")), "Unusable")
        broken_records("no record at all is refused",
                       lambda copied: [path.unlink() for path in copied.glob("*.json")], "Unusable")
        broken_records("a verdict the suite does not write is refused",
                       lambda copied: record(copied, lambda r: r["verdicts"].update({next(iter(r["verdicts"])): "maybe"})), "Unusable")
        broken_records("a grade line that is not text is refused",
                       lambda copied: record(copied, lambda r: r["grades"][graded].__setitem__(0, 7)), "Unusable")
        broken_records("a grader input the run directory cannot hold is a provider error the report names",
                       lambda copied: record(copied, lambda r: r["grader_inputs"].update({"qa-round-1.json/child": "text"})),
                       (1, "the provider's log holds `unusable` with exit status 64 for this run"))

        os.environ["SKL312_WORK"] = str(scratch / "unknown")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            status = provider.main(["provider.py", "no-such-run", "{}", "{}"])
        check("a run id with no record exits 64, not the void status", status == records.UNUSABLE)

        # The rules that read history, with the real comparison: every record was added after
        # the repository's first commit, where the case's grader and fixtures did not exist.
        graded_ids = {run_id for run_id in records.run_ids() if records.load(run_id)["outcome"] in records.GRADED}
        first_commit = records.git("rev-list", "--max-parents=0", "HEAD").stdout.split()[0]
        saved = records.added_in
        records.added_in = lambda run_id: first_commit
        try:
            left_out = compare.plan()[1]
        finally:
            records.added_in = saved
        check("a record added at a commit whose grader and fixtures were others is listed, not replayed",
              set(left_out) == graded_ids and all("changed after the commit that added the record" in why for why in left_out.values()))

        saved = records.git
        records.git = lambda *args: (subprocess.CompletedProcess(args, 0, "true\n", "")
                                     if args == ("rev-parse", "--is-shallow-repository") else saved(*args))
        try:
            records.added_in.__wrapped__(first_id)
            refused = False
        except records.Unusable:
            refused = True
        finally:
            records.git = saved
        check("a shallow clone is refused", refused)

        # grade.py with a stand-in grader: a last line the suite reads as PASS once stripped,
        # and a line before it that must not reach promptfoo.
        work = scratch / "graded"
        shutil.copytree(base, work)
        stand_in = scratch / "grader.py"
        stand_in.write_text('print("a line that quotes the run")\nprint("PASS ")\n')
        os.environ["SKL312_WORK"] = str(work)
        saved, records.GRADER = records.GRADER, stand_in
        try:
            taken = grade.get_assert(json.dumps({"run_dir": f"runs/{first_id}",
                                                 "grades": records.grades_to_take(records.load(first_id))}), {})
        finally:
            records.GRADER = saved
        check("a grade whose last line is PASS before trailing space passes, as the suite reads it", taken["pass"] is True)
        check("what the grader prints is not handed to promptfoo", "quotes the run" not in json.dumps(taken))
        check("a table cell with a column separator or a line break stays one cell",
              compare.row("run|extra", "two\nlines") == "| run\\|extra | two lines |")

    print(f"selftest: {len(failed)} failed" if failed else "selftest: every check holds")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
