# SKL-181 QA evidence - round 1

- Verified: 2026-11-20
- Path: `no-deployment`
- Target: [`24608ed762729bc570998750cba84e2b6ccb180e`](https://github.com/noahwhite/agent-skills/commit/24608ed762729bc570998750cba84e2b6ccb180e) on `origin/main`, merged in [PR #375](https://github.com/noahwhite/agent-skills/pull/375).
- Raw assertion output is attached to the story.

| Item | Verdict | Evidence |
| --- | --- | --- |
| AC12 - three engineer seats | Verified | Both committed profiles validate against `profile/schema.json` and each has three distinct reviewer models and families. |
| DoD 1 - acceptance criteria | Verified | AC12 is the only criterion and all its assertions passed. |
| DoD 2 - tests written and passing | Verified | `tests/test_profiles.py` covers both profiles, and [PR CI](https://github.com/noahwhite/agent-skills/actions/runs/44788077914) passed on a tree identical to the merge target. |
| DoD 3 - independent review | Verified | The [final review of record](https://github.com/noahwhite/agent-skills/pull/375#pullrequestreview-5997402613) is bound to `96cd91514d66504eedf658e614fadc657ab89c33`. |
| DoD 4 - docs if applicable | Correct by design | The profile documents the roster inline, and standalone docs are outside this profile-and-test slice. |
| DoD 5 - deployed verification if needed | Correct by design | The recorded `no-deployment` path verifies the merged commit instead. |
| DoD 6 - no critical bugs or regressions | Verified | The committed scope, profile assertions, CI and final review surfaced no critical story regression. |

The repository roster is DeepSeek V4.1 Flash 1017 (`deepseek`), GPT-6.2 Sol (`openai`) and MiMo V2.6 Flash (`xiaomi`).
Each launches through the existing `opencode run` command shape with `--title "{session_title}"`.
Both product-owner entries are unchanged and neither overlaps its reviewers' names or models.
The core voter-set commit is an ancestor of the target, and the regression test checks schema, seat count, families, models and product-owner separation.

The historical round-1 implementation review body and GitHub review commit binding disagree.
Its final review has matching bindings, so the historical discrepancy does not block QA.
