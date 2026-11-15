# SKL-312 findings: an evaluation framework and corpus for agent-skills on promptfoo

Labels used throughout:

- **observed**: seen in promptfoo `0.125.1` as installed and run for this spike, either by `bash spikes/SKL-312/poc/run.sh` or by a throwaway eval of a two-line script provider that is not committed.
- **documented**: read on the promptfoo documentation site on 2026-11-15 at the URL given, and not run here.
  The site documents the current release and has no page per version, so each documented name was also looked up in the `0.125.1` build, and the lookup result is stated beside it.
- **absent**: looked for in the `0.125.1` command line help and build, and not found.
- **unverified**: proposed here, with nothing run or read to support it.

## Success criteria

| Criterion | Status | Evidence |
|---|---|---|
| `## Decision` states Go, Partial-Go or No-Go with decider, date, version, commit, observations and reversal conditions | met | `## Decision` |
| `bash spikes/SKL-312/poc/run.sh` replays the recorded runs with zero model API calls and writes `compare.md` and `envelope.json` | met | `poc/compare.md` (24 of 24 records match), `poc/provider-contract/envelope.json` |
| `## Scope` names first skills, behaviours in scope and an out-of-scope list | met | `## Scope` |
| `## Test types` has one row per type with grading method, mechanism and cost per run | met | `## Test types` |
| `## Corpus` proposes sources, format, labels, size target, versioning and private-material exclusion | met | `## Corpus` |
| `## Infrastructure` recommends one runner and covers providers, credentials, storage, ceilings, gating and the Node footprint | met | `## Infrastructure` |
| `## Split` chooses one follow-up shape and defines each item | met | `## Split` |

## Decision

**No-Go for adopting promptfoo now.**
`skills/story-to-done/evals/run-suite.sh` stays the harness for behaviour and regression cases.
For the two test types `run-suite.sh` has no mechanism for, trigger and prose rubric, the evidence is insufficient, and the missing prerequisites are named below.

- Decider: the senior engineer implementing SKL-312, by role.
  The product owner accepts or overturns the decision when closing SKL-312.
- Date: 2026-11-15.
- promptfoo version: `0.125.1`.
- Repository commit tested: `186df218014aeb4ecee41cb2801ab72e4c794063`, where the last commit that changed `skills/story-to-done/evals/` is `192070793c871937e817be1c8f4105af8650a01a`.

Observations that drove it:

1. Grading parity holds.
   All 24 suite run records of `qa-unfinished-own-steps` replay through a promptfoo script provider and the unchanged `grader.py` to the recorded verdict, grade by grade and line by line (`poc/compare.md`, no mismatch).
   So no mismatch prevents adoption; the items below do.
2. Two harness tokens have no promptfoo outcome (`poc/compare.md`, "Unmapped tokens").
   A void run and a broken attempt both become ERROR, and the eval goes on where the suite stops.
   promptfoo has no rule that runs a void attempt again until N graded runs with a cap of 2N attempts; `--retry-errors` is one more pass per invocation.
   Adopting it for agent runs therefore needs a wrapper that re-implements what `suite.py` already does, and the run records and summary the suite writes would have to be rebuilt from promptfoo's export.
3. For a run driven through the script provider, promptfoo sees one opaque call.
   Its matrix, repeat, cache and report features work around that call (observed), and its tool-call assertions do not reach inside it: `trajectory:*` reads trace spans and `skill-used` reads provider metadata, neither of which a script provider returns.
4. The cost of entry is a Node toolchain in a Python repository: 617 packages and 747 MB for one pinned top-level version, with every dependency below it resolved again on each install because no lockfile is committed.
5. No model-graded assertion and no live agent provider was run here.
   Both are documented only, so their verdict stability and cost per run are unmeasured.

Missing prerequisites for the trigger and prose rubric types, one per follow-up spike in `## Split`:

- one observed model-graded rubric run on skill prose at the pinned version, with the agreement between repeats and the cost per call measured;
- one observed live trigger run for one skill at the pinned version, with the way a void run is told from a failed one stated and the cost per run measured.

Conditions that would reverse the decision:

- Both prerequisites are observed and hold: the decision becomes Partial-Go, promptfoo for trigger and prose rubric, `run-suite.sh` for behaviour and regression.
- promptfoo gains a result state distinct from ERROR for a run that produced nothing gradable, and a retry rule bounded by a graded-run count: behaviour and regression are then re-examined for a full Go.
- The owner accepts a committed Node lockfile and a dependency update routine in this repository: observation 4 no longer weighs against adoption.

