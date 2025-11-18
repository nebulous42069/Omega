# resources/lib/modules/seren_tools.py
import xbmc, xbmcaddon

def _set_umbrella_bool(setting_id, value=True):
    xbmcaddon.Addon('plugin.video.umbrella').setSetting(setting_id, 'true' if value else 'false')

def enable_and_auth(provider):
    mapping = {
        'premiumize': ('premiumize.enable', 'RunPlugin(plugin://plugin.video.umbrella/?action=pm_Authorize)'),
        'realdebrid': ('realdebrid.enable', 'RunPlugin(plugin://plugin.video.umbrella/?action=rd_Authorize)'),
        'offcloud': ('offcloud.enable', 'RunPlugin(plugin://plugin.video.umbrella/?action=oc_Authorize&query=9.0)'),
        'torbox': ('torbox.enable', 'RunPlugin(plugin://plugin.video.umbrella/?action=tb_Authorize)'),
        'easydebrid': ('easydebrid.enable', 'RunPlugin(plugin://plugin.video.umbrella/?action=ed_Authorize&query=9.0)'),
        'alldebrid':  ('alldebrid.enable',  'RunPlugin(plugin://plugin.video.umbrella/?action=ad_Authorize)')
    }
    setting_id, auth_cmd = mapping[provider]
    _set_umbrella_bool(setting_id, True)
    xbmc.executebuiltin(auth_cmd)
