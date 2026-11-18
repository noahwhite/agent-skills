# GENERATED from shared/resolve-full-suite.py by scripts/vendor_shared.py. Edit the source, then rerun the script.
#!/usr/bin/env python3
"""Resolve the full-suite option to on or off.

  python3 resolve-full-suite.py [--value on|off] [--story-key <KEY>] [--profile <path>]

The value is the first of these that is set:

  1. --value, the explicit argument; no profile is read
  2. profile.full_suite.teams[<team>]
  3. profile.full_suite.default
  4. off

The team is the prefix of --story-key (ABC for ABC-123), which need not equal
profile.tracker.team_key; without --story-key it is profile.tracker.team_key, and with neither the
teams step is skipped.

Without --profile the profile is the first of these that exists, the locations the skills load it
from, and a selected file that fails never falls through to the next one:

  1. the path in $AGENT_SKILLS_PROFILE
  2. .agent-skills/profile.yaml at the root of the git work tree holding the working directory
  3. ~/.config/agent-skills/profile.yaml

When none exists the value is off; a --profile that does not exist is an error. On success it exits 0 and prints exactly one line, on or off.
When a location's existence cannot be checked, git fails other than by reporting no work tree, the
profile is not a regular file, cannot be read or is not valid YAML, it is not a mapping, or
profile.full_suite is present and does not match profile/schema.json (an unquoted on or off value,
or an unquoted team key such as OFF, is a YAML boolean, not the string the schema needs), it prints a one-line reason to stderr, nothing to
stdout, and exits 16. A malformed command line, including a --value other than on or off or a
--story-key not shaped <TEAM>-<number>, exits 2. Reading a profile needs PyYAML>=6; it makes no
network call.
"""

from __future__ import annotations

import argparse
import os
import re
import stat
import subprocess
import sys

EXIT_UNRESOLVED = 16
GIT_TIMEOUT = 30
NAME = "resolve-full-suite"
VALUES = ("on", "off")
TEAM = re.compile(r"[A-Z][A-Z0-9]*")
STORY_KEY = re.compile(r"([A-Z][A-Z0-9]*)-[0-9]+")
ESCAPES = {"\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t"}


class Unresolved(Exception):
    """A fail-closed stop: one stderr line, nothing on stdout, exit 16."""


def escape(value: str) -> str:
    """One printable line, escaped as shared/select-path.py escapes."""
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


def work_tree() -> str | None:
    """The top of the git work tree holding the working directory, or None when git reports no
    work tree. Any other git failure stops the run rather than skipping the repository profile."""
    try:
        cwd = os.getcwd()
    except OSError as exc:
        raise Unresolved(f"cannot read the working directory to find the repository root: {exc}") from exc
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(LC_ALL="C", LANG="C")
    try:
        res = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            env=env, stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=GIT_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        raise Unresolved(f"git did not find the repository root within {GIT_TIMEOUT}s") from exc
    except OSError as exc:
        raise Unresolved(f"cannot run git to find the repository root: {exc}") from exc
    top = os.fsdecode(res.stdout[:-1] if res.stdout.endswith(b"\n") else res.stdout)
    err = res.stderr.decode("utf-8", "replace")
    if res.returncode == 0 and top:
        return top
    if "not a git repository" in err or "must be run in a work tree" in err:
        return None
    raise Unresolved(f"git could not find the repository root: {err.strip()}")


def present(path: str) -> bool:
    """Whether a location exists; one that cannot be checked stops the run rather than reading as absent."""
    try:
        os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError as exc:
        raise Unresolved(f"cannot check whether {path} exists: {exc.strerror or exc}") from exc
    return True


def find_profile(explicit: str | None) -> str | None:
    """The profile path, or None when no location holds one. Each candidate is computed only when
    every earlier one is absent, so git runs only when no profile is named."""
    def repo_candidate() -> str | None:
        root = work_tree()
        return os.path.join(root, ".agent-skills", "profile.yaml") if root else None

    if explicit is not None:
        candidates = [lambda: explicit]
    else:
        candidates = [
            lambda: os.environ.get("AGENT_SKILLS_PROFILE") or None,
            repo_candidate,
            lambda: os.path.expanduser("~/.config/agent-skills/profile.yaml"),
        ]
    for candidate in candidates:
        path = candidate()
        if path is None:
            continue
        try:
            path = os.path.abspath(path)
        except OSError as exc:
            raise Unresolved(f"cannot read the working directory to resolve {path}: {exc}") from exc
        if present(path):
            return path
        if explicit is not None:
            raise Unresolved(f"the profile {path} named by --profile does not exist")
    return None


