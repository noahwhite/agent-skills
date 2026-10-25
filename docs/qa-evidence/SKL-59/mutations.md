# SKL-59 mutation evidence

Measured on the delivered text of this change with CPython 3.12.3 and locked dependencies, with every command run from the repository root.
The modified files are `skills/story-refinement/SKILL.md`, `skills/story-refinement/references/refinement-record.md`, `tests/test_story_refinement.py` (the pins) and this evidence file.
Before each check the document bytes were saved, exactly one edit was made, the quoted command ran, and the saved bytes were restored even when the command failed; the final source matched the saved bytes and the tree was clean afterwards.
A deletion removes the one line that carries the phrase; the line is quoted below exactly as it appears in the file.
34 regression proofs failed as designed and 1 control passed.
Entries 1 to 34 are the regression proofs; entry 35 is the control.

## 1. Delete the basis-by-reference rule from Step 3 item 4

File: `SKILL.md`

Removed or matched text:

```text
     The rationale names drivers the pointing basis admits and nothing else, so verification strength, testability, coverage, the shape of the tests, a duration, effort or run-cost measure are out of basis.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`.

## 2. Delete the verification-versus-breakage sentence from Step 3 item 4

File: `SKILL.md`

Removed or matched text:

```text
     Verification strength is how well a behaviour is checked and the risk of breaking existing behaviour is what can silently change, so the first is out of basis while the second is a driver the basis admits, distinct from an interacting constraint the change carries.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`.

## 3. Delete the three narrowed value rules from Step 3 item 4

File: `SKILL.md`

Removed or matched text:

```text
     The rationale names no target value for this story, never treats another voter's revealed value as its answer, and names no point value before the reveal.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`.

## 4. Restate the pointing basis inside Step 3 item 4

File: `SKILL.md`

Removed or matched text:

```text
     The value is written only to that voter's own file in the session's scratch directory.
```

Written instead:

```text
     A point measures design difficulty and interaction, never work or time.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_does_not_restate_the_pointing_basis`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_does_not_restate_the_pointing_basis`.

## 5. Delete the pre-reveal value ban from Step 3 item 7

File: `SKILL.md`

Removed or matched text:

```text
     Before the reveal it must not name any point value.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_sizing_context_is_in_complexity_terms`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_sizing_context_is_in_complexity_terms`.

## 6. Delete the post-reveal permission and target-value ban from Step 3 item 7

File: `SKILL.md`

Removed or matched text:

```text
     After the reveal it may compare this story with an already-estimated item and name that item's recorded value, but it must not name or imply a target value for this story, including one implied by a split status, and such a statement is an anchoring event under the Anchoring guardrail.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_sizing_context_is_in_complexity_terms`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_sizing_context_is_in_complexity_terms`.

## 7. Drop the rationale rule from the pointing-prompt requirement

File: `SKILL.md`

Removed or matched text:

```text
, and carries the item 4 rationale rule
```

Written instead:

```text

```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_requires_the_basis_in_every_pointing_prompt`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_three_requires_the_basis_in_every_pointing_prompt`.

## 8. Delete the challenge duty from Step 4 item 1

File: `SKILL.md`

Removed or matched text:

```text
     In that round, and against the rationales recorded in Step 3, the facilitator challenges every ground outside the pointing basis, whether it is heard in the discussion or read in a recorded rationale.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 9. Delete the kind-and-author rule from Step 4 item 1

File: `SKILL.md`

Removed or matched text:

```text
     Challenging a ground is not comparing values or singling out a voter: the facilitator names the ground's kind and its author, never the ground's verbatim text, and a ground that embeds a point value is named by its kind alone.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 10. Delete the restate-or-retract rule for voters from Step 4 item 1

File: `SKILL.md`

Removed or matched text:

```text
     A challenged ground must be restated as a basis driver or retracted, and a voter whose basis does not support its recorded value records that in the re-vote.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 11. Delete the SM/EM withdraw-or-restate rule and its no-repair exceptions

File: `SKILL.md`

Removed or matched text:

```text
     The SM/EM withdraws or restates its own sizing comment on the same terms, except a point value named before the reveal, a target value named or implied for this story, including one implied by a split status, treating another voter's revealed value as the answer, or a statement of elapsed time, effort or run cost, each of which is an anchoring event as soon as the facilitator sees it.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 12. Delete the neither-outcome rule from Step 4 item 1

File: `SKILL.md`

Removed or matched text:

```text
     A ground that is neither is an anchoring event under the Anchoring guardrail.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`.

## 13. Delete the accepted-set clarification from Step 4 item 2

File: `SKILL.md`

Removed or matched text:

```text
     Recording an accepted set is not treating another voter's revealed value as the answer: the rationale for the set is about the basis, never about which value another voter recorded.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_re_vote_challenges_an_off_basis_rationale`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_re_vote_challenges_an_off_basis_rationale`.

