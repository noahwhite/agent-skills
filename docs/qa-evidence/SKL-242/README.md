# SKL-242 QA evidence

## Round 1, 2026-11-11

The repository deploys nothing (`environments: []`), so the environment under test is merged `main` of `noahwhite/agent-skills`, build `fdf8a9276b71065e42fb41701833e6f9b27442aa`.
That build is the squash commit of PR #198, whose reviewed head was `413c43a8a588fe9ada6735934e3ef20e23f91eac`; the two trees are identical.
Blockers SKL-241 and SKL-89 are Done.
Fixture: the committed `tests/fixtures/dossier_size/` inputs, built by the build's own `dossier_fixture.py` into throwaway repositories in the QA scratch directory.
A QA probe outside the repository rebuilt the fixture twice through the build's script, once in a normal environment and once with a hostile `HOME` and `XDG_CONFIG_HOME` git config and attributes file, `COLUMNS=200` and an `ADVERSARIAL_MODEL` value, and printed each measured value.
The baseline capture helper was rerun from a second detached worktree of the build, against a local `21f0265`.
The AC 7 amendment of 2026-11-11 (owner decision comment `1a0e0321`) is the acceptance basis for the `tests/test_skills.py` change.
There is no visual surface, so structured assertions and their raw output are the evidence, without screenshots.

## Evidence

- Tracker evidence: SKL-242, QA comment `ed9abbba`.
- Raw evidence: attachments titled `SKL-242 QA probe output (fixture, normalization, ceiling)`, `SKL-242 QA probe source` and `SKL-242 QA suite, CI, capture and repo state` on that story.
- Suites: the full suite `uv run --locked pytest -q` on the build (1647 passed; CI collects more because one module parametrizes over the awk binaries on `PATH`), the new module with `test_the_arbitration_report_layout_is_unchanged` and `test_house_spelling_is_artifact_everywhere_tracked` (18 passed), and main CI run 42949261778 on `fdf8a92` (success: 1665 passed, leak scan with private patterns, 18 skills valid).

## Verdicts

| Item | Verdict | Evidence |
|---|---|---|
| AC1 fixture inputs | Verified | The fixture directory holds eight ASCII, LF-only files and none matches `test_*.py` or `*_test.py`. `spec.txt`, `source-base.txt` and `source-head.txt` start with `SYNTHETIC FIXTURE - SKL-242 - not real data`; both phase reports start with `REVIEW-RAN: yes` and carry the marker on line 2. The test defines `MARKER` once, asserts the fixture module's copy equals it, and checks every text input. `.gitattributes` gains `tests/fixtures/dossier_size/** -text`, and `git check-attr text` reports `unset` for the fixture files. `scripts/leak_scan.py` passes locally (public patterns) and in main CI (private patterns). |
| AC2 deterministic fixture repository | Verified | Every git and script call runs under `fixed_env`: `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`, no user attributes file, fixed author, committer and date, `COLUMNS=80`, and `core.autocrlf=false` in the repository. The probe got two distinct commits, `78d1d146` (tag `base`) and `245b05aa`, equal to the pinned pair, and a `base...HEAD` diff of 25 files and 114,450 bytes. The hostile-environment run produced the same commits, a byte-identical diff and a byte-identical normalized dossier from a different temporary root. Spec 2,759, Phase 1 10,869 and Phase 2 7,797 bytes are inside their ranges, and every fixture file size, the baseline size and SHA-256, and the diff file count and bytes are pinned in the test. |
| AC3 accepted predecessors through the script | Verified | `arbitrate_dossier` runs `preflight --repo <tmp> --base base --test-cmd true`, `dossier sweep`, writes the Phase 1 report to the artifact path `paths` names, `record sweep`, then the same for hunt, then `dossier arbitrate`. No code path writes a `.stamp` file; the probe found the three stamps the script wrote, and the accepted sweep and hunt artifacts byte-equal the committed reports. |
| AC4 pinned baseline and its capture | Verified | `capture_baseline.py` rerun from a fresh worktree of the build regenerated `baseline-arbitrate.txt` at 139,645 bytes with SHA-256 `40a98db7...2b25`, leaving `git status` clean and its temporary `21f0265` worktree removed. The test module docstring names the helper; neither the tests nor `ci.yml` run it. |
| AC5 normalization | Verified | `normalize` replaces, in its documented order, the checkout path, the run directory, the temporary root and each fixture commit ID with constant placeholders, the commit placeholder 40 characters wide. On the probe run it was idempotent on both the current dossier and the baseline, left no temporary path and no 40-hex ID in either, and left the spec, both reports and the diff byte-unchanged. |
| AC6 ceiling | Verified | The normalized current arbitrate dossier is 25,762 bytes by `len` and by `LC_ALL=C wc -c`, against a ceiling of `floor(0.40 x 139645)` = 55,858 (ratio 0.1845). All 75 `HUNK-ONLY-MARKER` lines occur only on `+` lines of the diff and in the baseline, and none occurs in the current dossier. The baseline is the 21f0265 script's dossier on this fixture, so a regression to that output fails the ceiling. |
| AC7 standing constraint | Verified | PR #198 touches no file under `skills/`. Its only change to an existing module is the `SPELLING_EXEMPT` entry `tests/fixtures/dossier_size/baseline-arbitrate.txt` with a why note, which the amended AC allows; line 8 of the baseline carries the 21f0265 spelling. `test_the_arbitration_report_layout_is_unchanged` and `test_house_spelling_is_artifact_everywhere_tracked` pass, and the full suite passes. The new tests live in `tests/test_pipeline_dossier_fixture.py` (16 tests) and cover the marker, file sizes, baseline and diff sizes, normalization, ceiling and marker lines. |
| DoD all acceptance criteria met | Verified | AC1 to AC7 above. |
| DoD unit and integration tests written and passing | Verified | The new module and the full suite above, and main CI on the build. |
| DoD independently reviewed | Verified | PR #198 review of record at head `413c43a8a588fe9ada6735934e3ef20e23f91eac`, Codex GPT-6 Sol reviewer and DeepSeek V4 Pro adjudicator, merged with that head as the expected head. |
| DoD docs updated | Verified | The test module docstring and the helper's docstring document the baseline capture procedure; no user-facing doc changes. |
| DoD verified in a deployed environment (if needed) | Verified, not needed | The repository deploys nothing; verified on merged `main`. |
| DoD no critical bugs or regressions | Verified | Suite and CI are green and the probes found no defect. |

Decision: Done once this evidence PR merges through its review of record and CI.
