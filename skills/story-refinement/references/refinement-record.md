# Refinement and pointing records

Hand-written templates for the records the ceremony posts.
Use the refinement comment to identify the refined story, the Accept round result to record each accept round, and the pointing record to capture the recorded estimate, the consensus or the residual variance outcome.
Replace every placeholder and keep the raw voter files in the session's scratch directory.
The record never carries a local path; cite each raw voter file by its base name only.
Quote or attach any file content a reader needs in the record.

## Refinement comment

Post this as a tracker comment authored by the product owner, the only author of tracker writes, and posted by the product owner or, under the denied tracker writes fallback, by the facilitator verbatim.
Its comment id is the refined story identifier for both stages.
For a Bug, an Investigation or a Spike, the comment carries the `Pointing skipped` line; for a User Story it omits that line.
For a Bug, an Investigation or a Spike, the comment also carries the `Scope signal:` line with the reading `SKILL.md` (Unestimated issue types) defines; for a User Story it omits that line.
Replace `<reading>` with one whole reading: for a Bug or an Investigation `single change` or `more than one independently reviewable change (<reason>)`, and for a Spike `single research thread` or `more than one independent research thread (<reason>)`, with `<reason>` replaced too; when the Step 2 reconciliation finds no category with two or more voters, replace it with `missing`, which `SKILL.md` treats as a missing line.

```markdown
## Refinement record

- Story: <issue key> at <description version or commit>
- Pointing skipped: <Bug|Investigation|Spike> is unestimated (references/linear.md, Estimation and slicing)
- Scope signal: <reading>
- Tracker-write preflight: comment <id>
- Refined story identifier: <this comment id>
- Refined story snapshot: <the complete refined story and ACs where the filing template has them, or an immutable link/commit>
- Refined story identifier after blocking amendments: <the new comment id, or none>
- Voter inputs, each recorded in its own separate context:
  - Engineer one (<family or model>): <file base name>
  - Engineer two (<family or model>): <file base name>
  - Engineer three (<family or model>): <file base name>
- SM/EM contribution (not a vote): <file base name>
- Definition of Ready verdicts: <verdict per voter>
- Blocking amendments: <none, or the exact amendments>
- Non-blocking notes: <summary or none>
- Accept round 1: see the Accept round result comment
- Accept round 2 (only after a blocking amendment): see the Accept round result comment
- Result: see the Accept round result comment
- Tracker writes: product owner
```

Under the denied tracker writes fallback in `SKILL.md`, replace the tracker-writes line with:

```markdown
- Tracker writes: facilitator on the product owner's behalf (owner's direct authorization: "<verbatim quote>", <date>)
```

## Accept round result

Post this as a separate tracker comment after each accept round, authored by the product owner and posted by the product owner or, under the denied tracker writes fallback, by the facilitator verbatim.
Never edit the refinement comment to add the result; its id keeps identifying one immutable refined version.

```markdown
## Accept round result

- Refinement comment covered: <refinement comment id>
- Round: <1 or 2>
- Engineer one (<family or model>): <ACCEPT or OBJECT>
- Engineer two (<family or model>): <ACCEPT or OBJECT>
- Engineer three (<family or model>): <ACCEPT or OBJECT>
- Outcome: <accepted, another round, or unpointed for a User Story; accepted, another round, or not accepted for a Bug, an Investigation or a Spike>
- Blocking amendments: <each objecting voter's blocking amendments when any voter returned OBJECT; otherwise none>
```

## Pointing record

