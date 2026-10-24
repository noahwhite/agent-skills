# SKL-58 QA evidence

Date: 2026-10-24 UTC, repeat verification round 3.
Environment: `claude-code-env:skl58-rqa` (`sha256:a6f25779aab0c6b54e7425fba71e885ce731360df1ad712f807d2369120f2cc0`) and `opencode-env:skl58-rqa` (`sha256:950b1cb3bb0bf7b1cd90ba99c25be77ab8d4890f58ec1211727bb5452290a038`).
Build commits: `agent-skills` `a6e03c94b94e41e4b118d90772216acae8ccda17`, `claude-dev-container` `df162ab196cf6dca840f4b3c4e352188f8169a54`, and `opencode-dev-container` `82ce5c8fc649c30fd5252eb0e10ca61b9970b670`.
Fixtures: container session users `claude` and `opencode`; this story has no visual surface.
The sanitized raw assertion output is attached to SKL-58 as `SKL-58 QA assertions round 3`.

| Item | Verdict | Evidence |
|---|---|---|
| AC1 | Verified | Both image users created and removed a child of the literal `/tmp/agent-skills` base with the runtime job variable unset and `bash -u` active. |
| AC2 | Verified | The published snippet produced distinct existing session directories and its absent-base fallback in both images, while both shipped overlay checkers passed and rejected a base-level adjudicator path. |
| AC3 | Verified | Both 20-overlay image trees matched their merged sources, and direct scans found eight banned-token hits per tree, all labelled and allowlisted. |
| AC4 | Failed as written | Ten of 12 edited profile/overlay files have identical changed-line sets; `code-review.md` and `engineering-workflow.md` contain nonidentical changed lines, so their shared fragments do not satisfy byte-identical hunks. |
| AC5 | Verified | The absent-base fallback ran in both images, all 17 vendored runtime references match the shared source, the schema keeps `scratch_dir` optional, 416 base tests passed, and the vendor check passed. |
| DoD: all AC met | Failed | AC4 is unmet at the pinned consumer heads. |
| DoD: tests | Verified | The base suite passed 416 tests, the Claude suite passed 90, OpenCode portability passed 66, and all six OpenCode shell suites exited zero. |
| DoD: independent review | Verified | GitHub `COMMENTED` reviews of record match the exact final heads of all eight implementation PRs and include reviewer and adjudicator sections. |
| DoD: docs updated | Not fully met | Both consumer READMEs falsely say every SKL-58 changed hunk is byte-identical, and the OpenCode README also has a stale Workflow-label claim. |
| DoD: deployed verification | Verified | Both image IDs, the image profile payloads, and the OpenCode default entrypoint installation were checked directly. |
| DoD: no critical regressions | Verified in tested scope | No critical defect was observed in the tested scope. |

SKL-58 engineering owns the AC4 hunk reconciliation and correction of the two consumer README claims, followed by rebuilt images and repeat QA.
The stale OpenCode Workflow-label claim is incidental to the literal hunk-parity failure.
