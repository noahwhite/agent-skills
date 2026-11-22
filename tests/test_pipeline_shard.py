"""SKL-404: the hunt accepts a `--shard K/N` invocation and stops at a failed shard.

The core slice covers the shard invocation surface (grammar, the run-level `hunt.shards` plan,
the per-shard artifact and run-state files, `paths` and `dossier-sizes.md`), the stop contract,
and the `--shard 1/1` parity guarantee. Per-shard candidate subsets (SKL-409) and arbitration
over the shard set (SKL-408) are out of scope; only arbitration's refusal on an unaccepted shard
(AC5) is checked here.

Every test drives the pipeline script with stand-in agents in a throwaway repository, following
`tests/test_pipeline_failfast.py`.
"""

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "adversarial-review-pipeline" / "scripts" / "run-adversarial-pipeline.sh"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "dossier_size"

_spec = importlib.util.spec_from_file_location("dossier_fixture", FIXTURE_DIR / "dossier_fixture.py")
fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fixture)

HUNT_AGENT = '{ printf "REVIEW-RAN: yes\\nhunt ok\\n"; } > {output_file}'
SWEEP_AGENT = '{ printf "REVIEW-RAN: yes\\nsweep ok\\n"; } > {output_file}'
BLIND_AGENT = '{ printf "REVIEW-RAN: no - blind\\n"; } > {output_file}'
EXIT_AGENT = "exit 3"

# Host git configuration and repository-locating variables never reach a fixture: a developer's
# signing, hooks or diff settings must not decide these tests.
GIT_ISOLATION = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
GIT_LOCATORS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
                "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_EXTERNAL_DIFF")


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    # The fixture's own commits carry the same isolation as the script it drives: a host's signing
    # or hooks configuration must never decide whether this module runs.
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "agent-skills@example.com"],
        ["git", "config", "user.name", "agent-skills"],
    ):
        subprocess.run(command, cwd=repo, check=True, capture_output=True, env=clean_env())
    (repo / "tracked.txt").write_text("one\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True, capture_output=True,
                   env=clean_env())
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True, capture_output=True,
                   env=clean_env())
    return repo


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("ADVERSARIAL_") and not k.startswith("GIT_CONFIG")
           and k not in GIT_LOCATORS}
    return {**env, **GIT_ISOLATION, **(extra or {})}


