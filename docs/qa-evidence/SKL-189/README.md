# SKL-189 QA evidence - rounds 2 and 3

Date: 2026-11-02.
This is a CLI/configuration change, with no visual surface, screenshots or hosted page.
The [round-three QA comment](https://linear.app/officina-pub/issue/SKL-189/user-story-let-a-profile-seat-be-configured-but-disabled#comment-fec883d5) links the raw assertion attachment named `SKL-189 QA round 3 - fresh artifact assertions and retained regression proof`.
Its SHA256 is `781feb1e4ee4439b0978dbab206b2aacb39cc3a03e876e2f3abaa5cda022ea1c`.
That attachment is the raw record behind every table row: fresh assertions plus the complete checksum-verified round-two attachment, explicitly labelled historical.
The [round-two QA comment](https://linear.app/officina-pub/issue/SKL-189/user-story-let-a-profile-seat-be-configured-but-disabled#comment-7594fdb4) links that historical attachment, SHA256 `b865acdeb29b11a8835d8808d5647c1c08c72afd18e9fbd6574a05aaad993c1b`.
Round three reused the signed round-two README's observations after independent provenance checks; no interrupted gate phase was accepted.

## Builds and fixtures

- Upstream: fresh detached fetched `origin/main` at `f3ec7e9939d38271c25726b685084f0d7a2675db`, containing SKL-189 `cc869232b411c9728cd883f922dd1f062f0ea2bd` and the later SKL-175 schema change.
- Consumer: fresh detached fetched `origin/main` at `f6ad11e29cebcc80214ff2814dbfa5d03500802e` in `officina-pub/opencode-dev-container`.
- Round-three image: locally rebuilt `opencode-env:skl189-qa-round3`, ID `sha256:85fd4e7825bfb32e98beb82dc593ae5e4fb94d3324678eb9299596fb82408adc`, with the upstream SHA above and `OPENCODE_CLI_VERSION=2.2.5`.
- Historical round-two image: `opencode-env:skl189-qa-round2`, ID `sha256:944b32cfb01a6d48023879350c2d1b58bdcde670c132d3e420ff80483b112f2b`.
- Fixtures: consumer GLM-5.3-Flash optional seat, omitted-flag enabled sibling, two shadow seats and three distinct-family refinement entries with one disabled.
- Seat commands are deterministic spies, not paid-provider availability checks or a full live ceremony.
- Original checkout HEAD/status values, existing running containers and shared `latest` image were preserved.
- Gate/review seats come from the unchanged owner-authorised run profile; its arbiter override is `kimi/kimi-k3`.

## Per-item verdicts

| Item | Verdict | Evidence and limitation |
|---|---|---|
| AC1 | Verified | Fresh `schema-assertions.json`: true, false and omission accepted; string, null, numeric and unknown-key controls rejected on a valid baseline; default true and additionalProperties false checked. |
| AC2 | Verified on bounded execution fixtures | Fresh `optional-assertions.json` plus `prior-execution-recheck.json`: disabled optional seat launches nothing; historical shadow/refinement source hashes, ledgers and report sets independently rechecked, with zero disabled launches/reports and named disabled evidence. |
| AC3 | Verified | Fresh schema probe rejects false for reviewer, adjudicator, hunter, arbiter and both mandatory refinement roles before any launch. |
| AC4 | Toggle rules verified; current consumer integration blocked | README lines 99-106 explain whole-text reading and token costs; policy source retains missing-entry assertions, unknown-key controls and stale-route static scans; current whole-profile acceptance fails on the later three-reviewer requirement. |
| AC5 | Verified on real-consumer-derived fixture | Fresh GLM disable: 0 launches/no report; omitted sibling: 2 batch launches; same-run one-word re-enable: 2 batch launches and report. |
| DoD: all acceptance criteria met | Not met in current combined build | AC4 current-schema consumer integration remains blocked on separately owned rollout. |
| DoD: tests written and passing | Not met in current combined build | Fresh upstream CI read-back: 1017 tests passed; retained engineering-owned consumer regression at identical source heads has 8/9 scripts passing and 2 roster-related failures. |
| DoD: independently reviewed | Verified | Fresh GitHub API records bind both implementation reviews to their exact final heads, in API commit ID and review first-line SHA. |
| DoD: documentation updated | Verified | Upstream README and consumer README/code-review/engineering-workflow overlays inspected on fetched main. |
| DoD: deployed verification | Artifact delivery verified; integration blocked | Fresh image install has seven source hash matches; installed launcher emits GLM disabled without touching spy; whole-profile compatibility remains invalid. |
| DoD: no critical bugs/regressions | Combined-build sign-off withheld | No toggle failure found; later-schema roster incompatibility prevents green consumer integration sign-off. |

## Executed observations and retained evidence

Round-three fresh probes exercised 18 expected schema outcomes and the actual optional launcher over the consumer story diff against `cbb6b816bf45d5979126fb05649da1476c5d17ca`.
Disabled optional execution prints `GLM-5.3-Flash: disabled`, with zero launch-ledger events and no report; omitted and re-enabled controls each execute two batches.
Round-two actual-skill shadow execution recorded `disabled-shadow: disabled`, launched no disabled command and wrote no disabled report while its enabled sibling ran once; re-enabling produced one launch per shadow.
Round-two refinement execution stopped with `disabled-engineer: disabled` before PO preflight or voter launch when only two of three entries were enabled.
Re-enabling allowed one sandbox PO-preflight double and three voter doubles, stopping before real tracker writes, reconciliation or pointing.
Round three did not re-execute those shadow/refinement scenarios: it verified unchanged source hashes and independently checked all four historical scenario ledgers/report sets against the attached record.
Image verification ran the exact entrypoint agent-skills install block in a fresh disposable network-disabled container without host mounts or credentials, not full firewall/Tailscale startup.
Installed profile SHA256 is `16b08c6ab6d7ba3951329c3a2db233e9eb8a63aeefab3e255bf611c20a71821e`; schema SHA256 is `19f0218a448825ed85c4f81854b07c24d2b7678b7468570948aecbc0f94162fa`.
Profile, schema, optional launcher, refinement skill, code-review reference and baked OpenCode config all match fetched source hashes.

## Review and regression provenance

- Upstream implementation: [review of record](https://github.com/noahwhite/agent-skills/pull/132#pullrequestreview-5731312200), head `cd09a9cc169c204179d64c52125aa23a4249d226`.
- Consumer implementation: [review of record](https://github.com/officina-pub/opencode-dev-container/pull/67#pullrequestreview-5731338579), head `14b95f1e4f1984f5edef9ae80cb5083e3a151f96`.
- Upstream merged-main [CI run](https://github.com/noahwhite/agent-skills/actions/runs/41377883264): completed successfully, 1017 passed; status and log freshly read in round three.
- Retained engineering-owned regression: all nine consumer shell entrypoints ran at the same source heads; eight passed, one failed, zero skips; raw log hashes independently matched in round three.
- The optional-reviewer suite reported 213 passed/2 failed at `refinement.reviewers`; labelled original-SKL-189-schema control reported 215 passed and does not replace the current-schema failure.
- Missing-entry guards are direct assertions without removal-mutation controls; stale-route guards are lexical scans without scanner-wide injected-file controls, not runtime absence proofs.
- The consumer string-enabled negative test can be masked by the unrelated roster error; the independent schema probe uses a valid baseline and enabled-specific errors.
- The previously accepted mid-sentence launch-verb blind spot remains a policy-scan limitation, not a newly discovered toggle defect.

## Remaining owner action

[SKL-175](https://linear.app/officina-pub/issue/SKL-175/user-story-seat-three-engineers-as-estimators) tightened the schema to exactly three refinement reviewers after SKL-189 landed.
The consumer and untouched authorised run profile each still have two, so neither validates against current main; the unchanged consumer does validate against SKL-189's original schema.
[SKL-177](https://linear.app/officina-pub/issue/SKL-177/user-story-cross-repository-rollout-of-the-three-engineer-voter-set), Backlog when read, owns the consumer third reviewer and rebuild.
Its implementation/deployment owner must deliver the compatible roster; QA then repeats current-profile integration and installed-profile checks.
[SKL-181](https://linear.app/officina-pub/issue/SKL-181/user-story-seat-three-engineers-in-the-agent-skills-profiles), also Backlog when read, owns the repository third reviewer and validation guard; the authorised run-profile owner must refresh that copy.
No source profile was silently repaired and no toggle implementation fix is inferred from this later-schema incompatibility.
