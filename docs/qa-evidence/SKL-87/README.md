# SKL-87 QA evidence

## Round 1, 2026-11-10

The repository deploys nothing (`environments: []`), so the environment under test is merged `main` of `noahwhite/agent-skills`, build `bd946035c1a305e9ed28a26652ab3fb9bc126629`.
That build is the squash commit of PR #177, whose reviewed head was `d21a0f3523a429fae252138dd8a72b7c0272adef`.
Fixtures: a fresh two-commit git repository (a `base` tag and one distinct head commit), built by the QA probe in its scratch directory.
The head commit changes 11 files: many hunks, a first hunk over the cap, one 6,000-byte line, a 2,175-byte path, a binary file, a path with a quote and a tab, a non-ASCII path, a rename, a deletion, a CRLF file without a final newline, and a mode-only change.
The probe drove `run-adversarial-pipeline.sh` through `preflight`, `run` and `dossier` for sweep, hunt and arbitrate with a fake agent, and compared each dossier with an oracle built from the AC text.
It ran the same chain with the pre-PR script (`f689872`) to compare the dossier contract.
There is no visual surface, so structured assertions and their raw output are the evidence, without screenshots.

## Evidence

- Tracker evidence: SKL-87, QA comment `8e1dcd96`.
- Raw evidence: attachments titled `SKL-87 QA probe output (93/93)`, `SKL-87 QA suite, CI and repo state` and `SKL-87 QA probe source` on that story.
- Flows exercised: `run` and `dossier` for sweep and hunt, and `dossier` for arbitrate, on both the merged and the pre-PR script.
- Fault injection: a `git` wrapper on `PATH` failed only the `--unified=1` call, during `dossier sweep` and during `run sweep`.
- Suites: the full suite `uv run --locked pytest -q` on the build (1503 passed), and main CI run 42778460811 on `bd94603` (success).

## Verdicts

| Item | Verdict | Evidence |
|---|---|---|
| AC1 `--unified=1`, per-file cap with whole-hunk truncation, first-hunk and header clipping at line boundaries, exact marker, byte identity under the cap, unchanged diffstat, `git diff` failure, on sweep and hunt for both flows | Verified | The probe passed 93 of 93 assertions. The DIFF body of all four sweep and hunt dossiers equals the oracle byte for byte (11 sections, 9 truncated). Each marker names the destination path for a rename and the source path for a deletion, re-escapes the quoted path, shows the non-ASCII path raw, and names the dossier's own `CHECKOUT:` value. The over-cap header section emitted zero bytes and the 6,000-byte line was never cut. The two under-cap sections were byte-identical with no marker, and the diffstat equals `git diff --stat`. The injected failure exited 128 on both flows with no dossier path printed, no new dossier file, no agent launch, no binding left and the checkout removed. |
| AC2 report contract unchanged; existing suite unchanged and passing; new tests on a two-commit fixture | Verified | The arbitrate dossier is byte-identical between the pre-PR and merged scripts, and the sweep and hunt text before the DIFF section is identical. `tests/test_pipeline_dossier_checkout.py` is untouched by PR #177 and its `===== DIFF (` and `diff --git a/app.py b/app.py` assertions are present and pass. The new `tests/test_pipeline_diff_cap.py` covers each case AC1 lists for sweep and hunt on both flows, seeded from a `base` tag and a distinct head commit. Six extra edge-case tests (three exact-cap boundaries, short binary and mode-only sections, a pure rename with a new file, and many files) run on both flows for sweep only. |
| DoD all acceptance criteria met | Verified | AC1 and AC2 above. |
| DoD unit and integration tests written and passing | Verified | Full suite 1503 passed, and main CI is green on the build. |
| DoD independently reviewed | Verified | PR #177 review of record at the merged head `d21a0f3523a429fae252138dd8a72b7c0272adef`, Codex GPT-6 Sol reviewer and DeepSeek V4 Pro adjudicator, no findings. |
| DoD docs updated | Verified | The script header documents `DIFF_CAP_BYTES`, the truncation rules and the marker, and `SKILL.md` notes the python3 preflight check. |
| DoD verified in a deployed environment (if needed) | Verified, not needed | The repository deploys nothing; verified on merged `main`. |
| DoD no critical bugs or regressions | Verified | Suite and CI are green, the dossier contract is unchanged, and the probe found no defect. |

No incidental defect was observed.
Decision: Done once this evidence PR merges through its review of record and CI.
