# SKL-211 QA evidence

## Round 1

Date: 2026-11-07 UTC, independent QA round 1.
Build under test: `main` at `db1ad8a1d4a635dff8b5ebaa8e1f1238516de5f8`, the squash merge of PR 160, whose reviewed head `a0d19cffab9755a65a7aa9fd89a6cb9118323c6f` has the identical tree.
Environment: the profile lists no environments, so every item was verified against `main`.
Tool versions: git 2.43.0 and uv 0.13.7.
Fixtures: none needed.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-211 as the "QA r1 raw assertion output" attachment.

| Item | Verdict | Evidence |
|---|---|---|
| A1: note file on `main` | Verified | `docs/throwaway/s6-note.md` is the only file under `docs/throwaway`, and `od -c` shows exactly `SKL-206 S6 throwaway note` followed by one newline. |
| A2: tests on `main` | Verified | `uv run --locked pytest -q` at `db1ad8a` reports 1300 passed and exits 0. |
| DoD1: all acceptance criteria met | Verified | A1 and A2 are verified. |
| DoD2: tests pass | Verified | See A2; the `checks` job (Repository tests) of `main` push run 42421793060 succeeded. |
| DoD3: independently reviewed | Verified | PR 160 review 5815382655 at `a0d19cffab9755a65a7aa9fd89a6cb9118323c6f`, the final head, is the review of record (Codex GPT-6 Sol reviewer, DeepSeek V4 Pro adjudicator), with no findings. |
| DoD4: verified in a deployed environment | Not needed | The profile lists no environments, as the item states. |

Observations, not AC gaps:

- The `discovery` job of `main` push run 42421793060 failed with "skill API returned undecodable JSON", as it has on most runs on several branches since about 21:07 UTC on 2026-11-07; it does not run the repository tests.

Closing decision: Done once this evidence PR merges, since every acceptance criterion and Definition of Done item is verified.
