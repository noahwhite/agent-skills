"""Contract checks for the story-refinement skill and its profile keys."""

import ast
import inspect
import json
import re
import textwrap
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


FENCE_OPEN = re.compile(r" {0,3}(?:(`{3,})([^`]*)|(~{3,})(.*))")


def fence_opening(line: str) -> tuple[str, str] | None:
    """The fence marker and info string a line opens a fenced code block with, or None.

    A fence opens with three or more backticks or tildes indented at most three spaces; a backtick fence's info
    string holds no backtick, so a line that only starts with an inline code span opens nothing.
    """
    match = FENCE_OPEN.fullmatch(line.rstrip("\r\n"))
    if not match:
        return None
    marker = match.group(1) or match.group(3)
    info = match.group(2) if match.group(1) else match.group(4)
    return marker, info.strip()


def fence_ids(lines: list[str], where: str = "") -> list[int]:
    """Per line, the index of the fenced code block it belongs to (delimiters included), or -1 for prose.

    A fence closes with a line of the same character, at least as long, and nothing else; an unclosed fence fails as
    its own error, naming `where`, so a broken fence is never reported as a missing section.
    """
    ids, current, marker = [], -1, ""
    count = 0
    for line in lines:
        if marker:
            ids.append(current)
            if re.fullmatch(rf" {{0,3}}{re.escape(marker[0])}{{{len(marker)},}}[ \t]*", line.rstrip("\r\n")):
                marker = ""
            continue
        opening = fence_opening(line)
        if opening:
            marker, current = opening[0], count
            count += 1
            ids.append(current)
            continue
        ids.append(-1)
    assert not marker, f"unclosed code fence (block {current}){where}"
    return ids


def section(text: str, heading: str, level: int = 2, until: int | None = None, keep_fences: bool = False) -> str:
    """The operative text under a heading, up to the next heading of level `until` (default: the same) or higher.

    HTML comments are removed first, since commented-out text is not operative, and an unclosed one fails rather
    than leaving the text it opens operative; a heading-like line inside a fenced code block (a record template's own
    `## ...` title, for example) is neither the heading nor its end.
    Fenced code blocks are dropped too, since an instruction inside one is an example, not a rule; only a reader of
    a record or filing template passes `keep_fences=True` (see FENCE_READERS).
    """
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    assert "<!--" not in text, f"unclosed HTML comment (looking for {heading})"
    lines = text.splitlines(keepends=True)
    ids = fence_ids(lines, f" (looking for {heading})")
    own = re.compile(rf"{'#' * level} {re.escape(heading)}\s*$")
    ends = re.compile(rf"#{{1,{until or level}}} ")
    start, end = None, len(lines)
    for index, line in enumerate(lines):
        if ids[index] != -1:
            continue
        if start is None:
            if own.match(line):
                start = index + 1
        elif ends.match(line):
            end = index
            break
    assert start is not None, f"missing section: {heading}"
    return "".join(line for line, block in zip(lines[start:end], ids[start:end]) if keep_fences or block == -1)


def segments(body: str) -> list[tuple[str, str, str]]:
    """A section body split in order into ("prose", text, "") and ("fence", content, info string) parts.

    A fence part's content excludes its delimiter lines.
    """
    lines = body.splitlines(keepends=True)
    ids = fence_ids(lines)
    parts: list[tuple[int, list[str]]] = []
    for line, block in zip(lines, ids):
        if parts and parts[-1][0] == block:
            parts[-1][1].append(line)
        else:
            parts.append((block, [line]))
    return [
        ("prose", "".join(chunk), "") if block == -1 else ("fence", "".join(chunk[1:-1]), fence_opening(chunk[0])[1])
        for block, chunk in parts
    ]


def prose(body: str) -> str:
    """A section body without its fenced code blocks, so a prose rule cannot be met by template text."""
    return "".join(text for kind, text, _ in segments(body) if kind == "prose")


def flat(text: str) -> str:
    return " ".join(text.lower().split())


def bullet(body: str, label: str) -> str:
    """One labelled bullet of a section body, flattened; fenced blocks are dropped first, so a bullet moved into a
    code fence is not a bullet."""
    body = prose(body)
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
    start = next(
        (index for index, line in enumerate(lines) if line.startswith("- ⛔ Split a story whose estimate is")), None
    )
    assert start is not None, "shared/linear.md has no bullet starting '- ⛔ Split a story whose estimate is'"
    end = next(index for index in range(start + 1, len(lines)) if lines[index] and not lines[index].startswith(" "))
    bullet = flat(" ".join(lines[start:end]))
    assert bullet.startswith(
        "- ⛔ split a story whose estimate is above `profile.refinement.point_cap` or is 8 or more, without asking, "
        "before it is assigned or work is delegated, and present the slices."
    ), "the split rule starts with one unqualified sentence"
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


# --- SKL-304: a split is bounded by two rounds and the split bounds; SKL-230's never-escalate rule is superseded ---

RESPLIT_BULLET = (
    "- A slice that meets the split trigger is split again, within the two-round cap below, under these same "
    "bullets, along the boundary order in "
    "Estimation and slicing in [references/linear.md](references/linear.md): it stays the core slice and blocks its "
    "new siblings, every acceptance criterion of the slice is mapped to a sub-slice in a split comment, and each "
    "sub-slice, the core slice included, gets its own three-voter blind estimate."
)
ROUND_CAP = (
    "- A split runs at most two split rounds: split round 1 splits the whole story and split round 2 splits the "
    "round-1 slices that still meet it; a slice that still meets the split trigger after split round 2 stops the "
    "ceremony with `needs input` naming the slices and their values, before a third split is made, and no "
    "third-round split, estimate, record or tracker write happens."
)
SPLIT_BOUNDS = (
    "- After each split round the facilitator applies the split bounds in Estimation and slicing in "
    "[references/linear.md](references/linear.md): each slice's recorded value is strictly below the recorded value "
    "of the story it is split from, the slices of each parent are compared to that parent as a sum, and the sum of "
    "the current leaf slices' recorded values is compared to the original whole-story recorded estimate, each "
    "comparison stopping with `needs input`, warning in the split comment or proceeding with no flag by the bands "
    "stated there. "
    "A stop holds every further split round, estimate, record and tracker write for the slices until the owner "
    "answers. "
    "A round with a leaf slice recorded as unpointed still applies the per-slice bound and the round cap to each "
    "recorded value, records the sum comparisons as pending in the split comment and runs them once the owner's "
    "answer gives every leaf slice a recorded value."
)
SUPERSESSION = "- The two-round cap and the split bounds supersede the never-escalate rule of SKL-230."
# The SKL-230 sentences this story removes, split so a repository search for them finds no literal copy here.
STALE_SPLIT_SENTENCES = (
    "the split repeats until " + "no slice meets the split trigger",
    "There is no escalation exit " + "for an oversize slice",
    "as many rounds as it takes, " + "until no slice meets it; there is no escalation exit",
)
UNPOINTED_SLICE_STOP = (
    "A slice that takes the unpointed variance stop is recorded as unpointed in the split comment with its derived "
    "values, and the ceremony reports `needs input` to the owner naming the story, the slice and those values, so a "
    "partially pointed split always ends in that report rather than in an estimate, and its recorded outcome is the "
    "slice count with `needs input` for each unpointed slice."
)
# Phrases only the boundary order in shared/linear.md states; the Split rule cites it instead.
BOUNDARY_ORDER_PHRASES = (
    "planned PR or slice boundary",
    "narrower observable criteria",
    "interface or schema first",
)
SPLIT_RULE_SECTION = " ".join(
    (
        "The effective accepted maximum is `profile.refinement.point_cap` (default 5), with a schema maximum of 8.",
        "A story is split when its recorded estimate is above `profile.refinement.point_cap` or is 8 or more; the "
        "recorded estimate is the consensus, or the value the Step 4 consensus check or residual variance rule "
        "records.",
        "The lower trigger applies, and the 8-point rule in [references/linear.md](references/linear.md) is never "
        "relaxed.",
        "If the split trigger is met, split the story.",
        "- The original issue stays the core slice.",
        "- Siblings are created in the team of `STORY_ID`, as Team resolution in "
        "[references/linear.md](references/linear.md) states.",
        "- When the team of `STORY_ID` differs from `profile.tracker.team_key`, confirm "
        "`profile.tracker.states.backlog` and each sibling label on that team before creating any sibling, under the "
        "differing-team rule in Team resolution in [references/linear.md](references/linear.md).",
        "- Siblings are created from the `linear-user-story` template.",
        "- The original issue blocks each sibling.",
        "- Every acceptance criterion is mapped to a slice in the split comment.",
        "- Each slice gets its own three-voter estimate in the same blind round, with newly created voter contexts, "
        "and that round runs the same Step 4 consensus check, basis review and residual variance rule, so a slice "
        "records an estimate or takes the unpointed variance stop on the same terms.",
        UNPOINTED_SLICE_STOP,
        RESPLIT_BULLET,
        ROUND_CAP,
        SPLIT_BOUNDS,
        SUPERSESSION,
        "Cite [references/linear.md](references/linear.md) for the split mechanics; do not restate them here.",
    )
)
SPLIT_TRIGGER_PATTERN = re.compile(r"is above (`profile\.refinement\.point_cap`) or is (\d+) or more")


def test_split_rule_bounds_a_split_by_two_rounds_and_the_split_bounds() -> None:
    body = spaced(section(SKILL.read_text(), "Split rule"))
    for sentence in (RESPLIT_BULLET, ROUND_CAP, SPLIT_BOUNDS, SUPERSESSION):
        assert sentence in body, sentence


def test_split_rule_drops_the_superseded_never_escalate_sentences() -> None:
    body = spaced(section(SKILL.read_text(), "Split rule"))
    for sentence in STALE_SPLIT_SENTENCES:
        assert sentence not in body, f"the Split rule still carries the superseded sentence: {sentence}"
    stray = re.findall(r"escalat\w*", body.replace("never-escalate rule of SKL-230", ""), re.IGNORECASE)
    assert not stray, f"an escalation mention other than the SKL-230 supersession remains: {stray}"


SPLIT_BOUNDS_ROUTE = (
    "A round with no stop posts the block in the split comment.",
    "A round with a leaf slice recorded as unpointed and no stop posts the block in the split comment with result "
    "pending, naming the unpointed slices, and the sum checks run once the owner's answer gives every leaf slice a "
    "recorded value.",
    "With a leaf slice recorded as unpointed, the whole-story and each affected per-parent sum line read "
    "`sum pending: unpointed <slice keys>; band pending` in place of their sums and band, and a round with no stop "
    "and a pending line is pending.",
    "A stop posts nothing to the tracker: it reports `needs input` to the owner in one message carrying the block, "
    "and no further split round, slice record or tracker write for the slices happens until the owner answers.",
)
SPLIT_BOUNDS_FIELDS = (
    "- Split bounds, round <1 | 2>: <clear | warning | stop | pending: unpointed <slice keys>>",
    "- Whole-story sum: base <original whole-story recorded estimate>; 1.0 times = <value>, 1.5 times = <value>; "
    "sum <sum with each leaf slice's lower consensus value> (lower), <sum with each leaf slice's higher consensus "
    "value> (higher); band <clear | warning | stop>",
    "- Saturated base: <n/a, or: the base <value> is the highest value of the step sequence for <scale>, so the base "
    "is saturated and the 1.0 and 1.5 bounds computed from it are lower bounds on the true size>",
    "- Per-parent sum, one line per parent split this round: parent <key> <recorded value>; 1.0 times = <value>, "
    "1.5 times = <value>; sum of its slices <value> (lower), <value> (higher); band <clear | warning | stop>",
    "- Per-parent bound:",
    "- Round cap:",
    "- Warning for the human at triage:",
)
SPLIT_BOUNDS_EXAMPLE_RESULTS = (
    ("13 against 8 and 12", "stop"),
    ("12 against 8 and 12", "proceeds; the split comment carries the warning"),
    ("8 against 8 and 12", "proceeds with no flag"),
    ("11 against 8 and 12", "stop: parent 8, slice 8"),
    (
        "parent 8: 13 against 8 and 12 (stop); whole story: leaves 5, 5, 3, 5 sum 18 against 13 and 19.5 (warning)",
        "stop",
    ),
    ("leaf sum 13 against 13 and 19.5", "stop before a third split"),
    ("leaf sum 8 against 8 and 12", "proceeds unchanged"),
    ("21 against 13 and 19.5", "stop: the message names the base 13 saturated"),
)


