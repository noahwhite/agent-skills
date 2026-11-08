# SKL-207 QA evidence

## Round 1

Date: 2026-11-08 UTC, independent QA round 1.
Build under test: `main` at `69f3d5e99754df83dd5ad1a6eb6fe62d8065a41f`, the squash merge of PR 159, whose reviewed head is `73fe55dfd20ec9c7c95a6169776cc53848422acc`.
Environment: the profile lists no environments, so every item was verified against `main` and its CI.
Tool versions: git 2.43.0, uv 0.13.7, and `skills-ref` from agentskills at `69ef37e9` as CI pins it.
Fixtures: throwaway story SKL-213 and branch `throwaway/SKL-213-s5-observed`, which the S5 run used.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-207 as the "SKL-207 QA round 1 raw assertion output" attachment.

| Item | Verdict | Evidence |
|---|---|---|
| S1: base rule | Verified | `shared/github.md` lines 13 to 16 are one bullet directly after the `git -C` bullet. Line 13 is one sentence holding the phrase and naming the forms the permission checker cannot verify. Lines 14 to 16 forbid the three forms and give the three replacements the AC names. The bullet says nothing about pipes, heredocs or `cd` chains. |
| S2: briefs carry it | Verified | `grep -lF` over `skills/*/SKILL.md` lists exactly engineering-workflow, persona-staff-devops, persona-staff-engineer and story-to-done, and the story-to-done count is 2. Each list bullet sits directly after the bullet holding the secrets rule, including the combined secrets and Track-your-work bullet in story-to-done step 3. The Fix stage in `skills/engineering-workflow/SKILL.md` line 120 has the one sentence. The lines SKL-206 added in `f7171eb` hold the phrase 0 times. |
| S3: no consumer literal | Verified | The 14 lines added to `shared/github.md`, the four `SKILL.md` files and the workflow script match no email address, account, token variable name or key. They use the placeholders `$SECRET`, `$W`, `$SHA` and `<path>`. |
| S4: vendored copies in step | Verified | `vendor_shared.py` leaves the tree unchanged and `--check` exits 0. `grep -lF` over `skills/*/references/github.md` lists the 13 named paths. `git diff --name-only fc46ce0 69f3d5e` lists the 20 files the widened AC names. `pytest -q` reports 1340 passed, `leak_scan.py` exits 0, and the CI `skills-ref validate` loop reports all 18 skills valid. |
| S5: observed | Verified | The delegated Claude Code agent's transcript shows a brief holding the story-to-done shell-rule bullet. Its 5 Bash calls from the commit through the push verification match the PR 159 record verbatim and use none of the three forms. No call returned an error or a denial. The remote branch head is `3ab25f0cb08cbf6e88732a670f6483a182c1ae15`, and GitHub reports its signature verified. |
| S6: gate | Verified | The PR 159 body records the S4 commands and results, the S5 record and the head `73fe55d`. The `checks` and `discovery` runs succeeded on `73fe55d`. The latest review of record is on `73fe55d` with no defects, and no commit followed it. |
| DoD1: all acceptance criteria met | Verified | S1 to S6 are verified. |
| DoD2: tests written and passing | Verified | `tests/test_shell_command_rule.py` and the SKL-206 test pass (30 tests), and the full suite reports 1340 passed. |
| DoD3: independently reviewed | Verified | The review of record on PR 159 (Codex GPT-6 Sol reviewer, DeepSeek V4 Pro adjudicator) is on `73fe55d`, the merged head. |
| DoD4: docs updated | Verified | The change is the guidance itself, and the vendored copies are in step. |
| DoD5: verified in a deployed environment | Not needed | The profile lists no environments; `main` push run 42484526132 at `69f3d5e` succeeded. |
| DoD6: no critical bugs or regressions | Verified | `main` CI and the full suite are green. |

Closing decision: Done, once this evidence merges.
