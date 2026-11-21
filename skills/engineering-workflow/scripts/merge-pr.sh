#!/usr/bin/env bash
# One invocation for the step-10 merge: read the PR's reviews, read its required checks,
# verify the review of record against the live head, and merge with that head as the
# expected-head condition, or refuse and report the merge blocked.
#
# Run it by its installed path with the current directory inside the repository under review:
#   bash <skill dir>/scripts/merge-pr.sh <PR number> --repo <consumer repo>
#     [--approvals <file> --request-id <id>]
# The target repository is the current directory's, or --repo DIR; never the script's own location.
# The skills repository itself is refused unless --repo names it explicitly.
# --approvals names the merge-approval handshake's approvals file, and --request-id the request the
# manager approved; the merge runs only once a matching APPROVE for the live head is recorded.
#
# It uses the ambient gh auth and never puts a token in argv or in its output.
# Output: the PR number and URL, the live and reviewed head SHAs, the review URL, the check states,
# the marker reviews it excluded, and the merge or refusal result.
#
# Prerequisites, each checked before any GitHub call: bash, git, gh, jq, and python3 with PyYAML.
# Repository selection comes from --repo (or the current directory) alone: the helper clears
# inherited GIT_* and GH_REPO overrides before it resolves the repository.
# A relative --approvals path is resolved against the directory the helper was invoked from.
set -euo pipefail

PROG="merge-pr.sh"
NUMBER=""
REPO=""
APPROVALS=""
REQUEST_ID=""

usage() {
  echo "usage: $PROG <PR number> [--repo DIR] [--approvals FILE --request-id ID]" >&2
  exit 2
}

die() {
  local status="$1"
  shift
  echo "$PROG: $*" >&2
  exit "$status"
}

# A merge refusal: the reason on stderr, and the refusal result on stdout.
refuse() {
  local status="$1"
  shift
  printf 'Result: merge blocked: %s\n' "$*"
  die "$status" "$*"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --repo)
      [ $# -ge 2 ] || usage
      REPO="$2"
      shift 2
      ;;
    --approvals)
      [ $# -ge 2 ] || usage
      APPROVALS="$2"
      shift 2
      ;;
    --request-id)
      [ $# -ge 2 ] || usage
      REQUEST_ID="$2"
      shift 2
      ;;
    -h | --help) usage ;;
    -*) echo "ERROR: unknown option $1" >&2; usage ;;
    *)
      [ -z "$NUMBER" ] || usage
      NUMBER="$1"
      shift
      ;;
  esac
done

[ -n "$NUMBER" ] || usage
[[ "$NUMBER" =~ ^[0-9]+$ ]] || die 2 "the PR number must be numeric, got '$NUMBER'"
if [ -n "$APPROVALS" ] && [ -z "$REQUEST_ID" ]; then
  die 2 "--approvals needs the --request-id the manager approved"
fi
if [ -n "$REQUEST_ID" ] && [ -z "$APPROVALS" ]; then
  die 2 "--request-id needs the --approvals file it belongs to"
fi

