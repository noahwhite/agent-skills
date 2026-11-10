# SKL-88 QA evidence

## Round 1, 2026-11-10

The repository deploys nothing (`environments: []`), so the environment under test is merged `main` of `noahwhite/agent-skills`, build `f2f5c2ad015927bf2592962c1f694a8f286c9247`.
That build is the squash commit of PR #178, whose reviewed head was `1acbeb8c0c6b48bab9abfcc764a9a9bf84de5a5c`; the two trees differ only by an unrelated SKL-87 evidence README.
Fixtures: throwaway two-commit git repositories (a base tag and one head commit), built by the QA probe in its scratch directory.
The main fixture changes 20 files: paths under `linguist-generated` and `linguist-vendored` attributes set, `true`, `false`, unset and unspecified, paths matched by an `.adversarial-exclude` list exercising each syntax rule, a listed and an unlisted test module, and plain files.
In that fixture the base commit and the working tree carry different `.gitattributes` and `.adversarial-exclude` contents than the head, with `git status` clean.
The probe drove `run-adversarial-pipeline.sh` through `preflight` and `run` for sweep, hunt and arbitrate with a stand-in agent that keeps the dossier it was handed.
A second probe ran the same chain with the pre-PR script (`f99235b`) and the merged script on identical fixtures and compared the dossiers after normalizing per-run paths and commit SHAs.
There is no visual surface, so structured assertions and their raw output are the evidence, without screenshots.

## Evidence

- Tracker evidence: SKL-88, QA comment `eb2e1a77`.
- Raw evidence: attachments titled `SKL-88 QA probe output (end-to-end gate runs on main)`, `SKL-88 QA report-contract comparison (pre-PR vs merged script)`, `SKL-88 QA suite, CI and repo state`, `SKL-88 QA probe source` and `SKL-88 QA contract comparison source` on that story.
- Suites: the full suite `uv run --locked pytest -q` on the build (1526 passed), the pipeline suites `test_pipeline_failfast.py`, `test_pipeline_scratch.py` and `test_pipeline_exclusion.py` (90 passed), and main CI run 42782472870 on `f2f5c2a` (success).

## Verdicts

| Item | Verdict | Evidence |
|---|---|---|
| AC1 exclusion by attribute or list arm, read from the head; excluded paths stay in the diffstat with a reason; sweep and hunt only; test modules not auto-excluded; no repository opts in; header documents both arms | Verified | In sweep and hunt the EXCLUDED rows equal the expected 9 paths with reasons `linguist-generated`, `linguist-vendored` or `glob:<pattern>`, the DIFF holds exactly the 11 kept paths, no excluded content reaches the DIFF, and all 20 paths stay in the diffstat. The arbitrate dossier has no DIFF or EXCLUDED section. Attribute values `set` and `true` excluded a path; `false`, `unset` and unspecified kept it. The head's attributes and list decided, not the base's or the working tree's. In the list, `*` and `?` matched `/`, a bare `*.snap` matched a nested path, a leading `./` and surrounding whitespace were stripped, comment and blank lines were skipped, `!` and inline comments matched nothing, and a last line without a newline counted. A missing list and a comment-only list excluded nothing without error. An unlisted test module stayed in the diff and a listed one was excluded. The header's "Exclusion:" paragraph documents both arms and the list's name, location and syntax. `main` carries no `.adversarial-exclude` and no linguist attribute, and PR #178 touched only the script and its new test file. |
| AC2 report contract unchanged; existing suites pass unchanged; new tests cover the four named cases | Verified | With no opt-in, the pre-PR and merged scripts produce identical normalized sweep, hunt and arbitrate dossiers. With an exclusion list the arbitrate dossier is identical and sweep and hunt differ only in the EXCLUDED section and the DIFF body. A `REVIEW-RAN: no` report still fails the phase with exit 17, and an accepted artifact's first line is `REVIEW-RAN: yes`. The squash has no hunk in `accept_phase`, `record` or the dossier instructions. `tests/test_pipeline_failfast.py` and `tests/test_pipeline_scratch.py` are untouched and pass. `tests/test_pipeline_exclusion.py` covers an attribute-excluded file, a `linguist-generated=false` file kept, a list-excluded file, and a kept and a list-excluded test module. |
| DoD all acceptance criteria met | Verified | AC1 and AC2 above. |
| DoD unit and integration tests written and passing | Verified | Full suite 1526 passed, and main CI is green on the build. |
| DoD independently reviewed | Verified | PR #178 review of record at head `1acbeb8c0c6b48bab9abfcc764a9a9bf84de5a5c`, Codex GPT-6 Sol reviewer and DeepSeek V4 Pro adjudicator; one Medium finding fixed, then no findings. |
| DoD docs updated | Verified | The script header's "Exclusion:" paragraph. |
| DoD verified in a deployed environment (if needed) | Verified, not needed | The repository deploys nothing; verified on merged `main`. |
| DoD no critical bugs or regressions | Verified | Suite and CI are green, the dossier contract is unchanged, and the probes found no defect. |

The `dossier-sizes.md` naming line is SKL-89's scope per the story's dated AC note.
No incidental defect was observed.
Decision: Done once this evidence PR merges through its review of record and CI.
