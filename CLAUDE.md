# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

MSP Quarterly Business Review (QBR) generator. Connects to a HaloPSA instance, fetches ticket data for a client, computes business impact metrics, optionally generates AI-powered recommendations via Claude API, and outputs a branded PowerPoint deck.

## Commands

```bash
# Run the Streamlit web app (primary interface)
streamlit run app.py

# Regenerate the master PowerPoint template (creates Master_QBR_Template.pptx)
python create_qbr_template.py

# Test HaloPSA API connectivity
python main.py

# Generate a QBR from mock data (standalone test)
python generate_client_qbr.py

# Install dependencies
pip install -r requirements.txt
```

## Architecture

The pipeline flows: **HaloPSA API → Metrics Calculation → LLM Recommendations → PPTX Template Population → Download**

- **`app.py`** — Streamlit UI. Chat-driven interface with 50/50 split layout: chat panel (left) and results dashboard (right, hidden until first QBR). No sidebar (hidden via CSS). Credentials (HaloPSA, Anthropic API key, BEA API key) managed via `@st.dialog("Settings")` opened by gear icon. AI settings (toggle, num_recs, sample_size), client profile, industry, and MSP contact are configured via natural language chat. Auto-connects on launch when `.env` credentials exist. Chat supports: QBR generation ("Generate QBR for Acme for last quarter"), listing clients, checking health scores, configuring AI settings, setting client profiles, setting industry. Intent parsed via regex pre-filter then Claude Haiku fallback. Multi-turn follow-up questions for missing fields. Welcome screen with example prompt buttons. Results panel shows: download button, 4-column metrics row (Health Score badge, Same-Day Resolution, Avg First Response, Critical Resolution Time), Business Impact card, Risk Flags card, BEA panel. Collapsible via "Hide Results" button. Both panels independently scrollable via CSS. No emojis anywhere in the UI.
- **`chat_engine.py`** — Intent parsing, conversation state management, and response generation. `Intent` enum defines 8 intents (GENERATE_QBR, LIST_CLIENTS, SHOW_HEALTH_SCORE, SET_AI_SETTINGS, SET_CLIENT_PROFILE, SET_INDUSTRY, SHOW_LAST_QBR, HELP). `parse_intent_regex()` does lightweight pattern matching; `parse_intent_llm()` falls back to Claude Haiku for ambiguous messages. `parse_date_expression()` handles natural language dates ("last quarter", "Q4 2025", "past 6 months"). `resolve_client()` does fuzzy substring matching. `get_missing_fields()` / `get_optional_prompts()` drive the multi-turn follow-up flow. `match_industry()` maps free-text to BEA sector names.
- **`chat_preferences.py`** — Cross-session persistence for AI settings (use_ai, num_recs, sample_size), per-client industry sector, and MSP contact info. Stored in `chat_preferences.json` (gitignored). Atomic writes via `os.replace()`. Key functions: `get_ai_settings()`, `update_ai_settings()`, `get_client_industry()`, `set_client_industry()`, `get_msp_contact()`, `set_msp_contact()`.
- **`halo_client.py`** — `HaloClient` class. OAuth2 client credentials flow against HaloPSA REST API (`/auth/token`, `/api/Tickets`, `/api/Client`). Reads credentials from `.env` via `python-dotenv`.
- **`generate_client_qbr.py`** — Core engine. `calculate_metrics()` computes 4 KPIs from raw tickets (proactive/reactive split, same-day resolution rate, critical resolution time, avg first response). `calculate_health_score(metrics_data)` derives a 0–100 integer from those 4 KPIs (25 pts each). `generate_qbr()` opens a template PPTX, replaces `{{PLACEHOLDER}}` text in shapes, and inserts a matplotlib chart image in place of `{{CHART_PLACEHOLDER}}`. `build_recommendation_replacements()` maps recommendation dicts to `{{REC_N_TITLE}}`/`{{REC_N_RATIONALE}}` keys. `generate_qbr()` accepts a `num_recs` parameter; `_remove_unused_rec_slots(slide, num_recs)` deletes unused recommendation shapes (circles, numbers, titles, rationales) for slots beyond num_recs before populating the slide. `_estimate_text_height_in()` and `_reposition_rec_slots()` restack recommendation shapes at runtime based on actual post-replacement text height.
- **`create_qbr_template.py`** — Builds `Master_QBR_Template.pptx` programmatically using `python-pptx`. Defines slide structure with placeholder text (e.g., `{{CLIENT_NAME}}`, `{{SAME_DAY_RATE}}`). Run this to regenerate the template if slides need restructuring. `add_recommendations()` generates all 10 recommendation slots with named shapes (`rec_{i}_circle/num/title/rationale`); unused slots are removed at runtime by `generate_client_qbr.py`. Executive Summary slide contains impact/risk text boxes (`{{PRODUCTIVITY_HOURS_LOST}}`, `{{ESTIMATED_COST}}`, `{{RISK_STATEMENT}}`); BEA box is positioned below these. Recommendations slide has a Risk Spotlight header with `{{TOP_RISK_1}}`, `{{TOP_RISK_2}}`, `{{TOP_RISK_3}}` placeholders.
- **`recommendation_engine.py`** — Calls Anthropic Claude (`claude-sonnet-4-5-20250929`) with ticket metrics + sampled summaries to produce structured JSON recommendations. Accepts optional `employee_count`, `avg_hourly_rate`, `business_impact` (dict), and `risk_flags` (list) params. When provided, the prompt includes a CLIENT PROFILE section and a RISK FLAGS section. Each recommendation is required to: (a) name the specific risk with data evidence, (b) state the cost of inaction in dollar or time terms, (c) include ROI framing.
- **`client_profiles.py`** — JSON persistence for per-client employee count and average hourly rate. Stored in `client_profiles.json` (gitignored). Key functions: `get_profile(client_id)` returns profile dict or defaults (`employee_count=0, avg_hourly_rate=50`); `upsert_profile(client_id, employee_count, avg_hourly_rate)` saves atomically via `os.replace()` on a temp file; `load_profiles()` / `save_profiles(profiles)` for full dict access.
- **`business_impact.py`** — Computes productivity hours lost and estimated dollar cost from critical tickets and client profile. `calculate_business_impact(metrics_data, tickets, employee_count, avg_hourly_rate)` returns dict: `critical_ticket_count`, `avg_critical_res_hours`, `employees_affected` (employee_count × 0.1), `productivity_hours_lost` (critical_ticket_count × avg_critical_res_hours × employees_affected), `estimated_dollar_cost` (productivity_hours_lost × avg_hourly_rate), `risk_statement`, `has_data` (True when employee_count > 0). `format_impact_replacements(impact)` maps to `{{PRODUCTIVITY_HOURS_LOST}}`, `{{ESTIMATED_COST}}`, `{{RISK_STATEMENT}}`. `build_empty_impact_replacements()` fills empty strings for all three.
- **`risk_analyzer.py`** — Detects alarming ticket patterns as named risk flags. `analyze_risks(tickets)` returns up to 5 flag dicts (`flag`, `severity`, `detail`) ordered: open critical first, then critical volume (>3 tickets), then recurring keywords (≥3 occurrences in ticket summaries, up to 3). Severity is `high`/`medium`. `format_risk_replacements(risk_flags)` maps top 3 to `{{TOP_RISK_1}}` through `{{TOP_RISK_3}}`. `build_empty_risk_replacements()` fills empty strings.
- **`bea_client.py`** — Fetches GDP-by-Industry data from the BEA (Bureau of Economic Analysis) REST API. Returns recent quarterly growth metrics for a selected industry sector. Reads `BEA_API_KEY` from `.env`.
- **`bea_insights.py`** — Converts raw BEA API rows into formatted metrics and `{{BEA_*}}` PPTX placeholder values. Defines `INDUSTRY_SECTORS` mapping (display name → BEA industry code). Notable non-NAICS codes: `31G` (Manufacturing), `44RT` (Retail Trade), `48TW` (Transportation & Warehousing).
- **`qbr_data_replacer.py`** — Standalone placeholder replacer (earlier iteration). `replace_text_in_shape()` handles text frames, tables, and grouped shapes. Not used by the main pipeline (superseded by `generate_client_qbr.py`'s replacer).
- **`.streamlit/config.toml`** — Brand theme: indigo primary (`#242E65`), white background, light secondary (`#F8F9FC`), dark text (`#1A1A2E`), sans serif font.

## Key Conventions

- **Brand colors**: Indigo `#242E65` (primary — headers, buttons, chart colors, PPTX template) and halloween orange `#F05523` (accent — dividers, metric card borders, download button border). Applied via `.streamlit/config.toml` for native widgets and custom CSS in `app.py` for additional styling.
- **No emojis**: The UI deliberately avoids all emoji characters. Do not add emojis to user-facing text.
- **No sidebar**: The sidebar is hidden via CSS (`display: none`). All settings live in a `@st.dialog` opened by the gear icon.
- **Settings dialog**: Opened via `st.button(icon=":material/settings:")` in the page header. Contains HaloPSA credentials and API keys only (Anthropic, BEA). AI settings (toggle, sliders) are configured via chat commands. "Save" persists to session state; "Connect to HaloPSA" authenticates.
- **Chat interface**: 50/50 split layout (chat left, results right). Results panel hidden until first QBR generation. Both panels independently scrollable. Chat uses `st.chat_input` and `st.chat_message`. Intent parsing: regex pre-filter for common patterns, Claude Haiku fallback for ambiguous messages. Conversation history maintained in `st.session_state.chat_history`. Multi-turn follow-up questions for missing QBR fields (client, date range, MSP contact, employee count, industry).
- **Chat preferences persistence**: AI settings, per-client industry sector, and MSP contact are stored in `chat_preferences.json` (gitignored). Loaded automatically when generating QBRs to avoid re-asking.
- **Auto-connect**: On first load, if `.env` has `HALO_HOST`, `CLIENT_ID`, and `CLIENT_SECRET`, the app auto-authenticates. Controlled by `auto_connect_attempted` flag to prevent retry loops.
- **Placeholder format**: All PPTX placeholders use `{{DOUBLE_BRACES}}` (e.g., `{{CLIENT_NAME}}`, `{{TICKET_COUNT}}`). Recommendation slots are `{{REC_1_TITLE}}` through `{{REC_10_TITLE}}` with matching `_RATIONALE` keys. BEA economic context placeholders on the Executive Summary slide: `{{BEA_INDUSTRY}}`, `{{BEA_LATEST_VALUE}}`, `{{BEA_LATEST_PERIOD}}`, `{{BEA_QOQ_GROWTH}}`, `{{BEA_YOY_GROWTH}}`, `{{BEA_TREND_LABEL}}`. Business impact placeholders: `{{PRODUCTIVITY_HOURS_LOST}}`, `{{ESTIMATED_COST}}`, `{{RISK_STATEMENT}}` (Executive Summary). Risk Spotlight placeholders: `{{TOP_RISK_1}}`, `{{TOP_RISK_2}}`, `{{TOP_RISK_3}}` (Recommendations slide).
- **HaloPSA ticket type IDs**: Proactive types are `[30, 40, 100]`; all others are reactive. Priority ID `1` = Critical.
- **Template file**: The pipeline expects `Master_QBR_Template.pptx` in the project root. Only this file is tracked in git (all other `.pptx` files are gitignored).
- **Environment variables**: `HALO_HOST`, `CLIENT_ID`, `CLIENT_SECRET`, `HALO_SCOPE`, `ANTHROPIC_API_KEY`, `BEA_API_KEY` — loaded from `.env` (gitignored).
- **BEA industry persistence**: Per-client industry sector persisted in `chat_preferences.json` via `set_client_industry()`. Loaded automatically during QBR generation.
- **Dynamic recommendation slots**: `Master_QBR_Template.pptx` contains all 10 recommendation slots. At runtime, `_remove_unused_rec_slots()` in `generate_client_qbr.py` deletes shapes for slots N > num_recs (configurable via chat: "set 5 recommendations").
- **Ticket sampling status message**: When AI is enabled and ticket count exceeds `sample_size`, the status message clarifies how many will be sampled: "Retrieved N tickets (M will be sampled for AI analysis)."
- **Pre-commit hook**: `.pre-commit-config.yaml` uses `ruff` (v0.3.0) for linting (`--fix`) and formatting. Run `pre-commit install` after cloning.
- **Client Health Score**: Computed by `calculate_health_score()` in `generate_client_qbr.py` immediately after `calculate_metrics()`. Each of the 4 KPIs contributes 0–25 pts: proactive % (linear), same-day rate (linear), critical resolution time (≤4h=25, ≥24h=0, linear between), avg first response (≤30min=25, ≥240min=0, linear between; N/A=12.5 neutral). Thresholds: ≥80 green "Excellent", ≥50 yellow "Needs Attention", <50 red "At Risk". UI-only — no PPTX changes.
- **Client profile persistence**: Per-client employee count and avg hourly rate are stored in `client_profiles.json` (gitignored, in project root). Default fallback: `employee_count=0`, `avg_hourly_rate=50`. When `employee_count=0`, `has_data=False` and impact cards are not shown in the dashboard.
- **Business impact formula**: `employees_affected = employee_count × 0.1`; `productivity_hours_lost = critical_ticket_count × avg_critical_res_hours × employees_affected`; `estimated_dollar_cost = productivity_hours_lost × avg_hourly_rate`. Risk statement: "High risk" if critical_count > 3 and proactive_pct < 40; "Moderate risk" if critical_count > 0; else "Low risk".
- **Risk flag ordering**: `analyze_risks()` outputs flags in order: open critical tickets → critical volume → recurring keywords. Max 5 total; only top 3 are mapped to PPTX placeholders.
- **Test suite**: `tests/` contains 135 unit tests covering all core business logic modules (`generate_client_qbr`, `business_impact`, `risk_analyzer`, `bea_insights`, `client_profiles`, `recommendation_engine`). Run with `python -m pytest tests/ -v`. Note: `calculate_health_score()` uses Python 3 banker's rounding — `round(12.5)` returns `12`, not `13`.

## Interaction + Visual Verification Loop

When testing a feature:

1. Start dev server
2. Use Playwright MCP to navigate to the relevant page
3. Interact with the UI as a user would (fill forms, click buttons, etc.)
4. Take a screenshot after each meaningful state change
5. Visually inspect each screenshot
6. If something looks wrong or behaves unexpectedly, fix and repeat
