# story-to-done eval suite

Executed eval cases for the story-to-done skill.
The suite runner that repeats them is shared by every skill's `evals/`: `scripts/run-suite.sh` at the repository root, which takes the skill's `evals/` directory as its first argument.
That directory must be `skills/<skill>/evals` in the checkout holding the runner, so the harness commit a record names is the runner that ran; the runner refuses any other directory, an `evals/` directory with no case, and a case directory whose name the suite cannot run, both for a run and for `--list`.
Each case runs a real agent against a fixed scenario and grades the tool calls it recorded, never its prose.

## Prerequisites

- `opencode`, logged in to the provider of the model the case's `case.yaml` names under `runtime.model`.
- `uv`, which supplies `python3` with PyYAML from this repository's lockfile.
- Model access: the provider credential `opencode` uses for that model.
- `EVAL_AGENT_CMD` (required by the runner) is the agent command each case's `run.sh` runs.
  It is split on whitespace, so it carries no quoted argument.
  It must name its model with `--model provider/model[#variant]`; the runner records that model, the variant as the reasoning effort (`default` without one), and the command itself.
- `EVAL_PASS_ENV` names, separated by spaces, the variables an attempt gets beyond its base environment, such as the provider credential: `EVAL_PASS_ENV="DEEPSEEK_API_KEY"`.
  The base environment is `PATH`, `HOME`, `USER`, `LOGNAME`, `SHELL`, `LANG`, `TERM`, `TZ`, `TMPDIR`, `EVAL_AGENT_CMD`, `EVAL_TIMEOUT` and every `LC_*` and `XDG_*` variable.
  Each passed value is rewritten to `{redacted}` in every record; the runner refuses a passed value shorter than 8 characters, which is too common a string to redact.
- `EVAL_TIMEOUT` (optional) bounds each agent command in seconds, 900 by default.
- `EVAL_GRADING_MARGIN` (optional) is the seconds an attempt may run past `EVAL_TIMEOUT` for its setup and grading, 300 by default.
  Both are whole numbers of at least 1; the runner refuses any other value.

## Run

From a fresh shell, at the root of a checkout of this repository (the harness checkout).
`<checkout>` is the checkout holding the skill under test, and `<scratch>` any directory outside both checkouts.

First set the agent command, which every command below uses.
This is the command the committed runs used; the message comes last, because `run.sh` appends the prompt to it as `--file`:

```sh
export EVAL_AGENT_CMD="opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro Follow the instructions in the attached file exactly."
```

When the provider credential is an environment variable rather than stored `opencode` auth, also pass it to the agent:

```sh
export EVAL_PASS_ENV="DEEPSEEK_API_KEY"
```

One scenario, through the case's own `run.sh`:

```sh
bash skills/story-to-done/evals/qa-unfinished-own-steps/run.sh <checkout> own-steps "$(mktemp -d)/run"
```

One case, with 3 graded runs per scenario:

```sh
uv run --locked bash scripts/run-suite.sh skills/story-to-done/evals --runs 3 <checkout> <label> qa-unfinished-own-steps
```

The whole suite, every case directory holding a `case.yaml`:

```sh
uv run --locked bash scripts/run-suite.sh skills/story-to-done/evals <checkout> <label>
```

A baseline and a candidate are two suite runs, one per commit, each from its own detached checkout.
A baseline run of a discriminating case exits 1 by design, so run the commands one at a time, not in a shell that stops on the first non-zero status, or the cleanup is skipped:

```sh
git worktree add --detach <scratch>/skill-7a6cb17 7a6cb17
uv run --locked bash scripts/run-suite.sh skills/story-to-done/evals <scratch>/skill-7a6cb17 <model>-baseline-7a6cb17 qa-unfinished-own-steps
git worktree remove <scratch>/skill-7a6cb17
```

The case names, with nothing run:

```sh
uv run --locked bash scripts/run-suite.sh skills/story-to-done/evals --list
```

The runner lists cases from the harness checkout's `evals/` directory, never from `<checkout>`, so a baseline commit that predates a case still runs it.
It refuses a harness or skill checkout with any uncommitted change, tracked or untracked, because the commit it records would not describe the run; only the suite's own records under a `results/` directory of this `evals/` directory are allowed, untracked or with an unstaged modification; a record staged, deleted, renamed or unmerged is refused.
Another skill's uncommitted records are changes like any other, so commit or remove them before running a different skill's suite in the same checkout.

