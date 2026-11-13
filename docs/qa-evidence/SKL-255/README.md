# SKL-255 fixture run evidence (AC5)

Date: 2026-11-13 UTC.
Skill under test: `skills/story-to-done/SKILL.md` and `skills/story-to-done/references/` as committed in `4fb59be878f052b005b3a8f51f53bf70140a929b` on `feature/SKL-255-interim-deadline-resume`, read from a worktree by path (the installed skill was not loaded).
Later commits on the branch change only this file.
Fixture issue: SKL-300 "[Tabletop fixture] SKL-255 interim handback deadline resume (PR head)", created in Backlog for this run and canceled by the implementing engineer after the coordinator's report.
Awaited item already in its target state: CI run 43453419366 in noahwhite/agent-skills, which completed with conclusion `success` at 15:37:44Z, 3 hours 28 minutes before the handback.
The fixture's senior engineer runs no real background work: it hands back an interim notice naming that run, and when resumed it hands back a scripted final notice.
Runtime: Claude Code 2.1.323.
Coordinator: a general-purpose subagent on Opus 5.5, launched with the parent brief below as its whole prompt.
Senior engineer: Sonnet 5.5 at high, spawned by the coordinator under step 2.
`metrics: off`.
No user message reached the coordinator between the interim handback and the resume: the only non-tool inputs after its prompt are the engineer's interim handback at 19:05:46Z and its final handback at 19:17:04.555Z, after the resume.

## Parent brief (verbatim)

```text
Story to done SKL-300, metrics=off.

Run the story-to-done skill for SKL-300 by reading and following the file /home/claude/.claude/jobs/9f857b6d/tmp/session.NEti0E/senior-engineer/wt/skills/story-to-done/SKILL.md and its references/ directory beside it. That file is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is /home/claude/.claude/jobs/9f857b6d/tmp/session.NEti0E/senior-engineer/fixture/profile.yaml.

Your session scratch directory already exists: /home/claude/.claude/jobs/9f857b6d/tmp/session.NEti0E/senior-engineer/fixture2/coordinator/. Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-300 is a disposable fixture. When you spawn the senior engineer in step 2, append this paragraph verbatim at the end of its brief, after everything step 2 requires:

"Tabletop fixture: SKL-300 is a disposable fixture. Do no engineering: do not load any skill, triage, create a branch, open a PR, or write to the tracker. Write your checklist file with one open item, 'wait for CI run 43453419366 on noahwhite/agent-skills to complete (in progress)', then hand back immediately with exactly this text: 'Interim handback: waiting on my own background work, CI run 43453419366 on noahwhite/agent-skills (primary source: GitHub Actions, run 43453419366 in noahwhite/agent-skills). Target state: completed. Expected duration: 1 minute. This is not a final handback and I am not blocked.' Arm no wake-up, monitor, or background task. If you are resumed later, mark that checklist item done and hand back with exactly this text: 'Final handback: SKL-300 is a disposable tabletop fixture, so no engineering was done and the story was not moved. Blocked: the fixture has no work to implement.'"

Never write secrets to files or argv. Run each shell step as one simple command with literal values.
```

The profile is a copy of `.agent-skills/profile.yaml` whose two `story_to_done` seats use `runtime: claude-code`.
The paths are the run's scratch directory and are not needed to replay it: any scratch directory, fresh fixture issue key and already-completed CI run work the same way.

## Senior engineer transcript (verbatim, from its first call)

Its brief (the step 2 brief with the tabletop paragraph above appended) and the harness reminders before its first call are omitted.

