"""The sweep and hunt dossiers embed a per-file capped `--unified=1` diff with an exact marker.

SKL-87. Each file's diff section (the `diff --git` header, the hunk headers and every hunk) is
capped at 4096 bytes. A section over the cap loses whole hunks from the end, and its remainder is
replaced by exactly one marker line naming the file and its byte counts and the phase checkout
the dossier names on its own `CHECKOUT: ` line. A section at or below the cap is the byte-identical
`git diff --no-ext-diff --unified=1` output. The tests exercise sweep and hunt on the `run` and the
`dossier` flows over a real two-commit repository (never `--base HEAD`, whose empty diff would pass
vacuously), and compare every dossier section with the sections git itself produced.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "adversarial-review-pipeline" / "scripts" / "run-adversarial-pipeline.sh"
BASE_REF = "base"
CAP = 4096
FLOWS = ("run", "dossier")
PHASES = ("sweep", "hunt")

MARKER_RE = re.compile(
    rb"<!-- TRUNCATED: (?P<path>.*) \((?P<shown>\d+)/(?P<total>\d+) bytes\)"
    rb" - the full diff of this file is in your checkout at (?P<checkout>.*) -->\n"
)


def neutral_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """The host environment without ADVERSARIAL_* and GIT_* variables and without global or system
    git config, so a host's diff settings (renames, color, prefixes, submodule format) shape neither
    the fixtures, the oracle nor the script under test."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ADVERSARIAL_", "GIT_"))}
    return {**env, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", **(extra or {})}


NEUTRAL_GIT = neutral_env()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, env=NEUTRAL_GIT,
    ).stdout.strip()


def git_bytes(repo: Path, *args: str, env: dict[str, str] | None = None) -> bytes:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                          env=env or NEUTRAL_GIT).stdout


def run_script(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=120,
    )


def lines_of(data: bytes) -> list[bytes]:
    """Lines split on b"\\n" only; bytes.splitlines would also split on a bare CR."""
    return re.findall(rb"[^\n]*\n|[^\n]+", data)


# --- repositories ---------------------------------------------------------------------------------

def seed(tmp_path: Path, base: dict[str, bytes], head: dict[str, bytes | None],
         head_ops=None) -> Path:
    """A base commit tagged `base` holding `base`, then a head commit applying `head` (None
    deletes) and `head_ops(repo)` (renames, mode changes)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "agent-skills@example.com")
    git(repo, "config", "user.name", "agent-skills")
    git(repo, "config", "commit.gpgsign", "false")  # an inherited signing config must not break the fixture
    git(repo, "config", "tag.gpgsign", "false")
    git(repo, "config", "core.quotepath", "true")
    (repo / "README.md").write_bytes(b"seed\n")
    for name, data in base.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "base")
    git(repo, "tag", BASE_REF)
    if head_ops is not None:
        head_ops(repo)
    for name, data in head.items():
        path = repo / name
        if data is None:
            path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "head")
    return repo


def make_gate(tmp_path: Path, base: dict[str, bytes], head: dict[str, bytes | None],
              head_ops=None, env_extra: dict[str, str] | None = None) -> dict:
    repo = seed(tmp_path, base, head, head_ops)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    (tmp_path / "runtime-tmp").mkdir()
    env = neutral_env({"TMPDIR": str(tmp_path / "runtime-tmp"), **(env_extra or {})})
    spec = tmp_path / "spec.md"
    spec.write_text("Story SKL-87: cap the embedded diff.\n")
    g = {"repo": repo, "scratch": scratch, "env": env, "spec": spec, "tmp": tmp_path}
    preflight = run_script("preflight", "--repo", str(repo), "--base", BASE_REF,
                           "--test-cmd", "true", "--scratch", str(scratch), env=env)
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    return g


def common(g: dict, phase: str) -> list[str]:
    args = ["--repo", str(g["repo"]), "--base", BASE_REF, "--spec", str(g["spec"]),
            "--scratch", str(g["scratch"])]
    return args + (["--no-sweep"] if phase == "hunt" else [])


COPY_AGENT = (
    'cp {prompt_file} "$ADVERSARIAL_SESSION_SCRATCH/seen-dossier.md"; '
    'printf "REVIEW-RAN: yes\\n" > {output_file}'
)


def dossier_bytes(g: dict, phase: str, flow: str) -> bytes:
    """The phase's dossier as the `run` agent receives it, or as the `dossier` command writes it."""
    if flow == "run":
        result = run_script("run", phase, *common(g, phase), "--agent-cmd", COPY_AGENT, env=g["env"])
        assert result.returncode == 0, result.stdout + result.stderr
        return (g["scratch"] / "seen-dossier.md").read_bytes()
    result = run_script("dossier", phase, *common(g, phase), env=g["env"])
    assert result.returncode == 0, result.stdout + result.stderr
    return Path(result.stdout.strip().splitlines()[-1]).read_bytes()


