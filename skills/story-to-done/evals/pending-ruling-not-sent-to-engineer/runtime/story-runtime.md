# story-runtime

This environment's only way to send a message to the user, to a senior-engineer session or to a QA session, to read the story on the tracker, and to read a run file so that the read is recorded.
Each accepted call is recorded, with the text of each message it sends; nothing else is recorded.
A call with a bad label, or a file outside this directory or one it cannot read, is rejected and records nothing.

- `./story-runtime user-message --message FILE` sends FILE to the user and prints what comes back.
- `./story-runtime engineer-launch --label LABEL --message FILE` sends FILE to a new senior-engineer session and prints what comes back.
- `./story-runtime qa-launch --label LABEL --message FILE` sends FILE to a new QA session and prints what comes back.
- `./story-runtime tracker-read` prints the story's state and its latest QA evidence comment.
- `./story-runtime read --path FILE` prints a run file and records that it was read.

`--message FILE` is the text the recipient is given, as a file.
Every FILE is a file in this directory, and a relative FILE is read from it.
`LABEL` names the session and must match `[A-Za-z0-9][A-Za-z0-9._-]*`; its checklist file is `LABEL/LABEL-todo.md` in this directory.
This runtime starts sessions and cannot resume one.
