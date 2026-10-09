"""Structural checks every skill must pass, on any runtime."""

import json
import re
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted(p.parent for p in (ROOT / "skills").glob("*/SKILL.md"))
SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())
SPEC_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
EM_DASH = chr(0x2014)
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# Any profile.<path>, quoted or not (code blocks cite keys bare). A CommonMark parser strips
# emphasis, links and escapes, and the whole literal token up to a real terminator is the
# reference, so a malformed key (`a..b`, `a/x`, `a[0]`, a typo or stray `*` or `]` suffix)
# fails schema resolution instead of matching a valid prefix. Outside inline code one
# sentence-final `.` is punctuation. profile.md and the other file names are not keys;
# profile.<path> is a placeholder. A trailing `.*` names a whole section and resolves only
# when that key is an object.
PROFILE_REF_RE = re.compile(
    r"(?<![\w./-])profile\.(?!(?:md|yaml|json)\b)(?!<)([^\s`'\"(),;:!?<>]+)"
)
MARKDOWN = MarkdownIt("commonmark")


def profile_refs(text: str) -> list[str]:
    refs = []

    def scan(literal: str, is_code: bool) -> None:
        for ref in PROFILE_REF_RE.findall(literal):
            refs.append(ref if is_code else ref.removesuffix("."))

    def walk(tokens: list) -> None:
        for tok in tokens:
            if tok.children:
                walk(tok.children)  # inline content, and an image's alt text
            elif tok.type in ("text", "code_inline", "html_inline"):
                scan(tok.content, tok.type == "code_inline")

    for block in MARKDOWN.parse(text):
        if block.type == "inline":
            walk(block.children)
        elif block.content:
            scan(block.content, False)
    return refs


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


# An agent that judges work is clean and neutral together (shared/code-review.md), so a
# paragraph or list that makes an agent clean must also make it neutral, and the reverse.
CLEAN_RE = re.compile(
    r"(?i)\bclean[- ]context|\bown (?:clean )?context|\bclean (?:\w+ )?(?:agent|subagent|verifier|reviewer|adjudicator)\b"
    r"|\bfresh (?:\w+ ){0,2}?(?:agent|subagent|verifier|reviewer|adjudicator|context)\b"
    r"|\bbrief (?:a|the) fresh\b|\bto (?:a|the) fresh one\b|\bclean, neutral|\bclean and neutral|\*\*clean:\*\*"
)
NEUTRAL_RE = re.compile(r"(?i)(?<!runtime-)\bneutral")


def pairing_broken(block: str) -> bool:
    return bool(CLEAN_RE.search(block)) != bool(NEUTRAL_RE.search(block))


def schema_descriptions(node) -> list[str]:
    if isinstance(node, dict):
        found = [node["description"]] if isinstance(node.get("description"), str) else []
        return found + [d for v in node.values() for d in schema_descriptions(v)]
    if isinstance(node, list):
        return [d for v in node for d in schema_descriptions(v)]
    return []


def test_clean_neutral_pairing_check():
    for block in ["then a separate clean-context adjudicator.", "A fresh verifier tries to refute each finding.",
                  "else brief a fresh one with the PR state", "Spawn a clean subagent in its own context.",
                  "The brief is neutral: facts only.", "A clean verifier checks the findings.",
                  "A clean reviewer reads it.", "Hand the task to a fresh one."]:
        assert pairing_broken(block), block
    for block in ["then a separate clean, neutral adjudicator.", "Create a fresh one from the base.",
                  "The skills are runtime-neutral.", "The gate is clean on the head."]:
        assert not pairing_broken(block), block


def test_clean_and_neutral_go_together():
    offenders = []
    for md in md_files():
        for block in re.split(r"\n\s*\n", md.read_text()):
            if pairing_broken(block):
                offenders.append(f"{md.relative_to(ROOT)}: {block.strip().splitlines()[0]}")
    for description in schema_descriptions(SCHEMA):
        if pairing_broken(description):
            offenders.append(f"profile/schema.json: {description}")
    assert not offenders, "\n".join(offenders)