def split_bounds_record() -> str:
    return section(RECORD.read_text(), "Split bounds")


def test_split_bounds_record_routes_a_stop_to_the_owner_not_the_tracker() -> None:
    body = spaced(split_bounds_record())
    for sentence in SPLIT_BOUNDS_ROUTE:
        assert sentence in body, sentence


def test_split_bounds_record_carries_both_round_two_verdicts() -> None:
    body = template_block("Split bounds")[0]
    for field in SPLIT_BOUNDS_FIELDS:
        assert field in body, field


def test_split_bounds_worked_examples_compute_their_bands() -> None:
    """Every "S against L and U" pair has U = 1.5 L, and its row's result follows the bands."""
    rows = [
        line
        for line in split_bounds_record().splitlines()
        if line.startswith("| ") and " against " in line and not line.startswith("| Case ")
    ]
    assert len(rows) == 9, rows
    pairs = re.findall(r"(\d+(?:\.\d+)?) against (\d+(?:\.\d+)?) and (\d+(?:\.\d+)?)", "\n".join(rows))
    assert pairs
    for total, lower, upper in pairs:
        assert float(upper) == 1.5 * float(lower), (total, lower, upper)
    plain = 0
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if re.fullmatch(r"\d+(, \d+)+", cells[2]):
            plain += 1
            stated = int(re.match(r"(?:leaf sum )?(\d+) against", cells[3]).group(1))
            assert sum(map(int, cells[2].split(", "))) == stated, row
    assert plain == 6, plain
    for pair_text, result in SPLIT_BOUNDS_EXAMPLE_RESULTS:
        matching = [row for row in rows if f"| {pair_text} |" in row]
        assert matching, pair_text
        for row in matching:
            assert f"| {pair_text} | {result}" in row, (pair_text, result)
        total, lower, upper = map(float, re.search(r"(\d+) against (\d+) and (\d+(?:\.\d+)?)", pair_text).groups())
        band = "stop" if total > upper else "warning" if total > lower else "clear"
        if "parent" not in pair_text and "slice 8" not in result and "third split" not in result:
            assert (band == "stop") == result.startswith("stop"), (pair_text, band, result)
            assert (band == "warning") == ("warning" in result), (pair_text, band, result)


def test_split_rule_section_is_exactly_the_rule() -> None:
    """Pin the whole section, so an added stop, approval or hand-off for an oversize slice fails."""
    assert spaced(section(SKILL.read_text(), "Split rule")) == SPLIT_RULE_SECTION


def test_split_rule_cites_the_boundary_order_without_restating_it() -> None:
    body = spaced(section(SKILL.read_text(), "Split rule"))
    assert "boundary order in Estimation and slicing in [references/linear.md](references/linear.md)" in body
    for phrase in BOUNDARY_ORDER_PHRASES:
        assert phrase not in body, f"the Split rule restates the boundary order: {phrase}"


def test_split_rule_keeps_the_unpointed_variance_stop() -> None:
    body = spaced(section(SKILL.read_text(), "Split rule"))
    assert UNPOINTED_SLICE_STOP in body


def test_skill_and_shared_linear_state_the_same_split_trigger() -> None:
    skill = SPLIT_TRIGGER_PATTERN.findall(spaced(section(SKILL.read_text(), "Split rule")))
    shared = SPLIT_TRIGGER_PATTERN.findall(
        spaced(section((ROOT / "shared" / "linear.md").read_text(), "Estimation and slicing"))
    )
    assert len(skill) == 1, f"the Split rule states one trigger, found {skill}"
    assert len(shared) == 1, f"Estimation and slicing states one trigger, found {shared}"
    assert skill == shared, f"the triggers differ: SKILL.md {skill}, shared/linear.md {shared}"


def pointing_template() -> list[str]:
    body = section(RECORD.read_text(), "Pointing record", keep_fences=True)
    fences = [text for kind, text, _ in segments(body) if kind == "fence"]
    templates = [text for text in fences if text.startswith("## Pointing record\n")]
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
    """A step's operative text, scoped by `section()` at the step heading's level."""
    return section(text, heading, level=3)


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
        operative_step("Step 2: Reconciliation and the accept round")
    )
    assert "applies the po's writes only under the denied tracker writes fallback" in squash(section(text, "Triage"))


def test_probe_denial_has_a_resume_path_under_the_fallback() -> None:
    body = squash(step(SKILL.read_text(), "Step 1: Independent refinement"))
    assert "later write kinds fall under the denied tracker writes fallback" in body
    assert "after the owner acts, run the probe again" in body
    assert "if the owner directly authorizes the facilitator under the denied tracker writes fallback, the facilitator applies the po-authored probe verbatim, records its comment id, and the voters launch" in body


def test_record_allows_facilitator_posting_under_the_fallback() -> None:
    assert "posted by the product owner or, under the denied tracker writes fallback, by the facilitator verbatim" in squash(
        prose(section(RECORD.read_text(), "Refinement comment"))
    )


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


def template_block(heading: str) -> tuple[str, list[tuple[str, str, str]]]:
    """The first `markdown` fenced block in the heading's `section()`, and the two `segments()` parts after it."""
    parts = segments(section(RECORD.read_text(), heading, keep_fences=True))
    fenced = [index for index, (kind, _, info) in enumerate(parts) if kind == "fence" and info == "markdown"]
    assert fenced, f"no ```markdown template block under {heading}"
    first = fenced[0]
    assert parts[first][1].strip(), f"empty template block under {heading}"
    return parts[first][1], parts[first + 1: first + 3]


def template(heading: str) -> str:
    return template_block(heading)[0]


def fallback_alternative(heading: str) -> tuple[str, str]:
    """The prose introducing the fallback alternative right after the template, and the `markdown` block it introduces.

    Only those two parts, in that order, are the alternative, so neither a later fence nor text elsewhere in the
    section can stand in for it, and drift in that shape fails here by name.
    """
    _, following = template_block(heading)
    shape = [(kind, info) for kind, _, info in following]
    assert shape == [("prose", ""), ("fence", "markdown")], (
        f"under {heading}, expected prose then a ```markdown fallback block after the template, found {shape}"
    )
    return following[0][1], following[1][1]


@pytest.mark.parametrize("heading", ["Refinement comment", "Pointing record"])
def test_template_carries_the_preflight_line(heading: str) -> None:
    assert PREFLIGHT_LINE in template(heading).splitlines()


@pytest.mark.parametrize("heading", ["Refinement comment", "Pointing record"])
def test_template_carries_the_product_owner_writes_line(heading: str) -> None:
    assert WRITES_PO_LINE in template(heading).splitlines()


@pytest.mark.parametrize("heading", ["Refinement comment", "Pointing record"])
def test_template_carries_the_facilitator_writes_alternative(heading: str) -> None:
    intro, block = fallback_alternative(heading)
    assert WRITES_FACILITATOR_LINE in block.splitlines()
    assert "Under the denied tracker writes fallback in `SKILL.md`, replace the tracker-writes line with:" in intro.splitlines()


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
    """A step's operative text; `section()` removes HTML comments, since commented-out text is not operative."""
    return step(SKILL.read_text(), heading)


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
    body = spaced(prose(section(RECORD.read_text(), "Pointing record")))
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
        "- Outcome: <accepted, another round, or unpointed for a User Story; "
        "accepted, another round, or not accepted for a Bug, an Investigation or a Spike>",
        "- Blocking amendments: <each objecting voter's blocking amendments when any voter returned OBJECT; "
        "otherwise none>",
    ]


def test_record_says_the_result_comment_is_separate_and_posted_after_each_round() -> None:
    body = spaced(prose(section(RECORD.read_text(), "Accept round result")))
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
    intro = spaced(prose(section(RECORD.read_text(), "Refinement and pointing records", level=1, until=2)))
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
        "When `metrics` resolves on, the facilitator's first command, right after the todo list is created, is to take a UTC timestamp with a command and record it as `invocation_start` in the metrics file.",
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
    wanted = ("## Arguments", "## Read first")
    order = [line for line in section(SKILL.read_text(), "Story refinement", level=1).splitlines() if line in wanted]
    assert order == list(wanted), order


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


def test_invocation_start_is_the_first_command_after_the_todo_list() -> None:
    bullets = [line for line in section(SKILL.read_text(), ARGUMENTS).splitlines() if line.startswith("- ")]
    resolve = next(i for i, line in enumerate(bullets) if line.startswith("- Resolve both arguments"))
    assert bullets[resolve + 1].startswith(
        "- When `metrics` resolves on, the facilitator's first command, right after the todo list is created,"
    )


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
        "right after the todo list is created, once the `metrics` switch resolved on, to `invocation_end`, "
        "a UTC timestamp taken with a command "
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
    assert (
        "record invocation start (metrics on), collect metrics, and post the metrics summary on the story." in seed
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
        "- State: <for a Bug, an Investigation or a Spike: ready: all conditions met, or backlog with each unmet "
        "condition, or for an issue already in progress or later its retained state with all conditions met or with "
        "each unmet condition; for a Spike with more than one independent research thread the unmet condition reads "
        "re-file as separate Spikes (owner); when the `Scope signal:` line is missing or carries neither of its type's "
        "readings the unmet condition reads scope signal missing; omitted for a User Story>",
        "- Tracker writes: product owner",
    ]


def record_triage_section() -> str:
    """The Triage record section of the record reference, fenced template and fallback included."""
    return section(RECORD.read_text(), "Triage record")


def test_record_says_the_triage_record_is_a_po_triage_write() -> None:
    raw = record_triage_section()
    body = spaced(prose(raw))
    assert "- Priority comparison: <" in template("Triage record"), "the section holds its own template"
    assert (
        "Post this as a tracker comment authored by the product owner as a triage write, on every refinement "
        "outcome and on each split sibling, and posted by the product owner or, under the denied tracker writes "
        "fallback, by the facilitator verbatim."
    ) in body
    assert (
        "The priority is the value read back after the PO applied it; when the PO could not decide, the priority "
        "stays unset and the comparison line carries `needs input` with the open question."
    ) in body
    intro, block = fallback_alternative("Triage record")
    assert "Under the denied tracker writes fallback in `SKILL.md`, replace the tracker-writes line with:" in intro.splitlines()
    assert WRITES_FACILITATOR_LINE in block.splitlines()


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
        "a split sibling under the [split rule](#split-rule) gets the check against its own acceptance criteria before "
        "its estimate voters launch, and its guard list is part of the story surface those voters receive",
        "a story whose acceptance criteria changed after an earlier check gets the check against its final acceptance "
        "criteria before the po decides",
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


# --- SKL-237: a Bug, an Investigation or a Spike is refined and never pointed -------------------------

UNESTIMATED = "Unestimated issue types"
UNESTIMATED_LINK = "[Unestimated issue types](#unestimated-issue-types)"
TYPE_ITEM = "Run the type check after the roster check and before the tracker-write preflight"
STEP_ONE = "Step 1: Independent refinement"
POINTING_SKIPPED = (
    "Pointing skipped: <Bug|Investigation|Spike> is unestimated (references/linear.md, Estimation and slicing)"
)


def unestimated_bullet(label: str) -> str:
    """One labelled bullet of the issue-type section, flattened, nested bullets included."""
    return bullet(section(SKILL.read_text(), UNESTIMATED), label)


def type_item() -> str:
    return process_item(STEP_ONE, TYPE_ITEM)


def test_step_one_reads_the_labels_with_the_story() -> None:
    """B1: the todo list exists first, then the story read carries the issue's labels."""
    assert process_items(STEP_ONE)[0].startswith(
        "With the todo list already created (Read first), read the story completely, including its labels and "
        "`linear issue relation list <ID>` for every blocker."
    )


