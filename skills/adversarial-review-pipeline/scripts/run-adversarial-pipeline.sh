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
#   run-adversarial-pipeline.sh preflight --base REF [--test-cmd CMD] [--test-dir DIR] [--scratch DIR]
#   run-adversarial-pipeline.sh run <sweep|hunt|arbitrate> --base REF --agent-cmd TEMPLATE
#                               [--model ID] [--probe-cmd TEMPLATE] [--probe-timeout SECONDS]
#                               [--spec FILE] [--no-sweep] [--scratch DIR] [--timeout SECONDS]
#   run-adversarial-pipeline.sh dossier <sweep|hunt|arbitrate> --base REF [--spec FILE] [--no-sweep] [--scratch DIR]
#   run-adversarial-pipeline.sh record <sweep|hunt|arbitrate> --base REF [--model ID] [--spec FILE] [--no-sweep]  # accept a subagent's report
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
# The inputs (spec, --no-sweep, predecessor artifacts) are bound when the dossier is written; `record`
# and `run` refuse a report whose inputs changed since then (exit 13), so pass `record` the same
# --spec and --no-sweep as `dossier`.
# Re-running a phase (or the preflight) discards every later phase: its acceptance, its launch and
# binding, and any report in flight (a later `record` then exits 15).
#
# Isolation: every model phase runs in its own throwaway detached worktree at HEAD ({checkout},
# also the command's working directory), never in the primary checkout. A tripwire, not a boundary,
# compares the primary checkout before and after the agent: HEAD, tracked and untracked status, the
# diff, the shared git config and the hooks directory. Any change fails the phase (exit 18). It does
# not see ignored files or edits to files that were already untracked; the agent's sandbox is the
# real boundary (see references/runtimes.md).
#
# Env equivalents: ADVERSARIAL_REPO, ADVERSARIAL_TEST_CMD, ADVERSARIAL_TEST_DIR, ADVERSARIAL_BASE,
# ADVERSARIAL_SPEC_FILE, ADVERSARIAL_SCRATCH, ADVERSARIAL_AGENT_CMD, ADVERSARIAL_MODEL,
# ADVERSARIAL_PROBE_CMD, ADVERSARIAL_PROBE_TIMEOUT (30), ADVERSARIAL_TIMEOUT (900).
#
# --model ID (ADVERSARIAL_MODEL) is the model id this phase was given, quoted whole into the probe
# and echoed on every line as a label in which anything outside letters, digits and . _ / : @ # + ~
# , [ ] - becomes '_' (so no id can forge a field of a progress line), and an unset model prints as
# not-supplied. It must not contain control characters. The script never resolves a model: it echoes back the id it was handed. A phase that cannot run is failed, never skipped and
# never substituted with another model, provider or reviewer.
#
# --probe-cmd (ADVERSARIAL_PROBE_CMD) is an optional availability check for `run` (dossier and
# record say so and never probe): a shell command template whose {model} placeholder expands to
# "$ADVERSARIAL_PROBE_MODEL", the model id exported to the probe, so do not quote the placeholder
# inside the template and an id containing a space, an ampersand or a quote still stays one word. A template
# without {model} or ADVERSARIAL_PROBE_MODEL is refused (exit 2). That check is a lint on the text,
# not proof that the template queries the provider: a placeholder inside quotes or after an unquoted
# '#' is not expanded. The model is exported to the probe as ADVERSARIAL_PROBE_MODEL and {model}
# expands to it, so the value always arrives as one word; keep the probe a real call. It runs under
# its own --probe-timeout (ADVERSARIAL_PROBE_TIMEOUT, 30 seconds, never past the phase deadline),
# with stdin from /dev/null, in a fresh empty directory under the run's scratch directory - never
# inside the checkout under review. A configured probe that exits non-zero, prints a provider error (rate
# limit, authentication, quota exhaustion, unavailable or unknown model), or outlives its timeout
# fails the phase with exit 20 before the dossier is built and before any agent command runs,
# naming the phase, the model id supplied, the probe's exit code and its output tail (the timeout is
# named instead of an exit code when the probe outlived it). With no probe configured the phase
# records 'availability check: not configured' on stderr, so the absence is visible rather than
# silent.
#
# One deadline bounds the phase's work against a provider: the availability check, the throwaway
# checkout and the agent command with its whole process group share --timeout (ADVERSARIAL_TIMEOUT,
# default 900, at least 1). The local bookkeeping after the agent - the tripwire fingerprint and the
# acceptance checks - and the dossier write are not model work and are not bounded by it; they cost
# a few git calls each. The agent command runs in its own
# process group under one SIGKILL deadline of that whole group, and the group is killed when the
# command returns too, so a child the CLI leaves retrying after the main call failed cannot keep
# running past the phase. A phase killed by
# --timeout exits 19, naming the phase, the model id when supplied and the timeout in seconds; an
# interrupted gate (SIGINT, SIGTERM, SIGHUP) kills the same process group before it exits. No other
# failure path changes its exit code.
#
# Progress: while the agent runs, `run` writes an elapsed-time line to its own stderr - the first
# after one second, then at least every 30 seconds - carrying the phase, the elapsed seconds, the
# configured timeout and the availability-check state, and one completion line with the elapsed time
# and the phase's exit status on every exit of the phase attempt, success or failure. It is the last
# line the phase writes, after the artifact-path line and after an arbitration report has been
# echoed, so the status it reports is the status the process exits with (only teardown's own output
# can follow it). Its 'elapsed' covers everything up to that line, where a heartbeat line reports the agent's own
# elapsed seconds, and it carries 'exit=<status>' after the model id. The attempt starts once `run`
# accepts its agent command, so a `run` refused before that - usage, not a Git repository, a bad base
# - prints no completion line, because no phase ran. An agent can write anything to its own stderr,
# including a line shaped like this one: the phase's completion line is the last such line the phase
# writes (the phase's own last line: teardown and a checkout-cleanup warning can still follow it).
# Progress never reaches the artifact or the agent's stdout, so the artifact's first line
# stays 'REVIEW-RAN: yes'; stdout carries the artifact alone (arbitration's report), never progress,
# so do not merge the two streams and read the last line. A report the gate cannot write to stdout
# exits 1 through the same path, so its completion line names that failure; the phase itself stays
# accepted and stamped, because the model's work succeeded and only its delivery failed.
#
# Diagnosis: a non-zero agent exit, a timeout kill, and a report `accept_phase` rejects all print the
# phase, the exit code, the model id when supplied, and the last 40 lines of ${phase}-agent.err and
# ${phase}-agent.log (or, for `record`, the reason and the report tail) before exiting non-zero, plus
# every provider-error line from the full stderr log, so one is never lost past the tail window. The
# script cannot read a runtime's own session or event stream: a runtime that reports provider errors
# only there must surface them on the phase's stderr in its --agent-cmd template
# (references/runtimes.md, Models).
#
# A failed phase is never acceptable: it removes its own launch and binding, so a later `record` of
# the leftover report fails instead of stamping a report the run declared failed, and a re-run that
# fails before the agent starts still discards this phase's previous acceptance and every later
# phase.
#
# --scratch DIR names the session's scratch directory (references/runtimes.md, Scratch files): the
# script gives each run its own directory inside it, so a run's dossiers and checkouts do not
# collide. Never pass the profile's base directory itself. Omitted, the script creates its own
# standalone directory per invocation and exposes that directory to the phase agent. A phase agent
# also receives the session directory (the supplied one, else the standalone run directory) in
# ADVERSARIAL_SESSION_SCRATCH, so it can keep its own artefacts beside the run.
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
# first line), 18 the agent changed the primary checkout, 19 the phase was killed by --timeout,
# 20 the phase's availability check failed before any agent ran. An accepted arbitration report that
# cannot be written to stdout still exits 1, as it did before the completion-line work; the message
# names the stamped artifact so a driver does not re-run the model call.
# A checkout that cannot be created exits with git's own status, which is what that path did before
# the checkout became deadline-bounded.
set -euo pipefail

