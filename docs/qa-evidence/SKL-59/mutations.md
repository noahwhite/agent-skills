# SKL-59 mutation evidence

Measured on the delivered text of this change with CPython 3.12.3 and locked dependencies, with every command run from the repository root.
The modified files are `skills/story-refinement/SKILL.md` and `skills/story-refinement/references/refinement-record.md`.
Before each check the document bytes were saved, the edit shown below was made once, the quoted command ran, and the saved bytes were restored even when the command failed; the final source matched the saved bytes, and the tracked changes were then only the files this change delivers.
Each entry shows the exact matched text, and the exact replacement text where the edit substitutes or inserts one, so a re-runner can reproduce it from the delivered text.
35 regression proofs failed as designed and 1 control passed.
Entries 1 to 35 are the regression proofs; entry 36 is the control.

## 1. Remove the measure ban and driver-set sentence from Step 3 item 4

File: `SKILL.md`

Matched text:

```text
The rationale cites no duration, effort or run-cost measure, and it names complexity drivers only, each a property of the change: design difficulty, an interacting constraint, an unknown, or the risk of breaking existing behaviour.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`.

## 2. Remove the out-of-basis and inherited-value sentence from Step 3 item 4

File: `SKILL.md`

Matched text:

```text
Verification strength, testability, coverage and the shape of the tests are also out of basis, and so is weighing a point value already recorded for this story, a prior story, a parent or sibling, or an inherited split.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`.

## 3. Remove the verification-versus-breakage sentence from Step 3 item 4

File: `SKILL.md`

Matched text:

```text
Verification strength is how well a behaviour is checked and breakage risk is what can silently change, so the first is out of basis and the second is a basis driver.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`.

## 4. Remove the point-value ban from Step 3 item 7

File: `SKILL.md`

Matched text:

```text
It must not name, bound or imply any point value - a prior story's, an inherited split value, a value read from this story's own recorded pointing history, or one implied by a split status - and such a statement is an anchoring event under the Anchoring guardrail.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_sizing_context_is_in_complexity_terms`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_sizing_context_is_in_complexity_terms`.

## 5. Remove the challenge duty from Step 4 item 1

File: `SKILL.md`

Matched text:

```text
In that round, and against the rationales recorded in Step 3, the facilitator challenges every ground outside the pointing basis, whether it is heard in the discussion or read in a recorded rationale.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 6. Remove the no-value-comparison clarification from Step 4 item 1

File: `SKILL.md`

Matched text:

```text
Challenging a ground is not comparing values or singling out a voter: the facilitator names the ground and its author, and never the author's value.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 7. Remove the restate-or-retract rule from Step 4 item 1

File: `SKILL.md`

Matched text:

```text
A challenged ground must be restated as a basis driver, which may move the voter's value to the one its basis supports, or retracted; the SM/EM withdraws or restates its own sizing comment on the same terms, except a statement that names, bounds or implies a point value, or states elapsed time, effort or run cost, which is an anchoring event as soon as the facilitator sees it.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 8. Remove the neither-outcome rule from Step 4 item 1

File: `SKILL.md`

Matched text:

```text
A ground that is neither is an anchoring event under the Anchoring guardrail.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 9. Add a tenth Process item after the no-consensus decision item

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

## 10. Swap Step 4 Process items 3 and 4

File: `SKILL.md`

Matched text:

```text
  3. Consensus is the highest value in the intersection of the three accepted sets.
     If the intersection is empty, record no consensus and run the no-consensus decision (item 7).
  4. Never average and never take a value silently.
```

Replaced with:

```text
  3. Never average and never take a value silently.
  4. Consensus is the highest value in the intersection of the three accepted sets.
     If the intersection is empty, record no consensus and run the no-consensus decision (item 7).
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_process_items_keep_their_count_and_order`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_process_items_keep_their_count_and_order`.

## 11. Remove the re-vote challenge sentence from Step 4 item 2

File: `SKILL.md`

Matched text:

```text
     A re-vote rationale outside the pointing basis is challenged before the consensus is recorded, under the same restate-or-retract rule as item 1.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_re_vote_challenges_an_off_basis_rationale`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_re_vote_challenges_an_off_basis_rationale`.

## 12. Remove the point-value prohibited behaviour from the Anchoring guardrail

File: `SKILL.md`

Matched text:

```text
- for the SM/EM, naming, bounding or implying a point value in sizing context or in the discussion, including a prior story's, an inherited split value, a value recorded on the story surface, or one implied by a split status;
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_bans_naming_bounding_or_implying_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_bans_naming_bounding_or_implying_a_point_value`.

## 13. Remove the point-value-on-challenge clause from the Anchoring guardrail trigger

File: `SKILL.md`

Matched text:

```text
Every prohibited behaviour above, and a sizing comment that names, bounds or implies a point value or that states elapsed time, effort or run cost, is an anchoring event as soon as it is seen, with no challenge, restatement or retraction path.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_makes_a_point_value_sizing_note_an_event_on_challenge`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_makes_a_point_value_sizing_note_an_event_on_challenge`.

## 14. Remove the void-and-re-run paragraph from the Anchoring guardrail

File: `SKILL.md`

Matched text:

```text
Any other challenged ground that is neither restated as a basis driver nor retracted, or a sizing comment the SM/EM neither withdraws nor restates, is an anchoring event; a ground that taints votes recorded before it voids those votes too, and the independent vote from Step 3 is re-run in newly created voter contexts that exclude the tainted discussion and sizing comment.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_makes_a_point_value_sizing_note_an_event_on_challenge`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_makes_a_point_value_sizing_note_an_event_on_challenge`.

## 15. Remove the off-basis trigger clause from the Anchoring guardrail

File: `SKILL.md`

Matched text:

```text
An anchoring trigger is an off-basis ground Step 4 challenges, so it becomes an anchoring event only when it is neither restated as a basis driver nor retracted:
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_names_off_basis_grounds_as_a_trigger`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_names_off_basis_grounds_as_a_trigger`.

## 16. Remove the challenge requirement from the Records enumeration

File: `SKILL.md`

Matched text:

```text
every challenge with its outcome,
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_records_requires_every_challenge_with_its_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_records_requires_every_challenge_with_its_outcome`.

## 17. Remove the accepted-set clarification from Step 4 item 2

File: `SKILL.md`

Matched text:

```text
     Recording an accepted set is not weighing a recorded value: the rationale for the set is about complexity, never about which value was recorded earlier.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_re_vote_challenges_an_off_basis_rationale`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_re_vote_challenges_an_off_basis_rationale`.

## 18. Remove the fresh-context limitation paragraph from the Anchoring guardrail

File: `SKILL.md`

Matched text:

```text
Fresh voter contexts exclude the tainted discussion and the sizing comment, but they cannot exclude a point value recorded on the story surface that Step 1 hands every voter with the story, so the Step 3 rationale rule is what keeps such a value out of the vote.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_explains_why_context_cannot_exclude_a_recorded_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_explains_why_context_cannot_exclude_a_recorded_value`.

## 19. Drop the vote-voiding phrase from the anchoring recovery sentence

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

## 20. Remove the challenge sentence from the pointing-record intro

File: `refinement-record.md`

Matched text:

```text
A challenged ground is recorded with its author (a voter, or the SM/EM for a sizing comment) and either the restatement, the withdrawal or the retraction; a sizing comment that names, bounds or implies a point value voids the round under the Anchoring guardrail recovery as soon as the facilitator sees it, as does any ground that is neither restated nor retracted, and the void leaves the consensus field empty and is recorded under Anchoring events.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`.

## 21. Remove the challenge line from the pointing-record template

File: `refinement-record.md`

Matched text:

```text
- Challenges: <none, or each ground challenged, its author (a voter, or the SM/EM for a sizing comment), and the restatement, withdrawal or retraction, or the void>
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`.

## 22. Drop the point-value ban from the phrasing principle sentence

File: `refinement-record.md`

Matched text:

```text
it never names a point value, a range,
```

Replaced with:

```text
it never names a range,
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_intro_is_unchanged_and_adds_the_comparison_principle`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_intro_is_unchanged_and_adds_the_comparison_principle`.

