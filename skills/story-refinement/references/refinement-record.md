# Refinement and pointing records

Hand-written templates for the records the ceremony posts.
Use the refinement comment to identify the refined story and the pointing record to capture the consensus.
Replace every placeholder and keep the raw voter files under `profile.workspace.scratch_dir`.

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
  - Product owner: <scratch path>
  - Engineer one (<family or model>): <scratch path>
  - Engineer two (<family or model>): <scratch path>
- SM/EM contribution (not a vote): <scratch path>
- Definition of Ready verdicts: <verdict per voter>
- Blocking amendments: <none, or the exact amendments>
- Non-blocking notes: <summary or none>
- Accept round 1: <ACCEPT or OBJECT per voter>
- Accept round 2 (only after a blocking amendment): <ACCEPT or OBJECT per voter>
- Re-refine accept round (only after a Step 4 re-refine; one round): <ACCEPT or OBJECT per voter, or n/a>
- Result: <accepted or unpointed>
- Tracker writes: product owner
```

Under the denied tracker writes fallback in `SKILL.md`, replace the tracker-writes line with:

```markdown
- Tracker writes: facilitator on the product owner's behalf (owner's direct authorization: "<verbatim quote>", <date>)
```

## Pointing record

Post this after the re-vote, or record it as an unpointed result.
The three values are recorded before any SM/EM sizing comment or discussion.

```markdown
## Pointing record

- Tracker-write preflight: comment <id>
- Refined story identifier: <latest refinement comment id after any amendment>
- Estimate scale: <profile.tracker.estimate_scale>
- Values, recorded before the discussion:
  - Product owner: <value> - <short complexity rationale>
  - Engineer one: <value> - <short complexity rationale>
  - Engineer two: <value> - <short complexity rationale>
- SM/EM sizing context, after all three values: <scratch path or verbatim>
- Discussion: high <value>, low <value>
- Re-vote: <accepted set per voter, with complexity rationale>
- Consensus: <highest value in the intersection, or none>
- No-consensus decision: <split, re-refine, or leave unpointed; n/a when there is a consensus>
- Paths accepted: <set per voter, or n/a>
- Decision rationale: <one line, or n/a>
- Effective maximum: <profile.refinement.point_cap; the 8-point rule still triggers at 8 or more>
- Split: <none, or the slice mapping and sibling issue keys>
- Anchoring events: <none, or the verbatim comment and the recovery, including the newly created voter contexts>
- Tracker writes: product owner
```

Under the denied tracker writes fallback in `SKILL.md`, replace the tracker-writes line with:

```markdown
- Tracker writes: facilitator on the product owner's behalf (owner's direct authorization: "<verbatim quote>", <date>)
```

## Permitted and forbidden phrasing

The SM/EM may give factual, reference-only sizing context after all three values are recorded.
Everything in the forbidden column breaks independence or anchors the discussion.
A permitted comparison names at most one comparable story and at most one complexity difference; it never names a range, an average, elapsed time, effort, or a preferred value.

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
