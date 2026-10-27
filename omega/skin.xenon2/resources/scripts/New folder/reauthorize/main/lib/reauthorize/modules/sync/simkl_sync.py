import xbmc
import xbmcaddon
from reauthorize.modules import own_settings  # one read or write of our settings at a time
import xbmcvfs

from libs.common import var
from reauthorize.modules import control

# Simkl ties a sign-in to the app that made it: ReAuthorize's token under another add-on's
# Simkl app key is refused (401 user_token_failed, checked against Simkl 2026-10-05). So an
# add-on needs BOTH the token and ReAuthorize's app key. Until 1.3.9 most blocks here wrote
# only the token, and Red Light, Gears, TMDb Movies, The Crew and the Simkl scrobbler were
# not written at all (a user's report). Where the add-on reads its key from a setting, the
# setting is written; where the key is a line in a source file, simkl_appkey swaps the line.



from reauthorize.modules import sync_support
xbmcaddon = sync_support.addon_api(xbmcaddon)
def _client(stored):
    """ReAuthorize's Simkl app key: the saved one, or the one built in (old sign-ins saved none)."""
    if stored:
        return stored
    try:
        from reauthorize.modules.auth.simkl import SIMKL_CLIENT_ID
        return SIMKL_CLIENT_ID
    except Exception:
        sync_support.failed()
        return ''


def _write(addon, values):
    """setSetting for each (id, value) that differs. Returns how many were written."""
    written = 0
    for key, value in values:
        if addon.getSetting(key) != value:
            addon.setSetting(key, value)
            written += 1
    return written


# Where each add-on with its Simkl app key in a source file keeps the token (add-on id, setting).
_FILE_KEY_ADDONS = (('plugin.video.umbrella', 'simkltoken'),
                    ('plugin.video.thearchives', 'simkl.access_token'),
                    ('script.simkl', 'token'),
                    ('plugin.video.gratisred', 'simkl.token'))


def _gratisred_values(token, user, linking):
    """GratisRed is signed in with simkl.token + simkl.user; auth_version 1 keeps it on the key ReAuthorize swaps."""
    return [('simkl.token', token), ('simkl.user', user), ('simkl.auth_version', '1' if linking else ''),
            ('simkl.refresh', ''), ('simkl.expires', ''), ('simkl.authed', 'yes' if linking else '')]


def ensure_keys():
    """
    Start-up: an update of an add-on puts its own Simkl app key back in its file. Put ours back,
    and the sign-in with it.

    The sign-in too, because of what the scrobbler does (seen on the bench, 2026-10-06): the
    moment it was reinstalled it called Simkl with its own key and ReAuthorize's token, got
    401 user_token_failed, and BLANKED its token. So "still holds our token" is not the test.
    An add-on whose token is blank or ours is re-linked; one that holds a DIFFERENT sign-in was
    signed in to by the user inside the add-on, and keeps it and its own key.
    Returns how many add-ons were changed.
    """
    accountmgr = own_settings.addon()
    token = accountmgr.getSetting('simkl.token')
    if not token:
        return 0
    from reauthorize.modules.sync import simkl_appkey
    client = _client(accountmgr.getSetting('simkl.client.id'))
    username = accountmgr.getSetting('simkl.username')
    changed = 0
    for addon_id, setting in _FILE_KEY_ADDONS:
        try:
            if not xbmcvfs.exists(var.addons + addon_id + '/'):
                continue
            addon = xbmcaddon.Addon(addon_id)
            held = addon.getSetting(setting)
            if held and held != token:
                continue
            touched = simkl_appkey.ensure(addon_id, client)
            if held != token:
                addon.setSetting(setting, token)
                if addon_id == 'plugin.video.umbrella':
                    addon.setSetting('simklusername', username)
                elif addon_id == 'plugin.video.gratisred':
                    _write(addon, _gratisred_values(token, username or 'Simkl', True))
                xbmc.log('[ReAuthorize Simkl] sign-in put back in %s' % addon_id, xbmc.LOGINFO)
                touched = True
            if touched:
                changed += 1
        except Exception:
            sync_support.failed()
            xbmc.log('%s: Simkl key check failed for %s' % (var.amgr, addon_id), xbmc.LOGINFO)
    return changed


def sign_out_addons():
    """Simkl Revoke: blank the sign-in in every add-on and give each its own app key back."""
    control.set_wiping(True)
    try:
        Auth().simkl_auth()
        sync_support.scrub_crew_simkl()
    finally:
        control.set_wiping(False)


