# src/calculators.py
import math

# --- BMI ---
def bmi_calc(weight_kg: float, height_cm: float):
    if height_cm <= 0:
        raise ValueError("height_cm must be > 0")
    height_m = height_cm / 100.0
    bmi = weight_kg / (height_m  2)
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
    sex = sex.upper()
    if sex == 'M':
        if waist_cm - neck_cm <= 0:
            raise ValueError("waist must be larger than neck for navy formula")
        num = 495.0
        denom = 1.0324 - 0.19077 * math.log10(waist_cm - neck_cm) + 0.15456 * math.log10(height_cm)
        bf = num / denom - 450.0
    else:
        if waist_cm + (hip_cm or 0) - neck_cm <= 0:
            raise ValueError("inputs invalid for navy formula")
        num = 495.0
        denom = 1.29579 - 0.35004 * math.log10(waist_cm + (hip_cm or 0) - neck_cm) + 0.22100 * math.log10(height_cm)
        bf = num / denom - 450.0
    return round(max(2.0, min(60.0, bf)), 1)

# --- VO2 estimates ---
def vo2_cooper_from_distance(distance_m: float):
    if distance_m <= 0:
        raise ValueError("distance_m must be > 0")
    vo2 = (distance_m - 504.9) / 44.73
    return round(vo2, 2)

def vo2_simple_heuristic(age: int, sex: str, bmi: float, activity_level: str):
    base = 60.0 - 0.3 * age - 20)
    sex_adj = 0 if str(sex).
