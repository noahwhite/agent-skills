"""SKL-142: the profile names the commit signing key and a vendored preflight checks it.

C1 is the schema key, C2 the preflight script and its vendoring, C3 the rule in shared/github.md.
Every script test runs in a hermetic environment: a temporary HOME, GIT_CONFIG_GLOBAL and
SSH_AUTH_SOCK, generated keys and a test-owned ssh-agent, never the runner's keys or git config.
"""

import copy
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())
EXAMPLE = yaml.safe_load((ROOT / "profile" / "example.yaml").read_text())
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)
SOURCE = ROOT / "shared" / "check-signing-key.sh"
GITHUB = ROOT / "shared" / "github.md"
MANIFEST = json.loads((ROOT / "skills.json").read_text())
FINGERPRINT = re.compile(r"^SHA256:[A-Za-z0-9+/]{43}$")
VALID = "SHA256:Kj2Cb8r6b1YQ5hksGDH0FeiivWj1DZ8puXI8+IlN9l0"


# --- C1: the schema key --------------------------------------------------------------------


def with_key(value):
    profile = copy.deepcopy(EXAMPLE)
    profile["git"]["signing_key"] = value
    return profile


def test_the_schema_accepts_a_valid_fingerprint():
    assert not list(VALIDATOR.iter_errors(with_key(VALID)))


def test_the_schema_accepts_a_profile_without_the_key():
    profile = copy.deepcopy(EXAMPLE)
    del profile["git"]["signing_key"]
    assert not list(VALIDATOR.iter_errors(profile))


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        None,
        "SHA256:",
        VALID[:-1],
        VALID + "A",
        VALID + "=",
        " " + VALID,
        VALID + " ",
        "MD5:" + VALID[7:],
        "sha256:" + VALID[7:],
        VALID.replace("Kj2C", "Kj2_"),
        42,
    ],
    ids=[
        "empty", "whitespace", "null", "prefix-only", "short", "long", "padded",
        "leading-space", "trailing-space", "wrong-algorithm", "lowercase-prefix",
        "url-safe-alphabet", "number",
    ],
)
def test_the_schema_rejects_a_malformed_fingerprint(value):
    assert list(VALIDATOR.iter_errors(with_key(value)))


def test_the_signing_key_schema_entry_documents_itself():
    git = SCHEMA["properties"]["git"]["properties"]
    entry = git["signing_key"]
    assert entry["type"] == "string"
    assert entry["pattern"] == "^SHA256:[A-Za-z0-9+/]{43}$"
    assert "signed_commits" in entry["description"]
    assert "git.signing_key" in git["signed_commits"]["description"]
    assert "signing_key" not in SCHEMA["properties"]["git"].get("required", [])


def test_the_example_profile_shows_the_key_next_to_signed_commits():
    lines = (ROOT / "profile" / "example.yaml").read_text().splitlines()
    at = next(i for i, line in enumerate(lines) if line.strip().startswith("signed_commits:"))
    assert lines[at + 1].strip().startswith("signing_key: SHA256:")
    assert FINGERPRINT.match(EXAMPLE["git"]["signing_key"])


# --- C2: the preflight script --------------------------------------------------------------


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kw)


@dataclass
class Rig:
    """A hermetic signing environment: a repository, generated keys, a test-owned agent."""

    root: Path
    repo: Path
    env: dict
    a: Path  # the registered key
    b: Path  # a second, unregistered key
    fp_a: str
    fp_b: str

    def git(self, *args):
        res = run(["git", "-C", str(self.repo), *args], env=self.env)
        assert res.returncode == 0, res.stderr
        return res.stdout

    def config(self, key, value):
        self.git("config", "--global", key, value)

    def pub(self, key: Path) -> str:
        return key.with_suffix(".pub").read_text().strip()

    def add(self, key: Path):
        res = run(["ssh-add", str(key)], env=self.env)
        assert res.returncode == 0, res.stderr

    def emitter(self, name: str, body: str) -> str:
        """An executable the default key command can name, since git runs it without a shell."""
        path = self.root / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o755)
        return str(path)

    def key_command(self, key: Path, name: str = "emit") -> str:
        return self.emitter(name, f"printf 'key::%s\\n' \"$(cat {key}.pub)\"")

    def check(self, *args, script=SOURCE):
        return run(["bash", str(script), *args], env=self.env, cwd=self.repo)


def keygen(path: Path, comment: str) -> str:
    res = run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", comment, "-f", str(path)])
    assert res.returncode == 0, res.stderr
    res = run(["ssh-keygen", "-E", "sha256", "-lf", str(path) + ".pub"])
    return res.stdout.split()[1]


