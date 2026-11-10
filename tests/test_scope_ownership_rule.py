"""SKL-27: engineers never change acceptance criteria or ship skips keyed on another story; two exits only."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
SKILLS = ROOT / "skills"

AC1_RULE = (
    "Only the product owner or the refinement process adds, moves, or rewords acceptance criteria on any story.",
    'An implementing engineer never adds an AC to any story, never moves its own unmet AC onto another story, '
    'never rewords an AC, never records its own "accepted deviation", and never accepts an AC as met by any means '
    'other than the completion tick in "Completion (AC and DoD checkboxes)".',
)
AC1_CARVE_OUT = (
    'Ticking an AC box after observing the behaviour in the deployed environment, per "Completion (AC and DoD checkboxes)", '
    "is the verification record and not an AC change.",
    "The two edits this section already directs remain permitted and are not engineer-added scope: amending one criterion "
    "with a dated note when a deployment-review finding reopens that same story, and deleting the later-environment lines "
    "the user has decided not to promote.",
    "Neither licence extends to another story, and neither lets an engineer reword a criterion it cannot meet "
    "or use a dated note to make an unmet criterion pass.",
)
AC2_RULE = (
    "Code never carries skips, pending lists, or exemptions keyed on another story landing later "
    '(for example "skip if directory X is absent" or an exemption entry naming another tracker story\'s key).'
)
AC2_SEQUENCING = (
    "A story that needs another story's artifact is blocked by that story; "
    "a guard spanning several stories' files belongs in a story blocked by all of them.",
    "The only exceptions allowed are permanent exemptions that depend on no other story and carry a comment stating why; "
    'that allowance covers test, lint, and build exemptions and does not relax "Do not hide failures".',
)
EXITS = (
    "An engineer who meets a scope limit has only two permitted responses, the two exits below.",
    "Exit one, a refinement proposal: a downstream requirement the engineer discovers is posted as a comment on the target "
    'story headed "Refinement proposal (not an AC)" and listed in its handback (the completion summary, in `engineering-workflow`).',
    "Exit two, blocked: when an AC cannot be met or the work needs another story's artifact, the engineer stops and reports "
    "itself blocked, naming the story that supplies the precondition or, where no story does, the criterion and why it cannot "
    "be met so the product owner can re-refine it, and the story moves to `profile.tracker.states.blocked`.",
    "The engineer makes that move where it has tracker write access, and otherwise states in its handback that the move is required.",
    "A proposal never substitutes for blocking when a current AC cannot be met.",
)
AC7_RULE = (
    "An AC that requires another story's output (an artifact, credential, stack, or behaviour that story delivers) "
    "requires a formal blocked-by relation to that story.",
    'The template DoR box "No blocking stories, no unresolved external dependencies, and no other story already owns this scope" '
    "stays unticked until that relation exists and the blocker is in `profile.tracker.states.done`.",
    "This refines, and does not replace, the relation-graph rules above, including the dated downgrade of a blocker that does "
    "not gate the criteria from `blocks` to `related`.",
    "Before adding the relation, triage checks it creates no cycle; where it would (the other story consumes this one), "
    "the product owner or the refinement process sets the delivery order, the cross-story check moves to whichever story "
    "that order lands last, and that story gets the blocked-by relations instead.",
    "An implementing engineer never moves an acceptance criterion between stories to resolve a cycle.",
)

EXIT_POINTER = 'the only two exits are a "Refinement proposal (not an AC)" or reporting the story blocked'
LINEAR_LINK = '[references/linear.md](references/linear.md) "Acceptance criteria and scope"'
PRACTICE_LINK = '[references/engineering-practice.md](references/engineering-practice.md) "Make minimal, durable changes"'
POINTER_SKILLS = ("engineering-workflow", "story-to-done", "persona-staff-engineer", "persona-staff-devops")
BRIEF_SKILLS = ("story-to-done", "persona-staff-engineer", "persona-staff-devops")
BRIEF_PREFIX = "- The scope rule: "


def spaced(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def section(text: str, heading: str) -> str:
    assert f"\n## {heading}\n" in text, f"missing section: {heading}"
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def linear_files() -> list[Path]:
    return [SHARED / "linear.md", *sorted(SKILLS.glob("*/references/linear.md"))]


def practice_files() -> list[Path]:
    return [SHARED / "engineering-practice.md", *sorted(SKILLS.glob("*/references/engineering-practice.md"))]


def skill_file(name: str) -> Path:
    return SKILLS / name / "SKILL.md"


def pointer_phrases(name: str) -> tuple[str, ...]:
    links = (LINEAR_LINK,) if name == "story-to-done" else (LINEAR_LINK, PRACTICE_LINK)
    return (EXIT_POINTER, *links)


def required_phrases() -> dict[Path, tuple[str, ...]]:
    """Every file in the guarded set and the phrases it must carry."""
    required: dict[Path, tuple[str, ...]] = {}
    for path in linear_files():
        required[path] = (*AC1_RULE, *EXITS)
    for path in practice_files():
        required[path] = (AC2_RULE, *EXITS)
    for name in POINTER_SKILLS:
        required[skill_file(name)] = pointer_phrases(name)
    required[skill_file("story-to-done")] += (AC2_RULE,)
    return required


def missing(text: str, phrases: tuple[str, ...]) -> list[str]:
    flat = spaced(text)
    return [phrase for phrase in phrases if phrase not in flat]


# ---- permissive-inversion scan -----------------------------------------------------------------

NEGATION = re.compile(r"\b(never|not|no|neither|nor|cannot)\b|n't\b", re.IGNORECASE)
ENGINEER = re.compile(r"\b(engineers?|implementing agent|implementer|developer|agent|team|anyone)\b", re.IGNORECASE)
AC_CHANGE = re.compile(
    r"\b(add|adds|added|adding|amend|amends|amended|amending|modify|modifies|modified|modifying|alter|alters|altered|altering"
    r"|move|moves|moved|moving|reword|rewords|reworded|rewording"
    r"|update|updates|updated|updating|rewrite|rewrites|rewritten|rewriting|replace|replaces|replaced|replacing"
    r"|change|changes|changed|changing|edit|edits|edited|editing|delete|deletes|deleted|deleting|remove|removes|removed|removing"
    r"|untick|unticks|unticked|un-tick|waive|waives|waived|waiving|accept|accepts|accepted|accepting)\b"
    r"[^.;,]{0,60}?\b(ACs?|acceptance criteri(?:on|a)|criteri(?:on|a))\b"
    r"|\b(ACs?|acceptance criteri(?:on|a)|criteri(?:on|a))\b[^.;,]{0,60}?\b(as met|met|done|complete|completed)\b"
    r"|accepted (?:deviation|risk)|waiv(?:e|ed|er)\b",
    re.IGNORECASE,
)
SKIP_TERM = re.compile(r"\b(skips?|skipping|skipped|pending lists?|exemptions?|exempt|xfail|waive|waived|ignore|ignores|ignored)\b", re.IGNORECASE)
OTHER_STORY = re.compile(
    r"\b[A-Z]{2,}-\d+\b|\b(?:another|other|later|sibling|future|different|follow-up|subsequent|next)\s+(?:tracker\s+)?(?:story|stories|issue)\b"
    r"|story's key|stories' files|directory\s+\S+\s+is\s+absent",
    re.IGNORECASE,
)
PERMISSIVE = re.compile(r"\b(?:may|might|can|could|is allowed|are allowed|permitted)\b", re.IGNORECASE)
AC_SEGMENT_SPLIT = re.compile(r"[,;]|\band\b", flags=re.IGNORECASE)
SKIP_LINK_STRONG = re.compile(
    r"\b(?:keyed on|key|naming|named|tied to|if|while|when|because|until|depends on|supplied by|supplies|needed by|lands|landing|later|blocked by|after|once)\b",
    re.IGNORECASE,
)
SKIP_LINK_DEPENDENCY = re.compile(
    r"\b(?:if|while|when|until|depends on|supplied by|supplies|needed by|lands|landing|later|blocked by|after|once)\b",
    re.IGNORECASE,
)
SKIP_MISSING_STATE = re.compile(
    r"\b(?:absent|unavailable|missing|lacking|lack|incomplete|unfinished|pending|blocked|needed|required|depends|supplied|unsupported|unprovided|scarce|unmade|unbuilt|unwritten)\b"
    r"|\bno\s+(?:fixtures?|credentials?|files?|directories|directory|dirs?|tests?|checks?|artifacts?|outputs?|dependencies|keys?|tokens?|secrets?|configs?|configurations?|environments?|services?|apis?|contracts?|data|code|implementation)\b(?!\s+(?:are|is|were|was|be|been|being)\s+(?:expected|assumed|intentional|deliberate)\b|\s+by design\b)"
    r"|\b(?:not|n't|never|without)\s+(?:present|available|exist|existed|there|ready|landed|delivered|supplied|provided|added|created|built|written|done|complete|completed)\b"
    r"|\b(?:does|do|is|are)\s+not\s+(?:present|available|exist|ready|landed|delivered|supplied|provided|added|created|built|written|done|complete|completed)\b",
    re.IGNORECASE,
)
SKIP_TEMPORAL_DEPENDENCY = re.compile(
    r"\b(?:until|after|once|when|while)\b[^.;]{0,80}?\b(?:lands|landing|landed|deliver|delivers|delivered|delivery|provide|provides|provided|supply|supplies|supplied|add|adds|added|create|creates|created|build|builds|built|write|writes|written)\b"
    r"|\b(?:lands|landing|landed|deliver|delivers|delivered|delivery|provide|provides|provided|supply|supplies|supplied|add|adds|added|create|creates|created|build|builds|built|write|writes|written)\b[^.;]{0,80}?\b(?:until|after|once|when|while)\b",
    re.IGNORECASE,
)
SKIP_INDEPENDENT_AGENT = re.compile(r"\bby\s+(?:a|an|the)?\s*(?:tools?|scripts?|generators?|systems?|pipelines?|process(?:es)?|builds?|vendors?)\b", re.IGNORECASE)
SKIP_LINK_WEAK = re.compile(r"\b(?:for|on)\b", re.IGNORECASE)
SKIP_LINK_WEAK_IMMEDIATE = re.compile(r"\b(?:for|on)\s*$", re.IGNORECASE)
SKIP_IMMEDIATE_LINK = re.compile(r"\b(?:for|until|when|if|while|because|keyed on|depends on|blocked by|tied to|after|once)\s*$", re.IGNORECASE)
SKIP_STRICT_LINK = re.compile(r"\b(?:until|when|once|after|lands|landing)\b", re.IGNORECASE)
SKIP_BOUNDARY = re.compile(r";|\bbut\b", re.IGNORECASE)
STORY_KEY = re.compile(r"^[A-Z]{2,}-\d+$")
SKIP_CONTENT_STOP = frozenset(
    {
        "the", "and", "for", "with", "that", "this", "from", "into", "are", "was", "were", "will", "would", "can", "could", "may", "might",
        "permanent", "exemption", "exempt", "skip", "skips", "skipping", "pending", "lists", "code", "story", "stories", "issue", "another",
        "other", "later", "sibling", "future", "different", "follow", "subsequent", "next", "keyed", "key", "naming", "named", "tied",
        "depends", "blocked", "until", "after", "once", "when", "while", "lands", "landing", "landed", "deliver", "delivers", "delivered",
        "delivery", "provide", "provides", "provided", "supply", "supplies", "supplied", "add", "adds", "added", "create", "creates", "created",
        "build", "builds", "built", "write", "writes", "written", "tool", "tools", "script", "scripts", "generator", "generators", "system",
        "systems", "pipeline", "pipelines", "process", "processes", "vendor", "vendors", "expected", "expects", "assumed", "assumes",
        "intentional", "deliberate", "design",
    }
)


SKIP_ARTIFACT_GENERIC = frozenset(
    {
        "api", "apis", "artifact", "artifacts", "check", "checks", "config", "configs", "configuration", "configurations",
        "contract", "contracts", "credential", "credentials", "data", "dependency", "dependencies", "dir", "dirs", "directory",
        "directories", "environment", "environments", "file", "files", "fixture", "fixtures", "implementation", "key", "keys",
        "output", "outputs", "secret", "secrets", "service", "services", "test", "tests", "token", "tokens",
    }
)
SKIP_ARTIFACT_BLOCKERS = frozenset({"independent", "separate", "unrelated"})
SKIP_ARTIFACT_VERB = re.compile(
    r"\b(?:lands|landing|landed|deliver|delivers|delivered|delivery|provide|provides|provided|supply|supplies|supplied"
    r"|add|adds|added|create|creates|created|build|builds|built|write|writes|written)\b",
    re.IGNORECASE,
)
SKIP_ARTIFACT_MARKER = re.compile(r"\b(?:until|after|once|when|while)\b", re.IGNORECASE)
SKIP_ARTIFACT_ADJUNCT = re.compile(
    r"\b(?:in|on|for|with|by|from|at|to|into|onto|under|over|through|across|via|per|about|against|between|among|during|before|after|until|once|when|while)\b",
    re.IGNORECASE,
)


def temporal_artifact(text: str) -> str:
    return SKIP_ARTIFACT_MARKER.sub(" ", SKIP_ARTIFACT_VERB.sub(" ", text))


def story_artifact(text: str) -> str:
    artifacts = [
        SKIP_ARTIFACT_ADJUNCT.split(text[match.end() :], maxsplit=1)[0]
        for match in SKIP_ARTIFACT_VERB.finditer(text)
    ]
    return " ".join(artifacts) if artifacts else text


def content_overlap(left: str, right: str) -> bool:
    def words(text: str) -> set[str]:
        return {word for word in re.findall(r"[a-z]{3,}", text.lower()) if word not in SKIP_CONTENT_STOP}

    left_words = words(left)
    right_words = words(right)
    if not left_words or not right_words or (left_words | right_words) & SKIP_ARTIFACT_BLOCKERS:
        return False
    if (left_words - SKIP_ARTIFACT_GENERIC) & (right_words - SKIP_ARTIFACT_GENERIC):
        return True
    if not (left_words & right_words) & SKIP_ARTIFACT_GENERIC:
        return False
    left_modifiers = left_words - SKIP_ARTIFACT_GENERIC
    right_modifiers = right_words - SKIP_ARTIFACT_GENERIC
    return not left_modifiers or not right_modifiers or bool(left_modifiers & right_modifiers)


def sentences(text: str) -> list[str]:
    flat = spaced(re.sub(r"^\s*(?:[-*>]|\d+\.)\s+", "", text, flags=re.MULTILINE).replace("\n", " "))
    return [s for s in re.split(r"(?<=[.!?])\s+", flat) if s]


def permissive_inversions(text: str) -> list[str]:
    """Sentences that permit an engineer to change an AC, or that permit a skip keyed on another story.

    AC changes are affirmative once an unnegated change verb appears outside a negated and/or segment. Skip keys
    pair only with a story reference within a short gap in the same segment, so coordinated negations and permanent
    exemptions that depend on no other story stay clean.
    """
    hits = []
    for sentence in sentences(text):
        hit = False
        for segment in AC_SEGMENT_SPLIT.split(sentence):
            if not (ENGINEER.search(segment) or PERMISSIVE.search(segment)):
                continue
            for ac in AC_CHANGE.finditer(segment):
                before = segment[: ac.start()]
                if re.search(r"\bto\s+$", before) and re.search(r"\b(?:product owner|coordinator|reviewer|arbiter)\b", before, re.IGNORECASE):
                    continue
                if not NEGATION.search(segment[: ac.end()]):
                    hit = True
                    break
            if hit:
                break
        if not hit:
            skip_spans = [(m.start(), m.end()) for m in SKIP_TERM.finditer(sentence)]
            other_spans = [(m.start(), m.end()) for m in OTHER_STORY.finditer(sentence)]
            permissive_ends = [m.end() for m in PERMISSIVE.finditer(sentence)]
            boundary_ends = [m.end() for m in SKIP_BOUNDARY.finditer(sentence)]

            def scope_start(pos: int) -> int:
                start = 0
                for end in permissive_ends:
                    if end <= pos:
                        start = end
                    else:
                        break
                return start

            def unnegated(span: tuple[int, int]) -> bool:
                start = scope_start(span[0])
                for end in boundary_ends:
                    if end <= span[0]:
                        start = max(start, end)
                    else:
                        break
                return not NEGATION.search(sentence[start : span[0]])

            def linked(skip: tuple[int, int], other: tuple[int, int]) -> bool:
                other_text = sentence[other[0] : other[1]]
                other_is_key = bool(STORY_KEY.match(other_text))

                def crosses_boundary(start: int, end: int) -> bool:
                    return bool(SKIP_BOUNDARY.search(sentence[start:end]))

                def weak_link_ok(text: str) -> bool:
                    if SKIP_LINK_WEAK_IMMEDIATE.search(text):
                        return True
                    return (not other_is_key) and bool(SKIP_LINK_WEAK.search(text))

                if other[0] >= skip[1]:
                    gap = sentence[skip[1] : other[0]]
                    last_boundary = 0
                    for boundary in SKIP_BOUNDARY.finditer(gap):
                        last_boundary = boundary.end()
                    if SKIP_LINK_STRONG.search(gap[last_boundary:]):
                        return True
                    if crosses_boundary(skip[1], other[0]):
                        before_boundary = gap[:last_boundary]
                        temporal_match = SKIP_TEMPORAL_DEPENDENCY.search(before_boundary)
                        if temporal_match and SKIP_INDEPENDENT_AGENT.search(before_boundary):
                            temporal = content_overlap(
                                temporal_artifact(temporal_match.group(0)),
                                story_artifact(sentence[other[1] :]),
                            )
                        else:
                            temporal = bool(temporal_match)
                        return bool(
                            temporal
                            or (SKIP_LINK_DEPENDENCY.search(before_boundary) and SKIP_MISSING_STATE.search(before_boundary))
                        )
                    return weak_link_ok(gap)
                if skip[0] >= other[1]:
                    before_other = sentence[max(0, other[0] - 40) : other[0]]
                    between = sentence[other[1] : skip[0]]
                    after_skip = sentence[skip[1] :]
                    if SKIP_IMMEDIATE_LINK.search(before_other):
                        return True
                    if not crosses_boundary(other[1], skip[0]) and (
                        SKIP_LINK_STRONG.search(between) or weak_link_ok(between)
                    ):
                        return True
                    return bool(SKIP_STRICT_LINK.search(after_skip))
                return False

            for skip in skip_spans:
                for other in other_spans:
                    if unnegated(skip) and unnegated(other) and linked(skip, other):
                        hit = True
                        break
                if hit:
                    break
        if hit:
            hits.append(sentence)
    return hits


# ---- positive assertions -----------------------------------------------------------------------


def test_guarded_set_covers_every_source_copy_and_skill() -> None:
    required = required_phrases()
    assert len(linear_files()) >= 2, "shared/linear.md plus at least one vendored copy"
    assert len(practice_files()) >= 2
    assert all(path.is_file() for path in required)


def test_every_guarded_file_carries_its_phrases() -> None:
    gaps = {str(path.relative_to(ROOT)): gap for path, phrases in required_phrases().items() if (gap := missing(path.read_text(), phrases))}
    assert not gaps, gaps


def test_rules_sit_in_the_named_sections() -> None:
    linear = (SHARED / "linear.md").read_text()
    scope = spaced(section(linear, "Acceptance criteria and scope"))
    assert not missing(scope, (*AC1_RULE, *AC1_CARVE_OUT, *EXITS))
    assert not missing(spaced(section(linear, "Triage and Definition of Ready")), AC7_RULE)
    practice = spaced(section((SHARED / "engineering-practice.md").read_text(), "Make minimal, durable changes"))
    assert not missing(practice, (AC2_RULE, *AC2_SEQUENCING, *EXITS))


def test_triage_rule_reaches_the_product_owner_and_refinement() -> None:
    for name in ("persona-product-owner", "story-refinement"):
        assert not missing((SKILLS / name / "references" / "linear.md").read_text(), AC7_RULE), name


def test_story_to_done_vendors_linear_but_not_practice() -> None:
    refs = SKILLS / "story-to-done" / "references"
    assert (refs / "linear.md").is_file() and not (refs / "engineering-practice.md").exists()
    for name in ("persona-staff-engineer", "persona-staff-devops"):
        assert (SKILLS / name / "references" / "engineering-practice.md").is_file(), name


def brief_list(name: str) -> list[str]:
    lines = skill_file(name).read_text().splitlines()
    start = lines.index("It must include:") + 2
    end = start
    while end < len(lines) and lines[end].strip():
        end += 1
    return lines[start:end]


def test_each_brief_carries_one_scope_item_with_pointer_and_links() -> None:
    for name in BRIEF_SKILLS:
        items = [line for line in brief_list(name) if line.startswith(BRIEF_PREFIX)]
        assert len(items) == 1, name
        assert not missing(items[0], pointer_phrases(name)), name
    story_item = next(line for line in brief_list("story-to-done") if line.startswith(BRIEF_PREFIX))
    assert not missing(story_item, (AC2_RULE, AC2_SEQUENCING[0], "permanent exemptions that depend on no other story", "test, lint, and build exemptions", '"Do not hide failures"'))


def engineering_workflow_step(number: int, title: str) -> str:
    text = skill_file("engineering-workflow").read_text()
    return section(text, f"{number}. {title}")


def test_engineering_workflow_meets_the_rule_at_triage_and_self_review() -> None:
    triage = [line for line in engineering_workflow_step(1, "Triage the story").splitlines() if "scope rules" in line]
    assert len(triage) == 1 and triage[0].startswith("5. Apply the scope rules")
    assert EXIT_POINTER in triage[0] and LINEAR_LINK in triage[0] and PRACTICE_LINK in triage[0]
    assert '"Prepare the PR"' in triage[0] and '"Self-review against the acceptance criteria"' in triage[0]
    prepare = engineering_workflow_step(5, "Prepare the PR").splitlines()
    review = [line for line in prepare if line.startswith("4. Self-review against the acceptance criteria")]
    assert len(review) == 1
    assert '"Triage the story"' in review[0] and "Apply the scope rules" in review[0] and "two exits" in review[0]
    assert LINEAR_LINK in review[0] and PRACTICE_LINK in review[0]


# ---- negative assertion and false-positive probe -----------------------------------------------


def test_no_guarded_file_carries_a_permissive_inversion() -> None:
    offenders = {str(path.relative_to(ROOT)): hits for path in required_phrases() if (hits := permissive_inversions(path.read_text()))}
    assert not offenders, offenders


def test_false_positive_probe_passes() -> None:
    linear = section((SHARED / "linear.md").read_text(), "Acceptance criteria and scope")
    carve_out = [line for line in linear.splitlines() if any(spaced(line).endswith(c[-40:]) for c in AC1_CARVE_OUT)]
    assert len(carve_out) == len(AC1_CARVE_OUT), "carve-out lines moved: update the probe"
    probe = "\n".join(
        (
            'The rule is that an implementing engineer "never adds an AC", and the engineer "never moves an AC" either.',
            "The engineer never rewords an AC on any story.",
            "An engineer never adds an AC or moves an AC.",
            "Code never carries skips, pending lists, or exemptions keyed on another story landing later.",
            "SKL-123 is blocked, but code may carry a permanent exemption for vendored files.",
            "Code may carry a permanent exemption for generated files; SKL-123 supplies the fixtures.",
            "Code may carry a permanent exemption for generated files and SKL-123 supplies the fixtures.",
            "Code may carry a permanent exemption because the files are generated; SKL-123 supplies the fixtures.",
            "Code may carry a permanent exemption if the files are generated; SKL-123 supplies the fixtures.",
            "Code may carry a permanent exemption if the generated files are not hand-edited; SKL-123 supplies fixtures.",
            "Code may carry a permanent exemption if the generated files are created by a tool; SKL-123 supplies fixtures.",
            "Code may carry a permanent exemption if no fixtures are expected by design; SKL-123 supplies an unrelated API.",
            "Code may carry a permanent exemption while the files are created by a tool; SKL-123 supplies fixtures.",
            "Code may carry a permanent exemption while files are created by a tool; SKL-123 supplies unrelated files.",
            "Code may carry a skip while files are created by a tool; SKL-123 supplies separate files.",
            "Code may carry a skip while alpha files are created by a tool; SKL-123 supplies beta files.",
            "# Permanent exemption: generated references/ copies are skipped by the scan; this depends on no other story.",
            'EXEMPT = ("references",)  # why: vendored output, never hand-edited',
            *carve_out,
        )
    )
    assert permissive_inversions(probe) == []


def test_true_positive_probe_flags_permissive_inversions() -> None:
    fixtures = (
        "The implementer may add an acceptance criterion.",
        "The engineer may amend an acceptance criterion it cannot meet.",
        "The engineer must not reword an AC. The engineer may move the AC though.",
        "The engineer may add an AC when the story cannot proceed.",
        "Code may carry a skip if directory X is absent.",
        "Code may carry a skip keyed on SKL-123.",
        "Code may exempt a test for a follow-up story.",
        "Tests may xfail while another story lands.",
        "The engineer never adds an AC to this story and may move an AC to another story.",
        "Code never carries a skip keyed on SKL-123 and may carry a skip keyed on SKL-456.",
        "For SKL-123, code may carry a skip.",
        "Code may skip checks for this story and another story.",
        "For SKL-123; code may carry a skip until it lands.",
        "Code may carry a skip for the integration checks while the API contract and credentials needed by those checks are supplied by another story.",
        "Tests may xfail on another story.",
        "Code may carry exemptions tied to another story.",
        "The engineer may direct a developer to add an AC.",
        "Code may carry a skip for SKL-123.",
        "Tests may xfail on SKL-123.",
        "Code may carry a skip, but only until SKL-123 lands.",
        "Code may carry a skip; it is keyed on SKL-123.",
        "Code may carry a skip if the fixtures are absent; SKL-123 will add them.",
        "Code may carry a skip if the fixtures are unavailable; SKL-123 will provide them.",
        "Code may carry a skip while the credentials are not present; SKL-123 supplies them.",
        "Code may carry a skip if the directory does not exist; SKL-123 creates it.",
        "Code may carry a skip until the API lands; SKL-123 will deliver the API.",
        "Code may carry a skip if there are no fixtures; SKL-123 will provide them.",
        "Code may carry a skip until the API is delivered; SKL-123 delivers it.",
        "Code may carry a skip until the API client is delivered by a tool; SKL-123 delivers the client.",
        "Code may carry a skip until the client is landed by the pipeline; SKL-123 lands the client.",
        "Code may carry a skip while files are created by a tool; SKL-123 supplies the files.",
        "Code may carry a skip while generated files are created by a tool; SKL-123 supplies the files.",
        "Code may carry a skip while files are created by a tool; SKL-123 supplies the files in a separate package.",
        "Code may carry a skip until the client is landed by the pipeline; SKL-123 creates API docs for users and lands the client.",
        "The engineer may add or move an AC.",
        "An engineer adds an AC to another story.",
        "Tests xfail for another story.",
    )
    missed = [fixture for fixture in fixtures if not permissive_inversions(fixture)]
    assert not missed, missed


# ---- mutation tests ----------------------------------------------------------------------------


def guard_fails(path: Path, text: str) -> bool:
    return bool(missing(text, required_phrases()[path])) or bool(permissive_inversions(text))


def test_guard_kills_every_mutant() -> None:
    shared_linear = SHARED / "linear.md"
    shared_practice = SHARED / "engineering-practice.md"
    linear = shared_linear.read_text()
    practice = shared_practice.read_text()
    mutants: list[tuple[str, Path, str]] = [
        ("delete AC1 rule", shared_linear, linear.replace(AC1_RULE[0], "")),
        ("delete AC1 engineer sentence", shared_linear, linear.replace(AC1_RULE[1], "")),
        (
            "permit an engineer-added AC",
            shared_linear,
            linear.replace(AC1_RULE[0], "Only the product owner, the refinement process, or an implementing engineer adds acceptance criteria on any story."),
        ),
        (
            "permit an engineer to add an AC in the engineer sentence",
            shared_linear,
            linear.replace("never adds an AC to any story", "may add an AC to any story"),
        ),
        ("delete AC2 rule", shared_practice, practice.replace(AC2_RULE, "")),
        (
            "permit a skip keyed on another story",
            shared_practice,
            practice.replace(AC2_RULE, AC2_RULE.replace("Code never carries", "Code may carry")),
        ),
        (
            "delete AC2 restatement from the story-to-done brief",
            skill_file("story-to-done"),
            skill_file("story-to-done").read_text().replace(AC2_RULE, ""),
        ),
    ]
    for path in (*linear_files(), *practice_files()):
        text = path.read_text()
        for exit_sentence in EXITS:
            mutants.append((f"delete exit sentence from {path.relative_to(ROOT)}", path, text.replace(exit_sentence, "")))
    for path in (*linear_files()[1:], *practice_files()[1:]):
        text = path.read_text()
        rule = AC1_RULE[0] if path.name == "linear.md" else AC2_RULE
        mutants.append((f"delete rule from {path.relative_to(ROOT)}", path, text.replace(rule, "")))
    for name in POINTER_SKILLS:
        path = skill_file(name)
        mutants.append((f"delete exit pointer from {name}", path, path.read_text().replace(pointer_phrases(name)[0], "")))
    survivors = [label for label, path, text in mutants if text == path.read_text() or not guard_fails(path, text)]
    assert not survivors, survivors
