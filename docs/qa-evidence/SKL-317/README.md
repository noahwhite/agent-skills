# SKL-317 QA evidence

## QA round 1

Date: 2026-11-16 UTC, independent QA round 1.
Path: `spike`, selected by `select-path.py` with the label `Spike` and the recorded `path: spike` line, so no environment or build SHA applies.
Target: the deliverables the handoff note links, each a tracked file at `4fa73f50935388d026d87d807e274a017032b93e` on `main`, the squash merge of PR 306, whose reviewed head is `b7d7a5f9bfcf1e21d19980b1cb60fcc92f9921e9`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
The deliverables: `spikes/SKL-317/findings.md` and, under `spikes/SKL-317/poc/`, `run.sh`, `promptfooconfig.yaml`, `provider.py`, `README.md`, `compare.md`, `compare.py`, `grade.py`, `selftest.py` and `stub_agent.py`.
The live run in `compare.md` ran at `e653f377aca8fe9f0f84c6ba20fec72bd1966980`; its PoC scripts equal those at the target.
Fixtures: none; QA made no model call and used a throwaway spend ledger outside the repository.
The raw output is attached to SKL-317 as "SKL-317 QA round 1 assertion output"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| SC1: one live invocation through a promptfoo `0.125.1` script provider that owns the void retry, grades with the unmodified `grader.py` and writes `compare.md` | Verified | `compare.md` has one row per attempt with the exit status, outcome, promptfoo fields or `not reported`, token counts, model id and cost with price source and date, then the overall exit status 0, the commit, the version and the model id. N is 3, the cap 6, `maxConcurrency` 1 and promptfoo's own retry none. The `grader.py` blob `3a0a9947a2b05b661c316d67cfa400f726b151b7` is the same at `e653f377`, at the target and at its parent. QA recomputed all 13 attempt costs from the models.dev prices and each matches. A stub run of `run.sh` at the target exited 0 with the same report shape and left the checkout clean. |
| SC2: each `suite.py` rule stated with quoted values, observed behaviour and a status | Verified | All six quoted `suite.py` lines are present at `e653f377`. Rule (i) is `reproduced` and labelled `injected`; rules (ii) and (iii) are `not exercised in this run` and named as open questions in `## Decision`. Stub runs at the target with an all-void plan and a broken-attempt plan reproduced (ii) and (iii) with no model call. |
| SC3: re-check of every SKL-312 capability label | Verified | The 19 rows of `## Capability re-check` cover all 13 capability rows of SKL-312's table at `13486d84afe2603105b96a9b6ca7a9bd5aa7aa68`, each with method, evidence and agree or disagree. QA reproduced the documentation evidence of rows 4, 15, 16 and 17 on 2026-11-16. |
| SC4: `## Infrastructure data` as measurements only | Verified | Install method and command, Node and npm versions, package count with its definition and command, `du -sh` with the path, the supply-chain check with its exit status, and the date and machine are present, with no verdict. `npm view promptfoo@0.125.1` returns the version and the Node floor `run.sh` enforces. |
| SC5: `## Decision` | Verified | Inconclusive for behaviour and for regression, each observation citing a row, reversal conditions as observations, the limit of one behaviour scenario for regression, and the SKL-315 and SKL-316 outcomes that would change it. |
| Artifact paths and guards | Verified | The merge adds 10 files, all under `spikes/SKL-317/`; no `node_modules`, lockfile, promptfoo database, log or credential is tracked; `run.sh` pins `0.125.1` and points `PROMPTFOO_CONFIG_DIR` at a temporary directory. `findings.md` and `compare.md` hold no local path or session id. Total spend is 1.151759224 USD under the 5 USD ceiling. |
| Deliverable: findings with six sections | Verified | All six headings present. |
| Deliverable: proof of concept | Verified | All named files present; the README names `0.125.1`, the prerequisites and the environment variables without values. `selftest.py` exited 0 with 62 checks. |
| Deliverable: recommendation in `## Decision` | Verified | Inconclusive. |
| DoD: each criterion marked with evidence | Verified | `## Success criteria status` marks all five `met`, each with a file and section reference. |
| DoD: merged through a pull request, `## Guard results` complete | Verified | PR 306 merged as the target, with a review of record `COMMENTED` at `b7d7a5f9bfcf1e21d19980b1cb60fcc92f9921e9` and no findings. `## Guard results` records the four guards on `7cd9ba94`, whose CI run 43906545497 passed every step; between `7cd9ba94` and the reviewed head only `findings.md` changed. CI run 43908832525 (push to `main` at the target) passed. |
| DoD: decision comment | Verified | The Decision comment carries Inconclusive, the findings link at the target, promptfoo `0.125.1`, the model id `deepseek/deepseek-v4-pro`, N = 3 and 1.151759224 USD, with no credential. |
| DoD: decision recorded and follow-up linked | Verified | Inconclusive; the follow-up SKL-326 is in Backlog and linked to SKL-317. |

Pending owner rulings: none.

Closing decision: Done, once this evidence merges.
