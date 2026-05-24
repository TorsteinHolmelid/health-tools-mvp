from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO

import streamlit as st
import streamlit.components.v1 as components
import calculators
import matplotlib.pyplot as plt

# --- Stripe return / simple MVP unlock ---
paid = None
try:
    paid = st.query_params.get("paid")
except Exception:
    try:
        paid = st.experimental_get_query_params().get("paid")
    except Exception:
        paid = None

if isinstance(paid, list):
    paid = paid[0] if paid else None

if paid == "true":
    st.session_state["report_unlocked"] = True

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, HRFlowable, Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from calculators import (
    bmr_mifflin,
    tdee_including_weekly_exercise,
)

# ── Resting HR sync ──────────────────────────────────────────────────────────
_HR_KEYS = [
    "resting_hr", "global_resting_hr", "basic_resting_hr",
    "ui_resting_hr", "vo2_rhr_value", "bio_rhr_val",
]

def _sync_hr(source_key: str):
    val = st.session_state.get(source_key)
    if val is None:
        return
    try:
        v = int(val)
    except Exception:
        return
    for k in _HR_KEYS:
        if k != source_key:
            st.session_state[k] = v

def sync_from_basic():
    _sync_hr("basic_resting_hr")

def sync_from_calc():
    _sync_hr("ui_resting_hr")

def sync_from_vo2():
    _sync_hr("vo2_rhr_value")

def sync_from_bio():
    _sync_hr("bio_rhr_val")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Health Tools MVP",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
:root{
  --bg0:#070D18;
  --bg1:#0B1220;
  --card: rgba(15,23,42,.72);
  --card2: rgba(17,28,51,.62);
  --stroke: rgba(148,163,184,.16);
  --stroke2: rgba(148,163,184,.10);
  --text:#E5E7EB;
  --muted:#94A3B8;
  --muted2:#A7B4C6;
  --accent:#0EA5A3;
  --accent2:#3B82F6;
  --good:#22C55E;
  --warn:#F59E0B;
  --bad:#EF4444;
  --radius:16px;
}

img, svg, iframe { max-width: 100% !important; height: auto !important; }

