"""
Hevy-Flow Dashboard — Interactive Workout Analytics

A Streamlit dashboard that reads cleaned workout data from Supabase
(PostgreSQL) and presents interactive charts for tracking fitness progress.

Run with:  streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import psycopg2
from config import DATABASE_URL
from etl.extract import extract_workouts
from etl.transform import transform_workouts
from etl.load import load_to_supabase

# ── Page Config ──────────────────────────────────────

st.set_page_config(
    page_title="Hevy Flow | Workout Analytics",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme & Colors ───────────────────────────────────
# Inspired by Hevy app's dark UI: deep blacks, electric teal accents

TEAL = "#2DD4BF"
TEAL_DIM = "rgba(45, 212, 191, 0.15)"
TEAL_GLOW = "rgba(45, 212, 191, 0.4)"
CYAN = "#22D3EE"
VIOLET = "#A78BFA"
ROSE = "#FB7185"
AMBER = "#FBBF24"
EMERALD = "#34D399"
SLATE_50 = "#F8FAFC"
SLATE_300 = "#CBD5E1"
SLATE_400 = "#94A3B8"
SLATE_900 = "#0F172A"
SLATE_950 = "#020617"

CATEGORY_COLORS = {
    "Push": "#FB7185",
    "Pull": "#22D3EE",
    "Legs": "#34D399",
    "Upper": "#A78BFA",
    "Lower": "#FBBF24",
    "Full Body": "#FB923C",
}

CATEGORY_ORDER = ["Push", "Pull", "Legs", "Upper", "Lower", "Full Body"]

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
        background: linear-gradient(180deg, {SLATE_950} 0%, #0B1120 50%, {SLATE_950} 100%);
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
        background: linear-gradient(180deg, #080E1A 0%, #0D1525 100%);
        border-right: 1px solid rgba(45, 212, 191, 0.08);
    }}

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
        color: {SLATE_400};
    }}

    /* ── KPI Cards ──────────────────────── */
    div[data-testid="stMetric"] {{
        background: linear-gradient(145deg, rgba(15, 23, 42, 0.8) 0%, rgba(13, 21, 37, 0.9) 100%);
        border: 1px solid rgba(45, 212, 191, 0.12);
        border-radius: 16px;
        padding: 20px 24px;
        backdrop-filter: blur(12px);
        box-shadow:
            0 0 0 1px rgba(45, 212, 191, 0.04),
            0 8px 32px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.03);
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }}

    div[data-testid="stMetric"]:hover {{
        border-color: rgba(45, 212, 191, 0.3);
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
        background: rgba(45, 212, 191, 0.06);
        border: 1px solid rgba(45, 212, 191, 0.1);
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
        border-color: rgba(45, 212, 191, 0.06) !important;
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
        color: rgba(148, 163, 184, 0.4);
        font-size: 0.72rem;
        letter-spacing: 0.3px;
        padding: 20px 0 10px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Plotly shared layout ─────────────────────────────

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=SLATE_400, size=11),
    margin=dict(l=48, r=16, t=44, b=44),
    xaxis=dict(
        gridcolor="rgba(45, 212, 191, 0.05)",
        zeroline=False,
        tickfont=dict(size=10),
    ),
    yaxis=dict(
        gridcolor="rgba(45, 212, 191, 0.05)",
        zeroline=False,
        tickfont=dict(size=10),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=10, color=SLATE_400),
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
    ),
    hoverlabel=dict(
        bgcolor="#111827",
        bordercolor="rgba(45,212,191,0.3)",
        font_size=12,
        font_family="Inter",
        font_color=SLATE_50,
    ),
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

        # ── CSV Upload ───────────────────────────
        st.markdown('<div class="sidebar-section">📤 Upload Workout Log</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Upload Hevy CSV",
            type=["csv"],
            label_visibility="collapsed",
            help="Export your workouts from the Hevy app and upload the CSV here.",
        )
        if uploaded is not None:
            if st.button("⚡ Run Pipeline", use_container_width=True, type="primary"):
                with st.spinner("Running Extract → Transform → Load ..."):
                    try:
                        stats = _run_incremental_pipeline(uploaded)
                        if stats["new_workouts"] > 0:
                            st.success(
                                f"✅ Loaded **{stats['new_workouts']}** new sessions "
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
        st.markdown('<div class="sidebar-section">📅 Date Range</div>', unsafe_allow_html=True)
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
            workouts = workouts[
                (workouts["date"].dt.date >= s) & (workouts["date"].dt.date <= e)
            ]
            sets = sets[(sets["date"].dt.date >= s) & (sets["date"].dt.date <= e)]

        st.divider()

        # Category
        st.markdown('<div class="sidebar-section">🏷️ Category</div>', unsafe_allow_html=True)
        cats = sorted(workouts["workout_category"].unique())
        selected_cats = st.multiselect("cats", cats, default=cats, label_visibility="collapsed")
        workouts = workouts[workouts["workout_category"].isin(selected_cats)]
        sets = sets[sets["workout_category"].isin(selected_cats)]

        st.divider()

        # Exercise
        st.markdown('<div class="sidebar-section">💪 Exercise</div>', unsafe_allow_html=True)
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
    section("📈 Workout Frequency")

    weekly = (
        workouts.set_index("date")
        .resample("W")["workout_id"]
        .count()
        .reset_index()
        .rename(columns={"workout_id": "count"})
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weekly["date"], y=weekly["count"],
        mode="lines+markers",
        line=dict(color=TEAL, width=2, shape="spline"),
        marker=dict(size=4, color=TEAL, line=dict(width=0)),
        fill="tozeroy",
        fillcolor=TEAL_DIM,
        hovertemplate="Week of %{x|%b %d, %Y}<br><b>%{y} workouts</b><extra></extra>",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=310, yaxis_title="Workouts / Week")
    st.plotly_chart(fig, use_container_width=True)


def render_category_split(workouts, sets):
    """Category donut + volume breakdown."""
    section("🏷️ Workout Distribution")
    col1, col2 = st.columns(2)

    with col1:
        cat_counts = workouts["workout_category"].value_counts().reset_index()
        cat_counts.columns = ["category", "count"]
        colors = [CATEGORY_COLORS.get(c, SLATE_400) for c in cat_counts["category"]]

        fig = go.Figure(go.Pie(
            labels=cat_counts["category"], values=cat_counts["count"],
            hole=0.6,
            marker=dict(colors=colors, line=dict(color=SLATE_950, width=2)),
            textinfo="label+percent",
            textfont=dict(size=11, color=SLATE_300),
            hovertemplate="%{label}<br><b>%{value} sessions</b> (%{percent})<extra></extra>",
        ))
        fig.update_layout(
            **PLOTLY_LAYOUT, height=340, showlegend=False,
            title=dict(text="Sessions by Category", font=dict(size=13, color=SLATE_300)),
            annotations=[dict(
                text=f"<b>{len(workouts)}</b><br>total",
                x=0.5, y=0.5, font=dict(size=16, color=TEAL), showarrow=False,
            )],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        vol = sets.copy()
        vol["volume"] = vol["weight_kg"] * vol["reps"]
        by_cat = vol.groupby("workout_category")["volume"].sum().sort_values(ascending=True).reset_index()
        colors = [CATEGORY_COLORS.get(c, SLATE_400) for c in by_cat["workout_category"]]

        fig = go.Figure(go.Bar(
            x=by_cat["volume"], y=by_cat["workout_category"],
            orientation="h",
            marker=dict(color=colors, cornerradius=5,
                        line=dict(width=0)),
            hovertemplate="%{y}<br><b>%{x:,.0f} kg</b><extra></extra>",
        ))
        fig.update_layout(
            **PLOTLY_LAYOUT, height=340, xaxis_title="Volume (kg)",
            title=dict(text="Total Volume by Category", font=dict(size=13, color=SLATE_300)),
        )
        st.plotly_chart(fig, use_container_width=True)


def render_volume_timeline(sets):
    """Stacked volume per session over time."""
    section("🔥 Volume Over Time")

    vol = sets.copy()
    vol["volume"] = vol["weight_kg"] * vol["reps"]
    session_vol = vol.groupby(["date", "workout_category"])["volume"].sum().reset_index().sort_values("date")

    fig = go.Figure()
    for cat in CATEGORY_ORDER:
        d = session_vol[session_vol["workout_category"] == cat]
        if d.empty:
            continue
        fig.add_trace(go.Bar(
            x=d["date"], y=d["volume"], name=cat,
            marker=dict(color=CATEGORY_COLORS.get(cat, SLATE_400), cornerradius=3, line=dict(width=0)),
            hovertemplate="%{x|%b %d}<br><b>%{y:,.0f} kg</b><extra></extra>",
        ))

    fig.update_layout(**PLOTLY_LAYOUT, barmode="stack", height=360, yaxis_title="Volume (kg)")
    st.plotly_chart(fig, use_container_width=True)


def render_strength(sets, exercise):
    """Strength progression chart."""
    section("📊 Strength Progression")

    if exercise == "All Exercises":
        top = (
            sets.assign(v=sets["weight_kg"] * sets["reps"])
            .groupby("exercise_title")["v"].sum()
            .nlargest(5).index.tolist()
        )
        data = sets[sets["exercise_title"].isin(top)]
        subtitle = "Top 5 exercises by volume"
    else:
        data = sets[sets["exercise_title"] == exercise]
        top = [exercise]
        subtitle = exercise

    if data.empty:
        st.info("No data for the selected exercise.")
        return

    prog = data.groupby(["date", "exercise_title"])["weight_kg"].max().reset_index().sort_values("date")
    palette = [TEAL, CYAN, VIOLET, ROSE, AMBER]

    fig = go.Figure()
    for i, ex in enumerate(top):
        d = prog[prog["exercise_title"] == ex]
        c = palette[i % len(palette)]
        fig.add_trace(go.Scatter(
            x=d["date"], y=d["weight_kg"],
            mode="lines+markers", name=ex,
            line=dict(color=c, width=2, shape="spline"),
            marker=dict(size=5, color=c),
            hovertemplate="%{x|%b %d, %Y}<br><b>%{y:.1f} kg</b><extra></extra>",
        ))
    st.caption(subtitle)

    fig.update_layout(
        **PLOTLY_LAYOUT, height=400, yaxis_title="Max Weight (kg)",
    )
    fig.update_layout(
        margin=dict(l=48, r=16, t=60, b=44),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=10, color=SLATE_400),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_day_of_week(workouts):
    """Day-of-week bar chart."""
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_short = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    counts = workouts["day_of_week"].value_counts().reindex(day_order, fill_value=0)
    max_val = counts.max()

    colors = [TEAL if v == max_val else "rgba(45, 212, 191, 0.35)" for v in counts.values]

    fig = go.Figure(go.Bar(
        x=day_short, y=counts.values,
        marker=dict(color=colors, cornerradius=6, line=dict(width=0)),
        hovertemplate="%{x}<br><b>%{y} workouts</b><extra></extra>",
        text=counts.values,
        textposition="outside",
        textfont=dict(color=SLATE_400, size=10),
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT, height=310,
        title=dict(text="Training Days", font=dict(size=13, color=SLATE_300)),
        yaxis_title="Count",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_rpe(sets):
    """RPE trend over time."""
    rpe_data = sets.dropna(subset=["rpe"])
    if rpe_data.empty:
        st.info("No RPE data available.")
        return

    avg = rpe_data.groupby("date")["rpe"].mean().reset_index().sort_values("date")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=avg["date"], y=avg["rpe"],
        mode="lines+markers",
        line=dict(color=AMBER, width=2, shape="spline"),
        marker=dict(size=4, color=AMBER),
        fill="tozeroy",
        fillcolor="rgba(251, 191, 36, 0.06)",
        hovertemplate="%{x|%b %d, %Y}<br><b>RPE %{y:.1f}</b><extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT, height=310,
        title=dict(text="Avg RPE per Session", font=dict(size=13, color=SLATE_300)),
        yaxis_title="RPE",
    )
    fig.update_yaxes(range=[5, 10])
    st.plotly_chart(fig, use_container_width=True)


def render_top_exercises(sets):
    """Top 10 exercises horizontal bar."""
    top = (
        sets.groupby("exercise_title")
        .agg(total_sets=("id", "count"), avg_weight=("weight_kg", "mean"))
        .nlargest(10, "total_sets")
        .sort_values("total_sets", ascending=True)
        .reset_index()
    )

    fig = go.Figure(go.Bar(
        x=top["total_sets"], y=top["exercise_title"],
        orientation="h",
        marker=dict(
            color=top["total_sets"],
            colorscale=[[0, "rgba(45,212,191,0.25)"], [1, TEAL]],
            cornerradius=5, line=dict(width=0),
        ),
        text=top["total_sets"],
        textposition="outside",
        textfont=dict(color=SLATE_400, size=10),
        hovertemplate="%{y}<br><b>%{x} sets</b><br>Avg: %{customdata:.1f} kg<extra></extra>",
        customdata=top["avg_weight"],
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT, height=400, xaxis_title="Total Sets",
        title=dict(text="Top 10 Exercises", font=dict(size=13, color=SLATE_300)),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_duration(workouts):
    """Session duration scatter + rolling average."""
    data = workouts[["date", "duration_minutes", "workout_category"]].sort_values("date")
    colors = [CATEGORY_COLORS.get(c, SLATE_400) for c in data["workout_category"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["date"], y=data["duration_minutes"],
        mode="markers",
        marker=dict(size=7, color=colors, opacity=0.6,
                    line=dict(width=0.5, color="rgba(255,255,255,0.1)")),
        hovertemplate="%{x|%b %d, %Y}<br><b>%{y:.0f} min</b><extra></extra>",
        showlegend=False,
    ))

    if len(data) >= 5:
        roll = data.set_index("date")["duration_minutes"].rolling("14D").mean().reset_index()
        fig.add_trace(go.Scatter(
            x=roll["date"], y=roll["duration_minutes"],
            mode="lines", name="14-day avg",
            line=dict(color=TEAL, width=2, dash="dot"),
            hovertemplate="%{x|%b %d}<br><b>Avg: %{y:.0f} min</b><extra></extra>",
        ))

    fig.update_layout(
        **PLOTLY_LAYOUT, height=400, yaxis_title="Minutes",
        title=dict(text="Session Duration", font=dict(size=13, color=SLATE_300)),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Main ─────────────────────────────────────────────


def main():
    try:
        workouts_raw, sets_raw = load_data()
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        st.info("Ensure `.env` contains a valid `DATABASE_URL`. Run `python main.py` first.")
        return

    if workouts_raw.empty:
        st.warning("No data found. Run the ETL pipeline first: `python main.py`")
        return

    workouts, sets, selected_ex = render_sidebar(workouts_raw, sets_raw)

    # Header
    st.markdown(
        '<div class="dash-header">🏋️ Hevy<span> Flow</span></div>'
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
