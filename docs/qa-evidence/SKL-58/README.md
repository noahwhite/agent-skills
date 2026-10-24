# SKL-58 QA evidence

Date: 2026-10-24 UTC.
Environment: `claude-code-env:skl58-verify` (`sha256:27342575ee0d4ee86cab7fb478e5d5ef5eab4c2017c1741264732ad693c3e3cf`) and `opencode-env:skl58-verify` (`sha256:75c9043bb1b2e144c03f6cee575072aef293274dcc97a8426e18abed0dad621b`).
Build commits: `agent-skills` `221502c05445cd9bdf5e709656eddc0f02d5599d`, `claude-dev-container` `3ae63ab63dc34073177e4af79a5a8cdaba857d8c`, and `opencode-dev-container` `b0714e107213e7f6902fcdde102fd2aebe424de9`.
Fixtures: the `claude` and `opencode` image session users; no customer fixture or visual surface applies.
The sanitized command assertions are attached to the Linear story as `SKL-58 QA assertions`.

| Item | Verdict | Evidence |
|---|---|---|
| AC1 | Verified | Both image users created and removed a directory under the identical literal `/tmp/agent-skills` with the runtime job variable unset. |
| AC2 | Failed | Both shipped `code-review.md` and `engineering-workflow.md` overlays still use fixed `/tmp/pr-review*` and `/tmp/loop-review*` worktree and `CODEX_HOME` paths outside the session directory. |
| AC3 | Verified | Both consumer portability suites passed their labelled-exception checks. |
| AC4 | Verified for changed portions | The shared profile hunk and nine common overlay patch hunks matched byte for byte, the existing model-map divergence is documented, and hydration reported zero problems. |
| AC5 | Verified | The absent-base fallback test passed, schema optionality held, all vendored runtime references matched, and `vendor_shared.py --check` passed. |
| DoD: all AC met | Failed | AC2 remains unmet. |
| DoD: unit/integration tests | Verified | Base 391, Claude 51 plus 16 subtests, OpenCode 14 portability and all shell suites passed. |
| DoD: independently reviewed | Verified | The three merged implementation PRs carry head-matching review-of-record comments with separate reviewer and adjudicator. |
| DoD: docs updated | Verified | The shared scratch rules, schema description, and consumer divergence READMEs were present at the merged commits. |
| DoD: deployed verification | Verified | Both named image IDs and the bundled base SHA matched; the OpenCode entrypoint installed the profile with `NET_ADMIN`. |
| DoD: no critical regressions | Verified in tested scope | No critical defect was observed; the AC2 concurrency defect remains open. |

The work returns to In Progress for the AC2 fix and a new image verification.
