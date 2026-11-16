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
