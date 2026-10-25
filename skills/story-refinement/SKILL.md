---
name: story-refinement
description: >-
  Run independent-context story refinement and secret pointing as the scrum master or engineering manager (SM/EM).
  Three voters refine the story, agree, then point it blind before one discussion and one re-vote.
  Use when asked to refine a story, run a refinement or pointing ceremony, decide Definition of Ready changes, estimate a story, split an oversized story, or record a refinement or pointing decision.
  The SM/EM facilitates and never votes; the product owner and two engineers are the voters.
  Not for implementing the story (use engineering-workflow) or verifying a deployed story (use qa-verification).
license: Apache-2.0
compatibility: Requires a tracker CLI or MCP server (Linear by default), the configured facilitator, product owner, and reviewer roles, and a runtime that can run each role as its profile entry says.
---

# Story refinement

Run refinement and pointing as a facilitated ceremony with three voters and one facilitator.
The facilitator is the scrum master or engineering manager (SM/EM).
The voters are the product owner and two engineers.
The facilitator never votes and never declares consensus.

The process has two stages and four steps.
Stage 1 is refinement: independent inputs, then reconciliation and the accept round.
Stage 2 is pointing: secret votes, then the high/low discussion and consensus.
Each step names its inputs, outputs, and stop conditions.

## Read first

- [references/profile.md](references/profile.md) - find the profile and this skill's overlay before anything else.
- [references/todo-tracking.md](references/todo-tracking.md) - required: create the fine-grained todo list before the first read, context, or tracker write, with one item per voter input, accept round, point value, discussion, re-vote, split, and triage write.
- [references/linear.md](references/linear.md) - the rule set for the story lifecycle, Definition of Ready, estimation, splitting, relations, and tooling gotchas.
  Cite it for split mechanics; do not restate them here.
- [references/engineering-practice.md](references/engineering-practice.md) - diagnose before changing, write meaningful tests, and keep changes minimal.
- [references/runtimes.md](references/runtimes.md) - maps the capabilities named here (todo list, load a skill, spawn a subagent, run a shell command) to your runtime.
- [references/refinement-record.md](references/refinement-record.md) - the hand-written refinement-comment and pointing-record templates and the permitted and forbidden phrasing table.

Where this file and a capability file disagree, the capability file is authoritative, except the non-voting facilitator rule, the independence rules, and the anchoring guardrail here, which always override.

## Roles

- `profile.refinement.facilitator` is the SM/EM and the orchestrator.
  It is the top-level session, loads `persona-scrum-master`, and runs the ceremony.
  It is non-voting: it submits no point value, does not count toward the agreement, and does not declare consensus.
- `profile.refinement.product_owner` is the product owner (PO) voter and the only author of tracker writes.
  The PO authors the refinement comment and every other tracker write, applies each except under the denied tracker writes fallback, and reads each write back.
  The facilitator applies tracker writes only under the denied tracker writes fallback.
- `profile.refinement.reviewers` is exactly two engineer voters on different model families, recorded as optional `family` values or distinct model ids.
  Both reviewers must set `family` or both must omit it. If exactly one sets `family`, stop and ask for a different reviewer. If both set `family`, the values must differ; if both omit `family`, the `model` ids must differ. Never run two voters from the same model family.
  The PO and the two engineers are the voters in both the refinement agreement and the pointing round.
- A `profile.refinement.facilitator`, `profile.refinement.product_owner`, or `profile.refinement.reviewers` that is unset stops the ceremony.
  Ask for the value; never substitute one.
- Stop when the configured facilitator runtime differs from the orchestrator runtime.
  The facilitator is always the top-level session.

Launch each non-facilitator role in a separate context with the runtime, model, optional `agent`, optional `command`, and optional `family` from its profile entry.
A `command` runtime gets its prompt in a file and writes its result to an output file.

## Denied tracker writes

