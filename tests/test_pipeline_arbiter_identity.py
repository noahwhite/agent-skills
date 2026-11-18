"""The arbitration report carries the arbiter's identity, and every accepted arbitration is retained.

SKL-178 (AC 6). When the script accepts an arbitrate phase, on `run` or on `record`, it writes
`ARBITER-AGENT: <name>`, `ARBITER-MODEL: <model id as given>` and `ARBITER-HEAD: <full HEAD SHA>`
directly after the unchanged first line `REVIEW-RAN: yes`, before it stamps the artifact. The name
comes from `--agent` (or `ADVERSARIAL_AGENT`, which `--agent` overrides); an absent agent or model is
written as `not-supplied`. It then publishes an immutable copy of the report, before stamping it, under
`<git common dir>/adversarial-pipeline/arbitration-rounds` as
`round-<UTC timestamp>-<full HEAD SHA>-<first 12 hex of the report sha256>-<n>.md` with a no-clobber
hard link, and prints the retained absolute path on stderr. A re-run's discard and `cleanup` never
remove a retained copy, and every worktree of the clone resolves the same directory.

Every test seeds a base commit and a head commit and reviews the head against its base, on both
flows: `run`, and `dossier` followed by `record`.
"""

import hashlib
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "adversarial-review-pipeline" / "scripts" / "run-adversarial-pipeline.sh"
BASE_REF = "base"
FLOWS = ("run", "dossier")
AGENT_NAME = "Mistral Large 4"
# A model id the progress label would rewrite (space, '&', quote): the header carries it verbatim.
MODEL_ID = "openrouter/mistralai/mistral large & 'x'"
REPORT_BODY = "arbitrate report\n"
FIXED_TS = "20260101T000000Z"
RETAINED_RE = re.compile(r"^round-(\d{8}T\d{6}Z)-([0-9a-f]{40})-([0-9a-f]{12})-([1-9][0-9]*)\.md$")

GIT_ISOLATION = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
GIT_LOCATORS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
                "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_EXTERNAL_DIFF",
                "GIT_DEFAULT_HASH", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT")


def isolated_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("ADVERSARIAL_", "GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))
           and k not in GIT_LOCATORS}
    return {**env, **GIT_ISOLATION}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, env=isolated_env(),
    ).stdout.strip()


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "agent-skills@example.com")
    git(repo, "config", "user.name", "agent-skills")
    git(repo, "config", "commit.gpgsign", "false")
    git(repo, "config", "tag.gpgsign", "false")
    for content, message in (("x = 1\n", "base"), ("x = 2\n", "head")):
        (repo / "app.py").write_text(content)
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", message)
        if message == "base":
            git(repo, "tag", BASE_REF)
    return repo


def run_script(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=120,
    )


def make_gate(tmp_path: Path, repo: Path, name: str = "gate") -> dict:
    home = tmp_path / name
    home.mkdir()
    scratch = home / "session-scratch"
    scratch.mkdir()
    (home / "runtime-tmp").mkdir()
    env = {**isolated_env(), "TMPDIR": str(home / "runtime-tmp")}
    spec = home / "spec.md"
    spec.write_text("Story SKL-178: arbiter identity header and retained arbitration reports.\n")
    g = {"repo": repo, "scratch": scratch, "env": env, "spec": spec, "home": home}
    preflight = run_script("preflight", "--full-suite", "on", "--repo", str(repo), "--base", BASE_REF, "--test-cmd", "true",
                           "--scratch", str(scratch), env=env)
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    return g


@pytest.fixture
def gate(tmp_path):
    return make_gate(tmp_path, make_repo(tmp_path))


def with_fixed_clock(g: dict) -> dict[str, str]:
    """An environment whose `date` prints one fixed UTC timestamp, so retained names are predictable."""
    shim = g["home"] / "bin"
    shim.mkdir(exist_ok=True)
    fake = shim / "date"
    fake.write_text(f"#!/bin/sh\necho {FIXED_TS}\n")
    fake.chmod(0o755)
    return {**g["env"], "PATH": f"{shim}{os.pathsep}{g['env']['PATH']}"}


