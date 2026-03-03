"""Settings page — AI recommendation tuning parameters."""

import streamlit as st

st.set_page_config(page_title="Settings", page_icon="⚙️")

# Initialise the persistent (non-widget) keys — only on first load
if "num_recs" not in st.session_state:
    st.session_state.num_recs = 3
if "sample_size" not in st.session_state:
    st.session_state.sample_size = 100

# Sync the widget shadow keys from the persistent keys
if "_num_recs_widget" not in st.session_state:
    st.session_state._num_recs_widget = st.session_state.num_recs
if "_sample_size_widget" not in st.session_state:
    st.session_state._sample_size_widget = st.session_state.sample_size


def _on_num_recs_change():
    st.session_state.num_recs = st.session_state._num_recs_widget


def _on_sample_size_change():
    st.session_state.sample_size = st.session_state._sample_size_widget


st.title("⚙️ Settings")
st.subheader("AI Recommendations")

st.slider(
    "Number of Recommendations",
    min_value=1,
    max_value=10,
    key="_num_recs_widget",
    on_change=_on_num_recs_change,
    help="How many strategic recommendations Claude will generate.",
)
st.slider(
    "Ticket Sample Size for AI Analysis",
    min_value=10,
    max_value=500,
    step=10,
    key="_sample_size_widget",
    on_change=_on_sample_size_change,
    help="Number of recent ticket summaries to send to Claude for analysis.",
)
