# SKL-357 QA evidence

## QA round 1

Date: 2026-11-17 UTC, independent QA round 1.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `b168e010ad07ee05c913fc8660608bf9645b0b91` on `main`, which `git merge-base --is-ancestor` confirmed on `origin/main` after a fetch.
Fixtures: none; every check ran in a throwaway detached worktree of the target.
The raw output is attached to SKL-357 as "SKL-357 QA round 1 assertions"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC 1: waiting-handback bullet in both base templates and every rendered brief; step 2 vocabulary test unmodified | Verified | The exact bullet appears once in `assets/brief-engineer.md` and `assets/brief-qa.md`, and once in each of seven `render-brief.py` renders covering both roles on all three paths. The step 2 vocabulary test and the constants it reads are source-identical to the pre-story `main` and pass. |
| AC 2: unnamed waiting handback, its naming resume and its stops | Verified | `references/interim-handbacks.md` lines 9 to 11 and 16 hold the definition, the QA exclusion, the stall rule and the classification order. Lines 54 to 59 hold the naming resume, its bounds, the answer rule, the second-handback stop and the cannot-resume stop. |
| AC 3: checklist read at each interim and unnamed waiting handback | Verified | Lines 63 and 64 hold the read with every recorded state and `no previous read`, and its no-send, separate and outside-the-cap clauses. |
| AC 4: stale checklist and its one bounded resume | Verified | Lines 68 to 72 hold the stale definition, the stale-checklist resume, its once-per bound with the AC 2 stop taking precedence, its no-count clauses and the cannot-resume stop. |
| AC 5: suite green and pinned sentences mutation-proven | Verified | `uv run --locked pytest -q` passed 3223 tests. Removing each of 25 pinned lines, with the whole-file digest test deselected, failed at least two sentence tests each: 25 killed, 0 survived. |
| AC 6: first paragraph and Limits paragraph consistent | Verified | The first paragraph adds the new class at lines 9 to 11 and its read-back sentence covers both classes at line 12. The Limits paragraph at line 76 admits the new classes, reads, resumes and stops. |
| DoD: All acceptance criteria met | Verified | AC 1 to AC 6 above. |
| DoD: Unit/integration tests written and passing | Verified | New tests in `tests/test_story_to_done.py` and `tests/test_render_brief.py`, and the suite is green. |
| DoD: Independently reviewed | Verified | PR #330 carries a `COMMENTED` review of record whose `commit_id` and first-line SHA equal the PR head `b5e8ee4e3a07ab0260d96b6d3d1241c4a34019e7`, and the merged files equal that head. |
| DoD: Docs updated (if applicable) | Verified | The skill text is the documentation: `SKILL.md`, both brief templates, `interim-handbacks.md` and `metrics-protocol.md`. |
| DoD: Verified in a deployed environment (if needed) | Correct by design (not needed) | The path is `no-deployment`: the change is skill text and tests with no deployed surface. |
| DoD: No critical bugs/regressions | Verified | The full suite is green on the target, and CI `checks` and `discovery` succeeded on `b168e01`. |

Pending owner rulings: none.

Closing decision: Done, once this evidence merges.
