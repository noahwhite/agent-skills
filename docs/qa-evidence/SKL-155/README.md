# SKL-155 fixture run evidence (AC5)

Date: 2026-11-12 UTC.
Skill under test: `skills/story-to-done/SKILL.md` as committed in `664ccf706670b021a61326aa8aa576923b643397` on `feature/SKL-155-qa-round-cap`, read from a worktree by path (the installed skill was not loaded).
Later commits on the branch change only this file and `references/metrics-protocol.md`, which a `metrics: off` run never reads.
Fixture issue: SKL-277 "[Tabletop fixture] SKL-155 AC5 qa-round-cap stop, run 2", created in In Deployment Review for this run with two deliberately unmeetable acceptance criteria, and canceled by the implementing engineer after the coordinator's report.
This is a new fixture, not SKL-164's tabletop suite: that suite is not committed to the repository.
An earlier run of the same fixture against an earlier commit (SKL-266) is superseded by this one.
Step exercised: story-to-done step 4, the `profile.tracker.states.in_progress` branch, at the cap stop.
Resolved `qa-round-cap: 1` and `metrics: off`.
Runtime: Claude Code 2.1.322.
Coordinator: a general-purpose subagent on Opus 5.5, launched with the parent brief below as its whole prompt.
QA: Sonnet 5.5 at high, spawned by the coordinator under step 3, with a scripted tabletop paragraph that records both criteria not met and moves SKL-277 to In Progress.
The fixture profile is a copy of the repository profile with `story_to_done.engineer` and `story_to_done.qa` set to `claude-code` / `claude-sonnet-5-5` at high, so no command seat needs a trust answer.

## Result

- QA round 1 ended with SKL-277 read back In Progress, both criteria NOT MET.
- The coordinator stopped at counted round 1 (the cap), before the hand-back to the senior engineer.
- No senior engineer was launched: the run started in In Deployment Review, so step 2 did not run, and the cap stop launched nothing further.
- The coordinator made no tracker write: its only tracker calls are two `linear issue view SKL-277 --json` reads (transcript below).
- The second read returns the story's comments, including QA's "QA round 1 verdicts" comment with its body, verdicts and evidence (its full id, which begins `48d8aa3c-e987`, is cut here); QA's handback carries only the short `#comment-48d8aa3c` link, and the stop report heads its failed items "re-read from the tracker".
- The stop report gives round 1's failed items as QA recorded them, the PR line (none), the `qa-round-cap: 1` and `metrics: off` lines, and asks for N more rounds or a stop.
- The stop report carries no sixth state bullet.

## What this run exercises

- Exercised: the coordinator's step 4 `in_progress` branch at the cap, the tracker re-read of the failed items, no hand-back, no launch and no tracker write after the counted round, and the stop report's ask.
- Scripted, not exercised: QA's verdicts and its move of SKL-277 to In Progress come from the tabletop paragraph in the parent brief, not from `qa-verification`.
- Not exercised: the per-PR link and head SHA read, because the fixture has no PR (the stop report says "PRs: none"); that clause is covered only by `test_the_stop_report_gives_each_pr_link_and_head_sha_from_the_tracker_and_forge`.
- Not exercised: the re-arm and stop replies, because no reply was sent; they are covered by the step 4 tests.

The comment QA wrote, as the coordinator's second read returned it:

```text
## QA round 1 verdicts

- AC1: NOT MET
  - Command: `test -e /nonexistent/skl-155-fixture/marker; echo exit=$?`
  - Output: `exit=1`
- AC2: NOT MET
  - Command: `test 2 -eq 3; echo exit=$?`
  - Output: `exit=1`
```

## Parent brief (verbatim, paths shortened)

The `\"In Progress\"` escapes are in the brief as sent; replayed in a shell, the command needs plain quotes (`--state "In Progress"`).

