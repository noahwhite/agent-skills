# SKL-18 QA evidence

Verified on 2026-10-24 against fetched `origin/main` at `a30477e15a692fde158a7423caa191adfc1723e3` in an isolated worktree.
This repository has no hosted environment or deploy pipeline; `main` is the integration environment and no deploy step exists.
[Story](https://linear.app/officina-pub/issue/SKL-18/user-story-require-a-todo-list-update-after-every-step-in-every) and [QA evidence comment](https://linear.app/officina-pub/issue/SKL-18/user-story-require-a-todo-list-update-after-every-step-in-every#comment-a6c3366a) hold the tracker record.
[Implementation PR](https://github.com/noahwhite/agent-skills/pull/30) merged as the tested SHA.
Fixtures are `shared/todo-tracking.md`, `skills.json`, all 17 bundled references, `tests/test_todo_tracking.py`, and the implementation PR and CI runs.
Repository, GitHub, and Linear CLI lanes apply; there is no visual surface requiring screenshots.

| Item | Verdict | Evidence |
| --- | --- | --- |
| AC1: exact rules | Verified | Five exact sentences in rules 3/4; retired text absent; rule 4 retention text and rules 5/6 preserved against the parent. |
| AC2: bundles and seeds | Verified | All 17 copies match the source after the generated header; 11 direct manifest entries plus six transitive bundles match exactly; seed preamble present; all 11 direct skills represented by 10 seed labels, including the combined staff bullet. |
| AC3: regression and mutation evidence | Verified | Merged tests assert exact phrases, all copies, seed labels and final-report text; PR mutation (a) records 18 failures including `test_rule_three_requires_the_update_in_the_same_step` and every copy case; mutation (b) records `test_vendored_references_are_current` failing. |
| AC4: final-report rule | Verified | Exact rule 6 retained; `test_rules_five_and_six_are_unchanged` asserts both the complete rule and final-report sentence, so deletion fails. |
| AC5: suite and CI | Verified | Fresh `uv run --locked pytest -q`: 416 passed in 7.62s, exit 0; `python3 scripts/vendor_shared.py --check`: no output, exit 0; implementation-head and main CI successful. |
| DoD: all acceptance criteria | Verified | AC1 through AC5 above, with raw assertions in the tracker attachment. |
| DoD: tests written and passing | Verified | New regression module has eight plain tests and 17 copy cases; full suite passes 416 tests. |
| DoD: independently reviewed | Verified | [COMMENTED review](https://github.com/noahwhite/agent-skills/pull/30#pullrequestreview-5637576030) binds to final implementation head `d673797f80d84c7398faf20f629051f427e67504`; all 19 delivered implementation files match that head. |
| DoD: docs updated | Verified | Shared capability and all 17 generated references updated; seed bodies unchanged. |
| DoD: staging if needed | Correct by design | Tested main integration SHA; no separate staging environment or deploy step exists. |
| DoD: no critical bugs or regressions | Verified | No critical defect observed in the delivered scope; source/bundle assertions, suite, vendor check and both CI jobs pass. |

[Implementation-head CI](https://github.com/noahwhite/agent-skills/actions/runs/40078476462) covers `d673797f80d84c7398faf20f629051f427e67504`.
[Integration CI](https://github.com/noahwhite/agent-skills/actions/runs/40079319763) covers `a30477e15a692fde158a7423caa191adfc1723e3`.
Both runs passed repository tests, the public/private leak scan, validation of every skill, and discovery; the integration log names all 17 bundles valid.
The new tests and recorded mutations were inspected against their real file-reading paths; QA did not mutate the delivered source or regenerate bundles.
The only tree difference between the reviewed implementation head and tested main is unrelated `docs/qa-evidence/SKL-22/README.md`.
Incidental limitation: hypothetical future contradictory seed-body exceptions are not pinned, as recorded as Low/nonblocking in the implementation review; no such exception is delivered.
Instruction text and regression guards are verified; runtime agent compliance is outside the story's stated scope.
No required verification item is outstanding.

To reproduce, fetch `origin/main` and create an isolated checkout at the tested SHA.
Compare rules 3 through 6 and the seed preamble with the story, compare all generated references with the shared source, and inspect `tests/test_todo_tracking.py` and the implementation PR mutation section.
Run `uv run --locked pytest -q` and `python3 scripts/vendor_shared.py --check`, then inspect the linked CI runs at their recorded SHAs.
