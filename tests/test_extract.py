from io import BytesIO

import pandas as pd
import pytest

from config import EXPECTED_COLUMNS
from etl.extract import (
    HevyAPIClient,
    HevyAPIError,
    _flatten_api_workouts,
    extract_workouts,
)

# ── CSV path tests (existing, preserved) ─────────────


def test_extract_workouts_from_csv_file(tmp_path):
    """Test extracting from a valid CSV file via uploaded_file."""
    csv_file = tmp_path / "workouts.csv"

    df = pd.DataFrame(columns=EXPECTED_COLUMNS)
    df.loc[0] = ["Test"] * len(EXPECTED_COLUMNS)
    df.to_csv(csv_file, index=False)

    # Use uploaded_file to hit the CSV path
    with open(csv_file, "rb") as f:
        result = extract_workouts(uploaded_file=f)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert list(result.columns) == EXPECTED_COLUMNS


def test_extract_workouts_from_bytesio():
    """Test extracting from a Streamlit-like uploaded file object."""
    csv_data = ",".join(EXPECTED_COLUMNS) + "\n" + ",".join(["Test"] * len(EXPECTED_COLUMNS))
    uploaded_file = BytesIO(csv_data.encode("utf-8"))

    result = extract_workouts(uploaded_file=uploaded_file)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1


def test_extract_csv_missing_columns(tmp_path):
    """Test extraction raises ValueError if CSV columns are missing."""
    csv_file = tmp_path / "bad_workouts.csv"

    bad_cols = EXPECTED_COLUMNS[:-2]
    df = pd.DataFrame(columns=bad_cols)
    df.to_csv(csv_file, index=False)

    with open(csv_file, "rb") as f:
        with pytest.raises(ValueError, match="Missing expected columns"):
            extract_workouts(uploaded_file=f)


# ── API client tests ─────────────────────────────────


def test_hevy_client_missing_api_key():
    """Test HevyAPIClient raises clear error when no key is provided."""
    with pytest.raises(HevyAPIError, match="HEVY_API_KEY is not set"):
        HevyAPIClient(api_key="")


def test_hevy_client_fetch_all_workouts(requests_mock):
    """Test paginated fetch correctly aggregates across pages."""
    base = "https://api.hevyapp.com"

    # Page 1 of 2
    requests_mock.get(
        f"{base}/v1/workouts",
        [
            {
                "json": {
                    "page": 1,
                    "page_count": 2,
                    "workouts": [
                        {
                            "id": "aaa-111",
                            "title": "Push",
                            "start_time": "2024-06-01T10:00:00Z",
                            "end_time": "2024-06-01T11:00:00Z",
                            "exercises": [],
                        }
                    ],
                },
            },
            {
                "json": {
                    "page": 2,
                    "page_count": 2,
                    "workouts": [
                        {
                            "id": "bbb-222",
                            "title": "Pull",
                            "start_time": "2024-06-02T10:00:00Z",
                            "end_time": "2024-06-02T11:00:00Z",
                            "exercises": [],
                        }
                    ],
                },
            },
        ],
    )

    client = HevyAPIClient(api_key="test-key", request_delay=0)
    workouts = client.fetch_all_workouts()

    assert len(workouts) == 2
    assert workouts[0]["id"] == "aaa-111"
    assert workouts[1]["id"] == "bbb-222"


def test_hevy_client_retry_on_429(requests_mock):
    """Test client retries on 429 Too Many Requests."""
    base = "https://api.hevyapp.com"

    requests_mock.get(
        f"{base}/v1/workouts/count",
        [
            {"status_code": 429, "headers": {"Retry-After": "0"}},
            {"json": {"workout_count": 42}},
        ],
    )

    client = HevyAPIClient(api_key="test-key", request_delay=0)
    count = client.fetch_workout_count()
    assert count == 42


def test_hevy_client_error_on_401(requests_mock):
    """Test client raises HevyAPIError on 401 Unauthorized."""
    base = "https://api.hevyapp.com"

    requests_mock.get(
        f"{base}/v1/workouts/count",
        status_code=401,
        text="Unauthorized",
    )

    client = HevyAPIClient(api_key="bad-key", request_delay=0)
    with pytest.raises(HevyAPIError, match="401"):
        client.fetch_workout_count()


# ── Flattener tests ──────────────────────────────────


def test_flatten_api_workouts():
    """Test that nested API response is flattened to row-per-set DataFrame."""
    workouts = [
        {
            "id": "workout-uuid-1",
            "title": "Push Day",
            "start_time": "2024-06-01T10:00:00Z",
            "end_time": "2024-06-01T11:00:00Z",
            "description": "Chest focus",
            "exercises": [
                {
                    "title": "Bench Press (Barbell)",
                    "supersets_id": None,
                    "notes": "Good session",
                    "sets": [
                        {
                            "index": 0,
                            "type": "normal",
                            "weight_kg": 100,
                            "reps": 10,
                            "distance_meters": None,
                            "duration_seconds": None,
                            "rpe": 8.5,
                        },
                        {
                            "index": 1,
                            "type": "normal",
                            "weight_kg": 100,
                            "reps": 8,
                            "distance_meters": None,
                            "duration_seconds": None,
                            "rpe": 9.0,
                        },
                    ],
                },
                {
                    "title": "Push Up",
                    "supersets_id": None,
                    "notes": None,
                    "sets": [
                        {
                            "index": 0,
                            "type": "normal",
                            "weight_kg": None,
                            "reps": 20,
                            "distance_meters": None,
                            "duration_seconds": None,
                            "rpe": None,
                        },
                    ],
                },
            ],
        }
    ]

    df = _flatten_api_workouts(workouts)

    assert len(df) == 3  # 2 bench sets + 1 push-up set
    assert df.iloc[0]["workout_id"] == "workout-uuid-1"
    assert df.iloc[0]["exercise_title"] == "Bench Press (Barbell)"
    assert df.iloc[0]["weight_kg"] == 100
    assert df.iloc[0]["set_type"] == "normal"
    assert df.iloc[2]["exercise_title"] == "Push Up"
    assert pd.isna(df.iloc[2]["weight_kg"])


def test_flatten_api_workouts_empty():
    """Test that flattening an empty list returns an empty DataFrame."""
    df = _flatten_api_workouts([])
    assert len(df) == 0
    assert "workout_id" in df.columns


def test_flatten_distance_conversion():
    """Test that distance_meters is converted to distance_km."""
    workouts = [
        {
            "id": "w1",
            "title": "Run",
            "start_time": "2024-06-01T10:00:00Z",
            "end_time": "2024-06-01T11:00:00Z",
            "exercises": [
                {
                    "title": "Running",
                    "supersets_id": None,
                    "sets": [
                        {
                            "index": 0,
                            "type": "normal",
                            "weight_kg": None,
                            "reps": None,
                            "distance_meters": 5000,
                            "duration_seconds": 1800,
                            "rpe": None,
                        }
                    ],
                }
            ],
        }
    ]

    df = _flatten_api_workouts(workouts)
    assert df.iloc[0]["distance_km"] == 5.0
