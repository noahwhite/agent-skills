# SKL-55 QA evidence

Verified on 2026-10-24 UTC against shipped `main` commit `001d1a3338ce7ccb4774c82ff85cb4011de9ec01`.
Environment: repository release on `main`, GitHub Actions Ubuntu 24.04, and a fresh detached checkout using CPython 3.12.3 with locked dependencies.
This repository ships its main branch and has no application deployment pipeline.

Implementation: [PR](https://github.com/noahwhite/agent-skills/pull/38), reviewed head `08bf73799b347ef3efc80f302c0bd5edb927b46b`, squash commit `001d1a3338ce7ccb4774c82ff85cb4011de9ec01`.
[PR CI](https://github.com/noahwhite/agent-skills/actions/runs/40121908221) and [shipped main CI](https://github.com/noahwhite/agent-skills/actions/runs/40122347839) both passed checks and discovery, including the private leak scan and all skill validations.

## Acceptance criteria

| Item | Observed result |
|---|---|
| AC1 | Records instructs the workflow to cite each file by its base name only, never a directory path, and to quote or attach any content a reader needs. Both sentences are pinned. |
| AC2 | The template intro forbids local paths and requires needed content. All four refinement source fields and the pointing context use `<file base name>`. Each field is pinned separately. |
| AC3 | The original 94 refinement tests remain unchanged; the expanded suite passes 105 cases and the complete suite passes 427. Vendoring check passes. Each of nine positive phrases was deleted separately and failed its named test; four legacy-string probes and the original Records instruction also failed. Two correct-formatting probes passed. [Mutation commands and results](mutations.md) also appear in the implementation PR. CI is green at its reviewed head. |
| AC4 | Comparing the skill against base `715005b9a184783621fbe5e27f6d29f3f06581fb` after excluding Records yields identical bytes. Roles, Denied tracker writes, Anchoring guardrail, Split rule, and Steps 1–4 are unchanged. The existing test file is retained byte-for-byte, with new tests appended. |

## Original failure and regression proof

The fixture comment identified in the story (SKL-53, comment `01b443d4`) contains four absolute scratch source references: `refine-po.md`, `refine-eng1-deepseek.md`, `refine-eng2-codex.md`, and `refine-sm.md`.
The root cause was an explicit instruction to cite paths plus path-valued source placeholders.
The corrected instructions keep raw files local, cite base names, and carry needed content into the record.
The historical comment was left as observed evidence.
The removed instruction is preserved in [the immutable original source](https://github.com/noahwhite/agent-skills/blob/715005b9a184783621fbe5e27f6d29f3f06581fb/skills/story-refinement/SKILL.md#L228); the tracker and implementation PR retain the fixture reference.
Actual scratch directory prefixes are omitted from this public record; the source-level reproduction below supplies immutable regression proof.

Before implementation, the new skill tests failed on the original instruction; the new template tests failed on the intro and all five source fields.
Restoring the original Records instruction after the fix failed `test_records_cite_base_names_and_include_needed_content` and `test_skill_records_never_request_local_paths[cite their paths]`.
Every required deletion also failed its named test, as recorded in the mutation evidence.

## Definition of Done

| Item | Evidence |
|---|---|
| Root cause identified | The explicit path-citation instruction and all five path-valued source placeholders were corrected. |
| Original case verified | The cited fixture was inspected; RED/GREEN runs and the original-defect mutation prove the correction. |
| Regression protection | Eleven added cases cover both documents' instructions, each source field, and both banned strings; 14 defect probes failed and two formatting probes passed. |
| Independent review | [Review of record](https://github.com/noahwhite/agent-skills/pull/38#pullrequestreview-5639482581): Codex `gpt-6.1-sol`, then independent Kimi `kimi/kimi-k3`, no unresolved findings at the exact reviewed head. Both the review commit ID and its first-line SHA matched the live head before the guarded squash merge. |
| Docs/comments updated | Records and the hand-written record template explain base-name citations and inclusion of needed content. |
| No new regressions | Complete suite and vendoring pass again on the shipped merge commit. CI validates all 17 skills and all six discovery layouts. Existing ceremony contracts remain unchanged. |

Pre-PR sweep, empirical hunt, and independent arbitration converged without a blocking or Medium finding.
The optional GLM review passed.
Accepted Low guard limits concern hypothetical later edits: alternate path wording, conflicting or comment-hidden duplicates, indentation, and extra fallback blocks.
The current templates have none of these; AC3 intentionally pins exact phrases in two files.
Renaming `## Refinement comment` fails nine tests in the complete refinement suite, including five pre-existing tests.
No remediation was required.

Local private leak-scan patterns were unavailable; public scanning found no matches, and both remote CI runs completed the required public/private scan successfully.
No browser feature or environment promotion applies to this repository change.
