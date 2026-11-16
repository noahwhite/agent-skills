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
The outcome table and the grading margin are read from suite.py at the commit under test.

Every call is a new process, so the attempts, the calls and a stop are kept as files under
SKL317_WORK, and the spend of every attempt of this spike in a ledger outside the repository.
Before each attempt the provider adds up that ledger and stops with `ceiling reached` when the
next attempt could take the total past the ceiling.

The agent under test is not trusted with that state. Its environment and arguments name only
SKL317_ARENA (the checkout, the run directories and its temporary directory), never SKL317_WORK
or the ledger. The provider keeps its own copy of the ledger under SKL317_WORK, writes every
row to both, and stops with `spend ledger changed` when the two differ.

No prompt text, agent output, session id or path reaches promptfoo or the state files.
"""

import ast
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
SUITE = "skills/story-to-done/evals/suite.py"
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
# suite.py's rule for the environment of an attempt: these names, these prefixes, and the names
# EVAL_PASS_ENV lists. EVAL_AGENT_CMD and TMPDIR are set here, per attempt.
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
LEDGER_CHANGED = "spend ledger changed"
WRONG_MODEL = "another model ran"
SUBAGENT_CALLS = "subagent tokens uncounted"
SUITE_UNREADABLE = "suite rules unreadable"
STOPPED_EARLIER = "run stopped earlier"
BEYOND_N = "call beyond N"
BAD_INPUT = "unusable provider input"
REASONS = (CAP, BROKEN, CEILING_REACHED, NO_TOKEN_COUNTS, SPEND_UNKNOWN, LEDGER_CHANGED, WRONG_MODEL, SUBAGENT_CALLS,
           SUITE_UNREADABLE, STOPPED_EARLIER, BEYOND_N, BAD_INPUT)
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
            "work": work, "state": work / "state", "arena": pathlib.Path(env["SKL317_ARENA"]),
            "checkout": pathlib.Path(env["SKL317_CHECKOUT"]),
            "ledger": pathlib.Path(env["SKL317_SPEND_LEDGER"]), "mirror": work / "ledger-mirror.jsonl",
            "run": env["SKL317_RUN_ID"], "mode": env["SKL317_MODE"], "runs": int(env["SKL317_RUNS"]),
            "inject": int(env["SKL317_INJECT_VOID_ATTEMPT"] or 0),
            "plan": [token for token in env.get("SKL317_STUB_PLAN", "").split(",") if token],
        }
    except (KeyError, ValueError) as error:
        sys.exit(f"provider.py: run it through run.sh, which sets its settings ({error.__class__.__name__}: {error})")
    if cfg["mode"] not in ("live", "stub") or cfg["runs"] < 1 or set(cfg["plan"]) - set(STUB_BEHAVIOURS):
        sys.exit("provider.py: run it through run.sh, which sets its settings (a setting is out of range)")
    return cfg


def seconds(name: str, default: int) -> int:
    """suite.py's reading of a duration setting: a whole number of seconds, at least 1."""
    value = os.environ.get(name) or str(default)
    if not value.isdigit() or int(value) < 1:
        raise Stop(BAD_INPUT)
    return int(value)


def deadline(margin: int) -> int:
    """The seconds an attempt may take, as suite.py adds them up: EVAL_TIMEOUT for the agent
    and EVAL_GRADING_MARGIN, by default the suite's own margin, for the case's run.sh around it."""
    return seconds("EVAL_TIMEOUT", 900) + seconds("EVAL_GRADING_MARGIN", margin)


def rules_in(text: str) -> tuple[dict, int]:
    """The OUTCOMES table and the GRADING_MARGIN that the text of a suite.py assigns.

    OUTCOMES gives the outcome of each run.sh exit status, None being an attempt past its
    deadline; GRADING_MARGIN is the seconds an attempt may run past the agent's EVAL_TIMEOUT.
    The text is parsed, never run, and a table this provider cannot act on stops the run.
    """
    try:
        found = {}
        for node in ast.parse(text).body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                    and node.targets[0].id in ("OUTCOMES", "GRADING_MARGIN"):
                found[node.targets[0].id] = ast.literal_eval(node.value)
        outcomes, margin = found["OUTCOMES"], found["GRADING_MARGIN"]
    except (SyntaxError, ValueError, TypeError, KeyError, RecursionError, MemoryError):
        raise Stop(SUITE_UNREADABLE) from None
    usable = (type(outcomes) is dict and all(key is None or type(key) is int for key in outcomes)
              and all(value in ("pass", "fail", "void") for value in outcomes.values())
              and type(margin) is int and margin >= 1)
    if not usable:
        raise Stop(SUITE_UNREADABLE)
    return outcomes, margin