@pytest.fixture
def rig():
    # A short path: unix socket names are limited to about 100 bytes.
    root = Path(tempfile.mkdtemp(prefix="skl142-"))
    home = root / "home"
    (home / ".ssh").mkdir(parents=True)
    repo = root / "repo"
    repo.mkdir()
    sock = root / "agent.sock"
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "GIT_CONFIG_GLOBAL": str(home / "gitconfig"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "SSH_AUTH_SOCK": str(sock),
        "LANG": "C",
    }
    agent = subprocess.Popen(["ssh-agent", "-D", "-a", str(sock)], env=env, stdout=subprocess.DEVNULL)
    try:
        for _ in range(100):
            if sock.exists():
                break
            time.sleep(0.05)
        assert sock.exists(), "the test ssh-agent did not start"
        a, b = home / ".ssh" / "registered", home / ".ssh" / "other"
        built = Rig(root, repo, env, a, b, keygen(a, "registered@test"), keygen(b, "other@test"))
        built.git("init", "-q")
        built.config("gpg.format", "ssh")
        yield built
    finally:
        agent.terminate()
        agent.wait(timeout=10)
        shutil.rmtree(root, ignore_errors=True)


def assert_ok(res):
    assert res.returncode == 0, res.stderr
    assert res.stdout == "" and res.stderr == ""


def assert_fails(res, expected, resolved, reason):
    """Exactly one stderr line naming the expected and resolved fingerprints and the reason."""
    assert res.returncode != 0
    assert res.stdout == ""
    assert res.stderr.endswith("\n") and res.stderr.count("\n") == 1, res.stderr
    assert expected in res.stderr
    assert f"resolved {resolved}" in res.stderr, res.stderr
    assert reason and reason in res.stderr, res.stderr



# --- C2: git resolves the key; the preflight must agree with what git commit -S signs with ----


def make_key(rig, name, kind="ed25519", passphrase="", fmt=None):
    """Generate a key under HOME/.ssh; return (private path, SHA256 fingerprint)."""
    path = rig.root / "home" / ".ssh" / name
    cmd = ["ssh-keygen", "-q", "-t", kind, "-N", passphrase, "-C", name, "-f", str(path)]
    if kind == "rsa":
        cmd[1:1] = ["-b", "2048"]
    if fmt:
        cmd[1:1] = ["-m", fmt]
    res = run(cmd)
    assert res.returncode == 0, res.stderr
    out = run(["ssh-keygen", "-E", "sha256", "-lf", str(path) + ".pub"]).stdout
    return path, out.split()[1]


def load_into_agent(rig, path, passphrase=""):
    """ssh-add a key, answering a passphrase prompt through a test-owned askpass program."""
    env = dict(rig.env)
    if passphrase:
        askpass = rig.root / "askpass"
        askpass.write_text(f"#!/bin/sh\necho '{passphrase}'\n")
        askpass.chmod(0o755)
        env.update(SSH_ASKPASS=str(askpass), SSH_ASKPASS_REQUIRE="force")
    res = run(["ssh-add", str(path)], env=env, stdin=subprocess.DEVNULL)
    assert res.returncode == 0, res.stderr


def git_signs_with(rig, cwd=None):
    """The SHA256 fingerprint of the key a real git commit -S signs with, or None when git cannot sign."""
    allowed = rig.root / "allowed_signers"
    lines = []
    for pub in sorted((rig.root / "home" / ".ssh").glob("*.pub")):
        lines.append("* " + " ".join(pub.read_text().split()[:2]))
    allowed.write_text("\n".join(lines) + "\n")
    work = cwd or rig.repo
    base = ["git", "-c", f"gpg.ssh.allowedSignersFile={allowed}", "-c", "user.name=t", "-c", "user.email=t@example.com"]
    env = {**rig.env, "SSH_ASKPASS": "/bin/false", "SSH_ASKPASS_REQUIRE": "force"}
    res = run([*base, "commit", "-q", "--allow-empty", "-S", "-m", "x"], env=env, cwd=work, stdin=subprocess.DEVNULL)
    if res.returncode != 0:
        return None
    out = run([*base, "log", "-1", "--format=%GF"], env=env, cwd=work).stdout.strip()
    return out or None


def snapshot(rig):
    """Everything in the repository a preflight must leave alone: files, refs, config, index, objects."""
    files = {}
    for path in sorted(rig.repo.rglob("*")):
        if path.is_file():
            files[str(path.relative_to(rig.repo))] = (path.stat().st_size, path.read_bytes())
    refs = rig.git("for-each-ref") if (rig.repo / ".git" / "refs").exists() else ""
    return files, refs, (rig.root / "home" / "gitconfig").read_bytes()


def resolve_via_git(rig, cwd=None):
    """Run the oracle on a copy of the state, so the oracle's own commit does not disturb the next check."""
    before = rig.git("rev-parse", "-q", "--verify", "HEAD") if has_head(rig) else None
    fp = git_signs_with(rig, cwd)
    if before is None:
        shutil.rmtree(rig.repo / ".git" / "refs" / "heads", ignore_errors=True)
        (rig.repo / ".git" / "refs" / "heads").mkdir()
        (rig.repo / ".git" / "index").unlink(missing_ok=True)
    else:
        rig.git("reset", "-q", "--soft", before)
    return fp


