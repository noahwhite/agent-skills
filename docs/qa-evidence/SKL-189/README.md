# SKL-189 QA evidence - round 4

Date: 2026-11-02.
This CLI/configuration change has no visual surface, screenshots or hosted page.
The story comment titled "SKL-189 QA round 4 - 2026-11-02" carries the raw assertion attachment `SKL-189-qa-round-4-assertions.txt`, SHA256 `65a2b87c2c84a83884781e97793e2fb02e0ff01fca64e63e86730249a26271bb`.
It includes fresh assertions and the checksum-verified historical round-three attachment (`781feb1e4ee4439b0978dbab206b2aacb39cc3a03e876e2f3abaa5cda022ea1c`), which includes round two (`b865acdeb29b11a8835d8808d5647c1c08c72afd18e9fbd6574a05aaad993c1b`).
The story comment titled "SKL-189 QA round 4 - AC5 ceremony supplement" carries `SKL-189-qa-round-4-ceremony-supplement.txt`, SHA256 `99fd8a911970a00066d2b5d9505e47672c8371ccfbed93b3f2a33e3854ffbe7d`.
It adds fresh bounded review-ceremony observations, independent ledger/file assertions, CI head/status/conclusion and gate attempt history through the first accepted arbitration.
Historical shadow/refinement execution and engineering regression are retained observations, not newly executed ceremonies or tests.
The prior signed README at `0a87d5cf33b81e724007167611ed0ca929abf0e3` was inspected; no interrupted gate phase from earlier rounds is accepted.

## Scope ruling

The product owner ruling, quoted verbatim in the identified round-four QA comment on 2026-11-02, is: "The consumer-side three-engineer roster gap between the two merged repositories is SKL-177's work, not SKL-189's. SKL-189 is assessed on its own criteria, and the roster gap is left to SKL-177."
This supersedes the earlier QA rounds' use of that gap to withhold SKL-189 sign-off, not their raw observations.
The current combined consumer profile still fails the later three-reviewer schema; this evidence does not claim that build is wholly green.
The untouched owner-authorised run profile also fails that later schema because it still has two refinement reviewers; its refresh remains separately owned, not silently repaired for this evidence run.
SKL-177 owns the consumer roster rollout and rebuild; SKL-181 separately owns the repository profile third reviewer/validation guard, with the authorised run-profile refresh belonging to its owner.
Both were Backlog when read, and neither profile was silently repaired by QA.

## Builds and fixtures

- Fresh detached fetched upstream `origin/main`: `f3ec7e9939d38271c25726b685084f0d7a2675db`, containing SKL-189 merge `cc869232b411c9728cd883f922dd1f062f0ea2bd` and later SKL-175.
- Fresh detached fetched consumer repository `origin/main`: `f6ad11e29cebcc80214ff2814dbfa5d03500802e`.
- Fresh local image: `opencode-env:skl189-qa-round4`, ID `sha256:1966c507937c4c5727195d826fd6d8050f8fafc1fd13bc0860deff698c6a33ec`, built with the upstream SHA above.
- Fixtures: consumer GLM-5.3-Flash optional entry, omitted-flag sibling, two shadow entries and three distinct-family refinement entries with one disabled.
- Seat commands are deterministic spies, not paid-provider availability checks or a full ceremony.
- Original checkout HEAD/status and the consumer's existing `docker-compose.yml` modification were preserved, as recorded in `checkout-integrity.json`.
- Evidence gates use the owner-authorised profile, including the explicit `kimi/kimi-k3` arbiter override; the supplement records completed attempts, including failed attempts that were not accepted.

## Per-item verdicts

Every evidence filename below is a section in the raw tracker attachment or the round-four ceremony supplement, not an additional repository file.

