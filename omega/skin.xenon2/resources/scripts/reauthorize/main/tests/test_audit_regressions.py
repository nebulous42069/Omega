"""Offline regression tests: no Kodi installation, network or real credentials."""
import ast
import importlib.util
import pathlib
import re
import sys
import types
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
MOD = ROOT / 'lib/reauthorize/modules'
DATA = {}


class Addon:
    def __init__(self, aid):
        self.aid = aid
        self.data = DATA.setdefault(aid, {})

    def getSetting(self, key):
        return self.data.get(key, '')

    def setSetting(self, key, value):
        self.data[key] = value


class Var:
    amgr = 'audit'
    crew_client = 'old-client'
    crew_secret = 'old-secret'
    client_am = 'shared-client'
    secret_am = 'shared-secret'

    def __getattr__(self, key):
        return key


control = types.ModuleType('reauthorize.modules.control')
control._wiping = False
control.wiping = lambda: control._wiping
control.set_wiping = lambda v: setattr(control, '_wiping', v)
control.setting = lambda k: DATA.get('script.module.reauthorize', {}).get(k, '')
control.setSetting = lambda k,v: Addon('script.module.reauthorize').setSetting(k,v)
control.notification = lambda **kw: None
sys.modules['xbmc'] = types.SimpleNamespace(log=lambda *a:None, LOGINFO=1, LOGERROR=3, executebuiltin=lambda *a:None)
sys.modules['xbmcaddon'] = types.SimpleNamespace(Addon=Addon)
sys.modules['xbmcvfs'] = types.SimpleNamespace(exists=lambda p:True, translatePath=lambda p:p)
pkg=types.ModuleType('reauthorize');pkg.__path__=[str(MOD.parent)]
sys.modules['reauthorize']=pkg
pkg=types.ModuleType('reauthorize.modules');pkg.__path__=[str(MOD)]
sys.modules['reauthorize.modules']=pkg
sys.modules['reauthorize.modules.control']=control
libs=types.ModuleType('libs');libs.__path__=[];sys.modules['libs']=libs
common=types.ModuleType('libs.common');common.var=Var();sys.modules['libs.common']=common
from reauthorize.modules import sync_support


def definitions(file, names=None, extra=None):
    tree=ast.parse((MOD/file).read_bytes())
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and (names is None or n.name in names)]
    env={'re':re,'var':Var()}
    env.update(extra or {})
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(file),'exec'),env)
    return env


def run_writer(filename, aid, source):
    tree=ast.parse((MOD/'sync'/filename).read_bytes())
    for node in ast.walk(tree):
        if not isinstance(node,ast.Try):
            continue
        body=ast.Module(body=node.body,type_ignores=[])
        ids={n.args[0].value for n in ast.walk(body) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='Addon' and n.args and isinstance(n.args[0],ast.Constant)}
        if ids=={aid}:
            env={'sync_support':sync_support,'xbmcaddon':sync_support.addon_api(sys.modules['xbmcaddon']),
                 'xbmcvfs':sys.modules['xbmcvfs'],'var':Var(),'control':control}
            env.update(source)
            exec(compile(body,filename,'exec'),env)
            return
    raise AssertionError('Missing target block '+aid)


