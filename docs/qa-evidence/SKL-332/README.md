# SKL-332 QA evidence

## QA round 1

Date: 2026-11-18 UTC, independent QA round 1.
Path: `spike`, selected by `select-path.py` with the recorded `path: spike` line, so no environment or build SHA applies.
Target: the deliverable the handoff note links, the "SKL-332 list" comment on SKL-332 (comment `113e8e24`), and its section 10, the Go/No-Go.
The deliverable is not a tracked file, so it has no commit.
The list reviews agent-skills at the pin `4d2070d456b42b818c73550dcdb1d352c19582d3` and names `origin/main` at `f627b177a24bca497dd84bdf2e15250ad21983d4`.
Fixtures: the baseline log `pytest-baseline-4d2070d.log` attached to SKL-332, and a QA-owned detached worktree at the pin, which was removed after the round.
The criteria verified are the eight refined success criteria of the accepted refinement record, which replace the five in the description.
QA executed no test, on the owner's instruction for this run.
QA ran `uv run --locked pytest --collect-only -q -p no:cacheprovider` at the pin, which executes no test and printed `3076 tests collected`.
The raw output is attached to SKL-332 as "SKL-332 QA round 1 assertions"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| SC1 (refined 1): all modules covered, pin stated | Verified | The pin is stated, and the moved `main` is named with a diff-stat that matches git's output. There is one inventory row for each of the 47 `tests/test_*.py` files, and each row's collected count equals collect-only (3076 in total). Every row has a disposition, and sampled rows give the unclassified count. The evals tree is named out of scope. |
| SC2 (refined 2): each entry has its fields | Verified | All 36 entries carry a node id, file, test, lines, one category, a one-line reason and a recommendation. Each name, line range and case count matches the pin, and each test is unchanged at `f627b17`. None of the listed tests is a prose pin. |
| SC3 (refined 3): mutation-blind entries carry the D5 record | Verified | There is no mutation-blind entry. Section 6 states 0 mutants and every test "not probed", and the list says it is a lower bound. |
| SC4 (refined 4): duplicates name the canonical test and D6 evidence | Verified | E01 to E06 each name a collected canonical node id. The cited lines of `scripts/vendor_shared.py`, the canonical assertion and the grader lines match at the pin. |
| SC5 (refined 5): totals and runtime estimate | Verified | The totals tables match the entries. The per-entry estimates were recomputed from the baseline log and match: delete 0.285 s, merge 0.200 s, total 0.485 s of 333.67 s. The 173.62 s, 230.72 s and 242.00 s figures were also reproduced. |
| Refined 6: rankings, habits, SKL-333 | Verified | Modules are ranked by count and by runtime. The habit counts add up to 36, each habit has an example, and SKL-333 is named. |
| Refined 7: one comment with table, records, commands and Go/No-Go | Verified | One comment holds every section. The three follow-up slices give their node ids and overlap no sleep, skip or prose pin. |
| Refined 8: no tracked change, no dependency, no leftover worktrees | Verified | There is no SKL-332 commit, remote branch or PR, and the spike branch is 0 commits ahead with a clean status. `pyproject.toml` and `uv.lock` are unchanged. |
| Deliverable 1: the test list on SKL-332 | Verified | Comment `113e8e24`. |
| Deliverable 2: Go names follow-up stories with slices | Verified | Section 10, follow-ups 1 to 3. |
| Deliverable 3: if No-Go, why and the alternative | Verified | No-Go for speed, with SKL-339 as the alternative. |
| DoD: success criteria validated | Verified | The rows above. |
| DoD: findings documented in Linear | Verified | Comment `113e8e24` and the handoff note. |
| DoD: Go/No-Go decision made | Verified | Section 10. |
| DoD: next steps defined | Verified | Follow-ups 1 to 3 and SKL-333. |

Pending owner rulings: none.

Closing decision: In Deployment Review until this evidence merges; the evidence PR's CI test run waits on the owner's decision.
