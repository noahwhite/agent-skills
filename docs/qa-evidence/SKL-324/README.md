# SKL-324 QA evidence

## QA round 1

Date: 2026-11-17 UTC, independent QA round 1.
Target: `main` at `1f8d6338301f9e5966f6b6ddbf54104b4fe894ce`, the squash merge of PR 316, whose reviewed head is `938f2dba3a947b9c5dfa29f37e238d39e44b0dab`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`, and `git diff --stat` between the reviewed head and the target is empty.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
AC2 baseline: `skills/story-to-done/SKILL.md` steps 2 and 3 at the merge-base `ee17dfb64b44a59f4a5886177e3354ff5817e85c`.
Fixtures: a detached worktree at the target; every render wrote only into throwaway scratch directories, and the failure cases ran on a canary copy of the skill.
The raw output is attached to SKL-324 as "QA round 1: AC1-AC5 CLI probe, 238 assertions (raw output)" and "QA round 1: four guards, CI, AC2 baseline comparison, AC12 checks and review of record (raw output)"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: render | Verified | All three engineer paths and QA rounds 1, 2 and 12 on every path exit 0, print only the absolute brief path, and write the role file in the role directory; a re-render is byte-identical and replaces the file by rename, and other role directories are untouched. |
| AC2: content | Verified | No open `{{` token remains, each brief has one exact `path:` line, copied placeholders such as `$SECRET`, `$(...)` and `--match-head-commit <full reviewed SHA>` survive verbatim, link values are never re-expanded, and every `references/<name>.md` mention is absolute and exists. Every baseline sentence is present in each render, except the coordinator instructions AC2 requires resolved, each matched to its resolved text. |
| AC3: one source | Verified | The merge, git and shell rules each occur once across the templates and once in every render. |
| AC4: fail closed | Verified | 45 argument, pattern, scratch, symlink and missing-directory cases, a missing template, a read-only role directory and an output path that is a directory each exit non-zero with one `render-brief.py:` stderr line, empty stdout, no traceback, no canary text and no change. |
| AC5: no other content | Verified | The script imports only the standard library, uses no environment, stdin, subprocess or network, renders identically under an empty and a noisy environment, and its parser's argument set is the AC1 list. |
| AC9: tests, slice A | Verified | `tests/test_render_brief.py` holds the CLI render tests, one parametrized case per AC4 failure, the AC3 count test, the AC5 argument-set test, the absolute-reference test and the two hash pins; it passes with `test_signing_key.py` and `test_skills.py` (328 passed). |
| AC11: guards | Verified | At the target `uv run --locked pytest -q` passes 3063, the pinned `skills-ref validate` reports 18 of 18 valid, and `smoke-opencode.sh` discovers all 18 skills in 6 layouts. CI run 44086932407 on the target and CI run 44085995775 on the reviewed head, private leak scan included, succeeded. |
| AC12: templates | Verified | The ten templates live in `skills/story-to-done/assets/` of a skill the validator accepts, hold no em dash and no Markdown link, are walked by `tests/test_skills.py`, and the script imports only the standard library. |
| DoD: all AC met | Verified | Every AC in this slice is verified above. |
| DoD: unit and integration tests written and passing | Verified | AC9 and AC11. |
| DoD: independently reviewed | Verified | PR 316 review 5938651821 is a review of record at `938f2db`, the merged head, by the reviewer and adjudicator the profile on `main` names, with a clean verdict. |
| DoD: docs updated (if applicable) | Correct by design | This slice adds the script, the templates and the tests; the `SKILL.md` steps that call the script belong to SKL-328. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | The full suite passes at the target and in CI. |

Closing decision: Done once this evidence merges.
