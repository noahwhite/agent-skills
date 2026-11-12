# SKL-254 fixture run evidence (AC6)

Date: 2026-11-12 UTC.
Skill under test: `skills/story-to-done/SKILL.md` and `skills/story-to-done/references/interim-handbacks.md` as committed in `753c843` on `feature/SKL-254-interim-handback-deadline`, read from a worktree by path (the installed skill was not loaded).
Fixture issue: SKL-263 "[Tabletop fixture] SKL-254 interim handback deadline stop (fifth run)", created in Backlog for this run and canceled by the implementing engineer after the coordinator's report.
Awaited item held pending deterministically: the fixture's senior engineer names a move of SKL-263 to In Deployment Review that nothing performs.
The fixture exercises the coordinator's classification, wait, deadline read and stop with a scripted pending item; the engineer runs no real background work, as AC6's "fixture tracker state nothing moves" allows.
It exercises only the deadline branch: no second handback arrives and the target state is never reached.
Runtime: Claude Code 2.1.322.
Coordinator: a general-purpose subagent on Opus 5.5, launched with the parent brief below as its whole prompt.
Senior engineer: Sonnet 5.5 at high, spawned by the coordinator under step 2.
`metrics: off`.
No user message reached the coordinator between the handback and its report: the only non-tool input after its prompt is the engineer's handback at 00:53:46.190Z.

Four earlier runs are replaced by this one.
SKL-259 (on `6ef4b15`) stopped at its deadline, but Claude Code moved its first 570-second wait to the background after 180 seconds.
SKL-260 (on `3bb4db0`) capped each wait at 90 seconds, but sized its last wait past the deadline, so its read came 4.7 seconds late.
SKL-261 (on `40d4234`) sized each wait to the time left, but process start-up put its read 2.5 seconds after the deadline.
SKL-262 (on `53d6f3b`) read at the deadline, but its polling read had no timeout of its own and its receipt time was not defined.
`753c843` defines receipt, bounds every read inside a wait, and starts no wait with 5 seconds or less left.

## Parent brief (verbatim)

```text
story to done SKL-263, metrics=off.

Run the story-to-done skill for SKL-263 by reading and following the file /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/wt/skills/story-to-done/SKILL.md and its references/ directory beside it. That file is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/wt/.agent-skills/profile.yaml.

Your session scratch directory already exists: /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/fixture5/coordinator/. Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-263 is a disposable fixture. When you spawn the senior engineer in step 2, append this paragraph verbatim at the end of its brief, after everything step 2 requires:

"Tabletop fixture: SKL-263 is a disposable fixture. Do no engineering: do not load any skill, triage, create a branch, open a PR, or write to the tracker. Write your checklist file with one open item, 'wait for the tracker move of SKL-263 to In Deployment Review (in progress)', then hand back immediately with exactly this text: 'Interim handback: waiting on my own background work, the tracker move of SKL-263 to In Deployment Review (primary source: Linear, issue SKL-263). Expected duration: 2 minutes. This is not a final handback and I am not blocked.' Arm no wake-up, monitor, or background task."

Never write secrets to files or argv. Run each shell step as one simple command with literal values.
```

The paths are the run's scratch directory and are not needed to replay it: any scratch directory and any fresh fixture issue key work the same way.

## Senior engineer transcript (complete, verbatim)

```text
[2026-11-12T00:53:43.842Z] CALL Write: {"file_path": ".../senior-engineer/senior-engineer-todo.md", "content": "- [ ] wait for the tracker move of SKL-263 to In Deployment Review (in progress)\n"}
[2026-11-12T00:53:43.884Z] RESULT:
File created successfully at: .../senior-engineer/senior-engineer-todo.md (file state is current in your context - no need to Read it back)
[2026-11-12T00:53:45.399Z] CALL SubagentHandback: {"message": "Interim handback: waiting on my own background work, the tracker move of SKL-263 to In Deployment Review (primary source: Linear, issue SKL-263). Expected duration: 2 minutes. This is not a final handback and I am not blocked."}
[2026-11-12T00:53:45.706Z] RESULT:
{"success":true,"message":"Report delivered to your caller."}
```

