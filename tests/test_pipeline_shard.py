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
        "run", "preflight", "suite_log", "sweep", "hunt.1", "hunt.2", "arbitrate",
        "reuse_hits", "reuse_misses", "dossier_sizes",
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
    for extra in (("--shard", "1/3"), ("--shard", "2/3"), (), ("--shard", "1/1")):
        result = run_hunt(repo, scratch, env, *extra)
        assert result.returncode == 2, (extra, result.stdout + result.stderr)
        assert plan_file(run_dir).read_bytes() == plan_before, extra
        assert Path(f"{files['hunt.1']}.stamp").read_bytes() == stamp_before, extra
        assert (run_dir / "phase2-hunt.1.md").exists(), extra


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
    assert "shard=" not in failed.stderr.replace("shard=1/2", ""), failed.stderr
    arbitrate = run_arbitrate(repo, scratch, env)
    assert arbitrate.returncode == 13, arbitrate.stdout + arbitrate.stderr
    assert "1/2" in arbitrate.stderr and "hunt" in arbitrate.stderr, arbitrate.stderr

    plain_repo, plain_scratch, plain_env = accepted_hunt_gate(tmp_path / "unsharded")
    plain_failed = run_hunt(plain_repo, plain_scratch, plain_env, agent=BLIND_AGENT)
    assert plain_failed.returncode == failed.returncode, plain_failed.stdout + plain_failed.stderr
    assert "shard=" not in plain_failed.stderr, plain_failed.stderr


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


def test_every_phase_status_and_diagnosis_line_carries_the_shard(accepted_gate):
    repo, scratch, env = accepted_gate
    failed = run_hunt(repo, scratch, env, "--shard", "1/2", agent=BLIND_AGENT)
    assert failed.returncode == 17, failed.stdout + failed.stderr
    heads = [line for line in failed.stderr.splitlines()
             if line.startswith("adversarial-pipeline: phase=hunt")]
    assert heads, failed.stderr
    for line in heads:
        assert "shard=1/2" in line, line
    reason = [line for line in failed.stderr.splitlines() if "reason:" in line]
    assert reason, failed.stderr
    for line in reason:
        assert "shard=1/2" in line, line


# --- A sharded run and the identical-tree reuse: its ordinary sweep still donates -----------------

def test_a_sharded_run_whose_arbitration_lapsed_does_not_block_the_hunt(tmp_path):
    """A shard set never produced one hunt artifact, so it is no lapsed donor for a fresh hunt."""
    repo, scratch, env = new_gate(tmp_path)
    for k in (1, 2):
        hunt = run_hunt(repo, scratch, env, "--shard", f"{k}/2", "--no-sweep")
        assert hunt.returncode == 0, hunt.stdout + hunt.stderr
    arb = run_arbitrate(repo, scratch, env, "--no-sweep")
    assert arb.returncode == 0, arb.stdout + arb.stderr
    run_dir = paths(repo, env)["run"]
    history = (run_dir / "arbitrate.accepted.log").read_text()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                          capture_output=True, text=True, env=env).stdout.strip()
    accepted = [line for line in history.splitlines() if f"head={head}" in line]
    assert accepted, history
    assert "spec=none" in accepted[0] and "no_sweep=1" in accepted[0], accepted[0]
    (run_dir / "phase3-arbitration.md.stamp").unlink()
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "same tree"], cwd=repo,
                   check=True, capture_output=True, env=env)
    pre = run_preflight(repo, scratch, env)
    assert pre.returncode == 0, pre.stdout + pre.stderr
    marker = tmp_path / "hunt.launched"
    launched = (f"touch {marker}; {{ printf \"REVIEW-RAN: yes\\nhunt ok\\n\"; }} > {{output_file}}")
    again = run_hunt(repo, scratch, env, "--no-sweep", agent=launched)
    assert again.returncode == 0, again.stdout + again.stderr
    assert marker.exists(), "the fresh hunt was refused as a lapse of a sharded run"
    assert "acceptance lapsed" not in again.stderr, again.stderr


def test_a_sharded_hunt_prints_one_reuse_miss_and_paths_counts_it(accepted_gate):
    repo, scratch, env = accepted_gate
    hunt = run_hunt(repo, scratch, env, "--shard", "1/2")
    assert hunt.returncode == 0, hunt.stdout + hunt.stderr
    lines = [line for line in hunt.stderr.splitlines() if line.startswith("reuse: ")]
    assert lines == ["reuse: miss reason=no accepted run"], hunt.stderr
    listed = run_script("paths", "--repo", str(repo), "--base", "HEAD", env=env)
    assert listed.returncode == 0, listed.stdout + listed.stderr
    # One miss each for the preflight, the sweep and the sharded hunt.
    assert "reuse_misses 3" in listed.stdout, listed.stdout


def test_a_sharded_runs_sweep_is_reused_at_an_identical_tree_and_delta_resolves_it(tmp_path):
    repo, scratch, env = new_gate(tmp_path)
    sweep = run_sweep(repo, scratch, env)
    assert sweep.returncode == 0, sweep.stdout + sweep.stderr
    for k in (1, 2):
        hunt = run_hunt(repo, scratch, env, "--shard", f"{k}/2")
        assert hunt.returncode == 0, hunt.stdout + hunt.stderr
    arb = run_arbitrate(repo, scratch, env)
    assert arb.returncode == 0, arb.stdout + arb.stderr
    accepted_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                                   capture_output=True, text=True, env=env).stdout.strip()
    # A new head with the identical tree: the sharded run's arbitration accepts over its shard set,
    # so its ordinary sweep is reusable even though the sharded hunt itself is not.
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "same tree"], cwd=repo,
                   check=True, capture_output=True, env=env)
    pre = run_preflight(repo, scratch, env)
    assert pre.returncode == 0, pre.stdout + pre.stderr
    marker = tmp_path / "sweep.launched"
    launched = (f"touch {marker}; {{ printf \"REVIEW-RAN: yes\\nsweep ok\\n\"; }} > {{output_file}}")
    again = run_sweep(repo, scratch, env, agent=launched)
    assert again.returncode == 0, again.stdout + again.stderr
    assert not marker.exists(), "the sweep was launched instead of reused from the sharded run"
    reuse_lines = [line for line in again.stderr.splitlines() if line.startswith("reuse: hit ")]
    assert len(reuse_lines) == 1, again.stderr
    # And the sharded run is a valid delta base: an accepted ancestor of the new head.
    delta = run_script("paths", "--repo", str(repo), "--delta", env=env)
    assert delta.returncode == 0, delta.stdout + delta.stderr
    run_dir = Path(next(line.split(" ", 1)[1] for line in delta.stdout.splitlines()
                        if line.startswith("run ")))
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                          capture_output=True, text=True, env=env).stdout.strip()
    assert run_dir.name.endswith(f"-{head}"), run_dir
    assert accepted_head in run_dir.name, run_dir
