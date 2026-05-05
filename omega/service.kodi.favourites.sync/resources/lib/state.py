import json
import os

from resources.lib.kodi_compat import now_iso


STATE_FILE = "sync_state.json"


def state_path(profile_dir):
    return os.path.join(profile_dir, STATE_FILE)


def load_state(profile_dir):
    path = state_path(profile_dir)
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}

    if not isinstance(data, dict):
        return {}
    return data


def save_state(profile_dir, state):
    path = state_path(profile_dir)
    payload = dict(state)
    payload["updated_at"] = now_iso()
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
