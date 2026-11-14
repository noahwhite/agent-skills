# SKL-306 QA evidence

## QA round 1

Date: 2026-11-14 UTC, independent QA round 1.
Target: `main` at `d282a5de0153c9bdea8ca8ddcaa78a0719813cc8`, the squash merge of PR 256, whose reviewed head is `83d475c3bd07de322874b78eb1fa30d2f65b50f5`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
Path: `no-deployment`; the profile sets `environments: []`, so the target is the merged commit above, no environment or build SHA applies, and the lanes are the repository, GitHub and the tracker.
Fixtures: none.
Dependency SKL-304 is Done, and its merge `a559d43` is an ancestor of the target.
The raw output is attached to SKL-306 as `SKL-306-qa-round-1-tabletop-probe.txt` and `SKL-306-qa-round-1-dod.txt`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC5b: saturating base, slice brief | Verified | The ledger bullet in `shared/linear.md`, the slice-brief sentence of the Split rule, the Saturation note line of the Slice brief template, and the worked example on a whole story at 13, the top of `fibonacci`, whose slice briefs name the ledger prices as lower bounds. |
| AC7: priced shared-unknown ledger | Verified | Every clause is in `shared/linear.md`, Step 3 item 4, Step 4 items 2 and 8, the Anchoring guardrail, Records, the Pointing record Ledger line and the Slice brief section; the worked example recomputes exactly. |
| DoD: all acceptance criteria met | Verified | AC5b and AC7. |
| DoD: tests written and passing | Verified | Ledger tests in `tests/test_shared_linear.py` and `tests/test_story_refinement.py`; CI `checks` passed at the reviewed head and on `main` (2408 passed); QA ran no local pytest. |
| DoD: independently reviewed | Verified | Details below. |
| DoD: docs updated | Verified | `SKILL.md`, `references/refinement-record.md`, `shared/linear.md` and its vendored copies. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed: the run is on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | CI runs 43628277454 (reviewed head) and 43628872227 (`main`) passed `checks` and `discovery`. |

Details:

- AC5b and AC7:
  - A read-only probe asserted each AC5b and AC7 clause in the committed text at the target, and every assertion passed.
  - The same probe at the parent `37b585b` failed every one of those assertions, so the probe is not vacuous.
  - It recomputed the Slice brief worked example independently: each whole-story rationale sums to 13, and the ledger is auth 3 (median of 3, 5, 2), schema 2 (lower of 2, 3), vendor API 2 (lower of 2, 3) and migration 1 (sole price), total 8 beside 13.
  - Each slice-owned ledger unknown appears with its ledger price in exactly one slice rationale, and the blocker-owned vendor API appears in none.
  - The re-pricing row, the assigned-elsewhere row and the whole-story mismatch row (7, not 8) are each off-basis.
  - `scripts/vendor_shared.py --check` exits 0, and `SKILL.md` is 489 lines.
- DoD, independently reviewed:
  - Review 5906505391 on PR 256 is `COMMENTED`, and its `commit_id` and first line name the merged head `83d475c3bd07de322874b78eb1fa30d2f65b50f5`.
  - It was submitted at 18:47:43Z, before the 18:50:57Z merge.
  - Its reviewer is GPT-6.1 Sol (`gpt-6.1-sol`) and its adjudicator is DeepSeek V4.1 Flash (`deepseek/deepseek-flash`), the seats in `profile.review` at that head.
  - It records a delta round that resolves the earlier findings with no new finding, and no valid blocking finding is open at the head.
- Incidental, low:
  - `shared/linear.md` says a re-split slice's owner reassignment is recorded in the split comment of split round 2, and the Slice brief template takes owners from it.
  - The Split bounds block that a story split's split comment carries has no line for that reassignment.
  - The normative rule is present; only the template slot is missing.
  - The Slice rationales row of the Slice brief worked example says each ledger unknown appears in exactly one slice rationale while the blocker-owned vendor API appears in none; the quantifier should be each slice-owned ledger unknown, as the normative rule in `shared/linear.md` states.

