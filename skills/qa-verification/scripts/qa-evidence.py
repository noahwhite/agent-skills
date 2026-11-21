# GENERATED from shared/qa-evidence.py by scripts/vendor_shared.py. Edit the source, then rerun the script.
#!/usr/bin/env python3
"""Generate the QA evidence README skeleton for a story.

Writes `<evidence-dir>/<KEY>/README.md` with the headings, metadata lines and verdict table
`skills/qa-verification/SKILL.md` section 5 requires, so the QA agent fills verdicts and evidence
instead of authoring the structure.

  python3 qa-evidence.py --key SKL-386 --item='AC1 - one generator' [--item='AC2 - ...']
                         [--path spike|no-deployment|deployed] [--evidence-dir docs/qa-evidence]

The verdict and evidence cells are left empty, because a generated verdict would be an authored
result. An existing README is refused before any label is validated, with one line naming it, and
the README is then published atomically without overwriting, so a concurrent writer, a dangling
symlink at its path and a symlinked story directory are refused too, and a failed write removes its
temporary file and never leaves a README behind. A key outside ^[A-Z][A-Z0-9]+-[0-9]+$, an empty
`--evidence-dir`, and a story key the doc-lint rejects all exit 1 naming what is wrong.

A label is Markdown text, written as one table cell: its line breaks fold to spaces, runs of
whitespace collapse, and a backslash and a literal `|` are escaped, so the cell renders the label
you passed and a label can never add a column, a row or a heading. A label this repository's
doc-lint would reject exits 1 with one stderr line naming it: an empty label, and one that, as
written or as Markdown renders it, carries U+2014, a stray term, a verdict word, a runtime-specific
term, an unresolvable `profile.` reference (checked against the target repository's own
`profile/schema.json` when it has one), or the British spelling of artifact outside the evidence
tree that lint exempts.

It reads no tracker, makes no network call and needs no credential.
"""

import argparse
import html
import json
import os
import re
import sys
import tempfile
from pathlib import Path

DEFAULT_EVIDENCE_DIR = "docs/qa-evidence"
KEY_RE = re.compile(r"[A-Z][A-Z0-9]+-[0-9]+")
PATHS = ("spike", "no-deployment", "deployed")
TABLE_HEADER = "| Item | Verdict | Evidence |"
TABLE_SEPARATOR = "| --- | --- | --- |"
EM_DASH = "\u2014"
BRITISH_ARTIFACT = "arte" + "fact"
# The rules below mirror the doc-lint in tests/test_skills.py, which every committed Markdown file
# must pass; tests/test_qa_evidence.py asserts the copied patterns are that lint's own, and compares
# the decisions below with its helpers.
VERDICT_RE = re.compile(
    r"(?i)\b(?:verified|failed|correct by design|out of scope|not covered|pending owner ruling)\b"
)
CANONICAL_RE = re.compile(r"(?i)\bclean(?:,| and) neutral\b")
STRAY_RE = re.compile(
    r"(?i)\bclean[- ]context|\bown (?:clean )?context|\bclean,? (?:[\w-]+,? ){0,2}?(?:agent|subagent|verifier|reviewer|adjudicator|engineer)\b"
    r"|\bfresh (?:\w+ ){0,2}?(?:agent|subagent|verifier|reviewer|adjudicator|context)\b"
    r"|\bbrief (?:a|the) fresh\b|\b(?:hand|delegate|pass)\w* (?:\w+ ){0,3}?to (?:a|the) fresh one\b"
    r"|(?<!runtime-)\bneutral"
)
RUNTIME_TERMS_RE = re.compile(
    r"\b(TaskCreate|TaskUpdate|TodoWrite|todowrite|AskUserQuestion|subagent_type|CLAUDE_JOB_DIR)\b"
    r"|mcp__|~/\.claude/|\.opencode/"
)
PROFILE_REF_RE = re.compile(
    r"(?<![\w./-])profile\.(?!(?:md|yaml|json)\b)(?!<)([^\s`'\"(),;:!?<>]+)"
)
ESCAPE_RE = re.compile(r"\\([!-/:-@\[-`{-~])")
TAG_RE = re.compile(r"<[^>]*>")
MARKER_RE = re.compile(r"[*`]+")
# CommonMark treats `_` as emphasis only at a word boundary, so an identifier keeps its underscores.
UNDERSCORE_RE = re.compile(r"(?<!\w)_+|_+(?!\w)")
# The characters a CommonMark backslash escape can quote, and the delimiter pairs the reader strips.
ESCAPABLE = set("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
EMPHASIS_PATTERNS = (
    re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.S),
    re.compile(r"(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w)", re.S),
    re.compile(r"\*(?=\S)(.+?)(?<=\S)\*", re.S),
    re.compile(r"(?<!\w)_(?=\S)(.+?)(?<=\S)_(?!\w)", re.S),
)


