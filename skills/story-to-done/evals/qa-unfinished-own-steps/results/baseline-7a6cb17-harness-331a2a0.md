# Superseded baseline run: 7a6cb17, harness at `331a2a0`

Kept as history, not as current evidence. Its read-back item (whether the change needs a release-notes
entry) has since been replaced, so these runs no longer test the current case;
`baseline-7a6cb17-harness-1f24df1.md` is the current baseline record.

# Baseline run: 7a6cb17, harness at `331a2a0`

The skill as committed on the integration branch before this case, read from a detached checkout of `7a6cb17`, run and graded with the case harness as committed at `331a2a0`: one rule per scenario, each graded on exactly one role call.
It replaces `baseline-7a6cb17-harness-f591f0f.md`, whose own-steps fixture mixed both kinds of item in one handback.

- Configuration: `opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro`, default agent,
  through a wrapper set as `EVAL_AGENT_CMD` that adds run.sh's default message
  (`Follow the instructions in the attached file exactly.`), since that argument is quoted.
- Launcher: `run.sh` as committed at `331a2a0`, its checkout argument the `7a6cb17` checkout.
- Runs: 2026-11-09, one run directory per run outside both checkouts.
- Graded on: session identity, the calls `qa-runtime` recorded, and the checklist read before the
  role call, never on prose.
- The calls and grades behind every line below are in `baseline-7a6cb17-harness-331a2a0-calls.jsonl`:
  each line holds one record of a run's `actions.jsonl`, unchanged, under `call`, or the last line
  of its `grader-output.txt` under `grade`, with the run's name under `run`.

## own-steps: 0 of 3 runs pass

| Run | Calls recorded | Verdict |
|---|---|---|
| 1 | checklist read, then `stop`, reason naming the unmerged evidence PR and a resume at step 3 once it merges | FAIL |
| 2 | checklist read, then `stop`, the same remainder and a fresh QA round once it merges | FAIL |
| 3 | checklist read, then `stop`, the same remainder, owner QA agent | FAIL |

## read-back: 0 of 3 runs pass

| Run | Calls recorded | Verdict |
|---|---|---|
| 1 | checklist read, then `stop`, reason calling the release-notes question a pending owner decision | FAIL |
| 2 | checklist read, then `stop`, reason naming the product owner as its owner | FAIL |
| 3 | checklist read, then `stop`, reason calling it a pending owner decision | FAIL |

## Controls

| Scenario | Calls recorded | Verdict |
|---|---|---|
| owner-action | checklist read, then `stop`, reason naming the evidence PR gate and the maintainer approval | PASS |
| new-round | QA round 1's and the senior engineer's checklist reads, then `launch`, `qa-round-2-session`, round 2 | PASS |

Both controls pass on the baseline, so `own-steps` and `read-back` stay the discriminating scenarios.
