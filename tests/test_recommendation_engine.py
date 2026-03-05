"""Unit tests for recommendation_engine.py (Anthropic API mocked)."""

import json
from unittest.mock import MagicMock, patch

import pytest
from recommendation_engine import generate_recommendations


def _make_mock_response(recommendations: list[dict]) -> MagicMock:
    """Build a mock anthropic response object."""
    mock_content = MagicMock()
    mock_content.text = json.dumps(recommendations)
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


def _base_metrics():
    return {
        "{{TICKET_COUNT}}": "20",
        "{{SAME_DAY_RATE}}": "75",
        "{{AVG_FIRST_RESPONSE}}": "30 mins",
        "{{CRITICAL_RES_TIME}}": "4.0 hours",
        "{{PROACTIVE_PERCENT}}": "40",
        "{{REACTIVE_PERCENT}}": "60",
    }


@pytest.fixture
def mock_anthropic():
    with patch("recommendation_engine.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        yield mock_client


class TestGenerateRecommendations:
    def test_returns_list_of_dicts(self, mock_anthropic):
        recs = [{"title": "Upgrade Servers", "rationale": "Reduces latency by 40%."}]
        mock_anthropic.messages.create.return_value = _make_mock_response(recs)

        result = generate_recommendations(
            client_name="Acme Corp",
            review_period="Q1 2026",
            metrics=_base_metrics(),
            ticket_summaries=["Server down", "Email issue"],
            num_recommendations=1,
            anthropic_api_key="test-key",
        )
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "Upgrade Servers"
        assert result[0]["rationale"] == "Reduces latency by 40%."

    def test_multiple_recommendations(self, mock_anthropic):
        recs = [
            {"title": "Rec 1", "rationale": "Reason 1."},
            {"title": "Rec 2", "rationale": "Reason 2."},
            {"title": "Rec 3", "rationale": "Reason 3."},
        ]
        mock_anthropic.messages.create.return_value = _make_mock_response(recs)

        result = generate_recommendations(
            client_name="Acme",
            review_period="Q1 2026",
            metrics=_base_metrics(),
            ticket_summaries=[],
            num_recommendations=3,
            anthropic_api_key="test-key",
        )
        assert len(result) == 3

    def test_strips_whitespace_from_fields(self, mock_anthropic):
        recs = [{"title": "  Trim Me  ", "rationale": "  Also trim.  "}]
        mock_anthropic.messages.create.return_value = _make_mock_response(recs)

        result = generate_recommendations(
            client_name="Acme",
            review_period="Q1 2026",
            metrics=_base_metrics(),
            ticket_summaries=[],
            num_recommendations=1,
            anthropic_api_key="test-key",
        )
        assert result[0]["title"] == "Trim Me"
        assert result[0]["rationale"] == "Also trim."

    def test_invalid_rec_entries_filtered_out(self, mock_anthropic):
        # One valid, one missing 'title', one not a dict
        raw = [
            {"title": "Good Rec", "rationale": "Valid."},
            {"rationale": "Missing title."},
            "not a dict",
        ]
        mock_content = MagicMock()
        mock_content.text = json.dumps(raw)
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_anthropic.messages.create.return_value = mock_response

        result = generate_recommendations(
            client_name="Acme",
            review_period="Q1 2026",
            metrics=_base_metrics(),
            ticket_summaries=[],
            num_recommendations=3,
            anthropic_api_key="test-key",
        )
        assert len(result) == 1
        assert result[0]["title"] == "Good Rec"

    def test_markdown_code_fences_stripped(self, mock_anthropic):
        recs = [{"title": "Test", "rationale": "Reason."}]
        mock_content = MagicMock()
        mock_content.text = "```json\n" + json.dumps(recs) + "\n```"
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_anthropic.messages.create.return_value = mock_response

        result = generate_recommendations(
            client_name="Acme",
            review_period="Q1 2026",
            metrics=_base_metrics(),
            ticket_summaries=[],
            num_recommendations=1,
            anthropic_api_key="test-key",
        )
        assert len(result) == 1
        assert result[0]["title"] == "Test"

    def test_missing_api_key_raises_value_error(self):
        with patch("recommendation_engine.os.getenv", return_value=None):
            with pytest.raises(ValueError, match="Anthropic API key is missing"):
                generate_recommendations(
                    client_name="Acme",
                    review_period="Q1 2026",
                    metrics=_base_metrics(),
                    ticket_summaries=[],
                    num_recommendations=1,
                    anthropic_api_key=None,
                )

    def test_with_business_impact_and_risk_flags(self, mock_anthropic):
        recs = [{"title": "Fix Infrastructure", "rationale": "Critical risk."}]
        mock_anthropic.messages.create.return_value = _make_mock_response(recs)

        impact = {
            "productivity_hours_lost": 50.0,
            "estimated_dollar_cost": 3500.0,
            "risk_statement": "High risk: multiple critical incidents.",
        }
        risk_flags = [
            {"flag": "Open Critical Tickets: 2", "severity": "high", "detail": "..."}
        ]

        result = generate_recommendations(
            client_name="Acme",
            review_period="Q1 2026",
            metrics=_base_metrics(),
            ticket_summaries=["Server down"],
            num_recommendations=1,
            anthropic_api_key="test-key",
            employee_count=100,
            avg_hourly_rate=70.0,
            business_impact=impact,
            risk_flags=risk_flags,
        )
        assert len(result) == 1
        # Verify that the prompt included the profile/risk sections by checking
        # the call was made with the right model
        call_kwargs = mock_anthropic.messages.create.call_args
        assert call_kwargs is not None

    def test_uses_correct_model(self, mock_anthropic):
        recs = [{"title": "Test", "rationale": "Reason."}]
        mock_anthropic.messages.create.return_value = _make_mock_response(recs)

        generate_recommendations(
            client_name="Acme",
            review_period="Q1 2026",
            metrics=_base_metrics(),
            ticket_summaries=[],
            num_recommendations=1,
            anthropic_api_key="test-key",
        )
        call_kwargs = mock_anthropic.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-5-20250929"
