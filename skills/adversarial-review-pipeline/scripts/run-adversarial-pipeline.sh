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
#   run-adversarial-pipeline.sh preflight --base REF [--full-suite on|off] [--test-cmd CMD] [--test-dir DIR] [--scratch DIR]
#                               # --full-suite off: no suite run, 'full-suite: off' logged in its place;
#                               # omitted: resolve-full-suite.py resolves it from the profile (off when none)
#   run-adversarial-pipeline.sh run <sweep|hunt|arbitrate> --base REF --agent-cmd TEMPLATE
#                               [--model ID] [--agent NAME] [--probe-cmd TEMPLATE] [--probe-timeout SECONDS]
#                               [--spec FILE] [--no-sweep] [--scratch DIR] [--timeout SECONDS]
#                               [--shard K/N]   (hunt only)
#   run-adversarial-pipeline.sh dossier <sweep|hunt|arbitrate> --base REF [--spec FILE] [--no-sweep] [--scratch DIR]
#                               [--shard K/N]   (hunt only)
#                               # also creates the phase's checkout and prints 'CHECKOUT: <path>' on stderr
#   run-adversarial-pipeline.sh record <sweep|hunt|arbitrate> --base REF [--model ID] [--agent NAME] [--spec FILE] [--no-sweep]
#                               [--shard K/N]   (hunt only; pass the same value as `dossier hunt`)
#                               # accept a subagent's report
#   run-adversarial-pipeline.sh checkout --base REF [--scratch DIR]   # an extra throwaway detached worktree at HEAD
#   run-adversarial-pipeline.sh cleanup <checkout-path>               # removes a checkout this script made
#   run-adversarial-pipeline.sh paths --base REF                      # prints this run's artifact paths,
#                               # then a final 'dossier_sizes <path>' line naming the size log
#   run-adversarial-pipeline.sh checklist --base REF                  # prints the review checklist items
#                               # for the paths changed in REF...HEAD (see "Review checklist")
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
# Sharded hunt: `run hunt`, `dossier hunt` and `record hunt` accept `--shard K/N`. K and N are
# decimal integers with 1 <= K <= N and no leading zero; N = 1 is accepted only as `--shard 1/1`.
# Every other value is a usage error (exit 2) with one stderr line naming it, and so is `--shard`
# given more than once. `--shard` on sweep or arbitrate, or on any command other than run, dossier
# or record, is a usage error (exit 2) naming the command and the flag; the ADVERSARIAL_SHARD
# default applies only to those hunt commands, so a leftover value never refuses another command.
# `record hunt` must be passed the same `--shard` as `dossier hunt`, exactly as for `--spec` and
# `--no-sweep`. The launch file records that exact selection (`shard=<k>/<n>`, or `shard=none` when
# the flag was omitted), because `--shard 1/1` and an omitted flag share a byte-identical binding;
# a missing, empty or unreadable launch is a state error (exit 15), `record` refuses a launch whose
# selection differs (exit 13), and a different shard index finds no launch and exits 15.
# With N >= 2 the invocation writes <run dir>/phase2-hunt.<k>.md and never writes or accepts
# phase2-hunt.md for that run; its stamp and its binding carry the line shard=<k>/<n>. Each shard
# owns its run-state files beside its artifact, suffixed with the shard index - hunt.<k>.launch,
# hunt.<k>.binding, hunt.<k>.primary, hunt.<k>.dossier (size sidecar), hunt.<k>-agent.err and
# hunt.<k>-agent.log - and each is created, replaced and discarded only for its own shard. The
# unsharded names stay exactly today's. A later shard's re-run leaves every other shard's
# acceptance standing; a failed shard leaves no stamp and no accepted artifact for itself and is
# diagnosed with its shard=<k>/<n> on the progress, completion and diagnosis stderr lines.
# The first sharded hunt invocation of a run records the run's hunt plan in <run dir>/hunt.shards:
# a first line `n=<n>` followed by each shard's artifact path, one per line in shard order. It is
# written only when the invocation is sharded, so an unsharded plan is the file's absence. An
# omitted `--shard` and `--shard 1/1` both select the unsharded plan. A run whose hunt already ran
# unsharded rejects a later `--shard K/N` with N >= 2; a run whose plan is sharded requires an
# explicit `--shard K/N` carrying that recorded N. Any conflict is a usage error (exit 2) that
# changes neither the plan nor any acceptance. Re-running the preflight, or the sweep when the run
# uses one, removes the plan and every shard artifact and state file exactly as it discards an
# unsharded hunt today. When the plan is sharded, `paths` prints one `hunt.<k> <path>` line per
# recorded shard in shard order in place of the single `hunt` line, `dossier hunt`'s save-path
# line names the shard's artifact, and `dossier-sizes.md` lists one `hunt.<k>: <bytes> bytes` line
# per shard in shard order in place of the single `hunt` line. A plan that exists is the run's
# authority: a first line that is not n=<count> of at least two, or a path line that is not that
# shard's phase2-hunt.<k>.md, is refused with exit 13 naming the plan, never read as an absent plan.
# With no `--shard`, or with
# `--shard 1/1`, the artifact path, the stamp, the binding, the phase's file set and the `paths`
# output are exactly today's, and the dossier is identical to today's once each occurrence of its
# own checkout path is normalised. The launch is the phase's one run-state file whose content
# differs from today's: it records the hunt's selection (`shard=<k>/<n>`, or `shard=none` when the
# flag was omitted), and that recorded selection is what `record` enforces. A later
# `run arbitrate` requires every recorded hunt shard to
# be accepted and exits 13 naming the first unaccepted one. Chain mode's `--phases hunt,arbitrate`
# does not carry `--shard`; one shard is one invocation.
#
# Isolation: every model phase runs in its own throwaway detached worktree at HEAD ({checkout},
# also the command's working directory), never in the primary checkout. The checkout exists before
# the phase's dossier is written, and every dossier names it on a 'CHECKOUT: <path>' line beside
# 'BASE: <ref> <base SHA>' and 'HEAD: <sha>', so what a dossier does not embed is readable there:
# the sweep and hunt dossiers embed the diff, the arbitrate dossier only its diffstat. A dossier
# that cannot be written removes its checkout: `run` through its exit teardown, `dossier` itself
# before it exits; after a successful `dossier`, `cleanup` removes it. A tripwire, not a boundary,
# compares the primary checkout before and after the agent: HEAD, tracked and untracked status, the
# diff, the shared git config and the hooks directory. Any change fails the phase (exit 18). It does
# not see ignored files or edits to files that were already untracked; the agent's sandbox is the
# real boundary (see references/runtimes.md).
#
# Exclusion: the sweep and hunt dossiers leave generated, vendored and fixture files out of the
# embedded diff; they stay in the diffstat and in the checkout, and an 'EXCLUDED' section lists each
# one as '"<path>" | <reason>', the full repo-relative path always double-quoted and escaped exactly as the
# truncation marker and the size sidecar escape a quoted path (one shared escape: a quote or a backslash
# backslash-escaped, a control byte as its named escape or a three-digit octal escape, a byte of 127 or more as
# a three-digit octal escape). A changed path (repo-relative, without 'a/' or
# 'b/') is excluded when either arm holds, both read from the head under review, never the working
# tree:
#   (a) `git check-attr --source=<head SHA>` reports linguist-generated or linguist-vendored as
#       `set` or `true` (reason `linguist-generated` or `linguist-vendored`); `unset`, `unspecified`
#       and `false` never exclude. Only the head's .gitattributes files count: info/attributes,
#       core.attributesFile, init templates and the system attributes file are not read.
#   (b) the path matches a line of the exclusion list `.adversarial-exclude` at the root of the
#       repository under review, read from the head (reason `glob:<pattern>`). One glob per line,
#       surrounding whitespace stripped, a line whose first non-space character is '#' is a comment,
#       and a leading './' is stripped; each glob matches the whole path with bash
#       `[[ "$path" == <pattern> ]]` semantics, so '*' and '?' match '/' and '*.json' matches
#       'a/b.json'. Inline comments and '!' negation are unsupported. A missing or empty list
#       excludes nothing.
# An attribute reason wins over a matching glob. Changes are matched with rename detection on, and
# when either side of a rename is excluded both sides are, the other side listed with the excluded
# side's reason. Test modules get no automatic exclusion. The kept diff takes the same pinned options
# and per-file cap as the embedded diff below. The arbitrate dossier embeds no diff, so it lists no
# exclusions.
#
# Review checklist: `.agent-skills/review-checklist.txt` in the repository under review, read from the
# base commit (so a change cannot rewrite the checklist its own review uses), holds one
# `<bash glob> | <review item>` per line; blank lines and lines whose first non-space character is
# '#' are ignored, and any other line without ' | ', or holding a NUL or \001 byte, is skipped
# with a warning on stderr. The glob is the text before the first ' | ' and is matched unquoted with bash
# `[[ path == glob ]]` against each changed path as git prints it (repo-relative, no leading './',
# rename detection off, so both sides of a rename count): '*' crosses '/', and '**/x' does not match
# a top-level 'x'. `checklist` prints each matching item once (keyed on its text), in file order; a
# file absent at the base or no match prints nothing and exits 0, and a git failure exits 22. The
# sweep dossier ends with the same items, each prefixed '- ', under a '===== Review checklist'
# heading: every whole item that fits in CHECKLIST_CAP_CHARS, in order, then a truncation notice if
# any was left out. It has no such heading when none matches. With the sweep skipped (--no-sweep),
# no phase shows them.
#
# Embedded diff: the sweep and hunt dossiers embed `git diff --no-ext-diff --unified=1` of the run's
# range, and DIFF_CAP_BYTES (4096, in bytes of unified-diff text, per file and not a bound on the whole
# diff) caps each file's section: its `diff --git` header, hunk headers and hunks together. A section at
# or below the cap is emitted byte-identical to git's output. A larger one keeps whole hunks from the
# start and drops the rest; only when the header lines plus the first hunk already exceed the cap is
# that hunk clipped, and a header that alone exceeds the cap is cut, both at a line boundary (zero
# bytes when no complete line fits). The dropped remainder becomes one marker line,
#   <!-- TRUNCATED: <path> (<shown>/<total> bytes) - the full diff of this file is in your checkout at <CHECKOUT> -->
# where <path> is the destination path (the source path of a deletion), git-quoted only when it holds
# a double quote, backslash or control byte, <total> is the file's uncapped section and <shown> what
# was emitted, in bytes, and <CHECKOUT> is the dossier's own CHECKOUT: value. The diffstat is untouched,
# and a failing `git diff` still fails the dossier write. The call pins --no-color, the a/ and b/
# prefixes and --submodule=short, so a user's color.ui, diff.noprefix, diff.mnemonicPrefix or
# diff.submodule setting cannot hide a section boundary from the splitter, which streams the diff one
# section at a time. The splitter needs python3, which the preflight checks.
#
# Size sidecars: every completed dossier write, on `run` or `dossier`, leaves `<phase>.dossier` in the
# run directory: a `path=<absolute dossier path>` line, a `bytes=<n>` line (`LC_ALL=C wc -c` of that
# dossier), and one `excluded <path> reason=<reason>` line per path the exclusion step left out of the
# dossier's diff (the arbitrate dossier lists none); both paths are escaped as the truncation marker
# escapes its path, so every record is one physical line. A phase's start removes its own sidecar, a re-run removes the sidecars of the phases it
# discards, and a `dossier` whose write fails or is undone removes the one it wrote; an invocation
# refused before its phase starts removes nothing. `run` measures its dossier once, as its phase
# attempt exits, since the agent can rewrite its dossier, so no record outlives a rewrite. Each
# record is written to a temporary file and renamed into place. Sidecars are measurements only: they are not in any binding or stamp and never change
# acceptance. One that cannot be written prints a WARNING, removes only its own temporary file and
# changes no exit status.
#
# Size log: `dossier-sizes.md` in the run directory (`paths` names it) renders the sidecars present,
# rebuilt after every completed sidecar write and after every sidecar removal point (a phase's start
# and the phases it discards, whether or not a sidecar was there, and the `dossier` exit trap). It
# lists sweep, hunt and arbitrate in that order: '<phase>: <bytes> bytes' followed by the sidecar's
# `excluded` lines, or '<phase>: not run' without a usable sidecar. Under --no-sweep the sweep line is
# 'sweep: absent (--no-sweep)' and any sweep sidecar is ignored. A final 'total: <bytes> bytes' line
# appears once every phase --no-sweep does not disable has a sidecar, and sums those phases. The log
# is a view only: no phase demands it, it is in no binding or stamp, and one that cannot be written
# prints one WARNING and changes no exit status or acceptance.
#
# Env equivalents: ADVERSARIAL_REPO, ADVERSARIAL_TEST_CMD, ADVERSARIAL_TEST_DIR, ADVERSARIAL_BASE,
# ADVERSARIAL_SPEC_FILE, ADVERSARIAL_SCRATCH, ADVERSARIAL_AGENT_CMD, ADVERSARIAL_MODEL, ADVERSARIAL_AGENT,
# ADVERSARIAL_SHARD, ADVERSARIAL_PROBE_CMD, ADVERSARIAL_PROBE_TIMEOUT (30), ADVERSARIAL_TIMEOUT (900).
#
# Arbiter identity and retention: --agent NAME (ADVERSARIAL_AGENT) carries the name of the profile
# arbiter entry; --agent wins over ADVERSARIAL_AGENT when both are set, and it must not contain control
# characters. When the script accepts an arbitrate phase, on `run` or on `record`, it (not the model)
# writes three lines directly after the unchanged first line 'REVIEW-RAN: yes' and before it stamps
# the artifact:
#   ARBITER-AGENT: <name>
#   ARBITER-MODEL: <model id exactly as given by --model>
#   ARBITER-HEAD: <full HEAD SHA>
# An absent --agent or --model value is written as not-supplied, and so is an empty one where the
# command accepts it (`run` still refuses an empty --model with exit 2). Lines 2 to 4 are the only
# identity block: the body below them is the model's text, copied unchanged, so a reader never scans
# it for ARBITER- lines. ARBITER-HEAD is the HEAD when the script runs, so run `record arbitrate` at
# the reviewed head. A report whose first line is not exactly 'REVIEW-RAN: yes' (trailing whitespace
# or a CR included) fails (exit 17) and writes and retains nothing. The report with its identity
# lines is retained, before it is stamped, as an immutable (read-only) copy in
#   <git common dir>/adversarial-pipeline/arbitration-rounds
# where <git common dir> is the output of `git rev-parse --path-format=absolute --git-common-dir`, so every worktree of the
# clone resolves the same directory, independent of the run directory, --scratch and the worktree:
#   round-<UTC timestamp>-<full HEAD SHA>-<first 12 hex of the report sha256>-<n>.md
# The timestamp is `date -u +%Y%m%dT%H%M%SZ`. The copy is written to a temporary file in that
# directory and published with a no-clobber hard link; when the name exists the next <n> is tried,
# so two byte-identical arbitrations at one head leave two files and nothing is overwritten. Any
# failure to write or publish the copy, or to stamp the report after it, fails the phase (exit 21):
# no stamp is left, a copy it had published is removed, and the report is restored as the agent
# wrote it. A signal before publishing
# starts restores it the same way; once publishing starts, the copy and the stamp land together and
# the phase stays accepted. An accepted phase prints
#   Retained arbitration report -> <path>
# on stderr, the absolute path of the copy; stdout still carries the artifact alone. One dossier
# accepts one arbitration: recording an accepted arbitration again fails (exit 15), and a new round
# needs a new `dossier arbitrate` or `run arbitrate`. No re-run, discard or `cleanup` removes a
# retained copy.
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
# ADVERSARIAL_SESSION_SCRATCH, so it can keep its own artifacts beside the run.
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
# 20 the phase's availability check failed before any agent ran, 21 the arbitrate phase could not
# write its identity lines or retain its accepted report (not accepted), 22 the review checklist or
# the changed paths could not be read (checklist, dossier sweep). An accepted arbitration report that
# cannot be written to stdout still exits 1, as it did before the completion-line work; the message
# names the stamped artifact so a driver does not re-run the model call.
# A checkout that cannot be created exits with git's own status, which is what that path did before
# the checkout became deadline-bounded.
set -euo pipefail