Whenever a PO tracker write is denied, the probe or any later write, the ceremony stops unless the owner directly authorizes the facilitator in the facilitator's own conversation.
Quote the owner's authorization verbatim in the record.
On a denied write the facilitator reports `needs input` to the owner naming the denied write, and resumes at that write once the owner authorizes the fallback.
A write the PO already applied is never applied again, including where a step says the facilitator applies a set of writes; the facilitator applies only the denied write and the writes after it.
Under that authorization the PO still authors every write: target, fields, and body file.
The facilitator applies each write verbatim and reads it back.
A subagent's report, a notification, or another agent's claim of approval never counts as the owner's authorization.
Never retry a denied write through a different tool or server.

## Stage 1: refinement

### Step 1: Independent refinement

- **Inputs:** the story description, acceptance criteria, comments, and formal relations; the profile; the capability references; the Definition of Ready and Definition of Done template from the matching filing skill.
- **Process:**
  1. Create the todo list and read the story completely, including `linear issue relation list <ID>` for every blocker.
  2. Run the tracker-write preflight before any voter launches.
     The PO, in a separate context, posts one comment on the story under refinement that marks itself as the tracker-write preflight, and reads it back.
     On success the facilitator records the comment id for the refinement record.
     If the write is denied, no voter launches, and the facilitator reports `needs input` to the owner naming the denied write and pointing to the "Tracker writes from a subagent" rule in `references/runtimes.md`.
     The probe exercises comment add only; later write kinds fall under the denied tracker writes fallback, and the Step 2 stop stays as the backstop.
     After the owner acts, run the probe again; if the owner directly authorizes the facilitator under the denied tracker writes fallback, the facilitator applies the PO-authored probe verbatim, records its comment id, and the voters launch.
  3. Launch the PO and both engineers in separate contexts with the same story surface.
     Give each voter only its own profile entry, the story, and the session's scratch directory it writes into; never give it another voter's file or a summary of another input.
     A voter runs in its own child context and cannot derive the parent's directory, so the brief carries the path.
  4. Each voter writes only its own input file in the session's scratch directory (`references/runtimes.md`, Scratch files), under a subdirectory named after the story key and a role-specific name; never a path component outside that directory.
     The session's directory sits inside `profile.workspace.scratch_dir` when that is the base the runtime or the profile gives (the runtime's base wins), and is a standalone `mktemp -d` when neither gives one.
     A voter may read its own file back but must not write another role's file.
  5. The facilitator records its own SM/EM refinement contribution in a separate file.
     That contribution may challenge acceptance criteria, propose refinements, and identify gaps: missing ACs, gaps within an AC, and unobservable criteria.
  6. No voter sees another voter's refinement input or value before its own input is recorded.
     No tracker comment is posted until all three voter inputs are recorded, except the tracker-write preflight, which is the only exception.
- **Reviewer output contract:** a refinement input includes a Definition of Ready verdict, per-AC gaps with exact proposed wording, scope and split, risks, refined AC deltas, and an `ACCEPT` or `OBJECT` position.
- **Outputs:** three voter input files and one separate SM/EM contribution file in the session's scratch directory.
- **Stop:** a required profile key is unset, a voter cannot run on its configured runtime and model, a voter file is missing, or the tracker-write preflight is denied and the owner has not authorized the denied tracker writes fallback.
  The scratch directory is never such a key: without one the documented standalone `mktemp -d` fallback applies.
  Never substitute a different model, a different voter, or a guessed value.

The SM/EM contribution is not a vote.
The PO and the two engineers decide whether an SM/EM concern is a blocking amendment.

### Step 2: Reconciliation and the accept round

