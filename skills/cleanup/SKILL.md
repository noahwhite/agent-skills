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
- [references/linear.md](references/linear.md) - background for the tracker: resolving an issue, the status lifecycle the run leaves alone, and the comment path.
  The exact commands this skill runs are in steps 1 and 5.
- [references/github.md](references/github.md) - background for branches, worktrees, and merges.
  The merge evidence this skill requires is stated in step 3, and it is stricter than the general rule there.
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

- Resolve each key with `linear issue view <story-key> --no-download`, so resolving a key writes no file.
  A key does not resolve when that lookup fails, or when the story it returns belongs to a team other than `profile.tracker.team_key`.
- Report an unresolved key as `unresolved` and skip it.
  The other keys still run: one bad key never stops the run, and no artefact is attributed to it.
- Never invent, guess, or shorten a key, and never take one from the current branch, a worktree path, or the session's own history.
- Record each key's resolution in the final report.

## 2. Inventory every artefact before removing any

Print the inventory first: nothing is removed before the inventory report is printed.
Each line states the artefact, its path or URL, and its disposition, which is `remove`, `keep`, `skip`, or `refuse`.
A cited pull request is `keep`: it is the evidence the removal guard needs, not something to delete.
Find artefacts by story key: a session's scratch directory is per-session and randomly named, so nothing can be located by the directory a session happens to be in.

**Match the key at a token boundary.**
A name carries the key only when the key stands as its own token: the key starts the name or follows a `-` or `/` in it, and the key ends the name or is followed by a `-` in it.
`feature/<key>`, `<key>-follow-up`, and `fix-x-<key>` carry it; `<key>0`, `x<key>`, and `<key>x` do not.
A name that fails the boundary test is a different story's artefact: it is never inventoried as removable and never acted on, whatever a glob or a search returns.

Sources, all of them:

- **Worktrees.** Every entry `git worktree list` reports whose path or branch carries the key, which includes worktrees any worktree helper created.
- **Local branches.** Every branch whose name carries the key under a prefix in `profile.git.branch_prefixes`.
- **Remote branches.** Every head `git ls-remote --heads origin '*<key>*'` reports whose name carries the key at the boundary.
- **Pull requests.** Every PR `gh pr list --state all --search '<key>' --limit 200` returns, each cited with its full URL.
- **Disposable QA output.** QA runner scratch output and uncommitted evidence copies only, in the scratch location the overlay's QA lane names, including an uncommitted copy inside `profile.qa.evidence_dir`.
  Committed evidence, meaning the content the branch tip holds at `profile.qa.evidence_dir`, is out of scope here; a working-tree edit there is uncommitted and is inventoried.
- **Session files.** Session checklist and scratch files naming the key under `profile.workspace.scratch_dir`.
  When that key is unset, the sessions of this profile used standalone temporary directories, so the report names this source as unsearchable instead of reporting it as empty.

Never inventoried as removable:

- Evidence committed under `profile.qa.evidence_dir`: that directory is the durable record, so it is cited and never removed.
- Evidence `qa-verification` already attached to the story.
- The invoking session's own scratch directory.
- The merge-approval rendezvous file an engagement's brief names, because it belongs to the engagement rather than to a story.

Two more rules:

- A per-session scratch directory is idle only when it holds a checklist file whose every item is checked.
  A directory with no checklist file at all is inventoried as `skip`, never as idle, because nothing proves that session has finished.
- Anything the skill cannot attribute to the key is left out, and the report names it as skipped.

## 3. Delete only with merge evidence

Nothing is deleted while it still holds unmerged or unreviewed work: a branch holds it, and a worktree holds its own uncommitted or ignored files.
Before each removal, after `git fetch origin`, establish merge evidence from the story's pull requests:

- A merged PR whose head commit is the tip: `gh pr view <n> --json state,headRefOid` reports `MERGED`, and its `headRefOid` equals the tip from `git rev-parse <branch>` for a local branch, or from `git ls-remote --heads origin <branch>` for a remote one.
- Containment, only when `profile.git.merge_method` is neither `squash` nor `rebase`: `git merge-base --is-ancestor <branch-tip> origin/<profile.git.integration_branch>`, read after the same fetch.
  Under a squash or a rebase merge the integration branch holds a different commit, so containment proves nothing and is never used.

Remove in this order, so a branch is never refused because a worktree still holds it:

- **Worktree.** Removed with `git worktree remove` only when `git status --porcelain --ignored` is empty inside it, and only when it is not the worktree hosting the current session.
  Ignored files count: a worktree holding an ignored `.env`, build output, or local note is refused, because `git worktree remove` deletes those files with the directory and they never reached the inventory.
  A worktree hosting the current session is refused, because removing it deletes the ground the run stands on.
- **Local branch.** Removed with `git branch -D` once it has merge evidence.
  `-D` rather than `-d`, because a squash or a rebase merge leaves the tip unmerged in git's own eyes.
