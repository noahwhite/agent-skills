# SKL-389 QA evidence

- Round: 1, 2026-11-22.
- Path: `no-deployment`.
- Target: `2bc67d48ea0d13939da880766a3649e6fd601d30`, confirmed on fetched `origin/main`.
- Environment, deployed build and fixtures: not applicable; this repository deploys nothing.
- Implementation PR: https://github.com/noahwhite/agent-skills/pull/389.
- Implementation reviewed head: `1a7c39ed3a289445ad965b480aff9d63d8231724`.
- [Per-item structured assertions attached to the story](https://uploads.linear.app/7fbfc592-b1ef-432c-96af-87e5111c541e/5f29f681-04e0-4964-82b9-789c83b812f2/9226d278-a1ba-49d8-a292-52f1352d3b1d).
- [QA evidence comment](https://linear.app/officina-pub/issue/SKL-389/user-story-put-lite-mode-and-the-batched-poll-cadence-in-the-kickoff#comment-5b91d6ae).

## Verdicts

Each evidence label below names its record in the attached assertion output.

| Item | Verdict | Evidence |
|---|---|---|
| AC1 kickoff asset | Verified | AC1: exact caller line, one closed fence, coordinator run instruction, 5 lines and 77 words; batched 12-minute routine background polling, immediate handback handling, orchestration definition, default sentence and unchanged wait bounds/deadlines; only new skill file. |
| AC2 skill pointer | Verified | AC2: one linked default sentence at `skills/story-to-done/SKILL.md:108`, before all five step sections at lines 144, 171, 230, 266 and 330. |
| AC3 tests | Verified | AC3: 44 committed tests inspected; constant `CADENCE_MINUTES = 12`, caller, literals, fence shape, full block, pointer/link paths, placement and both ceilings pinned. |
| AC4 verification | Verified | AC4: implementation PR pastes exact asset and focused command/output, `408 passed in 6.78s`; only asset, skill and new test module changed. |
| AC5 guards | Verified | AC5: CI at reviewed head passes ruff, 3897 tests, private-required leak scan, skill validation and forced-install discovery in six layouts; the passing repository-vendoring test runs `vendor_shared.py --check`. |
| DoD1 all ACs met | Verified | DoD1: all AC1 to AC5 assertions true. |
| DoD2 tests written and passing | Verified | DoD2: AC3, focused execution record and CI suite success. |
| DoD3 independently reviewed | Verified | DoD3: [COMMENTED review of record](https://github.com/noahwhite/agent-skills/pull/389#pullrequestreview-6011619930) by the expected author; both marker and review commit equal the implementation PR head, both required seats completed, no unresolved valid finding. |
| DoD4 docs updated | Verified | DoD4: caller asset and discoverable skill pointer. |
| DoD5 deployed verification if needed | Correct by design, met | DoD5: not needed on fixed `no-deployment` path; profile has `environments: []`. |
| DoD6 no critical bugs/regressions | Verified | DoD6: artifact assertions, successful CI and exact-head independent review; no critical defect or regression observed. |

## Reproduction and provenance

Read target artifacts with `git show 2bc67d48ea0d13939da880766a3649e6fd601d30:<path>` for the two changed skill files and `tests/test_kickoff_prompt.py`.
Inspect scope with `git show --format= --name-status 2bc67d48ea0d13939da880766a3649e6fd601d30`.
Confirm containment after fetching main with `git merge-base --is-ancestor 2bc67d48ea0d13939da880766a3649e6fd601d30 origin/main`.
The caller line is outside the fence; the five block lines contain 77 whitespace-separated words.
The contract test module checks the complete block, not merely keyword presence.

The focused execution record is in the merged implementation PR body.
The [CI run](https://github.com/noahwhite/agent-skills/actions/runs/45008948214) is bound to implementation head `1a7c39ed3a289445ad965b480aff9d63d8231724`.
Read it with `gh run view 45008948214 --repo noahwhite/agent-skills --log`.
CI reports `3897 passed in 511.43s (0:08:31)`, `All checks passed!`, `Valid skill: skills/story-to-done`, and discovery of all 18 skills in each of six layouts with `OPENCODE_FORCE_INSTALL: 1`.
Its leak-scan step succeeded with `FORK_PR: false` and `--require-private`; no private pattern is copied into evidence.
`tests/test_resolve_model_role.py:876-881` runs the repository vendor check and asserts exit 0 with empty stdout, so the passing suite supplies the vendor-check evidence.
The reviewed head and target have identical trees, confirmed with `git diff --exit-code 1a7c39ed3a289445ad965b480aff9d63d8231724 2bc67d48ea0d13939da880766a3649e6fd601d30`.

QA used read-only artifact probes and historical execution evidence; it did not rerun or mutate the implementation suite.
Screenshots are not required on this no-deployment path; the attachment preserves the actual Markdown asset and pointer text.
The runtime has no hosted-evidence capability.
No incidental product defect, failed item or pending acceptance-basis ruling was observed.
This verifies the prompt contract, not runtime polling compliance or ACU savings.
The QA comment holds the closing state decision; this evidence records no story-body or criterion changes.