A run that stopped before writing its summary is continued with `--resume` and the same arguments and environment: each attempt that already has both records is counted from them instead of running again.
Resume refuses a record whose label, commits, model, reasoning effort or agent command differ from this run's, a record whose outcome or verdicts are not the ones its exit code and grades give (a verdict line that redaction rewrote keeps the recorded verdict), and a record of a broken attempt.
A run without `--resume` refuses a label that already has records, and no run writes a summary while a record of its label is one it did not count, as a resume with fewer runs or cases would leave.

## Runner behaviour

- Each attempt calls the case's `run.sh CHECKOUT SCENARIO RUN_DIR` through `bash` with a new run directory outside both checkouts.
- `run.sh` exits 0 for a graded pass, 1 for a graded fail and 2 for a void run.
  An attempt still running `EVAL_TIMEOUT` + `EVAL_GRADING_MARGIN` seconds after it started is killed and void.
- A void run is not counted as graded and is retried until the scenario has N graded runs or 2×N attempts.
  Its record names the runner's classified reason (`run.sh exited 2: void`, or `run.sh did not finish within N seconds`), never text from `run.sh`; the first `HARNESS:` or `run.sh:` line `run.sh` wrote to stderr goes to the operator's stderr only.
- The exit status is the scenario's verdict; only a scenario with further grades is counted from its grade files, and its status must still be 0 exactly when every grade passes.
- Any other exit status, further grades without the scenario's own `grader-output.txt`, further grade files that contradict the status, or grades that differ from an earlier graded attempt's of the same scenario mean the case or the machine is broken: the attempt is recorded with outcome `error` and the suite stops with exit 1, writing no summary.
- Before each attempt and before the summary, the runner checks that both checkouts are still clean and at their commits, with every committed record as it was when the run started; a checkout an attempt changed, a committed record included, stops the suite with exit 1.
- A case that names a scenario twice is refused.
- The runner exits 0 when every scenario has N graded runs and every graded run of every grade passed, 1 when any scenario has fewer, any graded run failed (the summary is still written, and stderr names each failing grade) or it stopped on a broken attempt, and 2 when it refuses to start or would overwrite a file.
  A baseline run of a discriminating case therefore exits 1 by design.
  Exit 1 alone does not say which: a run whose graded runs failed or fell short wrote `results/suite-<label>.md` and its stderr names them (`run-suite: failing graded runs for:` or `run-suite: fewer than N graded runs for:`), while a run that stopped on a broken attempt or a changed checkout wrote no summary.

## Results layout and naming

- `<case>/results/<label>-<scenario>-<checkout sha>-harness-<harness sha>-<attempt>.json` is the run record of one attempt, graded or void: case, scenario, label, both full commits, model, reasoning effort, agent command, exit status, outcome, void reason, each grade's verdict, the grader's output lines, and the run-directory files the grader reads.
- `<case>/results/<label>-<scenario>-<checkout sha>-harness-<harness sha>-<attempt>-calls.jsonl` is that attempt's tool-call record, the run's `actions.jsonl`; the run record's `calls_record` is `absent` when the run wrote none.
- `results/suite-<label>.md` is the suite summary: per case, scenario and skill commit, the graded run count n, the pass count k, the pass rate k/n, the variance k/n × (1 - k/n), the void count and reasons, and the model, reasoning effort, skill commit and harness commit.
  It carries counts and provenance only, never transcript text.
  When the harness and the skill checkout are the same tree, paths under it read `{checkout}`, and the record still names both commits.
- A scenario whose `run.sh` writes more than one grade file has one summary row per grade: `grader-output.txt` is the scenario's own grade, and `grader-<g>-output.txt` is a further grade in a row named `<scenario>-<g>` over the same runs.
  A control scenario's own row therefore counts its control grade alone.
- Both short SHAs are `git rev-parse --short=7`, at least 7 characters.
- The runner never overwrites a file: a name that exists stops it with exit 2, and each file is written whole or not at all.
- Before writing, it rewrites passed variable values to `{redacted}`, the run's roots to placeholders (`{run_dir}`, `{tmp}`, `{checkout}`, `{harness}`, `{tmpdir}`, `{home}`) where a whole path starts with one, whether the path is plain or spelled with any JSON escape inside a string literal, UUID shapes to `{uuid}`, any other absolute path to `{path}`, and anything else the repository's leak scan rejects to `{redacted}`, so a record passes that scan.
- Only files directly in `results/` or `<case>/results/` count as the suite's own records; any other uncommitted file stops the runner.
- The older `baseline-<sha>[-harness-<sha>]` and `candidate-<sha>` files in a case's `results/` predate the runner and stay as history.

