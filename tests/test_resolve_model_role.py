"""The model-role resolver: shared/resolve-model-role.py.

Every case runs the resolver as a subprocess, the way its callers do, with HOME and
AGENT_SKILLS_PROFILE pointed at fixtures under tmp_path and no provider credential in the
environment, so neither this repository's own profile nor the user's is ever read.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RESOLVER = ROOT / "shared" / "resolve-model-role.py"

PROFILE = """\
version: 1
review:
  reviewer:
    name: Reviewer
    runtime: codex
    model: gpt-test
  adjudicator:
    name: Adjudicator
    runtime: opencode
    model: provider/adjudicator-model
  pre_pr:
    arbiter:
      name: Arbiter
      runtime: claude-code
      model: sonnet
    hunter:
      name: Hunter
      runtime: codex
      model: gpt-test
      command: this text is ignored on a codex runtime
refinement:
  reviewers:
    - name: First
      runtime: command
      model: first/model
      command: first-cli --model first/model --file "{prompt_file}"
    - name: Second
      runtime: command
      command: second-cli --model second/model --file "{prompt_file}" > "{output_file}"
    - name: Third
      command: third-cli --file "{prompt_file}"
"""


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def base_env(home: Path) -> dict[str, str]:
    """A clean environment: no provider credential, no profile override, HOME at a fixture."""
    return {"PATH": os.environ["PATH"], "HOME": str(home), "LC_ALL": "C"}


@pytest.fixture
def home(tmp_path: Path) -> Path:
    h = tmp_path / "home"
    h.mkdir()
    return h


@pytest.fixture
def outside(tmp_path: Path) -> Path:
    """A working directory that is not inside any git work tree."""
    d = tmp_path / "outside"
    d.mkdir()
    return d


def resolve(*args: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RESOLVER), *args],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=60,
    )


def lines(role: str, runtime: str, model: str, source: Path, command: str | None = None) -> str:
    out = f"role: {role}\nruntime: {runtime}\nmodel: {model}\nsource: {source}\n"
    if command is not None:
        out += f"command: {command}\n"
    return out


def assert_fails(res: subprocess.CompletedProcess, *fragments: str) -> str:
    assert res.returncode == 16, res.stderr
    assert res.stdout == ""
    err = res.stderr.splitlines()
    assert len(err) == 1, res.stderr
    for fragment in fragments:
        assert fragment in err[0], err[0]
    return err[0]


# --- Discovery -----------------------------------------------------------------------------


def test_env_profile_wins_over_repo_and_home(tmp_path, home):
    repo = git_repo(tmp_path / "repo")
    env_profile = write(tmp_path / "env.yaml", PROFILE)
    write(repo / ".agent-skills" / "profile.yaml", PROFILE)
    write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE)
    env = base_env(home) | {"AGENT_SKILLS_PROFILE": str(env_profile)}
    res = resolve("--role", "review.reviewer", cwd=repo, env=env)
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.reviewer", "codex", "gpt-test", env_profile)
    assert res.stderr == ""


def test_repo_profile_wins_over_home(tmp_path, home):
    repo = git_repo(tmp_path / "repo")
    repo_profile = write(repo / ".agent-skills" / "profile.yaml", PROFILE)
    write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE)
    res = resolve("--role", "review.reviewer", cwd=repo, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.reviewer", "codex", "gpt-test", repo_profile)


def test_home_profile_is_the_last_location(tmp_path, home, outside):
    home_profile = write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE)
    res = resolve("--role", "review.reviewer", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.reviewer", "codex", "gpt-test", home_profile)


def test_an_env_path_that_does_not_exist_is_not_a_match(tmp_path, home, outside):
    home_profile = write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE)
    env = base_env(home) | {"AGENT_SKILLS_PROFILE": str(tmp_path / "absent.yaml")}
    res = resolve("--role", "review.reviewer", cwd=outside, env=env)
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.reviewer", "codex", "gpt-test", home_profile)


def test_repo_option_names_the_repository_from_outside_it(tmp_path, home, outside):
    repo = git_repo(tmp_path / "repo")
    repo_profile = write(repo / ".agent-skills" / "profile.yaml", PROFILE)
    write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE)
    res = resolve("--role", "review.reviewer", "--repo", str(repo), cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.reviewer", "codex", "gpt-test", repo_profile)


def test_a_repo_option_that_is_not_a_directory_fails_without_falling_through(tmp_path, home, home_profile, outside):
    line = assert_fails(
        resolve("--role", "review.reviewer", "--repo", str(tmp_path / "typo"), cwd=outside, env=base_env(home)),
        "review.reviewer", str(tmp_path / "typo"), "not a directory",
    )
    assert str(home_profile) not in line


def test_a_subdirectory_of_the_repository_reads_the_repository_root(tmp_path, home):
    repo = git_repo(tmp_path / "repo")
    repo_profile = write(repo / ".agent-skills" / "profile.yaml", PROFILE)
    sub = repo / "a" / "b"
    sub.mkdir(parents=True)
    write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE)
    res = resolve("--role", "review.reviewer", cwd=sub, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.reviewer", "codex", "gpt-test", repo_profile)


def test_the_working_directory_profile_is_not_read_when_repo_names_another(tmp_path, home):
    cwd = git_repo(tmp_path / "cwd-repo")
    write(cwd / ".agent-skills" / "profile.yaml", PROFILE.replace("gpt-test", "from-cwd"))
    other = git_repo(tmp_path / "other")
    home_profile = write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE)
    res = resolve("--role", "review.reviewer", "--repo", str(other), cwd=cwd, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.reviewer", "codex", "gpt-test", home_profile)


def test_a_non_repository_working_directory_profile_is_not_read(tmp_path, home, outside):
    write(outside / ".agent-skills" / "profile.yaml", PROFILE.replace("gpt-test", "from-cwd"))
    home_profile = write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE)
    res = resolve("--role", "review.reviewer", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.reviewer", "codex", "gpt-test", home_profile)


def test_the_resolver_installation_directory_profile_is_not_read(tmp_path, home, outside):
    install = tmp_path / "install"
    copy = install / "scripts" / "resolve-model-role.py"
    copy.parent.mkdir(parents=True)
    shutil.copyfile(RESOLVER, copy)
    write(install / ".agent-skills" / "profile.yaml", PROFILE.replace("gpt-test", "from-install"))
    write(install / "scripts" / ".agent-skills" / "profile.yaml", PROFILE.replace("gpt-test", "from-install"))
    home_profile = write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE)
    res = subprocess.run(
        [sys.executable, str(copy), "--role", "review.reviewer"],
        cwd=outside, env=base_env(home), capture_output=True, text=True, timeout=60,
    )
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.reviewer", "codex", "gpt-test", home_profile)


# --- Output --------------------------------------------------------------------------------


@pytest.fixture
def home_profile(home: Path) -> Path:
    return write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE)


def test_a_normal_entry_prints_no_command_line(home, home_profile, outside):
    res = resolve("--role", "review.pre_pr.arbiter", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.pre_pr.arbiter", "claude-code", "sonnet", home_profile)
    assert "command:" not in res.stdout


def test_a_command_on_a_model_runtime_is_ignored(home, home_profile, outside):
    res = resolve("--role", "review.pre_pr.hunter", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.pre_pr.hunter", "codex", "gpt-test", home_profile)


def test_a_command_entry_with_a_model_prints_both(home, home_profile, outside):
    res = resolve("--role", "refinement.reviewers[0]", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines(
        "refinement.reviewers[0]", "command", "first/model", home_profile,
        'first-cli --model first/model --file "{prompt_file}"',
    )


def test_a_command_entry_without_a_model_is_unresolved_and_prints_its_command(home, home_profile, outside):
    res = resolve("--role", "profile.refinement.reviewers[1]", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines(
        "refinement.reviewers[1]", "command", "unresolved", home_profile,
        'second-cli --model second/model --file "{prompt_file}" > "{output_file}"',
    )


def test_a_command_without_a_runtime_resolves_as_a_command_entry(home, home_profile, outside):
    res = resolve("--role", "refinement.reviewers[2]", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines(
        "refinement.reviewers[2]", "command", "unresolved", home_profile, 'third-cli --file "{prompt_file}"',
    )


def test_the_profile_prefix_is_accepted_and_stripped(home, home_profile, outside):
    res = resolve("--role", "profile.review.adjudicator", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.adjudicator", "opencode", "provider/adjudicator-model", home_profile)


def test_json_mode_prints_one_object(home, home_profile, outside):
    res = resolve("--role", "refinement.reviewers[1]", "--json", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout.count("\n") == 1
    assert list(json.loads(res.stdout).items()) == [
        ("role", "refinement.reviewers[1]"),
        ("runtime", "command"),
        ("model", "unresolved"),
        ("source", str(home_profile)),
        ("command", 'second-cli --model second/model --file "{prompt_file}" > "{output_file}"'),
    ]


def test_json_mode_omits_command_when_the_entry_sets_none(home, home_profile, outside):
    res = resolve("--role", "review.reviewer", "--json", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert json.loads(res.stdout) == {
        "role": "review.reviewer", "runtime": "codex", "model": "gpt-test", "source": str(home_profile),
    }


def test_newlines_in_values_are_escaped_in_text_mode_and_kept_in_json(home, outside):
    profile = write(
        home / ".config" / "agent-skills" / "profile.yaml",
        'r:\n  name: R\n  runtime: command\n  command: "line one\\nline two\\\\n $(touch x)"\n',
    )
    res = resolve("--role", "r", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("r", "command", "unresolved", profile, "line one\\nline two\\\\n $(touch x)")
    res = resolve("--role", "r", "--json", cwd=outside, env=base_env(home))
    assert json.loads(res.stdout)["command"] == "line one\nline two\\n $(touch x)"
    assert not (outside / "x").exists()


# --- Fail closed ---------------------------------------------------------------------------


def test_no_profile_anywhere_fails(tmp_path, home, outside):
    env = base_env(home) | {"AGENT_SKILLS_PROFILE": str(tmp_path / "absent.yaml")}
    line = assert_fails(
        resolve("--role", "review.reviewer", cwd=outside, env=env),
        "review.reviewer", str(tmp_path / "absent.yaml"), str(home / ".config" / "agent-skills" / "profile.yaml"),
    )
    assert "no profile" in line
    assert ".agent-skills/profile.yaml" in line


def test_no_profile_names_the_unset_variable_and_the_repository_candidate(tmp_path, home):
    repo = git_repo(tmp_path / "repo")
    assert_fails(
        resolve("--role", "review.reviewer", cwd=repo, env=base_env(home)),
        "AGENT_SKILLS_PROFILE", str(repo / ".agent-skills" / "profile.yaml"),
        str(home / ".config" / "agent-skills" / "profile.yaml"),
    )


def test_invalid_yaml_fails_without_falling_through(tmp_path, home, home_profile):
    repo = git_repo(tmp_path / "repo")
    bad = write(repo / ".agent-skills" / "profile.yaml", "review: [unclosed\n  - x: : :\n")
    line = assert_fails(
        resolve("--role", "review.reviewer", cwd=repo, env=base_env(home)),
        "review.reviewer", str(bad), "not valid YAML",
    )
    assert str(home_profile) not in line, "the home profile below the selected one was never searched"


def test_a_profile_that_is_not_a_mapping_fails(tmp_path, home, home_profile, outside):
    bad = write(tmp_path / "list.yaml", "- one\n- two\n")
    env = base_env(home) | {"AGENT_SKILLS_PROFILE": str(bad)}
    assert_fails(resolve("--role", "review.reviewer", cwd=outside, env=env), str(bad), "not a mapping")


def test_an_unreadable_profile_fails(tmp_path, home, home_profile, outside):
    bad = tmp_path / "dir.yaml"
    bad.mkdir()
    env = base_env(home) | {"AGENT_SKILLS_PROFILE": str(bad)}
    assert_fails(resolve("--role", "review.reviewer", cwd=outside, env=env), str(bad), "unreadable")


@pytest.mark.parametrize(
    "role",
    ["review.missing", "review.pre_pr", "review.reviewer.model", "refinement.reviewers[3]", "review[0]", "a..b", ""],
)
def test_a_role_that_does_not_resolve_to_an_entry_fails(home, home_profile, outside, role):
    assert_fails(resolve("--role", role, cwd=outside, env=base_env(home)), str(home_profile), "role")


@pytest.mark.parametrize(
    ("entry", "reason"),
    [
        ("name: E\nmodel: m\n", "neither runtime nor command"),
        ("name: E\nruntime: gemini\nmodel: m\n", "runtime"),
        ("name: E\nruntime: codex\n", "no model"),
        ("name: E\nruntime: opencode\nmodel: ''\n", "no model"),
        ("name: E\nruntime: claude-code\ncommand: cli --model m\n", "no model"),
        ("name: E\nruntime: command\nmodel: m\n", "no command"),
        ("name: E\nruntime: command\ncommand: '   '\n", "no command"),
    ],
)
def test_an_unusable_entry_fails(home, outside, entry, reason):
    body = "role:\n" + "".join(f"  {line}\n" for line in entry.splitlines())
    profile = write(home / ".config" / "agent-skills" / "profile.yaml", body)
    line = assert_fails(resolve("--role", "role", cwd=outside, env=base_env(home)), "role", str(profile), reason)
    assert "unresolved" not in line


def test_the_runtimes_the_resolver_accepts_are_the_schema_runtimes(home, outside):
    schema = json.loads((ROOT / "profile" / "schema.json").read_text())
    runtimes = set(schema["$defs"]["agent"]["properties"]["runtime"]["enum"])
    assert runtimes
    for runtime in runtimes - {"command"}:
        write(home / ".config" / "agent-skills" / "profile.yaml", f"r:\n  name: R\n  runtime: {runtime}\n  model: m\n")
        res = resolve("--role", "r", cwd=outside, env=base_env(home))
        assert res.returncode == 0, (runtime, res.stderr)


# --- Dry run and no execution --------------------------------------------------------------

AUDIT = """\
import runpy, sys
log = open(sys.argv[1], "w")
LAUNCHES = ("subprocess.", "socket.", "os.system", "os.exec", "os.posix_spawn", "os.fork", "os.spawn")
def hook(event, args):
    if event.startswith(LAUNCHES):
        log.write(event + "\\n")
        log.flush()
