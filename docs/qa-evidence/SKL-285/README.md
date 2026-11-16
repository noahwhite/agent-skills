# SKL-285 QA evidence

## QA round 1

Date: 2026-11-16 UTC, independent QA round 1.
Path: `spike`, selected with `select-path.py` from the step 12 note's `path: spike` line.
Target: the findings comment `588e08ea` on SKL-285, the filed stories SKL-320 to SKL-324, and the refinement proposal comments `535ff876` on SKL-284, `64802f50` on SKL-160 and `1081123c` on SKL-290.
None of these deliverables has a commit; the spike changed no tracked file, and no SKL-285 branch or PR exists.
Baseline read for the recount: `main` at `4103039823b376c5dacbeb32eb2c024234b9f8fd`, the SHA the findings record, in a detached worktree.
No environment and no deployed build apply on the `spike` path, and no fixture was needed.
There is no visual surface, so no screenshot applies.
The commands and their raw output are attached to SKL-285 as `SKL-285-qa-round-1-assertions.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| SC1: baseline SHA | Verified | Details below. |
| SC2: one row per section | Verified | Details below. |
| SC3: measured columns | Verified | Details below. |
| SC4: ownership | Verified | Details below. |
| SC5: pinning tests | Verified | Details below. |
| SC6: research questions | Verified | Details below. |
| D1: findings comment | Verified | Details below. |
| D2: Go or No-Go per row | Verified | Details below. |
| D3: filed stories | Verified | Details below. |
| D4: No-Go alternatives | Verified | Details below. |
| DoD: success criteria validated | Verified | SC1 to SC6. |
| DoD: findings documented in Linear | Verified | The findings comment on SKL-285. |
| DoD: Go or No-Go for every candidate row | Verified | D2. |
| DoD: next steps defined | Verified | D3 and SC4. |

Details:

- SC1:
  - `4103039` is an ancestor of `origin/main`.
  - It was committed at 05:13 UTC, the spike's agent stamp is 05:37 UTC, and the next `main` commit landed at 05:55 UTC, so it was `main` at spike start.
  - At that SHA, all 39 cited line ranges give the stated `wc -w`, the 10 stated sums add up, and the three file sizes (6,616, 2,176 and 1,112 words) match.
  - `tests/test_story_to_done.py` has 230 test functions, as stated.
- SC2:
  - SKILL.md has 11 `##` and `###` sections, interim-handbacks.md has its title and 3 `##` sections, and metrics-protocol.md has only its title; each has one row with a locator, a classification and a reason.
  - No `####` heading exists in these files.
  - The 9 files with the `GENERATED from shared/` header get rows only for references SKILL.md names, with owner `shared/`; SKILL.md names neither `github.md` nor `merge-approval.md`, as the findings state.
- SC3:
  - Each of the 21 candidate rows records words replaced as `wc -w` of a cited range, reads removed, frequency and verbatim output.
  - C10's frequency uses the SKL-270 path names.
- SC4:
  - Each candidate is `owned by`, `partly owned by` with the remainder stated, or `unowned`.
  - All 12 quoted criteria appear verbatim on SKL-284, SKL-160, SKL-209, SKL-270, SKL-290, SKL-278 and SKL-258, and the criterion numbers match.
  - The comments on SKL-284, SKL-160 and SKL-290 are headed "Refinement proposal (not an AC)", and each says it changes no acceptance criterion.
- SC5:
  - Every named test is a `def` in its stated module (`tests/test_story_to_done.py`, or `tests/test_merge_guard.py` where stated), and each count matches its list.
- SC6:
  - RQ1 to RQ4 are answered by number.
  - RQ2 names SKILL.md L281 and L282 in `## Boundaries` for the two scripts that would post.
  - RQ4 recommends one shared helper, citing the three existing scripts (45 lines in `skills/story-to-done/scripts/`, and 357 and 118 lines in `shared/`), and the two later scripts share no byte-identical function.
- D1:
  - The findings comment holds the baseline SHA, a table with the ten required columns, RQ1 to RQ4 and the next steps.
- D2:
  - All 21 candidate rows carry Go or No-Go with a reason citing words, reads and frequency.
  - Owned rows are judged against their owning story.
- D3:
  - SKL-320 to SKL-324 are SKL user stories in Backlog with the `linear-user-story` title prefix, labels and sections, each with a `related` relation to SKL-285.
  - SKL-320, the shared helper, is its own story and blocks SKL-321 and SKL-322, the two stories that use it.
  - SKL-323 covers C04 and C05, and SKL-322 covers C07 and C09, so each unowned Go candidate has one filed story.
  - SKL-320 and SKL-324 name a split line for the cap; SKL-321, SKL-322 and SKL-323 are each scoped to one behaviour, and their own refinement confirms the size.
- D4:
  - C01, C03, C06, C18, C19 and C20 name "keep the prose", and the C12 and C14 remainders name "fold into the owning story".

No item failed and no item is pending an owner ruling.

Closing decision: SKL-285 moves to Done once this evidence PR merges.
