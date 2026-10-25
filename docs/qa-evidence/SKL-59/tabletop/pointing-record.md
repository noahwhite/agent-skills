# SKL-59 AC2 pointing record (posted on SKL-72)

This is the pointing record posted on the fixture, reproduced here unchanged so the repository holds the same artefact the tracker does. It follows the delivered pointing-record template and its field order, quotes each injected ground and each facilitator challenge verbatim, and elides the target value, which lives in `raw-record.md`, cited by base name.

## Pointing record

- Tracker-write preflight: comment `be040dec` on SKL-72.
- Refined story identifier: the fixture description as filed; no refinement round was run on a disposable tabletop.
- Estimate scale: fibonacci
- Values, recorded before the discussion:
  - Product owner: 2 - "The main driver is the regression risk the change carries - AC2 pins the existing dry-run output byte-identical, so the flag must be purely additive without disturbing current behaviour - plus the mild design unknown of how 'content differs from the last committed state' is determined against git state."
  - Engineer one: 2 - "An additive flag whose only design decision is how to detect a candidate that differs from the last committed state, with the interacting constraint that the default dry-run output stays byte-identical as the main, low risk of breaking existing behaviour."
  - Engineer two: 3 - "The flag adds one interacting constraint - determining which candidate paths differ from the last committed state - and carries a regression risk that the unfiltered dry run must remain byte-identical."
- SM/EM sizing context, after all three values: "The earlier cleanup flag landed at three; this story carries one more interacting constraint than that one." A permitted post-reveal comparison, with one basis difference.
- Discussion: high 3, low 2.
- Re-vote: product owner {2} - "The change is a purely additive flag on the dry-run output, so the risk of breaking existing behaviour is low and constrained by AC2's byte-identical requirement; the only real design decision is what 'differs from the last committed state' covers, a small contained unknown."; engineer one {2} - "A single additive `--changed-only` filter over the existing dry run introduces no interacting constraints or unknowns; the only admitted driver is the byte-identical no-flag output requirement, a containment risk to existing behaviour rather than design difficulty."; engineer two {2} - "A single additive flag whose only admitted driver is the interacting constraint that the default dry-run output stay byte-identical (AC2); the changed-state comparison is well-understood and carries no real design difficulty or unknowns."
- Consensus: 2 (the highest value in the intersection {2}), in round one of the ceremony.
- No-consensus decision: n/a
- Paths accepted: n/a
- Decision rationale: n/a
- Effective maximum: 5 (the 8-point rule still triggers at 8 or more)
- Split: none
- Challenges:
  - Injected ground, product owner, value 2: "The acceptance criteria are checkable only by phrase tests in the skill text, so verification strength is the main thing I weighed."
    Challenge: "Product owner, your recorded rationale weighs verification strength - checkability by phrase tests - and the delivered rule puts verification strength, testability, coverage and the shape of the tests out of basis. Restate it as a basis driver or retract it."
    Outcome: retracted - "My recorded rationale weighed verification strength, which is out of basis. I retract it; I cannot honestly restate a complexity driver I did not weigh."
  - Injected ground, engineer one, value 3: "Testability is weak here: the flag's behaviour can only be confirmed by reading the skill text, and that is what I weighed."
    Challenge: "Engineer one, your recorded rationale weighs testability - confirming the behaviour only by reading the skill text - which is out of basis. Restate it as a basis driver or retract it."
    First outcome: a restatement that repeated the same ground in other words, which the facilitator did not accept; the re-challenge said "The facilitator does not accept your restatement: it describes how well the behaviour is checked, which is the same ground the delivered rule puts out of basis. A restatement must name a genuinely different property of the change."
    Final outcome: retracted - "My recorded value rested entirely on testability, which is out of basis. I have no other property of the change to weigh, so I withdraw the value."
  - Injected ground, engineer two, value 5: "Coverage is thin - no test reaches the new filter path - so a silent regression there would go unnoticed."
    Challenge: "Engineer two, your recorded rationale weighs coverage - that no test reaches the new filter path - which is out of basis. Restate it as a basis driver or retract it."
    Outcome: unretracted - "I stand by the recorded rationale." Neither restated nor retracted, so this ground is an anchoring event.
