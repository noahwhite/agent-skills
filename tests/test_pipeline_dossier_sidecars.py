"""Every completed dossier write leaves a size sidecar in the run directory.

SKL-89. A dossier write that completes, on the `run` path or on the `dossier` command, writes
`$RUN_DIR/<phase>.dossier`: one `path=<absolute dossier path>` line, one `bytes=<n>` line
(`LC_ALL=C wc -c` of that dossier), and one `excluded <path> reason=<reason>` line per path the
exclusion step left out of that dossier's diff, the path escaped as the truncation marker escapes
its path. `begin_phase` removes the phase's sidecar, `invalidate_downstream` removes the sidecar of
every phase it discards, and the `dossier` command's exit trap removes a sidecar its invocation
wrote. An invocation that exits before `begin_phase` removes nothing. A sidecar that cannot be
written prints one `WARNING:` line and changes no exit status, completion line or acceptance.

Every test seeds a base commit and a head commit and reviews the head against its base, on both
flows: `run`, and `dossier` followed by `record`.
"""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "adversarial-review-pipeline" / "scripts" / "run-adversarial-pipeline.sh"
BASE_REF = "base"
PHASES = ("sweep", "hunt", "arbitrate")
FLOWS = ("run", "dossier")

# Host git configuration and repository-locating variables never reach a fixture.
GIT_ISOLATION = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
GIT_LOCATORS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
                "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_EXTERNAL_DIFF")


def isolated_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("ADVERSARIAL_") and k not in GIT_LOCATORS}
    return {**env, **GIT_ISOLATION}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True, env=isolated_env(),
    ).stdout.strip()


def make_repo(tmp_path: Path, base: dict[str, str], head: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "agent-skills@example.com")
    git(repo, "config", "user.name", "agent-skills")
    git(repo, "config", "commit.gpgsign", "false")
    git(repo, "config", "tag.gpgsign", "false")
    for files, message in ((base, "base"), (head, "head")):
        for rel, content in files.items():
            path = repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
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


def make_gate(tmp_path: Path, repo: Path) -> dict:
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    (tmp_path / "runtime-tmp").mkdir()
    env = {**isolated_env(), "TMPDIR": str(tmp_path / "runtime-tmp")}
    spec = tmp_path / "spec.md"
    spec.write_text("Story SKL-89: size sidecars.\n")
    g = {"repo": repo, "scratch": scratch, "env": env, "spec": spec, "tmp": tmp_path}
    preflight = run_script("preflight", "--repo", str(repo), "--base", BASE_REF, "--test-cmd", "true",
                           "--scratch", str(scratch), env=env)
    assert preflight.returncode == 0, preflight.stdout + preflight.stderr
    return g


@pytest.fixture
def gate(tmp_path):
    repo = make_repo(tmp_path, {"app.py": "def total(items):\n    return sum(items)\n"},
                     {"app.py": "def total(items):\n    return sum(i for i in items if i > 0)\n"})
    return make_gate(tmp_path, repo)


def common(g: dict) -> list[str]:
    return ["--repo", str(g["repo"]), "--base", BASE_REF, "--spec", str(g["spec"]),
            "--scratch", str(g["scratch"])]


def artifact_paths(g: dict) -> dict[str, Path]:
    listed = run_script("paths", "--repo", str(g["repo"]), "--base", BASE_REF, env=g["env"])
    assert listed.returncode == 0, listed.stdout + listed.stderr
    return {name: Path(path) for name, _, path in
            (line.partition(" ") for line in listed.stdout.splitlines()) if path}


def run_dir(g: dict) -> Path:
    return artifact_paths(g)["run"]


def sidecar(g: dict, phase: str) -> Path:
    return run_dir(g) / f"{phase}.dossier"


def line_value(text: str, prefix: str) -> str:
    lines = [line for line in text.splitlines() if line.startswith(prefix)]
    assert len(lines) == 1, f"expected exactly one {prefix!r} line, got {lines}"
    return lines[0][len(prefix):]


