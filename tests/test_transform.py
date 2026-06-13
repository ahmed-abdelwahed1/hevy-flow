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
