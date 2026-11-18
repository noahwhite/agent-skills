# SKL-361 QA evidence

## QA round 1

Date: 2026-11-18 UTC, independent QA round 1.
Path: `no-deployment`, from the recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `af5ae9994f8b57d6f698d32ff007924f4daf11bc` on `main`, the squash of PR #336 head `5e7502cba68efd7d5d7f4794a030a7f3c0243f14`; both commits have tree `0e2e208`.
Owner override for this run: QA ran no test suite, full or partial.
Fixtures: a detached worktree at the target, a stub `--test-cmd` that touches a marker file, an empty `HOME`, three literal profiles selected through `AGENT_SKILLS_PROFILE`, a scratch git repository with no profile, and literal profiles for the resolver and the schema.
The probe scripts, their raw output and `full-suite-ci-checks.json` are attached to SKL-361; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| A1: `--full-suite on\|off`, resolution when omitted, invalid value | Behaviour verified; `full-suite-switch-tests.txt` not produced | `off` and `on` exit 0. Omitted, the flag resolves `off` from the repository profile and with no profile anywhere, and `on` from a profile `default` or `teams` value. An unquoted `on` exits 2. `maybe` exits 2 with the usage text. The flag on `paths` exits 2. |
| A2: schema shape, team rule, precedence | Behaviour verified; `full-suite-switch-tests.txt` not produced | Twelve resolver cases give the stated precedence, including an `OFF` key with `teams.OFF=on`, an `SKL` key resolving `off`, a missing team falling to `default` set `on` and `off`, a profile without `full_suite`, an explicit argument overriding the profile, and a story key prefix differing from `tracker.team_key`. The schema shape matches A2 and passes `check_schema`. `teams.OFF=on` is accepted; a lowercase key and non-enum values are rejected. `pyproject.toml` and `uv.lock` are unchanged. |
| A3: `off` skips the suite, dirty tree still fails, Phase 0 passes the flag | Behaviour verified; `full-suite-switch-tests.txt` not produced | With `off` the marker is absent and the suite log holds `full-suite: off`. With `on` the marker is present. `off` on a dirty tree exits 1. The Phase 0 command in `skills/adversarial-review-pipeline/SKILL.md` passes `--full-suite`, and a guard test is scoped to that block. |
| A4: mutation proof in one pass | Structure verified by reading; `full-suite-mutation-proof.txt` not produced | `tests/test_full_suite_mutations.py` maps 20 named mutations to target tests, asserts each mutated copy fails and the pristine copy passes, and exempts exactly four tests: the three schema tests (shape, acceptance, rejection) and the dirty-tree test. CI run 44231609632 at the PR head ran it within `3323 passed`. |
| A5: every guard passes, branch not fork | Verified | `full-suite-ci-checks.json` from CI run 44231609632 has `headSha` equal to the PR head and `checks` and `discovery` `success`. Those jobs run the suite, the leak scan with its private half, `skills-ref validate` for every skill and `scripts/smoke-opencode.sh`. PR #336 is from a repository branch. `python3 scripts/vendor_shared.py --check` exits 0 at the target. |
| DoD: all acceptance criteria met | Not yet | A1 to A4 lack their attached evidence files. |
| DoD: unit/integration tests written and passing | Verified | Both new test files are in the target. CI at the PR head and the post-merge run 44232574289 on `main` are green. |
| DoD: independently reviewed | Verified | PR #336 has clean reviews of record at `518baa2` and at the merged head `5e7502c`, by the profile's reviewer and adjudicator. |
| DoD: docs updated | Verified | The skill's `SKILL.md`, `shared/README.md` and the `full_suite` schema descriptions cover the change. |
| DoD: verified in a deployed environment | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | No defect found. |

Gaps: A1 to A3 name `full-suite-switch-tests.txt` and A4 names `full-suite-mutation-proof.txt`, each produced by a `uv run --locked pytest` command and attached to the PR.
Neither file was produced, by the engineer or by QA, under the owner override.

Pending owner rulings: none.

Closing decision: stays In Deployment Review until the product owner has the two evidence files produced and attached, or amends the evidence clauses of A1 to A4.

## QA round 2

