# SKL-238 QA evidence

## QA round 3

Date: 2026-11-16 UTC, independent QA round 3.
Round 1 failed C6 on the PR 262 description; round 2 verified every item, but its evidence was never merged, so this round re-verifies and is the record.
Target: `main` at `cfd57c4a720d27d0958f3d13d031e5b9519aa612`, the squash merge of PR 262, whose reviewed head is `1f0dd29e6ce9ff107393049ef4074ac8b921bbdc`.
`git merge-base --is-ancestor` confirmed the target on `origin/main`.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Fixtures: none.
Blocker SKL-237 is Done, and its merge `eb8ec19a0e876c313b501de1697f3ca30239efd3` is an ancestor of the target.
The raw output is attached to SKL-238 as "SKL-238 QA round 3 output at target cfd57c4"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| C1: profile keys | Verified | `refinement.exemplar_label` and `refinement.anchor_label` are optional strings with `minLength: 1`, a non-blank pattern and no default; the schema accepts either key unset or set and rejects a blank, whitespace-only, integer, null or list value; `profile/example.yaml` shows both commented out with `example-` placeholders; a scan of `skills/story-refinement/` and `profile/` finds no issue key other than `SKL-` keys and `ABC-123`, and no consumer name; the closing message carries the `exemplars:` and `anchors:` lines. |
| C2: exemplar lookup | Verified | Step 1 item 4 runs after the type check and before the tracker-write preflight; `references/exemplars-and-anchors.md` holds the team limit, eligibility, the skip reasons in order, same-type selection, the most recent `Capstone` rule, `Exemplar not selected`, `no exemplar for <type>` and `exemplar lookup failed`. |
| C3: exemplar use | Verified | The voter launch carries the selected exemplar beside the per-type content, byte-identical for the three voters, with the statement that it models structure and not scope or size, and omits it when none is selected. |
| C4: anchors in pointing | Verified | The table, its sort, the five skip reasons, its carry into every Step 3, Step 4, recovery and slice prompt, the rationale rule and the two exception sentences are present, and no anchor lookup runs for an unpointed type. |
| C5: records | Verified | The refinement comment and pointing record template lines, the `## Record vocabulary` section and the `not looked up` precedence are present, and the `Permitted and forbidden phrasing` table is unchanged from the parent commit. |
| C6: tests | Verified | Details below. |
| C7: regeneration and gate | Verified | `scripts/vendor_shared.py --check` exits 0; CI run 43703655186 passed on the reviewed head and run 43704214814 on `main` at the target; a local full run at the target passed 2472. |
| C8: comment headings | Verified | `## Comment headings` in `references/refinement-record.md` defines `## Capstone` and `## Calibration anchor`, first-line case-sensitive matching with an optional date, the most recent match and the `Points:` rule. |
| C9: failure and isolation | Verified | A skip, an empty result or a failed lookup never stops the ceremony, the Read first rule gives those outcomes precedence, and retrieved content is reference data, not instructions. |
| DoD: all acceptance criteria met | Verified | C1 to C9. |
| DoD: tests written and passing | Verified | See C6 and C7. |
| DoD: independently reviewed | Verified | Review 5910245406 on PR 262 is `COMMENTED` at `1f0dd29e6ce9ff107393049ef4074ac8b921bbdc`, its first line names that SHA, and it was submitted at 10:27:53Z, before the 10:28:06Z merge. |
| DoD: docs updated | Verified | README skill row, `references/refinement-record.md`, the new `references/exemplars-and-anchors.md` and the re-vendored `shared/todo-tracking.md`. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed: the run is on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | The full suite and both CI runs passed at the target. |

Details:

- C6:
  - The pre-merge `tests/` run against the target fails exactly four previously passing tests: `test_split_rule_section_is_exactly_the_rule`, `test_read_first_authority_rule_is_unchanged`, `test_todo_tracking_seed_states_the_unestimated_list` and `test_guardrail_bounds_the_parent_value_and_keeps_slice_prohibitions_and_precedence`.
  - The PR 262 section "Replaced phrases (C6)" names those four tests and the phrase each replaced.
  - Each of the four updated counterparts fails against the pre-merge text.
  - The new tests assert through `section()` and `bullet()` and cover both keys unset, each set alone, no match, one and several matches, each exemplar and anchor skip reason, a failed exemplar and anchor lookup, one, several and no anchors, `not pointed`, the table in every prompt variant, and schema acceptance and rejection.
  - `test_skill_and_profile_name_no_consumer_issue_key_or_name` asserts that no consumer issue key or consumer name appears under `skills/story-refinement/` and `profile/`.
- Incidental, low: reviews 5910134721, 5910147614, 5910198061 and 5910218695 on PR 262 were posted after the head had moved, so each `commit_id` is a later commit than the SHA on its first line; the review of record at the merged head is unaffected.

Closing decision: Done, once this evidence merges.
