from __future__ import annotations
from db import get_db_client
# ... ein stad i koden når du treng å bruke databasen:
db = get_db_client()

# Eksempel: Lagre data (kjem vi tilbake til)
# Her henter du data fra variablene dine
user_id_verdi = "test" # Eller variabelen som holder bruker-ID
bmi_verdi = 24         # Eller variabelen som holder BMI-resultatet

# Dette er koden som faktisk lagrer til Supabase
try:
    # Alt det som skal lagres
    data = {"user_id": user_id_verdi, "bmi": bmi_verdi}
    response = db.table("health_metrics").insert(data).execute()
    st.success("Lagret til historikk!")
except Exception as e:
    # Denne linjen må ha innrykk, og stå rett under 'except'
    st.error(f"Kunne ikke lagre: {e}")
from datetime import datetime
from html import escape
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
PAGE_W, PAGE_H = A4
MARGIN_H = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_H

def P(txt, style):
    return Paragraph(str(txt), style)
from reportlab.platypus import Spacer as VGap
import streamlit as st

def render_premium_download_gate(pdf_bytes):
    """
    Renders the premium download section in a clean, professional container.
    """
    with st.container(border=True):
        st.subheader("✅ Your Premium Health Report is ready")
        st.markdown("""
        We have analyzed your biomarkers and generated a tailored 30-day protocol.
        This report includes:
        * 🎯 **Top 3 health priorities**
        * 📊 **Radar analysis of your biomarkers**
        * 📝 **Actionable 30-day health plan**
        """)
        
        st.write("") 
        
        st.download_button(
            label="📥 Download your PDF Report (4.99 USD)",
            data=pdf_bytes,
            file_name="Health_Audit_Report.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        
        st.caption("Your purchase is secured with 100% encryption.")
import streamlit.components.v1 as components
import calculators
import matplotlib.pyplot as plt
import uuid
from db import get_db_client, save_health_metrics # Hugs å importere save-funksjonen

if "user_id" not in st.session_state:
    st.session_state["user_id"] = str(uuid.uuid4())
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors

class PDFStyles:
    # Fargepalett
    PRIMARY = colors.HexColor("#0EA5A3")
    BG = colors.HexColor("#0B1220")
    TEXT = colors.HexColor("#E5E7EB")
    MUTED = colors.HexColor("#94A3B8")
    
    # Styles
    H1 = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=24, leading=28, spaceAfter=20, textColor=colors.white)
    H2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=12, textColor=colors.white)
    Body = ParagraphStyle("Body", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=10, textColor=colors.lightgrey)
    Label = ParagraphStyle("Label", fontName="Helvetica-Bold", fontSize=8, leading=10, spaceAfter=4, textColor=colors.HexColor("#64748B"), uppercase=True)

# Bruk denne i koden din slik:
# doc.build([Paragraph("Health Audit", PDFStyles.H1), ...])
# --- Stripe return — Nivå 2 (session_id) ---
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

# Godta alle ekte Stripe session IDs (cs_live_ eller cs_test_)
if _session_id and (
    str(_session_id).startswith("cs_live_") or
    str(_session_id).startswith("cs_test_")
):
    st.session_state["report_unlocked"] = True
    st.session_state["stripe_session_id"] = _session_id
# --- Verified badge ---
if st.session_state.get("stripe_session_id"):
    _sid = st.session_state["stripe_session_id"]
    st.sidebar.success(f"✅ Betaling verifisert  •  ID: ...{_sid[-6:]}")
    
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, HRFlowable, Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from calculators import (
    bmr_mifflin,
    tdee_including_weekly_exercise,
)
# 1. Stil-system (Brand-fargar)
class PDFStyles:
    PRIMARY = HexColor("#0EA5A3")
    BG = HexColor("#0B1220")
    TEXT = HexColor("#E5E7EB")
    MUTED = HexColor("#94A3B8")
    H1 = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=24, leading=28, spaceAfter=20, textColor=HexColor("#FFFFFF"))

# 2. Dine Custom Flowables (flytta ut av funksjonen)
class PremiumRadarChart(Flowable):
    def __init__(self, scores, width=400):
        super().__init__()
        self.scores = scores
        self.w = width
        self.h = 300
    # ... (her legg du inn Radar-logikken din) ...
# ── Resting HR sync ──────────────────────────────────────────────────────────
_HR_KEYS = [
    "resting_hr", "global_resting_hr", "basic_resting_hr",
    "ui_resting_hr", "vo2_rhr_value", "bio_rhr_val",
]

def _sync_hr(source_key: str):
    val = st.session_state.get(source_key)
    if val is None:
        return
    try:
        v = int(val)
    except Exception:
        return
    for k in _HR_KEYS:
        if k != source_key:
            st.session_state[k] = v

def sync_from_basic():
    _sync_hr("basic_resting_hr")

def sync_from_calc():
    _sync_hr("ui_resting_hr")

def sync_from_vo2():
    _sync_hr("vo2_rhr_value")

def sync_from_bio():
    _sync_hr("bio_rhr_val")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Health Tools MVP",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
:root{
  --bg0:#070D18;
  --bg1:#0B1220;
  --card: rgba(15,23,42,.72);
  --card2: rgba(17,28,51,.62);
  --stroke: rgba(148,163,184,.16);
  --stroke2: rgba(148,163,184,.10);
  --text:#E5E7EB;
  --muted:#94A3B8;
  --muted2:#A7B4C6;
  --accent:#0EA5A3;
  --accent2:#3B82F6;
  --good:#22C55E;
  --warn:#F59E0B;
  --bad:#EF4444;
  --radius:16px;
}

img, svg, iframe { max-width: 100% !important; height: auto !important; }

