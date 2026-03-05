"""Unit tests for client_profiles.py"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest
import client_profiles


@pytest.fixture(autouse=True)
def isolated_profiles(tmp_path):
    """Redirect _PROFILES_PATH to a temp file for every test."""
    tmp_file = str(tmp_path / "client_profiles.json")
    with patch.object(client_profiles, "_PROFILES_PATH", tmp_file):
        yield tmp_file


class TestLoadProfiles:
    def test_missing_file_returns_empty_dict(self):
        result = client_profiles.load_profiles()
        assert result == {}

    def test_loads_valid_json(self, isolated_profiles):
        data = {"42": {"employee_count": 100, "avg_hourly_rate": 75.0}}
        with open(isolated_profiles, "w") as f:
            json.dump(data, f)
        result = client_profiles.load_profiles()
        assert result == data

    def test_corrupt_json_returns_empty_dict(self, isolated_profiles):
        with open(isolated_profiles, "w") as f:
            f.write("not valid json {{{{")
        result = client_profiles.load_profiles()
        assert result == {}


class TestSaveProfiles:
    def test_writes_and_reads_back(self):
        data = {"7": {"employee_count": 50, "avg_hourly_rate": 60.0}}
        client_profiles.save_profiles(data)
        assert client_profiles.load_profiles() == data

    def test_overwrites_existing(self):
        client_profiles.save_profiles({"1": {"employee_count": 10, "avg_hourly_rate": 50.0}})
        client_profiles.save_profiles({"2": {"employee_count": 20, "avg_hourly_rate": 55.0}})
        result = client_profiles.load_profiles()
        assert "1" not in result
        assert "2" in result


class TestGetProfile:
    def test_missing_client_returns_defaults(self):
        result = client_profiles.get_profile(99)
        assert result == {"employee_count": 0, "avg_hourly_rate": 50}

    def test_existing_client_returns_stored_values(self):
        client_profiles.save_profiles(
            {"5": {"employee_count": 200, "avg_hourly_rate": 80.0}}
        )
        result = client_profiles.get_profile(5)
        assert result["employee_count"] == 200
        assert result["avg_hourly_rate"] == 80.0

    def test_client_id_coerced_to_string(self):
        client_profiles.save_profiles(
            {"123": {"employee_count": 30, "avg_hourly_rate": 45.0}}
        )
        # integer key should still match
        result = client_profiles.get_profile(123)
        assert result["employee_count"] == 30


class TestUpsertProfile:
    def test_inserts_new_profile(self):
        client_profiles.upsert_profile(10, 150, 90.0)
        result = client_profiles.get_profile(10)
        assert result["employee_count"] == 150
        assert result["avg_hourly_rate"] == 90.0

    def test_updates_existing_profile(self):
        client_profiles.upsert_profile(10, 100, 70.0)
        client_profiles.upsert_profile(10, 250, 95.0)
        result = client_profiles.get_profile(10)
        assert result["employee_count"] == 250
        assert result["avg_hourly_rate"] == 95.0

    def test_preserves_other_clients(self):
        client_profiles.upsert_profile(1, 50, 60.0)
        client_profiles.upsert_profile(2, 75, 65.0)
        assert client_profiles.get_profile(1)["employee_count"] == 50
        assert client_profiles.get_profile(2)["employee_count"] == 75
