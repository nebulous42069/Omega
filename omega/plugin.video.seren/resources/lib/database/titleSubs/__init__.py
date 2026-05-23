"""Title Substitution database.

SQLite-backed user-configurable title mapping for overriding scraper search titles.
Maps problematic titles to search-friendly alternatives — useful for anime titles
(Japanese → Romanized), shows with special characters, and regional title differences.

Schema: original_title TEXT (PK, stored lowercase), substitute_title TEXT NOT NULL
"""

import collections

from resources.lib.database import Database
from resources.lib.modules.globals import g

# Default title substitutions: entries that smart search + auto-clean can't handle.
#
# Smart search covers: anime Japanese→English (AniList + MAL), special chars (auto-clean).
# Title subs covers: abbreviations, franchise prefix removal, ampersand→"and", short names.
#
# Format: (original_title_lowercase, substitute_title)
DEFAULT_TITLE_SUBS = [
    # --- Abbreviations: torrent sites use the short name ---
    ("csi: crime scene investigation", "CSI"),
    ("csi: miami", "CSI Miami"),
    ("csi: ny", "CSI NY"),
    ("csi: vegas", "CSI Vegas"),
    ("marvel's agents of s.h.i.e.l.d.", "Agents of SHIELD"),
    ("law & order: special victims unit", "Law and Order SVU"),
    ("law & order: organized crime", "Law and Order Organized Crime"),
    ("law & order", "Law and Order"),
    # --- Franchise prefix removal: uploaders drop the franchise name ---
    ("star wars: andor", "Andor"),
    ("star wars: ahsoka", "Ahsoka"),
    ("star wars: the book of boba fett", "Book of Boba Fett"),
    ("star wars: obi-wan kenobi", "Obi-Wan Kenobi"),
    ("star wars: the acolyte", "The Acolyte"),
    ("star wars: skeleton crew", "Skeleton Crew"),
    ("the lord of the rings: the rings of power", "Rings of Power"),
    ("dc's legends of tomorrow", "Legends of Tomorrow"),
    ("marvel's runaways", "Runaways"),
    ("marvel's luke cage", "Luke Cage"),
    ("marvel's jessica jones", "Jessica Jones"),
    ("marvel's iron fist", "Iron Fist"),
    ("marvel's the punisher", "The Punisher"),
    ("marvel's cloak & dagger", "Cloak and Dagger"),
    # --- Article/possessive removal: "The" or "'s" changes the search ---
    ("the handmaid's tale", "Handmaids Tale"),
    ("the d'amelio show", "Damelio Show"),
    # --- Ampersand → "and" (auto-clean strips & entirely, doesn't replace) ---
    ("penn & teller: fool us", "Penn and Teller Fool Us"),
    ("mike & molly", "Mike and Molly"),
    ("will & grace", "Will and Grace"),
    ("drake & josh", "Drake and Josh"),
]

