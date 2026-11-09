# Superseded candidate run: `b3b33ca`

Kept as history, not as current evidence. Its new-round run carries one grade under a grader that
tied the control to the checklist read; the grader now grades the control and `new-round-read`
apart, so these grades no longer match the current case. `candidate-1f24df1.md` is the current
candidate record.

# Candidate run: `b3b33ca`

The skill as committed at `b3b33ca`, the branch commit whose step 4 states that its classification covers only the items QA's handback names with what they wait on or who owns them, so an open item with no stated blocker or owner goes to step 0's checklist read-back resume first.
The case holds one rule per scenario: `own-steps` leaves one open item that states what it waits on, for step 4's continuation, and `read-back` leaves one open item the handback names with no blocker or owner (removing the temporary test data the round created), for step 0's read-back resume.
Each scenario is graded on exactly one role call.
It replaces `candidate-331a2a0.md`, whose read-back item (whether the change needs a release-notes entry) could be read as a pending owner decision.
A later commit on the branch adds these recorded runs and changes no line of `skills/story-to-done/SKILL.md` or `skills/story-to-done/references/metrics-protocol.md`.

- Configuration: `opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro`, default agent,
  through a wrapper set as `EVAL_AGENT_CMD` that adds run.sh's default message
  (`Follow the instructions in the attached file exactly.`), since that argument is quoted.
- Launcher: `run.sh` as committed at `b3b33ca`, run against a detached checkout of `b3b33ca`.
- Runs: 2026-11-09, one run directory per run outside the checkout.
- Graded on: session identity, the calls `qa-runtime` recorded, and the checklist read before the
  role call, never on prose.
- The calls and grades behind every line below are in `candidate-b3b33ca-calls.jsonl`: each line
  holds one record of a run's `actions.jsonl`, unchanged, under `call`, or the last line of its
  `grader-output.txt` under `grade`, with the run's name under `run`.

## own-steps: 3 of 3 runs pass

| Run | Calls recorded | Message recorded (backticks and line breaks dropped; verbatim in the calls file) |
|---|---|---|
| 1 | checklist read, then `resume qa-round-1-session`, round 1 | `Your QA round for story ABC-123 is unfinished. Continue your work in your scratch subdirectory: qa-agent-round-1` |
| 2 | checklist read, then `resume qa-round-1-session`, round 1 | `Your QA round is unfinished. Continue in your round scratch subdirectory qa-agent-round-1.` |
| 3 | checklist read, then `resume qa-round-1-session`, round 1 | `The QA round is unfinished. Continue it in your round's scratch subdirectory qa-agent-round-1.` |

## read-back: 2 of 3 runs pass

| Run | Calls recorded | Verdict |
|---|---|---|
| 1 | checklist read, then `resume qa-round-1-session`, round 1, with a step 4 continuation (`QA round 1 is unfinished. Continue the round using your scratch subdirectory: qa-agent-round-1/`) | FAIL |
| 2 | checklist read, then `resume qa-round-1-session`, round 1, with step 0's read-back message word for word | PASS |
| 3 | checklist read, then `resume qa-round-1-session`, round 1, with step 0's read-back message word for word | PASS |

Run 1 resumed the right session in the right round but treated the item as step 4 work and sent the continuation instead of the read-back message.

## Controls

| Scenario | Calls recorded | Verdict |
|---|---|---|
| owner-action | QA round 1's checklist read, then `stop`, naming the evidence PR merge and the maintainer approval as a mixed remainder | PASS |
| new-round | QA round 1's and the senior engineer's checklist reads, then `launch`, `qa-round-2-session`, round 2 | PASS |

The new round's launch brief is recorded in the calls file but not graded (`case.yaml`, `not_graded_on`).
