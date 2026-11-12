#!/usr/bin/env python3
"""The eval suite runner behind run-suite.sh: repeat each case's scenarios, record, summarise.

Every attempt runs the case's own run.sh (CHECKOUT SCENARIO RUN_DIR) through bash, and its exit
status is the attempt's verdict: 0 graded pass, 1 graded fail, 2 void. An attempt that outlives
its deadline is void too. A void attempt is recorded with its reason and retried until the
scenario has N graded runs or 2×N attempts. Any other exit status means the case or the machine
is broken, not that the run was void: the attempt is recorded and the suite stops.

Exit status: 0 every scenario reached N graded runs, 1 at least one did not or the suite stopped
on a broken attempt, 2 the suite refused to start or would have overwritten a file.
"""

import argparse
import ast
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

EVALS = Path(__file__).resolve().parent
ROOT = EVALS.parents[2]
EVALS_PARTS = EVALS.relative_to(ROOT).parts
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
# A relative file path a grader names, such as sessions.json or senior-engineer/todo.md.
RELATIVE_FILE = re.compile(r"(?:[A-Za-z0-9][A-Za-z0-9._-]*/)*[A-Za-z0-9][A-Za-z0-9_-]*\.[A-Za-z0-9._-]+")
ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# The environment every attempt gets; anything else, credentials included, reaches it only
# when EVAL_PASS_ENV names it.
# EVAL_AGENT_CMD and EVAL_TIMEOUT are the case contract's settings; no other EVAL_ variable is passed.
BASE_ENV = {"PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "TERM", "TZ", "TMPDIR",
            "EVAL_AGENT_CMD", "EVAL_TIMEOUT"}
BASE_ENV_PREFIXES = ("LC_", "XDG_")
# A passed value shorter than this is too common a string to redact from a record.
MIN_REDACTED = 8
UUID = re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
# An absolute path of two or more segments that no known root above accounted for. The
# lookbehind keeps URLs (scheme://host/path) and relative paths (a/b/c) as they are.
ABSOLUTE_PATH = re.compile(r"(?<![\w.:/{}~-])/(?:[\w.@+-]+/)+[\w.@+-]*")
VOID_LINE = re.compile(r"^(HARNESS|run\.sh):")
# The record fields --resume compares with this run, each against its run context key.
RECORD_FIELDS = {"label": "label", "checkout_commit": "checkout_commit", "harness_commit": "harness_commit",
                 "model": "model", "reasoning_effort": "effort", "agent_command": "agent_command"}
# The outcome each run.sh exit status gives; None is an attempt past its deadline.
OUTCOMES = {0: "pass", 1: "fail", 2: "void", None: "void"}
GRADE_FILE = re.compile(r"grader(?:-(?P<grade>[A-Za-z0-9._-]+))?-output\.txt")
MODEL_FLAG = re.compile(r"--model=(\S+)|(?:^|\s)(?:--model|-m)\s+(\S+)")
VARIANCE = "k/n × (1 - k/n)"
# Seconds an attempt may run past the agent's own EVAL_TIMEOUT for the case's setup and grading.
GRADING_MARGIN = 300


class Refused(Exception):
    """The suite cannot start, or would overwrite a file: exit 2."""


class Broken(Exception):
    """An attempt broke the case contract or changed a checkout: exit 1."""


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise Refused(f"git {' '.join(args)} failed in {repo}: {result.stderr.strip()}")
    return result.stdout.strip()


def is_record(path: str) -> bool:
    """True for a file the suite writes: directly in the suite's results/ or in a case's."""
    parts = Path(path).parts
    if parts[:len(EVALS_PARTS)] != EVALS_PARTS:
        return False
    rest = parts[len(EVALS_PARTS):]
    return (len(rest) == 2 and rest[0] == "results") or (len(rest) == 3 and rest[1] == "results")


def commit_of(repo: Path, role: str) -> tuple[Path, str, str]:
    """The checkout's root, full and short HEAD. A checkout with tracked or untracked changes is
    refused, because its commit would not describe what ran; only the suite's own uncommitted
    records under a results/ directory are allowed, since they are outputs, not code."""
    root = Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
    status = [line for line in git(root, "status", "--porcelain", "--untracked-files=all").splitlines() if line]
    changed = [line[3:] for line in status if not (line.startswith("??") and is_record(line[3:]))]
    if changed:
        raise Refused(f"the {role} checkout {root} has uncommitted changes ({', '.join(changed[:5])}), "
                      "so its commit would not describe the run")
    return root, git(root, "rev-parse", "HEAD"), git(root, "rev-parse", "--short=7", "HEAD")


def parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="run-suite.sh", description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=3, help="graded runs per scenario (default 3)")
    parser.add_argument("--resume", action="store_true",
                        help="continue an interrupted run of this LABEL from its existing records")
    parser.add_argument("checkout", type=Path, help="the checkout holding the skill under test")
    parser.add_argument("label", help="names this suite run's records and summary")
    parser.add_argument("cases", nargs="*", help="case directories to run (default: every case)")
    args = parser.parse_args(argv)
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    if not NAME.fullmatch(args.label):
        parser.error(f"LABEL {args.label!r} must match {NAME.pattern}")
    if not args.checkout.is_dir():
        parser.error(f"CHECKOUT {args.checkout} is not a directory")
    if len(set(args.cases)) != len(args.cases):
        parser.error("a CASE is named more than once")
    for case in args.cases:
        if not NAME.fullmatch(case) or not (EVALS / case / "case.yaml").is_file():
            parser.error(f"no case {case!r} in the harness checkout")
    return args


def grader_names(grader: Path) -> set[str]:
    """Every string the grader's code holds, docstrings excluded: the file names it can open."""
    try:
        tree = ast.parse(read(grader))
    except SyntaxError as error:
        raise Refused(f"{grader} does not parse: {error}") from None
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                docstrings.add(id(first.value))
    return {node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings}


def leak_patterns() -> list[re.Pattern]:
    """The repository's leak-scan patterns, public and any private ones loaded, so a record is
    normalised against exactly what the guard rejects."""
    spec = importlib.util.spec_from_file_location("leak_scan", ROOT / "scripts" / "leak_scan.py")
    if spec is None or spec.loader is None:
        raise Refused(f"cannot load {ROOT / 'scripts' / 'leak_scan.py'}")
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True  # a __pycache__ in the harness checkout would make it dirty
    spec.loader.exec_module(module)
    return [regex for regex, _ in module.load_public()] + module.load_private()


class Normaliser:
    """Rewrites the values of passed variables to {redacted}, local and scratch paths and UUID
    shapes to placeholders, longest path first, then any other absolute path to {path} and
    anything else the leak scan rejects to {redacted}, so a record carries no credential, path
    or identifier of the machine that ran it."""

    def __init__(self, leaks: list[re.Pattern], secrets: list[str] = (), **paths: Path) -> None:
        pairs = {}
        for name, path in paths.items():
            for form in {str(path), str(path.resolve())}:
                if len(form) > 1:
                    pairs.setdefault(form, "{" + name + "}")
        self.pairs = sorted(pairs.items(), key=lambda pair: -len(pair[0]))
        self.secrets = sorted({value for value in secrets if len(value) >= MIN_REDACTED}, key=len, reverse=True)
        self.leaks = leaks

    def __call__(self, text: str) -> str:
        for value in self.secrets:
            text = text.replace(value, "{redacted}")
        for path, placeholder in self.pairs:
            # A root is only replaced whole: /home/user never rewrites /home/user2 or /srv/home/user.
            text = re.sub(r"(?<![\w.-])" + re.escape(path) + r"(?![\w.-])", lambda _: placeholder, text)
        text = UUID.sub("{uuid}", text)
        text = ABSOLUTE_PATH.sub("{path}", text)
        for regex in self.leaks:
            text = regex.sub("{redacted}", text)
        return text


def stated_reason(stderr: str) -> str:
    """The first HARNESS: or run.sh: line run.sh wrote. It is shown to the operator only: a
    record and the summary carry the classified reason, never text run.sh passed through."""
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    return next((line for line in lines if VOID_LINE.match(line)), "run.sh stated no HARNESS: or run.sh: reason")