def has_head(rig):
    return run(["git", "-C", str(rig.repo), "rev-parse", "-q", "--verify", "HEAD"], env=rig.env).returncode == 0


def agree_with_git(rig, expect_fp, other_fp, cwd=None):
    """The preflight signs-with answer equals git's: a match passes, any other registered fp names the real signer."""
    git_fp = resolve_via_git(rig, cwd)
    assert git_fp == expect_fp, f"git signs with {git_fp}, the scenario expected {expect_fp}"
    run_in = cwd or rig.repo
    if git_fp is None:
        for fp in (rig.fp_a, other_fp):
            res = run(["bash", str(SOURCE), fp], env=rig.env, cwd=run_in)
            assert_fails(res, fp, "unresolved", "git cannot sign")
    else:
        assert_ok(run(["bash", str(SOURCE), git_fp], env=rig.env, cwd=run_in))
        other = other_fp if other_fp != git_fp else rig.fp_b
        res = run(["bash", str(SOURCE), other], env=rig.env, cwd=run_in)
        assert_fails(res, other, git_fp, "mismatch")


# Every way user.signingkey and gpg.ssh.defaultKeyCommand can name the registered key a.


def test_a_matching_key_literal_passes(rig):
    rig.add(rig.a)
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    assert_ok(rig.check(rig.fp_a))
    agree_with_git(rig, rig.fp_a, rig.fp_b)


def test_a_bare_ssh_literal_passes_as_git_signs_with_it(rig):
    rig.add(rig.a)
    rig.config("user.signingkey", rig.pub(rig.a))
    assert_ok(rig.check(rig.fp_a))
    agree_with_git(rig, rig.fp_a, rig.fp_b)


@pytest.mark.parametrize("value", ["literal", "bare", "file", "tilde"])
def test_a_public_key_that_is_not_loaded_in_the_agent_fails(rig, value):
    """A literal needs the agent; a public-key file needs it unless the private key sits beside it."""
    if value in ("file", "tilde"):
        rig.a.unlink()
    rig.config(
        "user.signingkey",
        {
            "literal": "key::" + rig.pub(rig.a),
            "bare": rig.pub(rig.a),
            "file": str(rig.a) + ".pub",
            "tilde": "~/.ssh/registered.pub",
        }[value],
    )
    res = rig.check(rig.fp_a)
    assert_fails(res, rig.fp_a, "unresolved", "ssh agent")
    agree_with_git(rig, None, rig.fp_b)


@pytest.mark.parametrize("value", ["file", "tilde"])
def test_a_public_key_file_with_its_private_key_beside_it_passes_without_the_agent(rig, value):
    rig.config("user.signingkey", str(rig.a) + ".pub" if value == "file" else "~/.ssh/registered.pub")
    assert_ok(rig.check(rig.fp_a))
    agree_with_git(rig, rig.fp_a, rig.fp_b)


def test_a_public_key_file_passes(rig):
    rig.add(rig.a)
    rig.config("user.signingkey", str(rig.a) + ".pub")
    assert_ok(rig.check(rig.fp_a))
    agree_with_git(rig, rig.fp_a, rig.fp_b)


def test_a_tilde_public_key_path_passes(rig):
    rig.add(rig.a)
    rig.config("user.signingkey", "~/.ssh/registered.pub")
    agree_with_git(rig, rig.fp_a, rig.fp_b)


def test_a_tilde_user_public_key_path_passes_as_it_does_for_git(rig):
    """~<user>/ resolves from the account's home in the passwd database, not from $HOME."""
    import pwd

    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    user = pwd.getpwuid(os.getuid()).pw_name
    rig.add(rig.a)
    rel = os.path.relpath(str(rig.a) + ".pub", home)
    rig.config("user.signingkey", f"~{user}/{rel}")
    agree_with_git(rig, rig.fp_a, rig.fp_b)


def test_an_unknown_tilde_user_is_unresolved_as_it_is_for_git(rig):
    rig.add(rig.a)
    rig.config("user.signingkey", "~no-such-user-skl142/key.pub")
    agree_with_git(rig, None, rig.fp_b)


@pytest.mark.parametrize("via", ["literal", "command"])
@pytest.mark.parametrize("kind", ["ed25519", "rsa", "ecdsa"])
def test_a_key_literal_and_command_output_of_each_key_type_pass(rig, kind, via):
    path, fp = make_key(rig, "typed", kind)
    load_into_agent(rig, path)
    if via == "literal":
        rig.config("user.signingkey", "key::" + path.with_suffix(".pub").read_text().strip())
    else:
        rig.config("gpg.ssh.defaultKeyCommand", rig.key_command(path))
    assert_ok(rig.check(fp))
    agree_with_git(rig, fp, rig.fp_b)


