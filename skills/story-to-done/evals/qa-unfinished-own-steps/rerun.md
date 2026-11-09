# Rerun instructions

The case is one directory: `skills/story-to-done/evals/qa-unfinished-own-steps/`.
It holds the prompt, four scenarios, a graded tool-call record and the recorded runs under `results/`.

## What a run does

`run.sh` copies one scenario, its QA round 1 checklist file (into the run's
`qa-agent-round-1/` subdirectory) and the run's `qa-runtime` into a run directory outside the
checkout, fills the prompt's two placeholders, launches the agent command from the
checkout, and then grades the record. The agent never launches a real QA role: `qa-runtime`
records the launch, continuation, stop or checklist read it decided on, and `grader.py` grades
only that record, so the result turns on session identity, tool-call evidence and the checklist
read, never on prose.

## Baseline

The baseline is the skill as committed on the integration branch before this case, `7a6cb17`.

```sh
scratch="$(mktemp -d)"
git -C <checkout> worktree add --detach "$scratch/baseline-7a6cb17" 7a6cb17
bash skills/story-to-done/evals/qa-unfinished-own-steps/run.sh \
  "$scratch/baseline-7a6cb17" own-steps "$scratch/runs/baseline-own-steps"
git -C <checkout> worktree remove "$scratch/baseline-7a6cb17"
```

## Candidate

The candidate is the checkout that carries this case.

```sh
scratch="$(mktemp -d)"
for scenario in own-steps read-back owner-action new-round; do
  bash skills/story-to-done/evals/qa-unfinished-own-steps/run.sh \
    <checkout> "$scenario" "$scratch/runs/candidate-$scenario"
done
```

Each run prints its assertions and ends in `PASS` or `FAIL`; the same output is kept in the
run directory as `grader-output.txt`, with the agent's own output beside it as
`agent-output.txt` and the call record as `actions.jsonl`.

## Configuration

- `EVAL_AGENT_CMD` replaces the recorded agent command. It is split on whitespace, so it carries
  no quoted argument; a model variant or a path with a space needs a wrapper script instead.
- `EVAL_TIMEOUT` bounds the agent command in seconds, 900 by default.
- Each run needs its own empty run directory.

## Exit codes

- `0` the run was graded and passed.
- `1` the run was graded and failed.
- `2` the run is void and nothing was graded: bad arguments, a run directory already in use, an
  agent command that failed or hit `EVAL_TIMEOUT`, or a checkout the agent changed. A void run is
  never recorded as a result.

## Recording a result

Record one file per version under `results/`, named `<version>-<ref>.md`, with the
configuration used and one line per scenario with its verdict, plus `<version>-<ref>-calls.jsonl`
holding the calls and grades the verdicts were read from. A rerun with a different model or a
later commit records its own file and names what it used; it never overwrites or deletes an
earlier result. When a result stops being current, keep it and mark it superseded in its first
paragraph, naming the record that replaces it, so the trail from run to claim stays readable.

## What the case shows

- `own-steps` and `read-back` are the discriminating scenarios, each with one open item and
  one role call.
  In `own-steps` the handback states what the item waits on, so the baseline stops and the
  candidate resumes the session it is already in, in the same round, with step 4's continuation:
  a message that carries only that the round is unfinished and the round's scratch subdirectory.
  In `read-back` the handback names the item with no stated blocker, so the candidate resumes the
  same session in the same round with step 0's checklist read-back resume, SKILL.md's prescribed
  message word for word.
  Each scenario holds one kind of open item, because a resume hands control back to QA and the
  next handback is a later step's input, so one step never owes both messages.
- `owner-action` and `new-round` are controls: both versions must stop for an owner action
  that sits beside QA's own work, and both must start a new session for a new round rather
  than reuse an earlier one.
