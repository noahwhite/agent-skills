# SKL-239 QA evidence

## QA round 1

Date: 2026-11-13 UTC, independent QA round 1.
Build under test: `main` at `784b609abb4efd41cba14c8e03936ad9c1f58583`, the squash merge of PR 234, whose reviewed head is `fdcb179f74a452d19056fc075313fc3f5100e396`.
The 23 files PR 234 changes are byte-identical between the reviewed head and the merge; the rest of the tree difference is base changes from other stories.
Environment: none; the profile sets `environments: []`, so the lanes are the repository (a detached worktree of the build), GitHub and the tracker.
Fixtures: the three scratch issues the PR names, SKL-298 (Bug, RTB), SKL-299 (Spike) and the split sibling SKL-301 (Bug, RTB), read back from the tracker.
The raw output is attached to SKL-239 as `SKL-239-qa-round-1-assertions.txt`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| B5: oversize split | Verified | The Scope signal and Oversize split bullets, Step 2 item 8 and the `shared/linear.md` line; details below. |
| B6: Spikes | Verified | The Spike re-file, Ready gate, Content per type and Closing outcome bullets and the Step 1 type check; details below. |
| B7b: scope signal line | Verified | The Refinement comment template line and the Closing outcome for a split; details below. |
| B8b: tests and proof | Pending owner ruling | The tests and the scratch runs hold; the PR body names the runs without a hyperlink, and two assertions do not use `bullet()`; details below. |
| B9: regeneration and gate | Verified | `vendor_shared.py --check` exit 0, the suite passes on the build, and CI passed on the reviewed head; details below. |
| DoD: all acceptance criteria met | Pending owner ruling | B8b. |
| DoD: tests written and passing | Verified | B8b tests and B9. |
| DoD: independently reviewed | Verified | The last review of record on PR 234 names `fdcb179f74a452d19056fc075313fc3f5100e396` in its first line and as its `commit_id`, the merged head. |
| DoD: docs updated | Verified | The change is the skill text itself, plus the README row for `story-refinement`. |
| DoD: verified in a deployed environment | Not applicable | The profile defines no environments, so the build was verified on `main`. |
| DoD: no critical bugs or regressions | Verified | CI passed on the reviewed head (run 43506149781) and on `main` (run 43507578006). |

Details:

- B5:
  - The Scope signal bullet of "Unestimated issue types" gives the Bug and Investigation readings `single change` and `more than one independently reviewable change (<reason>)` with the AC's examples.
  - The Oversize split bullet states each difference from the story split in the AC's order: the line as trigger, Step 2 after the accept round and before the Triage record, the `linear-bug` or `linear-investigation` template, the type label confirmed under the differing-team rule and read back, and no point value or slice estimate.
  - It keeps the original as the core slice blocking each sibling, maps every acceptance criterion or findings-scope item in the split comment, and re-splits a multi-change sibling without escalation.
  - Step 2 item 8 sits after the accept round items and runs the split before the PO posts the Triage record.
  - `shared/linear.md` (Estimation and slicing) gains one line with the trigger, present in all 18 vendored `references/linear.md` copies.
- B6:
  - The Spike re-file bullet keeps a multi-thread Spike unsplit in backlog with the `State:` reading "re-file as separate Spikes (owner)" and the closing outcome "refined, not pointed (Spike); needs input: re-file as separate Spikes" naming the story.
  - The Spike readings are `single research thread` and `more than one independent research thread (<reason>)`, and the Ready gate holds a multi-thread Spike.
  - The Step 1 type check names Bug, Investigation and Spike, and Content per type names all three, the Spike timebox "refined in place of an estimate".
- B7b:
  - `references/refinement-record.md` carries `- Scope signal: <reading>` in the Refinement comment template, right after the `Pointing skipped` line, stated for a Bug, an Investigation or a Spike only, with the B5 and B6 readings.
  - The Closing outcome bullet reads "refined, not pointed (<type>); split into <n> slices" when the oversize split runs, and the Closing message section names the split and the slice count.
- B8b:
  - `tests/test_story_refinement.py` asserts the B5 scope signal, sibling template and label, the no-slice-estimate rule, the `shared/linear.md` line, the B6 Spike scope signal and re-file wording, and the B7b record line.
  - The tracker holds the runs: SKL-298's refinement comment `d7d1467a` reads "Scope signal: more than one independently reviewable change (...)", its split comment `449d8c02` creates SKL-301, and SKL-301 carries the labels Bug and RTB and is blocked by SKL-298.
  - SKL-298, SKL-299 and SKL-301 read back estimate null and state Canceled.
  - SKL-299's Triage record `2ce31050` reads "- State: backlog: re-file as separate Spikes (owner)".
  - Pending owner ruling, reading 1: "The PR links a ceremony run" means the PR identifies the run; PR 234 names SKL-298, SKL-299 and SKL-301 and each comment by an 8-character id prefix, so the item is met.
  - Pending owner ruling, reading 2: "links" means a hyperlink; the rendered PR 234 body has no link at all, so the item is not met.
  - Pending owner ruling, reading 3: "each through `section()` and `bullet()`" means every listed assertion calls both helpers; the `shared/linear.md` line test uses `section()` only, and the B7b record line test uses `section()` and the fenced-template helper, so the item is not met for those two.
  - Pending owner ruling, reading 4: the helpers scope each assertion, with `bullet()` where the target is a `- **Label:**` bullet; those two targets are not labelled bullets, so the item is met.
  - Owner: the product owner.
