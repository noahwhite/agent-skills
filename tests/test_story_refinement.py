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

GENERATED_REFERENCES = ["profile", "runtimes", "linear", "todo-tracking", "engineering-practice", "metrics"]

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
    "exactly three engineer voters",
    "pairwise-distinct family values and pairwise-distinct model ids",
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
        "metrics",
    ]


def test_schema_has_refinement_object() -> None:
    """AC6: exactly three engineer reviewers, each required to carry a non-empty family."""
    refinement = SCHEMA["properties"]["refinement"]
    assert refinement["type"] == "object"
    assert refinement["additionalProperties"] is False
    props = refinement["properties"]
    assert props["facilitator"]["$ref"] == "#/$defs/required_refinement_role"
    assert props["product_owner"]["$ref"] == "#/$defs/required_refinement_role"
    reviewers = props["reviewers"]
    assert reviewers["type"] == "array"
    assert reviewers["minItems"] == 3, "the ceremony seats exactly three engineer voters"
    assert reviewers["maxItems"] == 3, "the ceremony seats exactly three engineer voters"
    items = reviewers["items"]
    assert items["$ref"] == "#/$defs/refinement_role"
    assert {"required": ["family"]} in items["allOf"], "each reviewer item must require family"
    assert SCHEMA["$defs"]["refinement_role"]["properties"]["family"]["minLength"] == 1
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
    assert set(props) == {"name", "runtime", "model", "agent", "command", "family", "enabled"}
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
    assert len(reviewers) == 3
    families = [role.get("family") for role in reviewers]
    models = [role["model"] for role in reviewers]
    assert all(families), "every reviewer must set a non-empty family"
    assert len(set(families)) == 3, "reviewer families must be pairwise distinct"
    assert len(set(models)) == 3, "reviewer models must be pairwise distinct"
    assert refinement["point_cap"] == 5


def test_readme_lists_skill() -> None:
    assert "skills/story-refinement/SKILL.md" in (ROOT / "README.md").read_text()


def test_readme_row_names_the_three_engineer_voters() -> None:
    """AC6: the README row names the three engineer voters, not a product-owner vote."""
    row = next(line for line in (ROOT / "README.md").read_text().splitlines()
               if "skills/story-refinement/SKILL.md" in line)
    lowered = row.lower()
    assert "three engineers voting" in lowered, row
    assert "po plus two engineers voting" not in lowered, row
    assert "product owner authoring every tracker write" in lowered, row


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


def test_step_four_derivation_replaces_the_path_vote() -> None:
    body = flat(section(SKILL.read_text(), STEP_FOUR, level=3))
    assert "each voter's re-vote value is the highest value in its accepted set" in body
    for removed in (
        "split, re-refine, or leave unpointed",
        "the set of paths it accepts",
        "the chosen path is in the intersection of the three accepted path sets",
        "the po chooses among them and records why",
        "the po decides",
        "the facilitator records the decision; it does not choose it",
        "paths it will accept",
        "paths it accepts",
    ):
        assert removed not in body, f"the removed path vote survived: {removed}"
    assert "accepted path" not in body, "no accepted-path set survives in Step 4"


def test_step_four_empty_path_intersection_leaves_the_story_unpointed() -> None:
    body = flat(section(SKILL.read_text(), STEP_FOUR, level=3))
    assert (
        "when the highest and the lowest derived values are more than one step apart (1 and 5, for example), "
        "the ceremony records the result as unpointed and stops" in body
    )


def test_step_four_outputs_and_stop_name_the_variance_outcome() -> None:
    body = section(SKILL.read_text(), STEP_FOUR, level=3)
    outputs = bullet(body, "Outputs")
    stop = bullet(body, "Stop")
    assert "the unpointed variance stop with the three values" in outputs
    assert "the `consensus check:` outcome in the pointing record" in outputs
    assert "the derived values are more than one step apart" in stop
    assert "reports `needs input` to the owner naming the story and the derived values" in stop
    for stale in ("no-consensus decision", "leave unpointed is the default", "re-refine"):
        assert stale not in outputs and stale not in stop, stale


def test_step_four_residual_variance_derives_one_value_per_voter() -> None:
    item = process_items(STEP_FOUR)[5]
    assert item.startswith(
        "Residual variance: when the re-vote leaves no value shared by all three accepted sets, each voter's "
        "re-vote value is the highest value in its accepted set."
    )
    assert (
        "A voter that records no consensus in item 4 has no accepted set, so its re-vote value is the value it "
        "recorded in its Step 3 file; after a void that is the value in the re-run's file, never a voided one." in item
    )


def test_step_four_empty_intersection_identical_derived_values_apply_the_tolerance_rule() -> None:
    item = process_items(STEP_FOUR)[5]
    assert (
        "For example, accepted sets `{5}` and `{5}`, with no consensus from the voter whose Step 3 value was "
        "5, derive 5, 5 and 5 from an empty intersection, so the ceremony records 5 as the estimate instead "
        "of stopping unpointed." in item
    )


def test_step_four_residual_variance_one_step_apart_records_the_higher_value() -> None:
    item = process_items(STEP_FOUR)[5]
    assert (
        "Every derived value comes from an accepted set or a Step 3 file, so it is on the sequence and its gap in "
        "scale steps is measurable." in item
    )
    assert (
        "When those derived per-voter values are identical, or the highest and the lowest of them are one step "
        "apart on the sequence in item 1, the same tolerance rule applies to them: the highest derived value "
        "is the estimate" in item
    )
    assert item.count("the highest and the lowest of them are one step apart") == 1, "the one-step branch is named once"
    assert "When those derived per-voter values are identical" in item, "the identical branch is named"


def test_step_four_residual_variance_pick_applies_the_split_rule() -> None:
    item = process_items(STEP_FOUR)[5]
    assert "the highest derived value is the estimate, and the split rule in item 9 still applies to it" in item


def test_step_four_abstention_with_a_wide_step3_value_stops_unpointed() -> None:
    item = process_items(STEP_FOUR)[5]
    assert (
        "A voter that records no consensus in item 4 has no accepted set, so its re-vote value is the value it "
        "recorded in its Step 3 file" in item
    )
    derived = (5, 5, 13)
    match = re.search(r"`fibonacci` ([0-9, ]+?);", process_items(STEP_FOUR)[0])
    assert match, "Step 4 item 1 states the fibonacci sequence"
    stated = match.group(1)
    sequence = [int(value) for value in stated.split(",")]
    gap = sequence.index(max(derived)) - sequence.index(min(derived))
    assert gap > 1, "5 and 13 are more than one step apart on the fibonacci sequence the skill states"
    assert "the highest and the lowest of them are one step apart on the sequence in item 1" in item
    assert (
        "When the highest and the lowest derived values are more than one step apart (1 and 5, for example), the "
        "ceremony records the result as unpointed and stops" in item
    )


def test_step_four_residual_variance_more_than_one_step_apart_stops_unpointed() -> None:
    item = process_items(STEP_FOUR)[5]
    assert (
        "When the highest and the lowest derived values are more than one step apart (1 and 5, for example), the "
        "ceremony records the result as unpointed and stops: it posts the three values, the derived values with "
        "the gap between the highest and the lowest in scale steps, and the three rationales, and reports "
        "`needs input` to the owner naming the story and the derived values." in item
    )
    assert (
        "The owner decides that outcome in a later run, which records it by editing the posted pointing record's "
        "`Owner decision:` line, which the posting run leaves as `pending owner decision in a later run`: a numeric "
        "decision is recorded as the estimate and the split rule applies to it, and a decision to leave the story "
        "unpointed is recorded with the owner's reason and records no estimate." in item
    )
    assert (
        "The product owner does not decide that outcome, and no facilitator and no voter chooses the value or the "
        "path." in item
    )


def test_step_four_names_the_unpointed_variance_stop_apart_from_the_denied_write() -> None:
    item = process_items(STEP_FOUR)[5]
    assert (
        "That unpointed variance stop is a `needs input` state of this skill, distinct from the `needs input` a "
        "denied tracker write produces." in item
    )
    closing = flat(section(SKILL.read_text(), "Closing message"))
    assert "including each `needs input`" in closing
    assert "the denied tracker write of step 1" in closing
    assert "the unpointed variance stop of step 4" in closing


def test_split_rule_takes_the_recorded_estimate() -> None:
    body = flat(section(SKILL.read_text(), "Split rule"))
    assert (
        "a story is split when its recorded estimate is above `profile.refinement.point_cap` or is 8 or more; "
        "the recorded estimate is the consensus, or the value the step 4 consensus check or residual variance "
        "rule records" in body
    )
    assert (
        "the lower trigger applies, and the 8-point rule in [references/linear.md](references/linear.md) is never "
        "relaxed" in body
    )
    assert "if the split trigger is met, split the story" in body
    assert "group-decided" not in body


SIZE_VOCABULARY = re.compile(
    r"tshirt|t[ -]?shirt|x-small|extra[ _]large|x-large|\bXS\b|\bXL\b|\bsize\b", re.IGNORECASE
)


T_SHIRT_VOCABULARY = re.compile(
    r"tshirt|t[ -]?shirt|x-small|extra[ _]large|x-large|\bXS\b|\bXL\b", re.IGNORECASE
)


def story_pointing_surfaces() -> list[Path]:
    """Every file that can state a story-pointing rule, outside the epic sizing home."""
    surfaces = [ROOT / "shared" / name for name in ("linear.md", "metrics.md", "todo-tracking.md")]
    surfaces += [path for path in (ROOT / "shared").glob("*.md")]
    for skill in sorted((ROOT / "skills").iterdir()):
        if not (skill / "SKILL.md").is_file() or skill.name == "linear-epic":
            continue
        surfaces.append(skill / "SKILL.md")
        surfaces += sorted((skill / "references").glob("*.md")) if (skill / "references").is_dir() else []
    return sorted(set(surfaces))


def test_no_story_pointing_surface_names_a_size() -> None:
    offenders = [
        f"{path.relative_to(ROOT)}:{number}: {line.strip()}"
        for path in story_pointing_surfaces()
        for number, line in enumerate(path.read_text().splitlines(), 1)
        if T_SHIRT_VOCABULARY.search(line)
    ]
    assert not offenders, "\n".join(offenders)


def test_the_epic_skill_is_the_one_home_for_t_shirt_sizing() -> None:
    epic = (ROOT / "skills" / "linear-epic" / "SKILL.md").read_text()
    assert "## T-shirt sizing" in epic
    assert "profile.tracker.epic.size_labels" in epic
    schema = SCHEMA["properties"]["tracker"]["properties"]
    assert "size_labels" in schema["epic"]["properties"]
    assert "tshirt" not in schema["estimate_scale"]["enum"]


def test_split_rule_has_no_size_clause() -> None:
    body = section(SKILL.read_text(), "Split rule")
    assert not SIZE_VOCABULARY.search(body), "the split rule reads a numeric estimate only"