| Item | Verdict | Evidence and limitation |
|---|---|---|
| AC1 | Verified | Fresh `schema-assertions.json`: valid baseline; booleans/omission accepted; string/null/numeric/unknown-key controls reject; default true and closed agent properties checked. |
| AC2 | Verified on bounded execution fixtures | Fresh `optional-assertions.json` and `prior-execution-recheck.json`: disabled entries have zero launches/reports and named disabled evidence; historical shadow/refinement source hashes, ledgers and report sets independently rechecked. |
| AC3 | Verified | Fresh schema probe rejects false for reviewer, adjudicator, hunter, arbiter and both mandatory refinement roles before launch. |
| AC4 | Verified in story scope | README lines 99-106 explain whole-text reading and more tokens than deletion/about the same as commenting; inspected consumer policy retains missing-entry, unknown-key and stale-route guards; historical original-story-schema control passed 215 tests; later roster incompatibility remains SKL-177-owned. |
| AC5 | Verified on bounded consumer-derived review ceremony | `ceremony-independent-assertions.json` in the supplement: GLM disabled 0 launches/no report versus re-enabled 2 batches/report; enabled sibling, mandatory reviewer/adjudicator, shadow and local posting/readback complete in both scenarios with identical remaining ledgers and output bytes. |
| DoD: all acceptance criteria met | Verified in story scope | AC1-5 observations above, assessed under the explicit product owner ruling. |
| DoD: tests written and passing | Verified in story scope | Upstream CI readback: 1017 passed; unchanged historical consumer regression: 8/9 scripts pass, optional suite 213 passed/2 roster failures; original-story-schema control 215 passed; no whole-build green claim. |
| DoD: independently reviewed | Verified | Fresh API records bind both implementation review comments to the exact final heads in both commit ID and first-line SHA. |
| DoD: docs updated | Verified | Upstream README and consumer README/code-review/engineering-workflow overlays inspected on fetched main. |
| DoD: deployed verification | Verified for delivered artifacts | Fresh `image-assertions.json`: seven baked/installed source hashes match; installed launcher prints GLM disabled without touching spy; roster compatibility is separately owned. |
| DoD: no critical bugs/regressions | Verified in story scope | No toggle failure found in schema/launcher/image probes and retained bounded execution/regression evidence; whole-build roster failure is not hidden. |

## Execution bounds and provenance

Fresh schema execution matched 18 expected outcomes on a valid baseline.
Optional execution drove the actual merged launcher over the consumer story diff against `cbb6b816bf45d5979126fb05649da1476c5d17ca`.
The supplemental fixture executes engineering-workflow steps 6-7 and local review-posting instructions, not the full implementation/merge/deploy workflow.
Its paired consumer-derived profiles differ only by GLM `enabled: false` to `true`; fixture controls add an enabled optional sibling and a shadow, while all seat commands are deterministic doubles.
Both scenarios produce two enabled-sibling batches followed by one mandatory reviewer, one adjudicator and one shadow launch; only the re-enabled scenario adds two GLM batches.
Independent checks confirm identical remaining launch ledgers and reviewer/adjudicator/shadow output bytes, identical adjudicator/shadow inputs, six changed files read by a local detached-worktree harness, and successful local COMMENTED posting/readback doubles at the full consumer head.
Scenario-prefixed report labels isolate files while ledgers retain configured names; the disabled evidence names GLM explicitly and no disabled report is read or required.
This does not validate provider availability, independent review substance, real GitHub posting, implementation, merge or deploy.
Historical shadow execution left the disabled command/report absent while its enabled sibling ran once; re-enabling produced one launch per shadow.
Historical refinement stopped with `disabled-engineer: disabled` before any PO preflight or voter launch when only two of three entries were enabled.
Re-enabling allowed one sandbox PO-preflight double and three voter doubles, stopping before real tracker writes, reconciliation or pointing.
Fresh independent ledger/report checks and unchanged skill-source hashes support reuse, not a claim that round four reran those scenarios.
Image verification ran the exact entrypoint agent-skills install block in a fresh disposable network-disabled container without host mounts or credentials, not full firewall/Tailscale startup.
Installed profile SHA256 is `16b08c6ab6d7ba3951329c3a2db233e9eb8a63aeefab3e255bf611c20a71821e`; schema SHA256 is `19f0218a448825ed85c4f81854b07c24d2b7678b7468570948aecbc0f94162fa`.
Upstream [implementation review](https://github.com/noahwhite/agent-skills/pull/132#pullrequestreview-5731312200) covers `cd09a9cc169c204179d64c52125aa23a4249d226`; consumer implementation review ID `5731338579` covers `14b95f1e4f1984f5edef9ae80cb5083e3a151f96`.
Consumer workspace/repository URLs stay in the tracker attachments, not this public repository's evidence file.
Upstream merged-main [CI run](https://github.com/noahwhite/agent-skills/actions/runs/41377883264) completed successfully with 1017 passed; status and logs were freshly read.
The supplement records that run's head `f3ec7e9939d38271c25726b685084f0d7a2675db`, status `completed` and conclusion `success`; local evidence preflight passes separately, without a claim of equivalent test collection or coverage.
All ten retained engineering regression/control log hashes match at unchanged source heads; the 215-pass original-story-schema control does not replace the two current-schema failures.
Missing-entry guards are direct assertions, stale-route guards are lexical scans, and the accepted mid-sentence launch-verb blind spot remains a limitation, not a runtime safety proof.
The consumer string-enabled negative control can be masked by the roster error; the independent schema probe avoids that by using a valid baseline.
Historical digest labels describe the original downloaded files; round three's embedding adds one trailing newline around the round-two block, so re-hash the original round-two attachment rather than that padded substring.
