#!/usr/bin/env python3
"""Copy shared capability files into each skill's references/ directory.

The Agent Skills spec wants every file a skill references to live inside the
skill directory, so installers that copy one skill at a time keep working.
shared/ is the single source; skills.json says which skill gets which file, and
any shared file those mention as references/<name>.md comes along with it.

Executable mode: skills.json may also map a skill to shared executables under
"executables", for example {"executables": {"<skill>": ["resolve-model-role.py"]}}.
Each lands in skills/<skill>/scripts/<file> as a byte-for-byte copy of the source with
one generated first-line header comment in the file's own language (# for .py and .sh,
// for .js). --check compares the copy with that header plus the source, so a copy whose
content after its first line differs from the source, or whose first line is not the
header, is stale. The header sits above any shebang, so a copy is never executable: callers
run it through its interpreter (python3 <copy>), and a copy with an executable bit is stale.
Only a file whose first line is exactly the header for its own name counts as generated, and
a write run deletes an orphaned one only when the rest of it is still that shared source;
otherwise it names the file and exits 1. A copy that is a symlink is stale, and a write run
replaces the link, never its target.

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
COMMENT = {".py": "#", ".sh": "#", ".js": "//"}
SKILL_NAME = re.compile(r"[a-z0-9][a-z0-9-]*")


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


def exec_header(name: str) -> bytes:
    """The first line of a vendored executable: a comment in the copy's own language."""
    comment = COMMENT.get(Path(name).suffix)
    if comment is None:
        sys.exit(f"no comment syntax for shared executable {name}")
    return (
        f"{comment} GENERATED from shared/{name} by scripts/vendor_shared.py. "
        "Edit the source, then rerun the script.\n"
    ).encode()


def expected_executables(manifest: dict) -> dict[Path, bytes]:
    out: dict[Path, bytes] = {}
    for skill, names in manifest.get("executables", {}).items():
        if not SKILL_NAME.fullmatch(skill):
            sys.exit(f"skills.json executables: {skill!r} is not a skill name")
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            sys.exit(f"skills.json executables: {skill} must map to a list of file names")
        if not (SKILLS / skill / "SKILL.md").is_file():
            sys.exit(f"skills.json names {skill}, which has no SKILL.md")
        for name in names:
            src = SHARED / name
            if "/" in name or name.endswith(".md") or not src.is_file():
                sys.exit(f"unknown shared executable {name}")
            out[SKILLS / skill / "scripts" / name] = exec_header(name) + src.read_bytes()
    return out


def expected() -> dict[Path, str | bytes]:
    """Every vendored file and its content: Markdown copies as text, executables as bytes."""
    manifest = json.loads(MANIFEST.read_text())
    out: dict[Path, str | bytes] = {}
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
    out.update(expected_executables(manifest))
    return out


def generated_files() -> set[Path]:
    return {
        p
        for p in SKILLS.glob("*/references/*.md")
        if p.read_text().startswith("<!-- GENERATED from shared/")
    }


def generated_executables() -> set[Path]:
    return {
        p
        for p in SKILLS.glob("*/scripts/*")
        if p.is_file() and p.suffix in COMMENT and p.read_bytes().startswith(exec_header(p.name))
    }


def is_stale(p: Path, body: str | bytes) -> bool:
    if not p.is_file():
        return True
    if isinstance(body, str):
        return p.read_text() != body
    return p.is_symlink() or p.read_bytes() != body or p.stat().st_mode & 0o111 != 0


def still_a_copy(p: Path) -> bool:
    """An orphaned executable is deleted only while it is the header plus its shared source."""
    src = SHARED / p.name
    return not p.is_symlink() and src.is_file() and p.read_bytes() == exec_header(p.name) + src.read_bytes()


def main() -> int:
    check = "--check" in sys.argv[1:]
    want = expected()
    stale = [p for p, body in want.items() if is_stale(p, body)]
    orphans = sorted((generated_files() | generated_executables()) - set(want))
    if check:
        for p in stale:
            print(f"stale or missing: {p.relative_to(ROOT)}")
        for p in orphans:
            print(f"orphaned generated file: {p.relative_to(ROOT)}")
        return 1 if stale or orphans else 0
    for p in stale:
        p.parent.mkdir(parents=True, exist_ok=True)
        body = want[p]
        if isinstance(body, bytes):
            if p.is_symlink():
                p.unlink()
            p.write_bytes(body)
            p.chmod(p.stat().st_mode & 0o666)
        else:
            p.write_text(body)
    kept = [p for p in orphans if p.suffix != ".md" and not still_a_copy(p)]
    for p in orphans:
        if p not in kept:
            p.unlink()
    for p in kept:
        print(
            f"not deleting {p.relative_to(ROOT)}: it carries the generated header but is not a copy of "
            f"shared/{p.name}; delete it or drop the header by hand",
            file=sys.stderr,
        )
    return 1 if kept else 0


if __name__ == "__main__":
    sys.exit(main())