def test_shared_linear_rule_has_no_size_clause() -> None:
    lines = (ROOT / "shared" / "linear.md").read_text().splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith("- ⛔ Split a story estimated at 8 points"))
    end = next(index for index in range(start + 1, len(lines)) if lines[index] and not lines[index].startswith(" "))
    bullet = flat(" ".join(lines[start:end]))
    assert bullet.startswith(
        "- ⛔ split a story estimated at 8 points or more at refinement, without asking, and present the slices."
    ), "the 8-point rule starts with one unqualified sentence"
    assert "equivalent" not in bullet, "no scale parenthetical survives"
    assert not SIZE_VOCABULARY.search(bullet), "the split rule names no size"


def test_split_rule_keeps_the_split_mechanics() -> None:
    body = flat(section(SKILL.read_text(), "Split rule"))
    for rule in (
        "the original issue stays the core slice",
        "siblings are created from the `linear-user-story` template",
        "the original issue blocks each sibling",
        "every acceptance criterion is mapped to a slice in the split comment",
    ):
        assert rule in body, rule


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


def test_pointing_template_records_the_consensus_check_outcome() -> None:
    assert "- Consensus check: <identical | one step | more than one step>" in pointing_template()


def test_pointing_template_records_the_residual_variance() -> None:
    lines = pointing_template()
    assert (
        "- Residual variance: <each voter's derived value, the gap between the highest and the lowest in scale "
        "steps, the rule applied and the resulting value, or the unpointed variance stop; n/a only when all three "
        "voters recorded an accepted set and the intersection is not empty, or when the consensus check, or the "
        "re-run of it that supersedes that outcome, recorded the estimate>" in lines
    )
    for removed in ("- No-consensus decision:", "- Paths accepted:", "- Decision rationale:"):
        assert not any(line.startswith(removed) for line in lines), f"removed line survived: {removed}"
    assert not any(line.startswith("- Re-refine") for line in lines), "the re-refine lines are removed"


def test_pointing_template_records_the_recorded_estimate() -> None:
    assert (
        "- Recorded estimate: <the value recorded, or unpointed with the gap between the highest and the lowest in "
        "scale steps when the round stopped there>" in pointing_template()
    )


def test_records_names_the_residual_variance() -> None:
    body = flat(section(SKILL.read_text(), "Records"))
    assert "the `consensus check:` outcome" in body
    assert (
        "the consensus or the residual variance outcome with the derived values, the gap between the highest "
        "and the lowest in scale steps and the rule applied, the recorded estimate or the unpointed variance "
        "stop" in body
    )
    assert "no-consensus decision" not in body


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


def step_one_item_index(prefix: str) -> int:
    """The index of the one Step 1 process item that starts with the given text."""
    items = process_items("Step 1: Independent refinement")
    found = [index for index, item in enumerate(items) if item.startswith(prefix)]
    assert len(found) == 1, f"expected one Step 1 item starting {prefix!r}, found {len(found)}"
    return found[0]


def test_step_one_probe_precedes_voter_launch() -> None:
    probe = step_one_item_index("Run the tracker-write preflight before any voter launches")
    launch = step_one_item_index("Launch the three engineers in separate contexts")
    assert probe < launch, "the probe must precede the voter launch"
    assert "the po, in a separate context, posts one comment" in squash(
        step(SKILL.read_text(), "Step 1: Independent refinement"))


def test_step_one_roster_check_precedes_the_probe_and_every_voter() -> None:
    """AC6: the roster check runs before the tracker-write preflight and before any voter launch."""
    roster = step_one_item_index(
        "Validate the refinement roster before the tracker-write preflight and before any voter launch")
    probe = step_one_item_index("Run the tracker-write preflight before any voter launches")
    launch = step_one_item_index("Launch the three engineers in separate contexts")
    assert roster < probe < launch, "the roster check must precede the probe and every voter launch"
    body = squash(step(SKILL.read_text(), "Step 1: Independent refinement"))
    assert "first-existing-file rule in [references/profile.md](references/profile.md)" in body
    assert "never a repository-only read" in body
    for requirement in (
        "exactly three entries",
        "fewer than three reviewers are enabled",
        "a required role (`facilitator`, `product_owner`, `reviewers`) is unset",
        "a reviewer `family` is missing or empty",
        "two reviewer families are equal",
        "two reviewer model ids are equal",
    ):
        assert requirement in body, requirement


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


def test_skill_states_the_product_owner_is_not_a_voter() -> None:
    """AC6: the roles intro and the Roles bullet both say the product owner does not vote."""
    assert "The product owner authors every tracker write and does not vote." in spaced(SKILL.read_text())
    roles = squash(section(SKILL.read_text(), "Roles"))
    assert "the po is not a voter" in roles


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
    item = process_items(STEP_FOUR)[5]
    assert (
        "The PO authors the unpointed variance record and applies it, or under the denied tracker writes fallback "
        "the facilitator applies the PO-authored record verbatim." in item
    )


# SKL-51: a point measures complexity, never the amount of work or elapsed time.

