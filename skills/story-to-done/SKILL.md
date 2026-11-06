---
name: story-to-done
description: >-
  Drive one Linear story from implementation to Done: a senior-engineer subagent implements it through engineering-workflow and takes it to deployment review, then a QA subagent verifies it through qa-verification, and every item QA rules not met goes back to the senior engineer until nothing keeps the story from Done.
  Takes the story identifier plus optional model and reasoning effort for each role (defaults: senior engineer Sonnet 5.5 at high, QA Opus 5.5 at high).
  Use when asked to implement a story and see it through QA to Done (for example "story to done ABC-123" or "implement ABC-123, QA it, and fix until done, QA on Opus 5.5 at max").
  Not for implementing without QA (use engineering-workflow), verifying a story without fixing it (use qa-verification), or staff-level triage, planning, and shadow adjudication (use persona-staff-engineer).
license: Apache-2.0
compatibility: Requires a runtime that can spawn subagents and set each one's model and reasoning effort, plus the linear CLI (schpet/linear-cli) with jq, or the Linear MCP server.
---

# Story to Done: implement, QA, fix until Done

You run the loop; you do not write the code or run the QA yourself.

## Arguments

`STORY_ID` is required: a Linear story identifier (for example `ABC-123`, with the team key `profile.tracker.team_key`).
If none was given, ask the user for one before doing anything else; never guess a story number.

Five arguments are optional, given as `key=value` or in plain words ("QA on Opus 5.5 at max" sets `qa-model` and `qa-effort`):

| Argument | Sets | Default |
|---|---|---|
| `engineer-model` | the senior engineer's model | Sonnet 5.5 (`claude-sonnet-5-5`) |
| `engineer-effort` | the senior engineer's reasoning effort | `high` |
| `qa-model` | the QA agent's model | Opus 5.5 (`claude-opus-5-5`) |
| `qa-effort` | the QA agent's reasoning effort | `high` |
| `metrics` | whether the run collects and reports run metrics | `off` |

- An argument left out takes its default.
- Effort is one of `low`, `medium`, `high`, `xhigh`, or `max`.
- If a value is ambiguous (an unknown model name, an effort outside that list), ask the user; never guess.
- Map each model and effort to your runtime with `references/runtimes.md`.
  If the runtime cannot run that exact model or effort level, stop and say so; never substitute another model or level.
- Each role keeps the same model and effort in every round.
- `metrics` is given as `metrics=on` or `metrics=off`, or in plain words: "with metrics" and "metrics on" mean on, "without metrics" and "metrics off" mean off; ask the user about any other phrasing about metrics; never guess.
- Resolve `metrics` before step 0 creates the todo list; it sets no model or effort.
- With `metrics` off or omitted, read no metrics reference, collect no figure, create no metrics file, post no metrics comment, and add no metrics content to any brief, report, todo list, or tracker write, other than the `metrics: off` line.
- Write the four resolved model and effort values and the `metrics: on|off` line at the top of your todo list and in the closing report of every end state (the step 5 report, or the report made at any stop, including one before step 0).

## Read first

- [references/profile.md](references/profile.md) - find the profile and this skill's overlay as soon as the story ID is known.
- [references/runtimes.md](references/runtimes.md) - maps todo list, subagents, model and effort, scratch directory and asking the user to your runtime; read its nesting rule before step 2.

Read each of these at the step that needs it:

- [references/todo-tracking.md](references/todo-tracking.md) - step 0, and every subagent brief.
- [references/linear.md](references/linear.md) - steps 1, 4, and 5: the status lifecycle and never done on merge alone.
- [references/code-review.md](references/code-review.md) - steps 2 and 3: what a clean, neutral delegated engineer and QA agent may and may not be told.
- [references/secrets.md](references/secrets.md) - its rules go into every brief.

Where this file and a capability file disagree, the capability file wins.

## Metrics

Only when `metrics` is on, read [references/metrics.md](references/metrics.md) once the story ID is known: it is the single home for what a `story-to-done` run collects and reports, and this file does not restate it.

The run rules for a `metrics=on` run - where the figures live, timed launches, extras, the start form, the command wrapper, the end form, the summary post, and the closing report - are in [references/metrics-protocol.md](references/metrics-protocol.md); read it with the runtime's file-read tool, which launches nothing, together with `references/metrics.md`, before the first command is launched.

