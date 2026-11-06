# SKL-50 QA evidence

Date: 2026-11-06 UTC, independent QA round 1.
Story: SKL-50 - story-to-done never lets the engineer arbitrate the pre-PR gate (core slice: AC1 to AC5 after the split).
Build under test: `cb60fdfaee350f249d6afcf671c4b6fdafa7ef20`, the squash merge of PR 142, whose reviewed head was `646f460c9cacc823f398f0a21affd02ff589d400`.
Environment: a detached checkout of `origin/main` at the build SHA.
The profile lists no environments and this repository deploys nothing, so `main` at the merge commit and the exact-build CI run are the deployed-build equivalent.
CI: run 42296188432 on the reviewed head and run 42296810716 on the build SHA, both successful.

Fixtures: none; the probes are read-only text assertions over `skills/story-to-done/SKILL.md`, the anchors it cites in `adversarial-review-pipeline` and `engineering-workflow`, the arbitrate dossier emitter in `run-adversarial-pipeline.sh`, and the test suite.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The assertion file `SKL-50-qa-assertions.txt` is attached to SKL-50.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: the engineer never arbitrates | Verified | The step 2 rule names `adversarial-review-pipeline` Phase 3 and the `engineering-workflow` step 4 Verify stage, forbids ruling a finding valid, invalid or accepted risk or the gate converged, and states that applying the gate's scope guard is not arbitration. All three anchors exist at the build. |
| AC2: a separate clean, neutral, independent arbiter | Verified | The rule requires "a separate clean, neutral arbiter on `profile.review.pre_pr.arbiter`, independent of engineer and coordinator" and restates no definition. The vendored Clean and Neutral bullets carry the fresh-context and input limits. The arbitrate dossier emits only the role, criteria and constraints, the base and head SHAs, the checkout, the story and AC, the diffstat, and the Phase 1 and Phase 2 reports. |
| AC3: one sentence, briefed verbatim after the merge-rules bullet | Verified | The rule occurs exactly twice, at line 107 as prose and line 100 as a brief bullet, byte-identical and one sentence. The bullet directly follows "The merge rules:". `test_clean_and_neutral_use_the_canonical_phrase` passes. |
| AC4: QA and adjudicator rulings are fixed, not overturned | Verified | The rule says the engineer "fixes what QA ruled not met or the adjudicator ruled valid without overturning those rulings" and the separate arbiter "arbitrates every head". The step 4 fix hand-back reuses the step 2 brief. The step 4 dispute line covers "a failed verdict or an adjudicator's ruling" and puts it to the user. |
| AC5: no launchable arbiter hands back blocked | Verified | The hand-back bullet reads "blocked and why, including when no arbiter can launch; a missing arbitration is never clean or converged". The shell-launched list is `command`, `codex` or `opencode`, as the pipeline names them. |
| DoD1: all acceptance criteria met | Verified | AC1 to AC5 above. |
| DoD2: tests written and passing | Verified | Five new contract tests in `tests/test_story_to_done.py`. `uv run pytest -q` reports 1087 passed at the build, and both CI runs are green. |
| DoD3: independently reviewed | Verified | PR review 5807230501 is the review of record at `646f460c9cacc823f398f0a21affd02ff589d400`, the merged head, by the profile's reviewer and adjudicator, posted before the merge. |
| DoD4: docs updated | Verified | The deliverable is the skill prose itself. |
| DoD5: verified in a deployed environment, if needed | Not applicable, correct by design | The profile lists no environments. |
| DoD6: no critical bugs or regressions | Verified in tested scope | The full suite and CI are green, and the prose compressions in the diff drop no rule. |

Incidental, non-blocking: the rule's "arbitrates every head" is stricter than the pipeline's Phase 4, whose re-verify after fixes is conditional.
The PR 142 review of record raised it and its adjudicator ruled it invalid; cross-skill wording alignment sits with SKL-179.

Closing decision: every AC and DoD item is verified, so the story moves to Done once this evidence PR merges.
