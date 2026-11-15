# SKL-312 replay comparison: qa-unfinished-own-steps

Written by `bash spikes/SKL-312/poc/run.sh`; never edited by hand.
It holds run ids, verdicts and counts only.

- promptfoo version: 0.125.1
- Commit of `skills/story-to-done/evals/` replayed (the last commit that changed it): `192070793c871937e817be1c8f4105af8650a01a`
- Suite run records replayed: 24, of which graded: 24
- Replayed runs that match their recorded verdict: 24 of 24
- Recorded runs listed and not replayed: 86 (see the last section); no parity is claimed for them

## Zero model API calls

- Providers in the eval, from promptfoo's export: `exec: python3 provider.py`, a local script.
- Assertion types in the eval: `python`, none model-graded.
- promptfoo's own count for the eval: 0 tokens, cost 0.
- `run.sh` starts promptfoo with `env -i`, so no provider credential reaches it.
  The variable names the provider script saw: `HOME`, `LANG`, `PATH`, `PROMPTFOO_CACHE_ENABLED`, `PROMPTFOO_CONFIG_DIR`, `PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION`, `PROMPTFOO_DISABLE_REMOTE_GENERATION`, `PROMPTFOO_DISABLE_SHARING`, `PROMPTFOO_DISABLE_TELEMETRY`, `PROMPTFOO_DISABLE_UPDATE`, `SKL312_WORK`.

## Replayed runs

One row per suite run record under `skills/story-to-done/evals/qa-unfinished-own-steps/results/`.
The recorded verdict is the record's `outcome` and, in brackets, each grade `grader.py` gave when the suite ran.
The promptfoo verdict is what promptfoo reported after `grade.py` ran the committed `grader.py` on the rebuilt run.
The mapped outcome is the promptfoo outcome the mapping table gives the recorded outcome.
Grader output compares each rebuilt grade file with the lines the record kept.

