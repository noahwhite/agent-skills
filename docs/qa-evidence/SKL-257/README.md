# SKL-257 AC5 fixture run: QA interim handback deadline resume

- Date: 2026-11-16
- Skill under test: `skills/story-to-done/` at commit ec67ab537e0cce28f4aa82132110b59977a08148 (branch `feature/SKL-257-qa-interim-handbacks`), read by path from the worktree; the commit that adds this file changes only this file
- Fixture issue: SKL-314, `[Tabletop fixture] SKL-257 QA interim handback deadline resume`, in In Deployment Review for the run so the coordinator starts at step 3, and Canceled after the run (tracker read below)
- Awaited item: CI run 43769704269 on noahwhite/agent-skills, already `completed`/`success` (updated 2026-11-15T22:37:01Z) before the run started
- Runtime: Claude Code 2.1.325
- Coordinator: a general-purpose Opus 5.5 subagent launched with the parent brief below
- QA seat: fixture profile copy with `story_to_done.qa` on `runtime: claude-code`, `claude-sonnet-5-5`, effort high
- `metrics: off`

An earlier run of the same fixture at commit 45d8f69 is superseded by this run on the final skill text.

## Parent brief (verbatim)

```text
Story to done SKL-314, metrics=off.

Run the story-to-done skill for SKL-314 by reading and following the file /home/claude/.claude/jobs/02213c5c/tmp/session.eG5tKG/senior-engineer/wt/skills/story-to-done/SKILL.md and its references/ directory beside it. That file is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is /home/claude/.claude/jobs/02213c5c/tmp/session.eG5tKG/senior-engineer/fixture/profile.yaml.

Your session scratch directory already exists: /home/claude/.claude/jobs/02213c5c/tmp/session.eG5tKG/senior-engineer/fixture/coordinator-2/. Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-314 is a disposable fixture. When you spawn the QA agent in step 3, append this paragraph verbatim at the end of its brief, after everything step 3 requires:

"Tabletop fixture: SKL-314 is a disposable fixture. Do no verification: do not load any skill, create a branch, open a PR, or write to the tracker. Write your checklist file with one open item, 'wait for CI run 43769704269 on noahwhite/agent-skills to complete (in progress)', then hand back immediately with exactly this text: 'Interim handback: waiting on my own background work, CI run 43769704269 on noahwhite/agent-skills (primary source: GitHub Actions, run 43769704269 in noahwhite/agent-skills). Target state: completed. Expected duration: 1 minute. This is not a final handback and I am not blocked.' Arm no wake-up, monitor, or background task. If you are resumed later, mark that checklist item done and hand back with exactly this text: 'Final handback: SKL-314 is a disposable tabletop fixture, so no verification was done and the story was not moved. Outstanding: the fixture issue SKL-314 must be canceled; owner: the story owner.'"

Never write secrets to files or argv. Run each shell step as one simple command with literal values.
```

The QA agent's own wake-up was not armed: its transcript holds two tool calls before the interim handback (the checklist write and the handback) and none after it until the resume arrived.

## Resume message (verbatim)

Sent by the coordinator with `SendMessage` to the same QA agent at 2026-11-16T01:40:49.352Z:

```text
QA round 1 is unfinished. Round scratch subdirectory: /home/claude/.claude/jobs/02213c5c/tmp/session.eG5tKG/senior-engineer/fixture/coordinator-2/qa-agent-round-1/ . Awaited item: CI run 43769704269 on noahwhite/agent-skills.
```

It states only that the round is unfinished, the round's scratch subdirectory and the awaited item.
It carries no conclusion (the coordinator had read `completed`/`success`), no verdict, no earlier round's conclusions and no senior engineer handback.

## QA agent transcript (UTC)