- **Usage:** Each launch's Tokens and Tool calls are read as the "Read a subagent's usage" row and the "Usage from shell-launched agents" rule in [references/runtimes.md](references/runtimes.md) state; this section states no usage formula of its own.

With `metrics` on, launch no command before the start form, not even to read a file or list a directory; read this skill, its references and the profile with the runtime's file-read tool, which launches nothing.

## 0. Track everything on a todo list

Once the story ID is known and the profile is read, create a fine-grained todo list per `references/todo-tracking.md`.
Seed it with at least: resolve the arguments, read the story state, spawn the senior engineer, each check on its checklist until it hands back, read back the deployment-review state, each QA round, each read-back of QA's resulting state, each failed item handed back, each fix round, and the final state read-back.
With `metrics` on, seed two more items: collect the metrics figures; then post the metrics summary on the story and read it back before giving the summary in the closing report.
Add an item for each new round as it starts; mark each item done once its outcome is observed.
Every subagent brief requires a checklist file in that subagent's own subdirectory of the scratch directory; read it from there and mirror it into your list whenever you check on the subagent.
If your todo tool is unavailable, use the primary-session checklist fallback in `references/todo-tracking.md`; never block.

## 1. Read the story and pick the starting point

Read the story and its state with the `linear` CLI, or the Linear MCP server if it fails.

- `profile.tracker.states.in_deployment_review`: implementation already reached deployment review; go to step 3.
- `profile.tracker.states.done`: report that there is nothing to do and stop.
- `profile.tracker.states.blocked`, `profile.tracker.states.canceled`, or `profile.tracker.states.duplicate`: report the state and stop.
- Any other state: go to step 2.

Do not triage the story yourself; `engineering-workflow` does, including the Definition of Ready.

## 2. Senior engineer: implement to deployment review

Spawn a clean, neutral subagent (not a fork of yours) on `engineer-model` at `engineer-effort`, and brief it as a senior engineer working this story.
It spawns reviewers of its own, and so does the QA agent in step 3, so check the nesting rule in `references/runtimes.md` first.
Where nesting is restricted, give both delegated agents nesting per that runtime map, or launch their review roles as shell commands (`runtime: command`, `codex` or `opencode`).
The nesting rule's primary-session option does not fit this skill, since each role finishes its own gates first.
If neither works, stop and say so.
The brief carries facts and constraints, never your expectations about the outcome.
It must include:

- The story identifier.
- An instruction to load and follow `engineering-workflow` for the whole story, from triage, the pre-PR gate and the PR to `profile.git.integration_branch` to the merge per `profile.review.merge_owner`, the deploy, and the move to `profile.tracker.states.in_deployment_review`.
- What to hand back: the story state, each PR link, the head SHA each PR's review of record covered, the merged commit, and the environment and deployed build it verified; or, if it stops, that it is blocked and why, including when no arbiter can launch; a missing arbitration is never clean or converged.
- The merge rules: a review of record binds only to the exact head it reviewed, so any change to the head, including an update-branch, needs a delta review posted before merging; every merge must run the merge guard in `references/code-review.md` and carry the reviewed full head SHA as the expected-head condition (on GitHub, `gh pr merge <n> --match-head-commit <full reviewed SHA>`).
- The engineer never does pre-PR arbitration (`adversarial-review-pipeline` Phase 3, `engineering-workflow` step 4 Verify stage) or rules a finding valid, invalid or accepted risk or the gate converged (applying its scope guard is not arbitration), and fixes QA and adjudicator rulings without overturning them; a separate clean, neutral arbiter on `profile.review.pre_pr.arbiter`, independent of engineer and coordinator, arbitrates every head.
- The secrets rule (never write secrets to files or argv) and the attribution rule from `profile.git.ai_attribution`.
- Its own subdirectory of the scratch directory, `<scratch>/senior-engineer/`, which you create and hand it in place of the scratch directory itself, never another role's files.
- A "Track your work" paragraph: before starting, write a fine-grained checklist file at the full path you give it in that subdirectory (`<scratch>/senior-engineer/senior-engineer-todo.md`, `- [ ]` and `- [x]` items, one per slice step, test, gate round, review round, remediation, deploy, verification, and wait, the current step marked `(in progress)`) and update it at every step.

