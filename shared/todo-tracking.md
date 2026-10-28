# Fine-grained todo tracking

Every skill tracks its work on a todo list the user can see.
The list is the visible record of the run: how many steps there are and where you are in them.
`references/runtimes.md` maps the todo list, subagents, and the scratch directory to your runtime's tools.

## Rules

1. **Create the list first.**
   Before the first investigation, edit, command, or delegation, create the todo list.
   Do not skip it because the task looks small.
2. **One item per concrete step**, not per phase.
   Good: "reproduce the 500 on dev", "write failing test for slice 2", "review round 1", "dispatch the dev deploy", "verify AC 3 on dev", "wait for CI on PR head".
   Bad: "implement", "review", "deploy".
   Each investigation, repro, slice, test, gate round, dispatch, deploy, verification, and wait is its own item.
3. **Update the list before you move on.**
   Mark the finished item completed and put the next item in progress as soon as that step's outcome is observed, before starting the next step.
   Batching those two updates, or leaving a stale in-progress item while the next step runs, is forbidden.
   Exactly one item is in progress whenever a next item exists; when none does, none is.
4. **Grow the list as work appears.**
   A new finding, remediation round, blocker, or follow-up gets an item when it is discovered, before that step starts.
   Do not delete items that turned out unnecessary; mark them completed with a short note, or drop them only if they were never started.
5. **An item is completed only when its outcome was observed** (test output seen, run concluded, state read back), not when the command was issued.
6. **Finish the list before reporting.**
   Write the final report only after every item is completed or explicitly noted as not done.

## Subagents

Subagents use checklist files whether or not a runtime exposes a todo tool to them.
Every brief you hand a subagent includes a "Track your work" paragraph requiring a checklist file at `<scratch directory>/<agent-label>/<agent-label>-todo.md`.
`<scratch directory>` is the one scratch directory the session created for its lifetime (`references/runtimes.md`, Scratch files), never a fixed path under the base directory, and `<agent-label>/` is the subdirectory you create inside it for that subagent.
Hand a voter, engineer, or QA agent only its own subdirectory, never the session's scratch directory or another role's files (`references/runtimes.md`, Scratch files); its checklist lives in that subdirectory.
The brief gives the checklist's full path, and the subagent writes it exactly there, without adding `<agent-label>/` to the directory it was handed.
The checklist file has:

- `- [ ]` and `- [x]` items, one per concrete step, with the current step marked `(in progress)`.
- Written before any work starts and updated at every step, including items added as work appears.

Whenever you check the subagent's status, read that file from the subagent's subdirectory and mirror it into your own todo list, so the list shows its real steps.

## Missing todo tools, including primary sessions

Whether the todo tool exists at all depends on the runtime and its configuration; some ship it off by default or behind an experimental flag, and a harness may still not expose it.
Consult `references/runtimes.md` for the version-specific mapping; do not assume a tool exists from configuration alone.
When the primary session has no todo tool, create a checklist file at `<scratch directory>/<session-label>-todo.md` before starting, using the same item granularity and `(in progress)` marker as a subagent.
`<scratch directory>` is the one per-session scratch directory (`references/runtimes.md`, Scratch files), never a fixed path under the base.
Tell the user its path and update it at every step; this file is the visible plan and the place to mirror delegated checklists.
Do not block or ask for a runtime reconfiguration merely because the todo tool is unavailable.
Tracking remains mandatory; only the storage mechanism changes.

## Seed lists

Starting points only; split further as the task demands.
Every seed list below carries one rule: update the list after each step's outcome, before the next step starts.

- **engineering-workflow:** triage the issue, read the code, one item per slice (failing test, implementation, green run), pre-PR gate preflight, each gate round, open PR, each review round, each remediation, CI green, merge, deploy, verify in the environment, each status move.
- **persona-platform-sre:** read primary-source running state, one item per IaC change and per test, plan and apply per stack, each dispatch, each wait on a run, verification of running state, cleanup of any debris.
- **persona-product-owner:** read the issue and its relations, one item per DoR box, estimate, slice or split, each status move, each AC and DoD tick after observation, epic update.
- **qa-verification:** read AC and DoD, one item per acceptance criterion and per DoD box (verify, capture evidence), each environment setup, evidence PR, the closing status decision.
- **cleanup:** read the named story keys, resolve each key against the tracker, the inventory report, the hosted-evidence decision (the capability row or the skip), each removal, each tracker attachment, the refusal comment, and the final report.
- **persona-scrum-master:** read the cycle and its issues, one item per sprint-planning check, the cycle-description update, the issue-to-cycle write and each state read-back, the standup report sections (WIP, aging, blockers), the sprint-review evidence rollup, each retro section and action item, the velocity/burnup values and carry-over reason, each DoR and DoD box checked, each hand-off.
- **persona-release-manager:** read `profile.git.promotion` and the promotion set, one item per included issue and readiness check, each missing-evidence stop, the promotion PR, each review round and finding, the review of record, the merge, each deploy hand-off, each promoted issue's post-deploy evidence, each failure decision (reopen, bug, or rollback), each epic rollback note, and each status hand-off.
- **persona-architect:** read the story or spike and the records already in `profile.decisions.dir`, one item per record written, supersede edit, issue link, review round, and hand-off.
- **story-refinement:** read the story and its relations, one item per voter input, the reconciliation and each accept round, each point value, the SM/EM sizing context, the high/low discussion and re-vote, each split and slice estimate, each PO tracker write and read-back, the anchoring check, the refinement and pointing records, and, only when the `metrics` switch is on, record invocation start (metrics on) and collect metrics.
- **persona-staff-engineer and persona-staff-devops:** see each skill's step 0.
- **story-to-done:** see the skill's step 0.
