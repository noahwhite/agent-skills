# SKL-58 QA evidence

Date: 2026-10-24 UTC, verification round 5.
Environment: `claude-code-env:skl58-ac4` (`sha256:c83d69b8c62529829e1b05c4fae3d0cf19707fa8ca183ac27798c7d7238bf1fd`) and `opencode-env:skl58-ac4` (`sha256:7fc29dfb4a64d1f2d284870169e3da49d1d71372cb833b7d7cb2fce717c5dfc8`).
Merged commits: agent-skills `305714a91f1121e94dd2e48d239f595222fb0dd1`, Claude consumer `9ce0255522764c6c047341491e3590784aa5b948`, OpenCode consumer `b38394363886e0128c17625eb2fc40996ce98d2c`.
Image base pin: agent-skills `a6e03c94b94e41e4b118d90772216acae8ccda17`.
Fixtures: image session users `claude` and `opencode`; this story has no visual surface or screenshots.
The sanitized raw assertion output and a self-contained evidence page are attached to Linear SKL-58 as round 5 files.

| Item | Verdict | Evidence |
|---|---|---|
| AC1 | Verified | Both image users created, read, and removed a child of the literal `/tmp/agent-skills` base with the container-specific job variable unset and nounset active. |
| AC2 | Verified | The documented snippet made two distinct session directories in each image, the absent-base fallback ran, and both image fixed-path checks exited cleanly. |
| AC3 | Verified | Both baked 20-overlay trees matched merged source, and all eight banned-token occurrences per image were runtime-labelled and explicitly allowlisted. |
| AC4 | Verified under the dated owner decision | Added lines match across all 12 touched profile and overlay files; the two differing removed-line sequences were pre-existing, both READMEs record divergence, and hydration reported zero problems. |
| AC5 | Verified | The absent-base fallback ran in both images, 17 vendored runtime references matched shared source, the schema kept `scratch_dir` optional, 416 base tests passed, and the vendor check passed. |
| DoD: all AC met | Verified | AC1 through AC5 passed, including AC4 under the 2026-10-24 owner decision. |
| DoD: tests | Verified | Base pytest passed 416 tests, Claude pytest passed 90 with one skip, OpenCode portability passed 67, and all remaining OpenCode shell suites passed. |
| DoD: independent review | Verified | GitHub `COMMENTED` reviews of record match the merged heads of all ten implementation PRs. |
| DoD: docs updated | Verified | The shared scratch rule, schema description, vendored copies, and both consumer README divergence records are present. |
| DoD: deployed verification | Verified | Both image IDs, baked profile and overlay bytes, base pin, and image-user probes were checked directly. |
| DoD: no critical regressions | Verified in tested scope | No critical defect was observed in the tested scope. |

Incidental test defect: an initial OpenCode `agent-definitions.test.sh` run intermittently failed on `printf` broken pipe at line 73; a rerun passed 24 of 24 checks.
Incidental host drift: this QA host's installed profile still carries the old variable-based scratch value; the two named images carry the corrected literal base.
