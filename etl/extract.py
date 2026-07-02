"""
Extract phase of the Hevy-Flow ETL pipeline.

Supports two extraction modes:
  1. **Hevy REST API** (primary) – fetches workouts from
     ``https://api.hevyapp.com`` using a paginated client.
  2. **CSV file** (fallback) – reads a manually exported Hevy CSV,
     used by the Streamlit dashboard's file-uploader.

The public entry-point ``extract_workouts()`` auto-selects the correct
mode based on the arguments it receives.
"""

import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from config import (
    EXPECTED_COLUMNS,
    HEVY_API_BASE_URL,
    HEVY_API_KEY,
    HEVY_API_PAGE_SIZE,
    HEVY_API_REQUEST_DELAY,
    RAW_DATA_PATH,
)

logger = logging.getLogger(__name__)


# ── Exceptions ───────────────────────────────────────


class HevyAPIError(Exception):
    """Raised when the Hevy API returns a non-2xx response."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Hevy API error {status_code}: {message}")


# ── API Client ───────────────────────────────────────


class HevyAPIClient:
    """Thin wrapper around the Hevy REST API with pagination and retries.

    Parameters
    ----------
    api_key : str
        Hevy API key (UUID format).
    base_url : str
        API base URL, defaults to ``HEVY_API_BASE_URL``.
    page_size : int
        Items per page (max 10 for workouts).
    request_delay : float
        Seconds to sleep between paginated requests.
    max_retries : int
        Maximum retry attempts on transient errors (429, 5xx).
    """

    def __init__(
        self,
        api_key: str = HEVY_API_KEY,
        base_url: str = HEVY_API_BASE_URL,
        page_size: int = HEVY_API_PAGE_SIZE,
        request_delay: float = HEVY_API_REQUEST_DELAY,
        max_retries: int = 3,
    ):
        if not api_key:
            raise HevyAPIError(
                401,
                "HEVY_API_KEY is not set. Add it to your .env file. "
                "Get your key at https://hevy.com/settings?developer",
            )
        self.base_url = base_url.rstrip("/")
        self.page_size = page_size
        self.request_delay = request_delay
        self.max_retries = max_retries

        self.session = requests.Session()
        self.session.headers.update({"api-key": api_key})

    # ── Public methods ───────────────────────────

    def fetch_all_workouts(self) -> list[dict]:
        """Paginate through ``GET /v1/workouts`` and return all workouts."""
        logger.info("Fetching all workouts from Hevy API")
        workouts: list[dict] = []
        page = 1

        while True:
            data = self._get(
                "/v1/workouts",
                params={"page": page, "pageSize": self.page_size},
            )
            batch = data.get("workouts", [])
            workouts.extend(batch)
            page_count = data.get("page_count", 1)

            logger.info(
                "Fetched page %d/%d — %d workouts in batch",
                page,
                page_count,
                len(batch),
            )

            if page >= page_count:
                break
            page += 1
            time.sleep(self.request_delay)

        logger.info("Total workouts fetched: %d", len(workouts))
        return workouts

    def fetch_workout_events(self, since: datetime) -> tuple[list[dict], list[str]]:
        """Fetch workout events (updates + deletes) since *since*.

        Returns
        -------
        tuple[list[dict], list[str]]
            ``(updated_workouts, deleted_workout_ids)``
        """
        since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.info("Fetching workout events since %s", since_iso)

        updated: list[dict] = []
        deleted: list[str] = []
        page = 1

        while True:
            data = self._get(
                "/v1/workouts/events",
                params={
                    "page": page,
                    "pageSize": self.page_size,
                    "since": since_iso,
                },
            )
            events = data.get("events", [])
            page_count = data.get("page_count", 1)

            for event in events:
                if event.get("type") == "deleted":
                    deleted.append(event["id"])
                elif event.get("type") == "updated":
                    updated.append(event["workout"])

            logger.info(
                "Events page %d/%d — %d events",
                page,
                page_count,
                len(events),
            )

            if page >= page_count:
                break
            page += 1
            time.sleep(self.request_delay)

        logger.info(
            "Events summary: %d updated, %d deleted",
            len(updated),
            len(deleted),
        )
        return updated, deleted

    def fetch_workout_count(self) -> int:
        """Return total workout count from ``GET /v1/workouts/count``."""
        data = self._get("/v1/workouts/count")
        count = data.get("workout_count", 0)
        logger.info("Hevy reports %d total workouts", count)
        return count

    # ── Internal helpers ─────────────────────────

    def _get(self, path: str, params: dict | None = None) -> dict:
        """Issue a GET request with retry + back-off logic."""
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=30)

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 2**attempt))
                    logger.warning(
                        "Rate limited (429). Retry-After: %ds (attempt %d/%d)",
                        retry_after,
                        attempt,
                        self.max_retries,
                    )
                    time.sleep(retry_after)
                    continue

                if resp.status_code >= 500:
                    wait = 2**attempt
                    logger.warning(
                        "Server error %d. Retrying in %ds (attempt %d/%d)",
                        resp.status_code,
                        wait,
                        attempt,
                        self.max_retries,
                    )
                    time.sleep(wait)
                    continue

                if resp.status_code >= 400:
                    raise HevyAPIError(resp.status_code, resp.text)

                return resp.json()

            except requests.RequestException as exc:
                last_exc = exc
                wait = 2**attempt
                logger.warning(
                    "Request error: %s. Retrying in %ds (attempt %d/%d)",
                    exc,
                    wait,
                    attempt,
                    self.max_retries,
                )
                time.sleep(wait)

        raise HevyAPIError(0, f"All {self.max_retries} retries exhausted: {last_exc}")


# ── Flattener ────────────────────────────────────────


def _flatten_api_workouts(workouts: list[dict]) -> pd.DataFrame:
    """Convert nested API workout JSON into a flat row-per-set DataFrame.

    Maps the Hevy API ``Workout`` schema to the same column layout that
    the downstream transform and load phases expect.
    """
    rows: list[dict] = []

    for workout in workouts:
        workout_id = workout.get("id", "")
        title = workout.get("title", "")
        start_time = workout.get("start_time", "")
        end_time = workout.get("end_time", "")
        description = workout.get("description", "")

        exercises = workout.get("exercises", [])
        for exercise in exercises:
            exercise_title = exercise.get("title", "")
            # API uses "supersets_id" (plural); our schema uses "superset_id"
            superset_id = exercise.get("supersets_id")
            exercise_notes = exercise.get("notes", "")

            sets = exercise.get("sets", [])
            for s in sets:
                distance_meters = s.get("distance_meters")
                distance_km = distance_meters / 1000.0 if distance_meters is not None else None

                rows.append(
                    {
                        "workout_id": workout_id,
                        "title": title,
                        "start_time": start_time,
                        "end_time": end_time,
                        "description": description,
                        "exercise_title": exercise_title,
                        "superset_id": superset_id,
                        "exercise_notes": exercise_notes,
                        "set_index": s.get("index", 0),
                        "set_type": s.get("type", "normal"),
                        "weight_kg": s.get("weight_kg"),
                        "reps": s.get("reps"),
                        "distance_km": distance_km,
                        "duration_seconds": s.get("duration_seconds"),
                        "rpe": s.get("rpe"),
                    }
                )

    if not rows:
        logger.warning("No sets found — returned empty DataFrame")
        return pd.DataFrame(
            columns=[
                "workout_id",
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
        )

    df = pd.DataFrame(rows)
    logger.info(
        "Flattened %d workouts into %d set-level rows",
        len(workouts),
        len(df),
    )
    return df


# ── CSV Extraction (legacy / dashboard fallback) ─────


def _extract_from_csv(filepath: Path = RAW_DATA_PATH, uploaded_file=None) -> pd.DataFrame:
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
    logger.info("Extracting from CSV source")

    if uploaded_file is not None:
        logger.info(
            "Source: uploaded file (%s)",
            getattr(uploaded_file, "name", "stream"),
        )
        df = pd.read_csv(uploaded_file)
    else:
        logger.info("Source file: %s", filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        file_size_kb = filepath.stat().st_size / 1024
        logger.info("File size: %.1f KB", file_size_kb)
        df = pd.read_csv(filepath)

    logger.info("Loaded %d rows × %d columns", len(df), len(df.columns))

    # Schema validation
    actual_columns = list(df.columns)
    missing = set(EXPECTED_COLUMNS) - set(actual_columns)
    extra = set(actual_columns) - set(EXPECTED_COLUMNS)

    if missing:
        raise ValueError(f"Missing expected columns: {missing}")
    if extra:
        logger.warning("Unexpected extra columns found: %s", extra)

    logger.info(
        "Schema validation passed — all %d expected columns present",
        len(EXPECTED_COLUMNS),
    )
    return df


# ── Public entry point ───────────────────────────────


def extract_workouts(filepath: Path = RAW_DATA_PATH, uploaded_file=None) -> pd.DataFrame:
    """Extract workout data from the Hevy API or a CSV file.

    When ``uploaded_file`` is provided the CSV path is used (dashboard
    fallback).  Otherwise, the Hevy REST API is called.

    Parameters
    ----------
    filepath : Path
        Path to CSV file (only used when ``uploaded_file`` is given and
        the file is on disk rather than in memory).
    uploaded_file : file-like, optional
        File-like object from Streamlit's ``file_uploader``.

    Returns
    -------
    pd.DataFrame
        The raw workout DataFrame (one row per set).
    """
    logger.info("Starting extraction phase")

    if uploaded_file is not None:
        # ── CSV path (dashboard file-uploader) ───
        df = _extract_from_csv(filepath=filepath, uploaded_file=uploaded_file)
    else:
        # ── API path (primary) ───────────────────
        client = HevyAPIClient()
        workouts = client.fetch_all_workouts()
        df = _flatten_api_workouts(workouts)

    logger.info("Extraction complete — %d rows × %d columns", len(df), len(df.columns))
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
        null_pct = (null_count / len(df)) * 100 if len(df) > 0 else 0
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
