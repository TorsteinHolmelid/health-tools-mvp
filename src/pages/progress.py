import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from __future__ import annotations

import uuid
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone

try:
    from db import get_db_client, get_user_history, has_premium_access
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

st.set_page_config(
    page_title="My Progress",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
:root{
  --bg0:#070D18;--bg1:#0B1220;--card:rgba(15,23,42,.72);
  --stroke:rgba(148,163,184,.16);--stroke2:rgba(148,163,184,.10);
  --text:#E5E7EB;--muted:#94A3B8;--muted2:#A7B4C6;
  --accent:#0EA5A3;--accent2:#3B82F6;--good:#22C55E;
  --warn:#F59E0B;--bad:#EF4444;--radius:16px;
}
.stApp{
  background:
    radial-gradient(1200px 600px at 18% -10%,rgba(14,165,163,.20),transparent 60%),
    radial-gradient(900px 520px at 90% 0%,rgba(59,130,246,.15),transparent 55%),
    linear-gradient(180deg,var(--bg0),var(--bg1) 40%,#070B14);
  color:var(--text);
}
.block-container{max-width:980px;padding-top:1.35rem;padding-bottom:2.2rem;}
h1,h2,h3,p,label,li{color:var(--text)!important;}
small,.stCaption,[data-testid="stCaptionContainer"]{color:var(--muted)!important;}
.ht-hero{
  background:linear-gradient(135deg,rgba(14,165,163,.18),rgba(59,130,246,.12));
  border:1px solid var(--stroke);border-radius:calc(var(--radius)+6px);
  padding:18px 18px;box-shadow:0 18px 50px rgba(0,0,0,.25);
  backdrop-filter:blur(8px);margin-bottom:14px;
}
.ht-hero h1{margin:0;font-size:34px;letter-spacing:-0.02em;}
.ht-hero .sub{margin-top:6px;color:var(--muted2);font-size:13px;line-height:1.4;}
.ht-card{
  background:var(--card);border:1px solid var(--stroke);
  border-radius:var(--radius);padding:14px;
  box-shadow:0 12px 36px rgba(0,0,0,.22);backdrop-filter:blur(8px);margin-bottom:12px;
}
[data-testid="stMetric"]{
  background:rgba(15,23,42,.55);border:1px solid var(--stroke);
  border-radius:14px;padding:10px 12px;
}
</style>
""",
    unsafe_allow_html=True,
)

if "user_id" not in st.session_state:
    st.session_state["user_id"] = str(uuid.uuid4())
user_id = st.session_state["user_id"]

_session_id = None
try:
    _session_id = st.query_params.get("session_id")
except Exception:
    _session_id = None
if isinstance(_session_id, list):
    _session_id = _session_id[0] if _session_id else None

db = get_db_client()

if _session_id and (str(_session_id).startswith("cs_live_") or str(_session_id).startswith("cs_test_")):
    st.session_state["report_unlocked"] = True
    st.session_state["stripe_session_id"] = _session_id
    from db import save_premium_access
    save_premium_access(db, user_id, _session_id)

_unlocked_session = st.session_state.get("report_unlocked", False)
_unlocked_db = has_premium_access(db, user_id)
is_premium = _unlocked_session or _unlocked_db

st.markdown(
    """
<div class="ht-hero">
  <h1>My Progress</h1>
  <div class="sub">Track your health metrics over time and see how far you've come.</div>
</div>
""",
    unsafe_allow_html=True,
)

if not is_premium:
    st.markdown(
        """
<div style="background:linear-gradient(135deg,rgba(14,165,163,.10),rgba(59,130,246,.08));
     border:1px solid rgba(14,165,163,.35);border-radius:18px;padding:32px 24px;
     text-align:center;margin:24px 0;">
  <div style="font-size:48px;margin-bottom:12px;">🔒</div>
  <div style="font-size:22px;font-weight:800;color:#E5E7EB;margin-bottom:8px;">
    Premium Feature
  </div>
  <div style="color:#94A3B8;font-size:14px;line-height:1.7;max-width:460px;margin:0 auto 20px;">
    The <strong style="color:#E5E7EB;">My Progress</strong> dashboard is included with your
    one-time report purchase. Unlock it to visualise all your health metrics over time.
  </div>
  <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:10px;margin-bottom:24px;">
    <span style="background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.3);
    color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">Full progress charts</span>
    <span style="background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.3);
    color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">Trend insights</span>
    <span style="background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.3);
    color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">One-time payment</span>
  </div>
  <div style="font-size:30px;font-weight:800;color:#0EA5A3;margin-bottom:4px;">4.99 USD</div>
  <div style="color:#64748B;font-size:11px;margin-bottom:20px;">One-time · No subscription</div>
</div>
""",
        unsafe_allow_html=True,
    )
    stripe_link = "https://buy.stripe.com/fZu00kbeq6J50LsdYk1Fe02"
    st.link_button("Unlock My Progress — 4.99 USD", stripe_link, type="primary", use_container_width=True)
    st.caption("After payment you will be redirected back here automatically.")
    st.stop()

history = get_user_history(db, user_id)
if not history:
    st.info("No measurements saved yet. Go back to the main page and calculate.")
    st.stop()

df = pd.DataFrame(history)
df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
df = df.dropna(subset=["created_at"]).sort_values("created_at").reset_index(drop=True)

numeric_cols = ["weight", "bmi", "vo2max", "bio_age", "weekly_activity_minutes", "resting_hr"]
for col in numeric_cols:
    if col not in df.columns:
        df[col] = float("nan")
    df[col] = pd.to_numeric(df[col], errors="coerce")

FILTER_OPTIONS = {"Last 30 days": 30, "Last 90 days": 90, "Last year": 365, "All time": None}
now_utc = datetime.now(timezone.utc)

col_filter, col_count = st.columns([2,1])
with col_filter:
    selected_range = st.select_slider("Time range", options=list(FILTER_OPTIONS.keys()), value="Last 90 days", label_visibility="collapsed")
days_back = FILTER_OPTIONS[selected_range]
if days_back:
    cutoff = now_utc - timedelta(days=days_back)
    df_view = df[df["created_at"] >= cutoff].copy()
else:
    df_view = df.copy()
with col_count:
    st.metric("Measurements", len(df_view))

if df_view.empty:
    st.warning("No measurements in selected range.")
    st.stop()

st.markdown('<div class="ht-card">', unsafe_allow_html=True)
m1,m2,m3,m4 = st.columns(4)

def _delta(series):
    valid = series.dropna()
    if valid.empty:
        return None, None
    latest = valid.iloc[-1]
    if len(valid) < 2:
        return latest, None
    delta = latest - valid.iloc[0]
    return latest, f"{delta:+.1f}"

w_val,w_delta = _delta(df_view["weight"])
bmi_val,bmi_delta = _delta(df_view["bmi"])
vo2_val,vo2_delta = _delta(df_view["vo2max"])
bio_val,bio_delta = _delta(df_view["bio_age"])

with m1:
    st.metric("Weight (kg)", f"{w_val:.1f}" if w_val else "--", w_delta)
with m2:
    st.metric("BMI", f"{bmi_val:.1f}" if bmi_val else "--", bmi_delta)
with m3:
    st.metric("VO2max", f"{vo2_val:.1f}" if vo2_val else "--", vo2_delta)
with m4:
    st.metric("Bio Age", f"{bio_val:.0f}" if bio_val else "--", bio_delta)
st.markdown("</div>", unsafe_allow_html=True)

# Enkel testgraf for å sjå om plotting fungerer
if not df_view["weight"].dropna().empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_view["created_at"], y=df_view["weight"], mode='lines+markers'))
    fig.update_layout(title="Weight over time", height=300)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.write("Ingen vektdata å vise.")
