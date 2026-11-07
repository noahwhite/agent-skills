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
| S6: observed | Not met | No story-to-done run on a throwaway story is recorded. The PR 157 body says "S6 (observed run): not yet done", no PR 157 comment records a run, and no throwaway SKL story exists. OFF-1420 is in Backlog, and its refinement says the end-to-end check stays with SKL-206 S6. |
| S7: gate | Not met | The PR 157 body records the S5 commands and outputs, the S4 output and the head `5366ec3`, CI run 42414771579 on that head succeeded, and the review of record's `commit_id` and first line both name `5366ec3`, with its one finding ruled invalid. The S6 evidence that S7 requires is absent from the PR body. |
| DoD1: all acceptance criteria met | Not met | S6 and S7 are not met. |
| DoD2: tests written and passing | Verified | `tests/test_git_identity_rule.py` reports 19 passed, and the full suite 1300 passed. |
| DoD3: independently reviewed | Verified | The PR 157 review of record at `5366ec3ebb4784f7502263235fb7415c92d84300` is by Codex GPT-6 Sol with DeepSeek V4 Pro adjudicating, the profile's pair, posted before the merge. |
| DoD4: docs updated | Verified | The change is the documentation itself: `shared/github.md`, four `SKILL.md` files and the 13 generated copies. |
| DoD5: verified in a deployed environment | Not applicable | The profile lists no environments; the consumer-run observation is S6. |
| DoD6: no critical bugs or regressions | Verified | The full suite passes, and CI run 42415037991 on the build succeeded. |

Incidental, non-blocking: the first CI run on the PR 157 head, 42414331232, failed in the `discovery` job because `opencode` kept returning a truncated skill list for the global-agents layout until the deadline; run 42414771579 on the same head passed.

Closing decision: In Progress, because S6 and S7 as written need an observed story-to-done run on a throwaway story, recorded in PR 157, and none exists.
