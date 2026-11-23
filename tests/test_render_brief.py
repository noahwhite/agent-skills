"""CLI tests for skills/story-to-done/scripts/render-brief.py and its brief templates (SKL-324)."""

import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "story-to-done"
SCRIPT = SKILL_DIR / "scripts" / "render-brief.py"
ASSETS = SKILL_DIR / "assets"

MERGE_RULE = (
    "- The merge rules: a review of record binds only to the exact head it reviewed, so any change to the head, "
    "including an update-branch, needs a delta review posted before merging; every merge must run the merge guard in "
    "`references/code-review.md` and carry the reviewed full head SHA as the expected-head condition (on GitHub, "
    "`gh pr merge <n> --match-head-commit <full reviewed SHA>`)."
)
GIT_RULE = (
    "- The git rule: run every commit-creating git command with the git identity already configured and, when "
    "`profile.git.signed_commits` is true, the signing already configured; never pass `-c user.name`, `-c user.email`, "
    "`--author`, `GIT_AUTHOR_*` or `GIT_COMMITTER_*`, never write `user.name` or `user.email` with `git config`, and "
    "when signing is on never pass `-c user.signingkey`, `-c gpg.*` or `-c commit.gpgsign`; a missing identity, a "
    "failed signing check or a pushed commit whose `.commit.verification.verified` is false is a configuration fault, "
    "so stop, do not override per command or write git config, make no further commits, and report it to the user."
)
SHELL_RULE = (
    "- The shell rule: run each shell step as one simple command with literal values; never assign a variable and use "
    "it in the same command (`W=<path>; git -C $W ...`) - write the literal path; never feed a `$(...)` result into a "
    "later argument of the same command - run the inner command as its own call and use its literal output in the next "
    "call; and never prefix a command with an inline `VAR=\"$SECRET\"` assignment - rely on the credential the session "
    "environment or the tool's own credential configuration already provides (for `gh`, its stored auth), and never "
    "set a credential per command."
)
RULES = {"merge": MERGE_RULE, "git": GIT_RULE, "shell": SHELL_RULE}

NO_SELF_REVIEW = (
    "- Don't start review or hardening rounds, or launch reviewer subagents, beyond the review gates this brief and "
    "the skills it tells you to load define."
)
ENGINEER_LINES = [
    "- Load and follow `engineering-workflow` for the whole story, from triage, the pre-PR gate and the PR to "
    "`profile.git.integration_branch` to the merge per `profile.review.merge_owner`, the deploy, and the move to "
    "`profile.tracker.states.in_deployment_review`.",
    "- Keep working until everything the brief asks for is done, and only stop to ask when you can't go on without the "
    "coordinator or before a risky step. The stop this brief already defines still holds: if you must stop, hand back "
    "blocked and say why.",
    "- The real-check rule: report a change done only with the output of a real check that exercises it (tests, "
    "type-checker, build, the changed command, or for infrastructure a plan or dry run against the target); a "
    "syntax-only check, or a check that failed to start, does not count.",
    "Install declared dependencies only with the project's own package manager and lockfile, never with sudo or the "
    "system package manager.",
    "If no real check can run, the report names the check not run and why.",
    "- When the work in the brief is done, stop and report.",
    "The tests the real-check rule needs are called for by this brief.",
    NO_SELF_REVIEW,
    "Don't add features, tests, files, docs or refactors the brief or the story's acceptance criteria don't call for.",
    "The pre-PR gate and the review of record that `engineering-workflow` defines stay allowed.",
    "- The engineer never does pre-PR arbitration (`adversarial-review-pipeline` Phase 3, `engineering-workflow` step 4 "
    "Verify stage) or rules a finding valid, invalid or accepted risk or the gate converged (applying the gate's scope "
    "guard is not arbitration), and fixes what QA ruled not met or the adjudicator ruled valid without overturning those "
    "rulings; a separate clean, neutral arbiter on `profile.review.pre_pr.arbiter`, independent of engineer and "
    "coordinator, arbitrates every head.",
    "- The scope rule: the engineer never changes an acceptance criterion on any story (`references/linear.md` "
    "\"Acceptance criteria and scope\").",
    "For both rules the only two exits are a \"Refinement proposal (not an AC)\" or reporting the story blocked, as that "
    "section states.",
    "- The secrets rule (never write secrets to files or argv) and the attribution rule from "
    "`profile.git.ai_attribution`.",
    "- Your own subdirectory of the scratch directory is `{{scratch}}/senior-engineer/`; use it in place of the scratch "
    "directory itself, and never touch another role's files.",
    "- Track your work: before starting, write a fine-grained checklist file at the full path "
    "`{{scratch}}/senior-engineer/senior-engineer-todo.md`",
]
HANDBACK_TAIL = (
    "; or, if it stops, that it is blocked and why, including when no arbiter can launch; a missing arbitration is "
    "never clean or converged."
)
ENGINEER_HANDBACK = {
    "deployed": "- What to hand back: the story state, each PR link, the head SHA each PR's review of record covered, "
    "the merged commit, and the environment and deployed build it verified" + HANDBACK_TAIL,
    "no-deployment": "- What to hand back: the story state, each PR link, the head SHA each PR's review of record "
    "covered, and the merged commit, in place of the environment and deployed build" + HANDBACK_TAIL,
    "spike": "- What to hand back: the story state, each PR link, the head SHA each PR's review of record covered, the "
    "merged commit when there is one, and each deliverable's link, with its commit when one exists, in place of the "
    "environment and deployed build" + HANDBACK_TAIL,
}
SPIKE_MERGE_STEPS = "- The steps from the PR through the merge run only when the spike changes a tracked file."