def one_line(text: str) -> str:
    """A diagnostic fragment that can never break the single stderr line it sits in."""
    return text.replace("\r", "\\r").replace("\n", "\\n")


def metadata_lines(path: str | None) -> list[str]:
    """The metadata lines, with the path-dependent ones only where the path calls for them."""
    lines = ["Date:", "Fixtures:"]
    if path is not None:
        lines.append(f"Path: {path}")
        lines.extend(["Environment:", "Build:"] if path == "deployed" else ["Target:"])
    return lines


def clean_label(label: str) -> str:
    """One table cell's text: breaks folded, whitespace collapsed, backslash and pipe escaped."""
    folded = " ".join(label.split())
    return folded.replace("\\", "\\\\").replace("|", r"\|")


def rendered_text(label: str) -> str:
    """The text Markdown renders for `label`, so a rule cannot be hidden behind markup."""
    text = html.unescape(label)
    text = ESCAPE_RE.sub(r"\1", text)
    text = TAG_RE.sub(" ", text)
    text = MARKER_RE.sub("", text)
    return UNDERSCORE_RE.sub("", text)


def lint_problem(text: str, *, spelling: bool) -> str | None:
    """Why `text` would make the generated README fail the repository's doc-lint, or None."""
    if EM_DASH in text:
        return "carries U+2014"
    if STRAY_RE.search(CANONICAL_RE.sub("", text)):
        return "trips the stray-term lint"
    verdict = VERDICT_RE.search(text)
    if verdict:
        return f"carries the verdict word {verdict.group(0)!r}"
    runtime = RUNTIME_TERMS_RE.search(text)
    if runtime:
        return f"carries the runtime-specific term {runtime.group(0)!r}"
    if spelling and BRITISH_ARTIFACT in text.lower():
        return "uses the British spelling of artifact, which the lint requires only in evidence files"
    return None


def strip_emphasis(text: str) -> str:
    """`text` with the balanced emphasis delimiters a CommonMark reader removes, wildcards kept."""
    for _ in range(3):
        before = text
        for pattern in EMPHASIS_PATTERNS:
            text = pattern.sub(r"\1", text)
        if text == before:
            break
    return text


def matching(text: str, start: int, opener: str, closer: str) -> int:
    """The index of the `closer` that balances the `opener` at `start`, or -1."""
    depth = 0
    index = start
    while index < len(text):
        if text[index] == "\\" and index + 1 < len(text):
            index += 2
            continue
        if text[index] == opener:
            depth += 1
        elif text[index] == closer:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def skip_link_tail(text: str, position: int) -> int:
    """Where the inline content resumes after a link or image body, skipping its destination."""
    if position < len(text) and text[position] == "(":
        end = matching(text, position, "(", ")")
        return len(text) if end == -1 else end + 1
    if position < len(text) and text[position] == "[":
        end = matching(text, position, "[", "]")
        return len(text) if end == -1 else end + 1
    return position


def inline_segments(text: str) -> list[tuple[str, bool]]:
    """The `(literal, is_code)` runs a CommonMark reader scans, in order.

    Code spans are literal and keep a trailing dot; link destinations and reference labels are
    not scanned; link text, image alt text and inline HTML are; escapes and entities decode in
    text; emphasis delimiters are removed. This mirrors the doc-lint's token walk in
    tests/test_skills.py, which the generated README must pass.
    """
    segments: list[tuple[str, bool]] = []
    pending: list[str] = []

    def flush() -> None:
        if pending:
            segments.append((html.unescape(strip_emphasis("".join(pending))), False))
            pending.clear()

    index = 0
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text):
            quoted = text[index + 1]
            pending.append(quoted if quoted in ESCAPABLE else char)
            index += 2 if quoted in ESCAPABLE else 1
            continue
        if char == "`":
            end = index
            while end < len(text) and text[end] == "`":
                end += 1
            width = end - index
            scan = end
            close = -1
            while scan < len(text):
                if text[scan] == "`":
                    run = scan
                    while run < len(text) and text[run] == "`":
                        run += 1
                    if run - scan == width:
                        close = scan
                        break
                    scan = run
                else:
                    scan += 1
            if close == -1:
                pending.append(text[index:end])
                index = end
                continue
            flush()
            content = text[end:close]
            if len(content) >= 2 and content[0] == " " and content[-1] == " " and content.strip():
                content = content[1:-1]
            segments.append((content, True))
            index = close + width
            continue
        if char == "!" and index + 1 < len(text) and text[index + 1] == "[":
            end = matching(text, index + 1, "[", "]")
            if end != -1 and end + 1 < len(text) and text[end + 1] in "([":
                flush()
                segments.extend(inline_segments(text[index + 2:end]))
                index = skip_link_tail(text, end + 1)
                continue
        if char == "[":
            end = matching(text, index, "[", "]")
            if end != -1 and end + 1 < len(text) and text[end + 1] in "([":
                flush()
                segments.extend(inline_segments(text[index + 1:end]))
                index = skip_link_tail(text, end + 1)
                continue
        if char == "<":
            if text.startswith("<!--", index):
                close = text.find("-->", index + 4)
                if close != -1:
                    flush()
                    segments.append((text[index:close + 3], False))
                    index = close + 3
                    continue
            close = text.find(">", index + 1)
            if close != -1 and "\n" not in text[index:close]:
                flush()
                segments.append((text[index:close + 1], False))
                index = close + 1
                continue
        pending.append(char)
        index += 1
    flush()
    return segments


