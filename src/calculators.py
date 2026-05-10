# src/calculators.py
import math

# --- BMI ---
def bmi_calc(weight_kg: float, height_cm: float):
    if height_cm <= 0:
        raise ValueError("height_cm must be > 0")
    height_m = height_cm / 100.0
    bmi = weight_kg / (height_m ** 2)
    bmi_rounded = round(bmi, 2)
    if bmi < 18.5:
        cat = "Underweight"
    elif bmi < 25:
        cat = "Normal"
    elif bmi < 30:
        cat = "Overweight"
    else:
        cat = "Obesity"
    return bmi_rounded, cat

# --- VO2 estimates ---
def vo2_cooper_from_distance(distance_m: float):
    if distance_m <= 0:
        raise ValueError("distance_m must be > 0")
    vo2 = (distance_m - 504.9) / 44.73
    return round(vo2, 2)

def vo2_simple_heuristic(age: int, sex: str, bmi: float, activity_level: str):
    base = 60.0 - 0.3 * (age - 20)
    sex_adj = 0 if str(sex).upper() == 'M' else -5.0
    if bmi < 18.5:
        bmi_adj = -2.0
    elif bmi < 25:
        bmi_adj = 0.0
    elif bmi < 30:
        bmi_adj = -3.0
    else:
        bmi_adj = -6.0
    act_map = {'low': -4.0, 'medium': 0.0, 'high': 4.0}
    act_adj = act_map.get(activity_level, 0.0)
    vo2 = base + sex_adj + bmi_adj + act_adj
    return max(5.0, round(vo2, 2))

# --- Biological age: quick vs detailed ---
def estimate_biological_age_quick(age: int, smoker: bool, bmi: float, activity_level: str):
    """A light 'fun' estimate based on a few heuristics."""
    bio = age
    if smoker:
        bio += 7
    if bmi >= 30:
        bio += 5
    pa_map = {'low': 4, 'medium': 0, 'high': -3}
    bio += pa_map.get(activity_level, 0)
    return int(round(bio))

def estimate_biological_age_detailed(age: int,
                                    smoker: bool,
                                    bmi: float,
                                    activity_level: str,
                                    systolic_bp: float=None,
                                    diabetes: bool=False,
                                    cholesterol_mg_dl: float=None,
                                    resting_hr: int=None):
    """
    A slightly more detailed heuristic. NOT clinical. For demo only.
    Adds penalties/credits for common risk markers.
    """
    bio = age
    if smoker:
        bio += 8
    if bmi < 18.5:
        bio -= 1
    elif bmi < 25:
        bio += 0
    elif bmi < 30:
        bio += 3
    else:
        bio += 6
    pa_map = {'low': 4, 'medium': 0, 'high': -4}
    bio += pa_map.get(activity_level, 0)
    if diabetes:
        bio += 7
    if systolic_bp is not None:
        if systolic_bp >= 160:
            bio += 6
        elif systolic_bp >= 140:
            bio += 3
    if cholesterol_mg_dl is not None and cholesterol_mg_dl >= 240:
        bio += 3
    if resting_hr is not None and resting_hr >= 90:
        bio += 2
    return int(round(bio))

# --- Triage / Symptom decision ---
DEFAULT_RED_FLAGS = {
    'chest pain', 'severe shortness of breath', 'loss of consciousness',
    'sudden weakness or numbness', 'severe bleeding', 'sudden severe headache'
}

def triage_decision(selected_symptoms: list,
                    red_flag_symptoms: set=None,
                    risk_factors: dict=None):
    """
    Returns (level, message)
    level: "Emergency", "See GP", "Monitor/Self-care"
    """
    if red_flag_symptoms is None:
        red_flag_symptoms = DEFAULT_RED_FLAGS
    if risk_factors is None:
        risk_factors = {}

    selected_set = set([s.lower() for s in selected_symptoms])
    if selected_set & set([s.lower() for s in red_flag_symptoms]):
        return "Emergency", "One or more red-flag symptoms selected. Seek emergency care immediately."

    n = len(selected_set)
    age = risk_factors.get('age', 0)
    has_comorbidity = risk_factors.get('diabetes', False) or risk_factors.get('heart_disease', False)

    if n >= 3 and (has_comorbidity or age >= 65):
        return "See GP", "Multiple symptoms plus risk factors — contact your primary care provider."
    if n >= 2:
        return "See GP", "Several symptoms — consider contacting a healthcare professional."
    if n == 1:
        return "Monitor/Self-care", "One symptom — monitor and seek care if it worsens."
    return "Monitor/Self-care", "No symptoms selected."

# --- Symptom lists (expanded) ---
COMMON_SYMPTOMS = [
    'fever', 'cough', 'sore throat', 'headache', 'nausea', 'vomiting',
    'dizziness', 'joint pain', 'stomach pain', 'fatigue', 'loss of smell',
    'loss of taste', 'diarrhea', 'runny nose', 'chills'
]

RED_FLAG_SYMPTOMS = sorted(list(DEFAULT_RED_FLAGS))