# --- the oracle: git's own sections and the cap rules of the story ---------------------------------

def git_sections(g: dict) -> list[bytes]:
    full = git_bytes(g["repo"], "diff", "--no-ext-diff", "--unified=1", f"{BASE_REF}...HEAD")
    sections: list[bytes] = []
    for line in lines_of(full):
        if line.startswith(b"diff --git "):
            sections.append(b"")
        sections[-1] += line
    return sections


def header_and_hunks(section: bytes) -> tuple[bytes, list[bytes]]:
    header, hunks = b"", []
    for line in lines_of(section):
        if line.startswith(b"@@"):
            hunks.append(b"")
        if hunks:
            hunks[-1] += line
        else:
            header += line
    return header, hunks


def longest_line_prefix(data: bytes, room: int) -> bytes:
    kept = b""
    for line in lines_of(data):
        if len(kept) + len(line) > room:
            break
        kept += line
    return kept


def expected_emission(section: bytes) -> bytes:
    """What the story says a section emits: itself at or below the cap, else whole hunks from the
    start, else the first hunk clipped at a line boundary, else a line-boundary prefix of the header."""
    if len(section) <= CAP:
        return section
    header, hunks = header_and_hunks(section)
    if len(header) > CAP:
        return longest_line_prefix(header, CAP)
    kept = header
    for i, hunk in enumerate(hunks):
        if len(kept) + len(hunk) <= CAP:
            kept += hunk
        elif i == 0:
            return kept + longest_line_prefix(hunk, CAP - len(kept))
        else:
            break
    return kept


def parse_diff_region(dossier: bytes) -> list[tuple[bytes, re.Match | None]]:
    """The dossier's DIFF section as (emitted section text, its marker match or None) in order."""
    header = re.search(rb"===== DIFF \([^\n]*\) =====\n", dossier)
    assert header, "the dossier carries no DIFF section"
    parsed: list[tuple[bytes, re.Match | None]] = []
    current = b""
    for line in lines_of(dossier[header.end():]):
        marker = MARKER_RE.fullmatch(line)
        if marker:
            if len(current) == int(marker["shown"]):
                parsed.append((current, marker))
            else:  # the marker belongs to a section of which zero bytes were emitted
                if current:
                    parsed.append((current, None))
                parsed.append((b"", marker))
            current = b""
        elif line.startswith(b"diff --git "):
            if current:
                parsed.append((current, None))
            current = line
        else:
            current += line
    if current:
        parsed.append((current, None))
    return parsed


def checkout_of(dossier: bytes) -> str:
    found = [line for line in dossier.decode().splitlines() if line.startswith("CHECKOUT: ")]
    assert len(found) == 1, found
    return found[0].removeprefix("CHECKOUT: ")


def blueprint_of(dossier: bytes) -> bytes:
    start = dossier.index(b"===== BLUEPRINT")
    start = dossier.index(b"\n", start) + 1
    return dossier[start:dossier.index(b"\n===== DIFF (")]  # the blank line before it is not diffstat


