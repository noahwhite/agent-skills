<!-- GENERATED from shared/linear.md by scripts/vendor_shared.py. Edit the source, then rerun the script. -->

# Linear and issue lifecycle discipline

Read this before triaging, updating, estimating, closing, or filing Linear issues and epics.
The team is `profile.tracker.team_key`; state and label names come from `profile.tracker.states.*` and `profile.tracker.labels.*` (see `references/profile.md`).
The `linear` CLI (schpet/linear-cli) is the primary tool; the Linear MCP server is the fallback when a CLI command fails.

## Status lifecycle

- Follow the flow `profile.tracker.states.in_progress` -> `profile.tracker.states.in_review` (PR open) -> `profile.tracker.states.in_deployment_review` (build deployed to the target environment) -> `profile.tracker.states.done`.
  Never jump straight to done.
- ⛔ Never mark an issue done on PR merge alone.
  A merge is not a deployment; verify the acceptance criteria in the deployed environment first.
- ⛔ Never move an issue to deployment review on merge.
  Leave it in review between merge and deploy; move it once the deploy has landed the build in the target environment.
- ⛔ Never advance an issue because a docs-only or adjacent PR merged; advance only when the merged PR implements the issue's own criteria.
- Do not rely on the tracker's GitHub integration to advance status.
  Drive every transition yourself, then read the issue back (`linear issue view ABC-123`) to confirm it.
- Driving transitions yourself does not mean asking first.
  Once every AC and DoD item is ticked and verified in the environment, move the issue to done.
- Move an issue to in progress the moment its branch is created, before writing code.
- An issue waiting on an external precondition goes to `profile.tracker.states.blocked`, with the reason in the body, never partially done.

## Completion (AC and DoD checkboxes)

- Ticking the Acceptance Criteria and Definition of Done checkboxes in the description is the completion record.
- ⛔ Never mark or call an issue done while any AC or DoD box is unticked.
  ⛔ Never pre-tick a box; tick only after observing the behavior in the deployed environment.
- To tick in bulk, a replace-all of `- [ ]` with `- [x]` avoids rewriting the description, but it flips every box.
  First confirm the only unticked boxes are the items you verified; otherwise patch each verified line individually.
- When every item is objectively satisfied, tick the boxes and set done in the same act.
  Ask only when an item is unmet or ambiguous.

## Triage and Definition of Ready

- Issues may be created in `profile.tracker.states.triage` or `profile.tracker.states.backlog`.
  Before in progress, finish triage: priority, estimate, assignee, and every DoR box.
- ⛔ `linear issue view` and `linear issue view --json` return no relations field, so triage from them misses every blocks and blocked-by edge.
  Enumerate relations with `linear issue relation list <ID>`, which prints both directions under "Outgoing" and "Incoming" with each relation's type.
  The Linear MCP server's get_issue tool (its response includes `relations`) and the GraphQL API also return them:

  ```graphql
  issue(id: "ABC-123") {
    relations        { nodes { type relatedIssue { identifier state { name } } } }
    inverseRelations { nodes { type issue        { identifier state { name } } } }
  }
  ```

  In the GraphQL response, a blocker appears as an `inverseRelations` node of type `blocks` (the other issue blocks yours) or a `relations` node of type `blocked by`.
  Read both lists and write down every blocker with its state before touching the DoR.
- The DoR item "no blocking issues or unresolved external dependencies" covers external unknowns and known blockers alike; leave it unticked until every blocker is done.
  Its scope-ownership clause fails separately when another issue already owns the work.
- ⛔ The relation graph and the DoR must never disagree.
  If a blocker is not done, either leave the DoR box unticked and keep the issue in backlog or blocked, or, only when that blocker does not gate this issue's criteria, downgrade the edge from `blocks` to `related` with a dated justification comment in the same action.
- ⛔ Never move an issue with that box unticked to `profile.tracker.states.ready`.
  If only part is pickable, split the unblocked part into its own issue.
- Say "refined" and "refinement", not "groomed" or "grooming".

