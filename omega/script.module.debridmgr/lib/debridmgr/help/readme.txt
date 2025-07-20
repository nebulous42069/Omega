
Description:
An add-on to make the painful task of authorizing numerous add-ons effortless. Pair multiple service(s) with supported add-ons via a single authorization point and easily manage the data for these service(s).

7o9 Repository
Instructions for adding this repo to Kodi:
-Open the Kodi File Manager
-Select "Add source"
-The path for the source is https://zaxxon709.github.io/repo/ (Give it the name "7o9Repo")

Custom Trakt API Key Section for Users:
-If you have your own Trakt API keys, please use them.
-You can enter your keys within Debrid Manager's settings under the Accounts menu.
-If you do not already have keys then just follow the link below to create them.

https://trakt.tv/oauth/applications/new

Custom Trakt API Key Section for Builders:
-Builders can add their own custom keys here.
-If you do not already have keys then just follow the link below to create them.
-You can enter your keys within Debrid Manager's settings under the Advanced menu.
-Keys added here are obfuscated using asterisks and are persistent after add-on updates/revokes.

https://trakt.tv/oauth/applications/new

Backup/Restore Data:
-The options to backup, restore and clear data can be found in Debrid Manager's settings menu.
-The backup created during authorization only backs up current installed add-ons. If you decide to add additional supported addons you should create another backup to save -     data for those add-ons.
-The default path is not persistent after build updates or fresh starts. For builders, I'd recommend your wizard data path for backups.
-The default backup path can be changed any time in Debrid Manager's settings menu. If the default path is changed make sure to complete another backup.
-Default Backup Path = special://userdata/addon_data/plugin.program.debridmgr/

Restore all Add-ons to Default:
WARNING! Use only to restore system to default settings.
-Open Debrid Manager and Navigate to the ‘Advanced’ category.
-Select ‘Restore Default Settings'
-This action will revoke all services, reset all add-on settings back to default, and delete all your saved data

How to Authorize Debrid:
-Open Debrid Manager
-Navigate to the ‘Accounts’ category and choose your debrid service(s)
-Select 'Authorize' and proceed to pair your account
-Wait for the 'Sync is complete' notification and choose 'OK' to exit
-All supported add-ons are now authorized!

How to Authorize Trakt:
-Open Debrid Manager
-Navigate to the ‘Accounts’ category and select ‘Authorize’ to pair your account
-Wait for the 'Sync is complete' notification and when prompted choose 'OK' to force close Kodi
-All supported add-ons are now authorized!

How to Sync Furk/Easynews/FilePursuit and Metadata:
-Open Debrid Manager
-Navigate to the ‘Accounts’ category and add your data into the appropriate field(s)
-Choose 'Sync Add-ons' to sync your data with installed Add-ons
-Wait for the 'Sync is complete' notification and when prompted choose 'OK' to force close Kodi
-All supported add-ons are now synced!

Open Debrid Manager:
RunAddon(script.module.debridmgr)


Authorize:
Real-Debrid
RunScript(script.module.debridmgr, action=realdebridAuth)

Premiumize
RunScript(script.module.debridmgr, action=premiumizeAuth)

AllDebrid
RunScript(script.module.debridmgr, action=alldebridAuth)

Trakt
RunScript(script.module.debridmgr, action=traktAuth)

TMDb
RunScript(script.module.debridmgr, action=tmdbAuth)


Sync:
Real-Debrid
RunScript(script.module.debridmgr, action=realdebridReSync)

Premiumize
RunScript(script.module.debridmgr, action=premiumizeReSync)

AllDebrid
RunScript(script.module.debridmgr, action=alldebridReSync)

Trakt
RunScript(script.module.debridmgr, action=traktReSync)

Sync Multiple Debrid Accounts
RunScript(script.module.debridmgr, action=ReSyncAll)

Sync Furk/Easynews/FilePursuit Accounts
RunScript(script.module.debridmgr, action=SyncAll)

Sync Metadata Accounts
RunScript(script.module.debridmgr, action=metaReSync)


View Authorized Addons:
Real-Debrid
ActivateWindow(10001,plugin://script.module.dbview/?mode=realdebrid,return)

Premiumize
ActivateWindow(10001,plugin://script.module.dbview/?mode=premiumize,return)

AllDebrid
ActivateWindow(10001,plugin://script.module.dbview/?mode=alldebrid,return)

Trakt
ActivateWindow(10001,plugin://script.module.dbview/?mode=trakt,return)

View Multiple Debrid Accounts
ActivateWindow(10001,plugin://script.module.dbview/?mode=allaccts,return)

View Furk/Easynews/FilePursuit Accounts
ActivateWindow(10001,plugin://script.module.dbview/?mode=nondebrid,return)

View Metadata Accounts
ActivateWindow(10001,plugin://script.module.dbview/?mode=metadata,return)