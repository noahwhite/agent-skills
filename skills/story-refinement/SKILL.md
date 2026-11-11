---
name: story-refinement
description: >-
  Run independent-context story refinement and secret pointing as the scrum master or engineering manager (SM/EM).
  Three voters refine the story, agree, then point it blind through a consensus check and, where it calls for them, at most one discussion and one re-vote, with a fresh independent vote after an anchoring recovery.
  Use when asked to refine a story, run a refinement or pointing ceremony, decide Definition of Ready changes, estimate a story, split an oversized story, or record a refinement or pointing decision.
  The SM/EM facilitates and never votes; the three engineer voters are the voters and the product owner authors every tracker write.
  Not for implementing the story (use engineering-workflow) or verifying a deployed story (use qa-verification).
license: Apache-2.0
compatibility: Requires a tracker CLI or MCP server (Linear by default), the configured facilitator, product owner, and reviewer roles, and a runtime that can run each role as its profile entry says.
---

# Story refinement

Run refinement and pointing as a facilitated ceremony with three voters and one facilitator.
The facilitator is the scrum master or engineering manager (SM/EM).
The voters are the three engineers.
The product owner authors every tracker write and does not vote.
The facilitator never votes and never declares consensus.

The process has two stages and four steps.
Stage 1 is refinement: independent inputs, then reconciliation and the accept round.
Stage 2 is pointing: secret votes, then a consensus check and, where the check calls for them, one high/low discussion and one re-vote ending in a recorded estimate or an unpointed stop.
Each step names its inputs, outputs, and stop conditions.

## Arguments

`STORY_ID` is required: any Linear issue key (for example `ABC-123`).
Its team prefix is the team for every read and write this skill performs on or for that issue, and it need not equal `profile.tracker.team_key`.
Any backlog or epic search this skill performs runs in the team of `STORY_ID`.
If none was given, ask the owner for one before doing anything else; never guess an issue key.

`metrics` is optional, given as `metrics=on` or `metrics=off` or in plain words, and defaults to `off`.
`with metrics` and `metrics on` mean on; `without metrics` and `metrics off` mean off.
Any other phrasing about metrics is asked about, never guessed.

- Resolve both arguments, asking about any ambiguity, before the todo list is created.
- When `metrics` resolves on, the facilitator's next action, before the todo list, is to take a UTC timestamp with a command and record it as `invocation_start` in the metrics file.
- Write the resolved value as one line `metrics: on` or `metrics: off` at the top of the todo list and in the closing message.

With `metrics` off or omitted, the facilitator does not open `references/metrics.md`, collects no figure, creates no metrics scratch file, posts no metrics comment, and adds no metrics content to any brief, record, report, todo list, closing message, or tracker write, other than the `metrics: off` line.
Every other metrics instruction in this skill applies only when `metrics` is on.

## Read first

- [references/profile.md](references/profile.md) - find the profile and this skill's overlay before anything else.
- [references/todo-tracking.md](references/todo-tracking.md) - required: create the fine-grained todo list before the first read, context, or tracker write, with one item per voter input, accept round, point value, consensus check, basis-challenge round, discussion and re-vote when the check calls for them, split, and triage write.
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
- `profile.refinement.product_owner` is the product owner (PO) and the only author of tracker writes.
  The PO authors the refinement comment and every other tracker write, applies each except under the denied tracker writes fallback, and reads each write back.
  The PO is not a voter: it authors no refinement input file, records no accept-round `ACCEPT` or `OBJECT`, no point value and no accepted-set value.
  The facilitator applies tracker writes only under the denied tracker writes fallback.
- `profile.refinement.reviewers` is exactly three engineer voters on different model families, each with a non-empty explicit `family`, on pairwise-distinct family values and pairwise-distinct model ids.
  A reviewer count other than three, a missing required role, a missing or empty reviewer `family`, a duplicate reviewer family or a duplicate reviewer model id stops the ceremony before any voter launch, and the roster check in Step 1 names the violated requirement.
  The three engineers are the voters in both the refinement agreement and the pointing round.
- A `profile.refinement.facilitator`, `profile.refinement.product_owner`, or `profile.refinement.reviewers` that is unset stops the ceremony.
  Ask for the value; never substitute one.
  A facilitator or product owner whose `enabled` is `false` stops the ceremony the same way, with a named error: neither is a launch this ceremony may skip, so no vote, tracker write or record follows.
- An engineer voter whose `enabled` is `false` is skipped before any launch: no process, no subagent, no output file, and the evidence reads "<name>: disabled", never a vote, a failed vote, or a clean one.
  Omission means enabled.
  The rules above count the enabled entries: if fewer than three engineer voters are enabled, or the enabled ones share a family or a model id, stop the ceremony and name the disabled entry in the stop.
  With `refinement.reviewers` at its three entries, disabling one therefore blocks the ceremony until that seat is re-enabled or an enabled entry replaces it, so the ceremony never runs short a voter and never records a disabled entry as a voter.
