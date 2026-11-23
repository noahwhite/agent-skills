# SKL-406 QA evidence, round 3

Verification path: `no-deployment`.
Target: [`82036d92507b17663d5dd13cc85dcfcca3a24fbd`](https://github.com/noahwhite/agent-skills/commit/82036d92507b17663d5dd13cc85dcfcca3a24fbd) on `main`, from [the implementation PR](https://github.com/noahwhite/agent-skills/pull/407).
Raw assertions and the 2026-11-23 product-owner ruling are on the SKL-406 tracker issue.
No deployment, fixtures or screenshots apply.

| Item | Verdict | Evidence |
| --- | --- | --- |
| AC1: budget and binding | Verified | The hunt dossier gives candidate, search, path, 40-command and stop limits; existing binding fields remain and only the hunt adds prompt identity. |
| AC2: pinning | Verified | The tests compare both generated budget blocks to independent sentence and count pins; all 28 focused tests passed on the target. |
| AC3: before and after | Owner ruled met; QA amendment pending | The [paired measurement and finding inventory](https://github.com/noahwhite/agent-skills/pull/407) show peak context fell from 156,570 to 114,144 (-27.1%) and shell calls fell from 62 to 27; the PR names and explains B1, B3 and B4. Earlier QA rounds reproduced the metrics from the session store. The 2026-11-23 ruling accepts the disclosed losses without amending the criterion. |
| AC4: acceptance contract | Verified | The merged diff preserves the existing marker, artifact, flags and predecessor logic; focused cases cover exit 13 for changed prompt inputs, legacy stamp rejection and the empty-list round trip. |
| AC5: arbitration | Verified | Tests confirm the note reads the accepted hunt stamp, names the budget in both modes and does not treat unchecked work as coverage. |
| AC6: guards | Verified | Vendor check and lint passed locally at the target; lint, pytest, private leak scan, skill validation and OpenCode discovery passed in [squash CI](https://github.com/noahwhite/agent-skills/actions/runs/45129937654). |
| DoD: all acceptance criteria met | Pending | QA requires a dated amendment to close AC3 after an ambiguous reading. |
| DoD: unit/integration tests written and passing | Verified on the local run only | [Review of record](https://github.com/noahwhite/agent-skills/pull/407#pullrequestreview-6017668240) records 3,995 local passes at reviewed head `834e716bd213c0cf77fe774898c181484e1d0d7b` (tree `fac9827637f459e6060bab15a30f0a8ef2888726`). [PR CI](https://github.com/noahwhite/agent-skills/actions/runs/45126048457/job/137530507319) passed 4,030 tests on test-merge commit `82efd9f680636815fa98478798ae76b298ccf57a` (tree `659ecd788d124ab10471873a3a7b9fc19b0bbee7`), which matches the squash tree but not the reviewed head. No exact-head or identical-tree CI coverage is claimed. |
| DoD: independently reviewed | Verified | The [review of record](https://github.com/noahwhite/agent-skills/pull/407#pullrequestreview-6017668240) covers the final implementation head and clears both Low findings. |
| DoD: docs updated | Verified | The merged skill documents the exploration budget, unchecked outcomes and prompt identity. |
| DoD: verified in a deployed environment | Correct by design | The repository deploys nothing; the merged commit is the target. |
| DoD: no critical bugs/regressions | Verified | The last pre-PR gate had no confirmed Critical, final review has no unresolved issue, and target CI passed. |

No incidental product defect was found.
