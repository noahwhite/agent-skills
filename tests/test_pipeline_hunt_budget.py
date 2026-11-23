"""SKL-406: the hunt carries an explicit exploration budget, and the arbitrate dossier says so truthfully.

The hunt phase's dossier is the agent's whole prompt, so these tests read the dossier the script itself
writes: accept a preflight (and a sweep when one runs) on a throwaway repository, write the hunt dossier,
and pin every budget sentence and the command count in it. The mode - the script's `--no-sweep` flag and
nothing else - decides the candidate source, so exactly one source sentence and one candidate-list
header appear per mode, never both. The arbitrate dossier claims the budget only when the recorded
hunt's binding carries this script's hunt-prompt identity, and says the hunt predates the budget
otherwise. A later edit can neither drop nor soften a sentence, cannot change the count without
changing this test, and cannot give the sweep dossier a hunt budget.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "adversarial-review-pipeline" / "scripts" / "run-adversarial-pipeline.sh"
BASE_REF = "base"

# The exploration budget the hunt dossier must carry, sentence by sentence, and the count both the
# hunt and the arbitrate dossier must name. These are the pins: an edit to the script that changes
# any of them without this test changing fails it.
BUDGET_HEADER = ("EXPLORATION BUDGET - this hunt is bounded by its exploration, not by its "
                 "input payload:")
COMMAND_COUNT = "40"
COUNT_SENTENCE = f"- At most {COMMAND_COUNT} shell commands in total."
# Exactly one candidate source is emitted per mode, decided by --no-sweep and nothing else.
SWEEP_SOURCE_SENTENCE = ("- Verify only the candidates listed in the sweep report, plus defects "
                         "those candidates directly point at.")
NO_SWEEP_SOURCE_SENTENCE = ("- With no sweep report in this hunt-only run, derive the candidate "
                            "list from the diff yourself, then verify only those candidates, plus "
                            "defects they directly point at.")
# AC1's literal stop rule.
STOP_SENTENCE = ("- stop and report once the candidate list is exhausted rather than continuing to "
                 "explore.")
# An accepted zero-candidate sweep must still let an obedient hunt produce an accepted report.
EMPTY_LIST_SENTENCE = ("- If the candidate list is empty, run one minimal check that the checkout is "
                       "at the reviewed head and that the list is empty, report no findings with "
                       "'REVIEW-RAN: yes', and do not start further exploration.")
# The acceptance-rule probes the same dossier carries share the budget and the stop point, and a rule
# the budget did not reach is reported honestly instead of attested.
RULE_BUDGET_SENTENCE = ("- Acceptance-rule probes share this command budget and this stop point; a "
                        "rule you could not execute inside them is listed as 'NOT-REACHED - <n>: "
                        "<reason>' with the rules, never PASSED or FAILED, before your final "
                        "unchecked-candidate list.")
SKIPPED_RULE_PROSE = ("and list a rule the budget did not reach as 'NOT-REACHED - <n>: <reason>' "
                      "beside them:")
# The third honest outcome: an unchecked candidate is never reported VERIFIED or REFUTED, and the
# report ends with the list of what it did not check.
NOT_REACHED_SENTENCE = ("- Report VERIFIED or REFUTED only for a candidate you actually checked; a "
                        "candidate you did not check is NOT-REACHED (budget spent).")
UNCHECKED_SENTENCE = "- End your report with the list of candidates you did not check, or 'none'."
GREP_SENTENCE = ("- Never run a repository-wide grep, find or rg; any search must be path-scoped to "
                 "a path named in the diffstat or by a candidate.")
READ_SENTENCE = "- Read only paths named in the diffstat unless a candidate names another path."
SHARED_SENTENCES = (GREP_SENTENCE, COUNT_SENTENCE, READ_SENTENCE, STOP_SENTENCE,
                    EMPTY_LIST_SENTENCE, RULE_BUDGET_SENTENCE, NOT_REACHED_SENTENCE,
                    UNCHECKED_SENTENCE)
RULE_LINE = "RULE <n> | PASSED or FAILED | the rule in one line | the command you ran | what you observed"
BUDGET_SENTENCES = (SWEEP_SOURCE_SENTENCE, *SHARED_SENTENCES)
NO_SWEEP_BUDGET_SENTENCES = (NO_SWEEP_SOURCE_SENTENCE, *SHARED_SENTENCES)

# The mode-aware candidate-list header: (Phase 1 sweep) never heads the hunt-only placeholder.
CANDIDATES_SWEEP_HEADER = "===== CANDIDATES (Phase 1 sweep) ====="
CANDIDATES_HUNT_ONLY_HEADER = "===== CANDIDATES (sweep not configured - hunt only) ====="
# The static body line a hunt-only dossier carries under that header, inside the prompt identity.
HUNT_ONLY_BODY = "(derive the candidate list from the diff, per the exploration budget above)"

# The two job sentences above the budget carry the same restriction, one variant per mode; without
# them a later edit could restore an open-ended hunt beside a pinned budget block.
JOB_1_SWEEP = "Job 1 - VERIFY. For each candidate in the sweep report below:"
JOB_1_NO_SWEEP = ("Job 1 - VERIFY. For each candidate you derive from the diff (see the "
                  "exploration budget below):")
JOB_2_SWEEP = ("Job 2 - HUNT only for defects those candidates directly point at, inside the "
               "exploration budget below: a")
JOB_2_NO_SWEEP = ("Job 2 - HUNT only for defects the candidates you derived directly point at, "
                  "inside the exploration budget below: a")

# The arbitrate note, one wording per direction: the recorded hunt carried the budget, or it
# predates it and its silence is therefore not bounded exploration.
ARBITRATE_NOTE = (
    "Note: the recorded hunt ran under an exploration budget - at most {count} shell commands "
    "per hunt invocation, verifying only {source} plus defects those candidates directly point "
    "at, searching only "
    "path-scoped and reading only the diffstat's paths unless a candidate names another. A "
    "candidate it reports as NOT-REACHED (budget spent), or a rule it reports as NOT-REACHED, is "
    "omitted work, never coverage: credit "
    "only the checks the hunt report evidences, and read its silence as the bounded exploration "
    "this budget allows, not as full coverage.")
ARBITRATE_NOTE_SWEEP = ARBITRATE_NOTE.format(
    count=COMMAND_COUNT, source="the candidates in the sweep report")
ARBITRATE_NOTE_NO_SWEEP = ARBITRATE_NOTE.format(
    count=COMMAND_COUNT, source="the candidates it derived from the diff")
PREDATES_NOTE = (
    "Note: the recorded hunt predates this exploration budget, so its prompt carried no command "
    "cap and no candidate-source rule. Its silence is not bounded exploration: treat an area it "
    "did not report on as unexplored, never as covered, and weigh that when reading its silence "
    "as coverage.")

SWEEP_REPORT = """REVIEW-RAN: yes
Candidate list for the hunt.