```text
01:29:23.751 user: QA brief for SKL-314 (step 3 brief plus the tabletop paragraph above)
01:29:25.561 Write qa-agent-round-1-todo.md: "- [ ] wait for CI run 43769704269 on noahwhite/agent-skills to complete (in progress)"
01:29:27.107 SubagentHandback: "Interim handback: waiting on my own background work, CI run 43769704269 on noahwhite/agent-skills (primary source: GitHub Actions, run 43769704269 in noahwhite/agent-skills). Target state: completed. Expected duration: 1 minute. This is not a final handback and I am not blocked."
01:40:49.512 message from the coordinator: the resume message above
01:40:51.937 Write qa-agent-round-1-todo.md: "- [x] wait for CI run 43769704269 on noahwhite/agent-skills to complete"
01:40:53.218 SubagentHandback: "Final handback: SKL-314 is a disposable tabletop fixture, so no verification was done and the story was not moved. Outstanding: the fixture issue SKL-314 must be canceled; owner: the story owner."
```

## Coordinator tool-call transcript from the QA spawn (UTC)

Bootstrap (reading the skill, its references and the profile, `select-path.py` printing `no-deployment`, the story read showing In Deployment Review) ran from 01:28:31 to 01:29:23 and is omitted.
The only incoming message between the interim handback at 01:29:27.892 and the resume at 01:40:49.352 is that handback itself; no user message arrived in that window.

```text
01:29:23.632 Agent (general-purpose, model sonnet, effort high): "QA round 1 for SKL-314"
01:29:27.095 Edit coordinator-todo.md: spawn ticked; "wait for QA round 1 handback (in progress)"
01:29:27.892 [incoming] QA agent handback: the interim handback text
01:29:30.604 Bash date -u -> 2026-11-16T01:29:30Z   (receipt)
01:29:34.620 Edit coordinator-todo.md:
             "- [x] Step 3: wait for QA round 1 handback (interim handback received 2026-11-16T01:29:30Z)
              - [ ] QA round 1 interim deadline: awaited item CI run 43769704269 on noahwhite/agent-skills; primary source GitHub Actions run 43769704269; target state completed; stated duration 1 min; deadline 2026-11-16T01:40:30Z (1 + 10 min); misses: 0 (in progress)"
01:29:35.373 Bash gh run view 43769704269 --repo noahwhite/agent-skills --json status,conclusion,headBranch,event,updatedAt
             -> {"conclusion":"success","event":"push","headBranch":"main","status":"completed","updatedAt":"2026-11-15T22:37:01Z"}
01:29:49.486 Write bounded-wait.sh (polls the run under a per-read timeout until the given seconds elapse)
01:29:51.433 Bash timeout 90 bounded-wait.sh 85 -> 01:31:17 status=completed conclusion=success
01:31:19.360 Bash timeout 90 bounded-wait.sh 85 -> 01:32:44 status=completed conclusion=success
01:32:46.637 Bash timeout 90 bounded-wait.sh 85 -> 01:34:11 status=completed conclusion=success
01:34:13.427 Bash timeout 90 bounded-wait.sh 85 -> 01:35:38 status=completed conclusion=success
01:35:39.886 Bash timeout 90 bounded-wait.sh 85 -> 01:37:05 status=completed conclusion=success
01:37:07.714 Bash timeout 90 bounded-wait.sh 85 -> 01:38:32 status=completed conclusion=success
01:38:34.912 Bash timeout 90 bounded-wait.sh 85 -> 01:40:00 status=completed conclusion=success
01:40:13.395 Bash timeout 28 bounded-wait.sh 24 -> 01:40:37 status=completed conclusion=success
01:40:40.856 Bash gh run view 43769704269 --repo noahwhite/agent-skills --json status,conclusion,updatedAt   (deadline read)
             -> {"conclusion":"success","status":"completed","updatedAt":"2026-11-15T22:37:01Z"}
01:40:47.611 Edit coordinator-todo.md:
             "misses: 0 (8 bounded foreground waits, 01:29:30Z-01:40:37Z)
              - [x] QA round 1 deadline read of the CI run state (01:40:37Z: completed, success -> concluded)
              - [ ] QA round 1 deadline resume of the same QA agent (in progress)"
01:40:49.352 SendMessage to the round 1 QA agent: the resume message above
01:40:54.731 [incoming] QA agent final handback
01:41:04.428 Read qa-agent-round-1-todo.md -> "- [x] wait for CI run 43769704269 on noahwhite/agent-skills to complete"
01:41:05.038 Bash linear issue view SKL-314 --json -> state In Deployment Review
01:41:11.257 Edit coordinator-todo.md: resume ticked; checklist read-back (read-back resumes: 0); step 4 owner-action stop
01:41:17.781 SubagentHandback: closing report
```

