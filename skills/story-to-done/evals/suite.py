#!/usr/bin/env python3
"""The eval suite runner behind run-suite.sh: repeat each case's scenarios, record, summarise.

Every attempt runs the case's own run.sh (CHECKOUT SCENARIO RUN_DIR), whose exit status is the
verdict: 0 graded pass, 1 graded fail, 2 void. Any other status is void too. A void attempt is
recorded with its reason and retried until the scenario has N graded runs or 2×N attempts.

Exit status: 0 every scenario reached N graded runs, 1 at least one did not, 2 the suite refused
to start or would have overwritten a file.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

EVALS = Path(__file__).resolve().parent
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
UUID = re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
VOID_LINE = re.compile(r"^(HARNESS|run\.sh):")
VARIANCE = "k/n × (1 - k/n)"


class Refused(Exception):
    """The suite cannot start, or would overwrite a file: exit 2."""


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise Refused(f"git {' '.join(args)} failed in {repo}: {result.stderr.strip()}")
    return result.stdout.strip()


def commit_of(repo: Path, role: str) -> tuple[Path, str, str]:
    """The checkout's root, full and short HEAD; a checkout with tracked changes is refused,
    because its commit would not describe what ran."""
    root = Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
    if git(root, "status", "--porcelain", "--untracked-files=no"):
        raise Refused(f"the {role} checkout {root} has uncommitted changes, so its commit would not describe the run")
    return root, git(root, "rev-parse", "HEAD"), git(root, "rev-parse", "--short=7", "HEAD")


def parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="run-suite.sh", description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=3, help="graded runs per scenario (default 3)")
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
    for case in args.cases:
        if not NAME.fullmatch(case) or not (EVALS / case / "case.yaml").is_file():
            parser.error(f"no case {case!r} in the harness checkout")
    return args


class Normaliser:
    """Rewrites local and scratch paths and UUID shapes to placeholders, longest path first, so a
    record carries no path of the machine that ran it."""

    def __init__(self, **paths: Path) -> None:
        pairs = {}
        for name, path in paths.items():
            for form in {str(path), str(path.resolve())}:
                if len(form) > 1:
                    pairs.setdefault(form, "{" + name + "}")
        self.pairs = sorted(pairs.items(), key=lambda pair: -len(pair[0]))

    def __call__(self, text: str) -> str:
        for path, placeholder in self.pairs:
            text = text.replace(path, placeholder)
        return UUID.sub("{uuid}", text)


def void_reason(code: int, stderr: str) -> str:
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    stated = next((line for line in lines if VOID_LINE.match(line)), lines[-1] if lines else "no reason given")
    return stated if code == 2 else f"run.sh exited {code}: {stated}"


def write_new(path: Path, text: str) -> None:
    try:
        with path.open("x") as handle:
            handle.write(text)
    except FileExistsError:
        raise Refused(f"{path} exists; a suite run never overwrites a record") from None


def run_scenario(case_dir: Path, scenario: dict, runs: int, ctx: dict) -> dict:
    name = scenario["name"]
    results = case_dir / "results"
    tally = {"n": 0, "k": 0, "voids": []}
    attempt = 0
    while tally["n"] < runs and attempt < 2 * runs:
        attempt += 1
        stem = f"{ctx['label']}-{name}-{ctx['checkout_short']}-harness-{ctx['harness_short']}-{attempt}"
        record_path, calls_path = results / f"{stem}.json", results / f"{stem}-calls.jsonl"
        for path in (record_path, calls_path):
            if path.exists():
                raise Refused(f"{path} exists; a suite run never overwrites a record")
        run_dir = ctx["tmp"] / f"{case_dir.name}-{name}-{attempt}"
        print(f"run-suite: {case_dir.name} {name} attempt {attempt}", file=sys.stderr, flush=True)
        done = subprocess.run([str(case_dir / "run.sh"), str(ctx["checkout"]), name, str(run_dir)],
                              stdin=subprocess.DEVNULL, capture_output=True, text=True)
        normalise = Normaliser(run_dir=run_dir, tmp=ctx["tmp"], checkout=ctx["checkout"],
                               harness=ctx["harness"], tmpdir=Path(tempfile.gettempdir()), home=Path.home())
        outcome = {0: "pass", 1: "fail"}.get(done.returncode, "void")
        reason = normalise(void_reason(done.returncode, done.stderr)) if outcome == "void" else None
        grades = {}
        if outcome != "void":
            tally["n"] += 1
            tally["k"] += outcome == "pass"
            for output in sorted(run_dir.glob("grader*-output.txt")):
                grades[output.name] = normalise(output.read_text()).splitlines()
        else:
            tally["voids"].append(f"attempt {attempt}: {reason}")
        actions = run_dir / "actions.jsonl"
        calls = normalise(actions.read_text()) if actions.is_file() else ""
        record = {
            "case": case_dir.name, "scenario": name, "label": ctx["label"], "attempt": attempt,
            "checkout_commit": ctx["checkout_commit"], "harness_commit": ctx["harness_commit"],
            "model": ctx["model"], "reasoning_effort": ctx["effort"], "agent_command": ctx["agent_command"],
            "exit_code": done.returncode, "outcome": outcome, "void_reason": reason, "grades": grades,
        }
        write_new(record_path, json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        write_new(calls_path, calls)
        if run_dir.exists():  # run.sh may refuse before it creates the directory
            shutil.rmtree(run_dir)  # scratch only: the records above are what is kept
    return {"name": name, "role": "control (regression pin)" if "control" in scenario else ctx["kind"], **tally}


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def summary(label: str, runs: int, sections: list[dict], ctx: dict) -> str:
    lines = [
        f"# Eval suite run `{label}`",
        "",
        f"- Graded runs asked for per scenario (N): {runs}; void runs are retried up to {2 * runs} attempts.",
        f"- Skill commit (CHECKOUT): `{ctx['checkout_commit']}`",
        f"- Harness commit: `{ctx['harness_commit']}`",
        f"- Agent command: {ctx['agent_command']}",
        f"- n is the graded run count, k the pass count, and the pass rate is k/n.",
        f"- Variance is {VARIANCE}, the variance of one run's pass or fail at the observed pass rate.",
        "- A scenario with n = 0 reports its pass rate and variance as `n/a`.",
        "- Counts and provenance only; each attempt's run record and tool-call record are under the case's `results/`.",
    ]
    for section in sections:
        lines += ["", f"## {section['case']} ({section['kind']})", "",
                  "| Scenario | Role | Skill commit | Harness commit | Model | Reasoning effort | n | k "
                  "| Pass rate k/n | Variance | Voids | Void reasons |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for row in section["rows"]:
            n, k = row["n"], row["k"]
            rate = f"{k}/{n} = {k / n:.3f}" if n else "n/a"
            variance = f"{(k / n) * (1 - k / n):.3f}" if n else "n/a"
            reasons = "; ".join(row["voids"]) or "none"
            lines.append(f"| {row['name']} | {row['role']} | {ctx['checkout_short']} | {ctx['harness_short']} "
                         f"| {cell(section['model'])} | {cell(section['effort'])} | {n} | {k} | {rate} "
                         f"| {variance} | {len(row['voids'])} | {cell(reasons)} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    args = parse(argv)
    harness, harness_commit, harness_short = commit_of(EVALS, "harness")
    checkout, checkout_commit, checkout_short = commit_of(args.checkout, "skill")
    cases = args.cases or sorted(path.parent.name for path in EVALS.glob("*/case.yaml"))
    summary_path = EVALS / "results" / f"suite-{args.label}.md"
    if summary_path.exists():
        raise Refused(f"{summary_path} exists; a suite run never overwrites a summary")
    tmp = Path(tempfile.mkdtemp(prefix="eval-suite-")).resolve()
    try:
        for root in (harness, checkout):
            if tmp == root or root in tmp.parents:
                raise Refused(f"the run directory {tmp} sits inside {root}; set TMPDIR outside both checkouts")
        ctx = {"label": args.label, "tmp": tmp, "checkout": checkout, "harness": harness,
               "checkout_commit": checkout_commit, "checkout_short": checkout_short,
               "harness_commit": harness_commit, "harness_short": harness_short,
               "agent_command": "EVAL_AGENT_CMD override" if os.environ.get("EVAL_AGENT_CMD")
               else "the case's run.sh default"}
        sections = []
        for case in cases:
            case_dir = EVALS / case
            spec = yaml.safe_load((case_dir / "case.yaml").read_text())
            runtime = spec.get("runtime") or {}
            ctx.update(kind=spec.get("kind", "unset"), model=str(runtime.get("model", "unset")),
                       effort=str(runtime.get("reasoning_effort", "unset")))
            (case_dir / "results").mkdir(exist_ok=True)
            rows = [run_scenario(case_dir, scenario, args.runs, ctx) for scenario in spec["scenarios"]]
            sections.append({"case": case, "kind": ctx["kind"], "model": ctx["model"], "effort": ctx["effort"],
                             "rows": rows})
        (EVALS / "results").mkdir(exist_ok=True)
        write_new(summary_path, summary(args.label, args.runs, sections, ctx))
    finally:
        shutil.rmtree(tmp)  # scratch only: every record was written above
    short = [f"{s['case']} {r['name']}" for s in sections for r in s["rows"] if r["n"] < args.runs]
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