It armed no wake-up, monitor or background task and made no tracker write.

## Coordinator transcript from the handback to the report (verbatim)

Earlier calls (00:52:58Z to 00:53:44Z) read the skill, its references and the profile, read SKL-263 in Backlog under step 1, wrote the checklist and spawned the engineer.
Each wait runs [`wait-state.sh`](wait-state.sh), written by the coordinator at 00:53:57Z and copied here unchanged, under `timeout`.
It polls `linear issue view SKL-263` every 15 seconds, each read under its own 20-second timeout, up to its argument in seconds, and exits 0 on In Deployment Review or 1 at its limit.

In both transcripts the scratch directory is shortened to `.../`, and the runtime's em dash in its Write result is shown as `-`.
The handback is quoted with the engineer's agent id and the harness framing lines replaced by markers.

```text
[2026-11-12T00:53:46.190Z] USER:
<agent-message from="[senior engineer agent id]">
  [harness hand-back framing omitted]
  Interim handback: waiting on my own background work, the tracker move of SKL-263 to In Deployment Review (primary source: Linear, issue SKL-263). Expected duration: 2 minutes. This is not a final handback and I am not blocked.
</agent-message>
[2026-11-12T00:53:50.083Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ"}
[2026-11-12T00:53:50.233Z] RESULT:
2026-11-12T00:53:50Z
[2026-11-12T00:53:54.697Z] CALL Edit: {"replace_all": false, "file_path": ".../coordinator-todo.md", "old_string": "- [ ] check on senior engineer checklist until it hands back (in progress)\n- [ ] classify senior engineer handback (interim or final)", "new_string": "- [x] check on senior engineer checklist until it hands back\n- [x] classify senior engineer handback: INTERIM (awaits tracker move; not final, not blocked)\n- [ ] interim deadline wait (in progress): awaited item = tracker move of SKL-263; primary source = Linear issue SKL-263; target state = In Deployment Review; receipt 2026-11-12T00:53:50Z; stated 2 min + max(10, 1) min = 12 min; deadline 2026-11-12T01:05:50Z\n- [ ] deadline read of SKL-263 state from Linear"}
[2026-11-12T00:53:54.712Z] RESULT:
The file .../coordinator-todo.md has been updated successfully.
[2026-11-12T00:53:57.784Z] CALL Write: {"file_path": ".../wait-state.sh", "content": "#!/usr/bin/env bash\n# Bounded wait on SKL-263 reaching In Deployment Review. Arg 1: max seconds.\n# Each read is bounded by the outer timeout this script runs under.\nend=$(( $(date +%s) + $1 ))\nwhile [ \"$(date +%s)\" -lt \"$end\" ]; do\n  state=\"$(timeout 20 linear issue view SKL-263 2>&1 | grep -m1 '^\\*\\*State:\\*\\*')\"\n  echo \"$(date -u +%H:%M:%SZ) $state\"\n  case \"$state\" in *\"In Deployment Review\"*) exit 0 ;; esac\n  left=$(( end - $(date +%s) ))\n  [ \"$left\" -le 0 ] && break\n  [ \"$left\" -gt 15 ] && left=15\n  sleep \"$left\"\ndone\nexit 1\n"}
[2026-11-12T00:53:57.827Z] RESULT:
File created successfully at: .../wait-state.sh (file state is current in your context - no need to Read it back)
[2026-11-12T00:54:00.888Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh 70", "timeout": 100000}
[2026-11-12T00:55:10.892Z] RESULT:
Exit code 1
00:54:01Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:54:16Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:54:32Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:54:47Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:55:02Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T00:55:12.589Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh 70", "timeout": 100000}
[2026-11-12T00:56:23.280Z] RESULT:
Exit code 1
00:55:13Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:55:29Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:55:44Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:55:59Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:56:15Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T00:56:24.934Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh 70", "timeout": 100000}
[2026-11-12T00:57:35.476Z] RESULT:
Exit code 1
00:56:25Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:56:41Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:56:56Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:57:12Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:57:27Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T00:57:37.342Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh 70", "timeout": 100000}
[2026-11-12T00:58:48.244Z] RESULT:
Exit code 1
00:57:38Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:57:54Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:58:09Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:58:24Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:58:40Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T00:58:49.917Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh 70", "timeout": 100000}
[2026-11-12T01:00:00.777Z] RESULT:
Exit code 1
00:58:51Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:59:06Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:59:21Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:59:37Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
00:59:52Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T01:00:02.268Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh 70", "timeout": 100000}
[2026-11-12T01:01:13.651Z] RESULT:
Exit code 1
01:00:04Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:00:19Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:00:34Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:00:50Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:01:05Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T01:01:15.315Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh 70", "timeout": 100000}
[2026-11-12T01:02:25.677Z] RESULT:
Exit code 1
01:01:15Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:01:31Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:01:46Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:02:02Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:02:17Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T01:02:27.700Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh 70", "timeout": 100000}
[2026-11-12T01:03:38.967Z] RESULT:
Exit code 1
01:02:29Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:02:45Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:03:01Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:03:16Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:03:31Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T01:03:40.219Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ"}
[2026-11-12T01:03:40.635Z] RESULT:
2026-11-12T01:03:40Z
[2026-11-12T01:03:42.806Z] CALL Bash: {"command": "timeout 90 bash .../wait-state.sh 70", "timeout": 100000}
[2026-11-12T01:04:53.723Z] RESULT:
Exit code 1
01:03:44Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:03:59Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:04:14Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:04:30Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:04:45Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T01:04:54.661Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ"}
[2026-11-12T01:04:55.321Z] RESULT:
2026-11-12T01:04:55Z
[2026-11-12T01:04:57.146Z] CALL Bash: {"command": "timeout 50 bash .../wait-state.sh 35", "timeout": 60000}
[2026-11-12T01:05:33.246Z] RESULT:
Exit code 1
01:04:58Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:05:13Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
01:05:29Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T01:05:34.171Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ"}
[2026-11-12T01:05:34.493Z] RESULT:
2026-11-12T01:05:34Z
[2026-11-12T01:05:36.630Z] CALL Bash: {"command": "timeout 11 bash .../wait-state.sh 5", "timeout": 20000}
[2026-11-12T01:05:42.236Z] RESULT:
Exit code 1
01:05:38Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T01:05:43.128Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ"}
[2026-11-12T01:05:43.957Z] RESULT:
2026-11-12T01:05:43Z
[2026-11-12T01:05:46.227Z] CALL Bash: {"command": "timeout 2 bash .../wait-state.sh 1", "timeout": 10000}
[2026-11-12T01:05:47.837Z] RESULT:
Exit code 1
01:05:46Z **State:** Backlog | **Priority:** --- | **Assignee:** Unassigned
[2026-11-12T01:05:48.998Z] CALL Bash: {"command": "linear issue view SKL-263"}
[2026-11-12T01:05:49.290Z] CALL Bash: {"command": "date -u +%Y-%m-%dT%H:%M:%SZ"}
[2026-11-12T01:05:49.386Z] RESULT:
# SKL-263: [Tabletop fixture] SKL-254 interim handback deadline stop (fifth run)

**State:** Backlog | **Priority:** --- | **Assignee:** Unassigned

Disposable fixture for SKL-254 AC6, run on the text fixed after the delta review of record: one story-to-done run (metrics=off) whose senior engineer hands back an interim notice naming a tracker move of this issue that nothing performs, so the awaited item stays pending. This issue is canceled after the run. No work is to be done on it: a senior engineer briefed on this issue does no engineering, triage, branch, PR or tracker write.
[2026-11-12T01:05:50.281Z] RESULT:
2026-11-12T01:05:50Z
[2026-11-12T01:05:54.036Z] CALL Edit: coordinator-todo.md, new_string: "- [x] interim deadline wait (12 bounded foreground waits, each <=90s, state Backlog throughout; no further handback):"
[2026-11-12T01:05:55.972Z] CALL Edit: coordinator-todo.md, new_string: "- [x] deadline read of SKL-263 state from Linear: Backlog at 2026-11-12T01:05:50Z -> STOP, report to owner\nNOT DONE (run stopped at interim deadline, per interim-handbacks.md): items below"
[2026-11-12T01:06:04.115Z] CALL SubagentHandback: (report below)
```

