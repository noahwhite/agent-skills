# SKL-59 mutation evidence

Measured on the delivered text of this change with CPython 3.12.3 and locked dependencies, with every command run from the repository root.
The modified files are `skills/story-refinement/SKILL.md` and `skills/story-refinement/references/refinement-record.md`.
Before each check the document bytes were saved, the edit named below was made, the quoted command ran, and the saved bytes were restored even when the command failed; the final source matched the saved bytes and the tracked changes were then only the files this change delivers.
Each entry quotes its literal exactly as it appears in the file, and each one removes, replaces or inserts that literal once, so a re-runner can reproduce it from the delivered text.
23 regression proofs failed as designed and 1 control passed.
Entries 1 to 23 are the regression proofs; entry 24 is the control.

## 1. Remove the rationale ban and driver-set sentence from Step 3 item 4

File: `SKILL.md`

```text
The rationale cites no duration, effort or run-cost measure, and it names complexity drivers only, each a property of the change: design difficulty, an interacting constraint, an unknown, or the risk of breaking existing behaviour.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`.

## 2. Remove the out-of-basis and inherited-value sentence from Step 3 item 4

File: `SKILL.md`

```text
Verification strength, testability, coverage and the shape of the tests are also out of basis, and so is weighing a point value already recorded for this story, a prior story, a parent or sibling, or an inherited split.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`.

## 3. Remove the verification-versus-breakage sentence from Step 3 item 4

File: `SKILL.md`

```text
Verification strength is how well a behaviour is checked and breakage risk is what can silently change, so the first is out of basis and the second is a basis driver.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`.

## 4. Remove the point-value ban sentence from Step 3 item 7

File: `SKILL.md`

```text
It must not name, bound or imply any point value - a prior story's, an inherited split value, a value read from this story's own recorded pointing history, or one implied by a split status - and such a statement is an anchoring event under the Anchoring guardrail unless the SM/EM withdraws it when the facilitator challenges it.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_sizing_context_is_in_complexity_terms`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_sizing_context_is_in_complexity_terms`.

## 5. Remove the challenge duty from Step 4 item 1

File: `SKILL.md`

```text
In that round, and against every rationale recorded in this ceremony - the Step 3 rationales and any re-vote rationale - the facilitator challenges every ground outside the pointing basis, whether it is heard in the discussion or read in a recorded rationale.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 6. Remove the restatement-or-withdrawal rule from Step 4 item 1

File: `SKILL.md`

```text
A challenged ground must be restated as a basis driver, withdrawn or retracted by its author, the SM/EM for its own sizing comment; a ground that is neither is an anchoring event under the Anchoring guardrail.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 7. Add a tenth Process item to Step 4

File: `SKILL.md`

```text
     The facilitator records the decision; it does not choose it.\n
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_process_items_keep_their_count_and_order`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_process_items_keep_their_count_and_order`.

## 8. Swap Step 4 Process items 3 and 4

File: `SKILL.md`

```text
  3. Consensus is the highest value in the intersection of the three accepted sets.\n     If the intersection is empty, record no consensus and run the no-consensus decision (item 7).\n  4. Never average and never take a value silently.\n
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_process_items_keep_their_count_and_order`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_process_items_keep_their_count_and_order`.

## 9. Remove the point-value prohibited behaviour from the Anchoring guardrail

File: `SKILL.md`

```text
- naming, bounding or implying a point value, including a prior story's, an inherited split value, a value recorded on the story surface, or one implied by a split status;\n
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_bans_naming_bounding_or_implying_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_bans_naming_bounding_or_implying_a_point_value`.

## 10. Remove the off-basis trigger paragraph from the Anchoring guardrail

File: `SKILL.md`

```text
A ground outside the pointing basis is an anchoring trigger on the same terms: a rationale or a sizing comment that weighs verification strength, testability, coverage, the shape of the tests, or a prior or inherited point value is challenged under Step 4, and the SM/EM's own sizing comment is withdrawn or restated by the SM/EM when the facilitator challenges it.\n
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_names_off_basis_grounds_as_a_trigger`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_names_off_basis_grounds_as_a_trigger`.

