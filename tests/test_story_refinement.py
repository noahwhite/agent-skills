"""Contract checks for the story-refinement skill and its profile keys."""

import json
import re
from pathlib import Path

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "story-refinement" / "SKILL.md"
RECORD = ROOT / "skills" / "story-refinement" / "references" / "refinement-record.md"
SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())
MANIFEST = json.loads((ROOT / "skills.json").read_text())

GENERATED_REFERENCES = ["profile", "runtimes", "linear", "todo-tracking", "engineering-practice"]

REQUIRED_PHRASES = [
    "profile.refinement.facilitator",
    "profile.refinement.product_owner",
    "profile.refinement.reviewers",
    "profile.refinement.point_cap",
    "profile.workspace.scratch_dir",
    "profile.tracker.estimate_scale",
    "non-voting",
    "factual, reference-only",
    "anchoring",
    "effective accepted maximum",
    "original issue stays the core slice",
    "never average",
    "two rounds",
    "`ACCEPT`",
    "`OBJECT`",
    "refinement comment id",
    "high and the low",
    "different model families",
    "never run two voters from the same model family",
    "both reviewers must set `family` or both must omit it",
    "complete refined story and acs",
    "newly created voter contexts",
    "split trigger is met",
    "uses its new comment id as the refined version",
    "records the set of values it accepts",
    "highest value in the intersection",
    "is 8 or more",
    "schema maximum of 8",
    "persona-scrum-master",
    "references/refinement-record.md",
]

CROSS_SKILLS = [
    "persona-product-owner",
    "persona-scrum-master",
    "engineering-workflow",
]

BARE_NEUTRAL = re.compile(r"(?<!runtime-)\bneutral", re.IGNORECASE)
RUNTIME_TERMS = re.compile(
    r"\b(TaskCreate|TaskUpdate|TodoWrite|todowrite|AskUserQuestion|subagent_type|CLAUDE_JOB_DIR)\b"
    r"|mcp__|~/\.claude/|\.opencode/"
)


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def test_skill_file_exists() -> None:
    assert SKILL.is_file(), f"missing {SKILL.relative_to(ROOT)}"