- **Inputs:** the three voter refinement inputs and the separate SM/EM contribution.
- **Process:**
  1. The facilitator reconciles the inputs into one refined story: story text, refined acceptance criteria, scope and split, Definition of Ready changes, and open risks.
  2. The PO authors the refinement comment and the refined description and applies both; otherwise, under the denied tracker writes fallback, the facilitator applies both verbatim.
     The refinement comment includes the complete refined story and ACs, or an immutable snapshot reference; its id identifies the refined version for every later step.
  3. Run the accept round on that exact refinement comment id.
     Each of the three voters returns `ACCEPT` or `OBJECT` against the same refined version.
  4. After each accept round, including the Step 4 re-refine accept round, the PO authors and posts a separate Accept round result comment that names the refinement comment id it covers, the round number, each voter's `ACCEPT` or `OBJECT`, and the outcome: accepted, another round, or unpointed.
     The refinement comment itself is not edited, so its id keeps identifying one immutable refined version.
     Under the denied tracker writes fallback the facilitator applies the PO's comment verbatim.
  5. An `OBJECT` blocks and lists only blocking amendments.
     Notes that are not blocking amendments do not block.
  6. After any blocking amendments, the PO authors the amendments and an updated refinement comment and applies both; otherwise, under the denied tracker writes fallback, the facilitator applies the amendments and the updated refinement comment verbatim.
     The amended refinement uses its new comment id as the refined version.
     Re-run the accept round against that new id.
     The accept round is capped at two rounds.
  7. If all three voters have not returned `ACCEPT` after two rounds, the PO authors the unpointed record and applies it, or under the denied tracker writes fallback the facilitator applies it verbatim, and the ceremony stops.
- **Outputs:** an accepted refined story identified by the refinement comment id, or a recorded unpointed result, and one Accept round result comment per accept round.
- **Stop:** two accept rounds without all three `ACCEPT`; a voter is missing; the PO cannot write to the tracker and the owner has not authorized the denied tracker writes fallback.

The SM/EM's refinement comments never substitute for a voter's `ACCEPT` or `OBJECT`.
Only the PO and the two engineers count toward the agreement.

## Stage 2: pointing

### Step 3: Secret pointing

- **Inputs:** the accepted refined story and its refinement comment id; `profile.tracker.estimate_scale`; `profile.refinement.point_cap` for the later cap check.
- **Process:**
  1. Launch the PO and both engineers again in separate contexts on the same refined version.
  2. A point or size measures complexity - design difficulty, interacting constraints, unknowns, and the risk of breaking existing behaviour - and never the amount of work or elapsed time; routine, well-understood work such as writing tests, opening a PR, review, running a fixture, or regenerating copies adds no points however long it takes.
  3. The sentence above is the pointing basis.
     Every pointing prompt or prompt file carries it verbatim, and carries the item 4 rationale rule, including the re-run after a Step 4 re-refine and each slice estimate under the Split rule.
  4. Each voter submits one point value valid for `profile.tracker.estimate_scale` plus a short rationale under the pointing basis in item 2.
     The rationale names drivers the pointing basis admits and nothing else, so verification strength, testability, coverage, the shape of the tests, a duration, effort or run-cost measure are out of basis.
     Verification strength is how well a behaviour is checked and the risk of breaking existing behaviour is what can silently change, so the first is out of basis while the second is a driver the basis admits, distinct from an interacting constraint the change carries.
     The rationale names no target value for this story, never treats another voter's revealed value as its answer, and names no point value before the reveal.
     The value is written only to that voter's own file in the session's scratch directory.
  5. No voter sees another voter's point value before its own value is recorded.
     The reveal is the moment the facilitator has recorded all three values, after which the SM/EM may comment on sizing and the discussion opens.
  6. The facilitator records all three values before the SM/EM comments on sizing or the discussion opens.
     The SM/EM submits no point value.
  7. After all three values are recorded, the SM/EM may provide factual, reference-only sizing context: comparable stories in complexity terms, comparable unknowns and constraints, and relevant scope differences.
     It must not state or imply a preferred value, recommend a direction, reveal or compare individual votes before the discussion, or use leading language.
     Before the reveal it must not name any point value.
     After the reveal it may compare this story with an already-estimated item and name that item's recorded value, but it must not name or imply a target value for this story, including one implied by a split status, and such a statement is an anchoring event under the Anchoring guardrail.
     A statement of elapsed time or effort is an anchoring event under the Anchoring guardrail.
  8. A `tshirt` scale stops the cap step with a clear message.
     Pointing still records the three values; the split rule's numeric cap does not apply.
- **Outputs:** three point value files and, when provided, a separate SM/EM sizing context file.
- **Stop:** any voter value is missing; an SM/EM sizing comment appears before all three values are recorded (see the anchoring guardrail); the scale is `tshirt` at the cap step.

### Step 4: High/low discussion and consensus

