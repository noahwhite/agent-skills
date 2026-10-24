# SKL-58 QA evidence

Date: 2026-10-24 UTC, verification round 4.
Environment: `claude-code-env:skl58-ac4` (`sha256:c83d69b8c62529829e1b05c4fae3d0cf19707fa8ca183ac27798c7d7238bf1fd`) and `opencode-env:skl58-ac4` (`sha256:7fc29dfb4a64d1f2d284870169e3da49d1d71372cb833b7d7cb2fce717c5dfc8`).
Build commits: agent-skills `85c3401e30e4a5ca0412f78dd21dda6f9f29eb99`, Claude consumer `9ce0255522764c6c047341491e3590784aa5b948`, OpenCode consumer `b38394363886e0128c17625eb2fc40996ce98d2c`.
Fixtures: image session users `claude` and `opencode`; this story has no visual surface.
The sanitized raw assertion output is attached to Linear SKL-58 as `SKL-58 QA assertions round 4`.

| Item | Verdict | Evidence |
|---|---|---|
| AC1 | Verified | Both image users created and removed a child of the literal `/tmp/agent-skills` base with the container-specific job variable unset and nounset active. |
| AC2 | Verified | The documented snippet made distinct session children and the absent-base fallback in both images; the shipped overlay checkers passed. |
| AC3 | Verified | Both shipped 20-overlay trees matched merged source; all eight banned-token occurrences per tree were labelled and allowlisted. |
| AC4 | Failed as written | All added lines match across 12 touched files, but the removed sides of the `code-review.md` and `engineering-workflow.md` changed hunks differ, leaving only 10 complete changed-line sequences identical. Hydration and consumer suites passed. |
| AC5 | Verified | The absent-base fallback ran in both images; 17 vendored runtime references match shared source, the schema keeps `scratch_dir` optional, 416 base tests passed, and the vendor check passed. |
| DoD: all AC met | Failed | AC4 is unmet at the pinned consumer heads. |
| DoD: tests | Verified | Base pytest passed 416 tests, Claude pytest passed 103 tests plus 16 subtests with one skip, OpenCode pytest passed 67 tests, and all six OpenCode shell suites exited zero. |
| DoD: independent review | Verified | GitHub `COMMENTED` reviews of record match the exact final heads of all ten implementation PRs. |
| DoD: docs updated | Not fully met | Both consumer READMEs acknowledge the differing removed lines but assert that they do not violate AC4. |
| DoD: deployed verification | Verified | Both image IDs, image payloads, base pin, and session-user probes were checked directly. |
| DoD: no critical regressions | Verified in tested scope | No critical defect was observed in the tested scope. |

SKL-58 engineering owns the AC4 hunk reconciliation and README correction, followed by rebuilt images and repeat QA.
The QA host's installed profile still carries the old variable-based scratch path; the two images under test do not.
