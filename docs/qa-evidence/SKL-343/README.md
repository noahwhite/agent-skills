# SKL-343 QA evidence

## QA round 1

Date: 2026-11-19 UTC, independent QA round 1.
Path: `no-deployment`, from the brief's recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `59c80cbc57d8c0cd8446430df4eeba38c78987b5` on `main`, the merge of PR #360 at head `97cc69cd1420da02ead85eac6aaf4cef9a7cc6b6` (identical tree), which `git merge-base --is-ancestor` confirmed on `origin/main`.
Fixtures: none.
The acceptance criteria verified are the nine refined criteria (R1 to R9) of the accepted refinement comment `9d6d5978`, which replace the description's five; each description box is mapped below.
The raw output is attached to SKL-343 as "SKL-343 QA round 1 assertion output"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| R1: refinement note | Verified | Comment `9d6d5978` names the eight files read, the unsupportable AC1 clause and D1 to D13. |
| R2: prior review in the delta reviewer brief | Verified | Rounds carries the earlier `Review of record <sha>` reviews as historical context that does not decide the verdict, and limits re-raising to a delta that changes or newly calls, imports or exercises the code. The judging-agent definition names that brief as its only exception. |
| R3: adjudicator stays clean, neutral | Verified | Rounds states that the adjudicator and shadow-adjudicator briefs never carry the prior review. The only added term is the canonical phrase "clean, neutral", and the two judging-agent definition bullets in `shared/code-review.md` are unchanged and in order. `tests/test_skills.py`: 85 passed. |
| R4: `pre-existing` tag, defined once | Verified | One definition under Handling findings covers the base SHA scope, adjudicator confirmation, the unconfirmed case, the non-blocking listing, filing and linking before merge, and the Medium/Low sentence. The gate and Handling findings cross-reference it. `tests/test_scope_ownership_rule.py` and `tests/test_merge_guard.py`: 45 passed. |
| R5: arbiter format line and drift test | Verified | The SKILL.md report format (before its first `###`) and the arbitrate dossier each carry one line, and the layout test is unmodified. `tests/test_pipeline_dossier_checkout.py` and `tests/test_pipeline_dossier_fixture.py`: 35 passed. With the dossier line deleted, the new test fails. |
| R6: generated copies | Verified | `scripts/vendor_shared.py --check` at the target exits 0. |
| R7: guards | Verified | Run 44564394375 on the reviewed head concluded `success` for `checks` (full pytest, leak scan with `--require-private`, `skills-ref validate`) and `discovery` (`smoke-opencode.sh`). The local full suite was not run: owner directive, full suite deferred to the end. |
| R8: boundary | Verified | The diff lists 18 files: `shared/code-review.md`, the 13 copies, the pipeline `SKILL.md` and script (under `skills/adversarial-review-pipeline/scripts/`), and two test files. |
| R9: size guard | Verified | Recomputed from base `edc0b24` for the 13 skills, the largest growth is 1.433% (linear-bug), matching the PR table. |
| Description: prior review in the brief | Verified | R2; D1 of the accepted refinement dropped the arbiter-format clause. |
| Description: pre-existing tag | Verified | R4 and R5. |
| Description: adjudicator brief without the prior review | Verified | R3. |
| Description: copies | Verified | R6 and R7. |
| Description: size guard | Verified | R9. |
| DoD: all acceptance criteria met | Verified | All rows above. |
| DoD: tests written and passing | Verified | Six new tests in `tests/test_merge_guard.py` and `tests/test_pipeline_dossier_checkout.py` pass. |
| DoD: independently reviewed | Verified | Review 5978937805 is the review of record on the merged head with adjudicator verdict CLEAR; its confirmed `pre-existing` findings are filed as SKL-370, SKL-371 and SKL-372. |
| DoD: docs updated | Verified | `shared/code-review.md`, its 13 copies and the arbiter report format. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | None found. |

Pending owner rulings: none.

Closing decision: Done, once this evidence merges.
