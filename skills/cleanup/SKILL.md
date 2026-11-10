---
name: cleanup
description: >-
  Remove every artifact a working session created for a Linear story - worktrees, local and remote branches, disposable QA output and scratch debris - and move the evidence the session hosted onto the story itself, under a guarded inventory that refuses anything still holding unmerged work.
  Use when asked to clean up, tidy up, or clear the artifacts of a story (for example "clean up ABC-123"), or to move a story's hosted evidence onto the tracker.
  Not for implementing or reviewing a story (use engineering-workflow), not for verifying one (use qa-verification), and not the `cleanup <path>` subcommand of the adversarial pre-PR pipeline script.
license: Apache-2.0
compatibility: Requires git, gh, and the linear CLI (schpet/linear-cli).
---

# Cleanup

Remove the artifacts a session created while working a Linear story, and move the evidence it hosted onto that story.
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
- [references/runtimes.md](references/runtimes.md) - steps 2 and 3: the "Persistent memory" row; step 4: the hosted-evidence capability row, and the capability mapping when a runtime is not listed.

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
  A key does not resolve only when that lookup fails: the tracker lookup alone decides, and a key whose team prefix differs from `profile.tracker.team_key` resolves like any other.
- Report an unresolved key as `unresolved` and skip it.
  The other keys still run: one bad key never stops the run, and no artifact is attributed to it.
- Never invent, guess, or shorten a key, and never take one from the current branch, a worktree path, or the session's own history.
- Record each key's resolution in the final report.
- Record each resolved key's tracker state, the state its `linear issue view` lookup reports, for the persistent-memory guard in step 3.

## 2. Inventory every artifact before removing any

Print the inventory first: nothing is removed before the inventory report is printed.
Each line states the artifact, its path or URL, and its disposition, which is `remove`, `keep`, `skip`, or `refuse`.
A cited pull request is `keep`: it is the evidence the removal guard needs, not something to delete.
Find artifacts by story key: a session's scratch directory is per-session and randomly named, so nothing can be located by the directory a session happens to be in.

**Match the key at a token boundary.**
A name carries the key only when the key stands as its own token: the key starts the name or follows a `-` or `/` in it, and the key ends the name or is followed by a `-` or `/` in it.
`feature/<key>`, `<key>-follow-up`, `fix-x-<key>`, and the directory `<key>` in `/tmp/<key>/checkout` all carry it; `<key>0`, `x<key>`, and `<key>x` do not.
Outside persistent-memory notes, which step 2 matches by their own rule below, a name that fails the boundary test is a different story's artifact: it is never inventoried as removable and never acted on, whatever a glob or a search returns.

Sources, all of them:

- **Worktrees.** Every entry `git worktree list` reports whose path or branch carries the key, which includes worktrees any worktree helper created.
  Under each worktree's line, the inventory lists by exact path every entry its status read (step 3) reports.
  Each regenerable ignored entry the run will delete (step 3) has disposition `remove`; the run will delete it only when the worktree passes every step 3 check, so the inventory evaluates those checks before it prints, and step 3 evaluates them again before deleting.
  A regenerable entry in a worktree that fails any of them is `keep`, and each other entry is `refuse`, with its kind.
- **Local branches.** Every branch whose name carries the key under a prefix in `profile.git.branch_prefixes`.
- **Remote branches.** Every head `git ls-remote --heads origin '*<key>*'` reports whose name carries the key at the boundary.
- **Pull requests.** Every PR `gh pr list --state all --search '<key>' --json number,url,state,headRefName --limit 1000` returns, each cited with its full URL.
  That limit fetches every page the CLI holds, so the record is complete for any realistic story; a result set that reaches it is not proven complete, and then the inventory is reported as incomplete and nothing is removed for that story until it is.
