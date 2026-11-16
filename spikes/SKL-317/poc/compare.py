#!/usr/bin/env python3
"""Write compare.md for one run of the SKL-317 proof of concept; run.sh calls it last.

It reads what the provider recorded (attempts, calls, a stop), promptfoo's JSON export, the
spend ledger before and after the run with the provider's own copy of it, and suite.py at the
commit under test, and writes one Markdown file of tables. It copies fields only: an exit
status, an outcome, a count, a model id, a fixed reason. No path, session id, prompt text,
agent output or error text of promptfoo reaches the file.

It is also the check of the run, and each check that fails is a blocker the file lists:

- the provider's record is one run under suite.py's rules: attempts numbered in order and no
  more than 2 x N of them, each outcome the one suite.py gives its exit status, each call a
  row of void attempts and then one hand-back;
- promptfoo's export reports that record: one result per repeat, each carrying the attempt its
  call handed back with the success, score, failure reason and error that attempt maps to, the
  runtime options run.sh asked for, and totals that count the same hand-backs;
- the spend follows: each cost is its token counts times the prices, the ledger is the
  provider's own copy of it, and what it gained is a start and an end row per attempt.

Its exit status is run.sh's: 0 when promptfoo received N graded runs and no check failed, 1
when the file lists a blocker.
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

SUITE = provider.SUITE
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
# What a record or an export that was not written as this file expects raises when read.
UNREADABLE = (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, ArithmeticError)
COLUMNS = {"input": "Input tokens", "cache_read": "Cached input tokens", "cache_write": "Cache write tokens",
           "output": "Output tokens", "reasoning": "Reasoning tokens"}
OUTCOME_TEXT = {"pass": "graded pass", "fail": "graded fail", "void": "void", "error": "error (broken attempt)"}
NOT_REPORTED = "not reported"
NOT_EXERCISED = "not exercised in this run"


def usd(amount: Decimal) -> str:
    """An amount in full, with six decimals or as many more as it has: nothing is rounded."""
    whole, _, fraction = format(amount.normalize(), "f").partition(".")
    return f"{whole}.{fraction.ljust(6, '0')}"


def code(text: str) -> str:
    return f"`{text}`"


def table(head: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |" for row in rows]
    return lines


def git(checkout: pathlib.Path, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(checkout), *arguments], capture_output=True, text=True)


def field(holder: object, *keys: str | int) -> str:
    """The number, boolean or null an export holds under KEYS, as JSON; anything else is not copied."""
    try:
        for key in keys:
            holder = holder[key]
    except UNREADABLE:
        return NOT_REPORTED
    return json.dumps(holder) if holder is None or type(holder) in (int, float, bool) else "unreadable"


def error_text(result: dict) -> str:
    """A result's `error`: its text, nothing when it has none, and a marker when it is no text."""
    error = result.get("error")
    if error is None or isinstance(error, str):
        return error or ""
    return "unreadable"


def readable(attempts: list[dict], calls: list[dict], stop: dict | None) -> None:
    """Raise unless every field this file copies is there, with the type the provider writes."""
    def whole(value: object) -> bool:
        return type(value) is int and value >= 0

    for attempt in attempts:
        usage, cost = attempt["usage"], attempt["cost"]
        fine = (whole(attempt["attempt"]) and whole(attempt["call"]) and attempt["outcome"] in OUTCOME_TEXT
                and type(attempt["injected"]) is bool and (attempt["exit_status"] is None or type(attempt["exit_status"]) is int)
                and (cost is None or (isinstance(cost, str) and Decimal(cost) >= 0))
                and (usage is None or (set(usage["counts"]) == set(provider.COUNTS) and isinstance(usage["model"], str)
                                       and all(whole(count) for count in usage["counts"].values())
                                       and whole(usage["subagent_calls"]))))
        if not fine:
            raise ValueError("attempt")
    for call in calls:
        fine = (whole(call["call"]) and type(call["attempts"]) is list and all(whole(number) for number in call["attempts"])
                and call["handed"] in ("pass", "fail", "error") and (call["reason"] is None or call["reason"] in provider.REASONS))
        if not fine:
            raise ValueError("call")
    if stop is not None:
        if not whole(stop["call"]) or stop["reason"] not in provider.REASONS:
            raise ValueError("stop")
        if stop["reason"] == provider.CEILING_REACHED and not (Decimal(stop["spent"]) >= 0 and Decimal(stop["estimate"]) >= 0):
            raise ValueError("stop")