# The fake agent records the dossier path it was handed and writes a minimal accepted report.
AGENT = (
    's="$ADVERSARIAL_SESSION_SCRATCH/seen-$PHASE_NAME"; mkdir -p "$s"; '
    'printf "%s" {prompt_file} > "$s/path"; cp {prompt_file} "$s/dossier.md"; '
    'printf "REVIEW-RAN: yes\\nreport\\n" > {output_file}'
)


def run_phase(g: dict, phase: str, *extra: str, env: dict[str, str] | None = None):
    return run_script("run", phase, *common(g), "--agent-cmd", AGENT, *extra,
                      env={**(env or g["env"]), "PHASE_NAME": phase})


def record(g: dict, phase: str, *extra: str) -> subprocess.CompletedProcess:
    artifact_paths(g)[phase].write_text(f"REVIEW-RAN: yes\n{phase} report\n")
    return run_script("record", phase, "--repo", str(g["repo"]), "--base", BASE_REF,
                      "--spec", str(g["spec"]), *extra, env=g["env"])


def cleanup(g: dict, checkout: Path) -> None:
    result = run_script("cleanup", str(checkout), "--repo", str(g["repo"]), env=g["env"])
    assert result.returncode == 0, result.stdout + result.stderr


def complete(g: dict, flow: str, phase: str, *extra: str) -> Path:
    """Runs the phase to acceptance on the given flow and returns the dossier path it wrote."""
    if flow == "run":
        result = run_phase(g, phase, *extra)
        assert result.returncode == 0, result.stdout + result.stderr
        return Path((g["scratch"] / f"seen-{phase}" / "path").read_text())
    result = run_script("dossier", phase, *common(g), *extra, env=g["env"])
    assert result.returncode == 0, result.stdout + result.stderr
    dossier = Path(result.stdout.strip().splitlines()[-1])
    recorded = record(g, phase, *extra)
    assert recorded.returncode == 0, recorded.stdout + recorded.stderr
    cleanup(g, Path(line_value(result.stderr, "CHECKOUT: ")))
    return dossier


def expected_sidecar(dossier: Path, excluded: list[bytes] = ()) -> bytes:
    size = len(dossier.read_bytes())
    return (b"path=" + os.fsencode(dossier) + b"\n" + b"bytes=%d\n" % size
            + b"".join(b"excluded " + line + b"\n" for line in excluded))


def check_sidecar(g: dict, phase: str, dossier: Path, excluded: list[bytes] = ()) -> bytes:
    assert dossier.is_absolute(), dossier
    assert dossier.name == f"{phase}-dossier.md", dossier
    side = sidecar(g, phase)
    assert side.is_file(), f"no {phase} sidecar at {side}"
    content = side.read_bytes()
    assert content == expected_sidecar(dossier, excluded), content
    return content


def present(g: dict) -> list[str]:
    return [phase for phase in PHASES if sidecar(g, phase).exists()]


# --- content and lifecycle on both flows -----------------------------------------------------------

@pytest.mark.parametrize("flow", FLOWS)
def test_the_sweep_leaves_its_sidecar(gate, flow):
    dossier = complete(gate, flow, "sweep")
    check_sidecar(gate, "sweep", dossier)
    assert present(gate) == ["sweep"]


@pytest.mark.parametrize("flow", FLOWS)
def test_the_hunt_adds_its_sidecar_and_never_remeasures_the_sweep(gate, flow):
    sweep = complete(gate, flow, "sweep")
    before = check_sidecar(gate, "sweep", sweep)
    hunt = complete(gate, flow, "hunt")
    check_sidecar(gate, "hunt", hunt)
    assert sidecar(gate, "sweep").read_bytes() == before, "the hunt invocation rewrote the sweep sidecar"
    assert present(gate) == ["sweep", "hunt"]


@pytest.mark.parametrize("flow", FLOWS)
def test_a_no_sweep_hunt_and_arbitrate_leave_their_sidecars(gate, flow):
    hunt = complete(gate, flow, "hunt", "--no-sweep")
    arbitrate = complete(gate, flow, "arbitrate", "--no-sweep")
    check_sidecar(gate, "hunt", hunt)
    check_sidecar(gate, "arbitrate", arbitrate)
    assert present(gate) == ["hunt", "arbitrate"]


