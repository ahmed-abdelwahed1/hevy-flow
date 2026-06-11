"""
Hevy-Flow Dashboard — Interactive Workout Analytics

A Streamlit dashboard that reads cleaned workout data from Supabase
(PostgreSQL) and presents interactive charts for tracking fitness progress.

Run with:  streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from config import DATABASE_URL

# ── Page Config ──────────────────────────────────────

st.set_page_config(
    page_title="Hevy-Flow | Workout Analytics",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────

st.markdown(
    """
    <style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }

    /* KPI metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    }

    div[data-testid="stMetric"] label {
        color: #a5b4fc !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #e0e7ff !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f23 0%, #1a1a3e 100%);
    }

    section[data-testid="stSidebar"] .stMarkdown h1 {
        color: #818cf8;
    }

    /* Section headers */
    .section-header {
        color: #818cf8;
        font-size: 1.4rem;
        font-weight: 700;
        margin-top: 2rem;
        margin-bottom: 0.5rem;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid rgba(129, 140, 248, 0.3);
    }

    /* Divider */
    hr {
        border-color: rgba(129, 140, 248, 0.15) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Color palette ────────────────────────────────────

COLORS = {
    "primary": "#818cf8",
    "secondary": "#6366f1",
    "accent": "#a78bfa",
    "success": "#34d399",
    "warning": "#fbbf24",
    "danger": "#f87171",
    "text": "#e0e7ff",
}

CATEGORY_COLORS = {
    "Push": "#f472b6",
    "Pull": "#60a5fa",
    "Legs": "#34d399",
    "Upper": "#a78bfa",
    "Lower": "#fbbf24",
    "Full Body": "#fb923c",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#c7d2fe"),
    margin=dict(l=40, r=20, t=40, b=40),
    xaxis=dict(gridcolor="rgba(99,102,241,0.1)", zeroline=False),
    yaxis=dict(gridcolor="rgba(99,102,241,0.1)", zeroline=False),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
    ),
    hoverlabel=dict(
        bgcolor="#1e1b4b",
        font_size=12,
        font_family="Inter",
    ),
)


# ── Data Loading ─────────────────────────────────────


@st.cache_data(ttl=300)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load workouts and workout_sets from Supabase PostgreSQL.

    Results are cached for 5 minutes to avoid repeated DB calls.
    """
    conn = psycopg2.connect(DATABASE_URL)

    workouts = pd.read_sql("SELECT * FROM workouts ORDER BY start_time DESC", conn)
    sets = pd.read_sql(
        """
        SELECT ws.*, w.workout_category, w.duration_minutes,
               w.day_of_week, w.date, w.month, w.year
        FROM workout_sets ws
        JOIN workouts w ON ws.workout_id = w.workout_id
        ORDER BY w.start_time DESC, ws.set_index
        """,
        conn,
    )

    conn.close()

    workouts["start_time"] = pd.to_datetime(workouts["start_time"])
    workouts["end_time"] = pd.to_datetime(workouts["end_time"])
    workouts["date"] = pd.to_datetime(workouts["date"])

    sets["date"] = pd.to_datetime(sets["date"])

    return workouts, sets


# ── Sidebar Filters ──────────────────────────────────


def render_sidebar(
    workouts: pd.DataFrame, sets: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Render sidebar filters and return filtered DataFrames."""
    with st.sidebar:
        st.markdown("# 🏋️ Hevy-Flow")
        st.caption("Workout Analytics Dashboard")
        st.divider()

        # Date range filter
        st.markdown("### 📅 Date Range")
        min_date = workouts["date"].min().date()
        max_date = workouts["date"].max().date()
        date_range = st.date_input(
            "Select range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            label_visibility="collapsed",
        )

        if len(date_range) == 2:
            start_date, end_date = date_range
            workouts = workouts[
                (workouts["date"].dt.date >= start_date)
                & (workouts["date"].dt.date <= end_date)
            ]
            sets = sets[
                (sets["date"].dt.date >= start_date)
                & (sets["date"].dt.date <= end_date)
            ]

        st.divider()

        # Category filter
        st.markdown("### 🏷️ Category")
        categories = sorted(workouts["workout_category"].unique())
        selected_cats = st.multiselect(
            "Filter categories",
            categories,
            default=categories,
            label_visibility="collapsed",
        )
        workouts = workouts[workouts["workout_category"].isin(selected_cats)]
        sets = sets[sets["workout_category"].isin(selected_cats)]

        st.divider()

        # Exercise filter
        st.markdown("### 💪 Exercise")
        exercises = sorted(sets["exercise_title"].unique())
        selected_exercise = st.selectbox(
            "Select exercise for progression",
            ["All Exercises"] + exercises,
            label_visibility="collapsed",
        )

        st.divider()
        st.caption(f"Showing {len(workouts)} workouts · {len(sets)} sets")

    return workouts, sets, selected_exercise


