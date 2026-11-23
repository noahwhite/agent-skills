#!/usr/bin/env python3
"""Render a story-to-done role brief into the role's own scratch subdirectory.

  render-brief.py --role engineer --story KEY --path PATH --scratch DIR
  render-brief.py --role qa --story KEY --path PATH --scratch DIR --round N [--environment NAME]
  render-brief.py --role qa --story KEY --path no-deployment --scratch DIR --round N --commit SHA
  render-brief.py --role qa --story KEY --path spike --scratch DIR --round N --link URL [--link URL ...]

PATH is spike, no-deployment or deployed. `--environment` is optional and only on a deployed QA render.

The brief is assembled from the templates in the skill's assets directory: the role's base template, the
shared rules fragment, the role's permissions fragment, the role's state-move fragment for the selected
path, then the role's per-path fragment. The tokens {{story}}, {{path}}, {{scratch}}, {{round}} and
{{target}} are replaced by exact string matching in one pass, so a value is never expanded again, and
each backticked mention of a file in the skill's references directory becomes its absolute path, except
inside a cited quotation span (a quoted sentence followed by " at " and a backticked file and line
number), so a quoted source sentence stays verbatim while every navigational mention, before or after
it, still resolves and is still checked. Nothing else in the template is syntax.

The output file is <scratch>/senior-engineer/senior-engineer-brief.md or
<scratch>/qa-agent-round-<n>/qa-agent-round-<n>-brief.md. The role subdirectory must already exist. The file
is written to a temporary file in that directory and renamed over the output, and its absolute path is the
only line printed on stdout.

The script reads no stdin, environment, profile, tracker or forge, and starts no process. Every failure exits
non-zero with one stderr line, nothing on stdout, and no file created or changed.

exit codes:
  0  the brief was written and its path printed
  1  a filesystem, template or write failure, or an unexpected error
  2  an invalid, missing, repeated or unknown argument, or an input the role or path does not take
"""

import argparse
import os
import re
import stat
import sys
import tempfile
from pathlib import Path

PROG = "render-brief.py"
ROLES = ("engineer", "qa")
PATHS = ("spike", "no-deployment", "deployed")
TOKENS = ("story", "path", "scratch", "round", "target")
STORY = re.compile(r"[A-Z][A-Z0-9]*-[0-9]+")
ROUND = re.compile(r"[1-9][0-9]*")
ENVIRONMENT = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")
COMMIT = re.compile(r"[0-9a-f]{40}")
# AC1: a link is a whitespace-free https:// URL. has_host() also requires the URL to name a host.
LINK = re.compile(r"https://\S+")
SCRATCH = re.compile(r"/[A-Za-z0-9._/-]+")
REFERENCE_NAME = re.compile(r"[a-z0-9-]+\.md")
REFERENCE_OPEN = "`references/"
# A cited quotation span: a quoted sentence followed by the file and line it comes from. Only the span
# is exempt from reference resolution; a navigational mention elsewhere on the same line still resolves.
QUOTATION = re.compile(r'"[^"]*" at `[^`]+\.md:\d+`')


class Refusal(Exception):
    def __init__(self, code: int, line: str) -> None:
        super().__init__(line)
        self.code = code
        self.line = line


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # ascii() escapes a newline or any other control character an argument value may carry, so the
        # refusal stays one line.
        raise Refusal(2, ascii(message)[1:-1])


class Once(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None) -> None:
        if getattr(namespace, self.dest) is not None:
            raise Refusal(2, f"{option_string} given more than once")
        setattr(namespace, self.dest, values)


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(prog=PROG, add_help=False, allow_abbrev=False)
    for option in ("--role", "--story", "--path", "--scratch", "--round", "--environment", "--commit"):
        parser.add_argument(option, action=Once)
    parser.add_argument("--link", action="append")
    return parser


def refuse(line: str, code: int = 2) -> None:
    raise Refusal(code, line)


def check(value, pattern: re.Pattern, option: str) -> None:
    if not pattern.fullmatch(value):
        refuse(f"invalid {option}: the value does not match its pattern")


def has_host(link: str) -> bool:
    """Whether the authority of an https:// URL names a host, after any userinfo and port."""
    authority = re.split(r"[/?#]", link.removeprefix("https://"), maxsplit=1)[0]
    host = authority.rpartition("@")[2]
    if host.startswith("["):
        return host.find("]") > 1
    return bool(host.partition(":")[0])


def not_taken(ns: argparse.Namespace, options: tuple[str, ...], what: str) -> None:
    for option in options:
        if getattr(ns, option.removeprefix("--")) is not None:
            refuse(f"{option} is not taken by {what}")


def checked_scratch(scratch: str, sub: str) -> str:
    """The role subdirectory, after the scratch directory and the subdirectory pass every check."""
    check(scratch, SCRATCH, "--scratch")
    if any(part in ("", ".", "..") for part in scratch.split("/")[1:]):
        refuse("invalid --scratch: an empty, '.' or '..' component")
    if os.path.realpath(scratch) != scratch:
        refuse("invalid --scratch: the path is not its own realpath")
    role_dir = scratch + "/" + sub
    if os.path.realpath(role_dir) != role_dir:
        refuse(f"invalid --scratch: the {sub} subdirectory is not its own realpath", 1)
    if not os.path.isdir(role_dir):
        refuse(f"missing role subdirectory {sub} in --scratch", 1)
    return role_dir


