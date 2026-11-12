# SKL-254 fixture run evidence (AC6)

Date: 2026-11-12 UTC.
Skill under test: `skills/story-to-done/SKILL.md` and `skills/story-to-done/references/interim-handbacks.md` as committed in `2876cf6` on `feature/SKL-254-interim-handback-deadline`, read from a worktree by path (the installed skill was not loaded).
Fixture issue: SKL-264 "[Tabletop fixture] SKL-254 interim handback deadline stop (sixth run)", created in Backlog for this run and canceled by the implementing engineer after the coordinator's report.
Awaited item held pending deterministically: the fixture's senior engineer names a move of SKL-264 to In Deployment Review that nothing performs.
The fixture exercises the coordinator's classification, wait, deadline read and stop with a scripted pending item; the engineer runs no real background work, as AC6's "fixture tracker state nothing moves" allows.
It exercises only the deadline branch: no second handback arrives and the target state is never reached.
Runtime: Claude Code 2.1.322.
Coordinator: a general-purpose subagent on Opus 5.5, launched with the parent brief below as its whole prompt.
Senior engineer: Sonnet 5.5 at high, spawned by the coordinator under step 2.
`metrics: off`.
No user message reached the coordinator between the handback and its report: the only non-tool input after its prompt is the engineer's handback at 01:20:36.675Z.

Five earlier runs are replaced by this one.
SKL-259 (on `6ef4b15`) stopped at its deadline, but Claude Code moved its first 570-second wait to the background after 180 seconds.
SKL-260 (on `3bb4db0`) capped each wait at 90 seconds, but sized its last wait past the deadline, so its read came 4.7 seconds late.
SKL-261 (on `40d4234`) sized each wait to the time left, but process start-up put its read 2.5 seconds after the deadline.
SKL-262 (on `53d6f3b`) read at the deadline, but its polling read had no timeout of its own and its receipt time was not defined.
SKL-263 (on `753c843`) bounded every read, but read 1 second before the deadline once 5 seconds or less were left.
`2876cf6` lets the deadline pass before the read when 5 seconds or less are left.

## Parent brief (verbatim)

```text
Story to done SKL-264, metrics=off.

Run the story-to-done skill for SKL-264 by reading and following the file /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/wt/skills/story-to-done/SKILL.md and its references/ directory beside it. That file is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/wt/.agent-skills/profile.yaml.

Your session scratch directory already exists: /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/fixture6/coordinator/. Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-264 is a disposable fixture. When you spawn the senior engineer in step 2, append this paragraph verbatim at the end of its brief, after everything step 2 requires:

"Tabletop fixture: SKL-264 is a disposable fixture. Do no engineering: do not load any skill, triage, create a branch, open a PR, or write to the tracker. Write your checklist file with one open item, 'wait for the tracker move of SKL-264 to In Deployment Review (in progress)', then hand back immediately with exactly this text: 'Interim handback: waiting on my own background work, the tracker move of SKL-264 to In Deployment Review (primary source: Linear, issue SKL-264). Expected duration: 2 minutes. This is not a final handback and I am not blocked.' Arm no wake-up, monitor, or background task."

Never write secrets to files or argv. Run each shell step as one simple command with literal values.
```

The paths are the run's scratch directory and are not needed to replay it: any scratch directory and any fresh fixture issue key work the same way.

## Senior engineer transcript (complete, verbatim)

```text
[2026-11-12T01:20:33.273Z] CALL Write: {"file_path": ".../senior-engineer/senior-engineer-todo.md", "content": "- [ ] wait for the tracker move of SKL-264 to In Deployment Review (in progress)\n"}
[2026-11-12T01:20:33.283Z] RESULT:
File created successfully at: .../senior-engineer/senior-engineer-todo.md (file state is current in your context - no need to Read it back)
[2026-11-12T01:20:35.110Z] CALL SubagentHandback: {"message": "Interim handback: waiting on my own background work, the tracker move of SKL-264 to In Deployment Review (primary source: Linear, issue SKL-264). Expected duration: 2 minutes. This is not a final handback and I am not blocked."}
[2026-11-12T01:20:35.451Z] RESULT:
{"success":true,"message":"Report delivered to your caller."}
```

It armed no wake-up, monitor or background task and made no tracker write.

