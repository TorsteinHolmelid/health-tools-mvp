# app.py - Full replacement (fixed, preserves VO2 diagram + activity types + improved PDF)
from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO

import matplotlib.pyplot as plt
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

import calculators

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Optional: import specific helpers if you prefer
from calculators import (
    bmr_mifflin,
    tdee_from_activity_factor,
    calories_burned_from_mets,
    weekly_exercise_calories,
    tdee_including_weekly_exercise,
)

# Page config + styling
st.set_page_config(page_title="Health Tools MVP", layout="wide")
st.markdown(
    """
    <style>
    .block-container { max-width: 1400px; padding-left: 2rem; padding-right: 2rem; }
    @media (max-width: 820px) { .block-container { max-width: 100%; padding-left: 1rem; padding-right: 1rem; } }
    .stApp { background-color: #0b1220; color: #e6eef8; }
    [data-testid="stSidebar"] { background-color: #0b1220 !important; color: #e6eef8 !important; border-right: 1px solid rgba(255,255,255,0.03); padding: 18px; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, textarea, select, .stSelectbox>div>div>div, .stDateInput>div>div>input {
      background-color: rgba(255,255,255,0.04) !important; color: #e6eef8 !important;
      border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 8px !important; padding: 8px !important;
    }
    .stExpander > button { background-color: rgba(255,255,255,0.03) !important; color: #e6eef8 !important; border-radius: 8px !important; padding: 8px 12px !important; }
    .result-box { background-color: rgba(255,255,255,0.03); color: #e6eef8; border: 1px solid rgba(255,255,255,0.04); padding: 14px; border-radius: 10px; margin-bottom: 12px; }
    .stButton>button { background-color: #0ea5a3 !important; color: #022b2a !important; border-radius: 8px !important; padding: 8px 12px !important; font-weight: 600 !important; }
    .stButton>button:hover { filter: brightness(0.95); }
    h1, h2, h3, p, label { color: #e6eef8 !important; }
    .stTable td, .stTable th { color: #e6eef8 !important; }
    @media (max-width: 600px) { .stButton>button { width: 100% !important; } }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Health Tools — MVP")
st.caption("Educational tool only — not a diagnostic tool. Data is not stored by default.")

# Consent
if "consent_given" not in st.session_state:
    st.session_state.consent_given = False

if not st.session_state.consent_given:
    with st.expander("Please read: Consent & privacy", expanded=True):
        st.markdown("This demo stores nothing by default and is for educational purposes only. By continuing you confirm you understand it's not clinical advice.")
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

# --- Plot helpers ---
def fig_to_png_buffer(fig) -> BytesIO:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


def plot_bmi_gauge(bmi_value: float):
    fig, ax = plt.subplots(figsize=(8.2, 1.7))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    bands = [(0.0, 18.5, "#3b82f6"), (18.5, 25.0, "#22c55e"), (25.0, 30.0, "#f59e0b"), (30.0, 45.0, "#ef4444")]
    for start, end, color in bands:
        ax.barh(0.5, end - start, left=start, height=0.45, color=color, edgecolor="none", alpha=0.95)
    marker_x = max(0.0, min(45.0, bmi_value or 0.0))
    ax.scatter([marker_x], [0.5], s=220, marker="v", color="#111827", zorder=5, edgecolor="white", linewidth=1.0)
    ax.text(marker_x, 1.00, f"{marker_x:.1f}", ha="center", va="bottom", fontsize=10.5, color="#e5e7eb", fontweight="bold")
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
    ax.bar(bands, means, color="#60a5fa", edgecolor="none", alpha=0.9)
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


# --- PDF helpers (ReportLab) ---
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
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=18 * mm, bottomMargin=14 * mm)
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

    inputs = report.get("inputs", {})
    inputs_rows = [
        ("Generated", report.get("generated", "")),
        ("Age", inputs.get("age", "—")),
        ("Sex", inputs.get("sex", "—")),
        ("Height", f'{inputs.get("height_cm", "—")} cm'),
        ("Weight", f'{inputs.get("weight_kg", "—")} kg'),
    ]
    story.append(make_key_value_table(inputs_rows))
    story.append(Spacer(1, 6 * mm))

    summary_rows = []
    if report.get("bmi"):
        summary_rows.append(("BMI", f'{report["bmi"]["value"]} ({report["bmi"]["category"]})'))
    if report.get("vo2"):
        summary_rows.append(("VO2max", f'{report["vo2"]["value"]} ml/kg/min | {report["vo2"].get("rating","—")} | {report["vo2"].get("percentile","—")}th percentile'))
    if report.get("bio_age"):
        summary_rows.append(("Biological age", f'{report["bio_age"]["value"]} years'))
    if report.get("triage"):
        summary_rows.append(("Conditions notes", report["triage"].get("message", "—")))
    if summary_rows:
        story.append(Paragraph("Summary", section))
        story.append(make_key_value_table(summary_rows))
        story.append(Spacer(1, 6 * mm))

    # BMI section
    if report.get("bmi"):
        story.append(Paragraph("BMI", section))
        story.append(Paragraph("BMI is a simple screening measure. Body composition, muscle mass, bone structure, age, pregnancy and athletic status can change how BMI should be interpreted.", body))
        story.append(Spacer(1, 2 * mm))
        story.append(make_key_value_table([("BMI", f'{report["bmi"]["value"]}'), ("Category", report["bmi"]["category"])]))
        story.append(Spacer(1, 4 * mm))
        try:
            fig = plot_bmi_gauge(report["bmi"]["value"])
            story.append(figure_image(fig, width_mm=176))
            story.append(Spacer(1, 3 * mm))
        except Exception:
            pass

    # VO2 section
    if report.get("vo2"):
        story.append(Paragraph("VO2max", section))
        story.append(Paragraph("VO2max is estimated from your chosen method or entered directly if you already know a measured value.", body))
        story.append(Spacer(1, 2 * mm))
        story.append(make_key_value_table([("Method", report["vo2"].get("method","—")), ("VO2max", f'{report["vo2"]["value"]} ml/kg/min'), ("Age band", report["vo2"].get("age_band","—")), ("Percentile", f'{report["vo2"].get("percentile","—")}th'), ("Reference rating", report["vo2"].get("rating","—"))]))
        story.append(Spacer(1, 4 * mm))
        try:
            fig = plot_vo2_reference_chart(report["vo2"]["value"], inputs.get("sex","M"), int(inputs.get("age", 30)))
            story.append(figure_image(fig, width_mm=176))
            story.append(Spacer(1, 4 * mm))
        except Exception:
            pass
        tips = report["vo2"].get("tips", [])
        if tips:
            story.append(Paragraph("VO2 improvement tips", section))
            for tip in tips:
                story.append(Paragraph(f"• {escape(str(tip))}", body))
            story.append(Spacer(1, 4 * mm))

    # Biological age
    if report.get("bio_age"):
        story.append(Paragraph("Biological age", section))
        story.append(Paragraph("This is an educational estimate based on the inputs you provided. Missing values do not block the result.", body))
        story.append(Spacer(1, 2 * mm))
        bio_rows = [("Biological age", f'{report["bio_age"]["value"]} years')]
        story.append(make_key_value_table(bio_rows))
        story.append(Spacer(1, 3 * mm))
        if report.get("bio_factors"):
            factor_rows = [(f["label"], f'{f.get("delta",0):+.0f} years') for f in report["bio_factors"]]
            story.append(make_key_value_table(factor_rows, col_widths=(70*mm, 100*mm)))
            story.append(Spacer(1, 4 * mm))

    # Conditions / recommendations
    if report.get("triage"):
        story.append(Paragraph("Conditions & Recommendations", section))
        tri = report["triage"]
        story.append(make_key_value_table([("Note", tri.get("message","—"))]))
        story.append(Spacer(1, 4 * mm))
        recs = report.get("triage_recommendations", [])
        if recs:
            story.append(Paragraph("Recommendations", body))
            for r in recs:
                story.append(Paragraph(f"• {escape(str(r))}", body))
            story.append(Spacer(1, 4 * mm))

    # Plan
    if report.get("plan"):
        piano = report["plan"]
        if not piano.get("error"):
            story.append(Paragraph("Goal / plan", section))
            plan_rows = [("Current maintenance kcal", f'{piano.get("current_needs_kcal","—")} kcal/day'), ("Recommended daily kcal", f'{piano.get("recommended_daily_kcal","—")} kcal/day'), ("Expected weekly change", f'{piano.get("kg_per_week",0):+.2f} kg/week')]
            story.append(make_key_value_table(plan_rows))
            story.append(Spacer(1, 3 * mm))
            milestones = piano.get("milestones", [])
            if milestones:
                story.append(Paragraph("Milestones", body))
                story.append(Spacer(1, 2 * mm))
                story.append(make_key_value_table([(f"Week {m.get('Week')}", f"{m.get('Projected weight (kg)')} kg — {m.get('Focus')}") for m in milestones], col_widths=(50*mm,125*mm)))
                story.append(Spacer(1, 4 * mm))

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


# Sidebar modules
st.sidebar.header("Modules")
run_bmi = st.sidebar.checkbox("BMI calculator", value=True, key="s_bmi")
run_vo2 = st.sidebar.checkbox("VO2max estimate", value=True, key="s_vo2")
run_bioage = st.sidebar.checkbox("Biological age", value=True, key="s_bio")
run_conditions = st.sidebar.checkbox("Conditions & recommendations", value=True, key="s_conditions")
run_plan = st.sidebar.checkbox("Weight goal / plan", value=True, key="s_plan")
st.sidebar.markdown("---")
st.sidebar.info("This app does not store personal health data. It is for education and demonstration only.")

# --- Basic inputs (unique keys, mobile-friendly layout)
st.header("Basic information")
c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    age = st.number_input("Age (years)", min_value=0, max_value=120, value=30, step=1, key="inp_age")
with c2:
    sex = st.selectbox("Sex", options=["M", "F"], index=0, key="inp_sex")
with c3:
    resting_hr_top = st.number_input("Resting HR (bpm) — optional", min_value=30, max_value=220, value=70, key="inp_resting_hr")

c4, c5 = st.columns(2)
with c4:
    height_cm = st.number_input("Height (cm)", min_value=50, max_value=250, value=170, key="inp_height")
with c5:
    weight_kg = st.number_input("Weight (kg)", min_value=20.0, max_value=300.0, value=70.0, format="%.1f", key="inp_weight")

if age < 18:
    st.warning("BMI and fitness estimates are less reliable under 18.")
elif age >= 70:
    st.info("For older adults, BMI is often less informative because muscle mass and frailty matter.")

# Defaults (use session_state where helpful)
if "exercise_kcal_per_week" not in st.session_state:
    st.session_state["exercise_kcal_per_week"] = 0.0

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

# --- BMI inputs and body composition
if run_bmi:
    with st.expander("BMI inputs and body composition", expanded=True):
        st.markdown("BMI is a simple screening tool, not a diagnosis.")
        use_waist_hip = st.checkbox("Add waist and hip measurements", value=False, key="b_use_whr")
        if use_waist_hip:
            c1, c2 = st.columns(2)
            with c1:
                waist_cm = st.number_input("Waist circumference (cm)", min_value=30.0, max_value=300.0, value=80.0, format="%.1f", key="b_waist")
            with c2:
                hip_cm = st.number_input("Hip circumference (cm)", min_value=30.0, max_value=300.0, value=95.0, format="%.1f", key="b_hip")
        use_neck = st.checkbox("Add neck measurement for body-fat estimate", value=False, key="b_use_neck")
        if use_neck:
            neck_cm = st.number_input("Neck circumference (cm)", min_value=20.0, max_value=80.0, value=38.0, format="%.1f", key="b_neck")
        bodyfat_requested = st.checkbox("Estimate body fat using the Navy method", value=False, key="b_bodyfat")

# --- VO2 inputs (preserve activity types and options)
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
            key="v_activity",
        )
        weekly_minutes = st.number_input("Weekly minutes of moderate-to-vigorous activity", min_value=0, max_value=2000, value=150, key="v_weekly_minutes")
        session_intensity = st.slider("Typical session intensity (1 = very light, 5 = very intense)", min_value=1, max_value=5, value=3, key="v_session_intensity")

        resting_hr_unknown = st.checkbox("I don't know my resting heart rate", value=False, key="vo2_rhr_unknown")
        if not resting_hr_unknown:
            default_rhr = resting_hr_top or 70
            resting_hr = st.number_input("Resting heart rate (bpm)", min_value=30, max_value=220, value=default_rhr, key="vo2_rhr_value")
            st.caption("Prefilled from the top Resting HR if provided.")
        else:
            resting_hr = None

        max_hr_unknown = st.checkbox("I don't know my max heart rate", value=True, key="vo2_maxhr_unknown")
        if not max_hr_unknown:
            max_hr = st.number_input("Estimated max heart rate (bpm)", min_value=40, max_value=240, value=180, key="vo2_maxhr_val")
        else:
            max_hr = None

        measured_vo2_input = st.number_input("If you know a measured VO2max (ml/kg/min), enter it here", min_value=0.0, value=0.0, format="%.1f", key="vo2_measured_input")

        vo2_method = st.selectbox("VO2 calculation method", options=["Questionnaire", "Cooper (12-min)", "Rockport (1-mile)", "Measured value"], index=0, key="vo2_method_select")
        if vo2_method == "Cooper (12-min)":
            vo2_distance_m = st.number_input("12-minute distance (meters)", min_value=0.0, value=0.0, format="%.1f", key="vo2_cooper_distance")
        elif vo2_method == "Rockport (1-mile)":
            rockport_time_min = st.number_input("1-mile time (minutes)", min_value=0.1, value=15.0, format="%.2f", key="vo2_rockport_time")
            rockport_hr = st.number_input("Heart rate at the end (bpm)", min_value=30, max_value=220, value=140, key="vo2_rockport_hr")

# --- Biological age inputs
if run_bioage:
    with st.expander("Biological age inputs", expanded=True):
        st.caption("You can leave fields blank or choose 'I don't know'.")
        smoker = st.checkbox("Smoker?", key="bio_smoker")
        diabetes = st.checkbox("Diabetes?", key="bio_diabetes")
        family_history = st.checkbox("Family history of premature cardiovascular disease?", key="bio_family_hist")
        if sex == "F":
            menopause = st.checkbox("Post-menopausal?", key="bio_menopause")
        st.markdown("#### Cardiovascular")
        bp_unknown = st.checkbox("I don't know my systolic blood pressure", value=True, key="bio_bp_unknown")
        if not bp_unknown:
            bp_systolic = st.number_input("Systolic blood pressure (mmHg)", min_value=70.0, max_value=260.0, value=120.0, key="bio_bp_val")
        chol_unknown = st.checkbox("I don't know my cholesterol", value=True, key="bio_chol_unknown")
        if not chol_unknown:
            cholesterol = st.number_input("Cholesterol (mg/dL)", min_value=50.0, max_value=500.0, value=180.0, key="bio_chol_val")
        rhr_unknown = st.checkbox("I don't know my resting heart rate", value=True, key="bio_rhr_unknown")
        if not rhr_unknown:
            resting_hr = st.number_input("Resting heart rate (bpm)", min_value=30, max_value=220, value=resting_hr_top or 70, key="bio_rhr_val")
        st.markdown("#### Lifestyle")
        sleep_unknown = st.checkbox("I don't know my sleep duration", value=True, key="bio_sleep_unknown")
        if not sleep_unknown:
            sleep_hours = st.number_input("Average sleep per night (hours)", min_value=0.0, max_value=24.0, value=7.0, format="%.1f", key="bio_sleep_val")
        alcohol_unknown = st.checkbox("I don't know my alcohol intake", value=True, key="bio_alc_unknown")
        if not alcohol_unknown:
            alcohol_units = st.number_input("Alcohol units per week", min_value=0, max_value=300, value=0, key="bio_alc_val")
        fruit_veg = st.number_input("Daily fruit & vegetable servings", min_value=0, max_value=20, value=3, key="bio_fv")
        perceived_stress = st.slider("Perceived stress (1 low - 10 high)", min_value=1, max_value=10, value=5, key="bio_stress")
        grip_unknown = st.checkbox("I don't know my grip strength", value=True, key="bio_grip_unknown")
        if not grip_unknown:
            grip_strength = st.number_input("Grip strength (kg)", min_value=0.0, max_value=100.0, value=30.0, format="%.1f", key="bio_grip_val")
        st.markdown("#### Body composition")
        bio_waist_unknown = st.checkbox("I don't know my waist-to-hip ratio", value=True, key="bio_waist_unknown")
        if not bio_waist_unknown:
            c1, c2 = st.columns(2)
            with c1:
                waist_bio = st.number_input("Waist circumference for bio-age (cm)", min_value=30.0, max_value=300.0, value=80.0, format="%.1f", key="bio_waist_val")
            with c2:
                hip_bio = st.number_input("Hip circumference for bio-age (cm)", min_value=30.0, max_value=300.0, value=95.0, format="%.1f", key="bio_hip_val")
            if waist_cm is None:
                waist_cm = waist_bio
            if hip_cm is None:
                hip_cm = hip_bio

# --- Conditions / recommendations
selected_conditions = []
custom_condition = ""
condition_goal_focus = "General"
if run_conditions:
    with st.expander("Conditions & recommendations", expanded=True):
        st.markdown("Select diagnoses/conditions to get exercise & prevention tips.")
        if hasattr(calculators, 'DIAGNOSIS_RECOMMENDATIONS'):
            condition_options = sorted(list(calculators.DIAGNOSIS_RECOMMENDATIONS.keys()))
        else:
            condition_options = ["Type 2 Diabetes", "Hypertension", "Lower Back Pain", "Asthma", "Osteoarthritis"]
        selected_conditions = st.multiselect("Select conditions (choose one or more)", options=condition_options, default=[], key="cond_select")
        custom_condition = st.text_input("Other condition (free text)", "", key="cond_custom")
        if custom_condition.strip():
            selected_conditions = (selected_conditions or []) + [custom_condition.strip()]
        condition_goal_focus = st.selectbox("Recommendations focus", options=["General", "VO2", "Weight", "Mobility"], index=0, key="cond_goal")

# --- Weight goal / plan
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
                target_weight = st.number_input("Target weight (kg)", min_value=30.0, max_value=400.0, value=65.0, format="%.1f", key="plan_target_weight")
            else:
                target_bmi = st.number_input("Target BMI", min_value=12.0, max_value=45.0, value=22.0, format="%.1f", key="plan_target_bmi")
            plan_weeks = st.number_input("Weeks to achieve target", min_value=4, max_value=52, value=12, step=1, key="plan_weeks")

# Helper conversions with clear errors
def _to_optional_float(val):
    try:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        if s == "":
            return None
        return float(s.replace(",", "."))
    except Exception:
        return None


def _to_int_or_none(val):
    try:
        if val is None:
            return None
        if isinstance(val, int):
            return val
        s = str(val).strip()
        if s == "":
            return None
        return int(float(s))
    except Exception:
        return None


# --- Calculate / Generate report button handler
if st.button("Calculate / Generate report", key="btn_calculate"):
    results = {}
    try:
        # Validate core inputs
        age_i = _to_int_or_none(age)
        if age_i is None:
            raise ValueError("Alder må være et tall.")

        sex_val = str(sex).upper() if sex else "M"
        height_f = _to_optional_float(height_cm)
        weight_f = _to_optional_float(weight_kg)
        if height_f is None or weight_f is None:
            raise ValueError("Høyde og vekt må være tall.")

        waist_f = _to_optional_float(waist_cm)
        hip_f = _to_optional_float(hip_cm)
        neck_f = _to_optional_float(neck_cm)

        measured_vo2_f = _to_optional_float(st.session_state.get("vo2_measured_input") or measured_vo2_input)
        vo2_dist_f = _to_optional_float(st.session_state.get("vo2_cooper_distance") or vo2_distance_m)
        rockport_time_f = _to_optional_float(st.session_state.get("vo2_rockport_time") or rockport_time_min)
        rockport_hr_i = _to_int_or_none(st.session_state.get("vo2_rockport_hr") or rockport_hr)

        weekly_min_i = _to_int_or_none(st.session_state.get("v_weekly_minutes") or weekly_minutes)
        session_int_i = _to_int_or_none(st.session_state.get("v_session_intensity") or session_intensity)
        resting_hr_i = _to_int_or_none(st.session_state.get("vo2_rhr_value") or resting_hr)
        max_hr_i = _to_int_or_none(st.session_state.get("vo2_maxhr_val") or max_hr)

        # BMI
        if run_bmi:
            bmi_value, bmi_category = calculators.bmi_calc(weight_f, height_f)
            results["bmi"] = {"value": round(float(bmi_value), 1), "category": bmi_category}
            if waist_f is not None and hip_f is not None:
                whr_value = calculators.waist_hip_ratio(waist_f, hip_f)
                whr_cat = calculators.whr_category(sex_val, whr_value)
                results["whr"] = {"value": round(float(whr_value), 2), "category": whr_cat}

        # Body fat (Navy) if requested
        if bodyfat_requested:
            try:
                if neck_f is None:
                    raise ValueError("Neck measurement required for Navy method.")
                if sex_val.startswith("M"):
                    if waist_f is None:
                        raise ValueError("Waist required for male body-fat estimate.")
                    bf = calculators.body_fat_navy(sex=sex_val, height_cm=height_f, neck_cm=neck_f, waist_cm=waist_f)
                else:
                    if waist_f is None or hip_f is None:
                        raise ValueError("Waist and hip required for female body-fat estimate.")
                    bf = calculators.body_fat_navy(sex=sex_val, height_cm=height_f, neck_cm=neck_f, waist_cm=waist_f, hip_cm=hip_f)
                results["bodyfat"] = {"value": round(float(bf), 1)}
            except Exception as e:
                st.warning(f"Body-fat estimate skipped: {e}")

        # VO2
        if run_vo2:
            vo2_method_sel = st.session_state.get("vo2_method_select", vo2_method)
            if measured_vo2_f is not None and measured_vo2_f > 0:
                vo2_value = calculators.vo2_measured_value(float(measured_vo2_f))
                method_used = "Measured value"
            elif vo2_method_sel == "Cooper (12-min)":
                vo2_value = calculators.vo2_cooper_from_distance(float(vo2_dist_f or 0.0))
                method_used = "Cooper (12-min)"
            elif vo2_method_sel == "Rockport (1-mile)":
                if rockport_time_f is None:
                    raise ValueError("Rockport time må være et tall for Rockport-metoden.")
                vo2_value = calculators.vo2_rockport_1mile(float(rockport_time_f), int(rockport_hr_i or 0), float(weight_f), int(age_i), sex_val)
                method_used = "Rockport (1-mile)"
            else:
                bmi_for_vo2 = results.get("bmi", {}).get("value") if results.get("bmi") else calculators.bmi_calc(weight_f, height_f)[0]
                vo2_value = calculators.vo2_questionnaire_estimate(
                    age=age_i,
                    sex=sex_val,
                    weekly_minutes=int(weekly_min_i or 0),
                    session_intensity_score=int(session_int_i or 1),
                    activity_level=st.session_state.get("v_activity", activity_level),
                    bmi=bmi_for_vo2,
                    resting_hr=int(resting_hr_i) if resting_hr_i is not None else None,
                    max_hr=int(max_hr_i) if max_hr_i is not None else None,
                )
                method_used = "Questionnaire"

            vo2_ref = calculators.vo2_reference(age_i, sex_val, float(vo2_value))
            vo2_tips = calculators.vo2_improvement_tips(vo2_value=float(vo2_value), sex=sex_val, age=age_i, activity_level=st.session_state.get("v_activity", activity_level), weekly_minutes=int(weekly_min_i or 0))
            top_descriptor = calculators.vo2_top_descriptor(age_i, sex_val, float(vo2_value))
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
            bmi_v = results.get("bmi", {}).get("value") if results.get("bmi") else calculators.bmi_calc(weight_f, height_f)[0]
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
                activity_level=st.session_state.get("v_activity", activity_level),
                sleep_hours=_to_optional_float(st.session_state.get("bio_sleep_val")),
                alcohol_units_per_week=_to_optional_float(st.session_state.get("bio_alc_val")),
                fruit_veg_servings=_to_optional_float(st.session_state.get("bio_fv")),
                perceived_stress=st.session_state.get("bio_stress", perceived_stress),
                grip_strength_kg=_to_optional_float(st.session_state.get("bio_grip_val")),
                bp_systolic=_to_optional_float(st.session_state.get("bio_bp_val")),
                cholesterol_mg_dl=_to_optional_float(st.session_state.get("bio_chol_val")),
                diabetes=st.session_state.get("bio_diabetes", False),
                resting_hr=_to_int_or_none(st.session_state.get("bio_rhr_val") or resting_hr_i),
                waist_to_hip_ratio=waist_to_hip,
                family_history=st.session_state.get("bio_family_hist", False),
                menopause=st.session_state.get("bio_menopause", False),
                measured_vo2=measured_vo2_for_bio,
            )
            results["bio_age"] = {"value": round(float(bio_age), 1)}
            results["bio_factors"] = bio_factors

        # Conditions
        if run_conditions:
            recs = calculators.recommendations_for_diagnoses(st.session_state.get("cond_select", []) or selected_conditions, st.session_state.get("cond_goal", condition_goal_focus))
            results["triage"] = {"level": "Info", "message": "Recommendations generated for selected conditions."}
            results["triage_recommendations"] = recs

        # Plan generation
        if run_plan and run_bmi and create_plan:
            if target_bmi is not None:
                t_w = float(target_bmi) * (float(height_f) / 100.0) ** 2
                target_weight = t_w
            # read current exercise burn from session_state
            ekpw = float(st.session_state.get("exercise_kcal_per_week", 0.0) or 0.0)
            if target_weight is not None:
                plan = calculators.generate_weight_plan(
                    current_weight_kg=float(weight_f),
                    target_weight_kg=float(target_weight),
                    weeks=int(st.session_state.get("plan_weeks", plan_weeks) or plan_weeks),
                    sex=sex_val,
                    height_cm=float(height_f),
                    age=int(age_i),
                    activity_level=st.session_state.get("v_activity", activity_level),
                    exercise_kcal_per_week=ekpw,
                )
                if plan.get("error"):
                    st.error(plan.get("message"))
                else:
                    results["plan"] = plan

    except Exception as e:
        st.error(f"Error during calculation: {e}")
        st.text("If you need help, paste the full traceback here.")
        import traceback, logging
        logging.exception("Calculation failed")
        st.text(traceback.format_exc())
        st.session_state["latest_results"] = {}
    else:
        st.session_state["latest_results"] = results
        st.success("Calculation finished — results ready.")

# --- Display results ---
results = st.session_state.get("latest_results", {})

if results:
    st.success("Results ready")

    # BMI
    if "bmi" in results:
        st.subheader("BMI")
        b = results["bmi"]["value"]
        cat = results["bmi"]["category"]
        st.markdown(f"""
            <div class="result-box">
                <div style="font-size:18px; font-weight:700;">Din BMI: {b:.1f}</div>
                <div style="margin-top:6px; padding:6px 10px; display:inline-block; border-radius:8px; background:#1f2937; color:#fff; font-weight:700;">
                    {cat}
                </div>
            </div>
        """, unsafe_allow_html=True)
        try:
            st.pyplot(plot_bmi_gauge(b), use_container_width=True)
        except Exception:
            pass

    # Energy & metabolism (BMR)
    st.markdown("---")
    st.subheader("Energy og Metabolism")

    def _to_float_local(val):
        try:
            return float(str(val).replace(",", ".").strip())
        except Exception:
            return None

    calc_age_f = _to_float_local(age)
    calc_weight = _to_float_local(weight_kg)
    calc_height = _to_float_local(height_cm)
    if calc_age_f is None or calc_weight is None or calc_height is None:
        st.info("Fyll inn alder, vekt og høyde for kaloriberegning.")
    else:
        bmr_val = bmr_mifflin(age=int(calc_age_f), sex=sex, weight_kg=float(calc_weight), height_cm=float(calc_height))
        daily_living = bmr_val * 1.2
        w_kcal = float(st.session_state.get("exercise_kcal_per_week", 0.0) or 0.0)
        tdee_total = tdee_including_weekly_exercise(bmr_val, st.session_state.get("v_activity", activity_level), w_kcal)
        c1, c2, c3 = st.columns(3)
        c1.metric("BMR", f"{int(bmr_val)} kcal")
        c2.metric("Daily Calorie Burn", f"{int(daily_living)} kcal")
        c3.metric("Total Daily Calorie Burn w/exercise", f"{int(tdee_total)} kcal")

    # VO2 display with fancy component
    if "vo2" in results:
        st.markdown("---")
        st.subheader("VO2 max & fitness")
        v_val = float(results["vo2"]["value"])
        v_pct = max(0.0, min(100.0, float(results["vo2"].get("percentile") or 0.0)))
        top_text = f"Top {100 - v_pct:.1f}%"

        c1, c2, c3 = st.columns(3)
        c1.metric("Your VO2 max", f"{v_val:.1f} ml/kg/min")
        c2.metric("Percentile", f"{v_pct:.0f}%")
        c3.metric("Ranking", top_text)

        # Determine label and color
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

        vo2_rows = [("20–29", 44, 40, "#26A690"), ("30–39", 40, 36, "#3B82F6"), ("40–49", 37, 33, "#7C7CF5"), ("50–59", 34, 30, "#EF6A3B"), ("60+", 30, 27, "#D18A1A")]

        def band_match(band: str) -> bool:
            if band == "20–29": return 20 <= age <= 29
            if band == "30–39": return 30 <= age <= 39
            if band == "40–49": return 40 <= age <= 49
            if band == "50–59": return 50 <= age <= 59
            return age >= 60

        active_band = None
        for band, _, _, _ in vo2_rows:
            if band_match(band):
                active_band = band
                break

        if str(sex).upper().startswith("M"):
            current_avg = dict((b, m) for b, m, _, _ in vo2_rows)
        else:
            current_avg = dict((b, w) for b, _, w, _ in vo2_rows)

# Render the rich VO2 HTML/CSS component (the chart you liked)
try:
    vo2_html = f"""
<style>
  .vo2-wrap {{
    font-family: Arial, sans-serif;
    color: #E5E7EB;
    padding: 2px;
  }}
  .vo2-grid {{
    display: grid;
    grid-template-columns: 1.2fr 0.8fr;
    gap: 14px;
    align-items: stretch;
  }}
  .vo2-card {{
    background: #1F2937;
    border: 1px solid #374151;
    border-radius: 16px;
    padding: 18px;
  }}
  .vo2-title {{
    margin: 0 0 6px 0;
    font-size: 20px;
    font-weight: 700;
    color: #F9FAFB;
  }}
  .vo2-sub {{
    margin: 0 0 16px 0;
    font-size: 12px;
    line-height: 1.4;
    color: #9CA3AF;
  }}
  .metric-row {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }}
  .metric {{
    background: #111827;
    border: 1px solid #374151;
    border-radius: 12px;
    padding: 10px 12px;
    min-width: 0;
  }}
  .metric-k {{
    margin: 0 0 4px 0;
    font-size: 12px;
    color: #9CA3AF;
  }}
  .metric-v {{
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    color: #F9FAFB;
    line-height: 1.1;
  }}
  .band {{
    display: grid;
    grid-template-columns: 56px 1fr 70px;
    gap: 10px;
    align-items: center;
    margin: 10px 0;
  }}
  .band-lbl {{
    font-size: 12px;
    color: #D1D5DB;
    white-space: nowrap;
  }}
  .band-bar {{
    height: 16px;
    background: #111827;
    border: 1px solid #374151;
    border-radius: 999px;
    overflow: hidden;
    position: relative;
  }}
  .band-fill {{
    height: 100%;
    border-radius: 999px;
  }}
  .band-badge {{
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 11px;
    font-weight: 700;
    color: #111827;
    background: rgba(255,255,255,0.88);
    padding: 1px 6px;
    border-radius: 999px;
  }}
  .band-val {{
    text-align: right;
    font-size: 12px;
    font-weight: 700;
    color: #E5E7EB;
  }}
  .band-active {{
    background: #F8FAFC;
    border-radius: 12px;
    padding: 8px 10px;
  }}
  .band-active .band-lbl {{
    color: #0F172A;
    font-weight: 700;
  }}
  .band-active .band-val {{
    color: #26A690;
  }}
  .pill-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;
  }}
  .pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #CBD5E1;
    background: #111827;
    border: 1px solid #374151;
    border-radius: 999px;
    padding: 6px 10px;
  }}
  .dot {{
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex: 0 0 10px;
  }}
  .gauge-wrap {{
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  .gauge-head {{
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 8px;
  }}
  .gauge-k {{
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    color: #F9FAFB;
  }}
  .gauge-sub {{
    margin: 4px 0 0 0;
    font-size: 12px;
    color: #9CA3AF;
    line-height: 1.4;
  }}
  .pct-num {{
    margin: 0;
    font-size: 34px;
    font-weight: 700;
    line-height: 1;
    color: {pct_color};
    text-align: right;
  }}
  .pct-lbl {{
    margin: 3px 0 0 0;
    font-size: 12px;
    color: #D1D5DB;
    text-align: right;
  }}
  .callout {{
    width: 100%;
    background: #111827;
    border: 1px solid #374151;
    border-radius: 12px;
    padding: 12px;
    color: #D1D5DB;
    font-size: 12px;
    line-height: 1.45;
    margin-top: 12px;
  }}
  .legend-col {{
    width: 100%;
    margin-top: 14px;
    display: grid;
    gap: 8px;
  }}
  .legend-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    background: #111827;
    border: 1px solid #374151;
    border-radius: 999px;
    padding: 8px 10px;
    font-size: 12px;
    color: #CBD5E1;
  }}
  .mini-note {{
    width: 100%;
    margin-top: 8px;
    font-size: 12px;
    color: #9CA3AF;
    text-align: center;
  }}
