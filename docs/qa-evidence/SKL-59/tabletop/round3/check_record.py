#!/usr/bin/env python3
"""Check that the round-3 pointing record reproduces its captures.

Every capture line that carries a value or an accepted set must appear in the record, every
capture rationale must appear verbatim, and the record's header fields must name the fixture
and the preflight comment. Exit 1 on any mismatch.
"""

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
RECORD = (HERE / "pointing-record.md").read_text()
BODY = RECORD.split("\n\n", 2)[2]

problems = []
checked = 0

for capture in sorted((HERE / "outputs").glob("*.txt")):
    stage, role, _ = capture.stem.split("-")
    text = capture.read_text()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("VALUE:", "ACCEPTED:")):
            token = line.split(":", 1)[1].strip()
            if token not in BODY:
                problems.append(f"{capture.name}: {line!r} absent from the record")
            checked += 1
        elif line.startswith("RATIONALE:"):
            rationale = line.split(":", 1)[1].strip()
            if rationale and rationale not in BODY:
                problems.append(f"{capture.name}: rationale absent from the record: {rationale[:60]!r}")
            checked += 1

for field in ("- Tracker-write preflight: comment `19253345` on SKL-77.",
              "- Estimate scale: fibonacci",
              "- Consensus: 2 (the highest value in the intersection {2})",
              "- Tracker writes: product owner"):
    if field not in BODY:
        problems.append(f"header field absent: {field!r}")

for stage, expected in (("v1", 3), ("v2", 3), ("v3", 3)):
    found = len(list((HERE / "outputs").glob(f"{stage}-*-output.txt")))
    if found != expected:
        problems.append(f"{stage}: expected {expected} captures, found {found}")

print(f"capture lines checked: {checked}")
if problems:
    print("MISMATCHES:")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print("RECORD MATCHES CAPTURES")
