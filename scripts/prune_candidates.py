#!/usr/bin/env python3
"""List tests, reference files and rules that are candidates for retirement.

Usage: python scripts/prune_candidates.py --since YYYY-MM-DD

Run it from anywhere inside the repository. It resolves HEAD once, evaluates that commit, reads
only git objects, and writes nothing. Each candidate carries its evidence and a retire or keep
proposal; the owner decides at the retro (docs/pruning-routine.md). The three categories:

- tests untouched since D: a tests/test_*.py file whose latest committer time, over every commit
  in the history of HEAD that changed that path (side branches of merges included), is before D.
- reference files uncited at this commit: a shared/*.md source other than README.md that no
  skills/*/SKILL.md cites as references/<name>.
- rules uncited at this commit, unchanged since D: a list item in any shared/*.md file whose own
  lines carry the stop sign, whose text (continuation lines and nested items included, whitespace
  collapsed, case ignored) shares no 40-character run with any file under tests/ or any
  skills/*/SKILL.md, and whose lines were all last changed before D per git blame.

D is 00:00 UTC on the --since date. A shallow or partial clone is refused, since its history or
objects are incomplete and reading them would fetch and write into the repository.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

STOP = "⛔"
WINDOW = 40
ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])(?: {1,4}|\s)")
MARKERS = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s", re.MULTILINE)
FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
BLOCK_START = re.compile(r"^\s*(?:#|>|\||```|~~~|---|\*\*\*|___)")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
CITE_PUNCT = r".,;:!?"  # ends a citation only when a delimiter or the end of the text follows it
CITE_EDGE = r"\s`'\"()\[\]{}<>*|" + CITE_PUNCT

# Every call is pinned to the repository root, takes paths literally, prints them unquoted, takes
# no optional locks, and overrides the configuration that would change what it reads, so the
# report does not depend on the caller's directory or on local git configuration. Git never
# prompts and never fetches a missing object.
GIT = [
    "git", "--literal-pathspecs", "--no-optional-locks", "--no-replace-objects",
    "-c", "core.quotePath=false", "-c", "log.showSignature=false",
]
root = "."


def clean_env() -> dict[str, str]:
    """The caller's environment without the variables that select another repository or history.

    Git lists its repository-local variables (GIT_DIR, GIT_WORK_TREE, GIT_INDEX_FILE and the
    like); without them the repository is always the one the caller's directory is in. Replace
    refs and grafts never substitute history. The GIT_TRACE* variables are dropped first, so no
    git call, this one included, writes a trace file.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_TRACE")}
    local = subprocess.run(
        ["git", "rev-parse", "--local-env-vars"], stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env
    ).stdout.split()
    env = {k: v for k, v in env.items() if k not in local and k != "GIT_NAMESPACE"}
    env.update(GIT_TERMINAL_PROMPT="0", GIT_NO_LAZY_FETCH="1", GIT_GRAFT_FILE=os.devnull)
    return env


ENV = clean_env()


def probe(*args: str) -> subprocess.CompletedProcess:
    # Arguments and output travel as raw bytes (surrogateescape), so no locale and no
    # non-UTF-8 path or text can break or merge them. Output is decoded by hand, not by
    # subprocess, which would turn a carriage return into a line feed.
    argv = [arg.encode("utf-8", "surrogateescape") for arg in (*GIT, "-C", root, *args)]
    result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, env=ENV)
    result.stdout = result.stdout.decode("utf-8", "surrogateescape")
    result.stderr = result.stderr.decode("utf-8", "surrogateescape")
    return result


