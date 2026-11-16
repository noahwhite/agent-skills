# SKL-304 QA evidence

## QA round 1

Date: 2026-11-14 UTC, independent QA round 1.
Path: `no-deployment`, printed by `skills/qa-verification/scripts/select-path.py` on the merged commit; no recorded `path:` line exists.
Target: `main` at `a559d4387547b7af68598fcd0beaee8fa58025ec`, the squash merge of PR 247, whose reviewed head is `3b52dd5614de93fae7d83db69066b51938a1c278`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
Environment: none; the profile sets `environments: []`, so no build SHA applies and the lanes are the repository, GitHub and the tracker.
Fixtures: none.
The raw output is attached to SKL-304 as `SKL-304-qa-round-1-assertions.txt`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: hard stop, whole-story sum | Verified | `shared/linear.md` check 2, the band, naming and stop-hold sentences; 8 into 5, 5, 3 sums 13 against 8 and 12 and stops in round 1. |
| AC2: warning band | Verified | 8 into 5, 5, 2 sums 12 against 8 and 12 and proceeds with the split-comment warning. |
| AC3: clear band | Verified | 8 into 5, 3 sums 8 against 8 and 12 and proceeds with no flag. |
| AC4: round cap | Verified | With `point_cap` 3, 13 into 8, 5, then 5, 3 and 3, 2, stops before a third split on the slice at 5; 8 into 5, 3, then 3, 2, proceeds unchanged. |
| AC5a: saturated base | Verified | Step 4 item 1 tops `fibonacci` at 13; 13 into 8, 8, 5 sums 21 against 13 and 19.5 and stops naming the base saturated and the bounds as lower bounds. |
| AC9a: supersession | Verified | Details below. |
| AC10: per-parent bound | Verified | 8 into 8, 3 stops (parent 8, slice 8, band warning); a round-2 parent 8 into 5, 5, 3 stops (13 against 8 and 12); 8 into 5, 3 proceeds. |
| DoD: all acceptance criteria met | Verified | AC1 to AC10. |
| DoD: tests written and passing | Verified | `tests/test_story_refinement.py` and `tests/test_shared_linear.py`; full suite 2359 passed. |
| DoD: independently reviewed | Verified | Details below. |
| DoD: docs updated | Verified | `SKILL.md` Split rule, `shared/linear.md` and its vendored copies, and the Split bounds section of `references/refinement-record.md`. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed: the path is `no-deployment`. |
| DoD: no critical bugs or regressions | Verified | CI runs 43602723610 (reviewed head) and 43603281133 (`main`) passed `checks` and `discovery`. |

Details:

- AC1 to AC5a and AC10:
  - Each AC's text was matched sentence by sentence in the "Estimation and slicing" section of `shared/linear.md` and the Split rule of `skills/story-refinement/SKILL.md`.
  - An independent tabletop recomputed all nine worked examples in `references/refinement-record.md` from the bands, and every result matched the table.
  - The clause "recorded value (lower consensus, AC8)" in AC1, AC4 and AC10 is out of scope: AC8 is owned by SKL-305, which is in Backlog.
  - This story's checks compare the recorded value and name the sum with each slice's lower and higher consensus value.
- AC9a:
  - The three superseded sentences match no file in the repository.
  - All 18 vendored `references/linear.md` copies equal `shared/linear.md` below the generated header and name SKL-230 as superseded, and `scripts/vendor_shared.py --check` exits 0.
  - The Split rule of `SKILL.md` names SKL-230 as superseded, and `SKILL.md` is 477 lines.
  - The two test files pin the new sentences and assert the old ones absent, with each old sentence split so that no literal copy exists.
  - `uv run --locked pytest -q` passed (2359 passed), the public leak scan exited 0, and `skills-ref validate` passed for all 18 skills.
- DoD, independently reviewed:
  - Review 5904737335 on PR 247 is `COMMENTED`, and its `commit_id` and first line name the merged head `3b52dd5614de93fae7d83db69066b51938a1c278`.
  - It was submitted at 14:03:32Z, before the 14:08:17Z merge.
  - Its reviewer is Codex GPT-6 Sol (`gpt-6-sol`) and its adjudicator is DeepSeek V4.1 Flash (`deepseek/deepseek-flash`), the seats in `profile.review` at that head.
  - It records rounds 1 to 4 with a verdict for every finding and a fix commit on the PR for each valid one, and round 5 at the head has no findings.
  - Rounds 1 to 4 were not posted as their own reviews at their heads; their findings and verdicts appear in the posted review of record.

Closing decision: Done, once this evidence merges.
