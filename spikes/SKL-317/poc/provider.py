#!/usr/bin/env python3
"""promptfoo script provider for the SKL-317 spike: one call hands promptfoo one graded run.

promptfoo runs `python3 provider.py PROMPT OPTIONS CONTEXT` once per repeat of the single test.
The prompt is the scenario name, never prompt text. A call runs attempts of the case's own
run.sh (CHECKOUT SCENARIO RUN_DIR) until one is graded, so the void retry lives here and
promptfoo never sees a void attempt:

- exit status 0 is a graded pass, 1 a graded fail and 2 a void attempt, and an attempt that
  outlives its deadline is void too (the OUTCOMES table of suite.py);
- a void attempt is absorbed: the next attempt starts inside the same call;
- at most 2 x N attempts run across the whole promptfoo run, N being the graded runs wanted;
- any other exit status is a broken attempt and stops the run.

A graded attempt is printed as one JSON line and the call exits 0. A call that cannot hand
back a graded attempt prints `SKL317: call <c>: <reason>` on stderr and exits 1, and so does
every later call of a stopped run, because a provider cannot stop promptfoo from calling it.

Only the case's run.sh grades, by running the case's grader.py, and it grades no void attempt.
Every call is a new process, so the attempts, the calls and a stop are kept as files under
SKL317_WORK, and the spend of every attempt of this spike in a ledger outside the repository.
Before each attempt the provider adds up that ledger and stops with `ceiling reached` when the
next attempt could take the total past the ceiling.

No prompt text, agent output, session id or path reaches promptfoo or the state files.
"""

import datetime
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
from decimal import Decimal

POC = pathlib.Path(__file__).resolve().parent
CASE = "skills/story-to-done/evals/qa-unfinished-own-steps"
SCENARIO = "own-steps"
MODEL = "deepseek/deepseek-v4-pro"
# US dollars per million tokens for MODEL. The source lists no cache write price, so a cache
# write is charged as the input it is.
PRICE_SOURCE = "https://models.dev/api.json"
PRICE_DATE = "2026-11-16"
PRICES = {"input": Decimal("0.66"), "cache_read": Decimal("0.022"), "cache_write": Decimal("0.66"),
          "output": Decimal("1.98"), "reasoning": Decimal("1.98")}
COUNTS = tuple(PRICES)
# The spend ceiling of the whole spike in US dollars, and what an attempt is taken to cost
# before any attempt has reported: after that, the highest cost a single attempt has reported.
CEILING = Decimal("1.00")
FIRST_ESTIMATE = Decimal("0.08")
# suite.py's table: the outcome each run.sh exit status gives; None is an attempt past its deadline.
OUTCOMES = {0: "pass", 1: "fail", 2: "void", None: "void"}
# suite.py's margin: seconds an attempt may run past the agent's EVAL_TIMEOUT for setup and grading.
GRADING_MARGIN = 300
# suite.py's rule for the environment of an attempt: these names, these prefixes, and the names
# EVAL_PASS_ENV lists. EVAL_AGENT_CMD is set here, per attempt.
BASE_ENV = {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "TERM", "TZ", "TMPDIR", "EVAL_TIMEOUT"}
BASE_ENV_PREFIXES = ("LC_", "XDG_")
# What a stub plan may ask of an attempt. No behaviour calls a model.
STUB_BEHAVIOURS = ("pass", "fail", "void", "broken")
# Why a call handed promptfoo an error. A stopped run stays stopped.
CAP = "attempt cap reached"
BROKEN = "broken attempt"
CEILING_REACHED = "ceiling reached"
NO_TOKEN_COUNTS = "no token counts"
SPEND_UNKNOWN = "cumulative spend unknown"
STOPPED_EARLIER = "run stopped earlier"
BEYOND_N = "call beyond N"
BAD_INPUT = "unusable provider input"
NO_AGENT = "none (no agent ran)"
STUB_AGENT = "none (stub agent, no model call)"


class Stop(Exception):
    """This call hands promptfoo an error; the text is one of the reasons above."""

    def __init__(self, reason: str, **detail: str) -> None:
        super().__init__(reason)
        self.reason, self.detail = reason, detail


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def entries(path: pathlib.Path) -> list[dict]:
    """The JSON lines of a state file, or none when it is not there yet."""
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def append(path: pathlib.Path, entry: dict) -> None:
    with path.open("a") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def settings() -> dict:
    env = os.environ
    try:
        work = pathlib.Path(env["SKL317_WORK"])
        cfg = {
            "work": work, "state": work / "state", "checkout": pathlib.Path(env["SKL317_CHECKOUT"]),
            "ledger": pathlib.Path(env["SKL317_SPEND_LEDGER"]), "run": env["SKL317_RUN_ID"],
            "mode": env["SKL317_MODE"], "runs": int(env["SKL317_RUNS"]),
            "inject": int(env["SKL317_INJECT_VOID_ATTEMPT"] or 0),
            "plan": [token for token in env.get("SKL317_STUB_PLAN", "").split(",") if token],
            "deadline": int(env.get("EVAL_TIMEOUT") or 900) + GRADING_MARGIN,
        }
    except (KeyError, ValueError) as error:
        sys.exit(f"provider.py: run it through run.sh, which sets its settings ({error.__class__.__name__}: {error})")
    if cfg["mode"] not in ("live", "stub") or cfg["runs"] < 1 or set(cfg["plan"]) - set(STUB_BEHAVIOURS):
        sys.exit("provider.py: run it through run.sh, which sets its settings (a setting is out of range)")
    return cfg