def git(*args: str) -> str:
    result = probe(*args)
    if result.returncode != 0:
        raise SystemExit(f"prune_candidates: git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def shown(path: str) -> str:
    """A path as one report field: control characters are escaped so a row stays one line."""
    return CONTROL.sub(lambda m: f"\\x{ord(m.group()):02x}", path)


def day(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%d")


def collapse(text: str) -> str:
    return " ".join(text.split())


def parse_since(value: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        parsed = None
    if parsed is None or parsed.date().isoformat() != value:
        raise argparse.ArgumentTypeError(f"expected a date as YYYY-MM-DD, got {value!r}")
    return parsed.replace(tzinfo=timezone.utc)


def show(head: str, path: str) -> str:
    return git("cat-file", "blob", f"{head}:{path}")


def test_candidates(head: str, files: list[str], cutoff: int) -> list[str]:
    out = []
    for path in files:
        if not re.fullmatch(r"tests/test_[^/]*\.py", path):
            continue
        times = git("log", "--full-history", "--no-follow", "--format=%ct", head, "--", path).split()
        if not times:
            raise SystemExit(f"prune_candidates: no commit in the history of {head} changed {shown(path)}")
        last = max(int(t) for t in times)
        if last < cutoff:
            out.append(
                f"- {shown(path)} | last change {day(last)} | proposal: keep "
                "(it still runs on every CI run; retire only on a finding that it adds no value)"
            )
    return out


def rule_sources(files: list[str]) -> list[str]:
    return [f for f in files if re.fullmatch(r"shared/[^/]*\.md", f)]


def sources(files: list[str]) -> list[str]:
    """The reference-file sources: every shared/*.md but the README, which is no reference file."""
    return [f for f in rule_sources(files) if f != "shared/README.md"]


def skill_texts(head: str, files: list[str]) -> list[str]:
    return [show(head, f) for f in files if re.fullmatch(r"skills/[^/]+/SKILL\.md", f)]


def cites(cite: str, text: str) -> bool:
    """True when text names cite as a whole relative path (optionally ./-prefixed).

    A cite counts only between delimiters (whitespace, quotes, brackets, punctuation), optionally
    followed by a #anchor. Punctuation after the cite ends it only when a delimiter or the end of
    the text follows. A cite inside a longer path or name, such as ../other/references/x.md,
    references/x.md/y, references/x.md.bak, references/x.md:y.md or references/x.md+old, does not
    count.
    """
    close = CITE_EDGE.removesuffix(CITE_PUNCT)
    pattern = (
        rf"(?:^|(?<=[{CITE_EDGE}]))(?:\./)?{re.escape(cite)}"
        rf"(?=$|[{close}#]|[{CITE_PUNCT}](?![^{CITE_EDGE}]))"
    )
    return re.search(pattern, text, re.MULTILINE) is not None


def reference_candidates(files: list[str], skills: list[str]) -> list[str]:
    out = []
    for path in sources(files):
        cite = f"references/{path.removeprefix('shared/')}"
        if not any(cites(cite, text) for text in skills):
            out.append(f"- {shown(path)} | no skills/*/SKILL.md cites {shown(cite)} | proposal: retire")
    return out


def indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def fenced_lines(lines: list[str]) -> list[bool]:
    """Mark each line inside a fenced code block, fences included.

    A fence closes only on the same character repeated at least as many times with nothing after
    it, so a ``` line inside a ~~~ block (or a shorter fence) stays inside the block. A fence
    belongs to its container: it opens at most 3 columns right of the content column of the list
    item it sits in (column 0 outside a list), and a fence left open ends with that item, at the
    first non-blank line indented left of that content column.
    """
    marks = []
    opener: str | None = None
    floor = 0
    items: list[tuple[int, int]] = []  # (marker indent, content column) of the enclosing list items
    for line in lines:
        if opener is not None and line.strip() and indent(line) < floor:
            opener = None  # the item that holds the fence has ended
        match = FENCE.match(line)
        if opener is None:
            item = ITEM.match(line)
            if line.strip():
                while items and indent(line) < items[-1][1] and not (item and indent(line) > items[-1][0]):
                    items.pop()
            if item:
                items.append((len(item.group(1)), item.end()))
            container = items[-1][1] if items and not item else 0
            if match and len(match.group(1)) - container <= 3:
                opener, floor = match.group(2), container
            marks.append(opener is not None)
            continue
        marks.append(True)
        if (
            match
            and match.group(2)[0] == opener[0]
            and len(match.group(2)) >= len(opener)
            and not match.group(3).strip()
        ):
            opener = None
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


def is_item(lines: list[str], fenced: list[bool], n: int) -> re.Match | None:
    return None if fenced[n] else ITEM.match(lines[n])


def own_lines(lines: list[str], fenced: list[bool], start: int, end: int) -> list[str]:
    """The lines of the item at start that are not inside one of its nested items."""
    own = [lines[start]]
    k = start + 1
    while k <= end:
        child = is_item(lines, fenced, k)
        if child:
            k = item_end(lines, fenced, k, len(child.group(1))) + 1
            continue
        own.append(lines[k])
        k += 1
    return own


def rule_items(text: str) -> list[tuple[int, int, str]]:
    """Return (first line, last line, text) for each list item whose own lines carry the stop sign.

    An item runs to its last continuation line, nested items included; a nested item that
    carries the stop sign is also its own item. List markers inside fenced code blocks are not
    items.
    """
    lines = text.split("\n")  # git counts lines by LF alone, so blame line numbers match
    fenced = fenced_lines(lines)
    items = []
    for i in range(len(lines)):
        match = is_item(lines, fenced, i)
        if not match:
            continue
        end = item_end(lines, fenced, i, len(match.group(1)))
        if STOP in "\n".join(own_lines(lines, fenced, i, end)):
            items.append((i + 1, end + 1, "\n".join(lines[i : end + 1])))
    return items


def rule_text(item: str) -> str:
    return collapse(MARKERS.sub("", item).replace(STOP, ""))


def cited_rules(texts: list[str], haystack: str) -> set[int]:
    """Return the indexes of the texts that share a WINDOW-character run with the haystack.

    A text shorter than WINDOW, the empty text included, has no WINDOW-character run and is never
    cited.
    """
    found = set()
    index: dict[str, list[int]] = {}
    for n, text in enumerate(texts):
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
    return max(int(line.split()[1]) for line in blame.split("\n") if line.startswith("committer-time "))


def blobs(head: str) -> list[str]:
    """Every file path in the tree of head; submodules and other non-blob entries are skipped."""
    out = []
    for entry in git("ls-tree", "-r", "-z", head).split("\0"):
        if not entry:
            continue
        meta, _, path = entry.partition("\t")
        if meta.split()[1] == "blob":
            out.append(path)
    return out


def rule_candidates(head: str, files: list[str], skills: list[str], cutoff: int) -> list[str]:
    tests = [show(head, f) for f in files if f.startswith("tests/")]
    haystack = "\n".join(collapse(t).lower() for t in tests + skills)
    rules = [
        (path, first, last, rule_text(body))
        for path in rule_sources(files)
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
                f"- {shown(path)}:{first} | last change {day(changed)} | \"{text}\" | proposal: retire "
                "(no test or SKILL.md quotes it)"
            )
    return out


def refusal(reason: str) -> int:
    print(f"prune_candidates: refusing to run in a {reason}", file=sys.stderr)
    return 2


def partial_clone() -> bool:
    if probe("config", "--get", "extensions.partialClone").stdout.strip():
        return True
    # --type=bool makes git apply its own boolean parsing, so yes, on and 1 all read as true.
    promisors = probe("config", "--type=bool", "--get-regexp", r"^remote\..*\.promisor$").stdout
    return any(line.rsplit(" ", 1)[-1] == "true" for line in promisors.split("\n"))


def missing_ignore_revs() -> list[str]:
    """Configured blame.ignoreRevsFile values that name no file.

    The empty --ignore-revs-file clears every configured file, but git still opens each one first
    and fails on a missing one, so such a configuration is refused before the report starts.
    """
    values = probe("config", "--type=path", "--get-all", "blame.ignoreRevsFile").stdout.split("\n")
    return [v for v in values if v and not os.path.isfile(os.path.join(root, v))]


def main(argv: list[str] | None = None) -> int:
    global root
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", required=True, type=parse_since, metavar="YYYY-MM-DD")
    args = parser.parse_args(argv)

    root = git("rev-parse", "--show-toplevel").removesuffix("\n")
    if git("rev-parse", "--is-shallow-repository").strip() == "true":
        return refusal(
            "shallow clone, whose history is incomplete; run `git fetch --unshallow` or use a full clone"
        )
    if partial_clone():
        return refusal(
            "partial clone, whose missing objects would be fetched into it; use a full clone"
        )

    missing = missing_ignore_revs()
    if missing:
        return refusal(
            f"repository whose blame.ignoreRevsFile names a missing file ({', '.join(map(shown, missing))}); "
            "create it or unset blame.ignoreRevsFile"
        )

    head = git("rev-parse", "--verify", "HEAD^{commit}").strip()
    since = args.since.date().isoformat()
    cutoff = int(args.since.timestamp())
    files = blobs(head)
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