## 11. Remove the void-and-re-run clause from the Anchoring guardrail

File: `SKILL.md`

```text
A challenged ground that is neither restated as a basis driver nor withdrawn or retracted is an anchoring event, and the void re-runs the independent vote from Step 3 in newly created voter contexts.\n\n
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_gives_the_sm_em_a_way_to_withdraw_its_own_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_gives_the_sm_em_a_way_to_withdraw_its_own_ground`.

## 12. Remove the fresh-context limitation paragraph from the Anchoring guardrail

File: `SKILL.md`

```text
Fresh voter contexts exclude the tainted discussion and the sizing comment, but they cannot exclude a point value recorded on the story surface that Step 1 hands every voter with the story, so the Step 3 rationale rule is what keeps such a value out of the vote.\n\n
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_explains_why_context_cannot_exclude_a_recorded_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_explains_why_context_cannot_exclude_a_recorded_value`.

## 13. Drop the vote-voiding phrase from the anchoring recovery sentence

File: `SKILL.md`

```text
void the consensus and any vote recorded after the anchor, and re-run the independent vote
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_recovery_mechanics_are_unchanged`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_recovery_mechanics_are_unchanged`.

## 14. Remove the challenge sentence from the pointing-record intro

File: `refinement-record.md`

```text
A challenged ground is recorded with its author (a voter, or the SM/EM for a sizing comment) and either the restatement, the withdrawal or the retraction; a ground that is neither voids the round and is recorded as the void.\n
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`.

## 15. Remove the challenge line from the pointing-record template

File: `refinement-record.md`

```text
- Challenges: <each ground challenged, its author (a voter, or the SM/EM for a sizing comment), and the restatement, withdrawal or retraction, or the void>\n
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`.

## 16. Drop the point-value ban from the phrasing principle sentence

File: `refinement-record.md`

```text
it never names a point value, a range,
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_intro_is_unchanged_and_adds_the_comparison_principle`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_intro_is_unchanged_and_adds_the_comparison_principle`.

## 17. Reintroduce the point-value permitted cell

File: `refinement-record.md`

```text
| "The comparable story had one fewer unknown to resolve." |
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`.

## 18. Reintroduce the split-status permitted cell

File: `refinement-record.md`

```text
| "The earlier story carried more breaking-behaviour risk." |
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`.

## 19. Put a digit-valued permitted cell back in the table

File: `refinement-record.md`

```text
| "The earlier story carried more breaking-behaviour risk." |
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`.

## 20. Put a spelled-out value in a permitted cell

File: `refinement-record.md`

```text
| "The earlier story carried more breaking-behaviour risk." |
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`.

## 21. Put a scale position in a permitted cell

File: `refinement-record.md`

```text
| "The earlier story carried more breaking-behaviour risk." |
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`.

## 22. Delete the whole phrasing-table body

File: `refinement-record.md`

```text
| "The comparable story had one fewer unknown to resolve." | "I would go higher." |\n| "The named story had three interacting constraints; this one has four." | "I would go lower." |\n| "This story has one more integration than that one." | "A target of 8 fits." |\n| "The prior story also changed the schema." | "I think it is 5." |\n| "That story carried no migration." | "The highest vote is the realistic one." |\n| "The scope differs in the deploy leg." | "The lowest vote is the realistic one." |\n| "This story has one more unknown than that one." | "Let us re-vote after I explain." |\n| "The comparable story had the same interacting constraints." | "The two of you are far apart." |\n| "The earlier story carried more breaking-behaviour risk." | Comparing individual votes before the discussion. |\n
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`.

## 23. Insert a non-row line carrying a point value inside the phrasing table

File: `refinement-record.md`

```text
| "The named story had one fewer external dependency." | "This would take a week." |
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`.

## 24. Control: add a blank line after the table

File: `refinement-record.md`

```text
Record every SM/EM sizing comment with the pointing record, even when it stays inside the permitted column.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
Result: PASSED (control).

The facilitator's challenge duty has no automated guard over a live round: a phrase test can pin the duty's text, and the mutations above prove that pin, but only a run can show a facilitator applying it, which is what the tabletop pointing round on the canceled fixture records.
