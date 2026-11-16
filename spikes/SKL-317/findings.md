# SKL-317 findings: a live behaviour run through promptfoo with the void retry in the script provider

- promptfoo version: `0.125.1`.
- Model id of the live runs: `deepseek/deepseek-v4-pro`.
- Graded runs wanted, N: 3, with at most 2N = 6 attempts.
- Live run of the final `run.sh`: one invocation of `bash spikes/SKL-317/poc/run.sh` on 2026-11-16 at commit `e653f377aca8fe9f0f84c6ba20fec72bd1966980`, exit status 0; its report is `poc/compare.md`.
- Earlier live runs: three invocations of the same command on 2026-11-16, at commits `50893a214a8dfab55995737895d26bd30a292fc3`, `327ac853822bacbf5e775f59f1a43af18364c15e` and `c8574c3c3eb5e005b3fa38e0d0e26c93744cb42d`, each with exit status 0, of the scripts as they were before each of two pre-PR review rounds and the review of the pull request changed them.
  The final run's report replaced theirs, and their rows are in `## Research questions`, 4.
- Measured total spend of the four live runs: 0.218164716 + 0.333814448 + 0.232140172 + 0.367639888 = 1.151759224 USD.

Labels used throughout:

- **live**: seen in the live invocation of the final `run.sh`, and written in `poc/compare.md` by that invocation.
- **earlier live run**: seen in one of the three earlier invocations.
  Each is reported for its attempt rows and its spend, and no status in this file rests on either.
- **stub, not live**: seen in a dry run of the final `run.sh`, the same promptfoo build and the case's own `run.sh` and `grader.py`, with a stub agent in place of the model.
  A stub run calls no model, spends nothing and writes no file in the repository, and it never counts as a live observation.
  The stub runs cited here ran at commit `0f2b36f948e87d1a3e1ff66fc6203614a38dfaf0`, whose scripts are the ones the live run ran.
- **observed**, **documented**, **absent**: defined in `## Capability re-check`.

## Decision

**Behaviour test type: Inconclusive.**
**Regression test type: Inconclusive.**

The behaviour decision is Inconclusive because the live run did not exercise rule (ii) or rule (iii) of `suite.py` and saw no natural void.
Each is a gap of this spike's method, and the story records a rule the run did not exercise as Inconclusive with the gap named.
Everything the live run did exercise matched the suite, and the observations below list it.
Neither decision is a decision to adopt promptfoo: SKL-312's No-Go on adopting it now rests on more than a live run, and the owner decides that.

- Decider: the senior-engineer agent that implemented SKL-317.
  The decision stands when the product owner accepts it by closing the story, and that owner can overturn it.
- Date: 2026-11-16.
- Repository commit tested: `e653f377aca8fe9f0f84c6ba20fec72bd1966980`.

Observations that drove the behaviour decision:

1. The live run ended with N graded results and exit status 0.
   Attempts 1, 3 and 4 are graded passes by the unmodified `grader.py`, and promptfoo holds 3 successes and no error (`poc/compare.md`, "Attempts" rows 1, 3 and 4, and "Provider calls" rows 1 to 3).
2. The provider absorbed a void and promptfoo never saw it.
   Attempt 2 is a void with exit status 2 that promptfoo did not report, and the same provider call went on to attempt 3 (`poc/compare.md`, "Attempts" row 2, and "Suite rules" row (i), `reproduced`).
   The void was `injected`, so this is not a natural observation.
   promptfoo has no void outcome of its own (`## Capability re-check`, row 19), so the absorbing is all in the provider.
3. promptfoo called the provider once per repeat and repeated no call.
   The run made 3 provider calls for `--repeat 3` at concurrency 1 with no retry flag (`poc/compare.md`, "Provider calls"; `## Capability re-check`, rows 8 and 19).
   The provider's count of attempts across calls therefore held the cap of 2N for the whole run.
4. promptfoo saw one opaque call per repeat, with no usage.
   Every result it holds has `tokenUsage.total` 0 and `cost` 0 (`poc/compare.md`, "Attempts", the column "What promptfoo reported").
   The token counts and costs in that table come from the agent's own session export, read by the provider.
   The attempt record, the spend ledger and the suite-rule report are therefore the provider's and the report writer's work, and promptfoo adds the repeat loop, the assertion call, the export and the exit status.
5. The cost of entry is the Node install measured in `## Infrastructure data`: 617 packages and 747M, with one signature check that exits 0 (rows "Package count", "Size on disk" and "Supply-chain check").
6. Rules (ii) and (iii) were not exercised (`poc/compare.md`, "Suite rules" rows (ii) and (iii), `not exercised in this run`).
   This observation alone makes the decision Inconclusive.

The gaps that make the behaviour decision Inconclusive.
Each is an open question, and none is counted as reproduced:

- Rule (ii), the run stops at 2N attempts, is `not exercised in this run`: the live run ended after 4 attempts (`poc/compare.md`, "Suite rules" row (ii)).
- Rule (iii), any other exit status stops the run, is `not exercised in this run`: no live attempt exited outside 0, 1 and 2 (`poc/compare.md`, "Suite rules" row (iii)).
- No natural void was seen: the one void was injected and ran no agent.

Two more things the live run did not show:

- No live attempt was a graded fail, so promptfoo reporting a live graded fail was not seen.
- The longest attempt of the live run took 449 seconds, and the longest of the earlier live runs 559 seconds.
  An attempt that runs to its deadline, `EVAL_TIMEOUT` plus `EVAL_GRADING_MARGIN`, 1200 seconds by default, was not seen.

The three earlier live runs had the same shape, 3 graded passes from 4 attempts with the injected void second, so they close none of these.
Stub runs, not live, exercised rule (ii), rule (iii) and a graded fail, and are described in `## Research questions`, 1 and 2.
They do not change any status above.

What the grade and the spend of the live run rest on:

- The agent under test runs as the same OS user as the harness, with no sandbox around it.
  Every check of the grade and of the spend is therefore one an agent that follows its prompt passes, not a barrier against one that sets out to defeat it (`poc/README.md`, "What the checks do not cover").
- The checks are these: the case's `run.sh` and `grader.py` run from a harness clone the agent is not told of, the provider compares that clone and the agent's clone with the commit's tree by content before and after each attempt, and it compares the ledger with its own copy and with a length and hash `run.sh` took before the eval.
  In the live run every one held, and `poc/compare.md` lists no blocker.
- Not stopped: an agent that changes a file and restores it between two checks, one that rewrites the harness's own files, one that rewrites the session record `opencode` keeps, and one that writes the case's `actions.jsonl` itself.
  The last is the case as committed, and `suite.py` runs the same case with the same limit, so the limit does not tell the two harnesses apart and changes neither decision.
- A process sandbox is possible on the machine of the live run and is not part of the PoC.
  Probed there on 2026-11-16, outside the PoC and with util-linux 2.39.3: `unshare -r -m`, a `tmpfs` mounted over a directory, then a nested `unshare -U -m --map-user=1000 --map-group=1000` gave a child process that saw the directory empty, could not unmount it or mount anything, and could not read the environment of the process that started it.
  The same probe failed inside the sandbox the review's own agent runs in, and which paths to hide is a question of its own, so the defence is left to SKL-326 (Follow-up work, below).

Conditions that would reverse the behaviour decision, as observations:

- To Go: a live run whose `compare.md` marks rules (ii) and (iii) `reproduced`, and a live run in which a void that was not injected is absorbed and not counted toward N.
- To Partial-Go: a live run whose `compare.md` marks rules (ii) and (iii) `reproduced`, while no natural void has been seen.
- To No-Go: a `compare.md` that marks any rule `differs`.
- To No-Go: promptfoo makes more provider calls than repeats when `--retry-errors` is not passed, or runs two calls at once at `--max-concurrency 1`, because the cap of 2N then no longer holds across the run.
- To No-Go: promptfoo ends a provider call before the case's `run.sh` returns, for an attempt inside its deadline.
- To No-Go: a natural void reaches promptfoo as a graded result.

Regression test type, and the limit of this evidence:

- The evidence is one behaviour scenario, run with one model at one commit per live run, 3 graded runs each, all passes.
- Regression testing runs the same cases against two versions of a skill and reports a graded fail on the version that has the defect.
  No run here compared two checkouts, and no live attempt failed its grade.
- A matrix of two provider entries was observed only with a script that prints its inputs (`## Capability re-check`, row 9), not with an agent.
- The cost and the void rate of this scenario say nothing about another case.
- That is a gap of this spike's method, so the regression decision is Inconclusive, not No-Go.
- It becomes Partial-Go or Go with one observation: an eval of one scenario over two checkouts, one of them with a known defect, that reports each checkout's graded results apart, with the fail on the defective one and the cap of 2N kept per checkout.

SKL-315 and SKL-316.
This decision rests on the rows cited above and does not depend on either spike.

- SKL-315, the prose rubric.
  A rubric call is a model-graded assertion and uses no script provider, so no outcome of SKL-315 changes what the live run showed.
  A Go there moves the behaviour decision toward Go: the Node install would already be carried for a type `run-suite.sh` has no mechanism for, and observation 5 would stop weighing against the behaviour type.
  A No-Go there moves it toward No-Go: the install would be carried for what observation 4 lists alone.
- SKL-316, the live trigger run.
  Its fourth research question is how a void run is told from a failed one in a live run through the script provider.
  A natural void that the script provider there classifies as void, and tells from a fail, closes the third gap above and moves the behaviour decision toward Go.
  A natural void that cannot be told from a fail by the case's exit status moves it toward No-Go, because the provider's retry rests on that exit status.
  Its result for `skill-used` through an agent provider changes nothing here.

Follow-up work: no new issue is created, and one existing Backlog spike is linked.
SKL-326, "Defend tabletop eval cases against the agent forging its own record", already owns the limit above for this case: its research questions cover an agent that restores a changed checkout before the end-of-run check and a sandboxed agent process.
It is linked to SKL-317 as related.
Rules (ii) and (iii) are provider logic that does not depend on the model: the stub runs exercised both through the same promptfoo build and the case's own runner, and `poc/selftest.py` checks both without promptfoo.
A live run exercises them only when attempts void six times or one breaks, which a working case does not do on demand, and the story allows one injected void.
The natural void is inside SKL-316's fourth research question.
The two-checkout observation for the regression type is worth a spike only if the owner moves toward adopting promptfoo, which SKL-312 ruled No-Go for now.
Work to adopt promptfoo waits on that decision and on SKL-315 and SKL-316, which are already in Backlog.