def test_step_one_type_check_runs_after_the_roster_and_before_the_probe_and_every_voter() -> None:
    """B1: roster check, then the type check, then the preflight, then the voter launch."""
    roster = step_one_item_index("Validate the refinement roster before the tracker-write preflight")
    kind = step_one_item_index(TYPE_ITEM)
    probe = step_one_item_index("Run the tracker-write preflight before any voter launches")
    launch = step_one_item_index("Launch the three engineers in separate contexts")
    assert roster < kind < probe < launch


@pytest.mark.parametrize(
    "sentence",
    [
        "Run the type check after the roster check and before the tracker-write preflight, so a type stop posts no "
        "comment, and complete it before any voter launch.",
        "Resolve `profile.tracker.labels.user_story`, `profile.tracker.labels.bug`, "
        "`profile.tracker.labels.investigation` and `profile.tracker.labels.spike` after profile defaults; a key "
        "that is unset stops with `needs input` naming the key, in every ceremony, User Story ceremonies included.",
        "When the team of `STORY_ID` differs from `profile.tracker.team_key`, confirm those four labels on that team "
        "under the differing-team rule in Team resolution in [references/linear.md](references/linear.md) before "
        "naming the type.",
        "An issue carrying `profile.tracker.labels.user_story` is a User Story whatever other labels it has (the "
        "`linear-user-story` skill files maintenance defect stories as `user_story` plus `bug`): it runs the ceremony "
        "as a User Story with `type: estimated`, even when it also carries one or more of the three type labels.",
        "Otherwise, name the issue type from the labels read in item 1: `profile.tracker.labels.bug` names a Bug, "
        "`profile.tracker.labels.investigation` an Investigation and `profile.tracker.labels.spike` a Spike.",
        "An issue without `profile.tracker.labels.user_story` carrying two or more of the three type labels stops with "
        "`needs input` naming the labels; any other co-label, for example `profile.tracker.labels.rtb`, does not "
        "affect the type check.",
        "An issue with none of the three type labels, maintenance work included, runs the ceremony as a User Story "
        "with `type: estimated`.",
        "Record `type: <Bug|Investigation|Spike|estimated>` on the todo list; the type is final once written there, "
        "and for a Bug, an Investigation or a Spike the list omits every Stage 2 item, as the story-refinement seed "
        "line in [references/todo-tracking.md](references/todo-tracking.md) states.",
    ],
)
def test_step_one_type_check_states_the_rule(sentence: str) -> None:
    """B1: the type rule, each stop, the differing-team confirmation and the todo record."""
    assert sentence in type_item()


def test_step_one_stop_names_the_type_check_stops() -> None:
    """B1: both type stops are Step 1 stop conditions."""
    assert (
        "the type check stops on an unset type-label key or on conflicting type labels (two or more type labels on "
        "an issue without the user story label)" in bullet(operative_step(STEP_ONE), "Stop")
    )


# B8a: one row per documented path. Each row is the label set an issue carries, the type-label keys left unset
# after profile defaults, the documented result, and the Stage 2 decision ("skip", "run", or the stop).
TYPE_FIXTURES = [
    ("bug", {"bug"}, set(), "Bug", "skip"),
    ("investigation", {"investigation", "rtb"}, set(), "Investigation", "skip"),
    ("spike", {"spike"}, set(), "Spike", "skip"),
    ("user story", {"user_story", "feature"}, set(), "estimated", "run"),
    ("maintenance, rtb only", {"rtb"}, set(), "estimated", "run"),
    ("two type labels", {"bug", "investigation"}, set(), "needs input", "stop: names the labels"),
    ("user_story with a type label (maintenance defect)", {"user_story", "bug", "rtb"}, set(), "estimated", "run"),
    ("user_story with two type labels", {"user_story", "bug", "spike"}, set(), "estimated", "run"),
    ("unset type-label key", {"user_story"}, {"investigation"}, "needs input", "stop: names the key"),
    ("unset user_story key, no type label", {"feature"}, {"user_story"}, "needs input", "stop: names the key"),
]
TYPE_LABEL_KEYS = ("user_story", "bug", "investigation", "spike")
TYPE_NAMES = {"bug": "Bug", "investigation": "Investigation", "spike": "Spike"}


def documented_type(labels: set[str], unset: set[str]) -> tuple[str, str]:
    """The type check applied to one fixture row, with its keys, its label-to-type map and the Stage 2 skip
    list read from the skill text rather than restated here."""
    item = type_item()
    resolve = re.search(r"Resolve (.*?) after profile defaults", item)
    assert resolve, "the type item names the keys it resolves"
    keys = set(re.findall(r"`profile\.tracker\.labels\.(\w+)`", resolve.group(1)))
    assert keys == set(TYPE_LABEL_KEYS)
    names = dict(re.findall(r"`profile\.tracker\.labels\.(\w+)` (?:names )?an? (Bug|Investigation|Spike)\b", item))
    assert names == TYPE_NAMES
    lead = section(SKILL.read_text(), UNESTIMATED).split("- **Refinement only:**", 1)[1].split("skips Stage 2", 1)[0]
    skipped = set(re.findall(r"\b(Bug|Investigation|Spike)\b", lead))
    story = re.search(r"An issue carrying `profile\.tracker\.labels\.(\w+)` is a User Story whatever other labels", item)
    assert story, "the type item names the label that makes an issue a User Story"
    assert "carrying two or more of the three type labels stops with `needs input` naming the labels" in item
    if unset & keys:
        return "needs input", "stop: names the key"
    if story.group(1) in labels:
        return "estimated", "run"
    kinds = labels & set(names)
    if len(kinds) > 1:
        return "needs input", "stop: names the labels"
    if kinds:
        kind = names[kinds.pop()]
        return kind, "skip" if kind in skipped else "run"
    return "estimated", "run"


def test_step_one_mentions_stage_two_only_to_omit_it() -> None:
    """B1: Step 1 names Stage 2 only in the todo-list omission and removal sentences, never as a path to run."""
    lines = [spaced(line) for line in operative_step(STEP_ONE).splitlines() if "stage 2" in line.lower()]
    assert lines == [
        "Record `type: <Bug|Investigation|Spike|estimated>` on the todo list; the type is final once written there, "
        "and for a Bug, an Investigation or a Spike the list omits every Stage 2 item, as the story-refinement seed "
        "line in [references/todo-tracking.md](references/todo-tracking.md) states.",
        "When the type written is Bug, Investigation or Spike, remove from the list every Stage 2 item, whether the "
        "bootstrap list (its Step 3 and Step 4 items) or the Read first seed placed it there, in the same update that "
        "writes the type.",
    ]


def test_step_one_inputs_and_reconciliation_take_the_template_as_it_is() -> None:
    """B3: an Investigation template has no acceptance criteria and no Definition of Done, so neither is demanded."""
    step_one = spaced(operative_step(STEP_ONE))
    assert (
        "the Definition of Ready and Definition of Done template from the matching filing skill, where that template "
        "has them." in step_one
    )
    assert (
        "The facilitator reconciles the inputs into one refined story: story text, refined acceptance criteria where "
        "the filing template has them," in process_items(STEP_TWO)[0]
    )
    assert (
        "The refinement comment includes the complete refined story and ACs where the filing template has them, or"
        in process_items(STEP_TWO)[1]
    )
    assert (
        "- Refined story snapshot: <the complete refined story and ACs where the filing template has them, or an "
        "immutable link/commit>" in template("Refinement comment").splitlines()
    )


def test_readme_row_says_unestimated_types_are_never_pointed() -> None:
    row = next(line for line in (ROOT / "README.md").read_text().splitlines() if "[`story-refinement`]" in line)
    assert "a Bug, an Investigation or a Spike is refined and never pointed" in row


# The skill text that documents each fixture row's path: the Step 1 type item, then for an unestimated type the
# type's own content bullet in the issue-type section, which every one of the three types must have.
TYPE_FIXTURE_TEXT = {
    "Bug": ("`profile.tracker.labels.bug` names a Bug", "Bug (`linear-bug` template):"),
    "Investigation": (
        "`profile.tracker.labels.investigation` an Investigation",
        "Investigation (`linear-investigation` template):",
    ),
    "Spike": ("`profile.tracker.labels.spike` a Spike", "Spike (`linear-spike` template):"),
    "estimated": ("runs the ceremony as a User Story with `type: estimated`", None),
    "stop: names the labels": ("stops with `needs input` naming the labels", None),
    "stop: names the key": ("a key that is unset stops with `needs input` naming the key", None),
}


@pytest.mark.parametrize("name, labels, unset, result, stage_two", TYPE_FIXTURES, ids=[row[0] for row in TYPE_FIXTURES])
def test_type_fixture_table_maps_each_label_set_to_its_documented_path(
    name: str, labels: set[str], unset: set[str], result: str, stage_two: str
) -> None:
    """B8a: each label set reaches the documented type and Stage 2 decision, and the skill documents that path."""
    assert documented_type(labels, unset) == (result, stage_two), name
    key = result if result != "needs input" else stage_two
    item_text, content_text = TYPE_FIXTURE_TEXT[key]
    assert item_text in type_item(), name
    if content_text:
        assert "skips stage 2 entirely" in unestimated_bullet("Refinement only"), name
        assert f"- {content_text}" in section(SKILL.read_text(), UNESTIMATED), name


def test_type_fixture_table_covers_every_type_and_stop() -> None:
    """B8a: one Bug, Investigation, Spike and User Story row, one row per B1 stop, and rows for `user_story`
    together with one and with two type labels, each run as an estimated User Story."""
    outcomes = [(row[3], row[4]) for row in TYPE_FIXTURES]
    for expected in (
        ("Bug", "skip"),
        ("Investigation", "skip"),
        ("Spike", "skip"),
        ("needs input", "stop: names the labels"),
    ):
        assert outcomes.count(expected) == 1, expected
    assert outcomes.count(("needs input", "stop: names the key")) == 2
    assert outcomes.count(("estimated", "run")) == 4
    story_with_type = [row for row in TYPE_FIXTURES if "user_story" in row[1] and row[1] & set(TYPE_NAMES)]
    assert sorted(len(row[1] & set(TYPE_NAMES)) for row in story_with_type) == [1, 2]
    assert {(row[3], row[4]) for row in story_with_type} == {("estimated", "run")}


def test_unestimated_section_skips_stage_two_entirely() -> None:
    """B2: all of Stage 1 runs and every Stage 2 activity is skipped."""
    assert flat(
        "A Bug, an Investigation or a Spike runs all of Stage 1 (independent inputs, the refinement comment and the "
        "accept round) and skips Stage 2 entirely: no pointing launch, no point value, no SM/EM sizing context, no "
        "consensus check, no basis-challenge round, no discussion or re-vote, no estimate write, no pointing record, "
        "no anchoring check, and no estimate-triggered split under the [Split rule](#split-rule)."
    ) in unestimated_bullet("Refinement only")


def test_unestimated_section_names_the_pointing_skipped_line() -> None:
    """B2: the refinement comment carries the exact line."""
    assert f"The refinement comment carries the line `{POINTING_SKIPPED}`." in spaced(
        section(SKILL.read_text(), UNESTIMATED)
    ), "the line is pinned case-sensitively, as the record template copy is"


def test_unestimated_section_reads_not_accepted_never_unpointed() -> None:
    """B2: the two-round cap reads not accepted, and the round 2 result is the stop record."""
    assert flat(
        'After two accept rounds without three `ACCEPT`, the outcome reads "not accepted", never "unpointed": '
        "Step 2 item 7 authors no unpointed pointing record for these types, and the round 2 Accept round result "
        "comment is the stop record and carries the objecting voters' blocking amendments."
    ) in unestimated_bullet("Not accepted")