Post this once Step 4 has recorded the estimate, or record it as an unpointed result; the basis review in Step 4 item 2 always runs before it is posted.
Never post it for a Bug, an Investigation or a Spike, which is never pointed.
The three values are recorded before any SM/EM sizing comment or discussion; a void before all three exist leaves the values block at the values recorded so far and carries no superseded values, and once the blind re-run finishes the values block carries the three standing values while the superseded line carries the voided ones.
Outside the recorded numeric values, the Ledger line's prices and the superseded-values line, no line of the posted record carries a point value named before the reveal or a prescription of this story's value: the Challenges and Anchoring events lines record a ground by its kind, its author (a voter, or the SM/EM for a sizing comment) and its outcome or recovery, and every field that could quote a participant elides those two classes permanently, because the posted record stays on the story surface that later voters read; the verbatim quote lives in the session's raw record, cited by its base name.
A sizing comment that names a point value before the reveal, prescribes this story's value, or states elapsed time, effort or run cost voids the round under the Anchoring guardrail recovery as soon as the facilitator sees it, as does any ground that is neither restated nor retracted, and the void records the voided consensus under Superseded values after a void, so the Consensus field carries the vote that stands, or n/a when the consensus check or the residual variance rule recorded the estimate.

```markdown
## Pointing record

- Tracker-write preflight: comment <id>
- Refined story identifier: <latest refinement comment id after any amendment>
- Estimate scale: <profile.tracker.estimate_scale>
- Values, recorded before the discussion: <the three values recorded before the discussion; when a basis-challenge replacement made the consensus check re-run they are the three values that re-run read; before a void, the values recorded before it>
  - Engineer one: <value, or not recorded> - <short complexity rationale, or none when the value is not recorded>
  - Engineer two: <value, or not recorded> - <short complexity rationale, or none when the value is not recorded>
  - Engineer three: <value, or not recorded> - <short complexity rationale, or none when the value is not recorded>
- Consensus check: <identical | one step | more than one step>
- Ledger: <for a whole-story round, each unknown with its unrounded price and, once the split is drafted, its owner slice or blocker story (no owner for an unsplit story), each merge of differently named unknowns, the ledger total beside the whole-story value (or beside the unpointed outcome, with no saturation note) and not reconciled to slice values, and the saturation note when the whole-story value is the highest value of the step sequence; n/a for a slice round, whose slice brief carries the ledger>
- Slice brief: <n/a for a whole-story round; for a slice round, the slice brief its voters received, verbatim>
- SM/EM sizing context, after all three values: <file base name> or verbatim, eliding a pre-reveal value or a prescription, or none
- Discussion: <high <value>, low <value>; or none when the discussion ran and recorded nothing; or skipped, when the consensus check recorded the estimate; the shared content names only the high and the low, while a voter's own recorded value and rationale are carried privately in that voter's prompt>
- Re-vote: <accepted set per voter, with complexity rationale; or no consensus, with its complexity rationale, for a voter that records none; or none when it ran and recorded nothing; or skipped, when the consensus check recorded the estimate>
- Consensus: <the highest value in the intersection of the vote that stands (the lowest for a slice), or n/a when the consensus check or the residual variance rule recorded the estimate, or none when the round stopped unpointed>
- Residual variance: <each voter's derived value, the gap between the highest and the lowest in scale steps, the rule applied and the resulting value, or the unpointed variance stop; n/a only when all three voters recorded an accepted set and the intersection is not empty, or when the consensus check, or the re-run of it that supersedes that outcome, recorded the estimate>
- Recorded estimate: <the value recorded, or unpointed with the gap between the highest and the lowest in scale steps when the round stopped there>
- Slice consensus: <n/a for a story that is not a slice; for a slice, the lower value, which is recorded, and the higher value, which Step 4 records for an unsplit story; or, for a slice that took the unpointed variance stop, unpointed with its lowest and highest derived values>
- Effective maximum: <profile.refinement.point_cap; the 8-point rule still triggers at 8 or more>
- Split: <none, or the slice mapping, each slice criterion with the exactly one criterion of the story it is split from and each criterion of that story with its slice, and sibling issue keys>
- Challenges: <none, or each ground challenged by kind, its author (a voter, or the SM/EM for a sizing comment), the restatement, withdrawal or retraction, and any replacement value it produced, or the void; elide a pre-reveal value or a prescription>
- Owner decision: <n/a when the round did not stop unpointed, otherwise pending owner decision in a later run until the later run edits this line, then the value the owner decided and the basis, or unpointed with the owner's reason>
- Superseded values after a void: <none, or the voided values, the voided estimate, the voided `Consensus check:` outcome, the voided consensus, the voided derived values and their outcome, and the blind vote that replaced them>
- Anchoring events: <none, or the comment and the recovery, including the newly created voter contexts, with the verbatim comment in the raw session record and its base name cited here>
- Tracker writes: product owner
```

