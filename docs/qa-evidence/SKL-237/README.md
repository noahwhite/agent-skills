# SKL-237 QA evidence

## QA round 1

Date: 2026-11-13 UTC, independent QA round 1.
Build under test: `main` at `eb8ec19a0e876c313b501de1697f3ca30239efd3`, the squash merge of PR 225, whose reviewed head `0d12eaf718e3983ff5bd714b21ed1f315238160f` has an identical tree.
Base: `954fb58`, the parent of the merge.
Environment: none; the profile sets `environments: []`, so the lanes are the repository (a detached worktree of the build), GitHub and the tracker.
Fixtures: the four scratch issues the PR names, SKL-291 (Bug), SKL-292 (Investigation, RTB), SKL-293 (Spike) and SKL-294 (User Story, Improvement), read back from the tracker.
The raw output is attached to SKL-237 as `SKL-237-qa-round-1-assertions.txt`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| B1: type check | Verified | Step 1 item 3 carries every clause, in roster, type, preflight, voter order; details below. |
| B2: refinement only | Verified | The "Unestimated issue types" section and every passage that names a pointing outcome; details below. |
| B3: content per type | Verified | The Content per type and Definition of Ready verdict bullets; details below. |
| B4: priority and state | Verified | The Priority and Ready gate bullets; details below. |
| B7: records and todo | Verified | The three record lines and the seed line by exact substring; details below. |
| B8a: tests and proof | Not met | The tests and the scratch runs hold, but PR 225 quotes the Triage `State:` line for SKL-291 only; details below. |
| B9: regeneration and gate | Verified | `vendor_shared.py --check` exit 0, the suite passes on the build, and CI passed on the reviewed head and on `main`; details below. |
| DoD: all acceptance criteria met | Not met | B8a. |
| DoD: tests written and passing | Verified | B8a tests and B9. |
| DoD: independently reviewed | Verified | The last review of record names `0d12eaf718e3983ff5bd714b21ed1f315238160f` in its first line and as its `commit_id`, the merged head. |
| DoD: docs updated | Verified | The change is the skill text itself, plus the README row for `story-refinement`. |
| DoD: verified in a deployed environment | Not applicable | The profile defines no environments, so the build was verified on `main`. |
| DoD: no critical bugs or regressions | Verified | CI passed on the reviewed head (run 43476178093) and on `main` (run 43477463570). |

Details:

- B1:
  - Step 1 item 1 reads the story "including its labels".
  - Item 3 sits after the roster check (item 2) and before the tracker-write preflight (item 4) and the voter launch (item 6), and states that a type stop posts no comment.
  - It resolves the four keys `user_story`, `bug`, `investigation` and `spike`, and an unset key stops with `needs input` naming the key in every ceremony; all four are keys of `profile/schema.json`.
  - `user_story` wins over any type label, two or more type labels without it stop with `needs input` naming the labels, other co-labels do not count, and no type label runs as `type: estimated`.
  - The differing-team rule confirms the four labels, and the todo list records `type: <Bug|Investigation|Spike|estimated>` and drops every Stage 2 item.
- B2:
  - The Refinement only bullet skips every Stage 2 activity the AC lists, and the `Pointing skipped` line is stated verbatim.
  - "not accepted" replaces "unpointed", Step 2 item 7 authors no unpointed record for these types, and the round 2 Accept round result is the stop record.
  - The overview, Step 2 items 4 and 7 with Outputs and Stop, Records, Metrics Order, the Closing message and the Read first todo bullet each state the unestimated reading.
  - The Metrics Order and "Stop before a record" rules cover both outcomes, with "pointing record" read as "refinement comment".
- B3:
  - The section "Unestimated issue types" names the Bug, Investigation and Spike content as the AC words it.
  - The Definition of Ready verdict reads "template has no Definition of Ready".
- B4:
  - Priority is decided and read back on an accepted and a "not accepted" outcome alike.
  - The ready gate lists every AC condition, including the filing template's own bracketed placeholders in each named evidence section.
  - When the gate fails, an issue in backlog stays there and an issue in ready moves back to backlog, each with a `State:` line naming the unmet condition; an issue in progress or later keeps its state and its `State:` line reads that retained state with each unmet condition.
  - A move to ready reads "ready: all conditions met".
- B7:
  - `references/refinement-record.md` has the `Pointing skipped` line, the per-type `Outcome` reading and the `State:` line.
  - The story-refinement seed line in `shared/todo-tracking.md` ends with the AC's omit-and-keep sentence verbatim, and the vendored copy matches.
- B8a:
  - `tests/test_story_refinement.py` pins each rule through `section()`, `bullet()` and `process_item()`, and the fixture table has the Bug, Investigation, Spike and User Story rows, both B1 stops, and `user_story` with one and with two type labels.
  - The tracker shows the runs: SKL-291, SKL-292 and SKL-293 each have estimate null, a `Pointing skipped` line in the refinement comment and a Triage `State: ready: all conditions met` line; SKL-294 has estimate 2 and a pointing record; all four are Canceled.
  - Gap: the AC asks the PR to quote the `Pointing skipped` line, the Triage `State:` line and the Closing outcome from each run.
  - The PR 225 E2E table quotes the `State:` line for SKL-291 only, not for SKL-292 or SKL-293, and elides each `Pointing skipped` line to `(...)`.
- B9:
  - `refinement-record.md` opens as hand-written, with no generated header.
  - `uv run --locked python scripts/vendor_shared.py --check` exited 0 on the build.
  - `uv run --locked pytest -q` passed on the build (2097 passed).
  - CI run 43476178093 on the reviewed head and run 43477463570 on `main` passed.

Closing decision: SKL-237 moves back to In Progress for the B8a PR quotes.
