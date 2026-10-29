# SKL-86 QA evidence

## Round 1, 2026-10-29

The repository deploys nothing (`environments: []`), so the environment under test is merged `main` of `noahwhite/agent-skills`, build `db6d1a913ea1df5e37f1c4fdb84dce27e4786ae0`.
That build contains PR #97, squash commit `58e867f3d940c19b65d17ec23bf5dc1139778f89`.
Fixtures: fresh two-commit git repositories (a `base` tag and one head commit changing two files), one per flow, built by the QA probe in its scratch directory.
The probe drove `run-adversarial-pipeline.sh` through `preflight`, `run`, `dossier`, `record` and `cleanup` with a fake agent that snapshots the dossier it was handed and the state of its checkout.
There is no visual surface, so structured assertions and their raw output are the evidence, without screenshots.

## Evidence

- Tracker evidence: SKL-86, QA comment `bf4605c4`.
- Raw evidence: attachment titled `SKL-86 QA round 1 - raw assertion output` on that story.
- Flows exercised: `run` for sweep, hunt and arbitrate; `run --no-sweep` for hunt and arbitrate; `dossier`, `record` and `cleanup` for each phase.
- Fault injection: a `git` wrapper on `PATH` refused the embedded diff during `run sweep` and the diffstat during `dossier arbitrate`, after each phase's checkout existed.
- Suites: `uv run --locked pytest -q tests/test_pipeline_failfast.py tests/test_pipeline_scratch.py` (67 passed), `tests/test_pipeline_dossier_checkout.py` (17 passed), and the full suite (807 passed).

## Verdicts

| Item | Verdict | Evidence |
|---|---|---|
| AC1 arbitrate dossier carries no unified diff and names its checkout; checkout lifecycle on both flows; preamble | Verified | On both flows the arbitrate dossier has no `===== DIFF` section and no `diff --git` line, and carries the story, the diffstat, both phase reports, `BASE:`, `HEAD:` and one `CHECKOUT:` line. `--no-sweep` keeps `(sweep not configured)`. The checkout existed at delivery, detached at the reviewed head, and was the agent's working directory. `dossier` printed the same `CHECKOUT:` path on stderr, and `cleanup` removed it after `record`. Both injected dossier-write failures exited 3 and left no extra worktree, no registry entry and no partial dossier, and `record` refused the failed phase (exit 15). The preamble offers the diffstat and a read-only checkout, and makes `REVIEW-RAN: yes` conditional on the diffstat, both phase results and the `CHECKOUT:` line. |
| AC2 phase payloads; `CHECKOUT:` and `BASE:` in every dossier on both flows | Verified, one clause out of scope | Sweep and hunt still embed the diff, hunt adds the sweep's candidates, and arbitrate carries the story, diffstat and both reports. All six dossiers carry one first `CHECKOUT: <absolute path>` and `BASE: base <base SHA>`. The sweep prompt makes its checkout read-only, the hunt may edit its own, and the arbiter must not edit its own. The filtered, `--unified=1`, capped diff is owned by SKL-87 (cap) and SKL-88 (filter), per the story's split. |
| AC3 report contract unchanged; existing suite unchanged and passing; new tests; `SKILL.md` rewords | Verified | The arbitration report layout is byte-identical to the pre-PR script, and `accept_phase`, `binding_text` and the `record` command are unchanged. The two existing test files are untouched and pass. The new test module covers every named topic and passes. `SKILL.md` no longer claims a whole-diff dossier, and the subagent flow and the 128 KiB argv rule are reworded. |
| DoD all acceptance criteria met | Verified | AC1 to AC3 above. |
| DoD unit and integration tests written and passing | Verified | Full suite 807 passed. |
| DoD independently reviewed | Verified | PR #97 review of record at the merged head `89e25f1b60c815026557615461c03f3c1463da88`, Codex GPT-6 Sol reviewer and DeepSeek V4 Pro adjudicator, clean. |
| DoD docs updated | Verified | Script header and `SKILL.md` reworded. |
| DoD verified in a deployed environment (if needed) | Verified, not needed | The repository deploys nothing; verified on merged `main`. |
| DoD no critical bugs or regressions | Verified | Main CI on `58e867f` and checks on `db6d1a9` are green, and the full suite passes. |

No incidental defect was observed.
Decision: Done once this evidence PR merges through its review of record and CI.
