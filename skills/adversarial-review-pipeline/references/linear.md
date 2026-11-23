<!-- GENERATED from shared/linear.md by scripts/vendor_shared.py. Edit the source, then rerun the script. -->

# Linear and issue lifecycle discipline

Read this before triaging, updating, estimating, closing, or filing Linear issues and epics.
The team for an operation on or for an issue named by key is that key's prefix, and `profile.tracker.team_key` is the team only when no issue is named (Team resolution, below).
State and label names come from `profile.tracker.states.*` and `profile.tracker.labels.*` (see `references/profile.md`).
The `linear` CLI (schpet/linear-cli) is the primary tool; the Linear MCP server is the fallback when a CLI command fails.

## Team resolution

- For any operation on or for an issue the caller named by key, the team is that key's prefix (`ABC` in `ABC-123`): the CLI `--team` takes the prefix on a command that accepts `--team` (a command addressed by the issue key, such as `linear issue view <key>`, takes the key and no `--team`), and MCP calls take the team name resolved from that key (the team in the team list, `linear team list` or the Linear MCP list_teams tool, whose key matches the prefix), never `profile.tracker.team_name`.
  A failed resolution stops the step and asks.
- `profile.tracker.team_key` and `profile.tracker.team_name` apply only to operations that name no issue and follow no invoked key: standalone filing, listing or searching the backlog.
- Differing team: when the named issue's team differs from `profile.tracker.team_key`, each profile state or label name (including `profile.tracker.states.ready` and `profile.tracker.states.backlog`, and the labels on split siblings) is used only after it is confirmed on that team with `linear team states <KEY>` and `linear label list --team <KEY>` (whose listing includes the workspace labels), where `<KEY>` is the team key, the issue key's prefix; use the Linear MCP list_issue_statuses and list_issue_labels tools if the CLI fails.
  A missing name, an unknown team or a failed listing stops the step before any write and asks; no other name is substituted.

## Named story keys

- An issue key the owner names explicitly is acted on as written, also when it appears inside an instruction about a different story, and is never treated as a typo for another key.
- When the named story is not yet in the state the action needs, wait, re-read its state, and say that you are waiting; when the instruction contradicts the story's state or another instruction, ask the owner before acting.
- Never substitute another key.
  A missing key is covered by the "never guess" line of the `STORY_ID` argument rule of a skill that takes one, not restated here.

## Status lifecycle

- Follow the flow `profile.tracker.states.in_progress` -> `profile.tracker.states.in_review` (PR open) -> `profile.tracker.states.in_deployment_review` (build deployed to the target environment) -> `profile.tracker.states.done`.
  Never jump straight to done.
- ⛔ Never mark an issue done on PR merge alone.
  A merge is not a deployment; verify the acceptance criteria in the deployed environment first.
- ⛔ Never move an issue to deployment review on merge.
  Leave it in review between merge and deploy; move it once the deploy has landed the build in the target environment.
- On the `no-deployment` and `spike` paths that `engineering-workflow` selects in its step 1, nothing is deployed: the move to deployment review follows the handoff its step 12 defines, and every condition in this file on a deploy or a deployed environment reads as verification against the merged commit, or, for a spike with no tracked-file change, against the deliverables the step 12 note links.
  A spike with no tracked-file change has no PR, so for it every condition in this file on a merged PR reads as the deliverables the step 12 note links.
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
  The estimate applies only to an estimated issue type: a Bug or an Investigation carries no estimate, and a Spike carries a timebox instead.
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
- ⛔ An AC that requires another story's output (an artifact, credential, stack, or behaviour that story delivers) requires a formal blocked-by relation to that story.
  The template DoR box "No blocking stories, no unresolved external dependencies, and no other story already owns this scope" stays unticked until that relation exists and the blocker is in `profile.tracker.states.done`.
  This refines, and does not replace, the relation-graph rules above, including the dated downgrade of a blocker that does not gate the criteria from `blocks` to `related`.
  Before adding the relation, triage checks it creates no cycle; where it would (the other story consumes this one), the product owner or the refinement process sets the delivery order, the cross-story check moves to whichever story that order lands last, and that story gets the blocked-by relations instead.
  An implementing engineer never moves an acceptance criterion between stories to resolve a cycle.