- B9:
  - `refinement-record.md` opens as hand-written, with no generated header, and `scripts/vendor_shared.py` does not name it.
  - `uv run --locked python scripts/vendor_shared.py --check` exited 0 on the build.
  - `uv run --locked pytest -q -p no:cacheprovider` passed on the build (2197 passed).
  - CI run 43506149781 on the reviewed head passed (`discovery` and `checks`).
  - `shared/todo-tracking.md` did not change in PR 234; its story-refinement seed line, from SKL-237, already keeps each split for these types, and the drift check shows every copy current.

Closing decision: SKL-239 stays In Deployment Review, pending the product owner's ruling on B8b.

## QA round 2

Date: 2026-11-13 UTC, independent QA round 2, after the product owner's dated B8b clarification of 2026-11-13.
The clarification reads: `bullet()` is required only where the asserted target is a labelled bullet, `section()` applies to every assertion, and "links a ceremony run" means real hyperlinks in the PR body.
Path: `no-deployment`, since the profile sets `environments: []`.
Target: the merged commit `784b609abb4efd41cba14c8e03936ad9c1f58583` (PR 234, reviewed head `fdcb179f74a452d19056fc075313fc3f5100e396`), an ancestor of `origin/main`.
Fixtures: SKL-298 (Bug), SKL-299 (Spike) and SKL-301 (split sibling), read back from the tracker.
The raw output is attached to SKL-239 as `SKL-239-qa-round-2-assertions.txt`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| B5: oversize split | Verified | The Scope signal and Oversize split bullets, Step 2 item 8, and the `shared/linear.md` line in the shared file and all 18 vendored copies. |
| B6: Spikes | Verified | The Refinement only, Scope signal, Spike re-file and Content per type bullets, and the Step 1 type check. |
| B7b: scope signal line | Verified | `- Scope signal: <reading>` in the Refinement comment template after the `Pointing skipped` line, limited to the three types; the Closing outcome and Closing message name the split and the slice count. |
| B8b: tests and proof | Failed | The PR 234 body now hyperlinks the run, but several assertions on the listed targets do not go through `section()`; details below. |
| B9: regeneration and gate | Verified | `refinement-record.md` is hand-written, `vendor_shared.py --check` exits 0, `pytest` passes on the target (2197 passed), and CI passed on the reviewed head (run 43506149781) and on the merge (run 43507578006). |
| DoD: all acceptance criteria met | Not met | B8b. |
| DoD: tests written and passing | Verified | B9. |
| DoD: independently reviewed | Verified | The latest review of record on PR 234 names `fdcb179f74a452d19056fc075313fc3f5100e396` in its first line and as its `commit_id`. |
| DoD: docs updated | Verified | The skill text and the README row for `story-refinement`. |
| DoD: verified in a deployed environment | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | CI passed on the reviewed head and on the merge. |

B8b details:

- The rendered PR 234 body links SKL-298, its refinement comment `d7d1467a`, its split comment `449d8c02`, SKL-301, SKL-299 and its Triage record `2ce31050`, so the hyperlink clause is met.
- The tracker holds the runs: SKL-301 carries the labels Bug and RTB and is blocked by SKL-298, SKL-299's Triage record reads "- State: backlog: re-file as separate Spikes (owner)", and all three issues are Canceled with estimate null.
- `section()` strips HTML comments and scopes by heading; `template()` and `step()` (behind `process_item()`) parse headings with their own regular expressions and do not call `section()`.
- The B7b record line is asserted only through `template()` in `test_refinement_template_carries_the_scope_signal_line` and `test_scope_signal_field_name_keeps_its_case`.
- The Split comment template's sibling template, sibling label and no-estimate lines are asserted through `template()` in `test_split_comment_template_has_the_fields`.
- The `shared/linear.md` line in each vendored copy is asserted on the whole file in `test_vendored_linear_copies_carry_the_unestimated_split_trigger`.
- The B5 trigger and B6 re-file wording in Step 2 item 8, and the scope signal in the voter brief, reconciliation and reviewer output contract, are asserted through `process_item()` or `operative_step()`.
- A probe on a scratch copy of the target wrapped the whole Refinement comment template in an HTML comment, and both B7b record-line tests still passed (2 passed).

Closing decision: SKL-239 returns to In Progress for the B8b fix.

## QA round 3

