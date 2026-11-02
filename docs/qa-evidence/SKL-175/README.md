# SKL-175 QA verification

- Date: 2026-11-02.
- Story: SKL-175.
- Delivered build: `f3ec7e9939d38271c25726b685084f0d7a2675db`, merged by [implementation PR](https://github.com/noahwhite/agent-skills/pull/133).
- Reviewed implementation head: `eb587a642ab33da2441ce88f21c567b4add1f10c`.
- Lane: read-only source and JSON Schema probes in a detached worktree at that merge; `profile.environments: []`, so no deploy target or installed-container claim.
- Fixtures: shipped example profile, in-memory reviewer counts 2/3/4, missing/empty families, allowed non-voting PO/reviewer model-and-family duplication, and the transitional repository profile.
- Evidence: 22 source assertions and seven direct JSON Schema assertions; sanitized raw output is attached to the story as `SKL-175-qa-assertions.txt`.
- CI: [merge-SHA run](https://github.com/noahwhite/agent-skills/actions/runs/41377883264), completed successfully; `uv run --locked pytest -q` reported `1017 passed in 120.19s`.
- No local suite was rebuilt or rerun, no ceremony or tracker-write mutation was used to check AC6, and there is no visual surface requiring screenshots.

## Verdicts

| Item | Verdict | Evidence |
|---|---|---|
| AC6: three engineer estimators; PO non-voting | Verified within core scope | `profile/schema.json:441-468,576-614`; `profile/example.yaml:141-153`; `skills/story-refinement/SKILL.md:7,17-18,59-72,102-104,111,128-161`; seven direct schema fixtures validate expected acceptance/rejection. |
| AC6: roster stop before preflight and launch | Verified as shipped instructions | `skills/story-refinement/SKILL.md:101-111`; operative numbered items order roster, preflight, engineers; named count, role, family and model-id errors and first-existing-file resolution are present; new runtime regression cases belong to SKL-181. |
| AC6: records, README and roster assertion rewrites | Verified | `README.md:34`; `skills/story-refinement/references/refinement-record.md:22-25,52-54,71-74`; changed guards in `tests/test_story_refinement.py` and `tests/test_seat_enabled.py` are present and merge-SHA CI passes. |
| AC6: accepted-path-set / PO tie-break clauses | Correct by upstream design | SKL-60 is Done and already replaced this mechanism; Step 4 is byte-identical to the merge parent, using residual variance and a later owner decision instead. |
| DoD: all acceptance criteria met | Verified within core scope | AC6 verdicts above; sibling-owned exclusions below are explicit in the accepted story, not removed at closure. |
| DoD: unit/integration tests written and passing | Verified | Merge-SHA CI run above reports 1017 passing; roster guards changed in the same implementation merge. |
| DoD: independently reviewed | Not fully covered against repository policy | The posted COMMENTED review of record binds both SHAs to the final implementation head, but names a different adjudicator than `.agent-skills/profile.yaml:60-63`; owner action below remains. |
| DoD: documentation updated | Verified | README row, ceremony roles/steps and all three record templates match the scoped three-engineer change. |
| DoD: verified in a deployed environment if needed | Correct by design | `.agent-skills/profile.yaml:92-95` declares no environments; exact merged-content verification is the specified lane. |
| DoD: no critical bugs/regressions | Verified within exercised scope | 29 structured assertions pass and merge-SHA CI succeeds; no critical product regression observed. |

## Outstanding owners and incidental findings

The implementation review of record names `openrouter/deepseek/deepseek-v4.1-flash`, while the repository profile at the verified build names `deepseek/deepseek-v4-pro`.
The implementation note also records a Grok pre-PR arbiter where that profile names `opencode/glm-5.3-flash-free`.
No per-story substitution authorization was found in the inspected story comments or review record; the container's standing roster differs from the repository-specific profile.
Noah White / engineering-workflow owns reconciling that authorization and the independent-review DoD; the configured V4 Pro seat returned `READY` here on OpenCode v2.2.5.
This is an outstanding process-evidence gap, not a failed product assertion; SKL-175 remains **In Deployment Review**, with Done gated on that owner action and the merged QA evidence.

SKL-181 is Backlog and owns the repository's still-two-reviewer profile plus the new validation regression cases; direct schema validation rejects that transitional profile as expected.
SKL-180 is Backlog and owns the old persona hand-offs; SKL-176 owns the unchanged pointing basis and phrasing table; SKL-177 owns consumer rollout.
No separate incidental product defect was observed or filed.