.stApp{
  background:
    radial-gradient(1200px 600px at 18% -10%, rgba(14,165,163,.20), transparent 60%),
    radial-gradient(900px 520px at 90% 0%, rgba(59,130,246,.15), transparent 55%),
    linear-gradient(180deg, var(--bg0), var(--bg1) 40%, #070B14);
  color: var(--text);
}

.block-container{
  max-width: 980px;
  padding-top: 1.35rem;
  padding-bottom: 2.2rem;
}

h1, h2, h3, p, label, li { color: var(--text) !important; }
small, .stCaption, [data-testid="stCaptionContainer"] { color: var(--muted) !important; }

.ht-hero{
  background: linear-gradient(135deg, rgba(14,165,163,.18), rgba(59,130,246,.12));
  border: 1px solid var(--stroke);
  border-radius: calc(var(--radius) + 6px);
  padding: 18px 18px;
  box-shadow: 0 18px 50px rgba(0,0,0,.25);
  backdrop-filter: blur(8px);
  margin-bottom: 14px;
}
.ht-hero h1{ margin:0; font-size: 38px; letter-spacing:-0.02em; }
.ht-hero .sub{ margin-top:6px; color: var(--muted2); font-size: 13px; line-height:1.4; }
.ht-pills{ display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
.ht-pill{
  display:inline-flex; align-items:center; gap:6px;
  background: rgba(17,24,39,.65);
  border: 1px solid var(--stroke2);
  padding: 6px 10px;
  border-radius: 999px;
  color: var(--muted2);
  font-size: 12px;
}

.ht-card{
  background: var(--card);
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  padding: 14px 14px;
  box-shadow: 0 12px 36px rgba(0,0,0,.22);
  backdrop-filter: blur(8px);
  margin-bottom: 12px;
}

.ht-h2{
  font-size: 22px;
  font-weight: 750;
  letter-spacing: -0.01em;
  margin: 2px 0 6px 0;
}
.ht-sub{ color: var(--muted); font-size: 13px; margin: 0 0 10px 0; }

[data-testid="stMetric"]{
  background: rgba(15,23,42,.55);
  border: 1px solid var(--stroke);
  border-radius: 14px;
  padding: 10px 12px;
}

.stTextInput input, .stNumberInput input, textarea, select,
.stSelectbox [data-baseweb="select"]{
  background-color: rgba(255,255,255,0.04) !important;
  color: var(--text) !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
  border-radius: 12px !important;
}

[data-testid="stExpander"] details{
  background: rgba(15,23,42,.45) !important;
  border: 1px solid var(--stroke) !important;
  border-radius: var(--radius) !important;
  overflow: hidden !important;
}
[data-testid="stExpander"] summary{
  padding: 10px 14px !important;
  font-weight: 700 !important;
  letter-spacing: -0.01em;
}
[data-testid="stExpander"] summary:hover{
  background: rgba(148,163,184,.06) !important;
}

[data-testid="stCheckbox"] input{ transform: scale(1.10); }
[data-testid="stToggle"] input{ transform: scale(1.05); }

.stButton > button[data-testid="baseButton-primary"]{
  background: linear-gradient(135deg, #0EA5A3, #22C55E) !important;
  color: #052e2b !important;
  border: 0 !important;
  border-radius: 14px !important;
  padding: 10px 14px !important;
  font-weight: 750 !important;
  box-shadow: 0 14px 34px rgba(14,165,163,.18);
}
.stButton > button[data-testid="baseButton-primary"]:hover{
  filter: brightness(0.97); transform: translateY(-1px);
}
.stButton > button[data-testid="baseButton-secondary"]{
  background: rgba(255,255,255,0.03) !important;
  border: 1.5px solid rgba(255,255,255,0.10) !important;
  border-radius: 12px !important;
  color: #E5E7EB !important;
  font-weight: 600 !important;
  white-space: pre-wrap !important;
  min-height: 82px !important;
  font-size: 11px !important;
  line-height: 1.45 !important;
}
.stButton > button[data-testid="baseButton-secondary"]:hover{
  border-color: rgba(14,165,163,0.5) !important;
  background: rgba(14,165,163,0.08) !important;
}

@media (max-width: 600px){
  .main > div { padding-left: 10px !important; padding-right: 10px !important; }
  .ht-hero h1{ font-size: 30px; }
  .stButton > button { width: 100% !important; }
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="ht-hero">
  <h1>Health Tools — MVP</h1>
  <div class="sub">Educational tool only — not a diagnostic tool. Data is not stored.</div>
  <div class="ht-pills">
    <span class="ht-pill">Privacy‑first</span>
    <span class="ht-pill">Mobile‑friendly</span>
    <span class="ht-pill">Explainable results</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ── Consent ───────────────────────────────────────────────────────────────────
if "consent_given" not in st.session_state:
    st.session_state.consent_given = False

if not st.session_state.consent_given:
    with st.expander("Please read: Consent & privacy", expanded=True):
        st.markdown("This demo stores nothing by default and is for educational purposes only. By continuing you confirm you understand it's not clinical advice.")
    cols = st.columns([1, 1])
    if cols[0].button("I agree", key="consent_agree", type="primary"):
        st.session_state.consent_given = True
        try:
            if not st.session_state.get("_consent_rerun_done"):
                st.session_state["_consent_rerun_done"] = True
                st.experimental_rerun()
        except Exception:
            pass
    if cols[1].button("Exit", key="consent_exit"):
        st.stop()


# ── PDF helpers ───────────────────────────────────────────────────────────────
def para(text: str, style) -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


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
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


from reportlab.lib.colors import HexColor
def create_pdf_bytes(report: dict) -> bytes:
    C_BG     = HexColor("#0F172A")
    C_CARD   = HexColor("#1E293B")
    C_CARD2  = HexColor("#162032")
    C_ACCENT = HexColor("#0EA5A3")
    C_BLUE   = HexColor("#3B82F6")
    C_GOOD   = HexColor("#22C55E")
    C_WARN   = HexColor("#F59E0B")
    C_BAD    = HexColor("#EF4444")
    C_TEXT   = HexColor("#E5E7EB")
    C_MUTED  = HexColor("#94A3B8")
    C_STROKE = HexColor("#334155")

    PAGE_W, PAGE_H = A4
    CONTENT_W = PAGE_W - 36 * mm

    buffer = BytesIO()

    styles_rl = getSampleStyleSheet()

    def ps(name, fontName="Helvetica", fontSize=10, leading=13, textColor=C_TEXT,
           alignment=0, spaceAfter=4, spaceBefore=0, bold=False):
        fn = "Helvetica-Bold" if bold else fontName
        return ParagraphStyle(
            name, parent=styles_rl["Normal"],
            fontName=fn, fontSize=fontSize, leading=leading,
            textColor=textColor, alignment=alignment,
            spaceAfter=spaceAfter, spaceBefore=spaceBefore,
        )

    P = Paragraph

    # ── Custom Flowables ──────────────────────────────────────────

    class Gap(Flowable):
        def __init__(self, h=8):
            super().__init__()
            self._h = h
        def wrap(self, aw, ah):
            return aw, self._h
        def draw(self):
            pass

    class SectionHeader(Flowable):
        def __init__(self, title, width=CONTENT_W, accent=None):
            super().__init__()
            self.title  = title
            self.w      = width
            self.accent = accent or C_ACCENT
            self.h      = 38

        def wrap(self, aw, ah):
            return self.w, self.h

        def draw(self):
            c = self.canv
            c.setFillColor(C_CARD)
            c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)
            c.setFillColor(self.accent)
            c.roundRect(0, 0, 4, self.h, 2, fill=1, stroke=0)
            c.setFillColor(C_TEXT)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(14, 13, self.title)

    class MetricRow(Flowable):
        def __init__(self, metrics, width=CONTENT_W):
            # metrics = list of (label, value, sub, color_hex_str)
            super().__init__()
            self.metrics = metrics
            self.w       = width
            self.h       = 62
            n            = len(metrics)
            self.card_w  = (width - (n - 1) * 8) / n if n > 0 else width

        def wrap(self, aw, ah):
            return self.w, self.h

        def draw(self):
            c = self.canv
            cw = self.card_w
            for i, (label, value, sub, col_str) in enumerate(self.metrics):
                col = HexColor(col_str) if isinstance(col_str, str) else col_str
                x   = i * (cw + 8)
                c.setFillColor(C_CARD)
                c.roundRect(x, 0, cw, 58, 8, fill=1, stroke=0)
                c.setFillColor(col)
                c.roundRect(x, 55, cw, 3, 1, fill=1, stroke=0)
                c.setFillColor(C_MUTED)
                c.setFont("Helvetica", 7)
                c.drawString(x + 8, 43, str(label).upper()[:22])
                c.setFillColor(col)
                c.setFont("Helvetica-Bold", 15)
                c.drawString(x + 8, 25, str(value)[:18])
                if sub:
                    c.setFillColor(C_MUTED)
                    c.setFont("Helvetica", 7)
                    c.drawString(x + 8, 10, str(sub)[:24])

    class BMIBar(Flowable):
        def __init__(self, bmi_val, width=CONTENT_W):
            super().__init__()
            self.bmi = bmi_val
            self.w   = width
            self.h   = 96

        def wrap(self, aw, ah):
            return self.w, self.h

        def draw(self):
            c   = self.canv
            bmi = self.bmi
            w   = self.w

            c.setFillColor(C_CARD)
            c.roundRect(0, 0, w, self.h, 10, fill=1, stroke=0)

            if bmi < 18.5:   bmi_col = "#3B82F6"
            elif bmi < 25.0: bmi_col = "#22C55E"
            elif bmi < 30.0: bmi_col = "#F59E0B"
            else:            bmi_col = "#EF4444"

            c.setFillColor(HexColor(bmi_col))
            c.setFont("Helvetica-Bold", 26)
            c.drawString(12, 62, f"{bmi:.1f}")
            c.setFillColor(C_MUTED)
            c.setFont("Helvetica", 8)
            c.drawString(12, 52, "BMI Score")

            scale_max = 45.0
            bar_x = 12
            bar_y = 28
            bar_h = 14
            bar_w = w - 24

            segs = [
                (0, 18.5, "#3B82F6",  "Underweight"),
                (18.5, 25.0, "#22C55E", "Normal"),
                (25.0, 30.0, "#F59E0B", "Overweight"),
                (30.0, 45.0, "#EF4444", "Obese"),
            ]

            for i, (s, e, col, lbl) in enumerate(segs):
                sx = bar_x + (s / scale_max) * bar_w
                sw = ((e - s) / scale_max) * bar_w
                c.setFillColor(HexColor(col))
                if i == 0:
                    c.roundRect(sx, bar_y, sw, bar_h, 3, fill=1, stroke=0)
                    c.rect(sx + 3, bar_y, sw - 3, bar_h, fill=1, stroke=0)
                elif i == len(segs) - 1:
                    c.roundRect(sx, bar_y, sw, bar_h, 3, fill=1, stroke=0)
                    c.rect(sx, bar_y, sw - 3, bar_h, fill=1, stroke=0)
                else:
                    c.rect(sx, bar_y, sw, bar_h, fill=1, stroke=0)
                c.setFillColor(HexColor("#0F172A"))
                c.setFont("Helvetica-Bold", 6)
                c.drawCentredString(sx + sw / 2, bar_y + 4, lbl)

            mx = bar_x + min(1.0, bmi / scale_max) * bar_w
            c.setStrokeColor(colors.white)
            c.setLineWidth(1.5)
            c.line(mx, bar_y - 2, mx, bar_y + bar_h + 2)
            c.setFillColor(colors.white)
            path = c.beginPath()
            path.moveTo(mx,     bar_y + bar_h + 9)
            path.lineTo(mx - 5, bar_y + bar_h + 2)
            path.lineTo(mx + 5, bar_y + bar_h + 2)
            path.close()
            c.drawPath(path, fill=1, stroke=0)

            for lbl, pos in [("0", 0), ("18.5", 18.5), ("25", 25), ("30", 30), ("45", 45)]:
                lx = bar_x + (pos / scale_max) * bar_w
                c.setFillColor(C_MUTED)
                c.setFont("Helvetica", 6)
                c.drawCentredString(lx, bar_y - 9, lbl)

    class VO2Visual(Flowable):
        def __init__(self, vo2_val, percentile, rating, width=CONTENT_W):
            super().__init__()
            self.vo2  = vo2_val
            self.pct  = float(percentile or 0)
            self.rating = rating
            self.w    = width
            self.h    = 86

        def wrap(self, aw, ah):
            return self.w, self.h

        def draw(self):
            c   = self.canv
            w   = self.w
            pct = self.pct

            if pct >= 80:   col = "#22C55E"
            elif pct >= 60: col = "#3B82F6"
            elif pct >= 40: col = "#F59E0B"
            else:           col = "#EF4444"

            c.setFillColor(C_CARD)
            c.roundRect(0, 0, w, self.h, 10, fill=1, stroke=0)

            c.setFillColor(HexColor(col))
            c.setFont("Helvetica-Bold", 26)
            c.drawString(12, 54, f"{self.vo2:.1f}")
            c.setFillColor(C_MUTED)
            c.setFont("Helvetica", 8)
            c.drawString(12, 44, "ml / kg / min")
            c.setFillColor(HexColor(col))
            c.setFont("Helvetica-Bold", 10)
            c.drawString(12, 28, str(self.rating or "—"))
            c.setFillColor(C_MUTED)
            c.setFont("Helvetica", 7)
            c.drawString(12, 16, "Rating")

            bx  = w * 0.44
            bw  = w * 0.52
            bh  = 12
            by  = 40
            c.setFillColor(C_STROKE)
            c.roundRect(bx, by, bw, bh, 4, fill=1, stroke=0)
            fill_w = max(8, (pct / 100.0) * bw)
            c.setFillColor(HexColor(col))
            c.roundRect(bx, by, fill_w, bh, 4, fill=1, stroke=0)
            c.setFillColor(C_MUTED)
            c.setFont("Helvetica", 7)
            c.drawString(bx, by + bh + 5, "POPULATION PERCENTILE")
            c.setFillColor(HexColor(col))
            c.setFont("Helvetica-Bold", 11)
            c.drawRightString(bx + bw, by - 11, f"{pct:.0f}th percentile")

            # 5-zone mini scale
            zones = [
                (0,  20,  "#EF4444"),
                (20, 40,  "#F59E0B"),
                (40, 60,  "#3B82F6"),
                (60, 80,  "#22C55E"),
                (80, 100, "#10B981"),
            ]
            sz_y = 16
            sz_h = 7
            for zs, ze, zc in zones:
                zx = bx + (zs / 100) * bw
                zw = ((ze - zs) / 100) * bw
                c.setFillColor(HexColor(zc))
                c.rect(zx, sz_y, zw, sz_h, fill=1, stroke=0)
            c.setStrokeColor(colors.white)
            c.setLineWidth(1.5)
            mx2 = bx + (pct / 100) * bw
            c.line(mx2, sz_y - 1, mx2, sz_y + sz_h + 1)

    class BioFactorBars(Flowable):
        def __init__(self, factors, width=CONTENT_W):
            super().__init__()
            self.factors = factors[:8]
            self.w       = width
            self.h       = len(self.factors) * 22 + 8

        def wrap(self, aw, ah):
            return self.w, self.h

        def draw(self):
            c = self.canv
            c.setFillColor(C_CARD)
            c.roundRect(0, 0, self.w, self.h, 8, fill=1, stroke=0)

            row_h = 22
            bar_x = self.w * 0.42
            bar_w = self.w * 0.45
            label_max = self.w * 0.40

            for i, f in enumerate(self.factors):
                y       = self.h - 14 - i * row_h
                delta   = float(f.get("delta", 0))
                col_str = "#22C55E" if delta <= 0 else "#EF4444" if delta > 1 else "#F59E0B"
                bar_pct = min(abs(delta) / 10.0, 1.0)

                c.setFillColor(C_MUTED)
                c.setFont("Helvetica", 7.5)
                lbl = str(f.get("label", ""))[:32]
                c.drawString(10, y - 4, lbl)

                c.setFillColor(C_STROKE)
                c.roundRect(bar_x, y - 4, bar_w, 8, 2, fill=1, stroke=0)
                if bar_pct > 0:
                    c.setFillColor(HexColor(col_str))
                    c.roundRect(bar_x, y - 4, bar_pct * bar_w, 8, 2, fill=1, stroke=0)

                c.setFillColor(HexColor(col_str))
                c.setFont("Helvetica-Bold", 7.5)
                c.drawRightString(self.w - 4, y - 4, f"{delta:+.1f} yrs")

    class MilestoneLine(Flowable):
        def __init__(self, week, weight, focus, progress_pct, col_str, is_last, width=CONTENT_W):
            super().__init__()
            self.week         = week
            self.weight       = weight
            self.focus        = focus
            self.progress_pct = progress_pct
            self.col_str      = col_str
            self.is_last      = is_last
            self.w            = width
            self.h            = 48

        def wrap(self, aw, ah):
            return self.w, self.h

        def draw(self):
            c   = self.canv
            col = HexColor(self.col_str)

            if not self.is_last:
                c.setStrokeColor(C_STROKE)
                c.setLineWidth(1)
                c.line(13, 0, 13, 10)

            c.setFillColor(col)
            c.circle(13, 36, 11, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(13, 32, str(self.week))

            c.setFillColor(C_CARD)
            c.roundRect(32, 14, self.w - 36, 34, 6, fill=1, stroke=0)
            c.setFillColor(col)
            c.roundRect(32, 44, self.w - 36, 4, 2, fill=1, stroke=0)

            c.setFillColor(col)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(42, 32, f"{self.weight:.1f} kg")
            c.setFillColor(C_MUTED)
            c.setFont("Helvetica", 7.5)
            c.drawString(42, 20, str(self.focus)[:40])

            bx = self.w - 90
            bw = 80
            c.setFillColor(C_STROKE)
            c.roundRect(bx, 20, bw, 6, 2, fill=1, stroke=0)
            c.setFillColor(col)
            c.roundRect(bx, 20, self.progress_pct / 100 * bw, 6, 2, fill=1, stroke=0)
            c.setFillColor(C_MUTED)
            c.setFont("Helvetica", 6.5)
            c.drawRightString(bx + bw, 13, f"{self.progress_pct:.0f}%")

    # ── Page template (dark bg + header/footer) ──────────────────

    def draw_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(C_BG)
        canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        canvas.setFillColor(C_ACCENT)
        canvas.rect(0, PAGE_H - 3, PAGE_W, 3, fill=1, stroke=0)
        canvas.setFillColor(C_CARD)
        canvas.rect(0, PAGE_H - 22, PAGE_W, 19, fill=1, stroke=0)
        canvas.setFillColor(C_TEXT)
        canvas.setFont("Helvetica-Bold", 8.5)
        canvas.drawString(18 * mm, PAGE_H - 15, "HEALTH TOOLS — PREMIUM REPORT")
        canvas.setFillColor(C_MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(PAGE_W - 18 * mm, PAGE_H - 15,
                               f"Page {canvas.getPageNumber()}")
        canvas.setFillColor(C_STROKE)
        canvas.rect(0, 0, PAGE_W, 14, fill=1, stroke=0)
        canvas.setFillColor(HexColor("#64748B"))
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(18 * mm, 4,
                          "Educational use only — not medical advice — health-tools.streamlit.app")
        canvas.drawRightString(PAGE_W - 18 * mm, 4,
                               datetime.utcnow().strftime("%Y-%m-%d UTC"))
        canvas.restoreState()

    # ── Build story ───────────────────────────────────────────────

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=26 * mm, bottomMargin=18 * mm,
    )

    story = []
    inp = report.get("inputs", {})

    # Cover
    story.append(Gap(6))
    story.append(P("HEALTH TOOLS",
                   ps("cvt", fontSize=30, leading=34, textColor=C_ACCENT,
                      bold=True, alignment=TA_CENTER)))
    story.append(P("Premium Health Report",
                   ps("cvs", fontSize=15, leading=19, textColor=C_TEXT,
                      alignment=TA_CENTER, spaceAfter=6)))

    # Info row
    age_v  = inp.get("age", "—")
    sex_v  = inp.get("sex", "—")
    h_v    = inp.get("height_cm", "—")
    w_v    = inp.get("weight_kg", "—")
    gen_v  = report.get("generated", "—")

    info_data = [
        [P("AGE",     ps("il", fontSize=7, textColor=C_MUTED)),
         P("SEX",     ps("il", fontSize=7, textColor=C_MUTED)),
         P("HEIGHT",  ps("il", fontSize=7, textColor=C_MUTED)),
         P("WEIGHT",  ps("il", fontSize=7, textColor=C_MUTED)),
         P("GENERATED", ps("il", fontSize=7, textColor=C_MUTED))],
        [P(f"{age_v} yrs", ps("iv", fontSize=12, bold=True, textColor=C_TEXT)),
         P(str(sex_v),     ps("iv", fontSize=12, bold=True, textColor=C_TEXT)),
         P(f"{h_v} cm",    ps("iv", fontSize=12, bold=True, textColor=C_TEXT)),
         P(f"{w_v} kg",    ps("iv", fontSize=12, bold=True, textColor=C_TEXT)),
         P(str(gen_v),     ps("iv", fontSize=8,  textColor=C_MUTED))],
    ]
    info_t = Table(info_data, colWidths=[CONTENT_W / 5] * 5)
    info_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_CARD),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_CARD, C_CARD2]),
        ("BOX",       (0, 0), (-1, -1), 1,   C_STROKE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, C_STROKE),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(info_t)
    story.append(Gap(10))

    # ── BMI ──
    if report.get("bmi"):
        bmi_v   = float(report["bmi"]["value"])
        bmi_cat = report["bmi"]["category"]
        story.append(SectionHeader("Body Mass Index"))
        story.append(Gap(5))
        story.append(BMIBar(bmi_v))
        if report.get("whr") or report.get("bodyfat"):
            story.append(Gap(4))
            extra = []
            if report.get("whr"):
                extra.append(("Waist-to-hip ratio",
                               f'{report["whr"]["value"]:.2f} — {report["whr"]["category"]}'))
            if report.get("bodyfat"):
                extra.append(("Body fat (Navy method)",
                               f'{report["bodyfat"]["value"]:.1f}%'))
            for lbl, val in extra:
                story.append(P(
                    f'<font color="#94A3B8">{lbl}:</font>  '
                    f'<font color="#E5E7EB"><b>{val}</b></font>',
                    ps("be", fontSize=9, leading=14),
                ))
        story.append(Gap(10))

    # ── VO2 ──
    if report.get("vo2"):
        v = report["vo2"]
        story.append(SectionHeader("VO2max & Cardio Fitness"))
        story.append(Gap(5))
        story.append(VO2Visual(
            float(v["value"]),
            float(v.get("percentile") or 0),
            v.get("rating", "—"),
        ))
        story.append(Gap(5))
        meta_data = [
            [P("METHOD",          ps("ml", fontSize=7, textColor=C_MUTED)),
             P("AGE BAND",        ps("ml", fontSize=7, textColor=C_MUTED)),
             P("POPULATION MEAN", ps("ml", fontSize=7, textColor=C_MUTED))],
            [P(str(v.get("method", "—")),
               ps("mv", fontSize=9, bold=True, textColor=C_TEXT)),
             P(str(v.get("age_band", "—")),
               ps("mv", fontSize=9, bold=True, textColor=C_TEXT)),
             P(f'{v.get("mean", "—")} ml/kg/min',
               ps("mv", fontSize=9, bold=True, textColor=C_TEXT))],
        ]
        meta_t = Table(meta_data, colWidths=[CONTENT_W / 3] * 3)
        meta_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_CARD2),
            ("BOX",       (0, 0), (-1, -1), 1,   C_STROKE),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, C_STROKE),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))
        story.append(meta_t)
        tips = v.get("tips", [])
        if tips:
            story.append(Gap(6))
            story.append(P("Training Recommendations",
                           ps("trh", fontSize=10, bold=True, textColor=C_ACCENT, spaceAfter=3)))
            for tip in tips[:5]:
                story.append(P(
                    f"→  {escape(str(tip))}",
                    ps(f"tip{id(tip)}", fontSize=8.5, leading=12,
                       textColor=HexColor("#CBD5E1"), spaceAfter=3),
                ))
        story.append(Gap(10))

    # ── Biological age ──
    if report.get("bio_age"):
        bio_val   = float(report["bio_age"]["value"])
        chron_age = float(inp.get("age", bio_val) or bio_val)
        diff      = bio_val - chron_age
        bio_col   = "#22C55E" if diff <= -1 else "#F59E0B" if diff <= 2 else "#EF4444"
        diff_txt  = f"{abs(diff):.1f} yrs {'younger' if diff < 0 else 'older'} than calendar"

        story.append(SectionHeader("Biological Age"))
        story.append(Gap(5))
        story.append(MetricRow([
            ("BIOLOGICAL AGE",    f"{bio_val:.1f} yrs",    diff_txt,              bio_col),
            ("CHRONOLOGICAL AGE", f"{chron_age:.0f} yrs",  "Calendar age",        "#94A3B8"),
            ("DIFFERENCE",        f"{diff:+.1f} yrs",       "Bio vs. calendar",    bio_col),
        ]))
        if report.get("bio_factors"):
            story.append(Gap(6))
            story.append(P("Factor Breakdown",
                           ps("bfh", fontSize=10, bold=True, textColor=C_ACCENT, spaceAfter=3)))
            story.append(BioFactorBars(report["bio_factors"]))
        story.append(Gap(10))

    # ── Exercise log ──
    ex = report.get("exercise_log")
    if ex:
        story.append(SectionHeader("Exercise Log"))
        story.append(Gap(5))
        kcal_pw   = float(ex.get("kcal_per_week", 0))
        total_min = int(ex.get("minutes", 0)) * int(ex.get("sessions_per_week", 0))
        story.append(MetricRow([
            ("ACTIVITY",    str(ex.get("activity", "—"))[:18],
             str(ex.get("intensity", "—")),                    "#0EA5A3"),
            ("KCAL / SESSION", f'{ex.get("kcal_per_session", 0):.0f}',
             "kcal",                                           "#3B82F6"),
            ("KCAL / WEEK", f'{kcal_pw:.0f}',
             f'{ex.get("sessions_per_week", 0)}× per week',   "#22C55E"),
            ("VOLUME",      f'{total_min} min/wk',
             f'{ex.get("minutes", 0)} min × {ex.get("sessions_per_week", 0)}', "#F59E0B"),
        ]))
        story.append(Gap(4))
        who_met = total_min >= 150
        who_col = "#22C55E" if who_met else "#F59E0B"
        who_txt = ("✓  Meets WHO 150 min/week guidelines"
                   if who_met else
                   f"⚠  {150 - total_min} min/week below WHO 150 min target")
        story.append(P(who_txt,
                       ps("who", fontSize=8.5, textColor=HexColor(who_col), spaceAfter=2)))
        story.append(Gap(10))

    # ── Conditions ──
    if report.get("triage") and report.get("triage_recommendations"):
        story.append(SectionHeader("Conditions & Recommendations"))
        story.append(Gap(5))
        for r in report["triage_recommendations"]:
            story.append(P(
                f"→  {escape(str(r))}",
                ps(f"rec{id(r)}", fontSize=8.5, leading=13,
                   textColor=HexColor("#CBD5E1"), spaceAfter=3),
            ))
        story.append(Gap(10))

    # ── Plan ──
    if report.get("plan") and not report["plan"].get("error"):
        plan = report["plan"]
        story.append(SectionHeader("Weight Goal Plan"))
        story.append(Gap(5))
        story.append(MetricRow([
            ("MAINTENANCE",  f'{plan.get("current_needs_kcal", "—")} kcal',
             "per day",                                  "#94A3B8"),
            ("RECOMMENDED",  f'{plan.get("recommended_daily_kcal", "—")} kcal',
             "per day",                                  "#0EA5A3"),
            ("WEEKLY CHANGE", f'{float(plan.get("kg_per_week", 0)):+.2f} kg',
             "per week",                                 "#3B82F6"),
        ]))
        milestones = plan.get("milestones", [])
        if milestones:
            story.append(Gap(6))
            story.append(P("Milestone Roadmap",
                           ps("mrh", fontSize=10, bold=True,
                              textColor=C_ACCENT, spaceAfter=3)))
            try:
                start_w = float(inp.get("weight_kg", 70) or 70)
            except Exception:
                start_w = 70.0
            try:
                end_w = float(milestones[-1].get("Projected weight (kg)", start_w))
            except Exception:
                end_w = start_w
            total_change = abs(end_w - start_w)
            m_cols = ["#3B82F6", "#7C3AED", "#0EA5A3", "#22C55E"]
            for i, m in enumerate(milestones):
                try:
                    pw = float(m.get("Projected weight (kg)", start_w))
                except Exception:
                    pw = start_w
                prog = (min(100, max(0, int(abs(pw - start_w) / total_change * 100)))
                        if total_change > 0.01 else 100)
                story.append(MilestoneLine(
                    week=m.get("Week", i + 1),
                    weight=pw,
                    focus=m.get("Focus", ""),
                    progress_pct=prog,
                    col_str=m_cols[i % len(m_cols)],
                    is_last=(i == len(milestones) - 1),
                ))
        story.append(Gap(10))

    # Disclaimer
    story.append(Gap(4))
    story.append(P(
        "This report is generated for educational purposes only and is not a medical diagnosis, "
        "clinical assessment, or substitute for professional healthcare advice. "
        "Always consult a qualified healthcare professional regarding any medical concerns.",
        ps("disc", fontSize=7.5, leading=10, textColor=HexColor("#64748B")),
    ))

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    buffer.seek(0)
    return buffer.read()


