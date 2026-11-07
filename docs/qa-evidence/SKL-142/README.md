# SKL-142 QA evidence

## Round 2

Date: 2026-11-07 UTC, independent QA round 2.
Acceptance basis: the product owner ruled that the acceptance criteria and Definition of Done stand exactly as written and no AC is amended, so every item is judged against its text.
Build under test: `main` at `a73ef64c527beba8ffb8fb9f59c6e4e123dbb787`, whose SKL-142 code is the PR 144 squash merge `f9ba006e4f5392d57e81be3b2ea38a1d547dd61f` (reviewed head `b37f71325bdfa475e355378c64e3cec91e15b9bd`), unchanged since.
Environment: the profile lists no environments, so verification ran against the merged code on `main`.
Fixtures for C2: generated ed25519 test keys and a probe-owned ssh-agent, with a temporary `HOME` and `GIT_CONFIG_GLOBAL`.
Fixtures for C6: the real agent holding the registered key `SHA256:Kj2Cb8r6b1YQ5hksGDH0FeiivWj1DZ8puXI8+IlN9l0` and the unregistered key `SHA256:Mr7r0feKeSqWjnxw0JQa1kywdtfK+hhp8sBn3nfX6XM`, in a throwaway clone at PR 144's head `b37f71325bdfa475e355378c64e3cec91e15b9bd`.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-142 as the "QA r2" attachments.

| Item | Verdict | Evidence |
|---|---|---|
| C1: profile key | Verified | The pattern is exactly `^SHA256:[A-Za-z0-9+/]{43}$`, both descriptions are present and the key is not required. Empty, space, tab, null, 42 and 44 characters, padded, leading and trailing space, MD5 prefix, `-` character and boolean values fail, and a profile without the key validates. |
| C2: preflight | Not met | Vendoring, the `bash` invocation and 27 of 30 hermetic cases behave as specified. A `gpg.ssh.defaultKeyCommand` first line beginning `ssh-` (for example `ssh-add -L`) exits 0 for a matching loaded key, where AC (3) requires the line to begin with `key::` and malformed command output to exit non-zero. A bare `ssh-` `user.signingkey` literal exits 0, which is none of the three forms AC (2) lists. |
| C3: skills use it | Verified | The Commits and signing section of `shared/github.md` states the rule once with the stop and no-override sentences, all 13 `references/github.md` copies match it, and no `SKILL.md` or other `shared/` file mentions the script. |
| C4: docs | Verified | The README "Commit signing key" section gives the meaning, the relation to `git.signed_commits`, the unset behaviour and the preflight command, and `profile/example.yaml` shows `signing_key` under `signed_commits`. |
| C5: tests | Verified | `uv run --locked pytest -q` reports 1216 passed, `vendor_shared.py --check` exits 0, CI run 42309941844 succeeded on PR 144's head `b37f713`, and the PR 144 body records the mutations. |
| C6: verified end to end | Verified | With the unregistered key selected the preflight exits 1 on both paths and no commit is made. With the registered key it exits 0 on both paths, and fixture commits `6c0564d4b6b54693ede46273cd838ae8e8a57df2` and `555213312c2dac97c5dc8e36af61a25b776878af` report `verified=true reason=valid`. All fixture branches were deleted and return 404. |
| DoD1: all acceptance criteria met | Not met | C2 is not met. |
| DoD2: tests written and passing | Verified | See C5. |
| DoD3: independently reviewed | Verified | PR review 5808241571 is the review of record at the merged head `b37f71325bdfa475e355378c64e3cec91e15b9bd`, by the profile's reviewer and adjudicator. |
| DoD4: docs updated | Verified | See C1 and C4. |
| DoD5: verified in a deployed environment | Not applicable, covered by C6 | The profile lists no environments. |
| DoD6: no critical bugs or regressions | Verified | The full suite and CI are green. |

Closing decision: In Progress, because the delivered preflight accepts `ssh-` key forms that C2 as written does not allow.

## Round 1

