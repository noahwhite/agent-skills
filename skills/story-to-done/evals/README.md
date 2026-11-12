# story-to-done eval suite

Executed eval cases for the story-to-done skill, and the suite runner that repeats them.
Each case runs a real agent against a fixed scenario and grades the tool calls it recorded, never its prose.

## Prerequisites

- `opencode`, logged in to the provider of the model the case's `case.yaml` names under `runtime.model`.
- `uv`, which supplies `python3` with PyYAML from this repository's lockfile.
- Model access: the provider credential `opencode` uses for that model.
- `EVAL_AGENT_CMD` (optional) replaces a case's agent command.
  It is split on whitespace, so it carries no quoted argument.
  It must name its model with `--model provider/model[#variant]`; the runner records that model, the variant as the reasoning effort (`default` without one), and the command itself.
  Without it, the runner records the case's `runtime.model` and `runtime.reasoning_effort` and "the case's run.sh default" as the command.
- `EVAL_TIMEOUT` (optional) bounds each agent command in seconds, 900 by default.
- `EVAL_GRADING_MARGIN` (optional) is the seconds an attempt may run past `EVAL_TIMEOUT` for its setup and grading, 300 by default.

## Run

From a fresh shell, at the root of a checkout of this repository (the harness checkout).
`<checkout>` is the checkout holding the skill under test, and `<scratch>` any directory outside both checkouts.

One scenario, through the case's own `run.sh`:

```sh
bash skills/story-to-done/evals/qa-unfinished-own-steps/run.sh <checkout> own-steps "$(mktemp -d)/run"
```

One case, with 3 graded runs per scenario:

```sh
uv run --locked bash skills/story-to-done/evals/run-suite.sh --runs 3 <checkout> <label> qa-unfinished-own-steps
```

The whole suite, every case directory holding a `case.yaml`:

```sh
uv run --locked bash skills/story-to-done/evals/run-suite.sh <checkout> <label>
```

A baseline and a candidate are two suite runs, one per commit, each from its own detached checkout:

```sh
git worktree add --detach <scratch>/skill-7a6cb17 7a6cb17
uv run --locked bash skills/story-to-done/evals/run-suite.sh <scratch>/skill-7a6cb17 <model>-baseline-7a6cb17 qa-unfinished-own-steps
git worktree remove <scratch>/skill-7a6cb17
```

The runner lists cases from the harness checkout, never from `<checkout>`, so a baseline commit that predates a case still runs it.
It refuses a harness or skill checkout with any uncommitted change, tracked or untracked, because the commit it records would not describe the run; only the suite's own uncommitted records under a `results/` directory are allowed.

An interrupted run is continued with `--resume` and the same arguments: each attempt that already has both records is counted from them instead of running again.

## Runner behaviour

- Each attempt calls the case's `run.sh CHECKOUT SCENARIO RUN_DIR` through `bash` with a new run directory outside both checkouts.
- `run.sh` exits 0 for a graded pass, 1 for a graded fail and 2 for a void run.
  An attempt still running `EVAL_TIMEOUT` + `EVAL_GRADING_MARGIN` seconds after it started is killed and void.
- A void run is recorded with its reason, the first `HARNESS:` or `run.sh:` line `run.sh` wrote to stderr, is not counted as graded, and is retried until the scenario has N graded runs or 2×N attempts.
- Any other exit status means the case or the machine is broken: the attempt is recorded with outcome `error` and the suite stops with exit 1, writing no summary.
- The runner exits 0 when every scenario has N graded runs, 1 when any has fewer or it stopped on a broken attempt, and 2 when it refuses to start or would overwrite a file.

## Results layout and naming

- `<case>/results/<label>-<scenario>-<checkout sha>-harness-<harness sha>-<attempt>.json` is the run record of one attempt, graded or void: case, scenario, label, both full commits, model, reasoning effort, agent command, exit status, outcome, void reason, each grade's verdict, the grader's output lines, and the run-directory files the grader reads.
- `<case>/results/<label>-<scenario>-<checkout sha>-harness-<harness sha>-<attempt>-calls.jsonl` is that attempt's tool-call record, the run's `actions.jsonl`; the run record's `calls_record` is `absent` when the run wrote none.
- `results/suite-<label>.md` is the suite summary: per case, scenario and skill commit, the graded run count n, the pass count k, the pass rate k/n, the variance k/n × (1 - k/n), the void count and reasons, and the model, reasoning effort, skill commit and harness commit.
  It carries counts and provenance only, never transcript text.
