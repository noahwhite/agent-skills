# SKL-410 QA evidence

## Round 1

- Story: SKL-410.
- Path: `no-deployment`.
- Target: [`6a3e21140b83b50a190f5658ef41670548ed405e`](https://github.com/noahwhite/agent-skills/commit/6a3e21140b83b50a190f5658ef41670548ed405e), confirmed on `origin/main`.
- Implementation: [PR #400](https://github.com/noahwhite/agent-skills/pull/400), reviewed at `ee35eecf18ddbf4cf6484bcfcfc39e188b348285`.
- Raw commands and output: `SKL-410-qa-round-1.txt`, attached to the story.

| Item | Verdict | Evidence |
| --- | --- | --- |
| AC1 - Scope and source | Verified | [`SKILL.md:110-118, 134`](https://github.com/noahwhite/agent-skills/blob/6a3e21140b83b50a190f5658ef41670548ed405e/skills/story-to-done/SKILL.md#L110-L135) scopes each boundary to the receiving role, excludes coordinator-persona rules, and requires verbatim `path:line` citations before dispatch. |
| AC2 - Prohibitions | Verified | [`SKILL.md:119-121`](https://github.com/noahwhite/agent-skills/blob/6a3e21140b83b50a190f5658ef41670548ed405e/skills/story-to-done/SKILL.md#L119-L121) distinguishes the examples and names the actor and source on the same Linear reference line. |
| AC3 - Permissions | Pending owner ruling | [`SKILL.md:122-128, 134`](https://github.com/noahwhite/agent-skills/blob/6a3e21140b83b50a190f5658ef41670548ed405e/skills/story-to-done/SKILL.md#L122-L134) specifies and quotes the permissions, but the raw engineer and QA render outputs each had zero matches for the quoted permissions. |
| AC4 - Ownership | Verified | [`SKILL.md:129-130`](https://github.com/noahwhite/agent-skills/blob/6a3e21140b83b50a190f5658ef41670548ed405e/skills/story-to-done/SKILL.md#L129-L130) delegates the completion tick without removing the permission or changing product-owner authority. |
| AC5 - Conflict | Verified | [`SKILL.md:131-132`](https://github.com/noahwhite/agent-skills/blob/6a3e21140b83b50a190f5658ef41670548ed405e/skills/story-to-done/SKILL.md#L131-L132) requires reporting, stopping, and escalating to the owner without silent resolution. |
| AC6 - Test pins | Verified | [`tests/test_brief_authoring.py`](https://github.com/noahwhite/agent-skills/blob/6a3e21140b83b50a190f5658ef41670548ed405e/tests/test_brief_authoring.py) asserts literal AC1-AC5 wording and the QA tick sentence, and 385 focused tests passed. |
| AC7 - Guards | Verified | At the merge target, local Ruff, vendoring, both skill validators, and discovery passed; the exact-target [CI run](https://github.com/noahwhite/agent-skills/actions/runs/45067503350) passed repository tests and the required public and private leak scan. |
| DoD1 - Acceptance criteria | Pending owner ruling | All criteria except AC3 are verified; the product owner's ruling on AC3 also resolves the acceptance basis for this item. |
| DoD2 - Tests written and passing | Verified | [PR #400](https://github.com/noahwhite/agent-skills/pull/400) records 3900 local tests passed and [PR-head CI](https://github.com/noahwhite/agent-skills/actions/runs/45066284339/job/137343041899) confirms the second signal at that head. |
| DoD3 - Independent review | Verified | The [final review of record](https://github.com/noahwhite/agent-skills/pull/400#pullrequestreview-6014412030) records the independent reviewer and adjudicator and matches the implementation PR head in both SHA fields. |
| DoD4 - Docs updated | Verified | The merged `story-to-done` skill documents the rules in its new Brief authoring section. |
| DoD5 - Deployed verification | Correct by design | Not needed on the `no-deployment` path. |
| DoD6 - No critical bugs or regressions | Verified | The independent review found no remaining Critical or High defects, and focused tests and exact-target CI passed. |

The product owner owns the AC3 ruling: if AC3 applies to the final brief that the coordinator prepares before dispatch, the committed rule and exact quotes satisfy it.
If AC3 requires the unedited renderer output itself to carry the permissions, the render check fails that reading.
DoD1 remains pending for the same reason.

## Round 2

- Path: `no-deployment`.
- Target: [`ddda852e4c73ff2051694810d577f8fa30cd8d4c`](https://github.com/noahwhite/agent-skills/commit/ddda852e4c73ff2051694810d577f8fa30cd8d4c), confirmed on `origin/main`.
- Implementation: [PR #403](https://github.com/noahwhite/agent-skills/pull/403), reviewed at `1261d47023976fd0b76aefc37a187399629e32fb`.
- Acceptance basis: the product owner's 2026-11-22 ruling requires verbatim permission quotations in the unedited role briefs.
- Raw commands and output: `SKL-410-qa-round-2-source.txt` and `SKL-410-qa-round-2-render.txt`, attached to the story.

| Item | Verdict | Evidence |
| --- | --- | --- |
| AC1 - Scope and source | Verified | The [landed skill](https://github.com/noahwhite/agent-skills/blob/ddda852e4c73ff2051694810d577f8fa30cd8d4c/skills/story-to-done/SKILL.md#L110-L134) scopes constraints to the recipient, excludes coordinator-persona rules, and requires verbatim `path:line` citations. |
| AC2 - Prohibitions | Verified | Lines 119-121 require the actor and source, distinguish the two prohibitions, and give the actual actor and wording from the cited line. |
| AC3 - Permissions | Verified under reading 2 | Seven raw briefs from `render-brief.py` carried 44 source-exact citations for verified ticks, assigned state moves, the role's PR, and posting the review of record. The two no-deployment briefs carried six engineer and seven QA citations, with no coordinator edits. |
| AC4 - Ownership | Verified | Lines 129-130 delegate the completion tick without transferring the product owner's authority or removing the observing agent's permission. |
| AC5 - Conflict | Verified | Lines 131-132 require the role to report and stop, and the coordinator to escalate to the owner without silently resolving the conflict. |
| AC6 - Test pins | Verified | `tests/test_brief_authoring.py` pins the literal criterion wording and QA tick sentence. The authoring and renderer modules passed all 128 focused tests. |
| AC7 - Guards | Verified | Local Ruff, vendoring and both skill validators passed. The [CI run](https://github.com/noahwhite/agent-skills/actions/runs/45093106615) passed 4,002 tests, the private leak scan and OpenCode discovery on the same tree as the merged target. |
| DoD1 - Acceptance criteria | Verified under reading 2 | All seven criteria are met, including physical permission citations in the raw briefs. |
| DoD2 - Tests written and passing | Required CI signal not covered | The implementation PR records 3,960 local passes at the reviewed head. For its CI run, checkout selected synthetic merge `26b41cb386680f6c51d66150853977931103a3ff`, whose tree `cf4e3de0707640cca8dc18793dc76fee6918212f` matches the landed commit but not the reviewed head's tree `eae7a6c9e991d380daae03cad397519d6799c917`. No equivalent-head Repository tests run was found. |
| DoD3 - Independent review | Verified | The [final review of record](https://github.com/noahwhite/agent-skills/pull/403#pullrequestreview-6015692087) is a PR comment review with both SHA fields matching the reviewed head. |
| DoD4 - Docs updated | Verified | The merged `story-to-done` skill contains the Brief authoring section. |
| DoD5 - Deployed verification | Correct by design | Not needed on `no-deployment`. |
| DoD6 - No critical bugs or regressions | Verified in scope | No critical issue surfaced in the raw renders, focused tests, same-tree CI, or independent review. |

Engineering owns the missing DoD2 CI evidence.
The pre-existing engineer intro says “the deploy” even on `no-deployment`; this does not change the quoted path-specific handoff and is not a completion blocker.

## Round 3

- Path: `no-deployment`.
- Target: [`ddda852e4c73ff2051694810d577f8fa30cd8d4c`](https://github.com/noahwhite/agent-skills/commit/ddda852e4c73ff2051694810d577f8fa30cd8d4c), confirmed on `origin/main`; only evidence changed after the target.
- Implementation: [PR #403](https://github.com/noahwhite/agent-skills/pull/403), reviewed at `1261d47023976fd0b76aefc37a187399629e32fb`.
- Acceptance basis: unchanged criteria and the product owner's 2026-11-22 AC3 reading 2, which requires the permission quotations in the unedited briefs.
- Raw commands and output: `SKL-410-qa-round-3-source.txt` and `SKL-410-qa-round-3-render.txt`, attached to the story.

| Item | Verdict | Evidence |
| --- | --- | --- |
| AC1 - Scope and source | Verified | [`SKILL.md:114-118,134`](https://github.com/noahwhite/agent-skills/blob/ddda852e4c73ff2051694810d577f8fa30cd8d4c/skills/story-to-done/SKILL.md#L114-L134) scopes rules to the recipient and requires exact `path:line` citations, not coordinator-persona rules. |
| AC2 - Prohibitions | Verified | Lines 119-121 bind the AC prohibition to its actor and source and reject a blanket DoD edit ban. |
| AC3 - Permissions | Verified under reading 2 | Seven unedited role/path briefs carried 44 source-exact citations covering verified ticks, assigned state moves, the role's PR, and the review of record. |
| AC4 - Ownership | Verified | Lines 129-130 delegate the completion tick without changing product-owner authority. |
| AC5 - Conflict | Verified | Lines 131-132 require reporting, stopping, and escalation without silent resolution. |
| AC6 - Test pins | Verified | `tests/test_brief_authoring.py` pins AC1-AC5 wording and the QA tick, and 128 focused authoring and renderer tests passed. |
| AC7 - Guards | Verified | Ruff, vendoring and both CI-pinned skill validators passed locally, and [CI on the landed tree](https://github.com/noahwhite/agent-skills/actions/runs/45093106615) passed 4,002 tests, private leak scanning and forced OpenCode discovery. |
| DoD1 - Acceptance criteria | Verified | All seven ACs are met, including AC3 under reading 2. |
| DoD2 - Tests written and passing | Verified | [PR #403](https://github.com/noahwhite/agent-skills/pull/403) changed `tests/test_render_brief.py`, triggering both signals, and records 3,960 local passes at its reviewed head. [Repository tests](https://github.com/noahwhite/agent-skills/actions/runs/45099813253/job/137447806037) passed 3,978 tests after checkout of `bd851eeb71b16c71deee2bc8468cd3880f9c61c2`. The GitHub commits API and local `git rev-parse` agree that both SHAs have tree `eae7a6c9e991d380daae03cad397519d6799c917`, and `git diff --exit-code` found no differences. |
| DoD3 - Independent review | Verified | The final reviews of record for [PR #400](https://github.com/noahwhite/agent-skills/pull/400#pullrequestreview-6014412030) and [PR #403](https://github.com/noahwhite/agent-skills/pull/403#pullrequestreview-6015692087) are comment reviews with both SHA fields matching their respective heads. |
| DoD4 - Docs updated | Verified | The merged `story-to-done` skill contains the Brief authoring section. |
| DoD5 - Deployed verification | Correct by design | No deployment is needed on `no-deployment`. |
| DoD6 - No critical bugs or regressions | Verified in scope | No critical issue surfaced in the raw renders, focused tests, CI, or reviews of record. |

The nonblocking, pre-existing engineer intro still says “the deploy” on `no-deployment` and `spike`.