## Research questions

### 1. Can a script provider run a live attempt, retry voids inside itself and hand promptfoo one graded result per test case

Yes, for what the live run exercised (live).

- The provider is `poc/provider.py`, started by promptfoo as an `exec:` provider.
  Each call runs the case's own `run.sh` on a fresh run directory until one attempt is graded, and then prints one line of JSON for the `python` assertion in `poc/grade.py` to read.
- promptfoo received 3 graded results from 4 attempts and reported 3 passes (`poc/compare.md`, "Attempts" and "Provider calls").
- The void attempt was graded by nothing: only the case's `run.sh` runs `grader.py`, and it does not grade a void attempt.
- promptfoo's own retry gap did not matter in this run, because promptfoo had nothing to retry: it saw no error.

What the provider hands promptfoo when all 2N attempts are void (stub, not live; plan `void,void,void,void,void,void`):

- The first provider call ran attempts 1 to 6, all void, then exited 1 with the reason `attempt cap reached`.
- promptfoo recorded that call as an error: `success` false, `score` 0, `failureReason` 2.
- The provider refused calls 2 and 3 without running an attempt, with the reason `run stopped earlier`, and promptfoo recorded two more errors.
- promptfoo's totals were 0 successes, 0 failures and 3 errors, the eval exited 100, and `run.sh` exited 1 and claimed no result.
- So promptfoo gets an error result, the same outcome it gives any failed provider call.
  Only the reason text tells a run of voids from another failure, and promptfoo has no outcome for it (`## Capability re-check`, row 19).

A graded fail (stub, not live; plan `fail,pass,fail`) reached promptfoo as a failed assertion with `failureReason` 1, apart from the errors above.
promptfoo's totals were 1 success, 2 failures and 0 errors, the eval exited 100, and `run.sh` exited 0 because the run had its N graded results.

### 2. Does the run reproduce the `suite.py` retry and stop rules, and which did it not exercise

| Rule | Live run (`poc/compare.md`, "Suite rules") | Stub runs, not live |
|---|---|---|
| (i) void attempts do not count toward N | `reproduced`, with an `injected` void only | The same in every plan with a void |
| (ii) the run stops at 2N attempts | `not exercised in this run` | Plan of six voids: the provider stopped after attempt 6 of 6 and started no further attempt |
| (iii) any other exit status stops the run | `not exercised in this run` | Plan `pass,void,broken,pass`: attempt 3 exited 3, the provider started no further attempt, the next call was refused, and `run.sh` exited 1 |

Rules (ii) and (iii) are open questions in `## Decision`, and they make the behaviour decision Inconclusive.

`poc/selftest.py` checks the three rules, the ceiling, the clone and ledger checks and the checks of `compare.py` without promptfoo, Node.js or a model.
It is run by hand, and no CI job runs it or `run.sh` (`poc/README.md`, "What no job runs").

One difference from the suite is by design and is not a rule above.
The suite stops its whole run at a broken attempt and exits 1.
promptfoo cannot be stopped by a provider, so it still made its remaining calls; the provider refused each one without running an attempt, and `run.sh` exited 1.

### 3. Which of SKL-312's labels still hold

All of them.
`## Capability re-check` has 19 rows for the 13 capabilities, and every re-check label equals the SKL-312 label.
Two rows disagree with SKL-312 on the page that documents a name, not on the label: `openai:codex-sdk` (row 4) and `skill-used` (row 16).

### 4. What one live attempt costs, void attempts included, and what the N = 3 run costs

The cost of an attempt is its token counts times the prices of `deepseek/deepseek-v4-pro` at https://models.dev/api.json , read 2026-11-16.
The seconds are the time between the attempt's start and end lines in the spend ledger.

The live run, from `poc/compare.md`, "Attempts" and "Spend":

| Attempt | Outcome | Seconds | Input tokens | Cached input tokens | Output tokens | Reasoning tokens | Cost in USD |
|---|---|---|---|---|---|---|---|
| 1 | graded pass | 157 | 46548 | 374912 | 1518 | 12457 | 0.066640244 |
| 2 | void, `injected` | 0 | 0 | 0 | 0 | 0 | 0.000000 |
| 3 | graded pass | 398 | 54772 | 534784 | 1715 | 34935 | 0.120481768 |
| 4 | graded pass | 449 | 90452 | 1523968 | 2718 | 41369 | 0.180517876 |

The earlier live run at `50893a214a8dfab55995737895d26bd30a292fc3`, from the report it wrote and the ledger:

| Attempt | Outcome | Seconds | Input tokens | Cached input tokens | Output tokens | Reasoning tokens | Cost in USD |
|---|---|---|---|---|---|---|---|
| 1 | graded pass | 46 | 18863 | 166016 | 1073 | 3147 | 0.024457532 |
| 2 | void, `injected` | 0 | 0 | 0 | 0 | 0 | 0.000000 |
| 3 | graded pass | 214 | 49562 | 713984 | 1553 | 19333 | 0.089772848 |
| 4 | graded pass | 304 | 52479 | 412928 | 1544 | 28867 | 0.103934336 |

