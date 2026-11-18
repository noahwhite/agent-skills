#!/usr/bin/env bash
# Run one scenario, or both, of the owner-wait-verified case and grade it.
#
#   run.sh CHECKOUT SCENARIO RUN_DIR
#
# CHECKOUT is the repository checkout holding the skill to test, SCENARIO one of rescoped-brief,
# owner-value or both, and RUN_DIR the empty directory this run writes to, which must sit outside
# CHECKOUT. `both` runs each scenario in turn, in RUN_DIR/rescoped-brief and RUN_DIR/owner-value,
# and exits with the worst of their codes. EVAL_AGENT_CMD overrides the agent command and is split
# on whitespace, so it carries no quoted argument; run.sh appends `--file RUN_DIR/workspace/prompt.md`
# to it, so the prompt is attached as a file and never put in argv, and the command must accept
# that argument. EVAL_TIMEOUT bounds the agent command in seconds, a positive whole number.
#
# The agent works in RUN_DIR/workspace: the scenario, its checklist file, QA round 1's launch
# record, the stub tracker and role-runtime, and the message files the agent writes. The call
# record and the message store the stubs keep sit in RUN_DIR itself, and the fixture stories the
# tracker serves stay in the case's scenario directory, so the agent reads a story only through
# the tracker.
#
# Exit codes: 0 the run was graded and passed, 1 the run was graded and failed, 2 the run itself
# is void (bad arguments, a run directory already in use, an agent command that failed or timed
# out, a checkout the agent changed, a record the grader cannot grade, or a judge that gave no
# verdict), and in that case
# nothing is graded.
set -euo pipefail

case_dir="$(cd "$(dirname "$0")" && pwd)"
if [ "$#" -ne 3 ]; then
  echo "usage: run.sh CHECKOUT SCENARIO RUN_DIR" >&2
  exit 2
fi
scenario="$2"
timeout_seconds="${EVAL_TIMEOUT:-900}"
case "$timeout_seconds" in
  ''|*[!0-9]*|0) echo "run.sh: EVAL_TIMEOUT must be a positive whole number of seconds" >&2; exit 2 ;;
esac

test -d "$1" || { echo "run.sh: no checkout at $1" >&2; exit 2; }
git -C "$1" rev-parse --verify --quiet HEAD > /dev/null ||
  { echo "run.sh: $1 is not a git checkout with a commit" >&2; exit 2; }
checkout_real="$(realpath "$1")"
run="$(realpath -m "$3")"
case "$scenario" in
  rescoped-brief|owner-value|both) ;;
  *) echo "run.sh: unknown scenario $scenario" >&2; exit 2 ;;
esac
if [ -e "$run" ] && [ ! -d "$run" ]; then
  echo "run.sh: RUN_DIR $run is not a directory" >&2
  exit 2