def test_unestimated_section_states_the_closing_outcome() -> None:
    """B2: the closing outcome on an accepted and on a not accepted outcome."""
    assert flat(
        'On an accepted outcome the closing message outcome reads "refined, not pointed (<type>)"; on a "not '
        'accepted" outcome it names that outcome and the two-round cap as the stop reason, never "unpointed".'
    ) in unestimated_bullet("Closing outcome")


@pytest.mark.parametrize(
    "sentence",
    [
        "Bug (`linear-bug` template): the symptom, the mechanism if known, the observed evidence, the expected "
        "behaviour, the fix scope, the acceptance criteria and the Definition of Done; a completed fix or verified "
        "root cause is not a prerequisite of refinement.",
        "Investigation (`linear-investigation` template): the incident reference, the question to answer, the "
        "findings scope, the remediation hand-off and the evidence to collect; the template has no acceptance "
        "criteria and no Definition of Done, so none is required, and completed findings or a root cause are not "
        "prerequisites of refinement.",
        "Spike (`linear-spike` template): the research questions, the success criteria, the deliverables, the "
        "timebox, refined in place of an estimate, and the Definition of Done.",
    ],
)
def test_unestimated_section_names_the_content_per_type(sentence: str) -> None:
    """B3: what the three voters refine for each type."""
    assert flat(sentence) in unestimated_bullet("Content per type")


def test_unestimated_section_dor_verdict_reads_template_has_none() -> None:
    """B3: the verdict covers only the template's boxes, and none of the three has any."""
    assert flat(
        "The voters' Definition of Ready verdict covers only the boxes the filing template has; none of the three "
        'templates has any, so the verdict reads "template has no Definition of Ready".'
    ) in unestimated_bullet("Definition of Ready verdict")


def test_unestimated_section_decides_priority_on_every_outcome() -> None:
    """B4: priority on an accepted and on a not accepted outcome, with the priority stop unchanged."""
    assert flat(
        "The PO decides and reads back a priority from at least one comparable prioritised story in the team of "
        '`STORY_ID`, as for a story, on an accepted and on a "not accepted" outcome alike, and posts the Triage '
        "record; the priority stop for a team with no comparable story applies unchanged."
    ) in unestimated_bullet("Priority")


@pytest.mark.parametrize(
    "sentence",
    [
        "A Bug, an Investigation or a Spike moves to `profile.tracker.states.ready` only when all three voters "
        "returned `ACCEPT`, no blocker remains, the priority is read back equal to the decided value, every "
        "Definition of Ready box its template has is ticked with evidence (none do, so this is vacuous), and the "
        "template's evidence sections are non-empty and no longer the filing template's placeholder text: Bug "
        "`Observed` and `Expected`, Investigation `Incident`, and Spike `Timebox` and `Research Questions`.",
        "A section still holds placeholder text when any bracketed template instruction that the filing template "
        "puts in that section remains in it verbatim, compared with each run of whitespace read as one space: each "
        "`[...]` instruction of the `linear-bug` or `linear-spike` template, whether on a line of its own like `[What "
        "should have happened instead.]`, wrapped across lines like the Bug `Observed` instruction, inline after the "
        "section label like `**Timebox:** [X days]`, or numbered like `1. [Key question to answer]`, and each of the "
        "`linear-investigation` template's own `<...>` tokens on its `Incident` line, such as `<Paging system>`; a "
        "section that is empty or still holds one fails this condition.",
        "Text the author wrote in brackets, such as a Markdown link, is not template placeholder text.",
        "Otherwise it stays in `profile.tracker.states.backlog` and the Triage record's `State:` line names the "
        'unmet condition; on a move to ready the line reads "ready: all conditions met".',
        "An issue already in `profile.tracker.states.ready` whose gate fails is moved back to "
        "`profile.tracker.states.backlog`, and its `State:` line names the unmet condition the same way.",
        "An issue already in `profile.tracker.states.in_progress` or a later state keeps its state and no state is "
        "written.",
        "When its gate fails, the Triage record's `State:` line reads its retained state with each unmet condition, "
        "and the ceremony reports `needs input` to the owner; when its gate passes, the line reads \"<retained "
        'state>: all conditions met".',
    ],
)
def test_unestimated_section_states_the_ready_gate(sentence: str) -> None:
    """B4: the end state and the State: line."""
    assert flat(sentence) in unestimated_bullet("Ready gate")


def filing_section(skill: str, start: str, end: str) -> str:
    """The text of one evidence section of a filing template, from its label up to the next label or rule."""
    template = section((ROOT / "skills" / skill / "SKILL.md").read_text(), "Template (the description)", keep_fences=True)
    body = template[template.index(start) + len(start):]
    return body[: body.index(end)]


# Each evidence section the ready gate names, the filing template's text that bounds it, and the bracket kind the
# gate's placeholder rule names for that template.
EVIDENCE_SECTIONS = [
    ("linear-bug", "**Observed**", "**Expected**", r"\[[^\]]+\]"),
    ("linear-bug", "**Expected**", "**Fix**", r"\[[^\]]+\]"),
    ("linear-investigation", "**Incident**", "---", r"<[^>]+>"),
    ("linear-spike", "**Timebox:**", "\n", r"\[[^\]]+\]"),
    ("linear-spike", "**📝 Research Questions**", "---", r"\[[^\]]+\]"),
]


@pytest.mark.parametrize("skill, start, end, kind", EVIDENCE_SECTIONS, ids=[f"{r[0]} {r[1]}" for r in EVIDENCE_SECTIONS])
def test_ready_gate_placeholder_rule_covers_every_evidence_section(skill: str, start: str, end: str, kind: str) -> None:
    """B4: every evidence section the gate names carries a filing placeholder of the bracket kind the rule detects,
    and every instruction in it is caught whatever its layout (own line, wrapped, inline after the label, numbered)."""
    body = filing_section(skill, start, end)
    spans = [" ".join(span.split()) for span in re.findall(kind, body)]
    assert spans, f"{skill} {start} has no placeholder the rule can detect"
    gate = spaced(section(SKILL.read_text(), UNESTIMATED))
    bracket = "`[...]` instruction of the `linear-bug` or `linear-spike` template" if kind.startswith(r"\[") else (
        "each of the `linear-investigation` template's own `<...>` tokens on its `Incident` line"
    )
    assert bracket in gate
    assert "remains in it verbatim, compared with each run of whitespace read as one space" in gate


def test_ready_gate_placeholder_examples_are_the_filing_templates_own() -> None:
    """B4: each layout example the gate quotes is the filing template's own text, so the examples cannot drift."""
    bug = (ROOT / "skills" / "linear-bug" / "SKILL.md").read_text()
    spike = (ROOT / "skills" / "linear-spike" / "SKILL.md").read_text()
    investigation = (ROOT / "skills" / "linear-investigation" / "SKILL.md").read_text()
    assert "\n[What should have happened instead.]\n" in bug
    assert "[Concrete evidence:" in filing_section("linear-bug", "**Observed**", "**Expected**")
    assert "\n" in filing_section("linear-bug", "**Observed**", "**Expected**").strip(), "the Observed text wraps"
    assert "\n**Timebox:** [X days]\n" in spike
    assert "\n1. [Key question to answer]\n" in spike
    assert "<Paging system>" in filing_section("linear-investigation", "**Incident**", "---")
    assert "<Paging system>" in investigation


def test_unestimated_section_has_no_estimate_write_instruction() -> None:
    """B2: no estimate write, so the section never tells the PO to set or clear an estimate."""
    text = spaced(section(SKILL.read_text(), UNESTIMATED)).lower()
    assert "no estimate write" in text
    for phrase in ("sets the estimate", "set the estimate", "removes it", "clears the estimate", "estimate to null"):
        assert phrase not in text, phrase


def placeholder_spans(skill: str, start: str, end: str, kind: str) -> list[str]:
    return [" ".join(span.split()) for span in re.findall(kind, filing_section(skill, start, end))]


def gate_admits(sections: dict[tuple[str, str], str]) -> bool:
    """The ready gate's evidence condition as the skill states it: each named section is non-empty and holds none
    of its filing template's own bracketed instructions verbatim, with each run of whitespace read as one space."""
    for skill, start, end, kind in EVIDENCE_SECTIONS:
        if (skill, start) not in sections:
            continue
        text = " ".join(sections[(skill, start)].split())
        if not text or any(span in text for span in placeholder_spans(skill, start, end, kind)):
            return False
    return True


BUG_OBSERVED = ("linear-bug", "**Observed**")
BUG_EXPECTED = ("linear-bug", "**Expected**")


@pytest.mark.parametrize(
    "name, observed, expected, admitted",
    [
        ("compliant Bug", "The export returns 500 for a 2 MB file.", "The export returns the file.", True),
        ("placeholder Bug", "The export returns 500.", "[What should have happened instead.]", False),
        ("empty Bug section", "The export returns 500.", "  \n ", False),
        (
            "author-written bracketed note",
            "The export returns 500, see [the log](https://example.invalid/log) [sic].",
            "The export returns the file.",
            True,
        ),
    ],
)
def test_ready_gate_admits_and_denies_bug_evidence(name: str, observed: str, expected: str, admitted: bool) -> None:
    """B4: a filled Bug passes, a placeholder or empty section fails, and an author's own brackets do not fail it."""
    assert "Text the author wrote in brackets, such as a Markdown link, is not template placeholder text." in spaced(
        section(SKILL.read_text(), UNESTIMATED)
    )
    assert gate_admits({BUG_OBSERVED: observed, BUG_EXPECTED: expected}) is admitted, name


def test_ready_gate_denies_the_wrapped_bug_observed_instruction() -> None:
    """B4: the Observed instruction wraps in the template; rewrapped in an issue it is still placeholder text."""
    (wrapped,) = placeholder_spans("linear-bug", "**Observed**", "**Expected**", r"\[[^\]]+\]")
    rewrapped = wrapped.replace(" ", "\n", 3)
    assert not gate_admits({BUG_OBSERVED: rewrapped, BUG_EXPECTED: "The export returns the file."})


@pytest.mark.parametrize(
    "path, sentence",
    [
        (
            "skills/story-refinement/SKILL.md",
            "For a Bug, an Investigation or a Spike, the brief also carries the type written on the todo list and that "
            "type's bullet under Content per type in [Unestimated issue types](#unestimated-issue-types).",
        ),
        (
            "skills/story-refinement/SKILL.md",
            "For a Bug, an Investigation or a Spike, per-AC gaps and refined AC deltas apply only where the filing "
            'template has acceptance criteria, and the Definition of Ready verdict reads "template has no Definition '
            'of Ready".',
        ),
        (
            "skills/story-refinement/SKILL.md",
            "For those types the stop ends Stage 1 only: the PO still decides and reads back the priority and posts "
            "the Triage record on this outcome, as [Unestimated issue types](#unestimated-issue-types) states, before "
            "the closing message.",
        ),
        ("skills/story-refinement/SKILL.md", "A Bug, an Investigation or a Spike is refined and never pointed."),
        (
            "skills/story-refinement/SKILL.md",
            "For those types, a stop after the refinement comment exists but before an accept round outcome (a voter "
            "is missing, or the tracker writes are denied without the fallback) posts only after the refinement "
            "comment and every Accept round result comment posted so far are read back.",
        ),
        (
            "shared/linear.md",
            "The estimate applies only to an estimated issue type: a Bug or an Investigation carries no estimate, and "
            "a Spike carries a timebox instead.",
        ),
    ],
)
def test_unestimated_types_reach_every_rule_that_assumes_a_pointed_story(path: str, sentence: str) -> None:
    """B2 and B3: the voter brief, output contract, accept round stop, description, metrics and triage rule each
    carve out a Bug, an Investigation and a Spike."""
    assert sentence in spaced((ROOT / path).read_text())


def test_type_item_states_user_story_precedence_before_the_stop_and_the_naming() -> None:
    """B1: the type item reads in rule order: user_story wins, then the two-label stop, then the type names."""
    item = type_item()
    story = item.index("is a User Story whatever other labels it has")
    stop = item.index("carrying two or more of the three type labels stops with `needs input`")
    naming = item.index("Otherwise, name the issue type")
    assert story < stop < naming


