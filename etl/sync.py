"""
Incremental sync orchestrator for the Hevy-Flow ETL pipeline.

Uses the Hevy API's ``/v1/workouts/events`` endpoint to fetch only
workouts that have been created, updated, or deleted since the last
successful sync.  The sync timestamp is persisted in the Supabase
``sync_metadata`` table so it works identically in local runs and
CI / GitHub Actions (where the filesystem is ephemeral).
"""

import logging
from datetime import UTC, datetime

import psycopg2

from config import DATABASE_URL
from etl.extract import HevyAPIClient, _flatten_api_workouts
from etl.load import (
    _create_tables,
    _insert_sets,
    _load_workouts,
    _prepare_sets_df,
    _prepare_workouts_df,
    delete_workouts,
    get_last_sync,
    set_last_sync,
)
from etl.transform import transform_workouts

logger = logging.getLogger(__name__)

# Epoch used as the "since" value when no prior sync has occurred.
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def run_incremental_sync() -> dict:
    """Run an event-based incremental sync from the Hevy API to Supabase.

    Workflow
    --------
    1. Read ``last_sync_at`` from the ``sync_metadata`` table.
    2. Fetch workout events since that timestamp.
    3. Delete any workouts marked as ``deleted`` in the events.
    4. Flatten, transform, and upsert any ``updated`` workouts.
    5. Write the current UTC timestamp back to ``sync_metadata``.

    Returns
    -------
    dict
        Sync statistics: ``updated``, ``deleted``, ``api_pages_fetched``.

    Raises
    ------
    ConnectionError
        If the database connection cannot be established.
    """
    stats = {"updated": 0, "deleted": 0, "api_pages_fetched": 0}

    if not DATABASE_URL:
        raise ConnectionError(
            "DATABASE_URL is not set. Add it to your .env file. "
            "See .env.example for the expected format."
        )

    conn = None
    try:
        # ── 1. Connect & ensure schema ───────────
        conn = psycopg2.connect(DATABASE_URL)
        logger.info("Connected to Supabase PostgreSQL")

        with conn.cursor() as cur:
            _create_tables(cur)
            conn.commit()

            # ── 2. Read last sync timestamp ──────
            last_sync = get_last_sync(cur)
            since = last_sync or _EPOCH
            logger.info("Syncing events since %s", since.isoformat())

            # ── 3. Fetch events from Hevy API ────
            client = HevyAPIClient()
            updated_workouts, deleted_ids = client.fetch_workout_events(since)

            # ── 4. Handle deletions ──────────────
            if deleted_ids:
                deleted_count = delete_workouts(cur, deleted_ids)
                stats["deleted"] = deleted_count
                conn.commit()
                logger.info("Deleted %d workouts", deleted_count)

            # ── 5. Handle updates / inserts ──────
            if updated_workouts:
                df_flat = _flatten_api_workouts(updated_workouts)
                df_clean = transform_workouts(df_flat)

                df_workouts = _prepare_workouts_df(df_clean)
                df_sets = _prepare_sets_df(df_clean)

                _load_workouts(cur, df_workouts)
                _insert_sets(cur, df_sets)
                conn.commit()

                stats["updated"] = len(df_workouts)
                logger.info(
                    "Upserted %d workouts (%d sets)",
                    len(df_workouts),
                    len(df_sets),
                )

            # ── 6. Persist sync timestamp ────────
            now = datetime.now(UTC)
            set_last_sync(cur, now)
            conn.commit()

    except psycopg2.OperationalError as exc:
        raise ConnectionError(f"Failed to connect to database: {exc}") from exc
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")

    logger.info(
        "Incremental sync complete — %d updated, %d deleted",
        stats["updated"],
        stats["deleted"],
    )
    return stats
