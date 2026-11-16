# SKL-278 QA evidence: story-to-done path in both briefs, PR gates and step 4 on every path

## QA round 1

- Date: 2026-11-16 UTC, independent QA round 1.
- Path: no-deployment; the repository profile sets `environments: []`, so the lanes are the repository, GitHub and the tracker.
- Target: `main` at `298a7ee290fb243dd175bd08df2a7f766ba5a74f`, the squash merge of PR 289; `git merge-base --is-ancestor` against `origin/main` exits 0.
- Reviewed head of PR 289: `d4bcb59bf4124dbdafcd73780104ef1049aa593f`.
- Dependencies SKL-270, SKL-269 and SKL-162 are Done, and their merged commits are ancestors of the target.
- Fixtures: none; every item is read from the committed artifacts at the target or from GitHub and the tracker.
- The raw output of every command below is attached to SKL-278 as `SKL-278-qa-round-1-assertions.txt`; there is no visual surface, so no screenshot applies.
- Line numbers refer to `skills/story-to-done/SKILL.md` at the target.

| Item | Verdict |
|---|---|
| AC1: briefs carry the path and state what each path needs | Verified |
| AC2: PR gates hold on every path | Verified |
| AC3: step 4 on paths without a deployment | Verified |
| AC4: AC2 sentences pinned | Verified |
| AC5: repository guards pass | Verified |
| DoD: all acceptance criteria met | Verified |
| DoD: unit/integration tests written and passing | Verified |
| DoD: independently reviewed | Verified |
| DoD: docs updated (if applicable) | Verified |
| DoD: verified in a deployed environment (if needed) | Not needed, correct by design (no-deployment path) |
| DoD: no critical bugs/regressions | Verified |

### Evidence per item

AC1: the step 2 list carries the `path: <value>` line at L166 and the step 3 list at L211, each saying the role never reselects the path.
L182 to L184 keep the step 2 brief as the list on `deployed`, ask for the merged commit on `no-deployment`, and on `spike` limit the PR-through-merge steps to a tracked-file change and ask for each deliverable's link with its commit when one exists.
L222 and L223 keep the step 3 brief as the list on `deployed` and, on `no-deployment` and `spike`, name the verification target in SKL-269's wording on every entry, a run that starts at step 3 included.
The step 3 heading at L202 is unchanged, and no other line of either brief changed in the diff.

AC2: L198 runs the step 2 and step 3 merged-PR read-backs unchanged on every path, L199 states the no-merged-PR stop with the `spike` exception, and L200 states that no path adds a waiver, an admin override or a change to the expected-head condition.
The read-back lines of steps 2 and 3 are untouched in the diff.

AC3: L238 counts the deployed-environment DoD item as verified on `no-deployment` and `spike` when its box is ticked and QA rules it not needed.
It is the only line the diff adds to step 4, and the step 4 state-bullet digests in the tests are unchanged.

AC4: `tests/test_story_to_done.py` pins both AC2 sentences verbatim as operative prose, stated once, in two tests that pass at the target.
In a throwaway worktree, editing each sentence made both tests fail (`2 failed`); the file was restored afterwards.
The only other test change is the re-baselined `STEP_3_SHA256` digest.

AC5: at the target, `scripts/leak_scan.py` passes its public half, `skills-ref validate skills/story-to-done/` reports a valid skill, and `scripts/smoke-opencode.sh` discovers all 18 skills in all six contexts.
CI run 43815351050 at the reviewed head (tests `2699 passed`, leak scan with `--require-private`, skill validation, discovery) and push CI run 43816508361 at the target both concluded `success`.
The broken `STEP_3_SHA256` pin was updated in the same PR.

DoD, tests: the two AC4 tests, and `uv run --locked pytest -q` at the target: `2681 passed`.

DoD, independently reviewed: review 5915828329 on PR 289 is `COMMENTED` and names `d4bcb59bf4124dbdafcd73780104ef1049aa593f` in its first line and as its commit, and that SHA is the PR's head at merge.
Its reviewer (GPT-6.1 Sol) and adjudicator (DeepSeek V4.1 Flash) match the profile at the target; the reviewer reported no findings and the adjudicator ruled the head clean.

DoD, docs: the change is to the skill document itself; the README's one-line summary of `story-to-done` does not describe the briefs and needs no change.

DoD, deployed environment: nothing is deployed on the no-deployment path, so the item is not needed.

DoD, regressions: the full suite and every CI guard pass at the target.

Closing decision: every AC and DoD item is verified or, for the deployed-environment item, not needed on this path, so SKL-278 moves to Done once this evidence merges.
