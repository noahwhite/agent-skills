# Pruning routine

The test suite and the skill text should not only grow.
At each retro, the scrum master runs a pruning-candidates script and records what it finds (`persona-scrum-master`, Retro).
The routine proposes; it removes nothing.
Each retire proposal becomes a retro action item, and nothing is removed until the owner approves it in a comment on the retro issue.

## Command

Run it from anywhere inside a full clone of this repository, at the commit under review:

```bash
uv run --locked python scripts/prune_candidates.py --since YYYY-MM-DD
```

`--since` is the previous retro's date, written exactly as `YYYY-MM-DD`.
The cutoff D is 00:00 UTC on that date.
The script resolves `HEAD` once and evaluates that commit, reads only git objects, and prints the evaluated commit SHA, the since-date and, for each category, the candidate count and then each candidate with its evidence and a retire or keep proposal.
It refuses a shallow clone, because a shallow history cannot show when a file last changed, and a partial clone, because reading its missing objects would fetch them into the repository.
A refusal exits 2 with a message on stderr that names the clone type, and prints nothing on stdout.
Paths are taken literally, and `blame.ignoreRevsFile` is cleared for the run, so the result for a commit does not depend on local git configuration.

## Categories

- **Tests untouched since D.**
  A `tests/test_*.py` file whose latest committer time, over every commit that touched it, is before D.
  Proposal: keep, since the file still runs in the suite on every CI run; retire it only on a finding that it adds no value (the test-quality review owns that judgement for the current suite).
- **Reference files uncited at this commit.**
  A `shared/` capability source (`shared/*.md`, except `README.md`) that no `skills/*/SKILL.md` cites as `references/<name>` at the evaluated commit.
  A citation is the whole path: `references/<name>` inside a longer path or name, such as `../other/references/<name>` or `references/<name>.bak`, does not count.
  Vendored copies under `skills/*/references/` are not counted.
  Proposal: retire, since no skill entry point links it.
- **Rules uncited at this commit, unchanged since D.**
  A list item in a `shared/*.md` source whose own lines carry the `⛔` marker, with its continuation lines (indented, lazy, or after a blank line) and its nested items.
  A nested item that carries the marker is also a rule of its own; a list item inside a fenced code block is not a rule.
  It is a candidate when no file under `tests/` and no `skills/*/SKILL.md` contains any 40-character run of its text (markers removed, whitespace collapsed, case ignored), and every line of it was last changed before D per `git blame`.
  A rule of 40 characters or fewer counts as cited only when its whole text appears with no letter or digit on either side; a marker with no text is never cited.
  The evidence quotes the whole rule.
  Proposal: retire, since no test pins it and nobody has touched it since D; keep it if the retro finds it still applies, ideally with a pin.

A count of zero is a valid result.

## What the signals mean

"Untouched since D" and "uncited at this commit" are proxies.
They are not measures of whether a test is exercised or whether a rule or file has value: a test file can hold skipped or conditional tests, and an unquoted rule can still be one an agent follows.
The rule check is a point-in-time check at the evaluated commit, so the report never says "uncited since D".
The last-change date is the evidence the retro weighs, together with any finding from a test-quality review.
