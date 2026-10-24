# QA evidence: SKL-22 - Port the agent-skills OpenCode discovery smoke test and CI to OpenCode 2.x

Verified 2026-10-24 by the QA lane on the repository/CI surface.
Build under test: `main` at `5159c6d678f13960fc4eca24d88452fe4b684d4c`, which contains the story merge `308d40b` (PR #26, reviewed head `a7ff1607d15b68484735aedca35ac3482f95db20`).
No portal environment applies to this repo-only tooling story, so verification ran against the merged build on `main` plus live runs of the smoke check from a clean checkout.
Fixtures: none; the smoke script builds its own isolated homes and projects.
Full raw assertion output is attached to the Linear story (four attachments); this directory is the durable index.

## Verdicts

| Item | Verdict | Evidence |
|---|---|---|
| AC1 package/version/override/gating | PASS | Script installs `@opencode/cli@$OPENCODE_VERSION` (default 2.1.2), override honored against installed v2.1.4, `allowScripts` in temp package.json; CI runs it on ubuntu-24.04/Node 22. |
| AC2 supported 2.x surface | PASS | `opencode api get /api/skill` with `x-opencode-directory`; no `debug skill` remains; surface and response shape recorded on the story before implementation. |
| AC3 every documented layout | PASS | Live forced-install run: all six layouts (project/global `.agents`, `.opencode`, `.claude`) discovered 17/17 skills, exit 0. |
| AC4 negative case | PASS | Removed SKILL.md: exit 1 naming `linear-bug/SKILL.md`; corrupted frontmatter: exit 1 naming `linear-spike`. |
| AC5 no credentials | PASS | Fixture env is PATH/HOME/XDG only; live run needed no model credentials; network is npm registry only. |
| AC6 CI passes on 2.x | PASS | `discovery` job pins Node 22 and OpenCode 2.1.2; green on PR head (run 39931601875) and on `main` (runs 39932233943, 40074609443). |
| AC7 version statement | PASS | README states OpenCode V2 2.1.2 from `@opencode/cli`; no CONTRIBUTING exists; no `opencode-ai`/1.x-only claim. |
| DoD tests | PASS | 391 tests passed on the merged build (`uv run --locked pytest -q`); CI `checks` job green. |
| DoD independent review | PASS | Review of record COMMENTED on PR #26 at merged head `a7ff160` (Codex review APPROVE, adjudication CONFIRMED). |
| DoD docs | PASS | README updated in PR #26. |
| DoD staging | N/A | Repo/CI tooling story with no staging deployment; verified on the merged `main` build. |
| DoD regressions | PASS | CI green on `main`, suite green, smoke green on all six layouts. |

Incidental observation: one corrupted-frontmatter run reported a transient CLI JSON-truncation message at the deadline instead of the missing-skill name; a repeat run named the skill, and the exit code is non-zero either way.
