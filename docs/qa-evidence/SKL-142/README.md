# SKL-142 QA evidence

## Round 4

Date: 2026-11-07 UTC, independent QA round 4.
Acceptance basis: the product owner ruled that the acceptance criteria and Definition of Done stand exactly as written and no AC is amended, so every item is judged against its text.
Build under test: `main` at `db0db290b79920ff7513ed897bc48eb23acc2e4c`, the squash merge of PR 153, whose reviewed head is `6fd16c57cd48deb018237f73d428b6ff6385af3a`; no SKL-142 file differs between the two.
Environment: the profile lists no environments, so C1 to C5 were verified against the merged code on `main`, and C6 ran at PR 153's head, as C6 requires.
Tool versions: git 2.43.0 and OpenSSH 9.6p1.
Fixtures for C2: generated ed25519, rsa, ecdsa and PEM test keys, some passphrase-protected, and a probe-owned ssh-agent, with a temporary `HOME` and `GIT_CONFIG_GLOBAL`; each case is compared with `git commit -S` under the same configuration.
Fixtures for C6: the real agent holding the registered key `SHA256:Kj2Cb8r6b1YQ5hksGDH0FeiivWj1DZ8puXI8+IlN9l0` and the unregistered key `SHA256:Mr7r0feKeSqWjnxw0JQa1kywdtfK+hhp8sBn3nfX6XM`, in a throwaway clone at `6fd16c57cd48deb018237f73d428b6ff6385af3a`.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-142 as the "QA r4" attachments.

| Item | Verdict | Evidence |
|---|---|---|
| C1: profile key | Verified | 25 of 25 schema cases pass: the pattern is exactly `^SHA256:[A-Za-z0-9+/]{43}$`, both descriptions are present, the key is not required, the malformed values fail, and a profile without the key validates. |
| C2: preflight | Not met | Vendoring to all 13 skills and the `bash` invocation behave as specified, and 56 of 59 hermetic cases behave as specified. Those 56 include the round 3 passphrase-protected private-key file, which now resolves with and without its `.pub`, and the round 2 bare `ssh-` forms (a `user.signingkey` literal and an `ssh-add -L` default key command), which exit 1 as AC (2) and (3) require although git signs with them. Three cases exit 1 with `resolved unresolved` although git 2.43.0 signs with that key (`git commit -S` exits 0, signature status `G` by that key): U27, a public-key file in `user.signingkey` reached through a `~<user>/` path, which the script does not expand (`shared/check-signing-key.sh` line 149 expands only `~/`); U29, a PEM private-key file with a line before its header and a matching `.pub`; and D16, a relative `gpg.ssh.defaultKeyCommand` with the preflight run from a subdirectory, which git runs from the top of the work tree and the script runs from the current directory (line 176). AC (2) and (3) require the script to resolve the key git would sign with, and none of these is a mismatch, an unresolvable key, or an unloaded key. The verdict rests on U27 and U29, which run from the top of the work tree. No case exits 0 where git would sign with another key. |
| C3: skills use it | Verified | The Commits and signing section of `shared/github.md` states each rule sentence once, all 13 `references/github.md` copies match it, and no `SKILL.md` or other `shared/` file restates the rule. |
| C4: docs | Verified | The README "Commit signing key" section under "Profile" covers the key, and `profile/example.yaml` shows `signing_key` directly under `signed_commits`. |
| C5: tests | Verified | `uv run --locked pytest -q` reports 1285 passed, `tests/test_signing_key.py` 147 passed, `vendor_shared.py --check` exits 0, CI succeeded on PR 153's head `6fd16c5` (run 42337045516), the PR 144 body records the mutations, and a diff read confirms the new passphrase tests drive the script and compare with git. |
| C6: verified end to end | Verified | With the unregistered key selected the preflight exits 1 on both paths and HEAD is unchanged. With the registered key it exits 0 on both paths, and fixture commits `c4d863212d5c40dd05cd9fbe72f9e0e5c597beee` (`user.signingkey` `key::` literal) and `12dd93c7941d1bab5426b4c78356eafd11751997` (container default key command, `user.signingkey` unset) report `verified=true reason=valid`. Both fixture branches were deleted by an exit trap and are absent. |
| DoD1: all acceptance criteria met | Not met | C2 is not met. |
| DoD2: tests written and passing | Verified | See C5. |
| DoD3: independently reviewed | Verified | PR 144 review 5808241571 at `b37f71325bdfa475e355378c64e3cec91e15b9bd`, PR 149 review 5809477523 at `b130f9246c69dec570b79186ec5408856b856e01` and PR 153 review 5810010818 at `6fd16c57cd48deb018237f73d428b6ff6385af3a` are the reviews of record at the merged heads, by the profile's reviewer and adjudicator. |
| DoD4: docs updated | Verified | See C1 and C4. |
| DoD5: verified in a deployed environment | Not applicable, covered by C6 | The profile lists no environments. |
| DoD6: no critical bugs or regressions | Verified | The full suite and CI are green; the C2 gaps fail closed. |

