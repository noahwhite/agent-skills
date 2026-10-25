# SKL-59 independent QA, 2026-10-25

The repository deployment surface is `main`; there is no hosted or visual surface.
The verified build is `702f53c9ab6fe4209fd4600ad2224c6e0431671a`, the squash merge of [implementation PR](https://github.com/noahwhite/agent-skills/pull/49) reviewed at `af623701e644509ab9c544d7b001f524e089204a`.
Verification used a clean detached checkout of that build, the pre-fix parent, original SKL-16 records, canceled tabletop SKL-71, and canceled precedent SKL-53.
The owner amendment (tracker comment `9426a923`) governs: post-reveal comparisons may name an already-estimated item's value, while pre-reveal values, this story's target value and adopting another voter's answer remain forbidden.
SKL-60 is related and in Backlog, and its replacement basis is explicitly sequenced after this fix rather than a blocking prerequisite.
The QA comment linking the sanitized assertion attachment (tracker comment `835ae633`) contains the exact outputs and quotations behind every row below.
No implementation or test file was changed, and the pre-existing `mutations.md` was left intact.

| Item | Verdict | Independently observed evidence |
|---|---|---|
| AC1, original grounds | Partial at QA; closed by owner ruling and replay, verified in QA round 2 | Replay rejects testability and verification grounds with restate-or-retract challenges, and rejects adoption of the inherited value as this story's target immediately; the original SM/EM note is only paraphrased, so its implication cannot be resolved under the amended post-reveal permission. |
| AC2, behavioural round | Not met at QA; closed by the 2026-10-25 remediation round below | SKL-71 is canceled, priority none, and has one pointing record, but no attached or quoted voter prompt bodies; the record names an earlier head and violates the final record rule by publishing its target value. |
| AC3, delivered text | Verified as amended | 33 independent text/structure checks pass, including rationale restrictions, reveal discipline, challenge duty, guardrail, template fields and unchanged recovery sentence. |
| AC4, adjacent cases and tests | Partial at QA; remediation submitted, awaiting QA re-verification | All named test edits and five unchanged test bodies are verified by AST comparison; table parsing, nine Step 4 process prefixes, full suite and vendor check pass; the AC2 behavioural precedent requirement remains incomplete. |
| DoD1, root cause | Verified | Parent diff exposes the former driver-set gap, absent sizing prohibition and challenge duty; the final text adds those rules and explains the story-surface limitation. |
| DoD2, original-case and live evidence | Partial at QA; remediation submitted, awaiting QA re-verification | Original-case replay is explicitly the substitute for the round that cannot be re-run; the fourth-ground ambiguity and AC2 behavioural gaps remain. |
| DoD3, regression protection | Partial at QA; remediation submitted, awaiting QA re-verification | All 34 documented regression mutations fail at their named assertions, the control passes, and two additional sentence removals fail; the live facilitator-duty evidence remains incomplete. |
| DoD4, independent review policy | Qualified at QA; resolved by the product owner's 2026-10-25 ruling recorded below | A separate reviewer/adjudicator record is COMMENTED at the exact reviewed head before merge, but accepts one valid Low without fixing it, so strict compliance with the loaded all-valid-findings-fixed policy is not established. |
| DoD5, non-obvious documentation | Verified | Step 3 item 4 distinguishes verification from breakage risk; the guardrail explains why new contexts cannot hide a value on the story surface. |
| DoD6, adjacent regressions | Verified | Full suite passes; independent assertions preserve recovery, re-refine's blind Step 3 re-run, the Split rule, point cap, item order and unchanged AC5 test bodies. |

The replay is the substitute: the original SKL-16 round cannot be re-run, and QA did not represent a text replay as a fresh voter ceremony.
Ground one, “checkability is uneven ... the versioning and notes semantics are pinned by phrase tests alone”, weighs verification or testability and must be restated or retracted.
Ground two, “the prior split already de-risked the slice; the earlier split consensus was also 3”, becomes an immediate event when used to adopt that inherited value as this story's answer; the de-risking clause alone is not enough to classify.
Ground three, “because the phrase-level contract test caps the verification risk”, weighs verification strength and must be challenged before consensus.
For ground four, the original SKL-16 pointing record (tracker comment `9c3110c9`) says only that the sizing note supplied an inherited value, and its process note (tracker comment `f283e4d8`) describes a comparable-story reference, so an original verbatim note or owner ruling is needed to establish a target implication.
The replay already posted on SKL-59 (tracker comment `25795ca4`) does state the substitution, but its fourth verdict depends on that unresolved implication.

The SKL-71 record (tracker comment `2c7e828f`) declares head `aafad08166d80ea77818278d82abc45bfc40b190`, and the final reviewed head changes operative challenge and record rules after that run.
Its Files section says “The four voter prompt files and the challenge lines are quoted above”, but contains no prompt bodies, and both SKL-71 and SKL-59 had zero attachments when inspected before this QA upload.
The record publishes a target value in both its sizing field and challenge, although the final template requires permanent elision outside numeric fields and retention in a raw session record cited by base name.
It also keeps the voided round as its primary Values block and places replacement values under Superseded values, reversing the final template's standing-versus-voided arrangement.
Quoted restatements, an unanswered coverage challenge, void/recovery and a surviving consensus are present, but the missing original prompts and outputs prevent independent confirmation of the blind contexts and stop chronology.
A compliant final-build tabletop with inspectable prompts, raw outputs, private raw target quotations and an appropriately elided posted record is owned by SKL-59's implementer and facilitator.
The product owner owns the original-note ambiguity and the review authority owns the accepted-valid-Low policy qualification.
These gaps belong to this story; no new bug or blocking story was created.

Exact sanitized local results follow.

```text
python3 <scratch>/check_text.py
TEXT/STRUCTURE CHECKS: 33 passed
uv run --locked pytest -q
531 passed in 63.25s (0:01:03)
uv run --locked python scripts/vendor_shared.py --check
exit=0; no shared/*.md change; refinement-record.md is hand-written
skills-ref validate skills/*/ (each directory, CI-pinned reference)
18 skills valid
OPENCODE_VERSION=2.1.2 bash scripts/smoke-opencode.sh
project-agents, project-opencode, project-claude,
global-agents, global-opencode, global-claude: each discovered all 18 skills
uv run --locked python scripts/leak_scan.py
exit=0; public patterns only; INCOMPLETE private coverage
uv run --locked python scripts/leak_scan.py --require-private
exit=2; leak scan INCOMPLETE: no private patterns loaded (LEAK_DENYLIST / LEAK_DENYLIST_FILE)
python3 <scratch>/reproduce_mutations.py
INDEPENDENT MUTATION RESULT: 34/34 rejected; 1/1 control passed; tracked documents and tests untouched
python3 <scratch>/extra_mutations.py
ADDITIONAL SENTENCE MUTATIONS: 2/2 rejected; originals untouched
```

Mutation probes copied the deployed documents into scratch and redirected the collected test module's document paths through a scratch-only collection hook; the tracked documents and test sources were never edited.
Each documented mutation applied only its quoted deletion or replacement, ran the documented named test with that hook, and checked the expected pytest failure and test name.
The added probes remove the reveal-definition sentence and the re-vote prompt's rationale-rule sentence; their named assertions fail with exit 1.
The [exact-build hosted CI](https://github.com/noahwhite/agent-skills/actions/runs/40155814393) reports success for both jobs, including the private scan unavailable locally.
The [implementation review of record](https://github.com/noahwhite/agent-skills/pull/49#pullrequestreview-5641230204) binds to the reviewed head and predates merge; its accepted Low is a lexical restatement guard that can miss a deliberately different paraphrase.
The weaker sizing sentence in `persona-scrum-master/SKILL.md:39` is an incidental, nonblocking follow-up already excluded by the owner's scope decision, with the product owner responsible and no follow-up issue yet.
The QA closing decision was to return SKL-59 to In Progress for its unmet behavioural evidence; the 2026-10-25 remediation round below answers that decision, and the story returns to In Deployment Review on the strength of it.

## Remediation round, 2026-10-25 (closes AC1 ground four, AC2, AC4, DoD2, DoD3; records DoD4)

The delivered skill text and its tests are unchanged by this round: QA verified AC3 as amended, and no QA finding required a text or test change.
Only evidence is added, under `docs/qa-evidence/SKL-59/tabletop/`.

### AC1 - the four grounds, all determinate

The substitution stands and is restated here: the original SKL-16 round cannot be re-run, so replaying the grounds its pointing record quotes is the substitute.

The original SM/EM sizing note is now settled. The product owner ruled on 2026-10-25 (tracker comment `4a2485a2`) that the inherited 3-point split pointing is this story's own inherited value, so naming it in the sizing context implies a target value for the story under estimate.
The note, as the ruling quotes it verbatim from the original SKL-16 pointing record:

> SM/EM sizing context, after all three values: no comparable story carries a recorded estimate; the only comparable number is the inherited 3-point split pointing; SKL-19 additionally regenerates 12 vendored copies, this story changes no `shared/*.md` file

| Ground | Verdict | Deciding delivered sentence | Required action |
|---|---|---|---|
| 1. Engineer one, value 5, "checkability is uneven ... the versioning and notes semantics are pinned by phrase tests alone" | Out of basis | Step 3 item 4: "verification strength, testability, coverage, the shape of the tests, a duration, effort or run-cost measure are out of basis" | Challenged under Step 4 item 1, then restated as a basis driver or retracted |
| 2. Engineer two, value 3, "the prior split already de-risked the slice; the earlier split consensus was also 3", with its re-vote resolved the same way | Out of basis | Step 3 item 4: "The rationale names no target value for this story ..."; Step 4 item 1: "a target value named or implied for this story, including one implied by a split status ... an anchoring event as soon as the facilitator sees it" | An anchoring event on sight: no restatement or retraction path; the round stops, the consensus and the affected votes are void and the independent vote is re-run |
| 3. Product owner re-vote, "because the phrase-level contract test caps the verification risk" | Out of basis | Step 3 item 4's verification-strength sentence, carried into the re-vote by Step 4 item 2 | Challenged under Step 4 item 2 before the consensus is recorded, then restated or retracted; a retraction records a replacement accepted set or no consensus |
| 4. The SM/EM sizing note naming the inherited 3-point split pointing | Out of basis, per the product owner's 2026-10-25 ruling | Step 3 item 7: "it must not name or imply a target value for this story, including one implied by a split status, and such a statement is an anchoring event under the Anchoring guardrail" | An anchoring event on sight with no repair path: the facilitator names it, the round stops, the consensus and the affected votes are void, and the independent vote is re-run blind in newly created contexts. The SM/EM's own restatement or retraction is recorded, and it does not cure the event |

Ground 4 is not treated as a permitted post-reveal comparison: the ruling establishes that the inherited value is this story's own inherited value, so naming it implies a target value for the story under estimate.

### AC2 - the behavioural round, inspectable

The whole run is a single ceremony on the fixture, and all of it is in `tabletop/`: twenty-five prompt files and their outputs, with provenance, the raw session record and the elided pointing record.

- `tabletop/README.md` - the run statement: the loaded commit `702f53c9ab6fe4209fd4600ad2224c6e0431671a`, the fixture SKL-72, the per-voter process and directory isolation, and the chronology of the ceremony's two rounds.
- `tabletop/raw-record.md` - the verbatim sizing comment (the target quotation), every value and every rationale, cited by base name from the posted record.
- `tabletop/pointing-record.md` - the record posted on SKL-72 as comment `c2121700` (superseding `7698722f`, `1de27e80` and `3c822ac7`), in the template's field order: the standing values in the values block, the voided values, the voided consensus positions and the replacement blind votes under the superseded line, each injected ground and each facilitator challenge quoted verbatim, and the round-two target value elided.
- `tabletop/prompts/` and `tabletop/outputs/` - the twenty-five prompt files and their twenty-five outputs.

The ceremony's rounds carry all three injected grounds: a product-owner rationale weighing verification strength and an engineer-one rationale weighing testability, both challenged and retracted, and an engineer-two coverage ground, challenged and deliberately left unretracted. Round one's sizing context was a permitted post-reveal comparison and its stopper was engineer two's unretracted ground; round two's sizing note named a target value for this story and stopped that round on sight before any discussion. Each voided the consensus position and the affected votes, and each was recovered by a blind re-run in newly created contexts that exclude the tainted discussion and sizing material.

### DoD4 - review-policy qualification

The product owner ruled on 2026-10-25 (tracker comment `4a2485a2`) that the accepted-Low disposition on PR #49 satisfies the review policy for this story: the reviewer and the adjudicator both ruled the Low non-blocking, the disposition and its reason are recorded on the pull request, and no fix is required. This round records that ruling and does not treat the Low as fixed.

### DoD3 - why the duty has no automated guard

Retained from the QA round and unchanged: a phrase test pins the challenge duty's text and the mutation evidence proves that pin, but a live round is the only evidence that a facilitator performs the challenge. The tabletop run above is that evidence.

## Round 3, 2026-10-25 - AC2 recovery evidence submitted for QA

QA round 2 (tracker comment `89a12de3`) left AC2 outstanding on two points: the live SKL-72 record did not reproduce the committed captures, and the rejected target-value rationales lacked the fresh blind recovery the rule requires.

- The record is corrected to the captures: SKL-72 comment `c2121700` carries the committed record verbatim.
- The missing recovery is supplied by a fresh run on the canceled priority-none fixture SKL-77, with one durable record (comment `264d0a47`), nine captured prompts and outputs in `tabletop/round3/`, an on-sight stop at a target value, and an independent blind re-run in newly created voter contexts.
- `tabletop/RECONCILIATION.md` records the deviation in the earlier handling and the artefacts that replace it; `tabletop/PROVENANCE.md` is extended to cover round 3.
- AC4, DoD2 and DoD3 depend on AC2 and are submitted with it for QA's re-verification; no skill text or test changed.
- What is not claimed here: the earlier SKL-72 handling of its rejected target-value rationales is recorded as a deviation, and the recovery mechanism is demonstrated on SKL-77 rather than retro-applied to SKL-72. QA decides whether that satisfies AC2.
