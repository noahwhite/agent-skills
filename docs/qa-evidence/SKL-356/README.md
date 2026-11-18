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
