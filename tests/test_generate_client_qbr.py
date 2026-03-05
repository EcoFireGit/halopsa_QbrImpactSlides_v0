"""Unit tests for generate_client_qbr.py (metrics, health score, recommendations)."""

import pytest
from generate_client_qbr import (
    calculate_metrics,
    calculate_health_score,
    build_recommendation_replacements,
    _estimate_text_height_in,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ticket(
    tickettype_id=1,
    priority_id=3,
    hasbeenclosed=True,
    dateoccurred="2026-01-10T09:00:00",
    dateclosed="2026-01-10T17:00:00",
    responsedate="2026-01-10T09:30:00",
    ticketage=8.0,
):
    return {
        "id": 1,
        "tickettype_id": tickettype_id,
        "priority_id": priority_id,
        "hasbeenclosed": hasbeenclosed,
        "dateoccurred": dateoccurred,
        "dateclosed": dateclosed,
        "responsedate": responsedate,
        "ticketage": ticketage,
    }


# ---------------------------------------------------------------------------
# calculate_metrics
# ---------------------------------------------------------------------------


class TestCalculateMetrics:
    def test_none_input_returns_empty_metrics(self):
        result = calculate_metrics(None)
        assert result["{{TICKET_COUNT}}"] == "0"
        assert result["{{SAME_DAY_RATE}}"] == "N/A"

    def test_empty_list_returns_empty_metrics(self):
        result = calculate_metrics([])
        assert result["{{TICKET_COUNT}}"] == "0"

    def test_total_ticket_count(self):
        tickets = [_ticket()] * 5
        result = calculate_metrics(tickets)
        assert result["{{TICKET_COUNT}}"] == "5"

    def test_proactive_ticket_type_30(self):
        tickets = [_ticket(tickettype_id=30), _ticket(tickettype_id=1)]
        result = calculate_metrics(tickets)
        # 1 proactive out of 2 typed = 50%
        assert result["{{PROACTIVE_PERCENT}}"] == "50"
        assert result["{{REACTIVE_PERCENT}}"] == "50"

    def test_proactive_ticket_types_40_and_100(self):
        tickets = [
            _ticket(tickettype_id=40),
            _ticket(tickettype_id=100),
            _ticket(tickettype_id=1),
        ]
        result = calculate_metrics(tickets)
        assert int(result["{{PROACTIVE_PERCENT}}"]) == pytest.approx(66, abs=1)

    def test_same_day_resolution_same_date(self):
        ticket = _ticket(
            hasbeenclosed=True,
            dateoccurred="2026-01-10T09:00:00",
            dateclosed="2026-01-10T17:00:00",
        )
        result = calculate_metrics([ticket])
        assert result["{{SAME_DAY_RATE}}"] == "100"

    def test_same_day_resolution_different_date(self):
        ticket = _ticket(
            hasbeenclosed=True,
            dateoccurred="2026-01-10T09:00:00",
            dateclosed="2026-01-11T09:00:00",
        )
        result = calculate_metrics([ticket])
        assert result["{{SAME_DAY_RATE}}"] == "0"

    def test_same_day_rate_zero_when_no_closed(self):
        ticket = _ticket(hasbeenclosed=False)
        result = calculate_metrics([ticket])
        assert result["{{SAME_DAY_RATE}}"] == "0"

    def test_critical_resolution_time_hours(self):
        ticket = _ticket(priority_id=1, ticketage=12.0)
        result = calculate_metrics([ticket])
        assert "12.0" in result["{{CRITICAL_RES_TIME}}"]

    def test_critical_res_time_no_critical_tickets(self):
        ticket = _ticket(priority_id=3)
        result = calculate_metrics([ticket])
        assert result["{{CRITICAL_RES_TIME}}"] == "< 1 hour"

    def test_critical_res_time_negative_age_treated_as_invalid(self):
        ticket = _ticket(priority_id=1, ticketage=-5.0)
        result = calculate_metrics([ticket])
        assert result["{{CRITICAL_RES_TIME}}"] == "< 1 hour"

    def test_avg_first_response_minutes(self):
        # 30-minute response
        ticket = _ticket(
            dateoccurred="2026-01-10T09:00:00",
            responsedate="2026-01-10T09:30:00",
        )
        result = calculate_metrics([ticket])
        assert result["{{AVG_FIRST_RESPONSE}}"] == "30 mins"

    def test_avg_first_response_hours(self):
        # 2-hour response
        ticket = _ticket(
            dateoccurred="2026-01-10T09:00:00",
            responsedate="2026-01-10T11:00:00",
        )
        result = calculate_metrics([ticket])
        assert "2.0 hours" in result["{{AVG_FIRST_RESPONSE}}"]

    def test_avg_first_response_na_when_invalid_response_date(self):
        ticket = _ticket(responsedate="0001-01-01T00:00:00")
        result = calculate_metrics([ticket])
        assert result["{{AVG_FIRST_RESPONSE}}"] == "N/A"

    def test_avg_first_response_skips_negative_diff(self):
        # response before occurrence — should be skipped
        ticket = _ticket(
            dateoccurred="2026-01-10T10:00:00",
            responsedate="2026-01-10T09:00:00",
        )
        result = calculate_metrics([ticket])
        assert result["{{AVG_FIRST_RESPONSE}}"] == "N/A"

    def test_untyped_ticket_not_counted_in_proactive_or_reactive(self):
        # ticket type 9999 is reactive; type 999 is unknown
        tickets = [_ticket(tickettype_id=999)]
        result = calculate_metrics(tickets)
        assert result["{{PROACTIVE_PERCENT}}"] == "0"
        assert result["{{REACTIVE_PERCENT}}"] == "0"


# ---------------------------------------------------------------------------
# calculate_health_score
# ---------------------------------------------------------------------------


class TestCalculateHealthScore:
    def test_perfect_score(self):
        metrics = {
            "{{PROACTIVE_PERCENT}}": "100",
            "{{SAME_DAY_RATE}}": "100",
            "{{CRITICAL_RES_TIME}}": "< 1 hour",
            "{{AVG_FIRST_RESPONSE}}": "10 mins",
        }
        assert calculate_health_score(metrics) == 100

    def test_zero_score(self):
        metrics = {
            "{{PROACTIVE_PERCENT}}": "0",
            "{{SAME_DAY_RATE}}": "0",
            "{{CRITICAL_RES_TIME}}": "24.0 hours",
            "{{AVG_FIRST_RESPONSE}}": "300 mins",
        }
        assert calculate_health_score(metrics) == 0

    def test_na_response_gives_neutral_12_5(self):
        metrics = {
            "{{PROACTIVE_PERCENT}}": "0",
            "{{SAME_DAY_RATE}}": "0",
            "{{CRITICAL_RES_TIME}}": "24.0 hours",
            "{{AVG_FIRST_RESPONSE}}": "N/A",
        }
        # proactive=0, same_day=0, critical=0, response=12.5 → 12 or 13
        score = calculate_health_score(metrics)
        assert score == 13  # int(round(12.5))

    def test_na_critical_time_gives_full_25(self):
        metrics = {
            "{{PROACTIVE_PERCENT}}": "0",
            "{{SAME_DAY_RATE}}": "0",
            "{{CRITICAL_RES_TIME}}": "N/A",
            "{{AVG_FIRST_RESPONSE}}": "300 mins",
        }
        # critical=25, others=0 → 25
        assert calculate_health_score(metrics) == 25

    def test_critical_time_at_4h_boundary(self):
        metrics = {
            "{{PROACTIVE_PERCENT}}": "0",
            "{{SAME_DAY_RATE}}": "0",
            "{{CRITICAL_RES_TIME}}": "4.0 hours",
            "{{AVG_FIRST_RESPONSE}}": "300 mins",
        }
        # critical=25, response=0, proactive=0, same_day=0
        assert calculate_health_score(metrics) == 25

    def test_critical_time_linear_interpolation(self):
        # 14h is midway between 4 and 24 → 12.5 pts for critical
        metrics = {
            "{{PROACTIVE_PERCENT}}": "0",
            "{{SAME_DAY_RATE}}": "0",
            "{{CRITICAL_RES_TIME}}": "14.0 hours",
            "{{AVG_FIRST_RESPONSE}}": "300 mins",
        }
        score = calculate_health_score(metrics)
        assert score == 13  # int(round(12.5))

    def test_response_at_30_min_boundary(self):
        metrics = {
            "{{PROACTIVE_PERCENT}}": "0",
            "{{SAME_DAY_RATE}}": "0",
            "{{CRITICAL_RES_TIME}}": "24.0 hours",
            "{{AVG_FIRST_RESPONSE}}": "30 mins",
        }
        assert calculate_health_score(metrics) == 25

    def test_response_in_hours_converted(self):
        # 1 hour = 60 mins — midway between 30 and 240: (60-30)/210 * 25 = ~3.57, so ~21.43 pts
        metrics = {
            "{{PROACTIVE_PERCENT}}": "0",
            "{{SAME_DAY_RATE}}": "0",
            "{{CRITICAL_RES_TIME}}": "24.0 hours",
            "{{AVG_FIRST_RESPONSE}}": "1.0 hours",
        }
        score = calculate_health_score(metrics)
        assert 20 <= score <= 22

    def test_invalid_proactive_defaults_to_zero(self):
        metrics = {
            "{{PROACTIVE_PERCENT}}": "bad",
            "{{SAME_DAY_RATE}}": "0",
            "{{CRITICAL_RES_TIME}}": "N/A",
            "{{AVG_FIRST_RESPONSE}}": "N/A",
        }
        score = calculate_health_score(metrics)
        # proactive=0, same_day=0, critical=25, response=12.5 → ~38
        assert 37 <= score <= 38

    def test_score_is_int(self):
        metrics = {
            "{{PROACTIVE_PERCENT}}": "50",
            "{{SAME_DAY_RATE}}": "60",
            "{{CRITICAL_RES_TIME}}": "8.0 hours",
            "{{AVG_FIRST_RESPONSE}}": "45 mins",
        }
        assert isinstance(calculate_health_score(metrics), int)


# ---------------------------------------------------------------------------
# build_recommendation_replacements
# ---------------------------------------------------------------------------


class TestBuildRecommendationReplacements:
    def test_single_recommendation(self):
        recs = [{"title": "Upgrade Servers", "rationale": "Reduces downtime risk."}]
        result = build_recommendation_replacements(recs)
        assert result["{{REC_1_TITLE}}"] == "Upgrade Servers"
        assert result["{{REC_1_RATIONALE}}"] == "Reduces downtime risk."
        # Unused slots filled with empty strings
        assert result["{{REC_2_TITLE}}"] == ""
        assert result["{{REC_10_TITLE}}"] == ""

    def test_always_generates_10_slots(self):
        recs = [{"title": f"Rec {i}", "rationale": "..."} for i in range(3)]
        result = build_recommendation_replacements(recs)
        assert len(result) == 20  # 10 titles + 10 rationales

    def test_empty_recommendations_all_empty(self):
        result = build_recommendation_replacements([])
        for v in result.values():
            assert v == ""

    def test_ten_recommendations_all_filled(self):
        recs = [{"title": f"Rec {i}", "rationale": f"Rationale {i}"} for i in range(10)]
        result = build_recommendation_replacements(recs)
        for i in range(1, 11):
            assert result[f"{{{{REC_{i}_TITLE}}}}"] == f"Rec {i - 1}"

    def test_key_format(self):
        recs = [{"title": "Test", "rationale": "Reason"}]
        result = build_recommendation_replacements(recs)
        assert "{{REC_1_TITLE}}" in result
        assert "{{REC_1_RATIONALE}}" in result


# ---------------------------------------------------------------------------
# _estimate_text_height_in
# ---------------------------------------------------------------------------


class TestEstimateTextHeightIn:
    def test_empty_text_returns_one_line_height(self):
        height = _estimate_text_height_in("", 12, 8.0)
        # 1 line * 12pt * 1.2 / 72 = 0.2 inches
        assert height == pytest.approx(0.2, rel=0.01)

    def test_long_text_has_more_lines_than_short_text(self):
        short = _estimate_text_height_in("Short text", 12, 4.0)
        long = _estimate_text_height_in("A" * 500, 12, 4.0)
        assert long > short

    def test_space_after_added_to_height(self):
        without = _estimate_text_height_in("test", 12, 8.0, space_after_pt=0)
        with_space = _estimate_text_height_in("test", 12, 8.0, space_after_pt=12)
        assert with_space > without
