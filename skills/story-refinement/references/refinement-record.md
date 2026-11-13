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

```markdown
## Refinement record

- Story: <issue key> at <description version or commit>
- Pointing skipped: <Bug|Investigation|Spike> is unestimated (references/linear.md, Estimation and slicing)
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
The three values are recorded before any SM/EM sizing comment or discussion; a void before all three exist leaves the values block at the values recorded so far and carries no superseded values, and once the blind re-run finishes the values block carries the three standing values while the superseded line carries the voided ones.
Outside the recorded numeric values and the superseded-values line, no line of the posted record carries a point value named before the reveal or a prescription of this story's value: the Challenges and Anchoring events lines record a ground by its kind, its author (a voter, or the SM/EM for a sizing comment) and its outcome or recovery, and every field that could quote a participant elides those two classes permanently, because the posted record stays on the story surface that later voters read; the verbatim quote lives in the session's raw record, cited by its base name.
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
- SM/EM sizing context, after all three values: <file base name> or verbatim, eliding a pre-reveal value or a prescription, or none
- Discussion: <high <value>, low <value>; or none when the discussion ran and recorded nothing; or skipped, when the consensus check recorded the estimate; the shared content names only the high and the low, while a voter's own recorded value and rationale are carried privately in that voter's prompt>
- Re-vote: <accepted set per voter, with complexity rationale; or no consensus, with its complexity rationale, for a voter that records none; or none when it ran and recorded nothing; or skipped, when the consensus check recorded the estimate>
- Consensus: <the highest value in the intersection of the vote that stands, or n/a when the consensus check or the residual variance rule recorded the estimate, or none when the round stopped unpointed>
- Residual variance: <each voter's derived value, the gap between the highest and the lowest in scale steps, the rule applied and the resulting value, or the unpointed variance stop; n/a only when all three voters recorded an accepted set and the intersection is not empty, or when the consensus check, or the re-run of it that supersedes that outcome, recorded the estimate>
- Recorded estimate: <the value recorded, or unpointed with the gap between the highest and the lowest in scale steps when the round stopped there>
- Effective maximum: <profile.refinement.point_cap; the 8-point rule still triggers at 8 or more>
- Split: <none, or the slice mapping and sibling issue keys>
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

## Triage record

Post this as a tracker comment authored by the product owner as a triage write, on every refinement outcome and on each split sibling, and posted by the product owner or, under the denied tracker writes fallback, by the facilitator verbatim.
The priority is the value read back after the PO applied it; when the PO could not decide, the priority stays unset and the comparison line carries `needs input` with the open question.

```markdown
## Triage record

- Priority: <the decided value, read back; or unset when the PO could not decide>
- Priority comparison: <each comparable story's identifier and priority; or `needs input` with the open question when the PO could not decide>
- State: <for a Bug, an Investigation or a Spike: ready: all conditions met, or backlog with each unmet condition; omitted for a User Story>
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
