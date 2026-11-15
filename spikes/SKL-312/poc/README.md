# SKL-312 proof of concept: replay recorded eval runs through promptfoo

This proof of concept answers one question of the SKL-312 spike: can promptfoo drive the existing eval harness and report the verdicts the harness reports.
It replays the committed run records of the case `skills/story-to-done/evals/qa-unfinished-own-steps` through promptfoo and grades each one with the case's own `grader.py`.
No agent runs and no model is called.
The findings are in `../findings.md`.

## Run it

```sh
bash spikes/SKL-312/poc/run.sh
```

The command exits 0 when every replayed run and every probe lands on the promptfoo outcome the mapping table gives it, and 1 otherwise.
It rewrites the two generated files below on every run.

## Pinned version

promptfoo `0.125.1`, set in `run.sh`.
`run.sh` installs exactly that version and stops when the installed binary reports another.

## Prerequisites

- `bash`, `git` and `python3` 3.12 or later, as the repository already requires.
- Node.js 22.22.0 or later with `npm`, the range promptfoo `0.125.1` declares.
- Network access to the npm registry for the install and for `npm audit signatures`.
- About 750 MB of free space in the temporary directory, which must be outside the repository (set `TMPDIR` when it is not).

No credential is needed, and none is read: promptfoo starts under `env -i` with only the variables `run.sh` names.

## Files

| File | What it is |
|---|---|
| `run.sh` | The single command: pinned install, signature check, replay, probes, report. |
| `promptfooconfig.yaml` | The promptfoo configuration: one script provider, one `python` assertion. |
| `provider.py` | The script provider: rebuilds one recorded run's directory from the committed record. |
| `grade.py` | The assertion: runs the case's `grader.py`, unchanged, on the rebuilt run. |
| `compare.py` | Lists the records for promptfoo and writes the two generated files. |
| `compare.md` | Generated: one row per recorded run, the verdict mapping table, unmapped tokens. |
| `provider-contract/envelope.json` | Generated: one provider invocation's arguments, input shape and environment variable names. |

## What stays out of the repository

`run.sh` installs promptfoo with `npm install --prefix` into a temporary directory and points `PROMPTFOO_CONFIG_DIR` at the same directory.
The `node_modules` tree, promptfoo's database, its logs, its result files and the rebuilt run directories all live there.
The directory is removed when the command exits 0 and kept, with its path printed, when it does not.
No Node lockfile is written to the repository, so the packages promptfoo depends on are resolved again on every run.
