#!/usr/bin/env python3
"""Check the SKL-78 (round 4) pointing record against its captures.

Semantic checks: every template field exactly once in the delivered order; the values block equal to the
three standing captures line for line; the discussion line naming exactly the high and low of the standing
values; the re-vote line exactly the three captures; the consensus recomputed from the accepted sets; the
superseded line carrying the three voided captures; the target sentence absent from every field except the
superseded one; the challenged ground's capture and outcome present in the Challenges line; the re-vote
prompts stating that the discussion named only the high and the low; and the fixed header values.
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
    head = (re.search(r"^ACCEPTED: (\{[^}]*\})", text, re.M).group(1) if stage == "v3"
            else re.search(r"^VALUE: (\d+)", text, re.M).group(1))
    rationale = re.search(r"^RATIONALE: (.*)", text, re.M | re.S).group(1).strip()
    return head, rationale


# 1. Fields once each, in order.
positions = []
for field in FIELDS:
    hits = re.findall(rf"^{re.escape(field)}", BODY, re.M)
    if len(hits) != 1:
        problems.append(f"template field appears {len(hits)} times: {field}")
    else:
        positions.append(BODY.index(field))
if len(positions) == len(FIELDS) and positions != sorted(positions):
    problems.append("template fields are out of order")

# 2. Values block equals the standing captures.
block = BODY.split("- Values, recorded before the discussion:", 1)[-1].split("- SM/EM sizing context", 1)[0]
lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
expected = [f'- {ROLES[k]}: {capture("v2", k)[0]} - "{capture("v2", k)[1]}"' for k in ROLES]
if lines != expected:
    problems.append(f"values block differs from the standing captures:\n  record: {lines}\n  capture: {expected}")

# 3. Discussion names exactly the standing high and low.
standing = {k: int(capture("v2", k)[0]) for k in ROLES}
discussion = re.search(r"^- Discussion: high (\d+), low (\d+)\.", BODY, re.M)
if not discussion:
    problems.append("discussion line does not hold the required high/low round")
else:
    if (int(discussion.group(1)), int(discussion.group(2))) != (max(standing.values()), min(standing.values())):
        problems.append(f"discussion {discussion.groups()} disagrees with standing values {standing}")

# 4. Re-vote line exactly the three captures, and the consensus derived from them.
revote = re.search(r"^- Re-vote: (.*)$", BODY, re.M)
consensus = re.search(r"^- Consensus: (.*)$", BODY, re.M)
expected_line = "- Re-vote: " + "; ".join(f'{ROLES[k].lower()} {capture("v3", k)[0]} - "{capture("v3", k)[1]}"' for k in ROLES)
if not revote or revote.group(0).strip() != expected_line:
    problems.append("re-vote line is not exactly the three captures in order")
sets = [{int(n) for n in re.findall(r"\d+", capture("v3", k)[0])} for k in ROLES]
inter = set.intersection(*sets)
want = (f"{max(inter)} (the highest value in the intersection {{{max(inter)}}})" if inter
        else "none; the intersection of " + ", ".join(capture("v3", k)[0] for k in ROLES) + " is empty")
if not consensus or consensus.group(1).strip() != want:
    problems.append(f"consensus {consensus.group(1).strip() if consensus else None!r} disagrees with the sets {sets}")

# 5. Superseded line carries the three voided captures.
superseded = re.search(r"^- Superseded values after a void: (.*)$", BODY, re.M)
if not superseded:
    problems.append("superseded line missing")
else:
    for k in ROLES:
        v, r = capture("v1", k)
        if f'{ROLES[k].lower()} {v} - "{r}"' not in superseded.group(1):
            problems.append(f"superseded line does not carry the voided {ROLES[k]} capture")

# 6. The target sentence stays out of every field except the superseded one.
match = re.search(r'"This should be[^"]*"', RAW)
if not match:
    problems.append("could not read the target sentence from raw-record.md")
else:
    target = match.group(0).strip('"')
    for number, line in enumerate(BODY.splitlines(), 1):
        if target in line and not line.startswith("- Superseded values after a void:"):
            problems.append(f"target sentence leaks at record line {number}")

# 6b. The Anchoring events line certifies the stop, the void and the blind re-run.
anchoring = re.search(r"^- Anchoring events: (.*)$", BODY, re.M)
if not anchoring:
    problems.append("anchoring events line missing")
else:
    claim = anchoring.group(1)
    for fragment in ("target value", "raw-record.md", "voided", "re-run blind in newly created voter contexts"):
        if fragment not in claim:
            problems.append(f"anchoring events line lacks {fragment!r}")

# 7. The challenged ground and its outcome are recorded.
challenges = re.search(r"^- Challenges: (.*)$", BODY, re.M)
if not challenges:
    problems.append("challenges line missing")
else:
    coverage = capture("v1", "e2")[1]
    if "Coverage is thin" not in challenges.group(1):
        problems.append("challenges line does not quote the challenged coverage ground")
    outcome = (HERE / "outputs" / "chal-e2-output.txt").read_text().splitlines()[0].split(":", 1)[1].strip()
    if f"Outcome: {outcome}" not in challenges.group(1):
        problems.append(f"challenges line does not record the outcome {outcome!r}")
    prompt_text = (HERE / "prompts" / "chal-prompt.txt").read_text()
    match = re.search(r"The facilitator has challenged that ground: (.*?)\n\nReply in this exact shape", prompt_text, re.S)
    if not match:
        problems.append("could not read the captured challenge text")
    elif match.group(1).strip() not in challenges.group(1):
        problems.append("challenges line does not quote the captured challenge verbatim")

# 8. Re-vote prompts state the discussion that was held.
for prompt in sorted((HERE / "prompts").glob("v3-*-prompt.txt")):
    text = prompt.read_text().lower()
    if "discussion round was held" not in text or "high value" not in text:
        problems.append(f"{prompt.name} does not state the held discussion round")

# 9. Fixed header values and capture inventory.
for field in ("- Tracker-write preflight: comment `c671f2cd` on SKL-78.",
              "- Estimate scale: fibonacci",
              "- Effective maximum: 5 (the 8-point rule still triggers at 8 or more)",
              "- Split: none",
              "- Tracker writes: product owner"):
    if field not in BODY:
        problems.append(f"header value absent: {field!r}")
for stage, expected in (("v1", 3), ("v2", 3), ("v3", 3), ("chal", 1)):
    found = len(list((HERE / "outputs").glob(f"{stage}-*-output.txt")))
    if found != expected:
        problems.append(f"{stage}: expected {expected} captures, found {found}")

print(f"template fields checked: {len(FIELDS)}")
print("captures compared: 10")
if problems:
    print("MISMATCHES:")
    for problem in problems:
        print(" -", problem)
    sys.exit(1)
print("RECORD MATCHES CAPTURES")