STEP_THREE = "Step 3: Secret pointing"
POINTING_BASIS = (
    "A point measures complexity - design difficulty, interacting constraints, unknowns, "
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
    assert items[0].startswith("Launch the three engineers again in separate contexts")
    assert items[1] == POINTING_BASIS


def test_step_three_requires_the_basis_in_every_pointing_prompt() -> None:
    assert process_items(STEP_THREE)[2] == (
        "The sentence above is the pointing basis. Every pointing prompt or prompt file carries it verbatim, and "
        "carries the item 4 rationale rule, including each slice estimate under the Split rule."
    )


def test_step_three_rationale_names_complexity_drivers_and_no_duration() -> None:
    body = process_item(STEP_THREE, "Each voter submits one point value")
    assert "plus a short rationale under the pointing basis in item 2." in body
    assert (
        "The rationale names drivers the pointing basis admits and nothing else, so verification strength, "
        "testability, coverage, the shape of the tests, a duration, effort or run-cost measure are out of basis."
    ) in body
    assert (
        "Verification strength is how well a behaviour is checked and the risk of breaking existing behaviour is "
        "what can silently change, so the first is out of basis while the second is a driver the basis admits, "
        "distinct from an interacting constraint the change carries."
    ) in body
    assert (
        "The rationale names no target value for this story, never treats another voter's revealed value as its "
        "answer, and names no point value before the reveal."
    ) in body
    assert "the complexity driver or drivers the voter weighed" not in body
    assert "design difficulty, an interacting constraint, an unknown" not in body


def test_pointing_basis_names_no_size() -> None:
    assert "size" not in POINTING_BASIS.lower(), "a story is given points, never a t-shirt size"
    item = process_items(STEP_THREE)[1]
    assert item == POINTING_BASIS, "the pinned constant is the document's own sentence"
    assert item.startswith("A point measures complexity")
    assert "or size" not in item


def test_step_three_does_not_restate_the_pointing_basis() -> None:
    items = process_items(STEP_THREE)
    assert squash(POINTING_BASIS) in squash(items[1]), "Step 3 item 2 carries the basis and belongs to SKL-60"
    without_basis_item = " ".join(items[:1] + items[2:])
    assert squash(POINTING_BASIS) not in squash(without_basis_item)
    for fragment in (
        "A point measures",
        "measures design difficulty",
        "design difficulty",
        "the amount of work or elapsed time",
        "amount of work",
    ):
        assert fragment not in without_basis_item, fragment


def test_step_four_re_vote_carries_the_basis_by_reference_to_step_three() -> None:
    item = process_items(STEP_FOUR)[3]
    assert item.startswith("Run one re-vote, when the consensus check calls for it.")
    assert "The re-vote prompt carries the pointing basis from Step 3." in item
    assert squash(POINTING_BASIS) not in squash(operative_step(STEP_FOUR))


STEP_THREE_ITEM_PREFIXES = [
    "Launch the three engineers again in separate contexts on the same refined version.",
    "A point measures complexity",
    "The sentence above is the pointing basis.",
    "Each voter submits one point value",
    "No voter sees another voter's point value before its own value is recorded.",
    "The facilitator records all three values before the SM/EM comments on sizing or the discussion opens.",
    "After all three values are recorded, the SM/EM may provide factual, reference-only sizing context:",
]


def test_step_three_has_no_size_cap_step() -> None:
    body = operative_step(STEP_THREE)
    stop = bullet(body, "Stop")
    assert not SIZE_VOCABULARY.search(body), "a t-shirt size is a project and epic label, not a story scale"
    assert not SIZE_VOCABULARY.search(stop)
    assert "cap step" not in body


def test_step_three_process_items_keep_their_count_and_order() -> None:
    items = process_items(STEP_THREE)
    assert len(items) == 7, "the cap item is removed and no size option may be added"
    for index, prefix in enumerate(STEP_THREE_ITEM_PREFIXES):
        assert items[index].startswith(prefix), (index, prefix)


def test_step_three_re_records_an_off_sequence_value_before_the_reveal() -> None:
    item = process_item(STEP_THREE, "Each voter submits one point value")
    assert (
        "and present in the fixed step sequence Step 4 item 1 states for that scale" in item
    )
    assert (
        "A value outside that sequence is re-recorded before the reveal, in a launch that starts a new voter "
        "context, so every value and every accepted set has a step position" in item
    )
    assert (
        "a second off-sequence value from the same voter stops the round with a missing-valid-value stop reason"
        in item
    )
    stop = bullet(operative_step(STEP_THREE), "Stop")
    assert "a voter's second off-sequence value is a missing-valid-value stop" in stop


def test_step_four_re_vote_recovers_an_off_sequence_accepted_value() -> None:
    item = process_items(STEP_FOUR)[3]
    assert (
        "An accepted-set value outside that sequence is re-recorded once under the Step 3 re-record rule, and a "
        "second off-sequence re-vote value from the same voter stops the round like a Step 3 off-sequence stop."
        in item
    )


def test_step_four_records_a_value_outside_the_sequence_as_wider_than_one_step() -> None:
    item = process_items(STEP_FOUR)[0]
    assert (
        "A value outside that sequence for the profile's scale has no step position, so two different values that "
        "involve one are more than one step apart; three identical values are identical, and Step 3 already "
        "re-records an off-sequence value before the reveal." in item
    )
    assert (
        "or they differ and either of them is outside the sequence, the discussion in item 3 and the re-vote in "
        "item 4 run" in item
    )


def test_step_three_defines_the_reveal() -> None:
    items = process_items(STEP_THREE)
    assert (
        "The reveal is the moment the facilitator has recorded all three values, after which the SM/EM may "
        "comment on sizing and the discussion opens."
    ) in items[4]


def test_step_four_re_vote_prompt_carries_the_rationale_rule() -> None:
    item = process_items(STEP_FOUR)[3]
    assert (
        "It also carries the Step 3 item 4 rationale rule and the fixed step sequence from item 1, since an "
        "accepted set is drawn from that sequence." in item
    )


def test_pointing_template_has_no_size_note() -> None:
    lines = pointing_template()
    assert not any(SIZE_VOCABULARY.search(line) for line in lines), "a pointing record never carries a size"
    outcome = next(line for line in (ROOT / "shared" / "metrics.md").read_text().splitlines() if line.startswith("- **Outcome:**"))
    assert not SIZE_VOCABULARY.search(outcome), "the outcome figure names an estimate, never a size"
    assert (
        "- Effective maximum: <profile.refinement.point_cap; the 8-point rule still triggers at 8 or more>"
        in lines
    )


def test_pointing_template_notes_the_private_self_context_rule() -> None:
    assert (
        "- Discussion: <high <value>, low <value>; or none when the discussion ran and recorded nothing; or "
        "skipped, when the consensus check recorded the estimate; the shared content names only the high and the "
        "low, while a voter's own recorded value and rationale are carried privately in that voter's prompt>"
        in pointing_template()
    )


def test_pointing_template_states_the_standing_consensus() -> None:
    assert (
        "- Consensus: <the highest value in the intersection of the vote that stands, or n/a when the consensus check "
        "or the residual variance rule recorded the estimate, or none when the round stopped unpointed>"
        in pointing_template()
    )


def test_step_four_re_vote_requires_a_complexity_rationale() -> None:
    item = process_items(STEP_FOUR)[3]
    assert (
        "Each voter records the set of values it accepts for this story (one or more, each valid for "
        "`profile.tracker.estimate_scale` and present in the item 1 sequence) or records no consensus, with a "
        "short complexity rationale under the Step 3 rationale rule."
    ) in item


SIZING_ITEM = "After all three values are recorded, the SM/EM may provide"


def test_step_three_sizing_context_is_in_complexity_terms() -> None:
    body = process_item(STEP_THREE, SIZING_ITEM)
    assert (
        "the SM/EM may provide factual, reference-only sizing context: comparable stories in complexity terms, "
        "their recorded values, comparable unknowns and constraints, and relevant scope differences."
    ) in body
    assert "historical sizing" not in squash(SKILL.read_text())
    assert "Before the reveal it must not name any point value." in body
    assert (
        "A factual reference is not a prescription: naming an already-estimated item's recorded value, alone or "
        "together with a basis difference, is permitted, and such a reference is information the voters weigh and "
        "never stops the round."
    ) in body
    assert (
        "It must not prescribe this story's value - no value to score, no target, no preferred direction - and "
        "must not reveal or compare individual votes before the discussion."
    ) in body
    assert (
        "A prescription of this story's value, from the SM/EM or from a voter, is an anchoring event under the "
        "Anchoring guardrail."
    ) in body


STEP_FOUR_ITEM_PREFIXES = [
    "Run the consensus check first, on the three values recorded in Step 3.",
    "Review every rationale recorded in Step 3 against the pointing basis,",
    "Hold one discussion round that names only the high and the low, when the consensus check calls for it.",
    "Run one re-vote, when the consensus check calls for it.",
    "When the re-vote ran, consensus is the highest value in the intersection of the three accepted sets.",
    "Residual variance: when the re-vote leaves no value shared by all three accepted sets,",
    "Never average and never take a value silently, except the tolerance value the consensus check or the residual variance rule records.",
    "The facilitator records the estimate or the consensus; it does not declare it.",
    "Apply the split rule when the split trigger it defines is met by the recorded estimate.",
]


CONSENSUS_CHECK = "Run the consensus check first, on the three values recorded in Step 3."
ESTIMATE_SEQUENCES = (
    "The ordered step sequence is fixed here for each `profile.tracker.estimate_scale` value, in the order given: "
    "`fibonacci` 1, 2, 3, 5, 8, 13; `linear` the ordinal list 1, 2, 3, 5, 8, 13; "
    "`exponential` 1, 2, 4, 8, 16."
)
CONSENSUS_CHECK_BRANCHES = (
    "When the three values are identical, or the highest and the lowest are one step apart (5 and 8 on "
    "`fibonacci`, for example), the highest of the three values is the estimate, the discussion in item 3 and "
    "the re-vote in item 4 are skipped, and the split rule in item 9 still applies to it. "
    "The basis review in item 2 still runs on this branch, and nothing is written to the tracker and no "
    "pointing record is posted until it has run. "
    "When the highest and the lowest are more than one step apart (1 and 5, for example), or they differ and "
    "either of them is outside the sequence, the discussion in item 3 and the re-vote in item 4 run, naming the "
    "high and the low."
)


def test_step_four_identical_values_record_the_higher_value_and_skip() -> None:
    item = process_items(STEP_FOUR)[0]
    assert item.startswith(CONSENSUS_CHECK)
    assert ESTIMATE_SEQUENCES in item
    assert (
        "The tolerance is one step, and it is fixed in this skill: no profile key and no skill argument sets it."
    ) in item
    assert CONSENSUS_CHECK_BRANCHES in item
    assert (
        "the record's values block keeps the values recorded before the discussion, and a replacement value "
        "appears on its Challenges line and in the voter's file" in item
    )
    assert (
        "Record the outcome in the pointing record as `Consensus check: <identical | one step | more than one "
        "step>`, so a skipped discussion and re-vote read as skipped and never as not run; the record's values "
        "block keeps the values recorded before the discussion, and a replacement value appears on its Challenges "
        "line and in the voter's file."
    ) in item
    assert process_items(STEP_FOUR)[2].startswith(
        "Hold one discussion round that names only the high and the low, when the consensus check calls for it."
    ), "an unconditional discussion would make an identical round run one"


def test_schema_estimate_scale_is_numeric_only() -> None:
    scales = SCHEMA["properties"]["tracker"]["properties"]["estimate_scale"]["enum"]
    assert scales == ["fibonacci", "linear", "exponential"], "story pointing runs on numeric scales only"


def test_epic_size_labels_are_untouched_and_carry_t_shirt_sizing() -> None:
    labels = SCHEMA["properties"]["tracker"]["properties"]["epic"]["properties"]["size_labels"]
    assert labels["type"] == "object"
    assert labels["additionalProperties"] is False
    assert set(labels["properties"]) == {"small", "medium", "large", "extra_large"}


def test_step_four_fixes_a_sequence_for_every_estimate_scale() -> None:
    item = process_items(STEP_FOUR)[0]
    scales = SCHEMA["properties"]["tracker"]["properties"]["estimate_scale"]["enum"]
    for scale in scales:
        assert f"`{scale}`" in item, f"no fixed step sequence for the {scale} scale"
    assert ESTIMATE_SEQUENCES in item, "the three numeric sequences are pinned verbatim"
    assert not SIZE_VOCABULARY.search(item), "a story is given points, never a t-shirt size"


def test_step_four_one_step_apart_records_the_higher_value_and_skips() -> None:
    item = process_items(STEP_FOUR)[0]
    assert "`fibonacci` 1, 2, 3, 5, 8, 13" in item
    assert (
        "the highest and the lowest are one step apart (5 and 8 on `fibonacci`, for example), the highest of "
        "the three values is the estimate, the discussion in item 3 and the re-vote in item 4 are skipped" in item
    )
    assert not SIZE_VOCABULARY.search(item), "a size has no step position on a numeric scale"


def test_step_four_more_than_one_step_apart_runs_the_discussion() -> None:
    item = process_items(STEP_FOUR)[0]
    run_clause = "the discussion in item 3 and the re-vote in item 4 run, naming the high and the low."
    assert "(1 and 5, for example), or they differ and either of them is outside the sequence, " + run_clause in item
    assert item.count(run_clause) == 1, "the discussion must run on the wide branch only"
    assert "is the estimate" in item


SKL13_VALUES = (8, 8, 8)
SKL13_OFF_BASIS = "the tests took two days to write, so this is a 13"
SPLIT_TRIGGER = 8
SKIP_BRANCH_REVIEW = (
    "Review every rationale recorded in Step 3 against the pointing basis, after the consensus check and before "
    "the estimate is written to the tracker and before the pointing record is posted, so a void never leaves a "
    "written estimate to unwind. This review is not the discussion: it runs on both branches, and the discussion "
    "in item 3 only carries the challenges it raises."
)
SKIP_BRANCH_CHALLENGE = (
    "When the consensus check skips the discussion and the re-vote, this review runs as a basis-challenge round "
    "of its own: the facilitator launches each challenged voter once per round in a newly created voter context "
    "whose prompt lists every ground challenged for that voter and carries the story, the refinement comment id, "
    "that voter's own recorded value and rationale, the Step 3 pointing basis and the Step 3 item 4 rationale "
    "rule; an off-sequence replacement value is re-recorded in a second launch of that voter. That launch records "
    "a replacement value for that voter only when the voter's basis does not support its recorded value, and "
    "otherwise the value that stands holds. An unresolved ground voids the round under the Anchoring guardrail, "
    "so no estimate and no split action survives an unresolved challenge."
)


def test_step_four_identical_values_skip_still_challenges_every_off_basis_ground() -> None:
    review = process_items(STEP_FOUR)[1]
    check = process_items(STEP_FOUR)[0]
    assert "When the three values are identical, or the highest and the lowest are one step apart" in check
    assert "the discussion in item 3 and the re-vote in item 4 are skipped" in check
    assert "skip the basis review" not in check, "the skip branch must keep the basis review"
    assert SKIP_BRANCH_REVIEW in review
    assert SKIP_BRANCH_CHALLENGE in review
    assert "A challenged ground must be restated as a basis driver or retracted" in review
    assert (
        "The basis-challenge round applies this same review to every rationale its launches record: an off-basis "
        "replacement rationale is restated or retracted, and an unresolved one voids the round." in review
    )
    assert "no estimate and no split action survives an unresolved challenge" in review
    # The fixture: three identical 8s (SKL-13) with one off-basis rationale.
    assert len(set(SKL13_VALUES)) == 1, "the fixture is three identical values"
    recorded = max(SKL13_VALUES)
    assert recorded >= SPLIT_TRIGGER, "SKL-13's recorded 8 reaches the eight-point split trigger"
    # The fixture rationale is off-basis on the skill's own trigger list (a duration).
    assert "two days" in SKL13_OFF_BASIS
    guardrail = flat(section(SKILL.read_text(), GUARDRAIL))
    assert "a duration, effort or run cost" in guardrail, "the guardrail names a duration as off basis"
    # The challenge fires on that rationale, and the round cannot end on it.
    assert "outside the pointing basis" in review
    assert "recorded rationale" in review
    assert "retracts an unsupported ground and records a replacement value" in review
    assert "An unresolved ground voids the round under the Anchoring guardrail" in review
    assert "no estimate and no split action survives an unresolved challenge" in review
    assert "before the estimate is written to the tracker" in review
    # And the recorded value still meets the skill's own split trigger.
    split_rule = flat(section(SKILL.read_text(), "Split rule"))
    matches = re.findall(r"or is (\d+) or more", split_rule)
    assert len(matches) == 1, f"exactly one numeric split trigger, found {matches}"
    assert recorded >= int(matches[0]), "the skill's split trigger catches SKL-13's 8"


def test_step_four_one_step_skip_still_challenges_every_off_basis_ground() -> None:
    review = process_items(STEP_FOUR)[1]
    check = process_items(STEP_FOUR)[0]
    assert "the highest and the lowest are one step apart (5 and 8 on `fibonacci`, for example), the highest of the three values is the estimate, the discussion in item 3 and the re-vote in item 4 are skipped" in check
    assert SKIP_BRANCH_REVIEW in review
    assert SKIP_BRANCH_CHALLENGE in review
    assert "no estimate and no split action survives an unresolved challenge" in review


def test_step_four_ordering_puts_the_basis_review_before_any_write() -> None:
    review = process_items(STEP_FOUR)[1]
    assert review.index("before the estimate is written to the tracker") < review.index(
        "before the pointing record is posted"
    )
    check = process_items(STEP_FOUR)[0]
    assert "nothing is written to the tracker and no pointing record is posted until it has run" in check


def test_step_four_owner_never_chooses_the_derived_value() -> None:
    item = process_items(STEP_FOUR)[5]
    assert "The product owner does not decide that outcome" in item
    assert "no facilitator and no voter chooses the value or the path" in item


def test_step_four_abstention_stop_reports_needs_input() -> None:
    item = process_items(STEP_FOUR)[5]
    assert (
        "and reports `needs input` to the owner naming the story and the derived values" in item
    )


def test_step_four_process_items_keep_their_count_and_order() -> None:
    items = process_items(STEP_FOUR)
    assert len(items) == 9, "Step 4 has nine items: the check, the review, the discussion, the re-vote, the consensus, the residual variance, no averaging, the record, the split"
    assert len(items) == len(STEP_FOUR_ITEM_PREFIXES)
    for index, prefix in enumerate(STEP_FOUR_ITEM_PREFIXES):
        assert items[index].startswith(prefix), (index, prefix)


STEP_FOUR_CROSS_REFERENCES = {
    1: "Run the consensus check first",
    2: "Review every rationale recorded in Step 3",
    3: "Hold one discussion round",
    4: "Run one re-vote",
    6: "Residual variance:",
    5: "When the re-vote ran, consensus is the highest value in the intersection",
    9: "Apply the split rule when the split trigger it defines is met",
}


def test_step_four_item_cross_references_resolve() -> None:
    items = process_items(STEP_FOUR)
    body = flat(section(SKILL.read_text(), STEP_FOUR, level=3))
    referenced = {int(number) for number in re.findall(r"item (\d+)", body)}
    assert referenced, "Step 4 refers to its own items"
    assert referenced <= set(range(1, len(items) + 1)), f"dangling item reference: {sorted(referenced)}"
    assert {1, 2, 3, 4, 6, 9} <= referenced, f"a numbered step stopped being referenced: {sorted(referenced)}"
    for number, prefix in STEP_FOUR_CROSS_REFERENCES.items():
        assert items[number - 1].startswith(prefix), (number, prefix)


def test_step_four_facilitator_challenges_every_off_basis_ground() -> None:
    item = process_items(STEP_FOUR)[1]
    assert (
        "The review challenges every ground outside the pointing basis that a recorded rationale carries; a "
        "ground first heard in the discussion of item 3 is challenged there, under item 3, "
        "except a prescription of this story's value and, from the SM/EM, a statement of elapsed time, effort or "
        "run cost, which are anchoring events the moment they are seen."
    ) in item
    assert (
        "That rule governs the shared discussion content and other voters' values; a voter's own recorded value "
        "and rationale may be carried privately in that voter's own prompt, so it can speak to its own ground."
    ) in item
    assert (
        "Challenging a ground is not comparing values or singling out a voter: the facilitator names the ground's "
        "kind, never its verbatim text; the facilitator never names another voter's value in the shared "
        "discussion, nor a voter's value to other voters, and the pointing record carries the author; a ground "
        "that embeds a point value is named by its kind alone."
    ) in item
    assert (
        "A challenged ground must be restated as a basis driver or retracted, except a prescription of this "
        "story's value, which is an anchoring event as soon as it is seen."
    ) in item
    assert (
        "The SM/EM withdraws or restates its own sizing comment on the same terms, except a point value named "
        "before the reveal, a prescription of this story's value, treating another voter's revealed value as the "
        "answer, or a statement of elapsed time, effort or run cost, each of which is an anchoring event as soon "
        "as the facilitator sees it."
    ) in item
    assert "A ground that is neither restated as a basis driver nor retracted is an anchoring event under the Anchoring guardrail." in item
    assert (
        "A voter whose basis does not support its recorded value retracts an unsupported ground and records a "
        "replacement value with a basis-driver rationale under the Step 3 item 4 rationale rule, in the re-vote or, "
        "when the consensus check skips the re-vote, in the basis-challenge round of this item, and the facilitator "
        "records it in that voter's Step 3 file on either path; one basis-challenge "
        "round runs per voter per ceremony, so a replacement whose rationale is again off basis leaves the ground "
        "unresolved and voids the round rather than starting another; a replacement value is valid for "
        "`profile.tracker.estimate_scale` and present in the item 1 sequence, re-recorded otherwise." in item
    )
    assert (
        "The facilitator records a replacement value in that voter's Step 3 file, so the value recorded there is "
        "the value that stands, and, when the consensus check skipped the re-vote, it then re-runs on the three "
        "standing values" in item
    )
    assert (
        "The re-run's outcome supersedes the `Consensus check:` outcome in the pointing record, and when it is "
        "more than one step apart the discussion in item 3 and the re-vote in item 4 run before any estimate is "
        "written or posted." in item
    )


def test_step_four_re_vote_challenges_an_off_basis_rationale() -> None:
    item = process_items(STEP_FOUR)[3]
    assert (
        "Recording an accepted set is not treating another voter's revealed value as the answer: the rationale "
        "for the set is about the basis, never about which value another voter recorded."
    ) in item
    assert (
        "A re-vote rationale outside the pointing basis is challenged before the consensus is recorded, under "
        "the same restate-or-retract rule as item 2, and a voter that retracts its re-vote rationale records a "
        "replacement accepted set within that same re-vote, with a basis-driver rationale, or records no "
        "consensus."
    ) in item


def test_anchoring_guardrail_makes_a_point_value_sizing_note_an_event_on_challenge() -> None:
    body = flat(section(SKILL.read_text(), GUARDRAIL))
    assert (
        "an anchoring trigger is an off-basis ground step 4 challenges, so it becomes an anchoring event only "
        "when it is neither restated as a basis driver nor retracted" in body
    )
    assert (
        "every prohibited behaviour above, a prescription of this story's value by any participant, and an sm/em "
        "sizing comment that names a point value before the reveal or states elapsed time, effort or run cost, are "
        "anchoring events as soon as they are seen, with no challenge, restatement or retraction path" in body
    )
    assert (
        "a factual reference is never such an event: naming an already-estimated item's recorded value, alone or "
        "together with a basis difference, is information the voters weigh, and the round continues." in body
    )
    assert (
        "any other challenged ground that is neither restated as a basis driver nor retracted, or a sizing comment "
        "the sm/em neither withdraws nor restates, is an anchoring event, and the recovery below is the "
        "single void rule: it voids the recorded estimate, the `consensus check:` outcome, the consensus, the "
        "residual variance derived values and their outcome, and every vote recorded after the anchor, and for a "
        "ground read "
        "in a recorded rationale the anchor precedes that rationale, so the vote it grounds and every later vote "
        "are void, and the independent vote from step 3 is re-run in newly created voter contexts that exclude "
        "the tainted discussion and sizing comment" in body
    )


GUARDRAIL = "Anchoring guardrail"


def test_anchoring_guardrail_bans_the_sm_em_value_behaviours() -> None:
    body = flat(section(SKILL.read_text(), GUARDRAIL))
    assert (
        "for the sm/em, naming a point value before the reveal, prescribing a value for this story - a value to "
        "score, a target, a preferred direction, or a claim that one vote is the realistic one - or treating "
        "another voter's revealed value as the answer" in body
    )
    assert "naming a target number" not in body


def test_anchoring_guardrail_names_off_basis_grounds_as_a_trigger() -> None:
    body = flat(section(SKILL.read_text(), GUARDRAIL))
    assert (
        "an anchoring trigger is an off-basis ground step 4 challenges, so it becomes an anchoring event only "
        "when it is neither restated as a basis driver nor retracted" in body
    )
    assert (
        "a ground that weighs verification strength, testability, coverage, the shape of the tests, or a "
        "duration, effort or run cost is such a trigger when a voter weighs it in a rationale or raises it in "
        "the discussion" in body
    )
    assert "verification strength, testability, coverage, the shape of the tests" in body


def test_anchoring_guardrail_explains_why_context_cannot_exclude_a_recorded_value() -> None:
    body = flat(section(SKILL.read_text(), GUARDRAIL))
    assert (
        "fresh voter contexts exclude the tainted discussion and the sizing comment, but they cannot exclude a "
        "value recorded on the story surface that step 1 hands every voter with the story, so the step 3 "
        "rationale rule is what keeps such a value from becoming the rationale's answer" in body
    )


def test_anchoring_guardrail_places_the_anchor_and_the_single_void_rule() -> None:
    body = flat(section(SKILL.read_text(), GUARDRAIL))
    assert (
        "and the recovery below is the single void rule: it voids the recorded estimate, the `consensus "
        "check:` outcome, the consensus, the residual variance derived values and their outcome, and every "
        "vote recorded after the anchor, and for a ground read in a recorded rationale the anchor precedes "
        "that rationale, so the "
        "vote it grounds and every later vote are void, and the independent vote from step 3 is re-run in newly "
        "created voter contexts that exclude the tainted discussion and sizing comment" in body
    )


def test_anchoring_guardrail_recovery_mechanics_are_unchanged() -> None:
    body = spaced(section(SKILL.read_text(), GUARDRAIL))
    assert (
        "On anchoring: stop the round, record the comment verbatim, void the recorded estimate, the `Consensus "
        "check:` outcome, the consensus, the residual variance derived values and their outcome, and any vote "
        "recorded after the anchor, and re-run the independent vote with newly created voter contexts that exclude "
        "the tainted discussion and sizing comment. Never reuse the sessions that saw the anchor. Record the "
        "recovery."
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
    "A factual reference is permitted and a prescription is not: naming an already-estimated item's recorded "
    "value, alone or together with a basis difference, is a reference the voters weigh, while a value to score, "
    "a target or a preferred direction for the story under estimate is a prescription that anchors the round.",
    "A permitted comparison names at most one comparable story and at most one basis difference; "
    "it never prescribes a value for the story under estimate, names a range, an average, elapsed time or "
    "effort, and it names another story's point value only after all three values are recorded.",
]
PHRASING_TRAILER = (
    "Record every SM/EM sizing comment with the pointing record, even when it stays inside the permitted column."
)


def test_phrasing_section_holds_only_the_intro_the_table_and_the_trailer() -> None:
    body = section(RECORD.read_text(), "Permitted and forbidden phrasing")
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    assert lines[: len(PHRASING_INTRO)] == PHRASING_INTRO
    rows = len(phrasing_rows())
    start = len(PHRASING_INTRO)
    assert lines[start : start + rows + 2] == [line for line in lines[start : start + rows + 2] if line.startswith("|")]
    assert lines[start + rows + 2 :] == [PHRASING_TRAILER]


def test_phrasing_table_header_names_both_columns() -> None:
    body = section(RECORD.read_text(), "Permitted and forbidden phrasing")
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    header = next(line for line in lines if line.startswith("|"))
    assert header == "| Permitted (factual, reference-only) | Forbidden (leading or anchoring) |"


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
    intro = [line for line in body.splitlines() if line.strip()][: len(PHRASING_INTRO)]
    assert intro == PHRASING_INTRO
    assert RECORD.read_text().count(intro[3]) == 1


PERMITTED_CELLS = [
    '"The comparable story was 5 points."',
    '"The named story had three interacting constraints; this one has four."',
    '"This story has one more integration than that one."',
    '"The prior story also changed the schema."',
    '"That story carried no migration."',
    '"The scope differs in the deploy leg."',
    '"This story has one more unknown than that one."',
    '"The comparable story had the same interacting constraints."',
    '"The earlier story was split once."',
    '"No comparable story exists."',
    '"The named story had one fewer external dependency."',
]


def test_phrasing_table_permitted_column_is_the_exact_curated_list() -> None:
    assert [row[0] for row in phrasing_rows()] == PERMITTED_CELLS


TARGET_VALUE_IN_PERMITTED = re.compile(
    r"\bthis (?:story|one) (?:is|was|scores?|scored|sits?|lands?|should be)\b"
    r"|\btarget\b|\bwe should\b|\bgo higher\b|\bgo lower\b"
    r"|\bmatch\b|\bsame as\b|\btreat(?:ed|s)? the same\b|\bpoint it at\b",
    re.IGNORECASE,
)


def test_phrasing_table_permitted_cells_state_no_target_value() -> None:
    permitted = [row[0] for row in phrasing_rows()]
    for cell in permitted:
        assert not TARGET_VALUE_IN_PERMITTED.search(cell), cell


def test_pointing_template_records_each_challenge_and_outcome() -> None:
    assert (
        "- Challenges: <none, or each ground challenged by kind, its author (a voter, or the SM/EM for a sizing "
        "comment), the restatement, withdrawal or retraction, and any replacement value it produced, or the void; "
        "elide a pre-reveal value or a "
        "prescription>" in pointing_template()
    )
    assert (
        "- Anchoring events: <none, or the comment and the recovery, including the newly created voter contexts, "
        "with the verbatim comment in the raw session record and its base name cited here>" in pointing_template()
    )
    assert (
        "- Superseded values after a void: <none, or the voided values, the voided estimate, the voided "
        "`Consensus check:` outcome, the voided consensus, the voided derived values and their outcome, and the "
        "blind vote that replaced them>"
        in pointing_template()
    )
    body = spaced(section(RECORD.read_text(), "Pointing record"))
    assert (
        "Outside the recorded numeric values and the superseded-values line, no line of the posted record carries "
        "a point value named before the reveal or a prescription of this story's value: the Challenges and Anchoring events "
        "lines record a ground by its kind, its author (a voter, or "
        "the SM/EM for a sizing comment) and its outcome or recovery, and every field that could quote a "
        "participant elides those two classes permanently, because the posted record stays on the story surface "
        "that later voters read; the verbatim quote lives in the session's raw record, cited by its base name."
    ) in body
    assert (
        "A sizing comment that names a point value before the reveal, prescribes this story's value, or states "
        "elapsed time, effort or run cost voids the round under the Anchoring guardrail recovery "
        "as soon as the facilitator sees it, as does any ground that is neither restated nor retracted, and the "
        "void records the voided consensus under Superseded values after a void, so the Consensus field carries "
        "the vote that stands, or n/a when the consensus check or the residual variance rule recorded the "
        "estimate."
    ) in body


def test_pointing_template_places_challenges_before_anchoring_events() -> None:
    lines = pointing_template()
    challenges = [index for index, line in enumerate(lines) if line.startswith("- Challenges:")]
    anchoring = [index for index, line in enumerate(lines) if line.startswith("- Anchoring events:")]
    assert len(challenges) == 1 and len(anchoring) == 1
    assert challenges[0] < anchoring[0]


def test_pointing_template_asks_for_complexity_rationales() -> None:
    lines = pointing_template()
    values = next(index for index, line in enumerate(lines) if line.startswith("- Values, recorded before the discussion:"))
    assert lines[values + 1 : values + 4] == [
        "  - Engineer one: <value, or not recorded> - <short complexity rationale, or none when the value is not recorded>",
        "  - Engineer two: <value, or not recorded> - <short complexity rationale, or none when the value is not recorded>",
        "  - Engineer three: <value, or not recorded> - <short complexity rationale, or none when the value is not recorded>",
    ]
    assert lines[values + 4].startswith("- Consensus check:"), (
        "the value block holds exactly the three engineer voters")
    assert not any(line.strip().startswith("- Product owner:") for line in lines), (
        "the product owner is not a pointing voter")
    assert [line for line in lines if line.startswith("- Re-vote:")] == [
        "- Re-vote: <accepted set per voter, with complexity rationale; or no consensus, with its complexity "
        "rationale, for a voter that records none; or none when it ran and recorded nothing; or skipped, when the "
        "consensus check recorded the estimate>"
    ]
    assert not any("<short rationale>" in line for line in lines)


# SKL-54: every accept round's result is posted in its own comment; the refinement comment stays immutable.

STEP_TWO = "Step 2: Reconciliation and the accept round"
RESULT_ITEM = "After each accept round,"
SEE_RESULT = "see the Accept round result comment"


def test_step_two_requires_an_accept_round_result_comment() -> None:
    item = process_item(STEP_TWO, RESULT_ITEM)
    assert (
        "After each accept round, the PO authors and posts "
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
        "- Round: <1 or 2>",
        "- Engineer one (<family or model>): <ACCEPT or OBJECT>",
        "- Engineer two (<family or model>): <ACCEPT or OBJECT>",
        "- Engineer three (<family or model>): <ACCEPT or OBJECT>",
        "- Outcome: <accepted, another round, or unpointed>",
    ]


def test_record_says_the_result_comment_is_separate_and_posted_after_each_round() -> None:
    body = spaced(section(RECORD.read_text(), "Accept round result"))
    assert (
        "Post this as a separate tracker comment after each accept round, "
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
    assert not any(line.startswith("- Re-refine") for line in lines), "the re-refine accept round is removed"


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
        ("Refinement comment", "- Engineer one (<family or model>): <file base name>"),
        ("Refinement comment", "- Engineer two (<family or model>): <file base name>"),
        ("Refinement comment", "- Engineer three (<family or model>): <file base name>"),
        ("Refinement comment", "- SM/EM contribution (not a vote): <file base name>"),
        ("Pointing record", "- SM/EM sizing context, after all three values: <file base name> or verbatim, eliding a pre-reveal value or a prescription, or none"),
    ],
)
def test_record_templates_cite_file_base_names(heading: str, line: str) -> None:
    assert line in [item.strip() for item in template(heading).splitlines()]