QA_LINES = [
    "- Load and follow `qa-verification` for the story, including its evidence and its closing status decision.",
    "- What to hand back: the story's final state, the verdict and evidence for each AC and DoD item, any item left "
    "outstanding with its owner, any incidental defect it noted, and each PR it merged with the head SHA its review of "
    "record covered.",
    "- Keep working until everything the brief asks for is done, and only stop to ask when you can't go on without the "
    "coordinator or before a risky step.",
    "The stop this brief already defines still holds: hand back any item left outstanding with its owner.",
    NO_SELF_REVIEW,
    "The pre-PR gate and the review of record that `engineering-workflow` defines, and the evidence PR's review of "
    "record that `qa-verification` defines, stay allowed.",
    "- The secrets rule (never write secrets to files or argv).",
]

SHA = "0123456789abcdef0123456789abcdef01234567"
LINKS = ["https://example.com/spike/report.md", "https://example.com/spike/notes?x=1&y=$W"]

# The AC5 list: the parser accepts exactly these options and nothing else.
ARGUMENTS = {"--role", "--story", "--path", "--scratch", "--round", "--environment", "--commit", "--link"}

SURVIVORS = ["<n>", "`W=<path>; git -C $W ...`", "<full reviewed SHA>", "$W", "`VAR=\"$SECRET\"`", "`$(...)`"]


def load_module():
    spec = importlib.util.spec_from_file_location("render_brief", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def scratch(tmp_path_factory) -> str:
    """A realpath scratch directory with both kinds of role subdirectory, under a pattern-safe base."""
    base = os.path.realpath(tempfile.mkdtemp(prefix="scratch", dir=tmp_path_factory.getbasetemp()))
    for sub in ("senior-engineer", "qa-agent-round-1", "qa-agent-round-2"):
        os.mkdir(os.path.join(base, sub))
    return base


def run(*args: str, script: Path = SCRIPT, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args], capture_output=True, stdin=subprocess.DEVNULL, env=env
    )


def render(*args: str, script: Path = SCRIPT, env: dict | None = None) -> tuple[Path, str]:
    result = run(*args, script=script, env=env)
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    out = result.stdout.decode()
    assert out.endswith("\n") and out.count("\n") == 1, out
    path = Path(out[:-1])
    assert path.is_absolute()
    return path, path.read_text(encoding="utf-8")


def engineer(scratch: str, path: str) -> tuple[Path, str]:
    return render("--role", "engineer", "--story", "ABC-123", "--path", path, "--scratch", scratch)


def qa(scratch: str, path: str, *extra: str, round_: str = "1") -> tuple[Path, str]:
    return render("--role", "qa", "--story", "ABC-123", "--path", path, "--scratch", scratch, "--round", round_, *extra)


def normalize(text: str, scratch: str, skill_dir: Path = SKILL_DIR) -> str:
    """The AC9 sentence-pin normalization: drop `<skill_dir>/`, and write the scratch path as `{{scratch}}`."""
    return text.replace(str(skill_dir.resolve()) + "/", "").replace(scratch, "{{scratch}}")


def all_renders(scratch: str) -> dict[str, tuple[Path, str]]:
    return {
        "engineer-deployed": engineer(scratch, "deployed"),
        "engineer-no-deployment": engineer(scratch, "no-deployment"),
        "engineer-spike": engineer(scratch, "spike"),
        "qa-deployed": qa(scratch, "deployed", "--environment", "dev"),
        "qa-deployed-default": qa(scratch, "deployed", round_="2"),
        "qa-no-deployment": qa(scratch, "no-deployment", "--commit", SHA),
        "qa-spike": qa(scratch, "spike", "--link", LINKS[0], "--link", LINKS[1]),
    }


# A line that quotes a source file and cites it; its backticked references stay as the source states them.
QUOTATION_LINE = re.compile(r" at `[^`]+\.md:\d+`")


@pytest.fixture(scope="module")
def renders(tmp_path_factory) -> dict[str, str]:
    """The seven role/path renders, produced once for the read-only assertions."""
    base = os.path.realpath(tempfile.mkdtemp(prefix="renders", dir=tmp_path_factory.getbasetemp()))
    for sub in ("senior-engineer", "qa-agent-round-1", "qa-agent-round-2"):
        os.mkdir(os.path.join(base, sub))
    return {name: text for name, (_, text) in all_renders(base).items()}


# AC1 Render


@pytest.mark.parametrize("path", ["deployed", "no-deployment", "spike"])
def test_engineer_render_writes_the_derived_file(scratch, path):
    out, text = engineer(scratch, path)
    assert str(out) == f"{scratch}/senior-engineer/senior-engineer-brief.md"
    assert sorted(os.listdir(os.path.join(scratch, "senior-engineer"))) == ["senior-engineer-brief.md"]
    assert "\npath: " + path + "\n" in text
    assert "ABC-123" in text


@pytest.mark.parametrize("round_", ["1", "2"])
def test_qa_render_writes_the_derived_file_for_each_round(scratch, round_):
    out, text = qa(scratch, "deployed", "--environment", "dev", round_=round_)
    assert str(out) == f"{scratch}/qa-agent-round-{round_}/qa-agent-round-{round_}-brief.md"
    assert f"QA round {round_}." in text
    assert f"`{scratch}/qa-agent-round-{round_}/qa-agent-round-{round_}-todo.md`" in text
    others = {"1": "2", "2": "1"}[round_]
    assert os.listdir(os.path.join(scratch, f"qa-agent-round-{others}")) == []
    assert os.listdir(os.path.join(scratch, "senior-engineer")) == []


