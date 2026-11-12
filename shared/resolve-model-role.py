#!/usr/bin/env python3
"""Resolve one model-launching role to its agent entry in the consumer profile.

  python3 resolve-model-role.py --role <role-key> [--repo DIR] [--json] [--dry-run] [--require-model]

<role-key> is a dotted path into the profile, such as review.pre_pr.arbiter, and may index
a role array from zero, such as refinement.reviewers[1]; a leading "profile." is accepted
and stripped from the reported role.

The profile is the first of these that exists, and a selected file that fails never falls
through to the next one:

  1. the path in $AGENT_SKILLS_PROFILE
  2. .agent-skills/profile.yaml at the root of the repository under review: --repo DIR when
     given, else the git work tree holding the working directory (none outside a work tree)
  3. ~/.config/agent-skills/profile.yaml

On success it prints role, runtime, model (the effective model), effort when the entry sets
one, source (the absolute profile path read) and, when the entry sets one, command, and
nothing else: as "key: value"
lines in that order with backslashes, control characters, lone surrogates and Unicode
line and paragraph separators escaped, or
with --json as one JSON object. It only reads files; it never runs the command text or starts
a model, and --dry-run prints exactly what a normal run prints. --require-model makes a
runtime: command entry with no model a resolution failure, for a caller such as story-to-done
whose seat cannot launch without one. Every resolution failure exits
16 with one line on stderr and nothing on stdout; a malformed command line exits 2 with
argparse's usage message. Documented in shared/profile.md, "Resolve a model role".
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys

EXIT_UNRESOLVED = 16
NAME = "resolve-model-role"
# The runtimes profile/schema.json defines for an agent entry (tests keep the two in step).
MODEL_RUNTIMES = ("claude-code", "opencode", "codex")
RUNTIMES = MODEL_RUNTIMES + ("command",)
# The reasoning efforts profile/schema.json defines for a seat (tests keep the two in step).
EFFORTS = ("low", "medium", "high", "xhigh", "max")
ENTRY_KEYS = ("name", "runtime", "model", "command")
SEGMENT = re.compile(r"([^.\[\]]+)((?:\[\d+\])*)")
INDEX = re.compile(r"\[(\d+)\]")
YAML_NOT_FOUND = "PyYAML is not installed"


class Unresolved(Exception):
    """A fail-closed stop: one stderr line, exit 16."""


ESCAPES = {"\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def escape(value: str) -> str:
    """One printable line: backslash, line feed, carriage return and tab as \\, \\n, \\r and
    \\t, any other control character as \\xNN, and a lone surrogate or a Unicode line or
    paragraph separator as \\uNNNN."""
    out = []
    for ch in value:
        code = ord(ch)
        if ch in ESCAPES:
            out.append(ESCAPES[ch])
        elif code < 0x20 or 0x7F <= code < 0xA0:
            out.append(f"\\x{code:02x}")
        elif 0xD800 <= code < 0xE000 or code in (0x2028, 0x2029):
            out.append(f"\\u{code:04x}")
        else:
            out.append(ch)
    return "".join(out)


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
    """The top of the git work tree holding cwd, or None when git reports no work tree.

    Every inherited GIT_* variable is dropped, so a caller's GIT_DIR, GIT_WORK_TREE or
    GIT_CEILING_DIRECTORIES (a git hook or a CI job sets them) cannot point discovery at a
    tree that does not hold cwd."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(LC_ALL="C", LANG="C")
    try:
        res = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            env=env, stdin=subprocess.DEVNULL, capture_output=True, check=False,
        )
    except OSError as exc:
        raise Unresolved(f"cannot run git to find the repository root: {exc}") from exc
    # Path bytes decode as the filesystem does, so a root that is not valid UTF-8 still resolves.
    top = os.fsdecode(res.stdout[:-1] if res.stdout.endswith(b"\n") else res.stdout)
    err = res.stderr.decode("utf-8", "replace")
    if res.returncode == 0 and top:
        return top
    # The two benign misses: outside any repository, and inside a git directory with no work tree.
    if "not a git repository" in err or "must be run in a work tree" in err:
        return None
    raise Unresolved(f"git could not find the repository root: {err.strip()}")


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
        if present(path, searched):
            searched.append(f"{path} (selected)")
            return path
        searched.append(f"{path} (not found)")
    raise Unresolved("no profile found")


def present(path: str, searched: list[str]) -> bool:
    """Whether a location exists; one that cannot be checked fails rather than reading as absent."""
    try:
        os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError as exc:
        searched.append(f"{path} (cannot check)")
        raise Unresolved(f"cannot check whether {path} exists: {exc.strerror or exc}") from exc
    return True


def repo_profile(repo: str | None) -> str | None:
    """The repository-local candidate: read only at the root of the repository under review."""
    if repo is not None and not os.path.isdir(repo):
        raise Unresolved(f"--repo {repo} is not a directory")
    if repo is not None:
        root = os.path.abspath(repo)
    else:
        try:
            cwd = os.getcwd()
        except OSError as exc:
            raise Unresolved(f"cannot read the working directory to find the repository root: {exc}") from exc
        root = work_tree(cwd)
    return os.path.join(root, ".agent-skills", "profile.yaml") if root else None


