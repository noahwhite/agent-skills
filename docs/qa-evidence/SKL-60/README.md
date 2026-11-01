# SKL-60 QA evidence

**Current scope:** Round 3 below verifies the numeric-only AC1 amendment.
It supersedes the historical t-shirt verdicts in rounds 1 and 2.
The current closing decision is In Deployment Review pending the correction's independent-review evidence, not the historical Done decisions below.

## Round 1

- Date: 2026-11-01.
- Story: SKL-60.
- Build: `5f3e33a7f361cfc3c7f5fa12905a8e609fef7089`, freshly fetched merged `main`.
- Implementation: https://github.com/noahwhite/agent-skills/pull/126.
- Environment: isolated checkout of the merged repository artifacts.
  The repository profile declares `environments: []`, so no deployed service exists or is required.
- Method: read-only assertions on the delivered instructions, templates and contract-test structure, plus authoritative merged-main CI.
  No implementation changes, local suite rerun, live ceremony, deployment or account mutations were performed.
- Fixtures: the four committed scale sequences, accepted-set and abstention examples, the SKL-13 `8/8/8` static fixture and the pointing-record template.
- Raw evidence: six sanitized text attachments on SKL-60, QA comment `c917b24c`.
  No screenshot is applicable to this CLI/instruction-artifact surface.

## Verdicts

The verdicts below verify the delivered repository instruction contract, not measured execution by a live facilitator.