def test_render_is_byte_identical_and_replaces_an_existing_file(scratch):
    out, first = engineer(scratch, "deployed")
    out.write_text("stale brief\n", encoding="utf-8")
    again, second = engineer(scratch, "deployed")
    assert again == out and second == first
    assert sorted(os.listdir(out.parent)) == ["senior-engineer-brief.md"], "the temp file must not survive"


# AC2 Content


@pytest.mark.parametrize("path", ["deployed", "no-deployment", "spike"])
def test_engineer_brief_carries_every_item_and_its_path_hand_back(scratch, path):
    _, text = engineer(scratch, path)
    text = normalize(text, scratch)
    for line in ENGINEER_LINES:
        assert text.count(line) == 1, line
    for name, handback in ENGINEER_HANDBACK.items():
        assert text.count(handback) == (1 if name == path else 0), name
    assert text.count(SPIKE_MERGE_STEPS) == (1 if path == "spike" else 0)
    assert "qa-agent-round" not in text


def test_qa_brief_names_the_environment_the_engineer_deployed_to(scratch):
    _, text = qa(scratch, "deployed", "--environment", "dev-2")
    assert "- The environment under test: `dev-2`.\n" in text


def test_qa_brief_without_an_environment_names_none(scratch):
    _, text = qa(scratch, "deployed")
    assert "- The environment under test: none is named, so `qa-verification` picks its default.\n" in text
    assert "verification target" not in text


def test_qa_brief_on_no_deployment_names_the_merged_commit(scratch):
    _, text = qa(scratch, "no-deployment", "--commit", SHA)
    assert f"the merged commit `{SHA}` on `profile.git.integration_branch`" in text
    assert "environment under test" not in text


def test_qa_brief_on_spike_lists_each_link_on_its_own_line(scratch):
    _, text = qa(scratch, "spike", "--link", LINKS[0], "--link", LINKS[1])
    assert text.endswith("one per line:\n\n" + LINKS[0] + "\n" + LINKS[1] + "\n")
    assert "environment under test" not in text


@pytest.mark.parametrize("name", ["qa-deployed", "qa-deployed-default", "qa-no-deployment", "qa-spike"])
def test_qa_brief_carries_every_item(scratch, name):
    text = normalize(all_renders(scratch)[name][1], scratch)
    for line in QA_LINES:
        assert text.count(line) == 1, line
    assert "senior-engineer" not in text
    assert "engineering-workflow` for the whole story" not in text


def test_rendered_briefs_hold_no_coordinator_instruction_or_open_token(scratch):
    for name, (_, text) in all_renders(scratch).items():
        for phrase in ["{{", "}}", "which you create and hand it", "the full path you give it", "step 1 selected",
                       "When step 2 did not run", "<scratch>", "<value>", "-<n>-"]:
            assert phrase not in text, (name, phrase)


def test_copied_placeholders_survive_byte_identical(scratch):
    for name, (_, text) in all_renders(scratch).items():
        for survivor in SURVIVORS:
            assert survivor in text, (name, survivor)
        assert "`profile.git.signed_commits`" in text, name


@pytest.mark.parametrize("link", ["https://[::1]/report", "https://user@example.com/x", "https://example.com",
                                  "https://example.com:8443/a?b=c#d"])
def test_any_whitespace_free_https_url_with_a_host_renders(scratch, link):
    _, text = qa(scratch, "spike", "--link", link)
    assert text.endswith("one per line:\n\n" + link + "\n")


def test_token_values_are_not_reexpanded(scratch):
    _, text = qa(scratch, "spike", "--link", "https://example.com/{{story}}/{{round}}")
    assert "https://example.com/{{story}}/{{round}}\n" in text


def test_reference_mentions_are_absolute_and_exist(renders):
    """Navigational mentions are absolutized; a cited quotation keeps its source's literal mention.

    A stray double quote cannot hide a navigational mention: only a cited quotation line is exempt.
    """
    skill_dir = str(SKILL_DIR.resolve())
    for name, text in renders.items():
        navigational = "\n".join(line for line in text.splitlines() if not QUOTATION_LINE.search(line))
        mentions = re.findall(r"`([^`\s]*references/[a-z0-9-]+\.md)`", navigational)
        assert mentions, name
        for mention in mentions:
            assert mention.startswith(skill_dir + "/references/"), (name, mention)
            assert Path(mention).is_file(), mention
        assert "`references/" not in navigational, name


# SKL-410 AC3: every rendered role brief physically carries the permissions its skill grants, quoted
# from that skill with `path:line`, beside the prohibitions the shared rules fragment states.


def permission_summary(role: str) -> str:
    skill = {"engineer": "engineering-workflow", "qa": "qa-verification"}[role]
    return (
        f"- Your permissions, quoted from the skill that governs you, sit beside the prohibitions above: you tick "
        f"the boxes you verified, move the states `{skill}` assigns, open your own PR, and post the review of record."
    )