# ── Modules (main) ────
with st.expander("⚙️ Choose modules", expanded=False):
    st.caption("Turn modules on/off. (Nothing is stored.)")
    cA, cB = st.columns(2)
    with cA:
        run_bmi = st.toggle("BMI calculator", value=True, key="s_bmi")
        run_vo2 = st.toggle("VO2max estimate", value=True, key="s_vo2")
        run_bioage = st.toggle("Biological age", value=True, key="s_bio")
    with cB:
        run_conditions = st.toggle("Conditions & recommendations", value=True, key="s_conditions")
        run_plan = st.toggle("Weight goal / plan", value=True, key="s_plan")

# ── Sidebar (kept minimal) ────
st.sidebar.info("This app does not store personal health data.")

# ── Session state defaults ────────────────────────────────────────────────────
if "resting_hr" not in st.session_state:
    st.session_state["resting_hr"] = None
if "exercise_kcal_per_week" not in st.session_state:
    st.session_state["exercise_kcal_per_week"] = 0.0
if "global_avg_hr" not in st.session_state:
    st.session_state["global_avg_hr"] = None
if "age" not in st.session_state:
    st.session_state["age"] = 30
if "global_resting_hr" not in st.session_state:
    st.session_state["global_resting_hr"] = None
if "global_waist_cm" not in st.session_state:
    st.session_state["global_waist_cm"] = None
if "global_hip_cm" not in st.session_state:
    st.session_state["global_hip_cm"] = None

# ── Basic inputs ──────────────────────────────────────────────────────────────
st.markdown("## 🧾 Basic information")
st.caption("These inputs drive BMI, calories, VO2 and biological age estimates.")
st.markdown('<div class="ht-card">', unsafe_allow_html=True)
resting_hr_basic = st.number_input(
    "Resting HR (bpm)",
    min_value=30, max_value=120,
    value=st.session_state.get("resting_hr") or 60,
    key="basic_resting_hr",
    on_change=sync_from_basic,
)
if st.session_state.get("resting_hr") is None and resting_hr_basic is not None:
    st.session_state["resting_hr"] = int(resting_hr_basic)
    st.session_state["global_resting_hr"] = int(resting_hr_basic)

age_input = st.number_input("Age (years)", min_value=5, max_value=120,
                             value=st.session_state.get("age", 30), key="age")
try:
    age = int(st.session_state.get("age", 30))
except Exception:
    age = 30

c1, c2 = st.columns(2)
with c1:
    sex = st.selectbox("Sex", ["M", "F"], index=0, key="inp_sex")
with c2:
    pass  # placeholder

c3, c4 = st.columns(2)
with c3:
    height_cm = st.number_input("Height (cm)", min_value=50, max_value=250, value=170, key="inp_height")
with c4:
    weight_kg = st.number_input("Weight (kg)", min_value=20.0, max_value=300.0, value=70.0,
                                 format="%.1f", key="inp_weight")
st.markdown("</div>", unsafe_allow_html=True)
if age < 18:
    st.warning("BMI and fitness estimates are less reliable under 18.")
elif age >= 70:
    st.info("For older adults, BMI is often less informative.")

# local defaults
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
vo2_method = "Questionnaire"
vo2_distance_m = 0.0
rockport_time_min = 0.0
rockport_hr = 0

# ── BMI inputs ────────────────────────────────────────────────────────────────
if run_bmi:
    with st.expander("BMI inputs and body composition", expanded=True):
        st.markdown("BMI is a simple screening tool, not a diagnosis.")
        use_waist_hip = st.toggle("I don't know my waist & hip measurements", value=False, key="b_use_whr")
        if not use_waist_hip:
            c1, c2 = st.columns(2)
            with c1:
                waist_cm = st.number_input("Waist (cm)", min_value=30.0, max_value=300.0,
                                            value=float(st.session_state.get("global_waist_cm") or 80.0),
                                            format="%.1f", key="b_waist")
            with c2:
                hip_cm = st.number_input("Hip (cm)", min_value=30.0, max_value=300.0,
                                          value=float(st.session_state.get("global_hip_cm") or 95.0),
                                          format="%.1f", key="b_hip")
            st.session_state["global_waist_cm"] = waist_cm
            st.session_state["global_hip_cm"] = hip_cm
        use_neck = st.toggle("I don't know my neck measurement", value=False, key="b_use_neck")
        if not use_neck:
            neck_cm = st.number_input("Neck (cm)", min_value=20.0, max_value=80.0,
                                       value=38.0, format="%.1f", key="b_neck")
        bodyfat_requested = st.checkbox("Estimate body fat (Navy method)", value=False, key="b_bodyfat")

