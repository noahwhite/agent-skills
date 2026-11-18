# SKL-366 QA evidence

## QA round 1

Date: 2026-11-18 UTC, independent QA round 1.
Path: `no-deployment`, from the recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `4e1c67f836f641134a896c92de9e784ef3cfbcc5` on `main`, the squash of PR #347 head `cd12783313760265b6253cfe74624a2bb14a5fb5`; both commits have tree `80b796343661f6bbf2e9f1aef1b46974c87e18f6`, confirmed an ancestor of `origin/main`.
Fixtures: detached worktrees at the target and at the base `bf288ae3891fd4495ec0768bcf911bf8dd459c7e`, the PR #347 description, its review of record, and CI run 44334921047.
The node-id lists were produced at each revision by `uv run --locked pytest --collect-only -q -p no:cacheprovider | sed '/tests collected/d' | LC_ALL=C sort > <revision>-nodeids.txt`.
There is no visual surface, so no screenshot applies; the collection node ids were captured to sorted lists and compared with `comm`, as the AC Collection row records.

| Item | Verdict | Evidence |
|---|---|---|
| AC Delete: 19 node ids gone | Verified | None of the 19 ids is collected at the target, and `git diff bf288ae...4e1c67f` removes each function. |
| AC Merge: 4 node ids gone, vendoring test kept | Verified | None of the 4 ids is collected at the target; `test_resolve_model_role.py::test_the_repository_vendoring_is_current` is collected; `git diff bf288ae...4e1c67f -- tests/test_resolve_model_role.py` is empty. |
| AC Nothing else | Verified | `git diff --name-only bf288ae...4e1c67f` lists 12 paths all under `tests/`; the diff is 146 deletions and 0 insertions; 23 test functions removed plus 5 `MANIFEST`, 4 `import sys`, 2 `import subprocess`, each named in the PR description with its removed user; no fixture, `conftest.py` or test file removed. |
| AC Still current | Verified | Base `bf288ae` is the merge base; the PR description carries a 24-row table; each of the 24 functions is AST-identical between `4d2070d` and `bf288ae` (all unchanged, so no retention). |
| AC Collection | Verified | Collection exits 0 at both: base `3327 tests collected`, head `3304 tests collected`. `LC_ALL=C comm -23 base-nodeids.txt head-nodeids.txt` prints exactly the 23 removed node ids, and `LC_ALL=C comm -13 base-nodeids.txt head-nodeids.txt` prints nothing. |
| AC CI | Verified | Run 44334921047 on head `cd12783313760265b6253cfe74624a2bb14a5fb5` has `checks` and `discovery` both `success`; those jobs run the suite, the leak scan with its private half, `skills-ref validate` for each skill and `scripts/smoke-opencode.sh`. |
| AC Boundary | Verified | No added or removed diff line names any of the 13 Follow-up 3 ids; `git diff --name-only` lists no path under `skills/story-to-done/evals/`. |
| DoD: all acceptance criteria met | Verified | All seven ACs are verified. |
| DoD: unit/integration tests written and passing | Verified | The change adds no test; the existing suite (3304 tests) passes in CI run 44334921047. |
| DoD: independently reviewed | Verified | PR #347 has a `Review of record cd12783313760265b6253cfe74624a2bb14a5fb5` PR review by GPT-6.2 Sol, adjudicated by DeepSeek V4.1 Flash, verdict "merge not blocked", posted before merge. |
| DoD: docs updated | Correct by design | Test removal only; no docs apply. |
| DoD: verified in a deployed environment | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | The diff is deletion-only and CI is green. |

Pending owner rulings: none.

Closing decision: Done, once this evidence is merged.
