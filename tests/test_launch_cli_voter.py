"""The CLI voter launcher: shared/launch-cli-voter.py.

Every case runs the launcher as a subprocess with fake commands (and fake codex and opencode
binaries on PATH), so no real CLI and no network is used.
"""

import json
import os
import re
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "shared" / "launch-cli-voter.py"
MANIFEST = json.loads((ROOT / "skills.json").read_text())
STATUS = re.compile(r"^voter=\S+ exit=\d+ bytes=\d+\n$")


@pytest.fixture
def rig(tmp_path):
    (tmp_path / "bin").mkdir()
    (tmp_path / "prompt.md").write_text("the prompt\n")
    return tmp_path


def fake(rig, name, body):
    path = rig / "bin" / name
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def launch(rig, *args, timeout=30):
    env = dict(os.environ, PATH=f"{rig / 'bin'}:{os.environ['PATH']}")
    return subprocess.run(
        [sys.executable, str(SOURCE), "--prompt", str(rig / "prompt.md"),
         "--output", str(rig / "out" / "result.md"), *args],
        capture_output=True, text=True, env=env, cwd=rig, timeout=timeout,
    )


def outdir(rig):
    return sorted(p.name for p in (rig / "out").iterdir()) if (rig / "out").exists() else []


def test_success_moves_output_and_prints_one_status_line(rig):
    res = launch(rig, "--timeout", "10", "--label", "alpha", "--", "sh", "-c", "echo hello")
    assert res.returncode == 0
    assert res.stdout == "voter=alpha exit=0 bytes=6\n"
    assert (rig / "out" / "result.md").read_text() == "hello\n"
    assert (rig / "out" / "result.md.status").read_text() == res.stdout
    assert outdir(rig) == ["result.md", "result.md.err", "result.md.status"]


def test_default_label_is_the_output_stem(rig):
    res = launch(rig, "--timeout", "10", "--", "sh", "-c", "echo x")
    assert res.stdout.startswith("voter=result exit=0")


def test_nonzero_exit_mirrors_code_and_leaves_no_output(rig):
    res = launch(rig, "--timeout", "10", "--", "sh", "-c", "echo partial; echo boom >&2; exit 7")
    assert res.returncode == 7
    assert STATUS.match(res.stdout) and "exit=7 bytes=0" in res.stdout
    assert "boom" not in res.stdout
    assert not (rig / "out" / "result.md").exists()
    assert "boom" in (rig / "out" / "result.md.err").read_text()
    assert (rig / "out" / "result.md.status").read_text() == res.stdout


@pytest.mark.parametrize("body", ["true", "printf '  \\n\\t\\n'"])
def test_empty_or_whitespace_output_is_failure(rig, body):
    res = launch(rig, "--timeout", "10", "--", "sh", "-c", body)
    assert res.returncode == 1
    assert "exit=1 bytes=0" in res.stdout
    assert not (rig / "out" / "result.md").exists()


def test_timeout_kills_the_process_group_and_exits_124(rig):
    marker = rig / "grandchild-alive"
    body = f"(sleep 4; touch {marker}) & echo partial; sleep 60"
    start = time.monotonic()
    res = launch(rig, "--timeout", "1", "--", "sh", "-c", body)
    assert time.monotonic() - start < 20
    assert res.returncode == 124
    assert "exit=124 bytes=0" in res.stdout
    assert not (rig / "out" / "result.md").exists()
    time.sleep(4.5)
    assert not marker.exists()


def test_stale_outputs_are_removed_first(rig):
    (rig / "out").mkdir()
    for name in ("result.md", "result.md.status", "result.md.err"):
        (rig / "out" / name).write_text("stale")
    res = launch(rig, "--timeout", "10", "--", "sh", "-c", "exit 3")
    assert res.returncode == 3
    assert not (rig / "out" / "result.md").exists()
    assert (rig / "out" / "result.md.status").read_text() == res.stdout


def test_no_temp_files_remain_after_success_or_failure(rig):
    launch(rig, "--timeout", "10", "--", "sh", "-c", "echo ok")
    launch(rig, "--timeout", "10", "--", "sh", "-c", "exit 1")
    assert not [n for n in outdir(rig) if n.startswith(".")]


def test_stdin_is_dev_null_by_default(rig):
    res = launch(rig, "--timeout", "10", "--", "sh", "-c", "wc -c; echo done")
    assert (rig / "out" / "result.md").read_text().split() == ["0", "done"]
    assert res.returncode == 0


def test_stdin_flag_feeds_the_prompt_file(rig):
    launch(rig, "--timeout", "10", "--stdin", "--", "cat")
    assert (rig / "out" / "result.md").read_text() == "the prompt\n"


