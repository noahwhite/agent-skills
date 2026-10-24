# SKL-58 QA evidence

Date: 2026-10-24 UTC, repeat verification.
Environment: `claude-code-env:skl58-ac2` (`sha256:f95c8e23f6cea1918df7ead1495a8b89ce148f6a293e8782f7b9124f9d4aacaf`) and `opencode-env:skl58-ac2` (`sha256:8a38cfb137b3037d1aad700cdfd05e71c50dbdc010f55c5f61c0b0df78245b7c`).
Build commits: `agent-skills` `221502c05445cd9bdf5e709656eddc0f02d5599d`, `claude-dev-container` `231a19ebbbda60a1968d5da4cd402570f26e399d`, and `opencode-dev-container` `f0c36df3d8352a4d1dbcf6eb97ead7b3d96fe445`.
Fixtures: container session users `claude` and `opencode`; no visual surface applies.
The sanitized [assertion output](https://uploads.linear.app/7fbfc592-b1ef-432c-96af-87e5111c541e/89695e00-f605-44bb-8e7c-280fb12c59d9/7e4edab3-0ddf-4943-934a-2cb5f15aefa4) is attached to SKL-58.

| Item | Verdict | Evidence |
|---|---|---|
| AC1 | Verified | Both installed profiles use `/tmp/agent-skills`, and both session users created and removed a subdirectory with `CLAUDE_JOB_DIR` unset and `bash -u` active. |
| AC2 | Failed | The OpenCode `code-review.md` overlay still instructs a fresh adjudicator `mktemp -d` under the profile base outside the one session directory; its shipped checker returns zero findings. |
| AC3 | Verified | The installed 20-overlay trees match the pinned source trees, and both consumer portability suites passed their runtime-label allowlist checks. |
| AC4 | Failed as written | Eleven of twelve changed profile and overlay line sets match; `engineering-workflow.md` has a Claude-only label addition because the OpenCode line was already labelled. |
| AC5 | Verified | The documented snippet made distinct directories and used the no-base fallback in both images; all 17 vendored runtime references match, the schema keeps the base optional, and the base suite and vendor check passed. |
| DoD: all AC met | Failed | AC2 and the literal AC4 hunk requirement remain open. |
| DoD: tests | Verified | The base suite passed 391 tests, the Claude suite passed 84 tests and 16 subtests, and all six OpenCode shell suites passed. |
| DoD: independent review | Verified | Six merged implementation PRs have `COMMENTED` reviews of record bound to their exact merged heads. |
| DoD: docs updated | Verified | The shared scratch rules, schema description, and consumer divergence READMEs are present at the pinned commits. |
| DoD: deployed verification | Verified | Both pinned image IDs and installed profile and overlay digests were checked directly. |
| DoD: no critical regressions | Verified in tested scope | No critical defect was observed; the AC2 contract failure remains open. |

SKL-58 engineering owns the corrections, rebuilt images, and repeat QA.