def test_pointing_record_template_is_never_posted_for_an_unestimated_type() -> None:
    assert "Never post it for a Bug, an Investigation or a Spike, which is never pointed." in spaced(
        prose(section(RECORD.read_text(), "Pointing record"))
    )


def test_unestimated_section_has_no_metrics_mention() -> None:
    assert "metric" not in section(SKILL.read_text(), UNESTIMATED).lower()


def test_overview_defers_to_the_issue_type_section() -> None:
    """B2: the overview names the unestimated reading."""
    overview = spaced(prose(section(SKILL.read_text(), "Story refinement", level=1, until=2)))
    assert (
        "A Bug, an Investigation or a Spike is unestimated: it runs Stage 1 only and is never pointed, as "
        f"{UNESTIMATED_LINK} states." in overview
    )


def test_read_first_todo_bullet_omits_stage_two_for_unestimated_types() -> None:
    """B2: the Read first todo-tracking bullet states the unestimated reading."""
    read_first = section(SKILL.read_text(), "Read first")
    lines = read_first.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("- [references/todo-tracking.md]"))
    end = next((i for i in range(start + 1, len(lines)) if not lines[i].startswith("  ")), len(lines))
    todo_bullet = spaced("\n".join(lines[start:end]))
    assert "For a Bug, an Investigation or a Spike the list omits every Stage 2 item, as that seed line states." in (
        todo_bullet
    )


def test_step_two_items_state_the_unestimated_reading() -> None:
    """B2: Step 2 items 4 and 7 state the not accepted reading."""
    assert (
        "For a Bug, an Investigation or a Spike the outcome is accepted, another round, or not accepted, never "
        "unpointed." in process_item(STEP_TWO, RESULT_ITEM)
    )
    assert (
        "For a Bug, an Investigation or a Spike the PO authors no unpointed record: the round 2 Accept round result "
        "comment is the stop record, its outcome reads not accepted, and it carries the objecting voters' blocking "
        "amendments." in process_item(STEP_TWO, "If all three voters have not returned `ACCEPT` after two rounds")
    )


def test_step_two_outputs_and_stop_state_the_unestimated_reading() -> None:
    """B2: the Outputs and Stop lines of Step 2."""
    body = operative_step(STEP_TWO)
    assert (
        'or a recorded unpointed result (for a bug, an investigation or a spike, a "not accepted" round 2 accept '
        'round result)' in bullet(body, "Outputs")
    )
    assert (
        'two accept rounds without all three `accept` (unpointed for a user story, "not accepted" for a bug, an '
        "investigation or a spike)" in bullet(body, "Stop")
    )


def test_stage_two_states_the_unestimated_skip() -> None:
    stage_two = spaced(section(SKILL.read_text(), "Stage 2: pointing"))
    assert stage_two.startswith(f"A Bug, an Investigation or a Spike skips this stage, as {UNESTIMATED_LINK} states.")


def test_records_states_the_unestimated_reading() -> None:
    assert (
        "For a Bug, an Investigation or a Spike, no pointing record is posted: the refinement comment carries the "
        '`Pointing skipped` line, a "not accepted" round 2 Accept round result comment is the stop record with the '
        "objecting voters' blocking amendments, and the Triage record carries the `State:` line, as "
        f"{UNESTIMATED_LINK} states." in spaced(section(SKILL.read_text(), "Records"))
    )


def test_triage_applies_the_unestimated_ready_gate() -> None:
    assert (
        "- For a Bug, an Investigation or a Spike, the PO also applies the ready gate and the `State:` line in "
        f"{UNESTIMATED_LINK}." in spaced(section(SKILL.read_text(), "Triage"))
    )


def test_metrics_order_covers_a_story_with_no_pointing_record() -> None:
    """B2: the summary posts after every Stage 1 record and the triage writes, on either outcome."""
    body = metrics_body()
    assert (
        "When no pointing record exists because the story is a Bug, an Investigation or a Spike, the comment is the "
        "invocation's last tracker write and posts only after the refinement comment, every Accept round result "
        'comment and the invocation\'s triage writes have been applied and read back, on an accepted and on a "not '
        'accepted" outcome alike.' in body
    )
    assert (
        'For a Bug, an Investigation or a Spike, this rule applies unchanged with "pointing record" read as '
        '"refinement comment".' in body
    )


def test_closing_message_states_the_unestimated_outcomes_and_type_stops() -> None:
    assert (
        'For a Bug, an Investigation or a Spike, an accepted outcome reads "refined, not pointed (<type>)", and a '
        '"not accepted" outcome names that outcome and the two-round cap as the stop reason, never unpointed, as '
        f"{UNESTIMATED_LINK} states; the stop reason also names each `needs input` of the Step 1 type check: an "
        "unset type-label key or conflicting type labels." in skill_section(CLOSING)
    )


def test_refinement_template_carries_the_pointing_skipped_line() -> None:
    """B7: the line sits in the Refinement comment template, scoped to the unestimated types."""
    assert f"- {POINTING_SKIPPED}" in template("Refinement comment").splitlines()
    assert (
        "For a Bug, an Investigation or a Spike, the comment carries the `Pointing skipped` line; for a User Story "
        "it omits that line." in spaced(prose(section(RECORD.read_text(), "Refinement comment")))
    )


SEED_UNESTIMATED = (
    "For a Bug, an Investigation and a Spike, the todo list omits each point value, the SM/EM sizing context, the "
    "consensus check, the basis-challenge round, the discussion and re-vote, the residual variance outcome or "
    "unpointed variance stop, each slice estimate, the pointing record and the anchoring check, and keeps the type "
    "check with the type recorded, the story read and its relations, the voter inputs, the reconciliation, each "
    "accept round, each split, priority, each PO write and read-back, the refinement record and, when metrics is "
    "on, the metrics items."
)


def test_todo_tracking_seed_states_the_unestimated_list() -> None:
    """B7: the seed line by exact substring in shared/todo-tracking.md."""
    seed = story_refinement_seed(ROOT)
    assert seed.endswith(
        "record invocation start (metrics on), collect metrics, and post the metrics summary on the story. "
        + SEED_UNESTIMATED
    ), "the unestimated clause directly follows the metrics clause and closes the seed line"
    assert seed.startswith("- **story-refinement:** read the story and its relations, the type check with the type "
                           "recorded, ")


UNESTIMATED_TYPE_NAME = re.compile(r"\b(Bug|Investigation|Spike)s?\b", re.IGNORECASE)


@pytest.mark.parametrize("heading", [STEP_THREE, STEP_FOUR])
def test_pointing_steps_carry_no_unestimated_type_path(heading: str) -> None:
    """B2: Stage 2 has no path for an unestimated type; the Stage 2 heading's skip sentence is its only rule."""
    assert not UNESTIMATED_TYPE_NAME.search(operative_step(heading)), heading


def test_priority_box_rules_apply_only_where_the_template_has_the_box() -> None:
    """B3/B4: the "Priority is clear" tick and untick are vacuous for the three unestimated templates."""
    assert (
        'Both "Priority is clear" rules apply only where the filing template has that Definition of Ready box; a '
        "Bug, an Investigation or a Spike template has none, so for those types no box is ticked or left unticked."
        in priority_bullet()
    )


SHARED_METRICS = ROOT / "shared" / "metrics.md"


def test_shared_metrics_outcome_names_the_unestimated_outcomes() -> None:
    """B2: the metrics summary Outcome has a value for each unestimated end state, never unpointed."""
    outcome = bullet(section(SHARED_METRICS.read_text(), "`story-refinement` extras", level=3), "Outcome")
    assert (
        'the recorded estimate; "refined, not pointed (<type>)" for an accepted bug, investigation or spike; "not '
        'accepted" with the two-round cap for a bug, an investigation or a spike; unpointed,' in outcome
    )


def test_shared_metrics_order_posts_after_the_unestimated_records() -> None:
    """B2: the shared order rule agrees with the SKILL.md Metrics Order sentence."""
    order = spaced(section(SHARED_METRICS.read_text(), "`story-refinement` order", level=3))
    assert (
        "- For a Bug, an Investigation or a Spike, which has no pointing record, the comment is posted after the "
        "refinement comment, every Accept round result comment and the triage writes are read back, on an accepted "
        'and on a "not accepted" outcome alike.' in order
    )


def test_engineering_workflow_triage_accepts_a_refined_unestimated_type() -> None:
    """B2: the implementation gate does not demand a pointing a Bug, an Investigation or a Spike never gets."""
    triage = spaced(section((ROOT / "skills" / "engineering-workflow" / "SKILL.md").read_text(), "1. Triage the story"))
    assert (
        "If the story is not refined and pointed, run `story-refinement` first; a Bug, an Investigation or a Spike "
        "is never pointed, so for one of those types refined is enough." in triage
    )
    assert (
        "for a Bug, an Investigation or a Spike it runs the refinement and the accept round only." in triage
    )


# --- SKL-239: the oversize split of a Bug or an Investigation and the multi-thread Spike re-file -----------------

SPLIT_ITEM = "For a Bug or an Investigation, after the accept round has accepted the refinement comment"
SCOPE_SIGNAL_LINE = "- Scope signal: <reading>"
SHARED_LINEAR_SPLIT = (
    "- ⛔ At refinement, without asking, split a Bug or an Investigation whose accepted refinement comment's `Scope "
    "signal:` line reads `more than one independently reviewable change`, with or without its `(<reason>)`: the "
    "original keeps the core slice and "
    "blocks each sibling, siblings come from its own filing template with its type label, no slice gets a point "
    "value or a slice estimate, and the split comment maps every acceptance criterion or findings-scope item to a "
    "slice; for these unestimated types that line, never an estimate, is the trigger."
)


@pytest.mark.parametrize(
    "sentence",
    [
        "For a Bug or an Investigation the refinement comment carries a `Scope signal:` line reading `single change` "
        "or `more than one independently reviewable change (<reason>)`, for example more than one root cause or more "
        "than one independently shippable fix.",
        "For a Spike the line reads `single research thread` or `more than one independent research thread "
        "(<reason>)`.",
    ],
)
def test_scope_signal_bullet_states_each_reading(sentence: str) -> None:
    """B5 and B6: the two readings per type, in the issue-type section's Scope signal bullet."""
    assert flat(sentence) in unestimated_bullet("Scope signal")


@pytest.mark.parametrize(
    "sentence",
    [
        "The reading `more than one independently reviewable change` on the accepted refinement comment of a Bug or "
        "an Investigation splits the issue on the same terms as a story under Estimation and slicing in "
        "[references/linear.md](references/linear.md), with these differences from the story split:",
        "the trigger is that line, not a point value;",
        "the split decision runs in Step 2 after the accept round and before the Triage record, not in Stage 2;",
        "siblings are created from the issue's own filing template (`linear-bug` or `linear-investigation`), never "
        "`linear-user-story`;",
        "each sibling carries the original's type label (`profile.tracker.labels.bug` or "
        "`profile.tracker.labels.investigation`), confirmed on that team under the differing-team rule in Team "
        "resolution in [references/linear.md](references/linear.md) when the team of `STORY_ID` differs from "
        "`profile.tracker.team_key`, and read back with that label;",
        "and no slice receives a point value or a slice estimate.",
        "The original stays the core slice, blocks each sibling, and every acceptance criterion (or, for an "
        "Investigation, every findings-scope item) is mapped to a slice in the split comment.",
        "A sibling that still needs more than one change is split again under this rule and never escalated.",
    ],
)
def test_oversize_split_states_the_trigger_and_each_difference(sentence: str) -> None:
    """B5: the trigger, the Step 2 placement, the sibling template and label, no slice estimate, and the re-split."""
    assert flat(sentence) in unestimated_bullet("Oversize split")


def test_oversize_split_lists_the_differences_in_order() -> None:
    """B5: the five differences read in the order the acceptance criterion gives them."""
    body = unestimated_bullet("Oversize split")
    marks = [
        "the trigger is that line",
        "the split decision runs in step 2",
        "siblings are created from the issue's own filing template",
        "each sibling carries the original's type label",
        "no slice receives a point value",
    ]
    assert [body.index(mark) for mark in marks] == sorted(body.index(mark) for mark in marks)


