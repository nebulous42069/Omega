import sys
import os
from inspect import currentframe, getframeinfo
#tools.log(str(str('Line ')+str(getframeinfo(currentframe()).lineno)+'___'+str(getframeinfo(currentframe()).filename)))

folder = str(os.path.split(str(getframeinfo(currentframe()).filename))[0])
current_directory = folder
sys.path.append(current_directory)
sys.path.append(current_directory.replace('a4kscrapers_wrapper',''))

try:
	import getSources
	import real_debrid
	import tools
	import source_tools
	import get_meta
	from get_meta import get_episode_meta
	from get_meta import get_movie_meta
	from getSources import Sources
except:
	from a4kscrapers_wrapper import getSources
	from a4kscrapers_wrapper import real_debrid
	from a4kscrapers_wrapper import tools
	from a4kscrapers_wrapper import source_tools
	from a4kscrapers_wrapper import get_meta
	from a4kscrapers_wrapper.get_meta import get_episode_meta
	from a4kscrapers_wrapper.get_meta import get_movie_meta
	from a4kscrapers_wrapper.getSources import Sources

import sys

rd_api = real_debrid.RealDebrid()


program_choices = {
	'Search Torrent (episode) 				"main.py -search \'foundation\' -episode 1 -season 2 -interactive False"': 1 ,
	'Search Torrent (movie)				"main.py -search \'batman begins\' -year 2005"': 2,
	'Start downloader service (if not running)		"main.py -downloader -start"': 3,
	'manage downloader list				"main.py -downloader -status"': 4,
	'Setup Providers					"main.py -providers_setup"': 5,
	'enable_disable_providers				"main.py -providers_enable"': 6,
	#'setup_userdata_folder': 7,
	'rd_auth						"main.py -rd_auth"': 8,
	'auto_clean_caches (7 days)				"main.py -auto_clean -days 7"': 9,
	'default settings.xml					"main.py -default_settings"': 10,
	'setup filters/limits/sorting			"main.py -setup_settings"': 11,
	'get current filters/limits/sorting 			"main.py -curr_settings"': 12
}

def downloader_daemon():
	from a4kscrapers_wrapper import daemon
	magnet_list = tools.get_setting('magnet_list')
	download_path = tools.get_setting('download_path')
	with daemon.DaemonContext():
		getSources.run_downloader(magnet_list, download_path)


def main():
	#program_choices = tools.program_choices
	try: result = tools.selectFromDict(program_choices, 'CHOOSE')
	except KeyboardInterrupt: 
		print('\nEXIT')
		return

	if result == 1:
		getSources.run_tv_search()

	if result == 2:
		getSources.run_movie_search()

	if result == 3:
		magnet_list = tools.get_setting('magnet_list')
		download_path = tools.get_setting('download_path')
		getSources.run_downloader(magnet_list, download_path)

	if result == 4:
		magnet_list = tools.get_setting('magnet_list')
		download_path = tools.get_setting('download_path')
		lines = tools.read_all_text(magnet_list).split('\n')
		for line in lines:
			try: new_line = eval(line)
			except: continue
			print('CURR_PACK=%s,          CURR_LINE=%s,        CURR_FILE=%s' % (new_line['download_type'], new_line['file_name'], new_line['release_title']))
		print('Process_Lines')
		print('\n')
		try: 
			append_line = input('Modify Downloads Y?\n')
		except: 
			print('\n')
			append_line = 'N'
		if append_line.lower()[:1] == 'y':
			except_flag = False
			file1 = open(magnet_list, "w")
			file1.write("\n")
			file1.close()
			for line in lines:
				if except_flag == False:
					try: new_line = eval(line)
					except: continue
					print('CURR_PACK=%s,          CURR_LINE=%s,        CURR_FILE=%s' % (new_line['download_type'], new_line['file_name'], new_line['release_title']))
					try: 
						append_line = input('Delete Line From File:  Y?\n')
						if append_line.lower()[:1] == 'y':
							continue
						else:
							file1 = open(magnet_list, "a") 
							file1.write(str(line))
							file1.write("\n")
							file1.close()
					except:
						except_flag = True
						file1 = open(magnet_list, "a") 
						file1.write(str(line))
						file1.write("\n")
						file1.close()
				else:
					print('EXCEPTION_EXIT\n')
					file1 = open(magnet_list, "a") 
					file1.write(str(line))
					file1.write("\n")
					file1.close()

	if result == 5:
		tools.setup_userdata()
		getSources.setup_providers('https://bit.ly/a4kScrapers')
	if result == 6:
		tools.setup_userdata()
		getSources.enable_disable_providers()
	elif result == 7:
		tools.setup_userdata()
	elif result == 8:
		tools.setup_userdata()
		getSources.rd_auth()
	elif result == 9:
		tools.auto_clean_cache(days=7)
	elif result == 10:
		tools.setup_userdata()
		info = get_meta.blank_meta()
		tools.SourceSorter(info).default_sort_methods()
	elif result == 11:
		info = get_meta.blank_meta()
		tools.SourceSorter(info).set_sort_method_settings()
	elif result == 12:
		info = get_meta.blank_meta()
		tools.SourceSorter(info).get_sort_methods()


if __name__ == "__main__":
	print(sys.argv)
	if 'downloader' in str(sys.argv):
		downloader_daemon()
	else:
		main()
