# SKL-257 AC5 fixture run: QA interim handback deadline resume

- Date: 2026-11-16
- Skill under test: `skills/story-to-done/` at commit 6a567c875f32deeaeee3553883f1975c2d75fe8d (branch `feature/SKL-257-qa-interim-handbacks`), read by path from the worktree; `git diff 6a567c8 HEAD -- skills/` is empty on the branch, so the text exercised is the text at the head
- Fixture issue: SKL-314, `[Tabletop fixture] SKL-257 QA interim handback deadline resume`, in In Deployment Review for the run so the coordinator starts at step 3, and Canceled after the run (tracker read below)
- Awaited item: CI run 43769704269 on noahwhite/agent-skills, already `completed`/`success` (updated 2026-11-15T22:37:01Z) before the run started
- Runtime: Claude Code 2.1.325
- Coordinator: a general-purpose Opus 5.5 subagent launched with the parent brief below
- QA seat: fixture profile copy with `story_to_done.qa` on `runtime: claude-code`, `claude-sonnet-5-5`, effort high
- `metrics: off`

Earlier runs of the same fixture at commits 45d8f69 and ec67ab5 were re-run because the skill text changed after each; this run is on the final skill text.

## Parent brief (verbatim)

```text
Story to done SKL-314, metrics=off.

Run the story-to-done skill for SKL-314 by reading and following the file /home/claude/.claude/jobs/02213c5c/tmp/session.eG5tKG/senior-engineer/wt/skills/story-to-done/SKILL.md and its references/ directory beside it. That file is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is /home/claude/.claude/jobs/02213c5c/tmp/session.eG5tKG/senior-engineer/fixture/profile.yaml.

Your session scratch directory already exists: /home/claude/.claude/jobs/02213c5c/tmp/session.eG5tKG/senior-engineer/fixture/coordinator-3/. Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-314 is a disposable fixture. When you spawn the QA agent in step 3, append this paragraph verbatim at the end of its brief, after everything step 3 requires:

"Tabletop fixture: SKL-314 is a disposable fixture. Do no verification: do not load any skill, create a branch, open a PR, or write to the tracker. Write your checklist file with one open item, 'wait for CI run 43769704269 on noahwhite/agent-skills to complete (in progress)', then hand back immediately with exactly this text: 'Interim handback: waiting on my own background work, CI run 43769704269 on noahwhite/agent-skills (primary source: GitHub Actions, run 43769704269 in noahwhite/agent-skills). Target state: completed. Expected duration: 1 minute. This is not a final handback and I am not blocked.' Arm no wake-up, monitor, or background task. If you are resumed later, mark that checklist item done and hand back with exactly this text: 'Final handback: SKL-314 is a disposable tabletop fixture, so no verification was done and the story was not moved. Outstanding: the fixture issue SKL-314 must be canceled; owner: the story owner.'"

Never write secrets to files or argv. Run each shell step as one simple command with literal values.
```

The QA agent's own wake-up was not armed: its transcript holds two tool calls before the interim handback (the checklist write and the handback) and none after it until the resume arrived.

## Resume message (verbatim)

Sent by the coordinator with `SendMessage` to the same QA agent at 2026-11-16T02:45:31.911Z:

```text
The QA round is unfinished. Round scratch subdirectory: /home/claude/.claude/jobs/02213c5c/tmp/session.eG5tKG/senior-engineer/fixture/coordinator-3/qa-agent-round-1/ . Awaited item: CI run 43769704269 on noahwhite/agent-skills.
```

It states only that the round is unfinished, the round's scratch subdirectory and the awaited item.
It carries no conclusion (the coordinator had read `completed`/`success`), no verdict, no earlier round's conclusions and no senior engineer handback.

## QA agent transcript (UTC)