def run_script(*args: str, env: dict[str, str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=timeout,
    )


def new_gate(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    """A throwaway repository with an accepted preflight, plus the session scratch directory."""
    repo = make_repo(tmp_path)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    runtime_tmp = tmp_path / "runtime-tmp"
    runtime_tmp.mkdir()
    env = clean_env({"TMPDIR": str(runtime_tmp)})
    preflight = run_script(
        "preflight", "--full-suite", "on", "--repo", str(repo), "--base", "HEAD", "--test-cmd", "true",
        "--scratch", str(scratch), env=env,
    )
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    return repo, scratch, env


def run_preflight(repo: Path, scratch: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return run_script(
        "preflight", "--full-suite", "on", "--repo", str(repo), "--base", "HEAD", "--test-cmd", "true",
        "--scratch", str(scratch), env=env,
    )


def run_sweep(repo: Path, scratch: Path, env: dict[str, str], *extra: str,
              agent: str = SWEEP_AGENT) -> subprocess.CompletedProcess:
    return run_script(
        "run", "sweep", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--agent-cmd", agent, *extra, env=env,
    )


def run_hunt(repo: Path, scratch: Path, env: dict[str, str], *extra: str,
             agent: str = HUNT_AGENT) -> subprocess.CompletedProcess:
    return run_script(
        "run", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--agent-cmd", agent, *extra, env=env,
    )


def run_arbitrate(repo: Path, scratch: Path, env: dict[str, str], *extra: str) -> subprocess.CompletedProcess:
    return run_script(
        "run", "arbitrate", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--agent-cmd", HUNT_AGENT, "--agent", "Arbiter", "--model", "model/x", *extra, env=env,
    )


def paths(repo: Path, env: dict[str, str]) -> dict[str, Path]:
    listed = run_script("paths", "--repo", str(repo), "--base", "HEAD", env=env)
    assert listed.returncode == 0, listed.stdout + listed.stderr
    out = {}
    for line in listed.stdout.splitlines():
        name, _, path = line.partition(" ")
        if path:
            out[name] = Path(path)
    return out


def accepted_hunt_gate(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    repo, scratch, env = new_gate(tmp_path)
    sweep = run_sweep(repo, scratch, env)
    assert sweep.returncode == 0, sweep.stdout + sweep.stderr
    return repo, scratch, env


@pytest.fixture
def gate(tmp_path):
    return new_gate(tmp_path)


def shard_state(run_dir: Path, shard: str) -> list[Path]:
    return [
        run_dir / f"hunt.{shard}.launch",
        run_dir / f"hunt.{shard}.binding",
        run_dir / f"hunt.{shard}.primary",
        run_dir / f"hunt.{shard}.dossier",
        run_dir / f"hunt.{shard}-agent.err",
        run_dir / f"hunt.{shard}-agent.log",
    ]


def plan_file(run_dir: Path) -> Path:
    return run_dir / "hunt.shards"


# --- AC1: the shard grammar and where the flag is allowed --------------------------------------

@pytest.mark.parametrize("value", ["0/2", "3/2", "2/1", "1/0", "0/0", "01/2", "1/02", "1.0/2", "two/3", ""])
def test_an_invalid_shard_value_is_a_usage_error_naming_it(gate, value):
    repo, scratch, env = gate
    result = run_hunt(repo, scratch, env, "--shard", value)
    assert result.returncode == 2, result.stdout + result.stderr
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert len(lines) == 1, result.stderr
    assert "--shard" in lines[0] and value in lines[0], result.stderr


def test_a_missing_shard_value_is_a_usage_error(gate):
    repo, scratch, env = gate
    result = run_hunt(repo, scratch, env, "--shard")
    assert result.returncode == 2, result.stdout + result.stderr
    assert len([line for line in result.stderr.splitlines() if line.strip()]) == 1, result.stderr
    assert "--shard" in result.stderr, result.stderr


@pytest.mark.parametrize(
    "argv",
    [
        ("run", "sweep"),
        ("run", "arbitrate"),
    ],
)
def test_the_flag_is_refused_on_sweep_and_arbitrate(gate, argv):
    repo, scratch, env = gate
    result = run_script(
        *argv, "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--agent-cmd", HUNT_AGENT, "--shard", "1/2", env=env,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert len(lines) == 1, result.stderr
    assert "--shard is not valid for the " + argv[1] + " phase" in lines[0], result.stderr


@pytest.mark.parametrize("argv", [("preflight",), ("paths",), ("checklist",), ("checkout",)])
def test_the_flag_is_refused_on_commands_that_take_no_phase(gate, argv):
    repo, scratch, env = gate
    result = run_script(
        *argv, "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch), "--shard", "1/2",
        env=env,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert len(lines) == 1, result.stderr
    assert "--shard is not valid for the " + argv[0] + " command" in lines[0], result.stderr


# --- AC1: plan, per-shard artifacts and state files -------------------------------------------

def test_a_sharded_hunt_writes_its_own_artifact_state_and_plan(gate):
    repo, scratch, env = gate
    sweep = run_sweep(repo, scratch, env)
    assert sweep.returncode == 0, sweep.stdout + sweep.stderr
    hunt = run_hunt(repo, scratch, env, "--shard", "1/2")
    assert hunt.returncode == 0, hunt.stdout + hunt.stderr
    files = paths(repo, env)
    run_dir = files["run"]
    assert files["hunt.1"] == run_dir / "phase2-hunt.1.md"
    assert (run_dir / "phase2-hunt.md").exists() is False
    for path in shard_state(run_dir, "1"):
        assert path.exists(), path
    assert (run_dir / "hunt.1.launch").read_bytes() == b"shard=1/2\n"
    for path in shard_state(run_dir, "2"):
        assert not path.exists(), path
    plan = plan_file(run_dir)
    assert plan.is_file()
    plan_lines = plan.read_text().splitlines()
    assert plan_lines[0] == "n=2"
    assert plan_lines[1:] == [
        str(run_dir / "phase2-hunt.1.md"),
        str(run_dir / "phase2-hunt.2.md"),
    ]
    binding = (run_dir / "hunt.1.binding").read_text()
    assert "shard=1/2" in binding.splitlines()
    stamp = Path(f"{files['hunt.1']}.stamp").read_text()
    assert "shard=1/2" in stamp.splitlines()


def test_paths_and_dossier_sizes_list_one_line_per_shard(accepted_gate):
    repo, scratch, env = accepted_gate
    for k in (1, 2):
        hunt = run_hunt(repo, scratch, env, "--shard", f"{k}/2")
        assert hunt.returncode == 0, hunt.stdout + hunt.stderr
    files = paths(repo, env)
    run_dir = files["run"]
    assert "hunt" not in files
    assert files["hunt.1"] == run_dir / "phase2-hunt.1.md"
    assert files["hunt.2"] == run_dir / "phase2-hunt.2.md"
    listed = run_script("paths", "--repo", str(repo), "--base", "HEAD", env=env)
    assert [line.split(" ", 1)[0] for line in listed.stdout.splitlines()] == [
        "run", "preflight", "suite_log", "sweep", "hunt.1", "hunt.2", "arbitrate", "dossier_sizes",
    ], listed.stdout
    sizes = (run_dir / "dossier-sizes.md").read_text().splitlines()
    hunt_lines = [line for line in sizes if line.startswith("hunt")]
    assert len(hunt_lines) == 2, sizes
    assert hunt_lines[0].startswith("hunt.1: ") and hunt_lines[0].endswith(" bytes"), sizes
    assert hunt_lines[1].startswith("hunt.2: ") and hunt_lines[1].endswith(" bytes"), sizes


@pytest.fixture
def accepted_gate(tmp_path):
    return accepted_hunt_gate(tmp_path)


def test_a_later_shard_completes_the_plan_and_re_running_one_leaves_the_other(accepted_gate):
    repo, scratch, env = accepted_gate
    first = run_hunt(repo, scratch, env, "--shard", "1/2")
    assert first.returncode == 0, first.stdout + first.stderr
    files = paths(repo, env)
    run_dir = files["run"]
    assert not (run_dir / "phase2-hunt.2.md").exists()
    second = run_hunt(repo, scratch, env, "--shard", "2/2")
    assert second.returncode == 0, second.stdout + second.stderr
    shard2_artifact = (run_dir / "phase2-hunt.2.md").read_bytes()
    shard2_stamp = (run_dir / "phase2-hunt.2.md.stamp").read_bytes()
    again = run_hunt(repo, scratch, env, "--shard", "1/2")
    assert again.returncode == 0, again.stdout + again.stderr
    assert (run_dir / "phase2-hunt.2.md").read_bytes() == shard2_artifact
    assert (run_dir / "phase2-hunt.2.md.stamp").read_bytes() == shard2_stamp
    for path in shard_state(run_dir, "2"):
        assert path.exists(), path


def test_a_plan_conflict_is_a_usage_error_that_changes_nothing(accepted_gate):
    repo, scratch, env = accepted_gate
    first = run_hunt(repo, scratch, env, "--shard", "1/2")
    assert first.returncode == 0, first.stdout + first.stderr
    files = paths(repo, env)
    run_dir = files["run"]
    plan_before = plan_file(run_dir).read_bytes()
    stamp_before = Path(f"{files['hunt.1']}.stamp").read_bytes()
    state_before = {path.name: path.read_bytes()
                    for path in sorted(run_dir.iterdir()) if path.is_file()}
    for extra in (("--shard", "1/3"), ("--shard", "2/3"), (), ("--shard", "1/1")):
        result = run_hunt(repo, scratch, env, *extra)
        assert result.returncode == 2, (extra, result.stdout + result.stderr)
        assert plan_file(run_dir).read_bytes() == plan_before, extra
        assert Path(f"{files['hunt.1']}.stamp").read_bytes() == stamp_before, extra
        assert (run_dir / "phase2-hunt.1.md").exists(), extra
    # `record` reads the same plan and refuses a conflicting count the same way.
    conflicting = run_script(
        "record", "hunt", "--repo", str(repo), "--base", "HEAD", "--shard", "1/3", env=env,
    )
    assert conflicting.returncode == 2, conflicting.stdout + conflicting.stderr
    assert plan_file(run_dir).read_bytes() == plan_before
    assert Path(f"{files['hunt.1']}.stamp").read_bytes() == stamp_before
    state_after = {path.name: path.read_bytes()
                   for path in sorted(run_dir.iterdir()) if path.is_file()}
    assert state_after == state_before


def test_an_unsharded_hunt_then_a_shard_is_a_usage_error(accepted_gate):
    repo, scratch, env = accepted_gate
    plain = run_hunt(repo, scratch, env)
    assert plain.returncode == 0, plain.stdout + plain.stderr
    files = paths(repo, env)
    run_dir = files["run"]
    assert not plan_file(run_dir).exists()
    result = run_hunt(repo, scratch, env, "--shard", "1/2")
    assert result.returncode == 2, result.stdout + result.stderr
    assert not plan_file(run_dir).exists()
    assert Path(f"{files['hunt']}.stamp").exists()


def test_dossier_and_record_hunt_take_the_same_shard(accepted_gate):
    repo, scratch, env = accepted_gate
    dossier = run_script(
        "dossier", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--shard", "1/2", env=env,
    )
    checkout, dossier_path = dossier_of(dossier)
    run_dir = paths(repo, env)["run"]
    report = run_dir / "phase2-hunt.1.md"
    assert str(report) in dossier.stderr, dossier.stderr
    assert dossier_path.name == "hunt.1-dossier.md", dossier_path
    report.write_text("REVIEW-RAN: yes\nshard one\n")
    wrong = run_script(
        "record", "hunt", "--repo", str(repo), "--base", "HEAD", "--shard", "2/2", env=env,
    )
    assert wrong.returncode == 15, wrong.stdout + wrong.stderr
    assert not Path(f"{report}.stamp").exists()
    missing = run_script("record", "hunt", "--repo", str(repo), "--base", "HEAD", env=env)
    assert missing.returncode == 2, missing.stdout + missing.stderr
    recorded = run_script(
        "record", "hunt", "--repo", str(repo), "--base", "HEAD", "--shard", "1/2", env=env,
    )
    assert recorded.returncode == 0, recorded.stdout + recorded.stderr
    assert Path(f"{report}.stamp").exists()
    assert "shard=1/2" in (run_dir / "hunt.1.binding").read_text().splitlines()
    assert run_script("cleanup", str(checkout), "--repo", str(repo), env=env).returncode == 0


def test_record_hunt_refuses_a_shard_selection_the_dossier_did_not_use(accepted_gate):
    repo, scratch, env = accepted_gate
    run_dir = paths(repo, env)["run"]
    report = run_dir / "phase2-hunt.md"
    launch = run_dir / "hunt.launch"

    # A dossier written as `--shard 1/1` is recorded only as `--shard 1/1`.
    dossier = run_script(
        "dossier", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--shard", "1/1", env=env,
    )
    checkout, _ = dossier_of(dossier)
    assert "the same --shard 1/1" in dossier.stderr, dossier.stderr
    report.write_text("REVIEW-RAN: yes\none of one\n")
    state_before = {path.name: path.read_bytes()
                    for path in sorted(run_dir.iterdir()) if path.is_file()}
    plain = run_script("record", "hunt", "--repo", str(repo), "--base", "HEAD", env=env)
    assert plain.returncode == 13, plain.stdout + plain.stderr
    assert "records 'shard=1/1'" in plain.stderr and "selects 'shard=none'" in plain.stderr, plain.stderr
    assert not Path(f"{report}.stamp").exists()
    state_after = {path.name: path.read_bytes()
                   for path in sorted(run_dir.iterdir()) if path.is_file()}
    assert state_after == state_before
    assert launch.read_bytes() == b"shard=1/1\n", launch.read_bytes()
    recorded = run_script(
        "record", "hunt", "--repo", str(repo), "--base", "HEAD", "--shard", "1/1", env=env,
    )
    assert recorded.returncode == 0, recorded.stdout + recorded.stderr
    assert Path(f"{report}.stamp").exists()
    assert run_script("cleanup", str(checkout), "--repo", str(repo), env=env).returncode == 0

    # And an unsharded dossier is recorded only without the flag.
    sweep = run_sweep(repo, scratch, env)
    assert sweep.returncode == 0, sweep.stdout + sweep.stderr
    assert not launch.exists(), launch
    dossier = run_script(
        "dossier", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch), env=env,
    )
    checkout, _ = dossier_of(dossier)
    assert "no --shard (this dossier recorded shard=none" in dossier.stderr, dossier.stderr
    assert launch.read_bytes() == b"shard=none\n", launch.read_bytes()
    report.write_text("REVIEW-RAN: yes\nplain\n")
    flagged = run_script(
        "record", "hunt", "--repo", str(repo), "--base", "HEAD", "--shard", "1/1", env=env,
    )
    assert flagged.returncode == 13, flagged.stdout + flagged.stderr
    assert "records 'shard=none'" in flagged.stderr and "selects 'shard=1/1'" in flagged.stderr, flagged.stderr
    assert not Path(f"{report}.stamp").exists()
    recorded = run_script("record", "hunt", "--repo", str(repo), "--base", "HEAD", env=env)
    assert recorded.returncode == 0, recorded.stdout + recorded.stderr
    assert not any(line.startswith("shard=") for line in
                   (run_dir / "hunt.binding").read_text().splitlines())
    assert run_script("cleanup", str(checkout), "--repo", str(repo), env=env).returncode == 0


def test_a_sharded_hunt_refuses_a_marker_naming_another_selection(accepted_gate):
    repo, scratch, env = accepted_gate
    run_dir = paths(repo, env)["run"]
    dossier = run_script(
        "dossier", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--shard", "1/2", env=env,
    )
    checkout, _ = dossier_of(dossier)
    assert "the same --shard 1/2" in dossier.stderr, dossier.stderr
    (run_dir / "hunt.1.launch").write_bytes(b"shard=none\n")
    (run_dir / "phase2-hunt.1.md").write_text("REVIEW-RAN: yes\nshard one\n")
    state_before = {path.name: path.read_bytes()
                    for path in sorted(run_dir.iterdir()) if path.is_file()}
    refused = run_script(
        "record", "hunt", "--repo", str(repo), "--base", "HEAD", "--shard", "1/2", env=env,
    )
    assert refused.returncode == 13, refused.stdout + refused.stderr
    assert "records 'shard=none'" in refused.stderr and "selects 'shard=1/2'" in refused.stderr, refused.stderr
    assert "dossier hunt --shard 1/2" in refused.stderr, refused.stderr
    assert not Path(f"{run_dir / 'phase2-hunt.1.md'}.stamp").exists()
    state_after = {path.name: path.read_bytes()
                   for path in sorted(run_dir.iterdir()) if path.is_file()}
    assert state_after == state_before
    # A marker naming another index of the same plan is the same mismatch, and a marker without
    # its trailing newline is the same selection.
    (run_dir / "hunt.1.launch").write_bytes(b"shard=2/2\n")
    (run_dir / "phase2-hunt.1.md").write_text("REVIEW-RAN: yes\nshard one\n")
    other_index = run_script(
        "record", "hunt", "--repo", str(repo), "--base", "HEAD", "--shard", "1/2", env=env,
    )
    assert other_index.returncode == 13, other_index.stdout + other_index.stderr
    assert "records 'shard=2/2'" in other_index.stderr, other_index.stderr
    (run_dir / "hunt.1.launch").write_bytes(b"shard=1/2")
    (run_dir / "phase2-hunt.1.md").write_text("REVIEW-RAN: yes\nshard one\n")
    recorded = run_script(
        "record", "hunt", "--repo", str(repo), "--base", "HEAD", "--shard", "1/2", env=env,
    )
    assert recorded.returncode == 0, recorded.stdout + recorded.stderr
    assert Path(f"{run_dir / 'phase2-hunt.1.md'}.stamp").exists()
    assert run_script("cleanup", str(checkout), "--repo", str(repo), env=env).returncode == 0


def test_an_environment_supplied_selection_is_recorded_and_required(accepted_gate):
    repo, scratch, env = accepted_gate
    run_dir = paths(repo, env)["run"]
    report = run_dir / "phase2-hunt.md"
    sharded_env = {**env, "ADVERSARIAL_SHARD": "1/1"}
    dossier = run_script(
        "dossier", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        env=sharded_env,
    )
    checkout, _ = dossier_of(dossier)
    assert (run_dir / "hunt.launch").read_bytes() == b"shard=1/1\n"
    report.write_text("REVIEW-RAN: yes\nenv\n")
    # The environment supplies the selection as the flag does, so the same value must be repeated.
    dropped = run_script("record", "hunt", "--repo", str(repo), "--base", "HEAD", env=env)
    assert dropped.returncode == 13, dropped.stdout + dropped.stderr
    assert "records 'shard=1/1'" in dropped.stderr and "selects 'shard=none'" in dropped.stderr, dropped.stderr
    assert not Path(f"{report}.stamp").exists()
    recorded = run_script(
        "record", "hunt", "--repo", str(repo), "--base", "HEAD", env=sharded_env,
    )
    assert recorded.returncode == 0, recorded.stdout + recorded.stderr
    assert Path(f"{report}.stamp").exists()
    assert run_script("cleanup", str(checkout), "--repo", str(repo), env=env).returncode == 0


def test_an_unreadable_hunt_launch_is_refused_and_never_read_as_empty(accepted_gate):
    repo, scratch, env = accepted_gate
    run_dir = paths(repo, env)["run"]
    report = run_dir / "phase2-hunt.md"
    launch = run_dir / "hunt.launch"
    dossier = run_script(
        "dossier", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch), env=env,
    )
    checkout, _ = dossier_of(dossier)
    report.write_text("REVIEW-RAN: yes\nplain\n")
    # An unreadable marker carrying a valid selection is a state error, never "no flag".
    launch.chmod(0)
    denied = True
    try:
        with launch.open("rb") as probe:
            probe.read(1)
        denied = False
    except PermissionError:
        denied = True
    try:
        if denied:
            refused = run_script("record", "hunt", "--repo", str(repo), "--base", "HEAD", env=env)
            assert refused.returncode == 15, refused.stdout + refused.stderr
            assert "launch marker" in refused.stderr, refused.stderr
            assert not Path(f"{report}.stamp").exists()
    finally:
        launch.chmod(0o644)
    if not denied:
        pytest.skip("this process can read a mode-000 file, so the denial cannot be established")
    # A marker without its trailing newline is the same selection, not a broken one.
    launch.write_bytes(launch.read_bytes().rstrip(b"\n"))
    report.write_text("REVIEW-RAN: yes\nplain\n")
    recorded = run_script("record", "hunt", "--repo", str(repo), "--base", "HEAD", env=env)
    assert recorded.returncode == 0, recorded.stdout + recorded.stderr
    assert Path(f"{report}.stamp").exists()
    assert run_script("cleanup", str(checkout), "--repo", str(repo), env=env).returncode == 0


def test_a_malformed_launch_marker_is_refused_with_a_bounded_sanitised_diagnosis(accepted_gate):
    repo, scratch, env = accepted_gate
    run_dir = paths(repo, env)["run"]
    report = run_dir / "phase2-hunt.md"
    launch = run_dir / "hunt.launch"
    dossier = run_script(
        "dossier", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch), env=env,
    )
    checkout, _ = dossier_of(dossier)
    # Anything but the one printable selection line is an unusable state, not a selection.
    long_valid = b"shard=1/" + b"1" * 57
    near_limit = b"shard=1/" + b"1" * 86
    assert len(near_limit) == 94
    for marker in (b"shard=none\nTRAIL\n", b"shard=none\n\n", b"shard=none\x00\n",
                   b"shard=none\x00", b"shard=none\r\n", b"shard=no\x1be\n",
                   b"shard=none \n", b"shard=3/2\n", b"shard=none" + b"x" * 55,
                   b"shard=none" + b"x" * 60, long_valid + b"\n" + b"JUNK\n",
                   near_limit + b"\n" + b"J", near_limit + b"J",
                   near_limit + b"\n" + b"1" * 100):
        sidecar = run_dir / "hunt.dossier"
        sidecar_before = sidecar.read_bytes() if sidecar.exists() else None
        launch.write_bytes(marker)
        report.write_text("REVIEW-RAN: yes\nplain\n")
        refused = run_script("record", "hunt", "--repo", str(repo), "--base", "HEAD", env=env)
        assert refused.returncode == 15, (marker, refused.stdout + refused.stderr)
        assert "not exactly the one selection line the launcher wrote" in refused.stderr, refused.stderr
        assert not Path(f"{report}.stamp").exists()
        assert (sidecar.read_bytes() if sidecar.exists() else None) == sidecar_before, marker
    # A long but valid selection the launcher could have written is a mismatch, not malformed state.
    launch.write_bytes(long_valid + b"\n")
    report.write_text("REVIEW-RAN: yes\nplain\n")
    long_mismatch = run_script("record", "hunt", "--repo", str(repo), "--base", "HEAD", env=env)
    assert long_mismatch.returncode == 13, long_mismatch.stdout + long_mismatch.stderr
    assert f"records '{long_valid.decode()}'" in long_mismatch.stderr, long_mismatch.stderr
    # The reader's limit is the boundary: 94-byte line plus newline is a mismatch, one more byte is overflow.
    launch.write_bytes(near_limit + b"\n")
    report.write_text("REVIEW-RAN: yes\nplain\n")
    at_limit = run_script("record", "hunt", "--repo", str(repo), "--base", "HEAD", env=env)
    assert at_limit.returncode == 13, at_limit.stdout + at_limit.stderr
    # A missing report is reported as the missing report, never as a selection problem.
    launch.write_bytes(b"shard=1/1\n")
    report.unlink()
    no_report = run_script("record", "hunt", "--repo", str(repo), "--base", "HEAD", env=env)
    assert no_report.returncode == 15, no_report.stdout + no_report.stderr
    assert "produced no report" in no_report.stderr, no_report.stderr
    # A printable marker naming another selection is a mismatch that names both values.
    launch.write_bytes(b"shard=1/1\n")
    report.write_text("REVIEW-RAN: yes\nplain\n")
    mismatch = run_script("record", "hunt", "--repo", str(repo), "--base", "HEAD", env=env)
    assert mismatch.returncode == 13, mismatch.stdout + mismatch.stderr
    assert "records 'shard=1/1'" in mismatch.stderr and "selects 'shard=none'" in mismatch.stderr, mismatch.stderr
    # A huge marker: the diagnosis stays bounded.
    launch.write_bytes(b"A" * (4 * 1024 * 1024))
    report.write_text("REVIEW-RAN: yes\nplain\n")
    huge = run_script("record", "hunt", "--repo", str(repo), "--base", "HEAD", env=env)
    assert huge.returncode == 15, huge.stdout + huge.stderr
    assert len(huge.stderr.encode()) < 4096, len(huge.stderr.encode())
    assert not Path(f"{report}.stamp").exists()
    assert run_script("cleanup", str(checkout), "--repo", str(repo), env=env).returncode == 0


def test_an_emptied_launch_marker_is_refused_for_either_selection(accepted_gate):
    repo, scratch, env = accepted_gate
    run_dir = paths(repo, env)["run"]
    report = run_dir / "phase2-hunt.md"
    launch = run_dir / "hunt.launch"

    # A truncated marker is not "the flag was omitted": it is refused, never read as the weaker form.
    dossier = run_script(
        "dossier", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch), env=env,
    )
    plain_checkout, _ = dossier_of(dossier)
    report.write_text("REVIEW-RAN: yes\nplain\n")
    launch.write_text("")
    plain = run_script("record", "hunt", "--repo", str(repo), "--base", "HEAD", env=env)
    assert plain.returncode == 15, plain.stdout + plain.stderr
    assert not Path(f"{report}.stamp").exists()
    assert run_script("cleanup", str(plain_checkout), "--repo", str(repo), env=env).returncode == 0

    sweep = run_sweep(repo, scratch, env)
    assert sweep.returncode == 0, sweep.stdout + sweep.stderr
    dossier = run_script(
        "dossier", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--shard", "1/1", env=env,
    )
    flagged_checkout, _ = dossier_of(dossier)
    report.write_text("REVIEW-RAN: yes\none of one\n")
    launch.write_text("\n")
    flagged = run_script(
        "record", "hunt", "--repo", str(repo), "--base", "HEAD", "--shard", "1/1", env=env,
    )
    assert flagged.returncode == 15, flagged.stdout + flagged.stderr
    assert not Path(f"{report}.stamp").exists()
    assert run_script("cleanup", str(flagged_checkout), "--repo", str(repo), env=env).returncode == 0


def test_a_flagged_dossier_recorded_with_its_flag_matches_the_unsharded_record(accepted_gate):
    repo, scratch, env = accepted_gate
    run_dir = paths(repo, env)["run"]
    report = run_dir / "phase2-hunt.md"
    report_text = "REVIEW-RAN: yes\nparity\n"

    plain_dossier = run_script(
        "dossier", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch), env=env,
    )
    plain_checkout, _ = dossier_of(plain_dossier)
    report.write_text(report_text)
    plain_record = run_script("record", "hunt", "--repo", str(repo), "--base", "HEAD", env=env)
    assert plain_record.returncode == 0, plain_record.stdout + plain_record.stderr
    plain_stamp = Path(f"{report}.stamp").read_bytes()
    plain_binding = (run_dir / "hunt.binding").read_bytes()
    plain_primary = (run_dir / "hunt.primary").read_bytes()
    plain_sidecar = (run_dir / "hunt.dossier").read_bytes()
    plain_files = sorted(path.name for path in run_dir.iterdir())
    sweep_artifact = (run_dir / "phase1-sweep.md").read_bytes()
    assert run_script("cleanup", str(plain_checkout), "--repo", str(repo), env=env).returncode == 0

    sweep = run_sweep(repo, scratch, env)
    assert sweep.returncode == 0, sweep.stdout + sweep.stderr
    # Re-running the sweep rewrites its artifact; restoring the bytes keeps every bound input
    # identical, so the two records can be compared byte for byte.
    (run_dir / "phase1-sweep.md").write_bytes(sweep_artifact)
    flagged_dossier = run_script(
        "dossier", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--shard", "1/1", env=env,
    )
    flagged_checkout, _ = dossier_of(flagged_dossier)
    report.write_text(report_text)
    flagged_record = run_script(
        "record", "hunt", "--repo", str(repo), "--base", "HEAD", "--shard", "1/1", env=env,
    )
    assert flagged_record.returncode == 0, flagged_record.stdout + flagged_record.stderr
    flagged_stamp = Path(f"{report}.stamp").read_bytes()
    flagged_binding = (run_dir / "hunt.binding").read_bytes()

    # Byte-identical to the unsharded record: the selection never enters the stamp or the binding.
    assert flagged_stamp == plain_stamp
    assert flagged_binding == plain_binding
    assert sorted(path.name for path in run_dir.iterdir()) == plain_files
    assert (run_dir / "hunt.primary").read_bytes() == plain_primary
    assert (run_dir / "hunt.dossier").read_bytes().split(b"\nbytes=")[-1] == plain_sidecar.split(b"\nbytes=")[-1]
    assert not (run_dir / "hunt.shards").exists()
    assert run_script("cleanup", str(flagged_checkout), "--repo", str(repo), env=env).returncode == 0


def test_rerunning_the_preflight_removes_the_plan_and_every_shard_file(accepted_gate):
    repo, scratch, env = accepted_gate
    for k in (1, 2):
        assert run_hunt(repo, scratch, env, "--shard", f"{k}/2").returncode == 0
    files = paths(repo, env)
    run_dir = files["run"]
    assert plan_file(run_dir).exists()
    again = run_preflight(repo, scratch, env)
    assert again.returncode == 0, again.stdout + again.stderr
    assert not plan_file(run_dir).exists()
    for k in (1, 2):
        assert not (run_dir / f"phase2-hunt.{k}.md").exists()
        assert not (run_dir / f"phase2-hunt.{k}.md.stamp").exists()
        for path in shard_state(run_dir, str(k)):
            assert not path.exists(), path


def test_rerunning_the_sweep_removes_the_plan_and_every_shard_file(accepted_gate):
    repo, scratch, env = accepted_gate
    for k in (1, 2):
        assert run_hunt(repo, scratch, env, "--shard", f"{k}/2").returncode == 0
    files = paths(repo, env)
    run_dir = files["run"]
    assert plan_file(run_dir).exists()
    again = run_sweep(repo, scratch, env)
    assert again.returncode == 0, again.stdout + again.stderr
    assert not plan_file(run_dir).exists()
    for k in (1, 2):
        assert not (run_dir / f"phase2-hunt.{k}.md").exists()
        for path in shard_state(run_dir, str(k)):
            assert not path.exists(), path


# --- AC5: the stop contract ----------------------------------------------------------------

def test_a_failed_shard_uses_the_unsharded_exit_code_and_keeps_its_sibling(tmp_path):
    repo, scratch, env = accepted_hunt_gate(tmp_path / "sharded")
    assert run_hunt(repo, scratch, env, "--shard", "2/2").returncode == 0
    files = paths(repo, env)
    run_dir = files["run"]
    sibling_stamp = (run_dir / "phase2-hunt.2.md.stamp").read_bytes()
    failed = run_hunt(repo, scratch, env, "--shard", "1/2", agent=BLIND_AGENT)
    assert failed.returncode == 17, failed.stdout + failed.stderr
    assert "shard=1/2" in failed.stderr, failed.stderr
    assert not (run_dir / "hunt.1.launch").exists()
    assert not (run_dir / "phase2-hunt.1.md.stamp").exists()
    assert (run_dir / "phase2-hunt.2.md.stamp").read_bytes() == sibling_stamp
    phase_lines = [line for line in failed.stderr.splitlines()
                   if line.startswith("adversarial-pipeline: phase=hunt")]
    assert phase_lines, failed.stderr
    for line in phase_lines:
        assert "shard=1/2" in line, line
    arbitrate = run_arbitrate(repo, scratch, env)
    assert arbitrate.returncode == 13, arbitrate.stdout + arbitrate.stderr
    assert "1/2" in arbitrate.stderr and "hunt" in arbitrate.stderr, arbitrate.stderr

    plain_repo, plain_scratch, plain_env = accepted_hunt_gate(tmp_path / "unsharded")
    plain_failed = run_hunt(plain_repo, plain_scratch, plain_env, agent=BLIND_AGENT)
    assert plain_failed.returncode == failed.returncode, plain_failed.stdout + plain_failed.stderr
    plain_phase_lines = [line for line in plain_failed.stderr.splitlines()
                         if line.startswith("adversarial-pipeline: phase=hunt")]
    assert plain_phase_lines, plain_failed.stderr
    for line in plain_phase_lines:
        assert "shard=" not in line, line


def test_a_non_zero_agent_exit_is_the_same_code_sharded_and_unsharded(tmp_path):
    sharded_repo, sharded_scratch, sharded_env = accepted_hunt_gate(tmp_path / "sharded")
    sharded = run_hunt(sharded_repo, sharded_scratch, sharded_env, "--shard", "1/2", agent=EXIT_AGENT)
    plain_repo, plain_scratch, plain_env = accepted_hunt_gate(tmp_path / "unsharded")
    plain = run_hunt(plain_repo, plain_scratch, plain_env, agent=EXIT_AGENT)
    assert sharded.returncode == plain.returncode == 15, sharded.stdout + sharded.stderr
    assert "shard=1/2" in sharded.stderr, sharded.stderr


# --- AC1: `--shard 1/1` is byte-identical to an unsharded run --------------------------------

def test_shard_one_of_one_is_byte_identical_to_an_unsharded_run(accepted_gate):
    repo, scratch, env = accepted_gate
    plain = run_hunt(repo, scratch, env)
    assert plain.returncode == 0, plain.stdout + plain.stderr
    files = paths(repo, env)
    run_dir = files["run"]
    assert files["hunt"] == run_dir / "phase2-hunt.md"
    artifact = files["hunt"].read_bytes()
    stamp = Path(f"{files['hunt']}.stamp").read_bytes()
    binding = (run_dir / "hunt.binding").read_bytes()
    one_of_one = run_hunt(repo, scratch, env, "--shard", "1/1")
    assert one_of_one.returncode == 0, one_of_one.stdout + one_of_one.stderr
    assert files["hunt"].read_bytes() == artifact
    assert Path(f"{files['hunt']}.stamp").read_bytes() == stamp
    assert (run_dir / "hunt.binding").read_bytes() == binding
    assert (run_dir / "hunt.launch").read_bytes() == b"shard=1/1\n"
    assert not plan_file(run_dir).exists()


def dossier_of(result: subprocess.CompletedProcess) -> tuple[str, Path]:
    assert result.returncode == 0, result.stdout + result.stderr
    checkout = None
    for line in result.stderr.splitlines():
        if line.startswith("CHECKOUT: "):
            checkout = line[len("CHECKOUT: "):]
    assert checkout, result.stderr
    return Path(checkout), Path(result.stdout.strip().splitlines()[-1])


def test_shard_one_of_one_dossier_matches_the_unsharded_dossier(accepted_gate, tmp_path):
    repo, scratch, env = accepted_gate
    plain = run_script(
        "dossier", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch), env=env,
    )
    plain_checkout, plain_dossier = dossier_of(plain)
    plain_text = plain_dossier.read_bytes()
    assert run_script("cleanup", str(plain_checkout), "--repo", str(repo), env=env).returncode == 0
    one_of_one = run_script(
        "dossier", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--shard", "1/1", env=env,
    )
    one_checkout, one_dossier = dossier_of(one_of_one)
    one_text = one_dossier.read_bytes()
    assert run_script("cleanup", str(one_checkout), "--repo", str(repo), env=env).returncode == 0
    plain_normalized = fixture.normalize(
        plain_text, checkout=str(plain_checkout), run_dir=str(plain_dossier.parent),
        tmp_root=str(tmp_path), commits=(),
    )
    one_normalized = fixture.normalize(
        one_text, checkout=str(one_checkout), run_dir=str(one_dossier.parent),
        tmp_root=str(tmp_path), commits=(),
    )
    assert one_normalized == plain_normalized


