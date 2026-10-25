# SKL-20 QA evidence

Date: 2026-10-25 UTC, independent QA round 2.
Story: SKL-20 - fail fast when an adversarial gate model is rate limited or unavailable.
Build under test: `0f4c33a41b1b2f37212039e614b10201a3d8008f`, the squash merge of the de-flake PR.
That build contains the story's implementation (`9cfaa75532c52500e6a70ce1e6ec3bcf5ed322cb`, PR 45), the AC4 completion-line fix (`ee3c1750400445b03cedd5ffd34d49ee0a2a83bb`, PR 57) and the test-only de-flake (`0f4c33a41b1b2f37212039e614b10201a3d8008f`, PR 58).
This round supersedes the round-1 record that failed AC4 at `9cfaa755`; the round-1 case is re-run here as the AC4 regression probe.
Environment: a fresh clone of `origin/main` at the build SHA, then a detached checkout at that commit.
This repository ships no running service, has no `develop` branch and no deploy workflow, so `main` is the integration point and the exact-build CI run on it is the deployed-build equivalent.
CI: run 40199189000 on `0f4c33a41b1b2f37212039e614b10201a3d8008f`, `checks` and `discovery` successful, repository tests 552 passed in 94.56s.

Fixtures: one throwaway Git repository with a base commit on `main` and one commit ahead on the head branch, a passing preflight run with `--test-cmd true`, and fake shell agents and probes passed through `--agent-cmd` and `--probe-cmd`.
No provider, portal, billing or production request was made and no credential was used.
The probes drive the delivered `run-adversarial-pipeline.sh` as a caller would, with a transient scratch directory per phase.
There is no visual surface, so the evidence is structured CLI assertions and raw stdout and stderr; no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1 | Verified | A probe exiting 7 with a rate-limit line, a probe printing an authentication failure with exit 0, and a probe outliving `--probe-timeout 2` each exit 20 before the agent runs, naming the phase, the supplied model id, the probe's exit code or timeout, and the output tail. A passing probe runs with stdin on `/dev/null` in a fresh empty `probe.<phase>.*` directory under the run scratch (not the checkout) and receives the model through `{model}` and `ADVERSARIAL_PROBE_MODEL`. No probe configured records `availability check: not configured`. `AC1-assertions.txt` attached to SKL-20 |
| AC2 | Verified | A failing agent prints the phase, its exit code, the model id and the last 40 lines of `${phase}-agent.err` and `${phase}-agent.log`, and the provider-error line appears verbatim past the tail window. An empty report, a report not starting with `REVIEW-RAN: yes`, a sandbox error on stderr and a changed primary checkout still exit 15, 17, 17 and 18 with no stamp, and `record` diagnoses a rejected report the same way. `AC2-assertions.txt` attached to SKL-20 |
| AC3 | Verified | `--timeout 3` against an agent that spawns a child exits 19, names the phase, the model id and the 3s deadline, and the recorded child pid is dead after the phase returns. The exit codes present in the script are unchanged from the pre-story commit except for the added 19 and 20. `AC3-assertions.txt` attached to SKL-20 |
| AC4 | Verified | A 25s successful agent prints heartbeat lines at 1s, 11s and 21s carrying phase, elapsed, timeout and availability state, then exactly one completion line `phase=sweep complete elapsed=25s model=qa/echo-model exit=0`; the artifact's first line remains `REVIEW-RAN: yes` and carries no progress line. The round-1 failing case, a delayed authentication failure, now exits 15 with exactly one completion line `phase=sweep complete elapsed=3s model=qa/failure-completion exit=15` printed after the diagnosis. `AC4-assertions.txt` attached to SKL-20 |
| AC5 | Verified | A phase whose model cannot run exits 15 with the requested model id and the reason, is unstamped, and the successor phase is refused with exit 13 instead of running on a substitute. `profile/schema.json` still defines no fallback key and the change adds no model, provider or reviewer substitution. `AC5-assertions.txt` attached to SKL-20 |
| AC6 | Verified | The delivered `tests/test_pipeline_failfast.py` drives `run` and `record` with fake agents and probes for every case AC6 lists, asserting the exit code, the message and the absence of a stamp. The AC4 regression test reproduces the round-1 failing command and pins one completion line with a non-zero elapsed time, the model id and `exit=15`, and a failure table pins the completion line and the exact exit status for 15, 17, 19 and 20. `AC6-assertions.txt` attached to SKL-20 |
| AC7 | Verified | The script's usage header, `skills/adversarial-review-pipeline/SKILL.md`, `shared/runtimes.md` (Models) and `shared/code-review.md` (Automated pre-PR gates) document the availability check, the stream-surfacing requirement, the timeout and its exit code, the progress and completion lines and the no-substitution rule. `scripts/vendor_shared.py --check` exits 0, so every vendored copy is current. `AC7-assertions.txt` attached to SKL-20 |
| DoD1: all acceptance criteria met | Verified | Every AC above is verified at the build under test, including AC4 against the round-1 failing case. `DoD-assertions.txt` attached to SKL-20 |
| DoD2: tests written and passing | Verified | The exact-build CI run on `0f4c33a` reports 552 passed, including the delivered failure-mode suite. `DoD-assertions.txt` attached to SKL-20 |
| DoD3: independently reviewed | Verified | Each implementation PR carries a review of record whose `commit_id` equals its head: PR 45 at `c3150743309b122fc24deb22068b1c0b7963cc5b`, PR 57 at `034ec46d000b01e7bb77051b1ba53c99d6f39099`, PR 58 at `5f794aead0db93e2c8ce7ba5c849911c29d688f3`. `DoD-assertions.txt` attached to SKL-20 |
| DoD4: docs updated | Verified | The four required documentation sources are updated and the vendored references are current, per AC7. `AC7-assertions.txt` attached to SKL-20 |
| DoD5: verified in a deployed environment, if needed | Not applicable, correct by design | This repository deploys nothing: only `ci.yml` exists, there is no `develop` branch and no deploy workflow, so `main` is the integration point and the exact-build CI run on the tested commit is the deployed-build equivalent. `DoD-assertions.txt` attached to SKL-20 |
| DoD6: no critical bugs or regressions | Verified in tested scope | Success, the failure exits 13, 15, 17, 18, 19 and 20, and the probe paths were exercised with no critical defect or regression observed. `DoD-assertions.txt` attached to SKL-20 |

Reproduction: clone `noahwhite/agent-skills` at `0f4c33a41b1b2f37212039e614b10201a3d8008f`, create a throwaway Git repository with one commit on `main` and one commit ahead, and run `run-adversarial-pipeline.sh preflight --base main --test-cmd true --scratch <dir>` in it.
Then run `run sweep --base main --model <id> --agent-cmd "<fake agent template>" --scratch <dir>`, adding `--probe-cmd "<fake probe template>"` on the probe cases; both templates are quoted verbatim in the per-item assertion files attached to SKL-20, and `--agent-cmd` is required, so a phase without it is refused with exit 2 before the attempt starts.
The permissions, isolation and `/dev/null` stdin facts come from a probe that prints `readlink /proc/self/fd/0`, `$PWD`, its own directory entry count and whether its path is under the checkout.

Closing decision: every AC and DoD item is verified, so the story moves to Done once this evidence PR merges.
The evidence-only diff changes this file alone.
