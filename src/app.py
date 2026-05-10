# Consent modal (simple)
if "consent_given" not in st.session_state:
    st.session_state.consent_given = False

if not st.session_state.consent_given:
    with st.modal("Consent"):
        st.markdown("By using this demo you accept that data is not stored and this tool is educational only.")
        cols = st.columns([1,1])
        if cols[0].button("I agree"):
            st.session_state.consent_given = True
            st.experimental_rerun()
        if cols[1].button("Cancel"):
            st.stop()
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


st.set_page_config(page_title="Health Tools MVP", layout="centered")

st.title("Health Tools — MVP")
st.caption("Educational tool only — not a diagnostic tool. Data is not stored.")

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
    ax.text(
        marker_x,
        1.00,
        f"{bmi_value:.1f}",
        ha="center",
        va="bottom",
        fontsize=10.5,
        color="#e5e7eb",
        fontweight="bold",
    )

    ax.set_xlim(0, 45)
    ax.set_ylim(0, 1.25)
    ax.set_yticks([])
    ax.set_xticks([0, 10, 18.5, 25, 30, 40, 45])
    ax.tick_params(axis="x", labelsize=9, colors="#cbd5e1")
    ax.set_xlabel("BMI", color="#cbd5e1", fontsize=10)
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
    ax.set_ylabel("VO2max (ml/kg/min)", color="#cbd5e1")
    ax.set_title(f"VO2max reference bands by age — age {age}", color="#e5e7eb", fontsize=11, fontweight="bold")
    ax.tick_params(axis="x", labelrotation=0, labelsize=8.5, colors="#cbd5e1")
    ax.tick_params(axis="y", labelsize=9, colors="#cbd5e1")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.legend(frameon=False, fontsize=8.5, labelcolor="#e5e7eb")
    plt.tight_layout()
    return fig


def plot_plan_chart(plan: dict):
    milestones = plan.get("milestones", [])
    if not milestones:
        return None

    weeks = [m["Week"] for m in milestones]
    weights = [m["Projected weight (kg)"] for m in milestones]

    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    ax.plot(weeks, weights, marker="o", color="#22c55e", linewidth=2.4)
    ax.set_xlabel("Week", color="#cbd5e1")
    ax.set_ylabel("Projected weight (kg)", color="#cbd5e1")
    ax.set_title("Goal progress milestones", color="#e5e7eb", fontsize=11, fontweight="bold")
    ax.tick_params(axis="x", colors="#cbd5e1")
    ax.tick_params(axis="y", colors="#cbd5e1")
    for spine in ax.spines.values():
        spine.set_visible(False)
    plt.tight_layout()
    return fig


# ----------------------------
# PDF helpers
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
                ("LEADING", (0, 0), (-1, -1), 11),
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


