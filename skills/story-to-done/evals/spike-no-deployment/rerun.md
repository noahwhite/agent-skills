# Rerun instructions

The case is one directory: `skills/story-to-done/evals/spike-no-deployment/`.
It holds the prompt, five scenarios, two fixture profiles, a stub runtime, a grader, and `results/` for recorded runs.

## What a run does

`run.sh` copies one scenario's `scenario.md`, the scenario's fixture profile as `profile.yaml`, and the stub `story-runtime` into the `workspace/` directory of a run directory outside the checkout.
It fills the prompt's two placeholders and launches the agent command from the checkout with `AGENT_SKILLS_PROFILE` naming that `profile.yaml`, so the skill and `select-path.py` read the fixture, never the checkout's or the home profile.
The `deployed` scenario gets `profiles/integration-environment.yaml`, with one environment, `dev`, on the integration branch; every other scenario gets `profiles/no-environment.yaml`, with `environments: []`.
The agent never reaches a real tracker, user, senior engineer or QA agent: `story-runtime` prints the story from the scenario's `story.json`, records each message and read the agent makes, and serves the scenario's senior-engineer handback, if it has one, to the first senior-engineer launch, reading it from the case's scenario directory.
Serving it moves the stub story to `In Deployment Review` and adds the handback's step 12 note to the story's comments.
A QA launch never hands back, so a run ends with QA started, or earlier.
`grader.py` grades only the record, `actions.jsonl` in the run directory, the message texts in `messages.json` beside it, and the coordinator's checklist, `workspace/coordinator-todo.md`; never the agent's prose.
The record sits outside the agent's `workspace/` but is not sandboxed from it, so an agent that writes outside its directory could forge it.

## Baseline and candidate

The baseline is `ec533a6`, the skill on `main` before SKL-270's change.
The candidate is `298a7ee`, a `main` commit that carries SKL-162, SKL-269 and SKL-270.
Run each from its own detached checkout, from the root of a clean harness checkout that carries this case, as `../README.md` states:

```sh
export EVAL_AGENT_CMD="opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro Follow the instructions in the attached file exactly."
export EVAL_PASS_ENV="DEEPSEEK_API_KEY"
git worktree add --detach <scratch>/skill-ec533a6 ec533a6
uv run --locked bash skills/story-to-done/evals/run-suite.sh --runs 3 <scratch>/skill-ec533a6 deepseek-v4-pro-baseline-ec533a6 spike-no-deployment
git worktree remove <scratch>/skill-ec533a6
git worktree add --detach <scratch>/skill-298a7ee 298a7ee
uv run --locked bash skills/story-to-done/evals/run-suite.sh --runs 3 <scratch>/skill-298a7ee deepseek-v4-pro-candidate-298a7ee spike-no-deployment
git worktree remove <scratch>/skill-298a7ee
```

One scenario, through `run.sh` directly:

```sh
bash skills/story-to-done/evals/spike-no-deployment/run.sh <checkout> no-deployment "$(mktemp -d)/run"
```

Each run prints its checks and ends in `PASS` or `FAIL`; the same output is kept in the run directory as `grader-output.txt`, and for `deployed` the path grade as `grader-path-output.txt`.

## Configuration

- `EVAL_AGENT_CMD` replaces the recorded agent command.
  It is split on whitespace, so it carries no quoted argument.
  `run.sh` appends `--file <run dir>/workspace/prompt.md` to it, so the command must accept that argument.
- `EVAL_TIMEOUT` bounds the agent command in seconds, a positive whole number, 900 by default.
- Each run needs its own empty run directory.

## Exit codes

- `0` the run was graded and passed.
- `1` the run was graded and failed.
- `2` the run is void and nothing was graded: bad arguments, a run directory already in use, an agent command that failed or hit `EVAL_TIMEOUT`, a checkout the agent changed, or a run with no `actions.jsonl` or with a call record or `messages.json` the runtime could not have written.

## What the case shows

- `spike`, `no-deployment` and `direct-entry` are graded on the `path:` line of each brief and of the coordinator's checklist, and on which roles were spawned; `direct-entry` also on the merged commit its QA brief names.
- `conflict` has a `[Spike]` title without the spike label, so `select-path.py` prints an `ask:` line: the coordinator must message the user, spawn no role, and leave `path: unresolved` in its checklist.
- `deployed` is the control: both roles spawned in order, and the QA brief naming `dev`, at both commits.
  Its further grade, `deployed-path`, adds `path: deployed` in each brief and in the checklist, which only the candidate carries.

## Normalization

The suite runner rewrites every record before writing it, as `../README.md` states; no guard rejected a recorded result of this case, so no further replacement was made.
