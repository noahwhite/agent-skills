# SKL-406 QA evidence, round 2

Verification path: `no-deployment`.
Target: [`82036d92507b17663d5dd13cc85dcfcca3a24fbd`](https://github.com/noahwhite/agent-skills/commit/82036d92507b17663d5dd13cc85dcfcca3a24fbd) on `main`, from [the implementation PR](https://github.com/noahwhite/agent-skills/pull/407).
The sanitized assertions are attached to the story and linked from the [round 2 QA evidence comment](https://linear.app/officina-pub/issue/SKL-406/user-story-bound-the-hunts-exploration-instead-of-its-payload#comment-ec54f29f).
No deployed environment, fixtures or screenshots apply.

| Item | Verdict | Evidence |
| --- | --- | --- |
| AC1: budget and binding | Verified | The hunt dossier gives candidate, search, path, 40-command and stop limits; the existing binding fields remain and only the hunt adds prompt identity. |
| AC2: pinning | Verified | The tests compare the complete generated budget blocks for both modes to independently pinned sentences and count. |
| AC3: before/after | Verified | Fresh reads of both session exports reproduce 156,570 to 114,144 peak context (-27.1%) and 62 to 27 shell calls; the PR explains B1, B3 and B4, and the [dated product-owner ruling](https://linear.app/officina-pub/issue/SKL-406/user-story-bound-the-hunts-exploration-instead-of-its-payload#comment-587a1fa2) accepts those disclosed losses under the unchanged criterion. |
| AC4: acceptance contract | Verified | The merged diff preserves the existing marker, artifact, flags and predecessor logic; tests cover exit 13 for changed prompt inputs, rejection of a legacy stamp, and the empty-list round trip. |
| AC5: arbitration | Verified | The note reads the accepted hunt stamp, names the budget in both modes, and tells arbitration not to count unchecked work as coverage. |
| AC6: guards | Verified | The vendor check exited 0 at the target; lint, pytest, private leak scan, skill validation and OpenCode smoke passed in [squash CI](https://github.com/noahwhite/agent-skills/actions/runs/45129937654). |
| DoD: all acceptance criteria met | Verified | AC1 through AC6 are met. |
| DoD: unit/integration tests written and passing | Not covered in full | The final implementation PR review records 3,995 local and 28 focused passes at `834e716bd213c0cf77fe774898c181484e1d0d7b`; the [PR CI checkout](https://github.com/noahwhite/agent-skills/actions/runs/45126048457/job/137530507319) passed 4,030 tests at `82efd9f680636815fa98478798ae76b298ccf57a`, whose tree matches the squash but differs from the reviewed head. |
| DoD: independently reviewed | Verified | The [review of record](https://github.com/noahwhite/agent-skills/pull/407#pullrequestreview-6017668240) covers the implementation PR's final head `834e716bd213c0cf77fe774898c181484e1d0d7b` and clears both Low findings. |
| DoD: docs updated | Verified | `skills/adversarial-review-pipeline/SKILL.md` documents the exploration budget, unchecked outcomes and prompt identity. |
| DoD: verified in a deployed environment | Correct by design | The repository deploys nothing; the merged commit is the verification target. |
| DoD: no critical bugs/regressions | Verified | The final pre-PR gate reported no confirmed Critical, the final PR review found no unresolved issue, and CI passed on the target tree. |

Engineering/CI owns the outstanding CI evidence on the reviewed head or an identical tree, because the implementation PR added a file under `tests/`.
No incidental product defect was found.
