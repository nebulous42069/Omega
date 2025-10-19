# resources/lib/modules/seren_tools.py
import xbmc, xbmcaddon

def _set_seren_bool(setting_id, value=True):
    xbmcaddon.Addon('plugin.video.seren').setSetting(setting_id, 'true' if value else 'false')

def enable_and_auth(provider):
    mapping = {
        'premiumize': ('premiumize.enabled', 'RunPlugin(plugin://plugin.video.seren/?action=authPremiumize)'),
        'realdebrid': ('realdebrid.enabled', 'RunPlugin(plugin://plugin.video.seren/?action=authRealDebrid)'),
        'alldebrid':  ('alldebrid.enabled',  'RunPlugin(plugin://plugin.video.seren/?action=authAllDebrid)')
    }
    setting_id, auth_cmd = mapping[provider]
    _set_seren_bool(setting_id, True)
    xbmc.executebuiltin(auth_cmd)