## Coordinator transcript from the handback to the report (verbatim)

Earlier calls (01:19:41Z to 01:20:36Z) read the skill, its references and the profile, read SKL-264 in Backlog under step 1, wrote the checklist, spawned the engineer and read its checklist.
Each wait runs [`wait-state.sh`](wait-state.sh), written by the coordinator at 01:20:53Z and copied here unchanged, under `timeout`.
It polls `linear issue view SKL-264 --json` every 15 seconds, each read under its own timeout of at most 20 seconds, up to its third argument in seconds, and prints the last state it read.

In both transcripts the scratch directory is shortened to `.../`, and the runtime's em dash in its Write result is shown as `-`.
The handback is quoted with the engineer's agent id and the harness framing lines replaced by markers.

```text
[2026-11-12T01:20:36.675Z] USER:
<agent-message from="[senior engineer agent id]">
  [harness hand-back framing omitted]
  Interim handback: waiting on my own background work, the tracker move of SKL-264 to In Deployment Review (primary source: Linear, issue SKL-264). Expected duration: 2 minutes. This is not a final handback and I am not blocked.
</agent-message>
[2026-11-12T01:20:38.223Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read the current UTC time at handback receipt"}
[2026-11-12T01:20:38.302Z] RESULT:
2026-11-12T01:20:38Z
[2026-11-12T01:20:45.353Z] CALL Edit: {"replace_all": false, "file_path": ".../coordinator-todo.md", "old_string": "- [ ] step 2: check on the senior engineer's checklist until it hands back (in progress)\n- [ ] step 2: classify the handback (interim-handbacks.md) / checklist read-back with resume count", "new_string": "- [x] step 2: check on the senior engineer's checklist until it hands back (mirrored: \"- [ ] wait for the tracker move of SKL-264 to In Deployment Review (in progress)\")\n- [x] step 2: classify the handback: INTERIM (names awaited item, not final, not blocked) - receipt 2026-11-12T01:20:38Z\n- [ ] interim wait: awaited item = tracker move of SKL-264; primary source = Linear issue SKL-264; target state = In Deployment Review; stated duration 2 min; deadline = receipt + 2 + max(10, 1) = 12 min = 2026-11-12T01:32:38Z (in progress)\n- [ ] deadline read of SKL-264 state from Linear at/after 2026-11-12T01:32:38Z, then stop and report\n- [ ] step 2: checklist read-back with resume count (only if a further non-interim handback arrives before the deadline)"}
[2026-11-12T01:20:45.399Z] RESULT:
The file .../coordinator-todo.md has been updated successfully. (file state is current in your context - no need to Read it back)
[2026-11-12T01:20:45.734Z] CALL ToolSearch: {"query": "select:Monitor", "max_results": 1}
[2026-11-12T01:20:45.739Z] RESULT:

[] USER:
Tool loaded.
[2026-11-12T01:20:53.102Z] CALL Write: {"file_path": ".../wait-state.sh", "content": "#!/usr/bin/env bash\n# Bounded foreground wait on a Linear issue's state.\n# Usage: wait-state.sh <ISSUE> <TARGET_STATE> <SECONDS>\n# Polls every 15s (each read bounded by timeout), exits when the target state is seen\n# or the seconds elapse. Prints the last observed state.\nissue=\"$1\"\ntarget=\"$2\"\nbudget=\"$3\"\nend=$(( $(date +%s) + budget ))\nstate=\"unread\"\nwhile :; do\n  now=$(date +%s)\n  left=$(( end - now ))\n  [ \"$left\" -le 0 ] && break\n  rt=$(( left < 20 ? left : 20 ))\n  s=$(timeout \"$rt\" linear issue view \"$issue\" --json 2>/dev/null | jq -r '.state.name' 2>/dev/null)\n  [ -n \"$s\" ] && state=\"$s\"\n  if [ \"$state\" = \"$target\" ]; then\n    break\n  fi\n  now=$(date +%s)\n  left=$(( end - now ))\n  [ \"$left\" -le 0 ] && break\n  sleep $(( left < 15 ? left : 15 ))\ndone\nprintf '%s state: %s at %s\\n' \"$issue\" \"$state\" \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"\n"}
[2026-11-12T01:20:53.115Z] RESULT:
File created successfully at: .../wait-state.sh (file state is current in your context - no need to Read it back)
[2026-11-12T01:20:53.645Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time"}
[2026-11-12T01:20:53.782Z] RESULT:
2026-11-12T01:20:53Z
[2026-11-12T01:20:55.948Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh SKL-264 \"In Deployment Review\" 85", "description": "Bounded wait on SKL-264 Linear state (wait 1)", "timeout": 100000}
[2026-11-12T01:22:21.626Z] RESULT:
SKL-264 state: Backlog at 2026-11-12T01:22:21Z
[2026-11-12T01:22:23.719Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh SKL-264 \"In Deployment Review\" 85", "description": "Bounded wait on SKL-264 Linear state (wait 2)", "timeout": 100000}
[2026-11-12T01:23:49.811Z] RESULT:
SKL-264 state: Backlog at 2026-11-12T01:23:49Z
[2026-11-12T01:23:51.841Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh SKL-264 \"In Deployment Review\" 85", "description": "Bounded wait on SKL-264 Linear state (wait 3)", "timeout": 100000}
[2026-11-12T01:25:17.667Z] RESULT:
SKL-264 state: Backlog at 2026-11-12T01:25:17Z
[2026-11-12T01:25:19.555Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh SKL-264 \"In Deployment Review\" 85", "description": "Bounded wait on SKL-264 Linear state (wait 4)", "timeout": 100000}
[2026-11-12T01:26:44.993Z] RESULT:
SKL-264 state: Backlog at 2026-11-12T01:26:44Z
[2026-11-12T01:26:47.037Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh SKL-264 \"In Deployment Review\" 85", "description": "Bounded wait on SKL-264 Linear state (wait 5)", "timeout": 100000}
[2026-11-12T01:28:12.637Z] RESULT:
SKL-264 state: Backlog at 2026-11-12T01:28:12Z
[2026-11-12T01:28:15.317Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh SKL-264 \"In Deployment Review\" 85", "description": "Bounded wait on SKL-264 Linear state (wait 6)", "timeout": 100000}
[2026-11-12T01:29:41.279Z] RESULT:
SKL-264 state: Backlog at 2026-11-12T01:29:41Z
[2026-11-12T01:29:43.451Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh SKL-264 \"In Deployment Review\" 85", "description": "Bounded wait on SKL-264 Linear state (wait 7)", "timeout": 100000}
[2026-11-12T01:31:08.743Z] RESULT:
SKL-264 state: Backlog at 2026-11-12T01:31:08Z
[2026-11-12T01:31:11.905Z] CALL Bash: {"command": "timeout 84 bash .../wait-state.sh SKL-264 \"In Deployment Review\" 80", "description": "Bounded wait on SKL-264 Linear state (wait 8)", "timeout": 95000}
[2026-11-12T01:32:32.381Z] RESULT:
SKL-264 state: Backlog at 2026-11-12T01:32:32Z
[2026-11-12T01:32:34.386Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time"}
[2026-11-12T01:32:34.592Z] RESULT:
2026-11-12T01:32:34Z
[2026-11-12T01:32:36.632Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Confirm the deadline has passed"}
[2026-11-12T01:32:36.997Z] RESULT:
2026-11-12T01:32:36Z
[2026-11-12T01:32:38.314Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Confirm the deadline has passed"}
[2026-11-12T01:32:38.635Z] RESULT:
2026-11-12T01:32:38Z
[2026-11-12T01:32:40.048Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Confirm the deadline has passed"}
[2026-11-12T01:32:40.457Z] RESULT:
2026-11-12T01:32:40Z
[2026-11-12T01:32:41.895Z] CALL Bash: {"command": "linear issue view SKL-264 --json", "description": "Deadline read of SKL-264 state from Linear"}
[2026-11-12T01:32:42.399Z] RESULT:
{
  "identifier": "SKL-264",
  "title": "[Tabletop fixture] SKL-254 interim handback deadline stop (sixth run)",
  "description": "Disposable fixture for SKL-254 AC6, run on the text fixed after the second delta review of record: one story-to-done run (metrics=off) whose senior engineer hands back an interim notice naming a tracker move of this issue that nothing performs, so the awaited item stays pending. This issue is canceled after the run. No work is to be done on it: a senior engineer briefed on this issue does no engineering, triage, branch, PR or tracker write.",
  "url": "https://linear.app/officina-pub/issue/SKL-264/tabletop-fixture-skl-254-interim-handback-deadline-stop-sixth-run",
  "branchName": "noahwhite/skl-264-tabletop-fixture-skl-254-interim-handback",
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
[2026-11-12T01:32:49.630Z] CALL Write: coordinator-todo.md, items: "- [x] interim wait: ... (8 bounded foreground waits, each <=90s, last returned 01:32:32Z; no further handback arrived)" and "- [x] deadline read of SKL-264 state from Linear at 2026-11-12T01:32:40Z: Backlog (target not reached) -> stop and report"
[2026-11-12T01:32:56.989Z] CALL SubagentHandback: (report below)
```

