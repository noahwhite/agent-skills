"""SKL-162 and SKL-282: engineering-workflow's run paths (spike, no-deployment, deployed).

SKL-162 selects exactly one path in step 1; SKL-282 hands the no-deployment and spike paths off to
deployment review in steps 11 and 12 without a deploy.
"""

import hashlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "engineering-workflow" / "SKILL.md"


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    rest = text[match.end():]
    following = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


def step_one_lines() -> list[str]:
    return section(SKILL.read_text(encoding="utf-8"), "1. Triage the story").splitlines()


# Each normative sentence of the step 1 path selection, pinned whole on its own line, so a
# deleted or reworded sentence fails exactly one test id.
PINS = {
    "triage-item": '6. Select the run\'s path as "Select the path" below states, before any later step runs.',
    "move-after-path": "7. Move it to `profile.tracker.states.in_progress` and read it back to confirm.",
    "subsection": "### Select the path",
    "three-paths": "A run follows exactly one path: `spike`, `no-deployment` or `deployed`.",
    "brief-governs": (
        "When a brief states the path, that path governs: no ask case applies and you never reselect it."
    ),
    "select-before-later-steps": (
        "When no brief states a path, select exactly one path before any later step runs."
    ),
    "ask-intro": "Ask the user for the path, and run no later step until answered, in exactly these cases:",
    "ask-environments-absent": "- `profile.environments` is absent (an absent key is never read as `[]`);",
    "ask-no-integration-entry": (
        "- `profile.environments` is non-empty and no entry's `branch` equals `profile.git.integration_branch`;"
    ),
    "ask-spike-title-no-label": (
        "- the story title starts with `[Spike]` and the story lacks the spike label "
        "(including when `profile.tracker.labels.spike` is unset);"
    ),
    "ask-spike-label-no-title": (
        "- the story carries the spike label and its title does not start with `[Spike]`."
    ),
    "ask-precedence": "An ask case takes precedence over the selection conditions below.",
    "ask-answer-is-path": (
        "The answer is one of `spike`, `no-deployment` or `deployed`, and it is the path: "
        "it replaces the selection below."
    ),
    "no-inference": "Never infer a path from prose, and ask nothing else about the path.",
    "select-intro": "Otherwise select:",
    "select-spike": (
        "- `spike` when the story carries the label named by `profile.tracker.labels.spike`, looked up on the "
        "story's team under the differing-team rule in [references/linear.md](references/linear.md) "
        '"Team resolution";'
    ),
    "select-no-deployment": (
        "- otherwise `no-deployment` when `profile.environments` is present and is `[]`;"
    ),
    "select-deployed": (
        "- otherwise `deployed` when `profile.environments` has an entry whose `branch` equals "
        "`profile.git.integration_branch`."
    ),
    "path-governs-run": "The selected path governs the whole run.",
}


@pytest.mark.parametrize("pin", list(PINS.values()), ids=list(PINS))
def test_step_one_pins_path_selection_sentence(pin: str) -> None:
    assert pin in step_one_lines(), f"step 1 must read the pinned sentence exactly: {pin}"


ASK_CASES = ("ask-environments-absent", "ask-no-integration-entry", "ask-spike-title-no-label", "ask-spike-label-no-title")
SELECTIONS = ("select-spike", "select-no-deployment", "select-deployed")


def block_after(lines: list[str], intro: str) -> list[str]:
    """The bullet lines that directly follow ``intro``, after any blank lines."""
    assert intro in lines, f"missing block intro: {intro}"
    start = lines.index(intro) + 1
    while start < len(lines) and not lines[start].strip():
        start += 1
    block = []
    for line in lines[start:]:
        if not line.startswith("- "):
            break
        block.append(line)
    return block


def test_ask_cases_are_exactly_the_four_named_cases() -> None:
    lines = step_one_lines()
    assert block_after(lines, PINS["ask-intro"]) == [PINS[key] for key in ASK_CASES]


def test_selection_conditions_are_ordered_spike_then_no_deployment_then_deployed() -> None:
    lines = step_one_lines()
    assert block_after(lines, PINS["select-intro"]) == [PINS[key] for key in SELECTIONS]


def test_ask_cases_come_before_the_selection_they_take_precedence_over() -> None:
    lines = step_one_lines()
    assert lines.index(PINS["ask-intro"]) < lines.index(PINS["ask-precedence"]) < lines.index(PINS["select-intro"])


TRACKER_FALLBACK = "If the tracker cannot be updated, stop and say the transition was not performed; never claim it was."
SUBSECTION_ORDER = (
    "subsection",
    "three-paths",
    "brief-governs",
    "select-before-later-steps",
    "ask-intro",
    *ASK_CASES,
    "ask-precedence",
    "ask-answer-is-path",
    "no-inference",
    "select-intro",
    *SELECTIONS,
    "path-governs-run",
)


