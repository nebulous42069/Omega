
Diggz Account Manager
===========
One authorization point. All your add-ons. Survives build installs.

Diggz Account Manager lets you authorize Real-Debrid, Premiumize, All-Debrid, TorBox,
Easy Debrid, OffCloud, Easynews, FilePursuit, Simkl, Trakt, Last.fm, MDBList,
Fanart.TV, YouTube for Kodi, and Metadata services once - then pushes those
credentials across every supported add-on automatically. After a build install
wipes your settings, Diggz Account Manager restores everything on the next Kodi start
with no action required from you.


----------------------------------------------------------------
YOUR DATA IS YOURS - PRIVACY & SECURITY
----------------------------------------------------------------
Diggz Account Manager's auto-restore feature stores an encoded copy of your
credentials on a private server so they can be recovered after a build
install or device wipe.

Here is what that means for your privacy:

- Your credentials are uniquely tied to your Kodi installation.
  A random device ID is generated the first time Diggz Account Manager runs
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

Bottom line: Diggz Account Manager is a convenience tool, not a data broker.
Your credentials stay yours.


----------------------------------------------------------------
WHEN WILL I NEED TO RE-AUTHORIZE?
----------------------------------------------------------------
Diggz Account Manager restores your credentials automatically on startup after
a build install - in most cases you will not need to do anything.

You will need to manually re-authorize in these situations:

  Trakt
    - Your Trakt token expires after 90 days of no use, or if you
      revoke access from trakt.tv > Settings > Applications.
    - Diggz Account Manager refreshes the token silently in the background
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
FOR BUILDERS - HOW TO INCLUDE Diggz Account Manager IN YOUR BUILD
----------------------------------------------------------------
1. Add both add-ons to your build:
     script.module.authorizediggz
     script.module.authorizediggz-core

2. Add your scrapers as you normally would - no extra steps needed.
   Diggz Account Manager does not touch scraper settings.

That is it. Diggz Account Manager does nothing on a fresh build until the
end user authorizes their own services, so there is no risk of your
personal credentials ever appearing in a build you zip and share.

When an end user installs your build and opens Diggz Account Manager for the
first time, the Read Me First tab walks them through getting started.
They authorize their own services from the service tabs. Each one
is saved and backed up as soon as it is linked, so their credentials
survive all future build installs automatically.


----------------------------------------------------------------
FOR BUILDERS - RUNSCRIPT QUICK REFERENCE
----------------------------------------------------------------

Open Diggz Account Manager Settings:
  RunAddon(script.module.authorizediggz)

Authorize:
  Real-Debrid    RunScript(script.module.authorizediggz, action=realdebridAuth)
  Premiumize     RunScript(script.module.authorizediggz, action=premiumizeAuth)
  All-Debrid     RunScript(script.module.authorizediggz, action=alldebridAuth)
  TorBox         RunScript(script.module.authorizediggz, action=torboxAuth)
  Easy Debrid    RunScript(script.module.authorizediggz, action=easydebridAuth)
  OffCloud       RunScript(script.module.authorizediggz, action=offcloudAuth)
  Easynews       RunScript(script.module.authorizediggz, action=easynewsAuth)
  FilePursuit    RunScript(script.module.authorizediggz, action=filepursuitAuth)
  Simkl          RunScript(script.module.authorizediggz, action=simklAuth)
  Trakt for Kodi RunScript(script.module.authorizediggz, action=traktAuth)
  TMDb           RunScript(script.module.authorizediggz, action=tmdbAuth)

Sync (re-push credentials to installed add-ons):
  Real-Debrid    RunScript(script.module.authorizediggz, action=realdebridReSync)
  Premiumize     RunScript(script.module.authorizediggz, action=premiumizeReSync)
  All-Debrid     RunScript(script.module.authorizediggz, action=alldebridReSync)
  TorBox         RunScript(script.module.authorizediggz, action=torboxReSync)
  Easy Debrid    RunScript(script.module.authorizediggz, action=easydebridReSync)
  OffCloud       RunScript(script.module.authorizediggz, action=offcloudReSync)
  Easynews       RunScript(script.module.authorizediggz, action=easynewsReSync)
  FilePursuit    RunScript(script.module.authorizediggz, action=filepursuitReSync)
  Simkl          RunScript(script.module.authorizediggz, action=simklReSync)
  Trakt for Kodi RunScript(script.module.authorizediggz, action=traktReSync)
  Metadata       RunScript(script.module.authorizediggz, action=metaReSync)
  YouTube        RunScript(script.module.authorizediggz, action=youtubeReSync)
  All Services   RunScript(script.module.authorizediggz, action=ReSyncAll)

View Authorized Add-ons:
  Real-Debrid    ActivateWindow(10001,plugin://script.module.authorizediggz-core/?mode=realdebrid,return)
  Premiumize     ActivateWindow(10001,plugin://script.module.authorizediggz-core/?mode=premiumize,return)
  All-Debrid     ActivateWindow(10001,plugin://script.module.authorizediggz-core/?mode=alldebrid,return)
  Trakt          ActivateWindow(10001,plugin://script.module.authorizediggz-core/?mode=trakt,return)
  TorBox         ActivateWindow(10001,plugin://script.module.authorizediggz-core/?mode=torbox,return)
  All Accounts   ActivateWindow(10001,plugin://script.module.authorizediggz-core/?mode=allaccts,return)
  Metadata       ActivateWindow(10001,plugin://script.module.authorizediggz-core/?mode=metadata,return)


----------------------------------------------------------------
NUKE THIS DEVICE
----------------------------------------------------------------
Wipes all credentials and removes your profile from the server so
you can start completely fresh. Available under Settings > Reset &
Clear > Nuke This Device. This cannot be undone.
