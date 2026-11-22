#!/usr/bin/env bash
# Run the cheap checks CI runs before pushing: the two doc lints, the vendored-copy check, and
# the focused test module each changed path maps to. This is a manual pre-push step; it installs
# no git hook and adds no flag to the pre-PR preflight.
#
#   bash scripts/pre-push-check.sh [--base REF] [--list]
#
# A passing run covers the exact HEAD being pushed: the checks run in a throwaway worktree at that
# HEAD, so neither staged content nor a mid-run edit in the working tree can change the result, and
# the run fails when HEAD moves. Re-run it whenever HEAD changes.
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
  '.agent-skills/review-checklist.txt tests/test_review_checklist.py'
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
  'scripts/vendor_shared.py tests/test_resolve_model_role.py'
  'shared/check-signing-key.sh tests/test_signing_key.py'
  'shared/github.md tests/test_shared_github.py'
  'shared/linear.md tests/test_shared_linear.py'
  'shared/resolve-full-suite.py tests/test_full_suite_switch.py'
  'shared/resolve-model-role.py tests/test_resolve_model_role.py'
  'shared/select-path.py tests/test_select_path.py'
  'shared/todo-enforce.py tests/test_todo_enforce.py'
  'skills.json tests/test_skills.py'
  'skills/engineering-workflow/SKILL.md tests/test_no_deployment_path.py'
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
  The checks run in a throwaway worktree at HEAD, so only committed content is judged and
  staged, unstaged or untracked files in the caller's checkout cannot change the result.
  The doc lint still scans every eligible file in that HEAD tree, not only the change set, so
  a stray checked-out file that HEAD already carries can fail it.

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
  that is absent from HEAD is a named startup error, as are a missing doc lint module or
  vendoring script.
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
Requires bash 4.4 or newer, git, uv, and the GNU date and sort that +%s%N and -z need;
another runtime is one named error with exit 2.

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

root=$(cd -P -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd) || die "cannot find the repository root"
cd -P -- "$root" || die "cannot enter $root"
# An inherited pytest option must not turn a run into collection only.
unset PYTEST_ADDOPTS

git rev-parse --git-dir > /dev/null 2>&1 || die "not in a git repository"
toplevel=$(git rev-parse --show-toplevel) || die "not in a git work tree"
[ "$toplevel" = "$root" ] ||
  die "the git work tree is $toplevel, not this checkout $root (check GIT_DIR and GIT_WORK_TREE)"
git rev-parse --verify --quiet --end-of-options "$base^{commit}" > /dev/null 2>&1 ||
  die "unresolvable base ref $base"
head_sha=$(git rev-parse --verify HEAD) || die "HEAD is unresolvable"
git merge-base "$base" "$head_sha" > /dev/null 2>&1 ||
  die "no merge base between $base and HEAD $head_sha"
unstaged=$(git -c core.quotePath=false diff --name-only) || die "git diff --name-only failed"
[ -z "$unstaged" ] ||
  die "unstaged modifications to tracked files (stage or revert them first): $(printf '%s' "$unstaged" | tr '\n' ' ')"
git diff --cached --quiet
staged_status=$?
case $staged_status in
  0 | 1) ;;
  *) die "git diff --cached --quiet failed" ;;
esac
hidden=$(git -c core.quotePath=false ls-files -v) || die "git ls-files -v failed"
hidden_paths=$(printf '%s\n' "$hidden" | sed -n '/^[a-zS] /s/^..//p')
[ -z "$hidden_paths" ] ||
  die "assume-unchanged or skip-worktree entries hide working-tree state (clear them first): $(printf '%s' "$hidden_paths" | tr '\n' ' ')"