def test_step_two_runs_the_split_after_the_accept_round_and_before_the_triage_record() -> None:
    """B5: the split decision is a Step 2 item after the accept round items, and names the Triage record bound."""
    items = process_items(STEP_TWO)
    split = [i for i, item in enumerate(items) if item.startswith(SPLIT_ITEM)]
    assert len(split) == 1
    accept = [i for i, item in enumerate(items) if item.startswith("Run the accept round on that exact")]
    cap = [i for i, item in enumerate(items) if item.startswith("If all three voters have not returned `ACCEPT`")]
    assert accept[0] < cap[0] < split[0]
    item = items[split[0]]
    assert (
        "and before the PO posts the Triage record, the PO applies the oversize split in "
        f"{UNESTIMATED_LINK} when the accepted `Scope signal:` line reads `more than one independently reviewable "
        "change`" in item
    )
    assert (
        "for a Spike the accepted line reading `more than one independent research thread` takes the Spike re-file "
        "instead, and no split runs." in item
    )


def test_step_two_split_writes_follow_the_apply_rule() -> None:
    """B5: the split is PO-authored, applied by the facilitator only under the fallback."""
    assert (
        "The PO authors and applies the sibling issues, their relations and the split comment, or under the denied "
        "tracker writes fallback the facilitator applies them verbatim." in process_item(STEP_TWO, SPLIT_ITEM)
    )


def test_shared_linear_states_the_unestimated_split_trigger() -> None:
    """B5: one line in Estimation and slicing states the trigger for unestimated types, next to the story rule."""
    body = prose(section((ROOT / "shared" / "linear.md").read_text(), "Estimation and slicing"))
    lines = body.splitlines()
    assert SHARED_LINEAR_SPLIT in lines
    story = next((i for i, line in enumerate(lines) if line.startswith("- ⛔ Split a story whose estimate is above")), None)
    assert story is not None, "missing the story split rule in Estimation and slicing"
    assert lines.index(SHARED_LINEAR_SPLIT) > story


def test_vendored_linear_copies_carry_the_unestimated_split_trigger() -> None:
    copies = sorted(ROOT.glob("skills/*/references/linear.md"))
    assert copies
    for copy in copies:
        try:
            lines = prose(section(copy.read_text(), "Estimation and slicing")).splitlines()
        except AssertionError as error:
            raise AssertionError(f"{copy.relative_to(ROOT)}: {error}") from error
        assert SHARED_LINEAR_SPLIT in lines, copy.relative_to(ROOT)


def test_reviewer_output_contract_states_the_scope_signal_reading() -> None:
    assert (
        "for a bug, an investigation or a spike, the input also states its `scope signal:` reading, as "
        "[unestimated issue types](#unestimated-issue-types) defines it."
        in bullet(operative_step(STEP_ONE), "Reviewer output contract")
    )


@pytest.mark.parametrize(
    "sentence",
    [
        "The reading `more than one independent research thread` on the accepted refinement comment of a Spike does "
        "not split the Spike: it stays in `profile.tracker.states.backlog`, the Triage `State:` line reads \"re-file "
        "as separate Spikes (owner)\", and the Closing message outcome reads \"refined, not pointed (Spike); needs "
        "input: re-file as separate Spikes\" naming the story.",
    ],
)
def test_spike_refile_bullet_states_the_end_state(sentence: str) -> None:
    """B6: a multi-thread Spike is not split, stays in backlog, and names the re-file."""
    assert flat(sentence) in unestimated_bullet("Spike re-file")


def test_ready_gate_holds_a_multi_thread_spike() -> None:
    """B6: the ready gate requires a single research thread, so the re-file reading never reaches ready."""
    assert flat(
        "A Spike also needs its `Scope signal:` line to read `single research thread`; when it reads `more than one "
        "independent research thread` its unmet condition reads \"re-file as separate Spikes (owner)\", and when it is "
        "missing or carries neither of its type's readings its unmet condition reads \"scope signal missing\", as the "
        "Scope signal bullet states."
    ) in unestimated_bullet("Ready gate")


def test_spike_path_names_every_unestimated_type() -> None:
    """B6: the type list and the content section name all three types, the Spike refining its timebox."""
    assert "`profile.tracker.labels.spike` a Spike" in type_item()
    content = unestimated_bullet("Content per type")
    for name in ("bug (`linear-bug` template)", "investigation (`linear-investigation` template)",
                 "spike (`linear-spike` template)"):
        assert name in content, name
    assert "the timebox" in content.split("spike (`linear-spike` template)", 1)[1]


def test_closing_outcome_bullet_names_the_split_and_the_refile() -> None:
    """B7b: the closing outcome names the split and the slice count, and the Spike re-file."""
    assert flat(
        "When the oversize split splits a Bug or an Investigation, the accepted outcome reads \"refined, not pointed "
        "(<type>); split into <n> slices\", naming the split and the slice count; a Spike with the re-file reading "
        "closes as the Spike re-file bullet states."
    ) in unestimated_bullet("Closing outcome")


def test_closing_message_section_names_the_split_and_the_refile() -> None:
    assert (
        "When the oversize split splits a Bug or an Investigation, the outcome names the split and the slice count, "
        "and a Spike with the re-file reading closes with \"refined, not pointed (Spike); needs input: re-file as "
        f"separate Spikes\" naming the story, as {UNESTIMATED_LINK} states." in skill_section(CLOSING)
    )


def test_records_names_the_scope_signal_and_the_split_comment() -> None:
    assert (
        "For a Bug, an Investigation or a Spike, the refinement comment also carries the `Scope signal:` line, and "
        "an oversize split of a Bug or an Investigation posts the split comment that maps every acceptance criterion "
        "or findings-scope item to a slice." in spaced(section(SKILL.read_text(), "Records"))
    )


def test_refinement_template_carries_the_scope_signal_line() -> None:
    """B7b: the line sits in the Refinement comment template, right after the Pointing skipped line."""
    lines = template("Refinement comment").splitlines()
    assert SCOPE_SIGNAL_LINE in lines
    assert lines.index(SCOPE_SIGNAL_LINE) == lines.index(f"- {POINTING_SKIPPED}") + 1
    assert (
        "For a Bug, an Investigation or a Spike, the comment also carries the `Scope signal:` line with the reading "
        "`SKILL.md` (Unestimated issue types) defines; for a User Story it omits that line."
        in spaced(prose(section(RECORD.read_text(), "Refinement comment")))
    )
    assert (
        "Replace `<reading>` with one whole reading: for a Bug or an Investigation `single change` or `more than one "
        "independently reviewable change (<reason>)`, and for a Spike `single research thread` or `more than one "
        "independent research thread (<reason>)`, with `<reason>` replaced too; when the Step 2 reconciliation finds "
        "no category with two or more voters, replace it with `missing`, which `SKILL.md` treats as a missing line."
        in spaced(prose(section(RECORD.read_text(), "Refinement comment")))
    )


def test_voter_brief_carries_the_scope_signal_bullet() -> None:
    """Gate fix: each voter is told the readings it must choose between."""
    assert (
        f"For those types the brief also carries the Scope signal bullet in {UNESTIMATED_LINK}, so each voter states "
        "one of its type's two readings." in process_item(STEP_ONE, "Launch the three engineers")
    )


def test_reconciliation_carries_the_majority_scope_signal_reading() -> None:
    """Gate fix: the reconciled reading is the category two or more voters gave, carried verbatim into the comment."""
    item = process_item(STEP_TWO, "The facilitator reconciles")
    assert (
        "For a Bug, an Investigation or a Spike, the reconciled story also carries the `Scope signal:` category that "
        f"two or more voters gave, as the Scope signal bullet in {UNESTIMATED_LINK} defines a category; for a category "
        "that takes a reason, the reconciled reading is that category followed by `(<reason>)` holding each of those "
        "voters' reasons, joined with `; `." in item
    )
    assert (
        "A voter whose line carries neither of its type's readings counts toward no category; when no category has "
        "two or more voters, the reconciled reading is `missing`, which the Scope signal bullet treats as a missing "
        "line." in item
    )
    assert (
        "For a Bug, an Investigation or a Spike, the refinement comment carries the reconciled reading verbatim on "
        "its `Scope signal:` line." in process_item(STEP_TWO, "The PO authors the refinement comment")
    )


def test_missing_scope_signal_stops_with_needs_input() -> None:
    assert flat(
        "An accepted refinement comment whose `Scope signal:` line is missing or carries neither of its type's "
        "readings runs no split and no re-file: the issue fails the ready gate with the unmet condition \"scope "
        "signal missing\", and the closing message reports `needs input` naming the story and that gap."
    ) in unestimated_bullet("Scope signal")
    assert flat(
        "Each of the three types also needs a `Scope signal:` line carrying one of its type's readings, as the Scope "
        "signal bullet states."
    ) in unestimated_bullet("Ready gate")


@pytest.mark.parametrize(
    "sentence",
    [
        "Otherwise the [Split rule](#split-rule) applies as written: siblings in the team of `STORY_ID`, the "
        "differing-team confirmation of `profile.tracker.states.backlog` and each label, and the split comment; these "
        "differences override its `linear-user-story` template and its slice estimate round.",
        "Each sibling is assigned to `profile.tracker.assignee`, keeps the original's project and cycle, and its body "
        "fills its filing template with its slice's content from the accepted refinement comment, never the "
        "template's placeholder text.",
        "The split comment, from the Split comment template in [references/refinement-record.md]"
        "(references/refinement-record.md), names the accepted refinement comment id and gives each slice its own "
        "`Scope signal:` reading.",
        "That is a sibling whose reading in the split comment is `more than one independently reviewable change`; it "
        "is split at once, in the same invocation, and its split comment maps the sibling's own items.",
        "A run that finds a split comment already naming the accepted refinement comment id creates no sibling again.",
    ],
)
def test_oversize_split_states_the_mechanics_siblings_and_resplit_trigger(sentence: str) -> None:
    """Gate fix: Split rule mechanics with overrides, sibling content, the re-split trigger and idempotency."""
    assert flat(sentence) in unestimated_bullet("Oversize split")


def test_spike_refile_keeps_a_retained_state() -> None:
    assert flat(
        "A Spike already in `profile.tracker.states.in_progress` or a later state keeps its state under the Ready gate "
        "bullet, and its `State:` line names the re-file as its unmet condition."
    ) in unestimated_bullet("Spike re-file")


def test_closing_outcome_defines_the_slice_count() -> None:
    assert flat("`<n>` counts the original and every sibling, re-split siblings included.") in unestimated_bullet(
        "Closing outcome"
    )


def test_step_two_outputs_name_the_split() -> None:
    body = operative_step(STEP_TWO)
    outputs = spaced(re.search(r"^- \*\*Outputs:\*\*(.*?)(?=^- \*\*)", body, re.MULTILINE | re.DOTALL).group(1))
    assert outputs.endswith("when the oversize split ran, also the split comment id and each sibling identifier.")


def test_metrics_order_waits_for_the_split() -> None:
    assert (
        "When the oversize split ran, the comment also posts only after the split comment, each sibling issue it "
        "created and each sibling's Triage record have been applied and read back." in skill_section("Metrics")
    )


def test_description_names_the_unestimated_split_and_refile() -> None:
    assert (
        "split an oversized story, Bug or Investigation, flag a multi-thread Spike for re-filing"
        in spaced(SKILL.read_text().split("---", 2)[1])
    )


