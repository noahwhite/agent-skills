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
    assert reason in res.stderr, res.stderr


SCRIPTS = [pytest.param(SOURCE, id="source")]


def test_a_matching_key_literal_passes(rig):
    rig.add(rig.a)
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    assert_ok(rig.check(rig.fp_a))


def test_a_matching_ssh_literal_passes(rig):
    rig.add(rig.a)
    rig.config("user.signingkey", rig.pub(rig.a))
    assert_ok(rig.check(rig.fp_a))


def test_a_matching_public_key_file_passes(rig):
    rig.add(rig.a)
    rig.config("user.signingkey", str(rig.a) + ".pub")
    assert_ok(rig.check(rig.fp_a))


def test_a_public_key_path_under_the_home_tilde_passes(rig):
    rig.add(rig.a)
    rig.config("user.signingkey", "~/.ssh/registered.pub")
    assert_ok(rig.check(rig.fp_a))


def test_a_matching_private_key_file_passes_without_the_agent(rig):
    rig.config("user.signingkey", str(rig.a))
    assert_ok(rig.check(rig.fp_a))


def test_a_matching_default_key_command_passes(rig):
    rig.add(rig.a)
    rig.config("gpg.ssh.defaultKeyCommand", f"printf 'key::%s\\n' \"$(cat {rig.a}.pub)\"")
    assert_ok(rig.check(rig.fp_a))


def test_only_the_first_line_of_the_command_output_counts(rig):
    rig.add(rig.a)
    rig.add(rig.b)
    rig.config(
        "gpg.ssh.defaultKeyCommand",
        f"printf 'key::%s\\nkey::%s\\n' \"$(cat {rig.a}.pub)\" \"$(cat {rig.b}.pub)\"",
    )
    assert_ok(rig.check(rig.fp_a))
    res = rig.check(rig.fp_b)
    assert_fails(res, rig.fp_b, rig.fp_a, "mismatch")


@pytest.mark.parametrize("form", ["literal", "file", "private"])
def test_a_different_key_fails_for_every_signingkey_form(rig, form):
    rig.add(rig.a)
    rig.add(rig.b)
    rig.config(
        "user.signingkey",
        {"literal": "key::" + rig.pub(rig.b), "file": str(rig.b) + ".pub", "private": str(rig.b)}[form],
    )
    assert_fails(rig.check(rig.fp_a), rig.fp_a, rig.fp_b, "mismatch")


def test_a_different_key_fails_through_the_default_key_command(rig):
    rig.add(rig.a)
    rig.add(rig.b)
    rig.config("gpg.ssh.defaultKeyCommand", f"printf 'key::%s\\n' \"$(cat {rig.b}.pub)\"")
    assert_fails(rig.check(rig.fp_a), rig.fp_a, rig.fp_b, "mismatch")


def test_no_resolvable_key_fails(rig):
    rig.add(rig.a)
    assert_fails(rig.check(rig.fp_a), rig.fp_a, "unresolved", "no signing key")


@pytest.mark.parametrize("value", ["", str("/nonexistent/key.pub"), "key::not a key", "key::"])
def test_an_unresolvable_signingkey_fails_without_falling_back(rig, value):
    rig.add(rig.a)
    rig.config("gpg.ssh.defaultKeyCommand", f"printf 'key::%s\\n' \"$(cat {rig.a}.pub)\"")
    rig.config("user.signingkey", value)
    assert_fails(rig.check(rig.fp_a), rig.fp_a, "unresolved", "user.signingkey")


def test_a_directory_as_signingkey_fails(rig):
    rig.config("user.signingkey", str(rig.root))
    assert_fails(rig.check(rig.fp_a), rig.fp_a, "unresolved", "user.signingkey")


@pytest.mark.parametrize("fmt", ["openpgp", "x509", None])
def test_a_gpg_format_other_than_ssh_fails(rig, fmt):
    rig.add(rig.a)
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    if fmt is None:
        rig.git("config", "--global", "--unset", "gpg.format")
    else:
        rig.config("gpg.format", fmt)
    assert_fails(rig.check(rig.fp_a), rig.fp_a, "unresolved", "gpg.format")


