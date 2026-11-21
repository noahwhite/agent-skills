# GENERATED from shared/qa-evidence.py by scripts/vendor_shared.py. Edit the source, then rerun the script.
#!/usr/bin/env python3
"""Generate the QA evidence README skeleton for a story.

Writes `<evidence-dir>/<KEY>/README.md` with the headings, metadata lines and verdict table
`skills/qa-verification/SKILL.md` section 5 requires, so the QA agent fills verdicts and evidence
instead of authoring the structure.

  python3 qa-evidence.py --key SKL-386 --item='AC1 - one generator' [--item='AC2 - ...']
                         [--path spike|no-deployment|deployed] [--evidence-dir docs/qa-evidence]

The verdict and evidence cells are left empty, because a generated verdict would be an authored
result. A relative `--evidence-dir` resolves against the working directory's checkout root, and the
profile schema and spelling policy come from the checkout that owns the destination. An existing
README is refused before any label is validated, with one line naming it, and the README is then
published through opened directory descriptors that refuse every symlink component, without
overwriting anything, so a concurrent writer, a dangling symlink and a symlinked directory are
refused too, and a failed write removes its temporary file and never leaves a README behind. A key
outside ^[A-Z][A-Z0-9]+-[0-9]+$, an empty `--evidence-dir`, and a story key the doc-lint rejects all
exit 1 naming what is wrong.

A label is written as one table cell of literal text: its line breaks fold to spaces, runs of
whitespace collapse, and every Markdown punctuation character is backslash-escaped, so a cell can
never add a column, a row, a heading or inline markup, and it renders exactly the label you passed.
The generator's own verdict-word rule is stricter than the repository doc-lint's `stray_terms`: it
refuses an empty label, a label holding more than one sentence, and one whose visible text carries
U+2014, a stray term, a verdict word, a runtime-specific term, the British spelling of artifact
outside the evidence tree that lint exempts, or an unresolvable `profile.` reference (checked
against the target repository's own `profile/schema.json` when it has a schema).

It reads no tracker, makes no network call and needs no credential.
"""

import argparse
import errno
import json
import os
import re
import sys
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
# The Markdown punctuation a literal cell escapes, so the reader renders the text unchanged.
LITERAL_ESCAPES = set("\\`*_[<>&|~$]")
# A sentence ends at `.`, `!` or `?` before whitespace or the end; dots inside an identifier do not.
SENTENCE_END_RE = re.compile(r"[.!?](?=\s|$)")
# Common abbreviations whose dot is not a sentence boundary.
ABBREVIATION_RE = re.compile(r"(?i)\b(?:e\.g|i\.e|etc|vs|mr|mrs|ms|dr)\.(?=\s|$)")
# Link errors that mean the filesystem cannot publish a hard link, where an exclusive copy is the fallback.
LINK_UNSUPPORTED = {errno.EPERM, errno.EXDEV, errno.EMLINK}
for _name in ("EOPNOTSUPP", "ENOTSUP"):
    if hasattr(errno, _name):
        LINK_UNSUPPORTED.add(getattr(errno, _name))


def one_line(text: str) -> str:
    """A diagnostic fragment that can never break the single stderr line it sits in."""
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    for separator in ("\u2028", "\u2029", "\u0085"):
        text = text.replace(separator, f"\\u{ord(separator):04x}")
    return text


def print_path(path: Path) -> None:
    """Print the created path, escaping any character the standard output cannot encode."""
    line = str(path.absolute())
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    sys.stdout.write(line.encode(encoding, "backslashreplace").decode(encoding) + "\n")


def metadata_lines(path: str | None) -> list[str]:
    """The metadata lines, with the path-dependent ones only where the path calls for them."""
    lines = ["Date:", "Fixtures:"]
    if path is not None:
        lines.append(f"Path: {path}")
        lines.extend(["Environment:", "Build:"] if path == "deployed" else ["Target:"])
    return lines


def clean_label(label: str) -> str:
    """One table cell's literal text: breaks folded, whitespace collapsed, Markdown punctuation escaped."""
    folded = " ".join(label.split())
    return "".join("\\" + char if char in LITERAL_ESCAPES else char for char in folded)


def visible_text(label: str) -> str:
    """The literal text a cell renders: its backslash escapes decoded, nothing else interpreted."""
    return ESCAPE_RE.sub(r"\1", label)


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


