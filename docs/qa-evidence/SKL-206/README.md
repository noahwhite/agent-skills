# SKL-206 QA evidence

## Round 1

Date: 2026-11-07 UTC, independent QA round 1.
Story: SKL-206 - tell delegated agents to use the configured git identity and never pass git `-c` flags.
Build under test: `main` at `f7171eb99bf0d3cc3c7635946c76aead8592cf10`, the squash merge of PR 157, whose reviewed head is `5366ec3ebb4784f7502263235fb7415c92d84300`.
Environment: the profile lists no environments, so every item was checked on the repository and tracker lanes, in a detached worktree of the build.
Fixtures: none.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-206 as `SKL-206-qa-round-1-assertions.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| S1: base rule | Verified | The Always list of "Commits and signing" in `shared/github.md` names `commit`, `commit --amend`, `merge`, `rebase`, `cherry-pick`, `revert` and `am`, says the rule holds whether or not `profile.git.signed_commits` is true, bans `-c user.name`, `-c user.email`, `--author`, `GIT_AUTHOR_*`, `GIT_COMMITTER_*` and `git config` writes of `user.name` or `user.email` at any scope, keeps `-m` and `-F`, and puts workflow files out of scope. The signed-commits list bans `-c user.signingkey`, `-c gpg.*` and `-c commit.gpgsign` and says to rely on the configured signing. |
| S2: fault path | Verified | The Always list says a missing configured identity is a configuration fault, and that on any configuration fault the agent stops, does not override per command, does not write git config, makes no further commits and reports the fault. The signed-commits list makes a failed `check-signing-key.sh` and a pushed commit with `verified` false configuration faults. "On a non-zero exit, stop and fix the configuration" no longer appears, and "Never commit with a per-commit key override" appears once. |
| S3: briefs carry it | Verified | One git-rule bullet sits next to the secrets rule bullet (and the attribution rule, where the list has it) in `story-to-done` steps 2 and 3, `persona-staff-engineer` and `persona-staff-devops`, and the `engineering-workflow` fixer prose carries the same sentence. `grep -l 'with the git identity already configured' skills/*/SKILL.md` lists exactly those four files, and `grep -c` on `skills/story-to-done/SKILL.md` prints 2. |
| S4: no consumer literal | Verified | The S4 scan over the lines PR 157 added under `shared` and `skills` prints nothing, with grep exit status 1. |
| S5: vendored copies in step | Verified | `python3 scripts/vendor_shared.py --check` exits 0, and the S3 phrase is in 13 of the 13 `skills/*/references/github.md` copies. `uv run --locked pytest -q` reports 1300 passed with exit 0. `uv run --locked python scripts/leak_scan.py` exits 0, reporting INCOMPLETE because this container loads no private patterns; CI run 42415037991 on the build ran it with `--require-private` and succeeded. The CI loop of `skills-ref validate` exits 0 for all 18 skills. |
| S6: observed | Not met | No story-to-done run on a throwaway story is recorded. The PR 157 body says "S6 (observed run): not yet done", no PR 157 comment records a run, and no throwaway SKL story exists. The linked consumer story is in Backlog, and its refinement says the end-to-end check stays with SKL-206 S6. |
| S7: gate | Not met | The PR 157 body records the S5 commands and outputs, the S4 output and the head `5366ec3`, CI run 42414771579 on that head succeeded, and the review of record's `commit_id` and first line both name `5366ec3`, with its one finding ruled invalid. The S6 evidence that S7 requires is absent from the PR body. |
| DoD1: all acceptance criteria met | Not met | S6 and S7 are not met. |
| DoD2: tests written and passing | Verified | `tests/test_git_identity_rule.py` reports 19 passed, and the full suite 1300 passed. |
| DoD3: independently reviewed | Verified | The PR 157 review of record at `5366ec3ebb4784f7502263235fb7415c92d84300` is by Codex GPT-6 Sol with DeepSeek V4 Pro adjudicating, the profile's pair, posted before the merge. |
| DoD4: docs updated | Verified | The change is the documentation itself: `shared/github.md`, four `SKILL.md` files and the 13 generated copies. |
| DoD5: verified in a deployed environment | Not applicable | The profile lists no environments; the consumer-run observation is S6. |
| DoD6: no critical bugs or regressions | Verified | The full suite passes, and CI run 42415037991 on the build succeeded. |

Incidental, non-blocking: the first CI run on the PR 157 head, 42414331232, failed in the `discovery` job because `opencode` kept returning a truncated skill list for the global-agents layout until the deadline; run 42414771579 on the same head passed.
The same failure hit the global-opencode layout in run 42416140490 on this evidence PR.

Closing decision: In Progress, because S6 and S7 as written need an observed story-to-done run on a throwaway story, recorded in PR 157, and none exists.

## Round 2

Date: 2026-11-07 UTC, independent QA round 2, after the rework for S6 and S7.
Build under test: `main` at `f7171eb99bf0d3cc3c7635946c76aead8592cf10`, unchanged since round 1; PR 157 head `5366ec3ebb4784f7502263235fb7415c92d84300`.
Environment: none, as in round 1; every item was checked on the repository, tracker, transcript and GitHub lanes, in a detached worktree of the build.
Fixtures: throwaway story SKL-208 (Canceled) and the transcript of the senior engineer delegated for it.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-206 as `SKL-206-qa-round-2-assertions.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| S1: base rule | Verified | Re-checked at `f7171eb`: each S1 phrase appears once in "Commits and signing" of `shared/github.md`. |
| S2: fault path | Verified | Re-checked at `f7171eb`: "A missing configured identity is a configuration fault", the stop line, both signed-commits fault lines and "Never commit with a per-commit key override" appear once each, and "On a non-zero exit, stop and fix the configuration" appears 0 times. |
| S3: briefs carry it | Verified | `grep -l 'with the git identity already configured' skills/*/SKILL.md` lists exactly the four files, `grep -c` on `skills/story-to-done/SKILL.md` prints 2, and each brief bullet sits next to the secrets rule bullet. |
| S4: no consumer literal | Verified | The S4 scan over `5409e40...f7171eb -- shared skills` prints nothing, with grep exit status 1. |
| S5: vendored copies in step | Verified | `vendor_shared.py --check` exit 0; the S1 phrase is in 13 of 13 `skills/*/references/github.md`; `uv run --locked pytest -q` 1300 passed, exit 0; `leak_scan.py` exit 0 (INCOMPLETE locally, no private patterns; push CI run 42415037991 ran it with `--require-private` and passed); `skills-ref validate` exit 0 for all 18 skills. |
| S6: observed | Not met | The run recorded for S6 is not a story-to-done run. The throwaway story SKL-208 asked for two commits and a push with no PR, and the coordinator composed the senior engineer's brief by hand from `main` because the installed skill copy had not synced. So `engineering-workflow` did not run to deployment review, and the story-to-done step 3 QA brief, which also carries the git rule, was never exercised. What was observed holds: the container's global git config sets `user.name`, `user.email`, `gpg.format`, `commit.gpgsign` and an SSH default key command (key names read, values not shown); the brief carries the merged git-rule bullet verbatim; the transcript holds 7 Bash calls, 2 of them commit-creating (`git -C <repo> commit -m ...` and `git -C <repo> commit -am ...`), with 0 matches for any S1 item; and `c50d6ffa8f67c0eb9f78bcff07dd3484a6f8b91b` and `889286da4b50e457fa44e40e6ddf1efc479f8f1f` both report `verified: true`, reason `valid`. |
| S7: gate | Not met | The PR 157 body records the S5 commands and outputs, the S4 output, the head `5366ec3`, and an "S6 (observed run)" section, but that section records the run above, which does not meet S6. CI run 42414771579 on `5366ec3` succeeded, and the review of record has `commit_id` and first line `5366ec3`, with its one finding ruled invalid. |
| DoD1: all acceptance criteria met | Not met | S6 and S7 are not met. |
| DoD2: tests written and passing | Verified | The full suite reports 1300 passed at `f7171eb`. |
| DoD3: independently reviewed | Verified | Unchanged from round 1: the PR 157 review of record at `5366ec3` is by Codex GPT-6 Sol with DeepSeek V4 Pro adjudicating, the profile's pair. |
| DoD4: docs updated | Verified | Unchanged from round 1. |
| DoD5: verified in a deployed environment | Not needed | The profile lists no environments; S6 is the runtime observation. |
| DoD6: no critical bugs or regressions | Verified | Full suite green, and push CI run 42415037991 on `f7171eb` succeeded. |