This skill assigns merge approval to no manager, so `engineering-workflow`'s own merge rules apply.
Let the senior engineer do the engineering; do not pre-empt its choices.
The engineer never does pre-PR arbitration (`adversarial-review-pipeline` Phase 3, `engineering-workflow` step 4 Verify stage) or rules a finding valid, invalid or accepted risk or the gate converged (applying its scope guard is not arbitration), and fixes QA and adjudicator rulings without overturning them; a separate clean, neutral arbiter on `profile.review.pre_pr.arbiter`, independent of engineer and coordinator, arbitrates every head.

When it hands back, read the story yourself and confirm it is in `profile.tracker.states.in_deployment_review`; a handback is a claim, the tracker is the record.
If it handed back blocked, or the story is not in deployment review, stop and report why.
Then, for every PR it merged, read the PR yourself with `gh pr view <n> --json headRefOid,mergeCommit` and `gh api --paginate repos/<owner>/<repo>/pulls/<n>/reviews`.
Select the review of record as the merge guard in `references/code-review.md` does (the `COMMENTED` review whose body begins with `Review of record` and has the greatest `submitted_at`).
Compare the merged PR's `headRefOid` (its head at merge, not the merge commit) separately with that review's `commit_id` and with the full head SHA on its first line.
Except under the explicit per-PR review waiver in The gate, a missing review, a missing SHA, or either mismatch is reported with the PR and all available SHAs, and stops the loop.
For a waived PR, compare the merged PR's `headRefOid` with the SHA recorded when the user gave the instruction; report and stop if that SHA is missing or differs.

## 3. QA agent: verify the deployed story

Spawn a new clean, neutral subagent on qa-model at qa-effort for every new QA round; never resume an agent from an earlier round, since it carries that round's conclusions.
Continuation of the current round under step 4 is the sole exception to that sentence, and a continuation never increments the round count.
A stop for an owner action ends the round: once the owner clears it, that round's work starts over as a new round under this step with a new QA agent, and a fix/deploy cycle or an amended acceptance basis likewise starts a new round.
Brief it as a QA agent, with only:

- The story identifier and the environment under test: the environment the senior engineer deployed to.
  When step 2 did not run in this engagement, use the environment the user named; if they named none, leave it out so `qa-verification` picks its default.
- An instruction to load and follow `qa-verification` for the story, including its evidence and its closing status decision.
- What to hand back: the story's final state, the verdict and evidence for each AC and DoD item, any item left outstanding with its owner, any incidental defect it noted, and each PR it merged with the head SHA its review of record covered.
- The merge rules: a review of record binds only to the exact head it reviewed, so any change to the head, including an update-branch, needs a delta review posted before merging; every merge must run the merge guard in `references/code-review.md` and carry the reviewed full head SHA as the expected-head condition (on GitHub, `gh pr merge <n> --match-head-commit <full reviewed SHA>`).
- Its own subdirectory of the scratch directory, `<scratch>/qa-agent-round-<n>/`, which you create and hand it in place of the scratch directory itself, never another role's files.
- The secrets rule and a "Track your work" paragraph (checklist file at the full path you give it, `<scratch>/qa-agent-round-<n>/qa-agent-round-<n>-todo.md`).

Never give it the senior engineer's handback beyond the environment, the PR's rationale, the fixes made, an earlier round's verdicts, or the verdict you expect.

When it hands back, read the story's state yourself.
For every PR it merged, such as the evidence PR, read the PR yourself with `gh pr view <n> --json headRefOid,mergeCommit` and `gh api --paginate repos/<owner>/<repo>/pulls/<n>/reviews`.
Select the review of record as the merge guard in `references/code-review.md` does (the `COMMENTED` review whose body begins with `Review of record` and has the greatest `submitted_at`).
Compare the merged PR's `headRefOid` (its head at merge, not the merge commit) separately with that review's `commit_id` and with the full head SHA on its first line.
Except under the explicit per-PR review waiver in The gate, a missing review, a missing SHA, or either mismatch is reported with the PR and all available SHAs, and stops the loop.
For a waived PR, compare the merged PR's `headRefOid` with the SHA recorded when the user gave the instruction; report and stop if that SHA is missing or differs.