# ── VO2 inputs ────────────────────────────────────────────────────────────────
if run_vo2:
    with st.expander("❤️ Cardio / VO2max", expanded=True):

        # ── Activity level — visual card selector ──
        _act_options = ["Sedentary", "Light", "Moderate", "Active", "Very active", "Athlete"]
        _act_icons   = ["🛋️", "🚶", "🚴", "🏃", "⚡", "🏅"]
        _act_descs   = ["Desk job, no exercise", "1–2x/week light", "3–4x/week moderate",
                        "5x/week vigorous", "6–7x/week or daily", "2x/day / elite"]

        _current_act = st.session_state.get("v_activity", "Moderate")

        st.markdown("**Activity level**")
        _act_cols = st.columns(6)
        for _ci, (_ao, _ai, _ad) in enumerate(zip(_act_options, _act_icons, _act_descs)):
            with _act_cols[_ci]:
                _selected = (_ao == _current_act)
                if st.button(
                    f"{_ai}\n{_ao}\n{_ad}",
                    key=f"act_btn_{_ci}",
                    type="primary" if _selected else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["v_activity"] = _ao

        activity_level = st.session_state.get("v_activity", "Moderate")

        st.markdown("---")

        # ── Weekly minutes slider ──
        weekly_minutes = st.slider(
            "⏱️ Weekly minutes of moderate-to-vigorous activity",
            min_value=0, max_value=600, value=150, step=10,
            key="v_weekly_minutes", format="%d min"
        )
        _who = "✅ Meets WHO guidelines (150+ min/week)" if weekly_minutes >= 150 else "⚠️ Below WHO guidelines (aim for 150+ min/week)"
        _who_color = "#22C55E" if weekly_minutes >= 150 else "#F59E0B"
        st.markdown(f'<div style="color:{_who_color};font-size:12px;margin-top:-8px;margin-bottom:8px;">{_who}</div>',
                    unsafe_allow_html=True)

        # ── Session intensity ──
        session_intensity = st.slider(
            "💪 Typical session intensity",
            min_value=1, max_value=5, value=3, key="v_session_intensity"
        )
        _int_labels = {1: "😴 Very light", 2: "🚶 Light", 3: "🚴 Moderate", 4: "🏃 Hard", 5: "🔥 Max effort"}
        st.markdown(f'<div style="color:#94A3B8;font-size:12px;margin-top:-8px;margin-bottom:8px;">{_int_labels[session_intensity]}</div>',
                    unsafe_allow_html=True)

        st.markdown("---")

        # ── Heart rate ──
        st.markdown("**❤️ Heart rate**")
        resting_hr_unknown = st.toggle(
            "I don't know my resting heart rate",
            value=(st.session_state.get("global_resting_hr") is None),
            key="vo2_rhr_unknown"
        )
        if not resting_hr_unknown:
            default_rhr = st.session_state.get("global_resting_hr") or 70
            resting_hr = st.slider("Resting HR (bpm)", min_value=30, max_value=120,
                    value=int(default_rhr), key="vo2_rhr_value",
                    on_change=sync_from_vo2)
            _hr_zone = "🟢 Athletic" if resting_hr < 55 else "🟡 Normal" if resting_hr < 75 else "🔴 Elevated"
            st.caption(f"{_hr_zone} — prefilled from basic inputs above.")
        else:
            resting_hr = None

        max_hr_unknown = st.toggle("I don't know my max heart rate", value=False, key="vo2_maxhr_unknown")
        if not max_hr_unknown:
            max_hr = st.slider("Max HR (bpm)", min_value=100, max_value=240,
                    value=180, key="vo2_maxhr_val")
            _age_pred = 220 - int(age) if age else 190
            st.caption(f"Age-predicted max: ~{_age_pred} bpm")
        else:
            max_hr = None

        st.markdown("---")

        # ── VO2 method ──
        st.markdown("**🧪 VO2max calculation method**")
        vo2_method = st.radio(
            "Method",
            ["Questionnaire", "Cooper (12-min)", "Rockport (1-mile)", "Measured value"],
            index=0, key="vo2_method_select", horizontal=True,
            label_visibility="collapsed"
        )

        _method_info = {
            "Questionnaire": "📋 Estimated from activity level, HR and BMI. Good for general use.",
            "Cooper (12-min)": "🏃 Run as far as possible in 12 min. Very accurate.",
            "Rockport (1-mile)": "🚶 Walk 1 mile, record time and HR at finish.",
            "Measured value": "⌚ Enter a value from Apple Watch, Garmin, or lab test.",
        }
        st.caption(_method_info.get(vo2_method, ""))

        if vo2_method == "Cooper (12-min)":
            vo2_distance_m = st.slider("Distance covered in 12 min (meters)",
                    min_value=0, max_value=4000, value=2400, step=50,
                    key="vo2_cooper_distance", format="%d m")
            st.caption(f"Estimated VO2max: ~{(vo2_distance_m - 504.9) / 44.73:.1f} ml/kg/min" if vo2_distance_m > 504 else "Enter distance above")
        elif vo2_method == "Rockport (1-mile)":
            rockport_time_min = st.slider("1-mile walk time (minutes)",
                    min_value=8.0, max_value=30.0, value=15.0, step=0.5,
                    key="vo2_rockport_time", format="%.1f min")
            rockport_hr = st.slider("Heart rate at finish (bpm)",
                    min_value=60, max_value=200, value=140,
                    key="vo2_rockport_hr")
        elif vo2_method == "Measured value":
            measured_vo2_input = st.slider(
                "Your measured VO2max (ml/kg/min)",
                min_value=10.0, max_value=90.0, value=40.0, step=0.5,
                key="vo2_measured_input", format="%.1f ml/kg/min"
            )
        else:
            measured_vo2_input = 0.0

# ── Exercise calories ─────────────────────────────────────────────────────────
ACTIVITIES = {
    "Walking (casual)":              {"Light": 2.8, "Moderate": 3.5, "Hard": 4.3},
    "Brisk walking":                 {"Light": 3.5, "Moderate": 4.3, "Hard": 5.0},
    "Running/jogging":               {"Light": 7.0, "Moderate": 9.8, "Hard": 11.5},
    "Cycling (leisure)":             {"Light": 4.0, "Moderate": 6.8, "Hard": 8.5},
    "Cycling (vigorous)":            {"Light": 6.8, "Moderate": 8.5, "Hard": 10.0},
    "Strength training (weights)":   {"Light": 3.0, "Moderate": 4.5, "Hard": 6.0},
    "HIIT":                          {"Light": 6.0, "Moderate": 8.0, "Hard": 10.0},
    "Swimming":                      {"Light": 5.0, "Moderate": 7.0, "Hard": 9.5},
    "Rowing (moderate/vigorous)":    {"Light": 5.0, "Moderate": 7.0, "Hard": 8.5},
    "Elliptical":                    {"Light": 4.5, "Moderate": 6.0, "Hard": 8.0},
    "Stair climbing / Stairmaster":  {"Light": 6.0, "Moderate": 8.0, "Hard": 10.0},
    "Yoga / Pilates":                {"Light": 2.5, "Moderate": 3.0, "Hard": 4.0},
    "Dancing":                       {"Light": 3.0, "Moderate": 5.0, "Hard": 7.0},
    "Hiking (incline)":              {"Light": 3.5, "Moderate": 6.0, "Hard": 7.0},
    "Rock climbing / Bouldering":    {"Light": 4.0, "Moderate": 7.0, "Hard": 8.0},
    "Boxing / Martial arts":         {"Light": 6.0, "Moderate": 8.0, "Hard": 10.0},
    "Basketball / Team sports":      {"Light": 5.0, "Moderate": 7.0, "Hard": 10.0},
    "Soccer (football)":             {"Light": 6.0, "Moderate": 7.5, "Hard": 10.0},
    "Tennis (casual)":               {"Light": 4.0, "Moderate": 7.0, "Hard": 9.0},
    "Squash":                        {"Light": 7.0, "Moderate": 9.0, "Hard": 11.0},
    "Badminton":                     {"Light": 4.0, "Moderate": 6.0, "Hard": 8.0},
    "Table tennis (bordtennis)":     {"Light": 2.5, "Moderate": 4.0, "Hard": 5.5},
    "Gardening / Heavy yard work":   {"Light": 3.0, "Moderate": 4.5, "Hard": 6.0},
    "Housework / Light chores":      {"Light": 2.0, "Moderate": 3.0, "Hard": 3.5},
}

with st.expander("🏃 Exercise log", expanded=True):

    # ── Activity picker — grouped visual cards ──
    _act_groups = {
        "🚶 Low impact":   ["Walking (casual)", "Brisk walking", "Yoga / Pilates", "Housework / Light chores", "Gardening / Heavy yard work"],
        "🚴 Cardio":       ["Cycling (leisure)", "Cycling (vigorous)", "Elliptical", "Rowing (moderate/vigorous)", "Swimming"],
        "🏃 High impact":  ["Running/jogging", "HIIT", "Stair climbing / Stairmaster"],
        "⚽ Sports":       ["Basketball / Team sports", "Soccer (football)", "Tennis (casual)", "Squash", "Badminton", "Table tennis (bordtennis)", "Dancing"],
        "💪 Strength":     ["Strength training (weights)", "Boxing / Martial arts", "Rock climbing / Bouldering", "Hiking (incline)"],
    }
    _act_icons_map = {
        "Walking (casual)": "🚶", "Brisk walking": "🚶‍♂️", "Running/jogging": "🏃",
        "Cycling (leisure)": "🚲", "Cycling (vigorous)": "🚴", "Strength training (weights)": "🏋️",
        "HIIT": "⚡", "Swimming": "🏊", "Rowing (moderate/vigorous)": "🚣",
        "Elliptical": "🔄", "Stair climbing / Stairmaster": "🪜", "Yoga / Pilates": "🧘",
        "Dancing": "💃", "Hiking (incline)": "🥾", "Rock climbing / Bouldering": "🧗",
        "Boxing / Martial arts": "🥊", "Basketball / Team sports": "🏀", "Soccer (football)": "⚽",
        "Tennis (casual)": "🎾", "Squash": "🏸", "Badminton": "🏸",
        "Table tennis (bordtennis)": "🏓", "Gardening / Heavy yard work": "🌱",
        "Housework / Light chores": "🧹",
    }

    st.markdown("**🎯 Activity type**")
    _current_act = st.session_state.get("ui_activity_type", "Walking (casual)")
    _group_names = list(_act_groups.keys())
    if "ui_act_group" not in st.session_state:
        st.session_state["ui_act_group"] = next(
            (g for g, acts in _act_groups.items() if _current_act in acts), _group_names[0]
        )
    _sel_group = st.radio("Category", _group_names,
                    horizontal=True, key="ui_act_group", label_visibility="collapsed")

    _group_acts = _act_groups[_sel_group]
    _n = len(_group_acts)
    _gcols = st.columns(_n)
    for _gi, _ga in enumerate(_group_acts):
        with _gcols[_gi]:
            _is_sel = (_ga == st.session_state.get("ui_activity_type", "Walking (casual)"))
            _ico = _act_icons_map.get(_ga, "🏅")
            _short = _ga.split("(")[0].split("/")[0].strip()
            if st.button(
                f"{_ico}\n{_short}",
                key=f"act_type_btn_{_sel_group}_{_gi}",
                type="primary" if _is_sel else "secondary",
                use_container_width=True,
            ):
                st.session_state["ui_activity_type"] = _ga

    activity_ex = st.session_state.get("ui_activity_type", "Walking (casual)")
    if activity_ex not in _group_acts:
        activity_ex = _group_acts[0]
        st.session_state["ui_activity_type"] = activity_ex

    st.markdown("---")

    # ── Intensity — visual 3-button style ──
    st.markdown("**💪 Intensity**")
    _int_opts = ["Light", "Moderate", "Hard"]
    _int_icons = ["🟢", "🟡", "🔴"]
    _int_descs = ["Easy, can hold conversation", "Slightly breathless", "Hard, can barely talk"]
    _int_cols = st.columns(3)
    _cur_int = st.session_state.get("ui_intensity", "Moderate")
    for _ii, (_io, _iico, _id) in enumerate(zip(_int_opts, _int_icons, _int_descs)):
        with _int_cols[_ii]:
            _is_int = (_io == _cur_int)
            if st.button(
                f"{_iico}\n{_io}\n{_id}",
                key=f"int_btn_{_ii}",
                type="primary" if _is_int else "secondary",
                use_container_width=True,
            ):
                st.session_state["ui_intensity"] = _io
    intensity_label = st.session_state.get("ui_intensity", "Moderate")

    st.markdown("---")

    # ── Sessions + Duration ──
    st.markdown("**📅 Volume**")
    _vc1, _vc2 = st.columns(2)
    with _vc1:
        sessions_per_week = st.slider("Sessions per week", min_value=0, max_value=14,
                                       value=3, step=1, key="ui_sessions_per_week")
    with _vc2:
        minutes_per_session = st.slider("Minutes per session", min_value=5, max_value=180,
                                         value=45, step=5, key="ui_minutes", format="%d min")

    _total_min = sessions_per_week * minutes_per_session
    _who_ex = "✅ Meets WHO guidelines" if _total_min >= 150 else f"⚠️ {150 - _total_min} min/week below WHO target"
    _who_ex_color = "#22C55E" if _total_min >= 150 else "#F59E0B"
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.04);border-radius:10px;padding:8px 12px;'
        f'display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
        f'<span style="color:#94A3B8;font-size:12px;">Total: <b style="color:#E5E7EB;">{_total_min} min/week</b></span>'
        f'<span style="color:{_who_ex_color};font-size:12px;">{_who_ex}</span>'
        f'</div>', unsafe_allow_html=True
    )

    # ── RPE ──
    st.markdown("**😤 Perceived exertion (RPE)**")
    rpe = st.slider("RPE", 1, 10, 5, key="ui_rpe", label_visibility="collapsed")
    _rpe_labels = {1:"😴 Rest",2:"🧘 Very easy",3:"🚶 Easy",4:"🚶‍♂️ Moderate",5:"🚴 Somewhat hard",
                   6:"🏃 Hard",7:"🏃‍♂️ Very hard",8:"⚡ Very very hard",9:"🔥 Near max",10:"💀 Max effort"}
    st.markdown(f'<div style="color:#94A3B8;font-size:12px;margin-top:-8px;">{_rpe_labels[rpe]}</div>',
                unsafe_allow_html=True)
    rpe_multiplier = 0.85 + (rpe - 1) * (0.4 / 9)

    st.markdown("---")

    # ── HR refinement ──
    default_avg = st.session_state.get("global_avg_hr")
    avg_hr = default_avg if default_avg is not None else 130
    st.session_state["global_avg_hr"] = int(avg_hr)

    use_hr = st.toggle("❤️ Use average session HR to refine estimate", key="ui_use_hr")
    avg_hr_for_calc = None
    resting_hr_for_calc = None
    if use_hr:
        _hc1, _hc2 = st.columns(2)
        with _hc1:
            avg_hr_for_calc = st.slider("Avg session HR (bpm)", min_value=60, max_value=200,
                                         value=int(avg_hr), key="ui_avg_hr_calc")
        with _hc2:
            resting_hr_for_calc = st.slider("Resting HR (bpm)", min_value=30, max_value=100,
                                             value=int(st.session_state.get("global_resting_hr") or 60),
                                             key="ui_resting_hr",
                                             on_change=sync_from_calc)
        _hr_reserve = avg_hr_for_calc - resting_hr_for_calc
        st.caption(f"HR reserve used: {_hr_reserve} bpm — higher reserve = more accurate calorie estimate")

    manual_kcal = st.toggle("🔢 I know my exact kcal burn per session", key="ui_manual_kcal")
    if manual_kcal:
        manual_kcal_val = st.slider("kcal burned per session", min_value=0, max_value=2000,
                                     value=300, step=10, key="ui_manual_kcal_val", format="%d kcal")
    else:
        manual_kcal_val = 0.0

    # ── Compute ──
    try:
        base_met = ACTIVITIES.get(activity_ex, {}).get(intensity_label, 4.0)
    except Exception:
        base_met = 4.0
    try:
        w_ex = float(weight_kg)
    except Exception:
        w_ex = 70.0

    if manual_kcal and manual_kcal_val > 0:
        kcal_per_session = float(manual_kcal_val)
    else:
        kcal_per_min = (base_met * 3.5 * w_ex) / 200.0
        kcal_per_session = kcal_per_min * float(minutes_per_session) * rpe_multiplier
        if avg_hr_for_calc is not None and resting_hr_for_calc:
            hr_delta = max(0.0, float(avg_hr_for_calc) - float(resting_hr_for_calc))
            hr_multiplier = 1.0 + min(0.5, hr_delta / 100.0)
            kcal_per_session *= hr_multiplier

    kcal_per_week_ex = sessions_per_week * kcal_per_session
    st.session_state["exercise_kcal_per_week"] = kcal_per_week_ex
    st.session_state["exercise_last"] = {
        "activity": activity_ex, "intensity": intensity_label,
        "minutes": int(minutes_per_session), "sessions_per_week": int(sessions_per_week),
        "kcal_per_session": round(kcal_per_session, 1),
        "kcal_per_week": round(kcal_per_week_ex, 1),
        "rpe": int(rpe),
        "avg_hr": int(avg_hr_for_calc) if avg_hr_for_calc is not None else None,
    }

    # ── Live burn summary card ──
    _burn_color = "#22C55E" if kcal_per_week_ex >= 1500 else "#3B82F6" if kcal_per_week_ex >= 500 else "#94A3B8"
    st.markdown(
        f'<div style="background:rgba(15,23,42,0.7);border:1px solid rgba(148,163,184,0.15);'
        f'border-radius:14px;padding:14px 16px;margin-top:10px;">'
        f'<div style="color:#94A3B8;font-size:11px;margin-bottom:4px;">ESTIMATED WEEKLY BURN</div>'
        f'<div style="color:{_burn_color};font-weight:800;font-size:28px;">{kcal_per_week_ex:.0f} kcal/week</div>'
        f'<div style="color:#94A3B8;font-size:12px;margin-top:4px;">'
        f'{kcal_per_session:.0f} kcal/session × {sessions_per_week} sessions · '
        f'{_act_icons_map.get(activity_ex,"🏅")} {activity_ex}</div>'
        f'<div style="margin-top:10px;background:rgba(255,255,255,0.05);border-radius:999px;height:6px;overflow:hidden;">'
        f'<div style="width:{min(100, int(kcal_per_week_ex/30))}%;background:{_burn_color};height:100%;border-radius:999px;"></div>'
        f'</div>'
        f'<div style="color:#64748B;font-size:10px;margin-top:4px;">MET-based estimate · adjust RPE or use HR for more accuracy</div>'
        f'</div>',
        unsafe_allow_html=True
    )