## 14. Delete the retracted-re-vote rule from Step 4 item 2

File: `SKILL.md`

Removed or matched text:

```text
     A re-vote rationale outside the pointing basis is challenged before the consensus is recorded, under the same restate-or-retract rule as item 1, and a voter that retracts its re-vote rationale records a new accepted set with a basis-driver rationale or records no consensus.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_re_vote_challenges_an_off_basis_rationale`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_step_four_re_vote_challenges_an_off_basis_rationale`.

## 15. Delete the SM/EM value prohibitions from the Anchoring guardrail

File: `SKILL.md`

Removed or matched text:

```text
- for the SM/EM, naming a point value before the reveal, naming or implying a target value for this story, including one implied by a split status, or treating another voter's revealed value as the answer;
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_bans_the_sm_em_value_behaviours`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_bans_the_sm_em_value_behaviours`.

## 16. Delete the anchoring-trigger definition from the Anchoring guardrail

File: `SKILL.md`

Removed or matched text:

```text
An anchoring trigger is an off-basis ground Step 4 challenges, so it becomes an anchoring event only when it is neither restated as a basis driver nor retracted: a ground that weighs verification strength, testability, coverage, the shape of the tests, a duration, effort or run cost, or a target value for this story is such a trigger when a voter weighs it in a rationale or raises it in the discussion.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_names_off_basis_grounds_as_a_trigger`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_names_off_basis_grounds_as_a_trigger`.

## 17. Delete the no-repair class from the Anchoring guardrail

File: `SKILL.md`

Removed or matched text:

```text
The SM/EM's prohibited behaviours above, and a sizing comment that names a point value before the reveal, names or implies a target value for this story, or states elapsed time, effort or run cost, are anchoring events as soon as they are seen, with no challenge, restatement or retraction path.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_makes_a_point_value_sizing_note_an_event_on_challenge`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_makes_a_point_value_sizing_note_an_event_on_challenge`.

## 18. Delete the void-and-re-run paragraph from the Anchoring guardrail

File: `SKILL.md`

Removed or matched text:

```text
Any other challenged ground that is neither restated as a basis driver nor retracted, or a sizing comment the SM/EM neither withdraws nor restates, is an anchoring event, and the recovery below is the single void rule: it voids the consensus and every vote recorded after the anchor, where a ground read in a recorded rationale anchors at the vote whose rationale carries it, and it re-runs the independent vote from Step 3 in newly created voter contexts that exclude the tainted discussion and sizing comment.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_makes_a_point_value_sizing_note_an_event_on_challenge`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_makes_a_point_value_sizing_note_an_event_on_challenge`.

## 19. Delete the fresh-context limitation paragraph from the Anchoring guardrail

File: `SKILL.md`

Removed or matched text:

```text
Fresh voter contexts exclude the tainted discussion and the sizing comment, but they cannot exclude a value recorded on the story surface that Step 1 hands every voter with the story, so the Step 3 rationale rule is what keeps such a value from becoming the rationale's answer.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_explains_why_context_cannot_exclude_a_recorded_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_explains_why_context_cannot_exclude_a_recorded_value`.

## 20. Drop the vote-voiding phrase from the anchoring recovery sentence

File: `SKILL.md`

Removed or matched text:

```text
void the consensus and any vote recorded after the anchor, and re-run the independent vote
```

Written instead:

```text
void the consensus and re-run the independent vote
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_recovery_mechanics_are_unchanged`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_anchoring_guardrail_recovery_mechanics_are_unchanged`.

## 21. Drop the challenge requirement from the Records enumeration

File: `SKILL.md`

Removed or matched text:

```text
every challenge with its outcome,
```

Written instead:

```text

```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_records_requires_every_challenge_with_its_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_records_requires_every_challenge_with_its_outcome`.

## 22. Delete the record redaction rule from the pointing-record intro

File: `refinement-record.md`

Removed or matched text:

```text
Outside the recorded numeric values and the superseded-values line, no line of the posted record carries a point value named before the reveal or a target value for this story: the Challenges and Anchoring events lines record a ground by its kind, its author (a voter, or the SM/EM for a sizing comment) and its outcome or recovery, and every field that could quote a participant elides those two classes permanently, because the posted record stays on the story surface that later voters read; the verbatim quote lives in the session's raw record, cited by its base name.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`.

## 23. Delete the sizing-comment void sentence from the pointing-record intro

