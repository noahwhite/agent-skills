# SKL-255 fixture run evidence (AC5)

Date: 2026-11-13 UTC.
Skill under test: `skills/story-to-done/SKILL.md` and `skills/story-to-done/references/interim-handbacks.md` as committed in `4703b12` on `feature/SKL-255-interim-deadline-resume`, read from a worktree by path (the installed skill was not loaded).
Fixture issue: SKL-295 "[Tabletop fixture] SKL-255 interim handback deadline resume", created in Backlog for this run and canceled by the implementing engineer after the coordinator's report.
Awaited item already in its target state: CI run 43453419366 in noahwhite/agent-skills, which completed with conclusion `success` at 15:37:44Z, two hours before the handback.
The fixture's senior engineer runs no real background work: it hands back an interim notice naming that run, and when resumed it hands back a scripted final notice.
Runtime: Claude Code 2.1.323.
Coordinator: a general-purpose subagent on Opus 5.5, launched with the parent brief below as its whole prompt.
Senior engineer: Sonnet 5.5 at high, spawned by the coordinator under step 2.
`metrics: off`.
No user message reached the coordinator between the interim handback and the resume: the only non-tool inputs after its prompt are the engineer's interim handback at 17:35:36.274Z and its final handback after the resume.

## Parent brief (verbatim)

```text
Story to done SKL-295, metrics=off.

Run the story-to-done skill for SKL-295 by reading and following the file /home/claude/.claude/jobs/9f857b6d/tmp/session.NEti0E/senior-engineer/wt/skills/story-to-done/SKILL.md and its references/ directory beside it. That file is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is /home/claude/.claude/jobs/9f857b6d/tmp/session.NEti0E/senior-engineer/fixture/profile.yaml.

Your session scratch directory already exists: /home/claude/.claude/jobs/9f857b6d/tmp/session.NEti0E/senior-engineer/fixture/coordinator/. Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-295 is a disposable fixture. When you spawn the senior engineer in step 2, append this paragraph verbatim at the end of its brief, after everything step 2 requires:

"Tabletop fixture: SKL-295 is a disposable fixture. Do no engineering: do not load any skill, triage, create a branch, open a PR, or write to the tracker. Write your checklist file with one open item, 'wait for CI run 43453419366 on noahwhite/agent-skills to complete (in progress)', then hand back immediately with exactly this text: 'Interim handback: waiting on my own background work, CI run 43453419366 on noahwhite/agent-skills (primary source: GitHub Actions, run 43453419366 in noahwhite/agent-skills). Target state: completed. Expected duration: 1 minute. This is not a final handback and I am not blocked.' Arm no wake-up, monitor, or background task. If you are resumed later, mark that checklist item done and hand back with exactly this text: 'Final handback: SKL-295 is a disposable tabletop fixture, so no engineering was done and the story was not moved. Blocked: the fixture has no work to implement.'"

Never write secrets to files or argv. Run each shell step as one simple command with literal values.
```

The profile is a copy of `.agent-skills/profile.yaml` whose two `story_to_done` seats use `runtime: claude-code`.
The paths are the run's scratch directory and are not needed to replay it: any scratch directory, fresh fixture issue key and already-completed CI run work the same way.

## Senior engineer transcript (complete, verbatim)

```text
[2026-11-13T17:35:32.512Z] CALL Bash: {"command": "mkdir -p .../senior-engineer", "description": "Create scratch directory"}
[2026-11-13T17:35:32.823Z] RESULT:
(Bash completed with no output)
[2026-11-13T17:35:34.730Z] CALL Write: {"file_path": ".../senior-engineer/senior-engineer-todo.md", "content": "- [ ] wait for CI run 43453419366 on noahwhite/agent-skills to complete (in progress)\n"}
[2026-11-13T17:35:34.752Z] RESULT:
File created successfully at: .../senior-engineer/senior-engineer-todo.md (file state is current in your context - no need to Read it back)
[2026-11-13T17:35:36.014Z] CALL SubagentHandback: {"message": "Interim handback: waiting on my own background work, CI run 43453419366 on noahwhite/agent-skills (primary source: GitHub Actions, run 43453419366 in noahwhite/agent-skills). Target state: completed. Expected duration: 1 minute. This is not a final handback and I am not blocked."}
[2026-11-13T17:35:36.210Z] RESULT:
{"success":true,"message":"Report delivered to your caller."}
[2026-11-13T17:46:50.876Z] USER:
<agent-message from="[coordinator agent id]">
The CI run you were waiting on has concluded: run 43453419366 on noahwhite/agent-skills, read from GitHub Actions at 2026-11-13T17:46:41Z, status completed, conclusion success. Continue with your work.
</agent-message>
[2026-11-13T17:46:52.068Z] CALL Write: {"file_path": ".../senior-engineer/senior-engineer-todo.md", "content": "- [x] wait for CI run 43453419366 on noahwhite/agent-skills to complete\n"}
[2026-11-13T17:46:52.149Z] RESULT:
The file .../senior-engineer/senior-engineer-todo.md has been updated successfully. (file state is current in your context - no need to Read it back)
[2026-11-13T17:46:53.028Z] CALL SubagentHandback: {"message": "Final handback: SKL-295 is a disposable tabletop fixture, so no engineering was done and the story was not moved. Blocked: the fixture has no work to implement."}
[2026-11-13T17:46:53.446Z] RESULT:
{"success":true,"message":"Report delivered to your caller."}
```

