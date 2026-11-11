# SKL-250 QA evidence

## Round 1

Date: 2026-11-11 UTC, independent QA round 1.
Story: SKL-250 - the `cleanup` remote-branch delete names the command for its second remote tip read.
Build under test: `main` at `da295a43a92deeaf0fc6f939c3bc182826ad6cb7`, which contains `a658d16dae1b547c7c6f9ae5777db1e732ca6aee`, the squash merge of PR 204, whose reviewed head is `489d96f3cacea1248e514a4560bdd92ffba1b64c`.
The two files PR 204 changes are identical at that head and at the merge, and the later commit `da295a4` changes neither the step 3 sentences below nor their tests.
Environment: the profile lists no environments, so every item was checked on the repository, GitHub and tracker lanes.
Method: a text probe asserted the step 3 sentences of `skills/cleanup/SKILL.md` at the build against the pre-fix text at `f75da71`, and a git probe ran the commands step 3 names against the fixture below.
Fixtures:

- A synthetic bare origin and clone with `main` as the integration branch.
- A remote branch `feature/SKL-9-b`, a nested remote branch `team/feature/SKL-9-b`, and a remote tag `feature/SKL-9-b`.

There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw output is attached to SKL-250 as `SKL-250-253-text-probe.txt` and `SKL-250-253-git-probe.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| AC 1: second remote tip read names its command | Verified | At `f75da71` the remote-branch bullet read "Read the remote tip a second time immediately before the delete and refuse if it moved" with no command. At the build it reads the tip "a second time with `git ls-remote --heads origin <branch>` immediately before the delete" and takes the SHA on the line whose ref is exactly `refs/heads/<branch>`. |
| AC 2: refuse if moved, delete immediately after | Verified | The bullet says to "compare it with the tip recorded at merge evidence, and refuse if it moved; otherwise run `git push origin --delete refs/heads/<branch>` immediately after that read, with no other step between". In the git probe a push between the merge-evidence read and the second read changes the exact-ref SHA, which the rule refuses. |
| AC 3: adjacent text unchanged | Verified | The local-branch second read behaves as before: its clause "Read the tip with `git rev-parse refs/heads/<branch>` a second time immediately before `git branch -D` and refuse if it moved" is unchanged. The one textual change in that bullet is the SKL-252 rename, in the same sentence, of the containment re-read from `origin/<profile.git.integration_branch>` to `refs/remotes/origin/<profile.git.integration_branch>`. The open-PR guard sentences (`gh pr list --state open --json headRefName,number --limit 1000`, the limit rule, and head-ref matching) are present unchanged. |
| DoD: root cause identified | Verified | The story comment of the reproduction on `09e869c` shows the bullet named no command and no comparison with the merge-evidence tip. |
| DoD: fix verified against the original failing case | Verified | AC 1 and AC 2 above, on the same bullet that failed. |
| DoD: regression protection | Verified | `test_a_remote_branch_tip_is_read_again_by_command_before_its_delete` pins the read, the comparison, the immediate delete and the failed or absent second read, and `test_the_remote_delete_names_the_exact_branch_ref` pins the full-ref delete. Both pass at the build. |
| DoD: independently reviewed | Verified | The PR 204 review of record names `489d96f3cacea1248e514a4560bdd92ffba1b64c` in its first line and as its `commit_id`, by Codex GPT-6 Sol with DeepSeek V4 Pro adjudicating, with no open finding. |
| DoD: docs updated | Verified | The bullet states why the delete names the full ref and why the window between the read and the delete is accepted. |
| DoD: no new regressions | Verified | `uv run pytest -q` at the build: 1715 passed. CI `ci` succeeded on `489d96f`, `a658d16` and `da295a4`. In the git probe the short `git push origin --delete feature/SKL-9-b` fails with "matches more than one" when a same-named tag exists, while the full-ref delete exits 0 and leaves the tag. |

Closing decision: Done, once this evidence merges.
