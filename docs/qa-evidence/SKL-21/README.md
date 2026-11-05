# SKL-21 QA evidence

Date: 2026-11-05 UTC, independent QA round 1.
Story: SKL-21 - resolve gate script models from the profile chain (slice 1, the resolver).
Build under test: `2ebad2fb85f6b859cbf475e36b2a40a3e725ff94`, the squash merge of PR 140, whose reviewed head was `e256c0dcc4775df331367e0f1e627c2db5c4fb87`.
Environment: a detached checkout of `origin/main` at the build SHA.
The profile lists no environments and this repository deploys nothing, so `main` at the merge commit and the exact-build CI run are the deployed-build equivalent.
CI: run 42132367125 on the build SHA, `checks` and `discovery` successful.

Fixtures: throwaway profiles, git repositories, a FIFO, a mode-000 file, PyYAML shadows on `PYTHONPATH`, and a copied vendoring tree, all under a temporary directory.
`HOME` and `AGENT_SKILLS_PROFILE` pointed at fixtures, and the child environment carried no credential.
No provider, network or production request was made.
The probes run `python3 shared/resolve-model-role.py` as a subprocess, as a caller would.
There is no visual surface, so the evidence is structured CLI assertions and raw stdout and stderr; no screenshot applies.
The per-item assertion files are attached to SKL-21.

| Item | Verdict | Evidence |
|---|---|---|
| AC1 | Verified | `$AGENT_SKILLS_PROFILE` wins over the repository and home profiles, a missing env path falls to the next location, and the home profile is last. `--repo` from outside, a subdirectory without `--repo`, and inherited `GIT_DIR`/`GIT_WORK_TREE` resolve the work-tree root only; a profile in the working directory, a subdirectory or the resolver's installation directory is never read. Text output is the five fields in order with escaping; `--json` is one object, `command` absent when unset and preserved verbatim, and a `$(touch ...)` command never ran. A `command` with no runtime reads as `runtime: command`, a command entry without a model prints `unresolved`, a command on `codex` is ignored, and `[N]` indexing and the `profile.` prefix work. In a temporary tree the generator writes a non-executable copy with a `#` header whose remainder equals the source, and `--check` fails on a flipped byte, a missing or stale header, an executable bit, a missing copy and an orphan. At the build, `executables` is `{}`, no copy or caller exists, and no skill script parses a profile. `AC1-assertions.txt`, `AC1-AC6-vendoring-assertions.txt` |
| AC2 | Verified | 24 cases exit 16 with empty stdout and one stderr line naming the key and the searched paths: no profile, invalid YAML (env and repository locations, no fall-through to a valid home profile), a list, an empty file, mode 000, a directory, a FIFO, an absent role or index, non-entry paths, neither runtime nor command, unknown runtimes, a model runtime with no or blank model (with and without a command), and a command entry with a missing, empty or blank command. No skill script changed. `AC2-assertions.txt` |
| AC3 | Verified | `--dry-run` is byte-identical to a normal run in text and JSON, and on a failing entry. An audit hook records no process or network event with `--repo` or `$AGENT_SKILLS_PROFILE`, and only `git rev-parse --show-toplevel` under default discovery. `AC3-assertions.txt` |
| AC4 | Verified | A `yaml.py` raising `ImportError` exits 16 with one line naming `PyYAML>=6`, the resolver path and a `pip install` action, with and without a profile, and PyYAML 5.4.1 is refused. `dependencies = []` stays, `pyproject.toml` and `uv.lock` are unchanged, and the compatibility line is the only edit to the pipeline `SKILL.md`. `AC4-assertions.txt`, `AC1-AC6-vendoring-assertions.txt` |
| AC5 | Verified | `uv run --locked pytest -q` reports 1082 passed at the build, and each AC5 case maps to a test in `tests/test_resolve_model_role.py` that runs the resolver as a subprocess under `tmp_path` with exact-output or exit-16 assertions. `AC5-assertions.txt` |
| AC6 | Verified | `shared/profile.md` states the invocation, role syntax, resolution chain and root discovery, field order, classification, fail-closed cases and code 16, the no-execution boundary, the dependencies and SKL-68's responsibilities. `shared/README.md` and `README.md` carry the required statements, the 18 vendored copies match, and a write run of `vendor_shared.py` changes nothing. `AC6-assertions.txt` |
| DoD1: all acceptance criteria met | Verified | AC1 to AC6 above. `DoD-assertions.txt` |
| DoD2: tests written and passing | Verified | The new resolver suite, 1082 passed locally and the exact-build CI run green. `DoD-assertions.txt` |
| DoD3: independently reviewed | Verified | PR review 5793720010 is the review of record at `e256c0dcc4775df331367e0f1e627c2db5c4fb87`, the merged head, by the profile's reviewer and adjudicator, posted before the merge. `DoD-assertions.txt` |
| DoD4: docs updated | Verified | Per AC6. `AC6-assertions.txt` |
| DoD5: verified in a deployed environment, if needed | Not applicable, correct by design | The profile lists no environments; `main` at the build plus its CI run is the deployed-build equivalent. `DoD-assertions.txt` |
| DoD6: no critical bugs or regressions | Verified in tested scope | The pre-story and post-story generators write byte-identical Markdown copies (130 files), `--check` is clean, and no defect was observed. `DoD-assertions.txt` |

Closing decision: every AC and DoD item is verified, so the story moves to Done once this evidence PR merges.
The evidence-only diff changes this file alone.
