# Rerun instructions

The case is one directory: `skills/story-to-done/evals/owner-wait-verified/`.
It holds the prompt, two scenarios, a stub tracker and a stub role runtime, a grader, and `results/` for recorded runs.

## What a run does

`run.sh` copies one scenario's `scenario.md`, QA round 1's launch record, its checklist file and both stubs into the `workspace/` directory of a run directory outside the checkout, fills the prompt's two placeholders, launches the agent command from the checkout, and then grades the record.
`run.sh <checkout> both <run dir>` runs both scenarios in one invocation, each in its own subdirectory, and exits with the worse code.
The agent never reaches a real tracker, user, senior engineer or QA agent.
`tracker` serves the scenario's fixture stories from `scenarios/<name>/stories/`, read from the case's scenario directory, and records each read.
`role-runtime` records each launch, resume, read and user message, and keeps each message's text.
`grader.py` grades only that record, `actions.jsonl` in the run directory, and the message texts kept in `messages.json` beside it; the final message is the last message the run sent to the user.
The record sits outside the agent's `workspace/` but is not sandboxed from it, so an agent that writes outside its directory could forge it.

## Baseline and candidate

The baseline is the skill on `main` immediately before SKL-356, `9e65dd3`; the candidate is SKL-356's commit that adds the owner-wait verification rule, named in each candidate run record.
Record each through the suite runner from the repository root, as `../README.md` states, with `EVAL_AGENT_CMD` set as it shows:

```sh
git worktree add --detach <scratch>/skill-9e65dd3 9e65dd3
uv run --locked bash skills/story-to-done/evals/run-suite.sh --runs 3 <scratch>/skill-9e65dd3 deepseek-v4-pro-baseline-9e65dd3 owner-wait-verified
git worktree remove <scratch>/skill-9e65dd3
uv run --locked bash skills/story-to-done/evals/run-suite.sh --runs 3 <checkout> deepseek-v4-pro-candidate-<sha> owner-wait-verified
```

One run without the suite:

```sh
bash skills/story-to-done/evals/owner-wait-verified/run.sh <checkout> both "$(mktemp -d)/run"
```

## Grading a recorded run again

Each run record keeps `messages.json` under `grader_inputs`, and its `-calls.jsonl` file is the run's `actions.jsonl`.
Write both into an empty directory under those names and run `python3 grader.py --run-dir <dir> --expectation <scenario>`; its verdict is the record's `outcome`.

## Configuration

- `EVAL_AGENT_CMD` replaces the recorded agent command.
  It is split on whitespace, so it carries no quoted argument.
  `run.sh` appends `--file <run dir>/workspace/prompt.md` to it, so the command must accept that argument.
- `EVAL_TIMEOUT` bounds the agent command in seconds, a positive whole number, 900 by default.
- Each run needs its own empty run directory.

## Exit codes

- `0` the run was graded and passed.
- `1` the run was graded and failed.
- `2` the run is void and nothing was graded: bad arguments, a run directory already in use, an agent command that failed or hit `EVAL_TIMEOUT`, a checkout the agent changed, or a call record or `messages.json` the stubs could not have written.
  A run that makes no call is graded on its empty record, never voided.

## What the case shows

- `rescoped-brief` is the discriminating scenario: QA hands back AC3 as needing a new brief from the owner, but the story on the tracker already carries the rescoped criteria and its only blocker is Done.
- `owner-value` is the control: AC2 needs a retention period only the owner can state in a comment, and no comment states it, so both versions stop and name AC2.