def assert_capped(g: dict, phase: str, flow: str, truncated_paths: list[str]) -> bytes:
    """Every dossier section is what the story prescribes for git's section; `truncated_paths` are
    the destination paths, in order, of the sections over the cap. Returns the dossier."""
    dossier = dossier_bytes(g, phase, flow)
    sections = git_sections(g)
    parsed = parse_diff_region(dossier)
    assert len(parsed) == len(sections), (len(parsed), len(sections))
    checkout = checkout_of(dossier)
    paths = iter(truncated_paths)
    for full, (text, marker) in zip(sections, parsed):
        emitted = expected_emission(full)
        if len(full) <= CAP:
            assert marker is None, f"an untruncated section carries a marker: {marker}"
            assert text == full, "a section at or below the cap is not byte-identical to git's output"
            continue
        assert marker is not None, "an over-cap section carries no marker"
        assert text == emitted, "the truncated section is not what the story prescribes"
        assert len(text) <= CAP and (text == b"" or text.endswith(b"\n"))
        assert full.startswith(text)
        assert marker["path"].decode() == next(paths)
        assert int(marker["shown"]) == len(text) and int(marker["total"]) == len(full)
        assert marker["checkout"].decode() == checkout
    assert next(paths, None) is None, "fewer truncated sections than expected"
    marker_lines = [line for line in lines_of(dossier) if line.startswith(b"<!-- TRUNCATED:")]
    assert len(marker_lines) == len(truncated_paths), "not exactly one marker per section"
    # the diffstat is git's own `git diff --stat` under the same config the script ran with
    assert blueprint_of(dossier) == git_bytes(g["repo"], "diff", "--stat", f"{BASE_REF}...HEAD",
                                              env=g["env"]), "the diffstat changed"
    return dossier


def numbered(prefix: str, count: int, changed=None) -> bytes:
    return b"".join(
        f"{prefix} {i:04d}{' CHANGED' if changed and changed(i) else ''}\n".encode()
        for i in range(1, count + 1)
    )


def deep_path(depth: int, leaf: str) -> str:
    return "/".join(["d" * 124] * depth + [leaf])


# --- unchanged emission at or below the cap --------------------------------------------------------

@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("phase", PHASES)
def test_sections_at_or_below_the_cap_are_git_s_unified_1_output_byte_for_byte(tmp_path, phase, flow):
    g = make_gate(tmp_path, {
        "app.py": b"def total(items):\n    return sum(items)\n",
        "crlf.txt": b"one\r\ntwo\r\nthree",
        "plain.txt": numbered("row", 40),
    }, {
        "app.py": b"def total(items):\n    return sum(i for i in items if i > 0)\n",
        "crlf.txt": b"one\r\nTWO\r\nthree",  # CRLF endings and no newline at the end of the file
        "plain.txt": numbered("row", 40, lambda i: i in (5, 30)),
    })
    dossier = assert_capped(g, phase, flow, [])
    full = git_bytes(g["repo"], "diff", "--no-ext-diff", "--unified=1", f"{BASE_REF}...HEAD")
    assert dossier.endswith(full), "the embedded diff is not git's --unified=1 output"
    assert b"\\ No newline at end of file\n" in full and b"\r\n" in full
    assert b"@@ -4,3 +4,3 @@" in full  # one line of context each side, not three


# --- truncation drops whole hunks from the end -----------------------------------------------------

@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("phase", PHASES)
def test_an_over_cap_section_loses_whole_hunks_from_the_end_and_gets_one_exact_marker(tmp_path, phase, flow):
    g = make_gate(tmp_path, {
        "big.txt": numbered("line", 800),
        "small.txt": numbered("tiny", 6),
    }, {
        "big.txt": numbered("line", 800, lambda i: i % 8 == 0),
        "small.txt": numbered("tiny", 6, lambda i: i == 3),
    })
    dossier = assert_capped(g, phase, flow, ["big.txt"])
    sections = git_sections(g)
    header, hunks = header_and_hunks(sections[0])
    assert len(hunks) > 20 and len(sections[0]) > CAP
    (text, marker), = [p for p in parse_diff_region(dossier) if p[1]]
    kept = header_and_hunks(text)[1]
    assert 1 < len(kept) < len(hunks) and text == header + b"".join(hunks[:len(kept)])
    assert len(text) + len(hunks[len(kept)]) > CAP, "a further whole hunk would still have fit"
    assert marker[0] == (
        f"<!-- TRUNCATED: big.txt ({len(text)}/{len(sections[0])} bytes) - the full diff of this file "
        f"is in your checkout at {checkout_of(dossier)} -->\n"
    ).encode()
    assert f"{len(text)}/{len(sections[0])} bytes".encode() in marker[0]


