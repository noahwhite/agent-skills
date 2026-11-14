# SKL-270 QA evidence

## QA round 1

Date: 2026-11-14 UTC, independent QA round 1.
Path: `no-deployment`, selected by the merged `skills/qa-verification/scripts/select-path.py`, which printed `no-deployment` with and without `--recorded-path`.
Target: `main` at `c8ca6d0881dc5644a3dcee4f510d2764bab72d9c`, the squash merge of PR 248, whose reviewed head is `a93708fc3eff87a5f4224f59af10268cc3aa18d2`.
`git merge-base --is-ancestor` confirmed the merged commit on `origin/main`.
Environment: none; the profile sets `environments: []`, so no build SHA applies and the lanes are the repository, GitHub and the tracker.
Fixtures: none.
The raw output is attached to SKL-270 as `SKL-270-qa-round-1-assertions.txt`; there is no visual surface, so no screenshot applies.
The blockers SKL-162, SKL-269 and SKL-282 are Done.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: script | Verified | 92 of 92 black-box cases pass; details below. |
| AC2: unit tests | Verified | `tests/test_select_path.py` covers every clause; details below. |
| AC3: story-to-done | Verified | Step 1, Arguments and the step 5 report; details below. |
| AC4: other skills | Verified | "Select the path", "The run's path" and the step 12 note; details below. |
| AC5: repository guards | Verified | Every guard passed on the merged commit and in CI; details below. |
| AC6: docs and compatibility | Verified | Details below. |
| DoD: all acceptance criteria met | Verified | AC1 to AC6. |
| DoD: tests written and passing | Verified | AC2 and AC5. |
| DoD: independently reviewed | Failed | The review of record's adjudicator is not the profile's; details below. |
| DoD: docs updated | Verified | AC3, AC4 and AC6. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed: the path is `no-deployment`. |
| DoD: no critical bugs or regressions | Verified | CI passed on the reviewed head (run 43569240182) and on `main` (run 43569783775). |

Details:

- AC1:
  - A black-box probe ran each vendored copy as callers do, `python3 scripts/select-path.py` from the skill directory, over 29 cases per copy: all nine outputs, the precedence between them, the exit-16 cases and the exit-2 command lines.
  - Five profile discovery cases on the `qa-verification` copy confirmed the order `AGENT_SKILLS_PROFILE`, the repository `.agent-skills/profile.yaml`, then `~/.config/agent-skills/profile.yaml`, and exit 16 when none exists.
  - The three copies are mode `100644` and share one blob, with the generated header above the shebang.
  - `skills.json` lists `select-path.py` under `executables` for exactly `story-to-done`, `engineering-workflow` and `qa-verification`.
  - The script imports only the standard library and PyYAML, and its only subprocess is `git rev-parse`.
- AC2:
  - `tests/test_select_path.py` runs `shared/select-path.py` through `sys.executable` as a subprocess with `AGENT_SKILLS_PROFILE` set to a temporary profile, and never imports it.
  - It covers each output, each precedence pair, absent, null and `[]` environments, an unset spike label, wrong-case prefix and label, the exit-16 cases, an exit-2 command line, and the `skills.json` listing.
  - It passes on the merged commit (55 passed).
- AC3:
  - Step 1 takes the `done`, `blocked`, `canceled` and `duplicate` stops first, then runs the script, then routes deployment review to step 3 and other states to step 2.
  - For a story in deployment review it passes the latest step 12 note's exact `path:` line value as `--recorded-path`, and nothing otherwise.
  - It passes the tracker label names under the differing-team rule, asks the user on an `ask:` line accepting only the three values, and spawns no role until answered.
  - The todo list and closing report carry `path: <value>` or `path: unresolved`, and a role handback `ask:` line stops the run with `path: unresolved`.
- AC4:
  - `engineering-workflow` "Select the path" and `qa-verification` "The run's path" run the script in place of the replaced prose, passing a brief `path:` line as `--recorded-path`.
  - The step 12 handoff note carries the path as a line whose whole text is `path: <value>`, and `qa-verification` reads only that line from the note.
  - A skill invoked directly asks the user on `ask:`; a skill running as a story-to-done role stops and quotes the line in its handback.
- AC5:
  - On the merged commit, `uv run --locked pytest -q` passed (2337 passed), `scripts/vendor_shared.py --check` and the public leak scan exited 0, and `--require-private` exited 2 locally with "leak scan INCOMPLETE", as decided.
  - `skills-ref validate` passed for all 18 skills, and `bash scripts/smoke-opencode.sh` exited 0.
  - CI runs 43569240182 and 43569783775 passed `checks`, which runs the leak scan with `--require-private`, and `discovery`.
  - The pin updates in `tests/test_no_deployment_path.py` and `tests/test_story_to_done.py` replace only the pins on the replaced prose.
- AC6:
  - `shared/README.md` names `select-path.py` among the shared non-Markdown files and keeps the substring "non-Markdown files are `resolve-model-role.py`, the model-role resolver".
  - The `compatibility:` lines of `story-to-done`, `engineering-workflow` and `qa-verification` name python3 and PyYAML>=6.
- DoD, independently reviewed:
  - Review 5902513980 on PR 248 is `COMMENTED`, its `commit_id` and first line name the merged head, and it reports no valid findings.
  - Its adjudicator is DeepSeek V4 Pro (`deepseek/deepseek-v4-pro`), while `profile.review.adjudicator` at that head is DeepSeek V4.1 Flash (`deepseek/deepseek-flash`).
  - `references/code-review.md` allows a different adjudicator only when the user asks and forbids a silent substitution; neither the story nor the PR records such a request.

Closing decision: SKL-270 returns to In Progress for the independently reviewed item, with the fix owned by `engineering-workflow`.
