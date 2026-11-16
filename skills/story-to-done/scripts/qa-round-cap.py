#!/usr/bin/env python3
"""Count story-to-done QA rounds against the `qa-round-cap` argument.

The count lives in <state-dir>/qa-round-cap/<KEY>.json. `record` and `rearm` read the story
through the ambient `linear` CLI (`linear issue view <KEY> --json`) and never write to the tracker.
A QA round is a story comment whose first line is exactly `## QA evidence`.
"""

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

POSITIVE = re.compile(r"[1-9][0-9]*")
STORY = re.compile(r"[A-Z][A-Z0-9]*-[1-9][0-9]*")
MARKER = "## QA evidence"
TRACKER_TIMEOUT = 120

EXIT_CODES = """exit codes:
  0  success
  1  any other failure (no count armed, unreadable state, failed tracker read)
  2  invalid argument or unknown subcommand
  3  the story's state is not the in_progress state given to arm

Every non-zero exit prints one stderr line and leaves the state file unchanged."""


class Refusal(Exception):
    def __init__(self, code: int, line: str) -> None:
        super().__init__(line)
        self.code = code
        self.line = line


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise Refusal(2, f"{self.prog}: {message}")


def positive(value: str, name: str) -> int:
    if not POSITIVE.fullmatch(value):
        raise Refusal(2, f"invalid {name}: expected a positive integer")
    return int(value)


def story_key(value: str) -> str:
    if not STORY.fullmatch(value):
        raise Refusal(2, "invalid --story: expected a story key such as ABC-123")
    return value


def state_path(state_dir: str, key: str) -> Path:
    return Path(state_dir) / "qa-round-cap" / f"{key}.json"


def load(state_dir: str, key: str) -> dict:
    path = state_path(state_dir, key)
    try:
        state = json.loads(path.read_text())
    except FileNotFoundError:
        raise Refusal(1, f"no QA round count armed for {key}: run arm first") from None
    except (OSError, ValueError):
        raise Refusal(1, f"unreadable QA round state for {key}") from None
    if not (
        isinstance(state, dict)
        and isinstance(state.get("cap"), int)
        and isinstance(state.get("in_progress"), str)
        and isinstance(state.get("armed_at"), str)
        and isinstance(state.get("rounds"), list)
    ):
        raise Refusal(1, f"unreadable QA round state for {key}")
    return state


def save(state_dir: str, key: str, state: dict) -> None:
    path = state_path(state_dir, key)
    path.parent.mkdir(exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=f".{key}.", suffix=".tmp", delete=False)
    try:
        with handle:
            json.dump(state, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, path)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise


def timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("not a timestamp")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp has no zone")
    return parsed