def test_path_is_selected_before_the_story_moves_to_in_progress() -> None:
    lines = step_one_lines()
    assert lines.index(PINS["triage-item"]) + 1 == lines.index(PINS["move-after-path"])


# Step 1 holds no unpinned addition: its non-blank lines other than the pins hash to the base
# commit 7ae1b94 step 1 without its "6. Move it to ..." line, which "move-after-path" renumbers.
STEP_ONE_UNPINNED_SHA256 = "7d5d8ebe33801124a58a20739cfa5885c552f62eceac0ca050cdcd22bad8a901"


def test_step_one_has_no_unpinned_line() -> None:
    pins = set(PINS.values())
    rest = [line for line in step_one_lines() if line.strip() and line not in pins]
    assert hashlib.sha256("\n".join(rest).encode()).hexdigest() == STEP_ONE_UNPINNED_SHA256


def test_subsection_directly_follows_the_tracker_fallback_paragraph() -> None:
    lines = step_one_lines()
    assert lines.index(PINS["subsection"]) == lines.index(TRACKER_FALLBACK) + 2


def test_subsection_holds_only_the_pinned_sentences_in_order() -> None:
    lines = step_one_lines()
    body = [line for line in lines[lines.index(PINS["subsection"]):] if line.strip()]
    assert body == [PINS[key] for key in SUBSECTION_ORDER]


# AC3: the path selection lives in step 1 only; no pinned sentence appears in any later step.
@pytest.mark.parametrize("key", list(PINS), ids=list(PINS))
def test_path_selection_sentence_appears_only_in_step_one(key: str) -> None:
    lines = SKILL.read_text(encoding="utf-8").splitlines()
    assert lines.count(PINS[key]) == 1, f"{key} must appear exactly once in the skill"


