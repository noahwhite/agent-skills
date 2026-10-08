#!/usr/bin/env bash
# Read-only adversarial PR review by an optional reviewer, BATCHED by a diff-line budget.
#
# Generic launcher for an entry of profile.review.optional_reviewers: the caller builds the agent
# command from that entry. Each batch carries a compact cross-file BLUEPRINT (diffstat + signature
# changes) so cross-file awareness survives batching, while each request stays bounded in size, cost
# and latency.
#
# Run it by its installed path with the current directory inside the repository under review:
#   cd <consumer repo> && <skill dir>/scripts/batched-diff-review.sh --base REF --agent-cmd TEMPLATE
# The target repository is the current directory's, or --repo DIR; never the script's own location.
# The skills repository itself is refused unless --repo names it explicitly.
#
# Usage:
#   batched-diff-review.sh --base REF --agent-cmd TEMPLATE [--repo DIR] [--name LABEL]
#                          [--line-budget N] [--timeout SECONDS] [--context N]
#
# TEMPLATE is a shell command with {prompt_file} (the batch input) and optionally {output_file}
# (if absent, the command's stdout is the batch result). It runs in an empty scratch directory with
# the batch input on stdin, under a SIGKILL timeout. Read the prompt from stdin (for codex:
# `codex exec ... -`) or from {prompt_file}; never expand it into argv (argv is visible to other
# processes and one argument is capped at 128 KiB).
# Env equivalents: REVIEW_REPO, REVIEW_BASE, REVIEW_AGENT_CMD, REVIEW_NAME, REVIEW_LINE_BUDGET (800),
# REVIEW_TIMEOUT (240), REVIEW_CONTEXT (30).
#
# Report: $(git rev-parse --git-path batched-review)/<LABEL>/report.md, ending in a VERDICT of
# PASS, FAIL or INCOMPLETE. Each batch must return exactly one PASS or FAIL verdict for every file it
# was given; a missing, extra, duplicate or unparseable verdict makes the batch INCOMPLETE. INCOMPLETE
# (also rate limit, timeout, no output) means "skipped", never "clean".
set -euo pipefail

usage() { awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0" >&2; exit 2; }

REPO="${REVIEW_REPO:-}"
BASE="${REVIEW_BASE:-}"
AGENT_CMD="${REVIEW_AGENT_CMD:-}"
NAME="${REVIEW_NAME:-optional-reviewer}"
LINE_BUDGET="${REVIEW_LINE_BUDGET:-800}"
BATCH_TIMEOUT="${REVIEW_TIMEOUT:-240}"
CONTEXT_LINES="${REVIEW_CONTEXT:-30}"
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --base) BASE="$2"; shift 2 ;;
    --agent-cmd) AGENT_CMD="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --line-budget) LINE_BUDGET="$2"; shift 2 ;;
    --timeout) BATCH_TIMEOUT="$2"; shift 2 ;;
    --context) CONTEXT_LINES="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "ERROR: unknown option $1" >&2; usage ;;
  esac
done
[ -n "$BASE" ] || { echo "ERROR: --base is required (origin/<integration branch> after a fetch)." >&2; exit 2; }
[ -n "$AGENT_CMD" ] || { echo "ERROR: --agent-cmd is required (built from the optional reviewer's profile entry)." >&2; exit 2; }
[[ "$NAME" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "ERROR: --name must be [A-Za-z0-9._-]+" >&2; exit 2; }

# The target repository: --repo, else the current directory. Never this script's location.
if [ -n "$REPO" ]; then
  ROOT="$(git -C "$REPO" rev-parse --show-toplevel 2>/dev/null)" || { echo "ERROR: --repo '$REPO' is not inside a Git repository." >&2; exit 11; }
else
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "ERROR: not inside a Git repository (cd into the repository under review, or pass --repo)." >&2; exit 11; }
  if [ -f "$ROOT/skills.json" ] && [ -f "$ROOT/shared/runtimes.md" ]; then
    echo "ERROR: the current directory is the skills repository ($ROOT), not a repository under review; cd into the consumer repository, or pass --repo to review the skills repository itself." >&2
    exit 2
  fi
fi
cd "$ROOT"
git rev-parse --verify -q "$BASE" >/dev/null || { echo "ERROR: base ref '$BASE' does not exist." >&2; exit 12; }