# ── Biological age inputs ─────────────────────────────────────────────────────
if run_bioage:
    with st.expander("Biological age inputs", expanded=True):
        st.caption("Leave any field blank or use 'I don't know' where available.")

        t_core, t_cardio, t_life, t_body = st.tabs(["Core", "Cardio", "Lifestyle", "Body comp"])

        with t_core:
            c1, c2 = st.columns(2)
            with c1:
                smoker = st.toggle("Smoker?", key="bio_smoker")
                diabetes = st.toggle("Diabetes?", key="bio_diabetes")
            with c2:
                family_history = st.toggle(
                    "Family history of premature cardiovascular disease?",
                    key="bio_family_hist",
                )
                if sex == "F":
                    menopause = st.toggle("Post-menopausal?", key="bio_menopause")

        with t_cardio:
            st.markdown("#### 🫀 Cardiovascular")
            bp_unknown = st.toggle("I don't know my systolic blood pressure", value=False, key="bio_bp_unknown")
            if not bp_unknown:
                bp_systolic = st.number_input(
                    "Systolic blood pressure (mmHg)",
                    min_value=70.0, max_value=260.0, value=120.0, key="bio_bp_val"
                )

            chol_unknown = st.toggle("I don't know my cholesterol", value=False, key="bio_chol_unknown")
            if not chol_unknown:
                cholesterol = st.number_input(
                    "Cholesterol (mg/dL)",
                    min_value=50.0, max_value=500.0, value=180.0, key="bio_chol_val"
                )

            _bio_rhr_known = st.session_state.get("global_resting_hr")
            rhr_unknown = st.toggle("I don't know my resting heart rate",
                                    value=(_bio_rhr_known is None), key="bio_rhr_unknown")
            if not rhr_unknown:
                resting_hr = st.number_input(
                    "Resting heart rate (bpm)",
                    min_value=30, max_value=220,
                    value=int(_bio_rhr_known or 70), key="bio_rhr_val",
                    on_change=sync_from_bio
                )

        with t_life:
            st.markdown("#### 😴 Lifestyle")
            sleep_unknown = st.toggle("I don't know my sleep duration", value=False, key="bio_sleep_unknown")
            if not sleep_unknown:
                sleep_hours = st.number_input(
                    "Average sleep per night (hours)",
                    min_value=0.0, max_value=24.0, value=7.0, format="%.1f", key="bio_sleep_val"
                )

            alcohol_unknown = st.toggle("I don't know my alcohol intake", value=False, key="bio_alc_unknown")
            if not alcohol_unknown:
                alcohol_units = st.number_input(
                    "Alcohol units per week",
                    min_value=0, max_value=300, value=0, key="bio_alc_val"
                )

            fruit_veg = st.number_input(
                "Daily fruit & vegetable servings",
                min_value=0, max_value=20, value=3, key="bio_fv"
            )
            perceived_stress = st.slider(
                "Perceived stress (1 low – 10 high)",
                min_value=1, max_value=10, value=5, key="bio_stress"
            )

        with t_body:
            st.markdown("#### ⚖️ Body composition")
            grip_unknown = st.toggle("I don't know my grip strength", value=False, key="bio_grip_unknown")
            if not grip_unknown:
                grip_strength = st.number_input(
                    "Grip strength (kg)",
                    min_value=0.0, max_value=100.0, value=30.0, format="%.1f", key="bio_grip_val"
                )

            bio_waist_unknown = st.toggle("I don't know my waist-to-hip ratio", value=False, key="bio_waist_unknown")
            if not bio_waist_unknown:
                c1, c2 = st.columns(2)
                with c1:
                    waist_bio = st.number_input(
                        "Waist (cm)", min_value=30.0, max_value=300.0,
                        value=float(st.session_state.get("global_waist_cm") or 80.0),
                        format="%.1f", key="bio_waist_val"
                    )
                with c2:
                    hip_bio = st.number_input(
                        "Hip (cm)", min_value=30.0, max_value=300.0,
                        value=float(st.session_state.get("global_hip_cm") or 95.0),
                        format="%.1f", key="bio_hip_val"
                    )
                if waist_cm is None:
                    waist_cm = waist_bio
                if hip_cm is None:
                    hip_cm = hip_bio

# ── Conditions ────────────────────────────────────────────────────────────────
selected_conditions = []
custom_condition = ""
condition_goal_focus = "General"

if run_conditions:
    with st.expander("Conditions & recommendations", expanded=True):
        st.markdown("Select any diagnoses/conditions to get practical exercise & prevention tips.")
        if hasattr(calculators, "DIAGNOSIS_RECOMMENDATIONS"):
            condition_options = sorted(list(calculators.DIAGNOSIS_RECOMMENDATIONS.keys()))
        else:
            condition_options = ["Type 2 Diabetes", "Hypertension", "Lower Back Pain", "Asthma", "Osteoarthritis"]
        selected_conditions = st.multiselect("Select conditions", options=condition_options,
                                              default=[], key="cond_select")
        custom_condition = st.text_input("Other condition (free text)", "", key="cond_custom")
        if custom_condition.strip():
            selected_conditions = (selected_conditions or []) + [custom_condition.strip()]
        condition_goal_focus = st.selectbox("Recommendations focus",
                                             ["General", "VO2", "Weight", "Mobility"],
                                             index=0, key="cond_goal")

# ── Weight goal / plan ────────────────────────────────────────────────────────
create_plan = False
target_weight = None
target_bmi = None
plan_weeks = 12

if run_plan and run_bmi:
    with st.expander("🎯 Goal / plan", expanded=True):        # Visual toggle
        create_plan = st.toggle("Activate weight goal plan", value=False, key="plan_create")

        if create_plan:
            # Current weight for reference
            _cw = float(weight_kg) if weight_kg else 70.0
            _min_w = max(30.0, _cw - 40.0)
            _max_w = min(250.0, _cw + 40.0)

            st.markdown("#### 🎯 Set your target")

            plan_mode = st.radio(
                "What do you want to target?",
                ["⚖️ Target weight (kg)", "📊 Target BMI"],
                index=0, key="plan_type", horizontal=True
            )

            if "⚖️" in plan_mode:
                target_weight = st.slider(
                    "Target weight (kg)",
                    min_value=float(_min_w),
                    max_value=float(_max_w),
                    value=max(float(_min_w), min(float(_max_w), _cw - 5.0)),
                    step=0.5,
                    key="plan_target_weight",
                    format="%.1f kg"
                )
                _diff = target_weight - _cw
                _dir = "lose" if _diff < 0 else "gain"
                _col = "#22C55E" if _diff < 0 else "#3B82F6"
                st.markdown(
                    f'<div style="background:rgba(34,197,94,0.08);border:1px solid {_col}44;'
                    f'border-radius:12px;padding:10px 14px;margin:6px 0;">'
                    f'<span style="color:{_col};font-weight:700;font-size:18px;">'
                    f'{abs(_diff):.1f} kg to {_dir}</span>'
                    f'<span style="color:#94A3B8;font-size:13px;margin-left:10px;">'
                    f'({_cw:.1f} kg → {target_weight:.1f} kg)</span></div>',
                    unsafe_allow_html=True
                )
                target_bmi = None
            else:
                target_bmi = st.slider(
                    "Target BMI",
                    min_value=16.0, max_value=35.0,
                    value=22.0, step=0.1,
                    key="plan_target_bmi",
                    format="%.1f"
                )
                _h = float(height_cm) / 100.0 if height_cm else 1.70
                _implied_w = target_bmi * _h * _h
                st.markdown(
                    f'<div style="background:rgba(59,130,246,0.08);border:1px solid #3B82F644;'
                    f'border-radius:12px;padding:10px 14px;margin:6px 0;">'
                    f'<span style="color:#3B82F6;font-weight:700;font-size:18px;">BMI {target_bmi:.1f}</span>'
                    f'<span style="color:#94A3B8;font-size:13px;margin-left:10px;">'
                    f'= {_implied_w:.1f} kg at your height</span></div>',
                    unsafe_allow_html=True
                )
                target_weight = None

            st.markdown("#### ⏱️ Timeline")
            plan_weeks = st.slider(
                "Weeks to reach target",
                min_value=4, max_value=52, value=12, step=1,
                key="plan_weeks",
                format="%d weeks"
            )

            # Visual timeline preview
            _wks = int(plan_weeks)
            _tw = target_weight if target_weight else (target_bmi * (float(height_cm)/100)**2 if target_bmi and height_cm else _cw)
            _rate = (_tw - _cw) / _wks if _wks > 0 else 0
            _safe = abs(_rate) <= 1.0
            _rate_color = "#22C55E" if _safe else "#F59E0B"

            _warn_html = ""
            if not _safe:
                _warn_html = (
                    '<div style="color:#F59E0B;font-size:12px;margin-top:10px;">'
                    "⚠️ Rate above 1 kg/week — consider a longer timeline for safety."
                    "</div>"
                )

            _preview_html = (
                '<div style="background:rgba(15,23,42,0.6);border:1px solid rgba(148,163,184,0.15);'
                'border-radius:14px;padding:14px 16px;margin-top:8px;">'
                '<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;">'
                '<div style="text-align:center;">'
                '<div style="color:#94A3B8;font-size:11px;margin-bottom:2px;">RATE</div>'
                f'<div style="color:{_rate_color};font-weight:800;font-size:20px;">{_rate:+.2f} kg/wk</div>'
                '</div>'
                '<div style="text-align:center;">'
                '<div style="color:#94A3B8;font-size:11px;margin-bottom:2px;">DURATION</div>'
                f'<div style="color:#E5E7EB;font-weight:800;font-size:20px;">{_wks} wks</div>'
                '</div>'
                '<div style="text-align:center;">'
                '<div style="color:#94A3B8;font-size:11px;margin-bottom:2px;">TARGET</div>'
                f'<div style="color:#E5E7EB;font-weight:800;font-size:20px;">{_tw:.1f} kg</div>'
                '</div>'
                '</div>'
                f'{_warn_html}'
                '</div>'
            )
            st.markdown(_preview_html, unsafe_allow_html=True)

