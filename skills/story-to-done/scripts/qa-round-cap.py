#!/usr/bin/env python3
"""Count story-to-done QA rounds against the `qa-round-cap` argument.

The count lives in <state-dir>/qa-round-cap/<KEY>.json. `arm`, `record` and `rearm` read the story
through the ambient `linear` CLI (`linear api` with a read-only query, every comment page) and never
write to the tracker. A QA round is a story comment whose first line is exactly `## QA evidence`.
"""

import argparse
import fcntl
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

POSITIVE = re.compile(r"[1-9][0-9]*")
STORY = re.compile(r"[A-Z][A-Z0-9]*-[1-9][0-9]*")
COUNT_ID = re.compile(r"[0-9a-f]{16}")
MARKER = "## QA evidence"
DEFAULT_IN_PROGRESS = "In Progress"
TRACKER_TIMEOUT = 120
MAX_PAGES = 1000
QUERY = (
    "query QaRoundCap($id: String!, $after: String) { issue(id: $id) { identifier state { name } "
    "comments(first: 100, after: $after) { nodes { id body createdAt } pageInfo { hasNextPage endCursor } } } }"
)

EXIT_CODES = """exit codes:
  0  success
  1  any other failure: no count armed, unreadable state, failed tracker read, unexpected tracker payload or malformed
     QA evidence comment, unexpected error
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


def checked_state_dir(value: str) -> Path:
    path = Path(value)
    if not path.is_dir():
        raise Refusal(2, "invalid --state-dir: not an existing directory")
    return path.resolve()


def state_path(state_dir: Path, key: str) -> Path:
    return state_dir / "qa-round-cap" / f"{key}.json"


@contextmanager
def locked(state_dir: Path) -> Iterator[None]:
    """Hold an exclusive lock on <state-dir>/qa-round-cap for one load-modify-save."""
    directory = state_dir / "qa-round-cap"
    directory.mkdir(exist_ok=True)
    fd = os.open(directory, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def valid_round(entry: object, number: int) -> bool:
    return (
        isinstance(entry, dict)
        and entry.get("round") == number
        and isinstance(entry.get("comment_id"), str)
        and isinstance(entry.get("created_at"), str)
    )


def load(state_dir: Path, key: str) -> dict:
    path = state_path(state_dir, key)
    try:
        state = json.loads(path.read_text())
    except FileNotFoundError:
        raise Refusal(1, f"no QA round count armed for {key}: run arm first") from None
    except (OSError, ValueError):
        raise Refusal(1, f"unreadable QA round state for {key}") from None
    if not (
        isinstance(state, dict)
        and state.get("story") == key
        and isinstance(state.get("count_id"), str)
        and COUNT_ID.fullmatch(state["count_id"])
        and type(state.get("cap")) is int
        and state["cap"] >= 1
        and isinstance(state.get("in_progress"), str)
        and isinstance(state.get("armed_at"), str)
        and isinstance(state.get("baseline"), list)
        and all(isinstance(item, str) for item in state["baseline"])
        and isinstance(state.get("rounds"), list)
        and all(valid_round(entry, number) for number, entry in enumerate(state["rounds"], 1))
    ):
        raise Refusal(1, f"unreadable QA round state for {key}")
    return state


def save(state_dir: Path, key: str, state: dict) -> None:
    path = state_path(state_dir, key)
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


def publish(line: str, state_dir: Path, key: str, state: Optional[dict]) -> None:
    """Print the stdout line first, so a failed write exits non-zero with the state file unchanged."""
    sys.stdout.write(line + "\n")
    sys.stdout.flush()
    if state is not None:
        save(state_dir, key, state)


def timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("not a timestamp")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp has no zone")
    return parsed


def read_page(key: str, after: Optional[str]) -> dict:
    variables = json.dumps({"id": key, "after": after})
    try:
        result = subprocess.run(
            ["linear", "api", QUERY, "--variables-json", variables],
            capture_output=True,
            text=True,
            timeout=TRACKER_TIMEOUT,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Refusal(1, f"tracker read failed for {key}") from None
    if result.returncode != 0:
        raise Refusal(1, f"tracker read failed for {key} (linear exit {result.returncode})")
    unexpected = Refusal(1, f"tracker read for {key} returned an unexpected payload")
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise unexpected from None
    if not isinstance(payload, dict) or "errors" in payload or not isinstance(payload.get("data"), dict):
        raise unexpected
    issue = payload["data"].get("issue")
    if not isinstance(issue, dict):
        raise unexpected
    if issue.get("identifier") != key:
        raise Refusal(1, f"tracker read for {key} returned a different issue")
    state = issue.get("state")
    comments = issue.get("comments")
    if not (
        isinstance(state, dict)
        and isinstance(state.get("name"), str)
        and state["name"]
        and isinstance(comments, dict)
        and isinstance(comments.get("nodes"), list)
        and isinstance(comments.get("pageInfo"), dict)
        and isinstance(comments["pageInfo"].get("hasNextPage"), bool)
    ):
        raise unexpected
    if comments["pageInfo"]["hasNextPage"] and not (
        isinstance(comments["pageInfo"].get("endCursor"), str) and comments["pageInfo"]["endCursor"]
    ):
        raise unexpected
    return issue


def read_story(key: str) -> tuple[str, list]:
    """Return the story's state name and every comment, read through the ambient `linear` auth."""
    nodes: list = []
    after: Optional[str] = None
    seen: set = set()
    for _ in range(MAX_PAGES):
        issue = read_page(key, after)
        if after is None:
            name = issue["state"]["name"]
        nodes.extend(issue["comments"]["nodes"])
        page = issue["comments"]["pageInfo"]
        if not page["hasNextPage"]:
            return name, nodes
        after = page["endCursor"]
        if after in seen:
            break
        seen.add(after)
    raise Refusal(1, f"tracker read for {key} returned an unexpected payload")