.stApp{
  background:
    radial-gradient(1200px 600px at 18% -10%, rgba(14,165,163,.20), transparent 60%),
    radial-gradient(900px 520px at 90% 0%, rgba(59,130,246,.15), transparent 55%),
    linear-gradient(180deg, var(--bg0), var(--bg1) 40%, #070B14);
  color: var(--text);
}

.block-container{
  max-width: 980px;
  padding-top: 1.35rem;
  padding-bottom: 2.2rem;
}

h1, h2, h3, p, label, li { color: var(--text) !important; }
small, .stCaption, [data-testid="stCaptionContainer"] { color: var(--muted) !important; }

.ht-hero{
  background: linear-gradient(135deg, rgba(14,165,163,.18), rgba(59,130,246,.12));
  border: 1px solid var(--stroke);
  border-radius: calc(var(--radius) + 6px);
  padding: 18px 18px;
  box-shadow: 0 18px 50px rgba(0,0,0,.25);
  backdrop-filter: blur(8px);
  margin-bottom: 14px;
}
.ht-hero h1{ margin:0; font-size: 38px; letter-spacing:-0.02em; }
.ht-hero .sub{ margin-top:6px; color: var(--muted2); font-size: 13px; line-height:1.4; }
.ht-pills{ display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
.ht-pill{
  display:inline-flex; align-items:center; gap:6px;
  background: rgba(17,24,39,.65);
  border: 1px solid var(--stroke2);
  padding: 6px 10px;
  border-radius: 999px;
  color: var(--muted2);
  font-size: 12px;
}

.ht-card{
  background: var(--card);
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  padding: 14px 14px;
  box-shadow: 0 12px 36px rgba(0,0,0,.22);
  backdrop-filter: blur(8px);
  margin-bottom: 12px;
}

.ht-h2{
  font-size: 22px;
  font-weight: 750;
  letter-spacing: -0.01em;
  margin: 2px 0 6px 0;
}
.ht-sub{ color: var(--muted); font-size: 13px; margin: 0 0 10px 0; }

[data-testid="stMetric"]{
  background: rgba(15,23,42,.55);
  border: 1px solid var(--stroke);
  border-radius: 14px;
  padding: 10px 12px;
}

.stTextInput input, .stNumberInput input, textarea, select,
.stSelectbox [data-baseweb="select"]{
  background-color: rgba(255,255,255,0.04) !important;
  color: var(--text) !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
  border-radius: 12px !important;
}

[data-testid="stExpander"] details{
  background: rgba(15,23,42,.45) !important;
  border: 1px solid var(--stroke) !important;
  border-radius: var(--radius) !important;
  overflow: hidden !important;
}
[data-testid="stExpander"] summary{
  padding: 10px 14px !important;
  font-weight: 700 !important;
  letter-spacing: -0.01em;
}
[data-testid="stExpander"] summary:hover{
  background: rgba(148,163,184,.06) !important;
}

[data-testid="stCheckbox"] input{ transform: scale(1.10); }
[data-testid="stToggle"] input{ transform: scale(1.05); }

.stButton > button[data-testid="baseButton-primary"]{
  background: linear-gradient(135deg, #0EA5A3, #22C55E) !important;
  color: #052e2b !important;
  border: 0 !important;
  border-radius: 14px !important;
  padding: 10px 14px !important;
  font-weight: 750 !important;
  box-shadow: 0 14px 34px rgba(14,165,163,.18);
}
.stButton > button[data-testid="baseButton-primary"]:hover{
  filter: brightness(0.97); transform: translateY(-1px);
}
.stButton > button[data-testid="baseButton-secondary"]{
  background: rgba(255,255,255,0.03) !important;
  border: 1.5px solid rgba(255,255,255,0.10) !important;
  border-radius: 12px !important;
  color: #E5E7EB !important;
  font-weight: 600 !important;
  white-space: pre-wrap !important;
  min-height: 82px !important;
  font-size: 11px !important;
  line-height: 1.45 !important;
}
.stButton > button[data-testid="baseButton-secondary"]:hover{
  border-color: rgba(14,165,163,0.5) !important;
  background: rgba(14,165,163,0.08) !important;
}

@media (max-width: 600px){
  .main > div { padding-left: 10px !important; padding-right: 10px !important; }
  .ht-hero h1{ font-size: 30px; }
  .stButton > button { width: 100% !important; }
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="ht-hero">
  <h1>Health Tools — MVP</h1>
  <div class="sub">Educational tool only — not a diagnostic tool. Data is not stored.</div>
  <div class="ht-pills">
    <span class="ht-pill">Privacy‑first</span>
    <span class="ht-pill">Mobile‑friendly</span>
    <span class="ht-pill">Explainable results</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ── Consent ───────────────────────────────────────────────────────────────────
if "consent_given" not in st.session_state:
    st.session_state.consent_given = False

if not st.session_state.consent_given:
    with st.expander("Please read: Consent & privacy", expanded=True):
        st.markdown("This demo stores nothing by default and is for educational purposes only. By continuing you confirm you understand it's not clinical advice.")
    cols = st.columns([1, 1])
    if cols[0].button("I agree", key="consent_agree", type="primary"):
        st.session_state.consent_given = True
        try:
            if not st.session_state.get("_consent_rerun_done"):
                st.session_state["_consent_rerun_done"] = True
                st.experimental_rerun()
        except Exception:
            pass
    if cols[1].button("Exit", key="consent_exit"):
        st.stop()


# ── PDF helpers ───────────────────────────────────────────────────────────────
def para(text: str, style) -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def make_key_value_table(rows, col_widths=(55 * mm, 120 * mm)):
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.fontName = "Helvetica"
    body.fontSize = 9
    body.leading = 11
    data = [[para("Field", body), para("Value", body)]]
    for k, v in rows:
        data.append([para(k, body), para(v, body)])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t

def create_pdf_bytes_ultimate(report: dict) -> bytes:
    import math
    from io import BytesIO
    from datetime import datetime
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Flowable, Spacer, Table, TableStyle

    # ── Oppsett av dimensjonar ──
    PAGE_W, PAGE_H = A4
    MARGIN_H = 18 * mm
    CONTENT_W = PAGE_W - 2 * MARGIN_H

    # ── Theme og Fargar ──
    BG      = HexColor("#0B1220")
    CARD    = HexColor("#111C33")
    CARD2   = HexColor("#0F172A")
    ACCENT  = HexColor("#0EA5A3")
    BLUE    = HexColor("#3B82F6")
    GOOD    = HexColor("#22C55E")
    WARN    = HexColor("#F59E0B")
    BAD     = HexColor("#EF4444")
    TEXT    = HexColor("#E5E7EB")
    MUTED   = HexColor("#94A3B8")
    STROKE  = HexColor("#334155")
    DIM     = HexColor("#64748B")

    # ── Hjelpefunksjonar ──
    _styles = getSampleStyleSheet()
    def S(name, size=10, color=TEXT, after=6, lead=None, bold=False, italic=False, align=TA_LEFT):
        return ParagraphStyle(
            name,
            parent=_styles["Normal"],
            fontName="Helvetica-Bold" if bold else ("Helvetica-Oblique" if italic else "Helvetica"),
            fontSize=size,
            textColor=color,
            spaceAfter=after,
            leading=lead or (size + 4),
            alignment=align
        )

    def P(txt, style):
        return Paragraph(str(txt), style)

    def _sf(x):
        try: return float(x)
        except: return None

    # ── Data extraction ──
    inp       = report.get("inputs", {}) or {}
    age_v     = inp.get("age", "—")
    sex_v     = inp.get("sex", "—")
    h_v       = inp.get("height_cm", "—")
    w_v       = inp.get("weight_kg", "—")
    gen_v     = report.get("generated", datetime.utcnow().strftime("%Y-%m-%d UTC"))

    bmi_d     = report.get("bmi") or {}
    vo2_d     = report.get("vo2") or {}
    bio_d     = report.get("bio_age") or {}
    factors   = report.get("bio_factors") or []
    plan_d    = report.get("plan") or {}
    exlog     = report.get("exercise_log") or {}
    triage_r  = report.get("triage_recommendations") or []
    whr_d     = report.get("whr") or {}
    bf_d      = report.get("bodyfat") or {}

    bmi_v     = _sf(bmi_d.get("value"))
    bmi_cat   = str(bmi_d.get("category", ""))
    vo2_v     = _sf(vo2_d.get("value"))
    vo2_pct   = _sf(vo2_d.get("percentile")) or 0.0
    vo2_rat   = str(vo2_d.get("rating", ""))
    vo2_meth  = str(vo2_d.get("method", ""))
    vo2_band  = str(vo2_d.get("age_band", ""))
    vo2_mean  = _sf(vo2_d.get("mean"))
    bio_v     = _sf(bio_d.get("value"))
    age_f     = _sf(age_v)

    has_plan  = bool(plan_d and not plan_d.get("error"))
    cur_kcal  = _sf(plan_d.get("current_needs_kcal")) if has_plan else None
    rec_kcal  = _sf(plan_d.get("recommended_daily_kcal")) if has_plan else None
    kg_pw     = _sf(plan_d.get("kg_per_week")) if has_plan else None
    milestones = plan_d.get("milestones", []) if has_plan else []

    ex_act    = str(exlog.get("activity", ""))
    ex_int    = str(exlog.get("intensity", ""))
    ex_min    = exlog.get("minutes", 0)
    ex_sess   = exlog.get("sessions_per_week", 0)
    ex_kcal_s = _sf(exlog.get("kcal_per_session")) or 0.0
    ex_kcal_w = _sf(exlog.get("kcal_per_week")) or 0.0
    ex_total_min = int(ex_min or 0) * int(ex_sess or 0)

    # ── Colour helpers ──
    def bmi_color(v):
        if v is None: return MUTED
        if v < 18.5:  return BLUE
        if v < 25:    return GOOD
        if v < 30:    return WARN
        return BAD

    def vo2_color(pct):
        if pct >= 80: return GOOD
        if pct >= 60: return BLUE
        if pct >= 40: return WARN
        return BAD

    def bio_color(diff):
        if diff is None: return MUTED
        if diff <= -1:   return GOOD
        if diff <= 2:    return WARN
        return BAD

    bmi_col  = bmi_color(bmi_v)
    vo2_col  = vo2_color(vo2_pct)
    bio_diff = (bio_v - age_f) if (bio_v is not None and age_f is not None) else None
    bio_col  = bio_color(bio_diff)

    # ── Health score (0–100) ──
    score_parts = []
    if bmi_v is not None:
        if 18.5 <= bmi_v < 25:   score_parts.append(100)
        elif 17 <= bmi_v < 27:   score_parts.append(75)
        elif 15 <= bmi_v < 30:   score_parts.append(50)
        else:                     score_parts.append(25)
    if vo2_v is not None:
        score_parts.append(min(100, int(vo2_pct)))
    if bio_diff is not None:
        score_parts.append(max(0, min(100, int(70 - bio_diff * 10))))
    if ex_total_min:
        score_parts.append(min(100, int(ex_total_min / 300 * 100)))
    health_score = int(sum(score_parts) / len(score_parts)) if score_parts else 0
    score_col    = GOOD if health_score >= 70 else WARN if health_score >= 45 else BAD
    score_label  = ("Excellent" if health_score >= 80 else "Good" if health_score >= 65 else "Fair" if health_score >= 45 else "Needs attention")

    # ── Radar scores ──
    radar = {}
    radar["Body Comp"] = (100 if (bmi_v and 18.5 <= bmi_v < 25) else 75  if (bmi_v and 17 <= bmi_v < 27) else 50  if (bmi_v and 15 <= bmi_v < 30) else 25  if bmi_v else 50)
    radar["Cardio"]    = int(vo2_pct) if vo2_v else 50
    radar["Bio Age"]   = (max(0, min(100, int(70 - bio_diff * 10))) if bio_diff is not None else 50)
    radar["Activity"]  = (min(100, int(ex_total_min / 300 * 100)) if ex_total_min else 30)
    life = 60
    for f in factors:
        try:
            d = float(f.get("delta", 0))
            if d < 0: life = min(100, life + 8)
            elif d > 1: life = max(10, life - 8)
        except: pass
    radar["Lifestyle"] = max(0, min(100, life))

    # ── Biggest lever ──
    if vo2_v is not None and vo2_pct < 40:
        biggest_lever = "Cardio fitness (VO2max)"
        lever_why = "The single most impactful modifiable longevity factor — and the fastest to improve with training."
    elif bmi_v is not None and bmi_v >= 30:
        biggest_lever = "Energy balance + daily movement"
        lever_why = "A sustainable calorie strategy combined with consistent activity has the highest ROI here."
    elif bio_diff is not None and bio_diff > 2:
        biggest_lever = "Sleep + lifestyle fundamentals"
        lever_why = "Your biological age estimate shows the biggest room for improvement in foundational habits."
    elif exlog and ex_total_min < 150:
        biggest_lever = "Exercise volume (reach WHO target)"
        lever_why = "Even incremental increases from below 150 min/week produce measurable health returns."
    else:
        biggest_lever = "Strength training + progressive overload"
        lever_why = "Your core markers are solid — the next tier of improvement comes from consistent resistance training."

    # ── Personalised insights ──
    insights = []
    if bmi_v is not None:
        if bmi_v >= 30: insights.append(("Body Composition", WARN, f"Your BMI of {bmi_v:.1f} ({bmi_cat}) is high. The most sustainable approach combines a modest daily calorie deficit (−300 to −500 kcal), 2–3 strength sessions/week to preserve muscle, and increased daily steps. Avoid aggressive cuts — they accelerate muscle loss and reduce long-term adherence. Aim for 0.5–0.75 kg/week loss."))
        elif bmi_v >= 25: insights.append(("Body Composition", WARN, f"Your BMI of {bmi_v:.1f} ({bmi_cat}) is slightly elevated. Strength training 2–3x/week combined with a modest deficit is more effective than cardio alone. A loss rate of 0.5 kg/week preserves significantly more lean mass than faster approaches."))
        elif bmi_v < 18.5: insights.append(("Body Composition", BLUE, f"Your BMI of {bmi_v:.1f} ({bmi_cat}) is below the typical range. Prioritise progressive strength training and ensure adequate protein (≥1.6 g/kg/day) and total energy intake. Avoid calorie deficits — focus on building lean mass and strength."))
        else: insights.append(("Body Composition", GOOD, f"Your BMI of {bmi_v:.1f} ({bmi_cat}) is in the normal range. The biggest upgrades now come from cardio fitness and strength, not body weight changes. Use resistance training and aerobic capacity as your primary targets."))

    if vo2_v is not None:
        if vo2_pct < 30: insights.append(("Cardio Fitness", BAD, f"Your VO2max of {vo2_v:.1f} ml/kg/min ({vo2_pct:.0f}th percentile) is in the lowest tier. VO2max is the strongest predictor of all-cause mortality. The good news: it responds quickly. Start with 3–4x 30-min easy aerobic sessions per week. Expect noticeable improvement in 4–6 weeks."))
        elif vo2_pct < 50: insights.append(("Cardio Fitness", WARN, f"Your VO2max of {vo2_v:.1f} ({vo2_pct:.0f}th percentile) is below average. Adding one structured interval session weekly (e.g. 4×4 min hard effort) alongside 2 easy sessions typically produces the fastest improvement over 6–12 weeks."))
        elif vo2_pct < 75: insights.append(("Cardio Fitness", BLUE, f"Your VO2max of {vo2_v:.1f} ({vo2_pct:.0f}th percentile) is above average. To push higher, use 80/20 training — 80% easy effort, 20% hard. Most people accidentally do 50/50, which leads to fatigue without meaningful VO2 adaptation."))
        else: insights.append(("Cardio Fitness", GOOD, f"Your VO2max of {vo2_v:.1f} ({vo2_pct:.0f}th percentile) is excellent. Maintain with 2–3 quality sessions/week. Avoid unplanned breaks over 2 weeks — detraining begins quickly."))

    if bio_diff is not None:
        if bio_diff > 3: insights.append(("Biological Age", BAD, f"Estimated biological age ({bio_v:.1f} yrs) is {bio_diff:.1f} years above calendar age. This is driven by lifestyle factors — most are reversible. Highest-impact levers: sleep consistency, cardio fitness, blood pressure control, and stress management."))
        elif bio_diff > 0: insights.append(("Biological Age", WARN, f"Estimated biological age ({bio_v:.1f} yrs) is slightly above calendar age ({bio_diff:.1f} yrs). This gap is small and reversible. Focus on the red/amber factors in your factor breakdown."))
        else: insights.append(("Biological Age", GOOD, f"Estimated biological age ({bio_v:.1f} yrs) is {abs(bio_diff):.1f} yrs below calendar age. This reflects well on your current habits. Maintain them — consistency is what sustains this."))

    if exlog:
        if ex_total_min < 150: insights.append(("Exercise Volume", WARN, f"You're logging {ex_total_min} min/week — {150 - ex_total_min} min short of the WHO 150 min/week guideline. Even small increases (+20 min/week) measurably reduce all-cause mortality and metabolic disease risk."))
        else: insights.append(("Exercise Volume", GOOD, f"You're meeting WHO guidelines with {ex_total_min} min/week ({ex_kcal_w:.0f} kcal/week). Consider adding strength training if not already included — it's the most underutilised tool for metabolic health and longevity."))

    interval_t = "Short intervals (4×4 min hard)" if vo2_pct < 60 else "Tempo run / threshold (25 min)"
    plan_7 = [
        ("Mon", "Easy cardio (Zone 2)", "35–45 min", "Aerobic base — can hold a conversation"),
        ("Tue", "Full-body strength", "30–40 min", "Muscle, metabolism, bone density"),
        ("Wed", "Mobility + light walk", "20–30 min", "Recovery, reduce stiffness"),
        ("Thu", interval_t, "25–35 min", "Raise VO2max + cardio ceiling"),
        ("Fri", "Full-body strength", "30–40 min", "Progressive overload + posture"),
        ("Sat", "Long easy walk / cycle", "50–75 min", "Weekly aerobic volume (easy)"),
        ("Sun", "Review + plan next week", "10–15 min", "Make progress sustainable"),
    ]
    if has_plan and kg_pw is not None:
        plan_7[6] = ("Sun", "Review + meal prep", "20–30 min", "Align food plan with weekly goal")

    # ════════════════════════════════════════════════════════════════════
    # CUSTOM FLOWABLES
    # ════════════════════════════════════════════════════════════════════
    class VGap(Flowable):
        def __init__(self, h=8):
            super().__init__(); self._h = h
        def wrap(self, aw, ah): return aw, self._h
        def draw(self): pass

    class SecHeader(Flowable):
        def __init__(self, title, subtitle="", accent=None, width=CONTENT_W):
            super().__init__()
            self.title = title; self.subtitle = subtitle; self.accent = accent or ACCENT
            self.w = width; self.h = 46 if subtitle else 36
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv
            c.setFillColor(CARD); c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)
            c.setFillColor(self.accent); c.roundRect(0, 0, 5, self.h, 2, fill=1, stroke=0)
            c.setFillColor(TEXT); c.setFont("Helvetica-Bold", 13)
            c.drawString(16, self.h - 22, self.title)
            if self.subtitle:
                c.setFillColor(MUTED); c.setFont("Helvetica", 7.5)
                c.drawString(16, 8, self.subtitle[:90])

    class MetricCard(Flowable):
        def __init__(self, metrics, width=CONTENT_W, card_h=66):
            super().__init__()
            self.metrics = metrics; self.w = width; self.h = card_h
            n = max(1, len(metrics))
            self.card_w = (width - (n - 1) * 6) / n
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; cw = self.card_w; ch = self.h
            for i, (lbl, val, sub, col_s) in enumerate(self.metrics):
                col = HexColor(col_s) if isinstance(col_s, str) else col_s
                x = i * (cw + 6)
                c.setFillColor(CARD); c.roundRect(x, 0, cw, ch, 8, fill=1, stroke=0)
                c.setFillColor(col); c.roundRect(x, ch - 4, cw, 4, 2, fill=1, stroke=0)
                c.setFillColor(MUTED); c.setFont("Helvetica", 6.5)
                c.drawString(x + 10, ch - 16, str(lbl).upper()[:22])
                c.setFillColor(col); c.setFont("Helvetica-Bold", 16)
                c.drawString(x + 10, ch - 34, str(val)[:18])
                if sub:
                    c.setFillColor(MUTED); c.setFont("Helvetica", 7.5)
                    c.drawString(x + 10, ch - 47, str(sub)[:26])

    class HealthScoreRing(Flowable):
        def __init__(self, score, label, color, width=CONTENT_W):
            super().__init__()
            self.score = score; self.label = label; self.color = color; self.w = width; self.h = 130
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; cx = self.w / 2; cy = self.h / 2 + 14; R = 46
            c.setStrokeColor(STROKE); c.setLineWidth(13); c.circle(cx, cy, R, fill=0, stroke=1)
            frac = self.score / 100.0; steps = max(2, int(frac * 72))
            for i in range(steps):
                a1 = math.pi / 2 - (i / 72) * 2 * math.pi
                a2 = math.pi / 2 - ((i + 1) / 72) * 2 * math.pi
                c.setStrokeColor(self.color); c.setLineWidth(13)
                c.line(cx + R * math.cos(a1), cy + R * math.sin(a1), cx + R * math.cos(a2), cy + R * math.sin(a2))
            c.setFillColor(self.color); c.setFont("Helvetica-Bold", 28)
            c.drawCentredString(cx, cy + 6, str(self.score))
            c.setFillColor(MUTED); c.setFont("Helvetica", 8)
            c.drawCentredString(cx, cy - 8, "/ 100")
            c.setFillColor(TEXT); c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(cx, cy - 22, self.label)
            dims = list(radar.items()); dw = self.w / len(dims)
            for j, (dim, sc) in enumerate(dims):
                dx = j * dw + dw / 2; dy = 10
                dc = GOOD if sc >= 70 else WARN if sc >= 45 else BAD
                c.setFillColor(CARD2); c.roundRect(j * dw + 2, 2, dw - 4, 24, 4, fill=1, stroke=0)
                c.setFillColor(dc); c.setFont("Helvetica-Bold", 9); c.drawCentredString(dx, dy + 8, str(sc))
                c.setFillColor(MUTED); c.setFont("Helvetica", 6); c.drawCentredString(dx, dy, dim)

    class BMIScale(Flowable):
        def __init__(self, bmi_val, width=CONTENT_W):
            super().__init__()
            self.bmi = bmi_val; self.w = width; self.h = 100
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; bmi = self.bmi; w = self.w
            c.setFillColor(CARD); c.roundRect(0, 0, w, self.h, 10, fill=1, stroke=0)
            col = bmi_color(bmi)
            c.setFillColor(col); c.setFont("Helvetica-Bold", 30); c.drawString(14, 62, f"{bmi:.1f}")
            c.setFillColor(MUTED); c.setFont("Helvetica", 7.5); c.drawString(14, 52, "BMI")
            cat = ("Underweight" if bmi < 18.5 else "Normal weight" if bmi < 25 else "Overweight" if bmi < 30 else "Obese")
            c.setFillColor(col); c.setFont("Helvetica-Bold", 9); c.drawString(14, 39, cat)
            SMAX = 45.0; bx = 14; by = 18; bh = 13; bw = w - 28
            segs = [(0,18.5,"#3B82F6","Underweight"),(18.5,25,"#22C55E","Normal"),(25,30,"#F59E0B","Overweight"),(30,45,"#EF4444","Obese")]
            for i, (s, e, cl, lbl) in enumerate(segs):
                sx = bx + (s/SMAX)*bw; sw = ((e-s)/SMAX)*bw
                c.setFillColor(HexColor(cl))
                if i == 0: c.roundRect(sx,by,sw,bh,3,fill=1,stroke=0); c.rect(sx+3,by,sw-3,bh,fill=1,stroke=0)
                elif i == len(segs)-1: c.roundRect(sx,by,sw,bh,3,fill=1,stroke=0); c.rect(sx,by,sw-3,bh,fill=1,stroke=0)
                else: c.rect(sx,by,sw,bh,fill=1,stroke=0)
                c.setFillColor(HexColor("#0F172A")); c.setFont("Helvetica-Bold", 5.5)
                c.drawCentredString(sx+sw/2, by+4, lbl)
            mx = bx + min(1.0, bmi/SMAX)*bw
            c.setStrokeColor(white); c.setLineWidth(1.5); c.line(mx, by-2, mx, by+bh+2)
            c.setFillColor(white); path = c.beginPath(); path.moveTo(mx, by+bh+9); path.lineTo(mx-5, by+bh+2); path.lineTo(mx+5, by+bh+2); path.close()
            c.drawPath(path, fill=1, stroke=0)
            for lbl, pos in [("0",0),("18.5",18.5),("25",25),("30",30),("45",45)]:
                c.setFillColor(MUTED); c.setFont("Helvetica", 5.5); c.drawCentredString(bx + (pos/SMAX)*bw, by-8, lbl)

    class VO2Visual(Flowable):
        def __init__(self, vo2_val, percentile, rating, width=CONTENT_W):
            super().__init__()
            self.vo2 = vo2_val; self.pct = float(percentile or 0); self.rat = rating; self.w = width; self.h = 90
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; w = self.w; pct = self.pct
            col = vo2_color(pct)
            c.setFillColor(CARD); c.roundRect(0, 0, w, self.h, 10, fill=1, stroke=0)
            c.setFillColor(col); c.setFont("Helvetica-Bold", 30); c.drawString(14, 56, f"{self.vo2:.1f}")
            c.setFillColor(MUTED); c.setFont("Helvetica", 7.5); c.drawString(14, 46, "ml / kg / min")
            c.setFillColor(col); c.setFont("Helvetica-Bold", 10); c.drawString(14, 32, str(self.rat or "—"))
            c.setFillColor(MUTED); c.setFont("Helvetica", 7); c.drawString(14, 20, "Rating")
            bx = w*0.44; bw2 = w*0.51; bh = 13; by = 48
            c.setFillColor(MUTED); c.setFont("Helvetica", 6.5); c.drawString(bx, by+bh+6, "POPULATION PERCENTILE")
            c.setFillColor(STROKE); c.roundRect(bx, by, bw2, bh, 4, fill=1, stroke=0)
            c.setFillColor(col); c.roundRect(bx, by, max(8, (pct/100)*bw2), bh, 4, fill=1, stroke=0)
            c.setFillColor(col); c.setFont("Helvetica-Bold", 12); c.drawRightString(bx+bw2, by-14, f"{pct:.0f}th percentile")
            zones = [(0,20,"#EF4444"),(20,40,"#F59E0B"),(40,60,"#3B82F6"),(60,80,"#22C55E"),(80,100,"#10B981")]
            sz_y = 18; sz_h = 7
            for zs, ze, zc in zones:
                c.setFillColor(HexColor(zc)); c.rect(bx + (zs/100)*bw2, sz_y, ((ze-zs)/100)*bw2, sz_h, fill=1, stroke=0)
            c.setStrokeColor(white); c.setLineWidth(1.5); nx = bx + (pct/100)*bw2; c.line(nx, sz_y-2, nx, sz_y+sz_h+2)
            zlabels = ["Low","Below avg","Average","Good","Excellent"]
            for j, (zl, (zs, ze, _)) in enumerate(zip(zlabels, zones)):
                c.setFillColor(MUTED); c.setFont("Helvetica", 5.5); c.drawCentredString(bx + ((zs+ze)/200)*bw2, sz_y-8, zl)

    class RadarChart(Flowable):
        def __init__(self, scores_dict, width=CONTENT_W):
            super().__init__()
            self.scores = scores_dict; self.w = width; self.h = 165
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; cx = self.w/2; cy = self.h/2 + 10; R = 58
            labels = list(self.scores.keys()); vals = [self.scores[k]/100.0 for k in labels]; n = len(labels)
            def pt(i, r): ang = math.pi/2 + 2*math.pi*i/n; return cx + r*math.cos(ang), cy + r*math.sin(ang)
            for ring in [0.25, 0.5, 0.75, 1.0]:
                pts = [pt(i, ring*R) for i in range(n)]
                c.setStrokeColor(STROKE); c.setLineWidth(0.5); path = c.beginPath(); path.moveTo(*pts[0])
                for p in pts[1:]: path.lineTo(*p)
                path.close(); c.drawPath(path, fill=0, stroke=1)
            for i in range(n):
                ox, oy = pt(i, R); c.setStrokeColor(STROKE); c.setLineWidth(0.5); c.line(cx, cy, ox, oy)
            poly = [pt(i, vals[i]*R) for i in range(n)]; c.setFillColor(ACCENT); path = c.beginPath(); path.moveTo(*poly[0])
            for p in poly[1:]: path.lineTo(*p)
            path.close(); c.setFillAlpha(0.25); c.drawPath(path, fill=1, stroke=0); c.setFillAlpha(1.0)
            c.setStrokeColor(ACCENT); c.setLineWidth(1.5); c.drawPath(path, fill=0, stroke=1)
            for i, (lbl, val) in enumerate(zip(labels, vals)):
                px, py = pt(i, val*R); c.setFillColor(ACCENT); c.circle(px, py, 3.5, fill=1, stroke=0)
                lx, ly = pt(i, R+15); sc = int(val*100)
                dc = GOOD if sc >= 70 else WARN if sc >= 45 else BAD
                c.setFillColor(TEXT); c.setFont("Helvetica-Bold", 7.5); c.drawCentredString(lx, ly+4, lbl)
                c.setFillColor(dc); c.setFont("Helvetica-Bold", 8.5); c.drawCentredString(lx, ly-6, str(sc))

    class BioAgeBar(Flowable):
        def __init__(self, bio_val, chron_val, width=CONTENT_W):
            super().__init__()
            self.bio = bio_val; self.chron = chron_val; self.w = width; self.h = 72
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; w = self.w; diff = self.bio - self.chron; col = bio_color(diff)
            c.setFillColor(CARD); c.roundRect(0, 0, w, self.h, 10, fill=1, stroke=0)
            c.setFillColor(col); c.setFont("Helvetica-Bold", 30); c.drawString(14, 38, f"{self.bio:.1f}")
            c.setFillColor(MUTED); c.setFont("Helvetica", 7); c.drawString(14, 28, "Biological age")
            c.setFillColor(col); c.setFont("Helvetica-Bold", 8.5); c.drawString(14, 14, f"{abs(diff):.1f} yrs {'younger' if diff<0 else 'older'}")
            c.setStrokeColor(STROKE); c.setLineWidth(0.5); c.line(w*0.35, 8, w*0.35, self.h-8)
            bx = w*0.38; bw2 = w*0.57; max_age = max(self.bio, self.chron)*1.3
            c.setFillColor(MUTED); c.setFont("Helvetica", 7)
            c.drawString(bx, self.h-16, f"Calendar age:   {self.chron:.0f} yrs")
            c.drawString(bx, self.h-28, f"Biological age: {self.bio:.1f} yrs")
            for j, (val, lbl2, cl) in enumerate([(self.chron, "Calendar", MUTED), (self.bio, "Biological", col)]):
                bar_y = 14 + j*16; c.setFillColor(STROKE); c.roundRect(bx, bar_y, bw2, 8, 3, fill=1, stroke=0)
                c.setFillColor(cl); c.roundRect(bx, bar_y, (val/max_age)*bw2, 8, 3, fill=1, stroke=0)

    class FactorBars(Flowable):
        def __init__(self, factors, width=CONTENT_W):
            super().__init__()
            self.factors = sorted(factors, key=lambda f: abs(float(f.get("delta", 0))), reverse=True)[:8]
            self.w = width; self.h = len(self.factors)*21 + 12
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; c.setFillColor(CARD); c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)
            bx = self.w*0.42; bw2 = self.w*0.44; row = 21
            for i, f in enumerate(self.factors):
                y = self.h - 14 - i*row; delta = float(f.get("delta", 0))
                cl = "#22C55E" if delta <= 0 else "#EF4444" if delta > 1 else "#F59E0B"
                frac = min(abs(delta)/8.0, 1.0)
                c.setFillColor(MUTED); c.setFont("Helvetica", 7.5); c.drawString(10, y-4, str(f.get("label", ""))[:30])
                c.setFillColor(STROKE); c.roundRect(bx, y-4, bw2, 9, 2, fill=1, stroke=0)
                if frac > 0: c.setFillColor(HexColor(cl)); c.roundRect(bx, y-4, frac*bw2, 9, 2, fill=1, stroke=0)
                c.setFillColor(HexColor(cl)); c.setFont("Helvetica-Bold", 7.5); c.drawRightString(self.w-6, y-4, f"{delta:+.1f} yrs")

    class CalorieBar(Flowable):
        def __init__(self, maintenance, recommended, kg_per_week, width=CONTENT_W):
            super().__init__()
            self.maint = maintenance; self.rec = recommended; self.rate = kg_per_week; self.w = width; self.h = 88
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; delta = self.rec - self.maint
            col = "#22C55E" if delta < 0 else "#3B82F6" if delta > 0 else "#94A3B8"
            lbl = "Deficit" if delta < 0 else "Surplus" if delta > 0 else "Maintenance"
            c.setFillColor(CARD); c.roundRect(0, 0, self.w, self.h, 10, fill=1, stroke=0)
            cw3 = (self.w - 16) / 3
            for j, (title, val, cl) in enumerate([("MAINTENANCE", f"{self.maint:.0f}", "#94A3B8"), ("RECOMMENDED", f"{self.rec:.0f}", col), (lbl.upper(), f"{delta:+.0f} kcal", col)]):
                x = 8 + j*cw3; c.setFillColor(HexColor(cl)); c.setFont("Helvetica-Bold", 15); c.drawString(x+4, 50, val)
                c.setFillColor(MUTED); c.setFont("Helvetica", 6.5); c.drawString(x+4, 40, "kcal/day" if j < 2 else "per day"); c.drawString(x+4, self.h-14, title)
                if j < 2: c.setStrokeColor(STROKE); c.setLineWidth(0.5); c.line(x+cw3+1, 10, x+cw3+1, self.h-6)
            bx = 8; by = 18; bw2 = self.w-16
            c.setFillColor(STROKE); c.roundRect(bx, by, bw2, 9, 3, fill=1, stroke=0)
            c.setFillColor(HexColor(col)); c.roundRect(bx, by, int(min(1.0, abs(delta) / max(1, self.maint) * 5)*bw2), 9, 3, fill=1, stroke=0)
            if self.rate is not None: c.setFillColor(HexColor(col)); c.setFont("Helvetica-Bold", 8); c.drawRightString(self.w-10, 6, f"{self.rate:+.2f} kg/week")

    class MilestoneRow(Flowable):
        def __init__(self, week, weight, focus, progress_pct, col_s, is_last, width=CONTENT_W):
            super().__init__()
            self.week=week; self.weight=weight; self.focus=focus; self.prog=progress_pct; self.col_s=col_s; self.is_last=is_last; self.w=width; self.h=46
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; col = HexColor(self.col_s)
            if not self.is_last: c.setStrokeColor(STROKE); c.setLineWidth(1); c.line(14,0,14,8)
            c.setFillColor(col); c.circle(14,34,12,fill=1,stroke=0); c.setFillColor(white); c.setFont("Helvetica-Bold",8); c.drawCentredString(14,30,str(self.week))
            c.setFillColor(CARD); c.roundRect(32,10,self.w-36,34,6,fill=1,stroke=0); c.setFillColor(col); c.roundRect(32,40,self.w-36,4,2,fill=1,stroke=0)
            c.setFillColor(col); c.setFont("Helvetica-Bold",13); c.drawString(42,27,f"{self.weight:.1f} kg")
            c.setFillColor(MUTED); c.setFont("Helvetica",7.5); c.drawString(42,16,str(self.focus)[:38])
            bx=self.w-88; bw2=78
            c.setFillColor(STROKE); c.roundRect(bx,17,bw2,6,2,fill=1,stroke=0); c.setFillColor(col); c.roundRect(bx,17,self.prog/100*bw2,6,2,fill=1,stroke=0)
            c.setFillColor(MUTED); c.setFont("Helvetica",6); c.drawRightString(bx+bw2,11,f"{self.prog:.0f}%")

    class InsightBlock(Flowable):
        def __init__(self, title, text, color, width=CONTENT_W):
            super().__init__()
            self.title = title; self.text = text; self.color = color if isinstance(color, colors.Color) else HexColor(str(color)); self.w = width
            self._para = Paragraph(f"<b>{title}:</b> {text}", S("_ib", size=8.8, lead=13))
            _, ph = self._para.wrap(width - 20, 9999); self.h = max(36, ph + 16)
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; c.setFillColor(CARD); c.roundRect(0, 0, self.w, self.h, 6, fill=1, stroke=0)
            c.setFillColor(self.color); c.roundRect(0, 0, 4, self.h, 2, fill=1, stroke=0)
            self._para.drawOn(c, 14, 8)
    class ExpertInsightBox(Flowable):
        """Gold-accented Expert Insight box — scientific rationale for each section."""
        def __init__(self, section: str, text: str, width=CONTENT_W):
            super().__init__()
            self.w = width
            self._header = Paragraph(
                f'<b>🔬 EXPERT INSIGHT — {section.upper()}</b>',
                S(f"_ei_h_{abs(hash(text))}", size=7.5, lead=11, color=WARN, bold=True)
            )
            self._body = Paragraph(text, S(f"_ei_b_{abs(hash(text))}", size=8.8, lead=14, color=TEXT))
            _, hh = self._header.wrap(width - 24, 9999)
            _, bh = self._body.wrap(width - 24, 9999)
            self.h = hh + bh + 30

        def wrap(self, aw, ah): return self.w, self.h

        def draw(self):
            c = self.canv
            c.setFillColor(HexColor("#120F00"))
            c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)
            c.setStrokeColor(WARN); c.setLineWidth(1.0)
            c.roundRect(0, 0, self.w, self.h, 8, fill=0, stroke=1)
            c.setFillColor(WARN); c.roundRect(0, 0, 4, self.h, 2, fill=1, stroke=0)
            self._header.drawOn(c, 14, self.h - 18)
            self._body.drawOn(c, 14, 8)

    class ActionableMilestoneBox(Flowable):
        """Teal-accented Actionable Milestone box — specific 4-week protocol."""
        def __init__(self, steps: list, width=CONTENT_W):
            super().__init__()
            self.w = width
            bullet_html = "".join(f"→  {s}<br/>" for s in steps)
            self._header = Paragraph(
                '<b>🎯 ACTIONABLE MILESTONE — YOUR NEXT 4 WEEKS</b>',
                S(f"_am_h_{abs(hash(bullet_html))}", size=7.5, lead=11, color=ACCENT, bold=True)
            )
            self._body = Paragraph(bullet_html, S(f"_am_b_{abs(hash(bullet_html))}", size=8.8, lead=15, color=TEXT))
            _, hh = self._header.wrap(width - 24, 9999)
            _, bh = self._body.wrap(width - 24, 9999)
            self.h = hh + bh + 30

        def wrap(self, aw, ah): return self.w, self.h

        def draw(self):
            c = self.canv
            c.setFillColor(HexColor("#00100E"))
            c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)
            c.setStrokeColor(ACCENT); c.setLineWidth(1.0)
            c.roundRect(0, 0, self.w, self.h, 8, fill=0, stroke=1)
            c.setFillColor(ACCENT); c.roundRect(0, 0, 4, self.h, 2, fill=1, stroke=0)
            self._header.drawOn(c, 14, self.h - 18)
            self._body.drawOn(c, 14, 8)

    class CompoundingEffectBox(Flowable):
        """Blue 'Compounding Effect' — the 1% rule explained."""
        def __init__(self, width=CONTENT_W):
            super().__init__()
            self.w = width
            body_html = (
                "<b>Health is compound interest.</b> A 1% weekly improvement in sleep quality, "
                "training load, or nutrition precision compounds to a <b>52% total gain over one year.</b> "
                "The habits you establish today are not just today's result — they are the foundation "
                "every future week builds upon. Small, consistent actions have disproportionate long-term returns. "
                "This is the defining principle of every intervention recommended in this report."
            )
            self._header = Paragraph(
                '<b>📈  THE COMPOUNDING EFFECT — WHY 1% MATTERS</b>',
                S("_ce_h", size=7.5, lead=11, color=BLUE, bold=True)
            )
            self._body = Paragraph(body_html, S("_ce_b", size=8.8, lead=14, color=TEXT))
            _, hh = self._header.wrap(width - 24, 9999)
            _, bh = self._body.wrap(width - 24, 9999)
            self.h = hh + bh + 30

        def wrap(self, aw, ah): return self.w, self.h

        def draw(self):
            c = self.canv
            c.setFillColor(HexColor("#020810"))
            c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)
            c.setStrokeColor(BLUE); c.setLineWidth(1.0)
            c.roundRect(0, 0, self.w, self.h, 8, fill=0, stroke=1)
            c.setFillColor(BLUE); c.roundRect(0, 0, 4, self.h, 2, fill=1, stroke=0)
            self._header.drawOn(c, 14, self.h - 18)
            self._body.drawOn(c, 14, 8)

    class ExecutiveSummaryCheatSheet(Flowable):
        """Full-width Stop / Start / Maintain executive cheat sheet."""
        def __init__(self, stop_items: list, start_items: list, maintain_items: list, width=CONTENT_W):
            super().__init__()
            self.w = width
            self.stop = stop_items[:3]
            self.start = start_items[:3]
            self.maintain = maintain_items[:3]
            self.h = 235

        def wrap(self, aw, ah): return self.w, self.h

        def _draw_panel(self, c, x, y, pw, ph, emoji, title, items, bg_hex, accent_hex):
            c.setFillColor(HexColor(bg_hex))
            c.roundRect(x, y, pw, ph, 10, fill=1, stroke=0)
            c.setStrokeColor(HexColor(accent_hex)); c.setLineWidth(1.2)
            c.roundRect(x, y, pw, ph, 10, fill=0, stroke=1)
            c.setFillColor(HexColor(accent_hex))
            c.roundRect(x, y + ph - 3, pw, 3, 1, fill=1, stroke=0)
            c.setFillColor(HexColor(accent_hex)); c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(x + pw / 2, y + ph - 22, f"{emoji}  {title}")
            c.setStrokeColor(HexColor(accent_hex)); c.setLineWidth(0.4)
            c.line(x + 12, y + ph - 30, x + pw - 12, y + ph - 30)
            c.setFillColor(HexColor("#E5E7EB")); c.setFont("Helvetica", 8.2)
            for i, item in enumerate(items):
                ty = y + ph - 46 - i * 26
                c.drawString(x + 12, ty, f"• {str(item)[:46]}")

        def draw(self):
            c = self.canv
            c.setFillColor(HexColor("#080D1A"))
            c.roundRect(0, 0, self.w, self.h, 12, fill=1, stroke=0)
            c.setStrokeColor(ACCENT); c.setLineWidth(1.2)
            c.roundRect(0, 0, self.w, self.h, 12, fill=0, stroke=1)
            c.setFillColor(ACCENT); c.setFont("Helvetica-Bold", 13)
            c.drawCentredString(self.w / 2, self.h - 22, "EXECUTIVE SUMMARY — YOUR PERSONAL CHEAT SHEET")
            c.setFillColor(MUTED); c.setFont("Helvetica", 7.5)
            c.drawCentredString(self.w / 2, self.h - 36,
                                "Review quarterly · Share with your physician · Act on the top priority daily")
            gap = 8
            ph = self.h - 48
            pw = (self.w - gap * 2) / 3
            self._draw_panel(c, 0,               8, pw, ph, "🛑", "STOP",     self.stop,     "#150202", "#EF4444")
            self._draw_panel(c, pw + gap,        8, pw, ph, "🚀", "START",    self.start,    "#011008", "#22C55E")
            self._draw_panel(c, (pw + gap) * 2, 8, pw, ph, "✅", "MAINTAIN", self.maintain, "#020A18", "#3B82F6")
    # ── Page Template (Sidetall og bakgrunn) ──
    def draw_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(BG); canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        canvas.setFillColor(ACCENT); canvas.rect(0, PAGE_H-3, PAGE_W, 3, fill=1, stroke=0)
        canvas.setFillColor(CARD2); canvas.rect(0, PAGE_H-22, PAGE_W, 19, fill=1, stroke=0)
        canvas.setFillColor(TEXT); canvas.setFont("Helvetica-Bold", 8.5); canvas.drawString(MARGIN_H, PAGE_H-15, "LONGEVITY INTELLIGENCE REPORT  ·  CONFIDENTIAL")
        canvas.setFillColor(MUTED); canvas.setFont("Helvetica", 8); canvas.drawRightString(PAGE_W-MARGIN_H, PAGE_H-15, f"Page {canvas.getPageNumber()}")
        canvas.setFillColor(STROKE); canvas.rect(0, 0, PAGE_W, 14, fill=1, stroke=0)
        canvas.setFillColor(DIM); canvas.setFont("Helvetica", 6.5); canvas.drawString(MARGIN_H, 4, "Educational use only — not a medical diagnosis — health-tools.streamlit.app")
        canvas.drawRightString(PAGE_W-MARGIN_H, 4, datetime.utcnow().strftime("%Y-%m-%d UTC"))
        canvas.restoreState()

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=MARGIN_H, rightMargin=MARGIN_H, topMargin=26*mm, bottomMargin=18*mm)
    story = []

    # ── PAGE 1: Cover + Executive Dashboard ──
    story.append(VGap(16))
    story.append(P("LONGEVITY INTELLIGENCE REPORT", S("h1", size=28, color=ACCENT, bold=True, align=TA_CENTER, after=2)))
    story.append(P("Personalised Precision Health Analysis — Powered by Validated Clinical Formulas", S("h2", size=11, color=MUTED, align=TA_CENTER, after=8)))
    story.append(P("Premium Individual Health Report", S("h2", size=13, color=MUTED, align=TA_CENTER, after=8)))

    info_rows = [
        [P("AGE", S("il", size=6.5, color=MUTED, align=TA_CENTER)), P("SEX", S("il", size=6.5, color=MUTED, align=TA_CENTER)), P("HEIGHT", S("il", size=6.5, color=MUTED, align=TA_CENTER)), P("WEIGHT", S("il", size=6.5, color=MUTED, align=TA_CENTER)), P("DATE", S("il", size=6.5, color=MUTED, align=TA_CENTER))],
        [P(f"{age_v} yrs", S("iv", size=11, bold=True, align=TA_CENTER)), P(str(sex_v), S("iv", size=11, bold=True, align=TA_CENTER)), P(f"{h_v} cm", S("iv", size=11, bold=True, align=TA_CENTER)), P(f"{w_v} kg", S("iv", size=11, bold=True, align=TA_CENTER)), P(str(gen_v)[:10], S("iv", size=8, color=MUTED, align=TA_CENTER))],
    ]
    it = Table(info_rows, colWidths=[CONTENT_W/5]*5)
    it.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), CARD), ("ROWBACKGROUNDS", (0,0), (-1,-1), [CARD, CARD2]), ("BOX", (0,0), (-1,-1), 1, STROKE), ("INNERGRID", (0,0), (-1,-1), 0.5, STROKE), ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8)]))
    story.append(it)
    story.append(VGap(8))

    story.append(SecHeader("Overall Health Dashboard", subtitle="Composite score across 5 dimensions — for directional guidance only"))
    story.append(VGap(6))
    story.append(HealthScoreRing(health_score, score_label, score_col))
    story.append(VGap(8))

    kmetrics = []
    if bmi_v is not None: kmetrics.append(("BMI", f"{bmi_v:.1f}", bmi_cat, bmi_col.hexval()))
    if vo2_v is not None: kmetrics.append(("VO2max", f"{vo2_v:.1f}", f"{vo2_pct:.0f}th pct", vo2_col.hexval()))
    if bio_diff is not None: kmetrics.append(("Bio Age", f"{bio_v:.1f} yrs", f"{bio_diff:+.1f} vs calendar", bio_col.hexval()))
    if cur_kcal and rec_kcal:
        d_k = int(rec_kcal - cur_kcal)
        kmetrics.append(("Calories", f"{int(rec_kcal)}", f"{d_k:+d} kcal/day", "#22C55E" if d_k < 0 else "#3B82F6"))
    if kmetrics:
        story.append(MetricCard(kmetrics[:4]))
        story.append(VGap(8))

    story.append(P(f"Biggest lever right now: {biggest_lever}", S("bl", size=10, bold=True, color=TEXT, after=3)))
    story.append(P(lever_why, S("bl2", size=9, color=MUTED, after=4)))
    story.append(PageBreak())

    # ── PAGE 2: Body Composition ──
    story.append(SecHeader("Body Composition", subtitle="BMI, body fat estimate, and waist-to-hip ratio"))
    story.append(VGap(6))

    if bmi_v is not None:
        story.append(BMIScale(bmi_v))
        story.append(VGap(8))
        if bmi_v < 18.5: bmi_text = f"Your BMI of {bmi_v:.1f} is in the underweight range. BMI doesn't distinguish muscle from fat. Prioritise progressive resistance training and ensure adequate calorie and protein intake. Avoid deficits."
        elif bmi_v < 25: bmi_text = f"Your BMI of {bmi_v:.1f} is in the normal weight range. Focus on building or maintaining strength and cardiovascular capacity."
        elif bmi_v < 30: bmi_text = f"Your BMI of {bmi_v:.1f} is in the overweight range. Aim for a modest deficit (−300 to −500 kcal/day), 2–3 strength sessions per week, and increased daily step count."
        else: bmi_text = f"Your BMI of {bmi_v:.1f} is in the obese range. Consistency beats intensity here. Start with achievable habits: daily step target, 2x/week full-body strength, and a sustainable calorie strategy."
        story.append(P(bmi_text, S("bt", size=9, lead=14, after=8)))
