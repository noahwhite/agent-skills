# SKL-59 mutation evidence

Measured on the delivered text of this change with CPython 3.12.3 and locked dependencies, with every command run from the repository root.
The modified files are `skills/story-refinement/SKILL.md` and `skills/story-refinement/references/refinement-record.md`.
Before each check the document bytes were saved, the edit shown below was made once, the quoted command ran, and the saved bytes were restored even when the command failed; the final source matched the saved bytes, and the only tracked changes were then the files this change delivers.
Each entry shows the exact matched text, and the exact replacement text where the edit substitutes or inserts one, so a re-runner can reproduce it from the delivered text.
33 regression proofs failed as designed and 1 control passed.
Entries 1 to 33 are the regression proofs; entry 34 is the control.

## 1. Remove the basis-by-reference and out-of-basis sentence from Step 3 item 4

File: `SKILL.md`

Matched text:

```text
The rationale names drivers the pointing basis admits and nothing else, so verification strength, testability, coverage, the shape of the tests, a duration, effort or run-cost measure are out of basis.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`.

## 2. Remove the verification-versus-breakage sentence from Step 3 item 4

File: `SKILL.md`

Matched text:

```text
Verification strength is how well a behaviour is checked and the risk of breaking existing behaviour is what can silently change, so the first is out of basis while the second is a driver the basis admits, distinct from an interacting constraint the change carries.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`.

## 3. Remove the three narrowed value rules from Step 3 item 4

File: `SKILL.md`

Matched text:

```text
The rationale names no target value for this story, never treats another voter's revealed value as its answer, and names no point value before the reveal.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`.

## 4. Restate the pointing basis inside Step 3 item 4

File: `SKILL.md`

Matched text:

```text
     The value is written only to that voter's own file in the session's scratch directory.
```

Replaced with:

```text
     A point or size measures complexity - design difficulty, interacting constraints, unknowns, and the risk of breaking existing behaviour - and never the amount of work or elapsed time.
     The value is written only to that voter's own file in the session's scratch directory.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_does_not_restate_the_pointing_basis`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_does_not_restate_the_pointing_basis`.

## 5. Remove the pre-reveal value ban from Step 3 item 7

File: `SKILL.md`

Matched text:

```text
Before the reveal it must not name any point value.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_sizing_context_permits_a_reference_after_the_reveal_and_bans_a_target`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_sizing_context_permits_a_reference_after_the_reveal_and_bans_a_target`.

## 6. Remove the reference-after-reveal permission and the target-value ban from Step 3 item 7

File: `SKILL.md`

Matched text:

```text
After the reveal it may compare this story with an already-estimated item and name that item's recorded value, but it must not name or imply a target value for this story, including one implied by a split status, and such a statement is an anchoring event under the Anchoring guardrail.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_sizing_context_permits_a_reference_after_the_reveal_and_bans_a_target`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_sizing_context_permits_a_reference_after_the_reveal_and_bans_a_target`.

## 7. Drop the rationale rule from the pointing-prompt requirement in Step 3 item 3

File: `SKILL.md`

Matched text:

```text
, and carries the item 4 rationale rule, including the re-run
```

Replaced with:

```text
, including the re-run
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_requires_the_basis_in_every_pointing_prompt`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_requires_the_basis_in_every_pointing_prompt`.

## 8. Remove the challenge duty from Step 4 item 1

File: `SKILL.md`

Matched text:

```text
In that round, and against the rationales recorded in Step 3, the facilitator challenges every ground outside the pointing basis, whether it is heard in the discussion or read in a recorded rationale.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 9. Remove the kind-and-author rule from Step 4 item 1

File: `SKILL.md`

Matched text:

```text
Challenging a ground is not comparing values or singling out a voter: the facilitator names the ground's kind and its author, never the ground's verbatim text, and a ground that embeds a point value is named by its kind alone.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 10. Remove the restate-or-retract rule and its no-repair exceptions from Step 4 item 1

File: `SKILL.md`

Matched text:

```text
A challenged ground must be restated as a basis driver or retracted, and a voter whose basis does not support its recorded value records that in the re-vote.
     The SM/EM withdraws or restates its own sizing comment on the same terms, except a point value named before the reveal, a target value for this story, or a statement of elapsed time, effort or run cost, each of which is an anchoring event as soon as the facilitator sees it.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 11. Remove the neither-outcome rule from Step 4 item 1

File: `SKILL.md`

Matched text:

```text
A ground that is neither is an anchoring event under the Anchoring guardrail.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 12. Remove the accepted-set clarification from Step 4 item 2