def make_data_table(rows, header_fill="#0f172a"):
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.fontName = "Helvetica"
    body.fontSize = 8.7
    body.leading = 10.5

    headers = list(rows[0].keys()) if rows else []
    data = [[para(h, body) for h in headers]]
    for row in rows:
        data.append([para(row.get(h, ""), body) for h in headers])

    col_count = max(1, len(headers))
    widths = [180 * mm / col_count for _ in range(col_count)]

    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_fill)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.7),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
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
    title = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle = ParagraphStyle(
        "SubtitleStyle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
    )
    section = ParagraphStyle(
        "SectionStyle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "BodyStyle",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=12,
        textColor=colors.HexColor("#111827"),
    )
    small = ParagraphStyle(
        "SmallStyle",
        parent=styles["BodyText"],
        fontName="Helvetica-Oblique",
        fontSize=7.8,
        leading=10,
        textColor=colors.HexColor("#475569"),
    )

    story = []
    story.append(Paragraph("Health Tools — Report", title))
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(
            "Educational report generated from the app inputs. This is not a medical diagnosis.",
            subtitle,
        )
    )
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

    # Summary box
    summary_rows = []
    if report.get("bmi"):
        summary_rows.append(("BMI", f'{report["bmi"]["value"]} ({report["bmi"]["category"]})'))
    if report.get("vo2"):
        summary_rows.append(
            ("VO2max",
             f'{report["vo2"]["value"]} ml/kg/min | {report["vo2"]["rating"]} | {report["vo2"]["percentile"]}th percentile')
        )
    if report.get("bio_age"):
        summary_rows.append(("Biological age", f'{report["bio_age"]["value"]} years'))
    if report.get("triage"):
        summary_rows.append(("Symptom triage", f'{report["triage"]["level"]}: {report["triage"]["message"]}'))
    if summary_rows:
        story.append(Paragraph("Summary", section))
        story.append(make_key_value_table(summary_rows))
        story.append(Spacer(1, 6 * mm))

    if report.get("bmi"):
        story.append(Paragraph("BMI", section))
        story.append(
            Paragraph(
                "BMI is a simple screening measure. Body composition, muscle mass, bone structure, age, pregnancy and athletic status can change how BMI should be interpreted.",
                body,
            )
        )
        story.append(Spacer(1, 2 * mm))
        story.append(make_key_value_table([("BMI", f'{report["bmi"]["value"]}'), ("Category", report["bmi"]["category"])]))
        story.append(Spacer(1, 4 * mm))
        story.append(figure_image(plot_bmi_gauge(report["bmi"]["value"]), width_mm=176))
        story.append(Spacer(1, 3 * mm))
        if report.get("bodyfat") is not None:
            story.append(make_key_value_table([("Estimated body fat", f'{report["bodyfat"]}%')]))
            story.append(Spacer(1, 3 * mm))
        if report.get("whr") is not None:
            story.append(make_key_value_table([("Waist-to-hip ratio", f'{report["whr"]["value"]} ({report["whr"]["category"]})')]))
            story.append(Spacer(1, 3 * mm))
        story.append(
            Paragraph(
                "Note: BMI interpretation is different in children/adolescents under 18 and should be used cautiously in older adults.",
                small,
            )
        )
        story.append(Spacer(1, 4 * mm))

    if report.get("vo2"):
        story.append(Paragraph("VO2max", section))
        story.append(
            Paragraph(
                "VO2max is estimated from your chosen method or entered directly if you already know a measured value.",
                body,
            )
        )
        story.append(Spacer(1, 2 * mm))
        story.append(
            make_key_value_table(
                [
                    ("Method", report["vo2"]["method"]),
                    ("VO2max", f'{report["vo2"]["value"]} ml/kg/min'),
                    ("Age band", report["vo2"]["age_band"]),
                    ("Percentile", f'{report["vo2"]["percentile"]}th'),
                    ("Reference rating", report["vo2"]["rating"]),
                ]
            )
        )
        story.append(Spacer(1, 4 * mm))
        story.append(figure_image(plot_vo2_reference_chart(report["vo2"]["value"], inputs["sex"], inputs["age"]), width_mm=176))
        story.append(Spacer(1, 4 * mm))
        ref_table = make_data_table(calculators.vo2_age_reference_table(inputs["sex"]))
        story.append(ref_table)
        story.append(Spacer(1, 4 * mm))
        tips = report["vo2"].get("tips", [])
        if tips:
            story.append(Paragraph("VO2 improvement tips", section))
            for tip in tips:
                story.append(Paragraph(f"• {escape(str(tip))}", body))
            story.append(Spacer(1, 4 * mm))

    if report.get("bio_age"):
        story.append(Paragraph("Biological age", section))
        story.append(
            Paragraph(
                "This is an educational estimate based on the inputs you provided. Missing values do not block the result.",
                body,
            )
        )
        story.append(Spacer(1, 2 * mm))
        bio_rows = [("Biological age", f'{report["bio_age"]["value"]} years')]
        story.append(make_key_value_table(bio_rows))
        story.append(Spacer(1, 3 * mm))
        if report.get("bio_factors"):
            factor_rows = [
                {"Factor": f["label"], "Effect": f'{f["delta"]:+.0f} years'}
                for f in report["bio_factors"]
            ]
            story.append(make_data_table(factor_rows))
            story.append(Spacer(1, 4 * mm))

    if report.get("triage"):
        story.append(Paragraph("Symptom triage", section))
        tri = report["triage"]
        story.append(make_key_value_table([("Level", tri["level"]), ("Message", tri["message"])]))
        story.append(Spacer(1, 4 * mm))

    if report.get("plan"):
        story.append(Paragraph("Goal / plan", section))
        plan = report["plan"]
        plan_rows = [
            ("Current maintenance kcal", f'{plan["current_needs_kcal"]} kcal/day'),
            ("Recommended daily kcal", f'{plan["recommended_daily_kcal"]} kcal/day'),
            ("Expected weekly change", f'{plan["kg_per_week"]:+.2f} kg/week'),
        ]
        story.append(make_key_value_table(plan_rows))
        story.append(Spacer(1, 3 * mm))
        story.append(make_data_table(plan["milestones"]))
        story.append(Spacer(1, 4 * mm))
        maybe_fig = plot_plan_chart(plan)
        if maybe_fig is not None:
            story.append(figure_image(maybe_fig, width_mm=176))
            story.append(Spacer(1, 3 * mm))

    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(
            "Disclaimer: educational demo only. Not clinically validated. For symptoms, worsening health, or emergency signs, seek professional help immediately.",
            small,
        )
    )

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
# Sidebar
# ----------------------------
st.sidebar.header("Modules")
run_bmi = st.sidebar.checkbox("BMI calculator", value=True)
run_vo2 = st.sidebar.checkbox("VO2max estimate", value=True)
run_bioage = st.sidebar.checkbox("Biological age", value=True)
run_symptom = st.sidebar.checkbox("Symptom checker", value=True)
run_plan = st.sidebar.checkbox("Weight goal / plan", value=True)

