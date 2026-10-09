#!/usr/bin/env bash
# Pre-PR adversarial gate helper: the deterministic preflight plus a generic launcher for the
# model phases (sweep, hunt, arbitrate). It never edits the working tree.
#
# Run it by its installed path with the current directory inside the repository under review:
#   cd <consumer repo> && <skill dir>/scripts/run-adversarial-pipeline.sh <command> ...
# The target repository is the current directory's, or --repo DIR. It is never the script's own
# location, and the skills repository itself is refused unless --repo names it explicitly.
#
# Usage:
#   run-adversarial-pipeline.sh preflight --base REF [--test-cmd CMD] [--test-dir DIR]
#   run-adversarial-pipeline.sh run <sweep|hunt|arbitrate> --base REF --agent-cmd TEMPLATE
#                               [--spec FILE] [--no-sweep] [--scratch DIR] [--timeout SECONDS]
#   run-adversarial-pipeline.sh dossier <sweep|hunt|arbitrate> --base REF [--spec FILE] [--no-sweep] [--scratch DIR]
#   run-adversarial-pipeline.sh record <sweep|hunt|arbitrate> --base REF [--no-sweep]  # accept a subagent's report
#   run-adversarial-pipeline.sh checkout --base REF [--scratch DIR]   # throwaway detached worktree at HEAD (subagent flow)
#   run-adversarial-pipeline.sh cleanup <checkout-path>               # removes a checkout this script made
#   run-adversarial-pipeline.sh paths --base REF                      # prints this run's artifact paths
# Every command also takes --repo DIR.
#
# Runs: artifacts live in a run directory keyed by the base and head commit SHAs, under
# `git rev-parse --git-path adversarial-pipeline`. A phase is accepted only when its artifact is
# non-empty, not older than that phase's launch, starts with the line `REVIEW-RAN: yes`, and is
# stamped by this script for the same run. The stamp binds the artifact's sha256, the spec's sha256
# and the sha256 of every predecessor artifact it was built from; changing any of them un-accepts it.
# Each phase refuses to start unless its predecessors are accepted for the same run (exit 13):
# sweep needs a PASS preflight; hunt needs the sweep; arbitrate needs the sweep and the hunt.
# --no-sweep (no sweeper configured) drops the sweep from both requirements; pass it consistently.
# Re-running a phase (or the preflight) discards every later phase's acceptance.
#
# Isolation: every model phase runs in its own throwaway detached worktree at HEAD ({checkout},
# also the command's working directory), never in the primary checkout. If the primary checkout's
# HEAD, status or diff changed while the agent ran, the phase fails (exit 18).
#
# Env equivalents: ADVERSARIAL_REPO, ADVERSARIAL_TEST_CMD, ADVERSARIAL_TEST_DIR, ADVERSARIAL_BASE,
# ADVERSARIAL_SPEC_FILE, ADVERSARIAL_SCRATCH, ADVERSARIAL_AGENT_CMD, ADVERSARIAL_TIMEOUT (900).
#
# --agent-cmd is a shell command template built from the profile's agent definition for that phase.
# Placeholders (substituted shell-quoted): {prompt_file} the dossier, {output_file} the artifact,
# {checkout} the phase's throwaway worktree. If the template has no {output_file}, its stdout
# becomes the artifact. The command's stdin is the dossier, and it runs under a SIGKILL timeout.
# Read the prompt from stdin (for codex: `codex exec ... -`) or from {prompt_file}; never expand
# its contents into argv (argv is visible to other processes and one argument is capped at 128 KiB).
#
# Exit codes: 0 ok / PASS, 1 preflight FAIL, 2 usage, 3 preflight INCOMPLETE, 11 not a git repo,
# 12 bad base, 13 missing or invalid prior artifact, 14 cleanup refused, 15 agent command failed
# or wrote no fresh report, 17 agent ran blind (sandbox error on its stderr, or no `REVIEW-RAN: yes`
# first line), 18 the agent changed the primary checkout.
set -euo pipefail

usage() { awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0" >&2; exit 2; }
die() { local code="$1"; shift; echo "ERROR: $*" >&2; exit "$code"; }
abspath() { realpath -m -- "$1"; }

cmd="${1:-}"; [ -n "$cmd" ] || usage; shift
phase=""; target=""
case "$cmd" in
  dossier|run|record) phase="${1:-}"; [ -n "$phase" ] || usage; shift ;;
  cleanup) target="${1:-}"; [ -n "$target" ] || usage; shift; target="$(abspath "$target")" ;;
  preflight|checkout|paths) ;;
  -h|--help|help) usage ;;
  *) echo "ERROR: unknown command '$cmd'" >&2; usage ;;
