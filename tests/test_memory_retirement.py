"""Guards for the persistent-memory retirement rule (SKL-218).

The rule lives once in shared/engineering-practice.md; shared/runtimes.md carries one
"Persistent memory" row that names each runtime's store and cross-references the rule.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRACTICE = ROOT / "shared" / "engineering-practice.md"
RUNTIMES = ROOT / "shared" / "runtimes.md"
SECTION_TITLE = "Retire superseded memory"
TABLE_HEADER = "| Capability | Claude Code | OpenCode (version-qualified) |"
FENCE = re.compile(r"^```.*?^```[^\n]*$", re.MULTILINE | re.DOTALL)


def headings(text: str) -> list[tuple[str, int]]:
    """Return (title, offset) of each level-2 heading outside fenced code blocks."""
    unfenced = FENCE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    return [(m.group(1).strip(), m.start()) for m in re.finditer(r"^## (.+)$", unfenced, re.MULTILINE)]


def retire_section() -> str:
    text = PRACTICE.read_text()
    found = headings(text)
    starts = [i for i, (title, _) in enumerate(found) if title == SECTION_TITLE]
    assert len(starts) == 1, f"expected one '## {SECTION_TITLE}' heading outside code fences"
    index = starts[0]
    end = found[index + 1][1] if index + 1 < len(found) else len(text)
    return text[found[index][1]:end]


def bullet(body: str, marker: str) -> str:
    """Return the one top-level bullet (with its continuation lines) that contains marker."""
    items = re.split(r"\n(?=- )", body)
    hits = [item for item in items if marker in item]
    assert len(hits) == 1, f"expected one bullet containing {marker!r}, got {len(hits)}"
    return hits[0]


def memory_cells() -> tuple[str, str, str]:
    """Return the three cells of the "Persistent memory" row of the capability table."""
    lines = RUNTIMES.read_text().splitlines()
    assert lines.count(TABLE_HEADER) == 1, "expected one capability table header"
    start = lines.index(TABLE_HEADER) + 2
    table = []
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        table.append(line)
    rows = []
    for line in table:
        cells = line.split("|")
        assert cells[0] == "" and cells[-1] == "", f"row must open and close with a pipe: {line[:40]}"
        assert len(cells) == 5, f"row must have three cells: {line[:40]}"
        capability = cells[1].strip()
        if capability == "Persistent memory" or capability.startswith("Persistent memory ("):
            rows.append(tuple(cell.strip() for cell in cells[1:4]))
    assert len(rows) == 1, f"expected one persistent-memory row in the capability table, got {len(rows)}"
    return rows[0]


def test_the_scope_line_covers_changing_a_skill_capability_file_or_overlay() -> None:
    scope = PRACTICE.read_text().split("\n## ", 1)[0]
    assert "or when changing a skill, capability file, or consumer overlay" in scope


def test_the_section_retires_the_note_by_delete_or_pointer_and_keeps_other_rules() -> None:
    body = retire_section()
    for phrase in (
        "first saves the rule in its new home, then retires the matching memory note in the same session",
        "deleting it together with its index entry where the store has one",
        "reducing it to a pointer naming the file and section of the new home",
        "A note that holds other rules keeps them; only the moved rule is removed.",
    ):
        assert phrase in body, phrase
    trigger = bullet(body, "first saves the rule")
    for target in ("skill", "capability file", "consumer overlay"):
        assert target in trigger, target


def test_the_section_confirms_a_note_belongs_to_the_checkout_before_retiring() -> None:
    body = retire_section()
    confirm = bullet(body, "confirms it belongs to the current checkout")
    assert "project path or project id" in confirm, "ownership is confirmed against the note's project path or id"
    assert "not confirmed" in confirm, "an unconfirmed note is not retired"
    assert "does not delete" in confirm, "an unconfirmed note is not deleted or rewritten"


def test_the_new_home_is_never_a_generated_copy() -> None:
    assert "never a generated copy" in retire_section()


def test_the_section_scopes_memory_to_the_runtime_map_and_spares_owner_files() -> None:
    body = retire_section()
    scope = bullet(body, '"Persistent memory" row')
    assert "`shared/runtimes.md`" in scope, "the rule names the runtime map by its source path"
    for phrase in (
        "Owner-authored instruction files (for example `CLAUDE.md`, `AGENTS.md`) are not persistent memory under this rule",
        "names the duplicated line to the owner and does not edit the file",
    ):
        assert phrase in body, phrase


def test_an_agent_without_the_memory_hands_the_note_back_and_the_pr_names_it() -> None:
    body = retire_section()
    for phrase in (
        "names the note in its handback, and the agent that holds that memory retires it",
        "names each retired note by path or slug and says whether it was deleted or reduced to a pointer",
    ):
        assert phrase in body, phrase
    handback = bullet(body, "names the note in its handback")
    assert "main store" in handback, "a worktree or delegated agent looks in the project's main store"
    assert "unchecked" in handback, "an unreachable store is reported as unchecked"
    assert "or the story when there is no PR" in body


def test_the_row_cross_references_the_rule_and_states_none_and_not_observed() -> None:
    capability, _, _ = memory_cells()
    for phrase in (
        f'"{SECTION_TITLE}" rule',
        "`shared/engineering-practice.md`",
        "does not apply where a cell reads `none`",
        "where a cell reads `not observed` the agent reports the rule as unchecked",
    ):
        assert phrase in capability, phrase


def test_the_row_cites_no_vendored_reference() -> None:
    # A `references/<name>.md` citation in this row would pull that capability into every
    # bundle that vendors runtimes.md (scripts/vendor_shared.py closure).
    assert "references/" not in " ".join(memory_cells())


def test_the_claude_cell_states_the_observed_store() -> None:
    _, claude, _ = memory_cells()
    for fact in (
        "Observed on 2.1.281",
        "`~/.claude/projects/<key>/memory/`",
        "`/workspace` keys `-workspace`",
        "`MEMORY.md`",
        "`Read`, `Write`, `Edit`",
        "`rm` through `Bash`",
    ):
        assert fact in claude, fact


def test_the_opencode_cell_records_v2_and_v1_as_not_observed() -> None:
    _, _, opencode = memory_cells()
    assert opencode.startswith("V2"), "the cell leads with V2"
    v2, sep, v1 = opencode.partition("V1:")
    assert sep, "the cell has a V1 part"
    assert "`not observed`" in v2, "V2"
    assert v1.strip() == "`not observed`", "V1"
    assert "`none`" not in opencode


def test_the_rule_text_is_not_restated_under_the_map_rules() -> None:
    text = RUNTIMES.read_text()
    rules = text.split("## Rules that follow from the map", 1)[1].split("\n## ", 1)[0]
    assert not re.search(r"memory|retir", rules, re.IGNORECASE), "no memory-retirement rule under the map rules"
