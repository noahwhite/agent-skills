# SKL-307 QA evidence

## QA round 1

Date: 2026-11-15 UTC, independent QA round 1.
Target: `main` at `31ee7ba2a85b2688f31caf0b2823b0b6c27fce13`, the squash merge of PR 260, whose reviewed head is `a4b6f5a21abf9b93a44a6b53e0560984f8104b77`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
Path: `no-deployment`, selected by `select-path.py` over the repository profile (`environments: []`), so no environment or build SHA applies.
Fixtures: none.
Blockers SKL-304 (`a559d43`), SKL-305 (`581de04`) and SKL-306 (`d282a5d`, `a7aa8f6`) are Done, and their merges are ancestors of the target.
The raw output is attached to SKL-307 as `SKL-307-qa-round-1-probe-target.txt`, `SKL-307-qa-round-1-probe-parent.txt` and `SKL-307-qa-round-1-dod.txt`; there is no visual surface, so no screenshot applies.

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
