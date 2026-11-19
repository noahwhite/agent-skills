# SKL-338 QA evidence

## QA round 1

Date: 2026-11-19 UTC, independent QA round 1.
Path: `no-deployment`, selected by `select-path.py`, so no environment or build SHA applies.
Target: merged commit `9d1ad1650f40b78c0538110e264c5565159406bd` (PR #366, reviewed head `67659ca15b2eda497d089cf146eccfd670efbefc`) on `main`.
`git merge-base --is-ancestor 9d1ad1650f40b78c0538110e264c5565159406bd origin/main` exits 0.
The repository has no `develop` branch, so `main` is the integration branch, as the repository profile states.
Fixtures: none; every item is a repository or tracker fact read at the target commit.
The raw output is attached to SKL-338 as "SKL-338 QA round 1 raw assertion output"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: refinement note | Verified | Story comment 99f1918f names the ten files, D1 to D13, the grep result and the install path. `git grep -n run-suite 5c3c388 -- 'skills/*/SKILL.md' 'skills/*/references/'` exits 1 with no output, as the note records. `README.md:64` holds the `ln -s` install, and `skills.json` has no evals entry. |
| AC2: workflow skills enumerated, remainder split | Verified | The story description lists the eight D1 skills and names SKL-348 for engineering-workflow. `linear issue relation list SKL-338` shows SKL-338 blocks SKL-348, SKL-349, SKL-350, SKL-351, SKL-352 and SKL-353. |
| AC3: shared runner | Verified | The runner exists only as `scripts/run-suite.sh` and `scripts/eval_suite.py`. `uv run --locked bash scripts/run-suite.sh skills/story-to-done/evals --list` prints `owner-wait-verified`, `pending-ruling-not-sent-to-engineer` and `qa-unfinished-own-steps` and exits 0. `test_a_failing_case_exits_non_zero_and_still_writes_its_summary` passes. |
| AC4: contract test generalised | Verified | `uv run --locked pytest -q tests/test_eval_suite.py` reports 362 passed. The test discovers cases with the glob `skills/*/evals/*/case.yaml`, and `test_a_case_of_any_skill_missing_its_grader_fails_the_contract` passes. |
| AC5: out of CI | Verified | `git grep -n -e EVAL_AGENT_CMD -e EVAL_PASS_ENV -e run-suite -e suite.py 9d1ad16 -- .github/workflows/` exits 1 with no output. `git diff --stat 55a26066...67659ca -- .github/workflows/` prints nothing. |
| AC6: boundary | Verified | `git diff --name-only 55a26066...67659ca` lists ten paths, all under `scripts/`, `skills/story-to-done/evals/` and `tests/`, plus `README.md`, which names the runner at line 236. |
| AC7: size guard | Verified | No skill text cites the runner and the diff changes no `SKILL.md` or `references/` file, so there is nothing to measure. |
| AC8: guards | Verified | CI `checks` on `67659ca` passed: `uv run --locked pytest -q` reported 3765 passed, the leak scan ran with `--require-private`, and all 18 skills validated. CI `discovery` passed, with smoke-opencode finding all 18 skills. The local full suite was not run, by owner directive; it is deferred to the end. |
| DoD: all acceptance criteria met | Verified | AC1 to AC8 above. |
| DoD: unit/integration tests written and passing | Verified | The new AC3 and AC4 tests pass: 362 locally and 3765 in CI. |
| DoD: independently reviewed | Verified | PR #366 review 5980784792 is the review of record on `67659ca`, with 15 findings, 13 valid, 0 blocking, and a verdict for each. |
| DoD: docs updated | Verified | `README.md:236`, `skills/story-to-done/evals/README.md` and `owner-wait-verified/rerun.md` cite `scripts/run-suite.sh`. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | One non-critical regression: `spikes/SKL-317/poc/provider.py:63` still names the old runner path. It lies outside the AC6 boundary and is tracked as SKL-376. |

Pending owner rulings: none.

Closing decision: Done, once this evidence merges.
