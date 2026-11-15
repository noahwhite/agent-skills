# GENERATED from shared/select-path.py by scripts/vendor_shared.py. Edit the source, then rerun the script.
#!/usr/bin/env python3
"""Select a run's path: spike, no-deployment or deployed.

  python3 select-path.py [--profile <path>] --title <title> [--label <name> ...] [--recorded-path <value>]

story-to-done, engineering-workflow and qa-verification all call this one script, so the three
skills can never disagree on a story's path. --title is the story title and each --label is one of
the story's label names as read from the tracker; the script compares names only.

Without --profile the profile is the first of these that exists, and a selected file that fails
never falls through to the next one:

  1. the path in $AGENT_SKILLS_PROFILE
  2. .agent-skills/profile.yaml at the root of the git work tree holding the working directory
  3. ~/.config/agent-skills/profile.yaml

On success it exits 0 and prints exactly one line, the first of these that applies:

  1. the recorded path, when --recorded-path is spike, no-deployment or deployed
  2. ask: invalid-recorded-path, when --recorded-path is given with any other value
  3. ask: environments-absent, when profile.environments is absent or null
  4. ask: no-integration-branch, when profile.environments is a non-empty list with no entry
     whose branch equals profile.git.integration_branch
  5. ask: spike-title-without-label, when the title starts with [Spike] and no --label equals
     profile.tracker.labels.spike (including when that key is unset)
  6. ask: spike-label-without-title, when a --label equals profile.tracker.labels.spike and the
     title does not start with [Spike]
  7. spike, when a --label equals profile.tracker.labels.spike
  8. no-deployment, when profile.environments is []
  9. deployed

The [Spike] prefix and the label name are matched exactly and case-sensitively; an environments
entry that is not a mapping never matches. When no profile file exists, a location's existence
cannot be checked, git fails other than by reporting no work tree, the profile is not a regular
file, cannot be read or is not valid YAML, it is not a mapping, or profile.environments is
present but not a list, it prints a one-line reason to stderr, nothing to stdout, and exits 16.
A malformed command line, including an empty --title, exits 2; pass a value that starts with "-" as --title=<value> or
--label=<value>. It needs PyYAML>=6 and makes no network call.
"""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys

EXIT_UNRESOLVED = 16
GIT_TIMEOUT = 30
NAME = "select-path"
PATHS = ("spike", "no-deployment", "deployed")
SPIKE_PREFIX = "[Spike]"
ESCAPES = {"\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t"}


class Unresolved(Exception):
    """A fail-closed stop: one stderr line, nothing on stdout, exit 16."""


def escape(value: str) -> str:
    """One printable line, escaped as shared/resolve-model-role.py escapes: backslash, line feed,
    carriage return and tab as \\\\, \\n, \\r and \\t, any other control character as \\xNN, and a
    lone surrogate or a Unicode line or paragraph separator as \\uNNNN."""
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
    # The two benign misses: outside any repository, and inside a git directory with no work tree.
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


def find_profile(explicit: str | None) -> str:
    # Each candidate is computed only when every earlier one is absent, so git runs only when
    # neither --profile nor $AGENT_SKILLS_PROFILE names a profile.
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
    searched = []
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
        searched.append(path)
    raise Unresolved(f"no profile found; searched: {', '.join(searched) or 'nothing'}")


def load(path: str):
    try:
        import yaml
    except ImportError as exc:
        raise Unresolved(f"PyYAML is not installed ({exc}); install it with: python3 -m pip install 'PyYAML>=6'") from exc
    major = str(getattr(yaml, "__version__", "0")).split(".")[0]
    if not major.isdigit() or int(major) < 6:
        raise Unresolved(f"PyYAML {getattr(yaml, '__version__', 'unknown')} is too old; PyYAML>=6 is required")
    # A FIFO or device would block or never end; only a regular file is read. The type is checked
    # on the file opened without blocking, so a path swapped to a FIFO after discovery is refused too.
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


def get(doc: dict, *keys: str):
    """The value at a nested key path, or None when any step is absent or not a mapping."""
    node = doc
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def select(doc: dict, path: str, title: str, labels: list[str], recorded: str | None) -> str:
    environments = doc.get("environments")
    if environments is not None and not isinstance(environments, list):
        raise Unresolved(f"profile.environments in {path} is present but not a list")
    if recorded is not None:
        return recorded if recorded in PATHS else "ask: invalid-recorded-path"
    if environments is None:
        return "ask: environments-absent"
    integration = get(doc, "git", "integration_branch")
    if environments and not (
        isinstance(integration, str) and integration and any(isinstance(e, dict) and e.get("branch") == integration for e in environments)
    ):
        return "ask: no-integration-branch"
    spike_label = get(doc, "tracker", "labels", "spike")
    has_label = isinstance(spike_label, str) and spike_label in labels
    spike_title = title.startswith(SPIKE_PREFIX)
    if spike_title and not has_label:
        return "ask: spike-title-without-label"
    if has_label and not spike_title:
        return "ask: spike-label-without-title"
    if has_label:
        return "spike"
    if not environments:
        return "no-deployment"
    return "deployed"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=NAME, description="Select a run's path: spike, no-deployment or deployed.", allow_abbrev=False)
    parser.add_argument("--profile", help="the profile file (default: the first of $AGENT_SKILLS_PROFILE, the repository profile, the home profile)")
    parser.add_argument("--title", required=True, help="the story title")
    parser.add_argument("--label", action="append", default=[], help="one of the story's label names; repeat for each")
    parser.add_argument("--recorded-path", help="a path already recorded for the run")
    args = parser.parse_args(argv)
    if not args.title:
        # An empty title would read as "not a spike" and select a path; a failed title read must not.
        parser.error("argument --title: expected a non-empty story title")
    try:
        path = find_profile(args.profile)
        line = select(load(path), path, args.title, args.label, args.recorded_path)
    except Unresolved as exc:
        sys.stderr.flush()
        sys.stderr.buffer.write((escape(f"{NAME}: {exc}") + "\n").encode("utf-8"))
        sys.stderr.buffer.flush()
        return EXIT_UNRESOLVED
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