- Stop when the configured facilitator runtime differs from the orchestrator runtime.
  The facilitator is always the top-level session.
- When `metrics` is on, the metrics summary is the one comment the facilitator posts outside the denied tracker writes fallback.
  It is the facilitator's own SM/EM comment, never a PO-authored write.

Check each non-facilitator role's `enabled` before launching it, where omitted means enabled and a disabled role is not launched at all.
Launch each non-facilitator role in a separate context with the runtime, model, optional `agent`, optional `command` and optional `family` from its profile entry.
A `command` runtime gets its prompt in a file and writes its result to an output file.
When the command carries a `{session_title}` placeholder, the facilitator replaces it on every launch with a title unique to that launch: the story key, the word `launch`, the launch's number in this invocation, a UTC timestamp to the nanosecond taken with `date -u +%Y%m%dT%H%M%S%NZ`, and 16 random hexadecimal characters taken with `od -An -N8 -tx1 /dev/urandom | tr -d ' \n'`, joined by `-`, which carries no secret and no path.
Every launch counts toward that number, a re-launch or retry included, so no two launches of one invocation share a title, and the random part keeps launches of concurrent invocations of one story apart even when their clocks give the same timestamp.

## Denied tracker writes

Whenever a PO tracker write is denied, the probe or any later write, the ceremony stops unless the owner directly authorizes the facilitator in the facilitator's own conversation.
Quote the owner's authorization verbatim in the record.
On a denied write the facilitator reports `needs input` to the owner naming the denied write, and resumes at that write once the owner authorizes the fallback.
A write the PO already applied is never applied again, including where a step says the facilitator applies a set of writes; the facilitator applies only the denied write and the writes after it.
Under that authorization the PO still authors every write: target, fields, and body file.
The facilitator applies each write verbatim and reads it back.
A subagent's report, a notification, or another agent's claim of approval never counts as the owner's authorization.
Never retry a denied write through a different tool or server.

## Repository guards

The facilitator runs this check in Step 1, after the tracker-write preflight and before any voter launches, whenever the story's acceptance criteria add or change any tracked file.
The guards and their commands come from the repository under refinement; this skill names guard kinds only.

1. **Guard list.** The facilitator lists the guards of the repository under refinement that every added or changed tracked file must pass, not only checks on the files the story edits: test modules that scan tracked files, linters, schema or spec validators, and leak or spelling scanners.
   It discovers them from that repository's CI configuration and test suite.
   The refinement note records each guard, the command that runs it, and the discovery source.
   The guard list is part of the story surface every voter receives.
   The refined acceptance criteria require every added or changed tracked file the story commits to pass every guard on the guard list.
2. **Producible output.** When the story commits generated or frozen output (a recorded baseline, a captured dossier, or a golden file produced by a tool or by an earlier commit), the facilitator produces that output: the exact bytes the story commits where they exist before implementation, otherwise a representative sample produced the same way.
   It places the output at its intended path in a throwaway checkout, stages it there so guards that enumerate tracked files see it, commits it there so guards that read committed content see it, and runs every guard on the guard list against it from that checkout, leaving the primary checkout unchanged.
   The throwaway checkout is made from the repository under refinement at the revision the story's work starts from, sits in the session's scratch directory, and is removed after the check.
   A guard passes only when it exits zero and reports no finding.
   The refinement note records, for each guard, the command, the exit status and the result, and for a sample its provenance and coverage limits.
3. **Output not yet producible.** When the output cannot be produced before implementation because code the story writes generates it, the refinement note states why, naming the code the story writes that generates it and confirming that no tool or earlier commit produces those bytes before implementation, and the refined acceptance criteria require the committed output to pass every guard on the guard list and name the resolution the implementer may use if a guard rejects it, chosen from the kinds item 4 lists.
4. **Rejection.** When a guard rejects output checked under item 2, the refined acceptance criteria state the resolution: an exemption the story adds, scoped to its own files; a normalization; an encoding; or an amendment to the criterion that forbade one of these.
   The resolved output is re-run through the rejecting guard and passes, and through every other guard on the guard list, which pass too; the refinement note records the rejection, the resolution and the passing re-run.