# ── Chart Builders ───────────────────────────────────


def render_kpis(workouts: pd.DataFrame, sets: pd.DataFrame) -> None:
    """Render the top KPI metrics row."""
    total_workouts = len(workouts)
    total_sets = len(sets)
    unique_exercises = sets["exercise_title"].nunique()
    avg_duration = workouts["duration_minutes"].mean()
    total_volume = (sets["weight_kg"] * sets["reps"]).sum()
    avg_rpe = sets["rpe"].dropna().mean()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Workouts", f"{total_workouts}")
    c2.metric("Total Sets", f"{total_sets:,}")
    c3.metric("Exercises", f"{unique_exercises}")
    c4.metric("Avg Duration", f"{avg_duration:.0f} min")
    c5.metric("Total Volume", f"{total_volume:,.0f} kg")
    c6.metric("Avg RPE", f"{avg_rpe:.1f}" if not pd.isna(avg_rpe) else "N/A")


def render_frequency_chart(workouts: pd.DataFrame) -> None:
    """Workout frequency over time (weekly rolling)."""
    st.markdown('<p class="section-header">📈 Workout Frequency</p>', unsafe_allow_html=True)

    weekly = (
        workouts.set_index("date")
        .resample("W")["workout_id"]
        .count()
        .reset_index()
        .rename(columns={"workout_id": "count"})
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=weekly["date"],
            y=weekly["count"],
            mode="lines+markers",
            line=dict(color=COLORS["primary"], width=2.5),
            marker=dict(size=5, color=COLORS["primary"]),
            fill="tozeroy",
            fillcolor="rgba(129, 140, 248, 0.1)",
            name="Workouts / Week",
            hovertemplate="Week of %{x|%b %d, %Y}<br>Workouts: %{y}<extra></extra>",
        )
    )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        yaxis_title="Workouts per Week",
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_category_charts(workouts: pd.DataFrame, sets: pd.DataFrame) -> None:
    """Category distribution — donut chart + volume by category."""
    st.markdown(
        '<p class="section-header">🏷️ Workout Distribution</p>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        cat_counts = workouts["workout_category"].value_counts().reset_index()
        cat_counts.columns = ["category", "count"]
        colors = [CATEGORY_COLORS.get(c, COLORS["accent"]) for c in cat_counts["category"]]

        fig = go.Figure(
            go.Pie(
                labels=cat_counts["category"],
                values=cat_counts["count"],
                hole=0.55,
                marker=dict(colors=colors),
                textinfo="label+percent",
                textfont=dict(size=12),
                hovertemplate="%{label}<br>Workouts: %{value}<br>%{percent}<extra></extra>",
            )
        )
        fig.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Sessions by Category", font=dict(size=14)),
            height=350,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        sets_vol = sets.copy()
        sets_vol["volume"] = sets_vol["weight_kg"] * sets_vol["reps"]
        vol_by_cat = (
            sets_vol.groupby("workout_category")["volume"]
            .sum()
            .sort_values(ascending=True)
            .reset_index()
        )
        colors = [CATEGORY_COLORS.get(c, COLORS["accent"]) for c in vol_by_cat["workout_category"]]

        fig = go.Figure(
            go.Bar(
                x=vol_by_cat["volume"],
                y=vol_by_cat["workout_category"],
                orientation="h",
                marker=dict(color=colors, cornerradius=6),
                hovertemplate="%{y}<br>Volume: %{x:,.0f} kg<extra></extra>",
            )
        )
        fig.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Total Volume by Category (kg)", font=dict(size=14)),
            height=350,
            xaxis_title="Volume (kg)",
        )
        st.plotly_chart(fig, use_container_width=True)


