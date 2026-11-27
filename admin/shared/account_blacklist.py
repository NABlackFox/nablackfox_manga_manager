
"""Fetch and locally cache the nhentai account blacklist."""

import json
import threading

import config
from admin.shared.nhentai_client import ApiError

CACHE_PATH = config.PROJECT_ROOT / "nhentai_blacklist.json"

_ids = set()
_lock = threading.Lock()


def load_cached():
    """Load the last saved blacklist."""
    global _ids

    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        values = data.get("ids", [])

        if not isinstance(values, list):
            raise ValueError("Invalid blacklist cache")

        ids = {
            value for value in values
            if isinstance(value, int) and not isinstance(value, bool)
        }

        with _lock:
            _ids = ids

        return True

    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def refresh(client):
    """Fetch the account blacklist and update the local cache."""

    global _ids

    if not client.has_key:
        load_cached()
        print("[BLACKLIST] No API key. Using local cache.")
        return False

    try:
        payload = client.request(
            "GET",
            "/blacklist/ids",
            group="detail"
        )

        if isinstance(payload, dict):
            payload = payload.get("ids", [])

        if not isinstance(payload, list):
            raise ValueError("Unexpected blacklist response")

        ids = {
            value for value in payload
            if isinstance(value, int) and not isinstance(value, bool)
        }

        temp_path = CACHE_PATH.with_name(CACHE_PATH.name + ".tmp")

        temp_path.write_text(
            json.dumps({"ids": sorted(ids)}, indent=2),
            encoding="utf-8"
        )

        temp_path.replace(CACHE_PATH)

        with _lock:
            _ids = ids

        print(f"[BLACKLIST] Updated successfully: {len(ids)} tags.")
        return True

    except (ApiError, OSError, ValueError, TypeError) as error:
        if load_cached():
            print(
                f"[BLACKLIST] Refresh failed: {error}. "
                "Using previous cache."
            )
        else:
            print(
                f"[BLACKLIST] Refresh failed: {error}. "
                "No local cache available."
            )

        return False


def get_ids():
    """Return a copy of the cached blacklist IDs."""
    with _lock:
        return set(_ids)
