# SKL-204 QA evidence

Date: 2026-11-06 UTC, independent QA round 1.
Story: SKL-204 - refinement takes the team from the invoked issue key, not the profile.
Build under test: `f5be1cc52257498833f27df9e585b8d3a25b3d04`, the squash merge of PR 145, whose reviewed head was `62ef9cf20ba2c58bfd0166b2baf7fc2ab943fb84`.
Environment: a fresh checkout of `main` at the build SHA.
The profile lists no environments and this repository deploys nothing, so `main` at the merge commit and the exact-build CI run are the deployed-build equivalent.
CI: run 42307999904 on the reviewed head and run 42308451512 on the build SHA, both successful.

Fixtures: none; the probes are read-only text assertions over the changed skills, `shared/linear.md` and its vendored copies, the test suite, and three read-only `linear` CLI calls against team SKL.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The assertion file `SKL-204-qa-assertions.txt` is attached to SKL-204 as "SKL-204 QA assertions (main f5be1cc)", SHA-256 `76e52618e0f7f0e0f371f144099579704fb62a672922f398faf14786efc0024c`, and the QA evidence comment `84d2ef1e` cites it.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: invocation key wins | Verified | `story-refinement`, `story-to-done`, `persona-staff-engineer` and `persona-staff-devops` each state that `STORY_ID` is any Linear issue key and carry the invocation-key sentence exactly once. The old parenthetical has no hit in `skills/` or `shared/`. |
| AC2: profile key is the fallback only | Verified | `shared/linear.md` line 4 and the MCP fallback line are rewritten. The Team resolution section states the prefix rule, CLI `--team` and MCP team-name resolution, the stop on a failed resolution, and the profile fallback. All 18 vendored copies match the shared body. |
| AC3: split siblings and searches follow the story's team | Verified | The story-refinement Arguments search sentence and Split rule sibling line exist. The shared Filing issues on-behalf sentence and both `linear-user-story` team rows exist. |
| AC4: differing team is handled, not silent | Verified | The differing-team rule names `linear team states <KEY>`, `linear label list --team <KEY>`, the MCP fallback, and the stop before any write. It is cited in the story-refinement Split rule and Triage and in story-to-done step 1. Live, `linear team states SKL` lists every profile state, the label listing includes workspace labels, and `linear issue view --team` exits 2. |
| AC5: no other skill regresses | Verified | The cleanup stop on a differing prefix is gone and `tests/test_cleanup.py` pins the new sentence. Every `git grep -n team_key` hit over `skills/` and `shared/` falls into a class the PR body lists. The only remaining profile-key rows are the standalone `linear-*` filing fallbacks. |
| AC6: vendored copies regenerated | Verified | `scripts/vendor_shared.py --check` exits 0, and a regeneration leaves zero drift. |
| AC7: tests and gate | Verified | The tests assert every named sentence, and the PR body records the revert-and-fail proof. `uv run --locked pytest -q` reports 1119 passed at the build, and both CI runs are green. |
| DoD1: all acceptance criteria met | Verified | AC1 to AC7 above. |
| DoD2: tests written and passing | Verified | New and updated tests in `test_shared_linear.py`, `test_story_refinement.py`, `test_cleanup.py` and the new `test_linear_user_story.py` pass. |
| DoD3: independently reviewed | Verified | PR review 5808123607 is the review of record at `62ef9cf20ba2c58bfd0166b2baf7fc2ab943fb84`, the merged head, posted before the merge. The reviewer was Codex GPT-6 Sol and the adjudicator a clean Claude Opus 5.5 agent; no finding was valid. |
| DoD4: docs updated | Verified | The deliverable is the skill prose itself. |
| DoD5: verified in a deployed environment, if needed | Not applicable, correct by design | The profile lists no environments. |
| DoD6: no critical bugs or regressions | Verified in tested scope | The full suite and CI are green. |

Closing decision: every AC and DoD item is verified, so the story moves to Done once this evidence PR merges.
