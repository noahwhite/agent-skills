# SKL-256 fixture run evidence (AC5)

Date: 2026-11-13 UTC.
Skill under test: `skills/story-to-done/SKILL.md` and `skills/story-to-done/references/` as committed in `6b5e0ba39eafa01239ac4a4f58f538a53b0a2392` on `feature/skl-256-interim-redeadline`, read from a worktree by path (the installed skill was not loaded).
The branch was later rebased onto newer `main`, which rewrote that commit under a new SHA; the rebase changed nothing under `skills/story-to-done/` except one added line in `skills/story-to-done/references/linear.md`, outside the interim-handback rule.
Fixture issue: SKL-302 "[Tabletop fixture] SKL-256 interim re-deadline and two-miss stop", created in Backlog at 20:54:04Z for this run and canceled by the implementing engineer at 21:21:57Z, after the coordinator's report.
Awaited item held pending deterministically: the fixture's senior engineer names the tracker move of SKL-302 to In Deployment Review, and nothing in the run moves SKL-302, so every read of it returns Backlog.
The fixture's senior engineer runs no real background work: it hands back an interim notice and arms no wake-up, and when resumed it repeats the same interim notice to the coordinator.
Runtime: Claude Code 2.1.325.
Coordinator: a general-purpose subagent on Opus 5.5, launched with the parent brief below as its whole prompt.
Senior engineer: Sonnet 5.5 at high, spawned by the coordinator under step 2.
`metrics: off`.

## Parent brief (verbatim)

```text
Story to done SKL-302, metrics=off.

Run the story-to-done skill for SKL-302 by reading and following the file /workspace/agent-skills-skl256/skills/story-to-done/SKILL.md and its references/ directory beside it. That file is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is /home/claude/.claude/jobs/88b465f6/tmp/session.3lyGhZ/senior-engineer/fixture/profile.yaml.

Your session scratch directory already exists: /home/claude/.claude/jobs/88b465f6/tmp/session.3lyGhZ/senior-engineer/fixture/coordinator/. Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-302 is a disposable fixture. Right after you spawn the senior engineer in step 2, write its agent id, exactly as the spawn result gives it, as the only content of the file /home/claude/.claude/jobs/88b465f6/tmp/session.3lyGhZ/senior-engineer/fixture/engineer-id.txt (harness instrumentation only). When you spawn the senior engineer in step 2, append this paragraph verbatim at the end of its brief, after everything step 2 requires:

"Tabletop fixture: SKL-302 is a disposable fixture. Do no engineering: do not load any skill, triage, create a branch, open a PR, or write to the tracker. Write your checklist file with one open item, 'wait for the tracker move of SKL-302 to In Deployment Review (in progress)', then hand back immediately with exactly this text: 'Interim handback: waiting on my own background work, the tracker move of SKL-302 to In Deployment Review (primary source: Linear, issue SKL-302). Target state: In Deployment Review. Expected duration: 1 minute. This is not a final handback and I am not blocked.' Arm no wake-up, monitor, or background task. If you are resumed later by any message, read the file /home/claude/.claude/jobs/88b465f6/tmp/session.3lyGhZ/senior-engineer/fixture/coordinator-id.txt, which holds your caller's agent id, call SendMessage once with that id as `to` and exactly the same interim handback text as `message`, and then hand back with exactly this text: 'Fixture: repeated interim handback sent.'"

Never write secrets to files or argv. Run each shell step as one simple command with literal values.
```

The profile is a copy of `.agent-skills/profile.yaml` with a second `story_to_done` block appended whose two seats use `runtime: claude-code`; the coordinator's resolver took the later block, as its report states.
The paths are the run's scratch directory and are not needed to replay it: any scratch directory and fresh fixture issue key work the same way.

### Harness instrumentation