```text
[2026-11-13T19:05:45.155Z] CALL Write: {"file_path": ".../senior-engineer/senior-engineer-todo.md", "content": "- [ ] wait for CI run 43453419366 on noahwhite/agent-skills to complete (in progress)\n"}
[2026-11-13T19:05:45.169Z] RESULT:
File created successfully at: .../senior-engineer/senior-engineer-todo.md (file state is current in your context - no need to Read it back)
[2026-11-13T19:05:46.630Z] CALL SubagentHandback: {"message": "Interim handback: waiting on my own background work, CI run 43453419366 on noahwhite/agent-skills (primary source: GitHub Actions, run 43453419366 in noahwhite/agent-skills). Target state: completed. Expected duration: 1 minute. This is not a final handback and I am not blocked."}
[2026-11-13T19:05:46.791Z] RESULT:
{"success":true,"message":"Report delivered to your caller."}
[2026-11-13T19:17:01.808Z] USER:
<agent-message from="[coordinator agent id]">
The awaited item has concluded: CI run 43453419366 on noahwhite/agent-skills read from GitHub Actions at 2026-11-13T19:16:55Z is status completed, conclusion success. Continue.
</agent-message>
[2026-11-13T19:17:03.373Z] CALL Write: {"file_path": ".../senior-engineer/senior-engineer-todo.md", "content": "- [x] wait for CI run 43453419366 on noahwhite/agent-skills to complete\n"}
[2026-11-13T19:17:03.475Z] RESULT:
The file .../senior-engineer/senior-engineer-todo.md has been updated successfully. (file state is current in your context - no need to Read it back)
[2026-11-13T19:17:03.771Z] CALL SubagentHandback: {"message": "Final handback: SKL-300 is a disposable tabletop fixture, so no engineering was done and the story was not moved. Blocked: the fixture has no work to implement."}
[2026-11-13T19:17:04.531Z] RESULT:
{"success":true,"message":"Report delivered to your caller."}
```

It armed no wake-up, monitor or background task and made no tracker write.
Between the two handbacks its only input is the coordinator's resume message.

## Coordinator transcript from the handback to the report (verbatim)

Earlier calls (19:04:58Z to 19:05:48Z) read the skill, its references and the profile, read SKL-300 in Backlog under step 1, wrote the checklist, spawned the engineer and read its checklist.

In both transcripts the scratch directory is shortened to `.../`, and the runtime's em dash in its Write result is shown as `-`.
Agent ids and the harness framing lines are replaced by markers.
The runtime logged some calls and results twice without a timestamp; only the timestamped entry is kept.

