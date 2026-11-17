# SKL-289 QA evidence

## QA round 1

Date: 2026-11-17 UTC, independent QA round 1.
Target: `main` at `2536932845a96474ab09a87bb56eed7ec89f4827`, the squash merge of PR 310, whose reviewed head is `55b4ad010da5ef060c10d6488f1e27269a6b99f8`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`, and `git diff --stat` between the reviewed head and the target is empty.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Pre-fix comparison: the target's parent `962e0a71d118f3f7001d3a9063fc6b11787be8b4`.
Fixtures: two fresh clones of `main`, one at the target and one at the parent; every change was made in those throwaway clones, and no probe started an eval attempt.
The raw output is attached to SKL-289 as "QA round 1: AC1-AC6 probe, regression runs, four guards, CI and review of record (raw output)"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: the repro names `README.md`, never `EADME.md`, exits 2 without a run, and the output is on the PR | Verified | With `README.md` emptied (` M README.md`), `run-suite.sh <clone> repro3` prints `(README.md)` and exits 2 with no `repro3` record at the target; the parent prints `(EADME.md)`. The PR 310 body holds the before and after output. |
| AC2: a staged modification, an unstaged modification, an untracked file and a staged rename are each named whole as the first entry | Verified | At the target `M  README.md`, ` M LICENSE`, `?? AAA-untracked.txt` and `R  README.md -> README-renamed.md` are named `README.md`, `LICENSE`, `AAA-untracked.txt` and `README.md -> README-renamed.md`, each with exit 2; the parent names ` M LICENSE` as `ICENSE`. |
| AC3: allowed records stay allowed, a tracked record with an unstaged change first proceeds, and with ` M README.md` the run refuses naming `README.md` | Verified | At the target an untracked record and a tracked record with an unstaged change pass `commit_of` and reach the later `EVAL_TIMEOUT` check, as a clean checkout does; the parent refuses the tracked record as `kills/...`. The record with an emptied `README.md` exits 2 naming `README.md`. |
| AC4: every other `git()` caller keeps its behaviour, and the two existing tests pass unmodified | Verified | `git()` keeps `strip=True` as its default, so the three `rev-parse` callers are unchanged; an AST comparison shows `test_a_checkout_with_changes_is_refused` and `test_uncommitted_records_do_not_block_a_later_run` identical between parent and target, and both pass at the target. |
| AC5: a regression test covers the cases, fails before the fix and passes after it | Verified | The target's `tests/test_eval_suite.py` against the parent's `suite.py` gives 13 failed and 286 passed, including both unstaged `README.md` cases, the tracked-record case and the record-with-`README.md` case; at the target the full suite passes. |
| AC6: all four guards pass at the final head, with no dependency or lockfile change | Verified | At the target `uv run --locked pytest -q` passes 2977, `leak_scan.py` exits 0, the pinned `skills-ref validate` reports 18 of 18 valid, and `smoke-opencode.sh` discovers all 18 skills in 6 layouts. CI run 44001690928 on the reviewed head, private leak scan included, succeeded. Only `suite.py`, its README and `tests/test_eval_suite.py` changed. |
| DoD: root cause identified | Verified | Stripping the porcelain output removed the first line's blank index column before the fixed `[3:]` cut; the fix reads that output unstripped. |
| DoD: fix verified against the original failing case, with evidence linked | Verified | AC1. |
| DoD: regression protection added | Verified | AC5. |
| DoD: independently reviewed per Review Policy | Verified | PR 310 carries reviews of record at `6c6f611`, `8df3c40`, `54175dc` and `55b4ad0`, the last clean at the reviewed head, by the reviewer and adjudicator the profile on `main` names. |
| DoD: docs and comments updated | Verified | The evals README states the allowed record states and the committed-record rule, and `suite.py` comments the unstripped read. |
| DoD: no new regressions | Verified | The full suite passes at the target, and AC3 and AC4 exercise the adjacent paths. |
| DoD: guard output at the final head and the pre-fix failing run linked | Verified | The `55b4ad0` review of record states the four guard results, and the PR 310 body holds the pre-fix failing run. |

Closing decision: Done once this evidence merges.
