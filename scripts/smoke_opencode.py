"""Discover complete skill bundles using the V2 API, without model requests."""

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

LAYOUTS = (
    "project-agents", "project-opencode", "project-claude",
    "global-agents", "global-opencode", "global-claude",
)


def check_layout(root, work, layout, binary, timeout=30):
    project = work / "project"
    project.mkdir(parents=True)
    home = work / "home"
    home.mkdir()
    # No inherited credentials, config overrides, or shared-service registration.
    env = {
        "PATH": os.environ["PATH"], "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local/share"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_STATE_HOME": str(home / ".local/state"),
    }
    subprocess.run(["git", "init", "-q", str(project)], env=env, cwd=project,
                   check=True, text=True, capture_output=True, timeout=30)
    scope, runtime = layout.split("-")
    base = project if scope == "project" else home
    destination = base / f".{runtime}" / "skills"
    if layout == "global-opencode":
        destination = home / ".config/opencode/skills"
    manifest = root / "skills.json"
    if not manifest.is_file():
        raise RuntimeError(f"{layout}: no skills manifest at {manifest}; pass --root to the repo root")
    names = sorted(json.loads(manifest.read_text())["skills"])
    if not names:
        raise RuntimeError("No skills declared in skills.json")
    expected = {}
    for name in names:
        source = root / "skills" / name
        if not (source / "SKILL.md").is_file():
            raise RuntimeError(f"{layout}: missing skill {name}/SKILL.md")
        shutil.copytree(source, destination / name)
        # Both sides are canonicalised: the API may report a sibling spelling of the
        # same path (for example through a symlinked fixture directory).
        expected[name] = os.path.realpath(destination / name / "SKILL.md")

    def cli(*args):
        return subprocess.run(
            [binary, *args], cwd=project, env=env,
            check=True, text=True, capture_output=True, timeout=30,
        ).stdout

    def skills_seen():
        # The real CLI can truncate a large response and still exit 0; one bad or
        # empty envelope is expected during registration, so it is retried below.
        try:
            payload = json.loads(cli("api", "get", "/api/skill", "--header",
                                     f"x-opencode-directory:{project}"))
        except subprocess.CalledProcessError as call_error:
            return None, f"skill API call failed: {call_error.stderr or call_error.stdout or call_error}"
        except (subprocess.TimeoutExpired, OSError) as call_error:
            return None, f"skill API call failed: {call_error}"
        except json.JSONDecodeError as parse_error:
            return None, f"skill API returned undecodable JSON: {parse_error}"
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            return None, "invalid V2 skill response"
        items = payload["data"]
        if any(not isinstance(item, dict) or not isinstance(item.get("id"), str)
               or not isinstance(item.get("path"), str) for item in items):
            return None, "invalid V2 skill entry"
        found = {item["id"]: os.path.realpath(item["path"]) for item in items}
        missing = [name for name, path in expected.items() if found.get(name) != path]
        if missing:
            return None, f"discovered skills are missing {', '.join(missing)}"
        return found, None

    # The service port is explicit so this fixture cannot attach to a user's server.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    cli("service", "set", "port", str(port))
    error = stop_error = None
    try:
        try:
            cli("service", "start")
            deadline = time.monotonic() + timeout
            last_problem = "registration did not start"
            while True:
                seen, last_problem = skills_seen()
                if seen is not None:
                    break
                # A fresh API call can return [] or builtins only.
                # Keep one service alive and wait for the expected IDs, never just nonempty data.
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        f"opencode did not discover the expected skills before the deadline ({last_problem})")
                time.sleep(.2)
        except Exception as discovery_error:
            error = discovery_error
    finally:
        try:
            cli("service", "stop")
        except Exception as failed_stop:
            stop_error = failed_stop
    if error is None and stop_error is None:
        print(f"{layout}: opencode discovered all {len(expected)} skills", flush=True)
        return
    if error is not None:
        stop_note = f" (service stop also failed: {stop_error})" if stop_error is not None else ""
        raise RuntimeError(f"{layout}: {error}{stop_note}") from error
    raise RuntimeError(f"{layout}: discovery succeeded, but 'opencode service stop' failed: {stop_error}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")
    binary = shutil.which("opencode")
    if binary is None:
        parser.error("opencode is not installed")
    with tempfile.TemporaryDirectory(prefix="agent-skills-discovery-") as scratch:
        for layout in LAYOUTS:
            check_layout(args.root.resolve(), Path(scratch) / layout, layout, binary, args.timeout)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"OpenCode command failed: {error.stderr or error.stdout}") from error
    except (RuntimeError, subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error
