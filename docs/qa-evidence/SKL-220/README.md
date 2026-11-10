# SKL-220 QA evidence

## Round 1, 2026-11-10

The repository deploys nothing (`environments: []`), so the environment under test is merged `main` of `noahwhite/agent-skills`, build `23c40cd26cc2c75140ebdfa29280aac99cf749aa`.
That build is the squash commit of PR #182, whose reviewed head was `66c2e97027b47c4dcb1d25008e345cd0898a9564`.
The PR's two files are identical at that head and in the build; the two trees differ only by SKL-89's two files from PR #181.
Fixtures: none, because the deliverable is the `cleanup` skill text and its contract tests.
A QA probe asserted each C1 rule against `skills/cleanup/SKILL.md` and its vendored `references/runtimes.md` on the build.
There is no visual surface, so structured assertions and their raw output are the evidence, without screenshots.

## Evidence

- Tracker evidence: SKL-220, QA comment `4dd86997`.
- Raw evidence: attachments titled `SKL-220 QA C1 probe output (cleanup SKILL.md on main 23c40cd)`, `SKL-220 QA suite, CI and repo state (main 23c40cd)` and `SKL-220 QA C1 probe source` on that story.
- Suites: the full suite `uv run --locked pytest -q` on the build (1565 passed), `tests/test_cleanup.py` (36 passed), and main CI run 42841724669 on `23c40cd` (success).

## Verdicts

| Item | Verdict | Evidence |
|---|---|---|
| C1 retire memory notes: step 1 state, step 2 memory source and match, scoped boundary text, step 3 state guard and read-back, step 6 report, pinned runtime lines | Verified | The probe passed 31 of 31 checks. Step 1 records each resolved key's tracker state. Step 2 adds the memory source from the runtimes "Persistent memory" row for the main checkout and each inventoried worktree, names no runtime and no store path, and reports an unreadable store as unsearchable. A note is `remove` on its file name, extension ignored, or frontmatter `name`, case-insensitively, with no letter or digit either side of the key; a body-only mention is `skip` and reported. The step 2 boundary sentence and the Boundaries bullet are scoped to admit notes. Step 3 removes a note with a single quoted-path `rm` only when the recorded state equals `profile.tracker.states.done` or `profile.tracker.states.canceled`, removes none when either key is unset and names it, reads each removal back as `refused` when still present, and leaves index lines unedited, said once. The merge-evidence sentence is the only other step 3 change, scoped to exclude notes. Step 6 reports each note by file name and carries the pinned `skipped:` and `unchecked:` lines, and the Read first bullet names the row. |
| C2 test, vendoring and suite | Verified | Each C1 rule maps to a named test in `tests/test_cleanup.py`. The boundary-sentence test pins the scoped text and asserts the unscoped sentence is gone. `scripts/vendor_shared.py --check` and a rerun leave no diff, and `uv run pytest` passes. |
| DoD all acceptance criteria met | Verified | C1 and C2 above. |
| DoD unit and integration tests written and passing | Verified | Full suite 1565 passed, and main CI is green on the build. |
| DoD independently reviewed | Verified | PR #182 review of record at head `66c2e97027b47c4dcb1d25008e345cd0898a9564`, Codex GPT-6 Sol reviewer and DeepSeek V4 Pro adjudicator; three findings ruled invalid against the story's out-of-scope list and accepted limits. |
| DoD docs updated | Verified | `skills/cleanup/SKILL.md` is the documentation the story changes. |
| DoD verified in a deployed environment (if needed) | Verified, not needed | The repository deploys nothing; verified on merged `main`. |
| DoD no critical bugs or regressions | Verified | Suite and CI are green, and the change touches only the cleanup skill text and its tests. |

No incidental defect was observed.
Decision: Done once this evidence PR merges through its review of record and CI.