def common(g: dict) -> list[str]:
    return ["--repo", str(g["repo"]), "--base", BASE_REF, "--spec", str(g["spec"]),
            "--scratch", str(g["scratch"])]


def artifact_paths(g: dict) -> dict[str, Path]:
    listed = run_script("paths", "--repo", str(g["repo"]), "--base", BASE_REF, env=g["env"])
    assert listed.returncode == 0, listed.stdout + listed.stderr
    return {name: Path(path) for name, _, path in
            (line.partition(" ") for line in listed.stdout.splitlines()) if path}


def line_value(text: str, prefix: str) -> str:
    lines = [line for line in text.splitlines() if line.startswith(prefix)]
    assert len(lines) == 1, f"expected exactly one {prefix!r} line, got {lines}"
    return lines[0][len(prefix):]


def agent_cmd(first_line: str = "REVIEW-RAN: yes") -> str:
    return f'printf "%s\\n%s" "{first_line}" "{REPORT_BODY}" > {{output_file}}'


def run_phase(g: dict, phase: str, *extra: str, env: dict[str, str] | None = None,
              first_line: str = "REVIEW-RAN: yes") -> subprocess.CompletedProcess:
    return run_script("run", phase, *common(g), "--agent-cmd", agent_cmd(first_line), *extra,
                      env=env or g["env"])


def cleanup(g: dict, checkout: Path) -> None:
    result = run_script("cleanup", str(checkout), "--repo", str(g["repo"]), env=g["env"])
    assert result.returncode == 0, result.stdout + result.stderr


def dossier_and_record(g: dict, phase: str, *extra: str, env: dict[str, str] | None = None,
                       first_line: str = "REVIEW-RAN: yes",
                       raw_report: str | None = None) -> subprocess.CompletedProcess:
    written = run_script("dossier", phase, *common(g), env=g["env"])
    assert written.returncode == 0, written.stdout + written.stderr
    report = raw_report if raw_report is not None else f"{first_line}\n{REPORT_BODY}"
    artifact_paths(g)[phase].write_bytes(report.encode())
    recorded = run_script("record", phase, "--repo", str(g["repo"]), "--base", BASE_REF,
                          "--spec", str(g["spec"]), *extra, env=env or g["env"])
    cleanup(g, Path(line_value(written.stderr, "CHECKOUT: ")))
    return recorded


def complete(g: dict, flow: str, phase: str, *extra: str, env: dict[str, str] | None = None,
             first_line: str = "REVIEW-RAN: yes") -> subprocess.CompletedProcess:
    if flow == "run":
        return run_phase(g, phase, *extra, env=env, first_line=first_line)
    return dossier_and_record(g, phase, *extra, env=env, first_line=first_line)


def ready_for_arbitration(g: dict, flow: str) -> None:
    for phase in ("sweep", "hunt"):
        result = complete(g, flow, phase)
        assert result.returncode == 0, result.stdout + result.stderr


def head_sha(g: dict) -> str:
    return git(g["repo"], "rev-parse", "HEAD")


def retention_dir(repo: Path) -> Path:
    common_dir = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    return common_dir / "adversarial-pipeline" / "arbitration-rounds"


def retained(repo: Path) -> list[Path]:
    d = retention_dir(repo)
    return sorted(d.iterdir()) if d.is_dir() else []


def retained_path_from(stderr: str) -> Path:
    return Path(line_value(stderr, "Retained arbitration report -> "))


def expected_report(agent: str, model: str, head: str) -> str:
    return (f"REVIEW-RAN: yes\nARBITER-AGENT: {agent}\nARBITER-MODEL: {model}\n"
            f"ARBITER-HEAD: {head}\n{REPORT_BODY}")


# --- the three identity lines ------------------------------------------------------------------------

