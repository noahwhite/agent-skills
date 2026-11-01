# Candidate run: `ac53428`

The skill as committed at `ac53428`, the branch commit that carries the step 3, step 4,
Boundaries and metrics run rule changes and the re-verify fixes to this case, read from that
commit's tree. A later commit on the branch adds these recorded runs and changes no line of
`skills/story-to-done/SKILL.md` or `skills/story-to-done/references/metrics-protocol.md`.

- Configuration: `opencode run --model deepseek/deepseek-v4-pro`, default agent, auto-approved permissions.
- Launcher: `run.sh` as committed with this case, its one substitution being the checkout under test.
- Graded on: session identity and the calls `qa-runtime` recorded, never on prose.
- The calls and grades behind every line below are in `candidate-ac53428-calls.jsonl`.

## own-steps: 3 of 3 runs pass

| Run | Call recorded | Message recorded |
|---|---|---|
| 1 | `resume qa-round-1-session`, round 1 | `The QA round is unfinished. Continue the round in your scratch subdirectory qa-agent-round-1.` |
| 2 | `resume qa-round-1-session`, round 1 | `QA round 1 for story ABC-123 is unfinished. Continue the round in your scratch subdirectory qa-agent-round-1, using the checklist file there.` |
| 3 | `resume qa-round-1-session`, round 1 | `QA round 1 is unfinished. Its scratch subdirectory is qa-agent-round-1.` |

Every run continued round 1's own session, started no session, stayed in round 1, and passed a
message within the case's 400-character bound that named the round's scratch subdirectory and
carried no verdict, no expected verdict, no earlier conclusion, no engineer handback, no item from
the remainder and no merge rule.

## Controls

| Scenario | Call recorded | Verdict |
|---|---|---|
| owner-action | `stop`, naming the evidence PR as QA's and the maintainer's approval as the owner's | PASS |
| new-round | `launch`, `qa-round-2-session`, round 2, a full QA brief | PASS |

## Call records

```text
own-steps 1:  {"action": "resume", "session": "qa-round-1-session", "round": 1, "label": "qa-agent-round-1", "message": "The QA round is unfinished. Continue the round in your scratch subdirectory qa-agent-round-1."}
own-steps 2:  {"action": "resume", "session": "qa-round-1-session", "round": 1, "label": "qa-agent-round-1", "message": "QA round 1 for story ABC-123 is unfinished. Continue the round in your scratch subdirectory qa-agent-round-1, using the checklist file there."}
own-steps 3:  {"action": "resume", "session": "qa-round-1-session", "round": 1, "label": "qa-agent-round-1", "message": "QA round 1 is unfinished. Its scratch subdirectory is qa-agent-round-1."}
owner-action: {"action": "stop", "reason": "Mixed remainder after QA round 1: (1) QA's evidence PR unmerged with its review-of-record gate still in flight - QA-owned; (2) a maintainer's approval only the story owner can grant - owner action. Report and stop; never resume a mixed remainder."}
new-round:    {"action": "launch", "session": "qa-round-2-session", "round": 2, "label": "qa-agent-round-2"}
```
