"""
Hevy-Flow Charts — Shared constants and Plotly figure builders

This module contains the colour palette, layout config, and every
``build_*`` function that constructs a Plotly ``Figure``.  Both the
Streamlit dashboard and the PDF report generator import from here,
avoiding circular-import issues.
"""

import plotly.graph_objects as go

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
BG_GRADIENT_MID = "#0B1120"
SIDEBAR_GRAD_START = "#080E1A"
SIDEBAR_GRAD_END = "#0D1525"
METRIC_BG_START = "rgba(15, 23, 42, 0.8)"
METRIC_BG_END = "rgba(13, 21, 37, 0.9)"
METRIC_BORDER = "rgba(45, 212, 191, 0.12)"
GRID_COLOR = "rgba(45, 212, 191, 0.05)"
METRIC_SHADOW = "0 8px 32px rgba(0, 0, 0, 0.3)"

CATEGORY_COLORS = {
    "Push": ROSE,
    "Pull": CYAN,
    "Legs": EMERALD,
    "Upper": VIOLET,
    "Lower": AMBER,
    "Full Body": "#FB923C",
}

CATEGORY_ORDER = ["Push", "Pull", "Legs", "Upper", "Lower", "Full Body"]

# ── Plotly shared layout ─────────────────────────────

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=SLATE_400, size=11),
    margin=dict(l=48, r=16, t=44, b=44),
    xaxis=dict(
        gridcolor=GRID_COLOR,
        zeroline=False,
        tickfont=dict(size=10),
    ),
    yaxis=dict(
        gridcolor=GRID_COLOR,
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


# ── Build Functions ──────────────────────────────────


def build_frequency(workouts):
    """Build weekly workout frequency figure."""
    weekly = (
        workouts.set_index("date")
        .resample("W-FRI")["workout_id"]
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
            line=dict(color=TEAL, width=2, shape="spline"),
            marker=dict(size=4, color=TEAL, line=dict(width=0)),
            fill="tozeroy",
            fillcolor=TEAL_DIM,
            hovertemplate="Week of %{x|%b %d, %Y}<br><b>%{y} workouts</b><extra></extra>",
        )
    )
    fig.update_layout(**PLOTLY_LAYOUT, height=310, yaxis_title="Workouts / Week")
    return fig


