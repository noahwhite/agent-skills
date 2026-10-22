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
3. **Exactly one item in progress** at a time.
   Mark it completed the moment it is done, never in a batch at the end.
4. **Grow the list as work appears.**
   A new finding, remediation round, blocker, or follow-up gets an item when it is discovered.
   Do not delete items that turned out unnecessary; mark them completed with a short note, or drop them only if they were never started.
5. **An item is completed only when its outcome was observed** (test output seen, run concluded, state read back), not when the command was issued.
6. **Finish the list before reporting.**
   Write the final report only after every item is completed or explicitly noted as not done.

## Subagents

Subagents have no todo list.
Every brief you hand a subagent includes a "Track your work" paragraph requiring a checklist file at `<scratch directory>/<agent-label>-todo.md`:

- `- [ ]` and `- [x]` items, one per concrete step, with the current step marked `(in progress)`.
- Written before any work starts and updated at every step, including items added as work appears.

Mirror that file into your own todo list whenever you check the subagent's status, so the list shows its real steps.

## Seed lists

Starting points only; split further as the task demands.

- **engineering-workflow:** triage the issue, read the code, one item per slice (failing test, implementation, green run), pre-PR gate preflight, each gate round, open PR, each review round, each remediation, CI green, merge, deploy, verify in the environment, each status move.
- **persona-platform-sre:** read primary-source running state, one item per IaC change and per test, plan and apply per stack, each dispatch, each wait on a run, verification of running state, cleanup of any debris.
- **persona-product-owner:** read the issue and its relations, one item per DoR box, estimate, slice or split, each status move, each AC and DoD tick after observation, epic update.
- **qa-verification:** read AC and DoD, one item per acceptance criterion and per DoD box (verify, capture evidence), each environment setup, evidence PR, the closing status decision.
- **persona-scrum-master:** read the cycle and its issues, one item per sprint-planning check, the cycle-description update, the issue-to-cycle write and each state read-back, the standup report sections (WIP, aging, blockers), the sprint-review evidence rollup, each retro section and action item, the velocity/burnup values and carry-over reason, each DoR and DoD box checked, each hand-off.
- **persona-release-manager:** read `profile.git.promotion` and the promotion set, one item per included issue and readiness check, each missing-evidence stop, the promotion PR, each review round and finding, the review of record, the merge, each deploy hand-off, each promoted issue's post-deploy evidence, each failure decision (reopen, bug, or rollback), each epic rollback note, and each status hand-off.
- **persona-architect:** read the story or spike and the records already in `profile.decisions.dir`, one item per record written, supersede edit, issue link, review round, and hand-off.
- **story-refinement:** read the story and its relations, one item per voter input, the reconciliation and each accept round, each point value, the SM/EM sizing context, the high/low discussion and re-vote, each split and slice estimate, each PO tracker write and read-back, the anchoring check, the refinement and pointing records.
- **persona-staff-engineer and persona-staff-devops:** see each skill's step 0.
- **story-to-done:** see the skill's step 0.