Alternatives while the decision is No-Go:

| Alternative | Gap it leaves | Cost |
|---|---|---|
| Extend `run-suite.sh` with a trigger case kind and a model-graded grade | No provider matrix and no result viewer; the rubric prompt, its parsing and its calibration are written and maintained here | One story per new kind, in Python, with no new toolchain |
| Keep `run-suite.sh` and add promptfoo for trigger and prose rubric only, after the two spikes | Two harnesses and two result formats; the Node footprint stays | Two spikes of at most 3 days, then one setup story |
| Evaluate a Python-native eval framework instead | Nothing about it is known here: unverified | One further spike of at most 3 days |

## Research questions

### 1. What promptfoo adds over `run-suite.sh`, and what it supports for agent runs

| Capability | Label | Evidence | Value over `run-suite.sh` |
|---|---|---|---|
| Script provider (`exec:`) | observed | `poc/provider-contract/envelope.json`; 24 replays | None by itself: `run-suite.sh` already calls each case's `run.sh` |
| Model and agent providers (`anthropic:claude-agent-sdk`, `opencode:sdk`, `openai:codex-sdk`) | documented | https://www.promptfoo.dev/docs/providers/claude-agent-sdk/ and https://www.promptfoo.dev/docs/providers/opencode-sdk/ ; all three ids are in the `0.125.1` build | A second way to start an agent, not the `opencode run` command the recorded runs used |
| Deterministic assertions (`python`, `contains`) | observed | `poc/grade.py` runs `grader.py`; `contains` in the throwaway eval | A library of ready assertions; the cases' graders already cover their own checks |
| Model-graded assertions (`llm-rubric`) | documented | https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/llm-rubric/ ; the type is in the build | The one grading method `run-suite.sh` lacks |
| Caching | observed | A second eval of the same config made no provider call and marked every response cached | Saves repeated model calls; it must be off for repeat runs of an agent, and `--no-cache` does that (observed) |
| Repeat runs (`--repeat N`) | observed | 2 tests x 2 providers x `--repeat 2` gave 8 results and 8 provider calls | Same as `--runs N`, without the graded-run count |
| Matrix over models and skill versions | observed | Two providers with different `config` values ran every test, and each value reached the script in its options argument | One command for baseline and candidate, where the suite takes one checkout per invocation |
| CI integration | observed and documented | Exit status 100 when a test fails or errors, and `-o` wrote json, csv, html, xml and yaml (observed); the GitHub Action is documented at https://www.promptfoo.dev/docs/integrations/github-action/ and not run | A machine-readable result and a non-zero status; the suite already exits non-zero |
| Viewer (`promptfoo view`) | observed | Started on a local port, it served its page and listed the evals in its local database | A browsable result grid; it reads a local database that is not shared |
| Agentic multi-step runs with tool use | documented, partly supported | Tools are off until `working_dir` is set, then read-only until write and shell tools are enabled (both provider pages above) | Supported for the agent providers; through the script provider promptfoo sees one call |
| Tool-call grading | observed and documented, partly supported | A `python` assertion over the committed `actions.jsonl` (observed, the replay); `trajectory:tool-used`, `trajectory:tool-sequence` and `skill-used` are in the build and documented at https://www.promptfoo.dev/docs/guides/evaluate-coding-agents/ | The built-in types need trace spans or `metadata.skillCalls`, which only the agent providers supply |
| Worktree or sandbox isolation | documented, partly supported | `copy_working_dir` gives each step a fresh copy or git clone, and the guide states that a workspace is not a sandbox; `copy_working_dir` is in the build | For a script provider it is lacking: the script runs in the config directory with promptfoo's own environment (observed), so isolation stays with the case's `run.sh` |
| A void outcome, a graded-run count, stop on a broken attempt | absent | `poc/compare.md`, "Unmapped tokens"; `eval --help` offers only `--retry-errors` | These are what `run-suite.sh` has and promptfoo lacks |

Two behaviours seen in the replay matter to anyone building on it (both observed):

- promptfoo's export replaced each run id, a token of more than 60 letters, digits and hyphens, with `[REDACTED]`, in the variables and in the rendered prompt.
  Shorter values came through unchanged, and the rule behind it was not traced in the source.
  `compare.py` therefore matches results to run ids by test index.
