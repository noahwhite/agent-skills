"""The model-role resolver: shared/resolve-model-role.py.

Every case runs the resolver as a subprocess, the way its callers do, with HOME and
AGENT_SKILLS_PROFILE pointed at fixtures under tmp_path and no provider credential in the
environment, so neither this repository's own profile nor the user's is ever read.
"""

import ast
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


@pytest.mark.parametrize(
    "inherited",
    [
        lambda repo, sub: {"GIT_DIR": str(repo / ".git"), "GIT_WORK_TREE": str(sub)},
        lambda repo, sub: {"GIT_CEILING_DIRECTORIES": str(repo)},
        lambda repo, sub: {"GIT_DIR": ".git"},
    ],
    ids=["git-dir-and-work-tree", "ceiling", "relative-git-dir-as-in-a-hook"],
)
def test_inherited_git_variables_do_not_move_the_repository_root(tmp_path, home, inherited):
    repo = git_repo(tmp_path / "repo")
    repo_profile = write(repo / ".agent-skills" / "profile.yaml", PROFILE)
    sub = repo / "a"
    write(sub / ".agent-skills" / "profile.yaml", PROFILE.replace("gpt-test", "from-subdirectory"))
    write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE.replace("gpt-test", "from-home"))
    res = resolve("--role", "review.reviewer", cwd=sub, env=base_env(home) | inherited(repo, sub))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("review.reviewer", "codex", "gpt-test", repo_profile)


def test_an_unsearchable_repository_profile_directory_fails_without_falling_through(tmp_path, home):
    repo = git_repo(tmp_path / "repo")
    write(repo / ".agent-skills" / "profile.yaml", PROFILE)
    home_profile = write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE.replace("gpt-test", "from-home"))
    (repo / ".agent-skills").chmod(0)
    try:
        if os.access(repo / ".agent-skills", os.X_OK):
            pytest.skip("running as a user that ignores directory permissions")
        line = assert_fails(
            resolve("--role", "review.reviewer", cwd=repo, env=base_env(home)),
            "review.reviewer", str(repo / ".agent-skills" / "profile.yaml"), "cannot check",
        )
        assert str(home_profile) not in line
    finally:
        (repo / ".agent-skills").chmod(0o755)


def test_a_repository_root_that_is_not_utf8_resolves(tmp_path, home):
    raw = os.fsencode(tmp_path) + b"/repo-\xff"
    os.mkdir(raw)
    repo = git_repo(Path(os.fsdecode(raw)))
    write(repo / ".agent-skills" / "profile.yaml", PROFILE)
    write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE.replace("gpt-test", "from-home"))
    res = subprocess.run(
        [sys.executable, str(RESOLVER), "--role", "review.reviewer"],
        cwd=raw, env=base_env(home), capture_output=True, timeout=60,
    )
    assert res.returncode == 0, res.stderr
    out = res.stdout.decode()
    assert "model: gpt-test\n" in out
    assert "source: " + str(tmp_path) + "/repo-\\udcff/.agent-skills/profile.yaml\n" in out


def test_a_repository_path_ending_in_a_space_keeps_it(tmp_path, home):
    repo = git_repo(tmp_path / "repo ")
    repo_profile = write(repo / ".agent-skills" / "profile.yaml", PROFILE)
    write(home / ".config" / "agent-skills" / "profile.yaml", PROFILE.replace("gpt-test", "from-home"))
    res = resolve("--role", "review.reviewer", cwd=repo, env=base_env(home))
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


