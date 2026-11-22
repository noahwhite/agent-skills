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
# manager approved; the merge runs only once the file holds a valid REQUEST for that ID, this PR,
# the live head, the selected review of record and a green CI state, followed by a matching APPROVE
# for the same ID and head.
#
# It uses the ambient gh auth and never puts a token in argv or in its output.
# Output: the PR number and URL, the live and reviewed head SHAs, the review URL, the check states,
# the marker reviews it excluded, and the merge or refusal result.
#
# Prerequisites: bash 3.2 or later, git, gh, jq, python3 with PyYAML, and the standard core
# utilities (mktemp, cat, rm and tr). The helper checks bash, git, gh, jq and python3 before any
# GitHub call and names the missing one.
# Repository selection comes from --repo (or the current directory) alone: the helper clears every
# inherited GIT_* variable, plus GH_REPO and GH_HOST, before it resolves the repository, so no
# caller environment can move the root, the profile lookup or the repository gh targets.
# A relative --approvals path is resolved against the directory the helper was invoked from.
set -euo pipefail

# The helper's own capture files. They start empty so the cleanup trap can never be pointed at a
# path an inherited environment variable of the same name supplied.
CHECKS_ERR_FILE=""
GH_STDERR_FILE=""

PROG="merge-pr.sh"
REPO_SET=0
# Regexes live in variables: bash 3.2, which macOS ships, parses `[[ x =~ $re ]]` but chokes on
# some literal patterns, so every match below goes through one of these.
PR_URL_RE='^https?://([A-Za-z0-9][A-Za-z0-9.-]*)/([A-Za-z0-9._-]+/[A-Za-z0-9._-]+)/pull/([0-9]+)/?$'
NUMERIC_RE='^[0-9]+$'
LOWER_SHA_RE='^[0-9a-f]{40}$'
MIXED_SHA_RE='^[0-9A-Fa-f]{40}$'
REVIEW_LINE_RE='^Review of record ([0-9A-Fa-f]{40})$'
REVIEW_URL_RE='^https?://([A-Za-z0-9][A-Za-z0-9.-]*)/([A-Za-z0-9._-]+/[A-Za-z0-9._-]+)/pull/([0-9]+)#pullrequestreview-[0-9]+$'
UTC_TIMESTAMP_RE='^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z$'
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
  # One line on stderr too: a refusal's reason can quote remote text, and a raw newline there could
  # forge a result-looking line in a transcript that merges both streams.
  printf '%s: %s\n' "$PROG" "$(one_line "$*")" >&2
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

# GitHub reports the PR merged, but the evidence is incomplete or inconsistent: the merge happened,
# so the caller must not treat this as "nothing merged" and must not retry it.
merged_unverified() {
  local status="$1"
  shift
  printf 'Result: merged but unverified: %s\n' "$(one_line "$*")"
  die "$status" "$*"
}

# Every value this helper prints that came from outside (a check name or state, a review URL, a
# command's output) is folded to one line first, so no remote or proxy text can forge a second
# `Result:` line in the transcript. CR, LF and TAB become spaces; every other C0 control, DEL, and
# the Unicode line separators U+2028, U+2029 and U+0085 are removed, so a terminal escape cannot
# repaint the summary either.
one_line() {
  local value="$1"
  value="${value//$'\r'/ }"
  value="${value//$'\n'/ }"
  value="${value//$'\t'/ }"
  value="${value//$'\342\200\250'/ }" # U+2028 line separator
  value="${value//$'\342\200\251'/ }" # U+2029 paragraph separator
  value="${value//$'\302\205'/ }"     # U+0085 next line
  value="$(printf '%s' "$value" | tr -d '\000-\037\177')"
  printf '%s' "$value"
}

# A command's own output, folded to one line and capped, for a refusal that carries the diagnosis
# without letting that output forge a result line or flood the transcript.
gh_detail() {
  # Folded to one line and bounded so a huge proxy body cannot flood a result line. The cut keeps
  # whole characters and then drops the last partial word.
  local text
  text="$(one_line "$1")"
  if [ "${#text}" -gt 1000 ]; then
    text="${text:0:1000}"
    text="${text% *} [truncated]"
  fi
  printf '%s' "$text"
}

