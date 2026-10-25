# SKL-59 independent QA round 4, 2026-10-25

The environment is the repository deployment surface `main`, verified at `52280a5f5bb11f6b0a193d9ede9136fc9ffe09f7` from a fresh fetch of `origin/main`.
There is no hosted or visual surface; the evidence is sanitized assertion output and quoted text.
The checkout is a detached worktree of an independent scratch clone because the source checkout's `.git` is read-only; the source working tree was not modified.
Fixtures inspected through the Linear CLI: original SKL-16, precedent SKL-53, and canceled priority-none SKL-71, SKL-72, SKL-77 and SKL-78.
No fixture implementation, new ceremony or reviewer process was launched by QA.
The owner amendment `9426a923` and ruling `4a2485a2` govern: post-reveal comparison with an already-estimated item remains permitted, the inherited original value is this story's target, and the accepted Low satisfies DoD4 without being fixed.
SKL-60 and SKL-75 are related and in Backlog, SKL-51 is Done, and the relation graph contains no blocking edge.
SKL-60's replacement basis is explicitly sequenced later, so this round verifies the delivered basis by reference rather than demanding its future replacement.

| Item | Verdict | Independently observed evidence |
|---|---|---|
| AC1 | Verified | The four original grounds were replayed against the delivered rule; the original record and process note corroborate the event, the explicit substitution is posted in SKL-59 comment `25795ca4`, and ruling `4a2485a2` resolves the original sizing note. |
| AC2 | Not met | SKL-78 has one matching record and a captured discussion, but no SM/EM sizing note, no unretracted-ground stop, and its discussion response names the middle value; the older fixtures cannot establish the requested compliant one-record run. |
| AC3 | Verified as amended | Independent assertions cover rationale restrictions, reveal/target rules, challenge and repair duties, recorded-value limitation, preserved recovery, parsed permitted cells and challenge template. |
| AC4 | Partial | Three changed tests are named in the implementation PR, five adjacent test ASTs and nine Step 4 process prefixes are unchanged, table parsing and recovery pass, 531 tests and vendor check pass; its AC2 precedent clause remains unmet. |
| DoD1 | Verified | Pre-fix comparison independently exposes the unconstrained driver set, endpoint sizing permission, absent explicit challenge duty and story-surface limitation addressed by the final text. |
| DoD2 | Partial | The original-case replay is explicitly the substitute and is linked on SKL-59; compliant behavioural evidence remains incomplete through AC2. |
| DoD3 | Partial | 34 documented mutations fail at their named tests, a control passes, and two additional sentence removals fail at their actual guarding tests; the live-duty limitation is stated, but AC2 remains incomplete. |
| DoD4 | Verified with owner ruling | GitHub COMMENTED review records bind to the exact final heads before each implementation/remediation merge; the accepted Low is recorded and allowed by ruling `4a2485a2`, not claimed fixed. |
| DoD5 | Verified | Step 3 explains verification versus breakage and interacting constraints, and the guardrail explains why fresh contexts cannot hide a value on the story surface. |
| DoD6 | Verified | Five adjacent ASTs, original recovery sentence, blind re-refine Step 3 re-run and Split rule are preserved; cap/eight-point assertions and the full suite pass. |

## Original-case replay

The SKL-16 round cannot be re-run; replaying its recorded grounds is the substitute, not a new ceremony.
Engineer one's “checkability is uneven ... the versioning and notes semantics are pinned by phrase tests alone” weighs verification/testability and must be challenged and restated as a basis driver or retracted.
Engineer two's “the prior split already de-risked the slice; the earlier split consensus was also 3” adopts the inherited answer; the prior-number clause is an immediate target-value event, requiring stop, void and fresh blind recovery, while the de-risking clause alone is not determinative.
The PO's “because the phrase-level contract test caps the verification risk” weighs verification and must be challenged before consensus, then restated or retracted with a replacement accepted set or no consensus.
The original SM/EM note says “the only comparable number is the inherited 3-point split pointing”; under the owner's explicit ruling this is the story's own target, so it requires immediate stop, void and blind recovery, and a withdrawal does not cure the event.
The deciding delivered rule is “verification strength, testability, coverage, the shape of the tests, a duration, effort or run-cost measure are out of basis”, together with the no-target rule and immediate-event recovery.

## AC2 deciding observations

The new SKL-78 authoritative comment `e0bcb6f8` equals the committed record's template body, and there is exactly one pointing-record post, matching the SKL-53 count.
The new captures state loaded build `ee605fcdf1d3355bb5da7152f06c87f2ed18da14`; git comparison confirms the skill, reference and tests are byte-identical between that build, implementation `702f53c` and the build under test.
Nine voting prompts carry the exact delivered basis and full rationale rule, and all thirteen prompt/output pairs are inspectable.
The new run establishes a target-value stop, fresh blind input prompts, a captured high/low discussion, a coverage challenge and retraction, accepted sets `{2, 3}`, `{2}`, `{2}`, and derived consensus 2.
Its record says, verbatim:

> SM/EM sizing context, after all three values: none. The round stopped on a recorded rationale before any sizing context was offered, and none was offered after the re-run.

The sole captured challenge response is:

```text
OUTCOME: retracted
RATIONALE:
```

Consequently this run never injects the required SM/EM prior/inherited-value sizing note and never leaves a third ground unretracted to cause the required stop; the voter target event exercises a different immediate-stop branch.
Earlier SKL-72 evidence contains those scenarios, but has four pointing-record posts and explicitly documents a target-value recovery deviation; SKL-77 has six posts and no required discussion.
Neither earlier record nor the new run demonstrates all required branches in the requested compliant one-record ceremony.
The owner amendment narrows which values are forbidden; this finding does not demand a ban on a permitted post-reveal comparison.

