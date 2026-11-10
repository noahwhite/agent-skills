# SKL-223 QA evidence

## Round 1

Date: 2026-11-10 UTC, independent QA round 1.
Story: SKL-223 - replace the stale `user.signingkey` confirm line in base `github.md` with a never-sets rule.
Build under test: `main` at `92e0ed51ca41aa32f72f70013b0781bc847c594d`, the squash merge of PR 175, whose reviewed head is `8d98ee68c84b13b4ab0b99b7fb2604356086f013`.
Environment: the profile lists no environments, so every item was checked on the repository, GitHub and tracker lanes, in a detached worktree of the build.
Fixtures: none.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-223 as `SKL-223-qa-round-1-assertions.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| T1: base line reworded | Verified | `shared/github.md:51` equals the exact T1 sentence as a top-level bullet, line 50 is byte-identical to the merge parent, and the `git.signed_commits` description in `profile/schema.json` and `README.md:117-118` carry the matching text. |
| T2: vendored copies in step | Verified | `uv run scripts/vendor_shared.py --check` exits 0. The negative grep prints nothing and exits 1. The positive grep, scoped as T2 states to `shared/github.md`, `profile/schema.json`, `README.md` and `skills/*/references/github.md`, returns 16 matches: the 3 hand-maintained files and 13 of 13 generated copies. Unscoped, as PR 175 ran it, it returns 17, the extra match being the `NEVER_SETS_SIGNINGKEY` test constant at `tests/test_signing_key.py:849`. |
| T3: downstream AC unblocked | Verified | `git grep -n 'user\.signingkey' -- shared skills` returns 53 matches of kinds a=14, b=14, c=14 and d=11, none containing "resolves". Kind d is the 6 SKL-206 restatements plus 5 lines of recorded eval transcripts under `skills/story-to-done/evals/qa-unfinished-own-steps/results/` that embed the same restatement and were present at the merge parent. `test_signingkey_mentions_are_allowlisted` in `tests/test_signing_key.py` fails on any mention outside the four kinds. |
| T4: no regression | Verified | `uv run --locked pytest -q` reports 1430 passed with exit 0. `RULE_SENTENCES` now holds the T1 sentence and the new allowlist test is added. PR 175 records "no change needed" for `test_the_readme_documents_the_key_and_the_preflight`, and that test asserts only the kept "When `git.signing_key` is unset" prefix. |
| T5: gate | Verified | The PR 175 body records the T2 commands with exit statuses, the T3 match list with per-kind counts, and the pytest, leak scan and `skills-ref validate` results for head `8d98ee6`, which is the final head. CI run 42763602438 on `8d98ee6` and push run 42764266532 on `92e0ed5` succeeded. Rerun at the build, `leak_scan.py` exits 0 (INCOMPLETE locally with no private patterns; CI runs it with `--require-private`) and `skills-ref validate` reports 18 of 18 skills valid. |

The story description has no Definition of Done section, so there are no DoD items to verify.

Closing decision: Done, once this evidence merges.
