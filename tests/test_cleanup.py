"""Contract checks for the cleanup skill.

The skill is the last step of a story's life: it removes the artifacts a session created for a
story and moves the evidence it hosted onto the story. These checks pin the registration the
repository contract-tests for every skill, and then the behaviour the acceptance criteria name.
"""

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "cleanup" / "SKILL.md"
MANIFEST = json.loads((ROOT / "skills.json").read_text())
HOST_RE = re.compile(r"\b[a-z0-9][a-z0-9-]*\.(?:ai|com|io|net|org|dev)\b", re.IGNORECASE)


def text() -> str:
    return SKILL.read_text(encoding="utf-8")


def runtime_map_lines() -> list[str]:
    return (ROOT / "shared" / "runtimes.md").read_text(encoding="utf-8").splitlines()


def section(body: str, heading: str) -> str:
    """One `## ` section, without its heading or the next heading."""
    match = re.search(rf"^## {re.escape(heading)}\s*$", body, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = body[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def hosted_evidence_row() -> str:
    rows = [line for line in runtime_map_lines() if line.startswith("| Hosted evidence")]
    assert len(rows) == 1, f"expected one hosted-evidence row in shared/runtimes.md, got {len(rows)}"
    return rows[0]


def repository_test_helper(name: str):
    """A function from tests/test_skills.py, loaded without making tests/ a package."""
    spec = importlib.util.spec_from_file_location("repo_test_skills", ROOT / "tests" / "test_skills.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, name)


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
        "Resolve each key with `linear issue view <story-key> --no-download`, so resolving a key writes no file",
        "A key does not resolve only when that lookup fails",
        "the tracker lookup alone decides",
        "a key whose team prefix differs from `profile.tracker.team_key` resolves like any other",
        "Report an unresolved key as `unresolved` and skip it",
        "The other keys still run",
        "Never invent, guess, or shorten a key",
    ):
        assert phrase in body, phrase
    # SKL-204: a differing team prefix is no longer a reason to treat a key as unresolved.
    for stale in ("team prefix is not `profile.tracker.team_key`", "so the prefix is the check"):
        assert stale not in body, stale


def test_inventory_prints_before_anything_is_removed_and_finds_artifacts_by_key() -> None:
    body = section(text(), "2. Inventory every artifact before removing any")
    for phrase in (
        "nothing is removed before the inventory report is printed",
        "states the artifact, its path or URL, and its disposition",
        "A cited pull request is `keep`",
        "Find artifacts by story key",
        "per-session and randomly named",
    ):
        assert phrase in body, phrase


def test_the_key_is_matched_at_a_token_boundary_never_as_a_substring() -> None:
    body = section(text(), "2. Inventory every artifact before removing any")
    for phrase in (
        "**Match the key at a token boundary.**",
        "the key starts the name or follows a `-` or `/` in it, and the key ends the name or is followed by a `-` or `/` in it",
        "the directory `<key>` in `/tmp/<key>/checkout` all carry it",
        "`<key>0`, `x<key>`, and `<key>x` do not",
        # SKL-220: scoped so it does not exclude persistent-memory notes, which have their own match.
        "Outside persistent-memory notes, which step 2 matches by their own rule below, "
        "a name that fails the boundary test is a different story's artifact",
    ):
        assert phrase in body, phrase
    assert "A name that fails the boundary test" not in text(), "the unscoped boundary sentence is back"


def test_inventory_names_every_source() -> None:
    body = section(text(), "2. Inventory every artifact before removing any")
    for phrase in (
        "Every entry `git worktree list` reports whose path or branch carries the key",
        "worktree helper created",
        "under a prefix in `profile.git.branch_prefixes`",
        "`git ls-remote --heads origin '*<key>*'`",
        "`gh pr list --state all --search '<key>' --json number,url,state,headRefName --limit 1000`",
        "That limit fetches every page the CLI holds",
        "nothing is removed for that story until it is",
        "its full URL",
        "QA runner scratch output and uncommitted evidence copies only",
        "an uncommitted copy inside `profile.qa.evidence_dir`",
        "Scan the session scratch base this runtime gives",
        "reported as unsearchable, never as empty",
        "Committed evidence, meaning the content the branch tip holds",
        "Session checklist and scratch files naming the key under `profile.workspace.scratch_dir`",
        "the report names this source as unsearchable instead of reporting it as empty",
    ):
        assert phrase in body, phrase


def test_inventory_excludes_the_durable_record_and_refuses_a_live_session() -> None:
    body = section(text(), "2. Inventory every artifact before removing any")
    for phrase in (
        "Evidence committed under `profile.qa.evidence_dir`",
        "durable record",
        "never removed",
        "Evidence `qa-verification` already attached",
        "The invoking session's own scratch directory",
        "merge-approval rendezvous file",
        "its checklist file exists and every item is checked",
        "A directory with no checklist file is never idle",
        "the report names it with the files it keeps, so a human can remove them deliberately",
        "This is the strict direction on purpose",
        "cannot attribute to the key is left out, and the report names it as skipped",
    ):
        assert phrase in body, phrase


def test_deletion_requires_merge_evidence_from_the_storys_pull_requests() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "Nothing is deleted while it still holds unmerged or unreviewed work",
        # SKL-220: a persistent-memory note is guarded by tracker state, not merge evidence.
        "Before each removal other than a persistent-memory note, after `git fetch origin`, establish merge evidence",
        "A merged PR whose head commit is the tip: `gh pr view <n> --json state,headRefOid`",
        "from `git ls-remote --heads origin <branch>` for a remote one",
        "`git merge-base --is-ancestor",
        "origin/<profile.git.integration_branch>",
    ):
        assert phrase in body, phrase


def bullet(body: str, start: str, end: str) -> str:
    """The text of one step 3 bullet, from its bold lead to the next bullet's bold lead."""
    return body[body.index(start): body.index(end)]


def test_containment_is_merge_evidence_for_a_local_branch_under_every_merge_method() -> None:
    # SKL-244: containment is a positive proof whatever the merge method; only exit 1 is uninformative.
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "establish merge evidence from the story's pull requests or, for a local branch, from containment:",
        # Containment is the evidence for a branch no PR reviewed, so it must settle the "unreviewed work" rule.
        "For a branch, the merge evidence below is what shows it holds no such work.",
    ):
        assert phrase in body, phrase
    containment = bullet(body, "- Containment, for a local branch only:", "Remove in this order")
    for phrase in (
        "after `git fetch origin` exits 0, `git merge-base --is-ancestor <tip> origin/<profile.git.integration_branch>` "
        "exiting 0 is merge evidence for a local branch under every `profile.git.merge_method`, including when no PR heads it",
        "`<tip>` is the output of `git rev-parse <branch>`.",
        "A tip reachable from the integration branch has every commit on it in the integration branch, "
        "whatever the merge method.",
        'Exit 1 is not evidence and is not reported as "unmerged": the branch then needs a merged PR whose head commit '
        'is the tip, and without one it is refused with the reason "no merge evidence".',
        "Any other exit status refuses that branch, whatever a PR shows, and the report names the exit status.",
        "When `git fetch origin` exits non-zero, containment is not read and the branch is handled as for exit 1: "
        'it needs a merged PR whose head commit is the tip, and without one it is refused with the reason "no merge '
        'evidence", and the report names the fetch exit status.',
        "a detached HEAD is refused even at a contained commit.",
    ):
        assert phrase in containment, phrase
    for stale in ("proves nothing and is never used", "neither `squash` nor `rebase`"):
        assert stale not in body, stale


