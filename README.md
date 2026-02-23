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

- **`app.py`** — Streamlit UI. Handles auth, client/date selection, AI toggle, and download. Orchestrates the full pipeline via `run_qbr_generation()`.
- **`halo_client.py`** — `HaloClient` class. OAuth2 client credentials flow against HaloPSA REST API (`/auth/token`, `/api/Tickets`, `/api/Client`). Reads credentials from `.env` via `python-dotenv`.
- **`generate_client_qbr.py`** — Core engine. `calculate_metrics()` computes 4 KPIs from raw tickets (proactive/reactive split, same-day resolution rate, critical resolution time, avg first response). `generate_qbr()` opens a template PPTX, replaces `{{PLACEHOLDER}}` text in shapes, and inserts a matplotlib chart image in place of `{{CHART_PLACEHOLDER}}`. `build_recommendation_replacements()` maps recommendation dicts to `{{REC_N_TITLE}}`/`{{REC_N_RATIONALE}}` keys.
- **`create_qbr_template.py`** — Builds `Master_QBR_Template.pptx` programmatically using `python-pptx`. Defines slide structure with placeholder text (e.g., `{{CLIENT_NAME}}`, `{{SAME_DAY_RATE}}`). Run this to regenerate the template if slides need restructuring.
- **`recommendation_engine.py`** — Calls Anthropic Claude (`claude-sonnet-4-5-20250929`) with ticket metrics + sampled summaries to produce structured JSON recommendations.
- **`qbr_data_replacer.py`** — Standalone placeholder replacer (earlier iteration). `replace_text_in_shape()` handles text frames, tables, and grouped shapes. Not used by the main pipeline (superseded by `generate_client_qbr.py`'s replacer).

## Key Conventions

- **Placeholder format**: All PPTX placeholders use `{{DOUBLE_BRACES}}` (e.g., `{{CLIENT_NAME}}`, `{{TICKET_COUNT}}`). Recommendation slots are `{{REC_1_TITLE}}` through `{{REC_10_TITLE}}` with matching `_RATIONALE` keys.
- **HaloPSA ticket type IDs**: Proactive types are `[30, 40, 100]`; all others are reactive. Priority ID `1` = Critical.
- **Template file**: The pipeline expects `Master_QBR_Template.pptx` in the project root. Only this file is tracked in git (all other `.pptx` files are gitignored).
- **Environment variables**: `HALO_HOST`, `CLIENT_ID`, `CLIENT_SECRET`, `HALO_SCOPE`, `ANTHROPIC_API_KEY` — loaded from `.env` (gitignored).
- **No test suite exists** — the project uses `main.py` and `generate_client_qbr.py`'s `__main__` block for manual testing with mock data.
