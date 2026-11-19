#!/usr/bin/env python3
"""Judge a pull request's workflow files against the base branch's copies.

The gate-base workflow runs this script from the base commit and reads the head
checkout as data only. Against each base workflow, the head copy may add jobs and
workflows, may add steps after a base job's last step, and may rename a workflow,
job or step. Everything else must stay as the base has it:

- every base workflow file is still present and parses, without duplicate keys,
  with booleans read as GitHub reads them (so only an `on` key declares triggers);
- every top-level key other than `name` and `jobs` (triggers, permissions, env,
  concurrency, defaults) is unchanged, and none is added; trigger spellings that
  GitHub reads the same (`on: push`, `on: [push]`, `push:` empty or `{}`) match;
- every base job is present, with every key other than `name` and `steps` unchanged
  and none added;
- every job's `needs` in a base workflow names jobs of that workflow without a cycle,
  since GitHub rejects the whole file otherwise and no base job runs;
- a base job's head steps start with its base steps, in order and unchanged in
  every field other than `name`. An added step runs only after every base step, so
  it cannot change their execution (through $GITHUB_ENV, for example).

Values compare by type as well as value, so `true` does not match `1`.

gate-base.yml itself may change only its workflow `name`, so nothing can be added to
the job that judges. A head job may not report a check that a base job or this gate
reports: no added job, in any workflow, may have a check name (its `name`, else its
id) that is `gate-base` or a base job's check name, and no head job may take an
expression as its name unless the base job had that same name.

--base-script and --head-script go together: the head file must have the base
file's bytes, so a pull request cannot weaken its own judge.

  scripts/gate_integrity.py --base DIR --head DIR [--base-script FILE --head-script FILE]

Exit 0 when nothing is violated, 1 when anything is violated or cannot be judged,
2 on a usage error.
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

GATE_WORKFLOW = "gate-base.yml"
GATE_CHECK = "gate-base"
SUFFIXES = (".yml", ".yaml")


class UniqueKeyLoader(yaml.SafeLoader):
    """A safe loader that reads booleans as GitHub does and refuses a repeated mapping key.

    GitHub parses workflows with the YAML 1.2 core schema, where only true and false (in
    lower, title or upper case) are booleans. PyYAML's YAML 1.1 schema also reads on, off,
    yes and no as booleans, which would make a head `true:` key look like `on:`.
    """

    yaml_implicit_resolvers = {
        first: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:bool"]
        for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }

    def construct_mapping(self, node, deep=False):
        keys = [self.construct_object(key, deep=deep) for key, _ in node.value]
        for i, key in enumerate(keys):
            if key in keys[:i]:
                raise yaml.constructor.ConstructorError(None, None, f"duplicate key {key!r}", node.start_mark)
        return super().construct_mapping(node, deep=deep)


UniqueKeyLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF"))


def same(a, b) -> bool:
    """Equality that also requires the same types, so True does not match 1 or 15 match 15.0."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


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
        document = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except yaml.constructor.ConstructorError as error:
        if "duplicate key" in str(error.problem):
            return None, f"does not parse: {error.problem}"
        return None, f"does not parse: {error.__class__.__name__}"
    except (yaml.YAMLError, UnicodeDecodeError, OSError) as error:
        return None, f"does not parse: {error.__class__.__name__}"
    if not isinstance(document, dict):
        return None, "is not a mapping"
    return {key: normalize_triggers(value) if key == "on" else value for key, value in document.items()}, None


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
        elif not same(head_fields[key], base_fields[key]):
            problems.append(f"{where}: {label(key)} changed")
    for key in head_fields:
        if key not in base_fields:
            problems.append(f"{where}: {label(key)} was added")
    return problems


def compare_steps(base_steps, head_steps, where: str) -> list[str]:
    """The head steps must start with the base steps, names aside; added steps follow them."""
    if not isinstance(base_steps, list) or not isinstance(head_steps, list):
        return [] if same(base_steps, head_steps) else [f"{where}: steps changed"]
    problems = []
    head_bodies = [step_body(step) for step in head_steps]
    for position, base_step in enumerate(base_steps, start=1):
        body = step_body(base_step)
        if position <= len(head_bodies) and same(head_bodies[position - 1], body):
            continue
        if any(same(head_body, body) for head_body in head_bodies):
            problems.append(f"{where}: {describe(position, base_step)} is out of order (moved, or an added"
                            " step runs before it; added steps go after the base steps)")
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
    if not isinstance(base_jobs, dict) or not isinstance(head_jobs, dict):
        return problems + ([] if same(base_jobs, head_jobs) else [f"{name}: jobs changed"])
    for job_id, base_job in base_jobs.items():
        where = f"{name} job '{job_id}'"
        if job_id not in head_jobs:
            problems.append(f"{where} was removed")
            continue
        head_job = head_jobs[job_id]
        if not isinstance(base_job, dict) or not isinstance(head_job, dict):
            if not same(base_job, head_job):
                problems.append(f"{where} changed")
            continue
        problems += compare_fields(base_job, head_job, ("name", "steps"), where)
        problems += compare_steps(base_job.get("steps"), head_job.get("steps"), where)
    return problems + broken_needs(name, head_jobs)


