# Superseded candidate run: `4a622c1`

Kept as history, not as current evidence. Its new-round run was graded on a read of QA round 1's
checklist, but a new round follows the senior engineer's fix-cycle handback, so the grader now
requires a read of the engineer's checklist there and these calls no longer re-grade to the
verdicts below; `candidate-f591f0f.md` is the current candidate record.

# Candidate run: `4a622c1`

The skill as committed at `4a622c1`, the branch commit that carries the SKL-219 checklist read-back
rule at story-to-done step 0, the `qa-runtime read` command, and the grader that requires a read of
QA round 1's exact checklist file before the run's first role call in every scenario.
It replaces `candidate-ac53428.md`, whose runs predate the checklist-read requirement.
A later commit on the branch adds these recorded runs and changes no line of
`skills/story-to-done/SKILL.md` or `skills/story-to-done/references/metrics-protocol.md`.

- Configuration: `opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro`, default agent,
  through a wrapper set as `EVAL_AGENT_CMD` that adds run.sh's default message
  (`Follow the instructions in the attached file exactly.`), since that argument is quoted.
- Launcher: `run.sh` as committed at `4a622c1`, run against a detached checkout of `4a622c1`.
- Runs: 2026-11-09, one run directory per run outside the checkout.
- Graded on: session identity and the calls `qa-runtime` recorded, never on prose.
- The calls and grades behind every line below are in `candidate-4a622c1-calls.jsonl`, copied
  unchanged from each run's `actions.jsonl` and the last line of its `grader-output.txt`.

## own-steps: 3 of 3 runs pass

| Run | Calls recorded | Message recorded (backticks dropped; verbatim in the calls file) |
|---|---|---|
| 1 | `read qa-agent-round-1/qa-agent-round-1-todo.md`, then `resume qa-round-1-session`, round 1 | `QA round 1 is unfinished. Continue it in your scratch subdirectory qa-agent-round-1.` |
| 2 | `read qa-agent-round-1/qa-agent-round-1-todo.md`, then `resume qa-round-1-session`, round 1 | `Your QA round is unfinished. Continue in your scratch subdirectory qa-agent-round-1.` |
| 3 | `read qa-agent-round-1/qa-agent-round-1-todo.md`, then `resume qa-round-1-session`, round 1 | `Your QA round is unfinished. Continue with it in your scratch subdirectory qa-agent-round-1.` |

Every run read round 1's checklist file before its role call, continued round 1's own session,
started no session, stayed in round 1, and passed a message within the case's 400-character bound
that named the round's scratch subdirectory and carried no excluded term.

## Controls

| Scenario | Calls recorded | Verdict |
|---|---|---|
| owner-action | checklist read, then `stop`, naming the QA-owned evidence PR merge and the story owner's maintainer approval | PASS |
| new-round | checklist read, then `launch`, `qa-round-2-session`, round 2, a full QA brief | PASS |