</style>

<div class="vo2-wrap">
  <div class="vo2-grid">
    <div class="vo2-card">
      <div class="vo2-title">VO2 max across age bands</div>
      <div class="vo2-sub">A more live and readable view than a standard table.</div>

      <div class="metric-row">
        <div class="metric">
          <div class="metric-k">Your VO2 max</div>
          <div class="metric-v">{v_val:.1f}</div>
        </div>
        <div class="metric">
          <div class="metric-k">Age band</div>
          <div class="metric-v">{active_band or "—"}</div>
        </div>
        <div class="metric">
          <div class="metric-k">Rating</div>
          <div class="metric-v">{pct_label}</div>
        </div>
      </div>

      {"".join([
        f'''
      <div class="band{' band-active' if band == active_band else ''}">
        <div class="band-lbl">{band}</div>
        <div class="band-bar">
          <div class="band-fill" style="width:{min(100, max(0, int(current_avg[band] / 50.0 * 100)))}%; background:{color};"></div>
          <div class="band-badge">{current_avg[band]} avg</div>
        </div>
        <div class="band-val">{'Your group' if band == active_band else 'Average'}</div>
      </div>
        '''
        for band, _, _, color in vo2_rows
      ])}

      <div class="pill-row">
        <div class="pill"><span class="dot" style="background:#26A690"></span>Very strong</div>
        <div class="pill"><span class="dot" style="background:#3B82F6"></span>Strong</div>
        <div class="pill"><span class="dot" style="background:#7C7CF5"></span>Mid range</div>
        <div class="pill"><span class="dot" style="background:#EF6A3B"></span>Needs work</div>
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

        <svg width="100%" viewBox="0 0 260 170" aria-label="Population percentile gauge">
          <path d="M40 122 A90 90 0 0 1 220 122" fill="none" stroke="#4B5563" stroke-width="18" stroke-linecap="round" pathLength="100"/>
          <path d="M40 122 A90 90 0 0 1 220 122" fill="none" stroke="{pct_color}" stroke-width="18" stroke-linecap="round" pathLength="100" stroke-dasharray="{v_pct} 100"/>
          <circle cx="130" cy="122" r="50" fill="#1F2937" stroke="#374151" stroke-width="1"/>
          <text x="130" y="116" text-anchor="middle" font-size="36" font-weight="700" fill="#F9FAFB">{int(round(v_pct))}</text>
          <text x="130" y="136" text-anchor="middle" font-size="12" fill="#CBD5E1">percentile</text>
          <text x="40" y="158" text-anchor="start" font-size="12" fill="#9CA3AF">0</text>
          <text x="130" y="158" text-anchor="middle" font-size="12" fill="#9CA3AF">50</text>
          <text x="220" y="158" text-anchor="end" font-size="12" fill="#9CA3AF">100</text>
        </svg>

        <div class="callout">
          <b>Interpretation:</b> You are performing very well compared to the average for your age.
        </div>

        <div class="legend-col">
          <div class="legend-item"><span class="dot" style="background:#3B82F6"></span>Population average</div>
          <div class="legend-item"><span class="dot" style="background:#26A690"></span>Better than average</div>
        </div>

        <div class="mini-note">Klar, fargekodet og mykje lettare å lese.</div>
      </div>
    </div>
  </div>
