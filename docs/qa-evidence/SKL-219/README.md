# SKL-219 QA evidence

## Round 1

Date: 2026-11-09 UTC, independent QA round 1.
Build under test: `main` at `4542552235e1e6587892e9242162d911dbda6930`, the squash merge of PR 173, whose reviewed head is `95aa3fa6625671cd379f77e86655216136168d84`.
`git diff --stat 95aa3fa 4542552` is empty, so the merged tree is the reviewed tree.
Environment: the profile lists no environments, so every item was verified against a fresh worktree of `main` and its CI.
Tool versions: uv 0.13.7, Python 3.12.3, pytest 9.1.1.
Fixtures: none.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-219 as the "SKL-219 QA round 1 raw assertion output" attachment.

| Item | Verdict | Evidence |
|---|---|---|
| B1: keep going | Verified | The quoted keep-going sentence appears once in each of the four briefs: `skills/story-to-done/SKILL.md` lines 110 (senior engineer) and 145 (QA agent), `skills/persona-staff-engineer/SKILL.md` line 78 and `skills/persona-staff-devops/SKILL.md` line 88. Each bullet's next sentence restates that brief's own stop point: hand back blocked, hand back outstanding items with their owner, the merge-approval handshake, and the stop before merge. |
| B2: real check | Verified | The "real-check rule" bullet (story-to-done line 111, staff-engineer line 79, staff-devops line 89) requires a real check that exercises the change, rejects a syntax-only check or one that failed to start, allows only the project's package manager and lockfile and never sudo or the system package manager, and names any check not run and why. The QA brief has no such bullet. |
| B3: scope | Verified | Both quoted scope sentences appear once in each engineer brief (story-to-done line 112, staff-engineer line 80, staff-devops line 90), followed by "The tests the real-check rule needs are called for by this brief." The QA brief does not carry them. |
| B4: no self-started reviews | Verified | The quoted sentence appears once in each of the four briefs (story-to-done lines 113 and 146, staff-engineer line 81, staff-devops line 91), each followed by the sentence that keeps the `engineering-workflow` pre-PR gate and review of record allowed; the QA brief also keeps the evidence PR's review of record. |
| B5: checklist read-back | Verified | Each skill's step 0 seeds "the checklist read-back at each handback with each subagent's read-back resume count" (line 70 in story-to-done, line 40 in both personas) and states the rule once, on the lines right after the mirroring sentence (story-to-done lines 74 to 82, both personas lines 43 to 48). The rule covers a missing checklist as open, the quoted resume message at most twice per subagent, the tracker state as the record, and the no-resume fallback that spawns no subagent. story-to-done adds the QA rules: before step 4, no verdict, no round increment, a separate cap, and its own launch row with `metrics` on. None of these sentences appears in the shadow adjudicator text in step 4 of either persona. B5 asks for this text, and the verdict covers the text only. The behavior eval does not show reliable adherence: in `skills/story-to-done/evals/qa-unfinished-own-steps/results/candidate-1f24df1.md`, the current candidate record, the read-back scenario passes 0 of 3 runs, and every run sends step 4's continuation instead of step 0's read-back message. Counting the superseded `candidate-b3b33ca.md` (2 of 3), the candidate passes 2 of 6 against the baseline's 0 of 6, on the `deepseek/deepseek-v4-pro` proxy model. PR 173's review of record ruled this adherence gap valid, Medium and non-blocking (finding D1). |
| B6: copies and tests | Verified | `git diff --stat 8eb74e0 4542552 -- shared/` is empty. Rerunning `scripts/vendor_shared.py` leaves `git status --porcelain` empty, and `--check` exits 0. `tests/test_delegated_briefs.py` holds 33 passing tests covering B1 to B5 and the shadow text. The `qa-unfinished-own-steps` eval was updated in PR 173. Outside the three skills, the read-back message is copied in that eval's `grader.py` (`READ_BACK_RESUME`), `tests/test_delegated_briefs.py` and `tests/test_story_to_done.py`, and each copy matches the skill text; no other fixture copies the changed SKILL.md text. `uv run pytest -q` reports 1418 passed. |
| DoD1: all acceptance criteria met | Verified | B1 to B6 are verified. |
| DoD2: tests written and passing | Verified | See B6. |
| DoD3: independently reviewed | Verified | The review of record on PR 173 (Codex GPT-6 Sol reviewer, DeepSeek V4 Pro adjudicator, `BLOCKING: none` on both rounds) is on `95aa3fa`, the merged head, submitted at 23:26:33Z before the 23:27:24Z merge. |
| DoD4: docs updated | Verified | The change is the skill text itself, and `skills/story-to-done/references/metrics-protocol.md` names the read-back resume. |
| DoD5: verified in a deployed environment | Not needed | The profile lists no environments; `main` at `4542552` was verified directly. |
| DoD6: no critical bugs or regressions | Verified | The full suite passes and `main` CI run 42720596800 succeeded on `4542552`. |

Closing decision: Done, once this evidence merges.
