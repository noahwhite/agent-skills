#!/usr/bin/env python3
"""List tests, reference files and rules that are candidates for retirement.

Usage: python scripts/prune_candidates.py --since YYYY-MM-DD

Run from inside the repository. It evaluates the checked-out HEAD, reads only git objects, and
writes nothing. Each candidate carries its evidence and a retire or keep proposal; the owner
decides at the retro (docs/pruning-routine.md). The three categories:

- tests untouched since D: a tests/test_*.py file whose last commit is before D.
- reference files uncited at this commit: a shared/*.md source other than README.md that no
  skills/*/SKILL.md cites as references/<name>.
- rules uncited at this commit, unchanged since D: a list item in a shared/*.md source that
  carries the stop sign, whose text (continuation lines included, whitespace collapsed, case
  ignored) shares no 40-character run with any file under tests/ or any skills/*/SKILL.md, and
  whose lines were all last changed before D per git blame.

D is 00:00 UTC on the --since date. A shallow clone is refused, since its history is incomplete.
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


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"prune_candidates: git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def show(path: str) -> str:
    raw = subprocess.run(["git", "show", f"HEAD:{path}"], capture_output=True, check=True).stdout
    return raw.decode("utf-8", errors="replace")


def day(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%d")


def collapse(text: str) -> str:
    return " ".join(text.split())


def parse_since(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a date as YYYY-MM-DD, got {value!r}")


def test_candidates(files: list[str], cutoff: int) -> list[str]:
    out = []
    for path in files:
        if not re.fullmatch(r"tests/test_[^/]*\.py", path):
            continue
        last = int(git("log", "-1", "--format=%ct", "HEAD", "--", path).strip())
        if last < cutoff:
            out.append(
                f"- {path} | last change {day(last)} | proposal: keep "
                "(it still runs on every CI run; retire only on a finding that it adds no value)"
            )
    return out


def sources(files: list[str]) -> list[str]:
    return [f for f in files if re.fullmatch(r"shared/[^/]*\.md", f) and f != "shared/README.md"]


def skill_texts(files: list[str]) -> list[str]:
    return [show(f) for f in files if re.fullmatch(r"skills/[^/]+/SKILL\.md", f)]


def reference_candidates(files: list[str], skills: list[str]) -> list[str]:
    out = []
    for path in sources(files):
        cite = f"references/{path.removeprefix('shared/')}"
        if not any(cite in text for text in skills):
            out.append(f"- {path} | no skills/*/SKILL.md cites {cite} | proposal: retire")
    return out


def rule_items(text: str) -> list[tuple[int, int, str]]:
    """Return (first line, last line, text) for each list item that carries the stop sign."""
    lines = text.splitlines()
    items = []
    i = 0
    while i < len(lines):
        match = ITEM.match(lines[i])
        if not match:
            i += 1
            continue
        indent = len(match.group(1))
        end = i
        while end + 1 < len(lines):
            nxt = lines[end + 1]
            if not nxt.strip() or ITEM.match(nxt) or len(nxt) - len(nxt.lstrip()) <= indent:
                break
            end += 1
        body = "\n".join(lines[i : end + 1])
        if STOP in body:
            items.append((i + 1, end + 1, body))
        i = end + 1
    return items


def rule_text(item: str) -> str:
    return collapse(ITEM.sub("", item, count=1).replace(STOP, ""))


def cited_rules(texts: list[str], haystack: str) -> set[int]:
    """Return the indexes of the texts that share a WINDOW-character run with the haystack."""
    found = set()
    index: dict[str, list[int]] = {}
    for n, text in enumerate(texts):
        if len(text) <= WINDOW:
            if text in haystack:
                found.add(n)
            continue
        for k in range(len(text) - WINDOW + 1):
            index.setdefault(text[k : k + WINDOW], []).append(n)
    for k in range(len(haystack) - WINDOW + 1):
        hit = index.get(haystack[k : k + WINDOW])
        if hit:
            found.update(hit)
    return found


def last_change(path: str, first: int, last: int) -> int:
    blame = git("blame", "--line-porcelain", "-L", f"{first},{last}", "HEAD", "--", path)
    return max(int(line.split()[1]) for line in blame.splitlines() if line.startswith("committer-time "))


def rule_candidates(files: list[str], skills: list[str], cutoff: int) -> list[str]:
    tests = [show(f) for f in files if f.startswith("tests/")]
    haystack = "\n".join(collapse(t).lower() for t in tests + skills)
    rules = [
        (path, first, last, rule_text(body))
        for path in sources(files)
        for first, last, body in rule_items(show(path))
    ]
    pinned = cited_rules([rule[3].lower() for rule in rules], haystack)
    out = []
    for n, (path, first, last, text) in enumerate(rules):
        if n in pinned:
            continue
        changed = last_change(path, first, last)
        if changed < cutoff:
            out.append(
                f"- {path}:{first} | last change {day(changed)} | \"{text[:80]}...\" | proposal: retire "
                "(no test or SKILL.md quotes it)"
            )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", required=True, type=parse_since, metavar="YYYY-MM-DD")
    args = parser.parse_args(argv)

    if git("rev-parse", "--is-shallow-repository").strip() == "true":
        print(
            "prune_candidates: refusing to run in a shallow clone, whose history is incomplete; "
            "run `git fetch --unshallow` or use a full clone",
            file=sys.stderr,
        )
        return 2

    since = args.since.strftime("%Y-%m-%d")
    cutoff = int(args.since.timestamp())
    files = git("ls-tree", "-r", "--name-only", "HEAD").splitlines()
    skills = skill_texts(files)

    print("Pruning candidates (proposals only; the owner decides, nothing is removed)")
    print(f"commit: {git('rev-parse', 'HEAD').strip()}")
    print(f"since: {since}")
    for heading, rows in (
        (f"tests untouched since {since}", test_candidates(files, cutoff)),
        ("reference files uncited at this commit", reference_candidates(files, skills)),
        (f"rules uncited at this commit, unchanged since {since}", rule_candidates(files, skills, cutoff)),
    ):
        print()
        print(f"{heading}: {len(rows)}")
        for row in rows:
            print(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
