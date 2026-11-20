# GENERATED from shared/qa-evidence.py by scripts/vendor_shared.py. Edit the source, then rerun the script.
#!/usr/bin/env python3
"""Generate the QA evidence README skeleton for a story.

Writes `<evidence-dir>/<KEY>/README.md` with the headings, metadata lines and verdict table
`skills/qa-verification/SKILL.md` section 5 requires, so the QA agent fills verdicts and evidence
instead of authoring the structure.

  python3 qa-evidence.py --key SKL-386 --item='AC1 - one generator' [--item='AC2 - ...']
                         [--path spike|no-deployment|deployed] [--evidence-dir docs/qa-evidence]

The verdict and evidence cells are left empty, because a generated verdict would be an authored
result. The README is created exclusively, so an existing one, a README another invocation creates
at the same moment, and a dangling symlink at its path all exit 1 naming the file and leave
whatever is there untouched. A key outside ^[A-Z][A-Z0-9]+-[0-9]+$ exits 1 and names the key.

An item label is written as one table cell: its line breaks fold to spaces, runs of whitespace
collapse, and a literal `|` is escaped, so a label can never add a column, a row or a heading. A
label the repository's doc-lint would reject, or one that would read as a verdict, exits 1 with
one stderr line naming the label: an empty label, and one carrying U+2014, a stray term or a
verdict word.

It reads no tracker, makes no network call and needs no credential.
"""

import argparse
import re
import sys
from pathlib import Path

DEFAULT_EVIDENCE_DIR = "docs/qa-evidence"
KEY_RE = re.compile(r"[A-Z][A-Z0-9]+-[0-9]+")
PATHS = ("spike", "no-deployment", "deployed")
TABLE_HEADER = "| Item | Verdict | Evidence |"
TABLE_SEPARATOR = "| --- | --- | --- |"
EM_DASH = "\u2014"
# The verdict values qa-verification records, which the skeleton must never contain.
VERDICT_WORDS = (
    "verified",
    "failed",
    "correct by design",
    "out of scope",
    "not covered",
    "pending owner ruling",
)
# Mirrors STRAY_RE in tests/test_skills.py, the lint every committed Markdown file must pass, and
# is deliberately at least as strict; tests/test_qa_evidence.py pins that every label the lint
# rejects is rejected here.
STRAY_RE = re.compile(
    r"(?i)\bclean[- ]context|\bown (?:clean )?context|\bclean,? (?:[\w-]+,? ){0,2}?(?:agent|subagent|verifier|reviewer|adjudicator|engineer)\b"
    r"|\bfresh (?:\w+ ){0,2}?(?:agent|subagent|verifier|reviewer|adjudicator|context)\b"
    r"|\bbrief (?:a|the) fresh\b|\b(?:hand|delegate|pass)\w* (?:\w+ ){0,3}?to (?:a|the) fresh one\b"
    r"|(?<!runtime-)\bneutral"
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


def label_problem(label: str) -> str | None:
    """Why a cleaned label cannot be written into the skeleton, or None when it can."""
    if not label:
        return "the label is empty"
    if EM_DASH in label:
        return "the label carries U+2014"
    if STRAY_RE.search(label):
        return "the label trips the stray-term lint"
    lowered = label.lower()
    for word in VERDICT_WORDS:
        if word in lowered:
            return f"the label carries the verdict word {word!r}"
    return None


def skeleton(key: str, items: list[str], path: str | None) -> str:
    lines = [f"# {key} QA evidence", "", "## QA round 1", "", *metadata_lines(path), ""]
    lines.extend([TABLE_HEADER, TABLE_SEPARATOR])
    lines.extend(f"| {item} |  |  |" for item in items)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the QA evidence README skeleton for a story.")
    parser.add_argument("--key", required=True, help="Story key, for example SKL-386.")
    parser.add_argument("--item", action="append", default=[], dest="items", help="One verdict table row.")
    parser.add_argument("--path", choices=PATHS, help="The run's path, when it is known.")
    parser.add_argument("--evidence-dir", default=DEFAULT_EVIDENCE_DIR, help="Evidence directory.")
    args = parser.parse_args(argv)

    if not KEY_RE.fullmatch(args.key):
        print(f"error: {args.key!r} is not a story key (expected ^[A-Z][A-Z0-9]+-[0-9]+$)", file=sys.stderr)
        return 1

    labels = []
    for raw in args.items:
        label = clean_label(raw)
        problem = label_problem(label)
        if problem is not None:
            print(f"error: item label {raw!r} cannot be written: {problem}", file=sys.stderr)
            return 1
        labels.append(label)

    target = Path(args.evidence_dir) / args.key / "README.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    text = skeleton(args.key, labels, args.path)
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(text)
    except FileExistsError:
        print(f"error: {target.absolute()} already exists; refusing to overwrite it", file=sys.stderr)
        return 1
    print(target.absolute())
    return 0


if __name__ == "__main__":
    sys.exit(main())