usage() { awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0" >&2; exit 2; }
die() { local code="$1"; shift; echo "ERROR: $*" >&2; exit "$code"; }

# Does a probe template reference the model somewhere the shell actually expands it? Walks the text
# with shell quoting state: {model} or ADVERSARIAL_PROBE_MODEL in normal text and inside double
# quotes (both expand there), but never inside single quotes or a comment.
probe_names_model() {
  local t="$1" i=0 n=${#1} c state=normal
  while [ "$i" -lt "$n" ]; do
    c="${t:$i:1}"
    case "$state" in
      normal)
        case "$c" in
          "'") state=single ;;
          '"') state=double ;;
          '#')
            case "${t:$(( i > 0 ? i - 1 : 0 )):1}" in
              ""|" "|"	"|";"|"|"|"&"|"("|")") state=comment ;;
            esac ;;
          *) case "${t:$i}" in
               "{model}"*) return 0 ;;
               ADVERSARIAL_PROBE_MODEL*)
                 case "${t:$(( i + 23 )):1}" in
                   ""|[!A-Za-z0-9_]*) return 0 ;;
                 esac ;;
             esac ;;
        esac ;;
      single)
        [ "$c" = "'" ] && state=normal ;;
      double)
        case "$c" in
          '"') state=normal ;;
          '\\') i=$(( i + 1 )) ;;
          *) case "${t:$i}" in
               "{model}"*) return 0 ;;
               ADVERSARIAL_PROBE_MODEL*)
                 case "${t:$(( i + 23 )):1}" in
                   ""|[!A-Za-z0-9_]*) return 0 ;;
                 esac ;;
             esac ;;
        esac ;;
      comment) : ;;
    esac
    i=$(( i + 1 ))
  done
  return 1
}
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
MODEL="${ADVERSARIAL_MODEL:-}"
MODEL_SET=0
PROBE_CMD="${ADVERSARIAL_PROBE_CMD:-}"
PROBE_TIMEOUT="${ADVERSARIAL_PROBE_TIMEOUT:-30}"
PROBE_SET=0
NO_SWEEP=0
SCRATCH_SET=0
while [ $# -gt 0 ]; do
  case "$1" in
    --repo|--base|--spec|--test-cmd|--test-dir|--scratch|--agent-cmd|--timeout|--model|--probe-cmd|--probe-timeout)
      [ $# -ge 2 ] || die 2 "$1 needs a value"
      case "$1" in
        --repo) REPO="$2" ;;
        --base) BASE="$2" ;;
        --spec) SPEC_FILE="$2" ;;
        --test-cmd) TEST_CMD="$2" ;;
        --test-dir) TEST_DIR="$2" ;;
        --scratch) SCRATCH="$2"; SCRATCH_SET=1 ;;
        --agent-cmd) AGENT_CMD="$2" ;;
        --timeout) TIMEOUT="$2" ;;
        --model) MODEL="$2"; MODEL_SET=1 ;;
        --probe-cmd) PROBE_CMD="$2"; PROBE_SET=1 ;;
        --probe-timeout) PROBE_TIMEOUT="$2" ;;
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
[[ "$TIMEOUT" =~ ^[1-9][0-9]*$ ]] || die 2 "--timeout must be a whole number of seconds, at least 1."
[[ "$PROBE_TIMEOUT" =~ ^[1-9][0-9]*$ ]] || die 2 "--probe-timeout must be a whole number of seconds, at least 1."
# A model id may be anything on one line; only `run` insists on a value when the flag is given.
# An explicitly empty model id is a usage error where the model is used; elsewhere it is unset.
if [ "$MODEL_SET" -eq 1 ] && [ -z "$MODEL" ] && [ "$cmd" = "run" ]; then
  die 2 "--model needs a non-empty model id"
