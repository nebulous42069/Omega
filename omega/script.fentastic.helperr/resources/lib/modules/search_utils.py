# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcvfs
import sys
import sqlite3 as database
from urllib.parse import quote
from urllib.parse import quote_plus

# Variables
MAX_HISTORY_ITEMS = 20

WINDOW_HOME = 10000
WINDOW_SEARCH = 10025
WINDOW_SEARCH_RESULTS = 1121

ADDON_DATA = xbmcvfs.translatePath(
    "special://profile/addon_data/script.fentastic.helperr/"
)
DB_PATH = xbmcvfs.translatePath(
    "special://profile/addon_data/script.fentastic.helperr/spath_cache.db"
)


class SPaths:
    def __init__(self):
        self._connect_database()

    # -----------------------------------------------------------------
    # Database Helpers
    # -----------------------------------------------------------------
    def _connect_database(self):
        if not xbmcvfs.exists(ADDON_DATA):
            xbmcvfs.mkdir(ADDON_DATA)

        self.dbcon = database.connect(DB_PATH, timeout=20)
        self.dbcur = self.dbcon.cursor()
        self.dbcur.execute(
            "CREATE TABLE IF NOT EXISTS spath ("
            "spath_id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "spath TEXT)"
        )
        self.dbcon.commit()

    def fetch_all_spaths(self):
        return self.dbcur.execute(
            "SELECT spath_id, spath FROM spath ORDER BY spath_id DESC"
        ).fetchall()

    def add_spath(self, term):
        self.dbcur.execute("DELETE FROM spath WHERE spath = ?", (term,))
        self.dbcur.execute("INSERT INTO spath (spath) VALUES (?)", (term,))
        self.dbcon.commit()

    def clear_all(self):
        self.dbcur.execute("DELETE FROM spath")
        self.dbcur.execute("DELETE FROM sqlite_sequence WHERE name='spath'")
        self.dbcon.commit()

    # -----------------------------------------------------------------
    # SEARCH HISTORY
    # -----------------------------------------------------------------
    def apply_search_history_to_skin(self, rows=None):
        if rows is None:
            rows = self.fetch_all_spaths()

        rows = rows[:MAX_HISTORY_ITEMS]

        # Read skin setting
        limit = xbmc.getInfoLabel("Skin.String(searchhistory.limit)")
        try:
            limit = int(limit)
        except ValueError:
            limit = 5  # fallback default

        labels = [term for _, term in rows[:limit]]

        # Populate fixed items
        for i in range(MAX_HISTORY_ITEMS):
            slot = i + 1
            if i < len(labels):
                xbmc.executebuiltin(
                    f"Skin.SetString(SearchHistory.{slot},{labels[i]})"
                )
            else:
                xbmc.executebuiltin(f"Skin.Reset(SearchHistory.{slot})")

        xbmc.executebuiltin(
            f"Skin.SetString(SearchHistoryCount,{len(labels)})"
        )

    # -----------------------------------------------------------------
    # SEARCH TOOLS
    # -----------------------------------------------------------------
    def open_search_window(self):
        xbmc.executebuiltin("Skin.Reset(SearchInput)")
        xbmc.executebuiltin("Skin.Reset(SearchInputEncoded)")
        xbmc.executebuiltin("Skin.SetString(SearchInputTraktEncoded,none)")
        xbmc.executebuiltin("ClearProperty(fentastic.results,1121)")

        xbmc.executebuiltin("ActivateWindow(1121)")
        xbmc.sleep(150)  # allow skin conditions to evaluate

        count = int(xbmc.getInfoLabel("Skin.String(SearchHistoryCount)") or 0)

        if count > 0:
            xbmc.executebuiltin("SetFocus(9000)")
        else:
            xbmc.executebuiltin("SetFocus(27400)")


    def search_input(self, search_term=None):
        if not search_term or not search_term.strip():
            title = ("Search" if xbmcgui.getCurrentWindowId() == WINDOW_HOME else "New Search")
            kb = xbmc.Keyboard("", title)
            kb.doModal()
            if not kb.isConfirmed():
                return
            search_term = kb.getText().strip()
            if not search_term:
                return

        search_term = search_term.strip()
        encoded = quote(search_term)

        # Set search strings FIRST
        xbmc.executebuiltin(f"Skin.SetString(SearchInput,{search_term})")
        xbmc.executebuiltin(f"Skin.SetString(SearchInputEncoded,{encoded})")
        xbmc.executebuiltin(f"Skin.SetString(SearchInputTraktEncoded,{encoded})")

        # Show spinner
        xbmc.executebuiltin("Skin.SetString(SearchBusy,1)")

        # Open results window if needed
        if xbmcgui.getCurrentWindowId() != WINDOW_SEARCH_RESULTS:
            xbmc.executebuiltin(f"ActivateWindow({WINDOW_SEARCH_RESULTS})")
            xbmc.sleep(150)

        self.add_spath(search_term)
        self.apply_search_history_to_skin()

        xbmc.executebuiltin("SetProperty(fentastic.results,1,1121)")

        # Trigger widget refresh
        xbmc.executebuiltin("Skin.SetString(SearchBusy,1)")
        xbmc.executebuiltin("Container(27001).Update()")

        # Wait for widgets to settle
        xbmc.executebuiltin("Skin.Reset(SearchBusy)")

    def re_search(self):
        term = ""

        # RunScript arguments are comma-separated
        for arg in sys.argv:
            if arg.startswith("query="):
                term = arg.replace("query=", "", 1)
                break

        if not term:
            xbmc.log("FENtastic+: re_search called with empty query", xbmc.LOGWARNING)
            return

        self.search_input(term)

    def search_from_history(self):
        query = ''

        for arg in sys.argv:
            if arg.startswith('query='):
                query = arg.replace('query=', '', 1).strip()
                break

        if not query:
            xbmc.log('FENtastic+: search_from_history called with empty query', xbmc.LOGWARNING)
            return

        self.search_input(query)
        
    def run_last_search(self):
        search_term = xbmc.getInfoLabel('Skin.String(SearchInput)')

        if not search_term:
            xbmc.executebuiltin('RunScript(script.fentastic.helperr,mode=search_input)')
            return

        # Reopen the search results window using the existing SearchInput/SearchInputEncoded
        xbmc.executebuiltin('ActivateWindow(1121)')

    def change_search_provider(self):
        providers = [
            ('0', 'TMDb Helper', 'plugin.video.themoviedb.helper'),
            ('1', 'Fen Light', 'plugin.video.fenlight'),
            ('2', 'Umbrella', 'plugin.video.umbrella'),
            ('3', 'POV', 'plugin.video.pov'),
            ('4', 'The Gears', 'plugin.video.gears'),
            ('5', 'Red Light', 'plugin.video.redlight'),
        ]

        installed = [
            (pid, name, addon_id)
            for pid, name, addon_id in providers
            if xbmc.getCondVisibility(
                'System.HasAddon({0})'.format(addon_id)
            )
        ]

        if not installed:
            xbmcgui.Dialog().notification(
                'FENtastic',
                'No search providers are installed'
            )
            return

        current = xbmc.getInfoLabel(
            'Skin.String(current_search_provider)'
        )

        labels = [name for pid, name, addon_id in installed]

        preselect = 0
        for idx, (pid, name, addon_id) in enumerate(installed):
            if pid == current:
                preselect = idx
                break

        choice = xbmcgui.Dialog().select(
            'Choose Search Provider',
            labels,
            preselect=preselect
        )

        if choice < 0:
            return

        provider_id, provider_name, addon_id = installed[choice]

        # No change
        if provider_id == current:
            return

        # Set provider
        xbmc.executebuiltin(
            'Skin.SetString(current_search_provider,{0})'
            .format(provider_id)
        )

        # Close SearchResults window
        xbmc.executebuiltin('ActivateWindow(home)')

        # Run last search term again with new provider
        self.run_last_search()

        
    def remove_all_spaths(self):    # Clear search history
        dialog = xbmcgui.Dialog()
        if not dialog.yesno("FENtastic","Are you sure you want to clear all search history?"):
            return

        self.clear_all()
        self.apply_search_history_to_skin([])

        xbmc.executebuiltin("ClearProperty(fentastic.results,1121)")
        xbmc.executebuiltin("Skin.SetString(SearchHistoryCount,0)")
        xbmc.executebuiltin("Skin.Reset(SearchInput)")
        xbmc.executebuiltin("Skin.Reset(SearchInputEncoded)")
        xbmc.executebuiltin("Skin.SetString(SearchInputTraktEncoded,none)")

        # Exit search UI entirely
        xbmc.executebuiltin("ActivateWindow(home)")
