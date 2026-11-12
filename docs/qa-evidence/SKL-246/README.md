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

## Round 2

Date: 2026-11-11 UTC, independent QA round 2.
Build under test: `main` at `da295a43a92deeaf0fc6f939c3bc182826ad6cb7`, which contains the fix `1898fb45efd009a85a09c5e626f1b2502df21319`.
`skills/story-to-done`, `skills/story-refinement` and `shared/` have no diff between the fix and this build.
The installed skills were shipped at 14:39 UTC and are identical to this build for `story-to-done` and `story-refinement`.
Environment: none; the lanes are the session transcripts, the repository and the tracker.
Fixtures: the owner-run post-fix sessions `ceee87d1` (`story-refinement` on a consumer project's story, started 14:46:59 UTC) and `3554eadc` (`story-to-done` on SKL-83, started 14:47:56 UTC), with their subagents.
The scan uses the AC1 method and columns plus per-call tracking of each list item's state, from a snapshot taken at 14:53:28 UTC.
Neither session had reached its final report at the snapshot, but transcripts are append-only, so the failures below are final.
The raw output is attached to SKL-246 as `SKL-246-qa-round-2-assertions.txt`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1 | Verified (round 1) | Unchanged. |
| AC2: `story-refinement` session | Not met | The list is created at call 2, before the first reference read at call 8. Item #2 is marked completed at call 13 without ever being in progress. Calls 75-80 run with no item in progress. The SM/EM contribution work at calls 87-90 starts before its item #12 goes in progress at call 91, and #12, which is not a delegation, is then in progress alongside voter items #9-#11. |
| AC2: `story-to-done` session | Not met | The list is created at call 2, before the first reference read at call 12. Items #1, #3, #4, #5 and #13 are marked completed without ever being in progress (calls 19, 20, 27, 41 and 48). Calls 11-18 run with no item in progress. Phase item #6 stays in progress alongside #14 and #17, which are not parallel delegations. |
| AC3: briefs | Verified (round 1) | Unchanged on this build. |
| AC3: subagent checklist behaviour | Not met | The `story-to-done` senior engineer first writes its checklist at its call 10, after nine actions, and leaves it stale through call 32. The `story-refinement` PO subagent writes its checklist first but ticks every item in one final write. The `story-refinement` voters never write their own checklist; the facilitator seeds and overwrites it, as the consumer's `story-refinement` overlay prescribes. |
| AC4-AC7 | Verified (round 1) | Re-check on this build: `scripts/vendor_shared.py --check` exited 0 and `tests/test_todo_tracking.py` reported 39 passed. |
| DoD: fix verified against the original failing case | Not met | Items completed without being in progress, and work run with no item in progress, recur in both sessions. |
| Other DoD boxes | Verified (round 1) | Unchanged. |

Against the AC1 baseline, the first todo call moved to call 2 in both sessions (baseline calls 3-22), and the longest untracked run fell to 14 and 8 calls (baseline up to 100 and 88).
Closing decision: SKL-246 reopens to In Progress with dated deployment-review notes on AC2 and AC3, and the fix goes back to `engineering-workflow`.

## Round 3

Date: 2026-11-12 UTC, independent QA round 3, against the rescoped story (hook enforcement, AC1-AC13).
Build under test: `main` at `d2c2b0fba7e49b8479ee9fda1fe93bb52f727a29`, the squash merge of PR 209, whose reviewed head is `5ec94c287c7f476e1998eb7152dee5fc6bae666d`.
The merge tree and the reviewed head tree are the same tree, `44e16c1120a436679abe2328ac1ff2b049da6b1b`.
Environment: none; the lanes are the repository (a detached worktree of the build), GitHub and the tracker.
Fixtures: no fixture accounts apply; AC9 runs on the committed enforcer test fixtures under `tests/fixtures/todo_enforce/`, copied from the AC2 probe.
The raw output, including every mutation proof, is attached to SKL-246 as `SKL-246-qa-round-3-assertions.txt`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: baseline | Verified (round 1) | The attachment "SKL-246 AC1 reproduction and cause" is still linked. |
| AC2: pre-implementation probe | Verified | The probe record was attached at 21:27:37 UTC on 2026-11-11, before the first enforcer commit `38bfda9` at 21:38:30 UTC. It answers (a), (b) and (c) and finds no contradiction with the Fix. Its logging hook was registered through a `--settings` file rather than the user-level settings file, a deviation the record states. |
| AC3: briefs | Verified | The two "Track your work" lines in `story-to-done` are identical to the pre-story text, `story-refinement` carries no inline brief before or after, and neither SKILL.md names a task tool or `ToolSearch`. PR 209 changes neither SKILL.md. |
| AC4: list-creation order and the five rules | Verified | The creation sentence precedes the first `references/` read in both skills, and all five rule phrases are in `shared/todo-tracking.md`. |
| AC5: unchanged files and no ToolSearch wording | Verified | `shared/runtimes.md` and its copies have no diff over PR 209 or over the whole story, and the "Missing todo tools" section is identical. PR 209 adds 45 Markdown lines, none with `ToolSearch` or deferred-tool wording. |
| AC6: `todo-tracking.md` vendoring | Verified | Two runs of `scripts/vendor_shared.py` left the tree clean, `--check` exited 0, and all 18 copies equal the generated header plus the source. |
| AC7: PR 197 guard mutation proof | Verified | Deleting each of the five rules and moving the creation sentence after the first read in each skill all failed `tests/test_todo_tracking.py`. |
| AC8: enforcer vendoring | Verified | Both `scripts/todo-enforce.py` copies equal the generated header plus `shared/todo-enforce.py`, the same convention as AC6. A second vendor run changed nothing, drift in either copy made `--check` exit 1, and none of the 18 SKILL.md files has a `hooks` key. |
| AC9: enforcer tests | Verified | `tests/test_todo_enforce.py` reported 81 passed, with tests for cases (a) to (i) and fixtures recording Claude Code 2.1.322. Five on-disk mutants (the deny, the owner check, the subagent completion, the unreadable task file and the not-in-progress completion) each failed their named test. |
| AC10: README block | Verified | The README registers one enforcer copy for the four events and states what it enforces, in which sessions, that it fails open, and how to remove it. |
| AC11: post-fix interactive sessions | Not covered (owner) | The README block is not in the QA container's user-level settings file, and the installed skills carry no enforcer copy. The sessions also need `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`, since the README states the hook is inert without the task tools. |
| AC12: `claude -p` and no-skill sessions | Not covered (owner) | Same prerequisites as AC11. |
| AC13: guards | Verified | CI run 43125210216 on the PR head passed the tests, the leak scan with private patterns, skills-ref validation and discovery, and run 43126011555 on `main` passed. Locally on the build, the suite reported 1796 passed, the leak scan exited 0, and the smoke script discovered all 18 skills. |
| DoD: root cause identified | Verified | AC1 and round 2. |
| DoD: fix verified against the original failing case | Not covered (owner) | The story defines this as the AC11 scan. |
| DoD: regression protection | Verified | AC7 and AC9. |
| DoD: independently reviewed | Verified | Review 5867064915 names `5ec94c287c7f476e1998eb7152dee5fc6bae666d` in its first line and as its `commit_id`, and was posted at 00:12:15 UTC, before the merge at 00:15:53 UTC. |
| DoD: docs updated | Verified | The README section, `shared/README.md` and the enforcer's docstring. |
| DoD: no new regressions | Partly verified, live half owner | The tests cover sessions without either skill, subagents and sessions without the task tools; the live adjacent paths are AC12. |

Closing decision: stays In Deployment Review until the owner runs the AC11 and AC12 sessions with the README block registered.
