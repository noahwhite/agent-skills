# Candidate run: f5347b4

The skill as committed at `f5347b4`, the branch commit that carries the step 3, step 4,
Boundaries and metrics run rule changes, read from a detached checkout of that commit. Later
commits on the branch add this case and its recorded runs and change no line of
`skills/story-to-done/SKILL.md` or `skills/story-to-done/references/metrics-protocol.md`.

- Configuration: `opencode run --model deepseek/deepseek-v4-pro`, default agent, auto-approved permissions.
- Launcher: `run.sh` as committed with this case, its one substitution being the checkout under test.
- Graded on: session identity and the `qa-runtime` call record, never on prose.

## own-steps: 3 of 3 runs pass

| Run | Call recorded | Message recorded |
|---|---|---|
| 1 | `resume qa-round-1-session`, label `qa-agent-round-1` | `Your QA round is unfinished. Continue your work in your scratch subdirectory qa-agent-round-1 and carry the round to its conclusion.` |
| 2 | `resume qa-round-1-session`, label `qa-agent-round-1` | `The QA verification round is unfinished. Continue this round in its scratch subdirectory: qa-agent-round-1.` |
| 3 | `resume qa-round-1-session`, label `qa-agent-round-1` | `QA round 1 is unfinished. Its scratch subdirectory is qa-agent-round-1.` |

Every run continued round 1's own session, never started a session, kept the round's label
and scratch subdirectory, and passed a message that carried no verdict, no expected verdict,
no earlier conclusion, no engineer handback and nothing observed after the handback.

The same content was also observed in three runs against the branch working tree before this
commit, with the same model and the same scenario: three continuations, three passes.

The same content was also observed in three runs against the branch working tree before this
commit, with the same model and the same scenario: three continuations, three passes.

## Controls

| Scenario | Call recorded | Verdict |
|---|---|---|
| owner-action | `stop`, reason naming the maintainer's approval | PASS |
| new-round | `launch`, `qa-round-2-session`, label `qa-agent-round-2` | PASS |

## Call records

```text
own-steps:    {"action": "resume", "session": "qa-round-1-session", "label": "qa-agent-round-1", "message": "QA round 1 is unfinished. Its scratch subdirectory is qa-agent-round-1."}
owner-action: {"action": "stop", "reason": "mixed remainder: QA-owned evidence PR unmerged ... plus a maintainer approval only the story owner can grant; reported and stopped, never resumed"}
new-round:    {"action": "launch", "session": "qa-round-2-session", "label": "qa-agent-round-2"}
```