def ref_candidates(text: str) -> list[str]:
    """The `profile.` references the doc-lint reads in `text`, a sentence-final dot removed."""
    refs = []
    for literal, is_code in inline_segments(text):
        for match in PROFILE_REF_RE.finditer(literal):
            ref = match.group(1)
            refs.append(ref if is_code else ref.removesuffix("."))
    return refs


def repository_root() -> Path:
    """The target repository root: the nearest ancestor with a schema, else with a `.git`."""
    here = Path.cwd()
    for candidate in (here, *here.parents):
        if (candidate / "profile" / "schema.json").is_file():
            return candidate
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return here


def local_schema(root: Path) -> tuple[dict | None, str | None]:
    """The target repository's profile schema, or None when it has none, with any read problem."""
    candidate = root / "profile" / "schema.json"
    if not candidate.is_file():
        return None, None
    try:
        return json.loads(candidate.read_text(encoding="utf-8")), None
    except (OSError, ValueError) as exc:
        return None, f"error: cannot read {one_line(str(candidate))}: {exc}"


def deref(node, defs: dict) -> dict:
    """A node with its `$ref`, or its `allOf` of exactly one `$ref`, resolved."""
    seen: set[str] = set()
    while isinstance(node, dict):
        if "$ref" in node:
            name = node["$ref"].split("/")[-1]
            if name in seen or name not in defs:
                return {}
            seen.add(name)
            node = defs[name]
        elif "properties" not in node and [list(item) for item in node.get("allOf", [])] == [["$ref"]]:
            node = node["allOf"][0]
        else:
            return node
    return {}


def schema_node(schema: dict, path: str) -> dict | None:
    """The node `path` names in `schema`, following properties, arrays and additional properties."""
    defs = schema.get("$defs", {})
    node: dict = schema
    for part in path.split("."):
        is_array = part.endswith("[]")
        key = part.removesuffix("[]")
        node = deref(node, defs)
        properties = node.get("properties", {})
        if key in properties:
            node = properties[key]
        elif isinstance(node.get("additionalProperties"), dict):
            node = node["additionalProperties"]
        else:
            return None
        if is_array:
            if node.get("type") != "array":
                return None
            node = node.get("items", {})
        node = deref(node, defs)
    return node


def resolves_ref(schema: dict, ref: str) -> bool:
    """Whether `ref`, the text after `profile.`, resolves in `schema`, wildcards included."""
    if ref.endswith(".*"):
        node = schema_node(schema, ref.removesuffix(".*"))
        return node is not None and (
            "properties" in node or isinstance(node.get("additionalProperties"), dict)
        )
    return schema_node(schema, ref) is not None


def refs_problem(schema: dict | None, text: str) -> str | None:
    """Why a reference in `text` would fail the doc-lint, or None; nothing without a schema."""
    if schema is None:
        return None
    for ref in ref_candidates(text):
        if ref.startswith("extra"):
            return f"carries profile.{ref}, and base text must not read profile.extra"
        if not resolves_ref(schema, ref):
            return f"carries the profile reference profile.{ref}, which the profile schema does not resolve"
    return None


def spelling_applies(root: Path, evidence_dir: str) -> bool:
    """The spelling lint exempts frozen QA evidence, so it applies outside that tree only."""
    target = Path(os.path.normpath(os.path.join(str(Path.cwd()), evidence_dir)))
    try:
        relative = target.relative_to(root)
    except ValueError:
        return True
    path = relative.as_posix()
    return not (path == DEFAULT_EVIDENCE_DIR or path.startswith(DEFAULT_EVIDENCE_DIR + "/"))


def key_syntax_problem(key: str) -> str | None:
    """Why `key` cannot name an evidence directory at all, or None when it can."""
    if not KEY_RE.fullmatch(key):
        return f"error: {key!r} is not a story key (expected ^[A-Z][A-Z0-9]+-[0-9]+$)"
    return None


