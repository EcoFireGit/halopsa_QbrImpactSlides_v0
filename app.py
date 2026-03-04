"""
MSP QBR Generator - Streamlit Web App
Branded UI with settings dialog, auto-connect, and dashboard results.

Prerequisites:
    pip install streamlit python-pptx matplotlib requests python-dotenv

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

# Load .env from the current working directory (values are fallbacks if not
# entered by the user in the sidebar).
load_dotenv()

# ─────────────────────────────────────────────
# ENV DEFAULTS (used to pre-fill settings fields)
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
# CUSTOM CSS — Brand Colors & Layout
# ─────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Hide sidebar completely */
    [data-testid="stSidebar"] { display: none; }
    section[data-testid="stSidebarNav"] { display: none; }

    /* Brand headers */
    h1, h2, h3 { color: #242E65 !important; }

    /* Orange accent dividers */
    hr { border-color: #F05523 !important; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #F0F1F8;
        border-left: 4px solid #F05523;
        padding: 0.75rem 1rem;
        border-radius: 6px;
    }

    /* Download button */
    [data-testid="stDownloadButton"] > button {
        background-color: #242E65 !important;
        color: white !important;
        border: 2px solid #F05523 !important;
    }
    [data-testid="stDownloadButton"] > button:hover {
        background-color: #1a2150 !important;
    }

    /* Minimal gear button */
    button[data-testid="stBaseButton-secondary"][kind="secondary"] {
        border: none;
        background: transparent;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# SESSION STATE INITIALISATION
# ─────────────────────────────────────────────
_defaults = {
    "authenticated": False,
    "clients": [],
    "halo_client": None,
    "qbr_bytes": None,
    "qbr_filename": "QBR_Report.pptx",
    "bea_insights": None,
    "bea_industry_name": None,
    "num_recs": 3,
    "sample_size": 100,
    "health_score": None,
    "metrics_display": None,
    # Settings dialog values (pre-filled from .env)
    "halo_url": _env_halo_url,
    "client_id_val": _env_client_id,
    "client_secret_val": _env_client_secret,
    "anthropic_key": _env_anthropic_key,
    "bea_key": _env_bea_key,
    "use_ai": True,
    "auto_connect_attempted": False,
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


def _render_bea_panel(insights: dict, industry_name: str):
    """Render the BEA economic context panel: metrics + trend chart."""
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

    # Trend chart
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
        ax.set_title(f"{industry_name} — 8-Quarter GDP Trend", fontsize=10)
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
        <div style="display:inline-block;background-color:{color};color:white;
                    font-size:2.5rem;font-weight:bold;padding:0.3rem 1rem;
                    border-radius:8px;line-height:1.2;">
            {score}
        </div>
        <span style="font-size:1.1rem;color:{color};font-weight:600;
                     margin-left:0.75rem;vertical-align:middle;">
            {label}
        </span>""",
        unsafe_allow_html=True,
    )


