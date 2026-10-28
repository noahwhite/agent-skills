# SKL-44 QA evidence, round 1, 2026-10-28

The repository deploys nothing and the profile lists no environment, so the deployment surface is `main` and there is no visual surface.
The verified build is `2125bfcfc6be5836fbaf566c38266dab78d4f243`, the squash merge of [PR #66](https://github.com/noahwhite/agent-skills/pull/66), whose head `4e27489c87c637738340f070395aafdf9553cba3` carries the delta review of record.
Verification used a clean detached worktree of that build and the runtimes installed in the agent container: Claude Code 2.1.312, codex-cli 0.163.0, and opencode 1.19.3 (V1 line).
No fixture accounts apply.
The QA comment on SKL-44 (tracker comment `40a5b606`) cites the sanitized attachments behind every row: repository checks, spot mutation check, runtime re-observation, and the evidence page.

| Item | Verdict | Evidence |
|---|---|---|
| A1 shared metrics reference | Verified | `shared/metrics.md` covers every A1 clause; `tests/test_metrics.py` passes; spot mutants for `no launches` and the `partial` non-zero condition fail named tests. |
| A2 independence and posting rules | Verified | The Independence and Posting sections carry every A2 rule; spot mutants for never-sets-state, the earlier-summary exclusion, and never-named-in-a-brief fail named tests. |
| A3 registered in the shared index only | Verified | `shared/README.md` lists the file and states a listed capability may wait for a later slice; `test_no_runtime_specific_terms` passes; the one cited key, `profile.tracker.states.in_deployment_review`, is in `profile/schema.json`; `skills.json` is unchanged. |
| A4 runtime map | Verified | The usage row and the shell-launched bullet are present, the observation comment `1925915b` is on the story, the vendor check is clean, and no bundle vendors the metrics reference. |
| A5 tests | Verified | `uv run --locked pytest -q` passes 652 tests, `uv run --locked python scripts/vendor_shared.py --check` exits 0, CI is green on the PR head (run 40626826432), and the PR records 99 plus 63 mutants. |
| A6 existing texts realigned | Verified | The four texts hand each role only `<scratch>/<role>/`, put its checklist there, and read it from there; `tests/test_scratch_directory.py` pins them; `skills/story-refinement/SKILL.md` and `skills.json` are unchanged. |
| DoD all acceptance criteria met | Verified | A1 to A6 above. |
| DoD tests written and passing | Verified | `tests/test_metrics.py` and `tests/test_scratch_directory.py`; the full suite passes. |
| DoD independently reviewed | Verified | Review of record 5676845202 at `00b419f` and delta review 5677482778 at `4e27489`, the merged head, were posted before the merge. |
| DoD docs updated | Verified | `shared/README.md`, `shared/metrics.md`, and `shared/runtimes.md`. |
| DoD verified in staging | Not applicable | No environment exists; A4 and A5 stand in, as the story states. |
| DoD no critical bugs or regressions | Verified | The suite passes at `main`. |

## Independent checks

QA re-ran each A4 claim on the same versions.
A Claude Code background subagent asked to run one command returned a usage block with `subagent_tokens`, `tool_uses` 2, and `duration_ms`, and no token breakdown.
`codex exec --json` ended with `turn.completed` carrying `usage` with the five fields the bullet names, and no tool-call count or duration field.
`opencode run --format json` emitted one `step_finish` per model step with `part.tokens` and one `tool_use` per tool call, each event with a millisecond `timestamp`, and no run total or tool-call count.
OpenCode V2 is not installed, which matches the cell's `not observed`.

QA applied 13 spot mutants across `shared/metrics.md`, `shared/runtimes.md`, `shared/README.md`, `shared/todo-tracking.md`, and the three A6 skills, and each failed at least one named test.

## Incidental findings

The `main` push CI run on 2125bfc (run 40627517384) failed on `tests/test_pipeline_failfast.py::test_a_refused_checkout_cleanup_does_not_replace_the_phase_exit_code`.
That test is a pre-existing timing flake that PR #66 does not touch; it also failed on `main` at f96fcef and 786247a.
`skills/story-refinement/SKILL.md` Step 1 still hands voters the session directory, which SKL-93 owns and A6 puts out of scope.