The delivered Step 4 instruction is “Hold one discussion round that names only the high and the low.”
In `tabletop/round4/prompts/disc-po-prompt.txt`, the high is 5, low is 2, and the prompt additionally supplies `VALUE: 3`.
The corresponding captured response says:

> REMARK: The byte-identical dry-run output is the behaviour that silently breaks if the size edge case is mishandled, so my 3 hinges on that risk being absorbed without failing the run.

Thus the discussion names a middle value despite the record's claim to name only the high and low.
The record checker passes that actual prompt/output, although it rejects an explicit “middle estimate is 3” probe; a passing consistency checker does not establish this process requirement.

The engineer/facilitator owns a compliant captured run or continuation preserving every AC2 branch, including the SM/EM sizing event and an unretracted-ground void with fresh blind recovery, followed by a discussion that names only its endpoints and a basis-only re-vote.
The product owner owns its matching authoritative tracker record, retaining the one-record precedent and the raw quotations and capture provenance.
Keep remediation on SKL-59; no new bug or blocker was filed.

## Reproduced checks

Commands ran from the exact-build checkout with caches and runtime data redirected beneath the session scratch directory where the sandbox made home paths read-only.
Scratch-only collection hooks redirected the existing test module's document paths to copied documents for mutations; no merged document, test or earlier evidence was modified.
All thirty-four documented mutations failed with exit 1 at their named assertions, and the blank-line control passed with exit 0.
Deleting the reveal-definition sentence failed `test_step_three_defines_the_reveal`.
Deleting the re-vote prompt's rationale-rule sentence passed the older basis-only test, as expected for that test's scope, and failed its actual guarding test `test_step_four_re_vote_prompt_carries_the_rationale_rule` at line 775.
The initial scratch runner selected the basis-only test for the latter extra probe; QA corrected that test selection rather than claiming that it guarded the new sentence.
The facilitator-duty limitation remains explicit: a phrase test pins the instruction, but only behavioural evidence shows a facilitator performing it.

```text
python3 <scratch>/verify_contract.py
TEXT/STRUCTURE/REVIEW CHECKS: 49 passed
uv run --locked pytest -q
531 passed in 64.49s (0:01:04)
uv run --locked python scripts/vendor_shared.py --check
exit=0; no shared source changed; reference is hand-written
skills-ref validate skills/*/ (each directory; CI-pinned reference)
18 skills valid
OPENCODE_VERSION=2.1.2 bash scripts/smoke-opencode.sh
project-agents, project-opencode, project-claude,
global-agents, global-opencode, global-claude: each discovered all 18 skills
uv run --locked python scripts/leak_scan.py
exit=0; no public-pattern matches; private coverage INCOMPLETE
uv run --locked python scripts/leak_scan.py --require-private
exit=2; leak scan INCOMPLETE: no private patterns loaded (LEAK_DENYLIST / LEAK_DENYLIST_FILE)
python3 <scratch>/probe_records.py
RECORD DRIFT PROBES: 8/8 rejected, 1/1 control passed
SKL-78: state=Canceled; priority=0; pointing-record posts=1
PASS: SKL-78 authoritative tracker record equals committed template body
```

The round-4 checker compared seventeen template fields and thirteen captures and printed `RECORD MATCHES CAPTURES`.
Independent drift probes rejected a changed standing value, wrong high, named middle value, blank anchor, leaked target, fabricated challenge, misattributed remark and extra off-basis recorded rationale.
All 25 older pairs and 12 round-3 pairs were also read; respectively 18 and nine voting prompts contain the exact basis and full rationale rule.
The authoritative SKL-72 and SKL-77 tracker bodies also match their committed template bodies.
GitHub independently reports the build signature verified and both check runs completed with conclusion success in [exact-build CI](https://github.com/noahwhite/agent-skills/actions/runs/40187170373), including the private scan unavailable locally.
Exact-head independent review records precede the merges of [implementation](https://github.com/noahwhite/agent-skills/pull/49), [first remediation](https://github.com/noahwhite/agent-skills/pull/51), [second remediation](https://github.com/noahwhite/agent-skills/pull/53) and [latest remediation](https://github.com/noahwhite/agent-skills/pull/55).

Incidental nonblocking defects: provenance/index prose still says nine or ten captures/processes where inventories show twelve or thirteen, and some historical supersession lists omit later record ids; the evidence author owns metadata cleanup.
The scoped-out weaker sizing sentence in `persona-scrum-master` remains the product owner's follow-up candidate, with no follow-up issue yet.
The record checker's missed `VALUE: 3`/“my 3” shape contributes to AC2's evidence gap but is not a separate implementation finding against the delivered skill.

## Publication and status handoff

The sanitized raw assertion output is attached to SKL-59 and its QA comment carries these per-item verdicts.
This round adds only `round-4.md`; every earlier evidence file and implementation/test file remains unchanged.
The evidence PR is deliberately left unmerged for the external exact-head review and merge required by the session brief; no nested reviewer was attempted.
Until evidence publication completes, QA is in flight and SKL-59 remains In Deployment Review, with all existing boxes preserved.
Once this evidence is merged, the closing decision is In Progress for unmet AC2, with AC2/AC4/DoD2/DoD3 unchecked and the already verified AC1/AC3/DoD1/DoD4/DoD5/DoD6 retained.
QA will then add the merged evidence citation and dated deployment-review note and read the state and boxes back.