It armed no wake-up, monitor or background task and made no tracker write.
Between the two handbacks its only input is the coordinator's resume message.

## Coordinator transcript from the handback to the report (verbatim)

Earlier calls (17:34:46Z to 17:35:33Z) read the skill, its references and the profile, read SKL-295 in Backlog under step 1, wrote the checklist and spawned the engineer.

In both transcripts the scratch directory is shortened to `.../`, and the runtime's em dash in its Write result is shown as `-`.
Agent ids and the harness framing lines are replaced by markers, and the read-back's `url` and `branchName` values, which name the tracker workspace, are replaced by markers.
The runtime logged some calls twice without a timestamp; only the timestamped entry is kept.

```text
[2026-11-13T17:35:36.274Z] USER:
<agent-message from="[senior engineer agent id]">
  [harness hand-back framing omitted]
  Interim handback: waiting on my own background work, CI run 43453419366 on noahwhite/agent-skills (primary source: GitHub Actions, run 43453419366 in noahwhite/agent-skills). Target state: completed. Expected duration: 1 minute. This is not a final handback and I am not blocked.
</agent-message>
[2026-11-13T17:35:37.833Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time for receipt"}
[2026-11-13T17:35:38.150Z] RESULT:
2026-11-13T17:35:38Z
[2026-11-13T17:35:45.967Z] CALL Edit: {"replace_all": false, "file_path": ".../coordinator-todo.md", "old_string": "- [ ] Wait for engineer handback (in progress)\n- [ ] Classify engineer handback (interim vs final)", "new_string": "- [x] Wait for engineer handback (received 2026-11-13T17:35:38Z)\n- [x] Classify engineer handback: INTERIM (awaited item named, not final, not blocked)\n- [ ] Interim deadline wait (in progress)\n  - awaited item: CI run 43453419366 on noahwhite/agent-skills\n  - primary source: GitHub Actions, run 43453419366 in noahwhite/agent-skills\n  - target state: completed\n  - stated duration 1 min -> deadline = 1 + max(10, 0.5) = 11 min after receipt 17:35:38Z = 2026-11-13T17:46:38Z\n- [ ] Bounded waits on the run until deadline (each <= 90s)\n- [ ] Deadline read of the run from GitHub Actions\n- [ ] Deadline resume of engineer if concluded (not counted against read-back cap)"}
[2026-11-13T17:35:45.983Z] RESULT:
The file .../coordinator-todo.md has been updated successfully.
[2026-11-13T17:35:46.680Z] CALL Bash: {"command": "timeout 85 gh run view 43453419366 --repo noahwhite/agent-skills --json status,conclusion,createdAt,updatedAt", "description": "Read CI run status from GitHub Actions"}
[2026-11-13T17:35:47.183Z] RESULT:
{"conclusion":"success","createdAt":"2026-11-13T15:31:15Z","status":"completed","updatedAt":"2026-11-13T15:37:44Z"}
[2026-11-13T17:35:49.588Z] CALL ToolSearch: {"query": "select:Monitor", "max_results": 1}
[2026-11-13T17:35:49.594Z] RESULT:

[] USER:
Tool loaded.
[2026-11-13T17:35:54.075Z] CALL Bash: {"command": "timeout 85 gh run watch 43453419366 --repo noahwhite/agent-skills --interval 30", "description": "Watch CI run under an 85-second bound"}
[2026-11-13T17:35:54.677Z] RESULT:
Run ci (43453419366) has already completed with 'success'
[2026-11-13T17:35:55.990Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time"}
[2026-11-13T17:35:56.220Z] RESULT:
2026-11-13T17:35:56Z
[2026-11-13T17:35:57.413Z] CALL Bash: {"command": "timeout 90 tail -f /dev/null", "description": "Bounded 90-second wait toward the interim deadline", "timeout": 100000}
[2026-11-13T17:37:27.519Z] RESULT:
Exit code 124
[2026-11-13T17:37:29.622Z] CALL Bash: {"command": "timeout 85 gh run view 43453419366 --repo noahwhite/agent-skills --json status,conclusion", "description": "Read CI run status"}
[2026-11-13T17:37:30.178Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time"}
[2026-11-13T17:37:30.183Z] RESULT:
{"conclusion":"success","status":"completed"}
[2026-11-13T17:37:30.684Z] RESULT:
2026-11-13T17:37:30Z
[2026-11-13T17:37:31.956Z] CALL Bash: {"command": "timeout 90 tail -f /dev/null", "description": "Bounded 90-second wait toward the interim deadline", "timeout": 100000}
[2026-11-13T17:37:32.583Z] CALL Bash: {"command": "timeout 90 tail -f /dev/null", "description": "Bounded 90-second wait toward the interim deadline", "timeout": 100000}
[2026-11-13T17:39:02.939Z] RESULT:
Exit code 124
[2026-11-13T17:39:02.945Z] RESULT:
Exit code 124
[2026-11-13T17:39:04.425Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time"}
[2026-11-13T17:39:04.761Z] RESULT:
2026-11-13T17:39:04Z
[2026-11-13T17:39:06.442Z] CALL Bash: {"command": "timeout 90 tail -f /dev/null", "description": "Bounded 90-second wait toward the interim deadline", "timeout": 100000}
[2026-11-13T17:40:36.575Z] RESULT:
Exit code 124
[2026-11-13T17:40:38.007Z] CALL Bash: {"command": "timeout 90 tail -f /dev/null", "description": "Bounded 90-second wait toward the interim deadline", "timeout": 100000}
[2026-11-13T17:42:08.097Z] RESULT:
Exit code 124
[2026-11-13T17:42:09.665Z] CALL Bash: {"command": "timeout 90 tail -f /dev/null", "description": "Bounded 90-second wait toward the interim deadline", "timeout": 100000}
[2026-11-13T17:43:39.778Z] RESULT:
Exit code 124
[2026-11-13T17:43:41.093Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time"}
[2026-11-13T17:43:41.484Z] RESULT:
2026-11-13T17:43:41Z
[2026-11-13T17:43:43.452Z] CALL Bash: {"command": "timeout 90 tail -f /dev/null", "description": "Bounded 90-second wait toward the interim deadline", "timeout": 100000}
[2026-11-13T17:45:13.623Z] RESULT:
Exit code 124
[2026-11-13T17:45:15.001Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time"}
[2026-11-13T17:45:15.296Z] RESULT:
2026-11-13T17:45:15Z
[2026-11-13T17:45:16.916Z] CALL Bash: {"command": "timeout 78 tail -f /dev/null", "description": "Bounded final wait up to the interim deadline", "timeout": 90000}
[2026-11-13T17:46:35.142Z] RESULT:
Exit code 124
[2026-11-13T17:46:36.455Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Read current UTC time"}
[2026-11-13T17:46:36.748Z] RESULT:
2026-11-13T17:46:36Z
[2026-11-13T17:46:38.629Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Confirm the deadline has passed"}
[2026-11-13T17:46:38.862Z] RESULT:
2026-11-13T17:46:38Z
[2026-11-13T17:46:41.398Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ", "description": "Confirm the deadline has passed"}
[2026-11-13T17:46:41.694Z] RESULT:
2026-11-13T17:46:41Z
[2026-11-13T17:46:43.014Z] CALL Bash: {"command": "timeout 60 gh run view 43453419366 --repo noahwhite/agent-skills --json status,conclusion,updatedAt", "description": "Deadline read of the CI run from GitHub Actions"}
[2026-11-13T17:46:43.522Z] RESULT:
{"conclusion":"success","status":"completed","updatedAt":"2026-11-13T15:37:44Z"}
[2026-11-13T17:46:45.541Z] CALL Edit: {"replace_all": false, "file_path": ".../coordinator-todo.md", "old_string": "- [ ] Interim deadline wait (in progress)", "new_string": "- [x] Interim deadline wait"}
[2026-11-13T17:46:45.557Z] RESULT:
The file .../coordinator-todo.md has been updated successfully.
[2026-11-13T17:46:48.284Z] CALL Edit: {"replace_all": false, "file_path": ".../coordinator-todo.md", "old_string": "- [ ] Bounded waits on the run until deadline (each <= 90s)\n- [ ] Deadline read of the run from GitHub Actions\n- [ ] Deadline resume of engineer if concluded (not counted against read-back cap)", "new_string": "- [x] Bounded waits on the run until deadline (each <= 90s; no engineer handback arrived before deadline)\n- [x] Deadline read of the run from GitHub Actions at 17:46:41Z: completed / success\n- [ ] Deadline resume of engineer with observed conclusion (not counted against read-back cap) (in progress)\n- [ ] Handle engineer's next handback"}
[2026-11-13T17:46:48.300Z] RESULT:
The file .../coordinator-todo.md has been updated successfully.
[2026-11-13T17:46:48.637Z] CALL ToolSearch: {"query": "select:SendMessage", "max_results": 1}
[2026-11-13T17:46:48.643Z] RESULT:

[] USER:
Tool loaded.
[2026-11-13T17:46:50.780Z] CALL SendMessage: {"to": "[senior engineer agent id]", "summary": "Deadline resume with CI conclusion", "message": "The CI run you were waiting on has concluded: run 43453419366 on noahwhite/agent-skills, read from GitHub Actions at 2026-11-13T17:46:41Z, status completed, conclusion success. Continue with your work."}
[2026-11-13T17:46:50.882Z] RESULT:
{"success":true,"message":"Resuming agent [senior engineer agent id]"}
[2026-11-13T17:46:53.490Z] CALL Edit: {"replace_all": false, "file_path": ".../coordinator-todo.md", "old_string": "- [ ] Deadline resume of engineer with observed conclusion (not counted against read-back cap) (in progress)\n- [ ] Handle engineer's next handback", "new_string": "- [x] Deadline resume of engineer with observed conclusion (sent 17:46Z; not counted against read-back cap)\n- [ ] Handle engineer's next handback (in progress)"}
[2026-11-13T17:46:53.538Z] RESULT:
The file .../coordinator-todo.md has been updated successfully.
[] USER:
<agent-message from="[senior engineer agent id]">
  [harness hand-back framing omitted]
  Final handback: SKL-295 is a disposable tabletop fixture, so no engineering was done and the story was not moved. Blocked: the fixture has no work to implement.
</agent-message>
[2026-11-13T17:46:55.461Z] CALL Read: {"file_path": ".../senior-engineer/senior-engineer-todo.md"}
[2026-11-13T17:46:55.470Z] RESULT:
1	- [x] wait for CI run 43453419366 on noahwhite/agent-skills to complete
[2026-11-13T17:46:55.959Z] CALL Bash: {"command": "linear issue view SKL-295 --json", "description": "Read back SKL-295 state"}
[2026-11-13T17:46:56.380Z] RESULT:
{"identifier": "SKL-295", "title": "[Tabletop fixture] SKL-255 interim handback deadline resume", "url": "[Linear URL redacted]", "branchName": "[branch name redacted]", "state": {"name": "Backlog"}, "assignee": null, ... (description and empty relation lists omitted)}
[2026-11-13T17:47:00.622Z] CALL Edit: {"replace_all": false, "file_path": ".../coordinator-todo.md", "old_string": "- [ ] Handle engineer's next handback (in progress)\n- [ ] Checklist read-back at handback (read-back resumes: 0/2)\n- [ ] Read back deployment-review state\n\n## Step 3\n- [ ] QA round 1 (if story reaches In Deployment Review)\n- [ ] Read back QA state\n\n## Step 4 / 5\n- [ ] Act on QA outcome\n- [ ] Final state read-back", "new_string": "- [x] Handle engineer's next handback: FINAL, blocked (fixture has no work)\n- [x] Checklist read-back at handback: all items done (read-back resumes: 0/2)\n- [x] Read back state: Backlog, not In Deployment Review -> step 2 stop\n\n## Step 3\n- [ ] QA round 1 - not run: loop stopped at step 2 (engineer blocked)\n- [ ] Read back QA state - not run, same reason\n\n## Step 4 / 5\n- [ ] Act on QA outcome - not run, same reason\n- [x] Final state read-back: Backlog"}
[2026-11-13T17:47:00.636Z] RESULT:
The file .../coordinator-todo.md has been updated successfully.
[2026-11-13T17:47:07.868Z] CALL SubagentHandback: (report below)
```

