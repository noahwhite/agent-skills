# SKL-204 QA evidence

## Round 2

Date: 2026-11-07 UTC, independent QA round 2, after the story was reopened with AC3, AC5 and AC7 amended and AC8 added.
Story: SKL-204 - refinement takes the team from the invoked issue key, not the profile.
Build under test: `6e917ed59ceefb18f53e94130feefe61e8b0b1fb`, the squash merge of PR 151, whose reviewed head was `59e066f3a07aab1b1b4ddc55c18da5f6f28b42eb`; it also carries round 1's PR 145 (`f5be1cc52257498833f27df9e585b8d3a25b3d04`).
Environment: a fresh checkout of `main` at the build SHA.
The profile lists no environments and this repository deploys nothing, so `main` at the merge commit and the exact-build CI run are the deployed-build equivalent.
CI: run 42332165919 on the reviewed head and run 42332500387 on the build SHA, both jobs (`checks`, `discovery`) successful.
Tool versions: linear CLI 2.6.0.

Fixtures: none; the probes are read-only text assertions over the changed skills, `shared/linear.md` and its 18 vendored copies, the test suite, and read-only `linear` CLI calls against team SKL.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The assertion file `SKL-204-qa-assertions-round2.txt` is attached to SKL-204 as "SKL-204 QA assertions round 2 (main 6e917ed)", SHA-256 `35d4f618f7fdaf257d0c30f9ab3f9d4471b9b1f9c78698f5a832c9154a316aac`, and the round 2 QA evidence comment cites it.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: invocation key wins | Verified | `story-refinement`, `story-to-done`, `persona-staff-engineer` and `persona-staff-devops` each state that `STORY_ID` is any Linear issue key and carry the invocation-key sentence. The old parenthetical's only hit in the repository is the test constant that asserts its absence. |
| AC2: profile key is the fallback only | Verified | The `shared/linear.md` intro and MCP fallback line are rewritten. The Team resolution section states the prefix rule, CLI `--team` and MCP team-name resolution, the stop on a failed resolution, and the profile fallback. All 18 `references/linear.md` copies match the shared body byte for byte. |
| AC3: split siblings and searches follow the story's team | Verified | The story-refinement Arguments search sentence, the Split rule sibling line and the shared Filing issues on-behalf sentence exist. `linear-user-story`, `linear-bug`, `linear-spike`, `linear-investigation` and `linear-epic` each carry the named-issue team key and team name rows with the profile fallback, and their CLI and MCP steps read the team from that table. Their vendored references match. |
| AC4: differing team is handled, not silent | Verified | The differing-team rule names `linear team states <KEY>`, `linear label list --team <KEY>`, the MCP fallback and the stop before any write. It is cited in the story-refinement Split rule and Triage and in story-to-done step 1. Live, `linear team states SKL` lists every profile state, the label listing includes workspace labels, and an unknown team exits 1. |
| AC5: no other skill regresses | Verified | The cleanup rule lets the tracker lookup alone decide, and `tests/test_cleanup.py` pins that sentence. Every `git grep -n team_key` hit over `skills/` and `shared/` falls into a class the PR 151 body lists, and the remaining profile-key rows are the standalone filing and epic-search fallbacks. No skill script reads the team key. |
| AC6: vendored copies regenerated | Verified | `scripts/vendor_shared.py --check` exits 0, and a regeneration leaves zero drift. |
| AC7: tests and gate | Verified | The named tests exist, including one team-row test per filing skill and the AC8 tests. The PR 145 and PR 151 bodies record the revert-and-fail proof. `uv run --locked pytest -q` reports 1235 passed at the build, and both CI runs are green. |
| AC8: epic search is scoped to one team | Verified | `linear-epic` searches with `linear project list --team ABC`, taking the named issue's team or else the profile team, and states that an epic belongs to exactly one team. A scan of `skills/`, `shared/`, `README.md` and `docs/` finds no other cross-team epic wording. Live, `linear issue query --search <term> --team SKL` and `linear project list --team SKL` both run. |
| DoD1: all acceptance criteria met | Verified | AC1 to AC8 above. |
| DoD2: tests written and passing | Verified | Tests in `test_linear_filing_skills.py`, `test_shared_linear.py`, `test_story_refinement.py` and `test_cleanup.py` pass with the full suite. |
| DoD3: independently reviewed | Verified | PR 151 review 5809688202 is the review of record at `59e066f3a07aab1b1b4ddc55c18da5f6f28b42eb`, the merged head, posted before the merge. The reviewer was Codex GPT-6 Sol and the adjudicator a clean Opus 5.5 agent, the owner's standing review-of-record seat; the repository profile names DeepSeek V4 Pro as adjudicator. |
| DoD4: docs updated | Verified | The deliverable is the skill prose itself. |
| DoD5: verified in a deployed environment, if needed | Not applicable, correct by design | The profile lists no environments. |
| DoD6: no critical bugs or regressions | Verified in tested scope | The full suite, skills-ref validation of all 18 skills, the leak scan over public patterns and CI are green. |

Closing decision: every AC and DoD item is verified, so the story moves to Done once this evidence PR merges.

## Round 1

Date: 2026-11-06 UTC, independent QA round 1.
Build under test: `f5be1cc52257498833f27df9e585b8d3a25b3d04`, the squash merge of PR 145, whose reviewed head was `62ef9cf20ba2c58bfd0166b2baf7fc2ab943fb84`.
Environment: a fresh checkout of `main` at the build SHA.
CI: run 42307999904 on the reviewed head and run 42308451512 on the build SHA, both successful.

Fixtures: none; the probes are read-only text assertions over the changed skills, `shared/linear.md` and its vendored copies, the test suite, and three read-only `linear` CLI calls against team SKL.
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

Closing decision: every AC and DoD item was verified; the story later reopened with AC3, AC5 and AC7 amended and AC8 added, which round 2 covers.