mapfile -t FILES < <(git diff --name-only "$BASE"...HEAD)
[ ${#FILES[@]} -gt 0 ] || { echo "ERROR: no changed files between '$BASE' and HEAD." >&2; exit 13; }

OUTDIR="$(git rev-parse --git-path batched-review)/$NAME"
mkdir -p "$OUTDIR"
REPORT="$OUTDIR/report.md"
: > "$REPORT"

SANDBOX_DIR="$(mktemp -d)"
trap 'rm -rf "$SANDBOX_DIR"' EXIT

BLUEPRINT="$SANDBOX_DIR/blueprint.txt"
{
  echo "=== PR FILE MAP (git diff --stat vs ${BASE}) ==="
  git diff --stat "$BASE"...HEAD
  echo
  echo "=== EXPORTED / SIGNATURE CHANGES ACROSS THIS PR (added +/removed -) ==="
  git diff --no-ext-diff "$BASE"...HEAD \
    | awk '
        /^\+\+\+ b\// { file = substr($0, 7); next }
        /^[+-][^+-]/ {
          if ($0 ~ /(export|function|class|interface|type |const |def |public |private |func )/) print file ": " $0
        }' \
    | head -n 120
} > "$BLUEPRINT" 2>/dev/null || true
head -c 8000 "$BLUEPRINT" > "$BLUEPRINT.cap" && mv "$BLUEPRINT.cap" "$BLUEPRINT"

read -r -d '' PROMPT <<'EOF' || true
You are an independent senior engineer performing an adversarial pre-merge review of a BATCH of files from one PR.

You are given: (1) a PR BLUEPRINT - the whole PR's file map and exported/signature changes, for cross-file awareness only; (2) the diffs of ONE OR MORE files (each under "===== FILE: <path> ====="). Review every file in the batch.

CONSTRAINT: Do NOT use tools, run commands, search, or read files from disk other than this input. Reason only from the blueprint and the diffs shown. If a concern depends on code not shown, phrase it as a question, not an asserted defect. Never write secrets anywhere.

For each file, emit:
### FILE: <path>
then, for every substantive finding:
- Severity: Critical | High | Medium | Low
- Location: symbol/line
- Problem: concise, evidence-based (flag cross-file/contract concerns from the blueprint)
- Recommendation: concrete fix
- Confidence: High | Medium | Low
If a file's diff is clean, write "No substantive findings." End each file with exactly one line:
### FILE VERDICT: PASS
or
### FILE VERDICT: FAIL
(FAIL only for a substantive Critical or High finding in that file.)
EOF

run_batch() {  # $1 = input file -> model output on stdout
  local q_in q_out line
  q_in="$(printf '%q' "$1")"
  q_out="$(printf '%q' "$SANDBOX_DIR/out.txt")"
  line="${AGENT_CMD//\{prompt_file\}/$q_in}"
  rm -f "$SANDBOX_DIR/out.txt"
  if [[ "$AGENT_CMD" == *"{output_file}"* ]]; then
    line="${line//\{output_file\}/$q_out}"
    (cd "$SANDBOX_DIR/cwd" && timeout -s KILL "${BATCH_TIMEOUT}s" bash -c "$line" < "$1" > /dev/null 2> "$SANDBOX_DIR/stderr.txt")
    cat "$SANDBOX_DIR/out.txt" 2>/dev/null || true
  else
    (cd "$SANDBOX_DIR/cwd" && timeout -s KILL "${BATCH_TIMEOUT}s" bash -c "$line" < "$1" 2> "$SANDBOX_DIR/stderr.txt")
  fi
}

# Validates one batch's verdicts: $1 = model output file, $2 = file listing the requested paths.
# Prints "ok <fail count>" only when every requested file has exactly one PASS or FAIL verdict under its
# own "### FILE: <path>" heading and nothing else claims a verdict; otherwise "bad <reason>".
check_verdicts() {
  awk -v req="$2" '
    BEGIN { while ((getline l < req) > 0) want[l] = 1 }
    { sub(/\r$/, ""); sub(/[ \t]+$/, "") }
    /^### FILE VERDICT:/ {
      v = $0; sub(/^### FILE VERDICT:[ \t]*/, "", v)
      if (cur == "") { if (err == "") err = "a verdict outside any file section"; next }
      if (v != "PASS" && v != "FAIL") { if (err == "") err = "unparseable verdict for " cur; next }
      if (cur in got) { if (err == "") err = "more than one verdict for " cur; next }
      got[cur] = v; if (v == "FAIL") fails++
      next
    }
    /FILE VERDICT/ { if (err == "") err = "malformed verdict line: " $0; next }
    /^### FILE:/ {
      cur = $0; sub(/^### FILE:[ \t]*/, "", cur)
      if (!(cur in want) && err == "") err = "a verdict section for an unrequested file " cur
      next
    }
    END {
      if (err == "") for (f in want) if (!(f in got)) { err = "no verdict for " f; break }
      if (err != "") print "bad " err; else print "ok " fails + 0
    }' "$1"
}
mkdir -p "$SANDBOX_DIR/cwd"   # empty CWD keeps the reviewer on the supplied text, not the tree

FAIL_COUNT=0
REVIEWED=0
BATCHES=0
RATE_HIT=0
INCOMPLETE=0
declare -a PENDING=()
PENDING_LINES=0

flush_batch() {
  [ ${#PENDING[@]} -eq 0 ] && return 0
  BATCHES=$((BATCHES + 1))
  local input="$SANDBOX_DIR/input.txt"
  {
    printf '%s\n\n' "$PROMPT"
    echo "===== PR BLUEPRINT (cross-file context only) ====="
    cat "$BLUEPRINT"
    echo
    for f in "${PENDING[@]}"; do
      echo "===== FILE: $f ====="
      git diff --no-ext-diff --unified="$CONTEXT_LINES" "$BASE"...HEAD -- "$f"
      echo
    done
  } > "$input"

  echo "  batch $BATCHES (${#PENDING[@]} file(s), ~${PENDING_LINES} lines): ${PENDING[*]}" >&2

  local out rc=0
  out="$(run_batch "$input")" || rc=$?

  if grep -qiE 'rate.?limit|RESOURCE_EXHAUSTED|too many requests|\b429\b' "$SANDBOX_DIR/stderr.txt" 2>/dev/null; then
    RATE_HIT=1
  fi

  {
    echo "## Batch $BATCHES - ${PENDING[*]}"
    echo
    if [[ $RATE_HIT -eq 1 && ( $rc -ne 0 || -z "$out" ) ]]; then
      echo "_Rate limit hit - these files were NOT reviewed._"
      INCOMPLETE=1
    elif [ "$rc" -eq 137 ]; then
      echo "_Batch timed out (killed after ${BATCH_TIMEOUT}s) - lower the line budget and re-run, or record a skip._"
      INCOMPLETE=1
    elif [[ $rc -ne 0 || -z "$out" ]]; then
      echo "_No output (exit $rc) - not reviewed._"
      echo '```'; tail -n 3 "$SANDBOX_DIR/stderr.txt" 2>/dev/null || true; echo '```'
      INCOMPLETE=1
    else
      echo "$out"
      printf '%s\n' "$out" > "$SANDBOX_DIR/batch-out.txt"
      printf '%s\n' "${PENDING[@]}" > "$SANDBOX_DIR/batch-files.txt"
      local parsed; parsed="$(check_verdicts "$SANDBOX_DIR/batch-out.txt" "$SANDBOX_DIR/batch-files.txt")"
      if [[ "$parsed" == ok\ * ]]; then
        FAIL_COUNT=$((FAIL_COUNT + ${parsed#ok }))
      else
        echo
        echo "_Verdicts incomplete (${parsed#bad }) - this batch counts as NOT reviewed._"
        INCOMPLETE=1
      fi
    fi
    echo; echo "---"; echo
  } >> "$REPORT"

  PENDING=(); PENDING_LINES=0
}

echo "Reviewing ${#FILES[@]} changed file(s) against $BASE, batched to ~${LINE_BUDGET} diff lines per request..." >&2

for FILE in "${FILES[@]}"; do
  N="$(git diff --no-ext-diff --unified="$CONTEXT_LINES" "$BASE"...HEAD -- "$FILE" | wc -l)"
  [ "$N" -eq 0 ] && continue
  REVIEWED=$((REVIEWED + 1))
  if [[ ${#PENDING[@]} -gt 0 && $((PENDING_LINES + N)) -gt $LINE_BUDGET ]]; then
    flush_batch
    [ "$RATE_HIT" -eq 1 ] && break
  fi
  PENDING+=("$FILE")
  PENDING_LINES=$((PENDING_LINES + N))
done
[ "$RATE_HIT" -eq 0 ] && flush_batch

if [ "$RATE_HIT" -eq 1 ]; then
  {
    echo "## Unreviewed (rate limit)"
    echo
    echo "The rate limit was hit mid-run; remaining files were not reviewed."
    echo; echo "---"; echo
  } >> "$REPORT"
fi

{
  echo "# Overall"
  echo
  echo "Reviewer: $NAME   Files: $REVIEWED   Batches: $BATCHES   Line budget per batch: $LINE_BUDGET"
  echo "Files with FAIL verdict: $FAIL_COUNT"
  echo
  echo "### VERDICT"
  if [ "$INCOMPLETE" -eq 1 ]; then
    echo "INCOMPLETE"
  elif [ "$FAIL_COUNT" -gt 0 ]; then
    echo "FAIL"
  else
    echo "PASS"
  fi
} >> "$REPORT"

echo "Batched review report: $REPORT" >&2
cat "$REPORT"
