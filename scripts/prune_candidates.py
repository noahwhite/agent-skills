#!/usr/bin/env python3
"""List tests, reference files and rules that are candidates for retirement.

Usage: python scripts/prune_candidates.py --since YYYY-MM-DD

Run from anywhere inside the repository. It resolves HEAD once, evaluates that commit, reads
only git objects, and writes nothing. Each candidate carries its evidence and a retire or keep
proposal; the owner decides at the retro (docs/pruning-routine.md). The three categories:

- tests untouched since D: a tests/test_*.py file whose latest committer time over every commit
  that touched it is before D.
- reference files uncited at this commit: a shared/*.md source other than README.md that no
  skills/*/SKILL.md cites as references/<name>.
- rules uncited at this commit, unchanged since D: a list item in a shared/*.md source that
  carries the stop sign, whose text (continuation lines and nested items included, whitespace
  collapsed, case ignored) shares no 40-character run with any file under tests/ or any
  skills/*/SKILL.md, and whose lines were all last changed before D per git blame.

D is 00:00 UTC on the --since date. A shallow or partial clone is refused, since its history or
objects are incomplete and reading them would fetch and write into the repository.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone

STOP = "⛔"
WINDOW = 40
ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s")
MARKERS = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s", re.MULTILINE)
FENCE = re.compile(r"^\s*(?:```|~~~)")
BLOCK_START = re.compile(r"^\s*(?:#|>|\||```|~~~|---|\*\*\*|___)")

# Every call is pinned to the repository root, takes paths literally, prints paths unquoted,
# and takes no optional locks, so the output does not depend on the caller's directory or on
# local configuration.
GIT = ["git", "--literal-pathspecs", "--no-optional-locks", "-c", "core.quotePath=false"]
root = "."


def probe(*args: str) -> subprocess.CompletedProcess:
    # Paths travel as UTF-8 bytes both ways, so a non-UTF-8 locale cannot break them.
    argv = [arg.encode("utf-8") for arg in (*GIT, "-C", root, *args)]
    return subprocess.run(argv, capture_output=True, encoding="utf-8", errors="replace")


def git(*args: str) -> str:
    result = probe(*args)
    if result.returncode != 0:
        raise SystemExit(f"prune_candidates: git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def day(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%d")


def collapse(text: str) -> str:
    return " ".join(text.split())


def parse_since(value: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        parsed = None
    if parsed is None or parsed.strftime("%Y-%m-%d") != value:
        raise argparse.ArgumentTypeError(f"expected a date as YYYY-MM-DD, got {value!r}")
    return parsed.replace(tzinfo=timezone.utc)


def show(head: str, path: str) -> str:
    return git("cat-file", "blob", f"{head}:{path}")


def test_candidates(head: str, files: list[str], cutoff: int) -> list[str]:
    out = []
    for path in files:
        if not re.fullmatch(r"tests/test_[^/]*\.py", path):
            continue
        last = max(int(t) for t in git("log", "--format=%ct", head, "--", path).split())
        if last < cutoff:
            out.append(
                f"- {path} | last change {day(last)} | proposal: keep "
                "(it still runs on every CI run; retire only on a finding that it adds no value)"
            )
    return out


def sources(files: list[str]) -> list[str]:
    return [f for f in files if re.fullmatch(r"shared/[^/]*\.md", f) and f != "shared/README.md"]


def skill_texts(head: str, files: list[str]) -> list[str]:
    return [show(head, f) for f in files if re.fullmatch(r"skills/[^/]+/SKILL\.md", f)]


def cites(cite: str, text: str) -> bool:
    """True when text names cite as a whole path, not as part of a longer or nested path."""
    return re.search(rf"(?<![\w./-]){re.escape(cite)}(?![\w-]|\.\w)", text) is not None


def reference_candidates(files: list[str], skills: list[str]) -> list[str]:
    out = []
    for path in sources(files):
        cite = f"references/{path.removeprefix('shared/')}"
        if not any(cites(cite, text) for text in skills):
            out.append(f"- {path} | no skills/*/SKILL.md cites {cite} | proposal: retire")
    return out


def indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def fenced_lines(lines: list[str]) -> list[bool]:
    """Mark each line inside a fenced code block, fences included."""
    marks = []
    inside = False
    for line in lines:
        if FENCE.match(line):
            marks.append(True)
            inside = not inside
        else:
            marks.append(inside)
    return marks


def item_end(lines: list[str], fenced: list[bool], start: int, marker: int) -> int:
    """Return the last line of the item that starts at start, children included."""
    end = start
    j = start + 1
    while j < len(lines):
        line = lines[j]
        if not line.strip():
            k = j + 1
            while k < len(lines) and not lines[k].strip():
                k += 1
            if k < len(lines) and indent(lines[k]) > marker:
                j = k
                continue
            break
        if indent(line) > marker:
            end = j
        elif (
            not fenced[j]
            and not ITEM.match(line)
            and not BLOCK_START.match(line)
            and lines[j - 1].strip()
            and not fenced[j - 1]
        ):
            end = j  # a lazy continuation line
        else:
            break
        j += 1
    return end


def rule_items(text: str) -> list[tuple[int, int, str]]:
    """Return (first line, last line, text) for each list item whose own lines carry the stop sign.

    An item runs to its last continuation line, nested items included; a nested item that
    carries the stop sign is also its own item. List markers inside fenced code blocks are not
    items.
    """
    lines = text.splitlines()
    fenced = fenced_lines(lines)
    items = []
    for i, line in enumerate(lines):
        match = ITEM.match(line)
        if fenced[i] or not match:
            continue
        end = item_end(lines, fenced, i, len(match.group(1)))
        own = i
        while own < end and not (ITEM.match(lines[own + 1]) and not fenced[own + 1]):
            own += 1
        if STOP in "\n".join(lines[i : own + 1]):
            items.append((i + 1, end + 1, "\n".join(lines[i : end + 1])))
    return items


def rule_text(item: str) -> str:
    return collapse(MARKERS.sub("", item).replace(STOP, ""))


def cited_rules(texts: list[str], haystack: str) -> set[int]:
    """Return the indexes of the texts that share a WINDOW-character run with the haystack.

    A text no longer than WINDOW counts as cited only when the haystack holds all of it with no
    word character on either side. An empty text is never cited.
    """
    found = set()
    index: dict[str, list[int]] = {}
    for n, text in enumerate(texts):
        if not text:
            continue
        if len(text) <= WINDOW:
            if re.search(rf"(?<!\w){re.escape(text)}(?!\w)", haystack):
                found.add(n)
            continue
        for k in range(len(text) - WINDOW + 1):
            index.setdefault(text[k : k + WINDOW], []).append(n)
    for k in range(len(haystack) - WINDOW + 1):
        hit = index.get(haystack[k : k + WINDOW])
        if hit:
            found.update(hit)
    return found


def last_change(head: str, path: str, first: int, last: int) -> int:
    # An empty --ignore-revs-file clears blame.ignoreRevsFile, so every line keeps its real commit.
    blame = git(
        "blame", "--line-porcelain", "--ignore-revs-file", "", "-L", f"{first},{last}", head, "--", path
    )
    return max(int(line.split()[1]) for line in blame.splitlines() if line.startswith("committer-time "))


def rule_candidates(head: str, files: list[str], skills: list[str], cutoff: int) -> list[str]:
    tests = [show(head, f) for f in files if f.startswith("tests/")]
    haystack = "\n".join(collapse(t).lower() for t in tests + skills)
    rules = [
        (path, first, last, rule_text(body))
        for path in sources(files)
        for first, last, body in rule_items(show(head, path))
    ]
    pinned = cited_rules([rule[3].lower() for rule in rules], haystack)
    out = []
    for n, (path, first, last, text) in enumerate(rules):
        if n in pinned:
            continue
        changed = last_change(head, path, first, last)
        if changed < cutoff:
            out.append(
                f"- {path}:{first} | last change {day(changed)} | \"{text}\" | proposal: retire "
                "(no test or SKILL.md quotes it)"
            )
    return out


def refusal(reason: str) -> int:
    print(f"prune_candidates: refusing to run in a {reason}", file=sys.stderr)
    return 2


def partial_clone() -> bool:
    if probe("config", "--get", "extensions.partialClone").stdout.strip():
        return True
    promisors = probe("config", "--get-regexp", r"^remote\..*\.promisor$").stdout.split("\n")
    return any(line.split(" ", 1)[-1].strip().lower() == "true" for line in promisors if line)


def main(argv: list[str] | None = None) -> int:
    global root
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", required=True, type=parse_since, metavar="YYYY-MM-DD")
    args = parser.parse_args(argv)

    root = git("rev-parse", "--show-toplevel").strip()
    if git("rev-parse", "--is-shallow-repository").strip() == "true":
        return refusal(
            "shallow clone, whose history is incomplete; run `git fetch --unshallow` or use a full clone"
        )
    if partial_clone():
        return refusal(
            "partial clone, whose missing objects would be fetched into it; use a full clone"
        )

    head = git("rev-parse", "--verify", "HEAD^{commit}").strip()
    since = args.since.strftime("%Y-%m-%d")
    cutoff = int(args.since.timestamp())
    files = [f for f in git("ls-tree", "-r", "-z", "--name-only", head).split("\0") if f]
    skills = skill_texts(head, files)

    print("Pruning candidates (proposals only; the owner decides, nothing is removed)")
    print(f"commit: {head}")
    print(f"since: {since}")
    for heading, rows in (
        (f"tests untouched since {since}", test_candidates(head, files, cutoff)),
        ("reference files uncited at this commit", reference_candidates(files, skills)),
        (
            f"rules uncited at this commit, unchanged since {since}",
            rule_candidates(head, files, skills, cutoff),
        ),
    ):
        print()
        print(f"{heading}: {len(rows)}")
        for row in rows:
            print(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