- skills/adversarial-review-pipeline/scripts/run-adversarial-pipeline.sh:1990 | Low | wording |
  A prompt sentence could drift from its test.
"""

HUNT_REPORT = """REVIEW-RAN: yes
No verified defects.
"""

GIT_ISOLATION = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def isolated_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("ADVERSARIAL_") and not k.startswith("GIT_")}
    return {**env, **GIT_ISOLATION, "GIT_AUTHOR_NAME": "Fixture Author",
            "GIT_AUTHOR_EMAIL": "fixture@example.com",
            "GIT_COMMITTER_NAME": "Fixture Author",
            "GIT_COMMITTER_EMAIL": "fixture@example.com",
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+0000",
            "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+0000"}


def git(repo: Path, env: dict[str, str], *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


def make_repo(tmp_path: Path, env: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, env, "init", "-q", "--initial-branch=main")
    git(repo, env, "config", "core.autocrlf", "false")
    git(repo, env, "config", "commit.gpgsign", "false")
    git(repo, env, "config", "tag.gpgsign", "false")
    for content, message in (("base\n", "base"), ("head\n", "head")):
        (repo / "file.txt").write_text(content)
        git(repo, env, "add", "-A")
        git(repo, env, "commit", "-q", "-m", message)
        if message == "base":
            git(repo, env, "tag", BASE_REF)
    return repo


def run_script(env: dict[str, str], *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=str(ROOT), env=env,
                          capture_output=True, text=True, timeout=300)


def run_pipeline(script: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(script), *args], cwd=str(ROOT), env=env,
                          capture_output=True, text=True, timeout=300)


def checked(result: subprocess.CompletedProcess, what: str) -> subprocess.CompletedProcess:
    assert result.returncode == 0, f"{what} exited {result.returncode}:\n{result.stdout}\n{result.stderr}"
    return result


def artifact_paths(repo: Path, env: dict[str, str]) -> dict[str, Path]:
    listed = checked(run_script(env, "paths", "--repo", str(repo), "--base", BASE_REF), "paths")
    return {name: Path(path) for name, _, path in
            (line.partition(" ") for line in listed.stdout.splitlines()) if path}


def start_run(tmp_path: Path) -> tuple[dict[str, str], Path, Path, list[str]]:
    """A throwaway repository with a green preflight; returns env, repo, scratch and the common args."""
    env = {**isolated_env(), "TMPDIR": str(tmp_path)}
    repo = make_repo(tmp_path, env)
    scratch = tmp_path / "session-scratch"
    scratch.mkdir()
    spec = tmp_path / "spec.md"
    spec.write_text("Story SKL-406: bound the hunt's exploration, not its payload.\n")
    common = ["--repo", str(repo), "--base", BASE_REF, "--spec", str(spec), "--scratch", str(scratch)]
    checked(run_script(env, "preflight", "--full-suite", "on", "--repo", str(repo), "--base", BASE_REF,
                       "--test-cmd", "true", "--scratch", str(scratch)), "preflight")
    return env, repo, scratch, common


def build_dossiers(tmp_path: Path, no_sweep: bool,
                   missing_binding: bool = False) -> dict[str, str]:
    """Writes the sweep (only when one runs), hunt and arbitrate dossiers on a throwaway repository.

    With `missing_binding`, the accepted hunt's binding file is removed before the arbitrate dossier
    is written: the note must read the stamp acceptance compared, not that mutable file.
    """
    env, repo, _, common = start_run(tmp_path)
    paths = artifact_paths(repo, env)
    out: dict[str, str] = {}
    phases = (("sweep", SWEEP_REPORT), ("hunt", HUNT_REPORT)) if not no_sweep else (("hunt", HUNT_REPORT),)
    for phase, report in phases:
        extra = ["--no-sweep"] if no_sweep else []
        written = checked(run_script(env, "dossier", phase, *common, *extra), f"dossier {phase}")
        out[phase] = Path(written.stdout.strip().splitlines()[-1]).read_text()
        paths[phase].write_text(report)
        checked(run_script(env, "record", phase, "--repo", str(repo), "--base", BASE_REF,
                           "--spec", str(common[common.index("--spec") + 1]), *extra), f"record {phase}")
    if missing_binding:
        (paths["run"] / "hunt.binding").unlink()
    extra = ["--no-sweep"] if no_sweep else []
    written = checked(run_script(env, "dossier", "arbitrate", *common, *extra), "dossier arbitrate")
    out["arbitrate"] = Path(written.stdout.strip().splitlines()[-1]).read_text()
    out["_run"] = str(paths["run"])
    return out


@pytest.fixture(scope="module")
def dossiers(tmp_path_factory):
    return build_dossiers(tmp_path_factory.mktemp("hunt-budget"), no_sweep=False)


@pytest.fixture(scope="module")
def no_sweep_dossiers(tmp_path_factory):
    return build_dossiers(tmp_path_factory.mktemp("hunt-budget-nosweep"), no_sweep=True)


@pytest.fixture(scope="module")
def missing_binding_dossiers(tmp_path_factory):
    return build_dossiers(tmp_path_factory.mktemp("hunt-budget-missing-binding"),
                          no_sweep=False, missing_binding=True)


def hunt_prompt(text: str) -> str:
    """The hunt dossier's own prompt, before the embedded candidate list and context it quotes."""
    head, marker, _ = text.partition("===== CANDIDATES")
    assert marker, "the hunt dossier has no CANDIDATES section"
    return head


