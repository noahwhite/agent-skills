# SKL-59 mutation evidence

Measured on the delivered text of this change with CPython 3.12.3 and locked dependencies, with every command run from the repository root.
The modified files are `skills/story-refinement/SKILL.md` and `skills/story-refinement/references/refinement-record.md`.
Before each check the document bytes were saved, only the named edit was made, the quoted command ran, and the saved bytes were restored even when the command failed; the final source matched the saved bytes and `git status` was clean.
Each deletion removes the exact named sentence once.

1. Delete the basis-only driver sentence from `SKILL.md` Step 3 item 4
   Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
   Exit: 1; FAILED `tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`

2. Delete the off-basis and inherited-value sentence from `SKILL.md` Step 3 item 4
   Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
   Exit: 1; FAILED `tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`

3. Delete the verification-versus-breakage sentence from `SKILL.md` Step 3 item 4
   Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_rationale_names_complexity_drivers_and_no_duration`
   Exit: 1; FAILED `tests/test_story_refinement.py::test_step_three_rationale_names_complexity_drivers_and_no_duration`

4. Delete the point-value ban sentence from `SKILL.md` Step 3 item 7
   Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_three_sizing_context_forbids_any_point_value`
   Exit: 1; FAILED `tests/test_story_refinement.py::test_step_three_sizing_context_forbids_any_point_value`

5. Delete the challenge duty from `SKILL.md` Step 4 item 1
   Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
   Exit: 1; FAILED `tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`

6. Delete the restatement-or-retraction rule from `SKILL.md` Step 4 item 1
   Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
   Exit: 1; FAILED `tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`

7. Insert a tenth Process item into `SKILL.md` Step 4
   Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_step_four_facilitator_challenges_every_off_basis_ground`
   Exit: 1; FAILED `tests/test_story_refinement.py::test_step_four_facilitator_challenges_every_off_basis_ground`

8. Delete the point-value prohibited behaviour from `SKILL.md` Anchoring guardrail
   Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_bans_naming_bounding_or_implying_a_point_value`
   Exit: 1; FAILED `tests/test_story_refinement.py::test_anchoring_guardrail_bans_naming_bounding_or_implying_a_point_value`

9. Delete the off-basis trigger paragraph from `SKILL.md` Anchoring guardrail
   Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_names_off_basis_grounds_as_a_trigger`
   Exit: 1; FAILED `tests/test_story_refinement.py::test_anchoring_guardrail_names_off_basis_grounds_as_a_trigger`

10. Delete the fresh-context limitation paragraph from `SKILL.md` Anchoring guardrail
    Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_explains_why_context_cannot_exclude_a_recorded_value`
    Exit: 1; FAILED `tests/test_story_refinement.py::test_anchoring_guardrail_explains_why_context_cannot_exclude_a_recorded_value`

11. Reword the anchoring recovery sentence in `SKILL.md`, dropping "and any vote recorded after the anchor"
    Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_anchoring_guardrail_recovery_mechanics_are_unchanged`
    Exit: 1; FAILED `tests/test_story_refinement.py::test_anchoring_guardrail_recovery_mechanics_are_unchanged`

12. Reintroduce the permitted cell `"The comparable story was 5 points."` in `refinement-record.md`
    Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
    Exit: 1; FAILED `tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`

13. Reintroduce the permitted cell `"The earlier story was split once."` in `refinement-record.md`
    Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
    Exit: 1; FAILED `tests/test_story_refinement.py::test_phrasing_table_permitted_cells_never_name_a_point_value`

14. Delete "a point value, " from the phrasing principle sentence in `refinement-record.md`
    Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_intro_is_unchanged_and_adds_the_comparison_principle`
    Exit: 1; FAILED `tests/test_story_refinement.py::test_phrasing_intro_is_unchanged_and_adds_the_comparison_principle`

15. Delete the challenge line from the pointing-record template in `refinement-record.md`
    Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
    Exit: 1; FAILED `tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`

16. Delete the challenge sentence from the pointing-record intro in `refinement-record.md`
    Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_pointing_template_records_each_challenge_and_outcome`
    Exit: 1; FAILED `tests/test_story_refinement.py::test_pointing_template_records_each_challenge_and_outcome`

17. Control: add a blank line after the phrasing table in `refinement-record.md`
    Command: `uv run --locked pytest -q tests/test_story_refinement.py -k test_phrasing_table_permitted_cells_never_name_a_point_value`
    Exit: 0; the control passes, so the pins fail on the guarded content and not on any edit.

The facilitator's challenge duty itself has no automated guard over a live round: a phrase test can pin the duty's text, but only a run can show a facilitator applying it, which is what the tabletop pointing round on the canceled fixture records.