The eighth wait started at 01:40:13 with 17 seconds left and ran 24 seconds, returning at 01:40:37, 7 seconds after the 01:40:30 deadline rather than at or before it.
The deadline read and the resume both came after the deadline.

## Coordinator checklist at the end of the run (QA section)

```text
- [x] Step 3: QA round 1 - spawn QA agent (launched, sonnet/high)
- [x] Step 3: wait for QA round 1 handback (interim handback received 2026-11-16T01:29:30Z)
- [ ] QA round 1 interim deadline: awaited item CI run 43769704269 on noahwhite/agent-skills; primary source GitHub Actions run 43769704269; target state completed; stated duration 1 min; deadline 2026-11-16T01:40:30Z (1 + 10 min); misses: 0 (8 bounded foreground waits, 01:29:30Z-01:40:37Z)
- [x] QA round 1 deadline read of the CI run state (01:40:37Z: completed, success -> concluded)
- [x] QA round 1 deadline resume of the same QA agent (final handback received)
- [x] Step 3: QA round 1 checklist read-back (all items done; read-back resumes: 0)
- [x] Step 3: read back QA's state (In Deployment Review; no PRs merged)
- [x] Step 4: in deployment review with an owner-owned outstanding item (cancel fixture SKL-314, owner: story owner) -> report and stop
- [x] Step 5: not reached (stopped at step 4); final state read back: In Deployment Review
```

## Coordinator closing report (excerpt)

```text
- **QA round 1 interim handback:** it was received at 2026-11-16T01:29:30Z, for CI run 43769704269 on noahwhite/agent-skills. Its stated duration was 1 minute, so the deadline was 2026-11-16T01:40:30Z.
  - I made 8 bounded foreground waits of 90 seconds or less on the run. I made the deadline read at 01:40:37Z: the run was completed with conclusion success.
  - I then resumed the same QA agent with only the unfinished-round message, the round's scratch subdirectory and the awaited item. There were no missed deadlines.
- **Counts:** 1 QA round, not counted toward the cap because it did not end in In Progress. No fix rounds, no PRs, no evidence recorded, no incidental defects. The coordinator made no tracker writes.
```

## Fixture cancellation (tracker read)

`linear issue update SKL-314 --state "Canceled"` after the run, then `linear issue view SKL-314 --json`:

```text
"identifier": "SKL-314",
"state": {
  "name": "Canceled",
```

## Results

| Check | Observed |
|---|---|
| Awaited item already in its target state at the interim handback | `completed`/`success` at 01:29:35, updated 2026-11-15T22:37:01Z |
| QA agent's own wake-up not armed | no QA tool call between 01:29:27.107 and the resume |
| Interim handback classified before step 0's read-back and step 4 | no checklist read-back or step 4 action until after the resume |
| Deadline recorded | 2026-11-16T01:40:30Z (receipt 01:29:30Z + 1 min + 10 min) |
| Bounded foreground waits | 8 waits of at most 90 s; the last returned 7 s after the deadline |
| Deadline read from the primary source | after the deadline: `gh run view` at 01:40:40.856, `completed`/`success` |
| Resume content | only the unfinished round, its scratch subdirectory and the awaited item |
| User message between interim handback and resume | none |
| QA round count | 1 before and after the resume (no QA round 2 spawned) |
| Read-back resume cap | 0 used |
| `metrics` | off |
| Fixture issue | SKL-314 Canceled after the run (tracker read above) |