def arbitrate_prompt(text: str) -> str:
    """The arbitrate dossier's own prompt, before the embedded phase reports it quotes."""
    head, marker, _ = text.partition("===== PHASE 1")
    assert marker, "the arbitrate dossier has no PHASE 1 section"
    return head


def budget_block(prompt: str) -> list[str]:
    """The budget block, whole: the header, every line after it up to the next prompt section, and
    no trailing blank line, so inserted prose or a contradictory extra bullet is compared too."""
    lines = prompt.splitlines()
    start = lines.index(BUDGET_HEADER)
    block: list[str] = []
    for line in lines[start:]:
        if line.startswith("Execute, do not just reason."):
            break
        block.append(line)
    while block and block[-1] == "":
        block.pop()
    return block


def test_the_pin_sets_are_not_empty():
    # An empty parametrize is skipped, not failed, so a pin set emptied in an edit must fail here.
    assert SHARED_SENTENCES
    assert BUDGET_SENTENCES
    assert NO_SWEEP_BUDGET_SENTENCES
    assert len(set(BUDGET_SENTENCES)) == len(BUDGET_SENTENCES)


def test_the_hunt_dossier_carries_the_budget_header(dossiers):
    assert BUDGET_HEADER in hunt_prompt(dossiers["hunt"])