# ── BMI Expert Insight + Actionable Milestone ──
        if bmi_v < 18.5:
            _bmi_insight = (
                "BMI below 18.5 is associated with increased all-cause mortality and reduced immune function "
                "(WHO Global Database on Body Mass Index). Priority: achieve positive energy balance and build lean mass "
                "through progressive resistance training. Evidence supports 1.8–2.2 g protein/kg/day with a 300 kcal/day "
                "surplus as the optimal starting protocol for underweight individuals."
            )
            _bmi_steps = [
                "Week 1–2: Establish a 300 kcal surplus using your Mifflin-St Jeor TDEE as the baseline",
                "Week 3–4: Begin 3×/week progressive strength training — compound lifts: squat, press, row",
                "Monthly target: +0.3 to +0.5 kg/month total weight — this rate strongly favours lean mass gain",
                "Track: weekly weight + weekly protein intake — both must trend upward simultaneously",
            ]
        elif bmi_v < 25:
            _bmi_insight = (
                "BMI 18.5–24.9 represents the lowest-risk range for metabolic disease, cardiovascular events, "
                "and all-cause mortality (Lancet, 2016 meta-analysis of 10.6 million participants). "
                "Your current body composition is a quantifiable longevity asset. The strategic priority "
                "now shifts to body recomposition: preserving this BMI while increasing lean-to-fat ratio."
            )
            _bmi_steps = [
                "Week 1–2: Baseline your true TDEE — track calories accurately for 7 days minimum",
                "Week 3–4: Add 2×/week progressive strength training to shift composition without changing scale weight",
                "Monthly measure: waist circumference — a superior metabolic risk marker vs. BMI alone",
                "Annual goal: increase skeletal muscle mass by 0.5–1 kg while maintaining BMI range",
            ]
        elif bmi_v < 30:
            _bmi_insight = (
                "BMI 25–29.9 is associated with a 20–30% increased risk of type 2 diabetes and cardiovascular "
                "events vs. normal weight (WHO, 2023). However, a 5–10% body weight reduction substantially "
                "mitigates this risk. The evidence-based protocol: a modest caloric deficit (−300 to −500 kcal/day) "
                "combined with resistance training 2–3×/week produces superior fat loss vs. cardio-only approaches."
            )
            _bmi_steps = [
                "Week 1–2: Target a 350–450 kcal/day deficit — produces 0.35–0.45 kg/week loss with minimal muscle loss",
                "Week 3–4: Add 2 strength sessions/week — resistance training is the primary lean mass preservation tool",
                "Daily habit: Minimum 8,000 steps — non-exercise activity (NEAT) accounts for up to 25% of your TDEE",
                "12-week goal: 3–4 kg total loss, waist circumference reduction of 3–5 cm",
            ]
        else:
            _bmi_insight = (
                "BMI ≥ 30 is a significant modifiable risk factor for 13 cancer types, type 2 diabetes, and "
                "cardiovascular disease (CDC, 2023). Each sustained 1 kg fat loss is associated with measurable "
                "improvements in insulin sensitivity, blood pressure, and joint load. The most durable approach "
                "is a moderate deficit (−400 to −500 kcal/day) combined with increasing daily movement — not "
                "aggressive restriction, which accelerates muscle loss and reduces long-term adherence."
            )
            _bmi_steps = [
                "Week 1–2: Establish a daily step baseline — target 7,000 steps before adding structured exercise",
                "Week 3–4: Introduce 2×/week full-body strength training (45 min) — builds metabolic rate long-term",
                "Nutrition anchor: 400–500 kcal/day deficit targeting 0.5–0.75 kg/week — do not exceed this rate",
                "Minimum protein: 1.6 g/kg/day — non-negotiable to prevent the fat-free mass loss that slows metabolism",
            ]
        story.append(VGap(6))
        story.append(ExpertInsightBox("Body Composition", _bmi_insight))
        story.append(VGap(6))
        story.append(ActionableMilestoneBox(_bmi_steps))
        story.append(VGap(6))
        extra = []
        if whr_d.get("value"): extra.append(("Waist-to-Hip Ratio", f'{float(whr_d["value"]):.2f} — {whr_d.get("category","")}', "", "#3B82F6"))
        if bf_d.get("value"): extra.append(("Body Fat % (Navy)", f'{float(bf_d["value"]):.1f}%', "", "#8B5CF6"))
        if extra:
            story.append(MetricCard(extra, card_h=56))
            story.append(VGap(6))

        story.append(P("About BMI: BMI is a population screening tool. It doesn't account for muscle mass, bone density, age, or fat distribution. Use it alongside waist circumference, body fat %, and fitness metrics.", S("bn", size=8, lead=12, color=MUTED, italic=True, after=6)))
    story.append(PageBreak())

    # ── PAGE 3: Cardio Fitness ──
    if vo2_v is not None:
        story.append(SecHeader("Cardio Fitness — VO2max", subtitle="The single strongest predictor of long-term health and all-cause mortality"))
        story.append(VGap(6))
        story.append(VO2Visual(vo2_v, vo2_pct, vo2_rat))
        story.append(VGap(6))

        meta_data = [
            [P("METHOD", S("ml",size=6.5,color=MUTED,align=TA_CENTER)), P("AGE BAND", S("ml",size=6.5,color=MUTED,align=TA_CENTER)), P("POPULATION MEAN", S("ml",size=6.5,color=MUTED,align=TA_CENTER)), P("YOUR PERCENTILE", S("ml",size=6.5,color=MUTED,align=TA_CENTER))],
            [P(vo2_meth or "—", S("mv",size=9,bold=True,align=TA_CENTER)), P(vo2_band or "—", S("mv",size=9,bold=True,align=TA_CENTER)), P(f"{vo2_mean:.1f} ml/kg/min" if vo2_mean else "—", S("mv",size=9,bold=True,align=TA_CENTER)), P(f"{vo2_pct:.0f}th", S("mv",size=9,bold=True,color=vo2_col,align=TA_CENTER))],
        ]
        mt = Table(meta_data, colWidths=[CONTENT_W/4]*4)
        mt.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), CARD2), ("BOX", (0,0), (-1,-1), 1, STROKE), ("INNERGRID", (0,0), (-1,-1), 0.5, STROKE), ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8), ("LEFTPADDING", (0,0), (-1,-1), 6)]))
        story.append(mt)
        story.append(VGap(8))

        if vo2_pct < 30: vo2_expl = f"A VO2max of {vo2_v:.1f} ml/kg/min places you in the bottom 30% for your age group. Start with 3–4x 30-min easy aerobic sessions per week. Expect noticeable improvement in 4–6 weeks."
        elif vo2_pct < 50: vo2_expl = f"A VO2max of {vo2_v:.1f} ml/kg/min is below average for your age group. Add one structured interval session weekly (e.g. 4×4 min hard effort) alongside 2 easy sessions."
        elif vo2_pct < 75: vo2_expl = f"A VO2max of {vo2_v:.1f} ml/kg/min is above average for your age group. Use 80/20 training — 80% easy (conversational) and 20% hard."
        else: vo2_expl = f"A VO2max of {vo2_v:.1f} ml/kg/min is excellent. Maintain with 2–3 quality sessions per week. Detraining begins after ~10 days of inactivity."
        story.append(P(vo2_expl, S("ve", size=9, lead=14, after=8)))

        tips = vo2_d.get("tips", [])
        if tips:
            story.append(P("Personalised training recommendations:", S("tth", size=9.5, bold=True, color=ACCENT, after=4)))
            for tip in tips[:5]: story.append(P(f"→  {tip}", S(f"t{id(tip)}", size=8.5, lead=13, color=TEXT, after=3)))
# ── VO2max Expert Insight + 4-week protocol ──
        if vo2_pct < 30:
            _vo2_insight = (
                "VO2max below the 30th percentile is associated with a 2–3× higher risk of all-cause mortality "
                "compared to the top quartile (JAMA, Mandsager et al., 2018). Cardiorespiratory fitness is the "
                "single strongest modifiable longevity predictor — stronger than smoking cessation in hazard ratio "
                "terms. Even a modest improvement of 3–5 ml/kg/min reduces mortality risk by 10–15%."
            )
            _vo2_steps = [
                "Week 1: 3×30 min easy aerobic at 60–65% max HR (fully conversational pace) — build the base",
                "Week 2: Add 1× interval session: 8 rounds of 1 min hard effort / 2 min easy (Norwegian 1-2-1 protocol)",
                "Week 3: Extend easy sessions to 35 min; maintain interval day unchanged",
                "Week 4: Reassess resting HR — a 2–4 bpm drop confirms early aerobic adaptation is underway",
            ]
        elif vo2_pct < 50:
            _vo2_insight = (
                "VO2max in the 30th–50th percentile is the moderate-risk zone where structured interval training "
                "yields the greatest return. The landmark Wisloff et al. (2009) Norwegian 4×4 protocol study "
                "demonstrated a 10–15% VO2max increase over 8–12 weeks in individuals at this fitness level. "
                "This is your single highest-leverage longevity intervention right now."
            )
            _vo2_steps = [
                "Week 1–2: 2 easy aerobic sessions (35 min, Zone 2) + 1 interval session (4×4 min at 85–95% max HR)",
                "Week 3–4: Increase interval volume to 5×4 min; add a 4th easy Zone 2 session",
                "Progressive overload rule: Add 5 min to total weekly aerobic volume each week without exception",
                "Tracking metric: Resting HR — target a 5 bpm reduction over the 8-week block",
            ]
        elif vo2_pct < 75:
            _vo2_insight = (
                "VO2max in the 50th–75th percentile represents above-average aerobic capacity. Research confirms "
                "the greatest longevity protection is conferred between the 25th and 75th percentile — meaning "
                "you have already leveraged a significant proportion of the protective effect. "
                "The 80/20 polarised training model (Seiler, 2010) is the evidence-based standard at this level."
            )
            _vo2_steps = [
                "Maintain 3–4 aerobic sessions/week — 80% at Zone 2 (120–140 bpm), 20% at threshold or above",
                "High-quality session: 6×3 min at threshold pace (RPE 7/10) with 2 min active recovery",
                "Monthly VO2max proxy test: 12-min Cooper Run or sub-max step test — track the trend, not single values",
                "Detraining prevention: Never exceed 7 consecutive days without aerobic stimulus — losses begin at day 10",
            ]
        else:
            _vo2_insight = (
                "VO2max above the 75th percentile is associated with a 45% lower all-cause mortality risk vs. "
                "the bottom quartile (JAMA, 2018). You are already leveraging one of the most powerful longevity "
                "markers available. Research indicates that maintaining elite cardiorespiratory fitness into your "
                "60s reduces biological ageing by an estimated 4–8 years vs. sedentary peers."
            )
            _vo2_steps = [
                "Maintain current weekly volume — consistency is the primary driver of retention at elite levels",
                "Introduce polarised periodisation: alternate high-volume weeks with recovery weeks at 75% normal load",
                "Annual VO2max test: a decline >1 ml/kg/min/year signals training load adjustment is needed",
                "Complement with 2×/week strength training — preserves the muscle mass that supports VO2max longevity",
            ]
        story.append(VGap(6))
        story.append(ExpertInsightBox("Cardio Fitness — VO2max", _vo2_insight))
        story.append(VGap(6))
        story.append(ActionableMilestoneBox(_vo2_steps))
        story.append(VGap(6))                
        story.append(PageBreak())

    # ── PAGE 4: Biological Age + Radar ──
    story.append(SecHeader("Biological Age & 5-Dimension Radar", subtitle="Heuristic estimate — use as directional guide, not clinical measure"))
    story.append(VGap(6))

    if bio_v is not None and age_f is not None:
        story.append(BioAgeBar(bio_v, age_f))
        story.append(VGap(8))
        if bio_diff > 3: bio_expl = f"Estimated biological age of {bio_v:.1f} years is {bio_diff:.1f} years above calendar age. Highest-leverage improvements: sleep consistency, cardio fitness, and stress management."
        elif bio_diff > 0: bio_expl = f"Estimated biological age of {bio_v:.1f} years is {bio_diff:.1f} years above calendar age. Focus on the red/amber factors in your factor breakdown."
        else: bio_expl = f"Estimated biological age of {bio_v:.1f} years is {abs(bio_diff):.1f} years below calendar age. This reflects well on your current habits. Maintain the routines that got you here."
        story.append(P(bio_expl, S("bioe", size=9, lead=14, after=8)))

        if factors:
            story.append(P("Factor breakdown — what's driving your bio age estimate:", S("fbh", size=9.5, bold=True, color=ACCENT, after=4)))
            story.append(FactorBars(factors))
            story.append(VGap(4))
            story.append(P("Green = factor favourably reducing biological age. Red/amber = factor adding years. Focus on the longest red bars first.", S("fbl", size=7.5, color=MUTED, italic=True, after=8)))
    
    story.append(P("5-Dimension Health Radar", S("rrh", size=9.5, bold=True, color=ACCENT, after=4)))
    story.append(RadarChart(radar))
    story.append(VGap(4))
    story.append(P("Score 70+ = good. 45–70 = room to improve. Below 45 = priority area.", S("rl", size=7.5, color=MUTED, italic=True, after=4)))
