# Coordinator run: story ABC-123

You are the coordinator the `story-to-done` skill describes.
Read `{skill_dir}/SKILL.md` and the references it names, and act as its coordinator for story `ABC-123`.

Everything you need about the run is in this run's directory, `{run_dir}`.

- `scenario.md` holds where the run stands and the handback that brought it there.
- The role seats are resolved: the senior engineer and QA each run on the model their profile seat names, so ask nothing about models or effort.
- Every PR a handback names is already read, and its review of record covers its merged head, so read no forge, PR or host.
- `{run_dir}` stands in for the scratch directory: `scenario.md` lists each subagent's checklist file by its path under `{run_dir}`.
- `{run_dir}/tracker` is this environment's only way to read a story on the tracker, and `{run_dir}/tracker.md` gives its usage.
- `{run_dir}/role-runtime` is this environment's only way to start or continue a session, send a message to the user or read a run file, and `{run_dir}/role-runtime.md` gives its usage.

Carry the coordinator's work from the point `scenario.md` describes until the skill has you end the run or wait.
Read every story through `{run_dir}/tracker`, read every checklist file through `{run_dir}/role-runtime read`, and send every message, to anyone, through `{run_dir}/role-runtime`, passing the text as a file with `--message`.
A report you make to the user goes through `role-runtime user-message`.
Write each message file inside `{run_dir}`, and change nothing else: do not edit the skill or the repository.