fi
# Only `run` probes, so only `run` insists on a probe template that names the model it checks.
if [ "$PROBE_SET" -eq 1 ] && [ -z "$PROBE_CMD" ] && [ "$cmd" = "run" ]; then
  die 2 "--probe-cmd needs a non-empty template"
fi
if [ "$cmd" = "run" ] && [ -n "$PROBE_CMD" ]; then
  probe_names_model "$PROBE_CMD" \
    || die 2 "--probe-cmd must reference the supplied model where the shell expands it ({model} unquoted, or ADVERSARIAL_PROBE_MODEL outside single quotes and comments); this is a lint, not proof that the template queries the provider"
fi
# A control character in a model id is a broken configuration on any command: refusing it loudly is
# better than printing a line it could forge.
case "$MODEL" in
  *[[:cntrl:]]*) die 2 "--model must not contain control characters; pass the model id on one line" ;;
esac
# The label is printed by every command, so any character that could forge a field or a line is
# mapped to '_' here; the model id's own shell metacharacters are still quoted whole into the probe.
if [ -z "$MODEL" ]; then
  MODEL_LABEL="not-supplied"
else
  MODEL_LABEL="$(printf '%s' "$MODEL" | tr -c 'A-Za-z0-9._/:@#+~,][-' '_')" || MODEL_LABEL="not-supplied"
fi

availability_state="availability check: not configured"

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