Date: 2026-11-06 UTC, independent QA round 1.
Story: SKL-142 - profile-defined commit signing key with a preflight check.
Build under test: `f9ba006e4f5392d57e81be3b2ea38a1d547dd61f`, the squash merge of PR 144, whose reviewed head was `b37f71325bdfa475e355378c64e3cec91e15b9bd`.
The SKL-142 files at the build are identical to that head; the build adds only the unrelated SKL-204 changes merged before it.
Environment: a checkout of `origin/main` at the build SHA.
The profile lists no environments and this repository deploys nothing, so `main` at the merge commit is the deployed-build equivalent.
CI: run 42309941844 on the reviewed head and run 42313522305 on the build SHA, both successful.

Fixtures for C2: generated ed25519 test keys and a probe-owned ssh-agent, with a temporary `HOME`, `GIT_CONFIG_GLOBAL` and `SSH_AUTH_SOCK`.
Fixtures for C6: the real agent holding the registered key `SHA256:Kj2Cb8r6b1YQ5hksGDH0FeiivWj1DZ8puXI8+IlN9l0` and the unregistered `~/.ssh/id_ed25519.pub` key `SHA256:Mr7r0feKeSqWjnxw0JQa1kywdtfK+hhp8sBn3nfX6XM`, in a throwaway clone.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output and a self-contained evidence page are attached to SKL-142.

| Item | Verdict | Evidence |
|---|---|---|
| C1: profile key | Verified | `git.signing_key` is an optional string with the pattern `^SHA256:[A-Za-z0-9+/]{43}$` and a description, and `git.signed_commits` has a description naming `git.signing_key`. Empty, space, tab, null, 42 and 44 characters, padded, leading space, MD5 prefix, `-` character and boolean values fail validation, and a profile without the key validates. |
| C2: preflight | Pending product-owner decision | `skills.json` lists the script for the 13 skills that receive `shared/github.md`, and each vendored copy is the generated header plus the source and not executable. Through the vendored copy run with `bash`, every case the AC lists gives the specified exit, exactly one stderr line naming the expected and resolved fingerprints, empty stdout, and no private key material or path. The preflight also accepts a `gpg.ssh.defaultKeyCommand` first line beginning `ssh-` and a bare `ssh-` `user.signingkey` literal, which the AC does not list; git 2.43.0 signs with both forms. |
| C3: skills use it | Verified | The Commits and signing section of `shared/github.md` states the rule once, all 13 `references/github.md` copies match it, and no `SKILL.md` or other `shared/` file mentions the script. |
| C4: docs | Verified | The README "Commit signing key" section gives the key's meaning, its relation to `git.signed_commits`, the unset behaviour and the preflight command, and `profile/example.yaml` shows `signing_key` under `signed_commits`. |
| C5: tests | Verified | `tests/test_signing_key.py` runs hermetically and covers every case the AC lists, and the PR body records the mutations. `uv run --locked pytest -q` reports 1216 passed at the build, and `uv run --locked python scripts/vendor_shared.py --check` exits 0. |
| C6: verified end to end | Verified | At the build, the preflight exits 1 with the unregistered key selected through `user.signingkey` and through `gpg.ssh.defaultKeyCommand`, and no commit is made. With the registered key it exits 0 on both paths, and fixture commits `e95da2e335b3ae6153dd556b5d445a70d560cf23` and `aca2ce868ff14cf4ad58e38bcf5e6009dc53c939` report `verified: true` with reason `valid`. Both fixture branches were deleted and confirmed absent. |
| DoD1: all acceptance criteria met | Pending | Waits on the C2 decision. |
| DoD2: tests written and passing | Verified | See C5. |
| DoD3: independently reviewed | Verified | PR review 5808241571 is the review of record at `b37f71325bdfa475e355378c64e3cec91e15b9bd`, the merged head, by the profile's reviewer and adjudicator, posted before the merge. |
| DoD4: docs updated | Verified | See C1 and C4. |
| DoD5: verified in a deployed environment | Not applicable, covered by C6 | The profile lists no environments. |
| DoD6: no critical bugs or regressions | Verified | The full suite and CI are green at the build. |

Incidental, non-blocking: python-jsonschema accepts the valid fingerprint followed by a trailing newline, because Python's `$` matches before a final newline and ECMA-262's does not.
The AC fixes this pattern, and the preflight rejects such an argument.

Closing decision: the story stays in In Deployment Review until the product owner decides the C2 amendment that the preflight accepts a `ssh-` key line as git does.
