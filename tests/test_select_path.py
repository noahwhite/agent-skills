"""SKL-270: the run's path (spike, no-deployment, deployed) chosen by one deterministic script.

Every test runs shared/select-path.py as a subprocess through python3, never importing it, with
AGENT_SKILLS_PROFILE pointing at a temporary profile and HOME at an empty directory, so no real
profile is ever read.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "shared" / "select-path.py"
SKILLS = ("engineering-workflow", "qa-verification", "story-to-done")
ABSENT = object()


def run(tmp_path, *args, profile=None, env_profile=True, cwd=None):
    """Run the script; ``profile`` is a mapping written as YAML, or raw text."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k != "AGENT_SKILLS_PROFILE"}
    env["HOME"] = str(home)
    if env_profile:
        path = tmp_path / "profile.yaml"
        if profile is not None:
            path.write_text(profile if isinstance(profile, str) else yaml.safe_dump(profile))
        env["AGENT_SKILLS_PROFILE"] = str(path)
    return subprocess.run(
        [sys.executable, str(SOURCE), *args],
        env=env, cwd=cwd or tmp_path, capture_output=True, text=True, timeout=30,
    )


def make_profile(environments=ABSENT, integration="main", spike_label="Spike"):
    doc = {"version": 1, "git": {"integration_branch": integration}, "tracker": {"labels": {}}}
    if integration is ABSENT:
        del doc["git"]["integration_branch"]
    if spike_label is not ABSENT:
        doc["tracker"]["labels"]["spike"] = spike_label
    if environments is not ABSENT:
        doc["environments"] = environments
    return doc


DEPLOYED_ENVS = [{"name": "dev", "branch": "main"}]
OTHER_ENVS = [{"name": "dev", "branch": "develop"}]


def selected(tmp_path, profile, *args):
    res = run(tmp_path, *args, profile=profile)
    assert res.returncode == 0, res.stderr
    assert res.stdout.count("\n") == 1 and res.stdout.endswith("\n"), repr(res.stdout)
    return res.stdout[:-1]


# AC1's nine outputs, each with the conditions of every later output also true where they can be,
# so each case also proves its precedence over the next.
@pytest.mark.parametrize("value", ["spike", "no-deployment", "deployed"])
def test_1_a_valid_recorded_path_is_printed_over_every_ask_case(tmp_path, value):
    profile = make_profile(environments=ABSENT)
    out = selected(tmp_path, profile, "--title", "[Spike] x", "--recorded-path", value)
    assert out == value


def test_2_an_invalid_recorded_path_asks_over_environments_absent(tmp_path):
    out = selected(tmp_path, make_profile(environments=ABSENT), "--title", "t", "--recorded-path", "Spike")
    assert out == "ask: invalid-recorded-path"


def test_2_an_empty_recorded_path_is_invalid(tmp_path):
    out = selected(tmp_path, make_profile(environments=[]), "--title", "t", "--recorded-path", "")
    assert out == "ask: invalid-recorded-path"


@pytest.mark.parametrize("environments", [ABSENT, None], ids=["absent", "null"])
def test_3_absent_or_null_environments_ask_over_the_spike_cases(tmp_path, environments):
    profile = make_profile(environments=environments)
    assert selected(tmp_path, profile, "--title", "[Spike] x") == "ask: environments-absent"
    assert selected(tmp_path, profile, "--title", "t", "--label", "Spike") == "ask: environments-absent"


def test_4_no_integration_branch_entry_asks_over_the_spike_cases(tmp_path):
    profile = make_profile(environments=OTHER_ENVS)
    assert selected(tmp_path, profile, "--title", "[Spike] x") == "ask: no-integration-branch"
    assert selected(tmp_path, profile, "--title", "t", "--label", "Spike") == "ask: no-integration-branch"


def test_4_an_unset_integration_branch_matches_no_entry(tmp_path):
    profile = make_profile(environments=[{"name": "dev"}], integration=ABSENT)
    assert selected(tmp_path, profile, "--title", "t") == "ask: no-integration-branch"


def test_4_an_entry_without_a_branch_does_not_match(tmp_path):
    profile = make_profile(environments=[{"name": "dev"}, {"name": "stage", "branch": "main"}])
    assert selected(tmp_path, profile, "--title", "t") == "deployed"


def test_5_spike_title_without_the_label_asks(tmp_path):
    profile = make_profile(environments=DEPLOYED_ENVS)
    out = selected(tmp_path, profile, "--title", "[Spike] x", "--label", "Bug")
    assert out == "ask: spike-title-without-label"


def test_5_spike_title_with_the_spike_label_unset_asks_even_with_a_spike_named_label(tmp_path):
    profile = make_profile(environments=DEPLOYED_ENVS, spike_label=ABSENT)
    out = selected(tmp_path, profile, "--title", "[Spike] x", "--label", "Spike")
    assert out == "ask: spike-title-without-label"


def test_6_spike_label_without_the_title_asks_over_selecting_spike(tmp_path):
    profile = make_profile(environments=DEPLOYED_ENVS)
    out = selected(tmp_path, profile, "--title", "[User Story] x", "--label", "Spike")
    assert out == "ask: spike-label-without-title"


def test_7_spike_title_and_label_select_spike_over_no_deployment(tmp_path):
    profile = make_profile(environments=[])
    out = selected(tmp_path, profile, "--title", "[Spike] x", "--label", "Other", "--label", "Spike")
    assert out == "spike"


