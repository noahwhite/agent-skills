# SKL-75 QA evidence - round 1

Date: 2026-11-10.
Build: `47cf94031bbdd20a1f640eb39f324e0d6a977013` on merged `main`.
Environment: repository CI; the repository profile has `environments: []`.
Surface: skill text, repository tests in merged CI, and the vendored reference copies.
Fixtures: none live; verification is the repository suite plus the authoring-time mutation and structural proof transcripts recorded on the implementation PR.
The attached assertions are the raw record, not screenshots or a hosted page.

## Evidence

- Tracker evidence: SKL-75, QA comment on the story.
- [Merged CI](https://github.com/noahwhite/agent-skills/actions/runs/42917135648): `checks` and `discovery` succeeded on the merge commit; `uv run --locked pytest -q` reported 1606 passed.
- [Implementation PR](https://github.com/noahwhite/agent-skills/pull/188): merged as the build above, with the review of record bound to `8964e381463f7d3db4c9ba8cb28697447b790152` (reviewer codex `gpt-6-sol`, adjudicator `deepseek-v4-pro` via direct API, one Medium finding adjudicated INVALID, no Critical/High).
- The suite invokes `scripts/vendor_shared.py --check` in `test_vendored_references_are_current`; it exited 0 on the PR head and again on the merge commit.
- Mutation check: 14 of 14 pinned-sentence deletions each failed exactly the named test (transcript inline in the PR body). Structural proof: 10 of 10 structural mutants caught.

QA read the merged tests and CI output rather than rebuilding or mutating the suite.

## Verdicts

| Item | Verdict | Evidence |
|---|---|---|
| AC1 Rule in shared source | Verified; the one-pass rule and ceremony exception are their own bullet under `## Acceptance criteria and scope` in `shared/linear.md`, pinned by `tests/test_one_pass_evidence.py`. | AC1; shared/linear.md lines 89-93; merged suite |
| AC2 Rule reaches filing skills | Verified; one-sentence citations in rules prose of linear-user-story (both sites), linear-bug and linear-spike; template blocks unchanged; linear-investigation and linear-epic exclusions pinned; 18 vendored copies regenerated. | AC2; skills/*/SKILL.md; vendor --check exit 0 |
| AC3 No weakening | Verified; preserved sentences pinned per source line and byte-identical; completion section and DoD template blocks untouched. | AC3; PRESERVED_SENTENCES pins; mutation check 14/14 |
| AC4 Tests | Verified; parametrized per-sentence pins with exactly-one-named-test failure, authoring-time mutation check recorded in the PR body, full suite green. | AC4; tests/test_one_pass_evidence.py; PR #188 body |
| AC5 Source/generated drift | Verified; hand-written set is shared/linear.md, three SKILL.md files and the test file; everything else is the 18 generated copies; `vendor_shared.py --check` exits 0. | AC5; PR #188 path inventory |
| DoD All AC met | Verified; AC1-AC5 above. | DoD1 |
| DoD Tests written and passing | Verified; 1606 passed on merged CI. | DoD2 |
| DoD Independently reviewed | Verified; review of record posted on PR #188 bound to the merged head content, clean verdict after adjudication. | DoD3 |
| DoD Docs updated | Verified; the rule and citations are the documentation change; no README change needed per AC5. | DoD4 |
| DoD Verified in a deployed environment | Correct by design / out of scope; the profile has no environments and this is a repository-text change verified by CI. | DoD5 |
| DoD No critical bugs/regressions | Verified; pre-PR adversarial gate converged with no unresolved Critical/High, review of record clean, merged CI green. | DoD6 |

## Reproduction and handoff

At the build above, run `uv run --locked pytest -q` in a checkout of `main`; the vendoring drift test fails if any `skills/*/references/linear.md` copy is hand-edited or stale.