def render_strength_progression(sets: pd.DataFrame, exercise: str) -> None:
    """Strength progression — max weight over time for a given exercise."""
    st.markdown(
        '<p class="section-header">📊 Strength Progression</p>',
        unsafe_allow_html=True,
    )

    if exercise == "All Exercises":
        # Show top 5 exercises by total volume
        top_exercises = (
            sets.assign(volume=sets["weight_kg"] * sets["reps"])
            .groupby("exercise_title")["volume"]
            .sum()
            .nlargest(5)
            .index.tolist()
        )
        filtered = sets[sets["exercise_title"].isin(top_exercises)]
        subtitle = "Top 5 exercises by volume"
    else:
        filtered = sets[sets["exercise_title"] == exercise]
        top_exercises = [exercise]
        subtitle = exercise

    if filtered.empty:
        st.info("No data available for the selected exercise and filters.")
        return

    progression = (
        filtered.groupby(["date", "exercise_title"])["weight_kg"]
        .max()
        .reset_index()
        .sort_values("date")
    )

    fig = go.Figure()
    for ex in top_exercises:
        ex_data = progression[progression["exercise_title"] == ex]
        fig.add_trace(
            go.Scatter(
                x=ex_data["date"],
                y=ex_data["weight_kg"],
                mode="lines+markers",
                name=ex,
                marker=dict(size=5),
                line=dict(width=2.5),
                hovertemplate="%{x|%b %d, %Y}<br>Max Weight: %{y:.1f} kg<extra></extra>",
            )
        )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=subtitle, font=dict(size=14)),
        yaxis_title="Max Weight (kg)",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_volume_over_time(sets: pd.DataFrame) -> None:
    """Total training volume per session over time."""
    st.markdown(
        '<p class="section-header">🔥 Volume Over Time</p>',
        unsafe_allow_html=True,
    )

    sets_vol = sets.copy()
    sets_vol["volume"] = sets_vol["weight_kg"] * sets_vol["reps"]

    session_vol = (
        sets_vol.groupby(["date", "workout_category"])["volume"]
        .sum()
        .reset_index()
        .sort_values("date")
    )

    fig = go.Figure()
    for cat in sorted(session_vol["workout_category"].unique()):
        cat_data = session_vol[session_vol["workout_category"] == cat]
        fig.add_trace(
            go.Bar(
                x=cat_data["date"],
                y=cat_data["volume"],
                name=cat,
                marker=dict(
                    color=CATEGORY_COLORS.get(cat, COLORS["accent"]),
                    cornerradius=4,
                ),
                hovertemplate="%{x|%b %d, %Y}<br>Volume: %{y:,.0f} kg<extra></extra>",
            )
        )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        barmode="stack",
        yaxis_title="Volume (kg)",
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_day_of_week(workouts: pd.DataFrame) -> None:
    """Day-of-week workout distribution."""
    day_order = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    ]
    day_counts = workouts["day_of_week"].value_counts().reindex(day_order, fill_value=0)

    fig = go.Figure(
        go.Bar(
            x=day_counts.index,
            y=day_counts.values,
            marker=dict(
                color=[COLORS["primary"] if v == day_counts.max() else COLORS["secondary"]
                       for v in day_counts.values],
                cornerradius=8,
            ),
            hovertemplate="%{x}<br>Workouts: %{y}<extra></extra>",
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Workouts by Day of Week", font=dict(size=14)),
        yaxis_title="Count",
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_rpe_analysis(sets: pd.DataFrame) -> None:
    """RPE trends over time."""
    rpe_data = sets.dropna(subset=["rpe"])
    if rpe_data.empty:
        st.info("No RPE data available for the selected filters.")
        return

    avg_rpe = (
        rpe_data.groupby("date")["rpe"]
        .mean()
        .reset_index()
        .sort_values("date")
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=avg_rpe["date"],
            y=avg_rpe["rpe"],
            mode="lines+markers",
            line=dict(color=COLORS["warning"], width=2.5),
            marker=dict(size=5, color=COLORS["warning"]),
            fill="tozeroy",
            fillcolor="rgba(251, 191, 36, 0.08)",
            hovertemplate="%{x|%b %d, %Y}<br>Avg RPE: %{y:.1f}<extra></extra>",
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Average RPE per Session", font=dict(size=14)),
        yaxis_title="RPE",
        height=320,
    )
    fig.update_yaxes(range=[5, 10])
    st.plotly_chart(fig, use_container_width=True)


def render_top_exercises(sets: pd.DataFrame) -> None:
    """Top 10 most performed exercises."""
    top = (
        sets.groupby("exercise_title")
        .agg(total_sets=("id", "count"), avg_weight=("weight_kg", "mean"))
        .nlargest(10, "total_sets")
        .sort_values("total_sets", ascending=True)
        .reset_index()
    )

    fig = go.Figure(
        go.Bar(
            x=top["total_sets"],
            y=top["exercise_title"],
            orientation="h",
            marker=dict(
                color=top["total_sets"],
                colorscale=[[0, "#4338ca"], [0.5, "#6366f1"], [1, "#a78bfa"]],
                cornerradius=6,
            ),
            text=top["total_sets"],
            textposition="outside",
            textfont=dict(color="#c7d2fe", size=11),
            hovertemplate="%{y}<br>Total Sets: %{x}<br>Avg Weight: %{customdata:.1f} kg<extra></extra>",
            customdata=top["avg_weight"],
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Top 10 Exercises by Total Sets", font=dict(size=14)),
        xaxis_title="Total Sets",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_duration_trend(workouts: pd.DataFrame) -> None:
    """Workout duration trend over time."""
    duration_data = workouts[["date", "duration_minutes", "workout_category"]].sort_values("date")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=duration_data["date"],
            y=duration_data["duration_minutes"],
            mode="markers",
            marker=dict(
                size=8,
                color=[CATEGORY_COLORS.get(c, COLORS["accent"])
                       for c in duration_data["workout_category"]],
                opacity=0.7,
                line=dict(width=1, color="rgba(255,255,255,0.2)"),
            ),
            hovertemplate="%{x|%b %d, %Y}<br>Duration: %{y:.0f} min<extra></extra>",
            showlegend=False,
        )
    )

    # Add rolling average
    if len(duration_data) >= 5:
        rolling = duration_data.set_index("date")["duration_minutes"].rolling("14D").mean().reset_index()
        fig.add_trace(
            go.Scatter(
                x=rolling["date"],
                y=rolling["duration_minutes"],
                mode="lines",
                line=dict(color=COLORS["accent"], width=2.5, dash="dot"),
                name="14-day avg",
                hovertemplate="%{x|%b %d, %Y}<br>14-day Avg: %{y:.0f} min<extra></extra>",
            )
        )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Session Duration Over Time", font=dict(size=14)),
        yaxis_title="Minutes",
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Main App ─────────────────────────────────────────


def main():
    """Main dashboard layout."""
    try:
        workouts_raw, sets_raw = load_data()
    except Exception as e:
        st.error(f"❌ Failed to connect to database: {e}")
        st.info("Make sure your `.env` file contains a valid `DATABASE_URL`.")
        return

    if workouts_raw.empty:
        st.warning("No workout data found. Run the ETL pipeline first: `python main.py`")
        return

    workouts, sets, selected_exercise = render_sidebar(workouts_raw, sets_raw)

    # Header
    st.markdown("## 🏋️ Hevy-Flow — Workout Analytics")
    st.caption("End-to-end data engineering pipeline · Extracted → Transformed → Loaded → Visualized")
    st.divider()

    if workouts.empty:
        st.warning("No data matches the selected filters.")
        return

    # KPIs
    render_kpis(workouts, sets)
    st.divider()

    # Frequency + Categories
    render_frequency_chart(workouts)

    col1, col2 = st.columns(2)
    with col1:
        render_day_of_week(workouts)
    with col2:
        render_rpe_analysis(sets)

    st.divider()
    render_category_charts(workouts, sets)

    st.divider()
    render_volume_over_time(sets)

    st.divider()
    render_strength_progression(sets, selected_exercise)

    st.divider()
    col3, col4 = st.columns(2)
    with col3:
        render_top_exercises(sets)
    with col4:
        render_duration_trend(workouts)

    # Footer
    st.divider()
    st.caption(
        "Built with Streamlit · Data from Hevy App · "
        "Pipeline: Python + pandas + psycopg2 + Supabase (PostgreSQL)"
    )


if __name__ == "__main__":
    main()
