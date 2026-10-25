#!/usr/bin/env python3
"""Check that the round-3 pointing record reproduces its captures and carries every template field.

Per voter and per stage the recorded value, accepted set and rationale must equal the capture, matched
against the specific record line for that voter rather than anywhere in the body. The record's template
fields must all be present, in the delivered order. Exit 1 on any mismatch.
"""

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
RECORD = (HERE / "pointing-record.md").read_text()
BODY = RECORD[RECORD.index("## Pointing record"):]

ROLES = {"po": "Product owner", "e1": "Engineer one", "e2": "Engineer two"}
TEMPLATE_FIELDS = [
    "- Tracker-write preflight:",
    "- Refined story identifier:",
    "- Estimate scale:",
    "- Values, recorded before the discussion:",
    "- SM/EM sizing context, after all three values:",
    "- Discussion:",
    "- Re-vote:",
    "- Consensus:",
    "- No-consensus decision:",
    "- Paths accepted:",
    "- Decision rationale:",
    "- Effective maximum:",
    "- Split:",
    "- Challenges:",
    "- Superseded values after a void:",
    "- Anchoring events:",
    "- Tracker writes:",
]

problems = []

# 1. Template fields, in the delivered order.
positions = []
for field in TEMPLATE_FIELDS:
    match = re.search(rf"^{re.escape(field)}", BODY, re.M)
    if not match:
        problems.append(f"template field absent: {field}")
    else:
        positions.append(match.start())
if positions != sorted(positions):
    problems.append("template fields are out of order")

# 2. Values block, per voter.
values_block = BODY.split("- Values, recorded before the discussion:", 1)[-1].split("- SM/EM sizing context", 1)[0]
for key, role in ROLES.items():
    capture = (HERE / "outputs" / f"v2-{key}-output.txt").read_text()
    value = re.search(r"^VALUE: (\d+)", capture, re.M).group(1)
    rationale = re.search(r"^RATIONALE: (.*)", capture, re.M | re.S).group(1).strip()
    expected = f"  - {role}: {value} - \"{rationale}\""
    if expected not in values_block:
        problems.append(f"values block does not carry the {role} capture: {expected[:70]!r}")

# 3. Re-vote line, per voter.
revote_line = re.search(r"^- Re-vote: (.*)$", BODY, re.M)
if not revote_line:
    problems.append("no Re-vote line")
else:
    line = revote_line.group(1)
    for key, role in ROLES.items():
        capture = (HERE / "outputs" / f"v3-{key}-output.txt").read_text()
        accepted = re.search(r"^ACCEPTED: (\{[^}]*\})", capture, re.M).group(1)
        rationale = re.search(r"^RATIONALE: (.*)", capture, re.M | re.S).group(1).strip()
        expected = f"{role.lower()} {accepted} - \"{rationale}\""
        if expected not in line:
            problems.append(f"re-vote line does not carry the {role} capture: {expected[:70]!r}")

# 4. Voided rationales, in the superseded line.
superseded = re.search(r"^- Superseded values after a void: (.*)$", BODY, re.M)
if not superseded:
    problems.append("no Superseded values line")
else:
    for key, role in ROLES.items():
        capture = (HERE / "outputs" / f"v1-{key}-output.txt").read_text()
        value = re.search(r"^VALUE: (\d+)", capture, re.M).group(1)
        rationale = re.search(r"^RATIONALE: (.*)", capture, re.M | re.S).group(1).strip()
        expected = f"{role.lower()} {value} - \"{rationale}\""
        if expected not in superseded.group(1):
            problems.append(f"superseded line does not carry the voided {role} capture: {expected[:70]!r}")

# 5. Capture inventory and the fixed header values.
for stage, expected in (("v1", 3), ("v2", 3), ("v3", 3)):
    found = len(list((HERE / "outputs").glob(f"{stage}-*-output.txt")))
    if found != expected:
        problems.append(f"{stage}: expected {expected} captures, found {found}")
for field in ("- Tracker-write preflight: comment `19253345` on SKL-77.",
              "- Estimate scale: fibonacci",
              "- Consensus: 2 (the highest value in the intersection {2})",
              "- Tracker writes: product owner"):
    if field not in BODY:
        problems.append(f"header value absent: {field!r}")

print(f"template fields checked: {len(TEMPLATE_FIELDS)}")
print(f"captures compared: {3 * len(ROLES)} (values, re-vote, superseded)")
if problems:
    print("MISMATCHES:")
    for problem in problems:
        print(" -", problem)
    sys.exit(1)
print("RECORD MATCHES CAPTURES")