The earlier live run at `327ac853822bacbf5e775f59f1a43af18364c15e`, from the report it wrote and the ledger:

| Attempt | Outcome | Seconds | Input tokens | Cached input tokens | Output tokens | Reasoning tokens | Cost in USD |
|---|---|---|---|---|---|---|---|
| 1 | graded pass | 481 | 67925 | 1411456 | 2610 | 25785 | 0.132104632 |
| 2 | void, `injected` | 0 | 0 | 0 | 0 | 0 | 0.000000 |
| 3 | graded pass | 356 | 57845 | 843648 | 2313 | 19481 | 0.099890076 |
| 4 | graded pass | 559 | 36842 | 469120 | 1605 | 32326 | 0.10181974 |

The earlier live run at `c8574c3c3eb5e005b3fa38e0d0e26c93744cb42d`, from the report it wrote and the ledger:

| Attempt | Outcome | Seconds | Input tokens | Cached input tokens | Output tokens | Reasoning tokens | Cost in USD |
|---|---|---|---|---|---|---|---|
| 1 | graded pass | 204 | 30368 | 309248 | 1229 | 16977 | 0.062894216 |
| 2 | void, `injected` | 0 | 0 | 0 | 0 | 0 | 0.000000 |
| 3 | graded pass | 304 | 45530 | 400128 | 1683 | 25725 | 0.093120456 |
| 4 | graded pass | 216 | 45453 | 467840 | 1649 | 16449 | 0.0761255 |

- The N = 3 live run cost 0.066640244 + 0.000000 + 0.120481768 + 0.180517876 = 0.367639888 USD.
- One attempt of it that called the model cost between 0.066640244 and 0.180517876 USD, and 0.367639888 / 3 = 0.122547 USD on average.
- Over all 4 of its attempts, the void included, the average is 0.367639888 / 4 = 0.091910 USD.
- The earlier live run at `50893a214a8dfab55995737895d26bd30a292fc3` cost 0.024457532 + 0.000000 + 0.089772848 + 0.103934336 = 0.218164716 USD; its script printed six decimals, 0.218165.
- The earlier live run at `327ac853822bacbf5e775f59f1a43af18364c15e` cost 0.132104632 + 0.000000 + 0.099890076 + 0.10181974 = 0.333814448 USD.
- The earlier live run at `c8574c3c3eb5e005b3fa38e0d0e26c93744cb42d` cost 0.062894216 + 0.000000 + 0.093120456 + 0.0761255 = 0.232140172 USD.
- Over the 12 attempts of the four runs that called the model, the cost was between 0.024457532 and 0.180517876 USD, and 1.151759224 / 12 = 0.095980 USD on average.
- The injected void ran no agent and cost nothing, so the cost of a natural void, which may spend tokens before it fails, was not measured.
- SKL-312 estimated 0.08 USD for an agent run: 8 of those 12 attempts cost more.
- promptfoo holds a cost of 0 and a token count of 0 for every one of these results, so each figure comes from the session record `opencode` keeps and the prices above (`poc/compare.md`, "Spend").

Spend ceiling:

- The ceiling for all live runs of this spike is 5 USD.
  The product owner raised it from 1 USD on 2026-11-16, after the second live run, and the spend already recorded counts toward it.
- The plan before the first run was at most 6 attempts at SKL-312's estimate: 6 x 0.08 = 0.48 USD, under the 1 USD ceiling of that time.
- The plan before the second run was the 0.218164716 USD already spent and at most 6 attempts at the highest cost of one attempt so far: 0.218164716 + 6 x 0.103934336 = 0.841770732 USD, under the 1 USD ceiling of that time.
- The plan before the third run was the 0.551979164 USD already spent and at most 6 attempts at the highest cost of one attempt so far: 0.551979164 + 6 x 0.132104632 = 1.344606956 USD, under the 5 USD ceiling.
- The plan before the final run was the 0.784119336 USD already spent and at most 6 attempts at the highest cost of one attempt so far: 0.784119336 + 6 x 0.132104632 = 1.576747128 USD, under the 5 USD ceiling.
- Before each attempt that calls the model the provider adds up a ledger kept outside the repository and stops with `ceiling reached` when the total plus the estimate of the next attempt is over 5 USD; the estimate is 0.08 USD, or the highest cost of one attempt so far when that is more.
  The estimate is not a bound on what one attempt costs.