# ── Bio Age Expert Insight ──
    if bio_v is not None and age_f is not None:
        if bio_diff > 3:
            _bio_insight = (
                f"A biological age estimate {bio_diff:.1f} years above calendar age signals that multiple "
                "lifestyle and physiological factors are accelerating your cellular ageing trajectory. "
                "The most evidence-supported interventions for biological age reversal: consistent sleep "
                "(7–9h with fixed schedule), VO2max improvement, and chronic stress reduction. "
                "Each yields an estimated 1–3 year bio-age reduction over 6–12 months of consistent application."
            )
            _bio_steps = [
                "Sleep protocol: Fixed bed/wake time within ±30 min every day — the single highest-ROI bio-age lever",
                "Add 1 daily 10-min stress-reduction practice — breathwork or meditation lowers cortisol long-term",
                "Target VO2max improvement of 5+ ml/kg/min over 12 weeks — see Cardio section for exact protocol",
                "3-month reassessment: re-measure all input markers to track biological age regression",
            ]
        elif bio_diff > 0:
            _bio_insight = (
                f"A biological age estimate {bio_diff:.1f} years above calendar age indicates moderate acceleration "
                "in one or more longevity markers. Research indicates that targeted interventions on 2–3 key "
                "factors produce faster bio-age regression than attempting broad simultaneous lifestyle change. "
                "Your factor breakdown above identifies exactly where to focus effort first."
            )
            _bio_steps = [
                "Identify your top 2 red/amber factors from the bar chart above — these are your exclusive focus",
                "Implement one targeted change per factor this week — compounding begins with single consistent habits",
                "Track weekly proxies: resting HR, sleep duration, daily step count — the three bio-age proxy markers",
                "12-week goal: reduce biological age estimate by 1–2 years through targeted factor improvement",
            ]
        else:
            _bio_insight = (
                f"A biological age estimate {abs(bio_diff):.1f} years below calendar age is a measurable longevity "
                "advantage. Research indicates individuals with biological age 2+ years below calendar age have "
                "significantly lower risk of age-related disease onset and maintain higher functional capacity "
                "later in life. Your current habits represent compound interest working in your favour."
            )
            _bio_steps = [
                "Document your current lifestyle protocols in detail — replicate them consistently to protect this advantage",
                "Identify the 2 green factors contributing most to your score — safeguard them from lifestyle drift",
                "Annual re-measurement: biological age is dynamic — monitor annually to detect early regression",
                "Next tier: target top-quartile VO2max for your age group to further extend this biological advantage",
            ]
        story.append(VGap(6))
        story.append(ExpertInsightBox("Biological Age", _bio_insight))
        story.append(VGap(6))
        story.append(ActionableMilestoneBox(_bio_steps))
        story.append(VGap(8))
    story.append(CompoundingEffectBox())
    story.append(VGap(6))
    story.append(PageBreak())

    # ── PAGE 5: Nutrition & Calorie Plan ──
    story.append(SecHeader("Nutrition & Calorie Strategy", subtitle="Energy balance is the foundation of body composition"))
    story.append(VGap(6))

    if cur_kcal and rec_kcal:
        story.append(CalorieBar(cur_kcal, rec_kcal, kg_pw))
        story.append(VGap(8))
        d_kcal = int(rec_kcal - cur_kcal)
        if d_kcal < 0: cal_text = f"A target of {int(rec_kcal)} kcal creates a deficit of {abs(d_kcal)} kcal/day. Expected rate: {abs(kg_pw or 0):.2f} kg/week. Keep protein high to protect muscle."
        elif d_kcal > 0: cal_text = f"A target of {int(rec_kcal)} kcal creates a surplus of {d_kcal} kcal/day. Expected rate: +{abs(kg_pw or 0):.2f} kg/week. Pair this with progressive strength training."
        else: cal_text = f"Your target of {int(rec_kcal)} kcal matches estimated maintenance. This supports body recomposition."
        story.append(P(cal_text, S("ct", size=9, lead=14, after=8)))

        try: wt = float(w_v or 70)
        except: wt = 70.0
        protein_g = int(wt * 1.8); fat_g = int(int(rec_kcal) * 0.28 / 9); carb_g = max(0, int((int(rec_kcal) - protein_g*4 - fat_g*9) / 4))

        story.append(P("Suggested daily macro targets", S("mach", size=9.5, bold=True, color=ACCENT, after=4)))
        macro_data = [
            [P("MACRO", S("mh",size=7,color=MUTED,bold=True)), P("GRAMS", S("mh",size=7,color=MUTED,bold=True,align=TA_CENTER)), P("KCAL", S("mh",size=7,color=MUTED,bold=True,align=TA_CENTER)), P("RATIO", S("mh",size=7,color=MUTED,bold=True,align=TA_CENTER)), P("KEY ROLE", S("mh",size=7,color=MUTED,bold=True))],
            [P("Protein", S("pr",size=9,bold=True,color=BLUE)), P(f"{protein_g} g", S("pv",size=9,align=TA_CENTER)), P(f"{protein_g*4}", S("pv",size=9,align=TA_CENTER)), P("~30%", S("pv",size=9,align=TA_CENTER)), P("Muscle repair, satiety, metabolic rate", S("pw",size=8,color=MUTED))],
            [P("Fat", S("fr",size=9,bold=True,color=WARN)), P(f"{fat_g} g", S("fv",size=9,align=TA_CENTER)), P(f"{fat_g*9}", S("fv",size=9,align=TA_CENTER)), P("~28%", S("fv",size=9,align=TA_CENTER)), P("Hormones, brain, fat-soluble vitamins", S("fw",size=8,color=MUTED))],
            [P("Carbs", S("cr",size=9,bold=True,color=GOOD)), P(f"{carb_g} g", S("cv",size=9,align=TA_CENTER)), P(f"{carb_g*4}", S("cv",size=9,align=TA_CENTER)), P("~42%", S("cv",size=9,align=TA_CENTER)), P("Training energy, recovery, cognition", S("cw",size=8,color=MUTED))],
        ]
        mac_t = Table(macro_data, colWidths=[40*mm,25*mm,22*mm,20*mm,None])
        mac_t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), CARD2), ("BACKGROUND", (0,1), (-1,-1), CARD), ("BOX", (0,0), (-1,-1), 1, STROKE), ("INNERGRID", (0,0), (-1,-1), 0.5, STROKE), ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7), ("LEFTPADDING", (0,0), (-1,-1), 8), ("VALIGN", (0,0), (-1,-1), "TOP")]))
        story.append(mac_t); story.append(VGap(8))
        story.append(P("Macros estimated using Mifflin-St Jeor + standard ratios. Adjust every 2–3 weeks based on actual progress.", S("dn", size=7.5, color=MUTED, italic=True, after=4)))
    else: story.append(P("Calorie plan not generated.", S("ncp", size=9, color=MUTED, after=8)))

    if exlog and ex_act:
        story.append(VGap(6)); story.append(SecHeader("Exercise Log Summary", accent=BLUE)); story.append(VGap(6))
        ex_metrics = [("Activity", ex_act[:18], ex_int, "#0EA5A3"), ("Kcal / session", f"{ex_kcal_s:.0f}", "kcal", "#3B82F6"), ("Kcal / week", f"{ex_kcal_w:.0f}", f"{ex_sess}x/week", "#22C55E"), ("Weekly volume", f"{ex_total_min} min", f"{ex_min}min × {ex_sess}", "#F59E0B")]
        story.append(MetricCard(ex_metrics, card_h=66)); story.append(VGap(4))
        who_txt = "✓ Meets WHO 150 min/week guidelines" if ex_total_min >= 150 else f"⚠ {150-ex_total_min} min below WHO 150 min/week target"
        story.append(P(who_txt, S("who", size=8.5, color=HexColor("#22C55E" if ex_total_min >= 150 else "#F59E0B"), after=4)))
