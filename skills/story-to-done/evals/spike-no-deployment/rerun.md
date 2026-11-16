# Rerun instructions

The case is one directory: `skills/story-to-done/evals/spike-no-deployment/`.
It holds the prompt, five scenarios, two fixture profiles, a stub runtime, a grader, and `results/` for recorded runs.

## What a run does

`run.sh` copies one scenario's `scenario.md`, the scenario's fixture profile as `profile.yaml`, and the stub `story-runtime`, with the scenario's directory written into it, into the `workspace/` directory of a run directory outside the checkout.
It also copies `runtime/sitecustomize.py` into the run directory's `selector-hook/` and puts that directory first on the agent's `PYTHONPATH`, so each run of `select-path.py` appends its arguments, its time and what it printed to `selector.jsonl` in the run directory.
It fills the prompt's two placeholders and launches the agent command from the checkout with `AGENT_SKILLS_PROFILE` naming that `profile.yaml`, so the skill and `select-path.py` read the fixture, never the checkout's or the home profile.
The `deployed` scenario gets `profiles/integration-environment.yaml`, with one environment, `dev`, on the integration branch; every other scenario gets `profiles/no-environment.yaml`, with `environments: []`.
The agent never reaches a real tracker, user, senior engineer or QA agent: `story-runtime` prints the story from the scenario's `story.json`, records each message and read the agent makes, and serves the scenario's senior-engineer handback, if it has one, to the first senior-engineer launch, reading it from the case's scenario directory.
Serving it moves the stub story to `In Deployment Review` and adds the handback's step 12 note to the story's comments.
A QA launch never hands back, so a run ends with QA started, or earlier.
`grader.py` grades only the record, `actions.jsonl` in the run directory, the message texts in `messages.json` beside it, `selector.jsonl`, and the coordinator's checklist, `workspace/coordinator-todo.md`; never the agent's prose.
The record sits outside the agent's `workspace/` but is not sandboxed from it, so an agent that writes outside its directory could forge it.
`run.sh` hashes the case directory, apart from `results/`, and the runtime, profile, prompt and hook it gave the agent, before and after the agent runs, and voids a run that changed any of them.

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
- `2` the run is void and nothing was graded: bad arguments, a run directory already in use, an agent command that failed or hit `EVAL_TIMEOUT`, a checkout the agent changed, a case or given file the agent changed, or a run with no `actions.jsonl` or with a call record, `messages.json` or `selector.jsonl` the runtime or the hook could not have written.

## What the case shows

- Every grade but the `deployed` control requires a run of `select-path.py` that printed the story's line no later than the first message, and every grade requires a tracker read before the first message.
- `spike`, `no-deployment` and `direct-entry` are graded on the `path:` line of each brief and of the coordinator's checklist, on how many sessions of each role were started, on no message to the user, and on the QA brief's target: the deliverable link on `spike`, the merged commit on `no-deployment` and `direct-entry`.
- `conflict` has a `[Spike]` title without the spike label, so `select-path.py` prints `ask: spike-title-without-label`: the coordinator must message the user, naming the three paths, spawn no role, and leave `path: unresolved` in its checklist.
- `deployed` is the control: one senior engineer, then one QA session after its handback, each brief naming the story and its role's skill, no message to the user, and a QA brief naming `dev`, at both commits.
  `run.sh` always grades the same run again as `deployed-path`, which adds the selector run and `path: deployed` in each brief and in the checklist.
  Only the candidate carries the path line, so the baseline fails `deployed-path` and its `deployed` run records have outcome `fail`, while the control's own grade passes at both commits.
- A brief names the story and its role's skill in a clause that denies nothing; the QA brief names its target in a clause that denies nothing and in no clause that denies anything.
  A clause ends at a line break or at punctuation followed by white space, and a name inside a URL, a path, an email address or a dotted host name does not count.
- `grader-fixtures/` holds, per scenario, a `keeping` run the grader passes and a `breaking-baseline` run it fails, copied from runs recorded before the selector hook existed, with a `selector.jsonl` added to each `keeping` run, which `tests/test_spike_no_deployment_case.py` grades.

## Normalization

The suite runner rewrites every record before writing it, as `../README.md` states.
Before grading, `run.sh` also rewrites each `user.` + `signingkey` in `messages.json` and the coordinator's checklist to `user.{signingkey}`.
`tests/test_signing_key.py` allows the git signing-key setting's name in a recorded run only inside the restated override sentence, and a coordinator restates the git rule in its own words.
No record is edited after it is written.