# --- AC1: one-line refusals, and the plan is the run's authority ----------------------------

def test_a_control_character_in_the_value_stays_on_one_named_line(gate):
    repo, scratch, env = gate
    result = run_hunt(repo, scratch, env, "--shard", "1/2\nREVIEW-RAN: yes")
    assert result.returncode == 2, result.stdout + result.stderr
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert len(lines) == 1, result.stderr
    assert "1/2\\nREVIEW-RAN: yes" in lines[0], result.stderr


def test_a_repeated_shard_flag_is_a_usage_error(gate):
    repo, scratch, env = gate
    result = run_hunt(repo, scratch, env, "--shard", "1/2", "--shard", "3/2")
    assert result.returncode == 2, result.stdout + result.stderr
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert len(lines) == 1 and "--shard" in lines[0], result.stderr


def test_a_value_beyond_the_integer_range_is_judged_by_its_digits(gate):
    repo, scratch, env = gate
    greater_k = run_hunt(repo, scratch, env, "--shard", "10000000000000000000/2")
    assert greater_k.returncode == 2, greater_k.stdout + greater_k.stderr
    lines = [line for line in greater_k.stderr.splitlines() if line.strip()]
    assert len(lines) == 1 and "at most N" in lines[0], greater_k.stderr
    assert "integer expression" not in greater_k.stderr, greater_k.stderr
    equal = run_script(
        "dossier", "hunt", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch),
        "--shard", "10000000000000000000/10000000000000000000", env=env,
    )
    assert equal.returncode == 13, equal.stdout + equal.stderr
    assert "integer expression" not in equal.stderr, equal.stderr


