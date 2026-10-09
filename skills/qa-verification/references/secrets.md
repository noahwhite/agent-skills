<!-- GENERATED from shared/secrets.md by scripts/vendor_shared.py. Edit the source, then rerun the script. -->

# Secrets and security discipline

Read this before handling secrets, tokens, credentials, untrusted input, or security fixes.
Where the project's secrets live and how they reach their consumers is consumer overlay detail (see `references/profile.md`).

## Handling secret values

- ⛔ Never let a secret value reach any output stream: CI logs, local shell output, or the conversation transcript.
  This covers the ad-hoc commands you run, not only the logging code you write.
- ⛔ Never `cat`, `grep`, or `echo` a file or response that can contain credentials (IaC backend config, Terraform or OpenTofu state, secrets-manager output, `docker inspect`, environment dumps).
  To inspect one, filter to an allowlist of exact field names, never a substring like `key`, which also matches `access_key` and `secret_key`.
- ⛔ Never print a secret prefix to compare values; a prefix is still secret material.
  Print a non-reversible fingerprint instead: `sha256sum | cut -c1-16`.
- ⛔ Do not rely on redaction regexes; a pattern that fails to match prints everything.
  Do not print lines that may contain secrets at all.
  - Test for presence only: `grep -q PATTERN file && echo present`.
  - Need the value? Capture it in a variable and use it; check `${#VAR}` for length, never echo it.
  - Showing context is the last resort: if it is unavoidable, redact the whole stream with a greedy catch-all, assume it may still miss, and show the minimum.
- Pipe, do not print: move secrets machine to machine (`<secrets-cli> get ... | ssh host 'sudo tee /path >/dev/null'`, `-e VAR` passthrough, and for HTTP, a header fed to curl on stdin so the token never reaches argv: `printf 'header = "Authorization: Bearer %s"\n' "$TOK" | curl --config - https://api.example.com/`).
- Shell default expansions such as `${VAR:-x}` can print a secret.
  Assume `set -x`, error output, and provider debug output all leak; redirect and filter before showing anything.
- Terraform and OpenTofu state store sensitive attributes in plaintext; treat state files, and any credential that reads the state backend, as secrets.
- If a leak happens, say so immediately, name exactly which credentials leaked and their blast radius, and drive the rotation.
  A leaked secret is rotated, never left.

## Where secrets live

- ⛔ Never write secrets to files or argv in your own shell or workspace, not even temporarily.
  Keep them in environment variables or pipe them straight into the consumer.
  The sanctioned exception is delivery to the final consuming location (a remote host file via `ssh ... 'sudo tee /path'`, a CI environment file, a secrets-manager action), and even then pipe it there directly.
- When you brief a subagent, tell it never to write secrets to files or argv.
- ⛔ Never embed secrets in cloud-init user data, Butane, or Ignition templates; they land in the cloud provider API, in IaC state, and on disk in plaintext.
  Deliver secrets after the machine is reachable, or fetch them at runtime from a secrets manager.
  The only exception is the one bootstrap credential the machine needs to join its private network.
- Mark provider credential variables `sensitive = true` and, on OpenTofu 1.11 or later, `ephemeral = true`, so they stay out of state and plan files.
- ⛔ Never manage scoped API tokens as IaC resources when their values land in state; mint them outside state and seed them to the secrets manager at deploy time.
- Secrets reach deployed services through the deploy pipeline, not by hand.
  Hand-seeding is reserved for keys that can move money, and long-lived signing keys are generated once and kept out of CI.

## Input validation and security fixes

- ⛔ Never validate a whole untrusted string with `grep`; it is line-oriented, so `^` and `$` anchor to lines and `-q` succeeds when any line matches.
  A multiline payload passes `grep -Eq '^...$'` and breaks out downstream.
  Anchor to the whole string in bash: `[[ "$v" =~ ^...$ ]]`.
- Validate `workflow_dispatch` inputs that reach a remote or root command, or `$GITHUB_OUTPUT`, strictly at the boundary.
  GitHub does not validate `type: string` inputs and the REST API accepts newlines; `$GITHUB_OUTPUT` is line-based, so a newline forges step outputs.
- Check that a guard can ever fire.
  A check that cannot fail (a length check on already well-formed output, an emptiness check on a set that is never empty) is worse than none, because it reads as coverage.
- A security check that was wrong once moves into its own script with its own tests, including multiline payloads, leading and trailing newlines, and metacharacters; confirm the tests fail against the broken version.
- Bash edge cases: `git ls-files -- <missing-path>` exits 0 with empty output, so validate each declared path; `if cmd=$(...)` is exempt from `set -e`, so assign on its own line, then test.
- Verify a security fix closes the threat before committing.
  Check whether the replacement exposes the secret through the same channel (argv, environment, `docker inspect`, `/proc`); swapping `--password=` for `-e MYSQL_PWD` fixes nothing, since both reach the process list.
