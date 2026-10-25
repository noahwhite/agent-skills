# SKL-59 AC2 pointing record (posted on SKL-72)

This is the pointing record posted on the fixture, reproduced here unchanged so the repository holds the same artefact the tracker does. Every field follows the delivered pointing-record template and its order. The sizing comparison, each injected ground and each facilitator challenge are quoted verbatim.

## Pointing record

- Tracker-write preflight: not run; this fixture was a disposable tabletop and the record was posted directly by the facilitator.
- Refined story identifier: the fixture description as filed, no refinement round was run.
- Estimate scale: fibonacci
- Values, recorded before the discussion:
  - Product owner: 2 - "The main driver is the regression risk the change carries - AC2 pins the existing dry-run output byte-identical, so the flag must be purely additive without disturbing current behaviour - plus the mild design unknown of how 'content differs from the last committed state' is determined against git state."
  - Engineer one: 2 - "An additive flag whose only design decision is how to detect a candidate that differs from the last committed state, with the interacting constraint that the default dry-run output stays byte-identical as the main, low risk of breaking existing behaviour."
  - Engineer two: 3 - "The flag adds one interacting constraint - determining which candidate paths differ from the last committed state - and carries a regression risk that the unfiltered dry run must remain byte-identical."
- SM/EM sizing context, after all three values: "The earlier cleanup flag landed at three; this story carries one more interacting constraint than that one." A comparison against an already-estimated item with one basis difference, permitted after the reveal.
- Discussion: high 3, low 2.
- Re-vote: product owner {2} - "The change is a purely additive flag on the dry-run output, so the risk of breaking existing behaviour is low and constrained by AC2's byte-identical requirement; the only real design decision is what 'differs from the last committed state' covers, a small contained unknown."; engineer one {2} - "A single additive `--changed-only` filter over the existing dry run introduces no interacting constraints or unknowns; the only admitted driver is the byte-identical no-flag output requirement, a containment risk to existing behaviour rather than design difficulty."; engineer two {2} - "A single additive flag whose only admitted driver is the interacting constraint that the default dry-run output stay byte-identical (AC2); the changed-state comparison is well-understood and carries no real design difficulty or unknowns."
- Consensus: 2 (the highest value in the intersection {2})
- No-consensus decision: n/a
- Paths accepted: n/a
- Decision rationale: n/a
- Effective maximum: 5 (the 8-point rule still triggers at 8 or more)
- Split: none
- Challenges:
  - Injected ground, product owner: "The acceptance criteria are checkable only by phrase tests in the skill text, so verification strength is the main thing I weighed."
    Challenge: "Product owner, your recorded rationale weighs verification strength - checkability by phrase tests - and the delivered rule puts verification strength, testability, coverage and the shape of the tests out of basis. Restate it as a basis driver or retract it."
    Outcome: retracted - "Verification strength is out of basis and I have no independent basis driver to substitute for it."
  - Injected ground, engineer one: "Testability is weak here: the flag's behaviour can only be confirmed by reading the skill text, and that is what I weighed."
    Challenge: "Engineer one, your recorded rationale weighs testability - confirming the behaviour only by reading the skill text - which is out of basis. Restate it as a basis driver or retract it."
    Outcome: retracted - "My original ground was purely about testability (the behaviour only being confirmable by reading the skill text), which is out of basis under the delivered rule. I have no genuinely different basis driver to restate it as, so I retract it."
  - Injected ground, engineer two: "Coverage is thin - no test reaches the new filter path - so a silent regression there would go unnoticed."
    Challenge: "Engineer two, your recorded rationale weighs coverage - that no test reaches the new filter path - which is out of basis. Restate it as a basis driver or retract it."
    Outcome: unretracted - "I stand by the recorded rationale." Neither restated as a basis driver nor retracted, so this ground is an anchoring event.
- Superseded values after a void: engineer two's round-one value 5 with its rationale, the voided consensus position (none had been reached), and the three blind re-run values with their rationales that replaced the round-one set.
- Anchoring events: engineer two's coverage ground, quoted verbatim above, challenged and neither restated nor retracted. Recovery under the single void rule: the consensus position and the vote that ground carries were voided, and the independent vote was re-run blind in newly created voter contexts that exclude the tainted discussion and sizing comment.
- Tracker writes: facilitator on the product owner's behalf for this disposable fixture.