- A failed provider call puts the whole argument list, prompt included, into the error text and the log.
  The case contract keeps the prompt out of argv, so a script provider must be given an id, as here, never prompt text.

### 2. Can a script provider drive the existing agent runs and keep their semantics

| Part | Proven by the replay | Inferred from documentation or source, not run |
|---|---|---|
| Provider invocation (`poc/provider-contract/envelope.json`) | The script receives the rendered prompt, the provider options and the call context as three arguments, with stdin closed, the config directory as working directory and promptfoo's environment; its trimmed stdout is the output and a non-zero status is a provider error | That the same provider can start a live agent through `<case>/run.sh CHECKOUT SCENARIO RUN_DIR`; that a run of up to `EVAL_TIMEOUT` seconds completes under promptfoo's own timeout settings |
| Verdict mapping (`poc/compare.md`, "Verdict mapping") | pass, fail and each further grade map one to one; exit 2 and exit 3 both map to ERROR; `--retry-errors` runs ERROR rows again once | A void by deadline, which no record or probe exercises |
| Grading of committed recorded runs (`poc/compare.md`, "Replayed runs") | 24 of 24 suite run records grade to their recorded verdict with identical grader output | Nothing; 86 runs in records that predate the runner are listed and not replayed, and no parity is claimed for them |

Grading recorded `actions.jsonl` through promptfoo is proven.
Keeping void, graded and retry semantics is not: two tokens are unmapped and need a wrapper.
Driving a live Claude Code or OpenCode run is not proven, because live orchestration was not run in this spike.

Questions 3 to 7 are answered in `## Test types`, `## Corpus`, `## Infrastructure` (5 and 6) and `## Relations`.

## Scope

Skills to evaluate first:

| Skill | Rationale |
|---|---|
| `story-to-done` | It has the only executed eval suite and the only recorded runs, so every new mechanism can be checked against existing verdicts |
| `engineering-workflow` | It is the longest gated procedure and selects one of three paths per run, so a wording change can alter behaviour without any pattern test noticing |
| The `linear-*` filing skills, as one group | Five sibling skills compete for similar requests on their descriptions alone, which is the failure a trigger test exists to catch |

Behaviours in scope, by test-type row:

- trigger: a request loads the skill that covers it and not a sibling.
- behaviour: a behaviour-changing commit moves the measured result of the case written for it.
- regression: a behaviour that passes at both commits keeps passing.
- prose rubric: skill text meets a writing rule that no pattern test can state.

Out of scope:

- Live agent orchestration through promptfoo, authoring cases, and provisioning any runner (proposals only, see `## Split`).
- The eval case for the `spike`, `no-deployment` and `deployed` paths (SKL-273).
- The `cap-reached-third-failed-round` case (SKL-309).
- The rule for override sentences restated in committed eval transcripts, and transcript redaction with it (SKL-310).
- Recording the graded runs of `pending-ruling-not-sent-to-engineer` (SKL-311).
- Any change to `run-suite.sh`, `suite.py` or the case contract.
- promptfoo's red-team features, its hosted sharing and its cloud service.
- Evaluating a consumer's overlay or profile.

## Test types

Prices are list prices in USD per million tokens from https://models.dev/api.json on 2026-11-15: `deepseek/deepseek-v4-pro` 0.66 input and 1.98 output, `deepseek/deepseek-flash` 0.15 input and 0.60 output.
Token counts are assumptions, because the run records hold no token counts: the `story-to-done` skill and one case's text are about 44 KB, taken as 11,000 tokens.

| Type | What it catches | Grading method | promptfoo mechanism | Cost per run | Measured or estimated |
|---|---|---|---|---|---|
| trigger | A skill that does not load for a request it covers, or loads for one a sibling covers | Tool-call assertion on the skill-load call | `skill-used` and `not-skill-used` on an agent provider (documented, in the build, not run); or a script provider with a `python` assertion over the tool-call record (mechanism observed in the replay) | 1 agent run of about 2 model calls; 0.02 USD at `deepseek/deepseek-v4-pro` for 25,000 input and 1,000 output tokens | estimated |
| behaviour | A change that does not move the behaviour it targets: the candidate passes and the baseline fails | Tool-call and message-file assertion by the case's `grader.py` | Script provider plus a `python` assertion that runs `grader.py` (observed); void and retry semantics `not supported` | Grading: 0 model calls, 0 USD, about 0.1 s per run (promptfoo reported 2 s for 24 replayed runs at concurrency 1). Agent run: 0.08 USD at `deepseek/deepseek-v4-pro` for 100,000 input and 5,000 output tokens, bounded at 900 s by `EVAL_TIMEOUT` | grading measured, agent run estimated |
| regression | A later change that breaks a behaviour that passed at both commits | Same as behaviour, on a control scenario or a regression-pin case | Same as behaviour | Same as behaviour | grading measured, agent run estimated |
| prose rubric | Skill text that breaks a writing rule no pattern test can state | Model-graded rubric | `llm-rubric`, with `--grader` naming the grading model (documented, in the build, not run) | 1 model call; 0.002 USD at `deepseek/deepseek-flash` for 12,000 input and 500 output tokens | estimated |