## 4. Act on the QA outcome

- **`profile.tracker.states.done`:** confirm the completion record before you accept it.
  On read-back every AC and DoD box is ticked, QA's handback rules every item verified, and, when `profile.qa.evidence_dir` is set, the evidence PR is merged on the head its review of record covered.
  If all three hold, go to step 5; if any does not, report the mismatch and stop.
- **`profile.tracker.states.in_progress`:** QA ruled at least one AC or DoD item not met and reopened the story.
  Those failed items are the issues to fix.
  Hand them back to the senior engineer: resume the same subagent if the runtime can, else spawn a new clean, neutral one on the same model and effort with the step 2 brief.
  Either way, add to the hand-back brief each failed item as QA recorded it on the story (the item, its verdict, and the evidence it cites), and instruct the engineer to fix them through `engineering-workflow` on this story and take it back to `profile.tracker.states.in_deployment_review`.
  Confirm that state as step 2 does, then run step 3 again with a new QA agent.
- **`profile.tracker.states.in_deployment_review`:** QA is not finished: one or more items in its handback are outstanding.
  Classify each outstanding item by its owner.
  When at least one item is outstanding and every outstanding item is work the current QA agent itself can finish under its existing authority in the current round, such as an evidence PR it opened that is still unmerged with its review-of-record gate in flight, or a QA step still to run, step 4 resumes that same QA agent with a clean, neutral continuation message that states only that the round is unfinished and names that round's scratch subdirectory.
  The continuation message carries no verdict, no expected verdict, no earlier round's conclusions, no senior engineer handback, and nothing the coordinator observed after the handback.
  The continuation does not increment the QA round count, reuses that round's scratch subdirectory and checklist, and with `metrics` on is recorded as its own launch row within that same round.
  After each continuation handback, step 3's state and merged-PR review-of-record read-backs repeat in full before this step applies again.
  If any outstanding item names any other owner - the owner, a maintainer's approval or access grant, a human merge, an external deploy, a pending acceptance-basis ruling - report exactly what remains and who owns it, and stop, even when QA-owned work also remains; a mixed remainder containing both an owner action and QA's own steps is reported and stopped, never resumed.
  If the runtime cannot resume that QA session, report the limitation and stop; never substitute a new clean, neutral subagent for it as a continuation of that round.
  A continuation is made at most once per observed change to the remainder: when a resumed handback leaves the same remaining items with no observed progress, report the stall and stop.
- **`profile.tracker.states.blocked`:** report the blocking story and stop.
- **Any other state:** report it and stop.

If the senior engineer disputes a failed verdict or an adjudicator's ruling, do not relay its argument to a QA agent and do not rule on it yourself.
Stop and put the item, its evidence, and the engineer's evidence to the user, since what an AC means is the product owner's decision.

Incidental defects QA noted that do not keep the story from Done are not fixed in this loop; report them to the user.

After each round, tell the user its number, the failed items, and the outcome.

## 5. Close out

Read the story back and confirm it is in `profile.tracker.states.done` with the completion record step 4 checks, then finish your todo list.
Report the story identifier, its final state, the four resolved model and effort values and the `metrics: on|off` line, each PR, the number of QA rounds with the items fixed in each, where QA recorded its evidence, and any incidental defects left open.

## Boundaries

- You resolve the arguments, spawn the two roles, relay QA's failed items, and confirm every state; the senior engineer implements and the QA agent verifies, each through its own skill.
- Only a QA agent's closing decision moves the story to Done; never mark it done yourself, and never on merge alone.
- The coordinator never merges a PR, including the evidence PR; never ticks an AC or DoD box; never moves the story state; never decides a QA verdict; and never bypasses a review gate.
- With `metrics` on, the coordinator's single permitted tracker write is the summary comment, which it reads back and repeats in the closing report; with `metrics` off it makes no tracker write.
- A continuation grants no new authority: it leaves that prohibition, and the single permitted tracker write above, exactly as they are.
- The review of record and QA's own gates run in full inside each role's skill; this loop never shortens them.