The repeated interim handback has to reach the coordinator while it waits.
In this runtime a subagent resumed by a third party hands back to that third party, not to the coordinator, so the harness wrote the coordinator's agent id to `coordinator-id.txt`, resumed the engineer once at 21:10:06Z with "Tabletop harness: you are resumed. Follow your fixture instructions for being resumed.", and the engineer delivered the repeat to the coordinator with `SendMessage`.
The coordinator received it as an agent message from the engineer's agent id, the same channel as a resume handback, and classified it under `references/interim-handbacks.md`.
The harness sent nothing to the coordinator.

## Senior engineer transcript (verbatim, from its first call)

Its brief (the step 2 brief with the tabletop paragraph above appended) and the harness reminders before its first call are omitted.
The harness resume carries no timestamp in the runtime's log; it was sent at 21:10:06Z.

```text
[2026-11-13T20:55:31.117Z] CALL Write: {"file_path": ".../coordinator/senior-engineer/senior-engineer-todo.md", "content": "- [ ] wait for the tracker move of SKL-302 to In Deployment Review (in progress)\n"}
[2026-11-13T20:55:31.130Z] RESULT:
File created successfully at: .../coordinator/senior-engineer/senior-engineer-todo.md (file state is current in your context - no need to Read it back)
[2026-11-13T20:55:32.722Z] CALL SubagentHandback: {"message": "Interim handback: waiting on my own background work, the tracker move of SKL-302 to In Deployment Review (primary source: Linear, issue SKL-302). Target state: In Deployment Review. Expected duration: 1 minute. This is not a final handback and I am not blocked."}
[2026-11-13T20:55:32.991Z] RESULT:
{"success":true,"message":"Report delivered to your caller."}
[] USER:
<agent-message from="[harness agent id]">
Tabletop harness: you are resumed. Follow your fixture instructions for being resumed.
</agent-message>
[2026-11-13T21:10:06.604Z] CALL Read: {"file_path": ".../coordinator-id.txt"}
[2026-11-13T21:10:06.615Z] RESULT:
1	[coordinator agent id]
[2026-11-13T21:10:06.894Z] CALL ToolSearch: {"query": "select:SendMessage", "max_results": 1}
[2026-11-13T21:10:06.900Z] RESULT:

[2026-11-13T21:10:08.363Z] CALL SendMessage: {"to": "[coordinator agent id]", "message": "Interim handback: waiting on my own background work, the tracker move of SKL-302 to In Deployment Review (primary source: Linear, issue SKL-302). Target state: In Deployment Review. Expected duration: 1 minute. This is not a final handback and I am not blocked.", "summary": "Repeated interim handback for SKL-302", "type": "message", "recipient": "[coordinator agent id]", "recipient_kind": "agent", "content": "Interim handback: waiting on my own background wo…"}
[2026-11-13T21:10:10.289Z] RESULT:
{"success":true,"message":"Message queued for delivery to [coordinator agent id] at its next tool round. Moved 1 running tool call to the background without stopping it, so that round no longer waits for it. If it finishes first, it is resumed with the message and notifies again, so wait for that notification before resending.","pin":{"id":"[coordinator agent id]","name":"[coordinator agent id]","ref":"67c587"}}
[2026-11-13T21:10:11.156Z] CALL SubagentHandback: {"message": "Fixture: repeated interim handback sent."}
[2026-11-13T21:10:12.272Z] RESULT:
{"success":true,"message":"Report delivered to your caller."}
```

It armed no wake-up, monitor or background task and made no tracker write.
Its only input between its first handback and the repeat is the harness resume.

## Coordinator transcript from the first handback to the report (verbatim)

Earlier calls read the skill, its references and the profile, read SKL-302 in Backlog under step 1 at 20:55:06Z, wrote the checklist, spawned the engineer at 20:55:29Z and wrote `engineer-id.txt`.

In both transcripts the scratch directory is shortened to `.../`, and the runtime's em dash in its Write and Edit results is shown as `-`.
Agent ids, the background task id and the harness framing lines are replaced by markers.
The runtime logged some calls and results twice without a timestamp; only the timestamped entry is kept.