The whole replay command took 19 s and 29 s on two runs, most of it the install (measured).
No benchmark campaign was run.

## Corpus

This spike authors no cases.

- **Sources.**
  Synthetic scenarios written from a skill's own decision points, as the existing cases are.
  One discriminating case per merged story that changes a skill's behaviour, pinned at that story's merge commit and its parent.
  Defects found in real runs, rewritten as synthetic fixtures with invented identifiers; the original transcript is never copied.
  For trigger cases, request sentences written for the purpose, including sentences a sibling skill should take.
- **Format.**
  `case.yaml` is reused.
  Behaviour and regression cases keep the SKL-164 case contract unchanged.
  Trigger and prose rubric cases would use the same file with two further `kind` values; that changes the contract, so it is a proposal for the follow-up spikes to confirm.
- **Labelling fields.**
  The existing ones: `case`, `skill`, `kind`, `baseline` and `candidate` commits, `runtime` (command, model, reasoning effort), `scenarios` with `expectation` and `control`.
  Proposed additions: the test type, the source (synthetic, story regression, defect rewrite), the originating story id, whether the case derives from private material and how it was made synthetic, and for a rubric case the rubric file and its version.
- **Size target.**
  8 cases per first-wave skill: 3 trigger, 3 behaviour, 1 regression pin and 1 prose rubric.
  5 graded repeats per scenario per commit, up from the 3 the suite defaults to.
- **What 5 repeats give.**
  Method: the Wilson score interval for a binomial proportion at 95% confidence.
  The widest half-width at n = 5 is 0.33 (2 or 3 passes of 5); at n = 3 it is 0.37, at n = 10 it is 0.26 and at n = 20 it is 0.20.
  5 passes of 5 give the interval 0.57 to 1.00, and 3 of 3 give 0.44 to 1.00.
  So 5 repeats separate "nearly always" from "about half", and say nothing finer.
  A skill-level rate pooled over 75 runs (15 scenarios at 5 repeats, with 3 scenarios per behaviour or regression case and 1 per trigger case) has a half-width of 0.11.
- **Repeats and flake rate.**
  Assumed flake rate: a scenario that should pass fails 1 run in 10 for reasons unrelated to the change, and the same in reverse.
  Under the current definition (every candidate run passes, every baseline run fails) a truly discriminating scenario is called discriminating with probability 0.9^6 = 0.53 at n = 3 and 0.9^10 = 0.35 at n = 5: more repeats make the all-or-nothing rule worse.
  Under a 4-of-5 rule (candidate passes at least 4 of 5, baseline at most 1 of 5) the probability is 0.919 x 0.919 = 0.84, and a scenario that passes half the time at both commits is called discriminating with probability 0.1875 x 0.1875 = 0.035.
  No variance experiment was run; the flake rate is an assumption, not a measurement.
- **Versioning.**
  A case is pinned by the commit ids in its `case.yaml`.
  Records keep the suite's naming (label, scenario, skill commit, harness commit, attempt) and are never overwritten.
  A changed grader, scenario or rubric records under a new label and the earlier records stay as history.
  Every promptfoo result names the promptfoo version that produced it.
- **Private-derived material.**
  Only synthetic or redacted cases enter this repository, and each case and record passes `uv run --locked python scripts/leak_scan.py --require-private` in the CI `checks` job before merge.
  A case that needs a consumer's real identifiers belongs in that consumer's overlay repository.
  Transcript redaction defers to SKL-310.

## Infrastructure

**Runner: local**, meaning the maintainer's development container, with records committed through a pull request as today.
Deciding constraint: a live run needs an agent runtime that is already signed in and has model access, and that exists only there; with a No-Go there is no case for provisioning anything.

