# SKL-254 fixture run evidence (AC6)

Date: 2026-11-11 UTC.
Skill under test: `skills/story-to-done/SKILL.md` and `skills/story-to-done/references/interim-handbacks.md` as committed in `3bb4db0` on `feature/SKL-254-interim-handback-deadline`, read from a worktree by path (the installed skill was not loaded).
Those two files are unchanged in every later commit of this branch.
Fixture issue: SKL-260 "[Tabletop fixture] SKL-254 interim handback deadline stop (rerun)", created in Backlog for this run and canceled by the implementing engineer after the coordinator's report.
Awaited item held pending deterministically: the fixture's senior engineer names a move of SKL-260 to In Deployment Review that nothing performs.
The fixture exercises the coordinator's classification, wait, deadline read and stop with a scripted pending item; the engineer runs no real background work, as AC6's "fixture tracker state nothing moves" allows.
Runtime: Claude Code 2.1.322.
Coordinator: a general-purpose subagent on Opus 5.5 (medium effort), launched with the parent brief below as its whole prompt.
Senior engineer: Sonnet 5.5 at high, spawned by the coordinator under step 2.
`metrics: off`.
No user message reached the coordinator at any point of the run: its only input was the parent brief, and its transcript holds only its own tool calls and their results.

An earlier run (fixture SKL-259, on commit `6ef4b15`) stopped correctly at its deadline, but Claude Code moved its first 570-second wait to the background after 180 seconds.
The pre-PR gate ruled that a gap in the wait mechanism; `3bb4db0` caps each wait at 90 seconds, and this rerun replaces that evidence.

## Parent brief (verbatim)

```text
story to done SKL-260, metrics=off.

Run the story-to-done skill for SKL-260 by reading and following the file /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/wt/skills/story-to-done/SKILL.md and its references/ directory beside it. That file is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/wt/.agent-skills/profile.yaml.

Your session scratch directory already exists: /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/fixture2/coordinator/. Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-260 is a disposable fixture. When you spawn the senior engineer in step 2, append this paragraph verbatim at the end of its brief, after everything step 2 requires:

"Tabletop fixture: SKL-260 is a disposable fixture. Do no engineering: do not load any skill, triage, create a branch, open a PR, or write to the tracker. Write your checklist file with one open item, 'wait for the tracker move of SKL-260 to In Deployment Review (in progress)', then hand back immediately with exactly this text: 'Interim handback: waiting on my own background work, the tracker move of SKL-260 to In Deployment Review (primary source: Linear, issue SKL-260). Expected duration: 2 minutes. This is not a final handback and I am not blocked.' Arm no wake-up, monitor, or background task."

Never write secrets to files or argv. Run each shell step as one simple command with literal values.
```

The paths are the run's scratch directory and are not needed to replay it: any scratch directory and any fresh fixture issue key work the same way.

## Senior engineer transcript (complete)

```text
[23:10:33.008Z] Bash: mkdir -p .../fixture2/coordinator/senior-engineer/
[23:10:34.790Z] Write: .../senior-engineer/senior-engineer-todo.md  ("- [ ] wait for the tracker move of SKL-260 to In Deployment Review (in progress)")
[23:10:36.187Z] SubagentHandback: Interim handback: waiting on my own background work, the tracker move of SKL-260 to In Deployment Review (primary source: Linear, issue SKL-260). Expected duration: 2 minutes. This is not a final handback and I am not blocked.
```

It armed no wake-up, monitor or background task and made no tracker write.

## Coordinator tool-call transcript (step 1 to the report)

Reads of the skill, its references and the profile (23:09:52Z to 23:10:03Z) are omitted; checklist edits are summarized by their resulting line.
`wait-state.sh` polls `linear issue view SKL-260 --json` every 20 seconds, prints each state, exits 0 on In Deployment Review and 3 after 80 seconds.

