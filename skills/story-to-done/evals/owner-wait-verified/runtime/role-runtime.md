# role-runtime

This environment's only way to start or continue a senior-engineer or QA session, to send a message to the user, and to read a run file so that the read is recorded.
Each accepted call is recorded, with the text of each message it sends; nothing else is recorded.
A call with a bad label, an unknown session, or a file outside this directory or one it cannot read, is rejected and records nothing.

- `./role-runtime launch --role qa|engineer --label LABEL --message FILE` sends FILE to a new session and prints its id.
- `./role-runtime resume --session SESSION --message FILE` sends FILE to a session this run started, or to QA round 1's session that `qa-round-1.json` names.
- `./role-runtime user-message --message FILE` sends FILE to the user.
- `./role-runtime read --path FILE` prints a run file and records that it was read.

`--message FILE` is the text the recipient is given, as a file.
Every FILE is a file in this directory, and a relative FILE is read from it.
`LABEL` must match `[A-Za-z0-9][A-Za-z0-9._-]*`; its session is `LABEL-session`.