# The permission each role is granted, with the file that states it. The line number is not pinned here:
# the rendered citation supplies it and `test_every_rendered_citation_...` resolves it against the source,
# so a moved line is reported as moved while a reworded or mis-cited quote still fails.
PERMISSIONS = {
    "engineer": (
        (
            "skills/engineering-workflow/references/linear.md",
            "Ticking the Acceptance Criteria and Definition of Done checkboxes in the description is the completion "
            "record.",
        ),
        (
            "skills/engineering-workflow/references/linear.md",
            "First confirm the only unticked boxes are the items you verified; otherwise patch each verified line "
            "individually.",
        ),
        (
            "skills/engineering-workflow/references/linear.md",
            "Move an issue to in progress the moment its branch is created, before writing code.",
        ),
        (
            "skills/engineering-workflow/references/github.md",
            "Open a PR only once the branch is cleanly based on its target.",
        ),
        (
            "skills/engineering-workflow/SKILL.md",
            "Post the review of record on the PR as one PR review with the comment event (`gh pr review <n> --comment "
            "--body-file <file>`; first line `Review of record <full head SHA>`, then findings, verdict per finding, "
            "fix commit per valid finding, the models used), never as an issue comment, **before** attempting the "
            "merge.",
        ),
    ),
    "qa": (
        ("skills/qa-verification/SKILL.md", "Tick the boxes you verified."),
        (
            "skills/qa-verification/references/linear.md",
            "Ticking the Acceptance Criteria and Definition of Done checkboxes in the description is the completion "
            "record.",
        ),
        (
            "skills/qa-verification/SKILL.md",
            "Ship it through the normal branch and PR flow in `references/github.md`, signed when "
            "`profile.git.signed_commits` is true, and verify the signature after pushing.",
        ),
        (
            "skills/qa-verification/SKILL.md",
            "If `profile.qa.evidence_dir` is unset, the project does not keep in-repo evidence; skip this step and say "
            "so in the report.",
        ),
        (
            "skills/qa-verification/SKILL.md",
            "post the review of record on the PR as a `--comment` PR review before the merge, never after.",
        ),
    ),
}

# The state move each path assigns: the deployed briefs carry the deployed rule, the others the handoff rule.
STATE_MOVES = {
    ("engineer", "deployed"): (
        "skills/engineering-workflow/SKILL.md",
        "Move the story to `profile.tracker.states.in_deployment_review` (never on merge alone).",
    ),
    ("engineer", "no-deployment"): (
        "skills/engineering-workflow/SKILL.md",
        "Move the story to `profile.tracker.states.in_deployment_review`.",
    ),
    ("engineer", "spike"): (
        "skills/engineering-workflow/SKILL.md",
        "Move the story to `profile.tracker.states.in_deployment_review`.",
    ),
    # QA's closing move is one permission on every path; the path fragment beside it names the target that
    # "in the environment" reads as on no-deployment and spike.
    ("qa", "deployed"): (
        "skills/qa-verification/references/linear.md",
        "Once every AC and DoD item is ticked and verified in the environment, move the issue to done.",
    ),
    ("qa", "no-deployment"): (
        "skills/qa-verification/references/linear.md",
        "Once every AC and DoD item is ticked and verified in the environment, move the issue to done.",
    ),
    ("qa", "spike"): (
        "skills/qa-verification/references/linear.md",
        "Once every AC and DoD item is ticked and verified in the environment, move the issue to done.",
    ),
}

# On no-deployment and spike, the closing move's "in the environment" is read as the path's target; the
# interpretation is quoted beside the permission on those two paths only.
INTERPRETATION = (
    "skills/qa-verification/references/linear.md",
    "every condition in this file on a deploy or a deployed environment reads as verification against the "
    "merged commit, or, for a spike with no tracked-file change, against the deliverables the step 12 note links.",
)
PATH_QUOTES = {
    ("qa", "no-deployment"): INTERPRETATION,
    ("qa", "spike"): INTERPRETATION,
}

RENDER_PATH = {
    "engineer-deployed": "deployed",
    "engineer-no-deployment": "no-deployment",
    "engineer-spike": "spike",
    "qa-deployed": "deployed",
    "qa-deployed-default": "deployed",
    "qa-no-deployment": "no-deployment",
    "qa-spike": "spike",
}

# The first line of each role's per-path fragment, so the ordering test can see both sides of the assembly.
PATH_MARKER = {
    "engineer-deployed": ENGINEER_HANDBACK["deployed"],
    "engineer-no-deployment": ENGINEER_HANDBACK["no-deployment"],
    "engineer-spike": SPIKE_MERGE_STEPS,
    "qa-deployed": "- The environment under test: `dev`.",
    "qa-deployed-default": "- The environment under test: none is named, so `qa-verification` picks its default.",
    "qa-no-deployment": f"the merged commit `{SHA}` on `profile.git.integration_branch`",
    "qa-spike": "The verification target, in place of an environment:",
}

PAIR = re.compile(r'"([^"]+)" at `([^`]+\.md):(\d+)`')


def renders_for(role: str, renders: dict[str, str]) -> dict[str, str]:
    return {name: text for name, text in renders.items() if name.startswith(role)}


def assert_cited(name: str, text: str, path: str, quote: str) -> None:
    """The rendered brief carries this exact quote with this exact file, and that file's line states it.

    The line number is read from the rendered citation, never hand-pinned here; a citation rewritten
    into a shape the parser does not read leaves no match, so an independent path check cannot mask it.
    """
    matches = [(found_path, number) for found_quote, found_path, number in PAIR.findall(text)
               if found_quote == quote and found_path == path]
    assert len(matches) == 1, f"{name}: expected one citation of {quote!r} at {path}, found {matches}"
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    number = int(matches[0][1])
    assert quote in lines[number - 1], f"{name}: {path}:{number} does not state {quote!r}"


