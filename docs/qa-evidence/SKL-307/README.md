# SKL-307 QA evidence

## QA round 1

Date: 2026-11-15 UTC, independent QA round 1.
Target: `main` at `31ee7ba2a85b2688f31caf0b2823b0b6c27fce13`, the squash merge of PR 260, whose reviewed head is `a4b6f5a21abf9b93a44a6b53e0560984f8104b77`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
Path: `no-deployment`, selected by `select-path.py` over the repository profile (`environments: []`), so no environment or build SHA applies.
Fixtures: none.
Blockers SKL-304 (`a559d43`), SKL-305 (`581de04`) and SKL-306 (`d282a5d`, `a7aa8f6`) are Done, and their merges are ancestors of the target.
The raw output is attached to SKL-307 as "SKL-307 QA round 1 probe at target 31ee7ba", "SKL-307 QA round 1 probe at parent 3eb4c5a" and "SKL-307 QA round 1 path, target and DoD output"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC9b: named sentence changes | Verified | The PR 260 body's "AC9b sentences" section names the guardrail factual-reference sentence, the closing fresh-contexts paragraph and the four `shared/linear.md` sentences after the slice-brief ledger sentence, and each named wording is present at the target. |
| AC11: prior-round context carry-forward | Verified | The four `shared/linear.md` sentences, the Split rule, Records, the Slice brief template and the pointing record `Slice brief:` line carry every clause; the tabletop slice brief below shows the parent value, its three voter values, the ledger and the ancestor rationales, and no same-round value. |
| AC12: Anchoring guardrail amendment | Verified | Every clause is in the Anchoring guardrail, the Step 3 rationale rule and the Split rule; the tabletop classifies both cases as the criterion requires; the owner's statement is recorded before the story left Ready To Work. |
| DoD: all acceptance criteria met | Verified | AC9b, AC11 and AC12. |
| DoD: tests written and passing | Verified | SKL-307 pins in `tests/test_shared_linear.py` and `tests/test_story_refinement.py`; CI `ci` passed on the reviewed head (run 43656244456) and on `main` (run 43657457807, 2410 passed); QA ran no local pytest. |
| DoD: independently reviewed | Verified | Details below. |
| DoD: docs updated | Verified | `SKILL.md`, `references/refinement-record.md`, `shared/linear.md` and its 18 vendored copies; `scripts/vendor_shared.py --check` exits 0, and `SKILL.md` is 496 lines. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed: the run is on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | CI `checks` (tests, leak scan, skills spec validation) and `discovery` passed on `main` at the target. |

Details:

- Probe:
  - A read-only probe asserted each AC9b, AC11 and AC12 clause in the committed text at the target, and all 51 assertions passed.
  - The same probe at the parent `3eb4c5a` passed 16 of 51, and those 16 are the PR body reads, text that predates the story and the probe's own tabletop brief, so the file-bound assertions are not vacuous.
- AC11 tabletop, the slice B brief of split round 1 filled from the Slice brief worked example:
  - Parent: recorded value 13, with the three standing voter values 13, 13, 13.
  - Per-parent bound: the fixed sentence naming 13, stated as a bound and not a value to score.
  - Ledger: auth 3 (owner B), schema 2 (owner A), vendor API 2 (owner X, priced in no slice), migration 1 (owner A), total 8 beside 13, with the saturation note.
  - Ancestor rationales: the three whole-story rationales, each summing to 13.
  - No value or rationale of slice A or C and no other slice B vote appears, and no field of the template asks for a same-round value.
- AC12 tabletop:
  - The bound sentence naming 13 in the slice B brief is a factual reference to an already-recorded item under the extended factual-reference sentence, so no anchoring event occurs and the round continues.
  - An SM/EM telling the slice B voters to aim for 5 before the reveal prescribes a target for the slice, an anchoring event under the unchanged slice prohibitions, so the round is voided and re-runs in newly created voter contexts.
  - The owner's statement that the amendment needs no further approval was posted at 22:41:23Z on 2026-11-14, before the move from Ready To Work at 22:41:29Z.
- DoD, independently reviewed:
  - Review 5908029786 on PR 260 is `COMMENTED` at `4b1a8a696ad7f7020e43aea011ed716d149f0294`; its one valid finding was fixed in `a4b6f5a`.
  - Review 5908077790 is `COMMENTED`, and its `commit_id` and first line name the merged head `a4b6f5a21abf9b93a44a6b53e0560984f8104b77`.
  - It was submitted at 00:17:25Z, before the 00:17:43Z merge.
  - Both name GPT-6.1 Sol (`gpt-6.1-sol`) as reviewer and DeepSeek V4.1 Flash (`deepseek/deepseek-flash`) as adjudicator, the seats in `profile.review` at the target.
