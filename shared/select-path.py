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

The [Spike] prefix and the label name are matched exactly and case-sensitively. When no profile
file exists, the profile cannot be read or is not valid YAML, it is not a mapping, or
profile.environments is present but not a list of mappings, it prints a one-line reason to
stderr, nothing to stdout, and exits 16. A malformed command line exits 2. It needs PyYAML>=6
and makes no network call.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

EXIT_UNRESOLVED = 16
NAME = "select-path"
PATHS = ("spike", "no-deployment", "deployed")
SPIKE_PREFIX = "[Spike]"


class Unresolved(Exception):
    """A fail-closed stop: one stderr line, nothing on stdout, exit 16."""


def work_tree() -> str | None:
    """The top of the git work tree holding the working directory, or None outside one."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(LC_ALL="C", LANG="C")
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            env=env, stdin=subprocess.DEVNULL, capture_output=True, check=False,
        )
    except OSError:
        return None
    top = os.fsdecode(res.stdout.rstrip(b"\n"))
    return top if res.returncode == 0 and top else None


def find_profile(explicit: str | None) -> str:
    if explicit is not None:
        candidates = [explicit]
    else:
        env_path = os.environ.get("AGENT_SKILLS_PROFILE") or None
        root = work_tree()
        candidates = [
            env_path,
            os.path.join(root, ".agent-skills", "profile.yaml") if root else None,
            os.path.expanduser("~/.config/agent-skills/profile.yaml"),
        ]
    searched = []
    for path in candidates:
        if path is None:
            continue
        path = os.path.abspath(path)
        if os.path.lexists(path):
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
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
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
    if environments is not None:
        if not isinstance(environments, list):
            raise Unresolved(f"profile.environments in {path} is present but not a list")
        if not all(isinstance(entry, dict) for entry in environments):
            raise Unresolved(f"profile.environments in {path} holds an entry that is not a mapping")
    if recorded is not None:
        return recorded if recorded in PATHS else "ask: invalid-recorded-path"
    if environments is None:
        return "ask: environments-absent"
    integration = get(doc, "git", "integration_branch")
    if environments and not (
        isinstance(integration, str) and integration and any(e.get("branch") == integration for e in environments)
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
    parser = argparse.ArgumentParser(prog=NAME, description="Select a run's path: spike, no-deployment or deployed.")
    parser.add_argument("--profile", help="the profile file (default: the first of $AGENT_SKILLS_PROFILE, the repository profile, the home profile)")
    parser.add_argument("--title", required=True, help="the story title")
    parser.add_argument("--label", action="append", default=[], help="one of the story's label names; repeat for each")
    parser.add_argument("--recorded-path", help="a path already recorded for the run")
    args = parser.parse_args(argv)
    try:
        path = find_profile(args.profile)
        line = select(load(path), path, args.title, args.label, args.recorded_path)
    except Unresolved as exc:
        print(f"{NAME}: {exc}".replace("\n", " "), file=sys.stderr)
        return EXIT_UNRESOLVED
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