esac

REPO="${ADVERSARIAL_REPO:-}"
BASE="${ADVERSARIAL_BASE:-}"
SPEC_FILE="${ADVERSARIAL_SPEC_FILE:-}"
TEST_CMD="${ADVERSARIAL_TEST_CMD:-}"
TEST_DIR="${ADVERSARIAL_TEST_DIR:-}"
SCRATCH="${ADVERSARIAL_SCRATCH:-}"
AGENT_CMD="${ADVERSARIAL_AGENT_CMD:-}"
TIMEOUT="${ADVERSARIAL_TIMEOUT:-900}"
NO_SWEEP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --repo|--base|--spec|--test-cmd|--test-dir|--scratch|--agent-cmd|--timeout)
      [ $# -ge 2 ] || die 2 "$1 needs a value"
      case "$1" in
        --repo) REPO="$2" ;;
        --base) BASE="$2" ;;
        --spec) SPEC_FILE="$2" ;;
        --test-cmd) TEST_CMD="$2" ;;
        --test-dir) TEST_DIR="$2" ;;
        --scratch) SCRATCH="$2" ;;
        --agent-cmd) AGENT_CMD="$2" ;;
        --timeout) TIMEOUT="$2" ;;
      esac
      shift 2 ;;
    --no-sweep) NO_SWEEP=1; shift ;;
    *) echo "ERROR: unknown option $1" >&2; usage ;;
  esac
done

# A named spec that is missing is an error; only an omitted spec gets the "no spec" fallback.
if [ -n "$SPEC_FILE" ]; then
  if [ ! -f "$SPEC_FILE" ] || [ ! -r "$SPEC_FILE" ]; then
    die 2 "--spec file '$SPEC_FILE' does not exist or is not readable."
  fi
  SPEC_FILE="$(abspath "$SPEC_FILE")"
fi
[[ "$TIMEOUT" =~ ^[0-9]+$ ]] || die 2 "--timeout must be a whole number of seconds."
if [ -n "$SCRATCH" ]; then SCRATCH="$(abspath "$SCRATCH")"; fi

# The target repository: --repo, else the current directory. Never this script's location.
if [ -n "$REPO" ]; then
  ROOT="$(git -C "$REPO" rev-parse --show-toplevel 2>/dev/null)" || die 11 "--repo '$REPO' is not inside a Git repository."
else
  ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || die 11 "not inside a Git repository (cd into the repository under review, or pass --repo)."
  if [ -f "$ROOT/skills.json" ] && [ -f "$ROOT/shared/runtimes.md" ]; then
    die 2 "the current directory is the skills repository ($ROOT), not a repository under review; cd into the consumer repository, or pass --repo to review the skills repository itself."
  fi
fi
cd "$ROOT"

OUT_BASE="$(git rev-parse --git-path adversarial-pipeline)"
mkdir -p "$OUT_BASE"
OUT_BASE="$(cd "$OUT_BASE" && pwd)"
REGISTRY="$OUT_BASE/checkouts.registry"

# Removes a checkout only if this script created and registered it and git still lists it as a
# worktree of this repository. There is no recursive-delete fallback: if git refuses, nothing is deleted.
remove_checkout() {  # $1 = absolute path
  local path="$1" listed=0 wt_line parent
  if [ ! -f "$REGISTRY" ] || ! grep -qxF -- "$path" "$REGISTRY"; then
    die 14 "'$path' is not a checkout this script created; refusing to remove it."
  fi
  while IFS= read -r wt_line; do
    case "$wt_line" in
      "worktree "*) if [ "$(abspath "${wt_line#worktree }")" = "$path" ]; then listed=1; fi ;;
    esac
  done < <(git worktree list --porcelain)
  [ "$listed" -eq 1 ] || die 14 "'$path' is registered but is not a worktree of $ROOT; refusing to remove it (run 'git worktree prune')."
  git worktree remove --force -- "$path" || die 14 "git refused to remove '$path'; nothing was deleted."
  grep -vxF -- "$path" "$REGISTRY" > "$REGISTRY.tmp" || true   # grep exits 1 when no line remains
  mv -- "$REGISTRY.tmp" "$REGISTRY"
  parent="$(dirname -- "$path")"
  case "$(basename -- "$parent")" in
    adversarial-checkout.*) rmdir -- "$parent" 2>/dev/null || true ;;   # our own mktemp dir, only if empty
  esac
  git worktree prune
}