Under the denied tracker writes fallback in `SKILL.md`, replace the tracker-writes line with:

```markdown
- Tracker writes: facilitator on the product owner's behalf (owner's direct authorization: "<verbatim quote>", <date>)
```

## Slice brief

Every slice estimate's pointing prompt is its slice brief: it carries the pointing basis and the rationale rule as Step 3 requires, and this block, filled in from the whole-story pointing record and, in split round 2, the parent slice's pointing record, under the priced shared-unknown ledger and the prior-round context in Estimation and slicing in `references/linear.md`.
The facilitator records each slice brief verbatim on the `Slice brief:` line of the slice's pointing record.

```markdown
## Slice brief

- Slice: <slice key> - <its slice>, split from <parent key> in split round <1 | 2>
- Parent: <parent key>, recorded value <value>, with the three standing voter values of its round <value>, <value>, <value>
- Per-parent bound: this slice's recorded value must be strictly below its parent's recorded value <value>; the split bounds apply it after the round, and it is not a value to score
- Ledger, from the whole-story pointing record, with owners as the split comment of split round 2 reassigns them for a sub-slice:
  - <unknown> - <ledger price> - owner <slice key, or blocker story key, priced in no slice>
- Ledger total: <value>, beside the whole-story value <value>, not reconciled to slice values
- Saturation note: <n/a, or: the whole-story value <value> is the highest value of the step sequence for <scale>, so the ledger prices are lower bounds on the true size>
- Unknowns this slice owns: <each by name with its ledger price, or none>
- Ancestor rationales: <each standing rationale of the whole-story round and, in split round 2, of the parent slice's round, by voter; never a voided vote or rationale, a ground the Step 4 basis review challenged, or a sibling slice's value or rationale>
```

Worked example on `fibonacci` (1, 2, 3, 5, 8, 13), a whole story pointed at 13 and split into core slice A and siblings B and C, with blocker story X.

| Case | Input | Result |
|---|---|---|
| Whole-story rationales | voter 1: 13 = auth 3 + schema 2 + migration 1 + remainder 7; voter 2: 13 = login flow 5 + schema 3 + vendor API 2 + remainder 3; voter 3: 13 = auth 2 + vendor API 3 + remainder 8 | each sums exactly to its value, so all three are on basis |
| Ledger in the pointing record | the three rationales above | login flow merged into auth (merge recorded); auth 3 (median of 3, 5, 2), schema 2 (lower of 2, 3), vendor API 2 (lower of 2, 3), migration 1 (sole price); ledger total 8 beside the whole-story value 13, not reconciled; saturation note, since 13 is the highest value of the sequence |
| Owners, assigned when the split is drafted | slice B's work resolves auth, slice A's resolves schema, no slice resolves migration, blocker X resolves vendor API | auth owner B, schema owner A, migration owner A (core slice), vendor API owner X, priced in no slice |
| Slice brief | slices A, B and C | each brief carries the four unknowns with their prices and owners, the ledger total 8 beside 13, and the saturation note naming the ledger prices as lower bounds |
| Slice rationales | A: schema 2 + migration 1 + own complexity; B: auth 3 + own complexity; C: own complexity only | each slice-owned ledger unknown appears with its ledger price in exactly one slice rationale, and vendor API appears in none |
| Re-pricing rationale | a slice B voter writes auth 5 | off-basis: the Step 4 basis review re-runs that vote once, and a second miss is recorded on the Challenges line |
| Unknown assigned elsewhere | a slice C voter names schema | off-basis on the same terms |
| Whole-story sum mismatch | a voter writes 8 = auth 3 + schema 2 + remainder 2 | off-basis: the prices plus the remainder are 7, not 8 |
| Prior-round context, split round 1 | the slice B brief | parent 13 with voter values 13, 13, 13, the four-unknown ledger, the three whole-story rationales and the bound sentence naming 13; no value or rationale of A or C and no other slice B vote |
| Prior-round context, split round 2 | slice B recorded 8 from voter values 8, 8, 8 and is split into core slice B and sibling B2; the B2 brief | parent B 8 with voter values 8, 8, 8, the ledger with owners as split round 2 reassigns them, the whole-story rationales and slice B's round-1 rationales, and the bound sentence naming 8; no value or rationale of B2's sibling, of A or of C |
| Voided or challenged ancestor rationale | a whole-story rationale voided by an anchoring recovery, or a ground the Step 4 basis review challenged | left out of every brief; only the rationale that stands, without the challenged ground, is carried |
| Parent value in the brief | the bound sentence naming 13 in the slice B brief | a factual reference to an already-recorded item: no anchoring event, and the round continues |
| SM/EM target for a slice | before the reveal the SM/EM tells the slice B voters to aim for 5 | anchoring event: the round is voided and the independent vote re-runs in newly created voter contexts |
| Rationale derived from the parent | a slice B voter writes "one step below the parent's 13, so 8" | off-basis under the Step 3 rationale rule: the Step 4 basis review challenges it |

