"""
Hevy-Flow PDF Report Generator

Builds a dark-themed A4 PDF report from the same Plotly figures
used by the Streamlit dashboard.  Charts are exported to PNG via
kaleido, then composed onto pages with fpdf2.
"""

import io
import tempfile
from datetime import datetime

import pandas as pd
from fpdf import FPDF

from charts import (
    SLATE_950,
    TEAL,
    build_category_donut,
    build_category_volume,
    build_day_of_week,
    build_duration,
    build_frequency,
    build_rpe,
    build_strength,
    build_top_exercises,
    build_volume_timeline,
)

# ── Constants ────────────────────────────────────────

A4_W = 210  # mm
A4_H = 297  # mm
MARGIN = 12  # mm
CONTENT_W = A4_W - 2 * MARGIN
HALF_W = (CONTENT_W - 4) / 2  # two columns with 4 mm gap

# Dark background RGB
BG_R, BG_G, BG_B = 2, 6, 23  # SLATE_950 = #020617
TEAL_R, TEAL_G, TEAL_B = 45, 212, 191  # #2DD4BF
TEXT_R, TEXT_G, TEXT_B = 248, 250, 252  # SLATE_50

# ── Helpers ──────────────────────────────────────────


def _fig_to_png(fig, width=900, height=400) -> bytes:
    """Export a Plotly figure to PNG bytes via kaleido."""
    return fig.to_image(
        format="png",
        width=width,
        height=height,
        scale=2,
    )


def _add_dark_page(pdf: FPDF):
    """Add a new A4 page with dark background."""
    pdf.add_page()
    pdf.set_fill_color(BG_R, BG_G, BG_B)
    pdf.rect(0, 0, A4_W, A4_H, "F")


