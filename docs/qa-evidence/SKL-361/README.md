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