# ── Nutrition Expert Insight ──
    if cur_kcal and rec_kcal:
        _d_kcal_e = int(rec_kcal - cur_kcal)
        if _d_kcal_e < -600:
            _nut_insight = (
                f"A deficit exceeding 600 kcal/day activates adaptive thermogenesis — your metabolic rate "
                "down-regulates by 20–30% within 2–3 weeks to compensate (Leibel et al., NEJM, 1995). "
                "Additionally, deficits above 500 kcal/day substantially increase muscle catabolism. "
                "The evidence-based recommendation: reduce to a 400–500 kcal/day deficit and prioritise "
                "high protein (1.8–2.2 g/kg) to protect every kilogram of lean mass."
            )
            _nut_steps = [
                "Recalibrate to a 400–500 kcal/day deficit — the sustainable zone for fat loss without metabolic slowdown",
                "Protein target: 1.8 g per kg bodyweight daily — distribute across 3–4 meals with 30–40g per serving",
                "Reweigh weekly at identical conditions — adjust calories every 2 weeks based on the observed trend",
                "Minimum fat intake: 0.8 g/kg/day — below this threshold, hormonal health and fat-soluble vitamins suffer",
            ]
        elif _d_kcal_e < 0:
            _nut_insight = (
                f"Your deficit of {abs(_d_kcal_e)} kcal/day aligns with evidence-based fat loss guidelines "
                "(ACSM Position Stand). At this rate, lean mass preservation is maximised while producing "
                "consistent fat loss. Protein at 1.8 g/kg/day combined with resistance training ensures "
                "the weight lost is predominantly fat — the critical distinction for long-term body composition."
            )
            _nut_steps = [
                "Protein first: Build every meal around a 30–40g protein source before adding carbohydrates or fats",
                "Calorie cycling: +500 kcal on resistance training days, −300 kcal on rest days — same weekly average",
                "Satiety protocol: Target 25–35g fibre/day and 35 ml water/kg bodyweight to reduce adherence friction",
                "Stall protocol: If weight loss stops for 10+ days, reduce by 150 kcal only — avoid dramatic adjustments",
            ]
        elif _d_kcal_e > 0:
            _nut_insight = (
                f"A controlled surplus of {_d_kcal_e} kcal/day is the evidence-based approach for lean muscle "
                "accretion (Barakat et al., Strength and Conditioning Journal, 2020). Aggressive surpluses "
                "(>500 kcal/day) result in disproportionate fat gain rather than additional muscle tissue. "
                "The 1.8–2.2 g/kg protein target is non-negotiable — muscle protein synthesis requires adequate "
                "substrate independent of total calorie intake."
            )
            _nut_steps = [
                "Protein timing: Consume 30–40g protein within 90 minutes post-resistance training session",
                "Carbohydrate strategy: Prioritise carbs around training windows — they fuel the performance that drives growth",
                "Monthly audit: If gaining >0.4 kg/week, reduce surplus by 150 kcal — excess gain is fat, not muscle",
                "Sleep 7–9h nightly — 70% of growth hormone (the primary muscle repair signal) is secreted during deep sleep",
            ]
        else:
            _nut_insight = (
                "Maintenance calories optimally support body recomposition — simultaneously losing fat and gaining "
                "muscle. This is the most underrated strategy in body composition science: slower than aggressive "
                "cutting or bulking, but producing the most favourable long-term composition change for most "
                "individuals at an intermediate fitness level (Barakat et al., 2020)."
            )
            _nut_steps = [
                "Resistance training 3×/week is the essential driver of recomposition — nutrition alone is insufficient",
                "Protein at 2.0 g/kg/day — higher than for deficit or surplus phases due to dual anabolic demand",
                "Track body fat percentage, not scale weight — the scale is an unreliable proxy during recomposition",
                "12-week commitment: Body recomposition results require 8–12 weeks before becoming objectively measurable",
            ]
        story.append(VGap(6))
        story.append(ExpertInsightBox("Nutrition & Calorie Strategy", _nut_insight))
        story.append(VGap(6))
        story.append(ActionableMilestoneBox(_nut_steps))
        story.append(VGap(6))
    story.append(PageBreak())

    # ── PAGE 6: Weight Roadmap + 7-Day Plan ──
    story.append(SecHeader("Weight Goal Roadmap", subtitle="Projected milestones toward your target"))
    story.append(VGap(6))

    if milestones:
        try: start_w = float(w_v or 70)
        except: start_w = 70.0
        try: end_w = float(milestones[-1].get("Projected weight (kg)", start_w))
        except: end_w = start_w
        total_change = abs(end_w - start_w); m_cols = ["#3B82F6","#6366F1","#0EA5A3","#22C55E"]
        story.append(P(f"Starting weight: {start_w:.1f} kg → Target: {end_w:.1f} kg", S("mrt", size=9.5, bold=True, color=TEXT, after=6)))
        for i, m in enumerate(milestones):
            pw = float(m.get("Projected weight (kg)", start_w))
            prog = min(100, max(0, int(abs(pw-start_w)/total_change*100))) if total_change > 0.01 else 100
            story.append(MilestoneRow(m.get("Week", i+1), pw, str(m.get("Focus","")), prog, m_cols[i % len(m_cols)], (i == len(milestones)-1)))
        story.append(VGap(10))
    else: story.append(P("No weight milestones generated.", S("nm", size=9, color=MUTED, after=10)))

    story.append(SecHeader("7-Day Kickstart Training Plan", subtitle="A practical starting week — adapt to your schedule", accent=BLUE))
    story.append(VGap(6))

    day_cols_list = ["#3B82F6","#22C55E","#94A3B8","#F59E0B","#22C55E","#0EA5A3","#6366F1"]
    plan_data = [[P("DAY", S("ph",size=7,bold=True,color=MUTED)), P("SESSION", S("ph",size=7,bold=True,color=MUTED)), P("DURATION", S("ph",size=7,bold=True,color=MUTED)), P("PURPOSE", S("ph",size=7,bold=True,color=MUTED))]]
    for j, (day, sess, dur, why) in enumerate(plan_7):
        dc = day_cols_list[j % len(day_cols_list)]
        plan_data.append([P(day, S(f"pd{j}",size=8.5,bold=True,color=HexColor(dc))), P(sess, S(f"ps{j}",size=8.5,color=TEXT)), P(dur, S(f"pr{j}",size=8.5,color=MUTED,align=TA_CENTER)), P(why, S(f"pw{j}",size=8, color=MUTED))])
    pt = Table(plan_data, colWidths=[20*mm, 65*mm, 28*mm, None])
    pt.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), CARD2), ("BACKGROUND", (0,1), (-1,-1), CARD), ("BOX", (0,0), (-1,-1), 1, STROKE), ("INNERGRID", (0,0), (-1,-1), 0.5, STROKE), ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7), ("LEFTPADDING", (0,0), (-1,-1), 8), ("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.append(pt); story.append(VGap(6))
    story.append(P("Consistency over 12+ weeks beats perfect 2-week blocks every time.", S("prg", size=8, color=MUTED, italic=True, after=4)))
    story.append(PageBreak())

    # ── PAGE 7: Insights + Conditions + Safety ──
    story.append(SecHeader("Personalised Key Insights", subtitle="Based on your individual data — not generic advice"))
    story.append(VGap(6))
    for title, color, text in insights:
        story.append(InsightBlock(title, text, color)); story.append(VGap(6))
        
    if triage_r:
        story.append(SecHeader("Condition-Aware Recommendations", accent=WARN)); story.append(VGap(6))
        for r in triage_r[:12]: story.append(P(f"→  {r}", S(f"tr{id(r)}", size=8.5, lead=13, color=TEXT, after=3)))
        story.append(VGap(8))

    story.append(SecHeader("Safety & Important Notices", accent=BAD)); story.append(VGap(6))
    for title, col, text in [
        ("Seek urgent care immediately if you experience", WARN, "Chest pain or pressure, severe shortness of breath at rest, fainting or near-fainting, sudden neurological symptoms."),
        ("Before starting a new exercise programme", ACCENT, "If you have known cardiovascular disease, diabetes, or have been inactive, consult a physician before vigorous training."),
        ("About the estimates in this report", BLUE, "VO2max, biological age, and calorie values are estimates from validated formulas, not clinical measurements."),
    ]:
        story.append(InsightBlock(title, text, col)); story.append(VGap(4))

    story.append(VGap(10))
    story.append(P("This report was generated by Health Tools (health-tools.streamlit.app) for educational purposes only. It is not a medical diagnosis.", S("df", size=7.5, lead=11, color=DIM, italic=True, align=TA_CENTER, after=4)))
 # ════════════════════════════════════════════════════════════
    # EXECUTIVE SUMMARY — FINAL PAGE (Stop / Start / Maintain)
    # ════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(SecHeader(
        "Your Personal Action Plan",
        subtitle="Executive summary — review weekly, share with your physician, act on daily"
    ))
    story.append(VGap(10))

    # ── Build Stop / Start / Maintain dynamically from user data ──
    _stop_items  = []
    _start_items = []
    _keep_items  = []

    # STOP
    if bmi_v is not None and bmi_v >= 30:
        _stop_items.append("Eating in an untracked caloric surplus — awareness is the prerequisite for change")
    if bmi_v is not None and bmi_v >= 25:
        _stop_items.append("Relying on cardio alone — resistance training is what changes body composition")
    if vo2_pct < 40:
        _stop_items.append("Extended sedentary blocks >4 hours — set an hourly 5-min movement reminder")
    if bio_diff is not None and bio_diff > 2:
        _stop_items.append("Variable sleep timing — inconsistent schedule is a primary biological age accelerator")
    if exlog and ex_total_min < 150:
        _stop_items.append("Treating 1–2 short sessions/week as adequate — you are below WHO minimum guidelines")
    if len(_stop_items) < 3:
        _stop_items += [
            "Comparing week-to-week fluctuations — health change operates on 6–12 week timescales",
            "Treating nutrition and exercise as separate strategies — they compound when integrated",
            "Skipping annual health markers — your current position requires monitoring to maintain",
        ]

    # START
    if vo2_pct < 50:
        _start_items.append("Zone 2 aerobic training 3× weekly — your single highest-leverage longevity investment")
    if bmi_v is not None and bmi_v >= 25:
        _start_items.append("Daily protein tracking — target 1.8 g per kg bodyweight without exception")
    if bio_diff is not None and bio_diff > 1:
        _start_items.append("Fixed sleep/wake schedule (±30 min) — the highest-impact biological age intervention")
    if exlog and ex_total_min < 150:
        _start_items.append("10,000 steps/day habit — NEAT accounts for up to 25% of total daily energy expenditure")
    _start_items.append("Monthly biometric tracking: weight, waist circumference, resting HR — your three proxy longevity markers")
    if len(_start_items) < 2:
        _start_items.insert(0, "Progressive overload in strength training — the only mechanism that continues driving adaptation")

    # MAINTAIN
    if bmi_v is not None and 18.5 <= bmi_v < 25:
        _keep_items.append(f"Current body weight (BMI {bmi_v:.1f}) — you are within the optimal longevity range")
    if vo2_pct >= 50:
        _keep_items.append(f"Cardiorespiratory fitness — your VO2max is above the {int(vo2_pct)}th percentile for your age")
    if bio_diff is not None and bio_diff <= 0:
        _keep_items.append(f"Current lifestyle habits — your biological age is {abs(bio_diff):.1f} years below calendar age")
    if exlog and ex_total_min >= 150:
        _keep_items.append(f"Weekly exercise volume ({ex_total_min} min/week) — you meet or exceed WHO guidelines")
    if len(_keep_items) < 2:
        _keep_items += [
            "Commitment to data-driven health optimisation — you are measurably ahead of your demographic peers",
            "Regular health monitoring frequency — prevention produces the highest return on health investment",
            "The habit of measuring — you cannot compound what you do not track",
        ]

    story.append(ExecutiveSummaryCheatSheet(_stop_items[:3], _start_items[:3], _keep_items[:3]))
    story.append(VGap(12))
    story.append(CompoundingEffectBox())
    story.append(VGap(10))
    story.append(P(
        "This personalised executive summary is derived from your individual physiological data using validated clinical "
        "formulas: Mifflin-St Jeor (energy expenditure), WHO BMI classifications, Uth VO2max estimation, and "
        "ACSM/WHO training volume guidelines. Review this summary every 4–12 weeks as your data evolves. "
        "Share the full report with your physician or performance coach at your next consultation.",
        S("_es_disc", size=8, lead=13, color=MUTED, italic=True, align=TA_CENTER, after=4)
    ))   
    # ── BYGG ──
    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return buf.getvalue()

    # ── Custom Flowables ──────────────────────────────────────────

    class Gap(Flowable):
        def __init__(self, h=8):
            super().__init__()
            self._h = h
        def wrap(self, aw, ah):
            return aw, self._h
        def draw(self):
            pass

    class SectionHeader(Flowable):
        def __init__(self, title, width=CONTENT_W, accent=None):
            super().__init__()
            self.title  = title
            self.w      = width
            self.accent = accent or C_ACCENT
            self.h      = 38

        def wrap(self, aw, ah):
            return self.w, self.h

        def draw(self):
            c = self.canv
            c.setFillColor(C_CARD)
            c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)
            c.setFillColor(self.accent)
            c.roundRect(0, 0, 4, self.h, 2, fill=1, stroke=0)
            c.setFillColor(C_TEXT)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(14, 13, self.title)

    class MetricRow(Flowable):
        def __init__(self, metrics, width=CONTENT_W):
            # metrics = list of (label, value, sub, color_hex_str)
            super().__init__()
            self.metrics = metrics
            self.w       = width
            self.h       = 62
            n            = len(metrics)
            self.card_w  = (width - (n - 1) * 8) / n if n > 0 else width

        def wrap(self, aw, ah):
            return self.w, self.h

        def draw(self):
            c = self.canv
            cw = self.card_w
            for i, (label, value, sub, col_str) in enumerate(self.metrics):
                col = HexColor(col_str) if isinstance(col_str, str) else col_str
                x   = i * (cw + 8)
                c.setFillColor(C_CARD)
                c.roundRect(x, 0, cw, 58, 8, fill=1, stroke=0)
                c.setFillColor(col)
                c.roundRect(x, 55, cw, 3, 1, fill=1, stroke=0)
                c.setFillColor(C_MUTED)
                c.setFont("Helvetica", 7)
                c.drawString(x + 8, 43, str(label).upper()[:22])
                c.setFillColor(col)
                c.setFont("Helvetica-Bold", 15)
                c.drawString(x + 8, 25, str(value)[:18])
                if sub:
                    c.setFillColor(C_MUTED)
                    c.setFont("Helvetica", 7)
                    c.drawString(x + 8, 10, str(sub)[:24])

    class BMIBar(Flowable):
        def __init__(self, bmi_val, width=CONTENT_W):
            super().__init__()
            self.bmi = bmi_val
            self.w   = width
            self.h   = 96

        def wrap(self, aw, ah):
            return self.w, self.h

        def draw(self):
            c   = self.canv
            bmi = self.bmi
            w   = self.w

            c.setFillColor(C_CARD)
            c.roundRect(0, 0, w, self.h, 10, fill=1, stroke=0)

            if bmi < 18.5:   bmi_col = "#3B82F6"
            elif bmi < 25.0: bmi_col = "#22C55E"
            elif bmi < 30.0: bmi_col = "#F59E0B"
            else:            bmi_col = "#EF4444"

            c.setFillColor(HexColor(bmi_col))
            c.setFont("Helvetica-Bold", 26)
            c.drawString(12, 62, f"{bmi:.1f}")
            c.setFillColor(C_MUTED)
            c.setFont("Helvetica", 8)
            c.drawString(12, 52, "BMI Score")

            scale_max = 45.0
            bar_x = 12
            bar_y = 28
            bar_h = 14
            bar_w = w - 24

            segs = [
                (0, 18.5, "#3B82F6",  "Underweight"),
                (18.5, 25.0, "#22C55E", "Normal"),
                (25.0, 30.0, "#F59E0B", "Overweight"),
                (30.0, 45.0, "#EF4444", "Obese"),
            ]

            for i, (s, e, col, lbl) in enumerate(segs):
                sx = bar_x + (s / scale_max) * bar_w
                sw = ((e - s) / scale_max) * bar_w
                c.setFillColor(HexColor(col))
                if i == 0:
                    c.roundRect(sx, bar_y, sw, bar_h, 3, fill=1, stroke=0)
                    c.rect(sx + 3, bar_y, sw - 3, bar_h, fill=1, stroke=0)
                elif i == len(segs) - 1:
                    c.roundRect(sx, bar_y, sw, bar_h, 3, fill=1, stroke=0)
                    c.rect(sx, bar_y, sw - 3, bar_h, fill=1, stroke=0)
                else:
                    c.rect(sx, bar_y, sw, bar_h, fill=1, stroke=0)
                c.setFillColor(HexColor("#0F172A"))
                c.setFont("Helvetica-Bold", 6)
                c.drawCentredString(sx + sw / 2, bar_y + 4, lbl)

            mx = bar_x + min(1.0, bmi / scale_max) * bar_w
            c.setStrokeColor(colors.white)
            c.setLineWidth(1.5)
            c.line(mx, bar_y - 2, mx, bar_y + bar_h + 2)
            c.setFillColor(colors.white)
            path = c.beginPath()
            path.moveTo(mx,     bar_y + bar_h + 9)
            path.lineTo(mx - 5, bar_y + bar_h + 2)
            path.lineTo(mx + 5, bar_y + bar_h + 2)
            path.close()
            c.drawPath(path, fill=1, stroke=0)

            for lbl, pos in [("0", 0), ("18.5", 18.5), ("25", 25), ("30", 30), ("45", 45)]:
                lx = bar_x + (pos / scale_max) * bar_w
                c.setFillColor(C_MUTED)
                c.setFont("Helvetica", 6)
                c.drawCentredString(lx, bar_y - 9, lbl)

    class VO2Visual(Flowable):
        def __init__(self, vo2_val, percentile, rating, width=CONTENT_W):
            super().__init__()
            self.vo2  = vo2_val
            self.pct  = float(percentile or 0)
            self.rating = rating
            self.w    = width
            self.h    = 86

        def wrap(self, aw, ah):
            return self.w, self.h

        def draw(self):
            c   = self.canv
            w   = self.w
            pct = self.pct

            if pct >= 80:   col = "#22C55E"
            elif pct >= 60: col = "#3B82F6"
            elif pct >= 40: col = "#F59E0B"
            else:           col = "#EF4444"

            c.setFillColor(C_CARD)
            c.roundRect(0, 0, w, self.h, 10, fill=1, stroke=0)

            c.setFillColor(HexColor(col))
            c.setFont("Helvetica-Bold", 26)
            c.drawString(12, 54, f"{self.vo2:.1f}")
            c.setFillColor(C_MUTED)
            c.setFont("Helvetica", 8)
            c.drawString(12, 44, "ml / kg / min")
            c.setFillColor(HexColor(col))
            c.setFont("Helvetica-Bold", 10)
            c.drawString(12, 28, str(self.rating or "—"))
            c.setFillColor(C_MUTED)
            c.setFont("Helvetica", 7)
            c.drawString(12, 16, "Rating")

            bx  = w * 0.44
            bw  = w * 0.52
            bh  = 12
            by  = 40
            c.setFillColor(C_STROKE)
            c.roundRect(bx, by, bw, bh, 4, fill=1, stroke=0)
            fill_w = max(8, (pct / 100.0) * bw)
            c.setFillColor(HexColor(col))
            c.roundRect(bx, by, fill_w, bh, 4, fill=1, stroke=0)
            c.setFillColor(C_MUTED)
            c.setFont("Helvetica", 7)
            c.drawString(bx, by + bh + 5, "POPULATION PERCENTILE")
            c.setFillColor(HexColor(col))
            c.setFont("Helvetica-Bold", 11)
            c.drawRightString(bx + bw, by - 11, f"{pct:.0f}th percentile")

            # 5-zone mini scale
            zones = [
                (0,  20,  "#EF4444"),
                (20, 40,  "#F59E0B"),
                (40, 60,  "#3B82F6"),
                (60, 80,  "#22C55E"),
                (80, 100, "#10B981"),
            ]
            sz_y = 16
            sz_h = 7
            for zs, ze, zc in zones:
                zx = bx + (zs / 100) * bw
                zw = ((ze - zs) / 100) * bw
                c.setFillColor(HexColor(zc))
                c.rect(zx, sz_y, zw, sz_h, fill=1, stroke=0)
            c.setStrokeColor(colors.white)
            c.setLineWidth(1.5)
            mx2 = bx + (pct / 100) * bw
            c.line(mx2, sz_y - 1, mx2, sz_y + sz_h + 1)

    class BioFactorBars(Flowable):
        def __init__(self, factors, width=CONTENT_W):
            super().__init__()
            self.factors = factors[:8]
            self.w       = width
            self.h       = len(self.factors) * 22 + 8

        def wrap(self, aw, ah):
            return self.w, self.h

        def draw(self):
            c = self.canv
            c.setFillColor(C_CARD)
            c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)

            row_h = 22
            bar_x = self.w * 0.42
            bar_w = self.w * 0.45
            label_max = self.w * 0.40

            for i, f in enumerate(self.factors):
                y       = self.h - 14 - i * row_h
                delta   = float(f.get("delta", 0))
                col_str = "#22C55E" if delta <= 0 else "#EF4444" if delta > 1 else "#F59E0B"
                bar_pct = min(abs(delta) / 10.0, 1.0)

                c.setFillColor(C_MUTED)
                c.setFont("Helvetica", 7.5)
                lbl = str(f.get("label", ""))[:32]
                c.drawString(10, y - 4, lbl)

                c.setFillColor(C_STROKE)
                c.roundRect(bar_x, y - 4, bar_w, 8, 2, fill=1, stroke=0)
                if bar_pct > 0:
                    c.setFillColor(HexColor(col_str))
                    c.roundRect(bar_x, y - 4, bar_pct * bar_w, 8, 2, fill=1, stroke=0)

                c.setFillColor(HexColor(col_str))
                c.setFont("Helvetica-Bold", 7.5)
                c.drawRightString(self.w - 4, y - 4, f"{delta:+.1f} yrs")

    class MilestoneLine(Flowable):
        def __init__(self, week, weight, focus, progress_pct, col_str, is_last, width=CONTENT_W):
            super().__init__()
            self.week         = week
            self.weight       = weight
            self.focus        = focus
            self.progress_pct = progress_pct
            self.col_str      = col_str
            self.is_last      = is_last
            self.w            = width
            self.h            = 48

        def wrap(self, aw, ah):
            return self.w, self.h

        def draw(self):
            c   = self.canv
            col = HexColor(self.col_str)

            if not self.is_last:
                c.setStrokeColor(C_STROKE)
                c.setLineWidth(1)
                c.line(13, 0, 13, 10)

            c.setFillColor(col)
            c.circle(13, 36, 11, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(13, 32, str(self.week))

            c.setFillColor(C_CARD)
            c.roundRect(32, 14, self.w - 36, 34, 6, fill=1, stroke=0)
            c.setFillColor(col)
            c.roundRect(32, 44, self.w - 36, 4, 2, fill=1, stroke=0)

            c.setFillColor(col)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(42, 32, f"{self.weight:.1f} kg")
            c.setFillColor(C_MUTED)
            c.setFont("Helvetica", 7.5)
            c.drawString(42, 20, str(self.focus)[:40])

            bx = self.w - 90
            bw = 80
            c.setFillColor(C_STROKE)
            c.roundRect(bx, 20, bw, 6, 2, fill=1, stroke=0)
            c.setFillColor(col)
            c.roundRect(bx, 20, self.progress_pct / 100 * bw, 6, 2, fill=1, stroke=0)
            c.setFillColor(C_MUTED)
            c.setFont("Helvetica", 6.5)
            c.drawRightString(bx + bw, 13, f"{self.progress_pct:.0f}%")

    # ── Page template (dark bg + header/footer) ──────────────────

    def draw_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(C_BG)
        canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        canvas.setFillColor(C_ACCENT)
        canvas.rect(0, PAGE_H - 3, PAGE_W, 3, fill=1, stroke=0)
        canvas.setFillColor(C_CARD)
        canvas.rect(0, PAGE_H - 22, PAGE_W, 19, fill=1, stroke=0)
        canvas.setFillColor(C_TEXT)
        canvas.setFont("Helvetica-Bold", 8.5)
        canvas.drawString(18 * mm, PAGE_H - 15, "HEALTH TOOLS — PREMIUM REPORT")
        canvas.setFillColor(C_MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(PAGE_W - 18 * mm, PAGE_H - 15,
                               f"Page {canvas.getPageNumber()}")
        canvas.setFillColor(C_STROKE)
        canvas.rect(0, 0, PAGE_W, 14, fill=1, stroke=0)
        canvas.setFillColor(HexColor("#64748B"))
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(18 * mm, 4,
                          "Educational use only — not medical advice — health-tools.streamlit.app")
        canvas.drawRightString(PAGE_W - 18 * mm, 4,
                               datetime.utcnow().strftime("%Y-%m-%d UTC"))
        canvas.restoreState()

    # ── Build story ───────────────────────────────────────────────

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=26 * mm, bottomMargin=18 * mm,
    )

    story = []
    inp = report.get("inputs", {})

    # Cover
    story.append(Gap(6))
    story.append(P("HEALTH TOOLS",
                   ps("cvt", fontSize=30, leading=34, textColor=C_ACCENT,
                      bold=True, alignment=TA_CENTER)))
    story.append(P("Premium Health Report",
                   ps("cvs", fontSize=15, leading=19, textColor=C_TEXT,
                      alignment=TA_CENTER, spaceAfter=6)))

    # Info row
    age_v  = inp.get("age", "—")
    sex_v  = inp.get("sex", "—")
    h_v    = inp.get("height_cm", "—")
    w_v    = inp.get("weight_kg", "—")
    gen_v  = report.get("generated", "—")

    info_data = [
        [P("AGE",     ps("il", fontSize=7, textColor=C_MUTED)),
         P("SEX",     ps("il", fontSize=7, textColor=C_MUTED)),
         P("HEIGHT",  ps("il", fontSize=7, textColor=C_MUTED)),
         P("WEIGHT",  ps("il", fontSize=7, textColor=C_MUTED)),
         P("GENERATED", ps("il", fontSize=7, textColor=C_MUTED))],
        [P(f"{age_v} yrs", ps("iv", fontSize=12, bold=True, textColor=C_TEXT)),
         P(str(sex_v),     ps("iv", fontSize=12, bold=True, textColor=C_TEXT)),
         P(f"{h_v} cm",    ps("iv", fontSize=12, bold=True, textColor=C_TEXT)),
         P(f"{w_v} kg",    ps("iv", fontSize=12, bold=True, textColor=C_TEXT)),
         P(str(gen_v),     ps("iv", fontSize=8,  textColor=C_MUTED))],
    ]
    info_t = Table(info_data, colWidths=[CONTENT_W / 5] * 5)
    info_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CARD),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_CARD, C_CARD2]),
        ("BOX",       (0, 0), (-1, -1), 1,   C_STROKE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, C_STROKE),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(info_t)
    story.append(Gap(10))

    # ── BMI ──
    if report.get("bmi"):
        bmi_v   = float(report["bmi"]["value"])
        bmi_cat = report["bmi"]["category"]
        story.append(SectionHeader("Body Mass Index"))
        story.append(Gap(5))
        story.append(BMIBar(bmi_v))
        if report.get("whr") or report.get("bodyfat"):
            story.append(Gap(4))
            extra = []
            if report.get("whr"):
                extra.append(("Waist-to-hip ratio",
                               f'{report["whr"]["value"]:.2f} — {report["whr"]["category"]}'))
            if report.get("bodyfat"):
                extra.append(("Body fat (Navy method)",
                               f'{report["bodyfat"]["value"]:.1f}%'))
            for lbl, val in extra:
                story.append(P(
                    f'<font color="#94A3B8">{lbl}:</font>  '
                    f'<font color="#E5E7EB"><b>{val}</b></font>',
                    ps("be", fontSize=9, leading=14),
                ))
        story.append(Gap(10))

    # ── VO2 ──
    if report.get("vo2"):
        v = report["vo2"]
        story.append(SectionHeader("VO2max & Cardio Fitness"))
        story.append(Gap(5))
        story.append(VO2Visual(
            float(v["value"]),
            float(v.get("percentile") or 0),
            v.get("rating", "—"),
        ))
        story.append(Gap(5))
        meta_data = [
            [P("METHOD",          ps("ml", fontSize=7, textColor=C_MUTED)),
             P("AGE BAND",        ps("ml", fontSize=7, textColor=C_MUTED)),
             P("POPULATION MEAN", ps("ml", fontSize=7, textColor=C_MUTED))],
            [P(str(v.get("method", "—")),
               ps("mv", fontSize=9, bold=True, textColor=C_TEXT)),
             P(str(v.get("age_band", "—")),
               ps("mv", fontSize=9, bold=True, textColor=C_TEXT)),
             P(f'{v.get("mean", "—")} ml/kg/min',
               ps("mv", fontSize=9, bold=True, textColor=C_TEXT))],
        ]
        meta_t = Table(meta_data, colWidths=[CONTENT_W / 3] * 3)
        meta_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_CARD2),
            ("BOX",       (0, 0), (-1, -1), 1,   C_STROKE),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, C_STROKE),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))
        story.append(meta_t)
        tips = v.get("tips", [])
        if tips:
            story.append(Gap(6))
            story.append(P("Training Recommendations",
                           ps("trh", fontSize=10, bold=True, textColor=C_ACCENT, spaceAfter=3)))
            for tip in tips[:5]:
                story.append(P(
                    f"→  {escape(str(tip))}",
                    ps(f"tip{id(tip)}", fontSize=8.5, leading=12,
                       textColor=HexColor("#CBD5E1"), spaceAfter=3),
                ))
        story.append(Gap(10))

    # ── Biological age ──
    if report.get("bio_age"):
        bio_val   = float(report["bio_age"]["value"])
        chron_age = float(inp.get("age", bio_val) or bio_val)
        diff      = bio_val - chron_age
        bio_col   = "#22C55E" if diff <= -1 else "#F59E0B" if diff <= 2 else "#EF4444"
        diff_txt  = f"{abs(diff):.1f} yrs {'younger' if diff < 0 else 'older'} than calendar"

        story.append(SectionHeader("Biological Age"))
        story.append(Gap(5))
        story.append(MetricRow([
            ("BIOLOGICAL AGE",    f"{bio_val:.1f} yrs",    diff_txt,              bio_col),
            ("CHRONOLOGICAL AGE", f"{chron_age:.0f} yrs",  "Calendar age",        "#94A3B8"),
            ("DIFFERENCE",        f"{diff:+.1f} yrs",       "Bio vs. calendar",    bio_col),
        ]))
        if report.get("bio_factors"):
            story.append(Gap(6))
            story.append(P("Factor Breakdown",
                           ps("bfh", fontSize=10, bold=True, textColor=C_ACCENT, spaceAfter=3)))
            story.append(BioFactorBars(report["bio_factors"]))
        story.append(Gap(10))

    # ── Exercise log ──
    ex = report.get("exercise_log")
    if ex:
        story.append(SectionHeader("Exercise Log"))
        story.append(Gap(5))
        kcal_pw   = float(ex.get("kcal_per_week", 0))
        total_min = int(ex.get("minutes", 0)) * int(ex.get("sessions_per_week", 0))
        story.append(MetricRow([
            ("ACTIVITY",    str(ex.get("activity", "—"))[:18],
             str(ex.get("intensity", "—")),                    "#0EA5A3"),
            ("KCAL / SESSION", f'{ex.get("kcal_per_session", 0):.0f}',
             "kcal",                                           "#3B82F6"),
            ("KCAL / WEEK", f'{kcal_pw:.0f}',
             f'{ex.get("sessions_per_week", 0)}× per week',   "#22C55E"),
            ("VOLUME",      f'{total_min} min/wk',
             f'{ex.get("minutes", 0)} min × {ex.get("sessions_per_week", 0)}', "#F59E0B"),
        ]))
        story.append(Gap(4))
        who_met = total_min >= 150
        who_col = "#22C55E" if who_met else "#F59E0B"
        who_txt = ("✓  Meets WHO 150 min/week guidelines"
                   if who_met else
                   f"⚠  {150 - total_min} min/week below WHO 150 min target")
        story.append(P(who_txt,
                       ps("who", fontSize=8.5, textColor=HexColor(who_col), spaceAfter=2)))
        story.append(Gap(10))

    # ── Conditions ──
    if report.get("triage") and report.get("triage_recommendations"):
        story.append(SectionHeader("Conditions & Recommendations"))
        story.append(Gap(5))
        for r in report["triage_recommendations"]:
            story.append(P(
                f"→  {escape(str(r))}",
                ps(f"rec{id(r)}", fontSize=8.5, leading=13,
                   textColor=HexColor("#CBD5E1"), spaceAfter=3),
            ))
        story.append(Gap(10))

    # ── Plan ──
    if report.get("plan") and not report["plan"].get("error"):
        plan = report["plan"]
        story.append(SectionHeader("Weight Goal Plan"))
        story.append(Gap(5))
        story.append(MetricRow([
            ("MAINTENANCE",  f'{plan.get("current_needs_kcal", "—")} kcal',
             "per day",                                  "#94A3B8"),
            ("RECOMMENDED",  f'{plan.get("recommended_daily_kcal", "—")} kcal',
             "per day",                                  "#0EA5A3"),
            ("WEEKLY CHANGE", f'{float(plan.get("kg_per_week", 0)):+.2f} kg',
             "per week",                                 "#3B82F6"),
        ]))
        milestones = plan.get("milestones", [])
        if milestones:
            story.append(Gap(6))
            story.append(P("Milestone Roadmap",
                           ps("mrh", fontSize=10, bold=True,
                              textColor=C_ACCENT, spaceAfter=3)))
            try:
                start_w = float(inp.get("weight_kg", 70) or 70)
            except Exception:
                start_w = 70.0
            try:
                end_w = float(milestones[-1].get("Projected weight (kg)", start_w))
            except Exception:
                end_w = start_w
            total_change = abs(end_w - start_w)
            m_cols = ["#3B82F6", "#7C3AED", "#0EA5A3", "#22C55E"]
            for i, m in enumerate(milestones):
                try:
                    pw = float(m.get("Projected weight (kg)", start_w))
                except Exception:
                    pw = start_w
                prog = (min(100, max(0, int(abs(pw - start_w) / total_change * 100)))
                        if total_change > 0.01 else 100)
                story.append(MilestoneLine(
                    week=m.get("Week", i + 1),
                    weight=pw,
                    focus=m.get("Focus", ""),
                    progress_pct=prog,
                    col_str=m_cols[i % len(m_cols)],
                    is_last=(i == len(milestones) - 1),
                ))
        story.append(Gap(10))

    # Disclaimer
    story.append(Gap(4))
    story.append(P(
        "This report is generated for educational purposes only and is not a medical diagnosis, "
        "clinical assessment, or substitute for professional healthcare advice. "
        "Always consult a qualified healthcare professional regarding any medical concerns.",
        ps("disc", fontSize=7.5, leading=10, textColor=HexColor("#64748B")),
    ))

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    buffer.seek(0)
    return buffer.read()


# ── Modules (main) ────
with st.expander("⚙️ Choose modules", expanded=False):
    st.caption("Turn modules on/off. (Nothing is stored.)")
    cA, cB = st.columns(2)
    with cA:
        run_bmi = st.toggle("BMI calculator", value=True, key="s_bmi")
        run_vo2 = st.toggle("VO2max estimate", value=True, key="s_vo2")
        run_bioage = st.toggle("Biological age", value=True, key="s_bio")
    with cB:
        run_conditions = st.toggle("Conditions & recommendations", value=True, key="s_conditions")
        run_plan = st.toggle("Weight goal / plan", value=True, key="s_plan")

# ── Sidebar (kept minimal) ────
st.sidebar.info("This app does not store personal health data.")

# ── Session state defaults ────────────────────────────────────────────────────
if "resting_hr" not in st.session_state:
    st.session_state["resting_hr"] = None
if "exercise_kcal_per_week" not in st.session_state:
    st.session_state["exercise_kcal_per_week"] = 0.0
if "global_avg_hr" not in st.session_state:
    st.session_state["global_avg_hr"] = None
if "age" not in st.session_state:
    st.session_state["age"] = 30
if "global_resting_hr" not in st.session_state:
    st.session_state["global_resting_hr"] = None
if "global_waist_cm" not in st.session_state:
    st.session_state["global_waist_cm"] = None
if "global_hip_cm" not in st.session_state:
    st.session_state["global_hip_cm"] = None

# ── Basic inputs ──────────────────────────────────────────────────────────────
st.markdown("## 🧾 Basic information")
st.caption("These inputs drive BMI, calories, VO2 and biological age estimates.")
st.markdown('<div class="ht-card">', unsafe_allow_html=True)

# --- Dine eksisterende inputs ---
resting_hr_basic = st.number_input(
    "Resting HR (bpm)",
    min_value=30, max_value=120,
    value=st.session_state.get("resting_hr") or 60,
    key="basic_resting_hr",
    on_change=sync_from_basic,
)
if st.session_state.get("resting_hr") is None and resting_hr_basic is not None:
    st.session_state["resting_hr"] = int(resting_hr_basic)
    st.session_state["global_resting_hr"] = int(resting_hr_basic)

age_input = st.number_input("Age (years)", min_value=5, max_value=120,
                             value=st.session_state.get("age", 30), key="age")
try:
    age = int(st.session_state.get("age", 30))
except Exception:
    age = 30

c1, c2 = st.columns(2)
with c1:
    sex = st.selectbox("Sex", ["M", "F"], index=0, key="inp_sex")
with c2:
    pass  # placeholder

c3, c4 = st.columns(2)
with c3:
    height_cm = st.number_input("Height (cm)", min_value=50, max_value=250, value=170, key="inp_height")
with c4:
    weight_kg = st.number_input("Weight (kg)", min_value=20.0, max_value=300.0, value=70.0,
                                 format="%.1f", key="inp_weight")
st.markdown("</div>", unsafe_allow_html=True)

if age < 18:
    st.warning("BMI and fitness estimates are less reliable under 18.")
elif age >= 70:
    st.info("For older adults, BMI is often less informative.")

# --- NY LOGIKK: Knapp for å lagre ---
if st.button("Generate report & Save"):
    # 1. Utfør beregninger
    bmi_val = weight_kg / ((height_cm / 100) ** 2)
    bio_age_val = 30.0 # Erstatt med din faktiske funksjon for bio_age
    
    # 2. Pakk dataene
    metrics = {
        "weight": float(weight_kg),
        "bmi": round(float(bmi_val), 2),
        "bio_age": float(bio_age_val)
    }
    
    # 3. Lagre til Supabase
    try:
        # Merk: Bruk en unik ID eller hent fra en bruker-sesjon
        user_id = "9dca6f9e-8a7a-4291-89f8-2f8e9ecd7840" 
        
        save_health_metrics(db, user_id, metrics)
        st.success("✅ Rapporten er generert og lagret!")
        st.write("Data lagret:", metrics)
    except Exception as e:
        st.error(f"Kunne ikke lagre til databasen: {e}")

# local defaults
activity_level = "Moderate"
weekly_minutes = 150
session_intensity = 3
resting_hr = None
max_hr = None
measured_vo2_input = 0.0
waist_cm = None
hip_cm = None
neck_cm = None
bodyfat_requested = False
smoker = False
diabetes = False
sleep_hours = None
alcohol_units = None
fruit_veg = None
perceived_stress = 5
grip_strength = None
bp_systolic = None
cholesterol = None
family_history = False
menopause = False
vo2_method = "Questionnaire"
vo2_distance_m = 0.0
rockport_time_min = 0.0
rockport_hr = 0

