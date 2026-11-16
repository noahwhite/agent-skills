# SKL-312 QA evidence

## QA round 1

Date: 2026-11-16 UTC, independent QA round 1.
Path: `spike`, selected by `select-path.py` with the label `Spike` and the recorded `path: spike` line, so no environment or build SHA applies.
Target: the deliverables the handoff note links, each a tracked file at `13486d84afe2603105b96a9b6ca7a9bd5aa7aa68` on `main`, the squash merge of PR 275, whose reviewed head is `39ace722cf79ab9ef24c5da458aed9553047b9b6`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
The deliverables: `spikes/SKL-312/findings.md` and, under `spikes/SKL-312/poc/`, `run.sh`, `promptfooconfig.yaml`, `provider.py`, `README.md`, `compare.md` and `provider-contract/envelope.json`.
Fixtures: the 24 committed run records of `skills/story-to-done/evals/qa-unfinished-own-steps/results/`, read as committed.
The raw output is attached to SKL-312 as "SKL-312 QA round 1 assertion output at target 13486d8"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| SC1: `## Decision` with outcome, decider, date, version, evals commit, observations, reversal conditions | Verified | `## Decision` states No-Go, names the decider by role, the date 2026-11-15, promptfoo `0.125.1`, five observations, three reversal conditions and the two missing prerequisites. `git log -1 -- skills/story-to-done/evals/` at the target returns `8a099a8181d21d9a2bc9ab10ae32eec15fc90935`, the commit `## Decision` and `compare.md` name. |
| SC2: `bash spikes/SKL-312/poc/run.sh` replays with zero model API calls and writes `compare.md` and `envelope.json` | Verified | In a fresh detached checkout of the target, `run.sh` exited 0 after installing promptfoo `0.125.1` outside the repository: the replay eval reported 13 passed and 11 failed, and the three probes landed as mapped. `git status --porcelain` stayed empty, so both generated files came out identical to the committed ones, and the temporary directory was removed. The 24 records read directly give 13 pass and 11 fail, each equal to its `compare.md` row. `compare.md` holds the run id, recorded verdict, promptfoo verdict and mapped outcome per run, the mapping table for pass, fail, grade, void, error and retry, retry as an unmapped blocker, no mismatch, and the pre-runner records listed with no parity claimed. `envelope.json` records argv, input shape and environment variable names only, none a credential. `selftest.py` exited 0 with 52 checks. |
| SC3: `## Scope` | Verified | Three first skills with a rationale each, behaviours by test-type row, and an out-of-scope list carrying SKL-273, SKL-309, SKL-310 and SKL-311. |
| SC4: `## Test types` | Verified | Four rows (trigger, behaviour, regression, prose rubric) with what each catches, grading method, promptfoo mechanism (void and retry `not supported`), and cost per run in USD at named models and list prices, model calls and seconds, each marked measured or estimated; no benchmark campaign. |
| SC5: `## Corpus` | Verified | Sources, `case.yaml` reused, labelling fields, 8 cases per first-wave skill at 5 repeats with a Wilson 95% half-width of 0.33, versioning, private material kept out through `leak_scan.py --require-private`, redaction deferred to SKL-310, no case authored. QA recomputed the half-widths (0.326 at n = 5, 0.365 at n = 3) and the flake probabilities. |
| SC6: `## Infrastructure` | Verified | Runner local with its deciding constraint and two alternatives; providers; credentials by name only; storage and retention; 25 USD per suite run and 12 runs a month with arithmetic that QA recomputed (10.22, 20.42, 300, 122.64); advisory pull request comment with a 4-of-5 flake policy; Node footprint with the pin, invocation, `npm audit signatures` (QA reproduced 617 verified signatures and 157 attestations) and telemetry and sharing disabled; labels observed, documented or unverified. |
| SC7: `## Split` | Verified | Named additional spikes, not an epic; each with a question, done condition, dependency and a timebox of 2 or 3 days; the No-Go handling of each. |
| Research questions 1 to 7 | Verified | Answered in `## Research questions` (1 with labels and documentation URLs, 2 in three parts split into proven and inferred), `## Test types`, `## Corpus`, `## Infrastructure` and `## Relations`, which gives each of the five stories a disposition, rationale and dependency. |
| Artifact paths and guards | Verified | The merged commit adds 11 files, all under `spikes/SKL-312/`; no `node_modules`, lockfile, promptfoo database, log or credential is tracked; `run.sh` pins `0.125.1` and writes promptfoo output outside the repository. |
| Deliverable: findings with nine headings and `## Guard results` | Verified | All nine headings present; `## Guard results` records the four commands, the pinned `skills-ref` reference `69ef37e9424c0a7ea9dd2293b559e43ec8176379`, each exit status and the two normalizations. |
| Deliverable: replay-only proof of concept | Verified | All six named files present at the target; the README names `0.125.1` and the prerequisites. |
| Deliverable: recommendation in `## Decision` | Verified | No-Go. |
| Deliverable: No-Go alternatives | Verified | Three, the first extending `run-suite.sh`, each with its gap and a one-line cost. |
| Deliverable: follow-up breakdown | Verified | `## Split`. |
| DoD: each criterion marked met or blocked with evidence | Verified | `## Success criteria` marks all seven met, each with an evidence reference; none is blocked. |
| DoD: merged through a pull request, four guards pass on the final state | Verified | PR 275 merged as the target, with a review of record `COMMENTED` at `39ace722cf79ab9ef24c5da458aed9553047b9b6`. CI run 43795784039 (`ci`, push to `main` at the target) passed `checks` (tests, leak scan with `--require-private`, `skills-ref validate`) and `discovery` (`scripts/smoke-opencode.sh`). At the target, `uv run --locked pytest -q` passed 2631 locally. |
| DoD: comment with decision, findings link at the merged commit and Relations | Verified | The handoff comment on SKL-312 carries the No-Go decision, the findings link at the target and the five dispositions, equal to `## Relations`, with no credential or transcript text. |
| DoD: decision made | Verified | No-Go. |
| DoD: follow-ups created in Backlog and linked | Verified | SKL-315 (2 days) and SKL-316 (3 days) are in Backlog, and SKL-312 blocks both. |

Closing decision: Done, once this evidence merges.
