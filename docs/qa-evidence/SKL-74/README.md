# SKL-74 QA evidence

## Round 1, 2026-11-05

SKL-74 is a decision spike and the repository deploys nothing, so the environment under test is the repository and tracker state at `6bce8e6fe66f0d5b5e182e0025bd02c4f77ce3d0`.
That commit is the baseline the findings name and was also the `main` head during QA.
The deliverables under test are the SKL-74 findings comment `4a9597af`, the implementation note `dfc1aa0b` and the SKL-150 note `2a818bd6`, checked against Linear (`linear api`), GitHub (`gh api` on PRs #49 to #63) and git at `6bce8e6`.
No fixture was used.
There is no visual surface, so the raw assertions are the evidence; they are attached to SKL-74 as "SKL-74 QA round 1 assertions (2026-11-05)", and the QA comment is `7b089ce3`.
The attachment is `SKL-74-qa-round-1-assertions.txt`, SHA256 `ef670d5f3ed85198bb3eab531ba469e21689043ad672cbecf52bf485e3c28c19`.

| Item | Verdict | Evidence |
|---|---|---|
| SC1 dated decisions, measurement or defect scenario, caveats, threshold, inconclusive as No-Go | Verified | Three decisions dated 2026-11-05, each with a threshold. The caveats state the bound direction per quantity, and observed and estimated figures are labelled. RQ2 names a defect present today with a falsifying test, and its inconclusive result is No-Go naming the missing evidence. |
| SC2 Go fields, No-Go retained policy and evidence | Verified | No decision is Go; each No-Go names the retained policy and why it wins. |
| SC3 follow-up story per Go, No-Go disposition | Verified | No decision is Go; all three record "No implementation story", and none proposes a separate change. |
| Baseline, seats, SKL-80 boundary, per-proposal status, evidence access | Verified | `6bce8e6` is `origin/main`, both profiles' seat lines match the findings, and the SKL-80, SKL-21, SKL-150 and SKL-154 states match. |
| Bounds on evidence and candidate pairings | Verified | Two candidates were probed and answered, and each is ruled out with a reason. |
| Evaluation scenarios | Verified | RQ1 covers post-gate edits and integration changes; RQ3 covers mixed changes, renames, executable docs, sensitive references and escalation; RQ2 covers a conflict and its reverse. |
| Deliverable 1 decision fields and RQ2 reconciliation | Verified | Each decision carries its required fields, and the one-line reconciliation quotes both profiles' seat lines. |
| Deliverable 2 Go change specification | Correct by design | No decision is Go. |
| Deliverable 3 No-Go alternative and rejecting evidence | Verified | Every policy line the findings cite matches git at `6bce8e6`, and the PR #49 to #63 facts reproduce from GitHub. |
| Deliverable 4 follow-up stories or explicit none | Verified | The findings' Next steps say no follow-up story is needed. |
| DoD success criteria validated | Verified | The rows above. |
| DoD findings documented in Linear | Verified | `4a9597af`. |
| DoD Go/No-Go decision made | Verified | The findings' summary table: three No-Go, with RQ2's two-seat split already satisfied. |
| DoD next steps defined | Verified | The findings' Next steps section and the SKL-150 note `2a818bd6`. |

### Incidental note

The findings list the round-2 fix commits on PR #49 without `e2ee197`, which the PR #49 review of record names as the fix for round 1 item 4 and round 2 item 4.
No verdict above depends on it.

Decision: Done once this evidence PR merges through its review of record and CI.