DIFF_CAP_BYTES=4096   # bytes of unified-diff text per file in an embedded diff (see "Embedded diff" above)
CHECKLIST_CAP_CHARS=8192   # characters of matched items in the sweep dossier (see "Review checklist" above)

SCRIPT_DIR="$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"   # the real directory, through any symlink

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
  cleanup)
    # A leading dash is a flag, not the checkout path: name the flag the command does not take.
    case "${1:-}" in
      --shard|--shard=*)
        die 2 "--shard is not valid for the cleanup command; it applies to run hunt, dossier hunt and record hunt" ;;
      -*) ;;
      *) target="${1:-}"; [ -n "$target" ] || usage; shift; target="$(abspath "$target")" ;;
    esac
    ;;
  preflight|checkout|paths|checklist) ;;
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
ARBITER_AGENT="${ADVERSARIAL_AGENT:-}"
# The env equivalent is a default for the commands that take the flag, so a leftover value never
# refuses a command that does not read it (the same rule ADVERSARIAL_MODEL follows).
SHARD="${ADVERSARIAL_SHARD:-}"
SHARD_SET=0
SHARD_SEEN=0
case "$cmd" in
  run|dossier|record) if [ "$phase" = "hunt" ] && [ -n "$SHARD" ]; then SHARD_SET=1; fi ;;
esac
PROBE_CMD="${ADVERSARIAL_PROBE_CMD:-}"
PROBE_TIMEOUT="${ADVERSARIAL_PROBE_TIMEOUT:-30}"
PROBE_SET=0
NO_SWEEP=0
SCRATCH_SET=0
FULL_SUITE=""
FULL_SUITE_SET=0
while [ $# -gt 0 ]; do
  case "$1" in
    --repo|--base|--spec|--test-cmd|--test-dir|--scratch|--agent-cmd|--agent|--timeout|--model|--probe-cmd|--probe-timeout|--full-suite|--shard)
      [ $# -ge 2 ] || die 2 "$1 needs a value"
      case "$1" in
        --full-suite) FULL_SUITE="$2"; FULL_SUITE_SET=1 ;;
        --repo) REPO="$2" ;;
        --base) BASE="$2" ;;
        --spec) SPEC_FILE="$2" ;;
        --test-cmd) TEST_CMD="$2" ;;
        --test-dir) TEST_DIR="$2" ;;
        --scratch) SCRATCH="$2"; SCRATCH_SET=1 ;;
        --agent-cmd) AGENT_CMD="$2" ;;
        --agent) ARBITER_AGENT="$2" ;;
        --timeout) TIMEOUT="$2" ;;
        --model) MODEL="$2"; MODEL_SET=1 ;;
        --probe-cmd) PROBE_CMD="$2"; PROBE_SET=1 ;;
        --probe-timeout) PROBE_TIMEOUT="$2" ;;
        --shard) SHARD_SEEN=$(( SHARD_SEEN + 1 )); SHARD="$2"; SHARD_SET=1 ;;
      esac
      shift 2 ;;
    --no-sweep) NO_SWEEP=1; shift ;;
    *) echo "ERROR: unknown option $1" >&2; usage ;;
  esac
done
if [ "$FULL_SUITE_SET" -eq 1 ]; then
  case "$FULL_SUITE" in
    on|off) ;;
    *) printf 'ERROR: --full-suite must be on or off, not %q\n' "$FULL_SUITE" >&2; usage ;;
  esac
  [ "$cmd" = "preflight" ] || { echo "ERROR: --full-suite is a preflight option; $cmd does not read it" >&2; usage; }
fi

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
case "$ARBITER_AGENT" in
  *[[:cntrl:]]*) die 2 "--agent (ADVERSARIAL_AGENT) must not contain control characters; pass the agent name on one line" ;;
esac
# --shard is the hunt's shard selector: grammar here, plan validation once the run directory is known.
SHARD_K="" SHARD_N="" SHARDED=0
if [ "$SHARD_SEEN" -gt 1 ]; then
  die 2 "--shard given $SHARD_SEEN times; pass it once"
fi
if [ "$SHARD_SET" -eq 1 ]; then
  case "$cmd" in
    run|dossier|record) ;;
    *) die 2 "--shard is not valid for the $cmd command; it applies to run hunt, dossier hunt and record hunt" ;;
  esac
  [ "$phase" = "hunt" ] || die 2 "--shard is not valid for the $phase phase of $cmd; it applies to hunt only"
  # AC1 wants one stderr line that names the offending value: escape anything that could forge a line.
  SHARD_SHOWN="${SHARD//$'\n'/\\n}"
  SHARD_SHOWN="${SHARD_SHOWN//$'\r'/\\r}"
  SHARD_SHOWN="${SHARD_SHOWN//$'\t'/\\t}"
  SHARD_SHOWN="$(printf '%s' "$SHARD_SHOWN" | tr -c '[:print:]' '?')"
  [[ "$SHARD" =~ ^([1-9][0-9]*)/([1-9][0-9]*)$ ]] \
    || die 2 "--shard value '$SHARD_SHOWN' is invalid: expected K/N with decimal integers 1 <= K <= N and no leading zero"
  SHARD_K="${BASH_REMATCH[1]}"
  SHARD_N="${BASH_REMATCH[2]}"
  # Canonical decimals with no leading zero compare by length, then lexically: no integer range.
  if [ "${#SHARD_K}" -gt "${#SHARD_N}" ] \
    || { [ "${#SHARD_K}" -eq "${#SHARD_N}" ] && [ "$SHARD_K" \> "$SHARD_N" ]; }; then
    die 2 "--shard value '$SHARD_SHOWN' is invalid: K must be at least 1 and at most N"
  fi
fi
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
    preflight|dossier|run|checkout|checklist) ;;
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
HUNT_PLAN="$RUN_DIR/hunt.shards"
SHARD_LABEL=""

# The run-state prefix of an invocation: hunt is per shard when the invocation is sharded.
state_key() {  # $1 phase -> the file-name prefix for this invocation's run-state files
  case "$1" in
    hunt) if [ "$SHARDED" -eq 1 ]; then echo "hunt.$SHARD_K"; else echo hunt; fi ;;
    *) echo "$1" ;;
  esac
}

plan_exists() { [ -e "$HUNT_PLAN" ]; }
plan_paths() { tail -n +2 -- "$HUNT_PLAN"; }

# Reads and validates the run's hunt plan, setting PLAN_N. A plan that exists is the run's
# authority, so a plan that is not the recorded shape is a state error rather than an absent plan:
# it never silently waives the shard prerequisites.
plan_read() {
  local line count=0
  PLAN_N="$(head -n 1 -- "$HUNT_PLAN" | sed -n 's/^n=\([1-9][0-9]*\)$/\1/p')"
  [ -n "$PLAN_N" ] \
    || die 13 "the run's hunt plan $HUNT_PLAN is corrupt: its first line is not n=<count>; re-run the preflight (or the sweep) to discard it"
  [ "$PLAN_N" != "1" ] \
    || die 13 "the run's hunt plan $HUNT_PLAN records n=1, but a sharded plan records at least two shards; re-run the preflight (or the sweep) to discard it"
  while IFS= read -r line; do
    count=$(( count + 1 ))
    [ "$line" = "$RUN_DIR/phase2-hunt.$count.md" ] \
      || die 13 "the run's hunt plan $HUNT_PLAN is corrupt: the artifact path on line $(( count + 1 )) is not shard $count's $RUN_DIR/phase2-hunt.$count.md; re-run the preflight (or the sweep) to discard it"
  done < <(plan_paths)
  [ "$count" = "$PLAN_N" ] \
    || die 13 "the run's hunt plan $HUNT_PLAN is corrupt: it records n=$PLAN_N but carries $count artifact paths; re-run the preflight (or the sweep) to discard it"
}