Alternatives:

- CI: fits checks that call no model (the repository tests, and the replay if it is ever wanted there, 19 to 29 s).
  It does not fit live runs: a public repository's pull request checks cannot hand provider credentials to a fork, and one suite run is over a hundred agent runs of up to 900 s each.
- The self-hosted worker that SKL-312 names as the third option: fits scheduled runs once the run count outgrows what a person starts by hand.
  Its capabilities for this are unverified, and provisioning it is out of scope.

Other items:

- **Providers.**
  Agent: the recorded command, `opencode run` with `deepseek/deepseek-v4-pro` (observed in the run records).
  Rubric grading: `deepseek/deepseek-flash` (unverified).
  promptfoo side: the `exec:` script provider (observed); the agent providers (documented).
- **Credentials, by name only.**
  The agent runtime uses its own stored login, or a provider key the caller names in `EVAL_PASS_ENV`, such as `DEEPSEEK_API_KEY`; an attempt gets no other credential (stated in the evals README).
  A promptfoo model-graded assertion would read `DEEPSEEK_API_KEY` or `OPENROUTER_API_KEY` (names found in the build, not exercised), and the Claude agent provider reads `ANTHROPIC_API_KEY` (documented).
  The only CI secret in use is `LEAK_DENYLIST`.
  The replay reads no credential: promptfoo starts under `env -i` (observed, the variable names are in `envelope.json`).
- **Result storage and retention.**
  Run records and suite summaries stay in git, under each case's `results/`, holding only what the grader reads plus the tool-call record (as today).
  promptfoo's database, logs and output files go to a temporary directory outside the repository and are deleted when the command succeeds (observed).
  Trend reporting is the committed summaries compared by label; no dashboard is proposed.
- **Budget.**
  One suite run is one skill at two commits under the size target, with 3 scenarios taken per behaviour or regression case (the existing case has 4).
  Agent runs: (3 behaviour + 1 regression) cases x 3 scenarios x 5 repeats x 2 commits = 120, at 0.08 USD = 9.60 USD.
  Trigger runs: 3 cases x 5 repeats x 2 commits = 30, at 0.02 USD = 0.60 USD.
  Rubric calls: 1 case x 5 repeats x 2 commits = 10, at 0.002 USD = 0.02 USD.
  Expected: 10.22 USD.
  Void retries can double the agent and trigger runs (the 2N cap): 19.20 + 1.20 + 0.02 = 20.42 USD.
  **Per-run ceiling: 25 USD per suite run.**
  **Monthly ceiling: 12 suite runs**, one per first-wave skill per week (3 x 4), so at most 12 x 25 = 300 USD and an expected 12 x 10.22 = 122.64 USD.
  All figures rest on the estimated per-run costs in `## Test types`.
- **Gating rule: advisory pull request comment.**
  The pull request that changes a skill's behaviour carries its suite summary, and reviewers read it; no check blocks on a pass rate, because 5 repeats leave a half-width of up to 0.33.
  Flake policy, with thresholds: a void run is retried up to 2N attempts (existing rule); a scenario passes at a commit with at least 4 of 5 graded passes, fails with at most 1 of 5, and is otherwise reported `inconclusive`; no run is repeated to reach a pass; a scenario inconclusive in two consecutive suite runs has its case revised or retired through a story.
  The 4-of-5 threshold differs from the definition in the evals README, so it is a proposal for the product owner.
