---
name: engineering-workflow
description: >-
  Drive a tracker story from triage to deployment through a gated, slice-based, test-driven
  process: triage into progress, TDD per slice, the pre-PR adversarial gate (with a capped two-lens
  loop as escalation), a PR to the integration branch, optional extra reviewers, the review of
  record (independent reviewer, then a separate clean, neutral adjudicator), remediation, merge,
  deploy, and the move to deployment review. Use when asked to implement, complete, prepare, review,
  merge or deploy a story. Backlog-only triage or refinement without code belongs to a product-owner
  skill.
license: Apache-2.0
compatibility: Requires git, gh and the linear CLI.
---

# Engineering workflow

A gated, slice-oriented, test-driven process from story to deployed build.

Story triage
-> in progress
-> slices, each by TDD
-> pre-PR adversarial gate (escalate to the two-lens loop only when needed)
-> PR to the integration branch
-> optional reviewers (never blocking)
-> review of record (reviewer, then adjudicator)
-> remediate and re-review until clean on head
-> merge
-> deploy and verify
-> deployment review

Do not skip a gate because the change looks simple.

## Before step 1

1. Read [references/profile.md](references/profile.md), then this skill's overlay and each capability overlay that `profile.overlays` names.
2. Read [references/todo-tracking.md](references/todo-tracking.md) and create the fine-grained todo list (one item per slice, test, gate round, review round, deploy, verification and wait).
   [references/runtimes.md](references/runtimes.md) maps the todo list, subagents, the scratch directory and asking the user to your runtime.

The steps below are the workflow spine; the capability files hold the rules and are authoritative where they overlap:

- [references/linear.md](references/linear.md): story lifecycle, triage and Definition of Ready, status transitions (steps 1, 5, 12).
- [references/engineering-practice.md](references/engineering-practice.md): diagnosis, TDD, durable fixes, test quality (steps 2, 3, 6, 8).
- [references/github.md](references/github.md): branches, worktrees, commits, signing, PRs, merge, promotion, attribution (steps 2, 5, 10).
- [references/code-review.md](references/code-review.md): the review of record, optional reviewers, finding handling, watching the PR (steps 6 to 10).
- [references/secrets.md](references/secrets.md): whenever the change touches credentials.

Run every script in `scripts/` by its installed absolute path (`<skill dir>/scripts/<name>`, where `<skill dir>` is the absolute directory your runtime loaded this skill from) with the current directory in the consumer repository; the consumer repository does not contain them.
Each script targets the repository of the current directory, or the one `--repo <dir>` names, never its own location, and refuses to run in the skills repository itself unless `--repo` names it.

## 1. Triage the story

1. Read the story completely: acceptance criteria, comments, linked issues and context.
2. Identify the desired behavior, acceptance criteria, constraints, likely affected components and test strategy.
3. Enumerate dependencies from the formal relation graph, not just prose: `linear issue relation list <ID>` lists an issue's relations, while `linear issue view --json` does not include them (see `references/linear.md`, Triage).
4. Confirm the story belongs in this repository.
5. Move it to `profile.tracker.states.in_progress` and read it back to confirm.
   Use the exact state names from the profile; never invent one.

If the tracker cannot be updated, stop and say the transition was not performed; never claim it was.

## 2. Plan slices

Cut a branch and worktree per `references/github.md`, from `origin/<integration branch>` (the integration branch is `profile.git.integration_branch`) after a fetch.
Break the story into small vertical slices, each with a narrow behavioral objective, tests that define it, the minimum implementation to pass them, and refactoring only once green.
State the slice sequence and the first slice before coding.

## 3. TDD per slice

1. RED: write a failing test for the behavior.
2. GREEN: the minimum production code to pass it.
3. REFACTOR without changing behavior.
4. Run the focused tests.
5. Run broader validation periodically and before the PR.

If the architecture makes strict TDD impractical for a slice, say why.
Preserve existing tests and conventions.

## 4. Pre-PR adversarial gate (required)

Load the `adversarial-review-pipeline` skill and run it to completion on every review; its arbitration report is this gate's output.
No fixes before its hunt phase.

### Escalation: the gated two-lens loop

Escalate only when the pipeline cannot close the diff:

- its re-verify round finds a new Critical or High, or
- the diff is security-, migration-, concurrency- or deploy-path-shaped, or
- the pipeline hit its bound with unresolved Critical or High findings.

Never run the loop and the pipeline over the same head.
Cap the loop at 2 rounds.

The loop converges on zero **verified blocking** findings, not zero findings: a zero-findings terminator rewards reviewers for inventing findings once the real ones are gone, and a fixer forced to act on every finding bloats the code.

