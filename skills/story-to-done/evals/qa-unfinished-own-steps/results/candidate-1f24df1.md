# Candidate run: `1f24df1`

The skill as committed at `1f24df1`, the branch commit that grades the new-round control on session identity alone and grades the same run again as `new-round-read` with the engineer checklist read.
Between `b3b33ca` and `1f24df1` no line of `skills/story-to-done/SKILL.md`, the prompt or any scenario changed; `references/metrics-protocol.md` gained one gloss, read only when `metrics` is on.
It replaces `candidate-b3b33ca.md`, whose new-round run carried one grade under the earlier grader.
A later commit on the branch adds these recorded runs and changes no line of `skills/story-to-done/SKILL.md` or `skills/story-to-done/references/metrics-protocol.md`.

- Configuration: `opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro`, default agent,
  through a wrapper set as `EVAL_AGENT_CMD` that adds run.sh's default message
  (`Follow the instructions in the attached file exactly.`), since that argument is quoted.
- Launcher: `run.sh` as committed at `1f24df1`, run against a detached checkout of `1f24df1`.
- Runs: 2026-11-09, one run directory per run outside the checkout.
- Graded on: session identity, the calls `qa-runtime` recorded, and the checklist read before the
  role call, never on prose.
- The calls and grades behind every line below are in `candidate-1f24df1-calls.jsonl`: each line
  holds one record of a run's `actions.jsonl`, unchanged, under `call`, or the last line of a
  grader output file under `grade` with the expectation it was graded on, with the run's name under `run`.

## own-steps: 3 of 3 runs pass

| Run | Calls recorded | Message recorded (backticks and line breaks dropped; verbatim in the calls file) |
|---|---|---|
| 1 | checklist read, then `resume qa-round-1-session`, round 1 | `The QA round is not finished. Continue it. Your round's scratch subdirectory is qa-agent-round-1.` |
| 2 | checklist read, then `resume qa-round-1-session`, round 1 | `The QA verification round is unfinished. Continue it in your scratch subdirectory qa-agent-round-1.` |
| 3 | checklist read, then `resume qa-round-1-session`, round 1 | `The QA round is unfinished. Continue it in your scratch subdirectory qa-agent-round-1.` |

## read-back: 0 of 3 runs pass

| Run | Calls recorded | Verdict |
|---|---|---|
| 1 | checklist read, then `resume qa-round-1-session`, round 1, with a step 4 continuation (`QA round 1 is unfinished. Continue your work in the scratch subdirectory qa-agent-round-1.`) | FAIL |
| 2 | checklist read, then `resume qa-round-1-session`, round 1, with a step 4 continuation (`Your QA round is unfinished. Continue with the remaining work in your scratch subdirectory qa-agent-round-1.`) | FAIL |
| 3 | checklist read, then `resume qa-round-1-session`, round 1, with a step 4 continuation (`The QA round is unfinished. The round's scratch subdirectory is qa-agent-round-1.`) | FAIL |

Every run resumed the right session in the right round but treated the item as step 4 work and sent the continuation instead of step 0's read-back message.

## Controls

| Scenario | Expectation | Calls recorded | Verdict |
|---|---|---|---|
| owner-action | owner-action | QA round 1's checklist read, then `stop`, naming the evidence PR merge and the maintainer approval as a mixed remainder | PASS |
| new-round | new-round | the senior engineer's checklist read, then `launch`, `qa-round-2-session`, round 2 | PASS |
| new-round | new-round-read | the same run, with the senior engineer's checklist read before the launch | PASS |

The new round's launch brief is recorded in the calls file but not graded (`case.yaml`, `not_graded_on`).