```text
02:34:00.216 user: QA brief for SKL-314 (step 3 brief plus the tabletop paragraph above)
02:34:02.264 Write qa-agent-round-1-todo.md: "- [ ] wait for CI run 43769704269 on noahwhite/agent-skills to complete (in progress)"
02:34:03.756 SubagentHandback: "Interim handback: waiting on my own background work, CI run 43769704269 on noahwhite/agent-skills (primary source: GitHub Actions, run 43769704269 in noahwhite/agent-skills). Target state: completed. Expected duration: 1 minute. This is not a final handback and I am not blocked."
02:45:32.074 message from the coordinator: the resume message above
02:45:34.430 Write qa-agent-round-1-todo.md: "- [x] wait for CI run 43769704269 on noahwhite/agent-skills to complete"
02:45:34.856 SubagentHandback: "Final handback: SKL-314 is a disposable tabletop fixture, so no verification was done and the story was not moved. Outstanding: the fixture issue SKL-314 must be canceled; owner: the story owner."
```

## Coordinator tool-call transcript from the QA spawn (UTC)

Bootstrap (reading the skill, its references and the profile, `select-path.py` printing `no-deployment`, the story read showing In Deployment Review) ran from 02:33:11 to 02:34:00 and is omitted.
The only incoming message between the interim handback at 02:34:04.135 and the resume at 02:45:31.911 is that handback itself; no user message arrived in that window.

```text
02:34:00.134 Agent (general-purpose, model sonnet, effort high): "QA round 1 SKL-314"
02:34:04.135 [incoming] QA agent handback: the interim handback text
02:34:05.982 Bash date -u -> 2026-11-16T02:34:06Z   (receipt)
02:34:12.239 Edit coordinator-todo.md:
             "- [x] QA round 1: classify handback - interim (own background work, not final, not blocked)
              - [ ] QA round 1 interim deadline: awaited item CI run 43769704269 on noahwhite/agent-skills; primary source GitHub Actions run 43769704269; target state completed; received 2026-11-16T02:34:06Z; stated 1 min + 10 min = deadline 2026-11-16T02:45:06Z; misses 0"
02:34:12.782 Bash gh run view 43769704269 -R noahwhite/agent-skills --json status,conclusion,headBranch,event
             -> {"conclusion":"success","event":"push","headBranch":"main","status":"completed"}
02:34:22.009 Bash timeout 85 gh run watch 43769704269 -R noahwhite/agent-skills --interval 30 --exit-status
             -> "Run ci (43769704269) has already completed with 'success'"
02:34:23.571 Bash timeout 85 tail -f /dev/null -> exit 124 at 02:35:49
02:35:52.253 Bash timeout 88 tail -f /dev/null (three calls sent in one block, run concurrently) -> exit 124 at 02:37:21
02:37:25.412 Bash timeout 88 tail -f /dev/null -> exit 124 at 02:38:53
02:38:55.140 Bash timeout 88 tail -f /dev/null -> exit 124 at 02:40:23
02:40:24.384 Bash timeout 88 tail -f /dev/null -> exit 124 at 02:41:52
02:41:55.217 Bash timeout 88 tail -f /dev/null -> exit 124 at 02:43:23
02:43:30.080 Bash timeout 88 tail -f /dev/null -> exit 124 at 02:44:58
02:44:59.851 Bash date -u -> 02:45:00
02:45:04.538 Bash timeout 8 tail -f /dev/null -> exit 124 at 02:45:12
02:45:18.213 Bash date -u -> 2026-11-16T02:45:18Z
02:45:20.768 Bash gh run view 43769704269 -R noahwhite/agent-skills --json status,conclusion   (deadline read)
             -> {"conclusion":"success","status":"completed"}
02:45:26.375 Edit coordinator-todo.md:
             "- [x] QA round 1: deadline read at 2026-11-16T02:45:18Z from GitHub Actions - status completed, conclusion success (concluded)
              - [ ] QA round 1: deadline resume of QA agent (does not count against read-back cap or round count) (in progress)"
02:45:31.911 SendMessage to the round 1 QA agent: the resume message above
02:45:35.277 [incoming] QA agent final handback
02:45:38.713 Read qa-agent-round-1-todo.md -> "- [x] wait for CI run 43769704269 on noahwhite/agent-skills to complete"
02:45:38.718 Bash linear issue view SKL-314 --json -> state In Deployment Review
02:45:44.415 Edit coordinator-todo.md: resume ticked; second handback final; checklist read-back (read-back resume count: 0); step 4 owner-action stop
02:45:51.903 SubagentHandback: closing report
```

