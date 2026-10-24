# SKL-55 mutation evidence

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

10. Reintroduce `<scratch path>` in SKILL.md
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k skill_records_never
   Exit: 1; FAILED tests/test_story_refinement.py::test_skill_records_never_request_local_paths[<scratch path>]

11. Reintroduce `cite their paths` in SKILL.md
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k skill_records_never
   Exit: 1; FAILED tests/test_story_refinement.py::test_skill_records_never_request_local_paths[cite their paths]

12. Reintroduce `<scratch path>` in refinement-record.md
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k record_templates_never
   Exit: 1; FAILED tests/test_story_refinement.py::test_record_templates_never_request_local_paths[<scratch path>]

13. Reintroduce `cite their paths` in refinement-record.md
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k record_templates_never
   Exit: 1; FAILED tests/test_story_refinement.py::test_record_templates_never_request_local_paths[cite their paths]

14. Restore original Records sentence
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k records_cite_base_names or skill_records_never
   Exit: 1; FAILED tests/test_story_refinement.py::test_records_cite_base_names_and_include_needed_content; FAILED tests/test_story_refinement.py::test_skill_records_never_request_local_paths[cite their paths]

15. Correct formatting probe in SKILL.md
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k records_cite_base_names or skill_records_never
   Exit: 0; 3 passed, 102 deselected in 0.06s

16. Correct formatting probe in refinement-record.md
   Command: uv run --locked pytest -q tests/test_story_refinement.py -k record_intro_excludes or record_templates
   Exit: 0; 8 passed, 97 deselected in 0.05s
