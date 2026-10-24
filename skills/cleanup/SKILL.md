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

## Boundaries

- It removes only artefacts it can attribute to a named key, in the repositories and directories the profile names.
  Everything else is left out and named as skipped.
- It never removes work that has not landed, and it never forces a removal.
- It never edits, reviews, or verifies a story, and it never moves a story's status.
- It reads no credential and writes none: every tracker and hosting call uses the credential its own CLI already holds.

## Completion summary

Report per story: the state of the key, what was removed, what was archived to the tracker with its attachment names, what was skipped and why, and what it refused to touch.
