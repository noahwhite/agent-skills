# GitHub and git discipline

Read this before any git, branch, worktree, PR, merge, or commit operation.
Branch names, merge method, promotion model, signing, and attribution come from the profile (see `references/profile.md`).

## Tooling

- `gh` is the primary tool for PRs, issues, checks, reviews, workflow dispatch, and the API.
  Fall back to a GitHub MCP server only when `gh` fails (auth error, missing scope, unsupported operation).
- If HTTPS git auth is not wired in the environment, run `gh auth setup-git` before the first HTTPS fetch, push, or clone.
- Use only the credential meant for GitHub; a container-registry or other service token is never a GitHub API credential.
- Prefer `git -C <path> ...` over `cd <path> && git ...`; compound commands can trigger permission prompts.

## Branching and worktrees

- Cut feature branches from `origin/<profile.git.integration_branch>` with the explicit base ref; never a bare `git checkout -b`.
  Changes to paths that exist only on `profile.git.release_branch` branch from `origin/<release_branch>` and PR to it; shared code still goes through the integration branch.
- ⛔ Never create a branch without `git fetch origin` first.
  Stale local refs pull already-merged work into the new branch.
- Use a dedicated worktree per story; never edit in the main checkout.
  If the worktree tool branches from a different base, recut the branch from the correct base right after entering, and never commit on an auto-created worktree branch.
- Hard-gate the base before the first commit and before push: `git rev-list --count <base>..HEAD` must equal your own commit count.
  A large number means the wrong base; stop and recut from the right one.
- ⛔ Never reuse a worktree after its PR merged.
  Remove it (`git worktree remove`, `git worktree prune`) and create a fresh one.
- Name branches with the prefix for the work type from `profile.git.branch_prefixes` plus the issue key and a short description.
- ⛔ Never rename a branch that heads an open PR; GitHub deletes the old branch and closes the PR.
  Create a new branch from the same commit and open a fresh PR.
- Run `git status` before any checkout and commit work in progress to the branch it belongs to; ask which story owns changes you cannot place.
- ⛔ Never use `git stash` to carry changes across branches; `stash pop` can silently drop hunks when branches diverged.
  Use a temporary commit and cherry-pick, or a diff file in the scratch directory and `git apply`.
- Delete merged local branches with `git branch -D`; squash and rebase merges produce a different SHA, so `-d` refuses.

## Commits and signing

When `profile.git.signed_commits` is true:

