# SKL-59 AC2 pointing record (posted on SKL-72)

This is the pointing record posted on the fixture, reproduced here unchanged so the repository holds the same artefact the tracker does. One ceremony ran two rounds on this fixture: the first raised the voter grounds and stopped on the unretracted one, and the second raised the off-basis SM/EM sizing note and stopped on sight. Each injected ground and each facilitator challenge is quoted verbatim.

## Round 1 - the voter grounds

- Tracker-write preflight: not run; this fixture was a disposable tabletop and the record was posted directly by the facilitator.
- Refined story identifier: the fixture description as filed, no refinement round was run.
- Estimate scale: fibonacci
- Values, recorded before the discussion:
  - Product owner: 2 - "The main driver is the regression risk the change carries - AC2 pins the existing dry-run output byte-identical, so the flag must be purely additive without disturbing current behaviour - plus the mild design unknown of how 'content differs from the last committed state' is determined against git state."
  - Engineer one: 2 - "An additive flag whose only design decision is how to detect a candidate that differs from the last committed state, with the interacting constraint that the default dry-run output stays byte-identical as the main, low risk of breaking existing behaviour."
  - Engineer two: 3 - "The flag adds one interacting constraint - determining which candidate paths differ from the last committed state - and carries a regression risk that the unfiltered dry run must remain byte-identical."
- SM/EM sizing context, after all three values: "The earlier cleanup flag landed at three; this story carries one more interacting constraint than that one." A comparison against an already-estimated item with one basis difference, permitted after the reveal.
- Discussion: high 3, low 2.
- Challenges:
  - Injected ground, product owner: "The acceptance criteria are checkable only by phrase tests in the skill text, so verification strength is the main thing I weighed."
    Challenge: "Product owner, your recorded rationale weighs verification strength - checkability by phrase tests - and the delivered rule puts verification strength, testability, coverage and the shape of the tests out of basis. Restate it as a basis driver or retract it."
    Outcome: retracted - "Verification strength is out of basis and I have no independent basis driver to substitute for it."
  - Injected ground, engineer one: "Testability is weak here: the flag's behaviour can only be confirmed by reading the skill text, and that is what I weighed."
    Challenge: "Engineer one, your recorded rationale weighs testability - confirming the behaviour only by reading the skill text - which is out of basis. Restate it as a basis driver or retract it."
    Outcome: retracted - "My original ground was purely about testability (the behaviour only being confirmable by reading the skill text), which is out of basis under the delivered rule. I have no genuinely different basis driver to restate it as, so I retract it."
  - Injected ground, engineer two: "Coverage is thin - no test reaches the new filter path - so a silent regression there would go unnoticed."
    Challenge: "Engineer two, your recorded rationale weighs coverage - that no test reaches the new filter path - which is out of basis. Restate it as a basis driver or retract it."
    Outcome: unretracted - "I stand by the recorded rationale." Neither restated nor retracted, so this ground is an anchoring event.
- Superseded values after a void: engineer two's round-one value 3 with its rationale, the voided consensus position (none had been reached), and the three blind re-run values with their rationales that replaced the round-one set.
- Anchoring events: engineer two's coverage ground, quoted verbatim above. Recovery under the single void rule: the consensus position and the vote that ground carries were voided, and the independent vote was re-run blind in newly created voter contexts that exclude the tainted discussion and sizing comment.
- Re-vote: product owner {2} - "The change is a purely additive flag on the dry-run output, so the risk of breaking existing behaviour is low and constrained by AC2's byte-identical requirement; the only real design decision is what 'differs from the last committed state' covers, a small contained unknown."; engineer one {2} - "A single additive `--changed-only` filter over the existing dry run introduces no interacting constraints or unknowns; the only admitted driver is the byte-identical no-flag output requirement, a containment risk to existing behaviour rather than design difficulty."; engineer two {2} - "A single additive flag whose only admitted driver is the interacting constraint that the default dry-run output stay byte-identical (AC2); the changed-state comparison is well-understood and carries no real design difficulty or unknowns."
- Consensus: 2 (the highest value in the intersection {2})
- No-consensus decision: n/a
- Paths accepted: n/a
- Decision rationale: n/a
- Effective maximum: 5 (the 8-point rule still triggers at 8 or more)
- Split: none

