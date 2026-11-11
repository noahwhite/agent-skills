# SKL-244 QA evidence

## Round 1

Date: 2026-11-10 UTC, independent QA round 1.
Story: SKL-244 - `cleanup` counts branch containment as merge evidence under every merge method.
Build under test: `main` at `91d5b04dc18ea105dfc507ffa2af1586f32dd2a3`, the squash merge of PR 190, whose reviewed head is `d885fec8cac45967f4c456e74582f33cda56730c`.
Environment: the profile lists no environments, so every item was checked on the repository, GitHub and tracker lanes.
The test suite and the text reads ran in a detached worktree of the build, and the mutation check ran in a second one.
Method: a text probe asserted each A1 to A3 sentence in step 3 of `skills/cleanup/SKILL.md` and compared the Worktree and Remote branch bullets with the merge parent; a git probe ran the step 3 containment rule literally against the fixtures below.
Fixtures:

- Synthetic repositories under a `squash` profile, each a bare origin and a clone with `main` as the integration branch.
- The SKL-88 shape: a local branch with no PR whose tip is contained in `origin/main` and which no worktree holds.
- A squash-merged branch, a tip that is not a commit in the repository, a failed `git fetch origin`, a contained branch held by a linked worktree, one held by the main working tree, and a detached HEAD worktree at a contained commit.

There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw output is attached to SKL-244 as `SKL-244-a1-a2-a3-skill-text-probe.txt`, `SKL-244-a1-a3-git-containment-probe.txt`, `SKL-244-a4-mutation-spot-check.txt`, `SKL-244-dod2-pytest-91d5b04.txt` and `SKL-244-repo-lane-dod.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| A1: containment as local-branch evidence | Verified | Step 3's evidence sentence names both sources, and the Containment bullet carries the exit 0, `<tip>`, exit 1, other-exit and fetch-failure sentences and the replacement sentence. Neither "neither `squash` nor `rebase`" nor "proves nothing and is never used" appears in step 3. The Worktree bullet is byte-identical to the merge parent, and the `Read first` line no longer says "stricter". In the git probe a contained tip exits 0, a squash-merged tip exits 1, a tip that is not a commit exits 128, and a failed fetch exits 128. |
| A2: remote rule, PR evidence only | Verified | The Remote branch bullet carries the sentence that containment is never remote evidence and is otherwise byte-identical to the merge parent, so its merged-PR, open-PR, complete-listing, second-read and never-a-PR rules are unchanged. |
| A3: checked-out branches | Verified | The Local branch bullet carries the checked-out-branch sentence. In the git probe the SKL-88 branch reaches `git branch -D` after both reads exit 0, and `git branch --list` reads back empty. `git branch -D` refuses a contained branch held by a linked worktree and deletes it once that worktree is removed. It also refuses a contained branch held by the main working tree, which step 3 never removes, so that branch stays refused. The PR 190 description carries the SKL-88 squash trace ending in the empty read-back. |
| A4: tests | Verified | The two old assertions are removed, the `git merge-base --is-ancestor` and `origin/<profile.git.integration_branch>` assertions stay, and every new assertion reads the step 3 section. The existing remote assertions are unchanged. Removing each of 8 A1 to A3 sentences, or restoring either old sentence, makes `tests/test_cleanup.py` fail 10 of 10 times. PR 190 notes its own mutation run, 17 of 17. |
| DoD: all acceptance criteria met | Verified | A1 to A4 above. |
| DoD: tests written and passing | Verified | `uv run --locked pytest -q` reports 1592 passed at the build. CI `checks` and `discovery` succeeded on `d885fec` and on `91d5b04`. |
| DoD: independently reviewed | Verified | The PR 190 review of record names `d885fec` in its first line and as its `commit_id`. Its reviewer is Codex GPT-6 Sol and its adjudicator is DeepSeek V4 Pro, and its one finding was ruled invalid. The two changed files are identical at that head and at the merge. |
| DoD: docs updated | Verified | PR 190 edits step 3 and the `Read first` line of `skills/cleanup/SKILL.md`. |
| DoD: verified in a deployed environment | Not needed | The repository deploys nothing (`environments: []`), so the delivered skill text on `main` at the build is what was verified. |
| DoD: no critical bugs or regressions | Verified | The full suite passes, and the Remote branch and Worktree rules are unchanged. |

Closing decision: Done, once this evidence merges.
