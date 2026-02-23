"""
MSP QBR Generator - Streamlit Web App
Week 4: Full User Interface

Prerequisites:
    pip install streamlit python-pptx matplotlib requests python-dotenv

Usage:
    streamlit run app.py
"""

import streamlit as st
import tempfile
import os
import io
from datetime import datetime, timedelta, date

# Import modules from previous weeks
from halo_client import HaloClient
from generate_client_qbr import calculate_metrics, generate_qbr

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
):
    from recommendation_engine import generate_recommendations
    from generate_client_qbr import (
        calculate_metrics,
        generate_qbr,
        build_recommendation_replacements,
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
    st.caption("Your credentials are used only for this session and are never stored.")

    halo_url = st.text_input(
        "HaloPSA URL", placeholder="https://your-instance.halopsa.com"
    )
    client_id = st.text_input("Client ID", placeholder="Your API Client ID")
    client_secret = st.text_input(
        "Client Secret", placeholder="Your API Client Secret", type="password"
    )

    st.markdown("---")
    st.subheader("🤖 AI Recommendations")
    anthropic_api_key = st.text_input(
        "Anthropic API Key",
        placeholder="sk-ant-...",
        type="password",
        help="Your Anthropic API key. Used only for this session and never stored.",
    )
    use_ai_recommendations = st.toggle(
        "Generate AI Recommendations",
        value=True,
        help="Use Claude to generate strategic recommendations from ticket data.",
    )

    connect_btn = st.button("🔌 Connect to HaloPSA", use_container_width=True)

    if connect_btn:
        if not halo_url or not client_id or not client_secret:
            st.error("Please fill in all three fields.")
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

# ── Section 2: Recommendations ──
st.header("2. AI Recommendations Settings")

col_a, col_b = st.columns([1, 1])

with col_a:
    num_recs = st.slider(
        "Number of Recommendations",
        min_value=1,
        max_value=10,
        value=3,
        help="How many strategic recommendations Claude will generate.",
    )

with col_b:
    sample_size = st.slider(
        "Ticket Sample Size for AI Analysis",
        min_value=10,
        max_value=500,
        value=100,
        step=10,
        help="Number of recent ticket summaries to send to Claude for analysis.",
    )

# Fallback manual recommendations (shown only if AI is toggled off)
if not use_ai_recommendations:
    st.caption("Enter recommendations manually:")
    manual_recs = []
    for i in range(num_recs):
        manual_recs.append(
            st.text_input(f"Recommendation {i + 1}", key=f"manual_rec_{i}")
        )

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
    else:
        pptx_bytes, filename = run_qbr_generation(
            selected_client=selected_client,
            start_date=start_date,
            end_date=end_date,
            msp_contact=msp_contact,
            rec1=rec1,
            rec2=rec2,
            rec3=rec3,
        )

        if pptx_bytes:
            st.session_state.qbr_bytes = pptx_bytes
            st.session_state.qbr_filename = filename
            st.success(f"🎉 QBR generated successfully for **{selected_name}**!")

# ── Section 5: Download ──
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
