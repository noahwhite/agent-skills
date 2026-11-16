# SKL-297 QA evidence: promotion presence check no longer uses `git grep -x`

## QA round 1

- Date: 2026-11-16 UTC, independent QA round 1.
- Path: no-deployment; the repository profile sets `environments: []`, so the lanes are the repository (a fresh clone of `noahwhite/agent-skills`), GitHub and the tracker.
- Target: `main` at `fa679adf36645f99d7d206d7c3938ad00192c8b3`, the squash merge of PR 284; `git merge-base --is-ancestor` against `origin/main` exits 0.
- Reviewed head of PR 284: `3cc108fc37318370fe932570c3488a765d555080`.
- git 2.43.0.
- Fixtures: the selection under test is the SKL-257 squash commit `2bbf8cac364d79ac177a58ea891ac4040eccced8`, already on `main`.
- Each negative case is a local branch in the clone, cut from `origin/main` with one commit: a revert of `2bbf8ca`, an edit of the story's changed line (`skills/story-to-done/SKILL.md` line 197), an edit two lines below it (line 199), the story's line kept only as a substring of a longer line, and a rename of `tests/test_delegated_briefs.py`.
- The positive control is a branch cut the same way with one edit far from the story's lines (`skills/story-to-done/SKILL.md` line 12).
- The raw output of every command below is attached to SKL-297 as `SKL-297-qa-round-1-assertions.txt`; there is no visual surface, so no screenshot applies.
- The four prescribed commands were run verbatim from the promotion sentence, with only `<worktree>`, `<patch>`, `<commit>` and the integration ref filled in.

| Item | Verdict |
|---|---|
| AC1: original failure no longer reproduces | Verified |
| AC2: present only with merged context; substring not present | Verified |
| AC3: source changed, copies regenerated, `--check` clean | Verified |
| AC4: sentence pinned exactly, mutation-proven | Verified |
| AC5: no other promotion sentence changes; other pins pass | Verified |
| DoD: root cause identified | Verified |
| DoD: fix verified against the original failing case | Verified |
| DoD: regression protection added | Verified |
| DoD: independently reviewed | Verified |
| DoD: docs/comments updated | Verified |
| DoD: no new regressions | Verified |

### Evidence per item

AC1: the old step 2 command, `git grep --fixed-strings -x -e foo origin/main`, still exits 129 with `error: unknown switch` and the usage text, so the original failure was reproduced as the story describes.
The prescribed commands run without a usage error in every case below: `git worktree add` exits 0, `git diff-tree` exits 0, the `git apply --check -R` step exits 0 or 1, and `git worktree remove` exits 0.
PR 284's description records one run with each command's exit status: exit 129 for the old command, exit 0 with no output against `origin/main`, and exit 1 against a ref without the story.

AC2, present: with the selection on `origin/main`, the check exits 0 and prints 0 bytes.
The same holds for the SKL-297 squash commit `fa679ad` itself (15 files).

AC2, not confirmed present: each case below exits 1 and prints `error:` lines naming the file.

| Integration ref | Check exit | Output |
|---|---|---|
| `4103039` (before the story merged) | 1 | patch does not apply in 3 files |
| revert of `2bbf8ca` | 1 | patch does not apply in 3 files |
| story's line edited later | 1 | `SKILL.md`: patch does not apply |
| line two below the story's line edited later | 1 | `SKILL.md`: patch does not apply |
| story's line only a substring of a longer line | 1 | `SKILL.md`: patch does not apply |
| `tests/test_delegated_briefs.py` renamed later | 1 | does not exist in index |

AC2, accepted residual: the story's Fix paragraph states the duplicated 3-line context residual, and the fail-closed environment and retry residuals beside it.

AC3: `shared/github.md` line 133 carries the corrected sentence, and each of the 13 `skills/*/references/github.md` copies carries it once.
`python3 scripts/vendor_shared.py --check` exits 0 with no output.
`git grep -F 'fixed-strings -x' -- shared skills` finds nothing.

AC4: `tests/test_shared_github.py` pins the corrected sentence in `PER_STORY_SENTENCES` and in the line-for-line `EXPECTED_PROMOTION_SECTION`.
In a throwaway worktree of `fa679ad`, deleting line 133 of `shared/github.md` gave `17 failed, 6 passed`, including `test_per_story_promotion_sentences_are_present_verbatim` and `test_promotion_section_is_pinned_line_for_line`.
After restoring the file, the module gave `23 passed`.
PR 284's description shows the same mutation with the same counts.

AC5: `git diff 2bbf8ca fa679ad` changes one line in `shared/github.md`, line 133 (`git diff -U0` hunk `@@ -133 +133 @@`), and one line in each vendored copy.
In `tests/test_shared_github.py` the only removed lines are the two old pins of that sentence; every other change is an addition.
Every other pin in the module passes at the target.

DoD, root cause: `git grep` has no `-x` switch; the AC1 run reproduces it, and PR 284's description states it.

DoD, original failing case: AC1.

DoD, regression protection: the pins in AC4, plus `test_promotion_no_longer_prescribes_git_grep` and the behavioural tests that run the four commands against a fixture repository.

DoD, independently reviewed: review `PRR_kwDOVBNk788AAAABYJlI4Q` on PR 284 is `COMMENTED` and names `3cc108fc37318370fe932570c3488a765d555080` in its first line and as its commit, and that SHA is the PR's head at merge.
Its reviewer (GPT-6.1 Sol) and adjudicator (DeepSeek V4.1 Flash) match the profile at the target.
Round 1 ruled one finding valid (Medium, `apply.ignoreWhitespace=change`), fixed in `3c8cdca` within the PR; the round 2 delta review has no findings and rules the head clean.
CI run 43812643396 at the reviewed head and push CI run 43813639766 at the target both concluded `success`.

DoD, docs: the promotion sentence itself states the flags, the confirmed and not-confirmed rules and the stop conditions; the fixture's comments state the hostile configuration it guards against.

DoD, regressions: an edit far from the story's lines still exits 0 with no output, so an unrelated later change does not stop a promotion.
A missing integration ref makes `git worktree add` exit 128, which the sentence reports as a failed check.
No throwaway worktree remained registered after the runs.
`uv run --locked pytest -q` on a fresh clone at the target: `2679 passed`.

Closing decision: every AC and DoD item is verified, so SKL-297 moves to Done once this evidence merges.