def read_story(key: str) -> tuple[str, list[dict]]:
    """Return the story's state name and comments, read through the ambient `linear` auth."""
    try:
        result = subprocess.run(
            ["linear", "issue", "view", key, "--json"],
            capture_output=True,
            text=True,
            timeout=TRACKER_TIMEOUT,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Refusal(1, f"tracker read failed for {key}") from None
    if result.returncode != 0:
        raise Refusal(1, f"tracker read failed for {key} (linear exit {result.returncode})")
    try:
        issue = json.loads(result.stdout)
        name = issue["state"]["name"]
        nodes = issue.get("comments", {}).get("nodes", [])
        if not isinstance(name, str) or not name or not isinstance(nodes, list):
            raise ValueError("unexpected shape")
    except (ValueError, TypeError, KeyError, AttributeError):
        raise Refusal(1, f"tracker read for {key} returned an unexpected payload") from None
    return name, nodes


def first_line(body: str) -> str:
    return body.split("\n", 1)[0].rstrip()


def summary(state: dict) -> str:
    rounds = len(state["rounds"])
    return f"round={rounds} cap={state['cap']} reached={'yes' if rounds >= state['cap'] else 'no'}"


def cmd_validate(args: argparse.Namespace) -> str:
    name, sep, value = args.token.partition("=")
    if name != "qa-round-cap" or not sep:
        raise Refusal(2, "invalid argument: expected qa-round-cap=<n>")
    return str(positive(value, "qa-round-cap"))


def checked_state_dir(value: str) -> str:
    if not Path(value).is_dir():
        raise Refusal(2, "invalid --state-dir: not an existing directory")
    return value


def cmd_arm(args: argparse.Namespace) -> str:
    key = story_key(args.story)
    cap = positive(args.cap, "--cap")
    if not args.in_progress.strip():
        raise Refusal(2, "invalid --in-progress: expected the in_progress state name")
    state_dir = checked_state_dir(args.state_dir)
    state = {
        "story": key,
        "count_id": secrets.token_hex(8),
        "cap": cap,
        "in_progress": args.in_progress,
        "armed_at": datetime.now(timezone.utc).isoformat(),
        "rounds": [],
    }
    save(state_dir, key, state)
    return summary(state)


def cmd_record(args: argparse.Namespace) -> str:
    key = story_key(args.story)
    state_dir = checked_state_dir(args.state_dir)
    state = load(state_dir, key)
    name, comments = read_story(key)
    if name != state["in_progress"]:
        raise Refusal(3, f"state={name}")
    try:
        counted = {r["comment_id"] for r in state["rounds"]}
        since = timestamp(state["rounds"][-1]["created_at"] if state["rounds"] else state["armed_at"])
    except (KeyError, TypeError, ValueError):
        raise Refusal(1, f"unreadable QA round state for {key}") from None
    candidates = []
    for comment in comments:
        try:
            if first_line(comment["body"]) != MARKER or comment["id"] in counted:
                continue
            created = timestamp(comment["createdAt"])
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if created > since:
            candidates.append((created, comment))
    if candidates:
        created, comment = max(candidates, key=lambda item: item[0])
        state["rounds"].append(
            {"round": len(state["rounds"]) + 1, "comment_id": comment["id"], "created_at": comment["createdAt"]}
        )
        save(state_dir, key, state)
    return summary(state)


def cmd_rearm(args: argparse.Namespace) -> str:
    key = story_key(args.story)
    additional = positive(args.additional_rounds, "--additional-rounds")
    state_dir = checked_state_dir(args.state_dir)
    state = load(state_dir, key)
    name, _ = read_story(key)
    if name != state["in_progress"]:
        raise Refusal(3, f"state={name}")
    state["cap"] = len(state["rounds"]) + additional
    save(state_dir, key, state)
    return f"state={name}"


def build_parser() -> Parser:
    parser = Parser(
        prog="qa-round-cap.py",
        description="Count story-to-done QA rounds against qa-round-cap. Reads the tracker only through `linear`.",
        epilog=EXIT_CODES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="subcommand")

    validate = sub.add_parser("validate", help="print the integer of qa-round-cap=<n>; exit 2 unless it is 1 or more")
    validate.add_argument("token", metavar="qa-round-cap=<n>")
    validate.set_defaults(run=cmd_validate)

    arm = sub.add_parser("arm", help="start a new count for the story; prints round=0 cap=<n> reached=no")
    arm.add_argument("--story", required=True)
    arm.add_argument("--cap", required=True)
    arm.add_argument("--in-progress", required=True, help="the profile's in_progress state name")
    arm.add_argument("--state-dir", required=True)
    arm.set_defaults(run=cmd_arm)

    record = sub.add_parser("record", help="count the newest new QA evidence comment; prints round=<n> cap=<c> reached=yes|no")
    record.add_argument("--story", required=True)
    record.add_argument("--state-dir", required=True)
    record.set_defaults(run=cmd_record)

    rearm = sub.add_parser("rearm", help="set the cap to the counted rounds plus N; prints state=<name>")
    rearm.add_argument("--story", required=True)
    rearm.add_argument("--additional-rounds", required=True)
    rearm.add_argument("--state-dir", required=True)
    rearm.set_defaults(run=cmd_rearm)
    return parser


def main(argv: list[str]) -> int:
    try:
        args = build_parser().parse_args(argv)
        line = args.run(args)
    except Refusal as refusal:
        sys.stderr.write(refusal.line + "\n")
        return refusal.code
    except Exception as error:  # one line, never a traceback
        sys.stderr.write(f"qa-round-cap.py: unexpected {type(error).__name__}\n")
        return 1
    sys.stdout.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
