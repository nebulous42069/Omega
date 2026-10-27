
ReAuthorize
===========
One authorization point. All your add-ons. Survives build installs.

ReAuthorize lets you authorize Real-Debrid, Premiumize, All-Debrid, TorBox,
Easy Debrid, OffCloud, Easynews, FilePursuit, Simkl, Trakt, Last.fm, MDBList,
Fanart.TV, YouTube for Kodi, and Metadata services once - then pushes those
credentials across every supported add-on automatically. After a build install
wipes your settings, ReAuthorize restores everything on the next Kodi start
with no action required from you.


----------------------------------------------------------------
YOUR DATA IS YOURS - PRIVACY & SECURITY
----------------------------------------------------------------
ReAuthorize's auto-restore feature stores an encoded copy of your
credentials on a private server so they can be recovered after a build
install or device wipe.

Here is what that means for your privacy:

- Your credentials are uniquely tied to your Kodi installation.
  A random device ID is generated the first time ReAuthorize runs
  and stored locally. No one else's device ID matches yours - not
  even someone on the same network or using the same build.

- No one else can read your data. Each device ID has its own
  isolated vault on the server. Fetching credentials requires the
  exact device ID that was generated on your machine.

- Nothing is logged. The server does not record request times, IP
  addresses, or access history. Only your encoded credential data
  is stored - nothing else.

- Your data is never shared with third parties, never sold, and never
  used for any purpose other than restoring your own credentials to
  your own device.

- The credentials themselves (Real-Debrid token, Trakt token, etc.)
  are temporary access tokens issued by each service. They grant access
  to those services - they are NOT your password. Even in the extremely
  unlikely event someone obtained them, they could not log in to your
  account or change your password.

- You can delete your server backup at any time from
  Settings > Backup & Restore > Server Sync > Delete Device from Server.
  After deletion nothing remains on the server.

Bottom line: ReAuthorize is a convenience tool, not a data broker.
Your credentials stay yours.


----------------------------------------------------------------
WHEN WILL I NEED TO RE-AUTHORIZE?
----------------------------------------------------------------
ReAuthorize restores your credentials automatically on startup after
a build install - in most cases you will not need to do anything.

You will need to manually re-authorize in these situations:

  Trakt
    - Your Trakt token expires after 90 days of no use, or if you
      revoke access from trakt.tv > Settings > Applications.
    - ReAuthorize refreshes the token silently in the background
      while it is still valid, so most users never see expiry.

  Real-Debrid
    - Tokens do not expire as long as your subscription is active.
    - If your subscription lapses and you renew, re-authorize once.

  Premiumize / All-Debrid / TorBox / Easy Debrid
    - Tokens are long-lived and do not expire during an active account.
    - Re-authorize only if you change your password or revoke access.

  OffCloud / Easynews / FilePursuit
    - These use your username/password or API key directly.
    - Re-enter only if you change your credentials on the service.

  Simkl
    - Tokens do not expire. Re-authorize only if you revoke access
      from simkl.com/settings/apps or change your Client ID.

  Metadata (TMDb, Fanart.TV, etc.)
    - API keys do not expire. No re-authorization needed.


----------------------------------------------------------------
FOR BUILDERS - HOW TO INCLUDE REAUTHORIZE IN YOUR BUILD
----------------------------------------------------------------
1. Add both add-ons to your build:
     script.module.reauthorize
     script.module.reauthorize-core

2. Add your scrapers as you normally would - no extra steps needed.
   ReAuthorize does not touch scraper settings.

That is it. ReAuthorize does nothing on a fresh build until the
end user authorizes their own services, so there is no risk of your
personal credentials ever appearing in a build you zip and share.

When an end user installs your build and opens ReAuthorize for the
first time, the Read Me First tab walks them through getting started.
They authorize their own services from the service tabs. Each one
is saved and backed up as soon as it is linked, so their credentials
survive all future build installs automatically.


----------------------------------------------------------------
FOR BUILDERS - RUNSCRIPT QUICK REFERENCE
----------------------------------------------------------------

Open ReAuthorize Settings:
  RunAddon(script.module.reauthorize)

Authorize:
  Real-Debrid    RunScript(script.module.reauthorize, action=realdebridAuth)
  Premiumize     RunScript(script.module.reauthorize, action=premiumizeAuth)
  All-Debrid     RunScript(script.module.reauthorize, action=alldebridAuth)
  TorBox         RunScript(script.module.reauthorize, action=torboxAuth)
  Easy Debrid    RunScript(script.module.reauthorize, action=easydebridAuth)
  OffCloud       RunScript(script.module.reauthorize, action=offcloudAuth)
  Easynews       RunScript(script.module.reauthorize, action=easynewsAuth)
  FilePursuit    RunScript(script.module.reauthorize, action=filepursuitAuth)
  Simkl          RunScript(script.module.reauthorize, action=simklAuth)
  Trakt for Kodi RunScript(script.module.reauthorize, action=traktAuth)
  TMDb           RunScript(script.module.reauthorize, action=tmdbAuth)

Sync (re-push credentials to installed add-ons):
  Real-Debrid    RunScript(script.module.reauthorize, action=realdebridReSync)
  Premiumize     RunScript(script.module.reauthorize, action=premiumizeReSync)
  All-Debrid     RunScript(script.module.reauthorize, action=alldebridReSync)
  TorBox         RunScript(script.module.reauthorize, action=torboxReSync)
  Easy Debrid    RunScript(script.module.reauthorize, action=easydebridReSync)
  OffCloud       RunScript(script.module.reauthorize, action=offcloudReSync)
  Easynews       RunScript(script.module.reauthorize, action=easynewsReSync)
  FilePursuit    RunScript(script.module.reauthorize, action=filepursuitReSync)
  Simkl          RunScript(script.module.reauthorize, action=simklReSync)
  Trakt for Kodi RunScript(script.module.reauthorize, action=traktReSync)
  Metadata       RunScript(script.module.reauthorize, action=metaReSync)
  YouTube        RunScript(script.module.reauthorize, action=youtubeReSync)
  All Services   RunScript(script.module.reauthorize, action=ReSyncAll)

View Authorized Add-ons:
  Real-Debrid    ActivateWindow(10001,plugin://script.module.reauthorize-core/?mode=realdebrid,return)
  Premiumize     ActivateWindow(10001,plugin://script.module.reauthorize-core/?mode=premiumize,return)
  All-Debrid     ActivateWindow(10001,plugin://script.module.reauthorize-core/?mode=alldebrid,return)
  Trakt          ActivateWindow(10001,plugin://script.module.reauthorize-core/?mode=trakt,return)
  TorBox         ActivateWindow(10001,plugin://script.module.reauthorize-core/?mode=torbox,return)
  All Accounts   ActivateWindow(10001,plugin://script.module.reauthorize-core/?mode=allaccts,return)
  Metadata       ActivateWindow(10001,plugin://script.module.reauthorize-core/?mode=metadata,return)


----------------------------------------------------------------
NUKE THIS DEVICE
----------------------------------------------------------------
Wipes all credentials and removes your profile from the server so
you can start completely fresh. Available under Settings > Reset &
Clear > Nuke This Device. This cannot be undone.
