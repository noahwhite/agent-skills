# SKL-319 QA evidence

## QA round 1

Date: 2026-11-16 UTC, independent QA round 1.
Target: `main` at `3cde37f583087368eb203896791a59d3e3ccd3b8`, the squash merge of PR 307, whose reviewed head is `4a682ef5233c8fc77726b7210aa30c62bfb1cc66`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`, and the dependency SKL-318 (Done, merged as `5a127dd03dcd8cc56d29aed6ddaf74352300cba8`) is an ancestor of the target.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Fixtures: none; every test and probe root is synthetic.
The raw output is attached to SKL-319 as "QA round 1: B1-B7 and DoD test runs, probe, CI, review of record"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| B1: a known root after a non-ASCII character is replaced; control characters stay redacted; only an ASCII letter, digit, `_`, `.` or `-` keeps the root | Verified | At the target `tests/test_eval_suite.py` passes 276, including all 62 ids of `test_only_an_ascii_word_character_before_a_known_root_keeps_it` and the record test. A scratch probe drives `Normaliser(...)(text)` with synthetic roots: `é` and `ñ` before a root in decoded text, raw UTF-8 JSON and `é` form give the placeholder; newline, tab, carriage return, backspace and form feed before a root give the placeholder; an ASCII letter, digit, `_`, `.` or `-` keeps the root whole; every result is idempotent (18 of 18 pass). |
| B2: generic paths keep their `57807ed` behaviour, `/café/home/u` becomes `/café{home}`, a spaced tail is kept | Verified | The probe gives `/café{home}` for `/café/home/u` and `é{run_dir}/My Notes/a b.txt` for a spaced tail, and keeps a URL and a relative path. The `cafe-then-home-root`, `cafe-generic-path`, `e-acute-generic-path` and `e-acute-run-root-spaced-tail` cases pass at the target. |
| B3: every case passing at `57807ed` still passes unchanged | Verified | `tests/test_eval_suite.py` from `57807ed` passes 146 against `suite.py` from `57807ed` and 146 against `suite.py` at the target. The diff to that file from `57807ed` adds cases and stub fields and changes no existing param or expected value. |
| B4: one parameterized test, must-fail red before and green after | Verified | `test_only_an_ascii_word_character_before_a_known_root_keeps_it` drives only `Normaliser(...)(text)` with synthetic roots, exact equality and idempotence, and names each id `must-fail` or `guard`. With `suite.py` restored from `57807ed` the selection gives 25 failed and 37 passed, all by `AssertionError`: the 24 `must-fail` ids and the record test fail, and no `guard` id fails. At the target all 62 pass. The PR 307 body quotes both outcomes with `must-fail-e-acute-run-root-decoded`. |
| B5: the stub's `é` run dir never reaches a record | Verified | The stub writes its run directory behind `é` into `evidence.json`. `test_run_directories_sit_outside_both_checkouts_and_never_reach_a_record` asserts that no JSON-decoded grader input holds a run directory; it passes at the target and fails with `suite.py` from `57807ed`. |
| B6: the redactor comment describes the ASCII left boundary | Verified | The comment above `ROOT_LEFT` in `suite.py` states that only an ASCII letter, digit, `_`, `.` or `-` before a root keeps it whole. |
| B7: every repository guard passes | Verified | CI run 43906692063 on head `4a682ef5233c8fc77726b7210aa30c62bfb1cc66` passed `checks` (2972 tests, the leak scan with `--require-private`, and the pinned `skills-ref validate` with `skills/story-to-done` valid) and `discovery`. Neither changed file is a GENERATED file, and a local public-pattern leak scan has no hit. |
| DoD: all acceptance criteria met | Verified | B1 to B7 above. |
| DoD: tests written and passing | Verified | At the target `tests/test_eval_suite.py` passes 276 locally, and CI run 43907913821 on the target passed `checks` with 2972 tests. |
| DoD: independently reviewed | Pending owner ruling | PR 307's review of record is `COMMENTED` at `4a682ef5233c8fc77726b7210aa30c62bfb1cc66`, clean, with its one finding ruled invalid. It names Codex GPT-6 Sol (`gpt-6-sol`) as reviewer and DeepSeek V4 Pro (`deepseek/deepseek-v4-pro`) as adjudicator, while `.agent-skills/profile.yaml` at that head names GPT-6.1 Sol (`gpt-6.1-sol`) and DeepSeek V4.1 Flash (`deepseek/deepseek-flash`). Under a reading that binds the seats to the profile's reviewer and adjudicator the item is not met; under a reading that requires an independent reviewer and a separate clean, neutral adjudicator, clean on the head with every finding adjudicated, it is met. The product owner owns the ruling. |
| DoD: docs updated | Verified | B6. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path; verified against the merged commit. |
| DoD: no critical bugs or regressions | Verified | The full suite passes in CI on the PR head and on the target, and the `57807ed` tests pass against the new `suite.py`. |

Closing decision: stays In Deployment Review until the product owner rules on "Independently reviewed".
