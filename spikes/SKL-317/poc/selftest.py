#!/usr/bin/env python3
"""Check the proof of concept's own rules, without promptfoo, Node.js, the network or a model.

  python3 spikes/SKL-317/poc/selftest.py

It does what promptfoo does in `run.sh` (call provider.py once per repeat, hand a graded line
to grade.py, write an export with the fields promptfoo 0.125.1 writes) and then runs compare.py
on the result, in a clone of this commit with a throwaway ledger:

- dry runs through the stub agent: the injected void, the cap of 2 x N attempts, a broken
  attempt, graded fails, the spend ceiling, and a ledger changed between two calls;
- the live path with a stand-in for `opencode` that calls no model: the cost of an attempt
  from its token counts, another model, a subagent call, no token counts, and an agent that
  rewrites the ledger during its attempt;
- one change at a time to a finished run's record, export or ledger, each of which compare.py
  must list as a blocker and exit 1;
- what run.sh refuses before it creates anything: a pre-release Node.js, a ledger that is not
  named, not there or in the repository, a duration that is no whole number of seconds;
- the reading of suite.py's outcome table and durations, and an amount below a millionth of a
  dollar.

It does not run promptfoo, so the install, promptfoo itself and the export it really writes are
checked only by `run.sh`. The repository's test job collects `tests/` only, and the spike keeps
every tracked change under `spikes/SKL-317/`, so this file is run by hand: it exits 0 when
every check holds and 1, naming the check, when one does not. It writes under a temporary
directory only.
"""

import dataclasses
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal

sys.dont_write_bytecode = True  # importing the scripts must leave nothing in the repository
import compare  # noqa: E402
import grade  # noqa: E402
import provider  # noqa: E402

POC = provider.POC
RUNS = 3
# Stands where the promptfoo version does, in the export and in what compare.py is told.
VERSION = "selftest"
# The token counts the stand-in for opencode reports for a session.
COUNTS = {"input": 12000, "cache_read": 30000, "cache_write": 0, "output": 800, "reasoning": 400}
OPENCODE = '''#!/usr/bin/env python3
"""Stand-in for opencode in the SKL-317 self-test: no model is called."""
import json
import os
import pathlib
import sys

here = pathlib.Path(__file__).resolve().parent
plan = json.loads((here / "plan.json").read_text())
arguments = sys.argv[1:]
if arguments[:1] == ["run"]:
    with (here / "titles").open("a") as titles:
        titles.write(arguments[arguments.index("--title") + 1] + "\\n")
    if plan["rewrite"]:
        pathlib.Path(plan["rewrite"]).write_text("")
    prompt = arguments[arguments.index("--file") + 1]
    os.execv(sys.executable, [sys.executable, plan["agent"], "pass", "--file", prompt])
elif arguments[:2] == ["session", "list"]:
    titles = (here / "titles").read_text().split()
    print(json.dumps([{"id": f"ses_{number}", "title": title} for number, title in enumerate(titles)]))
elif arguments[:2] == ["session", "export"]:
    print(json.dumps(plan["export"]))
else:
    sys.exit(64)
'''


@dataclasses.dataclass
class Run:
    """One run as run.sh leaves it: HOME holds work/, arena/ and ledger.jsonl."""
    home: pathlib.Path
    run_id: str
    mode: str
    inject: int
    eval_status: int

    @property
    def work(self) -> pathlib.Path:
        return self.home / "work"

    @property
    def ledger(self) -> pathlib.Path:
        return self.home / "ledger.jsonl"

    def state(self, name: str) -> list[dict]:
        return provider.entries(self.work / "state" / f"{name}.jsonl")

    def stopped(self) -> str | None:
        stop = self.work / "state" / "stop.json"
        return json.loads(stop.read_text())["reason"] if stop.is_file() else None

    def reasons(self) -> list[str | None]:
        return [call["reason"] for call in self.state("calls")]


def git(directory: pathlib.Path, *arguments: str) -> str:
    return subprocess.run(["git", "-C", str(directory), *arguments], check=True, capture_output=True, text=True).stdout.strip()