- ⛔ Never move an issue with that box unticked to `profile.tracker.states.ready`.
  If only part is pickable, split the unblocked part into its own issue.
- Say "refined" and "refinement", not "groomed" or "grooming".

## Estimation and slicing

- Estimates use `profile.tracker.estimate_scale`.
  Only user stories and maintenance work get estimates; spikes carry a timebox instead, and bugs and investigations are unestimated.
- `linear issue view --json` omits `estimate`, as it omits relations, even when the issue carries one, and the plain view prints no estimate line.
  Read an estimate with `linear api 'query { issue(id: "ABC-123") { estimate } }'`, or through the Linear MCP `get_issue` with the `estimate` field.
  The team issue list renders it in its estimate column, which is a display path, not a read path for a script.
- ⛔ Split a story whose estimate is above `profile.refinement.point_cap` or is 8 or more, without asking, before it is assigned or work is delegated, and present the slices.
  This is one split rule for an estimate recorded at refinement and for one made outside a ceremony, at filing or triage.
  Keep the original issue for the core slice, create siblings for the rest, and wire blocked-by or related edges.
- ⛔ Split a resulting slice that still meets that trigger again, for at most two split rounds: split round 1 splits the whole story and split round 2 splits the round-1 slices that still meet it.
  This bound supersedes the never-escalate rule of SKL-230.
  Each resulting slice gets its own estimate, made the way the story's was (at refinement, filing or triage), before it is tested against that trigger.
  A slice that cannot be estimated is recorded as unpointed and reported as `needs input` to the owner, naming the story and the slice, and also the derived values when a refinement voter round produced them, as the unpointed variance stop in story-refinement's Split rule does.
  Split along the first boundary that applies, in this order:
  1. the planned PR or slice boundary;
  2. an acceptance criterion;
  3. where one acceptance criterion alone still meets the trigger, that criterion is rewritten at refinement or triage into narrower observable criteria (by artifact, case or environment) that keep the same coverage, and the slice is split along them;
  4. the smallest outcome that can be reviewed, merged and verified on its own, including enabling work such as interface or schema first and behaviour second.

  No rung discards scope, delegates an oversize slice or hands one to the owner as an estimate.
  No slice grows scope: a slice carries only the acceptance criteria, scope and evidence of the story it is split from, and adds no criterion, evidence pass, fixture, test obligation or behaviour that story does not already contain.
  The split comment maps every slice criterion to exactly one criterion of the story it is split from, and so on back to the whole story; several slice criteria may map to one criterion of that story (rung 3).
  The mapping check runs in each split round before any slice is pointed: each slice criterion with no counterpart and each evidence pass, fixture, test obligation or behaviour a slice adds beyond the story it is split from are all named in one `needs input` message, and the round stops before any slice is pointed, so no check that needs a slice value runs.
