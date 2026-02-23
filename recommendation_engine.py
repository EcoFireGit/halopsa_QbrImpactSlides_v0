"""
recommendation_engine.py
Uses Anthropic Claude to generate strategic QBR recommendations
from aggregated ticket metrics and raw ticket summaries.
"""

import os
import json
import anthropic

def generate_recommendations(
    client_name: str,
    review_period: str,
    metrics: dict,
    ticket_summaries: list[str],
    num_recommendations: int = 3,
    anthropic_api_key: str = None
) -> list[dict]:
    """
    Calls Claude to generate strategic QBR recommendations.

    Args:
        client_name:        Name of the MSP's client.
        review_period:      The QBR period (e.g., "Q1 2026").
        metrics:            Dict of computed metrics from calculate_metrics().
        ticket_summaries:   List of ticket summary strings (already sampled).
        num_recommendations: Number of recommendations to generate (1–10).
        anthropic_api_key:  Anthropic API key. Falls back to env var if not provided.

    Returns:
        A list of dicts, each with 'title' and 'rationale' keys.
        e.g. [{"title": "Implement SSO", "rationale": "5 tickets this quarter ..."}]
    """
    api_key = anthropic_api_key.strip() if anthropic_api_key else os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Anthropic API key is missing. Please enter it in the sidebar.")
    client = anthropic.Anthropic(api_key=api_key)

    # ── Build the prompt ──────────────────────────────────────────────
    system_prompt = """You are a senior IT consultant and customer success strategist 
specializing in Managed Service Providers (MSPs). 
Your role is to analyze IT support data for a client and generate strategic, 
actionable recommendations that demonstrate the MSP's value and help the client 
improve their IT posture.

Your recommendations must:
1. Be a MIX of data-driven insights (grounded in the specific ticket data provided) 
   AND general IT best practice recommendations relevant to the client's situation.
2. Be written in plain, executive-friendly language — no jargon.
3. Each have a SHORT TITLE (5 words or fewer) and a 1-2 sentence RATIONALE.
4. Be returned as a valid JSON array ONLY — no preamble, no explanation outside JSON.

Output format:
[
  {
    "title": "Short Action Title",
    "rationale": "1-2 sentences explaining why this matters and what action to take."
  }
]"""

    # Format metrics into readable text for the prompt
    metrics_text = "\n".join([
        f"- Total Tickets: {metrics.get('{{TICKET_COUNT}}', 'N/A')}",
        f"- Same-Day Resolution Rate: {metrics.get('{{SAME_DAY_RATE}}', 'N/A')}%",
        f"- Average First Response Time: {metrics.get('{{AVG_FIRST_RESPONSE}}', 'N/A')}",
        f"- Critical Issue Resolution Time: {metrics.get('{{CRITICAL_RES_TIME}}', 'N/A')}",
        f"- Proactive Work: {metrics.get('{{PROACTIVE_PERCENT}}', 'N/A')}%",
        f"- Reactive Work: {metrics.get('{{REACTIVE_PERCENT}}', 'N/A')}%",
    ])

    # Format ticket summaries as a numbered list
    summaries_text = "\n".join(
        [f"{i+1}. {s}" for i, s in enumerate(ticket_summaries) if s and s.strip()]
    )

    user_prompt = f"""Please generate exactly {num_recommendations} strategic recommendations 
for the following MSP client QBR.

CLIENT: {client_name}
REVIEW PERIOD: {review_period}

--- AGGREGATED METRICS ---
{metrics_text}

--- SAMPLE TICKET SUMMARIES ({len(ticket_summaries)} tickets sampled) ---
{summaries_text}

Generate exactly {num_recommendations} recommendations as a JSON array.
Mix data-driven insights from the ticket summaries with general IT best practices.
"""

    # ── Call Claude ───────────────────────────────────────────────────
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    raw_text = response.content[0].text.strip()

    # ── Parse JSON response ───────────────────────────────────────────
    # Strip markdown code fences if Claude wraps in ```json ... ```
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    recommendations = json.loads(raw_text)

    # Validate structure
    validated = []
    for rec in recommendations:
        if isinstance(rec, dict) and "title" in rec and "rationale" in rec:
            validated.append({
                "title": str(rec["title"]).strip(),
                "rationale": str(rec["rationale"]).strip()
            })

    return validated
