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

# --------------------
# Helper functions
# --------------------

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
        ax.barh(0.5, end - start, left=start, height=0.6, color=color, edgecolor='none')

    # Marker
    marker_x = min(max(bmi_value, 0), max_bmi)
    ax.scatter([marker_x], [0.5], marker='v', s=200, color='black', zorder=5)

    # A lightweight label above marker
    # choose label color that contrasts typical dark theme (white) or fallback to black
    label_color = 'white' if plt.rcParams.get('axes.facecolor', '#FFFFFF') != '#FFFFFF' else 'black'
    ax.text(marker_x, 1.05, f"{bmi_value:.1f}", ha='center', va='bottom', fontsize=10, color=label_color)

    # Cosmetic cleanup
    ax.set_xlim(0, max_bmi)
    ax.set_ylim(0, 1.3)
    ax.set_yticks([])
    ax.set_xticks([0, 10, 18.5, 25, 30, 40])
    ax.set_xlabel("BMI")
    for spine in ax.spines.values():
        spine.set_visible(False)
    plt.tight_layout()
    return fig

# --------------------
# Sidebar: choose which modules to run
# --------------------
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

# --------------------
# Inputs
# --------------------
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
            bmi_extras['request_bodyfat'] = True

# Activity & VO2
vo2_distance_m = None
activity_level = "medium"
if run_vo2 or run_bioage:
    with st.expander("Activity & cardiopulmonary inputs", expanded=False):
        activity_level = st.selectbox("Physical activity level", options=["low", "medium", "high"], index=1)
        if run_vo2:
            st.markdown("VO2 options: choose a method and provide inputs for that method.")
            vo2_method = st.selectbox("VO2 method", options=["Heuristic (questionnaire)", "Cooper (12-min)", "Rockport (1-mile)"], index=0)
            if vo2_method == "Cooper (12-min)":
                vo2_distance_m = st.number_input("12-min Cooper distance (meters)", min_value=0.0, value=0.0, format="%.1f")
            elif vo2_method == "Rockport (1-mile)":
                rockport_time_min = st.number_input("Rockport 1-mile time (minutes, e.g. 15.5)", min_value=0.1, value=15.0, format="%.2f")
                rockport_hr = st.number_input("Heart rate at end (bpm)", min_value=30, max_value=220, value=140)
            else:
                weekly_minutes = st.number_input("Weekly MVPA minutes (moderate-vigorous)", min_value=0, max_value=2000, value=150)
                session_intensity = st.slider("Typical session intensity (1=very light .. 5=very intense)", min_value=1, max_value=5, value=3)

# Detailed bio-age inputs
systolic_bp = None; cholesterol = None; diabetes = False; resting_hr = None
sleep_hours = None; alcohol_units = None; fruit_veg = None; perceived_stress = None; grip_strength = None
if run_bioage:
    with st.expander("Biological age inputs (optional)", expanded=False):
        smoker = st.checkbox("Smoker?")
        if bioage_mode == "Detailed":
            diabetes = st.checkbox("Diabetes?")
            systolic_bp = st.number_input("Systolic BP (mmHg) - optional", value=120.0)
            cholesterol = st.number_input("Cholesterol (mg/dL) - optional", value=180.0)
            resting_hr = st.number_input("Resting heart rate (bpm) - optional", min_value=30, max_value=200, value=70)
            sleep_hours = st.number_input("Average sleep per night (hours) - optional", min_value=0.0, max_value=24.0, value=7.0, format="%.1f")
            alcohol_units = st.number_input("Alcohol units per week - optional", min_value=0, max_value=200, value=0)
            fruit_veg = st.number_input("Daily fruit & veg servings (approx) - optional", min_value=0, max_value=20, value=3)
            perceived_stress = st.slider("Perceived stress (1 low - 10 high)", min_value=1, max_value=10, value=5)
            grip_strength = st.number_input("Grip strength (kg) - optional", min_value=0.0, max_value=100.0, value=30.0, format="%.1f")
        else:
            # quick mode minimal optional inputs
            smoker = st.checkbox("Smoker?")

# Symptoms
selected_symptoms = []
if run_symptom:
    with st.expander("Symptoms (search or pick)", expanded=False):
        st.markdown("Type to search symptoms or pick from the list. You can also add custom symptoms below.")
        all_symptoms = getattr(calculators, "ALL_SYMPTOMS", calculators.COMMON_SYMPTOMS + list(calculators.DEFAULT_RED_FLAGS))
        selected_symptoms = st.multiselect("Select symptoms", options=sorted(all_symptoms), default=None, key="multi_symptoms")
        custom_symptom = st.text_input("Other symptoms (free text)", "")
        if custom_symptom:
            selected_symptoms = (selected_symptoms or []) + [custom_symptom]

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

# --------------------
# Compute & Results
# --------------------
if st.button("Calculate / Generate results"):
    results = {}
    try:
        # BMI
        if run_bmi:
            bmi, bmi_cat = calculators.bmi_calc(weight_kg, height_cm)
            results['bmi'] = {'value': bmi, 'category': bmi_cat}
