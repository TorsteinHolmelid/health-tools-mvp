# src/app.py
import io
import math
from math import erf, sqrt
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import traceback
import streamlit as st

# Temporær diagnostikk for å fange ImportError og vise full traceback i appen/loggene
try:
    from calculators import (
        bmr_mifflin,
        tdee_from_activity_factor,
        calories_burned_from_mets,
        weekly_exercise_calories,
        tdee_including_weekly_exercise,
    )
except Exception as e:
    # Vis enkel beskjed i UI så du slipper å gå rett til logs
    st.error("Import-feil ved lasting av calculators.py — se under for full traceback.")
    st.text(str(e))
    st.text("Full traceback:")
    st.text(traceback.format_exc())
    # Re-raise så Streamlit logger feilen også til sine logs
    raise


# --- Page config and dark-theme CSS (legg dette rett etter set_page_config) ---
st.set_page_config(page_title="Health Tools MVP", layout="centered", initial_sidebar_state="expanded")

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

    /* Knapper */
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

    /* Plotly container (for lys tekst på ticks) */
    .js-plotly-plot .xtick text, .js-plotly-plot .ytick text {
      fill: #e6eef8 !important;
    }

    /* Mobil: knapper 100% breidde */
    @media (max-width: 600px) {
      .stButton>button { width: 100% !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Helper: Plotly components ---

def percentile_strip(user_pct):
    fig = go.Figure()

    # bakgrunnstrip
    fig.add_trace(go.Bar(
        x=[100],
        y=[""],
        orientation='h',
        marker=dict(color='rgba(255,255,255,0.06)'),
        showlegend=False,
        hoverinfo='none'
    ))

    # bruker markør
    fig.add_trace(go.Scatter(
        x=[user_pct],
        y=[0],
        mode='markers+text',
        marker=dict(color='#ffb86b', size=16),
        text=[f"{user_pct:.1f}th percentile"],
        textposition='bottom center',
        textfont=dict(color='#e6eef8', size=12),
        showlegend=False
    ))

    fig.update_layout(
        height=120,
        margin=dict(l=12, r=12, t=8, b=24),
        xaxis=dict(
            range=[0, 100],
            tickmode='array',
            tickvals=[0, 10, 25, 50, 75, 90, 95, 99],
            ticktext=['0','10','25','50','75','90','95','99'],
            showgrid=True,
            gridcolor='rgba(255,255,255,0.04)',
            zeroline=False,
            tickfont=dict(color='#e6eef8')
        ),
        yaxis=dict(showticklabels=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def vo2_age_bars(age_bins, ref_values, user_age_bin_index, user_vo2):
    colors = ['rgba(94,169,255,0.95)'] * len(ref_values)
    highlight_color = 'rgba(255,184,107,0.98)'
    if 0 <= user_age_bin_index < len(colors):
        colors[user_age_bin_index] = highlight_color

    text_colors = ['#e6eef8'] * len(ref_values)
    if 0 <= user_age_bin_index < len(text_colors):
        text_colors[user_age_bin_index] = '#022b2a'  # mørk text på den lyse highlight

    fig = go.Figure(go.Bar(
        x=age_bins,
        y=ref_values,
        marker_color=colors,
        text=[f"{v:.0f}" for v in ref_values],
        textposition='outside',
        textfont=dict(color=text_colors, size=12),
    ))

    # legg til horisontal linje for brukerens verdi
    fig.add_hline(y=user_vo2, line_dash="dash", line_color="#ff6b6b",
                  annotation_text=f"Your VO2: {user_vo2:.1f}", annotation_position="top right",
                  annotation_font_color="#ffb86b", annotation_bgcolor='rgba(0,0,0,0.2)')

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis_title="VO2max (ml/kg/min)",
        margin=dict(l=40, r=20, t=30, b=40),
        height=360,
    )
    return fig


# --- Small utility: percentile from normal approx (without scipy) ---
def normal_cdf(x, mu=0, sigma=1):
    # CDF via error function
    z = (x - mu) / (sigma * sqrt(2))
    return 0.5 * (1 + erf(z))

def vo2_percentile_from_ref(user_vo2, ref_mean, ref_sd=6.0):
    # returns percentile (0-100)
    pct = normal_cdf(user_vo2, ref_mean, ref_sd) * 100
    return max(0.0, min(100.0, pct))


# --- App UI and logic ---

# Sidebar options
st.sidebar.header("Modules")
modules = {
    "BMI calculator": st.sidebar.checkbox("BMI calculator", value=True),
    "VO2max estimate": st.sidebar.checkbox("VO2max estimate", value=True),
    "Biological age": st.sidebar.checkbox("Biological age", value=True),
    "Conditions & recommendations": st.sidebar.checkbox("Conditions & recommendations", value=True),
    "Weight goal / plan": st.sidebar.checkbox("Weight goal / plan", value=True),
}

st.sidebar.markdown(
    """
    <div style="background:#123047; padding:10px; border-radius:8px; color:#e6f6ff">
    This app does not store personal health data. It is for education and demonstration only.
    </div>
    """,
    unsafe_allow_html=True
)

# Single title (only one)
st.title("Health Tools — MVP")
st.write("Educational tool only — not a diagnostic tool. Data is not stored.")

# --- Basic information inputs ---
st.header("Basic information")

col1, col2 = st.columns([1,1])
with col1:
    age = st.number_input("Age (years)", min_value=5, max_value=120, value=30)
    sex = st.selectbox("Sex", options=["M", "F"])
    activity_level = st.selectbox("Physical activity level", options=["sedentary","light","moderate","very","extra"], index=2)
with col2:
    height_cm = st.number_input("Height (cm)", min_value=50, max_value=250, value=170)
    weight_kg = st.number_input("Weight (kg)", min_value=20.0, max_value=300.0, value=70.0, format="%.1f")

st.markdown("")  # spacing

# --- BMI module ---
if modules["BMI calculator"]:
    st.subheader("BMI")
    bmi = weight_kg / ((height_cm/100.0)**2) if height_cm > 0 else 0
    bmi_cat = "Unknown"
    if bmi > 0:
        if bmi < 18.5: bmi_cat = "Underweight"
        elif bmi < 25: bmi_cat = "Normal"
        elif bmi < 30: bmi_cat = "Overweight"
        else: bmi_cat = "Obesity"
    st.markdown(f'<div class="result-box"><strong>BMI:</strong> {bmi:.1f} — {bmi_cat}</div>', unsafe_allow_html=True)

# --- VO2 module ---
user_vo2 = None
user_percentile = None
if modules["VO2max estimate"]:
    st.subheader("VO2max")
    vo2_method = st.selectbox("Method", options=["Measured value", "Simple estimate"], index=1)

    if vo2_method == "Measured value":
        user_vo2 = st.number_input("Measured VO2 (ml/kg/min)", min_value=1.0, max_value=100.0, value=38.2, format="%.1f")
    else:
        # Very simple heuristic estimate based on activity_level and age/sex
        base_by_activity = {
            'sedentary': 30.0,
            'light': 36.0,
            'moderate': 42.0,
            'very': 48.0,
            'extra': 54.0
        }
        base = base_by_activity.get(activity_level, 36.0)
        # adjust for age (decline ~0.2 ml/kg/min per year after 30)
        age_adj = (30 - age) * 0.2 if age < 30 else (30 - age) * 0.2
        # adjust modestly by sex
        sex_adj = 2.0 if sex == "M" else -2.0
        est_vo2 = max(10.0, base + sex_adj + age_adj)
        user_vo2 = st.number_input("Estimated VO2 (ml/kg/min) — editable", min_value=5.0, max_value=100.0, value=est_vo2, format="%.1f")

    # VO2 reference bands by age (example means)
    age_bins = ["18-29","30-39","40-49","50-59","60-69","70+"]
    ref_values = [40,36,34,31,28,25]  # example reference means (ml/kg/min)

    # find user's age bin index
    def age_to_bin_index_local(age):
        if age < 30: return 0
        if age < 40: return 1
        if age < 50: return 2
        if age < 60: return 3
        if age < 70: return 4
        return 5

    user_age_bin_index = age_to_bin_index_local(age)
    ref_mean = ref_values[user_age_bin_index]

    # compute percentile using normal approx
    user_percentile = vo2_percentile_from_ref(user_vo2, ref_mean, ref_sd=6.0)
    global_rank_top = 100.0 - user_percentile

    # show summary
    st.markdown(f"<h2 style='margin-top:8px'>{user_vo2:.1f} ml/kg/min</h2>", unsafe_allow_html=True)
    st.markdown(f"<div style='color:#cbd5e1'>Method: <strong>{vo2_method}</strong> &nbsp;&nbsp; Age band: <strong>{age_bins[user_age_bin_index]}</strong></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='result-box'><strong>Estimated population percentile:</strong> {user_percentile:.1f}th &nbsp;&nbsp; <strong>Reference rating:</strong> {'Below average' if user_percentile<40 else 'Average' if user_percentile<60 else 'Above average'}</div>", unsafe_allow_html=True)

    # Visible Global rank box (contrasting)
    subtitle_html = f"""
    <div style="
      background: rgba(18,48,71,0.95);
      color: #e6f6ff;
      padding:12px 16px;
      border-radius:8px;
      font-weight:700;
      margin-top:12px;
    ">
      Global rank: Top {global_rank_top:.1f}%
    </div>
    """
    st.markdown(subtitle_html, unsafe_allow_html=True)

    # Plot percentile strip (use our helper)
    st.plotly_chart(percentile_strip(user_percentile), use_container_width=True)

    # Plot VO2 age bars with highlight
    st.plotly_chart(vo2_age_bars(age_bins, ref_values, user_age_bin_index, user_vo2), use_container_width=True)


# --- Metabolism / BMR / TDEE section ---
st.subheader("Energy & metabolism estimates")

# quick workout input (simple)
st.markdown("Enter a representative weekly exercise session to estimate additional kcal burned:")
colA, colB, colC = st.columns([1,1,1])
with colA:
    ex_met = st.selectbox("Session MET (example)", options=[2.5, 3.5, 5.0, 7.0, 8.0], index=1, format_func=lambda x: f"{x} MET")
with colB:
    ex_minutes = st.number_input("Minutes per session", min_value=0, max_value=600, value=30)
with colC:
    ex_sessions = st.number_input("Sessions per week", min_value=0, max_value=21, value=3)

# Calculate BMR and TDEE
bmr = bmr_mifflin(age, sex, weight_kg, height_cm)
weekly_kcal = calories_burned_from_mets(weight_kg, ex_met, ex_minutes) * ex_sessions
tdee_no_ex = tdee_from_activity_factor(bmr, activity_level)
tdee_with_ex = tdee_including_weekly_exercise(bmr, activity_level, weekly_kcal)

col1, col2, col3 = st.columns(3)
col1.metric("BMR (basal, kcal/d)", f"{bmr:.0f}")
col2.metric("TDEE (without training, kcal/d)", f"{tdee_no_ex:.0f}")
col3.metric("TDEE incl. weekly exercise (avg/day)", f"{tdee_with_ex:.0f}")

st.caption("Estimater — veiledende. For medisinsk rådgivning, kontakt helsepersonell.")

# --- PDF export (basic textual report via ReportLab) ---
st.markdown("---")
st.subheader("Export / Download")

def pdf_generator_bytes(name="HealthReport", fields=None):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 20*mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20*mm, y, "Health Tools — Report")
    y -= 10*mm

    c.setFont("Helvetica", 10)
    for k, v in (fields or {}).items():
        text = f"{k}: {v}"
        c.drawString(20*mm, y, text)
        y -= 6*mm
        if y < 30*mm:
            c.showPage()
            y = height - 20*mm

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

report_fields = {
    "Age": age,
    "Sex": sex,
    "Height (cm)": height_cm,
    "Weight (kg)": weight_kg,
    "BMI": f"{bmi:.1f}" if 'bmi' in locals() else "N/A",
    "VO2 (ml/kg/min)": f"{user_vo2:.1f}" if user_vo2 is not None else "N/A",
    "VO2 percentile": f"{user_percentile:.1f}" if user_percentile is not None else "N/A",
    "Global rank (top %)": f"{global_rank_top:.1f}" if user_percentile is not None else "N/A",
    "BMR (kcal/d)": f"{bmr:.0f}",
    "TDEE no training (kcal/d)": f"{tdee_no_ex:.0f}",
    "TDEE incl. training (kcal/d avg/day)": f"{tdee_with_ex:.0f}",
    "Weekly exercise kcal (est)": f"{weekly_kcal:.0f}",
}

pdf_bytes = pdf_generator_bytes(fields=report_fields)
st.download_button("Download PDF report", data=pdf_bytes, file_name="health_report.pdf", mime="application/pdf")

# End of app
