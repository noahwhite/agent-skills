# SKL-286 QA evidence

## Round 1

Date: 2026-11-16 UTC, independent QA round 1.
Story: SKL-286 - `cleanup` removes a landed worktree whose only leftovers are profile-declared build output.
Path: `no-deployment`.
Target: `main` at `3bfaf7db2392cd7d8c99977818349585e4a9d21b`, the squash merge of PR 293, whose reviewed head is `ff78dc6491b7c309112c417abf7ebf8a8d2e413f`; the two trees are identical.
No environment or deployed build applies, so every item was checked on the repository, GitHub and tracker lanes.
The test suite, the guards and the probes ran in a detached worktree of the target.
Method: a probe read `skills/cleanup/SKILL.md` and `profile/schema.json` at the target and validated `cleanup` values with `jsonschema` against `profile/example.yaml`; a second probe applied 13 mutants one at a time and ran `tests/test_cleanup.py`.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw output and the probes are attached to SKL-286 as `SKL-286-a1-a4-text-schema-probe.txt`, `SKL-286-a5-mutation-spot-check.txt`, `SKL-286-a6-trace-check.txt`, `SKL-286-pr293-body.txt`, `SKL-286-a7-dod-repo-lane.txt`, `probe_text_schema.py` and `mutate.py`.

| Item | Verdict | Evidence |
|---|---|---|
| A1: profile key | Verified | The schema adds the optional `cleanup` object with `additionalProperties: false`, `regenerable_dirs` with `default: []`, and the exact item predicate the AC gives. It accepts 7 profiles, including one without `cleanup`, one with `cleanup: {}` and one with `cleanup: {regenerable_dirs: []}`, and rejects 17, including a `regenerable_dirs` item with a trailing newline, a NUL or the name `.git`, a bare-string `regenerable_dirs`, `regenerable_dirs: [1]` and an unknown key under `cleanup`. Step 3 cites the key in one sentence with the unset and no-ask clause, and Read first names the declared regenerable directories. |
| A2: declared entries are regenerable | Verified | The fixed-list sentence is unchanged, and the declared-entry, declaration-alone, content-check, "each regenerable directory, fixed-list or declared", either-source and never-regenerable texts are present verbatim in the AC's positions. |
| A3: SKL-243 A2 amended | Verified | The any-other-entry phrase and both recorded-instruction occurrences carry the new wording, and the old phrases are gone. The file is unchanged between 7ae1b94 and the merge parent, and the merge only adds the declared source, so with the key unset or `[]` every decision is as at 7ae1b94. |
| A4: inventory and report say why | Verified | The step 2 source sentence and both-sources label, the step 3 Report sentence and the step 6 template lines are present, and the untracked-entry line is unchanged. |
| A5: tests | Verified | The diff replaces and adds every assertion the AC lists, and `tests/test_cleanup.py` passes 87 tests. The PR records 36 killed mutants with their failing tests. A QA spot-check of 13 mutants at the target killed 13 of 13, each through the test the PR names. |
| A6: trace check | Pending owner ruling | Every named element of the trace is present and matches the consumer run it records. Worktree 2's deletion and removal are summarized as "the same over its five entries" rather than shown command by command, so the verdict depends on how "command by command with each command's output" is read. The SKL-286 QA evidence comment records both readings for the product owner. |
| A7: guards | Verified | At the target `pytest` passes 2708 tests, `skills-ref validate skills/cleanup` at the CI pin reports a valid skill, the opencode smoke test finds all 18 skills in 6 layouts, and the public leak scan is clean. CI `checks`, including the private leak scan, and `discovery` succeeded on `ff78dc6` and on `3bfaf7d`. No shared reference is touched, and PR 293 records the results. |
| DoD: all acceptance criteria met | Pending owner ruling | It follows A6; the other six criteria are verified. |
| DoD: tests written and passing | Verified | 2708 tests pass at the target, and CI is green. |
| DoD: independently reviewed | Verified | The PR 293 review of record names `ff78dc6` in its first line and as its `commit_id`, which is the merged head. Its reviewer is Codex GPT-6 Sol and its adjudicator is DeepSeek V4.1 Flash, with 0 findings. |
| DoD: docs updated | Verified | PR 293 edits steps 2, 3 and 6 of `skills/cleanup/SKILL.md` and `profile/schema.json`. |
| DoD: verified in a deployed environment | Not needed | Correct by design on the `no-deployment` path: the repository deploys nothing. |
| DoD: no critical bugs or regressions | Verified | The full suite passes, and the fixed-list rules and their pins are unchanged. |

