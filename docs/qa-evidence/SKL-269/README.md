# SKL-269 QA evidence

## QA round 1

Date: 2026-11-13 UTC, independent QA round 1.
Path: `no-deployment`, selected under "The run's path" because no brief stated one, the story has no Spike label and its title starts `[User Story]`, and `.agent-skills/profile.yaml` sets `environments: []`.
Target: merged commit `8d41c4097c8f60593922de1fbef9b2eede2f1561` on `main`, the squash merge of PR https://github.com/noahwhite/agent-skills/pull/235, confirmed with `git merge-base --is-ancestor` after a fetch.
Its reviewed head `d655087191148ddd5c762a66de9c0388324cde0c` has the same content for both changed files.
Environment and deployed build SHA: none on this path.
Fixtures: none; the probes read the skill at the target and run the repository's own tests and guards.
The raw output is attached to SKL-269 as `SKL-269-qa-round-1-assertions.txt`; there is no visual surface, so no screenshot applies.
The blockers SKL-162 and SKL-282 are Done, and their merges `77abaf1` and `1f6fc99` are ancestors of the target.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: path conditions | Verified | The ask cases, selections and brief rule match `engineering-workflow` step 1; details below. |
| AC2: QA without a deployed environment | Verified | Targets, records, DoD ruling, intro and brief scope present; details below. |
| AC3: deployed path regression | Verified | No other test module was edited, and all 8 that read the skill pass; details below. |
| AC4: pins | Verified | 32 pins, each mutation-proven in the PR, 5 re-proven by QA; details below. |
| AC5: repository guards | Verified | Every guard passed on the target and in CI; details below. |
| DoD: all acceptance criteria met | Verified | AC1 to AC5. |
| DoD: tests written and passing | Verified | AC4 and AC5. |
| DoD: independently reviewed | Verified | Review 5898202942 names `d655087191148ddd5c762a66de9c0388324cde0c` in its first line and as its `commit_id`, the merged head, with 0 blocking findings. |
| DoD: docs updated | Verified | The change is the skill text. |
| DoD: verified in a deployed environment | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | CI passed on the reviewed head (run 43509531190) and on `main` at the target (run 43510477897). |

Details:

- AC1:
  - "## The run's path" holds the four ask cases and the three selections byte for byte as `skills/engineering-workflow/SKILL.md` lines 75-78 and 86-88.
  - The precedence, answer, no-inference, brief-governs and governs-the-run sentences are identical too.
  - QA's wording differs only where it names what waits: "test nothing until answered" and "before any verification runs".
  - The spike selection cites "Team resolution" in `references/linear.md`, which holds the differing-team rule.
- AC2:
  - "The environment under test" names the `no-deployment` target (the merged commit, confirmed on `profile.git.integration_branch`) and the `spike` target (each deliverable the step 12 note links).
  - It records the merged commit SHA on `no-deployment`, and each deliverable's link and commit SHA, or no commit, on `spike`.
  - It states that neither path requires or records an environment or a deployed build SHA, and rules the deployed-environment DoD line not needed with the path as the reason.
  - The intro scopes the deployed wording to the `deployed` path, permits inspecting committed artifacts without replacing the code-review gates, and lets a brief state the path and its target.
  - `git diff --numstat 8d41c40^ 8d41c40` shows 43 added and 0 removed lines in the skill, so the `deployed` text and the evidence rules are unchanged.
- AC3:
  - `grep -l qa-verification tests/` returns 8 modules, and the merge edits only `tests/test_no_deployment_path.py`, removing 3 docstring lines.
  - Those 8 modules pass on the target (526 passed).
- AC4:
  - Each of the 32 non-blank lines the PR adds to the skill is one of the 32 pins in `tests/test_no_deployment_path.py`, enforced by the closed path-section test, the added-blocks test and the sha256 seal of the remaining text.
  - The seal's base blob equals the merge parent's blob (`d1eba16`).
  - No existing pin or fragment assertion is replaced, so no replacement comment is due.
  - The PR description's table shows each of the 32 deletion mutants failing its own test id.
  - QA deleted 5 pinned sentences in turn at the target, and each failed its own test id with the counts the PR table lists; unmutated, the module passes (116 passed).
- AC5:
  - On the target, `uv run --locked pytest -q` passed (2236 passed) and the public leak scan reported no hits.
  - `skills-ref validate skills/qa-verification/` reported a valid skill.
  - `bash scripts/smoke-opencode.sh` discovered 18 skills in each of its 6 layouts.
  - The private-pattern half of the leak scan runs only in CI.
  - CI run 43509531190 on the reviewed head passed `checks` (with the leak scan `--require-private`) and `discovery`.
  - CI run 43510477897 on `main` at the target passed both jobs.

Closing decision: SKL-269 moves to Done once this evidence PR merges.