# Has this run already hunted unsharded? Its artifact, every state file its launch, dossier and
# agent left behind, and the plan file's absence are the markers.
hunt_unsharded_state_exists() {
  local f
  for f in "$PHASE2" "$PHASE2.stamp" "$RUN_DIR/hunt.launch" "$RUN_DIR/hunt.binding" \
           "$RUN_DIR/hunt.primary" "$RUN_DIR/hunt.dossier" "$RUN_DIR/hunt.model" \
           "$RUN_DIR/hunt-agent.err" "$RUN_DIR/hunt-agent.log" "$RUN_DIR/hunt-probe.log"; do
    if [ -e "$f" ]; then return 0; fi
  done
  return 1
}

# Validates the invocation against the run's plan and decides whether it is sharded.
shard_plan_validate() {
  if plan_exists; then
    plan_read
    if [ "$SHARD_SET" -eq 0 ] || [ "$SHARD_N" = "1" ]; then
      die 2 "this run's hunt plan records n=$PLAN_N shards; pass --shard K/$PLAN_N (K from 1 to $PLAN_N) to run, dossier or record a shard"
    fi
    [ "$SHARD_N" = "$PLAN_N" ] \
      || die 2 "--shard $SHARD_K/$SHARD_N conflicts with this run's recorded hunt plan n=$PLAN_N; pass --shard K/$PLAN_N"
    SHARDED=1
  elif hunt_unsharded_state_exists; then
    if [ "$SHARD_SET" -eq 1 ] && [ "$SHARD_N" != "1" ]; then
      die 2 "--shard $SHARD_K/$SHARD_N conflicts with this run's unsharded hunt; a sharded plan must start the run's first hunt"
    fi
    SHARDED=0
  else
    if [ "$SHARD_SET" -eq 1 ] && [ "$SHARD_N" != "1" ]; then SHARDED=1; else SHARDED=0; fi
  fi
  if [ "$SHARDED" -eq 1 ]; then SHARD_LABEL=" shard=$SHARD_K/$SHARD_N"; else SHARD_LABEL=""; fi
}

# Records the run's hunt plan on the first sharded invocation; never rewrites an existing plan.
# The plan is published only when it holds one artifact path per shard, so a count the shell cannot
# enumerate is refused instead of leaving a plan no invocation can satisfy.
shard_plan_write() {
  local k tmp written
  [ "$SHARDED" -eq 1 ] || return 0
  plan_exists && return 0
  tmp="$(mktemp -p "$RUN_DIR" hunt.shards.XXXXXX)" || return 1
  {
    printf 'n=%s\n' "$SHARD_N"
    for (( k=1; k <= SHARD_N; k++ )); do printf '%s\n' "$RUN_DIR/phase2-hunt.$k.md"; done
  } > "$tmp" || { rm -f -- "$tmp"; return 1; }
  written="$(tail -n +2 -- "$tmp" | wc -l)"
  if [ "$written" != "$SHARD_N" ]; then rm -f -- "$tmp"; return 1; fi
  mv -fT -- "$tmp" "$HUNT_PLAN" || { rm -f -- "$tmp"; return 1; }
}

# Removes the plan and every shard's artifact and state files, plus the unsharded names.
remove_all_hunt() {
  rm -f -- "$PHASE2" "$PHASE2.stamp" "$RUN_DIR/hunt.launch" "$RUN_DIR/hunt.binding" \
    "$RUN_DIR/hunt.primary" "$RUN_DIR/hunt.dossier" "$RUN_DIR/hunt.model" \
    "$RUN_DIR/hunt-agent.err" "$RUN_DIR/hunt-agent.log" "$HUNT_PLAN" \
    "$RUN_DIR"/phase2-hunt.[0-9]*.md "$RUN_DIR"/phase2-hunt.[0-9]*.md.stamp \
    "$RUN_DIR"/hunt.[0-9]*.launch "$RUN_DIR"/hunt.[0-9]*.binding \
    "$RUN_DIR"/hunt.[0-9]*.primary "$RUN_DIR"/hunt.[0-9]*.dossier \
    "$RUN_DIR"/hunt.[0-9]*.model "$RUN_DIR"/hunt.[0-9]*-agent.err "$RUN_DIR"/hunt.[0-9]*-agent.log \
    "$RUN_DIR"/hunt-probe.log "$RUN_DIR"/hunt.[0-9]*-probe.log
}

artifact_for() {
  case "$1" in
    preflight) echo "$PHASE0" ;;
    sweep) echo "$PHASE1" ;;
    hunt) if [ "$SHARDED" -eq 1 ]; then echo "$RUN_DIR/phase2-hunt.$SHARD_K.md"; else echo "$PHASE2"; fi ;;
    arbitrate) echo "$PHASE3" ;;
    *) die 2 "unknown phase '$1' (sweep|hunt|arbitrate)" ;;
  esac
}
if [ -n "$phase" ]; then
  case "$phase" in sweep|hunt|arbitrate) ;; *) die 2 "unknown phase '$phase' (sweep|hunt|arbitrate)" ;; esac
fi

# Hashed through stdin: sha256sum escapes the digest of a named file whose path holds a backslash or newline.
sha_of() { sha256sum < "$1" | cut -d' ' -f1; }
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
  if [ "$1" = "hunt" ] && [ "$SHARDED" -eq 1 ]; then printf 'shard=%s/%s\n' "$SHARD_K" "$SHARD_N"; fi
  if [ "$1" != "preflight" ]; then printf 'spec=%s\nno_sweep=%s\n' "$SPEC_SHA" "$NO_SWEEP"; fi
  for p in $(deps_of "$1"); do
    dep="$(artifact_for "$p")"
    if [ -f "$dep" ]; then printf 'dep.%s=%s\n' "$p" "$(sha_of "$dep")"; else printf 'dep.%s=missing\n' "$p"; fi
  done
}

# The launch records the exact invocation a dossier was written for where the binding cannot see the
# difference: `--shard 1/1` and an omitted flag are unsharded and share a byte-identical binding
# (AC1's parity clause), so the launch itself carries the flag selection. `shard=none` is the
# omitted flag, so a launch that is missing, empty or unreadable is a state error, never a selection.
launch_text() {  # $1 = phase -> what the launch file records; only the hunt records a selection
  if [ "$1" = "hunt" ]; then
    if [ "$SHARD_SET" -eq 1 ]; then printf 'shard=%s/%s\n' "$SHARD_K" "$SHARD_N"; else printf 'shard=none\n'; fi
  fi
}
shard_choice_label() {  # -> the selection this invocation passes, as the operator wrote it
  if [ "$SHARD_SET" -eq 1 ]; then printf '%s' "--shard $SHARD_K/$SHARD_N"; else printf '%s' "no --shard"; fi
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
  local p k n
  for p in $(deps_of "$1"); do
    if [ "$p" = "hunt" ] && plan_exists; then
      plan_read; n="$PLAN_N"
      for (( k=1; k <= n; k++ )); do
        SHARDED=1; SHARD_K="$k"; SHARD_N="$n"
        accepted hunt \
          || die 13 "the $1 phase needs an accepted hunt shard $k/$n from this run (base ${BASE_SHA:0:12}, head ${HEAD_SHA:0:12}, this spec, same --no-sweep); run hunt --shard $k/$n at this head first."
      done
      SHARDED=0
      continue
    fi
    accepted "$p" || die 13 "the $1 phase needs an accepted $p artifact from this run (base ${BASE_SHA:0:12}, head ${HEAD_SHA:0:12}, this spec, same --no-sweep); run $p at this head first."
  done
}

invalidate_downstream() {  # $1 = phase: a re-run discards every later phase, including one in flight
  local p a
  for p in $(downstream_of "$1"); do
    if [ "$p" = "hunt" ]; then
      # A preflight or sweep re-run discards the whole shard set and its plan.
      remove_all_hunt
      continue
    fi
    a="$(artifact_for "$p")"
    rm -f -- "$a" "$a.stamp" "$RUN_DIR/$p.launch" "$RUN_DIR/$p.binding" "$RUN_DIR/$p.primary" \
      "$RUN_DIR/$p.dossier"
  done
  # Rebuilt whether or not a sidecar was there, so the log never shows a discarded phase.
  write_dossier_sizes
}

# A re-run discards this invocation's own previous output and attempt state before anything can
# fail, so a refused attempt can never leave an older report acceptable.
drop_own_output() {  # $1 = phase
  local art key; art="$(artifact_for "$1")"; key="$(state_key "$1")"
  rm -f -- "$art" "$art.stamp" "$RUN_DIR/$key.dossier" \
    "$RUN_DIR/$key.launch" "$RUN_DIR/$key.binding" "$RUN_DIR/$key.primary"
}

begin_phase() {  # $1 = phase: drop stale output and later phases, bind the inputs, mark the launch time
  local key; key="$(state_key "$1")"
  drop_own_output "$1"
  shard_plan_write || die 2 "could not write the hunt plan $HUNT_PLAN; the $1 phase never started."
  invalidate_downstream "$1"   # also rebuilds the size log, after this phase's own removal
  launch_text "$1" > "$RUN_DIR/$key.launch"
}

