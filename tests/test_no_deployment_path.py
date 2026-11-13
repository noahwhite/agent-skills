"""SKL-162, SKL-282 and SKL-269: the run paths (spike, no-deployment, deployed).

SKL-162 selects exactly one path in engineering-workflow step 1; SKL-282 hands the no-deployment and
spike paths off to deployment review in steps 11 and 12 without a deploy; SKL-269 has qa-verification
apply the same path conditions and verify those two paths without a deployed environment.
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
# commit 7ae1b94 step 1 without its "6. Move it to ..." line, which "move-after-path" renumbers, and with
# SKL-237's unestimated-type reading of the two "refined and pointed" lines (tests/test_story_refinement.py).
STEP_ONE_UNPINNED_SHA256 = "5b947c13a751f6608d794f636f864b0b5fdc82ffb13b986f2c4054c55f930222"


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
    # `handoff-after-merge` pins exactly AC1's condition: the merged commit confirmed on the
    # integration branch after a fetch (ancestry check only). It replaces an earlier pin of the same id
    # that also required the story's change to still be in effect on that branch, and the
    # `handoff-reverted-stops` pin that stopped the handoff when it was not. Both were dropped by the
    # owner's scope ruling on PR 224 (option (b)): that check went beyond AC1 and drew a new valid
    # finding in each of six review rounds. AC1's coverage is kept by this pin together with
    # `handoff-merged-commit-defined` and `test_handoff_blocks_appear_once_in_order`.
    "handoff-after-merge": (
        "Run this step once a fetch of `origin` shows the merged commit on "
        "`origin/<profile.git.integration_branch>` (`git merge-base --is-ancestor <merged commit> "
        "origin/<profile.git.integration_branch>` exits 0)."
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
        f"{p['handoff-merged-commit-defined']}\n{p['handoff-after-merge']}\n"
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


# SKL-269: qa-verification applies the same path conditions as engineering-workflow step 1 and
# verifies the `no-deployment` and `spike` paths against a target other than a deployed environment.
# Each new sentence is pinned whole on its own line within its section, so a deleted or reworded
# sentence fails its own test id. No existing pin is replaced.
QA_SKILL = ROOT / "skills" / "qa-verification" / "SKILL.md"

QA_DESCRIPTION_PINS = {
    "qa-description": (
        "  Also verifies a spike, or a story whose profile has no deployed environment, against its merged "
        "commit or its deliverables."
    ),
}
QA_INTRO_PINS = {
    "qa-intro-deployed-path": (
        "The deployed story, live environment and deployed behavior above belong to the `deployed` path, one "
        'of the three paths "The run\'s path" below defines.'
    ),
    "qa-intro-other-paths": (
        "On the `no-deployment` and `spike` paths, QA verifies the AC and DoD against the path's target that "
        '"The environment under test" names, without a live environment.'
    ),
    "qa-intro-committed-artifacts": (
        "There, inspecting committed artifacts for acceptance is permitted, and it does not replace the "
        "code-review gates."
    ),
    "qa-intro-brief": (
        "A delegated QA agent's brief may also state the run's path, and on the `no-deployment` and `spike` "
        "paths it names that path's target in place of the environment."
    ),
}
# The path conditions use the wording of engineering-workflow step 1 (`PINS`), except the two
# sentences that name what waits on the path: QA runs no verification and tests nothing until then.
# The shared values are taken from `PINS` on purpose, since AC1 asks for the same wording: a change
# to one of those engineering-workflow sentences must be made in qa-verification in the same change.
QA_PATH_PINS = {
    "qa-path-section": "## The run's path",
    "qa-three-paths": PINS["three-paths"],
    "qa-brief-governs": PINS["brief-governs"],
    "qa-select-before-verification": (
        "When no brief states a path, select exactly one path before any verification runs."
    ),
    "qa-ask-intro": "Ask the user for the path, and test nothing until answered, in exactly these cases:",
    **{f"qa-{key}": PINS[key] for key in ASK_CASES},
    "qa-ask-precedence": PINS["ask-precedence"],
    "qa-ask-answer-is-path": PINS["ask-answer-is-path"],
    "qa-no-inference": PINS["no-inference"],
    "qa-select-intro": PINS["select-intro"],
    **{f"qa-{key}": PINS[key] for key in SELECTIONS},
    "qa-path-governs-run": PINS["path-governs-run"],
}
QA_ENV_PINS = {
    "qa-env-other-paths": (
        "On the `no-deployment` and `spike` paths, QA chooses no environment and confirms no deployed build: "
        "every bullet above except the QA credentials bullet applies to the `deployed` path only, and QA "
        "verifies against the path's target instead:"
    ),
    "qa-env-target-no-deployment": (
        "- `no-deployment`: the target is the merged commit the `engineering-workflow` step 12 note names, "
        "confirmed on `profile.git.integration_branch` (after a fetch of `origin`, `git merge-base "
        "--is-ancestor <merged commit> origin/<profile.git.integration_branch>` exits 0); if it is not there, "
        "stop: the story is not yet testable, and it stays in `profile.tracker.states.in_deployment_review`."
    ),
    "qa-env-target-spike": (
        "- `spike`: the target is each deliverable the `engineering-workflow` step 12 note links, read at its "
        "commit on `profile.git.integration_branch` when it has one."
    ),
    "qa-env-record-no-deployment": "On `no-deployment`, record the merged commit SHA.",
    "qa-env-record-spike": (
        "On `spike`, record each deliverable's link and its commit SHA when one exists, or record that the "
        "deliverable has no commit."
    ),
    "qa-env-no-environment": (
        "Neither path requires or records an environment or a deployed build SHA; where a later step records "
        "the build SHA, the environment or the fixtures (the step 4 evidence comment, the step 5 evidence "
        "`README.md` and the completion summary), record the path and the target records above instead."
    ),
    "qa-env-dependency-rule": (
        "On both paths, every later condition on a deploy, a deployed build or the environment under test "
        "reads as the path's target, so step 1's dependency status rule verifies an item directly only when "
        "its dependency is in `profile.tracker.states.in_deployment_review` or `profile.tracker.states.done` "
        "and its change is contained in the target, and flags it blocked otherwise."
    ),
    "qa-env-containment": (
        "A dependency's change is contained in the target when its merged commit is an ancestor of the target "
        "commit (`git merge-base --is-ancestor <dependency merged commit> <target commit>` exits 0); when the "
        "target or the dependency has no commit, such as a spike deliverable, the change is contained only "
        "when the target links the dependency's merged commit or, for a dependency with no commit, each "
        "deliverable the dependency's `engineering-workflow` step 12 note links."
    ),
    "qa-env-no-lanes": (
        "On both paths, steps 2 and 3 apply to the `deployed` path only, except step 3's rule on mutating "
        "confirms (its item 3), which applies on every path: QA verifies each AC and DoD item by "
        "inspecting the target (the committed artifacts, or a deliverable linked as a comment or an "
        "attachment), and the item's evidence is the commands QA ran with their output, or the deliverable it "
        "read; no screenshot is required."
    ),
    "qa-env-dod-not-needed": (
        'On both paths, rule the DoD line "Verified in a deployed environment (if needed)" not needed with the '
        "verdict correct by design, giving the path as the reason, count it as met for step 6 and tick that box."
    ),
}
QA_PINS = {**QA_DESCRIPTION_PINS, **QA_INTRO_PINS, **QA_PATH_PINS, **QA_ENV_PINS}
# The pin inventory, listed apart from the pins so a pinned sentence cannot be dropped together with
# its pin and its block entry while the suite stays green.
QA_PIN_KEYS = (
    "qa-description",
    "qa-intro-deployed-path",
    "qa-intro-other-paths",
    "qa-intro-committed-artifacts",
    "qa-intro-brief",
    "qa-path-section",
    "qa-three-paths",
    "qa-brief-governs",
    "qa-select-before-verification",
    "qa-ask-intro",
    "qa-ask-environments-absent",
    "qa-ask-no-integration-entry",
    "qa-ask-spike-title-no-label",
    "qa-ask-spike-label-no-title",
    "qa-ask-precedence",
    "qa-ask-answer-is-path",
    "qa-no-inference",
    "qa-select-intro",
    "qa-select-spike",
    "qa-select-no-deployment",
    "qa-select-deployed",
    "qa-path-governs-run",
    "qa-env-other-paths",
    "qa-env-target-no-deployment",
    "qa-env-target-spike",
    "qa-env-record-no-deployment",
    "qa-env-record-spike",
    "qa-env-no-environment",
    "qa-env-dependency-rule",
    "qa-env-containment",
    "qa-env-no-lanes",
    "qa-env-dod-not-needed",
)


def test_qa_pin_inventory_is_complete() -> None:
    assert tuple(QA_PINS) == QA_PIN_KEYS


def text_between(text: str, start: str, end: str) -> str:
    """The text from ``start`` up to ``end``, failing with the missing marker named."""
    assert start in text, f"missing marker: {start!r}"
    begin = text.index(start)
    assert end in text[begin:], f"missing marker after {start!r}: {end!r}"
    return text[begin : text.index(end, begin)]


def qa_description_lines() -> list[str]:
    return text_between(QA_SKILL.read_text(encoding="utf-8"), "\ndescription: >-\n", "\nlicense: ").splitlines()


def qa_intro_lines() -> list[str]:
    return text_between(QA_SKILL.read_text(encoding="utf-8"), "\n# QA verification\n", "\n## Read first\n").splitlines()


def qa_path_lines() -> list[str]:
    text = QA_SKILL.read_text(encoding="utf-8")
    return [QA_PATH_PINS["qa-path-section"], *section(text, "The run's path").splitlines()]


def qa_env_lines() -> list[str]:
    return section(QA_SKILL.read_text(encoding="utf-8"), "The environment under test").splitlines()


QA_SECTION_LINES = {
    **dict.fromkeys(QA_DESCRIPTION_PINS, qa_description_lines),
    **dict.fromkeys(QA_INTRO_PINS, qa_intro_lines),
    **dict.fromkeys(QA_PATH_PINS, qa_path_lines),
    **dict.fromkeys(QA_ENV_PINS, qa_env_lines),
}


@pytest.mark.parametrize("key", list(QA_PINS), ids=list(QA_PINS))
def test_qa_pins_sentence_in_its_section(key: str) -> None:
    assert QA_PINS[key] in QA_SECTION_LINES[key](), f"qa-verification must read the pinned sentence: {key}"


def test_qa_ask_cases_and_selection_use_the_engineering_workflow_wording() -> None:
    lines = qa_path_lines()
    assert block_after(lines, QA_PATH_PINS["qa-ask-intro"]) == [PINS[key] for key in ASK_CASES]
    assert block_after(lines, QA_PATH_PINS["qa-select-intro"]) == [PINS[key] for key in SELECTIONS]


# The path section is closed on purpose: a sentence added to it must be added to `QA_PATH_PINS` too,
# so every rule that decides the path is pinned.
def test_qa_path_section_holds_only_the_pinned_sentences_in_order() -> None:
    assert [line for line in qa_path_lines() if line.strip()] == list(QA_PATH_PINS.values())


def test_qa_path_section_comes_before_the_environment_section() -> None:
    text = QA_SKILL.read_text(encoding="utf-8")
    assert "\n## The environment under test\n" in text_between(
        text, "\n## The run's path\n", "\n## 1. Read the story and enumerate what to verify\n"
    )


def test_qa_targets_are_exactly_the_two_paths() -> None:
    assert block_after(qa_env_lines(), QA_ENV_PINS["qa-env-other-paths"]) == [
        QA_ENV_PINS["qa-env-target-no-deployment"],
        QA_ENV_PINS["qa-env-target-spike"],
    ]


def qa_added_blocks() -> list[str]:
    """The exact text SKL-269 inserts into qa-verification, built from the pins in order."""
    description = f"{QA_DESCRIPTION_PINS['qa-description']}\n"
    intro = "".join(f"{line}\n" for line in QA_INTRO_PINS.values())
    p = QA_PATH_PINS
    asks = "".join(f"{p[f'qa-{key}']}\n" for key in ASK_CASES)
    selections = "".join(f"{p[f'qa-{key}']}\n" for key in SELECTIONS)
    path = (
        f"{p['qa-path-section']}\n\n{p['qa-three-paths']}\n{p['qa-brief-governs']}\n"
        f"{p['qa-select-before-verification']}\n\n{p['qa-ask-intro']}\n\n{asks}\n"
        f"{p['qa-ask-precedence']}\n{p['qa-ask-answer-is-path']}\n{p['qa-no-inference']}\n\n"
        f"{p['qa-select-intro']}\n\n{selections}\n{p['qa-path-governs-run']}\n\n"
    )
    e = QA_ENV_PINS
    env = (
        f"\n{e['qa-env-other-paths']}\n\n{e['qa-env-target-no-deployment']}\n{e['qa-env-target-spike']}\n\n"
        f"{e['qa-env-record-no-deployment']}\n{e['qa-env-record-spike']}\n{e['qa-env-no-environment']}\n"
        f"{e['qa-env-dependency-rule']}\n{e['qa-env-containment']}\n{e['qa-env-no-lanes']}\n{e['qa-env-dod-not-needed']}\n"
    )
    return [description, intro, path, env]


def test_qa_added_blocks_appear_once_in_order() -> None:
    text = QA_SKILL.read_text(encoding="utf-8")
    positions = []
    for block in qa_added_blocks():
        assert text.count(block) == 1, f"the SKL-269 block must appear exactly once, whole:\n{block}"
        positions.append(text.index(block))
    assert positions == sorted(positions)


# The `deployed` text is unchanged: with the four SKL-269 blocks cut out, qa-verification's
# SKILL.md is byte for byte the file at the base commit f9b6659.
# A later story that changes qa-verification's SKILL.md outside these blocks re-baselines this hash
# to the sha256 of the file at its own base with these blocks cut out, and says so in its PR.
QA_BASE_SHA256 = "4cbac447bd45659c82eef922306bda26824f657591b1c5cddceea8e14c10427d"


def test_qa_text_outside_the_added_blocks_is_unchanged() -> None:
    text = QA_SKILL.read_text(encoding="utf-8")
    for block in qa_added_blocks():
        text = text.replace(block, "", 1)
    assert hashlib.sha256(text.encode()).hexdigest() == QA_BASE_SHA256
