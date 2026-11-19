# Pruning routine

The test suite and the skill text should not only grow.
At each retro, the scrum master runs a pruning-candidates script and records what it finds (`persona-scrum-master`, Retro).
The routine proposes; it removes nothing.
Each retire proposal becomes a retro action item, and nothing is removed until the owner approves it in a comment on the retro issue.

## Command

Run it from a full clone of this repository, at the commit under review:

```bash
uv run --locked python scripts/prune_candidates.py --since YYYY-MM-DD
```

`--since` is the previous retro's date.
The cutoff D is 00:00 UTC on that date.
The script evaluates the checked-out `HEAD`, reads only git objects, and prints the evaluated commit SHA, the since-date and, for each category, the candidate count and then each candidate with its evidence and a retire or keep proposal.
It refuses a shallow clone, because a shallow history cannot show when a file last changed.

## Categories

- **Tests untouched since D.**
  A `tests/test_*.py` file whose last commit is before D.
  Proposal: keep, since the file still runs on every CI run; retire it only on a finding that it adds no value (SKL-332 owns that judgement for the current suite).
- **Reference files uncited at this commit.**
  A `shared/` capability source (`shared/*.md`, except `README.md`) that no `skills/*/SKILL.md` cites as `references/<name>` at the evaluated commit.
  Vendored copies under `skills/*/references/` are not counted.
  Proposal: retire, since no skill entry point links it.
- **Rules uncited at this commit, unchanged since D.**
  A list item in a `shared/*.md` source that carries the `⛔` marker, with its continuation lines.
  It is a candidate when no file under `tests/` and no `skills/*/SKILL.md` contains any 40-character run of its text (whitespace collapsed, case ignored), and every line of it was last changed before D per `git blame`.
  Proposal: retire, since no test pins it and nobody has touched it since D; keep it if the retro finds it still applies, ideally with a pin.

A count of zero is a valid result.

## What the signals mean

"Untouched since D" and "uncited at this commit" are proxies.
They are not measures of whether a test is exercised or whether a rule or file has value: every test runs on every CI run, and an unquoted rule can still be one an agent follows.
The rule check is a point-in-time check at the evaluated commit, so the report never says "uncited since D".
The last-change date is the evidence the retro weighs, together with any finding from a test-quality review.
