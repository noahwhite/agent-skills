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
README is refused before any label is validated, with one line naming it, and the new README is
then created exclusively through opened directory descriptors that refuse every symlink component,
without overwriting anything, so a concurrent writer, a dangling symlink, a symlinked directory and
a non-regular entry at the README path are refused too. A write that fails partway leaves a partial
README, which must be removed by hand before a retry. A key outside ^[A-Z][A-Z0-9]+-[0-9]+$, an
empty `--evidence-dir`, and a story key the doc-lint rejects all exit 1 naming what is wrong.

A label is written as one table cell of literal text: its line breaks fold to spaces, runs of
whitespace collapse, and the Markdown punctuation that could open a table cell, a heading or inline
markup is backslash-escaped, so a cell can never add a column, a row, a heading or inline markup.
The generator's own verdict-word rule is stricter than the repository doc-lint's `stray_terms`: it
refuses an empty label, a label holding a control character that survives whitespace folding, an
invisible format character or more than one sentence, and one whose visible text carries U+2014, a
stray term, a verdict word, a runtime-specific term, the British spelling of artifact outside the
evidence tree that lint exempts, or an unresolvable `profile.` reference (checked against the target
repository's own `profile/schema.json` when it has a schema).

It reads no tracker, makes no network call and needs no credential.
"""

import argparse
import errno
import json
import os
import re
import stat
import sys
import unicodedata
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
# A sentence ends at `.`, `!` or `?` before whitespace, the end or a closing quote, and at the
# full-width and Arabic forms, which need no following space.
SENTENCE_END_RE = re.compile(r"(?:[。｡？！؟]|[.!?][\"'\u2019\u201d)\]]*(?=\s|$))")
# A dot that never ends a sentence: an abbreviation or title that never ends one, a title before a
# name, an abbreviation that continues in lowercase, a standalone path argument, an initial in a
# sequence of initials or an acronym, or a numbered item or decimal that continues in lowercase.
# A dot that never ends a sentence: an abbreviation or title that never ends one, an abbreviation
# or acronym that continues in lowercase, an initial in a sequence of initials, a standalone path
# argument, or a numbered item or decimal that continues in lowercase. A dot before a capitalized
# word is a sentence end, because nothing distinguishes a proper name from a new sentence.
NEVER_BOUNDARY_RE = re.compile(
    r"\b(?i:etc|vs|fig|a\.m|p\.m)\.(?=\s+[a-z0-9])"
    r"|\b(?i:e\.g|i\.e|mr|mrs|prof)\."
    r"|(?<!\d )\b(?i:ms|dr|st|gen|col|sr|jr)\.(?=\s+[A-Z])"
    r"|\b[A-Z]\.(?=\s+[A-Z]\.)"
    r"|(?<=[A-Z]\.)[A-Z]\.(?=\s+[a-z0-9]|\s*$)"
    r"|(?<=[A-Z]\.\s)[A-Z]\.(?=\s+[A-Z][a-z])"
    r"|(?<=\s)\.(?=\s+[a-z0-9]|\s*$)"
    r"|\b\d+\.(?=\s+[a-z0-9])"
)
# O_PATH opens a directory for use as a `dir_fd` without requiring read permission on it.
PATH_FLAGS = getattr(os, "O_PATH", os.O_RDONLY)


def one_line(text: str) -> str:
    """A diagnostic fragment that can never break one line or reach a terminal as a control sequence."""
    pieces = []
    for char in text:
        if char == "\r":
            pieces.append("\\r")
        elif char == "\n":
            pieces.append("\\n")
        elif ord(char) < 0x20 or 0x7f <= ord(char) <= 0x9f or char in "\u2028\u2029" or unicodedata.category(char) == "Cf":
            pieces.append(f"\\u{ord(char):04x}")
        else:
            pieces.append(char)
    return "".join(pieces)


def print_path(path: Path) -> None:
    """Print the created path, escaping any character the standard output cannot show literally."""
    if sys.stdout is None:
        return
    line = one_line(str(path.absolute()))
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        sys.stdout.write(line.encode(encoding, "backslashreplace").decode(encoding) + "\n")
        sys.stdout.flush()
    except OSError:
        # The README is published; an output error must not turn success into a failure report.
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except OSError:
            pass


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
    """The nearest ancestor of `start` with a real `.git` entry, which is the checkout that owns it."""
    for candidate in (start, *start.parents):
        try:
            info = os.lstat(candidate / ".git")
        except OSError:
            continue
        if not stat.S_ISLNK(info.st_mode):
            return candidate
    return None


def repository_root() -> Path:
    """The checkout that contains the working directory, else the working directory itself."""
    here = Path.cwd()
    return checkout_root(here) or here


def resolve_evidence_dir(root: Path, value: str) -> Path:
    """The evidence directory as an absolute path, keeping every supplied component as written."""
    evidence = Path(value)
    if not evidence.is_absolute():
        evidence = root / evidence
    return evidence


def local_schema(root: Path) -> tuple[dict | None, str | None]:
    """The target repository's profile schema, or None when it has none, with any read problem."""
    candidate = root / "profile" / "schema.json"
    if not os.path.lexists(candidate):
        return None, None
    if not candidate.is_file():
        return None, f"error: {one_line(str(candidate))} is not a regular file"
    try:
        schema = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"error: cannot read {one_line(str(candidate))}: {exc}"
    if not isinstance(schema, dict):
        return None, f"error: {one_line(str(candidate))} is not a JSON object"
    return schema, None


def deref(node, defs: dict):
    """A node with its `$ref`, or its `allOf` of exactly one `$ref`, resolved; None when unresolvable."""
    seen: set[str] = set()
    while isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            if not isinstance(ref, str):
                return None
            name = ref.split("/")[-1]
            if name in seen or name not in defs:
                return None
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
    return node


def schema_node(schema: dict, path: str):
    """The node `path` names in `schema`, or None when it does not resolve as the lint requires."""
    defs = schema.get("$defs")
    if not isinstance(defs, dict):
        defs = {}
    node = schema
    for part in path.split("."):
        is_array = part.endswith("[]")
        key = part.removesuffix("[]")
        node = deref(node, defs)
        if not isinstance(node, dict):
            return None
        properties = node.get("properties")
        if isinstance(properties, dict) and key in properties:
            node = properties[key]
        elif isinstance(node.get("additionalProperties"), dict):
            node = node["additionalProperties"]
        else:
            return None
        if is_array:
            if not isinstance(node, dict) or node.get("type") != "array":
                return None
            items = node.get("items")
            if not isinstance(items, dict):
                return None
            node = items
        node = deref(node, defs)
    return node


def resolves_ref(schema: dict, ref: str) -> bool:
    """Whether `ref`, the text after `profile.`, resolves in `schema`, wildcards included."""
    if ref.endswith(".*"):
        node = schema_node(schema, ref.removesuffix(".*"))
        return isinstance(node, dict) and (
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


def destination_owner(root: Path, evidence: Path) -> Path | None:
    """The checkout that owns `evidence`, or the working root when the destination sits inside it."""
    owner = checkout_root(evidence)
    if owner is not None:
        return owner
    try:
        evidence.relative_to(root)
    except ValueError:
        return None
    return root


def spelling_applies(owner: Path | None, evidence: Path) -> bool:
    """The spelling lint exempts frozen QA evidence, so it applies inside a checkout outside that tree."""
    if owner is None:
        return False
    try:
        relative = evidence.relative_to(owner)
    except ValueError:
        return True
    path = Path(os.path.normpath(relative)).as_posix()
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


def mask_sentence_noise(text: str) -> str:
    """`text` with the dots that never end a sentence masked, so only real boundaries remain."""
    text = re.sub(r"^\d+\.(?=\s)", lambda match: match.group(0)[:-1], text)
    return NEVER_BOUNDARY_RE.sub(lambda match: match.group(0)[:-1], text)


def more_than_one_sentence(label: str) -> bool:
    """Whether the text a reader sees holds more than one sentence, with abbreviations accounted for."""
    prose = mask_sentence_noise(visible_text(label).rstrip())
    first = SENTENCE_END_RE.search(prose)
    return first is not None and first.end() < len(prose)


def label_problem(label: str, *, schema: dict | None, spelling: bool) -> str | None:
    """Why a cleaned label cannot be written into the skeleton, or None when it can."""
    if not label:
        return "is empty"
    if any(ord(char) < 0x20 or 0x7f <= ord(char) <= 0x9f for char in label):
        return "carries a control character"
    if any(unicodedata.category(char) == "Cf" for char in label):
        return "carries an invisible format character"
    if more_than_one_sentence(label):
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


def check_components(path: Path) -> str | None:
    """The refusal when a component of `path` that exists is a symlink or not a directory, else None."""
    if not path.is_absolute():
        return f"error: {one_line(str(path))} is not absolute"
    descriptor = os.open("/", PATH_FLAGS | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            try:
                child = os.open(part, PATH_FLAGS | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            except FileNotFoundError:
                os.close(descriptor)
                return None
            if not stat.S_ISDIR(os.fstat(child).st_mode):
                os.close(child)
                os.close(descriptor)
                return f"error: cannot open {one_line(str(path))}: a path component is a file or symlink"
            os.close(descriptor)
            descriptor = child
    except OSError as exc:
        os.close(descriptor)
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            return f"error: cannot open {one_line(str(path))}: a path component is a file or symlink"
        return f"error: cannot open {one_line(str(path))}: {exc.strerror or exc}"
    os.close(descriptor)
    return None


def open_directory(path: Path, *, create: bool) -> tuple[int | None, str | None]:
    """Open `path` one component at a time, never following a symlink, creating it when asked."""
    if not path.is_absolute():
        return None, f"error: {one_line(str(path))} is not absolute"
    descriptor = os.open("/", PATH_FLAGS | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            try:
                child = os.open(part, PATH_FLAGS | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    os.close(descriptor)
                    return None, None
                try:
                    os.mkdir(part, dir_fd=descriptor)
                except FileExistsError:
                    pass
                child = os.open(part, PATH_FLAGS | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            if not stat.S_ISDIR(os.fstat(child).st_mode):
                os.close(child)
                raise OSError(errno.ENOTDIR, os.strerror(errno.ENOTDIR))
            os.close(descriptor)
            descriptor = child
    except OSError as exc:
        os.close(descriptor)
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            return None, f"error: cannot open {one_line(str(path))}: a path component is a file or symlink"
        return None, f"error: cannot open {one_line(str(path))}: {exc.strerror or exc}"
    return descriptor, None


def existing_target_problem(descriptor: int, target: Path) -> str | None:
    """The refusal when `target` already exists under `descriptor`, or None when it does not."""
    path = one_line(str(target.absolute()))
    try:
        info = os.stat(target.name, dir_fd=descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        return f"error: cannot inspect {path}: {exc.strerror or exc}"
    if stat.S_ISLNK(info.st_mode):
        return f"error: {path} is a symlink; refusing to follow it"
    if not stat.S_ISREG(info.st_mode):
        return f"error: {path} is not a regular file; refusing to use it"
    return f"error: {path} already exists; refusing to overwrite it"


def target_problem(target: Path) -> str | None:
    """The refusal when `target` already exists on a safe path or sits on an unsafe one, else None."""
    problem = check_components(target.parent)
    if problem is not None:
        return problem
    descriptor, problem = open_directory(target.parent, create=False)
    if problem is not None:
        return problem
    if descriptor is None:
        return None
    try:
        return existing_target_problem(descriptor, target)
    finally:
        os.close(descriptor)


def publish(target: Path, text: str) -> bool:
    """Create `text` at `target` exclusively, or report why not."""
    try:
        data = text.encode("utf-8")
    except UnicodeError:
        print(f"error: the skeleton for {one_line(str(target))} cannot be encoded as UTF-8", file=sys.stderr)
        return False
    descriptor, problem = open_directory(Path(os.path.normpath(target.parent)), create=True)
    if descriptor is None:
        print(problem, file=sys.stderr)
        return False
    try:
        problem = existing_target_problem(descriptor, target)
        if problem is not None:
            print(problem, file=sys.stderr)
            return False
        try:
            handle = os.open(
                target.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=descriptor
            )
        except FileExistsError:
            print(
                existing_target_problem(descriptor, target)
                or f"error: {one_line(str(target.absolute()))} already exists; refusing to overwrite it",
                file=sys.stderr,
            )
            return False
        except OSError as exc:
            print(f"error: cannot write {one_line(str(target.absolute()))}: {exc.strerror or exc}", file=sys.stderr)
            return False
        failure: OSError | None = None
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(handle, view):]
        except OSError as write_error:
            failure = write_error
        finally:
            try:
                os.close(handle)
            except OSError as close_error:
                if failure is None:
                    failure = close_error
        if failure is not None:
            print(
                f"error: cannot write {one_line(str(target.absolute()))}: {failure.strerror or failure}; "
                "a partial README may remain and must be removed by hand",
                file=sys.stderr,
            )
            return False
        return True
    finally:
        os.close(descriptor)


OPTIONS = ("--key", "--item", "--path", "--evidence-dir")


def normalize_argv(argv: list[str]) -> list[str]:
    """Turn a `--key`, `--item` or `--evidence-dir` value into the `=` form, so a value starting with `-` is data."""
    normalized = []
    index = 0
    while index < len(argv):
        following = argv[index + 1] if index + 1 < len(argv) else None
        option_like = following is not None and following.startswith("--") and following.split("=")[0] in OPTIONS
        if argv[index] in ("--key", "--item", "--evidence-dir") and following is not None and not option_like:
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

    try:
        root = repository_root()
    except OSError as exc:
        print(f"error: cannot read the working directory: {exc.strerror or exc}", file=sys.stderr)
        return 1
    if not args.evidence_dir.strip():
        print("error: --evidence-dir is empty", file=sys.stderr)
        return 1
    problem = key_syntax_problem(args.key)
    if problem is not None:
        print(problem, file=sys.stderr)
        return 1

    evidence = resolve_evidence_dir(root, args.evidence_dir)
    supplied = evidence / args.key / "README.md"
    problem = check_components(supplied.parent)
    if problem is not None:
        print(problem, file=sys.stderr)
        return 1
    evidence = Path(os.path.normpath(evidence))
    target = evidence / args.key / "README.md"
    try:
        owner = destination_owner(root, target)
    except OSError as exc:
        print(f"error: cannot inspect {one_line(str(target.parent))}: {exc.strerror or exc}", file=sys.stderr)
        return 1
    problem = target_problem(target)
    if problem is not None:
        print(problem, file=sys.stderr)
        return 1

    spelling = spelling_applies(owner, evidence)
    problem = key_content_problem(args.key, spelling=spelling)
    if problem is not None:
        print(problem, file=sys.stderr)
        return 1

    schema: dict | None = None
    if any(ref_candidates(visible_text(clean_label(raw))) for raw in args.items):
        schema, schema_problem = local_schema(owner) if owner is not None else (None, None)
        if schema_problem is not None:
            print(schema_problem, file=sys.stderr)
            return 1
    labels = []
    for position, raw in enumerate(args.items, start=1):
        label = clean_label(raw)
        try:
            label.encode("utf-8")
        except UnicodeError:
            print(f"error: item label {position} {one_line(repr(raw))} cannot be encoded as UTF-8", file=sys.stderr)
            return 1
        problem = label_problem(label, schema=schema, spelling=spelling)
        if problem is not None:
            print(f"error: item label {position} {one_line(repr(raw))} cannot be written: it {problem}", file=sys.stderr)
            return 1
        labels.append(label)

    if not publish(target, skeleton(args.key, labels, args.path)):
        return 1
    print_path(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
