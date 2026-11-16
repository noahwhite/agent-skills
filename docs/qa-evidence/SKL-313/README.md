# SKL-313 QA evidence

## QA round 1

Date: 2026-11-16 UTC, independent QA round 1.
Target: `main` at `8a099a8181d21d9a2bc9ab10ae32eec15fc90935`, the squash merge of PR 272, whose reviewed head is `b1891a2f73a599d71eda0ba477fca50e7f7ce9dc`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`, and the merged tree equals the reviewed head's tree.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Fixtures: none; every probe path is synthetic.
The raw output is attached to SKL-313 as "SKL-313 QA round 1 assertion output at target 8a099a8"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: a path after each JSON escape is rewritten | Verified | At the target `uv run --locked pytest -q tests/test_eval_suite.py` passes 146. The parameterized test feeds `json.dumps`-serialised messages with a path after `\n`, `\t`, `\r`, `\b`, `\f` and `\uXXXX` (digit, letter and e-acute forms, plus uppercase hex as serialised text), for the run root (`{run_dir}`), the home root and another absolute path (`{path}`), and asserts exact equality. |
| AC2: other boundaries still rewritten, kept cases kept | Verified | The same run passes the space, raw quote, escaped quote and start-of-string cases for the run root and another path, and `other-standalone` rewrites `/srv/home/user` to `{path}`. The URL, relative path, `prefix` word and bare-`n` cases, for the run root and another path, keep the text unchanged. |
| AC3: one parameterized regression test, red before and green after | Verified | `test_the_normaliser_rewrites_a_path_after_each_boundary_in_a_serialised_message` is one parameterized test with synthetic roots (`/scratch/run-1`, `/scratch/home-1`, `/srv/home/user`) and an exact-equality assertion. With `suite.py` restored from `186df21` its 70 cases give 44 failed and 26 passed, every escape case among the failures and every kept or pre-existing boundary case among the passes; at the target all pass. The PR 272 body quotes both outcomes (`44 failed, 102 passed` and `146 passed`) with the failing case names. |
| DoD: root cause identified | Verified | The merged diff changes the two lookbehinds, not the path content: `AFTER_ESCAPE` (a lookbehind for a complete `\n \t \r \b \f \uXXXX` escape) is added as an alternative boundary to the run-root rewrite and to `ABSOLUTE_PATH`. |
| DoD: fix verified against the original failing case | Verified | A scratch probe builds the normaliser as `suite.py` does for a record, normalises a `messages.json` whose assistant message starts lines with the run directory, the scratch directory, the home directory and another absolute path, and serialises the record. At the target the record holds only placeholders and none of the probe base, the home name or the session marker; with `suite.py` from `186df21` all three remain. |
| DoD: regression protection added | Verified | The AC3 test, run by the `Repository tests` step of CI. |
| DoD: independently reviewed | Verified | The review of record on PR 272 is `COMMENTED` at `b1891a2f73a599d71eda0ba477fca50e7f7ce9dc`, with that SHA on its first line. It names GPT-6.1 Sol (`gpt-6.1-sol`) as reviewer and DeepSeek V4.1 Flash (`deepseek/deepseek-flash`) as adjudicator, with no findings and 0 blocking. |
| DoD: docs and comments updated | Verified | A comment above `AFTER_ESCAPE` in `suite.py` states why an escape is a boundary and that a quoted escape is over-redacted by design; the test pins that case as `quoted-escape`. |
| DoD: no new regressions | Verified | At the target the full suite passes 2631 locally. CI run 43790431353 on `main` at the target passed `checks` (repository tests, leak scan with private patterns, skill validation) and `discovery`. |

Closing decision: Done, once this evidence merges.
