# SKL-251 QA evidence

## Round 1

Date: 2026-11-11 UTC, independent QA round 1.
Story: SKL-251 - the `cleanup` local branch read-back is an exact-ref check instead of the glob `git branch --list`.
AC 3 was verified as amended by the owner: the worktree read-back is unchanged, and the remote read-back requires exit 0 and treats only the exact `refs/heads/<branch>` line as the branch still existing.
Build under test: `main` at `da295a43a92deeaf0fc6f939c3bc182826ad6cb7`, which contains `a658d16dae1b547c7c6f9ae5777db1e732ca6aee`, the squash merge of PR 204, whose reviewed head is `489d96f3cacea1248e514a4560bdd92ffba1b64c`.
The two files PR 204 changes are identical at that head and at the merge, and the later commit `da295a4` changes neither the step 3 sentences below nor their tests.
Environment: the profile lists no environments, so every item was checked on the repository, GitHub and tracker lanes.
Method: a text probe asserted the step 3 guard sentences of `skills/cleanup/SKILL.md` at the build against the pre-fix text at `f75da71`, and a git probe ran the read-back commands against the fixture below.
Fixtures:

- A synthetic bare origin and clone with `main` as the integration branch.
- Local branches `feature/SKL-1-x` and `feature/SKL-1-xy`.
- A remote branch `feature/SKL-9-b` and a nested remote branch `team/feature/SKL-9-b`, and an unreachable origin URL for the failed read.

There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw output is attached to SKL-251 as `SKL-250-253-text-probe.txt` and `SKL-250-253-git-probe.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| AC 1: read-back does not use `git branch --list` | Verified | At `f75da71` the guard used `git branch --list <branch>`. At the build the string `git branch --list` is absent from the skill. |
| AC 2: read-back proves the exact named ref is gone | Verified | The guard requires `git show-ref --verify --quiet refs/heads/<branch>` to exit 1 after a local-branch removal, with exit 0 and any other status both refusals. In the git probe it exits 0 while `feature/SKL-1-x` exists and 1 after `git branch -D`, with `feature/SKL-1-xy` still present. |
| AC 3 (amended): worktree read-back unchanged | Verified | The worktree read-back is still `git worktree list` must no longer list it, now scoped to a worktree removal, and the second-status-read clause is present unchanged. |
| AC 3 (amended): remote read-back exit 0 and exact line | Verified | The guard requires `git ls-remote --heads origin <branch>` to exit 0 and list no line whose ref is exactly `refs/heads/<branch>`, and calls any other exit status a failed read. No status-blind `git ls-remote ... must` requirement remains. In the git probe the read after the delete exits 0 and lists only `refs/heads/team/feature/SKL-9-b`, which is not the branch, and a read from an unreachable origin exits 128 with empty stdout. |
| DoD: root cause identified | Verified | The story comment records that `git branch --list` takes a glob, and that a false read-back was not reproducible with a valid ref name; the AC was implemented as written. |
| DoD: fix verified against the original failing case | Verified | AC 1 and AC 2 above, on the same guard line that failed. |
| DoD: regression protection | Verified | `test_a_local_branch_read_back_is_an_exact_ref_check` pins the per-kind read-backs and forbids `git branch --list`, and `test_every_remote_read_must_exit_0_and_match_the_exact_ref` pins the remote rule. Both pass at the build. |
| DoD: independently reviewed | Verified | The PR 204 review of record names `489d96f3cacea1248e514a4560bdd92ffba1b64c` in its first line and as its `commit_id`, by Codex GPT-6 Sol with DeepSeek V4 Pro adjudicating; its round 1 findings on the remote read-back were fixed in `eda3299` after the AC 3 amendment. |
| DoD: docs updated | Verified | The guard states that `--quiet` prints nothing, so the exit status is the evidence, and why a nested `/<branch>` line is not the branch. |
| DoD: no new regressions | Verified | `uv run pytest -q` at the build: 1715 passed. CI `ci` succeeded on `489d96f`, `a658d16` and `da295a4`. |

Closing decision: Done, once this evidence merges.
