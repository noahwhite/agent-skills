# SKL-47 QA evidence

Round 2 (B9, added on reopen) is below round 1.

## Round 1, 2026-10-28

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

### Independent checks

Both B7 fixtures read back Canceled with no relations, no children, and no comment carrying a run summary.
In the B7 run windows, no SKL story outside the fixtures and SKL-47 gained a relation, and no other comment came from the runs.
The relations an earlier attempt (SKL-107) created to SKL-73 and SKL-108 are gone.
The off-run closing message has `metrics: off` as its only metrics line.

### Incidental findings

The B7 on-run reports the elapsed wall-clock as "about 12m", measured from scratch-directory creation rather than from the invocation start that `shared/metrics.md` names.
The skill text is correct, so this is a property of that run, not an acceptance criterion failure.
With `metrics` on, voters are still handed the session scratch directory that holds the metrics file; the review of record ruled this out of scope, and SKL-93 owns the per-role subdirectory handoff.

## Round 2, 2026-10-28

The story was reopened with acceptance criterion B9 (invocation start is captured, not inferred), so this round verifies B9 and re-checks B1 to B7 and every DoD item.
The verified build is `fe24764eb9f36706395b475c97c8497cee8f08e7`, the squash merge of [PR #76](https://github.com/noahwhite/agent-skills/pull/76).
Its head `f6a1246e419ac022206e23b5b5bb781ccdd8a348` carries the review of record (PR review 5687830846).
Verification used a fresh clone of `main` at that build.
The B9 fixture is SKL-115 (`metrics=on`); the B7 fixtures SKL-112 and SKL-108 still read back as Canceled.
The round 2 QA comment on SKL-47 (tracker comment `536a2743`) cites the attachments behind every row: the evidence page, the repository assertions (70 of 70 pass), and the tracker and CI assertions.

| Item | Verdict | Evidence |
|---|---|---|
| B1 to B5 | Verified | Every round 1 repository assertion still passes at `fe24764`. |
| B2 off is unchanged | Verified | PR #76 adds one line to `skills/story-refinement/SKILL.md` and removes none; the line is in the Arguments section and opens "When `metrics` resolves on", and no text outside the permitted sections mentions metrics. |
| B6 tests | Verified | `uv run --locked pytest -q` passes 719 tests on `main`, the vendor check passes, and CI is green on the PR head (run 40746268452) and on `main` (run 40748496210). |
| B7 verified end to end | Verified | The round 1 evidence stands; SKL-112 and SKL-108 read back Canceled with no relations, no children, and no summary comment. |
| B9 invocation start | Verified | See the B9 checks below. |
| DoD all acceptance criteria met | Verified | B1 to B7 and B9. |
| DoD tests written and passing | Verified | The full suite passes 719 tests on `main`. |
| DoD independently reviewed | Verified | Review of record 5687830846 at `f6a1246`, the merged head, was posted before the merge, with Codex GPT-6 Sol as reviewer and Opus 5.5 as adjudicator. |
| DoD docs updated | Verified | The README row from PR #69 is intact, and B9 updates the `shared/todo-tracking.md` seed line. |
| DoD verified in staging | Not applicable | No environment exists; the B7 and B9 live runs stand in, as the story states. |
| DoD no critical bugs or regressions | Verified | The suite and CI pass at `main`. |

### B9 checks

The Arguments section states that when `metrics` resolves on, the facilitator's next action, before the todo list, is to take a UTC timestamp with a command and record it as `invocation_start` in the metrics file; that bullet directly follows argument resolution and precedes the `metrics:` line rule.
The Run totals in `shared/metrics.md` define elapsed wall-clock from the recorded `invocation_start` to `invocation_end`, computed from those two timestamps only, never from file, directory, or log times and never estimated, and `not reported` when either timestamp was not recorded.
The summary template line is `- Elapsed wall-clock: <elapsed> (<invocation_start> to <invocation_end>)`.
The `story-refinement` seed line lists "record invocation start (metrics on)" first among its metrics-on items.
Every vendored `metrics.md` and `todo-tracking.md` equals its source, and `--check` exits 0.
The tests pin each guarded phrase, and the PR records 12 of 12 phrase mutations each failing a named test; a diff read confirms each pinned phrase is asserted.
`story-to-done`, the other skill that vendors `metrics.md`, records its start as `invocation_start`, and its pinned test is updated.
The live run on SKL-115 (tracker comment `f87dea75`) reached an unpointed outcome, and its closing message reads `13m08s (2026-10-28T18:34:04Z to 2026-10-28T18:47:12Z)`, a difference of 788 seconds, equal to the stated value.
All four SKL-115 comments fall inside that window, no other comment, relation, or SKL issue change occurred in it, and SKL-115 reads back Canceled.

### Round 2 incidental findings

The SKL-115 closing message writes the token and tool-call totals without the square brackets around the `partial` note that the `shared/metrics.md` template shows; the skill text is correct, and the SKL-112 run used the brackets.
That the start capture ran before the todo list is self-reported in the run evidence; the tracker shows `invocation_start` before the run's first tracker write.
