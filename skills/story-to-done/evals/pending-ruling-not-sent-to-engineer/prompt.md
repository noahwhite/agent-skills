# Coordinator run: story ABC-123

You are the coordinator the `story-to-done` skill describes.
Read `{skill_dir}/SKILL.md` and the references it names, and act as its coordinator for story `ABC-123`.

Everything you need about the story is in this run's directory, `{run_dir}`.

- `scenario.md` holds the state you have just read back, the handback that brought it, and the story's acceptance criteria and Definition of Done.
- The role seats are resolved: the senior engineer and QA each run on the model their profile seat names, so ask nothing about models or effort.
- Every PR a handback names is already read, and its review of record covers its merged head, so read no forge, PR or host.
- `{run_dir}` stands in for the scratch directory: `scenario.md` lists each subagent's checklist file by its path under `{run_dir}`, and each handback names the checklist file its agent left.
- `{run_dir}/story-runtime` is this environment's only way to send a message, start a session, read the tracker or read a run file, and `{run_dir}/story-runtime.md` gives its usage.

Carry the coordinator's work from the point `scenario.md` describes until the skill has you end the run or wait.
Read every checklist file and the tracker through `{run_dir}/story-runtime`, and send every message, to anyone, through it, passing the text as a file with `--message`.
Write each message file inside `{run_dir}`, and change nothing else: do not edit the skill or the repository.
