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

Every evidence section below is in the tracker attachment linked above.

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
