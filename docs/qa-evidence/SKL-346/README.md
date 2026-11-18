# SKL-346 QA evidence

## QA round 1

Date: 2026-11-18 UTC, independent QA round 1.
Target: `main` at `59a8a3caae33233c14604a4f256147e410fb4501`, the squash merge of PR 337, whose reviewed head is `70e3e493f3db33ad9e3f96ca22a21c72111a855a`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
The PR's ten files are identical at the reviewed head and at the target.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Dependency: SKL-178 is Done and its merge `3385097` is an ancestor of the target.
Fixtures: a detached worktree at the target, and the three engineer briefs (deployed, no-deployment, spike) rendered there with `render-brief.py`.
No test suite ran locally, on the user's instruction; the pytest guard is evidenced by CI run 44230573752 only.
The raw output is attached to SKL-346 as "QA round 1: AC 4 and guard checks against 59a8a3c (raw output)"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC 4: ledger section, header row and `No rounds yet.` | Verified | `skills/story-to-done/SKILL.md` step 2 and step 4 and the three engineer templates carry `## Arbitration ledger`, the header row `\| round \| kind \| head \| engineer \| reviewer agent \| reviewer model \| report \|` and `No rounds yet.`; each rendered engineer brief carries them once. |
| AC 4: round definition | Verified | Step 2 and each template define a round as one arbitration or one escalation verification of one head; a re-run at an unchanged head and any changed head (step 4 fix, rebase, merge, force-push) start a new round. |
| AC 4: one entry per round and the two kinds | Verified | Step 2 and each template require one entry per round, QA-triggered fix rounds included, of kind `arbitration` or `escalation-verification`; step 4 restates the kinds. |
| AC 4: entry fields and provenance | Verified | The engineer gives round, kind, full head SHA and one report value (an absolute retained-report path, or an absolute path or `https://` URL for a verifier report) and writes `-` in the identity cells; the coordinator fills the engineer cell from the launched seat and the reviewer cells from the `ARBITER-AGENT:` and `ARBITER-MODEL:` lines or the `VERIFIER:` line, the header names the SKL-178 pipeline script writes. |
| AC 4: retained-report directory | Verified | The handback names `<git common dir>/adversarial-pipeline/arbitration-rounds` from `git rev-parse --path-format=absolute --git-common-dir`, the directory the pipeline script retains into. |
| AC 4: numbering, resume and missing-ledger stop | Verified | Rounds are contiguous from 1 per PR; step 2 and step 4 put the held ledger into every brief, on a resume and a new launch, and stop before relaunching when a PR with earlier rounds has no ledger; the engineer returns prior entries unchanged. |
| AC 4: no new-head review waived | Verified | Step 2 and each template require a separate clean, neutral arbiter for every changed head, recorded as the next entry. |
| AC 4: clause in all five places and the SKL-328 rebase | Verified | All five places carry the clause; SKL-328 is in Backlog, so this story landed first and the rebase falls to SKL-328. |
| AC 4: Verify stage lines | Verified | `skills/engineering-workflow/SKILL.md` item 2 of "Escalation: the gated two-lens loop" has the verifier write `VERIFIED-HEAD: <full head SHA>` and `VERIFIER: <agent name> <model id>`, each on its own line of its report. |
| AC 4: `--model` verbatim | Verified | Step 2, each template and each rendered brief pass `profile.review.pre_pr.arbiter.model` verbatim to `--model`. |
| AC 4: tests | Verified | A read of the `tests/test_story_to_done.py` diff shows assertions for the heading, the parsed header columns, the empty line and kinds in every named place, the `--model` instruction, the two Verify stage lines and the rendered briefs. |
| Guards: `uv run --locked pytest -q` | Verified (CI only) | The `checks` job of CI run 44230573752 on the reviewed head succeeded; no local suite ran. |
| Guards: leak scan with `--require-private` | Verified | The same job's leak scan step succeeded. |
| Guards: `skills-ref validate` | Verified | Both `skills/story-to-done/` and `skills/engineering-workflow/` report "Valid skill" at the target, and the CI validate step succeeded. |
| Guards: `bash scripts/smoke-opencode.sh` | Verified | At the target, opencode discovered all 18 skills in each of the six layouts, and the CI `discovery` job succeeded. |
| DoD: all acceptance criteria met | Verified | AC 4 and the guards are verified above. |
| DoD: unit and integration tests written and passing | Verified (CI only) | The new tests passed in CI run 44230573752. |
| DoD: independently reviewed | Verified | PR 337 has its review of record at `70e3e49`, the merged head, by GPT-6.1 Sol and DeepSeek V4.1 Flash, the reviewer and adjudicator the profile names. |
| DoD: docs updated (if applicable) | Verified | `skills/story-to-done/SKILL.md`, the three engineer brief templates and `skills/engineering-workflow/SKILL.md`. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | CI passed on the reviewed head, and the validator and smoke checks pass at the target. |

Closing decision: Done once this evidence merges.