Closing decision: In Progress, because the delivered preflight refuses a `~<user>/` public-key path and a PEM private-key file with a leading line, both of which git signs with and C2 as written requires the script to resolve.

## Round 3

Date: 2026-11-07 UTC, independent QA round 3.
Acceptance basis: the product owner ruled that the acceptance criteria and Definition of Done stand exactly as written and no AC is amended, so every item is judged against its text.
Build under test: `main` at `ce1f2757ed247d5fa794bf52d74658416280e1aa`, the squash merge of PR 149, whose reviewed head `b130f9246c69dec570b79186ec5408856b856e01` has the identical tree.
Environment: the profile lists no environments, so C1 to C5 were verified against the merged code on `main`, and C6 ran at PR 149's head, as C6 requires.
Tool versions: git 2.43.0 and OpenSSH 9.6p1.
Fixtures for C2: generated ed25519 test keys, one of them passphrase-protected, and a probe-owned ssh-agent, with a temporary `HOME` and `GIT_CONFIG_GLOBAL`.
Fixtures for C6: the real agent holding the registered key `SHA256:Kj2Cb8r6b1YQ5hksGDH0FeiivWj1DZ8puXI8+IlN9l0` and the unregistered key `SHA256:Mr7r0feKeSqWjnxw0JQa1kywdtfK+hhp8sBn3nfX6XM`, in a throwaway clone at `b130f9246c69dec570b79186ec5408856b856e01`.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-142 as the "QA r3" attachments.

| Item | Verdict | Evidence |
|---|---|---|
| C1: profile key | Verified | The pattern is exactly `^SHA256:[A-Za-z0-9+/]{43}$`, both descriptions are present and the key is not required. Empty, space, tab, null, 42 and 44 characters, padded, leading and trailing space, MD5 and lowercase prefixes, `-` character, boolean and integer values fail, and a profile without the key validates, with the same result as under the schema before SKL-142. |
| C2: preflight | Not met | Vendoring, the `bash` invocation and 43 of 43 hermetic cases behave as specified, including a bare `ssh-` `user.signingkey` literal and a `ssh-add -L` default key command, which now exit 1. A passphrase-protected private-key file in `user.signingkey`, whose key is the registered one and is loaded in the agent, exits 1 with `resolved unresolved: user.signingkey cannot be resolved`, with or without its `.pub` file beside it. git 2.43.0 signs with that file (`git commit -S` exits 0, signature status `G` by that key), and `ssh-keygen -lf` reads its fingerprint without the passphrase. AC (2) names a private-key file as a resolvable form, and the key is neither a mismatch, unresolvable, nor unloaded, so none of the AC's non-zero cases applies. |
| C3: skills use it | Verified | The Commits and signing section of `shared/github.md` states each rule sentence once, all 13 `references/github.md` copies match it, and no `SKILL.md` and no `shared/` file other than `shared/github.md` and `shared/check-signing-key.sh` itself mentions the script or the key. |
| C4: docs | Verified | The README "Commit signing key" section under "Profile" gives the meaning, the relation to `git.signed_commits`, the unset behaviour and the preflight command, and `profile/example.yaml` shows `signing_key` directly under `signed_commits`. |
| C5: tests | Verified | `uv run --locked pytest -q` reports 1216 passed, `tests/test_signing_key.py` 97 passed, `vendor_shared.py --check` exits 0, CI succeeded on PR 144's head `b37f713` (run 42309941844) and PR 149's head `b130f92` (run 42328743708), and the PR 144 body records the mutations. |
| C6: verified end to end | Verified | With the unregistered key selected the preflight exits 1 on both paths and HEAD is unchanged. With the registered key it exits 0 on both paths, and fixture commits `9a1ef5790e8f73a3abf9df2f1f1dc08ab18ddccb` (`user.signingkey` `key::` literal) and `650a05fdcb989808503e9d21af6622f5b3ae8d8d` (container default key command, `user.signingkey` unset) report `verified=true reason=valid`. Both fixture branches were deleted by an exit trap and return 404. |
| DoD1: all acceptance criteria met | Not met | C2 is not met. |
| DoD2: tests written and passing | Verified | See C5. |
| DoD3: independently reviewed | Verified | PR 144 review 5808241571 at `b37f71325bdfa475e355378c64e3cec91e15b9bd` and PR 149 review 5809477523 at `b130f9246c69dec570b79186ec5408856b856e01` are the reviews of record at the merged heads, by the profile's reviewer and adjudicator. |
| DoD4: docs updated | Verified | See C1 and C4. |
| DoD5: verified in a deployed environment | Not applicable, covered by C6 | The profile lists no environments. |
| DoD6: no critical bugs or regressions | Verified | The full suite and CI are green; the C2 gap fails closed. |

