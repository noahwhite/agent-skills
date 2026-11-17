# SKL-178 QA evidence

## QA round 1

Date: 2026-11-17 UTC, independent QA round 1.
Target: `main` at `3385097240910fd0e1453a3e207ffef08af26680`, the squash merge of PR 322, whose reviewed head is `9ef5a027d855cff8b4f4c5255bf47aad2a17feba`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
The PR's five files are identical at the reviewed head and at the target; the only other difference in the pipeline skill is a vendored `references/todo-tracking.md` line that another story landed on `main` first.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line, so no environment or build SHA applies.
Fixtures: a detached worktree at the target, and a throwaway two-commit git repository with one linked worktree that the QA probe built in a scratch directory.
The raw output is attached to SKL-178 as "QA round 1: AC 6 end-to-end CLI probe against 3385097, 32 assertions (raw output)" and "QA round 1: target, tests, CI, review of record and docs checks (raw output)"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC 6: identity lines | Verified | `run arbitrate` and `record arbitrate` both write `ARBITER-AGENT`, `ARBITER-MODEL` (the `--model` value verbatim) and `ARBITER-HEAD` (the full 40-hex HEAD) as lines 2 to 4 after an unchanged `REVIEW-RAN: yes`, with the body unchanged below them and the stamp covering the headed report. |
| AC 6: first line not exact | Verified | A `REVIEW-RAN: no` report exits 17 with no `ARBITER-` line, no stamp and no new retained file; the tests also cover trailing space, tab, CR and NUL on both flows. |
| AC 6: `--agent` and `not-supplied` | Verified | `--agent` wins over `ADVERSARIAL_AGENT`, the variable alone supplies the name, and a `record arbitrate` with neither `--agent` nor `--model` writes `not-supplied` in both fields. |
| AC 6: retention directory | Verified | The retained path is under the absolute `git rev-parse --git-common-dir` plus `adversarial-pipeline/arbitration-rounds`; an arbitration run in a linked worktree retains into the same directory, not its own `--git-path`, and removing that worktree keeps the copy. |
| AC 6: retention filename and no-clobber | Verified | Files are named `round-<UTC timestamp>-<full HEAD SHA>-<first 12 hex of the report sha256>-<n>.md` and are read-only; two byte-identical arbitrations at one head under a fixed clock leave `-1` and `-2` with no temporary file left; the script publishes with `ln -T` and retries the next `<n>` on an existing name, and a write or publish failure exits 21 with nothing accepted (test-covered). |
| AC 6: stderr path, re-run and cleanup | Verified | Each accepted arbitration prints `Retained arbitration report -> <absolute path>` on stderr while `run` stdout equals the artifact; a `hunt` re-run discards `phase3-arbitration.md` and `cleanup` removes the checkout, and every retained copy stays. |
| AC 6: `record arbitrate` at the reviewed head | Verified | The pipeline `SKILL.md` states that `record arbitrate` must run at the reviewed head. |
| AC 6: docs | Verified | The new "Arbiter identity and retained rounds" section of the pipeline `SKILL.md` and the script header document the three lines, the `not-supplied` rule, the retention directory and filename, the stderr path, and `--agent` with its precedence over `ADVERSARIAL_AGENT`. |
| AC 6: test | Verified | `tests/test_pipeline_arbiter_identity.py` covers every case the AC lists and passes at the target (42 passed, none skipped). |
| DoD: all AC met | Verified | AC 6 is verified above. |
| DoD: unit and integration tests written and passing | Verified | The AC 6 test above passes, the full suite passes at the target (`uv run --locked pytest -q`, 3172 passed), and CI run 44174758301 on the target and the `checks` and `discovery` jobs of run 44173515955 on the reviewed head succeeded. |
| DoD: independently reviewed | Verified | PR 322 review 5946410548 is the latest review of record, at `9ef5a02`, the merged head, by GPT-6.1 Sol and DeepSeek V4.1 Flash, the reviewer and adjudicator the profile names, with no findings. |
| DoD: docs updated (if applicable) | Verified | The pipeline `SKILL.md` and the script header, as in the AC 6 docs row. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | The full suite passes at the target and CI passes on it. |

Closing decision: Done once this evidence merges.