File: `SKILL.md`

Matched text:

```text
Recording an accepted set is not treating another voter's revealed value as the answer: the rationale for the set is about the basis, never about which value another voter recorded.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_re_vote_challenges_an_off_basis_rationale`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_re_vote_challenges_an_off_basis_rationale`.

## 13. Remove the re-vote challenge sentence from Step 4 item 2

File: `SKILL.md`

Matched text:

```text
A re-vote rationale outside the pointing basis is challenged before the consensus is recorded, under the same restate-or-retract rule as item 1.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_re_vote_challenges_an_off_basis_rationale`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_re_vote_challenges_an_off_basis_rationale`.

## 14. Add a tenth Process item after the no-consensus decision item

File: `SKILL.md`

Matched text:

```text
     The facilitator records the decision; it does not choose it.
```

Replaced with:

```text
     The facilitator records the decision; it does not choose it.
  10. Hold a second discussion round.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_process_items_keep_their_count_and_order`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_process_items_keep_their_count_and_order`.

## 15. Remove the SM/EM value prohibition from the Anchoring guardrail

File: `SKILL.md`

Matched text:

```text
- for the SM/EM, naming a point value before the reveal, naming or implying a target value for this story, including one implied by a split status, or treating another voter's revealed value as the answer;
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_bans_the_sm_em_value_behaviours`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_bans_the_sm_em_value_behaviours`.

## 16. Remove the anchoring-trigger definition from the Anchoring guardrail

File: `SKILL.md`

Matched text:

```text
An anchoring trigger is an off-basis ground Step 4 challenges, so it becomes an anchoring event only when it is neither restated as a basis driver nor retracted:
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_names_off_basis_grounds_as_a_trigger`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_names_off_basis_grounds_as_a_trigger`.

## 17. Remove the no-repair class from the Anchoring guardrail

File: `SKILL.md`

Matched text:

```text
The SM/EM's prohibited behaviours above, and a sizing comment that names a point value before the reveal, names or implies a target value for this story, or states elapsed time, effort or run cost, are anchoring events as soon as they are seen, with no challenge, restatement or retraction path.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_makes_a_point_value_sizing_note_an_event_on_challenge`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_makes_a_point_value_sizing_note_an_event_on_challenge`.

## 18. Remove the void-and-re-run paragraph from the Anchoring guardrail

File: `SKILL.md`

Matched text:

```text
Any other challenged ground that is neither restated as a basis driver nor retracted, or a sizing comment the SM/EM neither withdraws nor restates, is an anchoring event; because a ground read in a recorded rationale taints the votes recorded before it, it supersedes the three recorded values, and the recovery re-runs the independent vote from Step 3 in newly created voter contexts that exclude the tainted discussion and sizing comment.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_makes_a_point_value_sizing_note_an_event_on_challenge`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_makes_a_point_value_sizing_note_an_event_on_challenge`.

## 19. Remove the fresh-context limitation paragraph from the Anchoring guardrail

File: `SKILL.md`

Matched text:

```text
Fresh voter contexts exclude the tainted discussion and the sizing comment, but they cannot exclude a value recorded on the story surface that Step 1 hands every voter with the story, so the Step 3 rationale rule is what keeps such a value from becoming the rationale's answer.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_explains_why_context_cannot_exclude_a_recorded_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_explains_why_context_cannot_exclude_a_recorded_value`.

## 20. Drop the vote-voiding phrase from the anchoring recovery sentence

File: `SKILL.md`

Matched text:

```text
void the consensus and any vote recorded after the anchor, and re-run the independent vote
```

Replaced with:

```text
void the consensus and re-run the independent vote
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_recovery_mechanics_are_unchanged`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_recovery_mechanics_are_unchanged`.

## 21. Remove the challenge requirement from the Records enumeration

File: `SKILL.md`

Matched text:

```text
every challenge with its outcome,
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_records_requires_every_challenge_with_its_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_records_requires_every_challenge_with_its_outcome`.

## 22. Remove the open-round redaction rule from the pointing-record intro

File: `refinement-record.md`

Matched text:

```text
While any round is open, the Challenges and Anchoring events lines record a ground by its kind, its author (a voter, or the SM/EM for a sizing comment) and its outcome or recovery, with a point value named before the reveal or a target value for this story elided, because a verbatim quote of one in an open record names it again; the verbatim quote is carried once the round closes and no further round can be anchored by it.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`.

## 23. Remove the sizing-comment void sentence from the pointing-record intro

File: `refinement-record.md`

Matched text:

```text
A sizing comment that names a point value before the reveal, names or implies a target value for this story, or states elapsed time, effort or run cost voids the round under the Anchoring guardrail recovery as soon as the facilitator sees it, as does any ground that is neither restated nor retracted, and the void records the consensus as void and is recorded under Anchoring events.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`.

## 24. Remove the challenge line from the pointing-record template

File: `refinement-record.md`

Matched text:

```text
- Challenges: <none, or each ground challenged by kind, its author (a voter, or the SM/EM for a sizing comment), the restatement, withdrawal or retraction, or the void; elide a pre-reveal value or a target value while the round is open>
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`.

## 25. Remove the superseded-values line from the pointing-record template

File: `refinement-record.md`

Matched text:

```text
- Superseded values after a void: <none, or the voided values and the blind vote that replaced them>
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`.

## 26. Remove the reveal condition from the phrasing principle sentence

File: `refinement-record.md`

Matched text:

```text
, and it names a point value only after all three values are recorded
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_intro_is_unchanged_and_adds_the_comparison_principle`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_intro_is_unchanged_and_adds_the_comparison_principle`.

## 27. Put a target-value permitted cell in a row the curated list pins

File: `refinement-record.md`

Matched text:

```text
"The prior story also changed the schema."
```

Replaced with:

```text
"This story is a 5."
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_state_no_target_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_state_no_target_value`.

## 28. Put a preferred-direction permitted cell in a row the curated list pins

File: `refinement-record.md`

Matched text:

```text
"The prior story also changed the schema."
```

Replaced with:

```text
"We should go higher than that."
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_state_no_target_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_state_no_target_value`.

## 29. Delete one permitted row, leaving ten

File: `refinement-record.md`

Matched text:

```text
| "The prior story also changed the schema." | "I think it is 5." |
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_column_is_the_exact_curated_list`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_column_is_the_exact_curated_list`.

## 30. Insert a non-row line between two table rows

File: `refinement-record.md`

Matched text:

```text
| "The named story had one fewer external dependency." | "This would take a week." |
```

Replaced with:

```text
This story is a 5.
| "The named story had one fewer external dependency." | "This would take a week." |
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_section_holds_only_the_intro_the_table_and_the_trailer`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_section_holds_only_the_intro_the_table_and_the_trailer`.

## 31. Remove the reveal definition from Step 3 item 5

File: `SKILL.md`

Matched text:

```text
The reveal is the moment the facilitator has recorded all three values, after which the SM/EM may comment on sizing and the discussion opens.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_defines_the_reveal`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_defines_the_reveal - a...`.

## 32. Remove the rationale rule from the re-vote prompt sentence

File: `SKILL.md`

Matched text:

```text
     It also carries the Step 3 item 4 rationale rule.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_re_vote_prompt_carries_the_rationale_rule`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_re_vote_prompt_carries_the_rationale_rule`.

## 33. Make a voided consensus look like an untouched field

File: `refinement-record.md`

Matched text:

```text
- Consensus: <highest value in the intersection, or void when the round was voided>
```

Replaced with:

```text
- Consensus: <highest value in the intersection, or none>
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_marks_a_voided_consensus`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_marks_a_voided_consensus`.

## 34. Control: add a blank line after the table

File: `refinement-record.md`

Matched text:

```text
Record every SM/EM sizing comment with the pointing record, even when it stays inside the permitted column.
```

Replaced with:

```text

Record every SM/EM sizing comment with the pointing record, even when it stays inside the permitted column.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_section_holds_only_the_intro_the_table_and_the_trailer`
Result: PASSED (control).

Pins this file does not mutate, because they guard structure rather than one sentence: the phrasing table header labels, the Challenges-before-Anchoring-events ordering, the Step 4 item count and order, and the clause that another voter's revealed value is never the answer.

The facilitator's challenge duty has no automated guard over a live round: a phrase test can pin the duty's text, and the mutations above prove that pin, but only a run can show a facilitator applying it, which is what the tabletop pointing round on the canceled fixture records.
