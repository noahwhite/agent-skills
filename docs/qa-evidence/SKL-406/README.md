# SKL-406 QA evidence, round 4

Verification path: `no-deployment`.
Target: [`82036d92507b17663d5dd13cc85dcfcca3a24fbd`](https://github.com/noahwhite/agent-skills/commit/82036d92507b17663d5dd13cc85dcfcca3a24fbd) on `main`, from [the implementation PR](https://github.com/noahwhite/agent-skills/pull/407).
See the round 4 QA evidence comment (`27fda9f4`) and its assertion attachment on Linear story SKL-406.
No deployment, fixtures or screenshots apply.

| Item | Verdict | Evidence |
| --- | --- | --- |
| AC1: budget and binding | Verified | The hunt dossier gives candidate, search, path, 40-command and stop limits; existing binding fields remain and only the hunt adds prompt identity. |
| AC2: pinning | Verified | The tests compare both generated budget blocks to independent sentence and count pins; all 28 focused tests passed on the target. |
| AC3: before and after | Verified | The [paired measurement and finding inventory](https://github.com/noahwhite/agent-skills/pull/407) show peak context fell from 156,570 to 114,144 (-27.1%) and shell calls fell from 62 to 27; the PR names and explains B1, B3 and B4. Earlier QA rounds reproduced the metrics from the session store. On 2026-11-23 the owner said, "I rule AC3 is met", accepting those disclosed losses under AC3 as written (Linear comment `587a1fa2`). |
| AC4: acceptance contract | Verified | The merged diff preserves the existing marker, artifact, flags and predecessor logic; focused cases cover exit 13 for changed prompt inputs, legacy stamp rejection and the empty-list round trip. |
| AC5: arbitration | Verified | Tests confirm the note reads the accepted hunt stamp, names the budget in both modes and does not treat unchecked work as coverage. |
| AC6: guards | Verified | Vendor check and lint passed locally at the target; lint, pytest, private leak scan, skill validation and OpenCode discovery passed in [squash CI](https://github.com/noahwhite/agent-skills/actions/runs/45129937654). |
| DoD: all acceptance criteria met | Verified | All six acceptance criteria are met. |
| DoD: unit/integration tests written and passing | Verified | The [implementation review of record](https://github.com/noahwhite/agent-skills/pull/407#pullrequestreview-6017668240) records 3,995 local passes at reviewed head `834e716bd213c0cf77fe774898c181484e1d0d7b` (tree `fac9827637f459e6060bab15a30f0a8ef2888726`). [PR CI](https://github.com/noahwhite/agent-skills/actions/runs/45126048457/job/137530507319) passed 4,030 tests on test-merge commit `82efd9f680636815fa98478798ae76b298ccf57a` (tree `659ecd788d124ab10471873a3a7b9fc19b0bbee7`), which matches the squash tree but not the reviewed head. The general rule requires both signals when `tests/` changes, and no CI run is credited to the reviewed head. For SKL-406 only the owner directed QA to close this item on the reviewed-head local result alone. |
| DoD: independently reviewed | Verified | The [review of record](https://github.com/noahwhite/agent-skills/pull/407#pullrequestreview-6017668240) covers the final implementation head and clears both Low findings. |
| DoD: docs updated | Verified | The merged skill documents the exploration budget, unchecked outcomes and prompt identity. |
| DoD: verified in a deployed environment | Correct by design | The repository deploys nothing; the merged commit is the target. |
| DoD: no critical bugs/regressions | Verified | The last pre-PR gate had no confirmed Critical, final review has no unresolved issue, and target CI passed. |

Round 1 recorded the measurements and the open AC3 interpretation (Linear comment `0709c119`).
Round 2 reproduced the measurements and applied the AC3 ruling, but retained the CI coverage gap (Linear comment `ec54f29f`).
Round 3 documented the local-only test basis and left AC3 pending on process grounds; round 4 follows the owner's direction to apply the existing ruling without rewording AC3.
No incidental product defect was found.