def schema_node(path: str) -> dict | None:
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
            return None
        if is_array:
            if node.get("type") != "array":
                return None
            node = node["items"]
        if "$ref" in node:
            node = SCHEMA["$defs"][node["$ref"].split("/")[-1]]
    return node


def resolve_schema_path(path: str) -> bool:
    if path.endswith(".*"):
        node = schema_node(path.removesuffix(".*"))
        return node is not None and (
            "properties" in node or isinstance(node.get("additionalProperties"), dict)
        )
    return schema_node(path) is not None


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
        "[profile.git.integration_branch](guide.md)": "git.integration_branch",
        "*profile.git.integration_branch*": "git.integration_branch",
        "**profile.git.integration_branch**": "git.integration_branch",
        "[profile.environments[].preauthorized](x)": "environments[].preauthorized",
        "profile.git.x]y": "git.x]y",
        "profile.git.integration_branch/x": "git.integration_branch/x",
        "profile.git.integration_branch\u00e9": "git.integration_branch\u00e9",
        "`profile.environments[].preauthorized`": "environments[].preauthorized",
        "each `profile.review.*` role": "review.*",
        "each profile.review.* role": "review.*",
        "``profile.git.integration_branch*``": "git.integration_branch*",
        "`` `profile.git.integration_branch*` ``": "git.integration_branch*",
        "`profile.git.integration_branch.*`": "git.integration_branch.*",
        "profile.git.integration_branch.*[docs](guide.md)": "git.integration_branch.*",
        "profile.review.*[docs](guide.md)": "review.*",
        "see profile.review.*.": "review.*",
        "profile.review.*[0].name": "review.*[0].name",
        "*profile.git.integration_branch*.": "git.integration_branch",
        "[*profile.git.integration_branch*](guide.md)": "git.integration_branch",
        "profile.git.integration_branch..": "git.integration_branch.",
        "profile.git.integration_branch]]": "git.integration_branch]]",
        "profile.git.integration_branch[0](": "git.integration_branch[0]",
        "profile.git.integration_branch*": "git.integration_branch*",
        "\\[[profile.git.integration_branch]]": "git.integration_branch]]",
        "**bold** profile.git.integration_branch**": "git.integration_branch**",
        "profile.git.integration_branch[docs](guide(v2).md)": "git.integration_branch",
        "[profile.git.integration_branch](guide.md \"Guide\")": "git.integration_branch",
        "![profile.git.integration_branchTypo](icon.svg)": "git.integration_branchTypo",
        "![`profile.git.integration_branch.`](icon.svg)": "git.integration_branch.",
        "`profile.git.integration_branch*Typo`": "git.integration_branch*Typo",
        "`profile.git.integration_branch*`": "git.integration_branch*",
        "`profile.git.integration_branch.`": "git.integration_branch.",
        "**profile.git.integration_branch**[docs](guide.md)": "git.integration_branch",
        "profile.git.integration_branch*Typo": "git.integration_branch*Typo",
        "```bash profile.git.integration_branch": None,
    }
    for text, want in cases.items():
        got = profile_refs(text)
        assert got == ([want] if want else []), (text, got)
    for bad in ["git.integration_branchTypo", "git.integration_branch-x", "git.integration_branch..bad",
                "git..integration_branch", "environments[0].url", "git.x]y", "git.integration_branch/x",
                "git.integration_branch\u00e9", "git.integration_branch*Typo",
                "git.integration_branch*", "git.integration_branch.", "git.integration_branch.*",
                "review.*[0].name", "git.integration_branch]]", "git.integration_branch[0]",
                "git.integration_branch*"]:
        assert not resolve_schema_path(bad), bad
    assert resolve_schema_path("environments[].preauthorized")
    assert resolve_schema_path("review.*")


def test_profile_references_exist_in_schema():
    missing = []
    for md in md_files():
        for ref in profile_refs(md.read_text()):
            if ref.startswith("extra"):
                missing.append(f"{md.relative_to(ROOT)}: base text must not read profile.extra")
            elif not resolve_schema_path(ref):
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