def plan(ns: argparse.Namespace) -> tuple[str, str, list[str], dict]:
    """The role subdirectory, output name, template names and token values for valid arguments."""
    for option in ("--role", "--story", "--path", "--scratch"):
        if getattr(ns, option.removeprefix("--")) is None:
            refuse(f"missing {option}")
    if ns.role not in ROLES:
        refuse("invalid --role: expected engineer or qa")
    if ns.path not in PATHS:
        refuse("invalid --path: expected spike, no-deployment or deployed")
    check(ns.story, STORY, "--story")
    values = {"story": ns.story, "path": ns.path, "scratch": ns.scratch, "round": None, "target": None}

    if ns.role == "engineer":
        not_taken(ns, ("--round", "--environment", "--commit", "--link"), "an engineer render")
        sub = "senior-engineer"
        # Only the engineer's deployment-review rule differs by path; QA's closing rule is shared.
        state_move = "deployed" if ns.path == "deployed" else "handoff"
        templates = [
            "brief-engineer.md",
            "brief-rules.md",
            "brief-engineer-permissions.md",
            f"brief-engineer-state-move-{state_move}.md",
            f"brief-engineer-{ns.path}.md",
        ]
    else:
        if ns.round is None:
            refuse("missing --round")
        check(ns.round, ROUND, "--round")
        values["round"] = ns.round
        sub = f"qa-agent-round-{ns.round}"
        fragment = f"brief-qa-{ns.path}.md"
        if ns.path == "deployed":
            not_taken(ns, ("--commit", "--link"), "a deployed QA render")
            if ns.environment is None:
                fragment = "brief-qa-deployed-default.md"
            else:
                check(ns.environment, ENVIRONMENT, "--environment")
                values["target"] = ns.environment
        elif ns.path == "no-deployment":
            not_taken(ns, ("--environment", "--link"), "a no-deployment QA render")
            if ns.commit is None:
                refuse("missing --commit")
            check(ns.commit, COMMIT, "--commit")
            values["target"] = ns.commit
        else:
            not_taken(ns, ("--environment", "--commit"), "a spike QA render")
            if not ns.link:
                refuse("missing --link")
            for link in ns.link:
                check(link, LINK, "--link")
                if not has_host(link):
                    refuse("invalid --link: the URL names no host")
            values["target"] = "\n".join(ns.link)
        templates = [
            "brief-qa.md",
            "brief-rules.md",
            "brief-qa-permissions.md",
            "brief-qa-state-move.md",
            fragment,
        ]

    role_dir = checked_scratch(ns.scratch, sub)
    return role_dir, f"{sub}-brief.md", templates, values


def load(skill_dir: Path, names: list[str]) -> str:
    parts = []
    for name in names:
        try:
            parts.append((skill_dir / "assets" / name).read_bytes().decode("utf-8"))
        except FileNotFoundError:
            refuse(f"missing template {name}", 1)
        except (OSError, UnicodeDecodeError):
            refuse(f"unreadable template {name}", 1)
    return "".join(parts)


def substitute(text: str, values: dict, skill_dir: str) -> str:
    """One left-to-right pass of exact matches: a replaced value is never scanned again.

    A backticked `references/` mention is rewritten everywhere except inside a cited quotation span,
    so an unrelated literal quote never suppresses a navigational reference and a quoted sentence is
    never rewritten. The span, not a quote counter or the whole line, decides.
    """
    out = []
    for line in text.splitlines(keepends=True):
        quoted = [match.span() for match in QUOTATION.finditer(line)]
        i = 0
        while i < len(line):
            if line.startswith("{{", i):
                token = next((t for t in TOKENS if line.startswith("{{" + t + "}}", i)), None)
                if token is None:
                    refuse("a template holds an unknown token", 1)
                if values[token] is None:
                    refuse(f"a template uses the {token} token, which this render does not take", 1)
                out.append(values[token])
                i += len(token) + 4
                continue
            if not any(start <= i < end for start, end in quoted) and line.startswith(REFERENCE_OPEN, i):
                end = line.find("`", i + 1)
                name = line[i + len(REFERENCE_OPEN):end] if end != -1 else ""
                if REFERENCE_NAME.fullmatch(name):
                    absolute = skill_dir + "/references/" + name
                    if not os.path.isfile(absolute):
                        refuse(f"a template names a missing reference {name}", 1)
                    out.append("`" + absolute + "`")
                    i = end + 1
                    continue
            out.append(line[i])
            i += 1
    return "".join(out)


def write_atomic(role_dir: str, name: str, data: bytes) -> str:
    target = role_dir + "/" + name
    try:
        mode = os.lstat(target).st_mode
    except FileNotFoundError:
        mode = None
    except OSError:
        refuse("could not write the brief", 1)
    if mode is not None and not stat.S_ISREG(mode):
        refuse("could not write the brief: the output path is not a regular file", 1)
    if mode is None:
        # mkstemp creates the file 0600; a new brief gets the mode a plain create would give it.
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    try:
        fd, temp = tempfile.mkstemp(prefix="." + name + ".", suffix=".tmp", dir=role_dir)
    except OSError:
        refuse("could not write the brief", 1)
    try:
        os.fchmod(fd, stat.S_IMODE(mode))
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    except BaseException as exc:
        try:
            os.unlink(temp)
        except OSError:
            pass
        if isinstance(exc, OSError):
            refuse("could not write the brief", 1)
        raise
    return target


def main(argv: list[str] | None = None) -> int:
    try:
        ns = build_parser().parse_args(argv)
        role_dir, name, templates, values = plan(ns)
        skill_dir = Path(__file__).resolve().parent.parent
        text = substitute(load(skill_dir, templates), values, str(skill_dir))
        target = write_atomic(role_dir, name, text.encode("utf-8"))
    except Refusal as refusal:
        sys.stderr.write(f"{PROG}: {refusal.line}\n")
        return refusal.code
    except Exception as exc:
        sys.stderr.write(f"{PROG}: unexpected error: {type(exc).__name__}\n")
        return 1
    sys.stdout.write(target + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
