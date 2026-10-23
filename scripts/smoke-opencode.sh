#!/usr/bin/env bash
# Credential-free V2 discovery across the documented project and global layouts.
# Extra arguments are forwarded to smoke_opencode.py (see its --root and --timeout).
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
version="${OPENCODE_VERSION:-2.1.2}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

installed=""
if command -v opencode >/dev/null; then
  installed="$(opencode --version)"
fi
if [ "$installed" != "opencode v$version" ] || [ -n "${OPENCODE_FORCE_INSTALL:-}" ]; then
  mkdir -p "$work/npm"
  # npm requires project-scoped install-script policy in package.json, not a CLI flag.
  printf '%s\n' '{"private":true,"allowScripts":{"@opencode/cli":true}}' > "$work/npm/package.json"
  npm install --prefix "$work/npm" --no-audit --no-fund \
    --ignore-scripts=false "@opencode/cli@$version"
  PATH="$work/npm/node_modules/.bin:$PATH"
fi
if [ "$(opencode --version)" != "opencode v$version" ]; then
  echo "Expected OpenCode $version" >&2
  exit 1
fi

python3 "$root/scripts/smoke_opencode.py" --root "$root" "$@"
