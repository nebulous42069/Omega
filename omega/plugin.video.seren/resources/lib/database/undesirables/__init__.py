"""Undesirables keyword filter database.

SQLite-backed user-configurable keyword blocklist for filtering unwanted release titles
during scraping. Ships with sensible defaults (Russian release groups, non-video files,
junk content like trailers/samples/soundtracks) and lets users add their own keywords,
toggle individual defaults on/off, and manage everything through Kodi dialogs.

Schema: keyword TEXT (PK), user_defined INTEGER (0=default, 1=user), enabled INTEGER (0/1)
"""

import collections

from resources.lib.common.source_utils import DEFAULT_UNDESIRABLES
from resources.lib.database import Database
from resources.lib.modules.globals import g

schema = {
    "undesirables": {
        "columns": collections.OrderedDict(
            [
                ("keyword", ["TEXT", "NOT NULL"]),
                ("user_defined", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("enabled", ["INTEGER", "NOT NULL", "DEFAULT 1"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY (keyword)"],
        "indices": [],
        "default_seed": [(kw, 0, 1) for kw in DEFAULT_UNDESIRABLES],
    }
}


class UndesirableCache(Database):
    """Persistent keyword blocklist for filtering release titles.

    Usage:
        uc = UndesirableCache()
        keywords = uc.get_enabled()          # list of active keyword strings
        uc.set_many([('cam', True, True)])    # add user keyword
        uc.remove_many(['cam'])               # remove keyword
    """

    def __init__(self):
        super().__init__(g.UNDESIRABLES_DB_PATH, schema)

    def get_enabled(self):
        """Return sorted list of all enabled keywords (both default and user-defined)."""
        try:
            results = self.fetchall(
                "SELECT keyword FROM undesirables WHERE enabled = 1"
            )
            return sorted(row["keyword"] for row in results) if results else []
        except Exception as e:
            g.log(f"UndesirableCache.get_enabled error: {e}", "warning")
            return list(DEFAULT_UNDESIRABLES)

    def get_defaults(self):
        """Return sorted list of default keywords (regardless of enabled state)."""
        try:
            results = self.fetchall(
                "SELECT keyword FROM undesirables WHERE user_defined = 0"
            )
            return sorted(row["keyword"] for row in results) if results else []
        except Exception as e:
            g.log(f"UndesirableCache.get_defaults error: {e}", "warning")
            return list(DEFAULT_UNDESIRABLES)

    def get_user_defined(self):
        """Return sorted list of user-added keywords."""
        try:
            results = self.fetchall(
                "SELECT keyword FROM undesirables WHERE user_defined = 1"
            )
            return sorted(row["keyword"] for row in results) if results else []
        except Exception as e:
            g.log(f"UndesirableCache.get_user_defined error: {e}", "warning")
            return []

    def get_defaults_with_state(self):
        """Return list of (keyword, enabled) tuples for all defaults."""
        try:
            results = self.fetchall(
                "SELECT keyword, enabled FROM undesirables WHERE user_defined = 0 "
                "ORDER BY keyword"
            )
            return [(row["keyword"], bool(row["enabled"])) for row in results] if results else []
        except Exception as e:
            g.log(f"UndesirableCache.get_defaults_with_state error: {e}", "warning")
            return [(kw, True) for kw in DEFAULT_UNDESIRABLES]

    def set_many(self, entries):
        """Insert or replace keyword entries.

        Args:
            entries: list of (keyword, user_defined, enabled) tuples
                     user_defined: bool/int, enabled: bool/int
        """
        if not entries:
            return
        try:
            for keyword, user_defined, enabled in entries:
                self.execute_sql(
                    "INSERT OR REPLACE INTO undesirables (keyword, user_defined, enabled) "
                    "VALUES (?, ?, ?)",
                    (keyword.lower().strip(), int(user_defined), int(enabled)),
                )
        except Exception as e:
            g.log(f"UndesirableCache.set_many error: {e}", "warning")

    def remove_many(self, keywords):
        """Delete keywords from the database.

        Args:
            keywords: list of keyword strings to remove
        """
        if not keywords:
            return
        try:
            for keyword in keywords:
                self.execute_sql(
                    "DELETE FROM undesirables WHERE keyword = ?",
                    (keyword,),
                )
        except Exception as e:
            g.log(f"UndesirableCache.remove_many error: {e}", "warning")

    def add_new_defaults(self):
        """Add any new default keywords that were introduced in an update.

        Only inserts keywords not already present (preserves user's enabled/disabled choices).
        """
        try:
            current = set(self.get_defaults())
            new_keywords = [kw for kw in DEFAULT_UNDESIRABLES if kw not in current]
            if new_keywords:
                self.set_many([(kw, False, True) for kw in new_keywords])
                g.log(f"UndesirableCache: Added {len(new_keywords)} new default keywords", "info")
        except Exception as e:
            g.log(f"UndesirableCache.add_new_defaults error: {e}", "warning")

    def clear_all(self):
        """Clear all entries and re-seed defaults."""
        try:
            self.execute_sql("DELETE FROM undesirables")
            self.set_many([(kw, False, True) for kw in DEFAULT_UNDESIRABLES])
            g.log("UndesirableCache: Reset to defaults", "info")
        except Exception as e:
            g.log(f"UndesirableCache.clear_all error: {e}", "warning")


def undesirables_select_defaults():
    """Show multi-select dialog to toggle individual default keywords on/off."""
    import xbmcgui

    uc = UndesirableCache()
    defaults_with_state = uc.get_defaults_with_state()
    if not defaults_with_state:
        g.notification(g.ADDON_NAME, "No default keywords found")
        return

    keywords = [item[0] for item in defaults_with_state]
    preselect = [i for i, item in enumerate(defaults_with_state) if item[1]]

    dialog = xbmcgui.Dialog()
    choices = dialog.multiselect(
        "Select Active Default Keywords",
        keywords,
        preselect=preselect,
    )
    if choices is None:
        return

    enabled_set = set(choices)
    new_settings = [(kw, False, i in enabled_set) for i, kw in enumerate(keywords)]
    uc.set_many(new_settings)
    g.notification(g.ADDON_NAME, f"{len(enabled_set)} defaults enabled")


def undesirables_user_input():
    """Show text input dialog to add user-defined keywords (comma-separated)."""
    import xbmcgui

    uc = UndesirableCache()
    user_defined = uc.get_user_defined()
    current_string = ",".join(user_defined) if user_defined else ""

    dialog = xbmcgui.Dialog()
    new_string = dialog.input(
        g.get_language_string(30700),
        defaultt=current_string,
    )
    if not new_string:
        return

    new_keywords = [kw.strip().lower() for kw in new_string.split(",") if kw.strip()]
    if not new_keywords:
        return

    new_settings = [(kw, True, True) for kw in new_keywords]
    uc.set_many(new_settings)
    g.notification(g.ADDON_NAME, f"{len(new_keywords)} user keywords saved")


def undesirables_user_remove():
    """Show multi-select dialog to remove user-defined keywords."""
    import xbmcgui

    uc = UndesirableCache()
    user_keywords = uc.get_user_defined()
    if not user_keywords:
        g.notification(g.ADDON_NAME, "No user keywords set")
        return

    dialog = xbmcgui.Dialog()
    choices = dialog.multiselect(
        "Select Keywords to Remove",
        user_keywords,
    )
    if choices is None:
        return

    removals = [user_keywords[i] for i in choices]
    uc.remove_many(removals)
    g.notification(g.ADDON_NAME, f"Removed {len(removals)} keywords")


def undesirables_user_remove_all():
    """Remove all user-defined keywords after confirmation."""
    import xbmcgui

    uc = UndesirableCache()
    user_keywords = uc.get_user_defined()
    if not user_keywords:
        g.notification(g.ADDON_NAME, "No user keywords set")
        return

    dialog = xbmcgui.Dialog()
    if not dialog.yesno(g.ADDON_NAME, f"Remove all {len(user_keywords)} user keywords?"):
        return

    uc.remove_many(user_keywords)
    g.notification(g.ADDON_NAME, "All user keywords removed")


def undesirables_reset_defaults():
    """Reset database to defaults (removes user keywords, re-enables all defaults)."""
    import xbmcgui

    dialog = xbmcgui.Dialog()
    if not dialog.yesno(g.ADDON_NAME, "Reset all undesirable keywords to defaults?\nThis removes user keywords and re-enables all defaults."):
        return

    UndesirableCache().clear_all()
    g.notification(g.ADDON_NAME, "Reset to defaults")
