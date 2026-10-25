# Refinement and pointing records

Hand-written templates for the records the ceremony posts.
Use the refinement comment to identify the refined story, the Accept round result to record each accept round, and the pointing record to capture the consensus.
Replace every placeholder and keep the raw voter files in the session's scratch directory.
The record never carries a local path; cite each raw voter file by its base name only.
Quote or attach any file content a reader needs in the record.

## Refinement comment

Post this as a tracker comment authored by the product owner, the only author of tracker writes, and posted by the product owner or, under the denied tracker writes fallback, by the facilitator verbatim.
Its comment id is the refined story identifier for both stages.

```markdown
## Refinement record

- Story: <issue key> at <description version or commit>
- Tracker-write preflight: comment <id>
- Refined story identifier: <this comment id>
- Refined story snapshot: <the complete refined story and ACs, or an immutable link/commit>
- Refined story identifier after blocking amendments: <the new comment id, or none>
- Voter inputs, each recorded in its own separate context:
  - Product owner: <file base name>
  - Engineer one (<family or model>): <file base name>
  - Engineer two (<family or model>): <file base name>
- SM/EM contribution (not a vote): <file base name>
- Definition of Ready verdicts: <verdict per voter>
- Blocking amendments: <none, or the exact amendments>
- Non-blocking notes: <summary or none>
- Accept round 1: see the Accept round result comment
- Accept round 2 (only after a blocking amendment): see the Accept round result comment
- Re-refine accept round (only after a Step 4 re-refine; one round): see the Accept round result comment
- Result: see the Accept round result comment
- Tracker writes: product owner
```

Under the denied tracker writes fallback in `SKILL.md`, replace the tracker-writes line with:

```markdown
- Tracker writes: facilitator on the product owner's behalf (owner's direct authorization: "<verbatim quote>", <date>)
```

## Accept round result

Post this as a separate tracker comment after each accept round, including the Step 4 re-refine accept round, authored by the product owner and posted by the product owner or, under the denied tracker writes fallback, by the facilitator verbatim.
Never edit the refinement comment to add the result; its id keeps identifying one immutable refined version.

```markdown
## Accept round result

- Refinement comment covered: <refinement comment id>
- Round: <1, 2, or re-refine>
- Product owner: <ACCEPT or OBJECT>
- Engineer one (<family or model>): <ACCEPT or OBJECT>
- Engineer two (<family or model>): <ACCEPT or OBJECT>
- Outcome: <accepted, another round, or unpointed>
```

## Pointing record

Post this after the re-vote, or record it as an unpointed result.
The three values are recorded before any SM/EM sizing comment or discussion; a void before all three exist leaves the values block at the values recorded so far and carries no superseded values.
Outside the recorded numeric values and the superseded-values line, no line of the posted record carries a point value named before the reveal or a target value for this story: the Challenges and Anchoring events lines record a ground by its kind, its author (a voter, or the SM/EM for a sizing comment) and its outcome or recovery, and every field that could quote a participant elides those two classes permanently, because the posted record stays on the story surface that later voters read; the verbatim quote lives in the session's raw record, cited by its base name.
A sizing comment that names a point value before the reveal, names or implies a target value for this story, or states elapsed time, effort or run cost voids the round under the Anchoring guardrail recovery as soon as the facilitator sees it, as does any ground that is neither restated nor retracted, and the void records the voided consensus under Superseded values after a void, so the Consensus field always carries the vote that stands.

```markdown
## Pointing record

- Tracker-write preflight: comment <id>
- Refined story identifier: <latest refinement comment id after any amendment>
- Estimate scale: <profile.tracker.estimate_scale>
- Values, recorded before the discussion: <the three values, or the values recorded before a void>
  - Product owner: <value, or not recorded> - <short complexity rationale, or none when the value is not recorded>
  - Engineer one: <value, or not recorded> - <short complexity rationale, or none when the value is not recorded>
  - Engineer two: <value, or not recorded> - <short complexity rationale, or none when the value is not recorded>
- SM/EM sizing context, after all three values: <file base name> or verbatim, eliding a pre-reveal value or a target value, or none
- Discussion: <high <value>, low <value>, or none>
- Re-vote: <accepted set per voter, with complexity rationale, or none>
- Consensus: <highest value in the intersection of the vote that stands, or none when the intersection is empty>
- No-consensus decision: <split, re-refine, or leave unpointed; n/a when there is a consensus>
- Paths accepted: <set per voter, or n/a>
- Decision rationale: <one line, or n/a>
- Effective maximum: <profile.refinement.point_cap; the 8-point rule still triggers at 8 or more>
- Split: <none, or the slice mapping and sibling issue keys>
- Challenges: <none, or each ground challenged by kind, its author (a voter, or the SM/EM for a sizing comment), the restatement, withdrawal or retraction, or the void; elide a pre-reveal value or a target value>
- Superseded values after a void: <none, or the voided values, the voided consensus and the blind vote that replaced them>
- Anchoring events: <none, or the comment and the recovery, including the newly created voter contexts, with the verbatim comment in the raw session record and its base name cited here>
- Tracker writes: product owner
```

Under the denied tracker writes fallback in `SKILL.md`, replace the tracker-writes line with:

```markdown
- Tracker writes: facilitator on the product owner's behalf (owner's direct authorization: "<verbatim quote>", <date>)
```

## Permitted and forbidden phrasing

The SM/EM may give factual, reference-only sizing context after all three values are recorded.
Everything in the forbidden column breaks independence or anchors the discussion.
A permitted comparison names at most one comparable story and at most one basis difference; it never names a range, an average, elapsed time, effort, a target value for the story under estimate, or a preferred value, and it names a point value only after all three values are recorded.

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
