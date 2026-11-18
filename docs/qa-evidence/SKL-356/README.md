# SKL-356 QA evidence

## QA round 1

Date: 2026-11-18 UTC, independent QA round 1.
Target: `main` at `438494cfa9061de96c70ceefafd22d579f820c1c`, the squash merge of PR 335, whose reviewed head is `15f88eba396f57e91961d1249e6746f6ece68901`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
The target differs from the reviewed head only by `docs/qa-evidence/SKL-346/README.md`, another story's file.
Path: `deployed`, from the recorded `path: deployed` line, which `select-path.py` returns as given.
The profile lists no environment (`environments: []`), so the deployed path has no environment or build to verify against; without the recorded line, `select-path.py` selects `no-deployment` for this profile.
The recorded path and the profile disagree, and the path line needs reconciling by its owner before a later QA round.
The criteria below were checked by reading the merged commit and the CI runs named; no deployed-path exemption is applied.
Fixtures: a detached worktree at the target, and the case's committed scenario fixtures and results.
No test suite or eval ran locally, on the owner's instruction for this run; the pytest and private leak scan guards rest on CI run 44237455249 only.
The raw output is attached to SKL-356 as "QA round 1: AC and guard checks against 438494c (raw output)"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: verification rule in the skill | Verified | Step 4 of `skills/story-to-done/SKILL.md` carries one rule with no new step, covering a handback, the coordinator's own reading, step 0's resume path, any stop and step 5's report. It reads the story's state, criteria, comments and relations with each blocker's state, records `owner-only` and `coordinator-or-role-can-act` with their supporting field, and reports a failed read as unverified. The `in_deployment_review` owner-action stop defers to it, and the dispute rule is unchanged in the diff. |
| AC2: act, do not ask | Verified | With `owner-only: no` and `coordinator-or-role-can-act: yes` the coordinator does the next step or launches or resumes the role it dispatches, with a brief from the criteria, and reports no owner-wait, step 5's report included. The continuation and stall rules still apply, and the mixed-remainder sentence applies only to a remainder with an item verified `owner-only: yes`. |
| AC3: owner-only items still stop | Verified | The rule lists the owner-only categories, states that an owner-approval gate for the story's own outcome is not owner-only while a maintainer's approval stays owner-only, and on `owner-only: yes` reports and stops naming the story id, the exact criterion text, the comment or relation read and the category. |
| AC4: eval case pair | Failed | The case files, the `both` invocation, both scenario fixtures and the suite counts (baseline `rescoped-brief` 0/3, candidate 3/3 in both scenarios) are present. The committed `grader.py` replaced the check the records were graded with (harness `ad92cae`) by an LLM judge whose verdict is reused only from a kept `judge-verdict.json`, and no record keeps one. Re-grading each record with stub judges shows all six `owner-value` verdicts flip between pass and fail on the judge's answer, so they reproduce only through a new, unrecorded judge call. The candidate runs were recorded at `ad92cae`, and the merged rule text differs from it by the `owner-only: no` / `coordinator-or-role-can-act: no` line and "or access grant". |
| AC5: guards on the final files | Verified (CI only for pytest and the private leak scan) | CI run 44237455249 on the reviewed head passed repository tests, the leak scan with private patterns, spec validation and opencode discovery. `skills-ref validate skills/story-to-done` reports "Valid skill" at the target. No file under `skills/*/references/` or `shared/` changed, and the recorded files are unchanged since the commit that added them. |
| DoD: all acceptance criteria met | Failed | AC4 failed. |
| DoD: unit and integration tests written and passing | Verified (CI only) | `tests/test_story_to_done.py` pins the rule text, its place before the unchanged dispute rule and the deferral line, and the repository tests passed in CI run 44237455249. |
| DoD: independently reviewed | Verified | PR 335 has its review of record at `15f88eb`, the merged head, by GPT-6.1 Sol and DeepSeek V4.1 Flash, the reviewer and adjudicator the profile names. |
| DoD: docs updated (if applicable) | Verified | `skills/story-to-done/SKILL.md`, the `owner-wait-verified` section and row in `skills/story-to-done/evals/README.md`, and the case's `rerun.md`. |
| DoD: verified in a deployed environment (if needed) | Not covered | The recorded path is `deployed`, and the profile has no environment (`environments: []`) to verify in; the box stays unticked until the path is reconciled. |
| DoD: no critical bugs or regressions | Verified | CI passed on the reviewed head, and spec validation passes at the target. |

Closing decision: In Progress, with a dated deployment-review note on AC4; the path reconciliation is listed with it.
