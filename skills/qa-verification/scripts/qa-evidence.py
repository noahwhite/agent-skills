# GENERATED from shared/qa-evidence.py by scripts/vendor_shared.py. Edit the source, then rerun the script.
#!/usr/bin/env python3
"""Generate the QA evidence README skeleton for a story.

Writes `<evidence-dir>/<KEY>/README.md` with the headings, metadata lines and verdict table
`skills/qa-verification/SKILL.md` section 5 requires, so the QA agent fills verdicts and evidence
instead of authoring the structure.

  python3 qa-evidence.py --key SKL-386 --item 'AC1 - one generator' [--item 'AC2 - ...']
                         [--path spike|no-deployment|deployed] [--evidence-dir docs/qa-evidence]

The verdict and evidence cells are left empty, because a generated verdict would be an authored
result. An existing README is never overwritten: the script exits 1 and names the file. A key
outside ^[A-Z][A-Z0-9]+-[0-9]+$ exits 1 and names the key.

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


def metadata_lines(path: str | None) -> list[str]:
    """The metadata lines, with the path-dependent ones only where the path calls for them."""
    lines = ["Date:", "Fixtures:"]
    if path is not None:
        lines.append(f"Path: {path}")
        lines.extend(["Environment:", "Build:"] if path == "deployed" else ["Target:"])
    return lines


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

    target = (Path(args.evidence_dir) / args.key / "README.md").resolve()
    if target.exists():
        print(f"error: {target} already exists; refusing to overwrite it", file=sys.stderr)
        return 1

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(skeleton(args.key, args.items, args.path), encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