# gh's own stderr is captured rather than let through raw: a proxy or server error is external text
# and must not be able to print a result-looking line beside the helper's own. The captured text is
# emitted only through gh_detail, and only when a call fails. The capture file is created once the
# prerequisites are checked, so a missing prerequisite is still the first thing named.
gh_quiet() {
  gh "$@" 2>"${GH_STDERR_FILE:?gh stderr capture file}"
}
gh_stderr_detail() {
  [ -n "${GH_STDERR_FILE:-}" ] && [ -f "$GH_STDERR_FILE" ] || return 0
  gh_detail "$(cat -- "$GH_STDERR_FILE")"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --repo)
      [ "$REPO_SET" = 0 ] || die 2 "--repo may be given only once"
      REPO_SET=1
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
[[ "$NUMBER" =~ $NUMERIC_RE ]] || die 2 "the PR number must be numeric, got '$NUMBER'"
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
  REQUEST_ID_RE="^REQ-.+-PR${NUMBER}-[1-9][0-9]*$"
  [[ "$REQUEST_ID" =~ $REQUEST_ID_RE ]] \
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
# An inaccessible location is never read as absent (references/profile.md, Fail closed): a plain
# file test is false both for a file that is not there and for a path whose lookup failed, so the
# lookup is done by the interpreter that already reads the profile. It distinguishes "not there"
# from every other error, symlink loops and permission denials included, and a failed lookup
# refuses naming the candidate before any GitHub call.
candidate_state() {
  python3 -I - "$1" <<'PY'
import os
import sys

path = sys.argv[1]
try:
    os.lstat(path)
except FileNotFoundError:
    pass
except OSError:
    print("unsearchable " + os.path.dirname(path))
    raise SystemExit
else:
    print("present")
    raise SystemExit
# The candidate itself is not there. Walk up to the nearest ancestor that can be statted: its own
# lookup needs search permission on the chain above it, so any error other than "not found" means
# the candidate could not be checked, never that it is absent.
directory = os.path.dirname(path) or "."
while True:
    try:
        os.stat(directory)
    except FileNotFoundError:
        parent = os.path.dirname(directory)
        if not parent or parent == directory:
            print("absent")
            raise SystemExit
        directory = parent
        continue
    except OSError:
        print("unsearchable " + directory)
        raise SystemExit
    if os.access(directory, os.X_OK):
        print("absent " + directory)
    else:
        print("unsearchable " + directory)
    raise SystemExit
PY
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

if "record_author" in review and review["record_author"] is None:
    print(f"merge-pr.sh: review.record_author is null in {path}", file=sys.stderr)
    sys.exit(13)
record_author = review.get("record_author")
if record_author is not None and not isinstance(record_author, str):
    print(f"merge-pr.sh: review.record_author must be a string in {path}", file=sys.stderr)
    sys.exit(13)
if isinstance(record_author, str) and not record_author:
    # An explicitly empty value is not the same as an absent one: the schema's login pattern cannot
    # match "", and silently falling back to the ambient account would merge under another identity.
    print(f"merge-pr.sh: review.record_author is empty in {path}", file=sys.stderr)
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
  printf 'Result: merge blocked: the consumer profile %s was rejected\n' "$(one_line "$PROFILE")"
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
GH_STDERR_FILE="$(mktemp)" || {
  printf '%s: could not create a file for gh stderr\n' "$PROG" >&2
  exit 10
}
trap 'rm -f -- "${GH_STDERR_FILE:-}" "${CHECKS_ERR_FILE:-}"' EXIT
PR_JSON="$(gh_quiet pr view "$NUMBER" --json number,url,state,isDraft,mergeable,mergeStateStatus,headRefOid,baseRefName,mergeCommit,mergedAt)" \
  || refuse 12 "Could not read PR #$NUMBER with gh pr view: $(gh_stderr_detail)"
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
BASE_REF="$(json_field "$PR_JSON" .baseRefName)" \
  || refuse 12 "Could not read PR #$NUMBER with gh pr view: the response was not readable JSON"
[ -n "$BASE_REF" ] && [ "$BASE_REF" != "null" ] || refuse 12 "PR #$NUMBER carries no base branch name"
case "$IS_DRAFT" in
  true | false) ;;
  *) refuse 12 "PR #$NUMBER carries no boolean draft flag ('$(one_line "$IS_DRAFT")')" ;;
esac
[ "$PR_NUMBER" = "$NUMBER" ] || refuse 12 "gh pr view returned a different PR number than #$NUMBER"
if [[ ! "$PR_URL" =~ $PR_URL_RE ]]; then
  refuse 12 "Could not derive owner/repo and number from the PR URL ($PR_URL)"
fi
SLUG="${BASH_REMATCH[2]}"
HOST="${BASH_REMATCH[1]}"
[ "${BASH_REMATCH[3]}" = "$NUMBER" ] || refuse 12 "the PR URL ($PR_URL) is not PR #$NUMBER"
[[ "$HEAD" =~ $LOWER_SHA_RE ]] || refuse 12 "the PR head SHA read from GitHub is not a full commit SHA: '$HEAD'"

# A re-run after a queued merge landed finds the PR already merged. That is a satisfied end state,
# not a blocked merge and not a new merge: report the observed state and run no merge command.
if [ "$PR_STATE" = "MERGED" ]; then
  ALREADY_COMMIT="$(json_field "$PR_JSON" .mergeCommit.oid)" || ALREADY_COMMIT=""
  printf 'PR: %s %s\n' "$NUMBER" "$PR_URL"
  printf 'Live head: %s\n' "$HEAD"
  [[ "$ALREADY_COMMIT" =~ $LOWER_SHA_RE ]] \
    || merged_unverified 17 "PR #$NUMBER is already MERGED but reports no full merge commit; re-read the PR by hand"
  printf 'Merge attempt: none (this invocation ran no merge command)\n'
  printf 'Result: already merged %s\n' "$ALREADY_COMMIT"
  exit 0
fi

# The expected author of the review of record: review.record_author when set, else the login of
# the authenticated account.
AUTHOR="$RECORD_AUTHOR"
if [ -z "$AUTHOR" ]; then
  AUTHOR="$(gh_quiet api user --jq .login --hostname "$HOST")" \
    || refuse 15 "could not resolve the expected author: review.record_author is unset and gh api user --jq .login --hostname $HOST failed: $(gh_stderr_detail)"
fi
[ -n "$AUTHOR" ] \
  || refuse 15 "no expected author: review.record_author is unset and gh api user --jq .login returned nothing"

