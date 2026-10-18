# Refinement and pointing records

Hand-written templates for the records the ceremony posts.
Use the refinement comment to identify the refined story and the pointing record to capture the consensus.
Replace every placeholder and keep the raw voter files under `profile.workspace.scratch_dir`.

## Refinement comment

Post this as a tracker comment by the product owner, the only tracker mutator.
Its comment id is the refined story identifier for both stages.

```markdown
## Refinement record

- Story: <issue key> at <description version or commit>
- Refined story identifier: <this comment id>
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
- Result: <accepted or unpointed>
```

## Pointing record

Post this after the re-vote, or record it as an unpointed result.
The three values are recorded before any SM/EM sizing comment or discussion.

```markdown
## Pointing record

- Refined story identifier: <refinement comment id>
- Estimate scale: <profile.tracker.estimate_scale>
- Values, recorded before the discussion:
  - Product owner: <value> - <short rationale>
  - Engineer one: <value> - <short rationale>
  - Engineer two: <value> - <short rationale>
- SM/EM sizing context, after all three values: <scratch path or verbatim>
- Discussion: high <value>, low <value>
- Re-vote: <value each voter accepts>
- Consensus: <value, or none>
- Effective cap: <lower of profile.refinement.point_cap and 8>
- Split: <none, or the slice mapping and sibling issue keys>
- Anchoring events: <none, or the verbatim comment and the recovery>
```

## Permitted and forbidden phrasing

The SM/EM may give factual, reference-only sizing context after all three values are recorded.
Everything in the forbidden column breaks independence or anchors the discussion.

| Permitted (factual, reference-only) | Forbidden (leading or anchoring) |
|---|---|
| "The comparable story was 5 points." | "I would go higher." |
| "A similar change took two cycles." | "I would go lower." |
| "This story has one more integration than that one." | "A target of 8 fits." |
| "The prior story also changed the schema." | "I think it is 5." |
| "That story carried no migration." | "The highest vote is the realistic one." |
| "The scope differs in the deploy leg." | "The lowest vote is the realistic one." |
| "The historical range for this area is 3 to 8." | "Let us re-vote after I explain." |
| "The comparable work included tests and docs." | "The two of you are far apart." |
| "The earlier story was split once." | Comparing individual votes before the discussion. |
| "No comparable story exists." | Naming a preferred direction or value. |

Record every SM/EM sizing comment with the pointing record, even when it stays inside the permitted column.
