# SKL-317 proof of concept: a live behaviour run through promptfoo with the void retry in the provider

This proof of concept answers the first two questions of the SKL-317 spike: can a promptfoo script provider run a live agent attempt, retry void attempts inside itself and hand promptfoo one graded result per test, and does that reproduce the retry and stop rules of `skills/story-to-done/evals/suite.py`.
It runs the `own-steps` scenario of the case `skills/story-to-done/evals/qa-unfinished-own-steps` and grades each attempt with the case's own `run.sh` and `grader.py`, unchanged.
The findings are in `../findings.md`.

## Run it

```sh
SKL317_SPEND_LEDGER=<the spend ledger file of the spike> bash spikes/SKL-317/poc/run.sh
```

That is the live run: it calls a model and spends money, so it is not a command to repeat.
It writes `compare.md` beside the script.
It exits 0 when promptfoo received N graded runs and its report matches the provider's record of them.
It exits 1 when it did not or a blocker stopped the run, and `compare.md` names the blocker and claims no result.
It exits 2 when it refused to start, with the reason on stderr.

A dry run calls no model and spends nothing:

```sh
SKL317_MODE=stub SKL317_SPEND_LEDGER=<a ledger file> bash spikes/SKL-317/poc/run.sh
```

A dry run prints `compare.md` to stdout and never writes it to the repository.

The self-test checks the rules of the provider and of `compare.py` without promptfoo, Node.js, the network or a model:

```sh
python3 spikes/SKL-317/poc/selftest.py
```

## Pinned version

promptfoo `0.125.1`, set in `run.sh`.
`run.sh` installs exactly that version and refuses to start when the installed binary reports another.
The packages promptfoo depends on are pinned by date: `npm install --before` resolves each one to the newest version published before the instant `run.sh` names.
No Node lockfile is committed, because the story keeps one out of the repository.
So the install is the same only while the registry answers the same for that instant: a package version withdrawn from the registry changes it.
`npm audit signatures` checks the registry signature of every package that was installed, not that the set is the one an earlier run installed.

## Prerequisites

`run.sh` checks each of these, except network access and the model credential, before it creates anything.

- `bash`, `git`, `timeout` and `python3` 3.12 or later, as the repository already requires.
- A release of Node.js, 22.22.0 or later, with `npm`, the range promptfoo `0.125.1` declares.
  A version with a suffix, such as a release candidate, is refused.
- The spend ledger file, named by `SKL317_SPEND_LEDGER`: it exists before the first run, empty, and sits outside the repository.
- `opencode`, signed in to the model provider or given its credential (live run only).
- A checkout with nothing uncommitted except `compare.md` (live run only), at a path without whitespace.
- 1600 MB free in the temporary directory, which must be outside the repository (set `TMPDIR` when it is not).
- Network access to the npm registry for the install and for `npm audit signatures`, and to the model provider (live run only).

## Environment variables

Names only; no value belongs in this repository.

| Variable | Needed | What it is |
|---|---|---|
| `DEEPSEEK_API_KEY` | live run, when `opencode` is not already signed in | The model provider's credential. It reaches the agent only when `EVAL_PASS_ENV` names it. |
| `EVAL_PASS_ENV` | optional | Names of variables to pass to the agent, separated by spaces, as `run-suite.sh` reads it. It names no variable that begins with `SKL317_` or `PROMPTFOO_`, and not `EVAL_AGENT_CMD`. |
| `EVAL_TIMEOUT` | optional | Seconds the agent may run, as the case's `run.sh` reads it; default 900. |
| `EVAL_GRADING_MARGIN` | optional | Seconds an attempt may run past `EVAL_TIMEOUT` before it is killed, as `suite.py` reads it; default `GRADING_MARGIN` of `suite.py` at the commit under test. |
| `SKL317_MODE` | optional | `live` (default) or `stub`, the dry run. |
| `SKL317_STUB_PLAN` | optional, dry run only | What each attempt does, in order and comma-separated: `pass`, `fail`, `void` or `broken`. It replaces the injected void. |
| `SKL317_NPM_PREFIX` | optional, dry run only | A directory that already holds the pinned promptfoo install, to skip the install. |
| `SKL317_SPEND_LEDGER` | always | The spend ledger file of the spike, outside the repository. There is no default path. |
| `TMPDIR` | optional | Where the temporary directory of a run is made. |

