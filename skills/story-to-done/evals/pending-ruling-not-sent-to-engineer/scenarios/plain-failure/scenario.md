# Scenario: QA verifies the CSV export story

- Story `ABC-123`, "Export transactions as CSV"; the state you have just read back is In Deployment Review.
- The senior engineer has just handed back from implementing it: PR #40 (https://github.com/example/ledger/pull/40) is merged at head `4040404040404040404040404040404040404040`, its review of record covers that head, and the build on dev is that merged commit.
- No QA round has run yet, so step 3 is next.
- Checklist files in this run: `senior-engineer/senior-engineer-todo.md` (the senior engineer's).

The story's acceptance criteria and Definition of Done:

- AC1. The account page has an "Export CSV" button.
- AC2. The CSV has the columns date, description, amount and currency, in that order.
- AC3. Only the signed-in account's transactions are exported.
- AC4. The export finishes within 30 seconds for an account with 10,000 transactions.
- DoD1. Unit and integration tests written and passing.
- DoD2. Independently reviewed.
- DoD3. User docs updated.
