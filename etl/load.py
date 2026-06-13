"""
Load phase of the Hevy-Flow ETL pipeline.

Creates a normalized PostgreSQL schema in Supabase (workouts + workout_sets)
and loads the cleaned DataFrame using direct SQL via psycopg2.
"""

import logging

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from config import DATABASE_URL

logger = logging.getLogger(__name__)

# ── SQL DDL ──────────────────────────────────────────

CREATE_WORKOUTS_TABLE = """
CREATE TABLE IF NOT EXISTS workouts (
    workout_id      VARCHAR(8) PRIMARY KEY,
    title           TEXT NOT NULL,
    workout_category TEXT NOT NULL,
    start_time      TIMESTAMP NOT NULL,
    end_time        TIMESTAMP NOT NULL,
    duration_minutes NUMERIC(5,1) NOT NULL,
    date            DATE NOT NULL,
    day_of_week     TEXT NOT NULL,
    month           INTEGER NOT NULL,
    year            INTEGER NOT NULL
);
"""

CREATE_WORKOUT_SETS_TABLE = """
CREATE TABLE IF NOT EXISTS workout_sets (
    id              SERIAL PRIMARY KEY,
    workout_id      VARCHAR(8) NOT NULL REFERENCES workouts(workout_id) ON DELETE CASCADE,
    exercise_title  TEXT NOT NULL,
    superset_id     SMALLINT,
    set_index       SMALLINT NOT NULL,
    set_type        TEXT NOT NULL DEFAULT 'normal',
    weight_kg       NUMERIC(6,2) NOT NULL DEFAULT 0.0,
    reps            SMALLINT NOT NULL DEFAULT 0,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    rpe             NUMERIC(3,1),
    is_bodyweight   BOOLEAN NOT NULL DEFAULT FALSE,
    is_timed        BOOLEAN NOT NULL DEFAULT FALSE
);
"""

CREATE_SETS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_workout_sets_workout_id
    ON workout_sets(workout_id);
"""

CREATE_EXERCISE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_workout_sets_exercise
    ON workout_sets(exercise_title);
"""

# ── SQL DML ──────────────────────────────────────────

UPSERT_WORKOUTS = """
INSERT INTO workouts (
    workout_id, title, workout_category, start_time, end_time,
    duration_minutes, date, day_of_week, month, year
)
VALUES %s
ON CONFLICT (workout_id) DO UPDATE SET
    title            = EXCLUDED.title,
    workout_category = EXCLUDED.workout_category,
    start_time       = EXCLUDED.start_time,
    end_time         = EXCLUDED.end_time,
    duration_minutes = EXCLUDED.duration_minutes,
    date             = EXCLUDED.date,
    day_of_week      = EXCLUDED.day_of_week,
    month            = EXCLUDED.month,
    year             = EXCLUDED.year;
"""

INSERT_SETS = """
INSERT INTO workout_sets (
    workout_id, exercise_title, superset_id, set_index, set_type,
    weight_kg, reps, duration_seconds, rpe, is_bodyweight, is_timed
)
VALUES %s;
"""


def load_to_supabase(df: pd.DataFrame, incremental: bool = False) -> dict:
    """Load the cleaned DataFrame into Supabase PostgreSQL.

    Creates a normalized schema with two tables:

    - ``workouts``: one row per workout session
    - ``workout_sets``: one row per exercise set

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame from the transform phase.
    incremental : bool
        If ``True``, only insert workout sessions that don't already
        exist in the database (based on ``workout_id``).  When ``False``
        (default), all sets are truncated and re-inserted.

    Returns
    -------
    dict
        Load statistics: ``total_rows``, ``new_workouts``, ``new_sets``,
        ``skipped_workouts``.

    Raises
    ------
    ConnectionError
        If the database connection cannot be established.
    """
    logger.info("Starting load phase (mode=%s)", "incremental" if incremental else "full")

    stats = {"total_rows": len(df), "new_workouts": 0, "new_sets": 0, "skipped_workouts": 0}

    if not DATABASE_URL:
        raise ConnectionError(
            "DATABASE_URL is not set. Add it to your .env file. "
            "See .env.example for the expected format."
        )

    conn = None
    try:
        # ── 1. Connect ───────────────────────────────
        conn = psycopg2.connect(DATABASE_URL)
        logger.info("Connected to Supabase PostgreSQL")

        with conn.cursor() as cur:
            # ── 2. Create tables ─────────────────────
            _create_tables(cur)
            conn.commit()

            # ── 3. Filter to new data (incremental) ──
            if incremental:
                existing_ids = _get_existing_workout_ids(cur)
                all_ids = set(df["workout_id"].unique())
                new_ids = all_ids - existing_ids
                skipped = all_ids - new_ids

                stats["skipped_workouts"] = len(skipped)

                if not new_ids:
                    logger.info(
                        "No new workouts found — all %d sessions already in database",
                        len(all_ids),
                    )
                    stats["new_workouts"] = 0
                    stats["new_sets"] = 0
                    return stats

                df = df[df["workout_id"].isin(new_ids)]
                logger.info(
                    "Incremental: %d new sessions, %d already exist → loading %d sets",
                    len(new_ids),
                    len(skipped),
                    len(df),
                )

            # ── 4. Prepare data ──────────────────────
            df_workouts = _prepare_workouts_df(df)
            df_sets = _prepare_sets_df(df)

            stats["new_workouts"] = len(df_workouts)
            stats["new_sets"] = len(df_sets)

            # ── 5. Load workouts (upsert) ────────────
            _load_workouts(cur, df_workouts)
            conn.commit()

            # ── 6. Load sets ─────────────────────────
            if incremental:
                # Only insert new sets (no truncate)
                _insert_sets(cur, df_sets)
            else:
                # Full refresh: truncate + re-insert
                _load_sets(cur, df_sets)
            conn.commit()

        logger.info("Load phase complete")

    except psycopg2.OperationalError as exc:
        raise ConnectionError(f"Failed to connect to database: {exc}") from exc
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")

    return stats


