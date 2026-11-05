#!/usr/bin/env python3
"""Resolve one model-launching role to its agent entry in the consumer profile.

  python3 resolve-model-role.py --role <role-key> [--repo DIR] [--json] [--dry-run]

<role-key> is a dotted path into the profile, such as review.pre_pr.arbiter, and may index
a role array from zero, such as refinement.reviewers[1]; a leading "profile." is accepted
and stripped from the reported role.

The profile is the first of these that exists, and a selected file that fails never falls
through to the next one:

  1. the path in $AGENT_SKILLS_PROFILE
  2. .agent-skills/profile.yaml at the root of the repository under review: --repo DIR when
     given, else the git work tree holding the working directory (none outside a work tree)
  3. ~/.config/agent-skills/profile.yaml

On success it prints role, runtime, model (the effective model), source (the absolute
profile path read) and, when the entry sets one, command, and nothing else: as "key: value"
lines in that order with backslashes and line breaks escaped, or with --json as one JSON
object. It only reads files; it never runs the command text or starts a model, and --dry-run
prints exactly what a normal run prints. Every failure exits 16 with one line on stderr and
nothing on stdout. Documented in shared/profile.md, "Resolve a model role".
"""

import argparse
import json
import os
import re
import subprocess
import sys

EXIT_UNRESOLVED = 16
NAME = "resolve-model-role"
# The runtimes profile/schema.json defines for an agent entry (tests keep the two in step).
MODEL_RUNTIMES = ("claude-code", "opencode", "codex")
RUNTIMES = MODEL_RUNTIMES + ("command",)
ENTRY_KEYS = ("name", "runtime", "model", "command")
SEGMENT = re.compile(r"([^.\[\]]+)((?:\[\d+\])*)")
INDEX = re.compile(r"\[(\d+)\]")
YAML_NOT_FOUND = "PyYAML is not installed"


class Unresolved(Exception):
    """A fail-closed stop: one stderr line, exit 16."""


def escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")


def parse_role(key: str) -> tuple[str, list[str | int]]:
    """The reported role (prefix stripped) and its path as mapping keys and list indexes."""
    role = key[len("profile."):] if key.startswith("profile.") else key
    path: list[str | int] = []
    for part in role.split("."):
        m = SEGMENT.fullmatch(part)
        if not m:
            raise Unresolved(f"role key {role!r} is not a dotted role path")
        path.append(m.group(1))
        path += [int(i) for i in INDEX.findall(m.group(2))]
    return role, path


def work_tree(cwd: str) -> str | None:
    """The top of the git work tree holding cwd, or None when git reports no work tree."""
    env = dict(os.environ, LC_ALL="C", LANG="C")
    try:
        res = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False,
        )
    except OSError as exc:
        raise Unresolved(f"cannot run git to find the repository root: {exc}") from exc
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    # The two benign misses: outside any repository, and inside a git directory with no work tree.
    if "not a git repository" in res.stderr or "must be run in a work tree" in res.stderr:
        return None
    raise Unresolved(f"git could not find the repository root: {res.stderr.strip()}")


def select(repo: str | None, searched: list[str]) -> str:
    """The first profile location that exists; `searched` records each location tried."""
    env_path = os.environ.get("AGENT_SKILLS_PROFILE") or None
    locations = [
        lambda: os.path.abspath(env_path) if env_path else None,
        lambda: repo_profile(repo),
        lambda: os.path.abspath(os.path.expanduser("~/.config/agent-skills/profile.yaml")),
    ]
    unset = ["$AGENT_SKILLS_PROFILE (unset)", ".agent-skills/profile.yaml (no git work tree)", None]
    for location, label in zip(locations, unset):
        path = location()
        if path is None:
            searched.append(label)
            continue
        if os.path.lexists(path):
            searched.append(f"{path} (selected)")
            return path
        searched.append(f"{path} (not found)")
    raise Unresolved("no profile found")


def repo_profile(repo: str | None) -> str | None:
    """The repository-local candidate: read only at the root of the repository under review."""
    if repo is not None and not os.path.isdir(repo):
        raise Unresolved(f"--repo {repo} is not a directory")
    root = os.path.abspath(repo) if repo is not None else work_tree(os.getcwd())
    return os.path.join(root, ".agent-skills", "profile.yaml") if root else None