@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("phase", PHASES)
def test_a_first_hunk_over_the_cap_is_clipped_at_a_line_boundary_keeping_the_header(tmp_path, phase, flow):
    g = make_gate(tmp_path, {"one-hunk.txt": numbered("old", 300)},
                  {"one-hunk.txt": numbered("new", 300)})
    dossier = assert_capped(g, phase, flow, ["one-hunk.txt"])
    full, = git_sections(g)
    header, hunks = header_and_hunks(full)
    (text, _), = [p for p in parse_diff_region(dossier) if p[1]]
    assert len(hunks) == 1 and len(header) + len(hunks[0]) > CAP
    assert text.startswith(header + hunks[0].split(b"\n", 1)[0] + b"\n"), "the header or hunk header was lost"
    clipped = text[len(header):]
    assert hunks[0].startswith(clipped) and 1 < len(lines_of(clipped)) < len(lines_of(hunks[0]))
    assert len(text) + len(lines_of(hunks[0])[len(lines_of(clipped))]) > CAP, "a further line would have fit"


@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("phase", PHASES)
def test_a_single_line_over_the_cap_is_never_cut_in_the_middle(tmp_path, phase, flow):
    g = make_gate(tmp_path, {"wide.txt": b"before\n" + b"z" * 10000 + b"\nafter\n"},
                  {"wide.txt": b"before\n" + b"y" * 10000 + b"\nafter\n"})
    dossier = assert_capped(g, phase, flow, ["wide.txt"])
    full, = git_sections(g)
    header, hunks = header_and_hunks(full)
    (text, marker), = [p for p in parse_diff_region(dossier) if p[1]]
    first_hunk_line = hunks[0].split(b"\n", 1)[0] + b"\n"
    assert text == header + first_hunk_line + b" before\n", "only the complete lines that fit are kept"
    assert b"z" not in text and b"y" not in text


@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("phase", PHASES)
def test_a_later_hunk_that_does_not_fit_is_dropped_whole_never_clipped(tmp_path, phase, flow):
    # a small first hunk leaves room for several lines of the large second one, which still goes
    g = make_gate(tmp_path, {"two.txt": numbered("row", 600)},
                  {"two.txt": numbered("row", 600, lambda i: i == 3 or 100 <= i <= 400)})
    dossier = assert_capped(g, phase, flow, ["two.txt"])
    full, = git_sections(g)
    header, hunks = header_and_hunks(full)
    (text, _), = [p for p in parse_diff_region(dossier) if p[1]]
    assert len(hunks) == 2 and CAP - len(header + hunks[0]) > 1000
    assert text == header + hunks[0], "the second hunk was clipped instead of dropped"


def padded(tmp_path: Path, make, measure) -> tuple[dict, dict]:
    """(base, head) from `make(pad)`, with the pad chosen so that `measure(section)` of the unpadded
    fixture's single section reaches exactly CAP bytes; the pad lands inside the measured span."""
    probe = tmp_path / "probe"
    probe.mkdir()
    base, head = make(0)
    full = git_bytes(seed(probe, base, head), "diff", "--no-ext-diff", "--unified=1", f"{BASE_REF}...HEAD")
    measured = measure(full)
    assert measured < CAP
    return make(CAP - measured)


def edge_file(pad: int, changed: dict[int, bytes]) -> tuple[dict, dict]:
    lines = numbered("row", 60).splitlines(keepends=True)
    for i, text in changed.items():
        lines[i] = text.replace(b"PAD", b"p" * pad)
    return {"edge.txt": numbered("row", 60)}, {"edge.txt": b"".join(lines)}


@pytest.mark.parametrize("flow", FLOWS)
def test_a_section_of_exactly_the_cap_is_untouched(tmp_path, flow):
    base, head = padded(tmp_path, lambda pad: edge_file(pad, {1: b"row 0002 PAD\n"}), len)
    g = make_gate(tmp_path, base, head)
    full, = git_sections(g)
    assert len(full) == CAP
    assert_capped(g, "sweep", flow, [])