</div>
"""
    components.html(vo2_html, height=760, scrolling=False)

except Exception:
    # fallback
    st.pyplot(plot_vo2_reference_chart(v_val, sex, int(age)), use_container_width=True)

    # Biological age
    if "bio_age" in results:
        st.markdown("---")
        st.subheader("Biological age")
        st.metric("Biological age", f"{results['bio_age']['value']:.1f} years")
        if results.get("bio_factors"):
            st.markdown("**Factor breakdown**")
            factor_rows = [{"Factor": f["label"], "Effect": f"{f.get('delta', 0):+.0f} years"} for f in results["bio_factors"]]
            st.table(factor_rows)

    # Conditions / recommendations
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
        st.markdown("---")
        st.subheader("Weight goal / plan")
        plan = results["plan"]
        current_maint = int(plan.get("current_needs_kcal", 0))
        kg_per_week = float(plan.get("kg_per_week", 0.0))
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

    # PDF report (shared for all results)
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
    }
    try:
        pdf_bytes = create_pdf_bytes(report)
        st.download_button("Download PDF report", data=pdf_bytes, file_name="health_tools_report.pdf", mime="application/pdf", key="pdf_btn")
    except Exception as e:
        st.warning(f"PDF generation currently unavailable: {e}")

else:
    st.info("Trykk på 'Calculate / Generate report' for å kjøre beregningene.")
