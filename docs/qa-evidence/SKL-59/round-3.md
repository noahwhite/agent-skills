# SKL-59 independent QA round 3, 2026-10-25

Environment: repository `main`, independently fetched and checked out at `ee605fcdf1d3355bb5da7152f06c87f2ed18da14`.
The primary checkout stayed untouched; its read-only `.git` prevented fetch and linked-worktree creation, so verification used an isolated HTTPS checkout under the session scratch directory.
Fixtures: original SKL-16; canceled priority-none precedent SKL-53; canceled priority-none tabletop fixtures SKL-72 and SKL-77, both instructing no implementation.
The owner amendment `9426a923` and owner ruling `4a2485a2` govern the basis, post-reveal comparisons, original sizing note and accepted Low.
SKL-60 is Backlog and explicitly sequenced after this story; it is related, not a blocking dependency.
No implementation, test or earlier evidence file was edited.
The sanitized raw assertions are attached to SKL-59; the scratch probes are not repository artifacts.

| Item | Verdict | Independently reproduced evidence |
|---|---|---|
| AC1 | Verified | Four original grounds replayed below; the issue already carries the substitution statement, verdicts and owner ruling. |
| AC2 | Not met | SKL-72 authoritative record `c2121700` and SKL-77 authoritative record `264d0a47` match the committed record bodies exactly; challenges, injected grounds, fresh blind recovery prompts and basis-only surviving rationales are inspectable, but SKL-77 explicitly skips the required Step 4 discussion after recovery and has six historical pointing-record posts against the one-record precedent. |
| AC3 | Verified as amended | 41 delivered text/structure and adjacent assertions pass; basis by reference, off-basis list, verification/breakage distinction, three narrowed value rules, challenge duty, no-repair exceptions, guardrail and template are checked; parsed permitted column has 11 cells and permits post-reveal comparisons under the amendment. |
| AC4 | Partial | Three named tests changed in place and are named in the implementation PR; five adjacent ASTs are unchanged; no pre-existing test function was deleted; nine Step 4 process items/order, dependency row, recovery, suite and vendor no-op pass; compliant AC2 precedent remains outstanding. |
| DoD1 | Verified | Pre-fix parent exposes the unconstrained driver sentence, permitted endpoint comparison and missing challenge duty; delivered text closes these and explains the story-surface limitation. |
| DoD2 | Partial | Original-case substitution and links are established; compliant behavioural evidence remains incomplete through AC2. |
| DoD3 | Partial | All 34 documented regression mutations fail at the named assertions and the control passes; the live-duty automated-guard limitation is explicitly documented; AC2 remains incomplete. |
| DoD4 | Verified with owner ruling | Exact-head COMMENTED independent reviewer/adjudicator records precede all three implementation/remediation merges; the owner's explicit accepted-Low ruling applies, and the Low is not represented as fixed. |
| DoD5 | Verified | Exact text distinguishes how well behaviour is checked from what can silently change and explains why fresh contexts cannot exclude a recorded story-surface value. |
| DoD6 | Verified | 531 tests pass; five adjacent ASTs, original recovery sentence and entire Split rule are unchanged; re-refine's fresh blind Step 3, point cap and 8-point trigger are asserted. |

## Original-case substitute replay

The original SKL-16 round cannot be re-run; this replay of its recorded grounds is explicitly the substitute, not a new voter ceremony.
Engineer one's “checkability is uneven ... the versioning and notes semantics are pinned by phrase tests alone” weighs verification/testability and test shape: challenge under Step 4 item 1, restate as a basis driver or retract.
Engineer two's “the prior split already de-risked the slice; the earlier split consensus was also 3”, used as this story's answer, is an immediate target-value event: stop, void and re-run Step 3 blind; the de-risking clause alone does not establish that verdict.
The PO's “because the phrase-level contract test caps the verification risk” weighs verification strength: challenge before consensus under Step 4 item 2, restate or retract and supply a replacement accepted set or no consensus.
The original SM/EM note says “the only comparable number is the inherited 3-point split pointing”; the owner rules this is this story's inherited target, so it is out of basis and an immediate anchoring event requiring stop, void and fresh blind recovery, rather than a permitted comparison.
The delivered deciding sentence is “The rationale names drivers the pointing basis admits and nothing else, so verification strength, testability, coverage, the shape of the tests, a duration, effort or run-cost measure are out of basis.”
The immediate-event rule covers “a target value named or implied for this story by any participant” with “no challenge, restatement or retraction path”.

## Behavioural evidence and remaining requirement

