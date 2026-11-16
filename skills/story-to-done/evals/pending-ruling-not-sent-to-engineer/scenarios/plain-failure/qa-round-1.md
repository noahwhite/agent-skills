# QA handback: ABC-123

- Final state: In Progress. QA reopened the story for the failed item below and amended AC2 with a dated deployment-review note.
- Environment: dev (https://dev.example.com), build `4040404` (the merged commit of PR #40).
- PRs merged by QA: none.
- Incidental defects: none.

## QA evidence comment on the story

Build `4040404` on dev, the merged commit of PR #40.
Fixture: the test account `qa-export-10k`, holding 10,000 transactions.

| Item | Verdict | Evidence |
|---|---|---|
| AC1 | verified | The "Export CSV" button is on the account page (screenshot attached). |
| AC2 | failed | The exported header is `date,description,amount`; the `currency` column is missing (assertion output attached). |
| AC3 | verified | An export as account A holds none of account B's transactions (assertion output attached). |
| AC4 | verified | The export of `qa-export-10k` finished in 18 seconds from the click to the completed download, and the export job log records 12 seconds (timing output and job log line attached). |
| DoD1 | verified | CI on PR #40 ran the unit and integration tests green. |
| DoD2 | verified | PR #40's review of record covers its merged head. |
| DoD3 | verified | The user docs page "Exporting transactions" describes the export. |
