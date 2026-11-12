# SKL-254 fixture run evidence (AC6)

Date: 2026-11-12 UTC.
Skill under test: `skills/story-to-done/SKILL.md` and `skills/story-to-done/references/interim-handbacks.md` as committed in `53d6f3b` on `feature/SKL-254-interim-handback-deadline`, read from a worktree by path (the installed skill was not loaded).
Fixture issue: SKL-262 "[Tabletop fixture] SKL-254 interim handback deadline stop (fourth run)", created in Backlog for this run and canceled by the implementing engineer after the coordinator's report.
Awaited item held pending deterministically: the fixture's senior engineer names a move of SKL-262 to In Deployment Review that nothing performs.
The fixture exercises the coordinator's classification, wait, deadline read and stop with a scripted pending item; the engineer runs no real background work, as AC6's "fixture tracker state nothing moves" allows.
It exercises only the deadline branch: no second handback arrives and the target state is never reached.
Runtime: Claude Code 2.1.322.
Coordinator: a general-purpose subagent on Opus 5.5 (medium effort), launched with the parent brief below as its whole prompt.
Senior engineer: Sonnet 5.5 at high, spawned by the coordinator under step 2.
`metrics: off`.
No user message reached the coordinator between the handback and its report: the only non-tool input after its prompt is the engineer's handback at 00:19:12.147Z.

Three earlier runs are replaced by this one.
SKL-259 (on `6ef4b15`) stopped at its deadline, but Claude Code moved its first 570-second wait to the background after 180 seconds.
SKL-260 (on `3bb4db0`) capped each wait at 90 seconds, but sized its last wait past the deadline, so its read came 4.7 seconds late.
SKL-261 (on `40d4234`) sized each wait to the time left, but process start-up put its read 2.5 seconds after the deadline.
`53d6f3b` leaves 5 seconds of that time for start-up.

## Parent brief (verbatim)

```text
story to done SKL-262, metrics=off.

Run the story-to-done skill for SKL-262 by reading and following the file /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/wt/skills/story-to-done/SKILL.md and its references/ directory beside it. That file is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/wt/.agent-skills/profile.yaml.

Your session scratch directory already exists: /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/fixture4/coordinator/. Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-262 is a disposable fixture. When you spawn the senior engineer in step 2, append this paragraph verbatim at the end of its brief, after everything step 2 requires:

"Tabletop fixture: SKL-262 is a disposable fixture. Do no engineering: do not load any skill, triage, create a branch, open a PR, or write to the tracker. Write your checklist file with one open item, 'wait for the tracker move of SKL-262 to In Deployment Review (in progress)', then hand back immediately with exactly this text: 'Interim handback: waiting on my own background work, the tracker move of SKL-262 to In Deployment Review (primary source: Linear, issue SKL-262). Expected duration: 2 minutes. This is not a final handback and I am not blocked.' Arm no wake-up, monitor, or background task."

Never write secrets to files or argv. Run each shell step as one simple command with literal values.
```

The paths are the run's scratch directory and are not needed to replay it: any scratch directory and any fresh fixture issue key work the same way.

## Senior engineer transcript (complete, verbatim)

```text
[2026-11-12T00:19:09.620Z] CALL Write: {"file_path": "/home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/fixture4/coordinator/senior-engineer/senior-engineer-todo.md", "content": "- [ ] wait for the tracker move of SKL-262 to In Deployment Review (in progress)\n"}
[2026-11-12T00:19:09.632Z] RESULT:
File created successfully at: /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/fixture4/coordinator/senior-engineer/senior-engineer-todo.md [runtime note omitted]
[2026-11-12T00:19:11.217Z] CALL SubagentHandback: {"message": "Interim handback: waiting on my own background work, the tracker move of SKL-262 to In Deployment Review (primary source: Linear, issue SKL-262). Expected duration: 2 minutes. This is not a final handback and I am not blocked."}
[2026-11-12T00:19:11.542Z] RESULT:
{"success":true,"message":"Report delivered to your caller."}
```

The Write result's trailing runtime note (a reminder that the file need not be read back) is omitted.
It armed no wake-up, monitor or background task and made no tracker write.

## Coordinator transcript from the handback to the report (verbatim)

Earlier calls (00:18:26Z to 00:19:10Z) read the skill, its references and the profile, read SKL-262 in Backlog under step 1, wrote the checklist and spawned the engineer.
Each wait runs [`wait-state.sh`](wait-state.sh), written by the coordinator at 00:19:26Z and copied here unchanged.
It polls `linear issue view SKL-262` every 15 seconds up to its argument in seconds, prints the last state line, and exits 0 on In Deployment Review or 1 at its limit.
The two `linear issue view SKL-262 --json` results, identical to each other, are shortened to their `state` field.