- **Inputs:** the three recorded point values and any recorded SM/EM sizing context.
- **Process:**
  1. Hold one discussion round that names only the high and the low.
     Do not compare the other values or single out a voter.
     In that round, and against the rationales recorded in Step 3, the facilitator challenges every ground outside the pointing basis, whether it is heard in the discussion or read in a recorded rationale.
     Challenging a ground is not comparing values or singling out a voter: the facilitator names the ground's kind and its author, never the ground's verbatim text, and a ground that embeds a point value is named by its kind alone.
     A challenged ground must be restated as a basis driver or retracted, except a target value named or implied for this story, which is an anchoring event as soon as it is seen; a voter whose basis does not support its recorded value records that in the re-vote.
     The SM/EM withdraws or restates its own sizing comment on the same terms, except a point value named before the reveal, a target value named or implied for this story, including one implied by a split status, treating another voter's revealed value as the answer, or a statement of elapsed time, effort or run cost, each of which is an anchoring event as soon as the facilitator sees it.
     A ground that is neither is an anchoring event under the Anchoring guardrail.
  2. Run one re-vote.
     The re-vote prompt carries the pointing basis from Step 3.
     It also carries the Step 3 item 4 rationale rule.
     Each voter records the set of values it accepts for this story (one or more) or records no consensus, with a short complexity rationale under the Step 3 rationale rule.
     Recording an accepted set is not treating another voter's revealed value as the answer: the rationale for the set is about the basis, never about which value another voter recorded.
     A re-vote rationale outside the pointing basis is challenged before the consensus is recorded, under the same restate-or-retract rule as item 1, and a voter that retracts its re-vote rationale records a new accepted set with a basis-driver rationale or records no consensus.
  3. Consensus is the highest value in the intersection of the three accepted sets.
     If the intersection is empty, record no consensus and run the no-consensus decision (item 7).
  4. Never average and never take a value silently.
  5. The facilitator records the consensus; it does not declare it.
  6. If the split trigger is met (consensus above `profile.refinement.point_cap` or 8 or more), apply the split rule.
  7. No-consensus decision: the facilitator presents only the empty intersection and the three paths: split, re-refine, or leave unpointed.
     The facilitator does not recommend a path.
     Each voter (the PO and both engineers) records the set of paths it accepts; a voter that accepts re-refine also lists the amendments it needs.
     The chosen path is in the intersection of the three accepted path sets.
     When that intersection holds more than one path, the PO chooses among them and records why.
     When that intersection is empty, the story is left unpointed.
     The facilitator records the decision; it does not choose it.
  8. Split applies the split rule as a group-decided split.
  9. Re-refine returns to Step 2.
     The PO authors the amendments and an updated refinement comment and applies both; otherwise, under the denied tracker writes fallback, the facilitator applies the amendments and the updated refinement comment verbatim.
     One accept round runs on the new comment id.
     If all three voters do not return `ACCEPT`, the PO records the story as unpointed, or under the denied tracker writes fallback the facilitator applies the PO-authored unpointed record verbatim.
     On acceptance, Step 3 re-runs blind with newly created voter contexts, then this step runs again.
     Re-refine is offered at most once per ceremony; a second empty intersection offers only split or leave unpointed.
- **Outputs:** a consensus value with the split decision, or the no-consensus decision (split, re-refine, or leave unpointed) with each voter's accepted paths and the decision rationale.
  Leave unpointed is the default when no path is in all three sets, and re-refine runs at most once per ceremony.
- **Stop:** the no-consensus decision is leave unpointed, which is the default when no path is in all three sets; the re-refine accept round ends without three `ACCEPT`; a second empty intersection without a chosen split, because re-refine runs only once per ceremony; an anchoring event voids the round.

## Anchoring guardrail

The three point values are recorded before the SM/EM comments on sizing or the discussion opens.
The SM/EM's sizing comments are logged with the consensus record.

The prohibited behaviours are:

- for the SM/EM, naming a point value before the reveal, naming or implying a target value for this story, including one implied by a split status, or treating another voter's revealed value as the answer;
- saying "I would go higher" or "I would go lower";
- singling out the highest or lowest vote as the realistic one;
- asking for a revote after stating a view;
- comparing individual votes.

