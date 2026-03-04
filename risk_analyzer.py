"""
risk_analyzer.py
Surface the most alarming ticket patterns as named risk flags.
"""

from collections import Counter

_STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "and",
    "or",
    "with",
    "user",
    "issue",
    "ticket",
    "request",
    "please",
    "help",
    "not",
    "working",
    "unable",
    "error",
    "can",
    "cannot",
    "no",
    "new",
    "re",
    "",
}


def _detect_open_critical(tickets: list) -> list[dict]:
    """Flag if any priority_id==1 ticket has not been closed."""
    open_critical = [
        t
        for t in tickets
        if t.get("priority_id") == 1 and t.get("hasbeenclosed") is not True
    ]
    if not open_critical:
        return []
    return [
        {
            "flag": f"Open Critical Tickets: {len(open_critical)} critical ticket(s) remain unresolved",
            "severity": "high",
            "detail": (
                f"{len(open_critical)} priority-1 ticket(s) are still open. "
                "These represent active business-critical risks."
            ),
        }
    ]


def _detect_critical_volume(tickets: list) -> list[dict]:
    """Flag if critical ticket count exceeds threshold."""
    critical_count = sum(1 for t in tickets if t.get("priority_id") == 1)
    if critical_count <= 3:
        return []
    severity = "high" if critical_count > 6 else "medium"
    return [
        {
            "flag": f"Critical Ticket Volume: {critical_count} critical incidents this quarter",
            "severity": severity,
            "detail": (
                f"{critical_count} priority-1 tickets were logged. "
                "This volume suggests systemic infrastructure issues."
            ),
        }
    ]


def _detect_recurring_issues(tickets: list) -> list[dict]:
    """Flag recurring keywords from ticket summaries."""
    token_counts: Counter = Counter()
    for t in tickets:
        summary = t.get("summary", "") or ""
        tokens = summary.lower().split()
        first_non_stop = None
        for tok in tokens:
            cleaned = tok.strip(".,;:!?()[]{}\"'")
            if cleaned and cleaned not in _STOPWORDS:
                first_non_stop = cleaned
                break
        if first_non_stop:
            token_counts[first_non_stop] += 1

    flags = []
    for token, count in token_counts.most_common():
        if count < 3:
            break
        severity = "high" if count >= 6 else "medium"
        flags.append(
            {
                "flag": f'Recurring Issue — "{token}": {count} tickets this quarter',
                "severity": severity,
                "detail": (
                    f'The keyword "{token}" appeared in {count} ticket summaries, '
                    "indicating a persistent problem pattern."
                ),
            }
        )
        if len(flags) >= 3:
            break
    return flags


def analyze_risks(tickets: list) -> list[dict]:
    """
    Returns up to 5 risk flag dicts: {flag, severity, detail}.
    Ordered: open critical first, then volume, then recurring.
    """
    if not tickets:
        return []

    flags = []
    flags.extend(_detect_open_critical(tickets))
    flags.extend(_detect_critical_volume(tickets))
    flags.extend(_detect_recurring_issues(tickets))
    return flags[:5]


def format_risk_replacements(risk_flags: list[dict]) -> dict:
    """Map top 3 risk flags to PPTX placeholders."""
    replacements = {}
    for i in range(3):
        key = f"{{{{TOP_RISK_{i + 1}}}}}"
        if i < len(risk_flags):
            replacements[key] = risk_flags[i]["flag"]
        else:
            replacements[key] = ""
    return replacements


def build_empty_risk_replacements() -> dict:
    """Return empty strings for all three risk placeholders."""
    return {
        "{{TOP_RISK_1}}": "",
        "{{TOP_RISK_2}}": "",
        "{{TOP_RISK_3}}": "",
    }
