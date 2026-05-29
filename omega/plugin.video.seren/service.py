import sqlite3
import sys
from random import randint

import xbmc
import xbmcgui

from resources.lib.common import tools

if tools.is_stub():
    # noinspection PyUnresolvedReferences
    from mock_kodi import MOCK

from resources.lib.modules.globals import g

from resources.lib.modules.seren_version import do_version_change
from resources.lib.modules.serenMonitor import SerenMonitor
from resources.lib.modules.update_news import do_update_news
from resources.lib.modules.manual_timezone import validate_timezone_detected
from resources.lib.modules.accountmgr_sync import (
    sync_accountmgr_credentials,
    snapshot_enabled_flags,
    protect_enabled_flags
)

g.init_globals(sys.argv)

import os
import xbmcvfs
from resources.lib.modules.providers.install_manager import ProviderInstallManager


def install_embedded_provider_packages():

    provider_dir = os.path.join(
        g.ADDON_PATH,
        "embedded_providers"
    ) + os.sep

    if not xbmcvfs.exists(provider_dir):
        return

    try:
        files = xbmcvfs.listdir(provider_dir)[1]
    except Exception as e:
        g.log(f"Embedded provider scan failed: {e}", "error")
        return

    provider_zips = [
        f for f in files
        if f.lower().endswith(".zip")
    ]

    if not provider_zips:
        return

    selectable = []
    install_paths = []

    for filename in provider_zips:

        marker = os.path.join(
            g.ADDON_USERDATA_PATH,
            "installed_provider_" + filename + ".txt"
        )

        if xbmcvfs.exists(marker):
            continue

        selectable.append(filename)

        install_paths.append(
            os.path.join(provider_dir, filename)
        )

    if not selectable:
        return

    selected = xbmcgui.Dialog().multiselect(
        "Install One Or More Provider Packages",
        selectable
    )

    if selected is None:
        return

    for index in selected:

        filename = selectable[index]
        zip_path = install_paths[index]

        marker = os.path.join(
            g.ADDON_USERDATA_PATH,
            "installed_provider_" + filename + ".txt"
        )

        try:

            g.log(f"Installing provider package: {filename}")

            installer = ProviderInstallManager(
                silent=True
            )

            installer.install_package(
                install_style=1,
                url=zip_path
            )

            xbmcvfs.File(marker, "w").close()

            g.log(f"Installed provider package: {filename}")

        except Exception as e:

            g.log(
                f"Failed installing provider package "
                f"{filename}: {e}",
                "error"
            )


do_version_change()

snapshot_enabled_flags()

sync_accountmgr_credentials()

_prewarm_count = g.SETTINGS_CACHE.pre_warm_settings(g.SETTINGS_PATH)

g._store_service_state()

install_embedded_provider_packages()

xbmcgui.Window(10000).setProperty('seren.service.ready', g.VERSION)

_ = g.studio_icons

g.log("##################  STARTING SERVICE  ######################")
g.log(f"### {g.ADDON_ID} {g.VERSION}")
g.log(f"### Platform: {g.PLATFORM}")
g.log(f"### Python: {sys.version.split(' ', 1)[0]}")
g.log(f"### SQLite: {sqlite3.sqlite_version}")
g.log(f"### Detected Kodi Version: {g.KODI_VERSION}")
g.log(f"### Detected timezone: {repr(g.LOCAL_TIMEZONE.zone)}")
g.log(f"### Settings pre-warmed: {_prewarm_count}")
g.log("#############  SERVICE ENTERED KEEP ALIVE  #################")

monitor = SerenMonitor()

try:
    xbmc.executebuiltin(
        'RunPlugin("plugin://plugin.video.seren/?action=longLifeServiceManager")'
    )

    do_update_news()
    validate_timezone_detected()

    try:
        g.clear_kodi_bookmarks()

    except TypeError:
        g.log(
            "Unable to clear bookmarks on service init. "
            "This is not a problem if it occurs immediately after install.",
            "warning",
        )

    xbmc.executebuiltin(
        'RunPlugin("plugin://plugin.video.seren/?action=torrentCacheCleanup")'
    )

    xbmc.executebuiltin(
        'RunPlugin("plugin://plugin.video.seren/?action=undesirablesStartup")'
    )

    xbmc.executebuiltin(
        'RunPlugin("plugin://plugin.video.seren/?action=updateAnimeMappings")'
    )

    g.wait_for_abort(30)

    protect_enabled_flags()

    while not monitor.abortRequested():

        xbmc.executebuiltin(
            'RunPlugin("plugin://plugin.video.seren/?action=runMaintenance")'
        )

        if not g.wait_for_abort(15):

            xbmc.executebuiltin(
                'RunPlugin("plugin://plugin.video.seren/?action=syncTraktActivities")'
            )

        if not g.wait_for_abort(15):

            xbmc.executebuiltin(
                'RunPlugin("plugin://plugin.video.seren/?action=cleanOrphanedMetadata")'
            )

        if not g.wait_for_abort(15):

            xbmc.executebuiltin(
                'RunPlugin("plugin://plugin.video.seren/?action=updateLocalTimezone")'
            )

        if g.wait_for_abort(60 * randint(13, 17)):
            break

finally:
    xbmcgui.Window(10000).clearProperty('seren.service.ready')
    del monitor
    g.deinit()