st.sidebar.markdown("---")
st.sidebar.info("This app does not store personal health data. It is for education and demonstration only.")


# ----------------------------
# Basic inputs
# ----------------------------
st.header("Basic information")

col1, col2 = st.columns(2)
with col1:
    age = st.number_input("Age (years)", min_value=0, max_value=120, value=30, step=1)
    sex = st.selectbox("Sex", options=["M", "F"], index=0)
with col2:
    height_cm = st.number_input("Height (cm)", min_value=50, max_value=250, value=170)
    weight_kg = st.number_input("Weight (kg)", min_value=20.0, max_value=300.0, value=70.0, format="%.1f")

if age < 18:
    st.warning("BMI and fitness estimates are less reliable under 18 because different reference rules are used.")
elif age >= 70:
    st.info("For older adults, BMI is often less informative because muscle mass, frailty and overall context matter.")

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
        use_waist_hip = st.checkbox("Add waist and hip measurements", value=False)
        if use_waist_hip:
            c1, c2 = st.columns(2)
            with c1:
                waist_cm = st.number_input("Waist circumference (cm)", min_value=30.0, max_value=300.0, value=80.0, format="%.1f", key="waist_bmi")
            with c2:
                hip_cm = st.number_input("Hip circumference (cm)", min_value=30.0, max_value=300.0, value=95.0, format="%.1f", key="hip_bmi")

        use_neck = st.checkbox("Add neck measurement for body-fat estimate", value=False)
        if use_neck:
            neck_cm = st.number_input("Neck circumference (cm)", min_value=20.0, max_value=80.0, value=38.0, format="%.1f", key="neck_bmi")

        bodyfat_requested = st.checkbox("Estimate body fat using the Navy method", value=False)


# ----------------------------
# VO2 inputs
# ----------------------------
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
        )
        weekly_minutes = st.number_input(
            "Weekly minutes of moderate-to-vigorous activity",
            min_value=0,
            max_value=2000,
            value=150,
        )
        session_intensity = st.slider(
            "Typical session intensity (1 = very light, 5 = very intense)",
            min_value=1,
            max_value=5,
            value=3,
        )
        # Unique keys added here
        resting_hr_unknown = st.checkbox("I don't know my resting heart rate", value=True, key="vo2_rhr_unknown")
        if not resting_hr_unknown:
            resting_hr = st.number_input("Resting heart rate (bpm)", min_value=30, max_value=220, value=70, key="vo2_rhr_value")
        max_hr_unknown = st.checkbox("I don't know my max heart rate", value=True, key="vo2_maxhr_unknown")
        if not max_hr_unknown:
            max_hr = st.number_input("Estimated max heart rate (bpm)", min_value=40, max_value=240, value=180, key="vo2_maxhr_value")

        measured_vo2_input = st.number_input(
            "If you know a measured VO2max (Apple Watch, lab, etc.), enter it here",
            min_value=0.0,
            value=0.0,
            format="%.1f",
        )

        vo2_method = st.selectbox(
            "VO2 calculation method",
            options=["Questionnaire", "Cooper (12-min)", "Rockport (1-mile)", "Measured value"],
            index=0,
        )

        if vo2_method == "Cooper (12-min)":
            vo2_distance_m = st.number_input("12-minute distance (meters)", min_value=0.0, value=0.0, format="%.1f", key="vo2_cooper_distance")
        elif vo2_method == "Rockport (1-mile)":
            rockport_time_min = st.number_input("1-mile time (minutes)", min_value=0.1, value=15.0, format="%.2f", key="vo2_rockport_time")
            rockport_hr = st.number_input("Heart rate at the end (bpm)", min_value=30, max_value=220, value=140, key="vo2_rockport_hr")
        elif vo2_method == "Measured value":
            measured_vo2_input = st.number_input(
                "Measured VO2max (ml/kg/min)",
                min_value=0.0,
                value=max(measured_vo2_input, 0.0),
                format="%.1f",
                key="vo2_measured_input",
            )