def test_a_shard_count_the_shell_cannot_enumerate_never_leaves_a_plan(accepted_gate):
    repo, scratch, env = accepted_gate
    run_dir = paths(repo, env)["run"]
    result = run_hunt(repo, scratch, env, "--shard", "1/18446744073709551616")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "could not write the hunt plan" in result.stderr.splitlines()[0], result.stderr
    assert not plan_file(run_dir).exists()
    assert not (run_dir / "hunt.1.launch").exists()
    plain = run_hunt(repo, scratch, env)
    assert plain.returncode == 0, plain.stdout + plain.stderr


def test_a_shard_rerun_refused_by_its_predecessor_discards_its_own_acceptance(accepted_gate):
    repo, scratch, env = accepted_gate
    for k in (1, 2):
        assert run_hunt(repo, scratch, env, "--shard", f"{k}/2").returncode == 0
    run_dir = paths(repo, env)["run"]
    (run_dir / "phase1-sweep.md").unlink()
    refused = run_hunt(repo, scratch, env, "--shard", "1/2")
    assert refused.returncode == 13, refused.stdout + refused.stderr
    assert not (run_dir / "phase2-hunt.1.md").exists()
    assert not (run_dir / "phase2-hunt.1.md.stamp").exists()
    assert not (run_dir / "hunt.1.launch").exists()
    assert (run_dir / "phase2-hunt.2.md.stamp").exists()


