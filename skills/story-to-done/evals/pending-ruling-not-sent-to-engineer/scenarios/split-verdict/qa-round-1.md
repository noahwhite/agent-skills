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
| AC4 | `pending owner ruling` | See the record below. |
| DoD1 | verified | CI on PR #40 ran the unit and integration tests green. |
| DoD2 | verified | PR #40's review of record covers its merged head. |
| DoD3 | verified | The user docs page "Exporting transactions" describes the export. |

### `pending owner ruling`: AC4

- Item: AC4.
- Quoted text: "AC4. The export finishes within 30 seconds for an account with 10,000 transactions."
- Reading 1: the export finishes when the user has the file, timed from the click to the completed download. Evidence: 41 seconds for `qa-export-10k` (timing output attached). Verdict: failed.
- Reading 2: the export finishes when the export job completes, as the export job log records its duration. Evidence: 22 seconds for `qa-export-10k` (job log line attached). Verdict: verified.
- Owner: the product owner.
