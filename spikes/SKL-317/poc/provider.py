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
The outcome table and the grading margin are read from suite.py at the commit under test, in
the repository run.sh was started in, and no attempt runs unless that suite.py holds the rule
text this provider reproduces.

Two clones of the commit under test are used, as suite.py tells a harness checkout from a skill
checkout. The case's run.sh and grader.py run from the harness clone under SKL317_WORK. The
agent works in the other one, the checkout under SKL317_ARENA. Before and after each attempt
both are compared, file by file and by content, with the commit's tree, and a difference stops
the run with `checkout changed`, as a changed checkout stops suite.py.

Every call is a new process, so the attempts, the calls and a stop are kept as files under
SKL317_WORK, and the spend of every attempt of this spike in a ledger outside the repository.
Before each attempt that calls the model the provider adds up that ledger and stops with
`ceiling reached` when the attempt could take the total past the ceiling. The estimate is not a
bound on what one attempt costs: an attempt that costs more than the estimate can end past it.

The agent under test is not trusted with that state. Its environment and arguments name only
SKL317_ARENA (the checkout, the run directories and its temporary directory), never SKL317_WORK
or the ledger, whatever EVAL_PASS_ENV lists. The provider keeps its own copy of the ledger
under SKL317_WORK, writes every row to both, and stops with `spend ledger changed` when the two
differ or when the ledger no longer begins with the bytes run.sh read before the eval started
(SKL317_LEDGER_ANCHOR, their length and SHA-256, which run.sh holds in its own memory).

These checks find a change that is still there when they look. The agent runs as the same
operating-system user as this provider, so a process it starts can change a file and put it
back between two checks, or rewrite the provider's own files. README.md states that limit.