def test_a_matching_default_key_command_passes(rig):
    rig.add(rig.a)
    rig.config("gpg.ssh.defaultKeyCommand", rig.key_command(rig.a))
    assert_ok(rig.check(rig.fp_a))
    agree_with_git(rig, rig.fp_a, rig.fp_b)


def test_a_default_key_command_printing_a_bare_ssh_line_passes_as_git_signs_with_it(rig):
    rig.add(rig.a)
    rig.config("gpg.ssh.defaultKeyCommand", "ssh-add -L")
    assert_ok(rig.check(rig.fp_a))
    agree_with_git(rig, rig.fp_a, rig.fp_b)


def test_the_default_key_command_runs_without_a_shell_like_git(rig):
    rig.add(rig.a)
    rig.config("gpg.ssh.defaultKeyCommand", f"printf 'key::%s\\n' \"$(cat {rig.a}.pub)\"")
    agree_with_git(rig, None, rig.fp_b)


def test_the_signingkey_wins_over_the_default_key_command(rig):
    rig.add(rig.a)
    rig.add(rig.b)
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    rig.config("gpg.ssh.defaultKeyCommand", rig.key_command(rig.b))
    assert_ok(rig.check(rig.fp_a))
    assert_fails(rig.check(rig.fp_b), rig.fp_b, rig.fp_a, "mismatch")


@pytest.mark.parametrize("value", ["", "/nonexistent/key.pub", "key::not a key", "key::"])
def test_an_unresolvable_signingkey_fails_without_falling_back(rig, value):
    rig.add(rig.a)
    rig.config("user.signingkey", value)
    rig.config("gpg.ssh.defaultKeyCommand", rig.key_command(rig.a))
    assert_fails(rig.check(rig.fp_a), rig.fp_a, "unresolved", "git cannot sign")
    agree_with_git(rig, None, rig.fp_b)


def test_a_directory_as_signingkey_fails(rig):
    rig.add(rig.a)
    rig.config("user.signingkey", str(rig.root))
    agree_with_git(rig, None, rig.fp_b)


def test_no_resolvable_key_fails(rig):
    rig.add(rig.a)
    assert_fails(rig.check(rig.fp_a), rig.fp_a, "unresolved", "git cannot sign")


@pytest.mark.parametrize("command", ["false", "echo", "echo not-a-key", "echo key::bogus"])
def test_a_failing_or_malformed_default_key_command_fails(rig, command):
    rig.add(rig.a)
    rig.config("gpg.ssh.defaultKeyCommand", command)
    assert_fails(rig.check(rig.fp_a), rig.fp_a, "unresolved", "git cannot sign")
    agree_with_git(rig, None, rig.fp_b)


def test_only_the_first_line_of_the_command_output_counts(rig):
    rig.add(rig.a)
    rig.add(rig.b)
    script = rig.emitter("two", f"printf 'key::%s\\nkey::%s\\n' \"$(cat {rig.a}.pub)\" \"$(cat {rig.b}.pub)\"")
    rig.config("gpg.ssh.defaultKeyCommand", script)
    agree_with_git(rig, rig.fp_a, rig.fp_b)


def test_a_relative_default_key_command_runs_from_the_work_tree_top_as_for_git(rig):
    rig.add(rig.a)
    tools = rig.repo / "tools"
    tools.mkdir()
    emit = tools / "emit"
    emit.write_text(f"#!/bin/sh\nprintf 'key::%s\\n' \"$(cat {rig.a}.pub)\"\n")
    emit.chmod(0o755)
    sub = rig.repo / "deep" / "er"
    sub.mkdir(parents=True)
    rig.config("gpg.ssh.defaultKeyCommand", "tools/emit")
    agree_with_git(rig, rig.fp_a, rig.fp_b, cwd=sub)
    agree_with_git(rig, rig.fp_a, rig.fp_b)


@pytest.mark.parametrize("form", ["public", "private"])
def test_a_relative_key_path_is_relative_to_the_work_tree_top_as_for_git(rig, form):
    rig.add(rig.a)
    sub = rig.repo / "deep" / "er"
    sub.mkdir(parents=True)
    src = Path(str(rig.a) + (".pub" if form == "public" else ""))
    (rig.repo / "key").write_text(src.read_text())
    (rig.repo / "key").chmod(0o600)
    rig.config("user.signingkey", "key")
    agree_with_git(rig, rig.fp_a, rig.fp_b, cwd=sub)
    agree_with_git(rig, rig.fp_a, rig.fp_b)


# Private-key files: any type, format and passphrase state, loaded in the agent or not.

