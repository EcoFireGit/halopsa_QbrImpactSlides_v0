"""
chat_preferences.py
Cross-session persistence for AI settings and per-client industry sector.
Stored in chat_preferences.json (gitignored).
"""

import json
import os
import tempfile

_PREFS_PATH = os.path.join(os.path.dirname(__file__), "chat_preferences.json")

_DEFAULT_AI_SETTINGS = {
    "use_ai": True,
    "num_recs": 3,
    "sample_size": 100,
}


def load_preferences() -> dict:
    """Read chat_preferences.json; return defaults if absent or corrupt."""
    if not os.path.exists(_PREFS_PATH):
        return {"ai_settings": dict(_DEFAULT_AI_SETTINGS), "client_industries": {}}
    try:
        with open(_PREFS_PATH, "r") as f:
            data = json.load(f)
        # Ensure required keys exist
        if "ai_settings" not in data:
            data["ai_settings"] = dict(_DEFAULT_AI_SETTINGS)
        if "client_industries" not in data:
            data["client_industries"] = {}
        return data
    except (json.JSONDecodeError, OSError):
        return {"ai_settings": dict(_DEFAULT_AI_SETTINGS), "client_industries": {}}


def save_preferences(prefs: dict) -> None:
    """Write preferences atomically via os.replace() on a temp file."""
    dir_name = os.path.dirname(_PREFS_PATH) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(prefs, f, indent=2)
        os.replace(tmp_path, _PREFS_PATH)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def get_ai_settings() -> dict:
    """Return current AI settings dict with keys: use_ai, num_recs, sample_size."""
    prefs = load_preferences()
    settings = prefs.get("ai_settings", {})
    # Fill missing keys with defaults
    for k, v in _DEFAULT_AI_SETTINGS.items():
        if k not in settings:
            settings[k] = v
    return settings


def update_ai_settings(
    use_ai: bool | None = None,
    num_recs: int | None = None,
    sample_size: int | None = None,
) -> dict:
    """Update AI settings, saving only provided values. Returns updated settings."""
    prefs = load_preferences()
    settings = prefs.get("ai_settings", dict(_DEFAULT_AI_SETTINGS))
    if use_ai is not None:
        settings["use_ai"] = use_ai
    if num_recs is not None:
        settings["num_recs"] = max(1, min(10, num_recs))
    if sample_size is not None:
        settings["sample_size"] = max(10, min(500, sample_size))
    prefs["ai_settings"] = settings
    save_preferences(prefs)
    return settings


def get_client_industry(client_id) -> str | None:
    """Return persisted industry name for a client, or None."""
    prefs = load_preferences()
    return prefs.get("client_industries", {}).get(str(client_id))


def set_client_industry(client_id, industry_name: str) -> None:
    """Persist industry sector for a client."""
    prefs = load_preferences()
    prefs.setdefault("client_industries", {})[str(client_id)] = industry_name
    save_preferences(prefs)


def get_msp_contact() -> str | None:
    """Return persisted MSP contact info, or None."""
    prefs = load_preferences()
    return prefs.get("msp_contact")


def set_msp_contact(contact: str) -> None:
    """Persist MSP contact info."""
    prefs = load_preferences()
    prefs["msp_contact"] = contact
    save_preferences(prefs)