def suite_rules(checkout: pathlib.Path) -> tuple[dict, int]:
    """suite.py's OUTCOMES table and GRADING_MARGIN, read from the commit under test."""
    try:
        text = subprocess.run(["git", "-C", str(checkout), "show", f"HEAD:{SUITE}"], stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, check=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        raise Stop(SUITE_UNREADABLE) from None
    return rules_in(text)


def spend_of(ledger: pathlib.Path) -> tuple[Decimal, Decimal]:
    """The cumulative spend a ledger file holds and the highest cost of a single attempt.

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


def ledger_intact(cfg: dict) -> bool:
    """True when the ledger file is byte for byte the provider's own copy of it."""
    try:
        return cfg["ledger"].read_bytes() == cfg["mirror"].read_bytes()
    except OSError:
        return False


def spend(cfg: dict) -> tuple[Decimal, Decimal]:
    """The cumulative spend of this spike, from a ledger nothing but the provider wrote."""
    if not ledger_intact(cfg):
        raise Stop(LEDGER_CHANGED)
    return spend_of(cfg["mirror"])


def ledger_write(cfg: dict, entry: dict) -> bool:
    """Add a row to the provider's copy, and to the ledger when it is still that copy.

    False when the ledger changed outside the provider: the row is then kept in the copy alone,
    which holds the true record for the operator to restore the ledger from.
    """
    intact = ledger_intact(cfg)
    append(cfg["mirror"], entry)
    if intact:
        append(cfg["ledger"], entry)
    return intact


def cost_of(counts: dict) -> Decimal:
    return sum((Decimal(counts[name]) * PRICES[name] for name in COUNTS), Decimal(0)) / Decimal(1_000_000)


def attempt_env(cfg: dict, agent_command: str) -> dict:
    passed = set(os.environ.get("EVAL_PASS_ENV", "").split())
    env = {name: value for name, value in os.environ.items()
           if name in BASE_ENV or name in passed or name.startswith(BASE_ENV_PREFIXES)}
    env["EVAL_AGENT_CMD"] = agent_command
    env["TMPDIR"] = str(cfg["arena"] / "tmp")
    return env


def session_usage(cfg: dict, title: str) -> dict | None:
    """The token counts opencode recorded for the one session with this title, or None.

    The agent ran without --standalone and --archived under a title only this attempt has, so
    the session is found from the directory it was launched in. Both commands write to a file,
    never a pipe, and the files are removed once read. A session whose counts are all zero
    reports no usage of a model that ran, so it is no token counts either.
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
        if not all(type(count) is int and count >= 0 for count in counts.values()) or not any(counts.values()):
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


def run_attempt(cfg: dict, call: int, number: int, estimate: Decimal) -> tuple[dict, bool]:
    """Run attempt NUMBER, record its spend in the ledger, and return its record and whether
    the ledger was still the provider's own when the attempt ended."""
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
    run_dir = cfg["arena"] / "runs" / f"attempt-{number}"
    command = ["bash", str(cfg["checkout"] / CASE / "run.sh"), str(cfg["checkout"]), SCENARIO, str(run_dir)]
    if behaviour == "broken" and not injected:
        command = ["bash", "-c", "exit 3"]  # a runner whose status the case contract does not define

    if not ledger_write(cfg, {"at": now(), "run": cfg["run"], "attempt": number, "mode": cfg["mode"], "event": "start",
                              "reserved": format(estimate if model_runs else Decimal(0), "f")}):
        raise Stop(LEDGER_CHANGED)  # checked a moment ago by spend(); nothing ran
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                               start_new_session=True, env=attempt_env(cfg, agent))
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
    intact = ledger_write(cfg, {"at": now(), "run": cfg["run"], "attempt": number, "mode": cfg["mode"],
                                "event": "end", "cost": cost})
    return {"attempt": number, "call": call, "exit_status": code, "outcome": cfg["outcomes"].get(code, "error"),
            "injected": injected, "usage": usage, "cost": cost}, intact


def one_call(cfg: dict, call: int, ran: list[int]) -> dict:
    """Run attempts until one is graded and return its record, or raise Stop."""
    if len(sys.argv) < 2 or sys.argv[1] != SCENARIO:
        raise Stop(BAD_INPUT)
    if (cfg["state"] / "stop.json").is_file():
        raise Stop(STOPPED_EARLIER)
    attempts = entries(cfg["state"] / "attempts.jsonl")
    if sum(attempt["outcome"] in ("pass", "fail") for attempt in attempts) >= cfg["runs"]:
        raise Stop(BEYOND_N)
    cfg["outcomes"], margin = suite_rules(cfg["checkout"])
    cfg["deadline"] = deadline(margin)
    while True:
        if len(attempts) >= 2 * cfg["runs"]:
            raise Stop(CAP)
        spent, highest = spend(cfg)
        estimate = max(FIRST_ESTIMATE, highest)
        if spent + estimate > CEILING:
            raise Stop(CEILING_REACHED, spent=format(spent, "f"), estimate=format(estimate, "f"))
        record, intact = run_attempt(cfg, call, len(attempts) + 1, estimate)
        attempts.append(record)
        ran.append(record["attempt"])
        append(cfg["state"] / "attempts.jsonl", record)
        if not intact:
            raise Stop(LEDGER_CHANGED)
        if record["cost"] is None:
            raise Stop(NO_TOKEN_COUNTS)
        # An attempt whose spend is not what the cost above measures stops the run here, before
        # another attempt is admitted against the ceiling.
        if record["usage"]["model"] not in (NO_AGENT, STUB_AGENT, MODEL):
            raise Stop(WRONG_MODEL)
        if record["usage"]["subagent_calls"]:
            raise Stop(SUBAGENT_CALLS)
        if record["outcome"] == "error":
            raise Stop(BROKEN)
        if record["outcome"] != "void":
            return record


def main() -> int:
    cfg = settings()
    cfg["state"].mkdir(parents=True, exist_ok=True)
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