## Estimation and slicing

- Estimates use `profile.tracker.estimate_scale`.
  Only user stories and maintenance work get estimates; spikes carry a timebox instead, and bugs and investigations are unestimated.
- ⛔ Split a story estimated at 8 points or more (or the scale's equivalent) at refinement, without asking, and present the slices.
  Keep the original issue for the core slice, create siblings for the rest, and wire blocked-by or related edges.
- ⛔ Never split an issue at close time to carve off unfinished work; that is status laundering.

## Acceptance criteria and scope

- An issue delivers a complete feature the user can reach in the running environment.
  Bake reachability (routing, TLS, the deploy actually delivering the artifact) and any access gate into the criteria.
- Build each issue for every environment in `profile.environments` up front; promotion only tests, it never adds code.
  Gate a real production safety concern instead of scoping down to one environment.
- Making a synchronous external call on a request path non-blocking belongs to the issue that introduces the call, not to a later hardening issue.
- When the user decides no production promotion is scheduled and the only unticked items are later-environment legs, delete those lines, add an italic dated note naming who decided, tick the rest, and set done.
  Record the deferred steps in the epic.
- ⛔ A deployment-review finding covered by an existing issue's criteria reopens that issue: move it back to in progress, amend the criteria with a dated note, and run it through PR, review, merge, deploy, and deployment review again.
  File a new issue only when no existing criterion covers the behavior.
- `profile.tracker.labels.rtb` is only for maintenance of existing systems (CI fixes, dependency upgrades, config corrections, observability on running services).
  New capability is `profile.tracker.labels.feature`, even when it is docs, alerting, or hardening.
- When asked to preserve a broken state so a fix can be verified, file the tracking issue in the same turn with a "do not clean up until verified" note.

## Epics

- An epic is a Linear project.
  When an issue moves to in progress, move its epic to in progress too if the epic is still in backlog or planned.
- ⛔ Never attach an issue to a completed or canceled epic.
  Check the epic's status first; if it is closed, create the issue without a project.
- New epics follow `profile.tracker.epic.*` (name prefix, icon, label, size labels) with lead `profile.tracker.epic.lead`; the `linear-epic` skill has the template.

## Cycles

- Setting a cycle on a backlog issue may make Linear advance its state automatically (for example to the ready state), and reverting the state can drop the cycle.
- Set cycles deliberately during sprint planning, never as a side effect of triage, and read the state back after setting one.

## Filing issues

- ⛔ Load the matching filing skill and follow it; never copy structure from sibling issues:
  `linear-user-story`, `linear-bug`, `linear-spike`, `linear-investigation`, `linear-epic`.
- Search the team backlog and existing epics before creating (`linear issue list` with a query, or the Linear MCP server's list_issues tool with a filter); the issue may already exist.
- Assign every new issue to `profile.tracker.assignee`.
  Filter by `profile.tracker.assignee_email`, never by display name, since two accounts can share one.
- When `profile.tracker.agent_stamp` is true, comment `Worked by agent <session label> at <YYYY-MM-DD HH:MM> UTC` on each issue you pick up, before coding.
  The session label is defined in `references/runtimes.md`.
- When you investigate an incident, file an investigation issue to record diagnosis, root cause, and follow-ups, even when the fix lands elsewhere.
- ⛔ Verify an issue key exists and matches the work before putting it in a branch, commit, or PR title; never guess a number.
  Reactive fixes usually have no issue yet: file the bug first, then reference it.

## Linear MCP fallback

- Tool names: save_issue, get_issue, list_issues, save_project, get_project.
- The status field of save_issue is `state` (for example `state: "Done"`), not `status` or `stateId`; wrong names silently do nothing.
- Tools take `team` as the team name (`profile.tracker.team_name`); the CLI takes `--team` with `profile.tracker.team_key`.
- Use `project:` and `assignee:` (not `projectId:` or `assigneeId:`); `labels:` takes names.
  Create with team, title, and description only, then update by id to set project, assignee, labels, state, priority, and estimate.
