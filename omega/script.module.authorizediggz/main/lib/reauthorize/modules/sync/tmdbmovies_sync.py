"""Credential and status settings used by TMDb Movies."""
import xbmcaddon

from reauthorize.modules import sync_support

ADDON_ID = 'plugin.video.tmdbmovies'
CLOUD_STATUS = {
    'rd_api_key': 'rd_status',
    'pm_api_key': 'pm_status',
    'torbox_api_key': 'torbox_status',
    'oc_api_key': 'oc_status',
}


def cloud(key, value, wipe=False):
    if not (value or wipe) or not sync_support.installed(ADDON_ID):
        return
    if sync_support.put(ADDON_ID, [(key, '' if wipe else value)], wipe=wipe):
        status(CLOUD_STATUS[key], 'Disconnected' if wipe else 'Connected')


def status(key, value):
    addon = xbmcaddon.Addon(ADDON_ID)
    schema = sync_support.declared_settings(addon)
    if schema is not None and schema.get(key, 'action') != 'action':
        if not sync_support.put(ADDON_ID, [(key, value)]):
            raise RuntimeError('TMDb Movies status could not be saved')
