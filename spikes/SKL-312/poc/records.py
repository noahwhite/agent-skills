"""What the replay reads from the repository: the case, its suite run records, and the rules
for a record the replay can use. compare.py, provider.py and grade.py share it.

Nothing here writes a file. A record, a run id or a checkout the replay cannot use raises
Unusable with the reason, so each caller can name the blocker instead of failing on a
missing key or a missing file.
"""

import functools
import json
import pathlib
import re
import subprocess

POC = pathlib.Path(__file__).resolve().parent


class Unusable(Exception):
    """A run id, a record or the checkout cannot be replayed; the text says why."""


def git(*args: str) -> subprocess.CompletedProcess:
    """One read-only git command in this checkout; it takes no lock and refreshes no index."""
    return subprocess.run(["git", "--no-optional-locks", "-C", str(POC), *args], capture_output=True, text=True)


def checkout_root() -> pathlib.Path:
    """The repository this file is in, as git names it, so no path depth is assumed."""
    top = git("rev-parse", "--show-toplevel")
    if top.returncode != 0:
        raise SystemExit(f"records.py: the replay needs the git checkout it is in: {top.stderr.strip()}")
    return pathlib.Path(top.stdout.strip())


ROOT = checkout_root()
EVALS = ROOT / "skills" / "story-to-done" / "evals"
CASE = EVALS / "qa-unfinished-own-steps"
RESULTS = CASE / "results"
GRADER = CASE / "grader.py"
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
# The suite's grade file names (suite.py GRADE_FILE): grader-output.txt is the scenario's own
# grade and grader-<g>-output.txt a further grade named <scenario>-<g>.
GRADE_FILE = re.compile(r"grader(?:-(?P<grade>[A-Za-z0-9._-]+))?-output\.txt")
# Every placeholder suite.py's Normaliser writes over text before a record is committed: a
# passed value or leak-scan match ({redacted}), a UUID, and each path root it knows.
PLACEHOLDER = re.compile(r"\{(?:redacted|uuid|path|run_dir|tmp|checkout|harness|tmpdir|home)\}")
REDACTED = "{redacted}"
GRADED = ("pass", "fail")
OUTCOMES = (*GRADED, "void", "error")
FIELDS = {"scenario": str, "outcome": str, "harness_commit": str, "verdicts": dict, "grades": dict,
          "grader_inputs": dict, "calls_record": str}


def file_name(prompt: str) -> str:
    """The name under which the provider files what it writes about one prompt."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", prompt)


def run_ids() -> list[str]:
    """The run id of every suite run record of the case: the record's file stem."""
    return sorted(path.stem for path in RESULTS.glob("*.json"))


def load(run_id: str) -> dict:
    """One suite run record, checked for the fields the replay reads."""
    if not NAME.fullmatch(run_id):
        raise Unusable("the run id is not a record file stem")
    path = RESULTS / f"{run_id}.json"
    if not path.is_file():
        raise Unusable(f"no run record {run_id}.json")
    try:
        record = json.loads(path.read_text())
    except ValueError as error:
        raise Unusable(f"{path.name} is not JSON: {error}") from None
    if not isinstance(record, dict):
        raise Unusable(f"{path.name} is not a suite run record: it is not a JSON object")
    wrong = [field for field, kind in FIELDS.items() if not isinstance(record.get(field), kind)]
    if wrong:
        raise Unusable(f"{path.name} is not a suite run record: {', '.join(wrong)} missing or of the wrong type")
    if record["outcome"] not in OUTCOMES or not NAME.fullmatch(record["scenario"]):
        raise Unusable(f"{path.name} names an outcome or a scenario the suite does not write")
    if not all(isinstance(lines, list) for lines in record["grades"].values()) or \
            not all(isinstance(text, str) for text in record["grader_inputs"].values()):
        raise Unusable(f"{path.name} is not a suite run record: its grades or grader inputs are not text")
    return record


