"""
Hevy-Flow Dashboard — Interactive Workout Analytics

A Streamlit dashboard that reads cleaned workout data from Supabase
(PostgreSQL) and presents interactive charts for tracking fitness progress.

Run with:  streamlit run dashboard.py
"""

import pandas as pd
import psycopg2
import streamlit as st

from charts import (
    AMBER,
    BG_GRADIENT_MID,
    CATEGORY_COLORS,
    CYAN,
    GRID_COLOR,
    METRIC_BG_END,
    METRIC_BG_START,
    METRIC_BORDER,
    METRIC_SHADOW,
    PLOTLY_LAYOUT,
    ROSE,
    SIDEBAR_GRAD_END,
    SIDEBAR_GRAD_START,
    SLATE_50,
    SLATE_300,
    SLATE_400,
    SLATE_900,
    SLATE_950,
    TEAL,
    TEAL_DIM,
    TEAL_GLOW,
    VIOLET,
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
from config import DATABASE_URL, HEVY_API_KEY
from etl.extract import extract_workouts
from etl.load import load_to_supabase
from etl.sync import run_incremental_sync
from etl.transform import transform_workouts

# ── Page Config ──────────────────────────────────────

st.set_page_config(
    page_title="Hevy Flow | Workout Analytics",
    page_icon="assets/icon.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ── Global ─────────────────────────── */
    html, body, [class*="st-"] {{
        font-family: 'Inter', sans-serif;
    }}

    .stApp {{
        background: linear-gradient(180deg, {SLATE_950} 0%, {BG_GRADIENT_MID} 50%, {SLATE_950} 100%);
    }}

    /* Hide Streamlit header (navbar) and footer */
    header[data-testid="stHeader"] {{
        display: none !important;
    }}
    footer[data-testid="stFooter"] {{
        display: none !important;
    }}


    /* ── Sidebar ────────────────────────── */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {SIDEBAR_GRAD_START} 0%, {SIDEBAR_GRAD_END} 100%);
        border-right: 1px solid {TEAL_DIM};
    }}

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
        color: {SLATE_400};
    }}

    /* ── KPI Cards ──────────────────────── */
    div[data-testid="stMetric"] {{
        background: linear-gradient(145deg, {METRIC_BG_START} 0%, {METRIC_BG_END} 100%);
        border: 1px solid {METRIC_BORDER};
        border-radius: 16px;
        padding: 20px 24px;
        backdrop-filter: blur(12px);
        box-shadow: {METRIC_SHADOW};
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }}

    div[data-testid="stMetric"]:hover {{
        border-color: {TEAL_GLOW};
        box-shadow:
            0 0 0 1px rgba(45, 212, 191, 0.08),
            0 8px 32px rgba(0, 0, 0, 0.3),
            0 0 20px rgba(45, 212, 191, 0.06),
            inset 0 1px 0 rgba(255, 255, 255, 0.03);
    }}

    div[data-testid="stMetric"] label {{
        color: {SLATE_400} !important;
        font-weight: 500 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 1.2px;
    }}

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: {TEAL} !important;
        font-weight: 700 !important;
        font-size: 1.75rem !important;
    }}

    /* ── Section Titles ─────────────────── */
    .section-title {{
        color: {SLATE_50};
        font-size: 1.15rem;
        font-weight: 600;
        letter-spacing: -0.01em;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    .section-title::after {{
        content: '';
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, rgba(45, 212, 191, 0.2) 0%, transparent 100%);
        margin-left: 12px;
    }}

    /* ── Sidebar Brand ──────────────────── */
    .sidebar-brand {{
        font-size: 1.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, {TEAL} 0%, {CYAN} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 2px;
    }}

    .sidebar-tagline {{
        color: {SLATE_400};
        font-size: 0.78rem;
        font-weight: 400;
        letter-spacing: 0.5px;
        margin-bottom: 16px;
    }}

    .sidebar-section {{
        color: {TEAL};
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-top: 12px;
        margin-bottom: 8px;
    }}

    .sidebar-stat {{
        background: {TEAL_DIM};
        border: 1px solid {METRIC_BORDER};
        border-radius: 10px;
        padding: 10px 14px;
        margin-top: 12px;
        color: {SLATE_300};
        font-size: 0.82rem;
    }}

    .sidebar-stat strong {{
        color: {TEAL};
    }}

    /* ── Dividers ────────────────────────── */
    hr {{
        border-color: {TEAL_DIM} !important;
        margin: 1.5rem 0 !important;
    }}

    /* ── Header ──────────────────────────── */
    .dash-header {{
        font-size: 1.8rem;
        font-weight: 800;
        color: {SLATE_50};
        letter-spacing: -0.02em;
        line-height: 1.2;
    }}

    .dash-header span {{
        background: linear-gradient(135deg, {TEAL} 0%, {CYAN} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}

    .dash-subtitle {{
        color: {SLATE_400};
        font-size: 0.85rem;
        margin-top: 4px;
        font-weight: 400;
    }}

    /* ── Footer ──────────────────────────── */
    .dash-footer {{
        text-align: center;
        color: {SLATE_400};
        opacity: 0.5;
        font-size: 0.72rem;
        letter-spacing: 0.3px;
        padding: 20px 0 10px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Data Loading ─────────────────────────────────────


@st.cache_data(ttl=300)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load workouts and workout_sets from Supabase PostgreSQL."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("SELECT * FROM workouts ORDER BY start_time DESC")
    w_cols = [desc[0] for desc in cur.description]
    workouts = pd.DataFrame(cur.fetchall(), columns=w_cols)

    cur.execute("""
        SELECT ws.*, w.workout_category, w.duration_minutes,
               w.day_of_week, w.date, w.month, w.year
        FROM workout_sets ws
        JOIN workouts w ON ws.workout_id = w.workout_id
        ORDER BY w.start_time DESC, ws.set_index
    """)
    s_cols = [desc[0] for desc in cur.description]
    sets = pd.DataFrame(cur.fetchall(), columns=s_cols)

    cur.close()
    conn.close()

    workouts["start_time"] = pd.to_datetime(workouts["start_time"])
    workouts["end_time"] = pd.to_datetime(workouts["end_time"])
    workouts["date"] = pd.to_datetime(workouts["date"])
    workouts["duration_minutes"] = pd.to_numeric(workouts["duration_minutes"])
    workouts["month"] = pd.to_numeric(workouts["month"])
    workouts["year"] = pd.to_numeric(workouts["year"])

    sets["date"] = pd.to_datetime(sets["date"])
    sets["weight_kg"] = pd.to_numeric(sets["weight_kg"])
    sets["reps"] = pd.to_numeric(sets["reps"])
    sets["duration_seconds"] = pd.to_numeric(sets["duration_seconds"])
    sets["rpe"] = pd.to_numeric(sets["rpe"])
    sets["duration_minutes"] = pd.to_numeric(sets["duration_minutes"])
    sets["month"] = pd.to_numeric(sets["month"])
    sets["year"] = pd.to_numeric(sets["year"])

    return workouts, sets


# ── Sidebar ──────────────────────────────────────────


def _run_incremental_pipeline(uploaded_file) -> dict:
    """Run the ETL pipeline on an uploaded CSV in incremental mode."""
    df_raw = extract_workouts(uploaded_file=uploaded_file)
    df_clean = transform_workouts(df_raw)
    stats = load_to_supabase(df_clean, incremental=True)
    return stats


def render_sidebar(workouts, sets):
    """Render sidebar filters and return filtered data."""
    with st.sidebar:
        st.markdown('<div class="sidebar-brand">Hevy-Flow</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="sidebar-tagline">Workout Analytics Dashboard</div>',
            unsafe_allow_html=True,
        )
        st.divider()

        # ── API Sync ────────────────────────────
        if HEVY_API_KEY:
            st.markdown(
                '<div class="sidebar-section">⚡ Sync from Hevy</div>',
                unsafe_allow_html=True,
            )
            if st.button("Sync from Hevy API", use_container_width=True, type="primary"):
                with st.spinner("Syncing with Hevy API ..."):
                    try:
                        stats = run_incremental_sync()
                        if stats["updated"] > 0 or stats["deleted"] > 0:
                            st.success(
                                f"Synced **{stats['updated']}** updated, "
                                f"**{stats['deleted']}** deleted"
                            )
                        else:
                            st.info("Already up to date — nothing new.")
                        load_data.clear()
                        st.rerun()
                    except Exception as exc:
                        st.error(f"API sync failed: {exc}")
            st.divider()

        # ── CSV Upload ───────────────────────────
        st.markdown('<div class="sidebar-section">Upload Workout Log</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Upload Hevy CSV",
            type=["csv"],
            label_visibility="collapsed",
            help="Export your workouts from the Hevy app and upload the CSV here.",
        )
        if uploaded is not None:
            if st.button("Run Pipeline", use_container_width=True, type="primary"):
                with st.spinner("Running Extract → Transform → Load ..."):
                    try:
                        stats = _run_incremental_pipeline(uploaded)
                        if stats["new_workouts"] > 0:
                            st.success(
                                f"Loaded **{stats['new_workouts']}** new sessions "
                                f"({stats['new_sets']:,} sets)"
                            )
                        else:
                            st.info("All sessions already in database — nothing new to load.")
                        if stats["skipped_workouts"] > 0:
                            st.caption(f"{stats['skipped_workouts']} existing sessions skipped")
                        # Clear cache so charts refresh
                        load_data.clear()
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Pipeline failed: {exc}")

        st.divider()

        # Date range
        st.markdown('<div class="sidebar-section">Date Range</div>', unsafe_allow_html=True)
        min_date = workouts["date"].min().date()
        max_date = workouts["date"].max().date()
        date_range = st.date_input(
            "date_range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            label_visibility="collapsed",
        )
        if len(date_range) == 2:
            s, e = date_range
            workouts = workouts[(workouts["date"].dt.date >= s) & (workouts["date"].dt.date <= e)]
            sets = sets[(sets["date"].dt.date >= s) & (sets["date"].dt.date <= e)]

        st.divider()

        # Category
        st.markdown('<div class="sidebar-section">Category</div>', unsafe_allow_html=True)
        cats = sorted(workouts["workout_category"].unique())
        selected_cats = st.multiselect("cats", cats, default=cats, label_visibility="collapsed")
        workouts = workouts[workouts["workout_category"].isin(selected_cats)]
        sets = sets[sets["workout_category"].isin(selected_cats)]

        st.divider()

        # Exercise
        st.markdown('<div class="sidebar-section">Exercise</div>', unsafe_allow_html=True)
        exercises = sorted(sets["exercise_title"].unique()) if not sets.empty else []
        selected_ex = st.selectbox(
            "exercise",
            ["All Exercises"] + exercises,
            label_visibility="collapsed",
        )

        st.divider()

        # Stats summary
        st.markdown(
            f'<div class="sidebar-stat">'
            f"<strong>{len(workouts)}</strong> workouts &nbsp;·&nbsp; "
            f"<strong>{len(sets):,}</strong> sets"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.divider()

        # PDF Export
        st.markdown(
            '<div class="sidebar-section">📄 Export Report</div>',
            unsafe_allow_html=True,
        )
        if st.button("Download PDF Report", use_container_width=True):
            with st.spinner("Generating PDF report ..."):
                from report import generate_report

                pdf_bytes = generate_report(workouts, sets, selected_ex)
            st.download_button(
                label="💾 Save PDF",
                data=pdf_bytes,
                file_name="hevy_flow_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    return workouts, sets, selected_ex


# ── Chart Functions ──────────────────────────────────


def section(title: str):
    """Render a styled section header."""
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def render_kpis(workouts, sets):
    """Top KPI row."""
    n_workouts = len(workouts)
    n_sets = len(sets)
    n_exercises = sets["exercise_title"].nunique() if not sets.empty else 0
    avg_dur = workouts["duration_minutes"].mean() if not workouts.empty else 0
    total_vol = (sets["weight_kg"] * sets["reps"]).sum() if not sets.empty else 0
    avg_rpe = sets["rpe"].dropna().mean() if not sets.empty else float("nan")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Workouts", f"{n_workouts}")
    c2.metric("Total Sets", f"{n_sets:,}")
    c3.metric("Exercises", f"{n_exercises}")
    c4.metric("Avg Duration", f"{avg_dur:.0f} min")
    c5.metric("Total Volume", f"{total_vol:,.0f} kg")
    c6.metric("Avg RPE", f"{avg_rpe:.1f}" if not pd.isna(avg_rpe) else "—")


def render_frequency(workouts):
    """Weekly workout frequency."""
    section("Workout Frequency")
    st.plotly_chart(build_frequency(workouts), use_container_width=True)


def render_category_split(workouts, sets):
    """Category donut + volume breakdown."""
    section("Workout Distribution")
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(build_category_donut(workouts), use_container_width=True)

    with col2:
        st.plotly_chart(build_category_volume(sets), use_container_width=True)


def render_volume_timeline(sets):
    """Stacked volume per session over time."""
    section("Volume Over Time")
    st.plotly_chart(build_volume_timeline(sets), use_container_width=True)


def render_strength(sets, exercise):
    """Strength progression chart."""
    section("Strength Progression")
    fig, subtitle = build_strength(sets, exercise)
    if fig is None:
        st.info("No data for the selected exercise.")
        return
    st.caption(subtitle)
    st.plotly_chart(fig, use_container_width=True)


def render_day_of_week(workouts):
    """Day-of-week bar chart."""
    st.plotly_chart(build_day_of_week(workouts), use_container_width=True)


def render_rpe(sets):
    """RPE trend over time."""
    fig = build_rpe(sets)
    if fig is None:
        st.info("No RPE data available.")
        return
    st.plotly_chart(fig, use_container_width=True)


def render_top_exercises(sets):
    """Top 10 exercises horizontal bar."""
    st.caption("Top 10 Exercises")
    st.plotly_chart(build_top_exercises(sets), use_container_width=True)


def render_duration(workouts):
    """Session duration scatter + rolling average."""
    st.caption("Session Duration")
    st.plotly_chart(build_duration(workouts), use_container_width=True)


# ── Main ─────────────────────────────────────────────


def main():
    try:
        workouts_raw, sets_raw = load_data()
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        st.info("Ensure `.env` contains a valid `DATABASE_URL`. Run `python main.py` first.")
        return

    if workouts_raw.empty:
        st.warning("No data found. Run the ETL pipeline first: `python main.py`")
        return

    workouts, sets, selected_ex = render_sidebar(workouts_raw, sets_raw)

    # Header
    st.markdown(
        '<div class="dash-header">Hevy<span> Flow</span></div>'
        '<div class="dash-subtitle">Extract → Transform → Load → Visualize &nbsp;·&nbsp; '
        "Your workout data, engineered</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    if workouts.empty:
        st.warning("No data matches the selected filters.")
        return

    render_kpis(workouts, sets)
    st.divider()

    render_frequency(workouts)

    c1, c2 = st.columns(2)
    with c1:
        render_day_of_week(workouts)
    with c2:
        render_rpe(sets)

    st.divider()
    render_category_split(workouts, sets)

    st.divider()
    render_volume_timeline(sets)

    st.divider()
    render_strength(sets, selected_ex)

    st.divider()
    c3, c4 = st.columns(2)
    with c3:
        render_top_exercises(sets)
    with c4:
        render_duration(workouts)

    # Footer
    st.markdown(
        '<div class="dash-footer">'
        "HEVY FLOW · Python · pandas · psycopg2 · Supabase (PostgreSQL) · Streamlit · Plotly"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