## Split comment

Post this on the original issue when the oversize split in `SKILL.md` (Unestimated issue types) splits a Bug or an Investigation, authored by the product owner and posted by the product owner or, under the denied tracker writes fallback, by the facilitator verbatim.
A re-split sibling gets its own split comment on that sibling.

```markdown
## Split record

- Refinement comment split: <accepted refinement comment id; for a re-split sibling, the parent split comment id and the sibling key>
- Core slice: <original issue key> - <its slice> - Scope signal: <reading> - description trimmed to this slice
- Siblings, each from the `<linear-bug|linear-investigation>` template with the `<type label>` label, blocked by the original:
  - <sibling key> - <its slice> - Scope signal: <reading>
- Mapping: <each acceptance criterion, or for an Investigation each findings-scope item, and the slice it maps to; and each slice criterion or item and the exactly one criterion or item of the issue it is split from>
- Estimates: none; no slice receives a point value or a slice estimate
- Tracker writes: product owner
```

Under the denied tracker writes fallback in `SKILL.md`, replace the tracker-writes line with:

```markdown
- Tracker writes: facilitator on the product owner's behalf (owner's direct authorization: "<verbatim quote>", <date>)
```

## Split bounds

After each split round of a story split the facilitator runs the split bounds in Estimation and slicing in `references/linear.md` and fills in the block below.
A round with no stop posts the block in the split comment.
A round with a leaf slice recorded as unpointed and no stop posts the block in the split comment with result pending, naming the unpointed slices, and the pending checks run once the owner's answer gives every leaf slice a recorded value.
A stop posts nothing to the tracker: it reports `needs input` to the owner in one message carrying the block, its warning line included, and no further split round, slice record or tracker write for the slices happens until the owner answers.
A mapping-check stop also posts nothing to the tracker, and because it comes before any slice is pointed it fills no block: its one `needs input` message carries a `Mapping check, round <1 | 2>: stop` line naming each slice criterion with no counterpart and each evidence pass, fixture, test obligation or behaviour a slice adds beyond the story it is split from.

