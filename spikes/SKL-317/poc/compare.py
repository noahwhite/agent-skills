#!/usr/bin/env python3
"""Write compare.md for one run of the SKL-317 proof of concept; run.sh calls it last.

It reads what the provider recorded (attempts, calls, a stop), promptfoo's JSON export, the
spend ledger before and after the run, and suite.py at the commit under test, and writes one
Markdown file of tables. It copies fields only: an exit status, an outcome, a count, a model
id, a fixed reason. No path, session id, prompt text, agent output or error text of promptfoo
reaches the file.

Its exit status is run.sh's: 0 when promptfoo received N graded runs and its report matches
the provider's record of them, 1 when the file lists a blocker.
"""

import argparse
import json
import pathlib
import re
import subprocess
import sys
from decimal import Decimal

sys.dont_write_bytecode = True  # importing provider.py must leave nothing in the repository
import provider  # noqa: E402

SUITE = "skills/story-to-done/evals/suite.py"
GRADER = f"{provider.CASE}/grader.py"
# The rule text of suite.py this file quotes; each line is looked up at the commit under test.
Q_OUTCOMES = 'OUTCOMES = {0: "pass", 1: "fail", 2: "void", None: "void"}'
Q_LOOP = 'while tally["n"] < runs and attempt < 2 * runs:'
Q_VOID = 'if record["outcome"] == "void":'
Q_COUNT = 'tally["n"] += 1'
Q_ERROR = 'outcome = OUTCOMES.get(code, "error")'
Q_BROKEN = 'raise Broken(f"{case_dir.name} {name} attempt {attempt}: {reason}; the case or the machine is broken")'
QUOTES = (Q_OUTCOMES, Q_LOOP, Q_VOID, Q_COUNT, Q_ERROR, Q_BROKEN)
PROVIDER_ERROR = re.compile(r"SKL317: call (\d+): ([a-zA-Z ]+)")
# The reason grade.py gives promptfoo, which copies it into a failed result's `error`.
ASSERTION_REASON = re.compile(r"attempt \d+: run\.sh exited \d+, a graded (?:pass|fail)")
COLUMNS = {"input": "Input tokens", "cache_read": "Cached input tokens", "cache_write": "Cache write tokens",
           "output": "Output tokens", "reasoning": "Reasoning tokens"}
NOT_REPORTED = "not reported"
NOT_EXERCISED = "not exercised in this run"


def usd(amount: Decimal) -> str:
    return f"{amount:.6f}"


def code(text: str) -> str:
    return f"`{text}`"


def table(head: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |" for row in rows]
    return lines


def git(checkout: pathlib.Path, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(checkout), *arguments], capture_output=True, text=True)


def promptfoo_results(path: pathlib.Path, problems: list[str]) -> tuple[dict, dict]:
    """promptfoo's export, and its results keyed by the provider call each one came from."""
    try:
        export = json.loads(path.read_text())
        results = export["results"]["results"]
    except (OSError, ValueError, KeyError, TypeError):
        problems.append("promptfoo wrote no export that can be read")
        return {}, {}
    by_call = {}
    for result in sorted(results, key=lambda result: result.get("repeatIndex", 0)):
        call = None
        try:
            call = json.loads(result["response"]["output"])["call"]
        except (ValueError, KeyError, TypeError):
            named = PROVIDER_ERROR.search(result.get("error") or "")
            if named:
                call = int(named.group(1))
        if call is None or call in by_call:
            problems.append("a promptfoo result names no provider call, or names one twice")
        else:
            by_call[call] = result
    return export, by_call


def reported(result: dict | None) -> str:
    """The fields promptfoo reports for one result, without its error text."""
    if result is None:
        return NOT_REPORTED
    error = "none"
    if result.get("error") and result.get("failureReason") == 1:
        named = ASSERTION_REASON.search(result["error"])
        error = f"the assertion's reason, {named.group(0)}" if named else "an assertion reason grade.py did not write"
    elif result.get("error"):
        named = PROVIDER_ERROR.search(result["error"])
        error = f"provider error, {named.group(2).strip()}" if named else "an error the provider did not name"
    usage = result.get("tokenUsage") or {}
    return (f"`success` {json.dumps(result.get('success'))}, `score` {result.get('score')}, "
            f"`failureReason` {result.get('failureReason')}, `error` {error}, "
            f"`tokenUsage.total` {usage.get('total')}, `cost` {result.get('cost')}")