def test_the_budget_header_appears_exactly_once(dossiers, no_sweep_dossiers):
    assert hunt_prompt(dossiers["hunt"]).count(BUDGET_HEADER) == 1
    assert hunt_prompt(no_sweep_dossiers["hunt"]).count(BUDGET_HEADER) == 1


def test_the_sweep_mode_budget_block_is_exactly_the_pinned_sentences(dossiers):
    assert budget_block(hunt_prompt(dossiers["hunt"])) == [BUDGET_HEADER, *BUDGET_SENTENCES]


def test_the_no_sweep_mode_budget_block_is_exactly_the_pinned_sentences(no_sweep_dossiers):
    assert budget_block(hunt_prompt(no_sweep_dossiers["hunt"])) == [BUDGET_HEADER,
                                                                  *NO_SWEEP_BUDGET_SENTENCES]


@pytest.mark.parametrize("fixture_name", ["dossiers", "no_sweep_dossiers"])
def test_the_budget_names_its_command_count(request, fixture_name):
    prompt = hunt_prompt(request.getfixturevalue(fixture_name)["hunt"])
    assert COUNT_SENTENCE in prompt


def test_the_budget_names_the_third_verdict_and_the_unchecked_list(dossiers, no_sweep_dossiers):
    for out in (dossiers, no_sweep_dossiers):
        prompt = hunt_prompt(out["hunt"])
        assert "NOT-REACHED (budget spent)" in prompt
        assert NOT_REACHED_SENTENCE in prompt
        assert UNCHECKED_SENTENCE in prompt


def test_the_sweep_mode_hunt_carries_only_the_sweep_candidate_source(dossiers):
    prompt = hunt_prompt(dossiers["hunt"])
    assert SWEEP_SOURCE_SENTENCE in prompt
    assert NO_SWEEP_SOURCE_SENTENCE not in prompt
    # The sweep-mode hunt must really embed the accepted sweep report under the CANDIDATES header.
    assert SWEEP_REPORT.strip() in dossiers["hunt"]
    assert CANDIDATES_SWEEP_HEADER in dossiers["hunt"]
    assert CANDIDATES_HUNT_ONLY_HEADER not in dossiers["hunt"]
    assert HUNT_ONLY_BODY not in dossiers["hunt"]


def test_the_no_sweep_mode_hunt_carries_only_the_diff_candidate_source(no_sweep_dossiers):
    prompt = hunt_prompt(no_sweep_dossiers["hunt"])
    assert NO_SWEEP_SOURCE_SENTENCE in prompt
    assert SWEEP_SOURCE_SENTENCE not in prompt
    assert CANDIDATES_HUNT_ONLY_HEADER in no_sweep_dossiers["hunt"]
    assert CANDIDATES_SWEEP_HEADER not in no_sweep_dossiers["hunt"]
    # The hunt-only header must never head a sweep placeholder, and its body line is pinned.
    assert "(Phase 1 sweep)" not in no_sweep_dossiers["hunt"]
    assert HUNT_ONLY_BODY in no_sweep_dossiers["hunt"]


