# SKL-89 QA evidence

## Round 1, 2026-11-10

The repository deploys nothing (`environments: []`), so the environment under test is merged `main` of `noahwhite/agent-skills`, build `ee91695a4abd73610cb5656dd6528926b95525d0`.
That build is the squash commit of PR #181, whose reviewed head was `a314742054a70066866f6eb0d5d50310751b4e29`; the two trees are identical.
Fixtures: throwaway two-commit git repositories (a base tag and one head commit), built by the QA probe in its scratch directory.
One fixture is plain; the other opts in through `.gitattributes` (`linguist-generated`, `linguist-vendored`) and an `.adversarial-exclude` entry (`fixtures/*`), and adds a rename, a path matching both arms, and a path that needs escaping.
The probe drove `run-adversarial-pipeline.sh` through `preflight`, `run`, `dossier` and `record` for sweep, hunt and arbitrate on both flows, with a stand-in agent that keeps the dossier it was handed.
Fault cases used a `git` wrapper that refuses `git worktree add` (failed checkout) or `git diff --stat` (failed dossier write), a closed stdout on the `dossier` command (exit-trap undo), and an `mv` wrapper that fails only on sidecar targets (sidecar write failure).
The dossier and report-contract comparisons ran the pre-PR script (`c2378ce`) and the merged script on identical fixtures, normalizing per-run paths, temporary-name suffixes and commit SHAs.
There is no visual surface, so structured assertions and their raw output are the evidence, without screenshots.

## Evidence

- Tracker evidence: SKL-89, QA comment `744b8389`.
- Raw evidence: attachments titled `SKL-89 QA probe output (end-to-end gate runs on main)` (106 checks, 0 failed), `SKL-89 QA suite, CI and repo state` and `SKL-89 QA probe source` on that story.
- Suites: the full suite `uv run --locked pytest -q` on the build (1555 passed), and main CI run 42841463575 on `ee91695` (success).

## Verdicts

| Item | Verdict | Evidence |
|---|---|---|
| AC1 persisted measurement and its lifecycle | Verified | On both the `run` and `dossier` flows each sidecar holds exactly a `path=` line with the absolute dossier path and a `bytes=` line equal to `LC_ALL=C wc -c`, then one `excluded` line per EXCLUDED row of the dossier in the same order. All three reason kinds appear, a path matching an attribute and a glob carries the attribute reason, a rename lists both sides, and escaping matches the truncation marker. The arbitrate sidecar lists no excluded line. A later phase never re-measures an earlier sidecar. Re-running hunt drops the arbitrate sidecar, re-running sweep drops hunt and arbitrate, and re-running preflight drops all three. A `run` refused by its predecessor check (exit 13) leaves no sidecar of its own. A `dossier` refused by its predecessor check (exit 13) and a `run` missing `--agent-cmd` (exit 2) leave the earlier sidecar byte- and mtime-identical. A failed checkout, a failed dossier write and an exit-trap undo each leave no sidecar. Sidecar text enters no binding or stamp, and tampering with or deleting sidecars changes no acceptance. A sidecar write failure prints one `WARNING:` line and leaves exit 0, the completion line and `record` unchanged. Dossier bytes match the pre-PR script for all three phases. |
| AC2 report contract unchanged; existing suite passes unchanged; new tests cover the listed cases | Verified | Arbitrate stdout is the agent's report byte for byte and the accepted artifact's first line is `REVIEW-RAN: yes`. A run, a blind run, a `REVIEW-RAN: no` record and a good record exit `0, 17, 17, 0` on both scripts. The squash has no hunk in `accept_phase` or `record`. PR #181 touched only the script and the new `tests/test_pipeline_dossier_sidecars.py`, so every existing test module is unchanged and passes. The new module covers each listed case on both flows. |
| DoD all acceptance criteria met | Verified | AC1 and AC2 above. |
| DoD unit and integration tests written and passing | Verified | Full suite 1555 passed, and main CI is green on the build. |
| DoD independently reviewed | Verified | PR #181 review of record at head `a314742054a70066866f6eb0d5d50310751b4e29`, Codex GPT-6 Sol reviewer and DeepSeek V4 Pro adjudicator; one Medium finding fixed, then no findings. |
| DoD docs updated | Verified | The script header's "Size sidecars" paragraph. |
| DoD verified in a deployed environment (if needed) | Verified, not needed | The repository deploys nothing; verified on merged `main`. |
| DoD no critical bugs or regressions | Verified | Suite and CI are green, the dossier bytes and report contract are unchanged, and the probes found no defect. |

Incidental: PR #181's first review of record (5843996545) names `9d26546` on its first line but was posted against commit `a314742`; the final review of record matches the merged head.
Decision: Done once this evidence PR merges through its review of record and CI.
