from io import BytesIO

import pandas as pd
import pytest
from config import EXPECTED_COLUMNS

from etl.extract import extract_workouts


def test_extract_workouts_from_file(tmp_path):
    """Test extracting from a valid CSV file."""
    # Create a temporary CSV file
    csv_file = tmp_path / "workouts.csv"

    # We only need required columns for the schema check
    df = pd.DataFrame(columns=EXPECTED_COLUMNS)
    df.loc[0] = ["Test"] * len(EXPECTED_COLUMNS)  # dummy data
    df.to_csv(csv_file, index=False)

    # Extract
    result = extract_workouts(csv_file)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert list(result.columns) == EXPECTED_COLUMNS


def test_extract_workouts_from_bytesio():
    """Test extracting from a Streamlit-like uploaded file object."""
    # Create a CSV in memory
    csv_data = ",".join(EXPECTED_COLUMNS) + "\n" + ",".join(["Test"] * len(EXPECTED_COLUMNS))
    uploaded_file = BytesIO(csv_data.encode("utf-8"))

    # Extract
    result = extract_workouts(uploaded_file=uploaded_file)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1


def test_extract_workouts_missing_columns(tmp_path):
    """Test extraction raises ValueError if columns are missing."""
    csv_file = tmp_path / "bad_workouts.csv"

    # Missing some required columns
    bad_cols = EXPECTED_COLUMNS[:-2]
    df = pd.DataFrame(columns=bad_cols)
    df.to_csv(csv_file, index=False)

    with pytest.raises(ValueError, match="Missing expected columns"):
        extract_workouts(csv_file)
