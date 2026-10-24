# SKL-55 mutation evidence

Measured at implementation head `08bf73799b347ef3efc80f302c0bd5edb927b46b` using CPython 3.12.3 with locked dependencies; all 16 checks were replayed during evidence remediation against identical skill and test content from shipped `001d1a3338ce7ccb4774c82ff85cb4011de9ec01`.
The modified files are `skills/story-refinement/SKILL.md` and `skills/story-refinement/references/refinement-record.md`, with commands run from the repository root.
Before each check, save the document bytes, make only the specified edit, execute the quoted shell command below, then restore the saved bytes even if the command fails.
For each deletion, remove the exact named phrase once.
For each legacy-string probe, append the literal string to the named file; these include synthetic cross-file cases as well as strings present in the original documents.
For item 14, replace the new base-name instruction with the original sentence: "Keep the raw voter files in the session's scratch directory and cite their paths in the record."
For items 15 and 16, `\n` denotes an inserted newline; preserve all other text, including indentation except where specified.
All mutations were restored and the final source bytes matched the saved bytes.
All commands below were executed through the shell with the displayed quoting; the intended failures exited 1, and the formatting probes exited 0.

1. Delete `Keep the raw voter files in the session's scratch directory and cite each file by its base name only (never a directory path) in the record.` from SKILL.md once
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k records_cite_base_names
   Exit: 1; FAILED tests/test_story_refinement.py::test_records_cite_base_names_and_include_needed_content

2. Delete `Quote or attach any file content a reader needs in the record.` from SKILL.md once
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k records_cite_base_names
   Exit: 1; FAILED tests/test_story_refinement.py::test_records_cite_base_names_and_include_needed_content

3. Delete `The record never carries a local path; cite each raw voter file by its base name only.` from refinement-record.md once
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k record_intro_excludes
   Exit: 1; FAILED tests/test_story_refinement.py::test_record_intro_excludes_local_paths_and_includes_needed_content

4. Delete `Quote or attach any file content a reader needs in the record.` from refinement-record.md once
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k record_intro_excludes
   Exit: 1; FAILED tests/test_story_refinement.py::test_record_intro_excludes_local_paths_and_includes_needed_content

5. Delete `- Product owner: <file base name>` from refinement-record.md once
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k record_templates_cite_file_base_names
   Exit: 1; FAILED tests/test_story_refinement.py::test_record_templates_cite_file_base_names[Refinement comment-- Product owner: <file base name>]

6. Delete `- Engineer one (<family or model>): <file base name>` from refinement-record.md once
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k record_templates_cite_file_base_names
   Exit: 1; FAILED tests/test_story_refinement.py::test_record_templates_cite_file_base_names[Refinement comment-- Engineer one (<family or model>): <file base name>]

7. Delete `- Engineer two (<family or model>): <file base name>` from refinement-record.md once
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k record_templates_cite_file_base_names
   Exit: 1; FAILED tests/test_story_refinement.py::test_record_templates_cite_file_base_names[Refinement comment-- Engineer two (<family or model>): <file base name>]

8. Delete `- SM/EM contribution (not a vote): <file base name>` from refinement-record.md once
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k record_templates_cite_file_base_names
   Exit: 1; FAILED tests/test_story_refinement.py::test_record_templates_cite_file_base_names[Refinement comment-- SM/EM contribution (not a vote): <file base name>]

9. Delete `- SM/EM sizing context, after all three values: <file base name> or verbatim` from refinement-record.md once
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k record_templates_cite_file_base_names
   Exit: 1; FAILED tests/test_story_refinement.py::test_record_templates_cite_file_base_names[Pointing record-- SM/EM sizing context, after all three values: <file base name> or verbatim]

10. Introduce legacy-string probe `<scratch path>` in SKILL.md
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k skill_records_never
   Exit: 1; FAILED tests/test_story_refinement.py::test_skill_records_never_request_local_paths[<scratch path>]

11. Introduce legacy-string probe `cite their paths` in SKILL.md
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k skill_records_never
   Exit: 1; FAILED tests/test_story_refinement.py::test_skill_records_never_request_local_paths[cite their paths]

12. Introduce legacy-string probe `<scratch path>` in refinement-record.md
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k record_templates_never
   Exit: 1; FAILED tests/test_story_refinement.py::test_record_templates_never_request_local_paths[<scratch path>]

13. Introduce legacy-string probe `cite their paths` in refinement-record.md
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k record_templates_never
   Exit: 1; FAILED tests/test_story_refinement.py::test_record_templates_never_request_local_paths[cite their paths]

14. Restore original Records sentence
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k 'records_cite_base_names or skill_records_never'
   Exit: 1; FAILED tests/test_story_refinement.py::test_records_cite_base_names_and_include_needed_content; FAILED tests/test_story_refinement.py::test_skill_records_never_request_local_paths[cite their paths]

15. Correct formatting probe in SKILL.md: wrap `any file content a reader needs` as `any file content\na reader needs` and change `base name only` to `base  name only`
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k 'records_cite_base_names or skill_records_never'
   Exit: 0; 3 passed, 102 deselected in 0.05s

16. Correct formatting probe in refinement-record.md: wrap `any file content a reader needs` as `any file content\na reader needs` and indent the Product owner source line with four spaces instead of two
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k 'record_intro_excludes or record_templates'
   Exit: 0; 8 passed, 97 deselected in 0.05s
