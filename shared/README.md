# Shared capability references

This directory is the single source for the capability files that skills compose.
A skill links a capability through its vendored `references/<name>.md` copy.
`scripts/vendor_shared.py` writes those copies from the files below, using the capability list in `skills.json`.
A capability listed here may wait for a later slice to compose it.

## Files

| File | Capability |
|---|---|
| `code-review.md` | The review of record, optional reviewers, finding handling, and watching the PR. |
| `engineering-practice.md` | Diagnosis, TDD, durable fixes, and test quality. |
| `github.md` | Git, branch, worktree, PR, merge, promotion, commit signing, and attribution. |
| `infra-deploy.md` | Infrastructure as code, CI/CD, deploys, host operations, and incidents. |
| `linear.md` | Story and epic lifecycle, triage, estimation, and scope. |
| `merge-approval.md` | The delegated merge-approval handshake: approvals file, request ID, records, wake capability, waiting, and re-request. |
| `metrics.md` | Run metrics: what a run collects, the summary template, and the independence and posting rules. |
| `profile.md` | Finding and applying the consumer profile and its overlays. |
| `runtimes.md` | Mapping each named capability to the tools of each supported runtime. |
| `secrets.md` | Secrets, tokens, credentials, and input validation. |
| `todo-tracking.md` | The fine-grained todo list every persona keeps. |

## Adding a capability

1. Add the source file here.
2. List its name in `skills.json` for every skill that composes it.
3. Run `python3 scripts/vendor_shared.py`.
4. Run `uv run --locked pytest -q` and `python3 scripts/vendor_shared.py --check`.