def ref_candidates(text: str) -> list[str]:
    """The `profile.` references the doc-lint reads in a literal cell, a sentence-final dot removed."""
    return [match.group(1).removesuffix(".") for match in PROFILE_REF_RE.finditer(text)]


def checkout_root(start: Path) -> Path | None:
    """The nearest ancestor of `start` with a `.git` entry, which is the checkout that owns it."""
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def repository_root() -> Path:
    """The working directory's checkout root, else the nearest ancestor with a profile schema."""
    here = Path.cwd()
    root = checkout_root(here)
    if root is not None:
        return root
    for candidate in (here, *here.parents):
        if (candidate / "profile" / "schema.json").is_file():
            return candidate
    return here


def resolve_evidence_dir(root: Path, value: str) -> Path:
    """The evidence directory as an absolute path: a relative value resolves against the checkout root."""
    evidence = Path(value)
    if not evidence.is_absolute():
        evidence = root / evidence
    return Path(os.path.normpath(evidence))


def local_schema(root: Path) -> tuple[dict | None, str | None]:
    """The target repository's profile schema, or None when it has none, with any read problem."""
    candidate = root / "profile" / "schema.json"
    if not candidate.is_file():
        return None, None
    try:
        schema = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"error: cannot read {one_line(str(candidate))}: {exc}"
    if not isinstance(schema, dict):
        return None, f"error: {one_line(str(candidate))} is not a JSON object"
    return schema, None


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
        elif "properties" not in node:
            all_of = node.get("allOf")
            if (
                isinstance(all_of, list)
                and len(all_of) == 1
                and isinstance(all_of[0], dict)
                and list(all_of[0]) == ["$ref"]
            ):
                node = all_of[0]
            else:
                return node
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


def spelling_applies(root: Path, evidence: Path) -> bool:
    """The spelling lint exempts frozen QA evidence, so it applies outside that tree only."""
    try:
        relative = evidence.relative_to(root)
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
    for text in (key, visible_text(key)):
        problem = lint_problem(text, spelling=spelling)
        if problem is not None:
            return f"error: story key {key!r} {problem}"
    return None


def label_problem(label: str, *, schema: dict | None, spelling: bool) -> str | None:
    """Why a cleaned label cannot be written into the skeleton, or None when it can."""
    if not label:
        return "is empty"
    if len(SENTENCE_END_RE.findall(ABBREVIATION_RE.sub("", label))) > 1:
        return "holds more than one sentence"
    for text in (label, visible_text(label)):
        problem = lint_problem(text, spelling=spelling)
        if problem is not None:
            return problem
    return refs_problem(schema, visible_text(label))


def skeleton(key: str, items: list[str], path: str | None) -> str:
    lines = [f"# {key} QA evidence", "", "## QA round 1", "", *metadata_lines(path), ""]
    lines.extend([TABLE_HEADER, TABLE_SEPARATOR])
    lines.extend(f"| {item} |  |  |" for item in items)
    return "\n".join(lines) + "\n"


def open_directory(path: Path) -> tuple[int | None, str | None]:
    """Open `path` one component at a time, creating missing directories, never following a symlink."""
    if not path.is_absolute():
        return None, f"{one_line(str(path))} is not absolute"
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            except FileNotFoundError:
                try:
                    os.mkdir(part, dir_fd=descriptor)
                except FileExistsError:
                    pass
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
    except OSError as exc:
        os.close(descriptor)
        if exc.errno == errno.ELOOP:
            return None, f"{one_line(str(path))} has a symlink in its path"
        return None, f"cannot create {one_line(str(path))}: {exc.strerror or exc}"
    return descriptor, None


