"""A gate phase that cannot run is failed fast, and its failure is diagnosable.

SKL-20. The pipeline script takes the model id it was given (`--model`), can check that model's
availability before spending any agent budget (`--probe-cmd` under its own `--probe-timeout`),
runs the agent under one SIGKILL deadline of its whole process group, shows progress on stderr
without touching the artifact, and prints the streams it can see when a phase fails.

Every test drives `run` (or `record`) with fake agent and probe commands in a throwaway
repository, following tests/test_pipeline_scratch.py.
"""

import os
import re
import shlex
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "adversarial-review-pipeline" / "scripts" / "run-adversarial-pipeline.sh"


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "agent-skills@example.com"],
        ["git", "config", "user.name", "agent-skills"],
    ):
        subprocess.run(command, cwd=repo, check=True, capture_output=True)
    (repo / "tracked.txt").write_text("one\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True, capture_output=True)
    return repo


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """The test's own environment: the gate's ADVERSARIAL_* variables must never leak in."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("ADVERSARIAL_")}
    return {**env, **(extra or {})}


def run_script(*args: str, env: dict[str, str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=timeout,
    )


@pytest.fixture
def gate(tmp_path):
    """A throwaway repository with an accepted preflight, plus the session scratch directory."""
    repo = make_repo(tmp_path)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    runtime_tmp = tmp_path / "runtime-tmp"
    runtime_tmp.mkdir()
    env = clean_env({"TMPDIR": str(runtime_tmp)})
    preflight = run_script(
        "preflight", "--repo", str(repo), "--base", "HEAD", "--test-cmd", "true",
        "--scratch", str(scratch), env=env,
    )
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    return repo, scratch, env


def artifacts(repo: Path, env: dict[str, str]) -> dict[str, Path]:
    listed = run_script("paths", "--repo", str(repo), "--base", "HEAD", env=env)
    assert listed.returncode == 0, listed.stdout + listed.stderr
    out = {}
    for line in listed.stdout.splitlines():
        name, _, path = line.partition(" ")
        if path:
            out[name] = Path(path)
    return out


def assert_not_stamped(paths: dict[str, Path], phase: str) -> None:
    """A failed phase never stamps an artifact: acceptance binds it to the run and the spec."""
    stamp = Path(f"{paths[phase]}.stamp")
    assert not stamp.exists(), f"the failed {phase} phase stamped its artifact: {stamp}"


def assert_no_artifact(paths: dict[str, Path], phase: str) -> None:
    """A phase that fails before its agent runs writes no artifact at all."""
    assert not paths[phase].exists(), f"{phase} wrote an artifact it must not have written"
    assert_not_stamped(paths, phase)


SWEEP_AGENT = '{ printf "REVIEW-RAN: yes\\nsweep ok\\n"; } > {output_file}'


def run_sweep(repo: Path, scratch: Path, env: dict[str, str], *extra: str,
              agent: str = SWEEP_AGENT, timeout: int = 120) -> subprocess.CompletedProcess:
    return run_script(
        "run", "sweep", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--agent-cmd", agent, *extra, env=env, timeout=timeout,
    )


# --- AC1: the phase names its model and can check availability before it launches -----------------

def test_no_probe_is_recorded_as_not_configured_rather_than_silently_skipped(gate):
    repo, scratch, env = gate
    result = run_sweep(repo, scratch, env, "--model", "deepseek/deepseek-flash")
    assert result.returncode == 0, result.stdout + result.stderr
    launch = [line for line in result.stderr.splitlines() if "phase=sweep" in line and "model=" in line]
    assert launch, result.stderr
    assert any("deepseek/deepseek-flash" in line for line in launch), launch
    assert "availability check: not configured" in result.stderr, result.stderr


def test_a_passing_probe_runs_in_a_fresh_empty_directory_outside_the_checkout(gate, tmp_path):
    repo, scratch, env = gate
    observed = tmp_path / "probe-observed.txt"
    probe = (
        f'{{ pwd; printf "entries=%s\\n" "$(ls -A | wc -l)"; '
        f'printf "stdin=%s\\n" "$(readlink /proc/self/fd/0 2>/dev/null || echo unknown)"; '
        f'[ -e .git ] && echo in-checkout; true; }} > {shlex.quote(str(observed))}'
    )
    result = run_sweep(
        repo, scratch, env, "--model", "deepseek/deepseek-flash", "--probe-cmd", probe,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    lines = observed.read_text().splitlines()
    cwd = Path(lines[0])
    assert scratch in cwd.parents, f"the probe did not run under the run scratch directory: {cwd}"
    assert repo not in cwd.parents, f"the probe ran inside the checkout under review: {cwd}"
    assert cwd.name.startswith("probe."), cwd
    assert cwd.parent.name.startswith("run."), f"the probe ran outside the run directory: {cwd}"
    assert lines[1] == "entries=0", f"the probe directory was not fresh and empty: {lines}"
    assert lines[2] in ("stdin=/dev/null", "stdin=unknown"), f"the probe's stdin was not /dev/null: {lines}"
    assert "in-checkout" not in lines, lines
    assert "availability check: probe ok" in result.stderr, result.stderr


def test_a_probe_that_exits_non_zero_fails_the_phase_before_the_agent_runs(gate, tmp_path):
    repo, scratch, env = gate
    ran = tmp_path / "agent-ran.txt"
    probe = (
        "echo 'AI_APICallError: This request would exceed your account rate limit' >&2; exit 7"
    )
    agent = f"{SWEEP_AGENT}; touch {shlex.quote(str(ran))}"
    result = run_sweep(
        repo, scratch, env,
        "--model", "anthropic/claude-sonnet-5-5", "--probe-cmd", probe, agent=agent,
    )
    assert result.returncode == 20, result.stdout + result.stderr
    assert "sweep" in result.stderr, result.stderr
    assert "anthropic/claude-sonnet-5-5" in result.stderr, result.stderr
    assert "exit code 7" in result.stderr, result.stderr
    assert "rate limit" in result.stderr, result.stderr
    assert not ran.exists(), "the agent command ran although the availability check failed"
    assert not list(scratch.rglob("sweep-dossier.md")), "a dossier was built after the probe failed"
    assert_no_artifact(artifacts(repo, env), "sweep")


def test_a_probe_output_carrying_an_authentication_error_fails_the_phase(gate):
    repo, scratch, env = gate
    probe = "echo 'authentication failed: invalid api key'; exit 0"
    result = run_sweep(
        repo, scratch, env, "--model", "kimi/kimi-k3", "--probe-cmd", probe,
    )
    assert result.returncode == 20, result.stdout + result.stderr
    assert "kimi/kimi-k3" in result.stderr, result.stderr
    assert "provider error" in result.stderr, result.stderr
    assert "invalid api key" in result.stderr, result.stderr
    assert_no_artifact(artifacts(repo, env), "sweep")


def test_a_probe_that_outlives_its_own_timeout_fails_the_phase_and_names_the_timeout(gate):
    repo, scratch, env = gate
    result = run_sweep(
        repo, scratch, env,
        "--model", "deepseek/deepseek-flash", "--probe-cmd", "sleep 30",
        "--probe-timeout", "1",
    )
    assert result.returncode == 20, result.stdout + result.stderr
    assert "timed out" in result.stderr, result.stderr
    assert "1s" in result.stderr, result.stderr
    assert "deepseek/deepseek-flash" in result.stderr, result.stderr
    assert_no_artifact(artifacts(repo, env), "sweep")


def test_a_probe_without_a_model_says_the_model_was_not_supplied(gate):
    repo, scratch, env = gate
    result = run_sweep(repo, scratch, env, "--probe-cmd", "true")
    assert result.returncode == 20, result.stdout + result.stderr
    assert "no model was supplied" in result.stderr, result.stderr
    assert_no_artifact(artifacts(repo, env), "sweep")


# --- AC2: every failed phase is diagnosed from the streams the script can see ---------------------

def test_a_failed_agent_is_diagnosed_from_its_stderr_and_stdout_log(gate):
    repo, scratch, env = gate
    agent = "printf 'AI_APICallError: rate limit exceeded for model\\n' >&2; exit 1"
    result = run_sweep(
        repo, scratch, env, "--model", "anthropic/claude-sonnet-5-5", agent=agent,
    )
    assert result.returncode == 15, result.stdout + result.stderr
    assert "phase=sweep" in result.stderr, result.stderr
    assert "exit=15" in result.stderr, result.stderr
    assert "anthropic/claude-sonnet-5-5" in result.stderr, result.stderr
    assert "AI_APICallError: rate limit exceeded for model" in result.stderr, result.stderr
    assert "sweep-agent.err" in result.stderr, result.stderr
    assert "sweep-agent.log" in result.stderr, result.stderr
    assert "last 40 lines" in result.stderr, result.stderr
    assert_not_stamped(artifacts(repo, env), "sweep")


def test_an_agent_that_exits_zero_without_a_report_is_diagnosed(gate):
    repo, scratch, env = gate
    result = run_sweep(repo, scratch, env, "--model", "gpt-6-sol", agent="true")
    assert result.returncode == 15, result.stdout + result.stderr
    assert "produced no report" in result.stderr, result.stderr
    assert "phase=sweep" in result.stderr, result.stderr
    assert "exit=15" in result.stderr, result.stderr
    assert_not_stamped(artifacts(repo, env), "sweep")


def test_a_report_that_does_not_attest_the_review_is_diagnosed(gate):
    repo, scratch, env = gate
    agent = '{ printf "sweep ok\\n"; } > {output_file}'
    result = run_sweep(repo, scratch, env, "--model", "gpt-6-sol", agent=agent)
    assert result.returncode == 17, result.stdout + result.stderr
    assert "REVIEW-RAN: yes" in result.stderr, result.stderr
    assert "phase=sweep" in result.stderr, result.stderr
    assert "exit=17" in result.stderr, result.stderr
    assert_not_stamped(artifacts(repo, env), "sweep")


def test_record_gets_the_same_diagnosis_for_a_rejected_report(gate):
    repo, scratch, env = gate
    dossier = run_script(
        "dossier", "sweep", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        env=env,
    )
    assert dossier.returncode == 0, dossier.stdout + dossier.stderr
    paths = artifacts(repo, env)
    paths["sweep"].write_text("REVIEW-RAN: no - the sandbox refused to start\n")
    result = run_script(
        "record", "sweep", "--repo", str(repo), "--base", "HEAD",
        "--model", "gpt-6-sol", env=env,
    )
    assert result.returncode == 17, result.stdout + result.stderr
    assert "phase=sweep" in result.stderr, result.stderr
    assert "exit=17" in result.stderr, result.stderr
    assert "gpt-6-sol" in result.stderr, result.stderr
    assert "reason:" in result.stderr, result.stderr
    assert "the sandbox refused to start" in result.stderr, result.stderr


def test_an_agent_that_changes_the_primary_checkout_still_exits_18(gate):
    repo, scratch, env = gate
    agent = f'printf changed >> {shlex.quote(str(repo / "tracked.txt"))}; true'
    result = run_sweep(repo, scratch, env, "--model", "gpt-6-sol", agent=agent)
    assert result.returncode == 18, result.stdout + result.stderr
    assert "primary checkout" in result.stderr, result.stderr
    assert "phase=sweep" in result.stderr, result.stderr
    assert "exit=18" in result.stderr, result.stderr
    assert_not_stamped(artifacts(repo, env), "sweep")


# --- AC3: a phase cannot outlive its timeout, and a timeout kill is its own exit code -------------

def test_a_hung_agent_is_killed_with_its_process_group_and_exits_19(gate, tmp_path):
    repo, scratch, env = gate
    ticks = tmp_path / "child-ticks.txt"
    agent = (
        f'( while true; do printf x >> {shlex.quote(str(ticks))}; sleep 0.2; done ) & sleep 30'
    )
    result = run_sweep(
        repo, scratch, env, "--model", "gpt-6-sol", "--timeout", "2", agent=agent, timeout=60,
    )
    assert result.returncode == 19, result.stdout + result.stderr
    assert "phase=sweep" in result.stderr, result.stderr
    assert "gpt-6-sol" in result.stderr, result.stderr
    assert "2s" in result.stderr, result.stderr
    assert "timeout" in result.stderr.lower(), result.stderr
    assert ticks.exists(), "the child never ran, so the group kill was not exercised"
    before = ticks.stat().st_size
    time.sleep(2)
    assert ticks.stat().st_size == before, "a child outlived the phase timeout; the group was not killed"
    assert_not_stamped(artifacts(repo, env), "sweep")


# --- AC4: progress is observable while the phase runs, on stderr only -----------------------------

def test_progress_lines_and_one_completion_line_go_to_stderr_without_touching_the_artifact(gate):
    repo, scratch, env = gate
    agent = 'sleep 3; { printf "REVIEW-RAN: yes\\nsweep ok\\n"; } > {output_file}'
    result = run_sweep(repo, scratch, env, "--model", "gpt-6-sol", agent=agent)
    assert result.returncode == 0, result.stdout + result.stderr
    beats = [line for line in result.stderr.splitlines() if "phase=sweep elapsed=" in line]
    assert beats, f"no heartbeat line while the agent ran: {result.stderr}"
    beat = beats[0]
    assert "timeout=900s" in beat, beat
    assert "availability check: not configured" in beat, beat
    assert "model=gpt-6-sol" in beat, beat
    completion = [line for line in result.stderr.splitlines() if "phase=sweep complete elapsed=" in line]
    assert len(completion) == 1, completion
    assert "elapsed=" in completion[0], completion[0]
    assert completion[0].endswith("exit=0"), completion[0]
    artifact = artifacts(repo, env)["sweep"]
    assert artifact.read_text().splitlines()[0] == "REVIEW-RAN: yes", artifact.read_text()
    assert "elapsed=" not in artifact.read_text(), "progress leaked into the artifact"


def test_a_heartbeat_carries_the_probe_state_when_a_probe_ran(gate):
    repo, scratch, env = gate
    agent = 'sleep 3; { printf "REVIEW-RAN: yes\\n"; } > {output_file}'
    result = run_sweep(
        repo, scratch, env, "--model", "gpt-6-sol", "--probe-cmd", "true", agent=agent,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    beats = [line for line in result.stderr.splitlines() if "phase=sweep elapsed=" in line]
    assert beats, result.stderr
    assert "availability check: probe ok" in beats[0], beats[0]


# --- the probe contract: placeholders, env equivalents, and a healthy probe that says "unavailable"

def test_the_probe_receives_the_model_id_and_honours_the_env_equivalents(gate, tmp_path):
    repo, scratch, env = gate
    seen = tmp_path / "probe-model.txt"
    probe = f'printf "%s\\n" {{model}} > {shlex.quote(str(seen))}'
    env = {
        **env,
        "ADVERSARIAL_MODEL": "kimi/kimi-k3",
        "ADVERSARIAL_PROBE_CMD": probe,
        "ADVERSARIAL_PROBE_TIMEOUT": "5",
    }
    result = run_sweep(repo, scratch, env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert seen.read_text().strip() == "kimi/kimi-k3", seen.read_text()
    assert "model=kimi/kimi-k3" in result.stderr, result.stderr
    assert "availability check: probe ok" in result.stderr, result.stderr


def test_an_http_status_line_in_the_probe_output_fails_the_phase(gate):
    repo, scratch, env = gate
    result = run_sweep(
        repo, scratch, env, "--model", "gpt-6-sol", "--probe-cmd", "echo 'HTTP/2 429'; exit 0",
    )
    assert result.returncode == 20, result.stdout + result.stderr
    assert "HTTP/2 429" in result.stderr, result.stderr


def test_a_probe_reporting_quota_exhaustion_fails_the_phase(gate):
    repo, scratch, env = gate
    for probe in (
        "printf 'RESOURCE_EXHAUSTED\\n'; exit 0",
        "echo 'quota reached'; exit 0",
        "echo 'Your credit balance is too low to access the API'; exit 0",
        "echo 'credit balance: $0'; exit 0",
    ):
        result = run_sweep(repo, scratch, env, "--model", "gpt-6-sol", "--probe-cmd", probe)
        assert result.returncode == 20, (probe, result.stdout + result.stderr)
        assert "provider error" in result.stderr, result.stderr
        assert_not_stamped(artifacts(repo, env), "sweep")


def test_a_healthy_probe_that_merely_says_unavailable_does_not_fail_the_phase(gate):
    repo, scratch, env = gate
    result = run_sweep(
        repo, scratch, env, "--model", "gpt-6-sol",
        "--probe-cmd",
        "echo 'unavailable'; echo 'latency 403ms'; echo 'quota tier active'; echo '429 tokens left'; "
        "echo 'credit balance: $100; model available'; echo 'credit balance: $100; low latency'; exit 0",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "availability check: probe ok" in result.stderr, result.stderr


# --- a failed phase is never acceptable, and a failed re-run discards the earlier acceptance ------

def test_a_record_after_a_failed_run_cannot_accept_the_leftover_report(gate):
    repo, scratch, env = gate
    agent = 'printf "REVIEW-RAN: yes\\npartial report\\n"; exit 7'
    failed = run_sweep(repo, scratch, env, "--model", "gpt-6-sol", agent=agent)
    assert failed.returncode == 15, failed.stdout + failed.stderr
    rejected = run_script(
        "record", "sweep", "--repo", str(repo), "--base", "HEAD", "--model", "gpt-6-sol", env=env,
    )
    assert rejected.returncode != 0, rejected.stdout + rejected.stderr
    assert "no launch" in rejected.stderr, rejected.stderr
    assert_not_stamped(artifacts(repo, env), "sweep")


def test_a_failed_probe_discards_a_previously_accepted_phase(gate):
    repo, scratch, env = gate
    accepted = run_sweep(repo, scratch, env, "--model", "deepseek/deepseek-flash")
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    hunt = run_script(
        "run", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--model", "gpt-6-sol", "--agent-cmd", SWEEP_AGENT, env=env,
    )
    assert hunt.returncode == 0, hunt.stdout + hunt.stderr
    paths = artifacts(repo, env)
    sweep_stamp = Path(f"{paths['sweep']}.stamp")
    hunt_stamp = Path(f"{paths['hunt']}.stamp")
    assert sweep_stamp.exists() and hunt_stamp.exists(), "the first run was not accepted"

    rerun = run_sweep(
        repo, scratch, env, "--model", "deepseek/deepseek-flash",
        "--probe-cmd", "echo 'rate limit exceeded' >&2; exit 7",
    )
    assert rerun.returncode == 20, rerun.stdout + rerun.stderr
    assert not sweep_stamp.exists(), "a failed re-run left the previous sweep accepted"
    assert not hunt_stamp.exists(), "a failed re-run left the later hunt accepted"

    again = run_script(
        "run", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--model", "gpt-6-sol", "--agent-cmd", SWEEP_AGENT, env=env,
    )
    assert again.returncode == 13, again.stdout + again.stderr
    assert "accepted sweep artifact" in again.stderr, again.stderr


def test_a_probe_that_changes_the_primary_checkout_fails_the_phase(gate):
    repo, scratch, env = gate
    probe = f'printf x >> {shlex.quote(str(repo / "tracked.txt"))}; true'
    result = run_sweep(repo, scratch, env, "--model", "gpt-6-sol", "--probe-cmd", probe)
    assert result.returncode == 18, result.stdout + result.stderr
    assert "primary checkout" in result.stderr, result.stderr
    assert "availability check" in result.stderr, result.stderr
    assert_not_stamped(artifacts(repo, env), "sweep")


# --- the phase deadline bounds the availability check as well as the agent ------------------------

def test_the_phase_deadline_bounds_the_availability_check(gate):
    repo, scratch, env = gate
    started = time.monotonic()
    result = run_sweep(
        repo, scratch, env, "--model", "gpt-6-sol", "--probe-cmd", "sleep 10",
        "--timeout", "1", "--probe-timeout", "30", timeout=60,
    )
    elapsed = time.monotonic() - started
    assert result.returncode == 19, result.stdout + result.stderr
    assert elapsed < 9, f"the phase outlived its 1s deadline by {elapsed:.1f}s"
    assert "1s" in result.stderr and "--timeout" in result.stderr, result.stderr
    assert_not_stamped(artifacts(repo, env), "sweep")


# --- the diagnosis keeps a provider error past the tail window, and the stdout log -------------

def test_a_provider_error_past_the_tail_window_still_appears_verbatim(gate):
    repo, scratch, env = gate
    agent = (
        "printf 'AI_APICallError: rate limit exceeded for model\\n' >&2; "
        'for i in $(seq 1 60); do printf "retry_%s\\n" "$i" >&2; done; exit 1'
    )
    result = run_sweep(repo, scratch, env, "--model", "gpt-6-sol", agent=agent)
    assert result.returncode == 15, result.stdout + result.stderr
    assert "AI_APICallError: rate limit exceeded for model" in result.stderr, result.stderr
    assert "provider-error lines from" in result.stderr, result.stderr
    assert_not_stamped(artifacts(repo, env), "sweep")


def test_a_root_provider_error_survives_a_retry_storm_in_the_diagnosis(gate):
    repo, scratch, env = gate
    agent = (
        "printf 'AI_APICallError: your credit balance is too low\n' >&2; "
        'for i in $(seq 1 50); do printf "status 429 retry %s\n" "$i" >&2; done; exit 1'
    )
    result = run_sweep(repo, scratch, env, "--model", "gpt-6-sol", agent=agent)
    assert result.returncode == 15, result.stdout + result.stderr
    assert "AI_APICallError: your credit balance is too low" in result.stderr, result.stderr


def test_the_agents_stdout_log_is_diagnosed_when_stdout_is_the_artifact(gate):
    repo, scratch, env = gate
    agent = "printf 'partial report line\\n'; printf 'boom-on-stdout\\n'; exit 1"
    result = run_sweep(repo, scratch, env, "--model", "gpt-6-sol", agent=agent)
    assert result.returncode == 15, result.stdout + result.stderr
    assert "boom-on-stdout" in result.stderr, result.stderr
    assert "sweep-agent.log: last 40 lines" in result.stderr, result.stderr
    assert_not_stamped(artifacts(repo, env), "sweep")


# --- usage errors -------------------------------------------------------------------------------

def test_zero_timeouts_are_rejected_as_usage_errors(gate):
    repo, scratch, env = gate
    for flag in ("--timeout", "--probe-timeout"):
        result = run_sweep(repo, scratch, env, "--model", "gpt-6-sol", flag, "0")
        assert result.returncode == 2, result.stdout + result.stderr
        assert "at least 1" in result.stderr, result.stderr


def test_a_model_id_that_is_not_one_line_is_rejected(gate):
    repo, scratch, env = gate
    result = run_sweep(repo, scratch, env, "--model", "gpt-6-sol\nFORGED_LINE")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "FORGED_LINE" not in result.stderr, "an unvalidated model id forged a line of output"


# --- the heartbeat cadence and an interrupted gate ------------------------------------------------

def test_the_heartbeat_repeats_within_thirty_seconds(gate):
    repo, scratch, env = gate
    agent = 'sleep 12; { printf "REVIEW-RAN: yes\\n"; } > {output_file}'
    result = run_sweep(repo, scratch, env, "--model", "gpt-6-sol", agent=agent)
    assert result.returncode == 0, result.stdout + result.stderr
    beats = []
    for line in result.stderr.splitlines():
        match = re.search(r"phase=sweep elapsed=([0-9]+)s", line)
        if match:
            beats.append(int(match.group(1)))
    assert len(beats) >= 2, f"one progress line in 12s is not a 30s cadence: {beats}"
    gaps = [b - a for a, b in zip(beats, beats[1:])]
    assert max(gaps) <= 30, f"a progress gap exceeded 30s: {beats}"


def test_an_interrupted_gate_kills_its_agents_process_group(gate, tmp_path):
    repo, scratch, env = gate
    ticks = tmp_path / "interrupt-ticks.txt"
    agent = f'( while true; do printf x >> {shlex.quote(str(ticks))}; sleep 0.2; done ) & sleep 60'
    gate_process = subprocess.Popen(
        ["bash", str(SCRIPT), "run", "sweep", "--repo", str(repo), "--base", "HEAD",
         "--scratch", str(scratch), "--model", "gpt-6-sol", "--agent-cmd", agent],
        env=env, cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not (ticks.exists() and ticks.stat().st_size > 2):
            time.sleep(0.1)
        assert ticks.exists(), "the agent never started"
        gate_process.terminate()
        gate_process.wait(timeout=30)
        size = ticks.stat().st_size
        time.sleep(2)
        assert ticks.stat().st_size == size, \
            "the agent's process group outlived an interrupted gate"
    finally:
        if gate_process.poll() is None:
            gate_process.kill()


# --- a child the CLI leaves behind never outlives the phase ---------------------------------------

def test_a_child_left_by_a_successful_agent_dies_with_the_phase(gate, tmp_path):
    repo, scratch, env = gate
    ticks = tmp_path / "success-child-ticks.txt"
    agent = (
        f'( while true; do printf x >> {shlex.quote(str(ticks))}; sleep 0.2; done ) & '
        f'sleep 1; {{ printf "REVIEW-RAN: yes\\n"; }} > {{output_file}}'
    )
    result = run_sweep(repo, scratch, env, "--model", "gpt-6-sol", agent=agent)
    assert result.returncode == 0, result.stdout + result.stderr
    assert ticks.exists(), "the child never ran, so the group kill was not exercised"
    size = ticks.stat().st_size
    time.sleep(2)
    assert ticks.stat().st_size == size, "a child outlived a successful phase"


def test_a_child_left_by_a_failed_agent_dies_with_the_phase(gate, tmp_path):
    repo, scratch, env = gate
    ticks = tmp_path / "failed-child-ticks.txt"
    agent = (
        f'( while true; do printf x >> {shlex.quote(str(ticks))}; sleep 0.2; done ) & '
        "printf 'AI_APICallError: rate limit exceeded\\n' >&2; sleep 1; exit 1"
    )
    result = run_sweep(repo, scratch, env, "--model", "gpt-6-sol", agent=agent)
    assert result.returncode == 15, result.stdout + result.stderr
    size = ticks.stat().st_size
    time.sleep(2)
    assert ticks.stat().st_size == size, "a retry child survived the failed phase it belonged to"


# --- an interrupted run is never recordable, and a stale attempt is not diagnosed ------------------

def test_an_interrupted_run_cannot_be_recorded(gate, tmp_path):
    repo, scratch, env = gate
    started = tmp_path / "interrupt-report.txt"
    agent = (
        f'printf "REVIEW-RAN: yes\\npartial\\n" > {{output_file}}; touch {shlex.quote(str(started))}; '
        "sleep 60"
    )
    gate_process = subprocess.Popen(
        ["bash", str(SCRIPT), "run", "sweep", "--repo", str(repo), "--base", "HEAD",
         "--scratch", str(scratch), "--model", "gpt-6-sol", "--agent-cmd", agent],
        env=env, cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not started.exists():
            time.sleep(0.1)
        assert started.exists(), "the agent never wrote its report"
        gate_process.terminate()
        assert gate_process.wait(timeout=30) != 0
    finally:
        if gate_process.poll() is None:
            gate_process.kill()
    rejected = run_script(
        "record", "sweep", "--repo", str(repo), "--base", "HEAD", "--model", "gpt-6-sol", env=env,
    )
    assert rejected.returncode != 0, rejected.stdout + rejected.stderr
    assert "no launch" in rejected.stderr, rejected.stderr
    assert_not_stamped(artifacts(repo, env), "sweep")


def test_a_previous_attempts_agent_log_is_not_used_as_this_attempts_diagnosis(gate):
    repo, scratch, env = gate
    first = run_sweep(
        repo, scratch, env, "--model", "gpt-6-sol",
        agent="printf 'STALE_ATTEMPT_ONE_ERROR\\n' >&2; exit 1",
    )
    assert first.returncode == 15, first.stdout + first.stderr
    second = run_sweep(
        repo, scratch, env, "--model", "gpt-6-sol",
        "--probe-cmd", "echo 'provider error: rate limit exceeded' >&2; exit 7",
    )
    assert second.returncode == 20, second.stdout + second.stderr
    assert "STALE_ATTEMPT_ONE_ERROR" not in second.stderr, \
        "a stale agent log from an earlier attempt was diagnosed as this attempt's"


# --- the timeout kill wins over a dirty checkout, and the probe gets one argv word ----------------

def test_a_timeout_kill_is_reported_as_19_even_when_the_checkout_changed(gate):
    repo, scratch, env = gate
    agent = f'printf x >> {shlex.quote(str(repo / "tracked.txt"))}; sleep 30'
    result = run_sweep(
        repo, scratch, env, "--model", "gpt-6-sol", "--timeout", "1", agent=agent, timeout=60,
    )
    assert result.returncode == 19, result.stdout + result.stderr
    assert "primary checkout" in result.stderr, result.stderr
    assert_not_stamped(artifacts(repo, env), "sweep")


def test_a_model_id_with_a_space_reaches_the_probe_as_one_argument(gate, tmp_path):
    repo, scratch, env = gate
    seen = tmp_path / "probe-argv.txt"
    probe = f'printf "[%s]\\n" {{model}} > {shlex.quote(str(seen))}'
    result = run_sweep(
        repo, scratch, env, "--model", "provider/model with space", "--probe-cmd", probe,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert seen.read_text().splitlines() == ["[provider/model with space]"], seen.read_text()


def test_a_refused_checkout_cleanup_does_not_replace_the_phase_exit_code(gate, tmp_path):
    repo, scratch, env = gate
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    git_wrapper = fakebin / "git"
    git_wrapper.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = worktree ] && [ "$2" = remove ]; then echo "refusing to remove" >&2; exit 1; fi\n'
        'exec /usr/bin/git "$@"\n'
    )
    git_wrapper.chmod(0o755)
    env = {**env, "PATH": f"{fakebin}:{env['PATH']}"}
    result = run_sweep(
        repo, scratch, env, "--model", "gpt-6-sol", "--timeout", "1", agent="sleep 30", timeout=60,
    )
    assert result.returncode == 19, result.stdout + result.stderr
    assert "could not remove checkout" in result.stderr, result.stderr


# --- AC4: a failed phase still ends with its one completion line ---------------------------------

def test_a_failed_phase_still_prints_one_completion_line_with_its_elapsed_time(gate):
    """QA round 1, AC4: a delayed authentication failure must still report completion."""
    repo, scratch, env = gate
    agent = "sleep 2; printf 'authentication failed QA completion check\\n' >&2; exit 1"
    result = run_sweep(repo, scratch, env, "--model", "qa/failure-completion", agent=agent)
    assert result.returncode == 15, result.stdout + result.stderr
    completion = [line for line in result.stderr.splitlines() if "phase=sweep complete elapsed=" in line]
    assert len(completion) == 1, f"a failed phase printed {len(completion)} completion lines: {result.stderr}"
    assert re.search(r"elapsed=[1-9][0-9]*s", completion[0]), completion[0]
    assert "model=qa/failure-completion" in completion[0], completion[0]
    assert completion[0].endswith("exit=15"), completion[0]
    assert "authentication failed QA completion check" in result.stderr, result.stderr
    artifact = artifacts(repo, env)["sweep"]
    artifact_text = artifact.read_text() if artifact.exists() else ""
    assert "complete elapsed=" not in artifact_text, "the completion line leaked into the artifact"
    assert_not_stamped(artifacts(repo, env), "sweep")


def test_every_failed_phase_prints_one_completion_line_and_keeps_its_exit_code(gate):
    repo, scratch, env = gate
    cases = [
        (15, ["--model", "m"], "sleep 1; exit 1"),
        (17, ["--model", "m"], '{ printf "sweep ok\\n"; } > {output_file}'),
        (19, ["--model", "m", "--timeout", "1"], "sleep 30"),
        (20, ["--model", "m", "--probe-cmd", "exit 7"],
         '{ printf "REVIEW-RAN: yes\\n"; } > {output_file}'),
    ]
    for expected, flags, agent in cases:
        result = run_sweep(repo, scratch, env, *flags, agent=agent, timeout=60)
        assert result.returncode == expected, (expected, result.stdout + result.stderr)
        completion = [line for line in result.stderr.splitlines()
                      if "phase=sweep complete elapsed=" in line]
        assert len(completion) == 1, (expected, completion, result.stderr)
        assert completion[0].endswith(f"exit={expected}"), completion[0]
        assert_not_stamped(artifacts(repo, env), "sweep")


def test_a_phase_refused_for_a_missing_predecessor_still_reports_completion(tmp_path):
    """The attempt starts at the scratch directory, so a missing predecessor is a failed phase."""
    repo = make_repo(tmp_path)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    env = clean_env({"TMPDIR": str(tmp_path / "runtime-tmp")})
    (tmp_path / "runtime-tmp").mkdir()
    result = run_script(
        "run", "sweep", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--model", "gpt-6-sol", "--agent-cmd", SWEEP_AGENT, env=env,
    )
    assert result.returncode == 13, result.stdout + result.stderr
    completion = [line for line in result.stderr.splitlines()
                  if "phase=sweep complete elapsed=" in line]
    assert len(completion) == 1, result.stderr
    assert completion[0].endswith("exit=13"), completion[0]
    assert_not_stamped(artifacts(repo, env), "sweep")
    assert not list(scratch.glob("run.*")), "a refused attempt left a run directory behind"


def test_a_run_refused_before_the_attempt_starts_prints_no_completion_line(gate):
    """A usage refusal is not a phase, so the documented refusal is no completion line."""
    repo, scratch, env = gate
    result = run_script(
        "run", "sweep", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        env=env,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "complete elapsed=" not in result.stderr, result.stderr


def test_an_interrupted_phase_reports_completion_with_its_signal_status(gate, tmp_path):
    """AC4 covers every exit of the attempt, including an operator interrupt."""
    repo, scratch, env = gate
    started = tmp_path / "interrupt-completion.txt"
    agent = f'touch {shlex.quote(str(started))}; sleep 60'
    gate_process = subprocess.Popen(
        ["bash", str(SCRIPT), "run", "sweep", "--repo", str(repo), "--base", "HEAD",
         "--scratch", str(scratch), "--model", "gpt-6-sol", "--agent-cmd", agent],
        env=env, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not started.exists():
            time.sleep(0.1)
        assert started.exists(), "the agent never started"
        gate_process.terminate()
        _, stderr = gate_process.communicate(timeout=30)
    finally:
        if gate_process.poll() is None:
            gate_process.kill()
    completion = [line for line in stderr.splitlines() if "phase=sweep complete elapsed=" in line]
    assert len(completion) == 1, stderr
    assert completion[0].endswith("exit=143"), completion[0]