@pytest.mark.parametrize("flow", FLOWS)
def test_a_sweep_rerun_discards_the_hunt_and_arbitrate_sidecars(gate, flow):
    first = {phase: complete(gate, flow, phase) for phase in PHASES}
    assert present(gate) == list(PHASES)
    again = complete(gate, flow, "sweep")
    assert again != first["sweep"], "the re-run reused the earlier dossier"
    check_sidecar(gate, "sweep", again)
    assert present(gate) == ["sweep"]


# --- excluded lines: one per path, the reason the exclusion step carried ---------------------------

@pytest.fixture
def excluding_gate(tmp_path):
    """A repository that opts in through a .gitattributes attribute and an .adversarial-exclude entry."""
    repo = make_repo(
        tmp_path,
        {"app.py": "x = 1\n",
         ".gitattributes": "gen/** linguist-generated\nvendor/** linguist-vendored\n",
         ".adversarial-exclude": "# fixtures\nfixtures/*\n"},
        {"app.py": "x = 2\n",
         "gen/out.txt": "generated\n",
         "vendor/lib.js": "vendored\n",
         "fixtures/café.json": "{}\n",
         "fixtures/plain.json": "{}\n",
         'fixtures/q"uote\ttab.json': "{}\n"},
    )
    return make_gate(tmp_path, repo)


EXPECTED_EXCLUDED = [
    "fixtures/café.json reason=glob:fixtures/*".encode(),
    b"fixtures/plain.json reason=glob:fixtures/*",
    b'"fixtures/q\\"uote\\ttab.json" reason=glob:fixtures/*',
    b"gen/out.txt reason=linguist-generated",
    b"vendor/lib.js reason=linguist-vendored",
]


@pytest.mark.parametrize("flow", FLOWS)
def test_each_exclusion_reason_has_its_line(excluding_gate, flow):
    g = excluding_gate
    dossiers = {phase: complete(g, flow, phase) for phase in PHASES}
    for phase in ("sweep", "hunt"):
        check_sidecar(g, phase, dossiers[phase], EXPECTED_EXCLUDED)
        rows = dossiers[phase].read_text().split("===== EXCLUDED", 1)[1].split("=====\n", 1)[1]
        rows = rows.split("\n\n", 1)[0].splitlines()
        assert len(rows) == len(EXPECTED_EXCLUDED), rows
    check_sidecar(g, "arbitrate", dossiers["arbitrate"])


# --- writes that do not complete leave no sidecar ---------------------------------------------------

def fake_bin_env(g: dict, name: str, script: str) -> dict[str, str]:
    fakebin = g["tmp"] / f"fakebin-{name}"
    fakebin.mkdir(exist_ok=True)
    wrapper = fakebin / name
    wrapper.write_text("#!/usr/bin/env bash\n" + script)
    wrapper.chmod(0o755)
    return {**g["env"], "PATH": f"{fakebin}:{g['env']['PATH']}"}


def failing_git_env(g: dict, first: str, second: str) -> dict[str, str]:
    """A git that fails (exit 3) when called with `first second`, and is real git otherwise."""
    real_git = subprocess.run(["bash", "-c", "command -v git"], capture_output=True,
                              text=True, check=True).stdout.strip()
    return fake_bin_env(g, "git", (
        f'if [ "$1" = {first} ] && [ "$2" = {second} ]; then echo "refused" >&2; exit 3; fi\n'
        f'exec "{real_git}" "$@"\n'))


@pytest.mark.parametrize("flow", FLOWS)
def test_a_failed_dossier_write_leaves_no_sidecar(gate, flow):
    complete(gate, flow, "sweep")
    env = failing_git_env(gate, "diff", "--stat")
    if flow == "run":
        result = run_phase(gate, "sweep", env=env)
    else:
        result = run_script("dossier", "sweep", *common(gate), env=env)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "could not write the sweep dossier" in result.stderr, result.stderr
    assert present(gate) == []


def test_a_failed_checkout_on_the_dossier_command_leaves_no_sidecar(gate):
    complete(gate, "dossier", "sweep")
    result = run_script("dossier", "sweep", *common(gate), env=failing_git_env(gate, "worktree", "add"))
    assert result.returncode != 0, result.stdout + result.stderr
    assert "could not create the throwaway checkout" in result.stderr, result.stderr
    assert present(gate) == []


