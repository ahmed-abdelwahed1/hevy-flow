"""
Hevy-Flow ETL Pipeline — Main Entry Point

Orchestrates the full Extract → Transform → Load pipeline.

Usage
-----
    python main.py                   # incremental sync (default)
    python main.py --mode full       # full re-fetch from API
    python main.py --mode csv        # legacy CSV import
"""

import argparse
import logging
import sys
import time

from config import setup_logging
from etl.extract import extract_workouts
from etl.load import load_to_supabase
from etl.sync import run_incremental_sync
from etl.transform import transform_workouts

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Hevy-Flow ETL Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["incremental", "full", "csv"],
        default="incremental",
        help=(
            "Pipeline mode: "
            "'incremental' (default) — event-based sync via API, "
            "'full' — re-fetch all workouts from API, "
            "'csv' — legacy CSV file import."
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Run the Hevy-Flow ETL pipeline."""
    setup_logging()
    args = _parse_args()

    logger.info("=" * 60)
    logger.info("HEVY-FLOW ETL PIPELINE — Starting (mode=%s)", args.mode)
    logger.info("=" * 60)

    start_time = time.time()

    try:
        if args.mode == "incremental":
            _run_incremental(args)
        elif args.mode == "full":
            _run_full(args)
        elif args.mode == "csv":
            _run_csv(args)

    except FileNotFoundError as exc:
        logger.error("Pipeline failed — %s", exc)
        sys.exit(1)
    except ValueError as exc:
        logger.error("Pipeline failed — schema error: %s", exc)
        sys.exit(1)
    except ConnectionError as exc:
        logger.error("Pipeline failed — connection error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Pipeline failed — unexpected error: %s", exc, exc_info=True)
        sys.exit(1)

    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE — %.2f seconds", elapsed)
    logger.info("=" * 60)


def _run_incremental(_args: argparse.Namespace) -> None:
    """Event-based incremental sync via the Hevy API."""
    logger.info("Mode: INCREMENTAL SYNC")
    stats = run_incremental_sync()
    logger.info(
        "Sync results — %d updated, %d deleted",
        stats["updated"],
        stats["deleted"],
    )


def _run_full(_args: argparse.Namespace) -> None:
    """Full re-fetch of all workouts from the Hevy API."""
    logger.info("Mode: FULL API FETCH")

    # Phase 1: Extract
    logger.info("Phase 1/3: EXTRACT (API)")
    df_raw = extract_workouts()
    logger.info("Extraction complete — %d rows ready for transformation", len(df_raw))

    # Phase 2: Transform
    logger.info("Phase 2/3: TRANSFORM")
    df_clean = transform_workouts(df_raw)
    logger.info(
        "Transformation complete — %d rows, %d columns",
        len(df_clean),
        len(df_clean.columns),
    )

    # Phase 3: Load
    logger.info("Phase 3/3: LOAD")
    load_to_supabase(df_clean)


def _run_csv(_args: argparse.Namespace) -> None:
    """Legacy CSV file import."""
    logger.info("Mode: CSV IMPORT")

    # Phase 1: Extract
    logger.info("Phase 1/3: EXTRACT (CSV)")
    df_raw = extract_workouts()
    logger.info("Extraction complete — %d rows ready for transformation", len(df_raw))

    # Phase 2: Transform
    logger.info("Phase 2/3: TRANSFORM")
    df_clean = transform_workouts(df_raw)
    logger.info(
        "Transformation complete — %d rows, %d columns",
        len(df_clean),
        len(df_clean.columns),
    )

    # Phase 3: Load
    logger.info("Phase 3/3: LOAD")
    load_to_supabase(df_clean)


if __name__ == "__main__":
    main()