def test_a_leftover_shard_environment_value_never_refuses_another_command(gate):
    repo, scratch, env = gate
    env = {**env, "ADVERSARIAL_SHARD": "1/2"}
    listed = run_script("paths", "--repo", str(repo), "--base", "HEAD", env=env)
    assert listed.returncode == 0, listed.stdout + listed.stderr
    again = run_preflight(repo, scratch, env)
    assert again.returncode == 0, again.stdout + again.stderr


def test_cleanup_names_the_command_and_the_flag(gate):
    repo, scratch, env = gate
    made = run_script(
        "checkout", "--repo", str(repo), "--base", "HEAD", "--scratch", str(scratch), env=env,
    )
    assert made.returncode == 0, made.stdout + made.stderr
    checkout = [line for line in made.stdout.splitlines() if line.startswith("/")]
    assert checkout, made.stdout + made.stderr
    refused = run_script("cleanup", "--shard", "1/2", checkout[0], "--repo", str(repo), env=env)
    assert refused.returncode == 2, refused.stdout + refused.stderr
    lines = [line for line in refused.stderr.splitlines() if line.strip()]
    assert len(lines) == 1, refused.stderr
    assert "--shard is not valid for the cleanup command" in lines[0], refused.stderr
    assert run_script("cleanup", checkout[0], "--repo", str(repo), env=env).returncode == 0


