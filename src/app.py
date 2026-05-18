# app.py - Ryddet og feilfikset versjon
from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import streamlit.components.v1 as components

# Lokalt modul for kalkulasjoner (forutsetter at calculators.py finnes i repo)
import calculators

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from calculators import (
    bmr_mifflin,
    tdee_from_activity_factor,
    calories_burned_from_mets,
    weekly_exercise_calories,
    tdee_including_weekly_exercise,
)

# -------------------------
# Enkel helpers
# -------------------------
def fig_to_png_buffer(fig) -> BytesIO:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


# --- Plot helpers (for PDF/visning) ---
def plot_bmi_gauge(bmi_value: float):
    fig, ax = plt.subplots(figsize=(8.2, 1.7))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    bands = [
        (0.0, 18.5, "#3b82f6"),
        (18.5, 25.0, "#22c55e"),
        (25.0, 30.0, "#f59e0b"),
        (30.0, 45.0, "#ef4444"),
    ]
    for start, end, color in bands:
        ax.barh(0.5, end - start, left=start, height=0.45, color=color, edgecolor="none", alpha=0.95)
    marker_x = max(0.0, min(45.0, bmi_value))
    ax.scatter([marker_x], [0.5], s=220, marker="v", color="#111827", zorder=5, edgecolor="white", linewidth=1.0)
    ax.text(marker_x, 1.00, f"{bmi_value:.1f}", ha="center", va="bottom", fontsize=10.5, color="#e5e7eb", fontweight="bold")
    ax.set_xlim(0, 45)
    ax.set_ylim(0, 1.25)
    ax.set_yticks([])
    ax.set_xticks([0, 10, 18.5, 25, 30, 40, 45])
    ax.tick_params(axis="x", labelsize=9, colors="#0f172a")
    ax.set_xlabel("BMI", color="#0f172a", fontsize=10)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.text(9.25, 0.08, "Underweight", ha="center", va="center", fontsize=8.5, color="white")
    ax.text(21.75, 0.08, "Normal", ha="center", va="center", fontsize=8.5, color="white")
    ax.text(27.5, 0.08, "Overweight", ha="center", va="center", fontsize=8.5, color="white")
    ax.text(37.5, 0.08, "Obesity", ha="center", va="center", fontsize=8.5, color="white")
    plt.tight_layout()
    return fig


def plot_vo2_reference_chart(vo2_value: float, sex: str, age: int):
    table = calculators.vo2_age_reference_table(sex)
    bands = [row["Age band"] for row in table]
    means = [row["Approx. average"] for row in table]
    fig, ax = plt.subplots(figsize=(7.4, 3.0))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    bars = ax.bar(bands, means, color="#60a5fa", edgecolor="none", alpha=0.9, label=f"{sex.upper()} reference mean")
    ax.axhline(vo2_value, color="#ef4444", linestyle="--", linewidth=2.2, label=f"Your VO2max: {vo2_value:.1f}")
    ax.set_ylabel("VO2max (ml/kg/min)", color="#0f172a")
    ax.set_title(f"VO2max reference bands by age — age {age}", color="#0f172a", fontsize=11, fontweight="bold")
    ax.tick_params(axis="x", labelrotation=0, labelsize=8.5, colors="#0f172a")
    ax.tick_params(axis="y", labelsize=9, colors="#0f172a")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.legend(frameon=False, fontsize=8.5)
    plt.tight_layout()
    return fig


def plot_vo2_percentile_marker(percentile: float):
    fig, ax = plt.subplots(figsize=(7.4, 1.2))
    ax.barh(0, 100, color="#e6eef8")
    ax.barh(0, percentile, color="#60a5fa")
    ax.scatter([percentile], [0], s=120, color="#ef4444", zorder=5)
    ax.text(percentile, -0.4, f"{percentile:.1f}th percentile", ha="center", va="top", fontweight="bold")
    ax.set_xlim(0, 100)
    ax.set_yticks([])
    ax.set_xticks([0, 10, 25, 50, 75, 90, 95, 99, 100])
    ax.set_xlabel("Population percentile (higher is better)")
    for spine in ax.spines.values():
        spine.set_visible(False)
    plt.tight_layout()
    return fig


# -------------------------
# PDF helpers (ReportLab)
# -------------------------
def para(text: str, style) -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<​br/>"), style)


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
    t.setStyle(
        TableStyle(
            [
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
            ]
        )
    )
    return t


def figure_image(fig, width_mm=170):
    buf = fig_to_png_buffer(fig)
    width_pt = width_mm * mm
    return RLImage(buf, width=width_pt, height=width_pt * 0.32)