# The PR reviews, through the paginated reviews endpoint on the PR's own host (`gh api` does not
# infer the host from the checkout's remote, unlike `gh pr view`).
REVIEWS_JSON="$(
  gh_quiet api --paginate "repos/$SLUG/pulls/$NUMBER/reviews" --hostname "$HOST" --jq \
    '.[] | {id: .id, author: .user.login, state: .state, commit_id: .commit_id, submitted_at: .submitted_at, html_url: .html_url, body: .body}'
)" || refuse 15 "Could not read the reviews of PR #$NUMBER with gh api --paginate: $(gh_stderr_detail)"

# Among the COMMENTED reviews whose body begins with 'Review of record', the expected author's,
# with the greatest submitted_at. Every matching review's timestamp is audited first: an
# unorderable timestamp is a refusal, never a silent skip to an older review and never a clean
# audit, and a review whose submitted_at is not a string counts as unorderable rather than failing
# the audit with a jq error that the caller could mistake for success.
SELECTED=""
if [ -n "$REVIEWS_JSON" ]; then
  UNUSABLE_COUNT="$(
    printf '%s\n' "$REVIEWS_JSON" | jq -s -r --arg author "$AUTHOR" --arg re "$UTC_TIMESTAMP_RE" '
      [ .[]
        | select(.state == "COMMENTED")
        | select((.body // "") | startswith("Review of record"))
        | select(((.author // "") | ascii_downcase) == ($author | ascii_downcase))
        | select(if (.submitted_at | type) == "string"
                 then ((.submitted_at | test($re)) | not)
                 else true end) ]
      | length
    '
  )" || refuse 15 "could not audit the submitted_at timestamps of the reviews of PR #$NUMBER"
  [[ "$UNUSABLE_COUNT" =~ $NUMERIC_RE ]] \
    || refuse 15 "could not audit the submitted_at timestamps of the reviews of PR #$NUMBER"
  if [ "$UNUSABLE_COUNT" != 0 ]; then
    refuse 15 "$UNUSABLE_COUNT matching review-of-record marker(s) on PR #$NUMBER carry no usable submitted_at timestamp, so the latest matching review cannot be ordered"
  fi
  # Two reviews tied at the latest submitted_at cannot be ordered; refusing is the only fail-closed
  # reading of "select the greatest submitted_at".
  TIE_COUNT="$(
    printf '%s\n' "$REVIEWS_JSON" | jq -s -r --arg author "$AUTHOR" '
      [ .[]
        | select(.state == "COMMENTED")
        | select((.body // "") | startswith("Review of record"))
        | select(((.author // "") | ascii_downcase) == ($author | ascii_downcase)) ]
      | unique_by(.id)
      | if length == 0 then 0
        else (map(.submitted_at) | max) as $latest
          | map(select(.submitted_at == $latest)) | length end
    '
  )" || refuse 15 "Could not order the reviews of record of PR #$NUMBER"
  if [ "$TIE_COUNT" != 0 ] && [ "$TIE_COUNT" != 1 ]; then
    refuse 15 "$TIE_COUNT matching review-of-record marker(s) on PR #$NUMBER share the latest submitted_at, so the review of record cannot be ordered"
  fi
  SELECTED="$(
    printf '%s\n' "$REVIEWS_JSON" | jq -s --arg author "$AUTHOR" '
      [ .[]
        | select(.state == "COMMENTED")
        | select((.body // "") | startswith("Review of record"))
        | select(((.author // "") | ascii_downcase) == ($author | ascii_downcase)) ]
      | unique_by(.id)
      | sort_by(.submitted_at)
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
  # The selected review is named in the summary and re-read by a human, so it must carry both a
  # full commit and a URL on this PR's own host and repository; anything else is a refusal, never
  # the literal `null` or a URL that points somewhere else in the summary.
  [[ "$REVIEWED_COMMIT" =~ $MIXED_SHA_RE ]] \
    || refuse 15 "the review of record selected on PR #$NUMBER carries no full commit_id ('$(one_line "$REVIEWED_COMMIT")')"
  REVIEWED_COMMIT_LOWER="$(printf '%s' "$REVIEWED_COMMIT" | tr 'A-F' 'a-f')"
  if [[ ! "$REVIEW_URL" =~ $REVIEW_URL_RE ]]; then
    refuse 15 "the review of record selected on PR #$NUMBER carries no usable html_url ('$(one_line "$REVIEW_URL")')"
  fi
  if [ "${BASH_REMATCH[1]}" != "$HOST" ] || [ "${BASH_REMATCH[2]}" != "$SLUG" ] || [ "${BASH_REMATCH[3]}" != "$NUMBER" ]; then
    refuse 15 "the review of record URL ('$(one_line "$REVIEW_URL")') is not on PR #$NUMBER at $HOST/$SLUG"
  fi
  # references/code-review.md: the first line is exactly `Review of record <full head SHA>`; any
  # other text in that position is not a review of record.
  FIRST_LINE="$(
    printf '%s' "$SELECTED" \
      | jq -r '.body | split("\n")[0] | sub("\r$"; "") | sub("^[[:space:]]+"; "") | sub("[[:space:]]+$"; "")'
  )" || FIRST_LINE=""
  if [[ "$FIRST_LINE" =~ $REVIEW_LINE_RE ]]; then
    REVIEWED_FIRSTLINE_SHA="$(printf '%s' "${BASH_REMATCH[1]}" | tr 'A-F' 'a-f')"
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
    | .[] | "Excluded marker review: \((.author // "-") | tostring | gsub("[\u0001-\u001f\u007f\u2028\u2029\u0085]"; " ")) \((.html_url // "-") | tostring | gsub("[\u0001-\u001f\u007f\u2028\u2029\u0085]"; " ")) \((.commit_id // "-") | tostring | gsub("[\u0001-\u001f\u007f\u2028\u2029\u0085]"; " "))"
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
[[ "$REVIEWED_FIRSTLINE_SHA" =~ $LOWER_SHA_RE ]] \
  || refuse 15 "the review of record ($REVIEW_URL) does not carry a full head SHA on its first line"

if [ "$REVIEWED_COMMIT_LOWER" != "$HEAD" ]; then
  refuse 15 "the review of record ($REVIEW_URL) covers commit $REVIEWED_COMMIT, but the live head of PR #$NUMBER is $HEAD"
fi
if [ "$REVIEWED_FIRSTLINE_SHA" != "$HEAD" ]; then
  refuse 15 "the review of record ($REVIEW_URL) names $REVIEWED_FIRSTLINE_SHA on its first line, but the live head of PR #$NUMBER is $HEAD"
fi

# The manager-approval handshake: once the brief assigns merge approval to a manager, the merge
# runs only after a matching APPROVE for the live head is recorded.
if [ -n "$APPROVALS" ]; then
  if [ ! -e "$APPROVALS" ]; then
    refuse 18 "the approvals file $(one_line "$APPROVALS") does not exist"
  fi
  [ -f "$APPROVALS" ] || refuse 18 "the approvals path $(one_line "$APPROVALS") is not a regular file"
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
    # Real calendar validation in pure bash (no GNU date), so the helper stays portable: the shape
    # alone is not enough, because 2026-99-99T99:99:99Z matches it.
    local value="$1" year month day hour minute second days
    [[ "$value" =~ $UTC_TIMESTAMP_RE ]] || return 1
    year=$((10#${BASH_REMATCH[1]}))
    month=$((10#${BASH_REMATCH[2]}))
    day=$((10#${BASH_REMATCH[3]}))
    hour=$((10#${BASH_REMATCH[4]}))
    minute=$((10#${BASH_REMATCH[5]}))
    second=$((10#${BASH_REMATCH[6]}))
    [ "$month" -ge 1 ] && [ "$month" -le 12 ] || return 1
    [ "$hour" -le 23 ] && [ "$minute" -le 59 ] && [ "$second" -le 59 ] || return 1
    case "$month" in
      1 | 3 | 5 | 7 | 8 | 10 | 12) days=31 ;;
      4 | 6 | 9 | 11) days=30 ;;
      2)
        if { [ $((year % 4)) -eq 0 ] && [ $((year % 100)) -ne 0 ]; } || [ $((year % 400)) -eq 0 ]; then
          days=29
        else
          days=28
        fi
        ;;
      *) return 1 ;;
    esac
    [ "$day" -ge 1 ] && [ "$day" -le "$days" ]
  }
  # references/merge-approval.md: the engineer asks with a REQUEST for the request ID, the PR URL,
  # the full head SHA, the review-of-record URL and a green CI state, and only then can a manager
  # decision for that same ID and head authorize the merge. A decision whose head differs from the
  # request's is invalid, and a decision with no valid request before it approves nothing.
  REQUEST_SEEN=0
  DECISION=""
  DECISION_VERDICT=""
  CONFLICT=""
  RECORD_NO=0
  MALFORMED_LINES=""
  while IFS= read -r LINE; do
    RECORD_NO=$((RECORD_NO + 1))
    IFS='|' read -r -a FIELD <<<"$LINE"
    [ "${#FIELD[@]}" -ge 3 ] || continue
    VERDICT="$(trim_field "${FIELD[0]}")"
    RECORD_ID="$(trim_field "${FIELD[1]}")"
    [ "$RECORD_ID" = "$REQUEST_ID" ] || continue
    case "$VERDICT" in
      REQUEST)
        if [ "${#FIELD[@]}" -ne 7 ] ||
          [ "$(trim_field "${FIELD[2]}")" != "$PR_URL" ] ||
          [ "$(trim_field "${FIELD[3]}")" != "$HEAD" ] ||
          [ "$(trim_field "${FIELD[4]}")" != "$REVIEW_URL" ] ||
          [ "$(trim_field "${FIELD[5]}")" != "green" ] ||
          ! is_utc_timestamp "$(trim_field "${FIELD[6]}")"; then
          MALFORMED_LINES="$MALFORMED_LINES $RECORD_NO"
          continue
        fi
        REQUEST_SEEN=1
        continue
        ;;
      APPROVE)
        if [ "$REQUEST_SEEN" != 1 ] ||
          [ "${#FIELD[@]}" -ne 5 ] ||
          [ "$(trim_field "${FIELD[2]}")" != "$HEAD" ] ||
          [ -z "$(trim_field "${FIELD[3]}")" ] ||
          ! is_utc_timestamp "$(trim_field "${FIELD[4]}")"; then
          MALFORMED_LINES="$MALFORMED_LINES $RECORD_NO"
          continue
        fi
        CURRENT="APPROVE"
        CURRENT_VERDICT="APPROVE"
        ;;
      BOUNCE)
        if [ "$REQUEST_SEEN" != 1 ] ||
          [ "${#FIELD[@]}" -ne 6 ] ||
          [ "$(trim_field "${FIELD[2]}")" != "$HEAD" ] ||
          [ -z "$(trim_field "${FIELD[3]}")" ] ||
          [ -z "$(trim_field "${FIELD[4]}")" ] ||
          ! is_utc_timestamp "$(trim_field "${FIELD[5]}")"; then
          MALFORMED_LINES="$MALFORMED_LINES $RECORD_NO"
          continue
        fi
        CURRENT="BOUNCE $(trim_field "${FIELD[4]}")"
        CURRENT_VERDICT="BOUNCE"
        ;;
      *) continue ;;
    esac
    if [ -z "$DECISION" ]; then
      DECISION="$CURRENT"
      DECISION_VERDICT="$CURRENT_VERDICT"
    elif [ "$CURRENT_VERDICT" != "$DECISION_VERDICT" ]; then
      CONFLICT="first $DECISION_VERDICT, later $CURRENT_VERDICT"
    fi
  done <"$APPROVALS"
  if [ -n "$MALFORMED_LINES" ]; then
    printf 'Warning: malformed decision record(s) for %s at head %s were ignored (record number(s):%s); under references/merge-approval.md they are not decisions\n' \
      "$(one_line "$REQUEST_ID")" "$HEAD" "$MALFORMED_LINES" >&2
  fi
  if [ -n "$CONFLICT" ]; then
    printf 'Warning: conflicting decisions for %s at head %s in %s: %s; the first decision stands\n' \
      "$(one_line "$REQUEST_ID")" "$HEAD" "$(one_line "$APPROVALS")" "$(one_line "$CONFLICT")" >&2
  fi
  if [ "$REQUEST_SEEN" != 1 ]; then
    refuse 18 "no valid REQUEST for $REQUEST_ID at head $HEAD in file $APPROVALS: the request must name this PR, this head, the selected review of record and a green CI state before any decision can authorize a merge"
  fi
  case "$DECISION" in
    APPROVE) ;;
    BOUNCE*) refuse 18 "the manager bounced $REQUEST_ID at $HEAD: ${DECISION#BOUNCE }" ;;
    *) refuse 18 "no APPROVE recorded for $REQUEST_ID at head $HEAD in $APPROVALS" ;;
  esac
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

CHECKS_ALL=""
CHECKS_STATUS=0
CHECKS_EMPTY=0
SERVER_REQUIRED=""
SERVER_REQUIRED_NONE=0
POLICY_CONTEXTS=""
POLICY_CLASSIC_UNREADABLE=0

# Every page of the applicable rules, flattened (--slurp returns one array per page), and the
# branch's own protection configuration, read from the branch endpoint: both can impose required
# checks on one branch, so the union counts. Each requirement is printed as
# "<context><TAB><app-id>", with the app id empty when the policy does not name one. Exit 0 only
# when every source is fully read and well formed; anything else is a hard failure, because an
# unreadable policy must never read as an empty one.
policy_required_contexts() {
  local encoded rules from_rules branch from_branch
  encoded="$(printf '%s' "$BASE_REF" | jq -rn --arg v "$BASE_REF" '$v|@uri')" || return 2
  rules="$(gh_quiet api --paginate --slurp "repos/$SLUG/rules/branches/$encoded" --hostname "$HOST")" || return 2
  printf '%s' "$rules" | jq -e 'type == "array"' >/dev/null 2>&1 || return 2
  rules="$(printf '%s' "$rules" | jq -c '[ .[] | if type == "array" then .[] else . end ]')" || return 2
  # A recognized required-checks rule whose list is not an array is a policy this helper cannot
  # certify, not an empty one.
  if printf '%s' "$rules" | jq -e '[ .[] | select(.type == "required_status_checks") | select((.parameters.required_status_checks | type) != "array") ] | length > 0' >/dev/null 2>&1; then
    return 2
  fi
  from_rules="$(printf '%s' "$rules" | jq -r '[ .[] | select(.type == "required_status_checks") | .parameters.required_status_checks[] | [ .context, ((.integration_id // "") | tostring) ] | @tsv ] | .[]')" || return 2
  branch="$(gh_quiet api "repos/$SLUG/branches/$encoded" --hostname "$HOST")" || return 2
  printf '%s' "$branch" | jq -e 'type == "object" and ((.protected | type) == "boolean")' >/dev/null 2>&1 || return 2
  from_branch=""
  if [ "$(printf '%s' "$branch" | jq -r '.protected')" = "true" ]; then
    # A protected branch must expose its protection object and a readable required-status-checks
    # shape; a bounded endpoint with no protection is handled by .protected being false.
    printf '%s' "$branch" | jq -e '(.protection | type) == "object" and ((.protection.required_status_checks | type) == "object" or .protection.required_status_checks == null)' >/dev/null 2>&1 || return 2
    from_branch="$(printf '%s' "$branch" | jq -r '[
        ((.protection.required_status_checks.contexts // [])[] | [ ., "" ] | @tsv),
        ((.protection.required_status_checks.checks // [])[] | [ .context, ((.app_id // "") | tostring) ] | @tsv)
      ] | .[]')" || return 2
  fi
  if [ -n "$from_rules" ]; then printf '%s\n' "$from_rules"; fi
  if [ -n "$from_branch" ]; then printf '%s\n' "$from_branch"; fi
  return 0
}

CHECKS_ERR_FILE="$(mktemp)" || refuse 14 "could not create a file for the checks stderr of PR #$NUMBER"

# GitHub's own required set for this head (rulesets and classic protection included, computed
# server-side). A check the server requires but that has not reported is not in this list, which is
# why the readable branch policy is unioned in below.
SERVER_OUT="$(gh pr checks "$NUMBER" --required --json name,state 2>"$CHECKS_ERR_FILE")" || CHECKS_STATUS=$?
SERVER_ERR="$(cat -- "$CHECKS_ERR_FILE")"
case "$CHECKS_STATUS" in
  0 | 1 | 8) ;;
  *) refuse 14 "Could not read the required checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$SERVER_ERR$SERVER_OUT")" ;;
esac
if [ -n "$SERVER_OUT" ]; then
  case "$SERVER_OUT" in
    \[*) SERVER_REQUIRED="$(printf '%s' "$SERVER_OUT" | jq -r '.[].name' 2>/dev/null)" || refuse 14 "the required checks of PR #$NUMBER were not readable JSON" ;;
    *) refuse 14 "Could not read the required checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$SERVER_ERR$SERVER_OUT")" ;;
  esac
else
  case "$CHECKS_STATUS" in
    0) refuse 14 "Could not read the required checks of PR #$NUMBER: gh pr checks exited 0 with no output" ;;
    1 | 8)
      if [[ "$SERVER_ERR" != *$'\n'* ]]; then
        case "$SERVER_ERR" in
          "no required checks reported on the '"*"' branch" | "no checks reported on the '"*"' branch") SERVER_REQUIRED_NONE=1 ;;
          *) refuse 14 "Could not read the required checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$SERVER_ERR")" ;;
        esac
      else
        refuse 14 "Could not read the required checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$SERVER_ERR")"
      fi
      ;;
    *) refuse 14 "Could not read the required checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$SERVER_ERR")" ;;
  esac
fi

# The states of every check reported on the head.
CHECKS_STATUS=0
CHECKS_ALL="$(gh pr checks "$NUMBER" --json name,state 2>"$CHECKS_ERR_FILE")" || CHECKS_STATUS=$?
CHECKS_ERR="$(cat -- "$CHECKS_ERR_FILE")"
rm -f -- "$CHECKS_ERR_FILE"
case "$CHECKS_STATUS" in
  0 | 1 | 8) ;;
  *) refuse 14 "Could not read the checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$CHECKS_ERR$CHECKS_ALL")" ;;
esac
if [ -n "$CHECKS_ALL" ]; then
  case "$CHECKS_ALL" in
    \[*) : ;;
    *) refuse 14 "Could not read the checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$CHECKS_ERR$CHECKS_ALL")" ;;
  esac