An anchoring trigger is an off-basis ground Step 4 challenges, so it becomes an anchoring event only when it is neither restated as a basis driver nor retracted: a ground that weighs verification strength, testability, coverage, the shape of the tests, or a duration, effort or run cost is such a trigger when a voter weighs it in a rationale or raises it in the discussion.
Every prohibited behaviour above, a target value named or implied for this story by any participant, and a sizing comment that names a point value before the reveal or states elapsed time, effort or run cost, are anchoring events as soon as they are seen, with no challenge, restatement or retraction path.
Any other challenged ground that is neither restated as a basis driver nor retracted, or a sizing comment the SM/EM neither withdraws nor restates, is an anchoring event, and the recovery below is the single void rule: it voids the consensus and every vote recorded after the anchor, and for a ground read in a recorded rationale the anchor precedes that rationale, so the vote it grounds and every later vote are void, and the independent vote from Step 3 is re-run in newly created voter contexts that exclude the tainted discussion and sizing comment.

Fresh voter contexts exclude the tainted discussion and the sizing comment, but they cannot exclude a value recorded on the story surface that Step 1 hands every voter with the story, so the Step 3 rationale rule is what keeps such a value from becoming the rationale's answer.

On anchoring: stop the round, record the comment verbatim, void the consensus and any vote recorded after the anchor, and re-run the independent vote with newly created voter contexts that exclude the tainted discussion and sizing comment. Never reuse the sessions that saw the anchor. Record the recovery.
Do not resume the tainted discussion.

## Split rule

The effective accepted maximum is `profile.refinement.point_cap` (default 5), with a schema maximum of 8.
A story is split when its consensus is above `profile.refinement.point_cap` or is 8 or more; the lower trigger applies, and the 8-point rule in [references/linear.md](references/linear.md) is never relaxed.
A story is also split when the Step 4 no-consensus decision chooses split (a group-decided split); this trigger adds to the consensus thresholds and does not change them.

If either split trigger is met, split the story.

- The original issue stays the core slice.
- Siblings are created from the `linear-user-story` template.
- The original issue blocks each sibling.
- Every acceptance criterion is mapped to a slice in the split comment.
- Each slice gets its own three-voter estimate in the same blind round.
  After a group-decided split, the core slice has no consensus value of its own, so the core slice and each sibling get their own blind three-voter estimate in one round, with newly created voter contexts.
- A slice still at or above the split trigger is split again or escalated.

Cite [references/linear.md](references/linear.md) for the split mechanics; do not restate them here.

## Triage

The PO authors every tracker write (priority, assignee, estimate, Definition of Ready ticks, and state) and applies and reads each one back, except under the denied tracker writes fallback.
The SM/EM posts only its own comments, and applies the PO's writes only under the denied tracker writes fallback.

- The PO ticks a Definition of Ready box only after verifying the condition and records the evidence for every ticked box.
  An unverified box stays unticked.
- Set `profile.tracker.states.ready` only when no blocker remains.
- Leave blocked siblings in `profile.tracker.states.backlog` with the blocker Definition of Ready box unchecked.
- Priority comes from the PO's decision.

## Records

Use [references/refinement-record.md](references/refinement-record.md) for the refinement-comment template, the Accept round result template, the pointing-record template, and the permitted and forbidden phrasing table.
Keep the raw voter files in the session's scratch directory and cite each file by its base name only (never a directory path) in the record.
Quote or attach any file content a reader needs in the record.
Record the refinement comment id, every accept round, all three point values, the SM/EM sizing context, the discussion result, every challenge with its outcome, the consensus, any no-consensus decision with each voter's accepted paths and the decision rationale, and any split.

## Runtime portability

This skill is runtime-agnostic and cites [references/runtimes.md](references/runtimes.md) for the capability map.
The facilitator is the orchestrator session and loads `persona-scrum-master`.
Name capabilities, not tools.
Roles run as the profile entry says: a subagent of the configured runtime, or a shell command.
If a configured role cannot run on its runtime or model, stop and say so; never substitute another model for a voter.
