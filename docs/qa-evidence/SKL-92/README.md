# SKL-92 QA evidence

## Round 1, 2026-10-29

The repository deploys nothing, so the environment under test is merged `main`, build `077a4d6929f6fd68889d0d2cf991525b51b7390b` from [PR #90](https://github.com/noahwhite/agent-skills/pull/90).
Both live ceremonies load the skill and its references from separate detached checkouts at PR head `8b6f8a47ae53a11b53c8dcca645fc6ab3af9020a`, not from the installed skill.
The PR-head and squash-merge trees are identical (`963fa517d67f17937041a171fe6a0777861c533c`).
The merged build also has [successful CI run 40919049407](https://github.com/noahwhite/agent-skills/actions/runs/40919049407), reporting 790 passing tests.
Fixtures are SKL-130 (`metrics=on`) and SKL-131 (switch omitted).
There is no visual application surface; structured assertions and raw command output are the evidence, without invented screenshots.

| Item | Verdict | Evidence |
|---|---|---|
| C1 posting rules | Verified | Repository assertions verify all posting-rule contracts; the facilitator's own summary comment `239dea2c` is read back byte-identically and is the last ceremony comment after the pointing and triage records; the closing message repeats it and names its link. |
| C2 docs and vendoring | Verified | The on-only seed orders start capture, collection, then posting; all 18 committed vendored todo references exactly match their source after the generated banner; the README row names the switch, default, closing summary, and post. |
| C3 text contracts and CI | Verified | Inspected named exact-phrase contracts in `tests/test_story_refinement.py`; PR #90 records 29 mutation checks; [CI run 40918463339](https://github.com/noahwhite/agent-skills/actions/runs/40918463339) has successful checks and discovery for head `8b6f8a47ae53a11b53c8dcca645fc6ab3af9020a`, with 790 tests passing, including todo tests and the test invoking `vendor_shared.py --check`. |
| C4 live ceremonies | Verified | SKL-130 and SKL-131 each reached a recorded 1-point outcome from the exact PR-head checkout; summary, complete closing messages, off-path absence, permission provenance, and both Canceled read-backs are recorded on SKL-92 in comments `ba885326` and `2b64c49c`. |
| DoD all acceptance criteria met | Verified | C1-C4 above, with 27 passing combined tracker assertions and both fixture cancellation assertions. |
| DoD unit/integration tests written and passing | Verified | Added posting-rule tests are present and the implementation PR CI suite passes. |
| DoD independently reviewed | Verified with owner-authorized exception | [Review 5701927357](https://github.com/noahwhite/agent-skills/pull/90#pullrequestreview-5701927357) binds exact head `8b6f8a47ae53a11b53c8dcca645fc6ab3af9020a`; the owner explicitly accepted its Flash adjudicator instead of configured V4 Pro in [comment 6505175411](https://github.com/noahwhite/agent-skills/pull/90#issuecomment-6505175411) and tracker comment `4caf3c09`. |
| DoD docs updated | Verified | README row and shared todo seed, with all 18 generated copies. |
| DoD staging substitute | Verified | No staging deployment exists; both completed C4 fixture ceremonies are the story's specified substitute. |
| DoD no critical bugs/regressions | Verified within scope | Posting and omitted-switch checks pass, with implementation-head and merged-build CI green; run-discipline and historical-record findings below remain disclosed. |

### Test scope

QA read the shipped contracts and CI output rather than rebuilding or mutating the implementation.
Unreached end states are covered by C3's text contracts as C4 explicitly allows.

### Metrics-on fixture

SKL-130 reached a recorded consensus of 1, with no split, after one accept round, one blind pointing round, and one re-vote.
The resumed invocation captured its own UTC start and reports only its 15 launches; earlier invocation figures are preserved separately and excluded.
Its elapsed value, 1092.996 seconds, matches the raw timestamp difference of 1092.995841 seconds to the displayed millisecond precision.
Tokens and tool calls are `not reported`, with `[partial: 15 not reported, 0 cumulative]`, matching all 15 rows.
The normal facilitator shell action successfully posted its own SM/EM summary and read back the full body, without a denied-write fallback, permission edit, auto-approval flag, or alternate tool/server.
The summary comment `239dea2c`, complete genuine closing message, permission provenance, structured assertions, and cancellation read-back are recorded on SKL-92 in comment `ba885326`.
The coordinator canceled SKL-130 after the invocation; its state reads back Canceled and it has no children or split siblings.

### Omitted-switch fixture and final read-backs

SKL-131 reached a recorded consensus of 1 without a split, with the switch omitted and no metrics summary comment among its six live comments.
Its genuine closing message has `metrics: off` as its only metrics content.
Its pointing record is `baa08c0a`, and PO triage evidence is `add28754`; both were read back by the facilitator and independently observed by QA.
The fixture remained Backlog because hypothetical implementation write access was not verified; that fixture DoR item is not an outstanding SKL-92 criterion.
The coordinator canceled SKL-131 and independently read both fixtures back as Canceled, with no children or split siblings.
The complete off-run closing message, off issue link, on summary link, 27 passing combined tracker assertions, both cancellation assertions, scope snapshot, and merged-build CI record are attached to SKL-92 in comment `2b64c49c`.
The repository, documentation, and contract/CI assertions are attached in comment `9c89fc72`; its initial independent-review certification is qualified by the subsequently documented owner exception below.
No other story mutation appears in either ceremony's operation records, and only the two fixtures were created in the complete SKL baseline comparison.
That comparison also observed an SKL-94 preflight outside these operation records, so the evidence does not claim the shared tracker was globally idle.

### Ceremony process deviations

The metrics-on facilitator recovered a timeout after an already-applied preflight, an incomplete accept-result launch, and a guessed read-back identifier without duplicating tracker writes.
It documented stale child-checklist entries, some directory-name listings above a role's assigned directory, and a voter repeating its own point in process output.
No other voter's input/value contents were exposed before its own input/value was recorded, and those outputs were not handed to another voter.
These are run-discipline findings for the coordinator, not changes to SKL-92's posting implementation, and are not represented as a clean ceremony-process audit.
The off-run PO transiently included prohibited disabled-feature text inside its pointing record, then removed both the footer and a residual quoted clause and read back the corrected body before ending.
Those were edits to a ceremony record, not a separate metrics summary comment; the final six comments contain no metrics summary, and the full repair history remains in the raw ceremony handback.
The off-run also recovered a stale/truncated CLI read and moved its own accidentally created untracked relation capture out of the checkout; the final exact-head checkout is clean.

### Incidental record discrepancy

PR #90's historical mutation table M28 names `test_metrics_reference_orders_the_story_refinement_post`, which was replaced during the timestamp-review remediation by `test_metrics_reference_shares_the_timestamp_with_a_posted_summary` and the shared timing contracts.
The review of record describes the final timing implementation and its tests; the historical table is not proof that the replacement timing assertions were independently mutation-tested at the final head.
This does not remove any of C3's required C1-rule guards; report the stale historical test name to the coordinator rather than editing implementation history in QA.

### Owner exception, source conflict, and closing decision

Evidence review F1 correctly identified that the implementation review used Flash instead of repository-configured V4 Pro without a documented exception at that time.
The owner then directly authorized the exception in the QA conversation, recorded verbatim on SKL-92 in comment `4caf3c09` and on implementation PR #90 in comment `6505175411`:

> I authorize the use of deepseek flash in this case though it would be good to know why it was chosed if the profile have v4 pro. No need to return it to in progress.

The source conflict is verified: container-global `AGENTS.md` prescribes Codex plus DeepSeek V4.1 Flash, while this repository's profile pins DeepSeek V4 Pro.
The actual review followed the container-global model choice; its original driver did not document why it preferred that source, so no internal rationale is asserted.
This is an explicit post-review owner exception, not a claim that the repository profile originally named Flash or that a V4 Pro implementation adjudication ran.
The earlier proposed In Progress decision was withdrawn before any state change, as the owner directed.
All C1-C4 and DoD items are verified, with the independent-review item qualified by that authorization.
The closing decision is Done once this evidence PR has its own completed current-head review, green CI, and guarded merge; no implementation item remains outstanding.
The historical implementation review also says 776 tests passed while both linked CI runs report 790; that count discrepancy is non-blocking record follow-up for the coordinator.
