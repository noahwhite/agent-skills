# SKL-312 replay comparison: qa-unfinished-own-steps

Written by `bash spikes/SKL-312/poc/run.sh`; never edited by hand.
It holds run ids, verdicts and counts only.

- promptfoo version: 0.125.1
- Commit of `skills/story-to-done/evals/` replayed (the last commit that changed it; nothing under it was uncommitted): `8a099a8181d21d9a2bc9ab10ae32eec15fc90935`
- Suite run records: 24, of which graded: 24, replayed: 24
- Replayed runs that match their recorded verdict: 24 of 24
- Mapping probes that landed as mapped: 3 of 3
- Recorded runs listed and not replayed: 0 suite run records, and from before the runner 83 runs with 85 grade lines in call records and 1 kept in prose only (see the last section); no parity is claimed for them

## Zero model API calls

The report is written only when promptfoo's export of each of the three evals (the replay, the probes, the probes retried) says all of this.

- The only provider: `exec: python3 provider.py`, the script in this directory.
- The only assertion type: `python`, which runs `grade.py` and is not model-graded.
- promptfoo's own count: 0 tokens, and no result with a cost.
- `run.sh` starts promptfoo with `env -i`, so no provider credential reaches it.
  The variable names the provider script saw: `HOME`, `LANG`, `PATH`, `PROMPTFOO_CACHE_ENABLED`, `PROMPTFOO_CONFIG_DIR`, `PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION`, `PROMPTFOO_DISABLE_REMOTE_GENERATION`, `PROMPTFOO_DISABLE_SHARING`, `PROMPTFOO_DISABLE_TELEMETRY`, `PROMPTFOO_DISABLE_UPDATE`, `SKL312_WORK`, `TMPDIR`.

## Replayed runs

One row per suite run record under `skills/story-to-done/evals/qa-unfinished-own-steps/results/`.
The recorded verdict is the record's `outcome` and, in brackets, each grade `grader.py` gave when the suite ran.
The promptfoo verdict is what promptfoo reported after `grade.py` ran the committed `grader.py` on the rebuilt run.
The mapped outcome is the promptfoo outcome the mapping table gives the recorded outcome.
Grader output compares each rebuilt grade file with the lines the record kept: `identical` is line for line, with a placeholder the suite wrote standing for any text.
The verdict is checked apart from that text, grade by grade.
Placeholders names each kind the suite wrote into the grader inputs or the call record; the replay grades that text as committed.

The grader and the scenario fixtures a run is graded with are the committed ones.
A record names the harness commit it was graded at and carries no hash of the grader or the fixtures; the replayed records name `e46615c471d7bdd2c09a8ffeebaa5fdf9540b44f`.
The replay compares the grader and the fixtures with the commit that added the record and, where the clone holds it, with that harness commit, and lists a record as not replayed when either differs.
A harness commit of a squash-merged branch is on no branch, so a clone holds it only once it is fetched by id.
Without it the match is with the tree at the commit that added the record, which is then taken, not shown, to be the tree the suite graded with.