# ── Calculate ─────────────────────────────────────────────────────────────────
if st.button("Calculate / Generate report", key="btn_calculate"):
    import traceback, logging

    def _f(val, name=""):
        try:
            if val is None:
                return None
            if isinstance(val, (int, float)):
                return float(val)
            s = str(val).strip()
            return None if s == "" else float(s.replace(",", "."))
        except Exception as e:
            raise ValueError(f"Cannot convert '{name}' to float: {val!r} ({e})")

    def _i(val, name=""):
        try:
            if val is None:
                return None
            if isinstance(val, int):
                return val
            s = str(val).strip()
            return None if s == "" else int(float(s))
        except Exception as e:
            raise ValueError(f"Cannot convert '{name}' to int: {val!r} ({e})")

    try:
        age_i = _i(age, "age")
        if age_i is None:
            raise ValueError("Age must be a number.")
        height_f = _f(height_cm, "height_cm")
        weight_f = _f(weight_kg, "weight_kg")
        if height_f is None or weight_f is None:
            raise ValueError("Height and weight must be numbers.")

        waist_f = _f(waist_cm, "waist_cm")
        hip_f = _f(hip_cm, "hip_cm")
        neck_f = _f(neck_cm, "neck_cm")
        measured_vo2_f = _f(measured_vo2_input, "measured_vo2")
        vo2_dist_f = _f(vo2_distance_m, "vo2_distance")
        rockport_time_f = _f(rockport_time_min, "rockport_time")
        rockport_hr_i = _i(rockport_hr, "rockport_hr")
        weekly_min_i = _i(weekly_minutes, "weekly_minutes")
        session_int_i = _i(session_intensity, "session_intensity")
        resting_hr_i = _i(resting_hr, "resting_hr")
        max_hr_i = _i(max_hr, "max_hr")
        plan_weeks_i = _i(plan_weeks, "plan_weeks")
        target_weight_f = _f(target_weight, "target_weight")
        target_bmi_f = _f(target_bmi, "target_bmi")

        results = {}

        # BMI
        if run_bmi:
            bmi_value, bmi_category = calculators.bmi_calc(weight_f, height_f)
            results["bmi"] = {"value": float(bmi_value), "category": bmi_category}
            if waist_f is not None and hip_f is not None:
                whr_value = calculators.waist_hip_ratio(waist_f, hip_f)
                results["whr"] = {"value": float(whr_value),
                                   "category": calculators.whr_category(sex, whr_value)}

        # Body fat
        if bodyfat_requested and neck_f is not None:
            try:
                if sex == "M":
                    if waist_f is None:
                        raise ValueError("Waist required for male body-fat estimate.")
                    bf = calculators.body_fat_navy(sex=sex, height_cm=height_f,
                                                    neck_cm=neck_f, waist_cm=waist_f)
                else:
                    if waist_f is None or hip_f is None:
                        raise ValueError("Waist and hip required for female body-fat estimate.")
                    bf = calculators.body_fat_navy(sex=sex, height_cm=height_f,
                                                    neck_cm=neck_f, waist_cm=waist_f, hip_cm=hip_f)
                results["bodyfat"] = {"value": round(float(bf), 1)}
            except Exception as e:
                st.warning(f"Body-fat estimate skipped: {e}")

        # VO2
        if run_vo2:
            vo2_method_sel = st.session_state.get("vo2_method_select", vo2_method)
            if measured_vo2_f is not None and measured_vo2_f > 0:
                vo2_value = calculators.vo2_measured_value(measured_vo2_f)
                method_used = "Measured value"
            elif vo2_method_sel == "Cooper (12-min)":
                vo2_value = calculators.vo2_cooper_from_distance(float(vo2_dist_f or 0.0))
                method_used = "Cooper (12-min)"
            elif vo2_method_sel == "Rockport (1-mile)":
                if rockport_time_f is None:
                    raise ValueError("Rockport time must be a number.")
                vo2_value = calculators.vo2_rockport_1mile(
                    float(rockport_time_f), int(rockport_hr_i or 0),
                    weight_f, age_i, sex)
                method_used = "Rockport (1-mile)"
            else:
                bmi_v = results["bmi"]["value"] if "bmi" in results else calculators.bmi_calc(weight_f, height_f)[0]
                vo2_value = calculators.vo2_questionnaire_estimate(
                    age=age_i, sex=sex,
                    weekly_minutes=int(weekly_min_i or 0),
                    session_intensity_score=int(session_int_i or 1),
                    activity_level=st.session_state.get("v_activity", activity_level),
                    bmi=bmi_v,
                    resting_hr=int(resting_hr_i) if resting_hr_i is not None else None,
                    max_hr=int(max_hr_i) if max_hr_i is not None else None,
                )
                method_used = "Questionnaire"

            vo2_ref = calculators.vo2_reference(age_i, sex, float(vo2_value))
            vo2_tips = calculators.vo2_improvement_tips(
                vo2_value=float(vo2_value), sex=sex, age=age_i,
                activity_level=st.session_state.get("v_activity", activity_level),
                weekly_minutes=int(weekly_min_i or 0),
            )
            top_descriptor = calculators.vo2_top_descriptor(age_i, sex, float(vo2_value))
            results["vo2"] = {
                "value": round(float(vo2_value), 1),
                "method": method_used,
                "age_band": vo2_ref.get("age_band"),
                "percentile": vo2_ref.get("percentile"),
                "rating": vo2_ref.get("rating"),
                "mean": vo2_ref.get("mean"),
                "tips": vo2_tips,
                "top_descriptor": top_descriptor,
            }

        # Biological age
        if run_bioage:
            bmi_v = results["bmi"]["value"] if "bmi" in results else calculators.bmi_calc(weight_f, height_f)[0]
            waist_to_hip = None
            if waist_f is not None and hip_f is not None:
                try:
                    waist_to_hip = calculators.waist_hip_ratio(waist_f, hip_f)
                except Exception:
                    pass
            measured_vo2_for_bio = results.get("vo2", {}).get("value")
            bio_age, bio_factors = calculators.estimate_biological_age_detailed(
                age=age_i, sex=sex,
                smoker=st.session_state.get("bio_smoker", False),
                bmi=bmi_v,
                activity_level=st.session_state.get("v_activity", activity_level),
                sleep_hours=_f(st.session_state.get("bio_sleep_val"), "sleep"),
                alcohol_units_per_week=_f(st.session_state.get("bio_alc_val"), "alcohol"),
                fruit_veg_servings=_f(st.session_state.get("bio_fv"), "fruit_veg"),
                perceived_stress=st.session_state.get("bio_stress", perceived_stress),
                grip_strength_kg=_f(st.session_state.get("bio_grip_val"), "grip"),
                bp_systolic=_f(st.session_state.get("bio_bp_val"), "bp"),
                cholesterol_mg_dl=_f(st.session_state.get("bio_chol_val"), "chol"),
                diabetes=st.session_state.get("bio_diabetes", False),
                resting_hr=_i(st.session_state.get("bio_rhr_val") or resting_hr_i, "rhr"),
                waist_to_hip_ratio=waist_to_hip,
                family_history=st.session_state.get("bio_family_hist", False),
                menopause=st.session_state.get("bio_menopause", False),
                measured_vo2=measured_vo2_for_bio,
            )
            results["bio_age"] = {"value": round(float(bio_age), 1)}
            results["bio_factors"] = bio_factors

        # Conditions
        if run_conditions:
            recs = calculators.recommendations_for_diagnoses(
                st.session_state.get("cond_select", []) or selected_conditions,
                st.session_state.get("cond_goal", condition_goal_focus)
            )
            results["triage"] = {"level": "Info", "message": "Recommendations generated for selected conditions."}
            results["triage_recommendations"] = recs

        # Plan
        if run_plan and run_bmi and create_plan:
            target_w = (target_bmi_f * (height_f / 100.0) ** 2) if target_bmi_f else target_weight_f
            if target_w:
                ekpw = float(st.session_state.get("exercise_kcal_per_week", 0.0))
                plan = calculators.generate_weight_plan(
                    current_weight_kg=weight_f,
                    target_weight_kg=target_w,
                    weeks=int(plan_weeks_i or 12),
                    sex=sex, height_cm=height_f, age=age_i,
                    activity_level=st.session_state.get("v_activity", activity_level),
                    exercise_kcal_per_week=ekpw,
                )
                if plan.get("error"):
                    st.error(plan.get("message"))
                else:
                    results["plan"] = plan

    except Exception as e:
        st.error(f"Error during calculation: {e}")
        st.text(traceback.format_exc())
        logging.exception("Calculation failed")
        st.session_state["results"] = {}
    else:
        st.session_state["results"] = results
        st.success("Calculation finished — results ready.")

# ── Display results ───────────────────────────────────────────────────────────
results = st.session_state.get("results", {})

if results:
        # --- BMI SEKSJON ---
    if "bmi" in results:
        st.subheader("BMI")
        b = results["bmi"]["value"]
        cat = results["bmi"]["category"]

        # Fargekode basert på kategori
        if b < 18.5:
            bmi_color = "#3B82F6"
            bmi_emoji = "⬇️"
        elif b < 25.0:
            bmi_color = "#22C55E"
            bmi_emoji = "✅"
        elif b < 30.0:
            bmi_color = "#F59E0B"
            bmi_emoji = "⚠️"
        else:
            bmi_color = "#EF4444"
            bmi_emoji = "🔴"

        # Marker-posisjon på linja (0–45 skala → 0–100%)
        marker_pct = min(100, max(0, (b / 45.0) * 100))

        components.html(f"""
<style>
  .bmi-wrap {{
    font-family: Arial, sans-serif;
    background: #1F2937;
    border: 1px solid #374151;
    border-radius: 16px;
    padding: 20px 22px 18px 22px;
    color: #E5E7EB;
    max-width: 100%;
  }}
  .bmi-top {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 18px;
  }}
  .bmi-val {{
    font-size: 48px;
    font-weight: 800;
    color: {bmi_color};
    line-height: 1;
  }}
  .bmi-cat {{
    font-size: 14px;
    color: #9CA3AF;
    margin-top: 4px;
  }}
  .bmi-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: {bmi_color}22;
    border: 1px solid {bmi_color};
    color: {bmi_color};
    font-size: 14px;
    font-weight: 700;
    border-radius: 999px;
    padding: 6px 14px;
  }}
  .bmi-track-wrap {{
    position: relative;
    margin-bottom: 8px;
  }}
  .bmi-track {{
    display: flex;
    height: 20px;
    border-radius: 999px;
    overflow: hidden;
    width: 100%;
  }}
  .bmi-seg {{
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 700;
    color: rgba(0,0,0,0.7);
  }}
  .bmi-marker-row {{
    position: relative;
    height: 28px;
    margin-top: 2px;
  }}
  .bmi-marker {{
    position: absolute;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  .bmi-arrow {{
    width: 0; height: 0;
    border-left: 7px solid transparent;
    border-right: 7px solid transparent;
    border-bottom: 12px solid {bmi_color};
  }}
  .bmi-marker-val {{
    font-size: 12px;
    font-weight: 800;
    color: {bmi_color};
    margin-top: 2px;
    white-space: nowrap;
  }}
  .bmi-labels {{
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    color: #6B7280;
    margin-top: 4px;
  }}
  .bmi-legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;
  }}
  .bmi-leg-item {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    color: #CBD5E1;
    background: #111827;
    border: 1px solid #374151;
    border-radius: 999px;
    padding: 4px 10px;
  }}
  .bmi-dot {{
    width: 9px; height: 9px;
    border-radius: 50%;
    flex: 0 0 9px;
  }}
</style>

<div class="bmi-wrap">
  <div class="bmi-top">
    <div>
      <div class="bmi-val" id="bmi-val-anim">0.0</div>
      <div class="bmi-cat">Body Mass Index</div>
    </div>
    <div class="bmi-badge">{bmi_emoji} {cat}</div>
  </div>

  <div class="bmi-track-wrap">
    <div class="bmi-track">
      <!-- Underweight: 0–18.5 = 41.1% of 45 -->
      <div class="bmi-seg" style="width:41.1%; background:#3B82F6;">Under</div>
      <!-- Normal: 18.5–25 = 14.4% -->
      <div class="bmi-seg" style="width:14.4%; background:#22C55E;">Normal</div>
      <!-- Overweight: 25–30 = 11.1% -->
      <div class="bmi-seg" style="width:11.1%; background:#F59E0B;">Over</div>
      <!-- Obese: 30–45 = 33.3% -->
      <div class="bmi-seg" style="width:33.3%; background:#EF4444;">Obese</div>
    </div>

    <div class="bmi-marker-row">
      <div class="bmi-marker" style="left:{marker_pct:.1f}%;">
        <div class="bmi-arrow"></div>
        <div class="bmi-marker-val">{b:.1f}</div>
      </div>
    </div>
  </div>

  <div class="bmi-labels">
    <span>0</span>
    <span>18.5</span>
    <span>25</span>
    <span>30</span>
    <span>45+</span>
  </div>

  <div class="bmi-legend">
    <div class="bmi-leg-item"><span class="bmi-dot" style="background:#3B82F6"></span>Underweight (&lt;18.5)</div>
    <div class="bmi-leg-item"><span class="bmi-dot" style="background:#22C55E"></span>Normal (18.5–24.9)</div>
    <div class="bmi-leg-item"><span class="bmi-dot" style="background:#F59E0B"></span>Overweight (25–29.9)</div>
    <div class="bmi-leg-item"><span class="bmi-dot" style="background:#EF4444"></span>Obese (30+)</div>
  </div>
</div>
<script>
(function() {{
  var target = {b:.4f};
  var el = document.getElementById('bmi-val-anim');
  if (!el) return;
  var start = null, duration = 900;
  function step(ts) {{
    if (!start) start = ts;
    var p = Math.min((ts - start) / duration, 1);
    var ease = 1 - Math.pow(1 - p, 3);
    el.textContent = (target * ease).toFixed(1);
    if (p < 1) requestAnimationFrame(step);
    else el.textContent = target.toFixed(1);
  }}
  requestAnimationFrame(step);
}})();
</script>
        """, height=260)

    # ── Energy & Metabolism ───────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Energy og Metabolism")

    def _to_float(val):
        try:
            return float(str(val).replace(",", ".").strip())
        except Exception:
            return None

    calc_age_f = _to_float(age)
    calc_weight = _to_float(weight_kg)
    calc_height = _to_float(height_cm)

    if calc_age_f is None or calc_weight is None or calc_height is None:
        st.info("Fyll inn alder, vekt og høyde for kaloriberegning.")
    else:
        bmr_val = bmr_mifflin(age=int(calc_age_f), sex=sex,
                               weight_kg=float(calc_weight), height_cm=float(calc_height))
        daily_living = bmr_val * 1.2
        # ── FIX: use actual exercise kcal/week from session_state ──
        w_kcal = float(st.session_state.get("exercise_kcal_per_week", 0.0))
        tdee_total = tdee_including_weekly_exercise(
            bmr_val,
            st.session_state.get("v_activity", activity_level),
            w_kcal
        )
        st.session_state["latest_tdee_total"] = float(tdee_total)

        c1, c2, c3 = st.columns(3)
        c1.metric("BMR (base metabolic rate)", f"{int(bmr_val)} kcal")
        c2.metric("Daily burn (sedentary)", f"{int(daily_living)} kcal")
        c3.metric("Total daily burn incl. exercise", f"{int(tdee_total)} kcal")

        if w_kcal > 0:
            st.caption(f"Exercise contribution: {w_kcal:.0f} kcal/week = "
                       f"{w_kcal/7:.0f} kcal/day added to TDEE.")