# ── Internal helpers ─────────────────────────────────


def _create_tables(cur) -> None:
    """Create the workouts and workout_sets tables if they don't exist."""
    cur.execute(CREATE_WORKOUTS_TABLE)
    cur.execute(CREATE_WORKOUT_SETS_TABLE)
    cur.execute(CREATE_SETS_INDEX)
    cur.execute(CREATE_EXERCISE_INDEX)
    logger.info("Tables and indexes created (or already exist)")


def _get_existing_workout_ids(cur) -> set:
    """Query the database for all existing workout_ids."""
    cur.execute("SELECT workout_id FROM workouts")
    ids = {row[0] for row in cur.fetchall()}
    logger.info("Found %d existing workout sessions in database", len(ids))
    return ids


def _prepare_workouts_df(df: pd.DataFrame) -> pd.DataFrame:
    """Extract unique workout sessions from the set-level DataFrame."""
    workouts = (
        df.groupby("workout_id")
        .agg(
            title=("title", "first"),
            workout_category=("workout_category", "first"),
            start_time=("start_time", "first"),
            end_time=("end_time", "first"),
            duration_minutes=("duration_minutes", "first"),
            date=("date", "first"),
            day_of_week=("day_of_week", "first"),
            month=("month", "first"),
            year=("year", "first"),
        )
        .reset_index()
    )
    logger.info("Prepared %d workout sessions for loading", len(workouts))
    return workouts


def _prepare_sets_df(df: pd.DataFrame) -> pd.DataFrame:
    """Select and order the columns needed for the workout_sets table."""
    sets = df[
        [
            "workout_id",
            "exercise_title",
            "superset_id",
            "set_index",
            "set_type",
            "weight_kg",
            "reps",
            "duration_seconds",
            "rpe",
            "is_bodyweight",
            "is_timed",
        ]
    ].copy()

    logger.info("Prepared %d workout sets for loading", len(sets))
    return sets


def _safe_int(value):
    """Convert a value to int, returning None if NaN/None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return int(value)


def _safe_float(value):
    """Convert a value to float, returning None if NaN/None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)


def _load_workouts(cur, df_workouts: pd.DataFrame) -> None:
    """Upsert workout sessions into the workouts table."""
    values = [
        (
            row.workout_id,
            row.title,
            row.workout_category,
            row.start_time,
            row.end_time,
            float(row.duration_minutes),
            row.date,
            row.day_of_week,
            int(row.month),
            int(row.year),
        )
        for row in df_workouts.itertuples(index=False)
    ]

    execute_values(cur, UPSERT_WORKOUTS, values)
    logger.info("Upserted %d workout sessions", len(values))


def _load_sets(cur, df_sets: pd.DataFrame) -> None:
    """Clear existing sets and bulk-insert fresh data.

    This approach ensures idempotency — running the pipeline multiple
    times produces the same result without duplicates.
    """
    cur.execute("TRUNCATE TABLE workout_sets RESTART IDENTITY;")
    logger.info("Cleared existing workout_sets data")

    values = [
        (
            row.workout_id,
            row.exercise_title,
            _safe_int(row.superset_id),
            int(row.set_index),
            row.set_type,
            float(row.weight_kg),
            int(row.reps),
            int(row.duration_seconds),
            _safe_float(row.rpe),
            bool(row.is_bodyweight),
            bool(row.is_timed),
        )
        for row in df_sets.itertuples(index=False)
    ]

    execute_values(cur, INSERT_SETS, values, page_size=500)
    logger.info("Inserted %d workout sets", len(values))


def _insert_sets(cur, df_sets: pd.DataFrame) -> None:
    """Insert new sets without clearing existing data (incremental mode)."""
    values = [
        (
            row.workout_id,
            row.exercise_title,
            _safe_int(row.superset_id),
            int(row.set_index),
            row.set_type,
            float(row.weight_kg),
            int(row.reps),
            int(row.duration_seconds),
            _safe_float(row.rpe),
            bool(row.is_bodyweight),
            bool(row.is_timed),
        )
        for row in df_sets.itertuples(index=False)
    ]

    execute_values(cur, INSERT_SETS, values, page_size=500)
    logger.info("Inserted %d new workout sets (incremental)", len(values))