- The ledger held 0 USD over 32 stub attempts before the first live run, development and dry runs included.
- The first live run added 4 attempts and 0.218164716 USD, and three stub runs after it added 12 attempts and 0 USD.
- The second live run added 4 attempts and 0.333814448 USD, so the ledger held 0.551979164 USD over 52 attempts before the third.
- The third live run added 4 attempts and 0.232140172 USD, and three stub runs after it added 12 attempts and 0 USD, so the ledger held 0.784119336 USD over 68 attempts before the final run (`poc/compare.md`, "Spend").
- The final run added 4 attempts and 0.367639888 USD, and the three stub runs cited in this file added 12 attempts and 0 USD after it.
- The ledger now holds 0.218164716 + 0.333814448 + 0.232140172 + 0.367639888 = 1.151759224 USD over 84 attempts, 68 stub and 16 live, which is 3.848240776 USD under the ceiling.
- Not in the ledger, because each called no model and wrote to a throwaway ledger of its own: the stub runs and the runs of `poc/selftest.py` made while the scripts were changed after each review round, the rehearsals of the live path with a stand-in for `opencode` whose costs were made up, and one test that seeded a ledger with 0.80 USD spent and 0.08 USD reserved to see `ceiling reached`.
- Four live invocations were made, and exactly one of them is of the final `run.sh`.
  The first pre-PR review round found that the agent under test could reach the ledger and that `compare.py` did not check the cap, the results, the runtime options or the costs.
  The fixes changed `run.sh`, `provider.py` and `compare.py`, so the run was made again.
  The second round found that a grader rewritten in the agent's checkout behind `git update-index --assume-unchanged` graded every attempt a pass with no blocker listed, that a ledger and the provider's copy rewritten together passed as a smaller history, and that `EVAL_PASS_ENV` could hand the agent the harness's variable names.
  The fixes changed `run.sh`, `provider.py`, `compare.py` and `grade.py`, so the run was made a third time.
  The review of the pull request found that an attempt that ran another model or called a subagent left the cost of its parent session in the ledger as a known cost, which a later invocation would add up as the whole.
  The fix changed `provider.py` and `compare.py`, so the run was made a fourth time, on the final scripts.
- What the final scripts' checks of the ledger and of the grade do not cover is in `## Decision`, "What the grade and the spend of the live run rest on".

## Success criteria status

| Criterion | Status | Evidence |
|---|---|---|
| 1. `bash spikes/SKL-317/poc/run.sh` makes one live invocation through a promptfoo `0.125.1` script provider that owns the void retry, grades with the unmodified `grader.py` and writes `poc/compare.md`, with N = 3, at most 6 attempts, concurrency 1, no promptfoo retry, one row per attempt, and the ceiling check before each attempt | met | `poc/compare.md`: "Attempts" (4 rows and the list under them), "Provider calls" (runtime options and the retry line), "Spend"; the command exited 0 |
| 2. `compare.md` states each `suite.py` rule with its quoted lines, the provider's observed behaviour and one of the three statuses | met | `poc/compare.md`, "Suite rules": (i) `reproduced` with an `injected` void, (ii) and (iii) `not exercised in this run`, both named in `## Decision` as open questions that make the behaviour decision Inconclusive |
| 3. Every capability label of the SKL-312 table is re-checked, one row per label | met | `## Capability re-check`, rows 1 to 19; no label is `not re-checked` |
| 4. `## Infrastructure data` holds the Node footprint as measurements only | met | `## Infrastructure data` |
| 5. `## Decision` gives a decision for the behaviour and the regression test type, with its observations, reversal conditions, the limit for regression testing, and SKL-315 and SKL-316 | met | `## Decision` |

## Capability re-check

This section re-checks every label of the capability table under `## Research questions` of the SKL-312 findings at commit `13486d84afe2603105b96a9b6ca7a9bd5aa7aa68`.
A label that names two things, or one that joins `observed` and `documented`, has one row per part.
"Partly supported" in three SKL-312 labels is a judgement of fit, not one of the three labels, so only the `observed` and `documented` parts are re-checked.

How each label was re-checked:

- `observed`: the claim was reproduced on the `0.125.1` build on 2026-11-16, and the row gives the command, its exit status and its output.
- `documented`: the claim is stated on the official page the row names, read on 2026-11-16, and the row quotes the text.
- `absent`: neither, and the row gives the command that shows the absence.

The build is the install measured in `## Infrastructure data`; `promptfoo --version` printed `0.125.1` with exit status 0.
Every probe ran from a throwaway directory outside the repository with a scrubbed environment (`env -i`), with `PROMPTFOO_CONFIG_DIR` pointing promptfoo's cache and config directory at a throwaway directory, and with no model call.
The probe provider is `exec: python3 echo_provider.py`, a script that appends its prompt to a call log and prints its prompt, the `config.variant` of its options argument, whether its working directory is the config directory, and whether a variable set in promptfoo's environment is visible.
The probe config `matrix.yaml` holds two tests and two such providers whose `config.variant` is `baseline` and `candidate`, with a `contains` assertion on each test and a `python` assertion on the first.
The probe config `fail.yaml` holds one provider and two tests, one of whose `python` assertions fails.
No agent provider and no `llm-rubric` assertion was run, because either is a model call outside the live invocation of `run.sh`; those labels are re-checked against the pages and looked up in the build.
"In the build" means `grep -rlF --include='*.js' -e '<name>' dist | wc -l`, run in the installed `promptfoo` package directory, printed a count above 0 with grep exit status 0; the count is the number of files holding the name.

The pages were fetched with `curl` at 2026-11-16T05:15:20Z, each with HTTP 200.
The documentation site documents the current release.
On 2026-11-16 `npm view promptfoo dist-tags.latest` printed `0.125.1` with exit status 0, which is the pinned version, so no version drift between the pages and the build is known for that date.

