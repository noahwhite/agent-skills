# SKL-248 QA evidence

## Round 1

Date: 2026-11-11 UTC, independent QA round 1.
Story: SKL-248 - `cleanup` reads a branch tip with a bare `git rev-parse`, so a same-named tag answers.
Build under test: `main` at `da295a43a92deeaf0fc6f939c3bc182826ad6cb7`, which contains the squash merge of PR 200 (`f75da71a47000335e9b89997c219528f1f6b8e14`), whose reviewed head is `87774112cfe4ed9ac85297d95e0e38fa593ca694`.
Environment: the profile lists no environments, so every item was checked on the repository, GitHub and tracker lanes.
The test suite and the text probe ran in a detached worktree of the build, and the mutation spot-check ran in a second one.
Fixtures: a throwaway repository with a branch `feature/x` and a tag `feature/x` on different commits, the tag on the integration branch tip.

There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw output is attached to SKL-248 as `SKL-248-qa-assertions.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: no bare `git rev-parse <branch>` | Verified | Every `rev-parse` span in `skills/cleanup/SKILL.md` on the build is `refs/heads/<branch>`, `HEAD`, or `--git-path modules`. |
| AC2: merge evidence and second tip read use the branch tip | Verified | In the fixture, `git rev-parse refs/heads/feature/x` returns the branch commit, while the bare read returns the tag commit with an ambiguity warning. With the bare tip, `git merge-base --is-ancestor` exits 0, false containment evidence; with the full-ref tip it exits 1. The full-ref tip equals a simulated `headRefOid` for the branch, and the bare tip does not. |
| AC3: adjacent paths unchanged | Verified | The PR 200 diff leaves the `git ls-remote --heads origin <branch>` text and the SKL-245 recorded-instruction `refs/heads/` reads untouched. |
| DoD: root cause identified | Verified | A bare refname resolves `refs/tags/<name>` before `refs/heads/<name>`; all three bare sites were changed to the full ref. |
| DoD: fix verified against the original failing case | Verified | The AC2 fixture is the case the story records. |
| DoD: regression protection | Verified | `test_every_local_branch_tip_read_names_its_full_ref` passes on the build and fails on each of four mutations: a bare read at the merged-PR tip, the containment tip and the pre-delete tip, and a literal `git rev-parse feature/ABC-123`. `git status` was clean after restore. |
| DoD: independently reviewed | Verified | The PR 200 review of record names `87774112cfe4ed9ac85297d95e0e38fa593ca694` in its first line and as its `commit_id`, the merged head. Its reviewer is Codex GPT-6 Sol and its adjudicator is DeepSeek V4 Pro; the round 1 Low finding was fixed at that head and round 2 found nothing valid. |
| DoD: docs updated | Verified | Step 3 now states that `<branch>` is the name without its `refs/heads/` prefix, passed as one argument; the test comments name SKL-248. |
| DoD: no new regressions | Verified | `uv run pytest -q` at the build reported 1715 passed. CI `checks` and `discovery` succeeded on `f75da71` (run 42956397909) and on the build (run 43039747124). |

Closing decision: Done, once this evidence merges.
