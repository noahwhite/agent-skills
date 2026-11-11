# SKL-246 QA evidence

## Round 1

Date: 2026-11-11 UTC, independent QA round 1.
Story: SKL-246 - story-refinement and story-to-done agents do not reliably keep their todo list updated.
Build under test: `main` at `1898fb45efd009a85a09c5e626f1b2502df21319`, the squash merge of PR 197, whose reviewed head is `9a06309376fc8c56299e428471a48d4ebcf60ac8`.
The merge tree and the reviewed head tree are the same tree, `196344dcd9e591f39f6a2bf2da5953894cd3332f`.
Environment: the profile lists no environments, so every item was checked on the repository, GitHub and tracker lanes.
The test suite and the text probes ran in a detached worktree of the build, and the mutation proof ran in a second one.
Fixtures: none; the delivered skill text and its tests are the surface under test.

There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw output is attached to SKL-246 as `SKL-246-qa-assertions.txt` and `SKL-246-mutation-proof.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: pre-fix sessions, cause, re-refinement | Verified | The attachment "SKL-246 AC1 reproduction and cause" records fresh sessions 58d30630 and 21fe2e7b and a 45-session scan with the cause as list discipline. The Fix section was re-refined (accepted in round 2 at 21:47:51 UTC on 2026-11-10) before the first implementation commit at 22:03:21 UTC. |
| AC2: post-fix fresh interactive sessions | Not covered (owner) | It needs one fresh interactive session of each skill on a story the owner chooses, with the transcript scan linked. The container's installed skills (shipped 2026-11-10 04:19 UTC) still carry the pre-fix text, so no post-fix session has run yet. |
| AC3: subagent checklist files | Partly verified, behaviour pending (owner) | Both `story-to-done` briefs keep their "Track your work" paragraph unchanged and name no task tool, and `story-refinement` carries no inline brief before or after. The checklist-writing behaviour needs the AC2 sessions. |
| AC4: list-creation order and the five rules | Verified | The creation sentence leads `story-to-done` step 0 and `story-refinement` "Read first", and every earlier `references/` mention is deferred until after the list. `shared/todo-tracking.md` carries the seed-list granularity, add-an-item, transition, parallel-delegation and closing rules in the Fix section's words, and the exactly-one rule is gone. |
| AC5: unchanged files and no ToolSearch wording | Verified | `shared/runtimes.md` and its vendored copies have no diff, the "Missing todo tools" section is byte-identical, no added or removed line mentions `ToolSearch` or deferred tools, and the "Track your work" lines are identical. |
| AC6: vendoring | Verified | Two runs of `scripts/vendor_shared.py` left the tree clean, `--check` exited 0, and all 18 vendored copies equal the generated header plus the `shared/` source byte for byte. |
| AC7: guard test and mutation proof | Verified | On-disk mutations deleting each of the five rules, reordering the creation sentence after the first `references/` read in each skill, and deleting it in each skill all failed `tests/test_todo_tracking.py`, and the worktree was clean after restore. |
| DoD: root cause identified | Verified | AC1. |
| DoD: fix verified against the original failing case | Not covered (owner) | The story defines this as the AC2 post-fix scan. |
| DoD: regression protection | Verified | AC7. |
| DoD: independently reviewed | Verified | Review 5854367119 names `9a06309376fc8c56299e428471a48d4ebcf60ac8` in its first line and as its `commit_id`; reviewer Codex GPT-6 Sol, adjudicator DeepSeek V4 Pro, no valid findings. |
| DoD: docs updated | Verified | The delivered change is the skill text itself, and the guard tests carry SKL-246 comments. |
| DoD: no new regressions | Verified | `uv run pytest` at the build reported 1708 passed, CI succeeded on the PR head (run 42966660256) and on `main` (run 42967338739), and no other skill's text contradicts the new rules. |

Closing decision: stays In Deployment Review until the owner runs the AC2 sessions on the shipped post-fix skills.
