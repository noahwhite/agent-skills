---
name: cleanup
description: >-
  Remove every artefact a working session created for a Linear story - worktrees, local and remote branches, disposable QA output and scratch debris - and move the evidence the session hosted onto the story itself, under a guarded inventory that refuses anything still holding unmerged work.
  Use when asked to clean up, tidy up, or clear the artefacts of a story (for example "clean up ABC-123"), or to move a story's hosted evidence onto the tracker.
  Not for implementing or reviewing a story (use engineering-workflow), not for verifying one (use qa-verification), and not the `cleanup <path>` subcommand of the adversarial pre-PR pipeline script.
license: Apache-2.0
compatibility: Requires git, gh, and the linear CLI (schpet/linear-cli).
---

# Cleanup

Remove the artefacts a session created while working a Linear story, and move the evidence it hosted onto that story.
This is the last step of a story's life: the story ends with no leftover worktree, branch, or scratch debris, and with its evidence on the tracker rather than on a third-party host.
It deletes; it never implements, reviews, or verifies a story.

## Read first

- [references/profile.md](references/profile.md) - find the profile and this skill's overlay before anything else.
  Every value this skill names comes from the profile: the tracker team, the branch prefixes, the merge method, the scratch base, and the evidence directory.
- [references/todo-tracking.md](references/todo-tracking.md) - required before step 1: one item per named story key, per inventory source, per removal, per tracker attachment, and for the final report.
- [references/linear.md](references/linear.md) - steps 1, 5, and 6: resolving a story key, the refusal comment, and the tracker writes.
- [references/github.md](references/github.md) - steps 2 and 3: branches, worktrees, merge evidence, and deletion.
- [references/runtimes.md](references/runtimes.md) - step 4: the hosted-evidence capability row, and the capability mapping when a runtime is not listed.

## Invocation

The skill takes one or more story keys and nothing else:

```
/cleanup <story-key> [<story-key> ...]
```

- A story key is the whole input.
  The skill never infers a story from ambient context, from the current branch, or from a worktree path.
- With no story key it prints `usage: /cleanup <story-key> [<story-key> ...]` and stops without touching anything.
- This skill is not the `cleanup <path>` subcommand of the adversarial pre-PR pipeline: that one removes a throwaway checkout the script created and takes a path, never a story key.

## 0. Track the run on a todo list

Create the list before the first command, and update it after each step's outcome.
Give it one item per named story key, per inventory source, per removal, per tracker attachment, and for the final report, as [references/todo-tracking.md](references/todo-tracking.md) requires.

## 1. Resolve every key against the tracker

Do this before anything is touched, so a mistyped key removes nothing.

- Resolve each key with `linear issue view <story-key>`.
  A key does not resolve when that lookup fails, or when the story it returns belongs to a team other than `profile.tracker.team_key`.
- Report an unresolved key as `unresolved` and skip it.
  The other keys still run: one bad key never stops the run, and no artefact is attributed to it.
- Never invent, guess, or shorten a key, and never take one from the current branch, a worktree path, or the session's own history.
- Record each key's resolution in the final report.

## 2. Inventory every artefact before removing any

Print the inventory first: nothing is removed before the inventory report is printed.
Each line states the artefact, its path or URL, and its disposition, which is `remove`, `keep`, `skip`, or `refuse`.
Find artefacts by story key: a session's scratch directory is per-session and randomly named, so nothing can be located by the directory a session happens to be in.

Sources, all of them:

- **Worktrees.** Every entry `git worktree list` reports whose path or branch carries the key, which includes worktrees any worktree helper created.
- **Local branches.** Every branch whose name carries the key under a prefix in `profile.git.branch_prefixes`.
- **Remote branches.** Every head `git ls-remote --heads origin '*<key>*'` reports.
- **Pull requests.** Every PR `gh pr list --state all --search '<key>'` returns, each cited with its full URL.
- **Disposable QA output.** QA runner scratch output and uncommitted evidence copies only, in the scratch location the overlay's QA lane names, never a committed evidence directory.
- **Session files.** Session checklist and scratch files naming the key under `profile.workspace.scratch_dir`.

Never inventoried as removable:

