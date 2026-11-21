# GENERATED from shared/qa-evidence.py by scripts/vendor_shared.py. Edit the source, then rerun the script.
#!/usr/bin/env python3
"""Generate the QA evidence README skeleton for a story.

Writes `<evidence-dir>/<KEY>/README.md` with the headings, metadata lines and verdict table
`skills/qa-verification/SKILL.md` section 5 requires, so the QA agent fills verdicts and evidence
instead of authoring the structure.

  python3 qa-evidence.py --key SKL-386 --item='AC1 - one generator' [--item='AC2 - ...']
                         [--path spike|no-deployment|deployed] [--evidence-dir docs/qa-evidence]

The verdict and evidence cells are left empty, because a generated verdict would be an authored
result. The README is published atomically without overwriting: an existing one, one another
invocation creates at the same moment, and a dangling symlink at its path all exit 1 naming the
file and leave whatever is there untouched, and a write that fails leaves no README behind.
A key outside ^[A-Z][A-Z0-9]+-[0-9]+$ exits 1 and names the key.

An item label is written as one table cell: its line breaks fold to spaces, runs of whitespace
collapse, and a literal `|` is escaped, so a label can never add a column, a row or a heading.
A label or key the repository's doc-lint would reject exits 1 with one stderr line naming it: an
empty label, and one carrying U+2014, a stray term, a verdict word, a runtime-specific term, an
unresolvable `profile.` reference, or the British spelling of artifact outside the evidence tree.

It reads no tracker, makes no network call and needs no credential.
"""

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

DEFAULT_EVIDENCE_DIR = "docs/qa-evidence"
KEY_RE = re.compile(r"[A-Z][A-Z0-9]+-[0-9]+")
PATHS = ("spike", "no-deployment", "deployed")
TABLE_HEADER = "| Item | Verdict | Evidence |"
TABLE_SEPARATOR = "| --- | --- | --- |"
EM_DASH = "\u2014"
BRITISH_ARTIFACT = "arte" + "fact"
# The rules below mirror the doc-lint in tests/test_skills.py, which every committed Markdown file
# must pass; tests/test_qa_evidence.py checks each one against that lint, which is the oracle.
# The verdict values qa-verification records, which the skeleton must never contain.
VERDICT_RE = re.compile(
    r"(?i)\b(?:verified|failed|correct by design|out of scope|not covered|pending owner ruling)\b"
)
# "clean, neutral" and "clean and neutral" are the canonical phrases; every other use of neutral,
# and every other way of describing it, is a stray term.
CANONICAL_RE = re.compile(r"(?i)\bclean(?:,| and) neutral\b")
STRAY_RE = re.compile(
    r"(?i)\bclean[- ]context|\bown (?:clean )?context|\bclean,? (?:[\w-]+,? ){0,2}?(?:agent|subagent|verifier|reviewer|adjudicator|engineer)\b"
    r"|\bfresh (?:\w+ ){0,2}?(?:agent|subagent|verifier|reviewer|adjudicator|context)\b"
    r"|\bbrief (?:a|the) fresh\b|\b(?:hand|delegate|pass)\w* (?:\w+ ){0,3}?to (?:a|the) fresh one\b"
    r"|(?<!runtime-)\bneutral"
)
# Tool and path names of one runtime, which only shared/runtimes.md may carry.
RUNTIME_TERMS_RE = re.compile(
    r"\b(TaskCreate|TaskUpdate|TodoWrite|todowrite|AskUserQuestion|subagent_type|CLAUDE_JOB_DIR)\b"
    r"|mcp__|~/\.claude/|\.opencode/"
)
# Any profile.<path> reference, which the lint resolves against profile/schema.json.
PROFILE_REF_RE = re.compile(
    r"(?<![\w./-])profile\.(?!(?:md|yaml|json)\b)(?!<)([^\s`'\"(),;:!?<>]+)"
)


def metadata_lines(path: str | None) -> list[str]:
    """The metadata lines, with the path-dependent ones only where the path calls for them."""
    lines = ["Date:", "Fixtures:"]
    if path is not None:
        lines.append(f"Path: {path}")
        lines.extend(["Environment:", "Build:"] if path == "deployed" else ["Target:"])
    return lines


def clean_label(label: str) -> str:
    """One table cell's text: line breaks folded to spaces, whitespace collapsed, pipes escaped."""
    folded = " ".join(label.split())
    return folded.replace("|", r"\|")


def lint_problem(text: str, *, spelling: bool) -> str | None:
    """Why `text` would make the generated README fail the repository's doc-lint, or None."""
    if EM_DASH in text:
        return "carries U+2014"
    if STRAY_RE.search(CANONICAL_RE.sub("", text)):
        return "trips the stray-term lint"
    verdict = VERDICT_RE.search(text)
    if verdict:
        return f"carries the verdict word {verdict.group(0)!r}"
    runtime = RUNTIME_TERMS_RE.search(text)
    if runtime:
        return f"carries the runtime-specific term {runtime.group(0)!r}"
    if spelling and BRITISH_ARTIFACT in text.lower():
        return "uses the British spelling of artifact, which the lint requires only in evidence files"
    return None


