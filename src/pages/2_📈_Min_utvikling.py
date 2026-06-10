import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # legg til src-mappa i sti
"""
pages/2_📈_Min_utvikling.py  –  "My Progress" page
Shows time-series charts for all key health metrics stored in Supabase.
Requires the user to have paid (premium_access table) to view the full page.
"""
from __future__ import annotations

import uuid
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta, timezone

from db import get_db_client, get_user_history, has_premium_access

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="My Progress · Health Tools",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Shared CSS (mirrors main app) ─────────────────────────────────────────────
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

# ── Session state ─────────────────────────────────────────────────────────────
if "user_id" not in st.session_state:
    st.session_state["user_id"] = str(uuid.uuid4())

user_id: str = st.session_state["user_id"]

# ── Stripe callback: persist premium access ───────────────────────────────────
_session_id = None
try:
    _session_id = st.query_params.get("session_id")
except Exception:
    try:
        _raw = st.experimental_get_query_params().get("session_id")
        _session_id = _raw[0] if isinstance(_raw, list) else _raw
    except Exception:
        _session_id = None
if isinstance(_session_id, list):
    _session_id = _session_id[0] if _session_id else None

db = get_db_client()

if _session_id and (
    str(_session_id).startswith("cs_live_") or str(_session_id).startswith("cs_test_")
):
    st.session_state["report_unlocked"] = True
    st.session_state["stripe_session_id"] = _session_id
    # Persist to DB so they keep access across devices / sessions
    from db import save_premium_access
    save_premium_access(db, user_id, _session_id)

# ── Premium check ─────────────────────────────────────────────────────────────
# Allow access if: paid via Stripe this session OR row exists in premium_access
_unlocked_session = st.session_state.get("report_unlocked", False)
_unlocked_db = has_premium_access(db, user_id)
is_premium = _unlocked_session or _unlocked_db

# ── Hero header ───────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="ht-hero">
  <h1>📈 My Progress</h1>
  <div class="sub">Track your health metrics over time and see how far you've come.</div>
</div>
""",
    unsafe_allow_html=True,
)

# ── PAYWALL ───────────────────────────────────────────────────────────────────
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
    one-time report purchase. Unlock it to visualise all your health metrics over time —
    weight, BMI, VO₂max, biological age, activity minutes and resting heart rate.
  </div>
  <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:10px;margin-bottom:24px;">
    <span style="background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.3);
    color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">✅ Full progress charts</span>
    <span style="background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.3);
    color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">✅ Trend insights</span>
    <span style="background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.3);
    color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">✅ PDF report</span>
    <span style="background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.3);
    color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">✅ One-time payment</span>
  </div>
  <div style="font-size:30px;font-weight:800;color:#0EA5A3;margin-bottom:4px;">4.99 USD</div>
  <div style="color:#64748B;font-size:11px;margin-bottom:20px;">One-time · No subscription</div>
</div>
""",
        unsafe_allow_html=True,
    )

    stripe_link = "https://buy.stripe.com/fZu00kbeq6J50LsdYk1Fe02"
    st.link_button(
        "🔓 Unlock My Progress — 4.99 USD",
        stripe_link,
        type="primary",
        use_container_width=True,
    )
    st.caption("After payment you will be redirected back here automatically.")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
history = get_user_history(db, user_id)

if not history:
    st.info(
        "📭 No measurements saved yet. Go back to the main page, fill in your details "
        "and hit **Calculate / Generate report** — your results will be stored automatically."
    )
    st.stop()

# ── Build DataFrame ───────────────────────────────────────────────────────────
df = pd.DataFrame(history)

# Parse timestamps robustly
df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
df = df.dropna(subset=["created_at"]).sort_values("created_at").reset_index(drop=True)

# Ensure numeric columns exist (fill with NaN if DB column absent)
numeric_cols = ["weight", "bmi", "vo2max", "bio_age", "weekly_activity_minutes", "resting_hr"]
for col in numeric_cols:
    if col not in df.columns:
        df[col] = float("nan")
    df[col] = pd.to_numeric(df[col], errors="coerce")

# ── Time filter ───────────────────────────────────────────────────────────────
FILTER_OPTIONS = {
    "Last 30 days": 30,
    "Last 90 days": 90,
    "Last year": 365,
    "All time": None,
}

now_utc = datetime.now(timezone.utc)