@pytest.mark.parametrize("flow", FLOWS)
def test_whole_hunks_filling_exactly_the_cap_are_kept(tmp_path, flow):
    # three hunks: the pad sits in the second, so header + hunks 1-2 is exactly the cap
    changed = {1: b"row 0002 CHANGED\n", 20: b"row 0021 PAD\n", 49: b"row 0050 CHANGED\n"}

    def first_two(section: bytes) -> int:
        header, hunks = header_and_hunks(section)
        return len(header + hunks[0] + hunks[1])

    base, head = padded(tmp_path, lambda pad: edge_file(pad, changed), first_two)
    g = make_gate(tmp_path, base, head)
    dossier = assert_capped(g, "sweep", flow, ["edge.txt"])
    full, = git_sections(g)
    header, hunks = header_and_hunks(full)
    (text, marker), = [p for p in parse_diff_region(dossier) if p[1]]
    assert len(hunks) == 3 and text == header + hunks[0] + hunks[1] and int(marker["shown"]) == CAP


@pytest.mark.parametrize("flow", FLOWS)
def test_a_first_hunk_clip_keeps_a_line_ending_exactly_at_the_cap(tmp_path, flow):
    # one long hunk; the pad grows its second removed line so a line boundary falls exactly on the cap
    def make(pad: int) -> tuple[dict, dict]:
        old = numbered("old", 300).splitlines(keepends=True)
        old[1] = b"old 0002 " + b"p" * pad + b"\n"
        return {"clip.txt": b"".join(old)}, {"clip.txt": numbered("new", 300)}

    def last_boundary(section: bytes) -> int:
        return len(longest_line_prefix(section, CAP))

    base, head = padded(tmp_path, make, last_boundary)
    g = make_gate(tmp_path, base, head)
    dossier = assert_capped(g, "sweep", flow, ["clip.txt"])
    (text, marker), = [p for p in parse_diff_region(dossier) if p[1]]
    assert len(text) == CAP and int(marker["shown"]) == CAP


@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("phase", PHASES)
def test_a_clipped_hunk_keeps_its_cr_bytes_and_no_newline_annotation(tmp_path, phase, flow):
    old = b"".join(f"old {i:04d}\r\n".encode() for i in range(1, 301))[:-2]  # no newline at the end
    new = b"".join(f"new {i:04d}\n".encode() for i in range(1, 301))
    g = make_gate(tmp_path, {"crlf.txt": old}, {"crlf.txt": new})
    dossier = assert_capped(g, phase, flow, ["crlf.txt"])
    (text, _), = [p for p in parse_diff_region(dossier) if p[1]]
    assert b"-old 0299\r\n-old 0300\n\\ No newline at end of file\n+new 0001\n" in text


@pytest.mark.parametrize("flow", FLOWS)
def test_the_cap_holds_under_a_hostile_diff_config(tmp_path, flow):
    """color, no or mnemonic prefixes and submodule logs in the user's config change git's output;
    the dossier's sections are still git's plain --unified=1 sections, capped."""
    gitconfig = tmp_path / "hostile.gitconfig"
    gitconfig.write_text(
        "[color]\n\tui = always\n\tdiff = always\n"
        "[diff]\n\tnoprefix = true\n\tmnemonicPrefix = true\n\tsubmodule = log\n"
    )

    def add_submodule(repo: Path) -> None:
        sub = repo / "sub"
        sub.mkdir()
        git(sub, "init", "-q")
        git(sub, "config", "commit.gpgsign", "false")
        git(sub, "-c", "user.name=s", "-c", "user.email=s@example.com", "commit", "-q",
            "--allow-empty", "-m", "s")

    g = make_gate(tmp_path, {"big.txt": numbered("line", 800)},
                  {"big.txt": numbered("line", 800, lambda i: i % 8 == 0)},
                  head_ops=add_submodule,
                  env_extra={"GIT_CONFIG_GLOBAL": str(gitconfig), "GIT_CONFIG_NOSYSTEM": "1"})
    sections = git_sections(g)
    assert any(s.startswith(b"diff --git a/sub b/sub\n") for s in sections), "fixture lost its submodule"
    hostile = git_bytes(g["repo"], "diff", "--no-ext-diff", "--unified=1", f"{BASE_REF}...HEAD",
                        env=g["env"])
    assert b"\x1b[" in hostile and b"Submodule sub" in hostile, "the hostile config did not apply"
    for phase in PHASES:
        assert_capped(g, phase, flow, ["big.txt"])


