# SKL-78 pointing record

This file is the exact text posted on SKL-78 as its only pointing record, comment `e0bcb6f8`.

## Pointing record

- Supersession: this is the only pointing record for this run; no earlier record for SKL-78 exists.
- Tracker-write preflight: comment `c671f2cd` on SKL-78.
- Refined story identifier: the fixture description as filed; no refinement round was run on a disposable tabletop.
- Estimate scale: fibonacci
- Values, recorded before the discussion:
  - Product owner: 3 - "The byte-identical requirement on the existing dry-run output is the main risk of silently breaking existing behaviour, and the path whose size cannot be determined is an edge case the change must absorb without failing the run."
  - Engineer one: 2 - "The change is additive and low-design, but AC2 imposes an interacting constraint - the byte column must be added without altering the byte-identical legacy output - and the unknown-size edge case (AC3) is a small further constraint. The risk of silently changing existing output is the main complexity driver."
  - Engineer two: 5 - "Coverage is thin - no test reaches the byte column - so a silent regression there would go unnoticed."
- SM/EM sizing context, after all three values: none. The round stopped on a recorded rationale before any sizing context was offered, and none was offered after the re-run.
- Discussion: high 5, low 2. The required discussion round was held in the newly created voter contexts after the blind re-vote; it named only the high and the low, and no other value was compared.
- Re-vote: product owner {2, 3} - "This is a small additive change to an existing dry-run path with low design difficulty and no new interacting constraints; the only admitted driver is a contained risk of breaking existing behaviour, which the byte-identical requirement bounds rather than increases."; engineer one {2} - "The only complexity is an interacting constraint - the byte column must be purely additive so the output without it stays byte-identical, plus a fallback for undeterminable sizes. That is a small, well-scoped risk of changing existing output behaviour, with no meaningful design difficulty or unknowns."; engineer two {2} - "Complexity is low - the main driver is the byte-identical output constraint, a single interacting constraint carrying a modest risk of silently changing existing dry-run behaviour, while the size computation and the unknown-size fallback are routine and add no points."
- Consensus: 2 (the highest value in the intersection {2})
- No-consensus decision: n/a
- Paths accepted: n/a
- Decision rationale: n/a
- Effective maximum: 5 (the 8-point rule still triggers at 8 or more)
- Split: none
- Challenges: engineer two's coverage ground - "Coverage is thin - no test reaches the byte column - so a silent regression there would go unnoticed." - challenged in the discussion round with "Engineer two, your recorded rationale weighs coverage - that no test reaches the byte column - which is out of basis under the delivered rule. Restate it as a basis driver, or retract it. A restatement must name a genuinely different property of the change; restating the same ground in other words, or calling coverage an unknown, does not count." Outcome: retracted. No other ground was challenged; the round-one target value is an immediate event, not a challengeable ground, and is recorded under Anchoring events.
- Superseded values after a void: the round-one values with their rationales - product owner 2 - "The only real complexity is the interacting constraint that the dry-run output without the byte column must stay byte-identical to the previous release, which carries a modest risk of silently changing existing behaviour, plus the small unknown of a size that cannot be determined. Design difficulty beyond that is low."; engineer one 2 - "This should be 2 rather than 3, because the earlier cleanup flag landed at two."; engineer two 2 - "The change is an additive display column, but it carries a real backward-compatibility constraint (AC2's byte-identical requirement when the column is absent) and an unknown-size edge case (AC3), both of which the basis admits as complexity drivers; the design itself remains simple." - together with the voided consensus position (none had been reached), replaced by the three independent blind re-vote values above.
- Anchoring events: engineer one's recorded rationale naming a target value for this story, an anchoring event as soon as the facilitator saw it, with no challenge, restatement or retraction path; the sentence is quoted verbatim in `raw-record.md`, cited here by its base name, and elided from this record. Recovery under the single void rule: the consensus position and the three recorded values were voided, no discussion was opened on the tainted thread, and the independent vote from Step 3 was re-run blind in newly created voter contexts; the required Step 4 discussion round and re-vote were then held in those fresh contexts.
- Tracker writes: product owner
