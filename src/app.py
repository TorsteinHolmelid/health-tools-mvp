from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO

import matplotlib.pyplot as plt
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import calculators

# --- Page config and basic styling ---
st.set_page_config(page_title="Health Tools MVP", layout="centered")
st.markdown(
    """
    <style>
    /* Base - mørk, men høg kontrast på tekst */
    .stApp { background-color: #0b1220; color: #e6eef8; }

    /* Sidebar */
    [data-testid="stSidebar"] {
      background-color: #0b1220 !important;
      color: #e6eef8 !important;
      border-right: 1px solid rgba(255,255,255,0.03);
      padding: 18px;
    }

    /* Gjør input-felt lysare enn bakgrunnen (gir kontrast mot tekst) */
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

    /* Expander / accordions - mindre "tung" farge */
    .stExpander > button {
      background-color: rgba(255,255,255,0.03) !important;
      color: #e6eef8 !important;
      border: 1px solid rgba(255,255,255,0.04) !important;
      border-radius: 8px !important;
      padding: 8px 12px !important;
    }

    /* Resultat-boks */
    .result-box {
      background-color: rgba(255,255,255,0.03);
      color: #e6eef8;
      border: 1px solid rgba(255,255,255,0.04);
      padding: 14px;
      border-radius: 10px;
      margin-bottom: 12px;
    }

    /* Knapper - akse ntfarge som står ut på mørk bakgrunn */
    .stButton>button {
      background-color: #0ea5a3 !important;
      color: #022b2a !important;
      border-radius: 8px !important;
      padding: 8px 12px !important;
      font-weight: 600 !important;
    }
    .stButton>button:hover { filter: brightness(0.95); }

    /* Overskrifter/tekst */
    h1, h2, h3, p, label {
      color: #e6eef8 !important;
    }

    /* Tabellar og plots: sørg for lys tekst */
    .stTable td, .stTable th { color: #e6eef8 !important; }

    /* Mobil: knapper 100% breidde */
    @media (max-width: 600px) {
      .stButton>button { width: 100% !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Health Tools — MVP")
st.caption("Educational tool only — not a diagnostic tool. Data is not stored.")


# ----------------------------
# Consent modal (simple)
# ----------------------------
# --- Consent / privacy notice (safe version) ---
# Sørg for at flagget finnes
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

    # Opprett cols her slik at de alltid er definert før bruk
    cols = st.columns([1, 1])
    if cols[0].button("I agree", key="consent_agree"):
        st.session_state.consent_given = True
        # Trygg rerun: kjør bare én gang og håndter miljøer uten experimental_rerun
        try:
            if not st.session_state.get("_consent_rerun_done"):
                st.session_state["_consent_rerun_done"] = True
                st.experimental_rerun()
        except Exception:
            st.warning("App reload (experimental_rerun) er ikke tilgjengelig her — fortsetter uten reload.")
    if cols[1].button("Exit", key="consent_exit"):
        st.stop()


# ----------------------------
# Plot helpers
# ----------------------------
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
    # Visualize percentile on a horizontal axis (0-100)
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


# ----------------------------
# PDF helpers (kept and slightly improved)
# ----------------------------
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
        ("Age", inputs["age"]),
        ("Sex", inputs["sex"]),
        ("Height", f'{inputs["height_cm"]} cm'),
        ("Weight", f'{inputs["weight_kg"]} kg'),
    ]
    story.append(make_key_value_table(inputs_rows))
    story.append(Spacer(1, 6 * mm))
    summary_rows = []
    if report.get("bmi"):
        summary_rows.append(("BMI", f'{report["bmi"]["value"]} ({report["bmi"]["category"]})'))
    if report.get("vo2"):
        summary_rows.append(("VO2max", f'{report["vo2"]["value"]} ml/kg/min | {report["vo2"]["rating"]} | {report["vo2"]["percentile"]}th percentile'))
        if report["vo2"].get("top_descriptor"):
            summary_rows.append(("Global rank", report["vo2"]["top_descriptor"]))
    if report.get("bio_age"):
        summary_rows.append(("Biological age", f'{report["bio_age"]["value"]} years'))
    if report.get("triage"):
        summary_rows.append(("Conditions notes", report["triage"]["message"]))
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
        story.append(figure_image(plot_bmi_gauge(report["bmi"]["value"]), width_mm=176))
        story.append(Spacer(1, 3 * mm))
    # VO2 section
    if report.get("vo2"):
        story.append(Paragraph("VO2max", section))
        story.append(Paragraph("VO2max is estimated from your chosen method or entered directly if you already know a measured value.", body))
        story.append(Spacer(1, 2 * mm))
        story.append(make_key_value_table([("Method", report["vo2"]["method"]), ("VO2max", f'{report["vo2"]["value"]} ml/kg/min'), ("Age band", report["vo2"]["age_band"]), ("Percentile", f'{report["vo2"]["percentile"]}th'), ("Reference rating", report["vo2"]["rating"])]))
        story.append(Spacer(1, 4 * mm))
        story.append(figure_image(plot_vo2_reference_chart(report["vo2"]["value"], inputs["sex"], inputs["age"]), width_mm=176))
        story.append(Spacer(1, 4 * mm))
        if report["vo2"].get("top_descriptor"):
            story.append(make_key_value_table([("Global rank", report["vo2"]["top_descriptor"])]))
            story.append(Spacer(1, 3 * mm))
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
            factor_rows = [{"Factor": f["label"], "Effect": f'{f["delta"]:+.0f} years'} for f in report["bio_factors"]]
            story.append(make_key_value_table([(r["Factor"], r["Effect"]) for r in factor_rows], col_widths=(70*mm, 100*mm)))
            story.append(Spacer(1, 4 * mm))
    # Conditions / recommendations
    if report.get("triage"):
        story.append(Paragraph("Conditions & Recommendations", section))
        tri = report["triage"]
        story.append(make_key_value_table([("Note", tri["message"])]))
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
            plan = report["plan"]
            plan_rows = [("Current maintenance kcal", f'{plan["current_needs_kcal"]} kcal/day'), ("Recommended daily kcal", f'{plan["recommended_daily_kcal"]} kcal/day'), ("Expected weekly change", f'{plan["kg_per_week"]:+.2f} kg/week')]
            story.append(make_key_value_table(plan_rows))
            story.append(Spacer(1, 3 * mm))
            story.append(make_key_value_table([("Milestones", "")]))
            story.append(make_key_value_table([(str(m["Week"]), f'{m["Projected weight (kg)"]} kg — {m["Focus"]}') for m in plan["milestones"]], col_widths=(35*mm,145*mm)))
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


# ----------------------------
# Sidebar selection
# ----------------------------
st.sidebar.header("Modules")
run_bmi = st.sidebar.checkbox("BMI calculator", value=True, key="s_bmi")
run_vo2 = st.sidebar.checkbox("VO2max estimate", value=True, key="s_vo2")
run_bioage = st.sidebar.checkbox("Biological age", value=True, key="s_bio")
run_conditions = st.sidebar.checkbox("Conditions & recommendations", value=True, key="s_conditions")
run_plan = st.sidebar.checkbox("Weight goal / plan", value=True, key="s_plan")
st.sidebar.markdown("---")
st.sidebar.info("This app does not store personal health data. It is for education and demonstration only.")


# ----------------------------
# Basic inputs (unique keys)
# ----------------------------
st.header("Basic information")
col1, col2 = st.columns(2)
with col1:
    age = st.number_input("Age (years)", min_value=0, max_value=120, value=30, step=1, key="inp_age")
    sex = st.selectbox("Sex", options=["M", "F"], index=0, key="inp_sex")
with col2:
    height_cm = st.number_input("Height (cm)", min_value=50, max_value=250, value=170, key="inp_height")
    weight_kg = st.number_input("Weight (kg)", min_value=20.0, max_value=300.0, value=70.0, format="%.1f", key="inp_weight")

if age < 18:
    st.warning("BMI and fitness estimates are less reliable under 18 because different reference rules are used.")
elif age >= 70:
    st.info("For older adults, BMI is often less informative because muscle mass, frailty and overall context matter.")


# defaults for subsequent inputs (safe initialization)
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


# ----------------------------
# BMI inputs
# ----------------------------
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


# ----------------------------
# VO2 inputs
# ----------------------------
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
            value=150,
            key="v_weekly_minutes"
        )
        session_intensity = st.slider(
            "Typical session intensity (1 = very light, 5 = very intense)",
            min_value=1,
            max_value=5,
            value=3,
            key="v_session_intensity"
        )
        resting_hr_unknown = st.checkbox("I don't know my resting heart rate", value=True, key="vo2_rhr_unknown")
        if not resting_hr_unknown:
            resting_hr = st.number_input("Resting heart rate (bpm)", min_value=30, max_value=220, value=70, key="vo2_rhr_value")
        max_hr_unknown = st.checkbox("I don't know my max heart rate", value=True, key="vo2_maxhr_unknown")
        if not max_hr_unknown:
            max_hr = st.number_input("Estimated max heart rate (bpm)", min_value=40, max_value=240, value=180, key="vo2_maxhr_val")
        measured_vo2_input = st.number_input(
            "If you know a measured VO2max (Apple Watch, lab, etc.), enter it here",
            min_value=0.0,
            value=0.0,
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
            vo2_distance_m = st.number_input("12-minute distance (meters)", min_value=0.0, value=0.0, format="%.1f", key="vo2_cooper_distance")
        elif vo2_method == "Rockport (1-mile)":
            rockport_time_min = st.number_input("1-mile time (minutes)", min_value=0.1, value=15.0, format="%.2f", key="vo2_rockport_time")
            rockport_hr = st.number_input("Heart rate at the end (bpm)", min_value=30, max_value=220, value=140, key="vo2_rockport_hr")


# ----------------------------
# Biological age inputs
# ----------------------------
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
            bp_systolic = st.number_input("Systolic blood pressure (mmHg)", min_value=70.0, max_value=260.0, value=120.0, key="bio_bp_val")
        chol_unknown = st.checkbox("I don't know my cholesterol", value=True, key="bio_chol_unknown")
        if not chol_unknown:
            cholesterol = st.number_input("Cholesterol (mg/dL)", min_value=50.0, max_value=500.0, value=180.0, key="bio_chol_val")
        rhr_unknown = st.checkbox("I don't know my resting heart rate", value=True, key="bio_rhr_unknown")
        if not rhr_unknown:
            resting_hr = st.number_input("Resting heart rate (bpm)", min_value=30, max_value=220, value=70, key="bio_rhr_val")
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


# ----------------------------
# Conditions / recommendations (replaces symptom triage)
# ----------------------------
selected_conditions = []
custom_condition = ""
condition_goal_focus = "General"

if run_conditions:
    with st.expander("Conditions & recommendations", expanded=True):
        st.markdown("Select any diagnoses/conditions you have and choose a focus to get practical exercise & prevention tips.")
        condition_options = sorted(list(calculators.DIAGNOSIS_RECOMMENDATIONS.keys()))
        selected_conditions = st.multiselect("Select conditions (choose one or more)", options=condition_options, default=[], key="cond_select")
        custom_condition = st.text_input("Other condition (free text)", "", key="cond_custom")
        if custom_condition.strip():
            selected_conditions = (selected_conditions or []) + [custom_condition.strip()]
        condition_goal_focus = st.selectbox("Recommendations focus", options=["General", "VO2", "Weight", "Mobility"], index=0, key="cond_goal")


# ----------------------------
# Weight goal / plan
# ----------------------------
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


# ----------------------------
# Calculate / Generate report
# ----------------------------
if st.button("Calculate / Generate report", key="btn_calculate"):
    results = {}
    try:
        bmi_value = None
        bmi_category = None
        # BMI
        if run_bmi:
            bmi_value, bmi_category = calculators.bmi_calc(weight_kg, height_cm)
            results["bmi"] = {"value": bmi_value, "category": bmi_category}
            if waist_cm is not None and hip_cm is not None:
                whr_value = calculators.waist_hip_ratio(waist_cm, hip_cm)
                whr_cat = calculators.whr_category(sex, whr_value)
                results["whr"] = {"value": whr_value, "category": whr_cat}
            if bodyfat_requested and neck_cm is not None:
                try:
                    if sex == "M":
                        if waist_cm is None:
                            raise ValueError("Waist measurement required for male body-fat estimate")
                        bodyfat = calculators.body_fat_navy(sex, height_cm, neck_cm, waist_cm)
                    else:
                        if waist_cm is None or hip_cm is None:
                            raise ValueError("Waist and hip measurements required for female body-fat estimate")
                        bodyfat = calculators.body_fat_navy(sex, height_cm, neck_cm, waist_cm, hip_cm)
                    results["bodyfat"] = bodyfat
                except Exception as e:
                    st.warning(f"Body-fat estimate skipped: {e}")
        # VO2
        if run_vo2:
            measured_vo2 = measured_vo2_input if measured_vo2_input and measured_vo2_input > 0 else None
            if measured_vo2 is not None:
                vo2_value = calculators.vo2_measured_value(measured_vo2)
                method_used = "Measured value"
            elif vo2_method == "Cooper (12-min)":
                vo2_value = calculators.vo2_cooper_from_distance(vo2_distance_m)
                method_used = "Cooper (12-min)"
            elif vo2_method == "Rockport (1-mile)":
                vo2_value = calculators.vo2_rockport_1mile(rockport_time_min, int(rockport_hr), weight_kg, age, sex)
                method_used = "Rockport (1-mile)"
            else:
                if bmi_value is None and run_bmi:
                    bmi_value, _ = calculators.bmi_calc(weight_kg, height_cm)
                vo2_value = calculators.vo2_questionnaire_estimate(
                    age=age,
                    sex=sex,
                    weekly_minutes=int(weekly_minutes),
                    session_intensity_score=int(session_intensity),
                    activity_level=activity_level,
                    bmi=bmi_value,
                    resting_hr=int(resting_hr) if resting_hr is not None else None,
                    max_hr=int(max_hr) if max_hr is not None else None,
                )
                method_used = "Questionnaire"
            vo2_ref = calculators.vo2_reference(age, sex, vo2_value)
            vo2_tips = calculators.vo2_improvement_tips(
                vo2_value=vo2_value,
                sex=sex,
                age=age,
                activity_level=activity_level,
                weekly_minutes=int(weekly_minutes),
            )
            top_descriptor = calculators.vo2_top_descriptor(age, sex, vo2_value)
            results["vo2"] = {
                "value": vo2_value,
                "method": method_used,
                "age_band": vo2_ref["age_band"],
                "percentile": vo2_ref["percentile"],
                "rating": vo2_ref["rating"],
                "reference_mean": vo2_ref["mean"],
                "tips": vo2_tips,
                "top_descriptor": top_descriptor,
            }
        # Biological age
        if run_bioage:
            if bmi_value is None and run_bmi:
                bmi_value, _ = calculators.bmi_calc(weight_kg, height_cm)
            waist_to_hip = None
            if waist_cm is not None and hip_cm is not None:
                try:
                    waist_to_hip = calculators.waist_hip_ratio(waist_cm, hip_cm)
                except Exception:
                    waist_to_hip = None
            measured_vo2_for_bio = None
            if results.get("vo2") is not None:
                measured_vo2_for_bio = results["vo2"]["value"]
            bio_age, bio_factors = calculators.estimate_biological_age_detailed(
                age=age,
                sex=sex,
                smoker=smoker,
                bmi=bmi_value,
                activity_level=activity_level,
                sleep_hours=sleep_hours,
                alcohol_units_per_week=alcohol_units,
                fruit_veg_servings=fruit_veg,
                perceived_stress=perceived_stress,
                grip_strength_kg=grip_strength,
                bp_systolic=bp_systolic,
                cholesterol_mg_dl=cholesterol,
                diabetes=diabetes,
                resting_hr=resting_hr,
                waist_to_hip_ratio=waist_to_hip,
                family_history=family_history,
                menopause=menopause,
                measured_vo2=measured_vo2_for_bio,
            )
            results["bio_age"] = {"value": bio_age}
            results["bio_factors"] = bio_factors
        # Conditions & recommendations
        if run_conditions:
            recs = calculators.recommendations_for_diagnoses(selected_conditions, condition_goal_focus)
            # build a short message for display & PDF
            cond_message = "Recommendations generated for selected conditions."
            results["triage"] = {"level": "Info", "message": cond_message}
            results["triage_recommendations"] = recs
        # Plan
        if run_plan and run_bmi and create_plan:
            if target_bmi is not None:
                target_weight = target_bmi * (height_cm / 100.0) ** 2
            if target_weight is not None:
                plan = calculators.generate_weight_plan(
                    current_weight_kg=weight_kg,
                    target_weight_kg=target_weight,
                    weeks=int(plan_weeks),
                    sex=sex,
                    height_cm=height_cm,
                    age=age,
                    activity_level=activity_level,
                )
                # If plan returns error, show and don't add plan
                if plan.get("error"):
                    st.error(plan.get("message"))
                else:
                    results["plan"] = plan
    except Exception as e:
        st.error(f"Error during calculation: {e}")
        results = {}
    # ----------------------------
    # Display results
    # ----------------------------
# ------------------------------
# Display results
# ------------------------------
if results:
    st.success("Results ready")

    # --- 1. BMI SEKSJON ---
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
        
        # BMI Gauge
        st.pyplot(plot_bmi_gauge(b), use_container_width=True)
        plt.close("all")

    # --- 2. ENERGI & FORBRENNING (BMR/Koma seksjon) ---
    st.markdown("---")
    st.subheader("Energi og Forbrenning")
    
    # Beregninger
    import streamlit as st
st.write("Debug: available names in calculators module:", dir())

    bmr_val = bmr_mifflin(age, sex, weight_kg, height_cm)
    daily_living = bmr_val * 1.2 # Basis hverdagsaktivitet (uten trening)
    # Henter weekly_kcal hvis den finnes, ellers 0
    w_kcal = locals().get('weekly_kcal', 0)
    tdee_total = tdee_including_weekly_exercise(bmr_val, activity_level, w_kcal)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("BMR (Hvile)", f"{int(bmr_val)} kcal", help="Forbrenning i 'koma' (fullstendig hvile).")
    c2.metric("Hverdagsforbruk", f"{int(daily_living)} kcal", help="Forbrenning ved normal daglig aktivitet uten trening.")
    c3.metric("Total m/trening", f"{int(tdee_total)} kcal", help="Gjennomsnittlig dagsforbruk inkludert din ukentlige trening.")

    # --- 3. VO2 MAX & TABELL MED HIGHLIGHT ---
    if "vo2" in results:
        st.markdown("---")
        st.subheader("VO2max & Kondisjon")
        v_val = results["vo2"]["value"]
        v_pct = results["vo2"]["percentile"]
        
        st.metric("Din VO2max", f"{v_val:.1f} ml/kg/min", f"Topp {100-v_pct:.1f}%")
        
        # Referansetabell
        vo2_ref_data = {
            "Alder": ["20-29", "30-39", "40-49", "50-59", "60+"],
            "Menn (snitt)": [44, 40, 37, 34, 30],
            "Kvinner (snitt)": [38, 34, 31, 28, 25]
        }
        df_vo2 = pd.DataFrame(vo2_ref_data)

        # Highlight funksjon
        def highlight_row(s):
            is_me = False
            if 20<=age<=29 and s.Alder=="20-29": is_me=True
            elif 30<=age<=39 and s.Alder=="30-39": is_me=True
            elif 40<=age<=49 and s.Alder=="40-49": is_me=True
            elif 50<=age<=59 and s.Alder=="50-59": is_me=True
            elif age>=60 and s.Alder=="60+": is_me=True
            return ['background-color: #fde68a; font-weight: bold; color: black'] * len(s) if is_me else [''] * len(s)

        st.write("Slik ligger du an mot gjennomsnittet:")
        st.table(df_vo2.style.apply(highlight_row, axis=1))

    # --- 4. POPULATION PERCENTILE LISTE (Renere design) ---
    st.markdown("---")
    st.subheader("Population Percentile")
    
    # Her bruker vi HTML for å få det skikkelig clean og unngå "skvising"
    st.markdown(f"""
        <div style="background:#f8fafc; padding:15px; border-radius:12px; border:1px solid #e2e8f0;">
            <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #cbd5e1; color:#1e293b;">
                <span>Global Rank:</span> <strong>Topp {100-results.get('vo2',{}).get('percentile',50):.1f}%</strong>
            </div>
            <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #cbd5e1; color:#1e293b;">
                <span>Din aldersgruppe:</span> <strong>Bedre enn {results.get('vo2',{}).get('percentile',50):.1f}%</strong>
            </div>
            <div style="display:flex; justify-content:space-between; padding:8px 0; color:#1e293b;">
                <span>Helse-score:</span> <strong>Optimal</strong>
            </div>
        </div>
        <p style="color:#1e293b; font-size:12px; margin-top:10px; font-weight:500;">
            * Sammenlignet med data fra nasjonale helseundersøkelser.
        </p>
    """, unsafe_allow_html=True)
# Biological age
    if "bio_age" in results:
        st.subheader("Biological age")
        st.metric("Biological age", f"{results['bio_age']['value']:.1f} years")
        if results.get("bio_factors"):
            st.markdown("**Factor breakdown**")
            factor_rows = [
                {"Factor": f["label"], "Effect": f"{f.get('delta', 0):+.0f} years"}
                for f in results["bio_factors"]
            ]
            st.table(factor_rows)

    # Conditions
    if "triage" in results:
        st.subheader("Conditions & recommendations")
        if results.get("triage_recommendations"):
            for r in results["triage_recommendations"]:
                st.write(r)
        else:
            # Fallback: vis generell triage-melding hvis ingen liste
            st.info(results.get("triage", {}).get("message", "No triage details."))

    # Plan
    if "plan" in results:
        st.subheader("Weight goal / plan")
        plan = results["plan"]
        st.write(f"Current maintenance calories: **{plan.get('current_needs_kcal', 'N/A')} kcal/day**")
        st.write(f"Recommended daily calories: **{plan.get('recommended_daily_kcal', 'N/A')} kcal/day**")
        st.write(f"Expected weekly change: **{plan.get('kg_per_week', 0):+.2f} kg/week**")
        if plan.get("warning"):
            st.warning(plan["warning"])
        st.markdown("**Condensed milestones**")
        st.table(plan.get("milestones", []))
        # PDF
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
            st.warning(f"PDF generation is currently unavailable: {e}")
    else:
        st.warning("No results to show.")