else
  case "$CHECKS_STATUS" in
    0) refuse 14 "Could not read the checks of PR #$NUMBER: gh pr checks exited 0 with no output" ;;
    1 | 8)
      if [[ "$CHECKS_ERR" != *$'\n'* ]]; then
        case "$CHECKS_ERR" in
          "no checks reported on the '"*"' branch" | "no required checks reported on the '"*"' branch")
            CHECKS_ALL='[]'
            CHECKS_EMPTY=1
            ;;
          *) refuse 14 "Could not read the checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$CHECKS_ERR")" ;;
        esac
      else
        refuse 14 "Could not read the checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$CHECKS_ERR")"
      fi
      ;;
    *) refuse 14 "Could not read the checks of PR #$NUMBER (gh pr checks exited $CHECKS_STATUS): $(gh_detail "$CHECKS_ERR")" ;;
  esac
fi
printf '%s' "$CHECKS_ALL" | jq -e 'type == "array"' >/dev/null 2>&1 \
  || refuse 14 "the checks of PR #$NUMBER were not a JSON array"

POLICY_ROWS="$(policy_required_contexts)" \
  || refuse 14 "could not read the required-check configuration of $BASE_REF on $HOST/$SLUG, so the head cannot be judged green: $(gh_stderr_detail)"

