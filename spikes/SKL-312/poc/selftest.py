#!/usr/bin/env python3
"""Check the replay's own checks, without promptfoo, Node or the network.

  python3 spikes/SKL-312/poc/selftest.py

It does what promptfoo does in `run.sh` (call provider.py per run id, hand its output to
grade.py, write an export) in this process, then:

- writes the report from that replay and requires it to be the committed compare.md, apart
  from the two lines that name promptfoo's version and its environment;
- breaks one thing at a time, in the export, the provider's log or a copy of the records, and
  requires the report to refuse it or to exit 1.

The repository's test job collects `tests/` only, and the spike keeps every tracked change
under `spikes/SKL-312/`, so this file is run by hand: it exits 0 when every check holds and 1,
naming the check, when one does not. It writes under a temporary directory only.
"""

import contextlib
import copy
import io
import json
import os
import pathlib
import shutil
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
    """What `compare.py report` does with a work directory: its exit status or the refusal's
    name, and the compare.md it wrote."""
    out = work / "out"
    shutil.rmtree(out, ignore_errors=True)
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            status = compare.report(work, out)
    except (records.Unusable, compare.ContractChange) as refusal:
        return type(refusal).__name__, ""
    return status, (out / "compare.md").read_text()


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

        os.environ["SKL312_WORK"] = str(scratch / "unknown")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            status = provider.main(["provider.py", "no-such-run", "{}", "{}"])
        check("a run id with no record exits 64, not the void status", status == provider.UNUSABLE)

    print(f"selftest: {len(failed)} failed" if failed else "selftest: every check holds")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
