#!/usr/bin/env bash
# Run the cheap checks CI runs before pushing: the two doc lints, the vendored-copy check, and
# the focused test module each changed path maps to. This is a manual pre-push step; it installs
# no git hook and adds no flag to the pre-PR preflight.
#
#   bash scripts/pre-push-check.sh [--base REF] [--list]
#
# A passing run certifies the exact HEAD being pushed: when the index differs from HEAD the checks
# run against a clean snapshot of HEAD, and HEAD is re-checked whenever it changes.
# Exit status: 0 every check passed, 1 at least one check failed, 2 an input, git or startup error.
set -uo pipefail

die() {
  printf 'pre-push-check: error: %s\n' "$1" >&2
  exit 2
}

# The elapsed-time arithmetic needs GNU date, and the empty-array expansion needs bash 4.4.
if [ "${BASH_VERSINFO[0]}" -lt 4 ] ||
  { [ "${BASH_VERSINFO[0]}" -eq 4 ] && [ "${BASH_VERSINFO[1]}" -lt 4 ]; }; then
  die "bash 4.4 or newer is required (found $BASH_VERSION)"
fi
stamp=$(date +%s%N) || die "date +%s%N failed"
case $stamp in
  '' | *[!0-9]*) die "GNU date with +%s%N is required for elapsed seconds" ;;
esac

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd) || exit 2
cd -- "$root" || exit 2

base=origin/main
list=false
fallback=tests/test_skills.py

# The path-to-module table: at most one test module per path, matched exactly. A path with no row
# is unmapped and runs the fallback module, except that a tests/test_*.py path maps to itself.
# It is also printed by --help.
table=(
  '.agent-skills/profile.yaml tests/test_profiles.py'
  '.github/workflows/ci.yml tests/test_gate_integrity.py'
  '.github/workflows/gate-base.yml tests/test_gate_integrity.py'
  'profile/example.yaml tests/test_profiles.py'
  'profile/schema.json tests/test_profiles.py'
  'scripts/eval_suite.py tests/test_eval_suite.py'
  'scripts/gate_integrity.py tests/test_gate_integrity.py'
  'scripts/leak-patterns.txt tests/test_leak_scan.py'
  'scripts/leak_scan.py tests/test_leak_scan.py'
  'scripts/pre-push-check.sh tests/test_pre_push_check.py'
  'scripts/prune_candidates.py tests/test_prune_candidates.py'
  'scripts/run-suite.sh tests/test_eval_suite.py'
  'scripts/smoke-opencode.sh tests/test_smoke_opencode.py'
  'scripts/smoke_opencode.py tests/test_smoke_opencode.py'
  'scripts/vendor_shared.py tests/test_skills.py'
  'shared/check-signing-key.sh tests/test_signing_key.py'
  'shared/github.md tests/test_shared_github.py'
  'shared/linear.md tests/test_shared_linear.py'
  'shared/resolve-full-suite.py tests/test_full_suite_switch.py'
  'shared/resolve-model-role.py tests/test_resolve_model_role.py'
  'shared/select-path.py tests/test_select_path.py'
  'shared/todo-enforce.py tests/test_todo_enforce.py'
  'skills.json tests/test_skills.py'
  'skills/engineering-workflow/scripts/pr-status.sh tests/test_pr_status.py'
  'skills/engineering-workflow/scripts/select-path.py tests/test_select_path.py'
  'skills/qa-verification/scripts/select-path.py tests/test_select_path.py'
  'skills/story-refinement/scripts/todo-enforce.py tests/test_todo_enforce.py'
  'skills/story-to-done/scripts/qa-round-cap.py tests/test_qa_round_cap.py'
  'skills/story-to-done/scripts/render-brief.py tests/test_render_brief.py'
  'skills/story-to-done/scripts/select-path.py tests/test_select_path.py'
  'skills/story-to-done/scripts/todo-enforce.py tests/test_todo_enforce.py'
)