No prompt text, agent output, session id or path reaches promptfoo or the state files.
"""

import ast
import datetime
import hashlib
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
CEILING = Decimal("5.00")
FIRST_ESTIMATE = Decimal("0.08")
# suite.py's rule for the environment of an attempt: these names, these prefixes, and the names
# EVAL_PASS_ENV lists. EVAL_AGENT_CMD and TMPDIR are set here, per attempt. The harness's own
# names are never passed, whatever EVAL_PASS_ENV lists: they name the ledger and SKL317_WORK.
BASE_ENV = {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "TERM", "TZ", "TMPDIR", "EVAL_TIMEOUT"}
BASE_ENV_PREFIXES = ("LC_", "XDG_")
HARNESS_ENV_PREFIXES = ("SKL317_", "PROMPTFOO_")
# The rule text of suite.py this provider reproduces and compare.md quotes. Each is looked up
# at the commit under test before the first attempt, spacing aside.
Q_OUTCOMES = 'OUTCOMES = {0: "pass", 1: "fail", 2: "void", None: "void"}'
Q_LOOP = 'while tally["n"] < runs and attempt < 2 * runs:'
Q_VOID = 'if record["outcome"] == "void":'
Q_COUNT = 'tally["n"] += 1'
Q_ERROR = 'outcome = OUTCOMES.get(code, "error")'
Q_BROKEN = 'raise Broken(f"{case_dir.name} {name} attempt {attempt}: {reason}; the case or the machine is broken")'
QUOTES = (Q_OUTCOMES, Q_LOOP, Q_VOID, Q_COUNT, Q_ERROR, Q_BROKEN)
# What a stub plan may ask of an attempt. No behaviour calls a model.
STUB_BEHAVIOURS = ("pass", "fail", "void", "broken")
# Why a call handed promptfoo an error. A stopped run stays stopped.
CAP = "attempt cap reached"
BROKEN = "broken attempt"
CEILING_REACHED = "ceiling reached"
NO_TOKEN_COUNTS = "no token counts"
SPEND_UNKNOWN = "cumulative spend unknown"
LEDGER_CHANGED = "spend ledger changed"
CHECKOUT_CHANGED = "checkout changed"
WRONG_MODEL = "another model ran"
SUBAGENT_CALLS = "subagent tokens uncounted"
SUITE_UNREADABLE = "suite rules unreadable"
STOPPED_EARLIER = "run stopped earlier"
BEYOND_N = "call beyond N"
BAD_INPUT = "unusable provider input"
REASONS = (CAP, BROKEN, CEILING_REACHED, NO_TOKEN_COUNTS, SPEND_UNKNOWN, LEDGER_CHANGED, CHECKOUT_CHANGED, WRONG_MODEL,
           SUBAGENT_CALLS, SUITE_UNREADABLE, STOPPED_EARLIER, BEYOND_N, BAD_INPUT)
NO_AGENT = "none (no agent ran)"
STUB_AGENT = "none (stub agent, no model call)"


class Stop(Exception):
    """This call hands promptfoo an error; the text is one of the reasons above."""

    def __init__(self, reason: str, **detail: str) -> None:
        super().__init__(reason)
        self.reason, self.detail = reason, detail


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rows_of(data: bytes) -> list[dict]:
    return [json.loads(line) for line in data.decode().splitlines() if line.strip()]


def entries(path: pathlib.Path) -> list[dict]:
    """The JSON lines of a state file, or none when it is not there yet."""
    return rows_of(path.read_bytes()) if path.is_file() else []


def append(path: pathlib.Path, entry: dict) -> None:
    with path.open("a") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def settings() -> dict:
    env = os.environ
    try:
        work = pathlib.Path(env["SKL317_WORK"])
        cfg = {
            "work": work, "state": work / "state", "arena": pathlib.Path(env["SKL317_ARENA"]),
            "checkout": pathlib.Path(env["SKL317_CHECKOUT"]), "harness": pathlib.Path(env["SKL317_HARNESS"]),
            "source": pathlib.Path(env["SKL317_SOURCE"]), "commit": env["SKL317_COMMIT"],
            "ledger": pathlib.Path(env["SKL317_SPEND_LEDGER"]), "mirror": work / "ledger-mirror.jsonl",
            "anchor": env["SKL317_LEDGER_ANCHOR"],
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


def holds(text: str, quote: str) -> bool:
    """True when TEXT holds QUOTE, spacing and line breaks aside."""
    return "".join(quote.split()) in "".join(text.split())


def suite_text(source: pathlib.Path, commit: str) -> str:
    """suite.py at COMMIT, read from SOURCE, the repository run.sh was started in."""
    try:
        return subprocess.run(["git", "-C", str(source), "show", f"{commit}:{SUITE}"], stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, check=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        raise Stop(SUITE_UNREADABLE) from None


def suite_rules(source: pathlib.Path, commit: str) -> tuple[dict, int]:
    """suite.py's OUTCOMES table and GRADING_MARGIN at the commit under test.

    A suite.py that does not hold the rule text this provider reproduces is not the suite it
    reproduces, so it stops the run here, before an attempt has spent anything.
    """
    text = suite_text(source, commit)
    if not all(holds(text, quote) for quote in QUOTES):
        raise Stop(SUITE_UNREADABLE)
    return rules_in(text)


def as_committed(source: pathlib.Path, commit: str, clone: pathlib.Path) -> bool:
    """True when CLONE holds the files of COMMIT byte for byte, and no other file.

    Each file is compared by content and mode with the commit's tree, read from SOURCE by the
    commit's full id. Nothing is asked of the clone's own index or HEAD, which whoever works in
    the clone can rewrite: `git status` and `git diff` skip a changed file that
    `git update-index --assume-unchanged` names, and neither lists a file .gitignore covers.
    """
    try:
        listing = subprocess.run(["git", "-C", str(source), "ls-tree", "-r", "-z", commit], stdin=subprocess.DEVNULL,
                                 capture_output=True, check=True, timeout=60).stdout
        wanted = {}
        for entry in filter(None, listing.split(b"\0")):
            described, _, path = entry.partition(b"\t")
            mode, kind, blob = described.decode().split()
            if kind == "blob":
                wanted[os.fsdecode(path)] = (mode, blob)
        algorithm = "sha256" if any(len(blob) == 64 for _, blob in wanted.values()) else "sha1"

        def blob_id(data: bytes) -> str:
            return hashlib.new(algorithm, b"blob %d\0" % len(data) + data).hexdigest()

        found = {}
        for directory, names, files in os.walk(clone):
            here = pathlib.Path(directory)
            if here == clone:
                names.remove(".git")
            for name in files + [name for name in names if (here / name).is_symlink()]:
                path = here / name
                if path.is_symlink():
                    entry = ("120000", blob_id(os.fsencode(os.readlink(path))))
                elif path.is_file():
                    entry = ("100755" if path.stat().st_mode & 0o100 else "100644", blob_id(path.read_bytes()))
                else:
                    return False
                found[path.relative_to(clone).as_posix()] = entry
        return found == wanted
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def clones_as_committed(cfg: dict) -> bool:
    """True when the harness clone and the agent's checkout are both the commit under test."""
    return all(as_committed(cfg["source"], cfg["commit"], cfg[clone]) for clone in ("harness", "checkout"))


def spend_of(rows: list[dict]) -> tuple[Decimal, Decimal]:
    """The cumulative spend the rows of a ledger hold and the highest cost of a single attempt.

    An attempt that started and never reported counts as what was reserved for it. An attempt
    that ended without a known cost leaves the total unknown, which stops the run.
    """
    try:
        started, ended = {}, {}
        for entry in rows:
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
    except (ValueError, KeyError, TypeError, ArithmeticError):
        raise Stop(SPEND_UNKNOWN) from None
    return total, highest


