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
# and the merge or refusal result.
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

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI (gh) is required." >&2
  exit 10
fi

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
  [ -f "$AGENT_SKILLS_PROFILE" ] || die 13 "no consumer profile at AGENT_SKILLS_PROFILE ($AGENT_SKILLS_PROFILE); also searched $ROOT/.agent-skills/profile.yaml and ~/.config/agent-skills/profile.yaml"
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
  || die 12 "Could not read PR #$NUMBER with gh pr view"
json_field() { printf '%s' "$1" | jq -r "$2"; }
PR_URL="$(json_field "$PR_JSON" .url)"
HEAD="$(json_field "$PR_JSON" .headRefOid)"
MERGEABLE="$(json_field "$PR_JSON" .mergeable)"
MERGE_STATE="$(json_field "$PR_JSON" .mergeStateStatus)"
PR_STATE="$(json_field "$PR_JSON" .state)"
IS_DRAFT="$(json_field "$PR_JSON" .isDraft)"
[ "$(json_field "$PR_JSON" .number)" = "$NUMBER" ] || die 12 "gh pr view returned a different PR number than #$NUMBER"
if [[ ! "$PR_URL" =~ ^https?://([^/]+)/([^/]+/[^/]+)/pull/([0-9]+)/?$ ]]; then
  die 12 "Could not derive owner/repo and number from the PR URL ($PR_URL)"
fi
SLUG="${BASH_REMATCH[2]}"
[ "${BASH_REMATCH[3]}" = "$NUMBER" ] || die 12 "the PR URL ($PR_URL) is not PR #$NUMBER"
[[ "$HEAD" =~ ^[0-9a-f]{40}$ ]] || die 12 "the PR head SHA read from GitHub is not a full commit SHA: '$HEAD'"

# The expected author of the review of record: review.record_author when set, else the login of
# the authenticated account.
AUTHOR="$RECORD_AUTHOR"
if [ -z "$AUTHOR" ]; then
  AUTHOR="$(gh api user --jq .login)" \
    || die 15 "could not resolve the expected author: gh api user --jq .login failed"
fi
[ -n "$AUTHOR" ] \
  || die 15 "no expected author: review.record_author is unset and gh api user --jq .login returned nothing"

die 1 "reviews read is not implemented yet"
