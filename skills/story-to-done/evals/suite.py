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
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

EVALS = Path(__file__).resolve().parent
ROOT = EVALS.parents[2]
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
UUID = re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
# An absolute path of two or more segments that no known root above accounted for. The
# lookbehind keeps URLs (scheme://host/path) and relative paths (a/b/c) as they are.
ABSOLUTE_PATH = re.compile(r"(?<![\w.:/{}~-])/(?:[\w.@+-]+/)+[\w.@+-]*")
VOID_LINE = re.compile(r"^(HARNESS|run\.sh):")
GRADE_FILE = re.compile(r"grader(?:-(?P<grade>[A-Za-z0-9._-]+))?-output\.txt")
MODEL_FLAG = re.compile(r"--model=(\S+)|(?:^|\s)(?:--model|-m)\s+(\S+)")
VARIANCE = "k/n × (1 - k/n)"
# Seconds an attempt may run past the agent's own EVAL_TIMEOUT for the case's setup and grading.
GRADING_MARGIN = 300


class Refused(Exception):
    """The suite cannot start, or would overwrite a file: exit 2."""


class Broken(Exception):
    """An attempt exited with a status the case contract does not define: exit 1."""


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise Refused(f"git {' '.join(args)} failed in {repo}: {result.stderr.strip()}")
    return result.stdout.strip()


def is_record(path: str) -> bool:
    """True for a suite output path: a case's or the suite's results directory."""
    parts = Path(path).parts
    return "results" in parts[:-1]


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
    tree = ast.parse(grader.read_text(encoding="utf-8"))
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
    """Rewrites local and scratch paths and UUID shapes to placeholders, longest path first,
    then any other absolute path to {path} and anything else the leak scan rejects to
    {redacted}, so a record carries no path or identifier of the machine that ran it."""

    def __init__(self, leaks: list[re.Pattern], **paths: Path) -> None:
        pairs = {}
        for name, path in paths.items():
            for form in {str(path), str(path.resolve())}:
                if len(form) > 1:
                    pairs.setdefault(form, "{" + name + "}")
        self.pairs = sorted(pairs.items(), key=lambda pair: -len(pair[0]))
        self.leaks = leaks

    def __call__(self, text: str) -> str:
        for path, placeholder in self.pairs:
            # A root is only replaced whole: /home/user never rewrites /home/user2.
            text = re.sub(re.escape(path) + r"(?![\w.-])", lambda _: placeholder, text)
        text = UUID.sub("{uuid}", text)
        text = ABSOLUTE_PATH.sub("{path}", text)
        for regex in self.leaks:
            text = regex.sub("{redacted}", text)
        return text


def void_reason(stderr: str) -> str:
    """The reason run.sh states on a HARNESS: or run.sh: line, never other output, so no
    transcript text reaches a record or the summary."""
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


def verdicts(run_dir: Path, name: str, outcome: str) -> dict[str, str]:
    """Each grade's verdict, named for its scenario: grader-output.txt is the scenario's own
    grade, grader-<g>-output.txt a further grade named <scenario>-<g>. A case that writes no
    grade file is graded by run.sh's exit status alone."""
    found = {}
    for output in sorted(run_dir.glob("grader*-output.txt")):
        match = GRADE_FILE.fullmatch(output.name)
        if match:
            lines = [line.strip() for line in read(output).splitlines() if line.strip()]
            grade = name + (f"-{match['grade']}" if match["grade"] else "")
            found[grade] = "pass" if lines and lines[-1] == "PASS" else "fail"
    found.setdefault(name, outcome)
    return found