def test_split_comment_template_has_the_fields() -> None:
    assert template("Split comment").splitlines() == [
        "## Split record",
        "",
        "- Refinement comment split: <accepted refinement comment id; for a re-split sibling, the parent split "
        "comment id and the sibling key>",
        "- Core slice: <original issue key> - <its slice> - Scope signal: <reading> - description trimmed to this "
        "slice",
        "- Siblings, each from the `<linear-bug|linear-investigation>` template with the `<type label>` label, "
        "blocked by the original:",
        "  - <sibling key> - <its slice> - Scope signal: <reading>",
        "- Mapping: <each acceptance criterion, or for an Investigation each findings-scope item, and the slice it "
        "maps to>",
        "- Estimates: none; no slice receives a point value or a slice estimate",
        "- Tracker writes: product owner",
    ]
    assert "Use the Split comment template in the same file for the oversize split of a Bug or an Investigation." in (
        skill_section("Records")
    )


def test_triage_state_template_keeps_the_plain_ready_wording() -> None:
    state = next(line for line in template("Triage record").splitlines() if line.startswith("- State:"))
    assert "ready: all conditions met" in state


def test_scope_signal_matches_a_reading_by_its_category() -> None:
    """Re-verify fix: a reading with its `(<reason>)` matches every rule that names the bare category."""
    body = unestimated_bullet("Scope signal")
    assert flat(
        "A reading's category is its text before ` (<reason>)`: `single change`, `more than one independently "
        "reviewable change`, `single research thread` or `more than one independent research thread`."
    ) in body
    assert flat(
        "Every rule in this skill that names a reading, Step 2 included, matches the line's category, so `more than "
        "one independently reviewable change (two root causes)` reads `more than one independently reviewable "
        "change`."
    ) in body


def test_scope_signal_field_name_keeps_its_case() -> None:
    """Re-verify fix: flat() lowercases, so pin the literal `Scope signal:` field name case-sensitively."""
    raw = spaced(section(SKILL.read_text(), "Unestimated issue types"))
    assert "`Scope signal:`" in raw
    assert "`scope signal:`" not in raw
    assert SCOPE_SIGNAL_LINE in template("Refinement comment").splitlines()


@pytest.mark.parametrize(
    "sentence",
    [
        "Each sibling is filed under the rules of its filing skill (`linear-bug` or `linear-investigation`), its "
        "duplicate search included; the differences above take precedence where they conflict.",
        "The PO trims the original's description to its core slice, and the split comment's `Core slice:` line "
        "records the trim; the accepted refinement comment stays the full immutable snapshot.",
        "A re-split sibling's split comment names, on its `Refinement comment split:` line, the parent split comment "
        "id and the sibling key, and a run that finds a split comment already naming that pair creates no sibling "
        "again.",
    ],
)
def test_oversize_split_files_siblings_trims_the_original_and_keys_resplits(sentence: str) -> None:
    assert flat(sentence) in unestimated_bullet("Oversize split")


def test_closing_message_names_a_missing_scope_signal() -> None:
    assert (
        "For a Bug, an Investigation or a Spike whose `Scope signal:` line is missing or carries neither of its type's "
        "readings, it also names that `needs input`, naming the story and the gap, as the Scope signal bullet in "
        f"{UNESTIMATED_LINK} states." in skill_section(CLOSING)
    )


@pytest.mark.parametrize(
    "sentence",
    [
        "Post this on the original issue when the oversize split in `SKILL.md` (Unestimated issue types) splits a Bug "
        "or an Investigation, authored by the product owner and posted by the product owner or, under the denied "
        "tracker writes fallback, by the facilitator verbatim.",
        "A re-split sibling gets its own split comment on that sibling.",
    ],
)
def test_split_comment_section_states_its_author(sentence: str) -> None:
    assert sentence in spaced(prose(section(RECORD.read_text(), "Split comment")))


def test_split_comment_carries_the_facilitator_writes_alternative() -> None:
    intro, block = fallback_alternative("Split comment")
    assert "Under the denied tracker writes fallback in `SKILL.md`, replace the tracker-writes line with:" in intro.splitlines()
    assert WRITES_FACILITATOR_LINE in block.splitlines()


SECTION_FIXTURE = (
    "# Title\n\nintro\n"
    "## A\n\n<!--\n```markdown\n## Hidden\n- gone\n```\n-->\n```markdown\n## Kept\n- here\n```\n"
    "````\n## Four\n`````\n~~~markdown\n## Tilde\n```\n## Mixed\n~~~\n- item\n  ```text\n  ## Indented\n  ```\n"
    "   ```\n## Three\n   ```\n```inline``` span\n## Not fenced\nafter\n"
    "### Step\n\nstep text\n<!-- ### Commented step -->\n```\n### Fenced step\n```\nstep tail\n### Next step\nother\n"
    "    ```\n### Open step\nopen tail\n## B\nnext\n"
)


def test_section_drops_comments_and_skips_every_fence_kind() -> None:
    """B8b: commented-out text is not operative, and no fenced heading starts or ends a section, at any level.

    Covered: a commented-out fence, backtick fences of three and four (closed by a longer run), a tilde fence that a
    backtick line does not close, fences indented two and three spaces, a four-space indent that opens no fence, a
    line starting with an inline code span that opens no fence, and an unclosed fence or HTML comment.
    """
    assert "intro" in section(SECTION_FIXTURE, "Title", level=1, until=2)
    assert "here" not in section(SECTION_FIXTURE, "Title", level=1, until=2)
    body = section(SECTION_FIXTURE, "A")
    assert "- item" in body and "inline" in body and "after" not in body
    assert "gone" not in body and "here" not in body and "Four" not in body and "Three" not in body
    kept = section(SECTION_FIXTURE, "A", keep_fences=True)
    assert "gone" not in kept and "- here" in kept and "## Indented" in kept
    for fenced in ("Hidden", "Kept", "Four", "Tilde", "Mixed", "Indented", "Three"):
        with pytest.raises(AssertionError, match="missing section"):
            section(SECTION_FIXTURE, fenced)
    assert "after" in section(SECTION_FIXTURE, "Not fenced")
    step_body = section(SECTION_FIXTURE, "Step", level=3)
    assert "step text" in step_body and "step tail" in step_body and "other" not in step_body
    assert "Fenced step" not in step_body
    assert "Fenced step" in section(SECTION_FIXTURE, "Step", level=3, keep_fences=True)
    with pytest.raises(AssertionError, match="missing section"):
        section(SECTION_FIXTURE, "Commented step", level=3)
    assert "open tail" in section(SECTION_FIXTURE, "Open step", level=3)
    with pytest.raises(AssertionError, match=r"unclosed code fence \(block 0\) \(looking for A\)"):
        section("## A\n```\n## B\n", "A")
    with pytest.raises(AssertionError, match="unclosed HTML comment"):
        section("## A\n<!--\nrule\n## B\n", "A")


NESTED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def own_nodes(node: ast.AST):
    """`node` and every node under it, without descending into a nested function, lambda or class, whose code the
    helper itself never runs."""
    yield node
    for child in ast.iter_child_nodes(node):
        if not isinstance(child, NESTED_SCOPES):
            yield from own_nodes(child)


def called_name(node: ast.AST) -> str | None:
    return node.func.id if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) else None


def parsed(function) -> ast.FunctionDef:
    return ast.parse(textwrap.dedent(inspect.getsource(function))).body[0]


