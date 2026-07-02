import pandas as pd

from etl.transform import transform_workouts


def test_transform_workouts_logic(sample_raw_df):
    """Test all transformations on a sample raw dataframe."""
    clean_df = transform_workouts(sample_raw_df)

    # 1. Check datatypes
    assert pd.api.types.is_datetime64_any_dtype(clean_df["start_time"])
    assert pd.api.types.is_datetime64_any_dtype(clean_df["end_time"])

    # 2. Check derived columns
    assert "duration_minutes" in clean_df.columns
    assert "day_of_week" in clean_df.columns
    assert "month" in clean_df.columns
    assert "year" in clean_df.columns
    assert "workout_id" in clean_df.columns
    assert "is_bodyweight" in clean_df.columns
    assert "is_timed" in clean_df.columns
    assert "workout_category" in clean_df.columns

    # 3. Check specific derived values
    # Legs (index 0): 18:00 to 19:30 = 90 mins
    assert clean_df.iloc[0]["duration_minutes"] == 90.0

    # Push Up (index 2): missing weight_kg should be set to 0.0 and is_bodyweight=True
    assert clean_df.iloc[2]["weight_kg"] == 0.0
    assert clean_df.iloc[2]["is_bodyweight"]

    # Squat (index 0): 100.0 kg is not bodyweight
    assert clean_df.iloc[0]["weight_kg"] == 100.0
    assert not clean_df.iloc[0]["is_bodyweight"]


def test_transform_workout_category_normalization():
    """Test that titles are properly categorized."""
    df = pd.DataFrame(
        {
            "title": ["Pull", "Push", "LEGS", "Upper Body", "Lower Body", "Evening workout 🏋️"],
            "start_time": ["May 25, 2024, 06:00 PM"] * 6,
            "end_time": ["May 25, 2024, 07:30 PM"] * 6,
            "description": [None] * 6,
            "exercise_title": ["Test"] * 6,
            "superset_id": [None] * 6,
            "exercise_notes": [None] * 6,
            "set_index": [0] * 6,
            "set_type": ["normal"] * 6,
            "weight_kg": [10.0] * 6,
            "reps": [10] * 6,
            "distance_km": [None] * 6,
            "duration_seconds": [None] * 6,
            "rpe": [8.0] * 6,
        }
    )

    clean_df = transform_workouts(df)
    categories = clean_df["workout_category"].tolist()

    assert categories == ["Pull", "Push", "Legs", "Upper", "Lower", "Full Body"]


def test_transform_iso8601_datetimes():
    """Test that ISO 8601 timestamps (API path) are parsed correctly."""
    df = pd.DataFrame(
        {
            "title": ["Push"],
            "start_time": ["2024-06-01T10:00:00Z"],
            "end_time": ["2024-06-01T11:30:00Z"],
            "exercise_title": ["Bench Press"],
            "superset_id": [None],
            "set_index": [0],
            "set_type": ["normal"],
            "weight_kg": [100.0],
            "reps": [10],
            "duration_seconds": [None],
            "rpe": [8.0],
        }
    )

    clean_df = transform_workouts(df)

    assert pd.api.types.is_datetime64_any_dtype(clean_df["start_time"])
    assert clean_df.iloc[0]["duration_minutes"] == 90.0
    assert clean_df.iloc[0]["day_of_week"] == "Saturday"


def test_transform_skips_workout_id_when_present():
    """Test that workout_id generation is skipped when already populated (API path)."""
    df = pd.DataFrame(
        {
            "workout_id": ["uuid-from-api-123"],
            "title": ["Pull"],
            "start_time": ["2024-06-02T10:00:00Z"],
            "end_time": ["2024-06-02T11:15:00Z"],
            "exercise_title": ["Pull Up"],
            "superset_id": [None],
            "set_index": [0],
            "set_type": ["normal"],
            "weight_kg": [None],
            "reps": [15],
            "duration_seconds": [None],
            "rpe": [None],
        }
    )

    clean_df = transform_workouts(df)

    # UUID should be preserved, not overwritten by the md5 hash
    assert clean_df.iloc[0]["workout_id"] == "uuid-from-api-123"