- **Remote branch.** Deleted with `git push origin --delete <branch>` only when the remote tip has merge evidence and no open PR heads it.
  A branch named by `gh pr list --state open --json headRefName --limit 200` is refused, and a remote branch that never became a PR is refused rather than deleted.
- **Disposable QA output and session files.** Removed only from a directory the inventory proved idle, and only after step 5 has attached the evidence the run swept, so the run never deletes the only copy of something the story is about to receive.

Guards that hold for every removal:

- `--force` is never used, on any command, and a removal that would need it is refused instead.
- An artefact that fails a check is skipped, not forced, and the run continues with the others.
- Each removal is confirmed by reading it back: `git branch --list <branch>`, `git worktree list`, and `git ls-remote --heads origin <branch>` must no longer list the artefact.
  A read-back that still lists it is a refusal, not a removal, and its output is reported as the evidence.
- Every refusal is recorded in the report as a dated line naming the artefact, the failed check, and why, and step 6 posts it on the named story.

## 4. Hosted evidence (a self-contained, capability-detected section)

This section is separated on purpose: a consumer variant can drop it, or layer it through an overlay, without touching the rest of the skill.
It names no host and no runtime: both come from the hosted-evidence row of [references/runtimes.md](references/runtimes.md).

- Read that row for the runtime this session runs on.
  The row says whether the session can reach the evidence it hosted, and the mechanism to list it, download it, and delete it.
- When the row gives the runtime no such capability, or the map has no row for it, print `skipped: this runtime has no hosted-evidence capability`, touch no hosted content, and name the skip and its reason in the final report.
  A capability is never guessed from a runtime the map does list: for this capability a missing row means the skip, never a nearby mechanism.
- When the row does give the capability, sweep only through the mapped mechanism: list the evidence this session hosted for the story, download it into the session's scratch directory, attach it to the named story as step 5 says, and delete the hosted copy only through the mapped per-artefact delete action.
  With no mapped per-artefact delete action the copy stays where it is, and the report names it as left in place.
- Detection never guesses.
  A capability the row gives but the session cannot reach fails the run loudly: print `error: hosted-evidence capability unreachable: <failure>` naming the failure, touch no hosted content, print the report and post the story comments step 6 requires so the work already done is not silent, and exit non-zero.
  That is never a silent skip and never a pass.
- There is no user-facing runtime switch: the map decides, never a flag, an argument, or a phrase in this text.

## 5. Land the evidence on the story

Evidence the run swept into the tracker goes through the same tracker-attachment path `qa-verification` uses, and it is attached to the story it is evidence for.

- `linear issue attach <story-key> <file>` for a sidebar attachment on the story.
- `linear issue comment add <story-key> --attach <file>` where the image renders inline in the comment, with the body naming what the attachment shows.
- Name each attachment in a comment on the story, saying what it shows, because a plain CLI attachment is a sidebar link and images do not render inline.
- Cite, never re-upload and never delete: evidence `qa-verification` already attached, and evidence committed under `profile.qa.evidence_dir`.
  The in-repo copy is the durable record, and a second upload is noise on the story.
  Discover what is already attached before uploading: `linear issue view <story-key> --json` lists the story's attachments.
- No hosted-page or third-party link goes to the tracker: a hosted page can be private to its owner or deleted, which leaves a dead link on the story.

## 6. Report and confirm

The run ends with one report, structured per story, as the run's final message:

```
cleanup report

<story-key>: resolved | unresolved

removed:
- <artefact>: <path or URL>

archived to the tracker:
- <attachment name>: <what it shows>

skipped:
- <artefact>: <reason>

refused:
- <artefact>: <failed check>, <why>
```

- Every story named at invocation gets its own section, including an unresolved key, which carries only its resolution line.
- The report carries four parts per story: what was removed, what was archived to the tracker, with the attachment names, what was skipped and why, including the hosted-evidence skip, and what it refused to touch, with the failed check.
- The inventory report already printed before the first removal: nothing is removed before the inventory report is printed.
- When anything was archived or refused, post the same summary as a comment on that story, carrying the dated refusal lines step 3 recorded.
  One comment per story per run: the refusal detail lives inside this summary, never in a second comment.

## Boundaries

- It acts in one repository: the one the run starts in, or the one this skill's overlay names.
  An artefact in another repository is that repository's own run to clean, and is named as skipped rather than touched.
- It removes only artefacts it can attribute to a named key at a token boundary.
  Everything else is left out and named as skipped.
- It never removes work that has not landed, and it never forces a removal.
- It never edits, reviews, or verifies a story, and it never moves a story's status.
- It reads no credential and writes none: every tracker and hosting call uses the credential its own CLI already holds.

## Completion summary

Report per story: the state of the key, what was removed, what was archived to the tracker with its attachment names, what was skipped and why, and what it refused to touch.
