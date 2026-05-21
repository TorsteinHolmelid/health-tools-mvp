from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO

import streamlit as st
import streamlit.components.v1 as components
import calculators

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from calculators import (
    bmr_mifflin,
    tdee_including_weekly_exercise,
)

# ── Resting HR sync ──────────────────────────────────────────────────────────
def sync_from_basic():
    val = st.session_state.get("basic_resting_hr")
    if val is None:
        return
    try:
        v = int(val)
    except Exception:
        return
    st.session_state["resting_hr"] = v
    st.session_state["ui_resting_hr"] = v
    st.session_state["global_resting_hr"] = v


def sync_from_calc():
    val = st.session_state.get("ui_resting_hr")
    if val is None:
        return
    try:
        v = int(val)
    except Exception:
        return
    st.session_state["resting_hr"] = v
    st.session_state["basic_resting_hr"] = v
    st.session_state["global_resting_hr"] = v


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Health Tools MVP",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
img, svg, iframe { max-width: 100% !important; height: auto !important; }
@media (max-width: 600px) {
    .main > div { padding-left: 8px !important; padding-right: 8px !important; }
    .streamlit-expanderHeader { font-size: 16px !important; }
}
.stApp { background-color: #0b1220; color: #e6eef8; }
[data-testid="stSidebar"] {
  background-color: #0b1220 !important; color: #e6eef8 !important;
  border-right: 1px solid rgba(255,255,255,0.03); padding: 18px;
}
.stTextInput>div>div>input, .stNumberInput>div>div>input,
textarea, select, .stSelectbox>div>div>div, .stDateInput>div>div>input {
  background-color: rgba(255,255,255,0.04) !important; color: #e6eef8 !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 8px !important; padding: 8px !important;
}
.stExpander > button {
  background-color: rgba(255,255,255,0.03) !important; color: #e6eef8 !important;
  border: 1px solid rgba(255,255,255,0.04) !important;
  border-radius: 8px !important; padding: 8px 12px !important;
}
.result-box {
  background-color: rgba(255,255,255,0.03); color: #e6eef8;
  border: 1px solid rgba(255,255,255,0.04);
  padding: 14px; border-radius: 10px; margin-bottom: 12px;
}
.stButton>button {
  background-color: #0ea5a3 !important; color: #022b2a !important;
  border-radius: 8px !important; padding: 8px 12px !important; font-weight: 600 !important;
}
.stButton>button:hover { filter: brightness(0.95); }
h1, h2, h3, p, label { color: #e6eef8 !important; }
.stTable td, .stTable th { color: #e6eef8 !important; }
@media (max-width: 600px) { .stButton>button { width: 100% !important; } }
</style>
""", unsafe_allow_html=True)

st.title("Health Tools — MVP")
st.caption("Educational tool only — not a diagnostic tool. Data is not stored.")

# ── Consent ───────────────────────────────────────────────────────────────────
if "consent_given" not in st.session_state:
    st.session_state.consent_given = False

if not st.session_state.consent_given:
    with st.expander("Please read: Consent & privacy", expanded=True):
        st.markdown("This demo stores nothing by default and is for educational purposes only. By continuing you confirm you understand it's not clinical advice.")
    cols = st.columns([1, 1])
    if cols[0].button("I agree", key="consent_agree"):
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


def create_pdf_bytes(report: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=14*mm, rightMargin=14*mm,
                            topMargin=18*mm, bottomMargin=14*mm)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle("T", parent=styles["Title"], fontName="Helvetica-Bold",
                             fontSize=20, leading=24, alignment=TA_CENTER,
                             textColor=colors.HexColor("#0f172a"))
    sub_s = ParagraphStyle("S", parent=styles["BodyText"], fontName="Helvetica",
                           fontSize=9.5, leading=12, alignment=TA_CENTER,
                           textColor=colors.HexColor("#475569"))
    sec_s = ParagraphStyle("H", parent=styles["Heading2"], fontName="Helvetica-Bold",
                           fontSize=13, leading=15, textColor=colors.HexColor("#0f172a"), spaceAfter=4)
    body_s = ParagraphStyle("B", parent=styles["BodyText"], fontName="Helvetica",
                            fontSize=9.2, leading=12, textColor=colors.HexColor("#111827"))
    small_s = ParagraphStyle("Sm", parent=styles["BodyText"], fontName="Helvetica-Oblique",
                             fontSize=7.8, leading=10, textColor=colors.HexColor("#475569"))

    story = []
    story.append(Paragraph("Health Tools — Report", title_s))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Educational report. Not a medical diagnosis.", sub_s))
    story.append(Spacer(1, 6*mm))

    inp = report.get("inputs", {})
    story.append(make_key_value_table([
        ("Generated", report.get("generated", "")),
        ("Age", str(inp.get("age", "—"))),
        ("Sex", str(inp.get("sex", "—"))),
        ("Height", f'{inp.get("height_cm", "—")} cm'),
        ("Weight", f'{inp.get("weight_kg", "—")} kg'),
    ]))
    story.append(Spacer(1, 6*mm))

    # Summary
    summary = []
    if report.get("bmi"):
        summary.append(("BMI", f'{report["bmi"]["value"]:.1f} ({report["bmi"]["category"]})'))
    if report.get("vo2"):
        v = report["vo2"]
        summary.append(("VO2max", f'{v["value"]:.1f} ml/kg/min | {v.get("rating","—")} | {v.get("percentile","—")}th percentile'))
    if report.get("bio_age"):
        summary.append(("Biological age", f'{report["bio_age"]["value"]:.1f} years'))
    if report.get("triage"):
        summary.append(("Conditions note", report["triage"].get("message", "—")))
    if summary:
        story.append(Paragraph("Summary", sec_s))
        story.append(make_key_value_table(summary))
        story.append(Spacer(1, 6*mm))

    # BMI
    if report.get("bmi"):
        story.append(Paragraph("BMI", sec_s))
        story.append(Paragraph("BMI is a screening measure, not a diagnosis.", body_s))
        story.append(Spacer(1, 2*mm))
        story.append(make_key_value_table([
            ("BMI", f'{report["bmi"]["value"]:.1f}'),
            ("Category", report["bmi"]["category"]),
        ]))
        story.append(Spacer(1, 4*mm))

    # VO2
    if report.get("vo2"):
        v = report["vo2"]
        story.append(Paragraph("VO2max", sec_s))
        story.append(make_key_value_table([
            ("Method", v.get("method", "—")),
            ("VO2max", f'{v["value"]:.1f} ml/kg/min'),
            ("Age band", v.get("age_band", "—")),
            ("Percentile", f'{v.get("percentile","—")}th'),
            ("Rating", v.get("rating", "—")),
        ]))
        story.append(Spacer(1, 4*mm))
        tips = v.get("tips", [])
        if tips:
            story.append(Paragraph("VO2 improvement tips", sec_s))
            for tip in tips:
                story.append(Paragraph(f"• {escape(str(tip))}", body_s))
            story.append(Spacer(1, 4*mm))

    # Biological age
    if report.get("bio_age"):
        story.append(Paragraph("Biological age", sec_s))
        story.append(make_key_value_table([("Biological age", f'{report["bio_age"]["value"]:.1f} years')]))
        story.append(Spacer(1, 3*mm))
        if report.get("bio_factors"):
            story.append(make_key_value_table(
                [(f["label"], f'{f.get("delta", 0):+.0f} years') for f in report["bio_factors"]],
                col_widths=(70*mm, 100*mm)
            ))
            story.append(Spacer(1, 4*mm))

    # Conditions
    if report.get("triage"):
        story.append(Paragraph("Conditions & Recommendations", sec_s))
        story.append(make_key_value_table([("Note", report["triage"].get("message", "—"))]))
        story.append(Spacer(1, 3*mm))
        recs = report.get("triage_recommendations", [])
        for r in recs:
            story.append(Paragraph(f"• {escape(str(r))}", body_s))
        if recs:
            story.append(Spacer(1, 4*mm))

    # Plan
    if report.get("plan") and not report["plan"].get("error"):
        plan = report["plan"]
        story.append(Paragraph("Weight goal / plan", sec_s))
        story.append(make_key_value_table([
            ("Current maintenance kcal", f'{plan.get("current_needs_kcal","—")} kcal/day'),
            ("Recommended daily kcal", f'{plan.get("recommended_daily_kcal","—")} kcal/day'),
            ("Expected weekly change", f'{plan.get("kg_per_week",0):+.2f} kg/week'),
        ]))
        story.append(Spacer(1, 3*mm))
        milestones = plan.get("milestones", [])
        if milestones:
            story.append(make_key_value_table(
                [(f'Week {m.get("Week")}', f'{m.get("Projected weight (kg)")} kg — {m.get("Focus")}') for m in milestones],
                col_widths=(40*mm, 135*mm)
            ))
            story.append(Spacer(1, 4*mm))

    # Exercise log
    ex = report.get("exercise_log")
    if ex:
        story.append(Paragraph("Exercise log", sec_s))
        story.append(make_key_value_table([
            ("Activity", ex.get("activity", "—")),
            ("Intensity", ex.get("intensity", "—")),
            ("Minutes/session", str(ex.get("minutes", "—"))),
            ("Sessions/week", str(ex.get("sessions_per_week", "—"))),
            ("kcal/session", f'{ex.get("kcal_per_session","—"):.0f}'),
            ("kcal/week", f'{ex.get("kcal_per_week","—"):.0f}'),
        ]))
        story.append(Spacer(1, 4*mm))

    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "Disclaimer: educational demo only. Not clinically validated. "
        "For symptoms, worsening health, or emergency signs, seek professional help immediately.",
        small_s
    ))

    def add_header(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#0f172a"))
        canvas.rect(0, A4[1] - 26, A4[0], 26, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(doc.leftMargin, A4[1] - 18, "Health Tools — Report")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(A4[0] - doc.rightMargin, A4[1] - 18, f"Page {canvas.getPageNumber()}")
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(doc.leftMargin, 10, "Educational use only — not medical advice")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_header, onLaterPages=add_header)
    buffer.seek(0)
    return buffer.read()


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("Modules")
run_bmi = st.sidebar.checkbox("BMI calculator", value=True, key="s_bmi")
run_vo2 = st.sidebar.checkbox("VO2max estimate", value=True, key="s_vo2")
run_bioage = st.sidebar.checkbox("Biological age", value=True, key="s_bio")
run_conditions = st.sidebar.checkbox("Conditions & recommendations", value=True, key="s_conditions")
run_plan = st.sidebar.checkbox("Weight goal / plan", value=True, key="s_plan")
st.sidebar.markdown("---")
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

# ── Basic inputs ──────────────────────────────────────────────────────────────
st.header("Basic information")

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

if age < 18:
    st.warning("BMI and fitness estimates are less reliable under 18.")
elif age >= 70:
    st.info("For older adults, BMI is often less informative.")

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
        use_waist_hip = st.checkbox("Add waist and hip measurements", value=False, key="b_use_whr")
        if use_waist_hip:
            c1, c2 = st.columns(2)
            with c1:
                waist_cm = st.number_input("Waist (cm)", min_value=30.0, max_value=300.0,
                                            value=80.0, format="%.1f", key="b_waist")
            with c2:
                hip_cm = st.number_input("Hip (cm)", min_value=30.0, max_value=300.0,
                                          value=95.0, format="%.1f", key="b_hip")
        use_neck = st.checkbox("Add neck measurement for body-fat estimate", value=False, key="b_use_neck")
        if use_neck:
            neck_cm = st.number_input("Neck (cm)", min_value=20.0, max_value=80.0,
                                       value=38.0, format="%.1f", key="b_neck")
        bodyfat_requested = st.checkbox("Estimate body fat (Navy method)", value=False, key="b_bodyfat")

# ── VO2 inputs ────────────────────────────────────────────────────────────────
if run_vo2:
    with st.expander("Cardio / VO2max inputs", expanded=True):
        activity_level = st.selectbox(
            "Physical activity level",
            ["Sedentary", "Light", "Moderate", "Active", "Very active", "Athlete"],
            index=2, key="v_activity"
        )
        weekly_minutes = st.number_input("Weekly minutes of moderate-to-vigorous activity",
                                          min_value=0, max_value=2000, value=150, key="v_weekly_minutes")
        session_intensity = st.slider("Typical session intensity (1=very light, 5=very intense)",
                                       min_value=1, max_value=5, value=3, key="v_session_intensity")

        resting_hr_unknown = st.checkbox(
            "I don't know my resting heart rate",
            value=(st.session_state.get("global_resting_hr") is None),
            key="vo2_rhr_unknown"
        )
        if not resting_hr_unknown:
            default_rhr = st.session_state.get("global_resting_hr") or 70
            resting_hr = st.number_input("Resting heart rate (bpm)", min_value=30, max_value=220,
                                          value=default_rhr, key="vo2_rhr_value")
            st.caption("Prefilled from Resting HR above.")
        else:
            resting_hr = None

        max_hr_unknown = st.checkbox("I don't know my max heart rate", value=True, key="vo2_maxhr_unknown")
        if not max_hr_unknown:
            max_hr = st.number_input("Estimated max heart rate (bpm)", min_value=40, max_value=240,
                                      value=180, key="vo2_maxhr_val")
        else:
            max_hr = None

        measured_vo2_input = st.number_input(
            "If you know a measured VO2max (Apple Watch, lab, etc.), enter it here",
            min_value=0.0, value=0.0, format="%.1f", key="vo2_measured_input"
        )
        vo2_method = st.selectbox(
            "VO2 calculation method",
            ["Questionnaire", "Cooper (12-min)", "Rockport (1-mile)", "Measured value"],
            index=0, key="vo2_method_select"
        )
        if vo2_method == "Cooper (12-min)":
            vo2_distance_m = st.number_input("12-minute distance (meters)", min_value=0.0,
                                              value=0.0, format="%.1f", key="vo2_cooper_distance")
        elif vo2_method == "Rockport (1-mile)":
            rockport_time_min = st.number_input("1-mile time (minutes)", min_value=0.1,
                                                 value=15.0, format="%.2f", key="vo2_rockport_time")
            rockport_hr = st.number_input("Heart rate at the end (bpm)", min_value=30, max_value=220,
                                           value=140, key="vo2_rockport_hr")

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

with st.expander("🏃 Exercise log — enter before clicking Calculate", expanded=False):
    st.markdown("Specify your exercise habits for a more precise TDEE and plan. MET values are approximate.")

    sessions_per_week = st.number_input("Sessions per week", min_value=0, max_value=21,
                                         value=3, step=1, key="ui_sessions_per_week")

    default_avg = st.session_state.get("global_avg_hr")
    avg_hr = st.number_input(
        "Average HR during sessions (bpm) — optional",
        min_value=30, max_value=220,
        value=default_avg if default_avg is not None else 130,
        key="ui_avg_hr",
    )
    st.session_state["global_avg_hr"] = int(avg_hr) if avg_hr is not None else None

    activity_ex = st.selectbox("Activity type", list(ACTIVITIES.keys()), key="ui_activity_type")
    intensity_label = st.selectbox("Intensity", ["Light", "Moderate", "Hard"], index=1, key="ui_intensity")
    minutes_per_session = st.number_input("Minutes per session", min_value=1, max_value=300,
                                           value=45, step=5, key="ui_minutes")
    rpe = st.slider("Perceived exertion (RPE) 1–10", 1, 10, 5, key="ui_rpe")
    rpe_multiplier = 0.85 + (rpe - 1) * (0.4 / 9)

    use_hr = st.checkbox("Use average session HR to refine estimate", key="ui_use_hr")
    avg_hr_for_calc = None
    resting_hr_for_calc = None
    if use_hr:
        avg_hr_for_calc = st.number_input(
            "Average HR during session (bpm)",
            min_value=30, max_value=220,
            value=avg_hr if avg_hr is not None else 130,
            key="ui_avg_hr_calc",
        )
        resting_hr_for_calc = st.number_input(
            "Resting HR (bpm)",
            min_value=30, max_value=120, value=60,
            key="ui_resting_hr",
            on_change=sync_from_calc,
        )

    # Also allow manual kcal override
    manual_kcal = st.checkbox("I know my exact kcal burn per session — enter manually", key="ui_manual_kcal")
    manual_kcal_val = 0.0
    if manual_kcal:
        manual_kcal_val = st.number_input("kcal burned per session", min_value=0.0, max_value=5000.0,
                                           value=300.0, format="%.0f", key="ui_manual_kcal_val")

    # Compute
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
        "activity": activity_ex,
        "intensity": intensity_label,
        "minutes": int(minutes_per_session),
        "sessions_per_week": int(sessions_per_week),
        "kcal_per_session": round(kcal_per_session, 1),
        "kcal_per_week": round(kcal_per_week_ex, 1),
        "rpe": int(rpe),
        "avg_hr": int(avg_hr_for_calc) if avg_hr_for_calc is not None else None,
    }

    st.write(f"Estimated exercise burn: **{kcal_per_week_ex:.0f} kcal/week** "
             f"({kcal_per_session:.0f} kcal/session × {sessions_per_week} sessions)")
    st.caption("MET values are approximate. Use the HR option or adjust RPE for a more accurate estimate.")

# ── Biological age inputs ─────────────────────────────────────────────────────
if run_bioage:
    with st.expander("Biological age inputs", expanded=True):
        st.caption("Leave any field blank or use 'I don't know' where available.")
        smoker = st.checkbox("Smoker?", key="bio_smoker")
        diabetes = st.checkbox("Diabetes?", key="bio_diabetes")
        family_history = st.checkbox("Family history of premature cardiovascular disease?", key="bio_family_hist")
        if sex == "F":
            menopause = st.checkbox("Post-menopausal?", key="bio_menopause")
        st.markdown("#### Cardiovascular")
        bp_unknown = st.checkbox("I don't know my systolic blood pressure", value=True, key="bio_bp_unknown")
        if not bp_unknown:
            bp_systolic = st.number_input("Systolic blood pressure (mmHg)", min_value=70.0,
                                           max_value=260.0, value=120.0, key="bio_bp_val")
        chol_unknown = st.checkbox("I don't know my cholesterol", value=True, key="bio_chol_unknown")
        if not chol_unknown:
            cholesterol = st.number_input("Cholesterol (mg/dL)", min_value=50.0,
                                           max_value=500.0, value=180.0, key="bio_chol_val")
        rhr_unknown = st.checkbox("I don't know my resting heart rate", value=True, key="bio_rhr_unknown")
        if not rhr_unknown:
            resting_hr = st.number_input("Resting heart rate (bpm)", min_value=30, max_value=220,
                                          value=70, key="bio_rhr_val")
        st.markdown("#### Lifestyle")
        sleep_unknown = st.checkbox("I don't know my sleep duration", value=True, key="bio_sleep_unknown")
        if not sleep_unknown:
            sleep_hours = st.number_input("Average sleep per night (hours)", min_value=0.0,
                                           max_value=24.0, value=7.0, format="%.1f", key="bio_sleep_val")
        alcohol_unknown = st.checkbox("I don't know my alcohol intake", value=True, key="bio_alc_unknown")
        if not alcohol_unknown:
            alcohol_units = st.number_input("Alcohol units per week", min_value=0,
                                             max_value=300, value=0, key="bio_alc_val")
        fruit_veg = st.number_input("Daily fruit & vegetable servings", min_value=0,
                                     max_value=20, value=3, key="bio_fv")
        perceived_stress = st.slider("Perceived stress (1 low – 10 high)", min_value=1,
                                      max_value=10, value=5, key="bio_stress")
        grip_unknown = st.checkbox("I don't know my grip strength", value=True, key="bio_grip_unknown")
        if not grip_unknown:
            grip_strength = st.number_input("Grip strength (kg)", min_value=0.0,
                                             max_value=100.0, value=30.0, format="%.1f", key="bio_grip_val")
        st.markdown("#### Body composition")
        bio_waist_unknown = st.checkbox("I don't know my waist-to-hip ratio", value=True, key="bio_waist_unknown")
        if not bio_waist_unknown:
            c1, c2 = st.columns(2)
            with c1:
                waist_bio = st.number_input("Waist (cm)", min_value=30.0, max_value=300.0,
                                             value=80.0, format="%.1f", key="bio_waist_val")
            with c2:
                hip_bio = st.number_input("Hip (cm)", min_value=30.0, max_value=300.0,
                                           value=95.0, format="%.1f", key="bio_hip_val")
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
    with st.expander("Goal / plan", expanded=False):
        create_plan = st.checkbox("Create a simple plan to reach a target weight/BMI",
                                   value=False, key="plan_create")
        if create_plan:
            plan_type = st.radio("Plan target type",
                                  ["Target weight (kg)", "Target BMI"], index=0, key="plan_type")
            if plan_type == "Target weight (kg)":
                target_weight = st.number_input("Target weight (kg)", min_value=30.0,
                                                 max_value=400.0, value=65.0, format="%.1f",
                                                 key="plan_target_weight")
            else:
                target_bmi = st.number_input("Target BMI", min_value=12.0, max_value=45.0,
                                              value=22.0, format="%.1f", key="plan_target_bmi")
            plan_weeks = st.number_input("Weeks to achieve target", min_value=4, max_value=52,
                                          value=12, step=1, key="plan_weeks")

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
      <div class="bmi-val">{b:.1f}</div>
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

        c1, c2, c3 = st.columns(3)
        c1.metric("Your VO2 max", f"{v_val:.1f} ml/kg/min")
        c2.metric("Percentile", f"{v_pct:.0f}%")
        c3.metric("Ranking", top_text)

        # ── FIX: pct_color based on actual percentile ──
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

        # Age-band reference data  (male avg, female avg, bar colour)
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

        # ── FIX: bar colour = band's own colour; active band uses pct_color ──
        band_bars_html = "".join([
            f"""
      <div class="band{' band-active' if band == active_band else ''}">
        <div class="band-lbl">{band}</div>
        <div class="band-bar">
          <div class="band-fill" style="width:{min(100, max(0, int(current_avg[band] / 50.0 * 100)))}%;
               background:{pct_color if band == active_band else color};"></div>
          <div class="band-badge">{current_avg[band]} avg</div>
        </div>
        <div class="band-val">{'Your group' if band == active_band else 'Average'}</div>
      </div>"""
            for band, _, _, color in vo2_rows
        ])

        vo2_html = f"""
<style>
  .vo2-wrap{{font-family:Arial,sans-serif;color:#E5E7EB;padding:2px}}
  .vo2-grid {{ display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 14px; align-items: stretch; }}
  @media (max-width: 700px) {{ .vo2-grid {{ grid-template-columns: 1fr; }} }}
  .vo2-card{{background:#1F2937;border:1px solid #374151;border-radius:16px;padding:18px}}
  .vo2-title{{margin:0 0 6px 0;font-size:20px;font-weight:700;color:#F9FAFB}}
  .vo2-sub{{margin:0 0 16px 0;font-size:12px;line-height:1.4;color:#9CA3AF}}
  .metric-row{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-bottom:16px}}
  .metric{{background:#111827;border:1px solid #374151;border-radius:12px;padding:10px 12px;min-width:0}}
  .metric-k{{margin:0 0 4px 0;font-size:12px;color:#9CA3AF}}
  .metric-v{{margin:0;font-size:20px;font-weight:700;color:#F9FAFB;line-height:1.1}}
  .band{{display:grid;grid-template-columns:56px 1fr 70px;gap:10px;align-items:center;margin:10px 0}}
  .band-lbl{{font-size:12px;color:#D1D5DB;white-space:nowrap}}
  .band-bar{{height:16px;background:#111827;border:1px solid #374151;border-radius:999px;overflow:hidden;position:relative}}
  .band-fill{{height:100%;border-radius:999px}}
  .band-badge{{position:absolute;right:8px;top:50%;transform:translateY(-50%);font-size:11px;font-weight:700;color:#111827;background:rgba(255,255,255,0.88);padding:1px 6px;border-radius:999px}}
  .band-val{{text-align:right;font-size:12px;font-weight:700;color:#E5E7EB}}
  .band-active{{background:#F8FAFC;border-radius:12px;padding:8px 10px}}
  .band-active .band-lbl{{color:#0F172A;font-weight:700}}
  .band-active .band-val{{color:#26A690}}
  .pill-row{{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}}
  .pill{{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:#CBD5E1;background:#111827;border:1px solid #374151;border-radius:999px;padding:6px 10px}}
  .dot{{width:10px;height:10px;border-radius:50%;flex:0 0 10px}}
  .gauge-wrap{{display:flex;flex-direction:column;align-items:center}}
  .gauge-head{{width:100%;display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:8px}}
  .gauge-k{{margin:0;font-size:20px;font-weight:700;color:#F9FAFB}}
  .gauge-sub{{margin:4px 0 0 0;font-size:12px;color:#9CA3AF;line-height:1.4}}
  .pct-num{{margin:0;font-size:34px;font-weight:700;line-height:1;color:{pct_color};text-align:right}}
  .pct-lbl{{margin:3px 0 0 0;font-size:12px;color:#D1D5DB;text-align:right}}
  .callout{{width:100%;background:#111827;border:1px solid #374151;border-radius:12px;padding:12px;color:#D1D5DB;font-size:12px;line-height:1.45;margin-top:12px}}
  .legend-col{{width:100%;margin-top:14px;display:grid;gap:8px}}
  .legend-item{{display:flex;align-items:center;gap:8px;background:#111827;border:1px solid #374151;border-radius:999px;padding:8px 10px;font-size:12px;color:#CBD5E1}}
</style>
<div class="vo2-wrap">
  <div class="vo2-grid">
    <div class="vo2-card">
      <div class="vo2-title">VO2 max across age bands</div>
      <div class="vo2-sub">A live and readable view.</div>
      <div class="metric-row">
        <div class="metric"><div class="metric-k">Your VO2 max</div><div class="metric-v">{v_val:.1f}</div></div>
        <div class="metric"><div class="metric-k">Age band</div><div class="metric-v">{active_band or "—"}</div></div>
        <div class="metric"><div class="metric-k">Rating</div><div class="metric-v">{pct_label}</div></div>
      </div>
      {band_bars_html}
      <div class="pill-row">
        <div class="pill"><span class="dot" style="background:#26A690"></span>Very strong (20s)</div>
        <div class="pill"><span class="dot" style="background:#3B82F6"></span>Strong (30s)</div>
        <div class="pill"><span class="dot" style="background:#7C7CF5"></span>Mid range (40s)</div>
        <div class="pill"><span class="dot" style="background:#F59E0B"></span>Below avg (50s)</div>
        <div class="pill"><span class="dot" style="background:#EF6A3B"></span>Needs work (60+)</div>
      </div>
    </div>
    <div class="vo2-card">
      <div class="gauge-wrap">
        <div class="gauge-head">
          <div>
            <div class="gauge-k">Population percentile</div>
            <div class="gauge-sub">How you compare with others in your age group.</div>
          </div>
          <div>
            <div class="pct-num">{v_pct:.0f}%</div>
            <div class="pct-lbl">{pct_label}</div>
          </div>
        </div>
        <svg width="100%" viewBox="0 0 260 170">
          <path d="M40 122 A90 90 0 0 1 220 122" fill="none" stroke="#4B5563" stroke-width="18" stroke-linecap="round" pathLength="100"/>
          <path d="M40 122 A90 90 0 0 1 220 122" fill="none" stroke="{pct_color}" stroke-width="18" stroke-linecap="round" pathLength="100" stroke-dasharray="{v_pct} 100"/>
          <circle cx="130" cy="122" r="50" fill="#1F2937" stroke="#374151" stroke-width="1"/>
          <text x="130" y="116" text-anchor="middle" font-size="36" font-weight="700" fill="#F9FAFB">{int(round(v_pct))}</text>
          <text x="130" y="136" text-anchor="middle" font-size="12" fill="#CBD5E1">percentile</text>
          <text x="40" y="158" text-anchor="start" font-size="12" fill="#9CA3AF">0</text>
          <text x="130" y="158" text-anchor="middle" font-size="12" fill="#9CA3AF">50</text>
          <text x="220" y="158" text-anchor="end" font-size="12" fill="#9CA3AF">100</text>
        </svg>
        <div class="callout"><b>Interpretation:</b> {interpretation_text}</div>
        <div class="legend-col">
          <div class="legend-item"><span class="dot" style="background:{pct_color}"></span>Your result: {pct_label}</div>
          <div class="legend-item"><span class="dot" style="background:#3B82F6"></span>Population average</div>
          <div class="legend-item"><span class="dot" style="background:#26A690"></span>Better than average</div>
        </div>
      </div>
    </div>
  </div>
</div>"""

        components.html(vo2_html, height=1100, scrolling=False)

        # VO2 tips
        tips = results["vo2"].get("tips", [])
        if tips:
            st.markdown("**VO2 improvement tips**")
            for tip in tips:
                st.write(f"• {tip}")

    # ── Biological age ────────────────────────────────────────────────────────
    if "bio_age" in results:
        st.markdown("---")
        st.subheader("Biological age")
        st.metric("Biological age", f"{results['bio_age']['value']:.1f} years")
        if results.get("bio_factors"):
            st.markdown("**Factor breakdown**")
            factor_rows = [
                {"Factor": f["label"], "Effect": f"{f.get('delta', 0):+.0f} years"}
                for f in results["bio_factors"]
            ]
            st.table(factor_rows)

    # ── Conditions ────────────────────────────────────────────────────────────
    if "triage" in results:
        st.markdown("---")
        st.subheader("Conditions & recommendations")
        if results.get("triage_recommendations"):
            for r in results["triage_recommendations"]:
                st.write(r)
        else:
            st.info(results.get("triage", {}).get("message", "No triage details."))

    # ── Plan ──────────────────────────────────────────────────────────────────
    if "plan" in results:
        plan = results["plan"]
        st.markdown("---")
        st.subheader("Weight goal / plan")

        current_maint = float(st.session_state.get("latest_tdee_total",
                                                     plan.get("current_needs_kcal", 0) or 0.0))
        kg_per_week = float(plan.get("kg_per_week", 0.0) or 0.0)
        daily_change_kcal = kg_per_week * 7700.0 / 7.0
        recommended_daily = int(round(current_maint + daily_change_kcal))
        plan["current_needs_kcal"] = int(round(current_maint))
        plan["recommended_daily_kcal"] = recommended_daily

        st.write(f"Current maintenance calories: **{plan['current_needs_kcal']} kcal/day**")
        st.write(f"Recommended daily calories: **{plan['recommended_daily_kcal']} kcal/day**")
        st.write(f"Expected weekly change: **{kg_per_week:+.2f} kg/week**")
        if plan.get("warning"):
            st.warning(plan["warning"])
        st.table(plan.get("milestones", []))

    # ── PDF ───────────────────────────────────────────────────────────────────
    st.markdown("---")
    report = {
        "generated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "inputs": {"age": age, "sex": sex, "height_cm": height_cm, "weight_kg": weight_kg},
        "bmi": results.get("bmi"),
        "bodyfat": results.get("bodyfat"),
        "whr": results.get("whr"),
        "vo2": results.get("vo2"),
        "bio_age": results.get("bio_age"),
        "bio_factors": results.get("bio_factors"),
        "triage": results.get("triage"),
        "triage_recommendations": results.get("triage_recommendations"),
        "plan": results.get("plan"),
        "exercise_log": st.session_state.get("exercise_last"),
    }
    try:
        pdf_bytes = create_pdf_bytes(report)
        st.download_button(
            "📄 Download PDF report",
            data=pdf_bytes,
            file_name="health_tools_report.pdf",
            mime="application/pdf",
            key="pdf_btn",
        )
    except Exception as e:
        st.warning(f"PDF generation unavailable: {e}")

else:
    st.info("Trykk på 'Calculate / Generate report' for å kjøre beregningene.")
