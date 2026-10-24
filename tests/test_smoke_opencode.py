"""Exercise the discovery runner with only the external CLI mocked."""

import importlib.util
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def smoke():
    spec = importlib.util.spec_from_file_location("smoke_opencode", ROOT / "scripts/smoke_opencode.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def bundle(tmp_path):
    root = tmp_path / "bundle"
    for name in ("alpha", "beta"):
        directory = root / "skills" / name
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Example\n---\nOK\n")
        (directory / "references").mkdir()
        (directory / "references/policy.md").write_text("Policy\n")
    (root / "skills.json").write_text(json.dumps({"skills": {"alpha": [], "beta": []}}))
    return root


def fake_cli(monkeypatch, smoke, *, omit=None, wrong_path=False, malformed=False, fail=False,
             truncate=False, stop_fails=False, duplicate=False, busy_port=0):
    calls = []
    api_calls = []
    start_attempts = []

    def run(argv, *, cwd, env, **kwargs):
        calls.append((argv, Path(cwd), env))
        assert "OPENCODE_CONFIG_CONTENT" not in env
        assert "LINEAR_API_KEY" not in env
        assert "OPENAI_API_KEY" not in env
        assert kwargs["check"] and kwargs["timeout"] > 0
        if argv[1:3] == ["service", "start"]:
            # Simulate another process taking the free port between getsockname
            # and the first start attempt (retry must pick a new port).
            if len(start_attempts) < int(busy_port):
                start_attempts.append(argv)
                raise subprocess.CalledProcessError(
                    1, argv, stderr="port is already in use by another process")
            start_attempts.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[1:3] == ["service", "stop"] and stop_fails:
            raise subprocess.CalledProcessError(9, argv, stderr="stop broken")
        if argv[1:4] == ["api", "get", "/api/skill"]:
            assert argv[4:] == ["--header", f"x-opencode-directory:{cwd}"]
            if fail:
                raise subprocess.CalledProcessError(1, argv, stderr="API unavailable")
            project = Path(cwd)
            paths = [*project.glob(".*/skills/*/SKILL.md"),
                     *Path(env["HOME"]).glob(".*/skills/*/SKILL.md"),
                     *Path(env["XDG_CONFIG_HOME"]).glob("opencode/skills/*/SKILL.md")]
            # Captured V2 response: envelope data items use id/path, not name/location.
            payload = {"location": {"directory": str(project)}, "data": [
                {"id": p.parent.name, "name": "Display label", "path": str(p), "content": "OK"}
                for p in paths if p.parent.name != omit
            ]}
            if wrong_path:
                next(item for item in payload["data"] if item["id"] == "alpha")["path"] = "/builtin/alpha.md"
            if malformed:
                payload = []
            if duplicate:
                payload["data"].append(dict(payload["data"][0]))
                payload["data"][-1]["path"] = "/foreign/alpha.md"
            api_calls.append(payload)
            body = json.dumps(payload)
            # The real 2.1.3 CLI sometimes returns a truncated body with exit 0.
            # Call 1 stays the empty registration envelope; truncate call 2 only.
            if truncate and len(api_calls) == 2:
                body = body[:-len(body) // 3]
            if len(api_calls) == 1 and not malformed:
                return subprocess.CompletedProcess(
                    argv, 0, json.dumps({"location": {"directory": str(project)}, "data": []}), "")
            return subprocess.CompletedProcess(argv, 0, body, "")
        return subprocess.CompletedProcess(argv, 0, "", "")
    monkeypatch.setattr(smoke.subprocess, "run", run)
    monkeypatch.setattr(smoke.time, "sleep", lambda _: None)
    return calls, api_calls


@pytest.mark.parametrize("layout", [
    "project-agents", "project-opencode", "project-claude",
    "global-agents", "global-opencode", "global-claude",
])
def test_all_layouts_wait_for_registration_and_keep_supporting_files(smoke, bundle, tmp_path, monkeypatch, layout):
    calls, api_calls = fake_cli(monkeypatch, smoke)
    smoke.check_layout(bundle, tmp_path / layout, layout, "opencode", timeout=1)
    assert len(api_calls) == 2
    assert calls[-1][0] == ["opencode", "service", "stop"]
    assert calls[1][0][1:4] == ["service", "set", "port"]
    assert (Path(api_calls[-1]["data"][0]["path"]).parent / "references/policy.md").is_file()


@pytest.mark.parametrize("defect", ["missing", "wrong-path", "malformed", "api-failure"])
def test_discovery_fails_closed_and_stops_its_service(smoke, bundle, tmp_path, monkeypatch, defect):
    calls, _ = fake_cli(monkeypatch, smoke, omit="beta" if defect == "missing" else None,
                        wrong_path=defect == "wrong-path", malformed=defect == "malformed",
                        fail=defect == "api-failure")
    with pytest.raises((RuntimeError, subprocess.CalledProcessError)) as exc:
        smoke.check_layout(bundle, tmp_path / "fixture", "project-agents", "opencode", timeout=.01)
    if defect == "missing":
        assert "beta" in str(exc.value)
    if defect == "wrong-path":
        assert "alpha" in str(exc.value)
    assert calls[-1][0] == ["opencode", "service", "stop"]


def test_truncated_api_response_is_retried_within_the_deadline(smoke, bundle, tmp_path, monkeypatch):
    calls, api_calls = fake_cli(monkeypatch, smoke, truncate=True)
    smoke.check_layout(bundle, tmp_path / "fixture", "project-agents", "opencode", timeout=1)
    assert len(api_calls) == 3
    assert calls[-1][0] == ["opencode", "service", "stop"]


def test_undecodable_or_invalid_responses_until_deadline_fail_with_a_diagnosis(smoke, bundle, tmp_path, monkeypatch):
    calls, _ = fake_cli(monkeypatch, smoke, malformed=True)
    with pytest.raises(RuntimeError) as exc:
        smoke.check_layout(bundle, tmp_path / "fixture", "project-agents", "opencode", timeout=.01)
    assert "invalid V2 skill response" in str(exc.value)
    assert "the deadline" in str(exc.value)
    assert "project-agents" in str(exc.value)
    assert calls[-1][0] == ["opencode", "service", "stop"]


def test_canonical_path_comparison_tolerates_a_symlinked_discovery_path(smoke, bundle, tmp_path, monkeypatch):
    fake_cli(monkeypatch, smoke, wrong_path=True)
    # The expected path is where check_layout copies the skill (the fixture destination),
    # not the bundle source: the fake API 'resolved' /builtin/alpha.md onto that path.
    expected_alpha = str(tmp_path / "fixture" / "project" / ".agents" / "skills" / "alpha" / "SKILL.md")
    monkeypatch.setattr(smoke.os.path, "realpath",
                        lambda p: expected_alpha if str(p) == "/builtin/alpha.md" else str(p))
    # A success path, so the deadline must outlast the first poll: a 10 ms budget loses the
    # race under load and fails with "did not discover" instead of exercising the path check.
    # One second matches the other success-path tests in this file; the fake CLI answers on the
    # first poll, so it is a bound on the race, not a wait.
    smoke.check_layout(bundle, tmp_path / "fixture", "project-agents", "opencode", timeout=1)


def test_stop_failure_preserves_the_discovery_error_and_reports_cleanup(smoke, bundle, tmp_path, monkeypatch):
    calls, _ = fake_cli(monkeypatch, smoke, fail=True, stop_fails=True)
    with pytest.raises(RuntimeError) as exc:
        smoke.check_layout(bundle, tmp_path / "fixture", "project-agents", "opencode", timeout=.01)
    message = str(exc.value)
    assert "API unavailable" in message
    assert "service stop" in message
    assert calls[-1][0] == ["opencode", "service", "stop"]


def test_stop_failure_after_success_fails_the_layout(smoke, bundle, tmp_path, monkeypatch):
    fake_cli(monkeypatch, smoke, stop_fails=True)
    with pytest.raises(RuntimeError, match="service stop"):
        smoke.check_layout(bundle, tmp_path / "fixture", "project-agents", "opencode", timeout=1)


def test_occupied_port_is_retried_with_a_new_port(smoke, bundle, tmp_path, monkeypatch):
    calls, _ = fake_cli(monkeypatch, smoke, busy_port=1)
    smoke.check_layout(bundle, tmp_path / "fixture", "project-agents", "opencode", timeout=1)
    sets = [argv for argv, _, _ in calls if argv[1:3] == ["service", "set"]]
    starts = [argv for argv, _, _ in calls if argv[1:3] == ["service", "start"]]
    assert len(sets) == 2
    assert len(starts) == 2
    assert calls[-1][0] == ["opencode", "service", "stop"]


def test_persistent_occupied_port_fails_the_layout(smoke, bundle, tmp_path, monkeypatch):
    calls, _ = fake_cli(monkeypatch, smoke, busy_port=99)
    with pytest.raises(RuntimeError, match="port is already in use|in use"):
        smoke.check_layout(bundle, tmp_path / "fixture", "project-agents", "opencode", timeout=.01)
    # Nothing was ever started, so nothing is stopped (and three fresh ports were tried).
    assert not any(argv[1:3] == ["service", "stop"] for argv, _, _ in calls)
    assert len(calls) == 7  # git init + 3 x (set + start)


def test_duplicate_id_with_a_different_path_is_rejected(smoke, bundle, tmp_path, monkeypatch):
    fake_cli(monkeypatch, smoke, duplicate=True)
    with pytest.raises(RuntimeError, match="duplicate id [a-z]+"):
        smoke.check_layout(bundle, tmp_path / "fixture", "project-agents", "opencode", timeout=.01)


def test_manifest_prevents_deleted_skill_from_shrinking_expectation(smoke, bundle, tmp_path, monkeypatch):
    (bundle / "skills/beta/SKILL.md").unlink()
    fake_cli(monkeypatch, smoke)
    with pytest.raises(RuntimeError, match="beta"):
        smoke.check_layout(bundle, tmp_path / "fixture", "project-agents", "opencode", timeout=.01)


def test_ci_pins_v2_and_does_not_use_the_v1_package():
    script = (ROOT / "scripts/smoke-opencode.sh").read_text()
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    assert 'OPENCODE_VERSION:-2.1.2' in script
    assert '@opencode/cli@$version' in script
    assert '"allowScripts":{"@opencode/cli":true}' in script
    assert 'opencode-ai@' not in script
    assert 'debug skill' not in script
    assert 'OPENCODE_VERSION: 2.1.2' in ci
    assert 'OPENCODE_FORCE_INSTALL: "1"' in ci


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf"])
def test_timeout_requires_a_finite_positive_deadline(timeout, tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/smoke_opencode.py"),
         "--root", str(tmp_path / "absent"), "--timeout", timeout],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 2
    assert "--timeout must be finite and positive" in result.stderr


@pytest.fixture
def wrapper_cli(tmp_path, bundle):
    """Keep the wrapper and runner real; replace only their external CLI edges."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "commands.jsonl"
    cli = textwrap.dedent(f"""\
        #!{sys.executable}
        import json, os, sys
        from pathlib import Path
        args = sys.argv[1:]
        with open({str(log)!r}, "a") as stream:
            stream.write(json.dumps({{"tool": "opencode", "argv": args,
                                    "binary": sys.argv[0]}}) + "\\n")
        if args == ["--version"]:
            print("opencode v__VERSION__")
        elif args[:3] == ["service", "set", "port"]:
            assert len(args) == 4 and int(args[3]) > 0
        elif args in (["service", "start"], ["service", "stop"]):
            pass
        elif args[:3] == ["api", "get", "/api/skill"]:
            assert len(args) == 5 and args[3] == "--header"
            assert args[4].startswith("x-opencode-directory:")
            project = Path(args[4].split(":", 1)[1])
            assert project == Path.cwd()
            home = Path(os.environ["HOME"])
            bases = [project / name for name in (".agents", ".claude", ".opencode")]
            bases += [home / ".agents", home / ".claude",
                      Path(os.environ["XDG_CONFIG_HOME"]) / "opencode"]
            paths = [path for base in bases for path in base.glob("skills/*/SKILL.md")]
            assert paths
            print(json.dumps({{"data": [{{"id": p.parent.name, "path": str(p)}}
                                       for p in paths]}}))
        else:
            raise SystemExit("Unexpected opencode command: " + repr(args))
    """)

    def run(*, installed, requested, force=False, failure=None):
        opencode = bin_dir / "opencode"
        opencode.write_text(cli.replace("__VERSION__", installed))
        opencode.chmod(0o755)
        npm = bin_dir / "npm"
        npm.write_text(textwrap.dedent(f"""\
            #!{sys.executable}
            import json, sys
            from pathlib import Path
            args = sys.argv[1:]
            prefix = Path(args[args.index("--prefix") + 1])
            with open({str(log)!r}, "a") as stream:
                stream.write(json.dumps({{"tool": "npm", "argv": args,
                    "manifest": json.loads((prefix / "package.json").read_text())}}) + "\\n")
            if {failure!r} == "npm":
                raise SystemExit(42)
            target = prefix / "node_modules/.bin/opencode"
            target.parent.mkdir(parents=True)
            version = "0.0.0" if {failure!r} == "version" else args[-1].split("@")[-1]
            target.write_text({cli!r}.replace("__VERSION__", version))
            target.chmod(0o755)
        """))
        npm.chmod(0o755)
        env = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}",
                   OPENCODE_VERSION=requested)
        env.pop("OPENCODE_FORCE_INSTALL", None)
        if force:
            env["OPENCODE_FORCE_INSTALL"] = "1"
        result = subprocess.run(
            ["bash", str(ROOT / "scripts/smoke-opencode.sh"),
             "--root", str(bundle), "--timeout", "1"],
            env=env, text=True, capture_output=True, timeout=30,
        )
        return result, [json.loads(line) for line in log.read_text().splitlines()]

    return run


@pytest.mark.parametrize("installed,requested,force,installs", [
    ("2.1.2", "2.3.4", False, True),  # Explicit override replaces another CLI.
    ("2.3.4", "2.3.4", True, True),   # Forced install even when already matching.
    ("2.3.4", "2.3.4", False, False),
])
def test_wrapper_selects_requested_version_and_runs_discovery(
        wrapper_cli, installed, requested, force, installs):
    result, calls = wrapper_cli(installed=installed, requested=requested, force=force)
    assert result.returncode == 0, result.stderr
    npm_calls = [call for call in calls if call["tool"] == "npm"]
    assert len(npm_calls) == int(installs)
    if installs:
        install = npm_calls[0]
        assert install["manifest"] == {"private": True, "allowScripts": {"@opencode/cli": True}}
        assert install["argv"] == ["install", "--prefix", install["argv"][2],
                                   "--no-audit", "--no-fund", "--ignore-scripts=false",
                                   f"@opencode/cli@{requested}"]
    discovery = [call for call in calls if call["argv"][:3] == ["api", "get", "/api/skill"]]
    assert len(discovery) == 6
    assert result.stdout.count("opencode discovered all 2 skills") == 6
    assert sum(call["argv"] == ["service", "stop"] for call in calls) == 6
    for call in discovery:
        assert ("node_modules/.bin/opencode" in call["binary"]) == installs


@pytest.mark.parametrize("failure", ["npm", "version"])
def test_wrapper_install_failure_never_starts_discovery(wrapper_cli, failure):
    result, calls = wrapper_cli(installed="2.1.2", requested="2.3.4", failure=failure)
    assert result.returncode != 0
    assert sum(call["tool"] == "npm" for call in calls) == 1
    assert all(call["argv"] == ["--version"] for call in calls if call["tool"] == "opencode")
    assert "opencode discovered" not in result.stdout
    if failure == "npm":
        assert result.returncode == 42
    else:
        assert "Expected OpenCode 2.3.4" in result.stderr
