# SKL-232 QA evidence

## QA round 1

Date: 2026-11-17 UTC, independent QA round 1.
Target: `main` at `7bb5a66bf0618f588bb4c9a9818e948ced414489`, the squash merge of PR 314, whose reviewed head is `c70ed3d30d81289622398d6f62c3bf51695b6736`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`; the only later change on `main` is the SKL-324 evidence README.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Fixtures: a detached worktree at the target and a read of the agent's persistent memory store.
The raw output is attached to SKL-232 as "QA round 1: K1-K7 and DoD checks (raw output)"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| K1: read before asserting | Verified | `shared/engineering-practice.md` holds `## Read the source before asserting` directly after `## Do not hide failures`. Its bullets cover reading the authoritative source before theorizing, asserting, acting, filing or writing a fact, quoting the real error, proving the before-state, checking every "because X", and a labelled hypothesis. "Diagnose before you touch code" is linked by anchor, not restated. |
| K2: say "I don't know" | Verified | The section says to say you do not know or name what could not be checked, never a plausible sentence in its place, and to carry the unverified label into the PR description or handback. |
| K3: correct over convenient | Verified | The section says to pick the correct and robust option over least effort or cost, lists the five phrases that are not reasons to skip required work, and says incomplete work is reported with its blocker, never claimed done. |
| K4: one home | Verified | The payload-shape bullet stays and links to `#read-the-source-before-asserting`. `tests/test_read_source_rule.py` makes the four required assertions and passes (4 passed); the heading occurs once in `shared/` and once in each of the eight generated copies. The PR 314 body shows each assertion failing under its mutants and five false-positive probes passing. |
| K5: generic text | Verified | The section and the cross-reference name no host, plan, price, tenant, domain, network, consumer repository or consumer instruction file. The review of record covered the whole diff, and its first round raised a finding on the section's own wording. The private leak scan passed in CI run 44102557377 with `--require-private`. |
| K6: copies and memory | Verified | `scripts/vendor_shared.py --check` exits 0 at the target. In the memory store one note is absent, one is deleted with its index entry, and one is a pointer to the new section that keeps three rules the section does not hold. The outcomes are in the PR 314 description and on the story. The two owner-authored lines are named on the story, and neither file changed after the story's work began. |
| K7: guards | Verified | CI run 44102557377 on the PR head `c70ed3d` succeeded: 3085 tests passed, the private leak scan passed, all 18 skills validate, and opencode discovers every skill. The PR body links that run and the runs for every earlier head. At the target, `uv run --locked pytest -q` passes locally (3067 passed). |
| DoD: all AC met | Verified | K1 to K7 above. |
| DoD: unit and integration tests written and passing | Verified | `tests/test_read_source_rule.py` (K4) and the full suite (K7). |
| DoD: independently reviewed | Verified | PR 314 review 5940287854 is the review of record at `c70ed3d`, the merged head, by the reviewer and adjudicator `profile.review` names, with a clean verdict. |
| DoD: docs updated (if applicable) | Verified | The change is the documentation itself, in `shared/engineering-practice.md` and its generated copies. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | The full suite passes at the target and in CI. |

Closing decision: Done once this evidence merges.