Receipt: the first clock read after the handback, 00:53:50Z; the handback arrived at 00:53:46.190Z.
Recorded deadline: 2026-11-12T01:05:50Z.
Every wait returned before the deadline; the last returned at 01:05:47.837Z.
Nine waits ran under `timeout 90`; near the deadline the coordinator ran `timeout 50` with 53 seconds left, `timeout 11` with 16 seconds left and `timeout 2` with 7 seconds left.
The `timeout 50` wait was 2 seconds longer than the rule's 48 seconds and returned 17 seconds before the deadline.
No wait was moved to the background.
Primary-source read: `linear issue view SKL-263` at 01:05:48.998Z, after the 5-second floor stopped further waits, returning Backlog; the coordinator's next clock read gave 01:05:50Z.
Between the handback and the report the coordinator ran no Agent, SendMessage or `linear` write command; its only tracker calls were `issue view` reads.

## Coordinator report to the owner (verbatim)

```text
I stopped story-to-done for SKL-263 at the interim-handback deadline: SKL-263 was still in Backlog when the deadline passed.

- engineer-model: claude-sonnet-5-5 (Sonnet 5.5)
- engineer-effort: high
- qa-model: claude-opus-5-5 (Opus 5.5)
- qa-effort: high
- metrics: off

**What happened**
- **Step 1:** SKL-263 was in Backlog. Its team is SKL, the same as the profile's team_key, so the run went to step 2.
- **Step 2:** I spawned the senior engineer on Sonnet 5.5 at high, with the full step 2 brief and the tabletop paragraph appended verbatim.
- **Handback:** it returned the scripted interim notice: it was waiting on the tracker move of SKL-263 to In Deployment Review, expected in 2 minutes, not final and not blocked. I treated it as an interim handback under `references/interim-handbacks.md`, before any checklist read-back or deployment-review check.

**Deadline**
- I received the handback at 2026-11-12T00:53:50Z. The 2-minute estimate plus a 10-minute margin set the deadline at 01:05:50Z.
- Until then I polled Linear in bounded foreground waits of at most 90 seconds each, shortened near the deadline. SKL-263 read Backlog on every check, and no further handback arrived.
- The final read from Linear, at the deadline (01:05:50Z), still showed Backlog.

**Report to the owner**
- **Awaited item:** the move of SKL-263 to In Deployment Review.
- **Where it was checked:** Linear, issue SKL-263.
- **What I saw:** Backlog, not In Deployment Review, with no read errors.
- **Deadline:** 2026-11-12T01:05:50Z.

At the stop I launched nothing further, wrote nothing to the tracker and ruled on nothing. QA (steps 3 to 5) did not run, and there are no PRs, merges or QA rounds. Those items stay open on the checklist because the run stopped at the deadline.

Files are in `/home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/fixture5/coordinator/`:
- coordinator-todo.md
- wait-state.sh (the bounded polling script)
- senior-engineer/senior-engineer-todo.md (the engineer's checklist)
```

## Results

| AC6 requirement | Result |
|---|---|
| Interim handback with the engineer's wake-up not armed | Met: the engineer's whole transcript is two calls, neither a monitor or background task |
| Awaited item held pending deterministically | Met: SKL-263 stayed in Backlog; nothing moved it |
| Primary-source read at the deadline | Met: `linear issue view SKL-263` at 01:05:48.998Z, deadline 01:05:50Z, with no wait started in the last 5 seconds |
| Stop with the AC2 report | Met: the report names the awaited item, its primary source, the observed state and the deadline, and launches nothing further |
| No tracker write | Met: no `linear` write in the coordinator or engineer transcripts; SKL-263 read Backlog and unassigned at the deadline read, and the implementing engineer's cancel was the only later write |
| No user message between handback and report | Met |
| `metrics: off` | Met |