class Auth:
    def simkl_auth(self):
        accountmgr    = own_settings.addon()
        your_token    = accountmgr.getSetting('simkl.token')
        your_username = accountmgr.getSetting('simkl.username')
        your_client   = accountmgr.getSetting('simkl.client.id')

        from reauthorize.modules.sync import simkl_appkey
        wiping     = control.wiping()
        linking    = bool(your_token) and not wiping          # a sign-in to hand out
        app_client = _client(your_client) if linking else ''   # blank on a wipe: the add-on's own key again
        shown_user = your_username or ('Simkl' if linking else '')

        # Umbrella - its app key is a line in resources/lib/modules/simkl.py
        try:
            if xbmcvfs.exists(var.chk_umb):
                if linking:
                    simkl_appkey.ensure('plugin.video.umbrella', app_client)
                elif wiping:
                    simkl_appkey.restore('plugin.video.umbrella')
                addon = xbmcaddon.Addon('plugin.video.umbrella')
                if addon.getSetting('simkltoken') != your_token or not addon.getSetting('simkltoken'):
                    addon.setSetting('simkltoken',   your_token)
                    addon.setSetting('simklusername', your_username)
        except:
            sync_support.failed()
            xbmc.log('%s: Simkl Umbrella sync failed!' % var.amgr, xbmc.LOGINFO)

        # Infinity
        try:
            if xbmcvfs.exists(var.chk_infinity):
                addon = xbmcaddon.Addon('plugin.video.infinity')
                if addon.getSetting('simkltoken') != your_token or not addon.getSetting('simkltoken'):
                    addon.setSetting('simkltoken',   your_token)
                    addon.setSetting('simklusername', your_username)
                    if your_client or control.wiping():
                        addon.setSetting('simkl.apikey', your_client)
        except:
            sync_support.failed()
            xbmc.log('%s: Simkl Infinity sync failed!' % var.amgr, xbmc.LOGINFO)

        # Otaku 5.3.4: simkl.login is an action, not a credential.
        # Genocide
        try:
            if xbmcvfs.exists(var.chk_newgenocide):
                addon = xbmcaddon.Addon('plugin.video.genocide')
                if addon.getSetting('simkl.api.key') != your_client or not addon.getSetting('simkl.api.key'):
                    addon.setSetting('simkl.api.key', your_client)
        except:
            sync_support.failed()
            xbmc.log('%s: Simkl Genocide sync failed!' % var.amgr, xbmc.LOGINFO)

        # The Archives - its app key is a line in resources/lib/util/dev_api.py
        try:
            if xbmcvfs.exists(var.chk_thearchives):
                if linking:
                    simkl_appkey.ensure('plugin.video.thearchives', app_client)
                elif wiping:
                    simkl_appkey.restore('plugin.video.thearchives')
                addon = xbmcaddon.Addon('plugin.video.thearchives')
                if addon.getSetting('simkl.access_token') != your_token or not addon.getSetting('simkl.access_token'):
                    addon.setSetting('simkl.access_token', your_token)
        except:
            sync_support.failed()
            xbmc.log('%s: Simkl The Archives sync failed!' % var.amgr, xbmc.LOGINFO)

        # Prism - a 'simkl.client_id' setting wins over its own key. Its own sign-ins carry a
        # refresh token; ours has none, and a leftover one would be renewed under our key and fail.
        # Prism also refuses to use any sign-in unless 'simkl.auth_version' says "v2", and asks the
        # user to sign in again ("Simkl login was updated", seen on the bench 2026-10-06). That flag
        # is all it checks: Simkl answers Prism's own calls with ReAuthorize's sign-in (checked live).
        try:
            if xbmcvfs.exists(var.chk_prism):
                addon = xbmcaddon.Addon('plugin.video.prism')
                if addon.getSetting('simkl.auth') != your_token or not addon.getSetting('simkl.auth'):
                    addon.setSetting('simkl.auth',     your_token)
                    addon.setSetting('simkl.username', your_username)
                if linking or wiping:
                    _write(addon, [('simkl.client_id', app_client), ('simkl.refresh', ''), ('simkl.token_expires', '0'),
                                   ('simkl.auth_version', 'v2' if linking else '')])
        except:
            sync_support.failed()
            xbmc.log('%s: Simkl Prism sync failed!' % var.amgr, xbmc.LOGINFO)

        # Red Light - settings.db. Signed in = simkl.user + simkl.token; a key in simkl.client that
        # is not one of its own is used as it is; auth_version 1 = a sign-in with no refresh token.
        try:
            if linking or wiping:
                from reauthorize.modules.db import redlight_db
                redlight_db.push([('simkl.token', your_token),
                                  ('simkl.user', shown_user),
                                  ('simkl.client', app_client),
                                  ('simkl.auth_version', '1'),
                                  ('simkl.refresh', '0'),
                                  ('simkl.expires', '0')])
        except:
            sync_support.failed()
            xbmc.log('%s: Simkl Red Light sync failed!' % var.amgr, xbmc.LOGINFO)

        # Gears - settings.db. Signed in = simkl.user; its key is the simkl.client row.
        try:
            if linking or wiping:
                from reauthorize.modules.db import gears_db
                gears_db.push([('simkl.token', your_token),
                               ('simkl.user', shown_user),
                               ('simkl.username', shown_user),
                               ('simkl.client', app_client)])
        except:
            sync_support.failed()
            xbmc.log('%s: Simkl Gears sync failed!' % var.amgr, xbmc.LOGINFO)

        # TMDb Movies - 'simkl_client_id' is read before its own key; 'simkl_status' is what it shows.
        try:
            if (linking or wiping) and xbmcvfs.exists(var.chk_tmdbmovies):
                addon = xbmcaddon.Addon('plugin.video.tmdbmovies')
                status = ('Connected: %s' % your_username if your_username else 'Connected') if linking else 'Disconnected'
                _write(addon, [('simkl_client_id', app_client),
                               ('simkl_access_token', your_token),
                               ('simkl_username', your_username if linking else ''),
                               ('simkl_status', status)])
        except:
            sync_support.failed()
            xbmc.log('%s: Simkl TMDb Movies sync failed!' % var.amgr, xbmc.LOGINFO)

        # The Crew - 'simkl.client_id' is used instead of its own key. Signed in = simkl.token.
        # (Crew tracks with Trakt OR Simkl, the user's choice in Crew: 'tracker.service' is not touched.)
        try:
            if (linking or wiping) and xbmcvfs.exists(var.chk_crew):
                addon = xbmcaddon.Addon('plugin.video.thecrew')
                _write(addon, [('simkl.client_id', app_client),
                               ('simkl.token', your_token),
                               ('simkl.user', shown_user)])
        except:
            sync_support.failed()
            xbmc.log('%s: Simkl The Crew sync failed!' % var.amgr, xbmc.LOGINFO)

        # Cosmos - built with ReAuthorize in mind: its simkl.py reads 'simkl_access_token' from its
        # settings first ("for ReAuth compatibility", its own comment) and uses 'simkl_client_id' in
        # place of its own key. stored_at blank = "long-lived until Simkl rejects it", so it does not
        # try to renew a sign-in that has no refresh token. simkl_token.json is only its fallback when
        # the setting is blank, which is why a wipe has to remove it.
        try:
            if (linking or wiping) and xbmcvfs.exists(var.chk_cosmos):
                addon = xbmcaddon.Addon('plugin.video.cosmos')
                values = [('simkl_client_id', app_client), ('simkl_access_token', your_token),
                          ('simkl_refresh_token', ''), ('simkl_expires_in', ''), ('simkl_stored_at', ''),
                          ('simkl_username', your_username if linking else ''),
                          ('simkl_auth_done', 'true' if linking else 'false')]
                if addon.getSetting('simkl_access_token') != your_token:
                    # another account's cached lists must not be shown for this one (Cosmos does the same on sign-in)
                    values += [('simkl_cache_identity', ''), ('simkl_user_id', '')]
                _write(addon, values)
                if wiping:
                    leftover = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.cosmos/simkl_token.json')
                    if xbmcvfs.exists(leftover):
                        xbmcvfs.delete(leftover)
        except:
            sync_support.failed()
            xbmc.log('%s: Simkl Cosmos sync failed!' % var.amgr, xbmc.LOGINFO)

        # GratisRed - its app key is a line in resources/lib/modules/simkl.py (a user's report, 2026-10-05)
        try:
            if (linking or wiping) and xbmcvfs.exists(var.chk_gratisred):
                if linking:
                    simkl_appkey.ensure('plugin.video.gratisred', app_client)
                else:
                    simkl_appkey.restore('plugin.video.gratisred')
                _write(xbmcaddon.Addon('plugin.video.gratisred'), _gratisred_values(your_token, shown_user, linking))
        except:
            sync_support.failed()
            xbmc.log('%s: Simkl GratisRed sync failed!' % var.amgr, xbmc.LOGINFO)

        # Simkl scrobbler (script.simkl) - its app key is a line in resources/lib/api_simkl.py
        try:
            if (linking or wiping) and xbmcvfs.exists(var.chk_simkl):
                if linking:
                    simkl_appkey.ensure('script.simkl', app_client)
                else:
                    simkl_appkey.restore('script.simkl')
                addon = xbmcaddon.Addon('script.simkl')
                _write(addon, [('token', your_token)])
        except:
            sync_support.failed()
            xbmc.log('%s: Simkl scrobbler sync failed!' % var.amgr, xbmc.LOGINFO)