def _render_results_dashboard():
    """Render the dashboard-style results view after QBR generation."""
    st.markdown("---")

    # Download button — prominent, at top
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
):
    from recommendation_engine import generate_recommendations
    from generate_client_qbr import (
        build_recommendation_replacements,
    )
    from bea_client import BEAClient
    from bea_insights import (
        INDUSTRY_SECTORS,
        calculate_sector_growth,
        format_bea_replacements,
        build_empty_bea_replacements,
    )

    client = st.session_state.halo_client
    client_id = selected_client["id"]
    client_name = selected_client["name"]
    review_period = (
        f"{start_date.strftime('%B %d, %Y')} – {end_date.strftime('%B %d, %Y')}"
    )

    # 1. Fetch tickets
    with st.spinner("Fetching tickets from HaloPSA..."):
        data = client.get_tickets(
            client_id=client_id,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            page_size=500,
        )
        tickets = data.get("tickets", []) if isinstance(data, dict) else (data or [])

    if not tickets:
        st.warning(
            f"No tickets found for **{client_name}** in the selected date range."
        )
        return None, None, None

    if use_ai and anthropic_key and len(tickets) > sample_size:
        st.info(
            f"Retrieved **{len(tickets)}** tickets "
            f"(**{sample_size}** will be sampled for AI analysis)."
        )
    else:
        st.info(f"Retrieved **{len(tickets)}** tickets.")

    # 2. Compute metrics
    metrics_data = calculate_metrics(tickets)
    health_score = calculate_health_score(metrics_data)

    # Store metrics for dashboard display
    st.session_state.metrics_display = metrics_data

    # 2.5 Fetch BEA economic context (optional)
    bea_replacements = build_empty_bea_replacements()
    if bea_api_key and selected_industry_name:
        with st.spinner(f"Fetching BEA data for {selected_industry_name}..."):
            try:
                bea_client = BEAClient(api_key=bea_api_key)
                raw_rows = bea_client.get_gdp_by_industry(
                    INDUSTRY_SECTORS[selected_industry_name], num_quarters=8
                )
                insights = calculate_sector_growth(raw_rows)
                bea_replacements = format_bea_replacements(
                    selected_industry_name, insights
                )
                st.session_state.bea_insights = insights
                st.session_state.bea_industry_name = selected_industry_name
            except (ValueError, Exception) as e:
                st.warning(
                    f"BEA data unavailable: {e}. QBR proceeds without economic context."
                )

    # 3. Generate recommendations
    if use_ai and anthropic_key:
        with st.spinner(f"Asking Claude to generate {num_recs} recommendations..."):
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
                )
                st.success(f"Claude generated {len(recommendations)} recommendations.")

            except Exception as e:
                st.error(f"Claude API error: {e}")
                return None, None, None
    else:
        recommendations = [
            {"title": f"Recommendation {i + 1}", "rationale": rec}
            for i, rec in enumerate(manual_recs or [])
            if rec
        ]

    # 4. Build all replacement data
    rec_replacements = build_recommendation_replacements(recommendations)
    contextual_data = {
        "{{CLIENT_NAME}}": client_name,
        "{{REVIEW_PERIOD}}": review_period,
        "{{CHART_PLACEHOLDER}}": "",
        "{{MSP_CONTACT_INFO}}": msp_contact,
        **rec_replacements,
        **bea_replacements,
    }

    # 5. Generate PPTX
    with st.spinner("Generating PowerPoint..."):
        template_path = "Master_QBR_Template.pptx"
        if not os.path.exists(template_path):
            st.error("Master_QBR_Template.pptx not found.")
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
# SETTINGS DIALOG
# ─────────────────────────────────────────────
@st.dialog("Settings", width="large")
def settings_dialog():
    st.subheader("HaloPSA Connection")
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
    st.subheader("AI Recommendations")
    anthropic_key = st.text_input(
        "Anthropic API Key",
        value=st.session_state.anthropic_key,
        placeholder="sk-ant-...",
        type="password",
        help="Used only for this session. Leave blank to use ANTHROPIC_API_KEY from .env.",
    )
    use_ai = st.toggle(
        "Generate AI Recommendations",
        value=st.session_state.use_ai,
        help="Use Claude to generate strategic recommendations from ticket data.",
    )

    num_recs = st.slider(
        "Number of Recommendations",
        min_value=1,
        max_value=10,
        value=st.session_state.num_recs,
        help="How many strategic recommendations Claude will generate.",
    )
    sample_size = st.slider(
        "Ticket Sample Size for AI Analysis",
        min_value=10,
        max_value=500,
        step=10,
        value=st.session_state.sample_size,
        help="Number of recent ticket summaries to send to Claude for analysis.",
    )

    st.markdown("---")
    st.subheader("Economic Context (BEA)")
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
            st.session_state.use_ai = use_ai
            st.session_state.num_recs = num_recs
            st.session_state.sample_size = sample_size
            st.session_state.bea_key = bea_key
            st.rerun()
    with btn_col2:
        if st.button("Connect to HaloPSA", use_container_width=True):
            if not halo_url or not client_id or not client_secret:
                st.error("HaloPSA URL, Client ID, and Client Secret are required.")
            else:
                # Save values first
                st.session_state.halo_url = halo_url
                st.session_state.client_id_val = client_id
                st.session_state.client_secret_val = client_secret
                st.session_state.anthropic_key = anthropic_key
                st.session_state.use_ai = use_ai
                st.session_state.num_recs = num_recs
                st.session_state.sample_size = sample_size
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
    st.caption(
        "Connect to your HaloPSA instance, select a client and date range, "
        "and generate a business impact report in one click."
    )
