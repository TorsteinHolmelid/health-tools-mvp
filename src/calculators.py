# src/calculators.py
import math

# --- COMMON / SYMPTOMS ---
COMMON_SYMPTOMS = [
    'abdominal pain', 'back pain', 'chest pain', 'chills', 'confusion',
    'cough', 'diarrhea', 'dizziness', 'fatigue', 'fever', 'headache',
    'joint pain', 'loss of appetite', 'loss of smell', 'loss of taste',
    'muscle pain', 'nausea', 'neck pain', 'runny nose', 'shortness of breath',
    'sore throat', 'sweating', 'tremor', 'vomiting', 'weakness', 'weight loss',
    'rash', 'itching', 'palpitations', 'heart racing', 'blurred vision',
    'urinary frequency', 'blood in urine', 'leg swelling', 'difficulty swallowing',
    'hoarseness', 'nosebleed', 'ear pain', 'eye pain', 'insomnia', 'anxiety',
    'depression', 'memory problems', 'tingling', 'numbness', 'wheezing'
]

DEFAULT_RED_FLAGS = {
    'chest pain', 'severe shortness of breath', 'loss of consciousness',
    'sudden weakness or numbness', 'severe bleeding', 'sudden severe headache',
    'difficulty breathing', 'blue lips or face', 'unresponsive'
}

