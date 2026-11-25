#!/usr/bin/env python3
"""Run one CLI voter (runtime: command or codex) so the harness reports its exit.

Invoke it directly as the only command of one run_in_background Bash call, one call per voter:

  python3 launch-cli-voter.py --prompt FILE --output FILE --timeout SECONDS [--label NAME] \
      [--preset opencode-json --model MODEL | --preset codex-exec --model MODEL [--effort LEVEL]
       | [--stdin] -- COMMAND [ARG...]]

The CLI runs in a fresh temporary directory. Its result goes to a temporary file and is moved
to --output atomically only on success, after any stale --output, --output.status and
--output.err are removed, so a failed launch never leaves a partial output.

  generic       COMMAND runs and its result is the file it writes to LAUNCH_RESULT_FILE, else
                its stdout. Its stdin is the prompt file with
                --stdin, else /dev/null. The environment carries LAUNCH_PROMPT_FILE (the prompt,
                absolute) and LAUNCH_RESULT_FILE (a temporary path inside the run directory).
  codex-exec    codex exec -m MODEL -s read-only --skip-git-repo-check --cd <run dir>
                -o <result> - with stdin from the prompt file; --effort adds
                -c model_reasoning_effort=EFFORT. The result is the -o file.
  opencode-json opencode run --standalone --format json --model MODEL with the prompt file
                attached and every tool denied; the result is the final assistant message text,
                extracted from the JSON events with jq.

Failure is a non-zero CLI exit (the exit mirrors the CLI's code), a timeout (the whole process
group is killed; exit 124), or a result that is empty or only whitespace (exit 1). Exit 2 is a
usage error and writes no status.

On exit it prints exactly one line to stdout and writes the same line to --output.status:

  voter=<label> exit=<n> bytes=<n>

bytes is the size of --output on success and 0 on failure. The CLI's stderr goes to
--output.err. No model, host or secret is built in.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile

TIMEOUT_EXIT = 124
FAIL_EXIT = 1
USAGE_EXIT = 2

OPENCODE_CONFIG = (
    '{"permission":{"bash":"deny","edit":"deny","webfetch":"deny","websearch":"deny",'
    '"read":"deny","glob":"deny","grep":"deny","task":"deny","execute":"deny"},'
    '"tools":{"bash":false,"edit":false,"webfetch":false,"read":false,"glob":false,'
    '"grep":false,"task":false,"skill":false,"question":false,'
    '"experimental_image_generate":false,"execute":false}}'
)
OPENCODE_MESSAGE = "Follow the instructions in the attached file exactly. Do not modify any file."
JQ_FINAL_TEXT = (
    ".[-1].part.messageID as $m | ([.[] | select(.type == \"text\" and .part.messageID == $m)"
    ' | .part.text] | join("")) | if test("\\\\S") then . else error("no final assistant text") end'
)


def parse(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(add_help=True, usage="%(prog)s [options] [-- COMMAND ...]")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--timeout", required=True, type=int)
    ap.add_argument("--label")
    ap.add_argument("--preset", choices=["opencode-json", "codex-exec"])
    ap.add_argument("--model")
    ap.add_argument("--effort")
    ap.add_argument("--stdin", action="store_true")
    if "--" in argv:
        i = argv.index("--")
        args = ap.parse_args(argv[:i])
        args.command = argv[i + 1 :]
    else:
        args = ap.parse_args(argv)
        args.command = []
    if args.timeout < 1:
        ap.error("--timeout must be a positive number of seconds")
    if args.preset and args.command:
        ap.error("give a --preset or a command after --, not both")
    if not args.preset and not args.command:
        ap.error("give a --preset or a command after --")
    if args.preset and not args.model:
        ap.error("--preset needs --model")
    if args.effort and args.preset != "codex-exec":
        ap.error("--effort applies to --preset codex-exec only")
    if args.stdin and args.preset:
        ap.error("--stdin applies to a command after --; a preset sets its own stdin")
    if not os.path.isfile(args.prompt):
        ap.error(f"prompt file not found: {args.prompt}")
    return args


def run_group(cmd, *, stdin, stdout, stderr, cwd, env, timeout) -> int:
    """Run cmd in its own process group; kill the group on timeout. Returns the exit code."""
    proc = subprocess.Popen(
        cmd, stdin=stdin, stdout=stdout, stderr=stderr, cwd=cwd, env=env, start_new_session=True
    )
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        return TIMEOUT_EXIT


def launch(args: argparse.Namespace, run_dir: str, err) -> tuple[int, str]:
    """Returns (exit code, path of the result file)."""
    prompt = os.path.abspath(args.prompt)
    result = os.path.join(run_dir, "report")
    env = dict(os.environ, LAUNCH_PROMPT_FILE=prompt, LAUNCH_RESULT_FILE=result)

    if args.preset == "codex-exec":
        cmd = ["codex", "exec", "-m", args.model, "-s", "read-only", "--skip-git-repo-check"]
        cmd += ["--cd", run_dir, "-o", result]
        if args.effort:
            cmd += ["-c", f"model_reasoning_effort={args.effort}"]
        cmd.append("-")
        with open(prompt, "rb") as fin, open(os.path.join(run_dir, "log"), "wb") as log:
            code = run_group(cmd, stdin=fin, stdout=log, stderr=err, cwd=run_dir, env=env,
                             timeout=args.timeout)
        return code, result

    if args.preset == "opencode-json":
        raw = os.path.join(run_dir, "events")
        env["OPENCODE_CONFIG_CONTENT"] = OPENCODE_CONFIG
        env["OPENCODE_DISABLE_PROJECT_CONFIG"] = "1"
        cmd = ["opencode", "run", "--standalone", "--format", "json", "--model", args.model]
        cmd += [OPENCODE_MESSAGE, "--file", prompt]
        with open(os.devnull, "rb") as fin, open(raw, "wb") as fout:
            code = run_group(cmd, stdin=fin, stdout=fout, stderr=err, cwd=run_dir, env=env,
                             timeout=args.timeout)
        if code != 0:
            return code, result
        with open(raw, "rb") as fin, open(result, "wb") as fout:
            code = run_group(["jq", "-rs", JQ_FINAL_TEXT], stdin=fin, stdout=fout, stderr=err,
                             cwd=run_dir, env=env, timeout=60)
        return code, result

    stdout = os.path.join(run_dir, "stdout")
    with open(prompt if args.stdin else os.devnull, "rb") as fin, open(stdout, "wb") as fout:
        code = run_group(args.command, stdin=fin, stdout=fout, stderr=err, cwd=run_dir, env=env,
                         timeout=args.timeout)
    if os.path.isfile(result) and os.path.getsize(result) > 0:
        return code, result
    return code, stdout


def main(argv: list[str]) -> int:
    args = parse(argv)
    output = os.path.abspath(args.output)
    label = args.label or os.path.splitext(os.path.basename(output))[0]
    status_path, err_path = output + ".status", output + ".err"
    os.makedirs(os.path.dirname(output), exist_ok=True)
    for stale in (output, status_path, err_path):
        if os.path.lexists(stale):
            os.remove(stale)

    run_dir = tempfile.mkdtemp(prefix="cli-voter-")
    staging = tempfile.mkdtemp(prefix=".cli-voter-", dir=os.path.dirname(output))
    code, size = FAIL_EXIT, 0
    try:
        with open(err_path, "wb") as err:
            try:
                code, result = launch(args, run_dir, err)
            except OSError as exc:
                err.write(f"launch failed: {exc}\n".encode())
                code, result = FAIL_EXIT, ""
        if code == 0:
            try:
                with open(result, "rb") as fh:
                    data = fh.read()
            except OSError:
                data = b""
            if not data.strip():
                code = FAIL_EXIT
            else:
                staged = os.path.join(staging, "out")
                shutil.copyfile(result, staged)
                os.replace(staged, output)
                size = len(data)
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
        shutil.rmtree(staging, ignore_errors=True)

    line = f"voter={label} exit={code} bytes={size}"
    tmp_status = status_path + ".tmp"
    with open(tmp_status, "w") as fh:
        fh.write(line + "\n")
    os.replace(tmp_status, status_path)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
