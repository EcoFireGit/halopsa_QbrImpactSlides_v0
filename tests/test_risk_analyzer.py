"""Unit tests for risk_analyzer.py"""

from risk_analyzer import (
    _detect_open_critical,
    _detect_critical_volume,
    _detect_recurring_issues,
    analyze_risks,
    format_risk_replacements,
    build_empty_risk_replacements,
)


class TestDetectOpenCritical:
    def test_no_tickets_returns_empty(self):
        assert _detect_open_critical([]) == []

    def test_no_critical_returns_empty(self):
        tickets = [{"priority_id": 3, "hasbeenclosed": False}]
        assert _detect_open_critical(tickets) == []

    def test_critical_closed_returns_empty(self):
        tickets = [{"priority_id": 1, "hasbeenclosed": True}]
        assert _detect_open_critical(tickets) == []

    def test_open_critical_returns_flag(self):
        tickets = [{"priority_id": 1, "hasbeenclosed": False}]
        result = _detect_open_critical(tickets)
        assert len(result) == 1
        assert result[0]["severity"] == "high"
        assert "1 critical ticket" in result[0]["flag"].lower() or "1" in result[0]["flag"]

    def test_multiple_open_critical(self):
        tickets = [
            {"priority_id": 1, "hasbeenclosed": False},
            {"priority_id": 1, "hasbeenclosed": False},
            {"priority_id": 1, "hasbeenclosed": True},
        ]
        result = _detect_open_critical(tickets)
        assert len(result) == 1
        assert "2" in result[0]["flag"]

    def test_not_closed_via_missing_key(self):
        # hasbeenclosed not present — treated as not True, so open critical
        tickets = [{"priority_id": 1}]
        result = _detect_open_critical(tickets)
        assert len(result) == 1


class TestDetectCriticalVolume:
    def test_below_threshold_returns_empty(self):
        tickets = [{"priority_id": 1}] * 3
        assert _detect_critical_volume(tickets) == []

    def test_exactly_threshold_returns_empty(self):
        tickets = [{"priority_id": 1}] * 3
        assert _detect_critical_volume(tickets) == []

    def test_above_threshold_medium_severity(self):
        tickets = [{"priority_id": 1}] * 5
        result = _detect_critical_volume(tickets)
        assert len(result) == 1
        assert result[0]["severity"] == "medium"

    def test_above_six_high_severity(self):
        tickets = [{"priority_id": 1}] * 7
        result = _detect_critical_volume(tickets)
        assert len(result) == 1
        assert result[0]["severity"] == "high"

    def test_non_critical_tickets_not_counted(self):
        tickets = [{"priority_id": 3}] * 10
        assert _detect_critical_volume(tickets) == []


class TestDetectRecurringIssues:
    def test_no_tickets_returns_empty(self):
        assert _detect_recurring_issues([]) == []

    def test_single_keyword_below_threshold(self):
        tickets = [{"summary": "wifi problem"}, {"summary": "wifi issue"}]
        result = _detect_recurring_issues(tickets)
        assert result == []

    def test_recurring_keyword_triggers_flag(self):
        tickets = [{"summary": "wifi connectivity down"}] * 3
        result = _detect_recurring_issues(tickets)
        assert len(result) == 1
        assert "wifi" in result[0]["flag"]

    def test_high_severity_at_six_or_more(self):
        tickets = [{"summary": "vpn disconnecting"}] * 6
        result = _detect_recurring_issues(tickets)
        assert result[0]["severity"] == "high"

    def test_medium_severity_below_six(self):
        tickets = [{"summary": "vpn disconnecting"}] * 4
        result = _detect_recurring_issues(tickets)
        assert result[0]["severity"] == "medium"

    def test_max_three_recurring_flags(self):
        # Three different high-frequency keywords
        tickets = (
            [{"summary": "alpha failure"}] * 3
            + [{"summary": "beta failure"}] * 3
            + [{"summary": "gamma failure"}] * 3
            + [{"summary": "delta failure"}] * 3
        )
        result = _detect_recurring_issues(tickets)
        assert len(result) <= 3

    def test_stopwords_ignored(self):
        # "the" and "a" are stopwords, so they should not produce flags
        tickets = [{"summary": "the problem"}] * 5
        result = _detect_recurring_issues(tickets)
        # "the" is a stopword; "problem" appears 5 times and should trigger
        assert any("problem" in r["flag"] for r in result)

    def test_empty_summary_handled(self):
        tickets = [{"summary": ""}] * 5
        result = _detect_recurring_issues(tickets)
        assert result == []

    def test_missing_summary_handled(self):
        tickets = [{}] * 5
        result = _detect_recurring_issues(tickets)
        assert result == []