def find_schema(start: Path) -> dict | None:
    """The profile schema of the repository holding `start`, or None when it has none."""
    for directory in [start.resolve(), *start.resolve().parents]:
        candidate = directory / "profile" / "schema.json"
        if candidate.is_file():
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
    return None


def deref(node, defs: dict) -> dict:
    """A node with its `$ref`, or its `allOf` of exactly one `$ref`, resolved."""
    seen: set[str] = set()
    while isinstance(node, dict):
        if "$ref" in node:
            name = node["$ref"].split("/")[-1]
            if name in seen or name not in defs:
                return {}
            seen.add(name)
            node = defs[name]
        elif "properties" not in node and [list(item) for item in node.get("allOf", [])] == [["$ref"]]:
            node = node["allOf"][0]
        else:
            return node
    return {}


def resolves_ref(schema: dict | None, ref: str) -> bool:
    """Whether `ref`, the text after `profile.`, resolves inside the profile schema."""
    if schema is None:
        return False
    defs = schema.get("$defs", {})
    node: dict = schema
    trailing = False
    for part in ref.rstrip(".").split("."):
        trailing = part.endswith("[]")
        key = part.removesuffix("[]")
        if not key:
            return False
        node = deref(node, defs)
        properties = node.get("properties", {})
        if key not in properties:
            return False
        node = properties[key]
        if trailing:
            node = deref(node, defs).get("items", {})
    return bool(node)


def spelling_applies(evidence_dir: str) -> bool:
    """The spelling lint exempts frozen QA evidence, so it applies outside that tree only."""
    cleaned = Path(evidence_dir).as_posix().strip("/")
    return not (cleaned == DEFAULT_EVIDENCE_DIR or cleaned.startswith(DEFAULT_EVIDENCE_DIR + "/"))


def key_problem(key: str) -> str | None:
    """Why `key` cannot head the skeleton, or None when it can."""
    if not KEY_RE.fullmatch(key):
        return f"error: {key!r} is not a story key (expected ^[A-Z][A-Z0-9]+-[0-9]+$)"
    problem = lint_problem(key, spelling=False)
    if problem is not None:
        return f"error: story key {key!r} {problem}"
    return None


def label_problem(label: str, *, schema: dict | None, spelling: bool) -> str | None:
    """Why a cleaned label cannot be written into the skeleton, or None when it can."""
    if not label:
        return "is empty"
    problem = lint_problem(label, spelling=spelling)
    if problem is not None:
        return problem
    unresolved = [ref for ref in PROFILE_REF_RE.findall(label) if not resolves_ref(schema, ref)]
    if unresolved:
        return f"carries the profile reference profile.{unresolved[0]}, which the profile schema does not resolve"
    return None


def skeleton(key: str, items: list[str], path: str | None) -> str:
    lines = [f"# {key} QA evidence", "", "## QA round 1", "", *metadata_lines(path), ""]
    lines.extend([TABLE_HEADER, TABLE_SEPARATOR])
    lines.extend(f"| {item} |  |  |" for item in items)
    return "\n".join(lines) + "\n"


def publish(target: Path, text: str) -> bool:
    """Publish `text` at `target` without overwriting anything, or report why not."""
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: cannot create {target.parent}: {exc.strerror or exc}", file=sys.stderr)
        return False
    temp: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(dir=target.parent, prefix=".qa-evidence-", suffix=".tmp")
        temp = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(temp, 0o644)
        os.link(temp, target)
    except FileExistsError:
        print(f"error: {target.absolute()} already exists; refusing to overwrite it", file=sys.stderr)
        return False
    except OSError as exc:
        print(f"error: cannot write {target.absolute()}: {exc.strerror or exc}", file=sys.stderr)
        return False
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the QA evidence README skeleton for a story.")
    parser.add_argument("--key", required=True, help="Story key, for example SKL-386.")
    parser.add_argument("--item", action="append", default=[], dest="items", help="One verdict table row.")
    parser.add_argument("--path", choices=PATHS, help="The run's path, when it is known.")
    parser.add_argument("--evidence-dir", default=DEFAULT_EVIDENCE_DIR, help="Evidence directory.")
    args = parser.parse_args(argv)

    problem = key_problem(args.key)
    if problem is not None:
        print(problem, file=sys.stderr)
        return 1
    if not args.evidence_dir:
        print("error: --evidence-dir is empty", file=sys.stderr)
        return 1

    schema = find_schema(Path.cwd())
    spelling = spelling_applies(args.evidence_dir)
    labels = []
    for raw in args.items:
        label = clean_label(raw)
        problem = label_problem(label, schema=schema, spelling=spelling)
        if problem is not None:
            print(f"error: item label {raw!r} cannot be written: it {problem}", file=sys.stderr)
            return 1
        labels.append(label)

    target = Path(args.evidence_dir) / args.key / "README.md"
    text = skeleton(args.key, labels, args.path)
    try:
        text.encode("utf-8")
    except UnicodeError:
        print(f"error: the skeleton for {args.key} cannot be encoded as UTF-8", file=sys.stderr)
        return 1
    if not publish(target, text):
        return 1
    print(target.absolute())
    return 0


if __name__ == "__main__":
    sys.exit(main())
