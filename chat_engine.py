"""
chat_engine.py
Intent parsing, conversation state management, and response generation
for the chat-driven QBR interface.
"""

import json
import os
import re
from datetime import date, timedelta
from enum import Enum


class Intent(Enum):
    GENERATE_QBR = "generate_qbr"
    LIST_CLIENTS = "list_clients"
    SHOW_HEALTH_SCORE = "show_health_score"
    SET_AI_SETTINGS = "set_ai_settings"
    SET_CLIENT_PROFILE = "set_client_profile"
    SET_INDUSTRY = "set_industry"
    SHOW_LAST_QBR = "show_last_qbr"
    HELP = "help"
    UNKNOWN = "unknown"


# ── Regex-based intent detection ─────────────────────────────────────

_INTENT_PATTERNS = [
    (
        Intent.GENERATE_QBR,
        re.compile(
            r"generate.*qbr|create.*qbr|qbr\s+for|make.*qbr|build.*qbr|run.*qbr",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.LIST_CLIENTS,
        re.compile(
            r"list.*clients?|show.*clients?|all\s+clients?|which\s+clients?|what\s+clients?",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.SHOW_HEALTH_SCORE,
        re.compile(
            r"health\s*score|score\s+for",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.SET_AI_SETTINGS,
        re.compile(
            r"(enable|disable|turn\s+on|turn\s+off).*\bai\b"
            r"|set.*rec|recommendations?\s*\d+"
            r"|\d+\s*rec|\bnum.*rec|\bsample\s*size",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.SET_CLIENT_PROFILE,
        re.compile(
            r"employees?|hourly\s*rate|employee\s*count|workforce|headcount",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.SET_INDUSTRY,
        re.compile(
            r"\bindustry\b|\bsector\b",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.SHOW_LAST_QBR,
        re.compile(
            r"last\s+qbr|previous\s+qbr|recent\s+qbr",
            re.IGNORECASE,
        ),
    ),
    (
        Intent.HELP,
        re.compile(
            r"\bhelp\b|what\s+can\s+you|how\s+do\s+i|capabilities|commands",
            re.IGNORECASE,
        ),
    ),
]


def parse_intent_regex(message: str) -> tuple[Intent, dict]:
    """Try to match message against regex patterns. Returns (intent, extracted_params)."""
    for intent, pattern in _INTENT_PATTERNS:
        if pattern.search(message):
            params = _extract_params_regex(message, intent)
            return intent, params
    return Intent.UNKNOWN, {}


def _extract_params_regex(message: str, intent: Intent) -> dict:
    """Extract parameters from message based on intent using regex."""
    params = {}

    if intent == Intent.GENERATE_QBR:
        # Try to extract client name: "for <client>" or "qbr <client>"
        client_match = re.search(
            r"(?:for|qbr)\s+(.+?)(?:\s+for\s+|\s+from\s+|\s+in\s+|\s+last\s+|\s+q[1-4]|$)",
            message,
            re.IGNORECASE,
        )
        if client_match:
            params["client_name"] = client_match.group(1).strip().strip("\"'")

        # Try to extract date range
        date_range = parse_date_expression(message)
        if date_range:
            params["start_date"] = date_range[0]
            params["end_date"] = date_range[1]

    elif intent == Intent.SET_AI_SETTINGS:
        # Check enable/disable
        if re.search(r"(enable|turn\s+on).*\bai\b", message, re.IGNORECASE):
            params["use_ai"] = True
        elif re.search(r"(disable|turn\s+off).*\bai\b", message, re.IGNORECASE):
            params["use_ai"] = False

        # Extract number of recommendations
        rec_match = re.search(r"(\d+)\s*rec", message, re.IGNORECASE)
        if rec_match:
            params["num_recs"] = int(rec_match.group(1))

        # Extract sample size
        sample_match = re.search(
            r"sample\s*size\s*(?:of|to|=)?\s*(\d+)", message, re.IGNORECASE
        )
        if sample_match:
            params["sample_size"] = int(sample_match.group(1))

    elif intent == Intent.SET_CLIENT_PROFILE:
        emp_match = re.search(r"(\d+)\s*employees?", message, re.IGNORECASE)
        if emp_match:
            params["employee_count"] = int(emp_match.group(1))

        rate_match = re.search(
            r"\$?\s*(\d+(?:\.\d+)?)\s*(?:/\s*hr|per\s*hour|hourly)",
            message,
            re.IGNORECASE,
        )
        if rate_match:
            params["avg_hourly_rate"] = float(rate_match.group(1))

    elif intent in (Intent.SHOW_HEALTH_SCORE, Intent.SHOW_LAST_QBR):
        client_match = re.search(
            r"(?:for|of)\s+(.+?)(?:\s*$|\s*\?)", message, re.IGNORECASE
        )
        if client_match:
            params["client_name"] = client_match.group(1).strip().strip("\"'")

    return params


# ── Date parsing ─────────────────────────────────────────────────────

_MONTH_NAMES = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

_QUARTER_MONTHS = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}


def parse_date_expression(text: str) -> tuple[date, date] | None:
    """Parse natural language date references into (start_date, end_date)."""
    text_lower = text.lower()

    # "last quarter" / "previous quarter"
    if re.search(r"last\s+quarter|previous\s+quarter|prior\s+quarter", text_lower):
        today = date.today()
        current_q = (today.month - 1) // 3 + 1
        if current_q == 1:
            return date(today.year - 1, 10, 1), date(today.year - 1, 12, 31)
        start_month, end_month = _QUARTER_MONTHS[current_q - 1]
        return (
            date(today.year, start_month, 1),
            _last_day_of_month(today.year, end_month),
        )

    # "this quarter"
    if re.search(r"this\s+quarter|current\s+quarter", text_lower):
        today = date.today()
        current_q = (today.month - 1) // 3 + 1
        start_month, end_month = _QUARTER_MONTHS[current_q]
        return (
            date(today.year, start_month, 1),
            _last_day_of_month(today.year, end_month),
        )

    # "Q1 2025" / "q4 2025"
    q_match = re.search(r"q([1-4])\s*(\d{4})", text_lower)
    if q_match:
        q_num = int(q_match.group(1))
        year = int(q_match.group(2))
        start_month, end_month = _QUARTER_MONTHS[q_num]
        return (
            date(year, start_month, 1),
            _last_day_of_month(year, end_month),
        )

    # "past N months" / "last N months"
    months_match = re.search(r"(?:past|last)\s+(\d+)\s+months?", text_lower)
    if months_match:
        n = int(months_match.group(1))
        today = date.today()
        start = today - timedelta(days=n * 30)
        return start, today

    # "past N days" / "last N days"
    days_match = re.search(r"(?:past|last)\s+(\d+)\s+days?", text_lower)
    if days_match:
        n = int(days_match.group(1))
        today = date.today()
        return today - timedelta(days=n), today

    # "January to March 2026" / "Jan - Mar 2026"
    range_match = re.search(r"(\w+)\s+(?:to|through|-)\s+(\w+)\s+(\d{4})", text_lower)
    if range_match:
        start_month_name = range_match.group(1)
        end_month_name = range_match.group(2)
        year = int(range_match.group(3))
        sm = _MONTH_NAMES.get(start_month_name)
        em = _MONTH_NAMES.get(end_month_name)
        if sm and em:
            return date(year, sm, 1), _last_day_of_month(year, em)

    return None


def _last_day_of_month(year: int, month: int) -> date:
    """Return the last day of the given month."""
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


# ── Client resolution ────────────────────────────────────────────────


def resolve_client(name: str, clients: list[dict]) -> list[dict]:
    """Fuzzy-match client name. Returns list of matching client dicts."""
    if not name or not clients:
        return []
    name_lower = name.lower().strip()

    # Exact match first
    for c in clients:
        if c["name"].lower() == name_lower:
            return [c]

    # Substring match
    matches = [c for c in clients if name_lower in c["name"].lower()]
    if matches:
        return matches

    # Word-based match (any word matches)
    words = name_lower.split()
    matches = [c for c in clients if any(w in c["name"].lower() for w in words)]
    return matches


# ── Missing field detection ──────────────────────────────────────────


def get_missing_fields(state: dict) -> str | None:
    """Check what info is still needed for QBR generation. Returns a follow-up question or None."""
    if not state.get("client_id"):
        return "Which client would you like to generate the QBR for?"

    if not state.get("start_date") or not state.get("end_date"):
        return (
            "What date range should the QBR cover? "
            "For example: 'last quarter', 'Q4 2025', or 'January to March 2026'."
        )

    if not state.get("msp_contact"):
        return (
            "What is the MSP account manager contact info? "
            "For example: 'Jane Doe | jdoe@yourmsp.com | (555) 123-4567'"
        )

    return None


def get_optional_prompts(state: dict, has_bea_key: bool) -> str | None:
    """Check for optional but recommended fields. Returns a prompt or None."""
    if state.get("employee_count") is None or state.get("employee_count") == 0:
        if not state.get("asked_employee_count"):
            return (
                "How many employees does this client have? "
                "This helps calculate business impact. "
                "(You can type 'skip' to proceed without it.)"
            )

    if has_bea_key and not state.get("industry_name"):
        if not state.get("asked_industry"):
            return (
                "What industry is this client in? This adds economic context to the QBR. "
                "Options include: Healthcare, Finance, IT, Manufacturing, Retail, etc. "
                "(You can type 'skip' to proceed without it.)"
            )

    return None


# ── LLM intent parsing ──────────────────────────────────────────────


def parse_intent_llm(
    message: str,
    history: list[dict],
    state: dict,
    anthropic_api_key: str,
) -> tuple[Intent, dict]:
    """Use Claude to parse intent and extract parameters from ambiguous messages."""
    import anthropic

    api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return Intent.UNKNOWN, {}

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = """You are an intent parser for an MSP QBR Generator chatbot.
Given a user message and conversation context, extract the intent and parameters.

Valid intents: generate_qbr, list_clients, show_health_score, set_ai_settings,
set_client_profile, set_industry, show_last_qbr, help, unknown

Return ONLY valid JSON:
{
  "intent": "<intent_name>",
  "params": {
    "client_name": "<string or null>",
    "date_expression": "<string or null, e.g. 'Q4 2025', 'last quarter'>",
    "msp_contact": "<string or null>",
    "use_ai": "<boolean or null>",
    "num_recs": "<integer or null>",
    "sample_size": "<integer or null>",
    "employee_count": "<integer or null>",
    "avg_hourly_rate": "<float or null>",
    "industry_name": "<string or null>",
    "is_skip": "<boolean, true if user wants to skip current question>"
  }
}

Context about current conversation state:
""" + json.dumps(state, default=str)

    # Build messages from history (last 10)
    messages = []
    for msg in history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=system_prompt,
            messages=messages,
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)
        intent_str = parsed.get("intent", "unknown")
        params = parsed.get("params", {})
        # Remove null values
        params = {k: v for k, v in params.items() if v is not None}

        # Parse date expression if present
        if "date_expression" in params:
            date_range = parse_date_expression(params["date_expression"])
            if date_range:
                params["start_date"] = date_range[0]
                params["end_date"] = date_range[1]
            del params["date_expression"]

        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.UNKNOWN

        return intent, params

    except Exception:
        return Intent.UNKNOWN, {}


# ── Response formatting ──────────────────────────────────────────────


def format_help_message() -> str:
    """Return help text listing all capabilities."""
    return """Here's what I can help you with:

**Generate a QBR**
- "Generate a QBR for Acme Corp for last quarter"
- "Create QBR for Beta Industries Q4 2025"

**View clients**
- "List all clients"
- "Show clients"

**Check health score**
- "What's the health score for Acme Corp?"

**Configure AI recommendations**
- "Enable AI with 5 recommendations"
- "Disable AI recommendations"
- "Set sample size to 200"

**Set client profile**
- "Acme has 150 employees at $75/hr"
- "Set employee count to 200"

**Set industry**
- "Acme is in healthcare"
- "Set industry to Finance"

**Other**
- "Show last QBR" - download the most recently generated report"""


def format_client_list(clients: list[dict]) -> str:
    """Format client list for chat display."""
    if not clients:
        return "No clients found. Make sure you're connected to HaloPSA."
    lines = [f"**{len(clients)} clients available:**\n"]
    for i, c in enumerate(clients, 1):
        lines.append(f"{i}. {c['name']}")
    return "\n".join(lines)


def format_disambiguation(matches: list[dict]) -> str:
    """Format disambiguation prompt for multiple client matches."""
    lines = ["I found multiple clients matching that name. Which one did you mean?\n"]
    for i, c in enumerate(matches, 1):
        lines.append(f"{i}. {c['name']}")
    lines.append("\nPlease reply with the number or the full client name.")
    return "\n".join(lines)


def resolve_disambiguation(message: str, candidates: list[dict]) -> dict | None:
    """Try to resolve a disambiguation response (number or name)."""
    msg = message.strip()
    # Try number
    try:
        idx = int(msg) - 1
        if 0 <= idx < len(candidates):
            return candidates[idx]
    except ValueError:
        pass

    # Try name match
    for c in candidates:
        if msg.lower() in c["name"].lower():
            return c

    return None


# ── Industry matching ────────────────────────────────────────────────


def match_industry(text: str) -> str | None:
    """Match free-text industry name to a known BEA industry sector name."""
    from bea_insights import INDUSTRY_SECTORS

    text_lower = text.lower().strip()

    # Direct match
    for name in INDUSTRY_SECTORS:
        if text_lower == name.lower():
            return name

    # Keyword match
    _INDUSTRY_KEYWORDS = {
        "it": "Information Technology & Data Services",
        "tech": "Information Technology & Data Services",
        "technology": "Information Technology & Data Services",
        "software": "Information Technology & Data Services",
        "data": "Information Technology & Data Services",
        "healthcare": "Healthcare & Social Assistance",
        "health": "Healthcare & Social Assistance",
        "medical": "Healthcare & Social Assistance",
        "hospital": "Healthcare & Social Assistance",
        "finance": "Finance & Insurance",
        "financial": "Finance & Insurance",
        "banking": "Finance & Insurance",
        "insurance": "Finance & Insurance",
        "professional": "Professional, Scientific & Tech Svcs",
        "consulting": "Professional, Scientific & Tech Svcs",
        "legal": "Professional, Scientific & Tech Svcs",
        "manufacturing": "Manufacturing",
        "retail": "Retail Trade",
        "real estate": "Real Estate & Rental",
        "construction": "Construction",
        "education": "Educational Services",
        "school": "Educational Services",
        "university": "Educational Services",
        "hotel": "Accommodation & Food Services",
        "restaurant": "Accommodation & Food Services",
        "food": "Accommodation & Food Services",
        "hospitality": "Accommodation & Food Services",
        "transport": "Transportation & Warehousing",
        "logistics": "Transportation & Warehousing",
        "shipping": "Transportation & Warehousing",
        "wholesale": "Wholesale Trade",
        "management": "Management of Companies",
        "utilities": "Utilities",
        "energy": "Utilities",
        "agriculture": "Agriculture, Forestry & Fishing",
        "farming": "Agriculture, Forestry & Fishing",
    }

    for keyword, industry in _INDUSTRY_KEYWORDS.items():
        if keyword in text_lower:
            return industry

    return None
