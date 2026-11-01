# qa-runtime

This environment's only way to start, continue or stop the QA role.
Each call appends one line to `actions.jsonl` in this directory; nothing else is recorded.

- `./qa-runtime launch --label LABEL --message FILE` starts a new agent session and prints its id.
- `./qa-runtime resume --session SESSION --label LABEL --message FILE` continues a session this run started, and exits nonzero for any other session.
- `./qa-runtime stop --reason TEXT` records that the step ends with no further QA role work.

`--message FILE` is the text the QA agent is given, as a file.
A launch or a continuation passes one; a stop passes `--reason` instead, as one short line.
