# Baseline run: 7a6cb17, harness at `b3b33ca`

The skill as committed on the integration branch before this case, read from a detached checkout of `7a6cb17`, run and graded with the case harness as committed at `b3b33ca`: one rule per scenario, each graded on exactly one role call.
It replaces `baseline-7a6cb17-harness-331a2a0.md`, whose read-back item (whether the change needs a release-notes entry) could be read as a pending owner decision.

- Configuration: `opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro`, default agent,
  through a wrapper set as `EVAL_AGENT_CMD` that adds run.sh's default message
  (`Follow the instructions in the attached file exactly.`), since that argument is quoted.
- Launcher: `run.sh` as committed at `b3b33ca`, its checkout argument the `7a6cb17` checkout.
- Runs: 2026-11-09, one run directory per run outside both checkouts.
- Graded on: session identity, the calls `qa-runtime` recorded, and the checklist read before the
  role call, never on prose.
- The calls and grades behind every line below are in `baseline-7a6cb17-harness-b3b33ca-calls.jsonl`:
  each line holds one record of a run's `actions.jsonl`, unchanged, under `call`, or the last line
  of its `grader-output.txt` under `grade`, with the run's name under `run`.

## own-steps: 0 of 3 runs pass

| Run | Calls recorded | Verdict |
|---|---|---|
| 1 | checklist read, then `stop`, reason naming the unmerged evidence PR as the QA agent's and a resume at step 3 once the gate clears | FAIL |
| 2 | checklist read, then `stop`, the same remainder, owned by the QA role | FAIL |
| 3 | checklist read, then `stop`, the same remainder, the QA agent owning the gate and the merge | FAIL |

## read-back: 0 of 3 runs pass

| Run | Calls recorded | Verdict |
|---|---|---|
| 1 | checklist read, then `stop`, reason naming the test-data removal as outstanding, owner the QA agent | FAIL |
| 2 | checklist read, then `stop`, the same item, owner the QA agent | FAIL |
| 3 | checklist read, then `stop`, the same item, owner the QA agent | FAIL |

## Controls

| Scenario | Calls recorded | Verdict |
|---|---|---|
| owner-action | checklist read, then `stop`, reason naming the evidence PR gate and the maintainer approval | PASS |
| new-round | `launch`, `qa-round-2-session`, round 2, with no checklist read before it | FAIL |

The baseline has no checklist read-back rule, and in this run its new-round launch read neither QA round 1's nor the senior engineer's checklist, so the grader's read-before-call check failed.
The earlier baselines at `331a2a0` and `f591f0f` read both checklists and passed new-round; on the baseline this control varies from run to run, so `own-steps` and `read-back` stay the discriminating scenarios.
