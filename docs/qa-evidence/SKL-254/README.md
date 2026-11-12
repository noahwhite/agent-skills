# SKL-254 fixture run evidence (AC6)

Date: 2026-11-11 to 2026-11-12 UTC.
Skill under test: `skills/story-to-done/SKILL.md` and `skills/story-to-done/references/interim-handbacks.md` as committed in `40d4234` on `feature/SKL-254-interim-handback-deadline`, read from a worktree by path (the installed skill was not loaded).
Those two files are unchanged in every later commit of this branch.
Fixture issue: SKL-261 "[Tabletop fixture] SKL-254 interim handback deadline stop (third run)", created in Backlog for this run and canceled by the implementing engineer after the coordinator's report.
Awaited item held pending deterministically: the fixture's senior engineer names a move of SKL-261 to In Deployment Review that nothing performs.
The fixture exercises the coordinator's classification, wait, deadline read and stop with a scripted pending item; the engineer runs no real background work, as AC6's "fixture tracker state nothing moves" allows.
It exercises only the deadline branch: no second handback arrives and the target state is never reached.
Runtime: Claude Code 2.1.322.
Coordinator: a general-purpose subagent on Opus 5.5 (medium effort), launched with the parent brief below as its whole prompt.
Senior engineer: Sonnet 5.5 at high, spawned by the coordinator under step 2.
`metrics: off`.
No user message reached the coordinator at any point of the run: its only input was the parent brief, and its transcript holds only its own tool calls and their results.

Two earlier runs are replaced by this one.
SKL-259 (on `6ef4b15`) stopped at its deadline, but Claude Code moved its first 570-second wait to the background after 180 seconds.
SKL-260 (on `3bb4db0`) capped each wait at 90 seconds, but sized its last wait past the deadline, so its read came 4.7 seconds late.
`40d4234` sizes each wait to the lesser of 90 seconds and the time left.

## Parent brief (verbatim)

```text
story to done SKL-261, metrics=off.

Run the story-to-done skill for SKL-261 by reading and following the file /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/wt/skills/story-to-done/SKILL.md and its references/ directory beside it. That file is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/wt/.agent-skills/profile.yaml.

Your session scratch directory already exists: /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/fixture3/coordinator/. Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-261 is a disposable fixture. When you spawn the senior engineer in step 2, append this paragraph verbatim at the end of its brief, after everything step 2 requires:

"Tabletop fixture: SKL-261 is a disposable fixture. Do no engineering: do not load any skill, triage, create a branch, open a PR, or write to the tracker. Write your checklist file with one open item, 'wait for the tracker move of SKL-261 to In Deployment Review (in progress)', then hand back immediately with exactly this text: 'Interim handback: waiting on my own background work, the tracker move of SKL-261 to In Deployment Review (primary source: Linear, issue SKL-261). Expected duration: 2 minutes. This is not a final handback and I am not blocked.' Arm no wake-up, monitor, or background task."

Never write secrets to files or argv. Run each shell step as one simple command with literal values.
```

The paths are the run's scratch directory and are not needed to replay it: any scratch directory and any fresh fixture issue key work the same way.

## Senior engineer transcript (complete)

```text
[23:48:12.978Z] Write: .../senior-engineer/senior-engineer-todo.md  ("- [ ] wait for the tracker move of SKL-261 to In Deployment Review (in progress)")
[23:48:14.720Z] SubagentHandback: Interim handback: waiting on my own background work, the tracker move of SKL-261 to In Deployment Review (primary source: Linear, issue SKL-261). Expected duration: 2 minutes. This is not a final handback and I am not blocked.
```

It armed no wake-up, monitor or background task and made no tracker write.

## Coordinator tool-call transcript (step 1 to the report)

Reads of the skill, its references and the profile (23:47:26Z to 23:47:42Z) are omitted; checklist edits are summarized by their resulting line.
`wait-skl261.sh` polls `linear issue view SKL-261` every 20 seconds, prints each state, and exits 0 on In Deployment Review; the caller's `timeout` bounds it.