usage() {
  cat <<'EOF'
Usage: bash scripts/pre-push-check.sh [--base REF] [--list]

Run the cheap checks CI runs against the change set of the HEAD you are about to push:
the em-dash doc lint, the clean-and-neutral phrase doc lint, the vendored-copy check, and
the focused test module for each changed path. Run it first with --list to see the selection.

Change set:
  the union of the staged paths (git diff --cached --name-only) and the committed branch diff
  (git diff --name-only <merge-base>...HEAD), sorted and de-duplicated. Rename detection is
  off, so a rename is reported as a deletion plus an addition and both paths are selected.
  The base ref defaults to origin/main and --base REF overrides it. On the first push of a
  new topic branch the remote branch does not exist yet, and origin/main is still the base:
  the committed half is origin/main...HEAD.
  Unstaged modifications to tracked files are refused by name, so the set is deterministic,
  and so are assume-unchanged and skip-worktree entries, which would hide one.
  Untracked files are not in the change set.
  An empty change set is reported explicitly, and the doc and vendor checks still run.
  Stray files in the checkout can affect the doc lint, because it reads the working tree, so
  run the check in a clean checkout when its result matters. When the index differs from HEAD
  the checks run against a clean snapshot of HEAD instead, so a pass always covers HEAD.

Checks, in order, each continuing past a failure:
  tests/test_skills.py::test_no_em_dash
  tests/test_skills.py::test_clean_and_neutral_use_the_canonical_phrase
  python3 scripts/vendor_shared.py --check
  each selected module

Path to test module:
  a path from this table runs its module:

EOF
  for entry in "${table[@]}"; do
    printf '    %s -> %s\n' "${entry%% *}" "${entry#* }"
  done
  cat <<EOF

  a changed tests/test_*.py path maps to itself; every other path is unmapped: it prints
  "focused: no module for <path>" and runs the fallback module $fallback. A selected module
  that is absent from the revision under test is named and skipped.
EOF
  cat <<'EOF'

Flags:
  --base REF   base ref for the committed diff (default origin/main)
  --list       print the change set, the selected modules, the fallback and each unmapped
               path, and run nothing
  --help       print this text

Output: one line per check with its label and its elapsed seconds, one FAIL line per failed
check with its command and its output, and a total line.
Exit status: 0 every check passed, 1 at least one check failed, 2 an error (an unresolvable
base ref, invalid input, or a check that cannot start).
Requires bash 4.4 or newer and GNU date; another runtime is one named error with exit 2.

A passing run is required for the exact HEAD being pushed: re-run it whenever HEAD changes.
EOF
}

module_for() {
  local path=$1 entry
  for entry in "${table[@]}"; do
    if [ "${entry%% *}" = "$path" ]; then
      printf '%s\n' "${entry#* }"
      return 0
    fi
  done
  case $path in
    tests/test_*.py)
      printf '%s\n' "$path"
      return 0
      ;;
  esac
  return 1
}

while [ $# -gt 0 ]; do
  case $1 in
    --help | -h)
      usage
      exit 0
      ;;
    --list)
      list=true
      shift
      ;;
    --base)
      [ $# -ge 2 ] || die "--base needs a ref"
      base=$2
      shift 2
      ;;
    --base=*)
      base=${1#--base=}
      [ -n "$base" ] || die "--base needs a ref"
      shift
      ;;
    -*)
      die "unknown option $1"
      ;;
    *)
      die "unexpected argument $1"
      ;;
  esac
done

git rev-parse --git-dir > /dev/null 2>&1 || die "not in a git repository"
git rev-parse --verify --quiet --end-of-options "$base^{commit}" > /dev/null 2>&1 ||
  die "unresolvable base ref $base"
head_sha=$(git rev-parse --verify HEAD) || die "HEAD is unresolvable"
unstaged=$(git diff --name-only) || die "git diff --name-only failed"
[ -z "$unstaged" ] ||
  die "unstaged modifications to tracked files (stage or revert them first): $(printf '%s' "$unstaged" | tr '\n' ' ')"
hidden=$(git ls-files -v) || die "git ls-files -v failed"
hidden_paths=$(printf '%s\n' "$hidden" | sed -n '/^[a-zS] /s/^..//p')
[ -z "$hidden_paths" ] ||
  die "assume-unchanged or skip-worktree entries hide working-tree state (clear them first): $(printf '%s' "$hidden_paths" | tr '\n' ' ')"

staged=$(git diff --cached --name-only --no-renames) || die "git diff --cached --name-only failed"
committed=$(git diff --name-only --no-renames "$base...HEAD") || die "unresolvable base ref $base"
changes=$(printf '%s\n%s\n' "$staged" "$committed" | sed '/^$/d' | sort -u)

modules=()
unmapped=()
while IFS= read -r path; do
  [ -n "$path" ] || continue
  if module=$(module_for "$path"); then
    modules+=("$module")
  else
    unmapped+=("$path")
  fi
done <<< "$changes"

