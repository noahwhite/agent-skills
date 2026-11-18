# SKL-276 QA evidence

## QA round 1

Date: 2026-11-18 UTC, independent QA round 1.
Path: `no-deployment`, selected by `select-path.py` with the story's title, its two labels and the recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `6a132adced154b02cb57485b4d339ec0c027f8a1` on `main`, the squash merge of PR 333, whose reviewed head is `382a29ec3c5d1484ead0a8dcff10a5b31548ed92`.
`git merge-base --is-ancestor` confirmed the target on `origin/main`, and `git diff 382a29ec 6a132ad` touches only `docs/qa-evidence/SKL-363/README.md`, so every file of the PR is the reviewed file.
Owner constraint for this round: no test suite was run; the evidence is the merged code, direct invocations of the vendored hook copy at the target (not a copy installed in the user's skills directory) on hand-made payloads in a temporary state, config and home directory, `scripts/vendor_shared.py`, and the CI runs that ran automatically.
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
Calls 1 to 15 were allowed with the count reading 1 to 15, and call 16 was denied with a reason that names `Read`, 15 and `CADENCE_LIMIT` and tells the agent to bring the list up to date with the task-update tool (complete the finished item, mark the current step in progress) and then retry; the attached probe output quotes it in full.
Call 17 got the same reason, and a `Bash` call was denied naming `Bash`.
`TaskList`, `TaskGet`, `ToolSearch`, the ask-the-user tool and `Skill` were allowed at the limit and left the count at 15.
A subagent `Read` and a subagent task update were allowed at the limit, left the count at 15, and the next main-thread call was still denied.
A main-thread task update and a main-thread task create each removed the count, and the next call was allowed with the count at 1.
With the only main task completed, the rule-4 reason was returned and the count did not change, both below the limit and at count 15.
With the main task file unreadable, so the rule-4 check does not deny, 15 calls were allowed and call 16 was denied by the cadence.
An unarmed session allowed 20 calls with no count file, and an armed session whose transcript lacks the task tools allowed calls at count 15 and left it unchanged.
The counts `abc`, empty, `-2` and `1.5`, an unreadable count, an unwritable state directory at counts 5 and 15, an empty `agent_id`, a missing `tool_name` and non-JSON stdin each allowed the call with a `todo-enforce` stderr line and left the count unchanged.
With the lock held elsewhere, a call was allowed after 2.02 s with "lock not acquired within 2.0 seconds", and a task update logged "not reset" and left the count at 15.
Concurrent hook processes released together gave: 2 at count 0, both allowed and count 2; 2 at count 14, one allowed, one denied and count 15; 12 at count 0, all allowed and count 12; 10 at count 10, five allowed, five denied and count 15.

AC2: `tests/test_todo_enforce.py` adds one test per case (a) to (k), with (b) parametrized over the task-update and task-create tools, and (f) covering a malformed payload, an unparseable, unreadable and unwritable count and a lock timeout.
`tests/fixtures/todo_enforce/cadence-payloads.json` records Claude Code version 2.1.322, marks each of its six payloads `synthesized`, uses `<session-id>`, `<prompt-id>`, `<tool-use-id>` and `<agent-id>` placeholders, and carries no `/home/` path, username, email address or hostname.
`BRANCHES` gains the cadence deny, the count increment and the list-update reset, each with its no-op replacement in the mutation table.
The cases passed in CI; this round ran no suite.

AC3: the test diff removes one line, `PAYLOADS = {...}`, and replaces it with the same mapping plus the cadence payloads; no existing assertion, scenario or mutation row changes.
`uv run --locked python scripts/vendor_shared.py` run twice leaves `git status --porcelain` empty, and `--check` exits 0.
Both `skills/story-refinement/scripts/todo-enforce.py` and `skills/story-to-done/scripts/todo-enforce.py` are the generated header line plus the source byte for byte, and neither is executable.
The module docstring lists the update cadence.

AC4: the README section states `CADENCE_LIMIT` (15) as a module constant with no user setting, the armed task-enabled scope, the reset including a failed task create or task update, what is not counted, the task-update response including during polling, the reasserting task update, that the cadence does not enforce rule 3's immediacy, and the fail-open modes.
The README diff has two prose hunks and no change to the hooks block or the removal instructions.

AC5: not covered in this round.
It needs the owner to run one fresh interactive session with `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` and link the scan, its output, the transcript and the installed skills SHA on the story.

AC6: CI run https://github.com/noahwhite/agent-skills/actions/runs/44216589191 on head `382a29ec3c5d1484ead0a8dcff10a5b31548ed92` succeeded.
Its `checks` job ran `uv run --locked pytest -q` (3268 passed), the leak scan with `--require-private` and the secret set, and `skills-ref validate` with "Valid skill" for all 18 skills; its `discovery` job ran `bash scripts/smoke-opencode.sh`.
`uv run --locked python scripts/vendor_shared.py --check` exits 0 at that head.

DoD, independently reviewed: PR 333 carries a round 1 review of record on `255569c4` with one Medium finding ruled valid, and a round 2 delta review of record on `382a29ec` that rules it resolved with no blocking findings, by `profile.review.reviewer` GPT-6.1 Sol and `profile.review.adjudicator` DeepSeek V4.1 Flash; the PR merged on `382a29ec`.

Pending owner rulings: none.

Closing decision: the story stays in In Deployment Review until the owner's AC5 session run is on the story and verified.

## QA round 2

Date: 2026-11-18 UTC, independent QA round 2, verifying AC5 only, as amended on 2026-11-18 by the product owner.
Path: `no-deployment`, selected by `select-path.py` with the recorded `path: no-deployment` line; target merged commit `6a132adced154b02cb57485b4d339ec0c027f8a1`, confirmed on `origin/main` with `git merge-base --is-ancestor`.
Owner constraint for this round: no test suite was run.
The session run is the coordinating agent's, under the amendment: one non-interactive `claude -p` session with `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`, in an isolated HOME carrying the installed skills and the README hooks block, on story SKL-50, chosen by that agent.
The raw evidence is attached to SKL-276 as "SKL-276 AC5 session transcript (redacted)", "SKL-276 AC5 scan command and output" and "SKL-276 QA round 2 AC5 checks"; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| AC5: session run | Verified | Installed skills at `59a8a3caae33233c14604a4f256147e410fb4501`, which contains the target; the scan passes both bullets on the session transcript; the provoked denial is recorded on the story. |
| DoD: all acceptance criteria met | Verified | AC1 to AC4 and AC6 verified in round 1, AC5 in this round. |

AC5 evidence:
The installed skills are a clean clone at `59a8a3caae33233c14604a4f256147e410fb4501`, linked into the isolated HOME's skills directory, and `git merge-base --is-ancestor 6a132ad HEAD` exits 0 there.
`git diff 6a132ad 59a8a3c` is empty for `shared/todo-enforce.py`, `skills/story-to-done/scripts/todo-enforce.py` and `README.md`, and the installed copy sets `CADENCE_LIMIT = 15`.
The session's settings file is byte-identical to the README hooks block (`cmp` exits 0), and the transcript's Stop summary shows the one enforcer hook running.
The session's tool list carries the task tools, its first task create succeeded, and the enforcer's state directory holds the armed marker from the slash-command prompt, written before any tool call.
The session loaded story-to-done from the installed path, found SKL-50 Done, and ended in the skill's nothing-to-do report with the bare `report: final` line; the run exited 0.
The scan reads 32 main-thread tool calls once each by tool use id, with the enforcer's exempt set, a reset on each main-thread task create or task update, and denials found by the enforcer's reason text.
Its longest run of allowed non-exempt calls between list updates is 15.
It finds one cadence denial, `toolu_01S4K16K8XezfELcQoRToZq4` at `2026-11-18T04:18:52.709Z`, followed by the task update `toolu_01WSSdzTovYCtQzbUa6d11N4` and 7 further main-thread calls, the first non-exempt one the retried read, which was allowed.
The denial was provoked: the run prompt asked for 16 consecutive reads with no list update, and the 16th read is the denied call; no other denial occurred.
The scan docstring says counting starts at the first task create, while the code counts from the first transcript line; the session armed before any tool call, so the result is the same.
The attached transcript keeps all 121 tool use and tool result blocks of the original; account ids, UUIDs, the email address, home and run-directory paths and the container hostname are replaced by placeholders.

Pending owner rulings: none.

Closing decision: every acceptance criterion and Definition of Done item is verified, so the story moves to Done once this record merges.