def test_a_null_runtime_with_a_command_resolves_as_a_command_entry(home, outside):
    profile = write(home / ".config" / "agent-skills" / "profile.yaml", "r:\n  name: R\n  runtime: null\n  command: cli go\n")
    res = resolve("--role", "r", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("r", "command", "unresolved", profile, "cli go")


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


def test_control_characters_and_lone_surrogates_are_escaped_in_text_mode(home, outside):
    profile = write(
        home / ".config" / "agent-skills" / "profile.yaml",
        'r:\n  name: R\n  runtime: command\n  command: "a\\tb\\e[31mc\\x7fd\\x9be\\uD800f\\u00e9"\n',
    )
    res = resolve("--role", "r", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("r", "command", "unresolved", profile, "a\\tb\\x1b[31mc\\x7fd\\x9be\\ud800f\u00e9")
    res = resolve("--role", "r", "--json", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert json.loads(res.stdout)["command"] == "a\tb\x1b[31mc\x7fd\x9be\ud800f\u00e9"


def test_unicode_line_breaks_are_escaped_so_each_field_stays_one_line(home, outside):
    profile = write(
        home / ".config" / "agent-skills" / "profile.yaml",
        'r:\n  name: R\n  runtime: command\n  command: "a\\u2028b\\u2029c\\x85d\\x0be\\x0cf\\x1cg"\n',
    )
    res = resolve("--role", "r", cwd=outside, env=base_env(home))
    assert res.returncode == 0, res.stderr
    assert res.stdout == lines("r", "command", "unresolved", profile, "a\\u2028b\\u2029c\\x85d\\x0be\\x0cf\\x1cg")
    assert len(res.stdout.splitlines()) == 5


def test_an_unencodable_role_key_still_fails_with_one_line(home, home_profile, outside):
    line = assert_fails(resolve("--role", "review.missing\udcff", cwd=outside, env=base_env(home)), "\\udcff")
    assert str(home_profile) in line


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
    assert_fails(resolve("--role", "review.reviewer", cwd=outside, env=env), str(bad), "the selected profile is unreadable")


def test_a_too_deeply_nested_profile_fails(tmp_path, home, outside):
    deep = write(tmp_path / "deep.yaml", "r: " + "[" * 5000 + "]" * 5000 + "\n")
    env = base_env(home) | {"AGENT_SKILLS_PROFILE": str(deep)}
    assert_fails(resolve("--role", "r", cwd=outside, env=env), str(deep), "not valid YAML")


@pytest.mark.parametrize("kind", ["fifo", "device"])
def test_a_profile_that_is_not_a_regular_file_fails_without_reading_it(tmp_path, home, home_profile, outside, kind):
    if kind == "fifo":
        special = tmp_path / "profile.fifo"
        os.mkfifo(special)
    else:
        special = Path("/dev/null")
    env = base_env(home) | {"AGENT_SKILLS_PROFILE": str(special)}
    line = assert_fails(resolve("--role", "review.reviewer", cwd=outside, env=env), str(special), "not a regular file")
    assert str(home_profile) not in line


def test_a_profile_swapped_to_a_fifo_after_the_type_check_is_never_read(tmp_path, home, home_profile, outside):
    # Simulates a symlink retargeted between a path-based type check and the open: every
    # path-based check reports a regular file, so only a check on the opened file can refuse it.
    fifo = tmp_path / "profile.fifo"
    os.mkfifo(fifo)
    hook = tmp_path / "hook"
    write(
        hook / "sitecustomize.py",
        "import os.path\n"
        "os.path.isfile = lambda p: True\n"
        "os.path.isdir = lambda p: False\n"
        "os.path.exists = lambda p: True\n",
    )
    env = base_env(home) | {"AGENT_SKILLS_PROFILE": str(fifo), "PYTHONPATH": str(hook)}
    try:
        res = subprocess.run(
            [sys.executable, str(RESOLVER), "--role", "review.reviewer"],
            cwd=outside, env=env, capture_output=True, text=True, timeout=15,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("the resolver blocked opening a FIFO")
    line = assert_fails(res, str(fifo), "not a regular file")
    assert str(home_profile) not in line


def test_a_deleted_working_directory_fails_with_one_line(tmp_path, home, home_profile):
    gone = tmp_path / "gone"
    gone.mkdir()
    res = subprocess.run(
        ["sh", "-c", 'cd "$1" && rmdir "$1" && exec "$2" "$3" --role review.reviewer',
         "sh", str(gone), sys.executable, str(RESOLVER)],
        cwd=tmp_path, env=base_env(home), capture_output=True, text=True, timeout=60,
    )
    assert_fails(res, "review.reviewer", "working directory")


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
    # The converse: a runtime dropped from the schema is dropped from the resolver too.
    tree = ast.parse(RESOLVER.read_text())
    declared = next(
        ast.literal_eval(node.value) for node in tree.body
        if isinstance(node, ast.Assign) and [t.id for t in node.targets if isinstance(t, ast.Name)] == ["MODEL_RUNTIMES"]
    )
    assert set(declared) | {"command"} == runtimes


# --- Dry run and no execution --------------------------------------------------------------

AUDIT = """\
import runpy, sys
log = open(sys.argv[1], "w")
LAUNCHES = ("subprocess.", "socket.", "os.system", "os.exec", "os.posix_spawn", "os.fork", "os.spawn")
def hook(event, args):
    if event.startswith(LAUNCHES):
        argv = args[1] if event == "subprocess.Popen" else args
        log.write(f"{event} {argv!r}\\n")
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
    write(repo / ".agent-skills" / "profile.yaml", PROFILE)
    git_launch = "subprocess.Popen ['git', '-C', %r, 'rev-parse', '--show-toplevel']\n" % str(repo)
    # With --repo the resolver starts nothing; without it, the only launch is git finding the
    # work tree, which also shows the hook does see a launch, so an empty log is evidence.
    for discovery, cwd, run_env, launches in (
        (["--repo", str(repo)], outside, env, ""),
        ([], repo, {k: v for k, v in env.items() if k != "AGENT_SKILLS_PROFILE"}, git_launch),
    ):
        outputs = []
        for extra in ([], ["--dry-run"]):
            log = tmp_path / f"audit{len(outputs)}.log"
            res = subprocess.run(
                [sys.executable, str(hook), str(log), str(RESOLVER), "--role", "refinement.reviewers[1]",
                 *discovery, *mode, *extra],
                cwd=cwd, env=run_env, capture_output=True, text=True, timeout=60,
            )
            assert res.returncode == 0, res.stderr
            assert res.stderr == ""
            assert log.read_text() == launches, "the resolver spawned a process or opened a socket"
            outputs.append(res.stdout)
        assert outputs[0] == outputs[1]
        assert "second-cli" in outputs[1]
        assert "gpt-test" not in outputs[1]
    assert not marker.exists()


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


def test_a_missing_pyyaml_is_reported_even_with_no_profile(tmp_path, home, outside):
    shadow = tmp_path / "no-yaml"
    write(shadow / "yaml.py", "raise ImportError('No module named yaml')\n")
    env = base_env(home) | {"PYTHONPATH": str(shadow)}
    line = assert_fails(resolve("--role", "review.reviewer", cwd=outside, env=env), "PyYAML>=6", str(RESOLVER))
    assert str(home / ".config" / "agent-skills" / "profile.yaml") in line


@pytest.mark.parametrize(
    ("module", "fragment"),
    [
        ("__version__ = '5.4.1'\n", "PyYAML 5.4.1 is too old"),
        ("raise RuntimeError('broken install')\n", "PyYAML could not be imported"),
        ("raise SystemExit(0)\n", "PyYAML could not be imported"),
        ("__version__ = '6.0'\n", "PyYAML 6.0 lacks safe_load"),
    ],
    ids=["too-old", "broken", "exits-on-import", "no-safe-load"],
)
def test_an_unusable_pyyaml_fails_with_an_actionable_line(tmp_path, home, home_profile, outside, module, fragment):
    shadow = tmp_path / "bad-yaml"
    write(shadow / "yaml.py", module)
    env = base_env(home) | {"PYTHONPATH": str(shadow)}
    line = assert_fails(resolve("--role", "review.reviewer", cwd=outside, env=env), fragment, "PyYAML>=6", str(RESOLVER))
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


def test_a_vendored_copy_is_not_executable_because_its_header_masks_the_shebang(vendor_tree):
    source = vendor_tree / "shared" / "resolve-model-role.py"
    source.chmod(0o755)
    assert vendor(vendor_tree).returncode == 0
    copy = vendor_tree / "skills" / "alpha" / "scripts" / "resolve-model-role.py"
    assert copy.stat().st_mode & 0o111 == 0


def test_the_header_is_written_in_each_executable_language(vendor_tree):
    write(vendor_tree / "shared" / "tool.sh", "#!/bin/sh\necho tool\n")
    write(vendor_tree / "shared" / "tool.js", "console.log('tool');\n")
    manifest = json.loads((vendor_tree / "skills.json").read_text())
    manifest["executables"]["beta"] = ["tool.sh", "tool.js"]
    (vendor_tree / "skills.json").write_text(json.dumps(manifest))
    assert vendor(vendor_tree).returncode == 0
    scripts = vendor_tree / "skills" / "beta" / "scripts"
    tail = "by scripts/vendor_shared.py. Edit the source, then rerun the script.\n"
    assert (scripts / "tool.sh").read_text() == f"# GENERATED from shared/tool.sh {tail}#!/bin/sh\necho tool\n"
    assert (scripts / "tool.js").read_text() == f"// GENERATED from shared/tool.js {tail}console.log('tool');\n"
    assert vendor(vendor_tree, "--check").returncode == 0


def test_a_symlinked_copy_is_replaced_without_touching_its_target(vendor_tree, tmp_path):
    assert vendor(vendor_tree).returncode == 0
    copy = vendor_tree / "skills" / "alpha" / "scripts" / "resolve-model-role.py"
    victim = tmp_path / "victim.txt"
    victim.write_bytes(copy.read_bytes())
    copy.unlink()
    copy.symlink_to(victim)
    res = vendor(vendor_tree, "--check")
    assert res.returncode == 1
    assert "stale or missing: skills/alpha/scripts/resolve-model-role.py" in res.stdout.splitlines()
    victim.write_text("keep me\n")
    assert vendor(vendor_tree).returncode == 0
    assert victim.read_text() == "keep me\n"
    assert not copy.is_symlink()
    assert copy.read_bytes() == EXEC_HEADER + RESOLVER.read_bytes()


def test_a_script_carrying_the_exact_header_but_other_content_is_never_deleted(vendor_tree):
    hand = write(
        vendor_tree / "skills" / "beta" / "scripts" / "hand.py",
        "# GENERATED from shared/hand.py by scripts/vendor_shared.py. Edit the source, then rerun the script.\n"
        "print('mine')\n",
    )
    res = vendor(vendor_tree)
    assert res.returncode == 1
    assert "skills/beta/scripts/hand.py" in res.stderr
    assert hand.read_text().endswith("print('mine')\n")
    res = vendor(vendor_tree, "--check")
    assert res.returncode == 1
    assert "orphaned generated file: skills/beta/scripts/hand.py" in res.stdout.splitlines()


@pytest.mark.parametrize("skill", ["../rogue", "alpha/../beta", ""])
def test_an_executable_skill_key_must_name_a_skill_directory(vendor_tree, skill):
    manifest = json.loads((vendor_tree / "skills.json").read_text())
    manifest["executables"] = {skill: ["resolve-model-role.py"]}
    (vendor_tree / "skills.json").write_text(json.dumps(manifest))
    res = vendor(vendor_tree)
    assert res.returncode == 1
    assert "skill name" in res.stderr
    assert not (vendor_tree / "rogue").exists()


def test_a_hand_written_script_that_only_resembles_a_header_is_kept(vendor_tree):
    hand = write(
        vendor_tree / "skills" / "alpha" / "scripts" / "hand.py",
        "# GENERATED from shared/ templates by hand, then edited; not a vendored copy\nprint('mine')\n",
    )
    assert vendor(vendor_tree).returncode == 0
    assert hand.is_file()
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
        (lambda c: c.chmod(0o755), "stale or missing: skills/alpha/scripts/resolve-model-role.py"),
        (lambda c: write(c.parents[2] / "beta" / "scripts" / "resolve-model-role.py", c.read_text()),
         "orphaned generated file: skills/beta/scripts/resolve-model-role.py"),
    ],
    ids=["flipped-byte", "missing-header", "stale-header", "missing-copy", "executable-bit", "orphaned-copy"],
)
def test_the_drift_check_catches_each_defect(vendor_tree, mutate, message):
    assert vendor(vendor_tree).returncode == 0
    mutate(vendor_tree / "skills" / "alpha" / "scripts" / "resolve-model-role.py")
    res = vendor(vendor_tree, "--check")
    assert res.returncode == 1
    assert message in res.stdout.splitlines()
    assert vendor(vendor_tree).returncode == 0, "a write run repairs every defect"
    assert vendor(vendor_tree, "--check").returncode == 0
    assert (vendor_tree / "skills" / "alpha" / "scripts" / "resolve-model-role.py").stat().st_mode & 0o111 == 0
    assert not (vendor_tree / "skills" / "beta" / "scripts" / "resolve-model-role.py").exists()


def test_the_repository_vendoring_is_current():
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "vendor_shared.py"), "--check"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert (res.returncode, res.stdout) == (0, "")


def test_no_production_skill_carries_a_resolver_copy_yet():
    executables = json.loads((ROOT / "skills.json").read_text()).get("executables", {})
    assert not [skill for skill, names in executables.items() if "resolve-model-role.py" in names]
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
        "`override`", "SKL-68", "inherited `GIT_*` variable removed", "a tab as `\\t`", "a lone surrogate or a Unicode line or paragraph separator (U+2028, U+2029) as `\\uNNNN`",
        "through `python3`", "is not executable", "exits 2",
    ):
        assert fragment in doc, fragment
    # Every fail-closed case is listed, one bullet each.
    fail_closed = section(doc, "- **Fail closed.**").split("- **No execution.**")[0]
    for bullet in (
        "- no profile at any of the three locations;",
        "- a location whose existence cannot be checked, such as one under a directory without search permission, which never reads as absent;",
        "- a selected profile that is not a regular file (a FIFO or a device is never read), unreadable, not valid YAML (including YAML nested too deeply to parse), or not a mapping;",
        "- a working directory that no longer exists, when the repository root must be found from it;",
        "- a role key absent from the profile, or a role path that does not resolve to an agent entry;",
        "- an entry with neither `runtime` nor `command`;",
        "- a runtime the profile schema does not define;",
        "- a model-launching runtime (`claude-code`, `opencode`, `codex`) with no `model`;",
        "- a `runtime: command` entry with no non-empty `command`;",
        "- a missing, older or broken PyYAML, with an installation action and the resolver's own path, reported even when no profile exists.",
    ):
        assert bullet in fail_closed, bullet


def test_the_readmes_and_the_pipeline_compatibility_name_the_resolver():
    assert "`resolve-model-role.py` is the directory's one non-Markdown file" in (ROOT / "shared" / "README.md").read_text()
    contributing = section((ROOT / "README.md").read_text(), "## Contributing")
    assert "shared/resolve-model-role.py" in contributing
    assert "after stripping that first line" in contributing
    assert "treats a copy with an executable bit, or a symlink, as stale" in contributing
    skill = (ROOT / "skills" / "adversarial-review-pipeline" / "SKILL.md").read_text()
    compat = next(line for line in skill.splitlines() if line.startswith("compatibility:"))
    for dep in ("python3", "git", "PyYAML>=6"):
        assert dep in compat
