"""Mutation proof for tests/test_full_suite_switch.py (SKL-361, A4).

Each test of the full-suite option's behaviour must fail when the option is ignored. For each one,
this file copies the sources into a temporary directory, applies one named mutation there, runs
that test and asserts it fails, then runs it on an unmodified copy and asserts it passes. The
schema-shape and dirty-tree tests are exempt.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEST_FILE = "tests/test_full_suite_switch.py"
RESOLVER = "shared/resolve-full-suite.py"
PIPELINE = "skills/adversarial-review-pipeline/scripts/run-adversarial-pipeline.sh"
SKILL_MD = "skills/adversarial-review-pipeline/SKILL.md"
SOURCES = ("pyproject.toml", "profile/schema.json", RESOLVER, "skills/adversarial-review-pipeline", TEST_FILE)

RESOLVE_CALL = 'FULL_SUITE="$(python3 "$SCRIPT_DIR/resolve-full-suite.py" < /dev/null)"'
OFF_BRANCH = '      if [ "$FULL_SUITE" = "off" ]; then\n        echo "## 2. The suite (full-suite: off'

# (mutation name, file, original text, replacement, test it must break)
MUTATIONS = [
    ("teams-ignored", RESOLVER, "if isinstance(team, str) and team in teams:", "if False:",
     "test_an_off_key_with_teams_off_on_resolves_on"),
    ("teams-ignored-for-skl", RESOLVER, "if isinstance(team, str) and team in teams:", "if False:",
     "test_an_skl_key_resolves_off_from_its_team"),
    ("default-ignored", RESOLVER, 'return node.get("default", "off")', 'return "off"',
     "test_a_team_missing_from_teams_falls_to_a_default_of_on"),
    ("story-key-ignored", RESOLVER, "if story_key is not None:", "if False:",
     "test_a_team_missing_from_teams_falls_to_a_default_of_off"),
    ("team-key-ignored", RESOLVER, 'team = tracker.get("team_key") if isinstance(tracker, dict) else None', "team = None",
     "test_without_a_story_key_the_team_is_the_tracker_team_key"),
    ("final-fallback-on", RESOLVER, 'return node.get("default", "off")', 'return node.get("default", "on")',
     "test_a_profile_without_full_suite_resolves_off"),
    ("explicit-argument-ignored", RESOLVER, "    if args.value is not None:\n        print(args.value)\n        return 0\n", "",
     "test_an_explicit_argument_overrides_the_profile"),
    ("no-profile-resolves-on", RESOLVER, 'value = "off" if path is None else', 'value = "on" if path is None else',
     "test_no_profile_anywhere_resolves_off"),
    ("profile-validation-skipped", RESOLVER, "    node = full_suite(doc, path)\n", '    node = doc.get("full_suite") or {}\n',
     "test_a_profile_value_outside_the_schema_fails_closed"),
    ("tracker-team-key-type-unchecked", RESOLVER, "        if team is not None and not isinstance(team, str):\n", "        if False:\n",
     "test_an_unquoted_tracker_team_key_fails_closed"),
    ("flag-accepted-on-every-command", PIPELINE, '  [ "$cmd" = "preflight" ] ||', "  true ||",
     "test_full_suite_on_a_command_other_than_preflight_is_refused"),
    ("value-choices-dropped", RESOLVER, 'parser.add_argument("--value", choices=VALUES,', 'parser.add_argument("--value",',
     "test_a_malformed_command_line_exits_2"),
    ("preflight-off-ignored", PIPELINE, OFF_BRANCH, OFF_BRANCH.replace('[ "$FULL_SUITE" = "off" ]', "false"),
     "test_preflight_with_full_suite_off_runs_no_test_command_and_logs_off"),
    ("preflight-on-ignored", PIPELINE, OFF_BRANCH, OFF_BRANCH.replace('[ "$FULL_SUITE" = "off" ]', "true"),
     "test_preflight_with_full_suite_on_runs_the_test_command"),
    ("omitted-flag-is-on", PIPELINE, RESOLVE_CALL, 'FULL_SUITE="on"',
     "test_preflight_without_the_flag_and_without_a_profile_resolves_off"),
    ("omitted-flag-ignores-profile", PIPELINE, RESOLVE_CALL, 'FULL_SUITE="off"',
     "test_preflight_without_the_flag_reads_the_repository_profile"),
    ("invalid-value-accepted", PIPELINE, "    on|off) ;;\n", "    *) ;;\n",
     "test_preflight_rejects_an_invalid_full_suite_value_with_usage"),
    ("skill-command-drops-flag", SKILL_MD, '--full-suite "<on or off>" ', "",
     "test_the_skill_preflight_command_passes_full_suite"),
]


def copy_sources(dest: Path) -> Path:
    for rel in SOURCES:
        src, out = ROOT / rel, dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, out, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, out)
    return dest


def run_test(copy: Path, test: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"{TEST_FILE}::{test}"],
        cwd=copy, capture_output=True, text=True, timeout=600,
    )


@pytest.fixture(scope="module")
def pristine(tmp_path_factory) -> Path:
    return copy_sources(tmp_path_factory.mktemp("pristine"))


def test_every_mutated_test_exists_and_every_exemption_is_named():
    text = (ROOT / TEST_FILE).read_text()
    tests = {line.split("(")[0][4:] for line in text.splitlines() if line.startswith("def test_")}
    covered = {m[4] for m in MUTATIONS}
    assert covered <= tests, covered - tests
    exempt = {
        "test_the_schema_defines_full_suite_with_exactly_default_and_teams",
        "test_the_schema_accepts_teams_off_on",
        "test_the_schema_rejects_a_lowercase_team_key_or_a_non_enum_value",
        "test_preflight_with_full_suite_off_still_fails_a_dirty_tree",
    }
    assert tests - covered == exempt, tests - covered


@pytest.mark.parametrize("name, rel, old, new, test", MUTATIONS, ids=[f"{m[0]}:{m[4]}" for m in MUTATIONS])
def test_the_mutation_breaks_the_test_and_the_original_passes(tmp_path, pristine, name, rel, old, new, test):
    mutated = copy_sources(tmp_path / "mutated")
    target = mutated / rel
    text = target.read_text()
    assert text.count(old) == 1, f"mutation {name}: the original text is not found exactly once in {rel}"
    target.write_text(text.replace(old, new))
    broken = run_test(mutated, test)
    assert broken.returncode == 1, f"mutation {name} did not break {test}:\n{broken.stdout}{broken.stderr}"
    kept = run_test(pristine, test)
    assert kept.returncode == 0, f"{test} fails on the unmodified copy:\n{kept.stdout}{kept.stderr}"