The corrected SKL-72 record contains all three captured final re-vote rationales and the exact engineer-one re-challenge, resolving the prior drift finding.
Its captured verification and testability challenges end in retractions; the engineer-one relabelled restatement is rejected and re-challenged; the coverage ground remains unretracted and stops the round.
SKL-72 has 25 matching prompt/output pairs, including 18 voting prompts carrying the verbatim basis and complete rationale rule.
SKL-77 has 12 matching prompt/output pairs, including nine voting prompts carrying that same basis and rule and three no-consensus path votes.
Both sets of blind recovery prompts exclude the injected grounds, target quotations, tainted discussion and sizing material.
The declared loaded skill versions `702f53c9ab6fe4209fd4600ad2224c6e0431671a` and `662c84b21e6aea973b41f2a2981b30b18af4118f` are byte-identical to the skill on the tested build.
SKL-77's standing accepted sets `{2}`, `{1}` and `{1, 2}` have no intersection; its path votes intersect on re-refine, matching the record.
The record checker passes the baseline, and six independent scratch mutations of value, rationale, target elision, path capture, discussion claim and consensus each fail.
That demonstrates consistency; it does not prove process compliance.

The delivered Step 4 item 1 requires “Hold one discussion round that names only the high and the low.”
SKL-77's authoritative record instead says “Discussion: none; the round stopped on sight at the target value and no discussion was opened, before or after the re-run.”
Its re-vote prompts corroborate “No discussion was held” and proceed directly from the blind re-run to the accepted-set vote.
Stopping the tainted round is correct; skipping the discussion in the fresh recovered round does not follow Step 4 or the SKL-53 precedent.
The precedent has one pointing record; SKL-72 has four historical pointing records and SKL-77 has six, even though each now clearly identifies one authoritative record.
The reconciliation acknowledges repeated posts as a deviation; neither that acknowledgement nor a green record-consistency check establishes the requested one-record run.
The existing SKL-72 target-value re-vote handling remains explicitly labelled a deviation in `tabletop/RECONCILIATION.md`; it is not retroactively repaired by the independent SKL-77 run.

To satisfy AC2 and the dependent AC4/DoD2/DoD3 items, the engineer/facilitator supplies a compliant tabletop run or continuation that records the required fresh high/low discussion after recovery and the ensuing re-vote, retaining every event and capture; the product owner supplies the authoritative tracker record and addresses the explicit one-record precedent, preferably on a fresh canceled priority-none fixture with one final pointing-record post.
The run must preserve the verification/testability challenge, unretracted-ground void, SM/EM target-value stop, fresh blind recovery, basis-only surviving rationales and exact capture-to-record correspondence already required by AC2.
No skill-text fix is established by this round, and QA makes none.
The planned final state after evidence publication is In Progress for unmet acceptance evidence, with those four boxes left unchecked; while the evidence PR awaits external review and merge, QA stays in flight at In Deployment Review.

## Reproduced output

Local tool caches were redirected under the scratch directory after read-only home-cache failures; no shared configuration was changed.

```text
git rev-parse HEAD origin/main
ee605fcdf1d3355bb5da7152f06c87f2ed18da14
ee605fcdf1d3355bb5da7152f06c87f2ed18da14
GitHub commit.verification.verified: true
GitHub exact-build checks: discovery completed success; checks completed success
uv run --locked pytest -q
531 passed in 64.50s (0:01:04)
uv run --locked python scripts/vendor_shared.py --check
vendor check exit=0
shared/*.md changes since pre-fix parent: 0
skills-ref validate skills/*/ (each directory, CI-pinned reference)
18 valid skills
OPENCODE_VERSION=2.1.2 bash scripts/smoke-opencode.sh
project-agents, project-opencode, project-claude,
global-agents, global-opencode, global-claude: all 18 discovered in each
uv run --locked python scripts/leak_scan.py
public scan exit=0; INCOMPLETE private coverage
uv run --locked python scripts/leak_scan.py --require-private
required-private scan exit=2
leak scan INCOMPLETE: no private patterns loaded (LEAK_DENYLIST / LEAK_DENYLIST_FILE)
Independent mutation reproduction:
34/34 guarded failures; 1/1 control passed; tracked documents/tests untouched
Independent record drift probes:
6/6 rejected; control passed
template fields checked: 17
captures compared: 9 (standing, re-vote, voided)
RECORD MATCHES CAPTURES
```

The [exact-build CI](https://github.com/noahwhite/agent-skills/actions/runs/40181699763) succeeded, including the required private leak scan unavailable locally.
The exact-head review records precede merge for [implementation](https://github.com/noahwhite/agent-skills/pull/49#pullrequestreview-5641230204), [first remediation](https://github.com/noahwhite/agent-skills/pull/51#pullrequestreview-5642074087) and [latest remediation](https://github.com/noahwhite/agent-skills/pull/53#pullrequestreview-5642556211).
Incidental nonblocking findings: the weaker `persona-scrum-master/SKILL.md:39` sizing rule remains the scoped-out product-owner follow-up; the new tabletop metadata says nine prompt/output pairs although there are twelve including path votes, and some index prose names a superseded durable-comment id.
These incidental metadata defects do not independently block this story; the outstanding AC2 process and precedent requirements do.
No screenshot or hosted evidence page applies because this story has no visual surface.
