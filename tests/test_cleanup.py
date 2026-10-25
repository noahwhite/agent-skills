"""Contract checks for the cleanup skill.

The skill is the last step of a story's life: it removes the artefacts a session created for a
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
    return SKILL.read_text()


def section(body: str, heading: str) -> str:
    """One `## ` section, without its heading or the next heading."""
    match = re.search(rf"^## {re.escape(heading)}\s*$", body, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = body[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def hosted_evidence_row() -> str:
    rows = [line for line in (ROOT / "shared" / "runtimes.md").read_text().splitlines()
            if line.startswith("| Hosted evidence")]
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
        "the key's own team prefix is not `profile.tracker.team_key`",
        "The view's team field carries no key, so the prefix is the check",
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
        "A cited pull request is `keep`",
        "Find artefacts by story key",
        "per-session and randomly named",
    ):
        assert phrase in body, phrase


def test_the_key_is_matched_at_a_token_boundary_never_as_a_substring() -> None:
    body = section(text(), "2. Inventory every artefact before removing any")
    for phrase in (
        "**Match the key at a token boundary.**",
        "the key starts the name or follows a `-` or `/` in it, and the key ends the name or is followed by a `-` or `/` in it",
        "the directory `<key>` in `/tmp/<key>/checkout` all carry it",
        "`<key>0`, `x<key>`, and `<key>x` do not",
        "A name that fails the boundary test is a different story's artefact",
    ):
        assert phrase in body, phrase


def test_inventory_names_every_source() -> None:
    body = section(text(), "2. Inventory every artefact before removing any")
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
    body = section(text(), "2. Inventory every artefact before removing any")
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
        "Before each removal, after `git fetch origin`, establish merge evidence",
        "A merged PR whose head commit is the tip: `gh pr view <n> --json state,headRefOid`",
        "from `git ls-remote --heads origin <branch>` for a remote one",
        "Containment, only when `profile.git.merge_method` is neither `squash` nor `rebase`",
        "`git merge-base --is-ancestor",
        "origin/<profile.git.integration_branch>",
        "Under a squash or a rebase merge the integration branch holds a different commit",
    ):
        assert phrase in body, phrase


def test_each_artefact_kind_has_its_guarded_removal() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "Remove in this order, so a branch is never refused because a worktree still holds it",
        "Removed with `git worktree remove` only when `git status --porcelain --ignored` is empty inside it",
        "only when its HEAD is the tip of a branch with merge evidence",
        "A worktree with a detached HEAD, or on a branch without merge evidence, is refused",
        "not the worktree hosting the current session",
        "Ignored files count",
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


def test_worktrees_are_removed_before_the_branch_they_hold() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    assert body.index("**Worktree.**") < body.index("**Local branch.**") < body.index("**Remote branch.**")


def test_the_never_force_and_per_artefact_refusal_rules_are_pinned() -> None:
    body = section(text(), "3. Delete only with merge evidence")
    for phrase in (
        "`--force` is never used, on any command, and a removal that would need it is refused instead.",
        "An artefact that fails a check is skipped, not forced, and the run continues with the others.",
        "A read-back that still lists it is a refusal, not a removal",
        "Every refusal is recorded in the report as a dated line naming the artefact, the failed check, and why",
    ):
        assert phrase in body, phrase
    for line in body.splitlines():
        if "--force" in line:
            for escape in ("except", "unless", "other than", "apart from"):
                assert escape not in line.lower(), f"a never-force exception crept in: {line.strip()}"


def test_the_hosted_evidence_row_names_list_download_and_a_per_artefact_delete() -> None:
    capability, claude, opencode = (cell.strip() for cell in hosted_evidence_row().split("|")[1:4])
    assert capability.startswith("Hosted evidence")
    for phrase in ("list and download", "per-artifact delete action"):
        assert phrase in claude, phrase
    assert "where no per-artifact delete action is exposed, the map gives none and the copy stays" in claude
    assert "nothing to list, download, or delete" in opencode
    assert "conversation delete" not in claude, "a conversation-wide delete is not a per-artefact action"


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
        "delete the hosted copy only through the mapped per-artefact delete action",
        "With no mapped per-artefact delete action the copy stays where it is",
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
