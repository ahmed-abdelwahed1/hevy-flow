"""
Hevy-Flow ETL Pipeline — Main Entry Point

Orchestrates the full Extract → Transform → Load pipeline.
Run with:  python main.py
"""

import logging
import sys
import time

from config import setup_logging
from etl.extract import extract_workouts
from etl.transform import transform_workouts
from etl.load import load_to_supabase

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the Hevy-Flow ETL pipeline."""
    setup_logging()

    logger.info("=" * 60)
    logger.info("HEVY-FLOW ETL PIPELINE — Starting")
    logger.info("=" * 60)

    start_time = time.time()

    try:
        # ── Phase 1: Extract ─────────────────────────
        logger.info("Phase 1/3: EXTRACT")
        df_raw = extract_workouts()
        logger.info(
            "Extraction complete — %d rows ready for transformation", len(df_raw)
        )

        # ── Phase 2: Transform ───────────────────────
        logger.info("Phase 2/3: TRANSFORM")
        df_clean = transform_workouts(df_raw)
        logger.info(
            "Transformation complete — %d rows, %d columns",
            len(df_clean),
            len(df_clean.columns),
        )

        # ── Phase 3: Load ────────────────────────────
        logger.info("Phase 3/3: LOAD")
        load_to_supabase(df_clean)

    except FileNotFoundError as exc:
        logger.error("Pipeline failed — %s", exc)
        sys.exit(1)
    except ValueError as exc:
        logger.error("Pipeline failed — schema error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Pipeline failed — unexpected error: %s", exc, exc_info=True)
        sys.exit(1)

    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE — %.2f seconds", elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
