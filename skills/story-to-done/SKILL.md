---
name: story-to-done
description: >-
  Drive one Linear story from implementation to Done: a senior-engineer subagent implements it through engineering-workflow and takes it to deployment review, then a QA subagent verifies it through qa-verification, and every item QA rules not met goes back to the senior engineer until nothing keeps the story from Done.
  Takes the story identifier plus optional model and reasoning effort for each role (defaults: each role's seat in the profile, effort high when the seat sets none; with neither, it asks).
  Use when asked to implement a story and see it through QA to Done (for example "story to done ABC-123" or "implement ABC-123, QA it, and fix until done, QA on <model> at max").
  Not for implementing without QA (use engineering-workflow), verifying a story without fixing it (use qa-verification), or staff-level triage, planning, and shadow adjudication (use persona-staff-engineer).
license: Apache-2.0
compatibility: Requires a runtime that can spawn subagents and set each one's model and reasoning effort, plus the linear CLI (schpet/linear-cli) with jq, or the Linear MCP server.
---

# Story to Done: implement, QA, fix until Done

You run the loop; you do not write the code or run the QA yourself.

## Arguments

`STORY_ID` is required: any Linear issue key (for example `ABC-123`).
Its team prefix is the team for every read and write this skill performs on or for that issue, and it need not equal `profile.tracker.team_key`.
If none was given, ask the user for one before doing anything else; never guess a story number.

Five arguments are optional, given as `key=value` or in plain words ("QA on <model> at max" sets `qa-model` and `qa-effort`):

| Argument | Sets | Default |
|---|---|---|
| `engineer-model` | the senior engineer's model | `profile.story_to_done.engineer` |
| `engineer-effort` | the senior engineer's reasoning effort | seat effort (default high) |
| `qa-model` | the QA agent's model | `profile.story_to_done.qa` |
| `qa-effort` | the QA agent's reasoning effort | seat effort (default high) |
| `metrics` | whether the run collects and reports run metrics | `off` |

- An argument left out takes its default.
- Effort is one of `low`, `medium`, `high`, `xhigh`, or `max`.
- If a value is ambiguous (an unknown model, an effort outside that list), ask the user; never guess.
- After step 0 creates the todo list, map each model and effort to your runtime with `references/runtimes.md`.
  If the runtime cannot run that exact model or effort level, stop and say so; never substitute another model or level.
- `metrics` is given as `metrics=on` or `metrics=off`, or in plain words: "with metrics" and "metrics on" mean on, "without metrics" and "metrics off" mean off; ask the user about any other phrasing about metrics; never guess.
- Resolve `metrics` before step 0 creates the todo list; it sets no model or effort.
- With `metrics` off or omitted, read no metrics reference, collect no figure, create no metrics file, post no metrics comment, and add no metrics content to any brief, report, todo list, or tracker write, other than the `metrics: off` line.
- Write the four resolved model and effort values and the `metrics: on|off` line at the top of your todo list and in the closing report of every end state (the step 5 report, or the report made at any stop, including one before step 0).

### Seat resolution

The engineer seat is `profile.story_to_done.engineer` and the QA seat is `profile.story_to_done.qa`, read from the profile the chain in [references/profile.md](references/profile.md) selects (Find the profile), right after step 0 creates the todo list and before step 1.
A value not yet resolved is written as `unresolved` wherever the four values are written.

- Each value resolves on its own: the explicit argument, else the seat's field (`model` for a model, `effort` for an effort), else, for an effort only, `high`; a model has no default.
- An explicit argument overrides the seat field by field: it replaces only the value it names, and the seat's other fields still apply.
- When a seat argument is absent and the profile yields no usable value for it (no profile, no `profile.story_to_done` object, no `engineer` or `qa` entry, or an entry with no `model`), stop before spawning either role and ask the user for that seat's model and effort, asking only for the values the arguments left unset and the profile does not supply.
  A caller-supplied argument is used even when the seat entry is absent.
  Never fall back to a model id written in this skill, and never probe or fall back across a list of model ids.
- The seat's `runtime` decides the launch.
  `claude-code` or `opencode` is a subagent of that runtime, and a seat with no `runtime`, or no entry at all when the arguments supply its model, is a subagent of your own runtime.
  `command` is a separate process launched by the shell-launched agents rule in [references/runtimes.md](references/runtimes.md): fill `{model}`, `{effort}`, `{prompt_file}`, `{output_file}` and `{session_title}` in its `command` with the resolved model, the resolved effort, the brief's file, the file it hands back in, and a title unique to the launch.
  A seat whose runtime you cannot launch, such as an `opencode` seat under another runtime, stops the skill before either role is spawned: say which seat and why.
- One resolved seat serves its role in every round, unchanged: the senior engineer goes back to it for each fix round, and each new QA round spawns a new agent on it.
  A `command` seat is never resumed: step 4 hands the senior engineer's failed items to a new launch on the same seat with the step 2 brief, and a QA resume that step 0 or step 4 calls for is one the runtime cannot make.

These seats reuse the refinement seat pattern of `profile.refinement`, with four differences: no `family` field and no rule that the two seats sit on distinct families; an explicit argument overrides the profile field by field; one resolved seat is reused unchanged in every round, with QA respawned on the same seat; and a `command` seat launches by the shell-launched agents rule rather than as a resumed subagent.

## Read first

Step 0 creates the todo list before any file below is read.

- [references/profile.md](references/profile.md) - find the profile and this skill's overlay right after step 0 creates the todo list.
- [references/runtimes.md](references/runtimes.md) - maps todo list, subagents, model and effort, scratch directory and asking the user to your runtime.

Read each of these at the step that needs it:

- [references/todo-tracking.md](references/todo-tracking.md) - step 0, and every subagent brief.
- [references/linear.md](references/linear.md) - steps 1, 4, and 5: the status lifecycle and never done on merge alone.
- [references/code-review.md](references/code-review.md) - steps 2 and 3: what a clean, neutral delegated engineer and QA agent may and may not be told.
- [references/secrets.md](references/secrets.md) - its rules go into every brief.

Where this file and a capability file disagree, the capability file wins.

## Metrics

Only when `metrics` is on, read [references/metrics.md](references/metrics.md) right after step 0 creates the todo list: it is the single home for what a `story-to-done` run collects and reports, and this file does not restate it.

The run rules for a `metrics=on` run - where the figures live, timed launches, extras, the start form, the command wrapper, the end form, the summary post, and the closing report - are in [references/metrics-protocol.md](references/metrics-protocol.md); read it with the runtime's file-read tool, which launches nothing, together with `references/metrics.md`, after step 0 creates the todo list and before the first command is launched.

- **Usage:** Each launch's Tokens and Tool calls are read as the "Read a subagent's usage" row and the "Usage from shell-launched agents" rule in [references/runtimes.md](references/runtimes.md) state; this section states no usage formula of its own.

With `metrics` on, launch no command before the start form, not even to read a file or list a directory, except the scratch-directory creation that the step 0 checklist fallback needs when no todo tool exists, whose directory the start form then uses; after step 0 creates the todo list, read this skill's references and the profile with the runtime's file-read tool, which launches nothing.

## 0. Track everything on a todo list

Create the todo list as your first action, before you read any reference, the profile, or an overlay.
The only actions before it are the ones Arguments orders before step 0: resolving the arguments, asking the user about a missing story ID or any ambiguous value.
With no todo tool, compose the primary-session checklist first; only placing its file may then create its scratch directory when it does not exist yet and, when the runtime's scratch base is `profile.workspace.scratch_dir`, read that one key, and no other profile content is read before the checklist file exists.
Create it from this file alone as a bootstrap list: one item per file Read first names, including the profile and overlay those files locate, then one item per step 1 to 5.
After reading `references/todo-tracking.md`, expand the list to the seed items below, at the granularity that file requires, before your first investigation, edit, command, or delegation, and add the items that need the story or the profile as soon as they are known.
Seed it with at least: read the story state, spawn the senior engineer, each check on its checklist until it hands back, the checklist read-back at each handback with each subagent's read-back resume count, read back the deployment-review state, each QA round, each read-back of QA's state, each failed item handed back, each fix round, and the final state read-back.
With `metrics` on, seed two more items: collect the metrics figures; then post the metrics summary on the story and read it back before giving the summary in the closing report.
Add an item for each new round as it starts; mark each done once its outcome is observed.
Every subagent brief requires a checklist file in that subagent's own subdirectory of the scratch directory; read it from there and mirror it into your list whenever you check on the subagent.
When a senior engineer or QA agent hands back, read that subagent's checklist file before acting on the result; a missing or unreadable checklist counts as open items.
If items remain open with no stated blocker, resume that subagent with "Your checklist still has open items. Continue with them; if one is blocked, say what blocks it", at most twice per subagent, and then record the remaining items in your report and continue with this skill's existing step logic.
An open item the handback itself names, with what it waits on or who owns it, has a stated blocker.
The tracker state remains the record of completion; the checklist is never evidence that work is done.
A read-back never overrides the tracker state: after a read-back resume, the next step reads the state again and acts on it.
If the runtime cannot resume the subagent, record the open items and continue with this skill's existing step logic; spawn no new subagent for the read-back.
A read-back resume of the QA agent happens before step 4 handling, carries no verdict, does not increment the round count, and has a cap separate from step 4's "once per observed change to the remainder".
The items QA's handback names as outstanding with what they wait on or who owns them go to step 4's classification and never to a read-back resume, so a mixed remainder is reported and stopped as step 4 says; a read-back resume of QA applies to every other open checklist item, including one the handback names with no stated blocker.
With `metrics` on, each read-back resume is its own launch row.
If your todo tool is unavailable, use the primary-session checklist fallback in `references/todo-tracking.md`; never block.

## 1. Read the story and pick the starting point

Read the story and its state with the `linear` CLI, or the Linear MCP server if it fails.
When the team of `STORY_ID` differs from `profile.tracker.team_key`, confirm each state name below on that team before comparing against it, under the differing-team rule in Team resolution in [references/linear.md](references/linear.md).

- `profile.tracker.states.in_deployment_review`: implementation already reached deployment review; go to step 3.
- `profile.tracker.states.done`: report that there is nothing to do and stop.
- `profile.tracker.states.blocked`, `profile.tracker.states.canceled`, or `profile.tracker.states.duplicate`: report the state and stop.
- Any other state: go to step 2.

Do not triage the story yourself; `engineering-workflow` does, including the Definition of Ready.

## 2. Senior engineer: implement to deployment review

Spawn a clean, neutral subagent on `engineer-model` at `engineer-effort`, and brief it as a senior engineer working this story.
It spawns reviewers of its own, and so does the QA agent in step 3, so check the nesting rule in `references/runtimes.md` first.
Where nesting is restricted, give both delegated agents nesting per that runtime map, or launch their review roles as shell commands (`runtime: command`, `codex` or `opencode`).
The nesting rule's primary-session option does not fit this skill, since each role finishes its own gates first.
If neither works, stop and say so.
The brief carries facts and constraints, never your expectations about the outcome.
It must include:

- The story identifier.
- An instruction to load and follow `engineering-workflow` for the whole story, from triage, the pre-PR gate and the PR to `profile.git.integration_branch` to the merge per `profile.review.merge_owner`, the deploy, and the move to `profile.tracker.states.in_deployment_review`.
- What to hand back: the story state, each PR link, the head SHA each PR's review of record covered, the merged commit, and the environment and deployed build it verified; or, if it stops, that it is blocked and why, including when no arbiter can launch; a missing arbitration is never clean or converged.
- Keep working until everything the brief asks for is done, and only stop to ask when you can't go on without the coordinator or before a risky step. The stop this brief already defines still holds: if you must stop, hand back blocked and say why.
- The real-check rule: report a change done only with the output of a real check that exercises it (tests, type-checker, build, the changed command, or for infrastructure a plan or dry run against the target); a syntax-only check, or a check that failed to start, does not count. Install declared dependencies only with the project's own package manager and lockfile, never with sudo or the system package manager. If no real check can run, the report names the check not run and why.
- When the work in the brief is done, stop and report. Don't add features, tests, files, docs or refactors the brief or the story's acceptance criteria don't call for. The tests the real-check rule needs are called for by this brief.
- Don't start review or hardening rounds, or launch reviewer subagents, beyond the review gates this brief and the skills it tells you to load define. The pre-PR gate and the review of record that `engineering-workflow` defines stay allowed.
- The merge rules: a review of record binds only to the exact head it reviewed, so any change to the head, including an update-branch, needs a delta review posted before merging; every merge must run the merge guard in `references/code-review.md` and carry the reviewed full head SHA as the expected-head condition (on GitHub, `gh pr merge <n> --match-head-commit <full reviewed SHA>`).
- The engineer never does pre-PR arbitration (`adversarial-review-pipeline` Phase 3, `engineering-workflow` step 4 Verify stage) or rules a finding valid, invalid or accepted risk or the gate converged (applying the gate's scope guard is not arbitration), and fixes what QA ruled not met or the adjudicator ruled valid without overturning those rulings; a separate clean, neutral arbiter on `profile.review.pre_pr.arbiter`, independent of engineer and coordinator, arbitrates every head.
- The scope rule: the engineer never changes an acceptance criterion on any story ([references/linear.md](references/linear.md) "Acceptance criteria and scope"). Code never carries skips, pending lists, or exemptions keyed on another story landing later (for example "skip if directory X is absent" or an exemption entry naming another tracker story's key). A story that needs another story's artifact is blocked by that story; a guard spanning several stories' files belongs in a story blocked by all of them. The only exceptions allowed are permanent exemptions that depend on no other story and carry a why note; that allowance covers test, lint, and build exemptions and does not relax "Do not hide failures". For both rules the only two exits are a "Refinement proposal (not an AC)" or reporting the story blocked, as that section states.
- The git rule: run every commit-creating git command with the git identity already configured and, when `profile.git.signed_commits` is true, the signing already configured; never pass `-c user.name`, `-c user.email`, `--author`, `GIT_AUTHOR_*` or `GIT_COMMITTER_*`, never write `user.name` or `user.email` with `git config`, and when signing is on never pass `-c user.signingkey`, `-c gpg.*` or `-c commit.gpgsign`; a missing identity, a failed signing check or a pushed commit whose `.commit.verification.verified` is false is a configuration fault, so stop, do not override per command or write git config, make no further commits, and report it to the user.
- The secrets rule (never write secrets to files or argv) and the attribution rule from `profile.git.ai_attribution`.
- The shell rule: run each shell step as one simple command with literal values; never assign a variable and use it in the same command (`W=<path>; git -C $W ...`) - write the literal path; never feed a `$(...)` result into a later argument of the same command - run the inner command as its own call and use its literal output in the next call; and never prefix a command with an inline `VAR="$SECRET"` assignment - rely on the credential the session environment or the tool's own credential configuration already provides (for `gh`, its stored auth), and never set a credential per command.
- Its own subdirectory of the scratch directory, `<scratch>/senior-engineer/`, which you create and hand it in place of the scratch directory itself, never another role's files.
- A "Track your work" paragraph: before starting, write a fine-grained checklist file at the full path you give it in that subdirectory (`<scratch>/senior-engineer/senior-engineer-todo.md`, `- [ ]` and `- [x]` items, one per slice step, test, gate round, review round, remediation, deploy, verification, and wait, the current step marked `(in progress)`) and update it at every step.

This skill assigns merge approval to no manager, so `engineering-workflow`'s own merge rules apply.
Let the senior engineer do the engineering; do not pre-empt its choices.
The engineer never does pre-PR arbitration (`adversarial-review-pipeline` Phase 3, `engineering-workflow` step 4 Verify stage) or rules a finding valid, invalid or accepted risk or the gate converged (applying the gate's scope guard is not arbitration), and fixes what QA ruled not met or the adjudicator ruled valid without overturning those rulings; a separate clean, neutral arbiter on `profile.review.pre_pr.arbiter`, independent of engineer and coordinator, arbitrates every head.

When it hands back, do the step 0 checklist read-back first, then read the story yourself and confirm it is in `profile.tracker.states.in_deployment_review`; a handback is a claim, the tracker is the record.
If it handed back blocked or the story is not in deployment review, stop and report why.
Then, for every PR it merged, read the PR yourself with `gh pr view <n> --json headRefOid,mergeCommit` and `gh api --paginate repos/<owner>/<repo>/pulls/<n>/reviews`.
Select the review of record as the merge guard in `references/code-review.md` does (the `COMMENTED` review whose body begins with `Review of record` and has the greatest `submitted_at`).
Compare the merged PR's `headRefOid` (its head at merge, not the merge commit) separately with that review's `commit_id` and with the full head SHA on its first line.
Except under the explicit per-PR review waiver in The gate, a missing review, a missing SHA, or either mismatch is reported with the PR and all available SHAs, and stops the loop.
For a waived PR, compare the merged PR's `headRefOid` with the SHA recorded when the user gave the instruction; report and stop if that SHA is missing or differs.

## 3. QA agent: verify the deployed story

Spawn a new clean, neutral subagent on qa-model at qa-effort for every new QA round; never resume an agent from an earlier round, since it carries that round's conclusions.
Continuation of the current round under step 4 and the step 0 checklist read-back resume of the current round's QA agent are the only exceptions to that sentence, and neither increments the round count.
A stop for an owner action ends the round: once the owner clears it, that round's work starts over as a new round under this step with a new QA agent, and a fix/deploy cycle or an amended acceptance basis likewise starts a new round.
Brief it as a QA agent, with only:

- The story identifier and the environment under test: the environment the senior engineer deployed to.
  When step 2 did not run in this engagement, use the environment the user named; if they named none, leave it out so `qa-verification` picks its default.
- An instruction to load and follow `qa-verification` for the story, including its evidence and its closing status decision.
- What to hand back: the story's final state, the verdict and evidence for each AC and DoD item, any item left outstanding with its owner, any incidental defect it noted, and each PR it merged with the head SHA its review of record covered.
- Keep working until everything the brief asks for is done, and only stop to ask when you can't go on without the coordinator or before a risky step. The stop this brief already defines still holds: hand back any item left outstanding with its owner.
- Don't start review or hardening rounds, or launch reviewer subagents, beyond the review gates this brief and the skills it tells you to load define. The pre-PR gate and the review of record that `engineering-workflow` defines, and the evidence PR's review of record that `qa-verification` defines, stay allowed.
- The merge rules: a review of record binds only to the exact head it reviewed, so any change to the head, including an update-branch, needs a delta review posted before merging; every merge must run the merge guard in `references/code-review.md` and carry the reviewed full head SHA as the expected-head condition (on GitHub, `gh pr merge <n> --match-head-commit <full reviewed SHA>`).
- Its own subdirectory of the scratch directory, `<scratch>/qa-agent-round-<n>/`, which you create and hand it in place of the scratch directory itself, never another role's files.
- The git rule: run every commit-creating git command with the git identity already configured and, when `profile.git.signed_commits` is true, the signing already configured; never pass `-c user.name`, `-c user.email`, `--author`, `GIT_AUTHOR_*` or `GIT_COMMITTER_*`, never write `user.name` or `user.email` with `git config`, and when signing is on never pass `-c user.signingkey`, `-c gpg.*` or `-c commit.gpgsign`; a missing identity, a failed signing check or a pushed commit whose `.commit.verification.verified` is false is a configuration fault, so stop, do not override per command or write git config, make no further commits, and report it to the user.
- The secrets rule and a "Track your work" paragraph (checklist file at the full path you give it, `<scratch>/qa-agent-round-<n>/qa-agent-round-<n>-todo.md`).
- The shell rule: run each shell step as one simple command with literal values; never assign a variable and use it in the same command (`W=<path>; git -C $W ...`) - write the literal path; never feed a `$(...)` result into a later argument of the same command - run the inner command as its own call and use its literal output in the next call; and never prefix a command with an inline `VAR="$SECRET"` assignment - rely on the credential the session environment or the tool's own credential configuration already provides (for `gh`, its stored auth), and never set a credential per command.

Never give it the senior engineer's handback beyond the environment, the PR's rationale, the fixes made, an earlier round's verdicts, or the verdict you expect.

When it hands back, do the step 0 checklist read-back first, then read the story's state yourself.
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
  Hand them back to the senior engineer: resume the same subagent if the runtime can, else spawn a new clean, neutral one on the same seat with the step 2 brief.
  Either way, add to the hand-back brief each failed item as QA recorded it on the story (the item, its verdict, and the evidence it cites), and instruct the engineer to fix them through `engineering-workflow` on this story and take it back to `profile.tracker.states.in_deployment_review`.
  Confirm that state as step 2 does, then run step 3 again with a new QA agent.
- **`profile.tracker.states.in_deployment_review`:** QA is not finished: one or more items in its handback are outstanding.
  Classify each outstanding item by its owner.
  This classification covers only the items QA's handback names with what they wait on or who owns them: an open item with no stated blocker or owner goes to step 0's read-back resume first, even when QA could finish it itself, and is never step 4's continuation.
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