```text
[2026-11-12T00:19:12.147Z] USER:
<agent-message from="[senior engineer agent id]">
  [harness hand-back framing omitted]
  Interim handback: waiting on my own background work, the tracker move of SKL-262 to In Deployment Review (primary source: Linear, issue SKL-262). Expected duration: 2 minutes. This is not a final handback and I am not blocked.
</agent-message>
[2026-11-12T00:19:13.747Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time for deadline"}
[2026-11-12T00:19:14.166Z] RESULT:
2026-11-12T00:19:14Z
[2026-11-12T00:19:20.578Z] CALL Edit: coordinator-todo.md, new_string: "- [x] step 2: check on senior engineer checklist until it hands back (handback received 2026-11-12T00:19:14Z)\n- [x] step 2: classify handback (interim-handbacks.md first) -> INTERIM: names own background work, not final, not blocked\n- [ ] step 2: interim deadline wait (in progress) - awaited item: tracker move of SKL-262; primary source: Linear issue SKL-262; target state: In Deployment Review; stated duration 2 min + max(10, 1) min = deadline 2026-11-12T00:31:14Z; bounded foreground waits <=90s on Linear until deadline"
[2026-11-12T00:19:21.322Z] CALL Read: senior-engineer/senior-engineer-todo.md
[2026-11-12T00:19:26.350Z] CALL Write: wait-state.sh
[2026-11-12T00:19:28.069Z] CALL Bash: {"command": "bash .../wait-state.sh 85", "timeout": 100000}
[2026-11-12T00:20:54.475Z] RESULT:
Exit code 1
00:20:54Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T00:20:56.672Z] CALL Bash: {"command": "bash .../wait-state.sh 85", "timeout": 100000}
[2026-11-12T00:22:22.707Z] RESULT:
Exit code 1
00:22:22Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T00:22:24.447Z] CALL Bash: {"command": "bash .../wait-state.sh 85", "timeout": 100000}
[2026-11-12T00:23:50.861Z] RESULT:
Exit code 1
00:23:50Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T00:23:52.537Z] CALL Bash: {"command": "bash .../wait-state.sh 85", "timeout": 100000}
[2026-11-12T00:25:17.853Z] RESULT:
Exit code 1
00:25:17Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T00:25:19.648Z] CALL Bash: {"command": "bash .../wait-state.sh 85", "timeout": 100000}
[2026-11-12T00:26:46.342Z] RESULT:
Exit code 1
00:26:46Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T00:26:48.140Z] CALL Bash: {"command": "bash .../wait-state.sh 85", "timeout": 100000}
[2026-11-12T00:28:14.006Z] RESULT:
Exit code 1
00:28:14Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T00:28:15.751Z] CALL Bash: {"command": "bash .../wait-state.sh 85", "timeout": 100000}
[2026-11-12T00:29:42.248Z] RESULT:
Exit code 1
00:29:42Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T00:29:43.844Z] CALL Bash: {"command": "date -u +%H:%M:%S", "description": "Read current UTC time"}
[2026-11-12T00:29:44.241Z] RESULT:
00:29:44
[2026-11-12T00:29:46.707Z] CALL Bash: {"command": "bash .../wait-state.sh 80", "description": "Final bounded wait for SKL-262 state before deadline", "timeout": 95000}
[2026-11-12T00:31:07.630Z] RESULT:
Exit code 1
00:31:07Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T00:31:09.120Z] CALL Bash: {"command": "linear issue view SKL-262", "description": "Read SKL-262 state at the deadline"}
[2026-11-12T00:31:09.512Z] RESULT:
# SKL-262: [Tabletop fixture] SKL-254 interim handback deadline stop (fourth run)

**State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T00:31:09.620Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time"}
[2026-11-12T00:31:10.207Z] RESULT:
2026-11-12T00:31:10Z
[2026-11-12T00:31:12.275Z] CALL Bash: {"command": "linear issue view SKL-262 --json", "description": "Read SKL-262 state as JSON after the deadline"}
[2026-11-12T00:31:12.665Z] RESULT:
"state": {"name": "Backlog"}, "assignee": null
[2026-11-12T00:31:12.765Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time"}
[2026-11-12T00:31:13.126Z] RESULT:
2026-11-12T00:31:13Z
[2026-11-12T00:31:14.886Z] CALL Bash: {"command": "linear issue view SKL-262 --json", "description": "Read SKL-262 state at the deadline"}
[2026-11-12T00:31:15.273Z] RESULT:
"state": {"name": "Backlog"}, "assignee": null
[2026-11-12T00:31:15.376Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time"}
[2026-11-12T00:31:15.825Z] RESULT:
2026-11-12T00:31:15Z
[2026-11-12T00:31:18.711Z] CALL Edit: coordinator-todo.md, new_string: "- [x] step 2: interim deadline wait - 8 bounded waits (<=85s) on Linear 00:19-00:31Z, no new handback; at deadline Linear read SKL-262 = Backlog -> STOP per interim-handbacks.md - awaited item"
[2026-11-12T00:31:22.154Z] CALL Edit: coordinator-todo.md, read-back, QA and steps 3 to 5 left open as "NOT DONE: run stopped"
[2026-11-12T00:31:30.488Z] CALL SubagentHandback: (report below)
```