def session(model: str = provider.MODEL, counts: dict = COUNTS, tools: tuple[str, ...] = ("shell",)) -> dict:
    """A session export with the fields provider.py reads from `opencode session export`."""
    provider_id, _, model_id = model.partition("/")
    return {"info": {"tokens": {"input": counts["input"], "output": counts["output"], "reasoning": counts["reasoning"],
                                "cache": {"read": counts["cache_read"], "write": counts["cache_write"]}},
                     "model": {"providerID": provider_id, "id": model_id}},
            "messages": [{"content": [{"type": "tool", "name": name} for name in tools]}]}


def result(repeat: int, done: subprocess.CompletedProcess) -> dict:
    """What promptfoo 0.125.1 holds for one call of the script provider."""
    row = {"repeatIndex": repeat, "cost": 0, "tokenUsage": {"total": 0}}
    if done.returncode:
        return {**row, "success": False, "score": 0, "failureReason": 2,
                "error": f"Error: Command failed: python3 provider.py\n{done.stderr}"}
    graded = grade.get_assert(done.stdout, {})
    row.update(success=graded["pass"], score=graded["score"], failureReason=0 if graded["pass"] else 1,
               response={"output": done.stdout.strip()})
    if not graded["pass"]:
        row["error"] = graded["reason"]
    return row


def export(results: list[dict]) -> dict:
    passed, failed, errors = (sum(row["failureReason"] == reason for row in results) for reason in (0, 1, 2))
    return {"metadata": {"promptfooVersion": VERSION},
            "runtimeOptions": {"repeat": RUNS, "maxConcurrency": 1, "cache": False},
            "results": {"stats": {"successes": passed, "failures": failed, "errors": errors, "tokenUsage": {"total": 0}},
                        "repeatStability": {"groups": [{"repetitions": RUNS, "passed": passed, "failed": failed,
                                                        "errors": errors,
                                                        "passRate": passed / (passed + failed) if passed + failed else 0}]},
                        "results": results}}


def edit_lines(path: pathlib.Path, change) -> None:
    rows = provider.entries(path)
    change(rows)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def edit_json(path: pathlib.Path, change) -> None:
    document = json.loads(path.read_text())
    change(document)
    path.write_text(json.dumps(document))


def blockers(text: str) -> str:
    return text.partition("## Blockers")[2]


def rule(text: str, number: str) -> str:
    """The status cell of one row of the Suite rules table."""
    rows = [line for line in text.splitlines() if line.startswith(f"| ({number}) ")]
    return rows[0].rstrip(" |").rpartition(" | ")[2] if len(rows) == 1 else ""


