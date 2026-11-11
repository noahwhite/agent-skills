# SKL-254 fixture run evidence (AC6)

Date: 2026-11-11 UTC.
Skill under test: `skills/story-to-done/SKILL.md` and `skills/story-to-done/references/interim-handbacks.md` at commit `a7925c6` on `feature/SKL-254-interim-handback-deadline`, read from a worktree by path (the installed skill was not loaded).
Fixture issue: SKL-259 "[Tabletop fixture] SKL-254 interim handback deadline stop", created in Backlog for this run and canceled after it.
Awaited item held pending deterministically: the fixture's senior engineer names a move of SKL-259 to In Deployment Review that nothing performs.
Runtime: Claude Code 2.1.322.
Coordinator: a general-purpose subagent on Opus 5.5 (medium effort), launched with the parent brief below as its whole prompt.
Senior engineer: Sonnet 5.5 at high, spawned by the coordinator under step 2.
`metrics: off`.
No user message reached the coordinator at any point of the run: its only input was the parent brief, and its transcript holds only its own tool calls and their results.

## Parent brief (verbatim)

```text
story to done SKL-259, metrics=off.

Run the story-to-done skill for SKL-259 by reading and following the file /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/wt/skills/story-to-done/SKILL.md and its references/ directory beside it. That file is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/wt/.agent-skills/profile.yaml.

Your session scratch directory already exists: /home/claude/.claude/jobs/7e3bb4a9/tmp/session.1aOqq8/senior-engineer/fixture/coordinator/. Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-259 is a disposable fixture. When you spawn the senior engineer in step 2, append this paragraph verbatim at the end of its brief, after everything step 2 requires:

"Tabletop fixture: SKL-259 is a disposable fixture. Do no engineering: do not load any skill, triage, create a branch, open a PR, or write to the tracker. Write your checklist file with one open item, 'wait for the tracker move of SKL-259 to In Deployment Review (in progress)', then hand back immediately with exactly this text: 'Interim handback: waiting on my own background work, the tracker move of SKL-259 to In Deployment Review (primary source: Linear, issue SKL-259). Expected duration: 2 minutes. This is not a final handback and I am not blocked.' Arm no wake-up, monitor, or background task."

Never write secrets to files or argv. Run each shell step as one simple command with literal values.
```

## Senior engineer transcript (complete)

```text
[15:09:11.411Z] Bash: mkdir -p .../fixture/coordinator/senior-engineer/
[15:09:13.365Z] Write: .../senior-engineer/senior-engineer-todo.md  ("- [ ] wait for the tracker move of SKL-259 to In Deployment Review (in progress)")
[15:09:14.957Z] SubagentHandback: Interim handback: waiting on my own background work, the tracker move of SKL-259 to In Deployment Review (primary source: Linear, issue SKL-259). Expected duration: 2 minutes. This is not a final handback and I am not blocked.
```

It armed no wake-up, monitor or background task and made no tracker write.

## Coordinator tool-call transcript (from the spawn of the engineer to the report)

Reads of the skill, its references and the profile before 15:09 are omitted; checklist edits are summarized by their resulting line.

```text
[15:08:47.737Z] Bash: linear issue view SKL-259                 -> State: Backlog (step 1: go to step 2)
[15:09:09.462Z] Agent: Senior engineer SKL-259 (model sonnet)
[15:09:20.810Z] Bash: date -u +%Y-%m-%dT%H:%M:%SZ               -> 2026-11-11T15:09:20Z (receipt of the handback)
[15:09:28.161Z] Edit coordinator-todo.md: "Step 2: classify handback (interim handbacks rule): INTERIM, not final, not blocked"
                 "Interim wait: awaited item = tracker move of SKL-259; primary source = Linear issue SKL-259; target state = In Deployment Review; stated duration 2 min -> deadline 2026-11-11T15:21:20Z (2 + max(10, 1) = 12 min from receipt)"
[15:09:29.303Z] Bash: cat .../senior-engineer/senior-engineer-todo.md
[15:09:31.297Z] Bash: timeout 570 bash -c 'until linear issue view SKL-259 | grep -q "State:\*\* In Deployment Review"; do sleep 30; done; date -u +%H:%M:%SZ'
[15:12:31.911Z]   -> Claude Code moved the command to the background after 180s; its 570s timeout still bounded it
[15:19:03.771Z] Bash: date -u +%Y-%m-%dT%H:%M:%SZ               -> 2026-11-11T15:19:04Z (wait 1 timed out, state not reached)
[15:19:09.292Z] Bash: timeout 130 bash -c 'until linear issue view SKL-259 | grep -q "State:\*\* In Deployment Review"; do sleep 20; done; date -u +%H:%M:%SZ'
[15:21:19.429Z]   -> Exit code 124 (wait 2 timed out, state not reached)
[15:21:20.574Z] Bash: date -u +%Y-%m-%dT%H:%M:%SZ               -> 2026-11-11T15:21:21Z
[15:21:22.567Z] Bash: linear issue view SKL-259                 -> State: Backlog (primary-source read at the deadline)
[15:21:25.911Z] Edit coordinator-todo.md: "Interim wait: read SKL-259 state from Linear at deadline: Backlog (target In Deployment Review not reached) -> stop"
[15:21:31.416Z] Edit coordinator-todo.md: steps 2 read-backs, 3, 4 and 5 marked "NOT DONE: run stopped at interim deadline"
[15:21:39.522Z] SubagentHandback (report below)
```