col_filter, col_count = st.columns([2, 1])
with col_filter:
    selected_range = st.select_slider(
        "Time range",
        options=list(FILTER_OPTIONS.keys()),
        value="Last 90 days",
        label_visibility="collapsed",
    )

days_back = FILTER_OPTIONS[selected_range]
if days_back:
    cutoff = now_utc - timedelta(days=days_back)
    df_view = df[df["created_at"] >= cutoff].copy()
else:
    df_view = df.copy()

with col_count:
    st.metric("Measurements", len(df_view))

if df_view.empty:
    st.warning(f"No measurements found for **{selected_range}**. Try expanding the time range.")
    st.stop()

# ── Summary stats row ─────────────────────────────────────────────────────────
st.markdown('<div class="ht-card">', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)

def _delta(series: pd.Series):
    """Return (latest, delta_str) for a metric series, ignoring NaNs."""
    valid = series.dropna()
    if valid.empty:
        return None, None
    latest = valid.iloc[-1]
    if len(valid) < 2:
        return latest, None
    delta = latest - valid.iloc[0]
    return latest, f"{delta:+.1f}"

w_val, w_delta = _delta(df_view["weight"])
bmi_val, bmi_delta = _delta(df_view["bmi"])
vo2_val, vo2_delta = _delta(df_view["vo2max"])
bio_val, bio_delta = _delta(df_view["bio_age"])

with m1:
    st.metric("Weight (kg)", f"{w_val:.1f}" if w_val else "—", w_delta)
with m2:
    st.metric("BMI", f"{bmi_val:.1f}" if bmi_val else "—", bmi_delta)
with m3:
    st.metric("VO₂max", f"{vo2_val:.1f}" if vo2_val else "—", vo2_delta)
with m4:
    st.metric("Bio Age", f"{bio_val:.0f}" if bio_val else "—", bio_delta)

st.markdown("</div>", unsafe_allow_html=True)

# ── Shared chart style ────────────────────────────────────────────────────────
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94A3B8", size=11),
    margin=dict(l=10, r=10, t=36, b=10),
    height=260,
    xaxis=dict(
        showgrid=False,
        zeroline=False,
        color="#64748B",
        tickfont=dict(color="#64748B"),
    ),
    yaxis=dict(
        gridcolor="rgba(148,163,184,0.08)",
        zeroline=False,
        color="#64748B",
        tickfont=dict(color="#64748B"),
    ),
    hovermode="x unified",
)

ACCENT = "#0EA5A3"
BLUE = "#3B82F6"
YELLOW = "#F59E0B"
GREEN = "#22C55E"
PINK = "#EC4899"
ORANGE = "#F97316"