Date: 2026-11-14 UTC, independent QA round 3, after the B8b rework in PR 245.
Path: `no-deployment`, since the profile sets `environments: []`.
Target: `origin/main` at `a799b06919aac12ba32c7724432ace57fb1809a9`, the squash merge of PR 245 (reviewed head `59ee2e2bf140daca37d9839e91dc751c7334cd37`), with PR 234's merge `784b609abb4efd41cba14c8e03936ad9c1f58583` as an ancestor.
`tests/test_story_refinement.py` is byte-identical between PR 245's reviewed head and the merge.
Fixtures: SKL-298 (Bug), SKL-299 (Spike) and SKL-301 (split sibling), read back from the tracker.
The raw output is attached to SKL-239 as `SKL-239-qa-round-3-assertions.txt`; there is no visual surface, so no screenshot applies.

| Item | Verdict | Evidence |
|---|---|---|
| B5: oversize split | Verified | The Scope signal and Oversize split bullets, Step 2 item 8, and the `shared/linear.md` line in Estimation and slicing, in the shared file and all 18 vendored copies. |
| B6: Spikes | Verified | The Refinement only, Scope signal, Spike re-file, Ready gate and Content per type bullets, and the Step 1 type check naming Bug, Investigation and Spike. |
| B7b: scope signal line | Verified | `- Scope signal: <reading>` in the Refinement comment template, limited to the three types; the Closing outcome and Closing message name the split and the slice count. |
| B8b: tests and proof | Verified | Every listed assertion reads through `section()`, `bullet()` on the labelled bullets; 17 mutants killed and 2 controls pass; PR 234 hyperlinks the run; details below. |
| B9: regeneration and gate | Verified | `refinement-record.md` is hand-written, `vendor_shared.py --check` exits 0, `pytest` passes on the target (2301 passed), and CI passed on both reviewed heads and on the merge. |
| DoD: all acceptance criteria met | Verified | B5, B6, B7b, B8b and B9. |
| DoD: tests written and passing | Verified | B8b and B9. |
| DoD: independently reviewed | Verified | The latest review of record on PR 234 names `fdcb179f74a452d19056fc075313fc3f5100e396` and on PR 245 names `59ee2e2bf140daca37d9839e91dc751c7334cd37`, each in its first line and as its `commit_id`. |
| DoD: docs updated | Verified | The skill text and the README row for `story-refinement`. |
| DoD: verified in a deployed environment | Correct by design | Not needed on the `no-deployment` path. |
| DoD: no critical bugs or regressions | Verified | CI run 43506149781 (PR 234 head), 43539510168 (PR 245 head) and 43540097843 (`main` at the merge) passed `checks` and `discovery`. |

B8b details:

- `section()` removes HTML comments, fails on an unclosed one, skips fenced heading-like lines and drops fenced blocks unless a template reader keeps them.
- Every helper the B8b tests use reads through `section()`: `unestimated_bullet()`, `process_items()`, `process_item()`, `operative_step()`, `step()`, `type_item()`, `skill_section()`, `template()`, `template_block()` and `fallback_alternative()`.
- The `shared/linear.md` line is asserted in `section(..., "Estimation and slicing")` of the shared file and of each vendored copy.
- The labelled-bullet targets (Scope signal, Oversize split, Spike re-file, Ready gate, Content per type, Closing outcome, Reviewer output contract) are read with `bullet()`.
- A mutation probe on a scratch copy of the target ran the named tests per mutant:
  - Killed: the Refinement comment template wrapped in an HTML comment (both B7b record-line tests fail).
  - Killed: the Split comment template wrapped in an HTML comment, and its no-estimate line removed.
  - Killed: the trigger line commented out in the `linear-bug` vendored copy, and moved out of Estimation and slicing in `shared/linear.md`.
  - Killed: the Step 2 item 8 Spike re-file sentence commented out, and the whole item commented out.
  - Killed: the Spike scope signal sentence commented out, and the Scope signal bullet moved into a code fence.
  - Killed: the Oversize split bullet commented out, and its sibling-label clause commented out.
  - Killed: the Spike re-file bullet moved into a code fence.
  - Killed: the voter brief, reviewer output contract and reconciliation scope signal sentences commented out.
  - Killed: the Closing message split sentence fenced, and the Closing outcome split sentence commented out.
  - Controls pass: a plain example fence before the Refinement comment template, and a harmless HTML comment in the Unestimated issue types section.
- The rendered PR 234 body hyperlinks SKL-298, its refinement comment `d7d1467a`, its split comment `449d8c02`, SKL-301, SKL-299 and its Triage record `2ce31050`.
- SKL-298's refinement comment reads "Scope signal: more than one independently reviewable change (...)", and SKL-301 carries the labels Bug and RTB and is blocked by SKL-298.
- SKL-299's Triage record reads "- State: backlog: re-file as separate Spikes (owner)".
- SKL-298, SKL-299 and SKL-301 are Canceled with estimate null.

Closing decision: SKL-239 moves to Done once this evidence merges.
