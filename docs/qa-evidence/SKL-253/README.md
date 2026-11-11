# SKL-253 QA evidence

## Round 1

Date: 2026-11-11 UTC, independent QA round 1.
Story: SKL-253 - a failed branch tip read in the `cleanup` merged-PR evidence is never merge evidence.
Build under test: `main` at `da295a43a92deeaf0fc6f939c3bc182826ad6cb7`, which contains `a658d16dae1b547c7c6f9ae5777db1e732ca6aee`, the squash merge of PR 204, whose reviewed head is `489d96f3cacea1248e514a4560bdd92ffba1b64c`.
The two files PR 204 changes are identical at that head and at the merge, and the later commit `da295a4` changes neither the step 3 sentences below nor their tests.
Environment: the profile lists no environments, so every item was checked on the repository, GitHub and tracker lanes.
Method: a text probe asserted the step 3 sentences of `skills/cleanup/SKILL.md` at the build against the pre-fix text at `f75da71`, and a git probe ran the tip read against the fixture below.
Fixtures:

- A synthetic bare origin and clone with `main` as the integration branch and no branch `missing-branch`.

There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw output is attached to SKL-253 as `SKL-250-253-text-probe.txt` and `SKL-250-253-git-probe.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| AC 1: the bullet states what a non-zero tip read means | Verified | At `f75da71` the merged-PR bullet had no failed-read rule. At the build it says "A `git rev-parse refs/heads/<branch>` that exits non-zero is never merge evidence, whatever it printed". In the git probe `git rev-parse refs/heads/missing-branch` exits 128 and prints `refs/heads/missing-branch` on stdout, the output the rule rejects. |
| AC 2: a failed read refuses the branch and deletes nothing | Verified | The same bullet continues "the report names the branch as unreadable with the exit status, the branch is refused, and nothing is deleted for it." |
| AC 3: successful comparison and remote evidence path unchanged | Verified | The `gh pr view <n> --json state,headRefOid` comparison sentence is unchanged from `f75da71`, and in the git probe a present branch reads exit 0 with its SHA. The remote-branch rule that containment is never merge evidence and only a merged PR whose head commit is the remote tip is, is unchanged. |
| DoD: root cause identified | Verified | The story comment of the reproduction shows the read exiting 128 while still printing its argument, with no rule saying that outcome is not evidence. |
| DoD: fix verified against the original failing case | Verified | AC 1 and AC 2 above, against the same exit-128 read. |
| DoD: regression protection | Verified | `test_a_failed_local_tip_read_is_never_merge_evidence` pins the sentence inside the merged-PR bullet. It passes at the build. |
| DoD: independently reviewed | Verified | The PR 204 review of record names `489d96f3cacea1248e514a4560bdd92ffba1b64c` in its first line and as its `commit_id`, by Codex GPT-6 Sol with DeepSeek V4 Pro adjudicating, with no open finding. |
| DoD: docs updated | Verified | The rule says "whatever it printed", the non-obvious part, since the failed read still prints to stdout. |
| DoD: no new regressions | Verified | `uv run pytest -q` at the build: 1715 passed. CI `ci` succeeded on `489d96f`, `a658d16` and `da295a4`. |

Closing decision: Done, once this evidence merges.