def load(path: str) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise Unresolved(f"PyYAML is not installed ({exc}); install it with: python3 -m pip install 'PyYAML>=6'") from exc
    major = str(getattr(yaml, "__version__", "0")).split(".")[0]
    if not major.isdigit() or int(major) < 6:
        raise Unresolved(f"PyYAML {getattr(yaml, '__version__', 'unknown')} is too old; PyYAML>=6 is required")
    # Only a regular file is read; a FIFO or device would block or never end.
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError as exc:
        raise Unresolved(f"the profile {path} is unreadable: {exc}") from exc
    try:
        mode = os.fstat(fd).st_mode
        if stat.S_ISDIR(mode):
            raise Unresolved(f"the profile {path} is unreadable: it is a directory")
        if not stat.S_ISREG(mode):
            raise Unresolved(f"the profile {path} is not a regular file")
        chunks = []
        while chunk := os.read(fd, 65536):
            chunks.append(chunk)
    except OSError as exc:
        raise Unresolved(f"the profile {path} is unreadable: {exc}") from exc
    finally:
        os.close(fd)
    try:
        text = b"".join(chunks).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Unresolved(f"the profile {path} is unreadable: {exc}") from exc
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise Unresolved(f"the profile {path} is not valid YAML: {exc}") from exc
    except RecursionError as exc:
        raise Unresolved(f"the profile {path} is not valid YAML: it is nested too deeply") from exc
    if not isinstance(doc, dict):
        raise Unresolved(f"the profile {path} is not a mapping")
    return doc


def check_value(where: str, value) -> str:
    if isinstance(value, bool):
        raise Unresolved(f"{where} is the YAML boolean {str(value).lower()}; quote it as \"on\" or \"off\"")
    if value not in VALUES:
        raise Unresolved(f"{where} must be \"on\" or \"off\", not {value!r}")
    return value


def full_suite(doc: dict, path: str) -> dict:
    """profile.full_suite checked against its schema shape; {} when it is absent."""
    if "full_suite" not in doc:
        return {}
    node = doc["full_suite"]
    if not isinstance(node, dict):
        raise Unresolved(f"profile.full_suite in {path} must be a mapping")
    extra = sorted(str(k) for k in node if k not in ("default", "teams"))
    if extra:
        raise Unresolved(f"profile.full_suite in {path} has unknown keys: {', '.join(extra)}")
    if "default" in node:
        check_value(f"profile.full_suite.default in {path}", node["default"])
    teams = node.get("teams", {})
    if not isinstance(teams, dict):
        raise Unresolved(f"profile.full_suite.teams in {path} must be a mapping")
    for team, value in teams.items():
        if isinstance(team, bool):
            # YAML 1.1 reads an unquoted OFF, ON, YES or NO key as a boolean, so its spelling is lost.
            raise Unresolved(
                f"profile.full_suite.teams in {path} has a key YAML read as the boolean {str(team).lower()}; "
                "quote the team key, for example \"OFF\": \"on\""
            )
        if not (isinstance(team, str) and TEAM.fullmatch(team)):
            raise Unresolved(f"profile.full_suite.teams in {path} has a key {team!r} that is not an upper-case team key")
        check_value(f"profile.full_suite.teams.{team} in {path}", value)
    return node


def resolve(doc: dict, path: str, story_key: str | None) -> str:
    node = full_suite(doc, path)
    if story_key is not None:
        team = STORY_KEY.fullmatch(story_key).group(1)
    else:
        tracker = doc.get("tracker")
        if tracker is not None and not isinstance(tracker, dict):
            raise Unresolved(f"profile.tracker in {path} must be a mapping")
        team = tracker.get("team_key") if tracker is not None else None
        if team is not None and not (isinstance(team, str) and TEAM.fullmatch(team)):
            # An unquoted OFF reads as a boolean and a lower-case key never matches a teams key: fail closed,
            # never fall to the default.
            raise Unresolved(
                f"profile.tracker.team_key in {path} is {team!r}, not an upper-case team key string; "
                "quote it, for example team_key: \"OFF\""
            )
    teams = node.get("teams", {})
    if isinstance(team, str) and team in teams:
        return teams[team]
    return node.get("default", "off")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=NAME, description="Resolve the full-suite option to on or off.", allow_abbrev=False)
    parser.add_argument("--value", choices=VALUES, help="the explicit argument; it wins over the profile")
    parser.add_argument("--story-key", help="the story key, for example ABC-123; its prefix is the team")
    parser.add_argument("--profile", help="the profile file (default: the first of $AGENT_SKILLS_PROFILE, the repository profile, the home profile)")
    args = parser.parse_args(argv)
    if args.story_key is not None and not STORY_KEY.fullmatch(args.story_key):
        parser.error(f"argument --story-key: expected <TEAM>-<number>, not {args.story_key!r}")
    if args.value is not None:
        print(args.value)
        return 0
    try:
        path = find_profile(args.profile)
        value = "off" if path is None else resolve(load(path), path, args.story_key)
    except Unresolved as exc:
        sys.stderr.flush()
        sys.stderr.buffer.write((escape(f"{NAME}: {exc}") + "\n").encode("utf-8"))
        sys.stderr.buffer.flush()
        return EXIT_UNRESOLVED
    print(value)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
