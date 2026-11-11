# SKL-247 QA evidence

## Round 1

Date: 2026-11-11 UTC, independent QA round 1.
Story: SKL-247 - `story-refinement` checks repository guards against generated and frozen output a story commits.
Build under test: `main` at `8c0e00b44ca37a345365659448defebfdd184571`, the squash merge of PR 201, whose reviewed head is `99748ff895026bbda0fa591f751557ceab226182`.
The two files PR 201 changes are identical at that head and at the merge.
Environment: the profile lists no environments, so every item was checked on the repository, GitHub and tracker lanes.
The test suite and the text probe ran in a detached worktree of the build, and the mutation spot-check ran in a second one.
Method: a text probe asserted each AC requirement in its named section of `skills/story-refinement/SKILL.md`, scanned the added lines and the whole file for this repository's guard names, and matched every pinned requirement phrase and every test that pins one in the SKL-247 test block against the PR 201 body.
The block's two structural tests pin no AC requirement phrase and have no row in the PR 201 table: `test_guards_section_items_keep_their_headings_in_order` pins the seven item headings, "Guard list" to "No secrets", in order, and `test_guard_phrase_pins_keep_their_count` pins the sizes of the phrase lists.
A mutation spot-check deleted six pinned phrases and inserted two guard names, one at a time, and ran `tests/test_story_refinement.py` on each.
Fixtures: none; the delivered skill text and its tests are the surface under test.

There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw output is attached to SKL-247 as `SKL-247-qa-assertions-v2.txt`, `SKL-247-mutation-spot-check.txt` and `SKL-247-full-suite.txt`.

| Item | Verdict | Evidence |
|---|---|---|
| AC1: guard list before the voters | Verified | The new `## Repository guards` section runs in Step 1 after the tracker-write preflight and before the voter launch, whenever the acceptance criteria add or change a tracked file. Item 1 lists the guard kinds, covers every added or changed tracked file and not only the edited ones, discovers guards from CI configuration and the test suite, and records each guard, its command and the discovery source. The voter brief carries the guard list, and the Reviewer output contract includes a verdict on it. |
| AC2: producible output | Verified | Item 2 covers a recorded baseline, a captured dossier or a golden file, uses the exact bytes where they exist and otherwise a representative sample, places and stages the output in a throwaway checkout, runs every guard from there, and leaves the primary checkout unchanged. The note records each guard's command, exit status and result, and a sample's provenance and coverage limits. |
| AC3: output not yet producible | Verified | Item 3 requires the note to state why, and the refined acceptance criteria to require the committed output to pass every guard and to name the resolution the implementer may use. |
| AC4: rejection | Verified | Item 4 states the four resolution kinds, a passing re-run through the rejecting guard, and a note recording the rejection, the resolution and the re-run. |
| AC5: Definition of Ready box held | Verified | The Triage bullet holds the "checked against the implementation" box while the guard list is missing, producible output was not run, a guard could not be run, or a rejection lacks a resolution with a passing re-run. The Step 1 Stop condition and item 5 back it. |
| AC6: repository-agnostic text | Verified | Neither the added lines nor the whole `SKILL.md` contain `leak_scan`, `test_house_spelling`, `ci.yml`, `skills-ref`, `pytest`, `scripts/`, `.github` or `uv run`. `test_skill_names_none_of_this_repository_guards` asserts the four named guards are absent, and inserting `leak_scan` or `skills-ref` makes it fail. |
| AC7: pinned phrases and mutation evidence | Verified | The probe finds 43 pinned requirement phrases in the SKL-247 test block (42 lower-cased phrases and the mixed-case Step 1 item), each listed in the PR 201 table's 43 deletion rows, and every test that pins one named there. Each of the eight spot-check mutations failed the expected test with the named id, and `git status` was clean after restore. |
| DoD: all acceptance criteria met | Verified | AC1 to AC7 above. |
| DoD: tests written and passing | Verified | The local QA run of `uv run --locked pytest -q` at the build reported 1696 passed. CI `checks` and `discovery` succeeded on the PR head (run 42961579383) and on `main` at the build (run 42962244738). |
| DoD: independently reviewed | Verified | The PR 201 review of record names `99748ff895026bbda0fa591f751557ceab226182` in its first line and as its `commit_id`. Its reviewer is Codex GPT-6 Sol and its adjudicator is DeepSeek V4 Pro; the one Medium finding was fixed at that head and round 2 found nothing. |
| DoD: docs updated | Verified | The delivered change is the `story-refinement` skill text itself. |
| DoD: verified in a deployed environment | Not needed | The repository deploys nothing (`environments: []`), so the delivered skill text on `main` at the build is what was verified. |
| DoD: no critical bugs or regressions | Verified | The full suite and CI on `main` pass. |

Closing decision: Done, once this evidence merges.