def anchored(data: bytes, anchor: str) -> bool:
    """True when DATA begins with the ledger as run.sh read it before the eval started.

    ANCHOR is that ledger's length in bytes and its SHA-256, as `<length>:<hex digest>`.
    """
    length, _, digest = anchor.partition(":")
    return length.isdigit() and hashlib.sha256(data[:int(length)]).hexdigest() == digest


def ledger_intact(cfg: dict) -> bool:
    """True when the ledger file is byte for byte the provider's own copy of it, and both
    still begin with the ledger as it was before the eval started."""
    try:
        ledger = cfg["ledger"].read_bytes()
        return ledger == cfg["mirror"].read_bytes() and anchored(ledger, cfg["anchor"])
    except OSError:
        return False


def spend(cfg: dict) -> tuple[Decimal, Decimal]:
    """The cumulative spend of this spike, from a ledger nothing but the provider wrote."""
    if not ledger_intact(cfg):
        raise Stop(LEDGER_CHANGED)
    try:
        return spend_of(entries(cfg["mirror"]))
    except (OSError, ValueError):
        raise Stop(SPEND_UNKNOWN) from None


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


def measured(usage: dict | None) -> bool:
    """True when the token counts of USAGE, at the prices above, are all its attempt spent:
    the session reported counts, ran no other model and called no subagent."""
    return usage is not None and usage["model"] in (NO_AGENT, STUB_AGENT, MODEL) and not usage["subagent_calls"]


def attempt_env(cfg: dict, agent_command: str) -> dict:
    passed = {name for name in os.environ.get("EVAL_PASS_ENV", "").split() if not name.startswith(HARNESS_ENV_PREFIXES)}
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


def calls_model(cfg: dict, number: int) -> bool:
    """True when attempt NUMBER calls the model: a live attempt other than the injected void."""
    return cfg["mode"] == "live" and number != cfg["inject"]


def run_attempt(cfg: dict, call: int, number: int, reserved: Decimal) -> tuple[dict, bool]:
    """Run attempt NUMBER, record its spend in the ledger, and return its record and whether
    the ledger was still the provider's own when the attempt ended. RESERVED is what the
    ledger holds for the attempt until it reports its cost."""
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
    run_dir = cfg["arena"] / "runs" / f"attempt-{number}"
    command = ["bash", str(cfg["harness"] / CASE / "run.sh"), str(cfg["checkout"]), SCENARIO, str(run_dir)]
    if behaviour == "broken" and not injected:
        command = ["bash", "-c", "exit 3"]  # a runner whose status the case contract does not define

    if not ledger_write(cfg, {"at": now(), "run": cfg["run"], "attempt": number, "mode": cfg["mode"], "event": "start",
                              "reserved": format(reserved, "f")}):
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
    if calls_model(cfg, number):
        usage = session_usage(cfg, title)
    # Spend the counts do not measure is written as unknown, so that no later invocation adds
    # a part of it up as the whole: spend_of() stops every run on a row without a cost.
    cost = format(cost_of(usage["counts"]), "f") if measured(usage) else None
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
    cfg["outcomes"], margin = suite_rules(cfg["source"], cfg["commit"])
    cfg["deadline"] = deadline(margin)
    while True:
        if len(attempts) >= 2 * cfg["runs"]:
            raise Stop(CAP)
        number = len(attempts) + 1
        spent, highest = spend(cfg)
        # Only an attempt that calls the model can spend, so only that one is held to the ceiling.
        estimate = max(FIRST_ESTIMATE, highest) if calls_model(cfg, number) else Decimal(0)
        if estimate and spent + estimate > CEILING:
            raise Stop(CEILING_REACHED, spent=format(spent, "f"), estimate=format(estimate, "f"))
        if not clones_as_committed(cfg):
            raise Stop(CHECKOUT_CHANGED)
        record, intact = run_attempt(cfg, call, number, estimate)
        attempts.append(record)
        ran.append(record["attempt"])
        append(cfg["state"] / "attempts.jsonl", record)
        if not intact:
            raise Stop(LEDGER_CHANGED)
        # The grade of an attempt that left either clone changed is not the committed grader's.
        if not clones_as_committed(cfg):
            raise Stop(CHECKOUT_CHANGED)
        # An attempt whose spend is not measured has no cost, and stops the run here, before
        # another attempt is admitted against the ceiling.
        if record["usage"] is None:
            raise Stop(NO_TOKEN_COUNTS)
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
