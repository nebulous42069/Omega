# -*- coding: utf-8 -*-
"""
	ReAuthorize
"""

from reauthorize.modules.control import addonPath, addonVersion, joinPath

def _show(filename, heading):
	reauthorize_path = addonPath()
	helpFile = joinPath(reauthorize_path, 'lib', 'reauthorize', 'help', filename + '.txt')
	with open(helpFile, 'r', encoding='utf-8', errors='ignore') as f:
		text = f.read()
	_show_text(heading, text, reauthorize_path)

def _show_text(heading, text, reauthorize_path=None):
	from reauthorize.windows.textviewer import TextViewerXML
	if reauthorize_path is None:
		reauthorize_path = addonPath()
	w = TextViewerXML('textviewer.xml', reauthorize_path, heading=heading, text=text)
	w.run()
	del w

def get(file):
	_show(file, 'ReAuthorize v%s - %s' % (addonVersion(), file))

def get_readmefirst():
	_show('howto', 'ReAuthorize - Read Me First')

def get_howto(section=None):
	_show('howto', 'ReAuthorize v%s - How To Use ReAuthorize' % addonVersion())

def get_tmdb():
	_show('tmdbUser', 'ReAuthorize v%s - TMDb Login Help' % addonVersion())

def get_meta():
	_show('metaAuth', 'ReAuthorize v%s - Metadata API' % addonVersion())

def get_nondebrid():
	_show('nonDebrid', 'ReAuthorize v%s - OffCloud / Easynews / FilePursuit' % addonVersion())

def get_service_sync():
	_show('service_sync', 'ReAuthorize v%s - Auto-Sync Services' % addonVersion())

def get_custom():
	_show('custom_keys', 'ReAuthorize v%s - Custom Trakt API Keys' % addonVersion())

def get_restore():
	_show('restore', 'ReAuthorize v%s - Restore to Default' % addonVersion())

def get_readme():
	_show('readme', 'ReAuthorize v%s - Readme' % addonVersion())

def get_issues():
	_show('issues', 'ReAuthorize v%s - Reporting Issues' % addonVersion())

def compatible_text():
	"""
	The compatible add-ons, per service, built from Build Status' own list (addon_service_view), so it
	cannot fall behind the add-ons ReAuthorize really sends to. Until 1.4.0 this was a hand-kept file
	that still said v1.1.0 and listed retired add-ons.
	"""
	from reauthorize.modules import addon_service_view as view
	retired = {'plugin.video.salts', 'plugin.video.genesis', 'plugin.video.moria'}
	lines = ['The add-ons ReAuthorize sends your sign-ins to, by service.',
	         'Install any of them and it gets your sign-ins by itself.', '']
	for svc in view.get_service_definitions():
		names = sorted({view.get_addon_label(a) for a in view.SERVICE_ADDONS.get(svc['id'], []) if a not in retired},
		               key=lambda n: n.lower())
		if not names:
			continue
		lines += ['-' * 64, svc['label'].upper(), '-' * 64] + names + ['', '']
	return '\n'.join(lines)

def get_compatible():
	_show_text('ReAuthorize v%s - Compatible Add-ons' % addonVersion(), compatible_text())