if [ "$cmd" = "cleanup" ]; then
  remove_checkout "$target"
  echo "Removed checkout $target" >&2
  exit 0
fi

# --- every other command is bound to one run: base SHA + head SHA. --------------------------------
[ -n "$BASE" ] || die 12 "--base (or ADVERSARIAL_BASE) is required; use origin/<profile.git.integration_branch> after a fetch."
BASE_SHA="$(git rev-parse --verify -q "${BASE}^{commit}")" || die 12 "base ref '$BASE' does not exist (fetch it first)."
HEAD_SHA="$(git rev-parse --verify 'HEAD^{commit}')"
RUN_ID="${BASE_SHA}-${HEAD_SHA}"
RUN_DIR="$OUT_BASE/runs/$RUN_ID"
mkdir -p "$RUN_DIR"
PHASE0="$RUN_DIR/phase0-preflight.md"
SUITE_LOG="$RUN_DIR/phase0-suite.log"
PHASE1="$RUN_DIR/phase1-sweep.md"
PHASE2="$RUN_DIR/phase2-hunt.md"
PHASE3="$RUN_DIR/phase3-arbitration.md"

artifact_for() {
  case "$1" in
    preflight) echo "$PHASE0" ;;
    sweep) echo "$PHASE1" ;;
    hunt) echo "$PHASE2" ;;
    arbitrate) echo "$PHASE3" ;;
    *) die 2 "unknown phase '$1' (sweep|hunt|arbitrate)" ;;
  esac
}
if [ -n "$phase" ]; then
  case "$phase" in sweep|hunt|arbitrate) ;; *) die 2 "unknown phase '$phase' (sweep|hunt|arbitrate)" ;; esac
fi

sha_of() { sha256sum -- "$1" | cut -d' ' -f1; }
if [ -n "$SPEC_FILE" ]; then SPEC_SHA="$(sha_of "$SPEC_FILE")"; else SPEC_SHA="none"; fi

deps_of() {  # $1 = phase -> the phases its dossier is built from, one per line
  case "$1" in
    sweep) echo preflight ;;
    hunt) echo preflight; if [ "$NO_SWEEP" -eq 0 ]; then echo sweep; fi ;;
    arbitrate) echo preflight; if [ "$NO_SWEEP" -eq 0 ]; then echo sweep; fi; echo hunt ;;
  esac
}

downstream_of() {  # $1 = phase -> every later phase whose acceptance depends on it
  case "$1" in
    preflight) echo sweep hunt arbitrate ;;
    sweep) echo hunt arbitrate ;;
    hunt) echo arbitrate ;;
  esac
}

# The stamp binds the run, the artifact's content, the spec it was reviewed against (model phases)
# and the exact content of every predecessor artifact its dossier was built from.
stamp_text() {  # $1 = phase
  local art p dep; art="$(artifact_for "$1")"
  printf 'run=%s\nphase=%s\nsha256=%s\n' "$RUN_ID" "$1" "$(sha_of "$art")"
  if [ "$1" != "preflight" ]; then printf 'spec=%s\n' "$SPEC_SHA"; fi
  for p in $(deps_of "$1"); do
    dep="$(artifact_for "$p")"
    if [ -f "$dep" ]; then printf 'dep.%s=%s\n' "$p" "$(sha_of "$dep")"; else printf 'dep.%s=missing\n' "$p"; fi
  done
}

stamp() {  # $1 = phase: record that this run produced and accepted the phase's artifact
  local art; art="$(artifact_for "$1")"
  stamp_text "$1" > "$art.stamp"
}

accepted() {  # $1 = phase -> 0 when its artifact is non-empty, stamped for this run and spec, and
              # it and every predecessor it was built from are unchanged and accepted
  local art p; art="$(artifact_for "$1")"
  [ -s "$art" ] && [ -f "$art.stamp" ] || return 1
  [ "$(cat -- "$art.stamp")" = "$(stamp_text "$1")" ] || return 1
  for p in $(deps_of "$1"); do accepted "$p" || return 1; done
}

