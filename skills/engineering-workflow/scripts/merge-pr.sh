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
# Prerequisites, each checked before any GitHub call: bash, git, gh, jq, python3 with PyYAML, and
# the core utilities it calls (mktemp, dirname, cat, rm and date).
# Repository selection comes from --repo (or the current directory) alone: the helper clears every
# inherited GIT_* variable, plus GH_REPO and GH_HOST, before it resolves the repository, so no
# caller environment can move the root, the profile lookup or the repository gh targets.
# A relative --approvals path is resolved against the directory the helper was invoked from.
set -euo pipefail

PROG="merge-pr.sh"
NUMBER=""
REPO=""
APPROVALS=""
REQUEST_ID=""
APPROVALS_SET=0
REQUEST_ID_SET=0

usage() {
  echo "usage: $PROG <PR number> [--repo DIR] [--approvals FILE --request-id ID]"
  exit "${1:-2}"
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
  printf 'Result: merge blocked: %s\n' "$(one_line "$*")"
  die "$status" "$*"
}

# A merge attempt that GitHub may have accepted but not yet confirmed is not a refusal: the caller
# must re-read the PR before any retry, so it gets its own result line.
unconfirmed() {
  local status="$1"
  shift
  printf 'Result: merge submitted but not confirmed: %s\n' "$(one_line "$*")"
  die "$status" "$*"
}

# Every value this helper prints that came from outside (a check name or state, a review URL, a
# command's output) is folded to one line first, so no remote or proxy text can forge a second
# `Result:` line in the transcript. Control characters other than tab, CR and LF cannot start a
# line and are left alone.
one_line() {
  local value="$1"
  value="${value//$'\r'/ }"
  value="${value//$'\n'/ }"
  value="${value//$'\t'/ }"
  printf '%s' "$value"
}

# A command's own output, folded to one line and capped, for a refusal that carries the diagnosis
# without letting that output forge a result line or flood the transcript.
gh_detail() {
  local text
  text="$(one_line "$1")"
  printf '%s' "${text:0:300}"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --repo)
      [ $# -ge 2 ] || usage
      case "$2" in
        "" | --*) echo "ERROR: --repo needs a directory" >&2; usage ;;
      esac
      REPO="$2"
      shift 2
      ;;
    --approvals)
      [ $# -ge 2 ] || usage
      case "$2" in
        "" | --*) echo "ERROR: --approvals needs a file path" >&2; usage ;;
      esac
      APPROVALS="$2"
      APPROVALS_SET=1
      shift 2
      ;;
    --request-id)
      [ $# -ge 2 ] || usage
      case "$2" in
        "" | --*) echo "ERROR: --request-id needs the manager's request ID" >&2; usage ;;
      esac
      REQUEST_ID="$2"
      REQUEST_ID_SET=1
      shift 2
      ;;
    -h | --help) usage 0 ;;
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
# Option presence is tracked separately from its value: an empty manager argument is a usage error,
# never an implicit "no approval needed".
if [ "$APPROVALS_SET" = 1 ] && [ -z "$APPROVALS" ]; then
  die 2 "--approvals needs a file path"
fi
if [ "$REQUEST_ID_SET" = 1 ] && [ -z "$REQUEST_ID" ]; then
  die 2 "--request-id needs the manager's request ID"
fi
if [ "$APPROVALS_SET" != "$REQUEST_ID_SET" ]; then
  die 2 "--approvals and --request-id always travel together"
fi
if [ "$REQUEST_ID_SET" = 1 ]; then
  # references/merge-approval.md: the request ID is REQ-<story-key>-PR<number>-<n> with <n> from 1,
  # so it names the PR it authorizes; an ID naming another PR can never approve this merge.
  [[ "$REQUEST_ID" =~ ^REQ-.+-PR${NUMBER}-[1-9][0-9]*$ ]] \
    || die 2 "--request-id must name PR #$NUMBER as REQ-<story-key>-PR${NUMBER}-<n> with <n> from 1, got '$REQUEST_ID'"
