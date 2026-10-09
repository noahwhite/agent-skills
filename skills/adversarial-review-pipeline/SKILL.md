---
name: adversarial-review-pipeline
description: >-
  Run the pre-PR adversarial code-review gate: a deterministic preflight (clean tree, suite green in a
  detached worktree at HEAD), a cheap whole-diff sweep, an empirical verify-and-hunt pass that
  mutates and runs code in a throwaway worktree, one bounded arbitration by a strong reviewer, then
  fix and one bounded re-verify. Use on every pre-PR review, and when asked to run the adversarial
  gate, the pre-PR pipeline, or the sweep, hunt and arbitrate review. The two-lens loop in
  engineering-workflow is its escalation path, not an alternative.
license: Apache-2.0
compatibility: Requires git, bash and the CLIs of the agents configured for each review role.
---

# Pre-PR adversarial gate (sweep, hunt, arbitrate)

The gate every change runs before a PR exists.
It breaks single-model self-validation bias by tiering the work by cost, and it front-loads the two cheapest things that catch the most: a deterministic check that needs no model, and an adversary that mutates and runs code.

Read [references/profile.md](references/profile.md) first, then the overlay for this skill if `profile.overlays` names one.
[references/runtimes.md](references/runtimes.md) maps "spawn a subagent", "scratch directory" and shell-launched agents to your runtime.
Review-of-record rules live in [references/code-review.md](references/code-review.md); credential rules in [references/secrets.md](references/secrets.md); diagnosis and fix discipline in [references/engineering-practice.md](references/engineering-practice.md).

This is the only default pre-PR gate.
Do not alternate it with another gate shape across stories: alternating architectures makes results incomparable and leaves each shape's blind spots open for a full cycle.

## Roles and models

Every model comes from the profile; never substitute one.
If a configured agent cannot run on this runtime, stop and say so (see `references/runtimes.md`, Models).

| Phase | Agent | Job | Why this tier |
|---|---|---|---|
| 0 Preflight | none (deterministic) | Clean tree, every intended file committed, suite green in a detached worktree at HEAD | Free, seconds, catches a class no reviewer should spend tokens on |
| 1 Sweep | `profile.review.pre_pr.sweeper` | Read the whole diff, emit a raw candidate list with `file:line` and a concrete failure scenario | Large context at the lowest price; volume over precision |
| 2 Verify and hunt | `profile.review.pre_pr.hunter` | For each candidate: mutate, run, report VERIFIED or REFUTED with the command and result; then hunt open-ended for new defects | The only phase that proves rather than asserts |
| 3 Arbitrate | `profile.review.pre_pr.arbiter` | Filter false positives, weigh empirical evidence over theory, catch cross-module regressions, name accepted risks, decide converged or not | Strongest reasoning, spent once on a pre-filtered bundle |
| 4 Fix and re-verify | the implementing agent | Fix in-scope findings, re-run each proving mutant (it must now fail), one bounded re-verify | Closes the loop without unbounded ping-pong |

The sweep is configurable: if `profile.review.pre_pr.sweeper` is unset, record "sweep: not configured" and run Phase 2 as hunt only.
The hunter and the arbiter are required; if either is unset, the gate is blocked on it.
The arbiter must be a different agent from the implementing agent.

Phase 1 output is never the deliverable.
Phase 2 is evidence.
Phase 3 is the report the gate is judged on.

## Ordering rule (do not violate)

**Phase 2 runs before any fix.**
Once you start fixing, Phase 2 reviews a moved head: its REFUTED verdicts become artifacts of your own edits rather than an assessment of the diff, and the evidence is wasted.
Sweep, verify, arbitrate, then fix.

## The helper script

[scripts/run-adversarial-pipeline.sh](scripts/run-adversarial-pipeline.sh) runs the preflight and launches each model phase generically.
Its header documents every option and exit code.

Invoke it by its installed absolute path, with the current directory in the repository under review.
`$PIPELINE` in the examples below stands for `<skill dir>/scripts/run-adversarial-pipeline.sh`, where `<skill dir>` is the absolute directory your runtime loaded this skill from; the consumer repository does not contain the script.
The script reviews the repository of the current directory, or the one `--repo <dir>` names; it never uses its own location, and it refuses to run in the skills repository itself unless `--repo` names that repository.

Every phase belongs to one run, keyed by the base and head commit SHAs, under `git rev-parse --git-path adversarial-pipeline` (worktree-safe); `paths --base "$BASE"` prints the run's artifact paths.

- Each phase deletes its previous artifact before it launches, and accepts only a non-empty report written after that launch whose first line is `REVIEW-RAN: yes`.
  It then stamps the report with the sha256 of the report, of the spec, and of every predecessor artifact its dossier was built from.
- Each phase refuses to start (exit 13) unless its predecessors are accepted for the same run and the same spec: the sweep needs a PASS preflight, the hunt needs the sweep, and arbitration needs the sweep and the hunt.
  With no sweeper configured, pass `--no-sweep` to the hunt and to arbitration alike.
