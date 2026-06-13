import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_raw_df():
    """Returns a mock raw DataFrame simulating the CSV extracted from Hevy."""
    return pd.DataFrame(
        {
            "title": ["Legs", "Push", "Push"],
            "start_time": [
                "May 25, 2024, 06:00 PM",
                "May 26, 2024, 10:00 AM",
                "May 26, 2024, 10:00 AM",
            ],
            "end_time": [
                "May 25, 2024, 07:30 PM",
                "May 26, 2024, 11:15 AM",
                "May 26, 2024, 11:15 AM",
            ],
            "description": ["Leg day!", np.nan, np.nan],
            "exercise_title": ["Squat (Barbell)", "Bench Press", "Push Up"],
            "superset_id": [np.nan, np.nan, np.nan],
            "exercise_notes": [np.nan, np.nan, np.nan],
            "set_index": [0, 0, 1],
            "set_type": ["normal", "normal", "normal"],
            "weight_kg": [100.0, 80.0, np.nan],  # Push Up is bodyweight
            "reps": [8, 10, 20],
            "distance_km": [np.nan, np.nan, np.nan],
            "duration_seconds": [np.nan, np.nan, np.nan],
            "rpe": [8.0, 9.0, np.nan],
        }
    )


@pytest.fixture
def sample_clean_df():
    """Returns a mock clean DataFrame simulating the output of transform.py."""
    return pd.DataFrame(
        {
            "title": ["Legs", "Push", "Push"],
            "start_time": pd.to_datetime(
                ["2024-05-25 18:00", "2024-05-26 10:00", "2024-05-26 10:00"]
            ),
            "end_time": pd.to_datetime(
                ["2024-05-25 19:30", "2024-05-26 11:15", "2024-05-26 11:15"]
            ),
            "exercise_title": ["Squat (Barbell)", "Bench Press", "Push Up"],
            "superset_id": [np.nan, np.nan, np.nan],
            "set_index": [0, 0, 1],
            "set_type": ["normal", "normal", "normal"],
            "weight_kg": [100.0, 80.0, 0.0],
            "reps": [8, 10, 20],
            "duration_seconds": [0, 0, 0],
            "rpe": [8.0, 9.0, np.nan],
            "duration_minutes": [90.0, 75.0, 75.0],
            "day_of_week": ["Saturday", "Sunday", "Sunday"],
            "month": [5, 5, 5],
            "year": [2024, 2024, 2024],
            "date": ["2024-05-25", "2024-05-26", "2024-05-26"],
            "workout_id": ["Legs_20240525180000", "Push_20240526100000", "Push_20240526100000"],
            "is_bodyweight": [False, False, True],
            "is_timed": [False, False, False],
            "workout_category": ["Legs", "Push", "Push"],
        }
    )