5. **Stop.** When a guard on the guard list cannot be run, or the resolved output still fails any guard on the guard list, the facilitator stops and reports `needs input` to the owner naming the guard, its command and its result.
6. **Refresh.** When an accept-round amendment adds or changes a tracked file or committed output the check has not covered, the facilitator runs the check again against the amended acceptance criteria before the updated refinement comment is posted.
   A split sibling under the [Split rule](#split-rule), and a story whose acceptance criteria changed after an earlier check, get the check against their own final acceptance criteria before the PO decides the "checked against the implementation" Definition of Ready box.
7. **No secrets.** The guard list, guard output given to a voter, and the refinement note contain no secrets: a rejection that matched secret text is cited by guard, file and line, never quoted.

## Stage 1: refinement

### Step 1: Independent refinement

- **Inputs:** the story description, acceptance criteria, comments, and formal relations; the profile; the capability references; the Definition of Ready and Definition of Done template from the matching filing skill.
- **Process:**
  1. Create the todo list and read the story completely, including `linear issue relation list <ID>` for every blocker.
  2. Validate the refinement roster before the tracker-write preflight and before any voter launch.
     Resolve the profile through the first-existing-file rule in [references/profile.md](references/profile.md) (the `shared/profile.md` rule), never a repository-only read.
     Stop with a message naming the violated requirement when `profile.refinement.reviewers` does not hold exactly three entries, when fewer than three reviewers are enabled, when a required role (`facilitator`, `product_owner`, `reviewers`) is unset, when a reviewer `family` is missing or empty, when two reviewer families are equal, or when two reviewer model ids are equal.
  3. Run the tracker-write preflight before any voter launches.
     The PO, in a separate context, posts one comment on the story under refinement that marks itself as the tracker-write preflight, and reads it back.
     On success the facilitator records the comment id for the refinement record.
     If the write is denied, no voter launches, and the facilitator reports `needs input` to the owner naming the denied write and pointing to the "Tracker writes from a subagent" rule in `references/runtimes.md`.
     The probe exercises comment add only; later write kinds fall under the denied tracker writes fallback, and the Step 2 stop stays as the backstop.
     After the owner acts, run the probe again; if the owner directly authorizes the facilitator under the denied tracker writes fallback, the facilitator applies the PO-authored probe verbatim, records its comment id, and the voters launch.
  4. Run the repository guard check in [Repository guards](#repository-guards) before any voter launches.
  5. Launch the three engineers in separate contexts with the same story surface.
     Give each voter only its own profile entry, the story, the guard list from [Repository guards](#repository-guards) when that check ran, and the session's scratch directory it writes into; never give it another voter's file or a summary of another input.
     A voter runs in its own child context and cannot derive the parent's directory, so the brief carries the path.
  6. Each voter writes only its own input file in the session's scratch directory (`references/runtimes.md`, Scratch files), under a subdirectory named after the story key and a role-specific name; never a path component outside that directory.
     The session's directory sits inside `profile.workspace.scratch_dir` when that is the base the runtime or the profile gives (the runtime's base wins), and is a standalone `mktemp -d` when neither gives one.
     A voter may read its own file back but must not write another role's file.
  7. The facilitator records its own SM/EM refinement contribution in a separate file.
     That contribution may challenge acceptance criteria, propose refinements, and identify gaps: missing ACs, gaps within an AC, and unobservable criteria.
  8. No voter sees another voter's refinement input or value before its own input is recorded.
     No tracker comment is posted until all three voter inputs are recorded, except the tracker-write preflight, which is the only exception.
- **Reviewer output contract:** a refinement input includes a Definition of Ready verdict, a verdict on the guard list, per-AC gaps with exact proposed wording, scope and split, risks, refined AC deltas, and an `ACCEPT` or `OBJECT` position.
- **Outputs:** three voter input files and one separate SM/EM contribution file in the session's scratch directory.
- **Stop:** the roster check fails (a reviewer count other than three, fewer than three reviewers enabled, a required role unset, a missing or empty reviewer family, or a duplicate reviewer family or model id), a required profile key is unset, a voter cannot run on its configured runtime and model, a voter file is missing, a guard on the guard list cannot be run or still rejects the resolved output, or the tracker-write preflight is denied and the owner has not authorized the denied tracker writes fallback.
  The scratch directory is never such a key: without one the documented standalone `mktemp -d` fallback applies.
  Never substitute a different model, a different voter, or a guessed value.

The SM/EM contribution is not a vote.
The three engineer voters decide whether an SM/EM concern is a blocking amendment.

### Step 2: Reconciliation and the accept round

- **Inputs:** the three voter refinement inputs and the separate SM/EM contribution.
- **Process:**
  1. The facilitator reconciles the inputs into one refined story: story text, refined acceptance criteria, scope and split, Definition of Ready changes, and open risks.
  2. The PO authors the refinement comment and the refined description and applies both; otherwise, under the denied tracker writes fallback, the facilitator applies both verbatim.
     The refinement comment includes the complete refined story and ACs, or an immutable snapshot reference; its id identifies the refined version for every later step.
  3. Run the accept round on that exact refinement comment id.
     Each of the three voters returns `ACCEPT` or `OBJECT` against the same refined version.
  4. After each accept round, the PO authors and posts a separate Accept round result comment that names the refinement comment id it covers, the round number, each voter's `ACCEPT` or `OBJECT`, and the outcome: accepted, another round, or unpointed.
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
Only the three engineer voters count toward the agreement.

## Stage 2: pointing

### Step 3: Secret pointing

- **Inputs:** the accepted refined story and its refinement comment id; `profile.tracker.estimate_scale`.
- **Process:**
  1. Launch the three engineers again in separate contexts on the same refined version.
  2. A point measures complexity - design difficulty, interacting constraints, unknowns, and the risk of breaking existing behaviour - and never the amount of work or elapsed time; routine, well-understood work such as writing tests, opening a PR, review, running a fixture, or regenerating copies adds no points however long it takes.
  3. The sentence above is the pointing basis.
     Every pointing prompt or prompt file carries it verbatim, and carries the item 4 rationale rule, including each slice estimate under the Split rule.
  4. Each voter submits one point value valid for `profile.tracker.estimate_scale` and present in the fixed step sequence Step 4 item 1 states for that scale, plus a short rationale under the pointing basis in item 2.
     A value outside that sequence is re-recorded before the reveal, in a launch that starts a new voter context, so every value and every accepted set has a step position; a second off-sequence value from the same voter stops the round with a missing-valid-value stop reason.
     The rationale names drivers the pointing basis admits and nothing else, so verification strength, testability, coverage, the shape of the tests, a duration, effort or run-cost measure are out of basis.
     Verification strength is how well a behaviour is checked and the risk of breaking existing behaviour is what can silently change, so the first is out of basis while the second is a driver the basis admits, distinct from an interacting constraint the change carries.
     The rationale names no target value for this story, never treats another voter's revealed value as its answer, and names no point value before the reveal.
     The value is written only to that voter's own file in the session's scratch directory.
  5. No voter sees another voter's point value before its own value is recorded.
     The reveal is the moment the facilitator has recorded all three values, after which the SM/EM may comment on sizing and the discussion opens.
  6. The facilitator records all three values before the SM/EM comments on sizing or the discussion opens.
     The SM/EM submits no point value.
  7. After all three values are recorded, the SM/EM may provide factual, reference-only sizing context: comparable stories in complexity terms, their recorded values, comparable unknowns and constraints, and relevant scope differences.
     A factual reference is not a prescription: naming an already-estimated item's recorded value, alone or together with a basis difference, is permitted, and such a reference is information the voters weigh and never stops the round.
     It must not prescribe this story's value - no value to score, no target, no preferred direction - and must not reveal or compare individual votes before the discussion.
     Before the reveal it must not name any point value.
     A prescription of this story's value, from the SM/EM or from a voter, is an anchoring event under the Anchoring guardrail.
     A statement of elapsed time or effort is an anchoring event under the Anchoring guardrail.
- **Outputs:** three point value files and, when provided, a separate SM/EM sizing context file.
- **Stop:** any voter value is missing; a voter's second off-sequence value is a missing-valid-value stop, which the owner resolves by authorizing a re-run of that voter's record in a new invocation whose `Outcome` reads `missing valid value`; an SM/EM sizing comment appears before all three values are recorded (see the anchoring guardrail).

### Step 4: High/low discussion and consensus

- **Inputs:** the three recorded point values and any recorded SM/EM sizing context.
- **Process:**
  1. Run the consensus check first, on the three values recorded in Step 3.
     The ordered step sequence is fixed here for each `profile.tracker.estimate_scale` value, in the order given: `fibonacci` 1, 2, 3, 5, 8, 13; `linear` the ordinal list 1, 2, 3, 5, 8, 13; `exponential` 1, 2, 4, 8, 16.
     The tolerance is one step, and it is fixed in this skill: no profile key and no skill argument sets it.
     A value outside that sequence for the profile's scale has no step position, so two different values that involve one are more than one step apart; three identical values are identical, and Step 3 already re-records an off-sequence value before the reveal.
     When the three values are identical, or the highest and the lowest are one step apart (5 and 8 on `fibonacci`, for example), the highest of the three values is the estimate, the discussion in item 3 and the re-vote in item 4 are skipped, and the split rule in item 9 still applies to it.
     The basis review in item 2 still runs on this branch, and nothing is written to the tracker and no pointing record is posted until it has run.
     When the highest and the lowest are more than one step apart (1 and 5, for example), or they differ and either of them is outside the sequence, the discussion in item 3 and the re-vote in item 4 run, naming the high and the low.
     Record the outcome in the pointing record as `Consensus check: <identical | one step | more than one step>`, so a skipped discussion and re-vote read as skipped and never as not run; the record's values block keeps the values recorded before the discussion, and a replacement value appears on its Challenges line and in the voter's file.
  2. Review every rationale recorded in Step 3 against the pointing basis, after the consensus check and before the estimate is written to the tracker and before the pointing record is posted, so a void never leaves a written estimate to unwind.
     This review is not the discussion: it runs on both branches, and the discussion in item 3 only carries the challenges it raises.
     The review challenges every ground outside the pointing basis that a recorded rationale carries; a ground first heard in the discussion of item 3 is challenged there, under item 3, except a prescription of this story's value and, from the SM/EM, a statement of elapsed time, effort or run cost, which are anchoring events the moment they are seen.
     That rule governs the shared discussion content and other voters' values; a voter's own recorded value and rationale may be carried privately in that voter's own prompt, so it can speak to its own ground.
     Challenging a ground is not comparing values or singling out a voter: the facilitator names the ground's kind, never its verbatim text; the facilitator never names another voter's value in the shared discussion, nor a voter's value to other voters, and the pointing record carries the author; a ground that embeds a point value is named by its kind alone.
     A challenged ground must be restated as a basis driver or retracted, except a prescription of this story's value, which is an anchoring event as soon as it is seen.
     A voter whose basis does not support its recorded value retracts an unsupported ground and records a replacement value with a basis-driver rationale under the Step 3 item 4 rationale rule, in the re-vote or, when the consensus check skips the re-vote, in the basis-challenge round of this item, and the facilitator records it in that voter's Step 3 file on either path; one basis-challenge round runs per voter per ceremony, so a replacement whose rationale is again off basis leaves the ground unresolved and voids the round rather than starting another; a replacement value is valid for `profile.tracker.estimate_scale` and present in the item 1 sequence, re-recorded otherwise.
     The facilitator records a replacement value in that voter's Step 3 file, so the value recorded there is the value that stands, and, when the consensus check skipped the re-vote, it then re-runs on the three standing values, because the value it recorded was set by a basis the voter has withdrawn; on the re-vote branch items 5 and 6 are the only path to an estimate.
     The re-run's outcome supersedes the `Consensus check:` outcome in the pointing record, and when it is more than one step apart the discussion in item 3 and the re-vote in item 4 run before any estimate is written or posted.
     The SM/EM withdraws or restates its own sizing comment on the same terms, except a point value named before the reveal, a prescription of this story's value, treating another voter's revealed value as the answer, or a statement of elapsed time, effort or run cost, each of which is an anchoring event as soon as the facilitator sees it.
     A ground that is neither restated as a basis driver nor retracted is an anchoring event under the Anchoring guardrail.
     The basis-challenge round applies this same review to every rationale its launches record: an off-basis replacement rationale is restated or retracted, and an unresolved one voids the round.
     When the consensus check skips the discussion and the re-vote, this review runs as a basis-challenge round of its own: the facilitator launches each challenged voter once per round in a newly created voter context whose prompt lists every ground challenged for that voter and carries the story, the refinement comment id, that voter's own recorded value and rationale, the Step 3 pointing basis and the Step 3 item 4 rationale rule; an off-sequence replacement value is re-recorded in a second launch of that voter. That launch records a replacement value for that voter only when the voter's basis does not support its recorded value, and otherwise the value that stands holds. An unresolved ground voids the round under the Anchoring guardrail, so no estimate and no split action survives an unresolved challenge.
  3. Hold one discussion round that names only the high and the low, when the consensus check calls for it.
     Do not compare the other values or single out a voter.
     The round carries the challenges item 2 raised, and the facilitator challenges, on the terms item 2 sets and within that same round, any ground heard for the first time there; such a ground is restated or retracted and its voter records a replacement value in the re-vote when the basis does not support the value, and no estimate is recorded while any ground it raised is unresolved.
  4. Run one re-vote, when the consensus check calls for it.
     The re-vote prompt carries the pointing basis from Step 3.
     It also carries the Step 3 item 4 rationale rule and the fixed step sequence from item 1, since an accepted set is drawn from that sequence.
     Each voter records the set of values it accepts for this story (one or more, each valid for `profile.tracker.estimate_scale` and present in the item 1 sequence) or records no consensus, with a short complexity rationale under the Step 3 rationale rule.
     An accepted-set value outside that sequence is re-recorded once under the Step 3 re-record rule, and a second off-sequence re-vote value from the same voter stops the round like a Step 3 off-sequence stop.
     Recording an accepted set is not treating another voter's revealed value as the answer: the rationale for the set is about the basis, never about which value another voter recorded.
     A re-vote rationale outside the pointing basis is challenged before the consensus is recorded, under the same restate-or-retract rule as item 2, and a voter that retracts its re-vote rationale records a replacement accepted set within that same re-vote, with a basis-driver rationale, or records no consensus.
  5. When the re-vote ran, consensus is the highest value in the intersection of the three accepted sets.
     When a voter recorded no accepted set, or that intersection is empty, apply the residual variance rule in item 6.
  6. Residual variance: when the re-vote leaves no value shared by all three accepted sets, each voter's re-vote value is the highest value in its accepted set.
     A voter that records no consensus in item 4 has no accepted set, so its re-vote value is the value it recorded in its Step 3 file; after a void that is the value in the re-run's file, never a voided one.
     Every derived value comes from an accepted set or a Step 3 file, so it is on the sequence and its gap in scale steps is measurable.
     When those derived per-voter values are identical, or the highest and the lowest of them are one step apart on the sequence in item 1, the same tolerance rule applies to them: the highest derived value is the estimate, and the split rule in item 9 still applies to it.
     For example, accepted sets `{5}` and `{5}`, with no consensus from the voter whose Step 3 value was 5, derive 5, 5 and 5 from an empty intersection, so the ceremony records 5 as the estimate instead of stopping unpointed.
     When the highest and the lowest derived values are more than one step apart (1 and 5, for example), the ceremony records the result as unpointed and stops: it posts the three values, the derived values with the gap between the highest and the lowest in scale steps, and the three rationales, and reports `needs input` to the owner naming the story and the derived values.
     That unpointed variance stop is a `needs input` state of this skill, distinct from the `needs input` a denied tracker write produces.
     The PO authors the unpointed variance record and applies it, or under the denied tracker writes fallback the facilitator applies the PO-authored record verbatim.
     The owner decides that outcome in a later run, which records it by editing the posted pointing record's `Owner decision:` line, which the posting run leaves as `pending owner decision in a later run`: a numeric decision is recorded as the estimate and the split rule applies to it, and a decision to leave the story unpointed is recorded with the owner's reason and records no estimate.
     The product owner does not decide that outcome, and no facilitator and no voter chooses the value or the path.
  7. Never average and never take a value silently, except the tolerance value the consensus check or the residual variance rule records.
  8. The facilitator records the estimate or the consensus; it does not declare it.
  9. Apply the split rule when the split trigger it defines is met by the recorded estimate.
     The recorded estimate is the value this step's consensus check or residual variance rule records, or the consensus.
- **Outputs:** a recorded estimate with the split decision - the value the consensus check records, the consensus, or the highest derived value - or the unpointed variance stop with the three values, the derived values with the gap between the highest and the lowest in scale steps, and the three rationales; and the `Consensus check:` outcome in the pointing record.
- **Stop:** the residual variance rule stops the ceremony unpointed because the derived values are more than one step apart, which reports `needs input` to the owner naming the story and the derived values; an anchoring event voids the round.

## Anchoring guardrail

The three point values are recorded before the SM/EM comments on sizing or the discussion opens.
The SM/EM's sizing comments are logged with the pointing record.

The prohibited behaviours are:

- for the SM/EM, naming a point value before the reveal, prescribing a value for this story - a value to score, a target, a preferred direction, or a claim that one vote is the realistic one - or treating another voter's revealed value as the answer;
- saying "I would go higher" or "I would go lower";
- singling out the highest or lowest vote as the realistic one;
- asking for a revote after stating a view;
- comparing individual votes.

An anchoring trigger is an off-basis ground Step 4 challenges, so it becomes an anchoring event only when it is neither restated as a basis driver nor retracted: a ground that weighs verification strength, testability, coverage, the shape of the tests, or a duration, effort or run cost is such a trigger when a voter weighs it in a rationale or raises it in the discussion.
Every prohibited behaviour above, a prescription of this story's value by any participant, and an SM/EM sizing comment that names a point value before the reveal or states elapsed time, effort or run cost, are anchoring events as soon as they are seen, with no challenge, restatement or retraction path.
A factual reference is never such an event: naming an already-estimated item's recorded value, alone or together with a basis difference, is information the voters weigh, and the round continues.
Any other challenged ground that is neither restated as a basis driver nor retracted, or a sizing comment the SM/EM neither withdraws nor restates, is an anchoring event, and the recovery below is the single void rule: it voids the recorded estimate, the `Consensus check:` outcome, the consensus, the residual variance derived values and their outcome, and every vote recorded after the anchor, and for a ground read in a recorded rationale the anchor precedes that rationale, so the vote it grounds and every later vote are void, and the independent vote from Step 3 is re-run in newly created voter contexts that exclude the tainted discussion and sizing comment.

Fresh voter contexts exclude the tainted discussion and the sizing comment, but they cannot exclude a value recorded on the story surface that Step 1 hands every voter with the story, so the Step 3 rationale rule is what keeps such a value from becoming the rationale's answer.

On anchoring: stop the round, record the comment verbatim, void the recorded estimate, the `Consensus check:` outcome, the consensus, the residual variance derived values and their outcome, and any vote recorded after the anchor, and re-run the independent vote with newly created voter contexts that exclude the tainted discussion and sizing comment. Never reuse the sessions that saw the anchor. Record the recovery.
Do not resume the tainted discussion.

## Split rule

The effective accepted maximum is `profile.refinement.point_cap` (default 5), with a schema maximum of 8.
A story is split when its recorded estimate is above `profile.refinement.point_cap` or is 8 or more; the recorded estimate is the consensus, or the value the Step 4 consensus check or residual variance rule records.
The lower trigger applies, and the 8-point rule in [references/linear.md](references/linear.md) is never relaxed.

If the split trigger is met, split the story.

- The original issue stays the core slice.
- Siblings are created in the team of `STORY_ID`, as Team resolution in [references/linear.md](references/linear.md) states.
- When the team of `STORY_ID` differs from `profile.tracker.team_key`, confirm `profile.tracker.states.backlog` and each sibling label on that team before creating any sibling, under the differing-team rule in Team resolution in [references/linear.md](references/linear.md).
- Siblings are created from the `linear-user-story` template.
- The original issue blocks each sibling.
- Every acceptance criterion is mapped to a slice in the split comment.
- Each slice gets its own three-voter estimate in the same blind round, with newly created voter contexts, and that round runs the same Step 4 consensus check, basis review and residual variance rule, so a slice records an estimate or takes the unpointed variance stop on the same terms.
  A slice that takes the unpointed variance stop is recorded as unpointed in the split comment with its derived values, and the ceremony reports `needs input` to the owner naming the story, the slice and those values, so a partially pointed split always ends in that report rather than in an estimate, and its recorded outcome is the slice count with `needs input` for each unpointed slice.
- A slice still at or above the split trigger is split again or escalated.

Cite [references/linear.md](references/linear.md) for the split mechanics; do not restate them here.

## Triage

The PO authors every tracker write (priority, assignee, estimate, Definition of Ready ticks, and state) and applies and reads each one back, except under the denied tracker writes fallback.
The SM/EM posts only its own comments, and applies the PO's writes only under the denied tracker writes fallback.
When `metrics` is on, the metrics summary is the one comment the SM/EM posts outside the denied tracker writes fallback; it is the SM/EM's own comment, never a PO-authored write.

- The PO ticks a Definition of Ready box only after verifying the condition and records the evidence for every ticked box.
  An unverified box stays unticked.
- When the story's acceptance criteria add or change any tracked file, the PO does not tick the "checked against the implementation" Definition of Ready box while the guard list is missing, the check did not run against the story's final acceptance criteria, output was classed under item 3 without the evidence item 3 requires, producible output under item 2 of [Repository guards](#repository-guards) was not run, a guard could not be run, or a guard rejection lacks a resolution with a passing re-run.
- When the team of `STORY_ID` differs from `profile.tracker.team_key`, confirm `profile.tracker.states.ready`, `profile.tracker.states.backlog` and each label name on that team before writing it, under the differing-team rule in Team resolution in [references/linear.md](references/linear.md).
- Set `profile.tracker.states.ready` only when no blocker remains.
- Leave blocked siblings in `profile.tracker.states.backlog` with the blocker Definition of Ready box unchecked.
- Priority is the PO's decision on every refinement outcome: the story moving to `profile.tracker.states.ready`, the story staying in `profile.tracker.states.backlog`, and each split sibling.
  The PO decides, applies and reads back a priority before the invocation ends and before any move to `profile.tracker.states.ready`, unless the ceremony stops on priority as this bullet states.
  The PO chooses the priority by comparing the story with at least one comparable story already prioritised in the team of `STORY_ID`.
  The PO applies the priority and reads it back as a PO-authored tracker write.
  "No priority" counts as unset and is never a decided value.
  When the PO cannot decide, including when the team has no comparable prioritised story, the ceremony stops with the priority unset and "Priority is clear" unticked, and reports `needs input` to the owner naming the story; the closing message names that stop as its stop reason.
  The PO never guesses a priority.
  The PO ticks "Priority is clear" only after the priority is read back and equals the decided value.
  The PO posts the Triage record from [references/refinement-record.md](references/refinement-record.md) as a triage write on every outcome, the priority stop included.

## Records

Use [references/refinement-record.md](references/refinement-record.md) for the refinement-comment template, the Accept round result template, the pointing-record template, and the permitted and forbidden phrasing table.
Use the Triage record template in the same file for the triage write that records the priority and the comparison it rests on.
Keep the raw voter files in the session's scratch directory and cite each file by its base name only (never a directory path) in the record.
Quote or attach any file content a reader needs in the record.
Record the refinement comment id, every accept round, all three point values, the SM/EM sizing context, the `Consensus check:` outcome, the discussion result, every challenge with its outcome, the consensus or the residual variance outcome with the derived values, the gap between the highest and the lowest in scale steps and the rule applied, the recorded estimate or the unpointed variance stop, and any split.
When the [Repository guards](#repository-guards) check ran, the refinement comment also records the guard list with each guard's command and discovery source; for each guard run, its command, exit status and result; each sample's provenance and coverage limits; and each rejection with its resolution and passing re-run, with no secrets under item 7 of [Repository guards](#repository-guards).

## Metrics

This section applies only when `metrics` is on.
[references/metrics.md](references/metrics.md) defines what is collected, the summary template, and each label; this section binds it to this skill and does not restate it.

- **Location:** Figures live only in one metrics file in the session's scratch directory, outside every per-role subdirectory.
- **Never named:** The metrics file is never named in any brief.
- **Not reported:** A figure the runtime does not return is `not reported`; it is never estimated or inferred.
- **Usage:** Each launch's Tokens and Tool calls are read as the "Read a subagent's usage" row and the "Usage from shell-launched agents" rule in [references/runtimes.md](references/runtimes.md) state; this section states no usage formula of its own.
  With `metrics` on, the facilitator keeps each launch's title in the metrics file and reads that launch's usage by it.
- **Timed launches:** Time every launch the facilitator spawns, including each re-launch.
  That covers the tracker-write preflight; each Step 1 voter launch; each PO launch that authors or applies a tracker write or record; each accept-round voter launch; each Step 3 pointing launch; each Step 4 discussion launch; each Step 4 basis-challenge launch; each Step 4 re-vote launch; each anchoring recovery re-launch; and each slice estimate launch.
  Take the start timestamp immediately before the launch and the end timestamp when the launch returns.
- **Independence:** Add no metrics of this invocation and no other role's figures from this invocation to any voter brief, voter input, SM/EM sizing context, refinement comment, Accept round result comment, or pointing, unpointed, or split record; story comments posted by an earlier invocation stay part of the story surface.
- **Summary:** The closing message carries the run summary in the template `references/metrics.md` defines, on every end state and every stop, with every field filled or labelled as that reference defines (`not reported`, `cumulative`, `partial`, or, when the invocation performed no launch, `no launches` with `not applicable` totals), and the stop reason where the run stopped.
  The summary contains no secrets and no local or scratch paths.
- **Post:** When the invocation reaches a permitted post, the facilitator posts the summary on the story under refinement as its own SM/EM comment at the end of the invocation, when no further voter round will run in it, reads its own comment back, and the closing message names the posted comment.
  On a permitted post, `invocation_end` is taken immediately before the summary is composed, and the comment and the closing message carry that same summary; no second timestamp is taken.
  A failed or differing read-back is not retried: the closing message carries the summary and names the failed read-back.
  The comment contains no secrets and no local or scratch paths.
- **Order:** When a pointing record exists, the comment is the invocation's last tracker write.
  It posts only after every voter round, including every slice estimate under the Split rule, has finished; the pointing record (a recorded estimate, an unpointed result, or a split decision) and any split comment have been posted and read back; and the invocation's triage writes have been applied and read back.
- **Stop before a record:** On a stop before a pointing record exists, the comment posts only after every Step 1 voter input is recorded - with the three-voter roster, all three Stage 1 voter inputs - and every launched voter has returned or been stopped, with its end timestamp taken; on that path no pointing record and no triage write is required.
  A stop before every Step 1 voter input is recorded attempts no post, because Step 1 allows no tracker comment before then except the preflight, and the summary stays in the closing message.
- **Never during an anchoring recovery:** The comment is never posted while an anchoring recovery, its Step 3 re-run, or any Step 4 re-vote that follows them, is still to run.
- **Resumed run:** A resumed run is a new invocation and posts its own comment covering only that invocation; a resume in the same session after the owner authorizes the denied tracker writes fallback is the same invocation and posts once.
- **Denied post:** If the post is denied or unavailable, the closing message carries the summary and names the denied or unavailable write, and no other tool or server is tried.
  Where the run stopped on denied tracker writes without the owner's authorization, no post is attempted.

## Closing message

The closing message is the facilitator's final message to the owner when the invocation ends, on every end state and every stop.
It names the outcome (the recorded estimate, unpointed, or split with the slice count) or the stop reason, including each `needs input`: the denied tracker write of Step 1 and the unpointed variance stop of Step 4.
It carries the `metrics: on` or `metrics: off` line.
When `metrics` is on, it names the metrics summary comment the facilitator posted; when the post was denied or unavailable, it carries the summary and names the denied or unavailable write; when the read-back failed, it carries the summary and names the failed read-back; when no post was attempted, it carries the summary and names no comment.

## Runtime portability

This skill is runtime-agnostic and cites [references/runtimes.md](references/runtimes.md) for the capability map.
The facilitator is the orchestrator session and loads `persona-scrum-master`.
Name capabilities, not tools.
Roles run as the profile entry says: a subagent of the configured runtime, or a shell command.
If a configured role cannot run on its runtime or model, stop and say so; never substitute another model for a voter.