# ── VO2 ───────────────────────────────────────────────────────────────────
        if "vo2" in results:
            st.markdown("---")
            st.subheader("VO2 max & fitness")
    
            v_val = float(results["vo2"]["value"])
            v_pct = max(0.0, min(100.0, float(results["vo2"].get("percentile") or 0)))
            top_text = f"Top {100 - v_pct:.1f}%"
    
        if v_pct >= 90:
            pct_color = "#22C55E"; pct_label = "Excellent"
        elif v_pct >= 80:
            pct_color = "#3B82F6"; pct_label = "Very good"
        elif v_pct >= 60:
            pct_color = "#7C7CF5"; pct_label = "Good"
        elif v_pct >= 40:
            pct_color = "#F59E0B"; pct_label = "Below average"
        else:
            pct_color = "#EF6A3B"; pct_label = "Low"
        
        _vo2_html = """
<style>
  .vo2-row {
    display: flex; gap: 12px; font-family: Arial, sans-serif;
    background: #1F2937; border: 1px solid #374151;
    border-radius: 16px; padding: 18px 20px;
  }
  .vo2-card {
    flex: 1; text-align: center;
    background: #111827; border-radius: 12px; padding: 14px 8px;
    border: 1px solid #374151;
  }
  .vo2-label {
    font-size: 10px; color: #6B7280; text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 6px;
  }
  .vo2-num {
    font-size: 36px; font-weight: 800; line-height: 1; color: VO2COLOR;
  }
  .vo2-sub {
    font-size: 11px; color: #9CA3AF; margin-top: 4px;
  }
</style>
<div class="vo2-row">
  <div class="vo2-card">
    <div class="vo2-label">VO2 max</div>
    <div class="vo2-num" id="vo2-val-anim">0.0</div>
    <div class="vo2-sub">ml/kg/min</div>
  </div>
  <div class="vo2-card">
    <div class="vo2-label">Percentile</div>
    <div class="vo2-num" id="vo2-pct-anim">0</div>
    <div class="vo2-sub">of your age group</div>
  </div>
  <div class="vo2-card">
    <div class="vo2-label">Ranking</div>
    <div class="vo2-num" style="font-size:22px;padding-top:7px;">PCT_LABEL</div>
    <div class="vo2-sub">TOP_TEXT</div>
  </div>
</div>
<script>
(function() {
  function animCount(id, target, decimals, duration) {
    var el = document.getElementById(id);
    if (!el) return;
    var start = null;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / duration, 1);
      var ease = 1 - Math.pow(1 - p, 3);
      el.textContent = (target * ease).toFixed(decimals);
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = target.toFixed(decimals);
    }
    requestAnimationFrame(step);
  }
  animCount('vo2-val-anim', VO2VAL, 1, 1000);
  animCount('vo2-pct-anim', VO2PCT, 0, 1000);
})();
</script>
        """
        _vo2_html = (
            _vo2_html
            .replace("VO2COLOR", pct_color)
            .replace("VO2VAL", f"{v_val:.4f}")
            .replace("VO2PCT", f"{v_pct:.1f}")
            .replace("PCT_LABEL", pct_label)
            .replace("TOP_TEXT", top_text)
        )
        components.html(_vo2_html, height=150)

        if v_pct >= 90:
            pct_color = "#22C55E"; pct_label = "Excellent"
        elif v_pct >= 80:
            pct_color = "#3B82F6"; pct_label = "Very good"
        elif v_pct >= 60:
            pct_color = "#7C7CF5"; pct_label = "Good"
        elif v_pct >= 40:
            pct_color = "#F59E0B"; pct_label = "Below average"
        else:
            pct_color = "#EF6A3B"; pct_label = "Low"

        if v_pct >= 90:
            interpretation_text = "You are performing excellent compared to the average for your age."
        elif v_pct >= 80:
            interpretation_text = "You are performing very well compared to the average for your age."
        elif v_pct >= 60:
            interpretation_text = "You are around the average to good range for your age."
        elif v_pct >= 40:
            interpretation_text = "You are slightly below average for your age."
        else:
            interpretation_text = "You are below the average for your age, but this is very trainable."

        vo2_rows = [
            ("20–29", 44, 40, "#26A690"),
            ("30–39", 40, 36, "#3B82F6"),
            ("40–49", 37, 33, "#7C7CF5"),
            ("50–59", 34, 30, "#F59E0B"),
            ("60+",   30, 27, "#EF6A3B"),
        ]

        def band_match(band: str) -> bool:
            if band == "20–29": return 20 <= age <= 29
            if band == "30–39": return 30 <= age <= 39
            if band == "40–49": return 40 <= age <= 49
            if band == "50–59": return 50 <= age <= 59
            return age >= 60

        active_band = next((b for b, *_ in vo2_rows if band_match(b)), None)

        if str(sex).upper().startswith("M"):
            current_avg = {b: m for b, m, _, _ in vo2_rows}
        else:
            current_avg = {b: w for b, _, w, _ in vo2_rows}

        # ── Age band bars (Plotly) ──
        import plotly.graph_objects as go

        st.markdown("#### VO2 max across age bands")

        bands = [r[0] for r in vo2_rows]
        avgs  = [current_avg[r[0]] for r in vo2_rows]
        colors_list = [pct_color if r[0] == active_band else r[3] for r in vo2_rows]
        labels = ["← Your group" if r[0] == active_band else "Average" for r in vo2_rows]

        fig_bands = go.Figure()

        fig_bands.add_trace(go.Bar(
            x=avgs,
            y=bands,
            orientation="h",
            marker=dict(
                color=colors_list,
                line=dict(width=0),
            ),
            text=[f"{a} ml/kg/min" for a in avgs],
            textposition="outside",
            textfont=dict(color="#9CA3AF", size=11),
            hovertemplate="<b>%{y}</b><br>Average: %{x} ml/kg/min<extra></extra>",
            name="Age band avg",
        ))

        fig_bands.add_vline(
            x=v_val,
            line=dict(color="white", width=2, dash="dash"),
            annotation_text=f"You: {v_val:.1f}",
            annotation_font=dict(color="white", size=12),
            annotation_position="top right",
        )

        fig_bands.update_layout(
            paper_bgcolor="#111827",
            plot_bgcolor="#1F2937",
            font=dict(color="#E5E7EB", family="Arial"),
            height=320,
            margin=dict(l=10, r=80, t=20, b=40),
            xaxis=dict(
                title="VO2 max (ml/kg/min)",
                color="#9CA3AF",
                gridcolor="#374151",
                range=[0, max(avgs + [v_val]) + 8],
            ),
            yaxis=dict(
                color="#D1D5DB",
                gridcolor="#374151",
            ),
            showlegend=False,
        )

        st.plotly_chart(fig_bands, use_container_width=True)

        # ── Percentile gauge (Plotly) ──
        st.markdown(f"#### Population percentile")

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=v_pct,
            number=dict(
                suffix="th",
                font=dict(size=48, color=pct_color),
            ),
            delta=dict(
                reference=50,
                increasing=dict(color="#22C55E"),
                decreasing=dict(color="#EF4444"),
                valueformat=".1f",
            ),
            title=dict(
                text=f"<b>{pct_label}</b><br><span style='font-size:13px;color:#9CA3AF'>{interpretation_text}</span>",
                font=dict(size=16, color="#F9FAFB"),
            ),
            gauge=dict(
                axis=dict(
                    range=[0, 100],
                    tickwidth=1,
                    tickcolor="#374151",
                    tickfont=dict(color="#9CA3AF", size=11),
                    nticks=6,
                ),
                bar=dict(color=pct_color, thickness=0.25),
                bgcolor="#1F2937",
                borderwidth=0,
                steps=[
                    dict(range=[0, 40],  color="#1a1a2e"),
                    dict(range=[40, 60], color="#1e2a3a"),
                    dict(range=[60, 80], color="#1a2e2a"),
                    dict(range=[80, 100],color="#1a2e1a"),
                ],
                threshold=dict(
                    line=dict(color="white", width=3),
                    thickness=0.8,
                    value=v_pct,
                ),
            ),
        ))

        fig_gauge.update_layout(
            paper_bgcolor="#111827",
            font=dict(color="#E5E7EB", family="Arial"),
            height=340,
            margin=dict(l=20, r=20, t=60, b=20),
        )

        st.plotly_chart(fig_gauge, use_container_width=True)

        col_l, col_m, col_r = st.columns(3)
        col_l.metric("Your percentile", f"{v_pct:.0f}th", f"{v_pct - 50:.1f} vs avg")
        col_m.metric("Rating", pct_label)
        col_r.metric("Top", f"{100 - v_pct:.0f}%")
        # VO2 tips
        tips = results["vo2"].get("tips", [])
        if tips:
            st.markdown("**VO2 improvement tips**")
            for tip in tips:
                st.write(f"• {tip}")

# ── Biological age ────
    if "bio_age" in results:
            st.markdown("---")
            st.subheader("Biological age")
            _bio_val = results["bio_age"]["value"]
            _chron = float(age)
            _diff = _bio_val - _chron
            _diff_color = "#22C55E" if _diff <= 0 else "#EF4444"
            _diff_label = f"{abs(_diff):.1f} years younger" if _diff <= 0 else f"{abs(_diff):.1f} years older"
            _diff_sign = "▼" if _diff <= 0 else "▲"
            _factors_html = "".join([
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">'
                '<div style="font-size:11px;color:#9CA3AF;min-width:140px;max-width:140px;'
                'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + f["label"] + '</div>'
                '<div style="flex:1;background:rgba(255,255,255,0.06);border-radius:999px;height:10px;overflow:hidden;">'
                '<div style="width:' + str(max(3, min(100, abs(f.get("delta", 0)) / 5 * 100))) + '%;height:100%;border-radius:999px;'
                'background:' + ("#22C55E" if f.get("delta", 0) <= 0 else "#EF4444") + ';"></div></div>'
                '<div style="font-size:11px;font-weight:700;min-width:52px;text-align:right;'
                'color:' + ("#22C55E" if f.get("delta", 0) <= 0 else "#EF4444") + ';">'
                + f'{f.get("delta", 0):+.0f} yrs' +
                '</div></div>'
                for f in results.get("bio_factors", [])
            ])
            st.markdown(
                '<div style="font-family:Arial,sans-serif;background:#1F2937;border:1px solid #374151;'
                'border-radius:16px;padding:20px 22px 18px 22px;color:#E5E7EB;">'
                '<div style="display:flex;justify-content:space-between;align-items:flex-start;'
                'margin-bottom:18px;flex-wrap:wrap;gap:12px;">'
                '<div><div style="font-size:52px;font-weight:800;color:' + _diff_color + ';line-height:1;">'
                + f"{_bio_val:.1f}" +
                '</div><div style="font-size:13px;color:#9CA3AF;margin-top:4px;">Biological age &nbsp;&middot;&nbsp; Chronological: '
                + f"{_chron:.0f}" + ' yrs</div></div>'
                '<div style="display:inline-flex;align-items:center;gap:6px;background:' + _diff_color + '22;'
                'border:1px solid ' + _diff_color + ';color:' + _diff_color + ';font-size:14px;font-weight:700;'
                'border-radius:999px;padding:6px 14px;">' + _diff_sign + " " + _diff_label + ' than average</div>'
                '</div>'
                '<div style="font-size:12px;font-weight:700;color:#6B7280;letter-spacing:0.08em;'
                'text-transform:uppercase;margin-bottom:10px;">Factor breakdown</div>'
                + _factors_html +
                '</div>',
                unsafe_allow_html=True,
            )