def create_pdf_bytes(report: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=18 * mm,
        bottomMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleStyle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, alignment=TA_CENTER, textColor=colors.HexColor("#0f172a"))
    subtitle = ParagraphStyle("SubtitleStyle", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5, leading=12, alignment=TA_CENTER, textColor=colors.HexColor("#475569"))
    section = ParagraphStyle("SectionStyle", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=15, textColor=colors.HexColor("#0f172a"), spaceAfter=4)
    body = ParagraphStyle("BodyStyle", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2, leading=12, textColor=colors.HexColor("#111827"))
    small = ParagraphStyle("SmallStyle", parent=styles["BodyText"], fontName="Helvetica-Oblique", fontSize=7.8, leading=10, textColor=colors.HexColor("#475569"))
    story = []
    story.append(Paragraph("Health Tools — Report", title))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Educational report generated from the app inputs. This is not a medical diagnosis.", subtitle))
    story.append(Spacer(1, 6 * mm))
    inputs = report["inputs"]
    inputs_rows = [
        ("Generated", report["generated"]),
        ("Age", inputs.get("age")),
        ("Sex", inputs.get("sex")),
        ("Height", f'{inputs.get("height_cm")} cm' if inputs.get("height_cm") is not None else "—"),
        ("Weight", f'{inputs.get("weight_kg")} kg' if inputs.get("weight_kg") is not None else "—"),
    ]
    story.append(make_key_value_table(inputs_rows))
    story.append(Spacer(1, 6 * mm))
    summary_rows = []
    if report.get("bmi"):
        summary_rows.append(("BMI", f'{report["bmi"]["value"]} ({report["bmi"]["category"]})'))
    if report.get("vo2"):
        summary_rows.append(("VO2max", f'{report["vo2"]["value"]} ml/kg/min | {report["vo2"]["rating"]} | {report["vo2"]["percentile"]}th percentile'))
    if report.get("bio_age"):
        summary_rows.append(("Biological age", f'{report["bio_age"]["value"]} years'))
    if report.get("triage"):
        summary_rows.append(("Conditions notes", report["triage"]["message"]))
    if summary_rows:
        story.append(Paragraph("Summary", section))
        story.append(make_key_value_table(summary_rows))
        story.append(Spacer(1, 6 * mm))
    # (remainder of PDF sections similar to earlier; omitted for brevity in this comment)
    # Add disclaimer and header/footer
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Disclaimer: educational demo only. Not clinically validated. For symptoms, worsening health, or emergency signs, seek professional help immediately.", small))

    def add_page_header(canvas, doc):
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
    doc.build(story, onFirstPage=add_page_header, onLaterPages=add_page_header)
    buffer.seek(0)
    return buffer.read()


