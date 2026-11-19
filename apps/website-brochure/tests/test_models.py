import pytest
from pydantic import ValidationError

from website_brochure.llm import ProviderError, _validate_model_json
from website_brochure.models import Brochure, GeneratedContent


READY_OUTPUT = {
    "status": "ready",
    "factual_summary": "A workshop provider helps product teams improve practical decision-making skills.",
    "brochure": {
        "headline": "Make better product decisions together",
        "introduction": "Practical, facilitated workshops help established teams build repeatable product habits.",
        "sections": [
            {
                "heading": "Hands-on practice",
                "body": "Teams use realistic exercises alongside concise lessons and guided reflection.",
            },
            {
                "heading": "Built for teams",
                "body": "Programs serve product managers, designers, and engineers working together.",
            },
        ],
        "call_to_action": "Request a program outline through the inquiry form.",
    },
    "feedback": None,
}


def test_ready_output_validates() -> None:
    result = GeneratedContent.model_validate(READY_OUTPUT)
    assert result.brochure is not None
    assert len(result.brochure.sections) == 2


def test_ready_output_requires_brochure() -> None:
    invalid = {**READY_OUTPUT, "brochure": None}
    with pytest.raises(ValidationError, match="requires a brochure"):
        GeneratedContent.model_validate(invalid)


def test_ready_output_tolerates_unused_feedback_from_small_local_models() -> None:
    with_feedback = {**READY_OUTPUT, "feedback": "Extra source detail could improve the copy."}

    result = GeneratedContent.model_validate(with_feedback)

    assert result.status == "ready"
    assert result.brochure is not None


def test_insufficient_output_requires_feedback() -> None:
    invalid = {
        "status": "insufficient",
        "factual_summary": "The page contains a brief company name but no details about its program.",
        "brochure": None,
        "feedback": None,
    }
    with pytest.raises(ValidationError, match="requires feedback"):
        GeneratedContent.model_validate(invalid)


def test_invalid_provider_json_becomes_safe_error() -> None:
    with pytest.raises(ProviderError, match="invalid brochure"):
        _validate_model_json("not-json")


def test_unknown_model_fields_are_rejected() -> None:
    invalid = {**READY_OUTPUT, "secret_extra": "not allowed"}
    with pytest.raises(ValidationError, match="Extra inputs"):
        GeneratedContent.model_validate(invalid)


def test_unsupported_details_are_not_required_and_call_to_action_can_be_null() -> None:
    without_call_to_action = {
        **READY_OUTPUT,
        "brochure": {**READY_OUTPUT["brochure"], "call_to_action": None},
    }

    result = GeneratedContent.model_validate(without_call_to_action)

    assert result.brochure is not None
    assert result.brochure.call_to_action is None
    assert set(Brochure.model_fields) == {
        "headline",
        "introduction",
        "sections",
        "call_to_action",
    }

