"""Tests for the incremental sync orchestrator (etl/sync.py)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from etl.sync import run_incremental_sync


@pytest.fixture
def _mock_db_and_api(mocker):
    """Mock database and API interactions for sync tests."""
    # Mock psycopg2.connect
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mocker.patch("etl.sync.psycopg2.connect", return_value=mock_conn)
    mocker.patch("etl.sync.DATABASE_URL", "postgresql://test:test@localhost/test")

    return mock_conn, mock_cursor


def test_incremental_sync_no_events(_mock_db_and_api, mocker):
    """Test sync with no new events reports 0 updated, 0 deleted."""
    mock_conn, mock_cursor = _mock_db_and_api

    mocker.patch("etl.sync._create_tables")
    mocker.patch("etl.sync.get_last_sync", return_value=datetime(2024, 6, 1, tzinfo=timezone.utc))
    mocker.patch("etl.sync.set_last_sync")

    # Mock API client that returns no events
    mock_client = MagicMock()
    mock_client.fetch_workout_events.return_value = ([], [])
    mocker.patch("etl.sync.HevyAPIClient", return_value=mock_client)

    stats = run_incremental_sync()

    assert stats["updated"] == 0
    assert stats["deleted"] == 0


def test_incremental_sync_with_deletions(_mock_db_and_api, mocker):
    """Test sync correctly delegates deletion to delete_workouts."""
    mock_conn, mock_cursor = _mock_db_and_api

    mocker.patch("etl.sync._create_tables")
    mocker.patch("etl.sync.get_last_sync", return_value=None)
    mocker.patch("etl.sync.set_last_sync")

    mock_delete = mocker.patch("etl.sync.delete_workouts", return_value=2)

    mock_client = MagicMock()
    mock_client.fetch_workout_events.return_value = ([], ["id-1", "id-2"])
    mocker.patch("etl.sync.HevyAPIClient", return_value=mock_client)

    stats = run_incremental_sync()

    assert stats["deleted"] == 2
    mock_delete.assert_called_once()


def test_incremental_sync_with_updates(_mock_db_and_api, mocker):
    """Test sync correctly flattens, transforms, and loads updated workouts."""
    mock_conn, mock_cursor = _mock_db_and_api

    mocker.patch("etl.sync._create_tables")
    mocker.patch("etl.sync.get_last_sync", return_value=None)
    mocker.patch("etl.sync.set_last_sync")

    updated_workout = {
        "id": "w-updated-1",
        "title": "Push",
        "start_time": "2024-06-01T10:00:00Z",
        "end_time": "2024-06-01T11:00:00Z",
        "exercises": [
            {
                "title": "Bench Press",
                "supersets_id": None,
                "sets": [
                    {
                        "index": 0,
                        "type": "normal",
                        "weight_kg": 100,
                        "reps": 10,
                        "distance_meters": None,
                        "duration_seconds": None,
                        "rpe": 8.0,
                    }
                ],
            }
        ],
    }

    mock_client = MagicMock()
    mock_client.fetch_workout_events.return_value = ([updated_workout], [])
    mocker.patch("etl.sync.HevyAPIClient", return_value=mock_client)

    mock_load_workouts = mocker.patch("etl.sync._load_workouts")
    mock_insert_sets = mocker.patch("etl.sync._insert_sets")

    # _prepare_workouts_df and _prepare_sets_df need to return DataFrames
    mocker.patch(
        "etl.sync._prepare_workouts_df",
        return_value=pd.DataFrame({"workout_id": ["w-updated-1"]}),
    )
    mocker.patch(
        "etl.sync._prepare_sets_df",
        return_value=pd.DataFrame({"workout_id": ["w-updated-1"], "set_index": [0]}),
    )

    stats = run_incremental_sync()

    assert stats["updated"] == 1
    mock_load_workouts.assert_called_once()
    mock_insert_sets.assert_called_once()


def test_incremental_sync_no_database_url(mocker):
    """Test sync raises ConnectionError when DATABASE_URL is missing."""
    mocker.patch("etl.sync.DATABASE_URL", "")

    with pytest.raises(ConnectionError, match="DATABASE_URL is not set"):
        run_incremental_sync()