def test_a_corrupt_plan_is_refused_instead_of_waiving_the_hunt_requirement(accepted_gate):
    repo, scratch, env = accepted_gate
    run_dir = paths(repo, env)["run"]
    plan_file(run_dir).write_text("n=x\n")
    arbitrate = run_arbitrate(repo, scratch, env)
    assert arbitrate.returncode == 13, arbitrate.stdout + arbitrate.stderr
    assert "hunt plan" in arbitrate.stderr, arbitrate.stderr
    listed = run_script("paths", "--repo", str(repo), "--base", "HEAD", env=env)
    assert listed.returncode == 13, listed.stdout + listed.stderr


def test_a_plan_with_a_wrong_artifact_path_is_refused(accepted_gate):
    repo, scratch, env = accepted_gate
    run_dir = paths(repo, env)["run"]
    plan_file(run_dir).write_text(
        f"n=2\n{run_dir}/phase2-hunt.1.md\n{run_dir}/elsewhere.md\n"
    )
    arbitrate = run_arbitrate(repo, scratch, env)
    assert arbitrate.returncode == 13, arbitrate.stdout + arbitrate.stderr
    assert "hunt plan" in arbitrate.stderr, arbitrate.stderr


def test_a_plan_with_a_missing_artifact_path_is_refused(accepted_gate):
    repo, scratch, env = accepted_gate
    run_dir = paths(repo, env)["run"]
    plan_file(run_dir).write_text(f"n=3\n{run_dir}/phase2-hunt.1.md\n{run_dir}/phase2-hunt.2.md\n")
    arbitrate = run_arbitrate(repo, scratch, env)
    assert arbitrate.returncode == 13, arbitrate.stdout + arbitrate.stderr
    assert "hunt plan" in arbitrate.stderr, arbitrate.stderr