def agrees(call: dict, result: dict | None) -> bool:
    """True when promptfoo's result is the one the provider's hand-back maps to."""
    if result is None:
        return False
    if call["handed"] == "pass":
        return result.get("success") is True and result.get("failureReason") == 0
    if call["handed"] == "fail":
        return result.get("success") is False and result.get("failureReason") == 1
    return result.get("success") is False and result.get("failureReason") == 2


def outcome_text(attempt: dict) -> str:
    text = {"pass": "graded pass", "fail": "graded fail", "void": "void", "error": "error (broken attempt)"}[attempt["outcome"]]
    return f"{text}, `injected`" if attempt["injected"] else text


def ledger_total(path: pathlib.Path) -> tuple[Decimal | None, int]:
    """What a ledger file adds up to, or None when it cannot be added up, and its attempts."""
    try:
        attempts = sum(entry["event"] == "start" for entry in provider.entries(path))
        return provider.spend(path)[0], attempts
    except (provider.Stop, OSError, ValueError, KeyError, TypeError):
        return None, 0


def rules(attempts: list[dict], calls: list[dict], stop: dict | None, graded_by_promptfoo: int, runs: int,
          present: dict, commit: str) -> list[str]:
    """The three suite.py rules: the quoted rule, what the provider did, and the status."""
    graded = [attempt for attempt in attempts if attempt["outcome"] in ("pass", "fail")]
    voids = [attempt for attempt in attempts if attempt["outcome"] == "void"]
    reason = stop["reason"] if stop else None
    last = attempts[-1]["attempt"] if attempts else 0
    later_calls = [call for call in calls if call["reason"] == provider.STOPPED_EARLIER]

    def quoted(*texts: str) -> str:
        return "; ".join(code(text) if present[text] else f"{code(text)} (not found at this commit)" for text in texts)

    def status(exercised: bool, held: bool, texts: tuple[str, ...], injected_only: bool = False) -> str:
        if not all(present[text] for text in texts):
            return "`differs`: suite.py at this commit does not hold the quoted text"
        if not exercised:
            return code(NOT_EXERCISED)
        if not held:
            return "`differs`"
        return "`reproduced` (`injected` void only, not a natural observation)" if injected_only else "`reproduced`"

    # (i) A void is absorbed when its own call went on to another attempt or the run stopped,
    # and promptfoo holds exactly as many graded results as the provider handed it.
    handed = sum(call["handed"] in ("pass", "fail") for call in calls)
    absorbed = all(any(other["attempt"] == void["attempt"] + 1 and other["call"] == void["call"] for other in attempts)
                   or (void["attempt"] == last and reason is not None) for void in voids)
    void_list = ", ".join(f"attempt {void['attempt']} (exit status {void['exit_status']}"
                          f"{', `injected`' if void['injected'] else ''})" for void in voids)
    seen_one = (f"Void: {void_list}. The provider counted none of them: it handed promptfoo {handed} graded results "
                f"from {len(graded)} graded attempts of {len(attempts)} attempts, and promptfoo holds "
                f"{graded_by_promptfoo} graded results and none for a void attempt." if voids else "No attempt was void.")
    # (ii) The cap is exercised only when it stopped the run: 2N attempts and fewer than N graded.
    capped = reason == provider.CAP
    seen_two = (f"After attempt {last} of {2 * runs} with {len(graded)} graded, the provider started no attempt and "
                f"handed promptfoo an error ({provider.CAP})." if capped
                else f"The run ended after {len(attempts)} attempts with {len(graded)} graded, so the cap of {2 * runs} "
                     f"attempts never stopped it.")
    # (iii) A broken attempt is exercised when one attempt had an exit status outside 0, 1 and 2.
    broken = [attempt for attempt in attempts if attempt["outcome"] == "error"]
    seen_three = "No attempt had an exit status outside 0, 1 and 2."
    if broken:
        seen_three = (f"Attempt {broken[0]['attempt']} exited {broken[0]['exit_status']}. The provider started no further "
                      f"attempt, handed promptfoo an error ({provider.BROKEN}) for that call and refused each of the "
                      f"{len(later_calls)} later calls promptfoo still made ({provider.STOPPED_EARLIER}). "
                      f"suite.py stops the whole suite and exits 1; promptfoo itself did not stop.")
    rows = [
        ["(i) void attempts do not count toward N",
         f"{quoted(Q_OUTCOMES)}; an attempt past its deadline is the `None` entry; in `tally_record`, {quoted(Q_VOID)} "
         f"returns before {quoted(Q_COUNT)}",
         seen_one,
         status(bool(voids), absorbed and graded_by_promptfoo == handed, (Q_OUTCOMES, Q_VOID, Q_COUNT),
                all(void["injected"] for void in voids))],
        ["(ii) the run stops at 2N attempts", quoted(Q_LOOP), seen_two,
         status(capped, len(attempts) == 2 * runs, (Q_LOOP,))],
        ["(iii) any other exit status stops the run",
         f"{quoted(Q_ERROR)}, so a status other than 0, 1 and 2 is `error`; then {quoted(Q_BROKEN)}, and the suite exits 1",
         seen_three,
         status(bool(broken), bool(broken) and broken[0]["attempt"] == last and reason == provider.BROKEN,
                (Q_ERROR, Q_BROKEN))],
    ]
    return table(["Rule", f"`{SUITE}` at `{commit}`", "Provider, observed in this run", "Status"], rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write compare.md for one run of the SKL-317 proof of concept.")
    for name in ("work", "ledger", "mode", "runs", "commit", "version", "eval-status", "dirty", "out"):
        parser.add_argument(f"--{name}", required=True)
    args = parser.parse_args()
    work, runs, eval_status = pathlib.Path(args.work), int(args.runs), int(args.eval_status)
    checkout = work / "checkout"
    problems: list[str] = []

    attempts = provider.entries(work / "state" / "attempts.jsonl")
    calls = provider.entries(work / "state" / "calls.jsonl")
    stop_file = work / "state" / "stop.json"
    stop = json.loads(stop_file.read_text()) if stop_file.is_file() else None
    export, by_call = promptfoo_results(work / "results.json", problems)
    graded = [attempt for attempt in attempts if attempt["outcome"] in ("pass", "fail")]
    graded_by_promptfoo = sum(result.get("failureReason") in (0, 1) for result in by_call.values())

    # Blockers: anything that keeps this run from being N graded runs promptfoo reported as such.
    if eval_status not in (0, 100):
        problems.append(f"promptfoo eval exited {eval_status}")
    if stop:
        detail = ""
        if stop["reason"] == provider.CEILING_REACHED:
            detail = (f": cumulative spend {usd(Decimal(stop['spent']))} USD + next-attempt estimate "
                      f"{usd(Decimal(stop['estimate']))} USD > ceiling {usd(provider.CEILING)} USD")
        problems.append(f"the provider stopped the run at call {stop['call']}: `{stop['reason']}`{detail}")
    if len(graded) != runs:
        problems.append(f"the run has {len(graded)} graded runs, not N = {runs}")
    if len(calls) != runs or len(by_call) != runs:
        problems.append(f"promptfoo made {len(calls)} provider calls and reported {len(by_call)} results for {runs} repeats")
    if any(not agrees(call, by_call.get(call["call"])) for call in calls):
        problems.append("a promptfoo result is not the one the provider's hand-back maps to")
    if export and export.get("metadata", {}).get("promptfooVersion") != args.version:
        problems.append(f"the export is not of promptfoo {args.version}")
    if any(attempt["usage"] is None for attempt in attempts):
        problems.append("the agent reported no token counts for an attempt, so its cost is unknown")
    live = [attempt for attempt in attempts if attempt["usage"] and attempt["usage"]["model"] not in
            (provider.NO_AGENT, provider.STUB_AGENT)]
    if any(attempt["usage"]["model"] != provider.MODEL for attempt in live):
        problems.append(f"an attempt ran on another model than {provider.MODEL}")
    if any(attempt["usage"]["subagent_calls"] for attempt in live):
        problems.append("an attempt called a subagent, whose tokens its counts leave out")
    suite_text = git(checkout, "show", f"HEAD:{SUITE}").stdout
    present = {text: text in suite_text for text in QUOTES}
    if not all(present.values()):
        problems.append(f"{SUITE} at the commit under test does not hold a rule text this file quotes")
    grader_blob = git(checkout, "rev-parse", f"HEAD:{GRADER}").stdout.strip()
    grader_same = git(checkout, "diff", "--quiet", "HEAD", "--", GRADER).returncode == 0
    if not grader_blob or not grader_same:
        problems.append("the grader the run used is not the committed grader.py")
    before, before_attempts = ledger_total(work / "ledger-before.jsonl")
    after, _ = ledger_total(pathlib.Path(args.ledger))
    if before is None or after is None:
        problems.append(f"the spend ledger cannot be added up: `{provider.SPEND_UNKNOWN}`")
    status = 1 if problems else 0

    # The attempts, one row each.
    final = {call["attempts"][-1]: call["call"] for call in calls if call["handed"] in ("pass", "fail") and call["attempts"]}
    rows = []
    for attempt in attempts:
        number = attempt["attempt"]
        if number in final:
            seen = reported(by_call.get(final[number]))
        elif attempt["outcome"] == "void":
            seen = f"{NOT_REPORTED} (absorbed by the provider)"
        else:
            seen = f"{NOT_REPORTED} (call {attempt['call']} was reported as an error, see Provider calls)"
        usage = attempt["usage"]
        counts = [str(usage["counts"][name]) if usage else NOT_REPORTED for name in COLUMNS]
        exit_status = "none (past its deadline)" if attempt["exit_status"] is None else str(attempt["exit_status"])
        rows.append([str(number), str(attempt["call"]), exit_status, outcome_text(attempt), seen, *counts,
                     usage["model"] if usage else NOT_REPORTED,
                     usd(Decimal(attempt["cost"])) if attempt["cost"] is not None else NOT_REPORTED])
    run_cost = sum((Decimal(attempt["cost"]) for attempt in attempts if attempt["cost"] is not None), Decimal(0))
    prices = ", ".join(f"{name} {provider.PRICES[name]}" for name in provider.COUNTS)

    lines = [
        "# SKL-317: one promptfoo run with the void retry in the provider",
        "",
        "Generated by `bash spikes/SKL-317/poc/run.sh`; do not edit it by hand.",
        "A stub run is a dry run: a stub agent stands in for the model, and the file is not written to the repository."
        if args.mode == "stub" else "This is the live run: each attempt that names a model id called that model.",
        "",
        "## Attempts",
        "",
        f"One row per attempt of the case's own `run.sh` for the scenario `{provider.SCENARIO}` of `{provider.CASE}`.",
        "The outcome uses the exit-status mapping quoted under Suite rules: 0 graded pass, 1 graded fail, 2 void, "
        "past the deadline void, anything else an error.",
        f"The cost is the token counts times the prices of `{provider.MODEL}` in US dollars per million tokens "
        f"({prices}), from {provider.PRICE_SOURCE}, read {provider.PRICE_DATE}.",
        "Input tokens leave out the cached ones, and the source lists no cache write price, so a cache write is "
        "charged as input.",
        "",
        *table(["Attempt", "Provider call", "Exit status of the case's `run.sh`", "Outcome", "What promptfoo reported",
                *COLUMNS.values(), "Model id", f"Cost in USD ({provider.PRICE_SOURCE}, {provider.PRICE_DATE})"], rows),
        "",
        f"- Overall exit status of `spikes/SKL-317/poc/run.sh`: {status}.",
        f"- agent-skills commit under test: `{args.commit}`"
        f"{' (a dry run of a working tree with changes that are not committed)' if args.dirty else ''}.",
        f"- promptfoo version: `{args.version}`.",
        f"- Model id: `{provider.MODEL}`" + (" (not called: stub run)." if args.mode == "stub" else "."),
        f"- Mode: {args.mode}.",
        f"- Graded runs wanted, N: {runs}; attempt cap, 2N: {2 * runs}; attempts run: {len(attempts)}; "
        f"graded: {len(graded)}.",
        f"- Grader: `{GRADER}`, blob `{grader_blob}` at the commit under test, "
        f"{'unmodified' if grader_same else 'MODIFIED'}; only the case's `run.sh` ran it, and it graded no void attempt.",
        "",
        "## Provider calls",
        "",
        "One row per call promptfoo made to the script provider.",
        "",
    ]
    call_rows = []
    for call in calls:
        handed = {"pass": "a graded pass", "fail": "a graded fail"}.get(call["handed"], f"an error: {call['reason']}")
        call_rows.append([str(call["call"]), ", ".join(str(number) for number in call["attempts"]) or "none", handed,
                          reported(by_call.get(call["call"]))])
    lines += table(["Call", "Attempts it ran", "Handed to promptfoo", "What promptfoo reported"], call_rows)
    options = export.get("runtimeOptions", {}) if export else {}
    stats = export.get("results", {}).get("stats", {}) if export else {}
    groups = export.get("results", {}).get("repeatStability", {}).get("groups", []) if export else []
    lines += [
        "",
        f"- promptfoo eval exit status: {eval_status}.",
        f"- promptfoo runtime options, from its export: `repeat` {options.get('repeat')}, "
        f"`maxConcurrency` {options.get('maxConcurrency')}, `cache` {json.dumps(options.get('cache'))}.",
        "- promptfoo's own retry: none. Version 0.125.1 has no retry count; its one retry is the `--retry-errors` "
        "flag of a later eval, which this run does not pass.",
        f"- Provider calls: {len(calls)} for {runs} repeats, so promptfoo repeated no call.",
        f"- promptfoo totals: `successes` {stats.get('successes')}, `failures` {stats.get('failures')}, "
        f"`errors` {stats.get('errors')}, `tokenUsage.total` {stats.get('tokenUsage', {}).get('total')}.",
    ]
    if groups:
        lines.append(f"- promptfoo repeat group: `repetitions` {groups[0].get('repetitions')}, `passed` {groups[0].get('passed')}, "
                     f"`failed` {groups[0].get('failed')}, `errors` {groups[0].get('errors')}, `passRate` {json.dumps(groups[0].get('passRate'))}.")
    lines += [
        "",
        "## Suite rules",
        "",
        "Each quoted line was looked up in the file at the commit under test.",
        "",
        *rules(attempts, calls, stop, graded_by_promptfoo, runs, present, args.commit),
        "",
        "## Spend",
        "",
        f"- Ceiling for the whole spike: {usd(provider.CEILING)} USD.",
        f"- Before each attempt the provider adds up the ledger and stops with `{provider.CEILING_REACHED}` when the total "
        f"plus the next-attempt estimate is over the ceiling; the estimate is {usd(provider.FIRST_ESTIMATE)} USD, or the "
        "highest cost of a single attempt so far when that is more.",
    ]
    if before is not None and after is not None:
        sums = " + ".join(usd(Decimal(attempt["cost"])) for attempt in attempts if attempt["cost"] is not None)
        lines += [
            f"- Ledger before this run, development and dry runs included: {usd(before)} USD over {before_attempts} attempts.",
            f"- This run: {sums} = {usd(run_cost)} USD." if sums else f"- This run: no attempt ran, {usd(run_cost)} USD.",
            f"- Ledger after this run: {usd(before)} + {usd(after - before)} = {usd(after)} USD, "
            f"which leaves {usd(provider.CEILING - after)} USD under the ceiling.",
        ]
    lines += ["", "## Blockers", ""]
    if problems:
        lines += ["No result is claimed for this run."] + [f"- {problem[0].upper()}{problem[1:]}." for problem in problems]
    else:
        lines.append("None.")
    pathlib.Path(args.out).write_text("\n".join(lines) + "\n")
    return status


if __name__ == "__main__":
    sys.exit(main())
