import sqlite3
import xbmcaddon
import os
import json
import time
import xbmcvfs  # <--- NEW IMPORT: Use xbmcvfs for modern path translation

ADDON = xbmcaddon.Addon()

# 1. Get the pseudo-path (e.g., 'special://profile/addon_data/...')
PROFILE_PATH = ADDON.getAddonInfo("profile")

# 2. FIX: Use xbmcvfs.translatePath to convert the pseudo-path
#    into a valid system path (e.g., 'C:\Users\...\...')
ADDON_PROFILE = xbmcvfs.translatePath(PROFILE_PATH)

CACHE_DIR = os.path.join(ADDON_PROFILE, "cache")

# Ensure the profile directory exists
if not os.path.exists(ADDON_PROFILE):
    # This should now succeed with the translated path
    try:
        os.makedirs(ADDON_PROFILE)
    except Exception:
        # Include a fallback/pass just in case of race conditions, but this is less likely to fail now.
        pass

if not os.path.exists(CACHE_DIR):
    try:
        os.makedirs(CACHE_DIR)
    except Exception:
        pass


class CacheDB:
    def __init__(self, filename):
        self.db_path = os.path.join(CACHE_DIR, filename)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        """Creates the generic cache table if it doesn't exist."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_data (
                key TEXT PRIMARY KEY,
                data TEXT,
                timestamp INTEGER
            )
        """
        )
        self.conn.commit()

    def get_raw(self, key):
        """
        Retrieves the raw JSON data and timestamp.
        :return: (data_json, timestamp) or None.
        """
        try:
            self.cursor.execute(
                "SELECT data, timestamp FROM cache_data WHERE key=?", (key,)
            )
            row = self.cursor.fetchone()

            if row:
                return row[0], row[1]
            return None
        except Exception:
            return None

    def set_raw(self, key, data):
        """
        Stores data with the current timestamp.
        :param data: The Python object (list/dict) to be JSON serialized.
        """
        try:
            data_json = json.dumps(data)
            timestamp = int(time.time())

            self.cursor.execute(
                "REPLACE INTO cache_data (key, data, timestamp) VALUES (?, ?, ?)",
                (key, data_json, timestamp),
            )
            self.conn.commit()
        except Exception:
            pass

    def delete(self, key):
        """Deletes a specific key from the cache."""
        try:
            self.cursor.execute("DELETE FROM cache_data WHERE key=?", (key,))
            self.conn.commit()
        except Exception:
            pass

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