Recorded deadline: 2026-11-11T15:21:20Z.
Primary-source read: the `linear issue view SKL-259` call at 2026-11-11T15:21:22.567Z, returning Backlog.
Between 15:09:20Z and the report the coordinator ran no Agent, SendMessage or `linear` write command; its only tracker calls were the two `issue view` reads and the polling `issue view` inside the two bounded waits.

## Coordinator report to the owner (verbatim)

```text
SKL-259 story-to-done stopped at the interim-handback deadline: the awaited tracker move did not happen by the deadline. SKL-259 is still in Backlog.

- engineer-model: claude-sonnet-5-5, engineer-effort: high, qa-model: claude-opus-5-5, qa-effort: high
- metrics: off
- Step 1: SKL-259 was in Backlog, so the run went to step 2.
- Step 2: the senior engineer (Sonnet 5.5, high) was spawned with the full step 2 brief and the tabletop paragraph appended word for word at the end.
  - It handed back at 2026-11-11T15:09:20Z. I classified it as an interim handback under references/interim-handbacks.md, before any checklist read-back or deployment-review check.
- What it was waiting on:
  - Awaited item: the tracker move of SKL-259 to In Deployment Review.
  - Where I checked it: the Linear issue SKL-259.
  - Deadline: 2026-11-11T15:21:20Z. That is the stated 2 minutes plus max(10 min, 50% of 2 min), so 12 minutes after the handback.
- How I waited: two bounded waits polling SKL-259 in Linear, up to the deadline. Both timed out (15:19:04Z and 15:21:21Z) without the state being reached.
  - The first wait was meant to run in the foreground but the harness moved it to the background after 180s; its own 570s timeout still bounded it.
- At the deadline (15:21:21Z) I read SKL-259 from Linear: state **Backlog**, not In Deployment Review.
- After the stop:
  - I launched nothing further: no read-back resume, no QA agent.
  - I made no tracker write and ruled on nothing.
  - Steps 2 (read-backs), 3, 4 and 5 are recorded as not done on the checklist.
- The senior engineer's checklist was mirrored; it has one open item: "wait for the tracker move of SKL-259 to In Deployment Review (in progress)".
- No PRs, no QA rounds, no incidental defects.
```

## Observation

Claude Code 2.1.322 moves a foreground Bash command to the background after 180 seconds.
The coordinator's first bounded wait was moved this way; the coordinator idled until that command exited at its own timeout, then ran the second wait to the deadline.
The bounded timeout, not the subagent, ended each wait, so the stop did not depend on the engineer's wake-up.
A wake primitive for the deadline is SKL-258's scope.

## Results

| AC6 requirement | Result |
|---|---|
| Interim handback with the engineer's wake-up not armed | Met: the engineer's whole transcript is three calls, none a monitor or background task |
| Awaited item held pending deterministically | Met: SKL-259 stayed in Backlog; nothing moved it |
| Primary-source read at the deadline | Met: `linear issue view SKL-259` at 15:21:22.567Z, deadline 15:21:20Z |
| Stop with the AC2 report | Met: the report names the awaited item, its primary source, the observed state and the deadline, and launches nothing further |
| No tracker write | Met: no `linear` write in the coordinator or engineer transcripts; SKL-259 was still Backlog and unassigned after the run |
| No user message between handback and report | Met |
| `metrics: off` | Met |
