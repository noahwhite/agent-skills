#!/usr/bin/env python3
"""Check the SKL-79 (round 5) pointing record against its captures.

Semantic checks: every template field exactly once in the delivered order; the values block equal to the
three standing captures line for line; the sizing-context line carrying the permitted factual reference and
not the prescription; the discussion line naming exactly the standing high and low; the re-vote line exactly
the three captures; the consensus recomputed from the accepted sets; the superseded line carrying both
voided sets; the prescription absent from every field except the superseded one and the raw record; the
challenged ground, its captured challenge and its unretracted outcome recorded; the recovered discussion
remarks attributed to their own voters in the raw record; and the fixed header values.
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
SM_EM = (HERE / "outputs" / "sm-em-output.txt").read_text()
PERMITTED = re.search(r"^REFERENCE: (.*)$", SM_EM, re.M).group(1).strip()
PRESCRIPTION = re.search(r"^PRESCRIPTION: (.*)$", SM_EM, re.M).group(1).strip()
# A prescription says what this story's value is or should be; a reference never does.
PRESCRIPTION_PATTERN = re.compile(
    r"(?i)\b(?:this (?:one|story)|it)\s+(?:should|ought to|must|has to|needs to|is|scores?|lands?)\s+(?:be\s+)?(?:a\s+|an\s+)?\d"
    r"|\bi would size\b[^.\n]*\d|\bthis story at \d+ points\b|\btarget of \d+ fits\b|\bi would go (?:higher|lower)\b|\bthe (?:highest|lowest) vote is the realistic one\b"
    r"|\ba (?:target|score) of \d+\b"
)
problems = []


def capture(stage, key):
    text = (HERE / "outputs" / f"{stage}-{key}-output.txt").read_text()
    head = (re.search(r"^ACCEPTED: (\{[^}]*\})", text, re.M).group(1) if stage == "v4"
            else re.search(r"^VALUE: (\d+)", text, re.M).group(1))
    rationale = re.search(r"^RATIONALE: (.*)", text, re.M | re.S).group(1).strip()
    return head, rationale


positions = []
for field in FIELDS:
    hits = re.findall(rf"^{re.escape(field)}", BODY, re.M)
    if len(hits) != 1:
        problems.append(f"template field appears {len(hits)} times: {field}")
    else:
        positions.append(BODY.index(field))
if len(positions) == len(FIELDS) and positions != sorted(positions):
    problems.append("template fields are out of order")

block = BODY.split("- Values, recorded before the discussion:", 1)[-1].split("- SM/EM sizing context", 1)[0]
lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
expected = [f'- {ROLES[k]}: {capture("v3", k)[0]} - "{capture("v3", k)[1]}"' for k in ROLES]
if lines != expected:
    problems.append("values block differs from the standing captures")

sizing = re.search(r"^- SM/EM sizing context, after all three values: (.*)$", BODY, re.M)
if not sizing:
    problems.append("sizing-context line missing")
else:
    if PERMITTED not in sizing.group(1):
        problems.append("sizing-context line does not carry the permitted factual reference")
    if PRESCRIPTION in sizing.group(1):
        problems.append("sizing-context line publishes the prescription")

standing = {k: int(capture("v3", k)[0]) for k in ROLES}
discussion = re.search(r"^- Discussion: high (\d+), low (\d+)", BODY, re.M)
if not discussion:
    problems.append("discussion line does not hold the required high/low round")
elif (int(discussion.group(1)), int(discussion.group(2))) != (max(standing.values()), min(standing.values())):
    problems.append(f"discussion {discussion.groups()} disagrees with standing values {standing}")

revote = re.search(r"^- Re-vote: (.*)$", BODY, re.M)
consensus = re.search(r"^- Consensus: (.*)$", BODY, re.M)
expected_line = "- Re-vote: " + "; ".join(f'{ROLES[k].lower()} {capture("v4", k)[0]} - "{capture("v4", k)[1]}"' for k in ROLES)
if not revote or revote.group(0).strip() != expected_line:
    problems.append("re-vote line is not exactly the three captures in order")
sets = [{int(n) for n in re.findall(r"\d+", capture("v4", k)[0])} for k in ROLES]
inter = set.intersection(*sets)
want = (f"{max(inter)} (the highest value in the intersection {{{', '.join(str(n) for n in sorted(inter))}}})" if inter
        else "none; the intersection of " + ", ".join(capture("v4", k)[0] for k in ROLES) + " is empty")
if not consensus or consensus.group(1).strip() != want:
    problems.append(f"consensus {consensus.group(1).strip() if consensus else None!r} disagrees with the sets {sets}")

superseded = re.search(r"^- Superseded values after a void: (.*)$", BODY, re.M)
if not superseded:
    problems.append("superseded line missing")
else:
    for stage in ("v1", "v2"):
        for k in ROLES:
            v, r = capture(stage, k)
            if f'{ROLES[k].lower()} {v} - "{r}"' not in superseded.group(1):
                problems.append(f"superseded line does not carry the {stage} {ROLES[k]} capture")

for number, line in enumerate(BODY.splitlines(), 1):
    if PRESCRIPTION in line or PRESCRIPTION_PATTERN.search(line):
        problems.append(f"prescription leaks at record line {number}: {line[:60]!r}")
if PRESCRIPTION not in RAW:
    problems.append("raw record does not quote the prescription verbatim")

challenges = re.search(r"^- Challenges: (.*)$", BODY, re.M)
if not challenges:
    problems.append("challenges line missing")
else:
    standing_e2 = capture("v2", "e2")[1]
    if standing_e2 not in challenges.group(1):
        problems.append("challenges line does not quote the challenged standing rationale")
    chal_prompt = (HERE / "prompts" / "chal-e2-prompt.txt").read_text()
    m = re.search(r"The facilitator has challenged that ground: (.*?)\n\n", chal_prompt, re.S)
    if not m or m.group(1).strip() not in challenges.group(1):
        problems.append("challenges line does not quote the captured challenge verbatim")
    outcome = (HERE / "outputs" / "chal-e2-output.txt").read_text().splitlines()[0].split(":", 1)[1].strip()
    if f"Outcome: {outcome}" not in challenges.group(1):
        problems.append(f"challenges line does not record the outcome {outcome!r}")

for k in ROLES:
    remark = (HERE / "outputs" / f"disc3-{k}-output.txt").read_text().split(":", 1)[1].strip()
    if remark.upper() != "NONE" and f'- {ROLES[k]}: "{remark}"' not in RAW:
        problems.append(f"raw record does not attribute the {ROLES[k]} discussion remark to that voter")

allowed_values = {max(standing.values()), min(standing.values())}
for prompt in sorted((HERE / "prompts").glob("disc3-*-prompt.txt")):
    text = prompt.read_text()
    if f"high value, {max(standing.values())}, and the low value, {min(standing.values())}" not in text:
        problems.append(f"{prompt.name} does not state the standing high and low")
    named = {int(n) for n in re.findall(r"(?:value,?|points?)\s*(\d+)", text, re.I)}
    if not named <= allowed_values:
        problems.append(f"{prompt.name} discloses a value other than the high and the low: {sorted(named - allowed_values)}")
    if re.search(r"(?i)\bvoted\b|\bscored\b|\bsubmitted\b", text):
        problems.append(f"{prompt.name} reports how another voter voted")
    own = prompt.name.split("-")[1]
    for other_key, other_role in ROLES.items():
        if other_key != own and re.search(rf"(?i)\b{other_role.lower()}\b", text):
            problems.append(f"{prompt.name} names another voter's role, which can disclose its value")

anchoring = re.search(r"^- Anchoring events: (.*)$", BODY, re.M)
if not anchoring:
    problems.append("anchoring events line missing")
else:
    claim = anchoring.group(1)
    for fragment in ("prescribed this story's value", "raw-record.md", "coverage ground", "neither restated nor retracted", "re-run blind in newly created voter contexts"):
        if fragment not in claim:
            problems.append(f"anchoring events line lacks {fragment!r}")

for prompt in sorted((HERE / "prompts").glob("v4-*-prompt.txt")):
    text = prompt.read_text()
    if PRESCRIPTION_PATTERN.search(text):
        problems.append(f"{prompt.name} carries a prescription")
    for value in {str(n) for n in range(1, 14)}:
        if re.search(rf"\bvalue,? {value}\b", text) and int(value) not in {max(standing.values()), min(standing.values())}:
            problems.append(f"{prompt.name} names a value other than the high and the low")

if PRESCRIPTION_PATTERN.search(PERMITTED):
    problems.append("the permitted reference itself reads as a prescription")

for field in ("- Tracker-write preflight: comment `48c57a07` on SKL-79.",
              "- Estimate scale: fibonacci",
              "- Effective maximum: 5 (the 8-point rule still triggers at 8 or more)",
              "- Split: none",
              "- Tracker writes: product owner"):
    if field not in BODY:
        problems.append(f"header value absent: {field!r}")

for stage, expected_count in (("v1", 3), ("v2", 3), ("v3", 3), ("v4", 3), ("disc3", 3), ("chal", 1)):
    found = len(list((HERE / "outputs").glob(f"{stage}-*-output.txt")))
    if found != expected_count:
        problems.append(f"{stage}: expected {expected_count} captures, found {found}")

print(f"template fields checked: {len(FIELDS)}")
print(f"captures compared: {sum(1 for _ in (HERE / 'outputs').glob('*-output.txt'))}")
if problems:
    print("MISMATCHES:")
    for problem in problems:
        print(" -", problem)
    sys.exit(1)
print("RECORD MATCHES CAPTURES")
