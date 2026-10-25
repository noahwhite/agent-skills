# SKL-59 AC2 pointing record (posted on SKL-72)

This is the pointing record posted on the fixture, reproduced here unchanged so the repository holds the same artefact the tracker does. The target quotation is elided here and lives in `raw-record.md`, cited by base name.

## Pointing record

- Delivered text loaded: `702f53c9ab6fe4209fd4600ad2224c6e0431671a`, from a worktree checkout of that commit.
- Fixture: SKL-72, disposable tabletop, priority none, no implementation, canceled after the run.
- Estimate scale: fibonacci
- Values, recorded before the discussion:
  - Product owner: 2 - "The main driver is the regression risk the change carries - AC2 pins the existing dry-run output byte-identical, so the flag must be purely additive without disturbing current behaviour - plus the mild design unknown of how 'content differs from the last committed state' is determined against git state."
  - Engineer one: 2 - "An additive flag whose only design decision is how to detect a candidate that differs from the last committed state, with the interacting constraint that the default dry-run output stays byte-identical as the main, low risk of breaking existing behaviour."
  - Engineer two: 3 - "The flag adds one interacting constraint - determining which candidate paths differ from the last committed state - and carries a regression risk that the unfiltered dry run must remain byte-identical."
- SM/EM sizing context, after all three values: a comment naming a target value for this story implied by an inherited split pointing; elided here, verbatim in the raw session record, base name `raw-record.md`.
- Discussion: high 3, low 2.
- Challenges:
  - "Product owner, your recorded rationale weighs verification strength - checkability by phrase tests - and the delivered rule puts verification strength, testability, coverage and the shape of the tests out of basis. Restate it as a basis driver or retract it." Outcome: retracted, "Verification strength is out of basis and I have no independent basis driver to substitute for it."
  - "Engineer one, your recorded rationale weighs testability - confirming the behaviour only by reading the skill text - which is out of basis. Restate it as a basis driver or retract it." Outcome: retracted.
  - "Engineer two, your recorded rationale weighs coverage - that no test reaches the new filter path - which is out of basis. Restate it as a basis driver or retract it." Outcome: unretracted, "I stand by the recorded rationale."
  - "The SM/EM sizing comment names a target value for this story implied by the inherited 3-point split pointing; under the delivered rule that is an anchoring event as soon as it is seen, with no challenge, restatement or retraction path, so the comment is recorded and the round stops." Outcome: anchoring event; the comment is quoted verbatim in the raw session record and elided here.
- Superseded values after a void: the round-one values (product owner 2, engineer one 3, engineer two 5) with their rationales, together with the voided consensus and the sizing comment; the blind vote that replaced them is the values block above.
- Re-vote: product owner {2}, engineer one {2}, engineer two {2}
- Consensus: 2 (the highest value in the intersection {2})
- No-consensus decision: n/a
- Paths accepted: n/a
- Decision rationale: n/a
- Effective maximum: 5 (the 8-point rule still triggers at 8 or more)
- Split: none
- Anchoring events: the SM/EM sizing comment naming a target value for this story, quoted verbatim in the raw session record and elided here; engineer two's coverage ground, challenged and neither restated nor retracted. Recovery under the single void rule: the consensus and the three round-one values were voided, and the independent vote was re-run blind in newly created voter contexts that exclude the tainted discussion and sizing comment.