def key_content_problem(key: str, *, spelling: bool) -> str | None:
    """Why `key` would make the generated README fail the doc-lint, or None when it would not."""
    for text in (key, rendered_text(key)):
        problem = lint_problem(text, spelling=spelling)
        if problem is not None:
            return f"error: story key {key!r} {problem}"
    return None


def label_problem(label: str, *, schema: dict | None, spelling: bool) -> str | None:
    """Why a cleaned label cannot be written into the skeleton, or None when it can."""
    if not label:
        return "is empty"
    for text in (label, rendered_text(label)):
        problem = lint_problem(text, spelling=spelling)
        if problem is not None:
            return problem
    return refs_problem(schema, label)


def skeleton(key: str, items: list[str], path: str | None) -> str:
    lines = [f"# {key} QA evidence", "", "## QA round 1", "", *metadata_lines(path), ""]
    lines.extend([TABLE_HEADER, TABLE_SEPARATOR])
    lines.extend(f"| {item} |  |  |" for item in items)
    return "\n".join(lines) + "\n"


def publish(target: Path, text: str) -> bool:
    """Publish `text` at `target` without overwriting anything, or report why not."""
    story_dir = target.parent
    if story_dir.is_symlink():
        print(
            f"error: {one_line(str(story_dir.absolute()))} is a symlink; refusing to write the README through it",
            file=sys.stderr,
        )
        return False
    try:
        data = text.encode("utf-8")
    except UnicodeError:
        print(f"error: the skeleton for {one_line(str(target))} cannot be encoded as UTF-8", file=sys.stderr)
        return False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: cannot create {one_line(str(target.parent))}: {exc.strerror or exc}", file=sys.stderr)
        return False
    if story_dir.is_symlink():
        print(
            f"error: {one_line(str(story_dir.absolute()))} is a symlink; refusing to write the README through it",
            file=sys.stderr,
        )
        return False
    direct = target.is_symlink() or target.exists()
    if direct:
        print(f"error: {one_line(str(target.absolute()))} already exists; refusing to overwrite it", file=sys.stderr)
        return False
    temp: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(dir=target.parent, prefix=".qa-evidence-", suffix=".tmp")
        temp = Path(name)
        view = memoryview(data)
        try:
            while view:
                view = view[os.write(descriptor, view):]
        finally:
            os.close(descriptor)
        os.link(temp, target)
    except FileExistsError:
        print(f"error: {one_line(str(target.absolute()))} already exists; refusing to overwrite it", file=sys.stderr)
        return False
    except OSError as exc:
        print(f"error: cannot write {one_line(str(target.absolute()))}: {exc.strerror or exc}", file=sys.stderr)
        return False
    finally:
        if temp is not None:
            try:
                temp.unlink()
            except OSError:
                pass
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the QA evidence README skeleton for a story.",
        allow_abbrev=False,
    )
    parser.add_argument("--key", required=True, help="Story key, for example SKL-386.")
    parser.add_argument("--item", action="append", default=[], dest="items", help="One verdict table row.")
    parser.add_argument("--path", choices=PATHS, help="The run's path, when it is known.")
    parser.add_argument("--evidence-dir", default=DEFAULT_EVIDENCE_DIR, help="Evidence directory.")
    args = parser.parse_args(argv)

    root = repository_root()
    if not args.evidence_dir:
        print("error: --evidence-dir is empty", file=sys.stderr)
        return 1
    problem = key_syntax_problem(args.key)
    if problem is not None:
        print(problem, file=sys.stderr)
        return 1

    target = Path(args.evidence_dir) / args.key / "README.md"
    if target.is_symlink() or target.exists():
        print(f"error: {one_line(str(target.absolute()))} already exists; refusing to overwrite it", file=sys.stderr)
        return 1

    spelling = spelling_applies(root, args.evidence_dir)
    problem = key_content_problem(args.key, spelling=spelling)
    if problem is not None:
        print(problem, file=sys.stderr)
        return 1

    schema, schema_problem = local_schema(root)
    if schema_problem is not None:
        print(schema_problem, file=sys.stderr)
        return 1
    labels = []
    for raw in args.items:
        label = clean_label(raw)
        problem = label_problem(label, schema=schema, spelling=spelling)
        if problem is not None:
            print(f"error: item label {one_line(repr(raw))} cannot be written: it {problem}", file=sys.stderr)
            return 1
        labels.append(label)

    if not publish(target, skeleton(args.key, labels, args.path)):
        return 1
    print(target.absolute())
    return 0


if __name__ == "__main__":
    sys.exit(main())