# The union of the server-required names (no app identity) and the policy pairs, deduplicated on the
# exact pair. Exact comparison: a plain substring test would collapse names such as `a|b` and `b`.
UNION_CONTEXTS=()
UNION_APPS=()
add_requirement() {
  local ctx="$1" app="$2" i
  [ -n "$ctx" ] || return 0
  i=0
  while [ "$i" -lt "${#UNION_CONTEXTS[@]}" ]; do
    if [ "${UNION_CONTEXTS[$i]}" = "$ctx" ] && [ "${UNION_APPS[$i]}" = "$app" ]; then
      return 0
    fi
    i=$((i + 1))
  done
  UNION_CONTEXTS+=("$ctx")
  UNION_APPS+=("$app")
}
while IFS= read -r SERVER_NAME; do add_requirement "$SERVER_NAME" ""; done <<<"$SERVER_REQUIRED"
while IFS=$'\t' read -r POLICY_NAME POLICY_APP; do add_requirement "$POLICY_NAME" "${POLICY_APP:-}"; done <<<"$POLICY_ROWS"

# A required check that names a producer app is only satisfied by a successful check run from that
# app, so the check runs of the head are read once when any requirement names one.
CHECK_RUNS=""
NEED_APP=0
for i in ${UNION_APPS[@]+"${UNION_APPS[@]}"}; do
  [ -z "$i" ] || NEED_APP=1