Closing decision: the story stays in deployment review until the product owner rules on A6.

## Round 2

Date: 2026-11-16 UTC, independent QA round 2, after the product owner's dated A6 ruling on the story.
Path: `no-deployment`.
Target: `main` at `3bfaf7db2392cd7d8c99977818349585e4a9d21b`, the squash merge of PR 293; it is an ancestor of `main` at `b3e4eeaf66af0d053229d18d9491a2cf7ff98ce5`, and the three changed files are unchanged on `main` since.
No environment or deployed build applies, so every item was checked on the repository, GitHub and tracker lanes, with fresh evidence for every item.
The test suite, the guards and the probes ran in detached worktrees of the target.
Method: a probe read `skills/cleanup/SKILL.md` and `profile/schema.json` at the target and validated `cleanup` values with `jsonschema` against `profile/example.yaml`; a second probe applied 18 mutants one at a time and ran `tests/test_cleanup.py`; a third probe checked the PR 293 trace against A6 as amended.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw output and the probes are attached to SKL-286 under titles that begin "SKL-286 QA round 2".

| Item | Verdict | Evidence |
|---|---|---|
| A1: profile key | Verified | 43 checks pass: the `cleanup` object, `additionalProperties: false`, `default: []`, the descriptions, the exact item predicate, 7 accepted and 17 rejected `cleanup` values, the step 3 key sentence and the Read first bullet. |
| A2: declared entries are regenerable | Verified | The fixed-list sentence is unchanged, and the declared-entry, declaration-alone, content-check, "each regenerable directory, fixed-list or declared", either-source and never-regenerable texts are present verbatim in the AC's positions. |
| A3: SKL-243 A2 amended | Verified | The new any-other-entry phrase is present, the new recorded-instruction phrase occurs twice, and the old phrases are gone. `skills/cleanup/SKILL.md` is unchanged between 7ae1b94 and the merge parent, and the merge only adds rules that need a declared name, so with the key unset or `[]` every decision is as at 7ae1b94. |
| A4: inventory and report say why | Verified | The step 2 source sentence follows the remove-disposition sentence, the both-sources label rule and the step 3 Report sentence are present, and the step 6 template lines match with the untracked-entry line unchanged. |
| A5: tests | Verified | The diff replaces and adds every assertion the AC lists, and `tests/test_cleanup.py` passes 87 tests. PR 293 records 36 killed mutants with their failing tests. A QA spot-check of 18 mutants at the target killed 18 of 18, and the restored file passes. |
| A6: trace check | Verified | Checked against A6 as amended on 2026-11-16, under which a repetition over named entries stated as identical satisfies "command by command with each command's output". 33 of 33 trace checks pass: both worktrees, their branches with the story key at a token boundary, each HEAD paired with its PR, exact `-z` paths matching the consumer's recorded cleanup report, the nested-repository assumption, the key-set inventory, deletions, empty second status read and removals, and the key-unset refusals. The key appears in no committed YAML file. |
| A7: guards | Verified | At the target `pytest` passes 2708 tests, `skills-ref validate skills/cleanup` at the CI pin reports a valid skill, the opencode smoke test finds all 18 skills in 6 layouts, and the public leak scan is clean. CI `checks`, including the private leak scan, and `discovery` succeeded on `ff78dc6` and on `3bfaf7d`. No shared reference is touched, and PR 293 records the results. |
| DoD: all acceptance criteria met | Verified | A1 to A7 are verified. |
| DoD: tests written and passing | Verified | 2708 tests pass at the target, and CI is green. |
| DoD: independently reviewed | Verified | The PR 293 review of record is a `COMMENTED` review whose first line and `commit_id` are `ff78dc6491b7c309112c417abf7ebf8a8d2e413f`, the merged head. Its reviewer is Codex GPT-6 Sol and its adjudicator is DeepSeek V4.1 Flash, with 0 findings. |
| DoD: docs updated | Verified | PR 293 edits steps 2, 3 and 6 and Read first of `skills/cleanup/SKILL.md`, and `profile/schema.json`. |
| DoD: verified in a deployed environment | Not needed | Correct by design on the `no-deployment` path: the repository deploys nothing. |
| DoD: no critical bugs or regressions | Verified | The full suite passes, and the fixed-list rules and their pins are unchanged. |

Closing decision: every item is verified, so the story moves to Done once this evidence merges.
