import os

from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from . import config
from . import utils
from . import api

class Main():

	### MAIN
	def __init__(self, locid, mode='kodi'):

		if utils.monitor.abortRequested():
			return

		# Search
		if locid.startswith('loc'):
			api.setloc(locid[3])
			return

		# Wait for service thread
		if mode == 'kodi':
			count = 0
			while utils.setting('service') != 'idle':
				utils.log(f'Waiting for service thread: {utils.setting("service")}', 3)
				count += 1

				if count == 60:
					utils.log(f'Service thread not responding ...', 2)
					return

				utils.monitor.waitForAbort(1)

		# GeoIP
		if mode == 'geoip':
			api.getloc(locid)
			return

		# Init
		self.init(locid, mode)

		if not config.loc.lat or not config.loc.lon:
			utils.log(f'[LOC{locid}] Not configured', 1)
			return

		# Download
		if self.mode == 'download':

			# Weather
			if utils.lastupdate(f'loc{locid}data') >= 3600:
				with ThreadPoolExecutor(3) as pool:
					pool.map(self.getdata, config.map)

				if api.network():
					utils.setupdate(f'loc{locid}data')

			# Map
			if utils.lastupdate(f'loc{locid}map') >= 604800:
				self.getmap('osm')

				if api.network():
					utils.setupdate(f'loc{locid}map')


			# Layers
			if utils.lastupdate(f'loc{locid}layer') >= 1800:
				with ThreadPoolExecutor(2) as pool:
					pool.map(self.getmap, config.map_layers)

				if api.network():
					utils.setupdate(f'loc{locid}layer')

		# Update
		elif self.mode == 'update' or self.mode == 'kodi':

			# Note: Setting window properties is CPU bound, using threads seems to be slower
			# This needs more testing ...
			# with ThreadPoolExecutor(3) as pool:
			#	pool.map(self.setdata, config.map)
			for map in config.map:
				self.setdata(map)

			# Alerts
			config.alert()
			for map in config.map:
				self.setalert(map)

			# Properties
			self.setprop()

		# Update locs
		elif self.mode == 'updatelocs':
			self.setlocs()

		# Notification
		elif self.mode == 'notification':
			config.alert()

			for map in config.map:
				self.setalert(map)

			self.notification()

	### INIT
	def init(self, locid, mode):

		if mode == 'download':
			utils.log(f'[LOC{locid}] Initialising: mode={mode}, neterr={config.neterr}, net={api.network()}, dnscache={len(config.dnscache)}', 3)
		else:
			utils.log(f'[LOC{locid}] Initialising: mode={mode}', 3)

		# Addon
		config.init()

		# Location
		config.loc(locid)

		# Vars
		self.mode     = mode
		self.data     = {}
		self.now      = utils.dt('nowloc').strftime('%Y-%m-%d %H')
		self.today    = utils.dt('nowloc').strftime('%Y-%m-%d')
		self.midnight = utils.dt('nowloc').strftime('%Y-%m-%d 00')

		# Directory
		os.makedirs(f'{config.addon_cache}/{locid}', exist_ok=True)

	### GET DATA
	def getdata(self, type):
		utils.log(f'[LOC{config.loc.id}] Downloading data: {type}', 3)
		api.getdata(type, config.loc.id, [ config.loc.lat, config.loc.lon, self.today ])

	### SET DATA
	def setdata(self, type):

		# Data
		self.data[type] = api.getfile(f'{config.loc.id}/{type}.json')
		if not self.data[type]:
			utils.log(f'No {type} data for location {config.loc.id}', 2)
			return

		# Update data
		utils.log(f'[LOC{config.loc.id}] Updating data: {type}', 3)

		for map in config.map.get(type):

			# Current (Compatibility)
			if map[0] == 'current':
				self.setmap(type, map)

			# Current (Advanced)
			elif map[0] == 'currentskin' and config.addon.skin:
				self.setmap(type, map)

			# Current (KODI)
			elif map[0] == 'currentkodi' and self.mode == 'kodi':
				self.setmap(type, map)

			# Hourly (Compatibility)
			elif map[0] == 'hourly':
				self.setmulti(type, [ map, 'hourly', self.now, config.maxhours, config.minhours, 'hourly' ])

				if config.addon.enablehour:
					self.setmulti(type, [ map, 'hourly', self.midnight, config.maxhours, config.minhours, 'hour' ])

			# Hourly (Advanced)
			elif map[0] == 'hourlyskin' and config.addon.skin:
				self.setmulti(type, [ map, 'hourly', self.now, config.maxhours, config.minhours, 'hourly' ])

				if config.addon.enablehour:
					self.setmulti(type, [ map, 'hourly', self.midnight, config.maxhours, config.minhours, 'hour' ])

			# Daily (Compatibility)
			elif map[0] == 'daily':
				self.setmulti(type, [ map, 'daily', self.today, config.maxdays, config.mindays, 'daily' ])
				self.setmulti(type, [ map, 'daily', self.today, config.maxdays, config.mindays, 'day' ])

			# Daily (Advanced)
			elif map[0] == 'dailyskin' and config.addon.skin:
				self.setmulti(type, [ map, 'daily', self.today, config.maxdays, config.mindays, 'daily' ])
				self.setmulti(type, [ map, 'daily', self.today, config.maxdays, config.mindays, 'day' ])

			# Daily (KODI)
			elif map[0] == 'dailykodi' and self.mode == 'kodi':
				self.setmulti(type, [ map, 'daily', self.today, config.maxdays, config.mindays, 'daily' ])
				self.setmulti(type, [ map, 'daily', self.today, config.maxdays, config.mindays, 'day' ])

	### SET CURRENT
	def setcurrent(self, type, locid):

		# Data
		self.data[type] = api.getfile(f'{locid}/{type}.json')
		if not self.data[type]:
			utils.log(f'No {type} data for location {locid}', 2)
			return


		# Update data
		utils.log(f'[LOC{locid}] Updating current: {type}', 3)

		for map in config.map.get(type):

			# Current (Compatibility)
			if map[0] == 'current':
				self.setmap(type, map, locid=locid)

			# Current (Advanced)
			elif map[0] == 'currentskin' and config.addon.skin:
				self.setmap(type, map, locid=locid)

	### SET LOCATIONS
	def setlocs(self):
		locs = 0
		for locid in range(1, config.maxlocs):
			loc = utils.setting(f'loc{locid}')
			if loc:
				locs += 1

				config.loc(locid)
				for map in config.map:
					self.setcurrent(map, locid)

				utils.setprop(f'location{locid}', loc)
			else:
				utils.setprop(f'location{locid}', '')

		utils.setprop('locations', locs)

	### SET ALERT
	def setalert(self, type):

		# Data
		self.data[type] = api.getfile(f'{config.loc.id}/{type}.json')
		if not self.data[type]:
			utils.log(f'No {type} data for location {config.loc.id}', 2)
			return

		# Notification
		for map in config.map.get(type):
			if map[3] == 'graph':
				idx = utils.index(self.data[type])
				if idx:
					utils.setalert(self.data[type], map, idx, config.loc.id, config.loc.cid)

	### SET MULTI
	def setmulti(self, src, map):
		data  = self.data[src]
		time  = map[1]
		match = map[2]
		max   = map[3]
		min   = map[4]
		prop  = map[5]

		for idx in range(0, 300):

			try:
				if prop == 'day' or prop == 'daily':
					timecheck = utils.dt('stamploc', data[time]['time'][idx]).strftime('%Y-%m-%d')
				else:
					timecheck = utils.dt('stamploc', data[time]['time'][idx]).strftime('%Y-%m-%d %H')
			except:
				break

			if timecheck == match:

				if config.addon.skin is False and ( prop == 'hourly' or prop == 'daily' ):
					count = 1
				else:
					count = 0

				for index in range(idx, idx + max, 1):
					map[0][2][0] = prop
					self.setmap(src, map[0], index, count)
					count += 1

				count = -1
				for index in range(idx - 1, idx - min, -1):
					map[0][2][0] = prop
					self.setmap(src, map[0], index, count)
					count -= 1

				break

	### SET MAP
	def setmap(self, src, map, idx=None, count=None, locid=None):
		data = self.data[src]

		# Property
		if idx is not None:
			if map[2][0] == 'day':
				property = f'{map[2][0]}{count}.{map[2][1]}'
			else:
				property = f'{map[2][0]}.{count}.{map[2][1]}'
		else:
			if locid:
				property = f'{map[2][0]}.{locid}.{map[2][1]}'
			else:
				property = f'{map[2][0]}.{map[2][1]}'

		# Content
		try:
			content = utils.getprop(data, map, idx, count)
		except TypeError as e:
			utils.log(f'{property}: {type(e).__name__} {e}', 4)
			utils.clrprop(property)
		except Exception as e:
			utils.log(f'{property}: {type(e).__name__} {e}', 3)
			utils.clrprop(property)
		else:
			utils.setprop(property, content)

	### GET MAP
	def getmap(self, type):

		if not utils.settingbool(f'map{type}'):
			return

		utils.log(f'[LOC{config.loc.id}] Downloading map: {type}', 3)

		map   = []
		x, y  = utils.lat2coords(config.loc.lat, config.loc.lon, config.addon.mapzoom)
		tiles = [ [ x-1, y-1, 0, 0 ], [ x, y-1, 256, 0 ], [ x+1, y-1, 512, 0 ], [ x-1, y, 0, 256 ], [ x, y, 256, 256 ], [ x+1, y, 512, 256 ], [ x-1, y+1, 0, 512 ], [ x, y+1, 256, 512 ], [ x+1, y+1, 512, 512 ] ]

		# RV Index
		if type.startswith('rv'):
			time, path = api.getrvindex(type)

			if time is None or path is None:
				utils.log(f'RVIndex {type} currently not available ...', 3)
				return

		# Other
		else:
			time = utils.dt('nowutcstamp')
			path = None

		# Tiles
		for count in range(0,9):
			s, w, n, e = utils.coords2bbox(tiles[count][0], tiles[count][1], config.addon.mapzoom)
			map.append([ config.loc.id, type, count, config.addon.mapzoom, tiles[count][0], tiles[count][1], tiles[count][2], tiles[count][3], path, time, s, w, n, e ])

		# Check connectivity
		check = api.getmap(map[0], True)
		if check is None:
			utils.log(f'Map {type} currently not available ...', 3)
			return

		# Download
		with ThreadPoolExecutor(3) as pool:
			pool.map(api.getmap, map)

		# Merge
		api.mapmerge(map)

		# Cleanup
		dir     = f'{config.addon_cache}/{config.loc.id}'
		files   = sorted(list(Path(dir).glob(f'{type}_*')), reverse=True)
		history = int(utils.setting('maphistory'))*2

		for idx in range(0,100):

			try:
				file = files[idx]
			except:
				break
			else:
				if idx >= history:
					utils.log(f'Removing old map: {file.stem}', 3)
					os.remove(file)

	### PROPERTIES
	def setprop(self):

		# Maps
		index = 1
		for layer in config.map_layers:

			if not utils.settingbool(f'map{layer}'):
				continue

			dir     = f'{config.addon_cache}/{config.loc.id}'
			files   = sorted(list(Path(dir).glob(f'{layer}_*')), reverse=True)
			history = int(utils.setting('maphistory'))*2

			# Area
			if files:
				ut   = int(files[0].stem.split('_')[1])
				tz   = utils.dt('stamploc', ut)
				date = tz.strftime(config.kodi.date)
				time = tz.strftime(config.kodi.time)

				utils.setprop(f'Map.{index}.Area', f'{dir}/osm.png')
				utils.setprop(f'Map.{index}.Layer', f'{dir}/{layer}_{ut}.png')
				utils.setprop(f'Map.{index}.Heading', config.localization.layers.get(layer))
				utils.setprop(f'Map.{index}.Time', f'{date} {time}')
				utils.setprop(f'Map.{index}.Legend', '')
			else:
				for item in [ 'area', 'layer', 'heading', 'time', 'legend' ]:
					utils.setprop(f'Map.{index}.{item}', '')

			# Layers
			for idx in range(0, history):

				try:
					file = files[idx]
				except:
					utils.setprop(f'Map.{index}.Layer.{idx}', '')
					utils.setprop(f'Map.{index}.Time.{idx}', '')
				else:
					ut   = int(file.stem.split('_')[1])
					tz   = utils.dt('stamploc', ut)
					date = tz.strftime(config.kodi.date)
					time = tz.strftime(config.kodi.time)

					utils.setprop(f'Map.{index}.Layer.{idx}', f'{dir}/{layer}_{ut}.png')
					utils.setprop(f'Map.{index}.Time.{idx}', f'{date} {time}')

			index += 1

		# Locations
		utils.setprop('current.location', utils.setting(f'loc{config.loc.id}').split(',')[0])
		utils.setprop('location', utils.setting(f'loc{config.loc.id}'))
		self.setlocs()

		# Fetched
		for prop in [ 'current', 'weather', 'hourly', 'daily', 'map' ]:
			utils.setprop(f'{prop}.isfetched', 'true')

		# Other
		utils.setprop('alerts', config.addon.alerts)
		utils.setprop('addon.icons', config.addon.icons)
		utils.setprop('addon.iconsdir', config.addon_icons)
		utils.setprop('WeatherProvider', 'open-meteo.com, rainviewer.com, weather.gc.ca, met.no')
		utils.setprop('WeatherProviderLogo', f'{config.addon_path}/resources/banner.png')

	### NOTIFICATION
	def notification(self):
		queue    = config.addon.notify
		duration = int(utils.setting('alert_duration'))

		if queue:
			for alert in queue:
				utils.notification(alert[0], alert[1], alert[2], config.loc.id)
				utils.monitor.waitForAbort(duration)
				if utils.monitor.abortRequested():
					utils.log(f'Abort requested ...', 3)
					break