# --- headers alone over the cap, and sections without text hunks -----------------------------------

@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("phase", PHASES)
def test_when_no_complete_line_fits_zero_bytes_of_the_section_are_emitted(tmp_path, phase, flow):
    path = deep_path(20, "far-too-long.txt")  # the `diff --git` line alone is over 4096 bytes
    g = make_gate(tmp_path, {path: b"a\nb\nc\n"}, {path: b"a\nB\nc\n"})
    dossier = assert_capped(g, phase, flow, [path])
    full, = git_sections(g)
    assert len(lines_of(full)[0]) > CAP
    (text, marker), = [p for p in parse_diff_region(dossier) if p[1]]
    assert text == b"" and int(marker["shown"]) == 0 and int(marker["total"]) == len(full)
    assert b"diff --git" not in dossier[dossier.index(b"===== DIFF ("):].split(b"\n", 1)[1].split(b"<!--")[0]


@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("phase", PHASES)
def test_header_lines_alone_over_the_cap_are_cut_at_a_line_boundary(tmp_path, phase, flow):
    path = deep_path(11, "long-header.txt")  # header lines total over 4096 bytes; the first fit
    g = make_gate(tmp_path, {path: b"a\nb\nc\n"}, {path: b"a\nB\nc\n"})
    dossier = assert_capped(g, phase, flow, [path])
    full, = git_sections(g)
    header, hunks = header_and_hunks(full)
    (text, _), = [p for p in parse_diff_region(dossier) if p[1]]
    assert len(header) > CAP and 0 < len(text) < len(header) and header.startswith(text)
    assert b"@@" not in text, "a hunk survived a header that alone exceeds the cap"


@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("phase", PHASES)
def test_a_binary_section_over_the_cap_follows_the_line_boundary_rule(tmp_path, phase, flow):
    path = deep_path(11, "blob.bin")
    g = make_gate(tmp_path, {path: bytes(range(256)) * 4}, {path: bytes(range(255, -1, -1)) * 4})
    dossier = assert_capped(g, phase, flow, [path])
    full, = git_sections(g)
    assert b"Binary files" in full and b"@@" not in full
    (text, _), = [p for p in parse_diff_region(dossier) if p[1]]
    assert 0 < len(text) < len(full) and b"Binary files" not in text


@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("phase", PHASES)
def test_a_mode_only_section_over_the_cap_follows_the_line_boundary_rule(tmp_path, phase, flow):
    path = deep_path(16, "f" * 25)  # `diff --git` ends at 4067 bytes, `old mode` fits, `new mode` does not

    def chmod(repo: Path) -> None:
        (repo / path).chmod(0o755)

    g = make_gate(tmp_path, {path: b"#!/bin/sh\n"}, {}, head_ops=chmod)
    dossier = assert_capped(g, phase, flow, [path])
    full, = git_sections(g)
    assert b"old mode 100644\nnew mode 100755\n" in full and b"@@" not in full
    (text, _), = [p for p in parse_diff_region(dossier) if p[1]]
    assert text.endswith(b"old mode 100644\n") and b"new mode" not in text


@pytest.mark.parametrize("flow", FLOWS)
def test_short_binary_and_mode_only_sections_are_untouched(tmp_path, flow):
    def chmod(repo: Path) -> None:
        (repo / "run.sh").chmod(0o755)

    g = make_gate(tmp_path, {"blob.bin": bytes(range(256)), "run.sh": b"#!/bin/sh\n"},
                  {"blob.bin": bytes(range(255, -1, -1))}, head_ops=chmod)
    assert_capped(g, "sweep", flow, [])


# --- splitting edge cases: paths, renames, deletions, binary, look-alike content --------------------