def broken_needs(name: str, jobs: dict) -> list[str]:
    """Added jobs whose `needs` GitHub rejects, which stops every job in the file from running."""
    needs = {}
    for job_id, job in jobs.items():
        value = job.get("needs", []) if isinstance(job, dict) else []
        value = [value] if isinstance(value, str) else value
        if not isinstance(value, list) or not all(isinstance(n, str) for n in value):
            return [f"{name} job '{job_id}' needs something other than job ids"]
        missing = [n for n in value if n not in jobs]
        if missing:
            return [f"{name} job '{job_id}' needs a job that does not exist: {', '.join(missing)}"]
        needs[job_id] = value
    done, path = set(), []

    def cycle(job_id) -> bool:
        if job_id in path:
            return True
        if job_id in done:
            return False
        path.append(job_id)
        found = any(cycle(n) for n in needs[job_id])
        path.pop()
        done.add(job_id)
        return found

    if any(cycle(job_id) for job_id in needs):
        return [f"{name}: job needs form a cycle"]
    return []


def check_names(workflows: dict) -> dict:
    """(workflow file, job id) -> the check name the job reports: its `name`, else its id."""
    names = {}
    for file, workflow in workflows.items():
        jobs = workflow.get("jobs")
        for job_id, job in (jobs.items() if isinstance(jobs, dict) else ()):
            name = job.get("name") if isinstance(job, dict) else None
            names[(file, job_id)] = str(job_id) if name is None else name
    return names


def forged_checks(bases: dict, heads: dict) -> list[str]:
    """Head jobs that could report a check named like the gate's or a base job's."""
    base_names = check_names(bases)
    reserved = {GATE_CHECK, *(n for n in base_names.values() if isinstance(n, str))}
    problems = []
    for (file, job_id), name in check_names(heads).items():
        where = f"{file} job '{job_id}'"
        if (file, job_id) in base_names and same(base_names[(file, job_id)], name):
            continue
        if not isinstance(name, str) or "${{" in name:
            problems.append(f"{where} takes an expression as its name, so it could report any check name")
        elif name in reserved:
            problems.append(f"{where} would report a check named {name}, which a base job or this gate reports")
    return problems


def workflow_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if p.suffix.lower() in SUFFIXES)


def judge(base_dir: Path, head_dir: Path, base_script: Path | None, head_script: Path | None) -> list[str]:
    if head_dir.is_symlink() or head_dir.parent.is_symlink():
        return ["head .github/workflows is a symlink; the head checkout is judged only as it is"]
    problems, bases, heads = [], {}, {}
    for base_path in workflow_files(base_dir):
        base, problem = load(base_path)
        if problem:
            problems.append(f"base {base_path.name} {problem}")
        else:
            bases[base_path.name] = base
    for head_path in workflow_files(head_dir):
        head, problem = load(head_path)
        if problem:
            problems.append(f"head {head_path.name} {problem}")
        else:
            heads[head_path.name] = head
    for name, base in bases.items():
        head_path = head_dir / name
        if not head_path.exists() and not head_path.is_symlink():
            if name == GATE_WORKFLOW:
                problems.append(f"{name} was removed; the gate that judges workflow edits must stay")
            else:
                problems.append(f"{name} was removed")
        elif name in heads:
            problems += compare_workflow(name, base, heads[name])
    problems += forged_checks(bases, heads)
    if base_script is not None:
        if head_script.is_symlink() or not head_script.is_file():
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
    if (args.base_script is None) != (args.head_script is None):
        parser.error("--base-script and --head-script go together")
    if args.base_script is not None and (args.base_script.is_symlink() or not args.base_script.is_file()):
        parser.error(f"--base-script {args.base_script} is not a regular file")
    try:
        problems = judge(args.base, args.head, args.base_script, args.head_script)
    except (RecursionError, MemoryError, OSError) as error:
        problems = [f"could not judge: {error.__class__.__name__}"]
    for problem in problems:
        print(f"gate-base: {problem}")
    if problems:
        print(f"gate-base: FAIL, {len(problems)} violation(s)")
        return 1
    print("gate-base: PASS, no base workflow, job or step was changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