def scope_violations(definition: ast.FunctionDef, namespace: dict, text_positions: dict[str, set[str]]) -> list[str]:
    """Why the helper's result may hold text that no call to a scoped function produced; empty when there is none.

    `definition` is the helper's syntax tree and `namespace` its module globals. `text_positions` maps each scoped
    function to the parameters that take the text it scopes. The helper passes when:
    it defines no nested function, lambda or class; every local name is bound (assigned, augmented or iterated) only
    from expressions that carry scoped text and mention no other local, so rebinding a name to unscoped text unscopes
    it on every path; its own text parameters (those that appear anywhere in a text argument of a scoped call) and any
    multi-line module string appear only inside the arguments of scoped calls; and every return carries scoped text.

    An expression carries scoped text when every value it can take does: a scoped call or scoped local, an index or
    slice of one, both branches of a conditional, every operand of an operator or boolean, every item of a tuple, list
    or set, the element of a comprehension, and a method of one. Another call is taken to transform its argument, so
    it carries scoped text when one of its positional arguments does; what a call really returns is checked at run
    time by `test_every_scoping_helper_returns_only_section_text`.
    """
    nodes = list(own_nodes(definition))
    violations = [
        f"line {node.lineno}: nested {type(node).__name__}"
        for node in ast.walk(definition)
        if node is not definition and isinstance(node, NESTED_SCOPES)
    ]
    parameters = parameter_names(definition)
    inside_scoped = {
        id(inner)
        for call in nodes
        if called_name(call) in text_positions
        for argument in [*call.args, *(keyword.value for keyword in call.keywords)]
        for inner in ast.walk(argument)
    }
    text_names = text_parameters(definition, namespace, text_positions) | {
        name for name, value in namespace.items() if isinstance(value, str) and "\n" in value
    }
    violations += [
        f"line {node.lineno}: {node.id} used outside a scoped call"
        for node in nodes
        if isinstance(node, ast.Name) and node.id in text_names and id(node) not in inside_scoped
    ]

    bindings: dict[str, list[ast.AST]] = {}
    bound_targets: set[int] = set()

    def bind(target: ast.AST, source: ast.AST) -> None:
        for node in ast.walk(target):
            bound_targets.add(id(node))
            if isinstance(node, ast.Name):
                bindings.setdefault(node.id, []).append(source)

    for node in nodes:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                bind(target, node.value)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            bind(node.target, node.value)
        elif isinstance(node, ast.AugAssign):
            current = ast.Name(id=node.target.id, ctx=ast.Load()) if isinstance(node.target, ast.Name) else node.target
            bind(node.target, ast.BinOp(left=current, op=node.op, right=node.value))
        elif isinstance(node, (ast.For, ast.comprehension)):
            bind(node.target, node.iter)
    other = {
        node.id
        for node in nodes
        if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load) and id(node) not in bound_targets
    } | {node.name for node in nodes if isinstance(node, ast.ExceptHandler) and node.name} | {
        (alias.asname or alias.name).split(".")[0]
        for node in nodes
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    local_names = set(bindings) | other | parameters

    def carries(expression: ast.AST, scoped_locals: set[str]) -> bool:
        """Whether every value the expression can evaluate to comes from a scoped call or a scoped local."""
        if called_name(expression) in text_positions:
            return True
        match expression:
            case ast.Name(id=name):
                return name in scoped_locals
            case ast.Subscript(value=value) | ast.Starred(value=value):
                return carries(value, scoped_locals)
            case ast.IfExp(body=body, orelse=orelse):
                return carries(body, scoped_locals) and carries(orelse, scoped_locals)
            case ast.BoolOp(values=values) | ast.Tuple(elts=values) | ast.List(elts=values) | ast.Set(elts=values):
                return bool(values) and all(carries(value, scoped_locals) for value in values)
            case ast.BinOp(left=left, right=right):
                return carries(left, scoped_locals) and carries(right, scoped_locals)
            case ast.ListComp(elt=element) | ast.SetComp(elt=element) | ast.GeneratorExp(elt=element):
                return carries(element, scoped_locals)
            case ast.Call(func=ast.Attribute(value=receiver)) if carries(receiver, scoped_locals):
                return True
            case ast.Call(args=arguments):
                return any(carries(argument, scoped_locals) for argument in arguments)
        return False

    def clean(expression: ast.AST, scoped_locals: set[str]) -> bool:
        holds = carries(expression, scoped_locals)
        foreign = any(
            isinstance(node, ast.Name)
            and node.id in local_names - parameters - scoped_locals
            and id(node) not in inside_scoped
            for node in own_nodes(expression)
        )
        return holds and not foreign

    scoped_locals = set(bindings) - other - parameters
    while True:
        unscoped = {name for name in scoped_locals if not all(clean(source, scoped_locals) for source in bindings[name])}
        if not unscoped:
            break
        scoped_locals -= unscoped
    violations += [f"{name} is bound from text no scoped call produced" for name in sorted(local_names - parameters - scoped_locals)]
    returns = [node for node in nodes if isinstance(node, ast.Return)]
    violations += [] if returns else ["no return"]
    violations += [
        f"line {node.lineno}: {ast.unparse(node)}"
        for node in returns
        if node.value is None or not clean(node.value, scoped_locals)
    ]
    return violations


def parameter_names(definition: ast.AST) -> set[str]:
    return {argument.arg for argument in ast.walk(definition.args) if isinstance(argument, ast.arg)}


def text_parameters(definition: ast.FunctionDef, namespace: dict, text_positions: dict[str, set[str]]) -> set[str]:
    """The helper's parameters it passes into a text parameter of a scoped call, by position or by keyword."""
    parameters = parameter_names(definition)
    found: set[str] = set()
    for call in own_nodes(definition):
        if called_name(call) in text_positions:
            names = list(inspect.signature(namespace[call.func.id]).parameters)
            wanted = text_positions[call.func.id]
            arguments = [argument for index, argument in enumerate(call.args) if index < len(names) and names[index] in wanted]
            arguments += [keyword.value for keyword in call.keywords if keyword.arg in wanted]
            found |= {
                node.id
                for argument in arguments
                for node in ast.walk(argument)
                if isinstance(node, ast.Name) and node.id in parameters
            }
    return found


def unscoped_reads(function, scoped: set[str]) -> list[str]:
    """Each `.read_text()` call in the helper that is not passed straight to a scoped function."""
    definition = ast.parse(textwrap.dedent(inspect.getsource(function))).body[0]
    passed = {
        id(argument)
        for node in own_nodes(definition)
        if called_name(node) in scoped
        for argument in node.args
    }
    return [
        ast.unparse(node)
        for node in own_nodes(definition)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "read_text"
        and id(node) not in passed
    ]


SCOPING_HELPERS = (
    step, operative_step, process_items, process_item, template_block, template, fallback_alternative,
    pointing_template, record_triage_section, unestimated_bullet, type_item, skill_section,
)


def test_every_scoping_helper_goes_through_section() -> None:
    """B8b: every value each helper behind a listed assertion returns is derived from section(), directly or through
    another such helper, and the helper reads no file except straight into one of them."""
    text_positions = {"section": {"text"}}
    pending = {helper.__name__: helper for helper in SCOPING_HELPERS}
    while pending:
        found = {name: scope_violations(parsed(helper), helper.__globals__, text_positions) for name, helper in pending.items()}
        reached = [name for name, violations in found.items() if not violations]
        assert reached, found
        for name in reached:
            text_positions[name] = text_parameters(parsed(pending[name]), pending[name].__globals__, text_positions)
            del pending[name]
    for helper in SCOPING_HELPERS:
        reads = unscoped_reads(helper, set(text_positions))
        assert not reads, f"{helper.__name__} reads a file outside section(): {reads}"


@pytest.mark.parametrize(
    "body",
    [
        "    result = section(text, heading, level=3)\n    result = text\n    return result\n",
        "    body = section(text, heading, level=3)\n    return body + text\n",
        "    body = section(text, heading, level=3)\n    body = text[text.index(heading):]\n    return body\n",
        "    body = section(text, heading, level=3)\n    body += text\n    return body\n",
        "    parts = [section(text, heading, level=3)]\n    parts.append(text)\n    return ''.join(parts)\n",
        "    if heading:\n        return section(text, heading, level=3)\n    return text\n",
        "    section(text, heading, level=3)\n    return text\n",
        "    return (lambda: section(text, heading, level=3))() and text\n",
        "    return section(text + '', heading, level=3) + text\n",
        "    return section(text.strip(), heading, level=3) + text\n",
        "    return section(text, heading, level=3) if False else 'whole document'\n",
        "    return section(text, heading, level=3) if heading else 'whole document'\n",
        "    body = section(text, heading, level=3)\n    return body or 'whole document'\n",
        "    body = section(text, heading, level=3)\n    return body + 'whole document'\n",
        "    return 'whole document'\n",
    ],
)
def test_scope_guard_rejects_unscoped_text(body: str) -> None:
    """B8b: the helper guard fails a helper that scopes its text and then returns, mixes in or rebinds to the whole
    text on any path."""
    definition = ast.parse(f"def step(text: str, heading: str) -> str:\n{body}").body[0]
    assert scope_violations(definition, globals(), {"section": {"text"}}), body
    clean = ast.parse("def step(text: str, heading: str) -> str:\n    return section(text, heading, level=3)\n").body[0]
    assert not scope_violations(clean, globals(), {"section": {"text"}})


SEGMENT_KINDS = ("prose", "fence")


def result_strings(value) -> list[str]:
    """Every string in a helper's result, through tuples and lists; a `segments()` part's kind label is not text."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, tuple) and len(value) == 3 and value[0] in SEGMENT_KINDS:
        value = value[1:]
    if isinstance(value, (tuple, list)):
        return [text for item in value for text in result_strings(item)]
    raise AssertionError(f"unexpected {type(value).__name__} in a helper result")


def unscoped_output(function, arguments: tuple) -> list[str]:
    """Each string the helper returns that is not part of a text `section()` returned during the call; a helper that
    never calls `section()` returns nothing scoped.

    Whitespace is collapsed on both sides and case is kept, so a helper cannot recase a line into one an exact-case
    assertion wants. A lowercased string counts only when `flat()` itself produced it, during the call, from text that
    is part of a returned section, as `bullet()` does.
    """
    namespace = function.__globals__
    real_section, real_flat = namespace["section"], namespace["flat"]
    returned: list[str] = []
    flattened: list[str] = []

    def collapsed(text: str) -> str:
        return " ".join(text.split())

    def within(text: str) -> bool:
        return any(collapsed(text) in collapsed(body) for body in returned) or any(
            text in output for output in flattened
        )

    def recording_section(*args, **kwargs):
        result = real_section(*args, **kwargs)
        returned.append(result)
        return result

    def recording_flat(text):
        result = real_flat(text)
        if any(collapsed(text) in collapsed(body) for body in returned):
            flattened.append(result)
        return result

    namespace["section"], namespace["flat"] = recording_section, recording_flat
    try:
        result = function(*arguments)
    finally:
        namespace["section"], namespace["flat"] = real_section, real_flat
    if not returned:
        return ["<no section() call>"]
    return [text for text in result_strings(result) if not within(text)]


def parametrized_bindings(function: ast.FunctionDef) -> list[dict]:
    """Each set of parameter values a test's `pytest.mark.parametrize` decorators bind, or one empty set."""
    bindings: list[dict] = [{}]
    for decorator in function.decorator_list:
        if not (isinstance(decorator, ast.Call) and ast.unparse(decorator.func) == "pytest.mark.parametrize"):
            continue
        declared = ast.literal_eval(decorator.args[0])
        names = [name.strip() for name in (declared.split(",") if isinstance(declared, str) else declared)]
        values = eval(compile(ast.Expression(decorator.args[1]), "<parametrize>", "eval"), globals())
        rows = [dict(zip(names, value if len(names) > 1 else (value,))) for value in values]
        bindings = [{**bound, **row} for bound in bindings for row in rows]
    return bindings


def helper_call_sites() -> tuple[dict[str, list[tuple]], list[str]]:
    """The argument tuples of every call to a scoping helper in this file, resolved at module level and through the
    calling test's parametrized values, and each call outside a scoping helper whose arguments do not resolve."""
    names = {helper.__name__ for helper in SCOPING_HELPERS}
    sites: dict[str, list[tuple]] = {name: [] for name in names}
    unresolved: list[str] = []
    tree = ast.parse(Path(__file__).read_text())
    for function in tree.body:
        if not isinstance(function, ast.FunctionDef):
            continue
        for node in ast.walk(function):
            if called_name(node) not in names:
                continue
            for bound in parametrized_bindings(function):
                try:
                    arguments = tuple(
                        eval(compile(ast.Expression(argument), "<site>", "eval"), {**globals(), **bound})
                        for argument in node.args
                    )
                except NameError:
                    if function.name not in names:
                        unresolved.append(f"line {node.lineno}: {ast.unparse(node)}")
                    continue
                if node.keywords:
                    unresolved.append(f"line {node.lineno}: {ast.unparse(node)}")
                elif arguments not in sites[node.func.id]:
                    sites[node.func.id].append(arguments)
    return sites, unresolved


def test_every_scoping_helper_returns_only_section_text() -> None:
    """B8b: at every call site in this file, each string a helper behind a listed assertion returns is part of the
    text `section()` returned during that call, so no call, branch or literal can hand an assertion unscoped text."""
    sites, unresolved = helper_call_sites()
    assert not unresolved, f"helper calls whose arguments the check cannot resolve: {unresolved}"
    inner ={called_name(node) for helper in SCOPING_HELPERS for node in own_nodes(parsed(helper))}
    unchecked = sorted(name for name, found in sites.items() if not found and name not in inner)
    assert not unchecked, f"helpers with no call site to check, nor called by a checked helper: {unchecked}"
    found = {
        f"{helper.__name__}{arguments!r}"[:120]: unscoped
        for helper in SCOPING_HELPERS
        for arguments in sites[helper.__name__]
        if (unscoped := unscoped_output(helper, arguments))
    }
    assert not found, found


@pytest.mark.parametrize(
    "body",
    [
        "    return section(text, heading, level=3).join(['whole document'])\n",
        "    return ''.join(dict.fromkeys(['whole document'], section(text, heading, level=3)))\n",
        "    body = section(text, heading, level=3)\n    return body.replace(body, text)\n",
        "    return section(text, heading, level=3).replace('Process', 'PROCESS')\n",
        "    return spaced(section(text, heading, level=3)).lower()\n",
        "    section(text, heading, level=3)\n    return flat(text)\n",
        "    section(text, heading, level=3)\n    return text\n",
        "    return 'whole document'\n",
    ],
)
def test_section_text_check_rejects_unscoped_output(body: str) -> None:
    """B8b: the run-time check fails a helper whose result is not text `section()` returned, whatever call made it."""
    namespace = dict(globals())
    exec(compile(f"def probe(text, heading):\n{body}", "<probe>", "exec"), namespace)
    arguments = (SKILL.read_text(), "Step 1: Independent refinement")
    assert unscoped_output(namespace["probe"], arguments), body
    for control in ("section(text, heading, level=3)", "flat(section(text, heading, level=3))"):
        exec(compile(f"def probe(text, heading):\n    return {control}\n", "<probe>", "exec"), namespace)
        assert not unscoped_output(namespace["probe"], arguments), control


def test_no_assertion_slices_a_file_on_a_heading_or_fence() -> None:
    """B8b: no test scopes text by splitting it on a heading or a code fence; section() does that scoping."""
    tree = ast.parse(Path(__file__).read_text())
    found = [
        f"line {node.lineno}: {ast.unparse(node)}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"split", "rsplit", "partition", "rpartition", "index", "find"}
        and any(
            isinstance(literal, ast.Constant)
            and isinstance(literal.value, str)
            and re.search(r"^\s*(?:#|```|~~~)", literal.value, re.MULTILINE)
            for literal in [*node.args[:1], *(keyword.value for keyword in node.keywords if keyword.arg == "sep")]
        )
    ]
    assert not found, found


FENCE_READERS = {"template_block", "pointing_template", "filing_section", "test_section_drops_comments_and_skips_every_fence_kind"}


def test_only_template_readers_keep_fenced_text() -> None:
    """B8b: section() drops fenced blocks, so a rule moved into a code fence is not operative; only the readers of a
    record or filing template, and the fixture test, ask for fenced text."""
    tree = ast.parse(Path(__file__).read_text())
    readers = {
        function.name
        for function in ast.walk(tree)
        if isinstance(function, ast.FunctionDef)
        for node in own_nodes(function)
        if isinstance(node, ast.keyword) and node.arg == "keep_fences"
    }
    assert readers == FENCE_READERS, f"keep_fences used by {sorted(readers)}"


def test_readme_row_names_the_split_and_the_refile() -> None:
    row = next(line for line in (ROOT / "README.md").read_text().splitlines() if "skills/story-refinement/SKILL.md" in line)
    assert (
        "an oversized Bug or Investigation is split without an estimate, and a multi-thread Spike is flagged for "
        "re-filing" in row
    )
