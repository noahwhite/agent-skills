"""The leak scan must fire on every banned shape and stay quiet on examples."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import leak_scan  # noqa: E402

PUBLIC = leak_scan.load_public()
CLEAN = """\
Target `profile.git.integration_branch`, e.g. develop.
File the story as ABC-123 or EXA-42.
Clone git@github.com:example-org/example-app.git and mail bot@example.com.
opencode 1.18.34 and node 22.11.0 on 127.0.0.1 or 10.0.0.4 or 192.0.2.10.
Install from example-org/agent-skills.
"""


def test_each_pattern_matches_its_sample():
    for rx, sample in PUBLIC:
        assert rx.search(sample), f"{rx.pattern!r} no longer matches {sample!r}"


def test_each_sample_trips_the_scanner(tmp_path, monkeypatch):
    monkeypatch.setattr(leak_scan, "ROOT", tmp_path)
    for i, (_, sample) in enumerate(PUBLIC):
        (tmp_path / f"s{i}.md").write_text(sample + "\n")
    hits = leak_scan.scan([f"s{i}.md" for i in range(len(PUBLIC))], PUBLIC, [])
    flagged = {h.split(":", 1)[0] for h in hits}
    assert flagged == {f"s{i}.md" for i in range(len(PUBLIC))}


def test_clean_text_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(leak_scan, "ROOT", tmp_path)
    (tmp_path / "clean.md").write_text(CLEAN)
    assert leak_scan.scan(["clean.md"], PUBLIC, []) == []


def test_hits_never_echo_the_match(tmp_path, monkeypatch):
    monkeypatch.setattr(leak_scan, "ROOT", tmp_path)
    secret = "ghp_" + "a1" * 15
    (tmp_path / "t.md").write_text(f"token {secret}\n")
    hits = leak_scan.scan(["t.md"], PUBLIC, [])
    assert hits and all(secret not in h for h in hits)


def test_private_patterns_are_reported_by_number_only(tmp_path):
    (tmp_path / "x.md").write_text("internal-host-7\n")
    env = {"LEAK_DENYLIST": r"internal-host-\d+", "PATH": "/usr/bin:/bin"}
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "leak_scan.py"), str(tmp_path / "x.md")],
        capture_output=True, text=True, env=env,
    )
    assert res.returncode == 1
    assert "private pattern #1" in res.stdout
    assert "internal-host" not in res.stdout


def run_scan(tmp_path, env_extra, *args):
    env = {"PATH": "/usr/bin:/bin", **env_extra}
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "leak_scan.py"), *args],
        capture_output=True, text=True, env=env, cwd=tmp_path,
    )


def test_private_patterns_load_from_file(tmp_path):
    (tmp_path / "x.md").write_text("internal-host-7\n")
    (tmp_path / "deny.txt").write_text("# comment line\ninternal-host-\\d+\n")
    res = run_scan(tmp_path, {"LEAK_DENYLIST_FILE": str(tmp_path / "deny.txt")}, str(tmp_path / "x.md"))
    assert res.returncode == 1
    assert "private pattern #1" in res.stdout


def test_missing_private_patterns_is_reported(tmp_path):
    (tmp_path / "x.md").write_text("plain\n")
    res = run_scan(tmp_path, {}, str(tmp_path / "x.md"))
    assert res.returncode == 0 and "INCOMPLETE" in res.stdout
    res = run_scan(tmp_path, {}, "--require-private", str(tmp_path / "x.md"))
    assert res.returncode == 2 and "INCOMPLETE" in res.stdout


def test_non_utf8_files_are_still_scanned(tmp_path, monkeypatch):
    monkeypatch.setattr(leak_scan, "ROOT", tmp_path)
    addr = "ops" + "@" + "corp.test"
    (tmp_path / "latin1.md").write_bytes(f"caf\xe9 {addr}\n".encode("latin-1"))
    (tmp_path / "bin.png").write_bytes(b"\x89PNG\0\x01\x02\xff")
    texts = ["latin1.md"]
    line = f"note {addr}\n"
    # With and without a byte-order mark; "utf-16" and "utf-32" write a little-endian mark.
    encoded = {
        "utf-16": line.encode("utf-16"),
        "utf-16-le": line.encode("utf-16-le"),
        "utf-16-be": line.encode("utf-16-be"),
        "utf-32": line.encode("utf-32"),
        "utf-32-be-bom": b"\0\0\xfe\xff" + line.encode("utf-32-be"),
        # Mostly non-ASCII text without a mark.
        "utf-16-le-cyrillic": ("\u0437\u0430\u043c\u0435\u0442\u043a\u0430 " * 20 + line).encode("utf-16-le"),
        "utf-16-be-cjk": ("\u8bb0\u5f55" * 40 + " " + line).encode("utf-16-be"),
    }
    for enc, data in encoded.items():
        name = f"{enc}.txt"
        (tmp_path / name).write_bytes(data)
        texts.append(name)
    hits = leak_scan.scan(["latin1.md", "bin.png", *texts[1:]], PUBLIC, [])
    assert [h.split(":", 1)[0] for h in hits] == texts


def test_repository_is_clean():
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "leak_scan.py")],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stdout
