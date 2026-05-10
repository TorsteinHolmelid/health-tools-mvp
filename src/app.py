# src/app.py
import streamlit as st
from io import BytesIO
from datetime import datetime
import calculators
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import matplotlib.pyplot as plt

st.set_page_config(page_title="Health Tools MVP", layout="centered")
st.title("Health Tools — MVP")
st.markdown("**Educational tool — not a diagnostic tool.** This app is for demonstration only. Consult a healthcare professional for clinical advice.")

# Sidebar module selection
st.sidebar.header("Modules")
run_bmi = st.sidebar.checkbox("BMI calculator", value=True)
run_vo2 = st.sidebar.checkbox("VO2 estimate (Cooper / heuristic)", value=False)
run_bioage = st.sidebar.checkbox("Biological age", value=False)
run_symptom = st.sidebar.checkbox("Symptom checker", value=True)

st.sidebar.markdown("---")
st.sidebar.header("Settings")
bioage_mode = st.sidebar.selectbox("Biological age mode", ["Quick (fun)", "Detailed"], index=0)
st.sidebar.markdown("Disclaimer: Data is NOT stored. This is not medical advice.")

# Visual cue for active modules
active = [name for name, enabled in [
    ("BMI", run_bmi), ("VO2", run_vo2), ("Bio-age", run_bioage), ("Symptoms", run_symptom)
] if enabled]
if active:
    st.info(f"Active modules: {', '.join(active)}")

# --- Inputs ---
st.header("Inputs")

with st.expander("Basic info (required for many calculations)", expanded=True):
    age = st.number_input("Age (years)", min_value=0, max_value=120, value=30, step=1)
    sex = st.selectbox("Sex", options=["M", "F"])
    height_cm = st.number_input("Height (cm)", min_value=50, max_value=250, value=170)
    weight_kg = st.number_input("Weight (kg)", min_value=20.0, max_value=300.0, value=70.0, format="%.1f")

# BMI optional extras
bmi_extras = {}
if run_bmi:
    with st.expander("BMI extra options (optional — checking these gives more accurate assessment)", expanded=False):
        use_waist_hip = st.checkbox("Provide waist & hip (waist-to-hip ratio)")
        if use_waist_hip:
            waist_cm = st.number_input("Waist circumference (cm)", min_value=30.0, max_value=300.0, value=80.0, key="waist")
            hip_cm = st.number_input("Hip circumference (cm)", min_value=30.0, max_value=300.0, value=95.0, key="hip")
            bmi_extras['waist_cm'] = waist_cm
            bmi_extras['hip_cm'] = hip_cm
        use_neck = st.checkbox("Provide neck circumference (for body fat estimate)")
        if use_neck:
            neck_cm = st.number_input("Neck circumference (cm)", min_value=20.0, max_value=80.0, value=38.0, key="neck")
            bmi_extras['neck_cm'] = neck_cm
        use_bodyfat = st.checkbox("Request body-fat estimate (Navy method) — optional")
        if use_bodyfat:
            # navy requires neck + waist (+ hip for females)
            bmi_extras['request_bodyfat'] = True

# Activity & VO2
vo2_distance_m = None
activity_level = "medium"
if run_vo2 or run_bioage:
    with st.expander("Activity & cardiopulmonary inputs", expanded=False):
        activity_level = st.selectbox("Physical activity level", options=["low", "medium", "high"], index=1)
        if run_vo2:
            st.markdown("VO2 (Cooper) option: enter distance (meters) covered in 12 minutes (optional).")
            vo2_distance_m = st.number_input("12-min Cooper distance (meters, optional)", min_value=0.0, value=0.0, format="%.1f")

# Detailed bio-age inputs
systolic_bp = None; cholesterol = None; diabetes = False; resting_hr = None
if run_bioage and bioage_mode == "Detailed":
    with st.expander("Detailed biological age inputs", expanded=False):
        diabetes = st.checkbox("Diabetes?")
        systolic_bp = st.number_input("Systolic BP (mmHg) - optional", value=120.0)
        cholesterol = st.number_input("Cholesterol (mg/dL) - optional", value=180.0)
        resting_hr = st.number_input("Resting heart rate (bpm) - optional", min_value=30, max_value=200, value=70)

# Symptoms
selected_symptoms = []
if run_symptom:
    with st.expander("Symptoms (select all that apply)", expanded=False):
        st.markdown("Red flags first")
        for s in calculators.DEFAULT_RED_FLAGS:
            if st.checkbox(f"🔴 {s}", key=f"rf_{s}"):
                selected_symptoms.append(s)
        st.markdown("Other symptoms")
        for s in calculators.COMMON_SYMPTOMS:
            if st.checkbox(s, key=f"s_{s}"):
                selected_symptoms.append(s)