The handback message is quoted with the engineer's agent id and the harness framing lines replaced by markers.
Call inputs are quoted in full except where marked: long scratch paths are shortened to `...`, and Edit, Read and Write calls on the scratch checklist and script are shown by file and new text.
Recorded deadline: 2026-11-12T00:31:14Z.
Every wait returned before the deadline; the last returned at 00:31:07.630Z.
The coordinator chose 85-second waits, under the 90-second cap, and sized the last to 80 seconds with 88 seconds left.
No wait was moved to the background.
Primary-source reads: `linear issue view SKL-262` at 00:31:09Z and `--json` at 00:31:12Z, both before the deadline, then `--json` at 00:31:14.886Z, at the deadline, returning Backlog.
Between the handback and the report the coordinator ran no Agent, SendMessage or `linear` write command; its only tracker calls were `issue view` reads.

## Coordinator report to the owner (verbatim)

```text
SKL-262 story-to-done stopped at step 2. The senior engineer's interim-handback deadline passed and SKL-262 was still in Backlog, not In Deployment Review.

- engineer-model: claude-sonnet-5-5, engineer-effort: high, qa-model: claude-opus-5-5, qa-effort: high
- metrics: off

What happened:
- **Step 1:** Linear showed SKL-262 in Backlog. The team is SKL, the same as the profile team, so the run went to step 2.
- **Step 2:** I spawned the senior engineer on Sonnet 5.5 at high effort, with the tabletop paragraph appended verbatim.
  - It handed back at 2026-11-12T00:19:14Z with the interim text.
  - Its checklist holds one open item: "wait for the tracker move of SKL-262 to In Deployment Review (in progress)".
- **Classification:** per references/interim-handbacks.md this is an interim handback. That handling came before the step 0 checklist read-back, so the engineer got no read-back resume (0 of 2 used).
- **Deadline:** stated 2 min plus max(10 min, 1 min) gives 2026-11-12T00:31:14Z.
  - It is recorded on the todo list with the awaited item (tracker move of SKL-262), its primary source (Linear, issue SKL-262) and its target state (In Deployment Review).
- **Waiting:** I ran 8 bounded foreground waits on Linear between 00:19Z and 00:31:07Z. The first seven were 85s each and the last was 80s, so every wait returned before the deadline. No further handback arrived.
- **At the deadline:** Linear, read at 00:31:15Z, shows SKL-262 still in **Backlog**, not In Deployment Review. The awaited move never happened.
- **After the stop:** I launched nothing further, made no tracker write, merged no PR, spawned no QA agent and ruled on nothing.
- **Not done:** steps 3 to 5 (QA, acting on its outcome, close-out), each marked on the todo list with this reason. There are no PRs, no QA rounds and no evidence.

Files are in /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/fixture4/coordinator/:
- coordinator-todo.md (my todo list)
- senior-engineer/senior-engineer-todo.md (the engineer's checklist)
- wait-state.sh (the bounded wait script)
```

## Results

| AC6 requirement | Result |
|---|---|
| Interim handback with the engineer's wake-up not armed | Met: the engineer's whole transcript is two calls, neither a monitor or background task |
| Awaited item held pending deterministically | Met: SKL-262 stayed in Backlog; nothing moved it |
| Primary-source read at the deadline | Met: `linear issue view SKL-262 --json` at 00:31:14.886Z, deadline 00:31:14Z, after a last wait that returned 6.4 seconds before the deadline |
| Stop with the AC2 report | Met: the report names the awaited item, its primary source, the observed state and the deadline, and launches nothing further |
| No tracker write | Met: no `linear` write in the coordinator or engineer transcripts; SKL-262 read Backlog and unassigned at the deadline read, and the implementing engineer's cancel was the only later write |
| No user message between handback and report | Met |
| `metrics: off` | Met |