def spend(ledger: pathlib.Path) -> tuple[Decimal, Decimal]:
    """The cumulative spend the ledger holds and the highest cost of a single attempt.

    An attempt that started and never reported counts as what was reserved for it. An attempt
    that ended without a known cost leaves the total unknown, which stops the run.
    """
    try:
        started, ended = {}, {}
        for entry in entries(ledger):
            key = (entry["run"], entry["attempt"])
            if entry["event"] == "start":
                started[key] = Decimal(entry["reserved"])
            else:
                ended[key] = entry["cost"]
        total = highest = Decimal(0)
        for key, reserved in started.items():
            if key not in ended:
                total += reserved
            elif ended[key] is None:
                raise Stop(SPEND_UNKNOWN)
            else:
                total += Decimal(ended[key])
                highest = max(highest, Decimal(ended[key]))
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError):
        raise Stop(SPEND_UNKNOWN) from None
    return total, highest


def cost_of(counts: dict) -> Decimal:
    return sum((Decimal(counts[name]) * PRICES[name] for name in COUNTS), Decimal(0)) / Decimal(1_000_000)


def attempt_env(agent_command: str) -> dict:
    passed = set(os.environ.get("EVAL_PASS_ENV", "").split())
    env = {name: value for name, value in os.environ.items()
           if name in BASE_ENV or name in passed or name.startswith(BASE_ENV_PREFIXES)}
    env["EVAL_AGENT_CMD"] = agent_command
    return env


def session_usage(cfg: dict, title: str) -> dict | None:
    """The token counts opencode recorded for the one session with this title, or None.

    The agent ran without --standalone and --archived under a title only this attempt has, so
    the session is found from the directory it was launched in. Both commands write to a file,
    never a pipe, and the files are removed once read.
    """
    scratch = cfg["work"] / "usage"
    scratch.mkdir(exist_ok=True)
    listing, export = scratch / "sessions.json", scratch / "export.json"

    def opencode(arguments: list[str], out: pathlib.Path) -> object:
        with out.open("wb") as handle:
            subprocess.run(["opencode", "session", *arguments], cwd=cfg["checkout"], stdin=subprocess.DEVNULL,
                           stdout=handle, stderr=subprocess.DEVNULL, check=True, timeout=120)
        return json.loads(out.read_text())

    try:
        sessions = opencode(["list", "--format", "json", "--max-count", "1000"], listing)
        ids = [session["id"] for session in sessions if session.get("title") == title]
        if len(ids) != 1:
            return None
        session = opencode(["export", "--sanitize", ids[0]], export)
        info = session["info"]
        tokens = info["tokens"]
        counts = {"input": tokens["input"], "cache_read": tokens["cache"]["read"],
                  "cache_write": tokens["cache"]["write"], "output": tokens["output"],
                  "reasoning": tokens["reasoning"]}
        if not all(type(count) is int and count >= 0 for count in counts.values()):
            return None
        # A subagent runs in a session of its own, whose tokens this session's totals leave out.
        tools = [part.get("name") for message in session["messages"] for part in message.get("content", [])
                 if isinstance(part, dict) and part.get("type") == "tool"]
        reported = info.get("cost")
        return {"counts": counts, "model": f"{info['model']['providerID']}/{info['model']['id']}",
                "subagent_calls": sum(name in ("task", "subagent") for name in tools),
                "agent_cost": None if reported is None else format(Decimal(str(reported)), "f")}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, AttributeError, ArithmeticError):
        return None
    finally:
        listing.unlink(missing_ok=True)
        export.unlink(missing_ok=True)


def kill_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:  # the group already exited
        pass


