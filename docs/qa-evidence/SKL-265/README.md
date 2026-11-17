# SKL-265 QA evidence

Date: 2026-11-17 UTC, independent QA rounds 1 to 3.
Target: `main` at `8442597417fff261968962898cc68427b3b22a88`, the squash merge of PR 323, whose reviewed head is `c65b5c6b0dfb73bc7ad807c8e0ef81f1e426787d`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main` in each round, and `git diff c65b5c6 8442597` is empty, so the merged tree is the reviewed tree.
Path: `no-deployment`, selected by `select-path.py` with the story's title, its two labels and the recorded `path: no-deployment` line, so no environment or build SHA applies.
Fixtures: a fresh clone at the target in each round, and for AC7 one interactive Claude Code 2.1.326 session started with `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` through a pseudo-terminal, running story-to-done on SKL-246 (Done), per the 2026-11-17 owner decision in AC7.
The raw output of each round, the AC1 probe record and the AC7 scan command, scan output and session transcript are attached to SKL-265; there is no visual surface, so no screenshot applies.

| Item | Verdict | Round | Evidence |
|---|---|---|---|
| AC1: pre-implementation probe | Verified | 3 | The probe record "SKL-265 AC1 probe record (Claude Code 2.1.326)" was attached at 15:19:55Z, before the first PR 323 commit (authored 15:36:00Z). It records version 2.1.326, which the headless and background transcripts and the interactive screen log confirm, and covers one headless, one interactive (`CLAUDE_CODE_ENABLE_TODO_TOOLS=1`) and one background session with a logging hook on `Stop`, `SubagentStop` and PreToolUse `*`. Its (a) Stop fields, `agent_id` placement and `stop_hook_active` sequence match the raw payload log. It gives (c), (d) and its coverage limits. Its (b) names the earlier signal with line references that match `main` at 9556cbf, which the 2026-11-17 owner ruling accepts with no addendum. |
| AC2: report gate | Verified | 1 | Code read of the report gate and the Stop handler, and the suite's report-gate cases pass. A mutant that widens the signal to accept a list marker, backticks or emphasis is killed by 3 tests. |
| AC3: loop guard | Verified | 1 | `REPORT_BLOCK_LIMIT = 3` is one constant; the count lives in the session state directory and resets on an allowed Stop and on a main-thread prompt; `stop_hook_active` is not read. Mutants for a missing prompt reset and for `stop_hook_active` suppressing a block are each killed. |
| AC4: tests | Verified | 1 | Cases (a) to (j) are in `tests/test_todo_enforce.py`; the Stop payload fixture records version 2.1.326, marks each payload copied or synthesized and is normalized; six block branches are in the mutation table. Full suite: 3130 passed. |
| AC5: compatibility and vendoring | Verified | 1 | The pre-merge enforcer tests pass against the new enforcer except the exempt README block test; `vendor_shared.py` changes nothing and `--check` exits 0; the docstring lists Stop, the report gate and the loop guard. |
| AC6: README | Verified | 1 | The hooks block registers the enforcer for `Stop` with no matcher, the wording says five, every required statement is present, and the five-event block test passes. |
| AC7: session run | Verified | 2 | The installed skills match the target, the Stop hook is registered, and the session armed with the task tools present. The scan shows a question turn with no marker allowed, one report-gate block on the session's own first report followed by the session continuing (not provoked), and the next report allowed with every open item named as not done; the loop guard never fired. |
| AC8: repository guards | Verified | 1 | CI run 44164339908 on `c65b5c6`: `checks` (3148 passed, leak scan with `--require-private`, 18 valid skills) and `discovery` succeeded. |
| AC9: report marker in the skills | Verified | 1 | Both SKILL.md files carry the bare `report: final` rule and the "needs input never carries it" rule, the `metrics:` lines are unchanged, mutants removing either rule are killed by the guard test, and vendoring `--check` exits 0. |
| DoD: all AC met | Verified | 3 | AC1 to AC9 are verified. |
| DoD: unit and integration tests written and passing | Verified | 1 | 3130 passed locally and 3148 in CI. |
| DoD: independently reviewed | Verified | 1 | PR 323 review 5945747689 (COMMENTED, `commit_id` `c65b5c6`) by `profile.review.reviewer` GPT-6.1 Sol and `profile.review.adjudicator` DeepSeek V4.1 Flash, verdict clean, merged on that head. |
| DoD: docs updated (if applicable) | Verified | 1 | README, both SKILL.md files, and `shared/todo-tracking.md` rule 8 with its vendored copies. |
| DoD: verified in a deployed environment (if needed) | Correct by design | 1 | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | 2 | No defect on the merged commit, and in the live session the gate blocked and allowed as AC2 and AC3 specify while SKL-246's rule-4 deny still fired. |

AC1 ruling history: rounds 1 and 2 recorded AC1 (b) as pending an owner ruling, because the record names the earlier `metrics:` signal while amended (b) names `report: final`.
The product owner's dated 2026-11-17 amendment to AC1 rules that the probe record stands as a whole, including (b), with no addendum required, and round 3 verified AC1 against that text.

Closing decision: Done once this evidence PR merges.