def main() -> int:
    failed = []

    def check(name: str, holds: bool) -> None:
        print(f"{'ok  ' if holds else 'FAIL'} {name}", flush=True)
        if not holds:
            failed.append(name)

    with tempfile.TemporaryDirectory(prefix="skl317-selftest.") as scratch:
        scratch = pathlib.Path(scratch).resolve()
        root = pathlib.Path(git(POC, "rev-parse", "--show-toplevel"))
        commit = git(root, "rev-parse", "HEAD")
        clone = scratch / "clone"
        git(root, "clone", "--quiet", "--no-checkout", str(root), str(clone))
        git(clone, "checkout", "--quiet", "--detach", commit)
        git(clone, "remote", "remove", "origin")
        stand_in = scratch / "opencode"
        stand_in.mkdir()
        (stand_in / "opencode").write_text(OPENCODE)
        (stand_in / "opencode").chmod(0o755)

        def drive(name: str, mode: str = "stub", plan: str = "", inject: int = 0, seed: str = "", more: dict | None = None,
                  before_call=None, exported: dict | None = None, rewrite: bool = False) -> Run:
            """One run with promptfoo's part done here: N calls of the provider, one at a time."""
            run = Run(scratch / name, name, mode, inject, 0)
            (run.home / "arena" / "tmp").mkdir(parents=True)
            run.work.mkdir()
            run.ledger.write_text(seed)
            for copy in ("ledger-before.jsonl", "ledger-mirror.jsonl"):
                shutil.copy(run.ledger, run.work / copy)
            env = {key: os.environ[key] for key in ("PATH", "HOME", "LANG") if key in os.environ}
            env.update(SKL317_WORK=str(run.work), SKL317_ARENA=str(run.home / "arena"), SKL317_CHECKOUT=str(clone),
                       SKL317_SPEND_LEDGER=str(run.ledger), SKL317_RUN_ID=name, SKL317_MODE=mode, SKL317_RUNS=str(RUNS),
                       SKL317_INJECT_VOID_ATTEMPT=str(inject), SKL317_STUB_PLAN=plan, PYTHONDONTWRITEBYTECODE="1",
                       **(more or {}))
            if mode == "live":
                env["PATH"] = f"{stand_in}{os.pathsep}{env['PATH']}"
                (stand_in / "titles").write_text("")
                (stand_in / "plan.json").write_text(json.dumps({
                    "export": exported, "agent": str(POC / "stub_agent.py"), "rewrite": str(run.ledger) if rewrite else None}))
            results = []
            for repeat in range(RUNS):
                if before_call:
                    before_call(repeat + 1, run)
                results.append(result(repeat, subprocess.run(
                    [sys.executable, str(POC / "provider.py"), provider.SCENARIO, "{}", "{}"], cwd=POC, env=env,
                    stdin=subprocess.DEVNULL, capture_output=True, text=True)))
            (run.work / "results.json").write_text(json.dumps(export(results)))
            run.eval_status = 0 if all(row["success"] for row in results) else 100
            return run

        def report(run: Run) -> tuple[int, str]:
            """What compare.py makes of a run: its exit status and the compare.md it wrote."""
            out = run.home / "compare.md"
            done = subprocess.run(
                [sys.executable, str(POC / "compare.py"), "--work", str(run.work), "--checkout", str(clone),
                 "--ledger", str(run.ledger), "--run-id", run.run_id, "--mode", run.mode, "--runs", str(RUNS),
                 "--inject", str(run.inject), "--commit", commit, "--version", VERSION,
                 "--eval-status", str(run.eval_status), "--dirty", "", "--changed", "", "--out", str(out)],
                cwd=POC, capture_output=True, text=True)
            return done.returncode, out.read_text() if out.is_file() else ""

        # Dry runs through the stub agent.
        base = drive("dry", inject=2)
        status, text = report(base)
        attempts = base.state("attempts")
        check("a dry run with the injected void exits 0 and lists no blocker",
              status == 0 and blockers(text).strip() == "None.")
        check("its void is attempt 2, labelled injected, absorbed inside call 2",
              [attempt["outcome"] for attempt in attempts] == ["pass", "void", "pass", "pass"]
              and [attempt["injected"] for attempt in attempts] == [False, True, False, False]
              and [call["attempts"] for call in base.state("calls")] == [[1], [2, 3], [4]]
              and rule(text, "i").startswith("`reproduced` (`injected` void only"))
        check("the ledger gained a start and an end row per attempt and is the provider's copy of it",
              len(provider.entries(base.ledger)) == 8
              and base.ledger.read_bytes() == (base.work / "ledger-mirror.jsonl").read_bytes())

        run = drive("cap", plan="void,void,void,void,void,void")
        status, text = report(run)
        check("six void attempts stop the run at the cap of 2N, and no seventh attempt starts",
              status == 1 and len(run.state("attempts")) == 6 and run.stopped() == provider.CAP
              and run.reasons() == [provider.CAP, provider.STOPPED_EARLIER, provider.STOPPED_EARLIER]
              and rule(text, "ii") == "`reproduced`")

        run = drive("broken", plan="pass,void,broken")
        status, text = report(run)
        check("an exit status outside 0, 1 and 2 stops the run, and each later call is refused",
              status == 1 and len(run.state("attempts")) == 3 and run.stopped() == provider.BROKEN
              and run.reasons() == [None, provider.BROKEN, provider.STOPPED_EARLIER] and rule(text, "iii") == "`reproduced`")

        run = drive("fails", plan="fail,pass,fail")
        status, text = report(run)
        check("graded fails are graded runs: the run exits 0 with two failures",
              status == 0 and blockers(text).strip() == "None."
              and [call["handed"] for call in run.state("calls")] == ["fail", "pass", "fail"])

        earlier = "".join(
            json.dumps({"at": "2026-01-01T00:00:00Z", "run": "earlier", "attempt": number, "mode": "live", **row}) + "\n"
            for number in range(1, 11) for row in ({"event": "start", "reserved": "0.08"}, {"event": "end", "cost": "0.093"}))
        run = drive("ceiling", inject=2, seed=earlier)
        status, text = report(run)
        check("a ledger at 0.93 USD with attempts of 0.093 USD stops the run before any attempt: ceiling reached",
              status == 1 and run.state("attempts") == [] and run.stopped() == provider.CEILING_REACHED
              and run.ledger.read_text() == earlier
              and "cumulative spend 0.930000 USD + next-attempt estimate 0.093000 USD > ceiling 1.000000 USD" in blockers(text))

        def emptied_before_call_two(call: int, run: Run) -> None:
            if call == 2:
                run.ledger.write_text("")

        run = drive("between", before_call=emptied_before_call_two)
        status, text = report(run)
        check("a ledger changed between two calls stops the run before the next attempt, and the copy keeps its rows",
              status == 1 and len(run.state("attempts")) == 1 and run.stopped() == provider.LEDGER_CHANGED
              and run.reasons() == [None, provider.LEDGER_CHANGED, provider.STOPPED_EARLIER]
              and len(provider.entries(run.work / "ledger-mirror.jsonl")) == 2
              and "is not the provider's own copy of it" in blockers(text))

        run = drive("margin", more={"EVAL_GRADING_MARGIN": "5m"})
        check("a grading margin that is no whole number of seconds runs no attempt",
              run.state("attempts") == [] and run.reasons() == [provider.BAD_INPUT] * RUNS)

        # The live path, with a stand-in for opencode that calls no model.
        cost = provider.cost_of(COUNTS)
        run = drive("live", mode="live", inject=2, exported=session())
        status, text = report(run)
        attempts = run.state("attempts")
        check("a live-path run exits 0, and each attempt that ran the agent costs its token counts times the prices",
              status == 0 and blockers(text).strip() == "None." and cost == Decimal("0.010956")
              and [Decimal(attempt["cost"]) for attempt in attempts] == [cost, Decimal(0), cost, cost]
              and [attempt["usage"]["model"] for attempt in attempts]
              == [provider.MODEL, provider.NO_AGENT, provider.MODEL, provider.MODEL]
              and provider.spend_of(run.ledger)[0] == 3 * cost)
        for name, exported, reason in (
                ("another model", session(model="other/model"), provider.WRONG_MODEL),
                ("a subagent call", session(tools=("shell", "task")), provider.SUBAGENT_CALLS),
                ("no token counts", session(counts=dict.fromkeys(COUNTS, 0)), provider.NO_TOKEN_COUNTS)):
            run = drive(name.replace(" ", "-"), mode="live", exported=exported)
            status, text = report(run)
            check(f"an attempt with {name} stops the run before a second attempt: {reason}",
                  status == 1 and len(run.state("attempts")) == 1 and run.stopped() == reason
                  and run.reasons() == [reason, provider.STOPPED_EARLIER, provider.STOPPED_EARLIER])
        run = drive("rewrite", mode="live", exported=session(), rewrite=True)
        status, text = report(run)
        kept = provider.entries(run.work / "ledger-mirror.jsonl")
        check("an agent that empties the ledger during its attempt stops the run after it, and the copy keeps the cost",
              status == 1 and len(run.state("attempts")) == 1 and run.stopped() == provider.LEDGER_CHANGED
              and run.ledger.read_text() == ""
              and [(row["event"], row.get("cost")) for row in kept] == [("start", None), ("end", format(cost, "f"))]
              and "is not the provider's own copy of it" in blockers(text))

        # One change at a time to the finished dry run: compare.py lists each as a blocker. A
        # blocker is matched without its first word, which compare.md starts with a capital.
        def changed(number: int, change) -> tuple[int, str]:
            mutant = dataclasses.replace(base, home=scratch / f"changed-{number}")
            shutil.copytree(base.home, mutant.home)
            (mutant.home / "compare.md").unlink()
            change(mutant)
            return report(mutant)

        def attempts_file(change):
            return lambda run: edit_lines(run.work / "state" / "attempts.jsonl", change)

        def export_file(change):
            return lambda run: edit_json(run.work / "results.json", change)

        def without_last_row(*names: str):
            def change(run: Run) -> None:
                for path in (run.ledger if name == "ledger" else run.work / name for name in names):
                    path.write_text("".join(path.read_text().splitlines(keepends=True)[:-1]))
            return change

        def more_attempts(rows: list[dict]) -> None:
            rows.extend({**rows[1], "attempt": number, "call": 3, "injected": False} for number in (5, 6, 7))

        def other_attempt(document: dict) -> None:
            document["results"]["results"][0]["response"]["output"] = json.dumps(
                {"call": 1, "attempt": 999, "runner_exit_status": 1, "outcome": "fail"})

        def same_repeat(document: dict) -> None:
            for row in document["results"]["results"]:
                row["repeatIndex"] = 0

        def before_the_run(run: Run) -> None:
            with (run.work / "ledger-before.jsonl").open("a") as before:
                before.write(earlier)

        changes = (
            ("no change", lambda run: None, None),
            ("more attempts than 2N", attempts_file(more_attempts), "over the cap of 2N = 6"),
            ("a result that carries another attempt", export_file(other_attempt), "is not the one the provider's hand-back maps to"),
            ("the same `repeatIndex` on every result", export_file(same_repeat), "are not one per repeat"),
            ("other runtime options",
             export_file(lambda document: document["runtimeOptions"].update(repeat=99, maxConcurrency=12, cache=True)),
             "runtime options in the export are not"),
            ("a passed result with score 0 and an error",
             export_file(lambda document: document["results"]["results"][0].update(score=0, error="provider failed")),
             "is not the one the provider's hand-back maps to"),
            ("totals that count another result",
             export_file(lambda document: document["results"]["stats"].update(successes=2, failures=1)),
             "totals in the export do not count"),
            ("a repeat group that counts another result",
             export_file(lambda document: document["results"]["repeatStability"]["groups"][0].update(passed=2, failed=1)),
             "repeat group in the export does not count"),
            ("an export of another promptfoo version",
             export_file(lambda document: document["metadata"].update(promptfooVersion="0.0.0")),
             "export is not of promptfoo"),
            ("a cost that is not the token counts times the prices",
             attempts_file(lambda rows: rows[0].update(cost="999")), "is not its token counts times the prices"),
            ("an outcome its exit status does not give",
             attempts_file(lambda rows: rows[0].update(exit_status=2)), "is not the one suite.py gives its exit status"),
            ("the `injected` label on another attempt",
             attempts_file(lambda rows: rows[0].update(injected=True)), "`injected` label is not on the one attempt"),
            ("an attempt record without its usage",
             attempts_file(lambda rows: rows[0].pop("usage")), "provider's record of the run cannot be read"),
            ("a ledger row removed after the run", without_last_row("ledger"), "is not the provider's own copy of it"),
            ("a row removed from the ledger and from the provider's copy",
             without_last_row("ledger", "ledger-mirror.jsonl"), "are not a start and an end for each attempt"),
            ("another ledger before the run", before_the_run, "does not begin with the ledger as it was before the run"),
        )
        for number, (name, change, blocker) in enumerate(changes):
            status, text = changed(number, change)
            if blocker is None:
                check("a copy of the dry run with no change still exits 0", status == 0 and blockers(text).strip() == "None.")
            else:
                check(f"compare.py lists {name} as a blocker and exits 1", status == 1 and blocker in blockers(text))

        # What run.sh refuses before it creates anything, with a stand-in for node and npm.
        tools = scratch / "node"
        tools.mkdir()
        (tools / "npm").write_text("#!/bin/sh\nexit 64\n")
        (tools / "npm").chmod(0o755)
        nothing = scratch / "refusals"
        nothing.mkdir()
        (scratch / "ledger.jsonl").write_text("")

        def refused(node: str, **settings: str) -> str:
            """The message run.sh refuses to start with, or nothing when it did not refuse."""
            (tools / "node").write_text(f"#!/bin/sh\necho {node}\n")
            (tools / "node").chmod(0o755)
            env = {key: value for key, value in os.environ.items() if not key.startswith(("SKL317_", "EVAL_"))}
            env.update(PATH=f"{tools}{os.pathsep}{env['PATH']}", TMPDIR=str(nothing), SKL317_MODE="stub", **settings)
            done = subprocess.run(["bash", str(POC / "run.sh")], env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True)
            return done.stderr if done.returncode == 2 and not any(nothing.iterdir()) else ""

        ledger = {"SKL317_SPEND_LEDGER": str(scratch / "ledger.jsonl")}
        check("run.sh refuses a pre-release Node.js", "did not print a release version" in refused("v22.22.0-rc.1", **ledger))
        check("run.sh refuses a Node.js below the floor", "or later is needed" in refused("v22.21.9", **ledger))
        check("run.sh refuses to start without a ledger named", "SKL317_SPEND_LEDGER is needed" in refused("v22.22.0"))
        check("run.sh refuses a ledger that does not exist",
              "does not exist" in refused("v22.22.0", SKL317_SPEND_LEDGER=str(scratch / "none.jsonl")))
        check("run.sh refuses a ledger in the repository",
              "is inside the repository" in refused("v22.22.0", SKL317_SPEND_LEDGER=str(POC / "ledger.jsonl")))
        for name in ("EVAL_TIMEOUT", "EVAL_GRADING_MARGIN"):
            check(f"run.sh refuses an {name} that is no whole number of seconds",
                  f"{name} must be a whole number of seconds" in refused("v22.22.0", **ledger, **{name: "5m"}))

        # The reading of suite.py, of the durations and of a small amount.
        outcomes, margin = provider.suite_rules(clone)
        check("the outcome table read from suite.py at this commit is the one compare.py quotes",
              provider.rules_in(f"{compare.Q_OUTCOMES}\nGRADING_MARGIN = {margin}\n") == (outcomes, margin))

        def unreadable(text: str) -> bool:
            try:
                provider.rules_in(text)
            except provider.Stop as stop:
                return stop.reason == provider.SUITE_UNREADABLE
            return False

        check("a suite.py without a usable outcome table or margin stops the run",
              all(unreadable(text) for text in ("GRADING_MARGIN = 300\n", 'OUTCOMES = {0: "maybe"}\nGRADING_MARGIN = 300\n',
                                                'OUTCOMES = {0: "pass"}\nGRADING_MARGIN = 0\n', "OUTCOMES = {")))
        saved = {name: os.environ.pop(name, None) for name in ("EVAL_TIMEOUT", "EVAL_GRADING_MARGIN")}
        try:
            unset = provider.deadline(margin)
            os.environ.update(EVAL_TIMEOUT="10", EVAL_GRADING_MARGIN="7")
            both = provider.deadline(margin)
        finally:
            for name, value in saved.items():
                os.environ.pop(name, None)
                if value is not None:
                    os.environ[name] = value
        check("an attempt's deadline is EVAL_TIMEOUT plus EVAL_GRADING_MARGIN, by default 900 seconds plus suite.py's margin",
              unset == 900 + margin and both == 17)
        check("an amount is printed in full: six decimals, or as many more as it has",
              [compare.usd(Decimal(amount)) for amount in ("0.00000049", "0.218165", "1.00", "0")]
              == ["0.00000049", "0.218165", "1.000000", "0.000000"])

    print(f"selftest: {len(failed)} failed" if failed else "selftest: every check holds")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
