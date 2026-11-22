#!/usr/bin/env bash
# Run the cheap checks CI runs before pushing: the two doc lints, the vendored-copy check, and
# the focused test module each changed path maps to. This is a manual pre-push step; it installs
# no git hook and adds no flag to the pre-PR preflight.
#
#   bash scripts/pre-push-check.sh [--base REF] [--list]
#
# A passing run covers the exact HEAD being pushed: re-run it whenever HEAD changes.
# Exit status: 0 every check passed, 1 at least one check failed, 2 an input, git or startup error.
set -uo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd) || exit 2
cd -- "$root" || exit 2

base=origin/main
list=false
fallback=tests/test_skills.py

# The path-to-module table: at most one test module per path, matched exactly. A path with no row
# here is unmapped and runs the fallback module. It is also printed by --help.
table=(
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
  'tests/test_cleanup.py tests/test_cleanup.py'
  'tests/test_delegated_briefs.py tests/test_delegated_briefs.py'
  'tests/test_eval_suite.py tests/test_eval_suite.py'
  'tests/test_full_suite_mutations.py tests/test_full_suite_mutations.py'
  'tests/test_full_suite_switch.py tests/test_full_suite_switch.py'
  'tests/test_gate_integrity.py tests/test_gate_integrity.py'
  'tests/test_git_identity_rule.py tests/test_git_identity_rule.py'
  'tests/test_leak_scan.py tests/test_leak_scan.py'
  'tests/test_linear_filing_skills.py tests/test_linear_filing_skills.py'
  'tests/test_memory_retirement.py tests/test_memory_retirement.py'
  'tests/test_memory_rules_in_skills.py tests/test_memory_rules_in_skills.py'
  'tests/test_merge_approval.py tests/test_merge_approval.py'
  'tests/test_merge_guard.py tests/test_merge_guard.py'
  'tests/test_metrics.py tests/test_metrics.py'
  'tests/test_no_deployment_path.py tests/test_no_deployment_path.py'
  'tests/test_one_green_signal.py tests/test_one_green_signal.py'
  'tests/test_one_pass_evidence.py tests/test_one_pass_evidence.py'
  'tests/test_opencode_session_usage.py tests/test_opencode_session_usage.py'
  'tests/test_opencode_v2_guidance.py tests/test_opencode_v2_guidance.py'
  'tests/test_pending_ruling_case.py tests/test_pending_ruling_case.py'
  'tests/test_persona_architect.py tests/test_persona_architect.py'
  'tests/test_persona_release_manager.py tests/test_persona_release_manager.py'
  'tests/test_persona_scrum_master.py tests/test_persona_scrum_master.py'
  'tests/test_pipeline_arbiter_identity.py tests/test_pipeline_arbiter_identity.py'
  'tests/test_pipeline_diff_cap.py tests/test_pipeline_diff_cap.py'
  'tests/test_pipeline_dossier_checkout.py tests/test_pipeline_dossier_checkout.py'
  'tests/test_pipeline_dossier_fixture.py tests/test_pipeline_dossier_fixture.py'
  'tests/test_pipeline_dossier_sidecars.py tests/test_pipeline_dossier_sidecars.py'
  'tests/test_pipeline_dossier_sizes.py tests/test_pipeline_dossier_sizes.py'
  'tests/test_pipeline_exclusion.py tests/test_pipeline_exclusion.py'
  'tests/test_pipeline_failfast.py tests/test_pipeline_failfast.py'
  'tests/test_pipeline_scratch.py tests/test_pipeline_scratch.py'
  'tests/test_pr_status.py tests/test_pr_status.py'
  'tests/test_pre_push_check.py tests/test_pre_push_check.py'
  'tests/test_profiles.py tests/test_profiles.py'
  'tests/test_prune_candidates.py tests/test_prune_candidates.py'
  'tests/test_qa_await_gate.py tests/test_qa_await_gate.py'
  'tests/test_qa_pending_owner_ruling.py tests/test_qa_pending_owner_ruling.py'
  'tests/test_qa_round_cap.py tests/test_qa_round_cap.py'
  'tests/test_read_source_rule.py tests/test_read_source_rule.py'
  'tests/test_record_author.py tests/test_record_author.py'
  'tests/test_render_brief.py tests/test_render_brief.py'
  'tests/test_resolve_model_role.py tests/test_resolve_model_role.py'
  'tests/test_review_checklist.py tests/test_review_checklist.py'
  'tests/test_scope_ownership_rule.py tests/test_scope_ownership_rule.py'
  'tests/test_scratch_directory.py tests/test_scratch_directory.py'
  'tests/test_seat_enabled.py tests/test_seat_enabled.py'
  'tests/test_select_path.py tests/test_select_path.py'
  'tests/test_shared_github.py tests/test_shared_github.py'
  'tests/test_shared_linear.py tests/test_shared_linear.py'
  'tests/test_shell_command_rule.py tests/test_shell_command_rule.py'
  'tests/test_signing_key.py tests/test_signing_key.py'
  'tests/test_skills.py tests/test_skills.py'
  'tests/test_smoke_opencode.py tests/test_smoke_opencode.py'
  'tests/test_story_refinement.py tests/test_story_refinement.py'
  'tests/test_story_to_done.py tests/test_story_to_done.py'
  'tests/test_todo_enforce.py tests/test_todo_enforce.py'
  'tests/test_todo_tracking.py tests/test_todo_tracking.py'
)

