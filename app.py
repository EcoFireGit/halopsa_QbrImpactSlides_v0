"""
MSP QBR Generator - Streamlit Web App
Week 4: Full User Interface

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

from generate_client_qbr import calculate_metrics, generate_qbr
from halo_client import HaloClient

# Load .env from the current working directory (values are fallbacks if not
# entered by the user in the sidebar).
load_dotenv()

# ─────────────────────────────────────────────
# ENV DEFAULTS (used to pre-fill sidebar fields)
# ─────────────────────────────────────────────
_env_halo_url = os.environ.get("HALO_HOST", "")
_env_client_id = os.environ.get("CLIENT_ID", "")
_env_client_secret = os.environ.get("CLIENT_SECRET", "")
_env_anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
_env_bea_key = os.environ.get("BEA_API_KEY", "")

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="MSP QBR Generator", page_icon="📊", layout="wide")

# ─────────────────────────────────────────────
# SESSION STATE INITIALISATION
# ─────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "clients" not in st.session_state:
    st.session_state.clients = []
if "halo_client" not in st.session_state:
    st.session_state.halo_client = None
if "qbr_bytes" not in st.session_state:
    st.session_state.qbr_bytes = None
if "qbr_filename" not in st.session_state:
    st.session_state.qbr_filename = "QBR_Report.pptx"
if "bea_insights" not in st.session_state:
    st.session_state.bea_insights = None
if "bea_industry_name" not in st.session_state:
    st.session_state.bea_industry_name = None
if "num_recs" not in st.session_state:
    st.session_state.num_recs = 3
if "sample_size" not in st.session_state:
    st.session_state.sample_size = 100


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────
def try_authenticate(halo_url, client_id, client_secret):
    """Attempts to authenticate and fetch clients. Returns (success, error_msg)."""
    try:
        # Temporarily override env vars with form values
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

    st.subheader("📈 Industry Economic Context (BEA)")

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
        # Convert millions → billions
        chart_values_b = [v / 1000 for v in chart_values]

        fig, ax = plt.subplots(figsize=(9, 2.5))
        ax.plot(chart_labels, chart_values_b, marker="o", color="#2E5C8A", linewidth=2)
        ax.fill_between(chart_labels, chart_values_b, alpha=0.15, color="#2E5C8A")
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
    with st.spinner("📡 Fetching tickets from HaloPSA..."):
        data = client.get_tickets(
            client_id=client_id,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            page_size=500,
        )
        tickets = data.get("tickets", []) if isinstance(data, dict) else (data or [])

    if not tickets:
        st.warning(
            f"⚠️ No tickets found for **{client_name}** in the selected date range."
        )
        return None, None

    st.info(f"✅ Retrieved **{len(tickets)}** tickets.")

    # 2. Compute metrics
    metrics_data = calculate_metrics(tickets)

    # 2.5 Fetch BEA economic context (optional)
    bea_replacements = build_empty_bea_replacements()
    if bea_api_key and selected_industry_name:
        with st.spinner(f"📊 Fetching BEA data for {selected_industry_name}..."):
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
        with st.spinner(f"🤖 Asking Claude to generate {num_recs} recommendations..."):
            # Sample the most recent tickets up to sample_size
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
                st.success(
                    f"✅ Claude generated {len(recommendations)} recommendations."
                )

            except Exception as e:
                st.error(f"❌ Claude API error: {e}")
                return None, None
    else:
        # Use manual recommendations
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
    with st.spinner("🛠️ Generating PowerPoint..."):
        template_path = "Master_QBR_Template.pptx"
        if not os.path.exists(template_path):
            st.error("❌ Master_QBR_Template.pptx not found.")
            return None, None

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
    return pptx_bytes, filename


# ─────────────────────────────────────────────
# UI LAYOUT
# ─────────────────────────────────────────────
st.title("📊 MSP QBR Generator")
st.caption(
    "Connect to your HaloPSA instance, select a client and date range, and generate a business impact report in one click."
)

# ═══════════════════════════
# SIDEBAR: Credentials
# ═══════════════════════════
with st.sidebar:
    st.header("🔐 HaloPSA Connection")
    st.caption(
        "All fields are optional if the corresponding values are set in a `.env` file "
        "in the working directory. Entered values take precedence over `.env`."
    )

    halo_url = st.text_input(
        "HaloPSA URL",
        value=_env_halo_url,
        placeholder="https://your-instance.halopsa.com",
    )
    client_id = st.text_input(
        "Client ID",
        value=_env_client_id,
        placeholder="Your API Client ID",
    )
    client_secret = st.text_input(
        "Client Secret",
        value=_env_client_secret,
        placeholder="Your API Client Secret",
        type="password",
    )

    st.markdown("---")
    st.subheader("🤖 AI Recommendations")
    anthropic_api_key = st.text_input(
        "Anthropic API Key",
        value=_env_anthropic_key,
        placeholder="sk-ant-...",
        type="password",
        help="Used only for this session. Leave blank to use ANTHROPIC_API_KEY from .env.",
    )
    use_ai_recommendations = st.toggle(
        "Generate AI Recommendations",
        value=True,
        help="Use Claude to generate strategic recommendations from ticket data.",
    )
    st.caption("Configure recommendation count and sample size in ⚙️ Settings.")

    if not use_ai_recommendations:
        st.caption("Enter recommendations manually:")
        manual_recs = []
        for i in range(st.session_state.num_recs):
            manual_recs.append(
                st.text_input(f"Recommendation {i + 1}", key=f"manual_rec_{i}")
            )

    st.markdown("---")
    st.subheader("📈 Economic Context (BEA)")
    bea_api_key = st.text_input(
        "BEA API Key",
        value=_env_bea_key,
        placeholder="Get free key at apps.bea.gov/api/signup",
        type="password",
        help="Optional. Free registration at apps.bea.gov/api/signup. Leave blank to use BEA_API_KEY from .env.",
    )

    connect_btn = st.button("🔌 Connect to HaloPSA", use_container_width=True)

    if connect_btn:
        if not halo_url or not client_id or not client_secret:
            st.error(
                "HaloPSA URL, Client ID, and Client Secret are required. "
                "Enter them above or set HALO_HOST, CLIENT_ID, and CLIENT_SECRET in your .env file."
            )
        else:
            with st.spinner("Connecting..."):
                success, error = try_authenticate(halo_url, client_id, client_secret)
            if success:
                st.success(
                    f"✅ Connected! {len(st.session_state.clients)} clients found."
                )
            else:
                st.error(f"❌ Connection failed: {error}")

    # Status indicator
    if st.session_state.authenticated:
        st.markdown("---")
        st.markdown("🟢 **Status:** Connected")
    else:
        st.markdown("---")
        st.markdown("🔴 **Status:** Not Connected")

# ═══════════════════════════
# MAIN AREA
# ═══════════════════════════
if not st.session_state.authenticated:
    st.info(
        "👈 Enter your HaloPSA credentials in the sidebar and click **Connect** to get started."
    )
    st.stop()

# ── Section 1: Client & Date Selection ──
st.header("1. Select Client & Date Range")

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

    # Validate the date range
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        st.warning("Please select both a start and end date.")
        st.stop()

# ── Section 2: Economic Context ──
st.header("2. Economic Context (Optional)")
if bea_api_key:
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
    st.info("Enter a BEA API key in the sidebar to include industry economic context.")

# ── Section 3: MSP Contact Info ──
st.header("3. MSP Contact Info")
msp_contact = st.text_input(
    "Account Manager Contact",
    placeholder="Jane Doe | jdoe@yourmsp.com | (555) 123-4567",
)

# ── Section 4: Generate ──
st.markdown("---")
st.header("4. Generate QBR")

generate_btn = st.button(
    "🚀 Generate QBR Report", type="primary", use_container_width=True
)

if generate_btn:
    if not msp_contact:
        st.warning("Please enter your MSP contact information before generating.")
    elif start_date >= end_date:
        st.warning("Start date must be before end date.")
    elif use_ai_recommendations and not anthropic_api_key:
        st.warning(
            "An Anthropic API key is required for AI Recommendations. "
            "Enter it in the sidebar or set ANTHROPIC_API_KEY in your .env file, "
            "or toggle off AI Recommendations."
        )
    else:
        # Build manual recommendations list if AI is toggled off
        manual_recs = None
        if not use_ai_recommendations:
            manual_recs = [
                st.session_state.get(f"manual_rec_{i}", "")
                for i in range(st.session_state.num_recs)
            ]

        pptx_bytes, filename = run_qbr_generation(
            selected_client=selected_client,
            start_date=start_date,
            end_date=end_date,
            msp_contact=msp_contact,
            use_ai=use_ai_recommendations,
            anthropic_key=anthropic_api_key,
            num_recs=st.session_state.num_recs,
            sample_size=st.session_state.sample_size,
            manual_recs=manual_recs,
            bea_api_key=bea_api_key,
            selected_industry_name=selected_industry_name,
        )

        if pptx_bytes:
            st.session_state.qbr_bytes = pptx_bytes
            st.session_state.qbr_filename = filename
            st.success(f"🎉 QBR generated successfully for **{selected_name}**!")

            if st.session_state.bea_insights:
                _render_bea_panel(
                    st.session_state.bea_insights,
                    st.session_state.bea_industry_name,
                )

# ── Section 6: Download ──
if st.session_state.qbr_bytes:
    st.markdown("---")
    st.download_button(
        label="⬇️ Download PowerPoint QBR",
        data=st.session_state.qbr_bytes,
        file_name=st.session_state.qbr_filename,
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        use_container_width=True,
    )
    st.caption(f"📁 File: `{st.session_state.qbr_filename}`")
