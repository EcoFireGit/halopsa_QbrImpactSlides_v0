# halopsa_QbrImpactSlides_v0

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

- **`app.py`** — Single-page Streamlit app (sidebar hidden via CSS). All settings live in a `@st.dialog("Settings")` opened via a gear icon. Dialog contains HaloPSA credentials, AI toggle + sliders (num_recs, sample_size), and BEA API key. Auto-connects on launch when `.env` credentials exist (controlled by `auto_connect_attempted` flag). Main area uses collapsible `st.expander` sections for: (1a) Client & Date Range, (1b) Client Profile (employee count + avg hourly rate), Economic Context, MSP Contact Info, and Generate. After generation: download button, 4-column metrics row (Health Score badge, Same-Day %, Avg First Response, Critical Resolution Time), Business Impact card, Risk Flags card, and BEA panel. Metrics persist in `st.session_state.metrics_display` across reruns.
- **`halo_client.py`** — `HaloClient` class. OAuth2 client credentials flow against HaloPSA REST API (`/auth/token`, `/api/Tickets`, `/api/Client`). Reads credentials from `.env` via `python-dotenv`.
- **`generate_client_qbr.py`** — Core engine. `calculate_metrics()` computes 4 KPIs from raw tickets (proactive/reactive split, same-day resolution rate, critical resolution time, avg first response). `calculate_health_score(metrics_data)` derives a 0–100 integer from those 4 KPIs (25 pts each). `generate_qbr()` opens a template PPTX, replaces `{{PLACEHOLDER}}` text in shapes, and inserts a matplotlib chart image in place of `{{CHART_PLACEHOLDER}}`. Accepts a `num_recs` parameter. `build_recommendation_replacements()` maps recommendation dicts to `{{REC_N_TITLE}}`/`{{REC_N_RATIONALE}}` keys. `_remove_unused_rec_slots()` deletes template shapes for slots N > num_recs before populating the slide. `_estimate_text_height_in()` and `_reposition_rec_slots()` restack recommendation shapes at runtime based on actual post-replacement text height.
- **`create_qbr_template.py`** — Builds `Master_QBR_Template.pptx` programmatically using `python-pptx`. Defines slide structure with placeholder text (e.g., `{{CLIENT_NAME}}`, `{{SAME_DAY_RATE}}`). Executive Summary slide includes business impact placeholders (`{{PRODUCTIVITY_HOURS_LOST}}`, `{{ESTIMATED_COST}}`, `{{RISK_STATEMENT}}`) and BEA economic context boxes. Recommendations slide has a Risk Spotlight header with `{{TOP_RISK_1}}`–`{{TOP_RISK_3}}`. `add_recommendations()` generates all 10 slots with named shapes (`rec_{i}_circle/num/title/rationale`). Run this to regenerate the template if slides need restructuring.
- **`recommendation_engine.py`** — Calls Anthropic Claude (`claude-sonnet-4-5-20250929`) with ticket metrics + sampled summaries to produce structured JSON recommendations. Accepts optional `employee_count`, `avg_hourly_rate`, `business_impact` (dict), and `risk_flags` (list) params. When provided, injects a CLIENT PROFILE section and a RISK FLAGS section into the prompt. Each recommendation is required to name the specific risk with data evidence, state the cost of inaction in dollar or time terms, and include ROI framing.
- **`bea_client.py`** — Fetches GDP-by-Industry data from the BEA (Bureau of Economic Analysis) REST API. Returns recent quarterly growth metrics for a selected industry sector. Reads `BEA_API_KEY` from `.env`.
- **`bea_insights.py`** — Converts raw BEA API rows into formatted metrics and `{{BEA_*}}` PPTX placeholder values. `INDUSTRY_SECTORS` maps display names → BEA industry codes (including non-NAICS codes: `31G` for Manufacturing, `44RT` for Retail Trade, `48TW` for Transportation & Warehousing).
- **`client_profiles.py`** — JSON persistence for per-client employee count and avg hourly rate in `client_profiles.json` (gitignored). Key functions: `get_profile(client_id)` returns profile dict or defaults (`employee_count=0`, `avg_hourly_rate=50`); `upsert_profile(client_id, employee_count, avg_hourly_rate)` saves atomically via `os.replace()`.
- **`business_impact.py`** — `calculate_business_impact()` computes productivity hours lost and estimated dollar cost from critical tickets and client profile. `has_data=True` only when `employee_count > 0`. `format_impact_replacements()` maps results to `{{PRODUCTIVITY_HOURS_LOST}}`, `{{ESTIMATED_COST}}`, `{{RISK_STATEMENT}}`.
- **`risk_analyzer.py`** — `analyze_risks()` returns up to 5 flag dicts (`flag`, `severity`, `detail`) ordered: open critical tickets → critical volume (>3 tickets) → recurring keywords (≥3 occurrences). `format_risk_replacements()` maps top 3 to `{{TOP_RISK_1}}`–`{{TOP_RISK_3}}`.
- **`qbr_data_replacer.py`** — Standalone placeholder replacer (earlier iteration). `replace_text_in_shape()` handles text frames, tables, and grouped shapes. Not used by the main pipeline (superseded by `generate_client_qbr.py`'s replacer).

## Key Conventions

- **Brand colors**: Indigo `#242E65` (primary — headers, buttons, chart colors, PPTX template) and orange `#F05523` (accent — dividers, metric card borders, download button border). Applied via `.streamlit/config.toml` for native widgets and custom CSS in `app.py` for additional styling.
- **No emojis**: The UI deliberately avoids all emoji characters. Do not add emojis to user-facing text.
- **No sidebar**: Hidden via CSS (`display: none`). All settings live in a `@st.dialog` opened by the gear icon.
- **Auto-connect**: On first load, if `.env` has `HALO_HOST`, `CLIENT_ID`, and `CLIENT_SECRET`, the app auto-authenticates. Controlled by `auto_connect_attempted` flag to prevent retry loops.
- **Placeholder format**: All PPTX placeholders use `{{DOUBLE_BRACES}}` (e.g., `{{CLIENT_NAME}}`, `{{TICKET_COUNT}}`). Recommendation slots are `{{REC_1_TITLE}}` through `{{REC_10_TITLE}}` with matching `_RATIONALE` keys. Business impact placeholders: `{{PRODUCTIVITY_HOURS_LOST}}`, `{{ESTIMATED_COST}}`, `{{RISK_STATEMENT}}`. Risk Spotlight placeholders: `{{TOP_RISK_1}}`–`{{TOP_RISK_3}}`. BEA placeholders: `{{BEA_INDUSTRY}}`, `{{BEA_LATEST_VALUE}}`, `{{BEA_LATEST_PERIOD}}`, `{{BEA_QOQ_GROWTH}}`, `{{BEA_YOY_GROWTH}}`, `{{BEA_TREND_LABEL}}`.
- **HaloPSA ticket type IDs**: Proactive types are `[30, 40, 100]`; all others are reactive. Priority ID `1` = Critical.
- **Template file**: The pipeline expects `Master_QBR_Template.pptx` in the project root. Only this file is tracked in git (all other `.pptx` files are gitignored).
- **Environment variables**: `HALO_HOST`, `CLIENT_ID`, `CLIENT_SECRET`, `HALO_SCOPE`, `ANTHROPIC_API_KEY`, `BEA_API_KEY` — loaded from `.env` (gitignored).
- **Client Health Score**: Computed by `calculate_health_score()` immediately after `calculate_metrics()`. Each of 4 KPIs contributes 0–25 pts. Thresholds: ≥80 = green "Excellent", ≥50 = yellow "Needs Attention", <50 = red "At Risk". UI-only — no PPTX changes.
- **Client profile persistence**: Per-client employee count and avg hourly rate stored in `client_profiles.json` (gitignored). Default fallback: `employee_count=0`, `avg_hourly_rate=50`. When `employee_count=0`, `has_data=False` and impact cards are not shown in the dashboard.
- **Business impact formula**: `employees_affected = employee_count × 0.1`; `productivity_hours_lost = critical_ticket_count × avg_critical_res_hours × employees_affected`; `estimated_dollar_cost = productivity_hours_lost × avg_hourly_rate`. Risk statement: "High risk" if critical_count > 3 and proactive_pct < 40; "Moderate risk" if critical_count > 0; else "Low risk".
- **Risk flag ordering**: `analyze_risks()` outputs flags in order: open critical tickets → critical volume → recurring keywords. Max 5 total; only top 3 are mapped to PPTX placeholders.
- **Dynamic recommendation slots**: `Master_QBR_Template.pptx` contains all 10 recommendation slots. At runtime, `_remove_unused_rec_slots()` deletes shapes for slots N > num_recs (set in Settings dialog).
- **Ticket sampling status message**: When AI is enabled and ticket count exceeds `sample_size`, the status message clarifies how many will be sampled: "Retrieved N tickets (M will be sampled for AI analysis)."
- **BEA industry selectbox state**: Persisted per-client in Streamlit session state using key `bea_industry_{client_id}` to prevent resets on rerun.
- **Pre-commit hook**: `.pre-commit-config.yaml` uses `ruff` (v0.3.0) for linting (`--fix`) and formatting. Run `pre-commit install` after cloning.
- **No test suite exists** — the project uses `main.py` and `generate_client_qbr.py`'s `__main__` block for manual testing with mock data.
