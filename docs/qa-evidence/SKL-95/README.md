# SKL-95 QA evidence, round 1, 2026-10-28

The repository deploys nothing and the profile lists no environment, so the deployment surface is `main` and there is no visual surface.
The verified build is `90be48f92a93b4ac7cd2f1be4a6bc878b6c7653c`, the squash merge of [PR #73](https://github.com/noahwhite/agent-skills/pull/73).
Its head `f78452e70fe498ae99d326ed1e5586bab6ff3396` has the same tree as that build and carries the final review of record.
Verification used a clean clone of `main` and a detached checkout of that head.
The fixtures are the disposable issues SKL-110 (the engineer's run) and SKL-111 (the QA run), both read back as Canceled.
[`raw-output.txt`](raw-output.txt) holds the sanitized raw output behind every row: the test suite, the vendor check, the diff scope, CI, the reviews of record, the QA run's commands, timestamps and closing report, and the fixture read-backs.

| Item | Verdict | Evidence |
|---|---|---|
| C1 closing report | Verified | The Metrics section timestamps the start when the switch resolves, records a timed row with usage per coordinator command, gives the summary in the `references/metrics.md` template in the closing report of every end state, reads `no launches` only without any launch, and states no tracker write and no secrets or paths. The QA run exercised it. |
| C2 docs | Verified | The README row adds "with the run summary given in the closing report", and PR #73 changes no file under `shared/` and no vendored reference. |
| C3 tests | Verified | Eight new text-contract tests pin each C1 phrase, the PR body records a deletion mutant per phrase with the named failing tests, the orchestrator-state guard and scratch-directory tests are unchanged and pass, `uv run --locked pytest -q` passes 669 tests, the vendor check exits 0, and CI is green on the PR head (run 40730452808) and on `main` (run 40731383320). |
| C4 verified end to end | Verified | QA ran `story-to-done SKL-111 metrics=on` with a clean coordinator loading the skill from `f78452e`. It stopped at step 1 before any role, and its closing report has the heading line, four command rows in launch order each timed before and after (matching the four shell commands in its transcript), the elapsed wall-clock from the start timestamp, the totals block, and the `metrics: on` line, with no path or secret and no tracker write. The engineer's SKL-110 run is recorded on the story (tracker comment `70440152`). |
| DoD all acceptance criteria met | Verified | C1 to C4 above. |
| DoD tests written and passing | Verified | The C3 row. |
| DoD independently reviewed | Verified | Reviews of record at `0233d6e`, `93a4cfb`, `e603b74`, and `f78452e` (review 5686526750, the merged head), each a Codex GPT-6 Sol review with a DeepSeek V4 Pro adjudication, were posted before the merge. |
| DoD docs updated | Verified | The C2 row. |
| DoD verified in staging | Not applicable | No environment exists; C4 stands in, as the story states. |
| DoD no critical bugs or regressions | Verified | The suite and CI pass at `main`. |

## Incidental findings

In the engineer's SKL-110 run, one of four command rows has `not reported` as its duration because the coordinator did not time that command.
The skill text requires every command row to be timed, and the QA run timed all four, so this is run-to-run adherence variance and not an acceptance criterion failure.
The engineer's proposal in tracker comment `1115a862` to add "the `story-to-done` extras are added by SKL-96" to C1 is open for the product owner.