Closing decision: Done, once this evidence merges.

## QA round 2

Date: 2026-11-14 UTC, independent QA round 2, after the product owner amended AC7 with items (a) and (b) on 2026-11-14 and reopened the story.
Target: `main` at `a7aa8f600cea9851e457589ba3973569ed3d5134`, the squash merge of PR 258, whose reviewed head is `7ff3b5acd6bf77c98384e3408d239861acf139e7`.
The target is `origin/main`, and `git merge-base --is-ancestor` exits 0.
Path: `no-deployment`, selected by `select-path.py` over the repository profile (`environments: []`), so no environment or build SHA applies.
Fixtures: none.
Blockers SKL-304 (`a559d43`) and SKL-305 (`581de04`) are Done, and their merges and the first SKL-306 merge `d282a5d` are ancestors of the target.
The raw output is attached to SKL-306 as `SKL-306-qa-round-2-tabletop-probe.txt` and `SKL-306-qa-round-2-dod.txt`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC5b: saturating base, slice brief | Verified | All five AC5b assertions pass at the target and fail at `37b585b`. |
| AC7: priced shared-unknown ledger | Verified | All 28 core assertions pass at the target, including an independent recomputation of the worked example. |
| AC7 amendment (a): owner reassignment line | Verified | The Split bounds block has a `Ledger owners reassigned` line, matching the `shared/linear.md` clause; it is pinned in `SPLIT_BOUNDS_FIELDS`. |
| AC7 amendment (b): slice-owned wording | Verified | The Slice rationales row and its `LEDGER_EXAMPLE_RESULTS` pin say "each slice-owned ledger unknown". |
| DoD: all acceptance criteria met | Verified | AC5b and AC7. |
| DoD: tests written and passing | Verified | The test pins are updated; CI `checks` passed on the PR head (run 43650086810) and on `main` (run 43650607060, 2408 passed); QA ran no local pytest. |
| DoD: independently reviewed | Verified | Details below. |
| DoD: docs updated | Verified | `skills/story-refinement/references/refinement-record.md`; `scripts/vendor_shared.py --check` exits 0. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed: the run is on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | CI `checks` and `discovery` passed on `main` at the target, and the public `leak_scan.py` exits 0. |

Details:

- AC7 amendments:
  - `refinement-record.md` line 172 adds `Ledger owners reassigned` to the Split bounds block, which a round with no stop posts in the split comment.
  - That line gives the `shared/linear.md` clause, that a re-split slice's owner reassignment is recorded in the split comment of split round 2, a template slot.
  - `refinement-record.md` line 129 says each slice-owned ledger unknown appears in exactly one slice rationale, and the test pin carries the same string.
  - `git grep "ledger unknown"` finds no unscoped wording left in the skills or the tests.
  - The five amendment assertions pass at the target and fail at the parent `81fced0`, so the probe is not vacuous.
- AC5b and AC7:
  - The same probe passes all 41 assertions at the target and 4 of 41 at `37b585b`, where the four passes are pure recomputation or text that predates the story.
  - The worked example recomputes exactly: each whole-story rationale sums to 13, the ledger is auth 3, schema 2, vendor API 2 and migration 1, total 8 beside 13, and the blocker-owned vendor API is in no slice rationale.
- DoD, independently reviewed:
  - Review 5907620773 on PR 258 is `COMMENTED`, and its `commit_id` and first line name the merged head `7ff3b5acd6bf77c98384e3408d239861acf139e7`.
  - It was submitted at 22:52:02Z, before the 22:55:34Z merge.
  - Its reviewer is GPT-6.1 Sol (`gpt-6.1-sol`) and its adjudicator is DeepSeek V4.1 Flash (`deepseek/deepseek-flash`), the seats in `profile.review` at the target.
  - It records no findings.
- Incidental defects: none found this round.

Closing decision: Done, once this evidence merges.
