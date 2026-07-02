"""Tests for the main pipeline entry point."""

import pytest

import main


def test_main_incremental_mode(mocker, monkeypatch):
    """Test that main() in incremental mode calls run_incremental_sync."""
    monkeypatch.setattr("sys.argv", ["main.py", "--mode", "incremental"])

    mock_sync = mocker.patch("main.run_incremental_sync", return_value={"updated": 0, "deleted": 0})

    main.main()

    mock_sync.assert_called_once()


def test_main_full_mode(mocker, sample_raw_df, sample_clean_df, monkeypatch):
    """Test that main() in full mode calls extract, transform, and load."""
    monkeypatch.setattr("sys.argv", ["main.py", "--mode", "full"])

    mock_extract = mocker.patch("main.extract_workouts", return_value=sample_raw_df)
    mock_transform = mocker.patch("main.transform_workouts", return_value=sample_clean_df)
    mock_load = mocker.patch("main.load_to_supabase", return_value={"total_rows": 3})

    main.main()

    mock_extract.assert_called_once()
    mock_transform.assert_called_once_with(sample_raw_df)
    mock_load.assert_called_once_with(sample_clean_df)


def test_main_csv_mode(mocker, sample_raw_df, sample_clean_df, monkeypatch):
    """Test that main() in csv mode calls extract, transform, and load."""
    monkeypatch.setattr("sys.argv", ["main.py", "--mode", "csv"])

    mock_extract = mocker.patch("main.extract_workouts", return_value=sample_raw_df)
    mock_transform = mocker.patch("main.transform_workouts", return_value=sample_clean_df)
    mock_load = mocker.patch("main.load_to_supabase", return_value={"total_rows": 3})

    main.main()

    mock_extract.assert_called_once()
    mock_transform.assert_called_once_with(sample_raw_df)
    mock_load.assert_called_once_with(sample_clean_df)


def test_main_extract_failure(mocker, monkeypatch):
    """Test that main() handles extract failure gracefully."""
    monkeypatch.setattr("sys.argv", ["main.py", "--mode", "full"])
    mocker.patch("main.extract_workouts", side_effect=FileNotFoundError("No CSV found"))

    with pytest.raises(SystemExit) as exc_info:
        main.main()
    assert exc_info.value.code == 1


def test_main_default_mode_is_incremental(mocker, monkeypatch):
    """Test that default mode (no --mode flag) is incremental."""
    monkeypatch.setattr("sys.argv", ["main.py"])

    mock_sync = mocker.patch("main.run_incremental_sync", return_value={"updated": 0, "deleted": 0})

    main.main()

    mock_sync.assert_called_once()