def test_a_dossier_write_the_exit_trap_undoes_leaves_no_sidecar(gate):
    """With stdout closed the dossier is written but its path never reaches the caller."""
    result = subprocess.run(
        ["bash", "-c", 'exec >&-; exec bash "$0" "$@"', str(SCRIPT), "dossier", "sweep", *common(gate)],
        stderr=subprocess.PIPE, text=True, env=gate["env"], cwd=str(ROOT), timeout=120,
    )
    assert result.returncode != 0, result.stderr
    assert "could not write the sweep dossier" in result.stderr, result.stderr
    assert present(gate) == []


# --- invocations that exit before begin_phase remove nothing ----------------------------------------

def test_a_dossier_refused_by_its_predecessor_check_keeps_the_earlier_sidecar(gate):
    complete(gate, "dossier", "sweep")
    complete(gate, "dossier", "hunt")
    before = {phase: sidecar(gate, phase).read_bytes() for phase in ("sweep", "hunt")}
    other = gate["tmp"] / "other-spec.md"
    other.write_text("A different story.\n")
    refused = run_script("dossier", "hunt", "--repo", str(gate["repo"]), "--base", BASE_REF,
                         "--spec", str(other), "--scratch", str(gate["scratch"]), env=gate["env"])
    assert refused.returncode == 13, refused.stdout + refused.stderr
    assert {phase: sidecar(gate, phase).read_bytes() for phase in ("sweep", "hunt")} == before


def test_a_run_refused_for_a_missing_agent_cmd_keeps_the_earlier_sidecar(gate):
    complete(gate, "run", "sweep")
    before = sidecar(gate, "sweep").read_bytes()
    refused = run_script("run", "sweep", *common(gate), env=gate["env"])
    assert refused.returncode == 2, refused.stdout + refused.stderr
    assert "--agent-cmd" in refused.stderr, refused.stderr
    assert sidecar(gate, "sweep").read_bytes() == before


# --- a sidecar that cannot be written only warns ----------------------------------------------------

@pytest.mark.parametrize("flow", FLOWS)
def test_a_sidecar_write_failure_warns_and_changes_no_outcome(gate, flow):
    env = fake_bin_env(gate, "wc", 'echo "wc: refused" >&2\nexit 1\n')
    if flow == "run":
        result = run_phase(gate, "sweep", env=env)
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stderr.splitlines()[-1].endswith(" exit=0"), result.stderr
    else:
        result = run_script("dossier", "sweep", *common(gate), env=env)
        assert result.returncode == 0, result.stdout + result.stderr
        recorded = record(gate, "sweep")
        assert recorded.returncode == 0, recorded.stdout + recorded.stderr
        cleanup(gate, Path(line_value(result.stderr, "CHECKOUT: ")))
    warnings = [line for line in result.stderr.splitlines() if line.startswith("WARNING:")]
    assert len(warnings) == 1 and "sweep" in warnings[0], result.stderr
    assert "wc: refused" not in result.stderr, result.stderr
    assert present(gate) == []
    # the sweep stays accepted: the hunt starts from it
    hunt = complete(gate, flow, "hunt")
    check_sidecar(gate, "hunt", hunt)


# --- sidecars never enter the binding or the acceptance ---------------------------------------------

@pytest.mark.parametrize("flow", FLOWS)
def test_the_sidecars_alone_change_neither_the_binding_nor_acceptance(gate, flow):
    for phase in ("sweep", "hunt"):
        complete(gate, flow, phase)
    complete(gate, flow, "arbitrate")
    binding = (run_dir(gate) / "arbitrate.binding").read_text()
    stamps = {phase: Path(f"{artifact_paths(gate)[phase]}.stamp").read_text() for phase in PHASES}
    sidecar(gate, "sweep").write_text("path=/elsewhere\nbytes=1\n")
    sidecar(gate, "hunt").unlink()
    complete(gate, flow, "arbitrate")
    assert (run_dir(gate) / "arbitrate.binding").read_text() == binding
    assert {phase: Path(f"{artifact_paths(gate)[phase]}.stamp").read_text()
            for phase in PHASES} == stamps
