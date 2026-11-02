# SKL-189 QA evidence - rounds 2 and 3

Date: 2026-11-02.
This is a CLI/configuration change, with no visual surface, screenshots or hosted page.
The SKL-189 tracker comment `fec883d5` links the raw attachment named `SKL-189 QA round 3 - fresh artifact assertions and retained regression proof`.
Its SHA256 is `781feb1e4ee4439b0978dbab206b2aacb39cc3a03e876e2f3abaa5cda022ea1c`.
That initial attachment and the correction/reproducibility supplement jointly form the raw record behind the table; the initial attachment alone does not contain the additional profile-flow or corrected historical-recheck observations.
Read it with SKL-189 correction comment `d2ec9c57` and its reproducibility supplement, SHA256 `c3c4d2f98e85a78b2db23a38bef482d298a36822d036a5b1f459d56a9b6cf7fc`.
The supplement supplies probe sources, fixture inputs, the exact image-build invocation/log and the additional on-disk profile-flow observations.
Its corrected `prior-execution-recheck.json` has SHA256 `d0ca02a13f8fb57c8a099f6ebed1b75b95359a90d2a2cce5c70335c4b68a498f`, distinct from the initial attachment's earlier file of the same name.
The SKL-189 round-two tracker comment `7594fdb4` links the historical attachment, SHA256 `b865acdeb29b11a8835d8808d5647c1c08c72afd18e9fbd6574a05aaad993c1b`.
Consumer workspace and repository locators remain on the tracker, not in this public repository.
Intended reviewers with tracker access can resolve the evidence route by running `linear issue view SKL-189 --json` with their normal authenticated CLI: its comments include `fec883d5`, `d2ec9c57` and `7594fdb4`, and its attachments include the exact titles and digests above.
Download those attachments through the returned authenticated locators, then read the supplement's `source-assertions.json` review records and consumer-profile source section for the full consumer repository, commit and review URLs.
Round three reused the checksum-anchored historical observations in the embedded round-two attachment after independent provenance checks; no interrupted gate phase was accepted.

## Builds and fixtures

- Upstream: fresh detached fetched `origin/main` at `f3ec7e9939d38271c25726b685084f0d7a2675db`, containing SKL-189 `cc869232b411c9728cd883f922dd1f062f0ea2bd` and the later SKL-175 schema change.
- Consumer: fresh detached fetched `origin/main` at `f6ad11e29cebcc80214ff2814dbfa5d03500802e`; repository locator is retained in the private tracker evidence.
- Round-three image: locally rebuilt `opencode-env:skl189-qa-round3`, ID `sha256:85fd4e7825bfb32e98beb82dc593ae5e4fb94d3324678eb9299596fb82408adc`, with the upstream SHA above and `OPENCODE_CLI_VERSION=2.2.5`.
- Historical round-two image: `opencode-env:skl189-qa-round2`, ID `sha256:944b32cfb01a6d48023879350c2d1b58bdcde670c132d3e420ff80483b112f2b`.
- Optional fixtures derive from the consumer GLM-5.3-Flash entry, with deterministic commands replacing provider launches and a synthetic omitted-enabled sibling appended.
- Historical shadow/refinement fixtures are synthetic Example App profiles, not execution of the consumer's own shadow/refinement lists.
- Seat commands are deterministic spies, not paid-provider availability checks or a full live ceremony.
- Original checkout HEAD/status values were compared and unchanged; no baseline of running containers or the shared latest tag was captured, and no preservation assertion is made for those.
- Gate/review seats come from the unchanged owner-authorised run profile; its arbiter override is `kimi/kimi-k3`.

## Per-item verdicts

| Item | Verdict | Evidence and limitation |
|---|---|---|
| AC1 | Verified | Fresh schema controls accept true/false/omission and reject string/null/numeric/unknown keys on a valid baseline; default true is a checked schema annotation, not a jsonschema-applied runtime value; the agent-interpreted Step 6 fixture additionally exercises omission. |
| AC2 | Verified on bounded execution fixtures | Fresh optional execution plus the supplement's corrected `prior-execution-recheck.json`, identified by its SHA256 section header: historical shadow/refinement source hashes, attachment-anchored ledgers and exact report contents checked; zero disabled launches/reports and named disabled evidence. The initial attachment's earlier file of the same name lacks those later checks. |
| AC3 | Verified by schema refusal | Fresh schema probe rejects false for reviewer, adjudicator, hunter, arbiter and both mandatory refinement roles; no live mandatory-disabled gate session is claimed. |
| AC4 | Docs/policy inspected; current integration blocked | Upstream README section Switching a seat off explains text/token cost; source retains presence, unknown-key and lexical stale-route guards; current acceptance loop stops at reviewer count before true/false candidates, whose acceptance is shown by the historical original-schema control only. |
| AC5 | Verified on bounded agent-interpreted consumer fixture | QA read actual Step 6 and an on-disk fixture: GLM false gives 0 launches/no report while the omitted sibling runs 2 batches; QA physically edits only false to true, rereads the file and observes 2 GLM batches/report; see supplement profile-flow assertions/recipe. |
| DoD: all acceptance criteria met | Not met in current combined build | AC4 current-schema consumer integration remains blocked on separately owned rollout. |
| DoD: tests written and passing | Not met in current combined build | Fresh upstream CI read-back: 1017 tests passed; retained engineering-owned consumer regression at identical source heads has 8/9 scripts passing and 2 roster-related failures. |
| DoD: independently reviewed | Verified for implementation | Supplement retains fresh GitHub review id, COMMENTED state, API commit ID, first-line full SHA and body for both exact implementation heads; this evidence PR separately requires its own current-head review of record before merge. |
| DoD: documentation updated | Verified | Upstream README and consumer README/code-review/engineering-workflow overlays inspected on fetched main. |
| DoD: deployed verification | Artifact delivery verified; integration blocked | Seven installed-source hash comparisons match; image launcher explicit disabled CLI branch leaves spy untouched, not an autonomous profile-resolution check; whole-profile compatibility remains invalid. |
| DoD: no critical bugs/regressions | Combined-build sign-off withheld | No toggle failure found; later-schema roster incompatibility prevents green consumer integration sign-off. |

