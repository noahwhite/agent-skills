# SKL-305 QA evidence

## QA round 1

Date: 2026-11-14 UTC, independent QA round 1.
Target: `main` at `581de0468ad8c48aae1cdd675744130433d7d09f`, the squash merge of PR 252, whose reviewed head is `48f1309d54443f16f357c78a2d5807c974883185`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
Environment: none; the profile sets `environments: []`, so no build SHA applies and the lanes are the repository, GitHub and the tracker.
Fixtures: none.
Dependency SKL-304 is Done, and its merge `a559d43` is an ancestor of the target.
The raw output is attached to SKL-305 as `SKL-305-qa-round-1-tabletop-probe.txt` and `SKL-305-qa-round-1-dod.txt`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC6: no scope growth | Verified | The no-scope-growth, exactly-one mapping and before-pointing stop sentences in `shared/linear.md` and the Split rule; the unmapped row stops naming B2 before any slice is pointed, and the fully mapped row proceeds unchanged. |
| AC8: lower consensus for slices | Verified | Step 4 item 1 is unchanged for an unsplit story; slice votes 3, 5, 5 record 3 with both values; 8 into 3 (5), 3 (5), 3 (5) warns on the lower sum 9 while the higher sum 15 would stop; the hard-stop message names both sums and both bands. |
| AC13: check order and single report | Verified | Mapping, pointing, per-parent bound, whole-story sum, then the round cap after round 2 only; 8 into 8, 5 gives one `needs input` message naming the per-parent bound and the band stop. |
| DoD: all acceptance criteria met | Verified | AC6, AC8 and AC13. |
| DoD: tests written and passing | Verified | `tests/test_story_refinement.py` and `tests/test_shared_linear.py`; full suite 2364 passed at the target. |
| DoD: independently reviewed | Verified | Details below. |
| DoD: docs updated | Verified | `SKILL.md` Step 4 and Split rule, `shared/linear.md` and its vendored copies, and `references/refinement-record.md`. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed: the profile has no deployable environment. |
| DoD: no critical bugs or regressions | Verified | CI runs 43614960397 (reviewed head) and 43615527546 (`main`) passed `checks` and `discovery`. |

Details:

- AC6, AC8 and AC13:
  - Each AC's text was matched sentence by sentence in the "Estimation and slicing" section of `shared/linear.md`, Step 4 and the Split rule of `skills/story-refinement/SKILL.md`, and `references/refinement-record.md`.
  - An independent tabletop recomputed the two mapping-check rows and the single-round split-bounds rows from the mapping rule and the bands, and every result matched the table.
  - The tabletop found exactly four places where Step 4 records a highest value (item 1 tolerance, item 5 consensus, item 6 derived value, item 6 tolerance), the four the slice rule names.
  - All 18 vendored `references/linear.md` copies equal `shared/linear.md` below the generated header, and `SKILL.md` is 481 lines.
- DoD, independently reviewed:
  - Review 5905760905 on PR 252 is `COMMENTED`, and its `commit_id` and first line name the merged head `48f1309d54443f16f357c78a2d5807c974883185`.
  - It was submitted at 16:21:02Z, before the 16:25:26Z merge.
  - Its reviewer is Codex GPT-6 Sol (`gpt-6-sol`) and its adjudicator is DeepSeek V4.1 Flash (`deepseek/deepseek-flash`), the seats in `profile.review` at that head.
  - It records round 1 and a delta round with a verdict for every finding and a fix commit for the one valid finding, and no valid blocking finding is open at the head.
- Incidental, low:
  - In `references/refinement-record.md` the rows "Two failures in one round" and "Per-parent bound: a child equal to its parent" abbreviate the band in their result cell instead of naming both sums and both bands as the normative rule and the "Hard stop" row do.

Closing decision: Done, once this evidence merges.
