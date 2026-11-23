# SKL-411 QA evidence

Round 1, 2026-11-23, path `no-deployment`.
Verified the squash commit `8eb5f0bf3b5ea7da6592d7645c4e91b7df42365e` on `main`, whose tree matches [implementation PR #408](https://github.com/noahwhite/agent-skills/pull/408) head `f95c4b3ac2e89e8fa73d35c0b121464b7b2af7a1`.
Fixtures: disposable repository, stand-in phase agents, default and hostile Git configs, and the SKL-389 commit series listed in the implementation PR.
The SKL-411 tracker attachments hold the structured assertion output.

| Item | Verdict | Evidence |
| --- | --- | --- |
| AC1 Delta re-gate | Failed | Focused suite: 49 passed, including the exact exit-12 message and no state change, spec and ancestry selection, tie-breaks, and reviewed-range checks. When the sole accepted run ends at the current head, a stand-in replay showed `paths --delta` returns `73cc334…-8eb5f0b…`, preserving that run's old base instead of selecting its accepted head as the delta base. |
| AC2 Tree identity and reuse | Verified | `tree_prefix_of` resolves the merge-base and head trees and `reuse_identity` appends the spec hash. Stand-ins prove no launch on an exact match, report the stamp provenance, and decline a one-byte or spec change. |
| AC3 Reuse safeguards | Verified | Stand-ins exercise sweep/hunt reuse, fresh preflight and arbitration, missing and lapsed predecessor exits, and `paths` observability. The dedicated reuse path writes no launch marker and fresh arbitration still uses the retention path. |
| AC4 Test coverage | Failed | The required delta, identical-tree, one-byte, predecessor and normalized legacy-dossier checks exist and pass. The hostile-config reuse test does not assert diffstat equality; that comparison is in a separate normalized-dossier test, not the same reuse test as required. |
| AC5 Measured case | Failed | Recomputed all 21 rows pasted in the PR: 361,350 cumulative patch bytes vs 151,951 delta patch bytes (2.38x), with 21 distinct head trees. This is a commit-series proxy, not the story's recorded 27 SKL-389 gate runs; it omits repeat attempts and does not measure reuse in that series. |
| AC6 Guards | Verified | Local Ruff, `uv run --locked pytest -q` (4,071 passed), pinned `skills-ref`, OpenCode smoke, and the vendor check via `python3 scripts/vendor_shared.py --check` passed. [CI at the final reviewed head](https://github.com/noahwhite/agent-skills/actions/runs/45153875534) passed the private leak scan. Direct vendor invocation exited 126 because the tracked file has no executable bit. |
| AC7 Deterministic dossier | Failed | The pinning flags are present. Default vs hostile configurations at the exact same base and head produced identical diffstat and path-normalized dossier bytes, not byte-identical dossiers as read by the phase: the raw header and capped diff section contain per-run paths. The committed regression test compares only normalized bytes. |
| DoD: All acceptance criteria met | Failed | AC1, AC4, AC5 and AC7 are not met as written. |
| DoD: Tests written and passing | Verified | 49 focused tests and 4,071 full-suite tests passed locally on the squash (same tree as the final head). Final-head CI's `Repository tests` step also passed, as required for changes under `tests/`. |
| DoD: Independent review | Verified | [Review of record](https://github.com/noahwhite/agent-skills/pull/408#pullrequestreview-6020024309) is `COMMENTED` at the final head and records separate reviewer and adjudicator seats with no open findings. |
| DoD: Docs updated | Verified | The merged `skills/adversarial-review-pipeline/SKILL.md` documents the delta and reuse interface, reporting and the distinction between rendering pins and reuse identity. |
| DoD: Deployment verification | Correct by design | `no-deployment`; there is no deployed environment. |
| DoD: No critical bugs or regressions | Verified | No critical issue surfaced in the focused checks or the final review of record; the AC gaps above remain open. |

The incidental vendor invocation issue predates this change.
