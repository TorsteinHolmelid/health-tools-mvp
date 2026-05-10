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

# --- Waist-to-hip ratio and categories ---
def waist_hip_ratio(waist_cm: float, hip_cm: float):
    if hip_cm <= 0:
        raise ValueError("hip_cm must be > 0")
    ratio = waist_cm / hip_cm
    return round(ratio, 2)

def whr_category(sex: str, ratio: float):
    # WHO cutoffs (approx): men >0.9 elevated, women >0.85 elevated
    s = sex.upper()
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

# --- Navy body fat estimate (simple) ---
def body_fat_navy(sex: str, height_cm: float, neck_cm: float, waist_cm: float, hip_cm: float=None):
    """U.S. Navy method. For males: need neck and waist. For females: need neck, waist, hip."""
    sex = sex.upper()
    if sex == 'M':
        # male: BF% = 495 / (1.0324 - 0.19077*log10(waist - neck) + 0.15456*log10(height)) - 450
        if waist_cm - neck_cm <= 0:
            raise ValueError("waist must be larger than neck for navy formula")
        num = 495.0
        denom = 1.0324 - 0.19077 * math.log10(waist_cm - neck_cm) + 0.15456 * math.log10(height_cm)
        bf = num / denom - 450.0
    else:
        # female: BF% = 495 / (1.29579 - 0.35004*log10(waist + hip - neck) + 0.22100*log10(height)) - 450
        if waist_cm + (hip_cm or 0) - neck_cm <= 0:
            raise ValueError("inputs invalid for navy formula")
        num = 495.0
        denom = 1.29579 - 0.35004 * math.log10(waist_cm + (hip_cm or 0) - neck_cm) + 0.22100 * math.log10(height_cm)
        bf = num / denom - 450.0
    return round(max(2.0, min(60.0, bf)), 1)

# --- VO2 estimates (unchanged) ---
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

# --- Biological age: quick vs detailed (unchanged) ---
def estimate_biological_age_quick(age: int, smoker: bool, bmi: float, activity_level: str):
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

# --- Symptom triage (unchanged) ---
DEFAULT_RED_FLAGS = {
    # --- Symptom lists (expanded) ---
COMMON_SYMPTOMS = [
    'fever', 'cough', 'sore throat', 'headache', 'nausea', 'vomiting',
    'dizziness', 'joint pain', 'stomach pain', 'fatigue', 'loss of smell',
    'loss of taste', 'diarrhea', 'runny nose', 'chills'
]
    'chest pain', 'severe shortness of breath', 'loss of consciousness',
    'sudden weakness or numbness', 'severe bleeding', 'sudden severe headache'
}

def triage_decision(selected_symptoms: list,
                    red_flag_symptoms: set=None,
                    risk_factors: dict=None):
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

# --- Plan generator utilities ---
def bmr_mifflin_sea(sex: str, weight_kg: float, height_cm: float, age: int):
    # Mifflin-St Jeor
    if sex.upper() == 'M':
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
    """
    Returns a dict with weekly targets and daily calorie guidance.
    Caps recommended safe weight loss at 1.0 kg/week and safe gain at 0.5 kg/week.
    """
    if weeks <= 0:
        raise ValueError("weeks must be > 0")
    delta = target_weight_kg - current_weight_kg
    kg_per_week = delta / weeks
    # safety limits
    if kg_per_week < -1.0:
        warning = "Requested pace exceeds 1 kg/week weight loss. Recommendation capped to 1 kg/week (safer)."
        kg_per_week = -1.0
    elif kg_per_week > 0.5:
        warning = "Requested pace exceeds 0.5 kg/week weight gain. Recommendation capped to 0.5 kg/week (safer)."
        kg_per_week = 0.5
    else:
        warning = None

    # energy: ~7700 kcal per 1 kg fat (approx)
    daily_deficit = -kg_per_week * 7700 / 7  # negative for loss (deficit)
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