require_predecessors() {  # $1 = phase
  local p
  for p in $(deps_of "$1"); do
    accepted "$p" || die 13 "the $1 phase needs an accepted $p artifact from this run (base ${BASE_SHA:0:12}, head ${HEAD_SHA:0:12}, this spec, same --no-sweep); run $p at this head first."
  done
}

invalidate_downstream() {  # $1 = phase: a re-run discards every later phase's acceptance
  local p a
  for p in $(downstream_of "$1"); do a="$(artifact_for "$p")"; rm -f -- "$a.stamp"; done
}

begin_phase() {  # $1 = phase: drop any stale artifact and later acceptances, and mark the launch time
  local art; art="$(artifact_for "$1")"
  rm -f -- "$art" "$art.stamp"
  invalidate_downstream "$1"
  : > "$RUN_DIR/$1.launch"
}

# A fingerprint of the primary checkout: HEAD, status (untracked included) and the content diff.
primary_state() {
  git -C "$ROOT" rev-parse HEAD
  git -C "$ROOT" status --porcelain --untracked-files=all
  git -C "$ROOT" diff --no-ext-diff --binary HEAD | sha256sum
}

accept_phase() {  # $1 = phase, $2 = stderr log or "": validate a freshly written artifact, then stamp it
  local art; art="$(artifact_for "$1")"
  [ -f "$RUN_DIR/$1.launch" ] || die 15 "no launch marker for $1 in this run; write its dossier with 'dossier $1' first."
  [ -s "$art" ] || die 15 "the $1 agent produced no report ($art is missing or empty)."
  if [ "$RUN_DIR/$1.launch" -nt "$art" ]; then
    die 15 "$art is older than this $1 launch; it was not written by this run."
  fi
  # A reviewer whose sandbox could not start reads nothing yet may still exit 0: never a false clean.
  # Sandbox errors are looked for only in the agent's own stderr; the report may quote such text.
  if [ -n "$2" ] && [ -f "$2" ] && grep -qiE 'bwrap:|sandbox (failed|denied|could not)|Failed to make .* Permission denied' -- "$2"; then
    die 17 "the $1 agent ran blind (sandbox error on its stderr, see $2); treat this phase as failed, not clean."
  fi
  # The report must positively attest that the review ran.
  local first; first="$(head -n 1 -- "$art" | tr -d '\r' | sed 's/[[:space:]]*$//')"
  if [ "$first" != "REVIEW-RAN: yes" ]; then
    die 17 "the $1 report does not start with 'REVIEW-RAN: yes' (first line: '${first:0:120}'); treat this phase as failed, not clean."
  fi
  # The agent must not have touched the primary checkout.
  if [ -f "$RUN_DIR/$1.primary" ] && [ "$(primary_state)" != "$(cat -- "$RUN_DIR/$1.primary")" ]; then
    die 18 "the primary checkout ($ROOT) changed while the $1 agent ran; this phase is not accepted. Inspect 'git status' there."
  fi
  stamp "$1"
}

# The dossier and checkouts live outside .git: some agent runtimes refuse to read files under a
# repository's git dir, and some sandboxes make it read-only.
scratch_dir() {
  if [ -z "$SCRATCH" ]; then SCRATCH="$(mktemp -d -t adversarial-scratch.XXXXXX)"; fi
  mkdir -p -- "$SCRATCH"
  printf '%s\n' "$SCRATCH"
}

emit_spec() {
  if [ -n "$SPEC_FILE" ]; then
    cat -- "$SPEC_FILE"
  else
    echo "(no story/acceptance-criteria file supplied - judge scope from the diff alone)"
  fi
}

emit_context() {
  echo "===== STORY / ACCEPTANCE CRITERIA (the scope reference: work outside it is out of scope, not a defect) ====="
  emit_spec
  echo
  echo "===== BLUEPRINT (diffstat and files, ${BASE}...HEAD) ====="
  git diff --stat "$BASE_SHA"...HEAD
  echo
  echo "===== DIFF (${BASE}...HEAD) ====="
  git diff --no-ext-diff --unified=3 "$BASE_SHA"...HEAD
}

emit_prior() {  # $1 = phase, $2 = text when that phase is intentionally absent (--no-sweep)
  if accepted "$1"; then cat -- "$(artifact_for "$1")"; else echo "$2"; fi
}

