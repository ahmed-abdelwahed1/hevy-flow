import pytest

import main


def test_main_pipeline_success(mocker, sample_raw_df, sample_clean_df):
    """Test that main() calls extract, transform, and load in sequence."""

    # Mock the 3 ETL stages
    mock_extract = mocker.patch("main.extract_workouts", return_value=sample_raw_df)
    mock_transform = mocker.patch("main.transform_workouts", return_value=sample_clean_df)
    mock_load = mocker.patch("main.load_to_supabase", return_value={"total_rows": 3})

    # Run main wrapper
    main.main()

    # Verify sequence
    mock_extract.assert_called_once()
    mock_transform.assert_called_once_with(sample_raw_df)
    mock_load.assert_called_once_with(sample_clean_df)


def test_main_pipeline_extract_failure(mocker):
    """Test that main() handles extract failure gracefully or raises."""
    mocker.patch("main.extract_workouts", side_effect=FileNotFoundError("No CSV found"))

    # main catches exceptions natively and calls sys.exit(1)
    with pytest.raises(SystemExit) as exc_info:
        main.main()
    assert exc_info.value.code == 1