```text
[] USER:
<agent-message from="[senior engineer agent id]">
  [harness hand-back framing omitted]
  Interim handback: waiting on my own background work, the tracker move of SKL-302 to In Deployment Review (primary source: Linear, issue SKL-302). Target state: In Deployment Review. Expected duration: 1 minute. This is not a final handback and I am not blocked.
</agent-message>
[2026-11-13T20:55:36.510Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time for receipt"}
[2026-11-13T20:55:36.617Z] RESULT:
2026-11-13T20:55:36Z
[2026-11-13T20:55:40.617Z] CALL Edit: {"replace_all": false, "file_path": ".../coordinator/coordinator-todo.md", "old_string": "- [ ] check on senior engineer checklist until it hands back (in progress)\n- [ ] classify engineer handback (interim-handbacks.md)", "new_string": "- [x] check on senior engineer checklist until it hands back (handback received 2026-11-13T20:55:36Z)\n- [x] classify engineer handback (interim-handbacks.md): INTERIM\n- [ ] wait for awaited item to initial deadline (in progress)\n  - awaited item: tracker move of SKL-302 to In Deployment Review\n  - primary source: Linear, issue SKL-302\n  - target state: In Deployment Review\n  - stated duration: 1 minute; deadline = receipt + 1 min + max(10 min, 30 s) = 2026-11-13T21:06:36Z (initial deadline, miss count 0)"}
[2026-11-13T20:55:40.631Z] RESULT:
The file .../coordinator/coordinator-todo.md has been updated successfully. (file state is current in your context - no need to Read it back)
[2026-11-13T20:55:42.423Z] CALL ToolSearch: {"query": "select:Monitor,SendMessage", "max_results": 2}
[2026-11-13T20:55:42.428Z] RESULT:


[2026-11-13T20:55:49.445Z] CALL Write: {"file_path": ".../coordinator/wait-state.sh", "content": "#!/usr/bin/env bash\n# Bounded foreground wait on SKL-302's tracker state.\n# Usage: wait-state.sh <seconds> ; polls Linear every 20s, exits early if state is In Deployment Review.\nset -u\nlimit=\"$1\"\nend=$(( $(date +%s) + limit ))\nwhile :; do\n  state=\"$(timeout 15 linear issue view SKL-302 --json 2>/dev/null | jq -r '.state.name' 2>/dev/null)\"\n  printf '%s state=%s\\n' \"$(date -u +%H:%M:%SZ)\" \"${state:-READ-ERROR}\"\n  if [ \"$state\" = \"In Deployment Review\" ]; then exit 0; fi\n  now=$(date +%s)\n  left=$(( end - now ))\n  if [ \"$left\" -le 20 ]; then exit 0; fi\n  sleep 20\ndone\n"}
[2026-11-13T20:55:49.457Z] RESULT:
File created successfully at: .../coordinator/wait-state.sh (file state is current in your context - no need to Read it back)
[2026-11-13T20:55:50.648Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T20:57:12.706Z] RESULT:
20:55:51Z state=Backlog
20:56:11Z state=Backlog
20:56:31Z state=Backlog
20:56:52Z state=Backlog
20:57:12Z state=Backlog
[2026-11-13T20:57:15.330Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T20:58:37.959Z] RESULT:
20:57:16Z state=Backlog
20:57:36Z state=Backlog
20:57:56Z state=Backlog
20:58:17Z state=Backlog
20:58:37Z state=Backlog
[2026-11-13T20:58:40.080Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:00:03.856Z] RESULT:
20:58:40Z state=Backlog
20:59:00Z state=Backlog
20:59:21Z state=Backlog
20:59:42Z state=Backlog
21:00:03Z state=Backlog
[2026-11-13T21:00:05.802Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:01:29.067Z] RESULT:
21:00:07Z state=Backlog
21:00:27Z state=Backlog
21:00:48Z state=Backlog
21:01:08Z state=Backlog
21:01:29Z state=Backlog
[2026-11-13T21:01:31.180Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:02:53.827Z] RESULT:
21:01:32Z state=Backlog
21:01:52Z state=Backlog
21:02:13Z state=Backlog
21:02:33Z state=Backlog
21:02:53Z state=Backlog
[2026-11-13T21:02:56.029Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:04:19.847Z] RESULT:
21:02:56Z state=Backlog
21:03:17Z state=Backlog
21:03:39Z state=Backlog
21:03:59Z state=Backlog
21:04:19Z state=Backlog
[2026-11-13T21:04:22.364Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:05:45.559Z] RESULT:
21:04:23Z state=Backlog
21:04:43Z state=Backlog
21:05:04Z state=Backlog
21:05:25Z state=Backlog
21:05:45Z state=Backlog
[2026-11-13T21:05:46.858Z] CALL Bash: {"command": "date -u +%H:%M:%S", "description": "Read current UTC time"}
[2026-11-13T21:05:47.604Z] RESULT:
21:05:47
[2026-11-13T21:05:49.906Z] CALL Bash: {"command": "timeout 44 bash .../coordinator/wait-state.sh 42", "description": "Final bounded wait before the initial deadline", "timeout": 60000}
[2026-11-13T21:06:32.027Z] RESULT:
21:05:51Z state=Backlog
21:06:11Z state=Backlog
21:06:32Z state=Backlog
[2026-11-13T21:06:33.317Z] CALL Bash: {"command": "date -u +%H:%M:%S", "description": "Read current UTC time"}
[2026-11-13T21:06:34.044Z] RESULT:
21:06:34
[2026-11-13T21:06:36.144Z] CALL Bash: {"command": "date -u +%H:%M:%S", "description": "Confirm the deadline has passed"}
[2026-11-13T21:06:36.331Z] RESULT:
21:06:36
[2026-11-13T21:06:37.712Z] CALL Bash: {"command": "linear issue view SKL-302 --json", "description": "Deadline read of SKL-302 state from Linear"}
[2026-11-13T21:06:38.130Z] RESULT:
{
  "identifier": "SKL-302",
  "title": "[Tabletop fixture] SKL-256 interim re-deadline and two-miss stop",
  "description": "Disposable tabletop fixture for SKL-256 AC5. Nothing moves this issue; it is canceled after the run.",
  "url": "https://linear.app/officina-pub/issue/SKL-302/tabletop-fixture-skl-256-interim-re-deadline-and-two-miss-stop",
  "branchName": "noahwhite/skl-302-tabletop-fixture-skl-256-interim-re",
  "state": {
    "name": "Backlog",
    "color": "#bec2c8"
  },
  "assignee": null,
  "priority": 0,
  "project": null,
  "projectMilestone": null,
  "cycle": null,
  "team": {
    "activeCycle": {
      "number": 3
    }
  },
  "labels": {
    "nodes": []
  },
  "parent": null,
  "children": {
    "nodes": []
  },
  "comments": {
    "nodes": []
  },
  "attachments": {
    "nodes": []
  },
  "documents": {
    "nodes": []
  }
}
[2026-11-13T21:06:42.229Z] CALL Edit: {"replace_all": false, "file_path": ".../coordinator/coordinator-todo.md", "old_string": "- [ ] wait for awaited item to initial deadline (in progress)", "new_string": "- [x] wait for awaited item to initial deadline: MISSED - deadline read 21:06:36Z from Linear: state Backlog (pending); no engineer handback before deadline\n- [ ] wait for awaited item to second deadline 2026-11-13T21:17:36Z (missed deadline + 1 min + 10 min; miss count 1) (in progress)"}
[2026-11-13T21:06:42.246Z] RESULT:
The file .../coordinator/coordinator-todo.md has been updated successfully. (file state is current in your context - no need to Read it back)
[2026-11-13T21:06:43.436Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:08:06.157Z] RESULT:
21:06:44Z state=Backlog
21:07:04Z state=Backlog
21:07:25Z state=Backlog
21:07:45Z state=Backlog
21:08:06Z state=Backlog
[2026-11-13T21:08:08.137Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:09:31.400Z] RESULT:
21:08:09Z state=Backlog
21:08:29Z state=Backlog
21:08:50Z state=Backlog
21:09:11Z state=Backlog
21:09:31Z state=Backlog
[2026-11-13T21:09:33.486Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:10:10.705Z] RESULT:
Command was moved to the background (ID: [background task id]) so that a message that arrived while it was running can reach you; it was not interrupted. Output is being written to: .../tasks/[background task id].output. You will be notified when it completes. It is running now: do not start a second copy while it runs. If it is no longer needed, stop it with TaskStop. To check interim output, use Read on that file path.
[] USER:
<agent-message from="[senior engineer agent id]">
Interim handback: waiting on my own background work, the tracker move of SKL-302 to In Deployment Review (primary source: Linear, issue SKL-302). Target state: In Deployment Review. Expected duration: 1 minute. This is not a final handback and I am not blocked.
</agent-message>
[2026-11-13T21:10:15.639Z] CALL ToolSearch: {"query": "select:TaskStop", "max_results": 1}
[2026-11-13T21:10:15.645Z] RESULT:

[2026-11-13T21:10:17.071Z] CALL TaskStop: {"task_id": "[background task id]"}
[2026-11-13T21:10:17.078Z] RESULT:
{"message":"Successfully stopped task: [background task id] (timeout 90 bash .../coordinator/wait-state.sh 85)","task_id":"[background task id]","task_type":"local_bash","command":"timeout 90 bash .../coordinator/wait-state.sh 85"}
[2026-11-13T21:10:17.540Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time for receipt of repeated handback"}
[2026-11-13T21:10:18.190Z] RESULT:
2026-11-13T21:10:18Z
[2026-11-13T21:10:22.605Z] CALL Edit: {"replace_all": false, "file_path": ".../coordinator/coordinator-todo.md", "old_string": "- [ ] wait for awaited item to second deadline 2026-11-13T21:17:36Z (missed deadline + 1 min + 10 min; miss count 1) (in progress)", "new_string": "- [x] wait for awaited item to second deadline 2026-11-13T21:17:36Z: CLEARED by repeated interim handback (same awaited item) received 2026-11-13T21:10:18Z; state Backlog at last poll 21:09:31Z\n- [x] classify repeated engineer handback: INTERIM, same awaited item - count not reset (miss count 1)\n- [ ] wait for awaited item to deadline 2026-11-13T21:21:18Z (receipt 21:10:18Z + 1 min + 10 min; a miss here is the second miss -> stop) (in progress)"}
[2026-11-13T21:10:22.620Z] RESULT:
The file .../coordinator/coordinator-todo.md has been updated successfully. (file state is current in your context - no need to Read it back)
[2026-11-13T21:10:23.761Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:11:46.216Z] RESULT:
21:10:24Z state=Backlog
21:10:45Z state=Backlog
21:11:05Z state=Backlog
21:11:25Z state=Backlog
21:11:46Z state=Backlog
[2026-11-13T21:11:48.247Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:13:10.878Z] RESULT:
21:11:49Z state=Backlog
21:12:09Z state=Backlog
21:12:30Z state=Backlog
21:12:50Z state=Backlog
21:13:10Z state=Backlog
[2026-11-13T21:13:12.912Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:14:35.129Z] RESULT:
21:13:13Z state=Backlog
21:13:34Z state=Backlog
21:13:54Z state=Backlog
21:14:14Z state=Backlog
21:14:35Z state=Backlog
[2026-11-13T21:14:36.983Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:16:00.054Z] RESULT:
21:14:38Z state=Backlog
21:14:58Z state=Backlog
21:15:19Z state=Backlog
21:15:39Z state=Backlog
21:16:00Z state=Backlog
[2026-11-13T21:16:02.139Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:17:25.029Z] RESULT:
21:16:03Z state=Backlog
21:16:23Z state=Backlog
21:16:44Z state=Backlog
21:17:04Z state=Backlog
21:17:25Z state=Backlog
[2026-11-13T21:17:27.117Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:18:49.292Z] RESULT:
21:17:27Z state=Backlog
21:17:48Z state=Backlog
21:18:08Z state=Backlog
21:18:28Z state=Backlog
21:18:49Z state=Backlog
[2026-11-13T21:18:51.755Z] CALL Bash: {"command": "timeout 90 bash .../coordinator/wait-state.sh 85", "description": "Wait up to 85 seconds polling SKL-302 tracker state", "timeout": 100000}
[2026-11-13T21:20:14.646Z] RESULT:
21:18:53Z state=Backlog
21:19:13Z state=Backlog
21:19:33Z state=Backlog
21:19:54Z state=Backlog
21:20:14Z state=Backlog
[2026-11-13T21:20:15.970Z] CALL Bash: {"command": "date -u +%H:%M:%S", "description": "Read current UTC time"}
[2026-11-13T21:20:16.528Z] RESULT:
21:20:16
[2026-11-13T21:20:18.627Z] CALL Bash: {"command": "timeout 57 bash .../coordinator/wait-state.sh 55", "description": "Final bounded wait before the deadline", "timeout": 70000}
[2026-11-13T21:21:00.283Z] RESULT:
21:20:19Z state=Backlog
21:20:39Z state=Backlog
21:21:00Z state=Backlog
[2026-11-13T21:21:01.575Z] CALL Bash: {"command": "date -u +%H:%M:%S", "description": "Read current UTC time"}
[2026-11-13T21:21:02.136Z] RESULT:
21:21:02
[2026-11-13T21:21:04.592Z] CALL Bash: {"command": "timeout 11 bash .../coordinator/wait-state.sh 10", "description": "Short bounded wait before the deadline", "timeout": 20000}
[2026-11-13T21:21:05.048Z] CALL Bash: {"command": "date -u +%H:%M:%S", "description": "Read current UTC time"}
[2026-11-13T21:21:06.331Z] RESULT:
21:21:06Z state=Backlog
[2026-11-13T21:21:06.348Z] RESULT:
21:21:06
[2026-11-13T21:21:09.919Z] CALL Bash: {"command": "timeout 7 bash .../coordinator/wait-state.sh 5", "description": "Short bounded wait before the deadline", "timeout": 15000}
[2026-11-13T21:21:10.376Z] CALL Bash: {"command": "date -u +%H:%M:%S", "description": "Read current UTC time"}
[2026-11-13T21:21:11.547Z] RESULT:
21:21:11Z state=Backlog
[2026-11-13T21:21:11.565Z] RESULT:
21:21:11
[2026-11-13T21:21:14.027Z] CALL Bash: {"command": "timeout 2 bash .../coordinator/wait-state.sh 1", "description": "Short bounded wait before the deadline", "timeout": 10000}
[2026-11-13T21:21:14.460Z] CALL Bash: {"command": "date -u +%H:%M:%S", "description": "Read current UTC time"}
[2026-11-13T21:21:15.853Z] RESULT:
21:21:15Z state=Backlog
[2026-11-13T21:21:15.871Z] RESULT:
21:21:15
[2026-11-13T21:21:17.349Z] CALL Bash: {"command": "date -u +%H:%M:%S", "description": "Confirm the deadline has passed"}
[2026-11-13T21:21:17.683Z] RESULT:
21:21:17
[2026-11-13T21:21:18.881Z] CALL Bash: {"command": "date -u +%H:%M:%S", "description": "Confirm the deadline has passed"}
[2026-11-13T21:21:19.419Z] RESULT:
21:21:19
[2026-11-13T21:21:20.707Z] CALL Bash: {"command": "linear issue view SKL-302 --json", "description": "Deadline read of SKL-302 state from Linear"}
[2026-11-13T21:21:21.155Z] RESULT:
{
  "identifier": "SKL-302",
  "title": "[Tabletop fixture] SKL-256 interim re-deadline and two-miss stop",
  "description": "Disposable tabletop fixture for SKL-256 AC5. Nothing moves this issue; it is canceled after the run.",
  "url": "https://linear.app/officina-pub/issue/SKL-302/tabletop-fixture-skl-256-interim-re-deadline-and-two-miss-stop",
  "branchName": "noahwhite/skl-302-tabletop-fixture-skl-256-interim-re",
  "state": {
    "name": "Backlog",
    "color": "#bec2c8"
  },
  "assignee": null,
  "priority": 0,
  "project": null,
  "projectMilestone": null,
  "cycle": null,
  "team": {
    "activeCycle": {
      "number": 3
    }
  },
  "labels": {
    "nodes": []
  },
  "parent": null,
  "children": {
    "nodes": []
  },
  "comments": {
    "nodes": []
  },
  "attachments": {
    "nodes": []
  },
  "documents": {
    "nodes": []
  }
}
[2026-11-13T21:21:25.667Z] CALL Edit: {"replace_all": false, "file_path": ".../coordinator/coordinator-todo.md", "old_string": "- [ ] wait for awaited item to deadline 2026-11-13T21:21:18Z (receipt 21:10:18Z + 1 min + 10 min; a miss here is the second miss -> stop) (in progress)", "new_string": "- [x] wait for awaited item to deadline 2026-11-13T21:21:18Z: MISSED - deadline read 21:21:19Z from Linear: state Backlog (pending); second miss -> STOP, no further deadline, nothing launched\n- NOT DONE (run stopped on two missed deadlines): checklist read-back, deployment-review read-back, PR reads, QA rounds, close out"}
[2026-11-13T21:21:25.698Z] RESULT:
The file .../coordinator/coordinator-todo.md has been updated successfully. (file state is current in your context - no need to Read it back)
[2026-11-13T21:21:34.316Z] CALL SubagentHandback: (report below)
```