- Incidental, low:
  - `shared/linear.md` says the parent's recorded value with its round's voter values appears only on the template's Parent line, while the template's fixed bound sentence also names the parent's value.
  - The Step 3 Stop in `SKILL.md` keys the early sizing-comment stop to the slice's own three values, while the Split rule defers a slice's sizing comments until every slice of the round has its three values.
  - The Anchoring guardrail's precedence covers both, so neither affects an acceptance criterion.

Closing decision: Done, once this evidence merges.

## QA round 1 after the reopen

Date: 2026-11-15 UTC, independent QA round 1 after the story was reopened for four incidental defects.
Target: `main` at `42bd765df408a6fa2dbb159ab8cd381ec3967d60`, the squash merge of PR 263, whose reviewed head is `3d9721308661efdea36e0685cafb5dbce8db85c3`.
`git merge-base --is-ancestor` confirmed the target on `origin/main` and the original merge `31ee7ba` as its ancestor.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Fixtures: none.
Blockers SKL-304, SKL-305 and SKL-306 are Done, and their merges are ancestors of the target.
The raw output is attached to SKL-307 as "SKL-307 QA reopen round 1 probe at target 42bd765", "SKL-307 QA reopen round 1 probe at pre-fix 31ee7ba" and "SKL-307 QA reopen round 1 path, target and DoD output"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| Reopen defect 1: Parent-line sentence in `shared/linear.md` | Resolved | The sentence now says the parent's recorded value paired with its round's voter values appears only on the Parent line, and the parent's value appears as a bound only in the fixed sentence, matching the template's `Parent:` and `Per-parent bound:` lines; the 18 vendored copies match. |
| Reopen defect 2: Step 3 Stop timing | Resolved | The Step 3 `Stop:` now also stops a sizing comment made in a slice round before every slice of the round has its three values, as the Split rule defers; items 5 to 7 and the guardrail's opening line carry the same clause. |
| Reopen defect 3: "after all three values" in `refinement-record.md` | Resolved | The probe finds no line saying "after all three values" without the slice-round deferral, against three such lines at `31ee7ba`. |
| Reopen defect 4: "its Step 4 discussion" antecedent | Resolved | The Split rule now reads "the SM/EM's sizing comments on that slice and that slice's Step 4 discussion". |
| AC9b: named sentence changes | Verified | The PR 260 body's "AC9b sentences" section is unchanged, and each named sentence is still present at the target; PR 263 names every sentence it changed. |
| AC11: prior-round context carry-forward | Verified | Every clause is present at the target, and the tabletop slice B brief built on the template shows parent 13 with voter values 13, 13, 13, the four-unknown ledger with total 8, the three whole-story rationales and no same-round value. |
| AC12: Anchoring guardrail amendment | Verified | Every clause is present at the target; the bound sentence naming 13 is a factual reference with no anchoring event, and an SM/EM "aim for 5" before the reveal is a target prescription that voids the round. |
| DoD: all acceptance criteria met | Verified | AC9b, AC11 and AC12. |
| DoD: tests written and passing | Verified | PR 263 updates the pins in `tests/test_shared_linear.py` and `tests/test_story_refinement.py`; CI `ci` passed on the reviewed head (run 43701924837) and on `main` at the target (run 43702487990, 2413 passed); a local full run at the target passed 2395 with none failed. |
| DoD: independently reviewed | Verified | Review 5910179495 on PR 263 is `COMMENTED` at `3d9721308661efdea36e0685cafb5dbce8db85c3`, names GPT-6.1 Sol as reviewer and DeepSeek V4.1 Flash as adjudicator, and was submitted at 10:06:38Z, before the 10:06:53Z merge. |
| DoD: docs updated | Verified | `scripts/vendor_shared.py --check` exits 0, and `SKILL.md` is 496 lines. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed: the run is on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | CI `checks` and `discovery` passed on `main` at the target, and every AC assertion of the probe passes at both `31ee7ba` and the target. |

Details:

- Probe: a read-only probe passed 37 of 37 assertions at the target and 27 of 37 at `31ee7ba`; the ten that fail at `31ee7ba` are exactly the defect assertions, so they are not vacuous.
- Incidental, low: Step 3 item 5 in `SKILL.md` defines the reveal as the moment all three values are recorded "or, in a slice round," every slice of the round has its three values, which read as a plain disjunction would allow a per-slice reveal; items 6 and 7 and the guardrail's opening line say "and", the Split rule defers each slice's reveal explicitly, and the guardrail's precedence settles it, so no acceptance criterion is affected.

Closing decision: Done, once this evidence merges.
