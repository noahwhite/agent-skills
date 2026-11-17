# SKL-138 QA evidence

path: no-deployment
Target: merged commit `f83cacb6d5ebeda88b3671d57172d634ac1b3275` on `main`, the squash of PR 325, confirmed an ancestor of `origin/main` in both rounds.
The PR's reviewed head `5b95cfe9b3307461f4a34ee8aecebcfa4492d442` has no diff from the target under `skills/story-to-done`, `shared`, `README.md` and `tests/test_story_to_done.py`.
Environment: none; the repository profile sets `environments: []`, so the lanes are the repository (a detached worktree of the target), GitHub and the tracker.
Fixtures: SKL-359 and SKL-360, two `[Tabletop fixture]` issues in SKL created In Deployment Review for C6, both canceled after the runs and read back as Canceled in round 1 and again in round 2.
There is no visual surface, so no screenshot applies; the raw output is attached to SKL-138.

## Final verdicts (round 2)

| Item | Verdict |
|---|---|
| C1: explicit nesting input | Verified |
| C2: foreground launches when nested | Verified |
| C3: runtime map | Verified |
| C4: docs | Verified |
| C5: tests | Verified |
| C6: verified end to end | Verified |
| DoD: all acceptance criteria met | Verified |
| DoD: unit and integration tests written and passing | Verified |
| DoD: independently reviewed | Verified |
| DoD: docs updated | Verified |
| DoD: verified in a deployed environment | Correct by design |
| DoD: no critical bugs or regressions | Verified |

Per-item evidence:

- C1: the Arguments table has seven rows, the `nested` row defaults to `no`, and the intro line reads "Seven arguments are optional", as the 2026-11-17 AC amendment requires.
  "Six", "Five" and "Four arguments are optional" are absent.
  The closed plain-words map, the ask-or-stop rule with "not nested" and "non-nested" asked about, resolution before step 0 with no model or effort, the never-infer sentence (once), the `nested: yes|no` echo and the `nested: unresolved` exception are present.
- C2: steps 2, 3 and 4 each carry one `nested=yes` foreground line that keeps the runtime's default mode under `nested=no`.
  The only line that says "background" is the one reason sentence in Arguments, and the skill names no `run_in_background` flag.
  The identical-briefs, role-rows and metrics-rules sentence is present.
- C3: `shared/runtimes.md` has one Nested subagents rule carrying every C3 clause, and SKILL.md points at it as the nesting rule.
  The OpenCode V2 Tools page is in the V2 reference list, and the rule gives `experimental.subagent_depth: 3` for the top-level chain plus one level per hop above a spawner that is itself a subagent.
  The 18 vendored `runtimes.md` copies carry the source, and `scripts/vendor_shared.py --check` exits 0.
- C4: the README row names `nested` and its default `no` before the metrics clause and still ends with the posted-summary clause.
  The Arguments resolved-values bullet and the step 5 report name `nested: yes|no`.
- C5: `test_arguments_prose_count_matches_the_table` asserts seven rows and "Seven arguments are optional" and rejects "Six", "Five" and "Four".
  The new `nested` tests, the negation cases and the README row-ending test are present, and the skill frontmatter does not mention `nested`.
  `uv run --locked pytest -q` passed 3191 tests on the target in round 2.
  CI `checks` and `discovery` passed on the PR head and on the merged commit.
  The PR description holds the delete-each-phrase proof.
  C5 names `test_arguments_table_adds_the_metrics_switch_off_by_default` as the home of the count prose, but that test held no count prose before this story merged; the only count-prose pin, in `test_arguments_prose_count_matches_the_table`, now asserts "Seven".
- C6: Run 1 and Run 2 below, from round 1; C6 was not amended, and round 2 re-read both fixtures as Canceled.
- DoD all acceptance criteria met: C1 to C6 are verified.
- DoD tests written and passing: the C5 tests and the round 2 suite pass.
- DoD independently reviewed: PR 325 review 5946789264 names `5b95cfe9b3307461f4a34ee8aecebcfa4492d442` in its first line and as its `commit_id`, the merged head.
- DoD docs updated: see C4.
- DoD verified in a deployed environment: the path is no-deployment, and C6 is the end-to-end check.
- DoD no critical bugs or regressions: the full suite and CI passed.

## Round 2 (2026-11-17)

Round 2 follows the product owner's AC amendment of 2026-11-17, which sets the argument count in C1 and C5 to "Seven".
It re-ran the C1 to C5 static checks on a detached worktree of the target (62 assertions, 0 failed), the full suite, the vendor check and the CI read, and re-read the C6 fixtures.
The raw output is attached to SKL-138 as "SKL-138 QA round 2 - static checks (C1-C5)".