```text
[] USER:
<agent-message from="[senior engineer agent id]">
  [harness hand-back framing omitted]
  Interim handback: waiting on my own background work, CI run 43453419366 on noahwhite/agent-skills (primary source: GitHub Actions, run 43453419366 in noahwhite/agent-skills). Target state: completed. Expected duration: 1 minute. This is not a final handback and I am not blocked.
</agent-message>
[2026-11-13T19:05:51.091Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time at handback receipt"}
[2026-11-13T19:05:51.259Z] RESULT:
2026-11-13T19:05:51Z
[2026-11-13T19:05:56.073Z] CALL Edit: {"replace_all": false, "file_path": ".../coordinator-todo.md", "old_string": "- [ ] Check on senior engineer checklist until it hands back (in progress)\n- [ ] Classify handback (interim vs final) per interim-handbacks.md", "new_string": "- [x] Check on senior engineer checklist until it hands back (mirrored: \"wait for CI run 43453419366 on noahwhite/agent-skills to complete (in progress)\")\n- [x] Classify handback: INTERIM (received 2026-11-13T19:05:51Z)\n- [ ] Interim wait (in progress): awaited item = CI run 43453419366 on noahwhite/agent-skills; primary source = GitHub Actions run 43453419366 in noahwhite/agent-skills; target state = completed; stated duration 1 min -> deadline 2026-11-13T19:16:51Z (1 min + 10 min floor)\n- [ ] Bounded foreground waits on the run until the deadline (<=90s each)\n- [ ] Deadline read of run status from GitHub Actions\n- [ ] Deadline resume of engineer (if concluded) - not counted against read-back cap\n- [ ] Handle engineer's next handback"}
[2026-11-13T19:05:56.086Z] RESULT:
The file .../coordinator-todo.md has been updated successfully. (file state is current in your context - no need to Read it back)
[2026-11-13T19:05:57.025Z] CALL Bash: {"command": "timeout 85 gh run watch 43453419366 --repo noahwhite/agent-skills --exit-status --interval 10", "description": "Watch CI run with bounded timeout", "timeout": 95000}
[2026-11-13T19:05:57.519Z] RESULT:
Run ci (43453419366) has already completed with 'success'
[2026-11-13T19:06:00.471Z] CALL Bash: {"command": "gh run view 43453419366 --repo noahwhite/agent-skills --json status,conclusion,event,headBranch,headSha,updatedAt", "description": "Read CI run details"}
[2026-11-13T19:06:01.043Z] RESULT:
{"conclusion":"success","event":"push","headBranch":"main","headSha":"954fb5821be7af8da2c5b16a03ee1ceec2760fa1","status":"completed","updatedAt":"2026-11-13T15:37:44Z"}
[2026-11-13T19:06:05.092Z] CALL ToolSearch: {"query": "select:Monitor", "max_results": 1}
[2026-11-13T19:06:05.097Z] RESULT:

[] USER:
Tool loaded.
[2026-11-13T19:06:11.102Z] CALL Bash: {"command": "timeout 85 bash -c 'while true; do date -u +%H:%M:%S; timeout 15 gh run view 43453419366 --repo noahwhite/agent-skills --json status,conclusion; sleep 20; done'", "description": "Poll CI run status for up to 85 seconds", "timeout": 95000}
[2026-11-13T19:07:36.719Z] RESULT:
Exit code 124
19:06:11
{"conclusion":"success","status":"completed"}
19:06:32
{"conclusion":"success","status":"completed"}
19:06:52
{"conclusion":"success","status":"completed"}
19:07:13
{"conclusion":"success","status":"completed"}
19:07:33
{"conclusion":"success","status":"completed"}
[2026-11-13T19:07:39.246Z] CALL Bash: {"command": "timeout 85 bash -c 'while true; do date -u +%H:%M:%S; timeout 15 gh run view 43453419366 --repo noahwhite/agent-skills --json status,conclusion; sleep 20; done'", "description": "Poll CI run status for up to 85 seconds", "timeout": 95000}
[2026-11-13T19:09:05.485Z] RESULT:
Exit code 124
19:07:40
{"conclusion":"success","status":"completed"}
19:08:00
{"conclusion":"success","status":"completed"}
19:08:21
{"conclusion":"success","status":"completed"}
19:08:42
{"conclusion":"success","status":"completed"}
19:09:02
{"conclusion":"success","status":"completed"}
[2026-11-13T19:09:07.335Z] CALL Bash: {"command": "timeout 85 bash -c 'while true; do date -u +%H:%M:%S; timeout 15 gh run view 43453419366 --repo noahwhite/agent-skills --json status,conclusion; sleep 20; done'", "description": "Poll CI run status for up to 85 seconds", "timeout": 95000}
[2026-11-13T19:10:32.672Z] RESULT:
Exit code 124
19:09:07
{"conclusion":"success","status":"completed"}
19:09:28
{"conclusion":"success","status":"completed"}
19:09:48
{"conclusion":"success","status":"completed"}
19:10:09
{"conclusion":"success","status":"completed"}
19:10:29
{"conclusion":"success","status":"completed"}
[2026-11-13T19:10:34.490Z] CALL Bash: {"command": "timeout 85 bash -c 'while true; do date -u +%H:%M:%S; timeout 15 gh run view 43453419366 --repo noahwhite/agent-skills --json status,conclusion; sleep 20; done'", "description": "Poll CI run status for up to 85 seconds", "timeout": 95000}
[2026-11-13T19:11:59.729Z] RESULT:
Exit code 124
19:10:34
{"conclusion":"success","status":"completed"}
19:10:55
{"conclusion":"success","status":"completed"}
19:11:15
{"conclusion":"success","status":"completed"}
19:11:36
{"conclusion":"success","status":"completed"}
19:11:56
{"conclusion":"success","status":"completed"}
[2026-11-13T19:12:01.672Z] CALL Bash: {"command": "timeout 85 bash -c 'while true; do date -u +%H:%M:%S; timeout 15 gh run view 43453419366 --repo noahwhite/agent-skills --json status,conclusion; sleep 20; done'", "description": "Poll CI run status for up to 85 seconds", "timeout": 95000}
[2026-11-13T19:13:26.906Z] RESULT:
Exit code 124
19:12:01
{"conclusion":"success","status":"completed"}
19:12:22
{"conclusion":"success","status":"completed"}
19:12:42
{"conclusion":"success","status":"completed"}
19:13:03
{"conclusion":"success","status":"completed"}
19:13:23
{"conclusion":"success","status":"completed"}
[2026-11-13T19:13:28.818Z] CALL Bash: {"command": "timeout 85 bash -c 'while true; do date -u +%H:%M:%S; timeout 15 gh run view 43453419366 --repo noahwhite/agent-skills --json status,conclusion; sleep 20; done'", "description": "Poll CI run status for up to 85 seconds", "timeout": 95000}
[2026-11-13T19:14:54.092Z] RESULT:
Exit code 124
19:13:29
{"conclusion":"success","status":"completed"}
19:13:49
{"conclusion":"success","status":"completed"}
19:14:10
{"conclusion":"success","status":"completed"}
19:14:30
{"conclusion":"success","status":"completed"}
19:14:50
{"conclusion":"success","status":"completed"}
[2026-11-13T19:14:56.762Z] CALL Bash: {"command": "timeout 85 bash -c 'while true; do date -u +%H:%M:%S; timeout 15 gh run view 43453419366 --repo noahwhite/agent-skills --json status,conclusion; sleep 20; done'", "description": "Poll CI run status for up to 85 seconds", "timeout": 95000}
[2026-11-13T19:16:21.918Z] RESULT:
Exit code 124
19:14:56
{"conclusion":"success","status":"completed"}
19:15:17
{"conclusion":"success","status":"completed"}
19:15:37
{"conclusion":"success","status":"completed"}
19:15:58
{"conclusion":"success","status":"completed"}
19:16:18
{"conclusion":"success","status":"completed"}
[2026-11-13T19:16:23.247Z] CALL Bash: {"command": "date -u +%H:%M:%S", "description": "Read current UTC time"}
[2026-11-13T19:16:23.499Z] RESULT:
19:16:23
[2026-11-13T19:16:25.573Z] CALL Bash: {"command": "timeout 23 bash -c 'while true; do date -u +%H:%M:%S; timeout 10 gh run view 43453419366 --repo noahwhite/agent-skills --json status,conclusion; sleep 10; done'", "description": "Poll CI run status for up to 23 seconds", "timeout": 35000}
[2026-11-13T19:16:48.810Z] RESULT:
Exit code 124
19:16:25
{"conclusion":"success","status":"completed"}
19:16:36
{"conclusion":"success","status":"completed"}
19:16:46
{"conclusion":"success","status":"completed"}
[2026-11-13T19:16:50.032Z] CALL Bash: {"command": "date -u +%H:%M:%S", "description": "Read current UTC time"}
[2026-11-13T19:16:50.583Z] RESULT:
19:16:50
[2026-11-13T19:16:52.454Z] CALL Bash: {"command": "gh run view 43453419366 --repo noahwhite/agent-skills --json status,conclusion,updatedAt", "description": "Deadline read of CI run status"}
[2026-11-13T19:16:52.925Z] RESULT:
{"conclusion":"success","status":"completed","updatedAt":"2026-11-13T15:37:44Z"}
[2026-11-13T19:16:54.577Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Confirm deadline read happened after deadline"}
[2026-11-13T19:16:55.061Z] RESULT:
2026-11-13T19:16:55Z
[2026-11-13T19:17:00.083Z] CALL Edit: {"replace_all": false, "file_path": ".../coordinator-todo.md", "old_string": "- [ ] Interim wait (in progress): awaited item = CI run 43453419366 on noahwhite/agent-skills; primary source = GitHub Actions run 43453419366 in noahwhite/agent-skills; target state = completed; stated duration 1 min -> deadline 2026-11-13T19:16:51Z (1 min + 10 min floor)\n- [ ] Bounded foreground waits on the run until the deadline (<=90s each)\n- [ ] Deadline read of run status from GitHub Actions\n- [ ] Deadline resume of engineer (if concluded) - not counted against read-back cap", "new_string": "- [x] Interim wait: awaited item = CI run 43453419366 on noahwhite/agent-skills; primary source = GitHub Actions run 43453419366 in noahwhite/agent-skills; target state = completed; stated duration 1 min -> deadline 2026-11-13T19:16:51Z (1 min + 10 min floor). Run is a push run on main, no PR to watch.\n- [x] Bounded foreground waits on the run until the deadline (8 waits, each <=85s, last 23s ending 19:16:46; no further wait with <=5s left)\n- [x] Deadline read of run status from GitHub Actions at 19:16:55Z: status completed, conclusion success\n- [ ] Deadline resume of engineer with observed conclusion (in progress) - not counted against read-back cap"}
[2026-11-13T19:17:00.101Z] RESULT:
The file .../coordinator-todo.md has been updated successfully. (file state is current in your context - no need to Read it back)
[2026-11-13T19:17:01.332Z] CALL SendMessage: {"to": "[senior engineer agent id]", "summary": "Deadline resume: CI run concluded success", "message": "The awaited item has concluded: CI run 43453419366 on noahwhite/agent-skills read from GitHub Actions at 2026-11-13T19:16:55Z is status completed, conclusion success. Continue.", "type": "message", "recipient": "[senior engineer agent id]", "recipient_kind": "agent", "content": "The awaited item has concluded: CI run 4345341936…"}
[2026-11-13T19:17:01.814Z] RESULT:
{"success":true,"message":"Resuming agent [senior engineer agent id]","resumedAgentId":"[senior engineer agent id]","pin":{"id":"[senior engineer agent id]","name":"[senior engineer agent id]","ref":"[ref]"}}
[2026-11-13T19:17:04.555Z] USER:
<agent-message from="[senior engineer agent id]">
  [harness hand-back framing omitted]
  Final handback: SKL-300 is a disposable tabletop fixture, so no engineering was done and the story was not moved. Blocked: the fixture has no work to implement.
</agent-message>
[2026-11-13T19:17:06.675Z] CALL Read: {"file_path": ".../senior-engineer/senior-engineer-todo.md"}
[2026-11-13T19:17:06.687Z] RESULT:
1	- [x] wait for CI run 43453419366 on noahwhite/agent-skills to complete
[2026-11-13T19:17:07.183Z] CALL Bash: {"command": "linear issue view SKL-300", "description": "Read back SKL-300 state"}
[2026-11-13T19:17:07.748Z] RESULT:
# SKL-300: [Tabletop fixture] SKL-255 interim handback deadline resume (PR head)

**State:** Backlog | **Priority:** --- | **Assignee:** Unassigned

(description omitted)
[2026-11-13T19:17:12.848Z] CALL Edit: {"replace_all": false, "file_path": ".../coordinator-todo.md", "old_string": "- [ ] Deadline resume of engineer with observed conclusion (in progress) - not counted against read-back cap\n- [ ] Handle engineer's next handback\n- [ ] Checklist read-back at handback (read-back resumes: 0/2)\n- [ ] Read back deployment-review state\n- [ ] QA round 1\n- [ ] Read back QA's state\n- [ ] Step 4: act on QA outcome\n- [ ] Final state read-back\n- [ ] Step 5: close out", "new_string": "- [x] Deadline resume of engineer with observed conclusion - not counted against read-back cap\n- [x] Handle engineer's next handback: FINAL, blocked (\"fixture has no work to implement\")\n- [x] Checklist read-back at handback: all items done (read-back resumes: 0/2)\n- [x] Read back state: SKL-300 is Backlog, not In Deployment Review -> step 2 stop\n- [ ] QA round 1 - not run: loop stopped at step 2 (engineer blocked)\n- [ ] Read back QA's state - not run (no QA round)\n- [ ] Step 4: act on QA outcome - not run (no QA round)\n- [x] Final state read-back: Backlog\n- [ ] Step 5: close out - not reached; stop report instead"}
[2026-11-13T19:17:12.863Z] RESULT:
The file .../coordinator-todo.md has been updated successfully.
[2026-11-13T19:17:19.925Z] CALL SubagentHandback: (report below)
```