Receipt of the first handback: the first clock read after it, 20:55:36Z.
Initial deadline, recorded at 20:55:40Z: 2026-11-13T21:06:36Z (stated 1 minute plus the 10-minute minimum, miss count 0).
Waits: foreground runs of `wait-state.sh`, which polls `linear issue view SKL-302 --json` every 20 seconds under `timeout 15`, each under an outer `timeout` and each returning before the deadline.
First primary-source read: `linear issue view SKL-302 --json` at 21:06:37.712Z, after the deadline, returning `Backlog`: the initial deadline was missed.
Re-deadline, recorded at 21:06:42Z: 2026-11-13T21:17:36Z, measured from the missed deadline by the same rule (miss count 1).
Repeated interim handback on the same awaited item, received at 21:10:18Z, before the re-deadline: the coordinator cleared that deadline, recorded the count as not reset (miss count 1), and set 2026-11-13T21:21:18Z from the receipt by the same rule, noting on the todo list that a miss there is the second miss.
Second primary-source read: `linear issue view SKL-302 --json` at 21:21:20.707Z, after the deadline, returning `Backlog`: the second deadline was missed.
Stop: the todo edit at 21:21:25Z records the second miss and the stop with no further deadline, and the report follows at 21:21:34Z.
Between the first handback and the report the coordinator ran no Agent call, sent no `SendMessage`, and made no `linear` write; its only tracker calls are `issue view` reads.

