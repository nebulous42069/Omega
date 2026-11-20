from reauthorize.modules import sync_support
import xbmc, xbmcaddon
import xbmcvfs
import os
import json

from pathlib import Path
from reauthorize.modules import control
from libs.common import var

char_remov = ["'", ",", ")","("]

#Account Manager Real-Debrid
# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr
your_rd_username = accountmgr.getSetting("realdebrid.username")
your_rd_token = accountmgr.getSetting("realdebrid.token")
your_rd_client_id = accountmgr.getSetting("realdebrid.client_id")
your_rd_refresh = accountmgr.getSetting("realdebrid.refresh")
your_rd_secret = accountmgr.getSetting("realdebrid.secret")


from reauthorize.modules import sync_support
xbmcaddon = sync_support.addon_api(xbmcaddon)
class Auth:
    def realdebrid_auth(self):
        sync_support.put('plugin.video.seren', [
            ('rd.username', your_rd_username),
            ('rd.auth', your_rd_token),
            ('rd.client_id', your_rd_client_id),
            ('rd.refresh', your_rd_refresh),
            ('rd.secret', your_rd_secret),
            ('realdebrid.enabled', ('true' if your_rd_token and not control.wiping() else 'false') if your_rd_token else 'false'),
        ], wipe=control.wiping())

    #Coalition RD
        try:
                if xbmcvfs.exists(var.chk_coal):
                        chk_auth_coal = xbmcaddon.Addon('plugin.video.coalition').getSetting("rd.token")
                        chk_auth_coal_pm = xbmcaddon.Addon('plugin.video.coalition').getSetting("pm.token")
                        chk_auth_coal_ad = xbmcaddon.Addon('plugin.video.coalition').getSetting("ad.token")
                        if sync_support.needs('plugin.video.coalition', [('rd.username',your_rd_username),('rd.token',your_rd_token),('rd.client_id',your_rd_client_id),('rd.refresh',your_rd_refresh),('rd.secret',your_rd_secret)]):

                                addon = xbmcaddon.Addon("plugin.video.coalition")
                                addon.setSetting("rd.username", your_rd_username)
                                addon.setSetting("rd.token", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)

                                enabled_rd = ("true" if your_rd_token and not control.wiping() else "false")
                                addon.setSetting("rd.enabled", enabled_rd)

                                if str(chk_auth_coal_pm) != '':
                                        enabled_pm = ("true")
                                        addon.setSetting("pm.enabled", enabled_pm)
                                else:
                                        enabled_pm = ("false")
                                        addon.setSetting("pm.enabled", enabled_pm)
                        
                                if str(chk_auth_coal_ad) != '':
                                        enabled_ad = ("true")
                                        addon.setSetting("ad.enabled", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("ad.enabled", enabled_ad)
        except:
                sync_support.failed('plugin.video.coalition')
                xbmc.log('%s: Coalition Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #POV RD
        try:
                if xbmcvfs.exists(var.chk_pov):
                        addon = xbmcaddon.Addon('plugin.video.pov')
                        account_key = 'rd.account_id' if 'rd.account_id' in (addon.schema or {}) else 'rd.username'
                        sync_support.put('plugin.video.pov', [
                            (account_key, your_rd_username),
                            ('rd.client_id', your_rd_client_id),
                            ('rd.secret', your_rd_secret),
                            ('rd.refresh', your_rd_refresh),
                            ('rd.token', your_rd_token),
                            ('rd.enabled', ('true' if your_rd_token and not control.wiping() else 'false') if your_rd_token else 'false'),
                        ], wipe=control.wiping())
        except:
                sync_support.failed('plugin.video.pov')
                xbmc.log('%s: POV Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Umbrella RD
        try:
            if xbmcvfs.exists(var.chk_umb) and ((your_rd_token) or control.wiping()):
                sync_support.put('plugin.video.umbrella', [('realdebridusername', '' if control.wiping() else your_rd_username), ('realdebridtoken', '' if control.wiping() else your_rd_token), ('realdebrid.clientid', '' if control.wiping() else your_rd_client_id), ('realdebridrefresh', '' if control.wiping() else your_rd_refresh), ('realdebridsecret', '' if control.wiping() else your_rd_secret), ('realdebrid.enable', 'true' if your_rd_token and not control.wiping() else 'false')], wipe=control.wiping())
        except:
                sync_support.failed('plugin.video.umbrella')
                xbmc.log('%s: Umbrella Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Infinity RD
        try:
                if xbmcvfs.exists(var.chk_infinity):
                        chk_auth_infinity = xbmcaddon.Addon('plugin.video.infinity').getSetting("realdebridtoken")
                        chk_auth_infinity_pm = xbmcaddon.Addon('plugin.video.infinity').getSetting("premiumizetoken")
                        chk_auth_infinity_ad = xbmcaddon.Addon('plugin.video.infinity').getSetting("alldebridtoken")
                        if sync_support.needs('plugin.video.infinity', [('realdebridusername',your_rd_username),('realdebridtoken',your_rd_token),('realdebrid.clientid',your_rd_client_id),('realdebridrefresh',your_rd_refresh),('realdebridsecret',your_rd_secret)]):
                        
                                addon = xbmcaddon.Addon("plugin.video.infinity")
                                addon.setSetting("realdebridusername", your_rd_username)
                                addon.setSetting("realdebridtoken", your_rd_token)
                                addon.setSetting("realdebrid.clientid", your_rd_client_id)
                                addon.setSetting("realdebridrefresh", your_rd_refresh)
                                addon.setSetting("realdebridsecret", your_rd_secret)

                                enabled_rd = ("true" if your_rd_token and not control.wiping() else "false")
                                addon.setSetting("realdebrid.enable", enabled_rd)

                 
                                if str(chk_auth_infinity_pm) != '':
                                        enabled_pm = ("true")
                                        addon.setSetting("premiumize.enable", enabled_pm)
                                else:
                                        enabled_pm = ("false")
                                        addon.setSetting("premiumize.enable", enabled_pm)

                                if str(chk_auth_infinity_ad) != '':
                                        enabled_ad = ("true")
                                        addon.setSetting("alldebrid.enable", enabled_ad)
                                else:
                                        enabled_ad = ("false")
                                        addon.setSetting("alldebrid.enable", enabled_ad)
        except:
                sync_support.failed('plugin.video.infinity')
                xbmc.log('%s: Infinity Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #Shadow RD
        try:
                        

                if xbmcvfs.exists(var.chk_shadow):
                        chk_auth_shadow = xbmcaddon.Addon('plugin.video.shadow').getSetting("rd.auth")
                        chk_auth_shadow_pm = xbmcaddon.Addon('plugin.video.shadow').getSetting("premiumize.token")
                        chk_auth_shadow_ad = xbmcaddon.Addon('plugin.video.shadow').getSetting("alldebrid.token")
                        if sync_support.needs('plugin.video.shadow', [('rd.auth',your_rd_token),('rd.client_id',your_rd_client_id),('rd.refresh',your_rd_refresh),('rd.secret',your_rd_secret)]):

                                addon = xbmcaddon.Addon("plugin.video.shadow")
                                addon.setSetting("rd.auth", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)

                                rd_use = ("true")
                                addon.setSetting("debrid_use_rd", rd_use)

                                if str(chk_auth_shadow_pm) != '':
                                        pm_use = ("true")
                                        addon.setSetting("debrid_use_pm", pm_use)
                                else:
                                        pm_use = ("false")
                                        addon.setSetting("debrid_use_pm", pm_use)
                                        
                                if str(chk_auth_shadow_ad) != '':
                                        ad_use = ("true")
                                        addon.setSetting("debrid_use_ad", ad_use)
                                else:
                                        ad_use = ("false")
                                        addon.setSetting("debrid_use_ad", ad_use)
        except:
                sync_support.failed('plugin.video.shadow')
                xbmc.log('%s: Shadow Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
        
    #Ghost RD
        try:
                        

                if xbmcvfs.exists(var.chk_ghost):
                        chk_auth_ghost = xbmcaddon.Addon('plugin.video.ghost').getSetting("rd.auth")
                        if sync_support.needs('plugin.video.ghost', [('rd.auth',your_rd_token),('rd.client_id',your_rd_client_id),('rd.refresh',your_rd_refresh),('rd.secret',your_rd_secret)]):

                                addon = xbmcaddon.Addon("plugin.video.ghost")
                                addon.setSetting("rd.auth", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)

                                d_use = ("true")
                                addon.setSetting("debrid_use", d_use)
                                
                                d_select = ("0")
                                addon.setSetting("debrid_select", d_select)
        except:
                sync_support.failed('plugin.video.ghost')
                xbmc.log('%s: Ghost Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Blue Balls RD
        try:


                if xbmcvfs.exists(var.chk_blueballs):
                        chk_auth_blueballs = xbmcaddon.Addon('plugin.video.blueballs').getSetting("rd.auth")
                        if sync_support.needs('plugin.video.blueballs', [('rd.auth',your_rd_token),('rd.client_id',your_rd_client_id),('rd.refresh',your_rd_refresh),('rd.secret',your_rd_secret)]):

                                addon = xbmcaddon.Addon("plugin.video.blueballs")
                                addon.setSetting("rd.auth", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)

                                d_use = ("true")
                                addon.setSetting("debrid_use", d_use)

                                d_select = ("0")
                                addon.setSetting("debrid_select", d_select)
        except:
                sync_support.failed('plugin.video.blueballs')
                xbmc.log('%s: Blue Balls Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Twisted RD
        try:


                if xbmcvfs.exists(var.chk_twisted):
                        chk_auth_twisted = xbmcaddon.Addon('plugin.video.twisted').getSetting("rd.auth")
                        chk_auth_twisted_pm = xbmcaddon.Addon('plugin.video.twisted').getSetting("premiumize.token")
                        chk_auth_twisted_ad = xbmcaddon.Addon('plugin.video.twisted').getSetting("alldebrid.token")
                        if sync_support.needs('plugin.video.twisted', [('rd.auth',your_rd_token),('rd.client_id',your_rd_client_id),('rd.refresh',your_rd_refresh),('rd.secret',your_rd_secret)]):

                                addon = xbmcaddon.Addon("plugin.video.twisted")
                                addon.setSetting("rd.auth", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)

                                rd_use = ("true")
                                addon.setSetting("debrid_use_rd", rd_use)

                                if str(chk_auth_twisted_pm) != '':
                                        pm_use = ("true")
                                        addon.setSetting("debrid_use_pm", pm_use)
                                else:
                                        pm_use = ("false")
                                        addon.setSetting("debrid_use_pm", pm_use)

                                if str(chk_auth_twisted_ad) != '':
                                        ad_use = ("true")
                                        addon.setSetting("debrid_use_ad", ad_use)
                                else:
                                        ad_use = ("false")
                                        addon.setSetting("debrid_use_ad", ad_use)
        except:
                sync_support.failed('plugin.video.twisted')
                xbmc.log('%s: Twisted Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Aliunde K19 RD
        try:
                if xbmcvfs.exists(var.chk_aliunde):
                        chk_auth_aliunde = xbmcaddon.Addon('plugin.video.aliundek19').getSetting("rd.auth")
                        chk_auth_aliunde_pm = xbmcaddon.Addon('plugin.video.aliundek19').getSetting("premiumize.token")
                        chk_auth_aliunde_ad = xbmcaddon.Addon('plugin.video.aliundek19').getSetting("alldebrid.token")
                        if sync_support.needs('plugin.video.aliundek19', [('rd.auth',your_rd_token),('rd.client_id',your_rd_client_id),('rd.refresh',your_rd_refresh),('rd.secret',your_rd_secret)]):

                                addon = xbmcaddon.Addon("plugin.video.aliundek19")
                                addon.setSetting("rd.auth", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)

                                rd_use = ("true")
                                addon.setSetting("debrid_use_rd", rd_use)

                                if str(chk_auth_aliunde_pm) != '':
                                        pm_use = ("true")
                                        addon.setSetting("debrid_use_pm", pm_use)
                                else:
                                        pm_use = ("false")
                                        addon.setSetting("debrid_use_pm", pm_use)

                                if str(chk_auth_aliunde_ad) != '':
                                        ad_use = ("true")
                                        addon.setSetting("debrid_use_ad", ad_use)
                                else:
                                        ad_use = ("false")
                                        addon.setSetting("debrid_use_ad", ad_use)
        except:
                sync_support.failed('plugin.video.aliundek19')
                xbmc.log('%s: Aliunde K19 Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Base RD
        try:
                        

                if xbmcvfs.exists(var.chk_base):
                        chk_auth_base = xbmcaddon.Addon('plugin.video.base').getSetting("rd.auth")
                        if sync_support.needs('plugin.video.base', [('rd.auth',your_rd_token),('rd.client_id',your_rd_client_id),('rd.refresh',your_rd_refresh),('rd.secret',your_rd_secret)]):

                                addon = xbmcaddon.Addon("plugin.video.base")
                                addon.setSetting("rd.auth", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)

                                d_select = ("0")
                                addon.setSetting("debrid_select", d_select)
        except:
                sync_support.failed('plugin.video.base')
                xbmc.log('%s: Base Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Chains RD
        try:
                        

                if xbmcvfs.exists(var.chk_chains):
                        chk_auth_chains = xbmcaddon.Addon('plugin.video.thechains').getSetting("rd.auth")
                        if sync_support.needs('plugin.video.thechains', [('rd.auth',your_rd_token),('rd.client_id',your_rd_client_id),('rd.refresh',your_rd_refresh),('rd.secret',your_rd_secret)]):

                                addon = xbmcaddon.Addon("plugin.video.thechains")
                                addon.setSetting("rd.auth", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)

                                d_use = ("true")
                                addon.setSetting("debrid_use", d_use)
                                
                                d_select = ("0")
                                addon.setSetting("debrid_select", d_select)
        except:
                sync_support.failed('plugin.video.thechains')
                xbmc.log('%s: Chains Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Patriot RD
        try:
                        

                if xbmcvfs.exists(var.chk_patriot):
                        chk_auth_patriot = xbmcaddon.Addon('plugin.video.patriot').getSetting("rd.auth")
                        if sync_support.needs('plugin.video.patriot', [('rd.auth',your_rd_token),('rd.client_id',your_rd_client_id),('rd.refresh',your_rd_refresh),('rd.secret',your_rd_secret)]):

                                addon = xbmcaddon.Addon("plugin.video.patriot")
                                addon.setSetting("rd.auth", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)

                                d_select = ("0")
                                addon.setSetting("debrid_select", d_select)
        except:
                sync_support.failed('plugin.video.patriot')
                xbmc.log('%s: Patriot Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Black Lightning RD
        try:
                        

                if xbmcvfs.exists(var.chk_blackl):
                        chk_auth_blackl = xbmcaddon.Addon('plugin.video.blacklightning').getSetting("rd.auth")
                        chk_auth_blackl_pm = xbmcaddon.Addon('plugin.video.blacklightning').getSetting("premiumize.token")
                        chk_auth_blackl_ad = xbmcaddon.Addon('plugin.video.blacklightning').getSetting("alldebrid.token")
                        if sync_support.needs('plugin.video.blacklightning', [('rd.auth',your_rd_token),('rd.client_id',your_rd_client_id),('rd.refresh',your_rd_refresh),('rd.secret',your_rd_secret)]):

                                addon = xbmcaddon.Addon("plugin.video.blacklightning")
                                addon.setSetting("rd.auth", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)

                                rd_use = ("true")
                                addon.setSetting("debrid_use_rd", rd_use)

                                if str(chk_auth_blackl_pm) != '':
                                        pm_use = ("true")
                                        addon.setSetting("debrid_use_pm", pm_use)
                                else:
                                        pm_use = ("false")
                                        addon.setSetting("debrid_use_pm", pm_use)
                                        
                                if str(chk_auth_blackl_ad) != '':
                                        ad_use = ("true")
                                        addon.setSetting("debrid_use_ad", ad_use)
                                else:
                                        ad_use = ("false")
                                        addon.setSetting("debrid_use_ad", ad_use)
        except:
                sync_support.failed('plugin.video.blacklightning')
                xbmc.log('%s: Black Lightning Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Chains Genocide RD
        try:
                        
                        
                if xbmcvfs.exists(var.chk_genocide):
                        chk_auth_genocide = xbmcaddon.Addon('plugin.video.chainsgenocide').getSetting("realdebrid.token")
                        if sync_support.needs('plugin.video.chainsgenocide', [('realdebrid.username',your_rd_username),('realdebrid.token',your_rd_token),('realdebrid.client_id',your_rd_client_id),('realdebrid.refresh',your_rd_refresh),('realdebrid.secret',your_rd_secret)]):

                                addon = xbmcaddon.Addon("plugin.video.chainsgenocide")
                                addon.setSetting("realdebrid.username", your_rd_username)
                                addon.setSetting("realdebrid.token", your_rd_token)
                                addon.setSetting("realdebrid.client_id", your_rd_client_id)
                                addon.setSetting("realdebrid.refresh", your_rd_refresh)
                                addon.setSetting("realdebrid.secret", your_rd_secret)
        except:
                sync_support.failed('plugin.video.chainsgenocide')
                xbmc.log('%s: Chains Genocide Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
        # Otaku moved its Real-Debrid settings from rd.* to realdebrid.*.
        try:
            if xbmcvfs.exists(var.chk_otaku):
                addon = xbmcaddon.Addon('plugin.video.otaku')
                current = 'realdebrid.token' in (addon.schema or {})
                prefix = 'realdebrid.' if current else 'rd.'
                token_key = prefix + ('token' if current else 'auth')
                pairs = [
                    (prefix + 'username', your_rd_username),
                    (prefix + 'client_id', your_rd_client_id),
                    (prefix + 'secret', your_rd_secret),
                    (prefix + 'refresh', your_rd_refresh),
                ]
                if current:
                    expiry = control.setting('realdebrid.expires')
                    if control.wiping() or expiry.isdigit():
                        pairs.append(('realdebrid.expiry', '0' if control.wiping() else expiry))
                    if control.wiping():
                        pairs.append(('realdebrid.auth.status', ''))
                pairs.extend([
                    (token_key, your_rd_token),
                    ('realdebrid.enabled', ('true' if your_rd_token and not control.wiping() else 'false') if your_rd_token else 'false'),
                ])
                sync_support.put('plugin.video.otaku', pairs, wipe=control.wiping())
        except Exception:
            sync_support.failed('plugin.video.otaku')
            xbmc.log('%s: Otaku Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)

        # RealizerX keeps credentials in its own JSON file.
        try:
            if xbmcvfs.exists(var.chk_realx) and (your_rd_token or control.wiping()):
                from libs import jsonit
                jsonit.write_realizer_auth({
                    'client_id': accountmgr.getSetting('realdebrid.client_id'),
                    'client_secret': accountmgr.getSetting('realdebrid.secret'),
                    'token': your_rd_token,
                    'refresh_token': accountmgr.getSetting('realdebrid.refresh'),
                    'added': '202312010243',
                })
        except Exception:
            sync_support.failed('plugin.video.realizerx')
            xbmc.log('%s: Realizer Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)

    #All Accounts RD
        try:
                        
                        
                if xbmcvfs.exists(var.chk_allaccounts):
                        chk_auth_allaccounts = xbmcaddon.Addon('script.module.allaccounts').getSetting("realdebrid.token")
                        if sync_support.needs('script.module.allaccounts', [('realdebrid.username',your_rd_username),('realdebrid.token',your_rd_token),('realdebrid.client_id',your_rd_client_id),('realdebrid.refresh',your_rd_refresh),('realdebrid.secret',your_rd_secret)]):

                                addon = xbmcaddon.Addon("script.module.allaccounts")
                                addon.setSetting("realdebrid.username", your_rd_username)
                                addon.setSetting("realdebrid.token", your_rd_token)
                                addon.setSetting("realdebrid.client_id", your_rd_client_id)
                                addon.setSetting("realdebrid.refresh", your_rd_refresh)
                                addon.setSetting("realdebrid.secret", your_rd_secret)
        except:
                sync_support.failed('script.module.allaccounts')
                xbmc.log('%s: All Accounts Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #My Accounts RD
        try:
                        
                        
                if xbmcvfs.exists(var.chk_myaccounts):
                        chk_auth_myaccounts = xbmcaddon.Addon('script.module.myaccounts').getSetting("realdebrid.token")
                        if sync_support.needs('script.module.myaccounts', [('realdebrid.username',your_rd_username),('realdebrid.token',your_rd_token),('realdebrid.client_id',your_rd_client_id),('realdebrid.refresh',your_rd_refresh),('realdebrid.secret',your_rd_secret)]):

                                addon = xbmcaddon.Addon("script.module.myaccounts")
                                addon.setSetting("realdebrid.username", your_rd_username)
                                addon.setSetting("realdebrid.token", your_rd_token)
                                addon.setSetting("realdebrid.client_id", your_rd_client_id)
                                addon.setSetting("realdebrid.refresh", your_rd_refresh)
                                addon.setSetting("realdebrid.secret", your_rd_secret)
        except:
                sync_support.failed('script.module.myaccounts')
                xbmc.log('%s: My Accounts Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass
            
    #ResolveURL RD
        try:
                        
                    
                if xbmcvfs.exists(var.chk_rurl):
                        chk_auth_rurl = xbmcaddon.Addon('script.module.resolveurl').getSetting("RealDebridResolver_token")
                        
                        if sync_support.needs('script.module.resolveurl', [('RealDebridResolver_login',your_rd_username),('RealDebridResolver_token',your_rd_token),('RealDebridResolver_client_id',your_rd_client_id),('RealDebridResolver_refresh',your_rd_refresh),('RealDebridResolver_client_secret',your_rd_secret)]):
                                addon = xbmcaddon.Addon("script.module.resolveurl")
                                addon.setSetting("RealDebridResolver_login", ('true' if your_rd_token and not control.wiping() else 'false'))
                                addon.setSetting("RealDebridResolver_token", your_rd_token)
                                addon.setSetting("RealDebridResolver_client_id", your_rd_client_id)
                                addon.setSetting("RealDebridResolver_refresh", your_rd_refresh)
                                addon.setSetting("RealDebridResolver_client_secret", your_rd_secret)

                                cache_only = ("true")
                                addon.setSetting("RealDebridResolver_cached_only", cache_only)
        except:
                sync_support.failed('script.module.resolveurl')
                xbmc.log('%s: ResolveURL Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Gears RD
        try:
                if sync_support.profile_ready('plugin.video.gears', var.gears_settings_db):

                    from reauthorize.modules.db import debrid_db
                    conn = debrid_db.create_conn(var.gears_settings_db)

                    with conn:
                        cursor = conn.cursor()
                        cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('rd.token',))
                        auth_rd = cursor.fetchone()
                        chk_auth_gears = str(auth_rd)

                        cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('pm.token',))
                        auth_pm = cursor.fetchone()
                        chk_auth_gears_pm = str(auth_pm)

                        cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('ad.token',))
                        auth_ad = cursor.fetchone()
                        chk_auth_gears_ad = str(auth_ad)
                        cursor.close()

                        for char in char_remov:
                            chk_auth_gears = chk_auth_gears.replace(char, "")

                        if not str(your_rd_token) == chk_auth_gears:

                            from reauthorize.modules.db import debrid_db
                            debrid_db.auth_gears_rd()

                            for char in char_remov:
                                chk_auth_gears_pm = chk_auth_gears_pm.replace(char, "")

                            if chk_auth_gears_pm != 'empty_setting' or chk_auth_gears_pm != '' or chk_auth_gears_pm != None:
                                from reauthorize.modules.db import debrid_db
                                debrid_db.enable_gears_pm()
                            else:
                                from reauthorize.modules.db import debrid_db
                                debrid_db.disable_gears_pm()

                            for char in char_remov:
                                chk_auth_gears_ad = chk_auth_gears_ad.replace(char, "")

                            if chk_auth_gears_ad != 'empty_setting' or chk_auth_gears_ad != '' or chk_auth_gears_ad != None:
                                from reauthorize.modules.db import debrid_db
                                debrid_db.enable_gears_ad()
                            else:
                                from reauthorize.modules.db import debrid_db
                                debrid_db.disable_gears_ad()
                            var.remake_settings()
        except:
                sync_support.failed('plugin.video.gears')
                xbmc.log('%s: Gears Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Genocide (plugin.video.genocide) RD
        try:
                if xbmcvfs.exists(var.chk_newgenocide):
                        chk_auth_newgenocide = xbmcaddon.Addon('plugin.video.genocide').getSetting("realdebrid.token")
                        if sync_support.needs('plugin.video.genocide', [('realdebrid.token',your_rd_token),('realdebrid.username',your_rd_username),('realdebrid.client_id',your_rd_client_id),('realdebrid.refresh',your_rd_refresh),('realdebrid.secret',your_rd_secret)]):
                                addon = xbmcaddon.Addon("plugin.video.genocide")
                                addon.setSetting("realdebrid.token", your_rd_token)
                                addon.setSetting("realdebrid.username", your_rd_username)
                                addon.setSetting("realdebrid.client_id", your_rd_client_id)
                                addon.setSetting("realdebrid.refresh", your_rd_refresh)
                                addon.setSetting("realdebrid.secret", your_rd_secret)
                                addon.setSetting("realdebrid.enable", ('true' if your_rd_token and not control.wiping() else 'false'))
        except:
                sync_support.failed('plugin.video.genocide')
                xbmc.log('%s: Genocide Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Orion RD
        try:
                if xbmcvfs.exists(var.chk_orion):
                        chk_auth_orion = xbmcaddon.Addon('plugin.video.orion').getSetting("rd_token")
                        if sync_support.needs('plugin.video.orion', [('rd_token',your_rd_token),('rd_refresh',your_rd_refresh),('rd_client_id',your_rd_client_id),('rd_client_secret',your_rd_secret)]):
                                addon = xbmcaddon.Addon("plugin.video.orion")
                                addon.setSetting("rd_token", your_rd_token)
                                addon.setSetting("rd_refresh", your_rd_refresh)
                                addon.setSetting("rd_client_id", your_rd_client_id)
                                addon.setSetting("rd_client_secret", your_rd_secret)
                                # No rd_expires: ReAuthorize never stores a
                                # Real-Debrid expiry, it reads it live from the
                                # API. The line that used to be here referenced
                                # an undefined name, so it raised every time and
                                # the bare except swallowed it - which meant
                                # rd_enabled below never ran and Orion got a
                                # token it would not use.
                                addon.setSetting("rd_enabled", ('true' if your_rd_token and not control.wiping() else 'false'))
        except:
                sync_support.failed('plugin.video.orion')
                xbmc.log('%s: Orion Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Red Light RD
        try:
                from reauthorize.modules.db import redlight_db
                redlight_db.push([('rd.token', your_rd_token),
                                  ('rd.refresh', your_rd_refresh),
                                  ('rd.client_id', your_rd_client_id),
                                  ('rd.secret', your_rd_secret),
                                  ('rd.account_id', your_rd_username),
                                  ('rd.enabled', ('true' if your_rd_token and not control.wiping() else 'false'))])
        except:
                sync_support.failed()
                xbmc.log('%s: Red Light Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Cosmos RD
        try:
                if xbmcvfs.exists(var.chk_cosmos):
                        chk_auth_cosmos = xbmcaddon.Addon('plugin.video.cosmos').getSetting("rd_access_token")
                        if sync_support.needs('plugin.video.cosmos', [('rd_access_token',your_rd_token),('rd_refresh_token',your_rd_refresh),('rd_client_id',your_rd_client_id),('rd_client_secret',your_rd_secret)]):
                                addon = xbmcaddon.Addon("plugin.video.cosmos")
                                addon.setSetting("rd_access_token", your_rd_token)
                                addon.setSetting("rd_refresh_token", your_rd_refresh)
                                addon.setSetting("rd_client_id", your_rd_client_id)
                                addon.setSetting("rd_client_secret", your_rd_secret)
                                addon.setSetting("rd_auth_done", ('true' if your_rd_token and not control.wiping() else 'false'))
        except:
                sync_support.failed('plugin.video.cosmos')
                xbmc.log('%s: Cosmos Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #The Archives RD
        try:
                if xbmcvfs.exists(var.chk_thearchives):
                        chk_auth_thearchives = xbmcaddon.Addon('plugin.video.thearchives').getSetting("rd.token")
                        chk_auth_thearchives_pm = xbmcaddon.Addon('plugin.video.thearchives').getSetting("pm.token")
                        chk_auth_thearchives_ad = xbmcaddon.Addon('plugin.video.thearchives').getSetting("ad.token")
                        if sync_support.needs('plugin.video.thearchives', [('rd.token',your_rd_token),('rd.client_id',your_rd_client_id),('rd.refresh',your_rd_refresh),('rd.secret',your_rd_secret)]):

                                addon = xbmcaddon.Addon("plugin.video.thearchives")
                                addon.setSetting("rd.token", your_rd_token)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.secret", your_rd_secret)
                                addon.setSetting("rd.enabled", ('true' if your_rd_token and not control.wiping() else 'false'))

                                if str(chk_auth_thearchives_pm) != '':
                                        addon.setSetting("pm.enabled", 'true')
                                else:
                                        addon.setSetting("pm.enabled", 'false')

                                if str(chk_auth_thearchives_ad) != '':
                                        addon.setSetting("ad.enabled", 'true')
                                else:
                                        addon.setSetting("ad.enabled", 'false')
        except:
                sync_support.failed('plugin.video.thearchives')
                xbmc.log('%s: The Archives Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Diamond Media Player RD
        try:
                if xbmcvfs.exists(var.chk_rdtplayer):
                        chk_auth_rdtplayer = xbmcaddon.Addon('plugin.program.rdtplayer').getSetting("api_key")
                        if sync_support.needs('plugin.program.rdtplayer', [('api_key',your_rd_token)]):
                                addon = xbmcaddon.Addon("plugin.program.rdtplayer")
                                addon.setSetting("api_key", your_rd_token)
        except:
                sync_support.failed('plugin.program.rdtplayer')
                xbmc.log('%s: Diamond Media Player Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    #Prism RD
        try:
                if xbmcvfs.exists(var.chk_prism):
                        chk_auth_prism = xbmcaddon.Addon('plugin.video.prism').getSetting("rd.auth")
                        if sync_support.needs('plugin.video.prism', [('rd.auth',your_rd_token),('rd.refresh',your_rd_refresh),('rd.client_id',your_rd_client_id),('rd.secret',your_rd_secret)]):
                                addon = xbmcaddon.Addon("plugin.video.prism")
                                addon.setSetting("rd.auth", your_rd_token)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.secret", your_rd_secret)
                                addon.setSetting("realdebrid.enabled", ('true' if your_rd_token and not control.wiping() else 'false'))
        except:
                sync_support.failed('plugin.video.prism')
                xbmc.log('%s: Prism Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

    # TMDb Movies cloud account
        try:
            from reauthorize.modules.sync import tmdbmovies_sync
            tmdbmovies_sync.cloud('rd_api_key', your_rd_token, wipe=control.wiping())
        except Exception:
            sync_support.failed('plugin.video.tmdbmovies')
            xbmc.log('%s: TMDb Movies cloud status could not be saved.' % var.amgr, xbmc.LOGWARNING)

    #Youtube Theater RD
    #Despite the name, this is a Shadow-family debrid/streaming addon (Diamond
    #Build, same publisher as Diamond Media Player) - confirmed from its real
    #settings.xml and source, not from its label. Trakt client id/secret are
    #honoured from settings (Addon.getSetting('trakt_client_id') or a hardcoded
    #default), so no source patching or router.py block needed there.
        try:
                if xbmcvfs.exists(var.chk_youtubetheater):
                        chk_auth_ytheater = xbmcaddon.Addon('plugin.video.youtubetheater').getSetting("rd.auth")
                        if sync_support.needs('plugin.video.youtubetheater', [('rd.auth',your_rd_token),('rd.refresh',your_rd_refresh),('rd.client_id',your_rd_client_id),('rd.secret',your_rd_secret)]):
                                addon = xbmcaddon.Addon("plugin.video.youtubetheater")
                                addon.setSetting("rd.auth", your_rd_token)
                                addon.setSetting("rd.refresh", your_rd_refresh)
                                addon.setSetting("rd.client_id", your_rd_client_id)
                                addon.setSetting("rd.secret", your_rd_secret)
                                addon.setSetting("debrid_use_rd", ('true' if your_rd_token and not control.wiping() else 'false'))
        except:
                sync_support.failed('plugin.video.youtubetheater')
                xbmc.log('%s: Youtube Theater Real-Debrid Failed!' % var.amgr, xbmc.LOGINFO)
                pass