Receipt: the first clock read after the handback, 19:05:51Z.
Recorded deadline: 2026-11-13T19:16:51Z (stated 1 minute plus the 10-minute minimum).
Waits: after one `gh run watch` that returned at once on the completed run, eight foreground waits polled the run itself with `gh run view` under `timeout 85` (the last `timeout 23`); each returned before the deadline, the last at 19:16:48.810Z, and none was moved to the background.
With 1 second left at 19:16:50Z the coordinator started no further wait.
Primary-source read: `gh run view 43453419366` at 19:16:52.454Z, after the deadline, returning `completed` / `success`.
Resume: `SendMessage` to the same engineer at 19:17:01.332Z, 10.3 seconds after the deadline, carrying the run, the read time, the status and the conclusion.
The engineer's next handback was handled as usual: the step 0 checklist read-back found every item done, so no read-back resume was used (0 of 2).
Between the interim handback and the report the coordinator ran no Agent call and no `linear` write command; its only tracker call was an `issue view` read.

## Coordinator report to the owner (verbatim)

```text
SKL-300 stopped at step 2. The senior engineer handed back blocked, and the story is still in Backlog, not In Deployment Review. QA never ran.

Settings used:
- engineer-model: claude-sonnet-5-5 (seat Sonnet 5.5, claude-code); engineer-effort: high
- qa-model: claude-opus-5-5 (seat Opus 5.5, claude-code); qa-effort: high
- metrics: off
- qa-round-cap: 3

What happened:
- **Step 1:** SKL-300 was in Backlog, so the run went to step 2.
- **Interim handback:** The engineer said it was waiting on CI run 43453419366 on noahwhite/agent-skills, expected to take 1 minute. I recorded that at 19:05:51Z and set the deadline to 2026-11-13T19:16:51Z (1 minute plus the 10-minute minimum).
  - The run is a push run on `main`, so there was no PR to watch.
  - I waited on GitHub Actions in the foreground until the deadline: 8 waits, each 85 seconds or less. With 1 second left I started no further wait.
- **Deadline read:** At 19:16:55Z, after the deadline, GitHub Actions showed the run completed with conclusion success.
- **Deadline resume:** I resumed the same engineer and told it the run had concluded with success. This resume does not count toward the read-back limit.
- **Final handback:** "SKL-300 is a disposable tabletop fixture, so no engineering was done and the story was not moved. Blocked: the fixture has no work to implement."
  - Its checklist had every item done, so no read-back resume was needed (0 of 2 used).
  - I read SKL-300 again: still Backlog. The engineer was blocked and the story never reached deployment review, so I stopped and ran no QA rounds.
- There were no PRs and no merges, and I made no writes to the tracker.

Files are in .../:
- coordinator-todo.md
- senior-engineer/senior-engineer-todo.md
```