# Option: create plan after BMI
create_plan = False
target_weight = None
target_bmi = None
plan_weeks = 12
if run_bmi:
    with st.expander("Goal / Plan (optional)", expanded=False):
        create_plan = st.checkbox("Create a simple plan to reach a target weight/BMI", value=False)
        if create_plan:
            plan_type = st.radio("Plan target type", ["Target weight (kg)", "Target BMI"], index=0)
            if plan_type.startswith("Target weight"):
                target_weight = st.number_input("Target weight (kg)", min_value=30.0, max_value=300.0, value=65.0)
            else:
                target_bmi = st.number_input("Target BMI", min_value=12.0, max_value=40.0, value=22.0)
            plan_weeks = st.number_input("Weeks to achieve target", min_value=4, max_value=52, value=12)

# --- Compute button ---
if st.button("Calculate / Generate results"):
    results = {}
    try:
        # BMI
        if run_bmi:
            bmi, bmi_cat = calculators.bmi_calc(weight_kg, height_cm)
            results['bmi'] = {'value': bmi, 'category': bmi_cat}
            # extras
            extras_used = 0
            if bmi_extras.get('waist_cm') and bmi_extras.get('hip_cm'):
                ratio = calculators.waist_hip_ratio(bmi_extras['waist_cm'], bmi_extras['hip_cm'])
                whr_cat = calculators.whr_category(sex, ratio)
                results['whr'] = {'ratio': ratio, 'category': whr_cat}
                extras_used += 1
            if bmi_extras.get('neck_cm'):
                # if user wants bodyfat and provided required fields:
                if bmi_extras.get('request_bodyfat'):
                    if sex == 'M':
                        bf = calculators.body_fat_navy(sex, height_cm, bmi_extras['neck_cm'], bmi_extras.get('waist_cm', 0))
                    else:
                        bf = calculators.body_fat_navy(sex, height_cm, bmi_extras['neck_cm'], bmi_extras.get('waist_cm', 0), bmi_extras.get('hip_cm', None))
                    results['bodyfat'] = {'value': bf}
                    extras_used += 1
            results['bmi']['extras_used'] = extras_used

        # VO2
        if run_vo2:
            if vo2_distance_m and vo2_distance_m > 0:
                vo2 = calculators.vo2_cooper_from_distance(vo2_distance_m)
                results['vo2'] = {'method': 'Cooper 12-min', 'value': vo2}
            else:
                if 'bmi' not in results:
                    bmi, _ = calculators.bmi_calc(weight_kg, height_cm)
                else:
                    bmi = results['bmi']['value']
                vo2 = calculators.vo2_simple_heuristic(age, sex, bmi, activity_level)
                results['vo2'] = {'method': 'Heuristic', 'value': vo2}

        # Bio-age
        if run_bioage:
            if 'bmi' not in results:
                bmi, _ = calculators.bmi_calc(weight_kg, height_cm)
            else:
                bmi = results['bmi']['value']
            if bioage_mode == "Quick (fun)":
                bio_age = calculators.estimate_biological_age_quick(age, False, bmi, activity_level)
                results['bio_age'] = {'mode': 'quick', 'value': bio_age}
            else:
                bio_age = calculators.estimate_biological_age_detailed(
                    age, False, bmi, activity_level,
                    systolic_bp=systolic_bp, diabetes=diabetes,
                    cholesterol_mg_dl=cholesterol, resting_hr=resting_hr
                )
                results['bio_age'] = {'mode': 'detailed', 'value': bio_age}

        # Triage
        if run_symptom:
            advice_level, advice_message = calculators.triage_decision(
                selected_symptoms,
                red_flag_symptoms=set([s.lower() for s in calculators.DEFAULT_RED_FLAGS]),
                risk_factors={'age': age, 'diabetes': diabetes}
            )
            results['triage'] = {'level': advice_level, 'message': advice_message}

    except Exception as e:
        st.error(f"Error during calculation: {e}")
        results = None

    # --- Show results ---
    if results:
        st.success("Results ready")
        # BMI section: gauge + details
        if 'bmi' in results:
            b = results['bmi']['value']
            cat = results['bmi']['category']
            st.subheader("BMI")
            st.metric("BMI", f"{b}", cat)
            extras_note = f"Extras used for assessment: {results['bmi'].get('extras_used', 0)}"
            st.caption(extras_note)

            # plot gauge
import matplotlib.pyplot as plt