# ── Conditions ────
    if "triage" in results:
        st.markdown("---")
        st.subheader("Conditions & recommendations")
        if results.get("triage_recommendations"):
            _rec_cards_html = ""
            for _r in results["triage_recommendations"]:
                _r_lower = str(_r).lower()
                if any(w in _r_lower for w in ["avoid", "risk", "warning", "stop", "danger", "limit"]):
                    _rc = "#EF4444"; _ri = "⚠️"; _rbg = "rgba(239,68,68,0.08)"; _rb = "rgba(239,68,68,0.25)"
                elif any(w in _r_lower for w in ["exercise", "train", "cardio", "walk", "run", "strength", "activity"]):
                    _rc = "#3B82F6"; _ri = "🏃"; _rbg = "rgba(59,130,246,0.08)"; _rb = "rgba(59,130,246,0.25)"
                elif any(w in _r_lower for w in ["diet", "eat", "food", "nutrition", "calori", "protein", "vegetable", "fruit"]):
                    _rc = "#22C55E"; _ri = "🥗"; _rbg = "rgba(34,197,94,0.08)"; _rb = "rgba(34,197,94,0.25)"
                elif any(w in _r_lower for w in ["sleep", "stress", "mental", "relax", "breath", "meditat"]):
                    _rc = "#A78BFA"; _ri = "😴"; _rbg = "rgba(167,139,250,0.08)"; _rb = "rgba(167,139,250,0.25)"
                elif any(w in _r_lower for w in ["doctor", "consult", "medical", "physician", "specialist", "monitor"]):
                    _rc = "#F59E0B"; _ri = "🩺"; _rbg = "rgba(245,158,11,0.08)"; _rb = "rgba(245,158,11,0.25)"
                else:
                    _rc = "#0EA5A3"; _ri = "💡"; _rbg = "rgba(14,165,163,0.08)"; _rb = "rgba(14,165,163,0.25)"
                _rec_cards_html += (
                    '<div style="display:flex;align-items:flex-start;gap:12px;'
                    'background:' + _rbg + ';border:1px solid ' + _rb + ';'
                    'border-left:3px solid ' + _rc + ';border-radius:12px;'
                    'padding:12px 14px;margin-bottom:8px;">'
                    '<div style="font-size:18px;line-height:1.3;">' + _ri + '</div>'
                    '<div style="font-size:13px;color:#E5E7EB;line-height:1.6;">' + str(_r) + '</div>'
                    '</div>'
                )
            st.markdown(_rec_cards_html, unsafe_allow_html=True)
        else:
            st.info(results.get("triage", {}).get("message", "No triage details."))

    # ── Plan ──────────────────────────────────────────────────────────────────
        # ── Plan ────
    if "plan" in results:
        plan = results["plan"]
        st.markdown("---")
        st.subheader("🎯 Weight goal / plan")

        current_maint = float(st.session_state.get("latest_tdee_total",
                    plan.get("current_needs_kcal", 0) or 0.0))
        kg_per_week = float(plan.get("kg_per_week", 0.0) or 0.0)
        daily_change_kcal = kg_per_week * 7700.0 / 7.0
        recommended_daily = int(round(current_maint + daily_change_kcal))
        plan["current_needs_kcal"] = int(round(current_maint))
        plan["recommended_daily_kcal"] = recommended_daily

        if plan.get("warning"):
            st.warning(plan["warning"])

        # ── Top 3 metrics ──
        _pc1, _pc2, _pc3 = st.columns(3)
        _pc1.metric("Maintenance", f"{plan['current_needs_kcal']} kcal/day")
        _pc2.metric("Recommended", f"{plan['recommended_daily_kcal']} kcal/day",
                    delta=f"{plan['recommended_daily_kcal'] - plan['current_needs_kcal']:+d} kcal")
        _pc3.metric("Weekly change", f"{kg_per_week:+.2f} kg/wk")

        # ── Calorie deficit/surplus bar ──
        _deficit = plan['recommended_daily_kcal'] - plan['current_needs_kcal']
        _bar_color = "#22C55E" if _deficit < 0 else "#3B82F6"
        _bar_label = f"{'Deficit' if _deficit < 0 else 'Surplus'}: {abs(_deficit)} kcal/day"
        _bar_pct = min(100, int(abs(_deficit) / max(1, plan['current_needs_kcal']) * 100 * 5))
        st.markdown(
            f'<div style="margin:10px 0 4px 0;color:#94A3B8;font-size:12px;">{_bar_label}</div>'
            f'<div style="background:rgba(255,255,255,0.06);border-radius:999px;height:10px;overflow:hidden;">'
            f'<div style="width:{_bar_pct}%;background:{_bar_color};height:100%;border-radius:999px;'
            f'transition:width 0.4s;"></div></div>',
            unsafe_allow_html=True
        )

        # ── Milestone roadmap ──
        milestones = plan.get("milestones", [])
        if milestones:
            st.markdown("#### 🗺️ Milestone roadmap")
            _start_w = float(weight_kg)
            _end_w = float(milestones[-1].get("Projected weight (kg)", _start_w))
            _total_change = _end_w - _start_w
            _losing = _total_change < 0

            for i, m in enumerate(milestones):
                _wk = m.get("Week", i + 1)
                _pw = float(m.get("Projected weight (kg)", _start_w))
                _focus = m.get("Focus", "")
                _done = i == len(milestones) - 1

                # Progress toward goal
                if abs(_total_change) > 0.01:
                    _prog = min(100, max(0, int(abs(_pw - _start_w) / abs(_total_change) * 100)))
                else:
                    _prog = 100

                _is_last = i == len(milestones) - 1
                _dot_color = "#22C55E" if _is_last else "#3B82F6"
                _focus_icons = {
                    "Build routine": "🏗️",
                    "Maintain consistency": "🔄",
                    "Review progress": "📊",
                    "Re-check and set next goal": "🏁",
                }
                _icon = next((v for k, v in _focus_icons.items() if k.lower() in str(_focus).lower()), "📍")

                _connector = ""
                if not _is_last:
                    _connector = '<div style="width:2px;flex:1;min-height:20px;background:rgba(148,163,184,0.2);margin-top:2px;"></div>'

                _milestone_html = f"""
<div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:8px;">
  <div style="display:flex;flex-direction:column;align-items:center;min-width:28px;">
    <div style="width:28px;height:28px;border-radius:50%;background:{_dot_color};
    display:flex;align-items:center;justify-content:center;
    font-size:12px;font-weight:800;color:#fff;flex-shrink:0;">{_wk}</div>
    {_connector}
  </div>
  <div style="background:rgba(15,23,42,0.55);border:1px solid rgba(148,163,184,0.12);
  border-radius:12px;padding:10px 14px;flex:1;margin-bottom:4px;">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
      <div>
        <span style="color:#E5E7EB;font-weight:700;font-size:15px;">{_pw:.1f} kg</span>
        <span style="color:#94A3B8;font-size:12px;margin-left:8px;">{_icon} {_focus}</span>
      </div>
      <div style="background:rgba(255,255,255,0.06);border-radius:999px;
      padding:3px 10px;font-size:11px;color:#94A3B8;">Week {_wk} · {_prog}%</div>
    </div>
    <div style="margin-top:7px;background:rgba(255,255,255,0.05);
    border-radius:999px;height:5px;overflow:hidden;">
      <div style="width:{_prog}%;background:{_dot_color};height:100%;border-radius:999px;"></div>
    </div>
  </div>
</div>
"""
                st.markdown(_milestone_html, unsafe_allow_html=True)

                # ── Coach Insight ──
                _rate = float(plan.get("kg_per_week", 0.0) or 0.0)
                _tw_coach = float(milestones[-1].get("Projected weight (kg)", weight_kg)) if milestones else float(weight_kg)
                _wks_coach = int(plan_weeks) if plan_weeks else 12
                if _rate < 0:
                    _coach_msg = (
                        f"At {abs(_rate):.2f} kg/week, you are on a safe and sustainable fat loss trajectory. "
                        f"You will reach {_tw_coach:.1f} kg in approximately {_wks_coach} weeks. "
                        f"Consistency is your biggest advantage — small daily habits compound over time."
                    )
                    _coach_icon = "🟢"
                elif _rate > 0:
                    _coach_msg = (
                        f"You are in a controlled weight gain phase at {_rate:.2f} kg/week. "
                        f"Target: {_tw_coach:.1f} kg in {_wks_coach} weeks. "
                        f"Focus on strength training to maximise lean muscle gain."
                    )
                    _coach_icon = "🔵"
                else:
                    _coach_msg = (
                        "You are at maintenance calories. "
                        "Focus on body recomposition — building muscle while maintaining weight."
                    )
                    _coach_icon = "⚪"
        
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,rgba(14,165,163,0.12),rgba(34,197,94,0.08));'
                    f'border:1px solid rgba(14,165,163,0.3);border-left:4px solid #0EA5A3;'
                    f'border-radius:14px;padding:16px 18px;margin:14px 0;">'
                    f'<div style="color:#0EA5A3;font-size:12px;font-weight:700;letter-spacing:0.08em;'
                    f'text-transform:uppercase;margin-bottom:8px;">🧠 Coach Insight</div>'
                    f'<div style="color:#E5E7EB;font-size:14px;line-height:1.7;">{_coach_icon} {_coach_msg}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
else:
    st.info("Trykk på 'Calculate / Generate report' for å kjøre beregningene.")

# ── Paywall / PDF ──── (0 innrykk — UTANFOR if results:)
st.markdown("---")
_unlocked = st.session_state.get("report_unlocked", False)

if _unlocked:
    st.success("✅ Rapport låst opp!")

if not _unlocked:
    st.markdown(
        '<div style="background:linear-gradient(135deg,rgba(14,165,163,0.10),rgba(59,130,246,0.08));'
        'border:1px solid rgba(14,165,163,0.35);border-radius:18px;padding:24px 22px;'
        'text-align:center;margin:10px 0;">'
        '<div style="font-size:22px;font-weight:800;color:#E5E7EB;margin-bottom:6px;">'
        '🔒 Unlock your full report</div>'
        '<div style="color:#94A3B8;font-size:13px;margin-bottom:18px;">'
        'Get your complete personalized health analysis as a premium PDF</div>'
        '<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:10px;margin-bottom:20px;">'
        '<span style="background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);'
        'color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">✅ Full 12-week roadmap</span>'
        '<span style="background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);'
        'color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">✅ Personalized coach insights</span>'
        '<span style="background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);'
        'color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">✅ Calorie strategy</span>'
        '<span style="background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.3);'
        'color:#22C55E;border-radius:999px;padding:5px 14px;font-size:12px;">✅ PDF download</span>'
        '</div>'
        '<div style="font-size:28px;font-weight:800;color:#0EA5A3;margin-bottom:4px;">49 kr</div>'
        '<div style="color:#64748B;font-size:11px;margin-bottom:16px;">One-time · No subscription</div>'
        '</div>',
        unsafe_allow_html=True
    )
    stripe_link = "https://buy.stripe.com/fZu00kbeq6J50LsdYk1Fe02"
    st.link_button(
        "🔓 Unlock full report — 49 kr",
        stripe_link,
        type="primary",
        use_container_width=True,
    )
    st.caption("Etter betaling kjem du tilbake til appen. Legg til ?paid=true i URL-en for å låse opp.")

else:
    _results_for_pdf = st.session_state.get("results", {})
    if not _results_for_pdf:
        st.warning("⚠️ Kjør beregningane først (trykk 'Calculate'), så kan du laste ned PDF-rapporten.")
    else:
        report = {
            "generated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "inputs": {"age": age, "sex": sex, "height_cm": height_cm, "weight_kg": weight_kg},
            "bmi": _results_for_pdf.get("bmi"),
            "bodyfat": _results_for_pdf.get("bodyfat"),
            "whr": _results_for_pdf.get("whr"),
            "vo2": _results_for_pdf.get("vo2"),
            "bio_age": _results_for_pdf.get("bio_age"),
            "bio_factors": _results_for_pdf.get("bio_factors"),
            "triage": _results_for_pdf.get("triage"),
            "triage_recommendations": _results_for_pdf.get("triage_recommendations"),
            "plan": _results_for_pdf.get("plan"),
            "exercise_log": st.session_state.get("exercise_last"),
        }
        try:
            pdf_bytes = create_pdf_bytes(report)
            st.download_button(
                "📄 Download PDF report",
                data=pdf_bytes,
                file_name="health_tools_report.pdf",
                mime="application/pdf",
                key="pdf_btn",
            )
        except Exception as e:
            st.warning(f"PDF generation unavailable: {e}")