- **Disposable QA output.** QA runner scratch output and uncommitted evidence copies only.
  Scan the session scratch base this runtime gives (`profile.workspace.scratch_dir`, or the runtime's own base as the capability map names it), an uncommitted copy inside `profile.qa.evidence_dir`, and the QA runner's scratch directory when this skill's overlay names one.
  A location the overlay names but the run cannot reach is reported as unsearchable, never as empty.
  Committed evidence, meaning the content the branch tip holds at `profile.qa.evidence_dir`, is out of scope here; a working-tree edit there is uncommitted and is inventoried.
- **Session files.** Session checklist and scratch files naming the key under `profile.workspace.scratch_dir`.
  When that key is unset, the sessions of this profile used standalone temporary directories, so the report names this source as unsearchable instead of reporting it as empty.
- **Persistent-memory notes.** The notes in the stores the "Persistent memory" row of [references/runtimes.md](references/runtimes.md) names for the runtime this session runs on, for the main checkout and for each worktree this inventory lists.
  The row says where each store is; this text names no runtime and no store path.
  A store the run cannot read is reported as unsearchable, never as empty.
  A note is `remove` when its file name, with its extension ignored, or the `name` in its frontmatter carries the story key, compared without regard to letter case, with no letter or digit directly before or after the key.
  A note that carries the key only in its body is `skip`, and the report names it.
  When the row for the runtime reads `none`, print `skipped: this runtime has no persistent memory`; when it reads `not observed`, or the map has no row for the runtime, print `unchecked: persistent memory not observed on this runtime`; in both cases no note is listed or touched.

Never inventoried as removable:

- Evidence committed under `profile.qa.evidence_dir`: that directory is the durable record, so it is cited and never removed.
- Evidence `qa-verification` already attached to the story.
- The invoking session's own scratch directory.
- The merge-approval rendezvous file an engagement's brief names, because it belongs to the engagement rather than to a story.

Two more rules:

- A per-session scratch directory is idle only when the run can prove its session has finished: its checklist file exists and every item is checked.
  A directory with no checklist file is never idle: a session using its runtime's todo list writes no file, and a paused session's files look exactly like a finished one's, so nothing on disk proves that session is done.
  That directory is inventoried as `skip`, and the report names it with the files it keeps, so a human can remove them deliberately.
  This is the strict direction on purpose: a wrongly skipped directory leaves reported debris, while a wrongly deleted one destroys a live session's work.
- Anything the skill cannot attribute to the key is left out, and the report names it as skipped.

## 3. Delete only with merge evidence

Nothing is deleted while it still holds unmerged or unreviewed work: a branch holds it, and a worktree holds its own uncommitted or ignored files, apart from the regenerable ignored entries below.
Before each removal other than a persistent-memory note, after `git fetch origin`, establish merge evidence from the story's pull requests:

- A merged PR whose head commit is the tip: `gh pr view <n> --json state,headRefOid` reports `MERGED`, and its `headRefOid` equals the tip from `git rev-parse <branch>` for a local branch, or from `git ls-remote --heads origin <branch>` for a remote one.
- Containment, only when `profile.git.merge_method` is neither `squash` nor `rebase`: `git merge-base --is-ancestor <branch-tip> origin/<profile.git.integration_branch>`, read after the same fetch.
  Under a squash or a rebase merge the integration branch holds a different commit, so containment proves nothing and is never used.

Remove in this order, so a branch is never refused because a worktree still holds it:

- **Worktree.** Removed with `git worktree remove` only when its HEAD is the tip of a branch with merge evidence, only when it is not the worktree hosting the current session, only when git can remove it, and only when `git status --porcelain --ignored -z` inside it is empty or lists only regenerable ignored entries, which the run deletes first as below.
  A worktree with a detached HEAD, or on a branch without merge evidence, is refused, because nothing proves the commit it holds has landed.
  A worktree hosting the current session is refused, because removing it deletes the ground the run stands on.
  A worktree git cannot remove is refused before anything is deleted from it: the main working tree (the first entry `git worktree list --porcelain` reports), a worktree that listing marks `locked`, and a worktree that holds a submodule, unless git can remove it with nothing lost.
  The worktree's submodule paths are the entries `git ls-files --stage -z` lists inside it with mode `160000`; that read must exit 0, and `-z` delivers each path exactly as it is on disk, spaces included.
  A worktree with submodule paths is removable with nothing lost only when its own modules directory (the path `git rev-parse --git-path modules` prints inside the worktree) does not exist and each submodule path is absent or an empty directory, meaning `find ./<path> -mindepth 1 -print` prints nothing and exits 0, so an entry whose name begins with a dot counts.
  The status read never reports files inside a submodule path, and git refuses to remove a worktree that has a modules directory, so a worktree that fails any of these is refused.
  A worktree whose path no longer exists holds nothing to delete: the run skips its status read, removes it with `git worktree remove`, and confirms the removal with the `git worktree list` read-back.
  - **Status read.** Every status read in this step runs `git status --porcelain --ignored -z` inside the worktree and must exit 0; a read that exits non-zero refuses the worktree, whatever it printed.
    The `-z` form lists the same entries as `git status --porcelain --ignored`, separated by NUL and never quoted, so a path with a space, a quote or a non-ASCII character reaches the checks below exactly as it is on disk.
  - **Regenerable ignored entries.** An ignored entry is regenerable when `git status --porcelain --ignored -z` reports it with the ignored code `!!` as a directory (with a trailing `/`) whose final path component, with that trailing `/` removed, is one of `.venv`, `venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`; so `tests/__pycache__/` qualifies.
    An untracked entry (code `??`) is never regenerable, even with a matching name and a trailing `/`.
    A package manager or test runner recreates these directories, so deleting them loses nothing.
    Only when the worktree passes every other check in this step and its status lists no other entry, the run first lists the contents of each such directory at any depth, including entries whose names begin with a dot and without following symlinks (`find ./<path> -print` does; `ls -R` hides dot entries and does not qualify), and refuses the worktree when a listing holds a nested repository: an entry named `.git` at any depth, whether a directory or a file.
    A bare repository, a directory holding `HEAD`, `objects` and `refs` side by side, counts as a nested repository too.
    A listing that exits non-zero refuses the worktree, whatever it printed.
    It also requires a per-name content check before an entry counts as regenerable:
    - `__pycache__` holds only `*.pyc` files: every entry inside it is a regular file whose name ends in `.pyc`.
    - `.venv` and `venv` have `pyvenv.cfg` at their top: a regular file of that name directly inside the directory.
    - `.pytest_cache`, `.mypy_cache` and `.ruff_cache` have `CACHEDIR.TAG` at their top: a regular file of that name directly inside the directory.
    - `node_modules` has no content check and is subject to the nested-repository refusal only.

    A directory that fails its check is not regenerable and the worktree is refused.
    The run checks every regenerable entry before it deletes any, so a nested repository or a failed content check deletes nothing.
    A stray file inside a directory that passes its check is still deleted with it: neither the name nor the marker file can tell a file a tool wrote from one a person left there.
    Then the run records each regenerable entry by exact path in the inventory, and deletes each one with `rm -r -- <path>` on that exact path inside the worktree: no `-f`, no `--force`, no glob.
    The path is passed to `rm` as one argument, exactly as the `-z` read gave it, never through shell expansion.
    `rm` runs with standard input from `/dev/null`, so it never stops to prompt.
    The run stops at the first failed deletion and deletes nothing more.
    It then reads `git status --porcelain --ignored -z` inside the worktree again, and removes the worktree with `git worktree remove` only when that second read is empty, running the removal immediately after the read with no other step between them.
    A failed deletion, a second read that is not empty, a nested repository, or a failed content check refuses the worktree, and the report names the path and the failure.
    A failed `rm -r` can leave part of that entry behind, so the run then lists what remains at its path, and the report names it.
    An ignored file created between the second read and the removal is still deleted with the directory; git offers no checked removal short of `--force`, so this narrow window is accepted rather than closed.
    A worktree locked after its checks passed has its regenerable entries deleted before `git worktree remove` refuses it; the report names it as a refused removal, and since only regenerable entries are lost, this window is accepted too.
  - **Any other entry refuses.** When the status lists any other entry, the worktree is refused and nothing is deleted from it, the regenerable entries included.
    The other entries are: an ignored entry not on the regenerable list (for example `.env`, a local note, or other build output), a symlink or file named like a list entry, a tracked modification (staged, unstaged, deleted, renamed or conflicted), and an untracked entry (a file or a directory).
    `git worktree remove` deletes ignored files with the directory, so an entry the run cannot prove regenerable would be lost although the run never chose to delete it.
    The inventory and the refusal line name every such entry by exact path and kind.
    Under `-z` a rename or copy record carries two paths, the new one and then the original, and both are named.
  - **Report.** The final report lists, under the worktree it came from and by exact path, each entry deleted, including when the worktree removal was then refused, with the failed check, and each failed deletion as a refusal.
    A worktree refused because its status lists any other entry lists no entry as deleted.
    The step 6 template shows where these lines go.
- **Local branch.** Removed with `git branch -D` once it has merge evidence.
  `-D` rather than `-d`, because a squash or a rebase merge leaves the tip unmerged in git's own eyes.
- **Remote branch.** Deleted with `git push origin --delete <branch>` only when the remote tip has merge evidence and no open PR heads it.
  Read the remote tip a second time immediately before the delete and refuse if it moved: a push that lands between the check and the delete is the one case this run cannot prevent, because the repository forbids a force or lease push.
  A branch whose head ref is named at the key boundary by `gh pr list --state open --json headRefName,number --limit 1000` is refused, and a listing that returns exactly its limit is not proven complete, so the run refuses instead of deleting.
  Match head refs from that listing, not a free-text search: a search matches titles and bodies, so a PR whose head branch carries the key but whose text does not would slip past.
  A remote branch that never became a PR is refused rather than deleted.
- **Disposable QA output and session files.** Removed only from a directory the inventory proved idle, and only after step 5 has attached the evidence the run swept, so the run never deletes the only copy of something the story is about to receive.
  An uncommitted evidence copy is removable only once it has a home the story keeps: attached in step 5, or committed. Until then it is skipped, because a copy with no home is the durable record.
- **Persistent-memory note.** A note holds no branch or commit, so merge evidence does not apply: the story's tracker state is the only guard for it, and the merge-evidence guards of every other artifact are unchanged.
  A `remove` note is deleted with a single `rm` of its quoted path, only when the state step 1 recorded for its story equals `profile.tracker.states.done` or `profile.tracker.states.canceled`.
  A note whose story is in any other state is skipped, with the reason that the story is not done or canceled.
  When either of those two profile keys is unset, no note is removed, and the report names each unset key.
  Each note removal is read back by listing its store: a note still present is `refused`, not removed, and a store listing that fails reports the note `refused` with the failure's reason, never `removed`.
  Index lines are not edited: a line that links a removed note stays as it is, and the report says so once when any note was removed.

Guards that hold for every removal:

- `--force` is never used, on any command, and a removal that would need it is refused instead.
- An artifact that fails a check is skipped, not forced, and the run continues with the others.
- Each removal is confirmed by reading it back: `git branch --list <branch>`, `git worktree list`, and `git ls-remote --heads origin <branch>` must no longer list the artifact; for a worktree whose regenerable entries were deleted, the second status read is part of that read-back.
  A read-back that still lists it is a refusal, not a removal, and its output is reported as the evidence.
- Every refusal is recorded in the report as a dated line naming the artifact, the failed check, and why, and step 6 posts it on the named story.

## 4. Hosted evidence (a self-contained, capability-detected section)

This section is separated on purpose: a consumer variant can drop it, or layer it through an overlay, without touching the rest of the skill.
It names no host and no runtime: both come from the hosted-evidence row of [references/runtimes.md](references/runtimes.md).

- Read that row for the runtime this session runs on.
  The row says whether the session can reach the evidence it hosted, and the mechanism to list it, download it, and delete it.
  Reachability is the publishing session's own: a later session reaches none of an earlier session's hosted copies, which is why this step sweeps only what this session hosted.
- When the row gives the runtime no such capability, or the map has no row for it, print `skipped: this runtime has no hosted-evidence capability`, touch no hosted content, and name the skip and its reason in the final report.
  A capability is never guessed from a runtime the map does list: for this capability a missing row means the skip, never a nearby mechanism.
- When the row does give the capability, sweep only through the mapped mechanism: list the evidence this session hosted for the story, download it into the session's scratch directory, attach it to the named story as step 5 says, and delete the hosted copy only through the mapped per-artifact delete action.
  With no mapped per-artifact delete action the copy stays where it is, and the report names it as left in place.
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
- <artifact>: <path or URL>
  - deleted: <regenerable entry path>

archived to the tracker:
- <attachment name>: <what it shows>

skipped:
- <artifact>: <reason>

refused:
- <artifact>: <failed check>, <why>
  - deleted: <regenerable entry path>
  - refused: <regenerable entry path>: <failed deletion>
```

- Every story named at invocation gets its own section, including an unresolved key, which carries only its resolution line.
- The report carries four parts per story: what was removed, what was archived to the tracker, with the attachment names, what was skipped and why, including the hosted-evidence skip, and what it refused to touch, with the failed check.
- The inventory report already printed before the first removal: nothing is removed before the inventory report is printed.
- Each persistent-memory note is reported by its file name under removed, skipped, or refused, with the reason.
  Each persistent-memory store step 2 could not read is named in the report as unsearchable.
  The report carries the `skipped: this runtime has no persistent memory` or `unchecked: persistent memory not observed on this runtime` line when step 2 printed one, and, once, that index lines were not edited when any note was removed.
- When anything was archived or refused, post the same summary as a comment on that story, carrying the dated refusal lines step 3 recorded.
  One comment per story per run: the refusal detail lives inside this summary, never in a second comment.

## Boundaries

- It acts in one repository: the one the run starts in, or the one this skill's overlay names.
  An artifact in another repository is that repository's own run to clean, and is named as skipped rather than touched.
- It removes only artifacts it can attribute to a named key: at a token boundary, or, for a persistent-memory note, by the note match step 2 states.
  Everything else is left out and named as skipped.
- It never removes work that has not landed, and it never forces a removal.
- It never edits, reviews, or verifies a story, and it never moves a story's status.
- It reads no credential and writes none: every tracker and hosting call uses the credential its own CLI already holds.

## Completion summary

Report per story: the state of the key, what was removed, what was archived to the tracker with its attachment names, what was skipped and why, and what it refused to touch.
