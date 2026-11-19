# SKL-35 QA evidence

## QA round 1

Date: 2026-11-19 UTC, independent QA round 1.
Path: `no-deployment`, docs/schema/test change, no environment or build SHA applies.
Target: merged commit `a8568ff4ad13264e6038f7d1ab38add6104d5836` on `main`, the squash of PR #369 head `15a77d2d6a93fc5863c5995c56557e767c9d4a15`.
The merged commit is confirmed an ancestor of `origin/main` (`git fetch` then `merge-base --is-ancestor`).

| Item | Verdict | Evidence |
|---|---|---|
| AC1: merge guard step 2 resolves the expected author, filters marker reviews, fails closed | Verified | `shared/code-review.md` step 2 resolves `profile.review.record_author` else `gh api user --jq .login`, fails closed reporting the failing command outside the waiver, keeps only `COMMENTED` `Review of record` reviews whose `user.login` equals the expected author case-insensitively, selects the greatest `submitted_at`, and lists each excluded marker review with `user.login`, `html_url` and `commit_id`. The waiver paragraph is unchanged. |
| AC2: both read-backs carry the same selection rule and fail-closed reporting | Verified | `skills/story-to-done/SKILL.md` step 2 and step 3 read-backs replace the selection parenthetical with the AC1 rule and report the PR, the expected author (or `unresolved` plus the failing command), each excluded review's `user.login` and `html_url`, and all SHAs before stopping the loop; SHA comparisons and the waiver comparison are kept. No other selection sites exist: `shared/merge-approval.md`, `skills/engineering-workflow` and `skills/qa-verification` name the review without selecting. |
| AC3: optional `review.record_author` in schema and commented example | Verified | `profile/schema.json` `review.record_author`: string, `maxLength` 45, pattern `^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\[bot\])?$`, description states the `gh api user` default and the fail-closed rule. `profile/example.yaml` documents it as a commented line. |
| AC4: pins, schema tests, vendoring, suite green | Verified | `tests/test_merge_guard.py` pins the new step-2 sentences and read-back text; `tests/test_record_author.py` accepts valid and `[bot]` logins and rejects non-strings, empty and invalid values; `tests/test_story_to_done.py` re-pins the step-3 brief digest; `python scripts/vendor_shared.py --check` exits 0 (all vendored copies match); `uv run --locked pytest -q` passed 3808 tests at the target; mutation checks recorded in PR #369, each mutant failed the named test. |
| AC5: review of record on the final head, guard commands run by hand | Verified | PR #369 review of record at `15a77d2d6a93fc5863c5995c56557e767c9d4a15` by `noahwhite` (`pullrequestreview-5982944934`, first line `Review of record 15a77d2...`), commit_id equals the head. Hand-run: `profile.review.record_author` unset so `gh api user` yielded `noahwhite`; one marker review, kept; `commit_id` and first-line SHA matched `headRefOid`; merged with `sha` pinned. |
| DoD: root cause identified | Verified | Prior selection accepted the latest `Review of record` from any author; the story pins the expected author. |
| DoD: fix verified against the original failing case | Verified | The hand-run on PR #369 exercised the amended rule end to end; the adjudicator's overturn (leak scan on literal logins) was confirmed real in CI and fixed before merge. |
| DoD: regression protection added | Verified | The pinned sentences in `test_merge_guard.py` / `test_story_to_done.py` and the new `test_record_author.py` schema tests. |
| DoD: independently reviewed per Review Policy | Verified | Reviewer Codex (`gpt-6.1-terra`), adjudicator DeepSeek Flash; one overturn round resolved, APPROVE confirmed on the final head before merge. |
| DoD: docs/comments updated | Verified | The guard step 2 prose, both read-backs, the schema description and the example comment. |
| DoD: no new regressions | Verified | 3808 tests pass at the target; CI green on head `15a77d2` and on the merged commit. |

Pending owner rulings (recorded on PR #369, no action taken): schema `maxLength` 45 and the pinned prose admit logins GitHub cannot take; `gh api --paginate` emits one array per page with no merge command; the read-back report omits excluded reviews' `commit_id`; a PR editing its own `profile.yaml` can redefine `record_author` for itself.

Closing decision: Done, once this evidence is merged.
