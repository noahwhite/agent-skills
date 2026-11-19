# Pruning routine

The test suite and the skill text should not only grow.
At each retro, the scrum master runs a pruning-candidates script and records what it finds (`persona-scrum-master`, Retro).
The routine proposes; it removes nothing.
Each retire proposal becomes a retro action item, and nothing is removed until the owner approves it in a comment on the retro issue.

## Command

Run it from the root of a full clone of this repository, at the commit under review:

```bash
uv run --locked python scripts/prune_candidates.py --since YYYY-MM-DD
```

The script finds the repository root itself, so it gives the same report when invoked by its path from any subdirectory.
`--since` is the previous retro's date, written exactly as `YYYY-MM-DD`.
The cutoff D is 00:00 UTC on that date.
The script resolves `HEAD` once and evaluates that commit, reads only git objects, and prints the evaluated commit SHA, the since-date and, for each category, the candidate count and then each candidate with its evidence and a retire or keep proposal.
It refuses a shallow clone, because a shallow history cannot show when a file last changed, and a partial clone, because reading its missing objects would fetch them into the repository.
It also refuses a repository whose `blame.ignoreRevsFile` names a missing file, because `git blame` fails on it even when the setting is cleared.
A refusal exits 2 with a message on stderr that names the cause, and prints nothing on stdout.
The repository is always the one the working directory is in: git's repository-local environment variables (`GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE` and the like) are dropped for the run.
Paths are taken literally, rename history is not followed, signatures are not shown, replace refs and grafts are ignored, and `blame.ignoreRevsFile` is cleared for the run, so otherwise the result for a commit does not depend on local git configuration.
Submodules and other non-file tree entries are skipped, and a control character in a path is printed escaped, so each candidate stays on one line.

## Categories

- **Tests untouched since D.**
  A `tests/test_*.py` file whose latest committer time, over every commit in the history of the evaluated commit that changed that path (side branches of merges included), is before D.
  Proposal: keep, since the file still runs in the suite on every CI run; retire it only on a finding that it adds no value (the test-quality review owns that judgement for the current suite).
- **Reference files uncited at this commit.**
  A `shared/` capability source (`shared/*.md`, except `README.md`) that no `skills/*/SKILL.md` cites as `references/<name>` at the evaluated commit.
  A citation is the whole path, optionally written `./references/<name>`, between delimiters (whitespace, quotes, brackets or punctuation) and optionally followed by a `#anchor` or a sentence-final period.
  `references/<name>` inside a longer path or name, such as `../other/references/<name>`, `references/<name>/x`, `references/<name>.bak` or `references/<name>+old`, does not count.
  Only `skills/*/SKILL.md` files are searched, so a citation in a vendored reference file does not count.
  Vendored copies under `skills/*/references/` are not counted.
  Proposal: retire, since no skill entry point links it.
- **Rules uncited at this commit, unchanged since D.**
  A list item in any `shared/*.md` file, `README.md` included, whose own lines (not those of its nested items) carry the `⛔` marker, with its continuation lines (indented, lazy, or after a blank line) and its nested items.
  A nested item that carries the marker is also a rule of its own; a list item inside a fenced code block is not a rule, and a fence closes only on its own delimiter character, at least as long, or when the list item that holds it ends.
  Line numbers count LF line breaks only, as git does.
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
