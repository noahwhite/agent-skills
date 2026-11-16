# SKL-275 QA evidence

## QA round 1

Date: 2026-11-15 UTC, independent QA round 1.
Target: `main` at `192070793c871937e817be1c8f4105af8650a01a`, the squash merge of PR 265, whose reviewed head is `a94821cddfde2ffba495185636e80001f9ebf591`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Fixtures: none.
Blockers SKL-296 (`6838b35`), SKL-156 (`f9b6659`), SKL-155 (`54320bc`) and SKL-164 (`0e2a4ef`, `2246531`) are Done, and their merges are ancestors of the target.
The raw output is attached to SKL-275 as "SKL-275 QA round 1 probe at target 1920707" and "SKL-275 QA round 1 path, target, CI and review output"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: case directory and README differences | Verified | `skills/story-to-done/evals/pending-ruling-not-sent-to-engineer/` holds every contract file with `kind: discriminating` and the same top-level `case.yaml` keys as `qa-unfinished-own-steps`; the evals README section "Where `pending-ruling-not-sent-to-engineer` differs from the `qa-unfinished-own-steps` layout" lists the multi-round fixtures, the user message channel and the `control` field. |
| AC2: full commit ids | Verified | `candidate` is `6838b357652260562f481f747cf5e653d0f4e7c8` and `baseline` is `9bd3e1666c5ba17aa560424e0d402710aa765c75`, equal to `git rev-parse` of `6838b35` and `9bd3e16`, and both are reachable on `origin/main`. |
| AC3: phrase ban, fixtures, runtime, grader inputs, control | Verified | Details below. |
| AC4: grader fixtures and tests | Verified | The grader exits 1 on all five breaking fixtures, 0 on both keeping fixtures and 2 on a run directory without `actions.jsonl`; `tests/test_pending_ruling_case.py` passes 76, and a banned phrase added to `split-verdict/scenario.md` makes `test_no_file_the_agent_reads_names_the_banned_phrases` fail. |
| AC5: guards | Verified | At the target the full suite passes 2549, the public leak scan reports INCOMPLETE only for missing private patterns, `skills-ref validate` reports all 18 skill directories valid, and `smoke-opencode.sh` discovers all 18 skills; CI `checks` and `discovery` passed on the PR head (run 43709933095) and on `main` (run 43710584959). |
| DoD: all acceptance criteria met | Verified | AC1 to AC5. |
| DoD: tests written and passing | Verified | The 76 case tests and the full suite at the target. |
| DoD: independently reviewed | Verified | Details below. |
| DoD: docs updated | Verified | The evals README section and the case's `rerun.md`. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed: the run is on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | CI `checks` and `discovery` passed on `main` at the target, and the full local suite passed. |

Details:

- AC3:
  - `prompt.md`, `rerun.md`, both `scenario.md` files and `runtime/story-runtime.md` contain no `pending owner ruling` or `pending ruling` in any letter case and no term naming a party the item should go to.
  - Each `split-verdict` QA-round fixture records AC4 as `pending owner ruling`, with the quoted AC4 text, Reading 1 with verdict failed, Reading 2 with verdict verified, and the product owner as owner.
  - `runtime/story-runtime.md` documents `user-message --message FILE` and `engineer-launch --label LABEL --message FILE` with symmetric descriptions, `run.sh` copies the runtime and its doc into every scenario run, and the runtime records each send in `actions.jsonl` with its text in `messages.json`.
  - The grader opens only `actions.jsonl` and `messages.json`, and the split-verdict breaking fixtures cover a missing user message, an engineer brief, a QA brief and a carried hand-back.
  - `plain-failure` carries the `control` field in `case.yaml`; its first QA round has one failed item (AC2) and no pending item, and its keeping fixture passes only when AC2 reaches a senior-engineer launch brief.
- DoD, independently reviewed:
  - Reviews 5910427209 at `8d8dbce` and 5910471982 at `b61ac4c` on PR 265 are `COMMENTED`, and their valid findings were fixed in `b61ac4c` and `a94821c`.
  - Review 5910500872 is `COMMENTED`, its `commit_id` and first line name the merged head `a94821cddfde2ffba495185636e80001f9ebf591`, and it was submitted at 11:46:50Z, before the 11:47:03Z merge.
  - All three name GPT-6.1 Sol (`gpt-6.1-sol`) as reviewer and DeepSeek V4.1 Flash (`deepseek/deepseek-flash`) as adjudicator, the seats in `profile.review` at the target.

Closing decision: Done, once this evidence merges.
