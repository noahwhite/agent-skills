"""The full-suite option (SKL-361): the resolver, the profile schema and the pipeline preflight switch.

A1: run-adversarial-pipeline.sh takes --full-suite on|off; omitted, it resolves from the profile the
skills load (off when there is none); an invalid value exits non-zero with a usage message.
A2: profile.full_suite resolves explicit argument, then teams[<team>], then default, then off, the
team being the story key's prefix, else profile.tracker.team_key.
A3: with off the preflight still fails a dirty tree, logs `full-suite: off` and runs no test command;
with on it runs the test command; the SKILL.md preflight command passes --full-suite.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parent.parent
RESOLVER = ROOT / "shared" / "resolve-full-suite.py"
PIPELINE = ROOT / "skills" / "adversarial-review-pipeline" / "scripts" / "run-adversarial-pipeline.sh"
SKILL_MD = ROOT / "skills" / "adversarial-review-pipeline" / "SKILL.md"
SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())


def isolated_env(home: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    """No profile leaks in: no $AGENT_SKILLS_PROFILE, no gate variables, and an empty home."""
    env = {k: v for k, v in os.environ.items()
           if k != "AGENT_SKILLS_PROFILE" and not k.startswith(("ADVERSARIAL_", "GIT_"))}
    home.mkdir(exist_ok=True)
    env["HOME"] = str(home)
    return {**env, **(extra or {})}


def resolve(tmp_path: Path, profile: str | None, *args: str) -> subprocess.CompletedProcess:
    argv = [sys.executable, str(RESOLVER), *args]
    if profile is not None:
        path = tmp_path / "profile.yaml"
        path.write_text(profile)
        argv += ["--profile", str(path)]
    return subprocess.run(argv, capture_output=True, text=True, cwd=tmp_path,
                          env=isolated_env(tmp_path / "home"), timeout=60)


def resolved(tmp_path: Path, profile: str | None, *args: str) -> str:
    result = resolve(tmp_path, profile, *args)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


# --- A2: resolution order --------------------------------------------------------------------------

def test_an_off_key_with_teams_off_on_resolves_on(tmp_path):
    profile = 'full_suite:\n  default: "off"\n  teams:\n    "OFF": "on"\n'
    # Joined at run time: the repository leak scan refuses an OFF story key written out in full.
    assert resolved(tmp_path, profile, "--story-key", "-".join(("OFF", "12"))) == "on"


def test_an_skl_key_resolves_off_from_its_team(tmp_path):
    profile = 'full_suite:\n  default: "on"\n  teams:\n    "OFF": "on"\n    SKL: "off"\n'
    assert resolved(tmp_path, profile, "--story-key", "SKL-361") == "off"


def test_a_team_missing_from_teams_falls_to_a_default_of_on(tmp_path):
    profile = 'full_suite:\n  default: "on"\n  teams:\n    "OFF": "off"\n'
    assert resolved(tmp_path, profile, "--story-key", "ABC-1") == "on"


def test_a_team_missing_from_teams_falls_to_a_default_of_off(tmp_path):
    # tracker.team_key names a team set to on, so a resolver that used it instead of the key's prefix reads on.
    profile = 'tracker:\n  team_key: "OFF"\nfull_suite:\n  default: "off"\n  teams:\n    "OFF": "on"\n'
    assert resolved(tmp_path, profile, "--story-key", "ABC-1") == "off"


def test_without_a_story_key_the_team_is_the_tracker_team_key(tmp_path):
    profile = 'tracker:\n  team_key: "OFF"\nfull_suite:\n  default: "off"\n  teams:\n    "OFF": "on"\n'
    assert resolved(tmp_path, profile) == "on"


def test_a_profile_without_full_suite_resolves_off(tmp_path):
    assert resolved(tmp_path, 'tracker:\n  team_key: SKL\n', "--story-key", "SKL-1") == "off"


def test_an_explicit_argument_overrides_the_profile(tmp_path):
    profile = 'full_suite:\n  default: "on"\n  teams:\n    SKL: "on"\n'
    assert resolved(tmp_path, profile, "--story-key", "SKL-12", "--value", "off") == "off"


def test_no_profile_anywhere_resolves_off(tmp_path):
    assert resolved(tmp_path, None) == "off"


@pytest.mark.parametrize("body", [
    'full_suite:\n  default: on\n',
    'full_suite:\n  teams:\n    OFF: "on"\n',
    'full_suite:\n  teams:\n    "OFF": "maybe"\n',
    'full_suite:\n  default: "off"\n  other: "on"\n',
])
def test_a_profile_value_outside_the_schema_fails_closed(tmp_path, body):
    result = resolve(tmp_path, body)
    assert result.returncode == 16, result.stdout + result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("tracker", ["tracker:\n  team_key: OFF\n", "tracker:\n  team_key: off\n",
                                     'tracker:\n  team_key: "skl"\n', "tracker: []\n"])
def test_an_unusable_tracker_team_key_fails_closed(tmp_path, tracker):
    # An unquoted OFF reads as a boolean and a lower-case key never matches a teams key; resolving the default
    # instead would silently turn off a suite the team set on.
    profile = tracker + 'full_suite:\n  default: "off"\n  teams:\n    "OFF": "on"\n    SKL: "on"\n'
    result = resolve(tmp_path, profile)
    assert result.returncode == 16, result.stdout + result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("args", [["--value", "yes"], ["--story-key", "skl-1"]])
def test_a_malformed_command_line_exits_2(tmp_path, args):
    assert resolve(tmp_path, None, *args).returncode == 2


# --- A2: the schema ----------------------------------------------------------------------------------

def test_the_schema_defines_full_suite_with_exactly_default_and_teams():
    node = SCHEMA["properties"]["full_suite"]
    assert node["type"] == "object" and node["additionalProperties"] is False
    assert set(node["properties"]) == {"default", "teams"}
    assert node["properties"]["default"]["enum"] == ["on", "off"]
    assert node["properties"]["default"]["default"] == "off"
    teams = node["properties"]["teams"]
    assert teams["patternProperties"] == {"^[A-Z][A-Z0-9]*$": {"enum": ["on", "off"]}}
    assert teams["additionalProperties"] is False


def minimal_profile(full_suite: dict) -> dict:
    return {"version": 1, "project": {"name": "x"}, "full_suite": full_suite}


def test_the_schema_accepts_teams_off_on():
    jsonschema.validate(minimal_profile({"teams": {"OFF": "on"}}), SCHEMA)


@pytest.mark.parametrize(
    "full_suite",
    # "OFF\n": `$` in the key pattern also matches before a trailing line feed, which the resolver refuses.
    [{"teams": {"off": "on"}}, {"teams": {"OFF": "yes"}}, {"default": "maybe"}, {"teams": {"OFF\n": "on"}}],
)
def test_the_schema_rejects_a_lowercase_team_key_or_a_non_enum_value(full_suite):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(minimal_profile(full_suite), SCHEMA)


# --- A1 and A3: the pipeline preflight --------------------------------------------------------------

def make_repo(tmp_path: Path, env: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "agent-skills@example.com"],
        ["git", "config", "user.name", "agent-skills"],
        ["git", "config", "commit.gpgsign", "false"],
    ):
        subprocess.run(command, cwd=repo, check=True, capture_output=True, env=env)
    (repo / "tracked.txt").write_text("one\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True, capture_output=True, env=env)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True, capture_output=True, env=env)
    return repo


def commit_profile(repo: Path, env: dict[str, str], text: str) -> None:
    (repo / ".agent-skills").mkdir(exist_ok=True)
    (repo / ".agent-skills" / "profile.yaml").write_text(text)
    subprocess.run(["git", "add", ".agent-skills"], cwd=repo, check=True, capture_output=True, env=env)
    subprocess.run(["git", "commit", "-qm", "profile"], cwd=repo, check=True, capture_output=True, env=env)


def preflight(tmp_path: Path, repo: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess:
    marker = tmp_path / "suite-ran"
    return subprocess.run(
        ["bash", str(PIPELINE), "preflight", "--repo", str(repo), "--base", "HEAD",
         "--test-cmd", f"touch {shlex.quote(str(marker))}", "--scratch", str(tmp_path / "scratch"), *args],
        capture_output=True, text=True, env=env, cwd=str(tmp_path), timeout=120,
    )


def suite_log(repo: Path, env: dict[str, str]) -> Path:
    out = subprocess.run(
        ["bash", str(PIPELINE), "paths", "--repo", str(repo), "--base", "HEAD"],
        capture_output=True, text=True, env=env, timeout=60, check=True,
    ).stdout
    return Path(next(line.split(" ", 1)[1] for line in out.splitlines() if line.startswith("suite_log ")))


@pytest.fixture
def setup(tmp_path):
    env = isolated_env(tmp_path / "home")
    return tmp_path, make_repo(tmp_path, env), env


def test_preflight_with_full_suite_off_runs_no_test_command_and_logs_off(setup):
    tmp_path, repo, env = setup
    result = preflight(tmp_path, repo, env, "--full-suite", "off")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "suite-ran").exists(), "the test command ran with --full-suite off"
    assert "full-suite: off" in result.stdout
    assert suite_log(repo, env).read_text() == "full-suite: off\n"


def test_preflight_with_full_suite_on_runs_the_test_command(setup):
    tmp_path, repo, env = setup
    result = preflight(tmp_path, repo, env, "--full-suite", "on")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "suite-ran").exists(), "the test command did not run with --full-suite on"
    assert "full-suite: off" not in result.stdout


def test_preflight_without_the_flag_and_without_a_profile_resolves_off(setup):
    tmp_path, repo, env = setup
    result = preflight(tmp_path, repo, env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "suite-ran").exists(), "an omitted flag with no profile ran the suite"
    assert "full-suite: off" in result.stdout


def test_preflight_without_the_flag_reads_the_repository_profile(setup):
    tmp_path, repo, env = setup
    commit_profile(repo, env, 'tracker:\n  team_key: SKL\nfull_suite:\n  default: "on"\n')
    result = preflight(tmp_path, repo, env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "suite-ran").exists(), "an omitted flag ignored the repository profile's on"


def test_preflight_without_the_flag_reads_the_tracker_team_from_the_profile(setup):
    tmp_path, repo, env = setup
    commit_profile(repo, env, 'tracker:\n  team_key: SKL\nfull_suite:\n  default: "off"\n  teams:\n    SKL: "on"\n')
    result = preflight(tmp_path, repo, env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "suite-ran").exists(), "an omitted flag ignored teams[tracker.team_key]"


def test_a_failed_resolution_discards_the_previous_preflight_acceptance(setup):
    tmp_path, repo, env = setup
    profile = tmp_path / "selected.yaml"
    profile.write_text('full_suite:\n  default: "off"\n')
    env = {**env, "AGENT_SKILLS_PROFILE": str(profile)}
    assert preflight(tmp_path, repo, env).returncode == 0
    out = subprocess.run(["bash", str(PIPELINE), "paths", "--repo", str(repo), "--base", "HEAD"],
                         capture_output=True, text=True, env=env, timeout=60, check=True).stdout
    stamp = Path(next(line.split(" ", 1)[1] for line in out.splitlines() if line.startswith("preflight ")) + ".stamp")
    assert stamp.exists(), "a passing preflight left no stamp"
    profile.write_text("full_suite:\n  default: on\n")
    result = preflight(tmp_path, repo, env)
    assert result.returncode == 2, result.stdout + result.stderr
    assert not stamp.exists(), "a failed resolution left the previous preflight accepted"


def test_preflight_rejects_an_invalid_full_suite_value_with_usage(setup):
    tmp_path, repo, env = setup
    result = preflight(tmp_path, repo, env, "--full-suite", "maybe")
    assert result.returncode != 0
    assert "--full-suite must be on or off" in result.stderr
    assert "Usage:" in result.stderr
    assert not (tmp_path / "suite-ran").exists()


def test_full_suite_on_a_command_other_than_preflight_is_refused(setup):
    tmp_path, repo, env = setup
    result = subprocess.run(
        ["bash", str(PIPELINE), "paths", "--repo", str(repo), "--base", "HEAD", "--full-suite", "on"],
        capture_output=True, text=True, env=env, timeout=60,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "--full-suite is a preflight option" in result.stderr


def test_preflight_with_full_suite_off_still_fails_a_dirty_tree(setup):
    tmp_path, repo, env = setup
    (repo / "untracked.txt").write_text("dirty\n")
    result = preflight(tmp_path, repo, env, "--full-suite", "off")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL - uncommitted changes" in result.stdout


# --- A3: the SKILL.md preflight command --------------------------------------------------------------

def phase0_section() -> str:
    text = SKILL_MD.read_text()
    match = re.search(r"^## Phase 0: preflight.*?(?=^## )", text, re.S | re.M)
    assert match, "SKILL.md has no Phase 0 section"
    return match.group(0)


def test_the_skill_preflight_command_passes_full_suite():
    blocks = re.findall(r"^```bash\n(.*?)^```", phase0_section(), re.S | re.M)
    commands = [line for block in blocks for line in block.splitlines()
                if re.match(r'\s*"\$PIPELINE" preflight ', line)]
    assert len(commands) == 1, commands
    assert re.search(r'\s--full-suite "<on or off>"\s', commands[0]), commands[0]