def run_attempt(case_dir: Path, name: str, run_dir: Path, ctx: dict) -> tuple[int | None, str]:
    """Run one attempt in its own process group; None as the status means it timed out."""
    process = subprocess.Popen(["bash", str(case_dir / "run.sh"), str(ctx["checkout"]), name, str(run_dir)],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    try:
        _, stderr = process.communicate(timeout=ctx["deadline"])
        return process.returncode, stderr.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        return None, ""
    except BaseException:
        os.killpg(process.pid, signal.SIGKILL)
        raise


def tally_record(tally: dict, record: dict) -> None:
    if record["outcome"] == "void":
        tally["voids"].append(f"attempt {record['attempt']}: {record['void_reason']}")
        return
    tally["n"] += 1
    for grade, verdict in record["verdicts"].items():
        tally["k"][grade] = tally["k"].get(grade, 0) + (verdict == "pass")


def run_scenario(case_dir: Path, scenario: dict, runs: int, ctx: dict) -> dict:
    name = scenario["name"]
    results = case_dir / "results"
    tally = {"n": 0, "k": {}, "voids": []}
    attempt = 0
    while tally["n"] < runs and attempt < 2 * runs:
        attempt += 1
        stem = f"{ctx['label']}-{name}-{ctx['checkout_short']}-harness-{ctx['harness_short']}-{attempt}"
        record_path, calls_path = results / f"{stem}.json", results / f"{stem}-calls.jsonl"
        if ctx["resume"] and record_path.is_file() and calls_path.is_file():
            tally_record(tally, json.loads(read(record_path)))
            continue
        for path in (record_path, calls_path):
            if path.exists():
                raise Refused(f"{path} exists; a suite run never overwrites a record")
        run_dir = ctx["tmp"] / f"{case_dir.name}-{name}-{attempt}"
        print(f"run-suite: {case_dir.name} {name} attempt {attempt}", file=sys.stderr, flush=True)
        code, stderr = run_attempt(case_dir, name, run_dir, ctx)
        normalise = Normaliser(ctx["leaks"], run_dir=run_dir, tmp=ctx["tmp"], checkout=ctx["checkout"],
                               harness=ctx["harness"], tmpdir=Path(tempfile.gettempdir()), home=Path.home())
        outcome = {0: "pass", 1: "fail", 2: "void", None: "void"}.get(code, "error")
        reason = None
        if code is None:
            reason = f"run.sh did not finish within {ctx['deadline']} seconds"
        elif outcome in ("void", "error"):
            reason = normalise(void_reason(stderr))
        grades, inputs, marks = {}, {}, {}
        if outcome in ("pass", "fail"):
            for output in sorted(run_dir.glob("grader*-output.txt")):
                grades[output.name] = normalise(read(output)).splitlines()
            marks = verdicts(run_dir, name, outcome)
            # Keep every run-directory file the grader names, beside the call record, so the
            # attempt can be graded again from what is committed.
            for file_name in sorted(ctx["grader_reads"]):
                path = run_dir / file_name
                if file_name != "actions.jsonl" and path.is_file():
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
        if run_dir.exists():  # run.sh may refuse before it creates the directory
            shutil.rmtree(run_dir)  # scratch only: the records above are what is kept
        if outcome == "error":
            raise Broken(f"{case_dir.name} {name} attempt {attempt}: run.sh exited {code} ({reason}); "
                         "only 0, 1 and 2 are defined, so the case or the machine is broken")
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


def agent_config(runtime: dict, normalise) -> tuple[str, str, str]:
    """The agent command, model and reasoning effort an attempt runs with. An EVAL_AGENT_CMD
    override must name its model with --model, and the model's #variant is its effort, so a
    record never claims the case's configuration for another agent."""
    override = os.environ.get("EVAL_AGENT_CMD", "").strip()
    if not override:
        return ("the case's run.sh default", str(runtime.get("model", "unset")),
                str(runtime.get("reasoning_effort", "unset")))
    match = MODEL_FLAG.search(override)
    if not match:
        raise Refused("EVAL_AGENT_CMD must name its model with --model, so the records can name it")
    model = match.group(1) or match.group(2)
    model, _, variant = model.partition("#")
    return normalise(override), model, variant or "default"


def main(argv: list[str]) -> int:
    args = parse(argv)
    summary_path = EVALS / "results" / f"suite-{args.label}.md"
    if summary_path.exists():
        raise Refused(f"{summary_path} exists; a suite run never overwrites a summary")
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
        if not os.access(EVALS / case / "run.sh", os.R_OK) or not (EVALS / case / "grader.py").is_file():
            raise Refused(f"case {case} has no readable run.sh and grader.py")
        specs[case] = spec
    leaks = leak_patterns()
    tmp = Path(tempfile.mkdtemp(prefix="eval-suite-")).resolve()
    sections = []
    try:
        for root in (harness, checkout):
            if tmp == root or root in tmp.parents:
                raise Refused(f"the run directory {tmp} sits inside {root}; set TMPDIR outside both checkouts")
        roots = {"checkout": checkout} if harness == checkout else {"checkout": checkout, "harness": harness}
        names = Normaliser(leaks, tmp=tmp, **roots, tmpdir=Path(tempfile.gettempdir()), home=Path.home())
        ctx = {"label": args.label, "tmp": tmp, "checkout": checkout, "harness": harness, "resume": args.resume,
               "checkout_commit": checkout_commit, "checkout_short": checkout_short,
               "harness_commit": harness_commit, "harness_short": harness_short, "leaks": leaks,
               "deadline": int(os.environ.get("EVAL_TIMEOUT") or 900)
               + int(os.environ.get("EVAL_GRADING_MARGIN") or GRADING_MARGIN)}
        for case in cases:
            case_dir, spec = EVALS / case, specs[case]
            runtime = spec.get("runtime") or {}
            command, model, effort = agent_config(runtime, names)
            ctx.update(kind=str(spec.get("kind", "unset")), agent_command=command, model=model, effort=effort,
                       grader_reads={name for name in grader_names(case_dir / "grader.py")
                                     if NAME.fullmatch(name) and "." in name})
            (case_dir / "results").mkdir(exist_ok=True)
            rows = [run_scenario(case_dir, scenario, args.runs, ctx) for scenario in spec["scenarios"]]
            sections.append({"case": case, "kind": ctx["kind"], "model": model, "effort": effort, "rows": rows})
        short = [f"{s['case']} {r['name']}" for s in sections for r in s["rows"] if r["n"] < args.runs]
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