def build_category_donut(workouts):
    """Build sessions-by-category donut chart."""
    cat_counts = workouts["workout_category"].value_counts().reset_index()
    cat_counts.columns = ["category", "count"]
    colors = [CATEGORY_COLORS.get(c, SLATE_400) for c in cat_counts["category"]]

    fig = go.Figure(
        go.Pie(
            labels=cat_counts["category"],
            values=cat_counts["count"],
            hole=0.6,
            marker=dict(colors=colors, line=dict(color=SLATE_950, width=2)),
            textinfo="label+percent",
            textfont=dict(size=11, color=SLATE_300),
            hovertemplate="%{label}<br><b>%{value} sessions</b> (%{percent})<extra></extra>",
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=340,
        showlegend=False,
        title=dict(text="Sessions by Category", font=dict(size=13, color=SLATE_300)),
        annotations=[
            dict(
                text=f"<b>{len(workouts)}</b><br>total",
                x=0.5,
                y=0.5,
                font=dict(size=16, color=TEAL),
                showarrow=False,
            )
        ],
    )
    return fig


def build_category_volume(sets):
    """Build total-volume-by-category horizontal bar chart."""
    vol = sets.copy()
    vol["volume"] = vol["weight_kg"] * vol["reps"]
    by_cat = (
        vol.groupby("workout_category")["volume"]
        .sum()
        .sort_values(ascending=True)
        .reset_index()
    )
    colors = [CATEGORY_COLORS.get(c, SLATE_400) for c in by_cat["workout_category"]]

    fig = go.Figure(
        go.Bar(
            x=by_cat["volume"],
            y=by_cat["workout_category"],
            orientation="h",
            marker=dict(color=colors, cornerradius=5, line=dict(width=0)),
            hovertemplate="%{y}<br><b>%{x:,.0f} kg</b><extra></extra>",
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=340,
        xaxis_title="Volume (kg)",
        title=dict(text="Total Volume by Category", font=dict(size=13, color=SLATE_300)),
    )
    return fig


def build_volume_timeline(sets):
    """Build stacked volume per session over time figure."""
    vol = sets.copy()
    vol["volume"] = vol["weight_kg"] * vol["reps"]
    session_vol = (
        vol.groupby(["date", "workout_category"])["volume"].sum().reset_index().sort_values("date")
    )

    fig = go.Figure()
    for cat in CATEGORY_ORDER:
        d = session_vol[session_vol["workout_category"] == cat]
        if d.empty:
            continue
        fig.add_trace(
            go.Bar(
                x=d["date"],
                y=d["volume"],
                name=cat,
                marker=dict(
                    color=CATEGORY_COLORS.get(cat, SLATE_400), cornerradius=3, line=dict(width=0)
                ),
                hovertemplate="%{x|%b %d}<br><b>%{y:,.0f} kg</b><extra></extra>",
            )
        )

    fig.update_layout(**PLOTLY_LAYOUT, barmode="stack", height=360, yaxis_title="Volume (kg)")
    return fig


def build_strength(sets, exercise):
    """Build strength progression figure. Returns (fig, subtitle) or (None, None)."""
    if exercise == "All Exercises":
        top = (
            sets.assign(v=sets["weight_kg"] * sets["reps"])
            .groupby("exercise_title")["v"]
            .sum()
            .nlargest(5)
            .index.tolist()
        )
        data = sets[sets["exercise_title"].isin(top)]
        subtitle = "Top 5 exercises by volume"
    else:
        data = sets[sets["exercise_title"] == exercise]
        top = [exercise]
        subtitle = exercise

    if data.empty:
        return None, None

    prog = (
        data.groupby(["date", "exercise_title"])["weight_kg"]
        .max()
        .reset_index()
        .sort_values("date")
    )
    palette = [TEAL, CYAN, VIOLET, ROSE, AMBER]

    fig = go.Figure()
    for i, ex in enumerate(top):
        d = prog[prog["exercise_title"] == ex]
        c = palette[i % len(palette)]
        fig.add_trace(
            go.Scatter(
                x=d["date"],
                y=d["weight_kg"],
                mode="lines+markers",
                name=ex,
                line=dict(color=c, width=2, shape="spline"),
                marker=dict(size=5, color=c),
                hovertemplate="%{x|%b %d, %Y}<br><b>%{y:.1f} kg</b><extra></extra>",
            )
        )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=400,
        yaxis_title="Max Weight (kg)",
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
    return fig, subtitle


def build_day_of_week(workouts):
    """Build day-of-week bar chart figure."""
    day_order = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    day_short = ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"]
    counts = workouts["day_of_week"].value_counts().reindex(day_order, fill_value=0)
    max_val = counts.max()

    colors = [TEAL if v == max_val else "rgba(45, 212, 191, 0.35)" for v in counts.values]

    fig = go.Figure(
        go.Bar(
            x=day_short,
            y=counts.values,
            marker=dict(color=colors, cornerradius=6, line=dict(width=0)),
            hovertemplate="%{x}<br><b>%{y} workouts</b><extra></extra>",
            text=counts.values,
            textposition="outside",
            textfont=dict(color=SLATE_400, size=10),
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=310,
        title=dict(text="Training Days", font=dict(size=13, color=SLATE_300)),
        yaxis_title="Count",
    )
    return fig


def build_rpe(sets):
    """Build RPE trend figure. Returns fig or None if no RPE data."""
    rpe_data = sets.dropna(subset=["rpe"])
    if rpe_data.empty:
        return None

    avg = rpe_data.groupby("date")["rpe"].mean().reset_index().sort_values("date")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=avg["date"],
            y=avg["rpe"],
            mode="lines+markers",
            line=dict(color=AMBER, width=2, shape="spline"),
            marker=dict(size=4, color=AMBER),
            fill="tozeroy",
            fillcolor="rgba(251, 191, 36, 0.06)",
            hovertemplate="%{x|%b %d, %Y}<br><b>RPE %{y:.1f}</b><extra></extra>",
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=310,
        title=dict(text="Avg RPE per Session", font=dict(size=13, color=SLATE_300)),
        yaxis_title="RPE",
    )
    fig.update_yaxes(range=[5, 10])
    return fig


def build_top_exercises(sets):
    """Build top-10 exercises horizontal bar figure."""
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
                colorscale=[[0, "rgba(45,212,191,0.25)"], [1, TEAL]],
                cornerradius=5,
                line=dict(width=0),
            ),
            text=top["total_sets"],
            textposition="outside",
            textfont=dict(color=SLATE_400, size=10),
            hovertemplate="%{y}<br><b>%{x} sets</b><br>Avg: %{customdata:.1f} kg<extra></extra>",
            customdata=top["avg_weight"],
        )
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=400,
        xaxis_title="Total Sets",
    )
    return fig


def build_duration(workouts):
    """Build session duration scatter + rolling average figure."""
    data = workouts[["date", "duration_minutes", "workout_category"]].sort_values("date")
    colors = [CATEGORY_COLORS.get(c, SLATE_400) for c in data["workout_category"]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["duration_minutes"],
            mode="markers",
            marker=dict(
                size=7,
                color=colors,
                opacity=0.6,
                line=dict(width=0.5, color="rgba(255,255,255,0.1)"),
            ),
            hovertemplate="%{x|%b %d, %Y}<br><b>%{y:.0f} min</b><extra></extra>",
            showlegend=False,
        )
    )

    if len(data) >= 5:
        roll = data.set_index("date")["duration_minutes"].rolling("14D").mean().reset_index()
        fig.add_trace(
            go.Scatter(
                x=roll["date"],
                y=roll["duration_minutes"],
                mode="lines",
                name="14-day avg",
                line=dict(color=TEAL, width=2, dash="dot"),
                hovertemplate="%{x|%b %d}<br><b>Avg: %{y:.0f} min</b><extra></extra>",
            )
        )

    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=400,
        yaxis_title="Minutes",
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
    return fig
