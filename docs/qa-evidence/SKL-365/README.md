# SKL-365 QA evidence

## QA round 1

Date: 2026-11-19 UTC, independent QA round 1.
Path: `no-deployment`, from the recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `aa3f0bbb5f642f1b76b9777d9b7699c5ce6fcc03` on `main`, the squash of PR #364 head `2cd42e260c93bcdf2f048151741128d918b2616b`.
The merged commit is confirmed an ancestor of `origin/main`, and the PR's three files at the target are identical to the reviewed head.
Dependency: SKL-127 is Done, and its merge `385718b` is an ancestor of the target; the detector `sandbox_error_in` and `accept_phase` are unchanged since then.
Fixtures: detached checkouts at the target and at the unfixed revision `b59674261bbb1bbe6fa83016248c5ecf1928eacb` (`385718b^`), a copy of the target with only the script swapped to that revision, and the original SKL-70 `sweep-agent.err` (PR #326, base `f83cacb`, head `131ca43`, sha256 `bc826104ce6a6a20fde69c770050446a802c4d2849a7fbc3a127e403b8b84b16`).
End to end: a fresh one-commit repository per run, `preflight --full-suite on --test-cmd true`, then the production `run sweep` path into `accept_phase`, with an agent that writes the SKL-70 stderr to its own stderr and a valid report.
There is no visual surface, so no screenshot applies; the raw output is attached to the story as "SKL-365 QA round 1 raw output".

| Item | Verdict | Evidence |
|---|---|---|
| AC1: unfixed script exits 17 on the echoed SKL-70 stderr | Verified | The original SKL-70 stderr was found; its only match for the old check is line 982, the echoed `shared/runtimes.md` sentence "fails with a `bwrap:` error". At `b596742` the sweep exits 17 with "the sweep agent ran blind" and no stamp. PR #364 carries the revision, invocation, input and output. |
| AC2: fixed script accepts the same input | Verified | Same input and invocation at the target: exit 0, no "ran blind" line, the phase is stamped, and the kept `sweep-agent.err` is byte-identical to the input, echoed line included. PR #364 carries the revision, invocation and output. |
| AC3: a runtime error fixture per old alternative still exits 17 | Verified | `RUNTIME_ERROR_LINES` has one line per alternative; a test splits the verbatim old regex and requires exactly those five, and each line must trip only its own alternative. Each fixture names its runtime format (or "none (line shape only)") and its origin kind; the PR table names them. All five tests and the bubblewrap `Failed to make` test pass at the target, asserting exit 17, the blind message and no stamp. |
| AC4: echoed reviewed-file content, every alternative mid-line, is accepted | Verified | `tests/fixtures/sandbox_echo/echoed-reviewed-file.txt` is a different path from `shared/runtimes.md` and its vendored copies (a path check); the whole-file test asserts it quotes every old alternative and the SKL-70 phrase "fails with a `bwrap:` error", that no line opens with a marker, and that the run's stderr keeps it whole. Each per-alternative test asserts the marker is quoted in each of the five context kinds and that no quoting line is in the detector's line shape, before asserting exit 0, a stamp and the lines kept in stderr. |
| AC5: echo plus a runtime line still exits 17 | Verified | For each of the five runtime lines, the echoed file alone exits 0, the line alone exits 17, and both together exit 17 with the blind message, no stamp, and both in `sweep-agent.err`. |
| AC6: automated tests, red on the unfixed script, green on the fixed one | Verified | Focused tests: 25 passed at the target; with the script swapped to `b596742`, 16 failed and 9 passed, every failure `assert 17 == 0`. Both outputs are in PR #364. |
| AC7: final PR head passes every CI guard | Verified | CI run 44584024512 on head `2cd42e2` (non-fork, so `--require-private`): repository tests, leak scan, skills-ref validate and the opencode smoke all succeeded; the PR links them. Run 44588659838 on the merged commit is also green, with "3790 passed". |
| DoD: root cause identified | Verified | The pre-SKL-127 check grepped the whole agent stderr, which also carries the files opencode echoes; the SKL-70 match is that echoed line. SKL-127 replaced the grep with a line-shape detector, and this story pins it. |
| DoD: fix verified against the original failing case | Verified | AC1 and AC2 above, on the original SKL-70 stderr. |
| DoD: regression protection added | Verified | The SKL-365 tests and fixture in `tests/test_pipeline_failfast.py` and `tests/fixtures/sandbox_echo/`, with the fixture pinned LF in `.gitattributes`. |
| DoD: independently reviewed per Review Policy | Verified | PR #364 review of record by GPT-6.2 Sol, adjudicated by DeepSeek V4.1 Flash, five rounds; round 5 at the merged head `2cd42e2` found nothing merge-blocking and was posted before the merge. |
| DoD: docs/comments updated | Verified | The comment above `sandbox_error_in()` and SKILL.md lines 224 to 226 state the line-shape rule and its limits; the SKL-365 test block and the `.gitattributes` rule carry their own comments. |
| DoD: no new regressions | Verified | The change adds tests, one fixture, and one `.gitattributes` rule with its comment, and no script; `vendor_shared.py --check` exits 0; the full suite is green at the target in CI. |

Pending owner rulings: none.

Closing decision: Done, once this evidence is merged.
