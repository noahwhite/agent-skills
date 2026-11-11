# SKL-241 QA evidence

## Round 1, 2026-11-11

The repository deploys nothing (`environments: []`), so the environment under test is merged `main` of `noahwhite/agent-skills`, build `fd022dc8e06b65be94722a5489579b932afc32f4`.
That build is the squash commit of PR #192, whose reviewed head was `99bc462aeeb2778bf07df0988ea2dad2fa5218f7`; the two trees are identical.
Dependencies SKL-87, SKL-88 and SKL-89 are Done.
Fixtures: throwaway two-commit git repositories (a base tag and one head commit), one per flow, built by the QA probe in its scratch directory.
Each fixture opts in to exclusion through `.gitattributes` (`gen/** linguist-generated`) and `.adversarial-exclude` (`fixtures/*`), so the sweep and hunt sidecars carry `excluded` lines.
The probe drove `run-adversarial-pipeline.sh` from the build through `preflight`, `paths`, `run`, `dossier`, `record` and `cleanup` for sweep, hunt and arbitrate, once on the `run` flow and once on the `dossier` and `record` flow, with a stand-in agent that writes a `REVIEW-RAN: yes` report.
After each step it printed `dossier-sizes.md`, the sidecars present, and each sidecar's `bytes=` value against `LC_ALL=C wc -c` of its dossier.
Fault cases used a directory standing in the log's place (log write failure) and a closed stdout on the `dossier` command (exit-trap undo).
The `paths` comparison ran the pre-PR script (blob `c6c1698`) and the build's script on the same fixture.
There is no visual surface, so structured assertions and their raw output are the evidence, without screenshots.

## Evidence

- Tracker evidence: SKL-241, QA comment `e0785f78`.
- Raw evidence: attachments titled `SKL-241 QA probe output (run flow)`, `SKL-241 QA probe output (dossier flow)`, `SKL-241 QA probe output (paths and exit trap)`, `SKL-241 QA suite, CI and repo state` and `SKL-241 QA probe source` on that story.
- Suites: the full suite `uv run --locked pytest -q` on the build (1626 passed), the new module alone (34 passed), and main CI run 42933584577 on `fd022dc` (success).

## Verdicts

| Item | Verdict | Evidence |
|---|---|---|
| AC1 the log | Verified | On both flows the log lists sweep, hunt and arbitrate in order, each sidecar phase as `<phase>: <bytes> bytes` with its `excluded` lines in sidecar order and each other phase as `<phase>: not run`. Each logged size equals its sidecar and `wc -c` of the dossier. The `total` line appears only once all three phases have sidecars and equals their sum (7461 on `run`, 7502 on `dossier`). A sweep re-run leaves `hunt: not run` and `arbitrate: not run` with no total. A `--no-sweep` hunt and arbitrate print `sweep: absent (--no-sweep)` while a sweep sidecar is still on disk, and the total sums only hunt and arbitrate (5339 and 5360). A `dossier` undone by its exit trap leaves the log rebuilt to `hunt: not run` over a stale log. A `run` missing `--agent-cmd` (exit 2) and a `dossier` refused by its predecessor check (exit 13) leave the log byte- and mtime-identical. A tampered log leaves the arbitrate binding and the sweep and hunt stamps byte-identical, and no binding or stamp names the log. A directory in the log's place gives exit 0, one `WARNING:` line, the normal completion line, an accepted record, the sidecar still written, no temporary file left, and the next phase starting from the accepted sweep. `paths` prints the six earlier lines byte-identical to the pre-PR script, then `dossier_sizes <absolute run dir>/dossier-sizes.md`. |
| AC2 report contract unchanged; existing suite passes unchanged; new tests cover the listed cases | Verified | PR #192 changed only the script and added `tests/test_pipeline_dossier_sizes.py`, so every existing test module is unchanged. The script diff has no hunk in `accept_phase`, `record`, the `REVIEW-RAN` check or the arbitration report layout. The full suite passes on the build. The new module covers each listed case on both flows where the AC names both, plus the `paths` line and the two refusals. |
| DoD all acceptance criteria met | Verified | AC1 and AC2 above. |
| DoD unit and integration tests written and passing | Verified | The new module and the full suite above, and main CI on the build. |
| DoD independently reviewed | Verified | PR #192 review of record at head `99bc462aeeb2778bf07df0988ea2dad2fa5218f7`, Codex GPT-6 Sol reviewer and DeepSeek V4 Pro adjudicator. |
| DoD docs updated | Verified | The script's usage line for `paths` and its header's "Size log" paragraph. |
| DoD verified in a deployed environment (if needed) | Verified, not needed | The repository deploys nothing; verified on merged `main`. |
| DoD no critical bugs or regressions | Verified | Suite and CI are green, the `paths` lines and report contract are unchanged, and the probes found no defect. |

Decision: Done once this evidence PR merges through its review of record and CI.