def test_containment_is_never_merge_evidence_for_a_remote_branch() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    remote = bullet(body, "**Remote branch.**", "**Disposable QA output and session files.**")
    phrase = "Containment is never merge evidence for a remote branch, under any merge method"
    assert phrase in remote, phrase


def test_a_checked_out_local_branch_waits_for_its_worktree() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    local = bullet(body, "**Local branch.**", "**Remote branch.**")
    phrase = (
        "A local branch checked out in any worktree is removed only after that worktree is removed, and is refused, "
        "naming the worktree's failed check, when that worktree is refused or kept, including the main working tree "
        "and the worktree hosting the current session."
    )
    assert phrase in local, phrase


def test_a_local_branch_tip_is_read_again_before_its_delete() -> None:
    # A commit landing after the evidence read would otherwise be lost to `git branch -D`.
    body = section(text(), "3. Delete only with merge evidence")
    local = bullet(body, "**Local branch.**", "**Remote branch.**")
    phrase = (
        "Read the tip with `git rev-parse <branch>` a second time immediately before `git branch -D` and refuse if "
        "it moved; when containment is the evidence, run `git merge-base --is-ancestor <tip> "
        "origin/<profile.git.integration_branch>` again with that tip and refuse unless it exits 0, running the "
        "delete immediately after these reads with no other step between."
    )
    assert phrase in local, phrase