@pytest.mark.parametrize("flow", FLOWS)
def test_identity_lines_follow_an_unchanged_first_line(gate, flow):
    ready_for_arbitration(gate, flow)
    result = complete(gate, flow, "arbitrate", "--agent", AGENT_NAME, "--model", MODEL_ID)
    assert result.returncode == 0, result.stdout + result.stderr
    artifact = artifact_paths(gate)["arbitrate"]
    report = artifact.read_text()
    assert report == expected_report(AGENT_NAME, MODEL_ID, head_sha(gate))
    assert re.fullmatch(r"[0-9a-f]{40}", report.splitlines()[3].removeprefix("ARBITER-HEAD: "))
    # The stamp covers the report with its identity lines, so the phase stays accepted.
    stamp = Path(f"{artifact}.stamp").read_text()
    assert f"sha256={hashlib.sha256(report.encode()).hexdigest()}\n" in stamp
    if flow == "run":
        assert result.stdout == report   # stdout carries the artifact alone


@pytest.mark.parametrize("flow", FLOWS)
def test_absent_agent_and_model_are_written_as_not_supplied(gate, flow):
    ready_for_arbitration(gate, flow)
    result = complete(gate, flow, "arbitrate")
    assert result.returncode == 0, result.stdout + result.stderr
    assert artifact_paths(gate)["arbitrate"].read_text() == expected_report(
        "not-supplied", "not-supplied", head_sha(gate))