| # | SKL-312 capability and label | SKL-312 claim, quoted | Re-check label | Method | Command with exit status and output, or URL with quoted text (read 2026-11-16) | Result |
|---|---|---|---|---|---|---|
| 1 | Script provider (`exec:`): observed | "`poc/provider-contract/envelope.json`; 24 replays" | `observed` | Probe eval on the build, and the live run | `promptfoo eval -c matrix.yaml --no-cache --repeat 2 --no-table --no-progress-bar -o out/matrix.json`: exit status 0; 8 results, 8 successes, 8 lines in the script's call log. The live run in `poc/compare.md` ran its attempts through the same provider type. | agree |
| 2 | Model and agent providers, `anthropic:claude-agent-sdk`: documented | "https://www.promptfoo.dev/docs/providers/claude-agent-sdk/ and https://www.promptfoo.dev/docs/providers/opencode-sdk/ ; all three ids are in the `0.125.1` build" | `documented` | Page read; name looked up in the build | https://www.promptfoo.dev/docs/providers/claude-agent-sdk/ : "By default, Claude Agent SDK runs in a temporary directory with no tools enabled, using the default permission mode."; the page holds `anthropic:claude-agent-sdk` on 4 lines. In the build: 12 files. | agree |
| 3 | Model and agent providers, `opencode:sdk`: documented | as row 2 | `documented` | Page read; name looked up in the build | https://www.promptfoo.dev/docs/providers/opencode-sdk/ : "opencode:sdk - Uses OpenCode's configured model". In the build: 10 files. | agree |
| 4 | Model and agent providers, `openai:codex-sdk`: documented | as row 2 | `documented`, on a page SKL-312 did not cite | Both cited pages searched; a third page read; name looked up in the build | `grep -c -F -e 'openai:codex-sdk'` over each of the two cited pages printed 0 with exit status 1. https://www.promptfoo.dev/docs/providers/openai-codex-sdk/ (HTTP 200, title "OpenAI Codex SDK \| Promptfoo") holds `openai:codex-sdk` on 2 lines. In the build: 15 files. | disagree on the evidence, see below |
| 5 | Deterministic assertions (`python`, `contains`): observed | "`poc/grade.py` runs `grader.py`; `contains` in the throwaway eval" | `observed` | Probe evals on the build, and the live run | The command of row 1: exit status 0, and all 8 results passed their `contains` assertion and, on the first test, the inline `python` assertion. `promptfoo eval -c fail.yaml --no-cache --no-table --no-progress-bar -o out/fail.json out/fail.csv out/fail.html out/fail.xml out/fail.yaml`: exit status 100; 2 results, 1 success, 1 failure from the `python` assertion, 0 errors. The live run grades through a `python` assertion (`poc/grade.py`). | agree |
| 6 | Model-graded assertions (`llm-rubric`): documented | "https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/llm-rubric/ ; the type is in the build" | `documented` | Page read; name looked up in the build; not run | https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/llm-rubric/ : "llm-rubric is promptfoo's general-purpose grader for \"LLM as a judge\" evaluation." In the build: 15 files. | agree |
| 7 | Caching: observed | "A second eval of the same config made no provider call and marked every response cached" | `observed` | Three probe evals on the build | `promptfoo eval -c matrix.yaml --no-table --no-progress-bar -o out/cache1.json`: exit status 0, 4 provider calls, 0 cached responses. The same command again with `-o out/cache2.json`: exit status 0, 0 provider calls, 4 cached responses. The same command with `--no-cache` and `-o out/cache3.json`: exit status 0, 4 provider calls, 0 cached responses. | agree |
| 8 | Repeat runs (`--repeat N`): observed | "2 tests x 2 providers x `--repeat 2` gave 8 results and 8 provider calls" | `observed` | Probe eval on the build, and the live run | The command of row 1: exit status 0, 8 results and 8 provider calls. The live run passes `--repeat 3` (`poc/compare.md`, "Provider calls"). | agree |
| 9 | Matrix over models and skill versions: observed | "Two providers with different `config` values ran every test, and each value reached the script in its options argument" | `observed` | Probe eval on the build | The command of row 1: exit status 0; each of the two tests ran under both providers, and the outputs hold `variant=baseline` for the first provider and `variant=candidate` for the second. | agree |
| 10 | CI integration, exit status and output formats: observed | "Exit status 100 when a test fails or errors, and `-o` wrote json, csv, html, xml and yaml (observed)" | `observed` | Probe eval on the build, and the stub dry runs | The `fail.yaml` command of row 5: exit status 100 with 1 failed test; it wrote `fail.json` (9023 bytes), `fail.csv` (317), `fail.html` (45051), `fail.xml` (10323) and `fail.yaml` (6786). An eval whose provider call errors also exits 100 (stub dry run, `## Research questions`, 1). | agree |
| 11 | CI integration, GitHub Action: documented | "the GitHub Action is documented at https://www.promptfoo.dev/docs/integrations/github-action/ and not run" | `documented` | Page read; not run | https://www.promptfoo.dev/docs/integrations/github-action/ : "This guide describes how to automatically run a before vs. after evaluation of edited prompts using the promptfoo GitHub Action." | agree |
| 12 | Viewer (`promptfoo view`): observed | "Started on a local port, it served its page and listed the evals in its local database" | `observed` | Viewer started on the build | `promptfoo view -p 15617 -n`, stopped after the two requests: `GET /` gave HTTP 200, 1758 bytes, `<title>promptfoo</title>`; `GET /api/results` gave HTTP 200 and listed the 5 probe evals. | agree |
| 13 | Agentic multi-step runs with tool use: documented | "Tools are off until `working_dir` is set, then read-only until write and shell tools are enabled (both provider pages above)" | `documented` | Both pages read; not run | https://www.promptfoo.dev/docs/providers/claude-agent-sdk/ : "By default, when you specify a working directory, Claude Agent SDK is given read-only access to the directory." https://www.promptfoo.dev/docs/providers/opencode-sdk/ : "By default, OpenCode SDK runs in a temporary directory with no tools enabled." and "By default, when you specify a working directory, OpenCode SDK has access to these read-only tools: read, grep, glob, list." | agree |
| 14 | Tool-call grading, `python` assertion over the committed `actions.jsonl`: observed | "A `python` assertion over the committed `actions.jsonl` (observed, the replay)" | `observed` | SKL-312 replay run again on the build | `bash spikes/SKL-312/poc/run.sh` in a fresh clone at `07567d2dbe2284d7fb9c0a65bea5df9de29ed83c`: exit status 0; "Replayed runs that match their recorded verdict: 24 of 24". | agree |
| 15 | Tool-call grading, `trajectory:tool-used` and `trajectory:tool-sequence`: documented | "`trajectory:tool-used`, `trajectory:tool-sequence` and `skill-used` are in the build and documented at https://www.promptfoo.dev/docs/guides/evaluate-coding-agents/" | `documented` | Page read; names looked up in the build | https://www.promptfoo.dev/docs/guides/evaluate-coding-agents/ : "If your agent emits tool-oriented spans, add trajectory:tool-used or trajectory:tool-sequence to verify the exact tool path." In the build: 7 files each. | agree |
| 16 | Tool-call grading, `skill-used`: documented | as row 15 | `documented`, on pages SKL-312 did not cite for it | Cited page searched; two other pages read; name looked up in the build | `grep -c -F -e 'skill-used'` over the cited guide page printed 0 with exit status 1. https://www.promptfoo.dev/docs/providers/claude-agent-sdk/ : "Promptfoo normalizes Claude Skill tool invocations into response.metadata.skillCalls, so skill evals can use the same skill-used assertion style as Codex."; that page and https://www.promptfoo.dev/docs/providers/opencode-sdk/ each hold `skill-used` on 2 lines. In the build: `skill-used` 7 files, `skillCalls` 15 files. | disagree on the evidence, see below |
| 17 | Worktree or sandbox isolation: documented | "`copy_working_dir` gives each step a fresh copy or git clone, and the guide states that a workspace is not a sandbox; `copy_working_dir` is in the build" | `documented` | Page read; name looked up in the build; not run | https://www.promptfoo.dev/docs/guides/evaluate-coding-agents/ : "Set copy_working_dir: true to give each eval step a fresh copy instead", "A clone when working_dir is the root of a git repository whose files all match its current commit, with no untracked or ignored files. A copy of the directory otherwise." and "A workspace keeps calls from affecting each other, but it isn't a sandbox." In the build: 9 files. | agree |
| 18 | Worktree or sandbox isolation, script provider: observed | "the script runs in the config directory with promptfoo's own environment (observed)" | `observed` | Probe eval on the build | The command of row 1: exit status 0; all 8 outputs hold `cwd_is_config_dir=True` and `marker=visible`, the marker being a variable set only in promptfoo's environment. | agree |
| 19 | A void outcome, a graded-run count, stop on a broken attempt: absent | "`poc/compare.md`, \"Unmapped tokens\" and \"Tokens mapped with a loss\"; `eval --help` offers only `--retry-errors`" | `absent` | Help text of the build searched; stub dry runs | `promptfoo eval --help`: exit status 0. Of its lines, `grep -n -i -E 'retry\|void\|graded\|attempt'` prints one: "--retry-errors  Retry all ERROR results from the latest evaluation". Its only repeat option is "--repeat <number>  Number of times to run each test (default: 1)". In the build the result failure reasons are `NONE: 0`, `ASSERT: 1` and `ERROR: 2`, with no void among them. In the stub dry runs of `## Research questions`, 1 and 2, a call of six voids and a broken attempt both reached promptfoo as `failureReason` 2, and promptfoo went on to its next call. | agree |

