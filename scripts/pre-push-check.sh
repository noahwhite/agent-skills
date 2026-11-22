#!/usr/bin/env bash
# Run the cheap checks CI runs before pushing: the two doc lints, the vendored-copy check, and
# the focused test module each changed path maps to. This is a manual pre-push step; it installs
# no git hook and adds no flag to the pre-PR preflight.
#
#   bash scripts/pre-push-check.sh [--base REF] [--list]
#
# A passing run covers the tracked content of the exact HEAD being pushed: the run prints that
# HEAD, refuses to pass when HEAD moved during the run, and checks a clean snapshot of HEAD when
# the index differs from it. Re-run it whenever HEAD changes.
# Exit status: 0 every check passed, 1 at least one check failed, 2 an input, git or startup error.
set -uo pipefail

die() {
  printf 'pre-push-check: error: %s\n' "$1" >&2
  exit 2
}

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
  (git diff --name-only <merge-base>...HEAD), read as NUL-delimited raw paths, sorted and
  de-duplicated. Rename detection is off, so a rename is reported as a deletion plus an
  addition and both paths are selected.
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
  uv run --locked python scripts/vendor_shared.py --check
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
  that is absent from the revision under test is named and skipped, but the two doc lints and
  the vendored-copy check are required, so the run is a named startup error without them.
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
base ref, invalid input, a check that cannot start, or HEAD moving during the run).
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
# An inherited pytest option must not turn a run into collection only.
unset PYTEST_ADDOPTS

git rev-parse --git-dir > /dev/null 2>&1 || die "not in a git repository"
git rev-parse --verify --quiet --end-of-options "$base^{commit}" > /dev/null 2>&1 ||
  die "unresolvable base ref $base"
head_sha=$(git rev-parse --verify HEAD) || die "HEAD is unresolvable"
git merge-base "$base" "$head_sha" > /dev/null 2>&1 ||
  die "no merge base between $base and HEAD $head_sha"
unstaged=$(git diff --name-only) || die "git diff --name-only failed"
[ -z "$unstaged" ] ||
  die "unstaged modifications to tracked files (stage or revert them first): $(printf '%s' "$unstaged" | tr '\n' ' ')"
hidden=$(git ls-files -v) || die "git ls-files -v failed"
hidden_paths=$(printf '%s\n' "$hidden" | sed -n '/^[a-zS] /s/^..//p')
[ -z "$hidden_paths" ] ||
  die "assume-unchanged or skip-worktree entries hide working-tree state (clear them first): $(printf '%s' "$hidden_paths" | tr '\n' ' ')"

work=$(mktemp -d) || die "could not create a temporary directory"
snapshot=
cleanup() {
  if [ -n "$snapshot" ]; then
    git worktree remove --force -- "$snapshot" > /dev/null 2>&1
  fi
  rm -rf -- "$work"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

git diff --cached --name-only -z --no-renames > "$work/staged" ||
  die "git diff --cached --name-only failed"
git diff --name-only -z --no-renames "$base...$head_sha" > "$work/committed" ||
  die "git diff --name-only $base...HEAD failed"
cat -- "$work/staged" "$work/committed" | sort -z -u > "$work/changes" ||
  die "could not sort the change set"
path_count=$(tr -cd '\0' < "$work/changes" | wc -c | tr -d ' ')

modules=()
unmapped=()
while IFS= read -r -d '' path; do
  if module=$(module_for "$path"); then
    modules+=("$module")
  else
    unmapped+=("$path")
  fi
done < "$work/changes"

modules=$(printf '%s\n' "${modules[@]}" | sed '/^$/d' | sort -u)
if [ ${#unmapped[@]} -gt 0 ]; then
  modules=$(printf '%s\n%s\n' "$modules" "$fallback" | sed '/^$/d' | sort -u)
fi

if $list; then
  printf 'HEAD: %s\n' "$head_sha"
  if [ "$path_count" = 0 ]; then
    printf 'change set: empty\n'
  else
    printf 'change set:\n'
    while IFS= read -r -d '' path; do
      printf '  %s\n' "$path"
    done < "$work/changes"
  fi
  git diff --cached --quiet
  [ $? -eq 1 ] &&
    printf 'note: the index differs from HEAD %s; a run would check a clean snapshot of HEAD\n' "$head_sha"
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

run_start=$(date +%s%N)

# The checks read the tree they run in, so a staged change would let a passing run cover content
# that is not HEAD. With a staged change they run in a clean snapshot of HEAD instead, reusing the
# checkout's environment when it has one so every staged run does not rebuild it.
check_in=.
git diff --cached --quiet
staged_status=$?
case $staged_status in
  0) ;;
  1)
    snapshot=$work/head
    git -c core.hooksPath=/dev/null worktree add --detach --quiet "$snapshot" "$head_sha" ||
      die "could not create a clean snapshot worktree of HEAD $head_sha"
    check_in=$snapshot
    if [ -d "$root/.venv" ]; then
      export UV_PROJECT_ENVIRONMENT="$root/.venv"
    fi
    printf 'note: the index differs from HEAD %s; the checks run against a clean snapshot of HEAD\n' "$head_sha"
    ;;
  *) die "git diff --cached --quiet failed" ;;
esac

pytest_ready=$(cd -- "$check_in" && uv run --locked pytest --version 2>&1) ||
  die "cannot start the pytest checks: ${pytest_ready:-uv run --locked pytest failed}"
[ -f "$check_in/tests/test_skills.py" ] ||
  die "cannot start the doc lint checks: tests/test_skills.py is not in the revision under test"
[ -f "$check_in/scripts/vendor_shared.py" ] ||
  die "cannot start the vendor check: scripts/vendor_shared.py is not in the revision under test"

printf 'HEAD: %s\n' "$head_sha"
if [ "$path_count" = 0 ]; then
  printf 'change set: empty\n'
else
  printf 'change set: %s path(s)\n' "$path_count"
  while IFS= read -r -d '' path; do
    printf '  %s\n' "$path"
  done < "$work/changes"
fi
for path in "${unmapped[@]}"; do
  printf 'focused: no module for %s\n' "$path"
done

checked=0
failed=0

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
run_check 'vendor: uv run --locked python scripts/vendor_shared.py --check' \
  uv run --locked python scripts/vendor_shared.py --check
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
current=$(git rev-parse --verify HEAD) || die "HEAD became unresolvable during the run"
[ "$current" = "$head_sha" ] ||
  die "HEAD moved from $head_sha to $current during the run; re-run the check for the new HEAD"
exit 0
