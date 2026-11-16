# SKL-318 QA evidence

## QA round 1

Date: 2026-11-16 UTC, independent QA round 1.
Target: `main` at `5a127dd03dcd8cc56d29aed6ddaf74352300cba8`, the squash merge of PR 294, whose reviewed head is `2942f783ef175edfb49bab62b3006a1f20578d75`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Fixtures: none; every test and probe root is synthetic.
The raw output is attached to SKL-318 as "QA round 1: A1 A2 A4 A5 Normaliser probe output" and "QA round 1: A3 A6-A9 and DoD test runs, CI, review of record"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| A1: a known root inside a JSON string literal is redacted whatever its spelling | Verified | A scratch probe drives `Normaliser(...)(text)` at the target with one synthetic root per placeholder (`run_dir`, `home`, `tmp`, `tmpdir`), ASCII and non-ASCII, spelled with `\/`, every character as `\uXXXX`, one character as `\uXXXX`, `\/` and `\uXXXX` combined, raw UTF-8, and `json.dumps` default escapes. Every case decodes to its placeholder, leaves no root fragment, and is idempotent. At `57807ed` the `\/`, all-`\uXXXX` and combined spellings keep the root; plain spellings (raw UTF-8, and default `json.dumps` of an ASCII root) were already redacted by the text pass. |
| A2: the tail after a root is kept, and `\/` re-encodes to `/` | Verified | The same probe with the tail `/My Notes/a b.txt` gives `<placeholder>/My Notes/a b.txt` for every spelling, and a `\/` tail comes back as plain `/`. |
| A3: every case passing at `57807ed` still passes unchanged | Verified | `tests/test_eval_suite.py` from `57807ed` against `suite.py` at the target passes 146. The diff to that file changes no existing param or expected value; besides new cases, it adds an `\/`-escaped field to the stub's `evidence.json` and new assertions to the existing record test (A7). The text pass and `AFTER_ESCAPE` remain in `suite.py`. |
| A4: no-root text is unchanged, a changed literal re-encodes by rule | Verified | The probe compares 125 committed eval texts and 3 synthetic no-root texts byte for byte with `57807ed` output, with no difference. An all-ASCII literal re-encodes as ASCII, a raw UTF-8 literal stays raw, a literal with a lone surrogate re-encodes as ASCII and the output encodes as UTF-8, and bytes outside the changed literal are kept. |
| A5: undecodable literals and non-JSON text go to the text pass | Verified | The probe's undecodable literal, text with no decodable literal, and JSON Lines text with a bad line give the `57807ed` output, with the root redacted by the text pass. Literals in prose and in each JSON Lines line are redacted. `test_a_record_with_bytes_that_are_not_utf8_is_still_written` passes at the target. |
| A6: one parameterized test, must-fail red before and green after | Verified | `test_the_normaliser_decodes_each_string_literal_before_redacting_known_roots` covers the A1 and A2 spellings for both root sets, both lone-surrogate cases, and the no-change case, with `must-fail` and `guard` ids, exact equality, idempotence and a UTF-8 encode. With `suite.py` restored from `57807ed` the file gives 59 failed and 156 passed, all by `AssertionError`: 58 `must-fail` ids and the record test fail, and no `guard` id fails. At the target the file passes 215. The PR 294 body quotes both outcomes. |
| A7: the stub's `\/` run dir never reaches a record | Verified | The stub writes its run directory behind `\/` into `evidence.json`. `test_run_directories_sit_outside_both_checkouts_and_never_reach_a_record` asserts that spelling was written, that no JSON-decoded string of any record holds a run directory, and that the grader input decodes to `{run_dir}`. It passes at the target and fails with `suite.py` from `57807ed`. |
| A8: the redactor comment describes the decoded-literal pass | Verified | The comment above the redactor patterns in `suite.py` describes decoding each literal, redacting known roots, re-encoding only a changed literal, and the text pass as the second line of defence. |
| A9: every repository guard passes | Verified | CI run 43822435429 on head `2942f783ef175edfb49bab62b3006a1f20578d75` passed `checks` (2795 tests, the leak scan with `--require-private`, and the pinned `skills-ref validate` with `skills/story-to-done` valid) and `discovery`. None of the three changed files is a GENERATED file, and a local public-pattern leak scan has no hit. |
| DoD: all acceptance criteria met | Verified | A1 to A9 above. |
| DoD: tests written and passing | Verified | At the target `tests/test_eval_suite.py` passes 215 and the full suite passes 2777 locally. |
| DoD: independently reviewed | Verified | PR 294's review of record is `COMMENTED` at `2942f783ef175edfb49bab62b3006a1f20578d75`, with that SHA on its first line, naming Codex GPT-6 Sol as reviewer and DeepSeek V4 Pro as adjudicator, with both findings ruled invalid and the merge clear. |
| DoD: docs updated | Verified | `skills/story-to-done/evals/README.md` states that roots are rewritten whether the path is plain or spelled with any JSON escape inside a string literal. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path; verified against the merged commit. |
| DoD: no critical bugs or regressions | Verified | The full suite passes locally and in CI, and the `57807ed` tests pass against the new `suite.py`. |

Closing decision: Done, once this evidence merges.
