# Superseded candidate run: `f591f0f`

Kept as history, not as current evidence. Its own-steps fixture mixed an item with a stated
blocker and one with none in one handback, but the case now holds one rule per scenario and grades
exactly one role call in each, so these calls no longer re-grade to the verdicts below;
`candidate-b3b33ca.md` is the current candidate record.

# Candidate run: `f591f0f`

The skill as committed at `f591f0f`, the branch commit that carries the SKL-219 checklist read-back
rule at story-to-done step 0, the `qa-runtime read` command, and the grader that requires, before
the run's first role call, a read of the checklist file of the handback the run acts on: QA round
1's for own-steps and owner-action, the senior engineer's for new-round.
It replaces `candidate-4a622c1.md`, whose new-round run was graded on QA round 1's checklist.
A later commit on the branch adds these recorded runs and changes no line of
`skills/story-to-done/SKILL.md` or `skills/story-to-done/references/metrics-protocol.md`.

- Configuration: `opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro`, default agent,
  through a wrapper set as `EVAL_AGENT_CMD` that adds run.sh's default message
  (`Follow the instructions in the attached file exactly.`), since that argument is quoted.
- Launcher: `run.sh` as committed at `f591f0f`, run against a detached checkout of `f591f0f`.
- Runs: 2026-11-09, one run directory per run outside the checkout.
- Graded on: session identity, the calls `qa-runtime` recorded, and the checklist read before the
  first role call, never on prose.
- The calls and grades behind every line below are in `candidate-f591f0f-calls.jsonl`: each line
  holds one record of a run's `actions.jsonl`, unchanged, under `call`, or the last line of its
  `grader-output.txt` under `grade`, with the run's name under `run`.

## own-steps: 3 of 3 runs pass

| Run | Calls recorded | Message recorded (backticks dropped; verbatim in the calls file) |
|---|---|---|
| 1 | `read qa-agent-round-1/qa-agent-round-1-todo.md`, then `resume qa-round-1-session`, round 1 | `Your QA round is unfinished. Continue with your remaining work in your scratch subdirectory qa-agent-round-1.` |
| 2 | `read qa-agent-round-1/qa-agent-round-1-todo.md`, then `resume qa-round-1-session`, round 1, then `read actions.jsonl` | `QA round 1 is unfinished. Continue the round; your scratch subdirectory is qa-agent-round-1.` |
| 3 | `read qa-agent-round-1/qa-agent-round-1-todo.md`, then `resume qa-round-1-session`, round 1 | `QA round 1 for story ABC-123 is not finished. Continue your work in your scratch subdirectory qa-agent-round-1.` |

Every own-steps run read round 1's checklist file before its role call, continued round 1's own
session, started no session, stayed in round 1, and passed a message within the case's
400-character bound that named the round's scratch subdirectory and carried no excluded term.
Run 2's later read of its own call record is not a role call and does not change the grade.

## Controls

| Scenario | Calls recorded | Verdict |
|---|---|---|
| owner-action | QA round 1's checklist read, then `stop`, naming the QA-owned evidence PR merge and the maintainer approval as an owner action | PASS |
| new-round | QA round 1's and the senior engineer's checklist reads, then `launch`, `qa-round-2-session`, round 2 | PASS |

The new round's launch brief is recorded in the calls file but not graded (`case.yaml`, `not_graded_on`).