@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("phase", PHASES)
def test_the_marker_path_is_the_destination_path_re_escaped_only_when_it_must_be(tmp_path, phase, flow):
    names = {
        "my file.txt": "my file.txt",            # spaces need no quoting
        "café.txt": "café.txt",                  # git quotes it in the header; the marker does not
        'we"ird\\name.txt': '"we\\"ird\\\\name.txt"',  # a double quote and a backslash
        "tab\there.txt": '"tab\\there.txt"',     # a control byte
    }
    base = {name: numbered("old", 200) for name in names}
    head = {name: numbered("new", 200) for name in names}
    g = make_gate(tmp_path, base, head)
    sections = git_sections(g)
    assert any(s.startswith(b'diff --git "a/caf\\303\\251.txt"') for s in sections), "fixture lost its quoting"
    expected = [names[name] for name in sorted(names, key=lambda n: n.encode())]  # git sorts by path bytes
    assert_capped(g, phase, flow, expected)


@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("phase", PHASES)
def test_a_renamed_file_names_its_destination_and_a_deleted_file_its_source(tmp_path, phase, flow):
    def rename(repo: Path) -> None:
        (repo / "moved").mkdir()
        git(repo, "mv", "src/old name.txt", "moved/new name.txt")

    base = {"src/old name.txt": numbered("keep", 400), "gone/deleted.txt": numbered("bye", 400)}
    head = {"gone/deleted.txt": None,
            "moved/new name.txt": numbered("keep", 400, lambda i: i % 8 == 0)}
    g = make_gate(tmp_path, base, head, head_ops=rename)
    sections = git_sections(g)
    assert any(b"rename from src/old name.txt\nrename to moved/new name.txt\n" in s for s in sections)
    assert any(b"deleted file mode" in s and b"+++ /dev/null" in s for s in sections)
    dossier = assert_capped(g, phase, flow, ["gone/deleted.txt", "moved/new name.txt"])
    assert dossier.count(b"<!-- TRUNCATED: ") == 2


@pytest.mark.parametrize("flow", FLOWS)
def test_a_pure_rename_and_a_new_file_are_handled(tmp_path, flow):
    def rename(repo: Path) -> None:
        git(repo, "mv", "a.txt", "b.txt")

    g = make_gate(tmp_path, {"a.txt": numbered("same", 30)},
                  {"added.txt": numbered("fresh", 600)}, head_ops=rename)
    sections = git_sections(g)
    assert any(b"similarity index 100%" in s for s in sections)
    assert_capped(g, "sweep", flow, ["added.txt"])


@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("phase", PHASES)
def test_diff_look_alike_content_does_not_split_a_section(tmp_path, phase, flow):
    def lookalike(edit: bytes) -> bytes:  # lines 2 and 4 change, so lines 1, 3 and 5 are context
        return (b"diff --git a/x b/x\n@@ -1 +1 @@" + edit + b"\n<!-- TRUNCATED: fake (1/2 bytes) - nothing -->\n"
                b"\\ No newline at end of file" + edit + b"\n")

    g = make_gate(tmp_path, {"patch.txt": lookalike(b"") + numbered("body", 600)},
                  {"patch.txt": lookalike(b" edited") + numbered("body", 600, lambda i: i % 8 == 0)})
    sections = git_sections(g)
    assert len(sections) == 1 and b" diff --git a/x b/x\n" in sections[0]
    dossier = assert_capped(g, phase, flow, ["patch.txt"])
    assert b" diff --git a/x b/x\n" in dossier, "the look-alike context line was lost"


@pytest.mark.parametrize("flow", FLOWS)
def test_only_the_over_cap_files_are_truncated_among_many(tmp_path, flow):
    base = {f"f{i}.txt": numbered("row", 400) for i in range(6)}
    head = {f"f{i}.txt": numbered("row", 400, lambda n: n % (3 if i % 2 else 30) == 0) for i in range(6)}
    g = make_gate(tmp_path, base, head)
    sections = git_sections(g)
    over = [f"f{i}.txt" for i, s in enumerate(sections) if len(s) > CAP]
    assert 0 < len(over) < 6
    assert_capped(g, "sweep", flow, over)


# --- the arbitrate dossier still carries no diff ----------------------------------------------------

