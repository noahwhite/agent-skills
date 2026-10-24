"""Contract checks for the cleanup skill.

The skill is the last step of a story's life: it removes the artefacts a session created for a
story and moves the evidence it hosted onto the story. These checks pin the registration the
repository contract-tests for every skill, and then the behaviour the acceptance criteria name.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "cleanup" / "SKILL.md"
MANIFEST = json.loads((ROOT / "skills.json").read_text())


def text() -> str:
    return SKILL.read_text()


def section(body: str, heading: str) -> str:
    """One `## ` section, without its heading or the next heading."""
    match = re.search(rf"^## {re.escape(heading)}\s*$", body, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = body[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def test_skill_file_exists() -> None:
    assert SKILL.is_file(), f"missing {SKILL.relative_to(ROOT)}"


def test_manifest_registers_skill_with_its_capabilities() -> None:
    assert {"todo-tracking", "linear", "github"} <= set(MANIFEST["skills"]["cleanup"])


def test_vendored_bundle_carries_every_linked_capability() -> None:
    for name in ("profile", "runtimes", "todo-tracking", "linear", "github"):
        assert (SKILL.parent / "references" / f"{name}.md").is_file(), name


def test_readme_lists_skill_in_table() -> None:
    row = "| [`cleanup`](skills/cleanup/SKILL.md) |"
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
    assert found, "missing cleanup row from the README Skills table"


def test_todo_tracking_has_seed_entry() -> None:
    assert "- **cleanup:**" in (ROOT / "shared" / "todo-tracking.md").read_text()


def test_invocation_takes_one_or_more_story_keys_and_pins_the_usage_line() -> None:
    body = section(text(), "Invocation")
    assert [line.strip() for line in body.splitlines() if line.strip() == "/cleanup <story-key> [<story-key> ...]"]
    assert "prints `usage: /cleanup <story-key> [<story-key> ...]` and stops without touching anything" in body
    for phrase in (
        "never infers a story from ambient context",
        "from the current branch",
        "from a worktree path",
    ):
        assert phrase in body, phrase


def test_every_key_is_resolved_against_the_tracker_before_anything_is_touched() -> None:
    body = section(text(), "1. Resolve every key against the tracker")
    for phrase in (
        "before anything is touched",
        "Resolve each key with `linear issue view <story-key>`",
        "`profile.tracker.team_key`",
        "Report an unresolved key as `unresolved` and skip it",
        "The other keys still run",
        "Never invent, guess, or shorten a key",
    ):
        assert phrase in body, phrase


def test_inventory_prints_before_anything_is_removed_and_finds_artefacts_by_key() -> None:
    body = section(text(), "2. Inventory every artefact before removing any")
    for phrase in (
        "nothing is removed before the inventory report is printed",
        "states the artefact, its path or URL, and its disposition",
        "Find artefacts by story key",
        "per-session and randomly named",
    ):
        assert phrase in body, phrase


def test_inventory_names_every_source() -> None:
    body = section(text(), "2. Inventory every artefact before removing any")
    for phrase in (
        "Every entry `git worktree list` reports whose path or branch carries the key",
        "worktree helper created",
        "under a prefix in `profile.git.branch_prefixes`",
        "`git ls-remote --heads origin '*<key>*'`",
        "`gh pr list --state all --search '<key>'`",
        "its full URL",
        "QA runner scratch output and uncommitted evidence copies only",
        "Session checklist and scratch files naming the key under `profile.workspace.scratch_dir`",
    ):
        assert phrase in body, phrase


def test_inventory_excludes_the_durable_record_and_the_live_session() -> None:
    body = section(text(), "2. Inventory every artefact before removing any")
    for phrase in (
        "Evidence committed under `profile.qa.evidence_dir`",
        "durable record",
        "never removed",
        "Evidence `qa-verification` already attached",
        "The invoking session's own scratch directory",
        "merge-approval rendezvous file",
        "still live",
        "cannot attribute to the key is left out, and the report names it as skipped",
    ):
        assert phrase in body, phrase


def test_deletion_requires_merge_evidence_from_the_storys_pull_requests() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "Nothing is deleted while it still holds unmerged or unreviewed work",
        "A merged PR whose head commit is the branch tip",
        "`gh pr view <n> --json state,headRefOid`",
        "Containment, only when `profile.git.merge_method` is neither `squash` nor `rebase`",
        "`git merge-base --is-ancestor",
        "origin/<profile.git.integration_branch>",
        "Under a squash or a rebase merge the integration branch holds a different commit",
    ):
        assert phrase in body, phrase


def test_each_artefact_kind_has_its_guarded_removal() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "Removed with `git branch -D`",
        "Removed with `git worktree remove` only when `git status --porcelain` is empty inside it",
        "not the worktree hosting the current session",
        "only when no open PR heads it",
        "`gh pr list --state open --json headRefName`",
        "Removed only from a directory the inventory proved idle",
    ):
        assert phrase in body, phrase


def test_the_never_force_and_per_artefact_refusal_rules_are_pinned() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "`--force` is never used",
        "skipped, not forced, and the run continues with the others",
        "Every refusal is recorded in the report and posted as a dated comment on the named story",
        "naming the artefact, the failed check, and why",
        "confirmed by reading it back",
    ):
        assert phrase in body, phrase


def test_the_hosted_evidence_row_names_list_download_and_a_conditional_delete() -> None:
    runtimes = (ROOT / "shared" / "runtimes.md").read_text()
    row = next(line for line in runtimes.splitlines() if line.startswith("| Hosted evidence"))
    capability, claude, opencode = (cell.strip() for cell in row.split("|")[1:4])
    assert capability.startswith("Hosted evidence")
    for phrase in ("list and download", "delete"):
        assert phrase in claude, phrase
    assert "where no delete action is exposed, the map gives none and the copy stays" in claude
    assert "nothing to list, download, or delete" in opencode


def test_the_hosted_evidence_section_is_separated_and_cites_the_map() -> None:
    body = section(text(), "4. Hosted evidence (a self-contained, capability-detected section)")
    for phrase in (
        "separated on purpose",
        "drop it, or layer it through an overlay",
        "names no host and no runtime",
        "[references/runtimes.md](references/runtimes.md)",
        "Read that row for the runtime this session runs on",
        "map the capability to the closest equivalent and say which one was used",
    ):
        assert phrase in body, phrase


def test_the_capability_skip_leg_prints_the_pinned_line_and_touches_nothing() -> None:
    body = section(text(), "4. Hosted evidence (a self-contained, capability-detected section)")
    for phrase in (
        "print `skipped: this runtime has no hosted-evidence capability`",
        "touch no hosted content",
        "name the skip and its reason in the final report",
    ):
        assert phrase in body, phrase


def test_the_sweep_downloads_and_deletes_through_the_mapped_action_only() -> None:
    body = section(text(), "4. Hosted evidence (a self-contained, capability-detected section)")
    for phrase in (
        "download it into the session's scratch directory",
        "attach it to the named story as step 5 says",
        "delete the hosted copy only through the mapped delete action",
        "With no mapped delete action the copy stays where it is",
        "There is no user-facing runtime switch",
    ):
        assert phrase in body, phrase


def test_an_unreachable_mapped_capability_fails_loudly_instead_of_sweeping() -> None:
    body = section(text(), "4. Hosted evidence (a self-contained, capability-detected section)")
    for phrase in (
        "Detection never guesses",
        "`error: hosted-evidence capability unreachable: <failure>`",
        "touch no hosted content",
        "print the report so the work already done is not silent",
        "exit non-zero",
        "never a silent skip and never a pass",
    ):
        assert phrase in body, phrase
