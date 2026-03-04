"""
client_profiles.py
JSON persistence for per-client employee count and average hourly rate.
Stored in client_profiles.json (gitignored).
"""

import json
import os
import tempfile

_PROFILES_PATH = os.path.join(os.path.dirname(__file__), "client_profiles.json")


def load_profiles() -> dict:
    """Read client_profiles.json; return {} if absent or corrupt."""
    if not os.path.exists(_PROFILES_PATH):
        return {}
    try:
        with open(_PROFILES_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_profiles(profiles: dict) -> None:
    """Write profiles atomically via os.replace() on a temp file."""
    dir_name = os.path.dirname(_PROFILES_PATH) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(profiles, f, indent=2)
        os.replace(tmp_path, _PROFILES_PATH)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def get_profile(client_id) -> dict:
    """Return profile for client_id, or defaults if not found."""
    profiles = load_profiles()
    return profiles.get(str(client_id), {"employee_count": 0, "avg_hourly_rate": 50})


def upsert_profile(client_id, employee_count: int, avg_hourly_rate: float) -> None:
    """Load, update, and save the profile for a single client."""
    profiles = load_profiles()
    profiles[str(client_id)] = {
        "employee_count": employee_count,
        "avg_hourly_rate": avg_hourly_rate,
    }
    save_profiles(profiles)