@pytest.mark.parametrize("phrase", ["<scratch path>", "cite their paths"])
def test_record_templates_never_request_local_paths(phrase: str) -> None:
    assert phrase not in RECORD.read_text()


def test_refinement_template_voter_inputs_are_only_the_three_engineers() -> None:
    """AC6: the refinement comment's voter-input block is exactly the three engineer voters."""
    lines = template("Refinement comment").splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith("- Voter inputs,"))
    assert lines[start + 1 : start + 4] == [
        "  - Engineer one (<family or model>): <file base name>",
        "  - Engineer two (<family or model>): <file base name>",
        "  - Engineer three (<family or model>): <file base name>",
    ]
    assert lines[start + 4].startswith("- SM/EM contribution (not a vote):"), (
        "the voter-input block holds exactly the three engineer voters")
    assert not any(line.strip().startswith("- Product owner:") for line in lines), (
        "the product owner is not a voter")


# --- SKL-47: the metrics switch, the closing message, and the run summary --------------------------

ARGUMENTS = "Arguments"
CLOSING = "Closing message"
METRICS = "Metrics"


def skill_section(heading: str) -> str:
    return spaced(section(SKILL.read_text(), heading))


@pytest.mark.parametrize(
    "sentence",
    [
        "`STORY_ID` is required: any Linear issue key (for example `ABC-123`).",
        "Its team prefix is the team for every read and write this skill performs on or for that issue, "
        "and it need not equal `profile.tracker.team_key`.",
        "Any backlog or epic search this skill performs runs in the team of `STORY_ID`.",
        "If none was given, ask the owner for one before doing anything else; never guess an issue key.",
        "`metrics` is optional, given as `metrics=on` or `metrics=off` or in plain words, and defaults to `off`.",
        "`with metrics` and `metrics on` mean on; `without metrics` and `metrics off` mean off.",
        "Any other phrasing about metrics is asked about, never guessed.",
        "Resolve both arguments, asking about any ambiguity, before the todo list is created.",
        "Write the resolved value as one line `metrics: on` or `metrics: off` at the top of the todo list and in the closing message.",
        "When `metrics` resolves on, the facilitator's next action, before the todo list, is to take a UTC timestamp with a command and record it as `invocation_start` in the metrics file.",
    ],
)
def test_arguments_section_defines_the_story_identifier_and_the_metrics_switch(sentence: str) -> None:
    assert sentence in skill_section(ARGUMENTS)


