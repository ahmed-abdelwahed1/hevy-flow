"""
Centralized configuration for the Hevy-Flow ETL pipeline.

All paths, constants, and shared settings live here so that every module
imports from a single source of truth.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env if present ─────────────────────────────
load_dotenv()

# ── Paths ────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DATA_PATH = PROJECT_ROOT / "data" / "workouts.csv"
LOG_DIR = PROJECT_ROOT / "logs"

# ── Datetime parsing ─────────────────────────────────
# Hevy exports timestamps like "Jun 11, 2026, 1:01 PM"
DATETIME_FORMAT = "%b %d, %Y, %I:%M %p"

# ── Expected CSV schema ──────────────────────────────
EXPECTED_COLUMNS = [
    "title",
    "start_time",
    "end_time",
    "description",
    "exercise_title",
    "superset_id",
    "exercise_notes",
    "set_index",
    "set_type",
    "weight_kg",
    "reps",
    "distance_km",
    "duration_seconds",
    "rpe",
]

# ── Database ─────────────────────────────────────────
# Full PostgreSQL connection string from Supabase
# Format: postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres
DATABASE_URL = os.getenv("DATABASE_URL", "")

# ── Logging ──────────────────────────────────────────


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging to both console and a rotating log file.

    Creates the ``logs/`` directory if it doesn't exist and writes
    timestamped entries to ``logs/pipeline.log`` alongside console output.
    """
    LOG_DIR.mkdir(exist_ok=True)

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid adding duplicate handlers on repeated calls
    if root_logger.handlers:
        return

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    root_logger.addHandler(file_handler)
