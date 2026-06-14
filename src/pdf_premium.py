"""
Premium Longevity Intelligence Report — PDF generator (English, premium edition)
Drop-in replacement for create_pdf_bytes_ultimate(report).

Usage in app.py:
    from pdf_premium import create_pdf_bytes_premium as create_pdf_bytes_ultimate
(or simply rename the call site to create_pdf_bytes_premium)
"""

from __future__ import annotations
import io
import math
import uuid
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, PageBreak, Flowable, Spacer,
    Table, TableStyle, HRFlowable,
)


def create_pdf_bytes_premium(report: dict) -> bytes:
    buffer = io.BytesIO()
    PAGE_W, PAGE_H = A4
    MARGIN_H = 18 * mm
    CONTENT_W = PAGE_W - 2 * MARGIN_H

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN_H, rightMargin=MARGIN_H,
        topMargin=32 * mm, bottomMargin=22 * mm,  # Økt topp- og bunnmargin
    )

    # ── Theme ──────────────────────────────────────────────────────
    BG     = HexColor("#080C16")
    CARD   = HexColor("#121C32")
    CARD2  = HexColor("#0E1729")
    GOLD   = HexColor("#D4AF7A")          # premium accent
    ACCENT = HexColor("#14B8A6")
    BLUE   = HexColor("#3B82F6")
    GLOW   = HexColor("#38BDF8")          # spotlight blue, cover gradient
    GOOD   = HexColor("#22C55E")
    WARN   = HexColor("#F59E0B")
    BAD    = HexColor("#EF4444")
    TEXT   = HexColor("#F1F5F9")
    MUTED  = HexColor("#94A3B8")
    STROKE = HexColor("#28324A")
    DIM    = HexColor("#5B6B85")

    _styles = getSampleStyleSheet()

    def S(name, size=10, color=TEXT, after=6, lead=None, bold=False, italic=False, align=TA_LEFT):
        return ParagraphStyle(
            name, parent=_styles["Normal"],
            fontName="Helvetica-Bold" if bold else ("Helvetica-Oblique" if italic else "Helvetica"),
            fontSize=size, textColor=color, spaceAfter=after,
            leading=lead or (size + 4), alignment=align,
        )

    def P(txt, style):
        return Paragraph(str(txt), style)

    def _sf(x):
        try:
            return float(x)
        except Exception:
            return None

    # ── Pull data out of report ──────────────────────────────────
    inp   = report.get("inputs", {}) or {}
    age_v = inp.get("age", "—")
    sex_v = inp.get("sex", "—")
    h_v   = inp.get("height_cm", "—")
    w_v   = inp.get("weight_kg", "—")
    name_v = inp.get("name") or report.get("user_name") or ""

    gen_v = report.get("generated", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    report_id = report.get("report_id") or f"HT-{uuid.uuid4().hex[:8].upper()}"

    bmi_d   = report.get("bmi") or {}
    vo2_d   = report.get("vo2") or {}
    bio_d   = report.get("bio_age") or {}
    factors = report.get("bio_factors") or []
    plan_d  = report.get("plan") or {}
    exlog   = report.get("exercise_log") or {}
    triage_r = report.get("triage_recommendations") or []
    whr_d   = report.get("whr") or {}
    bf_d    = report.get("bodyfat") or {}

    bmi_v   = _sf(bmi_d.get("value"))
    bmi_cat = str(bmi_d.get("category", ""))
    vo2_v   = _sf(vo2_d.get("value"))
    vo2_pct = _sf(vo2_d.get("percentile")) or 0.0
    vo2_rat = str(vo2_d.get("rating", ""))
    bio_v   = _sf(bio_d.get("value"))
    age_f   = _sf(age_v)

    has_plan  = bool(plan_d and not plan_d.get("error"))
    cur_kcal  = _sf(plan_d.get("current_needs_kcal")) if has_plan else None
    rec_kcal  = _sf(plan_d.get("recommended_daily_kcal")) if has_plan else None
    kg_pw     = _sf(plan_d.get("kg_per_week")) if has_plan else None
    milestones = plan_d.get("milestones", []) if has_plan else []
    _goal     = plan_d.get("goal", "Maintenance")

    ex_min  = exlog.get("minutes", 0)
    ex_sess = exlog.get("sessions_per_week", 0)
    ex_kcal_w = _sf(exlog.get("kcal_per_week")) or 0.0
    ex_total_min = int(ex_min or 0) * int(ex_sess or 0)

    # ── 30-Day Training Plan — built only from the user's selected activities ──
    ACT_CATEGORY = {
        "Walking (casual)": "low", "Brisk walking": "low", "Yoga / Pilates": "low",
        "Housework / Light chores": "low", "Gardening / Heavy yard work": "low",
        "Cycling (leisure)": "cardio", "Cycling (vigorous)": "cardio", "Elliptical": "cardio",
        "Rowing (moderate/vigorous)": "cardio", "Swimming": "cardio",
        "Running/jogging": "cardio", "HIIT": "cardio", "Stair climbing / Stairmaster": "cardio",
        "Basketball / Team sports": "sport", "Soccer (football)": "sport", "Tennis (casual)": "sport",
        "Squash": "sport", "Badminton": "sport", "Table tennis (bordtennis)": "sport", "Dancing": "sport",
        "Strength training (weights)": "strength", "Boxing / Martial arts": "strength",
        "Rock climbing / Bouldering": "strength", "Hiking (incline)": "strength",
    }
    CAT_EMOJI = {"strength": "Strength", "cardio": "Cardio", "sport": "Sport", "low": "Low-impact"}

    selected_acts = [a for a in (report.get("selected_activities") or []) if a]
    _strength_sel = [a for a in selected_acts if ACT_CATEGORY.get(a) == "strength"]
    _cardio_sel   = [a for a in selected_acts if ACT_CATEGORY.get(a) == "cardio"]
    _sport_sel    = [a for a in selected_acts if ACT_CATEGORY.get(a) == "sport"]
    _low_sel      = [a for a in selected_acts if ACT_CATEGORY.get(a) == "low"]
    has_strength_act = bool(_strength_sel)
    has_cardio_act   = bool(_cardio_sel)
    has_sport_act    = bool(_sport_sel)
    plan30_strength = _strength_sel or ["Strength training (weights)"]
    plan30_cardio   = _cardio_sel or ["Running/jogging"]
    plan30_sport    = _sport_sel or []
    plan30_low      = _low_sel or ["Walking (casual)"]

    def _strength_rx(week, day_idx=0, activity=""):
        """
        Per-activity, per-day, per-week strength prescriptions.
        Day types: 0=push, 1=pull, 2=legs/core, 3=push, 4=pull, 5=full-body
        (mirrors the existing STRENGTH_SPLITS rotation but adds activity-specific cues)
        """
        day_types = {0: "push", 1: "pull", 2: "legs", 3: "push", 4: "pull", 5: "full"}
        dtype = day_types.get(day_idx % 6, "push")
        act = activity.lower()

        # ── STRENGTH TRAINING (WEIGHTS) ──────────────────────────────────────────
        if "strength training" in act or "weights" in act:
            P = {
                1: {
                    "push":  ("45 min", "Bench press 3×10, overhead press 3×10, tricep dips 3×12. RPE 6 — nail the form, no grinding reps."),
                    "pull":  ("45 min", "Barbell row 3×10, lat pulldown 3×10, face pulls 3×15. RPE 6 — full stretch at the bottom of every rep."),
                    "legs":  ("45 min", "Squat 3×10, Romanian deadlift 3×10, leg press 3×12. RPE 6 — controlled tempo, 3 s down."),
                    "full":  ("45 min", "Deadlift 3×8, push-up 3×15, goblet squat 3×12, plank 3×45 s. Full-body primer, moderate load."),
                },
                2: {
                    "push":  ("50 min", "Bench press 3×10 (+2.5 kg vs W1), incline DB press 3×10, lateral raises 3×15. RPE 7."),
                    "pull":  ("50 min", "Barbell row 3×10 (+2.5 kg), pull-ups 3×8, seated cable row 3×12. RPE 7 — squeeze the scapula."),
                    "legs":  ("50 min", "Squat 3×10 (+2.5 kg), hip thrust 3×12, walking lunges 3×10 each leg. RPE 7."),
                    "full":  ("50 min", "Deadlift 3×8 (+5 kg), dips 3×10, Bulgarian split squat 3×10, plank 3×60 s. Progressive load."),
                },
                3: {
                    "push":  ("55 min", "Bench press 4×8 (heaviest weight this month), OHP 4×8, cable fly 3×12 drop-set on last set. RPE 8."),
                    "pull":  ("55 min", "Barbell row 4×8 (heavy), weighted pull-ups 4×6, face pulls 3×15. RPE 8 — peak week, push the load."),
                    "legs":  ("55 min", "Squat 4×8 (heaviest), stiff-leg deadlift 4×8, leg press 4×10 drop-set. RPE 8."),
                    "full":  ("55 min", "Deadlift 4×6 (heaviest), push-press 3×8, front squat 3×8, ab wheel 3×10. Peak intensity full-body."),
                },
                4: {
                    "push":  ("40 min", "Bench press 3×8 (same weight as W3, no new PR), OHP 3×8, triceps 2×12. RPE 7 — lock in, don't push."),
                    "pull":  ("40 min", "Row 3×8 (W3 weight), lat pulldown 3×10, face pulls 2×15. RPE 7 — taper, protect the gains."),
                    "legs":  ("40 min", "Squat 3×8 (W3 weight), hip thrust 3×10, leg curl 2×12. RPE 7 — legs fresh for reassessment."),
                    "full":  ("40 min", "Deadlift 3×5 (W3 weight), push-up 2×15, goblet squat 2×10, plank 2×45 s. Light full-body flush."),
                },
            }

        # ── BOXING / MARTIAL ARTS ────────────────────────────────────────────────
        elif "boxing" in act or "martial arts" in act:
            P = {
                1: {
                    "push":  ("40 min", "Jab–cross technique on bag: 3×3 min rounds, 60 s rest. Focus on hip rotation and punch extension, not power."),
                    "pull":  ("40 min", "Defensive movement: slip, roll, parry drills with a partner or mirror × 3×3 min. Build the habit."),
                    "legs":  ("40 min", "Footwork fundamentals: in/out, lateral, pivot × 4×3 min. Stance, balance and weight transfer."),
                    "push":  ("40 min", "Combination work: 1-2, 1-2-3, 1-2-3-2 on bag × 4×2 min. Clean technique at 60% power."),
                    "pull":  ("40 min", "Clinch and grappling defence drills × 3×3 min. Posture, head position, hand control."),
                    "full":  ("40 min", "Shadow boxing: 4×3 min continuous movement, mix offence and defence. Aerobic base session."),
                },
                2: {
                    "push":  ("45 min", "Power combinations on bag: 1-2-hook, uppercut combos × 5×3 min, 60 s rest. 75% power."),
                    "pull":  ("45 min", "Defensive combinations: slip-cross, roll-hook, parry-jab counter × 4×3 min. Speed up the defence."),
                    "legs":  ("45 min", "Footwork + punch combos: step in/out with each combo × 4×3 min. Punches come from the feet."),
                    "push":  ("45 min", "Pad work or bag: 4×3 min moderate intensity — vary combo length from 2 to 6 punches."),
                    "pull":  ("45 min", "Sparring technique (light): 4×2 min controlled sparring or partner drills at 50% contact."),
                    "full":  ("45 min", "Shadow boxing + bag superset: 2 min shadow, 2 min bag × 5 rounds. Build work capacity."),
                },
                3: {
                    "push":  ("50 min", "Heavy bag power rounds: 6×3 min at 90% effort, 45 s rest. Hardest hitting session this month."),
                    "pull":  ("50 min", "Defensive gauntlet: partner throws combos, you slip/roll continuously × 6×2 min. Max reaction speed."),
                    "legs":  ("50 min", "Footwork hell: lateral shuffle + pivot + sprint × 8×2 min. 90% effort. Test the legs."),
                    "push":  ("50 min", "Pad work peak: 6×3 min at near-competition intensity. No holding back."),
                    "pull":  ("50 min", "Full sparring or hard partner drills: 5×3 min. Treat this as a real fight."),
                    "full":  ("50 min", "Full fight simulation: 8×3 min shadow + bag alternating. Cardio and technique at peak intensity."),
                },
                4: {
                    "push":  ("35 min", "Easy bag work: 4×2 min light combinations at 60% — feel sharp, not fatigued."),
                    "pull":  ("35 min", "Slow defensive drills: slips and rolls at 65% — groove the movements, no pressure."),
                    "legs":  ("35 min", "Light footwork: 4×2 min easy patterns, stay loose and mobile."),
                    "push":  ("35 min", "Light pad work: 3×2 min easy combos. Taper, stay sharp."),
                    "pull":  ("35 min", "Technical shadow boxing: 4×2 min — visualise the perfect defence and counter."),
                    "full":  ("35 min", "Easy shadow boxing: 4×2 min continuous. Aerobic flush, finish feeling fresh."),
                },
            }

        # ── ROCK CLIMBING / BOULDERING ───────────────────────────────────────────
        elif "climbing" in act or "bouldering" in act:
            P = {
                1: {
                    "push":  ("45 min", "Slab climbing technique: 4 easy-grade routes focusing on footwork precision and quiet feet. No overgripping."),
                    "pull":  ("45 min", "Hangboard protocol: 7 s on / 3 s off × 6 reps per hold, 3 hold types at 60% effort. Build finger tendon tolerance."),
                    "legs":  ("45 min", "Footwork drills: climb 3 routes using only slab technique — no pulling with arms. Legs do the work."),
                    "push":  ("45 min", "Overhang exploration: 3 easy overhangs at 60% effort — practice body positioning and hip-to-wall proximity."),
                    "pull":  ("45 min", "Dead-hang endurance: 10 s hang / 50 s rest × 8 sets on a jug. Gentle finger loading."),
                    "full":  ("45 min", "Volume day: 6 easy routes top-to-bottom without resting on the wall. Build movement fluency."),
                },
                2: {
                    "push":  ("50 min", "Technical slab: 5 moderate-grade routes — focus on precise foot placement, trust the rubber."),
                    "pull":  ("50 min", "Hangboard build: 10 s on / 5 s off × 6 reps, add one harder hold type vs. week 1."),
                    "legs":  ("50 min", "Dynamic movement: 3 moderate overhangs practising hip flags and drop-knees. Control the swing."),
                    "push":  ("50 min", "Problem-solving: 5 moderate-grade boulders you haven't sent — read the route before pulling on."),
                    "pull":  ("50 min", "Lock-off training: 3 s lock-off at 90°, 120°, 150° × 5 reps each arm. Build pulling strength."),
                    "full":  ("50 min", "Circuit day: 8 moderate routes, 3 min rest between each. Volume with moderate difficulty."),
                },
                3: {
                    "push":  ("55 min", "Hard project attempts: 3 routes at your limit — 5 attempts each with full rest between. Peak week."),
                    "pull":  ("55 min", "Hangboard peak: 10 s on / 5 s off × 8 reps on crimps and slopers. Heaviest finger loading this month."),
                    "legs":  ("55 min", "Powerful dynamics: campus ladder moves or hard boulders with dynamic throws × 6 problems. Max intensity."),
                    "push":  ("55 min", "Redpoint attempts: your hardest project, fresh skin, 6 attempts. This is your peak climbing session."),
                    "pull":  ("55 min", "Max pulling: weighted pull-ups or system board on hardest holds × 4×5 reps. Peak strength session."),
                    "full":  ("55 min", "Hard circuit: 6 near-limit routes, full rest, maximum quality. Push the ceiling."),
                },
                4: {
                    "push":  ("40 min", "Easy slab cruising: 4 easy routes at 65% — enjoy the movement, no projecting."),
                    "pull":  ("40 min", "Light hangboard: 7 s on / 53 s off × 4 reps on jugs only. Maintain, don't stress the tendons."),
                    "legs":  ("40 min", "Gentle traversing: low wall traverse for 20 min — footwork focus, easy effort."),
                    "push":  ("40 min", "Relaxed bouldering: 4 easy problems — notice how much more automatic the movement feels."),
                    "pull":  ("40 min", "Easy lock-offs: 2 s hold, 3 hold positions × 3 reps each arm. Taper, stay fresh."),
                    "full":  ("40 min", "Fun climbing: pick 4 routes you enjoy at easy grade. Taper week — finish smiling."),
                },
            }

        # ── HIKING (INCLINE) ─────────────────────────────────────────────────────
        elif "hiking" in act:
            P = {
                1: {
                    "push":  ("45 min", "Incline treadmill or hill walk at 6–8% gradient, 5 km/h — focus on upright posture and heel-to-toe strike."),
                    "pull":  ("45 min", "Descent practice: find a 15–20% downhill and walk down slowly, 4 × 5 min. Quad load, controlled pace."),
                    "legs":  ("45 min", "Uneven terrain walk: forest path or trail at easy effort — ankle stability and ground feel are the focus."),
                    "push":  ("45 min", "Weighted pack introduction: 5 kg pack, flat-to-moderate trail, 45 min. Posture over pace."),
                    "pull":  ("45 min", "Step-up strength: find stairs or a step, 3×15 each leg with a controlled 3 s up / 3 s down tempo."),
                    "full":  ("50 min", "Long easy hike: 50 min continuous at conversational pace, mixed terrain if possible."),
                },
                2: {
                    "push":  ("50 min", "Incline hike at 8–10% gradient — push the pace slightly vs. week 1, same 5 km/h but steeper."),
                    "pull":  ("50 min", "Descent intervals: 6 × 5 min fast descent, 3 min flat recovery. Build eccentric quad tolerance."),
                    "legs":  ("50 min", "Trail run-walk: alternate 3 min easy jog / 5 min hike × 5 rounds on mixed terrain."),
                    "push":  ("50 min", "Weighted pack build: 8 kg pack, moderate incline trail, 50 min at steady pace."),
                    "pull":  ("50 min", "Step-up + calf raise superset: 3×12 each leg, add 5 kg weight vest if available."),
                    "full":  ("60 min", "Endurance hike: 60 min continuous, mixed gradient — include at least 2 sustained uphills."),
                },
                3: {
                    "push":  ("60 min", "Steep incline hike: 10–15% gradient, 55 min sustained effort. Hardest ascent session this month."),
                    "pull":  ("55 min", "Descent power session: 8 × 5 min fast downhill, 2 min flat rest. Max eccentric loading."),
                    "legs":  ("55 min", "Trail intervals: 5 × 4 min hard uphill effort, walk 3 min down for recovery. Push the VO2max."),
                    "push":  ("60 min", "Heavy pack hike: 10–12 kg pack, sustained incline trail, 55 min. Peak load this month."),
                    "pull":  ("55 min", "Single-leg strength peak: pistol squat progressions or step-ups with max load × 4×10 each leg."),
                    "full":  ("70 min", "Long hard hike: 70 min, max elevation gain you can find. This is your peak endurance session."),
                },
                4: {
                    "push":  ("40 min", "Easy incline walk: 5% gradient, 4.5 km/h, 40 min — legs fresh, lungs easy."),
                    "pull":  ("35 min", "Gentle descent walk: easy grade, slow pace, 30 min. Flush out the legs."),
                    "legs":  ("40 min", "Flat trail walk: 40 min conversational pace — active recovery, no hills."),
                    "push":  ("40 min", "Light pack walk: 4 kg pack, flat-moderate terrain, 40 min. Taper, stay mobile."),
                    "pull":  ("35 min", "Easy step-ups: 2×10 each leg, bodyweight only. Stay loose, don't tire."),
                    "full":  ("45 min", "Easy nature hike: 45 min at your own comfortable pace. Enjoy it — notice how strong you feel."),
                },
            }

        # ── GENERIC STRENGTH FALLBACK ─────────────────────────────────────────────
        else:
            P = {
                1: {
                    "push":  ("45 min", "Push movements (press, push-up, dip): 3×10 at RPE 6 — establish the baseline, clean form only."),
                    "pull":  ("45 min", "Pull movements (row, pull-up, curl): 3×10 at RPE 6 — full range, slow eccentric."),
                    "legs":  ("45 min", "Leg movements (squat, hinge, lunge): 3×10 at RPE 6 — 3 s tempo on the way down."),
                    "full":  ("45 min", "Full-body circuit: one push + one pull + one leg + one core exercise, 3 rounds. Moderate load."),
                },
                2: {
                    "push":  ("50 min", "Push movements: 3×10, add 2.5–5% load vs. week 1. RPE 7."),
                    "pull":  ("50 min", "Pull movements: 3×10, add load or 1–2 reps vs. week 1. RPE 7."),
                    "legs":  ("50 min", "Leg movements: 3×10 (+load), add one unilateral exercise. RPE 7."),
                    "full":  ("50 min", "Full-body circuit: increase load or reps by 5–10% across all exercises. RPE 7."),
                },
                3: {
                    "push":  ("55 min", "Push movements: 4×8 at heaviest load this month. RPE 8 — push hard, technique must hold."),
                    "pull":  ("55 min", "Pull movements: 4×8 heavy. Drop-set on the final set of your last exercise. RPE 8."),
                    "legs":  ("55 min", "Leg movements: 4×8 heavy. Add a drop-set or paused reps on squats/hinges. RPE 8."),
                    "full":  ("55 min", "Full-body peak: 4 rounds, max load you can handle with good form. Hardest session this month."),
                },
                4: {
                    "push":  ("40 min", "Push movements: 3×8, same weight as week 3 — no new PRs. RPE 7. Taper."),
                    "pull":  ("40 min", "Pull movements: 3×8, maintain week 3 load. RPE 7. Protect the gains."),
                    "legs":  ("40 min", "Leg movements: 3×8 at week 3 weight. Keep legs fresh for reassessment."),
                    "full":  ("40 min", "Light full-body flush: 2 rounds, moderate load — finish feeling good, not drained."),
                },
            }

        dur, rx = P[week][dtype]
        return dur, rx

    def _cardio_easy_rx(week, activity=""):
        """Activity-specific easy cardio prescriptions with weekly progression."""
        act = activity.lower()

        if "running" in act or "jogging" in act:
            return {
                1: ("30 min", "Easy run at conversational pace (~65% HRmax) — you should be able to say full sentences. No watching pace."),
                2: ("35 min", "Easy run, 5 min longer than week 1 — same effort, let pace come naturally."),
                3: ("35 min", "Easy run with 4 × 20 s relaxed strides in the final 10 min — accelerate gently, don't sprint."),
                4: ("30 min", "Easy run, taper week — genuinely easy, arrive at next session fresh."),
            }[week]

        elif "cycling" in act:
            return {
                1: ("30 min", "Zone 2 ride at ~65% HRmax — flat or gentle rolling terrain, cadence 80–90 rpm, comfortable gear."),
                2: ("35 min", "Zone 2, 5 min longer — same easy effort, focus on smooth pedal stroke throughout."),
                3: ("35 min", "Zone 2 with 4 × 30 s relaxed cadence increases (100+ rpm) in the final 10 min. Keep effort easy."),
                4: ("30 min", "Easy Zone 2 spin — taper week, shorter session, same comfortable effort."),
            }[week]

        elif "swimming" in act:
            return {
                1: ("30 min", "Easy freestyle at ~65% effort — focus on stroke length and bilateral breathing. No splits, just feel."),
                2: ("35 min", "Easy swim, 5 min longer — alternate 100 m freestyle / 50 m backstroke to vary the load."),
                3: ("35 min", "Easy swim with 4 × 25 m relaxed tempo increases mid-session. Stroke quality must hold at speed."),
                4: ("30 min", "Easy mixed strokes — taper week, focus on feel and flow, not distance."),
            }[week]

        elif "rowing" in act:
            return {
                1: ("30 min", "Easy row at 18–20 spm, damper 4–5, ~65% effort — focus on sequencing: legs → body → arms each stroke."),
                2: ("35 min", "Easy row, 5 min longer — maintain the sequencing, add 1 spm if it still feels comfortable."),
                3: ("35 min", "Easy row with 4 × 1 min at 22 spm in the final 10 min — rate goes up, effort stays easy."),
                4: ("30 min", "Easy row at 18 spm — taper week, smooth technique, arrive fresh at the next session."),
            }[week]

        elif "elliptical" in act:
            return {
                1: ("30 min", "Easy elliptical at ~65% HRmax — zero incline, moderate resistance, focus on full push-pull arm drive."),
                2: ("35 min", "Easy elliptical, 5 min longer — add 1 resistance level if heart rate feels too low."),
                3: ("35 min", "Easy elliptical with 4 × 30 s higher cadence bursts in the last 10 min. Effort stays easy."),
                4: ("30 min", "Easy elliptical — taper week, comfortable resistance, shorter session."),
            }[week]

        elif "stair" in act:
            return {
                1: ("25 min", "Stairmaster or stair walk at level 4–6 (~65% effort) — upright posture, don't lean on the rails."),
                2: ("30 min", "Stair walk, 5 min longer — add 1 level if heart rate stays below 70% HRmax."),
                3: ("30 min", "Stair walk with 4 × 1 min at +2 levels in the last 10 min. Return to base level to recover."),
                4: ("25 min", "Easy stair walk — taper week, base level, comfortable effort."),
            }[week]

        elif "hiit" in act:
            return {
                1: ("20 min", "Active recovery HIIT day — 30 s easy bodyweight movement / 30 s complete rest × 10 rounds. Very low effort."),
                2: ("20 min", "Easy movement circuit — jumping jacks, march in place, arm circles × 10 min. Flush the legs."),
                3: ("20 min", "Gentle mobility flow: 5 min easy movement, 10 min static/dynamic stretching, 5 min cool-down walk."),
                4: ("20 min", "Full rest-day movement: 20 min easy walk or gentle yoga. No cardio stress."),
            }[week]

        else:
            return {
                1: ("30 min", "Zone 2 effort (~65% HRmax) — conversational pace, build the aerobic base."),
                2: ("35 min", "Zone 2, 5 min longer than last week, same easy effort."),
                3: ("35 min", "Zone 2 with 4 × 20 s relaxed pick-ups in the last 10 min."),
                4: ("30 min", "Zone 2 taper — keep it genuinely easy, shorter session."),
            }[week]

    def _cardio_interval_rx(week, pct, activity=""):
        """Activity-specific interval prescriptions scaled by VO2max percentile."""
        act = activity.lower()
        low_fit = pct is not None and pct < 50

        if "running" in act or "jogging" in act:
            if low_fit:
                return {
                    1: ("25 min", "5 × 2 min at a pace that feels 'comfortably hard' (Zone 3), 2 min easy jog recovery. Build the engine."),
                    2: ("28 min", "6 × 2 min hard effort / 2 min easy jog. Same pace as week 1 — add one rep."),
                    3: ("30 min", "6 × 3 min hard / 2 min easy jog — your toughest run this month. Push the pace."),
                    4: ("22 min", "4 × 2 min hard / 2 min easy jog — taper, stay sharp."),
                }[week]
            return {
                1: ("28 min", "6 × 2 min at Zone 4–5 (hard but controlled) / 2 min easy jog recovery."),
                2: ("32 min", "6 × 3 min hard / 2 min easy jog. Add 1 min to each rep vs. week 1."),
                3: ("35 min", "8 × 2 min hard / 90 s easy jog — hardest run this month. Race-effort reps."),
                4: ("24 min", "4 × 3 min hard / 2 min easy jog — taper, keep the legs snappy."),
            }[week]

        elif "cycling" in act:
            if low_fit:
                return {
                    1: ("28 min", "5 × 2 min hard effort (Zone 3, ~80% HRmax) / 2 min easy spin. Build power tolerance."),
                    2: ("30 min", "6 × 2 min hard / 2 min easy spin. Same effort, one extra rep."),
                    3: ("32 min", "6 × 3 min hard / 2 min easy — peak interval session. Push the watts."),
                    4: ("22 min", "4 × 2 min hard / 2 min easy spin — taper, stay sharp."),
                }[week]
            return {
                1: ("30 min", "6 × 2 min at ~90% HRmax / 2 min easy spin. Hard but not all-out."),
                2: ("34 min", "6 × 3 min hard / 2 min easy spin. Watts should feel unsustainable past 4 min."),
                3: ("36 min", "8 × 2 min max effort / 90 s easy — hardest bike session this month."),
                4: ("24 min", "4 × 3 min hard / 2 min easy spin — taper, keep the power."),
            }[week]

        elif "swimming" in act:
            if low_fit:
                return {
                    1: ("25 min", "5 × 50 m hard / 60 s rest at wall — controlled speed, focus on stroke not thrashing."),
                    2: ("28 min", "6 × 50 m hard / 50 s rest. Push the pace slightly vs. week 1."),
                    3: ("30 min", "6 × 75 m hard / 60 s rest — toughest swim session this month."),
                    4: ("20 min", "4 × 50 m controlled fast / 60 s rest — taper, feel sharp."),
                }[week]
            return {
                1: ("28 min", "6 × 50 m near-max / 45 s rest at wall. Strong stroke throughout."),
                2: ("30 min", "6 × 75 m hard / 50 s rest. Increase distance per rep vs. week 1."),
                3: ("32 min", "8 × 50 m max effort / 30 s rest — hardest swim this month."),
                4: ("22 min", "4 × 75 m controlled fast / 45 s rest — taper, stay sharp."),
            }[week]

        elif "rowing" in act:
            if low_fit:
                return {
                    1: ("25 min", "5 × 2 min at 22–24 spm, hard effort / 2 min easy row. Keep sequencing clean under fatigue."),
                    2: ("28 min", "6 × 2 min hard / 2 min easy. Add 1 spm vs. week 1 if form holds."),
                    3: ("30 min", "6 × 3 min at 24 spm / 2 min easy — your hardest row this month."),
                    4: ("22 min", "4 × 2 min hard / 2 min easy — taper, strong finish each rep."),
                }[week]
            return {
                1: ("28 min", "6 × 2 min at 26 spm, ~90% effort / 2 min easy row."),
                2: ("32 min", "6 × 3 min at 26–28 spm / 2 min easy. Each 500 m split should hurt."),
                3: ("35 min", "8 × 2 min at 28 spm / 90 s easy — hardest rowing session this month."),
                4: ("24 min", "4 × 3 min at 26 spm / 2 min easy — taper, snappy catch each stroke."),
            }[week]

        elif "elliptical" in act:
            if low_fit:
                return {
                    1: ("25 min", "5 × 2 min high resistance / 2 min easy glide. Push stride rate up on the hard intervals."),
                    2: ("28 min", "6 × 2 min hard / 2 min easy. Same resistance, add one rep."),
                    3: ("30 min", "6 × 3 min hard / 2 min easy — peak elliptical session."),
                    4: ("22 min", "4 × 2 min hard / 2 min easy — taper, keep the power."),
                }[week]
            return {
                1: ("28 min", "6 × 2 min max resistance / 2 min easy. Arms and legs fully engaged."),
                2: ("32 min", "6 × 3 min hard / 2 min easy glide. Add +1 resistance vs. week 1."),
                3: ("35 min", "8 × 2 min all-out / 90 s easy — hardest elliptical session this month."),
                4: ("24 min", "4 × 3 min hard / 2 min easy — taper, stay explosive."),
            }[week]

        elif "stair" in act:
            if low_fit:
                return {
                    1: ("25 min", "5 × 2 min at +3 levels above base / 2 min base level recovery. Build stair power."),
                    2: ("28 min", "6 × 2 min hard / 2 min base recovery. Add 1 level vs. week 1."),
                    3: ("30 min", "6 × 3 min at highest level you can hold / 2 min base — peak stair session."),
                    4: ("22 min", "4 × 2 min hard / 2 min base — taper, legs sharp."),
                }[week]
            return {
                1: ("28 min", "6 × 2 min at near-max level / 2 min base level recovery."),
                2: ("32 min", "6 × 3 min hard / 2 min base. Push level higher than week 1."),
                3: ("35 min", "8 × 2 min max level / 90 s base — hardest stair session this month."),
                4: ("24 min", "4 × 3 min hard / 2 min base — taper, finish each rep strong."),
            }[week]

        elif "hiit" in act:
            if low_fit:
                return {
                    1: ("20 min", "5 rounds: 30 s work (burpee or squat jump) / 90 s rest. Full recovery between rounds."),
                    2: ("22 min", "6 rounds: 30 s work / 75 s rest. Add one round vs. week 1."),
                    3: ("25 min", "6 rounds: 40 s work / 60 s rest — hardest HIIT session this month."),
                    4: ("18 min", "4 rounds: 30 s work / 90 s rest — taper, stay sharp."),
                }[week]
            return {
                1: ("22 min", "6 rounds: 40 s max-effort (burpee, squat jump, or sprint) / 80 s rest."),
                2: ("25 min", "7 rounds: 40 s max-effort / 70 s rest. Shorten rest vs. week 1."),
                3: ("28 min", "8 rounds: 40 s max / 60 s rest — hardest HIIT session this month."),
                4: ("20 min", "5 rounds: 30 s max / 90 s rest — taper, explosive quality over quantity."),
            }[week]

        else:
            if low_fit:
                return {
                    1: ("25 min", "5 × 2 min moderately hard / 2 min easy (Zone 3-4) — build interval tolerance."),
                    2: ("28 min", "6 × 2 min moderately hard / 2 min easy."),
                    3: ("30 min", "6 × 3 min hard / 2 min easy — your toughest interval session this month."),
                    4: ("22 min", "4 × 2 min hard / 2 min easy — taper, stay sharp."),
                }[week]
            return {
                1: ("28 min", "6 × 2 min hard (Zone 4-5) / 2 min easy recovery."),
                2: ("32 min", "6 × 3 min hard / 2 min easy."),
                3: ("35 min", "8 × 2 min hard / 90 s easy — your hardest session this month."),
                4: ("24 min", "4 × 3 min hard / 2 min easy — taper, keep the legs snappy."),
            }[week]

    def _cardio_long_rx(week, activity=""):
        """Activity-specific long aerobic session prescriptions."""
        act = activity.lower()

        if "running" in act or "jogging" in act:
            return {
                1: ("50 min", "Long easy run — pure volume at conversational pace. Don't watch splits. This is your aerobic foundation."),
                2: ("60 min", "Long easy run, 10 min longer than week 1 — same effort, let pace drift naturally."),
                3: ("70 min", "Long run with the final 10 min slightly brisker — still aerobic, just a hint of tempo at the end."),
                4: ("45 min", "Easy long run, taper week — shorter and genuinely comfortable. Arrive at reassessment fresh."),
            }[week]

        elif "cycling" in act:
            return {
                1: ("60 min", "Long Zone 2 ride — flat or rolling route, 80–90 rpm, completely conversational. Build the aerobic engine."),
                2: ("75 min", "Long ride, 15 min longer — add a small hill mid-ride but keep overall effort easy."),
                3: ("85 min", "Long ride with the final 15 min at a slightly brisker pace (Zone 3). Push gently at the end."),
                4: ("55 min", "Easy long ride, taper — comfortable effort, enjoy the route."),
            }[week]

        elif "swimming" in act:
            return {
                1: ("40 min", "Continuous easy swim — mix strokes every 200 m, focus on relaxed breathing and stroke efficiency."),
                2: ("50 min", "Long swim, 10 min longer — alternate freestyle and backstroke every 4 lengths to vary muscle load."),
                3: ("55 min", "Long swim with the final 10 min as a slightly harder tempo — controlled speed, technique must hold."),
                4: ("40 min", "Easy long swim, taper — relax in the water, focus on feel not distance."),
            }[week]

        elif "rowing" in act:
            return {
                1: ("50 min", "Long easy row at 18–20 spm — focus on sequencing consistency the whole session. Pure aerobic base."),
                2: ("60 min", "Long row, 10 min longer — maintain 18–20 spm, let the metres accumulate naturally."),
                3: ("70 min", "Long row with the final 10 min at 22 spm — lift the rate, keep the effort sustainable."),
                4: ("45 min", "Easy long row — taper week, comfortable pace, finish feeling good."),
            }[week]

        elif "elliptical" in act:
            return {
                1: ("55 min", "Long easy elliptical — moderate resistance, full arm engagement, completely conversational effort."),
                2: ("65 min", "Long elliptical, 10 min longer — add 1 resistance level mid-session if heart rate drops below Zone 2."),
                3: ("75 min", "Long elliptical with the final 10 min at +2 resistance — sustained aerobic push at the end."),
                4: ("50 min", "Easy long elliptical — taper week, comfortable resistance, shorter duration."),
            }[week]

        elif "stair" in act:
            return {
                1: ("40 min", "Long stair session at base level — steady continuous effort, no intervals, build leg endurance."),
                2: ("50 min", "Long stair, 10 min longer — add 1 level vs. week 1 if heart rate is still comfortable."),
                3: ("55 min", "Long stair with final 10 min at +2 levels — sustained effort, don't hold the rails."),
                4: ("35 min", "Easy stair endurance — taper week, comfortable level, finish fresh."),
            }[week]

        elif "hiit" in act:
            return {
                1: ("35 min", "Active recovery: 35 min continuous low-intensity bodyweight circuit — squats, lunges, push-ups at easy pace."),
                2: ("40 min", "Low-intensity circuit, 5 min longer — add one exercise but keep the effort genuinely easy."),
                3: ("40 min", "Aerobic circuit: 8 exercises × 40 s on / 20 s rest, 2 rounds. Moderate pace — complement the HIIT days."),
                4: ("35 min", "Easy movement circuit — taper week, flush the body, arrive at reassessment ready."),
            }[week]

        else:
            return {
                1: ("50 min", "Steady, easy pace — pure volume, conversational effort throughout."),
                2: ("60 min", "Steady, easy pace — 10 minutes longer than last week."),
                3: ("70 min", "Steady pace, with the last 10 minutes slightly brisker than the rest."),
                4: ("45 min", "Easy pace — taper week, shorter session, same comfortable effort."),
            }[week]

    def _low_rx(week, activity=""):
        """Activity-specific low-impact prescriptions with weekly progression."""
        act = activity.lower()

        if "brisk walking" in act:
            return {
                1: ("25 min", "Brisk walk at ~5.5 km/h — arms swinging, purposeful stride, heart rate ~110–120 bpm. Warm up 5 min easy first."),
                2: ("30 min", "Brisk walk, 5 min longer — push the pace slightly, aim for 6 km/h if it feels comfortable."),
                3: ("35 min", "Brisk walk with 3 × 3 min at near-power-walk pace mid-session. Recover to normal brisk pace between."),
                4: ("25 min", "Brisk walk taper — comfortable pace, finish feeling energised not tired."),
            }[week]

        elif "walking" in act:
            return {
                1: ("25 min", "Easy casual walk at comfortable pace — fresh air, low heart rate (~100 bpm), active recovery mindset."),
                2: ("30 min", "Easy walk, 5 min longer — add a gentle hill if possible to vary the stimulus."),
                3: ("30 min", "Easy walk with 2 × 5 min slightly faster pace — not brisk, just a shade quicker than your normal stroll."),
                4: ("25 min", "Easy walk — taper week, purely for movement and fresh air."),
            }[week]

        elif "yoga" in act or "pilates" in act:
            return {
                1: ("30 min", "Foundation session — 5 min breathwork, 20 min basic poses or Pilates fundamentals, 5 min savasana/rest."),
                2: ("35 min", "Build session — add 2–3 new poses or Pilates progressions. Hold each pose 5 s longer than week 1."),
                3: ("40 min", "Challenge session — attempt your hardest pose or sequence. Full class or flow at 75% effort."),
                4: ("30 min", "Restorative session — yin yoga or gentle Pilates. Passive holds, deep breathing, full recovery."),
            }[week]

        elif "housework" in act or "chores" in act:
            return {
                1: ("30 min", "30 min of active chores (vacuuming, mopping, scrubbing) — keep moving continuously, no sitting breaks."),
                2: ("35 min", "35 min of active chores — increase the pace or tackle a more physical task (moving furniture, deep clean)."),
                3: ("40 min", "40 min active chores at a slightly higher tempo — combine upper and lower body tasks back-to-back."),
                4: ("30 min", "30 min light chores — taper week, nothing heavy."),
            }[week]

        elif "gardening" in act or "yard" in act:
            return {
                1: ("30 min", "30 min of active gardening — digging, raking or weeding continuously. Good compound movement."),
                2: ("35 min", "35 min — tackle a heavier task: wheelbarrow loads, shifting compost, or digging a new bed."),
                3: ("40 min", "40 min of your most physically demanding garden task — sustained effort the whole time."),
                4: ("30 min", "30 min light gardening — planting, light weeding, easy tasks. Taper week."),
            }[week]

        else:
            return {
                1: ("25 min", "Easy effort activity, heart rate below ~120 bpm — pure recovery, mobility and movement."),
                2: ("30 min", "Easy effort, 5 min longer — gentle progression, still very comfortable."),
                3: ("30 min", "Easy effort with 2 × 3 min slightly livelier pace mid-session. Return to easy after each."),
                4: ("25 min", "Easy recovery activity — taper week, arrive at reassessment feeling fresh."),
            }[week]

    def _sport_rx(week, day_idx=0, activity=""):
        """
        Returns (duration, prescription) specific to the sport, week theme, and day of the week.
        day_idx: 0=Mon … 5=Sat  (Sunday is always rest, never reaches here)
        week: 1=Foundation, 2=Build, 3=Push, 4=Taper
        activity: the exact activity string from ACT_CATEGORY, used to pick sport-specific cues.
        Day types rotate so every session within a week is different:
          0=technique, 1=drills, 2=intervals, 3=tactical, 4=match, 5=conditioning
        """
        day_types = {0: "technique", 1: "drills", 2: "intervals",
                     3: "tactical",  4: "match",  5: "conditioning"}
        dtype = day_types.get(day_idx % 6, "technique")

        # ── TABLE TENNIS ─────────────────────────────────────────────────────────
        if "table tennis" in activity.lower() or "bordtennis" in activity.lower():
            P = {
                1: {
                    "technique":     ("30 min", "Slow-ball stroke mechanics — focus on contact point and consistent racket angle. No pace, pure form."),
                    "drills":        ("30 min", "Multiball FH & BH alternations — 20 balls per set, 60 s rest. Precision over speed."),
                    "intervals":     ("30 min", "Rally bursts: 10 strokes at 60% pace, 30 s rest × 8 sets. Learn the rhythm, not the pace."),
                    "tactical":      ("30 min", "Serve + 3rd-ball attack at half pace — one serve variation, repeat until automatic."),
                    "match":         ("35 min", "Friendly practice match at 70% — focus on placement, not winning."),
                    "conditioning":  ("35 min", "Long-rally endurance: both players aim for 20+ shot rallies, full footwork recovery between points."),
                },
                2: {
                    "technique":     ("35 min", "Add topspin to FH drives — 3 sets × 15 reps each side, full hip rotation."),
                    "drills":        ("40 min", "Combo drill: FH cross-court → BH cross-court → FH down-the-line. Rotate every 15 balls."),
                    "intervals":     ("35 min", "Pressure drills: 15 strokes at 75% pace, 20 s rest × 10 sets."),
                    "tactical":      ("40 min", "2-point tactical patterns — serve short/attack long or push long/attack return."),
                    "match":         ("40 min", "Practice match at 80% — best of 5, track unforced errors per game."),
                    "conditioning":  ("40 min", "Stamina rallies: aim for 30+ shots. Prioritise footwork recovery after each point."),
                },
                3: {
                    "technique":     ("45 min", "Power FH loop — maximum topspin, 4 sets × 12 reps, full hip drive."),
                    "drills":        ("50 min", "High-speed combos at 90%+: FH loop → BH block → FH counter-loop × 12 sets."),
                    "intervals":     ("50 min", "Max-intensity bursts: 20 strokes at 95% pace, 15 s rest × 12 sets. Hardest session this month."),
                    "tactical":      ("50 min", "Full tactical pressure — varied serves, immediate attack, strong opponent or fast multiball feed."),
                    "match":         ("55 min", "Competitive match at full intensity — treat every point as a tournament point."),
                    "conditioning":  ("55 min", "Peak endurance: 40+ shot rallies, full court movement. Finish with 10 min full-speed multiball."),
                },
                4: {
                    "technique":     ("30 min", "Light stroke review at 65% — feel the form, don't force it."),
                    "drills":        ("30 min", "Best drill from week 3, half the volume. Remind muscles what good feels like."),
                    "intervals":     ("25 min", "Short sharp sets: 10 strokes at 80%, 30 s rest × 6. Snappy but not fatiguing."),
                    "tactical":      ("30 min", "One pattern only — your strongest serve + attack combo. Groove it in."),
                    "match":         ("35 min", "Relaxed practice match — notice how much sharper you feel vs. week 1."),
                    "conditioning":  ("35 min", "Easy long-rally flow — light active recovery, not a workout."),
                },
            }

        # ── TENNIS ───────────────────────────────────────────────────────────────
        elif "tennis" in activity.lower():
            P = {
                1: {
                    "technique":     ("30 min", "Groundstroke mechanics — slow-feed rallies focusing on swing path and follow-through. No pace."),
                    "drills":        ("35 min", "Cross-court FH & BH rally drill, 3 sets each side × 10 min. Consistent depth over power."),
                    "intervals":     ("30 min", "Baseline sprint-and-recover: sprint to ball, reset to centre, repeat × 10 min. Build footwork habit."),
                    "tactical":      ("30 min", "Serve + 1 rally shot patterns at 60% — pick one serve target and repeat."),
                    "match":         ("35 min", "Practice sets at 70% — focus on getting the ball in play, not hitting winners."),
                    "conditioning":  ("35 min", "Long crosscourt rallies both sides — sustain 15+ shots, track rally length."),
                },
                2: {
                    "technique":     ("40 min", "Add topspin to BH — 3 sets of slow-to-medium feeds, exaggerate the low-to-high swing."),
                    "drills":        ("40 min", "Inside-out FH drill + BH down-the-line combo — 20 min each. Moderate pace."),
                    "intervals":     ("35 min", "Approach-shot sprint: short ball → move in → volley finish. 8 reps each side, 45 s rest."),
                    "tactical":      ("40 min", "Serve + return patterns: focus on 2-3 specific tactical constructions per set."),
                    "match":         ("45 min", "Practice match at 80% — play tiebreaks to build pressure tolerance."),
                    "conditioning":  ("40 min", "Sustained baseline rally sets — 20+ shots, keep feet moving the whole time."),
                },
                3: {
                    "technique":     ("45 min", "Full-power groundstrokes — max pace with controlled direction. 4 sets each side × 8 balls."),
                    "drills":        ("50 min", "High-tempo combo: FH inside-out → BH cross-court → approach → volley. 12 reps, full intensity."),
                    "intervals":     ("50 min", "Side-to-side defensive scramble: wide ball left, recover, wide ball right × 15 reps. Hardest session."),
                    "tactical":      ("50 min", "Match-simulation: specific patterns under score pressure, coach calling out game situations."),
                    "match":         ("55 min", "Full competitive set play at 100% — treat every game like a tournament match."),
                    "conditioning":  ("55 min", "Peak baseline endurance: 25+ shot rallies, maximum footwork, no slowing down."),
                },
                4: {
                    "technique":     ("30 min", "Easy groundstroke flow at 65% — smooth rhythm, no forcing."),
                    "drills":        ("30 min", "Favourite drill from week 3 at half volume. Stay loose and confident."),
                    "intervals":     ("25 min", "Light lateral sprints: 6 reps each side, 45 s rest. Stay sharp, not tired."),
                    "tactical":      ("30 min", "One serving pattern only — groove your best serve + first-strike combo."),
                    "match":         ("35 min", "Relaxed hitting session — play points but enjoy it, notice the improvement."),
                    "conditioning":  ("35 min", "Easy cross-court rallies — light aerobic flow, finish feeling fresh."),
                },
            }

        # ── SQUASH ───────────────────────────────────────────────────────────────
        elif "squash" in activity.lower():
            P = {
                1: {
                    "technique":     ("30 min", "Solo wall-hitting: straight drives both sides, focus on smooth swing and consistent height on the front wall."),
                    "drills":        ("30 min", "Boast & drive drill with a partner — feeder boasts, you drive straight, 10 min each side."),
                    "intervals":     ("30 min", "Ghost movement drill: 6-point ghost pattern × 6 reps, 60 s rest. Build court-movement habit."),
                    "tactical":      ("30 min", "Length game — rally to a back-corner target, penalise anything short. 70% pace."),
                    "match":         ("35 min", "Practice game at 70% — focus on length and width, not winning."),
                    "conditioning":  ("35 min", "Sustained straight-drive pairs: keep 15+ shot rallies going, both corners, recover position each time."),
                },
                2: {
                    "technique":     ("35 min", "Add disguise — same swing path for drive and drop. 3 sets of 10 drives + 2 drop-shot variations."),
                    "drills":        ("40 min", "3-shot combo: boast → cross-court drive → volley drop. 8 min on, 2 min rest × 3."),
                    "intervals":     ("35 min", "Court sprints: T-position → front corner → back corner → T. 10 reps, 30 s rest. Moderate effort."),
                    "tactical":      ("40 min", "Width game — rally wide to side walls, force the weak volley return, attack the short ball."),
                    "match":         ("45 min", "Practice games at 80% — best of 5, count unforced errors."),
                    "conditioning":  ("40 min", "Long rally pairs: 20+ shots each rally, high pace, full recovery to T after every shot."),
                },
                3: {
                    "technique":     ("45 min", "Attack from length — drive deep, step in on the short reply, hit a hard winner. 4 × 8 reps."),
                    "drills":        ("50 min", "High-speed 3-shot combo at 90%: boast → nick → straight drive. 12 reps, 20 s rest. Peak drill intensity."),
                    "intervals":     ("50 min", "Max-intensity ghost: 9-point ghost × 8 reps, 45 s rest. Hardest movement session this month."),
                    "tactical":      ("50 min", "Full match pressure drills — coach feeds random feeds, you construct a winner from any position."),
                    "match":         ("55 min", "Competitive games at 100% — no mercy, treat every point as a match point."),
                    "conditioning":  ("55 min", "Peak endurance rally: 25+ shots at near-match pace. Push the aerobic ceiling."),
                },
                4: {
                    "technique":     ("30 min", "Easy solo wall-hitting at 65% — fluent rhythm, no forcing."),
                    "drills":        ("30 min", "Boast & drive at moderate pace — half the reps of week 3. Keep it clean."),
                    "intervals":     ("25 min", "Light 6-point ghost × 5 reps, 60 s rest. Stay sharp, don't fatigue."),
                    "tactical":      ("30 min", "Length game only — groove the bread-and-butter straight drive. One pattern, perfect execution."),
                    "match":         ("35 min", "Easy practice game — play freely and notice how automatic the movement feels."),
                    "conditioning":  ("35 min", "Relaxed straight-drive pairs — easy aerobic flow, finish feeling fresh."),
                },
            }

        # ── BADMINTON ────────────────────────────────────────────────────────────
        elif "badminton" in activity.lower():
            P = {
                1: {
                    "technique":     ("30 min", "Clear & drop mechanics — slow feeds, focus on high contact point and wrist snap on the clear."),
                    "drills":        ("30 min", "Multi-shuttle feed: clear → drop → net lift sequence. 10 shuttles per set × 6 sets."),
                    "intervals":     ("30 min", "Footwork ladder: 6-point movement pattern around the court × 8 reps, 45 s rest."),
                    "tactical":      ("30 min", "Serve + attack pattern at 65% — short serve, net kill or push, reset. One pattern only."),
                    "match":         ("35 min", "Practice games at 70% — play to 15, focus on shuttle placement not smash speed."),
                    "conditioning":  ("35 min", "Sustained clears: both players trade high clears to the back line for 8+ shots, track rally length."),
                },
                2: {
                    "technique":     ("35 min", "Add deceptive net drops — same wrist position as the clear until the last moment. 3 sets × 12 reps."),
                    "drills":        ("40 min", "Attack-defence rotation: smash → block → lift → smash. 10 min on, 2 min rest × 3."),
                    "intervals":     ("35 min", "Pressure footwork: random 4-corner feeds at moderate pace × 10 reps, 30 s rest."),
                    "tactical":      ("40 min", "Double-attack patterns: push to BH side → attack the weak return. Two patterns, alternate."),
                    "match":         ("45 min", "Practice games at 80% — best of 3 to 21, note where errors come from."),
                    "conditioning":  ("40 min", "Rally pairs: mix clears and drops, sustain 12+ shots, full court recovery each point."),
                },
                3: {
                    "technique":     ("45 min", "Full-power smash mechanics — jump smash technique, 4 sets × 8 reps, max racket speed."),
                    "drills":        ("50 min", "High-speed 4-shot combo at 90%: smash → block → lift → re-smash × 12 reps. Hardest drill this month."),
                    "intervals":     ("50 min", "Max-intensity random feeds: 6-corner random at 90%+ speed × 10 reps, 20 s rest."),
                    "tactical":      ("50 min", "Full match-pressure tactics: serve rotation, attack construction, forced errors under score pressure."),
                    "match":         ("55 min", "Full competitive games at 100% — tournament mindset every point."),
                    "conditioning":  ("55 min", "Peak endurance: sustained fast-tempo rallies 15+ shots, push aerobic limit the whole session."),
                },
                4: {
                    "technique":     ("30 min", "Easy clear & drop at 65% — fluid motion, no forcing."),
                    "drills":        ("30 min", "Multi-shuttle feed at half volume — stay clean, not fast."),
                    "intervals":     ("25 min", "Light 4-corner feeds × 6 reps, 45 s rest. Sharp, not tired."),
                    "tactical":      ("30 min", "One serve + first-attack pattern — automate your strongest opener."),
                    "match":         ("35 min", "Relaxed practice game — enjoy the rhythm, notice the improvement since week 1."),
                    "conditioning":  ("35 min", "Easy clear rally pairs — light aerobic flow, finish fresh."),
                },
            }

        # ── BASKETBALL / TEAM SPORTS ─────────────────────────────────────────────
        elif "basketball" in activity.lower() or "team sports" in activity.lower():
            P = {
                1: {
                    "technique":     ("30 min", "Ball-handling & dribbling fundamentals — stationary and moving, both hands, 70% speed."),
                    "drills":        ("35 min", "Shooting form drill: 5 spots around the key, 5 shots each, slow and deliberate."),
                    "intervals":     ("30 min", "Defensive slide intervals: slide baseline-to-baseline × 8 reps, 45 s rest. Build lateral habit."),
                    "tactical":      ("30 min", "Pick-and-roll read drill at walk-through pace — identify the coverage and make the correct pass."),
                    "match":         ("35 min", "3-on-3 half-court scrimmage at 70% — focus on decisions, not athleticism."),
                    "conditioning":  ("35 min", "Full-court light transition runs: walk back, jog forward × 15 laps."),
                },
                2: {
                    "technique":     ("40 min", "Mid-range shooting off the dribble — jab-step pull-up, 3 sets × 10 reps each side."),
                    "drills":        ("40 min", "2-man passing & cutting drill: give-and-go, back-cut, 10 min each pattern."),
                    "intervals":     ("35 min", "Suicide sprints: half-court × 6 reps, full-court × 4 reps, 60 s rest between sets."),
                    "tactical":      ("40 min", "Transition offence drill: rebound → outlet → layup. 3 reps then switch roles. Moderate pace."),
                    "match":         ("45 min", "4-on-4 half-court at 80% — call your own fouls, emphasise communication."),
                    "conditioning":  ("40 min", "Full-court aerobic runs: steady pace with ball, change direction every 30 s."),
                },
                3: {
                    "technique":     ("45 min", "Contested shooting under fatigue — shoot immediately after a sprint to the spot. 4 sets × 8 reps."),
                    "drills":        ("50 min", "High-intensity 3-man weave full-court × 12 reps — max speed, no mistakes. Hardest drill this month."),
                    "intervals":     ("50 min", "Game-speed suicides: full-court × 8 reps, 30 s rest. Peak conditioning session."),
                    "tactical":      ("50 min", "5-on-5 half-court with coach calling plays — execute under real pressure."),
                    "match":         ("55 min", "Full 5-on-5 scrimmage at 100% — game pace, tournament mindset."),
                    "conditioning":  ("55 min", "Full-court interval runs: 10 sprints, 10 jog-backs. Finish with 10 min defensive slides."),
                },
                4: {
                    "technique":     ("30 min", "Easy shooting around — free throws and elbow jumpers at 65% effort."),
                    "drills":        ("30 min", "Light passing and cutting — half the volume of week 3, relaxed pace."),
                    "intervals":     ("25 min", "Half-court slides only × 6 reps, 60 s rest. Stay mobile, not exhausted."),
                    "tactical":      ("30 min", "Walk-through of your best play set — mental reps, no full-speed execution."),
                    "match":         ("35 min", "3-on-3 light scrimmage — enjoy it, notice how sharp your reads feel."),
                    "conditioning":  ("35 min", "Easy full-court jog with ball — light aerobic flush, finish feeling fresh."),
                },
            }

        # ── SOCCER / FOOTBALL ────────────────────────────────────────────────────
        elif "soccer" in activity.lower() or "football" in activity.lower():
            P = {
                1: {
                    "technique":     ("30 min", "First-touch control drill — 50 touches each foot with a wall or partner feed at 60% pace."),
                    "drills":        ("35 min", "Passing triangle: 3-player 5m triangle, one-touch passes × 10 min, then two-touch × 10 min."),
                    "intervals":     ("30 min", "Agility ladder footwork: 6 patterns × 5 reps each, 45 s rest. Build movement habit."),
                    "tactical":      ("30 min", "Positional rondo: 4v2 in a 10m square, focus on movement off the ball, not pace."),
                    "match":         ("35 min", "Small-sided game 4v4 at 70% — emphasis on passing combinations, not goals."),
                    "conditioning":  ("35 min", "Aerobic endurance run: 30 min at conversational pace, then 5 min cool-down dribble."),
                },
                2: {
                    "technique":     ("40 min", "Shooting technique — driven shot and placed finish from the edge of the box, 3 sets × 8 reps each."),
                    "drills":        ("40 min", "1-2 combination + finish: wall pass into a shot, 10 reps each side. Moderate pace."),
                    "intervals":     ("35 min", "High-intensity runs: 20m sprint → jog back × 10 reps, 30 s rest. Build sprint capacity."),
                    "tactical":      ("40 min", "Pressing drill: 6v6 with a pressing trigger — compact shape, immediate press on back-pass."),
                    "match":         ("45 min", "7v7 match at 80% — call out tactical patterns as they happen."),
                    "conditioning":  ("40 min", "Fartlek run: alternate 1 min hard / 2 min easy for 30 min. Ball optional."),
                },
                3: {
                    "technique":     ("45 min", "Power shooting under pressure — shoot immediately after a sprint, both feet, 4 sets × 8 reps."),
                    "drills":        ("50 min", "High-tempo possession drill: 6v3 rondo at full pace × 12 min, 2 min rest × 3. Hardest drill this month."),
                    "intervals":     ("50 min", "Match-intensity sprints: 30m × 10, 20 s rest. Plus 4 × 4 min hard runs, 3 min easy. Peak session."),
                    "tactical":      ("50 min", "Full 11v11 tactical shape practice — transitions, set-pieces and pressing under match intensity."),
                    "match":         ("55 min", "Full 11-a-side scrimmage at 100% — tournament intensity every minute."),
                    "conditioning":  ("55 min", "High-intensity intervals: 8 × 3 min at 90%+ effort with 2 min active recovery. Push the aerobic ceiling."),
                },
                4: {
                    "technique":     ("30 min", "Easy first-touch and passing at 65% — clean and confident, no forcing."),
                    "drills":        ("30 min", "Light passing triangle, half volume — keep it flowing and relaxed."),
                    "intervals":     ("25 min", "6 × 20m strides at 80% — stay sharp without accumulating fatigue."),
                    "tactical":      ("30 min", "Walk-through of your team's best attacking pattern at slow pace."),
                    "match":         ("35 min", "4v4 light game — enjoy it and notice how your positioning has improved."),
                    "conditioning":  ("35 min", "Easy aerobic jog 25 min — active recovery, arrive at the next session fresh."),
                },
            }

        # ── DANCING ──────────────────────────────────────────────────────────────
        elif "dancing" in activity.lower():
            P = {
                1: {
                    "technique":     ("30 min", "Isolations & footwork fundamentals — body rolls, hip isolation, weight shifts. Mirror work at 50% speed."),
                    "drills":        ("30 min", "8-count phrase repetition: learn one 8-count combo, repeat 20× until automatic."),
                    "intervals":     ("30 min", "Cardio rhythm session: freestyle to 3 min tracks × 6 rounds, 60 s rest. Easy effort, stay musical."),
                    "tactical":      ("30 min", "Musicality training — listen to 5 different tracks, mark the beat and phrase changes with movement."),
                    "match":         ("35 min", "Freestyle floor session at 70% — dance to 8 random tracks, focus on connection to the music."),
                    "conditioning":  ("35 min", "Choreography run-through at half pace — build the sequence from start to finish without stopping."),
                },
                2: {
                    "technique":     ("35 min", "Add dynamics — contrast sharp hits with smooth flows in the same 8-count. 3 × 10 min phrase work."),
                    "drills":        ("40 min", "Partner or mirror drill: call-and-response, one leads 4 counts then switch. 20 min each role."),
                    "intervals":     ("35 min", "Cardio bursts: 4 min freestyle at 75% effort, 1 min rest × 6. Keep the groove through the fatigue."),
                    "tactical":      ("40 min", "Stylistic training — pick one style (heels, hip-hop, latin) and drill its specific technique × 30 min."),
                    "match":         ("40 min", "Performance run-through at 80%: film yourself, review once, identify one thing to fix."),
                    "conditioning":  ("40 min", "Full choreography × 3 run-throughs with 2 min rest — build performance endurance."),
                },
                3: {
                    "technique":     ("45 min", "Power & precision — execute each move at full expression and energy. 4 sets of your hardest phrase."),
                    "drills":        ("50 min", "High-tempo combo drills at 90%: full-speed 8-count phrases × 15 reps, 30 s rest. Hardest drill this month."),
                    "intervals":     ("50 min", "Peak cardio: 5 min freestyle at 90% effort, 90 s rest × 6. Push the aerobic ceiling."),
                    "tactical":      ("50 min", "Performance-pressure session: dance in front of others or film every run — simulate the real thing."),
                    "match":         ("55 min", "Full performance at 100% — every track as if it's show night."),
                    "conditioning":  ("55 min", "Endurance choreo: full routine × 5 run-throughs, 90 s rest. Test what you're made of."),
                },
                4: {
                    "technique":     ("30 min", "Easy isolation flow at 65% — feel the movement, no forcing."),
                    "drills":        ("30 min", "Favourite 8-count from week 3, half the reps. Stay loose and musical."),
                    "intervals":     ("25 min", "Light freestyle: 3 min easy dance, 1 min rest × 5. Enjoy the rhythm."),
                    "tactical":      ("30 min", "Musicality review — one track, full attention on phrasing and dynamics. No stress."),
                    "match":         ("35 min", "Relaxed floor session — dance for fun and notice how much more natural it feels."),
                    "conditioning":  ("35 min", "Easy choreo run-through × 2 — light active recovery, arrive at the next session fresh."),
                },
            }

        # ── GENERIC SPORT FALLBACK ───────────────────────────────────────────────
        else:
            P = {
                1: {
                    "technique":     ("30 min", "Skill fundamentals at 60% intensity — focus on clean movement patterns and form over speed."),
                    "drills":        ("30 min", "Repetition drill: choose one core skill, 6 sets × 10 reps, 60 s rest. Quality over quantity."),
                    "intervals":     ("30 min", "Effort bursts: 30 s at 70% / 60 s easy × 8 rounds. Build work capacity."),
                    "tactical":      ("30 min", "Decision-making drill at half pace — slow down the game to understand the patterns."),
                    "match":         ("35 min", "Practice session at 70% — play points / situations, focus on execution not outcome."),
                    "conditioning":  ("35 min", "Sustained aerobic activity in your sport: 30 min easy, track how your breathing settles."),
                },
                2: {
                    "technique":     ("35 min", "Technique refinement — add one layer of complexity to the skill you drilled in week 1."),
                    "drills":        ("40 min", "Combination drill: link two skills together, 4 sets × 8 reps, moderate pace."),
                    "intervals":     ("35 min", "Effort bursts: 30 s at 80% / 45 s easy × 10 rounds. Push slightly harder than week 1."),
                    "tactical":      ("40 min", "2-option tactical reads — read one cue, pick the correct response. Moderate speed."),
                    "match":         ("45 min", "Practice session at 80% — track one error pattern and work to eliminate it."),
                    "conditioning":  ("40 min", "Sustained sport-specific aerobic effort: 35 min with 3 short harder bursts woven in."),
                },
                3: {
                    "technique":     ("45 min", "Full-speed skill execution under fatigue — perform the skill immediately after a sprint. 4 × 8 reps."),
                    "drills":        ("50 min", "High-speed combo drills at 90%+ — link 3 skills, full intensity × 12 reps. Hardest drill session."),
                    "intervals":     ("50 min", "Peak effort intervals: 40 s at 90-95% / 30 s easy × 12 rounds. Push the aerobic ceiling."),
                    "tactical":      ("50 min", "Full match-pressure tactical drill — random scenarios, fast decisions, no thinking time."),
                    "match":         ("55 min", "Full-intensity practice at 100% — treat every rep or point as competition."),
                    "conditioning":  ("55 min", "Peak endurance: 45 min sustained sport effort at the highest pace you can maintain."),
                },
                4: {
                    "technique":     ("30 min", "Easy skill flow at 65% — feel the movement, no forcing."),
                    "drills":        ("30 min", "Best drill from week 3 at half volume — clean reps, relaxed pace."),
                    "intervals":     ("25 min", "Light effort bursts: 20 s at 75% / 60 s easy × 6. Snappy but not fatiguing."),
                    "tactical":      ("30 min", "One tactical pattern only — automate your strongest play."),
                    "match":         ("35 min", "Relaxed practice session — enjoy it and notice how much sharper everything feels."),
                    "conditioning":  ("35 min", "Easy aerobic activity: 30 min at conversational pace. Active recovery, arrive at next session fresh."),
                },
            }

        dur, rx = P[week][dtype]
        return dur, rx

    STRENGTH_SPLITS = ["Full-Body Strength A - push emphasis", "Full-Body Strength B - pull emphasis", "Full-Body Strength C - lower-body emphasis"]

    def _weekly_template(goal):
        gl = (goal or "").lower()
        if "muscle" in gl:
            return [("Monday","strength"),("Tuesday","cardio_easy"),("Wednesday","strength"),
                    ("Thursday","sport"),("Friday","strength"),("Saturday","cardio_long"),("Sunday","rest")]
        if "fat" in gl:
            return [("Monday","strength"),("Tuesday","cardio_easy"),("Wednesday","cardio_interval"),
                    ("Thursday","strength"),("Friday","cardio_easy"),("Saturday","sport"),("Sunday","rest")]
        return [("Monday","strength"),("Tuesday","cardio_easy"),("Wednesday","sport"),
                ("Thursday","strength"),("Friday","cardio_interval"),("Saturday","sport"),("Sunday","rest")]

    def _resolve_role(role):
        if role == "strength" and not has_strength_act:
            role = "sport" if has_sport_act else ("cardio_easy" if has_cardio_act else "low")
        if role.startswith("cardio") and not has_cardio_act:
            role = "sport" if has_sport_act else "low"
        if role == "sport" and not has_sport_act:
            role = "cardio_long" if has_cardio_act else "low"
            if role.startswith("cardio") and not has_cardio_act:
                role = "low"
        return role

    def build_30_day_plan(goal, pct):
        template = _weekly_template(goal)
        counters = {"strength": 0, "cardio": 0, "sport": 0, "low": 0}
        weeks_out = []
        for week in range(1, 5):
            rows = []
            day_idx = 0  # tracks position within the week for day-varied prescriptions
            for day_name, role in template:
                r = _resolve_role(role)
                if r == "rest":
                    rows.append((day_name, "Rest", "Full rest, or light stretching / mobility work (10-15 min).", "—", "rest"))
                    day_idx += 1
                    continue
                if r == "strength":
                    act = plan30_strength[counters["strength"] % len(plan30_strength)]
                    split = STRENGTH_SPLITS[counters["strength"] % len(STRENGTH_SPLITS)]
                    counters["strength"] += 1
                    dur, rx = _strength_rx(week, day_idx, activity=act)
                    rows.append((day_name, "Strength", f"{act} - {split}. {rx}", dur, "strength"))
                elif r in ("cardio_easy", "cardio_interval", "cardio_long"):
                    act = plan30_cardio[counters["cardio"] % len(plan30_cardio)]
                    counters["cardio"] += 1
                    if r == "cardio_easy":
                        dur, rx = _cardio_easy_rx(week, activity=act); label = "Cardio - Easy"
                    elif r == "cardio_interval":
                        dur, rx = _cardio_interval_rx(week, pct, activity=act); label = "Cardio - Intervals"
                    else:
                        dur, rx = _cardio_long_rx(week, activity=act); label = "Cardio - Long"
                    rows.append((day_name, label, f"{act}: {rx}", dur, r))
                elif r == "sport":
                    act = plan30_sport[counters["sport"] % len(plan30_sport)]
                    counters["sport"] += 1
                    dur, rx = _sport_rx(week, day_idx, activity=act)
                    rows.append((day_name, "Sport", f"{act} - {rx}", dur, "sport"))
                else:
                    act = plan30_low[counters["low"] % len(plan30_low)]
                    counters["low"] += 1
                    dur, rx = _low_rx(week, activity=act)
                    rows.append((day_name, "Active Recovery", f"{act} - {rx}", dur, "low"))
                day_idx += 1
            weeks_out.append(rows)
        return weeks_out

    WEEK_THEMES = {
        1: ("Week 1 - Foundation", "Establish the rhythm and nail technique before adding load or intensity."),
        2: ("Week 2 - Build", "Small, deliberate increases in volume and load across the board."),
        3: ("Week 3 - Push", "Your hardest week - peak intensity across strength, cardio and sport."),
        4: ("Week 4 - Taper & Reassess", "A slightly lighter week to absorb the adaptations before you re-test."),
    }

    ROLE_COLOR = {
        "strength": BLUE, "cardio_easy": ACCENT, "cardio_interval": BAD,
        "cardio_long": ACCENT, "sport": GOLD, "low": MUTED, "rest": DIM,
    }

    def make_week_table(rows):
        data = [[P("DAY", S("p30h1", size=7, bold=True, color=MUTED)),
                 P("FOCUS", S("p30h2", size=7, bold=True, color=MUTED)),
                 P("SESSION DETAILS", S("p30h3", size=7, bold=True, color=MUTED)),
                 P("TIME", S("p30h4", size=7, bold=True, color=MUTED, align=TA_CENTER))]]
        for r_i, (day, label, detail, dur, role) in enumerate(rows):
            col = ROLE_COLOR.get(role, MUTED)
            data.append([
                P(day, S(f"p30d_{r_i}", size=8.5, bold=True, color=TEXT)),
                P(label, S(f"p30l_{r_i}", size=8, bold=True, color=col)),
                P(detail, S(f"p30de_{r_i}", size=8, lead=12, color=MUTED)),
                P(dur, S(f"p30du_{r_i}", size=8, color=MUTED, align=TA_CENTER)),
            ])
        t = Table(data, colWidths=[24*mm, 30*mm, None, 16*mm])
        style_cmds = [
            ("BACKGROUND", (0,0), (-1,0), CARD2), ("BACKGROUND", (0,1), (-1,-1), CARD),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [CARD, CARD2]),
            ("BOX", (0,0), (-1,-1), 1, STROKE), ("INNERGRID", (0,0), (-1,-1), 0.4, STROKE),
            ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8),  # Mer padding
            ("LEFTPADDING", (0,0), (-1,-1), 7), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]
        for r_i, (day, label, detail, dur, role) in enumerate(rows, start=1):
            style_cmds.append(("LINEBEFORE", (0, r_i), (0, r_i), 2.5, ROLE_COLOR.get(role, STROKE)))
        t.setStyle(TableStyle(style_cmds))
        return t

    # ── Colour helpers ─────────────────────────────────────────────
    def bmi_color(v):
        if v is None: return MUTED
        if v < 18.5:  return BLUE
        if v < 25:    return GOOD
        if v < 30:    return WARN
        return BAD

    def vo2_color(pct):
        if pct >= 80: return GOOD
        if pct >= 60: return BLUE
        if pct >= 40: return WARN
        return BAD

    def bio_color(diff):
        if diff is None: return MUTED
        if diff <= -1: return GOOD
        if diff <= 2:  return WARN
        return BAD

    bmi_col = bmi_color(bmi_v)
    vo2_col = vo2_color(vo2_pct)
    bio_diff = (bio_v - age_f) if (bio_v is not None and age_f is not None) else None
    if bio_diff is not None:
        bio_diff = max(-5.0, min(5.0, bio_diff))
        bio_v = age_f + bio_diff
    bio_col = bio_color(bio_diff)

    # ── Health score & radar ───────────────────────────────────────
    score_parts = []
    if bmi_v is not None:
        if 18.5 <= bmi_v < 25: score_parts.append(100)
        elif 17 <= bmi_v < 27: score_parts.append(75)
        elif 15 <= bmi_v < 30: score_parts.append(50)
        else: score_parts.append(25)
    if vo2_v is not None:
        score_parts.append(min(100, int(vo2_pct)))
    if bio_diff is not None:
        score_parts.append(max(0, min(100, int(70 - bio_diff * 10))))
    if ex_total_min:
        score_parts.append(min(100, int(ex_total_min / 300 * 100)))
    health_score = int(sum(score_parts) / len(score_parts)) if score_parts else 0
    score_col   = GOOD if health_score >= 70 else WARN if health_score >= 45 else BAD
    score_label = ("Excellent" if health_score >= 80 else "Good" if health_score >= 65
                   else "Fair" if health_score >= 45 else "Needs attention")

    radar = {}
    radar["Body Comp"] = (100 if (bmi_v and 18.5 <= bmi_v < 25) else 75 if (bmi_v and 17 <= bmi_v < 27)
                           else 50 if (bmi_v and 15 <= bmi_v < 30) else 25 if bmi_v else 50)
    radar["Cardio"]    = int(vo2_pct) if vo2_v else 50
    radar["Bio Age"]   = (max(0, min(100, int(70 - bio_diff * 10))) if bio_diff is not None else 50)
    radar["Activity"]  = (min(100, int(ex_total_min / 300 * 100)) if ex_total_min else 30)
    life = 60
    for f in factors:
        try:
            d = float(f.get("delta", 0))
            if d < 0: life = min(100, life + 8)
            elif d > 1: life = max(10, life - 8)
        except Exception:
            pass
    radar["Lifestyle"] = max(0, min(100, life))

    weakest_dim = min(radar, key=lambda k: radar[k])

    # ── #1 lever ────────────────────────────────────────────────────
    if vo2_v is not None and vo2_pct < 40:
        biggest_lever = "Raise your cardio fitness (VO2max)"
        lever_why = ("This is the single most powerful longevity lever you have right now — and "
                      "also the fastest one to move. Two structured sessions a week can shift your "
                      "percentile within 6–8 weeks.")
    elif bmi_v is not None and bmi_v >= 30:
        biggest_lever = "Build a sustainable energy-balance routine"
        lever_why = ("A modest, consistent calorie deficit paired with strength training and daily "
                      "steps will move every other marker in this report — body composition, "
                      "cardio efficiency, and biological age — in the right direction at once.")
    elif bio_diff is not None and bio_diff > 2:
        biggest_lever = "Fix sleep and stress fundamentals first"
        lever_why = ("Your biological age estimate shows the largest gap is coming from lifestyle "
                      "factors, not training. Stabilising sleep timing and reducing chronic stress "
                      "is the highest-leverage change available to you this month.")
    elif exlog and ex_total_min < 150:
        biggest_lever = "Reach the WHO activity threshold (150 min/week)"
        lever_why = ("You're currently below the minimum activity guideline. Closing this gap is "
                      "associated with one of the largest single drops in all-cause mortality risk "
                      "of any lifestyle change measured.")
    else:
        biggest_lever = "Layer in progressive strength training"
        lever_why = ("Your foundations are solid. The next tier of improvement — in metabolism, "
                      "bone density, and long-term independence — comes from consistent, "
                      "progressively-loaded resistance training.")

    # ── Stop / Start / Maintain lists ──────────────────────────────
    stop_items, start_items, keep_items = [], [], []
    if bmi_v is not None and bmi_v >= 30:
        stop_items.append("Skipping meals, then over-eating in the evening")
        start_items.append(f"A gentle daily deficit toward {int(rec_kcal) if rec_kcal else 'your target'} kcal")
    elif bmi_v is not None and bmi_v >= 25:
        stop_items.append("Relying on cardio alone to manage weight")
        start_items.append("2–3 strength sessions per week to protect lean mass")
    elif bmi_v is not None and bmi_v < 18.5:
        stop_items.append("Under-eating relative to your training load")
        start_items.append("Prioritise protein at every meal (≥1.6 g/kg/day)")
    else:
        keep_items.append(f"Your weight management — BMI {bmi_v:.1f} is in range" if bmi_v else "Your current weight management")

    if vo2_v is not None and vo2_pct < 50:
        stop_items.append("Doing only low-intensity cardio")
        start_items.append("One interval session per week (e.g. 4×4 min hard)")
    elif vo2_v is not None:
        keep_items.append(f"Your cardio routine — VO2max sits at the {vo2_pct:.0f}th percentile")

    if bio_diff is not None and bio_diff > 0:
        start_items.append("A consistent sleep/wake schedule, even on weekends")
    elif bio_diff is not None:
        keep_items.append("Whatever you're doing for sleep & recovery — it's working")

    if exlog and ex_total_min < 150:
        stop_items.append("Treating exercise as optional some weeks")
        start_items.append("A fixed weekly training calendar — same slots, every week")
    elif exlog:
        keep_items.append(f"Your activity volume — {ex_total_min} min/week meets WHO guidance")

    stop_items.append("Comparing your progress to anyone else's timeline")
    start_items.append("Tracking one consistency habit daily (sleep, steps, or protein)")
    keep_items.append("Reading reports like this one — awareness drives change")

    # ── Insight + action-step generators (mirrors original logic) ─
    def insight_and_steps_body():
        if bmi_v is None:
            return None, []
        if bmi_v >= 30:
            txt = (f"Your BMI of {bmi_v:.1f} ({bmi_cat}) places you in a range where modest, "
                   f"sustainable changes outperform aggressive ones. A daily deficit of "
                   f"300–500 kcal, combined with 2–3 strength sessions a week, preserves muscle "
                   f"while the scale moves — roughly 0.5–0.75 kg per week is the sweet spot.")
            steps = ["Walk 20 minutes after your largest meal, every day",
                     "Do two full-body strength sessions this week",
                     "Track bodyweight every morning, same time, same conditions",
                     "Hit your protein target (see Nutrition page) at least 5 days"]
        elif bmi_v >= 25:
            txt = (f"Your BMI of {bmi_v:.1f} ({bmi_cat}) is slightly above the typical range. "
                   f"Strength training 2–3×/week combined with a small deficit outperforms cardio-"
                   f"only approaches — and a 0.5 kg/week pace protects far more lean mass than a "
                   f"faster one.")
            steps = ["Add one strength session to your current routine this week",
                     "Aim for the calorie target on the Nutrition page on 5 of 7 days",
                     "Take a waist-circumference measurement and note the date",
                     "Plan your meals for tomorrow tonight — decisions made in advance stick"]
        elif bmi_v < 18.5:
            txt = (f"Your BMI of {bmi_v:.1f} ({bmi_cat}) is below the typical range. The priority "
                   f"is progressive strength training with adequate total energy and protein "
                   f"(≥1.6 g/kg/day) — not a calorie deficit.")
            steps = ["Add a calorie-dense snack between two main meals",
                     "Begin or continue a structured strength programme, 3×/week",
                     "Track total daily intake for 3 days to find your real baseline",
                     "Prioritise 7–9 hours of sleep to support recovery and growth"]
        else:
            txt = (f"Your BMI of {bmi_v:.1f} ({bmi_cat}) is within the normal range. From here, "
                   f"the biggest upgrades come from cardio fitness and strength — not further "
                   f"weight changes. Use the markers on the next pages as your scoreboard.")
            steps = ["Pick one strength or cardio metric to improve this month",
                     "Schedule your training week for the next 7 days right now",
                     "Re-take this assessment in 8–12 weeks to track the trend",
                     "Maintain current habits — consistency is the win here"]
        return txt, steps

    def insight_and_steps_vo2():
        if vo2_v is None:
            return None, []
        if vo2_pct < 30:
            txt = (f"Your VO2max of {vo2_v:.1f} ml/kg/min ({vo2_pct:.0f}th percentile) is in the "
                   f"lowest tier — but this is the marker that responds fastest to training. "
                   f"VO2max is the strongest single predictor of all-cause mortality of anything "
                   f"measured in this report. Three to four 30-minute easy aerobic sessions per "
                   f"week typically produce a noticeable shift within 4–6 weeks.")
            steps = ["Three 30-minute easy-pace sessions this week (walk, cycle, swim)",
                     "Keep effort conversational — you should be able to talk in full sentences",
                     "Add one slightly longer session (45 min) on a day off work",
                     "Re-test or re-estimate VO2max in 6 weeks to see the shift"]
        elif vo2_pct < 50:
            txt = (f"Your VO2max of {vo2_v:.1f} ({vo2_pct:.0f}th percentile) is below average. "
                   f"Adding one structured interval session weekly — alongside two easy sessions — "
                   f"is the fastest path to the next bracket over 6–12 weeks.")
            steps = ["One interval session: 4×4 minutes hard, 3 minutes easy between",
                     "Two easy aerobic sessions, 30–40 minutes each",
                     "Allow at least one full rest day between hard sessions",
                     "Track how the interval session feels week to week — it should get easier"]
        elif vo2_pct < 75:
            txt = (f"Your VO2max of {vo2_v:.1f} ({vo2_pct:.0f}th percentile) is above average. "
                   f"To push higher, an 80/20 split — 80% easy, 20% hard — out-performs the 50/50 "
                   f"mix most people drift into, which causes fatigue without real adaptation.")
            steps = ["Audit last week's training: was it closer to 80/20 or 50/50?",
                     "Keep easy sessions genuinely easy — slower than feels productive",
                     "Reserve hard efforts for one, maybe two sessions a week",
                     "Add 5–10 minutes to your longest aerobic session this week"]
        else:
            txt = (f"Your VO2max of {vo2_v:.1f} ({vo2_pct:.0f}th percentile) is excellent. "
                   f"Maintenance is the goal now — 2–3 quality sessions a week. Detraining begins "
                   f"within roughly two weeks of inactivity, so consistency matters more than "
                   f"volume from here.")
            steps = ["Maintain 2–3 sessions/week — don't chase more volume",
                     "Protect one quality (harder) session per week",
                     "If you must skip a week, keep at least one short session",
                     "Use spare capacity for strength training instead"]
        return txt, steps

    def insight_and_steps_bioage():
        if bio_diff is None:
            return None, []
        if bio_diff > 3:
            txt = (f"Your estimated biological age of {bio_v:.1f} years is {bio_diff:.1f} years "
                   f"above your calendar age. This gap is driven almost entirely by lifestyle "
                   f"factors — and lifestyle factors are reversible. The biggest single levers are "
                   f"sleep consistency, cardio fitness, and stress management.")
            steps = ["Pick the single largest red factor below and address only that this week",
                     "Set a fixed bedtime and wake time — including weekends",
                     "Add one 10-minute walk after your evening meal",
                     "Re-run this assessment in 12 weeks to track the gap closing"]
        elif bio_diff > 0:
            txt = (f"Your estimated biological age ({bio_v:.1f} yrs) is {bio_diff:.1f} years above "
                   f"your calendar age — a small, easily closable gap. Focus on the amber/red "
                   f"factors in the breakdown below.")
            steps = ["Identify your top factor below and make one change this week",
                     "Track sleep duration for 7 nights",
                     "Add one extra cardio session this week",
                     "Reassess in 8–12 weeks"]
        else:
            txt = (f"Your estimated biological age ({bio_v:.1f} yrs) is {abs(bio_diff):.1f} years "
                   f"below your calendar age — a strong reflection of your current habits. "
                   f"The priority now is protecting consistency, not adding more.")
            steps = ["Keep your current sleep and training rhythm — don't disrupt what's working",
                     "Re-test in 12 weeks to confirm the trend holds",
                     "Use any extra capacity for mobility or strength work",
                     "Share this report with your physician as a baseline"]
        return txt, steps

    def insight_and_steps_nutrition():
        if not (cur_kcal and rec_kcal):
            return None, []
        d_kcal = int(rec_kcal - cur_kcal)
        if d_kcal < 0:
            txt = (f"A target of {int(rec_kcal)} kcal/day creates a deficit of {abs(d_kcal)} kcal — "
                   f"projected at {abs(kg_pw or 0):.2f} kg/week. Keep protein high throughout to "
                   f"protect muscle while body fat comes down.")
            steps = ["Hit your protein target every day this week (see table above)",
                     "Pre-log tomorrow's meals tonight",
                     "Keep one 'free' meal per week — sustainability beats perfection",
                     "Re-weigh weekly, same morning conditions, and trend (don't react to one day)"]
        elif d_kcal > 0:
            txt = (f"A target of {int(rec_kcal)} kcal/day creates a surplus of {d_kcal} kcal — "
                   f"projected at +{abs(kg_pw or 0):.2f} kg/week. Pair this with progressive "
                   f"strength training so the surplus builds tissue, not just the scale number.")
            steps = ["Add a calorie-dense snack post-workout",
                     "Keep all current strength sessions — don't skip while eating more",
                     "Track weight weekly; adjust if the trend stalls for 2+ weeks",
                     "Prioritise protein at breakfast specifically"]
        else:
            txt = (f"Your target of {int(rec_kcal)} kcal/day matches your estimated maintenance — "
                   f"ideal for body recomposition: building muscle while body fat slowly drops.")
            steps = ["Hold calories steady and let strength training do the work",
                     "Track measurements (waist, photos) rather than just weight",
                     "Reassess in 6–8 weeks as your weight may barely move",
                     "Keep protein at the top of the macro table"]
        return txt, steps

    # ── Local custom flowables (med justerte høyder) ──────────────────
    class VGap(Flowable):
        def __init__(self, h=8): super().__init__(); self._h = h
        def wrap(self, aw, ah): return aw, self._h
        def draw(self): pass

    class HRule(Flowable):
        def __init__(self, w=CONTENT_W, color=STROKE):
            super().__init__(); self.w = w; self.color = color
        def wrap(self, aw, ah): return self.w, 1
        def draw(self):
            c = self.canv; c.setStrokeColor(self.color); c.setLineWidth(0.6)
            c.line(0, 0, self.w, 0)

    class SecHeader(Flowable):
        def __init__(self, num, title, subtitle="", accent=None, width=CONTENT_W):
            super().__init__()
            self.num = num; self.title = title; self.subtitle = subtitle
            self.accent = accent or ACCENT
            self.w = width; self.h = 48 if subtitle else 38
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv
            c.setFillColor(CARD); c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)
            c.setFillColor(self.accent); c.roundRect(0, 0, 5, self.h, 2, fill=1, stroke=0)
            c.setFillAlpha(0.15); c.setFillColor(self.accent)
            c.circle(self.w - 18, self.h - 16, 16, fill=1, stroke=0)
            c.setFillAlpha(1.0)
            if self.num:
                c.setFillColor(self.accent); c.setFont("Helvetica-Bold", 9)
                c.drawString(16, self.h - 14, str(self.num))
                c.setFillColor(TEXT); c.setFont("Helvetica-Bold", 13.5)
                c.drawString(40, self.h - 23, self.title)
            else:
                c.setFillColor(TEXT); c.setFont("Helvetica-Bold", 13.5)
                c.drawString(16, self.h - 23, self.title)
            if self.subtitle:
                c.setFillColor(MUTED); c.setFont("Helvetica", 7.5)
                c.drawString(16, 9, self.subtitle[:100])

    class MetricCard(Flowable):
        def __init__(self, metrics, width=CONTENT_W, card_h=70):
            super().__init__()
            self.metrics = metrics; self.w = width; self.h = card_h
            n = max(1, len(metrics))
            self.card_w = (width - (n - 1) * 6) / n
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; cw = self.card_w; ch = self.h
            for i, (lbl, val, sub, col_s) in enumerate(self.metrics):
                col = HexColor(col_s) if isinstance(col_s, str) else col_s
                x = i * (cw + 6)
                c.setFillColor(CARD); c.roundRect(x, 0, cw, ch, 8, fill=1, stroke=0)
                c.setStrokeColor(STROKE); c.setLineWidth(0.6); c.roundRect(x, 0, cw, ch, 8, fill=0, stroke=1)
                c.setFillColor(col); c.roundRect(x, ch - 4, cw, 4, 2, fill=1, stroke=0)
                c.setFillAlpha(0.18); c.setFillColor(col); c.circle(x + cw - 14, ch - 16, 9, fill=1, stroke=0)
                c.setFillAlpha(1.0); c.setFillColor(col); c.circle(x + cw - 14, ch - 16, 3.5, fill=1, stroke=0)
                c.setFillColor(MUTED); c.setFont("Helvetica", 6.5)
                c.drawString(x + 10, ch - 16, str(lbl).upper()[:24])
                c.setFillColor(col); c.setFont("Helvetica-Bold", 17)
                c.drawString(x + 10, ch - 36, str(val)[:18])
                if sub:
                    c.setFillColor(MUTED); c.setFont("Helvetica", 7.5)
                    c.drawString(x + 10, ch - 50, str(sub)[:28])

    class CoverHero(Flowable):
        def __init__(self, width=CONTENT_W):
            super().__init__(); self.w = width; self.h = 260
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; w = self.w; h = self.h
            c.setFillColor(BG); c.roundRect(0, 0, w, h, 14, fill=1, stroke=0)
            c.saveState()
            p = c.beginPath(); p.roundRect(0, 0, w, h, 14); c.clipPath(p, stroke=0, fill=0)
            cx, cy = w * 0.82, h * 0.92
            rings = 26
            for i in range(rings, 0, -1):
                t = i / rings
                r = t * (w * 0.62)
                alpha = (1 - t) ** 1.6 * 0.55
                c.setFillColor(GLOW); c.setFillAlpha(alpha)
                c.circle(cx, cy, r, fill=1, stroke=0)
            c.setFillAlpha(1.0)
            c.restoreState()
            c.setStrokeColor(GOLD); c.setLineWidth(1.2)
            c.roundRect(0, 0, w, h, 14, fill=0, stroke=1)
            c.setFillColor(GOLD)
            c.roundRect(w - 145, h - 28, 137, 18, 4, fill=1, stroke=0)
            c.setFillColor(BG); c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(w - 76.5, h - 22, "CONFIDENTIAL · FOR YOUR EYES ONLY")
            tag = f"INDIVIDUAL PLAN · {name_v.upper()}" if name_v else "INDIVIDUAL PLAN"
            c.setFillColor(GLOW); c.setFont("Helvetica-Bold", 7.5)
            c.drawString(16, h - 22, tag)
            c.setFillColor(white); c.setFont("Helvetica-Bold", 28)
            c.drawCentredString(w/2, h - 76, "LONGEVITY")
            c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 28)
            c.drawCentredString(w/2, h - 107, "INTELLIGENCE REPORT")
            c.setFillColor(MUTED); c.setFont("Helvetica", 10)
            c.drawCentredString(w/2, h - 130, "Personal Precision Health Analysis · Built Entirely From Your Own Data")
            display_name = name_v if name_v else "Your Personal Report"
            c.setFillColor(white); c.setFont("Helvetica-Bold", 15)
            c.drawCentredString(w/2, h - 160, f"Prepared exclusively for {display_name}")
            c.setFillColor(MUTED); c.setFont("Helvetica", 8)
            c.drawCentredString(w/2, h - 174, f"Report ID {report_id}   ·   Generated {gen_v}")
            c.setStrokeColor(STROKE); c.setLineWidth(0.6)
            c.line(40, h - 190, w - 40, h - 190)
            cells = [("AGE", f"{age_v}"), ("SEX", f"{sex_v}"), ("HEIGHT", f"{h_v} cm"), ("WEIGHT", f"{w_v} kg")]
            cw_ = w / len(cells)
            for i, (lbl, val) in enumerate(cells):
                cx2 = i * cw_ + cw_/2
                c.setFillColor(MUTED); c.setFont("Helvetica", 6.5)
                c.drawCentredString(cx2, h - 210, lbl)
                c.setFillColor(white); c.setFont("Helvetica-Bold", 12)
                c.drawCentredString(cx2, h - 225, val)
            c.setFillColor(MUTED); c.setFont("Helvetica-Oblique", 7.5)
            c.drawCentredString(w/2, 14, "Every page that follows is calculated from the numbers above — nothing here is generic.")

    class HealthScoreRing(Flowable):
        def __init__(self, score, label, color, width=CONTENT_W):
            super().__init__()
            self.score = score; self.label = label; self.color = color
            self.w = width; self.h = 134
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; cx = self.w / 2; cy = self.h / 2 + 16; R = 46
            c.setStrokeColor(STROKE); c.setLineWidth(13); c.circle(cx, cy, R, fill=0, stroke=1)
            frac = self.score / 100.0; steps = max(2, int(frac * 72))
            for i in range(steps):
                a1 = math.pi/2 - (i/72)*2*math.pi
                a2 = math.pi/2 - ((i+1)/72)*2*math.pi
                c.setStrokeColor(self.color); c.setLineWidth(13)
                c.line(cx + R*math.cos(a1), cy + R*math.sin(a1), cx + R*math.cos(a2), cy + R*math.sin(a2))
            c.setFillColor(self.color); c.setFont("Helvetica-Bold", 28)
            c.drawCentredString(cx, cy + 6, str(self.score))
            c.setFillColor(MUTED); c.setFont("Helvetica", 8)
            c.drawCentredString(cx, cy - 8, "/ 100")
            c.setFillColor(TEXT); c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(cx, cy - 22, self.label)
            dims = list(radar.items()); dw = self.w / len(dims)
            for j, (dim, sc) in enumerate(dims):
                dx = j*dw + dw/2; dy = 10
                dc = GOOD if sc >= 70 else WARN if sc >= 45 else BAD
                c.setFillColor(CARD2); c.roundRect(j*dw + 2, 2, dw - 4, 24, 4, fill=1, stroke=0)
                c.setFillColor(dc); c.setFont("Helvetica-Bold", 9); c.drawCentredString(dx, dy + 8, str(sc))
                c.setFillColor(MUTED); c.setFont("Helvetica", 6); c.drawCentredString(dx, dy, dim)

    class BMIScale(Flowable):
        def __init__(self, bmi_val, width=CONTENT_W):
            super().__init__(); self.bmi = bmi_val; self.w = width; self.h = 100
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; bmi = self.bmi; w = self.w
            c.setFillColor(CARD); c.roundRect(0, 0, w, self.h, 10, fill=1, stroke=0)
            col = bmi_color(bmi)
            c.setFillColor(col); c.setFont("Helvetica-Bold", 30); c.drawString(14, 62, f"{bmi:.1f}")
            c.setFillColor(MUTED); c.setFont("Helvetica", 7.5); c.drawString(14, 52, "BMI")
            cat = ("Underweight" if bmi < 18.5 else "Normal weight" if bmi < 25 else "Overweight" if bmi < 30 else "Obese")
            c.setFillColor(col); c.setFont("Helvetica-Bold", 9); c.drawString(14, 39, cat)
            SMAX = 45.0; bx = 14; by = 18; bh = 13; bw = w - 28
            segs = [(0,18.5,"#3B82F6","Underweight"),(18.5,25,"#22C55E","Normal"),(25,30,"#F59E0B","Overweight"),(30,45,"#EF4444","Obese")]
            for i, (s, e, cl, lbl) in enumerate(segs):
                sx = bx + (s/SMAX)*bw; sw = ((e-s)/SMAX)*bw
                c.setFillColor(HexColor(cl))
                if i == 0: c.roundRect(sx,by,sw,bh,3,fill=1,stroke=0); c.rect(sx+3,by,sw-3,bh,fill=1,stroke=0)
                elif i == len(segs)-1: c.roundRect(sx,by,sw,bh,3,fill=1,stroke=0); c.rect(sx,by,sw-3,bh,fill=1,stroke=0)
                else: c.rect(sx,by,sw,bh,fill=1,stroke=0)
                c.setFillColor(HexColor("#0F172A")); c.setFont("Helvetica-Bold", 5.5)
                c.drawCentredString(sx+sw/2, by+4, lbl)
            mx = bx + min(1.0, bmi/SMAX)*bw
            c.setStrokeColor(white); c.setLineWidth(1.5); c.line(mx, by-2, mx, by+bh+2)
            c.setFillColor(white); path = c.beginPath(); path.moveTo(mx, by+bh+9); path.lineTo(mx-5, by+bh+2); path.lineTo(mx+5, by+bh+2); path.close()
            c.drawPath(path, fill=1, stroke=0)
            for lbl, pos in [("0",0),("18.5",18.5),("25",25),("30",30),("45",45)]:
                c.setFillColor(MUTED); c.setFont("Helvetica", 5.5); c.drawCentredString(bx + (pos/SMAX)*bw, by-8, lbl)

    class ScoreHero(Flowable):
        def __init__(self, score, label, color, radar_dict, width=CONTENT_W):
            super().__init__()
            self.score = score; self.label = label; self.color = color
            self.radar = radar_dict; self.w = width; self.h = 170  # Økt høyde
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; w = self.w; h = self.h
            c.setFillColor(CARD); c.roundRect(0, 0, w, h, 12, fill=1, stroke=0)
            c.setStrokeColor(STROKE); c.setLineWidth(0.7); c.roundRect(0, 0, w, h, 12, fill=0, stroke=1)
            c.saveState()
            p = c.beginPath(); p.roundRect(0, 0, w, h, 12); c.clipPath(p, stroke=0, fill=0)
            cx, cy = w*0.235, h*0.54
            for i in range(18, 0, -1):
                t = i/18; r = t*64
                c.setFillColor(self.color); c.setFillAlpha((1-t)**1.7*0.35)
                c.circle(cx, cy, r, fill=1, stroke=0)
            c.setFillAlpha(1.0)
            c.restoreState()
            cx, cy, R = w*0.235, h*0.54, 38
            c.setStrokeColor(STROKE); c.setLineWidth(13); c.circle(cx, cy, R, fill=0, stroke=1)
            frac = self.score/100.0; steps = max(2, int(frac*72))
            for i in range(steps):
                a1 = math.pi/2 - (i/72)*2*math.pi
                a2 = math.pi/2 - ((i+1)/72)*2*math.pi
                c.setStrokeColor(self.color); c.setLineWidth(13); c.setLineCap(1)
                c.line(cx + R*math.cos(a1), cy + R*math.sin(a1), cx + R*math.cos(a2), cy + R*math.sin(a2))
            c.setFillColor(white); c.setFont("Helvetica-Bold", 28)
            c.drawCentredString(cx, cy + 5, str(self.score))
            c.setFillColor(MUTED); c.setFont("Helvetica", 8)
            c.drawCentredString(cx, cy - 9, "/ 100")
            c.setFillColor(self.color); c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(cx, 26, self.label.upper())
            c.setFillColor(MUTED); c.setFont("Helvetica", 6.5)
            c.drawCentredString(cx, 13, "OVERALL LONGEVITY SCORE")
            dx = w*0.45
            c.setStrokeColor(STROKE); c.setLineWidth(0.6); c.line(dx, 14, dx, h-14)
            bx = dx + 16; bw2 = w - bx - 16
            dims = list(self.radar.items()); n = len(dims)
            row_h = (h - 20) / n
            for i, (dim, sc) in enumerate(dims):
                ytop = h - 12 - i*row_h
                dc = GOOD if sc >= 70 else WARN if sc >= 45 else BAD
                by = ytop - row_h + 11
                c.setFillColor(TEXT); c.setFont("Helvetica-Bold", 8.5)
                c.drawString(bx, by + 11, dim)
                c.setFillColor(dc); c.setFont("Helvetica-Bold", 8.5)
                c.drawRightString(bx + bw2, by + 11, f"{sc}/100")
                c.setFillColor(STROKE); c.roundRect(bx, by, bw2, 5, 2.5, fill=1, stroke=0)
                c.setFillColor(dc); c.roundRect(bx, by, max(6, (sc/100.0)*bw2), 5, 2.5, fill=1, stroke=0)

    class DimensionRow(Flowable):
        def __init__(self, code, label, score, insight, width=CONTENT_W):
            super().__init__()
            self.code = code; self.label = label; self.score = score
            self.insight = insight; self.w = width; self.h = 42  # Økt høyde
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; w = self.w; h = self.h
            sc = self.score
            dc = GOOD if sc >= 70 else WARN if sc >= 45 else BAD
            c.setFillColor(CARD); c.roundRect(0, 0, w, h, 8, fill=1, stroke=0)
            c.setFillColor(dc); c.roundRect(0, 0, 4, h, 2, fill=1, stroke=0)
            bcx, bcy, br = 26, h/2, 13
            c.setFillAlpha(0.18); c.setFillColor(dc); c.circle(bcx, bcy, br, fill=1, stroke=0)
            c.setFillAlpha(1.0); c.setStrokeColor(dc); c.setLineWidth(1.2); c.circle(bcx, bcy, br, fill=0, stroke=1)
            c.setFillColor(dc); c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(bcx, bcy - 3, self.code)
            c.setFillColor(TEXT); c.setFont("Helvetica-Bold", 9)
            c.drawString(48, h - 13, self.label)
            c.setFillColor(dc); c.setFont("Helvetica-Bold", 8)
            c.drawRightString(w - 12, h - 12, f"{sc} / 100")
            c.setFillColor(MUTED); c.setFont("Helvetica", 7.5)
            c.drawString(48, 8, self.insight[:100])

    class WHRBox(Flowable):
        def __init__(self, whr_val, category, width=CONTENT_W):
            super().__init__(); self.whr = whr_val; self.cat = category; self.w = width; self.h = 56
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv
            cl = GOOD if (self.cat or "").lower().startswith(("low","good","healthy")) else WARN if "moder" in (self.cat or "").lower() else BAD
            c.setFillColor(CARD); c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)
            c.setFillColor(cl); c.roundRect(0, 0, 4, self.h, 2, fill=1, stroke=0)
            c.setFillColor(cl); c.setFont("Helvetica-Bold", 18); c.drawString(16, 28, f"{self.whr:.2f}")
            c.setFillColor(MUTED); c.setFont("Helvetica", 7); c.drawString(16, 16, "Waist-to-hip ratio")
            c.setFillColor(cl); c.setFont("Helvetica-Bold", 9); c.drawRightString(self.w - 14, 24, str(self.cat or "—"))
            c.setFillColor(MUTED); c.setFont("Helvetica", 7); c.drawRightString(self.w - 14, 12, "Cardiometabolic risk indicator")

    class HealthyWeightRangeBar(Flowable):
        def __init__(self, weight_kg, height_cm, width=CONTENT_W):
            super().__init__()
            self.weight = weight_kg; self.height_cm = height_cm; self.w = width; self.h = 88
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; w = self.w
            hm = self.height_cm / 100.0
            lo = 18.5 * hm * hm; hi = 25.0 * hm * hm
            c.setFillColor(CARD); c.roundRect(0, 0, w, self.h, 10, fill=1, stroke=0)
            c.setFillColor(MUTED); c.setFont("Helvetica", 6.5)
            c.drawString(14, self.h - 14, f"YOUR HEALTHY WEIGHT RANGE AT {self.height_cm:.0f} CM (BMI 18.5-25)")
            c.setFillColor(ACCENT); c.setFont("Helvetica-Bold", 17)
            c.drawString(14, self.h - 35, f"{lo:.1f} - {hi:.1f} kg")
            bx = 14; by = 20; bh = 14; bw2 = w - 28
            scale_lo = lo * 0.78; scale_hi = hi * 1.22; span = scale_hi - scale_lo
            def X(val): return bx + ((val - scale_lo) / span) * bw2
            c.setFillColor(HexColor("#3B82F6")); c.roundRect(bx, by, X(lo) - bx, bh, 3, fill=1, stroke=0)
            c.setFillColor(GOOD); c.rect(X(lo), by, X(hi) - X(lo), bh, fill=1, stroke=0)
            c.setFillColor(HexColor("#EF4444")); c.roundRect(X(hi), by, bx + bw2 - X(hi), bh, 3, fill=1, stroke=0)
            c.setFillColor(CARD); c.rect(X(lo) - 0.1, by, 0.1, bh, fill=1, stroke=0)
            mx = X(max(scale_lo, min(scale_hi, self.weight)))
            c.setStrokeColor(white); c.setLineWidth(1.6); c.line(mx, by - 3, mx, by + bh + 3)
            c.setFillColor(white); path = c.beginPath()
            path.moveTo(mx, by + bh + 10); path.lineTo(mx - 5, by + bh + 3); path.lineTo(mx + 5, by + bh + 3); path.close()
            c.drawPath(path, fill=1, stroke=0)
            c.setFillColor(white); c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(mx, by + bh + 13, f"You: {self.weight:.1f} kg")
            c.setFillColor(MUTED); c.setFont("Helvetica", 6)
            c.drawString(bx, by - 8, f"{scale_lo:.0f} kg")
            c.drawRightString(bx + bw2, by - 8, f"{scale_hi:.0f} kg")

    class BodyCompProfile(Flowable):
        def __init__(self, weight_kg, bf_pct, sex, width=CONTENT_W):
            super().__init__()
            self.weight = weight_kg; self.bf = bf_pct; self.sex = (sex or "M").upper()[:1]
            self.w = width; self.h = 156
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; w = self.w; h = self.h
            c.setFillColor(CARD); c.roundRect(0, 0, w, h, 12, fill=1, stroke=0)
            c.setStrokeColor(STROKE); c.setLineWidth(0.7); c.roundRect(0, 0, w, h, 12, fill=0, stroke=1)
            fat_mass = self.weight * self.bf / 100.0; lean_mass = self.weight - fat_mass
            cx, cy, R = w * 0.18, h * 0.58, 38
            c.setStrokeColor(STROKE); c.setLineWidth(14); c.circle(cx, cy, R, fill=0, stroke=1)
            frac = self.bf / 100.0; steps = max(2, int(frac * 72))
            for i in range(steps):
                a1 = math.pi/2 - (i/72)*2*math.pi
                a2 = math.pi/2 - ((i+1)/72)*2*math.pi
                c.setStrokeColor(BLUE); c.setLineWidth(14); c.setLineCap(1)
                c.line(cx + R*math.cos(a1), cy + R*math.sin(a1), cx + R*math.cos(a2), cy + R*math.sin(a2))
            c.setFillColor(white); c.setFont("Helvetica-Bold", 19)
            c.drawCentredString(cx, cy + 4, f"{self.bf:.1f}%")
            c.setFillColor(MUTED); c.setFont("Helvetica", 6.5)
            c.drawCentredString(cx, cy - 9, "BODY FAT")
            c.setFillColor(TEXT); c.setFont("Helvetica-Bold", 8.5)
            c.drawCentredString(cx, 14, "Estimated composition")
            gx = w * 0.40
            c.setFillColor(MUTED); c.setFont("Helvetica", 6.5)
            c.drawString(gx, h - 16, "ESTIMATED BODY COMPOSITION")
            c.setFillColor(BLUE); c.setFont("Helvetica-Bold", 12)
            c.drawString(gx, h - 32, f"Fat mass: {fat_mass:.1f} kg")
            c.setFillColor(GOOD); c.setFont("Helvetica-Bold", 12)
            c.drawString(gx, h - 48, f"Lean mass: {lean_mass:.1f} kg")
            bands_m = [(0,6,"#3B82F6","Essential"),(6,14,"#10B981","Athletes"),(14,18,"#22C55E","Fitness"),(18,25,"#F59E0B","Average"),(25,40,"#EF4444","Obese")]
            bands_f = [(0,14,"#3B82F6","Essential"),(14,21,"#10B981","Athletes"),(21,25,"#22C55E","Fitness"),(25,32,"#F59E0B","Average"),(32,45,"#EF4444","Obese")]
            bands = bands_m if self.sex == "M" else bands_f
            BMAX = bands[-1][1]
            gw = w - gx - 16; gy = 28; gh = 13
            c.setFillColor(MUTED); c.setFont("Helvetica", 6.5)
            c.drawString(gx, gy + gh + 22, f"WHERE YOU SIT — TYPICAL {('MEN' if self.sex=='M' else 'WOMEN')} RANGES")
            for s, e, col, lbl in bands:
                sx = gx + (s/BMAX)*gw; sw = ((e-s)/BMAX)*gw
                c.setFillColor(HexColor(col)); c.rect(sx, gy, sw, gh, fill=1, stroke=0)
                c.setFillColor(HexColor("#0F172A")); c.setFont("Helvetica-Bold", 5.5)
                c.drawCentredString(sx + sw/2, gy + 4.5, lbl)
            mx = gx + min(1.0, self.bf/BMAX) * gw
            c.setStrokeColor(white); c.setLineWidth(1.6); c.line(mx, gy - 3, mx, gy + gh + 3)
            c.setFillColor(white); c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(mx, gy + gh + 12, f"You: {self.bf:.1f}%")
            c.setFillColor(MUTED); c.setFont("Helvetica", 5.5)
            c.drawString(gx, gy - 8, "0%")
            c.drawRightString(gx + gw, gy - 8, f"{BMAX:.0f}%+")

    class VO2Visual(Flowable):
        def __init__(self, vo2_val, percentile, rating, width=CONTENT_W):
            super().__init__()
            self.vo2 = vo2_val; self.pct = float(percentile or 0); self.rat = rating
            self.w = width; self.h = 100  # Økt høyde
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; w = self.w; pct = self.pct
            col = vo2_color(pct)
            c.setFillColor(CARD); c.roundRect(0, 0, w, self.h, 10, fill=1, stroke=0)
            c.setFillColor(col); c.setFont("Helvetica-Bold", 30); c.drawString(14, 56, f"{self.vo2:.1f}")
            c.setFillColor(MUTED); c.setFont("Helvetica", 7.5); c.drawString(14, 46, "ml / kg / min")
            c.setFillColor(col); c.setFont("Helvetica-Bold", 10); c.drawString(14, 32, str(self.rat or "—"))
            c.setFillColor(MUTED); c.setFont("Helvetica", 7); c.drawString(14, 20, "Rating")
            bx = w * 0.44; bw2 = w * 0.51; bh = 13; by = 48
            c.setFillColor(MUTED); c.setFont("Helvetica", 6.5); c.drawString(bx, by + bh + 6, "POPULATION PERCENTILE")
            c.setFillColor(STROKE); c.roundRect(bx, by, bw2, bh, 4, fill=1, stroke=0)
            c.setFillColor(col); c.roundRect(bx, by, max(8, (pct / 100) * bw2), bh, 4, fill=1, stroke=0)
            c.setFillColor(col); c.setFont("Helvetica-Bold", 12); c.drawRightString(bx + bw2, by - 14, f"{pct:.0f}th percentile")
            zones = [(0, 20, "#EF4444"), (20, 40, "#F59E0B"), (40, 60, "#3B82F6"), (60, 80, "#22C55E"), (80, 100, "#10B981")]
            sz_y = 18; sz_h = 7
            for zs, ze, zc in zones:
                c.setFillColor(HexColor(zc)); c.rect(bx + (zs / 100) * bw2, sz_y, ((ze - zs) / 100) * bw2, sz_h, fill=1, stroke=0)
            c.setStrokeColor(white); c.setLineWidth(1.5); nx = bx + (pct / 100) * bw2; c.line(nx, sz_y - 2, nx, sz_y + sz_h + 2)
            zlabels = ["Low", "Below avg", "Average", "Good", "Excellent"]
            for j, (zl, (zs, ze, _)) in enumerate(zip(zlabels, zones)):
                c.setFillColor(MUTED); c.setFont("Helvetica", 5.5)
                c.drawCentredString(bx + ((zs + ze) / 200) * bw2, sz_y - 8, zl)

    class RadarChart(Flowable):
        def __init__(self, scores_dict, width=CONTENT_W):
            super().__init__(); self.scores = scores_dict; self.w = width; self.h = 190  # Økt høyde
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; cx = self.w/2; cy = self.h/2 + 12; R = 60
            labels = list(self.scores.keys()); vals = [self.scores[k]/100.0 for k in labels]; n = len(labels)
            def pt(i, r): ang = math.pi/2 + 2*math.pi*i/n; return cx + r*math.cos(ang), cy + r*math.sin(ang)
            for ring in [0.25, 0.5, 0.75, 1.0]:
                pts = [pt(i, ring*R) for i in range(n)]
                c.setStrokeColor(STROKE); c.setLineWidth(0.5); path = c.beginPath(); path.moveTo(*pts[0])
                for p in pts[1:]: path.lineTo(*p)
                path.close(); c.drawPath(path, fill=0, stroke=1)
            for i in range(n):
                ox, oy = pt(i, R); c.setStrokeColor(STROKE); c.setLineWidth(0.5); c.line(cx, cy, ox, oy)
            poly = [pt(i, vals[i]*R) for i in range(n)]; c.setFillColor(ACCENT); path = c.beginPath(); path.moveTo(*poly[0])
            for p in poly[1:]: path.lineTo(*p)
            path.close(); c.setFillAlpha(0.25); c.drawPath(path, fill=1, stroke=0); c.setFillAlpha(1.0)
            c.setStrokeColor(ACCENT); c.setLineWidth(1.5); c.drawPath(path, fill=0, stroke=1)
            for i, (lbl, val) in enumerate(zip(labels, vals)):
                px, py = pt(i, val*R); c.setFillColor(ACCENT); c.circle(px, py, 3.5, fill=1, stroke=0)
                lx, ly = pt(i, R+16); sc = int(val*100)
                dc = GOOD if sc >= 70 else WARN if sc >= 45 else BAD
                c.setFillColor(TEXT); c.setFont("Helvetica-Bold", 7.5); c.drawCentredString(lx, ly+4, lbl)
                c.setFillColor(dc); c.setFont("Helvetica-Bold", 8.5); c.drawCentredString(lx, ly-6, str(sc))

    class BioAgeBar(Flowable):
        def __init__(self, bio_val, chron_val, width=CONTENT_W):
            super().__init__(); self.bio = bio_val; self.chron = chron_val; self.w = width; self.h = 82  # Økt høyde
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; w = self.w; diff = self.bio - self.chron; col = bio_color(diff)
            c.setFillColor(CARD); c.roundRect(0, 0, w, self.h, 10, fill=1, stroke=0)
            c.setFillColor(col); c.setFont("Helvetica-Bold", 30); c.drawString(14, 38, f"{self.bio:.1f}")
            c.setFillColor(MUTED); c.setFont("Helvetica", 7); c.drawString(14, 28, "Biological age")
            c.setFillColor(col); c.setFont("Helvetica-Bold", 8.5); c.drawString(14, 14, f"{abs(diff):.1f} yrs {'younger' if diff<0 else 'older'}")
            c.setStrokeColor(STROKE); c.setLineWidth(0.5); c.line(w*0.35, 8, w*0.35, self.h-8)
            bx = w*0.38; bw2 = w*0.57; max_age = max(self.bio, self.chron)*1.3
            c.setFillColor(MUTED); c.setFont("Helvetica", 7)
            c.drawString(bx, self.h-16, f"Calendar age:   {self.chron:.0f} yrs")
            c.drawString(bx, self.h-28, f"Biological age: {self.bio:.1f} yrs")
            for j, (val, lbl2, cl) in enumerate([(self.chron, "Calendar", MUTED), (self.bio, "Biological", col)]):
                bar_y = 14 + j*16; c.setFillColor(STROKE); c.roundRect(bx, bar_y, bw2, 8, 3, fill=1, stroke=0)
                c.setFillColor(cl); c.roundRect(bx, bar_y, (val/max_age)*bw2, 8, 3, fill=1, stroke=0)

    class HeartRateZonesBox(Flowable):
        def __init__(self, age, vo2_pct, width=CONTENT_W):
            super().__init__()
            self.age = age; self.vo2_pct = vo2_pct; self.w = width
            hr_max = 220 - int(age); self.hr_max = hr_max
            self.zones = [
                (1, "Zone 1", "Active Recovery",    int(hr_max*0.50), int(hr_max*0.60), "#64748B", "Warm-up, cool-down, rest days"),
                (2, "Zone 2", "Aerobic Base",        int(hr_max*0.60), int(hr_max*0.70), "#22C55E", "Fat burning, conversational — most of your easy sessions"),
                (3, "Zone 3", "Aerobic Power",       int(hr_max*0.70), int(hr_max*0.80), "#3B82F6", "Comfortably hard — tempo runs, sustained efforts"),
                (4, "Zone 4", "Lactate Threshold",   int(hr_max*0.80), int(hr_max*0.90), "#F59E0B", "Hard — interval reps, race-pace efforts"),
                (5, "Zone 5", "VO2max / Neuromuscular", int(hr_max*0.90), hr_max,        "#EF4444", "Maximum effort — short sprints only"),
            ]
            self.h = 40 + len(self.zones) * 32 + 20  # Mer luft
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; w = self.w; h = self.h
            c.setFillColor(CARD); c.roundRect(0, 0, w, h, 10, fill=1, stroke=0)
            c.setStrokeColor(STROKE); c.setLineWidth(0.6); c.roundRect(0, 0, w, h, 10, fill=0, stroke=1)
            c.setFillColor(GOLD); c.roundRect(0, h-26, w, 26, 6, fill=1, stroke=0)
            c.rect(0, h-26, w*0.5, 26, fill=1, stroke=0)
            c.setFillColor(BG); c.setFont("Helvetica-Bold", 8.5)
            c.drawString(14, h-17, f"YOUR TRAINING HEART RATE ZONES  ·  HRmax = {self.hr_max} bpm  ·  Age {int(self.age)}")
            c.setFillColor(MUTED); c.setFont("Helvetica", 6)
            c.drawString(14,  h-38, "ZONE"); c.drawString(52, h-38, "NAME")
            c.drawString(170, h-38, "BPM RANGE"); c.drawString(250, h-38, "USE THIS FOR")
            c.setStrokeColor(STROKE); c.setLineWidth(0.4); c.line(10, h-42, w-10, h-42)
            for i, (z, name, label, lo, hi, col, use) in enumerate(self.zones):
                y = h - 56 - i*32  # Mer plass mellom radene
                c.setFillColor(HexColor(col)); c.roundRect(14, y+2, 26, 16, 4, fill=1, stroke=0)
                c.setFillColor(white); c.setFont("Helvetica-Bold", 8); c.drawCentredString(27, y+7, f"Z{z}")
                c.setFillColor(TEXT); c.setFont("Helvetica-Bold", 8.5); c.drawString(52, y+10, name)
                c.setFillColor(MUTED); c.setFont("Helvetica", 7); c.drawString(52, y+1, label)
                c.setFillColor(HexColor(col)); c.setFont("Helvetica-Bold", 10)
                c.drawString(170, y+4, f"{lo}–{hi} bpm")
                bx = 245; bw2 = w - bx - 14; bar_frac = (hi - lo) / self.hr_max
                bar_off = lo / self.hr_max
                c.setFillColor(STROKE); c.roundRect(bx, y+8, bw2, 8, 2, fill=1, stroke=0)
                c.setFillColor(HexColor(col)); c.setFillAlpha(0.35)
                c.roundRect(bx + bar_off*bw2, y+8, bar_frac*bw2, 8, 2, fill=1, stroke=0)
                c.setFillAlpha(1.0)
                c.setFillColor(MUTED); c.setFont("Helvetica", 6.5)
                c.drawString(bx, y+1, use)
                if i < len(self.zones)-1:
                    c.setStrokeColor(STROKE); c.setLineWidth(0.3); c.line(10, y-2, w-10, y-2)
            c.setFillColor(DIM); c.setFont("Helvetica-Oblique", 6)
            c.drawString(14, 6, f"HRmax estimated as 220 − age. Zones may vary ±5–10 bpm individually. Confirm with a ramp test for precision.")

    class SleepCalculatorBox(Flowable):
        def __init__(self, age, width=CONTENT_W):
            super().__init__()
            self.age = int(age); self.w = width; self.h = 108
            if age < 26: self.rec_h = 9
            elif age < 65: self.rec_h = 8
            else: self.rec_h = 7
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; w = self.w; h = self.h
            c.setFillColor(HexColor("#04080F")); c.roundRect(0, 0, w, h, 10, fill=1, stroke=0)
            c.setStrokeColor(GLOW); c.setLineWidth(0.8); c.roundRect(0, 0, w, h, 10, fill=0, stroke=1)
            c.setFillColor(GLOW); c.roundRect(0, 0, 4, h, 2, fill=1, stroke=0)
            c.setFillColor(GLOW); c.setFont("Helvetica-Bold", 8); c.drawString(14, h-16, "🌙  SLEEP OPTIMISATION CALCULATOR")
            c.setFillColor(MUTED); c.setFont("Helvetica", 7.5)
            c.drawString(14, h-28, f"For a {self.age}-year-old, the recommended sleep duration is {self.rec_h}–{self.rec_h+1} hours per night (NSF guidelines).")
            wake_times = ["05:30", "06:00", "06:30", "07:00", "07:30"]
            c.setFillColor(MUTED); c.setFont("Helvetica", 6.5); c.drawString(14, h-44, "IF YOU WAKE AT")
            c.drawString(130, h-44, f"GO TO BED BY ({self.rec_h}h sleep)")
            c.setStrokeColor(STROKE); c.setLineWidth(0.3); c.line(14, h-48, w-14, h-48)
            for i, wake in enumerate(wake_times):
                wh, wm = int(wake[:2]), int(wake[3:])
                bh2 = (wh - self.rec_h) % 24; bm2 = wm
                bed_str = f"{bh2:02d}:{bm2:02d}"
                y = h - 60 - i*10
                is_ideal = i == 2
                col2 = GLOW if is_ideal else MUTED
                c.setFillColor(col2); c.setFont("Helvetica-Bold" if is_ideal else "Helvetica", 7.5)
                c.drawString(14, y, wake + ("  ← ideal" if is_ideal else ""))
                c.drawString(130, y, bed_str + ("  ← target bedtime" if is_ideal else ""))
            c.setFillColor(DIM); c.setFont("Helvetica-Oblique", 6)
            c.drawString(14, 6, "Consistent timing (same bedtime ± 30 min every night) matters as much as duration for biological age.")

    class VO2PopComparisonBox(Flowable):
        def __init__(self, vo2_val, percentile, age, sex, width=CONTENT_W):
            super().__init__()
            self.vo2 = vo2_val; self.pct = float(percentile or 0)
            self.age = int(age); self.sex = str(sex).upper(); self.w = width; self.h = 90
            norms_m = {(20,29):44.0,(30,39):42.4,(40,49):40.0,(50,59):36.7,(60,69):33.1}
            norms_f = {(20,29):38.6,(30,39):36.3,(40,49):33.1,(50,59):29.7,(60,69):26.5}
            norms = norms_m if self.sex.startswith("M") else norms_f
            self.pop_avg = next((v for (lo,hi),v in norms.items() if lo <= self.age <= hi), 38.0)
            self.pop_good = self.pop_avg * 1.15
            self.pop_exc  = self.pop_avg * 1.30
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; w = self.w; h = self.h
            c.setFillColor(CARD2); c.roundRect(0, 0, w, h, 10, fill=1, stroke=0)
            c.setStrokeColor(STROKE); c.setLineWidth(0.5); c.roundRect(0, 0, w, h, 10, fill=0, stroke=1)
            col = vo2_color(self.pct)
            c.setFillColor(MUTED); c.setFont("Helvetica", 6.5)
            c.drawString(14, h-14, f"VO2MAX COMPARISON  ·  {self.sex} AGE {self.age}")
            cols_data = [("You", f"{self.vo2:.1f}", "ml/kg/min", col),
                         (f"Avg ({self.sex} {self.age}s)", f"{self.pop_avg:.1f}", "ml/kg/min", MUTED),
                         ("Good threshold", f"{self.pop_good:.1f}", "ml/kg/min", GOOD),
                         ("Excellent", f"{self.pop_exc:.1f}", "ml/kg/min", ACCENT)]
            cw4 = (w - 20) / 4
            for i, (lbl, val, unit, cl) in enumerate(cols_data):
                x = 10 + i*cw4
                c.setFillColor(cl); c.setFont("Helvetica-Bold", 14); c.drawString(x+4, h-38, val)
                c.setFillColor(MUTED); c.setFont("Helvetica", 6); c.drawString(x+4, h-48, unit)
                c.setFillColor(MUTED); c.setFont("Helvetica", 6.5); c.drawString(x+4, h-59, lbl)
                if i < 3: c.setStrokeColor(STROKE); c.setLineWidth(0.4); c.line(x+cw4, h-20, x+cw4, h-65)
            bx = 14; bw2 = w - 28; by = 16; bh2 = 10
            max_v = max(self.vo2, self.pop_exc) * 1.1
            ax = bx + (self.pop_avg / max_v) * bw2
            c.setStrokeColor(MUTED); c.setLineWidth(1); c.line(ax, by-4, ax, by+bh2+4)
            c.setFillColor(MUTED); c.setFont("Helvetica", 5.5); c.drawCentredString(ax, by-8, "Avg")
            gx = bx + (self.pop_good / max_v) * bw2
            c.setStrokeColor(GOOD); c.setLineWidth(0.8); c.line(gx, by-4, gx, by+bh2+4)
            c.setFillColor(STROKE); c.roundRect(bx, by, bw2, bh2, 3, fill=1, stroke=0)
            ux = bx + (self.vo2 / max_v) * bw2
            c.setFillColor(col); c.roundRect(bx, by, max(8, ux-bx), bh2, 3, fill=1, stroke=0)
            c.setFillColor(DIM); c.setFont("Helvetica-Oblique", 6)
            c.drawString(14, 4, "Reference: ACSM VO2max norms by age and sex (ml/kg/min).")

    class FactorBars(Flowable):
        def __init__(self, factors, width=CONTENT_W):
            super().__init__()
            self.factors = sorted(factors, key=lambda f: abs(float(f.get("delta", 0))), reverse=True)[:8]
            self.w = width; self.h = len(self.factors)*21 + 12
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; c.setFillColor(CARD); c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)
            bx = self.w*0.42; bw2 = self.w*0.44; row = 21
            for i, f in enumerate(self.factors):
                y = self.h - 14 - i*row; delta = float(f.get("delta", 0))
                cl = "#22C55E" if delta <= 0 else "#EF4444" if delta > 1 else "#F59E0B"
                frac = min(abs(delta)/8.0, 1.0)
                c.setFillColor(MUTED); c.setFont("Helvetica", 7.5); c.drawString(10, y-4, str(f.get("label", ""))[:30])
                c.setFillColor(STROKE); c.roundRect(bx, y-4, bw2, 9, 2, fill=1, stroke=0)
                if frac > 0: c.setFillColor(HexColor(cl)); c.roundRect(bx, y-4, frac*bw2, 9, 2, fill=1, stroke=0)
                c.setFillColor(HexColor(cl)); c.setFont("Helvetica-Bold", 7.5); c.drawRightString(self.w-6, y-4, f"{delta:+.1f} yrs")

    class CalorieBar(Flowable):
        def __init__(self, maintenance, recommended, kg_per_week, width=CONTENT_W):
            super().__init__()
            self.maint = maintenance; self.rec = recommended; self.rate = kg_per_week; self.w = width; self.h = 88
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; delta = self.rec - self.maint
            col = "#22C55E" if delta < 0 else "#3B82F6" if delta > 0 else "#94A3B8"
            lbl = "Deficit" if delta < 0 else "Surplus" if delta > 0 else "Maintenance"
            c.setFillColor(CARD); c.roundRect(0, 0, self.w, self.h, 10, fill=1, stroke=0)
            cw3 = (self.w - 16) / 3
            for j, (title, val, cl) in enumerate([("MAINTENANCE", f"{self.maint:.0f}", "#94A3B8"), ("RECOMMENDED", f"{self.rec:.0f}", col), (lbl.upper(), f"{delta:+.0f} kcal", col)]):
                x = 8 + j*cw3; c.setFillColor(HexColor(cl)); c.setFont("Helvetica-Bold", 15); c.drawString(x+4, 50, val)
                c.setFillColor(MUTED); c.setFont("Helvetica", 6.5); c.drawString(x+4, 40, "kcal/day" if j < 2 else "per day"); c.drawString(x+4, self.h-14, title)
                if j < 2: c.setStrokeColor(STROKE); c.setLineWidth(0.5); c.line(x+cw3+1, 10, x+cw3+1, self.h-6)
            bx = 8; by = 18; bw2 = self.w-16
            c.setFillColor(STROKE); c.roundRect(bx, by, bw2, 9, 3, fill=1, stroke=0)
            c.setFillColor(HexColor(col)); c.roundRect(bx, by, int(min(1.0, abs(delta) / max(1, self.maint) * 5)*bw2), 9, 3, fill=1, stroke=0)
            if self.rate is not None: c.setFillColor(HexColor(col)); c.setFont("Helvetica-Bold", 8); c.drawRightString(self.w-10, 6, f"{self.rate:+.2f} kg/week")

    class MilestoneRow(Flowable):
        def __init__(self, week, weight, focus, progress_pct, col_s, is_last, width=CONTENT_W):
            super().__init__()
            self.week=week; self.weight=weight; self.focus=focus; self.prog=progress_pct
            self.col_s=col_s; self.is_last=is_last; self.w=width; self.h=52  # Økt høyde
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; col = HexColor(self.col_s)
            if not self.is_last: c.setStrokeColor(STROKE); c.setLineWidth(1); c.line(14,0,14,8)
            c.setFillColor(col); c.circle(14,34,12,fill=1,stroke=0); c.setFillColor(white); c.setFont("Helvetica-Bold",8); c.drawCentredString(14,30,str(self.week))
            c.setFillColor(CARD); c.roundRect(32,10,self.w-36,34,6,fill=1,stroke=0); c.setFillColor(col); c.roundRect(32,40,self.w-36,4,2,fill=1,stroke=0)
            c.setFillColor(col); c.setFont("Helvetica-Bold",13); c.drawString(42,27,f"{self.weight:.1f} kg")
            c.setFillColor(MUTED); c.setFont("Helvetica",7.5); c.drawString(42,16,str(self.focus)[:38])
            bx=self.w-88; bw2=78
            c.setFillColor(STROKE); c.roundRect(bx,17,bw2,6,2,fill=1,stroke=0); c.setFillColor(col); c.roundRect(bx,17,self.prog/100*bw2,6,2,fill=1,stroke=0)
            c.setFillColor(MUTED); c.setFont("Helvetica",6); c.drawRightString(bx+bw2,11,f"{self.prog:.0f}%")

    class ExpertInsightBox(Flowable):
        def __init__(self, section, text, width=CONTENT_W):
            super().__init__(); self.w = width
            self._header = Paragraph(f'<b>🔬 EXPERT INSIGHT — {section.upper()}</b>',
                                      S(f"_ei_h_{abs(hash(text))}", size=7.5, lead=11, color=GOLD, bold=True))
            self._body = Paragraph(text, S(f"_ei_b_{abs(hash(text))}", size=8.8, lead=14, color=TEXT))
            _, hh = self._header.wrap(width - 24, 9999)
            _, bh = self._body.wrap(width - 24, 9999)
            self.h = hh + bh + 30
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv
            c.setFillColor(HexColor("#1A1404")); c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)
            c.setStrokeColor(GOLD); c.setLineWidth(1.0); c.roundRect(0, 0, self.w, self.h, 8, fill=0, stroke=1)
            c.setFillColor(GOLD); c.roundRect(0, 0, 4, self.h, 2, fill=1, stroke=0)
            self._header.drawOn(c, 14, self.h - 18)
            self._body.drawOn(c, 14, 8)

    class ActionableMilestoneBox(Flowable):
        def __init__(self, steps, width=CONTENT_W):
            super().__init__(); self.w = width
            bullet_html = "".join(f"→  {s}<br/>" for s in steps)
            self._header = Paragraph('<b>🎯 YOUR NEXT 4 WEEKS — DO THIS</b>',
                                      S(f"_am_h_{abs(hash(bullet_html))}", size=7.5, lead=11, color=ACCENT, bold=True))
            self._body = Paragraph(bullet_html, S(f"_am_b_{abs(hash(bullet_html))}", size=8.8, lead=15, color=TEXT))
            _, hh = self._header.wrap(width - 24, 9999)
            _, bh = self._body.wrap(width - 24, 9999)
            self.h = hh + bh + 30
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv
            c.setFillColor(HexColor("#00100E")); c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)
            c.setStrokeColor(ACCENT); c.setLineWidth(1.0); c.roundRect(0, 0, self.w, self.h, 8, fill=0, stroke=1)
            c.setFillColor(ACCENT); c.roundRect(0, 0, 4, self.h, 2, fill=1, stroke=0)
            self._header.drawOn(c, 14, self.h - 18)
            self._body.drawOn(c, 14, 8)

    class CompoundingEffectBox(Flowable):
        def __init__(self, width=CONTENT_W):
            super().__init__(); self.w = width
            body_html = (
                "<b>Health is compound interest.</b> A 1% weekly improvement in sleep quality, "
                "training load, or nutrition precision compounds to roughly a <b>67% gain over one "
                "year.</b> The habits you start this week aren't just this week's result — they're "
                "the foundation every future week builds on. This is the principle behind every "
                "recommendation in this report."
            )
            self._header = Paragraph('<b>📈  THE COMPOUNDING EFFECT — WHY 1% MATTERS</b>',
                                      S("_ce_h", size=7.5, lead=11, color=BLUE, bold=True))
            self._body = Paragraph(body_html, S("_ce_b", size=8.8, lead=14, color=TEXT))
            _, hh = self._header.wrap(width - 24, 9999)
            _, bh = self._body.wrap(width - 24, 9999)
            self.h = hh + bh + 30
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv
            c.setFillColor(HexColor("#020810")); c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)
            c.setStrokeColor(BLUE); c.setLineWidth(1.0); c.roundRect(0, 0, self.w, self.h, 8, fill=0, stroke=1)
            c.setFillColor(BLUE); c.roundRect(0, 0, 4, self.h, 2, fill=1, stroke=0)
            self._header.drawOn(c, 14, self.h - 18)
            self._body.drawOn(c, 14, 8)

    class ExecutiveSummaryPanel(Flowable):
        def __init__(self, stop_items, start_items, keep_items, lever, lever_why, width=CONTENT_W):
            super().__init__()
            self.stop = stop_items[:3]; self.start = start_items[:3]; self.keep = keep_items[:3]
            self.lever = lever; self.lever_why = lever_why
            self.w = width; self.h = 300
        def wrap(self, aw, ah): return self.w, self.h
        def _wrap_text(self, text, max_chars=34):
            words = text.split(); lines = []; cur = ""
            for word in words:
                if len(cur) + len(word) + 1 <= max_chars: cur += (" " if cur else "") + word
                else: lines.append(cur); cur = word
            if cur: lines.append(cur)
            return lines
        def draw(self):
            c = self.canv; w = self.w
            top_h = 64
            c.setFillColor(HexColor("#1B1306")); c.roundRect(0, self.h - top_h, w, top_h, 10, fill=1, stroke=0)
            c.setStrokeColor(GOLD); c.setLineWidth(1.0); c.roundRect(0, self.h - top_h, w, top_h, 10, fill=0, stroke=1)
            c.setFillColor(GOLD); c.roundRect(0, self.h - top_h, 4, top_h, 2, fill=1, stroke=0)
            c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 8)
            c.drawString(14, self.h - 16, "★  YOUR #1 PRIORITY RIGHT NOW")
            c.setFillColor(TEXT); c.setFont("Helvetica-Bold", 12.5)
            c.drawString(14, self.h - 32, self.lever)
            c.setFillColor(MUTED); c.setFont("Helvetica", 8)
            for i, line in enumerate(self._wrap_text(self.lever_why, 100)):
                c.drawString(14, self.h - 46 - i*10, line)
            gap = 8; ph = self.h - top_h - 18
            col_w = (w - 2*gap) / 3
            x_pos = [0, col_w + gap, 2*(col_w + gap)]
            cols = [("STOP", "#EF4444", "STOP", self.stop, "#150202"),
                    ("START", "#22C55E", "START", self.start, "#011008"),
                    ("KEEP DOING", "#3B82F6", "MAINTAIN", self.keep, "#020A18")]
            for idx, (title, color, _, items, bg) in enumerate(cols):
                x = x_pos[idx]
                c.setFillColor(HexColor(bg)); c.roundRect(x, 0, col_w, ph, 10, fill=1, stroke=0)
                c.setStrokeColor(HexColor(color)); c.setLineWidth(1); c.roundRect(x, 0, col_w, ph, 10, fill=0, stroke=1)
                c.setFillColor(HexColor(color)); c.roundRect(x, ph - 4, col_w, 4, 2, fill=1, stroke=0)
                c.setFillColor(HexColor(color)); c.setFont("Helvetica-Bold", 10.5)
                c.drawCentredString(x + col_w/2, ph - 18, title)
                c.setStrokeColor(HexColor(color)); c.setLineWidth(0.4)
                c.line(x + 10, ph - 24, x + col_w - 10, ph - 24)
                c.setFillColor(TEXT); c.setFont("Helvetica", 7.5)
                y = ph - 38
                for item in items:
                    for line in self._wrap_text(item, 32):
                        if y < 10: break
                        c.drawString(x + 9, y, ("• " + line) if line == self._wrap_text(item,32)[0] else "  " + line)
                        y -= 11
                    y -= 5

    class FinalActionCard(Flowable):
        def __init__(self, items, width=CONTENT_W):
            super().__init__(); self.items = items; self.w = width
            self.h = 30 + len(items) * 30
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv
            c.setFillColor(HexColor("#00100E")); c.roundRect(0, 0, self.w, self.h, 10, fill=1, stroke=0)
            c.setStrokeColor(ACCENT); c.setLineWidth(1.2); c.roundRect(0, 0, self.w, self.h, 10, fill=0, stroke=1)
            c.setFillColor(ACCENT); c.setFont("Helvetica-Bold", 11)
            c.drawString(16, self.h - 20, "TOMORROW: DO THESE THREE THINGS")
            for i, item in enumerate(self.items):
                y = self.h - 44 - i*30
                c.setFillColor(ACCENT); c.circle(22, y+4, 10, fill=1, stroke=0)
                c.setFillColor(BG); c.setFont("Helvetica-Bold", 11); c.drawCentredString(22, y, str(i+1))
                c.setFillColor(TEXT); c.setFont("Helvetica", 9.5); c.drawString(40, y, item[:95])

    class TrustRow(Flowable):
        def __init__(self, items, width=CONTENT_W):
            super().__init__(); self.items = items; self.w = width; self.h = 64
        def wrap(self, aw, ah): return self.w, self.h
        def draw(self):
            c = self.canv; n = len(self.items); cw = self.w / n
            for i, (icon, label) in enumerate(self.items):
                x = i*cw
                c.setFillColor(CARD); c.roundRect(x+3, 0, cw-6, self.h, 8, fill=1, stroke=0)
                c.setFillColor(ACCENT); c.setFont("Helvetica-Bold", 14); c.drawCentredString(x+cw/2, self.h-24, icon)
                c.setFillColor(TEXT); c.setFont("Helvetica", 7)
                words = label.split(); l1 = " ".join(words[:2]); l2 = " ".join(words[2:])
                c.drawCentredString(x+cw/2, self.h-40, l1)
                if l2: c.drawCentredString(x+cw/2, self.h-50, l2)

    # ── Page chrome ──────────────────────────────────────────────────
    def draw_page(canvas, doc_):
        canvas.saveState()
        canvas.setFillColor(BG); canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        canvas.setFillColor(GOLD); canvas.rect(0, PAGE_H-3, PAGE_W, 3, fill=1, stroke=0)
        canvas.setFillColor(CARD2); canvas.rect(0, PAGE_H-22, PAGE_W, 19, fill=1, stroke=0)
        canvas.setFillColor(TEXT); canvas.setFont("Helvetica-Bold", 8.5)
        header_label = f"LONGEVITY INTELLIGENCE REPORT  ·  {name_v.upper()}'S PLAN" if name_v else "LONGEVITY INTELLIGENCE REPORT  ·  CONFIDENTIAL"
        canvas.drawString(MARGIN_H, PAGE_H-15, header_label)
        canvas.setFillColor(MUTED); canvas.setFont("Helvetica", 8)
        canvas.drawRightString(PAGE_W-MARGIN_H, PAGE_H-15, f"Page {canvas.getPageNumber()}")
        canvas.setFillColor(STROKE); canvas.rect(0, 0, PAGE_W, 14, fill=1, stroke=0)
        canvas.setFillColor(DIM); canvas.setFont("Helvetica", 6.5)
        canvas.drawString(MARGIN_H, 4, f"Report {report_id}  ·  Educational use only — not a medical diagnosis")
        canvas.drawRightString(PAGE_W-MARGIN_H, 4, f"Generated {gen_v}")
        canvas.restoreState()

    # ════════════════════════════════════════════════════════════════
    # STORY
    # ════════════════════════════════════════════════════════════════
    story = []

    # ── PAGE 1 — COVER ──────────────────────────────────────────────
    story.append(VGap(6))
    story.append(CoverHero())
    story.append(VGap(14))

    summary_metrics = []
    if bmi_v is not None:
        summary_metrics.append(("BMI", f"{bmi_v:.1f}", bmi_cat, bmi_col.hexval()))
    if vo2_v is not None:
        summary_metrics.append(("VO2max", f"{vo2_v:.1f}", f"{vo2_pct:.0f}th percentile", vo2_col.hexval()))
    if bio_diff is not None:
        summary_metrics.append(("Biological age", f"{bio_v:.1f} yrs", f"{bio_diff:+.1f} vs calendar", bio_col.hexval()))
    if cur_kcal and rec_kcal:
        d_k = int(rec_kcal - cur_kcal)
        summary_metrics.append(("Daily calories", f"{int(rec_kcal)}", f"{d_k:+d} kcal/day", "#22C55E" if d_k < 0 else "#3B82F6"))

    story.append(P("AT A GLANCE", S("ag", size=9, bold=True, color=GOLD, after=4, align=TA_CENTER)))
    if summary_metrics:
        story.append(MetricCard(summary_metrics[:4], card_h=72))
    story.append(VGap(12))
    story.append(P(
        f"This report was generated exclusively from the data you provided on {gen_v}. "
        f"Every chart, score, and recommendation on the following pages is calculated against "
        f"<i>your</i> numbers — not population averages presented as advice. Treat it as a working "
        f"document: print it, annotate it, and bring it to your next check-up.",
        S("cov_intro", size=9, lead=14, color=MUTED, align=TA_CENTER, after=6)
    ))
    story.append(PageBreak())

    # ── PAGE 2 — EXECUTIVE SUMMARY ──────────────────────────────────
    story.append(SecHeader("01", "Executive Summary",
                            subtitle="Your personal cheat sheet — review this page every week"))
    story.append(VGap(12))
    story.append(ExecutiveSummaryPanel(stop_items, start_items, keep_items, biggest_lever, lever_why))
    story.append(VGap(16))
    story.append(CompoundingEffectBox())
    story.append(VGap(12))
    story.append(P(
        "How to use this report: pages 3–8 break down each marker individually with the science "
        "behind it and exactly what to do next. Page 9 turns everything into a week-by-week "
        "training plan, and the final pages give you a 12-week roadmap and a one-page action "
        "card for tomorrow morning.",
        S("howto", size=8.5, lead=13, color=MUTED, italic=True, after=4)
    ))
    story.append(PageBreak())

    # ── PAGE 3 — BIOMARKER DASHBOARD ────────────────────────────────
    story.append(SecHeader("02", "Your Biomarker Dashboard",
                            subtitle="A composite snapshot across five dimensions of healthy longevity"))
    story.append(VGap(12))
    story.append(ScoreHero(health_score, score_label, score_col, radar))
    story.append(VGap(16))

    dash_metrics = []
    if bmi_v is not None: dash_metrics.append(("Body Mass Index", f"{bmi_v:.1f}", bmi_cat, bmi_col.hexval()))
    if vo2_v is not None: dash_metrics.append(("Cardio (VO2max)", f"{vo2_v:.1f}", f"{vo2_pct:.0f}th percentile · {vo2_rat}", vo2_col.hexval()))
    if bio_diff is not None: dash_metrics.append(("Biological Age", f"{bio_v:.1f} yrs", f"{bio_diff:+.1f} yrs vs calendar", bio_col.hexval()))
    if dash_metrics:
        story.append(MetricCard(dash_metrics[:3], card_h=82))
        story.append(VGap(12))

    story.append(P(
        f"Your overall score of <b>{health_score}/100</b> ({score_label.lower()}) is a weighted "
        f"composite of body composition, cardio fitness, biological age, and activity volume. "
        f"Your weakest dimension right now is <b>{weakest_dim}</b> — this is where the next 12 "
        f"weeks of effort will pay off the most.",
        S("dash_txt", size=9.5, lead=14, after=8)
    ))

    story.append(P("Dimension-by-dimension breakdown", S("dim_h", size=9.5, bold=True, color=ACCENT, after=4)))

    dim_insights = {
        "Body Comp": (
            "BC",
            f"BMI {bmi_v:.1f} ({bmi_cat}) — a healthy range. Let cardio and strength drive the "
            f"next gains, not further weight changes."
            if bmi_v is not None else "Body composition data not available for this report."
        ),
        "Cardio": (
            "CV",
            f"VO2max {vo2_v:.1f} — {vo2_pct:.0f}th percentile ({vo2_rat}). One of the strongest "
            f"predictors of long-term health in this whole report."
            if vo2_v is not None else "Cardio fitness data not available for this report."
        ),
        "Bio Age": (
            "BA",
            (f"Biological age {bio_v:.1f} yrs — {abs(bio_diff):.1f} yrs "
             f"{'younger' if bio_diff < 0 else 'older'} than your calendar age. Your habits are "
             f"{'paying off' if bio_diff < 0 else 'worth addressing'}.")
            if bio_diff is not None else "Biological age data not available for this report."
        ),
        "Activity": (
            "AC",
            (f"{ex_total_min} min/week vs. the WHO target of 150 — closing this gap is your "
             f"single biggest lever right now.")
            if ex_total_min < 150 else
            (f"{ex_total_min} min/week — at or above the WHO target of 150. Maintenance and "
             f"consistency are now the priority.")
        ),
        "Lifestyle": (
            "LS",
            "Sleep, recovery and daily habits broadly support your results — protect this "
            "rhythm as you push the other dimensions."
        ),
    }
    for dim, sc in radar.items():
        code, insight = dim_insights.get(dim, ("--", ""))
        story.append(DimensionRow(code, dim, sc, insight))
        story.append(VGap(6))

    story.append(PageBreak())

    # ── PAGE 4 — BODY COMPOSITION ────────────────────────────────────
    story.append(SecHeader("03", "Body Composition",
                            subtitle="BMI, body fat, and waist-to-hip ratio — read together, not alone"))
    story.append(VGap(12))
    if bmi_v is not None:
        story.append(BMIScale(bmi_v))
        story.append(VGap(12))

    w_num = _sf(w_v); h_num = _sf(h_v)
    if w_num is not None and h_num:
        story.append(HealthyWeightRangeBar(w_num, h_num))
        story.append(VGap(12))

    bf_val = _sf(bf_d.get("value")) if isinstance(bf_d, dict) else None
    whr_val = _sf(whr_d.get("value")) if isinstance(whr_d, dict) else None
    whr_cat = whr_d.get("category") if isinstance(whr_d, dict) else None
    if whr_val is not None:
        story.append(WHRBox(whr_val, whr_cat or "—"))
        story.append(VGap(12))

    if bf_val is not None and w_num is not None:
        story.append(BodyCompProfile(w_num, bf_val, sex_v))
        story.append(VGap(12))
   

    bmi_txt, bmi_steps = insight_and_steps_body()
    if bmi_txt:
        story.append(P(bmi_txt, S("bmi_t", size=9.5, lead=14, after=8)))

    if bf_val is not None and w_num is not None and h_num:
        fat_mass = w_num * bf_val / 100.0; lean_mass = w_num - fat_mass
        bf_band_m = [(6,"essential"),(14,"athletic"),(18,"fitness"),(25,"average"),(999,"obese")]
        bf_band_f = [(14,"essential"),(21,"athletic"),(25,"fitness"),(32,"average"),(999,"obese")]
        bands_lbl = bf_band_m if (sex_v or "M").upper().startswith("M") else bf_band_f
        bf_cat_lbl = next(lbl for thresh, lbl in bands_lbl if bf_val < thresh)
        whr_phrase = (f"a waist-to-hip ratio of {whr_val:.2f} ({(whr_cat or '').lower()})"
                       if whr_val is not None else "a waist-to-hip ratio that wasn't provided")
        verdict = (f"<b>Put together:</b> a BMI of {bmi_v:.1f} ({bmi_cat.lower()}), an estimated body fat "
                   f"of {bf_val:.1f}% (the '{bf_cat_lbl}' range for your sex), and {whr_phrase} all tell a "
                   f"consistent story — your roughly {lean_mass:.0f} kg of lean mass is doing the heavy "
                   f"lifting for your metabolism, while {fat_mass:.1f} kg is fat mass. ")
        if bf_cat_lbl in ("athletic", "fitness", "essential"):
            verdict += ("There's very little 'extra' to lose here — further restriction would risk losing "
                        "muscle along with fat. The highest-leverage move from here is building or "
                        "preserving lean mass through strength training, not chasing a lower scale number.")
        elif bf_cat_lbl == "average":
            verdict += ("A modest, gradual reduction in fat mass — alongside the strength work in your "
                        "training plan — would move you into the 'fitness' range without sacrificing "
                        "lean mass, as long as protein stays high throughout.")
        else:
            verdict += ("Prioritising a sustainable calorie deficit with high protein intake (see your "
                        "nutrition page) while keeping resistance training in your weekly plan will "
                        "protect lean mass as fat mass comes down.")
        story.append(P(verdict, S("bc_verdict", size=9.5, lead=14, after=8)))

    story.append(ExpertInsightBox("Body Composition",
        "BMI is a population screening tool — it doesn't account for muscle mass, bone density, "
        "or fat distribution. Reading it alongside waist-to-hip ratio and body fat % (above) "
        "gives a far more accurate picture of your actual metabolic health than any single "
        "number. (Reference: WHO BMI classification; Lancet 2014 obesity series.)"))
    if bmi_steps:
        story.append(VGap(8))
        story.append(ActionableMilestoneBox(bmi_steps))
    story.append(PageBreak())

    # ── PAGE 5 — CARDIO FITNESS ──────────────────────────────────────
    if vo2_v is not None:
        story.append(SecHeader("04", "Cardio Fitness — VO2max",
                                subtitle="The single strongest predictor of long-term health and longevity"))
        story.append(VGap(12))
        story.append(VO2Visual(vo2_v, vo2_pct, vo2_rat))
        story.append(VGap(12))
        if age_f is not None:
            story.append(VO2PopComparisonBox(vo2_v, vo2_pct, age_f, sex_v))
            story.append(VGap(12))
        vo2_txt, vo2_steps = insight_and_steps_vo2()
        story.append(P(vo2_txt, S("vo2_t", size=9.5, lead=14, after=8)))
        if age_f is not None:
            story.append(HeartRateZonesBox(age_f, vo2_pct))
            story.append(VGap(12))
        story.append(ExpertInsightBox("Cardio Fitness — VO2max",
            "Mandsager et al., JAMA Network Open 2018 (doi:10.1001/jamanetworkopen.2018.3605) found "
            "that cardiorespiratory fitness in the top quartile was associated with roughly 45% lower "
            "all-cause mortality vs. the lowest quartile — a larger effect than smoking cessation, "
            "diabetes, or heart disease history. VO2max is trainable at any age."))
        story.append(VGap(8))
        story.append(ActionableMilestoneBox(vo2_steps))
        story.append(PageBreak())

    # ── PAGE 6 — BIOLOGICAL AGE + RADAR ─────────────────────────────
    story.append(SecHeader("05", "Biological Age & Whole-Body Radar",
                            subtitle="A heuristic estimate — directional, not a clinical measurement"))
    story.append(VGap(12))
    if bio_v is not None and age_f is not None:
        story.append(BioAgeBar(bio_v, age_f))
        story.append(VGap(12))
        bio_txt, bio_steps = insight_and_steps_bioage()
        story.append(P(bio_txt, S("bio_t", size=9.5, lead=14, after=8)))
        if factors:
            story.append(P("What's driving your biological age estimate", S("fbh", size=9.5, bold=True, color=ACCENT, after=4)))
            story.append(FactorBars(factors))
            story.append(VGap(6))
            story.append(P("Green bars are working in your favour. Amber/red bars add years — start with the longest one.",
                            S("fbl", size=7.5, color=MUTED, italic=True, after=8)))
    if age_f is not None:
        story.append(SleepCalculatorBox(age_f))
        story.append(VGap(12))
    story.append(P("Your 5-Dimension Health Radar", S("rrh", size=9.5, bold=True, color=ACCENT, after=4)))
    story.append(RadarChart(radar))
    story.append(VGap(8))
    story.append(P("70+ = strong. 45–70 = room to improve. Below 45 = priority area for the next 12 weeks.",
                    S("rl", size=7.5, color=MUTED, italic=True, after=4)))
    if bio_v is not None and age_f is not None:
        story.append(VGap(8))
        story.append(ExpertInsightBox("Biological Age",
            "Biological-age models developed by researchers such as Steve Horvath (doi:10.1186/"
            "gb-2013-14-10-r115) and Morgan Levine use measurable biomarkers and lifestyle factors "
            "to estimate how your body ages relative to the calendar. Unlike your date of birth, "
            "this number moves — in either direction — based on the choices in this report."))
        story.append(VGap(8))
        story.append(ActionableMilestoneBox(bio_steps))
    story.append(PageBreak())

    # ── PAGE 7 — NUTRITION & MACROS ─────────────────────────────────
    story.append(SecHeader("06", "Nutrition & Calorie Strategy",
                            subtitle="Energy balance is the foundation everything else is built on"))
    story.append(VGap(12))
    if cur_kcal and rec_kcal:
        story.append(CalorieBar(cur_kcal, rec_kcal, kg_pw))
        story.append(VGap(12))
        nut_txt, nut_steps = insight_and_steps_nutrition()
        story.append(P(nut_txt, S("nut_t", size=9.5, lead=14, after=8)))

        try: wt = float(w_v or 70)
        except Exception: wt = 70.0
        protein_g = int(wt * 1.8)
        fat_g = int(int(rec_kcal) * 0.28 / 9)
        carb_g = max(0, int((int(rec_kcal) - protein_g*4 - fat_g*9) / 4))

        story.append(P("Your Daily Macro Targets", S("mach", size=10.5, bold=True, color=GOLD, after=4)))
        macro_data = [
            [P("MACRO", S("mh",size=7,color=MUTED,bold=True)), P("GRAMS", S("mh",size=7,color=MUTED,bold=True,align=TA_CENTER)),
             P("KCAL", S("mh",size=7,color=MUTED,bold=True,align=TA_CENTER)), P("RATIO", S("mh",size=7,color=MUTED,bold=True,align=TA_CENTER)),
             P("WHY IT MATTERS FOR YOU", S("mh",size=7,color=MUTED,bold=True))],
            [P("Protein", S("pr",size=9,bold=True,color=BLUE)), P(f"{protein_g} g", S("pv",size=9,align=TA_CENTER)),
             P(f"{protein_g*4}", S("pv",size=9,align=TA_CENTER)), P("~30%", S("pv",size=9,align=TA_CENTER)),
             P("Preserves muscle while you change body composition; keeps you full longer", S("pw",size=8,color=MUTED))],
            [P("Fat", S("fr",size=9,bold=True,color=WARN)), P(f"{fat_g} g", S("fv",size=9,align=TA_CENTER)),
             P(f"{fat_g*9}", S("fv",size=9,align=TA_CENTER)), P("~28%", S("fv",size=9,align=TA_CENTER)),
             P("Hormone production, brain function, fat-soluble vitamin absorption", S("fw",size=8,color=MUTED))],
            [P("Carbohydrates", S("cr",size=9,bold=True,color=GOOD)), P(f"{carb_g} g", S("cv",size=9,align=TA_CENTER)),
             P(f"{carb_g*4}", S("cv",size=9,align=TA_CENTER)), P("~42%", S("cv",size=9,align=TA_CENTER)),
             P("Fuels your training sessions and supports recovery and focus", S("cw",size=8,color=MUTED))],
        ]
        mac_t = Table(macro_data, colWidths=[35*mm,22*mm,20*mm,18*mm,None])
        mac_t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), CARD2), ("BACKGROUND", (0,1), (-1,-1), CARD),
            ("BOX", (0,0), (-1,-1), 1, STROKE), ("INNERGRID", (0,0), (-1,-1), 0.5, STROKE),
            ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING", (0,0), (-1,-1), 8), ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        story.append(mac_t); story.append(VGap(8))
        story.append(P("Macros are estimated from Mifflin-St Jeor + standard ratios for your goal. "
                        "Re-check every 2–3 weeks against real-world progress, not the formula.",
                        S("dn", size=7.5, color=MUTED, italic=True, after=6)))
        meal_count = 4
        protein_per_meal = protein_g // meal_count
        chicken_g = int(protein_per_meal / 0.31)
        eggs_count = round(protein_per_meal / 6.3)
        story.append(P(
            f"🍗 <b>Protein per meal:</b> {protein_g} g/day ÷ {meal_count} meals = "
            f"<b>{protein_per_meal} g per meal</b> — e.g. {chicken_g} g chicken breast "
            f"or {eggs_count} eggs per sitting.",
            S("ppm", size=8.5, lead=13, color=TEXT, after=6)
        ))
        hydration_l = round(wt * 0.033, 1)
        story.append(P(f"💧 Hydration target: roughly <b>{hydration_l} litres/day</b>, more on training days "
                        f"or in hot weather.", S("hyd", size=8.5, color=MUTED, after=6)))
        if exlog:
            story.append(VGap(6))
            story.append(P("Your Logged Activity", S("exh", size=9.5, bold=True, color=ACCENT, after=4)))
            ex_metrics = [("Weekly minutes", f"{ex_total_min} min", "vs WHO 150 min/week", "#22C55E" if ex_total_min >= 150 else "#F59E0B"),
                          ("Sessions / week", f"{exlog.get('sessions_per_week','—')}", str(exlog.get("activity","")), "#3B82F6"),
                          ("Calories / week", f"{ex_kcal_w:.0f}", "from training alone", "#94A3B8")]
            story.append(MetricCard(ex_metrics, card_h=60))
            story.append(VGap(8))
        story.append(ExpertInsightBox("Nutrition", nut_txt[:0] + (
            "Calorie needs were estimated using the Mifflin-St Jeor equation (doi:10.1093/ajcn/"
            "51.2.241), adjusted for your logged activity (TDEE). This is one of the most validated "
            "resting-metabolism formulas in clinical use, typically accurate within 10% for most "
            "adults. Protein target of 1.8 g/kg/day is supported by Morton et al., BJSM 2018 "
            "(doi:10.1136/bjsports-2017-097608)."
        )))
        story.append(VGap(8))
        story.append(ActionableMilestoneBox(nut_steps))
    else:
        story.append(P("A personalised calorie plan wasn't generated for this report — "
                        "complete the nutrition step in the app to unlock this section.",
                        S("ncp", size=9, color=MUTED, after=8)))
    story.append(PageBreak())

    # ── PAGE 8 — 30-DAY PERSONALISED TRAINING PLAN ───────────────────
    story.append(SecHeader("07", "Your Personalised 30-Day Training Plan",
                            subtitle=f"Goal: {_goal} · Built only from the activities you selected"))
    story.append(VGap(12))

    if selected_acts:
        acts_str = ", ".join(selected_acts)
    else:
        acts_str = "strength training, running and easy walking (a balanced default mix)"
    intro_name = f"{name_v}, " if name_v else ""
    story.append(P(
        f"{intro_name}this plan is built specifically around <b>{acts_str}</b> — nothing generic. "
        f"It runs across four progressive blocks over the next 30 days: Foundation, Build, Push, and "
        f"Taper &amp; Reassess. Every session below names the exact activity you chose and tells you "
        f"precisely what to do, for how long, and at what effort.",
        S("plan30_intro", size=9.5, lead=14, after=8)
    ))

    if selected_acts:
        story.append(P("Your Training DNA — what this plan is built from", S("dna_h", size=9.5, bold=True, color=ACCENT, after=4)))
        dna_data = [[P("ACTIVITY", S("dnah1", size=7, bold=True, color=MUTED)),
                      P("ROLE IN YOUR PLAN", S("dnah2", size=7, bold=True, color=MUTED, align=TA_CENTER))]]
        for a in selected_acts:
            cat = ACT_CATEGORY.get(a, "low")
            col = ROLE_COLOR.get(cat if cat != "cardio" else "cardio_easy", MUTED)
            dna_data.append([P(a, S(f"dna_a_{a}", size=8.5, color=TEXT)),
                              P(CAT_EMOJI.get(cat, "Other"), S(f"dna_b_{a}", size=8.5, bold=True, color=col, align=TA_CENTER))])
        dna_t = Table(dna_data, colWidths=[CONTENT_W*0.68, None])
        dna_t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), CARD2), ("BACKGROUND", (0,1), (-1,-1), CARD),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [CARD, CARD2]),
            ("BOX", (0,0), (-1,-1), 1, STROKE), ("INNERGRID", (0,0), (-1,-1), 0.4, STROKE),
            ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 8), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(dna_t)
        story.append(VGap(10))

    plan30 = build_30_day_plan(_goal, vo2_pct)
    for wi, rows in enumerate(plan30, start=1):
        title, desc = WEEK_THEMES[wi]
        story.append(P(f"<b>{title}</b>  ·  Days {((wi-1)*7)+1}–{wi*7}",
                        S(f"wt30_{wi}", size=10.5, bold=True, color=GOLD, after=2)))
        story.append(P(desc, S(f"wd30_{wi}", size=8, color=MUTED, italic=True, after=4)))
        story.append(make_week_table(rows))
        story.append(VGap(12))
        if wi == 2:
            story.append(PageBreak())
            story.append(SecHeader("07", "Your Personalised 30-Day Training Plan",
                                    subtitle="Weeks 3-4 · Push, Taper & Reassess"))
            story.append(VGap(12))

    story.append(P("Days 29-30 — Reassessment", S("d2930h", size=10.5, bold=True, color=ACCENT, after=2)))
    story.append(P(
        "Day 29: repeat the same cardio test or timed effort you used to estimate your VO2max at "
        "the start, under the same conditions. Day 30: re-take your measurements (weight, waist) "
        "and notice how your selected activities feel compared to Day 1 — then re-run this "
        "assessment to see your updated numbers.",
        S("d2930b", size=8.5, lead=13, color=MUTED, after=6)
    ))
    story.append(VGap(6))
    story.append(P(
        "Why this works: every session is tagged by colour — blue for strength, teal for easy "
        "cardio, red for intervals, gold for your sport, and grey for active recovery or rest. "
        "Roughly 80% of the month stays easy-to-moderate, with one clearly harder session each "
        "week to drive adaptation — the same principle elite endurance and strength athletes use "
        "year-round.",
        S("p30_evi", size=8.5, lead=13, after=6)
    ))
    story.append(P("If you stop seeing progress for 2–3 weeks: reduce volume by ~20% for one week "
                    "(a deload), check sleep and protein intake first, then resume normal volume.",
                    S("deload", size=8.5, lead=13, color=MUTED, italic=True, after=4)))
    story.append(PageBreak())

    # ── PAGE — 12-WEEK ROADMAP ────────────────────────────────────────
    story.append(SecHeader("08", "Your 12-Week Roadmap",
                            subtitle="Realistic, week-by-week milestones toward your target"))
    story.append(VGap(12))
    if has_plan and milestones:
        try:
            start_w = float(w_v); end_w = float(plan_d.get("target_weight_kg", w_v))
        except Exception:
            start_w = end_w = None
        if start_w is not None:
            story.append(P(f"Starting weight: <b>{start_w:.1f} kg</b>  →  Target: <b>{end_w:.1f} kg</b>",
                            S("mrt", size=10, bold=True, after=8)))
        full_milestones = list(milestones)
        if len(full_milestones) < 12 and start_w is not None and end_w is not None:
            last = full_milestones[-1] if full_milestones else {}
            try: last_w = float(last.get("Projected weight (kg)", last.get("Weight", last.get("weight", end_w))))
            except Exception: last_w = end_w
            weekly_delta = (end_w - last_w) / max(1, 12 - len(full_milestones))
            phase_labels = ["Consolidate", "Build strength", "Refine nutrition", "Push cardio",
                            "Maintain deficit", "Build habits", "Reassess & adjust",
                            "Progressive overload", "Fine-tune macros", "Peak week",
                            "Taper & test", "Final reassessment"]
            for extra_i in range(12 - len(full_milestones)):
                wk = len(full_milestones) + extra_i + 1
                proj_w = last_w + weekly_delta * (extra_i + 1)
                focus = phase_labels[min(extra_i, len(phase_labels) - 1)]
                full_milestones.append({"Week": wk, "Projected weight (kg)": round(proj_w, 1), "Focus": focus})
        m_cols = ["#3B82F6", "#0EA5A3", "#22C55E", "#F59E0B"]
        for i, m in enumerate(full_milestones):
            try: pw = float(m.get("Projected weight (kg)", m.get("Weight", m.get("weight", start_w or 0))))
            except Exception: pw = start_w or 0
            prog = (i + 1) / len(full_milestones) * 100
            story.append(MilestoneRow(m.get("Week", i + 1), pw, str(m.get("Focus", m.get("focus",""))),
                                       prog, m_cols[i % len(m_cols)], (i == len(full_milestones) - 1)))
        story.append(VGap(12))
        story.append(P("If you fall off track for a week — that's normal. Resume at your last "
                        "completed milestone rather than trying to 'catch up'. Consistency over a "
                        "12-week horizon beats any single perfect week.",
                        S("fallback", size=8.5, lead=13, color=MUTED, italic=True, after=4)))
    else:
        story.append(P("No weight roadmap was generated — set a target weight in the app to unlock "
                        "a personalised week-by-week milestone plan here.",
                        S("nm", size=9, color=MUTED, after=8)))
    story.append(PageBreak())

    # ── PAGE — CONDITION-AWARE + SAFETY ──────────────────────────────
    story.append(SecHeader("09", "Condition-Aware Recommendations & Safety",
                            subtitle="Tailored to the health context you provided", accent=WARN))
    story.append(VGap(12))
    if triage_r:
        for r in triage_r:
            story.append(ExpertInsightBox("For You", str(r)))
            story.append(VGap(8))
    else:
        story.append(P("No specific health conditions were flagged for this report. The general "
                        "guidance below still applies to everyone.",
                        S("notriage", size=9, color=MUTED, after=8)))
    story.append(VGap(8))
    story.append(P(
        "<b>When to involve your doctor:</b> before starting a new training programme if you have "
        "a diagnosed cardiovascular, metabolic, or musculoskeletal condition; if you experience "
        "chest pain, unusual shortness of breath, dizziness, or joint pain that doesn't resolve "
        "within 48 hours; or before making significant changes to medication-relevant routines "
        "(e.g. fasting, large calorie deficits with diabetes medication).",
        S("doc", size=8.5, lead=13, after=8)
    ))
    story.append(P(
        "This report is generated using validated, published formulas — Mifflin-St Jeor (energy "
        "expenditure), WHO BMI classification, Uth VO2max estimation, and ACSM/WHO training volume "
        "guidelines — but it is <b>not a medical diagnosis</b> and does not replace a consultation "
        "with a qualified healthcare professional.",
        S("disc2", size=8, lead=12, color=MUTED, italic=True, after=4)
    ))
    story.append(PageBreak())

    # ── FINAL PAGE — ACTION + TRUST ──────────────────────────────────
    story.append(SecHeader("10", "Your Next Move",
                            subtitle="Three things to do tomorrow — no more, no less"))
    story.append(VGap(12))

    tomorrow_actions = []
    if vo2_v is not None and vo2_pct < 60:
        tomorrow_actions.append("Schedule this week's interval session — pick the day and time now")
    if cur_kcal and rec_kcal:
        tomorrow_actions.append(f"Plan tomorrow's meals to land near {int(rec_kcal)} kcal, protein first")
    if bio_diff is not None and bio_diff > 0:
        tomorrow_actions.append("Set a fixed bedtime for the next 7 nights — same time, every night")
    if not tomorrow_actions:
        tomorrow_actions.append("Re-read your Executive Summary and pick one START item to begin today")
    tomorrow_actions.append("Take a photo of this report's KPI page — it's your before-state")
    if len(tomorrow_actions) < 3:
        tomorrow_actions.append("Block your full training week into your calendar right now")
    story.append(FinalActionCard(tomorrow_actions[:3]))
    story.append(VGap(12))

    story.append(P("Why This Report", S("why", size=11, bold=True, color=GOLD, after=4)))
    story.append(TrustRow([
        ("100%", "Built from your data"),
        ("12wk", "Roadmap included"),
        ("🔒", "Private & encrypted"),
        ("📄", "Print-ready"),
    ]))
    story.append(VGap(10))
    story.append(P(
        "Your data is stored only in your private account, encrypted in transit, and never sold "
        "or shared with third parties. You can delete your data at any time from account settings. "
        "This report contains no recurring charges — it is a single, one-time purchase.",
        S("priv", size=8.5, lead=13, color=MUTED, after=6)
    ))
    story.append(HRule())
    story.append(VGap(10))
    story.append(P(
        "Reassess in 8–12 weeks. The numbers on page 1 are your baseline — the real value of this "
        "report is the comparison you'll be able to make next time. Good luck.",
        S("close", size=9.5, lead=14, italic=True, after=4)
    ))
    story.append(VGap(12))
    story.append(P("Health Tools  ·  health-tools.streamlit.app  ·  support available in-app",
                    S("contact", size=8, color=DIM, align=TA_CENTER, after=2)))

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    buffer.seek(0)
    return buffer.getvalue()