- ⛔ Bound every split of an estimated story made under the two bullets above (the Bug and Investigation split below gives no slice a point value, so these checks never run on it): after each split round, and before any further split round, slice record or tracker write for the slices, run these checks:
  1. Per-parent bound: each slice's recorded value is strictly below the recorded value of the story it is split from, where a round-1 parent's value is the recorded whole-story estimate and a round-2 parent's value is its round-1 recorded value; the slices of one parent are compared to that parent as a set by the bands below on their sum, and a slice at or above its parent stops with `needs input` naming the parent, the slice, both values and the band.
  2. Whole-story sum: the sum of the recorded values of the current leaf slices (a slice that is split again is replaced by its sub-slices) is compared to the original whole-story recorded estimate by the bands below.
  3. Round cap: a slice that still meets the split trigger after split round 2 stops with `needs input` naming the slices and their values, before a third split is made, and no third-round split, estimate, record or tracker write happens.

  The bands compare a sum to its base (the parent's value in check 1, the original whole-story recorded estimate in check 2): above 1.5 times the base stops with `needs input`; above 1.0 times and up to and including 1.5 times proceeds with a warning in the split comment that a human reads at triage; at or below 1.0 times proceeds with no flag.
  A slice's recorded value is the lower value of a within-one-step consensus (story-refinement Split rule), so each sum is formed from the lower-consensus values, and when the lower and the higher sums fall in different bands the lower-consensus band governs.
  Every band stop or warning names the sum both ways (with each slice's lower and with its higher consensus value, the two values a within-one-step consensus spans, which are one value otherwise), the band of each sum, both bounds (1.0 times and 1.5 times the base) and the round.
  The checks run in the order listed, the round cap after split round 2 only, and every applicable check runs before any stop is enforced: all failures of the round are reported in one `needs input` message and all its warnings in one split-comment entry, which a round that stops also carries in that message and posts with the split comment once the owner answers.
  A round-1 slice that still meets the split trigger goes to split round 2.
  In round 1 the only parent is the original story, so the per-parent band is the whole-story band and is recorded once.
  When the original whole-story recorded estimate is the highest value of the step sequence for `profile.tracker.estimate_scale` (story-refinement Step 4 item 1), every stop and warning whose base is that estimate states that the base is saturated and that the 1.0 and 1.5 bounds computed from it are lower bounds on the true size.
  A stop holds every further split round, record and tracker write for the slices until the owner answers; a split that completes within two rounds with no stop proceeds unchanged.
  A round with a leaf slice recorded as unpointed still runs the per-parent bound and the round cap on each recorded slice value, which stop as above, and every per-parent sum whose slices all have recorded values.
  For the whole-story sum and the sum of each parent with an unpointed slice, the sum of the recorded values is a lower bound on the true sum: a lower bound above 1.5 times the base stops as above with band stop, and otherwise that comparison is pending, because a warning or no flag can still change once the slice is valued.
  A stop in such a round routes as any stop, and its message names each unpointed slice; with no stop, the split comment records the pending comparisons beside that slice's `needs input`, and they run, with the per-parent bound and the round cap of each unpointed slice, once the owner's answer gives every leaf slice a recorded value, before any further split round, record or tracker write for the slices.
  Worked examples are in the Split bounds section of the story-refinement skill's refinement record reference.
- ⛔ Price a shared unknown once, in the priced shared-unknown ledger that every whole-story pointing round records (story-refinement Steps 3 and 4).
  Each voter lists, with its value, the unknowns behind that value with a point price each and the remainder, its non-unknown complexity; the prices plus the remainder sum exactly to the voter's value (in a re-vote, the highest value of its accepted set), and a rationale whose prices plus remainder differ from its value is off-basis.
  After the consensus check, once story-refinement Step 4 has recorded the estimate or the unpointed variance stop, the facilitator records one ledger in the pointing record from the rationales that stand: it merges unknowns that voters named differently and records each merge, takes one price per voter for each merged unknown (the voter's lowest, when it listed that unknown more than once), and prices each unknown at the median of the prices of the voters who listed it, the lower of the two prices when two listed it, or the sole price when one did.
  Ledger prices are not rounded; the ledger total is recorded beside the whole-story value and is not reconciled to slice values, and a slice value is a vote on the step sequence.
  A ledger from a saturated whole-story value (the highest value of the step sequence, as the bullet above states) carries the saturation note, that its prices are lower bounds on the true size, and is not adjusted.
  Each unknown has exactly one owner slice, the slice whose work resolves it, else the core slice, assigned when the split is drafted; an unsplit story records the ledger without owners, and a slice that is split again reassigns its owned unknowns to its sub-slices by the same rule, recorded in the split comment of split round 2, from which each sub-slice brief takes its owners.
  An unknown that a blocker story's work resolves is owned by that blocker story and is priced in no slice.
  Every slice brief, the pointing prompt of a slice estimate, carries the ledger with its prices and owners, and when the whole-story value is saturated it states that the ledger prices are lower bounds.
  Every pointing round after a story's first, a slice estimate in either split round, gives each voter in its slice brief, as text, the prior-round context: the parent's recorded value and the three voter values of the parent's round, the ledger, and the recorded rationales of the slice's ancestor rounds only, the whole-story round and, in split round 2, the parent slice's round, never a voided vote or rationale, a ground the story-refinement Step 4 basis review challenged, or a sibling slice's value or rationale.
  The brief states the per-parent bound only in the Slice brief template's fixed sentence, as a bound and never as a value to score; the parent's recorded value paired with its round's voter values appears only on the template's Parent line, and the parent's value appears as a bound only in that fixed sentence.
  Slice voters still run in newly created contexts, so the prior rounds reach them by the brief and never by session reuse, and the values of the same round, the sibling slices' and the round's other voters', stay hidden until every vote of the round is recorded.
  The facilitator records each slice brief verbatim in the slice's pointing record.
  A slice voter never re-prices an unknown: its rationale states the ledger price of each unknown its slice owns plus its own non-unknown complexity.
  A slice rationale that omits an unknown its slice owns, re-prices an unknown, prices one the ledger does not carry, or names one the ledger assigns elsewhere is off-basis: the story-refinement Step 4 basis review re-runs that vote once on its existing terms, and a second miss is recorded.
  Worked examples are in the Slice brief section of the story-refinement skill's refinement record reference.
- ⛔ At refinement, without asking, split a Bug or an Investigation whose accepted refinement comment's `Scope signal:` line reads `more than one independently reviewable change`, with or without its `(<reason>)`: the original keeps the core slice and blocks each sibling, siblings come from its own filing template with its type label, no slice gets a point value or a slice estimate, and the split comment maps every acceptance criterion or findings-scope item to a slice and every slice criterion or item to exactly one criterion or item of the issue it is split from; for these unestimated types that line, never an estimate, is the trigger.
- ⛔ Never split an issue at close time to carve off unfinished work; that is status laundering.

## Acceptance criteria and scope

- An issue delivers a complete feature the user can reach in the running environment.
  Bake reachability (routing, TLS, the deploy actually delivering the artifact) and any access gate into the criteria.
- Build each issue for every environment in `profile.environments` up front; promotion only tests, it never adds code.
  Gate a real production safety concern instead of scoping down to one environment.
- An acceptance criterion that needs behavioural evidence has the one artifact that proves it, and the single command, run or record that produces that artifact, named in the story's Verification line and never inside the criterion, and that artifact must be producible in one pass by one role.
  One pass means one session of the one role the criterion names, with no fix round, no second session and no resumed session to finish it.
  A live multi-context ceremony is allowed only when the ceremony is the story's subject; then the story names the fixture, the exact voter contexts a single run creates, and the one record that run posts.
  A fixture the story would have to build is its own story.
  A criterion that expects a re-run, a second fixture, a fix round or a resumed session after the first run is not one-pass and fails this rule.
- Write each acceptance criterion as one rule with one observable outcome: one sentence that states the state or behaviour reached, never how to reach it.
  Aim for at most 25 words per criterion and treat more than 40 as a trigger to rewrite it; no source sets a word limit, so this is house style.
  A criterion never joins two outcomes with "and".
  Aim for 3 to 5 criteria per story, a common practitioner rule of thumb and not a standard; more criteria, or two independently deliverable outcomes, means rewrite the criteria or split the story.
- Keep these out of the criteria: commands and flags, script and file names, polling intervals and window sizes, execution order, who merges, and how evidence is posted.
  The engineer decides them.
  Where the story needs them recorded, a runbook or test plan linked in Additional Context holds them.
  Evidence conventions live once in the Definition of Done, never in a criterion.
- Required failure behaviour is its own criterion, for example "a rolled-back tenant returns to held".
  Restoration steps, notifications and diagnostics belong in the runbook.
  When building the failure path is major work, it is its own story.
- Use Given/When/Then for event-driven behaviour and a plain rule for an invariant, a threshold or a configuration state.
  A constraint the owner imposes, such as an excluded host or a tenant that stays held, is a short fact in Additional Context or a criterion, never a procedure.
- Making a synchronous external call on a request path non-blocking belongs to the issue that introduces the call, not to a later hardening issue.
- When the user decides no production promotion is scheduled and the only unticked items are later-environment legs, delete those lines, add an italic dated note naming who decided, tick the rest, and set done.
  Record the deferred steps in the epic.
- ⛔ A deployment-review finding covered by an existing issue's criteria reopens that issue: move it back to in progress, amend the criteria with a dated note, and run it through PR, review, merge, deploy, and deployment review again.
  File a new issue only when no existing criterion covers the behavior.
- ⛔ Only the product owner or the refinement process adds, moves, or rewords acceptance criteria on any story.
  An implementing engineer never adds an AC to any story, never moves its own unmet AC onto another story, never rewords an AC, never records its own "accepted deviation", and never accepts an AC as met by any means other than the completion tick in "Completion (AC and DoD checkboxes)".
  Ticking an AC box after observing the behaviour in the deployed environment, per "Completion (AC and DoD checkboxes)", is the verification record and not an AC change.
  The two edits this section already directs remain permitted and are not engineer-added scope: amending one criterion with a dated note when a deployment-review finding reopens that same story, and deleting the later-environment lines the user has decided not to promote.
  Neither licence extends to another story, and neither lets an engineer reword a criterion it cannot meet or use a dated note to make an unmet criterion pass.
- An engineer who meets a scope limit has only two permitted responses, the two exits below.
  Exit one, a refinement proposal: a downstream requirement the engineer discovers is posted as a comment on the target story headed "Refinement proposal (not an AC)" and listed in its handback (the completion summary, in `engineering-workflow`).
  Exit two, blocked: when an AC cannot be met or the work needs another story's artifact, the engineer stops and reports itself blocked, naming the story that supplies the precondition or, where no story does, the criterion and why it cannot be met so the product owner can re-refine it, and the story moves to `profile.tracker.states.blocked`.
  The engineer makes that move where it has tracker write access, and otherwise states in its handback that the move is required.
  A proposal never substitutes for blocking when a current AC cannot be met.
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
- Assign an issue to a cycle with the tracker's issue update (`cycle` on the Linear MCP `save_issue`; the CLI equivalent is the issue update's cycle field), then read the issue's state and cycle back.
- Read completed-cycle points from the tracker's cycle and issue history (the Linear MCP cycle listing or the CLI equivalent); when the runtime cannot read it, report the velocity baseline as unavailable instead of inventing one.

## Filing issues

- ⛔ Load the matching filing skill and follow it; never copy structure from sibling issues:
  `linear-user-story`, `linear-bug`, `linear-spike`, `linear-investigation`, `linear-epic`.
- Search the team backlog and existing epics before creating (`linear issue query --search <term> --team <KEY>` for issues and `linear project list --team <KEY>` for epics, with `<KEY>` the team key from Team resolution, or the Linear MCP server's list_issues and list_projects tools with a filter); the issue may already exist.
- Filing or searching on behalf of a named issue (a split sibling of it, a backlog or epic search for it) uses that issue's team (Team resolution); the profile's team applies only when no issue is named.
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
- Tools take `team` as the team name and the CLI takes `--team` with the team key, both resolved as Team resolution states: from the named issue's key, else `profile.tracker.team_name` and `profile.tracker.team_key`.
- Use `project:` and `assignee:` (not `projectId:` or `assigneeId:`); `labels:` takes names.
  Create with team, title, and description only, then update by id to set project, assignee, labels, state, priority, estimate, and cycle.
- `cycle:` sets an issue's cycle; use the cycle id or name the tracker accepts, then read the issue back.
