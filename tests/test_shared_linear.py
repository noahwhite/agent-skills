"""Contract checks for estimate reads in shared/linear.md."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_estimate_read_paths_and_cli_display_limitations() -> None:
    text = (ROOT / "shared" / "linear.md").read_text()
    estimation = text.split("## Estimation and slicing\n", 1)[1].split("\n## ", 1)[0]
    lines = {line.strip().removeprefix("- ") for line in estimation.splitlines()}
    expected = {
        "`linear issue view --json` omits `estimate`, as it omits relations, "
        "even when the issue carries one, and the plain view prints no estimate line.",
        "Read an estimate with `linear api 'query { issue(id: \"ABC-123\") { estimate } }'`, "
        "or through the Linear MCP `get_issue` with the `estimate` field.",
        "The team issue list renders it in its estimate column, "
        "which is a display path, not a read path for a script.",
    }
    assert expected <= lines, f"missing estimate-read guidance: {expected - lines}"
