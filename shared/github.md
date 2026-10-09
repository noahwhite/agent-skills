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

- The merge bar: CI green, the review of record complete and clean at the current head (`references/code-review.md`), every finding resolved, and `mergeable_state` clean (or unstable only while every required check is green).
- Post the review-of-record comment on the PR as its own step and confirm it landed before any merge attempt.
- Who merges is `profile.review.merge_owner`.
  `agent`: merge once the bar is met, without re-asking.
  `human`: report that the gate is clean on head, with the PR URL, and wait.
- Feature PRs merge with `profile.git.merge_method`.
  Promotion PRs merge with the method the release branch's protection requires (the consumer overlay supplies it).
- When the base requires branches to be up to date, merge whichever PR is green immediately; never hold a green PR behind a sibling.
  After any merge, update the remaining PRs and re-arm their watches.
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

For any promotion:

- Review the promotion PR's whole cumulative diff (`references/code-review.md`).
- Inspect promotions with a fresh three-dot diff: `git fetch --prune origin` then `git diff --stat origin/<release>...origin/<integration>`.
  The two-dot diff shows release-only files as deletions.
- ⛔ Never merge the release branch into the integration branch (no back-merges), and never update-branch a promotion PR, which does the same.
  Resolve promotion conflicts on a separate branch.
- Fixes for a promotion PR go on a new feature branch to the integration branch and flow into the promotion.

## Attribution

`profile.git.ai_attribution` decides whether commits, PR bodies, and tracker comments may carry AI attribution.

- `forbid`: no `Co-Authored-By` trailer for an AI, no "generated with" footer, no "made with AI" line, and no model name in tracker stamps, in any repo.
  Check before every commit and PR create or edit; a runtime default, bot, or tool may add a footer, so remove attribution wherever it sits in the text.
- `allow`: follow the runtime's attribution convention.

Tracker stamps name the agent session, never the model (`references/linear.md`, Filing issues).
