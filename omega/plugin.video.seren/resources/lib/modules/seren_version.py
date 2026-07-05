from resources.lib.modules.globals import g

from resources.lib.common import maintenance


def do_version_change():
    if g.get_setting("seren.version") == g.CLEAN_VERSION:
        return

    g.log("Clearing all caches on Seren version change", "info")

    # Clear stale Python bytecode cache — prevents old .pyc from overriding new .py files
    try:
        import os
        import shutil
        addon_path = g.ADDON_PATH
        cleared = 0
        for dirpath, dirnames, filenames in os.walk(addon_path):
            for d in dirnames:
                if d == '__pycache__':
                    shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
                    cleared += 1
        if cleared:
            g.log(f"Version change: Cleared {cleared} __pycache__ directories", "info")
    except Exception as e:
        g.log(f"Version change: Failed to clear __pycache__: {e}", "warning")

    g.clear_cache(silent=True)

    # Also clear torrent cache and debrid cache to ensure fresh state
    try:
        from resources.lib.database.torrentCache import TorrentCache
        TorrentCache().clear_all()
        g.log("Version change: Cleared torrent cache", "info")
    except Exception as e:
        g.log(f"Version change: Failed to clear torrent cache: {e}", "warning")

    try:
        from resources.lib.database.debridCache import DebridCache
        DebridCache().clear_all()
        g.log("Version change: Cleared debrid hash cache", "info")
    except Exception as e:
        g.log(f"Version change: Failed to clear debrid cache: {e}", "warning")

    try:
        from resources.lib.database.providerPerformance import ProviderPerformance
        ProviderPerformance().clear_all()
        g.log("Version change: Cleared provider performance stats", "info")
    except Exception as e:
        g.log(f"Version change: Failed to clear provider performance stats: {e}", "warning")

    try:
        from resources.lib.database.animeCache import AnimeCache
        AnimeCache().execute_sql("DELETE FROM anime_titles WHERE anidb_id != 0", ())
        g.log("Version change: Cleared AniDB titles cache (episode-title pollution fix)", "info")
    except Exception as e:
        g.log(f"Version change: Failed to clear AniDB titles cache: {e}", "warning")

    # Clean stale Kodi texture cache entries to prevent thumbnail loading storm.
    # After cache clear, skin widgets re-render and Kodi's CImageLoader tries loading
    # hundreds of thumbnails whose cached files may no longer exist, flooding the log
    # with errors and freezing the UI.
    _clean_stale_textures()

    g.set_setting("seren.version", g.CLEAN_VERSION)

    # Reuselanguageinvoker update.  This should be last to execute as it can do a profile reload.
    # Restore the user's reuselanguageinvoker preference after version change.
    # Default is disabled, but if the user previously enabled it, respect that choice.
    maintenance.toggle_reuselanguageinvoker(
        True if g.get_setting("reuselanguageinvoker") == "Enabled" else False
    )


def _clean_stale_textures():
    """Remove stale entries from Kodi's Textures13.db where cached files are missing.

    After a Seren cache clear, Kodi's texture DB still references thumbnail files
    that may have been orphaned. When the skin tries to load these, each missing file
    generates an error and blocks an image loader thread. Cleaning stale entries
    lets Kodi re-download fresh thumbnails on demand.
    """
    try:
        import os
        import sqlite3

        import xbmcvfs

        textures_db = xbmcvfs.translatePath("special://database/Textures13.db")
        thumbnails_path = xbmcvfs.translatePath("special://masterprofile/Thumbnails/")

        if not os.path.isfile(textures_db):
            return

        conn = sqlite3.connect(textures_db, timeout=5)
        try:
            cursor = conn.execute("SELECT id, cachedurl FROM texture")
            stale_ids = []
            for row in cursor:
                texture_id, cached_url = row
                if cached_url:
                    full_path = os.path.join(thumbnails_path, cached_url)
                    if not os.path.isfile(full_path):
                        stale_ids.append(texture_id)

            if stale_ids:
                # Delete in batches to avoid locking the DB too long
                for i in range(0, len(stale_ids), 100):
                    batch = stale_ids[i:i + 100]
                    placeholders = ",".join("?" * len(batch))
                    conn.execute(f"DELETE FROM texture WHERE id IN ({placeholders})", batch)
                    conn.execute(f"DELETE FROM sizes WHERE idtexture IN ({placeholders})", batch)
                conn.commit()
                g.log(f"Version change: Cleaned {len(stale_ids)} stale texture cache entries", "info")
            else:
                g.log("Version change: No stale texture cache entries found", "debug")
        finally:
            conn.close()
    except Exception as e:
        g.log(f"Version change: Texture cache cleanup failed: {e}", "warning")
