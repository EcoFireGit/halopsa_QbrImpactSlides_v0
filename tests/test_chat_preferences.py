"""Unit tests for chat_preferences.py"""

import json
import os
import pytest
import tempfile
from unittest.mock import patch

import chat_preferences
from chat_preferences import (
    load_preferences,
    save_preferences,
    get_ai_settings,
    update_ai_settings,
    get_client_industry,
    set_client_industry,
    get_msp_contact,
    set_msp_contact,
)


@pytest.fixture(autouse=True)
def isolated_prefs_file(tmp_path, monkeypatch):
    """Redirect _PREFS_PATH to a temp file for each test."""
    prefs_file = str(tmp_path / "chat_preferences.json")
    monkeypatch.setattr(chat_preferences, "_PREFS_PATH", prefs_file)
    yield prefs_file


# ── load_preferences ─────────────────────────────────────────────────


class TestLoadPreferences:
    def test_returns_defaults_when_file_absent(self):
        result = load_preferences()
        assert "ai_settings" in result
        assert "client_industries" in result

    def test_default_ai_settings_values(self):
        result = load_preferences()
        ai = result["ai_settings"]
        assert ai["use_ai"] is True
        assert ai["num_recs"] == 3
        assert ai["sample_size"] == 100

    def test_default_client_industries_empty(self):
        result = load_preferences()
        assert result["client_industries"] == {}

    def test_loads_existing_file(self, isolated_prefs_file):
        data = {
            "ai_settings": {"use_ai": False, "num_recs": 5, "sample_size": 200},
            "client_industries": {"1": "Healthcare & Social Assistance"},
        }
        with open(isolated_prefs_file, "w") as f:
            json.dump(data, f)
        result = load_preferences()
        assert result["ai_settings"]["use_ai"] is False
        assert result["ai_settings"]["num_recs"] == 5
        assert result["client_industries"]["1"] == "Healthcare & Social Assistance"

    def test_corrupt_json_returns_defaults(self, isolated_prefs_file):
        with open(isolated_prefs_file, "w") as f:
            f.write("{ invalid json }")
        result = load_preferences()
        assert result["ai_settings"]["use_ai"] is True

    def test_missing_ai_settings_key_filled_with_defaults(self, isolated_prefs_file):
        data = {"client_industries": {}}
        with open(isolated_prefs_file, "w") as f:
            json.dump(data, f)
        result = load_preferences()
        assert "ai_settings" in result
        assert result["ai_settings"]["num_recs"] == 3

    def test_missing_client_industries_key_filled(self, isolated_prefs_file):
        data = {"ai_settings": {"use_ai": True, "num_recs": 3, "sample_size": 100}}
        with open(isolated_prefs_file, "w") as f:
            json.dump(data, f)
        result = load_preferences()
        assert "client_industries" in result
        assert result["client_industries"] == {}


# ── save_preferences ─────────────────────────────────────────────────


class TestSavePreferences:
    def test_saves_and_reloads(self, isolated_prefs_file):
        prefs = {
            "ai_settings": {"use_ai": False, "num_recs": 7, "sample_size": 300},
            "client_industries": {"42": "Finance & Insurance"},
        }
        save_preferences(prefs)
        with open(isolated_prefs_file, "r") as f:
            reloaded = json.load(f)
        assert reloaded["ai_settings"]["num_recs"] == 7
        assert reloaded["client_industries"]["42"] == "Finance & Insurance"

    def test_file_created_after_save(self, isolated_prefs_file):
        assert not os.path.exists(isolated_prefs_file)
        save_preferences({"ai_settings": {}, "client_industries": {}})
        assert os.path.exists(isolated_prefs_file)


# ── get_ai_settings ──────────────────────────────────────────────────


class TestGetAiSettings:
    def test_returns_defaults_when_no_file(self):
        result = get_ai_settings()
        assert result["use_ai"] is True
        assert result["num_recs"] == 3
        assert result["sample_size"] == 100

    def test_returns_saved_values(self, isolated_prefs_file):
        data = {
            "ai_settings": {"use_ai": False, "num_recs": 8, "sample_size": 250},
            "client_industries": {},
        }
        with open(isolated_prefs_file, "w") as f:
            json.dump(data, f)
        result = get_ai_settings()
        assert result["use_ai"] is False
        assert result["num_recs"] == 8
        assert result["sample_size"] == 250

    def test_fills_missing_keys_with_defaults(self, isolated_prefs_file):
        data = {"ai_settings": {"use_ai": True}, "client_industries": {}}
        with open(isolated_prefs_file, "w") as f:
            json.dump(data, f)
        result = get_ai_settings()
        assert "num_recs" in result
        assert "sample_size" in result