Retention: each run records only the files its grader reads, plus the tool-call record and the run record.
A file the grader reads is one its code names as a relative file path in a string, such as `sessions.json` or `senior-engineer/senior-engineer-todo.md`; the run record keeps each such file the run directory holds, except `actions.jsonl`, which is the tool-call record.
A file a grader names only through a constructed path, such as a checklist under the round's scratch subdirectory, is a committed scenario fixture that `run.sh` copies in, so the commit already holds it.
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
- `grader.py`, which grades the tool-call record (`actions.jsonl`) and message files, never the agent's prose: no file name in its code may be a `.txt` or `.log` file, name agent output, a transcript, stdout, stderr or a response, or be a file `run.sh` redirects into;
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

### Where `pending-ruling-not-sent-to-engineer` differs from the `qa-unfinished-own-steps` layout

- Fixtures for several QA rounds: each scenario holds a `rounds.json` that lists the QA records (`qa-round-<n>.md`) and senior-engineer handbacks (`engineer-handback-<n>.md`) the stub serves in turn, with the tracker state each one leaves, instead of one `qa-round-1.json` launch record.
  The stub serves them from the case's scenario directory, and the agent works in the run directory's `workspace/`, so no later round is in its directory before it is served.
- The user message channel in the stub runtime: `runtime/story-runtime` sends a message to the user as well as to a new senior-engineer or QA session, records each send in `actions.jsonl` with the QA round it follows and the record it served, and keeps each message's text in `messages.json`, which the grader reads beside the call record.
- The `control` field on control scenarios: `plain-failure` carries it in `case.yaml`, so the suite reports it as a control.
- Grader fixtures: `grader-fixtures/<scenario>/` holds a keeping fixture and one or more breaking fixtures, outside `results/`, which `tests/test_pending_ruling_case.py` grades.

### Where `owner-wait-verified` differs from the `qa-unfinished-own-steps` layout

- A stub tracker: `runtime/tracker` serves each scenario's fixture stories from `scenarios/<name>/stories/`, read from the case's scenario directory, and records each read with the story it named.
- A stub role runtime with a user message channel: `runtime/role-runtime` launches or resumes a senior-engineer or QA session and sends messages to the user, keeping each message's text in `messages.json`; the last user message is the run's final message, which the grader reads beside the call record.
- Two scenarios with opposite expectations, and `run.sh <checkout> both <run dir>` runs both in one invocation.
- A judge for the final message: the grader checks the recorded calls deterministically and has the run's own agent command, launched afresh with only the final message and the scenario's intent, judge whether the message carries that intent; it keeps the verdict in `judge-verdict.json`, so a recorded run grades again without a new judge call.

## Cases

| Case | Kind | Recorded runs meet the definition |
|---|---|---|
| `qa-unfinished-own-steps` | discriminating | not discriminating (DeepSeek V4 Pro, 3 graded runs per scenario at 7a6cb17 and 4f0eb79): `own-steps` fails 0/3 at baseline and passes 3/3 at candidate, `read-back` passes 0/3 at both commits, the `new-round-read` grade passes 3/3 at baseline and 1/3 at candidate, and the `owner-action` and `new-round` controls pass 3/3 at both commits; see `results/suite-deepseek-v4-pro-baseline-7a6cb17.md` and `results/suite-deepseek-v4-pro-candidate-4f0eb79.md` |
| `pending-ruling-not-sent-to-engineer` | discriminating | not discriminating (DeepSeek V4 Pro, 3 graded runs per scenario at 9bd3e16 and 6838b35, recorded on harness 07567d2 and again after each of two case revisions on harness 768ca16 and 7b8bc4f): in every recording `split-verdict` passes 3/3 at baseline and 3/3 at candidate, and the `plain-failure` control passes 3/3 at both commits; see `results/suite-deepseek-v4-pro-baseline-9bd3e16-h07567d2.md`, `results/suite-deepseek-v4-pro-candidate-6838b35-h07567d2.md`, `results/suite-deepseek-v4-pro-baseline-9bd3e16-r1-h768ca16.md`, `results/suite-deepseek-v4-pro-candidate-6838b35-r1-h768ca16.md`, `results/suite-deepseek-v4-pro-baseline-9bd3e16-r2-h7b8bc4f.md` and `results/suite-deepseek-v4-pro-candidate-6838b35-r2-h7b8bc4f.md` |
| `owner-wait-verified` | discriminating | meets the definition (DeepSeek V4 Pro, 3 graded runs per scenario at 9e65dd3 and ad92cae, harness ad92cae): `rescoped-brief` fails 0/3 at baseline and passes 3/3 at candidate, and the `owner-value` control passes 3/3 at both commits; see `results/suite-deepseek-v4-pro-baseline-9e65dd3-had92cae.md` and `results/suite-deepseek-v4-pro-candidate-ad92cae-had92cae.md` |
