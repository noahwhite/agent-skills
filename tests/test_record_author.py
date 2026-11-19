"""SKL-35 AC3: the optional `review.record_author` profile key pins the review-of-record author."""

import copy
import json

import jsonschema
import pytest
import yaml

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "profile" / "schema.json").read_text())
EXAMPLE = yaml.safe_load((ROOT / "profile" / "example.yaml").read_text())
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)


def errors(document) -> list:
    return list(VALIDATOR.iter_errors(document))


def with_record_author(value):
    profile = copy.deepcopy(EXAMPLE)
    profile["review"]["record_author"] = value
    return profile


def test_example_profile_validates_without_record_author() -> None:
    assert not errors(EXAMPLE)


@pytest.mark.parametrize("login", ["octocat", "devin-ai-integration[bot]", "a-bot9"])
def test_record_author_accepts_a_user_or_bot_login(login) -> None:
    assert not errors(with_record_author(login)), login


@pytest.mark.parametrize("value", [123, True, ["x"], None])
def test_record_author_rejects_a_non_string(value) -> None:
    assert errors(with_record_author(value)), value


def test_record_author_rejects_an_empty_string() -> None:
    assert errors(with_record_author(""))


@pytest.mark.parametrize("login", ["-octocat", "octocat-", "octo cat", "octocat.", "-bad[bot]", "x" * 46])
def test_record_author_rejects_an_invalid_login(login) -> None:
    assert errors(with_record_author(login)), login


def test_record_author_description_states_the_default_and_fail_closed() -> None:
    description = SCHEMA["properties"]["review"]["properties"]["record_author"]["description"]
    assert "authenticated account" in description
    assert "fail closed" in description


def test_example_documents_record_author_as_a_comment() -> None:
    text = (ROOT / "profile" / "example.yaml").read_text()
    assert "# record_author:" in text