bind_phase() {  # $1 = phase: record the inputs its dossier was built from and the primary checkout
  local key; key="$(state_key "$1")"
  binding_text "$1" > "$RUN_DIR/$key.binding"
  primary_state > "$RUN_DIR/$key.primary"
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

# Does an agent's stderr log ($1) show a sandbox start-up error? The log also carries whatever the
# agent echoes while it reads files, specs and diffs (SKL-127), and the skills' own text quotes these
# markers, so this is a line-shape heuristic, not a source identifier. A marker counts only at the
# start of a line or right after a carriage return (a progress line rewritten in place), after
# optional whitespace and terminal escape sequences (CSI, colour included, and OSC), optionally
# followed by one `<word>: ` tool prefix (the word starts with a letter or digit, so a `-`/`+` diff
# line is never read as a prefix) and more whitespace or escape sequences, so `codex: bwrap: `
# trips with or without colour. A marker quoted mid-line does not trip it. Two accepted limits of
# the line shape: (a) a real error wrapped in more than one prefix (a timestamp, a log level,
# `[pid] `, `error: ...: `) is missed; (b) echoed text already in the shape (an indented error
# example, a `Note: ` line, a diff context line) still marks the phase blind, which fails safe:
# the phase is retried. A real wrapper form seen in the wild gets its own bug and fixture.
# Brackets are written as [[] and [\] because \[ and \\ are undefined inside POSIX ERE brackets;
# LC_ALL=C keeps the byte ranges of the CSI grammar locale-independent.
sandbox_error_in() {
  local esc=$'\e' cr=$'\r' bel=$'\a'
  local escseq="(${esc}[[][0-?]*[ -/]*[@-~]|${esc}][^${bel}${esc}]*(${bel}|${esc}[\\]))"
  local gap="([[:space:]]|${escseq})*"
  local lead="(^|${cr})${gap}([[:alnum:]][[:alnum:]_.-]*:[[:space:]]${gap})?"
  LC_ALL=C grep -qiE "${lead}(bwrap: |sandbox (failed|denied|could not)|Failed to make .* Permission denied)" -- "$1"
}

accept_phase() {  # $1 = phase, $2 = stderr log or "": validate a freshly written artifact, then stamp it
  local art key launched launched_arg; art="$(artifact_for "$1")"; key="$(state_key "$1")"
  [ -f "$RUN_DIR/$key.launch" ] && [ -f "$RUN_DIR/$key.binding" ] && [ -f "$RUN_DIR/$key.primary" ] \
    || die 15 "no launch for $1 in this run (never started, discarded by a later re-run of an earlier phase, or an arbitration already accepted); write its dossier with 'dossier $1' first."
  if [ "$(cat -- "$RUN_DIR/$key.binding")" != "$(binding_text "$1")" ]; then
    die 13 "the $1 inputs changed since its dossier was written (spec, --shard, --no-sweep or a predecessor artifact); start the $1 phase again."
  fi
  # `--shard 1/1` and an omitted flag share a binding byte for byte, so the hunt's launch carries the
  # exact selection the dossier was written for: a record must repeat it exactly. The recorded value
  # is printed only after control characters are neutralised, so a tampered marker cannot forge a line.
  if [ "$1" = "hunt" ]; then
    if ! launched="$(cat -- "$RUN_DIR/$key.launch" 2>/dev/null)" || [ -z "$launched" ]; then
      die 15 "the hunt launch marker $RUN_DIR/$key.launch is missing, empty or unreadable; start the hunt phase again."
    fi
    if [ "$launched" != "$(launch_text "$1")" ]; then
      launched_arg="$(printf '%s' "$launched" | tr -c '[:print:]' '?')"
      die 13 "the hunt launch records '$launched_arg' but this record invocation passes '$(shard_choice_label)'; pass the --shard the dossier was written with, or start the hunt phase again."
    fi
  fi
  [ -s "$art" ] || die 15 "the $1 agent produced no report ($art is missing or empty)."
  if [ "$RUN_DIR/$key.launch" -nt "$art" ]; then
    die 15 "$art is older than this $1 launch; it was not written by this run."
  fi
  # A reviewer whose sandbox could not start reads nothing yet may still exit 0: never a false clean.
  # Sandbox errors are looked for only in the agent's own stderr; the report may quote such text.
  if [ -n "$2" ] && [ -f "$2" ] && sandbox_error_in "$2"; then
    die 17 "the $1 agent ran blind (sandbox error on its stderr, see $2); treat this phase as failed, not clean."
  fi
  # The report must positively attest that the review ran.
  local first; first="$(head -n 1 -- "$art" | tr -d '\r' | sed 's/[[:space:]]*$//')"
  if [ "$first" != "REVIEW-RAN: yes" ]; then
    die 17 "the $1 report does not start with 'REVIEW-RAN: yes' (first line: '${first:0:120}'); treat this phase as failed, not clean."
  fi
  # The agent must not have touched the primary checkout.
  if [ "$(primary_state)" != "$(cat -- "$RUN_DIR/$key.primary")" ]; then
    die 18 "the primary checkout ($ROOT) changed while the $1 agent ran; this phase is not accepted. Inspect 'git status' there."
  fi
  if [ "$1" = "arbitrate" ]; then
    stamp_and_retain_arbitration
  else
    stamp "$1"
  fi
}

# Arbitration identity and retention (see "Arbiter identity and retention" in the header). This
# writes the three identity lines after the first line and prepares the stamp, then publishes an
# immutable copy and puts the stamp in place as one step, so a phase is accepted exactly when its
# copy is retained. The launch is consumed for the transaction, so one dossier accepts one
# arbitration and recording it again fails (exit 15). Until publishing starts, any failure or signal
# restores the report as the agent wrote it and the launch, with no stamp, so the phase is not
# accepted and a retried `record` starts from the same report. Once publishing starts, signals are
# ignored (child processes inherit that) for the rest of the transaction, which runs in its own child
# (accept_in_child); a stamp that cannot be put in place removes the copy just published.
# The retained path goes to fd 3, which each caller points at the script's own stderr.
ARBITRATION_ROUNDS="$COMMON_DIR/adversarial-pipeline/arbitration-rounds"
ARB_SIGNALS="INT TERM HUP QUIT USR1 USR2"
ARB_ART="" ARB_LAUNCH="" ARB_CONSUMED="" ARB_ORIGINAL="" ARB_SAVED=0 ARB_HEADED="" ARB_STAMP_NEW=""
arbitration_rollback() {
  local f
  for f in "$ARB_HEADED" "$ARB_STAMP_NEW"; do
    if [ -n "$f" ]; then rm -f -- "$f"; fi
  done
  if [ "$ARB_SAVED" -eq 1 ]; then
    mv -f -- "$ARB_ORIGINAL" "$ARB_ART" || echo "WARNING: could not restore $ARB_ART as the agent wrote it" >&2
  elif [ -n "$ARB_ORIGINAL" ]; then
    rm -f -- "$ARB_ORIGINAL"   # a partial save is never restored over the report
  fi
  if [ -f "$ARB_CONSUMED" ]; then
    mv -f -- "$ARB_CONSUMED" "$ARB_LAUNCH" || echo "WARNING: could not restore the arbitrate launch" >&2
  fi
}
stamp_and_retain_arbitration() {
  local dest
  ARB_ART="$(artifact_for arbitrate)"
  ARB_LAUNCH="$RUN_DIR/arbitrate.launch"
  ARB_CONSUMED="$RUN_DIR/arbitrate.launch.accepting"
  ARB_ORIGINAL="" ARB_SAVED=0 ARB_HEADED="" ARB_STAMP_NEW=""
  # The shared check tolerates trailing whitespace and a CR; the identity block follows a first line
  # that is exactly 'REVIEW-RAN: yes', compared byte for byte (a shell variable would drop a NUL), so
  # anything else fails here, before anything is written.
  if ! head -n 1 -- "$ARB_ART" | cmp -s - <(printf 'REVIEW-RAN: yes\n') \
    && ! cmp -s -- "$ARB_ART" <(printf 'REVIEW-RAN: yes'); then
    die 17 "the arbitrate report's first line is not exactly 'REVIEW-RAN: yes' (trailing whitespace or a CR included); nothing was written or retained, and the phase is not accepted."
  fi
  # From the first change on, a signal rolls the transaction back.
  trap 'arbitration_rollback; exit 130' INT
  trap 'arbitration_rollback; exit 143' TERM
  trap 'arbitration_rollback; exit 129' HUP
  trap 'arbitration_rollback; exit 131' QUIT
  trap 'arbitration_rollback; exit 138' USR1
  trap 'arbitration_rollback; exit 140' USR2
  if ! ARB_ORIGINAL="$(mktemp -p "$RUN_DIR" arbitrate-original.XXXXXX)" \
    || ! cp -p -- "$ARB_ART" "$ARB_ORIGINAL" \
    || ! ARB_SAVED=1 \
    || ! mv -f -- "$ARB_LAUNCH" "$ARB_CONSUMED"; then
    arbitration_rollback
    die 21 "could not save the arbitration report before writing its identity lines; nothing was written or retained."
  fi
  if ! ARB_HEADED="$(mktemp -p "$RUN_DIR" arbitrate-headed.XXXXXX)" \
    || ! { printf 'REVIEW-RAN: yes\nARBITER-AGENT: %s\nARBITER-MODEL: %s\nARBITER-HEAD: %s\n' \
             "${ARBITER_AGENT:-not-supplied}" "${MODEL:-not-supplied}" "$HEAD_SHA" \
           && tail -n +2 -- "$ARB_ART"; } > "$ARB_HEADED" \
    || ! mv -f -- "$ARB_HEADED" "$ARB_ART"; then
    arbitration_rollback
    die 21 "could not write the arbiter identity lines into $ARB_ART; the phase is not accepted."
  fi
  ARB_HEADED=""
  if ! ARB_STAMP_NEW="$(mktemp -p "$RUN_DIR" arbitrate-stamp.XXXXXX)" \
    || ! stamp_text arbitrate > "$ARB_STAMP_NEW"; then
    arbitration_rollback
    die 21 "could not prepare the arbitration stamp; nothing was retained, and the phase is not accepted."
  fi
  # shellcheck disable=SC2086 # the signal list is meant to split
  trap '' $ARB_SIGNALS
  if ! dest="$(retain_arbitration "$ARB_ART")"; then
    arbitration_rollback
    die 21 "could not retain the accepted arbitration report under $ARBITRATION_ROUNDS; the phase is not accepted."
  fi
  # -T: a directory at the stamp path fails here instead of receiving the stamp.
  if ! mv -fT -- "$ARB_STAMP_NEW" "$ARB_ART.stamp"; then
    rm -f -- "$dest" || echo "WARNING: could not remove $dest, published for an arbitration that was not accepted" >&2
    arbitration_rollback
    die 21 "could not put the arbitration stamp in place; the copy published for it was removed, and the phase is not accepted."
  fi
  # Signals stay ignored to the end: the child exits right after this, and the phase is accepted.
  rm -f -- "$ARB_ORIGINAL" "$ARB_CONSUMED"
  printf 'Retained arbitration report -> %s\n' "$dest" >&3
}

# Runs accept_phase in a child and waits for it. A signal this shell receives meanwhile is forwarded
# to the child as TERM, so the child alone decides the outcome (an arbitration not yet publishing rolls
# back; one publishing completes). Returns the child's status, and sets ACCEPT_SIGNAL to the exit code
# of the signal that arrived (empty when none did). The caller reinstalls its own traps afterwards.
ACCEPT_PID="" ACCEPT_SIGNAL="" ACCEPT_INTERRUPTED=0
forward_to_accept() {  # $1 the exit code of the signal received
  ACCEPT_SIGNAL="$1"
  ACCEPT_INTERRUPTED=1
  if [ -n "$ACCEPT_PID" ]; then kill -TERM "$ACCEPT_PID" 2>/dev/null || true; fi
}
accept_in_child() {  # $1 phase, $2 the agent's stderr log or "", $3 the reason file for the child's stderr
  local rc
  ACCEPT_SIGNAL=""
  trap 'forward_to_accept 130' INT
  trap 'forward_to_accept 143' TERM
  trap 'forward_to_accept 129' HUP
  trap 'forward_to_accept 131' QUIT
  trap 'forward_to_accept 138' USR1
  trap 'forward_to_accept 140' USR2
  ( accept_phase "$1" "$2" ) 3>&2 2> "$3" &
  ACCEPT_PID=$!
  # A trapped signal ends `wait` early; wait again until the child's own status is in.
  while :; do
    ACCEPT_INTERRUPTED=0
    rc=0
    wait "$ACCEPT_PID" || rc=$?
    [ "$ACCEPT_INTERRUPTED" -eq 1 ] || break
  done
  ACCEPT_PID=""
  return "$rc"
}

# Publishes an immutable copy of $1 as round-<UTC timestamp>-<HEAD>-<sha12>-<n>.md: written to a
# temporary file in the retention directory, then hard-linked into place, which fails rather than
# overwrites when the name exists; on that failure the next <n> is tried. Prints the published path.
retain_arbitration() {
  local src="$1" ts sha12 tmp dest n=1
  mkdir -p -- "$ARBITRATION_ROUNDS" || return 1
  ts="$(date -u +%Y%m%dT%H%M%SZ)" && [ -n "$ts" ] || return 1
  sha12="$(sha_of "$src" | cut -c1-12)" && [ "${#sha12}" -eq 12 ] || return 1
  tmp="$(mktemp -p "$ARBITRATION_ROUNDS" .round-tmp.XXXXXX)" || return 1
  if ! cat -- "$src" > "$tmp" || ! chmod 0444 -- "$tmp"; then
    rm -f -- "$tmp"
    return 1
  fi
  while :; do
    dest="$ARBITRATION_ROUNDS/round-$ts-$HEAD_SHA-$sha12-$n.md"
    if ln -T -- "$tmp" "$dest" 2>/dev/null; then
      break
    fi
    if [ ! -e "$dest" ] && [ ! -L "$dest" ]; then
      echo "ERROR: could not publish the retained arbitration report as $dest" >&2
      rm -f -- "$tmp"
      return 1
    fi
    n=$(( n + 1 ))
  done
  rm -f -- "$tmp" || echo "WARNING: could not remove the temporary file $tmp" >&2
  printf '%s\n' "$dest"
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

PHASE_ACCEPTED=0  # set once `run` has accepted its phase; a later signal then leaves it accepted
on_signal() {  # $1 exit code: an interrupted gate orphans neither its process group nor its state
  kill_guarded
  if [ "$PHASE_ACCEPTED" -eq 1 ]; then
    printf 'adversarial-pipeline: phase=%s%s interrupted (exit %s) after the phase was accepted; it stays accepted\n' "$phase" "$SHARD_LABEL" "$1" >&2
    exit "$1"
  fi
  printf 'adversarial-pipeline: phase=%s%s interrupted (exit %s); this phase is not accepted\n' "$phase" "$SHARD_LABEL" "$1" >&2
  if [ -n "${phase:-}" ] && [ -n "${RUN_DIR:-}" ] && [ -d "$RUN_DIR" ]; then
    key="$(state_key "$phase")"
    rm -f -- "$RUN_DIR/$key.launch" "$RUN_DIR/$key.binding" "$RUN_DIR/$key.primary" \
      "$(artifact_for "$phase").stamp" 2>/dev/null || true
  fi
  exit "$1"
}

install_run_signal_traps() {  # a `run` attempt's handlers, also reinstalled after accept_in_child
  trap 'on_signal 130' INT
  trap 'on_signal 143' TERM
  trap 'on_signal 129' HUP
  trap 'on_signal 131' QUIT
  trap 'on_signal 138' USR1
  trap 'on_signal 140' USR2
}

progress_line() {  # $1 phase, $2 elapsed seconds: stderr only, never the artifact or the agent's stdout
  printf 'adversarial-pipeline: phase=%s%s elapsed=%ss timeout=%ss model=%s; %s\n' \
    "$1" "$SHARD_LABEL" "$2" "$TIMEOUT" "$MODEL_LABEL" "$availability_state" >&2
}

completion_line() {  # $1 phase, $2 elapsed seconds, $3 the phase's exit status
  printf 'adversarial-pipeline: phase=%s%s complete elapsed=%ss model=%s exit=%s\n' \
    "$1" "$SHARD_LABEL" "$2" "${MODEL_LABEL:-not-supplied}" "$3" >&2
}

# A phase attempt reports completion however it ends, so the elapsed time and the exit status are
# never missing from the evidence. The attempt starts once `run` accepts its agent command, so a
# refusal before it (usage, not a Git repository, a bad base) is the only path with no completion line.
PHASE_START=0
CHECKOUT_PATH=""
COMPLETION_EMITTED=0
DOSSIER_PENDING=0
DOSSIER_WRITTEN=0
on_run_exit() {  # a run attempt's single exit path: report completion, then clean up, keeping the status
  local rc=$?
  set +e
  trap - EXIT
  kill_guarded   # whatever ended the attempt, no guarded child may outlive it
  trap '' INT TERM HUP QUIT USR1 USR2   # the status is reported; a later signal must not rewrite it
  if [ "$DOSSIER_PENDING" -eq 1 ]; then
    # The dossier write failed: the phase never started, so nothing it bound may be accepted later.
    [ "$rc" -ne 0 ] || rc=1
    printf 'ERROR: could not write the %s dossier (exit %s); the phase never started, and its checkout is removed.\n' \
      "$phase" "$rc" >&2
    rm -f -- "$(artifact_for "$phase").stamp" "${dossier:-}" \
      "$RUN_DIR/$(state_key "$phase").launch" "$RUN_DIR/$(state_key "$phase").binding" \
      "$RUN_DIR/$(state_key "$phase").primary"
  fi
  # Measured only now, once the agent can no longer rewrite the dossier, so the record is never stale.
  if [ "$DOSSIER_WRITTEN" -eq 1 ]; then write_size_sidecar "$phase" "$dossier"; fi
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
  local phase_name="$1" code="$2" reason="${3:-}" report="${4:-}" key
  key="$(state_key "$phase_name")"
  printf 'adversarial-pipeline: phase=%s%s exit=%s model=%s\n' "$phase_name" "$SHARD_LABEL" "$code" "${MODEL_LABEL:-not-supplied}" >&2
  if [ -n "$reason" ]; then
    printf 'adversarial-pipeline: phase=%s%s reason: %s\n' "$phase_name" "$SHARD_LABEL" "${reason#ERROR: }" >&2
  fi
  if [ -n "$report" ]; then
    emit_tail "adversarial-pipeline: report tail" "$report"
    return 0
  fi
  emit_tail "adversarial-pipeline: ${key}-agent.err" "$RUN_DIR/${key}-agent.err"
  provider_lines "$RUN_DIR/${key}-agent.err"
  emit_tail "adversarial-pipeline: ${key}-agent.log" "$RUN_DIR/${key}-agent.log"
}

fail_phase() {  # $1 exit code, $2 reason: a failed phase is never acceptable, not even by a later record
  local code="$1" reason="${2:-}" key
  key="$(state_key "$phase")"
  diagnose_phase "$phase" "$code" "$reason"
  rm -f -- "$(artifact_for "$phase").stamp" \
    "$RUN_DIR/$key.launch" "$RUN_DIR/$key.binding" "$RUN_DIR/$key.primary"
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
  out="$RUN_DIR/$(state_key "$phase_name")-probe.log"
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

# The path escape shared by the truncation marker, the size sidecar's `excluded` lines and the
# dossier's EXCLUDED rows, so all three show a path byte-identically. The marker and the sidecar quote a
# path only when it needs it; an EXCLUDED row always quotes (`force`). `read` returns 1 at the end of the
# here-document: that is how it ends, not a failure.
IFS= read -r -d '' PATH_ESCAPE_PY <<'PYEOF' || true
import os
import sys

ESCAPES = {7: b"\\a", 8: b"\\b", 9: b"\\t", 10: b"\\n", 11: b"\\v", 12: b"\\f", 13: b"\\r",
           34: b'\\"', 92: b"\\\\"}


def escape(path, force=False):
    """The path as the marker shows it: raw, unless it holds a quote, backslash or control byte
    (or `force` asks for the quoted form)."""
    if not force and not any(b in (34, 92, 127) or b < 32 for b in path):
        return path
    out = bytearray(b'"')
    for b in path:
        if b in ESCAPES:
            out += ESCAPES[b]
        elif b < 32 or b >= 127:
            out += b"\\%03o" % b
        else:
            out.append(b)
    return bytes(out + b'"')
PYEOF

# The size sidecar's whole record: argv is the dossier path and its `wc -c` output; stdin holds
# NUL-terminated path and reason pairs. Writes the `path=` line (the dossier's absolute path,
# escaped), the `bytes=` line and one `excluded <escaped path> reason=<reason>` line per pair. Any
# failure, a bad byte count or an unwritable stdout included, exits non-zero.
IFS= read -r -d '' SIDECAR_PY <<'PYEOF' || true
size = sys.argv[2].strip()
if not size.isdigit():
    sys.exit("not a byte count: %r" % sys.argv[2])
fields = sys.stdin.buffer.read().split(b"\0")[:-1]
out = sys.stdout.buffer
out.write(b"path=" + escape(os.path.abspath(os.fsencode(sys.argv[1]))) + b"\n")
out.write(b"bytes=" + size.encode() + b"\n")
for path, reason in zip(fields[0::2], fields[1::2]):
    out.write(b"excluded " + escape(path) + b" reason=" + reason + b"\n")
out.flush()
PYEOF

# The EXCLUDED rows of a dossier: stdin holds NUL-terminated path and reason pairs; each becomes one
# `"<escaped path>" | <reason>` line, the path always quoted.
IFS= read -r -d '' EXCLUDED_ROWS_PY <<'PYEOF' || true
fields = sys.stdin.buffer.read().split(b"\0")[:-1]
out = sys.stdout.buffer
for path, reason in zip(fields[0::2], fields[1::2]):
    out.write(escape(path, True) + b" | " + reason + b"\n")
out.flush()
PYEOF

# The per-file splitter: reads one `git diff` on stdin, cuts it at `diff --git` lines and applies the
# cap to each file's section (see "Embedded diff" in the header). It works on bytes, so a section at or
# below the cap leaves it unchanged. argv: the cap in bytes and the phase checkout's path.
IFS= read -r -d '' DIFF_CAP_PY <<'PYEOF' || true
cap = int(sys.argv[1])
checkout = os.fsencode(sys.argv[2])


def size(lines):
    return sum(len(line) for line in lines)


def line_prefix(lines, room):
    """The longest run of whole lines, from the start, that fits in `room` bytes."""
    kept, used = [], 0
    for line in lines:
        if used + len(line) > room:
            break
        kept.append(line)
        used += len(line)
    return kept


def unquote(token):
    """A git C-style quoted token (or an unquoted one) as raw bytes."""
    if not (len(token) >= 2 and token[:1] == b'"' and token[-1:] == b'"'):
        return token
    body, out, i = token[1:-1], bytearray(), 0
    simple = {v[1]: k for k, v in ESCAPES.items()}
    while i < len(body):
        byte = body[i]
        if byte != 92:
            out.append(byte)
            i += 1
        elif body[i + 1:i + 4].isdigit():
            out.append(int(body[i + 1:i + 4], 8) & 0xFF)
            i += 4
        else:   # a named escape; anything git does not emit is kept as the byte after the backslash
            nxt = body[i + 1:i + 2]
            out += bytes([simple.get(nxt[0], nxt[0])]) if nxt else b"\\"
            i += 2
    return bytes(out)


def split_git_line(rest):
    """The a/ and b/ sides of `diff --git <rest>`, raw and without their prefixes."""
    if rest[:1] == b'"':
        end = 1
        while end < len(rest) and rest[end:end + 1] != b'"':
            end += 2 if rest[end:end + 1] == b"\\" else 1
        a_tok, b_tok = rest[:end + 1], rest[end + 2:]
    elif rest[-1:] == b'"' and b' "b/' in rest:
        a_tok, _, b_tok = rest.rpartition(b' "b/')
        b_tok = b'"b/' + b_tok
    else:
        half = (len(rest) - 5) // 2   # `a/P b/P` with one P twice: unquoted paths are symmetric
        if len(rest) == 2 * half + 5 and rest[2 + half:5 + half] == b" b/":
            a_tok, b_tok = rest[:2 + half], rest[3 + half:]
        else:
            a_tok, _, b_tok = rest.partition(b" b/")
            b_tok = b"b/" + b_tok
    return unquote(a_tok)[2:], unquote(b_tok)[2:]


PATH_LINES = (b"rename to ", b"copy to ", b"deleted file mode")


def destination(header):
    """The marker's path from a section's `diff --git` line and its PATH_LINES header lines."""
    a_path, b_path = split_git_line(header[0][len(b"diff --git "):].rstrip(b"\n"))
    for line in header[1:]:
        for prefix in (b"rename to ", b"copy to "):
            if line.startswith(prefix):
                return unquote(line[len(prefix):].rstrip(b"\n"))
        if line.startswith(b"deleted file mode"):
            return a_path
    return b_path


def cap_lines(section):
    """The emitted lines of an over-cap section, given its whole lines up to the first that crosses
    the cap: every decision (whole hunks that fit, a clipped first hunk, a cut header) lies in them."""
    first = next((i for i, line in enumerate(section) if line.startswith(b"@@")), len(section))
    header, hunks = section[:first], []
    for line in section[first:]:
        if line.startswith(b"@@"):
            hunks.append([])
        hunks[-1].append(line)
    if size(header) > cap:
        return line_prefix(header, cap)
    kept = list(header)
    for n, hunk in enumerate(hunks):
        if size(kept) + size(hunk) <= cap:
            kept += hunk
        else:
            if n == 0:
                kept += line_prefix(hunk, cap - size(kept))
            break
    return kept


class Section:
    """One file's section, streamed: it holds at most its first cap + 1 bytes (in whole lines) and
    the few header lines the marker's path needs, then only counts."""

    def __init__(self, first_line):
        self.pending, self.total, self.shown = [], 0, None
        self.header, self.in_header = [first_line], True
        self.add(first_line)

    def add(self, line):
        self.total += len(line)
        if line.startswith(b"@@"):
            self.in_header = False
        elif self.in_header and line.startswith(PATH_LINES):
            self.header.append(line)
        if self.shown is None:
            self.pending.append(line)
            if self.total > cap:
                kept = cap_lines(self.pending)
                out.write(b"".join(kept))
                self.shown, self.pending = size(kept), None

    def finish(self):
        if self.shown is None:
            out.write(b"".join(self.pending))
            return
        out.write(b"<!-- TRUNCATED: " + escape(destination(self.header))
                  + b" (%d/%d bytes)" % (self.shown, self.total)
                  + b" - the full diff of this file is in your checkout at " + checkout + b" -->\n")


out = sys.stdout.buffer
section = None
for line in sys.stdin.buffer:   # binary-mode lines end at b"\n" only, so CR bytes stay in place
    if line.startswith(b"diff --git "):
        if section is not None:
            section.finish()
        section = Section(line)
    elif section is None:
        out.write(line)
    else:
        section.add(line)
if section is not None:
    section.finish()
out.flush()
PYEOF

cap_diff_sections() {  # $1 = the phase's checkout; stdin = one `git diff`, stdout = the capped diff
  python3 -I -c "$PATH_ESCAPE_PY$DIFF_CAP_PY" "$DIFF_CAP_BYTES" "$1"
}

# The size sidecar of a completed dossier write (see "Size sidecars" in the header). The excluded
# paths and reasons are the ones classify_exclusions set for this dossier; the arbitrate dossier
# runs no classification, so it lists none. The record is written whole to a temporary file of this
# invocation's own and renamed into place, so no partial sidecar is ever published and a failure
# removes only that temporary file, never a sidecar another write published. A sidecar that cannot
# be written is warned about on one line; it never fails the phase.
EXCL_PATHS=(); EXCL_REASONS=()
write_size_sidecar() {  # $1 = phase, $2 = the dossier just written
  local key side tmp="" bytes i
  key="$(state_key "$1")"; side="$RUN_DIR/$key.dossier"
  if ! {
    tmp="$(mktemp "$RUN_DIR/$key.dossier.tmp.XXXXXX")" &&
    bytes="$(LC_ALL=C wc -c < "$2")" &&
    for i in "${!EXCL_PATHS[@]}"; do printf '%s\0%s\0' "${EXCL_PATHS[$i]}" "${EXCL_REASONS[$i]}"; done \
      | python3 -I -c "$PATH_ESCAPE_PY$SIDECAR_PY" "$2" "$bytes" > "$tmp" &&
    mv -f -- "$tmp" "$side"
  } 2>/dev/null; then
    [ -z "$tmp" ] || rm -f -- "$tmp" 2>/dev/null || true
    printf 'WARNING: could not write the %s dossier size sidecar %q; the phase is unaffected.\n' "$1" "$side" >&2
    return 0
  fi
  write_dossier_sizes
}

# The size log's text (see "Size log" in the header), built from the sidecars present now into
# DOSSIER_SIZES_TEXT. A sidecar that is not a regular file, cannot be read, or carries no byte count
# of at most 18 digits (so three still sum without overflow) gives no size: that phase reads
# 'not run' and the rest of the log is still rebuilt.
DOSSIER_SIZES_TEXT=""
SIDE_BYTES=""
SIDE_EXCLUDED=()
sidecar_read() {  # $1 = a size sidecar path -> sets SIDE_BYTES and SIDE_EXCLUDED
  local line content
  SIDE_BYTES=""; SIDE_EXCLUDED=()
  if [ -f "$1" ] && content="$(cat -- "$1" 2>/dev/null)"; then
    while IFS= read -r line; do
      case "$line" in
        bytes=*) SIDE_BYTES="${line#bytes=}" ;;
        "excluded "*) SIDE_EXCLUDED+=("$line") ;;
      esac
    done <<< "$content"
  fi
}

dossier_sizes_text() {
  local p side bytes line total=0 complete=1 text="" k n
  for p in sweep hunt arbitrate; do
    if [ "$p" = "sweep" ] && [ "$NO_SWEEP" -eq 1 ]; then
      text+="sweep: absent (--no-sweep)"$'\n'
      continue
    fi
    if [ "$p" = "hunt" ] && plan_exists; then
      plan_read; n="$PLAN_N"
      for (( k=1; k <= n; k++ )); do
        side="$RUN_DIR/hunt.$k.dossier"
        sidecar_read "$side"; bytes="$SIDE_BYTES"
        if ! [[ "$bytes" =~ ^[0-9]{1,18}$ ]]; then
          text+="hunt.$k: not run"$'\n'
          complete=0
          continue
        fi
        text+="hunt.$k: $bytes bytes"$'\n'
        for line in "${SIDE_EXCLUDED[@]}"; do text+="$line"$'\n'; done
        total=$(( total + 10#$bytes ))
      done
      continue
    fi
    side="$RUN_DIR/$p.dossier"
    sidecar_read "$side"; bytes="$SIDE_BYTES"
    if ! [[ "$bytes" =~ ^[0-9]{1,18}$ ]]; then
      text+="$p: not run"$'\n'
      complete=0
      continue
    fi
    text+="$p: $bytes bytes"$'\n'
    for line in "${SIDE_EXCLUDED[@]}"; do text+="$line"$'\n'; done
    total=$(( total + 10#$bytes ))
  done
  if [ "$complete" -eq 1 ]; then text+="total: $total bytes"$'\n'; fi
  DOSSIER_SIZES_TEXT="$text"
}

# Rewrites the size log whole: a temporary file renamed into place, so no partial log is published.
# A log that cannot be written warns once per invocation and never changes an exit status or
# acceptance; `mv -T` refuses to move the record into a directory standing in the log's place.
DOSSIER_SIZES_WARNED=0
write_dossier_sizes() {
  local log="$RUN_DIR/dossier-sizes.md" tmp=""
  if ! {
    dossier_sizes_text &&
    tmp="$(mktemp "$log.tmp.XXXXXX")" &&
    printf '%s' "$DOSSIER_SIZES_TEXT" > "$tmp" &&
    mv -fT -- "$tmp" "$log"
  } 2>/dev/null; then
    [ -z "$tmp" ] || rm -f -- "$tmp" 2>/dev/null || true
    if [ "$DOSSIER_SIZES_WARNED" -eq 0 ]; then
      DOSSIER_SIZES_WARNED=1
      printf 'WARNING: could not write the dossier size log %q; the phase is unaffected.\n' "$log" >&2
    fi
  fi
  return 0
}

# Every dossier names the phase's throwaway checkout and the base, so anything not embedded inline
# (for the arbiter, the whole diff) is readable there with `git diff <base SHA>...HEAD`. The diffstat
# and diff are taken at the pinned HEAD SHA, the commit the checkout holds, never the moving HEAD ref.
# The spec and phase reports may quote marker lines, so the header names the first ones as the run's.
emit_context() {  # $1 = the phase's checkout, $2 = 1 to embed the unified diff, 0 for the diffstat only
  echo "===== RUN (the first BASE:, HEAD: and CHECKOUT: lines below are this run's; read anything not embedded here in your checkout: git diff ${BASE_SHA}...HEAD) ====="
  echo "BASE: ${BASE} ${BASE_SHA}"
  echo "HEAD: ${HEAD_SHA}"
  echo "CHECKOUT: $1"
  echo
  echo "===== STORY / ACCEPTANCE CRITERIA (the scope reference: work outside it is out of scope, not a defect) ====="
  emit_spec
  echo
  echo "===== BLUEPRINT (diffstat and files, ${BASE}...HEAD) ====="
  git diff --stat "$BASE_SHA"..."$HEAD_SHA"
  if [ "$2" -eq 1 ]; then
    classify_exclusions
    if [ "${#EXCL_PATHS[@]}" -gt 0 ]; then
      echo
      echo "===== EXCLUDED (path | reason: generated, vendored or listed files; in the diffstat above, not in the diff below - read them in your checkout) ====="
      local i
      for i in "${!EXCL_PATHS[@]}"; do printf '%s\0%s\0' "${EXCL_PATHS[$i]}" "${EXCL_REASONS[$i]}"; done \
        | python3 -I -c "$PATH_ESCAPE_PY$EXCLUDED_ROWS_PY"
    fi
    echo
    echo "===== DIFF (${BASE}...HEAD) ====="
    # pipefail makes a failing `git diff` (or splitter) fail this pipeline, hence the dossier write.
    # The pinned options keep every section starting at a plain `diff --git a/... b/...` line.
    if [ "${#EXCL_PATHS[@]}" -eq 0 ]; then
      git diff --no-ext-diff --unified=1 --no-color --src-prefix=a/ --dst-prefix=b/ \
        --submodule=short "$BASE_SHA"..."$HEAD_SHA" | cap_diff_sections "$1"
    else
      emit_kept_diff | cap_diff_sections "$1"
    fi
  fi
}

# The embedded diff of the changes classify_exclusions kept, in diff order. Each kept path goes to git
# as an exact pathspec (exact_pathspec), in batches of at most 8192 characters, so a bulk change never
# exceeds the exec argument limit; a rename's two paths always share a batch, so the rename stays
# paired.
emit_kept_diff() {
  local -a spec=() entry=()
  local i p one size budget=8192 used=0
  for i in "${!KEPT_OLD[@]}"; do
    entry=(); size=0
    for p in "${KEPT_OLD[$i]}" "${KEPT_NEW[$i]}"; do
      if [ -z "$p" ]; then continue; fi
      exact_pathspec "$p" one
      entry+=("$one"); size=$((size + ${#one}))
    done
    if [ "${#spec[@]}" -gt 0 ] && [ $((used + size)) -gt "$budget" ]; then
      git diff --no-ext-diff --find-renames --unified=1 --no-color --src-prefix=a/ --dst-prefix=b/ \
        --submodule=short "$BASE_SHA"..."$HEAD_SHA" -- "${spec[@]}"
      spec=(); used=0
    fi
    spec+=("${entry[@]}"); used=$((used + size))
  done
  if [ "${#spec[@]}" -gt 0 ]; then
    git diff --no-ext-diff --find-renames --unified=1 --no-color --src-prefix=a/ --dst-prefix=b/ \
      --submodule=short "$BASE_SHA"..."$HEAD_SHA" -- "${spec[@]}"
  fi
}

# A pathspec matching exactly the path $1, never the paths under it: a plain or literal pathspec also
# matches a directory's contents, so a kept file replaced by a directory (or the reverse) would carry
# excluded files under its name. Glob magic with every glob character escaped, and the last character
# escaped too, so git cannot treat the pattern as a directory prefix. Sets the variable named by $2.
exact_pathspec() {  # $1 = path, $2 = variable to set
  local s="${1%?}" last="${1: -1}"
  s="${s//\\/\\\\}"; s="${s//\*/\\*}"; s="${s//\?/\\?}"; s="${s//\[/\\[}"
  printf -v "$2" ':(top,glob)%s\\%s' "$s" "$last"
}

# The two exclusion arms of the header's "Exclusion" paragraph, both read from HEAD_SHA. Changes are
# enumerated with rename detection, as the embedded diff shows them; a rename with either side
# excluded is excluded whole. Sets EXCL_PATHS and
# EXCL_REASONS, parallel and in diff order, and KEPT_OLD/KEPT_NEW, the kept changes in diff order
# (KEPT_NEW is empty unless the change is a rename). Attributes are checked in an empty bare git dir,
# made without templates and in this repository's object format, that reads this repository's
# object store, so neither the working tree, the repository's info/attributes, core.attributesFile,
# an init template nor the system attributes file can set them.
classify_exclusions() {
  EXCL_PATHS=(); EXCL_REASONS=(); KEPT_OLD=(); KEPT_NEW=()
  local tmp; tmp="$(mktemp -d -p "$SCRATCH" exclusions.XXXXXX)"
  git diff --find-renames --name-status -z "$BASE_SHA"..."$HEAD_SHA" > "$tmp/changes"
  local -a old=() new=() paths=() globs=()
  local status path other name value line
  while IFS= read -r -d '' status && IFS= read -r -d '' path; do
    other=""
    case "$status" in R*|C*) IFS= read -r -d '' other ;; esac
    old+=("$path"); new+=("$other"); paths+=("$path")
    if [ -n "$other" ]; then paths+=("$other"); fi
  done < "$tmp/changes"
  if [ "${#old[@]}" -eq 0 ]; then rm -rf -- "$tmp"; return 0; fi
  local objects format
  objects="$(git rev-parse --path-format=absolute --git-path objects)"
  format="$(git rev-parse --show-object-format)"
  if [ "$(git cat-file -t "${HEAD_SHA}:.adversarial-exclude" 2>/dev/null)" = "blob" ]; then
    git cat-file blob "${HEAD_SHA}:.adversarial-exclude" > "$tmp/list"
    while IFS= read -r line || [ -n "$line" ]; do
      line="${line#"${line%%[![:space:]]*}"}"
      line="${line%"${line##*[![:space:]]}"}"
      if [ -z "$line" ] || [ "${line:0:1}" = "#" ]; then continue; fi
      globs+=("${line#./}")
    done < "$tmp/list"
  fi
  # The repository's object store (GIT_OBJECT_DIRECTORY honoured) is handed over as the attrs dir's
  # own; every other variable that could point git back at this repository is dropped.
  env -u GIT_DIR -u GIT_WORK_TREE -u GIT_COMMON_DIR -u GIT_INDEX_FILE -u GIT_OBJECT_DIRECTORY \
    git init -q --bare --template= --object-format="$format" --initial-branch=attributes "$tmp/attr.git"
  printf '%s\0' "${paths[@]}" \
    | env -u GIT_DIR -u GIT_WORK_TREE -u GIT_COMMON_DIR -u GIT_INDEX_FILE \
        GIT_OBJECT_DIRECTORY="$objects" GIT_ATTR_NOSYSTEM=1 \
        git --git-dir="$tmp/attr.git" -c core.attributesFile=/dev/null \
        check-attr -z --stdin --source="$HEAD_SHA" linguist-generated linguist-vendored > "$tmp/attrs"
  local -A attr=()
  while IFS= read -r -d '' path && IFS= read -r -d '' name && IFS= read -r -d '' value; do
    if [ -z "${attr[$path]:-}" ] && { [ "$value" = "set" ] || [ "$value" = "true" ]; }; then
      attr[$path]="$name"
    fi
  done < "$tmp/attrs"
  rm -rf -- "$tmp"
  local -A why=()
  local reason glob
  for path in "${paths[@]}"; do
    reason="${attr[$path]:-}"
    if [ -z "$reason" ]; then
      for glob in "${globs[@]}"; do
        if [[ "${path#./}" == $glob ]]; then reason="glob:$glob"; break; fi
      done
    fi
    why[$path]="$reason"
  done
  # A rename's other side takes the excluded side's reason, so its hunks cannot carry the content back.
  local i
  for i in "${!old[@]}"; do
    reason="${why[${old[$i]}]}"
    if [ -n "${new[$i]}" ] && [ -z "$reason" ]; then reason="${why[${new[$i]}]}"; fi
    if [ -z "$reason" ]; then
      KEPT_OLD+=("${old[$i]}"); KEPT_NEW+=("${new[$i]}")
      continue
    fi
    for path in "${old[$i]}" "${new[$i]}"; do
      if [ -z "$path" ]; then continue; fi
      EXCL_PATHS+=("$path")
      if [ -n "${why[$path]}" ]; then EXCL_REASONS+=("${why[$path]}"); else EXCL_REASONS+=("$reason"); fi
    done
  done
}

# The review checklist items for this run's changed paths (see "Review checklist" in the header).
checklist_items() {
  local file=".agent-skills/review-checklist.txt" entry tmp line glob item path n=0
  local -a changed=()
  local -A seen=()
  # Read from the base, so a change cannot rewrite the checklist its own review runs against.
  entry="$(git ls-tree "$BASE_SHA" -- "$file")" \
    || die 22 "could not look up $file at the base $BASE_SHA."
  case "$entry" in
    "") return 0 ;;
    "100644 blob "* | "100755 blob "*) ;;
    *) die 22 "$file at the base $BASE_SHA is not a regular file." ;;
  esac
  tmp="$(mktemp -p "$RUN_DIR" checklist.XXXXXX)"
  # --ignore-submodules=none: a repository's diff.ignoreSubmodules must not hide a changed gitlink.
  if ! git diff --no-renames --ignore-submodules=none --name-only -z "$BASE_SHA"..."$HEAD_SHA" > "$tmp"; then
    rm -f -- "$tmp"; die 22 "could not list the paths changed in $BASE_SHA...$HEAD_SHA."
  fi
  while IFS= read -r -d '' path; do changed+=("$path"); done < "$tmp"
  # NUL becomes \001, which bash `read` keeps (it drops NUL silently), so the line can be skipped
  # with a warning; pipefail makes a failing `git cat-file` fail the pipeline.
  if ! git cat-file blob "${BASE_SHA}:${file}" | tr '\000' '\001' > "$tmp"; then
    rm -f -- "$tmp"; die 22 "could not read $file at the base $BASE_SHA."
  fi
  while IFS= read -r line || [ -n "$line" ]; do
    n=$(( n + 1 ))
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    if [ -z "$line" ] || [ "${line:0:1}" = "#" ]; then continue; fi
    case "$line" in *$'\001'*)
      echo "WARNING: $file line $n holds a NUL or \\001 byte; skipped." >&2; continue ;; esac
    glob="${line%% | *}"; glob="${glob%"${glob##*[![:space:]]}"}"
    item="${line#* | }"; item="${item#"${item%%[![:space:]]*}"}"
    case "$line" in *" | "*) ;; *) glob="" ;; esac
    if [ -z "$glob" ] || [ -z "$item" ]; then
      echo "WARNING: $file line $n is not '<bash glob> | <review item>'; skipped." >&2; continue
    fi
    if [ -n "${seen[$item]:-}" ]; then continue; fi
    for path in "${changed[@]}"; do
      if [[ "$path" == $glob ]]; then printf '%s\n' "$item"; seen[$item]=1; break; fi
    done
  done < "$tmp"
  rm -f -- "$tmp"
}

emit_prior() {  # $1 = phase, $2 = text when that phase is intentionally absent (--no-sweep)
  if accepted "$1"; then cat -- "$(artifact_for "$1")"; else echo "$2"; fi
}

write_dossier() {  # $1 = phase, $2 = dossier path, $3 = the phase's checkout (exists already)
  local p="$1" out="$2" co="$3" items item kept dropped
  case "$p" in
    sweep)
      items="$(checklist_items)"
      {
        echo "You are a high-volume adversarial code reviewer doing a FAST FIRST-PASS SWEEP."
        echo "Output ONLY a structured candidate list - no prose, no fixes, no plan. One entry per candidate:"
        echo "- file:line | severity (Critical/High/Medium/Low) | one-line claim | the concrete failure scenario"
        echo "Cover: vulnerability vectors, logic flaws, breaking changes, API/contract mismatches, test gaps, code smells."
        echo "Be exhaustive; volume over precision, and mark speculation as such."
        echo "Do NOT modify any files: the checkout on the CHECKOUT: line below is read-only, for reading code"
        echo "the diff does not show. Never write secrets to files or command arguments."
        echo "The session's scratch directory is ${SESSION_SCRATCH:-$SCRATCH}; keep any artifact you create there."
        echo "The FIRST line of your report must be exactly 'REVIEW-RAN: yes' when you read the diff below; otherwise"
        echo "make it 'REVIEW-RAN: no - <reason>'. A report without that line is treated as a review that did not run."
        echo
        emit_context "$co" 1
        if [ -n "$items" ]; then
          echo
          echo "===== Review checklist (owner-approved items read from the base, for the paths this diff changes: check each one, report a miss as a candidate) ====="
          kept="" dropped=0   # every whole item that fits, in order; one that does not is left out
          while IFS= read -r item; do
            # The cap counts the items joined by newlines: no separator after the last one.
            if [ $(( ${#kept} + ${#item} )) -le "$CHECKLIST_CAP_CHARS" ]; then
              kept+="$item"$'\n'
            else
              dropped=1
            fi
          done <<< "$items"
          if [ -n "$kept" ]; then printf '%s' "$kept" | sed 's/^/- /'; fi
          if [ "$dropped" -eq 1 ]; then
            echo "[checklist truncated at $CHECKLIST_CAP_CHARS characters; 'checklist --base $BASE_SHA' prints every item]"
          fi
        fi
      } > "$out"
      ;;
    hunt)
      {
        echo "You are an empirical adversarial reviewer working in a THROWAWAY checkout of the unfixed head: the"
        echo "one on the CHECKOUT: line below. You may edit files in that checkout to run experiments; never"
        echo "commit, push, or touch any other tree."
        echo "Never write secrets to files or command arguments."
        echo "The session's scratch directory is ${SESSION_SCRATCH:-$SCRATCH}; keep any artifact you create there."
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
        emit_context "$co" 1
      } > "$out"
      ;;
    arbitrate)
      {
        echo "You are the ARBITER for an adversarial code review. You get the diffstat (not the diff), a raw"
        echo "candidate list from a cheap sweep (Phase 1), empirical execution results (Phase 2), and a"
        echo "read-only checkout of the head under review on the CHECKOUT: line below: read the diff there with"
        echo "'git diff ${BASE_SHA}...HEAD', and any file you need. Do not edit, commit or push in it."
        echo "1. Filter hallucinations, false positives and unexploitable edge cases. Weigh the EMPIRICAL"
        echo "   Phase-2 results over Phase-1 theory."
        echo "2. Surface cross-module logic inconsistencies, security bypasses and architectural regressions"
        echo "   the lower tiers missed."
        echo "3. Never invent findings to fill a section. Do not modify files. Never write secrets to files or command arguments."
        echo "The session's scratch directory is ${SESSION_SCRATCH:-$SCRATCH}; keep any artifact you create there."
        echo "4. Prefix a finding with 'pre-existing' (as the first words of its The bug text: 'pre-existing: ...') only when the defect is present at the merge base of BASE and HEAD (not at BASE itself) in code the diff neither changes nor newly calls, imports or exercises; this pre-PR gate has no review-of-record adjudicator yet, so you are the confirming seat here: confirm the tag yourself against the merge base, per the pre-existing rule in references/code-review.md (Handling findings), whose adjudicator re-confirms any such tag at the PR review of record."
        echo "5. Output the final report in EXACTLY this Markdown layout and nothing else, after one first line:"
        echo "   'REVIEW-RAN: yes' when you read the diffstat and both phase results below and this dossier"
        echo "   carries its CHECKOUT: line; otherwise 'REVIEW-RAN: no - <reason>'. A report without that"
        echo "   line is treated as a review that did not run."
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
        emit_context "$co" 0
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
      # Nothing else runs on this path: the phase deadline is spent, so the container is removed and
      # the registration is left for the next checkout's prune (which runs under its own budget).
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
  # Only a registered checkout may be handed out: 'cleanup' refuses any other path, so a checkout
  # whose registration failed is removed here rather than advertised.
  if ! printf '%s\n' "$dir" >> "$REGISTRY"; then
    echo "ERROR: could not register the throwaway checkout in $REGISTRY; it is removed." >&2
    git worktree remove --force -- "$dir" >/dev/null 2>&1 || rm -rf -- "$dir"
    git worktree prune >/dev/null 2>&1 || true
    rmdir -- "$container" 2>/dev/null || true
    return 2
  fi
  printf '%s\n' "$dir"
}

case "$cmd" in
  preflight)
    # Omitted, the option resolves from the profile the skills load (no story key, so the team is
    # profile.tracker.team_key), and off when no profile exists. A profile that cannot be read stops
    # the run after the previous acceptance is discarded, so a failed resolution never leaves it standing.
    rm -f -- "$PHASE0.stamp"
    invalidate_downstream preflight
    if [ "$FULL_SUITE_SET" -eq 0 ]; then
      FULL_SUITE="$(python3 "$SCRIPT_DIR/resolve-full-suite.py" < /dev/null)" \
        || die 2 "--full-suite was omitted and could not be resolved from the profile (see above); pass --full-suite on|off or fix the profile."
      case "$FULL_SUITE" in
        on|off) ;;
        *) die 2 "--full-suite was omitted and the resolver printed $(printf '%q' "$FULL_SUITE"), not on or off." ;;
      esac
    fi
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
      if [ "$FULL_SUITE" = "off" ]; then
        echo "## 2. The suite (full-suite: off, not run)"
        echo "full-suite: off - the suite was not run; pass --full-suite on to run it."
        printf 'full-suite: off\n' > "$SUITE_LOG"
        echo "Suite log: $SUITE_LOG"
      elif [ -z "${TEST_CMD//[[:space:]]/}" ]; then
        echo "## 2. The suite, run in a clean checkout of HEAD"
        echo "SKIPPED - no test command, so NOTHING exercised the committed tree. This is INCOMPLETE, not a pass."
      else
        echo "## 2. The suite, run in a clean checkout of HEAD"
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
      echo "## 3. python3, which the sweep and hunt dossiers need to cap the embedded diff"
      if python3 -I -c '' < /dev/null > /dev/null 2>&1; then
        echo "PASS - python3 runs."
      else
        echo "FAIL - python3 is not runnable here, so no sweep or hunt dossier could be written."
        status=1
      fi
      echo
      echo "## Verdict"
      if [ "$status" -ne 0 ]; then
        echo "FAIL - fix this before spending any model budget."
      elif [ "$suite_ran" -eq 1 ]; then
        echo "PASS - proceed to the sweep and the hunt."
      elif [ "$FULL_SUITE" = "off" ]; then
        echo "PASS (full-suite: off, the suite was not run) - proceed to the sweep and the hunt."
      else
        echo "INCOMPLETE - the tree is clean but the suite did not run. Re-run with a test command."
      fi
    } > "$PHASE0"
    cat -- "$PHASE0"
    echo "Phase 0 (preflight) -> $PHASE0" >&2
    if [ "$status" -ne 0 ]; then exit 1; fi
    if [ "$suite_ran" -eq 0 ] && [ "$FULL_SUITE" != "off" ]; then exit 3; fi
    stamp preflight
    exit 0
    ;;

  dossier)
    if [ -n "$PROBE_CMD" ]; then
      echo "note: the availability check runs in 'run' only; dossier does not probe the model" >&2
    fi
    if [ "$phase" = "hunt" ]; then shard_plan_validate; fi
    require_predecessors "$phase"
    init_scratch
    begin_phase "$phase"
    dossier="$SCRATCH/$(state_key "$phase")-dossier.md"
    # The phase's checkout exists before its dossier, which names it on its CHECKOUT: line.
    # A phase that fails before its dossier path reaches the caller never started: it leaves no
    # launch, binding, partial dossier or checkout behind (set -e included).
    unstart_phase() {
      local key; key="$(state_key "$phase")"
      rm -f -- "$dossier" "$RUN_DIR/$key.launch" "$RUN_DIR/$key.binding" "$RUN_DIR/$key.primary" \
        "$RUN_DIR/$key.dossier"
      write_dossier_sizes
    }
    checkout_rc=0
    checkout="$(make_checkout)" || checkout_rc=$?
    if [ "$checkout_rc" -ne 0 ]; then
      unstart_phase
      die "$checkout_rc" "could not create the throwaway checkout for the $phase phase (status $checkout_rc; see the error above)."
    fi
    # Until the dossier path is delivered on stdout, any exit removes that checkout and unregisters
    # it; on success, 'cleanup' removes it once the phase is recorded.
    DOSSIER_CHECKOUT="$checkout"
    trap 'rc=$?; trap - EXIT; [ "$rc" -ne 0 ] || rc=1
      echo "ERROR: could not write the $phase dossier (exit $rc); the phase never started, and its checkout is removed." >&2
      ( remove_checkout "$DOSSIER_CHECKOUT" ) >/dev/null || echo "WARNING: could not remove checkout $DOSSIER_CHECKOUT (see above)" >&2
      unstart_phase
      exit "$rc"' EXIT
    write_dossier "$phase" "$dossier" "$checkout"
    write_size_sidecar "$phase" "$dossier"
    bind_phase "$phase"
    echo "CHECKOUT: $checkout" >&2
    echo "Work only in that checkout (never the primary checkout); the $phase dossier names it too. Remove it with 'cleanup $checkout' once the phase is recorded." >&2
    shard_hint=""
    if [ "$phase" = "hunt" ]; then shard_hint=" and the same --shard"; fi
    echo "Save the $phase report to $(artifact_for "$phase"), then run 'record $phase' with the same --base, --spec and --no-sweep${shard_hint}." >&2
    printf '%s\n' "$dossier"
    trap - EXIT
    ;;

  record)
    if [ -n "$PROBE_CMD" ]; then
      echo "note: the availability check runs in 'run' only; record does not probe the model" >&2
    fi
    if [ "$phase" = "hunt" ]; then shard_plan_validate; fi
    require_predecessors "$phase"
    rc_accept=0
    reason_file="$(mktemp -p "$RUN_DIR" record-reason.XXXXXX)" \
      || die 2 "could not create a status file in the run directory"
    accept_in_child "$phase" "" "$reason_file" || rc_accept=$?
    # shellcheck disable=SC2086 # the signal list is meant to split
    trap - $ARB_SIGNALS
    if [ "$rc_accept" -ne 0 ] && [ -n "$ACCEPT_SIGNAL" ]; then
      printf 'adversarial-pipeline: interrupted (exit %s); this phase is not accepted\n' "$ACCEPT_SIGNAL" >&2
      rc_accept="$ACCEPT_SIGNAL"
    elif [ -n "$ACCEPT_SIGNAL" ]; then
      printf 'adversarial-pipeline: interrupted (exit %s) after the phase was accepted; it stays accepted\n' "$ACCEPT_SIGNAL" >&2
    fi
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
    if [ "$phase" = "hunt" ]; then shard_plan_validate; fi
    PHASE_START=$SECONDS
    CHECKOUT_PATH=""
    COMPLETION_EMITTED=0
    install_run_signal_traps
    trap on_run_exit EXIT
    # From here the phase attempt is real, so every exit reports completion; a missing predecessor is
    # one of those failures, not a refusal before the attempt starts. The attempt first drops this
    # phase's own previous output, so a refused re-run can never leave an older report acceptable,
    # and only then checks its predecessors, so no launch, binding or plan is written for an attempt
    # that never starts. The primary-checkout baseline is taken before the probe, so a probe that
    # writes into the checkout cannot hide inside it, and stale logs go first: a diagnosis must never
    # show a previous attempt's streams as this attempt's.
    drop_own_output "$phase"
    require_predecessors "$phase"
    begin_phase "$phase"
    bind_phase "$phase"
    out="$(artifact_for "$phase")"
    errlog="$RUN_DIR/$(state_key "$phase")-agent.err"
    agentlog="$RUN_DIR/$(state_key "$phase")-agent.log"
    rm -f -- "$errlog" "$agentlog"
    init_scratch
    dossier="$SCRATCH/$(state_key "$phase")-dossier.md"
    if [ "$SECONDS" -ge "$(( PHASE_START + TIMEOUT ))" ]; then
      fail_phase 19 "the $phase phase was killed by --timeout: the ${TIMEOUT}s phase deadline expired while preparing the run directory (model=$MODEL_LABEL); the phase is a failure, not a clean one."
    fi
    # One deadline for the whole phase, measured from its start: everything that runs under it,
    # the probe and the throwaway checkout included, shares the remaining budget.
    phase_deadline=$(( PHASE_START + TIMEOUT ))
    # The availability check runs before the dossier is built and before any agent command.
    if [ -n "$PROBE_CMD" ]; then
      availability_probe "$phase" "$phase_deadline"
      if [ "$(primary_state)" != "$(cat -- "$RUN_DIR/$(state_key "$phase").primary")" ]; then
        fail_phase 18 "the primary checkout ($ROOT) changed while the availability check for the $phase phase ran; this phase is not accepted. Inspect 'git status' there."
      fi
    fi
    printf 'adversarial-pipeline: phase=%s%s model=%s; %s\n' "$phase" "$SHARD_LABEL" "$MODEL_LABEL" "$availability_state" >&2
    # Every phase gets its own throwaway checkout; no agent ever runs in the primary checkout. It
    # exists before the dossier is written, because the dossier names it on its CHECKOUT: line.
    CHECKOUT_DEADLINE="$phase_deadline"
    checkout_rc=0
    checkout="$(make_checkout)" || checkout_rc=$?
    unset CHECKOUT_DEADLINE
    if [ "$checkout_rc" -eq 124 ]; then
      fail_phase 19 "the $phase phase was killed by --timeout: the ${TIMEOUT}s phase deadline expired while creating the throwaway checkout (model=$MODEL_LABEL); the phase is a failure, not a clean one."
    fi
    if [ "$checkout_rc" -ne 0 ]; then
      fail_phase "$checkout_rc" "could not create the throwaway checkout for the $phase phase (status $checkout_rc; see the error above); the phase never started."
    fi
    CHECKOUT_PATH="$checkout"
    # A failed write exits through on_run_exit (set -e), which reports it and removes the checkout.
    DOSSIER_PENDING=1
    write_dossier "$phase" "$dossier" "$checkout"
    DOSSIER_PENDING=0
    DOSSIER_WRITTEN=1
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
    if [ "$(primary_state)" != "$(cat -- "$RUN_DIR/$(state_key "$phase").primary")" ]; then
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
    accept_in_child "$phase" "$errlog" "$reason_file" || rc_accept=$?
    if [ "$rc_accept" -eq 0 ]; then PHASE_ACCEPTED=1; fi
    install_run_signal_traps
    if [ "$rc_accept" -ne 0 ] && [ -n "$ACCEPT_SIGNAL" ]; then
      rm -f -- "$reason_file"
      on_signal "$ACCEPT_SIGNAL"
    elif [ -n "$ACCEPT_SIGNAL" ]; then
      printf 'adversarial-pipeline: interrupted (exit %s) after the phase was accepted; it stays accepted\n' "$ACCEPT_SIGNAL" >&2
    fi
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
  checklist) checklist_items ;;
  paths)
    printf 'run %s\npreflight %s\nsuite_log %s\nsweep %s\n' \
      "$RUN_DIR" "$PHASE0" "$SUITE_LOG" "$PHASE1"
    if plan_exists; then
      plan_read
      plan_k=1
      while IFS= read -r plan_path; do
        printf 'hunt.%s %s\n' "$plan_k" "$plan_path"
        plan_k=$(( plan_k + 1 ))
      done < <(plan_paths)
    else
      printf 'hunt %s\n' "$PHASE2"
    fi
    printf 'arbitrate %s\ndossier_sizes %s\n' "$PHASE3" "$RUN_DIR/dossier-sizes.md"
    ;;
esac