PRIVATE_FORMS = [
    pytest.param("ed25519", "", None, id="ed25519"),
    pytest.param("ed25519", "secret", None, id="ed25519-passphrase"),
    pytest.param("rsa", "", None, id="rsa"),
    pytest.param("rsa", "secret", None, id="rsa-passphrase"),
    pytest.param("rsa", "", "PEM", id="rsa-pem"),
    pytest.param("rsa", "secret", "PEM", id="rsa-pem-passphrase"),
    pytest.param("ecdsa", "", None, id="ecdsa"),
    pytest.param("ecdsa", "secret", None, id="ecdsa-passphrase"),
    pytest.param("ecdsa", "", "PEM", id="ecdsa-pem"),
    pytest.param("ecdsa", "secret", "PEM", id="ecdsa-pem-passphrase"),
]


@pytest.mark.parametrize("pub_beside", [True, False], ids=["pub-beside", "no-pub-beside"])
@pytest.mark.parametrize("loaded", [True, False], ids=["agent-loaded", "agent-empty"])
@pytest.mark.parametrize("kind,passphrase,fmt", PRIVATE_FORMS)
def test_a_private_key_file_agrees_with_what_git_signs_with(rig, kind, passphrase, fmt, loaded, pub_beside):
    path, fp = make_key(rig, "priv", kind, passphrase, fmt)
    if not pub_beside:
        Path(str(path) + ".pub").unlink()
    rig.config("user.signingkey", str(path))
    if loaded:
        load_into_agent(rig, path, passphrase)
    git_fp = resolve_via_git(rig)
    if git_fp is not None:
        assert git_fp == fp
        assert_ok(rig.check(fp))
        assert_fails(rig.check(rig.fp_b), rig.fp_b, fp, "mismatch")
    else:
        assert_fails(rig.check(fp), fp, "unresolved", "git cannot sign")
    if (loaded or not passphrase) and not (fmt == "PEM" and not pub_beside):
        assert git_fp == fp, "git must sign with a loaded or unencrypted key file"


def test_a_pem_private_key_with_leading_lines_agrees_with_git(rig):
    path, fp = make_key(rig, "priv", "rsa", "", "PEM")
    path.write_text("\n# note\n" + path.read_text())
    rig.config("user.signingkey", str(path))
    load_into_agent(rig, path)
    git_fp = resolve_via_git(rig)
    assert git_fp == fp
    assert_ok(rig.check(fp))


@pytest.mark.parametrize("loaded", ["foreign", "none"])
def test_a_foreign_public_file_beside_a_private_key_signs_with_the_foreign_key_only_via_the_agent(rig, loaded):
    """git takes the key from the .pub beside the file; the preflight reports whichever key git signs with."""
    path, fp = make_key(rig, "priv", "ed25519")
    other, other_fp = make_key(rig, "foreign", "ed25519")
    Path(str(path) + ".pub").write_text(Path(str(other) + ".pub").read_text())
    rig.config("user.signingkey", str(path))
    if loaded == "foreign":
        load_into_agent(rig, other)
    git_fp = resolve_via_git(rig)
    if loaded == "foreign":
        assert git_fp == other_fp
        assert_ok(rig.check(other_fp))
        assert_fails(rig.check(fp), fp, other_fp, "mismatch")
    else:
        assert git_fp is None
        assert_fails(rig.check(fp), fp, "unresolved", "git cannot sign")


# gpg.format, argument, output contract, repository untouched, cleanup.


@pytest.mark.parametrize("fmt", ["openpgp", "x509", None])
def test_a_gpg_format_other_than_ssh_fails(rig, fmt):
    rig.add(rig.a)
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    if fmt is None:
        rig.git("config", "--global", "--unset", "gpg.format")
    else:
        rig.config("gpg.format", fmt)
    assert_fails(rig.check(rig.fp_a), rig.fp_a, "unresolved", "gpg.format")


def test_the_signing_key_of_a_work_tree_with_includes_is_resolved_like_git(rig):
    rig.add(rig.a)
    (rig.root / "extra").write_text(f"[user]\n\tsigningkey = key::{rig.pub(rig.a)}\n")
    rig.git("config", "include.path", str(rig.root / "extra"))
    agree_with_git(rig, rig.fp_a, rig.fp_b)


@pytest.mark.parametrize(
    "args",
    [(), ("",), (" ",), ("SHA256:short",), ("MD5:" + "a" * 43,), (VALID, VALID), (VALID + "x",), (VALID[:-1],)],
    ids=["none", "empty", "space", "short", "md5", "two", "long", "short-by-one"],
)
def test_a_malformed_argument_fails(rig, args):
    rig.add(rig.a)
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    res = rig.check(*args)
    assert res.returncode != 0 and res.stdout == ""
    assert res.stderr.count("\n") == 1 and "argument" in res.stderr
    assert "expected invalid" in res.stderr
    for arg in args:
        assert not arg.strip() or arg not in res.stderr