work=$(mktemp -d) || die "could not create a temporary directory"
snapshot=$work/head
cleanup() {
  git worktree remove --force -- "$snapshot" > /dev/null 2>&1
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

: > "$work/modules"
unmapped=()
while IFS= read -r -d '' path; do
  if module=$(module_for "$path"); then
    printf '%s\0' "$module" >> "$work/modules"
  else
    unmapped+=("$path")
  fi
done < "$work/changes"
if [ ${#unmapped[@]} -gt 0 ]; then
  printf '%s\0' "$fallback" >> "$work/modules"
fi
sort -z -u "$work/modules" -o "$work/modulelist" || die "could not sort the selected modules"
module_count=$(tr -cd '\0' < "$work/modulelist" | wc -c | tr -d ' ')

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
  [ "$staged_status" -eq 1 ] &&
    printf 'note: the index differs from HEAD %s; a run checks a clean snapshot of HEAD\n' "$head_sha"
  printf 'selected modules:\n'
  if [ "$module_count" = 0 ]; then
    printf '  none\n'
  else
    while IFS= read -r -d '' module; do
      printf '  %s\n' "$module"
    done < "$work/modulelist"
    while IFS= read -r -d '' module; do
      git cat-file -e "$head_sha:$module" 2> /dev/null ||
        printf 'focused: module %s is not present in HEAD %s; a run refuses\n' "$module" "$head_sha"
    done < "$work/modulelist"
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

run_start=$(date +%s%N) || die "date +%s%N failed"
case $run_start in
  '' | *[!0-9]*) die "GNU date with +%s%N is required for elapsed seconds" ;;
esac

# Every check runs in a throwaway worktree at the captured HEAD, so the result covers that commit
# and nothing that is staged, unstaged, untracked or edited in the caller's checkout mid-run.
git -c core.hooksPath=/dev/null worktree add --detach --quiet "$snapshot" "$head_sha" ||
  die "could not create a clean snapshot worktree of HEAD $head_sha"
[ "$staged_status" -eq 1 ] &&
  printf 'note: the index differs from HEAD %s; the checks run against a clean snapshot of HEAD\n' "$head_sha"

pytest_ready=$(cd -- "$snapshot" && uv run --locked pytest --version 2>&1) ||
  die "cannot start the pytest checks: ${pytest_ready:-uv run --locked pytest failed}"
[ -f "$snapshot/tests/test_skills.py" ] ||
  die "cannot start the doc lint checks: tests/test_skills.py is not in HEAD $head_sha"
[ -f "$snapshot/scripts/vendor_shared.py" ] ||
  die "cannot start the vendor check: scripts/vendor_shared.py is not in HEAD $head_sha"

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
elapsed_s=0

elapsed() {
  local now
  now=$(date +%s%N) || die "date +%s%N failed during the run"
  case $now in
    '' | *[!0-9]*) die "date +%s%N stopped returning a timestamp during the run" ;;
  esac
  local ns=$((now - $1))
  printf -v elapsed_s '%d.%01d' $((ns / 1000000000)) $(((ns % 1000000000) / 100000000))
}

run_check() {
  local label=$1
  shift
  local start out code
  start=$(date +%s%N) || die "date +%s%N failed during the run"
  out=$(cd -- "$snapshot" && "$@" 2>&1)
  code=$?
  case $out in
    *"Failed to spawn:"*) die "cannot start $label: $out" ;;
  esac
  if [ "$code" -eq 127 ]; then
    die "cannot start $label: ${out:-exit 127}"
  fi
  checked=$((checked + 1))
  elapsed "$start"
  if [ "$code" -eq 0 ]; then
    printf 'ok %s (%ss)\n' "$label" "$elapsed_s"
    return
  fi
  failed=$((failed + 1))
  printf 'FAIL %s (%ss)\n' "$label" "$elapsed_s"
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
if [ "$module_count" -gt 0 ]; then
  while IFS= read -r -d '' module; do
    git cat-file -e "$head_sha:$module" 2> /dev/null ||
      die "cannot start $module: it is not present in HEAD $head_sha"
    run_check "$module" uv run --locked pytest -q "$module"
  done < "$work/modulelist"
fi

current=$(git rev-parse --verify HEAD) || die "HEAD became unresolvable during the run"
[ "$current" = "$head_sha" ] ||
  die "HEAD moved from $head_sha to $current during the run; re-run the check for the new HEAD"

elapsed "$run_start"
printf 'total: %d checks, %d failed, %ss (HEAD %s)\n' "$checked" "$failed" "$elapsed_s" "$head_sha"
[ "$failed" -eq 0 ] || exit 1
exit 0