Two deviations from the existing wait rule (`references/interim-handbacks.md`, Deadline) are recorded as observed:

- After the one `gh run watch` returned because the run had already completed, the waits were plain `tail -f /dev/null` sleeps under `timeout`, not watches on the primary source.
- The last wait started at 02:45:04 with 2 seconds left and ran 8 seconds, returning at 02:45:12, 6 seconds after the 02:45:06 deadline rather than at or before it.

## Coordinator checklist at the end of the run (QA section)

```text
- [x] QA round 1: create qa-agent-round-1/ and spawn QA agent
- [x] QA round 1: classify handback - interim (own background work, not final, not blocked)
- [ ] QA round 1 interim deadline: awaited item CI run 43769704269 on noahwhite/agent-skills; primary source GitHub Actions run 43769704269; target state completed; received 2026-11-16T02:34:06Z; stated 1 min + 10 min = deadline 2026-11-16T02:45:06Z; misses 0
- [x] QA round 1: bounded foreground waits on the run until the deadline (no new QA handback arrived before the deadline)
- [x] QA round 1: deadline read at 2026-11-16T02:45:18Z from GitHub Actions - status completed, conclusion success (concluded)
- [x] QA round 1: deadline resume of QA agent (does not count against read-back cap or round count)
- [x] QA round 1: second handback classified - final, not interim (names outstanding item owned by the story owner)
- [x] QA round 1: checklist read-back - all items done (read-back resume count: 0)
- [x] QA round 1: read back story state - In Deployment Review; QA merged no PR
- [x] Step 4: In Deployment Review with an outstanding item owned by the story owner (cancel fixture SKL-314) - report and stop
```

## Coordinator closing report (excerpt)

```text
- **Deadline read:** at 2026-11-16T02:45:18Z, from GitHub Actions: status completed, conclusion success. No deadline was missed.
- **Deadline resume:** I resumed the same QA agent with a message stating only that the round was unfinished, its scratch subdirectory and the awaited item. The resume did not increment the round count or use the read-back cap.
- **Rounds:** 1 counted QA round, which did not end In Progress, with 0 items fixed. QA recorded no evidence and noted no incidental defects.
```

## Fixture cancellation (tracker read)

`linear issue update SKL-314 --state "Canceled"` after the run, then `linear issue view SKL-314 --no-comments`:

```text
# SKL-314: [Tabletop fixture] SKL-257 QA interim handback deadline resume

**State:** Canceled | **Priority:** --- | **Assignee:** Unassigned | **Cycle:** #3 (now)
```

## Results

| Check | Observed |
|---|---|
| Awaited item already in its target state at the interim handback | `completed`/`success` at 02:34:12 |
| QA agent's own wake-up not armed | no QA tool call between 02:34:03.756 and the resume |
| Interim handback classified before step 0's read-back and step 4 | no checklist read-back or step 4 action until after the resume |
| Deadline recorded | 2026-11-16T02:45:06Z (receipt 02:34:06Z + 1 min + 10 min) |
| Deadline read from the primary source | after the deadline: clock 02:45:18Z, `gh run view` at 02:45:20.768, `completed`/`success` |
| Resume content | only the unfinished round, its scratch subdirectory and the awaited item |
| User message between interim handback and resume | none |
| QA round count | 1 before and after the resume (no QA round 2 spawned) |
| Read-back resume cap | 0 used |
| `metrics` | off |
| Fixture issue | SKL-314 Canceled after the run (tracker read above) |
