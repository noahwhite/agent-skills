# SKL-310 QA evidence

## QA round 1

Date: 2026-11-15 UTC, independent QA round 1.
Target: `main` at `86daabe92a4bbc0cb7e2f267997acf5e53f0898e`, the squash merge of PR 267, whose reviewed head is `7338649266fc408af79dadb2816fd46f553c57e3`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Fixtures: none.
Blockers SKL-156, SKL-164 and SKL-275 are Done.
The raw output is attached to SKL-310 as "SKL-310 QA round 1 assertion output at target 86daabe"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| C1: transcript classifier change | Verified | The merged commit changes only `tests/test_signing_key.py`. For a path matching `EVAL_TRANSCRIPT`, `signingkey_mention_kind` returns the restated-override kind only when `0 < mentions == inside`, both counted on the backtick-free line. The branch for every other path is the pre-change single-mention rule, unchanged. |
| C2: focused negative test, own commit | Verified | `test_a_transcript_line_with_a_mention_beyond_the_sentence_count_fails` passes at the target. With the rule loosened to accept any line holding a restated sentence, 3 of its 4 cases fail, so the test is not vacuous. The classifier change lands on `main` as the single commit `86daabe`, which touches no other file. |
| C3: producibility and guard record | Verified | The PR 267 body records the original rejection (two `candidate-sample` records with 3 and 5 mentions on one line, rejected by `test_signingkey_mentions_are_allowlisted`), the resolution, and the final-head guard table. Run 43767414515 on head `7338649` shows `checks` success (steps "Repository tests", "Leak scan (public and private patterns)", "Validate skills against the Agent Skills spec") and `discovery` success (step "opencode discovers every skill"). The case `results/` directory at the target holds only `.gitkeep`, so the sample records were not committed. A local public scan at the target reports INCOMPLETE with no finding. |
| C4: guard owner rejection path | Verified | Not triggered: no rejection of the classifier change is recorded on PR 267 or the story, and no other exemption was substituted. |
| DoD: all acceptance criteria met | Verified | C1 to C4. |
| DoD: tests written and passing | Verified | Four new parametrized tests in `tests/test_signing_key.py`. At the target the file passes 156 tests locally and the full suite passes 2561 with none failed locally; CI `checks` on `main` at the target (run 43768291261) passed 2579. With the pre-change classifier restored, 2 of the 3 multi-quote pass cases fail. |
| DoD: independently reviewed | Verified | The review of record on PR 267 is `COMMENTED` at `7338649266fc408af79dadb2816fd46f553c57e3`, with that SHA on its first line. It names GPT-6.1 Sol (`gpt-6.1-sol`) as reviewer and DeepSeek V4.1 Flash (`deepseek/deepseek-flash`) as adjudicator, with no findings and "Blocks merge: no". It was submitted at 22:15:30Z, before the 22:15:40Z merge. |
| DoD: docs updated (if applicable) | Correct by design | Not applicable: the change is test code only, and the classifier carries its own comment. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed: the run is on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | CI `checks` and `discovery` passed on `main` at the target (run 43768291261), with all 18 skills valid. |

Closing decision: Done, once this evidence merges.
