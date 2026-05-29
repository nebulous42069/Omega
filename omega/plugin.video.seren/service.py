import sqlite3
import sys
import os
import json
import zipfile
from random import randint

import xbmc
import xbmcgui
import xbmcvfs

from resources.lib.common import tools

if tools.is_stub():
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
from resources.lib.modules.providers.install_manager import ProviderInstallManager

g.init_globals(sys.argv)


def get_provider_package_name(zip_path):
    """
    Read provider package name from meta.json inside provider zip
    """

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:

            for member in zf.namelist():

                if member.lower().endswith("meta.json"):

                    with zf.open(member) as meta_file:

                        meta = json.loads(
                            meta_file.read().decode("utf-8")
                        )

                        return meta.get("name")

    except Exception as e:

        g.log(
            f"Failed reading provider meta from {zip_path}: {e}",
            "error"
        )

    return None


def remove_existing_provider_package(package_name):
    """
    Remove existing provider package before installing updated version
    """

    try:

        installer = ProviderInstallManager(silent=True)

        known_packages = installer.known_packages

        for package in known_packages:

            existing_name = package.get("pack_name")

            if existing_name == package_name:

                g.log(
                    f"Removing existing provider package: "
                    f"{existing_name}"
                )

                installer.uninstall_package(existing_name)

    except Exception as e:

        g.log(
            f"Failed removing existing provider package "
            f"{package_name}: {e}",
            "error"
        )


def install_embedded_provider_packages():

    provider_dir = os.path.join(
        g.ADDON_PATH,
        "embedded_providers"
    ) + os.sep

    if not xbmcvfs.exists(provider_dir):
        return

    version_marker = os.path.join(
        g.ADDON_USERDATA_PATH,
        f"provider_prompt_version_{g.VERSION}.txt"
    )

    if xbmcvfs.exists(version_marker):
        return

    try:

        files = xbmcvfs.listdir(provider_dir)[1]

    except Exception as e:

        g.log(
            f"Embedded provider scan failed: {e}",
            "error"
        )

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

        selectable.append(filename)

        install_paths.append(
            os.path.join(provider_dir, filename)
        )

    selected = xbmcgui.Dialog().multiselect(
        "Install Provider Packages",
        selectable
    )

    if selected is None:

        xbmcvfs.File(version_marker, "w").close()
        return

    for index in selected:

        filename = selectable[index]
        zip_path = install_paths[index]

        try:

            package_name = get_provider_package_name(
                zip_path
            )

            if package_name:

                remove_existing_provider_package(
                    package_name
                )

            g.log(
                f"Installing provider package: {filename}"
            )

            installer = ProviderInstallManager(
                silent=True
            )

            installer.install_package(
                install_style=1,
                url=zip_path
            )

            g.log(
                f"Installed provider package: {filename}"
            )

        except Exception as e:

            g.log(
                f"Failed installing provider package "
                f"{filename}: {e}",
                "error"
            )

    xbmcvfs.File(version_marker, "w").close()


do_version_change()

snapshot_enabled_flags()

sync_accountmgr_credentials()

_prewarm_count = g.SETTINGS_CACHE.pre_warm_settings(
    g.SETTINGS_PATH
)

g._store_service_state()

install_embedded_provider_packages()

xbmcgui.Window(10000).setProperty(
    'seren.service.ready',
    g.VERSION
)

_ = g.studio_icons

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
            "Unable to clear bookmarks on service init.",
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

    xbmcgui.Window(10000).clearProperty(
        'seren.service.ready'
    )

    del monitor

    g.deinit()
