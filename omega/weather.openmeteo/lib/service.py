import os

from . import weather
from . import config
from . import utils
from . import api

def Main():
	startup = True
	utils.log(f'Starting service ...')
	utils.log(config.addon_info, 3)

	while not utils.monitor.abortRequested():
		utils.setsetting('service', 'running')

		# Geolocation
		if startup and not utils.setting('geoip'):
			weather.Main('1', mode='geoip')
			weather.Main('1', mode='download')

		# Init
		if utils.settingrpc('weather.addon') == 'weather.openmeteo':
			utils.log(f'Running service ...', 3)

			start   = utils.dt('nowutc')
			current = utils.settingrpc("weather.currentlocation")

			# Download
			for locid in range(1, config.maxlocs):
				if utils.setting(f'loc{locid}'):
					weather.Main(str(locid), mode='download')

			# Update
			weather.Main(str(current), mode='update')
			utils.setsetting('service', 'idle')

			# Notification
			if startup or utils.lastupdate('alert_notification') >= int(utils.setting('alert_interval')) * 60:
				utils.setupdate('alert_notification')

				for locid in range(1, config.maxlocs):
					if utils.setting(f'loc{locid}') and utils.settingbool(f'loc{locid}alert'):
						weather.Main(str(locid), mode='notification')

			end = round((utils.dt('nowutc') - start).total_seconds(), 3)
			utils.log(f'Finished ({end} sec)', 3)

		else:
			utils.log('Addon not enabled ...', 3)
			utils.setsetting('service', 'idle')

		startup = False
		utils.monitor.waitForAbort(300)

	utils.log(f'Stopping service ...')
	api.s.close()

	# Workaround KODI issue (v0.9.5)
	try:
		utils.setsetting('service', 'stopped')
	except:
		pass