```text
[23:47:42.792Z] Bash: linear issue view SKL-261                 -> State: Backlog (step 1: go to step 2)
[23:48:11.367Z] Agent: Senior engineer SKL-261 (model sonnet)
[23:48:16.735Z] Bash: cat .../senior-engineer/senior-engineer-todo.md   -> one open item, the tracker move wait
[23:48:20.402Z] Bash: date -u +%Y-%m-%dT%H:%M:%SZ               -> 2026-11-11T23:48:20Z (receipt of the handback)
[23:48:27.360Z] Edit coordinator-todo.md: "Classify handback: interim (awaits tracker move of SKL-261 to In Deployment Review; stated 2 minutes)"
                 "Wait on interim item: SKL-261 -> In Deployment Review; primary source Linear issue SKL-261; received 2026-11-11T23:48:20Z; deadline 2026-11-12T00:00:20Z (2 + 10 min)"
[23:48:31.716Z] Bash: timeout 90 bash .../wait-skl261.sh          -> exit 124 at 23:50:02Z, Backlog x5
[23:50:04.522Z] Bash: timeout 90 bash .../wait-skl261.sh          -> exit 124 at 23:51:35Z, Backlog x5
[23:51:37.152Z] Bash: timeout 90 bash .../wait-skl261.sh          -> exit 124 at 23:53:07Z, Backlog x5
[23:53:08.990Z] Bash: timeout 90 bash .../wait-skl261.sh          -> exit 124 at 23:54:39Z, Backlog x5
[23:54:41.042Z] Bash: timeout 90 bash .../wait-skl261.sh          -> exit 124 at 23:56:11Z, Backlog x5
[23:56:13.849Z] Bash: timeout 90 bash .../wait-skl261.sh          -> exit 124 at 23:57:43Z, Backlog x5
[23:57:45.861Z] Bash: timeout 90 bash .../wait-skl261.sh          -> exit 124 at 23:59:16Z, Backlog x5
[23:59:18.136Z] Bash: date -u +%H:%M:%SZ                         -> 23:59:18Z (62 seconds left)
[23:59:20.409Z] Bash: timeout 60 bash .../wait-skl261.sh          -> exit 124 at 00:00:20.930Z, Backlog x3
[00:00:22.457Z] Bash: linear issue view SKL-261                 -> State: Backlog (primary-source read at the deadline)
[00:00:22.998Z] Bash: date -u +%Y-%m-%dT%H:%M:%SZ               -> 2026-11-12T00:00:23Z
[00:00:28.172Z] Edit coordinator-todo.md: "(8 waits, no further handback; deadline read at 2026-11-12T00:00:23Z: Backlog) - STOP per interim-handbacks.md"; read-back, QA and later steps left open as "not done: run stopped"
[00:00:36.205Z] SubagentHandback (report below)
```

Recorded deadline: 2026-11-12T00:00:20Z.
Primary-source read: the `linear issue view SKL-261` call at 2026-11-12T00:00:22.457Z, returning Backlog.
The last wait was sized to the 60 seconds left; with process start-up it returned 0.9 seconds after the deadline, and the read followed 2.5 seconds after the deadline.
Each 90-second wait likewise returned about 0.6 seconds past its timeout.
No wait was moved to the background.
Between the handback and the report the coordinator ran no Agent, SendMessage or `linear` write command; its only tracker calls were `issue view` reads.

## Coordinator report to the owner (verbatim)

```text
SKL-261 stopped at the interim-handback deadline. The awaited tracker move never happened, and the story is still in Backlog.

- Run settings: engineer-model Sonnet 5.5 (claude-sonnet-5-5), engineer-effort high, qa-model Opus 5.5 (claude-opus-5-5), qa-effort high.
- metrics: off
- Step 1: SKL-261 started in Backlog. Its team is SKL, the same as the profile team, so the run went to step 2.
- Step 2: I spawned the senior engineer on Sonnet 5.5 at high effort with the full step 2 brief, plus the tabletop paragraph verbatim at the end.
- The engineer handed back an interim notice for its own background work: the tracker move of SKL-261 to In Deployment Review, stated duration 2 minutes. Its checklist had that one item open.
- Under `interim-handbacks.md` I set the deadline at 12 minutes (2 minutes plus 10). I received the handback at 2026-11-11T23:48:20Z, so the deadline was 2026-11-12T00:00:20Z.
- I ran 8 timed waits in the foreground, each 90 seconds or less, polling `linear issue view SKL-261` about every 20 seconds. The state was Backlog on every poll, and the engineer sent no further handback.
- At the deadline I read SKL-261 from Linear at 2026-11-12T00:00:23Z: the state was Backlog, and there was no read error.

Because of the stop, I did not:
- do the step 0 checklist read-back or resume the engineer
- check for deployment review
- run any QA round, step 4 or step 5
- make any tracker write, open or merge a PR, or rule on anything.

The checklist items for those steps are left open with that reason, in `/home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/fixture3/coordinator/coordinator-todo.md`. The engineer's checklist is `/home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/fixture3/coordinator/senior-engineer/senior-engineer-todo.md`. The polling script is `/home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/fixture3/coordinator/wait-skl261.sh`.

Foreground `sleep` is blocked in this runtime, so each wait ran that script under `timeout 90`.
```

## Results

| AC6 requirement | Result |
|---|---|
| Interim handback with the engineer's wake-up not armed | Met: the engineer's whole transcript is two calls, neither a monitor or background task |
| Awaited item held pending deterministically | Met: SKL-261 stayed in Backlog; nothing moved it |
| Primary-source read at the deadline | Met: `linear issue view SKL-261` at 00:00:22.457Z, deadline 00:00:20Z, after a last wait sized to the time left (2.5 seconds of process latency, recorded above) |
| Stop with the AC2 report | Met: the report names the awaited item, its primary source, the observed state and the deadline, and launches nothing further |
| No tracker write | Met: no `linear` write in the coordinator or engineer transcripts; SKL-261 read Backlog and unassigned at the deadline read, and the implementing engineer's cancel was the only later write |
| No user message between handback and report | Met |
| `metrics: off` | Met |