- A scenario whose `run.sh` writes more than one grade file has one summary row per grade: `grader-output.txt` is the scenario's own grade, and `grader-<g>-output.txt` is a further grade in a row named `<scenario>-<g>` over the same runs.
  A control scenario's own row therefore counts its control grade alone.
- Both short SHAs are `git rev-parse --short=7`, at least 7 characters.
- The runner never overwrites a file: a name that exists stops it with exit 2, and each file is written whole or not at all.
- Before writing, it rewrites the run's roots to placeholders (`{run_dir}`, `{tmp}`, `{checkout}`, `{harness}`, `{tmpdir}`, `{home}`), UUID shapes to `{uuid}`, any other absolute path to `{path}`, and anything else the repository's leak scan rejects to `{redacted}`, so a record passes that scan.
- The older `baseline-<sha>[-harness-<sha>]` and `candidate-<sha>` files in a case's `results/` predate the runner and stay as history.

Retention: each run records only the files its grader reads, plus the tool-call record and the run record.
A file the grader reads is one its code names as a string, such as `sessions.json`; the run record keeps each such file the run directory holds, except `actions.jsonl`, which is the tool-call record.
Agent output and run directories are deleted once the records are written.

A run with a different model or configuration records its own results under its own name: give it its own LABEL, naming the model and configuration, and never reuse a label to replace an earlier record.

## Definitions

- A **discriminating** case has at least 3 graded runs per scenario at each of baseline and candidate.
  Every non-control scenario passes every candidate run and fails every baseline run, and every control scenario passes every run at both commits.
- A **regression pin** passes on both commits by design.
- A scenario whose `case.yaml` entry has a `control` field is graded as a regression pin inside its case.
- Any other result is reported as `not discriminating` or `inconclusive`.
  `inconclusive` means a scenario has fewer than 3 graded runs at either commit; `not discriminating` means the runs are complete and miss the definition.

## Case contract

Every case directory holds:

- `case.yaml`, with the fields of `qa-unfinished-own-steps/case.yaml` plus `kind: discriminating | regression-pin`;
- `prompt.md`;
- `grader.py`, which grades the tool-call record (`actions.jsonl`) and message files, never the agent's prose: no file name in its code may name agent output or a transcript;
- `run.sh`, committed as mode 100755, keeping the exit codes above;
- at least one scenario, with its fixtures under `scenarios/<name>/`;
- `results/`.

A tabletop case answered in text is not accepted.
`tests/test_eval_suite.py` asserts the contract for every case directory.

## Adding a case or a scenario

1. Copy the `qa-unfinished-own-steps` layout into a new directory, or add a `scenarios/<name>/` directory and its `case.yaml` entry to an existing case.
2. Set `kind`, the `baseline` and `candidate` commits (the parent of the owning story's merge commit, and that merge commit), and a `control` field on each control scenario.
3. Run the suite once at each commit with 3 graded runs per scenario, and commit the records and both summaries.
4. Add the case to the list below with whether its runs meet its definition.

The stories that add into this layout are SKL-274 (regression-pin cases), SKL-275 (discriminating cases), SKL-162 (`spike-no-deployment`) and SKL-188 (further `qa-unfinished-own-steps` scenarios).

## Cases

| Case | Kind | Recorded runs meet the definition |
|---|---|---|
| `qa-unfinished-own-steps` | discriminating | not discriminating (DeepSeek V4 Pro, 3 graded runs per scenario at 7a6cb17 and 4f0eb79): `own-steps` fails 0/3 at baseline and passes 3/3 at candidate, `read-back` passes 0/3 at both commits, the `new-round-read` grade passes 3/3 at both commits, and the `owner-action` and `new-round` controls pass 3/3 at both commits; see `results/suite-deepseek-v4-pro-baseline-7a6cb17.md` and `results/suite-deepseek-v4-pro-candidate-4f0eb79.md` |