@pytest.mark.parametrize("role", sorted(PERMISSIONS))
def test_every_rendered_citation_names_the_line_that_carries_its_quote(role, renders):
    """Every parsed citation in the brief resolves against the line it names."""
    for name, text in renders_for(role, renders).items():
        pairs = PAIR.findall(text)
        assert pairs, name
        for quote, path, number in pairs:
            lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
            assert quote in lines[int(number) - 1], f"{name}: {path}:{number} does not state {quote!r}"


@pytest.mark.parametrize("role", sorted(PERMISSIONS))
def test_every_rendered_brief_carries_the_required_permissions(role, renders):
    """Rendered through the real renderer: an absent, reworded or mis-cited permission line fails here."""
    for name, text in renders_for(role, renders).items():
        assert text.count(permission_summary(role)) == 1, name
        for path, quote in PERMISSIONS[role]:
            assert_cited(name, text, path, quote)


@pytest.mark.parametrize("role", sorted(PERMISSIONS))
def test_each_brief_moves_only_the_states_its_path_assigns(role, renders):
    """The engineer's rule is selected by path; QA's closing move is required on every path."""
    for name, text in renders_for(role, renders).items():
        key = (role, RENDER_PATH[name])
        expected_path, quote = STATE_MOVES[key]
        assert_cited(name, text, expected_path, quote)
        if key in PATH_QUOTES:
            assert_cited(name, text, *PATH_QUOTES[key])
        else:
            assert INTERPRETATION[1] not in text, name
        for (other_role, other_path), (_, other_quote) in STATE_MOVES.items():
            if other_role == role and other_path != RENDER_PATH[name] and other_quote != quote:
                assert other_quote not in text, (name, other_quote)


@pytest.mark.parametrize("role", sorted(PERMISSIONS))
def test_the_engineer_brief_grants_the_tick_without_assigning_closure(role, renders):
    """The engineer's skill ends at deployment review, so no engineer brief sets done; QA's closing move stays QA's."""
    for name, text in renders_for(role, renders).items():
        assert "set done in the same act" not in text, name
        if role == "engineer":
            assert "move the issue to done" not in text, name
        else:
            assert "move the issue to done" in text, name


@pytest.mark.parametrize("role", sorted(PERMISSIONS))
def test_role_permissions_sit_beside_the_prohibitions(role, renders):
    """Rules, then permissions, then the path's state move, then the path fragment: the documented order."""
    for name, text in renders_for(role, renders).items():
        # The shared rules are compared as their templates state them, so a resolved reference path is undone.
        text = text.replace(str(SKILL_DIR.resolve()) + "/", "")
        summary = text.index(permission_summary(role))
        for rule in RULES.values():
            assert text.index(rule) < summary, name
        state_quote = STATE_MOVES[(role, RENDER_PATH[name])][1]
        assert summary < text.index(f'"{state_quote}"'), name
        assert text.index(f'"{state_quote}"') < text.index(PATH_MARKER[name]), name


def test_a_stray_quote_cannot_suppress_a_navigational_reference(skill_copy, tmp_path_factory):
    """An unrelated literal quote in one template must not stop the merge rule's reference resolving."""
    rules = skill_copy / "assets" / "brief-rules.md"
    rules.write_text('" an unrelated literal quote\n' + rules.read_text(encoding="utf-8"), encoding="utf-8")
    base = os.path.realpath(tempfile.mkdtemp(prefix="stray", dir=tmp_path_factory.getbasetemp()))
    os.mkdir(os.path.join(base, "senior-engineer"))
    result = run("--role", "engineer", "--story", "ABC-123", "--path", "deployed", "--scratch", base,
                 script=skill_copy / "scripts" / "render-brief.py")
    assert result.returncode == 0, result.stderr
    text = Path(base, "senior-engineer", "senior-engineer-brief.md").read_text(encoding="utf-8")
    assert "`references/" not in text
    assert str(skill_copy.resolve()) + "/references/code-review.md" in text


MIXED_CITATION = '"Tick the boxes you verified." at `skills/qa-verification/SKILL.md:170`'


def append_mixed_line(skill_copy: Path, reference: str) -> None:
    template = skill_copy / "assets" / "brief-engineer.md"
    template.write_text(
        template.read_text(encoding="utf-8") + f"- Review {MIXED_CITATION} in `references/{reference}`.\n",
        encoding="utf-8",
    )


def mixed_scratch(tmp_path_factory) -> Path:
    base = Path(os.path.realpath(tempfile.mkdtemp(prefix="mixed", dir=tmp_path_factory.getbasetemp())))
    (base / "senior-engineer").mkdir()
    return base


def test_a_navigation_beside_a_cited_quotation_still_resolves(skill_copy, tmp_path_factory):
    """Only the cited span is exempt: a reference after it on the same line becomes absolute."""
    append_mixed_line(skill_copy, "code-review.md")
    base = mixed_scratch(tmp_path_factory)
    result = run("--role", "engineer", "--story", "ABC-123", "--path", "deployed", "--scratch", str(base),
                 script=skill_copy / "scripts" / "render-brief.py")
    assert result.returncode == 0, result.stderr
    text = Path(base, "senior-engineer", "senior-engineer-brief.md").read_text(encoding="utf-8")
    assert MIXED_CITATION in text
    assert str(skill_copy.resolve()) + "/references/code-review.md" in text
    assert "`references/" not in text


