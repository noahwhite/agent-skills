"""Guards for the persistent-memory retirement rule (SKL-218).

The rule lives once in shared/engineering-practice.md; shared/runtimes.md carries one
"Persistent memory" row that names each runtime's store and cross-references the rule.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRACTICE = ROOT / "shared" / "engineering-practice.md"
RUNTIMES = ROOT / "shared" / "runtimes.md"
SECTION = "## Retire superseded memory"


def retire_section() -> str:
    text = PRACTICE.read_text()
    assert text.count(SECTION) == 1, f"expected one '{SECTION}' heading"
    body = text.split(SECTION, 1)[1]
    return body.split("\n## ", 1)[0]


def memory_row() -> str:
    rows = [line for line in RUNTIMES.read_text().splitlines()
            if line.startswith("| Persistent memory")]
    assert len(rows) == 1, f"expected one persistent-memory row in shared/runtimes.md, got {len(rows)}"
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


def test_the_new_home_is_never_a_generated_copy() -> None:
    assert "never a generated copy" in retire_section()


def test_the_section_scopes_memory_to_the_runtime_map_and_spares_owner_files() -> None:
    body = retire_section()
    for phrase in (
        'the "Persistent memory" row of `references/runtimes.md`',
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


def test_the_row_has_three_non_empty_cells() -> None:
    cells = memory_row().split("|")
    assert cells[0] == "" and cells[-1] == "", "the row must open and close with a pipe"
    capability, claude, opencode = (cell.strip() for cell in cells[1:-1])
    assert capability and claude and opencode


def test_the_row_cross_references_the_rule_and_states_none_and_not_observed() -> None:
    capability, claude, opencode = (cell.strip() for cell in memory_row().split("|")[1:4])
    for phrase in (
        '"Retire superseded memory" rule in `references/engineering-practice.md`',
        "does not apply where a cell reads `none`",
        "where a cell reads `not observed` the agent reports the rule as unchecked",
    ):
        assert phrase in capability, phrase
    assert "Observed on" in claude and "MEMORY.md" in claude
    assert "V2" in opencode and "V1" in opencode


def test_the_rule_text_is_not_restated_under_the_map_rules() -> None:
    rules = RUNTIMES.read_text().split("## Rules that follow from the map", 1)[1].split("\n## ", 1)[0]
    assert "Persistent memory" not in rules
    assert "superseded memory" not in rules