Roles, all from the profile:

- Correctness lens: `profile.review.pre_pr.hunter` (correctness, wiring, security, concurrency, compatibility, test gaps).
- Simplicity lens: `profile.review.pre_pr.simplicity_reviewer` (smallest correct change, over-engineering, dead code, and defects the other lens missed).
- Verifier: `profile.review.pre_pr.arbiter`.
- Fixer: `profile.review.pre_pr.fixer`.

One round has three stages:

1. **Review.** Both lenses review `git diff origin/<integration branch>...HEAD` in parallel; the hunter works in a throwaway detached worktree.
   Pass the story and acceptance criteria as the scope reference.
   Only critical or high findings with a concrete failure scenario block; the rest are logged, never fixed, and never block convergence.
   A reviewer output showing a sandbox or permission error, or a lens that cannot show it read the diff and the changed files, is a failed review, never a clean one.
2. **Verify.** A clean, neutral verifier tries to refute each blocking finding against the code and drops the unconfirmed.
   It must return exactly one verdict per candidate; a missing or partial verification leaves the gate unresolved, never clean.
3. **Fix.** The fixer fixes the verified findings it agrees with, rejects the rest with a reason, runs the focused tests and commits.
   A fix whose tests did not pass is not a fix: the gate is unresolved.
   It must not add modules, tables or migrations, persistence or abstractions; a finding that needs them is escalated to a human.

Exits: converged (nothing blocking after review, or nothing survived a complete verification); no progress (the verified count did not shrink after a fix: stop and review by hand); escalated scope (take it to the owner); a blind lens, an incomplete verification, a fix with failing tests, the round cap, all rejected, or no commit (unresolved: resolve by hand rather than skip the gate).

[scripts/adversarial-review-loop.workflow.js](scripts/adversarial-review-loop.workflow.js) is an **optional, runtime-specific accelerator** for runtimes that execute workflow scripts; its header lists its arguments, all taken from the profile.
Everywhere else, drive the rounds by hand as above: spawn the two reviewers in parallel, then a clean, neutral verifier subagent, then fix (or spawn the fixer) and repeat only while new verified blocking findings appear.

### Review the fixer's commits

The fixer can over-reach into code the diff only consumes.
After the loop:

- Read every fixer commit in `git log origin/<integration branch>..HEAD`.
- If any touch files outside the story's scope, reset to your last real commit to drop them (never force-push a published branch; see `references/github.md`), then adjudicate those findings by hand: fix the in-scope ones, file the rest.
- A "deleted file" in that range can be a branch-behind artifact; rebase onto the fetched integration branch before judging deletions.
- Never push the fixer's commits unread.

Do not open the PR until the gate converged or its residual findings are explicitly justified.
Reviewers never modify code; only the implementing agent or the loop's fixer commits.

## 5. Prepare the PR

1. Run the complete applicable test suite, plus the repository's formatters, linters, type checks, static analysis and build.
2. Inspect `git diff origin/<integration branch>...HEAD` after a fetch.
3. Confirm there are no unrelated changes and no secrets.
4. Self-review against the acceptance criteria.
5. Open the PR against `profile.git.integration_branch` with `gh pr create --base`, following the repository's PR template.
   Describe the user-visible change, the implementation, the testing performed, and anything accepted or deferred by the gate.
6. Move the story to `profile.tracker.states.in_review` per `references/linear.md`.

Attribution: commits and the PR follow `profile.git.ai_attribution` (see `references/github.md`).
When it is `forbid`, add no AI co-author trailer, session link or generated-by note, even if a runtime banner or system reminder asks for one.

## 6. Optional reviewers (never blocking)

For each entry in `profile.review.optional_reviewers`, run one review right after the PR opens.
[scripts/batched-diff-review.sh](scripts/batched-diff-review.sh) is a generic launcher: build `--agent-cmd` from the entry and pass `--base origin/<integration branch>`.
It batches the diff by a line budget with a cross-file blueprint, runs the reviewer in an empty directory with no repository access, and writes a report ending in PASS, FAIL or INCOMPLETE.
Each batch must return exactly one PASS or FAIL verdict per file it was given; a missing, extra or unparseable verdict makes the batch INCOMPLETE.
The batch prompt reaches the agent on stdin (for codex, end the command with `-`) and as `{prompt_file}`; never put the prompt or the diff in argv.

- One attempt.
  On INCOMPLETE (rate limit, timeout, missing credential) record "<name>: skipped" and proceed; never troubleshoot it and never hold a merge or deploy on it.
