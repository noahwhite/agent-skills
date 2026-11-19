#!/usr/bin/env python3
"""Judge a pull request's workflow files against the base branch's copies.

The gate-base workflow runs this script from the base commit and reads the head
checkout as data only. Against each base workflow, the head copy may add jobs,
steps and workflows, and may rename a workflow, job or step. Everything else must
stay as the base has it:

- every base workflow file is still present and parses;
- every top-level key other than `name` and `jobs` (triggers, permissions, env,
  concurrency, defaults) is unchanged, and none is added; trigger spellings that
  GitHub reads the same (`on: push`, `on: [push]`, `push:` empty or `{}`) match;
- every base job is present, with every key other than `name` and `steps` unchanged
  and none added;
- every base step is present, unchanged in every field other than `name`, and in
  the same order: the base steps, names aside, are an in-order subsequence of the
  head steps, so added steps may sit anywhere.

gate-base.yml itself may change only its workflow `name`, so nothing can be added to
the job that judges. No head workflow may define a job whose id or name is
`gate-base`, the name of the check this gate reports.

When --base-script is given, it must name a file, and --head-script must name a
file with the same bytes, so a pull request cannot weaken its own judge.

  scripts/gate_integrity.py --base DIR --head DIR [--base-script FILE --head-script FILE]

Exit 0 when nothing is violated, 1 when anything is violated or cannot be judged,
2 on a usage error.
"""

import argparse
import sys
from pathlib import Path

import yaml

GATE_WORKFLOW = "gate-base.yml"
GATE_CHECK = "gate-base"
SUFFIXES = (".yml", ".yaml")


def normalize_triggers(on):
    """Read the `on` value the way GitHub does: an event list or name is events with no filter."""
    if isinstance(on, str):
        return {on: {}}
    if isinstance(on, list) and all(isinstance(event, str) for event in on):
        return {event: {} for event in on}
    if isinstance(on, dict):
        return {event: {} if config is None else config for event, config in on.items()}
    return on


def load(path: Path):
    """Parse one workflow file; return (document, problem)."""
    if path.is_symlink() or not path.is_file():
        return None, "is not a regular file"
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError, OSError) as error:
        return None, f"does not parse: {error.__class__.__name__}"
    if not isinstance(document, dict):
        return None, "is not a mapping"
    # yaml.safe_load reads the bare key `on` as the boolean True; a quoted 'on' stays a string.
    if True in document and "on" in document:
        return None, "has two `on` keys"
    return {("on" if key is True else key): (normalize_triggers(value) if key in (True, "on") else value)
            for key, value in document.items()}, None


def label(key) -> str:
    return "on (trigger)" if key == "on" else str(key)


def without(mapping, *keys) -> dict:
    return {k: v for k, v in mapping.items() if k not in keys}


def step_body(step):
    return without(step, "name") if isinstance(step, dict) else step


def describe(position: int, step) -> str:
    name = step.get("name") if isinstance(step, dict) else None
    return f"step {position}" + (f" '{name}'" if isinstance(name, str) else "")


def compare_fields(base: dict, head: dict, ignored: tuple, where: str) -> list[str]:
    problems = []
    base_fields, head_fields = without(base, *ignored), without(head, *ignored)
    for key in base_fields:
        if key not in head_fields:
            problems.append(f"{where}: {label(key)} was removed")
        elif head_fields[key] != base_fields[key]:
            problems.append(f"{where}: {label(key)} changed")
    for key in head_fields:
        if key not in base_fields:
            problems.append(f"{where}: {label(key)} was added")
    return problems


def compare_steps(base_steps, head_steps, where: str) -> list[str]:
    """Each base step, names aside, must appear in the head after the previous one's match."""
    if not isinstance(base_steps, list):
        return [] if base_steps == head_steps else [f"{where}: steps changed"]
    if not isinstance(head_steps, list):
        return [f"{where}: steps are no longer a list"]
    head_bodies = [step_body(step) for step in head_steps]
    problems, last = [], -1
    for position, base_step in enumerate(base_steps, start=1):
        body = step_body(base_step)
        match = next((i for i in range(last + 1, len(head_bodies)) if head_bodies[i] == body), None)
        if match is not None:
            last = match
        elif body in head_bodies[:last + 1]:
            problems.append(f"{where}: {describe(position, base_step)} moved; base step order changed")
        else:
            problems.append(f"{where}: {describe(position, base_step)} was removed or changed")
    return problems