def record_problems(attempts: list[dict], calls: list[dict], runs: int, inject: int, mode: str,
                    outcomes: dict | None) -> list[str]:
    """What keeps the provider's own record from being one run under suite.py's rules."""
    problems = []
    numbers = [attempt["attempt"] for attempt in attempts]
    if numbers != list(range(1, len(attempts) + 1)):
        problems.append("the attempts are not numbered 1, 2, 3 and so on, once each")
    if len(attempts) > 2 * runs:
        problems.append(f"the run has {len(attempts)} attempts, over the cap of 2N = {2 * runs}")
    if outcomes is not None and any(attempt["outcome"] != outcomes.get(attempt["exit_status"], "error")
                                    for attempt in attempts):
        problems.append("an attempt's outcome is not the one suite.py gives its exit status")
    if any(attempt["injected"] != (attempt["attempt"] == inject) for attempt in attempts):
        problems.append("the `injected` label is not on the one attempt the run injects a void for, and only there")
    for attempt in attempts:
        usage = attempt["usage"]
        if (usage is None) != (attempt["cost"] is None):
            problems.append("an attempt has a cost without token counts, or token counts without a cost")
        elif usage is not None:
            ran_model = mode == "live" and not attempt["injected"]
            if not ran_model and usage["model"] != (provider.STUB_AGENT if mode == "stub" else provider.NO_AGENT):
                problems.append("an attempt that ran no model names one")
            if ran_model != any(usage["counts"].values()):
                problems.append("an attempt that ran no model has token counts, or one that ran the model has none")
            if Decimal(attempt["cost"]) != provider.cost_of(usage["counts"]):
                problems.append("an attempt's cost is not its token counts times the prices")
    if [call["call"] for call in calls] != list(range(1, len(calls) + 1)):
        problems.append("the provider calls are not numbered 1, 2, 3 and so on, once each")
    by_number = {attempt["attempt"]: attempt for attempt in attempts}
    if [number for call in calls for number in call["attempts"]] != numbers or any(
            by_number[number]["call"] != call["call"] for call in calls for number in call["attempts"] if number in by_number):
        problems.append("the calls do not list every attempt once, in order, under the call that ran it")
    for call in calls:
        ran = [by_number[number] for number in call["attempts"] if number in by_number]
        if any(attempt["outcome"] != "void" for attempt in ran[:-1]):
            problems.append("a call ran another attempt after one that was not void")
        if call["handed"] in ("pass", "fail"):
            handed = bool(ran) and ran[-1]["outcome"] == call["handed"] and call["reason"] is None
        else:
            handed = call["reason"] is not None
        if not handed:
            problems.append("a call did not hand promptfoo the outcome of its last attempt, or an error with its reason")
    return sorted(set(problems), key=problems.index)


def promptfoo_results(path: pathlib.Path, runs: int, problems: list[str]) -> tuple[dict, dict]:
    """promptfoo's export, and its results keyed by the provider call each one came from.

    One provider call runs at a time, so the result of repeat r (`repeatIndex` r, from 0) is
    the one promptfoo holds for provider call r + 1.
    """
    try:
        export = json.loads(path.read_text())
        results = export["results"]["results"]
        repeats = sorted(result["repeatIndex"] for result in results if type(result.get("repeatIndex")) is int)
        if len(repeats) != len(results):
            raise ValueError("repeatIndex")
    except UNREADABLE:
        problems.append("the export promptfoo wrote cannot be read")
        return {}, {}
    if repeats != list(range(runs)):
        problems.append(f"the results in the export are not one per repeat, with `repeatIndex` 0 to {runs - 1}")
        return export, {}
    return export, {result["repeatIndex"] + 1: result for result in results}


def payload(result: dict) -> object:
    """The JSON line the provider printed, as promptfoo holds it, or None."""
    try:
        output = result["response"]["output"]
        return json.loads(output) if isinstance(output, str) else output
    except UNREADABLE:
        return None


