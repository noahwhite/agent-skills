"""SKL-75: one-pass-producible evidence in filed acceptance criteria.

The filing rule lives in shared/linear.md ("Acceptance criteria and scope") and the
filing skills cite it in rules prose. Each pinned sentence is matched per source
line after stripping the leading "- ", so deleting any one fails exactly one test.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SHARED_LINEAR = ROOT / "shared" / "linear.md"
USER_STORY_SKILL = ROOT / "skills" / "linear-user-story" / "SKILL.md"
BUG_SKILL = ROOT / "skills" / "linear-bug" / "SKILL.md"
SPIKE_SKILL = ROOT / "skills" / "linear-spike" / "SKILL.md"
EXCLUDED_SKILLS = ("linear-investigation", "linear-epic")

# AC1: the rule bullet, one pinned sentence per source line.
RULE_SENTENCES = (
    "An acceptance criterion that needs behavioural evidence must name the one artifact that proves it "
    "and the single command, run or record that produces that artifact, and that artifact must be "
    "producible in one pass by one role.",
    "One pass means one session of the one role the criterion names, with no fix round, no second session "
    "and no resumed session to finish it.",
    "A live multi-context ceremony is allowed only when the ceremony is the story's subject; then the story "
    "names the fixture, the exact voter contexts a single run creates, and the one record that run posts.",
    "A fixture the story would have to build is its own story.",
    "A criterion that expects a re-run, a second fixture, a fix round or a resumed session after the first run "
    "is not one-pass and fails this rule.",
)

# AC3: the preserved sentences, pinned per source line.
PRESERVED_SENTENCES = (
    "An issue delivers a complete feature the user can reach in the running environment.",
    "Bake reachability (routing, TLS, the deploy actually delivering the artifact) and any access gate "
    "into the criteria.",
    "Build each issue for every environment in `profile.environments` up front; promotion only tests, "
    "it never adds code.",
    "⛔ A deployment-review finding covered by an existing issue's criteria reopens that issue: move it back "
    "to in progress, amend the criteria with a dated note, and run it through PR, review, merge, deploy, "
    "and deployment review again.",
)

# AC2: one citation sentence per filing-skill site.
CITATIONS = (
    pytest.param(
        USER_STORY_SKILL,
        '**Acceptance Criteria:** an acceptance criterion that needs behavioural evidence must be one-pass producible, '
        'as [references/linear.md](references/linear.md) "Acceptance criteria and scope" states.',
        id="citation-linear-user-story-acceptance-criteria",
    ),
    pytest.param(
        USER_STORY_SKILL,
        '**Definition of Ready:** the "observable behaviour" box is checked against the one-pass evidence rule '
        'in [references/linear.md](references/linear.md) "Acceptance criteria and scope".',
        id="citation-linear-user-story-dor-observable-behaviour",
    ),
    pytest.param(
        BUG_SKILL,
        '**Acceptance Criteria:** each acceptance criterion that needs behavioural evidence must be one-pass producible, '
        'as [references/linear.md](references/linear.md) "Acceptance criteria and scope" states.',
        id="citation-linear-bug-acceptance-criteria",
    ),
    pytest.param(
        SPIKE_SKILL,
        '**Success Criteria:** each success criterion that needs behavioural evidence must be one-pass producible, '
        'as [references/linear.md](references/linear.md) "Acceptance criteria and scope" states.',
        id="citation-linear-spike-success-criteria",
    ),
)


def section(text: str, heading: str) -> str:
    assert f"\n## {heading}\n" in text, f"missing section: {heading}"
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def scope_lines() -> list[str]:
    text = section(SHARED_LINEAR.read_text(), "Acceptance criteria and scope")
    return [line.strip().removeprefix("- ") for line in text.splitlines() if line.strip()]


def skill_lines(path: Path) -> set[str]:
    return {
        line.strip().removeprefix("- ")
        for line in path.read_text().splitlines()
        if line.strip()
    }


def template_block(text: str) -> str:
    start = text.index("```markdown")
    end = text.index("\n```", start)
    return text[start:end]


RULE_CASES = (
    pytest.param(RULE_SENTENCES[0], id="rule-names-artifact-and-single-command"),
    pytest.param(RULE_SENTENCES[1], id="rule-one-pass-one-session"),
    pytest.param(RULE_SENTENCES[2], id="rule-ceremony-exception"),
    pytest.param(RULE_SENTENCES[3], id="rule-fixture-is-own-story"),
    pytest.param(RULE_SENTENCES[4], id="rule-not-one-pass-fails"),
)

PRESERVED_CASES = (
    pytest.param(PRESERVED_SENTENCES[0], id="preserved-reachability-line-1"),
    pytest.param(PRESERVED_SENTENCES[1], id="preserved-reachability-line-2"),
    pytest.param(PRESERVED_SENTENCES[2], id="preserved-per-environment"),
    pytest.param(PRESERVED_SENTENCES[3], id="preserved-deployment-review-reopens"),
)


@pytest.mark.parametrize("sentence", [*RULE_CASES, *PRESERVED_CASES])
def test_shared_linear_scope_section_pins(sentence: str) -> None:
    assert sentence in scope_lines()


@pytest.mark.parametrize("path,sentence", CITATIONS)
def test_filing_skill_cites_the_rule_in_rules_prose(path: Path, sentence: str) -> None:
    text = path.read_text()
    assert sentence in skill_lines(path)
    assert sentence not in template_block(text), "the citation must not sit inside the template block"
    assert text.index(sentence) < text.index("## Template (the description)"), (
        "the citation must sit in rules prose before the template"
    )


def test_skills_without_a_criteria_block_do_not_cite_the_rule() -> None:
    for name in EXCLUDED_SKILLS:
        text = (ROOT / "skills" / name / "SKILL.md").read_text()
        assert "one-pass producible" not in text, name
        assert "one-pass evidence rule" not in text, name