- A phase's inputs (the spec, `--no-sweep`, and each predecessor artifact) are bound when its dossier is written; a report whose inputs changed since then is refused (exit 13).
- Re-running a phase, or the preflight, discards every later phase, including a report still in flight (its `record` then exits 15), so arbitration never pairs a new sweep with an old hunt.
- A new commit is a new run: every phase starts again from the preflight.
- Every model phase runs in its own throwaway detached worktree at HEAD, which is also the command's working directory; no agent runs in the primary checkout.
  A tripwire compares the primary checkout before and after each agent: HEAD, tracked and untracked status, the diff, the shared git config, and the hooks directory (the default one and any `core.hooksPath`); any change fails the phase (exit 18).
  It does not see ignored files or edits to files that were already untracked, so it is a tripwire, not a boundary: the agent's sandbox is the boundary (see `references/runtimes.md`).

Common inputs:

- `--base origin/<integration branch>`, the integration branch being `profile.git.integration_branch`, after `git fetch origin <integration branch>`.
  A local branch of that name is usually stale and would hand reviewers the whole merged delta.
  Every command except `cleanup` needs it.
- `--spec <file>`: the story text and acceptance criteria, so reviewers can reject out-of-scope work as a category.
  Write it to the scratch directory.
  A `--spec` naming a missing file is an error; only omitting it gives the "judge scope from the diff alone" fallback.
- `--test-cmd`: `profile.project.test_command`; `--test-dir` when the suite must run from a subdirectory.

Launching a phase depends on the profile agent's `runtime`:

