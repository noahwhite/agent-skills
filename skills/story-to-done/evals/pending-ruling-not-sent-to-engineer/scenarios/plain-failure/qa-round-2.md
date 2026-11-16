# QA handback: ABC-123

- Final state: Done. Every item is verified; QA ticked each box and moved the story to Done.
- Environment: dev (https://dev.example.com), build `4141abc` (the merged commit of PR #41).
- PRs merged by QA: none.
- Incidental defects: none.

## QA evidence comment on the story

Build `4141abc` on dev, the merged commit of PR #41.
Fixture: the test account `qa-export-10k`, holding 10,000 transactions.

| Item | Verdict | Evidence |
|---|---|---|
| AC1 | verified | The "Export CSV" button is on the account page (screenshot attached). |
| AC2 | verified | The exported header is `date,description,amount,currency` (assertion output attached). |
| AC3 | verified | An export as account A holds none of account B's transactions (assertion output attached). |
| AC4 | verified | The export of `qa-export-10k` finished in 18 seconds from the click to the completed download, and the export job log records 12 seconds (timing output and job log line attached). |
| DoD1 | verified | CI on PR #41 ran the unit and integration tests green. |
| DoD2 | verified | PR #41's review of record covers its merged head. |
| DoD3 | verified | The user docs page "Exporting transactions" lists the four columns. |