done
if [ "$NEED_APP" = 1 ]; then
  CHECK_RUNS="$(gh_quiet api --paginate --slurp "repos/$SLUG/commits/$HEAD/check-runs" --hostname "$HOST")" \
    || refuse 14 "a required check names a producer app, and the check runs of head $HEAD could not be read"
  printf '%s' "$CHECK_RUNS" | jq -e 'type == "array"' >/dev/null 2>&1 \
    || refuse 14 "the check runs of head $HEAD were not readable JSON"
  CHECK_RUNS="$(printf '%s' "$CHECK_RUNS" | jq -c '[ .[] | if type == "array" then .[] else . end ] | [ .[] | .check_runs[]? ]')" \
    || refuse 14 "the check runs of head $HEAD were not readable JSON"
fi

if [ "${#UNION_CONTEXTS[@]}" -eq 0 ]; then
  printf 'Check: none\n'
else
  MISSING_CONTEXTS=""
  NON_GREEN=""
  i=0
  while [ "$i" -lt "${#UNION_CONTEXTS[@]}" ]; do
    REQUIRED_NAME="${UNION_CONTEXTS[$i]}"
    REQUIRED_APP="${UNION_APPS[$i]}"
    i=$((i + 1))
    REQUIRED_STATE="$(printf '%s' "$CHECKS_ALL" | jq -r --arg n "$REQUIRED_NAME" '[ .[] | select(.name == $n) | .state ] | if length == 0 then "MISSING" elif ([ .[] | select(. != "SUCCESS") ] | length) == 0 then "SUCCESS" else join(",") end')" \
      || refuse 14 "the checks of PR #$NUMBER were not readable JSON"
    if [ -n "$REQUIRED_APP" ]; then
      APP_OK="$(printf '%s' "$CHECK_RUNS" | jq -r --arg n "$REQUIRED_NAME" --arg a "$REQUIRED_APP" '[ .[] | select(.name == $n and ((.app.id // "") | tostring) == $a and .conclusion == "success") ] | length')" \
        || refuse 14 "the check runs of head $HEAD were not readable JSON"
      if [ "$APP_OK" = 0 ]; then
        printf 'Check: %s=%s (app %s)\n' "$(one_line "$REQUIRED_NAME")" "MISSING-FROM-APP" "$(one_line "$REQUIRED_APP")"
        MISSING_CONTEXTS="$MISSING_CONTEXTS$(one_line "$REQUIRED_NAME") (app $(one_line "$REQUIRED_APP")); "
        continue
      fi
      printf 'Check: %s=%s (app %s)\n' "$(one_line "$REQUIRED_NAME")" "$(one_line "$REQUIRED_STATE")" "$(one_line "$REQUIRED_APP")"
    else
      printf 'Check: %s=%s\n' "$(one_line "$REQUIRED_NAME")" "$(one_line "$REQUIRED_STATE")"
    fi
    case "$REQUIRED_STATE" in
      SUCCESS) ;;
      MISSING) MISSING_CONTEXTS="$MISSING_CONTEXTS$(one_line "$REQUIRED_NAME"); " ;;
      *) NON_GREEN="$NON_GREEN$(one_line "$REQUIRED_NAME")=$(one_line "$REQUIRED_STATE"), " ;;
    esac
  done
  if [ -n "$MISSING_CONTEXTS" ]; then
    refuse 14 "required check(s) on head $HEAD have not reported as green, so they are not green: $MISSING_CONTEXTS"
  fi
  if [ -n "$NON_GREEN" ]; then
    refuse 14 "the required checks on head $HEAD are not green: $NON_GREEN"
  fi
