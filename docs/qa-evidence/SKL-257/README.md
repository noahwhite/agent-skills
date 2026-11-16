# SKL-257 AC5 fixture run: QA interim handback deadline resume

- Date: 2026-11-16
- Skill under test: `skills/story-to-done/` at commit 45d8f69daae36697b9f67c440e05403181a1bed7 (branch `feature/SKL-257-qa-interim-handbacks`), read by path from the worktree
- Fixture issue: SKL-314, `[Tabletop fixture] SKL-257 QA interim handback deadline resume`, created in In Deployment Review so the coordinator starts at step 3, and Canceled after the run
- Awaited item: CI run 43769704269 on noahwhite/agent-skills, already `completed`/`success` (updated 2026-11-15T22:37:01Z) before the run started
- Runtime: Claude Code 2.1.325
- Coordinator: a general-purpose Opus 5.5 subagent launched with the parent brief below
- QA seat: fixture profile copy with `story_to_done.qa` on `runtime: claude-code`, `claude-sonnet-5-5`, effort high
- `metrics: off`

## Parent brief (verbatim)

```text
Story to done SKL-314, metrics=off.

Run the story-to-done skill for SKL-314 by reading and following the file /home/claude/.claude/jobs/02213c5c/tmp/session.eG5tKG/senior-engineer/wt/skills/story-to-done/SKILL.md and its references/ directory beside it. That file is the version under test, so do not load the installed story-to-done skill with the Skill tool. The profile is /home/claude/.claude/jobs/02213c5c/tmp/session.eG5tKG/senior-engineer/fixture/profile.yaml.

Your session scratch directory already exists: /home/claude/.claude/jobs/02213c5c/tmp/session.eG5tKG/senior-engineer/fixture/coordinator/. Use it as the scratch directory and create each role's subdirectory inside it. Your todo list is the checklist file coordinator-todo.md in that directory.

Tabletop harness: SKL-314 is a disposable fixture. When you spawn the QA agent in step 3, append this paragraph verbatim at the end of its brief, after everything step 3 requires:

"Tabletop fixture: SKL-314 is a disposable fixture. Do no verification: do not load any skill, create a branch, open a PR, or write to the tracker. Write your checklist file with one open item, 'wait for CI run 43769704269 on noahwhite/agent-skills to complete (in progress)', then hand back immediately with exactly this text: 'Interim handback: waiting on my own background work, CI run 43769704269 on noahwhite/agent-skills (primary source: GitHub Actions, run 43769704269 in noahwhite/agent-skills). Target state: completed. Expected duration: 1 minute. This is not a final handback and I am not blocked.' Arm no wake-up, monitor, or background task. If you are resumed later, mark that checklist item done and hand back with exactly this text: 'Final handback: SKL-314 is a disposable tabletop fixture, so no verification was done and the story was not moved. Outstanding: the fixture issue SKL-314 must be canceled; owner: the story owner.'"

Never write secrets to files or argv. Run each shell step as one simple command with literal values.
```

The QA agent's own wake-up was not armed: its transcript holds two tool calls before the interim handback (the checklist write and the handback) and none after it until the resume arrived.

## Resume message (verbatim)

Sent by the coordinator with `SendMessage` to the same QA agent at 2026-11-16T00:54:29.784Z:

```text
The round is unfinished. Round scratch subdirectory: /home/claude/.claude/jobs/02213c5c/tmp/session.eG5tKG/senior-engineer/fixture/coordinator/qa-agent-round-1/ . Awaited item: CI run 43769704269 on noahwhite/agent-skills.
```

It states only that the round is unfinished, the round's scratch subdirectory and the awaited item.
It carries no conclusion (the coordinator had read `completed`/`success`), no verdict, no earlier round's conclusions and no senior engineer handback.

## QA agent transcript (UTC)