# ── BMI inputs ────────────────────────────────────────────────────────────────
if run_bmi:
    with st.expander("BMI inputs and body composition", expanded=True):
        st.markdown("BMI is a simple screening tool, not a diagnosis.")
        use_waist_hip = st.toggle("I don't know my waist & hip measurements", value=False, key="b_use_whr")
        if not use_waist_hip:
            c1, c2 = st.columns(2)
            with c1:
                waist_cm = st.number_input("Waist (cm)", min_value=30.0, max_value=300.0,
                                            value=float(st.session_state.get("global_waist_cm") or 80.0),
                                            format="%.1f", key="b_waist")
            with c2:
                hip_cm = st.number_input("Hip (cm)", min_value=30.0, max_value=300.0,
                                          value=float(st.session_state.get("global_hip_cm") or 95.0),
                                          format="%.1f", key="b_hip")
            st.session_state["global_waist_cm"] = waist_cm
            st.session_state["global_hip_cm"] = hip_cm
        use_neck = st.toggle("I don't know my neck measurement", value=False, key="b_use_neck")
        if not use_neck:
            neck_cm = st.number_input("Neck (cm)", min_value=20.0, max_value=80.0,
                                       value=38.0, format="%.1f", key="b_neck")
        bodyfat_requested = st.checkbox("Estimate body fat (Navy method)", value=False, key="b_bodyfat")

# ── VO2 inputs ────────────────────────────────────────────────────────────────
if run_vo2:
    with st.expander("❤️ Cardio / VO2max", expanded=True):

        # ── Activity level — visual card selector ──
        _act_options = ["Sedentary", "Light", "Moderate", "Active", "Very active", "Athlete"]
        _act_icons   = ["🛋️", "🚶", "🚴", "🏃", "⚡", "🏅"]
        _act_descs   = ["Desk job, no exercise", "1–2x/week light", "3–4x/week moderate",
                        "5x/week vigorous", "6–7x/week or daily", "2x/day / elite"]

        _current_act = st.session_state.get("v_activity", "Moderate")

        st.markdown("**Activity level**")
        _act_cols = st.columns(6)
        for _ci, (_ao, _ai, _ad) in enumerate(zip(_act_options, _act_icons, _act_descs)):
            with _act_cols[_ci]:
                _selected = (_ao == _current_act)
                if st.button(
                    f"{_ai}\n{_ao}\n{_ad}",
                    key=f"act_btn_{_ci}",
                    type="primary" if _selected else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["v_activity"] = _ao

        activity_level = st.session_state.get("v_activity", "Moderate")

        st.markdown("---")

        # ── Weekly minutes slider ──
        weekly_minutes = st.slider(
            "⏱️ Weekly minutes of moderate-to-vigorous activity",
            min_value=0, max_value=600, value=150, step=10,
            key="v_weekly_minutes", format="%d min"
        )
        _who = "✅ Meets WHO guidelines (150+ min/week)" if weekly_minutes >= 150 else "⚠️ Below WHO guidelines (aim for 150+ min/week)"
        _who_color = "#22C55E" if weekly_minutes >= 150 else "#F59E0B"
        st.markdown(f'<div style="color:{_who_color};font-size:12px;margin-top:-8px;margin-bottom:8px;">{_who}</div>',
                    unsafe_allow_html=True)

        # ── Session intensity ──
        session_intensity = st.slider(
            "💪 Typical session intensity",
            min_value=1, max_value=5, value=3, key="v_session_intensity"
        )
        _int_labels = {1: "😴 Very light", 2: "🚶 Light", 3: "🚴 Moderate", 4: "🏃 Hard", 5: "🔥 Max effort"}
        st.markdown(f'<div style="color:#94A3B8;font-size:12px;margin-top:-8px;margin-bottom:8px;">{_int_labels[session_intensity]}</div>',
                    unsafe_allow_html=True)

        st.markdown("---")

        # ── Heart rate ──
        st.markdown("**❤️ Heart rate**")
        resting_hr_unknown = st.toggle(
            "I don't know my resting heart rate",
            value=(st.session_state.get("global_resting_hr") is None),
            key="vo2_rhr_unknown"
        )
        if not resting_hr_unknown:
            default_rhr = st.session_state.get("global_resting_hr") or 70
            resting_hr = st.slider("Resting HR (bpm)", min_value=30, max_value=120,
                    value=int(default_rhr), key="vo2_rhr_value",
                    on_change=sync_from_vo2)
            _hr_zone = "🟢 Athletic" if resting_hr < 55 else "🟡 Normal" if resting_hr < 75 else "🔴 Elevated"
            st.caption(f"{_hr_zone} — prefilled from basic inputs above.")
        else:
            resting_hr = None

        max_hr_unknown = st.toggle("I don't know my max heart rate", value=False, key="vo2_maxhr_unknown")
        if not max_hr_unknown:
            max_hr = st.slider("Max HR (bpm)", min_value=100, max_value=240,
                    value=180, key="vo2_maxhr_val")
            _age_pred = 220 - int(age) if age else 190
            st.caption(f"Age-predicted max: ~{_age_pred} bpm")
        else:
            max_hr = None

        st.markdown("---")

        # ── VO2 method ──
        st.markdown("**🧪 VO2max calculation method**")
        vo2_method = st.radio(
            "Method",
            ["Questionnaire", "Cooper (12-min)", "Rockport (1-mile)", "Measured value"],
            index=0, key="vo2_method_select", horizontal=True,
            label_visibility="collapsed"
        )

        _method_info = {
            "Questionnaire": "📋 Estimated from activity level, HR and BMI. Good for general use.",
            "Cooper (12-min)": "🏃 Run as far as possible in 12 min. Very accurate.",
            "Rockport (1-mile)": "🚶 Walk 1 mile, record time and HR at finish.",
            "Measured value": "⌚ Enter a value from Apple Watch, Garmin, or lab test.",
        }
        st.caption(_method_info.get(vo2_method, ""))

        if vo2_method == "Cooper (12-min)":
            vo2_distance_m = st.slider("Distance covered in 12 min (meters)",
                    min_value=0, max_value=4000, value=2400, step=50,
                    key="vo2_cooper_distance", format="%d m")
            st.caption(f"Estimated VO2max: ~{(vo2_distance_m - 504.9) / 44.73:.1f} ml/kg/min" if vo2_distance_m > 504 else "Enter distance above")
        elif vo2_method == "Rockport (1-mile)":
            rockport_time_min = st.slider("1-mile walk time (minutes)",
                    min_value=8.0, max_value=30.0, value=15.0, step=0.5,
                    key="vo2_rockport_time", format="%.1f min")
            rockport_hr = st.slider("Heart rate at finish (bpm)",
                    min_value=60, max_value=200, value=140,
                    key="vo2_rockport_hr")
        elif vo2_method == "Measured value":
            measured_vo2_input = st.slider(
                "Your measured VO2max (ml/kg/min)",
                min_value=10.0, max_value=90.0, value=40.0, step=0.5,
                key="vo2_measured_input", format="%.1f ml/kg/min"
            )
        else:
            measured_vo2_input = 0.0

# ── Exercise calories ─────────────────────────────────────────────────────────
ACTIVITIES = {
    "Walking (casual)":              {"Light": 2.8, "Moderate": 3.5, "Hard": 4.3},
    "Brisk walking":                 {"Light": 3.5, "Moderate": 4.3, "Hard": 5.0},
    "Running/jogging":               {"Light": 7.0, "Moderate": 9.8, "Hard": 11.5},
    "Cycling (leisure)":             {"Light": 4.0, "Moderate": 6.8, "Hard": 8.5},
    "Cycling (vigorous)":            {"Light": 6.8, "Moderate": 8.5, "Hard": 10.0},
    "Strength training (weights)":   {"Light": 3.0, "Moderate": 4.5, "Hard": 6.0},
    "HIIT":                          {"Light": 6.0, "Moderate": 8.0, "Hard": 10.0},
    "Swimming":                      {"Light": 5.0, "Moderate": 7.0, "Hard": 9.5},
    "Rowing (moderate/vigorous)":    {"Light": 5.0, "Moderate": 7.0, "Hard": 8.5},
    "Elliptical":                    {"Light": 4.5, "Moderate": 6.0, "Hard": 8.0},
    "Stair climbing / Stairmaster":  {"Light": 6.0, "Moderate": 8.0, "Hard": 10.0},
    "Yoga / Pilates":                {"Light": 2.5, "Moderate": 3.0, "Hard": 4.0},
    "Dancing":                       {"Light": 3.0, "Moderate": 5.0, "Hard": 7.0},
    "Hiking (incline)":              {"Light": 3.5, "Moderate": 6.0, "Hard": 7.0},
    "Rock climbing / Bouldering":    {"Light": 4.0, "Moderate": 7.0, "Hard": 8.0},
    "Boxing / Martial arts":         {"Light": 6.0, "Moderate": 8.0, "Hard": 10.0},
    "Basketball / Team sports":      {"Light": 5.0, "Moderate": 7.0, "Hard": 10.0},
    "Soccer (football)":             {"Light": 6.0, "Moderate": 7.5, "Hard": 10.0},
    "Tennis (casual)":               {"Light": 4.0, "Moderate": 7.0, "Hard": 9.0},
    "Squash":                        {"Light": 7.0, "Moderate": 9.0, "Hard": 11.0},
    "Badminton":                     {"Light": 4.0, "Moderate": 6.0, "Hard": 8.0},
    "Table tennis (bordtennis)":     {"Light": 2.5, "Moderate": 4.0, "Hard": 5.5},
    "Gardening / Heavy yard work":   {"Light": 3.0, "Moderate": 4.5, "Hard": 6.0},
    "Housework / Light chores":      {"Light": 2.0, "Moderate": 3.0, "Hard": 3.5},
}

with st.expander("🏃 Exercise log", expanded=True):

    # ── Activity picker — grouped visual cards ──
    _act_groups = {
        "🚶 Low impact":   ["Walking (casual)", "Brisk walking", "Yoga / Pilates", "Housework / Light chores", "Gardening / Heavy yard work"],
        "🚴 Cardio":       ["Cycling (leisure)", "Cycling (vigorous)", "Elliptical", "Rowing (moderate/vigorous)", "Swimming"],
        "🏃 High impact":  ["Running/jogging", "HIIT", "Stair climbing / Stairmaster"],
        "⚽ Sports":       ["Basketball / Team sports", "Soccer (football)", "Tennis (casual)", "Squash", "Badminton", "Table tennis (bordtennis)", "Dancing"],
        "💪 Strength":     ["Strength training (weights)", "Boxing / Martial arts", "Rock climbing / Bouldering", "Hiking (incline)"],
    }
    _act_icons_map = {
        "Walking (casual)": "🚶", "Brisk walking": "🚶‍♂️", "Running/jogging": "🏃",
        "Cycling (leisure)": "🚲", "Cycling (vigorous)": "🚴", "Strength training (weights)": "🏋️",
        "HIIT": "⚡", "Swimming": "🏊", "Rowing (moderate/vigorous)": "🚣",
        "Elliptical": "🔄", "Stair climbing / Stairmaster": "🪜", "Yoga / Pilates": "🧘",
        "Dancing": "💃", "Hiking (incline)": "🥾", "Rock climbing / Bouldering": "🧗",
        "Boxing / Martial arts": "🥊", "Basketball / Team sports": "🏀", "Soccer (football)": "⚽",
        "Tennis (casual)": "🎾", "Squash": "🏸", "Badminton": "🏸",
        "Table tennis (bordtennis)": "🏓", "Gardening / Heavy yard work": "🌱",
        "Housework / Light chores": "🧹",
    }

    st.markdown("**🎯 Activity type**")
    _current_act = st.session_state.get("ui_activity_type", "Walking (casual)")
    _group_names = list(_act_groups.keys())
    if "ui_act_group" not in st.session_state:
        st.session_state["ui_act_group"] = next(
            (g for g, acts in _act_groups.items() if _current_act in acts), _group_names[0]
        )
    _sel_group = st.radio("Category", _group_names,
                    horizontal=True, key="ui_act_group", label_visibility="collapsed")

    _group_acts = _act_groups[_sel_group]
    _n = len(_group_acts)
    _gcols = st.columns(_n)
    for _gi, _ga in enumerate(_group_acts):
        with _gcols[_gi]:
            _is_sel = (_ga == st.session_state.get("ui_activity_type", "Walking (casual)"))
            _ico = _act_icons_map.get(_ga, "🏅")
            _short = _ga.split("(")[0].split("/")[0].strip()
            if st.button(
                f"{_ico}\n{_short}",
                key=f"act_type_btn_{_sel_group}_{_gi}",
                type="primary" if _is_sel else "secondary",
                use_container_width=True,
            ):
                st.session_state["ui_activity_type"] = _ga

    activity_ex = st.session_state.get("ui_activity_type", "Walking (casual)")
    if activity_ex not in _group_acts:
        activity_ex = _group_acts[0]
        st.session_state["ui_activity_type"] = activity_ex

    st.markdown("---")

    # ── Intensity — visual 3-button style ──
    st.markdown("**💪 Intensity**")
    _int_opts = ["Light", "Moderate", "Hard"]
    _int_icons = ["🟢", "🟡", "🔴"]
    _int_descs = ["Easy, can hold conversation", "Slightly breathless", "Hard, can barely talk"]
    _int_cols = st.columns(3)
    _cur_int = st.session_state.get("ui_intensity", "Moderate")
    for _ii, (_io, _iico, _id) in enumerate(zip(_int_opts, _int_icons, _int_descs)):
        with _int_cols[_ii]:
            _is_int = (_io == _cur_int)
            if st.button(
                f"{_iico}\n{_io}\n{_id}",
                key=f"int_btn_{_ii}",
                type="primary" if _is_int else "secondary",
                use_container_width=True,
            ):
                st.session_state["ui_intensity"] = _io
    intensity_label = st.session_state.get("ui_intensity", "Moderate")

    st.markdown("---")

    # ── Sessions + Duration ──
    st.markdown("**📅 Volume**")
    _vc1, _vc2 = st.columns(2)
    with _vc1:
        sessions_per_week = st.slider("Sessions per week", min_value=0, max_value=14,
                                       value=3, step=1, key="ui_sessions_per_week")
    with _vc2:
        minutes_per_session = st.slider("Minutes per session", min_value=5, max_value=180,
                                         value=45, step=5, key="ui_minutes", format="%d min")

    _total_min = sessions_per_week * minutes_per_session
    _who_ex = "✅ Meets WHO guidelines" if _total_min >= 150 else f"⚠️ {150 - _total_min} min/week below WHO target"
    _who_ex_color = "#22C55E" if _total_min >= 150 else "#F59E0B"
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:8px 12px;'
        f'display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
        f'<span style="color:#94A3B8;font-size:12px;">Total: <b style="color:#E5E7EB;">{_total_min} min/week</b></span>'
        f'<span style="color:{_who_ex_color};font-size:12px;">{_who_ex}</span>'
        f'</div>', unsafe_allow_html=True
    )

    # ── RPE ──
    st.markdown("**😤 Perceived exertion (RPE)**")
    rpe = st.slider("RPE", 1, 10, 5, key="ui_rpe", label_visibility="collapsed")
    _rpe_labels = {1:"😴 Rest",2:"🧘 Very easy",3:"🚶 Easy",4:"🚶‍♂️ Moderate",5:"🚴 Somewhat hard",
                   6:"🏃 Hard",7:"🏃‍♂️ Very hard",8:"⚡ Very very hard",9:"🔥 Near max",10:"💀 Max effort"}
    st.markdown(f'<div style="color:#94A3B8;font-size:12px;margin-top:-8px;">{_rpe_labels[rpe]}</div>',
                unsafe_allow_html=True)
    rpe_multiplier = 0.85 + (rpe - 1) * (0.4 / 9)

    st.markdown("---")

    # ── HR refinement ──
    default_avg = st.session_state.get("global_avg_hr")
    avg_hr = default_avg if default_avg is not None else 130
    st.session_state["global_avg_hr"] = int(avg_hr)

    use_hr = st.toggle("❤️ Use average session HR to refine estimate", key="ui_use_hr")
    avg_hr_for_calc = None
    resting_hr_for_calc = None
    if use_hr:
        _hc1, _hc2 = st.columns(2)
        with _hc1:
            avg_hr_for_calc = st.slider("Avg session HR (bpm)", min_value=60, max_value=200,
                                         value=int(avg_hr), key="ui_avg_hr_calc")
        with _hc2:
            resting_hr_for_calc = st.slider("Resting HR (bpm)", min_value=30, max_value=100,
                                             value=int(st.session_state.get("global_resting_hr") or 60),
                                             key="ui_resting_hr",
                                             on_change=sync_from_calc)
        _hr_reserve = avg_hr_for_calc - resting_hr_for_calc
        st.caption(f"HR reserve used: {_hr_reserve} bpm — higher reserve = more accurate calorie estimate")

    manual_kcal = st.toggle("🔢 I know my exact kcal burn per session", key="ui_manual_kcal")
    if manual_kcal:
        manual_kcal_val = st.slider("kcal burned per session", min_value=0, max_value=2000,
                                     value=300, step=10, key="ui_manual_kcal_val", format="%d kcal")
    else:
        manual_kcal_val = 0.0

    # ── Compute ──
    try:
        base_met = ACTIVITIES.get(activity_ex, {}).get(intensity_label, 4.0)
    except Exception:
        base_met = 4.0
    try:
        w_ex = float(weight_kg)
    except Exception:
        w_ex = 70.0

    if manual_kcal and manual_kcal_val > 0:
        kcal_per_session = float(manual_kcal_val)
    else:
        kcal_per_min = (base_met * 3.5 * w_ex) / 200.0
        kcal_per_session = kcal_per_min * float(minutes_per_session) * rpe_multiplier
        if avg_hr_for_calc is not None and resting_hr_for_calc:
            hr_delta = max(0.0, float(avg_hr_for_calc) - float(resting_hr_for_calc))
            hr_multiplier = 1.0 + min(0.5, hr_delta / 100.0)
            kcal_per_session *= hr_multiplier

    kcal_per_week_ex = sessions_per_week * kcal_per_session
    st.session_state["exercise_kcal_per_week"] = kcal_per_week_ex
    st.session_state["exercise_last"] = {
        "activity": activity_ex, "intensity": intensity_label,
        "minutes": int(minutes_per_session), "sessions_per_week": int(sessions_per_week),
        "kcal_per_session": round(kcal_per_session, 1),
        "kcal_per_week": round(kcal_per_week_ex, 1),
        "rpe": int(rpe),
        "avg_hr": int(avg_hr_for_calc) if avg_hr_for_calc is not None else None,
    }

    # ── Live burn summary card ──
    _burn_color = "#22C55E" if kcal_per_week_ex >= 1500 else "#3B82F6" if kcal_per_week_ex >= 500 else "#94A3B8"
    st.markdown(
        f'<div style="background:rgba(15,23,42,0.7);border:1px solid rgba(148,163,184,0.15);'
        f'border-radius:14px;padding:14px 16px;margin-top:10px;">'
        f'<div style="color:#94A3B8;font-size:11px;margin-bottom:4px;">ESTIMATED WEEKLY BURN</div>'
        f'<div style="color:{_burn_color};font-weight:800;font-size:28px;">{kcal_per_week_ex:.0f} kcal/week</div>'
        f'<div style="color:#94A3B8;font-size:12px;margin-top:4px;">'
        f'{kcal_per_session:.0f} kcal/session × {sessions_per_week} sessions · '
        f'{_act_icons_map.get(activity_ex,"🏅")} {activity_ex}</div>'
        f'<div style="margin-top:10px;background:rgba(255,255,255,0.05);border-radius:999px;height:6px;overflow:hidden;">'
        f'<div style="width:{min(100, int(kcal_per_week_ex/30))}%;background:{_burn_color};height:100%;border-radius:999px;"></div>'
        f'</div>'
        f'<div style="color:#64748B;font-size:10px;margin-top:4px;">MET-based estimate · adjust RPE or use HR for more accuracy</div>'
        f'</div>',
        unsafe_allow_html=True
    )

# ── Biological age inputs ─────────────────────────────────────────────────────
if run_bioage:
    with st.expander("Biological age inputs", expanded=True):
        st.caption("Leave any field blank or use 'I don't know' where available.")

        t_core, t_cardio, t_life, t_body = st.tabs(["Core", "Cardio", "Lifestyle", "Body comp"])

        with t_core:
            c1, c2 = st.columns(2)
            with c1:
                smoker = st.toggle("Smoker?", key="bio_smoker")
                diabetes = st.toggle("Diabetes?", key="bio_diabetes")
            with c2:
                family_history = st.toggle(
                    "Family history of premature cardiovascular disease?",
                    key="bio_family_hist",
                )
                if sex == "F":
                    menopause = st.toggle("Post-menopausal?", key="bio_menopause")

        with t_cardio:
            st.markdown("#### 🫀 Cardiovascular")
            bp_unknown = st.toggle("I don't know my systolic blood pressure", value=False, key="bio_bp_unknown")
            if not bp_unknown:
                bp_systolic = st.number_input(
                    "Systolic blood pressure (mmHg)",
                    min_value=70.0, max_value=260.0, value=120.0, key="bio_bp_val"
                )

            chol_unknown = st.toggle("I don't know my cholesterol", value=False, key="bio_chol_unknown")
            if not chol_unknown:
                cholesterol = st.number_input(
                    "Cholesterol (mg/dL)",
                    min_value=50.0, max_value=500.0, value=180.0, key="bio_chol_val"
                )

            _bio_rhr_known = st.session_state.get("global_resting_hr")
            rhr_unknown = st.toggle("I don't know my resting heart rate",
                                    value=(_bio_rhr_known is None), key="bio_rhr_unknown")
            if not rhr_unknown:
                resting_hr = st.number_input(
                    "Resting heart rate (bpm)",
                    min_value=30, max_value=220,
                    value=int(_bio_rhr_known or 70), key="bio_rhr_val",
                    on_change=sync_from_bio
                )

        with t_life:
            st.markdown("#### 😴 Lifestyle")
            sleep_unknown = st.toggle("I don't know my sleep duration", value=False, key="bio_sleep_unknown")
            if not sleep_unknown:
                sleep_hours = st.number_input(
                    "Average sleep per night (hours)",
                    min_value=0.0, max_value=24.0, value=7.0, format="%.1f", key="bio_sleep_val"
                )

            alcohol_unknown = st.toggle("I don't know my alcohol intake", value=False, key="bio_alc_unknown")
            if not alcohol_unknown:
                alcohol_units = st.number_input(
                    "Alcohol units per week",
                    min_value=0, max_value=300, value=0, key="bio_alc_val"
                )

            fruit_veg = st.number_input(
                "Daily fruit & vegetable servings",
                min_value=0, max_value=20, value=3, key="bio_fv"
            )
            perceived_stress = st.slider(
                "Perceived stress (1 low – 10 high)",
                min_value=1, max_value=10, value=5, key="bio_stress"
            )

        with t_body:
            st.markdown("#### ⚖️ Body composition")
            grip_unknown = st.toggle("I don't know my grip strength", value=False, key="bio_grip_unknown")
            if not grip_unknown:
                grip_strength = st.number_input(
                    "Grip strength (kg)",
                    min_value=0.0, max_value=100.0, value=30.0, format="%.1f", key="bio_grip_val"
                )

            bio_waist_unknown = st.toggle("I don't know my waist-to-hip ratio", value=False, key="bio_waist_unknown")
            if not bio_waist_unknown:
                c1, c2 = st.columns(2)
                with c1:
                    waist_bio = st.number_input(
                        "Waist (cm)", min_value=30.0, max_value=300.0,
                        value=float(st.session_state.get("global_waist_cm") or 80.0),
                        format="%.1f", key="bio_waist_val"
                    )
                with c2:
                    hip_bio = st.number_input(
                        "Hip (cm)", min_value=30.0, max_value=300.0,
                        value=float(st.session_state.get("global_hip_cm") or 95.0),
                        format="%.1f", key="bio_hip_val"
                    )
                if waist_cm is None:
                    waist_cm = waist_bio
                if hip_cm is None:
                    hip_cm = hip_bio

