# SKL-214 QA evidence

## Round 1

Date: 2026-11-08 UTC, independent QA round 1.
Build under test: `main` at `5e3e0ae0a268a72611527a7027255ee48de6709a`, the squash merge of PR 162, whose reviewed head is `af4b07360b1736caed4e3ef99f33052aab757aaf`.
Environment: the profile lists no environments, so every item was verified against `main` and its CI.
Tool versions: git 2.43.0, uv 0.13.7, and `@opencode/cli` 2.1.2 and 2.2.6 from npm for the P6 measurement.
Fixtures: none needed.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-214 as the "SKL-214 QA round 1 - assertion output (build 5e3e0ae)" attachment.

| Item | Verdict | Evidence |
|---|---|---|
| P1: one source | Verified | `.opencode-version` is exactly `2.2.6` and one newline. A copy of the script, run in a temporary root from an unrelated directory with fake `npm` and `opencode`, used the trimmed file pin. An empty `OPENCODE_VERSION` fell back to the file, and a non-empty one won with the file present or missing. With the file missing, empty or whitespace-only and no override, it exited 1 with `.opencode-version` on stderr and made no `npm` or `opencode` call. |
| P2: no second copy of the pin number | Verified | `ci.yml` has no `OPENCODE_VERSION` and the script has no dotted version literal. `README.md` and `shared/runtimes.md` hold no pin number, name the version file with the required phrase, and keep the version-tied observations. The README install command reads the file, and the usage-row parenthetical, the Automation sentence and `tests/test_metrics.py` are reworded. The merge changes nothing under `docs/qa-evidence/`. |
| P3: discovery passes | Verified | PR-head run 42452877062 and `main` push run 42453211170 succeeded with no `OPENCODE_VERSION` in the discovery step. Each log has `opencode discovered all 18 skills` once for each of the six layouts, and `skills.json` declares 18 skills. A version mismatch after install exits 1 with `Expected OpenCode <version>` on stderr. |
| P4: vendored copies in step | Verified | `uv run --locked python scripts/vendor_shared.py --check` exits 0. All 18 `skills/*/references/runtimes.md` copies equal the generated header followed by `shared/runtimes.md`. |
| P5: tests pin the contract | Verified | The behavioural and static tests are present, and the old assertions at lines 205 and 210 are gone. Each of the four mutations the AC names was re-run and failed the tests the PR body lists. |
| P6: gate | Not met | The commands, exit codes, green CI and the review of record on `af4b073` are in place. The PR body records `/api/skill` sizes of about 442 to 445 KB on 2.1.2 and 454 to 457 KB on 2.2.6, and says the story's figures do not hold. An independent measurement with the method the PR body describes reproduced the story's figures instead. At `9449c65`, 2.1.2 returned 265,120 B, cut at 262,144 B through a pipe on 8 of 8 runs, and 2.2.6 returned 277,301 B, complete on 8 of 8 runs. |
| DoD1: all acceptance criteria met | Not met | P6 is not met. |
| DoD2: tests written and passing | Verified | `uv run --locked pytest -q` at `5e3e0ae` reports 1329 passed and exits 0, and the `checks` job of run 42453211170 succeeded. |
| DoD3: independently reviewed | Verified | The review of record on PR 162 (Codex GPT-6 Sol reviewer, DeepSeek V4 Pro adjudicator) is on `af4b073`, the merged head, with no findings. |
| DoD4: docs updated | Verified | See P2. |
| DoD5: verified in a deployed environment | Not needed | The profile lists no environments; `main` CI at `5e3e0ae` is green. |
| DoD6: no critical bugs or regressions | Verified | `main` CI and the full suite are green. |

Closing decision: back to In Progress, because the P6 measurement in the PR 162 body does not reproduce.
