"""Both shipped profiles validate and seat three engineer voters (SKL-181 AC12)."""

import json
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())
REPO_PROFILE = ROOT / ".agent-skills" / "profile.yaml"
EXAMPLE_PROFILE = ROOT / "profile" / "example.yaml"


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def reviewer_problems(profile: dict) -> list[str]:
    reviewers = profile["refinement"]["reviewers"]
    problems = []
    if len(reviewers) != 3:
        problems.append(f"expected exactly three reviewers, found {len(reviewers)}")
    absent = [role.get("name") for role in reviewers if not role.get("family")]
    if absent:
        problems.append(f"reviewers without a family: {absent}")
    families = [role.get("family") for role in reviewers]
    if len(set(families)) != len(families):
        problems.append(f"reviewer families are not pairwise distinct: {families}")
    models = [role.get("model") for role in reviewers]
    if len(set(models)) != len(models):
        problems.append(f"reviewer model ids are not pairwise distinct: {models}")
    return problems


def test_repo_and_example_profiles_validate():
    repo = load(REPO_PROFILE)
    example = load(EXAMPLE_PROFILE)
    for path, profile in ((REPO_PROFILE, repo), (EXAMPLE_PROFILE, example)):
        jsonschema.validate(profile, SCHEMA)
        assert reviewer_problems(profile) == [], path
    assert repo["refinement"]["reviewers"][2]["name"] != repo["refinement"]["product_owner"]["name"]