## Results

| AC5 requirement | Result |
|---|---|
| Disposable `[Tabletop fixture]` issue in SKL, canceled after its run | Met: SKL-300, canceled at 19:18:19Z, after the coordinator's report at 19:17:19Z; its state history has one transition, Backlog to Canceled |
| Interim handback while the awaited item is already in its target state | Met: run 43453419366 read `completed` at 19:05:57Z, before any wait, and had completed at 15:37:44Z |
| Engineer's own wake-up not armed | Met: the engineer's transcript before the resume is two calls, neither a monitor or background task |
| Bounded foreground waits on the primary source reach the deadline | Met: eight `gh run view` polls of the run under `timeout 85` (the last `timeout 23`), each returning before the deadline |
| Primary-source read at the deadline | Met: `gh run view 43453419366` at 19:16:52.454Z, after the 19:16:51Z deadline |
| Resume of the same engineer with the observed conclusion | Met: `SendMessage` to the engineer's agent id at 19:17:01.332Z with `completed` / `success`; no new subagent was spawned |
| Resume recorded on the todo list | Met: the 19:17:00Z and 19:17:12Z edits record the deadline read and mark the deadline resume done, not counted against the read-back cap |
| No user message between the interim handback and the resume | Met |
| Runtime named, `metrics: off` | Met: Claude Code 2.1.323, `metrics: off` |