promptfoo and the provider keep only the variables `suite.py` gives an attempt (`PATH`, `HOME`, `USER`, `LOGNAME`, `SHELL`, `LANG`, `TERM`, `TZ`, `TMPDIR`, `EVAL_TIMEOUT`, and the `LC_` and `XDG_` families), `EVAL_GRADING_MARGIN`, the ones `EVAL_PASS_ENV` names, and the settings `run.sh` gives the provider.
`run.sh` unsets every other variable in a subshell, so no value is put on a command line.
The agent gets the variables `suite.py` gives an attempt and the ones `EVAL_PASS_ENV` names, with a `TMPDIR` of its own: none of the provider's settings, so nothing names the ledger or the provider's state to it.
`run.sh` refuses to start when `EVAL_PASS_ENV` names a variable that begins with `SKL317_` or `PROMPTFOO_`, or names `EVAL_AGENT_CMD`.
The provider leaves those two families out of the agent's environment whatever the list holds.
`npm` starts under `env -i` with an empty home directory, so it sees no credential and no npm setting of the caller.

## How N graded runs map onto promptfoo

- N is 3, set in `run.sh`.
- The configuration has one test, and `run.sh` passes `--repeat 3`, so promptfoo calls the provider three times.
- `run.sh` passes `--max-concurrency 1`, so the calls run one after another, and `--no-cache`, so no call is answered from a cache.
- Each provider call runs attempts of the case's `run.sh` until one is graded, then hands promptfoo that one graded result.
- promptfoo `0.125.1` has no retry count to set to 0.
  Its one retry is the `--retry-errors` flag, which runs a later eval over the results that errored, and `run.sh` never passes it.
  `compare.md` records the number of provider calls beside the number of repeats, so a call promptfoo repeated on its own would show.

## The void retry

The provider applies the rules of `suite.py` to the exit status of each attempt of the case's `run.sh`.

- 0 is a graded pass, 1 a graded fail and 2 a void attempt; an attempt that outlives `EVAL_TIMEOUT` plus `EVAL_GRADING_MARGIN` is killed and is void too.
  The provider reads that table (`OUTCOMES`) and the default margin (`GRADING_MARGIN`) from `suite.py` at the commit under test, and stops with `suite rules unreadable` when it cannot.
- A void attempt does not count toward N: the provider absorbs it and starts the next attempt inside the same call.
- At most 2N = 6 attempts run across the whole promptfoo run.
  When the cap is reached with fewer than N graded runs, the provider hands promptfoo an error for that call.
- Any other exit status is a broken attempt: the provider starts no further attempt and hands promptfoo an error.
- A provider cannot stop promptfoo, so after a stop it refuses every later call with an error and runs nothing.

`run.sh` injects one void in the same invocation: for attempt 2 the provider gives the case's `run.sh` an agent command that fails, so the case's `run.sh` itself exits 2 and no model is called.
`compare.md` labels that attempt `injected`.

## Grading

Only the case's `run.sh` grades, by running the case's `grader.py` from the commit under test.
It grades an attempt only when the agent command exited 0 and left the checkout unchanged, so a void attempt is never graded.
`grade.py`, the promptfoo assertion, relays that grade and grades nothing again.

The commit under test is `HEAD`, and `run.sh` clones it twice, as `suite.py` keeps its own checkout apart from the one it tests.
The harness clone sits in the harness's temporary directory: the case's `run.sh`, its `grader.py`, its scenarios and its runtime run from there, and nothing given to the agent names it.
The agent's checkout sits in the second temporary directory: it is the agent's working directory and holds the skill the agent reads.
Before and after each attempt the provider compares both clones with the commit: every file the commit holds, with its content and mode, and no other file, ignored ones included.
It reads the commit's files from the repository `run.sh` was started in and reads each clone's files from disk, so a file that git in a clone was told to overlook still counts.
A clone that differs stops the run with `checkout changed`, and `compare.py` makes the same comparison after the eval.

