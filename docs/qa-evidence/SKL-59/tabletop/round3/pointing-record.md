# SKL-77 pointing record (the durable record posted on the fixture)

This file is the exact text posted on SKL-77 as comment `264d0a47`, superseding `45e5ecac`, `077378a0`, `04540f95` and `1dd2bb8c`. The record was generated from the captured outputs, so every rationale - standing and voided - matches its capture byte for byte; the target sentence is elided from the Anchoring events line and quoted verbatim in `raw-record.md`.

## Pointing record

- Tracker-write preflight: comment `19253345` on SKL-77.
- Refined story identifier: the fixture description as filed; no refinement round was run on a disposable tabletop.
- Estimate scale: fibonacci
- Values, recorded before the discussion:
  - Product owner: 2 - "The new age column must coexist with the existing dry-run output, which carries the interacting constraint of staying byte-identical when the column is absent, and reading the age from a source adds an unknown-age edge case that must not fail the run."
  - Engineer one: 2 - "The change adds an age column to existing dry-run output under a byte-identity compatibility constraint (AC2), and must handle paths whose age source is unavailable without failing (AC3), so it carries one interacting backward-compatibility constraint plus an unknown edge case."
  - Engineer two: 2 - "The change carries an interacting constraint - preserving byte-identical dry-run output when the new column is absent - and the risk of silently altering existing output when the age column is added. Handling the unknown-age case without failing the run adds a small amount of design uncertainty."
- SM/EM sizing context, after all three values: none. The round stopped on a recorded rationale before any sizing context was offered.
- Discussion: none; the round stopped on sight at the target value and no discussion was opened, before or after the re-run.
- Re-vote: product owner {2} - "The change reads an existing age source and prints one additional column, so design difficulty and unknowns are minimal; the only admitted driver is the risk of breaking existing behaviour, which the byte-identical-output constraint bounds and adds a modest interacting constraint."; engineer one {1} - "Low design difficulty: this is an additive display column with a documented source and a fallback for unknown age. The only interacting constraint is the byte-identical default output requirement, and unknowns and the risk of breaking existing behaviour are low."; engineer two {1, 2} - "Design difficulty is low (an additive column reading a path's age). The admitted drivers are the single interacting constraint of the age source and the risk of breaking existing behaviour from the byte-identical backward-compatibility requirement."
- Consensus: none; the intersection of {2}, {1}, {1, 2} is empty
- No-consensus decision: re-refine, the only path in all three accepted path sets.
- Paths accepted: product owner {re-refine}; engineer one {re-refine, leave unpointed}; engineer two {re-refine}
- Decision rationale: the three accepted path sets intersect on re-refine, and the voters' amendments ask for the acceptance criteria to make the 1-versus-2 boundary decidable, including whether the edge-case handling is in scope.
- Effective maximum: 5 (the 8-point rule still triggers at 8 or more)
- Split: none
- Challenges: none recorded. The immediate event below is not a challengeable ground, so no challenge was issued; the facilitator named it by kind and stopped the round.
- Superseded values after a void: the round-one values with their rationales - product owner 2 - "A single additive column over an existing dry-run output. The admitted drivers are the interacting constraint that legacy output must stay byte-identical and the mild unknown of reading an out-of-scope age source whose value may be undeterminable."; engineer one 2 - "This should be 2 rather than 3, because the earlier cleanup flag landed at two."; engineer two 2 - "The change interacts with the existing dry-run output, which must stay byte-identical when the new column is absent, and it introduces an edge case where a path's age cannot be determined and must degrade to `unknown` without failing the run." - together with the voided consensus position (none had been reached), replaced by the three independent blind re-run values above.
- Anchoring events: engineer one's recorded rationale naming a target value for this story, an anchoring event as soon as the facilitator saw it, with no challenge, restatement or retraction path; the sentence is quoted verbatim in `raw-record.md`, cited here by its base name, and elided from the Anchoring events line. Recovery under the single void rule: the consensus position and the three recorded values were voided, the discussion was never opened, and the independent vote from Step 3 was re-run blind in newly created voter contexts that exclude the tainted rationale and values.
- Tracker writes: product owner