def calls_text(run_id: str, record: dict) -> str | None:
    """The tool-call record the suite kept beside the run record, or None when the run left none."""
    if record["calls_record"] == "absent":
        return None
    path = RESULTS / f"{run_id}-calls.jsonl"
    if not path.is_file():
        raise Unusable(f"the record names a call record and {path.name} is missing")
    return path.read_text()


def grades_to_take(record: dict) -> list[dict]:
    """The grades the recorded run took, the scenario's own first. Each expectation is the name
    the suite gives the grade file, and together they must be the verdicts the record names."""
    taken = []
    for name in sorted(record["grades"], key=lambda name: (name != "grader-output.txt", name)):
        named = GRADE_FILE.fullmatch(name)
        if not named:
            raise Unusable(f"the record keeps a grade file the suite does not name: {name}")
        taken.append({"expectation": record["scenario"] + (f"-{named['grade']}" if named["grade"] else ""), "file": name})
    if {grade["expectation"] for grade in taken} != set(record["verdicts"]):
        raise Unusable("the record's grade files do not name the verdicts it records")
    return taken


def placeholders(run_id: str, record: dict) -> list[str]:
    """Each kind of placeholder the suite wrote into what the grader reads."""
    text = "".join(record["grader_inputs"].values()) + (calls_text(run_id, record) or "")
    return sorted(set(PLACEHOLDER.findall(text)))


@functools.cache
def case_changed(commit: str, scenario: str) -> bool:
    """True when the grader or one scenario's fixtures differ between a commit and HEAD."""
    diff = git("diff", "--quiet", commit, "HEAD", "--", str(GRADER), str(CASE / "scenarios" / scenario))
    if diff.returncode not in (0, 1):
        raise Unusable(f"git diff against {commit} failed: {diff.stderr.strip()}")
    return diff.returncode == 1


@functools.cache
def added_in(run_id: str) -> str:
    """The commit on HEAD's history that last added a run record."""
    if git("rev-parse", "--is-shallow-repository").stdout.strip() != "false":
        raise Unusable("the clone is shallow, and the replay reads history to see that the case is the one the records were graded with")
    log = git("log", "-1", "--diff-filter=A", "--format=%H", "--", str(RESULTS / f"{run_id}.json"))
    if log.returncode != 0 or not log.stdout.strip():
        raise Unusable(f"no commit on this branch adds {run_id}.json")
    return log.stdout.strip()


def not_replayable(run_id: str, record: dict) -> str | None:
    """Why a graded record cannot be graded again as the suite graded it, or None when it can.

    A record names the harness commit it was graded at and carries no hash of the grader or
    the fixtures. That commit is on a branch that was squash-merged, so it is on no branch
    here and a clone may not hold it. The grader and the scenario's fixtures are therefore
    compared with the commit that added the record, which every full clone holds, and with
    the harness commit too where the clone has it.
    """
    if REDACTED in placeholders(run_id, record):
        return "the suite redacted text the grader reads, so the run cannot be rebuilt as it was graded"
    if case_changed(added_in(run_id), record["scenario"]):
        return "the case's grader or this scenario's fixtures changed after the commit that added the record"
    harness = record["harness_commit"]
    if git("cat-file", "-e", f"{harness}^{{commit}}").returncode == 0 and case_changed(harness, record["scenario"]):
        return "the case's grader or this scenario's fixtures are not the ones at the record's harness commit"
    return None


def uncommitted() -> list[str]:
    """Paths under the evals directory that differ from HEAD: a replay of them is of no commit."""
    status = git("status", "--porcelain", "--untracked-files=all", "--", str(EVALS))
    if status.returncode != 0:
        raise Unusable(f"git status failed: {status.stderr.strip()}")
    return [line[3:] for line in status.stdout.splitlines() if line]


def same_lines(recorded: list[str], replayed: list[str] | None) -> bool:
    """True when a replayed grade file is the recorded one, a placeholder standing for any text."""
    if replayed is None or len(recorded) != len(replayed):
        return False
    return all(re.fullmatch(".+".join(re.escape(part) for part in PLACEHOLDER.split(old)), new, re.S)
               for old, new in zip(recorded, replayed))
