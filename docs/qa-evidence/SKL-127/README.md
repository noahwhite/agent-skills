# SKL-127 QA evidence

## QA round 1

Date: 2026-11-19 UTC, independent QA round 1.
Path: `no-deployment`, from the recorded `path: no-deployment` line, so no environment or build SHA applies.
Target: merged commit `385718be52e686e2608db05c79d6e0cfc99a7f4f` on `main`, the squash of PR #349 head `1009dbb998d95cfb539f5806d5077788acd8882a`.
The merged commit is confirmed an ancestor of `origin/main`, and it and the PR head share tree `5e989ac2afb16abcdea0374b9eb77aa36757f219`.
Fixtures: detached checkouts at the target and at the pre-fix parent `b59674261bbb1bbe6fa83016248c5ecf1928eacb`, QA-written stderr fixtures, and a scratch mutant of the script with the detector call replaced by `false`.
Detector probe: `sandbox_error_in()` extracted verbatim from the target and the inline grep extracted verbatim from the pre-fix parent, both run on the same 69 fixtures: 15 echoed lines, the 19 `runtimes.md` copies, 27 real error forms, 5 for residual edge (a) and 3 for residual edge (b).
End to end: `run-adversarial-pipeline.sh preflight --test-cmd true` and `run sweep` in a throwaway repository per case, with a fake agent that writes the fixture to its stderr, run against the target, the pre-fix parent and the mutant.
QA ran no test suite, by owner instruction; the suite result is read from CI run 44441572989 on the PR head.
There is no visual surface, so no screenshot applies; the raw output is attached to the story as "SKL-127 QA round 1 raw output".

| Item | Verdict | Evidence |
|---|---|---|
| AC: echoed `bwrap:` from a read file is accepted | Verified | All 19 `runtimes.md` copies are accepted by the new detector and tripped the old one; echoing `shared/runtimes.md` end to end exits 0 at the target and 17 at the pre-fix parent. |
| AC: real `bwrap:` error still exits 17 | Verified | Bare, indented, coloured, OSC, carriage-return and tool-prefixed `bwrap:` errors trip the detector; end to end they exit 17 with "ran blind". |
| AC: existing blind-reviewer cases still exit 17 | Verified | A report without `REVIEW-RAN: yes` exits 17 end to end at the target, the pre-fix parent and the mutant; the diff leaves that branch and its tests untouched. |
| AC amendment 2026-11-18: line-shape rule | Verified | Every real form in the amendment trips for all five markers, with and without the tool prefix (27 fixtures); echoed mid-line text is accepted (15 fixtures, including the old detector line, an AC line, grep hits and `+`/`-` diff lines); edge (a) is missed and edge (b) trips, as the code comment and SKILL.md document. |
| Comment AC: test for echoed `bwrap:` content | Verified | The echoed-content tests drive `run sweep`, each fixture trips the pre-fix detector, and they pass in CI. |
| Comment AC: test for a real wrapper error | Verified | `test_a_real_sandbox_error_line_still_marks_the_phase_blind` covers 5 markers by 14 line shapes and passes in CI. |
| Comment AC: mutation-proof | Verified | With the detector call removed, every real error exits 0 instead of 17 end to end; with the pre-fix match, every echoed case exits 17. |
| Comment AC: the other four markers still trip | Verified | `sandbox failed`, `sandbox denied`, `sandbox could not` and `Failed to make ... Permission denied` trip bare, prefixed, coloured and after a carriage return. |
| Comment AC: full suite green, vendored copies in sync | Verified | CI run 44441572989 job `checks` step `Repository tests` reports "3424 passed"; `python3 scripts/vendor_shared.py --check` exits 0 at the target. |
| Product owner decision 2026-11-18: in-scope items | Verified | Escapes after the tool prefix and OSC sequences trip; the parametrized echoed-content tests assert that their input carries the marker before the sweep, and the whole-document test asserts it on the captured stderr after a successful sweep; SKILL.md and the code comment describe carriage-return handling and both edges; one test fixture pins each edge. |
| DoD: root cause identified | Verified | The old grep matched a marker anywhere in stderr, which also carries echoed file text; the fix narrows the detector to the line shape instead of filtering stderr. |
| DoD: fix verified against the original failing case | Verified | The echoed `runtimes.md` case exits 17 at the pre-fix parent and 0 at the target. |
| DoD: regression protection added | Verified | Echoed-content and real-failure tests are added in `tests/test_pipeline_failfast.py` and pass in CI. |
| DoD: independently reviewed per Review Policy | Verified | PR #349 review of record by GPT-6.2 Sol, adjudicated by DeepSeek V4.1 Flash: round 1 at `a1bb1eb` with one valid Low finding fixed, round 2 delta clean at `1009dbb`, posted before the merge. |
| DoD: docs/comments updated | Verified | The comment above `sandbox_error_in()` and SKILL.md lines 220 to 223 state the rule and its limits. |
| DoD: no new regressions | Verified | `sandbox_error_in` has one caller, `accept_phase`; the `REVIEW-RAN` check still exits 17; CI is green on the merged tree. |

Pending owner rulings: none.

Closing decision: Done, once this evidence is merged.
