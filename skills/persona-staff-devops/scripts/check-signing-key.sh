# GENERATED from shared/check-signing-key.sh by scripts/vendor_shared.py. Edit the source, then rerun the script.
#!/usr/bin/env bash
# Refuse to continue when git would sign commits with a key other than the registered one.
#
#   bash check-signing-key.sh <SHA256:fingerprint>     (run from inside the target repository)
#
# The fingerprint is profile.git.signing_key. The script resolves the key git would sign with,
# in git's order, and compares its SHA256 fingerprint with the argument:
#   1. gpg.format must be ssh.
#   2. When user.signingkey is set it is a key:: or ssh- literal, a public-key file or a
#      private-key file; a value that cannot be resolved fails, with no fallback to another source.
#   3. When user.signingkey is unset, the first output line of gpg.ssh.defaultKeyCommand must
#      begin with key:: (or ssh-, the other form git accepts, as `ssh-add -L` prints). The command
#      is split into arguments and run without a shell, as git runs it.
# gpg.ssh.program is not inspected: a wrapper that signs with another key than git selected is
# outside what this check can see.
# A public-key resolution (literal, public-key file, command output) must also be loaded in the
# agent (ssh-add -l). Exit 0 and no output on a match. Any other outcome exits 1 with exactly one
# line on stderr naming the expected fingerprint, the resolved fingerprint or "unresolved", and a
# reason; nothing goes to stdout. The line carries public fingerprints only: no key material, no
# command output and no path.

set -u
export LC_ALL=C

pattern='^SHA256:[A-Za-z0-9+/]{43}$'
expected="${1-}"
resolved=unresolved

fail() {
  printf 'check-signing-key: expected %s, resolved %s: %s\n' "$expected" "$resolved" "$1" >&2
  exit 1
}

if [ "$#" -ne 1 ] || ! [[ $expected =~ $pattern ]]; then
  expected=invalid
  fail "argument must be one SHA256 fingerprint"
fi

# Print the SHA256 fingerprint of the public key on stdin; fail when it is not one.
fingerprint() {
  local out
  out=$(ssh-keygen -E sha256 -lf /dev/stdin 2>/dev/null) || return 1
  out=${out#* }
  out=${out%% *}
  [[ $out =~ $pattern ]] || return 1
  printf '%s\n' "$out"
}

format=$(git config --get gpg.format 2>/dev/null) || format=
[ "$format" = ssh ] || fail "gpg.format is not ssh"

public=1
if signing_key=$(git config --get user.signingkey 2>/dev/null); then
  case $signing_key in
    key::*) resolved=$(printf '%s\n' "${signing_key#key::}" | fingerprint) ;;
    ssh-*) resolved=$(printf '%s\n' "$signing_key" | fingerprint) ;;
    *)
      path=$signing_key
      case $path in "~/"*) path=${HOME:+$HOME/${path#"~/"}} ;; esac
      if [ -z "$path" ] || [ ! -f "$path" ] || [ ! -r "$path" ]; then
        resolved=
      elif IFS= read -r first <"$path" && [[ $first == *"PRIVATE KEY"* ]]; then
        public=0
        derived=$(ssh-keygen -y -P '' -f "$path" 2>/dev/null </dev/null) || derived=
        resolved=$(printf '%s\n' "$derived" | fingerprint)
      else
        resolved=$(head -n 1 "$path" | fingerprint)
      fi
      ;;
  esac
  [ -n "$resolved" ] || { resolved=unresolved; fail "user.signingkey cannot be resolved"; }
else
  command=$(git config --get gpg.ssh.defaultKeyCommand 2>/dev/null) || command=
  [ -n "$command" ] || fail "no signing key is configured"
  # Git splits the command into arguments (quotes group, no expansion) and runs it without a shell.
  output=$(printf '%s\n' "$command" | xargs -r sh -c 'exec "$@"' _ 2>/dev/null) ||
    fail "gpg.ssh.defaultKeyCommand failed"
  first=${output%%$'\n'*}
  case $first in
    key::*) first=${first#key::} ;;
    ssh-*) ;;
    *) fail "gpg.ssh.defaultKeyCommand output is malformed" ;;
  esac
  resolved=$(printf '%s\n' "$first" | fingerprint) || resolved=
  [ -n "$resolved" ] || { resolved=unresolved; fail "gpg.ssh.defaultKeyCommand output is malformed"; }
fi

[ "$resolved" = "$expected" ] || fail "mismatch: the resolved key is not the registered key"

if [ "$public" = 1 ]; then
  loaded=$(ssh-add -l 2>/dev/null </dev/null) || fail "the key is not loaded in the ssh agent (agent unavailable or empty)"
  found=0
  while read -r _ agent_fingerprint _; do
    [ "$agent_fingerprint" = "$expected" ] && found=1
  done <<<"$loaded"
  [ "$found" = 1 ] || fail "the key is not loaded in the ssh agent"
fi