```text
00:43:05.390 user: QA brief for SKL-314 (step 3 brief plus the tabletop paragraph above)
00:43:08.086 Write qa-agent-round-1-todo.md: "- [ ] wait for CI run 43769704269 on noahwhite/agent-skills to complete (in progress)"
00:43:10.722 SubagentHandback: "Interim handback: waiting on my own background work, CI run 43769704269 on noahwhite/agent-skills (primary source: GitHub Actions, run 43769704269 in noahwhite/agent-skills). Target state: completed. Expected duration: 1 minute. This is not a final handback and I am not blocked."
00:54:29.899 message from the coordinator: the resume message above
00:54:32.661 Write qa-agent-round-1-todo.md: "- [x] wait for CI run 43769704269 on noahwhite/agent-skills to complete"
00:54:34.772 SubagentHandback: "Final handback: SKL-314 is a disposable tabletop fixture, so no verification was done and the story was not moved. Outstanding: the fixture issue SKL-314 must be canceled; owner: the story owner."
```

## Coordinator tool-call transcript from the QA spawn (UTC)

Bootstrap (reading the skill, its references and the profile, `select-path.py` printing `no-deployment`, the story read showing In Deployment Review) ran from 00:42:08 to 00:43:05 and is omitted.
The only incoming message between the interim handback at 00:43:11.112 and the resume at 00:54:29.784 is that handback itself; no user message arrived in that window.

```text
00:43:05.254 Agent (general-purpose, model sonnet, effort high): "QA round 1 SKL-314"
00:43:07.823 Edit coordinator-todo.md: spawn ticked; "wait for handback, then classify it (in progress)"
00:43:11.112 [incoming] QA agent handback: the interim handback text
00:43:12.935 Bash date -u  -> 2026-11-16T00:43:13Z   (receipt)
00:43:17.942 Edit coordinator-todo.md:
             "- [x] QA round 1: wait for handback, then classify it (interim handback received 2026-11-16T00:43:13Z)
              - [ ] QA round 1 interim: awaited item CI run 43769704269 on noahwhite/agent-skills; primary source GitHub Actions run 43769704269; target state completed; stated 1 min -> deadline 2026-11-16T00:54:13Z (1 + max(10, 0.5) = 11 min); misses: 0 (in progress)"
00:43:18.344 Bash gh run view 43769704269 --repo noahwhite/agent-skills --json status,conclusion,updatedAt
             -> {"conclusion":"success","status":"completed","updatedAt":"2026-11-15T22:37:01Z"}
00:43:35.107 Write bounded-wait.sh (each wait = min(90 s, deadline - now - 5 s), gh run view under a per-read timeout)
00:43:35.907 Bash bounded-wait.sh -> 00:45:05.338 "last read: completed/success; 548 s to deadline"
00:45:07.058 Bash bounded-wait.sh -> 00:46:37.566 "last read: completed/success; 456 s to deadline"
00:46:38.929 Bash bounded-wait.sh -> 00:48:09.088 "last read: completed/success; 364 s to deadline"
00:48:10.547 Bash bounded-wait.sh -> 00:49:41.459 "last read: completed/success; 272 s to deadline"
00:49:42.815 Bash bounded-wait.sh -> 00:51:12.248 "last read: completed/success; 181 s to deadline"
00:51:13.814 Bash bounded-wait.sh -> 00:52:43.244 "last read: completed/success; 90 s to deadline"
00:52:44.740 Bash bounded-wait.sh -> 00:54:08.325 "last read: completed/success; 5 s to deadline"
00:54:10.124 Bash date -u -> 2026-11-16T00:54:10Z   (5 s or less left: no further wait)
00:54:11.806 Bash timeout 5 tail -f /dev/null -> exit 124 at 00:54:17.902
00:54:12.159 Bash date -u -> 2026-11-16T00:54:12Z
00:54:18.870 Bash timeout 3 tail -f /dev/null -> exit 124 at 00:54:22.914
00:54:19.158 Bash date -u -> 2026-11-16T00:54:19Z   (deadline passed)
00:54:24.324 Bash gh run view 43769704269 --repo noahwhite/agent-skills --json status,conclusion,updatedAt   (deadline read)
             -> {"conclusion":"success","status":"completed","updatedAt":"2026-11-15T22:37:01Z"}
00:54:28.433 Edit coordinator-todo.md:
             "- [x] QA round 1 interim: deadline read at 2026-11-16T00:54:19Z from GitHub Actions: completed/success (concluded)
              - [ ] QA round 1 interim: resume same QA agent (QA deadline resume, no round increment, not a read-back resume) (in progress)"
00:54:29.784 SendMessage to the round 1 QA agent: the resume message above
00:54:35.092 [incoming] QA agent final handback
00:54:36.996 Read qa-agent-round-1-todo.md -> "- [x] wait for CI run 43769704269 on noahwhite/agent-skills to complete"
00:54:37.045 Bash linear issue view SKL-314 --json -> state In Deployment Review
00:54:43.094 Edit coordinator-todo.md: resume ticked; final handback classified; read-back 0/2; step 4 owner-action stop
00:54:52.688 SubagentHandback: closing report
```

