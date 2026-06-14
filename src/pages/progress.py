import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone
from db import get_db_client, get_user_history, has_premium_access, is_authenticated, sign_out
# Bevar widget-keys frå hovudsida
from db import get_db_client, get_user_history, has_premium_access, is_authenticated, sign_out, get_user_profile

db_preserve = get_db_client()
if is_authenticated() and not st.session_state.get("profile_preserved"):
    _profile = get_user_profile(db_preserve)
    if _profile:
        for _k, _v in _profile.items():
            if _k not in st.session_state:
                st.session_state[_k] = _v
    st.session_state["profile_preserved"] = True

# --- Sidekonfigurasjon ---
st.set_page_config(
    page_title="My Progress",
    page_icon="📈",
    layout="centered",
)

# --- Innloggingssjekk (same som i app.py) ---
if not is_authenticated():
    st.warning("You must be logged in to see your progress.")
    st.info("Please go back to the main page and log in first.")
    st.stop()

# --- Brukar-ID frå session (sett ved innlogging) ---
user_id = st.session_state.get("user_id")
if not user_id:
    st.error("User ID not found. Please log in again.")
    st.stop()

# --- Sjekk premium (både session og database) ---
db = get_db_client()
_unlocked_session = st.session_state.get("report_unlocked", False)
_unlocked_db = has_premium_access(db)
is_premium = _unlocked_session or _unlocked_db

st.markdown("# 📈 My Progress")

if not is_premium:
    st.warning("This is a premium feature. Please upgrade to see your progress charts.")
    if st.button("🔓 Unlock full report — 4,99 USD", type="primary"):
    import requests as _requests
    _uid = st.session_state.get("user_id", "")
    _email = st.session_state.get("user_email", "")
    _supabase_url = st.secrets.get("SUPABASE_URL", "")
    _anon_key = st.secrets.get("SUPABASE_KEY", "")
    _fn_url = f"{_supabase_url}/functions/v1/stripe-checkout"
    try:
        _resp = _requests.post(
            _fn_url,
            json={"user_id": _uid, "email": _email},
            headers={
                "apikey": _anon_key,
                "Authorization": f"Bearer {_anon_key}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        _data = _resp.json()
        if "url" in _data:
            st.link_button("👉 Fortsett til betaling", _data["url"], type="primary")
        else:
            st.error("Kunne ikkje opprette betaling")
    except Exception as _e:
        st.error(f"Feil: {_e}")
    st.stop()

# --- Hent data ---
history = get_user_history(db)
if not history:
    st.info("No measurements saved yet. Go to the main page and calculate your health metrics first.")
    st.stop()

df = pd.DataFrame(history)
df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
df = df.sort_values("created_at").reset_index(drop=True)

# Sikre at kolonnar finst
for col in ["weight", "bmi", "vo2max", "bio_age", "weekly_activity_minutes", "resting_hr"]:
    if col not in df.columns:
        df[col] = None
    df[col] = pd.to_numeric(df[col], errors="coerce")

# --- Tidfilter ---
option = st.select_slider("Time range", ["Last 30 days", "Last 90 days", "Last year", "All time"])
days_map = {"Last 30 days": 30, "Last 90 days": 90, "Last year": 365, "All time": None}
days = days_map[option]
now_utc = datetime.now(timezone.utc)
if days:
    cutoff = now_utc - timedelta(days=days)
    df = df[df["created_at"] >= cutoff]

if df.empty:
    st.warning("No data in selected time range.")
    st.stop()

st.metric("Number of measurements", len(df))
st.markdown("---")

# --- Graf-funksjon (gjenbrukbar) ---
def plot_metric(df, col, title, unit, color, ref_line=None, ref_label=""):
    if col in df.columns and df[col].notna().any():
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["created_at"], y=df[col],
            mode="lines+markers", name=unit,
            line=dict(color=color, width=2),
            marker=dict(size=6)
        ))
        if ref_line is not None:
            fig.add_hline(y=ref_line, line_dash="dot", line_color="rgba(148,163,184,0.5)",
                          annotation_text=ref_label, annotation_font_color="#64748B")
        fig.update_layout(title=title, xaxis_title="Date", yaxis_title=unit,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption(f"No {title.lower()} data available yet.")

# --- Rad 1: Vekt + BMI ---
c1, c2 = st.columns(2)
with c1:
    plot_metric(df, "weight", "Weight", "kg", "#3B82F6")
with c2:
    plot_metric(df, "bmi", "BMI", "", "#0EA5A3", ref_line=25.0, ref_label="Overweight threshold")

# --- Rad 2: VO2max + Biologisk alder ---
c3, c4 = st.columns(2)
with c3:
    plot_metric(df, "vo2max", "VO₂max", "ml/kg/min", "#22C55E")
with c4:
    plot_metric(df, "bio_age", "Biological age", "years", "#EC4899")

# --- Rad 3: Ukentleg aktivitet + Kvilepuls ---
c5, c6 = st.columns(2)
with c5:
    plot_metric(df, "weekly_activity_minutes", "Weekly activity", "min", "#F59E0B",
                ref_line=150.0, ref_label="WHO goal: 150 min")
with c6:
    plot_metric(df, "resting_hr", "Resting heart rate", "bpm", "#F97316",
                ref_line=60.0, ref_label="Good: ≤60 bpm")

st.markdown("---")
st.caption("Measurements are saved each time you calculate on the main page. Log in to keep your data across devices.")