# --- SKL-204: the team comes from the invoked issue key, not the profile --------------------------

OLD_TEAM_PARENTHETICAL = "with the team key `profile.tracker.team_key`"
INVOCATION_KEY_TEAM = (
    "Its team prefix is the team for every read and write this skill performs on or for that issue, "
    "and it need not equal `profile.tracker.team_key`."
)
STORY_ID_SENTENCES = {
    "story-refinement": "`STORY_ID` is required: any Linear issue key (for example `ABC-123`).",
    "story-to-done": "`STORY_ID` is required: any Linear issue key (for example `ABC-123`).",
    "persona-staff-engineer": "This skill takes one argument, `STORY_ID`: any Linear issue key (for example `ABC-123`).",
    "persona-staff-devops": "This skill takes one argument, `STORY_ID`: any Linear issue key (for example `ABC-123`).",
}
DIFFERING_TEAM_CITE = (
    "under the differing-team rule in Team resolution in [references/linear.md](references/linear.md)"
)


@pytest.mark.parametrize("name", sorted(STORY_ID_SENTENCES))
def test_story_id_team_is_the_invoked_key_prefix(name: str) -> None:
    text = spaced((ROOT / "skills" / name / "SKILL.md").read_text())
    assert OLD_TEAM_PARENTHETICAL not in text, f"{name} still ties STORY_ID to the profile's team key"
    assert f"{STORY_ID_SENTENCES[name]} {INVOCATION_KEY_TEAM}" in text, f"{name} lacks the invocation-key sentence"


def test_split_siblings_are_created_in_the_team_of_the_story() -> None:
    body = spaced(section(SKILL.read_text(), "Split rule"))
    assert (
        "- Siblings are created in the team of `STORY_ID`, as Team resolution in "
        "[references/linear.md](references/linear.md) states."
    ) in body


def test_split_confirms_the_differing_team_before_creating_siblings() -> None:
    body = spaced(section(SKILL.read_text(), "Split rule"))
    confirm = (
        "- When the team of `STORY_ID` differs from `profile.tracker.team_key`, confirm "
        "`profile.tracker.states.backlog` and each sibling label on that team before creating any sibling, "
        f"{DIFFERING_TEAM_CITE}."
    )
    assert confirm in body
    assert body.index(confirm) < body.index("- Siblings are created from the `linear-user-story` template.")


