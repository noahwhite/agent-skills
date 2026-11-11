# SKL-249 QA evidence

## Round 1

Date: 2026-11-11 UTC, independent QA round 1.
Story: SKL-249 - the `cleanup` description claims it refuses all unmerged work despite the recorded instruction.
Build under test: `main` at `da295a43a92deeaf0fc6f939c3bc182826ad6cb7`, which contains the squash merge of PR 200 (`f75da71a47000335e9b89997c219528f1f6b8e14`), whose reviewed head is `87774112cfe4ed9ac85297d95e0e38fa593ca694`.
Environment: the profile lists no environments, so every item was checked on the repository, GitHub and tracker lanes.
The test suite, the skill validator and the OpenCode discovery smoke check ran in a detached worktree of the build, and the mutation spot-check ran in a second one.
Fixtures: none; the delivered skill text and its tests are the surface under test.

There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw output is attached to SKL-249 as `SKL-249-qa-assertions.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: no unqualified claim | Verified | The frontmatter `description` no longer ends "refuses anything still holding unmerged work."; it continues "unless the invocation carries an explicit recorded instruction naming it." |
| AC2: names the recorded instruction as the one exception | Verified | The description names the explicit recorded instruction and restates none of step 3's scope rules. |
| AC3: trigger phrases and discovery checks | Verified | PR 200 changes only the first description sentence; the "Use when" and "Not for" sentences are unchanged. `skills-ref validate skills/cleanup/` reports a valid skill, and `scripts/smoke-opencode.sh` reports all 18 skills discovered in all six layouts. |
| DoD: root cause identified | Verified | SKL-245 added the recorded-instruction path to step 3 without updating the description; the description itself was corrected. |
| DoD: fix verified against the original failing case | Verified | The text before and after PR 200 is compared in the attached output. |
| DoD: regression protection | Verified | `test_description_names_the_recorded_instruction_as_the_one_exception` passes on the build and fails when the pre-fix description is restored. `git status` was clean after restore. |
| DoD: independently reviewed | Verified | The PR 200 review of record names `87774112cfe4ed9ac85297d95e0e38fa593ca694` in its first line and as its `commit_id`, the merged head, with reviewer Codex GPT-6 Sol and adjudicator DeepSeek V4 Pro. |
| DoD: docs updated | Verified | The delivered change is the skill description itself; the test comment records why the qualifier exists. |
| DoD: no new regressions | Verified | `uv run pytest -q` at the build reported 1715 passed. CI `checks` and `discovery` succeeded on `f75da71` (run 42956397909) and on the build (run 43039747124). |

Closing decision: Done, once this evidence merges.