## Token counts and cost

The agent command of a live attempt is the suite's, with two differences: it carries a `--title` only that attempt has, and it leaves out `--standalone` and `--archived`.
That lets the provider find the attempt's session by its title afterwards and read the token counts `opencode session export` reports for it.
The counts of a void attempt are read the same way.
An attempt whose agent never started, the injected void, has no session and counts as zero tokens.
When the session of an attempt is not found, or its export holds no token counts or only zeros, the provider stops the run with `no token counts`.
When the export names another model than the one priced, it stops with `another model ran`, and when the session called a subagent, whose tokens its counts leave out, with `subagent tokens uncounted`.
Each of these stops the run at that attempt, before another one is admitted against the ceiling, and `compare.md` records the blocker and claims no result.

The cost of an attempt is its token counts times the prices `provider.py` names, with their source and the date they were read.
promptfoo holds a cost of 0 and a token count of 0 for every result of a script provider, so the spend is known only from the session record `opencode` keeps.

## Spend ceiling

The ceiling for the whole spike is 5 USD, and the spend already in the ledger counts toward it.
Every attempt, dry runs included, is written to the spend ledger, the file `SKL317_SPEND_LEDGER` names: one line when it starts, with what is reserved for it, and one when it ends, with its cost.
`run.sh` refuses to start when the variable is unset, when the file does not exist or when it is in the repository, so a mistyped path cannot start a second, empty ledger.
Before each attempt that calls the model the provider adds the ledger up and stops with `ceiling reached` when the total plus the next-attempt estimate is over 5 USD.
The estimate is 0.08 USD, the figure SKL-312 gave for one agent run, or the highest cost of a single attempt so far when that is more.
The estimate is not a bound: an attempt can cost more than every attempt before it, and the total can then pass the ceiling by what that attempt cost over its estimate.
An attempt that calls no model, a dry-run attempt or the injected void, reserves and costs nothing and is not held to the ceiling.
An attempt that started and never reported counts as what was reserved for it, and an attempt that ended without a known cost stops every later run with `cumulative spend unknown` until the ledger is corrected by hand.

The agent under test is not trusted with the ledger.
`run.sh` makes two temporary directories: one for the harness (the install, promptfoo's state, the provider's state, the harness clone and a copy of the ledger) and one for the attempts (the agent's checkout, the run directories and the agent's temporary directory).
The agent's environment and arguments name only the second.
Before the eval `run.sh` measures the ledger, its length and its SHA-256, keeps the two in its own shell and hands them to the provider and to `compare.py`.
The provider writes every row to the ledger and to its copy.
Before and after each attempt it requires that the two are the same byte for byte and that they still begin with the bytes `run.sh` measured, and it stops with `spend ledger changed` when either fails.
`compare.py` requires the same of the finished run, and that the rows added are a start and an end for each attempt with its cost.
Two runs at once on one ledger stop each other with `spend ledger changed`, which is the safe side; run one at a time.

## What the checks do not cover

The agent runs as the same operating-system user as the harness, and `run.sh` puts no sandbox around it.
So each check above finds a change that is still there when the harness looks, and none of them is an access control.

- A process the agent starts can change a file in either clone and put it back before the provider compares the clone again, so a grader rewritten only while an attempt is graded is not caught.
- It can rewrite the harness's own files: the scripts in this directory, the repository `run.sh` was started in, the promptfoo install, and the provider's state and records.
- It can rewrite the session record `opencode` keeps, which the token counts and so the costs are read from.
- It can write the record the grade is read from: `qa-runtime` appends to `actions.jsonl` in the run directory from inside the agent's own process, so nothing but the agent's behaviour separates a role call it made from a line it wrote.
  That is the case as committed, and the unmodified `grader.py` reads the record it is given.
