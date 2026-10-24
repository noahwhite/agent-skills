"""Contract checks for the persona-release-manager skill."""

import json
import re
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "persona-release-manager" / "SKILL.md"
MANIFEST = json.loads((ROOT / "skills.json").read_text())


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def test_skill_file_exists() -> None:
    assert SKILL.is_file(), f"missing {SKILL.relative_to(ROOT)}"


def test_manifest_registers_skill() -> None:
    required = {"github", "linear", "code-review", "todo-tracking"}
    assert required <= set(MANIFEST["skills"]["persona-release-manager"])


def test_todo_tracking_has_seed_entry() -> None:
    text = (ROOT / "shared" / "todo-tracking.md").read_text()
    assert "- **persona-release-manager:**" in text


def test_readme_lists_skill_in_table() -> None:
    row = "| [`persona-release-manager`](skills/persona-release-manager/SKILL.md) |"
    in_fence = False
    in_skills = False
    found = False
    for line in (ROOT / "README.md").read_text().splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if line.startswith("## "):
            in_skills = line.strip() == "## Skills"
            continue
        if in_skills and not in_fence and line.startswith(row):
            found = True
    assert found, "missing persona-release-manager row from the README Skills table"


def test_skill_links_to_required_references() -> None:
    text = SKILL.read_text()
    for name in ("profile", "todo-tracking", "github", "linear", "code-review", "runtimes"):
        assert f"](references/{name}.md)" in text, name


def test_persona_boundary_declares_each_owner() -> None:
    body = section(SKILL.read_text(), "Persona boundary").lower()
    for phrase in (
        "engineering-workflow",
        "ends at the integration environment",
        "persona-platform-sre",
        "executes deploy and rollback mechanics",
        "qa-verification",
        "owns post-deploy evidence",
        "persona-product-owner",
        "owns status transitions and closure",
        "release orchestration",
        "readiness",
        "the promotion pr",
        "production verification coordination",
        "hand-offs",
        "does not execute deploys or rollback",
    ):
        assert phrase in body, f"boundary missing: {phrase}"


def test_readiness_section_covers_each_promotion_mode() -> None:
    body = section(SKILL.read_text(), "Release readiness").lower()
    for phrase in (
        "profile.git.promotion",
        "enumerates the issues included in the promotion",
        "passing pre-production verification evidence",
        "last environment in `profile.environments` whose `production` is not true",
        "integration branch is the release branch",
        "each story's own deploy verification",
        "missing evidence stops the promotion and names the issue",
        "promotion head",
        "re-check",
        "stale",
        "there is no promotion set and no promotion pr",
        "tree is identical to the verified build",
        "evidence-only commits",
        "compare the code tree",
        "evidence for an earlier build, or for a head that a later merge or review fix changed, is stale and stops the promotion",
        "story-scoped promotion branch",
        "rather than the integration branch head",
    ):
        assert phrase in body, f"readiness missing: {phrase}"
    whole = SKILL.read_text().lower()
    for forbidden in ("promotion set under `none`", "promotion set for `none`", "stale evidence is accepted", "accept stale evidence"):
        assert forbidden not in whole, f"readiness contradicts itself: {forbidden}"


def test_promotion_section_cites_and_does_not_redefine() -> None:
    body = section(SKILL.read_text(), "Promotion").lower()
    for phrase in (
        "follows `profile.git.promotion` exactly",
        "references/github.md",
        "promotion",
        "does not redefine",
        "none",
        "whole-branch",
        "per-story",
        "single story's change",
        "never open a promotion pr that carries another story",
        "`per-story` promotion mechanism",
        "cites",
        "stop and ask only for a profile value the profile does not set",
        "never for a mechanism the promotion section defines",
        "three-dot diff",
        "no back-merges",
    ):
        assert phrase in body, f"promotion missing: {phrase}"
    for removed in ("story-scoped mechanism", "stop and ask for it"):
        assert removed not in body, f"promotion still asks for a defined mechanism: {removed}"
    whole = SKILL.read_text().lower()
    for forbidden in ("batch all pending stories", "batch the promotion", "batch stories into",
                      "include every pending story", "every pending story in one promotion"):
        assert forbidden not in whole, f"promotion contradicts no-batching: {forbidden}"


def test_review_section_covers_the_cumulative_diff_and_ownership() -> None:
    body = section(SKILL.read_text(), "Promotion review").lower()
    for phrase in (
        "review of record",
        "whole cumulative diff",
        "current head",
        "references/code-review.md",
        "owning story",
        "integration branch",
        "references/github.md",
        "promotion",
        "under `whole-branch`",
        "story-scoped promotion branch",
        "fresh pre-production verification",
        "post the review of record on the pr as a `--comment` pr review before the merge",
    ):
        assert phrase in body, f"review missing: {phrase}"