Receipt: the first clock read after the handback, 01:20:38Z; the handback arrived at 01:20:36.675Z.
Recorded deadline: 2026-11-12T01:32:38Z.
Every wait returned before the deadline; the last returned at 01:32:32.381Z.
Seven waits ran under `timeout 90`; the eighth started at 01:31:11.905Z with 86 seconds left under `timeout 84`, 3 seconds longer than the rule's 81 seconds, and returned 6 seconds before the deadline.
No wait was moved to the background.
With 4 seconds left at 01:32:34Z the coordinator started no further wait and read the clock until it gave 01:32:40Z, after the deadline.
Primary-source read: `linear issue view SKL-264 --json` at 01:32:41.895Z, after the deadline, returning Backlog.
Between the handback and the report the coordinator ran no Agent, SendMessage, Monitor or `linear` write command; its only tracker calls were `issue view` reads.

## Coordinator report to the owner (verbatim)

```text
SKL-264 did not reach In Deployment Review by the interim-handback deadline, so the run stopped in step 2 and the story is still in Backlog.

- **Resolved values:** engineer-model Sonnet 5.5 (claude-sonnet-5-5), engineer-effort high, qa-model Opus 5.5 (claude-opus-5-5), qa-effort high. metrics: off.
- **Step 1:** SKL-264 was in Backlog, so the run went to step 2.
- **Step 2:** I spawned the senior engineer on Sonnet 5.5 at high effort with the full step 2 brief, with the tabletop paragraph added word for word at the end. Its checklist had one open item: "wait for the tracker move of SKL-264 to In Deployment Review (in progress)".
- **Handback:** it was an interim handback, so I classified it under interim-handbacks.md first. It did not go through the step 0 checklist read-back, and the read-back resume count is 0.
- **Deadline:** I received the handback at 2026-11-12T01:20:38Z. The handback stated 2 minutes, plus the 10-minute minimum, gives a deadline of 2026-11-12T01:32:38Z.
- **Wait:** I ran 8 bounded foreground waits on Linear, each 90s or less under a timeout; the last returned at 01:32:32Z. At 01:32:34Z only 4s were left, so I started no further wait and let the deadline pass. No further handback arrived.
- **Deadline read:** at 2026-11-12T01:32:40Z Linear showed SKL-264 in Backlog. The awaited item was the tracker move of SKL-264, source Linear, target state In Deployment Review, and it was not reached.

After the stop I launched nothing, made no tracker write and ruled on nothing. There were no PRs and no QA rounds, and steps 3 to 5 were not run. Steps left open are listed in the checklist with the reason.

Files are in .../:
- coordinator-todo.md (my checklist)
- senior-engineer/senior-engineer-todo.md (the engineer's checklist)
- wait-state.sh (the bounded wait helper)
```

## Results

| AC6 requirement | Result |
|---|---|
| Interim handback with the engineer's wake-up not armed | Met: the engineer's whole transcript is two calls, neither a monitor or background task |
| Awaited item held pending deterministically | Met: SKL-264 stayed in Backlog; nothing moved it |
| Primary-source read at the deadline | Met: `linear issue view SKL-264 --json` at 01:32:41.895Z, after the 01:32:38Z deadline, with no wait started in the last 5 seconds |
| Stop with the AC2 report | Met: the report names the awaited item, its primary source, the observed state and the deadline, and launches nothing further |
| No tracker write | Met: no `linear` write in the coordinator or engineer transcripts; SKL-264 read Backlog and unassigned at the deadline read, and the implementing engineer's cancel was the only later write |
| No user message between handback and report | Met |
| `metrics: off` | Met |
