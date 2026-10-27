import xbmc
from libs.common import var

# Shared accessor: a cached Addon handle can revert settings written
# through another instance. See control._Settings.
from reauthorize.modules.control import accountmgr


class Auth:
    def debridlink_auth(self):
        """
        Nothing to sync. plugin.video.salts was the only addon ReAuthorize
        ever pushed a Debrid-Link credential to, and Salts is retired.

        Returning False rather than quietly doing nothing, so callers do not
        flag Debrid-Link as synced when it reached no addon at all. The
        credential is still stored and backed up - it just has nowhere to go
        until a supported addon is wired up.
        """
        if accountmgr.getSetting('debridlink.token'):
            xbmc.log('%s: Debrid-Link is stored but no installed add-on '
                     'accepts it yet.' % var.amgr, xbmc.LOGINFO)
        return False