# A supplied scratch directory is validated once, here and before any command creates something:
# a phase must never write a partial artifact and then reject the directory, a relative path would
# dirty the reviewed tree, and a directory inside the checkout dirties it too. Only the commands
# that use it validate it, so `cleanup` never fails on an unrelated flag.
validate_scratch() {
  local resolved_scratch resolved_root
  case "$cmd" in
    preflight|dossier|run|checkout) ;;
    *) return 0 ;;
  esac
  if [ "$SCRATCH_SET" -eq 1 ] && [ -z "$SCRATCH" ]; then
    die 2 "--scratch needs a directory value; omit the flag to let the script choose one"
  fi
  [ -n "${SCRATCH:-}" ] || return 0
  case "$SCRATCH" in
    /*) ;;
    *) die 2 "--scratch must be an absolute path: $SCRATCH" ;;
  esac
  if [ -e "$SCRATCH" ] && [ ! -d "$SCRATCH" ]; then
    die 2 "--scratch must be a directory, not a file: $SCRATCH"
  fi
  resolved_scratch="$(realpath -m -- "$SCRATCH")"
  resolved_root="$(realpath -m -- "$ROOT")"
  case "$resolved_scratch" in
    "$resolved_root" | "$resolved_root"/*)
      die 2 "--scratch must be outside the repository under review: $resolved_scratch"
      ;;
  esac
  mkdir -p -- "$SCRATCH" || die 2 "--scratch is not usable as a directory: $SCRATCH"
  [ -w "$SCRATCH" ] || die 2 "--scratch is not writable: $SCRATCH"
}

validate_scratch

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

# The binding names what a phase's dossier was built from: the run, the spec (model phases), the
# --no-sweep choice and the exact content of every predecessor artifact.
binding_text() {  # $1 = phase
  local p dep
  printf 'run=%s\nphase=%s\n' "$RUN_ID" "$1"
  if [ "$1" != "preflight" ]; then printf 'spec=%s\nno_sweep=%s\n' "$SPEC_SHA" "$NO_SWEEP"; fi
  for p in $(deps_of "$1"); do
    dep="$(artifact_for "$p")"
    if [ -f "$dep" ]; then printf 'dep.%s=%s\n' "$p" "$(sha_of "$dep")"; else printf 'dep.%s=missing\n' "$p"; fi
  done
}

# The stamp is the binding plus the artifact's own content.
stamp_text() {  # $1 = phase
  printf 'sha256=%s\n' "$(sha_of "$(artifact_for "$1")")"
  binding_text "$1"
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

invalidate_downstream() {  # $1 = phase: a re-run discards every later phase, including one in flight
  local p a
  for p in $(downstream_of "$1"); do
    a="$(artifact_for "$p")"
    rm -f -- "$a" "$a.stamp" "$RUN_DIR/$p.launch" "$RUN_DIR/$p.binding" "$RUN_DIR/$p.primary"
  done
}

begin_phase() {  # $1 = phase: drop stale output and later phases, bind the inputs, mark the launch time
  local art; art="$(artifact_for "$1")"
  rm -f -- "$art" "$art.stamp"
  invalidate_downstream "$1"
  : > "$RUN_DIR/$1.launch"
}

bind_phase() {  # $1 = phase: record the inputs its dossier was built from and the primary checkout
  binding_text "$1" > "$RUN_DIR/$1.binding"
  primary_state > "$RUN_DIR/$1.primary"
}

# A tripwire fingerprint of the primary checkout: HEAD, status (untracked included), the content diff,
# the shared git dir's config, and the default and effective (core.hooksPath) hooks dirs. Not ignored files.
COMMON_DIR="$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir)"
primary_state() {
  git -C "$ROOT" rev-parse HEAD
  git -C "$ROOT" status --porcelain --untracked-files=all
  git -C "$ROOT" diff --no-ext-diff --binary HEAD | sha256sum
  local f
  for f in config config.worktree; do
    if [ -f "$COMMON_DIR/$f" ]; then printf '%s %s\n' "$f" "$(sha_of "$COMMON_DIR/$f")"; else echo "$f absent"; fi
  done
  # The default hooks dir and the effective one (core.hooksPath may point anywhere).
  local d
  for d in "$COMMON_DIR/hooks" "$(git -C "$ROOT" rev-parse --path-format=absolute --git-path hooks)"; do
    if [ -d "$d" ]; then
      printf '%s ' "$d"
      (cd "$d" && find . -printf '%y %m %p\n' | LC_ALL=C sort && find . -type f -exec sha256sum {} + | LC_ALL=C sort) | sha256sum
    else
      echo "$d absent"
    fi
  done
}

accept_phase() {  # $1 = phase, $2 = stderr log or "": validate a freshly written artifact, then stamp it
  local art; art="$(artifact_for "$1")"
  [ -f "$RUN_DIR/$1.launch" ] && [ -f "$RUN_DIR/$1.binding" ] && [ -f "$RUN_DIR/$1.primary" ] \
    || die 15 "no launch for $1 in this run (never started, or discarded by a later re-run of an earlier phase); write its dossier with 'dossier $1' first."
  if [ "$(cat -- "$RUN_DIR/$1.binding")" != "$(binding_text "$1")" ]; then
    die 13 "the $1 inputs changed since its dossier was written (spec, --no-sweep or a predecessor artifact); start the $1 phase again."
  fi
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
  if [ "$(primary_state)" != "$(cat -- "$RUN_DIR/$1.primary")" ]; then
    die 18 "the primary checkout ($ROOT) changed while the $1 agent ran; this phase is not accepted. Inspect 'git status' there."
  fi
  stamp "$1"
}

# The dossier and checkouts live outside .git: some agent runtimes refuse to read files under a
# repository's git dir, and some sandboxes make it read-only.
init_scratch() {  # sets SCRATCH (this run's directory) and SESSION_SCRATCH (the supplied one)
  if [ -z "$SCRATCH" ]; then
    SCRATCH="$(mktemp -d -t adversarial-scratch.XXXXXX)" || die 2 "could not create a scratch directory"
    SESSION_SCRATCH=""
  else
    # A supplied directory is the session's scratch directory (references/runtimes.md, Scratch
    # files): give this run its own directory inside it, so two runs never share dossier names.
    SESSION_SCRATCH="$SCRATCH"
    [ -w "$SESSION_SCRATCH" ] || die 2 "--scratch is not writable: $SESSION_SCRATCH"
    SCRATCH="$(mktemp -d -p "$SESSION_SCRATCH" run.XXXXXX)" \
      || die 2 "could not create a run directory inside --scratch $SESSION_SCRATCH"
  fi
}

# --- process control: one SIGKILL deadline per phase, over the whole process group -----------------
# Seconds between progress lines once the first one has been written; the contract is "at least
# every 30 seconds", and the first line comes one second in so a short phase still shows progress.
HEARTBEAT_SECONDS=10
POLL_SECONDS=0.2
DIAGNOSIS_LINES=40
PROBE_TAIL_LINES=20
# Provider failures worth failing a phase for before spending budget on it. Each alternative names
# the provider condition or the model it is about, so healthy output that merely contains a word
# like "unavailable" does not fail a phase; the probe's own output tail is surfaced verbatim, so a
# false positive is visible and cheap to correct.
PROVIDER_ERROR_RE='rate[ _-]?limit|too many requests|unauthori[sz]ed|authentication (failed|error|required)|invalid[ _-]?api[ _-]?key|(http|status)[^[:alpha:]]{0,8}(40[13]|429|5[0-9][0-9])|(http|status)[ _-]*code[^0-9]{0,3}(40[13]|429|5[0-9][0-9])|quota[ _-]?(exceeded|exhausted|reached)|resource[ _-]?exhausted|exceeded your (current )?quota|insufficient[ _-](funds|credit|credits|quota|balance)|credit[ _-]balance([ _-]+is)?[ _-]+(too[ _-]+low|low|empty|exhausted|insufficient|zero)|credit[ _-]balance[ _:-]*[$]?[ _-]*0([^.0-9]|$)|out of quota|credits? (are )?(exhausted|depleted)|service unavailable|model[ _-]?not[ _-]?found|unknown model|no such model|model[^.]*(not found|not available|unavailable|overloaded)'

# Runs a command line in its own process group under one SIGKILL deadline of that whole group, so a
# child the CLI leaves retrying cannot keep the phase alive. The deadline is our own, so a timeout
# is attributable from this path and never guessed from an exit code (a self-killed child also
# exits 137). Results: RUN_RC (the command's exit status), RUN_TIMED_OUT (1 when the deadline
# killed the group), RUN_ELAPSED (whole seconds).
#   $1 command line  $2 timeout seconds  $3 stdin path  $4 stdout path
#   $5 stderr path, or --combined to merge stderr into $4  $6 phase to heartbeat for ("" = none)
RUN_RC=0
RUN_TIMED_OUT=0
RUN_ELAPSED=0
GUARDED_PID=""
run_guarded() {
  local line="$1" secs="$2" stdin_path="$3" stdout_path="$4" stderr_path="$5" hb_phase="$6"
  local rcfile pid start elapsed next_hb rc_extra=""
  RUN_RC=0
  RUN_TIMED_OUT=0
  RUN_ELAPSED=0
  rcfile="$(mktemp -p "$RUN_DIR" run-status.XXXXXX)" \
    || fail_phase 2 "could not create a status file for the phase's guard in the run directory ($RUN_DIR)"
  rm -f -- "$rcfile"
  if [ "$stderr_path" = "--combined" ]; then rc_extra="2>&1"; fi
  start="$SECONDS"
  next_hb=1
  # Job control gives the background job its own process group, so the kill reaches every child.
  # The status is captured with `||` so `set -e` cannot abort the job before it records it.
  set -m
  if [ -n "$rc_extra" ]; then
    { rc=0; bash -c "$line" < "$stdin_path" > "$stdout_path" 2>&1 || rc=$?; printf '%s\n' "$rc" > "$rcfile"; } &
  else
    { rc=0; bash -c "$line" < "$stdin_path" > "$stdout_path" 2> "$stderr_path" || rc=$?; printf '%s\n' "$rc" > "$rcfile"; } &
  fi
  pid=$!
  GUARDED_PID="$pid"
  set +m
  while [ ! -f "$rcfile" ]; do
    elapsed=$(( SECONDS - start ))
    if [ "$elapsed" -ge "$secs" ]; then
      kill_guarded
      wait "$pid" 2>/dev/null || true
      rm -f -- "$rcfile"
      RUN_TIMED_OUT=1
      RUN_RC=137
      RUN_ELAPSED="$elapsed"
      return 0
    fi
    if [ -n "$hb_phase" ] && [ "$elapsed" -ge "$next_hb" ]; then
      progress_line "$hb_phase" "$elapsed"
      next_hb=$(( elapsed + HEARTBEAT_SECONDS ))
    fi
    sleep "$POLL_SECONDS"
  done
  RUN_RC="$(cat -- "$rcfile" 2>/dev/null || echo "")"
  case "$RUN_RC" in ''|*[!0-9]*) RUN_RC=1 ;; esac
  wait "$pid" 2>/dev/null || true
  # A CLI can leave a retry child behind after its main call returns; never let it outlive the phase.
  kill -KILL -- "-$pid" 2>/dev/null || true
  GUARDED_PID=""
  rm -f -- "$rcfile"
  RUN_ELAPSED="$(( SECONDS - start ))"
}

kill_guarded() {  # SIGKILL the in-flight guarded process group, if any
  if [ -n "$GUARDED_PID" ]; then
    kill -KILL -- "-$GUARDED_PID" 2>/dev/null || true
    GUARDED_PID=""
  fi
}

on_signal() {  # $1 exit code: an interrupted gate orphans neither its process group nor its state
  kill_guarded
  printf 'adversarial-pipeline: interrupted (exit %s); this phase is not accepted\n' "$1" >&2
  if [ -n "${phase:-}" ] && [ -n "${RUN_DIR:-}" ] && [ -d "$RUN_DIR" ]; then
    rm -f -- "$RUN_DIR/$phase.launch" "$RUN_DIR/$phase.binding" "$RUN_DIR/$phase.primary" \
      "$(artifact_for "$phase").stamp" 2>/dev/null || true
  fi
  exit "$1"
}

progress_line() {  # $1 phase, $2 elapsed seconds: stderr only, never the artifact or the agent's stdout
  printf 'adversarial-pipeline: phase=%s elapsed=%ss timeout=%ss model=%s; %s\n' \
    "$1" "$2" "$TIMEOUT" "$MODEL_LABEL" "$availability_state" >&2
}

completion_line() {  # $1 phase, $2 elapsed seconds, $3 the phase's exit status
  printf 'adversarial-pipeline: phase=%s complete elapsed=%ss model=%s exit=%s\n' \
    "$1" "$2" "${MODEL_LABEL:-not-supplied}" "$3" >&2
}

# A phase attempt reports completion however it ends, so the elapsed time and the exit status are
# never missing from the evidence. The attempt starts once `run` accepts its agent command, so a
# refusal before it (usage, not a Git repository, a bad base) is the only path with no completion line.
PHASE_START=0
CHECKOUT_PATH=""
COMPLETION_EMITTED=0
on_run_exit() {  # a run attempt's single exit path: report completion, then clean up, keeping the status
  local rc=$?
  set +e
  trap - EXIT
  kill_guarded   # whatever ended the attempt, no guarded child may outlive it
  trap '' INT TERM HUP QUIT USR1 USR2   # the status is reported; a later signal must not rewrite it
  if [ "$COMPLETION_EMITTED" -eq 0 ] && [ -n "${phase:-}" ]; then
    COMPLETION_EMITTED=1
    completion_line "$phase" "$(( SECONDS - PHASE_START ))" "$rc"
  fi
  if [ -n "${CHECKOUT_PATH:-}" ]; then
    ( remove_checkout "$CHECKOUT_PATH" ) >/dev/null \
      || echo "WARNING: could not remove checkout $CHECKOUT_PATH (see above)" >&2
  fi
  exit "$rc"
}

emit_tail() {  # $1 label, $2 file: the last DIAGNOSIS_LINES lines, verbatim, or a note that it is absent
  local lines
  if [ ! -f "$2" ]; then
    printf '%s: (no such file: %s)\n' "$1" "$2" >&2
    return 0
  fi
  lines="$(tail -n "$DIAGNOSIS_LINES" -- "$2" 2>/dev/null || true)"
  if [ -z "$lines" ]; then
    printf '%s: (empty: %s)\n' "$1" "$2" >&2
  else
    printf '%s: last %s lines of %s:\n%s\n' "$1" "$DIAGNOSIS_LINES" "$2" "$lines" >&2
  fi
}

provider_lines() {  # $1 file: every provider-error line, verbatim, even past the tail window
  local lines
  [ -f "$1" ] || return 0
  # The first matches, not the last: the tail below already shows the most recent lines, so this is
  # what keeps a distinct root error that was followed by a retry storm.
  lines="$(grep -aiE -- "$PROVIDER_ERROR_RE" "$1" 2>/dev/null | head -n "$DIAGNOSIS_LINES" || true)"
  if [ -n "$lines" ]; then
    printf 'adversarial-pipeline: provider-error lines from %s:\n%s\n' "$1" "$lines" >&2
  fi
}

diagnose_phase() {  # $1 phase, $2 exit code, $3 reason (already captured), $4 report path when applicable
  local phase_name="$1" code="$2" reason="${3:-}" report="${4:-}"
  printf 'adversarial-pipeline: phase=%s exit=%s model=%s\n' "$phase_name" "$code" "${MODEL_LABEL:-not-supplied}" >&2
  if [ -n "$reason" ]; then
    printf 'adversarial-pipeline: reason: %s\n' "${reason#ERROR: }" >&2
  fi
  if [ -n "$report" ]; then
    emit_tail "adversarial-pipeline: report tail" "$report"
    return 0
  fi
  emit_tail "adversarial-pipeline: ${phase_name}-agent.err" "$RUN_DIR/${phase_name}-agent.err"
  provider_lines "$RUN_DIR/${phase_name}-agent.err"
  emit_tail "adversarial-pipeline: ${phase_name}-agent.log" "$RUN_DIR/${phase_name}-agent.log"
}

fail_phase() {  # $1 exit code, $2 reason: a failed phase is never acceptable, not even by a later record
  local code="$1" reason="${2:-}"
  diagnose_phase "$phase" "$code" "$reason"
  rm -f -- "$(artifact_for "$phase").stamp" \
    "$RUN_DIR/$phase.launch" "$RUN_DIR/$phase.binding" "$RUN_DIR/$phase.primary"
  exit "$code"
}

remove_probe_dir() {  # $1 directory: only a probe directory this function's caller made
  case "$1" in
    "$SCRATCH"/probe.*) rm -rf -- "$1" ;;
  esac
}

# The availability check: a caller-supplied probe template, run before the dossier is built and
# before any agent command. The script never resolves a model; it substitutes the id it was given.
# Its own --probe-timeout bounds it, and it never runs past the phase deadline shared with the agent.
availability_probe() {  # $1 phase, $2 phase deadline ($SECONDS at expiry): sets availability_state
  local phase_name="$1" deadline="$2" probedir out line tail_text provider_hit
  local remaining limit phase_bound=0
  if [ -z "$MODEL" ]; then
    fail_phase 20 "a probe is configured but no model was supplied; pass --model ID (or ADVERSARIAL_MODEL) so the probe has a model to check"
  fi
  remaining=$(( deadline - SECONDS ))
  limit="$PROBE_TIMEOUT"
  if [ "$remaining" -lt "$limit" ]; then limit="$remaining"; phase_bound=1; fi
  [ "$limit" -lt 0 ] && limit=0
  probedir="$(mktemp -d -p "$SCRATCH" "probe.$phase_name.XXXXXX")" \
    || fail_phase 2 "could not create a probe directory under the run's scratch directory ($SCRATCH)"
  out="$RUN_DIR/$phase_name-probe.log"
  : > "$out"
  # {model} expands to the model's value through its environment variable, so no quoting of the id
  # can be lost in the substitution and any id (a space, an ampersand, a quote) stays one word.
  line="${PROBE_CMD//\{model\}/\"\$ADVERSARIAL_PROBE_MODEL\"}"
  # stdin is /dev/null, and the working directory is a fresh empty directory under the run's
  # scratch directory - never the checkout under review.
  line="cd $(printf '%q' "$probedir") && ${line}"
  availability_state="availability check: running"
  # The model reaches the probe through this variable, and {model} expands to it. Whether the
  # template actually exercises the provider is the template's job; this only guarantees the value
  # arrives as one word, whatever the id contains.
  ADVERSARIAL_PROBE_MODEL="$MODEL" \
    run_guarded "$line" "$limit" /dev/null "$out" --combined "$phase_name"
  tail_text="$(tail -n "$PROBE_TAIL_LINES" -- "$out" 2>/dev/null || true)"
  provider_hit="$(grep -aiE -- "$PROVIDER_ERROR_RE" "$out" 2>/dev/null | head -n 1 || true)"
  if [ "$RUN_TIMED_OUT" -eq 1 ]; then
    remove_probe_dir "$probedir"
    if [ "$phase_bound" -eq 1 ]; then
      fail_phase 19 "the ${TIMEOUT}s phase deadline (--timeout) expired while the availability check for model '$MODEL' was still running; the phase is a failure, not a clean one.
probe output tail:
${tail_text:-(no output)}"
    fi
    fail_phase 20 "the availability check for model '$MODEL' timed out after its --probe-timeout (${limit}s) and was killed with its process group.
probe output tail:
${tail_text:-(no output)}"
  fi
  if [ "$RUN_RC" -ne 0 ]; then
    remove_probe_dir "$probedir"
    fail_phase 20 "the availability check for model '$MODEL' failed with exit code ${RUN_RC}.
probe output tail:
${tail_text:-(no output)}"
  fi
  if [ -n "$provider_hit" ]; then
    remove_probe_dir "$probedir"
    fail_phase 20 "the availability check for model '$MODEL' reported a provider error with exit code 0.
probe output tail:
${tail_text:-(no output)}"
  fi
  remove_probe_dir "$probedir"
  rm -f -- "$out"   # a passing check leaves no product behind
  availability_state="availability check: probe ok"
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
        echo "The session's scratch directory is ${SESSION_SCRATCH:-$SCRATCH}; keep any artefact you create there."
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
        echo "The session's scratch directory is ${SESSION_SCRATCH:-$SCRATCH}; keep any artefact you create there."
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
        echo "The session's scratch directory is ${SESSION_SCRATCH:-$SCRATCH}; keep any artefact you create there."
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
  local container dir bounded="" rc=0 started add_cmd
  if [ -n "${CHECKOUT_DEADLINE:-}" ]; then
    bounded="$(( CHECKOUT_DEADLINE - SECONDS ))"
    [ "$bounded" -ge 1 ] || return 124   # 124 = the phase deadline left no time (timeout's own code)
  fi
  if [ -n "$SCRATCH" ]; then
    mkdir -p -- "$SCRATCH" || return 2
    container="$(mktemp -d -p "$SCRATCH" adversarial-checkout.XXXXXX)" || return 2
  else
    container="$(mktemp -d -t adversarial-checkout.XXXXXX)" || return 2
  fi
  [ -n "$container" ] && [ -d "$container" ] || return 2
  dir="$(abspath "$container/head-${HEAD_SHA:0:12}")"
  add_cmd="git worktree prune && git worktree add -q --detach $(printf '%q' "$dir") $(printf '%q' "$HEAD_SHA")"
  if [ -n "$bounded" ]; then
    # The checkout runs under the same guarded SIGKILL deadline as the agent, so it needs no
    # external timeout(1) and a hung git cannot outlive the phase.
    run_guarded "$add_cmd" "$bounded" /dev/null "$RUN_DIR/checkout.log" "$RUN_DIR/checkout.err" ""
    if [ "$RUN_TIMED_OUT" -eq 1 ]; then
      # The cleanup prune is bounded too: the hung call was the git work itself.
      run_guarded "git worktree prune" 10 /dev/null "$RUN_DIR/checkout.log" "$RUN_DIR/checkout.err" ""
      case "$container" in */adversarial-checkout.*) rm -rf -- "$container" ;; esac
      return 124
    fi
    rc="$RUN_RC"
  else
    bash -c "$add_cmd"
    rc=$?
  fi
  if [ "$rc" -ne 0 ]; then
    rmdir -- "$container" 2>/dev/null || true
    return "$rc"
  fi
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
        if [ -n "$SCRATCH" ]; then
          mkdir -p -- "$SCRATCH"
          EXPORT_ROOT="$(mktemp -d -p "$SCRATCH" adversarial-preflight.XXXXXX)"
        else
          EXPORT_ROOT="$(mktemp -d -t adversarial-preflight.XXXXXX)"
        fi
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
    if [ -n "$PROBE_CMD" ]; then
      echo "note: the availability check runs in 'run' only; dossier does not probe the model" >&2
    fi
    require_predecessors "$phase"
    init_scratch
    begin_phase "$phase"
    dossier="$SCRATCH/${phase}-dossier.md"
    write_dossier "$phase" "$dossier"
    bind_phase "$phase"
    echo "Work in a throwaway checkout from 'checkout' (never the primary checkout)." >&2
    echo "Save the $phase report to $(artifact_for "$phase"), then run 'record $phase' with the same --base, --spec and --no-sweep." >&2
    printf '%s\n' "$dossier"
    ;;

  record)
    if [ -n "$PROBE_CMD" ]; then
      echo "note: the availability check runs in 'run' only; record does not probe the model" >&2
    fi
    require_predecessors "$phase"
    rc_accept=0
    reason_file="$(mktemp -p "$RUN_DIR" record-reason.XXXXXX)" \
      || die 2 "could not create a status file in the run directory"
    ( accept_phase "$phase" "" ) 2> "$reason_file" || rc_accept=$?
    if [ "$rc_accept" -ne 0 ]; then
      diagnose_phase "$phase" "$rc_accept" "$(cat -- "$reason_file" 2>/dev/null || true)" "$(artifact_for "$phase")"
      rm -f -- "$reason_file"
      exit "$rc_accept"
    fi
    rm -f -- "$reason_file"
    echo "Phase $phase accepted -> $(artifact_for "$phase")" >&2
    ;;

  run)
    [ -n "$AGENT_CMD" ] || die 2 "--agent-cmd (or ADVERSARIAL_AGENT_CMD) is required; build it from the profile agent for this phase."
    PHASE_START=$SECONDS
    CHECKOUT_PATH=""
    COMPLETION_EMITTED=0
    trap 'on_signal 130' INT
    trap 'on_signal 143' TERM
    trap 'on_signal 129' HUP
    trap 'on_signal 131' QUIT
    trap 'on_signal 138' USR1
    trap 'on_signal 140' USR2
    trap on_run_exit EXIT
    # From here the phase attempt is real, so every exit reports completion; a missing predecessor is
    # one of those failures, not a refusal before the attempt starts. A re-run discards this phase's
    # previous acceptance and every later phase before anything can fail, so no early failure can
    # leave an older report acceptable. The primary-checkout baseline is taken before the probe, so a
    # probe that writes into the checkout cannot hide inside it, and stale logs go first: a diagnosis
    # must never show a previous attempt's streams as this attempt's.
    begin_phase "$phase"
    bind_phase "$phase"
    out="$(artifact_for "$phase")"
    errlog="$RUN_DIR/${phase}-agent.err"
    agentlog="$RUN_DIR/${phase}-agent.log"
    rm -f -- "$errlog" "$agentlog"
    require_predecessors "$phase"
    init_scratch
    dossier="$SCRATCH/${phase}-dossier.md"
    if [ "$SECONDS" -ge "$(( PHASE_START + TIMEOUT ))" ]; then
      fail_phase 19 "the $phase phase was killed by --timeout: the ${TIMEOUT}s phase deadline expired while preparing the run directory (model=$MODEL_LABEL); the phase is a failure, not a clean one."
    fi
    # One deadline for the whole phase, measured from its start: everything that runs under it,
    # the probe and the throwaway checkout included, shares the remaining budget.
    phase_deadline=$(( PHASE_START + TIMEOUT ))
    # The availability check runs before the dossier is built and before any agent command.
    if [ -n "$PROBE_CMD" ]; then
      availability_probe "$phase" "$phase_deadline"
      if [ "$(primary_state)" != "$(cat -- "$RUN_DIR/$phase.primary")" ]; then
        fail_phase 18 "the primary checkout ($ROOT) changed while the availability check for the $phase phase ran; this phase is not accepted. Inspect 'git status' there."
      fi
    fi
    printf 'adversarial-pipeline: phase=%s model=%s; %s\n' "$phase" "$MODEL_LABEL" "$availability_state" >&2
    write_dossier "$phase" "$dossier"
    # Every phase gets its own throwaway checkout; no agent ever runs in the primary checkout.
    CHECKOUT_DEADLINE="$phase_deadline"
    checkout_rc=0
    checkout="$(make_checkout)" || checkout_rc=$?
    unset CHECKOUT_DEADLINE
    if [ "$checkout_rc" -eq 124 ]; then
      fail_phase 19 "the $phase phase was killed by --timeout: the ${TIMEOUT}s phase deadline expired while creating the throwaway checkout (model=$MODEL_LABEL); the phase is a failure, not a clean one."
    fi
    if [ "$checkout_rc" -ne 0 ]; then
      fail_phase "$checkout_rc" "could not create the throwaway checkout for the $phase phase (git worktree add failed with status $checkout_rc); the phase never started."
    fi
    CHECKOUT_PATH="$checkout"
    q_prompt="$(printf '%q' "$dossier")"
    q_out="$(printf '%q' "$out")"
    q_checkout="$(printf '%q' "$checkout")"
    line="${AGENT_CMD//\{prompt_file\}/$q_prompt}"
    line="${line//\{checkout\}/$q_checkout}"
    result_out="$out"
    if [[ "$AGENT_CMD" == *"{output_file}"* ]]; then
      line="${line//\{output_file\}/$q_out}"
      result_out="$agentlog"
    fi
    remaining=$(( phase_deadline - SECONDS ))
    if [ "$remaining" -le 0 ]; then
      fail_phase 19 "the $phase phase was killed by --timeout: the ${TIMEOUT}s phase deadline expired before the agent command could start (model=$MODEL_LABEL); the phase is a failure, not a clean one, and nothing was substituted for it."
    fi
    export ADVERSARIAL_SESSION_SCRATCH="${SESSION_SCRATCH:-$SCRATCH}"
    run_guarded "cd $q_checkout && ${line}" "$remaining" "$dossier" "$result_out" "$errlog" "$phase"
    unset ADVERSARIAL_SESSION_SCRATCH
    if [[ "$AGENT_CMD" != *"{output_file}"* ]]; then
      cp -- "$out" "$agentlog" 2>/dev/null || true   # the agent's stdout is both the artifact and its log
    fi
    changed_note=""
    if [ "$(primary_state)" != "$(cat -- "$RUN_DIR/$phase.primary")" ]; then
      changed_note=" It also changed the primary checkout ($ROOT), which no later phase would accept."
    fi
    if [ "$RUN_TIMED_OUT" -eq 1 ]; then
      fail_phase 19 "the $phase phase was killed by --timeout: its whole process group received SIGKILL ${RUN_ELAPSED}s into the ${TIMEOUT}s deadline (model=$MODEL_LABEL); the phase is a failure, not a clean one, and nothing was substituted for it.${changed_note}"
    fi
    if [ "$RUN_RC" -ne 0 ]; then
      if [ "$RUN_RC" -ge 128 ]; then
        fail_phase 15 "the $phase agent command was killed by signal $((RUN_RC - 128)) (exit $RUN_RC, model=$MODEL_LABEL); this phase is failed, not clean, and nothing was substituted for it.${changed_note}"
      fi
      fail_phase 15 "the $phase agent command failed (exit $RUN_RC, model=$MODEL_LABEL); this phase is failed, not clean, and nothing was substituted for it.${changed_note}"
    fi
    if [ -n "$changed_note" ]; then
      fail_phase 18 "the primary checkout ($ROOT) changed while the $phase agent ran; this phase is not accepted. Inspect 'git status' there."
    fi
    rc_accept=0
    reason_file="$(mktemp -p "$RUN_DIR" accept-reason.XXXXXX)" \
      || fail_phase 2 "could not create a status file in the run directory"
    ( accept_phase "$phase" "$errlog" ) 2> "$reason_file" || rc_accept=$?
    if [ "$rc_accept" -ne 0 ]; then
      fail_phase "$rc_accept" "$(cat -- "$reason_file" 2>/dev/null || true)"
    fi
    rm -f -- "$reason_file"
    echo "Phase $phase -> $out" >&2
    if [ "$phase" = "arbitrate" ]; then
      cat -- "$out" || {
        echo "ERROR: could not deliver the arbitration report (see the error above); the phase is accepted and stamped at $out, but its report did not reach stdout" >&2
        exit 1
      }
    fi
    ;;

  checkout) make_checkout || die 2 "could not create the throwaway checkout" ;;
  paths)
    printf 'run %s\npreflight %s\nsuite_log %s\nsweep %s\nhunt %s\narbitrate %s\n' \
      "$RUN_DIR" "$PHASE0" "$SUITE_LOG" "$PHASE1" "$PHASE2" "$PHASE3"
    ;;
esac