def test_frontmatter_is_valid() -> None:
    text = SKILL.read_text()
    assert text.startswith("---\n")
    head, body = text[4:].split("\n---\n", 1)
    meta = yaml.safe_load(head)
    assert meta["name"] == "story-refinement"
    assert set(meta) <= {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    assert "refinement" in meta["description"].lower()
    assert "pointing" in meta["description"].lower()
    assert meta["license"] == "Apache-2.0"
    assert 1 <= len(meta["compatibility"]) <= 500
    assert len(body.splitlines()) < 500


def test_skill_defines_two_stages_and_four_steps() -> None:
    text = SKILL.read_text()
    for heading in (
        "Stage 1: refinement",
        "Step 1: Independent refinement",
        "Step 2: Reconciliation and the accept round",
        "Stage 2: pointing",
        "Step 3: Secret pointing",
        "Step 4: High/low discussion and consensus",
    ):
        assert re.search(rf"^#+ {re.escape(heading)}\s*$", text, re.MULTILINE), heading


def test_each_step_names_inputs_outputs_and_stops() -> None:
    text = SKILL.read_text()
    for heading in (
        "Step 1: Independent refinement",
        "Step 2: Reconciliation and the accept round",
        "Step 3: Secret pointing",
        "Step 4: High/low discussion and consensus",
    ):
        match = re.search(rf"^### {re.escape(heading)}\s*$", text, re.MULTILINE)
        assert match, heading
        rest = text[match.end():]
        following = re.search(r"^###? ", rest, re.MULTILINE)
        body = rest[: following.start()] if following else rest
        for label in ("**Inputs:**", "**Outputs:**", "**Stop:**"):
            assert label in body, f"{heading} missing {label}"


def test_manifest_registers_skill() -> None:
    assert MANIFEST["skills"]["story-refinement"] == [
        "linear",
        "todo-tracking",
        "engineering-practice",
    ]


def test_schema_has_refinement_object() -> None:
    refinement = SCHEMA["properties"]["refinement"]
    assert refinement["type"] == "object"
    assert refinement["additionalProperties"] is False
    props = refinement["properties"]
    assert props["facilitator"]["$ref"] == "#/$defs/refinement_role"
    assert props["product_owner"]["$ref"] == "#/$defs/refinement_role"
    reviewers = props["reviewers"]
    assert reviewers["type"] == "array"
    assert reviewers["minItems"] == 2
    assert reviewers["maxItems"] == 2
    assert reviewers["items"]["$ref"] == "#/$defs/refinement_role"
    point_cap = props["point_cap"]
    assert point_cap["type"] == "integer"
    assert point_cap["minimum"] == 1
    assert point_cap["maximum"] == 8
    assert point_cap["default"] == 5


def test_refinement_role_shape() -> None:
    role = SCHEMA["$defs"]["refinement_role"]
    assert role["type"] == "object"
    assert role["additionalProperties"] is False
    assert set(role["required"]) == {"name", "runtime", "model"}
    props = role["properties"]
    assert set(props) == {"name", "runtime", "model", "agent", "command", "family"}
    assert set(props["runtime"]["enum"]) == {"opencode", "command", "codex", "claude-code"}
    assert any("command" in rule.get("then", {}).get("required", []) for rule in role.get("allOf", []))


def test_refinement_role_requires_command_for_command_runtime() -> None:
    role = SCHEMA["$defs"]["refinement_role"]
    instance = {"name": "Facilitator", "runtime": "command", "model": "generic-model"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance, role)
    instance["command"] = "generic-agent --prompt {prompt_file}"
    jsonschema.validate(instance, role)


def test_example_sets_refinement_values() -> None:
    refinement = yaml.safe_load((ROOT / "profile" / "example.yaml").read_text())["refinement"]
    for key in ("facilitator", "product_owner"):
        role = refinement[key]
        assert role["name"] and role["runtime"] and role["model"]
    reviewers = refinement["reviewers"]
    assert len(reviewers) == 2
    families = [role.get("family") for role in reviewers]
    models = [role["model"] for role in reviewers]
    assert all(families) or not any(families), "reviewer family settings must be all-set or all-unset"
    if all(families):
        assert len(set(families)) == 2, "reviewer families must differ"
    else:
        assert len(set(models)) == 2, "reviewer models must differ"
    assert refinement["point_cap"] == 5


def test_readme_lists_skill() -> None:
    assert "skills/story-refinement/SKILL.md" in (ROOT / "README.md").read_text()


def test_todo_tracking_has_seed_entry() -> None:
    assert "story-refinement:" in (ROOT / "shared" / "todo-tracking.md").read_text()


def test_record_reference_has_templates_and_phrasing_table() -> None:
    text = RECORD.read_text()
    for phrase in (
        "Refinement comment",
        "Pointing record",
        "Permitted",
        "Forbidden",
        "I would go higher",
        "I would go lower",
        "target",
        "realistic",
        "re-vote",
        "comparing individual votes",
    ):
        assert phrase.lower() in text.lower(), phrase


def test_skill_links_every_required_reference() -> None:
    text = SKILL.read_text()
    for name in GENERATED_REFERENCES:
        assert f"references/{name}.md" in text, name
    assert "references/refinement-record.md" in text


def test_skill_contains_contract_phrases() -> None:
    text = SKILL.read_text()
    lowered = text.lower()
    missing = [phrase for phrase in REQUIRED_PHRASES if phrase.lower() not in lowered]
    assert not missing, f"missing phrases: {missing}"


def test_skill_has_no_bare_neutral_term() -> None:
    assert not BARE_NEUTRAL.search(SKILL.read_text())


def test_skill_has_no_runtime_specific_terms() -> None:
    assert not RUNTIME_TERMS.search(SKILL.read_text())


def test_cross_skill_prose_names_story_refinement() -> None:
    for name in CROSS_SKILLS:
        text = (ROOT / "skills" / name / "SKILL.md").read_text()
        assert "`story-refinement`" in text, name
        assert not re.search(r"\]\([^)]*story-refinement", text), f"{name} uses a relative link"


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def step(text: str, heading: str) -> str:
    match = re.search(rf"^### {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, heading
    rest = text[match.end():]
    following = re.search(r"^###? ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def test_step_one_probe_precedes_voter_launch() -> None:
    body = squash(step(SKILL.read_text(), "Step 1: Independent refinement"))
    probe = body.find("tracker-write preflight")
    launch = body.find("launch the po and both engineers")
    assert probe != -1, "missing tracker-write preflight"
    assert launch != -1, "missing voter launch"
    assert probe < launch, "the probe must precede the voter launch"


def test_step_one_probe_is_a_comment_the_po_posts_and_reads_back() -> None:
    body = squash(step(SKILL.read_text(), "Step 1: Independent refinement"))
    assert "posts one comment on the story under refinement that marks itself as the tracker-write preflight" in body
    assert "reads it back" in body
    assert "records the comment id for the refinement record" in body


def test_step_one_probe_denial_stops_before_any_voter() -> None:
    body = squash(step(SKILL.read_text(), "Step 1: Independent refinement"))
    assert "if the write is denied, no voter launches" in body
    assert "reports `needs input` to the owner naming the denied write" in body
    assert 'the "tracker writes from a subagent" rule in `references/runtimes.md`' in body


def test_step_one_no_comment_rule_has_the_probe_as_only_exception() -> None:
    body = squash(step(SKILL.read_text(), "Step 1: Independent refinement"))
    assert (
        "no tracker comment is posted until all three voter inputs are recorded, "
        "except the tracker-write preflight, which is the only exception" in body
    )
    assert "probe exercises comment add only" in body


RUNTIMES = ROOT / "shared" / "runtimes.md"


def tracker_rule() -> str:
    text = RUNTIMES.read_text()
    match = re.search(r"^- \*\*Tracker writes from a subagent\.\*\*", text, re.MULTILINE)
    assert match, "missing the Tracker writes from a subagent rule"
    rest = text[match.end():]
    following = re.search(r"^(?:- \*\*|## )", rest, re.MULTILINE)
    return squash(rest[: following.start()] if following else rest)


def test_runtimes_table_has_tracker_writes_row() -> None:
    rows = [line for line in RUNTIMES.read_text().splitlines() if line.startswith("| Tracker writes from a subagent |")]
    assert len(rows) == 1, rows
    assert rows[0].count("|") == 4, "the row needs a Claude Code cell and an opencode cell"


def test_runtimes_rule_states_the_claude_code_observations() -> None:
    rule = tracker_rule()
    assert "on 2026-10-21 a subagent's tracker write was denied by the auto-mode permission check" in rule
    assert "although a matching `permissions.allow` rule existed" in rule


def test_runtimes_rule_states_the_write_that_later_passed() -> None:
    rule = tracker_rule()
    assert "passed in a later session after the owner's own message in that session asked for po tracker writes" in rule


def test_runtimes_rule_states_relayed_approval_was_not_accepted() -> None:
    assert "approval relayed by the facilitator was not accepted" in tracker_rule()


def test_runtimes_rule_states_only_the_owner_can_grant_the_permission() -> None:
    rule = tracker_rule()
    assert "an agent's edit of the auto-mode allow list was denied as self-modification" in rule
    assert "only the owner can grant the permission" in rule


def test_runtimes_rule_names_an_owner_action_decided_by_the_probe() -> None:
    rule = tracker_rule()
    assert "state the authorization in the session before the ceremony, or add the permission themselves" in rule
    assert "the preflight probe in step 1 of `story-refinement` is the deciding check" in rule


def test_runtimes_rule_maps_opencode_to_the_agent_file_bash_permission() -> None:
    rule = tracker_rule()
    assert "agent file's `permission.bash`" in rule
    assert "opencode 1.x names" in rule
    assert "skl-23" in rule


def test_vendored_runtimes_copies_carry_the_rule() -> None:
    copy = ROOT / "skills" / "story-refinement" / "references" / "runtimes.md"
    assert copy.read_text().endswith(RUNTIMES.read_text())


def denied_writes() -> str:
    return squash(section(SKILL.read_text(), "Denied tracker writes"))


def test_fallback_covers_the_probe_and_any_later_write() -> None:
    assert "whenever a po tracker write is denied, the probe or any later write, the ceremony stops" in denied_writes()


def test_fallback_needs_the_owner_directly_in_the_facilitator_conversation() -> None:
    assert (
        "unless the owner directly authorizes the facilitator in the facilitator's own conversation"
        in denied_writes()
    )


def test_fallback_quotes_the_authorization_verbatim_in_the_record() -> None:
    assert "quote the owner's authorization verbatim in the record" in denied_writes()


def test_fallback_keeps_the_po_as_author_and_the_facilitator_as_applier() -> None:
    body = denied_writes()
    assert "the po still authors every write: target, fields, and body file" in body
    assert "the facilitator applies each write verbatim and reads it back" in body


def test_fallback_forbids_relayed_approval() -> None:
    assert (
        "a subagent's report, a notification, or another agent's claim of approval never counts"
        in denied_writes()
    )


def test_fallback_forbids_retry_through_a_different_tool_or_server() -> None:
    assert "never retry a denied write through a different tool or server" in denied_writes()


def test_roles_make_the_po_the_only_author_of_tracker_writes() -> None:
    roles = squash(section(SKILL.read_text(), "Roles"))
    assert "the only author of tracker writes" in roles
    assert "only tracker mutator" not in roles


def test_roles_limit_the_facilitator_to_applying_under_the_fallback() -> None:
    roles = squash(section(SKILL.read_text(), "Roles"))
    assert "the facilitator applies tracker writes only under the denied tracker writes fallback" in roles


PREFLIGHT_LINE = "- Tracker-write preflight: comment <id>"
WRITES_PO_LINE = "- Tracker writes: product owner"
WRITES_FACILITATOR_LINE = (
    "- Tracker writes: facilitator on the product owner's behalf "
    '(owner\'s direct authorization: "<verbatim quote>", <date>)'
)


def template_block(heading: str) -> tuple[str, str]:
    """The first fenced block under the heading, and the text from the heading to the next template."""
    text = RECORD.read_text()
    start = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert start, heading
    rest = text[start.end():]
    block = re.search(r"```markdown\n(.*?)```", rest, re.DOTALL)
    assert block, f"no template block under {heading}"
    after = rest[block.end():]
    nxt = re.search(r"^## ", after, re.MULTILINE)
    return block.group(1), after[: nxt.start()] if nxt else after


def template(heading: str) -> str:
    return template_block(heading)[0]


def fallback_alternative(heading: str) -> str:
    return template_block(heading)[1]


@pytest.mark.parametrize("heading", ["Refinement comment", "Pointing record"])
def test_template_carries_the_preflight_line(heading: str) -> None:
    assert PREFLIGHT_LINE in template(heading).splitlines()


@pytest.mark.parametrize("heading", ["Refinement comment", "Pointing record"])
def test_template_carries_the_product_owner_writes_line(heading: str) -> None:
    assert WRITES_PO_LINE in template(heading).splitlines()


@pytest.mark.parametrize("heading", ["Refinement comment", "Pointing record"])
def test_template_carries_the_facilitator_writes_alternative(heading: str) -> None:
    assert WRITES_FACILITATOR_LINE in fallback_alternative(heading).splitlines()
