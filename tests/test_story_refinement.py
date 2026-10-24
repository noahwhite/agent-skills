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


def section(text: str, heading: str, level: int = 2) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)  # commented-out text is not operative
    match = re.search(rf"^{'#' * level} {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(rf"^#{{1,{level}}} ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def flat(text: str) -> str:
    return " ".join(text.lower().split())


def bullet(body: str, label: str) -> str:
    match = re.search(rf"^- \*\*{re.escape(label)}:\*\*(.*?)(?=^- \*\*|\Z)", body, re.MULTILINE | re.DOTALL)
    assert match, f"missing {label} line"
    return flat(match.group(1))


STEP_FOUR = "Step 4: High/low discussion and consensus"


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


def test_step_four_presents_three_paths_without_a_recommendation() -> None:
    body = flat(section(SKILL.read_text(), STEP_FOUR, level=3))
    assert "if the intersection is empty, record no consensus and run the no-consensus decision" in body
    assert (
        "the facilitator presents only the empty intersection and the three paths: "
        "split, re-refine, or leave unpointed" in body
    )
    assert "the facilitator does not recommend a path" in body
    assert "record no consensus and leave the story unpointed" not in body, "the bare stop is the original defect"


def test_step_four_path_decision_is_the_intersection_with_a_po_tie_break() -> None:
    body = flat(section(SKILL.read_text(), STEP_FOUR, level=3))
    assert "each voter (the po and both engineers) records the set of paths it accepts" in body
    assert "a voter that accepts re-refine also lists the amendments it needs" in body
    assert "the chosen path is in the intersection of the three accepted path sets" in body
    assert "when that intersection holds more than one path, the po chooses among them and records why" in body
    assert "the facilitator records the decision; it does not choose it" in body


def test_step_four_empty_path_intersection_leaves_the_story_unpointed() -> None:
    body = flat(section(SKILL.read_text(), STEP_FOUR, level=3))
    assert "when that intersection is empty, the story is left unpointed" in body


def test_step_four_split_path_applies_the_split_rule() -> None:
    body = flat(section(SKILL.read_text(), STEP_FOUR, level=3))
    assert "split applies the split rule as a group-decided split" in body


def test_step_four_re_refine_returns_to_step_two_with_one_accept_round() -> None:
    body = flat(section(SKILL.read_text(), STEP_FOUR, level=3))
    assert "re-refine returns to step 2" in body
    assert "the po authors the amendments and an updated refinement comment and applies both" in body
    assert "under the denied tracker writes fallback, the facilitator applies the amendments and the updated refinement comment verbatim" in body
    assert "one accept round runs on the new comment id" in body
    assert "if all three voters do not return `accept`, the po records the story as unpointed" in body
    assert "on acceptance, step 3 re-runs blind with newly created voter contexts, then this step runs again" in body


def test_step_four_re_refine_is_offered_once() -> None:
    body = flat(section(SKILL.read_text(), STEP_FOUR, level=3))
    assert "re-refine is offered at most once per ceremony" in body
    assert "a second empty intersection offers only split or leave unpointed" in body


def test_step_four_outputs_and_stop_name_the_decision() -> None:
    body = section(SKILL.read_text(), STEP_FOUR, level=3)
    outputs = bullet(body, "Outputs")
    stop = bullet(body, "Stop")
    for line in (outputs, stop):
        assert "no-consensus decision" in line
        assert "leave unpointed" in line and "is the default when no path is in all three sets" in line
        assert re.search(r"re-refine runs (at most|only) once per ceremony", line)
    assert "the re-refine accept round ends without three `accept`" in stop


def test_split_rule_adds_the_group_decided_trigger() -> None:
    body = flat(section(SKILL.read_text(), "Split rule"))
    assert "a story is also split when the step 4 no-consensus decision chooses split (a group-decided split)" in body
    assert "this trigger adds to the consensus thresholds and does not change them" in body
    assert "if either split trigger is met, split the story" in body
    assert (
        "a story is split when its consensus is above `profile.refinement.point_cap` or is 8 or more; "
        "the lower trigger applies, and the 8-point rule in [references/linear.md](references/linear.md) is never relaxed" in body
    )


def test_split_rule_keeps_the_split_mechanics() -> None:
    body = flat(section(SKILL.read_text(), "Split rule"))
    for rule in (
        "the original issue stays the core slice",
        "siblings are created from the `linear-user-story` template",
        "the original issue blocks each sibling",
        "every acceptance criterion is mapped to a slice in the split comment",
    ):
        assert rule in body, rule


def test_split_rule_re_points_the_core_slice_after_a_group_decided_split() -> None:
    body = flat(section(SKILL.read_text(), "Split rule"))
    assert (
        "after a group-decided split, the core slice has no consensus value of its own, so the core slice and each sibling "
        "get their own blind three-voter estimate in one round, with newly created voter contexts" in body
    )


def pointing_template() -> list[str]:
    body, inside, fenced = [], False, False
    for line in RECORD.read_text().splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("## "):
            inside = line == "## Pointing record"
            continue
        if inside:
            body.append(line)
    templates = re.findall(r"^```markdown\n(## Pointing record\n.*?)^```", "\n".join(body) + "\n", re.MULTILINE | re.DOTALL)
    assert len(templates) == 1, f"expected one pointing-record template, found {len(templates)}"
    return templates[0].splitlines()


def test_refinement_template_records_the_re_refine_accept_round() -> None:
    line = "- Re-refine accept round (only after a Step 4 re-refine; one round): see the Accept round result comment"
    assert line in template("Refinement comment").splitlines()


def test_pointing_template_records_the_no_consensus_decision() -> None:
    lines = pointing_template()
    for line in (
        "- No-consensus decision: <split, re-refine, or leave unpointed; n/a when there is a consensus>",
        "- Paths accepted: <set per voter, or n/a>",
        "- Decision rationale: <one line, or n/a>",
    ):
        assert line in lines, line


def test_records_names_the_no_consensus_decision() -> None:
    body = flat(section(SKILL.read_text(), "Records"))
    assert "any no-consensus decision with each voter's accepted paths and the decision rationale" in body



def test_records_requires_every_challenge_with_its_outcome() -> None:
    body = flat(section(SKILL.read_text(), "Records"))
    assert "every challenge with its outcome" in body


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
    assert "run the tracker-write preflight before any voter launches" in body


def test_step_one_probe_is_a_comment_the_po_posts_and_reads_back() -> None:
    body = squash(step(SKILL.read_text(), "Step 1: Independent refinement"))
    assert "the po, in a separate context, posts one comment on the story under refinement that marks itself as the tracker-write preflight" in body
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
    assert "the step 2 stop stays as the backstop" in body


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


def test_runtimes_rule_version_qualifies_opencode_shell_permissions() -> None:
    rule = tracker_rule()
    assert "v2" in rule and "`shell`" in rule and "`permissions`" in rule
    assert "v1" in rule and "`permission.bash`" in rule


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


def test_step_two_stop_and_triage_defer_to_the_fallback() -> None:
    text = SKILL.read_text()
    assert "the po cannot write to the tracker and the owner has not authorized the denied tracker writes fallback" in squash(
        step(text, "Step 2: Reconciliation and the accept round")
    )
    assert "applies the po's writes only under the denied tracker writes fallback" in squash(section(text, "Triage"))


def test_probe_denial_has_a_resume_path_under_the_fallback() -> None:
    body = squash(step(SKILL.read_text(), "Step 1: Independent refinement"))
    assert "later write kinds fall under the denied tracker writes fallback" in body
    assert "after the owner acts, run the probe again" in body
    assert "if the owner directly authorizes the facilitator under the denied tracker writes fallback, the facilitator applies the po-authored probe verbatim, records its comment id, and the voters launch" in body


def test_record_allows_facilitator_posting_under_the_fallback() -> None:
    assert "posted by the product owner or, under the denied tracker writes fallback, by the facilitator verbatim" in squash(RECORD.read_text())


def test_runtimes_rule_does_not_claim_an_unobserved_fact() -> None:
    assert "nor needed" not in tracker_rule()


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
    alternative = fallback_alternative(heading)
    assert WRITES_FACILITATOR_LINE in alternative.splitlines()
    assert "Under the denied tracker writes fallback in `SKILL.md`, replace the tracker-writes line with:" in alternative.splitlines()


def test_roles_po_authors_and_applies_except_under_the_fallback() -> None:
    roles = squash(section(SKILL.read_text(), "Roles"))
    assert "authors the refinement comment and every other tracker write, applies each except under the denied tracker writes fallback" in roles


def test_step_two_refined_description_applied_verbatim_under_the_fallback() -> None:
    body = squash(step(SKILL.read_text(), "Step 2: Reconciliation and the accept round"))
    assert "the po authors the refinement comment and the refined description and applies both; otherwise, under the denied tracker writes fallback, the facilitator applies both verbatim." in body


def test_step_two_amendments_follow_the_same_apply_rule() -> None:
    body = squash(step(SKILL.read_text(), "Step 2: Reconciliation and the accept round"))
    assert "the po authors the amendments and an updated refinement comment and applies both; otherwise, under the denied tracker writes fallback, the facilitator applies the amendments and the updated refinement comment verbatim." in body


def test_triage_applies_and_reads_back_except_under_the_fallback() -> None:
    triage = squash(section(SKILL.read_text(), "Triage"))
    assert "applies and reads each one back, except under the denied tracker writes fallback" in triage


def test_runtimes_rule_says_an_allow_rule_alone_was_not_sufficient() -> None:
    assert "an allow rule alone was not sufficient" in tracker_rule()


def test_skill_never_says_the_po_posts_the_refinement_comment_unconditionally() -> None:
    assert "the po posts the refinement comment" not in squash(SKILL.read_text())


def test_step_two_unpointed_record_follows_the_apply_rule() -> None:
    body = squash(step(SKILL.read_text(), "Step 2: Reconciliation and the accept round"))
    assert "under the denied tracker writes fallback the facilitator applies it verbatim, and the ceremony stops" in body


def test_step_one_stop_covers_a_denied_preflight() -> None:
    body = squash(step(SKILL.read_text(), "Step 1: Independent refinement"))
    assert "or the tracker-write preflight is denied and the owner has not authorized the denied tracker writes fallback" in body


def test_fallback_reports_needs_input_and_resumes_at_the_denied_write() -> None:
    assert (
        "on a denied write the facilitator reports `needs input` to the owner naming the denied write, "
        "and resumes at that write once the owner authorizes the fallback"
    ) in denied_writes()


def test_fallback_never_reapplies_a_write_the_po_already_applied() -> None:
    assert (
        "a write the po already applied is never applied again, "
        "including where a step says the facilitator applies a set of writes; "
        "the facilitator applies only the denied write and the writes after it"
    ) in denied_writes()


def test_step_four_unpointed_record_follows_the_apply_rule() -> None:
    body = flat(section(SKILL.read_text(), STEP_FOUR, level=3))
    assert (
        "the po records the story as unpointed, or under the denied tracker writes fallback "
        "the facilitator applies the po-authored unpointed record verbatim"
    ) in body


def test_step_four_amendments_use_the_otherwise_apply_rule() -> None:
    body = flat(section(SKILL.read_text(), STEP_FOUR, level=3))
    assert "applies both; otherwise, under the denied tracker writes fallback, the facilitator applies the amendments and the updated refinement comment verbatim" in body


# SKL-51: a point measures complexity, never the amount of work or elapsed time.

STEP_THREE = "Step 3: Secret pointing"
POINTING_BASIS = (
    "A point or size measures complexity - design difficulty, interacting constraints, unknowns, "
    "and the risk of breaking existing behaviour - and never the amount of work or elapsed time; "
    "routine, well-understood work such as writing tests, opening a PR, review, running a fixture, "
    "or regenerating copies adds no points however long it takes."
)


def operative_step(heading: str) -> str:
    """A step's text with HTML comments removed, since commented-out text is not operative."""
    return step(re.sub(r"<!--.*?-->", "", SKILL.read_text(), flags=re.DOTALL), heading)


def spaced(text: str) -> str:
    """Whitespace collapsed to single spaces, case kept, so a pin compares the exact sentence."""
    return re.sub(r"\s+", " ", text).strip()


def process_items(heading: str) -> list[str]:
    """The numbered Process items of a step, each collapsed to one line with its case kept."""
    body = operative_step(heading)
    match = re.search(r"^- \*\*Process:\*\*\n(.*?)(?=^- \*\*)", body, re.MULTILINE | re.DOTALL)
    assert match, f"no Process list in {heading}"
    items = re.split(r"^  \d+\. ", match.group(1), flags=re.MULTILINE)
    return [spaced(item) for item in items[1:]]


def process_item(heading: str, start: str) -> str:
    """The one Process item of a step that starts with the given text."""
    found = [item for item in process_items(heading) if item.startswith(start)]
    assert len(found) == 1, f"expected one {heading} item starting {start!r}, found {len(found)}"
    return found[0]


def test_pointing_basis_appears_once_in_the_skill_and_inside_step_three() -> None:
    assert spaced(SKILL.read_text()).count(POINTING_BASIS) == 1
    assert squash(SKILL.read_text()).count(squash(POINTING_BASIS)) == 1
    assert POINTING_BASIS in spaced(operative_step(STEP_THREE))


def test_pointing_basis_is_its_own_item_right_after_the_launch_item() -> None:
    items = process_items(STEP_THREE)
    assert items[0].startswith("Launch the PO and both engineers again in separate contexts")
    assert items[1] == POINTING_BASIS


def test_step_three_requires_the_basis_in_every_pointing_prompt() -> None:
    assert process_items(STEP_THREE)[2] == (
        "The sentence above is the pointing basis. Every pointing prompt or prompt file carries it verbatim, "
        "including the re-run after a Step 4 re-refine and each slice estimate under the Split rule."
    )


def test_step_three_rationale_names_complexity_drivers_and_no_duration() -> None:
    body = process_item(STEP_THREE, "Each voter submits one point value")
    assert "plus a short complexity rationale." in body
    assert (
        "The rationale cites no duration, effort or run-cost measure, and it names complexity drivers only, "
        "each a property of the change: design difficulty, an interacting constraint, an unknown, or the risk "
        "of breaking existing behaviour."
    ) in body
    assert (
        "Verification strength, testability, coverage and the shape of the tests are also out of basis, and so "
        "is weighing a point value already recorded for this story, a prior story, a parent or sibling, or an "
        "inherited split."
    ) in body
    assert (
        "Verification strength is how well a behaviour is checked and breakage risk is what can silently change, "
        "so the first is out of basis and the second is a basis driver."
    ) in body
    assert "the complexity driver or drivers the voter weighed" not in body


def test_step_four_re_vote_carries_the_basis_by_reference_to_step_three() -> None:
    item = process_items(STEP_FOUR)[1]
    assert item.startswith("Run one re-vote.")
    assert "The re-vote prompt carries the pointing basis from Step 3." in item
    assert squash(POINTING_BASIS) not in squash(operative_step(STEP_FOUR))


def test_step_four_re_vote_requires_a_complexity_rationale() -> None:
    item = process_items(STEP_FOUR)[1]
    assert (
        "Each voter records the set of values it accepts for this story (one or more) or records no consensus, "
        "with a short complexity rationale under the Step 3 rationale rule."
    ) in item


SIZING_ITEM = "After all three values are recorded, the SM/EM may provide"


def test_step_three_sizing_context_is_in_complexity_terms() -> None:
    body = process_item(STEP_THREE, SIZING_ITEM)
    assert (
        "the SM/EM may provide factual, reference-only sizing context: comparable stories in complexity terms, "
        "comparable unknowns and constraints, and relevant scope differences."
    ) in body
    assert "historical sizing" not in squash(SKILL.read_text())
    assert (
        "It must not name, bound or imply any point value - a prior story's, an inherited split value, a value "
        "read from this story's own recorded pointing history, or one implied by a split status - and such a "
        "statement is an anchoring event under the Anchoring guardrail."
    ) in body


def test_step_three_sizing_context_forbids_any_point_value() -> None:
    body = process_item(STEP_THREE, SIZING_ITEM)
    for origin in ("a prior story's", "an inherited split value", "this story's own recorded pointing history", "a split status"):
        assert origin in body, origin
    assert "it must not name, bound or imply any point value" in body.lower()
    assert "is an anchoring event under the anchoring guardrail" in body.lower()


STEP_FOUR_ITEM_PREFIXES = [
    "Hold one discussion round that names only the high and the low.",
    "Run one re-vote.",
    "Consensus is the highest value in the intersection of the three accepted sets.",
    "Never average and never take a value silently.",
    "The facilitator records the consensus; it does not declare it.",
    "If the split trigger is met",
    "No-consensus decision:",
    "Split applies the split rule as a group-decided split.",
    "Re-refine returns to Step 2.",
]


def test_step_four_process_items_keep_their_count_and_order() -> None:
    items = process_items(STEP_FOUR)
    assert len(items) == len(STEP_FOUR_ITEM_PREFIXES)
    for index, prefix in enumerate(STEP_FOUR_ITEM_PREFIXES):
        assert items[index].startswith(prefix), (index, prefix)


def test_step_four_facilitator_challenges_every_off_basis_ground() -> None:
    item = process_items(STEP_FOUR)[0]
    assert (
        "In that round, and against the rationales recorded in Step 3, the facilitator challenges every ground "
        "outside the pointing basis, whether it is heard in the discussion or read in a recorded rationale."
    ) in item
    assert (
        "Challenging a ground is not comparing values or singling out a voter: the facilitator names the ground "
        "and its author, never the value."
    ) in item
    assert (
        "A challenged ground must be restated as a basis driver or retracted; the SM/EM withdraws or restates its "
        "own sizing comment on the same terms, except a statement that names, bounds or implies a point value, "
        "which is an anchoring event as soon as the facilitator sees it."
    ) in item
    assert "A ground that is neither is an anchoring event under the Anchoring guardrail." in item


def test_step_four_re_vote_challenges_an_off_basis_rationale() -> None:
    item = process_items(STEP_FOUR)[1]
    assert (
        "Recording an accepted set is not weighing a recorded value: the rationale for the set is about "
        "complexity, never about which value was recorded earlier."
    ) in item
    assert (
        "A re-vote rationale outside the pointing basis is challenged before the consensus is recorded, under "
        "the same restate-or-retract rule as item 1."
    ) in item


def test_anchoring_guardrail_makes_a_point_value_sizing_note_an_event_on_challenge() -> None:
    body = flat(section(SKILL.read_text(), GUARDRAIL))
    assert (
        "every ground outside the pointing basis is an anchoring trigger: a rationale or a sizing comment that "
        "weighs verification strength, testability, coverage, the shape of the tests, or a prior or inherited "
        "point value is challenged under step 4, and a sizing comment that names, bounds or implies a point "
        "value is an anchoring event as soon as the facilitator sees it, with no challenge, restatement or "
        "retraction path" in body
    )
    assert (
        "any other challenged ground that is neither restated as a basis driver nor retracted, or a sizing "
        "comment the sm/em neither withdraws nor restates, is an anchoring event, and the void re-runs the "
        "independent vote from step 3 in newly created voter contexts that exclude the tainted discussion and "
        "sizing comment" in body
    )


GUARDRAIL = "Anchoring guardrail"


def test_anchoring_guardrail_bans_naming_bounding_or_implying_a_point_value() -> None:
    body = flat(section(SKILL.read_text(), GUARDRAIL))
    assert (
        "for the sm/em, naming, bounding or implying a point value in sizing context or in the discussion, "
        "including a prior story's, an inherited split value, a value recorded on the story surface, or one "
        "implied by a split status" in body
    )


def test_anchoring_guardrail_names_off_basis_grounds_as_a_trigger() -> None:
    body = flat(section(SKILL.read_text(), GUARDRAIL))
    assert "every ground outside the pointing basis is an anchoring trigger" in body
    assert "verification strength, testability, coverage, the shape of the tests" in body


def test_anchoring_guardrail_explains_why_context_cannot_exclude_a_recorded_value() -> None:
    body = flat(section(SKILL.read_text(), GUARDRAIL))
    assert (
        "fresh voter contexts exclude the tainted discussion and the sizing comment, but they cannot exclude a "
        "point value recorded on the story surface that step 1 hands every voter with the story, so the step 3 "
        "rationale rule is what keeps such a value out of the vote" in body
    )


def test_anchoring_guardrail_recovery_mechanics_are_unchanged() -> None:
    body = spaced(section(SKILL.read_text(), GUARDRAIL))
    assert (
        "On anchoring: stop the round, record the comment verbatim, void the consensus and any vote recorded "
        "after the anchor, and re-run the independent vote with newly created voter contexts that exclude the "
        "tainted discussion and sizing comment. Never reuse the sessions that saw the anchor. Record the recovery."
    ) in body


def test_step_three_time_or_effort_statement_is_an_anchoring_event() -> None:
    body = process_item(STEP_THREE, SIZING_ITEM)
    assert "A statement of elapsed time or effort is an anchoring event under the Anchoring guardrail." in body


def phrasing_rows() -> list[tuple[str, str]]:
    body = section(RECORD.read_text(), "Permitted and forbidden phrasing")
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    start = next(index for index, line in enumerate(lines) if line.startswith("|"))
    end = max(index for index, line in enumerate(lines) if line.startswith("|"))
    table = lines[start : end + 1]
    assert table[1] == "|---|---|", "the phrasing table has no separator row"
    rows = []
    for line in table:
        assert line.startswith("|") and line.endswith("|"), f"a line inside the table is not a table row: {line}"
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert len(cells) == 2, line
        rows.append((cells[0], cells[1]))
    return rows[2:]


PHRASING_INTRO = [
    "The SM/EM may give factual, reference-only sizing context after all three values are recorded.",
    "Everything in the forbidden column breaks independence or anchors the discussion.",
    "A permitted comparison names at most one comparable story and at most one complexity difference; "
    "it never names a point value, a range, an average, elapsed time, effort, or a preferred value.",
]
PHRASING_TRAILER = (
    "Record every SM/EM sizing comment with the pointing record, even when it stays inside the permitted column."
)


def test_phrasing_section_holds_only_the_intro_the_table_and_the_trailer() -> None:
    body = section(RECORD.read_text(), "Permitted and forbidden phrasing")
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    assert lines[:3] == PHRASING_INTRO
    rows = len(phrasing_rows())
    assert lines[3 : 3 + rows + 2] == [line for line in lines[3 : 3 + rows + 2] if line.startswith("|")]
    assert lines[3 + rows + 2 :] == [PHRASING_TRAILER]


def test_phrasing_table_permits_the_three_complexity_comparisons() -> None:
    permitted = [row[0] for row in phrasing_rows()]
    for cell in (
        '"The named story had three interacting constraints; this one has four."',
        '"This story has one more unknown than that one."',
        '"The comparable story had the same interacting constraints."',
    ):
        assert permitted.count(cell) == 1, cell


def test_phrasing_table_ends_with_the_dependency_row_forbidding_a_duration() -> None:
    row = ('"The named story had one fewer external dependency."', '"This would take a week."')
    rows = phrasing_rows()
    assert rows[-1] == row
    assert rows.count(row) == 1


def test_phrasing_table_drops_the_time_and_range_comparisons() -> None:
    text = RECORD.read_text()
    for phrase in (
        "A similar change took two cycles.",
        "The historical range for this area is 3 to 8.",
        "The comparable work included tests and docs.",
    ):
        assert phrase not in text, phrase


def test_phrasing_intro_is_unchanged_and_adds_the_comparison_principle() -> None:
    body = section(RECORD.read_text(), "Permitted and forbidden phrasing")
    intro = [line for line in body.splitlines() if line.strip()][:3]
    assert intro == [
        "The SM/EM may give factual, reference-only sizing context after all three values are recorded.",
        "Everything in the forbidden column breaks independence or anchors the discussion.",
        "A permitted comparison names at most one comparable story and at most one complexity difference; "
        "it never names a point value, a range, an average, elapsed time, effort, or a preferred value.",
    ]
    assert RECORD.read_text().count(intro[2]) == 1


NUMBER_WORDS = "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|dozen|thirty|fifty|hundred"
# A permitted cell never names, bounds or implies a point value: no digit-valued statement, no point
# or size unit, no scale position, no split status, and no value stated in value position ("was five").
POINT_VALUE_IN_PERMITTED = re.compile(
    r"\d"
    r"|\bpoints?\b|\bpts?\b"
    r"|\bscale\b|\bsplit\b"
    r"|\b(?:xxs|xs|s|m|l|xl|xxl|xxxl|small|medium|large|extra\s+large)\b"
    r"|\b(?:cap|maximum)\b"
    r"|\b(?:sizes?|sized|sizing|scores?|scored|rated|rating|estimates?)\b"
    rf"|\b(?:was|is|were|are|be|at)\s+(?:a|an|the)?\s*(?:{NUMBER_WORDS})\b",
    re.IGNORECASE,
)
NUMBER_WORD = re.compile(rf"\b(?:{NUMBER_WORDS})\b", re.IGNORECASE)
COMPLEXITY_FEATURE = re.compile(
    r"\b(?:constraints?|unknowns?|integrations?|dependenc(?:y|ies)|risks?|schema|migration|breaking|scope|deploy leg)\b",
    re.IGNORECASE,
)


def test_phrasing_table_permitted_cells_never_name_a_point_value() -> None:
    permitted = [row[0] for row in phrasing_rows()]
    assert len(permitted) == 11, "the permitted column keeps its eleven rows"
    for cell in (
        '"The comparable story had one fewer unknown to resolve."',
        '"The earlier story carried more breaking-behaviour risk."',
    ):
        assert permitted.count(cell) == 1, cell
    assert '"The comparable story was 5 points."' not in permitted
    assert '"The earlier story was split once."' not in permitted
    for cell in permitted:
        assert not POINT_VALUE_IN_PERMITTED.search(cell), cell
        if NUMBER_WORD.search(cell):
            assert COMPLEXITY_FEATURE.search(cell), f"a number without a complexity feature implies a value: {cell}"


def test_pointing_template_records_each_challenge_and_outcome() -> None:
    assert (
        "- Challenges: <each ground challenged, its author (a voter, or the SM/EM for a sizing comment), and the "
        "restatement, withdrawal or retraction, or the void>" in pointing_template()
    )
    body = spaced(section(RECORD.read_text(), "Pointing record"))
    assert (
        "A challenged ground is recorded with its author (a voter, or the SM/EM for a sizing comment) and either "
        "the restatement, the withdrawal or the retraction; a sizing comment that names, bounds or implies a point "
        "value voids the round as soon as the facilitator sees it, as does any ground that is neither restated "
        "nor retracted, and the void leaves the consensus field empty and is recorded under Anchoring events."
    ) in body


def test_pointing_template_places_challenges_before_anchoring_events() -> None:
    lines = pointing_template()
    assert lines.index("- Challenges: <each ground challenged, its author (a voter, or the SM/EM for a sizing comment), and the restatement, withdrawal or retraction, or the void>") < lines.index(
        "- Anchoring events: <none, or the verbatim comment and the recovery, including the newly created voter contexts>"
    )


def test_pointing_template_asks_for_complexity_rationales() -> None:
    lines = pointing_template()
    values = lines.index("- Values, recorded before the discussion:")
    assert lines[values + 1 : values + 4] == [
        "  - Product owner: <value> - <short complexity rationale>",
        "  - Engineer one: <value> - <short complexity rationale>",
        "  - Engineer two: <value> - <short complexity rationale>",
    ]
    assert [line for line in lines if line.startswith("- Re-vote:")] == [
        "- Re-vote: <accepted set per voter, with complexity rationale>"
    ]
    assert not any("<short rationale>" in line for line in lines)


# SKL-54: every accept round's result is posted in its own comment; the refinement comment stays immutable.

STEP_TWO = "Step 2: Reconciliation and the accept round"
RESULT_ITEM = "After each accept round, including the Step 4 re-refine accept round,"
SEE_RESULT = "see the Accept round result comment"


def test_step_two_requires_an_accept_round_result_comment() -> None:
    item = process_item(STEP_TWO, RESULT_ITEM)
    assert (
        "After each accept round, including the Step 4 re-refine accept round, the PO authors and posts "
        "a separate Accept round result comment that names the refinement comment id it covers, the round number, "
        "each voter's `ACCEPT` or `OBJECT`, and the outcome: accepted, another round, or unpointed."
    ) in item


def test_step_two_never_edits_the_refinement_comment() -> None:
    item = process_item(STEP_TWO, RESULT_ITEM)
    assert (
        "The refinement comment itself is not edited, so its id keeps identifying one immutable refined version."
    ) in item


def test_step_two_result_comment_applied_verbatim_under_the_fallback() -> None:
    item = process_item(STEP_TWO, RESULT_ITEM)
    assert "Under the denied tracker writes fallback the facilitator applies the PO's comment verbatim." in item


def test_step_two_result_item_follows_the_accept_round_item() -> None:
    items = process_items(STEP_TWO)
    index = [i for i, item in enumerate(items) if item.startswith(RESULT_ITEM)]
    assert len(index) == 1
    assert items[index[0] - 1].startswith("Run the accept round on that exact refinement comment id.")


def test_step_two_outputs_name_one_result_comment_per_round() -> None:
    outputs = bullet(operative_step(STEP_TWO), "Outputs")
    assert "and one accept round result comment per accept round" in outputs


def test_records_points_at_the_accept_round_result_template() -> None:
    body = spaced(section(SKILL.read_text(), "Records"))
    assert (
        "Use [references/refinement-record.md](references/refinement-record.md) for the refinement-comment template, "
        "the Accept round result template, the pointing-record template, and the permitted and forbidden phrasing table."
    ) in body


def test_record_has_the_accept_round_result_template_with_exactly_the_fields() -> None:
    assert template("Accept round result").splitlines() == [
        "## Accept round result",
        "",
        "- Refinement comment covered: <refinement comment id>",
        "- Round: <1, 2, or re-refine>",
        "- Product owner: <ACCEPT or OBJECT>",
        "- Engineer one (<family or model>): <ACCEPT or OBJECT>",
        "- Engineer two (<family or model>): <ACCEPT or OBJECT>",
        "- Outcome: <accepted, another round, or unpointed>",
    ]


def test_record_says_the_result_comment_is_separate_and_posted_after_each_round() -> None:
    body = spaced(section(RECORD.read_text(), "Accept round result"))
    assert (
        "Post this as a separate tracker comment after each accept round, including the Step 4 re-refine accept round, "
        "authored by the product owner and posted by the product owner or, under the denied tracker writes fallback, "
        "by the facilitator verbatim."
    ) in body
    assert "Never edit the refinement comment to add the result; its id keeps identifying one immutable refined version." in body


def test_refinement_template_points_every_accept_round_line_at_the_result_comment() -> None:
    lines = template("Refinement comment").splitlines()
    for line in (
        f"- Accept round 1: {SEE_RESULT}",
        f"- Accept round 2 (only after a blocking amendment): {SEE_RESULT}",
        f"- Result: {SEE_RESULT}",
    ):
        assert line in lines, line
    assert not any("<ACCEPT or OBJECT" in line or "<accepted or unpointed>" in line for line in lines)


def test_records_cite_base_names_and_include_needed_content() -> None:
    body = spaced(section(SKILL.read_text(), "Records"))
    assert (
        "Keep the raw voter files in the session's scratch directory and cite each file by its base name only "
        "(never a directory path) in the record."
    ) in body
    assert "Quote or attach any file content a reader needs in the record." in body


@pytest.mark.parametrize("phrase", ["<scratch path>", "cite their paths"])
def test_skill_records_never_request_local_paths(phrase: str) -> None:
    assert phrase not in SKILL.read_text()


def test_record_intro_excludes_local_paths_and_includes_needed_content() -> None:
    intro = spaced(RECORD.read_text().split("## Refinement comment", 1)[0])
    assert "The record never carries a local path; cite each raw voter file by its base name only." in intro
    assert "Quote or attach any file content a reader needs in the record." in intro


@pytest.mark.parametrize(
    ("heading", "line"),
    [
        ("Refinement comment", "- Product owner: <file base name>"),
        ("Refinement comment", "- Engineer one (<family or model>): <file base name>"),
        ("Refinement comment", "- Engineer two (<family or model>): <file base name>"),
        ("Refinement comment", "- SM/EM contribution (not a vote): <file base name>"),
        ("Pointing record", "- SM/EM sizing context, after all three values: <file base name> or verbatim"),
    ],
)
def test_record_templates_cite_file_base_names(heading: str, line: str) -> None:
    assert line in [item.strip() for item in template(heading).splitlines()]


@pytest.mark.parametrize("phrase", ["<scratch path>", "cite their paths"])
def test_record_templates_never_request_local_paths(phrase: str) -> None:
    assert phrase not in RECORD.read_text()