modules=$(printf '%s\n' "${modules[@]}" | sed '/^$/d' | sort -u)
if [ ${#unmapped[@]} -gt 0 ]; then
  modules=$(printf '%s\n%s\n' "$modules" "$fallback" | sed '/^$/d' | sort -u)
fi

if $list; then
  if [ -z "$changes" ]; then
    printf 'change set: empty\n'
  else
    printf 'change set:\n'
    while IFS= read -r path; do
      printf '  %s\n' "$path"
    done <<< "$changes"
  fi
  printf 'selected modules:\n'
  if [ -z "$modules" ]; then
    printf '  none\n'
  else
    while IFS= read -r module; do
      printf '  %s\n' "$module"
    done <<< "$modules"
  fi
  if [ ${#unmapped[@]} -gt 0 ]; then
    printf 'fallback: %s\n' "$fallback"
    for path in "${unmapped[@]}"; do
      printf 'focused: no module for %s\n' "$path"
    done
  else
    printf 'fallback: none\n'
  fi
  exit 0
fi

# The checks read the tree they run in, so a staged change would let a passing run cover content
# that is not HEAD. With a staged change they run in a clean snapshot of HEAD instead.
check_in=.
snapshot=
cleanup() {
  if [ -n "$snapshot" ]; then
    git worktree remove --force -- "$snapshot/head" > /dev/null 2>&1
    rm -rf -- "$snapshot"
  fi
}
trap cleanup EXIT
trap 'exit 130' INT TERM HUP
git diff --cached --quiet
staged_status=$?
case $staged_status in
  0) ;;
  1)
    snapshot=$(mktemp -d) || die "could not create a snapshot directory"
    git worktree add --detach --quiet "$snapshot/head" HEAD ||
      die "could not create a clean snapshot worktree of HEAD $head_sha"
    check_in=$snapshot/head
    printf 'note: the index differs from HEAD %s; the checks run against a clean snapshot of HEAD\n' "$head_sha"
    ;;
  *) die "git diff --cached --quiet failed" ;;
esac

pytest_ready=$(cd -- "$check_in" && uv run --locked pytest --version 2>&1) ||
  die "cannot start the pytest checks: ${pytest_ready:-uv run --locked pytest failed}"
command -v python3 > /dev/null 2>&1 || die "cannot start the vendor check: python3 is not on PATH"

if [ -z "$changes" ]; then
  printf 'change set: empty\n'
else
  printf 'change set: %s path(s)\n' "$(printf '%s\n' "$changes" | wc -l | tr -d ' ')"
  while IFS= read -r path; do
    printf '  %s\n' "$path"
  done <<< "$changes"
fi
for path in "${unmapped[@]}"; do
  printf 'focused: no module for %s\n' "$path"
done

checked=0
failed=0
run_start=$(date +%s%N)

elapsed() {
  local ns=$(($(date +%s%N) - $1))
  printf '%d.%01d' $((ns / 1000000000)) $(((ns % 1000000000) / 100000000))
}

run_check() {
  local label=$1
  shift
  local start out code
  start=$(date +%s%N)
  out=$(cd -- "$check_in" && "$@" 2>&1)
  code=$?
  checked=$((checked + 1))
  if [ "$code" -eq 126 ] || [ "$code" -eq 127 ]; then
    die "cannot start $label: ${out:-exit $code}"
  fi
  if [ "$code" -eq 0 ]; then
    printf 'ok %s (%ss)\n' "$label" "$(elapsed "$start")"
    return
  fi
  failed=$((failed + 1))
  printf 'FAIL %s (%ss)\n' "$label" "$(elapsed "$start")"
  printf '  command: %s\n' "$*"
  if [ -n "$out" ]; then
    printf '%s\n' "$out" | sed 's/^/  /'
  fi
}

run_check 'tests/test_skills.py::test_no_em_dash' uv run --locked pytest -q tests/test_skills.py::test_no_em_dash
run_check 'tests/test_skills.py::test_clean_and_neutral_use_the_canonical_phrase' \
  uv run --locked pytest -q tests/test_skills.py::test_clean_and_neutral_use_the_canonical_phrase
run_check 'vendor: scripts/vendor_shared.py --check' python3 scripts/vendor_shared.py --check
if [ -n "$modules" ]; then
  while IFS= read -r module; do
    if [ ! -f "$check_in/$module" ]; then
      printf 'focused: module %s is not present in the revision under test; skipped\n' "$module"
      continue
    fi
    run_check "$module" uv run --locked pytest -q "$module"
  done <<< "$modules"
fi

printf 'total: %d checks, %d failed, %ss\n' "$checked" "$failed" "$(elapsed "$run_start")"
[ "$failed" -eq 0 ] || exit 1
exit 0