fi

# The checks are read by PR number, and the PR's readiness can change without its head moving: a
# base advance makes it BEHIND, and a draft flag or a blocking merge state can appear. Re-read the
# whole readiness state, not just the SHA, and refuse on any change, on both the agent and the human
# paths: --match-head-commit bounds only the head, so the human path has no merge attempt to catch a
# base-only change.
MOVED_JSON="$(gh_quiet pr view "$NUMBER" --json headRefOid,baseRefName,state,isDraft,mergeable,mergeStateStatus)" \
  || refuse 16 "Could not re-read PR #$NUMBER after the checks read: $(gh_stderr_detail)"
RECHECK_HEAD="$(printf '%s' "$MOVED_JSON" | jq -r '.headRefOid // empty')" \
  || refuse 16 "Could not read the live head of PR #$NUMBER after the checks read"
RECHECK_BASE="$(printf '%s' "$MOVED_JSON" | jq -r '.baseRefName // empty')" \
  || refuse 16 "Could not read the base branch of PR #$NUMBER after the checks read"
RECHECK_STATE="$(printf '%s' "$MOVED_JSON" | jq -r '.state // empty')" \
  || refuse 16 "Could not read the state of PR #$NUMBER after the checks read"
RECHECK_DRAFT="$(printf '%s' "$MOVED_JSON" | jq -r '.isDraft | tostring')" \
  || refuse 16 "Could not read the draft flag of PR #$NUMBER after the checks read"
