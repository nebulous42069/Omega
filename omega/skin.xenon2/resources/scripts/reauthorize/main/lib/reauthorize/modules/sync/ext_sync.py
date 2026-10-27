import xbmc, xbmcaddon
import xbmcvfs
import os

from pathlib import Path
from reauthorize.modules import control
from reauthorize.modules.db import ext_db
from libs.common import var

char_remov = ["'", ",", ")","("]

# Ordered priority: first enabled+installed scraper wins for each addon
SCRAPER_OPTIONS = [
        ('script.module.cocoscrapers',  'CocoScrapers',  'ext.coco.enabled',    'chk_coco'),
        ('script.module.gearsscrapers', 'Gears Scrapers','ext.gears.enabled',   'chk_gears'),
        ('script.module.magneto',       'Magneto',       'ext.magneto.enabled', 'chk_magneto'),
        ('script.module.viperscrapers', 'Viper Scrapers','ext.viper.enabled',   'chk_viper'),
]

def _pick_scraper():
        """Return (module_id, name, chk_path) for the first enabled+installed scraper, or None."""
        for module_id, name, setting_key, chk_attr in SCRAPER_OPTIONS:
                if control.setting(setting_key) == 'true':
                        chk_path = getattr(var, chk_attr)
                        if xbmcvfs.exists(chk_path):
                                return module_id, name, chk_path
        return None

class Auth:
        def ext_auth(self, scraper_module=None, scraper_name=None, chk_scraper=None):
                if scraper_module is None:
                        picked = _pick_scraper()
                        if not picked:
                                xbmc.log('%s: No enabled+installed scraper found.' % var.amgr, xbmc.LOGINFO)
                                return
                        scraper_module, scraper_name, chk_scraper = picked

        #Umbrella
                try:
                        if xbmcvfs.exists(var.chk_umb) and xbmcvfs.exists(var.chkset_umb) and xbmcvfs.exists(chk_scraper):
                                addon = xbmcaddon.Addon("plugin.video.umbrella")
                                chk_auth = addon.getSetting("external_provider.module")
                                if chk_auth == scraper_module:
                                        pass
                                else:
                                        addon.setSetting("provider.external.enabled", 'true')
                                        addon.setSetting("external_provider.name", scraper_name)
                                        addon.setSetting("external_provider.module", scraper_module)
                except:
                        xbmc.log('%s: Umbrella Ext Provider Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

        #Infinity
                try:
                        if xbmcvfs.exists(var.chk_infinity) and xbmcvfs.exists(var.chkset_infinity) and xbmcvfs.exists(chk_scraper):
                                addon = xbmcaddon.Addon("plugin.video.infinity")
                                chk_auth = addon.getSetting("external_provider.module")
                                if chk_auth == scraper_module:
                                        pass
                                else:
                                        addon.setSetting("provider.external.enabled", 'true')
                                        addon.setSetting("external_provider.name", scraper_name)
                                        addon.setSetting("external_provider.module", scraper_module)
                except:
                        xbmc.log('%s: Infinity Ext Provider Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