def test_each_artifact_kind_has_its_guarded_removal() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "Remove in this order, so a branch is never refused because a worktree still holds it",
        "only when its HEAD is the tip of a branch with merge evidence",
        "A worktree with a detached HEAD, or on a branch without merge evidence, is refused",
        "not the worktree hosting the current session",
        "Removed with `git branch -D`",
        "only when the remote tip has merge evidence and no open PR heads it",
        "Read the remote tip a second time immediately before the delete and refuse if it moved",
        "`gh pr list --state open --json headRefName,number --limit 1000`",
        "Match head refs from that listing, not a free-text search",
        "a listing that returns exactly its limit is not proven complete",
        "A remote branch that never became a PR is refused rather than deleted",
        "Removed only from a directory the inventory proved idle, and only after step 5 has attached the evidence the run swept",
        "An uncommitted evidence copy is removable only once it has a home the story keeps",
    ):
        assert phrase in body, phrase


# The seven names SKL-243 A1 fixes, written out literally in its order and not derived from any
# other value in this file.
SEVEN_NAMES = "`.venv`, `venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`"
LIST_LEAD = "whose final path component, with that trailing `/` removed, is one of "


def test_a_worktree_holding_only_regenerable_ignored_entries_is_emptied_then_removed() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    # The whole clause after "is one of" is the list and nothing else, each name in its own backticks,
    # so `.venv` never stands in for `venv` and no extra name hides inside or after the clause.
    list_sentence = f"{LIST_LEAD}{SEVEN_NAMES}; so `tests/__pycache__/` qualifies."
    assert list_sentence in body, list_sentence
    list_line = next(line for line in body.splitlines() if LIST_LEAD in line)
    assert list_line.rstrip().endswith(list_sentence), list_line
    assert body.count(LIST_LEAD) == 1
    for phrase in (
        "uncommitted or ignored files, apart from the regenerable ignored entries below.",
        "and only when `git status --porcelain --ignored -z` inside it is empty or lists only regenerable ignored entries, which the run deletes first as below.",
        "An ignored entry is regenerable when `git status --porcelain --ignored -z` reports it with the ignored code `!!` as a directory (with a trailing `/`)",
        "An untracked entry (code `??`) is never regenerable, even with a matching name and a trailing `/`.",
        "Only when the worktree passes every other check in this step and its status lists no other entry",
        "records each regenerable entry by exact path in the inventory",
        "deletes each one with `rm -r -- <path>` on that exact path inside the worktree: no `-f`, no `--force`, no glob",
        "The path is passed to `rm` as one argument, exactly as the `-z` read gave it, never through shell expansion.",
        "The run stops at the first failed deletion and deletes nothing more.",
        "reads `git status --porcelain --ignored -z` inside the worktree again",
        "removes the worktree with `git worktree remove` only when that second read is empty, "
        "running the removal immediately after the read with no other step between them.",
        "A failed deletion, a second read that is not empty, a nested repository, or a failed content check refuses the worktree, "
        "and the report names the path and the failure",
        "A failed `rm -r` can leave part of that entry behind, so the run then lists what remains at its path, and the report names it.",
        "An ignored file created between the second read and the removal is still deleted with the directory; "
        "git offers no checked removal short of `--force`, so this narrow window is accepted rather than closed.",
        "A worktree locked after its checks passed has its regenerable entries deleted before `git worktree remove` refuses it; "
        "the report names it as a refused removal, and since only regenerable entries are lost, this window is accepted too.",
        "A nested repository created inside a regenerable entry after its listing is still deleted with it; "
        "nothing short of locking the directory closes this, so this window is accepted as well.",
    ):
        assert phrase in body, phrase
    assert (
        body.index("records each regenerable entry by exact path in the inventory")
        < body.index("`rm -r -- <path>`")
        < body.index("reads `git status --porcelain --ignored -z` inside the worktree again")
        < body.index("only when that second read is empty")
    )
    # SKL-243: the unqualified empty-status rule is replaced, not left beside the new one. Only the
    # bullet head and the second-read sentence may tie a worktree removal to an empty status.
    for stale in (
        "Removed with `git worktree remove` only when `git status --porcelain --ignored` is empty inside it",
        "Ignored files count",
    ):
        assert stale not in body, stale
    allowed = (
        "- **Worktree.** Removed with `git worktree remove` only when its HEAD",
        "It then reads `git status --porcelain --ignored -z` inside the worktree again",
    )
    for line in body.splitlines():
        if re.search(r"\bempty\b", line) and re.search(r"worktree remov|removal", line, re.IGNORECASE):
            assert line.strip().startswith(allowed), line