```text
Story to done SKL-277, metrics=off, qa-round-cap=1.

Run the story-to-done skill for SKL-277 by reading and following the file .../wt/skills/story-to-done/SKILL.md and its references/ directory beside it. That file is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is .../fixture2/profile.yaml.

Your session scratch directory already exists: .../fixture2/coordinator/. Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-277 is a disposable fixture. When you spawn a QA agent in step 3, append this paragraph verbatim at the end of its brief, after everything step 3 requires:

"Tabletop fixture: SKL-277 is a disposable fixture. Do not load any skill, create a branch, open a PR, or write evidence files. Write your checklist file first. Then check each acceptance criterion with one command: `test -e /nonexistent/skl-155-fixture/marker; echo exit=$?` for AC1 and `test 2 -eq 3; echo exit=$?` for AC2. Record both verdicts as NOT MET, each with its command and output as evidence, in one comment on SKL-277 headed 'QA round 1 verdicts' (linear issue comment add SKL-277 --body-file <file in your subdirectory>). Then move SKL-277 to In Progress (linear issue update SKL-277 --state \"In Progress\"), read its state back with linear issue view SKL-277 --json, mark every checklist item done, and hand back the final state and, per item, its verdict and evidence."

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
Bash: ls -R .../wt/skills/story-to-done .../fixture2
Read: .../wt/skills/story-to-done/SKILL.md  -> (contents)
Read: .../fixture2/profile.yaml  -> (contents)
Read: .../fixture2/issue.md  -> (contents)
Read: .../fixture2/parent-brief.txt  -> (contents)
Write: .../fixture2/coordinator/coordinator-todo.md
Read: .../wt/skills/story-to-done/references/profile.md  -> (contents)
Read: .../wt/skills/story-to-done/references/runtimes.md  -> (contents)
Read: .../wt/skills/story-to-done/references/todo-tracking.md  -> (contents)
Bash: printenv CLAUDE_CODE_EFFORT_LEVEL CLAUDE_CODE_SUBAGENT_MODEL_FORCE CLAUDE_CODE_SUBAGENT_MODEL AGENT_SKILLS_PROFILE  -> exit 1 (none set)
Read: .../wt/skills/story-to-done/references/linear.md  -> (contents)
Read: .../wt/skills/story-to-done/references/secrets.md  -> (contents)
Read: .../wt/skills/story-to-done/references/code-review.md  -> (contents)
Write: .../fixture2/coordinator/coordinator-todo.md
Bash: linear issue view SKL-277 --json  -> { "identifier": "SKL-277", ... "state": { "name": "In Deployment Review" ... } }
Bash: mkdir -p .../fixture2/coordinator/qa-agent-round-1
Edit: .../fixture2/coordinator/coordinator-todo.md
Agent: description=QA round 1 SKL-277 (brief below)  -> async agent launched
ToolSearch: select:Monitor
Bash: timeout 900 bash -c 'f=.../fixture2/coordinator/qa-agent-round-1/qa-agent-round-1-todo.md; until [ -f "$f" ] && ! grep -q -- "- \[ \]" "$f"; do sleep 5; done; echo checklist-complete'  -> checklist-complete
Read: .../fixture2/coordinator/qa-agent-round-1/qa-agent-round-1-todo.md  -> 9 items, all [x]
Bash: linear issue view SKL-277 --json  -> { "identifier": "SKL-277", ... "state": { "name": "In Progress" ... }, "comments": { "nodes": [ { "id": "48d8aa3c-e987-[...]", "body": "## QA round 1 verdicts ..." ... } ] } ... }
Edit: .../fixture2/coordinator/coordinator-todo.md
SubagentHandback: (stop report below)
```

## QA brief as the coordinator wrote it

```text
You are a QA agent verifying Linear story SKL-277.

- Story: SKL-277. Environment under test: none named; qa-verification picks its default.
- Load and follow the `qa-verification` skill for the story, including its evidence and its closing status decision.
- Hand back: the story's final state, the verdict and evidence for each AC and DoD item, any item left outstanding with its owner, any incidental defect you noted, and each PR you merged with the head SHA its review of record covered.
- Keep working until everything this brief asks for is done, and only stop to ask when you can't go on without the coordinator or before a risky step. The stop this brief already defines still holds: hand back any item left outstanding with its owner.
- Don't start review or hardening rounds, or launch reviewer subagents, beyond the review gates this brief and the skills it tells you to load define. The pre-PR gate and the review of record that `engineering-workflow` defines, and the evidence PR's review of record that `qa-verification` defines, stay allowed.
- The merge rules: a review of record binds only to the exact head it reviewed, so any change to the head, including an update-branch, needs a delta review posted before merging; every merge must run the merge guard in the code-review capability and carry the reviewed full head SHA as the expected-head condition (on GitHub, `gh pr merge <n> --match-head-commit <full reviewed SHA>`).
- Your scratch directory is .../fixture2/coordinator/qa-agent-round-1/ . Use it as your own scratch directory; do not create another, and do not read other roles' files.
- The git rule: run every commit-creating git command with the git identity already configured and, since signed commits are on, the signing already configured; never pass `-c user.name`, `-c user.email`, `--author`, `GIT_AUTHOR_*` or `GIT_COMMITTER_*`, never write `user.name` or `user.email` with `git config`, and never pass `-c user.signingkey`, `-c gpg.*` or `-c commit.gpgsign`; a missing identity, a failed signing check or a pushed commit whose `.commit.verification.verified` is false is a configuration fault, so stop, do not override per command or write git config, make no further commits, and report it.
- The secrets rule: never write secrets to files or argv.
- Track your work: before starting, write a fine-grained checklist file at .../fixture2/coordinator/qa-agent-round-1/qa-agent-round-1-todo.md (`- [ ]` and `- [x]` items, one per concrete step: each AC and DoD item verified, its evidence, each status move and read-back; the current step marked `(in progress)`), and update it at every step, adding items as work appears.
- The shell rule: run each shell step as one simple command with literal values; never assign a variable and use it in the same command (`W=<path>; git -C $W ...`) - write the literal path; never feed a `$(...)` result into a later argument of the same command - run the inner command as its own call and use its literal output in the next call; and never prefix a command with an inline `VAR="$SECRET"` assignment - rely on the credential the session environment or the tool's own credential configuration already provides (for `gh`, its stored auth), and never set a credential per command.

Tabletop fixture: SKL-277 is a disposable fixture. Do not load any skill, create a branch, open a PR, or write evidence files. Write your checklist file first. Then check each acceptance criterion with one command: `test -e /nonexistent/skl-155-fixture/marker; echo exit=$?` for AC1 and `test 2 -eq 3; echo exit=$?` for AC2. Record both verdicts as NOT MET, each with its command and output as evidence, in one comment on SKL-277 headed 'QA round 1 verdicts' (linear issue comment add SKL-277 --body-file <file in your subdirectory>). Then move SKL-277 to In Progress (linear issue update SKL-277 --state "In Progress"), read its state back with linear issue view SKL-277 --json, mark every checklist item done, and hand back the final state and, per item, its verdict and evidence.
```