# SKL-282: steps 11 and 12 hand a `no-deployment` or `spike` run off to deployment review without a
# deploy, and a spike with no tracked-file change skips steps 4 to 10.
# Each normative sentence SKL-282 adds, pinned whole on its own line within its step, so a deleted
# or reworded sentence fails its own test id.
SPIKE_NO_CHANGE_PINS = {
    "spike-subsection": "### Spike with no tracked-file change",
    "spike-three-checks": (
        "On the `spike` path, before step 4, fetch `origin`, confirm the checkout is on the spike's branch "
        "(`git branch --show-current` names it) and that the branch contains every commit of "
        "`origin/<profile.git.integration_branch>` (`git rev-list --count "
        "HEAD..origin/<profile.git.integration_branch>` prints `0`; otherwise update the branch first), and "
        "check for a tracked-file change in the working tree (`git diff --name-only`), the index "
        "(`git diff --cached --name-only`) and the commits relative to `origin/<profile.git.integration_branch>` "
        "(`git diff --name-only origin/<profile.git.integration_branch>...HEAD`)."
    ),
    "spike-no-hidden-changes": (
        "A stash or a file marked assume-unchanged or skip-worktree hides a tracked-file change from those "
        "checks, so `git stash list` must print no entry made on the spike's branch (one that reads "
        "`WIP on <branch>:` or `On <branch>:`), and `git ls-files -v` must print no line whose tag is a "
        "lowercase letter (assume-unchanged) or `S` (skip-worktree)."
    ),
    "spike-check-failure-stops": (
        "A failed fetch, or a `git` command above that exits non-zero, never reads as no tracked-file change: "
        "stop and resolve it before deciding."
    ),
    "spike-skip-and-recheck": (
        "Skip steps 4 to 10 only when all three checks show no tracked-file change, and repeat the fetch, the "
        "branch confirmations and every check immediately before step 12."
    ),
    "spike-untracked-deliverable": (
        "An untracked file is not a tracked-file change, so a deliverable that exists only as an untracked "
        "file is linked on the story as an attachment, and the step 12 note says it had no PR review or CI "
        "check."
    ),
    "spike-deliverable-no-secret": (
        "Before you link any deliverable on the story, as a comment or an attachment, confirm it holds no "
        "secret."
    ),
    "spike-change-runs-gates": (
        "If a tracked-file change appears at any point, complete steps 4 to 10 with every applicable gate, and "
        "the merge path of step 12 applies."
    ),
    "spike-merge-path-sticks": (
        "Once a tracked-file change has appeared, the spike stays on that merge path and the checks are not "
        "repeated, so a merged spike is never sent back through steps 4 to 10."
    ),
    "spike-pr-gates-unchanged": (
        "Any PR a spike produces runs every gate steps 4 to 10 define: the `spike` path changes no gate, "
        "waiver, admin override or expected-head condition."
    ),
}
STEP_ELEVEN_PINS = {
    "deploy-deployed-only": "This step runs on the `deployed` path only.",
    "deploy-skipped": "On the `no-deployment` and `spike` paths, skip it: claim no deploy and verify none.",
    "steps-through-merge-unchanged": (
        "Every step up to and including the merge runs on those two paths as on the `deployed` path, except "
        'steps 4 to 10 when the "Spike with no tracked-file change" subsection lets a spike skip them.'
    ),
}
STEP_TWELVE_PINS = {
    "deployed-conditions-scoped": (
        '"Only after the deployment is verified", its "(never on merge alone)" parenthetical and the Done '
        "sentence above apply to the `deployed` path only."
    ),
    "handoff-subsection": "### Handoff on the `no-deployment` and `spike` paths",
    "handoff-merged-commit-defined": (
        "The merged commit is the commit that merging this story's PR in step 10 put on the integration "
        "branch, as `profile.git.merge_method` produced it: the merge commit, the squash commit or the last "
        "rebased commit, which `gh pr view <PR number> --json mergeCommit --jq .mergeCommit.oid` prints."
    ),
    "handoff-after-merge": (
        "Run this step once a fetch of `origin` shows the merged commit on "
        "`origin/<profile.git.integration_branch>` (`git merge-base --is-ancestor <merged commit> "
        "origin/<profile.git.integration_branch>` exits 0) and the story's change is still present there: in a "
        "detached worktree of `origin/<profile.git.integration_branch>`, `git apply --check --reverse` of the "
        "diff `gh pr diff <PR number>` prints exits 0."
    ),
    "handoff-reverted-stops": (
        "When it exits non-zero, stop and report that the story's change is not intact on "
        "`origin/<profile.git.integration_branch>`."
    ),
    "handoff-spike-no-change": (
        "For a spike with no tracked-file change, run it instead once the checks repeated immediately before "
        "this step still show no tracked-file change and each deliverable is linked on the story as a comment "
        "or an attachment."
    ),
    "handoff-note": "1. Add a concise implementation and handoff note naming the path and the merged commit.",
    "handoff-note-no-change": (
        "   For a spike with no tracked-file change, the note names the path, states there is no merged commit, "
        "and says the spike had no tracked-file change and that steps 4 to 10 were skipped."
    ),
    "handoff-note-deliverables": (
        "   On `spike`, the note also names, for each deliverable the spike's Deliverables section lists, its "
        "link and, when the deliverable is a tracked artifact, its commit on "
        "`origin/<profile.git.integration_branch>`."
    ),
    "handoff-move": "2. Move the story to `profile.tracker.states.in_deployment_review`.",
    "handoff-state-absent": (
        "   If the profile sets no `in_deployment_review` state, stop and say the transition was not "
        "performed; never invent a state name."
    ),
    "handoff-read-back": "3. Read the story back to confirm the state.",
    "handoff-done-merged-commit": (
        "Done comes later, after the acceptance criteria are verified against the merged commit, not in a "
        "deployed environment (see `references/linear.md`)."
    ),
    "handoff-done-deliverables": (
        "For a spike with no tracked-file change, Done comes later, after the acceptance criteria are verified "
        "against the deliverables the step 12 note links."
    ),
}
HANDOFF_PINS = {
    **SPIKE_NO_CHANGE_PINS,
    **STEP_ELEVEN_PINS,
    **STEP_TWELVE_PINS,
}
HANDOFF_SECTIONS = {
    **dict.fromkeys(SPIKE_NO_CHANGE_PINS, "3. TDD per slice"),
    **dict.fromkeys(STEP_ELEVEN_PINS, "11. Deploy and verify"),
    **dict.fromkeys(STEP_TWELVE_PINS, "12. Deployment review"),
}


@pytest.mark.parametrize("key", list(HANDOFF_PINS), ids=list(HANDOFF_PINS))
def test_handoff_pins_sentence_in_its_step(key: str) -> None:
    lines = section(SKILL.read_text(encoding="utf-8"), HANDOFF_SECTIONS[key]).splitlines()
    heading = STEP_TWELVE_PINS["handoff-subsection"]
    if key in STEP_TWELVE_PINS and key not in ("deployed-conditions-scoped", "handoff-subsection"):
        # The handoff list repeats the `deployed` read-back line, so these pins are looked up only
        # below the handoff subsection heading.
        assert heading in lines, "step 12 must hold the handoff subsection"
        lines = lines[lines.index(heading):]
    assert HANDOFF_PINS[key] in lines, f"step {HANDOFF_SECTIONS[key]} must read the pinned sentence: {key}"


