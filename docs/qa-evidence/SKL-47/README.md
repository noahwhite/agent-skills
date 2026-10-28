# SKL-47 QA evidence, round 1, 2026-10-28

The repository deploys nothing and the profile lists no environment, so the deployment surface is `main` and there is no visual surface.
The verified build is `2c0d7b7553a705c8ff301a1da199bced45007545`, the squash merge of [PR #69](https://github.com/noahwhite/agent-skills/pull/69).
Its head `37b001311b649dcbbedda588a661f3bd8ede3d35` carries the review of record (PR review 5684408850).
Verification used a fresh clone of `main` at that build.
The B7 fixtures are SKL-112 (`metrics=on`) and SKL-108 (switch omitted); the failed attempts SKL-99, SKL-100, SKL-105, SKL-106, SKL-107, and SKL-109 all read back as Canceled.
The QA comment on SKL-47 (tracker comment `bd3c22da`) cites the attachments behind every row: the evidence page, the repository assertions (47 of 47 pass), and the tracker and CI assertions.

| Item | Verdict | Evidence |
|---|---|---|
| B1 switch and closing message | Verified | The Arguments section precedes "Read first" and states the required `STORY_ID`, `metrics=on` or `metrics=off` with the `off` default, the plain-word forms, the ask-on-other-phrasing rule, resolution before the todo list, and the `metrics:` line; the Closing message section defines the final message on every end state and stop. |
| B2 off is unchanged | Verified | The PR diff to `SKILL.md` only adds lines, in exactly three sections (Arguments, Metrics, Closing message); the off-path sentence is present, and no text outside those sections mentions metrics. |
| B3 wiring | Verified | `skills.json` appends `metrics` after `engineering-practice` in `story-refinement` only, `scripts/vendor_shared.py` is not in the diff, `--check` exits 0, the vendored file equals `shared/metrics.md` plus the generated header, and the on-only section names all ten launch kinds and the timestamp rule. |
| B4 independence and summary | Verified | The independence exclusion, the closing-message summary on every end state and stop with the no-launch case, the no-secrets-or-paths rule, and the no-post statement with its exception to "Read first" are present. |
| B5 registration and docs | Verified | `test_manifest_registers_skill` and `GENERATED_REFERENCES` include `metrics`, the README row names the switch, its `off` default, and the closing message, the seed line collects metrics only when the switch is on, and every vendored `todo-tracking.md` matches the source. |
| B6 tests | Verified | `uv run --locked pytest -q` passes 711 tests on `main`, the vendor check passes, and CI is green on the PR head (run 40706448165) and on `main` (run 40735717156); the PR records 41 phrase deletions, each killed by a named test. |
| B7 verified end to end | Verified | Tracker comments `84ac3b4a` (SKL-112, consensus 2) and `cf3b0e14` (SKL-108, consensus 2) record both closing messages; the on-run totals recompute exactly (21 rows, 12 `not reported`, 310384 tokens, 54 tool calls, `partial`), and its elapsed wall-clock was measured from scratch-directory creation (see Incidental findings). |
| DoD all acceptance criteria met | Verified | B1 to B7 above. |
| DoD tests written and passing | Verified | `tests/test_story_refinement.py` adds the SKL-47 contracts; the full suite passes. |
| DoD independently reviewed | Verified | Review of record 5684408850 at `37b0013`, the merged head, was posted before the merge, with Codex GPT-6 Sol as reviewer and Opus 5.5 as adjudicator. |
| DoD docs updated | Verified | The README row and the `shared/todo-tracking.md` seed line. |
| DoD verified in staging | Not applicable | No environment exists; B7 stands in, as the story states. |
| DoD no critical bugs or regressions | Verified | The suite and CI pass at `main`. |

## Independent checks

Both B7 fixtures read back Canceled with no relations, no children, and no comment carrying a run summary.
In the B7 run windows, no SKL story outside the fixtures and SKL-47 gained a relation, and no other comment came from the runs.
The relations an earlier attempt (SKL-107) created to SKL-73 and SKL-108 are gone.
The off-run closing message has `metrics: off` as its only metrics line.

## Incidental findings

The B7 on-run reports the elapsed wall-clock as "about 12m", measured from scratch-directory creation rather than from the invocation start that `shared/metrics.md` names.
The skill text is correct, so this is a property of that run, not an acceptance criterion failure.
With `metrics` on, voters are still handed the session scratch directory that holds the metrics file; the review of record ruled this out of scope, and SKL-93 owns the per-role subdirectory handoff.