Closing decision: In Progress, because the delivered preflight refuses a passphrase-protected private-key file that git signs with, which C2 as written requires it to resolve.

## Round 2

Date: 2026-11-07 UTC, independent QA round 2.
Acceptance basis: the product owner ruled that the acceptance criteria and Definition of Done stand exactly as written and no AC is amended, so every item is judged against its text.
Build under test: `main` at `a73ef64c527beba8ffb8fb9f59c6e4e123dbb787`, whose SKL-142 code is the PR 144 squash merge `f9ba006e4f5392d57e81be3b2ea38a1d547dd61f` (reviewed head `b37f71325bdfa475e355378c64e3cec91e15b9bd`), unchanged since.
Environment: the profile lists no environments, so C1 to C5 were verified against the merged code on `main`, and C6 ran at PR 144's head, as C6 requires; the SKL-142 files are identical at both commits.
Fixtures for C2: generated ed25519 test keys and a probe-owned ssh-agent, with a temporary `HOME` and `GIT_CONFIG_GLOBAL`.
Fixtures for C6: the real agent holding the registered key `SHA256:Kj2Cb8r6b1YQ5hksGDH0FeiivWj1DZ8puXI8+IlN9l0` and the unregistered key `SHA256:Mr7r0feKeSqWjnxw0JQa1kywdtfK+hhp8sBn3nfX6XM`, in a throwaway clone at PR 144's head `b37f71325bdfa475e355378c64e3cec91e15b9bd`.
There is no visual surface, so the evidence is structured assertions and raw output; no screenshot applies.
The raw probe output is attached to SKL-142 as the "QA r2" attachments.

| Item | Verdict | Evidence |
|---|---|---|
| C1: profile key | Verified | The pattern is exactly `^SHA256:[A-Za-z0-9+/]{43}$`, both descriptions are present and the key is not required. Empty, space, tab, null, 42 and 44 characters, padded, leading and trailing space, MD5 prefix, `-` character and boolean values fail, and a profile without the key validates. |
| C2: preflight | Not met | Vendoring, the `bash` invocation and 27 of 30 hermetic cases behave as specified. A `gpg.ssh.defaultKeyCommand` first line beginning `ssh-` (for example `ssh-add -L`) exits 0 for a matching loaded key, where AC (3) requires the line to begin with `key::` and malformed command output to exit non-zero. A bare `ssh-` `user.signingkey` literal exits 0, which is none of the three forms AC (2) lists. |
| C3: skills use it | Verified | The Commits and signing section of `shared/github.md` states the rule once with the stop and no-override sentences, all 13 `references/github.md` copies match it, and no `SKILL.md` and no `shared/` file other than `shared/github.md` and `shared/check-signing-key.sh` itself mentions the script. |
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
| C3: skills use it | Verified | The Commits and signing section of `shared/github.md` states the rule once, all 13 `references/github.md` copies match it, and no `SKILL.md` and no `shared/` file other than `shared/github.md` and `shared/check-signing-key.sh` itself mentions the script. |
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
