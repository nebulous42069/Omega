import time
import json

import xbmcaddon

from resources.lib.cache.cachedb import CacheDB  # <-- IMPORTING THE DB HANDLER

# --- CACHE TIME CONSTANTS (in seconds) ---
# Use a very large number for "Never Expire" since 0 could be treated as immediate expiration
NEVER_EXPIRE = 999999999  # Approx 31 years
# NOTE: If your platform supports a specific setting (like -1), use that.
# For SQLite timestamp comparison, a very large number is the safest "never expire" value.

CACHE_DURATION = {
    "CATEGORIES": 86400 * 30,  # 30 days
    "LIVE_STREAMS": 86400 * 30,  # 30 days
    "VOD_STREAMS": 86400 * 7,  # 14 days
    "SERIES_STREAMS": 86400 * 14,  # 14 days
    "SERIES_INFO": 86400 * 14,  # 14 days
    "TMDB_DATA": NEVER_EXPIRE,
}

ADDON = xbmcaddon.Addon()


class FetchCache:
    """
    Acts as the middleman, determining if data is cached/expired,
    and delegating read/write to the appropriate CacheDB instance.
    """

    def __init__(self):
        # Maps content type to its DB filename, duration key, and CacheDB instance
        self.db_map = {
            "categories": ("categories.db", "CATEGORIES"),
            "live": ("live_streams.db", "LIVE_STREAMS"),
            "vod": ("vod_streams.db", "VOD_STREAMS"),
            "series": ("series_streams.db", "SERIES_STREAMS"),
            "series_info": ("series_info.db", "SERIES_INFO"),
            "tmdb_data": ("tmdb_data.db", "TMDB_DATA"),
        }
        self.db_instances = {}
        self._initialize_instances()

    def _initialize_instances(self):
        """Initializes all CacheDB instances with server-specific filenames."""
        for content_type, (filename, _) in self.db_map.items():
            # CacheDB handles connection/table creation itself
            self.db_instances[content_type] = CacheDB(filename)

    def get(self, content_type, key):
        """
        Retrieves data, checks expiration, and returns deserialized data.
        :param content_type: Key from self.db_map (e.g., 'live_streams').
        :param key: Unique key for the content (e.g., category_id).
        :return: The deserialized data (list/dict) or None if expired or not found.
        """
        if content_type not in self.db_map:
            return None

        db_instance = self.db_instances[content_type]
        duration_key = self.db_map[content_type][1]
        duration = CACHE_DURATION[duration_key]

        raw_data = db_instance.get_raw(key)

        if raw_data is None:
            return None  # Key not found

        data_json, timestamp = raw_data

        # Check for expiration
        if time.time() - timestamp < duration:
            return json.loads(data_json)
        else:
            # Cache expired, delete it and return None
            db_instance.delete(key)
            return None

    def set(self, content_type, key, data):
        """
        Stores data using the underlying CacheDB instance.
        """
        if content_type not in self.db_map:
            return

        db_instance = self.db_instances[content_type]
        db_instance.set_raw(key, data)

    def close(self):
        """Closes all database connections."""
        for db in self.db_instances.values():
            db.close()


# Initialize a global instance for use in navigator.py
cache_handler = FetchCache()