## Round 1 (2026-11-17)

Round 1 verified C2, C3, C4 and C6 and recorded C1, C5 and the first DoD line as pending owner ruling on the argument count.
Its quoted text was "Six arguments are optional", while the merged skill says "Seven" over a seven-row table, because `qa-round-cap` (SKL-155) had already made six.
The product owner's amendment of 2026-11-17 settled it in favor of "Seven".

### C6 runs

Runtime: Claude Code 2.1.326, headless `claude -p` with `--output-format stream-json`, permission mode `auto`, one fresh process per run.
Fork mode: `CLAUDE_CODE_FORK_SUBAGENT=0`, set in the `env` block of the settings file passed with `--settings`; each run is a new process, so no restart was needed.
Docs read 2026-11-17: [env-vars](https://code.claude.com/docs/en/env-vars.md) says fork mode is on by default and that while it is on Claude "can't wait for a subagent in interactive terminal, VS Code, or desktop sessions".
[sub-agents](https://code.claude.com/docs/en/sub-agents.md) says that under `claude -p` and the Agent SDK "Claude can wait".
`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` is a documented alternative way to make Claude wait; it was not set.
In this configuration an `Agent` call with no `run_in_background` starts in the background (`is_backgrounded: true` in both such launches below), which is the runtime's default launch mode.
Both runs use `metrics=off`, a fixture profile equal to the repository profile with `qa` removed and both `story_to_done` seats on `claude-code` / `claude-sonnet-5-5` at high, and a QA brief with a scripted tabletop paragraph.
Step exercised: step 3, one QA launch, then the close-out; each fixture starts In Deployment Review, so no engineer is launched.
The coordinator reads the skill from a detached checkout at `5b95cfe9b3307461f4a34ee8aecebcfa4492d442`, not the installed skill.

#### Run 1: `nested=yes`

A top-level `claude -p` parent session spawns the coordinator as a subagent with this brief (paths shortened to `.../`, the tabletop paragraph cut at `[...]`):

```text
You are the parent session for a tabletop run. Do exactly this and nothing else.

Spawn one general-purpose subagent with the Agent tool, model sonnet, description "story-to-done SKL-359", whose whole prompt is the text between the BEGIN and END lines below, copied verbatim. Wait for its handback. Do not run any other tool, do not do its work yourself, and do not resume or re-spawn it. When it hands back, output its closing report verbatim as your final answer, with nothing before or after it.

The owner authorizes the tracker writes on SKL-359 that the tabletop paragraph below names.

BEGIN
Story to done SKL-359, nested=yes, metrics=off.

Run the story-to-done skill for SKL-359 by reading and following the file .../prhead/skills/story-to-done/SKILL.md and its references/ and scripts/ directories beside it. That checkout is detached at PR head 5b95cfe9b3307461f4a34ee8aecebcfa4492d442 and is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is .../c6/profile.yaml; the AGENT_SKILLS_PROFILE environment variable already names it. The target repository is the checkout above.

Your session scratch directory already exists: .../c6/run1/coordinator/ . Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-359 is a disposable fixture. When you spawn a QA agent in step 3, append this paragraph verbatim at the end of its brief, after everything step 3 requires: [...]

Never write secrets to files or argv. Run each shell step as one simple command with literal values.
END
```

Transcript, launch and wait lines (from the stream):

```text
[parent] Agent description="story-to-done SKL-359" (no run_in_background)  -> task_started is_backgrounded=true spawn_depth=1
[coord]  Write coordinator-todo.md (top lines include "nested: yes")
[coord]  Bash select-path.py ... --recorded-path=no-deployment  -> no-deployment
[coord]  Bash qa-round-cap.py arm --story SKL-359 --cap 3 ...  -> round=0 cap=3 reached=no
[coord]  Agent description="QA round 1 for SKL-359" effort=high run_in_background=false  -> task_started is_backgrounded=false spawn_depth=2
[coord]  Agent result (same call): "This agent's report was delivered to you as a message from <QA agent> (its SubagentHandback call)."
[coord]  Read QA checklist; Bash linear issue view SKL-359 --json; SubagentHandback
subagent_stats: requested background=0 foreground=1 unset=1; started_in_background=1; max_depth=2; completed=2; failed=0
```

The coordinator ran no wait command (`sleep`, a `cat` or `tail` of an output file, a polling loop) while QA ran.
QA's handback reached the coordinator and began: "SKL-359 final state: Done. The readback shows state Done and both description boxes ticked."

Coordinator closing report (verbatim, paths shortened):

```text
SKL-359: final state Done, confirmed by my own read-back.

engineer-model: claude-sonnet-5-5
engineer-effort: high
qa-model: claude-sonnet-5-5
qa-effort: high
metrics: off
qa-round-cap: 3
nested: yes
path: no-deployment

- **Engineer:** none launched. The story started in In Deployment Review, so step 1 routed straight to step 3.
- **QA:** one round. The agent was launched in the foreground (the Agent tool had `run_in_background`) and its handback came back to me. The Agent tool's model enum has no `claude-sonnet-5-5`, so I passed `sonnet` with effort high.
- **QA checklist:** read back at `.../c6/run1/coordinator/qa-agent-round-1/qa-agent-round-1-todo.md`. Every item is ticked. No read-back resume was needed (0).
- **Tracker read-back:** `linear issue view SKL-359 --json` shows state Done, both AC boxes ticked, and one comment headed "QA round 1 verdicts".
- **AC1:** VERIFIED. `test 2 -eq 2; echo exit=$?` printed `exit=0`.
- **AC2:** VERIFIED. `test -d /tmp; echo exit=$?` printed `exit=0`.
- **Outstanding items:** none.
- **Incidental defects:** none noted.
- **PRs:** none. QA merged no PR, and the profile has no `qa.evidence_dir`, so no evidence PR was needed.
- **QA rounds:** 1, with no failed items. The round-cap script's `arm` step ran once; `record` never ran because no round failed.
- **Coordinator todo list:** `.../c6/run1/coordinator/coordinator-todo.md`. All items are done.

report: final
```

The foreground QA launch follows the skill's `nested=yes` instruction under the configuration above; the run does not show that it would hold under another host configuration.

#### Run 2: `nested=no`

The coordinator is the top-level `claude -p` session, with the Run 1 text between BEGIN and END for SKL-360, `nested=no` and `.../c6/run2/` paths, plus the owner-authorization line.

```text
[coord]  Write coordinator-todo.md (top lines include "nested: no")
[coord]  Bash select-path.py ... --recorded-path no-deployment  -> no-deployment
[coord]  Bash qa-round-cap.py arm --story SKL-360 --cap 3 ...  -> round=0 cap=3 reached=no
[coord]  Bash render-brief.py --role qa --story SKL-360 --path no-deployment ... --round 1
[coord]  Agent description="QA round 1 for SKL-360" effort=high (no run_in_background)  -> task_started is_backgrounded=true spawn_depth=1
[coord]  Agent result: "Async agent launched successfully."; the turn ends waiting for the handback
[coord]  (new turn on QA's handback) Read QA checklist; Bash linear issue view SKL-360 --json
subagent_stats: requested background=0 foreground=0 unset=1; started_in_background=1; max_depth=1; completed=1; failed=0
```

Launch mode used: the runtime's default, which in this configuration is background.
The coordinator ran no wait command while QA ran, and received QA's handback, which began: "SKL-360 final state: Done (read back via `linear issue view SKL-360 --json`)."

Coordinator closing report (verbatim):

```text
SKL-360 is Done after one QA round.

- Story: SKL-360
- engineer-model: claude-sonnet-5-5
- engineer-effort: high
- qa-model: claude-sonnet-5-5
- qa-effort: high
- metrics: off
- qa-round-cap: 3
- nested: no
- path: no-deployment
- Final state: Done, read back from the tracker. AC1 and AC2 are both ticked.
- PRs: none.
- Rounds: 1. QA round 1 had no failed items, and the engineer was never launched because the story started in In Deployment Review.
- Evidence: the "QA round 1 verdicts" comment on SKL-360 (https://linear.app/officina-pub/issue/SKL-360/tabletop-fixture-skl-138-c6-run-2-nestedno#comment-16c61cb1).
  - AC1: VERIFIED. `test 2 -eq 2; echo exit=$?` printed `exit=0`.
  - AC2: VERIFIED. `test -d /tmp; echo exit=$?` printed `exit=0`.
- Incidental defects: none noted.
- Outstanding items: none.
- Note: the QA agent ran only the two fixture commands and did not check commit `f83cacb6d5ebeda88b3671d57172d634ac1b3275`, which the brief named as the target. That is as the tabletop paragraph specified.

report: final
```

#### What the runs exercise

- Exercised: `nested` resolution and its echo, the step 3 QA launch mode under each value, receipt of the QA handback, and the close-out.
- Scripted, not exercised: QA's verdicts and its tracker writes come from the tabletop paragraph, not from `qa-verification`.
- Not exercised: the step 2 and step 4 engineer launch lines, which the C5 text contracts cover.