The two disagreements are about the page cited, not about the label.

- Row 4. SKL-312 reads `openai:codex-sdk` as documented on the two provider pages it cites.
  This re-check finds the id on neither of them and finds it on the provider's own page, https://www.promptfoo.dev/docs/providers/openai-codex-sdk/ .
  The label `documented` holds with that page as its evidence.
- Row 16. SKL-312 reads `skill-used` as documented on the coding-agents guide.
  This re-check finds the name absent from that page as fetched and present on the Claude Agent SDK and OpenCode SDK provider pages.
  The label `documented` holds with those pages as its evidence.
  The guide may have named it when SKL-312 read it; the earlier text of the page was not recovered.

No label was left `not re-checked`.

## Infrastructure data

Measured on 2026-11-16 at 04:51 UTC in a Docker container running Ubuntu 24.04.5 LTS on Linux 7.0.0-43-generic, x86_64; the image name was not recorded.
Each figure is a measurement of one install into a throwaway directory outside the repository, written here as `<prefix>`.

| Item | Command | Exit status | Result |
|---|---|---|---|
| Install method | `npm install --no-audit --no-fund --ignore-scripts --loglevel=error --before=2026-11-15T00:00:00Z promptfoo@0.125.1 --prefix <prefix>`, run under `env -i` with only `PATH`, `HOME`, `TMPDIR`, `LANG`, `npm_config_cache` and `npm_config_update_notifier=false` set | 0 | "added 617 packages in 50s" |
| Node version | `node --version` | 0 | `v24.20.0` |
| npm version | `npm --version` | 0 | `11.19.0` |
| Package count | `npm ls --all --omit=dev --parseable --prefix <prefix>`, lines counted with `wc -l` | 0 | 618 lines: 617 installed packages and the root line. A package is one installed directory that npm lists, so a package installed at two versions counts twice. |
| Development total | `npm ls --all --parseable --prefix <prefix>`, lines counted with `wc -l` | 0 | 618 lines, the same count: installing `promptfoo` as a dependency installs no development dependency, so there is no separate development total. |
| Size on disk | `du -sh <prefix>/node_modules` | 0 | 747M |
| Supply-chain check | `npm audit signatures --prefix <prefix>` | 0 | "617 packages have verified registry signatures" and "157 packages have verified attestations" |
| Installed version | `<prefix>/node_modules/.bin/promptfoo --version` | 0 | `0.125.1` |

