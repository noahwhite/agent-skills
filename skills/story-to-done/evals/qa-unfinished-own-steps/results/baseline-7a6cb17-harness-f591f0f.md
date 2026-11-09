# Superseded baseline run: 7a6cb17, harness at `f591f0f`

Kept as history, not as current evidence. Its own-steps fixture mixed an item with a stated
blocker and one with none in one handback, but the case now holds one rule per scenario and grades
exactly one role call in each, so these calls no longer re-grade to the verdicts below;
`baseline-7a6cb17-harness-1f24df1.md` is the current baseline record.

# Baseline run: 7a6cb17, harness at `f591f0f`

The skill as committed on the integration branch before this case, read from a detached
checkout of `7a6cb17`, run and graded with the case harness as committed at `f591f0f`: its scenarios
list each subagent's checklist file and the `qa-runtime read` command, and its grader requires,
before the run's first role call, a read of the checklist file of the handback the run acts on.
It replaces `baseline-7a6cb17-harness-4a622c1.md`, whose new-round run was graded on QA round 1's checklist.

- Configuration: `opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro`, default agent,
  through a wrapper set as `EVAL_AGENT_CMD` that adds run.sh's default message
  (`Follow the instructions in the attached file exactly.`), since that argument is quoted.
- Launcher: `run.sh` as committed at `f591f0f`, its checkout argument the `7a6cb17` checkout.
- Runs: 2026-11-09, one run directory per run outside both checkouts.
- Graded on: session identity, the calls `qa-runtime` recorded, and the checklist read before the
  first role call, never on prose.
- The calls and grades behind every line below are in `baseline-7a6cb17-harness-f591f0f-calls.jsonl`:
  each line holds one record of a run's `actions.jsonl`, unchanged, under `call`, or the last line
  of its `grader-output.txt` under `grade`, with the run's name under `run`.

## own-steps: 0 of 3 runs pass

| Run | Calls recorded | Graded verdict | Why it fails the case |
|---|---|---|---|
| 1 | checklist read, then `stop`, reason naming the two items as QA's and a resume at step 3 once cleared | FAIL | the round is continued, so a stop is the wrong call |
| 2 | checklist read, then `stop`, the same reason | FAIL | the same stop |
| 3 | checklist read, then `resume qa-round-1-session` with a message restating both items and the merge rules | FAIL | the continuation carries the handback's remainder and the merge rules |

Every run read the checklist, because the scenario names it and the read command; two then did
what the baseline text prescribes (step 4 meets In Deployment Review, so it reports the remainder
and stops), and the third continued with a message that restates the round's substance.

## Controls

| Scenario | Calls recorded | Verdict |
|---|---|---|
| owner-action | checklist read, then `stop`, reason naming the evidence PR gate and the maintainer approval | PASS |
| new-round | QA round 1's and the senior engineer's checklist reads, then `launch`, `qa-round-2-session`, round 2 | PASS |

Both controls pass on the baseline, so `own-steps` stays the discriminating scenario.
