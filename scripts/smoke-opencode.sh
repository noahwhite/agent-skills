#!/usr/bin/env bash
# Install the skills into a throwaway project the way a consumer would
# (.agents/skills/<name>), then check opencode lists every one of them.
# Needs no model credentials: `opencode debug skill` only runs discovery.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
version="${OPENCODE_VERSION:-1.18.32}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

if ! command -v opencode >/dev/null || [ -n "${OPENCODE_FORCE_INSTALL:-}" ]; then
  npm install --prefix "$work/npm" --no-audit --no-fund "opencode-ai@$version" >/dev/null
  PATH="$work/npm/node_modules/.bin:$PATH"
fi

project="$work/project"
mkdir -p "$project/.agents/skills"
git -C "$project" init -q
for d in "$root"/skills/*/; do
  cp -R "$d" "$project/.agents/skills/"
done

# Isolate from any skills installed for the current user.
export HOME="$work/home" XDG_CONFIG_HOME="$work/home/.config"
mkdir -p "$HOME"

(cd "$project" && opencode debug skill > "$work/skills.json")

missing=0
for d in "$root"/skills/*/; do
  name="$(basename "$d")"
  want="$project/.agents/skills/$name/SKILL.md"
  if ! jq -e --arg n "$name" --arg p "$want" 'any(.[]; .name == $n and .location == $p)' "$work/skills.json" >/dev/null; then
    echo "opencode did not discover $name"
    missing=1
  fi
done
[ "$missing" -eq 0 ] && echo "opencode discovered all $(find "$root/skills" -mindepth 1 -maxdepth 1 -type d | wc -l) skills"
exit "$missing"