def test_a_regenerable_entry_needs_no_nested_repository_and_its_content_check() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    nested = (
        "the run first lists the contents of each such directory at any depth, including entries whose names begin "
        "with a dot and without following symlinks (`find ./<path> -print` does; `ls -R` hides dot entries and does "
        "not qualify), and refuses the worktree when a listing holds a nested repository: "
        "an entry named `.git` at any depth, whether a directory or a file."
    )
    nested_more = (
        "A bare repository, a directory holding `HEAD`, `objects` and `refs` side by side, counts as a nested repository too.",
        "A listing that exits non-zero refuses the worktree, whatever it printed.",
    )
    checks = (
        "It also requires a per-name content check before an entry counts as regenerable:",
        "- `__pycache__` holds only `*.pyc` files: every entry inside it is a regular file whose name ends in `.pyc`.",
        "- `.venv` and `venv` have `pyvenv.cfg` at their top: a regular file of that name directly inside the directory.",
        "- `.pytest_cache`, `.mypy_cache` and `.ruff_cache` have `CACHEDIR.TAG` at their top: "
        "a regular file of that name directly inside the directory.",
        "- `node_modules` has no content check and is subject to the nested-repository refusal only.",
        "A directory that fails its check is not regenerable and the worktree is refused.",
        "The run checks every regenerable entry before it deletes any, so a nested repository or a failed content check deletes nothing.",
    )
    stray = (
        "A stray file inside a directory that passes its check is still deleted with it: "
        "neither the name nor the marker file can tell a file a tool wrote from one a person left there."
    )
    no_prompt = "`rm` runs with standard input from `/dev/null`, so it never stops to prompt."
    for phrase in (nested, *nested_more, *checks, stray, no_prompt):
        assert phrase in body, phrase
    assert (
        body.index(nested)
        < body.index(nested_more[0])
        < body.index(nested_more[1])
        < body.index(checks[0])
        < body.index(checks[-1])
        < body.index("records each regenerable entry by exact path in the inventory")
        < body.index("`rm -r -- <path>`")
    )