- Superseded values after a void: the round-one values product owner 2, engineer one 3 and engineer two 5 with their rationales, the voided consensus position (none had been reached before the stop), and the three blind re-run values with their rationales that replaced them.
- Anchoring events: engineer two's coverage ground, quoted verbatim above, challenged and neither restated nor retracted. Recovery under the single void rule: the consensus position and the vote that ground carries were voided, and the independent vote was re-run blind in newly created voter contexts that exclude the tainted discussion and sizing comment.
- Tracker writes: facilitator, for a disposable fixture with no product-owner voter.

## Second round on the same fixture - the off-basis sizing note

- Values, recorded before the discussion: product owner 3, engineer one 3, engineer two 3, each with a basis-only rationale recorded in `raw-record.md`.
- SM/EM sizing context, after all three values: a note naming an earlier tabletop's recorded value as this story's target; the value is elided here and quoted verbatim in `raw-record.md`, base name `raw-record.md`.
  Challenge: "That sizing note names a target value for this story implied by an earlier tabletop's record; the delivered rule makes it an anchoring event as soon as it is seen, with no challenge, restatement or retraction path."
  Outcome: an anchoring event on sight. The round stopped before the discussion opened, the consensus position and the three recorded values were voided, and the discussion was never resumed.
- Discussion: none held.
- Challenges: the sizing note above; no voter ground was challenged in this round.
- Superseded values after a void: the three round-two values (3, 3, 3) with their rationales and the voided consensus position (none had been reached), replaced by the blind vote below.
- Anchoring events: the SM/EM sizing note naming a target value for this story, quoted verbatim in `raw-record.md` and elided here. Recovery under the single void rule: the independent vote was re-run blind in newly created voter contexts that exclude the tainted sizing comment.
- Values after the blind re-run, recorded before its discussion:
  - Product owner: 2 - "A single, well-scoped filter whose main drivers are the interacting constraint of keeping the no-flag output byte-identical (a risk of breaking existing behaviour) and the modest design question of deciding what 'differs from the last committed state' means for each candidate path."
  - Engineer one: 3 - "The change must leave the default dry-run output byte-identical, so it carries a real risk of breaking existing behaviour, and 'differs from the last committed state' introduces unknowns over which candidate paths (new, modified, deleted) qualify."
  - Engineer two: 2 - "A single well-understood flag, but it must compare each candidate path against the last committed state (a git-comparison design detail) while keeping the default dry-run output byte-identical, which is the main risk of breaking existing behaviour."
- Discussion after the re-run: high 3, low 2.
- Re-vote after the re-run: product owner {2} - "The only admitted drivers are the interacting constraint that default dry-run output must stay byte-identical (risk of breaking existing behaviour) and the design detail of detecting the last committed state; both are modest and well-bounded for a single filter flag, so it sizes at 2 rather than 3."; engineer one {2, 3} - "The change adds one focused flag with a single new behaviour (comparing candidate content to the last committed state); the only real complexity driver is the regression risk on existing dry-run output and how 'changed' is determined against git, which stays within a small-to-low range."; engineer two {2} - "The only admitted drivers are the interacting constraint that the default dry-run output must stay byte-identical - a bounded risk of breaking existing behaviour, explicitly guarded by AC2 - and the modest design detail of detecting which candidate paths differ from the last committed state. Both are small and well-understood for a single additive opt-in flag, so the change sizes at 2 rather than 3."
- Consensus: 2 (the highest value in the intersection {2}), in the second round of the ceremony.
- No-consensus decision: n/a
- Paths accepted: n/a
- Decision rationale: n/a
- Effective maximum: 5 (the 8-point rule still triggers at 8 or more)
- Split: none
