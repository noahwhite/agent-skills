# SKL-312 proof of concept: replay recorded eval runs through promptfoo

This proof of concept answers one question of the SKL-312 spike: can promptfoo drive the existing eval harness and report the verdicts the harness reports.
It replays the committed run records of the case `skills/story-to-done/evals/qa-unfinished-own-steps` through promptfoo and grades each one with the case's own `grader.py`.
No agent runs and no model is called.
The findings are in `../findings.md`.

## Run it

```sh
bash spikes/SKL-312/poc/run.sh
```

The command exits 0 when every replayed run and every probe lands on the promptfoo outcome the mapping table gives it and the two generated files below come out as committed.
It exits 1 otherwise, and names the reason on stderr or in `compare.md`.
It rewrites the two generated files on every run that reaches the report.

## Pinned version

promptfoo `0.125.1`, set in `run.sh`.
`run.sh` installs exactly that version and stops when the installed binary reports another.
The packages promptfoo depends on are pinned by date: `npm install --before` resolves each one to the newest version published before the instant `run.sh` names.
No Node lockfile is committed, because the story keeps one out of the repository.

## Prerequisites

`run.sh` checks these before it creates anything.

- `bash`, `git` and `python3` 3.12 or later, as the repository already requires.
- Node.js 22.22.0 or later with `npm`, the range promptfoo `0.125.1` declares.
- A full clone: the replay reads history to see that the case is the one the records were graded with.
- 1600 MB free in the temporary directory, which must be outside the repository (set `TMPDIR` when it is not).
- Network access to the npm registry for the install and for `npm audit signatures`.

No credential is needed.
`npm` and promptfoo both start under `env -i` with only the variables `run.sh` names, an empty home directory and no setting of the caller, so neither sees a credential the caller's environment or npm configuration holds.

## What the replay refuses

The command stops with one line on stderr, before the install, when any of these holds.

- A file under `skills/story-to-done/evals/` differs from `HEAD`: the replay would be of no commit.
- A run record is not one the suite wrote: not JSON, a field missing, a grade file the suite does not name, or a call record that is missing.
- No record with outcome `pass` can be replayed, which the retry probe needs.

A graded record is listed in `compare.md` as not replayed, with no parity claimed, when the suite redacted text the grader reads or when the case's grader or the scenario's fixtures changed after the commit that added the record.

## Files

| File | What it is |
|---|---|
| `run.sh` | The single command: prerequisites, pinned install, signature check, replay, probes, report. |
| `promptfooconfig.yaml` | The promptfoo configuration: one script provider, one `python` assertion. |
| `provider.py` | The script provider: rebuilds one recorded run's directory from the committed record. |
| `grade.py` | The assertion: runs the case's `grader.py`, unchanged, on the rebuilt run. |
| `records.py` | What the three scripts share: reading a run record and the rules for one the replay can use. |
| `compare.py` | Lists the records for promptfoo, checks promptfoo's export and writes the two generated files. |
| `selftest.py` | Checks the replay's own checks without promptfoo: `python3 spikes/SKL-312/poc/selftest.py`. |
| `compare.md` | Generated: one row per recorded run, the verdict mapping table, unmapped tokens. |
| `provider-contract/envelope.json` | Generated: one provider invocation's arguments, input shape and environment variable names. |

## What no job runs

No CI job runs `run.sh` or `selftest.py`.
The story keeps every tracked change under `spikes/SKL-312/`, and the repository's test job collects `tests/` only, so both are run by hand.
`run.sh` exits 1 when a generated file comes out different from the committed one, so a stale `compare.md` or `envelope.json` is found by the next run.

## What stays out of the repository

`run.sh` installs promptfoo with `npm install --prefix` into a temporary directory and points `PROMPTFOO_CONFIG_DIR`, `HOME`, `TMPDIR` and the npm cache at the same directory.
The `node_modules` tree, promptfoo's database, its logs, its result files and the rebuilt run directories all live there.
The directory is removed when the command exits 0.
When it does not, the install is removed and whatever the replay wrote is kept, with its path printed: promptfoo's export and log, the provider's log and the rebuilt runs, which hold recorded run content.
