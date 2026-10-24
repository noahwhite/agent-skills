# SKL-63 QA evidence

Date: 2026-10-24 UTC, verification round 1.
Build: `f446716699c15f6c40e7839be7f34d9a71fa987b`, merged `main` repository state; no deployment or running environment applies.
Fixtures: isolated QA worktree at that commit, read-only real tracker/GitHub inventory, and disposable local git worktrees and squash-merge branches.
This repository delivers a Markdown skill: contracts verify its instructions, and documented-command probes are not a full destructive cleanup integration run.
No visual surface or publishing capability applies, so there are no screenshots or hosted evidence page.
Raw output: attachment **SKL-63 round 1 assertions** on [SKL-63](https://linear.app/officina-pub/issue/SKL-63), filename `SKL-63-round-1-assertions.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: invocation and targeting | Verified | Independent read-only invocation returned the exact usage line; invalid then valid tracker lookups returned 1 then 0; explicit-key/team/continuation contracts passed. |
| AC2: inventory | Verified | Live worktree/local/remote/PR inventory commands succeeded; token examples excluded SKL-630 and SKL-59; all source, exclusion and inventory-first contracts passed. |
| AC3: guarded deletion | Verified | Real merged PR head checked; disposable fixture showed squash containment fails, ignored output requires the stronger status check, and clean worktree then branch removal reads back absent; remaining guards/refusal rules contract-verified. |
| AC4: hosted-evidence capability | Verified within the story's recorded boundary | Capability row, exact skip, loud-error/non-zero instructions, mapped per-artefact deletion and runtime-neutral wording contracts passed; no hosted content touched. |
| AC5: story attachments | Verified | Commands match installed CLI; named raw assertion attachment uploaded to SKL-63 and read back; citation-only and no-hosted-link contracts passed. |
| AC6: report and confirmation | Verified | Per-story removed/archived/skipped/refused report, inventory-before-removal, dated refusal and single-summary-comment contracts passed. |
| AC7: registration and tests | Verified | All 26 cleanup contracts passed; cleanup/todo selection passed 52; full suite passed 466; fresh vendoring produced no diff and vendor checks passed; manifest, README, counts and host-wording checks passed. |
| DoD: all AC met | Verified within the recorded boundary | AC1-AC7 above. |
| DoD: tests written and passing | Verified | Merged test additions inspected; independent 466-test suite and 52-test contract selection passed. |
| DoD: independently reviewed | Verified | Implementation [PR](https://github.com/noahwhite/agent-skills/pull/43) and [review of record](https://github.com/noahwhite/agent-skills/pull/43#pullrequestreview-5640139685) have matching head, review body SHA and commit_id `1d79dd70fe7d236790103600e48089179039f5c9`. |
| DoD: docs updated | Verified | Skill, README table, shared runtime/todo guidance and generated references inspected; vendor checks passed. |
| DoD: deployed verification if needed | Correct by design; integration verified | No deploy required; worktree HEAD equals the merged build and [main CI](https://github.com/noahwhite/agent-skills/actions/runs/40135466547) succeeded at that SHA. |
| DoD: no critical bugs/regressions | Verified in tested scope | No critical regression or incidental defect observed in the suite and independent probes. |

Reproduce from the build above: `uv run --locked pytest -q`, `uv run --locked pytest tests/test_cleanup.py tests/test_todo_tracking.py -v`, `python3 scripts/vendor_shared.py`, `python3 scripts/vendor_shared.py --check`, and `git diff --exit-code`.
The attachment records independent invocation, tracker/inventory commands, disposable git fixture results, named contracts, and exact-head implementation review verification.
AC4's positive hosted-evidence sweep is unexercised, neither passed nor failed, under the explicit story verification boundary; the publishing-session operator owns exercising it once hosted access returns.
The unreachable-capability leg is contract-verified, not a real inaccessible-host test.
Local leak scanning was public-pattern-only because private patterns are not injected; integration CI passed its required full scan.
No blocking item or incidental defect was found.