## Round 2 - the off-basis SM/EM sizing note

- Values, recorded before the discussion:
  - Product owner: 3 - "Deciding whether a candidate path differs from the last committed state adds a git-comparison interacting constraint on the existing dry-run path, and AC2's byte-identical default output requirement carries a real risk of breaking existing behaviour."
  - Engineer one: 3 - "Adding a git-state comparison introduces a new interacting constraint with the existing dry-run path, and the byte-identical default output carries a real risk of silently changing existing behaviour."
  - Engineer two: 3 - "Detecting which candidate paths differ from the last committed state is a design unknown that must integrate with the existing dry-run path, and the byte-identical default-output requirement carries a real risk of silently breaking existing behaviour."
- SM/EM sizing context, after all three values: "The earlier tabletop on this same fixture settled at three, so this one should settle at three as well."
  Challenge: "That sizing note names a target value for this story, three, implied by this fixture's own earlier pointing; the delivered rule makes it an anchoring event as soon as it is seen, with no challenge, restatement or retraction path."
  Outcome: an anchoring event on sight. The round stopped before the discussion opened; the consensus position and the three recorded values were voided, and the discussion was never resumed.
- Discussion: none held.
- Challenges: the sizing note above, quoted verbatim; no voter ground was challenged in this round.
- Superseded values after a void: the three round-two values (3, 3, 3) with their rationales and the voided consensus position (none had been reached), replaced by the blind vote below.
- Anchoring events: the SM/EM sizing note naming a target value for this story. Recovery under the single void rule: the independent vote was re-run blind in newly created voter contexts that exclude the tainted sizing comment.
- Values after the blind re-run, recorded before its discussion:
  - Product owner: 2 - "A single, well-scoped filter whose main drivers are the interacting constraint of keeping the no-flag output byte-identical (a risk of breaking existing behaviour) and the modest design question of deciding what 'differs from the last committed state' means for each candidate path."
  - Engineer one: 3 - "The change must leave the default dry-run output byte-identical, so it carries a real risk of breaking existing behaviour, and 'differs from the last committed state' introduces unknowns over which candidate paths (new, modified, deleted) qualify."
  - Engineer two: 2 - "A single well-understood flag, but it must compare each candidate path against the last committed state (a git-comparison design detail) while keeping the default dry-run output byte-identical, which is the main risk of breaking existing behaviour."
- Discussion after the re-run: high 3, low 2.
- Re-vote after the re-run: product owner {2} - "A single, well-understood filter flag whose only interacting constraint is preserving the default dry-run output byte-for-byte, with no real unknowns; detecting a path's difference from the last committed state is a standard comparison, so complexity stays low."; engineer one {3} - "The filter is additive and opt-in, so design difficulty is low and the default dry-run path's output is preserved by construction; the only substantive driver is the risk of breaking existing behaviour that the byte-identical guarantee pins down, and the diff-against-committed-state check is a well-understood operation with no interacting constraints or unknowns."; engineer two {2, 3} - "The only non-routine driver is the risk of breaking existing behaviour, since the flag must leave the default dry-run output byte-identical; determining which paths differ from the last committed state is otherwise a small, well-understood comparison with no meaningful unknowns or additional interacting constraints."
- Consensus: none; the intersection of {2}, {3} and {2, 3} is empty.
- No-consensus decision: re-refine, chosen by the group. Product owner accepted {re-refine, leave unpointed}, engineer one {re-refine}, engineer two {re-refine}; the intersection is {re-refine}. Amendments offered by the voters: clarify the acceptance criteria that separate a 2-point from a 3-point scope, enumerate the discrete tasks so the boundary is explicit, and state which optional work is in scope.
- Paths accepted: product owner {re-refine, leave unpointed}; engineer one {re-refine}; engineer two {re-refine}
- Decision rationale: the only path in all three accepted sets is re-refine; the fixture is disposed here and the re-refine is not run.
- Effective maximum: 5 (the 8-point rule still triggers at 8 or more)
- Split: none

## Tracker writes

Facilitator on the product owner's behalf for this disposable fixture.