- `command`, `codex` or `opencode`: build a command template from the agent definition and pass it as `--agent-cmd` to `run <phase>`.
  Placeholders: `{prompt_file}` (the dossier), `{output_file}` (the artifact), `{checkout}` (the phase's throwaway worktree).
  The command's stdin is the dossier.
  For `runtime: command`, the agent's `command` already is the template.
  For `runtime: codex`, read the prompt from stdin with `-`: `codex exec -m <model> -s read-only --cd {checkout} -o {output_file} -` for the sweep and arbitration; the hunter writes in its checkout, so it uses `codex exec -m <model> -s workspace-write --cd {checkout} -o {output_file} -`.
  Never default to `-s danger-full-access`; see the hunt phase for when it is allowed.
  For `runtime: opencode`, run it non-interactively with the agent's model and a short instruction to read `{prompt_file}` with its file tools and output only the report.
- A subagent runtime (`claude-code`, or the runtime you are in): run `dossier <phase>` to write the dossier and print its path.
  Also run `checkout --base "$BASE"` for a throwaway worktree, for every phase.
  Spawn a clean, neutral subagent (a fresh context whose whole brief is the dossier) with the agent's model, tell it to read the dossier and work only in that checkout, and save its final report to the phase's artifact path (`paths` prints them).
  Then run `record <phase>` with the same `--base`, `--spec` and `--no-sweep` as the dossier.
  It accepts the report only if it is non-empty, newer than the dossier, starts with `REVIEW-RAN: yes`, its inputs still match the dossier's, and the tripwire saw no change to the primary checkout since the dossier was written.
  Remove the checkout with `cleanup <path>`; it removes only a checkout the script created and registered, and refuses any other path.

Never put the dossier's contents in argv: argv is visible to other processes, and one argument is capped at 128 KiB, which a real diff exceeds.
Give it to the agent on stdin or as a path it reads.
Every dossier asks for a first line of `REVIEW-RAN: yes`, or `REVIEW-RAN: no - <reason>` when the agent could not read or run what it needed; keep that instruction in any prompt you write yourself.
Every prompt the script writes tells the agent never to write secrets to files or command arguments; keep that line in any prompt you write yourself.

## Phase 0: preflight (deterministic)

Set these once, in the consumer repository, before Phase 0:

```bash
PIPELINE="<skill dir>/scripts/run-adversarial-pipeline.sh"   # absolute path the runtime loaded this skill from
BASE="origin/<profile.git.integration_branch>"              # after: git fetch origin <profile.git.integration_branch>
SPEC="<scratch dir>/spec.md"                                # the story text and acceptance criteria, written first
```

```bash
"$PIPELINE" preflight --base "$BASE" --test-cmd "<profile.project.test_command>"
```

It asserts the working tree is clean (`git status --porcelain --untracked-files=all` empty), creates a detached worktree at `HEAD`, and runs the suite there.
A detached worktree, not an archive export, so tests that shell out to git still work.
Exit codes: 0 PASS, 1 FAIL (dirty tree or suite failed), 3 INCOMPLETE (clean tree but no test command: not a pass).
Any other failure while writing the report exits non-zero rather than passing.

- The suite's exit status is that of its last command, so chain a sequence with `&&` or use one self-checking wrapper.
- The test dir must stay inside the checkout; the script refuses a path that escapes it.
- A SIGKILL cannot be trapped and can leave the temp worktree registered; recover with `git worktree prune`.

A dirty tree is a real finding: a branch whose own contract test passes only against uncommitted files would fail its own CI.
Fix a FAIL before spending any model budget.

## Phase 1: sweep

```bash
"$PIPELINE" run sweep --base "$BASE" --spec "$SPEC" --agent-cmd "<template>"
```

The sweeper returns a structured candidate list, each entry with `file:line`, a severity, a one-line claim and a concrete failure scenario.
Expect false positives; Phase 2 exists to remove them.

## Phase 2: verify and hunt

```bash
"$PIPELINE" run hunt --base "$BASE" --spec "$SPEC" --agent-cmd "<template>"
```

The hunter works in a throwaway detached worktree of the **unfixed** head, never the working tree.
Its dossier asks for both jobs and demands execution rather than reasoning:

1. **Verify**: for each Phase-1 candidate, write and run a minimal adversarial check (mutate, run the suite, revert) and report VERIFIED with the exact command and observed result, or REFUTED with the observation that disproves it.
2. **Hunt** open-ended for defects the sweep missed: a change that applies wrongly, a gate that acts in the wrong environment, a test that passes vacuously, a regression to shipped behaviour.
   Mutate to prove each.

- A hunter whose sandbox could not start reads nothing yet may exit 0.
  A sandbox or permission error on the agent's stderr, or a report whose first line is not `REVIEW-RAN: yes`, is a failed phase, never a clean one (the script exits 17).
  The report itself may quote such error text; only stderr is searched for it.
- If the reviewer's own sandbox cannot start on this host (for Codex, its bwrap sandbox), that reviewer is unavailable: stop and say so.
  The one exception is an operator who confirms an outer sandbox, such as a disposable container or VM; only then may it run with `-s danger-full-access`.
  The throwaway worktree is not a sandbox and never justifies that flag.
- Keep at most one invocation of a given CLI reviewer in flight per session, including across the pre-PR gate and the PR review; shared auth and daemons contend.
  When other sessions on the host use the same CLI, give each invocation its own config home seeded with a copy of the login, per `references/code-review.md`.

## Phase 3: arbitration

```bash
"$PIPELINE" run arbitrate --base "$BASE" --spec "$SPEC" --agent-cmd "<template>"
```

The arbiter filters hallucinations and unexploitable edge cases, weighs Phase-2 empirical results over Phase-1 theory, surfaces cross-module and architectural regressions, writes the report, and states which categories it found clean.
Its output is the gate's deliverable.
Record the arbiter's agent name and model at the top of the report.

## Phase 4: fix, prove the mutants, one bounded re-verify

1. Fix the in-scope findings (see the scope guard below).
2. **Prove each fix**: re-run the exact mutation Phase 2 used to prove the finding.
   It must now fail.
   A fix without a re-run mutant is an assertion, not evidence.
3. Run Phase 0 again on the new head.
4. **One** re-verify round is allowed when the fixes were non-trivial or touched review-relevant code: the reviewers see the new head and findings are adjudicated the same way.
   More than one is the escalation below, not more rounds of this gate.

## Escalation: the two-lens loop

Escalate to the loop in `engineering-workflow` (its step 4, capped at 2 rounds) only when:

- the re-verify round finds a new Critical or High, or
- the diff is security-, migration-, concurrency- or deploy-path-shaped, or
- this gate hit its bound with unresolved Critical or High findings.

Never run the loop and this gate over the same head; that is duplicate spend.

## Scope guard on fixes

Reviewers report findings about code your diff only consumes (another component's endpoint, a shared library, another story's surface).
Those are follow-ups to file or flag, not work for this PR.
Fix only what this diff's own behaviour depends on, and write the rest down in the PR body as accepted or deferred.

## Final report format (the arbiter's output)

### Critical vulnerabilities and breaking bugs

Only items validated by Phase-2 execution or confirmed by the arbiter's reasoning.

- **File/Line:** `path/to/file.ext:line`
- **The bug:** concise description.
- **Empirical evidence:** the failing test log or exact logic trace.
- **Remediation:** the suggested patch.

### Optimizations and code smells

Lower-priority cleanups, performance and architectural adjustments.
Each Medium or Low is adjudicated: fixed, or explicitly accepted with a reason (the report lists the accepted risks).

### Verified safe modules

Which parts of the diff were attacked and stood up, plus an explicit statement of the categories found clean.

## Guardrails

- No fixes before Phase 2.
- Reviewers are read-only against the working tree: the hunter writes only in its throwaway checkout, and neither the hunter nor the arbiter edits the branch.
  Only the implementing agent commits.
- Do not trust a finding's label: Phase 2 disproves Phase 1's guesses, Phase 3 disproves Phase 2's false alarms, and the re-run mutants disprove your own fixes.
- Verdicts are per finding, not a score: report exactly what was attacked and what survived.
- Never use review output as proof that tests pass; run the tests.
- This gate is not the review of record.
  Never merge on this report: the PR still needs CI and the reviewer and adjudicator gate in `references/code-review.md`, and the pre-PR hunter run never counts as the PR review.
