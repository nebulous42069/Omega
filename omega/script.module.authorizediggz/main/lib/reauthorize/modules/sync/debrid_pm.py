from reauthorize.modules import sync_support
import xbmc, xbmcaddon
import xbmcvfs
import os

from pathlib import Path
from reauthorize.modules import control
from libs.common import var

char_remov = ["'", ",", ")","("]

#Account Manager Premiumize
# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr
your_pm_username = accountmgr.getSetting("premiumize.username")
your_pm_token = accountmgr.getSetting("premiumize.token")


from reauthorize.modules import sync_support
xbmcaddon = sync_support.addon_api(xbmcaddon)
class Auth:
    def premiumize_auth(self):
    #Seren PM
        try:
                if xbmcvfs.exists(var.chk_seren): #Check that the addon is installed and settings.xml exists
                        
                        #Get add-on setting to compare
                        chk_auth_seren = xbmcaddon.Addon('plugin.video.seren').getSetting("premiumize.token")
                        chk_auth_seren_rd = xbmcaddon.Addon('plugin.video.seren').getSetting("rd.auth")
                        chk_auth_seren_ad = xbmcaddon.Addon('plugin.video.seren').getSetting("alldebrid.apikey")
                        if sync_support.needs('plugin.video.seren', [('premiumize.username',your_pm_username),('premiumize.token',your_pm_token)]):
                                
                                #Write data to settings.xml
                                addon = xbmcaddon.Addon("plugin.video.seren")
                                addon.setSetting("premiumize.username", your_pm_username)
                                addon.setSetting("premiumize.token", your_pm_token)

                                premium_stat = ("Premium")
                                addon.setSetting("premiumize.premiumstatus", premium_stat)
                                
                                #Enable authorized debrid services
                                enabled_pm = ("true" if your_pm_token and not control.wiping() else "false")
                                addon.setSetting("premiumize.enabled", enabled_pm)

                                if str(chk_auth_seren_rd) != '': #Check if Real-Debrid is authorized
                                        enabled_rd = ("true")
                                        addon.setSetting("realdebrid.enabled", enabled_rd)
                                else:
                                        enabled_rd = ("false")
                                        addon.setSetting("realdebrid.enabled", enabled_rd)
                        
                                if str(chk_auth_seren_ad) != '': #Check if Premiumize is authorized
                                        enabled_ad = ("true")
                                        addon.setSetting("alldebrid.enabled", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("alldebrid.enabled", enabled_ad)
        except:
                sync_support.failed('plugin.video.seren')
                xbmc.log('%s: Seren Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Coalition PM
        try:
                if xbmcvfs.exists(var.chk_coal):
                        chk_auth_coal = xbmcaddon.Addon('plugin.video.coalition').getSetting("pm.token")
                        chk_auth_coal_rd = xbmcaddon.Addon('plugin.video.coalition').getSetting("rd.token")
                        chk_auth_coal_ad = xbmcaddon.Addon('plugin.video.coalition').getSetting("ad.token")
                        if sync_support.needs('plugin.video.coalition', [('pm.account_id',your_pm_username),('pm.token',your_pm_token)]):

                                addon = xbmcaddon.Addon("plugin.video.coalition")
                                addon.setSetting("pm.account_id", your_pm_username)
                                addon.setSetting("pm.token", your_pm_token)

                                enabled_pm = ("true" if your_pm_token and not control.wiping() else "false")
                                addon.setSetting("pm.enabled", enabled_pm)

                                if str(chk_auth_coal_rd) != '':
                                        enabled_rd = ("true")
                                        addon.setSetting("rd.enabled", enabled_rd)
                                else:
                                        enabled_rd = ("false")
                                        addon.setSetting("rd.enabled", enabled_rd)

                                if str(chk_auth_coal_ad) != '':
                                        enabled_ad = ("true")
                                        addon.setSetting("ad.enabled", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("ad.enabled", enabled_ad)
        except:
                sync_support.failed('plugin.video.coalition')
                xbmc.log('%s: Coalition Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #POV PM
        try:
                if xbmcvfs.exists(var.chk_pov):
                        chk_auth_pov = xbmcaddon.Addon('plugin.video.pov').getSetting("pm.token")
                        chk_auth_pov_rd = xbmcaddon.Addon('plugin.video.pov').getSetting("rd.token")
                        chk_auth_pov_ad = xbmcaddon.Addon('plugin.video.pov').getSetting("ad.token")
                        if sync_support.needs('plugin.video.pov', [('pm.account_id',your_pm_username),('pm.token',your_pm_token)]):
                                
                                addon = xbmcaddon.Addon("plugin.video.pov")
                                addon.setSetting("pm.account_id", your_pm_username)
                                addon.setSetting("pm.token", your_pm_token)

                                enabled_pm = ("true" if your_pm_token and not control.wiping() else "false")
                                addon.setSetting("pm.enabled", enabled_pm)

                                if str(chk_auth_pov_rd) != '':
                                        enabled_rd = ("true")
                                        addon.setSetting("rd.enabled", enabled_rd)
                                else:
                                        enabled_rd = ("false")
                                        addon.setSetting("rd.enabled", enabled_rd)

                                if str(chk_auth_pov_ad) != '':
                                        enabled_ad = ("true")
                                        addon.setSetting("ad.enabled", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("ad.enabled", enabled_ad)
        except:
                sync_support.failed('plugin.video.pov')
                xbmc.log('%s: POV Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass                

    #Umbrella PM
        try:
            if xbmcvfs.exists(var.chk_umb) and ((your_pm_token) or control.wiping()):
                sync_support.put('plugin.video.umbrella', [('premiumizeusername', '' if control.wiping() else your_pm_username), ('premiumizetoken', '' if control.wiping() else your_pm_token), ('premiumize.enable', 'true' if your_pm_token and not control.wiping() else 'false')], wipe=control.wiping())
        except:
                sync_support.failed('plugin.video.umbrella')
                xbmc.log('%s: Umbrella Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Infinity PM
        try:
                if xbmcvfs.exists(var.chk_infinity):
                        chk_auth_infinity = xbmcaddon.Addon('plugin.video.infinity').getSetting("premiumizetoken")
                        chk_auth_infinity_rd = xbmcaddon.Addon('plugin.video.infinity').getSetting("realdebridtoken")
                        chk_auth_infinity_ad = xbmcaddon.Addon('plugin.video.infinity').getSetting("alldebridtoken")
                        if sync_support.needs('plugin.video.infinity', [('premiumizeusername',your_pm_username),('premiumizetoken',your_pm_token)]):
                                
                                addon = xbmcaddon.Addon("plugin.video.infinity")
                                addon.setSetting("premiumizeusername", your_pm_username)
                                addon.setSetting("premiumizetoken", your_pm_token)

                                enabled_pm = ("true" if your_pm_token and not control.wiping() else "false")
                                addon.setSetting("premiumize.enable", enabled_pm)

                                if str(chk_auth_infinity_rd) != '':
                                        enabled_rd = ("true")
                                        addon.setSetting("alldebrid.enable", enabled_rd)
                                else:
                                        enabled_rd = ("false")
                                        addon.setSetting("realdebrid.enable", enabled_rd)

                                if str(chk_auth_infinity_ad) != '':
                                        enabled_ad = ("true")
                                        addon.setSetting("alldebrid.enable", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("alldebrid.enable", enabled_ad)
        except:
                sync_support.failed('plugin.video.infinity')
                xbmc.log('%s: Infinity Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #Shadow PM
        try:
                        

                if xbmcvfs.exists(var.chk_shadow):
                        chk_auth_shadow = xbmcaddon.Addon('plugin.video.shadow').getSetting("premiumize.token")
                        chk_auth_shadow_rd = xbmcaddon.Addon('plugin.video.shadow').getSetting("rd.auth")
                        chk_auth_shadow_ad = xbmcaddon.Addon('plugin.video.shadow').getSetting("alldebrid.token")
                        if sync_support.needs('plugin.video.shadow', [('premiumize.token',your_pm_token)]):

                                addon = xbmcaddon.Addon("plugin.video.shadow")
                                addon.setSetting("premiumize.token", your_pm_token)

                                pm_use = ("true")
                                addon.setSetting("debrid_use_pm", pm_use)

                                if str(chk_auth_shadow_rd) != '':
                                        rd_use = ("true")
                                        addon.setSetting("debrid_use_rd", rd_use)
                                else:
                                        rd_use = ("false")
                                        addon.setSetting("debrid_use_rd", rd_use)
                        
                                if str(chk_auth_shadow_ad) != '':
                                        ad_use = ("true")
                                        addon.setSetting("debrid_use_ad", ad_use)
                                else:
                                        ad_use = ("false")
                                        addon.setSetting("debrid_use_ad", ad_use)
        except:
                sync_support.failed('plugin.video.shadow')
                xbmc.log('%s: Shadow Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Blue Balls PM
        try:


                if xbmcvfs.exists(var.chk_blueballs):
                        chk_auth_blueballs = xbmcaddon.Addon('plugin.video.blueballs').getSetting("premiumize.token")
                        if sync_support.needs('plugin.video.blueballs', [('premiumize.token',your_pm_token)]):

                                addon = xbmcaddon.Addon("plugin.video.blueballs")
                                addon.setSetting("premiumize.token", your_pm_token)

                                d_use = ("true")
                                addon.setSetting("debrid_use", d_use)

                                d_select = ("1")
                                addon.setSetting("debrid_select", d_select)
        except:
                sync_support.failed('plugin.video.blueballs')
                xbmc.log('%s: Blue Balls Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Twisted PM
        try:


                if xbmcvfs.exists(var.chk_twisted):
                        chk_auth_twisted = xbmcaddon.Addon('plugin.video.twisted').getSetting("premiumize.token")
                        chk_auth_twisted_rd = xbmcaddon.Addon('plugin.video.twisted').getSetting("rd.auth")
                        chk_auth_twisted_ad = xbmcaddon.Addon('plugin.video.twisted').getSetting("alldebrid.token")
                        if sync_support.needs('plugin.video.twisted', [('premiumize.token',your_pm_token)]):

                                addon = xbmcaddon.Addon("plugin.video.twisted")
                                addon.setSetting("premiumize.token", your_pm_token)

                                pm_use = ("true")
                                addon.setSetting("debrid_use_pm", pm_use)

                                if str(chk_auth_twisted_rd) != '':
                                        rd_use = ("true")
                                        addon.setSetting("debrid_use_rd", rd_use)
                                else:
                                        rd_use = ("false")
                                        addon.setSetting("debrid_use_rd", rd_use)

                                if str(chk_auth_twisted_ad) != '':
                                        ad_use = ("true")
                                        addon.setSetting("debrid_use_ad", ad_use)
                                else:
                                        ad_use = ("false")
                                        addon.setSetting("debrid_use_ad", ad_use)
        except:
                sync_support.failed('plugin.video.twisted')
                xbmc.log('%s: Twisted Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Aliunde K19 PM
        try:
                if xbmcvfs.exists(var.chk_aliunde):
                        chk_auth_aliunde = xbmcaddon.Addon('plugin.video.aliundek19').getSetting("premiumize.token")
                        chk_auth_aliunde_rd = xbmcaddon.Addon('plugin.video.aliundek19').getSetting("rd.auth")
                        chk_auth_aliunde_ad = xbmcaddon.Addon('plugin.video.aliundek19').getSetting("alldebrid.token")
                        if sync_support.needs('plugin.video.aliundek19', [('premiumize.token',your_pm_token)]):

                                addon = xbmcaddon.Addon("plugin.video.aliundek19")
                                addon.setSetting("premiumize.token", your_pm_token)

                                pm_use = ("true")
                                addon.setSetting("debrid_use_pm", pm_use)

                                if str(chk_auth_aliunde_rd) != '':
                                        rd_use = ("true")
                                        addon.setSetting("debrid_use_rd", rd_use)
                                else:
                                        rd_use = ("false")
                                        addon.setSetting("debrid_use_rd", rd_use)

                                if str(chk_auth_aliunde_ad) != '':
                                        ad_use = ("true")
                                        addon.setSetting("debrid_use_ad", ad_use)
                                else:
                                        ad_use = ("false")
                                        addon.setSetting("debrid_use_ad", ad_use)
        except:
                sync_support.failed('plugin.video.aliundek19')
                xbmc.log('%s: Aliunde K19 Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        
    #Ghost PM
        try:
                        

                if xbmcvfs.exists(var.chk_ghost):
                        chk_auth_ghost = xbmcaddon.Addon('plugin.video.ghost').getSetting("premiumize.token")
                        if sync_support.needs('plugin.video.ghost', [('premiumize.token',your_pm_token)]):
                                
                                addon = xbmcaddon.Addon("plugin.video.ghost")
                                addon.setSetting("premiumize.token", your_pm_token)

                                d_use = ("true")
                                addon.setSetting("debrid_use", d_use)
                                
                                d_select = ("1")
                                addon.setSetting("debrid_select", d_select)
        except:
                sync_support.failed('plugin.video.ghost')
                xbmc.log('%s: Ghost Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #Base PM
        try:
                        

                if xbmcvfs.exists(var.chk_base):
                        chk_auth_base = xbmcaddon.Addon('plugin.video.base').getSetting("premiumize.token")
                        if sync_support.needs('plugin.video.base', [('premiumize.token',your_pm_token)]):
                        
                                addon = xbmcaddon.Addon("plugin.video.base")
                                addon.setSetting("premiumize.token", your_pm_token)

                                d_select = ("1")
                                addon.setSetting("debrid_select", d_select)
        except:
                sync_support.failed('plugin.video.base')
                xbmc.log('%s: Base Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Chains PM
        try:
                        

                if xbmcvfs.exists(var.chk_chains):
                        chk_auth_chains = xbmcaddon.Addon('plugin.video.thechains').getSetting("premiumize.token")
                        if sync_support.needs('plugin.video.thechains', [('premiumize.token',your_pm_token)]):

                                addon = xbmcaddon.Addon("plugin.video.thechains")
                                addon.setSetting("premiumize.token", your_pm_token)

                                d_use = ("true")
                                addon.setSetting("debrid_use", d_use)
                                
                                d_select = ("1")
                                addon.setSetting("debrid_select", d_select)
        except:
                sync_support.failed('plugin.video.thechains')
                xbmc.log('%s: Chains Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Patriot PM
        try:
                        

                if xbmcvfs.exists(var.chk_patriot):
                        chk_auth_patriot = xbmcaddon.Addon('plugin.video.patriot').getSetting("premiumize.token")
                        if sync_support.needs('plugin.video.patriot', [('premiumize.token',your_pm_token)]):
                                
                                addon = xbmcaddon.Addon("plugin.video.patriot")
                                addon.setSetting("premiumize.token", your_pm_token)

                                rd_use = ("false")
                                addon.setSetting("debrid_use_rd", rd_use)

                                pm_use = ("true")
                                addon.setSetting("debrid_use_pm", pm_use)

                                ad_use = ("false")
                                addon.setSetting("debrid_use_ad", ad_use)

                                d_select = ("1")
                                addon.setSetting("debrid_select", d_select)
        except:
                sync_support.failed('plugin.video.patriot')
                xbmc.log('%s: Patriot Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Black Lightning PM
        try:
                        

                if xbmcvfs.exists(var.chk_blackl):
                        chk_auth_blackl = xbmcaddon.Addon('plugin.video.blacklightning').getSetting("premiumize.token")
                        chk_auth_blackl_rd = xbmcaddon.Addon('plugin.video.blacklightning').getSetting("rd.auth")
                        chk_auth_blackl_ad = xbmcaddon.Addon('plugin.video.blacklightning').getSetting("alldebrid.token")
                        if sync_support.needs('plugin.video.blacklightning', [('premiumize.token',your_pm_token)]):

                                addon = xbmcaddon.Addon("plugin.video.blacklightning")
                                addon.setSetting("premiumize.token", your_pm_token)

                                pm_use = ("true")
                                addon.setSetting("debrid_use_pm", pm_use)

                                if str(chk_auth_blackl_rd) != '':
                                        rd_use = ("true")
                                        addon.setSetting("debrid_use_rd", rd_use)
                                else:
                                        rd_use = ("false")
                                        addon.setSetting("debrid_use_rd", rd_use)
                        
                                if str(chk_auth_blackl_ad) != '':
                                        ad_use = ("true")
                                        addon.setSetting("debrid_use_ad", ad_use)
                                else:
                                        ad_use = ("false")
                                        addon.setSetting("debrid_use_ad", ad_use)
        except:
                sync_support.failed('plugin.video.blacklightning')
                xbmc.log('%s: Black Lightning Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

     #Chains Genocide PM
        try:
                        
                        
                if xbmcvfs.exists(var.chk_genocide):
                        chk_auth_genocide = xbmcaddon.Addon('plugin.video.chainsgenocide').getSetting("premiumize.token")
                        if sync_support.needs('plugin.video.chainsgenocide', [('premiumize.username',your_pm_username),('premiumize.token',your_pm_token)]):
                        
                                addon = xbmcaddon.Addon("plugin.video.chainsgenocide")
                                addon.setSetting("premiumize.username", your_pm_username)
                                addon.setSetting("premiumize.token", your_pm_token)
        except:
                sync_support.failed('plugin.video.chainsgenocide')
                xbmc.log('%s: Chains Genocide Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
     #Otaku PM
        try:
                if sync_support.installed('plugin.video.otaku'):
                        pairs = [('premiumize.username', your_pm_username), ('premiumize.token', your_pm_token),
                                 ('premiumize.enabled', ('true' if your_pm_token and not control.wiping() else 'false') if your_pm_token and not control.wiping() else 'false')]
                        if control.wiping():
                                pairs.append(('premiumize.auth.status', ''))
                        sync_support.put('plugin.video.otaku', pairs, wipe=control.wiping())
        except Exception:
                sync_support.failed('plugin.video.otaku')

     #Premiumizer PM
        try:
                        

                if xbmcvfs.exists(var.chk_premx):
                        chk_auth_premx = xbmcaddon.Addon('plugin.video.premiumizerx').getSetting("premiumize.token")
                        if sync_support.needs('plugin.video.premiumizerx', [('premiumize.token',your_pm_token)]):
                                
                                addon = xbmcaddon.Addon("plugin.video.premiumizerx")
                                addon.setSetting("premiumize.status", 'Authorized')
                                addon.setSetting("premiumize.token", your_pm_token)
                                addon.setSetting("premiumize.refresh", '315360000')
        except:
                sync_support.failed('plugin.video.premiumizerx')
                xbmc.log('%s: Premiumizer Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #All Accounts PM
        try:
                        
                        
                if xbmcvfs.exists(var.chk_allaccounts):
                        chk_auth_allaccounts = xbmcaddon.Addon('script.module.allaccounts').getSetting("premiumize.token")
                        if sync_support.needs('script.module.allaccounts', [('premiumize.username',your_pm_username),('premiumize.token',your_pm_token)]):
                        
                                addon = xbmcaddon.Addon("script.module.allaccounts")
                                addon.setSetting("premiumize.username", your_pm_username)
                                addon.setSetting("premiumize.token", your_pm_token)
        except:
                sync_support.failed('script.module.allaccounts')
                xbmc.log('%s: All Accounts Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #My Accounts PM
        try:
                        
                        
                if xbmcvfs.exists(var.chk_myaccounts):
                        chk_auth_myaccounts = xbmcaddon.Addon('script.module.myaccounts').getSetting("premiumize.token")
                        if sync_support.needs('script.module.myaccounts', [('premiumize.username',your_pm_username),('premiumize.token',your_pm_token)]):
                        
                                addon = xbmcaddon.Addon("script.module.myaccounts")
                                addon.setSetting("premiumize.username", your_pm_username)
                                addon.setSetting("premiumize.token", your_pm_token)
        except:
                sync_support.failed('script.module.myaccounts')
                xbmc.log('%s: My Accounts Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #ResolveURL PM
        try:
                        
                        
                if xbmcvfs.exists(var.chk_rurl):
                        chk_auth_rurl = xbmcaddon.Addon('script.module.resolveurl').getSetting("PremiumizeMeResolver_token")
                        if sync_support.needs('script.module.resolveurl', [('PremiumizeMeResolver_token',your_pm_token)]):
                        
                                addon = xbmcaddon.Addon("script.module.resolveurl")
                                addon.setSetting("PremiumizeMeResolver_token", your_pm_token)

                                cache_only = ("true")
                                addon.setSetting("PremiumizeMeResolver_cached_only", cache_only)
        except:
                sync_support.failed('script.module.resolveurl')
                xbmc.log('%s: ResolveURL Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Gears PM
        try:
                if sync_support.profile_ready('plugin.video.gears', var.gears_settings_db):

                    from reauthorize.modules.db import debrid_db
                    conn = debrid_db.create_conn(var.gears_settings_db)

                    with conn:
                        cursor = conn.cursor()
                        cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('pm.token',))
                        auth_pm = cursor.fetchone()
                        chk_auth_gears = str(auth_pm)
                        cursor.close()

                        for char in char_remov:
                            chk_auth_gears = chk_auth_gears.replace(char, "")

                        if not str(your_pm_token) == chk_auth_gears:
                            from reauthorize.modules.db import debrid_db
                            debrid_db.auth_gears_pm()
                            var.remake_settings()
        except:
                sync_support.failed('plugin.video.gears')
                xbmc.log('%s: Gears Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Genocide (plugin.video.genocide) PM
        try:
                if xbmcvfs.exists(var.chk_newgenocide):
                        chk_auth_newgenocide = xbmcaddon.Addon('plugin.video.genocide').getSetting("premiumize.token")
                        if sync_support.needs('plugin.video.genocide', [('premiumize.token',your_pm_token),('premiumize.username',your_pm_username)]):
                                addon = xbmcaddon.Addon("plugin.video.genocide")
                                addon.setSetting("premiumize.token", your_pm_token)
                                addon.setSetting("premiumize.username", your_pm_username)
        except:
                sync_support.failed('plugin.video.genocide')
                xbmc.log('%s: Genocide Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Orion PM
        try:
                if xbmcvfs.exists(var.chk_orion):
                        chk_auth_orion = xbmcaddon.Addon('plugin.video.orion').getSetting("pm_token")
                        if sync_support.needs('plugin.video.orion', [('pm_token',your_pm_token)]):
                                addon = xbmcaddon.Addon("plugin.video.orion")
                                addon.setSetting("pm_token", your_pm_token)
                                addon.setSetting("pm_enabled", ('true' if your_pm_token and not control.wiping() else 'false'))
        except:
                sync_support.failed('plugin.video.orion')
                xbmc.log('%s: Orion Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Red Light PM
        try:
                from reauthorize.modules.db import redlight_db
                redlight_db.push([('pm.token', your_pm_token),
                                  ('pm.account_id', your_pm_username),
                                  ('pm.enabled', ('true' if your_pm_token and not control.wiping() else 'false'))])
        except:
                sync_support.failed()
                xbmc.log('%s: Red Light Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Cosmos PM
        try:
                if xbmcvfs.exists(var.chk_cosmos):
                        chk_auth_cosmos = xbmcaddon.Addon('plugin.video.cosmos').getSetting("pm_access_token")
                        if sync_support.needs('plugin.video.cosmos', [('pm_access_token',your_pm_token)]):
                                addon = xbmcaddon.Addon("plugin.video.cosmos")
                                addon.setSetting("pm_access_token", your_pm_token)
                                addon.setSetting("pm_auth_done", ('true' if your_pm_token and not control.wiping() else 'false'))
        except:
                sync_support.failed('plugin.video.cosmos')
                xbmc.log('%s: Cosmos Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #The Archives PM
        try:
                if xbmcvfs.exists(var.chk_thearchives):
                        chk_auth_thearchives = xbmcaddon.Addon('plugin.video.thearchives').getSetting("pm.token")
                        if sync_support.needs('plugin.video.thearchives', [('pm.token',your_pm_token)]):
                                addon = xbmcaddon.Addon("plugin.video.thearchives")
                                addon.setSetting("pm.token", your_pm_token)
                                addon.setSetting("pm.enabled", ('true' if your_pm_token and not control.wiping() else 'false'))
        except:
                sync_support.failed('plugin.video.thearchives')
                xbmc.log('%s: The Archives Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Diamond Media Player Premiumize
        try:
                if xbmcvfs.exists(var.chk_rdtplayer):
                        chk_auth_rdtplayer = xbmcaddon.Addon('plugin.program.rdtplayer').getSetting("premiumize_api_key")
                        if sync_support.needs('plugin.program.rdtplayer', [('premiumize_api_key',your_pm_token)]):
                                addon = xbmcaddon.Addon("plugin.program.rdtplayer")
                                addon.setSetting("premiumize_api_key", your_pm_token)
        except:
                sync_support.failed('plugin.program.rdtplayer')
                xbmc.log('%s: Diamond Media Player Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Prism Premiumize
    #premiumize.username matters, not just cosmetic: Prism's own OAuth flow
    #(resources/lib/debrid/premiumize.py's _poll_token) always sets it from a
    #live account_info() call right after the token, and its settings screen
    #reads it to show "authorized" - a token with enabled=true but no username
    #still displays as unauthorized. Confirmed live: Prism showed Premiumize as
    #not authorized with only token+enabled set, on a real box, 2026-09-28.
        try:
                if xbmcvfs.exists(var.chk_prism):
                        chk_auth_prism = xbmcaddon.Addon('plugin.video.prism').getSetting("premiumize.token")
                        chk_user_prism = xbmcaddon.Addon('plugin.video.prism').getSetting("premiumize.username")
                        # A token synced before this username fix existed matches on every later
                        # ReSync and never re-enters this block, so username stays blank forever
                        # unless a mismatch on username alone can also trigger the write. Confirmed
                        # live, 2026-09-29: token+enabled matched already, username never backfilled.
                        if sync_support.needs('plugin.video.prism', [('premiumize.token',your_pm_token),('premiumize.username',your_pm_username)]):
                                addon = xbmcaddon.Addon("plugin.video.prism")
                                addon.setSetting("premiumize.token", your_pm_token)
                                addon.setSetting("premiumize.username", your_pm_username)
                                addon.setSetting("premiumize.enabled", ('true' if your_pm_token and not control.wiping() else 'false'))
        except:
                sync_support.failed('plugin.video.prism')
                xbmc.log('%s: Prism Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    # TMDb Movies cloud account
        try:
            from reauthorize.modules.sync import tmdbmovies_sync
            tmdbmovies_sync.cloud('pm_api_key', your_pm_token, wipe=control.wiping())
        except Exception:
            sync_support.failed('plugin.video.tmdbmovies')
            xbmc.log('%s: TMDb Movies cloud status could not be saved.' % var.amgr, xbmc.LOGWARNING)

    #Youtube Theater Premiumize
        try:
                if xbmcvfs.exists(var.chk_youtubetheater):
                        chk_auth_ytheater = xbmcaddon.Addon('plugin.video.youtubetheater').getSetting("premiumize.token")
                        if sync_support.needs('plugin.video.youtubetheater', [('premiumize.token',your_pm_token)]):
                                addon = xbmcaddon.Addon("plugin.video.youtubetheater")
                                addon.setSetting("premiumize.token", your_pm_token)
                                addon.setSetting("debrid_use_pm", ('true' if your_pm_token and not control.wiping() else 'false'))
        except:
                sync_support.failed('plugin.video.youtubetheater')
                xbmc.log('%s: Youtube Theater Premiumize Failed!' % var.amgr, xbmc.LOGINFO)
                pass