def plot_bmi_gauge(bmi_value):
    """
    Draw a horizontal colored BMI bar with a marker.
    Transparent figure background so it looks good in dark mode.
    """
    max_bmi = 45
    fig, ax = plt.subplots(figsize=(7, 1.2))
    # Transparent backgrounds so it adapts to Streamlit theme
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    # colored bands and labels
    bands = [
        (0, 18.5, "#2196F3"),   # underweight (blue)
        (18.5, 25, "#4CAF50"),  # normal (green)
        (25, 30, "#FFB300"),    # overweight (amber)
        (30, max_bmi, "#E91E63")# obesity (pink/red)
    ]
    for start, end, color in bands:
        ax.barh(0.4, end - start, left=start, height=0.6, color=color, edgecolor='none')

    # Marker
    marker_x = min(max(bmi_value, 0), max_bmi)
    ax.scatter([marker_x], [0.7], marker='v', s=200, color='black', zorder=5)

    # A lightweight label above marker
    ax.text(marker_x, 1.15, f"{bmi_value:.1f}", ha='center', va='bottom', fontsize=10, color='white' if plt.rcParams.get('axes.facecolor') != 'white' else 'black')

    # Cosmetic cleanup
    ax.set_xlim(0, max_bmi)
    ax.set_ylim(0, 1.5)
    ax.set_yticks([])
    ax.set_xticks([0, 10, 18.5, 25, 30, 40])
    ax.set_xlabel("BMI")
    for spine in ax.spines.values():
        spine.set_visible(False)
    plt.tight_layout()
    return fig

            fig = plot_bmi_gauge(b)
            st.pyplot(fig)

            # Extra interpretations
            if 'bodyfat' in results:
                st.write(f"Estimated body fat (Navy method): **{results['bodyfat']['value']}%** (approx.)")
            if 'whr' in results:
                st.write(f"Waist-to-hip ratio: **{results['whr']['ratio']}** — {results['whr']['category']}")

            # Plan option (generate)
            if create_plan:
                # determine target weight if target_bmi provided
                if target_bmi:
                    # compute target weight from BMI: weight = BMI * height_m^2
                    target_weight = target_bmi * (height_cm / 100.0) ** 2
                plan = calculators.generate_weight_plan(weight_kg, target_weight, int(plan_weeks), sex, height_cm, age, activity_level)
                st.subheader("Suggested plan summary")
                st.write(f"Current daily maintenance kcal (estimate): **{plan['current_needs_kcal']} kcal/day**")
                st.write(f"Recommended daily kcal to meet goal: **{plan['recommended_daily_kcal']} kcal/day**")
                st.write(f"Planned weekly weight change (kg/week): **{plan['kg_per_week']:.2f}**")
                if plan['warning']:
                    st.warning(plan['warning'])
                st.markdown("Weekly steps (sample):")
                for s in plan['weekly_steps']:
                    st.write(f"- {s}")
                st.info("This is a simple, educational plan. Consult a dietitian or doctor before making large changes to diet/exercise.")

        # VO2
        if 'vo2' in results:
            st.subheader("VO2 estimate")
            st.write(f"Method: {results['vo2']['method']}")
            st.metric("VO2 (ml/kg/min)", f"{results['vo2']['value']}")

        # Bio-age
        if 'bio_age' in results:
            st.subheader("Biological age (estimate)")
            st.write(f"Mode: {results['bio_age']['mode']}")
            st.metric("Biological age", f"{results['bio_age']['value']} years")

        # Triage
        if 'triage' in results:
            st.subheader("Symptom triage")
            if results['triage']['level'] == "Emergency":
                st.error(results['triage']['message'])
            else:
                st.info(f"{results['triage']['level']}: {results['triage']['message']}")

        # Build PDF with only included sections
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
                if 'bodyfat' in context:
                    p.drawString(60, y, f"Estimated body fat: {context['bodyfat']['value']}%")
                    y -= 16
                if 'whr' in context:
                    p.drawString(60, y, f"Waist-to-hip ratio: {context['whr']['ratio']} ({context['whr']['category']})")
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
                message = context['triage']['message']
                p.drawString(60, y, f"Message: {message}")
                y -= 24
            p.setFont("Helvetica-Oblique", 7)
            p.drawString(40, 40, "Disclaimer: This tool is for educational/demo purposes only. Not clinically validated. Consult a healthcare professional.")
            p.showPage()
            p.save()
            buf.seek(0)
            return buf.read()

        # prepare PDF context
        included = []
        context = {}
        if 'bmi' in results:
            included.append('bmi')
            context['bmi'] = {'value': results['bmi']['value'], 'category': results['bmi']['category']}
            if 'bodyfat' in results:
                context['bodyfat'] = {'value': results['bodyfat']['value']}
            if 'whr' in results:
                context['whr'] = {'ratio': results['whr']['ratio'], 'category': results['whr']['category']}
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