## 23. Put a point-value permitted cell back in a row that no other assertion pins

File: `refinement-record.md`

Matched text:

```text
"The prior story also changed the schema."
```

Replaced with:

```text
"The comparable story was 5 points."
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`.

## 24. Put a split-status permitted cell in an unpinned row

File: `refinement-record.md`

Matched text:

```text
"The prior story also changed the schema."
```

Replaced with:

```text
"The earlier story was split once."
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`.

## 25. Put a digit-valued permitted cell in an unpinned row

File: `refinement-record.md`

Matched text:

```text
"The prior story also changed the schema."
```

Replaced with:

```text
"The earlier story was a 3."
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`.

## 26. Put a spelled-out value in a permitted cell

File: `refinement-record.md`

Matched text:

```text
"The prior story also changed the schema."
```

Replaced with:

```text
"The earlier story was five."
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`.

## 27. Put a bare t-shirt size letter in a permitted cell

File: `refinement-record.md`

Matched text:

```text
"The prior story also changed the schema."
```

Replaced with:

```text
"The earlier story was an M."
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`.

## 28. Put a spelled-out value in a count frame

File: `refinement-record.md`

Matched text:

```text
"The prior story also changed the schema."
```

Replaced with:

```text
"The earlier story came in at five."
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`.

## 29. Put a t-shirt scale position in a permitted cell

File: `refinement-record.md`

Matched text:

```text
"The prior story also changed the schema."
```

Replaced with:

```text
"The earlier story sat at Medium."
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_column_is_the_exact_curated_list`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_column_is_the_exact_curated_list`.

## 30. Put a value bounded by the cap in a permitted cell

File: `refinement-record.md`

Matched text:

```text
"The prior story also changed the schema."
```

Replaced with:

```text
"The earlier story sits under the cap."
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`.

## 31. Remove the superseded-values line from the pointing-record template

File: `refinement-record.md`

Matched text:

```text
- Superseded values after a void: <none, or the voided values and the blind vote that replaced them>
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`.

## 32. Add a permitted cell that implies a value without any banned token

File: `refinement-record.md`

Matched text:

```text
"The prior story also changed the schema."
```

Replaced with:

```text
"The earlier story drew a four on unknowns."
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_column_is_the_exact_curated_list`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_column_is_the_exact_curated_list`.

## 33. Delete one unpinned permitted row, leaving ten

File: `refinement-record.md`

Matched text:

```text
| "The prior story also changed the schema." | "I think it is 5." |
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_column_is_the_exact_curated_list`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_column_is_the_exact_curated_list`.

## 34. Insert a non-row line carrying a point value between two table rows

File: `refinement-record.md`

Matched text:

```text
| "The named story had one fewer external dependency." | "This would take a week." |
```

Replaced with:

```text
The comparable story was 5 points.
| "The named story had one fewer external dependency." | "This would take a week." |
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_section_holds_only_the_intro_the_table_and_the_trailer`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_section_holds_only_the_intro_the_table_and_the_trailer`.

## 35. Insert a point-value sentence between the intro and the table

File: `refinement-record.md`

Matched text:

```text

| Permitted (factual, reference-only) | Forbidden (leading or anchoring) |
```

Replaced with:

```text

The comparable story was a 3, so stay near it.

| Permitted (factual, reference-only) | Forbidden (leading or anchoring) |
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_section_holds_only_the_intro_the_table_and_the_trailer`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_section_holds_only_the_intro_the_table_and_the_trailer`.

## 36. Control: add a blank line after the table

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

The facilitator's challenge duty has no automated guard over a live round: a phrase test can pin the duty's text, and the mutations above prove that pin, but only a run can show a facilitator applying it, which is what the tabletop pointing round on the canceled fixture records.