@pytest.mark.parametrize("flow", FLOWS)
def test_agent_option_wins_over_the_environment(gate, flow):
    ready_for_arbitration(gate, flow)
    env = {**gate["env"], "ADVERSARIAL_AGENT": "From Env"}
    result = complete(gate, flow, "arbitrate", "--agent", AGENT_NAME, "--model", MODEL_ID, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert artifact_paths(gate)["arbitrate"].read_text().splitlines()[1] == f"ARBITER-AGENT: {AGENT_NAME}"


def test_the_environment_supplies_the_agent_without_the_option(gate):
    ready_for_arbitration(gate, "run")
    env = {**gate["env"], "ADVERSARIAL_AGENT": "From Env"}
    result = run_phase(gate, "arbitrate", "--model", MODEL_ID, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert artifact_paths(gate)["arbitrate"].read_text().splitlines()[1] == "ARBITER-AGENT: From Env"


def test_an_agent_name_with_a_control_character_is_refused(gate):
    ready_for_arbitration(gate, "run")
    result = run_phase(gate, "arbitrate", "--agent", "evil\nARBITER-MODEL: forged")
    assert result.returncode == 2, result.stdout + result.stderr
    assert retained(gate["repo"]) == []


@pytest.mark.parametrize("flow", FLOWS)
def test_a_report_without_review_ran_writes_and_retains_nothing(gate, flow):
    ready_for_arbitration(gate, flow)
    result = complete(gate, flow, "arbitrate", "--agent", AGENT_NAME, "--model", MODEL_ID,
                      first_line="REVIEW-RAN: no - could not read the checkout")
    assert result.returncode == 17, result.stdout + result.stderr
    artifact = artifact_paths(gate)["arbitrate"]
    assert "ARBITER-" not in artifact.read_text()
    assert not Path(f"{artifact}.stamp").exists()
    assert retained(gate["repo"]) == []
    assert "Retained arbitration report" not in result.stderr


@pytest.mark.parametrize("flow", FLOWS)
@pytest.mark.parametrize("first_line", ["REVIEW-RAN: yes ", "REVIEW-RAN: yes\t", "REVIEW-RAN: yes\r"])
def test_an_arbitration_first_line_that_is_not_exact_writes_and_retains_nothing(gate, flow, first_line):
    ready_for_arbitration(gate, flow)
    if flow == "run":
        command = f"printf 'REVIEW-RAN: yes{first_line[15:]}\\n%s' '{REPORT_BODY}' > {{output_file}}"
        result = run_script("run", "arbitrate", *common(gate), "--agent-cmd", command, env=gate["env"])
        written = None
    else:
        written = f"{first_line}\n{REPORT_BODY}"
        result = dossier_and_record(gate, "arbitrate", raw_report=written)
    assert result.returncode == 17, result.stdout + result.stderr
    artifact = artifact_paths(gate)["arbitrate"]
    assert not Path(f"{artifact}.stamp").exists()
    assert retained(gate["repo"]) == []
    if written is not None:
        assert artifact.read_bytes() == written.encode()


@pytest.mark.parametrize("flow", FLOWS)
def test_other_phases_get_no_identity_lines_and_no_retained_copy(gate, flow):
    ready_for_arbitration(gate, flow)
    for phase in ("sweep", "hunt"):
        assert "ARBITER-" not in artifact_paths(gate)[phase].read_text()
    assert retained(gate["repo"]) == []


# --- retention -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("flow", FLOWS)
def test_stderr_names_the_retained_copy_of_the_stamped_report(gate, flow):
    ready_for_arbitration(gate, flow)
    result = complete(gate, flow, "arbitrate", "--agent", AGENT_NAME, "--model", MODEL_ID)
    assert result.returncode == 0, result.stdout + result.stderr
    path = retained_path_from(result.stderr)
    assert path.is_absolute()
    assert path.parent == retention_dir(gate["repo"])
    assert retained(gate["repo"]) == [path]
    report = artifact_paths(gate)["arbitrate"].read_text()
    assert path.read_text() == report
    match = RETAINED_RE.match(path.name)
    assert match, path.name
    assert match.group(2) == head_sha(gate)
    assert match.group(3) == hashlib.sha256(report.encode()).hexdigest()[:12]
    assert match.group(4) == "1"
    assert not stat.S_IMODE(path.stat().st_mode) & 0o222, "the retained copy is read-only"
    assert str(path) not in result.stdout


@pytest.mark.parametrize("flow", FLOWS)
def test_two_byte_identical_arbitrations_at_one_head_leave_two_retained_files(gate, flow):
    ready_for_arbitration(gate, flow)
    env = with_fixed_clock(gate)
    first = complete(gate, flow, "arbitrate", "--agent", AGENT_NAME, "--model", MODEL_ID, env=env)
    assert first.returncode == 0, first.stdout + first.stderr
    second = complete(gate, flow, "arbitrate", "--agent", AGENT_NAME, "--model", MODEL_ID, env=env)
    assert second.returncode == 0, second.stdout + second.stderr
    one, two = retained_path_from(first.stderr), retained_path_from(second.stderr)
    assert one != two
    assert retained(gate["repo"]) == sorted([one, two])
    assert one.read_bytes() == two.read_bytes()
    assert [RETAINED_RE.match(p.name).group(4) for p in (one, two)] == ["1", "2"]
    assert {RETAINED_RE.match(p.name).group(1) for p in (one, two)} == {FIXED_TS}


def test_an_existing_round_file_is_never_overwritten(gate):
    ready_for_arbitration(gate, "run")
    env = with_fixed_clock(gate)
    report = expected_report(AGENT_NAME, MODEL_ID, head_sha(gate))
    sha12 = hashlib.sha256(report.encode()).hexdigest()[:12]
    d = retention_dir(gate["repo"])
    d.mkdir(parents=True)
    squatter = d / f"round-{FIXED_TS}-{head_sha(gate)}-{sha12}-1.md"
    squatter.write_text("an earlier round\n")
    result = run_phase(gate, "arbitrate", "--agent", AGENT_NAME, "--model", MODEL_ID, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert squatter.read_text() == "an earlier round\n"
    path = retained_path_from(result.stderr)
    assert path.name == f"round-{FIXED_TS}-{head_sha(gate)}-{sha12}-2.md"
    assert path.read_text() == report
    assert sorted(p.name for p in d.iterdir()) == sorted([squatter.name, path.name]), "no temporary file is left"


@pytest.mark.parametrize("flow", FLOWS)
def test_a_retention_failure_fails_the_phase_and_accepts_nothing(gate, flow):
    if os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")
    ready_for_arbitration(gate, flow)
    d = retention_dir(gate["repo"])
    d.mkdir(parents=True)
    d.chmod(0o555)
    try:
        result = complete(gate, flow, "arbitrate", "--agent", AGENT_NAME, "--model", MODEL_ID)
    finally:
        d.chmod(0o755)
    assert result.returncode != 0, result.stdout + result.stderr
    artifact = artifact_paths(gate)["arbitrate"]
    assert not Path(f"{artifact}.stamp").exists()
    assert list(d.iterdir()) == []
    assert "Retained arbitration report" not in result.stderr
    if flow == "dossier":
        # The report is restored as the subagent wrote it, so a retried record is not double-headed.
        assert artifact.read_text() == f"REVIEW-RAN: yes\n{REPORT_BODY}"
        retry = run_script("record", "arbitrate", "--repo", str(gate["repo"]), "--base", BASE_REF,
                           "--spec", str(gate["spec"]), "--agent", AGENT_NAME, "--model", MODEL_ID,
                           env=gate["env"])
        assert retry.returncode == 0, retry.stdout + retry.stderr
        assert artifact.read_text() == expected_report(AGENT_NAME, MODEL_ID, head_sha(gate))
    else:
        assert result.stdout == ""


@pytest.mark.parametrize("flow", FLOWS)
def test_a_rerun_discard_and_cleanup_keep_the_retained_copy(gate, flow):
    ready_for_arbitration(gate, flow)
    first = complete(gate, flow, "arbitrate", "--agent", AGENT_NAME, "--model", MODEL_ID)
    assert first.returncode == 0, first.stdout + first.stderr
    kept = retained_path_from(first.stderr)
    content = kept.read_bytes()
    # A re-run of the hunt discards the accepted arbitration (begin_phase / invalidate_downstream).
    rerun = complete(gate, flow, "hunt")
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr
    assert not artifact_paths(gate)["arbitrate"].exists()
    assert kept.read_bytes() == content
    # A re-run of arbitrate itself discards phase3-arbitration.md before it launches.
    again = run_script("dossier", "arbitrate", *common(gate), env=gate["env"])
    assert again.returncode == 0, again.stdout + again.stderr
    assert not artifact_paths(gate)["arbitrate"].exists()
    cleanup(gate, Path(line_value(again.stderr, "CHECKOUT: ")))
    assert kept.read_bytes() == content
    assert retained(gate["repo"]) == [kept]


def test_recording_an_accepted_arbitration_again_fails_and_retains_nothing_more(gate):
    ready_for_arbitration(gate, "dossier")
    first = dossier_and_record(gate, "arbitrate", "--agent", AGENT_NAME, "--model", MODEL_ID)
    assert first.returncode == 0, first.stdout + first.stderr
    artifact = artifact_paths(gate)["arbitrate"]
    accepted_report = artifact.read_bytes()
    kept = retained(gate["repo"])
    again = run_script("record", "arbitrate", "--repo", str(gate["repo"]), "--base", BASE_REF,
                       "--spec", str(gate["spec"]), "--agent", "Other Agent", "--model", "other/model",
                       env=gate["env"])
    assert again.returncode == 15, again.stdout + again.stderr
    assert artifact.read_bytes() == accepted_report
    assert Path(f"{artifact}.stamp").exists(), "the earlier acceptance stands"
    assert retained(gate["repo"]) == kept
    assert "Retained arbitration report" not in again.stderr


# The record process runs as a session leader, so its PID is the session id a shim reads from /proc.
SIGNAL_TARGETS = {
    "group": "kill -TERM 0",
    "record-pid": "kill -TERM \"$(cut -d' ' -f6 /proc/$$/stat)\"",
}


def signalling_shim(g: dict, command: str, target: str, args: str = "") -> dict[str, str]:
    """An environment whose `command` sends TERM once (to the target), then runs the real command.

    With `args`, only a call whose arguments contain that text sends it.
    """
    shim = g["home"] / "signal-bin"
    shim.mkdir(exist_ok=True)
    real = shutil.which(command, path=g["env"]["PATH"])
    marker = g["home"] / f"signalled-{command}"
    (shim / command).write_text(
        f"#!/bin/sh\ncase \"$*\" in *'{args}'*)\n"
        f"  if [ ! -e '{marker}' ]; then : > '{marker}'; {SIGNAL_TARGETS[target]}; fi ;;\nesac\n"
        f"exec '{real}' \"$@\"\n")
    (shim / command).chmod(0o755)
    return {**g["env"], "PATH": f"{shim}{os.pathsep}{g['env']['PATH']}"}


def record_arbitration_in_own_session(g: dict, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), "record", "arbitrate", "--repo", str(g["repo"]), "--base", BASE_REF,
         "--spec", str(g["spec"]), "--agent", AGENT_NAME, "--model", MODEL_ID],
        capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=120, start_new_session=True)


@pytest.mark.parametrize("target", sorted(SIGNAL_TARGETS))
def test_a_signal_before_publishing_rolls_the_arbitration_back(gate, target):
    ready_for_arbitration(gate, "dossier")
    written = run_script("dossier", "arbitrate", *common(gate), env=gate["env"])
    assert written.returncode == 0, written.stdout + written.stderr
    artifact = artifact_paths(gate)["arbitrate"]
    report = f"REVIEW-RAN: yes\n{REPORT_BODY}".encode()
    artifact.write_bytes(report)
    # `tail` runs only while the identity lines are being written, before anything is published.
    interrupted = record_arbitration_in_own_session(gate, signalling_shim(gate, "tail", target))
    assert interrupted.returncode == 143, interrupted.stdout + interrupted.stderr
    assert "this phase is not accepted" in interrupted.stderr
    assert not Path(f"{artifact}.stamp").exists()
    assert artifact.read_bytes() == report
    assert retained(gate["repo"]) == []
    retry = record_arbitration_in_own_session(gate, gate["env"])
    assert retry.returncode == 0, retry.stdout + retry.stderr
    assert artifact.read_text() == expected_report(AGENT_NAME, MODEL_ID, head_sha(gate))
    cleanup(gate, Path(line_value(written.stderr, "CHECKOUT: ")))


@pytest.mark.parametrize("target", sorted(SIGNAL_TARGETS))
def test_a_signal_while_publishing_lets_the_copy_and_the_stamp_land_together(gate, target):
    ready_for_arbitration(gate, "dossier")
    written = run_script("dossier", "arbitrate", *common(gate), env=gate["env"])
    assert written.returncode == 0, written.stdout + written.stderr
    artifact = artifact_paths(gate)["arbitrate"]
    artifact.write_bytes(f"REVIEW-RAN: yes\n{REPORT_BODY}".encode())
    # `ln` publishes the retained copy.
    result = record_arbitration_in_own_session(gate, signalling_shim(gate, "ln", target))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "it stays accepted" in result.stderr
    report = artifact.read_text()
    assert report == expected_report(AGENT_NAME, MODEL_ID, head_sha(gate))
    stamp = Path(f"{artifact}.stamp").read_text()
    assert f"sha256={hashlib.sha256(report.encode()).hexdigest()}\n" in stamp
    assert retained(gate["repo"]) == [retained_path_from(result.stderr)]
    cleanup(gate, Path(line_value(written.stderr, "CHECKOUT: ")))


@pytest.mark.parametrize("target", sorted(SIGNAL_TARGETS))
def test_a_signal_after_the_stamp_lands_keeps_the_phase_accepted(gate, target):
    ready_for_arbitration(gate, "dossier")
    written = run_script("dossier", "arbitrate", *common(gate), env=gate["env"])
    assert written.returncode == 0, written.stdout + written.stderr
    artifact = artifact_paths(gate)["arbitrate"]
    artifact.write_bytes(f"REVIEW-RAN: yes\n{REPORT_BODY}".encode())
    # This `rm` clears the transaction files after the copy and the stamp have both landed.
    shimmed = signalling_shim(gate, "rm", target, args="arbitrate-original.")
    result = record_arbitration_in_own_session(gate, shimmed)
    assert (gate["home"] / "signalled-rm").exists()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "it stays accepted" in result.stderr
    report = artifact.read_text()
    assert report == expected_report(AGENT_NAME, MODEL_ID, head_sha(gate))
    stamp = Path(f"{artifact}.stamp").read_text()
    assert f"sha256={hashlib.sha256(report.encode()).hexdigest()}\n" in stamp
    assert retained(gate["repo"]) == [retained_path_from(result.stderr)]
    cleanup(gate, Path(line_value(written.stderr, "CHECKOUT: ")))


@pytest.mark.parametrize("target", sorted(SIGNAL_TARGETS))
def test_a_signal_after_run_accepts_the_arbitration_keeps_it_accepted(gate, target):
    ready_for_arbitration(gate, "run")
    # This `rm` runs in `run` itself, after the acceptance child has returned.
    shimmed = signalling_shim(gate, "rm", target, args="accept-reason.")
    result = subprocess.run(
        ["bash", str(SCRIPT), "run", "arbitrate", *common(gate), "--agent-cmd", agent_cmd("REVIEW-RAN: yes"),
         "--agent", AGENT_NAME, "--model", MODEL_ID],
        capture_output=True, text=True, env=shimmed, cwd=str(ROOT), timeout=120, start_new_session=True)
    assert (gate["home"] / "signalled-rm").exists()
    assert result.returncode == 143, result.stdout + result.stderr
    assert "after the phase was accepted; it stays accepted" in result.stderr
    assert "this phase is not accepted" not in result.stderr
    artifact = artifact_paths(gate)["arbitrate"]
    report = artifact.read_text()
    assert report.startswith(f"REVIEW-RAN: yes\nARBITER-AGENT: {AGENT_NAME}\n")
    stamp = Path(f"{artifact}.stamp").read_text()
    assert f"sha256={hashlib.sha256(report.encode()).hexdigest()}\n" in stamp
    assert retained(gate["repo"]) == [retained_path_from(result.stderr)]


def test_a_stamp_that_cannot_land_removes_the_copy_published_for_it(gate):
    ready_for_arbitration(gate, "dossier")
    written = run_script("dossier", "arbitrate", *common(gate), env=gate["env"])
    assert written.returncode == 0, written.stdout + written.stderr
    artifact = artifact_paths(gate)["arbitrate"]
    report = f"REVIEW-RAN: yes\n{REPORT_BODY}".encode()
    artifact.write_bytes(report)
    # A directory at the stamp path: the stamp cannot be put in place there.
    blocker = Path(f"{artifact}.stamp")
    blocker.mkdir()
    failed = record_arbitration_in_own_session(gate, gate["env"])
    assert failed.returncode == 21, failed.stdout + failed.stderr
    assert "Retained arbitration report" not in failed.stderr
    assert blocker.is_dir() and list(blocker.iterdir()) == []
    assert artifact.read_bytes() == report
    assert retained(gate["repo"]) == []
    blocker.rmdir()
    retry = record_arbitration_in_own_session(gate, gate["env"])
    assert retry.returncode == 0, retry.stdout + retry.stderr
    assert retained(gate["repo"]) == [retained_path_from(retry.stderr)]
    cleanup(gate, Path(line_value(written.stderr, "CHECKOUT: ")))


def test_a_nul_byte_in_the_first_line_writes_and_retains_nothing(gate):
    ready_for_arbitration(gate, "dossier")
    written = f"REVIEW-RAN: ye\0s\n{REPORT_BODY}"
    result = dossier_and_record(gate, "arbitrate", raw_report=written)
    assert result.returncode == 17, result.stdout + result.stderr
    artifact = artifact_paths(gate)["arbitrate"]
    assert artifact.read_bytes() == written.encode()
    assert not Path(f"{artifact}.stamp").exists()
    assert retained(gate["repo"]) == []


def test_a_clone_path_with_a_backslash_keeps_the_documented_filename(tmp_path):
    parent = tmp_path / "back\\slash"
    parent.mkdir()
    g = make_gate(tmp_path, make_repo(parent))
    # The dossier flow: the reports are written from Python, so no test shell command re-reads the path.
    ready_for_arbitration(g, "dossier")
    result = dossier_and_record(g, "arbitrate", "--agent", AGENT_NAME, "--model", MODEL_ID)
    assert result.returncode == 0, result.stdout + result.stderr
    path = retained_path_from(result.stderr)
    match = RETAINED_RE.match(path.name)
    assert match, path.name
    report = artifact_paths(g)["arbitrate"].read_bytes()
    assert match.group(3) == hashlib.sha256(report).hexdigest()[:12]


def test_every_worktree_of_the_clone_resolves_the_same_directory(gate, tmp_path):
    ready_for_arbitration(gate, "run")
    first = run_phase(gate, "arbitrate", "--agent", AGENT_NAME, "--model", MODEL_ID)
    assert first.returncode == 0, first.stdout + first.stderr
    linked = tmp_path / "linked"
    git(gate["repo"], "worktree", "add", "-q", "--detach", str(linked), "HEAD")
    other = make_gate(tmp_path, linked, name="linked-gate")
    ready_for_arbitration(other, "run")
    second = run_phase(other, "arbitrate", "--agent", AGENT_NAME, "--model", MODEL_ID)
    assert second.returncode == 0, second.stdout + second.stderr
    one, two = retained_path_from(first.stderr), retained_path_from(second.stderr)
    assert one != two
    assert retained(gate["repo"]) == sorted([one, two])
    assert one.parent == two.parent == retention_dir(gate["repo"]) == retention_dir(linked)
    # The linked worktree's own git-path is elsewhere, and removing the worktree keeps both copies.
    assert Path(git(linked, "rev-parse", "--path-format=absolute", "--git-path",
                    "adversarial-pipeline")) != retention_dir(gate["repo"]).parent
    git(gate["repo"], "worktree", "remove", "--force", str(linked))
    assert one.exists() and two.exists()


# --- docs pin the contract -----------------------------------------------------------------------------

SKILL_MD = ROOT / "skills" / "adversarial-review-pipeline" / "SKILL.md"


def header_text() -> str:
    lines = []
    for line in SCRIPT.read_text().splitlines()[1:]:
        if not line.startswith("#"):
            break
        lines.append(line)
    return "\n".join(lines)


@pytest.mark.parametrize("doc", ["skill", "header"])
def test_the_docs_state_the_identity_and_retention_contract(doc):
    text = " ".join((SKILL_MD.read_text() if doc == "skill" else header_text()).replace("#", " ").split())
    for needle in ("ARBITER-AGENT: <name>", "ARBITER-MODEL: <model id", "ARBITER-HEAD: <full HEAD SHA>",
                   "not-supplied", "adversarial-pipeline/arbitration-rounds",
                   "git rev-parse --path-format=absolute --git-common-dir",
                   "round-<UTC timestamp>-<full HEAD SHA>-<first 12 hex of the report sha256>-<n>.md",
                   "Retained arbitration report -> <path>", "--agent NAME", "ADVERSARIAL_AGENT"):
        assert needle in text, needle
    assert re.search(r"--agent\b[^.]*\bwins\b[^.]*ADVERSARIAL_AGENT", text), "--agent precedence"
    if doc == "skill":
        assert re.search(r"`record arbitrate` must run at the reviewed head", text)
