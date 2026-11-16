# SKL-311 QA evidence

## QA round 1

Date: 2026-11-16 UTC, independent QA round 1.
Target: `main` at `5e552a7021d7fd51dd0ed1362399c9b804f78d44`, the squash merge of PR 300, whose reviewed head is `3919a295137725a441bf5567cb4532d341d221c2`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`, and `skills/story-to-done` is identical at the reviewed head and the target.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Fixtures: none; the evidence is the committed records, summaries and README at the target, PR 300, its CI runs and the tracker.
The raw output is attached to SKL-311 as "SKL-311 QA round 1 assertion output at target 5e552a7".
There is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| R1: the case is carried as its own story | Verified | R1 detail below. |
| R2: the graded recording | Pending owner ruling (record 1) | R2 detail and record 1 below. |
| R3: file scope and commit order | Verified | R3 detail below. |
| R4: guards on the final head | Verified | R4 detail below. |
| R5: no path prefix or session marker | Verified | R5 detail below. |
| DoD: all acceptance criteria met | Pending owner ruling (record 1) | This item follows R2. |
| DoD: tests written and passing | Verified | At the target the full suite `uv run --locked pytest -q` passes 2801 locally, and the "Repository tests" step passed in CI runs 43834143581 (head) and 43834966331 (target). |
| DoD: independently reviewed | Pending owner ruling (record 2) | Record 2 below. |
| DoD: docs updated | Verified | The README case list row is updated (R2 detail); `rerun.md` is outside R3's file set, and record 2 covers it. |
| DoD: verified in a deployed environment | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | Push CI run 43834966331 on `main` at the target passed `checks` and `discovery`. |

### R1 detail

The stop rule applies (R2 detail).
SKL-325 is the cut story.
Its description links PR 300, the committed `results/` directory at the target and all six suite summaries.
SKL-311 comment `ac6562b5` records the cut and names PR 300, holding revision 1 `768ca16` and revision 2 `7b8bc4f`, as the only revision PR.

### R2 detail

Every clause except the one in record 1 holds at the target.
The case `results/` directory holds 37 run records and 37 `-calls.jsonl` files, in the names `run-suite.sh` writes, under three label pairs with the suffixes `-h07567d2`, `-r1-h768ca16` and `-r2-h7b8bc4f`.
Each record names its checkout commit (`9bd3e16` or `6838b35`), the model `deepseek/deepseek-v4-pro` and the `case.yaml` command.
`case.yaml` is unchanged from the PR 300 merge base `ab03ba1`.
Each scenario has 3 graded runs at each pin in each recording.
The one void, baseline `split-verdict` attempt 2 on harness `7b8bc4f`, and its replacement, attempt 4, are both committed.
`results/.gitkeep` is gone.
The six summaries are under `skills/story-to-done/evals/results/`.
The README case list row reads `not discriminating`, with per-scenario counts for every recording.
Both revisions change only the `split-verdict` files `qa-round-1.md`, `qa-round-2.md`, `qa-round-3.md` and `rounds.json`.
The PR 300 body states each label's invocation, with the local checkout path written as `<checkout at <sha>>`.

### R3 detail

Outside the two results directories, the diff from the merge base `ab03ba1` to `3919a29` changes only `skills/story-to-done/evals/README.md` and the four revision files named in the R2 detail.
The SKL-310 classifier commit `86daabe` is an ancestor of `1190d2c`, the first commit that adds `results/` files.

### R4 detail

CI run 43834143581 (`pull_request`, head `3919a29`) passed.
In job `checks`, the steps "Repository tests", "Leak scan (public and private patterns)" and "Validate skills against the Agent Skills spec" passed.
In job `discovery`, the step "opencode discovers every skill" passed.
Guard 2 at the target reports `leak scan INCOMPLETE: no private patterns loaded (LEAK_DENYLIST / LEAK_DENYLIST_FILE)` with no finding.
The PR 300 body records each guard with its job, conclusion and link.

### R5 detail

Both searches below ran from the root of a checkout of the target, and both printed nothing and exited 1.

```
grep -rn -a -E '/home/|/tmp/|session\.|/root/|/Users/|\\/home|\\u002f' skills/story-to-done/evals/pending-ruling-not-sent-to-engineer/results skills/story-to-done/evals/results
grep -rn -a -P '(?<!\{run_dir\})/workspace' skills/story-to-done/evals/pending-ruling-not-sent-to-engineer/results skills/story-to-done/evals/results
```

The last two alternatives of the first pattern match JSON-escaped slashes: a backslash followed by `/home`, and a backslash followed by `u002f`.
`/workspace` occurs only as the `{run_dir}/workspace` placeholder, 171 times.
The PR 300 body records its own anchored command and its empty result.

### Pending owner ruling, record 1: R2 and the uncommitted recording 1

Owner: the product owner.
Quoted text (R2):

> Every run produced is committed, including a candidate run that fails and a baseline run that passes.
> "Every run produced" applies to the graded recording; the producibility run in AC3 is reverted and not committed.
> No run is deleted, re-rolled or repeated to reach a pass, and no pin is moved to reach a pass.

Evidence: recording 1 ran through `run-suite.sh` on harness `186df21` at both unchanged pins, with labels `deepseek-v4-pro-baseline-9bd3e16` and `deepseek-v4-pro-candidate-6838b35`, and produced 13 run records (SKL-311 comment `cc3f78a7`).
None of them is committed at the target: no committed record or summary names harness `186df21`.
2 of the 13 records held an absolute run path that R5 forbids, from the harness defect that SKL-313 fixed.
SKL-311 comment `baff0b12` quotes an owner ruling, relayed by the coordinator, that recording 1 is void, is not committed and is re-recorded in full, and that this is not a forbidden re-roll.
It also records that recording 1 was `split-verdict` 3/3 and `plain-failure` 3/3 at both pins, the same result as every committed recording.
No dated amendment of R2 is on the story.

- Reading A: the graded recording is the recording that is committed under R5, so a recording voided whole for a harness defect before any commit, and not for its results, is not part of it.
  Verdict: verified.
- Reading B: recording 1 is a graded recording through `run-suite.sh`, so its 13 runs are runs produced, and leaving them uncommitted breaches R2.
  Verdict: failed, and committing them would breach R5.

The DoD item "All acceptance criteria met" follows this record.

### Pending owner ruling, record 2: DoD "Independently reviewed"

Owner: the product owner.
Quoted text (Review Policy):

> "Independently reviewed" means the review of record in references/code-review.md is clean on the PR head and every finding is adjudicated.

Evidence: the review of record on PR 300 (review 5917283461, `COMMENTED`, `commit_id` and first line both `3919a295137725a441bf5567cb4532d341d221c2`, the merged head) names GPT-6.1 Sol (`gpt-6.1-sol`) as reviewer and DeepSeek V4.1 Flash (`deepseek/deepseek-flash`) as adjudicator.
It rules one finding Valid, Low and not blocking: `rerun.md:66` still describes round three as it was before revision 2.
PR 300 merged with no fix for it, because R3 does not let this story change `rerun.md`; SKL-325's first acceptance criterion carries the fix.
`shared/code-review.md` line 45 reads "Fix every finding ruled valid in the same PR."
Its line 128 reads "Valid findings are fixed in the PR, never filed as follow-ups."

- Reading A: "clean" means no finding blocks the merge, and every finding is adjudicated.
  Verdict: verified.
- Reading B: "clean" means no finding ruled valid is left unfixed in the PR.
  Verdict: failed, and no fix is possible within R3.

On SKL-257 the product owner's amended text holds this DoD item met once the story's last PR has a clean review of record and every finding ruled valid across the story's PRs is fixed on `main` (`docs/qa-evidence/SKL-257/README.md`, round 3).
That text is not on SKL-311, and it matches neither reading above: under it, this item stays unmet until the SKL-325 fix of `rerun.md` is on `main`.

Closing decision: no item failed, and records 1 and 2 are pending owner ruling, so SKL-311 stays in In Deployment Review.
