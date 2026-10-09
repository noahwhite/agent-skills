#!/usr/bin/env python3
"""Fail if any tracked file contains a consumer identifier or credential shape.

Public patterns live in scripts/leak-patterns.txt and cover generic shapes only.
Private patterns (consumer names, estates, vendors, issue keys) come from the
LEAK_DENYLIST environment variable or the file named by LEAK_DENYLIST_FILE, one
regex per line; matches against those are reported by pattern number only, so a
private pattern never reaches a log.

  scripts/leak_scan.py                       scan every tracked and untracked-unignored file
  scripts/leak_scan.py FILE...               scan only these files
  scripts/leak_scan.py --require-private ... fail when no private pattern is loaded
"""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERNS = ROOT / "scripts" / "leak-patterns.txt"
# The patterns file holds the identifiers it bans; LICENSE is third-party text.
EXEMPT = {"scripts/leak-patterns.txt", "LICENSE", "uv.lock"}


def load_public() -> list[tuple[re.Pattern, str]]:
    out = []
    for line in PATTERNS.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        regex, sample = line.split("\t", 1)
        out.append((re.compile(regex), sample))
    return out


def load_private() -> list[re.Pattern]:
    raw = os.environ.get("LEAK_DENYLIST", "")
    path = os.environ.get("LEAK_DENYLIST_FILE")
    if path:
        raw += "\n" + Path(path).read_text()
    lines = [l.strip() for l in raw.splitlines()]
    return [re.compile(l) for l in lines if l and not l.startswith("#")]


def files() -> list[str]:
    res = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    return [f for f in res.stdout.splitlines() if f not in EXEMPT and (ROOT / f).is_file()]


def decodings(data: bytes) -> list[str]:
    """Every plausible text reading of a file, so no encoding hides a match."""
    # UTF-32 marks first: the UTF-32LE mark starts with the UTF-16LE one.
    for bom, enc in ((b"\xff\xfe\0\0", "utf-32"), (b"\0\0\xfe\xff", "utf-32"),
                     (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16")):
        if data.startswith(bom):
            return [data.decode(enc, errors="replace")]  # PowerShell's `>` writes UTF-16
    # Decode leniently: a file in another encoding is still scanned, not skipped.
    texts = [data.decode("utf-8", errors="replace")]
    if b"\0" in data:
        # NULs without a mark: UTF-16 of either byte order, or binary. Scan both readings;
        # the patterns are specific shapes, so binary noise does not produce false hits.
        texts += [data.decode("utf-16-le", errors="replace"), data.decode("utf-16-be", errors="replace")]
    return texts


def scan(paths: list[str], public, private) -> list[str]:
    hits = []
    for rel in paths:
        found: list[str] = []
        for text in decodings((ROOT / rel).read_bytes()):
            for n, line in enumerate(text.splitlines(), 1):
                for rx, _ in public:
                    # Report the pattern, never the matched text: it may be a live credential.
                    if rx.search(line):
                        found.append(f"{rel}:{n}: matches {rx.pattern!r}")
                for i, rx in enumerate(private, 1):
                    if rx.search(line):
                        found.append(f"{rel}:{n}: matches private pattern #{i}")
        hits += dict.fromkeys(found)  # one report per hit, however many readings found it
    return hits


def main() -> int:
    args = sys.argv[1:]
    require_private = "--require-private" in args
    paths = [a for a in args if a != "--require-private"] or files()
    private = load_private()
    hits = scan(paths, load_public(), private)
    for h in hits:
        print(h)
    if not private:
        print("leak scan INCOMPLETE: no private patterns loaded (LEAK_DENYLIST / LEAK_DENYLIST_FILE)")
        if require_private:
            return 2
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
