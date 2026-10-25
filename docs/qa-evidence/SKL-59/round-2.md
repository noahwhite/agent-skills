# SKL-59 independent QA round 2, 2026-10-25

Environment: repository `main`, build `662c84b21e6aea973b41f2a2981b30b18af4118f`.
An isolated HTTPS clone fetched `origin/main` and checked out that exact commit; both refs matched before verification.
The primary checkout was clean and remained untouched; its read-only `.git` prevented fetch and linked-worktree creation, so the clone was used instead.
GitHub reported `verified: true`, with `checks` and `discovery` completed successfully at the exact build in [CI run](https://github.com/noahwhite/agent-skills/actions/runs/40172974330).
Fixtures: original SKL-16 records, canceled priority-none SKL-53 precedent and canceled priority-none SKL-72 tabletop.
All 17 story comments and both relation directions were read; SKL-51 is Done, SKL-60 is Backlog and related, with the owner explicitly sequencing it after this story.
The owner amendment `9426a923` governs the narrowed value restrictions and basis by reference; owner ruling `4a2485a2` resolves original ground four and the accepted-Low review-policy qualification.
This round adds only this file and leaves all earlier evidence, implementation and tests unchanged.
Sanitized raw assertion output is attached to SKL-59 as “SKL-59 round 2 independent assertions at 662c84b2”.

| Item | Verdict | Independently observed evidence |
|---|---|---|
| AC1: original failing grounds | Verified | The original SKL-16 sizing field and the owner ruling establish ground four as this story's inherited target; the replay explicitly substitutes for the original round that cannot be re-run, and all four out-of-basis verdicts and required actions are recorded on SKL-59. |
| AC2: behavioural tabletop | Not met | Twenty-five paired prompts/outputs exist, 18 voting prompts carry the exact basis and full rationale rule, and the initial challenge/void/recovery branches are inspectable, but the live durable SKL-72 record disagrees with the captures and the rejected target-value re-vote has no recorded blind Step 3 recovery. |
| AC3: delivered text | Verified under owner amendment | Independent assertions cover exclusive basis drivers, all named off-basis grounds, verification versus breakage, the three narrowed value restrictions, challenge duty and exceptions, anchoring, record fields, the parsed permitted table and word-for-word original recovery. |
| AC4: adjacent tests and precedent | Partial | The three required tests changed in place and their names appear in the implementation PR; five required adjacent test ASTs are identical to the pre-fix parent; no existing test function was deleted; nine Step 4 process openings/order, final dependency row, full suite and vendor no-op pass; the AC2 precedent gap remains. |
| DoD1: root cause | Verified | Parent versus delivered text confirms the driver-set gap, missing target-value restriction and challenge duty; the final text explains the story-surface limitation. |
| DoD2: original case plus live evidence | Partial | Original substitute replay is verified and linked on the story, but AC2 does not yet establish a compliant complete live run. |
| DoD3: regression protection | Partial | All 34 documented mutations independently fail at their named tests and the control passes using scratch document copies; the record correctly explains why a phrase test cannot prove a facilitator performed its duty; AC2 leaves that behavioural proof incomplete. |
| DoD4: independent review | Verified with explicit owner ruling | Exact-head COMMENTED reviewer/adjudicator records preceded both implementation and remediation merges; the owner explicitly accepts the implementation's nonblocking Low for this story, and QA does not represent it as fixed. |
| DoD5: non-obvious documentation | Verified | Step 3 item 4 distinguishes how well behaviour is checked from what can silently change; the guardrail explains why new contexts cannot exclude a value on the story surface. |
| DoD6: adjacent regressions | Verified | 531 tests pass; the five named adjacent test ASTs, original recovery sentence and entire Split rule remain unchanged; assertions cover blind Step 3 after re-refine, cap/8-point trigger and nine ordered Step 4 items. |

## Deciding behavioural evidence

The repository claims `tabletop/pointing-record.md` reproduces the durable SKL-72 comment `7698722f` unchanged.
Reading that comment from Linear and comparing it with the captured outputs gives:

```text
FIXTURE RATIONALE MATCH: rv-po repo=True live=False
FIXTURE RATIONALE MATCH: rv-e1 repo=True live=False
FIXTURE RATIONALE MATCH: rv-e2 repo=True live=False
EXACT RECHALLENGE: repo=True live=False
LIVE TRACKER WRITES: - Tracker writes: facilitator, for a disposable fixture with no product-owner voter.
```

For example, `outputs/rv-po-output.txt` and the repository record say:

> The flag depends on comparing candidate content against git's last-committed state, an interacting constraint, and the default dry-run path must stay byte-identical, a real risk of silently breaking existing behaviour.

The live durable comment instead says:

> Filtering on 'differs from the last committed state' adds an interacting constraint between the dry run and repository state, and AC2's byte-identical requirement is a real risk of breaking existing behaviour the change must preserve.

The live re-challenge is a shorter paraphrase, while AC2 requires the facilitator's challenge verbatim.
The live tracker-writes field also contradicts the product-owner voter present throughout the captured run.
Superseded comments remain visible, but this finding concerns the comment explicitly designated durable, not the existence of historical corrections.

The retained rejected round-two PO and engineer-two re-vote rationales each say:

> so it sizes at 2 rather than 3.

These name a target value in the rationale, outside the accepted-set field.
The delivered guardrail applies to a target named or implied “by any participant” and requires an immediate anchoring event “with no challenge, restatement or retraction path”.
Its unchanged recovery says:

> On anchoring: stop the round, record the comment verbatim, void the consensus and any vote recorded after the anchor, and re-run the independent vote with newly created voter contexts that exclude the tainted discussion and sizing comment. Never reuse the sessions that saw the anchor. Record the recovery.

`tabletop/PROVENANCE.md` instead records:

> The facilitator rejected them and re-ran the re-vote with the rationale rule restated in the prompt.

The retained replacement files are accepted-set re-votes, not fresh blind `VALUE` outputs after this additional event.
Neither the posted pointing record nor the raw record documents that additional event followed by the required fresh Step 3 vote.
The earlier `r3-*` blind votes precede this rejected re-vote and cannot establish its recovery.
The replacement rationales being within basis does not establish that the required recovery occurred.

To satisfy AC2, the engineer/facilitator must supply a compliant continuation or fresh run, retaining rejected captures, recording every immediate target event and its fresh blind Step 3 recovery, then posting one authoritative final record whose rationales, exact challenge text, standing/voided values and tracker-author field agree with the captures.
The product owner owns the authoritative tracker record under the delivered role rules, and QA re-verifies the result.
AC4 and DoD2/DoD3 remain unticked through this same behavioural gap; no new bug or blocking relation is needed.

## Original-case substitute replay

The original SKL-16 round cannot be re-run; replaying its recorded grounds is explicitly the substitute, not a new live ceremony.
Engineer one's “checkability is uneven ... the versioning and notes semantics are pinned by phrase tests alone” weighs testability or verification strength and is challenged with restate-or-retract under Step 4 item 1.
Engineer two's “the prior split already de-risked the slice; the earlier split consensus was also 3”, when adopted as this story's answer, is an immediate target-value anchoring event requiring stop, void and a fresh blind vote.
The PO's “because the phrase-level contract test caps the verification risk” is verification strength, challenged under Step 4 item 2 before consensus, with a replacement set or no consensus on retraction.
The original SM/EM note names “the only comparable number is the inherited 3-point split pointing”; the owner's ruling makes that this story's inherited target, an immediate event under Step 3 item 7, not a permitted post-reveal comparison.
This round records each required challenge/action on SKL-59; the previous indeterminacy of ground four is resolved by the owner ruling.

## Reproduced checks

All commands ran in the isolated checkout, with writable tool caches redirected into the session scratch directory after read-only home-cache errors.

```text
python3 <scratch>/check_build.py
65 PASS assertions; three live rationale mismatches and the exact re-challenge mismatch reported
uv run --locked pytest -q
531 passed in 63.40s (0:01:03)
uv run --locked python scripts/vendor_shared.py --check
exit=0; no shared/ change in the implementation; reference is hand-written
python3 <scratch>/mutations.py
INDEPENDENT MUTATION RESULT: 34/34 rejected; 1/1 control passed; tracked documents and tests untouched
skills-ref validate skills/*/ (each directory, CI-pinned revision)
18 skills valid
OPENCODE_VERSION=2.1.2 bash scripts/smoke-opencode.sh
project-agents, project-opencode, project-claude,
global-agents, global-opencode, global-claude: each discovered all 18 skills
uv run --locked python scripts/leak_scan.py
exit=0; public coverage only
uv run --locked python scripts/leak_scan.py --require-private
exit=2; leak scan INCOMPLETE: no private patterns loaded (LEAK_DENYLIST / LEAK_DENYLIST_FILE)
```

Mutation probes parsed each documented literal independently, changed one scratch copy, redirected the collected test module's document paths through a scratch plugin, and observed the named pytest failure; the control alone passed.
No tracked document or test was mutated.
The implementation review `5641230204` is COMMENTED at `af623701e644509ab9c544d7b001f524e089204a`, submitted `2026-10-25T02:47:34Z` before merge `02:47:48Z`.
The remediation delta review `5642074087` is COMMENTED at `587089e12362206151f8e64f819064c04508d7a8`, submitted `2026-10-25T07:29:39Z` before merge `07:29:47Z`, building on its full review.
Each record names a separate reviewer and adjudicator, and its first-line SHA and commit ID match the PR's final head.

Incidental nonblocking issue: `persona-scrum-master/SKILL.md:39` retains the weaker sizing sentence already excluded by the scope decision; the product owner owns that follow-up candidate.
Closing decision: In Progress for unmet AC2, with only AC1, AC3 and DoD1/DoD4/DoD5/DoD6 established.
This evidence PR is intentionally left unmerged for the orchestrator's external review of record and guarded merge; the repository evidence path is cited in Linear only after that merge.