def write_new(path: Path, text: str) -> None:
    """Write a file that must not exist yet, whole or not at all."""
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            raise Refused(f"{path} exists; a suite run never overwrites a record") from None
    finally:
        os.unlink(temp)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def verdicts(grades: dict, name: str, outcome: str) -> tuple[dict[str, str], str | None]:
    """Each grade's verdict, named for its scenario, or why there is none, from the lines of
    each grade file. run.sh's exit status is the scenario's verdict unless it writes further
    grades: grader-output.txt is then the scenario's own grade and grader-<g>-output.txt a
    further grade named <scenario>-<g>, since the status mixes them. The status must still be
    pass exactly when every grade passes."""
    found = {}
    for file_name in sorted(grades):
        match = GRADE_FILE.fullmatch(file_name)
        if match:
            lines = [line.strip() for line in grades[file_name] if line.strip()]
            grade = name + (f"-{match['grade']}" if match["grade"] else "")
            found[grade] = "pass" if lines and lines[-1] == "PASS" else "fail"
    if len(found) <= 1 and set(found) <= {name}:
        return {name: outcome}, None
    if name not in found:
        return {}, "run.sh wrote a further grade but no grader-output.txt, so the scenario has no own verdict"
    if all(verdict == "pass" for verdict in found.values()) != (outcome == "pass"):
        return {}, f"run.sh's grade files contradict its exit status, a graded {outcome}"
    return found, None


def kill_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:  # the group already exited
        pass


def run_attempt(case_dir: Path, name: str, run_dir: Path, ctx: dict) -> tuple[int | None, str]:
    """Run one attempt in its own process group; None as the status means it timed out."""
    process = subprocess.Popen(["bash", str(case_dir / "run.sh"), str(ctx["checkout"]), name, str(run_dir)],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True, env=ctx["env"])
    try:
        _, stderr = process.communicate(timeout=ctx["deadline"])
        return process.returncode, stderr.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        kill_group(process)
        process.communicate()
        return None, ""
    except BaseException:
        kill_group(process)
        raise


def other_grades(tally: dict, marks: dict) -> str | None:
    """Why a graded attempt's grades cannot be counted beside the earlier ones: every graded
    attempt of a scenario must write the same grades, or a grade's n would count attempts
    that hold no verdict for it."""
    if tally["graded"] is not None and set(marks) != tally["graded"]:
        return (f"run.sh wrote the grades {sorted(marks)}, but an earlier attempt wrote "
                f"{sorted(tally['graded'])}; every graded attempt must write the same grades")
    return None


def tally_record(tally: dict, record: dict) -> None:
    if record["outcome"] == "void":
        tally["voids"].append(f"attempt {record['attempt']}: {record['void_reason']}")
        return
    reason = other_grades(tally, record["verdicts"])
    if reason:
        raise Broken(f"{record['case']} {record['scenario']} attempt {record['attempt']}: {reason}")
    tally["graded"] = set(record["verdicts"])
    tally["n"] += 1
    for grade, verdict in record["verdicts"].items():
        tally["k"][grade] = tally["k"].get(grade, 0) + (verdict == "pass")


def resumed(record_path: Path, name: str, ctx: dict) -> dict:
    """An existing record that --resume counts: it must come from this run's configuration,
    its outcome and verdicts must be the ones its exit code and grades give, and a broken
    attempt is never counted, so it stops the resume."""
    record = json.loads(read(record_path))
    differ = [field for field, key in RECORD_FIELDS.items() if record.get(field) != ctx[key]]
    if differ:
        raise Refused(f"{record_path} records a different {', '.join(differ)} than this run; "
                      "--resume continues only the same configuration")
    outcome, grades = record.get("outcome"), record.get("grades")
    if outcome not in ("pass", "fail", "void"):
        raise Refused(f"{record_path} records a broken attempt; fix the case and start a new LABEL")
    if not isinstance(grades, dict) or not all(isinstance(lines, list) for lines in grades.values()):
        grades = None
    given = ({}, None) if outcome == "void" or grades is None else verdicts(grades, name, outcome)
    if (record.get("scenario") != name or OUTCOMES.get(record.get("exit_code")) != outcome
            or grades is None or given != (record.get("verdicts"), None)):
        raise Refused(f"{record_path} records an outcome or verdicts that its exit code and grades do not give; "
                      "--resume counts only records the suite wrote")
    return record


def label_records(label: str) -> set[Path]:
    """Every run record on disk that names LABEL, in any case's results."""
    found = set()
    for path in EVALS.glob(f"*/results/{label}-*.json"):
        try:
            named = json.loads(read(path)).get("label")
        except (ValueError, AttributeError):
            named = label  # an unreadable record is never silently left out
        if named == label:
            found.add(path)
    return found