def test_a_run_refused_by_a_missing_predecessor_leaves_no_launch_and_no_plan(gate):
    repo, scratch, env = gate
    run_dir = paths(repo, env)["run"]
    refused = run_hunt(repo, scratch, env)
    assert refused.returncode == 13, refused.stdout + refused.stderr
    assert not (run_dir / "hunt.launch").exists()
    assert not (run_dir / "hunt.binding").exists()
    assert not (run_dir / "hunt.primary").exists()
    sharded = run_hunt(repo, scratch, env, "--shard", "1/2")
    assert sharded.returncode == 13, sharded.stdout + sharded.stderr
    assert not plan_file(run_dir).exists()


def test_an_unsharded_attempt_that_left_only_its_agent_streams_refuses_a_shard(accepted_gate):
    repo, scratch, env = accepted_gate
    failed = run_hunt(repo, scratch, env, agent=EXIT_AGENT)
    assert failed.returncode == 15, failed.stdout + failed.stderr
    run_dir = paths(repo, env)["run"]
    assert (run_dir / "hunt-agent.err").exists() or (run_dir / "hunt-agent.log").exists()
    sharded = run_hunt(repo, scratch, env, "--shard", "1/2")
    assert sharded.returncode == 2, sharded.stdout + sharded.stderr
    assert not plan_file(run_dir).exists()