| Run id | `grader.py` verdict (recorded) | promptfoo verdict | Mapped outcome | Grader output | Match |
|---|---|---|---|---|---|
| `deepseek-v4-pro-baseline-7a6cb17-new-round-7a6cb17-harness-e46615c-1` | pass (new-round: pass, new-round-read: pass) | PASS (new-round: pass, new-round-read: pass) | PASS | identical | yes |
| `deepseek-v4-pro-baseline-7a6cb17-new-round-7a6cb17-harness-e46615c-2` | pass (new-round: pass, new-round-read: pass) | PASS (new-round: pass, new-round-read: pass) | PASS | identical | yes |
| `deepseek-v4-pro-baseline-7a6cb17-new-round-7a6cb17-harness-e46615c-3` | pass (new-round: pass, new-round-read: pass) | PASS (new-round: pass, new-round-read: pass) | PASS | identical | yes |
| `deepseek-v4-pro-baseline-7a6cb17-own-steps-7a6cb17-harness-e46615c-1` | fail (own-steps: fail) | FAIL (own-steps: fail) | FAIL | identical | yes |
| `deepseek-v4-pro-baseline-7a6cb17-own-steps-7a6cb17-harness-e46615c-2` | fail (own-steps: fail) | FAIL (own-steps: fail) | FAIL | identical | yes |
| `deepseek-v4-pro-baseline-7a6cb17-own-steps-7a6cb17-harness-e46615c-3` | fail (own-steps: fail) | FAIL (own-steps: fail) | FAIL | identical | yes |
| `deepseek-v4-pro-baseline-7a6cb17-owner-action-7a6cb17-harness-e46615c-1` | pass (owner-action: pass) | PASS (owner-action: pass) | PASS | identical | yes |
| `deepseek-v4-pro-baseline-7a6cb17-owner-action-7a6cb17-harness-e46615c-2` | pass (owner-action: pass) | PASS (owner-action: pass) | PASS | identical | yes |
| `deepseek-v4-pro-baseline-7a6cb17-owner-action-7a6cb17-harness-e46615c-3` | pass (owner-action: pass) | PASS (owner-action: pass) | PASS | identical | yes |
| `deepseek-v4-pro-baseline-7a6cb17-read-back-7a6cb17-harness-e46615c-1` | fail (read-back: fail) | FAIL (read-back: fail) | FAIL | identical | yes |
| `deepseek-v4-pro-baseline-7a6cb17-read-back-7a6cb17-harness-e46615c-2` | fail (read-back: fail) | FAIL (read-back: fail) | FAIL | identical | yes |
| `deepseek-v4-pro-baseline-7a6cb17-read-back-7a6cb17-harness-e46615c-3` | fail (read-back: fail) | FAIL (read-back: fail) | FAIL | identical | yes |
| `deepseek-v4-pro-candidate-4f0eb79-new-round-4f0eb79-harness-e46615c-1` | fail (new-round: pass, new-round-read: fail) | FAIL (new-round: pass, new-round-read: fail) | FAIL | identical | yes |
| `deepseek-v4-pro-candidate-4f0eb79-new-round-4f0eb79-harness-e46615c-2` | pass (new-round: pass, new-round-read: pass) | PASS (new-round: pass, new-round-read: pass) | PASS | identical | yes |
| `deepseek-v4-pro-candidate-4f0eb79-new-round-4f0eb79-harness-e46615c-3` | fail (new-round: pass, new-round-read: fail) | FAIL (new-round: pass, new-round-read: fail) | FAIL | identical | yes |
| `deepseek-v4-pro-candidate-4f0eb79-own-steps-4f0eb79-harness-e46615c-1` | pass (own-steps: pass) | PASS (own-steps: pass) | PASS | identical | yes |
| `deepseek-v4-pro-candidate-4f0eb79-own-steps-4f0eb79-harness-e46615c-2` | pass (own-steps: pass) | PASS (own-steps: pass) | PASS | identical | yes |
| `deepseek-v4-pro-candidate-4f0eb79-own-steps-4f0eb79-harness-e46615c-3` | pass (own-steps: pass) | PASS (own-steps: pass) | PASS | identical | yes |
| `deepseek-v4-pro-candidate-4f0eb79-owner-action-4f0eb79-harness-e46615c-1` | pass (owner-action: pass) | PASS (owner-action: pass) | PASS | identical | yes |
| `deepseek-v4-pro-candidate-4f0eb79-owner-action-4f0eb79-harness-e46615c-2` | pass (owner-action: pass) | PASS (owner-action: pass) | PASS | identical | yes |
| `deepseek-v4-pro-candidate-4f0eb79-owner-action-4f0eb79-harness-e46615c-3` | pass (owner-action: pass) | PASS (owner-action: pass) | PASS | identical | yes |
| `deepseek-v4-pro-candidate-4f0eb79-read-back-4f0eb79-harness-e46615c-1` | fail (read-back: fail) | FAIL (read-back: fail) | FAIL | identical | yes |
| `deepseek-v4-pro-candidate-4f0eb79-read-back-4f0eb79-harness-e46615c-2` | fail (read-back: fail) | FAIL (read-back: fail) | FAIL | identical | yes |
| `deepseek-v4-pro-candidate-4f0eb79-read-back-4f0eb79-harness-e46615c-3` | fail (read-back: fail) | FAIL (read-back: fail) | FAIL | identical | yes |

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
| retry (behaviour) | a void attempt is run again until the scenario has N graded runs or 2N attempts | `promptfoo eval --retry-errors` runs the ERROR rows of the latest eval again, once per invocation | `probe:void-once` |

## Mapping probes

No committed record is void or broken, so three provider probes exercise those exit statuses.
They replay no case content and are not recorded runs.
The first column of outcomes is from one eval of the probes, the second from `promptfoo eval --retry-errors` on that eval.

| Probe | Provider exit status | promptfoo outcome | After `--retry-errors` | As mapped |
|---|---|---|---|---|
| `probe:void` | 2 every call | ERROR | ERROR | yes |
| `probe:exit-3` | 3 every call | ERROR | ERROR | yes |
| `probe:void-once:deepseek-v4-pro-baseline-7a6cb17-new-round-7a6cb17-harness-e46615c-1` | 2 on the first call, then replays the run | ERROR | PASS | yes |

## Unmapped tokens (blockers)

- `error`: promptfoo has one ERROR outcome, so a broken attempt and a void run land on the same outcome and the eval does not stop.
  Telling them apart, and stopping without a summary, stays with a wrapper that reads the provider's exit status.
- retry: promptfoo has no rule that runs a void attempt again until N graded runs with a cap of 2N attempts.
  `--retry-errors` is one more pass over the ERROR rows per invocation, so the count and the cap stay with a wrapper.

## Recorded runs not replayed

These records predate the suite runner, and the eval README keeps them as history.
A file holds several runs as call lines and one grade line each, with no run record: no scenario name, no grader inputs and no session ledger.
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