@pytest.mark.parametrize("flow", FLOWS)
def test_the_arbitrate_dossier_carries_neither_diff_nor_marker(tmp_path, flow):
    g = make_gate(tmp_path, {"big.txt": numbered("line", 800)},
                  {"big.txt": numbered("line", 800, lambda i: i % 8 == 0)})
    result = run_script("run", "hunt", *common(g, "hunt"), "--agent-cmd", COPY_AGENT, env=g["env"])
    assert result.returncode == 0, result.stdout + result.stderr
    if flow == "run":
        result = run_script("run", "arbitrate", *common(g, "hunt"), "--agent-cmd", COPY_AGENT, env=g["env"])
        assert result.returncode == 0, result.stdout + result.stderr
        seen = (g["scratch"] / "seen-dossier.md").read_bytes()
    else:
        result = run_script("dossier", "arbitrate", *common(g, "hunt"), env=g["env"])
        assert result.returncode == 0, result.stdout + result.stderr
        seen = Path(result.stdout.strip().splitlines()[-1]).read_bytes()
    assert b"===== DIFF" not in seen and b"<!-- TRUNCATED:" not in seen and b"diff --git" not in seen
    assert b"big.txt | " in seen, "the arbitrate dossier lost the diffstat"


# --- a failing `git diff` still fails the dossier write --------------------------------------------

def failing_unified_diff_env(g: dict) -> dict[str, str]:
    """A git that fails the capped diff call (and only it), after the checkout and diffstat succeed."""
    fakebin = g["tmp"] / "fakebin"
    fakebin.mkdir(exist_ok=True)
    real_git = subprocess.run(["bash", "-c", "command -v git"], capture_output=True,
                              text=True, check=True).stdout.strip()
    wrapper = fakebin / "git"
    wrapper.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = diff ] && [ "$2" = --no-ext-diff ]; then echo "capped diff refused" >&2; exit 3; fi\n'
        f'exec "{real_git}" "$@"\n'
    )
    wrapper.chmod(0o755)
    return {**g["env"], "PATH": f"{fakebin}:{g['env']['PATH']}"}


def registered_worktrees(repo: Path) -> list[str]:
    out = git(repo, "worktree", "list", "--porcelain")
    return [line.removeprefix("worktree ") for line in out.splitlines() if line.startswith("worktree ")]


@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("phase", PHASES)
def test_a_failing_diff_call_fails_the_dossier_write_and_leaves_nothing_behind(tmp_path, phase, flow):
    g = make_gate(tmp_path, {"big.txt": numbered("line", 800)},
                  {"big.txt": numbered("line", 800, lambda i: i % 8 == 0)})
    env = failing_unified_diff_env(g)
    if flow == "run":
        result = run_script("run", phase, *common(g, phase), "--agent-cmd", COPY_AGENT, env=env)
    else:
        result = run_script("dossier", phase, *common(g, phase), env=env)
    assert result.returncode != 0, result.stdout + result.stderr
    assert f"could not write the {phase} dossier" in result.stderr, result.stderr
    assert not (g["scratch"] / "seen-dossier.md").exists(), "the agent ran on a failed dossier"
    assert not list(g["scratch"].rglob(f"{phase}-dossier.md")), "a partial dossier was left"
    assert registered_worktrees(g["repo"]) == [str(g["repo"].resolve())], "a checkout was left registered"
    run_dir = Path(git(g["repo"], "rev-parse", "--path-format=absolute", "--git-path", "adversarial-pipeline"))
    left = [p.name for p in run_dir.rglob("*") if p.name in (f"{phase}.launch", f"{phase}.binding")]
    assert left == [], f"the failed {phase} phase left {left}"


def test_the_preflight_fails_when_python3_cannot_run(tmp_path):
    g = make_gate(tmp_path, {"a.txt": b"a\n"}, {"a.txt": b"b\n"})
    fakebin = tmp_path / "nopython"
    fakebin.mkdir()
    (fakebin / "python3").write_text("#!/bin/sh\nexit 127\n")
    (fakebin / "python3").chmod(0o755)
    env = {**g["env"], "PATH": f"{fakebin}:{g['env']['PATH']}"}
    result = run_script("preflight", "--repo", str(g["repo"]), "--base", BASE_REF,
                        "--test-cmd", "true", "--scratch", str(g["scratch"]), env=env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL - python3 is not runnable here" in result.stdout, result.stdout
