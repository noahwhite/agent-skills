# Baseline run: 7a6cb17, harness at `1f24df1`

The skill as committed on the integration branch before this case, read from a detached checkout of `7a6cb17`, run and graded with the case harness as committed at `1f24df1`: one rule per scenario, each graded on exactly one role call, the new-round run graded on the control and again as `new-round-read`.
It replaces `baseline-7a6cb17-harness-b3b33ca.md`, whose new-round run carried one grade under the earlier grader.

- Configuration: `opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro`, default agent,
  through a wrapper set as `EVAL_AGENT_CMD` that adds run.sh's default message
  (`Follow the instructions in the attached file exactly.`), since that argument is quoted.
- Launcher: `run.sh` as committed at `1f24df1`, its checkout argument the `7a6cb17` checkout.
- Runs: 2026-11-09, one run directory per run outside both checkouts.
- Graded on: session identity, the calls `qa-runtime` recorded, and the checklist read before the
  role call, never on prose.
- The calls and grades behind every line below are in `baseline-7a6cb17-harness-1f24df1-calls.jsonl`:
  each line holds one record of a run's `actions.jsonl`, unchanged, under `call`, or the last line
  of a grader output file under `grade` with the expectation it was graded on, with the run's name under `run`.

## own-steps: 0 of 3 runs pass

| Run | Calls recorded | Verdict |
|---|---|---|
| 1 | checklist read, then `stop`, reason naming the evidence PR as unmerged with its gate running, the QA agent owning the review and the merge | FAIL |
| 2 | checklist read, then `stop`, the same remainder, the QA agent owning the gate and the merge | FAIL |
| 3 | checklist read, then `stop`, the same remainder, owned by the QA agent, resume at step 3 once cleared | FAIL |

## read-back: 0 of 3 runs pass

| Run | Calls recorded | Verdict |
|---|---|---|
| 1 | checklist read, then `stop`, reason naming the test-data removal as outstanding, owner the QA agent | FAIL |
| 2 | checklist read, then `stop`, the same item, owner the QA agent | FAIL |
| 3 | checklist read, then `stop`, the same item, owned by the QA agent | FAIL |

## Controls

| Scenario | Expectation | Calls recorded | Verdict |
|---|---|---|---|
| owner-action | owner-action | checklist read, then `stop`, reason naming the evidence PR gate and the maintainer approval | PASS |
| new-round | new-round | QA round 1's and the senior engineer's checklist reads, then `launch`, `qa-round-2-session`, round 2 | PASS |
| new-round | new-round-read | the same run, with the senior engineer's checklist read before the launch | PASS |

The baseline has no checklist read-back rule; in this run it read both checklists before the launch, so it passed `new-round-read` too.
The `b3b33ca` baseline run read neither and would fail `new-round-read` while passing the control; the read on the baseline varies from run to run.
