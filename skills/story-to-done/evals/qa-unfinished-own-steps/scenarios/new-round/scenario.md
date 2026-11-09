# Scenario: a new QA round is due after a fix cycle

- Story `ABC-123`; the state you have just read back is In Deployment Review.
- QA round 1 ended with the story reopened; the senior engineer fixed the failed item, and that fix is merged.
- The senior engineer has just handed back from that fix cycle: the story is back in deployment review, and no QA round is running.
- `qa-round-1.json` is round 1's launch record.
- QA's round 1 handback names nothing that is still outstanding.
- Checklist files in this run: `qa-agent-round-1/qa-agent-round-1-todo.md` (QA round 1's) and `senior-engineer/senior-engineer-todo.md` (the senior engineer's).
