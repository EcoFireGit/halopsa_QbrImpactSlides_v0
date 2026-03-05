"""Unit tests for business_impact.py"""

import pytest
from business_impact import (
    _parse_crit_res_hours,
    calculate_business_impact,
    format_impact_replacements,
    build_empty_impact_replacements,
)


class TestParseCritResHours:
    def test_na_returns_zero(self):
        assert _parse_crit_res_hours("N/A") == 0.0

    def test_less_than_prefix_returns_half(self):
        assert _parse_crit_res_hours("< 1 hour") == 0.5

    def test_hours_plural(self):
        assert _parse_crit_res_hours("8.0 hours") == 8.0

    def test_hour_singular(self):
        assert _parse_crit_res_hours("1.0 hour") == 1.0

    def test_float_string(self):
        assert _parse_crit_res_hours("12.5 hours") == 12.5

    def test_invalid_string_returns_zero(self):
        assert _parse_crit_res_hours("bad data") == 0.0

    def test_whitespace_stripped(self):
        assert _parse_crit_res_hours("  4.0 hours  ") == 4.0


class TestCalculateBusinessImpact:
    def _make_tickets(self, count_critical, count_non_critical=0):
        tickets = []
        for _ in range(count_critical):
            tickets.append({"priority_id": 1})
        for _ in range(count_non_critical):
            tickets.append({"priority_id": 3})
        return tickets

    def test_no_employee_count_has_data_false(self):
        tickets = self._make_tickets(2)
        metrics = {"{{CRITICAL_RES_TIME}}": "4.0 hours", "{{PROACTIVE_PERCENT}}": "50"}
        result = calculate_business_impact(metrics, tickets, 0, 50.0)
        assert result["has_data"] is False

    def test_with_employees_has_data_true(self):
        tickets = self._make_tickets(2)
        metrics = {"{{CRITICAL_RES_TIME}}": "4.0 hours", "{{PROACTIVE_PERCENT}}": "50"}
        result = calculate_business_impact(metrics, tickets, 100, 65.0)
        assert result["has_data"] is True

    def test_critical_ticket_count(self):
        tickets = self._make_tickets(3, count_non_critical=5)
        metrics = {"{{CRITICAL_RES_TIME}}": "N/A", "{{PROACTIVE_PERCENT}}": "30"}
        result = calculate_business_impact(metrics, tickets, 50, 60.0)
        assert result["critical_ticket_count"] == 3

    def test_productivity_hours_formula(self):
        tickets = self._make_tickets(2)
        metrics = {"{{CRITICAL_RES_TIME}}": "10.0 hours", "{{PROACTIVE_PERCENT}}": "50"}
        result = calculate_business_impact(metrics, tickets, 100, 50.0)
        # employees_affected = 100 * 0.1 = 10
        # productivity_hours_lost = 2 * 10.0 * 10 = 200
        assert result["employees_affected"] == pytest.approx(10.0)
        assert result["productivity_hours_lost"] == pytest.approx(200.0)

    def test_estimated_dollar_cost(self):
        tickets = self._make_tickets(2)
        metrics = {"{{CRITICAL_RES_TIME}}": "10.0 hours", "{{PROACTIVE_PERCENT}}": "50"}
        result = calculate_business_impact(metrics, tickets, 100, 75.0)
        # 200 hours * $75 = $15,000
        assert result["estimated_dollar_cost"] == pytest.approx(15000.0)

    def test_high_risk_statement(self):
        tickets = self._make_tickets(5)
        metrics = {"{{CRITICAL_RES_TIME}}": "N/A", "{{PROACTIVE_PERCENT}}": "20"}
        result = calculate_business_impact(metrics, tickets, 50, 50.0)
        assert "High risk" in result["risk_statement"]

    def test_moderate_risk_statement(self):
        tickets = self._make_tickets(2)
        metrics = {"{{CRITICAL_RES_TIME}}": "N/A", "{{PROACTIVE_PERCENT}}": "60"}
        result = calculate_business_impact(metrics, tickets, 50, 50.0)
        assert "Moderate risk" in result["risk_statement"]

    def test_low_risk_statement_no_critical(self):
        tickets = self._make_tickets(0, count_non_critical=3)
        metrics = {"{{CRITICAL_RES_TIME}}": "N/A", "{{PROACTIVE_PERCENT}}": "70"}
        result = calculate_business_impact(metrics, tickets, 50, 50.0)
        assert "Low risk" in result["risk_statement"]

    def test_high_risk_boundary_exactly_3_critical(self):
        # critical_count == 3 is NOT > 3, so not high risk
        tickets = self._make_tickets(3)
        metrics = {"{{CRITICAL_RES_TIME}}": "N/A", "{{PROACTIVE_PERCENT}}": "10"}
        result = calculate_business_impact(metrics, tickets, 50, 50.0)
        assert "Moderate risk" in result["risk_statement"]

    def test_proactive_percent_invalid_defaults_to_zero(self):
        tickets = self._make_tickets(5)
        metrics = {"{{CRITICAL_RES_TIME}}": "N/A", "{{PROACTIVE_PERCENT}}": "bad"}
        result = calculate_business_impact(metrics, tickets, 50, 50.0)
        # proactive_pct = 0, critical > 3, should be high risk
        assert "High risk" in result["risk_statement"]


class TestFormatImpactReplacements:
    def _base_impact(self, hours=100.0, cost=5000.0, statement="Low risk"):
        return {
            "productivity_hours_lost": hours,
            "estimated_dollar_cost": cost,
            "risk_statement": statement,
        }

    def test_hours_formatted(self):
        result = format_impact_replacements(self._base_impact(hours=123.4))
        assert result["{{PRODUCTIVITY_HOURS_LOST}}"] == "123.4"

    def test_cost_formatted_with_dollar(self):
        result = format_impact_replacements(self._base_impact(cost=12345.0))
        assert result["{{ESTIMATED_COST}}"] == "$12,345"

    def test_zero_hours_returns_zero_string(self):
        result = format_impact_replacements(self._base_impact(hours=0.0))
        assert result["{{PRODUCTIVITY_HOURS_LOST}}"] == "0"

    def test_zero_cost_returns_zero_string(self):
        result = format_impact_replacements(self._base_impact(cost=0.0))
        assert result["{{ESTIMATED_COST}}"] == "$0"

    def test_risk_statement_passed_through(self):
        result = format_impact_replacements(self._base_impact(statement="High risk: test"))
        assert result["{{RISK_STATEMENT}}"] == "High risk: test"


class TestBuildEmptyImpactReplacements:
    def test_returns_three_keys(self):
        result = build_empty_impact_replacements()
        assert len(result) == 3

    def test_all_values_empty_string(self):
        result = build_empty_impact_replacements()
        for v in result.values():
            assert v == ""

    def test_expected_keys_present(self):
        result = build_empty_impact_replacements()
        assert "{{PRODUCTIVITY_HOURS_LOST}}" in result
        assert "{{ESTIMATED_COST}}" in result
        assert "{{RISK_STATEMENT}}" in result
