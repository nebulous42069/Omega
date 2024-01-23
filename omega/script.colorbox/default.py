import os, sys, re
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
from functools import reduce
from threading import Thread
ADDON =             xbmcaddon.Addon()
ADDON_VERSION =     ADDON.getAddonInfo('version')
ADDON_LANGUAGE =    ADDON.getLocalizedString
ADDON_PATH =        ADDON.getAddonInfo('path')
ADDON_ID =          ADDON.getAddonInfo('id')
ADDON_DATA_PATH =   os.path.join(xbmcvfs.translatePath("special://profile/addon_data/%s" % ADDON_ID))
HOME =              xbmcgui.Window(10000)
from resources.lib import utils
ColorBox_settings_map = {
        'pixelsize':    utils.set_pixelsize,
        'bitsize':      utils.set_bitsize,
        'blursize':     utils.set_blursize,
        'black':        utils.set_black,
        'white':        utils.set_white,
        'lgint':        utils.set_lgint,
        'lgsteps':      utils.set_lgsteps,
        'comp':         utils.set_comp,
        'main':         utils.set_main,
        'desat':        utils.set_desat,
        'sharp':        utils.set_sharp,
        'blend':        utils.set_blend,
        'quality':      utils.set_quality}
ColorBox_strip =        ('[CR]', ' '), ('<BR>', ' '), ('<br>', ' '), ('&#10;', ' '), ('&&#10;', ' ')
#ColorBox_strip =       ('[B]', ''), ('[/B]', ''), ('[CR]', ' ')
class ColorBoxMain:
    def __init__(self):
        utils.log("version %s started" % ADDON_VERSION)
        self._init_vars()
        self._parse_argv()
        if not xbmcvfs.exists(ADDON_DATA_PATH):
            xbmcvfs.mkdir(ADDON_DATA_PATH)
        if self.control == "plugin":
            xbmcplugin.endOfDirectory(self.handle)
        utils.Load_Colors_Dict()
        monitor = xbmc.Monitor()
        while self.daemon and not monitor.abortRequested():
            utils.Show_Percentage()
            self.label_now_TWO = xbmc.getInfoLabel("Control.GetLabel(7972)")
            if (self.label_now_TWO != self.label_prev_TWO):
                self.label_prev_TWO = self.label_now_TWO
                HOME.setProperty('LabelFilterTWO', re.sub('\s+',' ',reduce(lambda CBX_a, CBX_kv: CBX_a.replace(*CBX_kv), ColorBox_strip, self.label_now_TWO).strip()))
            self.label_now_THREE = xbmc.getInfoLabel("Control.GetLabel(7973)")
            if (self.label_now_THREE != self.label_prev_THREE):
                self.label_prev_THREE = self.label_now_THREE
                HOME.setProperty('LabelFilterTHREE', re.sub('\s+',' ',reduce(lambda CBX_a, CBX_kv: CBX_a.replace(*CBX_kv), ColorBox_strip, self.label_now_THREE).strip()))
            self.label_now_FOUR = xbmc.getInfoLabel("Control.GetLabel(7974)")
            if (self.label_now_FOUR != self.label_prev_FOUR):
                self.label_prev_FOUR = self.label_now_FOUR
                HOME.setProperty('LabelFilterFOUR', re.sub('\s+',' ',reduce(lambda CBX_a, CBX_kv: CBX_a.replace(*CBX_kv), ColorBox_strip, self.label_now_FOUR).strip()))
            FIVE_daemon_set = HOME.getProperty("FIVE_daemon_set")
            if not FIVE_daemon_set == '':
                self.image_now_FIVE = xbmc.getInfoLabel("Control.GetLabel(7975)")
                if (self.image_now_FIVE != self.image_prev_FIVE and self.image_now_FIVE != "") or HOME.getProperty("FIVE_daemon_fire"):
                    HOME.setProperty('Daemon_FIVE_ImageUpdating', self.image_now_FIVE)
                    HOME.clearProperty("FIVE_daemon_fire")
                    #HOME.clearProperty("ImageFilterFIVE")
                    try:
                        HOME.setProperty('ImageFilterFIVE', utils.ColorBox_go_map(self.image_now_FIVE, FIVE_daemon_set))
                    except Exception as e:
                        utils.log("5err: %s img: %s" % (e,self.image_now_FIVE))
                    else:
                        self.image_prev_FIVE = self.image_now_FIVE
                        HOME.setProperty("OldImageColorFIVE", HOME.getProperty("ImageColorFIVE"))
                        HOME.setProperty("OldImageCColorFIVE", HOME.getProperty("ImageCColorFIVE"))
                        HOME.setProperty('ImageFIVE', self.image_now_FIVE)
                        tm1 = Thread(target=utils.Color_Only, args=(self.image_now_FIVE, "ImageColorFIVE", "ImageCColorFIVE"))
                        tm1.start()
                    HOME.setProperty('Daemon_FIVE_ImageUpdating', '')
            cfa_daemon_set = HOME.getProperty("cfa_daemon_set")
            #curr_window = xbmc.getInfoLabel("Window.Property(xmlfile)")
            if not cfa_daemon_set == '':
                self.image_now_cfa = xbmc.getInfoLabel("ListItem.Art(fanart)")
                if (self.image_now_cfa != self.image_prev_cfa and self.image_now_cfa != "") or HOME.getProperty("cfa_daemon_fire"):
                    HOME.setProperty('Daemon_cfa_ImageUpdating', self.image_now_cfa)
                    HOME.clearProperty("cfa_daemon_fire")
                    #HOME.clearProperty("ImageFiltercfa")
                    try:
                        HOME.setProperty('ImageFiltercfa', utils.ColorBox_go_map(self.image_now_cfa, cfa_daemon_set))
                    except Exception as e:
                        utils.log("cerr: %s img: %s" % (e,self.image_now_cfa))
                    else:
                        self.image_prev_cfa = self.image_now_cfa
                        HOME.setProperty("OldImageColorcfa", HOME.getProperty("ImageColorcfa"))
                        HOME.setProperty("OldImageCColorcfa", HOME.getProperty("ImageCColorcfa"))
                        tf = Thread(target=utils.Color_Only, args=(self.image_now_cfa, "ImageColorcfa", "ImageCColorcfa"))
                        tf.start()
                    HOME.setProperty('Daemon_cfa_ImageUpdating', '')
            SEVEN_daemon_set = HOME.getProperty("SEVEN_daemon_set")
            if not SEVEN_daemon_set == '':
                self.image_now_SEVEN = xbmc.getInfoLabel("Control.GetLabel(7977)")
                if self.image_now_SEVEN != self.image_prev_SEVEN and self.image_now_SEVEN != "":
                    try:
                        self.image_prev_SEVEN = self.image_now_SEVEN
                        HOME.setProperty("OldImageColorSEVEN", HOME.getProperty("ImageColorSEVEN"))
                        HOME.setProperty("OldImageCColorSEVEN", HOME.getProperty("ImageCColorSEVEN"))
                        tm3 = Thread(target=utils.Color_Only, args=(self.image_now_SEVEN, "ImageColorSEVEN", "ImageCColorSEVEN"))
                        tm3.start()
                    except Exception as e:
                        utils.log("7err: %s img: %s" % (e,self.image_now_SEVEN))
            EIGHT_daemon_set = HOME.getProperty("EIGHT_daemon_set")
            if not EIGHT_daemon_set == '':
                self.image_now_EIGHT = xbmc.getInfoLabel("Control.GetLabel(7978)")
                if (self.image_now_EIGHT != self.image_prev_EIGHT and self.image_now_EIGHT != "") or HOME.getProperty("EIGHT_daemon_fire"):
                    HOME.setProperty('Daemon_EIGHT_ImageUpdating', self.image_now_EIGHT)
                    HOME.clearProperty("EIGHT_daemon_fire")
                    #HOME.clearProperty("ImageFilterEIGHT")
                    try:
                        HOME.setProperty('ImageFilterEIGHT', utils.ColorBox_go_map(self.image_now_EIGHT, EIGHT_daemon_set))
                    except Exception as e:
                        utils.log("8err: %s img: %s" % (e,self.image_now_EIGHT))
                    else:
                        self.image_prev_EIGHT = self.image_now_EIGHT
                        HOME.setProperty("OldImageColorEIGHT", HOME.getProperty("ImageColorEIGHT"))
                        HOME.setProperty("OldImageCColorEIGHT", HOME.getProperty("ImageCColorEIGHT"))
                        HOME.setProperty('ImageEIGHT', self.image_now_EIGHT)
                        tm4 = Thread(target=utils.Color_Only, args=(self.image_now_EIGHT, "ImageColorEIGHT", "ImageCColorEIGHT"))
                        tm4.start()
                    HOME.setProperty('Daemon_EIGHT_ImageUpdating', '')
            self.manual_set_NINE = HOME.getProperty("NINE_manual_set")
            if (self.manual_set_NINE != '' and self.manual_set_NINE != self.prefix_prev_NINE) or HOME.getProperty("NINE_daemon_fire"):
                HOME.setProperty('Daemon_NINE_ImageUpdating', self.manual_set_NINE)
                try:
                    HOME.clearProperty("NINE_daemon_fire")
                    self.prefix_prev_NINE = self.manual_set_NINE
                    self.info = ""
                    self.id = ""
                    self.set = ""
                    self.var = ""
                    self.prefix = ""
                    for larg in self.manual_set_NINE.strip().split('|'):
                        for arg in larg.strip().split(','):
                            arg = arg.replace('"', "")
                            if arg.startswith('info='):
                                self.info = utils.Remove_Quotes(arg[5:])
                            elif arg.startswith('id='):
                                self.id = utils.Remove_Quotes(arg[3:])
                            elif arg.startswith('set='):
                                self.set = utils.Remove_Quotes(arg[4:])
                            elif arg.startswith('var='):
                                self.var = utils.Remove_Quotes(arg[4:])
                            elif arg.startswith('prefix='):
                                self.prefix = arg[7:]
                                if not self.prefix.endswith("."):
                                    self.prefix = self.prefix + "."
                        if self.info != "":
                            HOME.setProperty(self.prefix + 'ImageFilterNINE', utils.ColorBox_go_map(self.id, self.info))
                            HOME.setProperty(self.prefix + "ImageNINE", self.id)
                            imagecolor, cimagecolor = utils.Color_Only_Manual(self.id, self.prefix + "ImageColorNINE")
                            HOME.setProperty(self.prefix + "ImageColorNINE", imagecolor)
                            HOME.setProperty(self.prefix + "ImageCColorNINE", cimagecolor)
                        elif self.var != "":
                            ColorBox_settings_map[self.var](self.set)
                except Exception as e:
                    utils.log("9err: %s img: %s" % (e,self.manual_set_NINE))
                HOME.setProperty('Daemon_NINE_ImageUpdating', '')
            if self.ColorBox_multis != []:
                for line in self.ColorBox_multis:
                    self.wpnam, self.mfx, self.mqual = line.strip().split(':')
                    self.image_now_MULTI = xbmc.getInfoLabel("Control.GetLabel(" + str(self.idm) + ")")
                    if self.image_now_MULTI != HOME.getProperty(self.wpnam) and self.image_now_MULTI != "":
                        try:
                            HOME.setProperty(self.wpnam + "ImageFilter", utils.ColorBox_go_map(self.image_now_MULTI, self.mfx, self.mqual))
                        except Exception as e:
                            utils.log("merr: %s img: %s" % (e,self.ColorBox_multis))
                        else:
                            HOME.setProperty(self.wpnam + "Image", self.image_now_MULTI)
                            imagecolor, cimagecolor = utils.Color_Only_Manual(self.image_now_MULTI, self.wpnam + "ImageColor")
                            HOME.setProperty(self.wpnam + "ImageColor", imagecolor)
                            HOME.setProperty(self.wpnam + "ImageCColor", cimagecolor)
            monitor.waitForAbort(0.2)
    def _init_vars(self):
        HOME.setProperty("OldImageColorFIVE", "FFffffff")
        HOME.setProperty("ImageColorFIVE", "FFffffff")
        HOME.setProperty("OldImageCColorFIVE", "FFffffff")
        HOME.setProperty("ImageCColorFIVE", "FFffffff")
        HOME.setProperty("OldImageColorcfa", "FFffffff")
        HOME.setProperty("ImageColorcfa", "FFffffff")
        HOME.setProperty("OldImageCColorcfa", "FFffffff")
        HOME.setProperty("ImageCColorcfa", "FFffffff")
        HOME.setProperty("OldImageColorSEVEN", "FFffffff")
        HOME.setProperty("ImageColorSEVEN", "FFffffff")
        HOME.setProperty("OldImageColorEIGHT", "FFffffff")
        HOME.setProperty("ImageColorEIGHT", "FFffffff")
        HOME.setProperty("OldImageColorNINE", "FFffffff")
        HOME.setProperty("ImageColorNINE", "FFffffff")
        HOME.setProperty("OldImageCColorSEVEN", "FFffffff")
        HOME.setProperty("ImageCColorSEVEN", "FFffffff")
        HOME.setProperty("OldImageCColorEIGHT", "FFffffff")
        HOME.setProperty("ImageCColorEIGHT", "FFffffff")
        HOME.setProperty("OldImageCColorNINE", "FFffffff")
        HOME.setProperty("ImageCColorNINE", "FFffffff")
        self.window =           xbmcgui.Window(10000)
        self.control =          None
        self.id =               ""
        self.prefix =           ""
        self.daemon =           False
        self.show_watched =     ""
        self.label_now_TWO =    ""
        self.label_now_THREE =  ""
        self.label_now_FOUR =   ""
        self.image_now_FIVE =   ""
        self.image_now_cfa =    ""
        self.image_now_SEVEN =  ""
        self.image_now_EIGHT =  ""
        self.image_now_NINE =   ""
        self.label_prev_TWO =   ""
        self.label_prev_THREE = ""
        self.label_prev_FOUR =  ""
        self.image_prev_FIVE =  ""
        self.image_prev_cfa =   ""
        self.image_prev_SEVEN = ""
        self.image_prev_EIGHT = ""
        self.image_prev_NINE =  ""
        self.manual_set_NINE =  ""
        self.prefix_prev_NINE = ""
        self.autoclose =        ""
    def _parse_argv(self):
        args = sys.argv
        self.infos = []
        self.ColorBox_multis = []
        for arg in args:
            arg = arg.replace('"', "")
            if arg == 'script.colorbox':
                continue
            elif arg.startswith('multis='):
                self.multim = utils.Remove_Quotes(arg[7:])
                self.ColorBox_multis = self.multim.split("|")
            elif arg.startswith('daemon='):
                self.daemon = True
                utils.log("daemon started")
class ColorBoxMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
    def onPlayBackStarted(self):
        pass
if __name__ == "__main__":
    args =		sys.argv
    infom =		""
    idm =		""
    varm =		120
    prefixm	=	""
    for arg in args:
        arg = arg.replace('"', "")
        if arg == 'script.colorbox':
            continue
        elif arg.startswith('daemon='):
            ColorBoxMain()
        elif arg.startswith('info='):
            infom = utils.Remove_Quotes(arg[5:])
        elif arg.startswith('id='):
            idm = utils.Remove_Quotes(arg[3:])
        elif arg.startswith('var='):
            varm = utils.Remove_Quotes(arg[4:])
        elif arg.startswith('quality='):
            ColorBox_settings_map['quality'](utils.Remove_Quotes(arg[8:]))
        elif arg.startswith('blursize='):
            ColorBox_settings_map['blursize'](utils.Remove_Quotes(arg[9:]))
        elif arg.startswith('pixelsize='):
            ColorBox_settings_map['pixelsize'](utils.Remove_Quotes(arg[10:]))
        elif arg.startswith('bitsize='):
            ColorBox_settings_map['bitsize'](utils.Remove_Quotes(arg[8:]))
        elif arg.startswith('black='):
            ColorBox_settings_map['black'](utils.Remove_Quotes(arg[6:]))
        elif arg.startswith('white='):
            ColorBox_settings_map['white'](utils.Remove_Quotes(arg[6:]))
        elif arg.startswith('prefix='):
            prefixm = arg[7:]
            if not prefixm.endswith("."):
                prefixm = prefixm + "."
    if infom == 'randomcolor':
        HOME.setProperty(prefixm + "ImageColor", utils.Random_Color())
        HOME.setProperty(prefixm + "ImageCColor", utils.Complementary_Color(HOME.getProperty(prefixm + "ImageColor")))
    elif infom == 'shuffle' and idm != '':
        us1 = Thread(target=utils.Shuffle_Set, args=(idm,varm))
        us1.start()
    elif infom != "" and idm != "":
        HOME.setProperty(prefixm + "ImageFilter", utils.ColorBox_go_map(idm, infom))
        HOME.setProperty(prefixm + "Image", idm)
        imagecolor, cimagecolor = utils.Color_Only_Manual(idm, prefixm + "ImageColor")
        HOME.setProperty(prefixm + "ImageColor", imagecolor)
        HOME.setProperty(prefixm + "ImageCColor", cimagecolor)