usage() {
  cat <<'EOF'
Usage: bash scripts/pre-push-check.sh [--base REF] [--list]

Run the cheap checks CI runs against the change set of the HEAD you are about to push:
the em-dash doc lint, the clean-and-neutral phrase doc lint, the vendored-copy check, and
the focused test module for each changed path. Run it first with --list to see the selection.

Change set:
  the union of the staged paths (git diff --cached --name-only) and the committed branch diff
  (git diff --name-only <merge-base>...HEAD), sorted and de-duplicated.
  The base ref defaults to origin/main and --base REF overrides it. On the first push of a
  new topic branch the remote branch does not exist yet, and origin/main is still the base:
  the committed half is origin/main...HEAD.
  Unstaged modifications to tracked files are refused by name, so the set is deterministic.
  Untracked files are not in the change set.
  An empty change set is reported explicitly, and the doc and vendor checks still run.
  Stray files in the checkout can affect the doc lint, because it scans the working tree, so
  run the check in a clean checkout when its result matters.

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

  every other path is unmapped: it prints "focused: no module for <path>" and runs the
  fallback module $fallback.

Flags:
  --base REF   base ref for the committed diff (default origin/main)
  --list       print the change set, the selected modules, the fallback and each unmapped
               path, and run nothing
  --help       print this text

Output: one line per check with its label and its elapsed seconds, one FAIL line per failed
check with its command and its output, and a total line.
Exit status: 0 every check passed, 1 at least one check failed, 2 an error (an unresolvable
base ref, invalid input, or a check that cannot start).

A passing run is required for the exact HEAD being pushed: re-run it whenever HEAD changes.
EOF
}

die() {
  printf 'pre-push-check: error: %s\n' "$1" >&2
  exit 2
}

module_for() {
  local path=$1 entry
  for entry in "${table[@]}"; do
    if [ "${entry%% *}" = "$path" ]; then
      printf '%s\n' "${entry#* }"
      return 0
    fi
  done
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
if [ -n "$(git diff --name-only)" ]; then
  die "unstaged modifications to tracked files (stage or revert them first): $(git diff --name-only | tr '\n' ' ')"
fi

staged=$(git diff --cached --name-only) || die "git diff --cached --name-only failed"
committed=$(git diff --name-only "$base...HEAD") || die "unresolvable base ref $base"

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
  out=$("$@" 2>&1)
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

check() {
  run_check "$@"
}

check 'tests/test_skills.py::test_no_em_dash' uv run --locked pytest -q tests/test_skills.py::test_no_em_dash
check 'tests/test_skills.py::test_clean_and_neutral_use_the_canonical_phrase' \
  uv run --locked pytest -q tests/test_skills.py::test_clean_and_neutral_use_the_canonical_phrase
check 'vendor: scripts/vendor_shared.py --check' python3 scripts/vendor_shared.py --check
if [ -n "$modules" ]; then
  while IFS= read -r module; do
    check "$module" uv run --locked pytest -q "$module"
  done <<< "$modules"
fi

printf 'total: %d checks, %d failed, %ss\n' "$checked" "$failed" "$(elapsed "$run_start")"
[ "$failed" -eq 0 ] || exit 1
exit 0