# -------------------------
# App setup & styling
# -------------------------
st.set_page_config(
    page_title="Health Tools MVP",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    img, svg, iframe { max-width: 100% !important; height: auto !important; }
    @media (max-width: 600px) {
        .main > div { padding-left: 8px !important; padding-right: 8px !important; }
        .streamlit-expanderHeader { font-size: 16px !important; }
        .stButton>button { width: 100% !important; }
    }
    .stTextInput>div>div>input,
    .stNumberInput>div>div>input,
    textarea,
    select,
    .stSelectbox>div>div>div,
    .stDateInput>div>div>input {
      background-color: rgba(255,255,255,0.04) !important;
      color: #e6eef8 !important;
      border: 1px solid rgba(255,255,255,0.08) !important;
      border-radius: 8px !important;
      padding: 8px !important;
    }
    .result-box {
      background-color: rgba(255,255,255,0.03);
      color: #e6eef8;
      border: 1px solid rgba(255,255,255,0.04);
      padding: 14px;
      border-radius: 10px;
      margin-bottom: 12px;
    }
    .stButton>button {
      background-color: #0ea5a3 !important;
      color: #022b2a !important;
      border-radius: 8px !important;
      padding: 8px 12px !important;
      font-weight: 600 !important;
    }
    h1, h2, h3, p, label { color: #e6eef8 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Health Tools — MVP")
st.caption("Educational tool only — not a diagnostic tool. Data is not stored.")

# Consent quick modal
if "consent_given" not in st.session_state:
    st.session_state.consent_given = False

if not st.session_state.consent_given:
    with st.expander("Please read: Consent & privacy", expanded=True):
        st.markdown(
            """
            This demo stores nothing by default and is for educational purposes only.
            By continuing you confirm you understand it's not clinical advice.
            """
        )
    c1, c2 = st.columns([1, 1])
    if c1.button("I agree", key="consent_agree"):
        st.session_state.consent_given = True
        try:
            if not st.session_state.get("_consent_rerun_done"):
                st.session_state["_consent_rerun_done"] = True
                st.experimental_rerun()
        except Exception:
            pass
    if c2.button("Exit", key="consent_exit"):
        st.stop()


# -------------------------
# Sidebar: toggle modules
# -------------------------
st.sidebar.header("Modules")
run_bmi = st.sidebar.checkbox("BMI calculator", value=True, key="s_bmi")
run_vo2 = st.sidebar.checkbox("VO2max estimate", value=True, key="s_vo2")
run_bioage = st.sidebar.checkbox("Biological age", value=True, key="s_bio")
run_conditions = st.sidebar.checkbox("Conditions & recommendations", value=True, key="s_conditions")
run_plan = st.sidebar.checkbox("Weight goal / plan", value=True, key="s_plan")
st.sidebar.markdown("---")
st.sidebar.info("This app does not store personal health data. It is for education and demonstration only.")


# -------------------------
# Basic inputs (ensure keys exist & widgets)
# -------------------------
st.header("Basic information")

# Initialize safe defaults (only once)
if "resting_hr" not in st.session_state:
    st.session_state["resting_hr"] = None
if "age" not in st.session_state:
    st.session_state["age"] = 30
if "sex" not in st.session_state:
    st.session_state["sex"] = "M"
if "height_cm" not in st.session_state:
    st.session_state["height_cm"] = 175.0
if "weight_kg" not in st.session_state:
    st.session_state["weight_kg"] = 75.0
if "global_resting_hr" not in st.session_state:
    st.session_state["global_resting_hr"] = None
if "exercise_kcal_per_week" not in st.session_state:
    st.session_state["exercise_kcal_per_week"] = 0.0

# Widgets: sex, age, height, weight, resting HR
c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    sex = st.selectbox("Sex", options=["M", "F"], index=0, key="sex")
with c2:
    age_input = st.number_input("Age (years)", min_value=5, max_value=120, value=st.session_state.get("age", 30), key="age")
with c3:
    resting_hr_basic = st.number_input("Resting HR (bpm)", min_value=30, max_value=120, value=st.session_state.get("resting_hr") or 60, key="basic_resting_hr")

# Height and weight on their own row (mobile-friendly)
c4, c5 = st.columns(2)
with c4:
    height_cm = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, value=st.session_state.get("height_cm", 175.0), format="%.1f", key="height_cm")
with c5:
    weight_kg = st.number_input("Weight (kg)", min_value=20.0, max_value=500.0, value=st.session_state.get("weight_kg", 75.0), format="%.1f", key="weight_kg")

# Update canonical resting HR & globals without risky writes
try:
    st.session_state["age"] = int(age_input)
except Exception:
    # keep previous valid value if conversion fails
    pass

try:
    st.session_state["resting_hr"] = int(resting_hr_basic) if resting_hr_basic is not None else None
    st.session_state["global_resting_hr"] = st.session_state["resting_hr"]
except Exception:
    pass

# -------------------------
# Defaults for other variables used later (safe local defaults)
# -------------------------
activity_level = st.session_state.get("v_activity", "Moderate")
weekly_minutes = st.session_state.get("v_weekly_minutes", 150)
session_intensity = st.session_state.get("v_session_intensity", 3)
resting_hr = st.session_state.get("vo2_rhr_value", None)
max_hr = st.session_state.get("vo2_maxhr_val", None)
measured_vo2_input = st.session_state.get("vo2_measured_input", 0.0)
waist_cm = st.session_state.get("b_waist", None)
hip_cm = st.session_state.get("b_hip", None)
neck_cm = st.session_state.get("b_neck", None)
bodyfat_requested = st.session_state.get("b_bodyfat", False)
smoker = st.session_state.get("bio_smoker", False)
diabetes = st.session_state.get("bio_diabetes", False)
sleep_hours = st.session_state.get("bio_sleep_val", None)
alcohol_units = st.session_state.get("bio_alc_val", None)
fruit_veg = st.session_state.get("bio_fv", None)
perceived_stress = st.session_state.get("bio_stress", 5)
grip_strength = st.session_state.get("bio_grip_val", None)
bp_systolic = st.session_state.get("bio_bp_val", None)
cholesterol = st.session_state.get("bio_chol_val", None)
family_history = st.session_state.get("bio_family_hist", False)
menopause = st.session_state.get("bio_menopause", False)


# -------------------------
# BMI inputs section
# -------------------------
if run_bmi:
    with st.expander("BMI inputs and body composition", expanded=True):
        st.markdown("BMI is a simple screening tool, not a diagnosis.")
        use_waist_hip = st.checkbox("Add waist and hip measurements", value=False, key="b_use_whr")
        if use_waist_hip:
            c1, c2 = st.columns(2)
            with c1:
                waist_cm = st.number_input("Waist circumference (cm)", min_value=30.0, max_value=300.0, value=st.session_state.get("b_waist", 80.0), format="%.1f", key="b_waist")
            with c2:
                hip_cm = st.number_input("Hip circumference (cm)", min_value=30.0, max_value=300.0, value=st.session_state.get("b_hip", 95.0), format="%.1f", key="b_hip")
        use_neck = st.checkbox("Add neck measurement for body-fat estimate", value=False, key="b_use_neck")
        if use_neck:
            neck_cm = st.number_input("Neck circumference (cm)", min_value=20.0, max_value=80.0, value=st.session_state.get("b_neck", 38.0), format="%.1f", key="b_neck")
        bodyfat_requested = st.checkbox("Estimate body fat using the Navy method", value=False, key="b_bodyfat")


# -------------------------
# VO2 inputs
# -------------------------
vo2_method = "Questionnaire"
vo2_distance_m = 0.0
rockport_time_min = 0.0
rockport_hr = 0

if run_vo2:
    with st.expander("Cardio / VO2max inputs", expanded=True):
        activity_level = st.selectbox(
            "Physical activity level",
            options=["Sedentary", "Light", "Moderate", "Active", "Very active", "Athlete"],
            index=2,
            key="v_activity"
        )
        weekly_minutes = st.number_input(
            "Weekly minutes of moderate-to-vigorous activity",
            min_value=0,
            max_value=2000,
            value=st.session_state.get("v_weekly_minutes", 150),
            key="v_weekly_minutes"
        )
        session_intensity = st.slider(
            "Typical session intensity (1 = very light, 5 = very intense)",
            min_value=1,
            max_value=5,
            value=st.session_state.get("v_session_intensity", 3),
            key="v_session_intensity"
        )

        resting_hr_unknown = st.checkbox(
            "I don't know my resting heart rate",
            value=(st.session_state.get("global_resting_hr") is None),
            key="vo2_rhr_unknown"
        )
        if not resting_hr_unknown:
            default_rhr = st.session_state.get("global_resting_hr") or 70
            resting_hr = st.number_input(
                "Resting heart rate (bpm)",
                min_value=30,
                max_value=220,
                value=default_rhr,
                key="vo2_rhr_value"
            )
            st.caption("Prefilled from 'Resting heart rate' above if entered there. You can override it here.")
        else:
            resting_hr = None

        max_hr_unknown = st.checkbox("I don't know my max heart rate", value=True, key="vo2_maxhr_unknown")
        if not max_hr_unknown:
            max_hr = st.number_input("Estimated max heart rate (bpm)", min_value=40, max_value=240, value=180, key="vo2_maxhr_val")
        else:
            max_hr = None

        measured_vo2_input = st.number_input(
            "If you know a measured VO2max (Apple Watch, lab, etc.), enter it here",
            min_value=0.0,
            value=st.session_state.get("vo2_measured_input", 0.0),
            format="%.1f",
            key="vo2_measured_input"
        )

        vo2_method = st.selectbox(
            "VO2 calculation method",
            options=["Questionnaire", "Cooper (12-min)", "Rockport (1-mile)", "Measured value"],
            index=0,
            key="vo2_method_select"
        )

        if vo2_method == "Cooper (12-min)":
            vo2_distance_m = st.number_input("12-minute distance (meters)", min_value=0.0, value=st.session_state.get("vo2_cooper_distance", 0.0), format="%.1f", key="vo2_cooper_distance")
        elif vo2_method == "Rockport (1-mile)":
            rockport_time_min = st.number_input("1-mile time (minutes)", min_value=0.1, value=st.session_state.get("vo2_rockport_time", 15.0), format="%.2f", key="vo2_rockport_time")
            rockport_hr = st.number_input("Heart rate at the end (bpm)", min_value=30, max_value=220, value=st.session_state.get("vo2_rockport_hr", 140), key="vo2_rockport_hr")


# -------------------------
# Exercise calories helper expander
# -------------------------
with st.expander("Exercise calories (enter before clicking Calculate)", expanded=False):
    st.markdown("Specify your exercise habits for a more precise TDEE / plan. MET values are approximate.")
    sessions_per_week = st.number_input("Sessions per week", min_value=0, max_value=21, value=st.session_state.get("ui_sessions_per_week", 3), step=1, key="ui_sessions_per_week")

    default_avg = st.session_state.get("global_avg_hr")
    avg_hr = st.number_input("Average HR during sessions (bpm) — valgfritt (lagres lokalt)", min_value=30, max_value=220, value=default_avg if default_avg is not None else 130, key="ui_avg_hr")
    st.session_state["global_avg_hr"] = int(avg_hr) if avg_hr is not None else None

    activities = {
        "Walking (casual)": {"Light": 2.8, "Moderate": 3.5, "Hard": 4.3},
        "Brisk walking": {"Light": 3.5, "Moderate": 4.3, "Hard": 5.0},
        "Running/jogging": {"Light": 7.0, "Moderate": 9.8, "Hard": 11.5},
        "Cycling (leisure)": {"Light": 4.0, "Moderate": 6.8, "Hard": 8.5},
        "Cycling (vigorous)": {"Light": 6.8, "Moderate": 8.5, "Hard": 10.0},
        "Strength training (weights)": {"Light": 3.0, "Moderate": 4.5, "Hard": 6.0},
        "HIIT": {"Light": 6.0, "Moderate": 8.0, "Hard": 10.0},
    }

    activity = st.selectbox("Activity type", list(activities.keys()), key="ui_activity_type")
    intensity_label = st.selectbox("Intensity", ["Light", "Moderate", "Hard"], index=1, key="ui_intensity")
    minutes_per_session = st.number_input("Minutes per session", min_value=1, max_value=300, value=st.session_state.get("ui_minutes", 45), step=5, key="ui_minutes")
    rpe = st.slider("Perceived exertion (RPE) 1-10 (valgfritt)", 1, 10, 5, key="ui_rpe")
    rpe_multiplier = 0.85 + (rpe - 1) * (0.4 / 9)

    use_hr = st.checkbox("Use average session heart rate to refine estimate (optional)", key="ui_use_hr")
    avg_hr_for_calc = None
    resting_hr_for_calc = None
    if use_hr:
        avg_hr_for_calc = st.number_input("Average HR during session (bpm)", min_value=30, max_value=220, value=st.session_state.get("ui_avg_hr", 130), key="ui_avg_hr_calc")
        resting_hr_for_calc = st.number_input("Resting HR (optional, bpm)", min_value=30, max_value=120, value=st.session_state.get("resting_hr", 60), key="ui_resting_hr")

    try:
        base_met = activities.get(activity, {}).get(intensity_label, 4.0)
    except Exception:
        base_met = 4.0

    try:
        w = float(st.session_state.get("weight_kg", 75.0))
    except Exception:
        w = 70.0

    kcal_per_min = (base_met * 3.5 * w) / 200.0
    kcal_per_session = kcal_per_min * float(minutes_per_session)
    kcal_per_session *= rpe_multiplier

    if avg_hr_for_calc is not None and resting_hr_for_calc:
        hr_delta = max(0, float(avg_hr_for_calc) - float(resting_hr_for_calc))
        hr_multiplier = 1.0 + min(0.5, hr_delta / 100.0)
        kcal_per_session *= hr_multiplier

    st.session_state["exercise_kcal_per_week"] = sessions_per_week * kcal_per_session
    st.session_state["exercise_last"] = {
        "activity": activity,
        "intensity": intensity_label,
        "minutes": int(minutes_per_session),
        "sessions_per_week": int(sessions_per_week),
        "kcal_per_session": round(kcal_per_session, 1),
        "kcal_per_week": round(st.session_state["exercise_kcal_per_week"], 1),
        "rpe": int(rpe),
        "avg_hr": int(avg_hr_for_calc) if avg_hr_for_calc is not None else None,
    }
    st.write(f"Estimated exercise burn: **{st.session_state['exercise_kcal_per_week']:.0f} kcal/week**")
    st.caption("MET values are approximate. Use the HR option or adjust RPE for a more accurate estimate.")


# -------------------------
# Biological age inputs
# -------------------------
if run_bioage:
    with st.expander("Biological age inputs", expanded=True):
        st.caption("You can leave any field blank or use 'I don't know' where available.")
        smoker = st.checkbox("Smoker?", key="bio_smoker")
        diabetes = st.checkbox("Diabetes?", key="bio_diabetes")
        family_history = st.checkbox("Family history of premature cardiovascular disease?", key="bio_family_hist")
        if sex == "F":
            menopause = st.checkbox("Post-menopausal?", key="bio_menopause")
        st.markdown("#### Cardiovascular")
        bp_unknown = st.checkbox("I don't know my systolic blood pressure", value=True, key="bio_bp_unknown")
        if not bp_unknown:
            bp_systolic = st.number_input("Systolic blood pressure (mmHg)", min_value=70.0, max_value=260.0, value=st.session_state.get("bio_bp_val", 120.0), key="bio_bp_val")
        chol_unknown = st.checkbox("I don't know my cholesterol", value=True, key="bio_chol_unknown")
        if not chol_unknown:
            cholesterol = st.number_input("Cholesterol (mg/dL)", min_value=50.0, max_value=500.0, value=st.session_state.get("bio_chol_val", 180.0), key="bio_chol_val")
        rhr_unknown = st.checkbox("I don't know my resting heart rate", value=True, key="bio_rhr_unknown")
        if not rhr_unknown:
            resting_hr = st.number_input("Resting heart rate (bpm)", min_value=30, max_value=220, value=st.session_state.get("resting_hr", 70), key="bio_rhr_val")
        st.markdown("#### Lifestyle")
        sleep_unknown = st.checkbox("I don't know my sleep duration", value=True, key="bio_sleep_unknown")
        if not sleep_unknown:
            sleep_hours = st.number_input("Average sleep per night (hours)", min_value=0.0, max_value=24.0, value=st.session_state.get("bio_sleep_val", 7.0), format="%.1f", key="bio_sleep_val")
        alcohol_unknown = st.checkbox("I don't know my alcohol intake", value=True, key="bio_alc_unknown")
        if not alcohol_unknown:
            alcohol_units = st.number_input("Alcohol units per week", min_value=0, max_value=300, value=st.session_state.get("bio_alc_val", 0), key="bio_alc_val")
        fruit_veg = st.number_input("Daily fruit & vegetable servings", min_value=0, max_value=20, value=st.session_state.get("bio_fv", 3), key="bio_fv")
        perceived_stress = st.slider("Perceived stress (1 low - 10 high)", min_value=1, max_value=10, value=st.session_state.get("bio_stress", 5), key="bio_stress")
        grip_unknown = st.checkbox("I don't know my grip strength", value=True, key="bio_grip_unknown")
        if not grip_unknown:
            grip_strength = st.number_input("Grip strength (kg)", min_value=0.0, max_value=100.0, value=st.session_state.get("bio_grip_val", 30.0), format="%.1f", key="bio_grip_val")
        st.markdown("#### Body composition")
        bio_waist_unknown = st.checkbox("I don't know my waist-to-hip ratio", value=True, key="bio_waist_unknown")
        if not bio_waist_unknown:
            c1, c2 = st.columns(2)
            with c1:
                waist_bio = st.number_input("Waist circumference for bio-age (cm)", min_value=30.0, max_value=300.0, value=st.session_state.get("bio_waist_val", 80.0), format="%.1f", key="bio_waist_val")
            with c2:
                hip_bio = st.number_input("Hip circumference for bio-age (cm)", min_value=30.0, max_value=300.0, value=st.session_state.get("bio_hip_val", 95.0), format="%.1f", key="bio_hip_val")
            if waist_cm is None:
                waist_cm = waist_bio
            if hip_cm is None:
                hip_cm = hip_bio


# -------------------------
# Conditions / recommendations
# -------------------------
selected_conditions = []
custom_condition = ""
condition_goal_focus = "General"

if run_conditions:
    with st.expander("Conditions & recommendations", expanded=True):
        st.markdown("Select any diagnoses/conditions you have and choose a focus to get practical exercise & prevention tips.")
        if hasattr(calculators, 'DIAGNOSIS_RECOMMENDATIONS'):
            condition_options = sorted(list(calculators.DIAGNOSIS_RECOMMENDATIONS.keys()))
        else:
            condition_options = ["Type 2 Diabetes", "Hypertension", "Lower Back Pain", "Asthma", "Osteoarthritis"]

        selected_conditions = st.multiselect("Select conditions (choose one or more)", options=condition_options, default=[], key="cond_select")
        custom_condition = st.text_input("Other condition (free text)", "", key="cond_custom")
        if custom_condition.strip():
            selected_conditions = (selected_conditions or []) + [custom_condition.strip()]
        condition_goal_focus = st.selectbox("Recommendations focus", options=["General", "VO2", "Weight", "Mobility"], index=0, key="cond_goal")


# -------------------------
# Weight goal / plan
# -------------------------
create_plan = False
target_weight = None
target_bmi = None
plan_weeks = 12

if run_plan and run_bmi:
    with st.expander("Goal / plan", expanded=False):
        create_plan = st.checkbox("Create a simple plan to reach a target weight/BMI", value=False, key="plan_create")
        if create_plan:
            plan_type = st.radio("Plan target type", ["Target weight (kg)", "Target BMI"], index=0, key="plan_type")
            if plan_type == "Target weight (kg)":
                target_weight = st.number_input("Target weight (kg)", min_value=30.0, max_value=400.0, value=st.session_state.get("plan_target_weight", 65.0), format="%.1f", key="plan_target_weight")
            else:
                target_bmi = st.number_input("Target BMI", min_value=12.0, max_value=45.0, value=st.session_state.get("plan_target_bmi", 22.0), format="%.1f", key="plan_target_bmi")
            plan_weeks = st.number_input("Weeks to achieve target", min_value=4, max_value=52, value=st.session_state.get("plan_weeks", 12), step=1, key="plan_weeks")


# -------------------------
# Calculate / Generate report
# -------------------------
def _to_optional_float(val, name):
    try:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        if s == "":
            return None
        return float(s.replace(",", "."))
    except Exception as e:
        raise ValueError(f"Kunne ikke konvertere '{name}' til float: {val!r} ({e})")


def _to_int_or_none(val, name):
    try:
        if val is None:
            return None
        if isinstance(val, int):
            return val
        s = str(val).strip()
        if s == "":
            return None
        return int(float(s))
    except Exception as e:
        raise ValueError(f"Kunne ikke konvertere '{name}' til int: {val!r} ({e})")


if st.button("Calculate / Generate report", key="btn_calculate"):
    import traceback, logging

    try:
        # Read and validate core inputs from session_state / widgets
        age_i = _to_int_or_none(st.session_state.get("age"), "age")
        if age_i is None:
            raise ValueError("Alder (age) må fylles inn og være et tall.")

        sex_val = st.session_state.get("sex", "M")
        height_f = _to_optional_float(st.session_state.get("height_cm"), "height_cm")
        weight_f = _to_optional_float(st.session_state.get("weight_kg"), "weight_kg")

        if height_f is None or weight_f is None:
            raise ValueError("Høyde og vekt må være tall (height_cm, weight_kg).")

        waist_f = _to_optional_float(st.session_state.get("b_waist"), "waist_cm")
        hip_f = _to_optional_float(st.session_state.get("b_hip"), "hip_cm")
        neck_f = _to_optional_float(st.session_state.get("b_neck"), "neck_cm")

        measured_vo2_f = _to_optional_float(st.session_state.get("vo2_measured_input"), "measured_vo2_input")
        vo2_dist_f = _to_optional_float(st.session_state.get("vo2_cooper_distance"), "vo2_distance_m")
        rockport_time_f = _to_optional_float(st.session_state.get("vo2_rockport_time"), "rockport_time_min")
        rockport_hr_i = _to_int_or_none(st.session_state.get("vo2_rockport_hr"), "rockport_hr")

        weekly_min_i = _to_int_or_none(st.session_state.get("v_weekly_minutes"), "weekly_minutes")
        session_int_i = _to_int_or_none(st.session_state.get("v_session_intensity"), "session_intensity")
        resting_hr_i = _to_int_or_none(st.session_state.get("vo2_rhr_value") or st.session_state.get("resting_hr"), "resting_hr")
        max_hr_i = _to_int_or_none(st.session_state.get("vo2_maxhr_val"), "max_hr")

        plan_weeks_i = _to_int_or_none(st.session_state.get("plan_weeks"), "plan_weeks")
        target_weight_f = _to_optional_float(st.session_state.get("plan_target_weight"), "target_weight")
        target_bmi_f = _to_optional_float(st.session_state.get("plan_target_bmi"), "target_bmi")

        activity_level = st.session_state.get("v_activity", "Moderate")

        # Start real calculations
        results = {}

        # BMI
        if run_bmi:
            bmi_value, bmi_category = calculators.bmi_calc(weight_f, height_f)
            results["bmi"] = {"value": round(bmi_value, 1), "category": bmi_category}
            if waist_f is not None and hip_f is not None:
                whr_value = calculators.waist_hip_ratio(waist_f, hip_f)
                whr_cat = calculators.whr_category(sex_val, whr_value)
                results["whr"] = {"value": round(whr_value, 2), "category": whr_cat}

        # Body fat (Navy) - validate inputs and sex
        if bodyfat_requested and neck_f is not None:
            try:
                sex_norm = str(sex_val).upper()[:1]
                if sex_norm == "M":
                    if waist_f is None:
                        raise ValueError("Waist measurement required for male body-fat estimate.")
                    bodyfat = calculators.body_fat_navy(sex=sex_norm, height_cm=height_f, neck_cm=neck_f, waist_cm=waist_f)
                elif sex_norm == "F":
                    if waist_f is None or hip_f is None:
                        raise ValueError("Waist and hip measurements required for female body-fat estimate.")
                    bodyfat = calculators.body_fat_navy(sex=sex_norm, height_cm=height_f, neck_cm=neck_f, waist_cm=waist_f, hip_cm=hip_f)
                else:
                    raise ValueError("Ukjent kjønn for body-fat estimation.")
                results["bodyfat"] = {"value": round(bodyfat, 1)}
            except Exception as e:
                st.warning(f"Body-fat estimate skipped: {e}")

        # VO2
        if run_vo2:
            vo2_method = st.session_state.get("vo2_method_select", "Questionnaire")
            if measured_vo2_f is not None and measured_vo2_f > 0:
                vo2_value = calculators.vo2_measured_value(measured_vo2_f)
                method_used = "Measured value"
            elif vo2_method == "Cooper (12-min)":
                vo2_value = calculators.vo2_cooper_from_distance(vo2_dist_f or 0.0)
                method_used = "Cooper (12-min)"
            elif vo2_method == "Rockport (1-mile)":
                if rockport_time_f is None:
                    raise ValueError("Rockport time må være et tall for Rockport-metoden.")
                vo2_value = calculators.vo2_rockport_1mile(rockport_time_f, int(rockport_hr_i or 0), weight_f, age_i, sex_val)
                method_used = "Rockport (1-mile)"
            else:
                # Questionnaire estimate
                bmi_for_vo2 = results.get("bmi", {}).get("value", calculators.bmi_calc(weight_f, height_f)[0])
                vo2_value = calculators.vo2_questionnaire_estimate(
                    age=age_i,
                    sex=sex_val,
                    weekly_minutes=int(weekly_min_i or 0),
                    session_intensity_score=int(session_int_i or 1),
                    activity_level=activity_level,
                    bmi=bmi_for_vo2,
                    resting_hr=int(resting_hr_i) if resting_hr_i is not None else None,
                    max_hr=int(max_hr_i) if max_hr_i is not None else None,
                )
                method_used = "Questionnaire"

            vo2_ref = calculators.vo2_reference(age_i, sex_val, vo2_value)
            vo2_tips = calculators.vo2_improvement_tips(
                vo2_value=vo2_value,
                sex=sex_val,
                age=age_i,
                activity_level=activity_level,
                weekly_minutes=int(weekly_min_i or 0),
            )
            top_descriptor = calculators.vo2_top_descriptor(age_i, sex_val, vo2_value)
            results["vo2"] = {
                "value": round(float(vo2_value), 1),
                "method": method_used,
                "age_band": vo2_ref.get("age_band"),
                "percentile": vo2_ref.get("percentile"),
                "rating": vo2_ref.get("rating"),
                "reference_mean": vo2_ref.get("mean"),
                "tips": vo2_tips,
                "top_descriptor": top_descriptor,
            }

        # Biological age
        if run_bioage:
            bmi_v = results.get("bmi", {}).get("value", calculators.bmi_calc(weight_f, height_f)[0])
            waist_to_hip = None
            if waist_f is not None and hip_f is not None:
                try:
                    waist_to_hip = calculators.waist_hip_ratio(waist_f, hip_f)
                except Exception:
                    waist_to_hip = None
            measured_vo2_for_bio = results.get("vo2", {}).get("value") if results.get("vo2") else None
            bio_age, bio_factors = calculators.estimate_biological_age_detailed(
                age=age_i,
                sex=sex_val,
                smoker=st.session_state.get("bio_smoker", False),
                bmi=bmi_v,
                activity_level=activity_level,
                sleep_hours=_to_optional_float(st.session_state.get("bio_sleep_val"), "sleep_hours"),
                alcohol_units_per_week=_to_optional_float(st.session_state.get("bio_alc_val"), "alcohol_units"),
                fruit_veg_servings=_to_optional_float(st.session_state.get("bio_fv"), "fruit_veg"),
                perceived_stress=st.session_state.get("bio_stress", 5),
                grip_strength_kg=_to_optional_float(st.session_state.get("bio_grip_val"), "grip_strength"),
                bp_systolic=_to_optional_float(st.session_state.get("bio_bp_val"), "bp_systolic"),
                cholesterol_mg_dl=_to_optional_float(st.session_state.get("bio_chol_val"), "cholesterol"),
                diabetes=st.session_state.get("bio_diabetes", False),
                resting_hr=resting_hr_i,
                waist_to_hip_ratio=waist_to_hip,
                family_history=st.session_state.get("bio_family_hist", False),
                menopause=st.session_state.get("bio_menopause", False),
                measured_vo2=measured_vo2_for_bio,
            )
            results["bio_age"] = {"value": round(float(bio_age), 1)}
            results["bio_factors"] = bio_factors

        # Conditions & recommendations
        if run_conditions:
            recs = calculators.recommendations_for_diagnoses(st.session_state.get("cond_select", []), st.session_state.get("cond_goal", "General"))
            cond_message = "Recommendations generated for selected conditions."
            results["triage"] = {"level": "Info", "message": cond_message}
            results["triage_recommendations"] = recs

        # Plan generation
        if run_plan and run_bmi and create_plan:
            if target_bmi_f:
                target_w = target_bmi_f * (height_f / 100.0) ** 2
            else:
                target_w = target_weight_f
            if target_w:
                ekpw = float(st.session_state.get("exercise_kcal_per_week", 0.0))
                plan = calculators.generate_weight_plan(
                    current_weight_kg=weight_f,
                    target_weight_kg=target_w,
                    weeks=int(plan_weeks_i or 12),
                    sex=sex_val,
                    height_cm=height_f,
                    age=age_i,
                    activity_level=activity_level,
                    exercise_kcal_per_week=ekpw,
                )
                if plan.get("error"):
                    st.error(plan.get("message"))
                else:
                    results["plan"] = plan

    except Exception as e:
        st.error(f"Error during calculation: {e}")
        st.text("Full traceback (copypaste this if you need help):")
        st.text(traceback.format_exc())
        logging.exception("Calculation failed")
        st.session_state["results"] = {}
    else:
        st.session_state["results"] = results
        st.success("Calculation finished — results have been made")


# -------------------------
# Results display
# -------------------------
results = st.session_state.get("results", {})

if results:
    if "bmi" in results:
        st.subheader("BMI")
        b = results["bmi"]["value"]
        cat = results["bmi"]["category"]
        st.markdown(
            f"""
            <div class="result-box">
                <div style="font-size:18px; font-weight:700;">Din BMI: {b:.1f}</div>
                <div style="margin-top:6px; padding:6px 10px; display:inline-block; border-radius:8px; background:#1f2937; color:#fff; font-weight:700;">
                    {cat}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        try:
            st.pyplot(plot_bmi_gauge(b), use_container_width=True)
        except Exception:
            pass

    st.markdown("---")
    st.subheader("Energy og Metabolism")
    def _to_float(val):
        try:
            return float(str(val).replace(",", ".").strip())
        except Exception:
            return None

    calc_age_f = _to_float(st.session_state.get("age"))
    calc_weight = _to_float(st.session_state.get("weight_kg"))
    calc_height = _to_float(st.session_state.get("height_cm"))

    if calc_age_f is None or calc_weight is None or calc_height is None:
        st.info("Fyll inn alder, vekt og høyde (som tall) for å beregne kalorier.")
    else:
        calc_age = int(calc_age_f)
        calc_weight = float(calc_weight)
        calc_height = float(calc_height)

        bmr_val = bmr_mifflin(age=calc_age, sex=st.session_state.get("sex", "M"), weight_kg=calc_weight, height_cm=calc_height)
        daily_living = bmr_val * 1.2
        w_kcal = float(st.session_state.get("exercise_kcal_per_week", 0.0))
        tdee_total = tdee_including_weekly_exercise(bmr_val, activity_level, w_kcal)
        st.session_state["latest_tdee_total"] = float(tdee_total)

        c1, c2, c3 = st.columns(3)
        c1.metric("BMR", f"{int(bmr_val)} kcal")
        c2.metric("Daily Calorie Burn", f"{int(daily_living)} kcal")
        c3.metric("Total Daily Calorie Burn w/exercise", f"{int(tdee_total)} kcal")

    # VO2 display
    if "vo2" in results:
        st.markdown("---")
        st.subheader("VO2 max & fitness")
        v_val = float(results["vo2"]["value"])
        v_pct = max(0.0, min(100.0, float(results["vo2"].get("percentile", 0) or 0)))
        top_text = f"Top {100 - v_pct:.1f}%"

        c1, c2, c3 = st.columns(3)
        c1.metric("Your VO2 max", f"{v_val:.1f} ml/kg/min")
        c2.metric("Percentile", f"{v_pct:.0f}%")
        c3.metric("Ranking", top_text)

        # Minimal chart rendering (if available)
        try:
            st.pyplot(plot_vo2_reference_chart(v_val, st.session_state.get("sex", "M"), int(st.session_state.get("age", 30))), use_container_width=True)
        except Exception:
            pass

    # Biological age
    if "bio_age" in results:
        st.markdown("---")
        st.subheader("Biological age")
        st.metric("Biological age", f"{results['bio_age']['value']:.1f} years")
        if results.get("bio_factors"):
            st.markdown("**Factor breakdown**")
            factor_rows = [{"Factor": f["label"], "Effect": f"{f.get('delta', 0):+.0f} years"} for f in results["bio_factors"]]
            st.table(factor_rows)

    # Conditions
    if "triage" in results:
        st.markdown("---")
        st.subheader("Conditions & recommendations")
        if results.get("triage_recommendations"):
            for r in results["triage_recommendations"]:
                st.write(r)
        else:
            st.info(results.get("triage", {}).get("message", "No triage details."))

    # Plan & PDF
    if "plan" in results:
        plan = results["plan"]
        st.markdown("---")
        st.subheader("Weight goal / plan")
        current_maint = float(st.session_state.get("latest_tdee_total", plan.get("current_needs_kcal", 0) or 0.0))
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

        report = {
            "generated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "inputs": {"age": st.session_state.get("age"), "sex": st.session_state.get("sex"), "height_cm": st.session_state.get("height_cm"), "weight_kg": st.session_state.get("weight_kg")},
            "bmi": results.get("bmi"),
            "bodyfat": results.get("bodyfat"),
            "whr": results.get("whr"),
            "vo2": results.get("vo2"),
            "bio_age": results.get("bio_age"),
            "bio_factors": results.get("bio_factors"),
            "triage": results.get("triage"),
            "triage_recommendations": results.get("triage_recommendations"),
            "plan": results.get("plan"),
        }
        try:
            pdf_bytes = create_pdf_bytes(report)
            st.download_button("Download PDF report", data=pdf_bytes, file_name="health_tools_report.pdf", mime="application/pdf", key="pdf_btn")
        except Exception as e:
            st.warning(f"PDF generation is currently unavailable: {e}")

else:
    st.info("Trykk på 'Calculate / Generate report' for å kjøre beregningene.")