sys.addaudithook(hook)
script = sys.argv[2]
sys.argv = sys.argv[2:]
runpy.run_path(script, run_name="__main__")
"""


@pytest.mark.parametrize("mode", [[], ["--json"]])
def test_dry_run_matches_a_normal_run_and_launches_nothing(tmp_path, outside, mode):
    home = tmp_path / "dry-home"
    profile = write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE)
    repo = git_repo(tmp_path / "repo")
    marker = tmp_path / "launched"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for name in ("codex", "opencode", "claude", "second-cli", "curl", "wget"):
        tool = fake_bin / name
        tool.write_text(f"#!/bin/sh\ntouch '{marker}'\n")
        tool.chmod(0o755)
    env = {
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}", "HOME": str(home), "LC_ALL": "C",
        "AGENT_SKILLS_PROFILE": str(profile),
    }
    hook = tmp_path / "audit.py"
    hook.write_text(AUDIT)
    outputs = []
    for extra in ([], ["--dry-run"]):
        log = tmp_path / f"audit{len(outputs)}.log"
        res = subprocess.run(
            [sys.executable, str(hook), str(log), str(RESOLVER), "--role", "refinement.reviewers[1]",
             "--repo", str(repo), *mode, *extra],
            cwd=outside, env=env, capture_output=True, text=True, timeout=60,
        )
        assert res.returncode == 0, res.stderr
        assert res.stderr == ""
        assert log.read_text() == "", "the resolver spawned a process or opened a socket"
        outputs.append(res.stdout)
    assert outputs[0] == outputs[1]
    assert "second-cli" in outputs[1]
    assert not marker.exists()
    # Control: the hook does see a launch, so an empty log above is evidence. Without --repo the
    # resolver asks git for the work tree, which is the one process it may start.
    log = tmp_path / "control.log"
    control_env = {k: v for k, v in env.items() if k != "AGENT_SKILLS_PROFILE"}
    res = subprocess.run(
        [sys.executable, str(hook), str(log), str(RESOLVER), "--role", "review.reviewer", *mode],
        cwd=repo, env=control_env, capture_output=True, text=True, timeout=60,
    )
    assert res.returncode == 0, res.stderr
    assert "subprocess.Popen" in log.read_text()


def test_dry_run_needs_no_credential(home, home_profile, outside):
    env = base_env(home)
    assert not any(k.endswith(("_API_KEY", "_TOKEN")) for k in env)
    res = resolve("--role", "review.reviewer", "--dry-run", cwd=outside, env=env)
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.reviewer", "codex", "gpt-test", home_profile)


# --- Dependency ----------------------------------------------------------------------------


def test_a_missing_pyyaml_fails_with_an_actionable_line(tmp_path, home, home_profile, outside):
    shadow = tmp_path / "no-yaml"
    write(shadow / "yaml.py", "raise ImportError('No module named yaml')\n")
    env = base_env(home) | {"PYTHONPATH": str(shadow)}
    line = assert_fails(
        resolve("--role", "review.reviewer", cwd=outside, env=env), "PyYAML>=6", str(RESOLVER),
    )
    assert "install" in line


# --- Vendoring -----------------------------------------------------------------------------

EXEC_HEADER = (
    b"# GENERATED from shared/resolve-model-role.py by scripts/vendor_shared.py. "
    b"Edit the source, then rerun the script.\n"
)


@pytest.fixture
def vendor_tree(tmp_path: Path) -> Path:
    """A copy of the generator with a fixture shared/, skills.json and skill tree."""
    tree = tmp_path / "tree"
    (tree / "scripts").mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts" / "vendor_shared.py", tree / "scripts" / "vendor_shared.py")
    write(tree / "shared" / "profile.md", "# Profile\n")
    write(tree / "shared" / "runtimes.md", "# Runtimes\n")
    shutil.copyfile(RESOLVER, tree / "shared" / "resolve-model-role.py")
    for skill in ("alpha", "beta"):
        write(tree / "skills" / skill / "SKILL.md", f"---\nname: {skill}\n---\n")
    write(tree / "skills" / "alpha" / "scripts" / "own.sh", "#!/bin/sh\necho mine\n")
    (tree / "skills.json").write_text(json.dumps({
        "skills": {"alpha": [], "beta": []},
        "executables": {"alpha": ["resolve-model-role.py"]},
    }))
    return tree


def vendor(tree: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(tree / "scripts" / "vendor_shared.py"), *args],
        cwd=tree, capture_output=True, text=True, timeout=60,
    )


def test_the_generator_vendors_the_resolver_with_a_comment_header(vendor_tree):
    assert vendor(vendor_tree).returncode == 0
    copy = vendor_tree / "skills" / "alpha" / "scripts" / "resolve-model-role.py"
    assert copy.read_bytes() == EXEC_HEADER + RESOLVER.read_bytes()
    assert not (vendor_tree / "skills" / "beta" / "scripts").exists()
    assert (vendor_tree / "skills" / "alpha" / "references" / "profile.md").read_text().startswith(
        "<!-- GENERATED from shared/profile.md by scripts/vendor_shared.py."
    )
    assert (vendor_tree / "skills" / "alpha" / "scripts" / "own.sh").read_text() == "#!/bin/sh\necho mine\n"
    res = vendor(vendor_tree, "--check")
    assert (res.returncode, res.stdout) == (0, "")


def test_a_vendored_copy_runs_from_a_single_copied_skill_directory(vendor_tree, tmp_path, home, home_profile, outside):
    assert vendor(vendor_tree).returncode == 0
    lone = tmp_path / "lone-skill"
    shutil.copytree(vendor_tree / "skills" / "alpha", lone)
    res = subprocess.run(
        [sys.executable, str(lone / "scripts" / "resolve-model-role.py"), "--role", "review.reviewer"],
        cwd=outside,
        env=base_env(home), capture_output=True, text=True, timeout=60,
    )
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.reviewer", "codex", "gpt-test", home_profile)


def flip_a_byte(copy: Path) -> None:
    data = bytearray(copy.read_bytes())
    data[len(EXEC_HEADER) + 40] ^= 0x01
    copy.write_bytes(bytes(data))


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (flip_a_byte, "stale or missing: skills/alpha/scripts/resolve-model-role.py"),
        (lambda c: c.write_bytes(RESOLVER.read_bytes()), "stale or missing: skills/alpha/scripts/resolve-model-role.py"),
        (lambda c: c.write_bytes(EXEC_HEADER.replace(b"rerun", b"re-run") + RESOLVER.read_bytes()),
         "stale or missing: skills/alpha/scripts/resolve-model-role.py"),
        (lambda c: c.unlink(), "stale or missing: skills/alpha/scripts/resolve-model-role.py"),
        (lambda c: write(c.parents[2] / "beta" / "scripts" / "resolve-model-role.py", c.read_text()),
         "orphaned generated file: skills/beta/scripts/resolve-model-role.py"),
    ],
    ids=["flipped-byte", "missing-header", "stale-header", "missing-copy", "orphaned-copy"],
)
def test_the_drift_check_catches_each_defect(vendor_tree, mutate, message):
    assert vendor(vendor_tree).returncode == 0
    mutate(vendor_tree / "skills" / "alpha" / "scripts" / "resolve-model-role.py")
    res = vendor(vendor_tree, "--check")
    assert res.returncode == 1
    assert message in res.stdout.splitlines()
    assert vendor(vendor_tree).returncode == 0, "a write run repairs every defect"
    assert vendor(vendor_tree, "--check").returncode == 0
    assert not (vendor_tree / "skills" / "beta" / "scripts" / "resolve-model-role.py").exists()


def test_the_repository_vendoring_is_current():
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "vendor_shared.py"), "--check"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert (res.returncode, res.stdout) == (0, "")


def test_no_production_skill_carries_a_resolver_copy_yet():
    assert json.loads((ROOT / "skills.json").read_text()).get("executables", {}) == {}
    assert not list((ROOT / "skills").glob("*/scripts/resolve-model-role.py"))


# --- Docs ----------------------------------------------------------------------------------


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end == -1 else text[start:end]


def test_the_profile_reference_documents_the_resolver():
    doc = section((ROOT / "shared" / "profile.md").read_text(), "## Resolve a model role")
    for fragment in (
        "python3 <path>/resolve-model-role.py --role <role-key> [--repo DIR] [--json] [--dry-run]",
        "`refinement.reviewers[1]`", "`profile.`", "git rev-parse --show-toplevel", "`--repo DIR`",
        "`role`, `runtime`, `model` (the effective model), `source`", "`command` only when",
        "`unresolved`", "code 16", "never falls through", "byte-identical", "`PyYAML>=6`", "`git`", "`python3`",
        "`override`", "SKL-68",
    ):
        assert fragment in doc, fragment


def test_the_readmes_and_the_pipeline_compatibility_name_the_resolver():
    assert "`resolve-model-role.py` is the directory's one non-Markdown file" in (ROOT / "shared" / "README.md").read_text()
    contributing = section((ROOT / "README.md").read_text(), "## Contributing")
    assert "shared/resolve-model-role.py" in contributing
    assert "after stripping that first line" in contributing
    skill = (ROOT / "skills" / "adversarial-review-pipeline" / "SKILL.md").read_text()
    compat = next(line for line in skill.splitlines() if line.startswith("compatibility:"))
    for dep in ("python3", "git", "PyYAML>=6"):
        assert dep in compat