def test_a_missing_reference_beside_a_cited_quotation_still_fails(skill_copy, tmp_path_factory):
    """A missing navigational reference after a cited span is still refused, with no brief created."""
    append_mixed_line(skill_copy, "no-such-file.md")
    base = mixed_scratch(tmp_path_factory)
    result = run("--role", "engineer", "--story", "ABC-123", "--path", "deployed", "--scratch", str(base),
                 script=skill_copy / "scripts" / "render-brief.py")
    assert result.returncode != 0
    assert result.stdout == b""
    err = result.stderr.decode()
    assert err.endswith("\n") and err.count("\n") == 1, err
    assert "no-such-file.md" in err
    assert not (base / "senior-engineer" / "senior-engineer-brief.md").exists()


# AC3 One source


def test_each_shared_rule_exists_once_across_the_templates_and_once_per_brief(scratch):
    templates = sorted(ASSETS.glob("*.md"))
    assert templates
    for rule in RULES.values():
        assert sum(t.read_text(encoding="utf-8").count(rule) for t in templates) == 1
        assert (ASSETS / "brief-rules.md").read_text(encoding="utf-8").count(rule) == 1
    for name, (_, text) in all_renders(scratch).items():
        text = normalize(text, scratch)
        for rule_name, rule in RULES.items():
            assert text.count(rule) == 1, (name, rule_name)


# AC5 No other content


def test_parser_argument_set_is_the_ac1_list():
    parser = load_module().build_parser()
    options = {s for action in parser._actions for s in action.option_strings}
    assert options == ARGUMENTS
    assert all(action.option_strings for action in parser._actions), "no positional (free text) argument"


def test_script_reads_no_environment_stdin_subprocess_or_network():
    source = SCRIPT.read_text(encoding="utf-8")
    for forbidden in ["os.environ", "getenv", "sys.stdin", "input(", "subprocess", "os.system", "os.popen",
                      "socket", "urllib", "http.client", "yaml", "profile.yaml"]:
        assert forbidden not in source, forbidden
    imports = set(re.findall(r"^(?:from|import) ([a-z_.]+)", source, re.M))
    assert imports <= set(sys.stdlib_module_names) | {"__future__"}, imports


def test_render_ignores_the_environment(scratch):
    _, first = qa(scratch, "deployed", "--environment", "dev")
    env = {"PATH": os.environ.get("PATH", ""), "LANG": "C", "LC_ALL": "C", "TMPDIR": "/nonexistent",
           "PYTHONIOENCODING": "latin-1", "HOME": "/nonexistent"}
    _, second = render("--role", "qa", "--story", "ABC-123", "--path", "deployed", "--scratch", scratch,
                       "--round", "1", "--environment", "dev", env=env)
    assert second == first


# AC9 hash pins, after the {{skill_dir}} and {{scratch}} normalization


def pin(text: str, scratch: str) -> str:
    normalized = text.replace(str(SKILL_DIR.resolve()), "{{skill_dir}}").replace(scratch, "{{scratch}}")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# SKL-357 re-pinned both QA digests for the waiting-handback bullet in brief-qa.md, and pinned the other renders.
# Fixed inputs: story ABC-123, round 1, environment `dev`. SKL-410 re-pinned all six for the role permission
# lines and their per-path state move.
DEPLOYED_QA_SHA256 = "5ee2a2331e38e2887d38361864c9e6587c7dbcced8f93f1f6915a1fba9c2cf9c"
# Fixed inputs: story ABC-123, round 1, the two LINKS above.
SPIKE_QA_SHA256 = "6da5abdbedd48c85e929e54de532557459cbaebd69297f2efa5d88db079d6ef2"
# Fixed inputs: story ABC-123, round 1, commit SHA above.
NO_DEPLOYMENT_QA_SHA256 = "cb1e875107f7823661515ab7d71329c4329a8d9a8bde381a932ac84248242a10"
# Fixed inputs: story ABC-123, one engineer render per path. SKL-346 pinned them for the ledger; SKL-410 re-pinned
# all three for the role permission lines and their per-path state move.
ENGINEER_SHA256 = {
    "deployed": "d98e35ea8a7967087188db4082368c94b46dc201328b7f313cf47b1cf3d16e24",
    "no-deployment": "799469c767290b5ab09a98a3deb04f9524fe1638b6ab74b6aa685a5a09b47225",
    "spike": "0b919ac154f88849c1bca114bc3d062f77c8ce089058a5b1b06d2a91a1121868",
}


@pytest.mark.parametrize("path", sorted(ENGINEER_SHA256))
def test_engineer_render_is_pinned(scratch, path):
    _, text = engineer(scratch, path)
    assert pin(text, scratch) == ENGINEER_SHA256[path]


def test_no_deployment_qa_render_is_pinned(scratch):
    _, text = qa(scratch, "no-deployment", "--commit", SHA)
    assert pin(text, scratch) == NO_DEPLOYMENT_QA_SHA256


def test_deployed_qa_render_is_pinned(scratch):
    _, text = qa(scratch, "deployed", "--environment", "dev")
    assert pin(text, scratch) == DEPLOYED_QA_SHA256


def test_spike_render_with_several_links_is_pinned(scratch):
    _, text = qa(scratch, "spike", "--link", LINKS[0], "--link", LINKS[1])
    assert pin(text, scratch) == SPIKE_QA_SHA256


# AC4 Fail closed

CANARY = "CANARY-7f3a-brief-text"
OLD = b"existing brief, untouched\n"