def test_8_empty_environments_select_no_deployment_over_deployed(tmp_path):
    assert selected(tmp_path, make_profile(environments=[]), "--title", "t") == "no-deployment"


def test_9_an_integration_branch_entry_selects_deployed(tmp_path):
    assert selected(tmp_path, make_profile(environments=DEPLOYED_ENVS), "--title", "t") == "deployed"


def test_wrong_case_spike_prefix_is_not_a_spike_title(tmp_path):
    profile = make_profile(environments=[])
    assert selected(tmp_path, profile, "--title", "[spike] x") == "no-deployment"


def test_wrong_case_spike_label_is_not_the_spike_label(tmp_path):
    profile = make_profile(environments=[])
    assert selected(tmp_path, profile, "--title", "[Spike] x", "--label", "spike") == "ask: spike-title-without-label"
    assert selected(tmp_path, profile, "--title", "t", "--label", "spike") == "no-deployment"


def test_the_recorded_path_is_matched_exactly(tmp_path):
    out = selected(tmp_path, make_profile(environments=[]), "--title", "t", "--recorded-path", "Deployed")
    assert out == "ask: invalid-recorded-path"


def test_profile_flag_overrides_the_environment_variable(tmp_path):
    other = tmp_path / "other.yaml"
    other.write_text(yaml.safe_dump(make_profile(environments=DEPLOYED_ENVS)))
    res = run(tmp_path, "--profile", str(other), "--title", "t", profile=make_profile(environments=[]))
    assert (res.returncode, res.stdout) == (0, "deployed\n")


def test_without_the_environment_variable_the_repository_profile_is_read(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".agent-skills").mkdir(parents=True)
    (repo / "sub").mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".agent-skills" / "profile.yaml").write_text(yaml.safe_dump(make_profile(environments=[])))
    res = run(tmp_path, "--title", "t", env_profile=False, cwd=repo / "sub")
    assert (res.returncode, res.stdout) == (0, "no-deployment\n")


def test_without_a_repository_profile_the_home_profile_is_read(tmp_path):
    config = tmp_path / "home" / ".config" / "agent-skills"
    config.mkdir(parents=True)
    (config / "profile.yaml").write_text(yaml.safe_dump(make_profile(environments=DEPLOYED_ENVS)))
    outside = tmp_path / "outside"
    outside.mkdir()
    res = run(tmp_path, "--title", "t", env_profile=False, cwd=outside)
    assert (res.returncode, res.stdout) == (0, "deployed\n")


def assert_exit_16(res):
    assert res.returncode == 16
    assert res.stdout == ""
    assert res.stderr.count("\n") == 1 and res.stderr.strip(), repr(res.stderr)


def test_exit_16_when_no_profile_file_exists(tmp_path):
    assert_exit_16(run(tmp_path, "--title", "t", profile=None))


def test_exit_16_when_no_profile_exists_anywhere(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    assert_exit_16(run(tmp_path, "--title", "t", env_profile=False, cwd=outside))


def test_exit_16_when_the_profile_is_not_valid_yaml(tmp_path):
    assert_exit_16(run(tmp_path, "--title", "t", profile="git: [unclosed\n"))


@pytest.mark.parametrize("environments", [{}, "dev", 3], ids=["mapping", "string", "number"])
def test_exit_16_when_environments_is_present_but_not_a_list(tmp_path, environments):
    assert_exit_16(run(tmp_path, "--title", "t", profile=make_profile(environments=environments)))


def test_exit_16_when_an_environment_entry_is_not_a_mapping(tmp_path):
    assert_exit_16(run(tmp_path, "--title", "t", profile=make_profile(environments=["dev"])))


def test_exit_16_when_the_profile_is_not_a_mapping(tmp_path):
    assert_exit_16(run(tmp_path, "--title", "t", profile="- a\n- b\n"))


def test_exit_16_holds_even_with_a_valid_recorded_path(tmp_path):
    assert_exit_16(run(tmp_path, "--title", "t", "--recorded-path", "deployed", profile=None))


@pytest.mark.parametrize(
    "args",
    [[], ["--label", "Spike"], ["--title", "t", "--bogus"], ["--title"]],
    ids=["no-title", "label-only", "unknown-flag", "title-without-value"],
)
def test_a_malformed_command_line_exits_2(tmp_path, args):
    res = run(tmp_path, *args, profile=make_profile(environments=[]))
    assert res.returncode == 2
    assert res.stdout == ""


def test_skills_json_lists_select_path_for_exactly_the_three_skills():
    executables = json.loads((ROOT / "skills.json").read_text())["executables"]
    listed = sorted(skill for skill, names in executables.items() if "select-path.py" in names)
    assert listed == sorted(SKILLS)


@pytest.mark.parametrize("skill", SKILLS)
def test_the_vendored_copy_runs_through_python3_like_the_source(tmp_path, skill):
    copy = ROOT / "skills" / skill / "scripts" / "select-path.py"
    assert not os.access(copy, os.X_OK)
    assert copy.read_text().splitlines()[1] == SOURCE.read_text().splitlines()[0] == "#!/usr/bin/env python3"
    (tmp_path / "profile.yaml").write_text(yaml.safe_dump(make_profile(environments=[])))
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(HOME=str(tmp_path), AGENT_SKILLS_PROFILE=str(tmp_path / "profile.yaml"))
    res = subprocess.run(
        [sys.executable, str(copy), "--title", "t"], env=env, cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert (res.returncode, res.stdout) == (0, "no-deployment\n")