## Coordinator checklist at the end of the run (QA section)

```text
- [x] QA round 1: spawn QA agent (Sonnet 5.5, effort high, no environment named)
- [x] QA round 1: wait for handback, then classify it (interim handback received 2026-11-16T00:43:13Z)
- [ ] QA round 1 interim: awaited item CI run 43769704269 on noahwhite/agent-skills; primary source GitHub Actions run 43769704269; target state completed; stated 1 min -> deadline 2026-11-16T00:54:13Z (1 + max(10, 0.5) = 11 min); misses: 0; bounded foreground waits (7 x <=90 s) until deadline
- [x] QA round 1 interim: deadline read at 2026-11-16T00:54:19Z from GitHub Actions: completed/success (concluded)
- [x] QA round 1 interim: resume same QA agent (QA deadline resume, no round increment, not a read-back resume)
- [x] QA round 1: next handback classified final (not interim)
- [x] QA round 1: read back QA checklist (all items done; read-back resumes: 0/2)
- [x] QA round 1: read back story state (In Deployment Review); no PRs merged by QA, so no review-of-record read-back
- [x] Step 4: In Deployment Review bullet; outstanding item "cancel fixture SKL-314" owned by the story owner -> report and stop
```

## Coordinator closing report (excerpt)

```text
- **QA round 1:** one QA agent on Sonnet 5.5 at high effort, with no environment named.
  - **Interim handback:** received at 2026-11-16T00:43:13Z. It named CI run 43769704269 on noahwhite/agent-skills, target state completed, expected duration 1 minute. The deadline was 00:54:13Z: 1 minute plus 10 minutes, since 10 minutes is more than half of 1 minute.
  - **Resume:** I resumed the same QA agent with a message stating only that the round is unfinished, its scratch subdirectory and the awaited item. This did not count as a new round or against the read-back resume cap.
**Rounds and evidence:** 1 QA round, which counts toward neither the cap nor fixes, because its read-back was not In Progress.
```

## Results

| Check | Observed |
|---|---|
| Awaited item already in its target state at the interim handback | `completed`/`success` at 00:43:18, updated 2026-11-15T22:37:01Z |
| QA agent's own wake-up not armed | no QA tool call between 00:43:10.722 and the resume |
| Interim handback classified before step 0's read-back and step 4 | no checklist read-back or step 4 action until after the resume |
| Deadline recorded | 2026-11-16T00:54:13Z (receipt 00:43:13Z + 1 min + 10 min) |
| Bounded foreground waits | 7 waits of at most 90 s, the last returning with 5 s left |
| Deadline read from the primary source | 2026-11-16T00:54:19Z, `gh run view` at 00:54:24: `completed`/`success` |
| Resume content | only the unfinished round, its scratch subdirectory and the awaited item |
| User message between interim handback and resume | none |
| QA round count | 1 before and after the resume (no QA round 2 spawned) |
| Read-back resume cap | 0/2 used |
| `metrics` | off |
| Fixture issue | SKL-314 Canceled after the run |