def _line_chart(
    series: pd.Series,
    title: str,
    unit: str,
    color: str = ACCENT,
    fill: bool = True,
    reference_line: float | None = None,
    ref_label: str = "",
):
    """Render a single metric over time as a Plotly line chart."""
    plot_df = df_view[["created_at"]].copy()
    plot_df["value"] = series.values
    plot_df = plot_df.dropna(subset=["value"])

    if plot_df.empty:
        st.caption(f"No data available for {title}.")
        return

    fig = go.Figure()

    # Gradient fill under line
    if fill:
        fig.add_trace(
            go.Scatter(
                x=plot_df["created_at"],
                y=plot_df["value"],
                fill="tozeroy",
                mode="none",
                fillcolor=color.replace(")", ",0.10)").replace("rgb", "rgba")
                if "rgb" in color
                else f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.10)",
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # Main line
    fig.add_trace(
        go.Scatter(
            x=plot_df["created_at"],
            y=plot_df["value"],
            mode="lines+markers",
            line=dict(color=color, width=2.5),
            marker=dict(color=color, size=6, line=dict(color="#0B1220", width=1.5)),
            name=unit,
            hovertemplate=f"<b>%{{y:.1f}} {unit}</b><br>%{{x|%b %d, %Y}}<extra></extra>",
        )
    )

    # Optional reference / target line
    if reference_line is not None:
        fig.add_hline(
            y=reference_line,
            line_dash="dot",
            line_color="rgba(148,163,184,0.35)",
            annotation_text=ref_label,
            annotation_font_color="#64748B",
            annotation_font_size=10,
        )

    layout = dict(CHART_LAYOUT)
    layout["title"] = dict(text=title, font=dict(color="#E5E7EB", size=14), x=0)
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Charts ────────────────────────────────────────────────────────────────────

st.markdown("---")

# Row 1: Weight + BMI
c1, c2 = st.columns(2)
with c1:
    _line_chart(df_view["weight"], "⚖️ Weight over time", "kg", color=BLUE)
with c2:
    _line_chart(
        df_view["bmi"],
        "📐 BMI over time",
        "BMI",
        color=ACCENT,
        reference_line=25.0,
        ref_label="BMI 25 (overweight threshold)",
    )

# Row 2: VO2max + Bio Age
c3, c4 = st.columns(2)
with c3:
    _line_chart(df_view["vo2max"], "🫁 VO₂max over time", "ml/kg/min", color=GREEN)
with c4:
    _line_chart(df_view["bio_age"], "🧬 Biological Age over time", "yrs", color=PINK)

# Row 3: Weekly activity minutes + Resting HR
c5, c6 = st.columns(2)
with c5:
    # Weekly activity as bar chart
    act_df = df_view[["created_at", "weekly_activity_minutes"]].dropna(
        subset=["weekly_activity_minutes"]
    )
    if not act_df.empty:
        fig_act = go.Figure(
            go.Bar(
                x=act_df["created_at"],
                y=act_df["weekly_activity_minutes"],
                marker_color=YELLOW,
                marker_line_color="rgba(0,0,0,0)",
                name="min/week",
                hovertemplate="<b>%{y:.0f} min</b><br>%{x|%b %d, %Y}<extra></extra>",
            )
        )
        layout_act = dict(CHART_LAYOUT)
        layout_act["title"] = dict(
            text="🏃 Weekly Activity Minutes", font=dict(color="#E5E7EB", size=14), x=0
        )
        # WHO guideline 150 min/week reference
        fig_act.add_hline(
            y=150,
            line_dash="dot",
            line_color="rgba(148,163,184,0.35)",
            annotation_text="WHO 150 min target",
            annotation_font_color="#64748B",
            annotation_font_size=10,
        )
        fig_act.update_layout(**layout_act)
        st.plotly_chart(fig_act, use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption("No weekly activity data available yet.")

with c6:
    _line_chart(
        df_view["resting_hr"],
        "❤️ Resting Heart Rate",
        "bpm",
        color=ORANGE,
        reference_line=60.0,
        ref_label="Good: ≤60 bpm",
    )

# ── Trend insight box ─────────────────────────────────────────────────────────
st.markdown("---")

def _trend_text(series: pd.Series, label: str, unit: str, invert: bool = False) -> str:
    """Return a plain-English trend sentence for a metric."""
    valid = series.dropna()
    if len(valid) < 2:
        return ""
    delta = valid.iloc[-1] - valid.iloc[0]
    direction = "↑" if delta > 0 else "↓"
    positive = delta < 0 if invert else delta > 0
    color = "#22C55E" if positive else "#EF4444"
    sign = "+" if delta > 0 else ""
    return (
        f'<span style="color:{color};font-weight:700;">{direction} {sign}{delta:.1f} {unit}</span> '
        f'in {label} over the selected period.'
    )


insights = [
    _trend_text(df_view["weight"], "weight", "kg", invert=True),
    _trend_text(df_view["bmi"], "BMI", "", invert=True),
    _trend_text(df_view["vo2max"], "VO₂max", "ml/kg/min", invert=False),
    _trend_text(df_view["bio_age"], "biological age", "yrs", invert=True),
    _trend_text(df_view["weekly_activity_minutes"], "weekly activity", "min", invert=False),
    _trend_text(df_view["resting_hr"], "resting HR", "bpm", invert=True),
]
insights = [i for i in insights if i]

if insights:
    rows = "".join(f"<li style='margin-bottom:6px;'>{i}</li>" for i in insights)
    st.markdown(
        f"""
<div style="background:linear-gradient(135deg,rgba(14,165,163,.08),rgba(59,130,246,.06));
     border:1px solid rgba(14,165,163,.25);border-left:4px solid #0EA5A3;
     border-radius:14px;padding:18px 20px;margin-top:8px;">
  <div style="color:#0EA5A3;font-size:12px;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;margin-bottom:10px;">📊 Trend Summary</div>
  <ul style="margin:0;padding-left:18px;color:#E5E7EB;font-size:14px;line-height:1.8;">
    {rows}
  </ul>
</div>
""",
        unsafe_allow_html=True,
    )

# ── Footer note ───────────────────────────────────────────────────────────────
st.caption(
    "Measurements are saved automatically each time you run a calculation on the main page. "
    f"Showing **{len(df_view)}** of **{len(df)}** total records."
)
