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
- `profile.refinement.product_owner` is the product owner (PO) voter and the only tracker mutator.
  The PO posts the refinement comment, applies every tracker write, and reads each write back.
- `profile.refinement.reviewers` is exactly two engineer voters on different model families, recorded as optional `family` values or distinct model ids.
  Both reviewers must set `family` or both must omit it. If exactly one sets `family`, stop and ask for a different reviewer. If both set `family`, the values must differ; if both omit `family`, the `model` ids must differ. Never run two voters from the same model family.
  The PO and the two engineers are the voters in both the refinement agreement and the pointing round.
- A `profile.refinement.facilitator`, `profile.refinement.product_owner`, or `profile.refinement.reviewers` that is unset stops the ceremony.
  Ask for the value; never substitute one.
- Stop when the configured facilitator runtime differs from the orchestrator runtime.
  The facilitator is always the top-level session.

Launch each non-facilitator role in a separate context with the runtime, model, optional `agent`, optional `command`, and optional `family` from its profile entry.
A `command` runtime gets its prompt in a file and writes its result to an output file.

## Stage 1: refinement

### Step 1: Independent refinement

- **Inputs:** the story description, acceptance criteria, comments, and formal relations; the profile; the capability references; the Definition of Ready and Definition of Done template from the matching filing skill.
- **Process:**
  1. Create the todo list and read the story completely, including `linear issue relation list <ID>` for every blocker.
  2. Launch the PO and both engineers in separate contexts with the same story surface.
     Give each voter only its own profile entry and the story; never give it another voter's file or a summary of another input.
  3. Each voter writes only its own input file in `profile.workspace.scratch_dir`, under a per-story directory and a role-specific name.
     A voter may read its own file back but must not write another role's file.
  4. The facilitator records its own SM/EM refinement contribution in a separate file.
     That contribution may challenge acceptance criteria, propose refinements, and identify gaps: missing ACs, gaps within an AC, and unobservable criteria.
  5. No voter sees another voter's refinement input or value before its own input is recorded.
     No tracker comment is posted until all three voter inputs are recorded.
- **Reviewer output contract:** a refinement input includes a Definition of Ready verdict, per-AC gaps with exact proposed wording, scope and split, risks, refined AC deltas, and an `ACCEPT` or `OBJECT` position.
- **Outputs:** three voter input files and one separate SM/EM contribution file in `profile.workspace.scratch_dir`.
- **Stop:** a profile key is unset, a voter cannot run on its configured runtime and model, or a voter file is missing.
  Never substitute a different model, a different voter, or a guessed value.

The SM/EM contribution is not a vote.
The PO and the two engineers decide whether an SM/EM concern is a blocking amendment.

### Step 2: Reconciliation and the accept round

- **Inputs:** the three voter refinement inputs and the separate SM/EM contribution.
- **Process:**
  1. The facilitator reconciles the inputs into one refined story: story text, refined acceptance criteria, scope and split, Definition of Ready changes, and open risks.
  2. The PO posts the refinement comment and applies the refined description as the only tracker mutator.
     The refinement comment includes the complete refined story and ACs, or an immutable snapshot reference; its id identifies the refined version for every later step.
  3. Run the accept round on that exact refinement comment id.
     Each of the three voters returns `ACCEPT` or `OBJECT` against the same refined version.
  4. An `OBJECT` blocks and lists only blocking amendments.
     Notes that are not blocking amendments do not block.
  5. After any blocking amendments, the PO applies them, posts an updated refinement comment, and uses its new comment id as the refined version.
     Re-run the accept round against that new id.
     The accept round is capped at two rounds.
  6. If all three voters have not returned `ACCEPT` after two rounds, the PO records the story as unpointed and the ceremony stops.
- **Outputs:** an accepted refined story identified by the refinement comment id, or a recorded unpointed result.
- **Stop:** two accept rounds without all three `ACCEPT`; a voter is missing; the PO cannot write to the tracker.

The SM/EM's refinement comments never substitute for a voter's `ACCEPT` or `OBJECT`.
Only the PO and the two engineers count toward the agreement.

## Stage 2: pointing

### Step 3: Secret pointing