fi
case "$run/" in
  "$checkout_real"/*) echo "run.sh: RUN_DIR must sit outside CHECKOUT" >&2; exit 2 ;;
esac
if [ -d "$run" ] && [ -n "$(ls -A "$run")" ]; then
  echo "run.sh: RUN_DIR $run is not empty; give each run its own directory" >&2
  exit 2
fi

# Both scenarios in one invocation: each runs as its own run, and the worst code is the run's.
if [ "$scenario" = both ]; then
  worst=0
  for each in rescoped-brief owner-value; do
    code=0
    bash "$case_dir/run.sh" "$checkout_real" "$each" "$run/$each" || code=$?
    case "$code" in
      0) ;;
      1) [ "$worst" -eq 2 ] || worst=1 ;;
      *) worst=2 ;;
    esac
  done
  exit "$worst"
fi

fixtures="$case_dir/scenarios/$scenario"
for needed in scenario.md qa-round-1.json checklists stories; do
  test -e "$fixtures/$needed" || { echo "run.sh: scenario $scenario has no $needed" >&2; exit 2; }
done

# The checkout's state outside its ignored paths, content included: status alone repeats for a
# file that was already modified and is modified again, and it says nothing about an untracked
# file's contents, so the fingerprint carries the diff against HEAD and a hash per untracked file.
state() {
  git -C "$1" rev-parse HEAD
  git -C "$1" diff HEAD
  git -C "$1" ls-files --others --exclude-standard -z |
    while IFS= read -r -d '' file; do
      printf '%s\0' "$file"
      entry="$1/$file"
      if [ -L "$entry" ]; then
        printf 'link %s\n' "$(readlink "$entry")"
        sha256sum < "$entry" 2>/dev/null || printf 'unreadable\n'
      elif [ -f "$entry" ]; then
        sha256sum < "$entry" 2>/dev/null || printf 'unreadable\n'
      else
        printf 'other\n'
      fi
    done
}
state_before="$(state "$checkout_real")"

workspace="$run/workspace"
mkdir -p "$workspace"
{
  # The tracker serves the scenario's stories from the case, never from the agent's directory.
  printf '%s\n' "$fixtures" > "$run/scenario-path" &&
  # A run that makes no call is graded on an empty record, never voided for want of one.
  touch "$run/actions.jsonl" &&
  cp "$fixtures/scenario.md" "$fixtures/qa-round-1.json" "$workspace/" &&
  cp "$case_dir/runtime/tracker" "$case_dir/runtime/tracker.md" "$workspace/" &&
  cp "$case_dir/runtime/role-runtime" "$case_dir/runtime/role-runtime.md" "$workspace/" &&
  chmod +x "$workspace/tracker" "$workspace/role-runtime" &&
  # The checklist file QA round 1 left, at the path its brief gives it.
  cp -R "$fixtures/checklists/." "$workspace/"
} || { echo "run.sh: cannot set up the run directory $run" >&2; exit 2; }
# The paths go into the prompt through sed, so escape what sed reads specially.
escape() { printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'; }
sed -e "s|{skill_dir}|$(escape "$checkout_real/skills/story-to-done")|g" \
    -e "s|{run_dir}|$(escape "$workspace")|g" \
    "$case_dir/prompt.md" > "$workspace/prompt.md"

agent=(opencode run --standalone --auto --archived --model deepseek/deepseek-v4-pro "Follow the instructions in the attached file exactly.")
if [ -n "${EVAL_AGENT_CMD:-}" ]; then
  read -r -a agent <<< "$EVAL_AGENT_CMD"
fi
status=0
(cd "$checkout_real" && timeout --kill-after=30 "$timeout_seconds" "${agent[@]}" --file "$workspace/prompt.md" > "$run/agent-output.txt" 2>&1) || status=$?
if [ "$status" -ne 0 ]; then
  echo "HARNESS: the agent command exited $status (124 or 137 means it hit EVAL_TIMEOUT); nothing was graded." >&2
  exit 2
fi
# The checkout under test must be exactly as it was: a new commit is as much a change as a
# dirty file, so the whole state taken before the agent ran is compared with the state after.
if [ "$(state "$checkout_real")" != "$state_before" ]; then
  echo "HARNESS: the agent changed $checkout_real; that run is void and nothing was graded." >&2
  git -C "$checkout_real" status --porcelain --untracked-files=all >&2
  exit 2
fi

# The grader's own exit code is the run's: written to the file first, so a failed write is a
# harness error, never a graded failure. The grader's judge is the agent command this run used,
# so the model that wrote the final message is the model that judges it. The agent ran from the
# checkout and the judge runs from an empty directory, so a relative path in the command is
# resolved against the checkout first: a word that is not absolute, has a "/", and names a file
# or directory there. A word such as the model id deepseek/deepseek-v4-pro names none and is kept.
judge=()
for word in "${agent[@]}"; do
  case "$word" in
    /*) judge+=("$word") ;;
    */*) if [ -e "$checkout_real/$word" ]; then judge+=("$checkout_real/$word"); else judge+=("$word"); fi ;;
    *) judge+=("$word") ;;
  esac
done
: > "$run/grader-output.txt" 2>/dev/null || { echo "HARNESS: cannot write $run/grader-output.txt" >&2; exit 2; }
graded=0
python3 "$case_dir/grader.py" --run-dir "$run" --expectation "$scenario" --judge "${judge[@]}" > "$run/grader-output.txt" || graded=$?
cat "$run/grader-output.txt"
exit "$graded"
