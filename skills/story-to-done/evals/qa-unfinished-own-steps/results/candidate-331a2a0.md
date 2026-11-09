# Superseded candidate run: `331a2a0`

Kept as history, not as current evidence. Its read-back item (whether the change needs a release-notes
entry) could be read as a pending owner decision, and its skill text let step 4's continuation claim an
open item with no stated blocker; the fixture item and step 4 have since changed, so these runs no
longer test the current case. `candidate-b3b33ca.md` is the current candidate record.

# Candidate run: `331a2a0`

The skill as committed at `331a2a0`, the branch commit whose case holds one rule per scenario: `own-steps` leaves one open item that states what it waits on, for step 4's continuation, and `read-back` leaves one open item the handback names with no blocker or owner, for step 0's checklist read-back resume.
Each scenario is graded on exactly one role call.
It replaces `candidate-f591f0f.md`, whose own-steps fixture mixed both kinds of item in one handback.
A later commit on the branch adds these recorded runs and changes no line of `skills/story-to-done/SKILL.md` or `skills/story-to-done/references/metrics-protocol.md`.

- Configuration: `opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro`, default agent,
  through a wrapper set as `EVAL_AGENT_CMD` that adds run.sh's default message
  (`Follow the instructions in the attached file exactly.`), since that argument is quoted.
- Launcher: `run.sh` as committed at `331a2a0`, run against a detached checkout of `331a2a0`.
- Runs: 2026-11-09, one run directory per run outside the checkout.
- Graded on: session identity, the calls `qa-runtime` recorded, and the checklist read before the
  role call, never on prose.
- The calls and grades behind every line below are in `candidate-331a2a0-calls.jsonl`: each line
  holds one record of a run's `actions.jsonl`, unchanged, under `call`, or the last line of its
  `grader-output.txt` under `grade`, with the run's name under `run`.

## own-steps: 3 of 3 runs pass

| Run | Calls recorded | Message recorded (backticks dropped; verbatim in the calls file) |
|---|---|---|
| 1 | checklist read, then `resume qa-round-1-session`, round 1 | `Your QA round for ABC-123 is unfinished. Continue it in your scratch subdirectory qa-agent-round-1.` |
| 2 | checklist read, then `resume qa-round-1-session`, round 1 | `The QA round is unfinished. Continue with the unfinished work in the round's scratch subdirectory qa-agent-round-1.` |
| 3 | checklist read, then `resume qa-round-1-session`, round 1 | `QA round 1 is unfinished. Continue it in your scratch subdirectory: qa-agent-round-1.` |

## read-back: 2 of 3 runs pass

| Run | Calls recorded | Verdict |
|---|---|---|
| 1 | checklist read, then `resume qa-round-1-session`, round 1, with step 0's read-back message word for word | PASS |
| 2 | checklist read, then `resume qa-round-1-session`, round 1, with step 0's read-back message word for word | PASS |
| 3 | checklist read, then `stop`, reason naming the release-notes question as the product owner's acceptance-basis decision | FAIL |

Run 3 assigned the item an owner the handback does not name, and stopped as step 4 does for an owner action.

## Controls

| Scenario | Calls recorded | Verdict |
|---|---|---|
| owner-action | QA round 1's checklist read, then `stop`, naming the QA-owned evidence PR merge and the maintainer approval as a mixed remainder | PASS |
| new-round | QA round 1's and the senior engineer's checklist reads, then `launch`, `qa-round-2-session`, round 2 | PASS |

The new round's launch brief is recorded in the calls file but not graded (`case.yaml`, `not_graded_on`).