def test_triage_cites_the_differing_team_rule() -> None:
    body = spaced(section(SKILL.read_text(), "Triage"))
    assert (
        "- When the team of `STORY_ID` differs from `profile.tracker.team_key`, confirm "
        "`profile.tracker.states.ready`, `profile.tracker.states.backlog` and each label name on that team "
        f"before writing it, {DIFFERING_TEAM_CITE}."
    ) in body


def test_story_to_done_cites_the_differing_team_rule() -> None:
    text = (ROOT / "skills" / "story-to-done" / "SKILL.md").read_text()
    body = spaced(section(text, "1. Read the story and pick the starting point"))
    assert (
        "When the team of `STORY_ID` differs from `profile.tracker.team_key`, confirm each state name below "
        f"on that team before comparing against it, {DIFFERING_TEAM_CITE}."
    ) in body


def test_arguments_section_precedes_read_first() -> None:
    text = SKILL.read_text()
    assert text.index("\n## Arguments\n") < text.index("\n## Read first\n")


@pytest.mark.parametrize(
    "sentence",
    [
        "The closing message is the facilitator's final message to the owner when the invocation ends, on every end state and every stop.",
        "It names the outcome (the recorded estimate, unpointed, or split with the slice count) or the stop reason, including each `needs input`: the denied tracker write of Step 1 and the unpointed variance stop of Step 4.",
        "It carries the `metrics: on` or `metrics: off` line.",
    ],
)
def test_closing_message_is_defined_on_every_end_state_and_stop(sentence: str) -> None:
    assert sentence in skill_section(CLOSING)


def test_vendored_metrics_reference_is_present() -> None:
    copy = ROOT / "skills" / "story-refinement" / "references" / "metrics.md"
    assert copy.is_file()
    header = "<!-- GENERATED from shared/metrics.md by scripts/vendor_shared.py. Edit the source, then rerun the script. -->\n\n"
    assert copy.read_text() == header + (ROOT / "shared" / "metrics.md").read_text()


def test_only_the_metrics_consumers_list_metrics() -> None:
    """B3: only the two consumers `shared/metrics.md` names (this skill and story-to-done, SKL-48) vendor it."""
    assert sorted(name for name, caps in MANIFEST["skills"].items() if "metrics" in caps) == [
        "story-refinement", "story-to-done"]


def test_metrics_reference_is_linked_from_the_metrics_section_and_not_read_first() -> None:
    assert "[references/metrics.md](references/metrics.md)" in section(SKILL.read_text(), METRICS)
    assert "references/metrics.md" not in section(SKILL.read_text(), "Read first")


def test_metrics_section_opens_with_the_on_only_condition() -> None:
    assert skill_section(METRICS).startswith("This section applies only when `metrics` is on.")


@pytest.mark.parametrize(
    "sentence",
    [
        # B3: one line each, as the reference defines them.
        "Figures live only in one metrics file in the session's scratch directory, outside every per-role subdirectory.",
        "The metrics file is never named in any brief.",
        "A figure the runtime does not return is `not reported`; it is never estimated or inferred.",
        # B3: timing.
        "Time every launch the facilitator spawns, including each re-launch.",
        "Take the start timestamp immediately before the launch and the end timestamp when the launch returns.",
        # B4: independence.
        "Add no metrics of this invocation and no other role's figures from this invocation to any voter brief, voter input, SM/EM sizing context, refinement comment, Accept round result comment, or pointing, unpointed, or split record; story comments posted by an earlier invocation stay part of the story surface.",
        # B4: the summary in the closing message.
        "The closing message carries the run summary in the template `references/metrics.md` defines, on every end state and every stop, with every field filled or labelled as that reference defines (`not reported`, `cumulative`, `partial`, or, when the invocation performed no launch, `no launches` with `not applicable` totals), and the stop reason where the run stopped.",
        "The summary contains no secrets and no local or scratch paths.",
    ],
)
def test_metrics_section_states_the_bindings(sentence: str) -> None:
    assert sentence in skill_section(METRICS)


@pytest.mark.parametrize(
    "launch",
    [
        "the tracker-write preflight",
        "each Step 1 voter launch",
        "each PO launch that authors or applies a tracker write or record",
        "each accept-round voter launch",
        "each Step 3 pointing launch",
        "each Step 4 discussion launch",
        "each Step 4 basis-challenge launch",
        "each Step 4 re-vote launch",
        "each anchoring recovery re-launch",
        "each slice estimate launch",
    ],
)
def test_metrics_section_names_each_timed_launch_kind(launch: str) -> None:
    timed = bullet(section(SKILL.read_text(), METRICS), "Timed launches")
    assert flat(launch) in timed


def test_metrics_section_does_not_restate_the_reference() -> None:
    body = section(SKILL.read_text(), METRICS)
    for phrase in ("| Role | Runtime |", "Run metrics: <skill>", "Accept rounds:", "Pointing rounds:"):
        assert phrase not in body, phrase


def test_read_first_authority_rule_is_unchanged() -> None:
    assert (
        "Where this file and a capability file disagree, the capability file is authoritative, except the "
        "non-voting facilitator rule, the independence rules, and the anchoring guardrail here, which always override."
    ) in skill_section("Read first")


@pytest.mark.parametrize(
    "sentence",
    [
        "With `metrics` off or omitted, the facilitator does not open `references/metrics.md`, collects no figure, creates no metrics scratch file, posts no metrics comment, and adds no metrics content to any brief, record, report, todo list, closing message, or tracker write, other than the `metrics: off` line.",
        "Every other metrics instruction in this skill applies only when `metrics` is on.",
    ],
)
def test_arguments_section_states_the_off_path(sentence: str) -> None:
    assert sentence in skill_section(ARGUMENTS)


def test_metrics_mentions_outside_the_permitted_sections_are_absent() -> None:
    """B2: outside Arguments, Metrics, Closing, and the Roles and Triage bullets pinned separately, no metrics mention."""
    text = re.sub(r"<!--.*?-->", "", SKILL.read_text(), flags=re.DOTALL)
    for heading in (ARGUMENTS, METRICS, CLOSING, "Roles", "Triage"):
        text, count = re.subn(rf"^## {re.escape(heading)}\s*$.*?(?=^#{{1,2}} |\Z)", "", text,
                              flags=re.MULTILINE | re.DOTALL)
        assert count == 1, heading
    assert "metric" not in text.lower()


def test_readme_row_names_the_metrics_switch() -> None:
    row = next(line for line in (ROOT / "README.md").read_text().splitlines()
               if "skills/story-refinement/SKILL.md" in line)
    assert "`metrics` switch (default `off`)" in row
    assert "run summary in the closing message" in row


def test_todo_tracking_seed_collects_metrics_only_when_the_switch_is_on() -> None:
    seed = next(line for line in (ROOT / "shared" / "todo-tracking.md").read_text().splitlines()
                if line.startswith("- **story-refinement:**"))
    assert (
        "and, only when the `metrics` switch is on, record invocation start (metrics on), collect metrics, "
        "and post the metrics summary on the story." in seed
    )


def test_todo_tracking_seed_lists_invocation_start_first_among_metrics_on_items() -> None:
    seed = next(line for line in (ROOT / "shared" / "todo-tracking.md").read_text().splitlines()
                if line.startswith("- **story-refinement:**"))
    metrics_on = seed[seed.index("only when the `metrics` switch is on, ") + len("only when the `metrics` switch is on, "):]
    assert metrics_on.startswith("record invocation start (metrics on)")


def test_invocation_start_is_the_first_action_after_the_switch_resolves() -> None:
    bullets = [line for line in section(SKILL.read_text(), ARGUMENTS).splitlines() if line.startswith("- ")]
    resolve = next(i for i, line in enumerate(bullets) if line.startswith("- Resolve both arguments"))
    assert bullets[resolve + 1].startswith("- When `metrics` resolves on, the facilitator's next action, before the todo list,")


# --- SKL-92: the metrics summary is posted on the story -------------------------------------------


def metrics_body() -> str:
    """The Metrics section, whitespace collapsed, case kept: these pins are exact phrases."""
    return spaced(section(SKILL.read_text(), METRICS))


def test_metrics_section_posts_the_summary_as_its_own_sm_em_comment() -> None:
    body = metrics_body()
    assert "**Post:** When the invocation reaches a permitted post, the facilitator posts the summary" in body
    assert "the facilitator posts the summary on the story under refinement as its own SM/EM comment" in body
    assert "at the end of the invocation, when no further voter round will run in it" in body
    assert "reads its own comment back, and the closing message names the posted comment" in body


def test_metrics_section_pins_the_post_sequence_and_the_end_timestamp() -> None:
    assert (
        "On a permitted post, `invocation_end` is taken immediately before the summary is composed, and the comment "
        "and the closing message carry that same summary; no second timestamp is taken." in metrics_body()
    )


def test_metrics_reference_shares_the_timestamp_with_a_posted_summary() -> None:
    """The timing sequence is bound in the reference itself, so the skill and the capability agree."""
    text = spaced((ROOT / "shared" / "metrics.md").read_text())
    sentence = (
        "The elapsed wall-clock runs from the recorded `invocation_start`, the UTC timestamp taken with a command "
        "the moment the `metrics` switch resolved on, to `invocation_end`, a UTC timestamp taken with a command "
        "immediately before the closing message or closing report, or, where the skill composes the summary "
        "before that message, immediately before the summary is composed."
    )
    assert text.count(sentence) == 1
    assert (
        "A posted summary and the closing report therefore share one `invocation_end`, and the elapsed it reports "
        "excludes the post and its read-back."
    ) in text


def test_metrics_section_does_not_retry_a_failed_read_back() -> None:
    assert (
        "A failed or differing read-back is not retried: the closing message carries the summary and names the "
        "failed read-back." in metrics_body()
    )


def test_metrics_section_orders_the_post_as_the_last_tracker_write() -> None:
    body = metrics_body()
    assert "When a pointing record exists, the comment is the invocation's last tracker write." in body
    assert (
        "It posts only after every voter round, including every slice estimate under the Split rule, has finished; "
        "the pointing record (a recorded estimate, an unpointed result, or a split decision) and any split comment "
        "have been posted and read back; and the invocation's triage writes have been applied and read back." in body
    )


def test_metrics_section_posts_on_a_stop_only_after_the_step_one_inputs() -> None:
    assert (
        "On a stop before a pointing record exists, the comment posts only after every Step 1 voter input is "
        "recorded - with the three-voter roster, all three Stage 1 voter inputs - and every launched voter has "
        "returned or been stopped, with its end timestamp taken; on that path no pointing record and no triage "
        "write is required." in metrics_body()
    )


def test_metrics_section_attempts_no_post_before_the_step_one_inputs() -> None:
    assert (
        "A stop before every Step 1 voter input is recorded attempts no post, because Step 1 allows no tracker "
        "comment before then except the preflight, and the summary stays in the closing message." in metrics_body()
    )