`--ignore-scripts` keeps every package's install script from running, and `--before` resolves no version published after 2026-11-15T00:00:00Z.
`poc/run.sh` installs with the same command and runs the same signature check before each eval.
In the live run that install added 617 packages, and the check exited 0 with 617 verified registry signatures and 157 verified attestations.

The story keeps a Node lockfile out of the repository, so only `promptfoo` itself is pinned by version.
Every other package is the newest version its range allows among those published before the `--before` instant, so two installs are the same while the registry serves the same versions for that instant, and the install is not byte-reproducible.
The signature check shows that each installed package is signed by the registry, not that the set equals an earlier install's.

## Guard results

The guards are the four in `.github/workflows/ci.yml` at this branch's head.
Their commands are the ones the story lists; the one difference is that the workflow sets `OPENCODE_FORCE_INSTALL=1` for guard 4, which makes `scripts/smoke-opencode.sh` install the pinned opencode even when the same version is already on the machine.
Pinned `skills-ref` reference, from that file: `git+https://github.com/agentskills/agentskills@69ef37e9424c0a7ea9dd2293b559e43ec8176379#subdirectory=skills-ref`.

The four guards ran on commit `7cd9ba94e018eedab3724a361243abf08772e272` on 2026-11-16, locally and in [ci run 43906545497](https://github.com/noahwhite/agent-skills/actions/runs/43906545497), which ran on the pull request that merges this file when that commit was its head.
A file cannot name the CI run of the commit that holds it.
Every commit after that one, the merged one included, gets the same four guards from the `ci` workflow, which runs guards 1, 2 and 3 in its `checks` job and guard 4 in its `discovery` job on every pull request head and on every push to `main`.
The pull request that merges this file and the SKL-317 handoff comment name those runs.

| Guard | Command | Commit | Where it ran | Exit status | Result |
|---|---|---|---|---|---|
| 1 | `uv run --locked pytest -q` | `7cd9ba94e018eedab3724a361243abf08772e272` | locally, and the `checks` job of ci run 43906545497 | 0 in both | pass: 2801 passed locally; the step "Repository tests" succeeded |
| 2 | `uv run --locked python scripts/leak_scan.py --require-private` | `7cd9ba94e018eedab3724a361243abf08772e272` | the `checks` job of ci run 43906545497 | 0 | pass: the step "Leak scan (public and private patterns)" succeeded |
| 3 | `uvx --from "<pinned reference>" skills-ref validate "$d"` for each of the 18 `skills/*/` directories | `7cd9ba94e018eedab3724a361243abf08772e272` | locally, and the `checks` job of ci run 43906545497 | 0 for each | pass: "Valid skill" for each of the 18 locally; the step "Validate skills against the Agent Skills spec" succeeded |
| 4 | `bash scripts/smoke-opencode.sh` | `7cd9ba94e018eedab3724a361243abf08772e272` | locally, and the `discovery` job of ci run 43906545497 with `OPENCODE_FORCE_INSTALL=1` | 0 in both | pass: opencode discovered all 18 skills in each of the 6 locations locally; the step "opencode discovers every skill" succeeded |

- Guard 2 needs the private patterns, which exist only as the CI secret `LEAK_DENYLIST`.
  Run locally, the command exits 2 with `INCOMPLETE` because no private pattern is loaded, so its status above is the CI one.
  The public patterns alone, `uv run --locked python scripts/leak_scan.py`, exit 0 locally.
- `python3 spikes/SKL-317/poc/selftest.py` exited 0 on the same commit with "selftest: every check holds".
  It is not one of the four guards, and no CI job runs it.
- No guard rejected a spike file, so no normalization, encoding, exemption or amendment was needed after a guard ran.
- No exemption entry was added: no tracked file outside `spikes/SKL-317/` changed, and the locked uv environment and its lockfile are unchanged.
- `poc/compare.md` was committed as the live run wrote it: `poc/compare.py` writes tabulated fields only, and no path outside the repository, session id, prompt text or agent output.
