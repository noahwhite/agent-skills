# SKL-356 QA evidence

## QA round 1

Date: 2026-11-18 UTC, independent QA round 1.
Merged change: `main` at `438494cfa9061de96c70ceefafd22d579f820c1c`, the squash merge of PR 335, whose reviewed head is `15f88eba396f57e91961d1249e6746f6ece68901`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
Path: `deployed`, from the recorded `path: deployed` line, which `select-path.py` returns as given.
The profile lists no environment (`environments: []`), so the deployed path has no environment or deployed build to verify against; without the recorded line, `select-path.py` selects `no-deployment` for this profile.
The recorded path and the profile disagree, so no item could be verified on the recorded path, and no other path's target or exemption is applied.
The path line needs reconciling by its owner, then a new QA round verifies every item.
No test suite or eval ran locally, on the owner's instruction for this run.
The raw output is attached to SKL-356 as "QA round 1: AC and guard checks against 438494c (raw output)"; there is no visual surface, so no screenshot applies.

Each verdict below is for the recorded `deployed` path.
The observations come from reading the merged commit and CI runs; they are not verdicts, and the next round verifies them afresh.

| Item | Verdict | Observation at the merged commit |
|---|---|---|
| AC1: verification rule in the skill | Not covered | Step 4 of `skills/story-to-done/SKILL.md` carries one rule with no new step, covering a handback, the coordinator's own reading, step 0's resume path, any stop and step 5's report, with the tracker read, the two todo entries and the failed-read report; the `in_deployment_review` stop defers to it, and the dispute rule is unchanged. |
| AC2: act, do not ask | Not covered | The rule acts on `owner-only: no` with `coordinator-or-role-can-act: yes`, keeps the continuation and stall rules, and limits the mixed-remainder sentence to a remainder with an item verified `owner-only: yes`. |
| AC3: owner-only items still stop | Not covered | The rule lists the owner-only categories, states the own-outcome approval distinction, and reports and stops naming the story id, criterion text, comment or relation and category. |
| AC4: eval case pair | Not covered | Two clauses do not hold. The committed `grader.py` decides each `owner-value` verdict through an LLM judge it reuses only from a kept `judge-verdict.json`, no record keeps one, and re-grading with stub judges flips all six `owner-value` verdicts, so re-running it does not reproduce the recorded verdicts without a new judge call; the records were graded by the harness at `ad92cae`. The candidate runs were recorded at `ad92cae`, and the merged rule text differs from it by the `owner-only: no` / `coordinator-or-role-can-act: no` line and "or access grant". |
| AC5: guards on the final files | Not covered | CI run 44237455249 on the reviewed head passed repository tests, the leak scan with private patterns, spec validation and opencode discovery; `skills-ref validate skills/story-to-done` reports "Valid skill" at the merged commit; no file under `skills/*/references/` or `shared/` changed. |
| DoD: all acceptance criteria met | Not covered | No criterion could be verified on the recorded path. |
| DoD: unit and integration tests written and passing | Not covered | `tests/test_story_to_done.py` pins the rule; repository tests passed in CI run 44237455249. |
| DoD: independently reviewed | Not covered | PR 335 has its review of record at `15f88eb`, the merged head, by GPT-6.1 Sol and DeepSeek V4.1 Flash. |
| DoD: docs updated (if applicable) | Not covered | `skills/story-to-done/SKILL.md`, the `owner-wait-verified` section and row in `skills/story-to-done/evals/README.md`, and the case's `rerun.md` changed. |
| DoD: verified in a deployed environment (if needed) | Not covered | The profile has no environment to verify in. |
| DoD: no critical bugs or regressions | Not covered | CI passed on the reviewed head. |

Closing decision: QA is not finished; the story stays in In Deployment Review until the path is reconciled and a new round runs.

## QA round 2

Date: 2026-11-18 UTC, independent QA round 2.
Path: `no-deployment`, from the recorded `path: no-deployment` line, which supersedes the earlier `path: deployed` line; `select-path.py` returns `no-deployment`.
Target: `main` at `438494cfa9061de96c70ceefafd22d579f820c1c`, the squash merge of PR 335, whose reviewed head is `15f88eba396f57e91961d1249e6746f6ece68901`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
The profile lists no environment, so there is no deployed build; fixtures: none.
No test suite, smoke script, eval or live-judge grading ran, on the owner's instruction for this run; CI run 44237455249 on the reviewed head stands in for the four guards.
The raw output is attached to SKL-356 as "QA round 2: AC and guard checks against 438494c, no-deployment path (raw output)"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence at the merged commit |
|---|---|---|
| AC1: verification rule in the skill | Verified | Step 4 of `skills/story-to-done/SKILL.md` (lines 308-311) states one rule with no new step, binding a handback, the coordinator's own reading, step 0's resume path, any stop and step 5's report, with the tracker read, the two todo entries and the failed-read report; line 300 defers the `in_deployment_review` stop to it; the dispute rule (lines 319-320) is unchanged. |
| AC2: act, do not ask | Verified | Line 314 acts on `owner-only: no` with `coordinator-or-role-can-act: yes` and reports no owner-wait, step 5 included; line 315 keeps the continuation and stall rules; line 300 limits the mixed-remainder sentence to a remainder with an item verified `owner-only: yes`. |
| AC3: owner-only items still stop | Verified | Line 312 lists the categories, line 313 states the own-outcome approval distinction and keeps a maintainer's approval owner-only, and line 317 reports and stops naming the story id, criterion text, comment or relation and category. |
| AC4: eval case pair | Failed | The candidate runs were recorded at `ad92cae`, and the merged rule adds, after them, the `owner-only: no` / `coordinator-or-role-can-act: no` stop line and "or access grant", so no candidate run exercised the delivered skill text. Re-running the committed `grader.py` with a judge that launches no model voids the 9 records that carry a final message, since no record keeps `judge-verdict.json`; reproduction was not shown. The case structure, the `both` invocation, the two fixtures, the grading predicates and the baseline (`9e65dd3`, Scenario A failing 3 of 3) hold. |
| AC5: guards on the final files | Verified | CI run 44237455249 on the reviewed head passed repository tests, the leak scan with private patterns, spec validation and opencode discovery; the results were added in one commit and never edited; no file under `skills/*/references/` or `shared/` changed. |
| DoD: all acceptance criteria met | Failed | AC4 failed. |
| DoD: unit and integration tests written and passing | Verified | `tests/test_story_to_done.py` and `tests/test_merge_guard.py` pin the rule; repository tests passed in CI on the reviewed head. |
| DoD: independently reviewed | Verified | PR 335's review of record at `15f88eb`, by GPT-6.1 Sol and DeepSeek V4.1 Flash, is clean with every finding adjudicated. |
| DoD: docs updated (if applicable) | Verified | `skills/story-to-done/SKILL.md`, the `owner-wait-verified` section and row in `skills/story-to-done/evals/README.md`, and the case's `rerun.md`. |
| DoD: verified in a deployed environment (if needed) | Not needed | Correct by design on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | CI passed on the reviewed head, and none was found. |

Closing decision: AC4 failed, so the story goes back to In Progress for the engineer.
