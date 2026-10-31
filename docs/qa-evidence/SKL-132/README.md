# SKL-132 QA evidence

## Round 1, 2026-10-30

The repository deploys nothing (`environments: []`), so the environment under test is merged `main`, build `6a0c3c18ff06fee0c67df348507fc479150e8e3a`.
That build is the squash of [PR #115](https://github.com/noahwhite/agent-skills/pull/115) on top of the squash of [PR #100](https://github.com/noahwhite/agent-skills/pull/100), `3487cb430df9540523b61c6bd91c6fde463ef7bc`.
[CI run 41116703540](https://github.com/noahwhite/agent-skills/actions/runs/41116703540) succeeded on the build.
Checks ran from a fresh detached checkout of `origin/main` with opencode v2.2.0.
No tracker fixture was used.
The live probe made three local `opencode run` launches on `deepseek/deepseek-flash`, built from the repository profile's engineer-one command (a unique `--title`, `--file`, the default output format, no `--standalone`); two ran concurrently, and the third resumed the first with `-s`.
The probe ran the usage snippet copied verbatim from `shared/runtimes.md` and compared it with an independent `jq` read of each session export.
There is no visual surface, so the raw assertions are the evidence; they are attached to SKL-132 as "SKL-132 QA round 1 - AC and DoD assertions", and the QA comment is `2aa8c71f`.
No raw export, prompt or tool output is kept here or in the attachment.

Outcome: AC8 cannot be exercised in this container, so the story stays In Deployment Review.

| Item | Verdict | Evidence |
|---|---|---|
| AC1 usage capture | Verified | The snippet gave launch 1 Tokens 3968 (input 3795 + output 66 + reasoning 107, cache read 18304 excluded) and Tool calls 1, and launch 2 Tokens 4074 and Tool calls 1, each equal to the independent read; the reference states the top-level-only scope. |
| AC2 deterministic session id | Verified | The two concurrent launches each matched exactly one session by title, with distinct ids; an empty title gave `not reported` for both cells; the zero-match, multiple-match and no-newest rules are in the reference text and its stub tests. |
| AC3 resume | Verified | The `-s` resume of launch 1 gave `4468 cumulative` and `2 cumulative`, equal to the independent read; the reference excludes `--continue`. |
| AC4 output format | Verified | Both statements are in the reference, and `test_usage_bullet_never_sums_stream_events_for_opencode_v2` asserts both. |
| AC5 runtime reference | Verified | The row and the rule carry every required element; `not observed` remains only for V2 `subagent` tool launches; `tests/test_metrics.py` pins the new wording. |
| AC6 metrics reference | Verified | `shared/metrics.md` carries the session-level total sentence and the cumulative-on-resume sentence. |
| AC7 vendoring | Verified | `scripts/vendor_shared.py --check` exits 0. |
| AC8 live proof | Not verified, blocked on access | The profile's facilitator `opencode-go/minimax-m3.1-flash`, product owner `opencode-go/grok-4.7` and engineer two `openai/gpt-6.1-sol` are absent from `opencode models`; only `deepseek/deepseek-flash` runs, and no model was substituted. |
| AC9 no regression | Verified | The full suite passes (880), and no codex or Claude row test changed; the story removed two assertions from `tests/test_metrics.py`: the V2 `not observed` OpenCode row assertion, replaced by the v2.2.0 wording, and `test_usage_bullet_states_command_has_no_common_contract`, whose guidance for other `runtime: command` programs stays in the reference, reworded, and is still asserted by the `other-commands` case of `test_usage_bullet_records_the_opencode_v2_procedure`. |
| AC10 failure | Verified | A live unknown explicit id printed `Session not found` and gave `not reported` for both cells; the unparseable-export, absent-field and partial-label rules are in the reference text and its stub tests. |
| AC11 shared service | Verified | The reference states the `--standalone` omission and the consumer wrapper note; the repository profile's voter commands carry no `--standalone`. |
| AC12 scope and privacy | Verified | `skills/story-to-done/scripts/metrics-summary.sh` is unchanged; both SKILL.md metrics sections point to the shared procedure with no formula of their own; the privacy sentence is present. |
| DoD all acceptance criteria met | Not met | AC8. |
| DoD tests written and passing | Verified | `tests/test_opencode_session_usage.py` is added and `tests/test_metrics.py` updated; the targeted run passes (443) and the full suite passes (880). |
| DoD independently reviewed | Verified, with disclosure | [Review 5717685200](https://github.com/noahwhite/agent-skills/pull/100#pullrequestreview-5717685200) binds PR #100 head `049bac3f83c4fb90167dcdb6df276b33d474eea4` and was posted after the owner merged it, at the owner's request; [review 5717744330](https://github.com/noahwhite/agent-skills/pull/115#pullrequestreview-5717744330) binds PR #115 head `605cb74449dbbd1122ff0c521f92cb711cf814c5` and was posted before its merge; both used Codex GPT-6 Sol and DeepSeek V4 Pro, the repository profile's pair. |
| DoD docs updated | Verified | The shared runtime and metrics references, both SKILL.md metrics sections, the schema `{session_title}` description and every vendored copy. |
| DoD verified in a deployed environment | Not applicable | No environment exists; AC8 is the live proof. |
| DoD no critical bugs or regressions | Verified | The suite and CI are green, and no defect was found. |

### Outstanding

AC8 is owned by the repository owner: make the profile's refinement roster models runnable in the agent container, or decide a different roster.
QA then runs a `metrics=on` ceremony on a tabletop fixture and compares each launch's export with the closing-message summary.

## Round 2, 2026-10-31

The environment under test is merged `main`, checked on `24639434c2fe6ee58afeb63307968e55181ed9bf` ([CI run 41119481614](https://github.com/noahwhite/agent-skills/actions/runs/41119481614) succeeded).
After SKL-151 ([PR #116](https://github.com/noahwhite/agent-skills/pull/116)) landed, `86e8ea70292907e1181c19f617499c6a7dc0e288` was re-checked ([CI run 41146784676](https://github.com/noahwhite/agent-skills/actions/runs/41146784676) succeeded): the full suite passes, 898 in each cited CI run and 880 locally, where `tests/test_story_to_done.py` parametrizes over the distinct awk binaries found and the local `awk`, `mawk` and `nawk` all resolve to one; `scripts/vendor_shared.py --check` exits 0, and the story-to-done Usage pointer is intact.
Checks ran from a fresh detached checkout of `origin/main` with opencode v2.2.0.
The fixture is SKL-153, a disposable tabletop story created for AC8 and canceled after this round.
There is no visual surface, so the raw assertions are the evidence; they are attached to SKL-132 as "SKL-132 QA round 2 - AC and DoD assertions", and the QA comment is `104609e5`.
No raw export, prompt or tool output is kept here or in the attachment.

### AC8 verification note

- Story: SKL-153, `metrics=on`.
- Facilitator: `opencode-go/minimax-m3.1-flash`, reading the story-refinement and persona-scrum-master skills from the `main` checkout.
- Voters: three OpenCode voters, all `runtime: command`: product owner `opencode-go/grok-4.7`, engineer one `deepseek/deepseek-flash`, engineer two `openai/gpt-6.1-sol`.
- Launches: 20; outcome consensus 1.
- Launch command, run from the role's directory: `opencode run --model <model> "Follow the instructions in the attached file exactly. Do not modify any file." --title <launch title> --file <prompt> > <output> < /dev/null`, in the default output format, with no `--standalone` and no `--continue`.
- Export commands: `opencode session list --format json --max-count 1000`, matched on exactly one title, then `opencode session export <session id>`, each written to a file.

Each of the 20 rows' Tokens and Tool calls in the closing-message summary equals an independent read of that launch's export.
The Totals, Tokens 805365 and Tool calls 204, equal the sums of the exports, with no `partial` label.

Outcome: every acceptance criterion and Definition of Done item is met.

| Item | Verdict | Evidence |
|---|---|---|
| AC1 usage capture | Verified | Two live `deepseek/deepseek-flash` launches gave Tokens 446 (input 368 + output 45 + reasoning 33, cache read 21632 excluded) and 608, and Tool calls 1 each, from the shipped snippet, each equal to an independent read of the export; the 20 ceremony launches agree as well (AC8). |
| AC2 deterministic session id | Verified | Two concurrent launches each matched exactly one session by title, with distinct ids; a title with no session, a title shared by two sessions and an empty title each gave `not reported` for both cells. |
| AC3 resume | Verified | A live `-s <id>` resume of launch 1 gave `874 cumulative` and `2 cumulative`, equal to the independent read; the reference excludes `--continue`. |
| AC4 output format | Verified | Both statements are in the reference, and `test_usage_bullet_never_sums_stream_events_for_opencode_v2` asserts both. |
| AC5 runtime reference | Verified | The row and the rule carry every required element; `V2 (2.1.2): not observed` is gone, and `not observed` remains only for V2 `subagent` tool launches; `tests/test_metrics.py` pins the new wording. |
| AC6 metrics reference | Verified | `shared/metrics.md` carries the session-level total rule and the cumulative-on-resume sentence. |
| AC7 vendoring | Verified | `scripts/vendor_shared.py --check` exits 0 on both builds, and all 18 vendored `runtimes.md` copies equal the source after the generated header. |
| AC8 live proof | Verified | The verification note above: 20 of 20 rows equal their exports, the Totals equal the export sums, and there is no `partial` label; the summary comment posted on SKL-153 carries the same rows and Totals, with no local path. |
| AC9 no regression | Verified | The full suite passes (898 in CI, 880 locally); the Claude Code cell and the codex bullet are unchanged, and the two removed assertions are the replaced V2 `not observed` assertion and the old `command` contract sentence, whose reworded guidance is still asserted. |
| AC10 failure | Verified | A live unknown explicit id printed `Session not found` and gave `not reported` for both cells; the unparseable-export, absent-field and no-messages rules are in the reference text and `tests/test_opencode_session_usage.py`. |
| AC11 shared service | Verified | The reference states the `--standalone` omission and the consumer wrapper note; the repository profile's commands carry no `--standalone`, and the ceremony's sessions resolved in the shared service. |
| AC12 scope and privacy | Verified | `skills/story-to-done/scripts/metrics-summary.sh` is unchanged; both SKILL.md metrics sections point to the shared procedure with no formula of their own, re-checked after SKL-151; the privacy sentence is present. |
| DoD all acceptance criteria met | Verified | AC1 to AC12 above. |
| DoD tests written and passing | Verified | `tests/test_opencode_session_usage.py` is added and `tests/test_metrics.py` updated; the full suite passes (898 in CI, 880 locally). |
| DoD independently reviewed | Verified, with disclosure | [Review 5717685200](https://github.com/noahwhite/agent-skills/pull/100#pullrequestreview-5717685200) binds PR #100 head `049bac3f83c4fb90167dcdb6df276b33d474eea4` and was posted after the owner merged it, at the owner's request; [review 5717744330](https://github.com/noahwhite/agent-skills/pull/115#pullrequestreview-5717744330) binds PR #115 head `605cb74449dbbd1122ff0c521f92cb711cf814c5` and was posted before its merge. |
| DoD docs updated | Verified | The shared runtime and metrics references, both SKILL.md metrics sections, the schema `{session_title}` description and every vendored copy. |
| DoD verified in a deployed environment | Not applicable | No environment exists; AC8 is the live proof. |
| DoD no critical bugs or regressions | Verified | The suite and CI are green on both builds. |

### Incidental

The facilitator wrote `invocation_start` and `invocation_end` as `HH:MM:SS<nanoseconds>Z` with no separator, for example `23:53:55309268160Z`, and that form reached the posted summary's Elapsed line.
`shared/metrics.md` asks for a UTC timestamp taken with a command but names no format; this is not an SKL-132 item.
