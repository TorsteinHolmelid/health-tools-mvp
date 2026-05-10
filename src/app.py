# src/app.py
import streamlit as st
from io import BytesIO
from datetime import datetime
import calculators
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Health Tools MVP", layout="centered")
st.title("Health Tools — MVP")
st.markdown("**Educational tool — not a diagnostic tool.** This app is for demonstration only.")

# --- Sidebar: choose which modules to run ---
st.sidebar.header("Modules")
run_bmi = st.sidebar.checkbox("BMI calculator", value=True)
run_vo2 = st.sidebar.checkbox("VO2 estimate (Cooper / heuristic)", value=False)
run_bioage = st.sidebar.checkbox("Biological age", value=False)
run_symptom = st.sidebar.checkbox("Symptom checker", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("Settings")
bioage_mode = st.sidebar.selectbox("Biological age mode", ["Quick (fun)", "Detailed"], index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("Disclaimer: Data is NOT stored. This is not medical advice.")

# --- Main form sections ---
st.header("Inputs")

# Shared basic info
with st.expander("Basic info (required for most calculators)", expanded=True):
    age = st.number_input("Age (years)", min_value=0, max_value=120, value=30, step=1)
    sex = st.selectbox("Sex", options=["M", "F"])
    height_cm = st.number_input("Height (cm)", min_value=50, max_value=250, value=170)
    weight_kg = st.number_input("Weight (kg)", min_value=20.0, max_value=300.0, value=70.0, format="%.1f")

# VO2 inputs
vo2_distance_m = None
activity_level = "medium"
if run_vo2 or run_bioage:
    with st.expander("Activity & cardiopulmonary inputs", expanded=False):
        activity_level = st.selectbox("Physical activity level", options=["low", "medium", "high"], index=1)
        if run_vo2:
            st.markdown("VO2 (Cooper) option: enter distance (meters) covered in 12 minutes (optional).")
            vo2_distance_m = st.number_input("12-min Cooper distance (meters, optional)", min_value=0.0, value=0.0, format="%.1f")

# Biological age detailed inputs
systolic_bp = None; cholesterol = None; diabetes = False; resting_hr = None
if run_bioage and bioage_mode == "Detailed":
    with st.expander("Detailed biological age inputs", expanded=False):
        diabetes = st.checkbox("Diabetes?")
        systolic_bp = st.number_input("Systolic BP (mmHg) - optional", value=120.0)
        cholesterol = st.number_input("Cholesterol (mg/dL) - optional", value=180.0)
        resting_hr = st.number_input("Resting heart rate (bpm) - optional", min_value=30, max_value=200, value=70)

# Symptom inputs
selected_symptoms = []
if run_symptom:
    with st.expander("Symptoms", expanded=False):
        st.markdown("Select all symptoms that apply. Red-flag symptoms are at top.")
        # red flags
        for s in calculators.RED_FLAG_SYMPTOMS:
            if st.checkbox(f"🔴 {s}", key=f"rf_{s}"):
                selected_symptoms.append(s)
        st.markdown("Other symptoms")
        for s in calculators.COMMON_SYMPTOMS:
            if st.checkbox(s, key=f"s_{s}"):
                selected_symptoms.append(s)

# Run / Compute button
if st.button("Calculate / Generate results"):
    results = {}
    # BMI
    try:
        if run_bmi:
            bmi, bmi_cat = calculators.bmi_calc(weight_kg, height_cm)
            results['bmi'] = {'value': bmi, 'category': bmi_cat}
        # VO2
        if run_vo2:
            if vo2_distance_m and vo2_distance_m > 0:
                vo2 = calculators.vo2_cooper_from_distance(vo2_distance_m)
                results['vo2'] = {'method': 'Cooper 12-min', 'value': vo2}
            else:
                # fallback heuristic
                # compute BMI if not yet
                if 'bmi' not in results:
                    bmi, _ = calculators.bmi_calc(weight_kg, height_cm)
                vo2 = calculators.vo2_simple_heuristic(age, sex, bmi, activity_level)
                results['vo2'] = {'method': 'Heuristic', 'value': vo2}
        # Biological age
        if run_bioage:
            if bioage_mode == "Quick (fun)":
                if 'bmi' not in results:
                    bmi, _ = calculators.bmi_calc(weight_kg, height_cm)
                bio_age = calculators.estimate_biological_age_quick(age, False, bmi, activity_level)
                results['bio_age'] = {'mode': 'quick', 'value': bio_age}
            else:
                if 'bmi' not in results:
                    bmi, _ = calculators.bmi_calc(weight_kg, height_cm)
                bio_age = calculators.estimate_biological_age_detailed(
                    age, False, bmi, activity_level,
                    systolic_bp=systolic_bp, diabetes=diabetes,
                    cholesterol_mg_dl=cholesterol, resting_hr=resting_hr
                )
                results['bio_age'] = {'mode': 'detailed', 'value': bio_age}
        # Symptom triage
        if run_symptom:
            rf_set = set([s.lower() for s in calculators.RED_FLAG_SYMPTOMS])
            advice_level, advice_message = calculators.triage_decision(
                selected_symptoms,
                red_flag_symptoms=rf_set,
                risk_factors={'age': age, 'diabetes': diabetes}
            )
            results['triage'] = {'level': advice_level, 'message': advice_message}
    except Exception as e:
        st.error(f"Error during calculation: {e}")
        results = None

    # Show results
    if results:
        st.success("Results ready")
        if 'bmi' in results:
            st.metric("BMI", f"{results['bmi']['value']}", results['bmi']['category'])
        if 'vo2' in results:
            st.write(f"VO2 estimate ({results['vo2']['method']}): **{results['vo2']['value']} ml/kg/min**")
        if 'bio_age' in results:
            st.write(f"Biological age ({results['bio_age']['mode']}): **{results['bio_age']['value']} years**")
        if 'triage' in results:
            if results['triage']['level'] == "Emergency":
                st.error(f"RED FLAG: {results['triage']['message']}")
            else:
                st.info(f"{results['triage']['level']}: {results['triage']['message']}")

        # Prepare PDF content (only include sections present in results)
        def create_pdf_bytes(context: dict, included_sections: list):
            buf = BytesIO()
            p = canvas.Canvas(buf, pagesize=A4)
            y = 800
            p.setFont("Helvetica-Bold", 14)
            p.drawString(40, y, "Health Tools — Report")
            p.setFont("Helvetica", 9)
            y -= 20
            p.drawString(40, y, f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
            y -= 20
            p.drawString(40, y, f"Age: {age}  Sex: {sex}  Height(cm): {height_cm}  Weight(kg): {weight_kg}")
            y -= 30

            if 'bmi' in included_sections:
                p.setFont("Helvetica-Bold", 11)
                p.drawString(40, y, "BMI")
                p.setFont("Helvetica", 10)
                y -= 16
                p.drawString(60, y, f"BMI: {context['bmi']['value']} ({context['bmi']['category']})")
                y -= 20

            if 'vo2' in included_sections:
                p.setFont("Helvetica-Bold", 11)
                p.drawString(40, y, "VO2 Estimate")
                p.setFont("Helvetica", 10)
                y -= 16
                p.drawString(60, y, f"Method: {context['vo2']['method']}   VO2: {context['vo2']['value']} ml/kg/min")
                y -= 20

            if 'bio_age' in included_sections:
                p.setFont("Helvetica-Bold", 11)
                p.drawString(40, y, "Biological Age")
                p.setFont("Helvetica", 10)
                y -= 16
                p.drawString(60, y, f"Mode: {context['bio_age']['mode']}   Biological age: {context['bio_age']['value']} years")
                y -= 20

            if 'triage' in included_sections:
                p.setFont("Helvetica-Bold", 11)
                p.drawString(40, y, "Symptom Triage")
                p.setFont("Helvetica", 10)
                y -= 16
                p.drawString(60, y, f"Level: {context['triage']['level']}")
                y -= 14
                # wrap long message
                message = context['triage']['message']
                p.drawString(60, y, f"Message: {message}")
                y -= 24

            p.setFont("Helvetica-Oblique", 7)
            p.drawString(40, 40, "Disclaimer: This tool is for educational/demo purposes only. Not clinically validated.")
            p.showPage()
            p.save()
            buf.seek(0)
            return buf.read()

        # Build context + included sections
        included = []
        context = {}
        if 'bmi' in results:
            included.append('bmi')
            context['bmi'] = {'value': results['bmi']['value'], 'category': results['bmi']['category']}
        if 'vo2' in results:
            included.append('vo2')
            context['vo2'] = {'method': results['vo2']['method'], 'value': results['vo2']['value']}
        if 'bio_age' in results:
            included.append('bio_age')
            context['bio_age'] = {'mode': results['bio_age']['mode'], 'value': results['bio_age']['value']}
        if 'triage' in results:
            included.append('triage')
            context['triage'] = {'level': results['triage']['level'], 'message': results['triage']['message']}

        pdf_bytes = create_pdf_bytes(context, included)
        st.download_button("Download PDF report", data=pdf_bytes, file_name="health_report.pdf", mime="application/pdf")
    else:
        st.warning("No results to show.")