Receipt: the first clock read after the handback, 17:35:38Z; the handback arrived at 17:35:36.274Z.
Recorded deadline: 2026-11-13T17:46:38Z (stated 1 minute plus the 10-minute minimum).
Every wait returned before the deadline; the last returned at 17:46:35.142Z.
The waits were `timeout` sleeps, not waits on the run: `gh run watch` returned at once because the run had already completed, so it could not hold until the deadline.
At 17:37:31Z the coordinator started two 90-second waits in parallel; both returned at 17:39:02Z.
No wait was moved to the background.
With 2 seconds left at 17:46:36Z the coordinator started no further wait and read the clock until it gave 17:46:41Z, after the deadline.
Primary-source read: `gh run view 43453419366` at 17:46:43.014Z, after the deadline, returning `completed` / `success`.
Resume: `SendMessage` to the same engineer at 17:46:50.780Z, 12.8 seconds after the deadline, carrying the run, the read time, the status and the conclusion.
The engineer's next handback was handled as usual: the step 0 checklist read-back found every item done, so no read-back resume was used (0 of 2).
Between the interim handback and the report the coordinator ran no Agent call and no `linear` write command; its only tracker calls were `issue view` reads.

## Coordinator report to the owner (verbatim)

```text
I stopped SKL-295 at step 2: the senior engineer handed back blocked and the story is still in Backlog, not In Deployment Review. No QA round ran.

- engineer-model: claude-sonnet-5-5, engineer-effort: high (from the profile's engineer seat, runtime claude-code)
- qa-model: claude-opus-5-5, qa-effort: high (from the profile's QA seat, runtime claude-code)
- metrics: off
- qa-round-cap: 3

How the run went:
- **Step 1:** SKL-295 was in Backlog, so the run went to step 2.
- **Step 2, first handback:** I spawned the senior engineer on sonnet at high effort. It handed back an interim notice waiting on CI run 43453419366 in noahwhite/agent-skills, expected duration 1 minute.
- **Interim deadline:** I received the handback at 2026-11-13T17:35:38Z and set the deadline to 17:46:38Z (1 minute plus 10 minutes). I waited in the foreground in steps of 90 seconds or less and made no other wait after 17:46:36Z, when 2 seconds were left. The engineer sent nothing before the deadline.
- **Deadline read:** at 17:46:41Z, after the deadline, GitHub Actions showed the run completed with conclusion success. The run had already finished at 15:37:44Z, before the handback.
- **Deadline resume:** I resumed the same engineer with that result. This resume does not count against the read-back cap.
- **Final handback:** the engineer said the story is a disposable tabletop fixture, so it did no engineering and did not move the story, and reported itself blocked.
- **Read-back:** its checklist has every item done, so no read-back resume was needed (0 of 2 used). SKL-295 reads back as Backlog.

No PRs, no QA evidence and no incidental defects. I made no tracker writes.

One deviation from the brief's shell rule: I used `timeout 90 tail -f /dev/null` for the bounded waits. The skill asks for a bounded wait on the run itself, but `gh run watch` returns at once on a run that has already finished, so it cannot hold until the deadline.

Files are in .../:
- coordinator-todo.md
- senior-engineer/senior-engineer-todo.md
```

## Results

| AC5 requirement | Result |
|---|---|
| Disposable `[Tabletop fixture]` issue in SKL, canceled after its run | Met: SKL-295, canceled at 17:49:53Z, after the coordinator's report at 17:47:07Z; its state history has one transition, Backlog to Canceled |
| Interim handback while the awaited item is already in its target state | Met: run 43453419366 read `completed` at 17:35:47Z, before any wait, and had completed at 15:37:44Z |
| Engineer's own wake-up not armed | Met: the engineer's transcript before the resume is three calls, none a monitor or background task |
| Primary-source read at the deadline | Met: `gh run view 43453419366` at 17:46:43.014Z, after the 17:46:38Z deadline |
| Resume of the same engineer with the observed conclusion | Met: `SendMessage` to the engineer's agent id at 17:46:50.780Z with `completed` / `success`; no new subagent was spawned |
| Resume recorded on the todo list | Met: the 17:46:53Z edit marks the deadline resume done, not counted against the read-back cap |
| No user message between the interim handback and the resume | Met |
| Runtime named, `metrics: off` | Met: Claude Code 2.1.323, `metrics: off` |