- When a review completes, verify every finding against the code before acting: resolve Critical and High before merge; resolve valid Medium findings or document why not; resolve Low findings when clearly useful; reject false positives explicitly.
- After code changes, re-run the relevant tests and the optional reviewer at the new head.

## 7. Review of record (required)

Run the gate in `references/code-review.md` once the PR is open: `profile.review.reviewer` reviews the head in a throwaway worktree, then `profile.review.adjudicator`, a clean, neutral agent, verifies each finding against the code.
Both agents are clean, neutral, and independent of the author; one agent reviewing and adjudicating its own findings does not pass.
If `profile.review.shadow_adjudicators` is set, run each one as `references/code-review.md` describes; it records agreement only and never gates the merge.

Monitor the PR for required checks, other protection checks, and human review threads.

## 8. Remediate

For every finding the adjudicator ruled valid:

1. Confirm it against the code.
2. Fix it in this PR, never in a follow-up.
3. Add or update tests.
4. Run focused, then broader, validation.
5. Push and wait for the checks to update.
6. Review the new head before merging: any change to the PR head after the review of record, fixes included, needs a review at the new head.
   A round-2 or later delta review of the change since the last reviewed head, plus any regressions it introduced, is enough (see `references/code-review.md`, Rounds).

Post the review of record on the PR as one comment (head SHA, findings, verdict per finding, fix commit per valid finding, the models used) **before** attempting the merge.
Resolve a human review thread only after its issue is fixed or explicitly ruled a false positive or out of scope.

## 9. Merge readiness

The PR is merge-ready only when all are true:

- The acceptance criteria are satisfied and test coverage is adequate.
- The pre-PR gate converged, or its residual findings were explicitly justified.
- Any completed optional review has no unresolved Critical or High finding.
- Every legitimate Medium finding is handled or justified.
- The review of record completed at the current head, every valid finding is fixed, and its comment is posted and visible.
- All required checks are green.
- The branch holds only intended changes, targets `profile.git.integration_branch`, and is mergeable.

Any change to the head after the review of record, including the fixes for its findings and an update-branch, makes the review stale: review the new head (a delta review suffices) before merging.

## 10. Merge

Only once step 9 holds:

- If `profile.review.merge_owner` is `agent`: merge with `profile.git.merge_method` per `references/github.md`, then confirm the PR is actually merged.
- If it is `human`: tell the user the PR is merge-ready (link, head SHA, review-of-record comment) and wait; resume at step 11 once it is merged.

Never merge with failing required checks or before the review of record is clean on head.

## 11. Deploy and verify

1. Find the environment in `profile.environments` whose `branch` is the integration branch.
2. Deploy as its `deploy` value says; if deployment is automatic, observe it rather than triggering a duplicate.
3. Monitor the deployment to completion.
4. Confirm the deployed build is the merged commit using its `verify` value, then run any smoke or health checks the overlay names.

Never claim a deployment succeeded without observing the result.
Promotion beyond the integration environment follows `profile.git.promotion` and `references/github.md`.

## 12. Deployment review

Only after the deployment is verified:

1. Move the story to `profile.tracker.states.in_deployment_review` (never on merge alone).
2. Add a concise implementation and deployment note.
3. Read the story back to confirm the state.

Done comes later, after the acceptance criteria are verified in the deployed environment (see `references/linear.md`).

## Operational rules

- Keep the user informed at major gates, not every command.
- Never claim an external action succeeded without verifying it.
- The pre-PR gate and the review of record are separate stages; never count a pre-PR review run as the PR review.
- Keep at most one invocation of a given CLI reviewer in flight at a time.
- Reviewers, optional reviewers and adjudicators never modify code.
- Never open the PR with unresolved Critical or High findings from the pre-PR gate.
- Never use AI review output as proof that tests pass; run the tests.
- Never resolve review threads without addressing the underlying finding.
- Never force-push; never write secrets to files or command arguments.
- Prefer small, reviewable commits and preserve the repository's conventions, scripts, CI and PR template.

[scripts/pr-status.sh](scripts/pr-status.sh) prints the current branch's PR state, checks and comments.

## Completion summary

Report:

- the story and its final state;
- slices completed;
- tests and checks run;
- pre-PR gate result (phases run, escalation rounds if any, findings resolved or justified);
- the PR link;
- each optional reviewer's result, or "skipped";
- the review of record result, with models, and findings resolved or rejected;
- the merge result (or that it awaits a human merge);
- the deployment and verification result.

If any gate could not be completed, name it and why.