@pytest.mark.parametrize("form", ["literal", "file", "command"])
def test_a_public_key_that_is_not_loaded_in_the_agent_fails(rig, form):
    rig.add(rig.b)
    if form == "command":
        rig.config("gpg.ssh.defaultKeyCommand", f"printf 'key::%s\\n' \"$(cat {rig.a}.pub)\"")
    else:
        rig.config("user.signingkey", "key::" + rig.pub(rig.a) if form == "literal" else str(rig.a) + ".pub")
    assert_fails(rig.check(rig.fp_a), rig.fp_a, rig.fp_a, "agent")


def test_an_unreachable_agent_fails_for_a_public_key(rig):
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    rig.env["SSH_AUTH_SOCK"] = str(rig.root / "no-such.sock")
    assert_fails(rig.check(rig.fp_a), rig.fp_a, rig.fp_a, "agent")
    del rig.env["SSH_AUTH_SOCK"]
    assert_fails(rig.check(rig.fp_a), rig.fp_a, rig.fp_a, "agent")


@pytest.mark.parametrize(
    "command",
    [
        "true",
        "printf '\\n'",
        "printf 'ssh-ed25519 AAAA\\n'",
        "printf 'KEY::x\\n'",
        "printf 'key::garbage\\n'",
        "printf '\\nkey::x\\n'",
        "printf 'key::x\\n'; exit 3",
    ],
    ids=["empty", "blank", "no-prefix", "case", "garbage-key", "leading-blank", "command-fails"],
)
def test_malformed_default_key_command_output_fails(rig, command):
    rig.add(rig.a)
    rig.config("gpg.ssh.defaultKeyCommand", command)
    assert_fails(rig.check(rig.fp_a), rig.fp_a, "unresolved", "defaultKeyCommand")


def test_the_signingkey_wins_over_the_default_key_command(rig):
    rig.add(rig.a)
    rig.add(rig.b)
    rig.config("user.signingkey", "key::" + rig.pub(rig.b))
    rig.config("gpg.ssh.defaultKeyCommand", f"printf 'key::%s\\n' \"$(cat {rig.a}.pub)\"")
    assert_fails(rig.check(rig.fp_a), rig.fp_a, rig.fp_b, "mismatch")


@pytest.mark.parametrize(
    "args",
    [
        [],
        [""],
        [" "],
        ["SHA256:"],
        ["MD5:aa:bb"],
        [VALID[:-1]],
        [VALID + "="],
        [" " + VALID],
        [VALID + "\n"],
        [VALID, VALID],
        ["key::ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIM9Y6g9Uw8IqP8Nfc4LVcKV9FYjoxoP8"],
    ],
    ids=["none", "empty", "space", "prefix", "md5", "short", "padded", "leading", "newline", "two", "key-material"],
)
def test_a_malformed_argument_fails(rig, args):
    rig.add(rig.a)
    rig.config("user.signingkey", "key::" + rig.pub(rig.a))
    res = rig.check(*args)
    assert res.returncode != 0
    assert res.stdout == ""
    assert res.stderr.count("\n") == 1 and res.stderr.endswith("\n")
    assert "argument" in res.stderr
    # The line never echoes the argument back: it could be key material.
    for arg in args:
        assert not arg.strip() or arg.strip() not in res.stderr


def test_a_failure_is_one_line_and_leaks_no_private_key_material(rig):
    rig.config("user.signingkey", str(rig.b))
    body = [
        line for line in rig.b.read_text().splitlines() if line and not line.startswith("-----")
    ]
    pub_body = rig.pub(rig.b).split()[1]
    for res in (rig.check(rig.fp_a), rig.check(rig.fp_b + "x"), rig.check()):
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


RULE_SENTENCES = (
    "- When `profile.git.signing_key` is set, it is the OpenSSH SHA256 fingerprint of the key registered for signing.",
    "Before the first commit of a task, and again after any change to git config, run `bash <skill dir>/scripts/check-signing-key.sh <profile.git.signing_key>` from inside the target repository.",
    "On a non-zero exit, stop and fix the configuration.",
    "Never commit with a per-commit key override, and never fall back to another key.",
    "- When `profile.git.signing_key` is unset, confirm `user.signingkey` resolves to that key before committing.",
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