| Run id | `grader.py` verdict (recorded) | promptfoo verdict | Mapped outcome | Grader output | Placeholders | Match |
|---|---|---|---|---|---|---|
| `deepseek-v4-pro-baseline-7a6cb17-new-round-7a6cb17-harness-e46615c-1` | pass (new-round: pass, new-round-read: pass) | PASS (new-round: pass, new-round-read: pass) | PASS | identical | `{run_dir}` | yes |
| `deepseek-v4-pro-baseline-7a6cb17-new-round-7a6cb17-harness-e46615c-2` | pass (new-round: pass, new-round-read: pass) | PASS (new-round: pass, new-round-read: pass) | PASS | identical | `{run_dir}` | yes |
| `deepseek-v4-pro-baseline-7a6cb17-new-round-7a6cb17-harness-e46615c-3` | pass (new-round: pass, new-round-read: pass) | PASS (new-round: pass, new-round-read: pass) | PASS | identical | `{run_dir}` | yes |
| `deepseek-v4-pro-baseline-7a6cb17-own-steps-7a6cb17-harness-e46615c-1` | fail (own-steps: fail) | FAIL (own-steps: fail) | FAIL | identical | `{run_dir}` | yes |
| `deepseek-v4-pro-baseline-7a6cb17-own-steps-7a6cb17-harness-e46615c-2` | fail (own-steps: fail) | FAIL (own-steps: fail) | FAIL | identical | none | yes |
| `deepseek-v4-pro-baseline-7a6cb17-own-steps-7a6cb17-harness-e46615c-3` | fail (own-steps: fail) | FAIL (own-steps: fail) | FAIL | identical | none | yes |
| `deepseek-v4-pro-baseline-7a6cb17-owner-action-7a6cb17-harness-e46615c-1` | pass (owner-action: pass) | PASS (owner-action: pass) | PASS | identical | none | yes |
| `deepseek-v4-pro-baseline-7a6cb17-owner-action-7a6cb17-harness-e46615c-2` | pass (owner-action: pass) | PASS (owner-action: pass) | PASS | identical | none | yes |
| `deepseek-v4-pro-baseline-7a6cb17-owner-action-7a6cb17-harness-e46615c-3` | pass (owner-action: pass) | PASS (owner-action: pass) | PASS | identical | none | yes |
| `deepseek-v4-pro-baseline-7a6cb17-read-back-7a6cb17-harness-e46615c-1` | fail (read-back: fail) | FAIL (read-back: fail) | FAIL | identical | none | yes |
| `deepseek-v4-pro-baseline-7a6cb17-read-back-7a6cb17-harness-e46615c-2` | fail (read-back: fail) | FAIL (read-back: fail) | FAIL | identical | none | yes |
| `deepseek-v4-pro-baseline-7a6cb17-read-back-7a6cb17-harness-e46615c-3` | fail (read-back: fail) | FAIL (read-back: fail) | FAIL | identical | `{run_dir}` | yes |
| `deepseek-v4-pro-candidate-4f0eb79-new-round-4f0eb79-harness-e46615c-1` | fail (new-round: pass, new-round-read: fail) | FAIL (new-round: pass, new-round-read: fail) | FAIL | identical | `{run_dir}` | yes |
| `deepseek-v4-pro-candidate-4f0eb79-new-round-4f0eb79-harness-e46615c-2` | pass (new-round: pass, new-round-read: pass) | PASS (new-round: pass, new-round-read: pass) | PASS | identical | `{run_dir}` | yes |
| `deepseek-v4-pro-candidate-4f0eb79-new-round-4f0eb79-harness-e46615c-3` | fail (new-round: pass, new-round-read: fail) | FAIL (new-round: pass, new-round-read: fail) | FAIL | identical | `{run_dir}` | yes |
| `deepseek-v4-pro-candidate-4f0eb79-own-steps-4f0eb79-harness-e46615c-1` | pass (own-steps: pass) | PASS (own-steps: pass) | PASS | identical | `{run_dir}` | yes |
| `deepseek-v4-pro-candidate-4f0eb79-own-steps-4f0eb79-harness-e46615c-2` | pass (own-steps: pass) | PASS (own-steps: pass) | PASS | identical | none | yes |
| `deepseek-v4-pro-candidate-4f0eb79-own-steps-4f0eb79-harness-e46615c-3` | pass (own-steps: pass) | PASS (own-steps: pass) | PASS | identical | none | yes |
| `deepseek-v4-pro-candidate-4f0eb79-owner-action-4f0eb79-harness-e46615c-1` | pass (owner-action: pass) | PASS (owner-action: pass) | PASS | identical | none | yes |
| `deepseek-v4-pro-candidate-4f0eb79-owner-action-4f0eb79-harness-e46615c-2` | pass (owner-action: pass) | PASS (owner-action: pass) | PASS | identical | none | yes |
| `deepseek-v4-pro-candidate-4f0eb79-owner-action-4f0eb79-harness-e46615c-3` | pass (owner-action: pass) | PASS (owner-action: pass) | PASS | identical | none | yes |
| `deepseek-v4-pro-candidate-4f0eb79-read-back-4f0eb79-harness-e46615c-1` | fail (read-back: fail) | FAIL (read-back: fail) | FAIL | identical | `{run_dir}` | yes |
| `deepseek-v4-pro-candidate-4f0eb79-read-back-4f0eb79-harness-e46615c-2` | fail (read-back: fail) | FAIL (read-back: fail) | FAIL | identical | none | yes |
| `deepseek-v4-pro-candidate-4f0eb79-read-back-4f0eb79-harness-e46615c-3` | fail (read-back: fail) | FAIL (read-back: fail) | FAIL | identical | none | yes |

