# SKL-345 QA evidence

## QA round 1

Date: 2026-11-19 UTC, independent QA round 1.
Path: `no-deployment`, from the brief's recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `edc0b24af9a8f59d919d8521adf66291cf19f83f` on `main`, the merge of PR #357 at head `b44be02555056e175f7c0e41581dfa32b7d26bd1`, which `git merge-base --is-ancestor` confirmed on `origin/main`.
The merged tree is identical to the reviewed head.
Fixtures: none; every QA run of the script left `git status --porcelain` empty.
The raw output is attached to SKL-345 as "SKL-345 QA round 1 assertion output"; there is no visual surface, so no screenshot applies.
The story description carries five acceptance criteria, and the accepted round 3 refinement (comment `bd7e8b47`) carries nine refined criteria; both sets are verified.

| Item | Verdict | Evidence |
|---|---|---|
| Refined AC1: refinement note | Verified | Refinement record `bd7e8b47` names the files read, records D1 to D13 and names the two unsupported claims; it precedes the move to Ready in Triage record `7668c113`. |
| Refined AC2: categories and script | Verified | `scripts/prune_candidates.py` imports only the standard library and requires `--since YYYY-MM-DD`. It prints the commit, the since-date and three counted categories with evidence and a proposal per row. `tests/test_prune_candidates.py` passes (64 tests), with one candidate and one non-candidate per category and explicit zero counts. |
| Refined AC3: read-only and shallow refusal | Verified | `test_run_writes_nothing` hashes every file and asserts an empty `git status --porcelain`. `test_shallow_clone_is_refused` asserts exit 2 with "shallow" on stderr. |
| Refined AC4: dry run | Verified | The PR body holds the full output at `b44be02` with `--since 2026-10-09`: 0 tests, 0 reference files and 0 rules. A QA re-run at the target gives the same counts. |
| Refined AC5: Retro hook and owner decides | Verified | One separate two-line Retro bullet is added and no other Retro line changes. It carries the conditional, the previous retro's date, the retire or keep proposal, the action item and the owner approval in a comment on the retro issue. Its two pins pass in `tests/test_persona_scrum_master.py` (20 tests). |
| Refined AC6: routine doc | Verified | `docs/pruning-routine.md` documents the command, the three categories, the since-date and that both signals are proxies. |
| Refined AC7: boundary | Verified | The merge diff lists only the script, two test files, one `docs/` file and the `persona-scrum-master` `SKILL.md`. The PR body makes every required statement. |
| Refined AC8: size guard | Verified | QA measured 132141 to 132490 bytes (+0.264%) for `persona-scrum-master`, as the PR body states. The PR states that the new files are outside the measured set. |
| Refined AC9: guards | Verified | On the PR head, run 44561880999 concluded `success` for `checks` (pytest, leak scan with `--require-private`, `skills-ref validate`) and `discovery` (`smoke-opencode.sh`). The local full suite was not run: owner directive, full suite deferred to the end. |
| AC: routine | Verified | Refined AC2, AC5 and AC6. |
| AC: owner decides | Verified | Refined AC3 and AC5. |
| AC: dry run | Verified | Refined AC4. |
| AC: boundary | Verified | Refined AC7; the diff deletes nothing. |
| AC: size guard | Verified | Refined AC8. |
| DoD: all acceptance criteria met | Verified | The rows above. |
| DoD: tests written and passing | Verified | 64 and 20 tests pass locally; the head's `Repository tests` step is green. |
| DoD: independently reviewed | Verified | The latest review of record covers `b44be02555056e175f7c0e41581dfa32b7d26bd1`, the merged head, with no blocking finding. |
| DoD: docs updated | Verified | `docs/pruning-routine.md` and the Retro bullet. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | None found. |

Pending owner rulings: none.

Closing decision: Done, once this evidence merges.