def test_every_status_read_is_unquoted_and_must_succeed() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "Every status read in this step runs `git status --porcelain --ignored -z` inside the worktree and must exit 0; "
        "a read that exits non-zero refuses the worktree, whatever it printed.",
        "The `-z` form lists the same entries as `git status --porcelain --ignored`, separated by NUL and never quoted, "
        "so a path with a space, a quote or a non-ASCII character reaches the checks below exactly as it is on disk.",
    ):
        assert phrase in body, phrase


def test_a_worktree_git_cannot_remove_is_refused_before_any_deletion() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "only when git can remove it",
        "A worktree git cannot remove is refused before anything is deleted from it: the main working tree "
        "(the first entry `git worktree list --porcelain` reports), a worktree that listing marks `locked`, "
        "and a worktree that holds a submodule, unless git can remove it with nothing lost.",
        "The worktree's submodule paths are the entries `git ls-files --stage -z` lists inside it with mode `160000`; "
        "that read must exit 0, and `-z` delivers each path exactly as it is on disk, spaces included.",
        "A worktree with submodule paths is removable with nothing lost only when its own modules directory "
        "(the path `git rev-parse --git-path modules` prints inside the worktree) does not exist and each submodule path "
        "is absent (nothing at all exists at `./<path>`, not even a symlink) or an empty directory "
        "(`find ./<path> -mindepth 1 -print` prints nothing and exits 0, so an entry whose name begins with a dot counts).",
        "The status read never reports files inside a submodule path, and git refuses to remove a worktree "
        "that has a modules directory, so a worktree that fails any of these is refused.",
        "A worktree whose path no longer exists holds nothing to delete: the run skips its status read, "
        "removes it with `git worktree remove`, and confirms the removal with the `git worktree list` read-back.",
    ):
        assert phrase in body, phrase
    assert "a worktree whose path does not exist" not in body


def test_any_other_status_entry_refuses_the_worktree_and_nothing_is_deleted() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "When the status lists any other entry, the worktree is refused and nothing is deleted from it, the regenerable entries included",
        "an ignored entry not on the regenerable list (for example `.env`, a local note, or other build output)",
        "a symlink or file named like a list entry",
        "a tracked modification (staged, unstaged, deleted, renamed or conflicted)",
        "an untracked entry (a file or a directory)",
        "The inventory and the refusal line name every such entry by exact path and kind",
        "Under `-z` a rename or copy record carries two paths, the new one and then the original, and both are named.",
    ):
        assert phrase in body, phrase


def test_the_inventory_and_report_name_each_regenerable_entry_by_exact_path() -> None:
    inventory = section(text(), "2. Inventory every artifact before removing any")
    for phrase in (
        "Under each worktree's line, the inventory lists by exact path every entry its status read (step 3) reports.",
        "Each regenerable ignored entry the run will delete (step 3) has disposition `remove`; the run will delete it only "
        "when the worktree passes every step 3 check, so the inventory evaluates those checks before it prints, "
        "and step 3 evaluates them again before deleting.",
        "A regenerable entry in a worktree that fails any of them is `keep`, and each other entry is `refuse`, with its kind.",
    ):
        assert phrase in inventory, phrase
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "The final report lists, under the worktree it came from and by exact path, each entry deleted, "
        "including when the worktree removal was then refused, with the failed check, and each failed deletion as a refusal",
        "A worktree refused because its status lists any other entry lists no entry as deleted",
        "The step 6 template shows where these lines go.",
        "for a worktree whose regenerable entries were deleted, the second status read is part of that read-back",
    ):
        assert phrase in body, phrase
    report = section(text(), "6. Report and confirm")
    removed = "removed:\n- <artifact>: <path or URL>\n  - deleted: <regenerable entry path>\n"
    refused = (
        "refused:\n- <artifact>: <failed check>, <why>\n"
        "  - deleted: <regenerable entry path>\n"
        "  - refused: <regenerable entry path>: <failed deletion>\n"
    )
    assert removed in report, removed
    assert refused in report, refused
    assert report.index(removed) < report.index(refused)