class TestAnalyzeRisks:
    def test_empty_tickets_returns_empty(self):
        assert analyze_risks([]) == []

    def test_max_five_flags_returned(self):
        # Craft tickets to trigger all three detectors with lots of data
        tickets = (
            [{"priority_id": 1, "hasbeenclosed": False}] * 3  # open critical
            + [{"priority_id": 1, "hasbeenclosed": True}] * 5  # critical volume (8 total)
            + [{"summary": "alpha crash"}] * 3
            + [{"summary": "beta crash"}] * 3
            + [{"summary": "gamma crash"}] * 3
            + [{"summary": "delta crash"}] * 3
        )
        result = analyze_risks(tickets)
        assert len(result) <= 5

    def test_ordering_open_critical_first(self):
        tickets = (
            [{"priority_id": 1, "hasbeenclosed": True}] * 7  # critical volume
            + [{"priority_id": 1, "hasbeenclosed": False}]   # one open critical
        )
        result = analyze_risks(tickets)
        # open critical should come first
        assert "Open Critical" in result[0]["flag"]

    def test_no_critical_no_recurring_returns_empty(self):
        tickets = [{"priority_id": 3, "hasbeenclosed": True, "summary": "misc task"}]
        result = analyze_risks(tickets)
        assert result == []


class TestFormatRiskReplacements:
    def test_empty_flags_fills_empty_strings(self):
        result = format_risk_replacements([])
        assert result["{{TOP_RISK_1}}"] == ""
        assert result["{{TOP_RISK_2}}"] == ""
        assert result["{{TOP_RISK_3}}"] == ""

    def test_single_flag_fills_first_key(self):
        flags = [{"flag": "Disk space critical", "severity": "high", "detail": "..."}]
        result = format_risk_replacements(flags)
        assert result["{{TOP_RISK_1}}"] == "Disk space critical"
        assert result["{{TOP_RISK_2}}"] == ""
        assert result["{{TOP_RISK_3}}"] == ""

    def test_three_flags_fills_all_keys(self):
        flags = [
            {"flag": "Risk A", "severity": "high", "detail": ""},
            {"flag": "Risk B", "severity": "medium", "detail": ""},
            {"flag": "Risk C", "severity": "medium", "detail": ""},
        ]
        result = format_risk_replacements(flags)
        assert result["{{TOP_RISK_1}}"] == "Risk A"
        assert result["{{TOP_RISK_2}}"] == "Risk B"
        assert result["{{TOP_RISK_3}}"] == "Risk C"

    def test_more_than_three_flags_only_top_three_mapped(self):
        flags = [{"flag": f"Risk {i}", "severity": "high", "detail": ""} for i in range(5)]
        result = format_risk_replacements(flags)
        assert len(result) == 3
        assert result["{{TOP_RISK_1}}"] == "Risk 0"


class TestBuildEmptyRiskReplacements:
    def test_returns_three_keys(self):
        result = build_empty_risk_replacements()
        assert len(result) == 3

    def test_all_values_empty_string(self):
        for v in build_empty_risk_replacements().values():
            assert v == ""

    def test_expected_keys_present(self):
        result = build_empty_risk_replacements()
        assert "{{TOP_RISK_1}}" in result
        assert "{{TOP_RISK_2}}" in result
        assert "{{TOP_RISK_3}}" in result
