# SKL-335 QA evidence

## QA round 1

Date: 2026-11-19 UTC, independent QA round 1.
Path: `no-deployment`, from the brief's recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `5c3c388682bcf3c15e903ec580bf70e674824bfc` on `main`, the merge of PR #354 at head `3c6f8a8a1f9f55f942e8e71c1540cc7b4f9c4b98`, which `git merge-base --is-ancestor` confirmed on `origin/main`.
Fixtures: none; QA changed no repository setting and ran the judge only on local copies of the workflows.
The raw output is attached to SKL-335 as "SKL-335 QA round 1 assertion output"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: mechanism and files read | Verified | The refinement note (SKL-335, comment `af0bf27e`) names `.github/workflows/ci.yml`, `tests/test_smoke_opencode.py` and the ruleset 26798896 JSON, and records D1 to D6. |
| AC2: gate-integrity check | Verified | The merged judge, run over copies of the real workflows, exits 1 for a removed step, `if: false`, `continue-on-error: true`, a removed `push` trigger, a removed `gate-base.yml` and a changed head judge script, and exits 0 for an appended `run` step and an added job. `tests/test_gate_integrity.py` passes (164 tests) and holds every case the AC names. |
| AC3: workflow | Verified | `gate-base.yml` triggers only on `pull_request_target` with no `paths` filter, has `contents: read` and `checks: write`, one job `gate` with no `name`, SHA-pinned checkouts without persisted credentials, no cache, no `secrets.`, and posts the `gate-base` check run on the PR head SHA. The nine workflow tests pass. |
| AC4: boundary and no skill change | Failed | The diff lists only `gate-base.yml`, `scripts/gate_integrity.py`, `tests/test_gate_integrity.py` and `README.md`, so the size guard is not triggered. The PR body, reviews and commits do not say so. |
| AC5: README | Verified | The new README section states that workflow files are judged by the base copy, the D6 procedure, that merges are signed merge commits, and that there is no bypass. |
| AC6: guards | Verified | On the PR head, run 44489520934 concluded `success` for `checks` (pytest, leak scan, `skills-ref validate`) and `discovery` (`smoke-opencode.sh`). The local `scripts/leak_scan.py --require-private` exits 2 `INCOMPLETE`, which the AC excludes. The local full suite was not run: owner directive, full suite deferred to the end. |
| DoD: all acceptance criteria met | Failed | AC4. |
| DoD: tests written and passing | Verified | 164 tests pass locally; the head's `Repository tests` step is green. |
| DoD: independently reviewed | Verified | The latest review of record covers `3c6f8a8a1f9f55f942e8e71c1540cc7b4f9c4b98`, the merged head, with no findings. |
| DoD: docs updated | Verified | The README section in AC5. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | None found. |

Pending owner rulings: none.

Incidental: the PR #354 body is stale against its merged head; it reports 99 passing tests and lists as not fixed items that later commits in the PR fixed.

Closing decision: In Progress, for the AC4 statement on the PR.

## QA round 2

Date: 2026-11-19 UTC, independent QA round 2.
Path: `no-deployment`, from the brief's recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: the same merged commit `5c3c388682bcf3c15e903ec580bf70e674824bfc` on `main` (PR #354, head `3c6f8a8a1f9f55f942e8e71c1540cc7b4f9c4b98`), which `git merge-base --is-ancestor` confirmed on `origin/main`.
Fixtures: none; QA changed no repository setting.
The raw output is attached to SKL-335 as "SKL-335 QA round 2 assertion output"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: mechanism and files read | Verified | The refinement note (SKL-335, comment `af0bf27e`) names `.github/workflows/ci.yml`, `tests/test_smoke_opencode.py` and the ruleset 26798896 JSON, and records D1 to D6. |
| AC2: gate-integrity check | Verified | `tests/test_gate_integrity.py` passes at the target (164 tests) and holds every non-zero and zero case the AC names. |
| AC3: workflow | Verified | `gate-base.yml` at the target triggers only on `pull_request_target` with no `paths` filter, has `contents: read` and `checks: write`, one job `gate` with no `name`, SHA-pinned checkouts without persisted credentials, no cache and no `secrets.`, and posts the `gate-base` check run on the PR head SHA; its workflow tests pass. |
| AC4: boundary and no skill change | Verified | The merge diff lists only `gate-base.yml`, `scripts/gate_integrity.py`, `tests/test_gate_integrity.py` and `README.md`, so no skill text changed and the size guard is not triggered. PR #354 comment 7004918996 states that the epic's 4.0% size guard is not triggered. |
| AC5: README | Verified | The README section states that workflow files are judged by the base copy, the D6 procedure, that merges are signed merge commits, and that there is no bypass. |
| AC6: guards | Verified | On the PR head, run 44489520934 concluded `success` for `checks` (pytest, leak scan, `skills-ref validate`) and `discovery` (`smoke-opencode.sh`). The local `scripts/leak_scan.py --require-private` exits 2 `INCOMPLETE`, which the AC excludes. The local full suite was not run: owner directive, full suite deferred to the end. |
| DoD: all acceptance criteria met | Verified | AC1 to AC6. |
| DoD: tests written and passing | Verified | 164 tests pass locally; the head's `Repository tests` step is green. |
| DoD: independently reviewed | Verified | The latest review of record covers `3c6f8a8a1f9f55f942e8e71c1540cc7b4f9c4b98`, the merged head. |
| DoD: docs updated | Verified | The README section in AC5. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | None found. |

Pending owner rulings: none.

Closing decision: Done, once this evidence merges.
