"""Structural checks every skill must pass, on any runtime."""

import json
import re
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted(p.parent for p in (ROOT / "skills").glob("*/SKILL.md"))
SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())
SPEC_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
EM_DASH = chr(0x2014)
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# Any profile.<path>, quoted or not (code blocks cite keys bare). The whole token up to a
# real terminator is captured, so a malformed key (`a..b`, `a/x`, `a[0]`, a typo suffix)
# fails schema resolution instead of matching a valid prefix. A single trailing `.` is
# sentence punctuation. profile.md and the other file names are not keys; profile.<path>
# is a placeholder.
PROFILE_REF_RE = re.compile(
    r"(?<![\w./-])profile\.(?!(?:md|yaml|json)\b)(?!<)"
    r"([^\s`'\"(),;:!?<>]+?)(?=\.?(?:$|[\s`'\"(),;:!?<>]))",
    re.M,
)

# Tool and path names of one runtime. Skill text names capabilities; shared/runtimes.md maps them.
RUNTIME_TERMS = re.compile(
    r"\b(TaskCreate|TaskUpdate|TodoWrite|todowrite|AskUserQuestion|subagent_type|CLAUDE_JOB_DIR)\b"
    r"|mcp__|~/\.claude/|\.opencode/"
)


def split_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text()
    assert text.startswith("---\n"), f"{path} must start with YAML frontmatter"
    head, body = text[4:].split("\n---\n", 1)
    return yaml.safe_load(head), body


def md_files() -> list[Path]:
    return sorted(
        p for p in ROOT.rglob("*.md")
        if ".git" not in p.parts and ".venv" not in p.parts
    )


@pytest.fixture(params=SKILLS, ids=lambda p: p.name)
def skill(request) -> Path:
    return request.param


def test_there_are_skills():
    assert SKILLS


def test_frontmatter_follows_spec(skill):
    meta, body = split_frontmatter(skill / "SKILL.md")
    assert set(meta) <= SPEC_KEYS, f"non-spec keys: {set(meta) - SPEC_KEYS}"
    assert NAME_RE.match(meta["name"]) and len(meta["name"]) <= 64
    assert meta["name"] == skill.name, "name must match the directory"
    assert 1 <= len(meta["description"]) <= 1024
    assert meta.get("license") == "Apache-2.0"
    if "compatibility" in meta:
        assert 1 <= len(meta["compatibility"]) <= 500
    if "metadata" in meta:
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in meta["metadata"].items())
    assert len(body.splitlines()) < 500, "keep SKILL.md under 500 lines; move detail to references/"


def test_links_stay_inside_the_skill(skill):
    for md in skill.rglob("*.md"):
        for target in LINK_RE.findall(md.read_text()):
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue
            resolved = (md.parent / target.split("#", 1)[0]).resolve()
            assert resolved.is_relative_to(skill.resolve()), f"{md}: {target} leaves the skill"
            assert resolved.exists(), f"{md}: {target} does not exist"


def test_no_runtime_specific_terms():
    exempt = {ROOT / "shared" / "runtimes.md", ROOT / "README.md"}
    offenders = []
    for md in md_files():
        if md in exempt or md.name == "runtimes.md":
            continue
        for n, line in enumerate(md.read_text().splitlines(), 1):
            if RUNTIME_TERMS.search(line):
                offenders.append(f"{md.relative_to(ROOT)}:{n}: {line.strip()}")
    assert not offenders, "\n".join(offenders)


def resolve_schema_path(path: str) -> bool:
    node = SCHEMA
    for part in path.split("."):
        is_array = part.endswith("[]")
        key = part.removesuffix("[]")
        if "$ref" in node:
            node = SCHEMA["$defs"][node["$ref"].split("/")[-1]]
        props = node.get("properties", {})
        if key in props:
            node = props[key]
        elif isinstance(node.get("additionalProperties"), dict):
            node = node["additionalProperties"]
        else:
            return False
        if is_array:
            if node.get("type") != "array":
                return False
            node = node["items"]
        if "$ref" in node:
            node = SCHEMA["$defs"][node["$ref"].split("/")[-1]]
    return True


def test_profile_ref_regex_captures_whole_token():
    cases = {
        "`profile.git.integration_branchTypo`": "git.integration_branchTypo",
        "use profile.git.integration_branch-x here": "git.integration_branch-x",
        "Target profile.git.integration_branch.": "git.integration_branch",
        "see profile.md and profile.yaml": None,
        "cite profile.<path> here": None,
        "profile.git.integration_branch..bad": "git.integration_branch..bad",
        "profile.git..integration_branch": "git..integration_branch",
        "profile.environments[0].url": "environments[0].url",
        "profile.git.integration_branch/x": "git.integration_branch/x",
        "profile.git.integration_branch\u00e9": "git.integration_branch\u00e9",
        "`profile.environments[].preauthorized`": "environments[].preauthorized",
        "each `profile.review.*` role": "review.*",
    }
    for text, want in cases.items():
        got = PROFILE_REF_RE.findall(text)
        assert got == ([want] if want else []), (text, got)
    for bad in ["git.integration_branchTypo", "git.integration_branch-x", "git.integration_branch..bad",
                "git..integration_branch", "environments[0].url", "git.integration_branch/x",
                "git.integration_branch\u00e9"]:
        assert not resolve_schema_path(bad), bad
    assert resolve_schema_path("environments[].preauthorized")


def test_profile_references_exist_in_schema():
    missing = []
    for md in md_files():
        for ref in PROFILE_REF_RE.findall(md.read_text()):
            if ref.startswith("extra"):
                missing.append(f"{md.relative_to(ROOT)}: base text must not read profile.extra")
            elif not resolve_schema_path(ref.removesuffix(".*")):  # `.*` names a whole section
                missing.append(f"{md.relative_to(ROOT)}: profile.{ref}")
    assert not missing, "\n".join(missing)


def test_example_profile_matches_schema():
    example = yaml.safe_load((ROOT / "profile" / "example.yaml").read_text())
    jsonschema.validate(example, SCHEMA)


def test_schema_rejects_unknown_keys():
    example = yaml.safe_load((ROOT / "profile" / "example.yaml").read_text())
    example["git"]["integration_brnach"] = "develop"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(example, SCHEMA)


def test_vendored_references_are_current():
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "vendor_shared.py"), "--check"],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr


def test_no_em_dash():
    offenders = [
        str(p.relative_to(ROOT))
        for p in ROOT.rglob("*")
        if p.is_file()
        and ".git" not in p.parts
        and ".venv" not in p.parts
        and p.suffix in {".md", ".py", ".json", ".yaml", ".yml", ".sh", ".js", ".txt", ".toml"}
        and EM_DASH in p.read_text(errors="ignore")
    ]
    assert not offenders, offenders


def test_schema_rejects_preauthorized_production():
    example = yaml.safe_load((ROOT / "profile" / "example.yaml").read_text())
    prod = next(e for e in example["environments"] if e.get("production"))
    prod["preauthorized"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(example, SCHEMA)


def test_every_mentioned_reference_exists(skill):
    missing = sorted(
        {
            f"{md.relative_to(ROOT)} mentions {ref}"
            for md in skill.rglob("*")
            if md.is_file() and md.suffix in {".md", ".sh", ".js", ".json"}
            for ref in re.findall(r"references/[a-z0-9-]+\.md", md.read_text())
            if not (skill / ref).is_file()
        }
    )
    assert not missing, "\n".join(missing)