- Commit with local git and automatic signing (`commit.gpgsign=true`, or `gpg.format=ssh` with an SSH key).
- ⛔ Never create commits through API file-write tools (an MCP server's push_files or create_or_update_file tool); they produce unsigned commits that fail or silently block the PR.
- Select the signing key that is registered on the account, by its fingerprint or agent comment (`ssh-add -l`), never by trusting whichever public key file is on disk.
  The consumer overlay supplies the registered key's identity.
- Confirm `user.signingkey` resolves to that key before committing, and check the result after push: `gh api repos/<owner>/<repo>/commits/<sha> --jq '.commit.verification'`.
- Workflows that create commits must sign them (for example `sign-commits: true` on a create-pull-request action).

Always:

- Verify committed content after any commit that matters: `git show HEAD:<file>` or `git diff HEAD -- <file>` must show what you intended.
  Staging can capture a stale copy when a concurrent git operation ran; local tests read the working tree and hide it.

## Pull requests

- Open a PR only once the branch is cleanly based on its target.
  If a prerequisite PR must land first, wait, rebase, then open.
- Before starting story work, check for an existing PR or branch: `gh pr list --state open --search "<issue key>"`, `git ls-remote --heads origin '*<issue key>*'`, `git worktree list`.
  Extend an existing one rather than opening a rival.
- For merged evidence, use `gh pr list --state merged --search "<issue key>"`, or the PR links on the issue.
- Feature PRs target `profile.git.integration_branch`; always pass `--base` explicitly.
  Exceptions: promotion PRs and release-only changes (see Merging and promotion).
- Open PRs ready for review, not draft, unless the user asks for a draft.
- A push is not a review: after opening a PR or pushing anything beyond adjudicated fixes, run the review of record at the new head (`references/code-review.md`).
- Assign each new PR to `profile.git.pr_assignee` right after creating it, when that key is set.
- Cite every PR and issue number with its full URL, in every mention.
- Check `mergeable` and `mergeable_state` right after creating a PR (`dirty` = conflict, `unstable` = checks pending); never assume a clean merge.
- Rebase or update open PRs promptly when a merge to their base touches the same files.
- ⛔ Never assume PR state from conversation timing; check `gh pr view` before saying something is or is not merged.

## Merging

- The merge bar: CI green, the review of record complete and clean at the current head (`references/code-review.md`), every finding resolved, `mergeable_state` clean (or unstable only while every required check is green), and the merge guard in `references/code-review.md` passes.
- Except under the explicit per-PR review waiver in The gate, the merge bar requires a completed review of record at the current head.
  Post it as a `--comment` PR review and confirm its state is `COMMENTED` and its `commit_id` matches that head before any merge attempt.
  Under the waiver, use the head SHA recorded when the user gave the instruction and run the merge guard.
- Who merges is `profile.review.merge_owner`.
  `agent`: merge once the bar is met, without re-asking.
  `human`: report that the gate is clean on head, with the PR URL, and wait.
- Carve-out for a delegated manager approval: an engineer whose brief assigns merge approval to a manager follows [merge-approval.md](merge-approval.md) (the `references/merge-approval.md` copy) and does not merge until the matching `APPROVE` is recorded for the current head SHA, even when `profile.review.merge_owner` is `agent`.
  The handshake adds approval; `profile.review.merge_owner` still decides who performs the merge.
  A delegated engineer merges as soon as the matching approval is recorded and the merge bar still holds, and not before.
  Every other case keeps the rule above.
- Feature PRs merge with `profile.git.merge_method`.
  Promotion PRs merge with the method the release branch's protection requires (the consumer overlay supplies it).
- When the base requires branches to be up to date, merge a PR as soon as it is green and its review of record covers its current head; never hold such a PR behind a sibling.
  After any merge, update the remaining PRs except promotion PRs (Promotion) and re-arm their watches; each update that changes the head SHA needs a delta review before that PR merges.
- For trivial PRs keep the posted review write-up terse; reserve long write-ups for risky changes.
- ⛔ Never force-push (`--force`, `--force-with-lease`), even on your own new branch.
  Correct a bad branch by cutting a new one from the right base and re-applying the changes.
- ⛔ Before merging a PR that adds a versioned schema migration, re-check the base for the same version: `git fetch origin <base>` then `git ls-tree -r --name-only origin/<base> -- <migration-dir>`.
  Renumber yours (unapplied only) if the version is taken; two same-version files merge cleanly and fail at deploy.
- Confirm every intended commit is in the PR before merging, and the key changes are on the base after.
  ⛔ Never push to a branch after its PR merged; those commits are lost.
- When CI fails, check whether the PR already merged; if so, fetch the base, delete the old branch, and fix on a fresh branch.
- After any deployment, assume the PR merged and its branch was deleted; start the next change from a fresh base.
- Leave the tracker status alone between merge and deploy (`references/linear.md`, Status lifecycle).

## Promotion

`profile.git.promotion` decides how `profile.git.integration_branch` reaches `profile.git.release_branch`:

- `none`: trunk-based; the integration branch is the release branch and there is no promotion PR.
- `whole-branch`: one promotion PR carries the whole integration branch, opened only after every story awaiting promotion is verified in its pre-production environment.
  Never promote a single story on its own.
- `per-story`: promote each story individually after its feature PR merges, deploy, then close the story; never batch stories.

Under `per-story`, build the promotion branch and its PR like this:

1. Cut the promotion branch from `origin/<profile.git.release_branch>` with that explicit base ref, after `git fetch --prune origin`.
2. Identify the story's merged feature PR, by its issue key, with `gh pr list --state merged --base <profile.git.integration_branch> --limit 1000 --json number,headRefName,mergeCommit,commits`, and stop when the result count reaches that limit, because the list may be truncated.
   Keep the PR whose head branch carries the issue key as a whole token, delimited by a non-alphanumeric character or the end of the name, and stop when that leaves zero or more than one.
   Select, from `origin/<profile.git.integration_branch>`, only the commits that PR added:
   With `profile.git.merge_method` `squash`, select that PR's squash commit.
   With `profile.git.merge_method` `rebase`, select the commits in `origin/<profile.git.release_branch>..origin/<profile.git.integration_branch>` whose `git patch-id --stable` id matches one of the PR's own commits, and stop when the match count differs from the PR's commit count.
   With `profile.git.merge_method` `merge`, select that PR's merge commit.
   Confirm the selection reproduces that PR's own diff, by patch id: for `squash` the squash commit against `gh pr diff <number>`, for `rebase` the selected commits against the PR's commits, and for `merge` `git diff <merge>^1 <merge>` against `gh pr diff <number>`.
   Stop and report when any commit of that PR, from its `commits` list, has a subject that does not carry the story's issue key, because another story's change is riding along inside that PR and a squash or merge commit would carry it unnoticed.
   Stop and report as well when that list holds 100 commits or more, because the list is truncated there and cannot be checked whole.
   Record the PR number and the selected commit SHAs in the promotion PR body.
   Before carrying them, confirm the story's change is still present on `origin/<profile.git.integration_branch>`: the lines the selection adds are present in that branch's version of each file and the lines it removes are absent, checked as whole lines with `git grep --fixed-strings -x` against `origin/<profile.git.integration_branch>`, and stop and report the story as reverted when they are not.
3. Carry the selected commits onto the promotion branch by cherry-picking them one at a time in their original order, with `-m 1` when a selected commit is a merge commit, or by applying non-merge selections with `git cherry-pick -n` in order and making one commit.
4. Run the promotion branch's local checks, push it, then open the promotion PR from it to `profile.git.release_branch` and let its CI run.
   A whole-branch integration-to-release PR is not used under `per-story`.
5. Stop and report instead of carrying another story's commit or merging the integration branch into the promotion when the selection finds no commit, matches more than one feature PR, or cannot apply without an un-promoted story.
   A cherry-pick conflict that needs another story's commits is that stop: report the conflicting commit and the story it needs, and do not pull that story in to clear the conflict.
   An empty application, because a selected commit is already on the release branch, is that stop too: report the story as already promoted.
   A check that fails only because another story's change is absent is that stop as well.

Under `per-story`, a valid review fix lands on a new feature branch to `profile.git.integration_branch` and merges there before its commit is carried.
The stale promotion PR is then closed unmerged, and the fix is carried in this order: cut a fresh story-scoped promotion branch from the release branch under a new branch name, carry the selection recorded in the closed PR body, then select the fix PR's own commits by `profile.git.merge_method` and cherry-pick them onto the branch in their original order, with `-m 1` when one is a merge commit.
The story's updated commits, the original selection plus the fix commits, are what the branch carries.
Record the fix PR number in the promotion PR body when that PR merges, and select from that recorded number instead of running the discovery again, which would match a second feature PR and stop.
Open a fresh promotion PR from that branch to `profile.git.release_branch`, carrying the story's updated commits.
Refresh the story's pre-production evidence against that promotion head before the merge.
Do not back-merge the release branch into the promotion branch, update-branch a promotion PR, or force-push one; rebuild it instead.

For any promotion:

- Review the promotion PR's whole cumulative diff (`references/code-review.md`).
- Inspect a `whole-branch` promotion with a fresh three-dot diff: `git fetch --prune origin` then `git diff --stat origin/<release>...origin/<integration>`.
  The two-dot diff shows release-only files as deletions.
- Inspect a `per-story` promotion with its own story-scoped three-dot diff: `git fetch --prune origin` then `git diff --stat origin/<release>...<promotion-branch>`.
  Never inspect the whole integration branch for a `per-story` promotion.
- ⛔ Never merge the release branch into the integration branch (no back-merges), and never update-branch a promotion PR, which does the same.
  Resolve promotion conflicts on a separate branch.
- Under `whole-branch`, fixes for a promotion PR go on a new feature branch to the integration branch and flow into the promotion.

## Attribution

`profile.git.ai_attribution` decides whether commits, PR bodies, and tracker comments may carry AI attribution.

- `forbid`: no `Co-Authored-By` trailer for an AI, no "generated with" footer, no "made with AI" line, and no model name in tracker stamps, in any repo.
  Check before every commit and PR create or edit; a runtime default, bot, or tool may add a footer, so remove attribution wherever it sits in the text.
- `allow`: follow the runtime's attribution convention.

Tracker stamps name the agent session, never the model (`references/linear.md`, Filing issues).
