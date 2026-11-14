# Shared capability references

This directory is the single source for the capability files that skills compose.
A skill links a capability through its vendored `references/<name>.md` copy.
`scripts/vendor_shared.py` writes those copies from the files below, using the capability list in `skills.json` plus every capability a vendored file cites as `references/<name>.md`.
A capability listed here may wait for a later slice to compose it.
Three of the directory's non-Markdown files are `resolve-model-role.py`, the model-role resolver (`profile.md`, Resolve a model role), `select-path.py`, the run-path selector (`engineering-workflow` step 1, Select the path), and `todo-enforce.py`, the Claude Code todo enforcer hook (the repository README, Todo enforcer hook); each is vendored into a skill's `scripts/` when `skills.json` lists it under `executables`.

## Files

| File | Capability |
|---|---|
| `code-review.md` | The review of record, optional reviewers, finding handling, and watching the PR. |
| `engineering-practice.md` | Diagnosis, TDD, durable fixes, test quality, and retiring a memory note once its rule moves into a skill. |
| `github.md` | Git, branch, worktree, PR, merge, promotion, commit signing, and attribution. |
| `infra-deploy.md` | Infrastructure as code, CI/CD, deploys, host operations, and incidents. |
| `linear.md` | Story and epic lifecycle, triage, estimation, and scope. |
| `merge-approval.md` | The delegated merge-approval handshake: approvals file, request ID, records, wake capability, waiting, and re-request. |
| `metrics.md` | Run metrics: what a run collects, the summary template, and the independence and posting rules. |
| `profile.md` | Finding and applying the consumer profile and its overlays, and resolving a model role. |
| `resolve-model-role.py` | The model-role resolver that `profile.md` documents. |
| `runtimes.md` | Mapping each named capability to the tools of each supported runtime. |
| `secrets.md` | Secrets, tokens, credentials, and input validation. |
| `select-path.py` | The run-path selector (`spike`, `no-deployment` or `deployed`) that `story-to-done`, `engineering-workflow` and `qa-verification` call. |
| `todo-enforce.py` | The Claude Code hook that holds a `story-to-done` or `story-refinement` main thread to its task list. |
| `todo-tracking.md` | The fine-grained todo list every persona keeps. |

## Adding a capability

1. Add the source file here.
2. List its name in `skills.json` for every skill that composes it.
3. Run `python3 scripts/vendor_shared.py`.
4. Run `uv run --locked pytest -q` and `python3 scripts/vendor_shared.py --check`.