schema = {
    "title_subs": {
        "columns": collections.OrderedDict(
            [
                ("original_title", ["TEXT", "NOT NULL"]),
                ("substitute_title", ["TEXT", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["PRIMARY KEY (original_title)"],
        "indices": [],
        "default_seed": [],
    }
}


class TitleSubsCache(Database):
    """Persistent title substitution database.

    Usage:
        ts = TitleSubsCache()
        alt = ts.get_substitute("Law & Order: SVU")  # returns "Law and Order SVU" or None
        ts.set_substitute("Law & Order: SVU", "Law and Order SVU")
        ts.remove("law & order: svu")
        all_subs = ts.get_all()  # list of {"original_title": ..., "substitute_title": ...}
    """

    _cache = None

    def __init__(self):
        super().__init__(g.TITLE_SUBS_DB_PATH, schema)
        self._seed_defaults_if_empty()
        if TitleSubsCache._cache is None:
            self._load_cache()

    def _seed_defaults_if_empty(self):
        """Seed default substitutions on first use (empty DB only)."""
        try:
            count = self.fetchone("SELECT COUNT(*) as cnt FROM title_subs")
            if count and count["cnt"] == 0:
                for orig, sub in DEFAULT_TITLE_SUBS:
                    self.execute_sql(
                        "INSERT OR IGNORE INTO title_subs (original_title, substitute_title) VALUES (?, ?)",
                        (orig, sub),
                    )
                g.log(f"TitleSubsCache: Seeded {len(DEFAULT_TITLE_SUBS)} default substitutions", "info")
        except Exception as e:
            g.log(f"TitleSubsCache._seed_defaults_if_empty error: {e}", "warning")

    def _load_cache(self):
        """Load all substitutions into memory for fast lookup during scraping."""
        try:
            results = self.fetchall("SELECT original_title, substitute_title FROM title_subs")
            TitleSubsCache._cache = {row["original_title"]: row["substitute_title"] for row in results} if results else {}
        except Exception as e:
            g.log(f"TitleSubsCache._load_cache error: {e}", "warning")
            TitleSubsCache._cache = {}

    @classmethod
    def invalidate_cache(cls):
        """Force cache reload on next access."""
        cls._cache = None

    def get_substitute(self, title):
        """Look up a title substitution. Returns the substitute or None if not found.

        Args:
            title: Original title string (case-insensitive lookup)
        Returns:
            Substitute title string, or None if no substitution exists
        """
        if TitleSubsCache._cache is None:
            self._load_cache()
        return TitleSubsCache._cache.get(title.lower().strip()) if title else None

    def get_all(self):
        """Return list of all substitutions as dicts with original_title and substitute_title."""
        try:
            results = self.fetchall(
                "SELECT original_title, substitute_title FROM title_subs ORDER BY original_title"
            )
            return results if results else []
        except Exception as e:
            g.log(f"TitleSubsCache.get_all error: {e}", "warning")
            return []

    def set_substitute(self, original_title, substitute_title):
        """Add or update a title substitution.

        Args:
            original_title: The problematic title (stored lowercase)
            substitute_title: The search-friendly replacement
        """
        if not original_title or not substitute_title:
            return
        try:
            self.execute_sql(
                "INSERT OR REPLACE INTO title_subs (original_title, substitute_title) VALUES (?, ?)",
                (original_title.lower().strip(), substitute_title.strip()),
            )
            self.invalidate_cache()
        except Exception as e:
            g.log(f"TitleSubsCache.set_substitute error: {e}", "warning")

    def remove(self, original_title):
        """Remove a title substitution.

        Args:
            original_title: The original title key to remove (case-insensitive)
        """
        if not original_title:
            return
        try:
            self.execute_sql(
                "DELETE FROM title_subs WHERE original_title = ?",
                (original_title.lower().strip(),),
            )
            self.invalidate_cache()
        except Exception as e:
            g.log(f"TitleSubsCache.remove error: {e}", "warning")

    def remove_many(self, titles):
        """Remove multiple title substitutions.

        Args:
            titles: list of original title strings to remove
        """
        if not titles:
            return
        try:
            for title in titles:
                self.execute_sql(
                    "DELETE FROM title_subs WHERE original_title = ?",
                    (title.lower().strip(),),
                )
            self.invalidate_cache()
        except Exception as e:
            g.log(f"TitleSubsCache.remove_many error: {e}", "warning")

    def add_new_defaults(self):
        """Add any new default substitutions that were introduced in an update.

        Only inserts entries not already present (preserves user edits to existing defaults).
        """
        try:
            current = {row["original_title"] for row in self.get_all()}
            new_entries = [(orig, sub) for orig, sub in DEFAULT_TITLE_SUBS if orig not in current]
            if new_entries:
                for orig, sub in new_entries:
                    self.execute_sql(
                        "INSERT OR IGNORE INTO title_subs (original_title, substitute_title) VALUES (?, ?)",
                        (orig, sub),
                    )
                self.invalidate_cache()
                g.log(f"TitleSubsCache: Added {len(new_entries)} new default substitutions", "info")
        except Exception as e:
            g.log(f"TitleSubsCache.add_new_defaults error: {e}", "warning")

    def clear_all(self):
        """Delete all substitutions and re-seed defaults."""
        try:
            self.execute_sql("DELETE FROM title_subs")
            for orig, sub in DEFAULT_TITLE_SUBS:
                self.execute_sql(
                    "INSERT OR IGNORE INTO title_subs (original_title, substitute_title) VALUES (?, ?)",
                    (orig, sub),
                )
            self.invalidate_cache()
            g.log("TitleSubsCache: Reset to defaults", "info")
        except Exception as e:
            g.log(f"TitleSubsCache.clear_all error: {e}", "warning")


def title_subs_add():
    """Show input dialogs to add a new title substitution."""
    import xbmcgui

    dialog = xbmcgui.Dialog()
    original = dialog.input(g.get_language_string(30750))
    if not original:
        return

    substitute = dialog.input(g.get_language_string(30751))
    if not substitute:
        return

    TitleSubsCache().set_substitute(original, substitute)
    g.notification(g.ADDON_NAME, g.get_language_string(30752))


def title_subs_view_remove():
    """Show list of all substitutions and let user select ones to remove."""
    import xbmcgui

    ts = TitleSubsCache()
    all_subs = ts.get_all()
    if not all_subs:
        g.notification(g.ADDON_NAME, g.get_language_string(30753))
        return

    display_items = [f"{s['original_title']}  →  {s['substitute_title']}" for s in all_subs]

    dialog = xbmcgui.Dialog()
    choices = dialog.multiselect(g.get_language_string(30754), display_items)
    if choices is None:
        return

    removals = [all_subs[i]["original_title"] for i in choices]
    ts.remove_many(removals)
    g.notification(g.ADDON_NAME, g.get_language_string(30755).format(len(removals)))


def title_subs_clear_all():
    """Reset all title substitutions to defaults after confirmation."""
    import xbmcgui

    dialog = xbmcgui.Dialog()
    if not dialog.yesno(g.ADDON_NAME, g.get_language_string(30756)):
        return

    TitleSubsCache().clear_all()
    g.notification(g.ADDON_NAME, g.get_language_string(30757))