- **Node footprint.**
  Pinned version: promptfoo `0.125.1`, which needs Node.js 22.22.0 or later (observed in its package metadata).
  Invocation: `npm install --prefix <temporary directory> --ignore-scripts promptfoo@0.125.1`, then the installed binary by path; no `npx`, no global install, nothing under the repository (observed).
  Supply-chain check and result: `npm audit signatures` on the installed tree reported 617 packages with verified registry signatures and 157 with verified attestations, on every run (observed); the install ran with package scripts disabled and the replay passed (observed); the Socket report for `promptfoo@0.125.1` scored supply chain 69, vulnerability 100, quality 100, maintenance 99 and license 100 on 2026-11-15 (https://socket.dev/npm/package/promptfoo).
  Open risk: no lockfile is committed, so the packages below the pin are resolved again on each install.
  Telemetry and remote sharing: off, through `PROMPTFOO_DISABLE_TELEMETRY=1`, `PROMPTFOO_DISABLE_UPDATE=1`, `PROMPTFOO_DISABLE_SHARING=1`, `PROMPTFOO_DISABLE_REMOTE_GENERATION=1`, `--no-share` and `sharing: false` (observed set in `run.sh`; telemetry and the update check are documented at https://www.promptfoo.dev/docs/configuration/telemetry/ as on unless disabled).

## Split

Chosen: **named additional spikes**, not an epic.
An epic would plan adoption work the decision does not yet support.

| Spike | Question | Done when | Timebox | Depends on |
|---|---|---|---|---|
| Prose rubric through promptfoo | Does a promptfoo model-graded rubric give a stable verdict on one skill's prose at an acceptable cost | A findings file records, for one skill and one rubric at the pinned version, the verdict of each of 5 repeats, the agreement between them, the measured cost per call, and Go or No-Go for the prose rubric type | 2 days | SKL-312 merged |
| Live trigger run through promptfoo | Can promptfoo run a live trigger test for one skill and report which skill loaded, with a void run told apart from a failed one | A findings file records, for one skill with at least one sibling-skill request, the outcome of each run through the script provider and through one documented agent provider, how a void run is detected, the measured cost per run, and Go or No-Go for the trigger type | 3 days | SKL-312 merged |

On a No-Go:

- The current decision is No-Go for adoption now, and both spikes are the prerequisites it names, so both go to Backlog.
- If a spike itself returns No-Go, its test type falls to the first alternative in `## Decision` (extend `run-suite.sh`) and the spike closes with no further promptfoo work for that type.
- If the product owner rules out promptfoo altogether, both spikes are canceled unstarted and the same alternative covers both types.

## Relations

This spike edits and closes none of these stories; every change below is a proposal.

| Story | Disposition | Rationale | Dependency |
|---|---|---|---|
| SKL-164 (suite harness, Done) | unchanged | `run-suite.sh` stays the harness for behaviour and regression; its exit statuses and records are what the replay read | None; both follow-up spikes read its record format |
| SKL-273 (case for the spike, no-deployment and deployed paths) | unchanged | A behaviour case in the SKL-164 layout, which this decision keeps | None on this spike |
| SKL-309 (`cap-reached-third-failed-round` case) | unchanged | Same: a behaviour case recorded through `run-suite.sh` | None on this spike |
| SKL-310 (override sentence in eval transcripts, Done) | reuse | Its rule for committed eval transcripts applies as it stands to any record a later promptfoo-driven case commits, and `## Corpus` defers transcript redaction to it | None |
| SKL-311 (recording the pending-ruling case) | unchanged | It records through `run-suite.sh`; its records, once merged, are further input the replay could read with no change to that story | None on this spike |

## Guard results

Pinned `skills-ref` reference, resolved from `.github/workflows/ci.yml`: `git+https://github.com/agentskills/agentskills@69ef37e9424c0a7ea9dd2293b559e43ec8176379#subdirectory=skills-ref`.

| Guard | Command | Where it ran | Exit status |
|---|---|---|---|
| 1 | `uv run --locked pytest -q` | locally | 0 |
| 2 | `uv run --locked python scripts/leak_scan.py --require-private` | the `checks` job of the `ci` workflow | 0 |
| 3 | `uvx --from "<pinned reference>" skills-ref validate "$d"` for each of the 18 `skills/*/` directories | locally | 0 for each |
| 4 | `bash scripts/smoke-opencode.sh` | locally | 0 |

- Guard 2 needs the private patterns, which exist only as the CI secret `LEAK_DENYLIST`.
  Run locally, the command exits 2 with `INCOMPLETE` because no private pattern is loaded, so its status above is the CI one.
  The public patterns alone, `uv run --locked python scripts/leak_scan.py`, exit 0 locally.
- The `ci` workflow runs guards 1, 2 and 3 in its `checks` job and guard 4 in its `discovery` job on every pull request head, the merged one included.
- No guard rejected a spike file, and no exemption entry was added: no tracked file outside `spikes/SKL-312/` changed.
- One normalization was made before any guard ran.
  SKL-312 names the third runner option by its host name, and `## Infrastructure` calls it "the self-hosted worker", because a consumer's host name does not belong in the public base repository.
- Had a guard with no scoped exemption mechanism rejected a spike file that could not be normalized, the fallback was to leave that content out of the repository and mark the criterion blocked.