def agrees(call: dict, last: dict | None, result: dict | None) -> bool:
    """True when promptfoo's result is the one the provider's hand-back maps to.

    LAST is the last attempt the call ran. A graded hand-back carries that attempt and the
    success, score, failure reason and error grade.py gives it; an error carries no output and
    names the call and the provider's reason, and nothing else of the provider.
    """
    if result is None:
        return False
    error = error_text(result)
    if call["handed"] in ("pass", "fail"):
        if last is None:
            return False
        printed = {"call": call["call"], "attempt": last["attempt"], "runner_exit_status": last["exit_status"],
                   "outcome": last["outcome"]}
        reason = f"attempt {last['attempt']}: run.sh exited {last['exit_status']}, a graded {last['outcome']}"
        if payload(result) != printed:
            return False
        if call["handed"] == "pass":
            return result.get("success") is True and result.get("score") == 1 and result.get("failureReason") == 0 \
                and not error
        return result.get("success") is False and result.get("score") == 0 and result.get("failureReason") == 1 \
            and error == reason
    named = {(int(number), reason.strip()) for number, reason in PROVIDER_ERROR.findall(error)}
    return result.get("success") is False and result.get("score") == 0 and result.get("failureReason") == 2 \
        and payload(result) is None and named == {(call["call"], call["reason"])}


def export_problems(export: dict, by_call: dict, calls: list[dict], attempts: list[dict], runs: int,
                    version: str) -> list[str]:
    """What keeps promptfoo's export from reporting the provider's record of this run."""
    problems = []
    by_number = {attempt["attempt"]: attempt for attempt in attempts}
    last = {call["call"]: by_number.get(call["attempts"][-1]) if call["attempts"] else None for call in calls}
    if any(not agrees(call, last[call["call"]], by_call.get(call["call"])) for call in calls):
        problems.append("a promptfoo result is not the one the provider's hand-back maps to: the attempt it carries, "
                        "or its `success`, `score`, `failureReason` or `error`, differs")
    if export.get("metadata", {}).get("promptfooVersion") != version:
        problems.append(f"the export is not of promptfoo {version}")
    options = export.get("runtimeOptions") or {}
    if type(options.get("repeat")) is not int or options.get("repeat") != runs \
            or type(options.get("maxConcurrency")) is not int or options.get("maxConcurrency") != 1 \
            or options.get("cache") is not False:
        problems.append(f"the runtime options in the export are not `repeat` {runs}, `maxConcurrency` 1 and `cache` false")
    handed = {kind: sum(call["handed"] == kind for call in calls) for kind in ("pass", "fail", "error")}
    stats = export.get("results", {}).get("stats") or {}
    if (stats.get("successes"), stats.get("failures"), stats.get("errors")) != (handed["pass"], handed["fail"], handed["error"]):
        problems.append("the totals in the export do not count the passes, fails and errors the provider handed promptfoo")
    groups = (export.get("results", {}).get("repeatStability") or {}).get("groups") or []
    if len(groups) != 1 or (groups[0].get("repetitions"), groups[0].get("passed"), groups[0].get("failed"),
                            groups[0].get("errors")) != (runs, handed["pass"], handed["fail"], handed["error"]):
        problems.append("the repeat group in the export does not count the passes, fails and errors the provider handed promptfoo")
    return problems


def ledger_rows(work: pathlib.Path, ledger: pathlib.Path, run_id: str, mode: str, attempts: list[dict]) -> list[str]:
    """What keeps the ledger from being the ledger before the run plus this run's rows."""
    try:
        before = (work / "ledger-before.jsonl").read_bytes()
        mirror = (work / "ledger-mirror.jsonl").read_bytes()
        current = ledger.read_bytes()
    except OSError:
        return ["the spend ledger, or the provider's copy of it, cannot be read"]
    problems = []
    if current != mirror:
        problems.append(f"the spend ledger is not the provider's own copy of it: `{provider.LEDGER_CHANGED}`")
    if not mirror.startswith(before):
        return problems + ["the provider's copy of the ledger does not begin with the ledger as it was before the run"]
    try:
        added = [json.loads(line) for line in mirror[len(before):].decode().splitlines() if line.strip()]
        found = [(row["run"], row["attempt"], row["mode"], row["event"],
                  row["cost"] if row["event"] == "end" else Decimal(row["reserved"]) >= 0) for row in added]
        if any("at" not in row for row in added):
            raise KeyError("at")
    except UNREADABLE:
        found = None
    wanted = [row for attempt in attempts for row in ((run_id, attempt["attempt"], mode, "start", True),
                                                       (run_id, attempt["attempt"], mode, "end", attempt["cost"]))]
    if found != wanted:
        problems.append("the rows this run added to the ledger are not a start and an end for each attempt, with its cost")
    return problems


