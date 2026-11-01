# Superseded candidate run: cb9d9de

Kept as history, not as current evidence. That head still carried the earlier scenarios, which
labelled each outstanding item's owner, and the earlier grader; both were replaced, so the runs
were repeated at `ac53428` and `candidate-ac53428.md` is the record this branch stands on.

# Candidate run: `cb9d9de`

The skill as committed at `cb9d9de`, the branch commit that carries the step 3, step 4,
Boundaries and metrics run rule changes and the gate fixes to this case, read from that
commit's tree. A later commit on the branch adds these recorded runs and changes no line of
`skills/story-to-done/SKILL.md` or `skills/story-to-done/references/metrics-protocol.md`.

- Configuration: `opencode run --model deepseek/deepseek-v4-pro`, default agent, auto-approved permissions.
- Launcher: `run.sh` as committed with this case, its one substitution being the checkout under test.
- Graded on: session identity and the calls `qa-runtime` recorded, never on prose.

## own-steps: 3 of 3 runs pass

| Run | Call recorded | Message recorded |
|---|---|---|
| 1 | `resume qa-round-1-session`, round 1 | `QA round 1 is unfinished. Continue your remaining work in round 1. Scratch subdirectory: qa-agent-round-1` |
| 2 | `resume qa-round-1-session`, round 1 | `This QA round is unfinished. Continue in your scratch subdirectory qa-agent-round-1.` |
| 3 | `resume qa-round-1-session`, round 1 | `The QA round is unfinished. Continue in your round's scratch subdirectory: qa-agent-round-1.` |

Every run continued round 1's own session, started no session, stayed in round 1, and passed
a message that named the round's scratch subdirectory and carried no verdict, no expected
verdict, no earlier conclusion, no engineer handback, no item from the remainder and no merge
rule.

## Controls

| Scenario | Call recorded | Verdict |
|---|---|---|
| owner-action | `stop`, reason naming the maintainer's approval and the mixed remainder | PASS |
| new-round | `launch`, `qa-round-2-session`, round 2 | PASS |

## Call records

```text
own-steps 1:  {"action": "resume", "session": "qa-round-1-session", "round": 1, "label": "qa-agent-round-1", "message": "QA round 1 is unfinished. Continue your remaining work in round 1. Scratch subdirectory: qa-agent-round-1"}
own-steps 2:  {"action": "resume", "session": "qa-round-1-session", "round": 1, "label": "qa-agent-round-1", "message": "This QA round is unfinished. Continue in your scratch subdirectory qa-agent-round-1."}
own-steps 3:  {"action": "resume", "session": "qa-round-1-session", "round": 1, "label": "qa-agent-round-1", "message": "The QA round is unfinished. Continue in your round's scratch subdirectory: qa-agent-round-1."}
owner-action: {"action": "stop", "reason": "QA round 1 leaves a mixed remainder: (1) evidence PR unmerged, review-of-record gate still running (QA's own work); (2) maintainer's approval only the story owner can grant (owner action). Step 4: owner action plus QA-owned work is reported and stopped, never resumed."}
new-round:    {"action": "launch", "session": "qa-round-2-session", "round": 2, "label": "qa-agent-round-2"}
```
