# SKL-284 QA evidence

## Round 1

Date: 2026-11-16 UTC, independent QA round 1.
Story: SKL-284 - `story-to-done`: script the `qa-round-cap` round counting and re-arm.
Path: `no-deployment`.
Target: `main` at `9c0ee6db65a83086facda57fd0e73cef81f3b34c`, the squash merge of PR 302, whose reviewed head is `4c33704d6098577c1c822d293c5a0d49c158c640`.
No environment or deployed build applies, so every item was checked on the repository, GitHub and tracker lanes.
The test suite, the guards and the probe ran in a detached worktree of the target.
Method: an independent probe drove `skills/story-to-done/scripts/qa-round-cap.py` through its CLI with a recording stub `linear` first on `PATH` and a sentinel token in the environment, making 42 assertions; the diff, the word counts and the tests were read at the target; the live check was read from the tracker.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw output is attached to SKL-284 under titles that begin "SKL-284 QA round 1".

| Item | Verdict | Evidence |
|---|---|---|
| AC1: interface | Verified | `--help` names `validate`, `arm`, `record` and `rearm` and exit codes 0 to 3. An unknown or missing subcommand exits 2 with one stderr line. Every non-zero exit in the probe printed one stderr line and left the state file's digest unchanged. |
| AC2: validate | Verified | `1`, `3` and `42` print the integer and exit 0. `0`, `-2`, `2.5`, `abc`, an empty value, no `=`, `007` and `+3` exit 2. |
| AC3: arm | Verified | The state file is `<state-dir>/qa-round-cap/<KEY>.json` with a 16-character lowercase hexadecimal count id and no temp file left beside it. `arm` without `--state-dir` exits 2. A second `arm` starts a new count with a new id and no rounds. |
| AC4: record | Verified | A QA evidence comment from before `arm` is not counted, a new one is, a comment whose first line is not the marker is not, and recording again with no new comment prints the unchanged line and leaves the state unchanged. Outside In Progress `record` exits 3 and records nothing. The second round prints `round=2 cap=2 reached=yes`. |
| AC5: re-arm | Verified | `--additional-rounds` `0` and `1.5` exit 2. On Done `rearm` exits 3 with stderr exactly `state=Done` and writes nothing. In In Progress it prints `state=In Progress` and sets the cap to 2 counted rounds plus 2, and the next round records as `round=3 cap=4 reached=no`. |
| AC6: failure, credentials, no writes | Verified | A failed tracker read on `record` and on `rearm` exits non-zero and keeps the three counted rounds. Every stub call is `linear api` with no mutation. The sentinel token is absent from the argv log, the state file, stdout and stderr. `tests/test_qa_round_cap.py` holds the sentinel and recording-stub tests the AC names. |
| AC7: evidence marker | Verified | `skills/qa-verification/SKILL.md` step 4 requires the QA evidence comment's first line to be exactly `## QA evidence`. The AC's "item 4" is that comment item as numbered when the story was refined; a later item renumbered it to item 5. `test_qa_verification_requires_the_qa_evidence_first_line` pins the marker. |
| AC8: invocations | Verified | The Arguments entry calls `validate`. The `in_progress` bullet carries the `arm`, `record` and `rearm` invocations in place of the counting, round-history and re-read sentences, each one simple command with literal values, and says the coordinator relays the script's stdout line. |
| AC9: kept prose | Verified | The ask-and-wait, reply-interpretation, re-arm ask, stop, hand-back, no-verdict, report-assembly and PR-read sentences remain, and the diff changes them only where they name the script. |
| AC10: unchanged | Verified | The `SKILL.md` diff has hunks at lines 41, 245 and 251 only, and Boundaries starts at line 289. `references/metrics-protocol.md` is not in the diff. |
| AC11: word count | Verified | Against merge-base `b3e4eea`, `SKILL.md` goes from 6908 to 6907 words and the `in_progress` bullet from 524 to 518. The PR 302 description records the merge-base, the extraction command and both counts, and the diff touches only the Arguments entry and the bullet. |
| AC12: tests | Verified | Tests drive the CLI with a stub `linear` first on `PATH`, and the fixture uses the synthetic key `ABC-123`, synthetic ids and the house spelling. Only the pins on removed sentences are replaced, and the no-verdict pin and `METRICS_CAP_STOP` stay. The three changed test files pass 486 tests, and the full suite passes 2893 tests. |
| AC13: guards | Verified | At the target `pytest` passes 2893 tests, `skills-ref validate` at the CI pin reports both changed skills valid, the opencode smoke test finds all 18 skills in 6 layouts, and the public leak scan is clean. CI `checks`, including the private leak scan, and `discovery` succeeded on `4c33704`, and CI succeeded on `9c0ee6d`. |
| AC14: live check | Verified | Throwaway story SKL-327 is Canceled and carries one comment whose first line is `## QA evidence`. The SKL-284 live-check comment shows `arm` with cap 1 and then `record` printing `round=1 cap=1 reached=yes`, which `record` prints only in In Progress, and the PR 302 description does not contain that line. |
| DoD: all acceptance criteria met | Verified | AC1 to AC14 are verified. |
| DoD: tests written and passing | Verified | 2893 tests pass at the target, and CI is green. |
| DoD: independently reviewed | Verified | The latest PR 302 review of record is a `COMMENTED` review whose first line and `commit_id` are `4c33704d6098577c1c822d293c5a0d49c158c640`, the merged head. Its reviewer is GPT-6.1 Sol and its adjudicator is DeepSeek V4.1 Flash. |
| DoD: docs updated | Verified | PR 302 edits `skills/story-to-done/SKILL.md` and `skills/qa-verification/SKILL.md`. |
| DoD: verified in a deployed environment | Not needed | Correct by design on the `no-deployment` path: the repository deploys nothing. |
| DoD: no critical bugs or regressions | Verified | The full suite passes, and the gate-invariant pins are unchanged. |

Closing decision: every item is verified, so the story moves to Done once this evidence merges.