def test_the_hunt_dossier_binds_both_jobs_to_the_budget(dossiers):
    prompt = hunt_prompt(dossiers["hunt"])
    assert JOB_1_SWEEP in prompt
    assert JOB_2_SWEEP in prompt
    assert JOB_1_NO_SWEEP not in prompt
    assert JOB_2_NO_SWEEP not in prompt
    assert "open-ended" not in prompt


def test_the_no_sweep_hunt_dossier_binds_both_jobs_to_the_budget(no_sweep_dossiers):
    prompt = hunt_prompt(no_sweep_dossiers["hunt"])
    assert JOB_1_NO_SWEEP in prompt
    assert JOB_2_NO_SWEEP in prompt
    assert JOB_1_SWEEP not in prompt
    assert JOB_2_SWEEP not in prompt
    assert "open-ended" not in prompt


def test_the_sweep_mode_budget_is_ordered_source_limits_stop(dossiers):
    prompt = hunt_prompt(dossiers["hunt"])
    ordered = (SWEEP_SOURCE_SENTENCE, GREP_SENTENCE, COUNT_SENTENCE, READ_SENTENCE,
               STOP_SENTENCE, EMPTY_LIST_SENTENCE, RULE_BUDGET_SENTENCE,
               NOT_REACHED_SENTENCE, UNCHECKED_SENTENCE)
    positions = [prompt.index(sentence) for sentence in ordered]
    assert positions == sorted(positions)


def test_the_no_sweep_mode_budget_is_ordered_source_limits_stop(no_sweep_dossiers):
    prompt = hunt_prompt(no_sweep_dossiers["hunt"])
    ordered = (NO_SWEEP_SOURCE_SENTENCE, GREP_SENTENCE, COUNT_SENTENCE, READ_SENTENCE,
               STOP_SENTENCE, EMPTY_LIST_SENTENCE, RULE_BUDGET_SENTENCE,
               NOT_REACHED_SENTENCE, UNCHECKED_SENTENCE)
    positions = [prompt.index(sentence) for sentence in ordered]
    assert positions == sorted(positions)


def test_the_hunt_rule_probes_share_the_budget_and_have_a_not_reached_disposition(dossiers, no_sweep_dossiers):
    for out in (dossiers, no_sweep_dossiers):
        prompt = hunt_prompt(out["hunt"])
        assert RULE_LINE in prompt
        assert SKIPPED_RULE_PROSE in prompt
        assert RULE_BUDGET_SENTENCE in prompt


def test_the_arbitrate_dossier_notes_the_budgeted_sweep_hunt(dossiers):
    prompt = arbitrate_prompt(dossiers["arbitrate"])
    assert ARBITRATE_NOTE_SWEEP in prompt
    assert PREDATES_NOTE not in prompt


def test_the_arbitrate_dossier_notes_the_budgeted_hunt_only_run(no_sweep_dossiers):
    prompt = arbitrate_prompt(no_sweep_dossiers["arbitrate"])
    assert ARBITRATE_NOTE_NO_SWEEP in prompt
    assert PREDATES_NOTE not in prompt


def test_a_missing_hunt_binding_cannot_flip_the_note_to_predates(missing_binding_dossiers):
    # The note reads the stamp acceptance compared, never the mutable binding file beside it.
    prompt = arbitrate_prompt(missing_binding_dossiers["arbitrate"])
    assert ARBITRATE_NOTE_SWEEP in prompt
    assert PREDATES_NOTE not in prompt


def test_a_genuine_legacy_hunt_is_refused_before_any_note(tmp_path):
    # A hunt whose stamp carries no prompt identity is not accepted; arbitration refuses it (13)
    # rather than emitting a note about a hunt it never verified.
    env, repo, _, common = start_run(tmp_path)
    paths = artifact_paths(repo, env)
    for phase, report in (("sweep", SWEEP_REPORT), ("hunt", HUNT_REPORT)):
        checked(run_script(env, "dossier", phase, *common), f"dossier {phase}")
        paths[phase].write_text(report)
        checked(run_script(env, "record", phase, "--repo", str(repo), "--base", BASE_REF,
                           "--spec", str(common[common.index("--spec") + 1])), f"record {phase}")
    # Remove only the prompt line from the stamp acceptance wrote: the artifact hash and every other
    # bound input still match, so the refusal is about the missing prompt identity alone.
    stamp = Path(f"{paths['hunt']}.stamp")
    kept = [line for line in stamp.read_text().splitlines() if not line.startswith("prompt=")]
    stamp.write_text("\n".join(kept) + "\n")
    refused = run_script(env, "dossier", "arbitrate", *common)
    assert refused.returncode == 13, refused.stdout + refused.stderr
    assert "needs an accepted hunt artifact" in refused.stderr


