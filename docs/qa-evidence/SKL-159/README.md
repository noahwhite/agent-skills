# SKL-159 QA evidence

## Round 2 - acceptance criteria met

Date: 2026-11-01.
Artifact: merged `main` at `77c8f0599193c89b957000b3983bda13843a9b8b` in an isolated checkout.
Environment: repository artifact only; the profile declares `environments: []`, so no deployed build exists.
Fixtures: fictional `ABC-123`, committed baseline/candidate traces and scratch-only reconstructed grader inputs.
Lanes: source contracts, recorded session/tool-call traces, read-only vendor drift check, GitHub CI/reviews and Linear.
No visual surface, screenshots or hosted page apply.
Raw evidence is attached to SKL-159 as `SKL-159 QA round 2 repository assertions`.
Tracker QA comment identifier prefix: `294639ab`.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: ownership and same-round continuation | Verified | Exact source rules at `SKILL.md:152-160`; committed candidate traces regrade 3/3 same-session resumes and mixed-owner stop passes. Runtime-unavailable, read-back and stall rules are repository instructions, not live fault injections. |
| AC2: new agent for every new round | Verified | Exact full lines at `SKILL.md:120-122`; recorded new-round control launches `qa-round-2-session`. |
| AC3: authority boundary | Verified | `SKILL.md:176-183`; summary permission unchanged from baseline; recorded echo contains resume only. Prior round's fresh echo remains owner-verified; round 2 claims no new model execution. |
| AC4: exact pins, deletions, evaluation and checks | Verified | Remediation pins the whole operative owner-stop sentence exactly once in the named test at `tests/test_story_to_done.py:183-191`; individual deletion ledgers include owner-clear. Metrics launch/sum wording, case artifacts and ownership split inspected; baseline trace regrades 0/3 continuations, candidate 3/3 and both controls pass. Vendor drift exits 0; PR-head CI reports 935 passing tests. |
| DoD: all acceptance criteria met | Verified | AC1-4 above; round 1's owner-clear pin gap is closed by the merged remediation. |
| DoD: tests written and passing | Verified | Named contract/harness tests and locked-suite PR-head CI: 935 passed; read-only vendor check exits 0. Historical local 917 count is not reused as CI evidence. |
| DoD: independently reviewed | Verified | Both merged implementation/remediation heads match the latest COMMENTED review's commit and first-line SHA; configured separate reviewer/adjudicator and all findings fixed. |
| DoD: docs updated | Verified | Skill steps, Boundaries, metrics protocol, case metadata and rerun instructions. |
| DoD: deployed verification if needed | Correct by design | No environment exists; repository artifact verified directly, main checks/discovery successful. |
| DoD: no critical bugs/regressions | Verified within tested scope | None observed; stub-harness limitations remain explicit. |

[Implementation PR](https://github.com/noahwhite/agent-skills/pull/122) reviewed head: `95c1a8fc55c72f0568773c09ea24d756356d4095`.
[Remediation PR](https://github.com/noahwhite/agent-skills/pull/124) reviewed head: `ca89afc0d84e012b64364a7d99752ef19850f329`.
[PR-head CI](https://github.com/noahwhite/agent-skills/actions/runs/41299081797) and [main CI](https://github.com/noahwhite/agent-skills/actions/runs/41299287197) are successful.
Closing decision: Done after this evidence PR merges through its current-head review gate; until then evidence merge is owned by this QA agent and status remains In Deployment Review.
No new incidental defect was observed.
QA changed no implementation or tests, did not mutate or rerun the implementation suite, and spot-checked the actual merged remediation diff.

## Round 1 - historical failed review

Date: 2026-11-01.
Artifact: merged `main` at `4f0eb796d9390e77a7388aa26ce2ec1e24aa20a2` in an isolated checkout.
Environment: repository state; `.agent-skills/profile.yaml` declares `environments: []`, so no deployed build exists.
Fixtures: fictional `ABC-123`, stub `qa-round-1-session`, and the committed baseline/candidate tabletop records.
Lanes: source-contract assertions, sandbox session/tool-call traces, locked tests, GitHub checks/reviews, and Linear.
There is no visual surface and no hosted page; sanitized assertion output is attached to SKL-159 as `SKL-159 QA round 1 assertions`.
Tracker QA comment identifier prefix: `dd0726a1`; raw attachment identifier prefix: `e876ba1c`.

## Verdicts

| Item | Verdict | Evidence |
|---|---|---|
| AC1: current-round continuation and ownership rules | Verified | `SKILL.md:152-160` contains the nine rules; the own-steps probe resumes `qa-round-1-session` in round 1 with a clean, neutral message; mixed-owner probe stops. Runtime-unavailable, repeated-read-back and stall rules are verified as instructions, not claimed as live-runtime executions. |
| AC2: new clean, neutral agent for every new round | Verified | Exact sentence at `SKILL.md:120`, exception/reset rules at lines 121-122, and new-round tabletop session-identity control. |
| AC3: coordinator authority boundary | Verified | `SKILL.md:176-183`; summary-comment permission unchanged from baseline; scratch echo tabletop produces one continuation and no mock merge, tick, state, verdict or bypass action. |
| AC4: exact pins, deletion records, eval case and checks | Not met | The full new sentence at `SKILL.md:122` is not asserted exactly: `tests/test_story_to_done.py:128-136` checks three fragments but never checks `once the owner clears it`. The PR's deletion ledger has no individual deletion record for this clause. Other checked portions pass: committed eval artifacts and baseline/candidate traces, 917 tests, vendor check, and both PR-head CI jobs. |
| DoD: all acceptance criteria met | Not met | AC4 gap above. |
| DoD: unit/integration tests written and passing | Verified | Committed contract/harness tests; `uv run --locked pytest -q`: 917 passed; `uv run --locked python scripts/vendor_shared.py --check`: exit 0. Passing tests do not close AC4's pin-coverage gap. |
| DoD: independently reviewed | Verified | [Implementation PR](https://github.com/noahwhite/agent-skills/pull/122) latest `COMMENTED` review of record: both `commit_id` and first-line SHA equal merged PR head `95c1a8fc55c72f0568773c09ea24d756356d4095`; Codex GPT-6 Sol then separate DeepSeek V4 Pro; all findings fixed and final verdict clean. |
| DoD: docs updated | Verified | Merged skill steps, Boundaries, metrics protocol, eval metadata and rerun instructions. |
| DoD: verified in a deployed environment if needed | Correct by design | No environment exists; merged repository artifact verified directly, with both `main` CI jobs successful. |
| DoD: no critical bugs/regressions | Verified within tested scope | Full suite and tabletop probes show no critical runtime regression; AC4 is a required contract-test coverage gap, not a demonstrated production failure. |

## Closing decision

Reopen SKL-159 to In Progress after this evidence is recorded.
The implementing senior engineer owns AC4 remediation: pin the complete changed sentence exactly in a named test and record its guarded-phrase deletion failures, then pass normal review and CI before a fresh QA round.
QA changed no implementation or tests and created no replacement bug.
No incidental defect was observed beyond the story-owned AC4 gap.
Interrupted supplemental probe attempts are void, not passing results or product failures; their completed reruns are recorded in the tracker attachment.