with header_col2:
    if st.button("", icon=":material/settings:", key="settings_btn"):
        settings_dialog()

# Connection status
if st.session_state.authenticated:
    st.success(
        f"Connected to HaloPSA — {len(st.session_state.clients)} clients available"
    )
else:
    st.info("Open Settings (gear icon) to enter your HaloPSA credentials and connect.")
    st.stop()

# ── Section 1: Client & Date Range ──
with st.expander("1. Client & Date Range", expanded=True):
    col1, col2 = st.columns([1, 1])

    with col1:
        client_options = {c["name"]: c for c in st.session_state.clients}
        selected_name = st.selectbox(
            "Client",
            options=list(client_options.keys()),
            help="Select the client for whom you want to generate the QBR.",
        )
        selected_client = client_options[selected_name]

    with col2:
        default_end = date.today()
        default_start = default_end - timedelta(days=90)

        date_range = st.date_input(
            "Review Period",
            value=(default_start, default_end),
            help="Select the start and end date for the QBR review period.",
        )

        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            st.warning("Please select both a start and end date.")
            st.stop()

# ── Section 2: Economic Context ──
with st.expander("2. Economic Context (Optional)", expanded=True):
    if st.session_state.bea_key:
        from bea_insights import INDUSTRY_SECTORS

        selected_industry_name = st.selectbox(
            "Client's Industry Sector",
            options=list(INDUSTRY_SECTORS.keys()),
            index=0,
            key=f"bea_industry_{selected_client['id']}",
        )
        st.caption(f"BEA sector code: `{INDUSTRY_SECTORS[selected_industry_name]}`")
    else:
        selected_industry_name = None
        st.info("Enter a BEA API key in Settings to include industry economic context.")

# ── Section 3: MSP Contact Info & Manual Recommendations ──
with st.expander("3. MSP Contact Info", expanded=True):
    msp_contact = st.text_input(
        "Account Manager Contact",
        placeholder="Jane Doe | jdoe@yourmsp.com | (555) 123-4567",
    )

    if not st.session_state.use_ai:
        st.markdown("---")
        st.markdown("**Manual Recommendations**")
        st.caption(
            "AI recommendations are disabled. Enter recommendations manually below."
        )
        manual_recs_list = []
        for i in range(st.session_state.num_recs):
            manual_recs_list.append(
                st.text_input(f"Recommendation {i + 1}", key=f"manual_rec_{i}")
            )

# ── Section 4: Generate QBR ──
with st.expander("4. Generate QBR", expanded=True):
    generate_btn = st.button(
        "Generate QBR Report", type="primary", use_container_width=True
    )

    if generate_btn:
        if not msp_contact:
            st.warning("Please enter your MSP contact information before generating.")
        elif start_date >= end_date:
            st.warning("Start date must be before end date.")
        elif st.session_state.use_ai and not st.session_state.anthropic_key:
            st.warning(
                "An Anthropic API key is required for AI Recommendations. "
                "Enter it in Settings, or toggle off AI Recommendations."
            )
        else:
            manual_recs = None
            if not st.session_state.use_ai:
                manual_recs = [
                    st.session_state.get(f"manual_rec_{i}", "")
                    for i in range(st.session_state.num_recs)
                ]

            pptx_bytes, filename, health_score = run_qbr_generation(
                selected_client=selected_client,
                start_date=start_date,
                end_date=end_date,
                msp_contact=msp_contact,
                use_ai=st.session_state.use_ai,
                anthropic_key=st.session_state.anthropic_key,
                num_recs=st.session_state.num_recs,
                sample_size=st.session_state.sample_size,
                manual_recs=manual_recs,
                bea_api_key=st.session_state.bea_key,
                selected_industry_name=selected_industry_name,
            )

            if pptx_bytes:
                st.session_state.qbr_bytes = pptx_bytes
                st.session_state.qbr_filename = filename
                st.session_state.health_score = health_score
                st.success(f"QBR generated successfully for **{selected_name}**!")

# ── Results Dashboard ──
if st.session_state.qbr_bytes:
    _render_results_dashboard()