def test_the_script_keeps_the_predates_note_for_an_unevidenced_hunt():
    # The owner's strategy requires the fallback wording to exist; acceptance makes it unreachable,
    # so it is pinned against the script source rather than a fabricated run state.
    assert PREDATES_NOTE in SCRIPT.read_text()


def test_a_changed_hunt_prompt_unaccepts_the_recorded_hunt(tmp_path):
    # A real prompt edit between the dossier and the record is an inputs change (exit 13), so the
    # identity must track the prompt text: a constant id would accept this report silently.
    env, repo, _, common = start_run(tmp_path)
    paths = artifact_paths(repo, env)
    edited = tmp_path / "pipeline.sh"
    shutil.copy(SCRIPT, edited)
    written = checked(run_pipeline(edited, env, "dossier", "hunt", *common, "--no-sweep"),
                      "dossier hunt")
    assert Path(written.stdout.strip().splitlines()[-1]).exists()
    paths["hunt"].write_text(HUNT_REPORT)
    text = edited.read_text()
    assert f"HUNT_BUDGET_COMMANDS={COMMAND_COUNT}" in text
    edited.write_text(text.replace(
        f"HUNT_BUDGET_COMMANDS={COMMAND_COUNT}", f"HUNT_BUDGET_COMMANDS={int(COMMAND_COUNT) + 1}"))
    refused = run_pipeline(edited, env, "record", "hunt", "--repo", str(repo), "--base", BASE_REF,
                           "--spec", str(common[common.index("--spec") + 1]), "--no-sweep")
    assert refused.returncode == 13, refused.stdout + refused.stderr
    assert "inputs changed since its dossier was written" in refused.stderr
    assert "the hunt prompt" in refused.stderr


def record_hunt_after_edit(tmp_path: Path, no_sweep: bool, old: str, new: str) -> subprocess.CompletedProcess:
    """Dossiers a hunt with a pristine script copy, edits one prompt string, then records it."""
    env, repo, _, common = start_run(tmp_path)
    paths = artifact_paths(repo, env)
    extra = ["--no-sweep"] if no_sweep else []
    if not no_sweep:
        checked(run_script(env, "dossier", "sweep", *common, *extra), "dossier sweep")
        paths["sweep"].write_text(SWEEP_REPORT)
        checked(run_script(env, "record", "sweep", "--repo", str(repo), "--base", BASE_REF,
                           "--spec", str(common[common.index("--spec") + 1]), *extra), "record sweep")
    edited = tmp_path / "pipeline.sh"
    shutil.copy(SCRIPT, edited)
    checked(run_pipeline(edited, env, "dossier", "hunt", *common, *extra), "dossier hunt")
    paths["hunt"].write_text(HUNT_REPORT)
    text = edited.read_text()
    assert old in text
    edited.write_text(text.replace(old, new))
    return run_pipeline(edited, env, "record", "hunt", "--repo", str(repo), "--base", BASE_REF,
                        "--spec", str(common[common.index("--spec") + 1]), *extra)


def test_an_invisible_sweep_fallback_edit_keeps_the_hunt_accepted(tmp_path):
    # In sweep mode the agent reads the accepted sweep report, so the fallback text is not part of
    # the emitted prompt and editing it must not invalidate the paid hunt.
    recorded = record_hunt_after_edit(tmp_path, no_sweep=False,
                                      old="(sweep not configured - hunt only)",
                                      new="(sweep absent)")
    assert recorded.returncode == 0, recorded.stdout + recorded.stderr