def test_worktrees_are_removed_before_the_branch_they_hold() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    assert body.index("**Worktree.**") < body.index("**Local branch.**") < body.index("**Remote branch.**")


def test_the_never_force_and_per_artifact_refusal_rules_are_pinned() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "`--force` is never used, on any command, and a removal that would need it is refused instead.",
        "An artifact that fails a check is skipped, not forced, and the run continues with the others.",
        "A read-back that still lists it is a refusal, not a removal",
        "Every refusal is recorded in the report as a dated line naming the artifact, the failed check, and why",
    ):
        assert phrase in body, phrase
    for line in body.splitlines():
        if "--force" in line:
            for escape in ("except", "unless", "other than", "apart from"):
                assert escape not in line.lower(), f"a never-force exception crept in: {line.strip()}"


def test_the_hosted_evidence_row_names_list_download_and_a_per_artifact_delete() -> None:
    capability, claude, opencode = (cell.strip() for cell in hosted_evidence_row().split("|")[1:4])
    assert capability.startswith("Hosted evidence")
    for phrase in ("list and download", "per-artifact delete action"):
        assert phrase in claude, phrase
    assert "where no per-artifact delete action is exposed, the map gives none and the copy stays" in claude
    assert "nothing to list, download, or delete" in opencode
    assert "conversation delete" not in claude, "a conversation-wide delete is not a per-artifact action"


def test_the_hosted_evidence_section_is_separated_and_cites_the_map() -> None:
    body = section(text(), "4. Hosted evidence (a self-contained, capability-detected section)")
    for phrase in (
        "separated on purpose",
        "drop it, or layer it through an overlay",
        "names no host and no runtime",
        "[references/runtimes.md](references/runtimes.md)",
        "Read that row for the runtime this session runs on",
        "a later session reaches none of an earlier session's hosted copies",
    ):
        assert phrase in body, phrase


def test_the_capability_skip_leg_prints_the_pinned_line_and_touches_nothing() -> None:
    body = section(text(), "4. Hosted evidence (a self-contained, capability-detected section)")
    for phrase in (
        "print `skipped: this runtime has no hosted-evidence capability`",
        "touch no hosted content",
        "name the skip and its reason in the final report",
        "A capability is never guessed from a runtime the map does list",
    ):
        assert phrase in body, phrase


def test_the_sweep_downloads_and_deletes_through_the_mapped_action_only() -> None:
    body = section(text(), "4. Hosted evidence (a self-contained, capability-detected section)")
    for phrase in (
        "download it into the session's scratch directory",
        "attach it to the named story as step 5 says",
        "delete the hosted copy only through the mapped per-artifact delete action",
        "With no mapped per-artifact delete action the copy stays where it is",
        "There is no user-facing runtime switch",
    ):
        assert phrase in body, phrase


def test_an_unreachable_mapped_capability_fails_loudly_instead_of_sweeping() -> None:
    body = section(text(), "4. Hosted evidence (a self-contained, capability-detected section)")
    for phrase in (
        "Detection never guesses",
        "`error: hosted-evidence capability unreachable: <failure>`",
        "touch no hosted content",
        "print the report and post the story comments step 6 requires so the work already done is not silent",
        "exit non-zero",
        "never a silent skip and never a pass",
    ):
        assert phrase in body, phrase


def test_evidence_is_attached_through_the_path_qa_verification_uses() -> None:
    body = section(text(), "5. Land the evidence on the story")
    for phrase in (
        "the same tracker-attachment path `qa-verification` uses",
        "`linear issue attach <story-key> <file>`",
        "`linear issue comment add <story-key> --attach <file>`",
        "where the image renders inline",
        "Name each attachment in a comment on the story, saying what it shows",
        "a plain CLI attachment is a sidebar link and images do not render inline",
    ):
        assert phrase in body, phrase