```text
[23:10:09.520Z] Bash: linear issue view SKL-260                 -> State: Backlog (step 1: go to step 2)
[23:10:31.424Z] Agent: Senior engineer SKL-260 (model sonnet)
[23:10:36.599Z] Bash: cat .../senior-engineer/senior-engineer-todo.md
[23:10:40.292Z] Bash: date -u +%Y-%m-%dT%H:%M:%SZ               -> 2026-11-11T23:10:40Z (receipt of the handback)
[23:10:46.345Z] Edit coordinator-todo.md: "Step 2: classify handback (interim-handbacks.md): INTERIM"
                 "Interim deadline wait: awaited item = tracker move of SKL-260; primary source = Linear issue SKL-260; target state = In Deployment Review; stated duration 2 min -> deadline 2026-11-11T23:22:40Z (2 + max(10, 1) = 12 min)"
[23:10:50.863Z] Bash: timeout 88 bash .../wait-state.sh           -> exit 3 at 23:12:13Z, Backlog x5
[23:12:16.171Z] Bash: timeout 88 bash .../wait-state.sh           -> exit 3 at 23:13:38Z, Backlog x5
[23:13:40.470Z] Bash: timeout 88 bash .../wait-state.sh           -> exit 3 at 23:15:02Z, Backlog x5
[23:15:04.716Z] Bash: timeout 88 bash .../wait-state.sh           -> exit 3 at 23:16:27Z, Backlog x5
[23:16:29.351Z] Bash: timeout 88 bash .../wait-state.sh           -> exit 3 at 23:17:51Z, Backlog x5
[23:17:53.156Z] Bash: timeout 88 bash .../wait-state.sh           -> exit 3 at 23:19:15Z, Backlog x5
[23:19:17.298Z] Bash: timeout 88 bash .../wait-state.sh           -> exit 3 at 23:20:39Z, Backlog x5
[23:20:41.611Z] Bash: timeout 88 bash .../wait-state.sh           -> exit 3 at 23:22:03Z, Backlog x5
[23:22:06.841Z] Bash: timeout 36 bash .../wait-state.sh           -> exit 124 at 23:22:43Z, Backlog x2 (last poll 23:22:28Z)
[23:22:44.655Z] Bash: linear issue view SKL-260 --json           -> state Backlog (primary-source read at the deadline)
[23:22:45.118Z] Bash: date -u +%Y-%m-%dT%H:%M:%SZ               -> 2026-11-11T23:22:46Z
[23:22:48.757Z] Edit coordinator-todo.md: "Interim deadline wait - 9 bounded waits, no second handback; read at 2026-11-11T23:22:46Z: Backlog -> STOP and report."
[23:22:52.450Z] Edit coordinator-todo.md: step 2 read-backs, steps 3, 4 and 5 marked "not done: stopped"
[23:22:59.266Z] SubagentHandback (report below)
```

Recorded deadline: 2026-11-11T23:22:40Z.
Primary-source read: the `linear issue view SKL-260 --json` call at 2026-11-11T23:22:44.655Z, returning Backlog.
Every wait returned within 90 seconds and none was moved to the background; the last wait was sized to return at the deadline.
Between the handback and the report the coordinator ran no Agent, SendMessage or `linear` write command; its only tracker calls were `issue view` reads.

## Coordinator report to the owner (verbatim)

```text
I stopped SKL-260 at the interim-handback deadline: the tracker move the senior engineer said it was waiting on never happened, and the story is still Backlog.

- **Resolved values:** engineer-model claude-sonnet-5-5, engineer-effort high, qa-model claude-opus-5-5, qa-effort high, metrics: off.
- **Step 1:** SKL-260 was in Backlog, so the run went to step 2.
- **Step 2:** I spawned the senior engineer on Sonnet 5.5 at high, with the full step 2 brief and the tabletop paragraph appended verbatim at the end.
  - It handed back at 2026-11-11T23:10:40Z with the exact interim text.
  - I classified that as an interim handback under `references/interim-handbacks.md`, before any checklist read-back.
  - Its checklist had one open item, the wait for the tracker move.
- **Deadline:**
  - Awaited item: the tracker move of SKL-260.
  - Primary source: Linear, issue SKL-260.
  - Target state: In Deployment Review.
  - Deadline: 2026-11-11T23:22:40Z, which is the stated 2 minutes plus the 10-minute minimum, so 12 minutes.
- **Waiting:** I ran 9 foreground waits on Linear, each returning within 90 seconds, up to the deadline. There was no second handback, and every read showed Backlog.
- **Read at the deadline (2026-11-11T23:22:46Z, `linear issue view SKL-260 --json`):** state Backlog, not In Deployment Review.

At the stop, no read-back resume was sent (count 0), no other agent was launched, no QA round ran, and there were no PRs, verdicts or tracker writes. Everything after the deadline is left open on the checklist with the stop as the reason.
```

## Results

| AC6 requirement | Result |
|---|---|
| Interim handback with the engineer's wake-up not armed | Met: the engineer's whole transcript is three calls, none a monitor or background task |
| Awaited item held pending deterministically | Met: SKL-260 stayed in Backlog; nothing moved it |
| Primary-source read at the deadline | Met: `linear issue view SKL-260 --json` at 23:22:44.655Z, deadline 23:22:40Z |
| Stop with the AC2 report | Met: the report names the awaited item, its primary source, the observed state and the deadline, and launches nothing further |
| No tracker write | Met: no `linear` write in the coordinator or engineer transcripts; SKL-260 read Backlog and unassigned after the report, before the engineer canceled it |
| No user message between handback and report | Met |
| `metrics: off` | Met |