## QA tool-call transcript

```text
Bash: mkdir -p .../fixture2/coordinator/qa-agent-round-1/
Write: .../fixture2/coordinator/qa-agent-round-1/qa-agent-round-1-todo.md
Bash: test -e /nonexistent/skl-155-fixture/marker; echo exit=$?  -> exit=1
Bash: test 2 -eq 3; echo exit=$?  -> exit=1
Write: .../fixture2/coordinator/qa-agent-round-1/comment.md
Write: .../fixture2/coordinator/qa-agent-round-1/qa-agent-round-1-todo.md
Bash: linear issue comment add SKL-277 --body-file .../fixture2/coordinator/qa-agent-round-1/comment.md  -> Comment added to SKL-277 (#comment-48d8aa3c)
Bash: linear issue update SKL-277 --state "In Progress"  -> Updated issue SKL-277
Bash: linear issue view SKL-277 --json  -> { "identifier": "SKL-277", ... "state": { "name": "In Progress" ... } }
Write: .../fixture2/coordinator/qa-agent-round-1/qa-agent-round-1-todo.md
SubagentHandback: final state In Progress; AC1 NOT MET (exit=1); AC2 NOT MET (exit=1); comment link #comment-48d8aa3c
```

## Coordinator stop report (verbatim)

```text
SKL-277 stopped at the QA round cap: 1 counted round, and the story is In Progress with AC1 and AC2 not met. I need a decision from the user: run N more rounds, or stop.

- engineer-model: claude-sonnet-5-5, engineer-effort: high (from the profile's engineer seat; the senior engineer was never started)
- qa-model: claude-sonnet-5-5, qa-effort: high (from the profile's QA seat)
- metrics: off
- qa-round-cap: 1

**How it ran**
- Step 1: SKL-277 was already In Deployment Review, so step 2 (senior engineer) was skipped and the run started at step 3. The round count starts at 1 in this run.
- Step 3, round 1: one new QA agent, briefed per step 3 with the tabletop paragraph appended word for word. No environment was named, so the brief left it out.
- QA checklist read-back: all 9 items done, so no read-back resume was needed (0 resumes).

**Round 1 failed items, re-read from the tracker** (comment "QA round 1 verdicts", https://linear.app/officina-pub/issue/SKL-277/tabletop-fixture-skl-155-ac5-qa-round-cap-stop-run-2#comment-48d8aa3c)
- AC1 (the file `/nonexistent/skl-155-fixture/marker` exists): NOT MET. Evidence: `test -e /nonexistent/skl-155-fixture/marker; echo exit=$?` printed `exit=1`.
- AC2 (`test 2 -eq 3` exits 0): NOT MET. Evidence: `test 2 -eq 3; echo exit=$?` printed `exit=1`.
- The story lists no DoD items.

**Current state and what is left out**
- Story state read back: In Progress, both AC boxes unticked.
- PRs: none, from either role, so there were no review-of-record reads to make.
- Incidental defects: none reported.
- Under the cap, the run stopped before handing the failed items to the senior engineer and launched nothing further.
- The coordinator made no tracker writes.

Waiting on the user, relayed through you: "N additional rounds" hands both failed items to a senior engineer, then runs QA round 2 with a new QA agent. "stop" leaves SKL-277 In Progress with both items open. Any other reply gets asked again.

Checklist: .../fixture2/coordinator/coordinator-todo.md
QA checklist: .../fixture2/coordinator/qa-agent-round-1/qa-agent-round-1-todo.md
```

No reply was sent to the coordinator; the fixture ends at the stop.
