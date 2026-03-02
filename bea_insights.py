"""
BEA Data Processing — Sector Growth Insights
Converts raw BEA GDP-by-Industry rows into formatted metrics and PPTX placeholders.
"""

_ROMAN_TO_Q = {"I": "Q1", "II": "Q2", "III": "Q3", "IV": "Q4"}


def _period_label(row: dict) -> str:
    """Build a display label like '2024 Q3' from BEA Year/Quarter fields."""
    year = row.get("Year", "")
    quarter = _ROMAN_TO_Q.get(row.get("Quarter", ""), "")
    return f"{year} {quarter}".strip() if year else ""


INDUSTRY_SECTORS = {
    "Information Technology & Data Services": "51",
    "Healthcare & Social Assistance": "62",
    "Finance & Insurance": "52",
    "Professional, Scientific & Tech Svcs": "54",
    "Manufacturing": "31G",
    "Retail Trade": "44RT",
    "Real Estate & Rental": "53",
    "Construction": "23",
    "Educational Services": "61",
    "Accommodation & Food Services": "72",
    "Transportation & Warehousing": "48TW",
    "Wholesale Trade": "42",
    "Management of Companies": "55",
    "Utilities": "22",
    "Agriculture, Forestry & Fishing": "11",
}


def calculate_sector_growth(raw_rows: list[dict]) -> dict:
    """
    Compute growth metrics from BEA GDP-by-Industry rows.

    Returns a dict with:
        latest_period, latest_value, qoq_pct, yoy_pct,
        qoq_direction, yoy_direction, trend_labels, trend_values,
        industry_name_bea
    """
    if not raw_rows:
        return _empty_insights()

    # Sort chronologically; Roman numerals (I < II < III < IV) sort correctly lexicographically.
    rows = sorted(raw_rows, key=lambda r: (r.get("Year", ""), r.get("Quarter", "")))

    def parse_value(row):
        raw = row.get("DataValue", "").replace(",", "")
        try:
            return float(raw)
        except (ValueError, AttributeError):
            return None

    trend_labels = [_period_label(r) for r in rows]
    trend_values = [parse_value(r) for r in rows]

    latest_row = rows[-1]
    latest_raw = parse_value(latest_row)
    latest_period = _period_label(latest_row)

    # BEA values are in millions of chained 2017 dollars → divide by 1000 for $B
    if latest_raw is not None:
        latest_value = f"${latest_raw / 1000:.1f}B"
    else:
        latest_value = "N/A"

    # QoQ: compare last row to second-to-last
    qoq_pct = "N/A"
    qoq_direction = "flat"
    if len(rows) >= 2 and parse_value(rows[-2]) is not None and latest_raw is not None:
        prev = parse_value(rows[-2])
        if prev != 0:
            pct = (latest_raw - prev) / prev * 100
            qoq_pct = f"+{pct:.1f}%" if pct >= 0 else f"{pct:.1f}%"
            qoq_direction = "up" if pct > 0.05 else ("down" if pct < -0.05 else "flat")

    # YoY: compare last row to row[-5] (same quarter prior year, 4 quarters back)
    yoy_pct = "N/A"
    yoy_direction = "flat"
    if len(rows) >= 5 and parse_value(rows[-5]) is not None and latest_raw is not None:
        year_ago = parse_value(rows[-5])
        if year_ago != 0:
            pct = (latest_raw - year_ago) / year_ago * 100
            yoy_pct = f"+{pct:.1f}%" if pct >= 0 else f"{pct:.1f}%"
            yoy_direction = "up" if pct > 0.05 else ("down" if pct < -0.05 else "flat")

    industry_name_bea = latest_row.get(
        "IndustrYDescription", latest_row.get("Industry", "")
    )

    return {
        "latest_period": latest_period,
        "latest_value": latest_value,
        "qoq_pct": qoq_pct,
        "yoy_pct": yoy_pct,
        "qoq_direction": qoq_direction,
        "yoy_direction": yoy_direction,
        "trend_labels": trend_labels,
        "trend_values": trend_values,
        "industry_name_bea": industry_name_bea,
    }


def _empty_insights() -> dict:
    return {
        "latest_period": "N/A",
        "latest_value": "N/A",
        "qoq_pct": "N/A",
        "yoy_pct": "N/A",
        "qoq_direction": "flat",
        "yoy_direction": "flat",
        "trend_labels": [],
        "trend_values": [],
        "industry_name_bea": "",
    }


def format_bea_replacements(
    industry_display_name: str, insights: dict
) -> dict[str, str]:
    """Map sector growth insights to {{BEA_*}} PPTX placeholder keys."""
    yoy = insights.get("yoy_pct", "N/A")
    direction = insights.get("yoy_direction", "flat")

    if yoy != "N/A":
        if direction == "up":
            trend_label = f"Sector expanding {yoy} YoY — favorable market conditions"
        elif direction == "down":
            trend_label = (
                f"Sector contracting {yoy} YoY — challenging market environment"
            )
        else:
            trend_label = f"Sector stable {yoy} YoY — steady market conditions"
    else:
        trend_label = "Sector trend data unavailable"

    def clean(val):
        return "" if val == "N/A" else val

    return {
        "{{BEA_INDUSTRY}}": industry_display_name,
        "{{BEA_LATEST_VALUE}}": clean(insights.get("latest_value", "N/A")),
        "{{BEA_LATEST_PERIOD}}": clean(insights.get("latest_period", "N/A")),
        "{{BEA_QOQ_GROWTH}}": clean(insights.get("qoq_pct", "N/A")),
        "{{BEA_YOY_GROWTH}}": clean(insights.get("yoy_pct", "N/A")),
        "{{BEA_TREND_LABEL}}": trend_label if yoy != "N/A" else "",
    }


def build_empty_bea_replacements() -> dict[str, str]:
    """Return all BEA placeholder keys mapped to empty strings."""
    return {
        "{{BEA_INDUSTRY}}": "",
        "{{BEA_LATEST_VALUE}}": "",
        "{{BEA_LATEST_PERIOD}}": "",
        "{{BEA_QOQ_GROWTH}}": "",
        "{{BEA_YOY_GROWTH}}": "",
        "{{BEA_TREND_LABEL}}": "",
    }
