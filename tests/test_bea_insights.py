"""Unit tests for bea_insights.py"""

import pytest
from bea_insights import (
    _period_label,
    calculate_sector_growth,
    format_bea_replacements,
    build_empty_bea_replacements,
)


def _row(year="2024", quarter="III", value="100000"):
    return {"Year": year, "Quarter": quarter, "DataValue": value}


class TestPeriodLabel:
    def test_standard_quarter(self):
        assert _period_label({"Year": "2024", "Quarter": "III"}) == "2024 Q3"

    def test_all_roman_quarters(self):
        assert _period_label({"Year": "2024", "Quarter": "I"}) == "2024 Q1"
        assert _period_label({"Year": "2024", "Quarter": "II"}) == "2024 Q2"
        assert _period_label({"Year": "2024", "Quarter": "III"}) == "2024 Q3"
        assert _period_label({"Year": "2024", "Quarter": "IV"}) == "2024 Q4"

    def test_missing_year_returns_empty(self):
        result = _period_label({"Quarter": "I"})
        assert result == ""

    def test_unknown_quarter_omitted(self):
        result = _period_label({"Year": "2024", "Quarter": "V"})
        assert result == "2024"


class TestCalculateSectorGrowth:
    def test_empty_rows_returns_empty_insights(self):
        result = calculate_sector_growth([])
        assert result["latest_value"] == "N/A"
        assert result["qoq_pct"] == "N/A"
        assert result["yoy_pct"] == "N/A"

    def test_single_row_no_growth_data(self):
        result = calculate_sector_growth([_row("2024", "I", "500000")])
        assert result["latest_value"] == "$500.0B"
        assert result["latest_period"] == "2024 Q1"
        assert result["qoq_pct"] == "N/A"
        assert result["yoy_pct"] == "N/A"

    def test_qoq_positive_growth(self):
        rows = [_row("2024", "I", "100000"), _row("2024", "II", "110000")]
        result = calculate_sector_growth(rows)
        assert result["qoq_pct"] == "+10.0%"
        assert result["qoq_direction"] == "up"

    def test_qoq_negative_growth(self):
        rows = [_row("2024", "I", "110000"), _row("2024", "II", "100000")]
        result = calculate_sector_growth(rows)
        assert result["qoq_pct"].startswith("-")
        assert result["qoq_direction"] == "down"

    def test_qoq_flat(self):
        rows = [_row("2024", "I", "100000"), _row("2024", "II", "100000")]
        result = calculate_sector_growth(rows)
        assert result["qoq_pct"] == "+0.0%"
        assert result["qoq_direction"] == "flat"

    def test_yoy_growth_requires_five_rows(self):
        rows = [_row("2023", "I", "100000")] + [_row("2024", q, "110000") for q in ["I", "II", "III"]]
        result = calculate_sector_growth(rows)
        assert result["yoy_pct"] == "N/A"  # only 4 rows

    def test_yoy_positive_growth(self):
        rows = [
            _row("2023", "I", "100000"),
            _row("2023", "II", "105000"),
            _row("2023", "III", "108000"),
            _row("2023", "IV", "110000"),
            _row("2024", "I", "115000"),
        ]
        result = calculate_sector_growth(rows)
        assert result["yoy_pct"] == "+15.0%"
        assert result["yoy_direction"] == "up"

    def test_latest_value_converted_to_billions(self):
        rows = [_row("2024", "I", "2000000")]
        result = calculate_sector_growth(rows)
        assert result["latest_value"] == "$2000.0B"

    def test_comma_in_data_value_handled(self):
        rows = [_row("2024", "I", "1,500,000")]
        result = calculate_sector_growth(rows)
        assert result["latest_value"] == "$1500.0B"

    def test_trend_labels_match_rows(self):
        rows = [_row("2024", "I", "100000"), _row("2024", "II", "110000")]
        result = calculate_sector_growth(rows)
        assert result["trend_labels"] == ["2024 Q1", "2024 Q2"]

    def test_trend_values_are_floats(self):
        rows = [_row("2024", "I", "100000"), _row("2024", "II", "110000")]
        result = calculate_sector_growth(rows)
        assert result["trend_values"] == [100000.0, 110000.0]

    def test_rows_sorted_chronologically(self):
        # Provide out-of-order rows; latest should be IV
        rows = [_row("2024", "IV", "120000"), _row("2024", "I", "100000")]
        result = calculate_sector_growth(rows)
        assert result["latest_period"] == "2024 Q4"

    def test_industry_name_from_industry_description(self):
        row = _row("2024", "I", "100000")
        row["IndustrYDescription"] = "Software Publishers"
        result = calculate_sector_growth([row])
        assert result["industry_name_bea"] == "Software Publishers"


class TestFormatBeaReplacements:
    def _base_insights(self, yoy="+3.5%", direction="up"):
        return {
            "latest_value": "$1500.0B",
            "latest_period": "2024 Q3",
            "qoq_pct": "+1.2%",
            "yoy_pct": yoy,
            "qoq_direction": "up",
            "yoy_direction": direction,
        }

    def test_keys_present(self):
        result = format_bea_replacements("IT Services", self._base_insights())
        expected_keys = {
            "{{BEA_INDUSTRY}}",
            "{{BEA_LATEST_VALUE}}",
            "{{BEA_LATEST_PERIOD}}",
            "{{BEA_QOQ_GROWTH}}",
            "{{BEA_YOY_GROWTH}}",
            "{{BEA_TREND_LABEL}}",
        }
        assert expected_keys == set(result.keys())

    def test_industry_name_set(self):
        result = format_bea_replacements("Healthcare", self._base_insights())
        assert result["{{BEA_INDUSTRY}}"] == "Healthcare"

    def test_expanding_trend_label(self):
        result = format_bea_replacements("IT", self._base_insights("+3.5%", "up"))
        assert "expanding" in result["{{BEA_TREND_LABEL}}"].lower()

    def test_contracting_trend_label(self):
        result = format_bea_replacements("IT", self._base_insights("-2.1%", "down"))
        assert "contracting" in result["{{BEA_TREND_LABEL}}"].lower()

    def test_stable_trend_label(self):
        result = format_bea_replacements("IT", self._base_insights("+0.0%", "flat"))
        assert "stable" in result["{{BEA_TREND_LABEL}}"].lower()

    def test_na_yoy_clears_trend_label(self):
        insights = self._base_insights()
        insights["yoy_pct"] = "N/A"
        result = format_bea_replacements("IT", insights)
        assert result["{{BEA_TREND_LABEL}}"] == ""
        assert result["{{BEA_YOY_GROWTH}}"] == ""

    def test_na_values_cleaned_to_empty_string(self):
        insights = {
            "latest_value": "N/A",
            "latest_period": "N/A",
            "qoq_pct": "N/A",
            "yoy_pct": "N/A",
            "yoy_direction": "flat",
        }
        result = format_bea_replacements("IT", insights)
        assert result["{{BEA_LATEST_VALUE}}"] == ""
        assert result["{{BEA_QOQ_GROWTH}}"] == ""


class TestBuildEmptyBeaReplacements:
    def test_returns_six_keys(self):
        result = build_empty_bea_replacements()
        assert len(result) == 6

    def test_all_values_empty_string(self):
        for v in build_empty_bea_replacements().values():
            assert v == ""