def test_metrics_section_never_posts_during_an_anchoring_recovery() -> None:
    assert (
        "The comment is never posted while an anchoring recovery, its Step 3 re-run, or any Step 4 re-vote "
        "that follows them, is still to run." in metrics_body()
    )


def test_metrics_section_states_the_resumed_run_rule() -> None:
    assert (
        "A resumed run is a new invocation and posts its own comment covering only that invocation; a resume in "
        "the same session after the owner authorizes the denied tracker writes fallback is the same invocation "
        "and posts once." in metrics_body()
    )


def test_metrics_section_names_the_denied_post() -> None:
    body = metrics_body()
    assert (
        "If the post is denied or unavailable, the closing message carries the summary and names the denied or "
        "unavailable write, and no other tool or server is tried." in body
    )
    assert (
        "Where the run stopped on denied tracker writes without the owner's authorization, no post is attempted."
        in body
    )


def test_metrics_section_forbids_secrets_and_paths_in_the_comment() -> None:
    assert "The comment contains no secrets and no local or scratch paths." in metrics_body()


ROLES_METRICS_SENTENCE = (
    "When `metrics` is on, the metrics summary is the one comment the facilitator posts outside the denied "
    "tracker writes fallback.\n  It is the facilitator's own SM/EM comment, never a PO-authored write."
)
TRIAGE_METRICS_SENTENCE = (
    "When `metrics` is on, the metrics summary is the one comment the SM/EM posts outside the denied tracker "
    "writes fallback; it is the SM/EM's own comment, never a PO-authored write."
)


def test_roles_carry_the_metrics_posting_exception() -> None:
    raw = section(SKILL.read_text(), "Roles")
    assert ROLES_METRICS_SENTENCE in raw
    roles = flat(raw)
    # the phrases SKL-47 and the fallback stories pin stay verbatim
    assert "the only author of tracker writes" in roles
    assert "the facilitator applies tracker writes only under the denied tracker writes fallback" in roles


def test_triage_carries_the_metrics_posting_exception() -> None:
    raw = section(SKILL.read_text(), "Triage")
    assert TRIAGE_METRICS_SENTENCE in raw
    triage = flat(raw)
    # the phrases the fallback stories pin stay verbatim
    assert "the sm/em posts only its own comments" in triage
    assert "applies the po's writes only under the denied tracker writes fallback" in triage
    assert "applies and reads each one back, except under the denied tracker writes fallback" in triage


def test_roles_and_triage_add_only_their_one_metrics_sentence() -> None:
    roles = section(SKILL.read_text(), "Roles")
    triage = section(SKILL.read_text(), "Triage")
    assert roles.count(ROLES_METRICS_SENTENCE) == 1
    assert triage.count(TRIAGE_METRICS_SENTENCE) == 1
    assert "metric" not in roles.replace(ROLES_METRICS_SENTENCE, "").lower()
    assert "metric" not in triage.replace(TRIAGE_METRICS_SENTENCE, "").lower()


def test_closing_message_names_the_posted_comment() -> None:
    assert (
        "When `metrics` is on, it names the metrics summary comment the facilitator posted; when the post was "
        "denied or unavailable, it carries the summary and names the denied or unavailable write; when the "
        "read-back failed, it carries the summary and names the failed read-back; when no post was attempted, it "
        "carries the summary and names no comment." in skill_section(CLOSING)
    )


def test_metrics_section_no_longer_states_that_the_skill_does_not_post() -> None:
    text = spaced(SKILL.read_text())
    assert "This skill does not post the summary on the story" not in text
    assert "no posting statement in `references/metrics.md` applies to it" not in text
    assert 'This is an exception to the "Read first" rule' not in text


def story_refinement_seed(root: Path) -> str:
    todo = root / "shared" / "todo-tracking.md"
    return next(line for line in todo.read_text().splitlines() if line.startswith("- **story-refinement:**"))


def test_todo_tracking_seed_posts_the_metrics_summary_only_when_the_switch_is_on() -> None:
    seed = story_refinement_seed(ROOT)
    marker = "only when the `metrics` switch is on, "
    assert marker in seed, "the metrics-on condition is missing from the seed line"
    assert seed.endswith(
        "record invocation start (metrics on), collect metrics, and post the metrics summary on the story."
    )


def test_vendored_todo_tracking_seed_matches_the_shared_seed() -> None:
    copy = ROOT / "skills" / "story-refinement" / "references" / "todo-tracking.md"
    copy_seed = next(line for line in copy.read_text().splitlines() if line.startswith("- **story-refinement:**"))
    assert copy_seed == story_refinement_seed(ROOT)
    assert "post the metrics summary on the story" in copy_seed


def test_readme_row_says_the_summary_is_posted_on_the_story() -> None:
    row = next(line for line in (ROOT / "README.md").read_text().splitlines()
               if "skills/story-refinement/SKILL.md" in line)
    assert "run summary in the closing message" in row
    assert "posts it on the story" in row


# --- SKL-215: priority is an explicit PO step with a recorded comparison --------------------------

PRIORITY_BULLET_LEAD = "- Priority is the PO's decision on every refinement outcome:"


def priority_bullet() -> str:
    """The Triage bullet that carries the priority step: its lead line and its indented continuation lines only.

    A blank line, the next bullet or a loose paragraph ends the bullet, so a rule moved out of it is not counted.
    """
    lines = section(SKILL.read_text(), "Triage").splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(PRIORITY_BULLET_LEAD)), None)
    assert start is not None, f"Triage has no bullet starting {PRIORITY_BULLET_LEAD!r}"
    end = next((i for i in range(start + 1, len(lines)) if not lines[i].startswith("  ")), len(lines))
    return spaced("\n".join(lines[start:end]))


def test_triage_replaces_the_bare_priority_bullet() -> None:
    triage = section(SKILL.read_text(), "Triage")
    assert "Priority comes from the PO's decision." not in triage
    assert sum(line.startswith(PRIORITY_BULLET_LEAD) for line in triage.splitlines()) == 1


@pytest.mark.parametrize(
    "phrase",
    [
        # AC1: every outcome, decided before the invocation ends and before ready.
        "Priority is the PO's decision on every refinement outcome: the story moving to "
        "`profile.tracker.states.ready`, the story staying in `profile.tracker.states.backlog`, and each split sibling.",
        "The PO decides, applies and reads back a priority before the invocation ends and before any move to "
        "`profile.tracker.states.ready`, "
        "unless the ceremony stops on priority as this bullet states.",
        # AC1: the comparison basis.
        "The PO chooses the priority by comparing the story with at least one comparable story already prioritised "
        "in the team of `STORY_ID`.",
        # AC1: the PO-authored write and its read-back.
        "The PO applies the priority and reads it back as a PO-authored tracker write.",
        # AC1: "No priority" is unset.
        '"No priority" counts as unset and is never a decided value.',
        # AC2: the stop-and-ask path.
        "When the PO cannot decide, including when the team has no comparable prioritised story, the ceremony stops "
        'with the priority unset and "Priority is clear" unticked, and reports `needs input` to the owner naming '
        "the story",
        "The PO never guesses a priority.",
        # AC4: the tick rule.
        'The PO ticks "Priority is clear" only after the priority is read back and equals the decided value.',
        # AC4: the triage record the bullet points at.
        "The PO posts the Triage record from [references/refinement-record.md](references/refinement-record.md) "
        "as a triage write on every outcome, the priority stop included.",
    ],
)
def test_triage_priority_bullet_carries_the_phrase(phrase: str) -> None:
    assert phrase in priority_bullet()


def test_triage_priority_bullet_orders_decide_apply_stop_then_tick() -> None:
    """The decision precedes the write, the write precedes the stop path, and the tick comes after both."""
    bullet = priority_bullet()
    order = [
        "The PO decides, applies and reads back a priority before the invocation ends",
        "The PO chooses the priority by comparing the story",
        "The PO applies the priority and reads it back",
        "When the PO cannot decide",
        "The PO never guesses a priority.",
        'The PO ticks "Priority is clear" only after the priority is read back',
    ]
    counts = {phrase: bullet.count(phrase) for phrase in order}
    assert all(count == 1 for count in counts.values()), counts
    positions = [bullet.find(phrase) for phrase in order]
    assert positions == sorted(positions), dict(zip(order, positions))


def test_triage_priority_stop_names_itself_as_the_closing_stop_reason() -> None:
    """The bullet names its stop as the closing stop reason, relying on Closing's existing `needs input` clause.

    The second assertion does not prove a link; it keeps the Closing clause the bullet relies on, which this
    story leaves unedited.
    """
    assert "the closing message names that stop as its stop reason" in priority_bullet()
    assert "or the stop reason, including each `needs input`" in skill_section(CLOSING)


def test_records_lists_the_triage_record_template() -> None:
    body = spaced(section(SKILL.read_text(), "Records"))
    assert (
        "Use the Triage record template in the same file for the triage write that records the priority and the "
        "comparison it rests on."
    ) in body


def test_record_has_the_triage_record_template_with_exactly_the_fields() -> None:
    assert template("Triage record").splitlines() == [
        "## Triage record",
        "",
        "- Priority: <the decided value, read back; or unset when the PO could not decide>",
        "- Priority comparison: <each comparable story's identifier and priority; or `needs input` with the open "
        "question when the PO could not decide>",
        "- Tracker writes: product owner",
    ]


def record_triage_section() -> str:
    """The Triage record section of the record reference, fenced template and fallback included.

    `section()` would stop at the template's own `## Triage record` line inside the fence, so this slices from the
    section heading to the next `## ` heading outside a code fence, whichever section that is.
    """
    lines = RECORD.read_text().splitlines()
    start = next((i for i, line in enumerate(lines) if line.rstrip() == "## Triage record"), None)
    assert start is not None, "the record reference has a Triage record section"
    in_fence = False
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("```"):
            in_fence = not in_fence
        elif not in_fence and lines[i].startswith("## "):
            end = i
            break
    return "\n".join(lines[start + 1: end])


def test_record_says_the_triage_record_is_a_po_triage_write() -> None:
    raw = record_triage_section()
    body = spaced(raw)
    assert "- Priority comparison: <" in raw, "the section holds its own template"
    assert (
        "Post this as a tracker comment authored by the product owner as a triage write, on every refinement "
        "outcome and on each split sibling, and posted by the product owner or, under the denied tracker writes "
        "fallback, by the facilitator verbatim."
    ) in body
    assert (
        "The priority is the value read back after the PO applied it; when the PO could not decide, the priority "
        "stays unset and the comparison line carries `needs input` with the open question."
    ) in body
    assert (
        "Under the denied tracker writes fallback in `SKILL.md`, replace the tracker-writes line with:"
    ) in body
    assert WRITES_FACILITATOR_LINE in fallback_alternative("Triage record").splitlines()


# --- SKL-247: refinement checks repository guards against what a story commits -------------------