@pytest.fixture
def skill_copy(tmp_path_factory) -> Path:
    """A copy of the skill whose every template carries a canary string."""
    base = Path(os.path.realpath(tempfile.mkdtemp(prefix="skill", dir=tmp_path_factory.getbasetemp())))
    copy = base / "story-to-done"
    for sub in ("scripts", "assets", "references"):
        shutil.copytree(SKILL_DIR / sub, copy / sub)
    for template in (copy / "assets").glob("*.md"):
        template.write_text(CANARY + "\n" + template.read_text(encoding="utf-8"), encoding="utf-8")
    return copy


def snapshot(root: str) -> dict:
    state = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            full = os.path.join(dirpath, name)
            st = os.lstat(full)
            body = open(full, "rb").read() if os.path.isfile(full) and not os.path.islink(full) else None
            state[full] = (st.st_mode, st.st_mtime_ns, body)
    return state


def seeded_scratch(base: Path) -> str:
    scratch = os.path.realpath(tempfile.mkdtemp(prefix="scratch", dir=base))
    for sub, name in (("senior-engineer", "senior-engineer-brief.md"), ("qa-agent-round-1", "qa-agent-round-1-brief.md")):
        os.mkdir(os.path.join(scratch, sub))
        with open(os.path.join(scratch, sub, name), "wb") as fh:
            fh.write(OLD)
    return scratch


def ok_engineer(scratch: str) -> list[str]:
    return ["--role", "engineer", "--story", "ABC-123", "--path", "deployed", "--scratch", scratch]


def ok_qa(scratch: str, path: str = "deployed") -> list[str]:
    return ["--role", "qa", "--story", "ABC-123", "--path", path, "--scratch", scratch, "--round", "1"]


def with_scratch(args: list[str], value: str) -> list[str]:
    args = list(args)
    args[args.index("--scratch") + 1] = value
    return args


FAILURES = {
    "unknown role": lambda s: ["--role", "boss", "--story", "ABC-123", "--path", "deployed", "--scratch", s],
    "unknown path": lambda s: ["--role", "engineer", "--story", "ABC-123", "--path", "staged", "--scratch", s],
    "unknown argument": lambda s: ok_engineer(s) + ["--model", "x"],
    "abbreviated argument": lambda s: ["--ro", "engineer", "--story", "ABC-123", "--path", "deployed", "--scratch", s],
    "help argument": lambda s: ok_engineer(s) + ["--help"],
    "free text": lambda s: ok_engineer(s) + ["do the work"],
    "repeated argument": lambda s: ok_engineer(s) + ["--story", "ABC-124"],
    "story pattern": lambda s: ["--role", "engineer", "--story", "abc-1", "--path", "deployed", "--scratch", s],
    "story with newline": lambda s: ["--role", "engineer", "--story", "ABC-1\nX", "--path", "deployed", "--scratch", s],
    "round pattern": lambda s: ["--role", "qa", "--story", "ABC-1", "--path", "deployed", "--scratch", s, "--round", "0"],
    "environment pattern": lambda s: ok_qa(s) + ["--environment", "Dev"],
    "environment too long": lambda s: ok_qa(s) + ["--environment", "a" * 64],
    "commit pattern": lambda s: ok_qa(s, "no-deployment") + ["--commit", SHA[:39]],
    "commit uppercase": lambda s: ok_qa(s, "no-deployment") + ["--commit", SHA.upper()],
    "link not https": lambda s: ok_qa(s, "spike") + ["--link", "http://example.com/x"],
    "link with whitespace": lambda s: ok_qa(s, "spike") + ["--link", "https://example.com/a b"],
    "link empty host": lambda s: ok_qa(s, "spike") + ["--link", "https://"],
    "link without host": lambda s: ok_qa(s, "spike") + ["--link", "https://#"],
    "link with userinfo and no host": lambda s: ok_qa(s, "spike") + ["--link", "https://user@/x"],
    "link with port and no host": lambda s: ok_qa(s, "spike") + ["--link", "https://:443/x"],
    "link with empty brackets": lambda s: ok_qa(s, "spike") + ["--link", "https://[]/x"],
    "missing role": lambda s: ["--story", "ABC-123", "--path", "deployed", "--scratch", s],
    "missing story": lambda s: ["--role", "engineer", "--path", "deployed", "--scratch", s],
    "missing path": lambda s: ["--role", "engineer", "--story", "ABC-123", "--scratch", s],
    "missing scratch": lambda s: ["--role", "engineer", "--story", "ABC-123", "--path", "deployed"],
    "qa without round": lambda s: ["--role", "qa", "--story", "ABC-123", "--path", "deployed", "--scratch", s],
    "no-deployment without commit": lambda s: ok_qa(s, "no-deployment"),
    "spike without link": lambda s: ok_qa(s, "spike"),
    "engineer with round": lambda s: ok_engineer(s) + ["--round", "1"],
    "engineer with environment": lambda s: ok_engineer(s) + ["--environment", "dev"],
    "engineer with commit": lambda s: ok_engineer(s) + ["--commit", SHA],
    "engineer with link": lambda s: ok_engineer(s) + ["--link", LINKS[0]],
    "deployed with commit": lambda s: ok_qa(s) + ["--commit", SHA],
    "deployed with link": lambda s: ok_qa(s) + ["--link", LINKS[0]],
    "spike with commit": lambda s: ok_qa(s, "spike") + ["--link", LINKS[0], "--commit", SHA],
    "spike with environment": lambda s: ok_qa(s, "spike") + ["--link", LINKS[0], "--environment", "dev"],
    "no-deployment with link": lambda s: ok_qa(s, "no-deployment") + ["--commit", SHA, "--link", LINKS[0]],
    "no-deployment with environment": lambda s: ok_qa(s, "no-deployment") + ["--commit", SHA, "--environment", "dev"],
    "relative scratch": lambda s: with_scratch(ok_engineer(s), os.path.relpath(s)),
    "scratch pattern": lambda s: with_scratch(ok_engineer(s), s + "/sp ace"),
    "scratch dot component": lambda s: with_scratch(ok_engineer(s), s + "/."),
    "scratch dot-dot component": lambda s: with_scratch(ok_engineer(s), s + "/../" + os.path.basename(s)),
    "scratch trailing slash": lambda s: with_scratch(ok_engineer(s), s + "/"),
    "scratch symlink": lambda s: with_scratch(ok_engineer(s), s + "-link"),
    "role subdirectory symlink": lambda s: with_scratch(ok_engineer(s), s + "-linkedrole"),
    "missing role subdirectory": lambda s: ok_qa(s)[:-1] + ["2"],
    "role subdirectory is a file": lambda s: with_scratch(ok_engineer(s), s + "-filerole"),
    "missing template": lambda s: ok_engineer(s),
    "output path is a directory": lambda s: ok_engineer(s),
    "write failure": lambda s: ok_engineer(s),
}