Date: 2026-11-18 UTC, independent QA round 2, after the product owner's dated amendment of 2026-11-18.
The amendment removed the pytest output files from the evidence clauses of A1 to A4; each now names the cases QA records against the merged commit, here and in the QA evidence comment, plus the green CI run on the merged commit.
Path: `no-deployment`, from the recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `af5ae9994f8b57d6f698d32ff007924f4daf11bc` on `main`, confirmed an ancestor of `origin/main`.
Owner override for this run: QA ran no test suite, full or partial; every case below is a direct run of the script or the resolver, a schema validation, or a read.
Fixtures: a detached worktree at the target, a detached worktree at the PR #336 merge base `aa0a5e891e5f3f06c46ca5740ca3fa99afa8fdd2`, fresh fixture git repositories, a stub `--test-cmd` that touches a marker file, an empty `HOME`, and six literal profiles selected through `AGENT_SKILLS_PROFILE`, committed as a repository profile, or placed as the home profile.
The probe scripts, the fixture profiles, the raw output and the CI run record are attached to SKL-361; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| A1: `--full-suite on\|off`, resolution when omitted, invalid value | Verified | `off` and `on` exit 0, with the marker absent and present. Omitted, the flag resolves `off` with no profile anywhere, `off` from a profile whose `teams` lacks the `tracker.team_key` team, and `on` from an `AGENT_SKILLS_PROFILE` default, a `teams` entry for `tracker.team_key`, a committed repository profile and a home profile. An unquoted `on` in the selected profile exits 2 without running the suite. `maybe` and `ON` exit 2 with the error and the usage text; the flag with no value and the flag on `paths` exit 2. CI run 44232574289 on the target is `success`. |
| A2: schema shape, team rule, precedence | Verified | Thirteen resolver cases give the stated order: an `OFF` key with `teams.OFF=on` resolves `on`; an `SKL` key resolves `off`; a team missing from `teams` falls to `default` set `on` and set `off`; a profile without `full_suite` resolves `off`; an explicit argument overrides the profile both ways; with no story key the team is `tracker.team_key`; a story key prefix wins over a differing `tracker.team_key`. The resolver reads only the profile, with no tracker lookup. `full_suite` is a top-level object with exactly `default` and `teams`, `additionalProperties: false` on both, `default` enum `on`/`off` with schema default `off`, and `teams` `patternProperties` `^[A-Z][A-Z0-9]*$` to `on`/`off`. Draft 2020-12 `check_schema` passes; `teams.OFF=on` is accepted; lowercase keys, non-enum values, an extra property and a key with a trailing line feed are rejected. `pyproject.toml` and `uv.lock` are unchanged, and `jsonschema` was already a dev dependency. CI run 44232574289 on the target is `success`. |
| A3: `off` skips the suite, dirty tree still fails, `on` as at the merge base, Phase 0 passes the flag | Verified | With `off` the marker is absent, the report heads section 2 "The suite (full-suite: off, not run)" and the suite log holds exactly `full-suite: off`. With `on` the marker is present. `off` on a dirty tree exits 1 with "FAIL - uncommitted changes". The target with `on` and the merge-base script give byte-identical normalised reports and the same exit codes for a passing stub (0), a failing stub (1) and an empty test command (3). The Phase 0 command in `skills/adversarial-review-pipeline/SKILL.md` passes `--full-suite "<on or off>"`, and `test_the_skill_preflight_command_passes_full_suite` is scoped to the Phase 0 section's code blocks. CI run 44232574289 on the target is `success`. |
| A4: mutation proof in one pass | Verified by reading | `tests/test_full_suite_switch.py` defines 24 tests. `tests/test_full_suite_mutations.py` names 20 mutations, one per option-behaviour test, each original text found exactly once in its source at the target. The four tests without a mutation are exactly the three schema tests and the dirty-tree test, which the file's completeness test asserts. Each mutation case copies the sources to a temporary directory, applies the mutation, asserts the target test exits 1, then asserts it exits 0 on an unmodified copy. CI run 44232574289 on the target ran both files within `3323 passed`. |
| A5: every guard passes, branch not fork | Verified | Unchanged from round 1 and re-read: CI run 44231609632 has `headSha` `5e7502cba68efd7d5d7f4794a030a7f3c0243f14`, the PR #336 head, and is `success`; the `full-suite-ci-checks.json` comment is on PR #336; the PR is from a repository branch. `python3 scripts/vendor_shared.py --check` exits 0 at the target. |
| DoD: all acceptance criteria met | Verified | A1 to A5 are verified. |
| DoD: unit/integration tests written and passing | Verified | Both new test files are in the target; CI run 44232574289 on the target reports `3323 passed`. |
| DoD: independently reviewed | Verified | PR #336 has "Review of record" PR reviews at `518baa28782c38ea0e67200259dd05c34f7486e4` and at the merged head `5e7502cba68efd7d5d7f4794a030a7f3c0243f14`, by the profile's reviewer and adjudicator, each `ADJUDICATION: clean`. |
| DoD: docs updated | Verified | `skills/adversarial-review-pipeline/SKILL.md` documents the flag, the resolver and the exit codes; `shared/README.md` lists `resolve-full-suite.py`; the `full_suite` schema descriptions cover the order and the team rule. |
| DoD: verified in a deployed environment | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | No defect found in the probes or the read; CI on the PR head and on the target are green. |

Pending owner rulings: none.

Closing decision: Done, once this evidence is merged.
