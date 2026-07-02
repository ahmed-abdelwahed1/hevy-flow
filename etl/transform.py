"""
Transform phase of the Hevy-Flow ETL pipeline.

Cleans, normalizes, and enriches the raw workout data extracted from the
Hevy CSV export.  Each transformation step is implemented as a separate
function so it can be tested, logged, and reasoned about independently.
"""

import hashlib
import logging

import pandas as pd

from config import DATETIME_FORMAT

logger = logging.getLogger(__name__)

# ── Title → Category mapping ────────────────────────
# Hevy's workout titles evolved over time.  This map normalises the
# free-text session names into a consistent set of categories.
_TITLE_CATEGORY_MAP: dict[str, str] = {
    "Push": "Push",
    "PUSH": "Push",
    "Pull": "Pull",
    "PULL": "Pull",
    "Legs": "Legs",
    "LEGS": "Legs",
    "Upper": "Upper",
    "UPPER": "Upper",
    "Upper Body": "Upper",
    "Lower": "Lower",
    "LOWER": "Lower",
    "Lower Body": "Lower",
    "Day 1 – Upper Push": "Push",
    "Day 2 – Upper Pull": "Pull",
    "Evening workout 🏋️": "Full Body",
    "Hotel Full Body Workout": "Full Body",
}


def transform_workouts(df: pd.DataFrame) -> pd.DataFrame:
    """Run the full transformation pipeline on the raw workout DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame from the extraction phase.

    Returns
    -------
    pd.DataFrame
        Cleaned, enriched DataFrame ready for loading.
    """
    logger.info("Starting transformation phase — %d rows in", len(df))
    row_count_in = len(df)

    df = _parse_datetimes(df)
    df = _add_derived_time_columns(df)
    df = _generate_workout_ids(df)
    df = _handle_weight_nulls(df)
    df = _handle_reps_nulls(df)
    df = _handle_rpe_nulls(df)
    df = _normalize_titles(df)
    df = _drop_empty_columns(df)
    df = _enforce_dtypes(df)

    logger.info(
        "Transformation complete — %d rows out (%d columns)",
        len(df),
        len(df.columns),
    )
    assert len(df) == row_count_in, "Row count changed during transformation!"

    _log_transform_summary(df)
    return df


# ── Individual transformation steps ─────────────────


def _parse_datetimes(df: pd.DataFrame) -> pd.DataFrame:
    """Convert ``start_time`` and ``end_time`` from text to datetime.

    Auto-detects the source format:
    - Already datetime (from a prior step) → no-op.
    - ISO 8601 strings (API) → ``pd.to_datetime(utc=True)``.
    - CSV-format strings → ``pd.to_datetime(format=DATETIME_FORMAT)``.
    """
    df = df.copy()

    for col in ("start_time", "end_time"):
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            logger.info("%s already datetime — skipping parse", col)
            continue

        # Try ISO 8601 first (API path), fall back to CSV format
        try:
            df[col] = pd.to_datetime(df[col], utc=True)
            logger.info("Parsed %s as ISO 8601", col)
        except (ValueError, TypeError):
            df[col] = pd.to_datetime(df[col], format=DATETIME_FORMAT)
            logger.info("Parsed %s using CSV format (%s)", col, DATETIME_FORMAT)

    logger.info(
        "Parsed datetimes — range: %s to %s",
        df["start_time"].min().strftime("%Y-%m-%d"),
        df["start_time"].max().strftime("%Y-%m-%d"),
    )
    return df


def _add_derived_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Compute workout duration and calendar attributes from timestamps."""
    df = df.copy()

    df["duration_minutes"] = ((df["end_time"] - df["start_time"]).dt.total_seconds() / 60).round(1)

    df["day_of_week"] = df["start_time"].dt.day_name()
    df["month"] = df["start_time"].dt.month
    df["year"] = df["start_time"].dt.year
    df["date"] = df["start_time"].dt.date

    logger.info("Added derived columns: duration_minutes, day_of_week, month, year, date")
    return df


def _generate_workout_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Create a deterministic ``workout_id`` for each unique session.

    When the API path is used, ``workout_id`` is already populated with
    Hevy's canonical UUID during flattening — in that case this step is
    skipped.  For CSV imports the hash is still generated.
    """
    if "workout_id" in df.columns and df["workout_id"].notna().all():
        unique_sessions = df["workout_id"].nunique()
        logger.info(
            "workout_id already present (API path) — %d unique sessions",
            unique_sessions,
        )
        return df

    df = df.copy()

    def _hash_session(row: pd.Series) -> str:
        key = f"{row['title']}_{row['start_time']}"
        return hashlib.md5(key.encode()).hexdigest()[:8]

    df["workout_id"] = df.apply(_hash_session, axis=1)

    unique_sessions = df["workout_id"].nunique()
    logger.info("Generated workout_id — %d unique sessions (CSV path)", unique_sessions)
    return df


