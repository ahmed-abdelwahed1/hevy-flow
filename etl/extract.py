"""
Extract phase of the Hevy-Flow ETL pipeline.

Reads the raw Hevy workout CSV export and performs initial validation
to ensure the data conforms to the expected schema before downstream
processing.
"""

import logging
from pathlib import Path

import pandas as pd

from config import EXPECTED_COLUMNS, RAW_DATA_PATH

logger = logging.getLogger(__name__)


def extract_workouts(filepath: Path = RAW_DATA_PATH, uploaded_file=None) -> pd.DataFrame:
    """Read the raw Hevy CSV export and validate its schema.

    Parameters
    ----------
    filepath : Path
        Absolute or relative path to the CSV file.  Used when
        ``uploaded_file`` is *not* provided.
    uploaded_file : file-like, optional
        A file-like object (e.g. ``BytesIO`` from Streamlit's
        ``file_uploader``).  When provided, ``filepath`` is ignored.

    Returns
    -------
    pd.DataFrame
        The raw (uncleaned) workout DataFrame.

    Raises
    ------
    FileNotFoundError
        If no ``uploaded_file`` is given and the CSV does not exist.
    ValueError
        If required columns are missing from the CSV.
    """
    logger.info("Starting extraction phase")

    # ── 1. Read CSV ──────────────────────────────────
    if uploaded_file is not None:
        logger.info("Source: uploaded file (%s)", getattr(uploaded_file, "name", "stream"))
        df = pd.read_csv(uploaded_file)
    else:
        logger.info("Source file: %s", filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        file_size_kb = filepath.stat().st_size / 1024
        logger.info("File size: %.1f KB", file_size_kb)
        df = pd.read_csv(filepath)

    logger.info("Loaded %d rows × %d columns", len(df), len(df.columns))

    # ── 2. Schema validation ─────────────────────────
    actual_columns = list(df.columns)
    missing = set(EXPECTED_COLUMNS) - set(actual_columns)
    extra = set(actual_columns) - set(EXPECTED_COLUMNS)

    if missing:
        raise ValueError(f"Missing expected columns: {missing}")

    if extra:
        logger.warning("Unexpected extra columns found: %s", extra)

    logger.info("Schema validation passed — all %d expected columns present", len(EXPECTED_COLUMNS))

    # ── 3. Profile the data ──────────────────────────
    _log_data_profile(df)

    return df


def _log_data_profile(df: pd.DataFrame) -> None:
    """Log a summary profile of the extracted DataFrame.

    Outputs column data types, null counts, and unique value counts
    to give a quick snapshot of data quality before transformation.
    """
    logger.info("── Data Profile ────────────────────────────────")
    logger.info("Columns and dtypes:")

    for col in df.columns:
        null_count = df[col].isna().sum()
        null_pct = (null_count / len(df)) * 100
        unique_count = df[col].nunique()
        logger.info(
            "  %-20s | dtype: %-10s | nulls: %4d (%5.1f%%) | unique: %d",
            col,
            str(df[col].dtype),
            null_count,
            null_pct,
            unique_count,
        )

    logger.info("── Sample rows (first 3) ───────────────────────")
    for idx, row in df.head(3).iterrows():
        logger.info("  Row %d: %s", idx, row.to_dict())

    logger.info("── End of data profile ─────────────────────────")