def test_the_check_outside_a_repository_fails_with_one_line(rig):
    res = run(["bash", str(SOURCE), rig.fp_a], env=rig.env, cwd=rig.root)
    assert res.returncode != 0 and res.stdout == "" and res.stderr.count("\n") == 1


def test_a_passed_check_changes_nothing_in_the_repository(rig):
    rig.add(rig.a)
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    rig.git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "base", "--no-gpg-sign")
    (rig.repo / "work").write_text("w")
    rig.git("add", "work")
    (rig.repo / "other").write_text("o")
    before, head = snapshot(rig), rig.git("rev-parse", "HEAD")
    objects = rig.git("count-objects", "-v")
    assert_ok(rig.check(rig.fp_a))
    assert_fails(rig.check(rig.fp_b), rig.fp_b, rig.fp_a, "mismatch")
    assert snapshot(rig) == before
    assert rig.git("rev-parse", "HEAD") == head
    assert rig.git("count-objects", "-v") == objects
    assert rig.git("fsck", "--lost-found", "--no-dangling") == ""
    assert rig.git("status", "--porcelain") == "A  work\n?? other\n"


def test_a_failed_check_changes_nothing_in_the_repository(rig):
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    before = snapshot(rig)
    assert rig.check(rig.fp_a).returncode != 0
    assert snapshot(rig) == before


def temp_dir_after(rig, fingerprint):
    tmp = Path(tempfile.mkdtemp(dir=rig.root))
    res = run(["bash", str(SOURCE), fingerprint], env={**rig.env, "TMPDIR": str(tmp)}, cwd=rig.repo)
    return res, list(tmp.iterdir())


def test_the_temporary_directory_is_removed_on_success_and_on_failure(rig):
    rig.add(rig.a)
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    for fp in (rig.fp_a, rig.fp_b):
        res, left = temp_dir_after(rig, fp)
        assert left == [], res.stderr