def _place_image(pdf: FPDF, img_bytes: bytes, x: float, y: float, w: float):
    """Write PNG bytes to a temp file and place on the PDF."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(img_bytes)
        f.flush()
        pdf.image(f.name, x=x, y=y, w=w)


def _heading(pdf: FPDF, text: str, size: int = 10):
    """Draw a teal section heading at the current cursor."""
    pdf.set_text_color(TEAL_R, TEAL_G, TEAL_B)
    pdf.set_font("Helvetica", "B", size)
    pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")


# ── Main Entry Point ─────────────────────────────────


def generate_report(
    workouts: pd.DataFrame,
    sets: pd.DataFrame,
    selected_ex: str = "All Exercises",
) -> bytes:
    """
    Generate a dark-themed A4 PDF report with all dashboard charts.

    Returns the PDF as bytes suitable for st.download_button.
    """
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(MARGIN, MARGIN, MARGIN)

    # Compute KPI values
    n_workouts = len(workouts)
    n_sets = len(sets)
    n_exercises = sets["exercise_title"].nunique() if not sets.empty else 0
    avg_dur = workouts["duration_minutes"].mean() if not workouts.empty else 0
    total_vol = (sets["weight_kg"] * sets["reps"]).sum() if not sets.empty else 0
    avg_rpe = sets["rpe"].dropna().mean() if not sets.empty else float("nan")

    date_min = workouts["date"].min().strftime("%b %d, %Y") if not workouts.empty else "—"
    date_max = workouts["date"].max().strftime("%b %d, %Y") if not workouts.empty else "—"

    # ── PAGE 1: Header + KPIs + Frequency ────────────
    _add_dark_page(pdf)

    # Title
    pdf.set_y(MARGIN)
    pdf.set_text_color(TEXT_R, TEXT_G, TEXT_B)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 12, "Hevy Flow Report", new_x="LMARGIN", new_y="NEXT")

    # Subtitle with date range
    pdf.set_text_color(148, 163, 184)  # SLATE_400
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(
        0,
        5,
        f"{date_min}  -  {date_max}   |   Generated {datetime.now().strftime('%b %d, %Y %H:%M')}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(6)

    # KPI boxes
    kpis = [
        ("Workouts", f"{n_workouts}"),
        ("Total Sets", f"{n_sets:,}"),
        ("Exercises", f"{n_exercises}"),
        ("Avg Duration", f"{avg_dur:.0f} min"),
        ("Total Volume", f"{total_vol:,.0f} kg"),
        ("Avg RPE", f"{avg_rpe:.1f}" if not pd.isna(avg_rpe) else "—"),
    ]
    kpi_w = (CONTENT_W - 5 * 3) / 6  # 6 boxes with 3 mm gaps
    kpi_y = pdf.get_y()
    for i, (label, value) in enumerate(kpis):
        kx = MARGIN + i * (kpi_w + 3)
        # Box background
        pdf.set_fill_color(15, 23, 42)  # SLATE_900
        pdf.set_draw_color(TEAL_R, TEAL_G, TEAL_B)
        pdf.rect(kx, kpi_y, kpi_w, 18, "FD")
        # Label
        pdf.set_xy(kx, kpi_y + 2)
        pdf.set_text_color(148, 163, 184)
        pdf.set_font("Helvetica", "", 6)
        pdf.cell(kpi_w, 4, label, align="C")
        # Value
        pdf.set_xy(kx, kpi_y + 7)
        pdf.set_text_color(TEAL_R, TEAL_G, TEAL_B)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(kpi_w, 8, value, align="C")

    pdf.set_y(kpi_y + 24)

    # Frequency chart
    _heading(pdf, "Workout Frequency")
    freq_png = _fig_to_png(build_frequency(workouts), width=1000, height=380)
    _place_image(pdf, freq_png, MARGIN, pdf.get_y(), CONTENT_W)

    # ── PAGE 2: Day-of-Week + RPE, Category Split ────
    _add_dark_page(pdf)
    pdf.set_y(MARGIN)

    _heading(pdf, "Training Days & RPE")
    chart_y = pdf.get_y()

    dow_png = _fig_to_png(build_day_of_week(workouts), width=550, height=380)
    _place_image(pdf, dow_png, MARGIN, chart_y, HALF_W)

    rpe_fig = build_rpe(sets)
    if rpe_fig is not None:
        rpe_png = _fig_to_png(rpe_fig, width=550, height=380)
        _place_image(pdf, rpe_png, MARGIN + HALF_W + 4, chart_y, HALF_W)

    pdf.set_y(chart_y + 80)
    pdf.ln(4)
    _heading(pdf, "Workout Distribution")
    cat_y = pdf.get_y()

    donut_png = _fig_to_png(build_category_donut(workouts), width=550, height=420)
    _place_image(pdf, donut_png, MARGIN, cat_y, HALF_W)

    vol_cat_png = _fig_to_png(build_category_volume(sets), width=550, height=420)
    _place_image(pdf, vol_cat_png, MARGIN + HALF_W + 4, cat_y, HALF_W)

    # ── PAGE 3: Volume Timeline + Strength ───────────
    _add_dark_page(pdf)
    pdf.set_y(MARGIN)

    _heading(pdf, "Volume Over Time")
    vol_png = _fig_to_png(build_volume_timeline(sets), width=1000, height=400)
    _place_image(pdf, vol_png, MARGIN, pdf.get_y(), CONTENT_W)

    pdf.set_y(pdf.get_y() + 80)
    pdf.ln(4)
    _heading(pdf, "Strength Progression")

    strength_fig, subtitle = build_strength(sets, selected_ex)
    if strength_fig is not None:
        if subtitle:
            pdf.set_text_color(148, 163, 184)
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(0, 5, subtitle, new_x="LMARGIN", new_y="NEXT")
        str_png = _fig_to_png(strength_fig, width=1000, height=440)
        _place_image(pdf, str_png, MARGIN, pdf.get_y(), CONTENT_W)
    else:
        pdf.set_text_color(148, 163, 184)
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, "No data for the selected exercise.", new_x="LMARGIN", new_y="NEXT")

    # ── PAGE 4: Top Exercises + Duration, Footer ─────
    _add_dark_page(pdf)
    pdf.set_y(MARGIN)

    _heading(pdf, "Top Exercises & Session Duration")
    chart_y = pdf.get_y()

    top_png = _fig_to_png(build_top_exercises(sets), width=550, height=480)
    _place_image(pdf, top_png, MARGIN, chart_y, HALF_W)

    dur_png = _fig_to_png(build_duration(workouts), width=550, height=480)
    _place_image(pdf, dur_png, MARGIN + HALF_W + 4, chart_y, HALF_W)

    # Footer
    pdf.set_y(A4_H - MARGIN - 8)
    pdf.set_text_color(148, 163, 184)
    pdf.set_font("Helvetica", "", 7)
    pdf.cell(
        0,
        5,
        "HEVY FLOW  ·  Python  ·  pandas  ·  Supabase (PostgreSQL)  ·  Streamlit  ·  Plotly",
        align="C",
    )

    # Output
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