def publish(target: Path, text: str) -> bool:
    """Publish `text` at `target` without overwriting anything, or report why not."""
    try:
        data = text.encode("utf-8")
    except UnicodeError:
        print(f"error: the skeleton for {one_line(str(target))} cannot be encoded as UTF-8", file=sys.stderr)
        return False
    descriptor, problem = open_directory(target.parent)
    if descriptor is None:
        print(f"error: {problem}", file=sys.stderr)
        return False
    temp = f".qa-evidence-{os.getpid()}-{os.urandom(6).hex()}.tmp"
    created = False
    try:
        try:
            os.stat(target.name, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            print(f"error: {one_line(str(target.absolute()))} already exists; refusing to overwrite it", file=sys.stderr)
            return False
        try:
            handle = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=descriptor)
            created = True
        except OSError as exc:
            print(f"error: cannot write {one_line(str(target.absolute()))}: {exc.strerror or exc}", file=sys.stderr)
            return False
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(handle, view):]
        except OSError as exc:
            print(f"error: cannot write {one_line(str(target.absolute()))}: {exc.strerror or exc}", file=sys.stderr)
            return False
        finally:
            os.close(handle)
        try:
            os.link(temp, target.name, src_dir_fd=descriptor, dst_dir_fd=descriptor, follow_symlinks=False)
        except FileExistsError:
            print(f"error: {one_line(str(target.absolute()))} already exists; refusing to overwrite it", file=sys.stderr)
            return False
        except OSError as exc:
            if exc.errno not in LINK_UNSUPPORTED:
                print(f"error: cannot write {one_line(str(target.absolute()))}: {exc.strerror or exc}", file=sys.stderr)
                return False
            # The filesystem cannot publish a hard link: create the target exclusively and copy, so an
            # existing README is still never overwritten and an orderly failure removes our own file.
            try:
                direct = os.open(
                    target.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=descriptor
                )
            except FileExistsError:
                print(
                    f"error: {one_line(str(target.absolute()))} already exists; refusing to overwrite it",
                    file=sys.stderr,
                )
                return False
            except OSError as fallback_error:
                print(
                    f"error: cannot write {one_line(str(target.absolute()))}: {fallback_error.strerror or fallback_error}",
                    file=sys.stderr,
                )
                return False
            failure: OSError | None = None
            try:
                view = memoryview(data)
                while view:
                    view = view[os.write(direct, view):]
            except OSError as write_error:
                failure = write_error
            finally:
                os.close(direct)
            if failure is not None:
                try:
                    os.unlink(target.name, dir_fd=descriptor)
                except OSError:
                    pass
                print(
                    f"error: cannot write {one_line(str(target.absolute()))}: {failure.strerror or failure}",
                    file=sys.stderr,
                )
                return False
        return True
    finally:
        if created:
            try:
                os.unlink(temp, dir_fd=descriptor)
            except OSError:
                pass
        os.close(descriptor)


def normalize_argv(argv: list[str]) -> list[str]:
    """Turn `--key`, `--item` and `--evidence-dir` values into the `=` form, so a value starting with `-` is data."""
    normalized = []
    index = 0
    while index < len(argv):
        if argv[index] in ("--key", "--item", "--evidence-dir") and index + 1 < len(argv):
            normalized.append(f"{argv[index]}={argv[index + 1]}")
            index += 2
            continue
        normalized.append(argv[index])
        index += 1
    return normalized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the QA evidence README skeleton for a story.",
        allow_abbrev=False,
    )
    parser.add_argument("--key", required=True, help="Story key, for example SKL-386.")
    parser.add_argument("--item", action="append", default=[], dest="items", help="One verdict table row.")
    parser.add_argument("--path", choices=PATHS, help="The run's path, when it is known.")
    parser.add_argument("--evidence-dir", default=DEFAULT_EVIDENCE_DIR, help="Evidence directory.")
    args = parser.parse_args(normalize_argv(sys.argv[1:] if argv is None else argv))

    root = repository_root()
    if not args.evidence_dir:
        print("error: --evidence-dir is empty", file=sys.stderr)
        return 1
    problem = key_syntax_problem(args.key)
    if problem is not None:
        print(problem, file=sys.stderr)
        return 1

    evidence = resolve_evidence_dir(root, args.evidence_dir)
    destination_root = checkout_root(evidence) or root
    target = evidence / args.key / "README.md"
    if target.is_symlink() or target.exists():
        print(f"error: {one_line(str(target.absolute()))} already exists; refusing to overwrite it", file=sys.stderr)
        return 1

    spelling = spelling_applies(destination_root, evidence)
    problem = key_content_problem(args.key, spelling=spelling)
    if problem is not None:
        print(problem, file=sys.stderr)
        return 1

    schema: dict | None = None
    if any("profile." in visible_text(clean_label(raw)) for raw in args.items):
        schema, schema_problem = local_schema(destination_root)
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
    print_path(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