def added_blocks() -> list[str]:
    """The exact text SKL-282 inserts into steps 3, 11 and 12, built from the pins in order."""
    p = HANDOFF_PINS
    spike = (
        f"{p['spike-subsection']}\n\n{p['spike-three-checks']}\n{p['spike-no-hidden-changes']}\n"
        f"{p['spike-check-failure-stops']}\n{p['spike-skip-and-recheck']}\n{p['spike-untracked-deliverable']}\n"
        f"{p['spike-deliverable-no-secret']}\n{p['spike-change-runs-gates']}\n{p['spike-merge-path-sticks']}\n{p['spike-pr-gates-unchanged']}\n\n"
    )
    eleven = f"{p['deploy-deployed-only']}\n{p['deploy-skipped']}\n{p['steps-through-merge-unchanged']}\n\n"
    twelve = (
        f"\n{p['deployed-conditions-scoped']}\n\n{p['handoff-subsection']}\n\n"
        f"{p['handoff-merged-commit-defined']}\n{p['handoff-after-merge']}\n{p['handoff-reverted-stops']}\n"
        f"{p['handoff-spike-no-change']}\n\n"
        f"{p['handoff-note']}\n{p['handoff-note-no-change']}\n{p['handoff-note-deliverables']}\n"
        f"{p['handoff-move']}\n{p['handoff-state-absent']}\n{p['handoff-read-back']}\n\n"
        f"{p['handoff-done-merged-commit']}\n{p['handoff-done-deliverables']}\n"
    )
    return [spike, eleven, twelve]


# SKL-282 replaced SKL-162's `test_steps_two_to_twelve_are_unchanged`, which hashed steps 2 to 12
# whole against the base commit 7ae1b94 and so failed on any edit, including the step 3, 11 and 12
# additions SKL-282 is in scope to make. Its coverage is kept, not loosened: the same digest of the
# same text still has to match once the three SKL-282 blocks are cut out, so every pre-existing
# sentence of steps 2 to 12 (the `deployed` path text of steps 11 and 12 included) must stay byte for
# byte as it was, and the blocks themselves are kept whole and in order by the pins in
# `HANDOFF_PINS` and `test_handoff_blocks_appear_once_in_order`.
STEPS_TWO_TO_TWELVE_SHA256 = "a36c006733b7b3bc23d65530faee575a02b5e59c1b8c68d48d7657fcf639f2c3"


def steps_two_to_twelve() -> str:
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("\n## 2. Plan slices\n") + 1
    end = text.index("\n## Operational rules\n") + 1
    return text[start:end]


def test_handoff_blocks_appear_once_in_order() -> None:
    text = steps_two_to_twelve()
    positions = []
    for block in added_blocks():
        assert text.count(block) == 1, f"the SKL-282 block must appear exactly once, whole:\n{block}"
        positions.append(text.index(block))
    assert positions == sorted(positions)


def test_steps_two_to_twelve_outside_the_handoff_blocks_are_unchanged() -> None:
    text = steps_two_to_twelve()
    for block in added_blocks():
        text = text.replace(block, "", 1)
    assert hashlib.sha256(text.encode()).hexdigest() == STEPS_TWO_TO_TWELVE_SHA256


# SKL-282: the lifecycle rules in `references/linear.md` (vendored from `shared/linear.md`) govern
# step 12, so they scope their deploy conditions for the `no-deployment` and `spike` handoff.
LINEAR_HANDOFF_PINS = {
    "linear-handoff": (
        "- On the `no-deployment` and `spike` paths that `engineering-workflow` selects in its step 1, nothing "
        "is deployed: the move to deployment review follows the handoff its step 12 defines, and every "
        "condition in this file on a deploy or a deployed environment reads as verification against the "
        "merged commit, or, for a spike with no tracked-file change, against the deliverables the step 12 note "
        "links."
    ),
    "linear-handoff-no-pr": (
        "  A spike with no tracked-file change has no PR, so for it every condition in this file on a merged PR "
        "reads as the deliverables the step 12 note links."
    ),
}
LINEAR_FILES = {
    "shared": ROOT / "shared" / "linear.md",
    "engineering-workflow": ROOT / "skills" / "engineering-workflow" / "references" / "linear.md",
}


@pytest.mark.parametrize("copy", list(LINEAR_FILES))
@pytest.mark.parametrize("key", list(LINEAR_HANDOFF_PINS))
def test_linear_lifecycle_scopes_deploy_conditions_to_the_deployed_path(key: str, copy: str) -> None:
    lines = section(LINEAR_FILES[copy].read_text(encoding="utf-8"), "Status lifecycle").splitlines()
    assert LINEAR_HANDOFF_PINS[key] in lines