```markdown
- Split bounds, round <1 | 2>: <clear | warning | stop | pending: unpointed <slice keys>>
  - Whole-story sum: base <original whole-story recorded estimate>; 1.0 times = <value>, 1.5 times = <value>; sum <sum with each leaf slice's lower consensus value> (lower), <sum with each leaf slice's higher consensus value> (higher); band <clear | warning | stop> (lower, governs), <clear | warning | stop> (higher)
  - Saturated base: <n/a, or: the base <value> is the highest value of the step sequence for <scale>, so the base is saturated and the 1.0 and 1.5 bounds computed from it are lower bounds on the true size>
  - Per-parent sum, one line per parent split this round: <n/a in round 1, whose only parent is the original story, so the whole-story sum line records its band once; otherwise parent <key> <recorded value>; 1.0 times = <value>, 1.5 times = <value>; sum of its slices <value> (lower), <value> (higher); band <clear | warning | stop> (lower, governs), <clear | warning | stop> (higher)>
  - Per-parent bound: <pass, or each slice at or above its parent: parent <key> <value>, slice <key> <value>, band <band of that parent's sum>>
  - Round cap: <n/a before split round 2; pass; or each slice still meeting the split trigger after split round 2, with its value>
  - Ledger owners reassigned: <n/a in split round 1; in split round 2, for each slice split again, parent <key>: each unknown it owned with its ledger price and the sub-slice that now owns it>
  - Warning for the human at triage: <none, or one entry listing every warning of the round with its sums, bands and bounds above, posted in the split comment; a round that stops also carries it in its `needs input` message and posts it once the owner answers>
```

The round's result is the most severe of its lines: any stop makes the round a stop, else any warning makes it a warning, else it is clear.
With a leaf slice recorded as unpointed, the whole-story sum line and the per-parent sum line of each parent with an unpointed slice read `sum at least <recorded lower values summed> (lower), at least <recorded higher values summed> (higher); unpointed <slice keys>; band <stop | pending>` in place of their sums and band, with band stop when the lower bound is above 1.5 times the base and band pending otherwise; a per-parent bound stop under such a parent records that parent's band, and every other line is computed.
The round's result then ranks stop, then pending, then warning, then clear, and a warning on a computed line is still listed in the warning line.

Worked examples on `fibonacci` (1, 2, 3, 5, 8, 13) with `profile.refinement.point_cap` 5 unless stated.
In round 1 the only parent is the original story, so its per-parent sum and the whole-story sum share one base and one band, recorded once on the whole-story sum line; a slice at or above that parent still stops on its own.
Each slice is listed by its recorded lower-consensus value, with its higher value in brackets where the two differ.

| Case | Original | Slices | Sum against 1.0 and 1.5 times | Result |
|---|---|---|---|---|
| Hard stop: the lowest sum above 1.5 times an original of 8 with every slice below 8 | 8 | 5, 5, 3 | 13 against 8 and 12 | stop: `needs input` naming the sums 13 (lower) and 13 (higher), the bands stop (lower) and stop (higher), the bounds 8 and 12, and round 1 |
| Lower consensus governs: the lower sum warns while the higher sum would stop | 8 | 3 (5), 3 (5), 3 (5) | 9 (lower) and 15 (higher) against 8 and 12 | proceeds; the split comment carries the warning naming the sums 9 (lower) and 15 (higher), the bands warning (lower) and stop (higher), the bounds 8 and 12, and round 1 |
| Two failures in one round | 8 | 8, 5 | 13 against 8 and 12 | stop: one `needs input` message naming both failures, the per-parent bound (parent 8, slice 8) and the band stop of the sum 13 |
| Warning band: the highest sum at or below 1.5 times an original of 8 | 8 | 5, 5, 2 | 12 against 8 and 12 | proceeds; the split comment carries the warning |
| Clear band: the highest sum at or below 1.0 times an original of 8 | 8 | 5, 3 | 8 against 8 and 12 | proceeds with no flag |
| Per-parent bound: a child equal to its parent | 8 | 8, 3 | 11 against 8 and 12 | stop: parent 8, slice 8, both values, band warning |
| Per-parent bound: siblings above 1.5 times their round-2 parent | 13; round 1 8, 5 | the 8 split into 5, 5, 3 | parent 8: 13 against 8 and 12 (stop); whole story: leaves 5, 5, 3, 5 sum 18 against 13 and 19.5 (warning) | stop: parent 8, siblings 5, 5, 3, band stop; the whole-story line records its warning |
| Per-parent bound: every child below its parent | 8 | 5, 3 | 8 against 8 and 12 | proceeds with no flag |
| Round cap, `point_cap` 3: a slice still meets the trigger after split round 2 | 13; round 1 8, 5 | round 2: 8 into 5, 3; 5 into 3, 2 | leaf sum 13 against 13 and 19.5 | stop before a third split: `needs input` naming the slice at 5 |
| Round cap, `point_cap` 3: a split that completes within two rounds | 8; round 1 5, 3 | round 2: 5 into 3, 2 | leaf sum 8 against 8 and 12 | proceeds unchanged |
| Saturated base: a top-of-scale whole story | 13 | 8, 8, 5 | 21 against 13 and 19.5 | stop: the message names the base 13 saturated and the bounds 13 and 19.5 as lower bounds on the true size |