# ----------------------------
# Biological age inputs
# ----------------------------
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
            bp_systolic = st.number_input("Systolic blood pressure (mmHg)", min_value=70.0, max_value=260.0, value=120.0, key="bio_bp_value")

        chol_unknown = st.checkbox("I don't know my cholesterol", value=True, key="bio_chol_unknown")
        if not chol_unknown:
            cholesterol = st.number_input("Cholesterol (mg/dL)", min_value=50.0, max_value=500.0, value=180.0, key="bio_chol_value")

        rhr_unknown = st.checkbox("I don't know my resting heart rate", value=True, key="bio_rhr_unknown")
        if not rhr_unknown:
            resting_hr = st.number_input("Resting heart rate (bpm)", min_value=30, max_value=220, value=70, key="bio_rhr_value")

        st.markdown("#### Lifestyle")
        sleep_unknown = st.checkbox("I don't know my sleep duration", value=True, key="bio_sleep_unknown")
        if not sleep_unknown:
            sleep_hours = st.number_input("Average sleep per night (hours)", min_value=0.0, max_value=24.0, value=7.0, format="%.1f", key="bio_sleep_value")

        alcohol_unknown = st.checkbox("I don't know my alcohol intake", value=True, key="bio_alc_unknown")
        if not alcohol_unknown:
            alcohol_units = st.number_input("Alcohol units per week", min_value=0, max_value=300, value=0, key="bio_alc_value")

        fruit_veg = st.number_input("Daily fruit & vegetable servings", min_value=0, max_value=20, value=3, key="bio_fv")
        perceived_stress = st.slider("Perceived stress (1 low - 10 high)", min_value=1, max_value=10, value=5, key="bio_stress")

        grip_unknown = st.checkbox("I don't know my grip strength", value=True, key="bio_grip_unknown")
        if not grip_unknown:
            grip_strength = st.number_input("Grip strength (kg)", min_value=0.0, max_value=100.0, value=30.0, format="%.1f", key="bio_grip_value")

        st.markdown("#### Body composition")
        bio_waist_unknown = st.checkbox("I don't know my waist-to-hip ratio", value=True, key="bio_waist_unknown")
        if not bio_waist_unknown:
            c1, c2 = st.columns(2)
            with c1:
                waist_bio = st.number_input("Waist circumference for bio-age (cm)", min_value=30.0, max_value=300.0, value=80.0, format="%.1f", key="bio_waist_value")
            with c2:
                hip_bio = st.number_input("Hip circumference for bio-age (cm)", min_value=30.0, max_value=300.0, value=95.0, format="%.1f", key="bio_hip_value")
            if waist_cm is None:
                waist_cm = waist_bio
            if hip_cm is None:
                hip_cm = hip_bio
# ----------------------------
# Symptom checker
# ----------------------------
selected_symptoms = []
custom_symptom = ""

if run_symptom:
    with st.expander("Symptoms", expanded=True):
        st.markdown("Select symptoms below or type a custom one. Red-flag symptoms will trigger emergency advice.")
        selected_symptoms = st.multiselect(
            "Select symptoms",
            options=calculators.ALL_SYMPTOMS,
            default=[],
        )
        custom_symptom = st.text_input("Other symptom (free text)", "")
        if custom_symptom.strip():
            selected_symptoms = (selected_symptoms or []) + [custom_symptom.strip()]


# ----------------------------
# Weight goal / plan
# ----------------------------
create_plan = False
target_weight = None
target_bmi = None
plan_weeks = 12

if run_plan and run_bmi:
    with st.expander("Goal / plan", expanded=False):
        create_plan = st.checkbox("Create a simple plan to reach a target weight/BMI", value=False)
        if create_plan:
            plan_type = st.radio("Plan target type", ["Target weight (kg)", "Target BMI"], index=0)
            if plan_type == "Target weight (kg)":
                target_weight = st.number_input("Target weight (kg)", min_value=30.0, max_value=400.0, value=65.0, format="%.1f")
            else:
                target_bmi = st.number_input("Target BMI", min_value=12.0, max_value=45.0, value=22.0, format="%.1f")
            plan_weeks = st.number_input("Weeks to achieve target", min_value=4, max_value=52, value=12, step=1)