fi

# Resolve a relative --approvals path and a relative AGENT_SKILLS_PROFILE where the caller wrote
# them, before the cd into the repository root below turns them into different paths.
INVOCATION_DIR="$PWD"
case "$APPROVALS" in
  "" | /*) ;;
  *) APPROVALS="$INVOCATION_DIR/$APPROVALS" ;;
esac
if [ -n "${AGENT_SKILLS_PROFILE:-}" ]; then
  case "$AGENT_SKILLS_PROFILE" in
    /*) ;;
    *) AGENT_SKILLS_PROFILE="$INVOCATION_DIR/$AGENT_SKILLS_PROFILE" ;;
  esac
fi

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git is required (the helper resolves the repository root with it)." >&2
  exit 10
fi
if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI (gh) is required." >&2
  exit 10
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required (the helper parses gh's JSON with it)." >&2
  exit 10
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required (the helper reads the consumer profile with it)." >&2
  exit 10
fi

# The repository comes from --repo or the current directory, never from an inherited override: a
# caller's GIT_DIR, GIT_WORK_TREE, GIT_COMMON_DIR, GIT_INDEX_FILE, GIT_CEILING_DIRECTORIES,
# GIT_DISCOVERY_ACROSS_FILESYSTEM, GIT_CONFIG_* or any other GIT_* variable must not move the
# root, the profile lookup or the repository gh targets, so every exported GIT_* name is cleared,
# not a hand-listed few. The same holds for gh's own repository and host overrides.
while IFS= read -r inherited; do
  [ -n "$inherited" ] || continue
  unset "$inherited" 2>/dev/null || true
done < <(compgen -e GIT_)
unset GH_REPO GH_HOST

if [ -n "$REPO" ]; then
  ROOT="$(git -C "$REPO" rev-parse --show-toplevel)" || die 11 "--repo '$REPO' is not inside a Git repository"
else
  ROOT="$(git rev-parse --show-toplevel)" || die 11 "Not inside a Git repository (cd into the repository under review, or pass --repo)"
  if [ -f "$ROOT/skills.json" ] && [ -f "$ROOT/shared/runtimes.md" ]; then
    die 2 "the current directory is the skills repository ($ROOT); cd into the consumer repository, or pass --repo to target the skills repository itself"
  fi
fi
cd "$ROOT"

# The consumer profile, at the three locations references/profile.md names, in documented order:
# the explicit AGENT_SKILLS_PROFILE, then the repository's own, then the home one. An absent
# candidate is skipped; a candidate that exists but cannot be read as a file fails closed rather
# than letting a lower-priority profile decide the merge policy.
#
# An inaccessible location is never read as absent (references/profile.md, Fail closed): `-e` is
# false both for a file that is not there and for a path whose parent cannot be searched, so the
# nearest existing ancestor decides which of the two happened, and a failed lookup refuses naming
# the candidate before any GitHub call.
candidate_state() {
  local candidate="$1" dir
  if [ -e "$candidate" ] || [ -L "$candidate" ]; then
    printf 'present'
    return 0
  fi
  dir="$(dirname -- "$candidate")"
  while [ -n "$dir" ] && [ "$dir" != "/" ] && [ "$dir" != "." ]; do
    if [ -d "$dir" ]; then
      if [ -x "$dir" ]; then
        printf 'absent %s' "$dir"
      else
        printf 'unsearchable %s' "$dir"
      fi
      return 0
    fi
    dir="$(dirname -- "$dir")"
  done
  printf 'absent %s' "$dir"
}

HOME_DIR="${HOME:-}"
PROFILE=""
CANDIDATES=()
[ -z "${AGENT_SKILLS_PROFILE:-}" ] || CANDIDATES+=("$AGENT_SKILLS_PROFILE")
CANDIDATES+=("$ROOT/.agent-skills/profile.yaml")
[ -z "$HOME_DIR" ] || CANDIDATES+=("$HOME_DIR/.config/agent-skills/profile.yaml")
for candidate in "${CANDIDATES[@]}"; do
  CANDIDATE_STATE="$(candidate_state "$candidate")"
  case "$CANDIDATE_STATE" in
    present) ;;
    absent*) continue ;;
    unsearchable*)
      refuse 13 "the consumer profile candidate $candidate could not be checked: ${CANDIDATE_STATE#unsearchable } is not searchable"
      ;;
    *)
      refuse 13 "the consumer profile candidate $candidate could not be checked"
      ;;
  esac
  [ -f "$candidate" ] || refuse 13 "the consumer profile $candidate is not a regular file"
  [ -r "$candidate" ] || refuse 13 "the consumer profile $candidate is not readable"
  PROFILE="$candidate"
  break
done
[ -n "$PROFILE" ] \
  || refuse 13 "no consumer profile: searched $ROOT/.agent-skills/profile.yaml and ~/.config/agent-skills/profile.yaml (AGENT_SKILLS_PROFILE is ${AGENT_SKILLS_PROFILE:-unset})"

# Print the three values this helper needs, or exit 13 naming the key that is missing or invalid.
read_profile() {
  # -I isolates the interpreter from the checkout on every supported Python: it never imports a
  # same-named module (such as a checkout-local yaml.py) from the consumer repository, so the reader
  # runs no consumer code. PyYAML must therefore be importable in the interpreter's own environment
  # (system or virtualenv site-packages), which the prerequisite message names.
  python3 -I - "$PROFILE" <<'PY'
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
    print(f"merge-pr.sh: cannot read the consumer profile {path}: {exc.strerror}", file=sys.stderr)
    sys.exit(13)
except yaml.YAMLError as exc:
    # The parser's own text can quote the source line, so report only the location.
    mark = getattr(exc, "problem_mark", None)
    where = f" at line {mark.line + 1}, column {mark.column + 1}" if mark is not None else ""
    print(f"merge-pr.sh: the consumer profile {path} is not valid YAML{where}", file=sys.stderr)
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
if merge_owner == "agent" and merge_method not in ("squash", "merge", "rebase"):
    print(f"merge-pr.sh: git.merge_method is missing or not 'squash', 'merge' or 'rebase' in {path}", file=sys.stderr)
    sys.exit(13)
if merge_owner == "human" and merge_method not in ("squash", "merge", "rebase"):
    # The human owner merges; the method only matters to the agent path, so an absent one is not a
    # reason to withhold the verified merge-ready report.
    merge_method = ""

record_author = review.get("record_author")
if record_author is not None and not isinstance(record_author, str):
    print(f"merge-pr.sh: review.record_author must be a string in {path}", file=sys.stderr)
    sys.exit(13)
if record_author:
    import re

    # The schema's login pattern: letters, digits and hyphens, with an optional literal [bot]
    # suffix. A value outside it (a newline included) could inject another profile setting into the
    # line-based hand-off below, so it fails closed here, before any GitHub call, and the value is
    # never echoed back into the transcript.
    login = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\[bot\])?")
    if len(record_author) > 45 or not login.fullmatch(record_author):
        print(f"merge-pr.sh: review.record_author is not a GitHub login in {path}", file=sys.stderr)
        sys.exit(13)

print(f"merge_owner={merge_owner}")
print(f"merge_method={merge_method}")
print(f"record_author={record_author or ''}")
PY
}

PROFILE_LINES="$(read_profile)" || {
  printf 'Result: merge blocked: the consumer profile %s was rejected\n' "$PROFILE"
  exit 13
}
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
PR_URL="$(json_field "$PR_JSON" .url)" \
  || refuse 12 "Could not read PR #$NUMBER with gh pr view: the response was not readable JSON"
HEAD="$(json_field "$PR_JSON" .headRefOid)" \
  || refuse 12 "Could not read PR #$NUMBER with gh pr view: the response was not readable JSON"
MERGEABLE="$(json_field "$PR_JSON" .mergeable)" \
  || refuse 12 "Could not read PR #$NUMBER with gh pr view: the response was not readable JSON"
MERGE_STATE="$(json_field "$PR_JSON" .mergeStateStatus)" \
  || refuse 12 "Could not read PR #$NUMBER with gh pr view: the response was not readable JSON"
PR_STATE="$(json_field "$PR_JSON" .state)" \
  || refuse 12 "Could not read PR #$NUMBER with gh pr view: the response was not readable JSON"
IS_DRAFT="$(json_field "$PR_JSON" .isDraft)" \
  || refuse 12 "Could not read PR #$NUMBER with gh pr view: the response was not readable JSON"
PR_NUMBER="$(json_field "$PR_JSON" .number)" \
  || refuse 12 "Could not read PR #$NUMBER with gh pr view: the response was not readable JSON"
[ "$PR_NUMBER" = "$NUMBER" ] || refuse 12 "gh pr view returned a different PR number than #$NUMBER"
if [[ ! "$PR_URL" =~ ^https?://([^/]+)/([^/]+/[^/]+)/pull/([0-9]+)/?$ ]]; then
  refuse 12 "Could not derive owner/repo and number from the PR URL ($PR_URL)"
fi
SLUG="${BASH_REMATCH[2]}"
HOST="${BASH_REMATCH[1]}"
[ "${BASH_REMATCH[3]}" = "$NUMBER" ] || refuse 12 "the PR URL ($PR_URL) is not PR #$NUMBER"
[[ "$HEAD" =~ ^[0-9a-f]{40}$ ]] || refuse 12 "the PR head SHA read from GitHub is not a full commit SHA: '$HEAD'"

# The expected author of the review of record: review.record_author when set, else the login of
# the authenticated account.
AUTHOR="$RECORD_AUTHOR"
if [ -z "$AUTHOR" ]; then
  AUTHOR="$(gh api user --jq .login --hostname "$HOST")" \
    || refuse 15 "could not resolve the expected author: gh api user --jq .login --hostname $HOST failed"
fi
[ -n "$AUTHOR" ] \
  || refuse 15 "no expected author: review.record_author is unset and gh api user --jq .login returned nothing"

# The PR reviews, through the paginated reviews endpoint on the PR's own host (`gh api` does not
# infer the host from the checkout's remote, unlike `gh pr view`).
REVIEWS_JSON="$(
  gh api --paginate "repos/$SLUG/pulls/$NUMBER/reviews" --hostname "$HOST" --jq \
    '.[] | {id: .id, author: .user.login, state: .state, commit_id: .commit_id, submitted_at: .submitted_at, html_url: .html_url, body: .body}'
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
# references/code-review.md's merge guard step 2: list every marker review the selection excluded
# (the selected one is not excluded), with its login, URL and commit, and never a review body.
REVIEWED_COMMIT=""
REVIEW_URL=""
REVIEW_ID=""
REVIEWED_FIRSTLINE_SHA=""
if [ -n "$SELECTED" ]; then
  REVIEW_ID="$(json_field "$SELECTED" .id)" \
    || refuse 15 "the review of record selected on PR #$NUMBER was not readable JSON"
  REVIEWED_COMMIT="$(json_field "$SELECTED" .commit_id)" \
    || refuse 15 "the review of record selected on PR #$NUMBER was not readable JSON"
  REVIEW_URL="$(json_field "$SELECTED" .html_url)" \
    || refuse 15 "the review of record selected on PR #$NUMBER was not readable JSON"
  REVIEW_SUBMITTED="$(json_field "$SELECTED" .submitted_at)" \
    || refuse 15 "the review of record selected on PR #$NUMBER was not readable JSON"
  # A matching marker review that cannot be ordered is refused by name, never reported as absent:
  # claiming no review exists would hide the real cause. Only the documented UTC form is ordered,
  # so a non-UTC timestamp is a refusal rather than a silent skip to an older review.
  if [[ ! "$REVIEW_SUBMITTED" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]]; then
    refuse 15 "the review of record for PR #$NUMBER carries no usable submitted_at timestamp ('$(one_line "$REVIEW_SUBMITTED")'), so the latest matching review cannot be ordered"
  fi
  # The selected review is named in the summary and re-read by a human, so it must carry both a
  # full commit and its own URL; a missing one is a refusal, never the literal `null` in a summary.
  [[ "$REVIEWED_COMMIT" =~ ^[0-9A-Fa-f]{40}$ ]] \
    || refuse 15 "the review of record selected on PR #$NUMBER carries no full commit_id ('$(one_line "$REVIEWED_COMMIT")')"
  REVIEWED_COMMIT_LOWER="${REVIEWED_COMMIT,,}"
  case "$REVIEW_URL" in
    "" | "null" | "-")
      refuse 15 "the review of record selected on PR #$NUMBER carries no html_url, so it cannot be named or re-read"
      ;;
  esac
  # references/code-review.md: the first line is exactly `Review of record <full head SHA>`; any
  # other text in that position is not a review of record.
  FIRST_LINE="$(
    printf '%s' "$SELECTED" \
      | jq -r '.body | split("\n")[0] | sub("\r$"; "") | sub("^[[:space:]]+"; "") | sub("[[:space:]]+$"; "")'
  )" || FIRST_LINE=""
  if [[ "$FIRST_LINE" =~ ^Review\ of\ record\ ([0-9a-f]{40})$ ]]; then
    REVIEWED_FIRSTLINE_SHA="${BASH_REMATCH[1]}"
  else
    REVIEWED_FIRSTLINE_SHA=""
  fi
fi
# Excluded by review id (or its URL when the API returns no id), not by URL alone: an absent URL
# would otherwise list the selected review as excluded. Every printed field is folded to one line
# so a remote value cannot forge a result line.
EXCLUDE_KEY="$REVIEW_ID"
case "$EXCLUDE_KEY" in
  "" | "null") EXCLUDE_KEY="$REVIEW_URL" ;;
esac
EXCLUDED_MARKERS="$(
  printf '%s\n' "$REVIEWS_JSON" | jq -s -r --arg sel "$EXCLUDE_KEY" '
    [ .[] | select((.body // "") | startswith("Review of record")) | select(((.id // .html_url // "") | tostring) != $sel) ]
    | .[] | "Excluded marker review: \((.author // "-") | tostring | gsub("[\\r\\n\\t]"; " ")) \((.html_url // "-") | tostring | gsub("[\\r\\n\\t]"; " ")) \((.commit_id // "-") | tostring | gsub("[\\r\\n\\t]"; " "))"
  '
)" || refuse 15 "Could not list the excluded marker reviews of PR #$NUMBER"

if [ -z "$SELECTED" ]; then
  printf 'PR: %s %s\n' "$NUMBER" "$PR_URL"
  printf 'Live head: %s\n' "$HEAD"
  printf '%s\n' "$EXCLUDED_MARKERS"
  refuse 15 "no review of record on PR #$NUMBER: no COMMENTED review whose body begins with 'Review of record' was submitted by $AUTHOR at the live head $HEAD"
fi

printf 'PR: %s %s\n' "$NUMBER" "$PR_URL"
printf 'Live head: %s\n' "$HEAD"
printf 'Reviewed head: %s\n' "$REVIEWED_COMMIT"
printf 'Review of record: %s\n' "$REVIEW_URL"
if [ -n "$EXCLUDED_MARKERS" ]; then
  printf '%s\n' "$EXCLUDED_MARKERS"
fi

# The first line of the review of record must carry the reviewed head as a full SHA; a value in
# that position is only ever printed after this check, so unrelated review text cannot leak out.
[[ "$REVIEWED_FIRSTLINE_SHA" =~ ^[0-9a-f]{40}$ ]] \
  || refuse 15 "the review of record ($REVIEW_URL) does not carry a full head SHA on its first line"

if [ "$REVIEWED_COMMIT_LOWER" != "$HEAD" ]; then
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
CHECKS_NONE=0
CHECKS_ERR_FILE="$(mktemp)" || refuse 14 "could not create a file for the required-checks stderr of PR #$NUMBER"
trap 'rm -f -- "${CHECKS_ERR_FILE:-}"' EXIT
CHECKS_OUT="$(gh pr checks "$NUMBER" --required --json name,state 2>"$CHECKS_ERR_FILE")" || CHECKS_STATUS=$?
CHECKS_ERR="$(cat -- "$CHECKS_ERR_FILE")"
rm -f -- "$CHECKS_ERR_FILE"
trap - EXIT
case "$CHECKS_STATUS" in
  0 | 1 | 8) ;;
  *) refuse 14 "Could not read the required checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$CHECKS_ERR$CHECKS_OUT")" ;;
esac
if [ -n "$CHECKS_OUT" ]; then
  case "$CHECKS_OUT" in
    \[*) CHECKS_JSON="$CHECKS_OUT" ;;
    *) refuse 14 "Could not read the required checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$CHECKS_ERR$CHECKS_OUT")" ;;
  esac
elif [ "$CHECKS_STATUS" = 1 ]; then
  # gh prints one of these two diagnostics on stderr and exits 1 when there is nothing to report on
  # the head: the branch configures no required checks, or the head has no check contexts at all.
  # Only that whole single-line value means "nothing can be non-green"; a warning or a multiline
  # failure never does, because a `*` in a case pattern would otherwise span lines.
  if [[ "$CHECKS_ERR" == *$'\n'* ]]; then
    refuse 14 "Could not read the required checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$CHECKS_ERR$CHECKS_OUT")"
  fi
  case "$CHECKS_ERR" in
    "no required checks reported on the '"*"' branch" | "no checks reported on the '"*"' branch")
      CHECKS_JSON='[]'
      CHECKS_NONE=1
      ;;
    *) refuse 14 "Could not read the required checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$CHECKS_ERR$CHECKS_OUT")" ;;
  esac
else
  refuse 14 "Could not read the required checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$CHECKS_ERR$CHECKS_OUT")"
fi
CHECKS_COUNT="$(printf '%s' "$CHECKS_JSON" | jq -r 'if type == "array" then length else "invalid" end')" \
  || refuse 14 "the required checks of PR #$NUMBER were not readable JSON"
[ "$CHECKS_COUNT" != "invalid" ] \
  || refuse 14 "the required checks of PR #$NUMBER were not a JSON array"
if [ "$CHECKS_COUNT" = "0" ]; then
  printf 'Check: none\n'
else
  # @tsv escapes tab, CR and LF inside a check name, so a remote-controlled name can never print a
  # second line, let alone a forged `Result:` one.
  while IFS=$'\t' read -r CHECK_NAME CHECK_STATE; do
    printf 'Check: %s=%s\n' "$CHECK_NAME" "$CHECK_STATE"
  done < <(printf '%s' "$CHECKS_JSON" | jq -r '.[] | [.name, .state] | @tsv')
fi
# Only a clean read can authorize a merge; exit 8 still carries the states, and they are reported in
# the refusal, but a command that exited non-zero never counts as green.
NON_GREEN="$(
  printf '%s' "$CHECKS_JSON" \
    | jq -r '[ .[] | select(.state != "SUCCESS") | "\(( .name | tostring | gsub("[\\r\\n\\t]"; " ")))=\((.state | tostring | gsub("[\\r\\n\\t]"; " ")))" ] | join(", ")'
)" || refuse 14 "the required checks of PR #$NUMBER were not readable JSON"
if [ "$CHECKS_STATUS" != 0 ] && [ "$CHECKS_NONE" = 0 ]; then
  refuse 14 "the required checks of PR #$NUMBER were not read cleanly (gh pr checks exited $CHECKS_STATUS): ${NON_GREEN:-none reported}, stderr: $(gh_detail "$CHECKS_ERR")"
fi
if [ -n "$NON_GREEN" ]; then
  refuse 14 "the required checks on head $HEAD are not green: $NON_GREEN"
fi

# The checks are read by PR number, and the PR's readiness can change without its head moving: a
# base advance makes it BEHIND, and a draft flag or a blocking merge state can appear. Re-read the
# whole readiness state, not just the SHA, and refuse on any change, on both the agent and the human
# paths: --match-head-commit bounds only the head, so the human path has no merge attempt to catch a
# base-only change.
MOVED_JSON="$(gh pr view "$NUMBER" --json headRefOid,state,isDraft,mergeable,mergeStateStatus)" \
  || refuse 16 "Could not re-read PR #$NUMBER after the checks read"
RECHECK_HEAD="$(printf '%s' "$MOVED_JSON" | jq -r '.headRefOid // empty')" \
  || refuse 16 "Could not read the live head of PR #$NUMBER after the checks read"
RECHECK_STATE="$(printf '%s' "$MOVED_JSON" | jq -r '.state // empty')" \
  || refuse 16 "Could not read the state of PR #$NUMBER after the checks read"
RECHECK_DRAFT="$(printf '%s' "$MOVED_JSON" | jq -r '.isDraft | tostring')" \
  || refuse 16 "Could not read the draft flag of PR #$NUMBER after the checks read"
RECHECK_MERGEABLE="$(printf '%s' "$MOVED_JSON" | jq -r '.mergeable // empty')" \
  || refuse 16 "Could not read the mergeability of PR #$NUMBER after the checks read"
RECHECK_MERGE_STATE="$(printf '%s' "$MOVED_JSON" | jq -r '.mergeStateStatus // empty')" \
  || refuse 16 "Could not read the merge state of PR #$NUMBER after the checks read"
[ -n "$RECHECK_HEAD" ] \
  || refuse 16 "Could not read the live head of PR #$NUMBER after the checks read"
[ "$RECHECK_HEAD" = "$HEAD" ] \
  || refuse 16 "the head of PR #$NUMBER moved from $HEAD to $RECHECK_HEAD while its checks were read; re-run the helper at the new head"
[ "$RECHECK_STATE" = "OPEN" ] \
  || refuse 16 "PR #$NUMBER is in state $RECHECK_STATE after the checks read, not OPEN"
[ "$RECHECK_DRAFT" != "true" ] \
  || refuse 16 "PR #$NUMBER became a draft (merge state $RECHECK_MERGE_STATE) while its checks were read"
[ "$RECHECK_MERGEABLE" = "MERGEABLE" ] \
  || refuse 16 "PR #$NUMBER is not mergeable after the checks read (mergeable=$RECHECK_MERGEABLE, merge state $RECHECK_MERGE_STATE)"
case "$RECHECK_MERGE_STATE" in
  CLEAN | UNSTABLE) ;;
  *) refuse 16 "PR #$NUMBER is in merge state $RECHECK_MERGE_STATE after the checks read" ;;
esac

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
  is_utc_timestamp() {
    local value="$1" parsed
    [[ "$value" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || return 1
    # The shape is not enough: 2026-99-99T99:99:99Z matches it. Re-render the instant and require
    # the same text, so an impossible calendar date or clock time never counts as a decision.
    parsed="$(date -u -d "$value" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" || return 1
    [ "$parsed" = "$value" ]
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
        is_utc_timestamp "$(trim_field "${FIELD[4]}")" || continue
        CURRENT="APPROVE"
        ;;
      BOUNCE)
        [ "${#FIELD[@]}" -eq 6 ] || continue
        [ -n "$(trim_field "${FIELD[3]}")" ] || continue
        [ -n "$(trim_field "${FIELD[4]}")" ] || continue
        is_utc_timestamp "$(trim_field "${FIELD[5]}")" || continue
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
  if [ -n "$CONFLICT" ]; then
    printf 'Warning: conflicting decisions for %s at head %s in %s: %s; the first decision stands\n' \
      "$REQUEST_ID" "$HEAD" "$APPROVALS" "$CONFLICT" >&2
  fi
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
# refuses here, and a rejected head change below is never retried without it. The already-captured
# help is matched by a bash pattern: piping it into `grep -q` would let grep close the pipe early,
# and `pipefail` would then turn a successful match into a false "unsupported" refusal.
MERGE_HELP="$(gh pr merge --help)" || refuse 17 "could not read gh pr merge --help"
case "$MERGE_HELP" in
  *--match-head-commit*) ;;
  *) refuse 17 "this gh cannot carry an expected-head condition (gh pr merge has no --match-head-commit)" ;;
esac

case "$MERGE_METHOD" in
  squash) METHOD_FLAG="--squash" ;;
  merge) METHOD_FLAG="--merge" ;;
  rebase) METHOD_FLAG="--rebase" ;;
esac

MERGE_OUT=""
MERGE_STATUS=0
MERGE_OUT="$(gh pr merge "$NUMBER" --match-head-commit "$HEAD" "$METHOD_FLAG")" || MERGE_STATUS=$?

# Success only once GitHub reports the PR merged, at the reviewed head; a queued merge is not a
# merge. The read runs after every attempt, so a client error that arrives after GitHub accepted the
# merge is reported as the merge it is, and it never retries the mutation. The attempt's own exit
# status, not its captured output, decides whether it failed.
CONFIRM_JSON="$(gh pr view "$NUMBER" --json state,mergedAt,mergeCommit,headRefOid)" \
  || unconfirmed 17 "could not re-read PR #$NUMBER after the merge command"
CONFIRM_STATE="$(printf '%s' "$CONFIRM_JSON" | jq -r '.state // empty' 2>/dev/null)" || CONFIRM_STATE=""
[ -n "$CONFIRM_STATE" ] \
  || unconfirmed 17 "could not read PR #$NUMBER after the merge command"
CONFIRM_HEAD="$(printf '%s' "$CONFIRM_JSON" | jq -r '.headRefOid // empty' 2>/dev/null)" || CONFIRM_HEAD=""
MERGE_COMMIT="$(printf '%s' "$CONFIRM_JSON" | jq -r '.mergeCommit.oid // empty' 2>/dev/null)" || MERGE_COMMIT=""
if [ "$MERGE_STATUS" != 0 ] && [ "$CONFIRM_STATE" != "MERGED" ]; then
  refuse 17 "gh pr merge $NUMBER --match-head-commit $HEAD $METHOD_FLAG failed (exit $MERGE_STATUS): $(gh_detail "$MERGE_OUT")"
fi
[ "$CONFIRM_STATE" = "MERGED" ] \
  || unconfirmed 17 "the merge was submitted, but PR #$NUMBER is in state $CONFIRM_STATE, not MERGED yet (a queued merge is not a success; re-read the PR before any retry)"
[ "$CONFIRM_HEAD" = "$HEAD" ] \
  || refuse 17 "PR #$NUMBER merged head $CONFIRM_HEAD, not the reviewed head $HEAD"
[ -n "$MERGE_COMMIT" ] || refuse 17 "PR #$NUMBER reports no merge commit after merging head $HEAD"

printf 'Result: merged %s\n' "$MERGE_COMMIT"