GUARDS = "Repository guards"
GUARD_ITEM = "Run the repository guard check in [Repository guards](#repository-guards) before any voter launches."
DOR_GUARD_BULLET = (
    "- When the story's acceptance criteria add or change any tracked file, "
    'the PO does not tick the "checked against the implementation" Definition of Ready box'
)
GUARD_ITEM_HEADINGS = (
    "Guard list", "Producible output", "Output not yet producible", "Rejection", "Stop", "Refresh", "No secrets",
)
# Each of this repository's guard names, matched with any run of spaces, underscores or hyphens between its words.
THIS_REPOSITORY_GUARD_PATTERNS = {
    "leak_scan": r"\bleak[\s_-]*scan\b",
    "test_house_spelling": r"\btest[\s_-]*house[\s_-]*spelling\b",
    "ci.yml": r"\bci\.ya?ml\b",
    "skills-ref": r"\bskills[\s_-]*ref\b",
}


def guards_section() -> str:
    return flat(section(SKILL.read_text(), GUARDS))


def guard_items() -> list[str]:
    """The numbered items of the Repository guards section, index 0 being the text before item 1, each flattened."""
    return [flat(part) for part in re.split(r"^\d+\. ", section(SKILL.read_text(), GUARDS), flags=re.MULTILINE)]


def dor_guard_bullet() -> str:
    """The one Triage bullet that holds the guard condition on the implementation-check DoR box, continuation lines included."""
    lines = section(SKILL.read_text(), "Triage").splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(DOR_GUARD_BULLET)]
    assert len(starts) == 1, f"expected one Triage bullet starting {DOR_GUARD_BULLET!r}, found {len(starts)}"
    start = starts[0]
    end = next((i for i in range(start + 1, len(lines)) if not lines[i].startswith("  ")), len(lines))
    return flat("\n".join(lines[start:end]))


def test_guards_section_items_keep_their_headings_in_order() -> None:
    """The numbered cross-references ("item 2", "item 4") keep pointing at the requirement they name."""
    items = guard_items()
    assert len(items) == len(GUARD_ITEM_HEADINGS) + 1, "one item per heading"
    for number, heading in enumerate(GUARD_ITEM_HEADINGS, start=1):
        assert items[number].startswith(f"**{heading.lower()}.**"), (number, heading)


GUARD_LIST_PHRASES = (
    (0, "before any voter launches, whenever the story's acceptance criteria add or change any tracked file"),
    (1, "lists the guards of the repository under refinement that every added or changed tracked file must pass"),
    (1, "not only checks on the files the story edits"),
    (1, "test modules that scan tracked files, linters, schema or spec validators, and leak or spelling scanners"),
    (1, "discovers them from that repository's ci configuration and test suite"),
    (1, "the refinement note records each guard, the command that runs it, and the discovery source"),
    (1, "the guard list is part of the story surface every voter receives"),
    (1, "the refined acceptance criteria require every added or changed tracked file the story commits to pass every "
        "guard on the guard list"),
)


@pytest.mark.parametrize("item, phrase", GUARD_LIST_PHRASES)
def test_guards_section_requires_the_guard_list(item: int, phrase: str) -> None:
    """AC1: the facilitator lists every repository guard before the voters launch."""
    assert phrase in guard_items()[item]


def test_step_one_runs_the_guard_check_after_the_probe_and_before_any_voter() -> None:
    """AC1: the guard list exists before the voters launch, so it reaches the story surface they receive."""
    probe = step_one_item_index("Run the tracker-write preflight before any voter launches")
    guard = step_one_item_index(GUARD_ITEM)
    launch = step_one_item_index("Launch the three engineers in separate contexts")
    assert probe < guard < launch, "the guard check must sit between the probe and the voter launch"
    assert process_item("Step 1: Independent refinement", GUARD_ITEM) == GUARD_ITEM


def test_step_one_voter_brief_carries_the_guard_list() -> None:
    """AC1: the voter launch brief, which lists everything a voter receives, includes the guard list."""
    launch = flat(process_item("Step 1: Independent refinement", "Launch the three engineers in separate contexts"))
    assert (
        "give each voter only its own profile entry, the story, the guard list from "
        "[repository guards](#repository-guards) when that check ran,"
    ) in launch


def test_reviewer_output_contract_includes_a_guard_list_verdict() -> None:
    """AC1: every voter's input carries a verdict on the guard list."""
    contract = bullet(step(SKILL.read_text(), "Step 1: Independent refinement"), "Reviewer output contract")
    assert "a verdict on the guard list" in contract


PRODUCIBLE_OUTPUT_PHRASES = (
    "a recorded baseline, a captured dossier, or a golden file produced by a tool or by an earlier commit",
    "the exact bytes the story commits where they exist before implementation, "
    "otherwise a representative sample produced the same way",
    "places the output at its intended path in a throwaway checkout",
    "stages it there so guards that enumerate tracked files see it",
    "every guard runs twice, once with the output staged and not yet committed and once after the output is "
    "committed there, so a guard that reads the staged set, the index or committed content sees it; a guard passes "
    "only when both runs pass",
    "a run passes only when the guard exits zero and reports no finding",
    "runs every guard on the guard list against it from that checkout, leaving the primary checkout unchanged",
    "the throwaway checkout is a disposable clone of the repository under refinement with its own object store, "
    "never a worktree that shares one, at the revision the story's work starts from; it sits in the session's "
    "scratch directory, and the whole clone is removed after the check",
    "for each guard, the command, the exit status and the result of each run, "
    "and for a sample its provenance and coverage limits",
)


@pytest.mark.parametrize("phrase", PRODUCIBLE_OUTPUT_PHRASES)
def test_guards_section_runs_producible_output_through_every_guard(phrase: str) -> None:
    """AC2: producible generated or frozen output is staged in a throwaway checkout and run through every guard."""
    assert phrase in guard_items()[2]


NOT_PRODUCIBLE_PHRASES = (
    "cannot be produced before implementation because code the story writes generates it, "
    "the refinement note states why",
    "naming the code the story writes that generates it and confirming that no tool or earlier commit produces "
    "those bytes before implementation",
    "the refined acceptance criteria require the committed output to pass every guard on the guard list "
    "and name the resolution the implementer may use if a guard rejects it, chosen from the kinds item 4 lists",
)


@pytest.mark.parametrize("phrase", NOT_PRODUCIBLE_PHRASES)
def test_guards_section_covers_output_not_producible_before_implementation(phrase: str) -> None:
    """AC3: output only the story's code can generate still carries the guard requirement and a resolution."""
    assert phrase in guard_items()[3]


REJECTION_PHRASES = (
    "when a guard rejects output checked under item 2, the refined acceptance criteria state the resolution",
    "an exemption the story adds, scoped to its own files; a normalization; an encoding; "
    "or an amendment to the criterion that forbade one of these",
    "the resolved output is re-run through the rejecting guard and passes",
    "and through every other guard on the guard list, which pass too",
    "the refinement note records the rejection, the resolution and the passing re-run",
)


@pytest.mark.parametrize("phrase", REJECTION_PHRASES)
def test_guards_section_resolves_a_rejection_with_a_passing_re_run(phrase: str) -> None:
    """AC4: a rejection ends in a stated resolution and a passing re-run, recorded in the refinement note."""
    assert phrase in guard_items()[4]


def test_guards_section_stops_on_an_unrunnable_guard_or_a_surviving_rejection() -> None:
    """AC5: a guard that cannot run, or a rejection the resolution does not clear, stops the ceremony."""
    assert (
        "when a guard on the guard list cannot be run, or the resolved output still fails any guard on the guard list, "
        "the facilitator stops and reports `needs input` to the owner naming the guard, its command and its result"
    ) in guard_items()[5]
    stop = bullet(step(SKILL.read_text(), "Step 1: Independent refinement"), "Stop")
    assert "a guard on the guard list cannot be run or still rejects the resolved output" in stop


@pytest.mark.parametrize(
    "phrase",
    [
        "when an accept-round amendment adds or changes a tracked file or committed output the check has not "
        "covered, the facilitator runs the check again against the amended acceptance criteria before the updated "
        "refinement comment is posted",
        "a split sibling under the [split rule](#split-rule), and a story whose acceptance criteria changed after an "
        "earlier check, get the check against their own final acceptance criteria",
    ],
)
def test_guards_section_refreshes_the_check_against_the_final_criteria(phrase: str) -> None:
    """AC5: the check covers the story's final acceptance criteria, amendments and split siblings included."""
    assert phrase in guard_items()[6]


def test_guards_section_keeps_secrets_out_of_guard_evidence() -> None:
    """Guard evidence reaches voters and the tracker, so a rejection on secret text is cited, never quoted."""
    assert (
        "the guard list, guard output given to a voter, and the refinement note contain no secrets: a rejection "
        "that matched secret text is cited by guard, file and line, never quoted"
    ) in guard_items()[7]


def test_records_carry_the_guard_evidence() -> None:
    """AC1, AC2, AC4: the Records contract carries every guard field the refinement note records."""
    assert (
        "when the [repository guards](#repository-guards) check ran, the refinement comment also records the guard "
        "list with each guard's command and discovery source; for each guard run, its command, exit status and "
        "result; each sample's provenance and coverage limits; and each rejection with its resolution and passing "
        "re-run, with no secrets under item 7 of [repository guards](#repository-guards)"
    ) in flat(section(SKILL.read_text(), "Records"))


DOR_GUARD_PHRASES = (
    "when the story's acceptance criteria add or change any tracked file, the po does not tick",
    'the po does not tick the "checked against the implementation" definition of ready box '
    "while the guard list is missing",
    "the check did not run against the story's final acceptance criteria",
    "output was classed under item 3 without the evidence item 3 requires",
    "producible output under item 2 of [repository guards](#repository-guards) was not run",
    "a guard could not be run",
    "or a guard rejection lacks a resolution with a passing re-run",
)


@pytest.mark.parametrize("phrase", DOR_GUARD_PHRASES)
def test_triage_holds_the_implementation_check_box_on_the_guard_check(phrase: str) -> None:
    """AC5: the implementation-check DoR box stays unticked until the guard check is complete."""
    assert phrase in dor_guard_bullet()


def test_guard_phrase_pins_keep_their_count() -> None:
    """Dropping a pinned phrase from a parametrize list fails here instead of silently shrinking the suite."""
    assert [len(GUARD_LIST_PHRASES), len(PRODUCIBLE_OUTPUT_PHRASES), len(NOT_PRODUCIBLE_PHRASES),
            len(REJECTION_PHRASES), len(DOR_GUARD_PHRASES)] == [8, 9, 3, 5, 7]


@pytest.mark.parametrize(
    "phrase",
    [
        "the guards and their commands come from the repository under refinement; this skill names guard kinds only",
        "test modules that scan tracked files, linters, schema or spec validators, and leak or spelling scanners",
        "stages it there so guards that enumerate tracked files see it",
    ],
)
def test_guards_section_names_kinds_not_one_repository(phrase: str) -> None:
    """AC6: the procedure names guard kinds and capabilities and leaves every concrete guard to the repository."""
    assert phrase in guards_section()


def test_skill_names_none_of_this_repository_guards() -> None:
    """AC6: the skill names none of this repository's guard commands, scripts, tests or paths, in any spelling."""
    text = SKILL.read_text().lower()
    assert "## repository guards" in text, "the added section is present"
    for name, pattern in THIS_REPOSITORY_GUARD_PATTERNS.items():
        assert not re.search(pattern, text), name
