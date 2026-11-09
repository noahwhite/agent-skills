# Superseded baseline run: 7a6cb17, harness at `4a622c1`

Kept as history, not as current evidence. Its new-round run was graded on a read of QA round 1's
checklist, but a new round follows the senior engineer's fix-cycle handback, so the grader now
requires a read of the engineer's checklist there and these calls no longer re-grade to the
verdicts below; `baseline-7a6cb17-harness-f591f0f.md` is the current baseline record.

# Baseline run: 7a6cb17, harness at `4a622c1`

The skill as committed on the integration branch before this case, read from a detached
checkout of `7a6cb17`, run and graded with the case harness as committed at `4a622c1`: its prompt
names QA round 1's checklist file and the `qa-runtime read` command, and its grader requires a read
of that exact file before the run's first role call in every scenario.
It replaces `baseline-7a6cb17.md`, whose runs predate the checklist-read requirement.

- Configuration: `opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro`, default agent,
  through a wrapper set as `EVAL_AGENT_CMD` that adds run.sh's default message
  (`Follow the instructions in the attached file exactly.`), since that argument is quoted.
- Launcher: `run.sh` as committed at `4a622c1`, its checkout argument the `7a6cb17` checkout.
- Runs: 2026-11-09, one run directory per run outside both checkouts.
- Graded on: session identity and the calls `qa-runtime` recorded, never on prose.
- The calls and grades behind every line below are in `baseline-7a6cb17-harness-4a622c1-calls.jsonl`,
  copied unchanged from each run's `actions.jsonl` and the last line of its `grader-output.txt`.

## own-steps: 0 of 3 runs pass

| Run | Calls recorded | Graded verdict | Why it fails the case |
|---|---|---|---|
| 1 | checklist read, then `stop`, reason naming the two outstanding items as QA's | FAIL | the round is continued, so a stop is the wrong call |
| 2 | checklist read, then `stop`, reason naming the two items and a resume at step 3 once cleared | FAIL | the same stop |
| 3 | checklist read, then `stop`, reason naming the two items as remaining with the QA agent | FAIL | the same stop |

Every run read the checklist, because the prompt names the read command, and then did what the
baseline text prescribes: step 4 meets In Deployment Review, so it reports the remainder and stops.
The case fails that on the decision itself.

## Controls

| Scenario | Calls recorded | Verdict |
|---|---|---|
| owner-action | checklist read, then `stop`, reason naming the evidence PR gate and the maintainer approval | PASS |
| new-round | checklist read, then `launch`, `qa-round-2-session`, round 2 | PASS |

Both controls pass on the baseline, so `own-steps` stays the discriminating scenario.