def test_command_runs_in_a_fresh_dir_with_the_prompt_path_in_env(rig):
    launch(rig, "--timeout", "10", "--", "sh", "-c", 'pwd; echo "$LAUNCH_PROMPT_FILE"')
    cwd, prompt = (rig / "out" / "result.md").read_text().split("\n")[:2]
    assert Path(cwd) != rig and "cli-voter-" in cwd
    assert prompt == str(rig / "prompt.md")


def test_command_may_write_its_result_to_the_result_file(rig):
    res = launch(rig, "--timeout", "10", "--", "sh", "-c",
                 'echo ignored; echo viafile > "$LAUNCH_RESULT_FILE"')
    assert res.returncode == 0
    assert (rig / "out" / "result.md").read_text() == "viafile\n"


def test_codex_preset_args_and_stdin(rig):
    fake(rig, "codex", 'echo "$@" > "$(dirname "$0")/args"; cat > "$(dirname "$0")/stdin"; '
         'while [ $# -gt 0 ]; do [ "$1" = -o ] && echo reviewed > "$2"; shift; done\n')
    res = launch(rig, "--timeout", "10", "--preset", "codex-exec", "--model", "m-1",
                 "--effort", "xhigh")
    assert res.returncode == 0, res.stdout
    args = (rig / "bin" / "args").read_text()
    assert args.startswith("exec -m m-1 -s read-only --skip-git-repo-check --cd ")
    assert "-c model_reasoning_effort=xhigh" in args and args.strip().endswith("-")
    assert (rig / "bin" / "stdin").read_text() == "the prompt\n"
    assert (rig / "out" / "result.md").read_text() == "reviewed\n"


def test_codex_preset_empty_report_is_failure(rig):
    fake(rig, "codex", "cat > /dev/null\n")
    res = launch(rig, "--timeout", "10", "--preset", "codex-exec", "--model", "m-1")
    assert res.returncode == 1 and not (rig / "out" / "result.md").exists()


def test_opencode_preset_extracts_final_assistant_text(rig):
    events = [
        {"type": "text", "part": {"messageID": "m1", "text": "draft"}},
        {"type": "text", "part": {"messageID": "m2", "text": "final "}},
        {"type": "tool_use", "part": {"messageID": "m2"}},
        {"type": "text", "part": {"messageID": "m2", "text": "answer"}},
    ]
    lines = "\n".join(json.dumps(e) for e in events)
    fake(rig, "opencode", f'echo "$@" > "$(dirname "$0")/args"; cat <<\'EOF\'\n{lines}\nEOF\n')
    res = launch(rig, "--timeout", "10", "--preset", "opencode-json", "--model", "p/m")
    assert res.returncode == 0, res.stdout
    assert (rig / "out" / "result.md").read_text() == "final answer\n"
    args = (rig / "bin" / "args").read_text()
    assert "run --standalone --format json --model p/m" in args and "--file " in args


def test_opencode_preset_without_final_text_is_failure(rig):
    fake(rig, "opencode", 'echo \'{"type":"text","part":{"messageID":"m","text":"  "}}\'\n')
    res = launch(rig, "--timeout", "10", "--preset", "opencode-json", "--model", "p/m")
    assert res.returncode != 0 and "bytes=0" in res.stdout
    assert not (rig / "out" / "result.md").exists()


def test_missing_cli_is_failure_with_status(rig):
    res = launch(rig, "--timeout", "10", "--", "no-such-cli-xyz")
    assert res.returncode == 1 and "exit=1 bytes=0" in res.stdout
    assert not (rig / "out" / "result.md").exists()


@pytest.mark.parametrize("args", [
    ["--timeout", "10"],
    ["--timeout", "0", "--", "true"],
    ["--timeout", "10", "--preset", "codex-exec"],
    ["--timeout", "10", "--preset", "codex-exec", "--model", "m", "--", "true"],
    ["--timeout", "10", "--effort", "high", "--", "true"],
])
def test_usage_errors_exit_2_and_print_no_status(rig, args):
    res = launch(rig, *args)
    assert res.returncode == 2 and res.stdout == ""
    assert not (rig / "out").exists()


def test_the_launcher_is_vendored_where_the_manifest_lists_it():
    skills = [s for s, names in MANIFEST["executables"].items() if "launch-cli-voter.py" in names]
    assert {"story-refinement", "story-to-done"} <= set(skills)
    body = SOURCE.read_bytes()
    for skill in skills:
        copy = ROOT / "skills" / skill / "scripts" / "launch-cli-voter.py"
        assert copy.read_bytes().split(b"\n", 1)[1] == body


def test_the_runtimes_rule_states_the_background_launch_contract():
    text = (ROOT / "shared" / "runtimes.md").read_text()
    for phrase in ("run_in_background", "only command of its own", "`nohup`",
                   "does not poll or sleep", "never substitutes another model", "`--timeout`"):
        assert phrase in text