File: `refinement-record.md`

Removed or matched text:

```text
A sizing comment that names a point value before the reveal, names or implies a target value for this story, or states elapsed time, effort or run cost voids the round under the Anchoring guardrail recovery as soon as the facilitator sees it, as does any ground that is neither restated nor retracted, and the void records the consensus as void and is recorded under Anchoring events.
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`.

## 24. Delete the challenge line from the pointing-record template

File: `refinement-record.md`

Removed or matched text:

```text
- Challenges: <none, or each ground challenged by kind, its author (a voter, or the SM/EM for a sizing comment), the restatement, withdrawal or retraction, or the void; elide a pre-reveal value or a target value>
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`.

## 25. Delete the superseded-values line from the pointing-record template

File: `refinement-record.md`

Removed or matched text:

```text
- Superseded values after a void: <none, or the voided values and the blind vote that replaced them>
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`.

## 26. Drop the session-record wording from the Anchoring events template line

File: `refinement-record.md`

Removed or matched text:

```text
, quoted verbatim in the session record and elided here
```

Written instead:

```text

```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`.

## 27. Make the consensus field carry a void marker

File: `refinement-record.md`

Removed or matched text:

```text
- Consensus: <highest value in the intersection of the vote that stands, or none when the intersection is empty>
```

Written instead:

```text
- Consensus: <highest value in the intersection, or void when the round was voided>
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_states_the_standing_consensus`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_states_the_standing_consensus`.

## 28. Drop the elision from a voter values line

File: `refinement-record.md`

Removed or matched text:

```text
  - Engineer one: <value> - <short complexity rationale, eliding a pre-reveal value or a target value>
```

Written instead:

```text
  - Engineer one: <value> - <short complexity rationale>
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_asks_for_complexity_rationales`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_pointing_template_asks_for_complexity_rationales`.

## 29. Drop the elision from the SM/EM sizing-context slot

File: `refinement-record.md`

Removed or matched text:

```text
 or verbatim, eliding a pre-reveal value or a target value
```

Written instead:

```text

```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_record_templates_cite_file_base_names`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_record_templates_cite_file_base_names[Pointing record-- SM/EM sizing context, after all three values: <file base name> or verbatim, eliding a pre-reveal value or a target value]`.

## 30. Drop the reveal condition from the phrasing principle sentence

File: `refinement-record.md`

Removed or matched text:

```text
, and it names a point value only after all three values are recorded
```

Written instead:

```text

```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_intro_is_unchanged_and_adds_the_comparison_principle`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_intro_is_unchanged_and_adds_the_comparison_principle`.

## 31. Put a target-value permitted cell in a row the curated list pins

File: `refinement-record.md`

Removed or matched text:

```text
"The prior story also changed the schema."
```

Written instead:

```text
"This story is a 5."
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_state_no_target_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_state_no_target_value`.

## 32. Put a preferred-direction permitted cell in a row the curated list pins

File: `refinement-record.md`

Removed or matched text:

```text
"The prior story also changed the schema."
```

Written instead:

```text
"We should go higher than that."
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_state_no_target_value`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_cells_state_no_target_value`.

## 33. Delete one permitted row

File: `refinement-record.md`

Removed or matched text:

```text
| "The prior story also changed the schema." | "I think it is 5." |
```

Written instead:

```text

```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_column_is_the_exact_curated_list`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_table_permitted_column_is_the_exact_curated_list`.

## 34. Insert a non-row line between two table rows

File: `refinement-record.md`

Removed or matched text:

```text
| "The named story had one fewer external dependency." | "This would take a week." |
```

Written instead:

```text
This story is a 5.
| "The named story had one fewer external dependency." | "This would take a week." |
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_section_holds_only_the_intro_the_table_and_the_trailer`
Result: FAILED (as designed); `FAILED tests/test_story_refinement.py::test_phrasing_section_holds_only_the_intro_the_table_and_the_trailer`.

## 35. Control: add a blank line after the table

File: `refinement-record.md`

Removed or matched text:

```text
Record every SM/EM sizing comment with the pointing record
```

Written instead:

```text

Record every SM/EM sizing comment with the pointing record
```

Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_section_holds_only_the_intro_the_table_and_the_trailer`
Result: PASSED (control).

Pins this file does not mutate, because they guard structure rather than one sentence: the phrasing table header labels, the Challenges-before-Anchoring-events ordering, the Step 4 item count and order, and the reveal definition's position in Step 3.

The facilitator's challenge duty has no automated guard over a live round: a phrase test can pin the duty's text, and the mutations above prove that pin, but only a run can show a facilitator applying it, which is what the tabletop pointing round on the canceled fixture records.