def run_scenario(case_dir: Path, scenario: dict, runs: int, ctx: dict) -> dict:
    name = scenario["name"]
    results = case_dir / "results"
    tally = {"n": 0, "k": {}, "voids": [], "graded": None}
    attempt = 0
    while tally["n"] < runs and attempt < 2 * runs:
        attempt += 1
        stem = f"{ctx['label']}-{name}-{ctx['checkout_short']}-harness-{ctx['harness_short']}-{attempt}"
        record_path, calls_path = results / f"{stem}.json", results / f"{stem}-calls.jsonl"
        if ctx["resume"] and record_path.is_file() and calls_path.is_file():
            tally_record(tally, resumed(record_path, name, ctx))
            ctx["counted"].add(record_path)
            continue
        for path in (record_path, calls_path):
            if path.exists():
                raise Refused(f"{path} exists; a suite run never overwrites a record")
        ctx["unchanged"]()
        run_dir = ctx["tmp"] / f"{case_dir.name}-{name}-{attempt}"
        print(f"run-suite: {case_dir.name} {name} attempt {attempt}", file=sys.stderr, flush=True)
        code, stderr = run_attempt(case_dir, name, run_dir, ctx)
        normalise = Normaliser(ctx["leaks"], ctx["secrets"], run_dir=run_dir, tmp=ctx["tmp"], checkout=ctx["checkout"],
                               harness=ctx["harness"], tmpdir=Path(tempfile.gettempdir()), home=Path.home())
        outcome = OUTCOMES.get(code, "error")
        reason = None
        if code is None:
            reason = f"run.sh did not finish within {ctx['deadline']} seconds"
        elif code == 2:
            reason = "run.sh exited 2: void"
        elif outcome == "error":
            reason = f"run.sh exited {code}, a status the case contract does not define"
        if outcome in ("void", "error") and code is not None:
            print(f"run-suite: {case_dir.name} {name} attempt {attempt}: {normalise(stated_reason(stderr))}",
                  file=sys.stderr, flush=True)
        grades, inputs, marks = {}, {}, {}
        if outcome in ("pass", "fail"):
            for output in sorted(run_dir.glob("grader*-output.txt")):
                grades[output.name] = normalise(read(output)).splitlines()
            marks, reason = verdicts(grades, name, outcome)
            reason = reason or other_grades(tally, marks)
            if reason:
                outcome = "error"
            # Keep every run-directory file the grader names, beside the call record, so the
            # attempt can be graded again from what is committed.
            for file_name in sorted(ctx["grader_reads"]):
                path = run_dir / file_name
                if file_name != "actions.jsonl" and path.is_file() and run_dir.resolve() in path.resolve().parents:
                    inputs[file_name] = normalise(read(path))
        actions = run_dir / "actions.jsonl"
        record = {
            "case": case_dir.name, "scenario": name, "label": ctx["label"], "attempt": attempt,
            "checkout_commit": ctx["checkout_commit"], "harness_commit": ctx["harness_commit"],
            "model": ctx["model"], "reasoning_effort": ctx["effort"], "agent_command": ctx["agent_command"],
            "exit_code": code, "outcome": outcome, "void_reason": reason, "verdicts": marks,
            "grades": grades, "grader_inputs": inputs, "calls_record": "actions.jsonl" if actions.is_file() else "absent",
        }
        write_new(calls_path, normalise(read(actions)) if actions.is_file() else "")
        write_new(record_path, json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        ctx["counted"].add(record_path)
        if run_dir.exists():  # run.sh may refuse before it creates the directory
            shutil.rmtree(run_dir)  # scratch only: the records above are what is kept
        if outcome == "error":
            raise Broken(f"{case_dir.name} {name} attempt {attempt}: {reason}; the case or the machine is broken")
        tally_record(tally, record)
    role = "control (regression pin)" if "control" in scenario else ctx["kind"]
    grades = sorted(tally["k"], key=lambda grade: (grade != name, grade)) or [name]
    return {"name": name, "n": tally["n"], "voids": tally["voids"],
            "grades": [{"name": grade, "k": tally["k"].get(grade, 0),
                        "role": role if grade == name else f"{ctx['kind']} (further grade of {name})"}
                       for grade in grades]}


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def summary(label: str, runs: int, sections: list[dict], short: list[str], ctx: dict) -> str:
    lines = [
        f"# Eval suite run `{label}`",
        "",
        f"- Graded runs asked for per scenario (N): {runs}; void runs are retried up to {2 * runs} attempts.",
        f"- Skill commit (CHECKOUT): `{ctx['checkout_commit']}`",
        f"- Harness commit: `{ctx['harness_commit']}`",
        f"- Agent command: `{cell(ctx['agent_command'])}`",
        "- n is the graded run count, k the pass count, and the pass rate is k/n.",
        f"- Variance is {VARIANCE}, the variance of one run's pass or fail at the observed pass rate.",
        "- A scenario with n = 0 reports its pass rate and variance as `n/a`.",
        "- A scenario graded more than once has one row per grade; a further grade's row is named "
        "`<scenario>-<grade>` and counts the same runs.",
        "- Counts and provenance only; each attempt's run record and tool-call record are under the case's `results/`.",
        f"- Scenarios short of N graded runs: {', '.join(short) if short else 'none'}.",
    ]
    for section in sections:
        lines += ["", f"## {section['case']} ({section['kind']})", "",
                  "| Scenario | Role | Skill commit | Harness commit | Model | Reasoning effort | n | k "
                  "| Pass rate k/n | Variance | Voids | Void reasons |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for row in section["rows"]:
            n = row["n"]
            reasons = "; ".join(row["voids"]) or "none"
            for grade in row["grades"]:
                k = grade["k"]
                rate = f"{k}/{n} = {k / n:.3f}" if n else "n/a"
                variance = f"{(k / n) * (1 - k / n):.3f}" if n else "n/a"
                lines.append(f"| {grade['name']} | {grade['role']} | {ctx['checkout_short']} | {ctx['harness_short']} "
                             f"| {cell(section['model'])} | {cell(section['effort'])} | {n} | {k} | {rate} "
                             f"| {variance} | {len(row['voids'])} | {cell(reasons)} |")
    return "\n".join(lines) + "\n"


def agent_config(normalise) -> tuple[str, str, str]:
    """The agent command, model and reasoning effort every attempt runs with, all read from
    EVAL_AGENT_CMD, which the suite requires: it names its model with --model, and the model's
    #variant is its effort, so a record names the agent that ran rather than one a case claims."""
    command = os.environ.get("EVAL_AGENT_CMD", "").strip()
    if not command:
        raise Refused("set EVAL_AGENT_CMD to the agent command, naming its model with --model, "
                      "so the records name the agent that ran")
    match = MODEL_FLAG.search(command)
    if not match:
        raise Refused("EVAL_AGENT_CMD must name its model with --model, so the records can name it")
    model, _, variant = (match.group(1) or match.group(2)).partition("#")
    return normalise(command), normalise(model), normalise(variant or "default")


def agent_env() -> tuple[dict[str, str], list[str]]:
    """The environment every attempt runs in and the passed values to redact: the base names,
    plus each variable EVAL_PASS_ENV names, such as the model provider's credential."""
    passed = os.environ.get("EVAL_PASS_ENV", "").split()
    bad = [name for name in passed if not ENV_NAME.fullmatch(name)]
    if bad:
        raise Refused(f"EVAL_PASS_ENV names {bad}, which are not variable names")
    short = [name for name in passed if name in os.environ and len(os.environ[name]) < MIN_REDACTED]
    if short:
        raise Refused(f"EVAL_PASS_ENV names {short}, whose values are shorter than {MIN_REDACTED} characters "
                      "and so could not be redacted from the records")
    env ={name: value for name, value in os.environ.items()
           if name in BASE_ENV or name.startswith(BASE_ENV_PREFIXES) or name in passed}
    return env, [os.environ[name] for name in passed if name in os.environ]


def seconds(name: str, default: int) -> int:
    value = os.environ.get(name) or str(default)
    if not value.isdigit() or int(value) < 1:
        raise Refused(f"{name} must be a whole number of seconds, at least 1, not {value!r}")
    return int(value)


def main(argv: list[str]) -> int:
    args = parse(argv)
    summary_path = EVALS / "results" / f"suite-{args.label}.md"
    if summary_path.exists():
        raise Refused(f"{summary_path} exists; a suite run never overwrites a summary")
    existing = label_records(args.label)
    if existing and not args.resume:
        raise Refused(f"{min(existing)} exists, a record of {args.label}; start a new LABEL, "
                      "or --resume with the arguments that run started with")
    harness, harness_commit, harness_short = commit_of(EVALS, "harness")
    checkout, checkout_commit, checkout_short = commit_of(args.checkout, "skill")
    cases = args.cases or sorted(path.parent.name for path in EVALS.glob("*/case.yaml"))
    specs = {}
    for case in cases:
        if not NAME.fullmatch(case):
            raise Refused(f"case directory {case!r} must match {NAME.pattern}")
        spec = yaml.safe_load(read(EVALS / case / "case.yaml"))
        scenarios = spec.get("scenarios") if isinstance(spec, dict) else None
        if not scenarios or not all(isinstance(s, dict) and NAME.fullmatch(str(s.get("name", ""))) for s in scenarios):
            raise Refused(f"case {case} names no scenarios, or a scenario without a valid name")
        if len({s["name"] for s in scenarios}) != len(scenarios):
            raise Refused(f"case {case} names a scenario more than once")
        if not os.access(EVALS / case / "run.sh", os.R_OK) or not (EVALS / case / "grader.py").is_file():
            raise Refused(f"case {case} has no readable run.sh and grader.py")
        specs[case] = spec
    deadline = seconds("EVAL_TIMEOUT", 900) + seconds("EVAL_GRADING_MARGIN", GRADING_MARGIN)
    env, secrets = agent_env()
    leaks = leak_patterns()
    tmp = Path(tempfile.mkdtemp(prefix="eval-suite-")).resolve()
    sections = []

    def unchanged() -> None:
        """Both checkouts are still at the commits the records name, with nothing uncommitted
        but the suite's own records: an attempt that changed either stops the suite."""
        for repo, role, commit in ((harness, "harness", harness_commit), (checkout, "skill", checkout_commit)):
            try:
                now = commit_of(repo, role)[1]
            except Refused as error:
                raise Broken(f"{error}, after an attempt of this run changed it") from None
            if now != commit:
                raise Broken(f"the {role} checkout moved from {commit} to {now} during the run")

    try:
        for root in (harness, checkout):
            if tmp == root or root in tmp.parents:
                raise Refused(f"the run directory {tmp} sits inside {root}; set TMPDIR outside both checkouts")
        roots = {"checkout": checkout} if harness == checkout else {"checkout": checkout, "harness": harness}
        names = Normaliser(leaks, secrets, tmp=tmp, **roots, tmpdir=Path(tempfile.gettempdir()), home=Path.home())
        command, model, effort = agent_config(names)
        ctx = {"label": args.label, "tmp": tmp, "checkout": checkout, "harness": harness, "resume": args.resume,
               "checkout_commit": checkout_commit, "checkout_short": checkout_short,
               "harness_commit": harness_commit, "harness_short": harness_short, "leaks": leaks,
               "secrets": secrets, "env": env, "deadline": deadline, "unchanged": unchanged,
               "agent_command": command, "model": model, "effort": effort, "counted": set()}
        for case in cases:
            case_dir, spec = EVALS / case, specs[case]
            # A relative path the grader's code names, such as sessions.json, is a file it
            # reads from the run directory; actions.jsonl is kept as the tool-call record.
            ctx.update(kind=str(spec.get("kind", "unset")),
                       grader_reads={name for name in grader_names(case_dir / "grader.py")
                                     if RELATIVE_FILE.fullmatch(name) and ".." not in name.split("/")})
            (case_dir / "results").mkdir(exist_ok=True)
            rows = [run_scenario(case_dir, scenario, args.runs, ctx) for scenario in spec["scenarios"]]
            sections.append({"case": case, "kind": ctx["kind"], "model": model, "effort": effort, "rows": rows})
        unchanged()
        # The summary accounts for every record of its label: a resume with fewer runs or
        # cases than the run started with would leave records out of it.
        uncounted = sorted(label_records(args.label) - ctx["counted"])
        if uncounted:
            raise Refused(f"{uncounted[0]} records an attempt of {args.label} that this run did not count; "
                          "--resume with the --runs and cases that run started with")
        short =[f"{s['case']} {r['name']}" for s in sections for r in s["rows"] if r["n"] < args.runs]
        (EVALS / "results").mkdir(exist_ok=True)
        write_new(summary_path, summary(args.label, args.runs, sections, short, ctx))
    finally:
        shutil.rmtree(tmp)  # scratch only: every record was written above
    if short:
        print(f"run-suite: fewer than {args.runs} graded runs for: {', '.join(short)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Refused as error:
        print(f"run-suite: {error}", file=sys.stderr)
        sys.exit(2)
    except Broken as error:
        print(f"run-suite: {error}", file=sys.stderr)
        sys.exit(1)
