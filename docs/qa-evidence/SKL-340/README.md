# SKL-340 QA evidence

## QA round 1

Date: 2026-11-19 UTC, independent QA round 1.
Path: `no-deployment`, from the brief's recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `9c76b03ea686480c85542f883e49e161cdcde752` on `main`, the merge of PR #358 at head `ed309241bb55e261a00fdc637493649ac4549c38`, which `git merge-base --is-ancestor` confirmed on `origin/main`.
Fixtures: none; QA changed no repository setting.
The raw output is attached to SKL-340 as "SKL-340 QA round 1 assertion output"; there is no visual surface, so no screenshot applies.
The AC numbers are those of the accepted refinement record; the description's five AC lines map to AC2 to AC6.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: refinement note | Verified | The refinement record names the eleven files read, records D1 to D9, and its D3 makes the profile's `project.test_command` the preflight target. |
| AC2: linter configured | Verified | `pyproject.toml` adds `ruff>=0.17` to the dev group with `select = ["E4", "E7", "E9", "F"]` and no excludes or per-file ignores; the diff adds no `# noqa`; `uv.lock` pins ruff 0.17.5. `uv run --locked ruff check .` at the target prints `All checks passed!` and exits 0, and step `Lint` concluded `success` in run 44613384055 on the PR head. |
| AC3: in CI | Verified | `ci.yml` has one `Lint` step running `uv run --locked ruff check .` in `checks`, before `Repository tests`, with no `continue-on-error` and zero deleted lines. Draft PR #359 added only `import zipfile` to `tests/test_select_path.py`; run 44560803202 shows `checks` failed at step `Lint`. PR #359 is closed and its branch is gone. |
| AC4: in the preflight | Not run: owner directive, full suite deferred to the end | `project.test_command` is `uv run --locked ruff check . && uv run --locked pytest`, with the pytest half unfiltered. The named artifact, a preflight transcript with that full command, does not exist yet. A QA preflight at the target with the pytest half narrowed to one file printed `All checks passed!` before the pytest summary and passed. |
| AC5: fix only reports | Verified | `uvx --from ruff==0.17.5 ruff check --select E4,E7,E9,F` at base `aafe80f` reports 24 findings, and every `.py` hunk of the merge diff fixes one of them: an f-string prefix, `l` renamed `ln`, the unused local `started` removed, and the loop variable `copy` renamed `copy_path` with the import left alone. The PR body maps the same 24 findings. Its `tests/test_merge_guard.py` line numbers come from the earlier base `631b7af`. |
| AC6: boundary | Verified | `git diff --numstat aafe80f 9c76b03` lists only `pyproject.toml`, `uv.lock`, `ci.yml` (2 added, 0 deleted), `.agent-skills/profile.yaml` and the seven files with a base finding. No `SKILL.md` and no path under `skills/`, `references/` or `shared/` changed. The PR body states that the size guard is not triggered. |
| AC7: guards | Not run: owner directive, full suite deferred to the end | On the PR head, run 44613384055 concluded `success` for `checks` (pytest, leak scan with `--require-private`, `skills-ref validate`) and `discovery`. `smoke-opencode.sh` at the target found all 18 skills in all six layouts. The local `scripts/leak_scan.py --require-private` exits 2 `INCOMPLETE`, which the AC excludes. The local full suite was not run. |
| DoD: all acceptance criteria met | Open | Waits on AC4 and AC7. |
| DoD: tests written and passing | Verified | The story adds no tests by design (AC5 and AC6); the six touched test files pass locally (134 tests), and the head's `Repository tests` step is green. |
| DoD: independently reviewed | Verified | Review of record 5983271566 covers `ed309241bb55e261a00fdc637493649ac4549c38`, the merged head, and is clean. |
| DoD: docs updated | Correct by design | AC6 allows no documentation change in this story. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | None found; run 44615295586 on `main` at the target concluded `success`. |

Pending owner rulings: none.

Closing decision: In Deployment Review, until the owner's end-of-epic full-suite run covers AC4 and AC7.