write_dossier() {  # $1 = phase, $2 = dossier path
  local p="$1" out="$2"
  case "$p" in
    sweep)
      {
        echo "You are a high-volume adversarial code reviewer doing a FAST FIRST-PASS SWEEP."
        echo "Output ONLY a structured candidate list - no prose, no fixes, no plan. One entry per candidate:"
        echo "- file:line | severity (Critical/High/Medium/Low) | one-line claim | the concrete failure scenario"
        echo "Cover: vulnerability vectors, logic flaws, breaking changes, API/contract mismatches, test gaps, code smells."
        echo "Be exhaustive; volume over precision, and mark speculation as such."
        echo "Do NOT modify any files. Never write secrets to files or command arguments."
        echo "The FIRST line of your report must be exactly 'REVIEW-RAN: yes' when you read the diff below; otherwise"
        echo "make it 'REVIEW-RAN: no - <reason>'. A report without that line is treated as a review that did not run."
        echo
        emit_context
      } > "$out"
      ;;
    hunt)
      {
        echo "You are an empirical adversarial reviewer working in a THROWAWAY checkout of the unfixed head."
        echo "You may edit files in that checkout to run experiments; never commit, push, or touch any other tree."
        echo "Never write secrets to files or command arguments."
        echo
        echo "Job 1 - VERIFY. For each candidate below, write and run a minimal adversarial check (mutate the"
        echo "code, run the relevant tests, revert) and report VERIFIED with the exact command and observed"
        echo "result, or REFUTED with the observation that disproves it."
        echo "Job 2 - HUNT open-ended for defects the candidate list missed: a change that applies wrongly, a"
        echo "gate that acts in the wrong environment, a test that passes vacuously, a regression to shipped"
        echo "behaviour. Mutate and run to prove each one."
        echo
        echo "Execute, do not just reason. Report each finding with file:line, severity, the command run and"
        echo "the observed result. If your sandbox prevents reading or running anything, say so in the first"
        echo "line of your report; never report a clean result for a review that could not run."
        echo "The FIRST line of your report must be exactly 'REVIEW-RAN: yes' when you read the diff below and ran your checks in the checkout; otherwise"
        echo "make it 'REVIEW-RAN: no - <reason>'. A report without that line is treated as a review that did not run."
        echo
        echo "===== CANDIDATES (Phase 1 sweep) ====="
        emit_prior sweep "(sweep not configured - hunt only)"
        echo
        emit_context
      } > "$out"
      ;;
    arbitrate)
      {
        echo "You are the ARBITER for an adversarial code review. You get the diff, a raw candidate list from a"
        echo "cheap sweep (Phase 1), and empirical execution results (Phase 2)."
        echo "1. Filter hallucinations, false positives and unexploitable edge cases. Weigh the EMPIRICAL"
        echo "   Phase-2 results over Phase-1 theory."
        echo "2. Surface cross-module logic inconsistencies, security bypasses and architectural regressions"
        echo "   the lower tiers missed."
        echo "3. Never invent findings to fill a section. Do not modify files. Never write secrets to files or command arguments."
        echo "4. Output the final report in EXACTLY this Markdown layout and nothing else, after one first line:"
        echo "   'REVIEW-RAN: yes' when you read the diff and both phase results below; otherwise"
        echo "   'REVIEW-RAN: no - <reason>'. A report without that line is treated as a review that did not run."
        echo
        echo "### Critical vulnerabilities and breaking bugs"
        echo "(Only items validated by Phase-2 execution or confirmed by your reasoning.)"
        echo "* **File/Line:** path/to/file.ext:line"
        echo "* **The bug:** concise description."
        echo "* **Empirical evidence:** failing test log or exact logic trace."
        echo "* **Remediation:** suggested patch."
        echo
        echo "### Optimizations and code smells"
        echo "(Lower-priority cleanups, performance, architectural adjustments.)"
        echo
        echo "### Verified safe modules"
        echo "(The parts of the diff that were attacked and stood up, and the categories found clean.)"
        echo
        emit_context
        echo
        echo "===== PHASE 1 (sweep candidates) ====="
        emit_prior sweep "(sweep not configured)"
        echo
        echo "===== PHASE 2 (empirical results) ====="
        emit_prior hunt "(no Phase-2 results)"
      } > "$out"
      ;;
  esac
}

