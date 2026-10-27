from reauthorize.modules import sync_support
from reauthorize.modules import own_settings  # one read or write of our settings at a time
import xbmc, xbmcaddon, xbmcgui
import xbmcvfs
import os
from pathlib import Path
from libs.common import var
from reauthorize.modules.sync import trakt_select

char_remov = ["'", ",", ")","("]

#Account Manager Trakt

translatePath = xbmcvfs.translatePath
addon_id = xbmcaddon.Addon().getAddonInfo('id')
addon = xbmcaddon.Addon(addon_id)
addoninfo = addon.getAddonInfo
addon_data = translatePath(addon.getAddonInfo('profile'))


from reauthorize.modules import sync_support
xbmcaddon = sync_support.addon_api(xbmcaddon)
class Auth:
    def trakt_auth(self):
        accountmgr = own_settings.addon()
        your_token = accountmgr.getSetting("trakt.token")
        your_username = accountmgr.getSetting("trakt.username")
        your_refresh = accountmgr.getSetting("trakt.refresh")
        your_expires = accountmgr.getSetting("trakt.expires")
        #Whole seconds. ReAuthorize used to store this as '1791750555.0', and an add-on that reads
        #it with int() (POV's TraktMonitor) raised on the '.0' and reported "Error from Trakt".
        try: your_expires = str(int(float(your_expires)))
        except: sync_support.failed(); pass
        #Every installed add-on gets Trakt. This used to depend on the user picking
        #one primary add-on into trakt_sync_list.json, and a build wipe deleted that
        #file, leaving Trakt pushed nowhere. ReAuthorize now renews the token itself
        #(Trakt.refresh_if_due), so no add-on has to be the only one holding it.
        current = trakt_select.installed_addons()
        if current:
    #Seren
                try:
                    if 'Seren' in current: # Check if addon is included in sync list
                        if xbmcvfs.exists(var.chk_seren): #Check that the addon is installed and settings.xml exists.
                                    
                                #Get add-on setting to compare
                                chk_auth_seren = xbmcaddon.Addon('plugin.video.seren').getSetting("trakt.auth")
                                if True:  # Repair the complete Trakt bundle.
                            
                                        #Write data to settings.xml
                                        addon = xbmcaddon.Addon("plugin.video.seren")
                                        addon.setSetting("trakt.clientid", var.client_am)
                                        addon.setSetting("trakt.secret", var.secret_am)
                                        addon.setSetting("trakt.auth", your_token)
                                        addon.setSetting("trakt.username", your_username)
                                        addon.setSetting("trakt.refresh", your_refresh)
                                            
                                        your_expires_float = float(your_expires)
                                        your_expires_rnd = int(your_expires_float)
                                        your_expires_str = str(your_expires_rnd)
                                        addon.setSetting("trakt.expires", your_expires_str)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Seren Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
    #Coalition
                try:
                    if 'The Coalition' in current:
                        if xbmcvfs.exists(var.chk_coal):
                                chk_auth_coal = xbmcaddon.Addon('plugin.video.coalition').getSetting("trakt.token")
                                if True:  # Repair the complete Trakt bundle.
                                    
                                            with open(var.path_coal,'r') as f:
                                                data = f.read()

                                            client = data.replace(var.coal_client,var.client_am).replace(var.coal_secret,var.secret_am)

                                            with open(var.path_coal,'w') as f:
                                                f.write(client)

                                            addon = xbmcaddon.Addon("plugin.video.coalition")
                                            addon.setSetting("trakt.token", your_token)
                                            addon.setSetting("trakt_user", your_username)
                                            addon.setSetting("trakt.refresh", your_refresh)
                                            addon.setSetting("trakt.expires", your_expires)
                                            addon.setSetting("trakt.indicators_active", 'true')
                                            addon.setSetting("watched_indicators", '1')
                except:
                        sync_support.failed()
                        xbmc.log('%s: Coalition Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
            
    #POV
                try:
                    if 'POV' in current:
                        if xbmcvfs.exists(var.chk_pov):
                                chk_auth_pov = xbmcaddon.Addon('plugin.video.pov').getSetting("trakt.token")
                                #also when only the expiry differs: a POV still holding the old '...0' form is repaired
                                chk_expires_pov = xbmcaddon.Addon('plugin.video.pov').getSetting("trakt.expires")
                                if True:  # Repair the complete Trakt bundle.

                                        addon = xbmcaddon.Addon("plugin.video.pov")
                                        addon.setSetting("trakt.client_id", var.client_am)
                                        addon.setSetting("trakt.client_secret", var.secret_am)
                                        addon.setSetting("trakt.token", your_token)
                                        addon.setSetting("trakt_user", your_username)
                                        addon.setSetting("trakt.refresh", your_refresh)
                                        addon.setSetting("trakt.expires", your_expires)
                                        addon.setSetting("trakt_indicators_active", 'true')
                                        addon.setSetting("watched_indicators", '1')              
                except:
                        sync_support.failed()
                        xbmc.log('%s: POV Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
        
    #Umbrella
                try:
                    if 'Umbrella' in current:
                        if xbmcvfs.exists(var.chk_umb):
                                chk_auth_umb = xbmcaddon.Addon('plugin.video.umbrella').getSetting("trakt.user.token")
                                if True:  # Repair the complete Trakt bundle.

                                        addon = xbmcaddon.Addon("plugin.video.umbrella")
                                        addon.setSetting("trakt.user.name", your_username)
                                        addon.setSetting("trakt.user.token", your_token)
                                        addon.setSetting("trakt.refreshtoken", your_refresh)
                                        addon.setSetting("trakt.token.expires", your_expires)
                                        addon.setSetting("traktuserkey.customenabled", 'true')
                                        addon.setSetting("trakt.clientid", var.client_am)
                                        addon.setSetting("trakt.clientsecret", var.secret_am)
                                        addon.setSetting("trakt.authed.clientid", var.client_am)
                                        addon.setSetting("trakt.scrobble", 'true')
                                        addon.setSetting("resume.source", '1')  
                except:
                        sync_support.failed()
                        xbmc.log('%s: Umbrella Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Infinity
                try:
                    if 'Infinity' in current:
                        if xbmcvfs.exists(var.chk_infinity):
                                chk_auth_infinity = xbmcaddon.Addon('plugin.video.infinity').getSetting("trakt.user.token")
                                if True:  # Repair the complete Trakt bundle.

                                        addon = xbmcaddon.Addon("plugin.video.infinity")
                                        addon.setSetting("trakt.user.name", your_username)
                                        addon.setSetting("trakt.user.token", your_token)
                                        addon.setSetting("trakt.refreshtoken", your_refresh)
                                        addon.setSetting("trakt.token.expires", your_expires)
                                        addon.setSetting("traktuserkey.customenabled", 'true')
                                        addon.setSetting("trakt.clientid", var.client_am)
                                        addon.setSetting("trakt.clientsecret", var.secret_am)
                                        addon.setSetting("trakt.scrobble", 'true')
                                        addon.setSetting("resume.source", '1')  
                except:
                        sync_support.failed()
                        xbmc.log('%s: Infinity Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
            
    #Shadow
                try:
                    if 'Shadow' in current:
                        if xbmcvfs.exists(var.chk_shadow) and not xbmcvfs.exists(var.shadow_ud):
                                os.mkdir(var.shadow_ud)
                                xbmcvfs.copy(os.path.join(var.shadow), os.path.join(var.chkset_shadow))
                                    
                        if xbmcvfs.exists(var.chk_shadow) and not xbmcvfs.exists(var.chkset_shadow):
                                xbmcvfs.copy(os.path.join(var.shadow), os.path.join(var.chkset_shadow))

                        if xbmcvfs.exists(var.chk_shadow):
                                chk_auth_shadow = xbmcaddon.Addon('plugin.video.shadow').getSetting("trakt_access_token")
                                if True:  # Repair the complete Trakt bundle.
                                            
                                        with open(var.path_shadow,'r') as f:
                                            data = f.read()

                                        client = data.replace(var.shadow_client,var.client_am).replace(var.shadow_secret,var.secret_am)

                                        with open(var.path_shadow,'w') as f:
                                            f.write(client)

                                        addon = xbmcaddon.Addon("plugin.video.shadow")
                                        addon.setSetting("trakt_access_token", your_token)
                                        addon.setSetting("trakt_refresh_token", your_refresh)
                                        addon.setSetting("trakt_expires_at", your_expires)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Shadow Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
        
    #Ghost
                try:
                    if 'Ghost' in current:
                        if xbmcvfs.exists(var.chk_ghost) and not xbmcvfs.exists(var.ghost_ud):
                                os.mkdir(var.ghost_ud)
                                xbmcvfs.copy(os.path.join(var.ghost), os.path.join(var.chkset_ghost))
                                    
                        if xbmcvfs.exists(var.chk_ghost) and not xbmcvfs.exists(var.chkset_ghost):
                                xbmcvfs.copy(os.path.join(var.ghost), os.path.join(var.chkset_ghost))

                        if xbmcvfs.exists(var.chk_ghost):
                                chk_auth_ghost = xbmcaddon.Addon('plugin.video.ghost').getSetting("trakt_access_token")
                                if True:  # Repair the complete Trakt bundle.
                                            
                                        with open(var.path_ghost,'r') as f:
                                            data = f.read()

                                        client = data.replace(var.ghost_client,var.client_am).replace(var.ghost_secret,var.secret_am)

                                        with open(var.path_ghost,'w') as f:
                                            f.write(client)

                                        addon = xbmcaddon.Addon("plugin.video.ghost")
                                        addon.setSetting("trakt_access_token", your_token)
                                        addon.setSetting("trakt_refresh_token", your_refresh)
                                        addon.setSetting("trakt_expires_at", your_expires)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Ghost Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Blue Balls
                try:
                    if 'Blue Balls' in current:
                        if xbmcvfs.exists(var.chk_blueballs) and not xbmcvfs.exists(var.blueballs_ud):
                                os.mkdir(var.blueballs_ud)
                                xbmcvfs.copy(os.path.join(var.blueballs), os.path.join(var.chkset_blueballs))

                        if xbmcvfs.exists(var.chk_blueballs) and not xbmcvfs.exists(var.chkset_blueballs):
                                xbmcvfs.copy(os.path.join(var.blueballs), os.path.join(var.chkset_blueballs))

                        if xbmcvfs.exists(var.chk_blueballs):
                                chk_auth_blueballs = xbmcaddon.Addon('plugin.video.blueballs').getSetting("trakt_access_token")
                                if True:  # Repair the complete Trakt bundle.

                                        with open(var.path_blueballs,'r') as f:
                                            data = f.read()

                                        client = data.replace(var.blueballs_client,var.client_am).replace(var.blueballs_secret,var.secret_am)

                                        with open(var.path_blueballs,'w') as f:
                                            f.write(client)

                                        addon = xbmcaddon.Addon("plugin.video.blueballs")
                                        addon.setSetting("trakt_access_token", your_token)
                                        addon.setSetting("trakt_refresh_token", your_refresh)
                                        addon.setSetting("trakt_expires_at", your_expires)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Blue Balls Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Twisted
                try:
                    if 'Twisted' in current:
                        if xbmcvfs.exists(var.chk_twisted) and not xbmcvfs.exists(var.twisted_ud):
                                os.mkdir(var.twisted_ud)
                                xbmcvfs.copy(os.path.join(var.twisted), os.path.join(var.chkset_twisted))

                        if xbmcvfs.exists(var.chk_twisted) and not xbmcvfs.exists(var.chkset_twisted):
                                xbmcvfs.copy(os.path.join(var.twisted), os.path.join(var.chkset_twisted))

                        if xbmcvfs.exists(var.chk_twisted):
                                chk_auth_twisted = xbmcaddon.Addon('plugin.video.twisted').getSetting("trakt_access_token")
                                if True:  # Repair the complete Trakt bundle.

                                        with open(var.path_twisted,'r') as f:
                                            data = f.read()

                                        client = data.replace(var.twisted_client,var.client_am).replace(var.twisted_secret,var.secret_am)

                                        with open(var.path_twisted,'w') as f:
                                            f.write(client)

                                        addon = xbmcaddon.Addon("plugin.video.twisted")
                                        addon.setSetting("trakt_access_token", your_token)
                                        addon.setSetting("trakt_refresh_token", your_refresh)
                                        addon.setSetting("trakt_expires_at", your_expires)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Twisted Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Base
                try:
                    if 'Base' in current:
                        if xbmcvfs.exists(var.chk_base) and not xbmcvfs.exists(var.base_ud):
                                os.mkdir(var.base_ud)
                                xbmcvfs.copy(os.path.join(var.base), os.path.join(var.chkset_base))
                                    
                        if xbmcvfs.exists(var.chk_base) and not xbmcvfs.exists(var.chkset_base):
                                xbmcvfs.copy(os.path.join(var.base), os.path.join(var.chkset_base))

                        if xbmcvfs.exists(var.chk_base):
                                chk_auth_base = xbmcaddon.Addon('plugin.video.base').getSetting("trakt_access_token")
                                if True:  # Repair the complete Trakt bundle.
                                            
                                        with open(var.path_base,'r') as f:
                                            data = f.read()

                                        client = data.replace(var.base_client,var.client_am).replace(var.base_secret,var.secret_am)

                                        with open(var.path_base,'w') as f:
                                            f.write(client)

                                        addon = xbmcaddon.Addon("plugin.video.base")
                                        addon.setSetting("trakt_access_token", your_token)
                                        addon.setSetting("trakt_refresh_token", your_refresh)
                                        addon.setSetting("trakt_expires_at", your_expires)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Base Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
        
    #Chain Reaction
                try:
                    if 'Chain Reaction' in current:
                        if xbmcvfs.exists(var.chk_chains) and not xbmcvfs.exists(var.chains_ud):
                                os.mkdir(var.chains_ud)
                                xbmcvfs.copy(os.path.join(var.chains), os.path.join(var.chkset_chains))
                                    
                        if xbmcvfs.exists(var.chk_chains) and not xbmcvfs.exists(var.chkset_chains):
                                xbmcvfs.copy(os.path.join(var.chains), os.path.join(var.chkset_chains))

                        if xbmcvfs.exists(var.chk_chains):
                                chk_auth_chains = xbmcaddon.Addon('plugin.video.thechains').getSetting("trakt_access_token")
                                if True:  # Repair the complete Trakt bundle.
                                            
                                        with open(var.path_chains,'r') as f:
                                            data = f.read()

                                        client = data.replace(var.chains_client,var.client_am).replace(var.chains_secret,var.secret_am)

                                        with open(var.path_chains,'w') as f:
                                            f.write(client)

                                        addon = xbmcaddon.Addon("plugin.video.thechains")
                                        addon.setSetting("trakt_access_token", your_token)
                                        addon.setSetting("trakt_refresh_token", your_refresh)
                                        addon.setSetting("trakt_expires_at", your_expires)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Chain Reaction Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
        
    #Patriot
                try:
                    if 'Patriot' in current:
                        if xbmcvfs.exists(var.chk_patriot) and not xbmcvfs.exists(var.patriot_ud):
                                os.mkdir(var.patriot_ud)
                                xbmcvfs.copy(os.path.join(var.patriot), os.path.join(var.chkset_patriot))
                                    
                        if xbmcvfs.exists(var.chk_patriot) and not xbmcvfs.exists(var.chkset_patriot):
                                xbmcvfs.copy(os.path.join(var.patriot), os.path.join(var.chkset_patriot))

                        if xbmcvfs.exists(var.chk_patriot):
                                chk_auth_patriot = xbmcaddon.Addon('plugin.video.patriot').getSetting("trakt_access_token")
                                if True:  # Repair the complete Trakt bundle.
                                            
                                        with open(var.path_patriot,'r') as f:
                                            data = f.read()

                                        client = data.replace(var.patriot_client,var.client_am).replace(var.patriot_secret,var.secret_am)

                                        with open(var.path_patriot,'w') as f:
                                            f.write(client)

                                        addon = xbmcaddon.Addon("plugin.video.patriot")
                                        addon.setSetting("trakt_access_token", your_token)
                                        addon.setSetting("trakt_refresh_token", your_refresh)
                                        addon.setSetting("trakt_expires_at", your_expires)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Patriot Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Black Lightning
                try:
                    if 'Black Lightning' in current:
                        if xbmcvfs.exists(var.chk_blackl) and not xbmcvfs.exists(var.blackl_ud):
                                os.mkdir(var.blackl_ud)
                                xbmcvfs.copy(os.path.join(var.blackl), os.path.join(var.chkset_blackl))
                                    
                        if xbmcvfs.exists(var.chk_blackl) and not xbmcvfs.exists(var.chkset_blackl):
                                xbmcvfs.copy(os.path.join(var.blackl), os.path.join(var.chkset_blackl))

                        if xbmcvfs.exists(var.chk_blackl):
                                chk_auth_blackl = xbmcaddon.Addon('plugin.video.blacklightning').getSetting("trakt_access_token")
                                if True:  # Repair the complete Trakt bundle.
                                            
                                        with open(var.path_blackl,'r') as f:
                                            data = f.read()

                                        client = data.replace(var.blackl_client,var.client_am).replace(var.blackl_secret,var.secret_am)

                                        with open(var.path_blackl,'w') as f:
                                            f.write(client)

                                        addon = xbmcaddon.Addon("plugin.video.blacklightning")
                                        addon.setSetting("trakt_access_token", your_token)
                                        addon.setSetting("trakt_refresh_token", your_refresh)
                                        addon.setSetting("trakt_expires_at", your_expires)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Black Lightning Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
            
    #Homelander
                try:
                    if 'Homelander' in current:
                        if xbmcvfs.exists(var.chk_home) and not xbmcvfs.exists(var.home_ud):
                                os.mkdir(var.home_ud)
                                xbmcvfs.copy(os.path.join(var.home), os.path.join(var.chkset_home))
                                    
                        if xbmcvfs.exists(var.chk_home) and not xbmcvfs.exists(var.chkset_home):
                                xbmcvfs.copy(os.path.join(var.home), os.path.join(var.chkset_home))

                        if xbmcvfs.exists(var.chk_home):
                                chk_auth_home = xbmcaddon.Addon('plugin.video.homelander').getSetting("trakt.token")
                                if True:  # Repair the complete Trakt bundle.

                                        addon = xbmcaddon.Addon("plugin.video.homelander")
                                        addon.setSetting("trakt.user", your_username)
                                        addon.setSetting("trakt.token", your_token)
                                        addon.setSetting("trakt.refresh", your_refresh)
                                        addon.setSetting("trakt.authed", 'yes')
                                        addon.setSetting("trakt.client_id", var.client_am)
                                        addon.setSetting("trakt.client_secret", var.secret_am)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Homelander Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
        
    #Quicksilver
                try:
                    if 'Quicksilver' in current:
                        if xbmcvfs.exists(var.chk_quick) and not xbmcvfs.exists(var.quick_ud):
                                os.mkdir(var.quick_ud)
                                xbmcvfs.copy(os.path.join(var.quick), os.path.join(var.chkset_quick))
                                    
                        if xbmcvfs.exists(var.chk_quick) and not xbmcvfs.exists(var.chkset_quick):
                                xbmcvfs.copy(os.path.join(var.quick), os.path.join(var.chkset_quick))

                        if xbmcvfs.exists(var.chk_quick):
                                chk_auth_quick = xbmcaddon.Addon('plugin.video.quicksilver').getSetting("trakt.token")
                                if True:  # Repair the complete Trakt bundle.

                                        addon = xbmcaddon.Addon("plugin.video.quicksilver")
                                        addon.setSetting("trakt.user", your_username)
                                        addon.setSetting("trakt.token", your_token)
                                        addon.setSetting("trakt.refresh", your_refresh)
                                        addon.setSetting("trakt.authed", 'yes')
                                        addon.setSetting("trakt.client_id", var.client_am)
                                        addon.setSetting("trakt.client_secret", var.secret_am)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Quicksilver Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Chains Genocide
                try:
                    if 'Chains Genocide' in current:
                        if xbmcvfs.exists(var.chk_genocide) and not xbmcvfs.exists(var.genocide_ud):
                                os.mkdir(var.genocide_ud)
                                xbmcvfs.copy(os.path.join(var.genocide), os.path.join(var.chkset_genocide))
                                
                        if xbmcvfs.exists(var.chk_genocide) and not xbmcvfs.exists(var.chkset_genocide):
                                xbmcvfs.copy(os.path.join(var.genocide), os.path.join(var.chkset_genocide))

                        if xbmcvfs.exists(var.chk_genocide):
                                chk_auth_genocide = xbmcaddon.Addon('plugin.video.chainsgenocide').getSetting("trakt.token")
                                if True:  # Repair the complete Trakt bundle.

                                        with open(var.path_genocide,'r') as f:
                                            data = f.read()

                                        client = data.replace(var.genocide_client,var.client_am).replace(var.genocide_secret,var.secret_am)

                                        with open(var.path_genocide,'w') as f:
                                            f.write(client)
                                            
                                        addon = xbmcaddon.Addon("plugin.video.chainsgenocide")
                                        addon.setSetting("trakt.username", your_username)
                                        addon.setSetting("trakt.token", your_token)
                                        addon.setSetting("trakt.refresh", your_refresh)
                                        addon.setSetting("trakt.isauthed", 'true')
                except:
                        sync_support.failed()
                        xbmc.log('%s: Chains Genocide Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
            
    #Absolution
                try:
                        if 'Absolution' in current:
                            if xbmcvfs.exists(var.chk_absol) and not xbmcvfs.exists(var.absol_ud):
                                    os.mkdir(var.absol_ud)
                                    xbmcvfs.copy(os.path.join(var.absol), os.path.join(var.chkset_absol))
                                    
                            if xbmcvfs.exists(var.chk_absol) and not xbmcvfs.exists(var.chkset_absol):
                                    xbmcvfs.copy(os.path.join(var.absol), os.path.join(var.chkset_absol))

                            if xbmcvfs.exists(var.chk_absol):
                                    chk_auth_absol = xbmcaddon.Addon('plugin.video.absolution').getSetting("trakt.token")
                                    if True:  # Repair the complete Trakt bundle.

                                            addon = xbmcaddon.Addon("plugin.video.absolution")
                                            addon.setSetting("trakt.user", your_username)
                                            addon.setSetting("trakt.token", your_token)
                                            addon.setSetting("trakt.refresh", your_refresh)
                                            addon.setSetting("trakt.authed", 'yes')
                                            addon.setSetting("trakt.client_id", var.client_am)
                                            addon.setSetting("trakt.client_secret", var.secret_am)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Absolution Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Shazam
                try:
                        if 'Shazam' in current:
                            if xbmcvfs.exists(var.chk_shazam) and not xbmcvfs.exists(var.shazam_ud):
                                    os.mkdir(var.shazam_ud)
                                    xbmcvfs.copy(os.path.join(var.shazam), os.path.join(var.chkset_shazam))
                                    
                            if xbmcvfs.exists(var.chk_shazam) and not xbmcvfs.exists(var.chkset_shazam):
                                    xbmcvfs.copy(os.path.join(var.shazam), os.path.join(var.chkset_shazam))

                            if xbmcvfs.exists(var.chk_shazam):
                                    chk_auth_shazam = xbmcaddon.Addon('plugin.video.shazam').getSetting("trakt.token")
                                    if True:  # Repair the complete Trakt bundle.

                                            addon = xbmcaddon.Addon("plugin.video.shazam")
                                            addon.setSetting("trakt.user", your_username)
                                            addon.setSetting("trakt.token", your_token)
                                            addon.setSetting("trakt.refresh", your_refresh)
                                            addon.setSetting("trakt.authed", 'yes')
                                            addon.setSetting("trakt.client_id", var.client_am)
                                            addon.setSetting("trakt.client_secret", var.secret_am)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Shazam Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
            
    #The Crew
                try:
                        if 'The Crew' in current:
                            if xbmcvfs.exists(var.chk_crew) and not xbmcvfs.exists(var.crew_ud):
                                    os.mkdir(var.crew_ud)
                                    xbmcvfs.copy(os.path.join(var.crew), os.path.join(var.chkset_crew))
                                    
                            if xbmcvfs.exists(var.chk_crew) and not xbmcvfs.exists(var.chkset_crew):
                                    xbmcvfs.copy(os.path.join(var.crew), os.path.join(var.chkset_crew))
                                    
                            if xbmcvfs.exists(var.chk_crew):
                                    # Crew 3.x keeps its key in keys.py, deletes a sign-in while trakt.revoked is
                                    # true, and wants trakt.expires_at: see sync/crew_trakt.py (1.3.8).
                                    from reauthorize.modules.sync import crew_trakt
                                    crew_trakt.link(your_username, your_token, your_refresh, your_expires)
                except:
                        sync_support.failed()
                        xbmc.log('%s: The Crew Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
        
    #Nightwing (plugin.video.nightwing, 1.4.0): Moria's code base, same settings and signed-in rule
                try:
                        if 'Nightwing' in current:

                            if xbmcvfs.exists(var.chk_nightwing):
                                    chk_auth_nightwing = xbmcaddon.Addon('plugin.video.nightwing').getSetting("trakt.token")
                                    if True:  # Repair the complete Trakt bundle.

                                            addon = xbmcaddon.Addon("plugin.video.nightwing")
                                            addon.setSetting("trakt.user", your_username)
                                            addon.setSetting("trakt.token", your_token)
                                            addon.setSetting("trakt.refresh", your_refresh)
                                            addon.setSetting("trakt.authed", 'yes')
                                            addon.setSetting("trakt.client_id", var.client_am)
                                            addon.setSetting("trakt.client_secret", var.secret_am)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Nightwing Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Scrubs V2
                try:
                        if 'Scrubs V2' in current:
                            if xbmcvfs.exists(var.chk_scrubs) and not xbmcvfs.exists(var.scrubs_ud):
                                    os.mkdir(var.scrubs_ud)
                                    xbmcvfs.copy(os.path.join(var.scrubs), os.path.join(var.chkset_scrubs))
                                    
                            if xbmcvfs.exists(var.chk_scrubs) and not xbmcvfs.exists(var.chkset_scrubs):
                                    xbmcvfs.copy(os.path.join(var.scrubs), os.path.join(var.chkset_scrubs))

                            if xbmcvfs.exists(var.chk_scrubs):
                                    chk_auth_scrubs = xbmcaddon.Addon('plugin.video.scrubsv2').getSetting("trakt.token")
                                    if True:  # Repair the complete Trakt bundle.

                                            with open(var.path_scrubs,'r') as f:
                                                data = f.read()

                                            client = data.replace(var.scrubs_client,var.client_am).replace(var.scrubs_secret,var.secret_am)

                                            with open(var.path_scrubs,'w') as f:
                                                f.write(client)

                                            addon = xbmcaddon.Addon("plugin.video.scrubsv2")
                                            addon.setSetting("trakt.user", your_username)
                                            addon.setSetting("trakt.token", your_token)
                                            addon.setSetting("trakt.refresh", your_refresh)
                                            addon.setSetting("trakt.authed", 'yes')
                except:
                        sync_support.failed()
                        xbmc.log('%s: Scrubs V2 Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #TMDB Helper
                try:
                        if 'TMDb Helper' in current:
                            if xbmcvfs.exists(var.chk_tmdbh) and not xbmcvfs.exists(var.tmdbh_ud):
                                    os.mkdir(var.tmdbh_ud)
                                    xbmcvfs.copy(os.path.join(var.tmdbh), os.path.join(var.chkset_tmdbh))
                                    
                            if xbmcvfs.exists(var.chk_tmdbh) and not xbmcvfs.exists(var.chkset_tmdbh):
                                    xbmcvfs.copy(os.path.join(var.tmdbh), os.path.join(var.chkset_tmdbh))

                            if xbmcvfs.exists(var.chk_tmdbh):

                                    chk_auth_tmdbh = xbmcaddon.Addon('plugin.video.themoviedb.helper').getSetting("trakt_token")
                                    
                                    if False:  # Repair all token metadata, including expiry, on resync.
                                        pass
                                            
                                    else:                           
                                        with open(var.path_tmdbh,'r') as f:
                                            data = f.read()

                                        client = data.replace(var.tmdbh_client,var.client_am).replace(var.tmdbh_secret,var.secret_am)

                                        with open(var.path_tmdbh,'w') as f:
                                            f.write(client)
                                                
                                        addon = xbmcaddon.Addon("plugin.video.themoviedb.helper")
                                        your_expires_float = float(your_expires)
                                        your_expires_rnd = int(your_expires_float)
                                        import json
                                        lifetime = int(float(accountmgr.getSetting('trakt.lifetime') or 604800))
                                        tmdbh_data = json.dumps({'access_token': your_token, 'refresh_token': your_refresh,
                                            'token_type': 'bearer', 'expires_in': lifetime,
                                            'created_at': your_expires_rnd - lifetime, 'scope': 'public'})
                                        addon.setSettingString("trakt_token", tmdbh_data)
                                        addon.setSetting("startup_notifications", 'false')
                except:
                        sync_support.failed()
                        xbmc.log('%s: TMDBh Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Trakt Addon
                try:
                        if 'Trakt Addon' in current:
                            if xbmcvfs.exists(var.chk_trakt) and not xbmcvfs.exists(var.trakt_ud):
                                    os.mkdir(var.trakt_ud)
                                    xbmcvfs.copy(os.path.join(var.trakt), os.path.join(var.chkset_trakt))
                                    
                            if xbmcvfs.exists(var.chk_trakt) and not xbmcvfs.exists(var.chkset_trakt):
                                    xbmcvfs.copy(os.path.join(var.trakt), os.path.join(var.chkset_trakt))
                            
                            if xbmcvfs.exists(var.chk_trakt):
                                    
                                    chk_auth_trakt = xbmcaddon.Addon('script.trakt').getSetting("trakt_token")
                                    
                                    if str(your_token) in str(chk_auth_trakt):
                                        pass
                                            
                                    else:
                                        # 3.9.0 keeps its key as a list of numbers: swap the lines (traktaddon_key.py)
                                        from reauthorize.modules.sync import traktaddon_key
                                        with open(var.path_trakt,'r') as f:
                                            data = f.read()

                                        client = traktaddon_key.swap_key(data, var.client_am, var.secret_am)

                                        with open(var.path_trakt,'w') as f:
                                            f.write(client)
                                        
                                        addon = xbmcaddon.Addon("script.trakt")
                                        addon.setSetting("user", your_username)
                                        your_expires_float = float(your_expires)
                                        your_expires_rnd = int(your_expires_float)
                                        token = '{"access_token": "'
                                        refresh = f'","token_type": "bearer", "expires_in": 7776000, "refresh_token": "'
                                        expires = f'", "scope": "public", "created_at": '
                                        trakt_data = '%s%s%s%s%s%s}' %(token, your_token, refresh, your_refresh, expires, your_expires_rnd)
                                        addon.setSetting("authorization", trakt_data)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Trakt Addon Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #All Accounts
                try:
                        if 'All Accounts' in current:
                            if xbmcvfs.exists(var.chk_allaccounts) and not xbmcvfs.exists(var.allaccounts_ud):
                                    os.mkdir(var.allaccounts_ud)
                                    xbmcvfs.copy(os.path.join(var.allaccounts), os.path.join(var.chkset_allaccounts))
                                    
                            if xbmcvfs.exists(var.chk_allaccounts) and not xbmcvfs.exists(var.chkset_allaccounts):
                                    xbmcvfs.copy(os.path.join(var.allaccounts), os.path.join(var.chkset_allaccounts))
                                    
                            if xbmcvfs.exists(var.chk_allaccounts):
                                    chk_auth_allaccounts = xbmcaddon.Addon('script.module.allaccounts').getSetting("trakt.token")
                                    if True:  # Repair the complete Trakt bundle.

                                            with open(var.path_allaccounts,'r') as f:
                                                data = f.read()

                                            client = data.replace(var.allacts_client,var.client_am).replace(var.allacts_secret,var.secret_am)

                                            with open(var.path_allaccounts,'w') as f:
                                                f.write(client)

                                            addon = xbmcaddon.Addon("script.module.allaccounts")
                                            addon.setSetting("trakt.token", your_token)
                                            addon.setSetting("trakt.username", your_username)
                                            addon.setSetting("trakt.refresh", your_refresh)
                                            addon.setSetting("trakt.expires", your_expires)
                except:
                        sync_support.failed()
                        xbmc.log('%s: All Accounts Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass
            
    #My Accounts
                try:
                        if 'My Accounts' in current:
                            if xbmcvfs.exists(var.chk_myaccounts) and not xbmcvfs.exists(var.myaccounts_ud):
                                    os.mkdir(var.myaccounts_ud)
                                    xbmcvfs.copy(os.path.join(var.myaccounts), os.path.join(var.chkset_myaccounts))
                                    
                            if xbmcvfs.exists(var.chk_myaccounts) and not xbmcvfs.exists(var.chkset_myaccounts):
                                    xbmcvfs.copy(os.path.join(var.myaccounts), os.path.join(var.chkset_myaccounts))
                                    
                            if xbmcvfs.exists(var.chk_myaccounts):
                                    chk_auth_myaccounts = xbmcaddon.Addon('script.module.myaccounts').getSetting("trakt.token")
                                    if True:  # Repair the complete Trakt bundle.

                                            with open(var.path_myaccounts,'r') as f:
                                                data = f.read()

                                            client = data.replace(var.myacts_client,var.client_am).replace(var.myacts_secret,var.secret_am)

                                            with open(var.path_myaccounts,'w') as f:
                                                f.write(client)

                                            addon = xbmcaddon.Addon("script.module.myaccounts")
                                            addon.setSetting("trakt.token", your_token)
                                            addon.setSetting("trakt.username", your_username)
                                            addon.setSetting("trakt.refresh", your_refresh)
                                            addon.setSetting("trakt.expires", your_expires)
                except:
                        sync_support.failed()
                        xbmc.log('%s: My Accounts Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Mad Titan Sports (plugin.video.madtitansports, 1.4.0). Takes the Trakt key from its settings (its own
    #code has none) and counts as signed in when trakt.user_id is set. It puts that id in its URLs
    #(/users/<id>/...), and ReAuthorize's username can hold spaces, so it gets 'me', Trakt's name for the
    #signed-in user (checked live 2026-10-09: watchlist, collection, lists, watched all 200). It never renews
    #by itself; ReAuthorize re-sends after every renewal. trakt_wipe blanks trakt.user_id with the token.
                try:
                        if 'Mad Titan Sports' in current:
                            if xbmcvfs.exists(var.chk_madtitan):
                                    chk_auth_madtitan = xbmcaddon.Addon('plugin.video.madtitansports').getSetting("trakt.access_token")
                                    if True:  # Repair the complete Trakt bundle.
                                            addon = xbmcaddon.Addon("plugin.video.madtitansports")
                                            addon.setSetting("trakt.client_id", var.client_am)
                                            addon.setSetting("trakt.client_secret", var.secret_am)
                                            addon.setSetting("trakt.access_token", your_token)
                                            addon.setSetting("trakt.refresh_token", your_refresh)
                                            addon.setSetting("trakt.user_id", 'me' if your_token else '')
                except:
                        sync_support.failed()
                        xbmc.log('%s: Mad Titan Sports Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Gears
                try:
                        if 'Gears' in current:
                            if xbmcvfs.exists(var.chk_gears_video) and xbmcvfs.exists(var.chkset_gears):

                                from reauthorize.modules.db import trakt_db
                                conn = trakt_db.create_conn(var.gears_settings_db)

                                with conn:
                                    cursor = conn.cursor()
                                    cursor.execute('''SELECT setting_value FROM settings WHERE setting_id = ?''', ('trakt.token',))
                                    auth_trakt = cursor.fetchone()
                                    chk_auth_gears = str(auth_trakt)
                                    cursor.close()

                                    for char in char_remov:
                                        chk_auth_gears = chk_auth_gears.replace(char, "")

                                    if True:  # Repair the complete Trakt bundle.

                                        from reauthorize.modules.db import trakt_db
                                        trakt_db.auth_gears_trakt()
                                        xbmcvfs.delete(var.gears_trakt_db)
                                        var.remake_settings()
                except:
                        sync_support.failed()
                        xbmc.log('%s: Gears Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Genocide (plugin.video.genocide)
                try:
                        if 'Genocide' in current:
                            if xbmcvfs.exists(var.chk_newgenocide):
                                    # Its Trakt key is hard-coded in resources/lib/indexers/trakt.py and the trakt.client_id
                                    # settings below are never read, so without this swap it sent our token under its own
                                    # key: 401 on every call, invalid_grant on every refresh, and a prompt to authorize.
                                    # Optional, like TMDb Movies: a missing or moved file must not stop the settings write.
                                    try:
                                        with open(var.path_newgenocide, 'r') as f:
                                            data = f.read()
                                        if var.chk_api not in data:
                                            with open(var.path_newgenocide, 'w') as f:
                                                f.write(data.replace(var.genocide_client, var.client_am).replace(var.genocide_secret, var.secret_am))
                                    except Exception:
                                        sync_support.failed()
                                        xbmc.log('%s: Genocide Trakt key file not patched' % var.amgr, xbmc.LOGINFO)
                                    chk_auth_newgenocide = xbmcaddon.Addon('plugin.video.genocide').getSetting("trakt.token")
                                    if True:  # Repair the complete Trakt bundle.
                                            addon = xbmcaddon.Addon("plugin.video.genocide")
                                            addon.setSetting("trakt.token", your_token)
                                            addon.setSetting("trakt.username", your_username)
                                            addon.setSetting("trakt.refresh", your_refresh)
                                            addon.setSetting("trakt.expires", your_expires)
                                            addon.setSetting("trakt.isauthed", 'true')
                                            addon.setSetting("trakt.client_id", var.client_am)
                                            addon.setSetting("trakt.client_secret", var.secret_am)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Genocide Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Aliunde K19
                try:
                        if 'Aliunde K19' in current:
                            if xbmcvfs.exists(var.chk_aliunde) and not xbmcvfs.exists(var.aliunde_ud):
                                    os.mkdir(var.aliunde_ud)
                                    xbmcvfs.copy(os.path.join(var.aliunde), os.path.join(var.chkset_aliunde))

                            if xbmcvfs.exists(var.chk_aliunde) and not xbmcvfs.exists(var.chkset_aliunde):
                                    xbmcvfs.copy(os.path.join(var.aliunde), os.path.join(var.chkset_aliunde))

                            if xbmcvfs.exists(var.chk_aliunde):
                                    chk_auth_aliunde = xbmcaddon.Addon('plugin.video.aliundek19').getSetting("trakt_access_token")
                                    if True:  # Repair the complete Trakt bundle.

                                            with open(var.path_aliunde,'r') as f:
                                                data = f.read()

                                            client = data.replace(var.aliunde_client,var.client_am).replace(var.aliunde_secret,var.secret_am)

                                            with open(var.path_aliunde,'w') as f:
                                                f.write(client)

                                            addon = xbmcaddon.Addon("plugin.video.aliundek19")
                                            addon.setSetting("trakt_access_token", your_token)
                                            addon.setSetting("trakt_refresh_token", your_refresh)
                                            addon.setSetting("trakt_expires_at", your_expires)
                                            addon.setSetting("trakt_client_id", var.client_am)
                                            addon.setSetting("trakt_client_secret", var.secret_am)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Aliunde K19 Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #GratisRed
                try:
                        if 'GratisRed' in current:
                            if xbmcvfs.exists(var.chk_gratisred):
                                    chk_auth_gratisred = xbmcaddon.Addon('plugin.video.gratisred').getSetting("trakt.token")
                                    if True:  # Repair the complete Trakt bundle.

                                            #Insert Account Manager API keys, so GratisRed presents to
                                            #Trakt as the same Community App as every other addon
                                            with open(var.path_gratisred,'r') as f:
                                                data = f.read()

                                            client = data.replace(var.gratisred_client,var.client_am).replace(var.gratisred_secret,var.secret_am)

                                            with open(var.path_gratisred,'w') as f:
                                                f.write(client)

                                            addon = xbmcaddon.Addon("plugin.video.gratisred")
                                            #GratisRed treats itself as signed out unless user, token
                                            #and refresh are ALL set (getTraktCredentialsInfo), so
                                            #without trakt.user the token was always ignored.
                                            addon.setSetting("trakt.user", your_username)
                                            addon.setSetting("trakt.token", your_token)
                                            addon.setSetting("trakt.refresh", your_refresh)
                                            #'yes' is what GratisRed's own sign-in writes.
                                            addon.setSetting("trakt.authed", 'yes')
                                            #GratisRed 2.0.4 reads its Trakt app key from these two
                                            #settings BEFORE the lines in its file, at every call
                                            #(_trakt_app_keys). An update of GratisRed puts its own
                                            #lines back, and until they were swapped again (and Kodi
                                            #restarted) it called Trakt under its own key with our
                                            #sign-in, was refused, and showed an error (1.4.2).
                                            if "trakt.client_id" in data:
                                                addon.setSetting("trakt.client_id", var.client_am)
                                                addon.setSetting("trakt.client_secret", var.secret_am)
                                            #No trakt.expires on purpose: GratisRed only refreshes
                                            #when it has one, and every addon that refreshes on its
                                            #own spends the refresh token the others share.
                except:
                        sync_support.failed()
                        xbmc.log('%s: GratisRed Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Orion
                try:
                        if 'Orion' in current:
                            if xbmcvfs.exists(var.chk_orion):
                                    chk_auth_orion = xbmcaddon.Addon('plugin.video.orion').getSetting("trakt_token")
                                    if True:  # Repair the complete Trakt bundle.
                                            addon = xbmcaddon.Addon("plugin.video.orion")
                                            addon.setSetting("trakt_token", your_token)
                                            addon.setSetting("trakt_refresh", your_refresh)
                                            addon.setSetting("trakt_enabled", 'true')
                except:
                        sync_support.failed()
                        xbmc.log('%s: Orion Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Red Light
    #trakt.user is what Red Light checks to count itself signed in. trakt.expires
    #is required, unlike GratisRed: Red Light refreshes whenever now > expires, and
    #its default is '0', so leaving it out would spend the shared refresh token on
    #the very first call. trakt.client/secret are honoured from settings, so no
    #source patching.
                try:
                        if 'Red Light' in current:
                            from reauthorize.modules.db import redlight_db
                            redlight_db.push([('trakt.token', your_token),
                                              ('trakt.refresh', your_refresh),
                                              ('trakt.expires', your_expires),
                                              ('trakt.user', your_username),
                                              ('trakt.client', var.client_am),
                                              ('trakt.secret', var.secret_am)])
                except:
                        sync_support.failed()
                        xbmc.log('%s: Red Light Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Cosmos
                try:
                        if 'Cosmos' in current:
                            if xbmcvfs.exists(var.chk_cosmos):
                                    chk_auth_cosmos = xbmcaddon.Addon('plugin.video.cosmos').getSetting("trakt_access_token")
                                    if True:  # Repair the complete Trakt bundle.
                                            addon = xbmcaddon.Addon("plugin.video.cosmos")
                                            addon.setSetting("trakt_access_token", your_token)
                                            addon.setSetting("trakt_refresh_token", your_refresh)
                                            addon.setSetting("trakt_expires_in", '')
                                            addon.setSetting("trakt_created_at", '')
                                            addon.setSetting("trakt_username", your_username)
                                            addon.setSetting("trakt_client_id", var.client_am)
                                            addon.setSetting("trakt_client_secret", var.secret_am)
                                            addon.setSetting("trakt_auth_done", 'true')
                except:
                        sync_support.failed()
                        xbmc.log('%s: Cosmos Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #The Archives
                try:
                        if 'The Archives' in current:
                            if xbmcvfs.exists(var.chk_thearchives):
                                    chk_auth_thearchives = xbmcaddon.Addon('plugin.video.thearchives').getSetting("trakt.access_token")
                                    if True:  # Repair the complete Trakt bundle.
                                            addon = xbmcaddon.Addon("plugin.video.thearchives")
                                            addon.setSetting("trakt.access_token", your_token)
                                            addon.setSetting("trakt.refresh_token", your_refresh)
                                            addon.setSetting("trakt.expires", your_expires)
                                            addon.setSetting("trakt.user_id", your_username)
                except:
                        sync_support.failed()
                        xbmc.log('%s: The Archives Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #FidoK19
                try:
                        if 'FidoK19' in current:
                            if xbmcvfs.exists(var.chk_fidok19):
                                    chk_auth_fidok19 = xbmcaddon.Addon('plugin.video.fidoK19').getSetting("trakt.access_token")
                                    if True:  # Repair the complete Trakt bundle.
                                            addon = xbmcaddon.Addon("plugin.video.fidoK19")
                                            addon.setSetting("trakt.access_token", your_token)
                                            addon.setSetting("trakt.refresh_token", your_refresh)
                                            addon.setSetting("trakt.user_id", your_username)
                                            addon.setSetting("trakt.client_id", var.client_am)
                                            addon.setSetting("trakt.client_secret", var.secret_am)
                except:
                        sync_support.failed()
                        xbmc.log('%s: FidoK19 Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #TorqueLite
                try:
                        if 'TorqueLite' in current:
                            if xbmcvfs.exists(var.chk_torquelite):
                                    chk_auth_torquelite = xbmcaddon.Addon('plugin.video.torquelite').getSetting("trakt.access_token")
                                    if True:  # Repair the complete Trakt bundle.
                                            addon = xbmcaddon.Addon("plugin.video.torquelite")
                                            addon.setSetting("trakt.access_token", your_token)
                                            addon.setSetting("trakt.refresh_token", your_refresh)
                                            addon.setSetting("trakt.user_id", your_username)
                                            addon.setSetting("trakt.client_id", var.client_am)
                                            addon.setSetting("trakt.client_secret", var.secret_am)
                except:
                        sync_support.failed()
                        xbmc.log('%s: TorqueLite Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #TorqueLive
                try:
                        if 'TorqueLive' in current:
                            if xbmcvfs.exists(var.chk_torquelive):
                                    chk_auth_torquelive = xbmcaddon.Addon('plugin.video.torquelive').getSetting("trakt.access_token")
                                    if True:  # Repair the complete Trakt bundle.
                                            addon = xbmcaddon.Addon("plugin.video.torquelive")
                                            addon.setSetting("trakt.access_token", your_token)
                                            addon.setSetting("trakt.refresh_token", your_refresh)
                                            addon.setSetting("trakt.user_id", your_username)
                                            addon.setSetting("trakt.client_id", var.client_am)
                                            addon.setSetting("trakt.client_secret", var.secret_am)
                except:
                        sync_support.failed()
                        xbmc.log('%s: TorqueLive Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Diamond Media Player
    #Trakt client id/secret are honoured from settings (no source patching needed),
    #same as POV/Umbrella/Infinity. No trakt_expires field exists in its settings.xml,
    #so there is nowhere to send one - matches FidoK19/TorqueLite/TorqueLive above.
                try:
                        if 'Diamond Media Player' in current:
                            if xbmcvfs.exists(var.chk_rdtplayer):
                                    chk_auth_rdtplayer = xbmcaddon.Addon('plugin.program.rdtplayer').getSetting("trakt_access_token")
                                    if True:  # Repair the complete Trakt bundle.
                                            addon = xbmcaddon.Addon("plugin.program.rdtplayer")
                                            addon.setSetting("trakt_client_id", var.client_am)
                                            addon.setSetting("trakt_client_secret", var.secret_am)
                                            addon.setSetting("trakt_access_token", your_token)
                                            addon.setSetting("trakt_refresh_token", your_refresh)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Diamond Media Player Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #TMDb Movies
    #TRAKT_CLIENT_ID/SECRET are hardcoded in resources/lib/config.py, read as
    #ADDON.getSetting('trakt_client_id') or <hardcoded value> - source patch needed,
    #same as Aliunde K19/Blue Balls/Twisted (also needs a router.py revoke block,
    #added alongside this). trakt_created_at + trakt_expires_in are tracked
    #separately (not a single expiry field): Trakt tokens are always a fixed
    #90-day (7776000s) lifetime, so created_at is back-computed from ReAuthorize's
    #own absolute expiry rather than left blank - a blank/zero created_at would
    #read as "already expired" and make the addon refresh (and spend) the shared
    #token on its very first use even though it is still fresh.
                try:
                        if 'TMDb Movies' in current:
                            if xbmcvfs.exists(var.chk_tmdbmovies):
                                    chk_auth_tmdbmovies = xbmcaddon.Addon('plugin.video.tmdbmovies').getSetting("trakt_access_token")
                                    if True:  # Repair the complete Trakt bundle.

                                            # TMDb Movies 1.1.308 moved config.py to resources/lib/core/. Its settings override the
                                            # hardcoded keys either way, so the patch is optional: a missing file must not stop the
                                            # settings below being written (it did, and TMDb Movies got no Trakt at all).
                                            try:
                                                cfg = var.path_tmdbmovies
                                                if not os.path.isfile(cfg):
                                                    cfg = os.path.join(os.path.dirname(var.path_tmdbmovies), 'core', 'config.py')
                                                with open(cfg, 'r') as f:
                                                    data = f.read()
                                                client = data.replace(var.tmdbmovies_client, var.client_am).replace(var.tmdbmovies_secret, var.secret_am)
                                                with open(cfg, 'w') as f:
                                                    f.write(client)
                                            except Exception:
                                                sync_support.failed()
                                                xbmc.log('%s: TMDb Movies source patch skipped (config.py not found)' % var.amgr, xbmc.LOGINFO)

                                            addon = xbmcaddon.Addon("plugin.video.tmdbmovies")
                                            addon.setSetting("trakt_client_id", var.client_am)
                                            addon.setSetting("trakt_client_secret", var.secret_am)
                                            addon.setSetting("trakt_access_token", your_token)
                                            addon.setSetting("trakt_refresh_token", your_refresh)
                                            expires_in = 7776000
                                            your_expires_float = float(your_expires)
                                            addon.setSetting("trakt_expires_in", str(expires_in))
                                            addon.setSetting("trakt_created_at", str(int(your_expires_float) - expires_in))
                except:
                        sync_support.failed()
                        xbmc.log('%s: TMDb Movies Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

    #Youtube Theater
    #trakt_client_id/secret are honoured from settings (resources/modules/general.py's
    #_get_trakt_client_secret() checks Addon.getSetting first, hardcoded default
    #second) - no source patching or router.py block needed, unlike TMDb Movies.
    #trakt_expires_at exists as its own field (not created_at/expires_in like
    #TMDb Movies), so ReAuthorize's own absolute expiry maps straight across.
                try:
                        if 'Youtube Theater' in current:
                            if xbmcvfs.exists(var.chk_youtubetheater):
                                    chk_auth_ytheater = xbmcaddon.Addon('plugin.video.youtubetheater').getSetting("trakt_access_token")
                                    if True:  # Repair the complete Trakt bundle.
                                            addon = xbmcaddon.Addon("plugin.video.youtubetheater")
                                            addon.setSetting("trakt_client_id", var.client_am)
                                            addon.setSetting("trakt_client_secret", var.secret_am)
                                            addon.setSetting("trakt_access_token", your_token)
                                            addon.setSetting("trakt_refresh_token", your_refresh)
                                            addon.setSetting("trakt_expires_at", your_expires)
                except:
                        sync_support.failed()
                        xbmc.log('%s: Youtube Theater Trakt Failed!' % var.amgr, xbmc.LOGINFO)
                        pass