[ "$RECHECK_DRAFT" = "true" ] || [ "$RECHECK_DRAFT" = "false" ] \
  || refuse 16 "PR #$NUMBER carries no boolean draft flag after the checks read ('$(one_line "$RECHECK_DRAFT")')"
RECHECK_MERGEABLE="$(printf '%s' "$MOVED_JSON" | jq -r '.mergeable // empty')" \
  || refuse 16 "Could not read the mergeability of PR #$NUMBER after the checks read"
RECHECK_MERGE_STATE="$(printf '%s' "$MOVED_JSON" | jq -r '.mergeStateStatus // empty')" \
  || refuse 16 "Could not read the merge state of PR #$NUMBER after the checks read"
[ -n "$RECHECK_HEAD" ] \
  || refuse 16 "Could not read the live head of PR #$NUMBER after the checks read"
[ "$RECHECK_HEAD" = "$HEAD" ] \
  || refuse 16 "the head of PR #$NUMBER moved from $HEAD to $RECHECK_HEAD while its checks were read; re-run the helper at the new head"
[ "$RECHECK_BASE" = "$BASE_REF" ] \
  || refuse 16 "PR #$NUMBER was retargeted from $BASE_REF to ${RECHECK_BASE:-an unreadable base} while its checks were read"
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

# The human merge owner performs the merge itself.
if [ "$MERGE_OWNER" = "human" ]; then
  printf 'Result: merge-ready; profile.review.merge_owner is human, so no merge command was run\n'
  exit 0
fi

# The merge must carry the reviewed head as an expected-head condition; a gh that cannot carry one
# refuses here, and a rejected head change below is never retried without it. The already-captured
# help is matched by a bash pattern: piping it into `grep -q` would let grep close the pipe early,
# and `pipefail` would then turn a successful match into a false "unsupported" refusal.
MERGE_HELP="$(gh_quiet pr merge --help)" || refuse 17 "could not read gh pr merge --help: $(gh_stderr_detail)"
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
MERGE_OUT="$(gh_quiet pr merge "$NUMBER" --match-head-commit "$HEAD" "$METHOD_FLAG")" || MERGE_STATUS=$?
# Keep the merge attempt's own diagnosis before the confirmation read overwrites the capture file.
MERGE_STDERR_DETAIL="$(gh_stderr_detail)"

# Success only once GitHub reports the PR merged, at the reviewed head; a queued merge is not a
# merge. The read runs after every attempt, so a client error that arrives after GitHub accepted the
# merge is reported as the merge it is, and it never retries the mutation. The attempt's own exit
# status, not its captured output, decides whether it failed.
CONFIRM_JSON="$(gh_quiet pr view "$NUMBER" --json state,mergedAt,mergeCommit,headRefOid)" \
  || unconfirmed 17 "could not re-read PR #$NUMBER after the merge command: $(gh_stderr_detail)"
CONFIRM_STATE="$(printf '%s' "$CONFIRM_JSON" | jq -r '.state // empty' 2>/dev/null)" || CONFIRM_STATE=""
[ -n "$CONFIRM_STATE" ] \
  || unconfirmed 17 "could not read PR #$NUMBER after the merge command"
CONFIRM_HEAD="$(printf '%s' "$CONFIRM_JSON" | jq -r '.headRefOid // empty' 2>/dev/null)" || CONFIRM_HEAD=""
MERGE_COMMIT="$(printf '%s' "$CONFIRM_JSON" | jq -r '.mergeCommit.oid // empty' 2>/dev/null)" || MERGE_COMMIT=""
if [ "$MERGE_STATUS" != 0 ] && [ "$CONFIRM_STATE" != "MERGED" ]; then
  refuse 17 "gh pr merge $NUMBER --match-head-commit $HEAD $METHOD_FLAG failed (exit $MERGE_STATUS): $(gh_detail "$MERGE_OUT") ${MERGE_STDERR_DETAIL:-}"
fi
[ "$CONFIRM_STATE" = "MERGED" ] \
  || unconfirmed 17 "the merge was submitted, but PR #$NUMBER is in state $CONFIRM_STATE, not MERGED yet (a queued merge is not a success; re-read the PR before any retry)"
[ "$CONFIRM_HEAD" = "$HEAD" ] \
  || merged_unverified 17 "the merge attempt ran, and PR #$NUMBER reports merged head $CONFIRM_HEAD, not the reviewed head $HEAD"
[[ "$MERGE_COMMIT" =~ $LOWER_SHA_RE ]] \
  || merged_unverified 17 "PR #$NUMBER reports MERGED but no full merge commit after merging head $HEAD ('$(one_line "$MERGE_COMMIT")')"

# Report the attempt and the observed state separately: a client error can arrive after GitHub
# accepted the merge, and a MERGED PR is a fact about the PR, not proof that this call merged it.
if [ "$MERGE_STATUS" != 0 ]; then
  printf 'Merge attempt: gh pr merge exited %s (client error); GitHub reports PR #%s MERGED at the reviewed head %s\n' \
    "$MERGE_STATUS" "$NUMBER" "$HEAD"
else
  printf 'Merge attempt: gh pr merge exited 0; GitHub reports PR #%s MERGED at the reviewed head %s\n' \
    "$NUMBER" "$HEAD"
fi

printf 'Result: merged %s\n' "$MERGE_COMMIT"