make_checkout() {  # prints the path of a registered throwaway detached worktree at HEAD
  local container dir
  if [ -n "$SCRATCH" ]; then
    mkdir -p -- "$SCRATCH"
    container="$(mktemp -d -p "$SCRATCH" adversarial-checkout.XXXXXX)"
  else
    container="$(mktemp -d -t adversarial-checkout.XXXXXX)"
  fi
  dir="$(abspath "$container/head-${HEAD_SHA:0:12}")"
  git worktree prune
  git worktree add -q --detach "$dir" "$HEAD_SHA"
  printf '%s\n' "$dir" >> "$REGISTRY"
  printf '%s\n' "$dir"
}

case "$cmd" in
  preflight)
    rm -f -- "$PHASE0.stamp"
    invalidate_downstream preflight
    status=0
    suite_ran=0
    EXPORT_ROOT=""
    # An interrupt or early abort must not leave the throwaway worktree registered in .git.
    # Only the script's own mktemp directory is removed, and only once git has emptied it.
    trap 'if [ -n "${EXPORT_ROOT:-}" ]; then git worktree remove --force "$EXPORT_ROOT/HEAD" >/dev/null 2>&1 || true; rmdir "$EXPORT_ROOT" 2>/dev/null || true; git worktree prune >/dev/null 2>&1 || true; fi' EXIT
    {
      echo "# Phase 0 - preflight (deterministic, no model)"
      echo
      echo "Base: ${BASE} (${BASE_SHA})"
      echo "Head: ${HEAD_SHA}"
      echo
      echo "## 1. Every intended file committed"
      # --untracked-files=all: plain --porcelain honours status.showUntrackedFiles=no and would hide the
      # untracked-but-intended file this check exists to catch. A failing git status is a FAIL, never "clean".
      if ! DIRTY="$(git status --porcelain --untracked-files=all 2>&1)"; then
        echo "FAIL - could not read the working-tree state, so it cannot be called clean:"
        echo '```'; printf '%s\n' "$DIRTY"; echo '```'
        status=1
      elif [ -z "$DIRTY" ]; then
        echo "PASS - the working tree is clean (untracked files included)."
      else
        echo "FAIL - uncommitted changes. A suite run against the working tree is not evidence that the"
        echo "committed branch passes; commit first."
        echo '```'; printf '%s\n' "$DIRTY"; echo '```'
        status=1
      fi
      echo
      echo "## 2. The suite, run in a clean checkout of HEAD"
      if [ -z "${TEST_CMD//[[:space:]]/}" ]; then
        echo "SKIPPED - no test command, so NOTHING exercised the committed tree. This is INCOMPLETE, not a pass."
      else
        # A detached worktree, not an archive export: it keeps git metadata, so tests that shell out to
        # git (ls-files, rev-parse) still work.
        EXPORT_ROOT="$(mktemp -d -t adversarial-preflight.XXXXXX)"
        EXPORT="$EXPORT_ROOT/HEAD"
        if ! git worktree add -q --detach "$EXPORT" "$HEAD_SHA" 2>/dev/null; then
          echo "ERROR - could not create a throwaway worktree at HEAD (stale registration? run 'git worktree prune')."
          status=1
        else
          # The test dir must stay inside the checkout, or a green run elsewhere becomes a PASS for this head.
          RESOLVED_EXPORT="$(realpath -m "$EXPORT")"
          RESOLVED_CWD="$(realpath -m "$EXPORT${TEST_DIR:+/$TEST_DIR}")"
          SUITE_CWD=""
          case "$RESOLVED_CWD" in
            "$RESOLVED_EXPORT" | "$RESOLVED_EXPORT"/*) SUITE_CWD="$RESOLVED_CWD" ;;
            *) echo "ERROR - the test dir escapes the committed checkout ($RESOLVED_CWD); refusing to run."; status=1 ;;
          esac
          if [ -n "$SUITE_CWD" ]; then
            echo "Checkout: detached worktree at HEAD (committed content only)"
            echo "Command: ${TEST_CMD}${TEST_DIR:+   (in $TEST_DIR)}"
            echo "NOTE: the exit status is the LAST command's; chain a sequence with && ('false; echo ok' exits 0)."
            echo '```'
            # The suite's own failure is the expected one and is handled here; every other failure propagates.
            suite_rc=0
            SUITE_OUT="$(cd "$SUITE_CWD" && bash -c "$TEST_CMD" 2>&1 < /dev/null)" || suite_rc=$?
            printf '%s\n' "$SUITE_OUT" | tail -n 40
            echo '```'
            if [ "$suite_rc" -eq 0 ]; then
              echo "PASS - the committed tree passes its own suite."
              suite_ran=1
            else
              echo "FAIL - the committed tree does NOT pass its own suite (exit $suite_rc, see above)."
              status=1
            fi
            printf '%s\n' "$SUITE_OUT" > "$SUITE_LOG"
            echo "Full suite output: $SUITE_LOG"
          fi
        fi
      fi
      echo
      echo "## Verdict"
      if [ "$status" -ne 0 ]; then
        echo "FAIL - fix this before spending any model budget."
      elif [ "$suite_ran" -eq 1 ]; then
        echo "PASS - proceed to the sweep and the hunt."
      else
        echo "INCOMPLETE - the tree is clean but the suite did not run. Re-run with a test command."
      fi
    } > "$PHASE0"
    cat -- "$PHASE0"
    echo "Phase 0 (preflight) -> $PHASE0" >&2
    if [ "$status" -ne 0 ]; then exit 1; fi
    if [ "$suite_ran" -eq 0 ]; then exit 3; fi
    stamp preflight
    exit 0
    ;;

  dossier)
    require_predecessors "$phase"
    begin_phase "$phase"
    dossier="$(scratch_dir)/${phase}-dossier.md"
    write_dossier "$phase" "$dossier"
    primary_state > "$RUN_DIR/$phase.primary"
    echo "Work in a throwaway checkout from 'checkout' (never the primary checkout)." >&2
    echo "Save the $phase report to $(artifact_for "$phase"), then run 'record $phase' with the same --base." >&2
    printf '%s\n' "$dossier"
    ;;

  record)
    require_predecessors "$phase"
    accept_phase "$phase" ""
    echo "Phase $phase accepted -> $(artifact_for "$phase")" >&2
    ;;

  run)
    [ -n "$AGENT_CMD" ] || die 2 "--agent-cmd (or ADVERSARIAL_AGENT_CMD) is required; build it from the profile agent for this phase."
    require_predecessors "$phase"
    out="$(artifact_for "$phase")"
    dossier="$(scratch_dir)/${phase}-dossier.md"
    write_dossier "$phase" "$dossier"
    # Every phase gets its own throwaway checkout; no agent ever runs in the primary checkout.
    checkout="$(make_checkout)"
    trap 'remove_checkout "$checkout" >/dev/null || echo "WARNING: could not remove checkout $checkout" >&2' EXIT
    q_prompt="$(printf '%q' "$dossier")"
    q_out="$(printf '%q' "$out")"
    q_checkout="$(printf '%q' "$checkout")"
    line="${AGENT_CMD//\{prompt_file\}/$q_prompt}"
    line="${line//\{checkout\}/$q_checkout}"
    errlog="$RUN_DIR/${phase}-agent.err"
    begin_phase "$phase"
    primary_state > "$RUN_DIR/$phase.primary"
    rc=0
    if [[ "$AGENT_CMD" == *"{output_file}"* ]]; then
      line="${line//\{output_file\}/$q_out}"
      (cd "$checkout" && timeout -s KILL "${TIMEOUT}s" bash -c "$line" < "$dossier" > "$RUN_DIR/${phase}-agent.log" 2> "$errlog") || rc=$?
    else
      (cd "$checkout" && timeout -s KILL "${TIMEOUT}s" bash -c "$line" < "$dossier" > "$out" 2> "$errlog") || rc=$?
    fi
    if [ "$(primary_state)" != "$(cat -- "$RUN_DIR/$phase.primary")" ]; then
      rm -f -- "$out.stamp"
      die 18 "the primary checkout ($ROOT) changed while the $phase agent ran; this phase is not accepted. Inspect 'git status' there."
    fi
    if [ "$rc" -ne 0 ]; then
      echo "ERROR: agent command failed for $phase (exit $rc; 137 = timed out). See $errlog:" >&2
      tail -n 5 "$errlog" >&2 || true
      exit 15
    fi
    accept_phase "$phase" "$errlog"
    echo "Phase $phase -> $out" >&2
    if [ "$phase" = "arbitrate" ]; then cat -- "$out"; fi
    ;;

  checkout) make_checkout ;;
  paths)
    printf 'run %s\npreflight %s\nsuite_log %s\nsweep %s\nhunt %s\narbitrate %s\n' \
      "$RUN_DIR" "$PHASE0" "$SUITE_LOG" "$PHASE1" "$PHASE2" "$PHASE3"
    ;;
esac
