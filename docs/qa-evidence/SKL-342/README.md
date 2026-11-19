# SKL-342 QA evidence

## QA round 1

Date: 2026-11-19 UTC, independent QA round 1.
Path: `no-deployment`, from the brief's recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `09b9b749d9ccb9231d3976e94491db3b8aa05467` on `main`, the squash merge of PR #361 at head `565c8b0334df1079797b2f9f2d13b8f700ccb932`, which `git merge-base --is-ancestor` confirmed on `origin/main`.
The merged tree is identical to the reviewed head.
Fixtures: one throwaway git repository holding the committed `.agent-skills/review-checklist.txt`, made and discarded by the QA probe.
The raw output is attached to SKL-342 as "SKL-342 QA round 1 assertion output"; there is no visual surface, so no screenshot applies.
The story description carries four acceptance criteria, and the accepted round 3 refinement (comment `bc6032bb`) carries nine refined criteria; both sets are verified.

| Item | Verdict | Evidence |
|---|---|---|
| Refined AC1: refinement note | Verified | Comment `bc6032bb` names the seven files read and records D1 to D12, the D4 known limit, D3 (prose gives no mapping) and D7 (owner approval cannot be proven in one pass, reworded). The PR body links it. |
| Refined AC2: checklist file | Verified | The file holds five `<bash glob> \| <review item>` items, and one "Phase 1: sweep" paragraph documents its path and format. `tests/test_review_checklist.py` passes (27 tests). |
| Refined AC3: reader | Verified | The same 27 tests pass. A QA probe of the merged script prints exactly the one mapped item for a diff touching one mapped path and 0 bytes for an unmapped diff, both with exit 0. |
| Refined AC4: sweep dossier | Verified | The QA probe's sweep dossier ends with the `===== Review checklist` heading and the item when one matches, and has no such heading when none matches. |
| Refined AC5: Retro step | Verified | The new Retro bullet reads every review of record and arbiter reports in PR bodies, counts a miss once per distinct PR, excludes scratch reports and proposes one line per miss seen in two or more PRs. `tests/test_persona_scrum_master.py` passes (22 tests). The known limit below applies. |
| Refined AC6: owner approval | Verified | The same bullet says an item enters only through an engineer PR linking the owner's approval comment on the retro issue, and the persona never adds it. The known limit below applies. |
| Refined AC7: boundary | Verified | `git diff --name-only 74a29d4...565c8b0` lists only the checklist, the two `SKILL.md` files, the pipeline script and two test files. |
| Refined AC8: size guard | Verified | Measured as the AC defines it, `wc -c` over `SKILL.md` plus every file under `references/`, at the merge base `74a29d4` and the head: `adversarial-review-pipeline` at 175081 to 175430 bytes (+0.20%) and `persona-scrum-master` at 134340 to 135181 bytes (+0.63%), as the PR body states. |
| Refined AC9: guards | Verified | CI run 44570542770 on the head concluded `success` for pytest, the leak scan with `--require-private`, `skills-ref validate` and `smoke-opencode.sh`. The local full suite was not run: owner directive, full suite deferred to the end. |
| AC: checklist file | Verified | Refined AC2, AC3 and AC4. |
| AC: retro step | Verified | Refined AC5. |
| AC: owner approval | Verified | Refined AC6. |
| AC: size guard | Verified | Refined AC8. |
| DoD: all acceptance criteria met | Verified | The rows above. |
| DoD: tests written and passing | Verified | 27 and 22 tests pass at the target, and the head's `Repository tests` step is green. |
| DoD: independently reviewed | Verified | Review of record round 12 covers `565c8b0334df1079797b2f9f2d13b8f700ccb932`, the merged head, and is clean. |
| DoD: docs updated | Verified | The "Phase 1: sweep" paragraph, the script header's "Review checklist" block and the Retro bullet. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | None found. |

Known limit outside the acceptance criteria: the Retro section still allows the cycle record to live only in a project document, while the new bullet posts proposals and the owner's approval on the retro issue, so a document-only retro has nowhere to post either.
The description AC and refined AC6 both name the retro issue, so AC5 and AC6 are met as written, and the two tests pin only the bullet's wording.
PR #361's review of record (finding 3, Medium, non-blocking) and its PR body already record this as a refinement proposal, not an AC; no tracker issue carries it yet, and its owner is the product owner.

Pending owner rulings: none.

Closing decision: Done, once this evidence merges.
