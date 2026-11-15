# Rerun instructions

The case is one directory: `skills/story-to-done/evals/pending-ruling-not-sent-to-engineer/`.
It holds the prompt, two scenarios, a stub runtime, a grader and its fixtures, and `results/` for recorded runs.

## What a run does

`run.sh` copies one scenario's files, its checklist files and the stub `story-runtime` into a run directory outside the checkout, fills the prompt's two placeholders, launches the agent command from the checkout, and then grades the record.
The agent never reaches a real user, senior engineer or QA agent: `story-runtime` records each message and read the agent makes, and serves the next handback the scenario's `rounds.json` lists for each launch.
`grader.py` grades only that record, `actions.jsonl`, and the message texts kept in `messages.json`, never the agent's prose.

## Baseline

The baseline is the skill as committed on `main` before SKL-296, `9bd3e16`.
Run each snippet from the repository root; `EVAL_AGENT_CMD` (see Configuration) replaces the agent command.

```sh
scratch="$(mktemp -d)"
git -C <checkout> worktree add --detach "$scratch/baseline-9bd3e16" 9bd3e16
bash skills/story-to-done/evals/pending-ruling-not-sent-to-engineer/run.sh \
  "$scratch/baseline-9bd3e16" split-verdict "$scratch/runs/baseline-split-verdict"
git -C <checkout> worktree remove "$scratch/baseline-9bd3e16"
```

## Candidate

The candidate is SKL-296's merge commit, `6838b35`, or a later checkout that carries this case.

```sh
scratch="$(mktemp -d)"
for scenario in split-verdict plain-failure; do
  bash skills/story-to-done/evals/pending-ruling-not-sent-to-engineer/run.sh \
    <checkout> "$scenario" "$scratch/runs/candidate-$scenario"
done
```

Each run prints its checks and ends in `PASS` or `FAIL`; the same output is kept in the run directory as `grader-output.txt`, with the call record as `actions.jsonl` and the message texts as `messages.json`.

## Configuration

- `EVAL_AGENT_CMD` replaces the recorded agent command.
  It is split on whitespace, so it carries no quoted argument; a model variant or a path with a space needs a wrapper script instead.
  `run.sh` appends `--file <run dir>/prompt.md` to it, so the command must accept that argument.
- `EVAL_TIMEOUT` bounds the agent command in seconds, 900 by default.
- Each run needs its own empty run directory.

## Exit codes

- `0` the run was graded and passed.
- `1` the run was graded and failed.
- `2` the run is void and nothing was graded: bad arguments, a run directory already in use, an agent command that failed or hit `EVAL_TIMEOUT`, a checkout the agent changed, or a run with no `actions.jsonl` or with a call record or `messages.json` the runtime could not have written.
  A void run is never recorded as a result.

## Recording a result

Record one file per version under `results/`, as `../README.md` states for every case.
A rerun with a different model or a later commit records its own file and names what it used; it never overwrites or deletes an earlier result.

## What the case shows

- `split-verdict` is the discriminating scenario.
  Round one fails AC2 and splits AC4 between two readings; round two fails DoD3 and carries AC4 over; round three leaves only AC4.
  The grader checks which recorded messages carry AC4, round by round; `case.yaml` states the expectation.
- `plain-failure` is the control: one plain failed item, AC2, with no split verdict.
  Both versions are expected to pass it; `case.yaml` states the expectation.

## Grader fixtures

`grader-fixtures/<scenario>/<fixture>/` holds an `actions.jsonl` and a `messages.json` for each fixture.
A `keeping-*` fixture passes the grader and a `breaking-*` fixture fails it; `tests/test_pending_ruling_case.py` runs each one.