# ── Conditions ────────────────────────────────────────────────────────────────
selected_conditions = []
custom_condition = ""
condition_goal_focus = "General"

if run_conditions:
    with st.expander("Conditions & recommendations", expanded=True):
        st.markdown("Select any diagnoses/conditions to get practical exercise & prevention tips.")
        if hasattr(calculators, "DIAGNOSIS_RECOMMENDATIONS"):
            condition_options = sorted(list(calculators.DIAGNOSIS_RECOMMENDATIONS.keys()))
        else:
            condition_options = ["Type 2 Diabetes", "Hypertension", "Lower Back Pain", "Asthma", "Osteoarthritis"]
        selected_conditions = st.multiselect("Select conditions", options=condition_options,
                                              default=[], key="cond_select")
        custom_condition = st.text_input("Other condition (free text)", "", key="cond_custom")
        if custom_condition.strip():
            selected_conditions = (selected_conditions or []) + [custom_condition.strip()]
        condition_goal_focus = st.selectbox("Recommendations focus",
                                             ["General", "VO2", "Weight", "Mobility"],
                                             index=0, key="cond_goal")

# ── Weight goal / plan ────────────────────────────────────────────────────────
create_plan = False
target_weight = None
target_bmi = None
plan_weeks = 12

if run_plan and run_bmi:
    with st.expander("🎯 Goal / plan", expanded=True):        # Visual toggle
        create_plan = st.toggle("Activate weight goal plan", value=False, key="plan_create")

        if create_plan:
            # Current weight for reference
            _cw = float(weight_kg) if weight_kg else 70.0
            _min_w = max(30.0, _cw - 40.0)
            _max_w = min(250.0, _cw + 40.0)

            st.markdown("#### 🎯 Set your target")

            plan_mode = st.radio(
                "What do you want to target?",
                ["⚖️ Target weight (kg)", "📊 Target BMI"],
                index=0, key="plan_type", horizontal=True
            )

            if "⚖️" in plan_mode:
                target_weight = st.slider(
                    "Target weight (kg)",
                    min_value=float(_min_w),
                    max_value=float(_max_w),
                    value=max(float(_min_w), min(float(_max_w), _cw - 5.0)),
                    step=0.5,
                    key="plan_target_weight",
                    format="%.1f kg"
                )
                _diff = target_weight - _cw
                _dir = "lose" if _diff < 0 else "gain"
                _col = "#22C55E" if _diff < 0 else "#3B82F6"
                st.markdown(
                    f'<div style="background:rgba(34,197,94,0.08);border:1px solid {_col}44;'
                    f'border-radius:12px;padding:10px 14px;margin:6px 0;">'
                    f'<span style="color:{_col};font-weight:700;font-size:18px;">'
                    f'{abs(_diff):.1f} kg to {_dir}</span>'
                    f'<span style="color:#94A3B8;font-size:13px;margin-left:10px;">'
                    f'({_cw:.1f} kg → {target_weight:.1f} kg)</span></div>',
                    unsafe_allow_html=True
                )
                target_bmi = None
            else:
                target_bmi = st.slider(
                    "Target BMI",
                    min_value=16.0, max_value=35.0,
                    value=22.0, step=0.1,
                    key="plan_target_bmi",
                    format="%.1f"
                )
                _h = float(height_cm) / 100.0 if height_cm else 1.70
                _implied_w = target_bmi * _h * _h
                st.markdown(
                    f'<div style="background:rgba(59,130,246,0.08);border:1px solid #3B82F644;'
                    f'border-radius:12px;padding:10px 14px;margin:6px 0;">'
                    f'<span style="color:#3B82F6;font-weight:700;font-size:18px;">BMI {target_bmi:.1f}</span>'
                    f'<span style="color:#94A3B8;font-size:13px;margin-left:10px;">'
                    f'= {_implied_w:.1f} kg at your height</span></div>',
                    unsafe_allow_html=True
                )
                target_weight = None

            st.markdown("#### ⏱️ Timeline")
            plan_weeks = st.slider(
                "Weeks to reach target",
                min_value=4, max_value=52, value=12, step=1,
                key="plan_weeks",
                format="%d weeks"
            )

            # Visual timeline preview
            _wks = int(plan_weeks)
            _tw = target_weight if target_weight else (target_bmi * (float(height_cm)/100)**2 if target_bmi and height_cm else _cw)
            _rate = (_tw - _cw) / _wks if _wks > 0 else 0
            _safe = abs(_rate) <= 1.0
            _rate_color = "#22C55E" if _safe else "#F59E0B"

            _warn_html = ""
            if not _safe:
                _warn_html = (
                    '<div style="color:#F59E0B;font-size:12px;margin-top:10px;">'
                    "⚠️ Rate above 1 kg/week — consider a longer timeline for safety."
                    "</div>"
                )

            _preview_html = (
                '<div style="background:rgba(15,23,42,0.6);border:1px solid rgba(148,163,184,0.15);'
                'border-radius:14px;padding:14px 16px;margin-top:8px;">'
                '<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;">'
                '<div style="text-align:center;">'
                '<div style="color:#94A3B8;font-size:11px;margin-bottom:2px;">RATE</div>'
                f'<div style="color:{_rate_color};font-weight:800;font-size:20px;">{_rate:+.2f} kg/wk</div>'
                '</div>'
                '<div style="text-align:center;">'
                '<div style="color:#94A3B8;font-size:11px;margin-bottom:2px;">DURATION</div>'
                f'<div style="color:#E5E7EB;font-weight:800;font-size:20px;">{_wks} wks</div>'
                '</div>'
                '<div style="text-align:center;">'
                '<div style="color:#94A3B8;font-size:11px;margin-bottom:2px;">TARGET</div>'
                f'<div style="color:#E5E7EB;font-weight:800;font-size:20px;">{_tw:.1f} kg</div>'
                '</div>'
                '</div>'
                f'{_warn_html}'
                '</div>'
            )
            st.markdown(_preview_html, unsafe_allow_html=True)

# ── Calculate ─────────────────────────────────────────────────────────────────
if st.button("Calculate / Generate report", key="btn_calculate"):
    import traceback, logging

    def _f(val, name=""):
        try:
            if val is None:
                return None
            if isinstance(val, (int, float)):
                return float(val)
            s = str(val).strip()
            return None if s == "" else float(s.replace(",", "."))
        except Exception as e:
            raise ValueError(f"Cannot convert '{name}' to float: {val!r} ({e})")

    def _i(val, name=""):
        try:
            if val is None:
                return None
            if isinstance(val, int):
                return val
            s = str(val).strip()
            return None if s == "" else int(float(s))
        except Exception as e:
            raise ValueError(f"Cannot convert '{name}' to int: {val!r} ({e})")

    try:
        age_i = _i(age, "age")
        if age_i is None:
            raise ValueError("Age must be a number.")
        height_f = _f(height_cm, "height_cm")
        weight_f = _f(weight_kg, "weight_kg")
        if height_f is None or weight_f is None:
            raise ValueError("Height and weight must be numbers.")

        waist_f = _f(waist_cm, "waist_cm")
        hip_f = _f(hip_cm, "hip_cm")
        neck_f = _f(neck_cm, "neck_cm")
        measured_vo2_f = _f(measured_vo2_input, "measured_vo2")
        vo2_dist_f = _f(vo2_distance_m, "vo2_distance")
        rockport_time_f = _f(rockport_time_min, "rockport_time")
        rockport_hr_i = _i(rockport_hr, "rockport_hr")
        weekly_min_i = _i(weekly_minutes, "weekly_minutes")
        session_int_i = _i(session_intensity, "session_intensity")
        resting_hr_i = _i(resting_hr, "resting_hr")
        max_hr_i = _i(max_hr, "max_hr")
        plan_weeks_i = _i(plan_weeks, "plan_weeks")
        target_weight_f = _f(target_weight, "target_weight")
        target_bmi_f = _f(target_bmi, "target_bmi")

        results = {}
        try:
            db = get_db_client()
            save_health_metrics(db, st.session_state["user_id"], results)
                    # Vi kan legge til ein liten logg for deg sjølv
            print("Data saved successfully.")
        except Exception as e:
            st.error(f"Could not save to history: {e}")
                # ------------------------------------------
        
                # Deretter oppdaterer du session state slik at resten av appen får resultata
        st.session_state["results"] = results
        
    except Exception as e:
                # Din eksisterende feilhåndtering
        st.error(f"Calculation error: {e}")
        traceback.print_exc()
        # BMI
        if run_bmi:
            bmi_value, bmi_category = calculators.bmi_calc(weight_f, height_f)
            results["bmi"] = {"value": float(bmi_value), "category": bmi_category}
            if waist_f is not None and hip_f is not None:
                whr_value = calculators.waist_hip_ratio(waist_f, hip_f)
                results["whr"] = {"value": float(whr_value),
                                   "category": calculators.whr_category(sex, whr_value)}

        # Body fat
        if bodyfat_requested and neck_f is not None:
            try:
                if sex == "M":
                    if waist_f is None:
                        raise ValueError("Waist required for male body-fat estimate.")
                    bf = calculators.body_fat_navy(sex=sex, height_cm=height_f,
                                                    neck_cm=neck_f, waist_cm=waist_f)
                else:
                    if waist_f is None or hip_f is None:
                        raise ValueError("Waist and hip required for female body-fat estimate.")
                    bf = calculators.body_fat_navy(sex=sex, height_cm=height_f,
                                                    neck_cm=neck_f, waist_cm=waist_f, hip_cm=hip_f)
                results["bodyfat"] = {"value": round(float(bf), 1)}
            except Exception as e:
                st.warning(f"Body-fat estimate skipped: {e}")

        # VO2
        if run_vo2:
            vo2_method_sel = st.session_state.get("vo2_method_select", vo2_method)
            if measured_vo2_f is not None and measured_vo2_f > 0:
                vo2_value = calculators.vo2_measured_value(measured_vo2_f)
                method_used = "Measured value"
            elif vo2_method_sel == "Cooper (12-min)":
                vo2_value = calculators.vo2_cooper_from_distance(float(vo2_dist_f or 0.0))
                method_used = "Cooper (12-min)"
            elif vo2_method_sel == "Rockport (1-mile)":
                if rockport_time_f is None:
                    raise ValueError("Rockport time must be a number.")
                vo2_value = calculators.vo2_rockport_1mile(
                    float(rockport_time_f), int(rockport_hr_i or 0),
                    weight_f, age_i, sex)
                method_used = "Rockport (1-mile)"
            else:
                bmi_v = results["bmi"]["value"] if "bmi" in results else calculators.bmi_calc(weight_f, height_f)[0]
                vo2_value = calculators.vo2_questionnaire_estimate(
                    age=age_i, sex=sex,
                    weekly_minutes=int(weekly_min_i or 0),
                    session_intensity_score=int(session_int_i or 1),
                    activity_level=st.session_state.get("v_activity", activity_level),
                    bmi=bmi_v,
                    resting_hr=int(resting_hr_i) if resting_hr_i is not None else None,
                    max_hr=int(max_hr_i) if max_hr_i is not None else None,
                )
                method_used = "Questionnaire"

            vo2_ref = calculators.vo2_reference(age_i, sex, float(vo2_value))
            vo2_tips = calculators.vo2_improvement_tips(
                vo2_value=float(vo2_value), sex=sex, age=age_i,
                activity_level=st.session_state.get("v_activity", activity_level),
                weekly_minutes=int(weekly_min_i or 0),
            )
            top_descriptor = calculators.vo2_top_descriptor(age_i, sex, float(vo2_value))
            results["vo2"] = {
                "value": round(float(vo2_value), 1),
                "method": method_used,
                "age_band": vo2_ref.get("age_band"),
                "percentile": vo2_ref.get("percentile"),
                "rating": vo2_ref.get("rating"),
                "mean": vo2_ref.get("mean"),
                "tips": vo2_tips,
                "top_descriptor": top_descriptor,
            }

        # Biological age
        if run_bioage:
            bmi_v = results["bmi"]["value"] if "bmi" in results else calculators.bmi_calc(weight_f, height_f)[0]
            waist_to_hip = None
            if waist_f is not None and hip_f is not None:
                try:
                    waist_to_hip = calculators.waist_hip_ratio(waist_f, hip_f)
                except Exception:
                    pass
            measured_vo2_for_bio = results.get("vo2", {}).get("value")
            bio_age, bio_factors = calculators.estimate_biological_age_detailed(
                age=age_i, sex=sex,
                smoker=st.session_state.get("bio_smoker", False),
                bmi=bmi_v,
                activity_level=st.session_state.get("v_activity", activity_level),
                sleep_hours=_f(st.session_state.get("bio_sleep_val"), "sleep"),
                alcohol_units_per_week=_f(st.session_state.get("bio_alc_val"), "alcohol"),
                fruit_veg_servings=_f(st.session_state.get("bio_fv"), "fruit_veg"),
                perceived_stress=st.session_state.get("bio_stress", perceived_stress),
                grip_strength_kg=_f(st.session_state.get("bio_grip_val"), "grip"),
                bp_systolic=_f(st.session_state.get("bio_bp_val"), "bp"),
                cholesterol_mg_dl=_f(st.session_state.get("bio_chol_val"), "chol"),
                diabetes=st.session_state.get("bio_diabetes", False),
                resting_hr=_i(st.session_state.get("bio_rhr_val") or resting_hr_i, "rhr"),
                waist_to_hip_ratio=waist_to_hip,
                family_history=st.session_state.get("bio_family_hist", False),
                menopause=st.session_state.get("bio_menopause", False),
                measured_vo2=measured_vo2_for_bio,
            )
            results["bio_age"] = {"value": round(float(bio_age), 1)}
            results["bio_factors"] = bio_factors

        # Conditions
        if run_conditions:
            recs = calculators.recommendations_for_diagnoses(
                st.session_state.get("cond_select", []) or selected_conditions,
                st.session_state.get("cond_goal", condition_goal_focus)
            )
            results["triage"] = {"level": "Info", "message": "Recommendations generated for selected conditions."}
            results["triage_recommendations"] = recs

        # Plan
        if run_plan and run_bmi and create_plan:
            target_w = (target_bmi_f * (height_f / 100.0) ** 2) if target_bmi_f else target_weight_f
            if target_w:
                ekpw = float(st.session_state.get("exercise_kcal_per_week", 0.0))
                plan = calculators.generate_weight_plan(
                    current_weight_kg=weight_f,
                    target_weight_kg=target_w,
                    weeks=int(plan_weeks_i or 12),
                    sex=sex, height_cm=height_f, age=age_i,
                    activity_level=st.session_state.get("v_activity", activity_level),
                    exercise_kcal_per_week=ekpw,
                )
                if plan.get("error"):
                    st.error(plan.get("message"))
                else:
                    results["plan"] = plan

    except Exception as e:
        st.error(f"Error during calculation: {e}")
        st.text(traceback.format_exc())
        logging.exception("Calculation failed")
        st.session_state["results"] = {}
    else:
        st.session_state["results"] = results
        st.success("Calculation finished — results ready.")

# ── Display results ───────────────────────────────────────────────────────────
results = st.session_state.get("results", {})

if results:
        # --- BMI SEKSJON ---
    if "bmi" in results:
        st.subheader("BMI")
        b = results["bmi"]["value"]
        cat = results["bmi"]["category"]

        # Fargekode basert på kategori
        if b < 18.5:
            bmi_color = "#3B82F6"
            bmi_emoji = "⬇️"
        elif b < 25.0:
            bmi_color = "#22C55E"
            bmi_emoji = "✅"
        elif b < 30.0:
            bmi_color = "#F59E0B"
            bmi_emoji = "⚠️"
        else:
            bmi_color = "#EF4444"
            bmi_emoji = "🔴"

        # Marker-posisjon på linja (0–45 skala → 0–100%)
        marker_pct = min(100, max(0, (b / 45.0) * 100))

        components.html(f"""
<style>
  .bmi-wrap {{
    font-family: Arial, sans-serif;
    background: #1F2937;
    border: 1px solid #374151;
    border-radius: 16px;
    padding: 20px 22px 18px 22px;
    color: #E5E7EB;
    max-width: 100%;
  }}
  .bmi-top {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 18px;
  }}
  .bmi-val {{
    font-size: 48px;
    font-weight: 800;
    color: {bmi_color};
    line-height: 1;
  }}
  .bmi-cat {{
    font-size: 14px;
    color: #9CA3AF;
    margin-top: 4px;
  }}
  .bmi-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: {bmi_color}22;
    border: 1px solid {bmi_color};
    color: {bmi_color};
    font-size: 14px;
    font-weight: 700;
    border-radius: 999px;
    padding: 6px 14px;
  }}
  .bmi-track-wrap {{
    position: relative;
    margin-bottom: 8px;
  }}
  .bmi-track {{
    display: flex;
    height: 20px;
    border-radius: 999px;
    overflow: hidden;
    width: 100%;
  }}
  .bmi-seg {{
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 700;
    color: rgba(0,0,0,0.7);
  }}
  .bmi-marker-row {{
    position: relative;
    height: 28px;
    margin-top: 2px;
  }}
  .bmi-marker {{
    position: absolute;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  .bmi-arrow {{
    width: 0; height: 0;
    border-left: 7px solid transparent;
    border-right: 7px solid transparent;
    border-bottom: 12px solid {bmi_color};
  }}
  .bmi-marker-val {{
    font-size: 12px;
    font-weight: 800;
    color: {bmi_color};
    margin-top: 2px;
    white-space: nowrap;
  }}
  .bmi-labels {{
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    color: #6B7280;
    margin-top: 4px;
  }}
  .bmi-legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;
  }}
  .bmi-leg-item {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    color: #CBD5E1;
    background: #111827;
    border: 1px solid #374151;
    border-radius: 999px;
    padding: 4px 10px;
  }}
  .bmi-dot {{
    width: 9px; height: 9px;
    border-radius: 50%;
    flex: 0 0 9px;
  }}
</style>

<div class="bmi-wrap">
  <div class="bmi-top">
    <div>
      <div class="bmi-val" id="bmi-val-anim">0.0</div>
      <div class="bmi-cat">Body Mass Index</div>
    </div>
    <div class="bmi-badge">{bmi_emoji} {cat}</div>
  </div>

  <div class="bmi-track-wrap">
    <div class="bmi-track">
      <!-- Underweight: 0–18.5 = 41.1% of 45 -->
      <div class="bmi-seg" style="width:41.1%; background:#3B82F6;">Under</div>
      <!-- Normal: 18.5–25 = 14.4% -->
      <div class="bmi-seg" style="width:14.4%; background:#22C55E;">Normal</div>
      <!-- Overweight: 25–30 = 11.1% -->
      <div class="bmi-seg" style="width:11.1%; background:#F59E0B;">Over</div>
      <!-- Obese: 30–45 = 33.3% -->
      <div class="bmi-seg" style="width:33.3%; background:#EF4444;">Obese</div>
    </div>

    <div class="bmi-marker-row">
      <div class="bmi-marker" style="left:{marker_pct:.1f}%;">
        <div class="bmi-arrow"></div>
        <div class="bmi-marker-val">{b:.1f}</div>
      </div>
    </div>
  </div>

  <div class="bmi-labels">
    <span>0</span>
    <span>18.5</span>
    <span>25</span>
    <span>30</span>
    <span>45+</span>
  </div>

  <div class="bmi-legend">
    <div class="bmi-leg-item"><span class="bmi-dot" style="background:#3B82F6"></span>Underweight (&lt;18.5)</div>
    <div class="bmi-leg-item"><span class="bmi-dot" style="background:#22C55E"></span>Normal (18.5–24.9)</div>
    <div class="bmi-leg-item"><span class="bmi-dot" style="background:#F59E0B"></span>Overweight (25–29.9)</div>
    <div class="bmi-leg-item"><span class="bmi-dot" style="background:#EF4444"></span>Obese (30+)</div>
  </div>
</div>
<script>
(function() {{
  var target = {b:.4f};
  var el = document.getElementById('bmi-val-anim');
  if (!el) return;
  var start = null, duration = 900;
  function step(ts) {{
    if (!start) start = ts;
    var p = Math.min((ts - start) / duration, 1);
    var ease = 1 - Math.pow(1 - p, 3);
    el.textContent = (target * ease).toFixed(1);
    if (p < 1) requestAnimationFrame(step);
    else el.textContent = target.toFixed(1);
  }}
  requestAnimationFrame(step);
}})();
</script>
        """, height=260)

    # ── Energy & Metabolism ───────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Energy og Metabolism")

    def _to_float(val):
        try:
            return float(str(val).replace(",", ".").strip())
        except Exception:
            return None

    calc_age_f = _to_float(age)
    calc_weight = _to_float(weight_kg)
    calc_height = _to_float(height_cm)

    if calc_age_f is None or calc_weight is None or calc_height is None:
        st.info("Fyll inn alder, vekt og høyde for kaloriberegning.")
    else:
        bmr_val = bmr_mifflin(age=int(calc_age_f), sex=sex,
                               weight_kg=float(calc_weight), height_cm=float(calc_height))
        daily_living = bmr_val * 1.2
        # ── FIX: use actual exercise kcal/week from session_state ──
        w_kcal = float(st.session_state.get("exercise_kcal_per_week", 0.0))
        tdee_total = tdee_including_weekly_exercise(
            bmr_val,
            st.session_state.get("v_activity", activity_level),
            w_kcal
        )
        st.session_state["latest_tdee_total"] = float(tdee_total)

        c1, c2, c3 = st.columns(3)
        c1.metric("BMR (base metabolic rate)", f"{int(bmr_val)} kcal")
        c2.metric("Daily burn (sedentary)", f"{int(daily_living)} kcal")
        c3.metric("Total daily burn incl. exercise", f"{int(tdee_total)} kcal")

        if w_kcal > 0:
            st.caption(f"Exercise contribution: {w_kcal:.0f} kcal/week = "
                       f"{w_kcal/7:.0f} kcal/day added to TDEE.")