def test_existing_evidence_is_cited_and_never_re_uploaded_or_deleted() -> None:
    body = section(text(), "5. Land the evidence on the story")
    for phrase in (
        "Cite, never re-upload and never delete",
        "evidence `qa-verification` already attached",
        "evidence committed under `profile.qa.evidence_dir`",
        "`linear issue view <story-key> --json` lists the story's attachments",
        "No hosted-page or third-party link goes to the tracker",
        "attached to the story it is evidence for",
    ):
        assert phrase in body, phrase


def test_the_run_ends_with_one_report_covering_every_outcome() -> None:
    body = section(text(), "6. Report and confirm")
    for phrase in (
        "one report, structured per story, as the run's final message",
        "what was removed",
        "what was archived to the tracker, with the attachment names",
        "what was skipped and why, including the hosted-evidence skip",
        "what it refused to touch, with the failed check",
        "nothing is removed before the inventory report is printed",
        "post the same summary as a comment on that story",
        "One comment per story per run",
    ):
        assert phrase in body, phrase


def test_the_run_acts_in_one_repository() -> None:
    body = section(text(), "Boundaries")
    for phrase in (
        "It acts in one repository: the one the run starts in, or the one this skill's overlay names",
        "named as skipped rather than touched",
    ):
        assert phrase in body, phrase


def persistent_memory_row() -> str:
    rows = [line for line in runtime_map_lines() if line.startswith("| Persistent memory")]
    assert len(rows) == 1, f"expected one persistent-memory row in shared/runtimes.md, got {len(rows)}"
    return rows[0]


def test_step_1_records_each_resolved_keys_tracker_state() -> None:
    body = section(text(), "1. Resolve every key against the tracker")
    assert (
        "Record each resolved key's tracker state, the state its `linear issue view` lookup reports"
        in body
    )


def test_the_read_first_runtimes_bullet_names_the_persistent_memory_row() -> None:
    bullets = [line for line in section(text(), "Read first").splitlines()
               if line.startswith("- [references/runtimes.md]")]
    assert len(bullets) == 1, "the Read first section has no single references/runtimes.md bullet"
    assert 'the "Persistent memory" row' in bullets[0]


def test_persistent_memory_notes_are_an_inventory_source_read_from_the_runtime_map_row() -> None:
    body = section(text(), "2. Inventory every artifact before removing any")
    for phrase in (
        "**Persistent-memory notes.**",
        'the stores the "Persistent memory" row of [references/runtimes.md](references/runtimes.md) names',
        "for the main checkout and for each worktree this inventory lists",
        "this text names no runtime and no store path",
        "A store the run cannot read is reported as unsearchable, never as empty.",
    ):
        assert phrase in body, phrase


def test_a_note_is_matched_on_file_name_or_frontmatter_name_case_insensitively() -> None:
    body = section(text(), "2. Inventory every artifact before removing any")
    for phrase in (
        "A note is `remove` when its file name, with its extension ignored, or the `name` in its frontmatter carries the story key",
        "compared without regard to letter case",
        "with no letter or digit directly before or after the key",
        "A note that carries the key only in its body is `skip`, and the report names it.",
    ):
        assert phrase in body, phrase


def test_a_runtime_without_observed_memory_touches_no_note_and_prints_the_pinned_line() -> None:
    body = section(text(), "2. Inventory every artifact before removing any")
    for phrase in (
        "When the row for the runtime reads `none`, print `skipped: this runtime has no persistent memory`",
        "when it reads `not observed`, or the map has no row for the runtime, "
        "print `unchecked: persistent memory not observed on this runtime`",
        "in both cases no note is listed or touched",
    ):
        assert phrase in body, phrase


