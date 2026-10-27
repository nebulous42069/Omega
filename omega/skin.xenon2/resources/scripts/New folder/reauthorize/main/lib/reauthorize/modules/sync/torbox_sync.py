from reauthorize.modules import sync_support
import xbmc, xbmcaddon, xbmcgui
import xbmcvfs
import os

from pathlib import Path
from libs.common import var

char_remov = ["'", ",", ")","("]

#Account Manager Torbox
# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr
your_token = accountmgr.getSetting("torbox.token")
your_acct_id = accountmgr.getSetting("torbox.acct_id")
          

from reauthorize.modules import sync_support
xbmcaddon = sync_support.addon_api(xbmcaddon)
class Auth:
    def torbox_auth(self):
    #Umbrella
        try:
                if xbmcvfs.exists(var.chk_umb):
                        chk_auth_umb = xbmcaddon.Addon('plugin.video.umbrella').getSetting("torboxtoken")
                        if sync_support.needs('plugin.video.umbrella', [('torboxtoken',your_token),('torbox.username',your_acct_id)]):
                        
                                addon = xbmcaddon.Addon("plugin.video.umbrella")
                                addon.setSetting("torboxtoken", your_token)
                                addon.setSetting("torbox.username", your_acct_id)
                                addon.setSetting("torbox.enable", 'true')

        except:
                sync_support.failed()
                xbmc.log('%s: Umbrella TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #POV
        try:
                if xbmcvfs.exists(var.chk_pov):
                        chk_auth_pov = xbmcaddon.Addon('plugin.video.pov').getSetting("tb.token")
                        if sync_support.needs('plugin.video.pov', [('tb.token',your_token),('tb.account_id',your_acct_id)]):

                                addon = xbmcaddon.Addon("plugin.video.pov")
                                addon.setSetting("tb.token", your_token)
                                addon.setSetting("tb.account_id", your_acct_id)
                                addon.setSetting("tb.enabled", 'true')
                                addon.setSetting("tb.expires", '0')

        except:
                sync_support.failed()
                xbmc.log('%s: POV TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Infinity
        try:
                if xbmcvfs.exists(var.chk_infinity):
                        chk_auth_infinity = xbmcaddon.Addon('plugin.video.infinity').getSetting("torboxtoken")
                        if sync_support.needs('plugin.video.infinity', [('torboxtoken',your_token),('torbox.username',your_acct_id)]):

                                addon = xbmcaddon.Addon("plugin.video.infinity")
                                addon.setSetting("torboxtoken", your_token)
                                addon.setSetting("torbox.username", your_acct_id)
                                addon.setSetting("torbox.enable", 'true')
                                addon.setSetting("torbox.expirynotice", '0')

        except:
                sync_support.failed()
                xbmc.log('%s: Infinity TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

     #Otaku
        try:
                if xbmcvfs.exists(var.chk_otaku) and not xbmcvfs.exists(var.otaku_ud):
                        os.mkdir(var.otaku_ud)
                        xbmcvfs.copy(os.path.join(var.otaku), os.path.join(var.chkset_otaku))
                        
                if xbmcvfs.exists(var.chk_otaku) and not xbmcvfs.exists(var.chkset_otaku):
                        xbmcvfs.copy(os.path.join(var.otaku), os.path.join(var.chkset_otaku))

                if xbmcvfs.exists(var.chk_otaku):
                        chk_auth_otaku = xbmcaddon.Addon('plugin.video.otaku').getSetting("tb.apikey")
                        if sync_support.needs('plugin.video.otaku', [('tb.apikey',your_token)]):
                        
                                addon = xbmcaddon.Addon("plugin.video.otaku")
                                addon.setSetting("tb.apikey", your_token)
                                addon.setSetting("tb.enabled", 'true')
        except:
                sync_support.failed()
                xbmc.log('%s: Otaku TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Gears TorBox
        try:
                if xbmcvfs.exists(var.chk_gears_video) and xbmcvfs.exists(var.chkset_gears):

                    from reauthorize.modules.db import torbox_db
                    conn = torbox_db.create_conn(var.gears_settings_db)

                    with conn:
                        cursor = conn.cursor()
                        cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('tb.token',))
                        auth_tb = cursor.fetchone()
                        chk_auth_gears = str(auth_tb)
                        cursor.close()

                        for char in char_remov:
                            chk_auth_gears = chk_auth_gears.replace(char, "")

                        if not str(your_token) == chk_auth_gears:
                            from reauthorize.modules.db import torbox_db
                            torbox_db.auth_gears_tb()
                            var.remake_settings()
        except:
                sync_support.failed()
                xbmc.log('%s: Gears TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Genocide (plugin.video.genocide) TorBox
        try:
                if xbmcvfs.exists(var.chk_newgenocide):
                        chk_auth_newgenocide = xbmcaddon.Addon('plugin.video.genocide').getSetting("torbox.token")
                        if sync_support.needs('plugin.video.genocide', [('torbox.token',your_token),('torbox.username',your_acct_id)]):
                                addon = xbmcaddon.Addon("plugin.video.genocide")
                                addon.setSetting("torbox.token", your_token)
                                addon.setSetting("torbox.username", your_acct_id)
        except:
                sync_support.failed()
                xbmc.log('%s: Genocide TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Orion TorBox
        try:
                if xbmcvfs.exists(var.chk_orion):
                        chk_auth_orion = xbmcaddon.Addon('plugin.video.orion').getSetting("tb_token")
                        if sync_support.needs('plugin.video.orion', [('tb_token',your_token)]):
                                addon = xbmcaddon.Addon("plugin.video.orion")
                                addon.setSetting("tb_token", your_token)
                                addon.setSetting("tb_enabled", 'true')
        except:
                sync_support.failed()
                xbmc.log('%s: Orion TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Red Light TorBox
        try:
                from reauthorize.modules.db import redlight_db
                redlight_db.push([('tb.token', your_token),
                                  ('tb.enabled', 'true')])
        except:
                sync_support.failed()
                xbmc.log('%s: Red Light TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #The Archives TorBox
        try:
                if xbmcvfs.exists(var.chk_thearchives):
                        chk_auth_thearchives = xbmcaddon.Addon('plugin.video.thearchives').getSetting("tb.token")
                        if sync_support.needs('plugin.video.thearchives', [('tb.token',your_token)]):

                                addon = xbmcaddon.Addon("plugin.video.thearchives")
                                addon.setSetting("tb.token", your_token)
                                addon.setSetting("tb.enabled", 'true')
        except:
                sync_support.failed()
                xbmc.log('%s: The Archives TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Cosmos TorBox
        try:
                if xbmcvfs.exists(var.chk_cosmos):
                        chk_auth_cosmos = xbmcaddon.Addon('plugin.video.cosmos').getSetting("tb_api_key")
                        if sync_support.needs('plugin.video.cosmos', [('tb_api_key',your_token)]):
                                addon = xbmcaddon.Addon("plugin.video.cosmos")
                                addon.setSetting("tb_api_key", your_token)
                                addon.setSetting("tb_auth_done", 'true')
        except:
                sync_support.failed()
                xbmc.log('%s: Cosmos TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Diamond Media Player TorBox
        try:
                if xbmcvfs.exists(var.chk_rdtplayer):
                        chk_auth_rdtplayer = xbmcaddon.Addon('plugin.program.rdtplayer').getSetting("torbox_token")
                        if sync_support.needs('plugin.program.rdtplayer', [('torbox_token',your_token)]):
                                addon = xbmcaddon.Addon("plugin.program.rdtplayer")
                                addon.setSetting("torbox_token", your_token)
        except:
                sync_support.failed()
                xbmc.log('%s: Diamond Media Player TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Prism TorBox
    #tb.token isn't in settings.xml (visible="false" with no id= match in that file);
    #confirmed from Prism's own resources/lib/debrid/torbox.py: TB_TOKEN_KEY = "tb.token".
        try:
                if xbmcvfs.exists(var.chk_prism):
                        chk_auth_prism = xbmcaddon.Addon('plugin.video.prism').getSetting("tb.token")
                        if sync_support.needs('plugin.video.prism', [('tb.token',your_token)]):
                                addon = xbmcaddon.Addon("plugin.video.prism")
                                addon.setSetting("tb.token", your_token)
                                addon.setSetting("torbox.enabled", 'true')
        except:
                sync_support.failed()
                xbmc.log('%s: Prism TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #TMDb Movies TorBox
        try:
                if xbmcvfs.exists(var.chk_tmdbmovies):
                        chk_auth_tmdbmovies = xbmcaddon.Addon('plugin.video.tmdbmovies').getSetting("torbox_api_key")
                        if sync_support.needs('plugin.video.tmdbmovies', [('torbox_api_key',your_token)]):
                                addon = xbmcaddon.Addon("plugin.video.tmdbmovies")
                                addon.setSetting("torbox_api_key", your_token)
        except:
                sync_support.failed()
                xbmc.log('%s: TMDb Movies TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Youtube Theater TorBox
        try:
                if xbmcvfs.exists(var.chk_youtubetheater):
                        chk_auth_ytheater = xbmcaddon.Addon('plugin.video.youtubetheater').getSetting("tb.token")
                        if sync_support.needs('plugin.video.youtubetheater', [('tb.token',your_token)]):
                                addon = xbmcaddon.Addon("plugin.video.youtubetheater")
                                addon.setSetting("tb.token", your_token)
                                addon.setSetting("debrid_use_tr", 'true')
        except:
                sync_support.failed()
                xbmc.log('%s: Youtube Theater TorBox Failed!' % var.amgr, xbmc.LOGINFO)
                pass
