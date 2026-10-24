# QA evidence: SKL-23 - Update agent-skills runtime guidance for OpenCode 2.x config and invocation

Verified 2026-10-24 by the QA lane on the repository/CI surface.
Build under test: `main` at `a30477e15a692fde158a7423caa191adfc1723e3`, which contains the story merge `308d40b` (PR #26, reviewed head `a7ff1607d15b68484735aedca35ac3482f95db20`).
`main` advanced past the story merge during verification (PRs #27-#30); every check below ran against `a30477e`.
No hosted environment applies to this repo-only documentation story, so verification ran against the merged build on `main` plus live runs of the repository's own checks.
Fixtures: none; checks are deterministic greps, the vendoring sync check, and the pytest suite.
Full raw assertion output is attached to the Linear story (six attachments, ac1 through ac6); this directory is the durable index.

## Verdicts

| Item | Verdict | Evidence |
|---|---|---|
| AC1 version-qualified config semantics | PASS | `shared/runtimes.md` line 59 states V2 defaults `experimental.subagent_depth` and the top-level field is ignored with a warning; line 97 states V2 action `subagent` replaces V1 `task`; line 62 keeps the V1 form as version-qualified legacy guidance. |
| AC2 generated copies match source | PASS | `python3 scripts/vendor_shared.py --check` exits 0; all 17 `skills/*/references/runtimes.md` copies carry the GENERATED header. |
| AC3 OpenCode 2 invocation contract | PASS | Automation section documents `opencode run --agent ID --model provider/model#variant` and that the root TUI rejects `--agent`/`--model`; Interactive sessions section documents agent files, `default_agent`, `OPENCODE_CONFIG_CONTENT`, and command frontmatter. |
| AC4 no stale TUI instructions | PASS | Repo-wide grep for `opencode --agent` / `opencode --model` finds nothing; the only `--agent`/`--model` mentions are the rejection caveat itself and the pipeline scripts' own `--agent-cmd` flag. |
| AC5 consistent supported-version statement | PASS | 2.1.2 from `@opencode/cli` is pinned identically in `shared/runtimes.md`, `README.md`, `.github/workflows/ci.yml`, and `scripts/smoke-opencode.sh`; V1 is stated as legacy/untested; dependency SKL-22 (the discovery/CI story owning the version statement) is Done. |
| AC6 tests pass | PASS | `uv run --locked pytest -q`: 416 passed at `a30477e`; `tests/test_skills.py`: 79 passed, including the vendored-sync test that runs `vendor_shared.py --check`. |
| DoD all ACs met | PASS | AC1-AC6 all PASS above. |
| DoD tests written and passing | PASS | 416 passed at the build under test. |
| DoD independently reviewed | PASS | Review of record in state COMMENTED on PR #26 at merged head `a7ff1607d15b68484735aedca35ac3482f95db20` (Codex review APPROVE, adjudication CONFIRMED), confirmed via the GitHub API. |
| DoD docs updated | PASS | The story is itself documentation: `shared/runtimes.md`, the 17 generated copies, and `README.md` were updated in PR #26. |
| DoD verified in staging | N/A | No staging environment exists for this repository; the story's deployment model is consumers pulling the repo, so the merged `main` build is the deployment surface. |
| DoD no critical bugs/regressions | PASS | CI green on `main` at `a30477e` (run 40079319763, conclusion success) and on every merge since PR #26. |

Incidental observations: none affecting this story's scope.
The two post-merge nits recorded on PR #26 (ROC-01 cleanup-error stderr, ROC-02 README retry-budget wording) remain open follow-ups owned by the implementer and do not gate this story.
