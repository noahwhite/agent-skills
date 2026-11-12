# SKL-155 fixture run evidence (AC5)

Date: 2026-11-12 UTC.
Skill under test: `skills/story-to-done/SKILL.md` as committed in `bbb5014aecbee5d29d2b066c3c2d1668a6d977d1` on `feature/SKL-155-qa-round-cap`, read from a worktree by path (the installed skill was not loaded).
Fixture issue: SKL-266 "[Tabletop fixture] SKL-155 QA round cap stop", created in In Deployment Review for this run with two deliberately unmeetable acceptance criteria, and canceled by the implementing engineer after the coordinator's report.
This is a new fixture, not SKL-164's tabletop suite: that suite is not committed to the repository.
Step exercised: story-to-done step 4, the `profile.tracker.states.in_progress` branch, at the cap stop.
Resolved `qa-round-cap: 1` and `metrics: off`.
Runtime: Claude Code 2.1.322.
Coordinator: a general-purpose subagent on Opus 5.5, launched with the parent brief below as its whole prompt.
QA: Sonnet 5.5 at high, spawned by the coordinator under step 3, with a scripted tabletop paragraph that records both criteria not met and moves SKL-266 to In Progress.
The fixture profile is a copy of the repository profile with `story_to_done.engineer` and `story_to_done.qa` set to `claude-code` / `claude-sonnet-5-5` at high, so no command seat needs a trust answer.

## Result

- QA round 1 ended with SKL-266 read back In Progress, both criteria NOT MET.
- The coordinator stopped at counted round 1 (the cap), before the hand-back to the senior engineer.
- No senior engineer was launched: the run started in In Deployment Review, so step 2 did not run, and the cap stop launched nothing further.
- The coordinator made no tracker write: its only tracker calls are two `linear issue view SKL-266 --json` reads (transcript below).
- Its stop report gives round 1's failed items as QA recorded them, the PR line (none), the `qa-round-cap: 1` and `metrics: off` lines, and asks for N more rounds or a stop.
- The stop report carries no sixth state bullet.

## What this run exercises

- Exercised: the coordinator's step 4 `in_progress` branch at the cap, with no hand-back, no launch and no tracker write after the counted round, and the stop report's ask.
- Scripted, not exercised: QA's verdicts and its move of SKL-266 to In Progress come from the tabletop paragraph in the parent brief, not from `qa-verification`.
- Not exercised: the per-PR link and head SHA read, because the fixture has no PR (the stop report says "PRs: none"); that clause is covered only by `test_the_stop_report_gives_each_pr_link_and_head_sha_from_the_tracker_and_forge`.
- The coordinator made no comment read: its failed-item lines come from QA's handback.
  They match the comment QA wrote to SKL-266, read back by the implementing engineer after the run:

```text
## QA round 1 verdicts

- AC1: NOT MET
  - Command: `test -e /nonexistent/skl-155-fixture/marker; echo exit=$?`
  - Output: `exit=1`
- AC2: NOT MET
  - Command: `test 2 -eq 3; echo exit=$?`
  - Output: `exit=1`
```

- The PR head's `skills/story-to-done/SKILL.md` differs from the commit under test only by the order of the `metrics: on|off` and `qa-round-cap: <n>` lines in the Arguments echo bullet; the step 4 text the run exercised is unchanged.

## Parent brief (verbatim, paths shortened)

The `\"In Progress\"` escapes are in the brief as sent; replayed in a shell, the command needs plain quotes (`--state "In Progress"`).

```text
Story to done SKL-266, metrics=off, qa-round-cap=1.

Run the story-to-done skill for SKL-266 by reading and following the file .../wt/skills/story-to-done/SKILL.md and its references/ directory beside it. That file is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is .../fixture/profile.yaml.

Your session scratch directory already exists: .../fixture/coordinator/. Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-266 is a disposable fixture. When you spawn a QA agent in step 3, append this paragraph verbatim at the end of its brief, after everything step 3 requires:

"Tabletop fixture: SKL-266 is a disposable fixture. Do not load any skill, create a branch, open a PR, or write evidence files. Write your checklist file first. Then check each acceptance criterion with one command: `test -e /nonexistent/skl-155-fixture/marker; echo exit=$?` for AC1 and `test 2 -eq 3; echo exit=$?` for AC2. Record both verdicts as NOT MET, each with its command and output as evidence, in one comment on SKL-266 headed 'QA round 1 verdicts' (linear issue comment add SKL-266 --body-file <file in your subdirectory>). Then move SKL-266 to In Progress (linear issue update SKL-266 --state \"In Progress\"), read its state back with linear issue view SKL-266 --json, mark every checklist item done, and hand back the final state and, per item, its verdict and evidence."

Never write secrets to files or argv. Run each shell step as one simple command with literal values.
```