@pytest.mark.parametrize("target", ["group-sigint", "shell-sigterm", "shell-sighup", "shell-sigint"])
def test_an_interrupted_run_stops_the_signer_removes_its_temporary_directory_and_prints_one_line(rig, target):
    rig.add(rig.a)
    started, pidfile = rig.root / "started", rig.root / "signer.pid"
    program = rig.emitter("slow-sign", f"echo $$ > {pidfile}\n: > {started}\nexec sleep 30")
    rig.config("gpg.ssh.program", program)
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    tmp = Path(tempfile.mkdtemp(dir=rig.root))
    proc = subprocess.Popen(
        ["bash", str(SOURCE), rig.fp_a],
        env={**rig.env, "TMPDIR": str(tmp)},
        cwd=rig.repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        for _ in range(200):
            if started.exists():
                break
            time.sleep(0.05)
        assert started.exists(), "the signing program never started"
        if target == "group-sigint":
            os.killpg(proc.pid, signal.SIGINT)
        else:
            proc.send_signal({"sigterm": signal.SIGTERM, "sighup": signal.SIGHUP, "sigint": signal.SIGINT}[target.split("-")[1]])
        out, err = proc.communicate(timeout=10)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
    assert proc.returncode == 1 and out == ""
    assert err.count("\n") == 1 and err.startswith("check-signing-key: expected "), err
    assert list(tmp.iterdir()) == []
    pid = int(pidfile.read_text())
    for _ in range(100):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        raise AssertionError("the signer is still running")


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGHUP, signal.SIGINT], ids=["term", "hup", "int"])
@pytest.mark.parametrize("target", ["shell", "group"])
def test_a_signal_during_cleanup_cannot_skip_the_removal_or_the_single_line(rig, sig, target):
    rig.add(rig.a)
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    shim, marker = rig.root / "shim", rig.root / "rm-started"
    shim.mkdir()
    rm = shim / "rm"
    rm.write_text(f"#!/bin/sh\n: > {marker}\nsleep 1\nexec /bin/rm \"$@\"\n")
    rm.chmod(0o755)
    tmp = Path(tempfile.mkdtemp(dir=rig.root))
    proc = subprocess.Popen(
        ["bash", str(SOURCE), rig.fp_a],
        env={**rig.env, "PATH": f"{shim}:{rig.env['PATH']}", "TMPDIR": str(tmp)},
        cwd=rig.repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        for _ in range(200):
            if marker.exists():
                break
            time.sleep(0.02)
        assert marker.exists(), "cleanup never started"
        if target == "group":
            os.killpg(proc.pid, sig)
        else:
            proc.send_signal(sig)
        out, err = proc.communicate(timeout=10)
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
    # The run had already succeeded when the signal arrived: cleanup finishes, silently, exit 0.
    assert (proc.returncode, out, err) == (0, "", "")
    assert list(tmp.iterdir()) == []


def test_a_setup_failure_prints_exactly_one_line(rig):
    rig.add(rig.a)
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    res = run(
        ["bash", str(SOURCE), rig.fp_a],
        env={**rig.env, "TMPDIR": str(rig.root / "missing")},
        cwd=rig.repo,
    )
    assert res.returncode == 1 and res.stdout == "" and res.stderr.count("\n") == 1
    assert str(rig.root) not in res.stderr


@pytest.mark.parametrize("registered", ["match", "mismatch"])
def test_a_failure_to_remove_the_temporary_directory_is_reported_once_never_as_success(rig, registered):
    rig.add(rig.a)
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    shim = rig.root / "shim"
    shim.mkdir()
    rm = shim / "rm"
    rm.write_text("#!/bin/sh\nexit 1\n")
    rm.chmod(0o755)
    tmp = Path(tempfile.mkdtemp(dir=rig.root))
    res = run(
        ["bash", str(SOURCE), rig.fp_a if registered == "match" else rig.fp_b],
        env={**rig.env, "PATH": f"{shim}:{rig.env['PATH']}", "TMPDIR": str(tmp)},
        cwd=rig.repo,
    )
    assert res.returncode == 1 and res.stdout == "" and res.stderr.count("\n") == 1
    assert "temporary directory" in res.stderr


def test_an_encrypted_private_key_that_the_agent_does_not_hold_fails_without_prompting(rig):
    path, fp = make_key(rig, "priv", "ed25519", "secret")
    rig.config("user.signingkey", str(path))
    assert_fails(rig.check(fp), fp, "unresolved", "git cannot sign")



def test_a_failure_is_one_line_and_leaks_no_private_key_material(rig):
    rig.config("user.signingkey", str(rig.b))
    body = [
        line for line in rig.b.read_text().splitlines() if line and not line.startswith("-----")
    ]
    pub_body = rig.pub(rig.b).split()[1]
    for res in (rig.check(rig.fp_a), rig.check(rig.fp_b + "x"), rig.check()):
        assert res.returncode != 0 and res.stdout == ""
        assert res.stderr.count("\n") == 1
        for secret in body:
            assert secret not in res.stdout + res.stderr
        assert pub_body not in res.stdout + res.stderr


def test_a_failure_names_no_path_outside_the_checkout_or_the_ssh_directory(rig):
    rig.config("user.signingkey", str(rig.root / "elsewhere" / "key.pub"))
    res = rig.check(rig.fp_a)
    assert res.returncode != 0
    assert str(rig.root) not in res.stderr


def test_success_never_prints_the_resolved_key(rig):
    rig.config("user.signingkey", str(rig.a))
    res = rig.check(rig.fp_a)
    assert (res.returncode, res.stdout, res.stderr) == (0, "", "")


def test_the_readme_documents_the_key_and_the_preflight():
    readme = (ROOT / "README.md").read_text()
    start = readme.index("### Commit signing key")
    body = readme[start : readme.index("\n### ", start + 1)]
    for needle in (
        "`git.signing_key`",
        "`git.signed_commits`",
        "bash <skill dir>/scripts/check-signing-key.sh <git.signing_key>",
        "When `git.signing_key` is unset",
    ):
        assert needle in body, needle


def test_the_script_is_a_bash_script_with_a_shebang_and_no_secrets_in_argv():
    text = SOURCE.read_text()
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -u" in text


# --- C2/C3: vendoring and the rule ---------------------------------------------------------


def receivers():
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import vendor_shared
    finally:
        sys.path.pop(0)
    return sorted(
        skill
        for skill, caps in MANIFEST["skills"].items()
        if "github" in vendor_shared.closure(vendor_shared.ALWAYS + caps)
    )


def test_thirteen_skills_receive_github_today():
    assert len(receivers()) == 13


def test_every_skill_that_receives_github_receives_the_script():
    for skill in receivers():
        assert "check-signing-key.sh" in MANIFEST["executables"].get(skill, []), skill
        assert (ROOT / "skills" / skill / "references" / "github.md").is_file()
        assert (ROOT / "skills" / skill / "scripts" / "check-signing-key.sh").is_file(), skill


def test_no_other_skill_receives_the_script():
    for skill, names in MANIFEST["executables"].items():
        if "check-signing-key.sh" in names:
            assert skill in receivers(), skill


def test_each_vendored_copy_is_the_header_plus_the_source_and_not_executable():
    header = (
        b"# GENERATED from shared/check-signing-key.sh by scripts/vendor_shared.py. "
        b"Edit the source, then rerun the script.\n"
    )
    for skill in receivers():
        copy_path = ROOT / "skills" / skill / "scripts" / "check-signing-key.sh"
        assert copy_path.read_bytes() == header + SOURCE.read_bytes(), skill
        assert not copy_path.stat().st_mode & 0o111, skill


def test_a_vendored_copy_behaves_like_the_source_when_run_through_bash(rig):
    rig.add(rig.a)
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    vendored = ROOT / "skills" / "engineering-workflow" / "scripts" / "check-signing-key.sh"
    assert_ok(rig.check(rig.fp_a, script=vendored))
    assert_fails(rig.check(rig.fp_b, script=vendored), rig.fp_b, rig.fp_a, "mismatch")


def commits_and_signing() -> list[str]:
    lines = GITHUB.read_text().splitlines()
    start = lines.index("## Commits and signing")
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
    return [line.strip() for line in lines[start:end]]


NEVER_SETS_SIGNINGKEY = (
    "- An agent never sets `user.signingkey` itself, by `git config` or otherwise; "
    "a read-only check (for example `git config --get user.signingkey`) is not a set."
)
OVERRIDE_PROHIBITION = (
    "- Never pass `-c user.signingkey`, `-c gpg.*` or `-c commit.gpgsign` "
    "to a commit-creating git command; rely on the configured signing."
)
# The SKL-206 restatement of the same override inside the briefs and rules of the skills.
OVERRIDE_RESTATEMENT = "never pass `-c user.signingkey`, `-c gpg.*` or `-c commit.gpgsign`"

RULE_SENTENCES = (
    "- When `profile.git.signing_key` is set, it is the OpenSSH SHA256 fingerprint of the key registered for signing.",
    "Before the first commit of a task, and again after any change to git config, run `bash <skill dir>/scripts/check-signing-key.sh <profile.git.signing_key>` from inside the target repository.",
    "A non-zero exit is a configuration fault, handled as the Always list below says.",
    "Never commit with a per-commit key override, and never fall back to another key.",
    NEVER_SETS_SIGNINGKEY,
    "- Check the result after push: `gh api repos/<owner>/<repo>/commits/<sha> --jq '.commit.verification'`.",
)


@pytest.mark.parametrize("sentence", RULE_SENTENCES)
def test_the_signing_rule_is_stated_in_shared_github(sentence):
    assert commits_and_signing().count(sentence) == 1


def test_the_rule_is_stated_once_and_nowhere_else():
    assert GITHUB.read_text().count("check-signing-key") == 1
    for path in [*(ROOT / "shared").glob("*.md"), *(ROOT / "skills").glob("*/SKILL.md")]:
        if path != GITHUB:
            assert "check-signing-key" not in path.read_text(), path


def signingkey_mentions() -> list[tuple[str, str]]:
    """Every line under shared/ and skills/ that names user.signingkey, as the AC's git grep."""
    found = []
    for base in (ROOT / "shared", ROOT / "skills"):
        for path in sorted(p for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
            data = path.read_bytes()
            if b"\0" in data:
                continue
            rel = path.relative_to(ROOT).as_posix()
            for line in data.decode("utf-8").splitlines():
                if re.search(r"user\.signingkey", line):
                    found.append((rel, line))
    return found


def signingkey_mention_kind(rel: str, line: str) -> str | None:
    """The one allowlisted kind a mention belongs to, or None for an unlisted mention."""
    github = rel == "shared/github.md" or re.fullmatch(r"skills/[^/]+/references/github\.md", rel)
    script = rel == "shared/check-signing-key.sh" or re.fullmatch(
        r"skills/[^/]+/scripts/check-signing-key\.sh", rel
    )
    if github and line == NEVER_SETS_SIGNINGKEY:
        return "a: the never-sets rule"
    if github and line == OVERRIDE_PROHIBITION:
        return "b: the override prohibition"
    if script and line.startswith("# user.signingkey"):
        return "c: the resolution-forms comment"
    if rel.startswith("skills/") and OVERRIDE_RESTATEMENT in line:
        return "d: the restated override"
    return None


def test_signingkey_mentions_are_allowlisted():
    mentions = signingkey_mentions()
    unlisted = [(rel, line) for rel, line in mentions if signingkey_mention_kind(rel, line) is None]
    assert unlisted == []
    assert not [rel for rel, line in mentions if "resolves" in line]
    per_file = {}
    for rel, line in mentions:
        kind = signingkey_mention_kind(rel, line)
        per_file[rel] = [*per_file.get(rel, []), kind]
    for skill in [None, *receivers()]:
        base = "shared" if skill is None else f"skills/{skill}"
        docs = f"{base}/github.md" if skill is None else f"{base}/references/github.md"
        script = f"{base}/check-signing-key.sh" if skill is None else f"{base}/scripts/check-signing-key.sh"
        assert per_file[docs].count("a: the never-sets rule") == 1, docs
        assert per_file[docs].count("b: the override prohibition") == 1, docs
        assert len(per_file[docs]) == 2, docs
        assert len(per_file[script]) == 1, script
