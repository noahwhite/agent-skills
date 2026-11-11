# SKL-252 QA evidence

## Round 1

Date: 2026-11-11 UTC, independent QA round 1.
Story: SKL-252 - `cleanup` containment checks and loss listings read the remote-tracking ref, so a same-named tag never answers.
Build under test: `main` at `da295a43a92deeaf0fc6f939c3bc182826ad6cb7`, which contains `a658d16dae1b547c7c6f9ae5777db1e732ca6aee`, the squash merge of PR 204, whose reviewed head is `489d96f3cacea1248e514a4560bdd92ffba1b64c`.
The two files PR 204 changes are identical at that head and at the merge, and the later commit `da295a4` changes neither the step 3 sentences below nor their tests.
Environment: the profile lists no environments, so every item was checked on the repository, GitHub and tracker lanes.
Method: a text probe asserted the step 3 sentences of `skills/cleanup/SKILL.md` at the build against the pre-fix text at `f75da71`, and a git probe ran the containment and loss-listing commands against the fixture below.
Fixtures:

- A synthetic bare origin and clone with commits A then B on `main`, pushed so `refs/remotes/origin/main` is B.
- A local tag `origin/main` on A.

There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw output is attached to SKL-252 as `SKL-250-253-text-probe.txt` and `SKL-250-253-git-probe.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| AC 1: no short `origin/<integration_branch>` in step 3 | Verified | At `f75da71` step 3 held three short `origin/<profile.git.integration_branch>` reads. At the build step 3 holds no `origin/` that is not preceded by `refs/remotes/`. |
| AC 2: checks read the remote-tracking ref despite a same-named tag | Verified | All three reads, the two `git merge-base --is-ancestor` checks and the `git log --oneline` loss listing, name `refs/remotes/origin/<profile.git.integration_branch>`, and the rule says a tag of the same name never answers. In the git probe the short `origin/main` resolves to A: `git merge-base --is-ancestor B origin/main` exits 1 and `git log --oneline origin/main..B` lists B. The full ref gives exit 0 and an empty listing. |
| AC 3: `git fetch origin` step and merge-evidence order unchanged | Verified | The sentence "Before each removal other than a persistent-memory note, after `git fetch origin`, establish merge evidence..." is unchanged, containment still requires `git fetch origin` to exit 0, and the order fetch, merged PR, containment is the same as at `f75da71`. |
| DoD: root cause identified | Verified | The story comment of the reproduction shows git resolving the short name through `refs/tags/` before `refs/remotes/`. |
| DoD: fix verified against the original failing case | Verified | AC 2 above reproduces the story's failing case and shows the fixed command answers from the remote-tracking ref. |
| DoD: regression protection | Verified | `test_every_integration_branch_read_names_the_remote_tracking_ref` rejects any short remote-tracking read and requires the three reads to name `refs/remotes/origin/`. It passes at the build. |
| DoD: independently reviewed | Verified | The PR 204 review of record names `489d96f3cacea1248e514a4560bdd92ffba1b64c` in its first line and as its `commit_id`, by Codex GPT-6 Sol with DeepSeek V4 Pro adjudicating, with no open finding. |
| DoD: docs updated | Verified | The containment bullet states why every integration-branch read names the full ref. |
| DoD: no new regressions | Verified | `uv run pytest -q` at the build: 1715 passed. CI `ci` succeeded on `489d96f`, `a658d16` and `da295a4`. |

Closing decision: Done, once this evidence merges.