- Evidence committed under `profile.qa.evidence_dir`: that directory is the durable record, so it is cited and never removed.
- Evidence `qa-verification` already attached to the story.
- The invoking session's own scratch directory.
- The merge-approval rendezvous file an engagement's brief names, because it belongs to the engagement rather than to a story.

Two more rules:

- A per-session scratch directory is inventoried as `skip` once its checklist file still carries an unchecked item, because that session is still live.
  Only the individual files naming the key are removed from a directory the run can prove idle.
- Anything the skill cannot attribute to the key is left out, and the report names it as skipped.

## 3. Delete only with merge evidence

Nothing is deleted while it still holds unmerged or unreviewed work.
Before each removal, establish merge evidence from the story's pull requests:

- A merged PR whose head commit is the branch tip: `gh pr view <n> --json state,headRefOid` reports `MERGED`, and its `headRefOid` equals the tip from `git rev-parse <branch>`.
- Containment, only when `profile.git.merge_method` is neither `squash` nor `rebase`: `git merge-base --is-ancestor <branch-tip> origin/<profile.git.integration_branch>`.
  Under a squash or a rebase merge the integration branch holds a different commit, so containment proves nothing and is never used.

Then, per artefact kind:

- **Local branch.** Removed with `git branch -D` once it has merge evidence.
  `-D` rather than `-d`, because a squash or a rebase merge leaves the tip unmerged in git's own eyes.
- **Worktree.** Removed with `git worktree remove` only when `git status --porcelain` is empty inside it, and only when it is not the worktree hosting the current session.
  A worktree hosting the current session is refused, because removing it deletes the ground the run stands on.
- **Remote branch.** Deleted with `git push origin --delete <branch>` only when no open PR heads it: a branch named by `gh pr list --state open --json headRefName` is refused.
- **Disposable QA output and session files.** Removed only from a directory the inventory proved idle.

Guards that hold for every removal:

- `--force` is never used, on any command, and a removal that would need it is refused instead.
- An artefact that fails a check is skipped, not forced, and the run continues with the others.
- Every refusal is recorded in the report and posted as a dated comment on the named story, naming the artefact, the failed check, and why.
- Each removal is confirmed by reading it back: `git branch`, `git worktree list`, or `git ls-remote --heads origin '*<key>*'` no longer lists it.

## 4. Hosted evidence (a self-contained, capability-detected section)

This section is separated on purpose: a consumer variant can drop it, or layer it through an overlay, without touching the rest of the skill.
It names no host and no runtime: both come from the hosted-evidence row of [references/runtimes.md](references/runtimes.md).

- Read that row for the runtime this session runs on.
  The row says whether the session can reach the evidence it hosted, and the mechanism to list it, download it, and delete it.
  A runtime the map does not list follows the map's unlisted rule: map the capability to the closest equivalent and say which one was used.
- When the row gives the runtime no such capability, print `skipped: this runtime has no hosted-evidence capability`, touch no hosted content, and name the skip and its reason in the final report.
- When it does, sweep only through the mapped mechanism: list the evidence this session hosted for the story, download it into the session's scratch directory, attach it to the named story as step 5 says, and delete the hosted copy only through the mapped delete action.
  With no mapped delete action the copy stays where it is, and the report names it as left in place.
- Detection never guesses.
  A capability the row gives but the session cannot reach fails the run loudly: print `error: hosted-evidence capability unreachable: <failure>` naming the failure, touch no hosted content, print the report so the work already done is not silent, and exit non-zero.
  That is never a silent skip and never a pass.
- There is no user-facing runtime switch: the map decides, never a flag, an argument, or a phrase in this text.

## Boundaries

- It removes only artefacts it can attribute to a named key, in the repositories and directories the profile names.
  Everything else is left out and named as skipped.
- It never removes work that has not landed, and it never forces a removal.
- It never edits, reviews, or verifies a story, and it never moves a story's status.
- It reads no credential and writes none: every tracker and hosting call uses the credential its own CLI already holds.

## Completion summary

Report per story: the state of the key, what was removed, what was archived to the tracker with its attachment names, what was skipped and why, and what it refused to touch.