@pytest.mark.parametrize("case", sorted(FAILURES))
def test_each_failure_exits_with_one_line_and_touches_nothing(case, skill_copy, tmp_path_factory):
    base = Path(os.path.realpath(tempfile.mkdtemp(prefix="fail", dir=tmp_path_factory.getbasetemp())))
    scratch = seeded_scratch(base)
    if case == "scratch symlink":
        os.symlink(scratch, scratch + "-link")
    elif case == "role subdirectory symlink":
        os.mkdir(scratch + "-linkedrole")
        os.symlink(os.path.join(scratch, "senior-engineer"), scratch + "-linkedrole/senior-engineer")
    elif case == "role subdirectory is a file":
        os.mkdir(scratch + "-filerole")
        Path(scratch + "-filerole/senior-engineer").write_bytes(OLD)
    elif case == "missing template":
        (skill_copy / "assets" / "brief-rules.md").unlink()
    elif case == "output path is a directory":
        target = Path(scratch, "senior-engineer", "senior-engineer-brief.md")
        target.unlink()
        target.mkdir()
    before = snapshot(str(base))
    role_dir = os.path.join(scratch, "senior-engineer")
    if case == "write failure":
        # A read-only role subdirectory: the temp file cannot be created (chmod leaves the mtime alone).
        os.chmod(role_dir, 0o555)
    try:
        result = run(*FAILURES[case](scratch), script=skill_copy / "scripts" / "render-brief.py")
    finally:
        os.chmod(role_dir, 0o755)
    assert result.returncode != 0
    assert result.stdout == b""
    err = result.stderr.decode()
    assert err.endswith("\n") and err.count("\n") == 1, err
    assert "Traceback" not in err
    assert CANARY not in err
    assert snapshot(str(base)) == before


@pytest.mark.parametrize("step", ["write", "fsync", "replace"])
def test_a_failure_after_the_temp_file_exists_leaves_the_old_brief_and_no_temp(step, tmp_path_factory, monkeypatch,
                                                                                capsys):
    """The brief is written to a temp file and renamed: a failure at any later step removes the temp file and
    leaves the existing brief byte-identical, so an in-place overwrite or a missing cleanup fails this test."""
    base = Path(os.path.realpath(tempfile.mkdtemp(prefix="atomic", dir=tmp_path_factory.getbasetemp())))
    scratch = seeded_scratch(base)
    before = snapshot(str(base))
    module = load_module()

    def boom(*args, **kwargs):
        raise OSError("injected")

    if step == "write":
        real_fdopen = os.fdopen

        def fdopen(fd, *args, **kwargs):
            handle = real_fdopen(fd, *args, **kwargs)
            handle.write = boom
            return handle

        monkeypatch.setattr(module.os, "fdopen", fdopen)
    else:
        monkeypatch.setattr(module.os, step, boom)
    assert module.main(ok_engineer(scratch)) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err.endswith("\n") and err.count("\n") == 1, err

    # Creating and removing the temp file moves the role directory's own mtime; every entry and byte is unchanged.
    def entries(state: dict) -> dict:
        return {path: value if value[2] is not None else value[0] for path, value in state.items()}

    assert entries(snapshot(str(base))) == entries(before)


def test_a_new_brief_gets_the_umask_mode_and_a_replaced_brief_keeps_its_mode(scratch):
    umask = os.umask(0)
    os.umask(umask)
    out, _ = engineer(scratch, "deployed")
    assert os.stat(out).st_mode & 0o7777 == 0o666 & ~umask
    os.chmod(out, 0o640)
    engineer(scratch, "deployed")
    assert os.stat(out).st_mode & 0o7777 == 0o640


def test_the_canary_reaches_a_successful_render(skill_copy, tmp_path_factory):
    """The canary proves the failure tests would see template text if it leaked."""
    base = Path(os.path.realpath(tempfile.mkdtemp(prefix="ok", dir=tmp_path_factory.getbasetemp())))
    scratch = seeded_scratch(base)
    result = run(*ok_engineer(scratch), script=skill_copy / "scripts" / "render-brief.py")
    assert result.returncode == 0, result.stderr
    assert CANARY not in result.stdout.decode()
    assert CANARY in Path(scratch, "senior-engineer", "senior-engineer-brief.md").read_text(encoding="utf-8")