def load(path: str, yaml) -> dict:
    # A FIFO or device would block or never end; only a regular file is read. The type is
    # checked on the opened file, which is opened without blocking, so a path swapped to a
    # FIFO after discovery is refused too.
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError as exc:
        raise Unresolved(f"the selected profile is unreadable: {exc}") from exc
    try:
        mode = os.fstat(fd).st_mode
        if stat.S_ISDIR(mode):
            raise Unresolved("the selected profile is unreadable: it is a directory")
        if not stat.S_ISREG(mode):
            raise Unresolved("the selected profile is not a regular file")
        chunks = []
        while chunk := os.read(fd, 65536):
            chunks.append(chunk)
    except OSError as exc:
        raise Unresolved(f"the selected profile is unreadable: {exc}") from exc
    finally:
        os.close(fd)
    try:
        text = b"".join(chunks).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Unresolved(f"the selected profile is unreadable: {exc}") from exc
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise Unresolved(f"the selected profile is not valid YAML: {exc}") from exc
    except RecursionError as exc:
        raise Unresolved("the selected profile is not valid YAML: it is nested too deeply") from exc
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


def classify(entry: dict, role: str, require_model: bool = False) -> tuple[str, str, str | None]:
    """(runtime, effective model, command or None) for a usable entry."""
    if entry.get("runtime") is None and entry.get("command") is None:
        raise Unresolved(f"role {role} sets neither runtime nor command")
    # A null runtime is an unset one, so an entry with only a command reads as runtime: command.
    runtime = entry.get("runtime")
    if runtime is None:
        runtime = "command"
    if not isinstance(runtime, str) or runtime not in RUNTIMES:
        raise Unresolved(f"role {role} has runtime {runtime!r}, which the profile schema does not define")
    model = text_value(entry, "model", role)
    if runtime == "command":
        command = text_value(entry, "command", role)
        if command is None:
            raise Unresolved(f"role {role} has runtime command and no command")
        if model is None and require_model:
            raise Unresolved(f"role {role} has runtime command and no model, and --require-model is set")
        return runtime, model or "unresolved", command
    # A command on a model-launching runtime is ignored, so it never stands in for the model.
    if model is None:
        raise Unresolved(f"role {role} has runtime {runtime} and no model")
    return runtime, model, None


def effort_of(entry: dict, role: str) -> str | None:
    """The entry's effort, or None when it sets none; a value outside the schema enum fails."""
    if "effort" not in entry or entry["effort"] is None:
        return None
    effort = entry["effort"]
    if not isinstance(effort, str) or effort not in EFFORTS:
        raise Unresolved(f"role {role} has effort {effort!r}, which the profile schema does not define")
    return effort


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
    except (Exception, SystemExit) as exc:  # a broken installation can raise anything at import
        raise Unresolved(
            f"PyYAML could not be imported ({type(exc).__name__}: {exc}); {here} needs PyYAML>=6; {action}"
        ) from exc
    major = str(getattr(yaml, "__version__", "0")).split(".")[0]
    if not major.isdigit() or int(major) < 6:
        raise Unresolved(f"PyYAML {getattr(yaml, '__version__', 'unknown')} is too old; {here} needs PyYAML>=6; {action}")
    error = getattr(yaml, "YAMLError", None)
    if not callable(getattr(yaml, "safe_load", None)) or not (isinstance(error, type) and issubclass(error, Exception)):
        raise Unresolved(f"PyYAML {yaml.__version__} lacks safe_load or YAMLError; {here} needs PyYAML>=6; {action}")
    return yaml


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=NAME, description="Resolve a profile role to its agent entry.")
    parser.add_argument("--role", required=True, help="dotted role key, e.g. review.pre_pr.arbiter or refinement.reviewers[1]")
    parser.add_argument("--repo", help="root of the repository under review (default: the git work tree of the working directory)")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of key: value lines")
    parser.add_argument("--require-model", action="store_true", help="fail when a runtime: command entry sets no model")
    parser.add_argument("--dry-run", action="store_true", help="print the resolution only; identical to a normal run, which never launches anything")
    args = parser.parse_args(argv)
    searched: list[str] = []
    try:
        try:
            source = select(args.repo, searched)
        except Unresolved:
            import_yaml()  # a missing PyYAML is the more actionable report, profile or not
            raise
        yaml = import_yaml()
        role, path = parse_role(args.role)
        entry = entry_at(load(source, yaml), role, path)
        runtime, model, command = classify(entry, role, args.require_model)
        effort = effort_of(entry, role)
    except Unresolved as exc:
        where = "; searched: " + ", ".join(searched) if searched else ""
        emit(sys.stderr, escape(f"{NAME}: {exc}; profile key {args.role}{where}") + "\n")
        return EXIT_UNRESOLVED
    fields = {"role": role, "runtime": runtime, "model": model}
    if effort is not None:
        fields["effort"] = effort
    fields["source"] = source
    if command is not None:
        fields["command"] = command
    emit(sys.stdout, render(fields, args.json))
    return 0


def emit(stream, text: str) -> None:
    """Write UTF-8 whatever the locale; escape() and json.dumps leave nothing unencodable."""
    stream.flush()
    stream.buffer.write(text.encode("utf-8"))
    stream.buffer.flush()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