def load(path: str, yaml) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise Unresolved(f"the selected profile is unreadable: {exc}") from exc
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise Unresolved(f"the selected profile is not valid YAML: {exc}") from exc
    if not isinstance(doc, dict):
        raise Unresolved("the selected profile is not a mapping")
    return doc


def entry_at(doc: dict, role: str, path: list[str | int]) -> dict:
    node = doc
    for step in path:
        if isinstance(step, int):
            if not isinstance(node, list) or step >= len(node):
                raise Unresolved(f"role {role} is absent from the profile")
            node = node[step]
        else:
            if not isinstance(node, dict) or step not in node:
                raise Unresolved(f"role {role} is absent from the profile")
            node = node[step]
    if not isinstance(node, dict) or not any(k in node for k in ENTRY_KEYS):
        raise Unresolved(f"role {role} does not resolve to an agent entry")
    return node


def text_value(entry: dict, key: str, role: str) -> str | None:
    """A non-empty string value, or None when the key is absent or blank."""
    value = entry.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise Unresolved(f"role {role} has a {key} that is not a string")
    return value if value.strip() else None


def classify(entry: dict, role: str) -> tuple[str, str, str | None]:
    """(runtime, effective model, command or None) for a usable entry."""
    if "runtime" not in entry and "command" not in entry:
        raise Unresolved(f"role {role} sets neither runtime nor command")
    runtime = entry.get("runtime", "command")
    if not isinstance(runtime, str) or runtime not in RUNTIMES:
        raise Unresolved(f"role {role} has runtime {runtime!r}, which the profile schema does not define")
    model = text_value(entry, "model", role)
    if runtime == "command":
        command = text_value(entry, "command", role)
        if command is None:
            raise Unresolved(f"role {role} has runtime command and no command")
        return runtime, model or "unresolved", command
    # A command on a model-launching runtime is ignored, so it never stands in for the model.
    if model is None:
        raise Unresolved(f"role {role} has runtime {runtime} and no model")
    return runtime, model, None


def render(fields: dict[str, str], as_json: bool) -> str:
    if as_json:
        return json.dumps(fields) + "\n"
    return "".join(f"{k}: {escape(v)}\n" for k, v in fields.items())


def import_yaml():
    here = os.path.abspath(__file__)
    action = "install it with: python3 -m pip install 'PyYAML>=6'"
    try:
        import yaml
    except ImportError as exc:
        raise Unresolved(f"{YAML_NOT_FOUND} ({exc}); {here} needs PyYAML>=6; {action}") from exc
    major = str(getattr(yaml, "__version__", "0")).split(".")[0]
    if not major.isdigit() or int(major) < 6:
        raise Unresolved(f"PyYAML {getattr(yaml, '__version__', 'unknown')} is too old; {here} needs PyYAML>=6; {action}")
    return yaml


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=NAME, description="Resolve a profile role to its agent entry.")
    parser.add_argument("--role", required=True, help="dotted role key, e.g. review.pre_pr.arbiter or refinement.reviewers[1]")
    parser.add_argument("--repo", help="root of the repository under review (default: the git work tree of the working directory)")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of key: value lines")
    parser.add_argument("--dry-run", action="store_true", help="print the resolution only; identical to a normal run, which never launches anything")
    args = parser.parse_args(argv)
    searched: list[str] = []
    try:
        source = select(args.repo, searched)
        yaml = import_yaml()
        role, path = parse_role(args.role)
        runtime, model, command = classify(entry_at(load(source, yaml), role, path), role)
    except Unresolved as exc:
        where = "; searched: " + ", ".join(searched) if searched else ""
        sys.stderr.write(escape(f"{NAME}: {exc}; profile key {args.role}{where}") + "\n")
        return EXIT_UNRESOLVED
    fields = {"role": role, "runtime": runtime, "model": model, "source": source}
    if command is not None:
        fields["command"] = command
    sys.stdout.write(render(fields, args.json))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