Mapping check worked examples, in split round 1 of a story with criteria AC1 to AC3.

| Case | Story criteria | Slice criteria mapped | Result |
|---|---|---|---|
| Mapping check stop: a slice criterion with no counterpart | AC1, AC2, AC3 | slice A: A1 -> AC1, A2 -> AC2; slice B: B1 -> AC3, B2 -> none | stop before any slice is pointed: one `needs input` message with `Mapping check, round 1: stop` naming B2; no slice is pointed and no split bound runs |
| Mapping check clear: every slice criterion maps to exactly one criterion of the story | AC1, AC2, AC3 | slice A: A1 -> AC1, A2 -> AC1, A3 -> AC2; slice B: B1 -> AC3 | proceeds unchanged: the slices are pointed and the split bounds run |

## Triage record

Post this as a tracker comment authored by the product owner as a triage write, on every refinement outcome and on each split sibling, and posted by the product owner or, under the denied tracker writes fallback, by the facilitator verbatim.
The priority is the value read back after the PO applied it; when the PO could not decide, the priority stays unset and the comparison line carries `needs input` with the open question.

```markdown
## Triage record

- Priority: <the decided value, read back; or unset when the PO could not decide>
- Priority comparison: <each comparable story's identifier and priority; or `needs input` with the open question when the PO could not decide>
- State: <for a Bug, an Investigation or a Spike: ready: all conditions met, or backlog with each unmet condition, or for an issue already in progress or later its retained state with all conditions met or with each unmet condition; for a Spike with more than one independent research thread the unmet condition reads re-file as separate Spikes (owner); when the `Scope signal:` line is missing or carries neither of its type's readings the unmet condition reads scope signal missing; omitted for a User Story>
- Tracker writes: product owner
```

Under the denied tracker writes fallback in `SKILL.md`, replace the tracker-writes line with:

```markdown
- Tracker writes: facilitator on the product owner's behalf (owner's direct authorization: "<verbatim quote>", <date>)
```

## Permitted and forbidden phrasing

The SM/EM may give factual, reference-only sizing context after all three values are recorded.
Everything in the forbidden column breaks independence or anchors the discussion.
A factual reference is permitted and a prescription is not: naming an already-estimated item's recorded value, alone or together with a basis difference, is a reference the voters weigh, while a value to score, a target or a preferred direction for the story under estimate is a prescription that anchors the round.
A permitted comparison names at most one comparable story and at most one basis difference; it never prescribes a value for the story under estimate, names a range, an average, elapsed time or effort, and it names another story's point value only after all three values are recorded.

| Permitted (factual, reference-only) | Forbidden (leading or anchoring) |
|---|---|
| "The comparable story was 5 points." | "I would go higher." |
| "The named story had three interacting constraints; this one has four." | "I would go lower." |
| "This story has one more integration than that one." | "A target of 8 fits." |
| "The prior story also changed the schema." | "I think it is 5." |
| "That story carried no migration." | "The highest vote is the realistic one." |
| "The scope differs in the deploy leg." | "The lowest vote is the realistic one." |
| "This story has one more unknown than that one." | "Let us re-vote after I explain." |
| "The comparable story had the same interacting constraints." | "The two of you are far apart." |
| "The earlier story was split once." | Comparing individual votes before the discussion. |
| "No comparable story exists." | Naming a preferred direction or value. |
| "The named story had one fewer external dependency." | "This would take a week." |

Record every SM/EM sizing comment with the pointing record, even when it stays inside the permitted column.