- It cannot rewrite what `run.sh` holds only in its shell, the measure of the ledger before the eval, so rows dropped from the ledger and its copy alike are caught while the scripts themselves are as committed.

`suite.py` runs its agent as the same user as itself and shares this limit.
Only another user account, a container or a sandbox around the agent closes it, and a harness whose result has to hold against the agent it tests needs one.

## Dry runs

`SKL317_MODE=stub` puts `stub_agent.py` in place of the model: it makes the scenario's role calls through the run's own `qa-runtime`, so the case's `run.sh` and `grader.py` grade a dry run as they grade a live one.
Without a plan a dry run has the shape of the live run: three passes and the injected void.
`SKL317_STUB_PLAN` sets what each attempt does instead, for example `void,void,void,void,void,void` for the attempt cap or `pass,broken` for a broken attempt, whose runner exits 3.

## Files

| File | What it is |
|---|---|
| `run.sh` | The single command: prerequisites, pinned install, signature check, clone, one promptfoo eval, report. |
| `promptfooconfig.yaml` | The promptfoo configuration: one script provider, one test, one `python` assertion. |
| `provider.py` | The script provider: the void retry, the attempt cap, the token counts and the spend ceiling. |
| `grade.py` | The assertion: relays the grade the case's `run.sh` gave. |
| `stub_agent.py` | The agent of a dry run. |
| `compare.py` | Writes `compare.md` from the provider's records and promptfoo's export, and checks the run: see below. |
| `selftest.py` | Checks the provider's and `compare.py`'s rules without promptfoo: `python3 spikes/SKL-317/poc/selftest.py`. |
| `compare.md` | Generated by the live run: one row per attempt, the provider calls, the suite rules, the spend. |

## What compare.py checks

`compare.py` is the check of the run as well as its report, and each check that fails is a blocker in `compare.md` and an exit status of 1.

- The provider's record is one run under the rules of `suite.py`: attempts numbered in order and no more than 2N of them, each outcome the one `suite.py` gives its exit status, the `injected` label on the injected attempt only, each call a row of void attempts and then one hand-back.
- promptfoo's export reports that record: one result per repeat, each carrying the attempt its call handed back with the `success`, `score`, `failureReason` and `error` that attempt maps to, the runtime options `repeat` N, `maxConcurrency` 1 and `cache` false, the pinned version, totals that count the same hand-backs, a cost and a token count of 0 in every result, the pass rate of the repeat group, and the exit status of the eval that those hand-backs give.
- The spend follows: each cost is its token counts times the prices, only the priced model ran and no subagent, and the ledger still begins with what `run.sh` measured before the eval and gained exactly this run's rows.
- The run is of one commit: both clones hold the files of the commit named and no other, and the repository did not change under the run.

## What stays out of the repository

`run.sh` installs promptfoo with `npm install --prefix` into the harness's temporary directory and points `PROMPTFOO_CONFIG_DIR` and `TMPDIR` at the same directory, with `PROMPTFOO_CACHE_ENABLED=false`.
The `node_modules` tree, the npm cache, promptfoo's database, its logs, its result file, the harness clone and the provider's state, log and copy of the ledger all live there; the agent's checkout and the run directories live in the second temporary directory; and Python is told to write no bytecode beside the scripts.
Both directories are removed when the command exits 0.
When it does not, the install and both clones are removed and promptfoo's output and the provider's state, log and copy of the ledger are kept, with the path printed.
`compare.md` holds fields only: no path, session id, prompt text, agent output or promptfoo error text.

## What no job runs

No CI job runs `run.sh` or `selftest.py`.
The story keeps every tracked change under `spikes/SKL-317/`, and the repository's test job collects `tests/` only, so both are run by hand, and a later change to these files is checked only by running them.
`selftest.py` does not run promptfoo: it calls the provider once per repeat itself and writes an export with the fields promptfoo `0.125.1` writes, so the install, promptfoo itself and the export it really writes are checked only by `run.sh`.
