# SKL-387 QA evidence

- Round: 1, 2026-11-21.
- Path: `no-deployment`.
- Target: `bb7b17c473bf702cd9ef76faca0018280a5c7433`, confirmed on fetched `origin/main` with `git merge-base --is-ancestor`.
- Implementation: https://github.com/noahwhite/agent-skills/pull/383.
- Reviewed implementation head: `ee38d3e8065b1fb5ee2ebcb80eb1a90dcbd6a802`.
- Fixtures: committed skill documents, test modules, PR records and Actions records; no accounts or deployed environment.
- Raw evidence: `SKL-387-QA-round-1-assertions.txt`, linked from SKL-387 comment whose identifier starts `12172032`.
- Per-item tracker record: SKL-387 QA evidence comment whose identifier starts `1f33125c`, available with `linear issue comment list SKL-387 --json`.

## Verdicts

Attachment section names below refer to `SKL-387-QA-round-1-assertions.txt` in the story attachment.

| Item | Verdict | Evidence |
|---|---|---|
| AC1 One green signal | Verified | `AC1.txt`: all four sentences at workflow lines 93-97, 177-181, 244-248 and story-template lines 97-101. |
| AC2 Exception and blast radius | Verified | `AC2.txt`: named path exceptions and preservation text; only two skills and two test modules changed, with workflows, dependencies and preflight implementation untouched. |
| AC3 Pins | Verified | `AC3.txt`: whole-line and location pins, CommonMark rendered-item pin, exact CI contract, fallback/exception/combined decision cases and mutation guard inspected at target. |
| AC4 Verification | Verified | `AC4.txt`: focused command/output and skill diff pasted in implementation PR; focused 20 passed; final-head local suite 3835 passed; final-head CI checks passed. |
| AC5 Guards | Verified | `AC5.txt`: lint, CI suite, private scan, skills-ref validation and forced-install discovery passed; passing `test_the_repository_vendoring_is_current` invokes `scripts/vendor_shared.py --check`. |
| DoD All acceptance criteria met | Verified | `DoD.txt`, `AC1.txt`-`AC5.txt`. |
| DoD Unit/integration tests written & passing | Verified | `AC3.txt`-`AC5.txt`: committed pins, focused output and local/CI suite records. |
| DoD Independently reviewed | Verified | `DoD3.txt`: [COMMENTED review of record](https://github.com/noahwhite/agent-skills/pull/383#pullrequestreview-6008588559) at exact implementation head, Low fixed and clean delta. |
| DoD Docs updated | Verified | `AC1.txt`: both skill documents updated at all named locations. |
| DoD Verified in a deployed environment (if needed) | Correct by design, met | `DoD.txt`: selected no-deployment path; profile declares `environments: []`. |
| DoD No critical bugs/regressions | Verified within acceptance scope | `DoD.txt`: all acceptance assertions and CI guards pass; no new incidental defect found. |

## Reproducible records

Inspect the target with `git show bb7b17c473bf702cd9ef76faca0018280a5c7433:<path>` for each path named above.
Read implementation evidence with `gh pr view 383 --repo noahwhite/agent-skills --json body,comments,reviews,headRefOid,mergeCommit`.
Read the [checks job](https://github.com/noahwhite/agent-skills/actions/runs/44955531910/job/137002651512) with `gh api repos/noahwhite/agent-skills/actions/jobs/137002651512`.
Its `Repository tests` step ran `uv run --locked pytest -q`: **3853 passed in 587.10s**.
The PR records the final implementation head's local suite as **3835 passed in 519.37s**.
CI incorporates a newer base than that local head: checkout tested synthetic merge `4f67f265c4aed21dae29d6f1d52ab27f369fc6eb`, not the head commit itself.
`gh api repos/noahwhite/agent-skills/git/commits/4f67f265c4aed21dae29d6f1d52ab27f369fc6eb` reports tree `d838fa0bdaabc31560b9d4a212a40ba4719789df`, identical to `git rev-parse bb7b17c473bf702cd9ef76faca0018280a5c7433^{tree}`.
The [discovery job](https://github.com/noahwhite/agent-skills/actions/runs/44955531910/job/137002651766) passed `bash scripts/smoke-opencode.sh` with `OPENCODE_FORCE_INSTALL: "1"`.
QA inspected committed artifacts and completed execution records; it did not rerun or mutate the implementation suite.
No screenshots or hosted page apply to this nonvisual, no-deployment verification.

## Notes

No failed criterion, coverage gap or pending owner ruling remains.
The initial pre-PR local run remains mandatory under AC1's fallback; the existing refinement proposal to change that is owned by the product owner, not an acceptance failure.
The implementation PR records an existing Low fail-closed limitation: an inline-code `<!--` can make the active-line scanner falsely reject text.
The target text does not exercise that limitation, and this QA pass found no new incidental defect.
Closing the story requires this evidence PR to merge after its own head-bound review of record.