def test_a_preflight_rerun_discards_probe_logs_too(accepted_gate):
    repo, scratch, env = accepted_gate
    run_dir = paths(repo, env)["run"]
    (run_dir / "hunt-probe.log").write_text("stale\n")
    (run_dir / "hunt.1-probe.log").write_text("stale\n")
    again = run_preflight(repo, scratch, env)
    assert again.returncode == 0, again.stdout + again.stderr
    assert not (run_dir / "hunt-probe.log").exists()
    assert not (run_dir / "hunt.1-probe.log").exists()


def test_every_phase_status_and_diagnosis_line_carries_the_shard(accepted_gate, tmp_path):
    repo, scratch, env = accepted_gate
    failed = run_hunt(repo, scratch, env, "--shard", "1/2", agent=BLIND_AGENT)
    assert failed.returncode == 17, failed.stdout + failed.stderr
    heads = [line for line in failed.stderr.splitlines()
             if line.startswith("adversarial-pipeline: phase=hunt")]
    assert heads, failed.stderr
    for line in heads:
        assert [field for field in line.split() if field.startswith("shard=")] == ["shard=1/2"], line
    reason = [line for line in failed.stderr.splitlines() if "reason:" in line]
    assert reason, failed.stderr
    for line in reason:
        assert [field for field in line.split() if field.startswith("shard=")] == ["shard=1/2"], line

    plain_repo, plain_scratch, plain_env = accepted_hunt_gate(tmp_path / "plain-status")
    plain_failed = run_hunt(plain_repo, plain_scratch, plain_env, agent=BLIND_AGENT)
    assert plain_failed.returncode == 17, plain_failed.stdout + plain_failed.stderr
    plain_heads = [line for line in plain_failed.stderr.splitlines()
                   if line.startswith("adversarial-pipeline: phase=hunt")]
    assert plain_heads, plain_failed.stderr
    for line in plain_heads:
        assert [field for field in line.split() if field.startswith("shard=")] == [], line