# ── update_ai_settings ───────────────────────────────────────────────


class TestUpdateAiSettings:
    def test_update_use_ai(self):
        result = update_ai_settings(use_ai=False)
        assert result["use_ai"] is False

    def test_update_use_ai_to_true(self):
        update_ai_settings(use_ai=False)
        result = update_ai_settings(use_ai=True)
        assert result["use_ai"] is True

    def test_update_num_recs(self):
        result = update_ai_settings(num_recs=5)
        assert result["num_recs"] == 5

    def test_num_recs_clamped_to_min(self):
        result = update_ai_settings(num_recs=0)
        assert result["num_recs"] == 1

    def test_num_recs_clamped_to_max(self):
        result = update_ai_settings(num_recs=99)
        assert result["num_recs"] == 10

    def test_update_sample_size(self):
        result = update_ai_settings(sample_size=200)
        assert result["sample_size"] == 200

    def test_sample_size_clamped_to_min(self):
        result = update_ai_settings(sample_size=1)
        assert result["sample_size"] == 10

    def test_sample_size_clamped_to_max(self):
        result = update_ai_settings(sample_size=9999)
        assert result["sample_size"] == 500

    def test_none_values_not_updated(self):
        # Set to known state
        update_ai_settings(num_recs=4, sample_size=150)
        # Call with None — should not change anything
        result = update_ai_settings(use_ai=None, num_recs=None, sample_size=None)
        assert result["num_recs"] == 4
        assert result["sample_size"] == 150

    def test_partial_update_preserves_others(self):
        update_ai_settings(use_ai=False, num_recs=7, sample_size=300)
        result = update_ai_settings(num_recs=2)
        assert result["use_ai"] is False
        assert result["num_recs"] == 2
        assert result["sample_size"] == 300

    def test_persists_to_file(self, isolated_prefs_file):
        update_ai_settings(num_recs=6)
        with open(isolated_prefs_file, "r") as f:
            data = json.load(f)
        assert data["ai_settings"]["num_recs"] == 6


# ── get_client_industry / set_client_industry ────────────────────────


class TestClientIndustry:
    def test_returns_none_for_unknown_client(self):
        result = get_client_industry(99)
        assert result is None

    def test_set_and_get_industry(self):
        set_client_industry(1, "Finance & Insurance")
        result = get_client_industry(1)
        assert result == "Finance & Insurance"

    def test_overwrite_existing(self):
        set_client_industry(1, "Finance & Insurance")
        set_client_industry(1, "Healthcare & Social Assistance")
        result = get_client_industry(1)
        assert result == "Healthcare & Social Assistance"

    def test_different_clients_independent(self):
        set_client_industry(10, "Finance & Insurance")
        set_client_industry(20, "Manufacturing")
        assert get_client_industry(10) == "Finance & Insurance"
        assert get_client_industry(20) == "Manufacturing"

    def test_client_id_stored_as_string(self):
        set_client_industry(42, "Retail Trade")
        result = get_client_industry("42")
        assert result == "Retail Trade"

    def test_persists_to_file(self, isolated_prefs_file):
        set_client_industry(5, "Construction")
        with open(isolated_prefs_file, "r") as f:
            data = json.load(f)
        assert data["client_industries"]["5"] == "Construction"


# ── get_msp_contact / set_msp_contact ───────────────────────────────


class TestMspContact:
    def test_returns_none_when_not_set(self):
        result = get_msp_contact()
        assert result is None

    def test_set_and_get(self):
        set_msp_contact("Jane Doe | jdoe@msp.com | (555) 123-4567")
        result = get_msp_contact()
        assert result == "Jane Doe | jdoe@msp.com | (555) 123-4567"

    def test_overwrite(self):
        set_msp_contact("Old Contact")
        set_msp_contact("New Contact | new@msp.com")
        result = get_msp_contact()
        assert result == "New Contact | new@msp.com"

    def test_persists_to_file(self, isolated_prefs_file):
        set_msp_contact("Bob Smith | bob@msp.com")
        with open(isolated_prefs_file, "r") as f:
            data = json.load(f)
        assert data["msp_contact"] == "Bob Smith | bob@msp.com"

    def test_empty_string_stored(self):
        set_msp_contact("")
        result = get_msp_contact()
        assert result == ""