# Resolve a relative --approvals path where the caller wrote it, before the cd into the repository
# root below turns it into a different (same-named) file.
INVOCATION_DIR="$PWD"
case "$APPROVALS" in
  "" | /*) ;;
  *) APPROVALS="$INVOCATION_DIR/$APPROVALS" ;;
esac

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI (gh) is required." >&2
  exit 10
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required (the helper parses gh's JSON with it)." >&2
  exit 10
fi

# The repository comes from --repo or the current directory, never from an inherited override: a
# caller's GIT_DIR, GIT_WORK_TREE, GIT_COMMON_DIR, GIT_INDEX_FILE, GIT_CEILING_DIRECTORIES or
# GH_REPO must not move the root, the profile lookup or the repository gh targets.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR GIT_CEILING_DIRECTORIES GH_REPO

if [ -n "$REPO" ]; then
  ROOT="$(git -C "$REPO" rev-parse --show-toplevel)" || die 11 "--repo '$REPO' is not inside a Git repository"
else
  ROOT="$(git rev-parse --show-toplevel)" || die 11 "Not inside a Git repository (cd into the repository under review, or pass --repo)"
  if [ -f "$ROOT/skills.json" ] && [ -f "$ROOT/shared/runtimes.md" ]; then
    die 2 "the current directory is the skills repository ($ROOT); cd into the consumer repository, or pass --repo to target the skills repository itself"
  fi
fi
cd "$ROOT"

# The consumer profile, at the three locations references/profile.md names, first that exists.
HOME_DIR="${HOME:-}"
PROFILE=""
if [ -n "${AGENT_SKILLS_PROFILE:-}" ]; then
  [ -f "$AGENT_SKILLS_PROFILE" ] || die 13 "no consumer profile at AGENT_SKILLS_PROFILE ($AGENT_SKILLS_PROFILE); unset it to fall back to $ROOT/.agent-skills/profile.yaml and ~/.config/agent-skills/profile.yaml"
  PROFILE="$AGENT_SKILLS_PROFILE"
elif [ -f "$ROOT/.agent-skills/profile.yaml" ]; then
  PROFILE="$ROOT/.agent-skills/profile.yaml"
elif [ -n "$HOME_DIR" ] && [ -f "$HOME_DIR/.config/agent-skills/profile.yaml" ]; then
  PROFILE="$HOME_DIR/.config/agent-skills/profile.yaml"
else
  die 13 "no consumer profile: searched AGENT_SKILLS_PROFILE, $ROOT/.agent-skills/profile.yaml and ~/.config/agent-skills/profile.yaml"
fi

# Print the three values this helper needs, or exit 13 naming the key that is missing or invalid.
read_profile() {
  python3 - "$PROFILE" <<'PY'
import sys

path = sys.argv[1]
try:
    import yaml
except ImportError:
    print("merge-pr.sh: PyYAML is required to read the consumer profile (install PyYAML)", file=sys.stderr)
    sys.exit(13)

try:
    with open(path, encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
except OSError as exc:
    print(f"merge-pr.sh: cannot read the consumer profile {path}: {exc}", file=sys.stderr)
    sys.exit(13)
except yaml.YAMLError as exc:
    print(f"merge-pr.sh: the consumer profile {path} is not valid YAML: {exc}", file=sys.stderr)
    sys.exit(13)

if not isinstance(document, dict):
    print(f"merge-pr.sh: the consumer profile {path} is not a mapping", file=sys.stderr)
    sys.exit(13)

review = document.get("review")
merge_owner = review.get("merge_owner") if isinstance(review, dict) else None
if merge_owner not in ("agent", "human"):
    print(f"merge-pr.sh: review.merge_owner is missing or not 'agent' or 'human' in {path}", file=sys.stderr)
    sys.exit(13)

git = document.get("git")
merge_method = git.get("merge_method") if isinstance(git, dict) else None
if merge_method not in ("squash", "merge", "rebase"):
    print(f"merge-pr.sh: git.merge_method is missing or not 'squash', 'merge' or 'rebase' in {path}", file=sys.stderr)
    sys.exit(13)

record_author = review.get("record_author")
if record_author is not None and not isinstance(record_author, str):
    print(f"merge-pr.sh: review.record_author must be a string in {path}", file=sys.stderr)
    sys.exit(13)
if record_author:
    import re

    # The schema's login pattern: letters, digits and hyphens, with an optional literal [bot]
    # suffix. A value outside it (a newline included) could inject another profile setting into the
    # line-based hand-off below, so it fails closed here, before any GitHub call.
    login = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\[bot\])?")
    if len(record_author) > 45 or not login.fullmatch(record_author):
        print(
            f"merge-pr.sh: review.record_author is not a GitHub login (got {record_author!r}) in {path}",
            file=sys.stderr,
        )
        sys.exit(13)

print(f"merge_owner={merge_owner}")
print(f"merge_method={merge_method}")
print(f"record_author={record_author or ''}")
PY
}

PROFILE_LINES="$(read_profile)"
MERGE_OWNER=""
MERGE_METHOD=""
RECORD_AUTHOR=""
while IFS='=' read -r key value; do
  case "$key" in
    merge_owner) MERGE_OWNER="$value" ;;
    merge_method) MERGE_METHOD="$value" ;;
    record_author) RECORD_AUTHOR="$value" ;;
  esac
done <<<"$PROFILE_LINES"

# The live PR: number, URL, state, draft flag, mergeability, merge state and head SHA.
PR_JSON="$(gh pr view "$NUMBER" --json number,url,state,isDraft,mergeable,mergeStateStatus,headRefOid)" \
  || refuse 12 "Could not read PR #$NUMBER with gh pr view"
json_field() { printf '%s' "$1" | jq -r "$2"; }
PR_URL="$(json_field "$PR_JSON" .url)"
HEAD="$(json_field "$PR_JSON" .headRefOid)"
MERGEABLE="$(json_field "$PR_JSON" .mergeable)"
MERGE_STATE="$(json_field "$PR_JSON" .mergeStateStatus)"
PR_STATE="$(json_field "$PR_JSON" .state)"
IS_DRAFT="$(json_field "$PR_JSON" .isDraft)"
[ "$(json_field "$PR_JSON" .number)" = "$NUMBER" ] || refuse 12 "gh pr view returned a different PR number than #$NUMBER"
if [[ ! "$PR_URL" =~ ^https?://([^/]+)/([^/]+/[^/]+)/pull/([0-9]+)/?$ ]]; then
  refuse 12 "Could not derive owner/repo and number from the PR URL ($PR_URL)"
fi
SLUG="${BASH_REMATCH[2]}"
[ "${BASH_REMATCH[3]}" = "$NUMBER" ] || refuse 12 "the PR URL ($PR_URL) is not PR #$NUMBER"
[[ "$HEAD" =~ ^[0-9a-f]{40}$ ]] || refuse 12 "the PR head SHA read from GitHub is not a full commit SHA: '$HEAD'"

# The expected author of the review of record: review.record_author when set, else the login of
# the authenticated account.
AUTHOR="$RECORD_AUTHOR"
if [ -z "$AUTHOR" ]; then
  AUTHOR="$(gh api user --jq .login)" \
    || refuse 15 "could not resolve the expected author: gh api user --jq .login failed"
fi
[ -n "$AUTHOR" ] \
  || refuse 15 "no expected author: review.record_author is unset and gh api user --jq .login returned nothing"

# The PR reviews, through the paginated reviews endpoint.
REVIEWS_JSON="$(
  gh api --paginate "repos/$SLUG/pulls/$NUMBER/reviews" --jq \
    '.[] | {author: .user.login, state: .state, commit_id: .commit_id, submitted_at: .submitted_at, html_url: .html_url, body: .body}'
)" || refuse 15 "Could not read the reviews of PR #$NUMBER with gh api --paginate"

# Among the COMMENTED reviews whose body begins with 'Review of record', the expected author's,
# with the greatest submitted_at.
SELECTED=""
if [ -n "$REVIEWS_JSON" ]; then
  SELECTED="$(
    printf '%s\n' "$REVIEWS_JSON" | jq -s --arg author "$AUTHOR" '
      [ .[]
        | select(.state == "COMMENTED")
        | select((.body // "") | startswith("Review of record"))
        | select(((.author // "") | ascii_downcase) == ($author | ascii_downcase)) ]
      | sort_by(.submitted_at // "")
      | if length == 0 then empty else .[-1] end
    '
  )" || refuse 15 "Could not select the review of record from the reviews of PR #$NUMBER"
fi
[ -n "$SELECTED" ] \
  || refuse 15 "no review of record on PR #$NUMBER: no COMMENTED review whose body begins with 'Review of record' was submitted by $AUTHOR at the live head $HEAD"

REVIEWED_COMMIT="$(json_field "$SELECTED" .commit_id)"
REVIEW_URL="$(json_field "$SELECTED" .html_url)"
REVIEWED_FIRSTLINE_SHA="$(
  printf '%s' "$SELECTED" \
    | jq -r '.body | split("\n")[0] | sub("^[[:space:]]+"; "") | sub("[[:space:]]+$"; "")' \
    | awk '{print $NF}'
)"

printf 'PR: %s %s\n' "$NUMBER" "$PR_URL"
printf 'Live head: %s\n' "$HEAD"
printf 'Reviewed head: %s\n' "$REVIEWED_COMMIT"
printf 'Review of record: %s\n' "$REVIEW_URL"

# references/code-review.md's merge guard step 2: list every marker review it excluded, with its
# login, URL and commit, and never a review body.
EXCLUDED_MARKERS="$(
  printf '%s\n' "$REVIEWS_JSON" | jq -s -r --arg sel "$REVIEW_URL" '
    [ .[]
      | select((.body // "") | startswith("Review of record"))
      | select((.html_url // "") != $sel) ]
    | .[] | "Excluded marker review: \(.author // "-") \(.html_url // "-") \(.commit_id // "-")"
  '
)" || refuse 15 "Could not list the excluded marker reviews of PR #$NUMBER"
if [ -n "$EXCLUDED_MARKERS" ]; then
  printf '%s\n' "$EXCLUDED_MARKERS"
fi

if [ "$REVIEWED_COMMIT" != "$HEAD" ]; then
  refuse 15 "the review of record ($REVIEW_URL) covers commit $REVIEWED_COMMIT, but the live head of PR #$NUMBER is $HEAD"
fi
if [ "$REVIEWED_FIRSTLINE_SHA" != "$HEAD" ]; then
  refuse 15 "the review of record ($REVIEW_URL) names $REVIEWED_FIRSTLINE_SHA on its first line, but the live head of PR #$NUMBER is $HEAD"
fi

# A merge needs an open PR, no draft, a mergeable branch and no blocking merge state.
if [ "$PR_STATE" != "OPEN" ]; then
  refuse 16 "PR #$NUMBER is in state $PR_STATE, not OPEN"
fi
if [ "$IS_DRAFT" = "true" ]; then
  refuse 16 "PR #$NUMBER is a draft (merge state $MERGE_STATE)"
fi
if [ "$MERGEABLE" != "MERGEABLE" ]; then
  refuse 16 "PR #$NUMBER is not mergeable (mergeable=$MERGEABLE, merge state $MERGE_STATE)"
fi
case "$MERGE_STATE" in
  CLEAN | UNSTABLE) ;;
  *) refuse 16 "PR #$NUMBER is in merge state $MERGE_STATE" ;;
esac

CHECKS_JSON=""
CHECKS_OUT=""
CHECKS_ERR=""
CHECKS_STATUS=0
CHECKS_ERR_FILE="$(mktemp)" || refuse 14 "could not create a file for the required-checks stderr of PR #$NUMBER"
CHECKS_OUT="$(gh pr checks "$NUMBER" --required --json name,state,bucket 2>"$CHECKS_ERR_FILE")" || CHECKS_STATUS=$?
CHECKS_ERR="$(cat -- "$CHECKS_ERR_FILE")"
rm -f -- "$CHECKS_ERR_FILE"
case "$CHECKS_STATUS" in
  0 | 1 | 8) ;;
  *) refuse 14 "Could not read the required checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $CHECKS_ERR$CHECKS_OUT" ;;
esac
case "$CHECKS_OUT" in
  \[*) CHECKS_JSON="$CHECKS_OUT" ;;
  '')
    # gh prints exactly this diagnostic on stderr and exits 1 when the branch configures no
    # required checks; only that shape means "none", and a warning on stderr never does.
    if [ "$CHECKS_STATUS" = 1 ] && printf '%s' "$CHECKS_ERR" | grep -q "no required checks reported on the '"; then
      CHECKS_JSON='[]'
    else
      refuse 14 "Could not read the required checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $CHECKS_ERR$CHECKS_OUT"
    fi
    ;;
  *)
    refuse 14 "Could not read the required checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $CHECKS_ERR$CHECKS_OUT"
    ;;
esac
CHECKS_COUNT="$(printf '%s' "$CHECKS_JSON" | jq -r 'if type == "array" then length else "invalid" end')" \
  || refuse 14 "the required checks of PR #$NUMBER were not readable JSON"
[ "$CHECKS_COUNT" != "invalid" ] \
  || refuse 14 "the required checks of PR #$NUMBER were not a JSON array"
if [ "$CHECKS_COUNT" = "0" ]; then
  printf 'Check: none\n'
else
  printf '%s' "$CHECKS_JSON" | jq -r '.[] | "Check: \(.name)=\(.state)"'
fi
NON_GREEN="$(
  printf '%s' "$CHECKS_JSON" \
    | jq -r '[ .[] | select(.state != "SUCCESS") | "\(.name)=\(.state)" ] | join(", ")'
)" || refuse 14 "the required checks of PR #$NUMBER were not readable JSON"
if [ -n "$NON_GREEN" ]; then
  refuse 14 "the required checks on head $HEAD are not green: $NON_GREEN"
fi

# The manager-approval handshake: once the brief assigns merge approval to a manager, the merge
# runs only after a matching APPROVE for the live head is recorded.
if [ -n "$APPROVALS" ]; then
  [ -f "$APPROVALS" ] || refuse 18 "the approvals file $APPROVALS does not exist"
  # references/merge-approval.md: a record is one complete newline-terminated line; a reader that
  # sees a trailing partial line ignores it, the first decision for the (request id, head) pair in
  # file order wins, and a conflicting later decision is reported.
  trim_field() {
    local value="$1"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    printf '%s' "$value"
  }
  DECISION=""
  CONFLICT=""
  while IFS= read -r LINE; do
    IFS='|' read -r -a FIELD <<<"$LINE"
    [ "${#FIELD[@]}" -ge 3 ] || continue
    VERDICT="$(trim_field "${FIELD[0]}")"
    RECORD_ID="$(trim_field "${FIELD[1]}")"
    RECORD_HEAD="$(trim_field "${FIELD[2]}")"
    [ "$RECORD_ID" = "$REQUEST_ID" ] || continue
    [ "$RECORD_HEAD" = "$HEAD" ] || continue
    case "$VERDICT" in
      APPROVE)
        [ "${#FIELD[@]}" -eq 5 ] || continue
        [ -n "$(trim_field "${FIELD[3]}")" ] || continue
        [ -n "$(trim_field "${FIELD[4]}")" ] || continue
        CURRENT="APPROVE"
        ;;
      BOUNCE)
        [ "${#FIELD[@]}" -eq 6 ] || continue
        [ -n "$(trim_field "${FIELD[3]}")" ] || continue
        [ -n "$(trim_field "${FIELD[4]}")" ] || continue
        [ -n "$(trim_field "${FIELD[5]}")" ] || continue
        CURRENT="BOUNCE $(trim_field "${FIELD[4]}")"
        ;;
      *) continue ;;
    esac
    if [ -z "$DECISION" ]; then
      DECISION="$CURRENT"
    elif [ "$CURRENT" != "$DECISION" ]; then
      CONFLICT="first ${DECISION%% *}, later ${CURRENT%% *}"
    fi
  done <"$APPROVALS"
  [ -z "$CONFLICT" ] \
    || refuse 18 "conflicting decisions for $REQUEST_ID at head $HEAD in $APPROVALS: $CONFLICT"
  case "$DECISION" in
    APPROVE) ;;
    BOUNCE*) refuse 18 "the manager bounced $REQUEST_ID at $HEAD: ${DECISION#BOUNCE }" ;;
    *) refuse 18 "no APPROVE recorded for $REQUEST_ID at head $HEAD in $APPROVALS" ;;
  esac
fi

# The human merge owner performs the merge itself.
if [ "$MERGE_OWNER" = "human" ]; then
  printf 'Result: merge-ready; profile.review.merge_owner is human, so no merge command was run\n'
  exit 0
fi

# The merge must carry the reviewed head as an expected-head condition; a gh that cannot carry one
# refuses here, and a rejected head change below is never retried without it.
MERGE_HELP="$(gh pr merge --help)" || refuse 17 "could not read gh pr merge --help"
if ! printf '%s' "$MERGE_HELP" | grep -q -- '--match-head-commit'; then
  refuse 17 "this gh cannot carry an expected-head condition (gh pr merge has no --match-head-commit)"
fi

case "$MERGE_METHOD" in
  squash) METHOD_FLAG="--squash" ;;
  merge) METHOD_FLAG="--merge" ;;
  rebase) METHOD_FLAG="--rebase" ;;
esac

MERGE_OUT=""
if ! MERGE_OUT="$(gh pr merge "$NUMBER" --match-head-commit "$HEAD" "$METHOD_FLAG")"; then
  refuse 17 "gh pr merge $NUMBER --match-head-commit $HEAD $METHOD_FLAG failed: $MERGE_OUT"
fi

# Success only once GitHub reports the PR merged; a queued merge is not a merge.
CONFIRM_JSON="$(gh pr view "$NUMBER" --json state,mergedAt,mergeCommit)" \
  || refuse 17 "merge not confirmed: could not re-read PR #$NUMBER after the merge command"
CONFIRM_STATE="$(json_field "$CONFIRM_JSON" .state)"
[ "$CONFIRM_STATE" = "MERGED" ] \
  || refuse 17 "merge not confirmed: the merge was submitted, but PR #$NUMBER is in state $CONFIRM_STATE, not MERGED yet (a queued merge is not a success; re-read the PR before any retry)"
MERGE_COMMIT="$(printf '%s' "$CONFIRM_JSON" | jq -r '.mergeCommit.oid // empty')"
[ -n "$MERGE_COMMIT" ] || refuse 17 "merge not confirmed: PR #$NUMBER reports no merge commit"

printf 'Result: merged %s\n' "$MERGE_COMMIT"

