# SKL-218 QA evidence

## Round 1

Date: 2026-11-09 UTC, independent QA round 1.
Build under test: `main` at `d64aea6393d8e01af7ab48917f29efa88e90475b`, the squash merge of PR 169, whose reviewed head is `7d203a89eff45c2ed0c014b5924992933c074dcd`.
`git diff --stat 7d203a8 d64aea6` is empty, so the merged tree is the reviewed tree.
Environment: the profile lists no environments, so every item was verified against a fresh worktree of `main` and its CI.
Tool versions: uv 0.13.7, Python 3.12.3.
Fixtures: none.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-218 as the "SKL-218 QA round 1 raw assertion output" attachment.

| Item | Verdict | Evidence |
|---|---|---|
| K1: rule | Verified | `shared/engineering-practice.md` line 3 scope line adds "or when changing a skill, capability file, or consumer overlay". Section "Retire superseded memory" (line 75) states: save the rule in its new home first, then retire the note in the same session by deleting it with its index entry where the store has one or reducing it to a pointer naming the file and section (lines 77 to 78); a note keeps its other rules (line 80); persistent memory is the store in the runtime map's "Persistent memory" row, and owner-authored `CLAUDE.md` or `AGENTS.md` are named to the owner, not edited (lines 81 to 82); an agent that cannot reach the memory names the note in its handback (line 83); the PR, or the story without a PR, names each retired note and whether it was deleted or reduced to a pointer (line 85). |
| K2: runtime map | Verified | `shared/runtimes.md` line 26 is the one "Persistent memory" row, with 3 cells like every row on lines 9 to 26. The Claude Code cell names the per-project `memory/` directory, the working-directory key, the `MEMORY.md` index, the `Read`, `Write`, `Edit` and `rm` through `Bash` edit path, and "Observed on 2.1.281"; the implementing agent's transcript records Claude Code 2.1.281, and this container's store keys (`-workspace`, `.` mapped to `-`, one store per worktree) match the cell. The OpenCode cell reads "V2 ...: `not observed`" and "V1: `not observed`". The capability cell states the rule does not apply where a cell reads `none` and is reported unchecked where it reads `not observed`, and cross-references `shared/engineering-practice.md`. No line under "Rules that follow from the map" mentions memory. |
| K3: copies | Verified | `scripts/vendor_shared.py --check` exits 0. Rerunning `scripts/vendor_shared.py` exits 0 and `git status --porcelain --untracked-files=all` is empty afterwards. `uv run pytest -q` reports 1366 passed. |
| DoD1: all acceptance criteria met | Verified | K1 to K3 are verified. |
| DoD2: tests written and passing | Verified | `tests/test_memory_retirement.py` adds 10 tests, all passing, and the full suite passes (see K3). |
| DoD3: independently reviewed | Verified | The review of record on PR 169 (Codex GPT-6 Sol reviewer, no findings; DeepSeek V4 Pro adjudicator, clean) is on `7d203a8`, the merged head, submitted at 20:18:35Z before the 20:19:49Z merge. |
| DoD4: docs updated | Verified | The change is the guidance itself; `shared/README.md` and the `engineering-workflow` and `persona-platform-sre` SKILL.md blurbs name the new content, and the vendored copies are in step. |
| DoD5: verified in a deployed environment | Not needed | The profile lists no environments; `main` at `d64aea6` was verified directly. |
| DoD6: no critical bugs or regressions | Verified | The full suite passes and `main` CI run 42691924291 succeeded on `d64aea6`. |

Closing decision: Done, once this evidence merges.