def _handle_weight_nulls(df: pd.DataFrame) -> pd.DataFrame:
    """Flag bodyweight exercises and fill their ``weight_kg`` with 0.0."""
    df = df.copy()

    df["is_bodyweight"] = df["weight_kg"].isna()
    bodyweight_count = df["is_bodyweight"].sum()

    df["weight_kg"] = df["weight_kg"].fillna(0.0)

    bw_exercises = df.loc[df["is_bodyweight"], "exercise_title"].unique()
    logger.info(
        "Handled weight_kg nulls — %d bodyweight sets (%.1f%%) across %d exercises: %s",
        bodyweight_count,
        (bodyweight_count / len(df)) * 100,
        len(bw_exercises),
        ", ".join(sorted(bw_exercises)),
    )
    return df


def _handle_reps_nulls(df: pd.DataFrame) -> pd.DataFrame:
    """Handle null reps — these are timed exercises (e.g. Plank).

    Sets ``is_timed = True`` for exercises that use ``duration_seconds``
    instead of reps, and fills reps with 0.
    """
    df = df.copy()

    df["is_timed"] = df["reps"].isna()
    timed_count = df["is_timed"].sum()

    df["reps"] = df["reps"].fillna(0)
    df["duration_seconds"] = df["duration_seconds"].fillna(0)

    if timed_count > 0:
        timed_exercises = df.loc[df["is_timed"], "exercise_title"].unique()
        logger.info(
            "Handled reps nulls — %d timed sets flagged: %s",
            timed_count,
            ", ".join(sorted(timed_exercises)),
        )
    else:
        logger.info("Handled reps nulls — no timed exercises found")

    return df


def _handle_rpe_nulls(df: pd.DataFrame) -> pd.DataFrame:
    """Leave RPE nulls as NaN — they represent untracked sessions."""
    rpe_null_count = df["rpe"].isna().sum()
    rpe_pct = (rpe_null_count / len(df)) * 100
    logger.info(
        "RPE nulls preserved as NaN — %d rows (%.1f%%) without RPE tracking",
        rpe_null_count,
        rpe_pct,
    )
    return df


def _normalize_titles(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw workout titles to a consistent ``workout_category``."""
    df = df.copy()

    df["workout_category"] = df["title"].map(_TITLE_CATEGORY_MAP)

    unmapped = df[df["workout_category"].isna()]["title"].unique()
    if len(unmapped) > 0:
        logger.warning("Unmapped workout titles: %s — defaulting to 'Other'", unmapped)
        df["workout_category"] = df["workout_category"].fillna("Other")

    category_counts = df["workout_category"].value_counts().to_dict()
    logger.info("Normalized titles into categories: %s", category_counts)
    return df


def _drop_empty_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop columns that are >95% null or carry no useful information.

    Defensively checks column existence and null percentage rather than
    hardcoding names, so both API and CSV paths work safely.
    """
    candidates = ["description", "exercise_notes", "distance_km"]
    to_drop: list[str] = []

    for col in candidates:
        if col not in df.columns:
            continue
        null_pct = df[col].isna().sum() / len(df) if len(df) > 0 else 1.0
        if null_pct >= 0.95:
            to_drop.append(col)

    if to_drop:
        df = df.drop(columns=to_drop)
        logger.info("Dropped empty columns (≥95%% null): %s", to_drop)
    else:
        logger.info("No columns dropped — all candidates have data")

    return df


def _enforce_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Enforce correct data types on the final DataFrame."""
    df = df.copy()

    df["set_index"] = df["set_index"].astype(int)
    df["reps"] = df["reps"].astype(int)
    df["duration_seconds"] = df["duration_seconds"].astype(int)
    df["month"] = df["month"].astype(int)
    df["year"] = df["year"].astype(int)

    logger.info("Enforced final data types")
    return df


# ── Summary ──────────────────────────────────────────


def _log_transform_summary(df: pd.DataFrame) -> None:
    """Log a post-transformation summary of the DataFrame."""
    logger.info("── Post-Transform Summary ──────────────────────")
    logger.info("Shape: %d rows × %d columns", len(df), len(df.columns))
    logger.info("Columns: %s", list(df.columns))
    logger.info("Dtypes:")
    for col in df.columns:
        null_count = df[col].isna().sum()
        logger.info(
            "  %-20s | %-12s | nulls: %d",
            col,
            str(df[col].dtype),
            null_count,
        )
    logger.info("── End of summary ─────────────────────────────")
