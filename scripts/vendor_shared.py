#!/usr/bin/env python3
"""Copy shared capability files into each skill's references/ directory.

The Agent Skills spec wants every file a skill references to live inside the
skill directory, so installers that copy one skill at a time keep working.
shared/ is the single source; skills.json says which skill gets which file, and
any shared file those mention as references/<name>.md comes along with it.

  scripts/vendor_shared.py          write the copies
  scripts/vendor_shared.py --check  exit 1 if any copy is missing or stale
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
SKILLS = ROOT / "skills"
MANIFEST = ROOT / "skills.json"
ALWAYS = ["profile", "runtimes"]
REF_RE = re.compile(r"references/([a-z0-9-]+)\.md")


def closure(caps: list[str]) -> list[str]:
    """The listed capabilities plus every shared file they mention, transitively."""
    out: list[str] = []
    todo = list(caps)
    while todo:
        cap = todo.pop(0)
        if cap in out:
            continue
        src = SHARED / f"{cap}.md"
        if not src.is_file():
            sys.exit(f"unknown capability {cap}")
        out.append(cap)
        todo += [c for c in REF_RE.findall(src.read_text()) if (SHARED / f"{c}.md").is_file()]
    return out


def header(name: str) -> str:
    return (
        f"<!-- GENERATED from shared/{name}.md by scripts/vendor_shared.py. "
        "Edit the source, then rerun the script. -->\n\n"
    )


def expected() -> dict[Path, str]:
    manifest = json.loads(MANIFEST.read_text())
    out: dict[Path, str] = {}
    for skill, caps in manifest["skills"].items():
        if not (SKILLS / skill / "SKILL.md").is_file():
            sys.exit(f"skills.json names {skill}, which has no SKILL.md")
        for cap in closure(ALWAYS + caps):
            src = SHARED / f"{cap}.md"
            out[SKILLS / skill / "references" / f"{cap}.md"] = header(cap) + src.read_text()
    unlisted = sorted(
        p.parent.name for p in SKILLS.glob("*/SKILL.md") if p.parent.name not in manifest["skills"]
    )
    if unlisted:
        sys.exit(f"skills missing from skills.json: {', '.join(unlisted)}")
    return out


def generated_files() -> set[Path]:
    return {
        p
        for p in SKILLS.glob("*/references/*.md")
        if p.read_text().startswith("<!-- GENERATED from shared/")
    }


def main() -> int:
    check = "--check" in sys.argv[1:]
    want = expected()
    stale = [p for p, body in want.items() if not p.is_file() or p.read_text() != body]
    orphans = sorted(generated_files() - set(want))
    if check:
        for p in stale:
            print(f"stale or missing: {p.relative_to(ROOT)}")
        for p in orphans:
            print(f"orphaned generated file: {p.relative_to(ROOT)}")
        return 1 if stale or orphans else 0
    for p in stale:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(want[p])
    for p in orphans:
        p.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
