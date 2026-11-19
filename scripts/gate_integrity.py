#!/usr/bin/env python3
"""Judge a pull request's workflow files against the base branch's copies.

The gate-base workflow runs this script from the base commit and reads the head
checkout as data only. Against each base workflow, the head copy may add jobs,
steps and workflows, and may rename a workflow, job or step's display name only
where the name is not the step's identity. Everything else must stay as the base
has it:

- every base workflow file is still present and parses;
- every top-level key other than `name` and `jobs` (triggers, permissions, env,
  concurrency, defaults) is unchanged, and none is added;
- every base job is present, with every key other than `name` and `steps` unchanged
  and none added;
- every base step is present and unchanged in every field, in the same order.
  A named step is matched by its name (the n-th step of a name to the n-th step of
  that name); an unnamed step is matched by its position among the unnamed steps.

When --base-script names an existing file, --head-script must name a file with the
same bytes, so a pull request cannot weaken its own judge.

  scripts/gate_integrity.py --base DIR --head DIR [--base-script FILE --head-script FILE]

Exit 0 when nothing is violated, 1 when anything is, 2 on a usage error.
"""

import argparse
import sys
from pathlib import Path

import yaml

GATE_WORKFLOW = "gate-base.yml"
SUFFIXES = (".yml", ".yaml")


def load(path: Path):
    """Parse one workflow file; return (document, problem)."""
    if path.is_symlink() or not path.is_file():
        return None, "is not a regular file"
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError) as error:
        return None, f"does not parse: {error.__class__.__name__}"
    if not isinstance(document, dict):
        return None, "is not a mapping"
    return document, None


def label(key) -> str:
    # yaml.safe_load reads the bare key `on` as the boolean True; a quoted 'on' stays a string.
    return "on (trigger)" if key is True or key == "on" else str(key)


def step_keys(steps) -> list:
    """Identity of each step: (name, occurrence) when named, else ("unnamed", position)."""
    keys, seen, unnamed = [], {}, 0
    for step in steps:
        name = step.get("name") if isinstance(step, dict) else None
        if isinstance(name, str):
            seen[name] = seen.get(name, 0) + 1
            keys.append(("named", name, seen[name]))
        else:
            unnamed += 1
            keys.append(("unnamed", unnamed))
    return keys


def describe(key) -> str:
    if key[0] == "unnamed":
        return f"unnamed step {key[1]}"
    return f"step '{key[1]}'" + (f" (occurrence {key[2]})" if key[2] > 1 else "")


def without(mapping, *keys) -> dict:
    return {k: v for k, v in mapping.items() if k not in keys}


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
    if not isinstance(base_steps, list):
        return [] if base_steps == head_steps else [f"{where}: steps changed"]
    if not isinstance(head_steps, list):
        return [f"{where}: steps are no longer a list"]
    head_index = {key: i for i, key in enumerate(step_keys(head_steps))}
    problems, last = [], -1
    for key, base_step in zip(step_keys(base_steps), base_steps):
        i = head_index.get(key)
        if i is None:
            problems.append(f"{where}: {describe(key)} was removed")
            continue
        if head_steps[i] != base_step:
            problems.append(f"{where}: {describe(key)} changed")
        if i < last:
            problems.append(f"{where}: {describe(key)} moved; base step order changed")
        last = max(last, i)
    return problems


def compare_workflow(name: str, base: dict, head: dict) -> list[str]:
    problems = compare_fields(base, head, ("name", "jobs"), name)
    base_jobs, head_jobs = base.get("jobs") or {}, head.get("jobs") or {}
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


def workflow_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.iterdir() if p.suffix in SUFFIXES) if directory.is_dir() else []


def judge(base_dir: Path, head_dir: Path, base_script: Path | None, head_script: Path | None) -> list[str]:
    problems = []
    for base_path in workflow_files(base_dir):
        name = base_path.name
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
    if base_script is not None and base_script.is_file():
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
    problems = judge(args.base, args.head, args.base_script, args.head_script)
    for problem in problems:
        print(f"gate-base: {problem}")
    if problems:
        print(f"gate-base: FAIL, {len(problems)} violation(s)")
        return 1
    print("gate-base: PASS, every base workflow, job and step is unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