def test_an_emitted_hunt_only_body_edit_unaccepts_the_hunt(tmp_path):
    # In hunt-only mode that body line is what the agent reads, so it is part of the identity.
    recorded = record_hunt_after_edit(tmp_path, no_sweep=True, old=HUNT_ONLY_BODY,
                                      new="(derive the candidate list from the diff)")
    assert recorded.returncode == 13, recorded.stdout + recorded.stderr
    assert "inputs changed since its dossier was written" in recorded.stderr


def test_an_empty_candidate_list_still_carries_the_budget_and_the_rule_disposition(tmp_path):
    # The arbiter's empty-list case: the budget, its stop point and the rule-probe disposition are
    # present even when the sweep hands the hunt nothing to verify.
    env, repo, _, common = start_run(tmp_path)
    paths = artifact_paths(repo, env)
    checked(run_script(env, "dossier", "sweep", *common), "dossier sweep")
    paths["sweep"].write_text("REVIEW-RAN: yes\nNo candidates found.\n")
    checked(run_script(env, "record", "sweep", "--repo", str(repo), "--base", BASE_REF,
                       "--spec", str(common[common.index("--spec") + 1])), "record sweep")
    written = checked(run_script(env, "dossier", "hunt", *common), "dossier hunt")
    dossier = Path(written.stdout.strip().splitlines()[-1]).read_text()
    prompt = hunt_prompt(dossier)
    assert BUDGET_HEADER in prompt
    assert STOP_SENTENCE in prompt
    assert EMPTY_LIST_SENTENCE in prompt
    assert RULE_BUDGET_SENTENCE in prompt
    assert RULE_LINE in prompt
    assert "===== ACCEPTANCE RULES ARE BEHAVIOURAL PROBES =====" in dossier
    # And the zero-finding report an obedient hunt returns is accepted and reaches arbitration.
    paths["hunt"].write_text(HUNT_REPORT)
    checked(run_script(env, "record", "hunt", "--repo", str(repo), "--base", BASE_REF,
                       "--spec", str(common[common.index("--spec") + 1])), "record hunt")
    arbitrate = checked(run_script(env, "dossier", "arbitrate", *common), "dossier arbitrate")
    text = Path(arbitrate.stdout.strip().splitlines()[-1]).read_text()
    assert ARBITRATE_NOTE_SWEEP in arbitrate_prompt(text)


def test_the_sweep_dossier_carries_no_hunt_budget(dossiers):
    # The fixture's payload is a toy diff, so the whole generated dossier can be checked: no budget
    # text may appear anywhere, including after the embedded payload.
    absent = (BUDGET_HEADER, *BUDGET_SENTENCES, *NO_SWEEP_BUDGET_SENTENCES, JOB_1_SWEEP,
              JOB_1_NO_SWEEP, JOB_2_SWEEP, JOB_2_NO_SWEEP, "NOT-REACHED",
              CANDIDATES_SWEEP_HEADER, CANDIDATES_HUNT_ONLY_HEADER)
    for text in absent:
        assert text not in dossiers["sweep"]


def test_only_the_hunt_binding_carries_the_prompt_identity(dossiers):
    # AC4 permits exactly one binding addition: the hunt's. No other phase's binding changes.
    run_dir = Path(dossiers["_run"])
    hunt = (run_dir / "hunt.binding").read_text().splitlines()
    assert sum(line.startswith("prompt=") for line in hunt) == 1
    for phase in ("sweep", "arbitrate"):
        lines = (run_dir / f"{phase}.binding").read_text().splitlines()
        assert not any(line.startswith("prompt=") for line in lines), phase


def test_the_hunt_binding_carries_the_prompt_identity(tmp_path):
    env, repo, _, common = start_run(tmp_path)
    paths = artifact_paths(repo, env)
    checked(run_script(env, "dossier", "hunt", *common, "--no-sweep"), "dossier hunt")
    binding = (paths["run"] / "hunt.binding").read_text().splitlines()
    prompt = [line for line in binding if line.startswith("prompt=")]
    assert len(prompt) == 1, binding
    assert re.fullmatch(r"prompt=[0-9a-f]{64}", prompt[0]), binding
    assert "no_sweep=1" in binding
    assert "run=" in "\n".join(binding) and "phase=hunt" in binding
