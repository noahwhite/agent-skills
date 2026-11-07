#!/usr/bin/env bash
# Refuse to continue when git would sign commits with a key other than the registered one.
#
#   bash check-signing-key.sh <SHA256:fingerprint>     (run from inside the target repository)
#
# The fingerprint is profile.git.signing_key. Git resolves the key itself: the script asks git
# to sign a throwaway commit under the effective git config of the repository it runs in, reads
# the signer's fingerprint back from that signature, and compares it with the argument. So
# user.signingkey (a key:: or bare ssh- literal, a public-key file or a private-key file,
# including ~ and relative paths), gpg.ssh.defaultKeyCommand and the agent are resolved exactly
# as for git commit; the script parses no key file and no command output.
#   - gpg.format must be ssh.
#   - A key git can only sign with through the agent (a literal, command output, or a public-key
#     file with no private key beside it) fails when it is not loaded in the agent.
#   - A public-key file with its private key beside it, and a private-key file without a
#     passphrase, sign without the agent.
#   - A .pub beside a private-key file that holds another key is followed by git when the agent
#     holds that key, so the signer reported is that key.
# The throwaway commit is made with git commit-tree into a temporary object directory, so the
# repository gains no commit, ref, object or config change; git may create and remove a
# temporary signing buffer file in the work tree while it signs. The temporary directory is
# removed on exit and on interrupt.
# gpg.ssh.program is honoured by git, so a wrapper that signs with another key is seen too.
# Exit 0 and no output on a match. Any other outcome exits 1 with exactly one line on stderr
# naming the expected fingerprint, the resolved fingerprint or "unresolved", and a reason;
# nothing goes to stdout. The line carries public fingerprints only: no key material, no command
# output and no path.

set -u
export LC_ALL=C

pattern='^SHA256:[A-Za-z0-9+/]{43}$'
expected="${1-}"
resolved=unresolved
work=

cleanup() {
  [ -n "$work" ] && rm -rf "$work"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

fail() {
  printf 'check-signing-key: expected %s, resolved %s: %s\n' "$expected" "$resolved" "$1" >&2
  exit 1
}

if [ "$#" -ne 1 ] || ! [[ $expected =~ $pattern ]]; then
  expected=invalid
  fail "argument must be one SHA256 fingerprint"
fi

git rev-parse --git-dir >/dev/null 2>&1 || fail "not inside a git repository"

format=$(git config --get gpg.format 2>/dev/null) || format=
[ "$format" = ssh ] || fail "gpg.format is not ssh"

work=$(mktemp -d "${TMPDIR:-/tmp}/check-signing-key.XXXXXX") || fail "no temporary directory"

# A private key whose passphrase git would ask for must not prompt here: no tty, askpass fails.
export SSH_ASKPASS=/bin/false SSH_ASKPASS_REQUIRE=force
# git leaves temporary key files in TMPDIR when it signs with a key:: literal; keep them inside $work.
export TMPDIR="$work"
export GIT_OBJECT_DIRECTORY="$work/objects"
export GIT_AUTHOR_NAME=preflight GIT_AUTHOR_EMAIL=preflight@invalid
export GIT_COMMITTER_NAME=preflight GIT_COMMITTER_EMAIL=preflight@invalid
export GIT_AUTHOR_DATE="1000000000 +0000" GIT_COMMITTER_DATE="1000000000 +0000"
unset GIT_ALTERNATE_OBJECT_DIRECTORIES

mkdir "$GIT_OBJECT_DIRECTORY" || fail "no temporary directory"
tree=$(git hash-object -t tree -w --stdin </dev/null 2>/dev/null) || fail "cannot create the throwaway commit"
commit=$(git commit-tree -S -m preflight "$tree" 2>/dev/null </dev/null) \
  || fail "git cannot sign with the configured key (unresolvable, or not loaded in the ssh agent)"
git cat-file commit "$commit" >"$work/commit" 2>/dev/null || fail "cannot read the throwaway commit"

# Split the commit into its signed payload and the armoured signature (the gpgsig header).
awk -v sig="$work/sig" -v payload="$work/payload" '
  /^gpgsig /      { sub(/^gpgsig /, ""); print > sig; insig = 1; next }
  insig && /^ /   { sub(/^ /, ""); print > sig; next }
                  { insig = 0; print > payload }
' "$work/commit"
[ -s "$work/sig" ] || fail "git did not sign the throwaway commit"

verdict=$(ssh-keygen -Y check-novalidate -n git -s "$work/sig" <"$work/payload" 2>/dev/null) \
  || fail "the signature cannot be read"
signer_pattern='key (SHA256:[A-Za-z0-9+/]{43})$'
[[ $verdict =~ $signer_pattern ]] || fail "the signer of the signature cannot be identified"
resolved="${BASH_REMATCH[1]}"

[ "$resolved" = "$expected" ] || fail "mismatch: the resolved key is not the registered key"
exit 0