## Mismatches

None.

## Verdict mapping

Every token `suite.py` can record, and the behaviour it attaches to a void run.

| Harness token | The harness emits it when | promptfoo outcome | Observed here |
|---|---|---|---|
| `pass` (outcome) | `run.sh` exits 0 | PASS: `success` true, `failureReason` 0 | 13 recorded runs |
| `fail` (outcome) | `run.sh` exits 1 | FAIL: `success` false, `failureReason` 1 (assertion) | 11 recorded runs |
| `pass` or `fail` (a grade in `verdicts`) | a grade file ends in `PASS` or not | named score 1 or 0 under the grade's name | 30 recorded grades |
| `void` (outcome) | `run.sh` exits 2, or the attempt passes its deadline | ERROR: `success` false, `failureReason` 2, counted under `errors` | 0 recorded runs; `probe:void` for exit 2; the deadline is not exercised |
| `error` (outcome) | any other exit status, or grade files that contradict it; the suite stops | ERROR, the same outcome as `void`, and the eval goes on | 0 recorded runs; `probe:exit-3` |
| retry (behaviour) | a void attempt is run again until the scenario has N graded runs or 2N attempts | none: `promptfoo eval --retry-errors` runs the ERROR rows of the latest eval again, once per invocation | `probe:void-once` |

## Mapping probes

No committed record is void or broken, so three provider probes exercise those exit statuses.
They replay no case content and are not recorded runs.
The exit statuses are the ones the provider logged, one per call: the first eval, then `promptfoo eval --retry-errors` on that eval.
The two outcome columns are promptfoo's after each.

| Probe | The provider | Exit statuses logged | promptfoo outcome | After `--retry-errors` | As mapped |
|---|---|---|---|---|---|
| `probe:void` | exits 2 on every call | 2, 2 | ERROR | ERROR | yes |
| `probe:exit-3` | exits 3 on every call | 3, 3 | ERROR | ERROR | yes |
| `probe:void-once:deepseek-v4-pro-baseline-7a6cb17-new-round-7a6cb17-harness-e46615c-1` | exits 2 on the first call, then replays the run | 2, 0 | ERROR | PASS | yes |

## Unmapped tokens (blockers)

- retry: promptfoo has no rule that runs a void attempt again until N graded runs with a cap of 2N attempts.
  `--retry-errors` is one more pass over the ERROR rows per invocation, so the count and the cap stay with a wrapper.

## Tokens mapped with a loss (blockers)

- `error`: it has a promptfoo outcome, ERROR, and `void` has the same one, so a broken attempt and a void run cannot be told apart in the result, and the eval does not stop.
  Telling them apart, and stopping without a summary, stays with a wrapper that reads the provider's exit status.

## Recorded runs not replayed

### Suite run records

None.

### Records that predate the suite runner

The eval README keeps these records as history.
A call file holds several runs as call lines and one grade line for each expectation a run was graded on, with no run record: no scenario name, no grader inputs and no session ledger.
Each grade came from the grader at that file's own commit, not the current one.
Replaying them would compare two graders, so they are listed and not replayed.