def test_release_profile_contract() -> None:
    schema = json.loads((ROOT / "profile" / "schema.json").read_text())
    release = schema["properties"]["release"]
    assert schema["additionalProperties"] is False
    assert "release" not in schema["required"]
    assert release["type"] == "object"
    assert release["additionalProperties"] is False
    assert not release.get("required")
    expected = {
        "versioning": {"semver", "calver"},
        "notes": {"github-release", "tracker-comment"},
    }
    assert set(release["properties"]) == set(expected)
    example = yaml.safe_load((ROOT / "profile" / "example.yaml").read_text())
    for key, values in expected.items():
        prop = release["properties"][key]
        assert sorted(prop["enum"]) == sorted(values)
        assert prop["description"].strip()
        assert example["release"][key] in values
    jsonschema.validate(example["release"], release)


def test_promotion_release_type_has_a_validated_request_source() -> None:
    body = section(SKILL.read_text(), "Promotion")
    for phrase in (
        "tracker description",
        "Release-Type: major|minor|patch",
        "highest component any promoted story requests",
        "exact lowercase",
        "malformed or duplicate",
        "stop and ask",
    ):
        assert phrase in body, f"release type missing: {phrase}"


def test_versioning_section_covers_release_schemes() -> None:
    body = section(SKILL.read_text(), "Versioning")
    for phrase in (
        "profile.release.versioning",
        "v0.1.0",
        "Release-Type",
        "major",
        "minor",
        "patch",
        "YYYY.MM.DD",
        "Use the bare date when it is free",
        "Only when the bare date tag is taken",
        "lowest integer N at or above 1 whose tag is free",
        "untagged",
        "profile.git.release_branch",
        "highest of those tags by numeric semantic version",
        "increment the selected component",
        "reset every component to its right to zero",
        "v3.0.0",
        "v2.4.0",
        "v2.3.5",
        "already carries",
        "reuse that tag",
        "annotated",
        "signed when `profile.git.signed_commits` is true",
        "push that tag to `origin`",
        "If it already exists, stop and report the collision",
        "never move or force-update a tag",
        "If signing fails, stop and report",
    ):
        assert phrase in body, f"versioning missing: {phrase}"
    for forbidden in (
        "force-update the tag when the commit matches",
        "create an unsigned tag if signing fails",
    ):
        assert forbidden not in body.lower(), f"unsafe versioning: {forbidden}"


def test_release_notes_section_covers_destinations_and_safety() -> None:
    body = section(SKILL.read_text(), "Release notes")
    for phrase in (
        "profile.release.notes",
        "github-release",
        "tracker-comment",
        "requires a tag",
        "auto-generated",
        "issue set enumerated in Release readiness",
        "each issue's merged PRs",
        "immediately after the tag is confirmed on `origin` and before the deployment hand-off",
        "report the published URL",
        "If versioning did not produce and confirm a tag, stop publication",
        "reuse the already confirmed tag",
        "existing per-issue tracker comment",
        "retry only missing entries",
    ):
        assert phrase in body, f"release notes missing: {phrase}"


def test_release_sections_follow_promotion_review_before_production() -> None:
    text = SKILL.read_text()
    headings = (
        "Promotion review",
        "Versioning",
        "Release notes",
        "Production verification",
    )
    positions = []
    for heading in headings:
        matches = list(re.finditer(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE))
        assert len(matches) == 1, f"expected one section: {heading}"
        positions.append(matches[0].start())
    assert positions == sorted(positions)


def test_production_verification_section_covers_evidence_and_failure() -> None:
    body = section(SKILL.read_text(), "Production verification").lower()
    for phrase in (
        "post-deploy evidence",
        "qa-verification",
        "recorded against it",
        "reopens the owning story",
        "references/linear.md",
        "no existing",
        "criterion covers the failure",
        "record on the epic whether rollback is indicated",
        "with the evidence behind that judgment",
        "rollback",
        "persona-platform-sre",
        "each production environment it reaches",
        "every story awaiting closure",
        "evidence and status",
    ):
        assert phrase in body, f"production verification missing: {phrase}"


def test_handoffs_name_every_owning_skill() -> None:
    body = section(SKILL.read_text(), "Hand-offs").lower()
    for phrase in (
        "engineering-workflow",
        "persona-platform-sre",
        "qa-verification",
        "persona-product-owner",
        "deploy",
        "rollback",
        "post-deploy evidence",
        "status",
        "never executes either",
        "merge result",
        "deploy or rollback execution result",
        "does not execute deploy or rollback mechanics",
    ):
        assert phrase in body, f"hand-offs missing: {phrase}"
    whole = SKILL.read_text().lower()
    for forbidden in ("may execute deploy", "release manager executes", "skill executes deploy"):
        assert forbidden not in whole, f"boundary breach allowed: {forbidden}"
