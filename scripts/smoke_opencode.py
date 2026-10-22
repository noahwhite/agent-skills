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
    names = sorted(json.loads((root / "skills.json").read_text())["skills"])
    if not names:
        raise RuntimeError("No skills declared in skills.json")
    expected = {}
    for name in names:
        source = root / "skills" / name
        if not (source / "SKILL.md").is_file():
            raise RuntimeError(f"{layout}: missing skill {name}/SKILL.md")
        shutil.copytree(source, destination / name)
        expected[name] = str(destination / name / "SKILL.md")

    def cli(*args):
        return subprocess.run(
            [binary, *args], cwd=project, env=env,
            check=True, text=True, capture_output=True, timeout=30,
        ).stdout

    # The service port is explicit so this fixture cannot attach to a user's server.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    cli("service", "set", "port", str(port))
    try:
        cli("service", "start")
        deadline = time.monotonic() + timeout
        while True:
            # A managed server starts in HOME, not the CLI's cwd: select this fixture.
            payload = json.loads(cli("api", "get", "/api/skill", "--header",
                                     f"x-opencode-directory:{project}"))
            # V2 returns an envelope; id is stable even when the display name changes.
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise RuntimeError(f"{layout}: invalid V2 skill response")
            items = payload["data"]
            if any(not isinstance(item, dict) or not isinstance(item.get("id"), str)
                   or not isinstance(item.get("path"), str) for item in items):
                raise RuntimeError(f"{layout}: invalid V2 skill entry")
            found = {item["id"]: item["path"] for item in items}
            missing = [name for name, path in expected.items() if found.get(name) != path]
            if not missing:
                print(f"{layout}: opencode discovered all {len(expected)} skills", flush=True)
                return
            # Registration is asynchronous: a fresh API call can return [] or builtins only.
            # Keep one service alive and wait for the expected IDs, never just nonempty data.
            if time.monotonic() >= deadline:
                raise RuntimeError(f"{layout}: opencode did not discover {', '.join(missing)}")
            time.sleep(.2)
    finally:
        cli("service", "stop")


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
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error)) from error
