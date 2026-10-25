# SKL-59 AC2 pointing record (posted on SKL-72)

This is the pointing record posted on the fixture, reproduced here unchanged so the repository holds the same artefact the tracker does. Every field follows the delivered pointing-record template and its order. The target quotation is elided here and lives in `raw-record.md`, cited by base name.

## Pointing record

- Tracker-write preflight: not run; this fixture was a disposable tabletop and the record was posted directly by the facilitator.
- Refined story identifier: the fixture description as filed, no refinement round was run.
- Estimate scale: fibonacci
- Values, recorded before the discussion:
  - Product owner: 2 - "The main driver is the regression risk the change carries - AC2 pins the existing dry-run output byte-identical, so the flag must be purely additive without disturbing current behaviour - plus the mild design unknown of how 'content differs from the last committed state' is determined against git state."
  - Engineer one: 2 - "An additive flag whose only design decision is how to detect a candidate that differs from the last committed state, with the interacting constraint that the default dry-run output stays byte-identical as the main, low risk of breaking existing behaviour."
  - Engineer two: 3 - "The flag adds one interacting constraint - determining which candidate paths differ from the last committed state - and carries a regression risk that the unfiltered dry run must remain byte-identical."
- SM/EM sizing context, after all three values: a comment naming a target value for this story implied by an inherited split pointing; elided here, verbatim in the raw session record, base name `raw-record.md`.
- Discussion: high 3, low 2.
- Re-vote: product owner {2} - "The change is a purely additive flag on the dry-run output, so the risk of breaking existing behaviour is low and constrained by AC2's byte-identical requirement; the only real design decision is what 'differs from the last committed state' covers, a small contained unknown."; engineer one {2} - "A single additive `--changed-only` filter over the existing dry run introduces no interacting constraints or unknowns; the only admitted driver is the byte-identical no-flag output requirement, a containment risk to existing behaviour rather than design difficulty."; engineer two {2} - "A single additive flag whose only admitted driver is the interacting constraint that the default dry-run output stay byte-identical (AC2); the changed-state comparison is well-understood and carries no real design difficulty or unknowns."
- Consensus: 2 (the highest value in the intersection {2})
- No-consensus decision: n/a
- Paths accepted: n/a
- Decision rationale: n/a
- Effective maximum: 5 (the 8-point rule still triggers at 8 or more)
- Split: none
- Challenges: the product owner's verification-strength ground, challenged and retracted ("Verification strength is out of basis and I have no independent basis driver to substitute for it."); engineer one's testability ground, challenged and retracted (no substitute basis driver offered); engineer two's coverage ground, challenged and neither restated nor retracted ("I stand by the recorded rationale."); the SM/EM sizing comment, named by kind as an anchoring event as soon as the facilitator saw it, with no restatement or retraction path.
- Superseded values after a void: the round-one values (product owner 2, engineer one 3, engineer two 5) with their rationales, the voided consensus, and the blind vote that replaced them - the values block above.
- Anchoring events: the SM/EM sizing comment naming a target value for this story, quoted verbatim in the raw session record under base name `raw-record.md` and elided here; engineer two's coverage ground, challenged and neither restated nor retracted. Recovery under the single void rule: the consensus and the three round-one values were voided, and the independent vote was re-run blind in newly created voter contexts that exclude the tainted discussion and sizing comment.
- Tracker writes: facilitator on the product owner's behalf for this disposable fixture.