| Item | Verdict | Evidence attached to the story |
| --- | --- | --- |
| AC1: consensus check | Verified: fixed sequences and tolerance; check first; identical/adjacent maximum skips discussion/re-vote; wider spread names high/low; split/tshirt handling; record and named guards | `ac1-assertions.txt`; `SKILL.md:179-187,253-268`; `refinement-record.md:75-82` |
| AC2: residual variance | Verified: accepted-set maximum, standing Step 3 fallback, identical/adjacent tolerance, split, distinct wide-spread needs-input stop, later owner decision, removed paths and record fields | `ac2-assertions.txt`; `SKILL.md:211-228,284-289`; `refinement-record.md:78-85` |
| AC3: basis challenge survives skip | Verified: every rationale reviewed before any estimate write or record post, restate/retract, fresh challenge contexts and void/re-run; both skip guards and SKL-13 split fixture present | `ac3-assertions.txt`; `SKILL.md:184,188-200,243-250`; `tests/test_story_refinement.py:1054-1126` |
| DoD: all AC met | Verified in the repository-artifact scope above | Per-AC attachments; `dod-assertions.txt` |
| DoD: unit/integration tests written and passing | Verified: committed contract tests; merged-main CI reports 951 passed in 118.50s | `ci-assertions.txt`; `dod-assertions.txt`; [CI run](https://github.com/noahwhite/agent-skills/actions/runs/41308383401) |
| DoD: independently reviewed | Verified: COMMENTED review's commit and first-line SHA both equal merged implementation head `1a1a7ddf26b31cd05ce9af70819d8aa7fdd86d1e` | `dod-assertions.txt`; [implementation review](https://github.com/noahwhite/agent-skills/pull/126#pullrequestreview-5728133744) |
| DoD: docs updated | Verified: skill, pointing template and shared/vendored references document the new rules in place | `dod-assertions.txt`; implementation PR diff |
| DoD: deployed verification if needed | Correct by design: no deployment is needed; the merged-main artifact is the named environment | `environment-assertions.txt`; `dod-assertions.txt`; `.agent-skills/profile.yaml:92-95` |
| DoD: no critical bugs/regressions | Verified within exercised scope: none observed, all per-AC instruction assertions pass, merged-main checks/discovery green | `dod-assertions.txt`; `ci-assertions.txt`; CI run |

## Limits and non-blocking observations

The static tests pin the instruction contract and do not execute challenge/recovery side effects.
An initial executable-handler expectation was rejected as inapplicable because this repository delivers instructions, not such a handler.
The SKL-13 rationale mixes a duration with a point-value prescription rather than isolating restate/retract; the delivered instructions correctly distinguish immediate anchoring from challengeable grounds.
The SKL-60 maintainer owns optional fixture clarification; no runtime failure was established.
The earlier implementation note/review says 933 tests, whereas authoritative merged-main CI reports 951; this record uses the actual CI result.
The implementation-note author owns any historical-note correction.
No critical defect was discovered; this is not proof of universal defect absence or live ceremony behavior.
The live counterfactual measurement remains with SKL-173, currently Backlog, and is not an incoming blocker of SKL-60.
The outgoing rollout, voter-set, effort-basis and re-point stories retain their own scope and are not claimed complete here.

## Round 2 (independent re-verification, 2026-11-01)

- Story: SKL-60, already Done.
- Build: `8787db08af1674ad8801866e44cf62e848920868`, freshly fetched merged `main`.
  The implementation commit `5f3e33a7f361cfc3c7f5fa12905a8e609fef7089` is an ancestor of this head, and the evidence-only commit `8787db0` adds `docs/qa-evidence/SKL-60/README.md`.
- Environment: the merged `main` tree is the named environment.
  The repository profile declares `environments: []`, so nothing deploys and no live ceremony is executed.
- Method: fresh independent read of the merged instructions, templates, tests and CI, in a throwaway worktree.
  The shared `/workspace/agent-skills` checkout and the implementation were not modified.
- Local suite: `uv run pytest -q` reports 933 passed (0 failed) at this head; `uv run --locked pytest -q` reports the same.
- Authoritative merged-main CI: `checks` and `discovery` both green at `8787db0`, with the `checks` job reporting 951 passed in 116.48s.
- Fixtures: the four committed scale sequences, the accepted-set and abstention examples, the SKL-13 `8/8/8` fixture and the pointing-record template.
- No visual surface exists, so no screenshot applies.

| Item | Verdict | Evidence |
| --- | --- | --- |
| AC1 consensus check | Verified as delivered instruction contract: fixed per-scale sequences, one-step tolerance fixed in-skill, identical/adjacent maximum skips discussion and re-vote, wider spread names high/low, tshirt larger size with cap stop, and the `Consensus check:` record line. | `ac1-assertions.txt`; `SKILL.md:179-187`; `refinement-record.md:75` |
| AC2 residual variance | Verified as delivered instruction contract: highest accepted-set value per voter with the Step 3 fallback, identical/adjacent derived values record the highest with the split rule, wider spread stops unpointed with a `needs input` to the owner distinct from the denied-write `needs input`, and the path vote, group-decided trigger, core-slice re-point sentence and re-refine accept round are removed. | `ac2-assertions.txt`; `SKILL.md:211-222`; `refinement-record.md:80-85` |
| AC3 skipped discussion keeps the basis challenge | Verified as delivered instruction contract: the basis review is its own Step 4 item after the consensus check and before any estimate write or record post, so the skip branch cannot skip it; restate-or-retract, fresh challenge contexts, and void/re-run are named; both skip-branch guards and the SKL-13 split fixture are present. | `ac3-assertions.txt`; `SKILL.md:188-200`; `tests/test_story_refinement.py:1054-1126` |
| DoD: all AC met | Verified within the repository-artifact scope above. | Per-AC files; `dod-assertions.txt` |
| DoD: unit/integration tests written and passing | Verified: committed contract tests; merged-main CI green (checks and discovery); independent local run green. | `ci-assertions.txt`; `dod-assertions.txt`; local run `933 passed`; CI run `951 passed` |
| DoD: independently reviewed | Verified: PR 126 review of record is `COMMENTED` at `1a1a7ddf26b31cd05ce9af70819d8aa7fdd86d1e`, whose first line names the same full SHA, and PR 126 merged to `5f3e33a`. | `dod-assertions.txt`; implementation review on PR 126 |
| DoD: docs updated | Verified: skill, pointing template, metrics and shared/vendored references document the new rules in place. | `dod-assertions.txt`; implementation PR 126 diff |
| DoD: verified in a deployed environment (if needed) | Correct by design: no deployment exists or is required. | `environment-assertions.txt`; `.agent-skills/profile.yaml` `environments: []` |
| DoD: no critical bugs/regressions | Verified within exercised scope: none observed, per-AC assertions hold, merged-main CI green. | `dod-assertions.txt`; `ci-assertions.txt` |

### Round 2 observations

- The local suite reports 933 passed while merged-main CI reports 951 passed.
  The checkout, command, lockfile and Python 3.12.3 are identical between the two runs, so the 18-test delta is unexplained from the repository side; both runs are fully green with 0 failures, and no AC or DoD verdict depends on the delta.
  Round 1 recorded the CI figure (951) as authoritative; this round keeps that.
- Round 1 attributed the 933 figure to a stale implementation note; this round reproduces 933 on a fresh independent run, so 933 is the local runner's count, not a stale note.
- The `skills-ref validate` command is not installed in this container, so the CI `Validate skills` step is the record for that check; it is green.
- No required SKL-60 item remains outstanding; the story stays Done.
- Live counterfactual ceremony measurement remains with SKL-173, not a blocker of SKL-60.

## Round 3 (numeric-only amendment, 2026-11-01)

- Build: `9cf409d4c53257c443f053e03ecf822685aad5f1`, freshly cloned `origin/main`, including https://github.com/noahwhite/agent-skills/pull/129.
- Environment: isolated merged-main repository tree.
  The authoritative `.agent-skills/profile.yaml` declares `environments: []`; nothing deploys.
- Method: read-only assertions on the merged instructions, schema, templates and contract-test structure, plus merged-main CI.
  These verdicts verify delivered instruction contracts, not execution by a live facilitator.
  No implementation changes, local suite rerun, live ceremony or shared-checkout edits were performed.
- Fixtures: three numeric scale sequences, accepted-set and abstention examples, SKL-13's `8/8/8` static fixture and the pointing-record template.
- Raw evidence: seven `round3-*-assertions.txt` attachments on SKL-60, QA comment `eba51909`.
  No visual surface exists, so no screenshot or hosted page applies.
- Test record: [merged-main CI](https://github.com/noahwhite/agent-skills/actions/runs/41330551926), checks and discovery successful, **957 passed in 118.87s**.
  The profile test command is `uv run pytest`; CI runs `uv run --locked pytest -q`.

| Item | Verdict | Evidence attached to SKL-60 |
| --- | --- | --- |
| AC1: numeric-only consensus | Verified: schema has exactly fibonacci/linear/exponential; fixed sequences and one-step check; skip/wide branches and split preserved; removed t-shirt rules absent; epic size_labels unchanged from parent schema. | `round3-ac1-assertions.txt`; `SKILL.md:146-184,250-264`; `profile/schema.json:176-182` |
| AC2: residual variance | Verified: accepted-set maximum or standing Step 3 fallback; identical/adjacent maximum with split; wide-gap owner needs-input stop distinct from denied writes; old path vote removed. | `round3-ac2-assertions.txt`; `SKILL.md:201-225`; `refinement-record.md:70-88` |
| AC3: basis challenge survives skip | Verified: every rationale reviewed before writes; clean bounded challenge contexts; restate/retract, recomputation and unresolved void; both skip guards and SKL-13 split fixture present. | `round3-ac3-assertions.txt`; `SKILL.md:185-200,240-247`; `tests/test_story_refinement.py:1130-1181` |
| DoD1: all AC met | Verified within the instruction-artifact scope above. | Per-AC attachments; `round3-dod-assertions.txt` |
| DoD2: tests written and passing | Verified: committed contract guards inspected; merged-main CI checks/discovery green, 957 tests passed. | `round3-ci-assertions.txt`; `round3-dod-assertions.txt` |
| DoD3: independently reviewed | Not covered for the correction: owner approval exists at final head `b9ff9fede3a4407ec130d3313f6627b3ef11cd6e`, but no configured reviewer/adjudicator review of record is posted there. | `round3-review-assertions.txt`; [correction approval](https://github.com/noahwhite/agent-skills/pull/129#pullrequestreview-5729304800) |
| DoD4: docs updated | Verified: skill, schema, template and shared rules updated; all 20 vendored linear/metrics references match sources. | `round3-dod-assertions.txt`; correction diff |
| DoD5: deployed verification if needed | Correct by design: no deployment exists or is needed; merged main is the named environment. | `round3-environment-assertions.txt` |
| DoD6: no critical bugs/regressions | Verified within exercised scope: none observed; static assertions and merged-main CI green, not proof of universal absence or live execution. | Per-AC attachments; `round3-ci-assertions.txt`; `round3-dod-assertions.txt` |

### Round 3 closing decision and limits

Retain **In Deployment Review**: QA remains in flight pending the SKL-60 maintainer/PR129 owner's independent-review record or explicit policy disposition for DoD3.
The original [implementation review](https://github.com/noahwhite/agent-skills/pull/126#pullrequestreview-5728133744) covers `1a1a7ddf26b31cd05ce9af70819d8aa7fdd86d1e`, not the correction delta.
The correction PR body records arbitration unavailable and an owner hand review; an approval alone is not treated as an inferred review-policy waiver.
No acceptance criterion failed, and no implementation fix or new bug is requested by this pass.
The SKL-13 fixture mixes a duration with a value prescription rather than isolating the restatable duration-only path; the maintainer owns optional fixture clarification, with no functional defect established.
Rejecting consumer profiles that still set `estimate_scale: tshirt` is the amendment's intentional contract change, not an incidental regression.
Live counterfactual measurement remains owned by SKL-173 (Backlog), not an incoming blocker of SKL-60.
Downstream voter-set, effort-basis, rollout and re-point stories retain their own scope.