| Record | Run | Expectation | Recorded grade |
|---|---|---|---|
| `baseline-7a6cb17-calls.jsonl` | own-1 | - | FAIL |
| `baseline-7a6cb17-calls.jsonl` | own-2 | - | FAIL |
| `baseline-7a6cb17-calls.jsonl` | own-3 | - | FAIL |
| `baseline-7a6cb17-calls.jsonl` | owner-action | - | PASS |
| `baseline-7a6cb17-calls.jsonl` | new-round | - | PASS |
| `baseline-7a6cb17-harness-1f24df1-calls.jsonl` | own-steps-1 | own-steps | FAIL |
| `baseline-7a6cb17-harness-1f24df1-calls.jsonl` | own-steps-2 | own-steps | FAIL |
| `baseline-7a6cb17-harness-1f24df1-calls.jsonl` | own-steps-3 | own-steps | FAIL |
| `baseline-7a6cb17-harness-1f24df1-calls.jsonl` | read-back-1 | read-back | FAIL |
| `baseline-7a6cb17-harness-1f24df1-calls.jsonl` | read-back-2 | read-back | FAIL |
| `baseline-7a6cb17-harness-1f24df1-calls.jsonl` | read-back-3 | read-back | FAIL |
| `baseline-7a6cb17-harness-1f24df1-calls.jsonl` | owner-action | owner-action | PASS |
| `baseline-7a6cb17-harness-1f24df1-calls.jsonl` | new-round | new-round | PASS |
| `baseline-7a6cb17-harness-1f24df1-calls.jsonl` | new-round | new-round-read | PASS |
| `baseline-7a6cb17-harness-331a2a0-calls.jsonl` | own-steps-1 | - | FAIL |
| `baseline-7a6cb17-harness-331a2a0-calls.jsonl` | own-steps-2 | - | FAIL |
| `baseline-7a6cb17-harness-331a2a0-calls.jsonl` | own-steps-3 | - | FAIL |
| `baseline-7a6cb17-harness-331a2a0-calls.jsonl` | read-back-1 | - | FAIL |
| `baseline-7a6cb17-harness-331a2a0-calls.jsonl` | read-back-2 | - | FAIL |
| `baseline-7a6cb17-harness-331a2a0-calls.jsonl` | read-back-3 | - | FAIL |
| `baseline-7a6cb17-harness-331a2a0-calls.jsonl` | owner-action | - | PASS |
| `baseline-7a6cb17-harness-331a2a0-calls.jsonl` | new-round | - | PASS |
| `baseline-7a6cb17-harness-4a622c1-calls.jsonl` | own-1 | - | FAIL |
| `baseline-7a6cb17-harness-4a622c1-calls.jsonl` | own-2 | - | FAIL |
| `baseline-7a6cb17-harness-4a622c1-calls.jsonl` | own-3 | - | FAIL |
| `baseline-7a6cb17-harness-4a622c1-calls.jsonl` | owner-action | - | PASS |
| `baseline-7a6cb17-harness-4a622c1-calls.jsonl` | new-round | - | PASS |
| `baseline-7a6cb17-harness-b3b33ca-calls.jsonl` | own-steps-1 | - | FAIL |
| `baseline-7a6cb17-harness-b3b33ca-calls.jsonl` | own-steps-2 | - | FAIL |
| `baseline-7a6cb17-harness-b3b33ca-calls.jsonl` | own-steps-3 | - | FAIL |
| `baseline-7a6cb17-harness-b3b33ca-calls.jsonl` | read-back-1 | - | FAIL |
| `baseline-7a6cb17-harness-b3b33ca-calls.jsonl` | read-back-2 | - | FAIL |
| `baseline-7a6cb17-harness-b3b33ca-calls.jsonl` | read-back-3 | - | FAIL |
| `baseline-7a6cb17-harness-b3b33ca-calls.jsonl` | owner-action | - | PASS |
| `baseline-7a6cb17-harness-b3b33ca-calls.jsonl` | new-round | - | FAIL |
| `baseline-7a6cb17-harness-f591f0f-calls.jsonl` | own-1 | - | FAIL |
| `baseline-7a6cb17-harness-f591f0f-calls.jsonl` | own-2 | - | FAIL |
| `baseline-7a6cb17-harness-f591f0f-calls.jsonl` | own-3 | - | FAIL |
| `baseline-7a6cb17-harness-f591f0f-calls.jsonl` | owner-action | - | PASS |
| `baseline-7a6cb17-harness-f591f0f-calls.jsonl` | new-round | - | PASS |
| `candidate-1f24df1-calls.jsonl` | own-steps-1 | own-steps | PASS |
| `candidate-1f24df1-calls.jsonl` | own-steps-2 | own-steps | PASS |
| `candidate-1f24df1-calls.jsonl` | own-steps-3 | own-steps | PASS |
| `candidate-1f24df1-calls.jsonl` | read-back-1 | read-back | FAIL |
| `candidate-1f24df1-calls.jsonl` | read-back-2 | read-back | FAIL |
| `candidate-1f24df1-calls.jsonl` | read-back-3 | read-back | FAIL |
| `candidate-1f24df1-calls.jsonl` | owner-action | owner-action | PASS |
| `candidate-1f24df1-calls.jsonl` | new-round | new-round | PASS |
| `candidate-1f24df1-calls.jsonl` | new-round | new-round-read | PASS |
| `candidate-331a2a0-calls.jsonl` | own-steps-1 | - | PASS |
| `candidate-331a2a0-calls.jsonl` | own-steps-2 | - | PASS |
| `candidate-331a2a0-calls.jsonl` | own-steps-3 | - | PASS |
| `candidate-331a2a0-calls.jsonl` | read-back-1 | - | PASS |
| `candidate-331a2a0-calls.jsonl` | read-back-2 | - | PASS |
| `candidate-331a2a0-calls.jsonl` | read-back-3 | - | FAIL |
| `candidate-331a2a0-calls.jsonl` | owner-action | - | PASS |
| `candidate-331a2a0-calls.jsonl` | new-round | - | PASS |
| `candidate-4a622c1-calls.jsonl` | own-1 | - | PASS |
| `candidate-4a622c1-calls.jsonl` | own-2 | - | PASS |
| `candidate-4a622c1-calls.jsonl` | own-3 | - | PASS |
| `candidate-4a622c1-calls.jsonl` | owner-action | - | PASS |
| `candidate-4a622c1-calls.jsonl` | new-round | - | PASS |
| `candidate-ac53428-calls.jsonl` | own-1 | - | PASS |
| `candidate-ac53428-calls.jsonl` | own-2 | - | PASS |
| `candidate-ac53428-calls.jsonl` | own-3 | - | PASS |
| `candidate-ac53428-calls.jsonl` | owner-action | - | PASS |
| `candidate-ac53428-calls.jsonl` | new-round | - | PASS |
| `candidate-b3b33ca-calls.jsonl` | own-steps-1 | - | PASS |
| `candidate-b3b33ca-calls.jsonl` | own-steps-2 | - | PASS |
| `candidate-b3b33ca-calls.jsonl` | own-steps-3 | - | PASS |
| `candidate-b3b33ca-calls.jsonl` | read-back-1 | - | FAIL |
| `candidate-b3b33ca-calls.jsonl` | read-back-2 | - | PASS |
| `candidate-b3b33ca-calls.jsonl` | read-back-3 | - | PASS |
| `candidate-b3b33ca-calls.jsonl` | owner-action | - | PASS |
| `candidate-b3b33ca-calls.jsonl` | new-round | - | PASS |
| `candidate-cb9d9de-calls.jsonl` | own-steps-1 | - | PASS |
| `candidate-cb9d9de-calls.jsonl` | own-steps-2 | - | PASS |
| `candidate-cb9d9de-calls.jsonl` | own-steps-3 | - | PASS |
| `candidate-cb9d9de-calls.jsonl` | owner-action | - | PASS |
| `candidate-cb9d9de-calls.jsonl` | new-round | - | PASS |
| `candidate-f591f0f-calls.jsonl` | own-1 | - | PASS |
| `candidate-f591f0f-calls.jsonl` | own-2 | - | PASS |
| `candidate-f591f0f-calls.jsonl` | own-3 | - | PASS |
| `candidate-f591f0f-calls.jsonl` | owner-action | - | PASS |
| `candidate-f591f0f-calls.jsonl` | new-round | - | PASS |
| `candidate-f5347b4.md` | - | - | in prose only |