- **Inputs:** the accepted refined story and its refinement comment id; `profile.tracker.estimate_scale`; `profile.refinement.point_cap` for the later cap check.
- **Process:**
  1. Launch the PO and both engineers again in separate contexts on the same refined version.
  2. Each voter submits one point value valid for `profile.tracker.estimate_scale` plus a short rationale.
     The value is written only to that voter's own file in `profile.workspace.scratch_dir`.
  3. No voter sees another voter's point value before its own value is recorded.
  4. The facilitator records all three values before the SM/EM comments on sizing or the discussion opens.
     The SM/EM submits no point value.
  5. After all three values are recorded, the SM/EM may provide factual, reference-only sizing context: comparable stories, historical sizing, and relevant scope differences.
     It must not state or imply a preferred value, recommend a direction, reveal or compare individual votes before the discussion, or use leading language.
  6. A `tshirt` scale stops the cap step with a clear message.
     Pointing still records the three values; the split rule's numeric cap does not apply.
- **Outputs:** three point value files and, when provided, a separate SM/EM sizing context file.
- **Stop:** any voter value is missing; an SM/EM sizing comment appears before all three values are recorded (see the anchoring guardrail); the scale is `tshirt` at the cap step.

### Step 4: High/low discussion and consensus

- **Inputs:** the three recorded point values and any recorded SM/EM sizing context.
- **Process:**
  1. Hold one discussion round that names only the high and the low.
     Do not compare the other values or single out a voter.
  2. Run one re-vote.
     Each voter records the set of values it accepts for this story (one or more) or records no consensus.
  3. Consensus is the highest value in the intersection of the three accepted sets.
     If the intersection is empty, record no consensus and leave the story unpointed.
  4. Never average and never take a value silently.
  5. The facilitator records the consensus; it does not declare it.
  6. If the split trigger is met (consensus above `profile.refinement.point_cap` or 8 or more), apply the split rule.
- **Outputs:** a consensus value with the split decision, or a recorded unpointed result.
- **Stop:** no value all three accept; an anchoring event voids the round.

## Anchoring guardrail

The three point values are recorded before the SM/EM comments on sizing or the discussion opens.
The SM/EM's sizing comments are logged with the consensus record.

The prohibited behaviours are:

- naming a target number;
- saying "I would go higher" or "I would go lower";
- singling out the highest or lowest vote as the realistic one;
- asking for a revote after stating a view;
- comparing individual votes.

On anchoring: stop the round, record the comment verbatim, void the consensus and any vote recorded after the anchor, and re-run the independent vote with newly created voter contexts that exclude the tainted discussion and sizing comment. Never reuse the sessions that saw the anchor. Record the recovery.
Do not resume the tainted discussion.

## Split rule

The effective accepted maximum is `profile.refinement.point_cap` (default 5), with a schema maximum of 8.
A story is split when its consensus is above `profile.refinement.point_cap` or is 8 or more; the lower trigger applies, and the 8-point rule in [references/linear.md](references/linear.md) is never relaxed.

If the split trigger is met, split the story.

- The original issue stays the core slice.
- Siblings are created from the `linear-user-story` template.
- The original issue blocks each sibling.
- Every acceptance criterion is mapped to a slice in the split comment.
- Each slice gets its own three-voter estimate in the same blind round.
- A slice still at or above the split trigger is split again or escalated.

Cite [references/linear.md](references/linear.md) for the split mechanics; do not restate them here.

## Triage

The PO performs every tracker write (priority, assignee, estimate, Definition of Ready ticks, and state) and reads each write back.
The SM/EM posts only its own comments.

- The PO ticks a Definition of Ready box only after verifying the condition and records the evidence for every ticked box.
  An unverified box stays unticked.
- Set `profile.tracker.states.ready` only when no blocker remains.
- Leave blocked siblings in `profile.tracker.states.backlog` with the blocker Definition of Ready box unchecked.
- Priority comes from the PO's decision.

## Records

Use [references/refinement-record.md](references/refinement-record.md) for the refinement-comment template, the pointing-record template, and the permitted and forbidden phrasing table.
Keep the raw voter files in `profile.workspace.scratch_dir` and cite their paths in the record.
Record the refinement comment id, every accept round, all three point values, the SM/EM sizing context, the discussion result, the consensus, and any split.

## Runtime portability

This skill is runtime-agnostic and cites [references/runtimes.md](references/runtimes.md) for the capability map.
The facilitator is the orchestrator session and loads `persona-scrum-master`.
Name capabilities, not tools.
Roles run as the profile entry says: a subagent of the configured runtime, or a shell command.
If a configured role cannot run on its runtime or model, stop and say so; never substitute another model for a voter.
