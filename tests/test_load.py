from etl.load import load_to_supabase


def test_load_to_supabase_full_refresh(mocker, sample_clean_df):
    """Test full load mode (truncates tables)."""
    # Mock psycopg2 connect and cursor
    mock_connect = mocker.patch("etl.load.psycopg2.connect")
    mock_execute_values = mocker.patch("etl.load.execute_values")
    mock_conn = mock_connect.return_value
    mock_cursor = mock_conn.cursor.return_value.__enter__.return_value

    # Run load with incremental=False (default)
    stats = load_to_supabase(sample_clean_df, incremental=False)

    # Verify connection was made
    mock_connect.assert_called_once()

    # Verify cursor calls
    calls = [call.args[0] for call in mock_cursor.execute.call_args_list if call.args]

    # In full refresh, we should see TRUNCATE
    assert any("TRUNCATE TABLE workout_sets" in call for call in calls)

    # Verify execute_values was called for upserting
    assert mock_execute_values.called

    assert stats["total_rows"] == 3
    assert stats["new_workouts"] == 2  # 2 unique workout IDs in sample_clean_df
    assert stats["new_sets"] == 3
    assert stats["skipped_workouts"] == 0

    # Verify commit
    mock_conn.commit.assert_called()
    mock_conn.close.assert_called()


def test_load_to_supabase_incremental(mocker, sample_clean_df):
    """Test incremental load mode (skips existing)."""
    mock_connect = mocker.patch("etl.load.psycopg2.connect")
    mocker.patch("etl.load.execute_values")
    mock_conn = mock_connect.return_value
    mock_cursor = mock_conn.cursor.return_value.__enter__.return_value

    # Mock the existing workout IDs query to return one of our mock IDs
    # Our sample_clean_df has ["Legs_20240525180000", "Push_20240526100000"]
    mock_cursor.fetchall.return_value = [("Legs_20240525180000",)]

    # Run load with incremental=True
    stats = load_to_supabase(sample_clean_df, incremental=True)

    # Check SQL calls
    calls = [call.args[0] for call in mock_cursor.execute.call_args_list if call.args]

    # In incremental, we should NOT see TRUNCATE
    assert not any("TRUNCATE TABLE workout_sets" in call for call in calls)

    # Check stats
    assert stats["total_rows"] == 3
    # Since "Legs" was existing, it's skipped. "Push" is new.
    assert stats["new_workouts"] == 1
    assert stats["skipped_workouts"] == 1
    # Sets for "Push" only (2 sets)
    assert stats["new_sets"] == 2