class RegressionTests(unittest.TestCase):
    def setUp(self):
        DATA.clear();control._wiping=False;sync_support.begin()

    def test_metadata_preserves_unconfigured_services(self):
        DATA['plugin.video.umbrella']={'tmdb.apikey':'existing','tmdb.sessionid':'session'}
        tree=ast.parse((MOD/'sync/meta_sync.py').read_bytes())
        src={n.id:'' for n in ast.walk(tree) if isinstance(n,ast.Name) and n.id.startswith('your_')}
        src['your_fanart_api']='fanart'
        run_writer('meta_sync.py','plugin.video.umbrella',src)
        self.assertEqual(DATA['plugin.video.umbrella']['tmdb.apikey'],'existing')
        self.assertEqual(DATA['plugin.video.umbrella']['tmdb.sessionid'],'session')

    def test_explicit_metadata_wipe_clears(self):
        control._wiping=True;DATA['plugin.video.seren']={'fanart.apikey':'old'}
        run_writer('meta_sync.py','plugin.video.seren',{'your_fanart_api':'','your_omdb_api':'','your_tmdb_api':''})
        self.assertEqual(DATA['plugin.video.seren']['fanart.apikey'],'')

    def test_linksnappy_password_change(self):
        DATA['plugin.video.cosmos']={'ls_username':'user','ls_password':'old'}
        run_writer('linksnappy_sync.py','plugin.video.cosmos',{'your_username':'user','your_password':'new'})
        self.assertEqual(DATA['plugin.video.cosmos']['ls_password'],'new')

    def test_easynews_username_change(self):
        DATA['plugin.video.umbrella']={'easynews.password':'same','easynews.user':'old'}
        run_writer('easy_sync.py','plugin.video.umbrella',{'your_easy_user':'new','your_easy_pass':'same'})
        self.assertEqual(DATA['plugin.video.umbrella']['easynews.user'],'new')

    def test_filepursuit_consumer_key(self):
        run_writer('filepursuit_sync.py','plugin.video.umbrella',{'your_file_api':'new'})
        self.assertEqual(DATA['plugin.video.umbrella']['filepursuittoken'],'new')
        self.assertNotIn('filepursuit.api',DATA['plugin.video.umbrella'])

    def test_partial_rd_bundle_is_repaired(self):
        DATA['plugin.video.seren']={'rd.auth':'token','rd.refresh':'wrong'}
        self.assertTrue(sync_support.needs('plugin.video.seren',[('rd.auth','token'),('rd.refresh','right')]))

    def test_missing_enable_is_repaired(self):
        DATA['plugin.video.pov']={'rd.token':'token','rd.enabled':'false'}
        self.assertTrue(sync_support.needs('plugin.video.pov',[('rd.token','token')]))

    def test_supplemental_torbox_targets(self):
        DATA['script.module.reauthorize']={'torbox.token':'key'}
        sync_support.extra('torbox')
        self.assertEqual(DATA['script.module.resolveurl']['TorBoxResolver_apikey'],'key')
        self.assertEqual(DATA['plugin.video.seren']['torbox.token'],'key')

    def test_supplemental_offcloud(self):
        DATA['script.module.reauthorize']={'offcloud.token':'key'}
        sync_support.extra('offc')
        self.assertEqual(DATA['plugin.video.seren']['offcloud.apikey'],'key')

    def test_crew_xml_escape(self):
        env=definitions('sync/crew_trakt.py',['_set_in_xml'])
        text,_=env['_set_in_xml']('<settings><setting id="trakt.user">old</setting></settings>',{'trakt.user':'A & B'})
        self.assertEqual(ET.fromstring(text)[0].text,'A & B')

    def test_crew_marked_key_rotation_and_restore(self):
        env=definitions('sync/crew_trakt.py',['swap_key','restore_key'],{'MARK':'# ReAuthorize; was: ',
            '_KEY_LINE':re.compile(r'^(?P<name>CLIENT_ID|CLIENT_SECRET)(?P<eq>\s*=\s*)(?P<value>[^#\r\n]*?)(?P<tail>\s*(?:#.*)?)$',re.M),
            '_MARKED':re.compile(r'^(CLIENT_ID|CLIENT_SECRET)(\s*=\s*).*?\#\ ReAuthorize;\ was:\ (.+?)\s*$',re.M)})
        raw="CLIENT_ID = 'first'  # ReAuthorize; was: keys.trakt_id\nCLIENT_SECRET = 'first-secret'  # ReAuthorize; was: keys.trakt_secret\n"
        updated=env['swap_key'](raw,'second','second-secret')
        self.assertIn("'second'",updated)
        self.assertIn('CLIENT_ID = keys.trakt_id',env['restore_key'](updated))

    def test_crew_key_failure_stops_send(self):
        env=definitions('sync/crew_trakt.py',['link'],{'installed':lambda:True,'ensure_key':lambda:False})
        with self.assertRaises(RuntimeError):env['link']('user','token','refresh','1800000000')

    def test_helper_expiry_contract(self):
        tree=ast.parse((MOD/'sync/trakt_sync.py').read_bytes())
        assign=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='tmdbh_data' for t in n.targets))
        import json
        env={'json':json,'your_token':'a','your_refresh':'r','lifetime':604800,'your_expires_rnd':1800000000}
        exec(compile(ast.Module(body=[assign],type_ignores=[]),'expiry','exec'),env)
        data=json.loads(env['tmdbh_data'])
        self.assertEqual(data['created_at']+data['expires_in'],1800000000)

    def test_rd_failure_tuple_is_unpacked(self):
        tree=ast.parse((MOD/'auth/realdebrid.py').read_bytes())
        fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='auth')
        self.assertTrue(any(isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Tuple) for n in ast.walk(fn)))
        self.assertFalse(any(isinstance(n,ast.If) and isinstance(n.test,ast.Call) and isinstance(n.test.func,ast.Attribute) and n.test.func.attr=='get_token' for n in ast.walk(fn)))

    def test_otaku_action_not_written_as_token(self):
        self.assertNotIn('setSetting(\'simkl.login\'',(MOD/'sync/simkl_sync.py').read_text())

    def test_cancel_filepursuit_preserves_previous(self):
        env=definitions('auth/filepursuit.py',['Filepursuit'],{'xbmcgui':types.SimpleNamespace(Dialog=lambda:types.SimpleNamespace(input=lambda *a:'')), 'control':control})
        DATA['script.module.reauthorize']={'filepursuit.api.key':'old'}
        env['Filepursuit']().auth()
        self.assertEqual(DATA['script.module.reauthorize']['filepursuit.api.key'],'old')

    def test_source_key_patch_preserves_other_constants(self):
        with tempfile.TemporaryDirectory() as folder:
            p=pathlib.Path(folder)/'keys.py'
            p.write_text("CLIENT = 'old'\nOTHER = 'untouched'\n")
            sync_support.patch_constants(str(p),{'CLIENT':'new'})
            self.assertIn("OTHER = 'untouched'",p.read_text())
            sync_support.patch_constants(str(p),{'CLIENT':'newer'})
            self.assertIn("# ReAuthorize; was: 'old'",p.read_text())

    def test_unknown_source_layout_is_not_modified(self):
        with tempfile.TemporaryDirectory() as folder:
            p=pathlib.Path(folder)/'keys.py';p.write_text('OTHER = 1\n')
            with self.assertRaises(RuntimeError):sync_support.patch_constants(str(p),{'CLIENT':'new'})
            self.assertEqual(p.read_text(),'OTHER = 1\n')

    def test_removal_preserves_independent_accounts(self):
        import_map=types.ModuleType('reauthorize.modules.import_map')
        import_map.SETTINGS={'addon.one':{'credential':'realdebrid.token'},'addon.two':{'credential':'realdebrid.token'}}
        import_map.DATABASES={}
        sys.modules['reauthorize.modules.import_map']=import_map
        parent=sys.modules['reauthorize.modules'];old=getattr(parent,'import_map',None);parent.import_map=import_map
        DATA['addon.one']={'credential':'shared'};DATA['addon.two']={'credential':'independent'}
        try:sync_support.clear_matching({'realdebrid.token':'shared'},{'realdebrid.token'})
        finally:
            if old is not None:parent.import_map=old
            else:delattr(parent,'import_map')
        self.assertEqual(DATA['addon.one']['credential'],'')
        self.assertEqual(DATA['addon.two']['credential'],'independent')

    def test_inner_failure_is_returned_by_runner(self):
        env=definitions('sync_all.py',['_try'],{'_only_tags':(), '_wipe_tags':(),
            '_SERVICE_LABELS':{'rd':'Real-Debrid'},'control':control,'xbmc':sys.modules['xbmc']})
        before=sync_support.extra;sync_support.extra=lambda tag:None
        failed=[]
        try:env['_try']('rd',failed,lambda:sync_support.failed('dummy-addon'))
        finally:sync_support.extra=before
        self.assertEqual(failed,['Real-Debrid'])
        self.assertEqual(DATA['script.module.reauthorize']['sync.rd.service'],'')

    def test_youtube_capture_changes_issuing_keys_together(self):
        keys=('youtube.api.key','youtube.api.id','youtube.api.secret')
        DATA['script.module.reauthorize']={key:'old' for key in keys}
        DATA['plugin.video.youtube']={key:'new' for key in keys}
        env=definitions('sync/youtube_sync.py',['_capture_keys'],{'API_KEYS':keys,'YT_ADDON_ID':'plugin.video.youtube',
            'xbmcaddon':sys.modules['xbmcaddon'],'clean_value':lambda k,v:v,'_log':lambda *a:None})
        self.assertTrue(env['_capture_keys'](Addon('script.module.reauthorize')))
        self.assertEqual([DATA['script.module.reauthorize'][key] for key in keys],['new']*3)
        self.assertFalse(env['_capture_keys'](Addon('script.module.reauthorize')))

    def test_all_sources_parse(self):
        for p in ROOT.rglob('*.py'):
            ast.parse(p.read_bytes(),str(p))


if __name__=='__main__':
    unittest.main(verbosity=2)