def run_attempt(cfg: dict, call: int, number: int, estimate: Decimal) -> dict:
    """Run attempt NUMBER, record its spend in the ledger and return its record."""
    injected = number == cfg["inject"]
    behaviour = "live"
    if cfg["mode"] == "stub":
        behaviour = cfg["plan"][number - 1] if number <= len(cfg["plan"]) else "pass"
    title = f"skl317-{cfg['run']}-attempt-{number}"
    if injected or behaviour == "void":
        agent = "false"
    elif cfg["mode"] == "stub":
        agent = f"python3 {POC / 'stub_agent.py'} {behaviour}"
    else:
        agent = f"opencode run --auto --title {title} --model {MODEL} Follow the instructions in the attached file exactly."
    model_runs = cfg["mode"] == "live" and agent != "false"
    run_dir = cfg["work"] / "runs" / f"attempt-{number}"
    command = ["bash", str(cfg["checkout"] / CASE / "run.sh"), str(cfg["checkout"]), SCENARIO, str(run_dir)]
    if behaviour == "broken" and not injected:
        command = ["bash", "-c", "exit 3"]  # a runner whose status the case contract does not define

    append(cfg["ledger"], {"at": now(), "run": cfg["run"], "attempt": number, "mode": cfg["mode"],
                           "event": "start", "reserved": format(estimate if model_runs else Decimal(0), "f")})
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                               start_new_session=True, env=attempt_env(agent))
    try:
        _, stderr = process.communicate(timeout=cfg["deadline"])
        code = process.returncode
    except subprocess.TimeoutExpired:
        kill_group(process)
        _, stderr = process.communicate()
        code = None
    except BaseException:
        kill_group(process)
        raise
    with (cfg["work"] / "provider.log").open("a") as log:  # for the operator; never committed
        log.write(f"attempt {number}: exit status {code}\n{stderr.decode('utf-8', errors='replace')}\n")
    shutil.rmtree(run_dir, ignore_errors=True)

    usage = {"counts": dict.fromkeys(COUNTS, 0), "model": STUB_AGENT if cfg["mode"] == "stub" else NO_AGENT,
             "subagent_calls": 0, "agent_cost": None}
    if model_runs:
        usage = session_usage(cfg, title)
    cost = None if usage is None else format(cost_of(usage["counts"]), "f")
    append(cfg["ledger"], {"at": now(), "run": cfg["run"], "attempt": number, "mode": cfg["mode"],
                           "event": "end", "cost": cost})
    return {"attempt": number, "call": call, "exit_status": code, "outcome": OUTCOMES.get(code, "error"),
            "injected": injected, "usage": usage, "cost": cost}


def one_call(cfg: dict, call: int, ran: list[int]) -> dict:
    """Run attempts until one is graded and return its record, or raise Stop."""
    if len(sys.argv) < 2 or sys.argv[1] != SCENARIO:
        raise Stop(BAD_INPUT)
    if (cfg["state"] / "stop.json").is_file():
        raise Stop(STOPPED_EARLIER)
    attempts = entries(cfg["state"] / "attempts.jsonl")
    if sum(attempt["outcome"] in ("pass", "fail") for attempt in attempts) >= cfg["runs"]:
        raise Stop(BEYOND_N)
    while True:
        if len(attempts) >= 2 * cfg["runs"]:
            raise Stop(CAP)
        spent, highest = spend(cfg["ledger"])
        estimate = max(FIRST_ESTIMATE, highest)
        if spent + estimate > CEILING:
            raise Stop(CEILING_REACHED, spent=format(spent, "f"), estimate=format(estimate, "f"))
        record = run_attempt(cfg, call, len(attempts) + 1, estimate)
        attempts.append(record)
        ran.append(record["attempt"])
        append(cfg["state"] / "attempts.jsonl", record)
        if record["cost"] is None:
            raise Stop(NO_TOKEN_COUNTS)
        if record["outcome"] == "error":
            raise Stop(BROKEN)
        if record["outcome"] != "void":
            return record


def main() -> int:
    cfg = settings()
    cfg["state"].mkdir(parents=True, exist_ok=True)
    cfg["ledger"].parent.mkdir(parents=True, exist_ok=True)
    calls = cfg["state"] / "calls.jsonl"
    call = len(entries(calls)) + 1
    ran: list[int] = []
    try:
        record = one_call(cfg, call, ran)
    except Stop as stop:
        if stop.reason not in (STOPPED_EARLIER, BEYOND_N, BAD_INPUT):
            (cfg["state"] / "stop.json").write_text(json.dumps({"call": call, "reason": stop.reason, **stop.detail}) + "\n")
        append(calls, {"call": call, "attempts": ran, "handed": "error", "reason": stop.reason})
        print(f"SKL317: call {call}: {stop.reason}", file=sys.stderr)
        return 1
    append(calls, {"call": call, "attempts": ran, "handed": record["outcome"], "reason": None})
    print(json.dumps({"call": call, "attempt": record["attempt"], "runner_exit_status": record["exit_status"],
                      "outcome": record["outcome"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