def compare_workflow(name: str, base: dict, head: dict) -> list[str]:
    if name == GATE_WORKFLOW:
        return compare_fields(base, head, ("name",), f"{name} (only its workflow name may change; a gate"
                                                     " change follows the owner's disable, merge, re-enable"
                                                     " procedure)")
    problems = compare_fields(base, head, ("name", "jobs"), name)
    base_jobs, head_jobs = base.get("jobs") or {}, head.get("jobs") or {}
    if not isinstance(base_jobs, dict):
        return problems + ([] if base_jobs == head_jobs else [f"{name}: jobs changed"])
    if not isinstance(head_jobs, dict):
        return problems + [f"{name}: jobs are no longer a mapping"]
    for job_id, base_job in base_jobs.items():
        where = f"{name} job '{job_id}'"
        head_job = head_jobs.get(job_id)
        if head_job is None:
            problems.append(f"{where} was removed")
            continue
        if not isinstance(base_job, dict) or not isinstance(head_job, dict):
            if base_job != head_job:
                problems.append(f"{where} changed")
            continue
        problems += compare_fields(base_job, head_job, ("name", "steps"), where)
        problems += compare_steps(base_job.get("steps"), head_job.get("steps"), where)
    return problems


def forged_checks(name: str, head: dict) -> list[str]:
    """A job whose check run would carry the gate's own check name."""
    jobs = head.get("jobs")
    if name == GATE_WORKFLOW or not isinstance(jobs, dict):
        return []
    return [f"{name} job '{job_id}' would report a check named {GATE_CHECK}"
            for job_id, job in jobs.items()
            if job_id == GATE_CHECK or (isinstance(job, dict) and job.get("name") == GATE_CHECK)]


def workflow_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if p.suffix.lower() in SUFFIXES)


def judge(base_dir: Path, head_dir: Path, base_script: Path | None, head_script: Path | None) -> list[str]:
    if head_dir.is_symlink() or head_dir.parent.is_symlink():
        return ["head .github/workflows is a symlink; the head checkout is judged only as it is"]
    problems = []
    base_names = set()
    for base_path in workflow_files(base_dir):
        name = base_path.name
        base_names.add(name)
        base, problem = load(base_path)
        if problem:
            problems.append(f"base {name} {problem}")
            continue
        head_path = head_dir / name
        if not head_path.exists() and not head_path.is_symlink():
            if name == GATE_WORKFLOW:
                problems.append(f"{name} was removed; the gate that judges workflow edits must stay")
            else:
                problems.append(f"{name} was removed")
            continue
        head, problem = load(head_path)
        if problem:
            problems.append(f"head {name} {problem}")
            continue
        problems += compare_workflow(name, base, head)
        problems += forged_checks(name, head)
    for head_path in workflow_files(head_dir):
        if head_path.name not in base_names:
            head, problem = load(head_path)
            if not problem:
                problems += forged_checks(head_path.name, head)
    if base_script is not None:
        if head_script is None or head_script.is_symlink() or not head_script.is_file():
            problems.append("scripts/gate_integrity.py was removed; the base copy judges and must stay")
        elif head_script.read_bytes() != base_script.read_bytes():
            problems.append("scripts/gate_integrity.py differs from base; a gate change follows the owner's"
                            " disable, merge, re-enable procedure")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", type=Path, required=True, help="base workflow directory")
    parser.add_argument("--head", type=Path, required=True, help="head workflow directory, read as data")
    parser.add_argument("--base-script", type=Path, help="base copy of scripts/gate_integrity.py")
    parser.add_argument("--head-script", type=Path, help="head copy of scripts/gate_integrity.py")
    args = parser.parse_args(argv)
    if not args.base.is_dir():
        parser.error(f"--base {args.base} is not a directory")
    if args.base_script is not None and (args.base_script.is_symlink() or not args.base_script.is_file()):
        parser.error(f"--base-script {args.base_script} is not a regular file")
    try:
        problems = judge(args.base, args.head, args.base_script, args.head_script)
    except (RecursionError, OSError) as error:
        problems = [f"could not judge: {error.__class__.__name__}"]
    for problem in problems:
        print(f"gate-base: {problem}")
    if problems:
        print(f"gate-base: FAIL, {len(problems)} violation(s)")
        return 1
    print("gate-base: PASS, every base workflow, job and step is unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
