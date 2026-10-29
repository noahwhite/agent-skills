# SKL-96 QA evidence - round 1

Date: 2026-10-29.
Build: `b424c25ad25265635f74c930cf0495b84c9c2258` on merged `main`.
Environment: repository CI; the repository profile has `environments: []`.
Surface: skill text, repository tests in merged CI, and the shipped CLI end form.
Fixtures: scratch-only timestamp pairs naming `senior-engineer-1` and `qa-round-1`; no live role loop, account, deployment, or visual surface.
The attached assertions are the raw record, not screenshots or a hosted page.

## Evidence

- Tracker evidence: SKL-96, comment `9162762b`.
- Raw evidence: attachment titled `SKL-96 QA round 1 - AC and DoD assertions` on that story, including per-item assertions and CLI output.
- [Merged CI](https://github.com/noahwhite/agent-skills/actions/runs/40825922676): `checks` and `discovery` succeeded; `uv run --locked pytest -q` reported 744 passed in 99.29s.
- [Implementation PR](https://github.com/noahwhite/agent-skills/pull/86): merged as the build above, with the latest submitted review of record bound to `619c40098f067875d5c4de547b9b2083e4964dd3`.

The suite invokes `scripts/vendor_shared.py --check` in `test_vendored_references_are_current`.
QA read the merged tests and CI output rather than rebuilding or mutating the suite.
The implementation PR records named failing tests for phrase deletions and the later failed-items correction.

## Verdicts

Every evidence section below is in the tracker attachment identified above.

| Item | Verdict | Evidence |
|---|---|---|
| C1 Collection | Not met as an integrated contract; the required text is present, but the mandatory consumer cannot emit role metadata, reported usage/cumulative markings, or extras. | C1; skill lines 63-68 and 84-85; end form lines 5-10 |
| C2 Independence | Verified; both role-brief sections are byte-identical to the parent, with no metrics content, and later rounds are explicitly excluded. | C2 |
| C3 Docs | Verified; separate on-only seed sentence, unchanged shared/vendored todo text. | C3 |
| C4 Tests | Verified for the specified text-contract scope; seven new guards, unchanged state/scratch guards, mutation record, and green merged CI. | C4 |
| DoD All AC met | Not met because of C1. | DoD1 |
| DoD Tests written and passing | Verified for this slice; 744 tests passed, including vendoring checks. | DoD2 |
| DoD Independent review | Verified as a historical completed review at the implementation head; its emitter deferral does not determine QA acceptance. | DoD3 |
| DoD Docs updated | Verified; skill step 0 has the required seed. | DoD4 |
| DoD Staging | Correct by design / out of scope; no staging target, and live-role verification is owned by SKL-97/SKL-98, both Backlog. | DoD5 |
| DoD No critical bugs/regressions | Not met for the feature; the role-metrics closing path loses its central data. | DoD6 |

## Reproduction and handoff

At the build above, give the shipped `metrics-summary.sh` a scratch file containing start/end timestamp pairs for `start`, `senior-engineer-1`, and `qa-round-1`, each label unique, then invoke its documented end form.
The raw capture shows both role rows as `command | not set | not set | 1.000000000s | not reported | not reported`, with no extra lines and hardcoded usage totals.
The script has no metadata or extras input format, so it cannot preserve those figures regardless of runtime availability.
This is a CLI-consumer reproduction, not a claim that an engineer or QA role was launched.
The new collection rules and the mandatory verbatim end-form output cannot both be followed.

Decision: return SKL-96 to In Progress, with C1, DoD All AC, and DoD No critical bugs/regressions left unchecked.
Fix owner: SKL-96 engineer through `engineering-workflow`, coordinating the emitter boundary with SKL-95's owner; do not file a replacement bug for this unmet delivered criterion.
SKL-48 and SKL-95 are Done, so they are not undeployed blockers.
SKL-97/SKL-98 own the real engineer/QA role-launch verification, and SKL-94 owns posting.
No separate incidental defect was observed.

## Round 2 - 2026-10-29

Build: `d06da60c3d737fd7fb31ae3d611f23cd897c0f44`, freshly fetched merged `main`.
Environment: repository CI, with `environments: []` in the current-main repository profile; no service deployment or staging target exists.
Fixtures: scratch-only records for an initial engineer, a resumed engineer and two QA rounds, using the artifact's documented writer commands, real command timestamps and synthetic usage values.
These probes exercise the CLI protocol, not live role launches.
No visual surface exists, so there are no screenshots; this runtime has no hosted-artifact capability.
The round-1 record above is retained as history, not the verdict on this build.

### Round-2 evidence

- Tracker evidence: SKL-96, comment `cfed1db1`.
- Raw record: story attachment titled `SKL-96 QA round 2 - AC and DoD assertions`, with sections C1-C4, DoD1-DoD6 and CI.
- [Merged CI](https://github.com/noahwhite/agent-skills/actions/runs/40834323141): `checks` and `discovery` succeeded on the build above; `uv run --locked pytest -q` reported 772 passed in 102.34s.
- [Remediation implementation PR](https://github.com/noahwhite/agent-skills/pull/88): merged as the build above; latest submitted review of record's first-line SHA and `commit_id` both match head `9e43d572b91718c08c44427a198c07eebbfeec6e`.

QA inspected the merged diff's realistic caller tests: they execute the documented writer commands and assert the exact end-form output, including literal model characters and cumulative handling.
The passing unfiltered CI suite includes `scripts/vendor_shared.py --check` via `test_vendored_references_are_current`.
The implementation PRs record named failed tests for guarded-phrase deletions; QA did not rebuild or mutate the suite.

### Round-2 verdicts

Every evidence section below is in the round-2 tracker attachment.

| Item | Verdict | Evidence |
|---|---|---|
| C1 Collection | Verified: required text and documented commands preserve four ordered role rows, metadata, exact measured durations, unknown usage, independent cumulative markings and all eight extras. | C1 |
| C2 Independence | Verified: both brief sections are byte-identical to before SKL-96; later-round and re-spawn exclusions remain explicit. | C2 |
| C3 Docs | Verified: separate on-only seed; shared and all vendored todo files unchanged across both implementation rounds. | C3 |
| C4 Tests | Verified: exact-phrase guards, named deletion records, unchanged state/scratch guards, realistic caller tests and green merged CI. | C4, CI |
| DoD All AC met | Verified within this story's text-contract and executable protocol scope. | DoD1, C1-C4 |
| DoD Tests written and passing | Verified: 772 merged-CI tests passed, including vendoring checks. | DoD2, CI |
| DoD Independent review | Verified: implementation review is bound to the exact merged PR head. | DoD3 |
| DoD Docs updated | Verified: required step-0 seed is present. | DoD4, C3 |
| DoD Staging | Correct by design / N/A as specified; live orchestration runs remain owned by SKL-97/SKL-98, both Backlog, not completed here. | DoD5 |
| DoD No critical bugs/regressions | Verified within observed scope: emitter conflict no longer reproduces, invalid records refuse without writes, command-only behavior is preserved, merged CI passes. | DoD6, C1, CI |

The four-row probe preserved `120000`, `not reported`, `260000 cumulative` and `3000` tokens, and `41`, `not reported`, `5` and `6 cumulative` tool calls.
Totals were `123000` tokens and `46` tool calls, each with `3 not reported, 1 cumulative`, proving exclusion is per figure rather than per row.
Unknown-extra, malformed-figure and duplicate-label inputs returned nonzero without changing their records or printing a summary.
Command-only output matched the pre-remediation build after normalizing only dynamic end-time-derived cells.
Decision: accept this slice and move it to Done once this evidence is merged through the exact-head review and CI gate.
SKL-48 and SKL-95 are Done, so no undeployed dependency blocks direct verification.
Outstanding downstream work remains SKL-97's live engineer run, SKL-98's live QA run and SKL-94's posting, all Backlog; none is claimed complete here.
No separate incidental defect was observed.