# Combine into a master list for UI (deduplicated)
ALL_SYMPTOMS = sorted(list(set(COMMON_SYMPTOMS) | set(DEFAULT_RED_FLAGS))

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

# --- Waist-to-hip ratio ---
def waist_hip_ratio(waist_cm: float, hip_cm: float):
    if hip_cm <= 0:
        raise ValueError("hip_cm must be > 0")
    ratio = waist_cm / hip_cm
    return round(ratio, 2)

def whr_category(sex: str, ratio: float):
    s = str(sex).upper()
    if s == 'M':
        if ratio <= 0.9:
            return "Low risk"
        elif ratio <= 0.99:
            return "Moderate risk"
        else:
            return "High risk"
    else:
        if ratio <= 0.8:
            return "Low risk"
        elif ratio <= 0.84:
            return "Moderate risk"
        else:
            return "High risk"

# --- Navy body fat estimate ---
def body_fat_navy(sex: str, height_cm: float, neck_cm: float, waist_cm: float, hip_cm: float=None):
    sex = str(sex).upper()
    if sex == 'M':
        if waist_cm - neck_cm <= 0:
            raise ValueError("waist must be larger than neck for navy formula")
        num = 495.0
        denom = 1.0324 - 0.19077 * math.log10(waist_cm - neck_cm) + 0.15456 * math.log10(height_cm)
        bf = num / denom - 450.0
    else:
        if hip_cm is None:
            raise ValueError("hip_cm required for female navy formula")
        if waist_cm + hip_cm - neck_cm <= 0:
            raise ValueError("inputs invalid for navy formula")
        num = 495.0
        denom = 1.29579 - 0.35004 * math.log10(waist_cm + hip_cm - neck_cm) + 0.22100 * math.log10(height_cm)
        bf = num / denom - 450.0
    # Clamp to sensible range and round
    return round(max(2.0, min(60.0, bf)), 1)

# --- VO2 estimation methods ---
def vo2_cooper_from_distance(distance_m: float):
    """
    Cooper 12-min test: VO2max ~ (distance_m - 504.9)/44.73
    """
    if distance_m <= 0:
        raise ValueError("distance_m must be > 0")
    vo2 = (distance_m - 504.9) / 44.73
    return round(vo2, 2)

def vo2_rockport_1mile(time_min: float, hr_at_end: int, weight_kg: float, age: int, sex: str):
    """
    Rockport 1-mile walk test formula:
    VO2max = 132.853 - (0.0769 * weight_lbs) - (0.3877 * age) + (6.315 * gender) - (3.2649 * time_min) - (0.1565 * hr)
    gender: 1 for male, 0 for female
    """
    if time_min <= 0 or hr_at_end <= 0:
        raise ValueError("time_min and hr_at_end must be > 0")
    weight_lbs = weight_kg * 2.20462
    gender = 1 if str(sex).upper() == 'M' else 0
    vo2 = 132.853 - (0.0769 * weight_lbs) - (0.3877 * age) + (6.315 * gender) - (3.2649 * time_min) - (0.1565 * hr_at_end)
    return round(max(5.0, vo2), 2)

def vo2_simple_heuristic(age: int, sex: str, bmi: float, activity_level: str):
    """
    Existing heuristic kept for compatibility.
    """
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

def vo2_questionnaire_estimate(age: int, sex: str, weekly_minutes: int, session_intensity_score: int, bmi: float):
    """
    Questionnaire-based estimate:
      - weekly_minutes: total MVPA minutes per week
      - session_intensity_score: 1..5
    """
    base = 45.0 - 0.2 * (age - 30)
    sex_adj = 0 if str(sex).upper() == 'M' else -4.0
    vol_adj = (weekly_minutes / 150.0) * 6.0  # meeting 150 min gives ~+6 ml/kg/min
    intensity_adj = (session_intensity_score - 3) * 1.5
    bmi_penalty = -2.0 if bmi >= 30 else (0 if bmi < 25 else -1.0)
    vo2 = base + sex_adj + vol_adj + intensity_adj + bmi_penalty
    return round(max(5.0, vo2), 1)

# --- Biological age estimates ---
def estimate_biological_age_quick(age: int, smoker: bool, bmi: float, activity_level: str):
    """
    Quick heuristic: small set of inputs, educational only.
    """
    bio = age
    if smoker:
        bio += 7
    if bmi >= 30:
        bio += 5
    pa_map = {'low': 4, 'medium': 0, 'high': -3}
    bio += pa_map.get(activity_level, 0)
    return int(round(bio))

def estimate_biological_age_extended(age: int,
                                    smoker: bool,
                                    bmi: float,
                                    activity_level: str,
                                    sleep_hours: float=None,
                                    alcohol_units_per_week: int=None,
                                    fruit_veg_servings: int=None,
                                    perceived_stress: int=None,
                                    grip_strength_kg: float=None,
                                    bp_systolic: float=None,
                                    cholesterol_mg_dl: float=None,
                                    diabetes: bool=False,
                                    resting_hr: int=None):
    """
    Extended heuristic combining lifestyle and clinical inputs.
    Returns an integer 'biological age' estimate (educational only).
    """
    bio = age
    # Smoking
    if smoker:
        bio += 8
    # BMI
    if bmi >= 30:
        bio += 6
    elif bmi >= 25:
        bio += 2
    elif bmi < 18.5:
        bio += 1
    # Activity
    act_map = {'low': 4, 'medium': 0, 'high': -4}
    bio += act_map.get(activity_level, 0)
    # Sleep
    if sleep_hours is not None:
        if sleep_hours < 6:
            bio += 2
        elif 7 <= sleep_hours <= 9:
            bio -= 1
    # Alcohol
    if alcohol_units_per_week is not None:
        if alcohol_units_per_week > 14:
            bio += 2
        elif alcohol_units_per_week == 0:
            bio -= 1
    # Diet
    if fruit_veg_servings is not None and fruit_veg_servings >= 5:
        bio -= 1
    # Stress (1-10)
    if perceived_stress is not None:
        try:
            stress_adj = (perceived_stress - 5) * 0.5
            bio += stress_adj
        except Exception:
            pass
    # Grip strength proxy
    if grip_strength_kg is not None:
        if grip_strength_kg > 40:
            bio -= 2
    # Clinical
    if diabetes:
        bio += 7
    if bp_systolic is not None:
        try:
            if bp_systolic >= 160:
                bio += 6
            elif bp_systolic >= 140:
                bio += 3
        except Exception:
            pass
    if cholesterol_mg_dl is not None:
        try:
            if cholesterol_mg_dl >= 240:
                bio += 3
        except Exception:
            pass
    if resting_hr is not None:
        try:
            if resting_hr >= 90:
                bio += 2
        except Exception:
            pass
    return int(round(bio))

# --- Symptom triage ---
def triage_decision(selected_symptoms: list,
                    red_flag_symptoms: set=None,
                    risk_factors: dict=None):
    """
    Simple non-diagnostic triage heuristic:
    - If any red flag symptom -> Emergency
    - If multiple symptoms and comorbidity/age -> See GP
    - 2 symptoms -> See GP
    - 1 symptom -> Monitor/self-care
    """
    if red_flag_symptoms is None:
        red_flag_symptoms = DEFAULT_RED_FLAGS
    if risk_factors is None:
        risk_factors = {}
    # Normalize to lowercase
    selected_set = set([str(s).lower() for s in (selected_symptoms or []) if s])
    red_lower = set([str(r).lower() for r in red_flag_symptoms])
    if selected_set & red_lower:
        return "Emergency", "One or more red-flag symptoms selected. Seek emergency care immediately."
    n = len(selected_set)
    age = int(risk_factors.get('age', 0) or 0)
    has_comorbidity = bool(risk_factors.get('diabetes', False)) or bool(risk_factors.get('heart_disease', False))
    if n >= 3 and (has_comorbidity or age >= 65):
        return "See GP", "Multiple symptoms plus risk factors — contact your primary care provider."
    if n >= 2:
        return "See GP", "Several symptoms — consider contacting a healthcare professional."
    if n == 1:
        return "Monitor/Self-care", "One symptom — monitor and seek care if it worsens."
    return "Monitor/Self-care", "No symptoms selected."

# --- BMR and planning utilities ---
def bmr_mifflin_sea(sex: str, weight_kg: float, height_cm: float, age: int):
    if str(sex).upper() == 'M':
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return round(bmr, 0)

def activity_factor_map(level: str):
    return {'low': 1.2, 'medium': 1.55, 'high': 1.725}.get(level, 1.3)

def daily_calorie_needs(sex: str, weight_kg: float, height_cm: float, age: int, activity_level: str):
    bmr = bmr_mifflin_sea(sex, weight_kg, height_cm, age)
    af = activity_factor_map(activity_level)
    return int(round(bmr * af))

def generate_weight_plan(current_weight_kg: float, target_weight_kg: float, weeks: int,
                         sex: str, height_cm: float, age: int, activity_level: str):
    if weeks <= 0:
        raise ValueError("weeks must be > 0")
    delta = target_weight_kg - current_weight_kg
    kg_per_week = delta / weeks
    warning = None
    # Safety caps
    if kg_per_week < -1.0:
        warning = "Requested pace exceeds 1 kg/week weight loss. Recommendation capped to 1 kg/week (safer)."
        kg_per_week = -1.0
    elif kg_per_week > 0.5:
        warning = "Requested pace exceeds 0.5 kg/week weight gain. Recommendation capped to 0.5 kg/week (safer)."
        kg_per_week = 0.5
    daily_deficit = -kg_per_week * 7700 / 7  # approx kcal/day (negative for loss)
    current_needs = daily_calorie_needs(sex, current_weight_kg, height_cm, age, activity_level)
    recommended_daily = int(round(current_needs - daily_deficit))
    weekly_steps = []
    for w in range(1, weeks + 1):
        desc = f"Week {w}: aim for {kg_per_week:.2f} kg this week (adjust as needed)."
        weekly_steps.append(desc)
    return {
        "current_needs_kcal": current_needs,
        "recommended_daily_kcal": recommended_daily,
        "kg_per_week": kg_per_week,
        "daily_deficit": int(round(daily_deficit)),
        "weeks": weeks,
        "weekly_steps": weekly_steps,
        "warning": warning
    }
