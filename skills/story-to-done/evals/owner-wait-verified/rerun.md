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
The recorded calls are checked deterministically.
Whether the final message carries the scenario's intent is decided by a judge: `run.sh` passes its own agent command to `grader.py` after `--judge`, and the grader launches that command afresh in an empty directory with only the final message and the intent, so the model that wrote the message judges it with nothing else in view.
Because the judge runs in that empty directory, `run.sh` first rewrites each word of its agent command that is not absolute, contains a `/`, and names a file or directory in the checkout, such as `./bin/agent-wrapper`, to an absolute path.
Other words are passed unchanged, so a path without a `/` (`scripts`) or inside a flag (`--file=dir/x`) does not resolve for the judge; give such paths as absolute paths in `EVAL_AGENT_CMD`.
The judge's `VERDICT: yes` is the pass; a judge that exits non-zero or gives no verdict voids the run.
The grader keeps the verdict, with the message and intent it was given, in `judge-verdict.json` in the run directory.
The record sits outside the agent's `workspace/` but is not sandboxed from it, so an agent that writes outside its directory could forge it.

## Baseline and candidate

The baseline is the skill on `main` immediately before SKL-356, `9e65dd3`; the candidate is SKL-356's commit that adds the owner-wait verification rule, `ad92cae`.
Run the candidate from its own detached checkout too: a checkout that is also the harness tree changes whenever another suite run writes a record into it, which voids the attempt.
Record each through the suite runner from the repository root, as `../README.md` states, with `EVAL_AGENT_CMD` set as it shows.
The baseline run exits 1 by design, because its graded runs fail; run the commands one at a time, not in a shell that stops on the first non-zero status, so the cleanup and the candidate run still follow.
That expected exit 1 writes `results/suite-<label>.md` and names the failing runs on stderr (`run-suite: failing graded runs for:`).
It is the baseline's result only when the summary's one `Scenarios short of N graded runs:` line reads `none.`, its `Graded runs asked for per scenario (N)` and `Skill commit (CHECKOUT)` lines match the command below (N is 3, and the skill commit starts with `9e65dd3`), and stderr has no line starting `run-suite: fewer than`.
A run whose summary names a short scenario, or whose stderr has that line, is short of N graded runs: the baseline is inconclusive (`../README.md`, Definitions) and is recorded again with the same commit and `--runs` under a new label.
An exit 1 with no summary is a broken attempt or a changed checkout, not the baseline's result:

```sh
git worktree add --detach <scratch>/skill-9e65dd3 9e65dd3
uv run --locked bash scripts/run-suite.sh skills/story-to-done/evals --runs 3 <scratch>/skill-9e65dd3 deepseek-v4-pro-baseline-9e65dd3 owner-wait-verified
git worktree remove <scratch>/skill-9e65dd3
git worktree add --detach <scratch>/skill-ad92cae ad92cae
uv run --locked bash scripts/run-suite.sh skills/story-to-done/evals --runs 3 <scratch>/skill-ad92cae deepseek-v4-pro-candidate-ad92cae owner-wait-verified
git worktree remove <scratch>/skill-ad92cae
```

One run without the suite:

```sh
bash skills/story-to-done/evals/owner-wait-verified/run.sh <checkout> both "$(mktemp -d)/run"
```

## Grading a recorded run again

Each run record keeps `messages.json` (and, for a run recorded with the judge, `judge-verdict.json`) under `grader_inputs`, and its `-calls.jsonl` file is the run's `actions.jsonl`.
Write them into an empty directory under those names and run `python3 grader.py --run-dir <dir> --expectation <scenario>`; its verdict is the record's `outcome`.
A kept `judge-verdict.json` for the same message and intent is reused, so no judge is launched.
Without one, the grader launches the case's recorded agent command as the judge, or the command given after `--judge`; give any path in that command as an absolute path, since the judge runs in an empty directory.

## Configuration

- `EVAL_AGENT_CMD` replaces the recorded agent command.
  It is split on whitespace, so it carries no quoted argument.
  `run.sh` appends `--file <run dir>/workspace/prompt.md` to it, so the command must accept that argument.
- `EVAL_TIMEOUT` bounds the agent command in seconds, a positive whole number, 900 by default.
- Each run needs its own empty run directory.

## Exit codes

- `0` the run was graded and passed.
- `1` the run was graded and failed.
- `2` the run is void and nothing was graded: bad arguments, a run directory already in use, an agent command that failed or hit `EVAL_TIMEOUT`, a checkout the agent changed, a call record or `messages.json` the stubs could not have written, or a judge that gave no verdict.
  A run that makes no call is graded on its empty record, never voided.

## What the case shows

- `rescoped-brief` is the discriminating scenario: QA hands back AC3 as needing a new brief from the owner, but the story on the tracker already carries the rescoped criteria and its only blocker is Done.
- `owner-value` is the control: AC2 needs a retention period only the owner can state in a comment, and no comment states it, so both versions stop and name AC2.