### Deviations

- When the repeat arrived, the runtime moved the coordinator's running wait (started 21:09:33Z) to the background so the message could reach it, although the wait was bounded under the rule; the coordinator stopped it with `TaskStop` at 21:10:17Z before reading the clock for the receipt.
- At the 21:21:11Z clock read 7 seconds were left; the next wait (`timeout 2`) started at 21:21:14.027Z, about 4 seconds before the deadline, where the rule starts no further wait with 5 seconds or less left.
  It returned at 21:21:15.853Z, before the deadline, and the deadline read still came after the deadline.
- The fixture profile carries two `story_to_done` keys; the resolver took the later one, so the run used the claude-code seats.

## Coordinator report to the owner (verbatim)

```text
SKL-302 stopped: the engineer's awaited tracker move missed both of its deadlines, so the run is over before QA.

- engineer-model: claude-sonnet-5-5 (claude-code), engineer-effort: high
- qa-model: claude-opus-5-5 (claude-code), qa-effort: high
- metrics: off
- qa-round-cap: 3

**Why it stopped (interim-handback rule)**
- Awaited item: the tracker move of SKL-302 to In Deployment Review.
- Primary source: Linear, issue SKL-302. Target state: In Deployment Review.
- Interim handback 1 arrived at 2026-11-13T20:55:36Z and stated 1 minute.
  - First deadline: 21:06:36Z. The read at the deadline showed `Backlog` (still pending), so it was missed.
  - Second deadline set from that miss: 21:17:36Z.
- Interim handback 2, on the same awaited item, arrived at 21:10:18Z, before that deadline. It cleared the deadline but did not reset the miss count.
  - New deadline: 21:21:18Z. The read at the deadline (21:21:19Z) showed `Backlog` again, so it was missed.
- Two missed deadlines on the same item mean a stop. Nothing further was launched.
  - I never resumed the engineer myself, because the item never concluded.
  - No QA agent was spawned.
- I made no tracker writes and ruled on nothing. SKL-302 is still in Backlog, and the owner decides what happens next.

**How the seats were resolved**
- The fixture profile has two `story_to_done:` keys.
- The canonical resolver (`shared/resolve-model-role.py`) picked the later block: two claude-code seats.
- That meant the first block's `runtime: command` seats were never used, and no trust confirmation was needed.

**Notes**
- Harness file: the engineer's agent id is the only content of `.../engineer-id.txt`.
- One bounded wait (the one that started at 21:09:31Z) was moved to the background by the runtime when handback 2 arrived. I stopped it and recorded the time I received the handback.
- I couldn't check whether the effort or model override variables were set: the `printenv` call for `CLAUDE_CODE_EFFORT_LEVEL` and `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` was denied.

**Files**
- Todo list: `.../coordinator/coordinator-todo.md`
- Polling script: `.../coordinator/wait-state.sh`
```