Notes, non-blocking:
- The PR 157 body says the scanned transcript has 9 Bash calls; it has 7 (plus 3 Write, 1 Skill and 1 hand-back call), and the conclusion is the same.
- The `discovery` job failure from round 1 recurs: runs 42416754248, 42417057949 and 42417329558 on this PR's round 1 head and run 42418896884 on the first round 2 head failed it, each with `skill API returned undecodable JSON: Unterminated string` at about character 242,800, in the project-claude, global-agents or global-claude layout.

Closing decision: In Progress, because S6 as written needs a story-to-done run on a throwaway story, and the recorded run is a hand-composed single-agent brief that exercised neither `engineering-workflow` to deployment review nor the step 3 QA brief; S7 and DoD1 follow S6.

## Round 3

Date: 2026-11-07 UTC, independent QA round 3, after the second rework for S6 and S7.
Build under test: `main` at `c5c745a2d586579332377067035230336ebe3bc8`, which contains the PR 157 squash `f7171eb99bf0d3cc3c7635946c76aead8592cf10`; PR 157 head `5366ec3ebb4784f7502263235fb7415c92d84300`.
Environment: none, as in rounds 1 and 2; every item was checked on the repository, tracker, transcript and GitHub lanes, in a detached worktree of the build.
Fixtures: throwaway story SKL-211 (Done), its PRs 160 and 161, and the transcripts of the four agents its story-to-done run delegated.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-206 as `SKL-206-qa-round-3-assertions.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| S1: base rule | Verified | Each S1 phrase appears once in "Commits and signing" of `shared/github.md` at `c5c745a`. |
| S2: fault path | Verified | Both fault lines, the stop line and "Never commit with a per-commit key override" appear once each; "On a non-zero exit, stop and fix the configuration" appears 0 times. |
| S3: briefs carry it | Verified | `grep -l 'with the git identity already configured' skills/*/SKILL.md` lists exactly the four files, and `grep -c` on `skills/story-to-done/SKILL.md` prints 2. |
| S4: no consumer literal | Verified | The S4 scan over `f7171eb^..f7171eb -- shared skills` prints nothing, with grep exit status 1. |
| S5: vendored copies in step | Verified | `vendor_shared.py --check` exit 0; 13 of 13 copies; `uv run --locked pytest -q` 1300 passed, exit 0; `leak_scan.py` exit 0 (INCOMPLETE locally, no private patterns); `skills-ref validate` exit 0 for all 18 skills. |
| S6: observed | Verified | The installed `story-to-done` skill is identical to `main`, and the senior engineer and QA briefs carry its git-rule bullet verbatim. The container's global git config sets identity and SSH signing (key names read, values not shown). The four delegated agents' transcripts hold 45, 98, 25 and 5 distinct Bash calls, 3 of them commit-creating, with 0 S1-forbidden actions; the scanner flagged 10 of 10 forbidden samples in a self-test. The three agent commits and the squash merges of PRs 157, 160 and 161 all report `verified: true`, reason `valid`. |
| S7: gate | Verified | The PR 157 body records the S5 commands and outputs, the S4 output, the head `5366ec3`, and the SKL-211 run with no identity or key value. CI run 42414771579 on `5366ec3` succeeded, and review of record 5815043900 has `commit_id` and first line `5366ec3`, with its one finding ruled invalid. |
| DoD1: all acceptance criteria met | Verified | S1 to S7. |
| DoD2: tests written and passing | Verified | The full suite reports 1300 passed at `c5c745a`. |
| DoD3: independently reviewed | Verified | Unchanged from round 1. |
| DoD4: docs updated | Verified | Unchanged from round 1. |
| DoD5: verified in a deployed environment | Not needed | The profile lists no environments; S6 is the runtime observation. |
| DoD6: no critical bugs or regressions | Verified | Full suite green, and the `checks` and `discovery` jobs succeeded on `c5c745a`. |

Notes, non-blocking:
- The `discovery` job failure from rounds 1 and 2 still recurs; it failed on this PR's previous head `ef24a8d` in run 42419209267.
- SKL-211's description says its content is removed after the evidence is recorded, but `docs/throwaway/s6-note.md` and `docs/qa-evidence/SKL-211/` remain on `main`.

Closing decision: Done, once this evidence merges.
