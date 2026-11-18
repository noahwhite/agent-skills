# SKL-276 QA evidence

## QA round 1

Date: 2026-11-18 UTC, independent QA round 1.
Path: `no-deployment`, selected by `select-path.py` with the story's title, its two labels and the recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `6a132adced154b02cb57485b4d339ec0c027f8a1` on `main`, the squash merge of PR 333, whose reviewed head is `382a29ec3c5d1484ead0a8dcff10a5b31548ed92`.
`git merge-base --is-ancestor` confirmed the target on `origin/main`, and `git diff 382a29ec 6a132ad` touches only `docs/qa-evidence/SKL-363/README.md`, so every file of the PR is the reviewed file.
Owner constraint for this round: no test suite was run; the evidence is the merged code, direct invocations of the installed hook copy on hand-made payloads in a temporary state, config and home directory, `scripts/vendor_shared.py`, and the CI runs that ran automatically.
Fixtures: a throwaway worktree at the target, and the committed transcript fixtures `transcript-with-task-tools.jsonl` and `transcript-without-task-tools.jsonl` as session transcripts.
The raw output is attached to SKL-276 as "SKL-276 QA round 1 AC1 hook probe output" and "SKL-276 QA round 1 repository, vendoring and CI evidence"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: update cadence | Verified | 42 of 42 direct hook checks pass, listed below. |
| AC2: tests | Verified | Cases (a) to (k), the fixture and the mutation rows are in the merged diff; CI ran them green. |
| AC3: compatibility and vendoring | Verified | The only removed test line is replaced by a superset; vendoring is a no-op and `--check` exits 0. |
| AC4: README | Verified | Every required statement is present; the hooks block and removal instructions are untouched. |
| AC5: session run | Not covered, owner action | The owner runs one fresh interactive session; no scan is on the story yet. |
| AC6: repository guards | Verified | CI run 44216589191 on `382a29ec` succeeded; `vendor_shared.py --check` exits 0 on that head. |
| DoD: all acceptance criteria met | Not covered | AC5 is outstanding. |
| DoD: unit and integration tests written and passing | Verified | 3268 passed in CI on the PR head. |
| DoD: independently reviewed | Verified | Review of record on `382a29ec`, the merged head. |
| DoD: docs updated (if applicable) | Verified | README todo enforcer section and the module docstring. |
| DoD: verified in a deployed environment (if needed) | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | No defect found in the probe or the diff read; the full suite and every guard passed in CI. |

## Evidence per item

AC1: the probe drove `skills/story-to-done/scripts/todo-enforce.py` at the target, one process per hook event, with `XDG_STATE_HOME`, `CLAUDE_CONFIG_DIR` and `HOME` set to a temporary directory.
`CADENCE_LIMIT = 15` is one module constant.
Twenty calls before arming were allowed and left no count file, and the count was absent right after arming.
Calls 1 to 15 were allowed with the count reading 1 to 15, and call 16 was denied with "todo-enforce: Read was not run because 15 tool calls (CADENCE_LIMIT) have run since your last todo-list update. Bring the list up to date with TaskUpdate: complete the finished item and mark the current step in_progress, then retry."
Call 17 got the same reason, and a `Bash` call was denied naming `Bash`.
`TaskList`, `TaskGet`, `ToolSearch`, `AskUserQuestion` and `Skill` were allowed at the limit and left the count at 15.
A subagent `Read` and a subagent `TaskUpdate` were allowed at the limit, left the count at 15, and the next main-thread call was still denied.
A main-thread `TaskUpdate` and a main-thread `TaskCreate` each removed the count, and the next call was allowed with the count at 1.
With the only main task completed, the rule-4 reason was returned at counts 3 and 15 and the count did not change.
With the main task file unreadable, so the rule-4 check does not deny, 15 calls were allowed and call 16 was denied by the cadence.
An unarmed session allowed 20 calls with no count file, and an armed session whose transcript lacks the task tools allowed calls at count 15 and left it unchanged.
The counts `abc`, empty, `-2` and `1.5`, an unreadable count, an unwritable state directory at counts 5 and 15, an empty `agent_id`, a missing `tool_name` and non-JSON stdin each allowed the call with a `todo-enforce` stderr line and left the count unchanged.
With the lock held elsewhere, a call was allowed after 2.02 s with "lock not acquired within 2.0 seconds", and a `TaskUpdate` logged "not reset" and left the count at 15.
Concurrent hook processes released together gave: 2 at count 0, both allowed and count 2; 2 at count 14, one allowed, one denied and count 15; 12 at count 0, all allowed and count 12; 10 at count 10, five allowed, five denied and count 15.

AC2: `tests/test_todo_enforce.py` adds one test per case (a) to (k), with (b) parametrized over `TaskUpdate` and `TaskCreate`, and (f) covering a malformed payload, an unparseable, unreadable and unwritable count and a lock timeout.
`tests/fixtures/todo_enforce/cadence-payloads.json` records Claude Code version 2.1.322, marks each of its six payloads `synthesized`, uses `<session-id>`, `<prompt-id>`, `<tool-use-id>` and `<agent-id>` placeholders, and carries no `/home/` path, username, email address or hostname.
`BRANCHES` gains the cadence deny, the count increment and the list-update reset, each with a `NEUTRAL` mutant.
The cases passed in CI; this round ran no suite.

AC3: the test diff removes one line, `PAYLOADS = {...}`, and replaces it with the same mapping plus the cadence payloads; no existing assertion, scenario or mutation row changes.
`uv run --locked python scripts/vendor_shared.py` run twice leaves `git status --porcelain` empty, and `--check` exits 0.
Both `skills/story-refinement/scripts/todo-enforce.py` and `skills/story-to-done/scripts/todo-enforce.py` are the generated header line plus the source byte for byte, and neither is executable.
The module docstring lists the update cadence.

AC4: the README section states `CADENCE_LIMIT` (15) as a module constant with no user setting, the armed task-enabled scope, the reset including a failed `TaskCreate` or `TaskUpdate`, what is not counted, the `TaskUpdate` response including during polling, the reasserting `TaskUpdate`, that the cadence does not enforce rule 3's immediacy, and the fail-open modes.
The README diff has two prose hunks and no change to the hooks block or the removal instructions.

AC5: not covered in this round.
It needs the owner to run one fresh interactive session with `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` and link the scan, its output, the transcript and the installed skills SHA on the story.

AC6: CI run https://github.com/noahwhite/agent-skills/actions/runs/44216589191 on head `382a29ec3c5d1484ead0a8dcff10a5b31548ed92` succeeded.
Its `checks` job ran `uv run --locked pytest -q` (3268 passed), the leak scan with `--require-private` and the secret set, and `skills-ref validate` with "Valid skill" for all 18 skills; its `discovery` job ran `bash scripts/smoke-opencode.sh`.
`uv run --locked python scripts/vendor_shared.py --check` exits 0 at that head.

DoD, independently reviewed: PR 333 carries a round 1 review of record on `255569c4` with one Medium finding ruled valid, and a round 2 delta review of record on `382a29ec` that rules it resolved with no blocking findings, by `profile.review.reviewer` GPT-6.1 Sol and `profile.review.adjudicator` DeepSeek V4.1 Flash; the PR merged on `382a29ec`.

Pending owner rulings: none.

Closing decision: the story stays in In Deployment Review until the owner's AC5 session run is on the story and verified.