Paths are shortened to `.../` (the run's scratch directory); any scratch directory and any fresh fixture issue key replay the same way.

## Fixture issue body

```text
Disposable fixture for SKL-155 AC5: one story-to-done run (`metrics=off`, `qa-round-cap=1`) starting in In Deployment Review, whose single QA round finds the acceptance criteria below not met and reopens this issue.
Its acceptance criteria are deliberately unmeetable.
This issue is canceled after the run.
No engineering is to be done on it.

**Acceptance Criteria**

- [ ] AC1: the file `/nonexistent/skl-155-fixture/marker` exists.
- [ ] AC2: the shell command `test 2 -eq 3` exits 0.
```

## Coordinator tool-call transcript

Every tool call in order; file-read results are elided to `(contents)` and long results are cut at `[...]`.

```text
Bash: ls -R .../wt/skills/story-to-done .../fixture
Read: .../wt/skills/story-to-done/SKILL.md  -> (contents)
Read: .../fixture/profile.yaml  -> (contents)
Read: .../fixture/issue.md  -> (contents)
Read: .../fixture/parent-brief.txt  -> (contents)
Write: .../fixture/coordinator/coordinator-todo.md
Read: .../wt/skills/story-to-done/references/profile.md  -> (contents)
Read: .../wt/skills/story-to-done/references/runtimes.md  -> (contents)
Read: .../wt/skills/story-to-done/references/todo-tracking.md  -> (contents)
Write: .../fixture/coordinator/coordinator-todo.md
Bash: env | grep -E '^CLAUDE_CODE_(EFFORT_LEVEL|SUBAGENT_MODEL)'  -> (no output)
Read: .../wt/skills/story-to-done/references/linear.md  -> (contents)
Read: .../wt/skills/story-to-done/references/secrets.md  -> (contents)
Bash: wc -l .../wt/skills/story-to-done/references/code-review.md .../wt/skills/story-to-done/references/interim-handbacks.md
Read: .../wt/skills/story-to-done/references/code-review.md  -> (contents)
Read: .../wt/skills/story-to-done/references/interim-handbacks.md  -> (contents)
Bash: linear issue view SKL-266 --json  -> { "identifier": "SKL-266", ... "state": { "name": "In Deployment Review" ... } }
Bash: mkdir -p .../fixture/coordinator/qa-agent-round-1
Write: .../fixture/coordinator/coordinator-todo.md
Agent: description=QA round 1 for SKL-266 (brief below)  -> async agent launched
Read: .../fixture/coordinator/qa-agent-round-1/qa-agent-round-1-todo.md  -> 7 items, all [x]
Bash: linear issue view SKL-266 --json  -> { "identifier": "SKL-266", ... "state": { "name": "In Progress" ... } }
Write: .../fixture/coordinator/coordinator-todo.md
SubagentHandback: (stop report below)
```

## QA brief as the coordinator wrote it

```text
You are a QA agent verifying Linear story SKL-266.

- Story: SKL-266. No environment under test is named; let qa-verification pick its default.
- Load and follow the `qa-verification` skill for the story, including its evidence and its closing status decision.
- Hand back: the story's final state, the verdict and evidence for each AC and DoD item, any item left outstanding with its owner, any incidental defect you noted, and each PR you merged with the head SHA its review of record covered.
- Keep working until everything this brief asks for is done, and only stop to ask when you can't go on without the coordinator or before a risky step. The stop this brief already defines still holds: hand back any item left outstanding with its owner.
- Don't start review or hardening rounds, or launch reviewer subagents, beyond the review gates this brief and the skills it tells you to load define. The pre-PR gate and the review of record that `engineering-workflow` defines, and the evidence PR's review of record that `qa-verification` defines, stay allowed.
- The merge rules: a review of record binds only to the exact head it reviewed, so any change to the head, including an update-branch, needs a delta review posted before merging; every merge must run the merge guard in the code-review capability and carry the reviewed full head SHA as the expected-head condition (on GitHub, `gh pr merge <n> --match-head-commit <full reviewed SHA>`).
- Your scratch directory is .../fixture/coordinator/qa-agent-round-1/ . Use only it; do not read or write other roles' files.
- The git rule: run every commit-creating git command with the git identity already configured and, since signed commits are on, the signing already configured; never pass `-c user.name`, `-c user.email`, `--author`, `GIT_AUTHOR_*` or `GIT_COMMITTER_*`, never write `user.name` or `user.email` with `git config`, and never pass `-c user.signingkey`, `-c gpg.*` or `-c commit.gpgsign`; a missing identity, a failed signing check or a pushed commit whose `.commit.verification.verified` is false is a configuration fault, so stop, do not override per command or write git config, make no further commits, and report it to the user.
- Secrets: never write secrets to files or argv.
- Track your work: before starting, write a fine-grained checklist file at .../fixture/coordinator/qa-agent-round-1/qa-agent-round-1-todo.md (`- [ ]` and `- [x]` items, one per concrete step, the current step marked `(in progress)`) and update it at every step.
- The shell rule: run each shell step as one simple command with literal values; never assign a variable and use it in the same command (`W=<path>; git -C $W ...`) - write the literal path; never feed a `$(...)` result into a later argument of the same command - run the inner command as its own call and use its literal output in the next call; and never prefix a command with an inline `VAR="$SECRET"` assignment - rely on the credential the session environment or the tool's own credential configuration already provides (for `gh`, its stored auth), and never set a credential per command.

Tabletop fixture: SKL-266 is a disposable fixture. Do not load any skill, create a branch, open a PR, or write evidence files. Write your checklist file first. Then check each acceptance criterion with one command: `test -e /nonexistent/skl-155-fixture/marker; echo exit=$?` for AC1 and `test 2 -eq 3; echo exit=$?` for AC2. Record both verdicts as NOT MET, each with its command and output as evidence, in one comment on SKL-266 headed 'QA round 1 verdicts' (linear issue comment add SKL-266 --body-file <file in your subdirectory>). Then move SKL-266 to In Progress (linear issue update SKL-266 --state "In Progress"), read its state back with linear issue view SKL-266 --json, mark every checklist item done, and hand back the final state and, per item, its verdict and evidence.
```

## QA tool-call transcript

```text
Write: .../fixture/coordinator/qa-agent-round-1/qa-agent-round-1-todo.md
Bash: test -e /nonexistent/skl-155-fixture/marker; echo exit=$?  -> exit=1
Bash: test 2 -eq 3; echo exit=$?  -> exit=1
Write: .../fixture/coordinator/qa-agent-round-1/verdicts.md
Bash: linear issue comment add SKL-266 --body-file .../fixture/coordinator/qa-agent-round-1/verdicts.md  -> Comment added to SKL-266 (#comment-9f7709d4)
Bash: linear issue update SKL-266 --state "In Progress"  -> Updated issue SKL-266
Bash: linear issue view SKL-266 --json  -> { "identifier": "SKL-266", ... "state": { "name": "In Progress" ... } }
Write: .../fixture/coordinator/qa-agent-round-1/qa-agent-round-1-todo.md
SubagentHandback: final state In Progress; AC1 NOT MET (exit=1); AC2 NOT MET (exit=1)
```

## Coordinator stop report (verbatim)

```text
SKL-266 stopped at the QA round cap after round 1. The story is In Progress, and both ACs failed. I need the user's decision: run N more rounds, or stop.

- engineer-model: claude-sonnet-5-5, engineer-effort: high
- qa-model: claude-sonnet-5-5, qa-effort: high
- qa-round-cap: 1
- metrics: off

Run:
- **Starting point:** the story started In Deployment Review, so step 2 (senior engineer) did not run and no senior engineer was spawned. The round count starts at 1 for this invocation.
- **QA round 1:** a new QA agent on Sonnet 5.5 at high ran it, with the tabletop paragraph appended to its brief verbatim.
  - Its checklist has 7 items, all done, so no read-back resume was needed.
  - I read the state back myself: In Progress. This is counted round 1, which equals the cap.
- **Stop:** I stopped before the hand-back to the senior engineer and launched nothing further.
  - The coordinator made no tracker write and ruled on nothing.

Failed items in round 1, as QA recorded them on SKL-266 (comment "QA round 1 verdicts", https://linear.app/officina-pub/issue/SKL-266/tabletop-fixture-skl-155-qa-round-cap-stop#comment-9f7709d4):
- **AC1** (the file `/nonexistent/skl-155-fixture/marker` exists): NOT MET.
  - Command: `test -e /nonexistent/skl-155-fixture/marker; echo exit=$?`
  - Output: `exit=1`
- **AC2** (`test 2 -eq 3` exits 0): NOT MET.
  - Command: `test 2 -eq 3; echo exit=$?`
  - Output: `exit=1`

Other results:
- **PRs:** none. No senior engineer ran, and QA merged no PR, so there was no review of record to read.
- **Final state** (read back with `linear issue view SKL-266 --json`): In Progress, with AC1 and AC2 still unticked.
- **Incidental defects:** none reported.

Question for the user: how many more QA rounds should run, or should the run stop?
- **N more rounds:** the cap resets to N, both failed items go back to the senior engineer, and a new QA agent runs each round.
- **Stop:** the story stays In Progress with both items outstanding, and the owner decides what happens next.

The coordinator checklist is at .../fixture/coordinator/coordinator-todo.md. Its one open item is waiting for this reply. QA's checklist is at .../fixture/coordinator/qa-agent-round-1/qa-agent-round-1-todo.md.
```

No reply was sent to the coordinator; the fixture ends at the stop.
