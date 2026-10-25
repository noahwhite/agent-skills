# SKL-19 QA evidence

Verified on 2026-10-25 against `noahwhite/agent-skills` `main` build `d6e5980d44eda89b7284740efb15a808442df0c1`, the squash merge of [PR #46](https://github.com/noahwhite/agent-skills/pull/46).
The repository ships no runtime deploy unit; the push-triggered [CI run 40150794535](https://github.com/noahwhite/agent-skills/actions/runs/40150794535) is the delivered build and passed `checks` and `discovery` at that exact SHA.
Fixtures were the merged commit and its parent, `shared/github.md`, the release-manager skill, schema, contract tests, 13 vendored references, PR diff, CI run, and implementation review.
The raw-assertion attachment on SKL-19 records the per-item probes; no screenshot applies to these repository and tracker surfaces.

| Item | Verdict | Evidence |
| --- | --- | --- |
| AC1: per-story construction and commit selection | Verified | `shared/github.md` Promotion gives the explicit release base, issue-key PR discovery, all three schema merge methods, patch-id check, ordered cherry-pick, release PR, and fail-closed stops. |
| AC2: review-fix flow | Verified | Promotion closes the stale PR, carries original plus fix commits on a fresh story branch, refreshes evidence, forbids back-merge/update/force-push, and qualifies the shared and skill fix rules to `whole-branch`. |
| AC3: inspection by mode | Verified | Promotion has both exact three-dot commands, retains the two-dot caveat, and forbids inspecting the whole integration branch for `per-story`. |
| AC4: release-manager skill | Verified | The skill cites the named mechanism, removes the obsolete mechanism request, keeps the unset-profile-value stop, and binds evidence to the story branch. |
| AC5: contract tests | Verified | `tests/test_shared_github.py` pins exact sentences and the whole section; the persona tests pin the updated citation; deleting one required sentence in an isolated fixture failed four tests. |
| AC6: vendors, suite, CI | Verified; count corrected by design | All 13 copies present in the build were regenerated, `uv run --locked pytest -q` passed 511 tests, the interpreter-run vendor check passed, and both CI jobs succeeded; the story's count of 12 predates the added `cleanup` skill. |
| AC7: SKL-16 scope | Verified | PR #46 changed neither `profile/schema.json` nor `profile/example.yaml` and added no `profile.release.*` key; SKL-16 is Done. |
| AC8: other modes | Verified | The old `none` and `whole-branch` rules remain, with only the named mode qualifications and new `per-story` text; the contract test pins the section. |
| DoD1: all AC met | Verified | AC1–AC8 above. |
| DoD2: tests written and passing | Verified | New shared contract tests, updated persona tests, 511 local passes, and green CI `checks`. |
| DoD3: independent review | Verified | [Review of record 5640935039](https://github.com/noahwhite/agent-skills/pull/46#pullrequestreview-5640935039) was `COMMENTED` at reviewed head `c964b58659319bbd8dd8bfe191ef1310331fd528` before merge; per its own body it records a Codex GPT-6 Sol review and a Kimi K3 adjudication. |
| DoD4: docs updated | Verified | The merged PR updated the shared guide and all 13 vendored references. |
| DoD5: staging, if needed | Correct by design | No staging or deploy unit exists for this library; the merged `main` CI build is its delivery surface. |
| DoD6: no critical regressions | Verified within tested surface | The suite, vendor check, CI jobs, and implementation review passed; no critical defect was observed. |

The vendor script is mode 0644, so direct shell execution gives permission denied; the repository's interpreter invocation, `uv run --locked python scripts/vendor_shared.py --check`, passed.
To reproduce, check out the build SHA, run the locked suite and interpreter-run vendor check, inspect the cited files and PR diff, and compare the CI run and review to the merged head.
