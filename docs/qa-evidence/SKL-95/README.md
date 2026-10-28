# SKL-95 QA evidence, round 1, 2026-10-28

The repository deploys nothing and the profile lists no environment, so the deployment surface is `main` and there is no visual surface.
The verified build is `90be48f92a93b4ac7cd2f1be4a6bc878b6c7653c`, the squash merge of [PR #73](https://github.com/noahwhite/agent-skills/pull/73).
Its head `f78452e70fe498ae99d326ed1e5586bab6ff3396` has the same tree as that build and carries the final review of record.
Verification used a clean clone of `main` and a detached checkout of that head.
The fixtures are the disposable issues SKL-110 (the engineer's run) and SKL-111 (the QA run), both read back as Canceled.
[`raw-output.txt`](raw-output.txt) holds the sanitized raw output behind every row: the test suite, the vendor check, the diff scope, CI, the reviews of record, the QA run's commands, timestamps and closing report, the SKL-110 run's per-row timestamps and closing report, and the fixture read-backs.

Outcome: C1 and C4 are not met, so the story returns to In Progress.

| Item | Verdict | Evidence |
|---|---|---|
| C1 closing report | Not met | The Metrics section states every C1 rule, but neither real run at `f78452e` timed every command row before and after the launch. In the engineer's SKL-110 run (tracker comment `70440152`) row 3, "show story description from saved JSON", has `not reported` as its duration because the coordinator did not time that command, and `references/metrics.md` reserves `not reported` for figures the runtime does not return, while duration is measured by the coordinator. In both the SKL-110 and the QA SKL-111 runs, row 1, the start-timestamp command, has one timestamp repeated as start and end (see the C4 row). The QA run timed rows 2 to 4 inside each command. |
| C2 docs | Verified | The README row adds "with the run summary given in the closing report", and PR #73 changes no file under `shared/` and no vendored reference. |
| C3 tests | Verified | Eight new text-contract tests pin each C1 phrase, the PR body records a deletion mutant per phrase with the named failing tests, the orchestrator-state guard and scratch-directory tests are unchanged and pass, `uv run --locked pytest -q` passes 669 tests, the vendor check exits 0, and CI is green on the PR head (run 40730452808) and on `main` (run 40731383320). |
| C4 verified end to end | Not met | QA ran `story-to-done SKL-111 metrics=on` with a clean coordinator loading the skill from `f78452e`. It stopped at step 1 before any role, and its closing report has the heading line, four command rows in launch order matching the four shell commands in its transcript, the elapsed wall-clock from the start timestamp, the totals block, and the `metrics: on` line, with no path or secret and no tracker write. Rows 2 to 4 carry start and end timestamps taken inside each command, but row 1, the start-timestamp command, is one `date` call whose single timestamp is repeated as start and end, so its `0.000 s` is derived and that row is not timestamped before and after the launch, which C4 requires of every row. The engineer's SKL-110 run has the same row 1. C4 is re-run at the fix head. |
| DoD all acceptance criteria met | Not met | C1 and C4 above. |
| DoD tests written and passing | Verified | The C3 row. |
| DoD independently reviewed | Verified | Reviews of record at `0233d6e`, `93a4cfb`, `e603b74`, and `f78452e` (review 5686526750, the merged head), each a Codex GPT-6 Sol review with a DeepSeek V4 Pro adjudication, were posted before the merge. |
| DoD docs updated | Verified | The C2 row. |
| DoD verified in staging | Not applicable | No environment exists; C4 stands in, as the story states. |
| DoD no critical bugs or regressions | Verified | The suite and CI pass at `main`. |

## Failed item for the engineer

C1: with `metrics` on, a coordinator left a command it launched untimed and reported its duration as `not reported`.
C1 and C4: in both runs the start-timestamp command's row has one timestamp, repeated as its start and end.
The skill text must make every coordinator-launched command, the start-timestamp command included, carry its own before and after timestamps reliably, and C4 is re-run at the fix head.

## Incidental findings

The engineer's proposal in tracker comment `1115a862` to add "the `story-to-done` extras are added by SKL-96" to C1 is open for the product owner.

# SKL-95 QA evidence, round 2, 2026-10-28

The verified build is `caba7b7fbc00f801cfcf3628b7f2a02ddeba8b92`, the squash merge of [PR #78](https://github.com/noahwhite/agent-skills/pull/78).
Its head `c47ae61c958c5143df219e7721469f6d22ea1f1f` has the same tree as that build and carries the final review of record (review 5689017268, posted before the merge).
Verification used a clean clone of `main` at that build.
The fixture is the disposable issue SKL-117, created Blocked and read back as Canceled after the run.
The engineer's re-run on SKL-116 at `c47ae61` (tracker comment `7d8889f1`) was also read.
[`raw-output-round-2.txt`](raw-output-round-2.txt) holds the sanitized raw output behind every row: the build and tree check, the reviews of record, the test suite, the vendor check, the mutation spot-check, CI, the QA run's tool calls, shell commands, metrics file and closing report, the template comparison, and the fixture read-backs.

Outcome: the round 1 timing defect is fixed, but C1 and C4 are not met, so the story returns to In Progress.

| Item | Verdict | Evidence |
|---|---|---|
| C1 closing report | Not met | The Metrics section states every C1 rule, and the QA run timed each of its four command rows with distinct start and end timestamps from separate `date` calls, the start row included, with no command launched before the start form. The summary is not in the template `references/metrics.md` defines: its Run totals rule labels a total `partial`, with the count of launches not reported and the count excluded as `cumulative`, whenever either count is non-zero. Four launches are `not reported` for tokens and tool calls, so each line must read `not reported [partial: 4 not reported, 0 cumulative]`. Both runs at `c47ae61` (SKL-116 and SKL-117) omit the note, while both round 1 runs had it. The QA run's Elapsed line also gives `invocation_end` as 20:18:31.469 UTC, while the recorded value is 1793218712.469115491, which is 20:18:32.469 UTC. |
| C2 docs | Verified | The README row ends "with the run summary given in the closing report", and PRs #73 and #78 change no file under `shared/` and no vendored `todo-tracking.md`. |
| C3 tests | Verified | `uv run --locked pytest -q` passes 731 tests and the vendor check exits 0. The orchestrator-state guard test and the scratch-directory tests are unchanged and pass. CI is green on the PR head (run 40760437086) and on `main` (run 40761182315). The PR #78 body records 65 mutants that each fail a test, and a QA spot-check deleting five guarded lines failed named tests each time. |
| C4 verified end to end | Not met | QA ran `story-to-done SKL-117 metrics=on` with a clean coordinator loading the skill from the clone. It stopped at step 1 before any role. Its closing report has the heading line, four rows in launch order matching the four shell commands in its transcript, an elapsed wall-clock of 36.625 s equal to the recorded `invocation_end` minus `invocation_start`, and the `metrics: on` line, with no path or secret and no tracker write. Its totals block lacks the required `partial` note (see C1). |
| DoD all acceptance criteria met | Not met | C1 and C4 above. |
| DoD tests written and passing | Verified | The C3 row. |
| DoD independently reviewed | Verified | PR #78 has reviews of record on nine heads, each naming Codex GPT-6 Sol as reviewer and DeepSeek V4 Pro as adjudicator, as the repository profile configures (the round 3 review had no findings to adjudicate), and the last covers the merged head `c47ae61`. |
| DoD docs updated | Verified | The C2 row. |
| DoD verified in staging | Not applicable | No environment exists; C4 stands in, as the story states. |
| DoD no critical bugs or regressions | Verified | The suite and CI pass at `main`. |

## Failed items for the engineer, round 2

C1 and C4: with launches `not reported` for tokens and tool calls, the Totals lines must carry the `partial` note the template defines; both runs at `c47ae61` omit it.
C1 and C4: the Elapsed line must give the recorded `invocation_end`; the QA run gave a value one second earlier than the one it recorded.
Advisory, not a verdict driver: the Metrics sentence that the skill does not yet record the `story-to-done` extras was added by this story's PR #73, yet the two runs at `c47ae61` disagree on it (SKL-116 printed no extras lines, SKL-117 printed eight).

## Incidental findings, round 2

The QA run printed eight `story-to-done` extras lines, although the Metrics section says the skill does not yet record them; C1 says the extras are added by SKL-96, and the template has a slot for them, so this is not ruled a C1 or C4 failure (see the advisory above).
The AC clarification proposed in tracker comment `1115a862` is now in the C1 text.
