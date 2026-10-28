# SKL-48 QA evidence, round 1, 2026-10-28

The repository deploys nothing and the profile lists no environment, so the deployment surface is `main` and there is no visual surface.
The verified build is `b8d08df49ac6353e2c1931659e2365d0839699b8`, the squash merge of [PR #70](https://github.com/noahwhite/agent-skills/pull/70).
Its head `72c5032c4364a4e31899853a8e8af20647cbdac4` has the same tree as that build and carries the delta review of record.
Verification used a clean detached worktree of that build.
The fixtures are the disposable issues SKL-101 to SKL-104, all read back as Canceled.
The QA comment on SKL-48 (tracker comment `958fe061`) cites the attachments behind every row: the evidence page and the sanitized raw output (test suite, vendor check, spot mutants, fixture read-back, reviews of record, and CI).

| Item | Verdict | Evidence |
|---|---|---|
| C1 switch | Verified | The Arguments table has the `metrics` row with its `off` default, the plain-word mapping, the ask-on-other-phrasing rule, resolution before step 0, the three updated prose counts, and the step 5 line. |
| C2 off is unchanged | Verified | The off-path sentence is in Arguments, the Metrics section's two sentences open on-only, and step 0 is untouched, so the sentence pinned by `tests/test_scratch_directory.py` is verbatim. |
| C3 wiring | Verified | `skills.json` appends `metrics` after `secrets` in `story-to-done` only, `scripts/vendor_shared.py` is not in the diff, `--check` exits 0, and the vendored file equals `shared/metrics.md` plus the generated header. |
| C4 docs | Verified | The README row names the switch and its `off` default, and no `todo-tracking.md` is in the diff. |
| C5 tests | Verified | `uv run --locked pytest -q` passes 661 tests, the vendor check passes, and CI is green on the PR head (run 40646795252) and on `main` (run 40647746976). |
| C6 verified end to end | Verified | Tracker comment `8020f0f4` records the SKL-103 (`metrics=on`) and SKL-104 (switch omitted) runs at `72c5032`, both stopped at step 1, with both closing reports and end states. |
| DoD all acceptance criteria met | Verified | C1 to C6 above. |
| DoD tests written and passing | Verified | `tests/test_story_to_done.py` adds nine tests and extends the required-links test; the full suite passes. |
| DoD independently reviewed | Verified | Review of record 5678888851 at `c55ad9b` and delta review 5678966998 at `72c5032`, the merged head, were posted before the merge. |
| DoD docs updated | Verified | The README row and the switch wording in the skill. |
| DoD verified in staging | Not applicable | No environment exists; C6 stands in, as the story states. |
| DoD no critical bugs or regressions | Verified | The suite and CI pass at `main`. |

## Independent checks

C3 says nothing about collection or posting, so its precedence clause does not pull those rules into this story.
The story's Constraints require that the coordinator makes no tracker write, which the Metrics section's on-path sentence keeps.
The raw todo lists of the two C6 runs open with `metrics: on` and `metrics: off`.
QA applied nine spot mutants to the skill, the README, and the vendored reference, and eight failed named tests.

## Incidental findings

Inserting the unconditional line "Record the engineer launch time in the brief." before step 2 passes every test.
The off-path scan in `test_metrics_off_changes_nothing_but_the_metrics_line` matches a fixed word list with no timing words.
No line of the skill uses `time`, `timed`, `timing`, `elapsed`, or `clock` today, so adding them to the list changes no current result.
C5's literal requirement (an exact pin per phrase and a recorded deletion mutant per phrase) is met, so this is not an acceptance criterion failure.
The engineer's proposal in tracker comment `8020f0f4` to clarify C3's precedence clause is open for the product owner.
