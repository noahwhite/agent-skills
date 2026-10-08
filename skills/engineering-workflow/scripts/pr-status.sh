#!/usr/bin/env bash
# Prints the current branch's PR state, checks and comments.
#
# Run it by its installed path with the current directory inside the repository under review:
#   cd <consumer repo> && <skill dir>/scripts/pr-status.sh [--repo DIR]
# The target repository is the current directory's, or --repo DIR; never the script's own location.
# The skills repository itself is refused unless --repo names it explicitly.
set -euo pipefail

REPO=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) [ $# -ge 2 ] || { echo "ERROR: --repo needs a value" >&2; exit 2; }; REPO="$2"; shift 2 ;;
    *) echo "ERROR: unknown option $1 (usage: pr-status.sh [--repo DIR])" >&2; exit 2 ;;
  esac
done

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI (gh) is required." >&2
  exit 10
fi

if [ -n "$REPO" ]; then
  ROOT="$(git -C "$REPO" rev-parse --show-toplevel 2>/dev/null)" || {
    echo "ERROR: --repo '$REPO' is not inside a Git repository." >&2
    exit 11
  }
else
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "ERROR: Not inside a Git repository (cd into the repository under review, or pass --repo)." >&2
    exit 11
  }
  if [ -f "$ROOT/skills.json" ] && [ -f "$ROOT/shared/runtimes.md" ]; then
    echo "ERROR: the current directory is the skills repository ($ROOT); cd into the consumer repository, or pass --repo to target the skills repository itself." >&2
    exit 2
  fi
fi
cd "$ROOT"

PR="$(gh pr view --json number,url,state,baseRefName,headRefName,isDraft,mergeable,statusCheckRollup 2>/dev/null)" || {
  echo "ERROR: Could not determine the current PR." >&2
  exit 12
}

printf '%s\n' "$PR"

echo
echo "=== PR comments (review of record is posted as an issue comment) ==="
# A PR with no comments is expected; any other gh failure propagates.
gh pr view --comments --json comments --jq '
  .comments[]
  | {author: .author.login, body: .body, createdAt: .createdAt, url: .url}
'