def test_a_memory_note_is_removed_only_when_its_story_is_done_or_canceled() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "**Persistent-memory note.**",
        "the story's tracker state is the only guard for it",
        "the merge-evidence guards of every other artifact are unchanged",
        "deleted with a single `rm` of its quoted path",
        "only when the state step 1 recorded for its story equals "
        "`profile.tracker.states.done` or `profile.tracker.states.canceled`",
        "When either of those two profile keys is unset, no note is removed, and the report names each unset key.",
    ):
        assert phrase in body, phrase
    guards = body[body.index("Guards that hold for every removal:"):]
    assert "merge evidence" not in guards, "a guard for every removal would override the note's state-only guard"


def test_a_memory_note_removal_is_read_back_and_index_lines_are_not_edited() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "Each note removal is read back",
        "a note still present is `refused`, not removed",
        "a store listing that fails reports the note `refused` with the failure's reason, never `removed`",
        "Index lines are not edited",
        "the report says so once when any note was removed",
    ):
        assert phrase in body, phrase


def test_the_report_names_each_memory_note_and_carries_the_pinned_lines() -> None:
    body = section(text(), "6. Report and confirm")
    for phrase in (
        "Each persistent-memory note is reported by its file name under removed, skipped, or refused, with the reason",
        "Each persistent-memory store step 2 could not read is named in the report as unsearchable.",
        "The report carries the `skipped: this runtime has no persistent memory` or "
        "`unchecked: persistent memory not observed on this runtime` line when step 2 printed one",
        "once, that index lines were not edited when any note was removed",
    ):
        assert phrase in body, phrase


def test_the_boundaries_bullet_is_scoped_to_admit_memory_notes() -> None:
    body = section(text(), "Boundaries")
    assert (
        "It removes only artifacts it can attribute to a named key: at a token boundary, "
        "or, for a persistent-memory note, by the note match step 2 states."
    ) in body


def test_the_skill_text_names_no_runtime_or_store_path_the_memory_row_names() -> None:
    headers = [line for line in runtime_map_lines() if line.startswith("| Capability |")]
    assert len(headers) == 1, f"expected one runtime map header in shared/runtimes.md, got {len(headers)}"
    runtimes = [re.sub(r"\s*\(.*\)$", "", cell.strip()) for cell in headers[0].split("|")[2:] if cell.strip()]
    runtime_cells = "|".join(persistent_memory_row().split("|")[2:])
    # Every backticked name the row's runtime cells give, bare store names included, except the
    # cell values and the delete command the skill itself must quote.
    contract_words = {"none", "not observed", "rm"}
    tokens = {token for token in re.findall(r"`([^`]+)`", runtime_cells)
              if re.search(r"[A-Za-z]", token) and token.lower() not in contract_words}
    paths = {token for token in tokens if token.startswith(("~", "/")) or token.endswith(".md")}
    assert runtimes and paths, (runtimes, paths)
    body = text()
    lowered = body.lower()
    for name in runtimes:
        assert not re.search(rf"(?<![A-Za-z0-9]){re.escape(name.lower())}(?![A-Za-z0-9])", lowered), name
    for token in tokens:
        assert f"`{token.lower()}`" not in lowered, token
    for path in paths:
        assert path.lower() not in lowered, path


def test_the_skill_text_names_no_host_the_capability_map_names() -> None:
    map_hosts = set(HOST_RE.findall(hosted_evidence_row()))
    assert map_hosts, "the hosted-evidence row names no host at all"
    assert map_hosts & set(HOST_RE.findall(text())) == set()


def test_the_runtime_neutral_wording_check_flags_the_host_the_map_names() -> None:
    offenders = repository_test_helper("hosted_store_offenders")
    map_hosts = sorted(HOST_RE.findall(hosted_evidence_row()))
    assert map_hosts, "the hosted-evidence row names no host to test the wording check with"
    for host in map_hosts:
        assert named_host(offenders, host), f"the extended wording check does not flag {host}"


def named_host(offenders, host: str) -> list[str]:
    """Run the shared check over one synthetic skill line naming `host`."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "SKILL.md"
        probe.write_text(f"Download the evidence from {host}.\n")
        return offenders([probe])