# ----------------------------
# Calculate
# ----------------------------
if st.button("Calculate / Generate report"):
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
                if bmi_value is None:
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
            results["vo2"] = {
                "value": vo2_value,
                "method": method_used,
                "age_band": vo2_ref["age_band"],
                "percentile": vo2_ref["percentile"],
                "rating": vo2_ref["rating"],
                "reference_mean": vo2_ref["mean"],
                "tips": vo2_tips,
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

        # Triage
        if run_symptom:
            triage_level, triage_message = calculators.triage_decision(
                selected_symptoms=selected_symptoms,
                red_flag_symptoms=calculators.DEFAULT_RED_FLAGS,
                risk_factors={"age": age, "diabetes": diabetes, "heart_disease": family_history},
            )
            results["triage"] = {"level": triage_level, "message": triage_message}

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
                results["plan"] = plan

    except Exception as e:
        st.error(f"Error during calculation: {e}")
        results = {}

    # ----------------------------
    # Display results
    # ----------------------------
    if results:
        st.success("Results ready")

        # BMI
        if "bmi" in results:
            st.subheader("BMI")
            b = results["bmi"]["value"]
            cat = results["bmi"]["category"]

            st.markdown(
                f"""
                <div style="padding:14px;border-radius:12px;background:#111827;color:#f9fafb;border:1px solid #334155;">
                    <div style="font-size:18px;font-weight:700;">BMI: {b}</div>
                    <div style="margin-top:6px;padding:6px 10px;display:inline-block;border-radius:8px;background:#1f2937;color:#fff;font-weight:700;">
                        {cat}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                """
                <div style="margin-top:10px;padding:12px;border-radius:12px;background:#0b1221;color:#e5eef8;border:1px solid #1f2937;">
                <strong>Note:</strong> BMI is a simple screening indicator. Muscle mass, bone density, fat distribution, age, pregnancy, and athletic status can affect how the number should be interpreted. 
                BMI is specifically less accurate for children/adolescents under 18 and for older adults.
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.pyplot(plot_bmi_gauge(b), use_container_width=True)
            plt.close("all")

            if "bodyfat" in results:
                st.write(f"Estimated body fat (Navy method): **{results['bodyfat']}%**")
            if "whr" in results:
                st.write(f"Waist-to-hip ratio: **{results['whr']['value']}** — {results['whr']['category']}")

        # VO2
        if "vo2" in results:
            st.subheader("VO2max estimate")
            vo2 = results["vo2"]
            st.metric("VO2max", f"{vo2['value']:.1f} ml/kg/min")
            st.write(f"Method: **{vo2['method']}**")
            st.write(f"Age band: **{vo2['age_band']}**")
            st.write(f"Estimated population percentile: **{vo2['percentile']}th**")
            st.write(f"Reference rating: **{vo2['rating']}**")

            st.pyplot(plot_vo2_reference_chart(vo2["value"], sex, age), use_container_width=True)
            plt.close("all")

            st.markdown("**VO2 reference table by age**")
            st.table(calculators.vo2_age_reference_table(sex))

            st.markdown("**Tips to improve VO2max**")
            for tip in vo2["tips"]:
                st.write(f"- {tip}")

        # Biological age
        if "bio_age" in results:
            st.subheader("Biological age")
            st.metric("Biological age", f"{results['bio_age']['value']} years")

            if results.get("bio_factors"):
                st.markdown("**Factor breakdown**")
                factor_rows = [
                    {"Factor": f["label"], "Effect": f'{f["delta"]:+.0f} years'}
                    for f in results["bio_factors"]
                ]
                st.table(factor_rows)

        # Triage
        if "triage" in results:
            st.subheader("Symptom triage")
            if results["triage"]["level"] == "Emergency":
                st.error(results["triage"]["message"])
            else:
                st.info(f"{results['triage']['level']}: {results['triage']['message']}")

        # Plan
        if "plan" in results:
            st.subheader("Weight goal / plan")
            plan = results["plan"]
            st.write(f"Current maintenance calories: **{plan['current_needs_kcal']} kcal/day**")
            st.write(f"Recommended daily calories: **{plan['recommended_daily_kcal']} kcal/day**")
            st.write(f"Expected weekly change: **{plan['kg_per_week']:+.2f} kg/week**")

            if plan.get("warning"):
                st.warning(plan["warning"])

            st.markdown("**Condensed milestones**")
            st.table(plan["milestones"])

        # PDF
        report = {
            "generated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "inputs": {
                "age": age,
                "sex": sex,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
            },
            "bmi": results.get("bmi"),
            "bodyfat": results.get("bodyfat"),
            "whr": results.get("whr"),
            "vo2": results.get("vo2"),
            "bio_age": results.get("bio_age"),
            "bio_factors": results.get("bio_factors"),
            "triage": results.get("triage"),
            "plan": results.get("plan"),
        }

        try:
            pdf_bytes = create_pdf_bytes(report)
            st.download_button(
                "Download PDF report",
                data=pdf_bytes,
                file_name="health_tools_report.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.warning(f"PDF generation is currently unavailable: {e}")

    else:
        st.warning("No results to show.")
