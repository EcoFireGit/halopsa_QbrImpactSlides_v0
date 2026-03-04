"""
business_impact.py
Convert ticket metrics + client profile into dollar/time/risk statements.
"""


def _parse_crit_res_hours(crit_res_str: str) -> float:
    """Parse metrics_data['{{CRITICAL_RES_TIME}}'] back to a float of hours."""
    s = crit_res_str.strip()
    if s == "N/A":
        return 0.0
    if s.startswith("<"):
        return 0.5
    try:
        return float(s.replace(" hours", "").replace(" hour", "").strip())
    except (ValueError, TypeError):
        return 0.0


def calculate_business_impact(
    metrics_data: dict,
    tickets: list,
    employee_count: int,
    avg_hourly_rate: float,
) -> dict:
    """
    Compute dollar/time/risk impact from ticket metrics and client profile.

    Returns a dict with:
        critical_ticket_count, avg_critical_res_hours, employees_affected,
        productivity_hours_lost, estimated_dollar_cost, risk_statement, has_data
    """
    critical_ticket_count = sum(1 for t in tickets if t.get("priority_id") == 1)

    avg_critical_res_hours = _parse_crit_res_hours(
        metrics_data.get("{{CRITICAL_RES_TIME}}", "N/A")
    )

    employees_affected = employee_count * 0.1
    productivity_hours_lost = (
        critical_ticket_count * avg_critical_res_hours * employees_affected
    )
    estimated_dollar_cost = productivity_hours_lost * avg_hourly_rate

    # Risk statement based on proactive_pct and critical_ticket_count
    try:
        proactive_pct = float(metrics_data.get("{{PROACTIVE_PERCENT}}", "0") or "0")
    except (ValueError, TypeError):
        proactive_pct = 0.0

    if critical_ticket_count > 3 and proactive_pct < 40:
        risk_statement = (
            f"High risk: {critical_ticket_count} critical incidents with only "
            f"{int(proactive_pct)}% proactive coverage indicates significant "
            f"exposure to business-disrupting outages."
        )
    elif critical_ticket_count > 0:
        risk_statement = (
            f"Moderate risk: {critical_ticket_count} critical incident(s) this "
            f"quarter. Each incident affected an estimated "
            f"{int(employees_affected)} employees."
        )
    else:
        risk_statement = (
            "Low risk: No critical incidents this quarter. "
            "Current proactive maintenance is keeping operations stable."
        )

    return {
        "critical_ticket_count": critical_ticket_count,
        "avg_critical_res_hours": avg_critical_res_hours,
        "employees_affected": employees_affected,
        "productivity_hours_lost": productivity_hours_lost,
        "estimated_dollar_cost": estimated_dollar_cost,
        "risk_statement": risk_statement,
        "has_data": employee_count > 0,
    }


def format_impact_replacements(impact: dict) -> dict:
    """Map impact dict to PPTX placeholder strings."""
    hours = impact["productivity_hours_lost"]
    cost = impact["estimated_dollar_cost"]
    return {
        "{{PRODUCTIVITY_HOURS_LOST}}": f"{hours:,.1f}" if hours > 0 else "0",
        "{{ESTIMATED_COST}}": f"${cost:,.0f}" if cost > 0 else "$0",
        "{{RISK_STATEMENT}}": impact["risk_statement"],
    }


def build_empty_impact_replacements() -> dict:
    """Return empty strings for all three impact placeholders."""
    return {
        "{{PRODUCTIVITY_HOURS_LOST}}": "",
        "{{ESTIMATED_COST}}": "",
        "{{RISK_STATEMENT}}": "",
    }