## Executed observations and retained evidence

The initial round-three probe exercised 18 schema outcomes and launcher flags derived from in-memory fixtures; it did not edit/reread a profile and is not the AC5 profile-flow evidence.
The additional QA-agent execution reads actual merged Step 6 and the on-disk consumer-derived profile, then physically edits and rereads the one-word change in the same run.
The skill is agent-interpreted: QA selects explicit lowercase launcher flags from the file as instructed, with omission selecting true; no autonomous executable resolver or full PR ceremony is claimed.
This bounded optional step reviews the consumer merge diff against parent `cbb6b816bf45d5979126fb05649da1476c5d17ca`, not an open PR.
Disabled GLM emits `GLM-5.3-Flash: disabled`, with zero launches/no report at that step; the synthetic omitted sibling and the physically re-enabled GLM each execute two batches and write reports.
Round-two actual-skill shadow execution recorded `disabled-shadow: disabled`, launched no disabled command and wrote no disabled report while its enabled sibling ran once; re-enabling produced one launch per shadow.
Round-two refinement execution stopped with `disabled-engineer: disabled` before PO preflight or voter launch when only two of three entries were enabled.
Re-enabling allowed one sandbox PO-preflight double and three voter doubles, stopping before real tracker writes, reconciliation or pointing.
Round three did not re-execute shadow/refinement: it checked unchanged source hashes, then anchored execution-results JSON and all three existing launch ledgers to SHA256 section headers in the downloaded, checksum-verified historical attachment.
It checked report contents against the exact deterministic spy output newly in round three; report bodies were not separately captured in the historical attachment, and the corrupted copied-report mutant now rejects.
Image verification extracted the unmodified entrypoint agent-skills install block and redirected CONFIG_DIR/PROFILE_DIR into disposable temporary destinations; it ran network-disabled without host mounts/credentials, not full firewall/Tailscale startup or normal persistent-volume destinations.
The image build command/log is in the supplement; the image ID is a local observation, not a registry digest or retained-image guarantee.
Installed profile SHA256 is `16b08c6ab6d7ba3951329c3a2db233e9eb8a63aeefab3e255bf611c20a71821e`; schema SHA256 is `19f0218a448825ed85c4f81854b07c24d2b7678b7468570948aecbc0f94162fa`.
Profile, schema, optional launcher, refinement skill, code-review reference and baked OpenCode config all match fetched source hashes.

## Review and regression provenance

- Upstream implementation: [review of record](https://github.com/noahwhite/agent-skills/pull/132#pullrequestreview-5731312200), head `cd09a9cc169c204179d64c52125aa23a4249d226`.
- Consumer implementation: review record id `5731338579`, head `14b95f1e4f1984f5edef9ae80cb5083e3a151f96`; full locator is retained in the private tracker evidence.
- Upstream merged-main [CI run](https://github.com/noahwhite/agent-skills/actions/runs/41377883264): completed successfully, 1017 passed; status and log freshly read in round three.
- Retained engineering-owned regression: all nine consumer shell entrypoints ran at the same source heads; eight passed, one failed, zero skips; raw log hashes independently matched in round three.
- The optional-reviewer suite reported 213 passed/2 failed at `refinement.reviewers`; labelled original-SKL-189-schema control reported 215 passed and does not replace the current-schema failure.
- Missing-entry guards are direct assertions without removal-mutation controls; stale-route guards are lexical scans without scanner-wide injected-file controls, not runtime absence proofs.
- The consumer string-enabled negative test can be masked by the unrelated roster error; the independent schema probe uses a valid baseline and enabled-specific errors.
- The previously accepted mid-sentence launch-verb blind spot remains a policy-scan limitation, not a newly discovered toggle defect.
- No repository test guards this story-specific evidence document's future links/digests; this evidence-only gap is explicitly accepted, with the recorded attachments and byte checks serving as the current record.
- The existing prose-mapping test mutant M1 can still pass; this documentation-only remediation claims no implementation-test fix, only additional actual-skill observations and narrower evidence wording.

## Remaining owner action

SKL-175 tightened the schema to exactly three refinement reviewers after SKL-189 landed.
The consumer and untouched authorised run profile each still have two, so neither validates against current main; the unchanged consumer does validate against SKL-189's original schema.
SKL-177, Backlog when read, owns the consumer third reviewer and rebuild.
Its implementation/deployment owner must deliver the compatible roster; QA then repeats current-profile integration and installed-profile checks.
SKL-181, also Backlog when read, owns the repository third reviewer and validation guard; the authorised run-profile owner must refresh that copy.
No source profile was silently repaired and no toggle implementation fix is inferred from this later-schema incompatibility.