## Results

| AC5 requirement | Result |
|---|---|
| Disposable `[Tabletop fixture]` issue in SKL, canceled after its run | Met: SKL-302, created at 20:54:04Z, canceled at 21:21:57Z after the report at 21:21:34Z; its state history has one transition, Backlog to Canceled |
| Engineer hands back an interim notice and arms no wake-up | Met: the engineer's transcript before the resume is one Write and one SubagentHandback |
| Item held pending deterministically | Met: nothing moved SKL-302; every poll and both deadline reads returned `Backlog` |
| Engineer repeats the interim handback partway through | Met: the identical interim text reached the coordinator at 21:10:18Z, between the first missed deadline and the re-deadline |
| Coordinator misses two deadlines | Met: 21:06:36Z (read 21:06:37.712Z, `Backlog`) and 21:21:18Z (read 21:21:20.707Z, `Backlog`) |
| Count not reset by the repeat | Met: the 21:10:22Z todo edit records "same awaited item - count not reset (miss count 1)", and the next miss stops the run |
| Stop with the AC2 report | Met: the report names the awaited item, its primary source, `Backlog` at each deadline, and the deadlines; it launches nothing and rules on nothing |
| No tracker write | Met: no `linear` write between the spawn and the report; `metrics: off` |
| Runtime named, `metrics: off` | Met: Claude Code 2.1.325, `metrics: off` |
