"""
MSP QBR Generator - Chat-Driven Streamlit Web App
Natural language chat interface with results dashboard panel.

Prerequisites:
    pip install streamlit python-pptx matplotlib requests python-dotenv anthropic

Usage:
    streamlit run app.py
"""

import os
import tempfile
from datetime import date, timedelta

import streamlit as st
from dotenv import load_dotenv

from generate_client_qbr import calculate_metrics, calculate_health_score, generate_qbr
from halo_client import HaloClient
from client_profiles import get_profile, upsert_profile
from chat_preferences import (
    get_ai_settings,
    update_ai_settings,
    get_client_industry,
    set_client_industry,
    get_msp_contact,
    set_msp_contact,
)
from chat_engine import (
    Intent,
    parse_intent_regex,
    parse_intent_llm,
    parse_date_expression,
    resolve_client,
    resolve_disambiguation,
    get_missing_fields,
    get_optional_prompts,
    format_help_message,
    format_client_list,
    format_disambiguation,
    match_industry,
)

load_dotenv()

# ─────────────────────────────────────────────
# ENV DEFAULTS
# ─────────────────────────────────────────────
_env_halo_url = os.environ.get("HALO_HOST", "")
_env_client_id = os.environ.get("CLIENT_ID", "")
_env_client_secret = os.environ.get("CLIENT_SECRET", "")
_env_anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
_env_bea_key = os.environ.get("BEA_API_KEY", "")

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="MSP QBR Generator", layout="wide")

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
# Load Inter font
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    /* ── Font ── */
    [data-testid="stApp"] {
        font-family: 'Inter', sans-serif;
    }

    /* Hide sidebar */
    [data-testid="stSidebar"] { display: none; }
    section[data-testid="stSidebarNav"] { display: none; }

    /* ── Reduce dead space ── */
    [data-testid="stMainBlockContainer"] {
        padding-top: 1rem !important;
        max-width: 1200px;
    }

    /* ── Typography ── */
    h1 {
        color: #242E65 !important;
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }
    h2 {
        color: #242E65 !important;
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
    }
    h3 {
        color: #242E65 !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }

    /* ── Dividers: subtle gray gradient fade ── */
    hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, transparent, #e5e7eb 30%, #e5e7eb 70%, transparent) !important;
    }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #f0f1f3;
        border-left: 4px solid #F05523;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: box-shadow 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    [data-testid="stMetric"] [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        color: #6b7280 !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #242E65 !important;
    }

    /* ── Download button ── */
    [data-testid="stDownloadButton"] > button {
        background: linear-gradient(135deg, #242E65, #2d3a7e) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(36,46,101,0.25) !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stDownloadButton"] > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(36,46,101,0.35) !important;
    }

    /* ── Minimal gear button ── */
    button[data-testid="stBaseButton-secondary"][kind="secondary"] {
        border: none;
        background: transparent;
        border-radius: 8px;
        transition: background-color 0.15s ease;
    }
    button[data-testid="stBaseButton-secondary"][kind="secondary"]:hover {
        background-color: #f0f1f8;
    }

    /* ── Chat input ── */
    [data-testid="stChatInput"] textarea {
        border-radius: 12px !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: #242E65 !important;
        box-shadow: 0 0 0 3px rgba(36,46,101,0.1) !important;
    }

    /* ── Chat messages ── */
    [data-testid="stChatMessage"][data-testid-role="user"] {
        background-color: #f0f1f8;
        border-radius: 10px;
        padding: 0.5rem;
    }
    [data-testid="stChatMessage"][data-testid-role="assistant"] {
        background-color: #ffffff;
        border: 1px solid #f0f1f3;
        border-radius: 10px;
        padding: 0.5rem;
    }

    /* ── Dialog inputs ── */
    [data-testid="stDialog"] input,
    [data-testid="stDialog"] textarea {
        border-radius: 8px !important;
        transition: border-color 0.2s ease !important;
    }
    [data-testid="stDialog"] input:focus,
    [data-testid="stDialog"] textarea:focus {
        border-color: #242E65 !important;
    }

    /* ── Welcome hero ── */
    .chat-welcome-hero {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 50vh;
        text-align: center;
        padding: 2rem 1rem;
    }
    .chat-welcome-hero .hero-icon {
        width: 64px;
        height: 64px;
        background: linear-gradient(135deg, #242E65, #2d3a7e);
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 1.25rem;
        box-shadow: 0 4px 16px rgba(36,46,101,0.2);
    }
    .chat-welcome-hero .hero-icon span {
        color: white;
        font-size: 1.75rem;
        font-weight: 700;
        font-family: 'Inter', sans-serif;
    }
    .chat-welcome-hero .hero-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #242E65;
        margin: 0 0 0.5rem 0;
    }
    .chat-welcome-hero .hero-subtitle {
        color: #6b7280;
        font-size: 0.95rem;
        max-width: 480px;
        line-height: 1.6;
        margin: 0;
    }

    /* ── Example prompt buttons as cards ── */
    .st-key-example_prompts {
        max-width: 600px;
        margin: 0 auto;
    }
    .st-key-example_prompts button {
        background: #ffffff !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 12px !important;
        color: #1A1A2E !important;
        transition: all 0.2s ease !important;
        font-weight: 500 !important;
    }
    .st-key-example_prompts button:hover {
        border-color: #242E65 !important;
        box-shadow: 0 4px 12px rgba(36,46,101,0.1) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Connection banner ── */
    .connection-banner {
        background: #f0f1f8;
        border: 1px solid #e0e2ef;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        color: #242E65;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    .connection-banner .banner-label {
        font-weight: 600;
    }
    .connection-banner .banner-desc {
        color: #6b7280;
        font-size: 0.85rem;
    }

    /* ── Settings dialog section headers ── */
    [data-testid="stDialog"] h2,
    [data-testid="stDialog"] h3 {
        font-size: 1rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        color: #6b7280 !important;
    }

    /* ── When two-panel QBR view is active, constrain the full ancestor chain
       so the panels can be independently scrollable within a fixed viewport.
       The :has() selector activates only when the nested HorizontalBlock
       (metrics row etc.) is present inside a column — i.e., QBR is shown. ── */

    /* 1. Constrain the stMain scrollable area */
    [data-testid="stMain"]:has([data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"]) {
        height: 100vh;
        overflow: hidden;
    }

    /* 2. Constrain stMainBlockContainer */
    [data-testid="stMainBlockContainer"]:has([data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"]) {
        height: 100%;
        overflow: hidden;
        padding-bottom: 0 !important;
    }

    /* 3. stVerticalBlock fills height and allows flex children to shrink */
    [data-testid="stMainBlockContainer"]:has([data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"]) > [data-testid="stVerticalBlock"] {
        height: 100%;
        overflow: hidden;
    }

    /* 4. The stLayoutWrapper wrapping the main panel block grows to fill remaining space */
    [data-testid="stMainBlockContainer"]:has([data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"]) > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:has([data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"]) {
        flex: 1;
        min-height: 0;
        overflow: hidden;
    }

    /* 5. The main two-panel HorizontalBlock fills the wrapper */
    [data-testid="stHorizontalBlock"]:has([data-testid="stHorizontalBlock"]) {
        height: 100%;
        overflow: hidden;
    }

    /* 6. Each column scrolls independently */
    [data-testid="stHorizontalBlock"]:has([data-testid="stHorizontalBlock"]) > [data-testid="stColumn"] {
        height: 100%;
        overflow-y: auto;
        min-height: 0;
    }

    /* Chat panel — white conversation surface */
    [data-testid="stHorizontalBlock"]:has([data-testid="stHorizontalBlock"]) > [data-testid="stColumn"]:nth-child(1) {
        background-color: #ffffff;
    }

    /* Results panel — light tinted dashboard surface + vertical divider */
    [data-testid="stHorizontalBlock"]:has([data-testid="stHorizontalBlock"]) > [data-testid="stColumn"]:nth-child(2) {
        background-color: #f8f9fc;
        border-left: 1px solid #e0e2ef;
        padding-left: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# SESSION STATE INITIALISATION
# ─────────────────────────────────────────────
_ai_prefs = get_ai_settings()
_defaults = {
    "authenticated": False,
    "clients": [],
    "halo_client": None,
    "qbr_bytes": None,
    "qbr_filename": "QBR_Report.pptx",
    "bea_insights": None,
    "bea_industry_name": None,
    "num_recs": _ai_prefs["num_recs"],
    "sample_size": _ai_prefs["sample_size"],
    "health_score": None,
    "metrics_display": None,
    "business_impact": None,
    "risk_flags": None,
    "client_employee_count": 0,
    "client_avg_hourly_rate": 50.0,
    # Settings dialog values
    "halo_url": _env_halo_url,
    "client_id_val": _env_client_id,
    "client_secret_val": _env_client_secret,
    "anthropic_key": _env_anthropic_key,
    "bea_key": _env_bea_key,
    "use_ai": _ai_prefs["use_ai"],
    "auto_connect_attempted": False,
    # Chat state
    "chat_history": [],
    "conv_state": {},
    "results_visible": True,
    "results_collapsed": False,
}
for key, default in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────
def try_authenticate(halo_url, client_id, client_secret):
    """Attempts to authenticate and fetch clients. Returns (success, error_msg)."""
    try:
        os.environ["HALO_HOST"] = halo_url.rstrip("/")
        os.environ["CLIENT_ID"] = client_id
        os.environ["CLIENT_SECRET"] = client_secret

        client = HaloClient()
        token = client.authenticate()

        if not token:
            return False, "Authentication failed: No token returned."

        clients = client.get_clients()
        if not clients:
            return False, "Authenticated, but no clients found in this Halo instance."

        st.session_state.halo_client = client
        st.session_state.clients = clients
        st.session_state.authenticated = True
        return True, None

    except Exception as e:
        return False, str(e)


def _add_message(role: str, content: str):
    """Append a message to chat history."""
    st.session_state.chat_history.append({"role": role, "content": content})


def _render_bea_panel(insights: dict, industry_name: str):
    """Render the BEA economic context panel."""
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    st.subheader("Industry Economic Context (BEA)")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Sector GDP Value", insights.get("latest_value", "N/A"))
    with col2:
        qoq = insights.get("qoq_pct", "N/A")
        direction = insights.get("qoq_direction", "flat")
        delta_color = "normal" if direction != "flat" else "off"
        st.metric(
            "QoQ Growth",
            qoq,
            delta=qoq if qoq != "N/A" else None,
            delta_color=delta_color,
        )
    with col3:
        yoy = insights.get("yoy_pct", "N/A")
        direction_y = insights.get("yoy_direction", "flat")
        delta_color_y = "normal" if direction_y != "flat" else "off"
        st.metric(
            "YoY Growth",
            yoy,
            delta=yoy if yoy != "N/A" else None,
            delta_color=delta_color_y,
        )
    with col4:
        st.metric("Latest Period", insights.get("latest_period", "N/A"))

    labels = insights.get("trend_labels", [])
    values = insights.get("trend_values", [])
    valid_pairs = [(lbl, val) for lbl, val in zip(labels, values) if val is not None]
    if valid_pairs:
        chart_labels, chart_values = zip(*valid_pairs)
        chart_values_b = [v / 1000 for v in chart_values]

        fig, ax = plt.subplots(figsize=(9, 2.5))
        ax.plot(chart_labels, chart_values_b, marker="o", color="#242E65", linewidth=2)
        ax.fill_between(chart_labels, chart_values_b, alpha=0.15, color="#242E65")
        ax.set_ylabel("GDP ($B, chained 2017$)", fontsize=9)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}B"))
        ax.tick_params(axis="x", labelsize=8, rotation=30)
        ax.tick_params(axis="y", labelsize=8)
        ax.set_title(f"{industry_name} -- 8-Quarter GDP Trend", fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    st.caption(
        "Source: U.S. Bureau of Economic Analysis (BEA), GDP by Industry. "
        "Data subject to ~1 quarter publication lag. Values in chained 2017 dollars."
    )


def _render_health_score(score: int):
    if score >= 80:
        color, label = "#16a34a", "Excellent"
    elif score >= 50:
        color, label = "#ca8a04", "Needs Attention"
    else:
        color, label = "#dc2626", "At Risk"

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:1rem;">
            <div style="background-color:{color};color:white;
                        font-size:2.5rem;font-weight:700;padding:0.3rem 1rem;
                        border-radius:10px;line-height:1.2;
                        box-shadow:0 2px 8px {color}40;">
                {score}
            </div>
            <div>
                <div style="font-size:0.75rem;font-weight:500;text-transform:uppercase;
                            letter-spacing:0.05em;color:#6b7280;">
                    Health Score
                </div>
                <div style="font-size:1.1rem;font-weight:600;color:{color};">
                    {label}
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_business_impact(impact: dict):
    """Render business impact metrics."""
    st.subheader("Business Impact")

    if not impact.get("has_data"):
        st.info(
            "Set employee count and hourly rate via chat to see business impact estimates. "
            "Example: 'Acme has 150 employees at $75/hr'"
        )
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Critical Tickets", impact["critical_ticket_count"])
    with col2:
        st.metric(
            "Productivity Hours at Risk",
            f"{impact['productivity_hours_lost']:,.1f}",
        )
    with col3:
        st.metric(
            "Estimated Cost",
            f"${impact['estimated_dollar_cost']:,.0f}",
        )

    st.markdown(f"> {impact['risk_statement']}")
    st.caption(
        "Assumes 10% of workforce affected per critical incident. "
        "Cost = hours lost x loaded hourly rate."
    )


def _render_risk_flags(risk_flags: list[dict]):
    """Render color-coded risk flag cards."""
    if not risk_flags:
        return

    st.subheader("Risk Flags")

    severity_colors = {
        "high": ("#dc2626", "#fef2f2"),
        "medium": ("#ea580c", "#fff7ed"),
        "low": ("#ca8a04", "#fefce8"),
    }

    for rf in risk_flags:
        text_color, bg_color = severity_colors.get(
            rf["severity"], ("#4a5568", "#f7fafc")
        )
        sev_label = rf["severity"].upper()
        st.markdown(
            f'<div style="background-color:{bg_color};border-left:4px solid {text_color};'
            f'padding:0.6rem 0.85rem;margin-bottom:0.5rem;border-radius:8px;'
            f'transition:transform 0.15s ease;"'
            f' onmouseover="this.style.transform=\'translateX(2px)\'"'
            f' onmouseout="this.style.transform=\'translateX(0)\'">'
            f'<span style="background:{text_color};color:white;font-weight:600;'
            f'font-size:0.7rem;padding:2px 8px;border-radius:4px;'
            f'letter-spacing:0.03em;display:inline-block;margin-right:0.5rem;">'
            f"{sev_label}</span>"
            f'<span style="color:#1a1a2e;font-size:0.9rem;">{rf["flag"]}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_results_dashboard():
    """Render the dashboard-style results view."""
    # Collapse toggle
    if st.button(
        "Hide Results" if not st.session_state.results_collapsed else "Show Results",
        key="collapse_results",
        use_container_width=True,
    ):
        st.session_state.results_collapsed = not st.session_state.results_collapsed
        st.rerun()

    if st.session_state.results_collapsed:
        return

    st.markdown("---")

    # Download button
    st.download_button(
        label="Download PowerPoint QBR",
        data=st.session_state.qbr_bytes,
        file_name=st.session_state.qbr_filename,
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        use_container_width=True,
    )
    st.caption(f"File: `{st.session_state.qbr_filename}`")

    # Metrics row
    metrics = st.session_state.get("metrics_display")
    health = st.session_state.get("health_score")
    if metrics or health is not None:
        st.markdown("---")
        st.subheader("Results Dashboard")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("**Client Health Score**")
            if health is not None:
                _render_health_score(health)
        with col2:
            st.metric(
                "Same-Day Resolution",
                f"{metrics.get('{{SAME_DAY_RATE}}', 'N/A')}%" if metrics else "N/A",
            )
        with col3:
            st.metric(
                "Avg First Response",
                metrics.get("{{AVG_FIRST_RESPONSE}}", "N/A") if metrics else "N/A",
            )
        with col4:
            st.metric(
                "Critical Resolution",
                metrics.get("{{CRITICAL_RES_TIME}}", "N/A") if metrics else "N/A",
            )

        st.caption(
            "Health Score = avg of 4 KPIs: Proactive %, Same-Day Resolution, "
            "Critical Resolution Time, Avg First Response (25 pts each)"
        )

    # Business Impact
    if st.session_state.get("business_impact"):
        st.markdown("---")
        _render_business_impact(st.session_state.business_impact)

    # Risk Flags
    if st.session_state.get("risk_flags"):
        st.markdown("---")
        _render_risk_flags(st.session_state.risk_flags)

    # BEA panel
    if st.session_state.bea_insights:
        st.markdown("---")
        _render_bea_panel(
            st.session_state.bea_insights,
            st.session_state.bea_industry_name,
        )


def run_qbr_generation(
    selected_client,
    start_date,
    end_date,
    msp_contact,
    use_ai,
    anthropic_key,
    num_recs,
    sample_size,
    manual_recs=None,
    bea_api_key=None,
    selected_industry_name=None,
    employee_count=0,
    avg_hourly_rate=50.0,
):
    from recommendation_engine import generate_recommendations
    from generate_client_qbr import build_recommendation_replacements
    from bea_client import BEAClient
    from bea_insights import (
        INDUSTRY_SECTORS,
        calculate_sector_growth,
        format_bea_replacements,
        build_empty_bea_replacements,
    )
    from business_impact import (
        calculate_business_impact,
        format_impact_replacements,
        build_empty_impact_replacements,
    )
    from risk_analyzer import analyze_risks, format_risk_replacements

    client = st.session_state.halo_client
    client_id = selected_client["id"]
    client_name = selected_client["name"]
    review_period = (
        f"{start_date.strftime('%B %d, %Y')} -- {end_date.strftime('%B %d, %Y')}"
    )

    # 1. Fetch tickets
    _add_message("assistant", f"Fetching tickets for **{client_name}**...")
    data = client.get_tickets(
        client_id=client_id,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        page_size=500,
    )
    tickets = data.get("tickets", []) if isinstance(data, dict) else (data or [])

    if not tickets:
        _add_message(
            "assistant",
            f"No tickets found for **{client_name}** in the selected date range.",
        )
        return None, None, None

    if use_ai and anthropic_key and len(tickets) > sample_size:
        _add_message(
            "assistant",
            f"Retrieved **{len(tickets)}** tickets "
            f"(**{sample_size}** will be sampled for AI analysis).",
        )
    else:
        _add_message("assistant", f"Retrieved **{len(tickets)}** tickets.")

    # 2. Compute metrics
    metrics_data = calculate_metrics(tickets)
    health_score = calculate_health_score(metrics_data)
    st.session_state.metrics_display = metrics_data

    # 2.5 Fetch BEA economic context
    bea_replacements = build_empty_bea_replacements()
    if bea_api_key and selected_industry_name:
        _add_message("assistant", f"Fetching BEA data for {selected_industry_name}...")
        try:
            bea_client = BEAClient(api_key=bea_api_key)
            raw_rows = bea_client.get_gdp_by_industry(
                INDUSTRY_SECTORS[selected_industry_name], num_quarters=8
            )
            insights = calculate_sector_growth(raw_rows)
            bea_replacements = format_bea_replacements(selected_industry_name, insights)
            st.session_state.bea_insights = insights
            st.session_state.bea_industry_name = selected_industry_name
        except Exception as e:
            _add_message(
                "assistant",
                f"BEA data unavailable: {e}. Proceeding without economic context.",
            )

    # 2c. Business impact
    impact_replacements = build_empty_impact_replacements()
    impact = calculate_business_impact(
        metrics_data, tickets, employee_count, avg_hourly_rate
    )
    st.session_state.business_impact = impact
    if impact["has_data"]:
        impact_replacements = format_impact_replacements(impact)

    # 2d. Risk analysis
    risk_flags = analyze_risks(tickets)
    st.session_state.risk_flags = risk_flags
    risk_replacements = format_risk_replacements(risk_flags)

    # 3. Recommendations
    if use_ai and anthropic_key:
        _add_message("assistant", f"AI is generating {num_recs} recommendations...")
        sampled = tickets[:sample_size]
        summaries = [t.get("summary", "") for t in sampled if t.get("summary")]

        try:
            recommendations = generate_recommendations(
                client_name=client_name,
                review_period=review_period,
                metrics=metrics_data,
                ticket_summaries=summaries,
                num_recommendations=num_recs,
                anthropic_api_key=anthropic_key,
                employee_count=employee_count,
                avg_hourly_rate=avg_hourly_rate,
                business_impact=impact,
                risk_flags=risk_flags,
            )
        except Exception as e:
            _add_message("assistant", f"Claude API error: {e}")
            return None, None, None
    else:
        recommendations = [
            {"title": f"Recommendation {i + 1}", "rationale": rec}
            for i, rec in enumerate(manual_recs or [])
            if rec
        ]

    # 4. Build replacements
    rec_replacements = build_recommendation_replacements(recommendations)
    contextual_data = {
        "{{CLIENT_NAME}}": client_name,
        "{{REVIEW_PERIOD}}": review_period,
        "{{CHART_PLACEHOLDER}}": "",
        "{{MSP_CONTACT_INFO}}": msp_contact,
        **rec_replacements,
        **bea_replacements,
        **impact_replacements,
        **risk_replacements,
    }

    # 5. Generate PPTX
    _add_message("assistant", "Generating PowerPoint...")
    template_path = "Master_QBR_Template.pptx"
    if not os.path.exists(template_path):
        _add_message("assistant", "Master_QBR_Template.pptx not found.")
        return None, None, None

    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        output_path = tmp.name

    generate_qbr(
        template_path=template_path,
        output_path=output_path,
        contextual_data=contextual_data,
        ticket_data=tickets,
        num_recs=num_recs,
    )

    with open(output_path, "rb") as f:
        pptx_bytes = f.read()
    os.remove(output_path)

    safe_name = client_name.replace(" ", "_").replace("/", "-")
    filename = f"{safe_name}_QBR_{start_date.strftime('%Y%m%d')}.pptx"
    return pptx_bytes, filename, health_score


# ─────────────────────────────────────────────
# SETTINGS DIALOG (credentials only)
# ─────────────────────────────────────────────
@st.dialog("Settings", width="large")
def settings_dialog():
    _conn_color = "#16a34a" if st.session_state.authenticated else "#dc2626"
    _conn_text = "Connected" if st.session_state.authenticated else "Not connected"
    st.markdown(
        f'<h2 style="display:flex;align-items:center;gap:0.5rem;">'
        f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
        f'background:{_conn_color};"></span> HaloPSA Connection'
        f'<span style="font-size:0.75rem;font-weight:400;color:{_conn_color};'
        f'margin-left:auto;">{_conn_text}</span></h2>',
        unsafe_allow_html=True,
    )
    halo_url = st.text_input(
        "HaloPSA URL",
        value=st.session_state.halo_url,
        placeholder="https://your-instance.halopsa.com",
    )
    col1, col2 = st.columns(2)
    with col1:
        client_id = st.text_input(
            "Client ID",
            value=st.session_state.client_id_val,
            placeholder="Your API Client ID",
        )
    with col2:
        client_secret = st.text_input(
            "Client Secret",
            value=st.session_state.client_secret_val,
            placeholder="Your API Client Secret",
            type="password",
        )

    st.markdown("---")
    st.subheader("API Keys")
    anthropic_key = st.text_input(
        "Anthropic API Key",
        value=st.session_state.anthropic_key,
        placeholder="sk-ant-...",
        type="password",
        help="Used for AI recommendations and chat intent parsing.",
    )
    bea_key = st.text_input(
        "BEA API Key",
        value=st.session_state.bea_key,
        placeholder="Get free key at apps.bea.gov/api/signup",
        type="password",
        help="Optional. Free registration at apps.bea.gov/api/signup.",
    )

    st.markdown("---")
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("Save", type="primary", use_container_width=True):
            st.session_state.halo_url = halo_url
            st.session_state.client_id_val = client_id
            st.session_state.client_secret_val = client_secret
            st.session_state.anthropic_key = anthropic_key
            st.session_state.bea_key = bea_key
            st.rerun()
    with btn_col2:
        if st.button("Connect to HaloPSA", use_container_width=True):
            if not halo_url or not client_id or not client_secret:
                st.error("HaloPSA URL, Client ID, and Client Secret are required.")
            else:
                st.session_state.halo_url = halo_url
                st.session_state.client_id_val = client_id
                st.session_state.client_secret_val = client_secret
                st.session_state.anthropic_key = anthropic_key
                st.session_state.bea_key = bea_key
                with st.spinner("Connecting..."):
                    success, error = try_authenticate(
                        halo_url, client_id, client_secret
                    )
                if success:
                    st.success(
                        f"Connected! {len(st.session_state.clients)} clients found."
                    )
                    st.rerun()
                else:
                    st.error(f"Connection failed: {error}")


# ─────────────────────────────────────────────
# CHAT MESSAGE HANDLER
# ─────────────────────────────────────────────
def _handle_chat_message(user_message: str):
    """Process a user chat message: parse intent, execute action, respond."""
    state = st.session_state.conv_state

    # Handle disambiguation response
    if state.get("awaiting") == "disambiguation":
        candidates = state.get("pending_disambiguation", [])
        selected = resolve_disambiguation(user_message, candidates)
        if selected:
            state["client_id"] = selected["id"]
            state["client_name"] = selected["name"]
            state["awaiting"] = None
            state["pending_disambiguation"] = None
            _add_message("assistant", f"Selected **{selected['name']}**.")
            # Load persisted profile for this client
            profile = get_profile(selected["id"])
            if profile["employee_count"] > 0:
                state["employee_count"] = profile["employee_count"]
                state["avg_hourly_rate"] = profile["avg_hourly_rate"]
            # Load persisted industry
            saved_industry = get_client_industry(selected["id"])
            if saved_industry:
                state["industry_name"] = saved_industry
            # Continue checking for missing fields
            _check_and_prompt_missing(state)
            return
        else:
            _add_message(
                "assistant",
                "I couldn't match that. Please reply with a number from the list "
                "or the full client name.",
            )
            return

    # Handle awaiting responses (follow-up questions)
    if state.get("awaiting") == "date_range":
        date_range = parse_date_expression(user_message)
        if date_range:
            state["start_date"] = date_range[0].isoformat()
            state["end_date"] = date_range[1].isoformat()
            state["awaiting"] = None
            _add_message(
                "assistant",
                f"Date range set: **{date_range[0].strftime('%B %d, %Y')}** to "
                f"**{date_range[1].strftime('%B %d, %Y')}**.",
            )
            _check_and_prompt_missing(state)
            return
        else:
            _add_message(
                "assistant",
                "I couldn't parse that date range. Try something like "
                "'last quarter', 'Q4 2025', or 'January to March 2026'.",
            )
            return

    if state.get("awaiting") == "msp_contact":
        state["msp_contact"] = user_message.strip()
        state["awaiting"] = None
        set_msp_contact(user_message.strip())
        _add_message("assistant", f"MSP contact set: **{user_message.strip()}**.")
        _check_and_prompt_missing(state)
        return

    if state.get("awaiting") == "employee_count":
        lower = user_message.lower().strip()
        if lower == "skip":
            state["asked_employee_count"] = True
            state["awaiting"] = None
            _check_and_prompt_missing(state)
            return
        # Try to extract number
        import re

        match = re.search(r"(\d+)", user_message)
        if match:
            emp_count = int(match.group(1))
            state["employee_count"] = emp_count
            state["awaiting"] = None
            # Also check for hourly rate in same message
            rate_match = re.search(
                r"\$?\s*(\d+(?:\.\d+)?)\s*(?:/\s*hr|per\s*hour|hourly)",
                user_message,
                re.IGNORECASE,
            )
            if rate_match:
                state["avg_hourly_rate"] = float(rate_match.group(1))
                _add_message(
                    "assistant",
                    f"Set **{emp_count}** employees at "
                    f"**${state['avg_hourly_rate']:.0f}/hr**.",
                )
            else:
                _add_message("assistant", f"Set employee count to **{emp_count}**.")
                state["awaiting"] = "hourly_rate"
                _add_message(
                    "assistant",
                    "What is the average loaded hourly rate for this client? "
                    "(e.g., '$75/hr' or just '75'). Type 'skip' for default $50/hr.",
                )
                return
            # Persist profile
            if state.get("client_id"):
                upsert_profile(
                    state["client_id"],
                    state.get("employee_count", 0),
                    state.get("avg_hourly_rate", 50.0),
                )
            _check_and_prompt_missing(state)
            return
        _add_message(
            "assistant",
            "Please enter a number for employee count, or type 'skip'.",
        )
        return

    if state.get("awaiting") == "hourly_rate":
        lower = user_message.lower().strip()
        if lower == "skip":
            state["avg_hourly_rate"] = 50.0
            state["awaiting"] = None
            _add_message("assistant", "Using default rate of **$50/hr**.")
            if state.get("client_id"):
                upsert_profile(
                    state["client_id"],
                    state.get("employee_count", 0),
                    state.get("avg_hourly_rate", 50.0),
                )
            _check_and_prompt_missing(state)
            return
        import re

        match = re.search(r"(\d+(?:\.\d+)?)", user_message)
        if match:
            state["avg_hourly_rate"] = float(match.group(1))
            state["awaiting"] = None
            _add_message(
                "assistant",
                f"Hourly rate set to **${state['avg_hourly_rate']:.0f}/hr**.",
            )
            if state.get("client_id"):
                upsert_profile(
                    state["client_id"],
                    state.get("employee_count", 0),
                    state.get("avg_hourly_rate", 50.0),
                )
            _check_and_prompt_missing(state)
            return
        _add_message(
            "assistant",
            "Please enter a number for hourly rate, or type 'skip'.",
        )
        return

    if state.get("awaiting") == "industry":
        lower = user_message.lower().strip()
        if lower == "skip":
            state["asked_industry"] = True
            state["awaiting"] = None
            _check_and_prompt_missing(state)
            return
        matched = match_industry(user_message)
        if matched:
            state["industry_name"] = matched
            state["awaiting"] = None
            _add_message("assistant", f"Industry set to **{matched}**.")
            if state.get("client_id"):
                set_client_industry(state["client_id"], matched)
            _check_and_prompt_missing(state)
            return
        _add_message(
            "assistant",
            "I couldn't match that industry. Try: Healthcare, Finance, IT, "
            "Manufacturing, Retail, Construction, Education, etc. Or type 'skip'.",
        )
        return

    # ── Normal intent parsing ────────────────────
    intent, params = parse_intent_regex(user_message)

    # Fall back to LLM for unknown intents
    if intent == Intent.UNKNOWN and st.session_state.anthropic_key:
        intent, params = parse_intent_llm(
            user_message,
            st.session_state.chat_history,
            state,
            st.session_state.anthropic_key,
        )

    # ── Handle skip from LLM ────────────────────
    if params.get("is_skip"):
        if state.get("awaiting"):
            state[f"asked_{state['awaiting']}"] = True
            state["awaiting"] = None
            _check_and_prompt_missing(state)
            return

    # ── Route by intent ──────────────────────────
    if intent == Intent.HELP:
        _add_message("assistant", format_help_message())
        return

    if intent == Intent.LIST_CLIENTS:
        if not st.session_state.authenticated:
            _add_message(
                "assistant",
                "Not connected to HaloPSA. Please configure credentials in Settings (gear icon).",
            )
            return
        _add_message("assistant", format_client_list(st.session_state.clients))
        return

    if intent == Intent.SET_AI_SETTINGS:
        updated = update_ai_settings(
            use_ai=params.get("use_ai"),
            num_recs=params.get("num_recs"),
            sample_size=params.get("sample_size"),
        )
        st.session_state.use_ai = updated["use_ai"]
        st.session_state.num_recs = updated["num_recs"]
        st.session_state.sample_size = updated["sample_size"]

        parts = []
        if "use_ai" in params:
            parts.append(
                f"AI recommendations **{'enabled' if updated['use_ai'] else 'disabled'}**"
            )
        if "num_recs" in params:
            parts.append(f"Number of recommendations: **{updated['num_recs']}**")
        if "sample_size" in params:
            parts.append(f"Sample size: **{updated['sample_size']}**")
        _add_message("assistant", "Settings updated. " + ". ".join(parts) + ".")
        return

    if intent == Intent.SET_CLIENT_PROFILE:
        # Need to know which client
        if not state.get("client_id"):
            # Try to find client name in params
            client_name = params.get("client_name")
            if client_name and st.session_state.authenticated:
                matches = resolve_client(client_name, st.session_state.clients)
                if len(matches) == 1:
                    state["client_id"] = matches[0]["id"]
                    state["client_name"] = matches[0]["name"]
                elif len(matches) > 1:
                    _add_message(
                        "assistant",
                        "Which client? " + format_disambiguation(matches),
                    )
                    return

        emp = params.get("employee_count")
        rate = params.get("avg_hourly_rate")
        if state.get("client_id"):
            profile = get_profile(state["client_id"])
            if emp is not None:
                profile["employee_count"] = emp
                state["employee_count"] = emp
            if rate is not None:
                profile["avg_hourly_rate"] = rate
                state["avg_hourly_rate"] = rate
            upsert_profile(
                state["client_id"],
                profile["employee_count"],
                profile["avg_hourly_rate"],
            )
            _add_message(
                "assistant",
                f"Updated profile for **{state.get('client_name', 'client')}**: "
                f"{profile['employee_count']} employees, "
                f"${profile['avg_hourly_rate']:.0f}/hr.",
            )
        else:
            _add_message(
                "assistant",
                "Which client should I update? Please specify the client name.",
            )
        return

    if intent == Intent.SET_INDUSTRY:
        industry_text = params.get("industry_name") or user_message
        matched = match_industry(industry_text)
        if matched:
            if state.get("client_id"):
                state["industry_name"] = matched
                set_client_industry(state["client_id"], matched)
                _add_message(
                    "assistant",
                    f"Industry for **{state.get('client_name', 'client')}** "
                    f"set to **{matched}**.",
                )
            else:
                _add_message(
                    "assistant",
                    "Which client? Please select a client first "
                    "(e.g., 'Generate QBR for Acme').",
                )
        else:
            _add_message(
                "assistant",
                "I couldn't match that industry. Try: Healthcare, Finance, IT, "
                "Manufacturing, Retail, Construction, Education, etc.",
            )
        return

    if intent == Intent.SHOW_LAST_QBR:
        if st.session_state.qbr_bytes:
            st.session_state.results_collapsed = False
            _add_message(
                "assistant",
                f"The last generated QBR is available in the Results panel: "
                f"**{st.session_state.qbr_filename}**.",
            )
        else:
            _add_message("assistant", "No QBR has been generated yet in this session.")
        return

    if intent == Intent.SHOW_HEALTH_SCORE:
        if not st.session_state.authenticated:
            _add_message(
                "assistant",
                "Not connected to HaloPSA. Please configure credentials in Settings.",
            )
            return
        client_name = params.get("client_name")
        if not client_name:
            _add_message("assistant", "Which client? Please specify the client name.")
            return
        matches = resolve_client(client_name, st.session_state.clients)
        if not matches:
            _add_message(
                "assistant",
                f"No client matching '{client_name}' found.",
            )
            return
        if len(matches) > 1:
            _add_message("assistant", format_disambiguation(matches))
            return
        target = matches[0]
        # Fetch recent tickets and compute score
        today = date.today()
        start = today - timedelta(days=90)
        halo = st.session_state.halo_client
        data = halo.get_tickets(
            client_id=target["id"],
            start_date=start.strftime("%Y-%m-%d"),
            end_date=today.strftime("%Y-%m-%d"),
            page_size=500,
        )
        tickets = data.get("tickets", []) if isinstance(data, dict) else (data or [])
        if not tickets:
            _add_message(
                "assistant",
                f"No tickets found for **{target['name']}** in the last 90 days.",
            )
            return
        metrics = calculate_metrics(tickets)
        score = calculate_health_score(metrics)
        if score >= 80:
            label = "Excellent"
        elif score >= 50:
            label = "Needs Attention"
        else:
            label = "At Risk"
        _add_message(
            "assistant",
            f"**{target['name']}** health score (last 90 days): "
            f"**{score}** ({label})\n\n"
            f"- Same-Day Resolution: {metrics.get('{{SAME_DAY_RATE}}', 'N/A')}%\n"
            f"- Avg First Response: {metrics.get('{{AVG_FIRST_RESPONSE}}', 'N/A')}\n"
            f"- Critical Resolution: {metrics.get('{{CRITICAL_RES_TIME}}', 'N/A')}\n"
            f"- Proactive: {metrics.get('{{PROACTIVE_PERCENT}}', 'N/A')}%",
        )
        return

    if intent == Intent.GENERATE_QBR:
        if not st.session_state.authenticated:
            _add_message(
                "assistant",
                "Not connected to HaloPSA. Please configure credentials "
                "in Settings (gear icon).",
            )
            return

        # Merge params into state
        if params.get("client_name"):
            matches = resolve_client(params["client_name"], st.session_state.clients)
            if not matches:
                _add_message(
                    "assistant",
                    f"No client matching '{params['client_name']}' found. "
                    f"Try 'list clients' to see available clients.",
                )
                return
            if len(matches) == 1:
                state["client_id"] = matches[0]["id"]
                state["client_name"] = matches[0]["name"]
                # Load persisted profile
                profile = get_profile(matches[0]["id"])
                if profile["employee_count"] > 0:
                    state["employee_count"] = profile["employee_count"]
                    state["avg_hourly_rate"] = profile["avg_hourly_rate"]
                saved_industry = get_client_industry(matches[0]["id"])
                if saved_industry:
                    state["industry_name"] = saved_industry
                _add_message("assistant", f"Client: **{matches[0]['name']}**.")
            elif len(matches) > 1:
                state["awaiting"] = "disambiguation"
                state["pending_disambiguation"] = matches
                _add_message("assistant", format_disambiguation(matches))
                return

        if params.get("start_date"):
            state["start_date"] = params["start_date"].isoformat()
            state["end_date"] = params["end_date"].isoformat()

        if params.get("msp_contact"):
            state["msp_contact"] = params["msp_contact"]

        # Load persisted MSP contact if not already set
        if not state.get("msp_contact"):
            saved_contact = get_msp_contact()
            if saved_contact:
                state["msp_contact"] = saved_contact

        _check_and_prompt_missing(state)
        return

    # Unknown intent
    if st.session_state.anthropic_key:
        _add_message(
            "assistant",
            "I'm not sure what you mean. Type 'help' to see what I can do.",
        )
    else:
        _add_message("assistant", format_help_message())


def _check_and_prompt_missing(state: dict):
    """Check for missing required/optional fields, prompt or execute QBR."""
    # Check required fields
    missing = get_missing_fields(state)
    if missing:
        if "client" in missing.lower():
            state["awaiting"] = "client"
        elif "date" in missing.lower():
            state["awaiting"] = "date_range"
        elif "contact" in missing.lower():
            state["awaiting"] = "msp_contact"
        _add_message("assistant", missing)
        return

    # Check optional fields
    has_bea = bool(st.session_state.bea_key)
    optional = get_optional_prompts(state, has_bea)
    if optional:
        if "employee" in optional.lower():
            state["awaiting"] = "employee_count"
        elif "industry" in optional.lower():
            state["awaiting"] = "industry"
        _add_message("assistant", optional)
        return

    # All fields collected -- run QBR generation
    _execute_qbr(state)


def _execute_qbr(state: dict):
    """Execute the QBR generation pipeline with collected state."""
    from datetime import date as date_cls

    selected_client = {"id": state["client_id"], "name": state["client_name"]}
    start_date = date_cls.fromisoformat(state["start_date"])
    end_date = date_cls.fromisoformat(state["end_date"])

    _add_message(
        "assistant",
        f"Generating QBR for **{state['client_name']}** "
        f"({start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')})...",
    )

    pptx_bytes, filename, health_score = run_qbr_generation(
        selected_client=selected_client,
        start_date=start_date,
        end_date=end_date,
        msp_contact=state.get("msp_contact", ""),
        use_ai=st.session_state.use_ai,
        anthropic_key=st.session_state.anthropic_key,
        num_recs=st.session_state.num_recs,
        sample_size=st.session_state.sample_size,
        bea_api_key=st.session_state.bea_key,
        selected_industry_name=state.get("industry_name"),
        employee_count=state.get("employee_count", 0),
        avg_hourly_rate=state.get("avg_hourly_rate", 50.0),
    )

    if pptx_bytes:
        st.session_state.qbr_bytes = pptx_bytes
        st.session_state.qbr_filename = filename
        st.session_state.health_score = health_score
        st.session_state.results_visible = True
        st.session_state.results_collapsed = False
        _add_message(
            "assistant",
            f"QBR generated successfully for **{state['client_name']}**. "
            f"Download it from the Results panel.",
        )

    # Reset conv state for next QBR (keep persisted settings)
    st.session_state.conv_state = {}


# ─────────────────────────────────────────────
# AUTO-CONNECT ON LAUNCH
# ─────────────────────────────────────────────
if (
    not st.session_state.authenticated
    and not st.session_state.auto_connect_attempted
    and _env_halo_url
    and _env_client_id
    and _env_client_secret
):
    st.session_state.auto_connect_attempted = True
    success, error = try_authenticate(_env_halo_url, _env_client_id, _env_client_secret)
    if success:
        st.rerun()
    else:
        st.warning(
            f"Auto-connect failed: {error}. Open Settings to update credentials."
        )


# ─────────────────────────────────────────────
# UI LAYOUT
# ─────────────────────────────────────────────

# Page header with gear icon
header_col1, header_col2 = st.columns([9, 1])
with header_col1:
    st.title("MSP QBR Generator")
with header_col2:
    if st.button("", icon=":material/settings:", key="settings_btn"):
        settings_dialog()

# Connection status
if not st.session_state.authenticated:
    st.markdown(
        '<div class="connection-banner">'
        '<span class="banner-label">Not connected</span>'
        '<span class="banner-desc"> -- Open Settings (gear icon) to enter your '
        "HaloPSA credentials and connect.</span></div>",
        unsafe_allow_html=True,
    )

# ── Two-panel layout ──
has_results = st.session_state.qbr_bytes is not None

if has_results and st.session_state.results_visible:
    chat_col, results_col = st.columns([1, 1])
else:
    chat_col = st.container()
    results_col = None

# ── Chat Panel ──
with chat_col:
    # Welcome message if chat is empty
    if not st.session_state.chat_history:
        st.markdown(
            """<div class="chat-welcome-hero">
                <div class="hero-icon"><span>Q</span></div>
                <p class="hero-title">MSP QBR Generator</p>
                <p class="hero-subtitle">
                    Generate polished Quarterly Business Review decks, analyze client
                    health scores, and surface risk insights -- all through natural
                    language conversation.
                </p>
            </div>""",
            unsafe_allow_html=True,
        )

        # Example prompt buttons (styled as cards via CSS)
        with st.container(key="example_prompts"):
            ex_col1, ex_col2 = st.columns(2)
            with ex_col1:
                st.caption("REPORTS")
                if st.button(
                    "Generate a QBR for last quarter",
                    key="ex_qbr",
                    use_container_width=True,
                ):
                    _add_message("user", "Generate a QBR for last quarter")
                    _handle_chat_message("Generate a QBR for last quarter")
                    st.rerun()
                st.caption("CLIENTS")
                if st.button(
                    "List all clients",
                    key="ex_list",
                    use_container_width=True,
                ):
                    _add_message("user", "List all clients")
                    _handle_chat_message("List all clients")
                    st.rerun()
            with ex_col2:
                st.caption("HELP")
                if st.button(
                    "What can you do?",
                    key="ex_help",
                    use_container_width=True,
                ):
                    _add_message("user", "What can you do?")
                    _handle_chat_message("What can you do?")
                    st.rerun()
                st.caption("AI SETTINGS")
                if st.button(
                    "Enable AI with 5 recommendations",
                    key="ex_ai",
                    use_container_width=True,
                ):
                    _add_message("user", "Enable AI with 5 recommendations")
                    _handle_chat_message("Enable AI with 5 recommendations")
                    st.rerun()

    # Render chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Type a message..."):
        _add_message("user", prompt)
        _handle_chat_message(prompt)
        st.rerun()

# ── Results Panel ──
if results_col is not None:
    with results_col:
        _render_results_dashboard()