def reported(result: dict | None) -> str:
    """The fields promptfoo reports for one result, without its error text."""
    if result is None:
        return NOT_REPORTED
    error, text = "none", error_text(result)
    if text and result.get("failureReason") == 1:
        named = ASSERTION_REASON.fullmatch(text)
        error = f"the assertion's reason, {named.group(0)}" if named else "an assertion reason grade.py did not write"
    elif text:
        named = PROVIDER_ERROR.search(text)
        error = f"provider error, {named.group(2).strip()}" if named and named.group(2).strip() in provider.REASONS \
            else "an error the provider did not name"
    return (f"`success` {field(result, 'success')}, `score` {field(result, 'score')}, "
            f"`failureReason` {field(result, 'failureReason')}, `error` {error}, "
            f"`tokenUsage.total` {field(result, 'tokenUsage', 'total')}, `cost` {field(result, 'cost')}")


def outcome_text(attempt: dict) -> str:
    text = OUTCOME_TEXT[attempt["outcome"]]
    return f"{text}, `injected`" if attempt["injected"] else text


def ledger_total(path: pathlib.Path) -> tuple[Decimal | None, int]:
    """What a ledger file adds up to, or None when it cannot be added up, and its attempts."""
    try:
        attempts = sum(entry["event"] == "start" for entry in provider.entries(path))
        return provider.spend_of(path)[0], attempts
    except (provider.Stop, *UNREADABLE):
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
    for name in ("work", "checkout", "ledger", "run-id", "mode", "runs", "inject", "commit", "version", "eval-status",
                 "dirty", "changed", "out"):
        parser.add_argument(f"--{name}", required=True)
    args = parser.parse_args()
    work, runs, eval_status = pathlib.Path(args.work), int(args.runs), int(args.eval_status)
    checkout = pathlib.Path(args.checkout)
    problems: list[str] = []

    # suite.py's rules at the commit under test: the outcome table and the quoted rule text.
    suite_text = git(checkout, "show", f"HEAD:{SUITE}").stdout
    present = {text: text in suite_text for text in QUOTES}
    try:
        outcomes = provider.suite_rules(checkout)[0]
    except provider.Stop:
        outcomes = None

    # The provider's record. One that cannot be read as written is a blocker, and nothing of it is reported.
    stop_file = work / "state" / "stop.json"
    try:
        attempts = provider.entries(work / "state" / "attempts.jsonl")
        calls = provider.entries(work / "state" / "calls.jsonl")
        stop = json.loads(stop_file.read_text()) if stop_file.is_file() else None
        readable(attempts, calls, stop)
        record = record_problems(attempts, calls, runs, int(args.inject), args.mode, outcomes)
    except UNREADABLE:
        attempts, calls, stop, record = [], [], None, ["the provider's record of the run cannot be read"]
    export, by_call = promptfoo_results(work / "results.json", runs, problems)
    graded = [attempt for attempt in attempts if attempt["outcome"] in ("pass", "fail")]
    graded_by_promptfoo = sum(result.get("failureReason") in (0, 1) for result in by_call.values())

    # Blockers: anything that keeps this run from being N graded runs promptfoo reported as such.
    if eval_status not in (0, 100):
        problems.append(f"the promptfoo eval exited {eval_status}")
    if stop:
        detail = ""
        if stop["reason"] == provider.CEILING_REACHED:
            detail = (f": cumulative spend {usd(Decimal(stop['spent']))} USD + next-attempt estimate "
                      f"{usd(Decimal(stop['estimate']))} USD > ceiling {usd(provider.CEILING)} USD")
        problems.append(f"the provider stopped the run at call {stop['call']}: `{stop['reason']}`{detail}")
    problems += record
    if len(graded) != runs:
        problems.append(f"the run has {len(graded)} graded runs, not N = {runs}")
    if len(calls) != runs:
        problems.append(f"the eval made {len(calls)} provider calls for {runs} repeats")
    if export:
        try:
            problems += export_problems(export, by_call, calls, attempts, runs, args.version)
        except UNREADABLE:
            problems.append("the export promptfoo wrote cannot be read")
    if any(attempt["usage"] is None for attempt in attempts):
        problems.append("the agent reported no token counts for an attempt, so its cost is unknown")
    live = [attempt for attempt in attempts if attempt["usage"] and args.mode == "live" and not attempt["injected"]]
    if any(attempt["usage"]["model"] != provider.MODEL for attempt in live):
        problems.append(f"an attempt ran on another model than {provider.MODEL}")
    if any(attempt["usage"]["subagent_calls"] for attempt in live):
        problems.append("an attempt called a subagent, whose tokens its counts leave out")
    if not all(present.values()):
        problems.append(f"the commit under test does not hold, in `{SUITE}`, a rule text this file quotes")
    if outcomes is None:
        problems.append(f"the commit under test holds, in `{SUITE}`, no outcome table this run can read")
    # The clone the attempts ran in is the commit named, as committed: the case's run.sh, the
    # grader and the skill the agent read.
    grader_blob = git(checkout, "rev-parse", f"HEAD:{GRADER}").stdout.strip()
    clone_status = git(checkout, "status", "--porcelain", "--untracked-files=all")
    clone_same = (git(checkout, "rev-parse", "HEAD").stdout.strip() == args.commit
                  and clone_status.returncode == 0 and not clone_status.stdout.strip())
    if not grader_blob or not clone_same:
        problems.append("the clone the attempts ran in is not the commit under test as committed, so neither is its grader.py")
    if args.changed:
        problems.append("the repository's commit or working tree changed while the run was under way")
    problems += ledger_rows(work, pathlib.Path(args.ledger), args.run_id, args.mode, attempts)
    before, before_attempts = ledger_total(work / "ledger-before.jsonl")
    after, _ = ledger_total(pathlib.Path(args.ledger))
    run_cost = sum((Decimal(attempt["cost"]) for attempt in attempts if attempt["cost"] is not None), Decimal(0))
    if before is None or after is None:
        problems.append(f"the spend ledger cannot be added up: `{provider.SPEND_UNKNOWN}`")
    elif after - before != run_cost:
        problems.append(f"the ledger gained {usd(after - before)} USD in this run, and its attempts cost {usd(run_cost)} USD")
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
        f"{'unmodified' if clone_same else 'NOT as committed'}; only the case's `run.sh` ran it, and it graded no void attempt.",
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
    group = ("results", "repeatStability", "groups", 0)
    lines += [
        "",
        f"- promptfoo eval exit status: {eval_status}.",
        f"- promptfoo runtime options, from its export: `repeat` {field(export, 'runtimeOptions', 'repeat')}, "
        f"`maxConcurrency` {field(export, 'runtimeOptions', 'maxConcurrency')}, "
        f"`cache` {field(export, 'runtimeOptions', 'cache')}.",
        "- promptfoo's own retry: none. Version 0.125.1 has no retry count; its one retry is the `--retry-errors` "
        "flag of a later eval, which this run does not pass.",
        f"- Provider calls: {len(calls)} for {runs} repeats" + (", so promptfoo repeated no call." if len(calls) == runs else "."),
        f"- promptfoo totals: `successes` {field(export, 'results', 'stats', 'successes')}, "
        f"`failures` {field(export, 'results', 'stats', 'failures')}, `errors` {field(export, 'results', 'stats', 'errors')}, "
        f"`tokenUsage.total` {field(export, 'results', 'stats', 'tokenUsage', 'total')}.",
        f"- promptfoo repeat group: `repetitions` {field(export, *group, 'repetitions')}, "
        f"`passed` {field(export, *group, 'passed')}, `failed` {field(export, *group, 'failed')}, "
        f"`errors` {field(export, *group, 'errors')}, `passRate` {field(export, *group, 'passRate')}.",
    ]
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
        f"- The provider writes each ledger row to a copy of its own as well, in a directory the agent under test is "
        f"not told of, and stops with `{provider.LEDGER_CHANGED}` when the ledger is not that copy before or after an attempt.",
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