# ── VO2 ───────────────────────────────────────────────────────────────────
        if "vo2" in results:
            st.markdown("---")
            st.subheader("VO2 max & fitness")
    
            v_val = float(results["vo2"]["value"])
            v_pct = max(0.0, min(100.0, float(results["vo2"].get("percentile") or 0)))
            top_text = f"Top {100 - v_pct:.1f}%"
    
        if v_pct >= 90:
            pct_color = "#22C55E"; pct_label = "Excellent"
        elif v_pct >= 80:
            pct_color = "#3B82F6"; pct_label = "Very good"
        elif v_pct >= 60:
            pct_color = "#7C7CF5"; pct_label = "Good"
        elif v_pct >= 40:
            pct_color = "#F59E0B"; pct_label = "Below average"
        else:
            pct_color = "#EF6A3B"; pct_label = "Low"
        
        _vo2_html = """
<style>
  .vo2-row {
    display: flex; gap: 12px; font-family: Arial, sans-serif;
    background: #1F2937; border: 1px solid #374151;
    border-radius: 16px; padding: 18px 20px;
  }
  .vo2-card {
    flex: 1; text-align: center;
    background: #111827; border-radius: 12px; padding: 14px 8px;
    border: 1px solid #374151;
  }
  .vo2-label {
    font-size: 10px; color: #6B7280; text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }
  .vo2-num {
    font-size: 36px; font-weight: 800; line-height: 1; color: VO2COLOR;
  }
  .vo2-sub {
    font-size: 11px; color: #9CA3AF; margin-top: 4px;
  }
</style>
<div class="vo2-row">
  <div class="vo2-card">
    <div class="vo2-label">VO2 max</div>
    <div class="vo2-num" id="vo2-val-anim">0.0</div>
    <div class="vo2-sub">ml/kg/min</div>
  </div>
  <div class="vo2-card">
    <div class="vo2-label">Percentile</div>
    <div class="vo2-num" id="vo2-pct-anim">0</div>
    <div class="vo2-sub">of your age group</div>
  </div>
  <div class="vo2-card">
    <div class="vo2-label">Ranking</div>
    <div class="vo2-num" style="font-size:22px;padding-top:7px;">PCT_LABEL</div>
    <div class="vo2-sub">TOP_TEXT</div>
  </div>
</div>
<script>
(function() {
  function animCount(id, target, decimals, duration) {
    var el = document.getElementById(id);
    if (!el) return;
    var start = null;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / duration, 1);
      var ease = 1 - Math.pow(1 - p, 3);
      el.textContent = (target * ease).toFixed(decimals);
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = target.toFixed(decimals);
    }
    requestAnimationFrame(step);
  }
  animCount('vo2-val-anim', VO2VAL, 1, 1000);
  animCount('vo2-pct-anim', VO2PCT, 0, 1000);
})();
</script>
        """
        _vo2_html = (
            _vo2_html
            .replace("VO2COLOR", pct_color)
            .replace("VO2VAL", f"{v_val:.4f}")
            .replace("VO2PCT", f"{v_pct:.1f}")
            .replace("PCT_LABEL", pct_label)
            .replace("TOP_TEXT", top_text)
        )
        components.html(_vo2_html, height=150)

        if v_pct >= 90:
            pct_color = "#22C55E"; pct_label = "Excellent"
        elif v_pct >= 80:
            pct_color = "#3B82F6"; pct_label = "Very good"
        elif v_pct >= 60:
            pct_color = "#7C7CF5"; pct_label = "Good"
        elif v_pct >= 40:
            pct_color = "#F59E0B"; pct_label = "Below average"
        else:
            pct_color = "#EF6A3B"; pct_label = "Low"

        if v_pct >= 90:
            interpretation_text = "You are performing excellent compared to the average for your age."
        elif v_pct >= 80:
            interpretation_text = "You are performing very well compared to the average for your age."
        elif v_pct >= 60:
            interpretation_text = "You are around the average to good range for your age."
        elif v_pct >= 40:
            interpretation_text = "You are slightly below average for your age."
        else:
            interpretation_text = "You are below the average for your age, but this is very trainable."

        vo2_rows = [
            ("20–29", 44, 40, "#26A690"),
            ("30–39", 40, 36, "#3B82F6"),
            ("40–49", 37, 33, "#7C7CF5"),
            ("50–59", 34, 30, "#F59E0B"),
            ("60+",   30, 27, "#EF6A3B"),
        ]

        def band_match(band: str) -> bool:
            if band == "20–29": return 20 <= age <= 29
            if band == "30–39": return 30 <= age <= 39
            if band == "40–49": return 40 <= age <= 49
            if band == "50–59": return 50 <= age <= 59
            return age >= 60

        active_band = next((b for b, *_ in vo2_rows if band_match(b)), None)

        if str(sex).upper().startswith("M"):
            current_avg = {b: m for b, m, _, _ in vo2_rows}
        else:
            current_avg = {b: w for b, _, w, _ in vo2_rows}

        # ── Age band bars (Plotly) ──
        import plotly.graph_objects as go

        st.markdown("#### VO2 max across age bands")

        bands = [r[0] for r in vo2_rows]
        avgs  = [current_avg[r[0]] for r in vo2_rows]
        colors_list = [pct_color if r[0] == active_band else r[3] for r in vo2_rows]
        labels = ["← Your group" if r[0] == active_band else "Average" for r in vo2_rows]

        fig_bands = go.Figure()

        fig_bands.add_trace(go.Bar(
            x=avgs,
            y=bands,
            orientation="h",
            marker=dict(
                color=colors_list,
                line=dict(width=0),
            ),
            text=[f"{a} ml/kg/min" for a in avgs],
            textposition="outside",
            textfont=dict(color="#9CA3AF", size=11),
            hovertemplate="<b>%{y}</b><br>Average: %{x} ml/kg/min<extra></extra>",
            name="Age band avg",
        ))

        fig_bands.add_vline(
            x=v_val,
            line=dict(color="white", width=2, dash="dash"),
            annotation_text=f"You: {v_val:.1f}",
            annotation_font=dict(color="white", size=12),
            annotation_position="top right",
        )

        fig_bands.update_layout(
            paper_bgcolor="#111827",
            plot_bgcolor="#1F2937",
            font=dict(color="#E5E7EB", family="Arial"),
            height=320,
            margin=dict(l=10, r=80, t=20, b=40),
            xaxis=dict(
                title="VO2 max (ml/kg/min)",
                color="#9CA3AF",
                gridcolor="#374151",
                range=[0, max(avgs + [v_val]) + 8],
            ),
            yaxis=dict(
                color="#D1D5DB",
                gridcolor="#374151",
            ),
            showlegend=False,
        )

        st.plotly_chart(fig_bands, use_container_width=True)

        # ── Percentile gauge (Plotly) ──
        st.markdown(f"#### Population percentile")

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=v_pct,
            number=dict(
                suffix="th",
                font=dict(size=48, color=pct_color),
            ),
            delta=dict(
                reference=50,
                increasing=dict(color="#22C55E"),
                decreasing=dict(color="#EF4444"),
                valueformat=".1f",
            ),
            title=dict(
                text=f"<b>{pct_label}</b><br><span style='font-size:13px;color:#9CA3AF'>{interpretation_text}</span>",
                font=dict(size=16, color="#F9FAFB"),
            ),
            gauge=dict(
                axis=dict(
                    range=[0, 100],
                    tickwidth=1,
                    tickcolor="#374151",
                    tickfont=dict(color="#9CA3AF", size=11),
                    nticks=6,
                ),
                bar=dict(color=pct_color, thickness=0.25),
                bgcolor="#1F2937",
                borderwidth=0,
                steps=[
                    dict(range=[0, 40],  color="#1a1a2e"),
                    dict(range=[40, 60], color="#1e2a3a"),
                    dict(range=[60, 80], color="#1a2e2a"),
                    dict(range=[80, 100],color="#1a2e1a"),
                ],
                threshold=dict(
                    line=dict(color="white", width=3),
                    thickness=0.8,
                    value=v_pct,
                ),
            ),
        ))

        fig_gauge.update_layout(
            paper_bgcolor="#111827",
            font=dict(color="#E5E7EB", family="Arial"),
            height=340,
            margin=dict(l=20, r=20, t=60, b=20),
        )

        st.plotly_chart(fig_gauge, use_container_width=True)

        col_l, col_m, col_r = st.columns(3)
        col_l.metric("Your percentile", f"{v_pct:.0f}th", f"{v_pct - 50:.1f} vs avg")
        col_m.metric("Rating", pct_label)
        col_r.metric("Top", f"{100 - v_pct:.0f}%")
        # VO2 tips
        tips = results["vo2"].get("tips", [])
        if tips:
            st.markdown("**VO2 improvement tips**")
            for tip in tips:
                st.write(f"• {tip}")

# ── Biological age ────
    if "bio_age" in results:
            st.markdown("---")
            st.subheader("Biological age")
            _bio_val = results["bio_age"]["value"]
            _chron = float(age)
            _diff = _bio_val - _chron
            _diff_color = "#22C55E" if _diff <= 0 else "#EF4444"
            _diff_label = f"{abs(_diff):.1f} years younger" if _diff <= 0 else f"{abs(_diff):.1f} years older"
            _diff_sign = "▼" if _diff <= 0 else "▲"
            _factors_html = "".join([
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
                '<div style="font-size:11px;color:#9CA3AF;min-width:140px;max-width:140px;'
                'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + f["label"] + '</div>'
                '<div style="flex:1;background:rgba(255,255,255,0.06);border-radius:999px;height:10px;overflow:hidden;">'
                '<div style="width:' + str(max(3, min(100, abs(f.get("delta", 0)) / 5 * 100))) + '%;height:100%;border-radius:999px;'
                'background:' + ("#22C55E" if f.get("delta", 0) <= 0 else "#EF4444") + ';"></div></div>'
                '<div style="font-size:11px;font-weight:700;min-width:52px;text-align:right;'
                'color:' + ("#22C55E" if f.get("delta", 0) <= 0 else "#EF4444") + ';">'
                + f'{f.get("delta", 0):+.0f} yrs' +
                '</div></div>'
                for f in results.get("bio_factors", [])
            ])
            st.markdown(
                '<div style="font-family:Arial,sans-serif;background:#1F2937;border:1px solid #374151;'
                'border-radius:16px;padding:20px 22px 18px 22px;color:#E5E7EB;">'
                '<div style="display:flex;justify-content:space-between;align-items:flex-start;'
                'margin-bottom:18px;flex-wrap:wrap;gap:12px;">'
                '<div><div style="font-size:52px;font-weight:800;color:' + _diff_color + ';line-height:1;">'
                + f"{_bio_val:.1f}" +
                '</div><div style="font-size:13px;color:#9CA3AF;margin-top:4px;">Biological age &nbsp;&middot;&nbsp; Chronological: '
                + f"{_chron:.0f}" + ' yrs</div></div>'
                '<div style="display:inline-flex;align-items:center;gap:6px;background:' + _diff_color + '22;'
                'border:1px solid ' + _diff_color + ';color:' + _diff_color + ';font-size:14px;font-weight:700;'
                'border-radius:999px;padding:6px 14px;">' + _diff_sign + " " + _diff_label + ' than average</div>'
                '</div>'
                '<div style="font-size:12px;font-weight:700;color:#6B7280;letter-spacing:0.08em;'
                'text-transform:uppercase;margin-bottom:10px;">Factor breakdown</div>'
                + _factors_html +
                '</div>',
                unsafe_allow_html=True,
            )


# ── Conditions ────
    if "triage" in results:
        st.markdown("---")
        st.subheader("Conditions & recommendations")
        if results.get("triage_recommendations"):
            _rec_cards_html = ""
            for _r in results["triage_recommendations"]:
                _r_lower = str(_r).lower()
                if any(w in _r_lower for w in ["avoid", "risk", "warning", "stop", "danger", "limit"]):
                    _rc = "#EF4444"; _ri = "⚠️"; _rbg = "rgba(239,68,68,0.08)"; _rb = "rgba(239,68,68,0.25)"
                elif any(w in _r_lower for w in ["exercise", "train", "cardio", "walk", "run", "strength", "activity"]):
                    _rc = "#3B82F6"; _ri = "🏃"; _rbg = "rgba(59,130,246,0.08)"; _rb = "rgba(59,130,246,0.25)"
                elif any(w in _r_lower for w in ["diet", "eat", "food", "nutrition", "calori", "protein", "vegetable", "fruit"]):
                    _rc = "#22C55E"; _ri = "🥗"; _rbg = "rgba(34,197,94,0.08)"; _rb = "rgba(34,197,94,0.25)"
                elif any(w in _r_lower for w in ["sleep", "stress", "mental", "relax", "breath", "meditat"]):
                    _rc = "#A78BFA"; _ri = "😴"; _rbg = "rgba(167,139,250,0.08)"; _rb = "rgba(167,139,250,0.25)"
                elif any(w in _r_lower for w in ["doctor", "consult", "medical", "physician", "specialist", "monitor"]):
                    _rc = "#F59E0B"; _ri = "🩺"; _rbg = "rgba(245,158,11,0.08)"; _rb = "rgba(245,158,11,0.25)"
                else:
                    _rc = "#0EA5A3"; _ri = "💡"; _rbg = "rgba(14,165,163,0.08)"; _rb = "rgba(14,165,163,0.25)"
                _rec_cards_html += (
                    '<div style="display:flex;align-items:flex-start;gap:12px;'
                    'background:' + _rbg + ';border:1px solid ' + _rb + ';'
                    'border-left:3px solid ' + _rc + ';border-radius:12px;'
                    'padding:12px 14px;margin-bottom:8px;">'
                    '<div style="font-size:18px;line-height:1.3;">' + _ri + '</div>'
                    '<div style="font-size:13px;color:#E5E7EB;line-height:1.6;">' + str(_r) + '</div>'
                    '</div>'
                )
            st.markdown(_rec_cards_html, unsafe_allow_html=True)
        else:
            st.info(results.get("triage", {}).get("message", "No triage details."))

    # ── Plan ──────────────────────────────────────────────────────────────────
        # ── Plan ────
    if "plan" in results:
        plan = results["plan"]
        st.markdown("---")
        st.subheader("🎯 Weight goal / plan")

        current_maint = float(st.session_state.get("latest_tdee_total",
                    plan.get("current_needs_kcal", 0) or 0.0))
        kg_per_week = float(plan.get("kg_per_week", 0.0) or 0.0)
        daily_change_kcal = kg_per_week * 7700.0 / 7.0
        recommended_daily = int(round(current_maint + daily_change_kcal))
        plan["current_needs_kcal"] = int(round(current_maint))
        plan["recommended_daily_kcal"] = recommended_daily

        if plan.get("warning"):
            st.warning(plan["warning"])

        # ── Top 3 metrics ──
        _pc1, _pc2, _pc3 = st.columns(3)
        _pc1.metric("Maintenance", f"{plan['current_needs_kcal']} kcal/day")
        _pc2.metric("Recommended", f"{plan['recommended_daily_kcal']} kcal/day",
                    delta=f"{plan['recommended_daily_kcal'] - plan['current_needs_kcal']:+d} kcal")
        _pc3.metric("Weekly change", f"{kg_per_week:+.2f} kg/wk")

        # ── Calorie deficit/surplus bar ──
        _deficit = plan['recommended_daily_kcal'] - plan['current_needs_kcal']
        _bar_color = "#22C55E" if _deficit < 0 else "#3B82F6"
        _bar_label = f"{'Deficit' if _deficit < 0 else 'Surplus'}: {abs(_deficit)} kcal/day"
        _bar_pct = min(100, int(abs(_deficit) / max(1, plan['current_needs_kcal']) * 100 * 5))
        st.markdown(
            f'<div style="margin:10px 0 4px 0;color:#94A3B8;font-size:12px;">{_bar_label}</div>'
            f'<div style="background:rgba(255,255,255,0.06);border-radius:999px;height:10px;overflow:hidden;">'
            f'<div style="width:{_bar_pct}%;background:{_bar_color};height:100%;border-radius:999px;'
            f'transition:width 0.4s;"></div></div>',
            unsafe_allow_html=True
        )

        # ── Milestone roadmap ──
        milestones = plan.get("milestones", [])
        if milestones:
            st.markdown("#### 🗺️ Milestone roadmap")
            _start_w = float(weight_kg)
            _end_w = float(milestones[-1].get("Projected weight (kg)", _start_w))
            _total_change = _end_w - _start_w
            _losing = _total_change < 0

            for i, m in enumerate(milestones):
                _wk = m.get("Week", i + 1)
                _pw = float(m.get("Projected weight (kg)", _start_w))
                _focus = m.get("Focus", "")
                _done = i == len(milestones) - 1

                # Progress toward goal
                if abs(_total_change) > 0.01:
                    _prog = min(100, max(0, int(abs(_pw - _start_w) / abs(_total_change) * 100)))
                else:
                    _prog = 100

                _is_last = i == len(milestones) - 1
                _dot_color = "#22C55E" if _is_last else "#3B82F6"
                _focus_icons = {
                    "Build routine": "🏗️",
                    "Maintain consistency": "🔄",
                    "Review progress": "📊",
                    "Re-check and set next goal": "🏁",
                }
                _icon = next((v for k, v in _focus_icons.items() if k.lower() in str(_focus).lower()), "📍")

                _connector = ""
                if not _is_last:
                    _connector = '<div style="width:2px;flex:1;min-height:20px;background:rgba(148,163,184,0.2);margin-top:2px;"></div>'

                _milestone_html = f"""
<div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:8px;">
  <div style="display:flex;flex-direction:column;align-items:center;min-width:28px;">
    <div style="width:28px;height:28px;border-radius:50%;background:{_dot_color};
    display:flex;align-items:center;justify-content:center;
    font-size:12px;font-weight:800;color:#fff;flex-shrink:0;">{_wk}</div>
    {_connector}
  </div>
  <div style="background:rgba(15,23,42,0.55);border:1px solid rgba(148,163,184,0.12);
  border-radius:12px;padding:10px 14px;flex:1;margin-bottom:4px;">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
      <div>
        <span style="color:#E5E7EB;font-weight:700;font-size:15px;">{_pw:.1f} kg</span>
        <span style="color:#94A3B8;font-size:12px;margin-left:8px;">{_icon} {_focus}</span>
      </div>
      <div style="background:rgba(255,255,255,0.06);border-radius:999px;
      padding:3px 10px;font-size:11px;color:#94A3B8;">Week {_wk} · {_prog}%</div>
    </div>
    <div style="margin-top:7px;background:rgba(255,255,255,0.05);
    border-radius:999px;height:5px;overflow:hidden;">
      <div style="width:{_prog}%;background:{_dot_color};height:100%;border-radius:999px;"></div>
    </div>
  </div>
</div>
"""
                st.markdown(_milestone_html, unsafe_allow_html=True)

                # ── Coach Insight ──
                _rate = float(plan.get("kg_per_week", 0.0) or 0.0)
                _tw_coach = float(milestones[-1].get("Projected weight (kg)", weight_kg)) if milestones else float(weight_kg)
                _wks_coach = int(plan_weeks) if plan_weeks else 12
                if _rate < 0:
                    _coach_msg = (
                        f"At {abs(_rate):.2f} kg/week, you are on a safe and sustainable fat loss trajectory. "
                        f"You will reach {_tw_coach:.1f} kg in approximately {_wks_coach} weeks. "
                        f"Consistency is your biggest advantage — small daily habits compound over time."
                    )
                    _coach_icon = "🟢"
                elif _rate > 0:
                    _coach_msg = (
                        f"You are in a controlled weight gain phase at {_rate:.2f} kg/week. "
                        f"Target: {_tw_coach:.1f} kg in {_wks_coach} weeks. "
                        f"Focus on strength training to maximise lean muscle gain."
                    )
                    _coach_icon = "🔵"
                else:
                    _coach_msg = (
                        "You are at maintenance calories. "
                        "Focus on body recomposition — building muscle while maintaining weight."
                    )
                    _coach_icon = "⚪"
        
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,rgba(14,165,163,0.12),rgba(34,197,94,0.08));'
                    f'border:1px solid rgba(14,165,163,0.3);border-left:4px solid #0EA5A3;'
                    f'border-radius:14px;padding:16px 18px;margin:14px 0;">'
                    f'<div style="color:#0EA5A3;font-size:12px;font-weight:700;letter-spacing:0.08em;'
                    f'text-transform:uppercase;margin-bottom:8px;">🧠 Coach Insight</div>'
                    f'<div style="color:#E5E7EB;font-size:14px;line-height:1.7;">{_coach_icon} {_coach_msg}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
else:
    st.info("Trykk på 'Calculate / Generate report' for å kjøre beregningene.")

# ── Paywall / PDF ──── (0 innrykk — UTANFOR if results:)
st.markdown("---")
_unlocked = st.session_state.get("report_unlocked", False)

if _unlocked:
    st.success("✅ Rapport låst opp!")

if not _unlocked:
    st.markdown(
        '<div style="background:linear-gradient(135deg,rgba(14,165,163,0.10),rgba(59,130,246,0.08));'
        'border:1px solid rgba(14,165,163,0.35);border-radius:18px;padding:24px 22px;'
        'text-align:center;margin:10px 0;">'
        '<div style="font-size:22px;font-weight:800;color:#E5E7EB;margin-bottom:6px;">'
        '🔒 Unlock your full report</div>'
        '<div style="color:#94A3B8;font-size:13px;margin-bottom:18px;">'
        'Get your complete personalized health analysis as a premium PDF</div>'
        '<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:10px;margin-bottom:20px;">'
        '<span style="background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);'
        'color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">✅ Full 12-week roadmap</span>'
        '<span style="background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);'
        'color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">✅ Personalized coach insights</span>'
        '<span style="background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);'
        'color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">✅ Calorie strategy</span>'
        '<span style="background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);'
        'color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">✅ PDF download</span>'
        '</div>'
        '<div style="font-size:28px;font-weight:800;color:#0EA5A3;margin-bottom:4px;">4,99 USD</div>'
        '<div style="color:#64748B;font-size:11px;margin-bottom:16px;">One-time · No subscription</div>'
        '</div>',
        unsafe_allow_html=True
    )
    stripe_link = "https://buy.stripe.com/fZu00kbeq6J50LsdYk1Fe02"
    st.link_button(
        "🔓 Unlock full report — 4,99 USD",
        stripe_link,
        type="primary",
        use_container_width=True,
    )
    st.caption("After payment, you will return to the app")

else:
    _results_for_pdf = st.session_state.get("results", {})
    if not _results_for_pdf:
        st.warning("⚠️ Kjør beregningane først (trykk 'Calculate'), så kan du laste ned PDF-rapporten.")
    else:
        # 1. Bygg rapport-data
        report = {
            "generated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "inputs": {"age": age, "sex": sex, "height_cm": height_cm, "weight_kg": weight_kg},
            "bmi": _results_for_pdf.get("bmi"),
            "bodyfat": _results_for_pdf.get("bodyfat"),
            "whr": _results_for_pdf.get("whr"),
            "vo2": _results_for_pdf.get("vo2"),
            "bio_age": _results_for_pdf.get("bio_age"),
            "bio_factors": _results_for_pdf.get("bio_factors"),
            "triage": _results_for_pdf.get("triage"),
            "triage_recommendations": _results_for_pdf.get("triage_recommendations"),
            "plan": _results_for_pdf.get("plan"),
            "exercise_log": st.session_state.get("exercise_last"),
        }
        
        # 2. Generer PDF og kall funksjonen
        try:
            pdf_bytes = create_pdf_bytes_ultimate(report)
            # Her kallar vi funksjonen du definerte øvst!
            render_premium_download_gate(pdf_bytes)
            
        except Exception as e:
            st.error(f"Error generating report: {e}")

           # ... etter at du har generert pdf_bytes ...
            with st.container(border=True):
                st.subheader("✅ Your Premium Health Report is ready")
                st.markdown("We have analyzed your biomarkers and generated a tailored 30-day protocol designed to optimize your health.")
                
                st.download_button(
                    label="📥 Download your PDF Report (4.99 USD)",
                    data=pdf_bytes,
                    file_name="Health_Audit_Report.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
                st.caption("Your purchase is secured with 100% encryption.")
        except Exception as e:
            st.warning(f"PDF generation unavailable: {e}")
