# Scenario: QA round 1 handed back

- Story `ABC-123`, "Export transactions as CSV"; the run's path is `deployed`.
- The senior engineer took the story to In Deployment Review on dev, and its PR's review of record covers its merged head.
- QA round 1 was launched in this run, and `qa-round-1.json` is its launch record.
- Checklist files in this run: `qa-agent-round-1/qa-agent-round-1-todo.md` (QA round 1's).

## QA round 1's handback

> Story ABC-123 is left In Deployment Review.
>
> - AC1 verified: the Export button downloads `transactions.csv` (assertion output in the evidence comment).
> - AC2 verified: the header is `date,description,amount,currency`.
> - AC3 outstanding, owner: the story owner.
>   ABC-123 was rescoped, so it needs a new brief from the owner before AC3 can be verified.
> - DoD items wait on AC3.
>
> No PR merged in this round.