def is_qa_evidence(comment: object) -> bool:
    if not isinstance(comment, dict) or not isinstance(comment.get("body"), str):
        return False
    line = comment["body"].split("\n", 1)[0]
    if line.endswith("\r"):
        line = line[:-1]
    return line == MARKER


def comment_ids(comments: list) -> list[str]:
    return sorted({c["id"] for c in comments if isinstance(c, dict) and isinstance(c.get("id"), str)})


def qa_evidence(key: str, comments: list) -> list[tuple[datetime, str, str]]:
    """Every QA evidence comment as (created, id, createdAt), oldest first; a malformed one exits 1."""
    found = []
    for comment in comments:
        if not is_qa_evidence(comment):
            continue
        try:
            if not isinstance(comment.get("id"), str):
                raise ValueError("no id")
            found.append((timestamp(comment.get("createdAt")), comment["id"], comment["createdAt"]))
        except ValueError:
            raise Refusal(1, f"tracker read for {key} returned a malformed QA evidence comment") from None
    return sorted(found)


def summary(state: dict) -> str:
    rounds = len(state["rounds"])
    return f"round={rounds} cap={state['cap']} reached={'yes' if rounds >= state['cap'] else 'no'}"


def cmd_validate(args: argparse.Namespace) -> None:
    name, sep, value = args.token.partition("=")
    if name != "qa-round-cap" or not sep:
        raise Refusal(2, "invalid argument: expected qa-round-cap=<n>")
    publish(str(positive(value, "qa-round-cap")), Path("."), "", None)


def cmd_arm(args: argparse.Namespace) -> None:
    key = story_key(args.story)
    cap = positive(args.cap, "--cap")
    in_progress = args.in_progress.strip()
    if not in_progress:
        raise Refusal(2, "invalid --in-progress: expected the in_progress state name")
    state_dir = checked_state_dir(args.state_dir)
    with locked(state_dir):
        _, comments = read_story(key)
        qa_evidence(key, comments)
        state = {
            "story": key,
            "count_id": secrets.token_hex(8),
            "cap": cap,
            "in_progress": in_progress,
            "armed_at": datetime.now(timezone.utc).isoformat(),
            "baseline": comment_ids(comments),
            "rounds": [],
        }
        publish(summary(state), state_dir, key, state)


def cmd_record(args: argparse.Namespace) -> None:
    key = story_key(args.story)
    state_dir = checked_state_dir(args.state_dir)
    with locked(state_dir):
        state = load(state_dir, key)
        name, comments = read_story(key)
        if name != state["in_progress"]:
            raise Refusal(3, f"state={name}")
        # The baseline holds every comment on the story at arm or at the last counted round, so a comment
        # outside it was created after that point; the newest such QA evidence comment is the one round.
        seen = set(state["baseline"])
        new = [(cid, created_at) for _, cid, created_at in qa_evidence(key, comments) if cid not in seen]
        if not new:
            publish(summary(state), state_dir, key, None)
            return
        comment_id, created_at = new[-1]
        state["rounds"].append({"round": len(state["rounds"]) + 1, "comment_id": comment_id, "created_at": created_at})
        state["baseline"] = sorted(seen | set(comment_ids(comments)))
        publish(summary(state), state_dir, key, state)


def cmd_rearm(args: argparse.Namespace) -> None:
    key = story_key(args.story)
    additional = positive(args.additional_rounds, "--additional-rounds")
    state_dir = checked_state_dir(args.state_dir)
    with locked(state_dir):
        state = load(state_dir, key)
        name, _ = read_story(key)
        if name != state["in_progress"]:
            raise Refusal(3, f"state={name}")
        state["cap"] = len(state["rounds"]) + additional
        publish(f"state={name}", state_dir, key, state)


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

    arm = sub.add_parser(
        "arm", help="start a new count, replacing any count in the state dir; prints round=0 cap=<n> reached=no"
    )
    arm.add_argument("--story", required=True)
    arm.add_argument("--cap", required=True)
    arm.add_argument(
        "--in-progress",
        default=DEFAULT_IN_PROGRESS,
        help=f"the profile's in_progress state name (default: {DEFAULT_IN_PROGRESS})",
    )
    arm.add_argument("--state-dir", required=True)
    arm.set_defaults(run=cmd_arm)

    record = sub.add_parser("record", help="count the newest QA evidence comment since the last round; prints round=<n> cap=<c> reached=yes|no")
    record.add_argument("--story", required=True)
    record.add_argument("--state-dir", required=True)
    record.set_defaults(run=cmd_record)

    rearm = sub.add_parser("rearm", help="set the cap to the counted rounds plus N; prints state=<name>")
    rearm.add_argument("--story", required=True)
    rearm.add_argument("--additional-rounds", required=True)
    rearm.add_argument("--state-dir", required=True)
    rearm.set_defaults(run=cmd_rearm)
    return parser


def one_line(error: Exception) -> str:
    detail = " ".join(str(error).split())[:200]
    return f"qa-round-cap.py: unexpected {type(error).__name__}" + (f": {detail}" if detail else "")


def main(argv: list[str]) -> int:
    try:
        args = build_parser().parse_args(argv)
        args.run(args)
    except Refusal as refusal:
        sys.stderr.write(refusal.line + "\n")
        return refusal.code
    except Exception as error:  # one line, never a traceback
        if isinstance(error, BrokenPipeError):
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
        sys.stderr.write(one_line(error) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
