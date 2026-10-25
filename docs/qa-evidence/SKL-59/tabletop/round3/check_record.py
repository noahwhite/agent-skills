#!/usr/bin/env python3
"""Check that the round-3 pointing record reproduces and agrees with its captures.

The check is semantic, not textual:
- every template field appears exactly once, in the delivered order;
- the values block carries exactly the three standing captures, line for line;
- the re-vote line carries exactly the three captures, and the consensus is derived from them;
- the discussion line agrees with the standing values;
- the superseded line carries the three voided captures;
- the target sentence, read from raw-record.md, appears nowhere outside the superseded line;
- the fixed header values are exact.

Exit 1 on any mismatch, with every problem printed.
"""

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
RECORD = (HERE / "pointing-record.md").read_text()
BODY = RECORD[RECORD.index("## Pointing record"):]
RAW = (HERE / "raw-record.md").read_text()

ROLES = {"po": "Product owner", "e1": "Engineer one", "e2": "Engineer two"}
FIELDS = [
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


def capture(stage, key):
    text = (HERE / "outputs" / f"{stage}-{key}-output.txt").read_text()
    if stage == "v3":
        head = re.search(r"^ACCEPTED: (\{[^}]*\})", text, re.M).group(1)
    else:
        head = re.search(r"^VALUE: (\d+)", text, re.M).group(1)
    rationale = re.search(r"^RATIONALE: (.*)", text, re.M | re.S).group(1).strip()
    return head, rationale


# 1. Each template field exactly once, in order.
positions = []
for field in FIELDS:
    hits = re.findall(rf"^{re.escape(field)}", BODY, re.M)
    if len(hits) != 1:
        problems.append(f"template field appears {len(hits)} times: {field}")
    else:
        positions.append(BODY.index(field))
if len(positions) == len(FIELDS) and positions != sorted(positions):
    problems.append("template fields are out of order")

# 2. Values block: exactly the three standing captures, as whole lines.
values_block = BODY.split("- Values, recorded before the discussion:", 1)[-1].split("- SM/EM sizing context", 1)[0]
value_lines = [ln.strip() for ln in values_block.splitlines() if ln.strip()]
expected_values = []
standing = {}
for key, role in ROLES.items():
    value, rationale = capture("v2", key)
    standing[key] = int(value)
    expected_values.append(f'- {role}: {value} - "{rationale}"')
if value_lines != expected_values:
    problems.append(f"values block differs from the standing captures:\n  record: {value_lines}\n  capture: {expected_values}")

# 3. Re-vote line: exactly the three captures, and the consensus derived from them.
revote = re.search(r"^- Re-vote: (.*)$", BODY, re.M)
consensus = re.search(r"^- Consensus: (.*)$", BODY, re.M)
if not revote or not consensus:
    problems.append("re-vote or consensus line missing")
else:
    line = revote.group(1)
    sets = []
    for key, role in ROLES.items():
        accepted, rationale = capture("v3", key)
        expected = f'{role.lower()} {accepted} - "{rationale}"'
        if expected not in line:
            problems.append(f"re-vote line does not carry the {role} capture")
        sets.append({int(n) for n in re.findall(r"\d+", accepted)})
    if not line.startswith(f"product owner {{"): 
        problems.append("re-vote line does not start with the product-owner entry")
    intersection = set.intersection(*sets)
    if intersection:
        want = f"2 (the highest value in the intersection {{2}})" if max(intersection) == 2 else str(max(intersection))
        if consensus.group(1).strip() != want:
            problems.append(f"consensus does not match the re-vote sets {sets}: {consensus.group(1).strip()!r}")
    else:
        if not consensus.group(1).strip().startswith("none"):
            problems.append(f"empty intersection {sets} but consensus says {consensus.group(1).strip()!r}")

# 4. Discussion agrees with the standing values.
discussion = re.search(r"^- Discussion: (.*)$", BODY, re.M)
if not discussion:
    problems.append("discussion line missing")
else:
    high, low = max(standing.values()), min(standing.values())
    want = f"high {high}, low {low}."
    if discussion.group(1).strip() != want:
        problems.append(f"discussion {discussion.group(1).strip()!r} disagrees with standing values {standing}")

# 5. Superseded line carries the three voided captures.
superseded = re.search(r"^- Superseded values after a void: (.*)$", BODY, re.M)
if not superseded:
    problems.append("superseded line missing")
else:
    for key, role in ROLES.items():
        value, rationale = capture("v1", key)
        expected = f'{role.lower()} {value} - "{rationale}"'
        if expected not in superseded.group(1):
            problems.append(f"superseded line does not carry the voided {role} capture")

# 6. The target sentence stays out of every line except the superseded one.
target = None
match = re.search(r'"This should be[^"]*"', RAW)
if match:
    target = match.group(0).strip('"')
if not target:
    problems.append("could not read the target sentence from raw-record.md")
else:
    for number, line in enumerate(BODY.splitlines(), 1):
        if target in line and not line.startswith("- Superseded values after a void:"):
            problems.append(f"target sentence leaks at record line {number}: {line[:70]!r}")
    for field in ("- Challenges:", "- Anchoring events:"):
        match = re.search(rf"^{re.escape(field)}(.*)$", BODY, re.M)
        if match and target in match.group(1):
            problems.append(f"target sentence present in {field}")

# 7. Fixed header values.
for field in ("- Tracker-write preflight: comment `19253345` on SKL-77.",
              "- Refined story identifier: the fixture description as filed; no refinement round was run on a disposable tabletop.",
              "- Estimate scale: fibonacci",
              "- Effective maximum: 5 (the 8-point rule still triggers at 8 or more)",
              "- Split: none",
              "- Tracker writes: product owner"):
    if field not in BODY:
        problems.append(f"header value absent: {field!r}")

# 8. Capture inventory.
for stage, expected in (("v1", 3), ("v2", 3), ("v3", 3)):
    found = len(list((HERE / "outputs").glob(f"{stage}-*-output.txt")))
    if found != expected:
        problems.append(f"{stage}: expected {expected} captures, found {found}")

print(f"template fields checked: {len(FIELDS)}")
print(f"captures compared: {3 * len(ROLES)} (standing, re-vote, voided)")
if problems:
    print("MISMATCHES:")
    for problem in problems:
        print(" -", problem)
    sys.exit(1)
print("RECORD MATCHES CAPTURES")
