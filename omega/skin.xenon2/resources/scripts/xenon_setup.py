"""Single-file Xenon 2 wizard: source -> selection -> installation -> results.

Flow: links, add-ons, Debrid authorization, favorite, Home checklist, save menus, tracking, Finish.
"""
import json
import base64
import os
import re
import time
import sys
import shutil
import tempfile
import hashlib
import uuid
import xml.etree.ElementTree as ET

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

# Copy this single file into skin.xenon2/resources/scripts/.
# Launch: RunScript(special://skin/resources/scripts/xenon_setup.py)
# Kodi 21/22 test build. No companion add-on installation required.
# User choices and generated UI files stay in this Kodi profile.
PROFILE = xbmcvfs.translatePath('special://profile/addon_data/skin.xenon2.setup/')
ROOT = os.path.join(PROFILE, 'ui')
CATALOG = {
    "free": [
        {
            "id": "plugin.video.lookmovietomb",
            "name": "LookMovieTomb",
            "icon": "special://home/addons/resource.images.skinicons.wide/resources/icons/lookmovies.png"
        },
        {
            "id": "plugin.video.tmdbmovies",
            "name": "TMDB Movies",
            "icon": "special://home/addons/resource.images.skinicons.wide/resources/icons/tmdb.png"
        },
        {
            "id": "plugin.video.gratisred",
            "name": "Gratis Red",
            "icon": "special://home/addons/resource.images.skinicons.wide/resources/icons/gratisred.png"
        },
        {
            "id": "plugin.video.9movies",
            "name": "9 Movies",
            "icon": "special://home/addons/resource.images.skinicons.wide/resources/icons/9movies.png"
        },
        {
            "id": "plugin.video.vidscr",
            "name": "Vidscr",
            "icon": "special://home/addons/resource.images.skinicons.wide/resources/icons/vidscr.png"
        },
        {
            "id": "plugin.video.blacklodge",
            "name": "BlackLodge",
            "icon": "special://home/addons/resource.images.skinicons.wide/resources/icons/blacklodge.png"
        },
        {
            "id": "plugin.video.twisted",
            "name": "Twisted",
            "icon": "special://home/addons/resource.images.skinicons.wide/resources/icons/twisted.png"
        }
    ],
    "debrid": [

        {
            "id": "plugin.video.umbrella",
            "name": "Umbrella",
            "icon": "special://home/addons/resource.images.skinicons.wide/resources/icons/umbrella.png"
        },
        {
            "id": "plugin.video.redlight",
            "name": "Redlight",
            "icon": "special://home/addons/resource.images.skinicons.wide/resources/icons/redlight.png"
        },
        {
            "id": "plugin.video.seren",
            "name": "Seren",
            "icon": "special://home/addons/resource.images.skinicons.wide/resources/icons/seren.png"
        },
        {
            "id": "plugin.video.thecrew",
            "name": "The Crew",
            "icon": "special://home/addons/resource.images.skinicons.wide/resources/icons/crew.png"
        },
        {
            "id": "plugin.video.pov",
            "name": "POV",
            "icon": "special://home/addons/resource.images.skinicons.wide/resources/icons/pov.png"
        }       
    ]
}
# Custom service artwork paths. Falls back to ReAuthorize artwork, then a placeholder.
SERVICES = [
    {
        "name": "Real Debrid",
        "id": "realdebrid",
        "action": "realdebridAuth",
        "icon": "special://skin/media/setup/services/realdebrid.png"
    },
    {
        "name": "Premiumize",
        "id": "premiumize",
        "action": "premiumizeAuth",
        "icon": "special://skin/media/setup/services/premiumize.png"
    },
    {
        "name": "AllDebrid",
        "id": "alldebrid",
        "action": "alldebridAuth",
        "icon": "special://skin/media/setup/services/alldebrid.png"
    },
    {
        "name": "TorBox",
        "id": "torbox",
        "action": "torboxAuth",
        "icon": "special://skin/media/setup/services/torbox.png"
    },
    {
        "name": "Easy Debrid",
        "id": "easydebrid",
        "action": "easydebridAuth",
        "icon": "special://skin/media/setup/services/easydebrid.png"
    },
    {
        "name": "OffCloud",
        "id": "offcloud",
        "action": "offcloudAuth",
        "icon": "special://skin/media/setup/services/offcloud.png"
    },
    {
        "name": "Easynews",
        "id": "easynews",
        "action": "easynewsAuth",
        "icon": "special://skin/media/setup/services/easynews.png"
    },
    {
        "name": "FilePursuit",
        "id": "filepursuit",
        "action": "filepursuitAuth",
        "icon": "special://skin/media/setup/services/filepursuit.png"
    },
    {
        "name": "Linksnappy",
        "id": "linksnappy",
        "action": "linksnappyAuth",
        "icon": "special://skin/media/setup/services/linksnappy.png"
    },
    {
        "name": "Debrid-Link",
        "id": "debridlink",
        "action": "debridlinkAuth",
        "icon": "special://skin/media/setup/services/debridlink.png"
    }
]
# Each flavor is a complete read-only script.skinshortcuts folder.
# Labels within that flavor identify checklist entries; duplicate labels are grouped.
MENU_FILE = 'special://profile/addon_data/script.skinshortcuts/skin.xenon2-mainmenu.DATA.xml'
FLAVOR_ROOT = 'special://skin/resources/scripts/flavors/'
# Setup launcher entries are hidden after applying a flavor.
DISABLED_SETUP_LABELS = ['Xenon Setup', 'Xenon 2 Setup', 'Xenon2 Setup']
# Debrid favorite add-ons (Free favorites are configured separately below).
FLAVORS = [
    {
        "id": "tmdbhelper",
        "name": "The Movie Database Helper",
        "addon": "plugin.video.themoviedb.helper",
        "folder": "tmdbhelper",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/icons/tmdbh.png",
        "always_labels": [
            "1036",
            "24001",
            "Diggz Xenon"
        ]
    },
    {
        "id": "redlight",
        "name": "Red Light",
        "addon": "plugin.video.redlight",
        "folder": "redlight",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/icons/fenlight.png",
        "always_labels": [
            "1036",
            "24001",
            "Diggz Xenon"
        ]
    },
    {
        "id": "umbrella",
        "name": "Umbrella",
        "addon": "plugin.video.umbrella",
        "folder": "umbrella",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/umbrella.png",
        "always_labels": [
            "1036",
            "24001",
            "Diggz Xenon"
        ]
    }
]
# Free profiles skip Debrid authorization. Tracking authorization remains shared.
FREE_FLAVORS = [
    {
        "id": "xenonfree",
        "name": "Xenon Free",
        "addon": "",
        "folder": "xenonfree",
        "icon": "special://home/addons/resource.images.skinicons.wide/resources/free.png",
        "always_labels": [
            "1036",
            "24001",
            "Diggz Xenon"
        ]
    }
]

TRACKING_SERVICES = [
    {
        "id": "trakt",
        "name": "Trakt",
        "action": "traktAuth",
        "icon": "special://skin/media/setup/tracking/trakt.png"
    },
    {
        "id": "simkl",
        "name": "Simkl",
        "action": "simklAuth",
        "icon": "special://skin/media/setup/tracking/simkl.png"
    },
    {
        "id": "mdblist",
        "name": "MDBList",
        "action": "mdblistOAuthAuth",
        "icon": "special://skin/media/setup/tracking/mdblist.png"
    }
]
LAYOUT = '<window>\n  <defaultcontrol always="true">100</defaultcontrol>\n  <coordinates />\n  <controls>\n    <control type="image">\n      <left>0</left>\n      <top>0</top>\n      <width>1920</width>\n      <height>1080</height>\n      <texture>panel.png</texture>\n    </control>\n    <control type="image">\n      <left>0</left>\n      <top>0</top>\n      <width>1920</width>\n      <height>1080</height>\n      <texture colordiffuse="__THEME__">circuit.png</texture>\n    </control>\n    <control type="image">\n      <left>180</left>\n      <top>175</top>\n      <width>1560</width>\n      <height>6</height>\n      <texture colordiffuse="__THEME__">accent.png</texture>\n    </control>\n    <control type="label" id="10">\n      <left>180</left>\n      <top>83</top>\n      <width>1560</width>\n      <height>82</height>\n      <font>font_MainMenu</font>\n      <textcolor>__THEME__</textcolor>\n      <wrapmultiline>true</wrapmultiline>\n      <label />\n      <align>center</align>\n      <aligny>center</aligny>\n    </control>\n    <control type="label" id="11">\n      <left>180</left>\n      <top>205</top>\n      <width>1560</width>\n      <height>65</height>\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <wrapmultiline>true</wrapmultiline>\n      <label />\n    </control>\n    <control type="label" id="12">\n      <left>180</left>\n      <top>290</top>\n      <width>1560</width>\n      <height>90</height>\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <wrapmultiline>true</wrapmultiline>\n      <label />\n    </control>\n    <control type="button" id="100">\n      <left>180</left>\n      <top>420</top>\n      <width>750</width>\n      <height>88</height>\n      <label>FREE</label>\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <disabledcolor>FF777777</disabledcolor>\n      <aligny>center</aligny>\n      <textoffsetx>25</textoffsetx>\n      <texturefocus colordiffuse="__THEME__">focus.png</texturefocus>\n      <texturenofocus>button.png</texturenofocus>\n      <onup>301</onup>\n      <ondown>301</ondown>\n      <onleft>101</onleft>\n      <onright>101</onright>\n    </control>\n    <control type="button" id="101">\n      <left>990</left>\n      <top>420</top>\n      <width>750</width>\n      <height>88</height>\n      <label>Debrid</label>\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <disabledcolor>FF777777</disabledcolor>\n      <aligny>center</aligny>\n      <textoffsetx>25</textoffsetx>\n      <texturefocus colordiffuse="__THEME__">focus.png</texturefocus>\n      <texturenofocus>button.png</texturenofocus>\n      <onup>301</onup>\n      <ondown>301</ondown>\n      <onleft>100</onleft>\n      <onright>100</onright>\n    </control>\n    <control type="radiobutton" id="200">\n      <left>330</left>\n      <top>400</top>\n      <width>900</width>\n      <height>88</height>\n      <label />\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <disabledcolor>FF777777</disabledcolor>\n      <aligny>center</aligny>\n      <textoffsetx>25</textoffsetx>\n      <texturefocus colordiffuse="__THEME__">focus.png</texturefocus>\n      <texturenofocus>button.png</texturenofocus>\n      <onup>301</onup>\n      <ondown>201</ondown>\n      <onleft>600</onleft>\n      <onright>301</onright>\n      <radiowidth>44</radiowidth>\n      <radioheight>44</radioheight>\n      <radioposx>825</radioposx>\n      <radioposy>22</radioposy>\n      <textureradioonfocus>checked.png</textureradioonfocus>\n      <textureradioonnofocus>checked.png</textureradioonnofocus>\n      <textureradioofffocus>unchecked.png</textureradioofffocus>\n      <textureradiooffnofocus>unchecked.png</textureradiooffnofocus>\n    </control>\n    <control type="radiobutton" id="201">\n      <left>330</left>\n      <top>515</top>\n      <width>900</width>\n      <height>88</height>\n      <label />\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <disabledcolor>FF777777</disabledcolor>\n      <aligny>center</aligny>\n      <textoffsetx>25</textoffsetx>\n      <texturefocus colordiffuse="__THEME__">focus.png</texturefocus>\n      <texturenofocus>button.png</texturenofocus>\n      <onup>200</onup>\n      <ondown>202</ondown>\n      <onleft>600</onleft>\n      <onright>301</onright>\n      <radiowidth>44</radiowidth>\n      <radioheight>44</radioheight>\n      <radioposx>825</radioposx>\n      <radioposy>22</radioposy>\n      <textureradioonfocus>checked.png</textureradioonfocus>\n      <textureradioonnofocus>checked.png</textureradioonnofocus>\n      <textureradioofffocus>unchecked.png</textureradioofffocus>\n      <textureradiooffnofocus>unchecked.png</textureradiooffnofocus>\n    </control>\n    <control type="radiobutton" id="202">\n      <left>330</left>\n      <top>630</top>\n      <width>900</width>\n      <height>88</height>\n      <label />\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <disabledcolor>FF777777</disabledcolor>\n      <aligny>center</aligny>\n      <textoffsetx>25</textoffsetx>\n      <texturefocus colordiffuse="__THEME__">focus.png</texturefocus>\n      <texturenofocus>button.png</texturenofocus>\n      <onup>201</onup>\n      <ondown>301</ondown>\n      <onleft>600</onleft>\n      <onright>301</onright>\n      <radiowidth>44</radiowidth>\n      <radioheight>44</radioheight>\n      <radioposx>825</radioposx>\n      <radioposy>22</radioposy>\n      <textureradioonfocus>checked.png</textureradioonfocus>\n      <textureradioonnofocus>checked.png</textureradioonnofocus>\n      <textureradioofffocus>unchecked.png</textureradioofffocus>\n      <textureradiooffnofocus>unchecked.png</textureradiooffnofocus>\n    </control>\n    <control type="button" id="300">\n      <left>670</left>\n      <top>830</top>\n      <width>1070</width>\n      <height>88</height>\n      <label>Install (0) add-ons</label>\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <disabledcolor>FF777777</disabledcolor>\n      <aligny>center</aligny>\n      <textoffsetx>25</textoffsetx>\n      <texturefocus colordiffuse="__THEME__">focus.png</texturefocus>\n      <texturenofocus>button.png</texturenofocus>\n      <onup>202</onup>\n      <ondown>200</ondown>\n      <onleft>301</onleft>\n      <onright>301</onright>\n    </control>\n    <control type="button" id="301">\n      <left>180</left>\n      <top>830</top>\n      <width>460</width>\n      <height>88</height>\n      <label>Back</label>\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <disabledcolor>FF777777</disabledcolor>\n      <aligny>center</aligny>\n      <textoffsetx>25</textoffsetx>\n      <texturefocus colordiffuse="__THEME__">focus.png</texturefocus>\n      <texturenofocus>button.png</texturenofocus>\n      <onup>202</onup>\n      <ondown>200</ondown>\n      <onleft>300</onleft>\n      <onright>306</onright>\n    </control>\n    <control type="image" id="400">\n      <left>1335</left>\n      <top>415</top>\n      <width>340</width>\n      <height>290</height>\n      <texture>$INFO[Container(750).ListItem.Property(addon_icon)]</texture>\n      <aspectratio>keep</aspectratio>\n    </control>\n    <control type="label" id="401">\n      <left>1290</left>\n      <top>720</top>\n      <width>430</width>\n      <height>55</height>\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <align>center</align>\n      <label>$INFO[Container(750).ListItem.Label]</label>\n    </control>\n    <control type="label" id="500">\n      <left>920</left>\n      <top>422</top>\n      <width>200</width>\n      <height>44</height>\n      <font>font13</font>\n      <textcolor>__THEME__</textcolor>\n      <align>center</align>\n      <aligny>center</aligny>\n      <label>Installed</label>\n    </control>\n    <control type="label" id="501">\n      <left>920</left>\n      <top>537</top>\n      <width>200</width>\n      <height>44</height>\n      <font>font13</font>\n      <textcolor>__THEME__</textcolor>\n      <align>center</align>\n      <aligny>center</aligny>\n      <label>Installed</label>\n    </control>\n    <control type="label" id="502">\n      <left>920</left>\n      <top>652</top>\n      <width>200</width>\n      <height>44</height>\n      <font>font13</font>\n      <textcolor>__THEME__</textcolor>\n      <align>center</align>\n      <aligny>center</aligny>\n      <label>Installed</label>\n    </control>\n    <control type="button" id="600">\n      <left>180</left>\n      <top>455</top>\n      <width>110</width>\n      <height>110</height>\n      <label />\n      <texturefocus colordiffuse="__THEME__">focus.png</texturefocus>\n      <texturenofocus>button.png</texturenofocus>\n      <onup>601</onup>\n      <ondown>601</ondown>\n      <onleft>301</onleft>\n      <onright>200</onright>\n    </control>\n    <control type="image" id="602">\n      <left>195</left>\n      <top>470</top>\n      <width>80</width>\n      <height>80</height>\n      <texture>arrow_up.png</texture>\n    </control>\n    <control type="button" id="601">\n      <left>180</left>\n      <top>590</top>\n      <width>110</width>\n      <height>110</height>\n      <label />\n      <texturefocus colordiffuse="__THEME__">focus.png</texturefocus>\n      <texturenofocus>button.png</texturenofocus>\n      <onup>600</onup>\n      <ondown>600</ondown>\n      <onleft>301</onleft>\n      <onright>200</onright>\n    </control>\n    <control type="image" id="603">\n      <left>195</left>\n      <top>605</top>\n      <width>80</width>\n      <height>80</height>\n      <texture>arrow_down.png</texture>\n    </control>\n    <control type="button" id="303">\n      <left>1280</left>\n      <top>830</top>\n      <width>460</width>\n      <height>88</height>\n      <label>Authorize Debrid</label>\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <aligny>center</aligny>\n      <textoffsetx>20</textoffsetx>\n      <texturefocus colordiffuse="__THEME__">focus.png</texturefocus>\n      <texturenofocus>button.png</texturenofocus>\n      <onup>202</onup>\n      <ondown>200</ondown>\n      <onleft>300</onleft>\n      <onright>301</onright>\n    </control>\n    <control type="button" id="304">\n      <left>1260</left>\n      <top>830</top>\n      <width>480</width>\n      <height>88</height>\n      <label>Finish</label>\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <aligny>center</aligny>\n      <textoffsetx>20</textoffsetx>\n      <texturefocus colordiffuse="__THEME__">focus.png</texturefocus>\n      <texturenofocus>button.png</texturenofocus>\n      <onup>700</onup>\n      <ondown>700</ondown>\n      <onleft>306</onleft>\n      <onright>301</onright>\n    </control>\n    <control type="list" id="700">\n      <left>330</left>\n      <top>400</top>\n      <width>900</width>\n      <height>345</height>\n      <onup>301</onup>\n      <ondown>306</ondown>\n      <onleft>600</onleft>\n      <onright>304</onright>\n      <scrolltime>150</scrolltime>\n      <itemlayout height="115" width="900">\n        <control type="image">\n          <left>0</left>\n          <top>0</top>\n          <width>900</width>\n          <height>88</height>\n          <texture>button.png</texture>\n        </control>\n        <control type="label">\n          <left>25</left>\n          <top>0</top>\n          <width>565</width>\n          <height>88</height>\n          <font>font13</font>\n          <textcolor>FFFFFFFF</textcolor>\n          <aligny>center</aligny>\n          <label>$INFO[ListItem.Label]</label>\n        </control>\n      <control type="image"><left>590</left><top>22</top><width>300</width><height>44</height><texture colordiffuse="FF247A45">button.png</texture><visible>String.IsEqual(ListItem.Property(authorized),true)</visible></control><control type="image"><left>590</left><top>22</top><width>300</width><height>44</height><texture colordiffuse="FF803B3B">button.png</texture><visible>String.IsEqual(ListItem.Property(authorized),false)</visible></control><control type="label"><left>600</left><top>0</top><width>280</width><height>88</height><font>font12</font><align>right</align><aligny>center</aligny><textcolor>FFFFFFFF</textcolor><label>$INFO[ListItem.Property(auth_status)]</label></control></itemlayout>\n      <focusedlayout height="115" width="900">\n        <control type="image">\n          <left>0</left>\n          <top>0</top>\n          <width>900</width>\n          <height>88</height>\n          <texture colordiffuse="__THEME__">focus.png</texture>\n        </control>\n        <control type="label">\n          <left>25</left>\n          <top>0</top>\n          <width>565</width>\n          <height>88</height>\n          <font>font13</font>\n          <textcolor>FFFFFFFF</textcolor>\n          <aligny>center</aligny>\n          <label>$INFO[ListItem.Label]</label>\n        </control>\n      <control type="image"><left>590</left><top>22</top><width>300</width><height>44</height><texture colordiffuse="FF247A45">button.png</texture><visible>String.IsEqual(ListItem.Property(authorized),true)</visible></control><control type="image"><left>590</left><top>22</top><width>300</width><height>44</height><texture colordiffuse="FF803B3B">button.png</texture><visible>String.IsEqual(ListItem.Property(authorized),false)</visible></control><control type="label"><left>600</left><top>0</top><width>280</width><height>88</height><font>font12</font><align>right</align><aligny>center</aligny><textcolor>FFFFFFFF</textcolor><label>$INFO[ListItem.Property(auth_status)]</label></control></focusedlayout>\n    </control>\n    <control type="image" id="710">\n      <left>1335</left>\n      <top>415</top>\n      <width>340</width>\n      <height>290</height>\n      <texture>$INFO[Container(700).ListItem.Property(service_icon)]</texture>\n      <aspectratio>keep</aspectratio>\n    </control>\n    <control type="label" id="711">\n      <left>1290</left>\n      <top>720</top>\n      <width>430</width>\n      <height>55</height>\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <align>center</align>\n      <label>$INFO[Container(700).ListItem.Label]</label>\n    </control>\n    <control type="button" id="305">\n      <left>1280</left>\n      <top>830</top>\n      <width>460</width>\n      <height>88</height>\n      <label>Select Flavor</label>\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <aligny>center</aligny>\n      <textoffsetx>20</textoffsetx>\n      <texturefocus colordiffuse="__THEME__">focus.png</texturefocus>\n      <texturenofocus>button.png</texturenofocus>\n      <onup>202</onup>\n      <ondown>200</ondown>\n      <onleft>300</onleft>\n      <onright>301</onright>\n    </control>\n    <control type="list" id="720">\n      <left>330</left>\n      <top>400</top>\n      <width>900</width>\n      <height>345</height>\n      <onup>301</onup>\n      <ondown>304</ondown>\n      <onleft>600</onleft>\n      <onright>304</onright>\n      <scrolltime>150</scrolltime>\n      <itemlayout height="115" width="900">\n        <control type="image">\n          <left>0</left>\n          <top>0</top>\n          <width>900</width>\n          <height>88</height>\n          <texture>button.png</texture>\n        </control>\n        <control type="label">\n          <left>25</left>\n          <top>0</top>\n          <width>850</width>\n          <height>88</height>\n          <font>font13</font>\n          <textcolor>FFFFFFFF</textcolor>\n          <aligny>center</aligny>\n          <label>$INFO[ListItem.Label]</label>\n        </control>\n      </itemlayout>\n      <focusedlayout height="115" width="900">\n        <control type="image">\n          <left>0</left>\n          <top>0</top>\n          <width>900</width>\n          <height>88</height>\n          <texture colordiffuse="__THEME__">focus.png</texture>\n        </control>\n        <control type="label">\n          <left>25</left>\n          <top>0</top>\n          <width>850</width>\n          <height>88</height>\n          <font>font13</font>\n          <textcolor>FFFFFFFF</textcolor>\n          <aligny>center</aligny>\n          <label>$INFO[ListItem.Label]</label>\n        </control>\n      </focusedlayout>\n    </control>\n    <control type="image" id="721">\n      <left>1335</left>\n      <top>415</top>\n      <width>340</width>\n      <height>290</height>\n      <texture>$INFO[Container(720).ListItem.Property(flavor_icon)]</texture>\n      <aspectratio>keep</aspectratio>\n    </control>\n    <control type="label" id="722">\n      <left>1290</left>\n      <top>720</top>\n      <width>430</width>\n      <height>55</height>\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <align>center</align>\n      <label>$INFO[Container(720).ListItem.Label]</label>\n    </control>\n    <control type="list" id="740">\n      <left>330</left>\n      <top>400</top>\n      <width>900</width>\n      <height>345</height>\n      <onup>301</onup>\n      <ondown>304</ondown>\n      <onleft>600</onleft>\n      <onright>304</onright>\n      <scrolltime>150</scrolltime>\n      <itemlayout height="115" width="900">\n        <control type="image">\n          <left>0</left>\n          <top>0</top>\n          <width>900</width>\n          <height>88</height>\n          <texture>button.png</texture>\n        </control>\n        <control type="label">\n          <left>25</left>\n          <top>0</top>\n          <width>740</width>\n          <height>88</height>\n          <font>font13</font>\n          <textcolor>FFFFFFFF</textcolor>\n          <aligny>center</aligny>\n          <label>$INFO[ListItem.Label]</label>\n          <focusedcolor>FFFFFFFF</focusedcolor>\n          <disabledcolor>FF888888</disabledcolor>\n        </control>\n        <control type="image">\n          <left>825</left>\n          <top>22</top>\n          <width>44</width>\n          <height>44</height>\n          <texture>checked.png</texture>\n          <visible>String.IsEqual(ListItem.Property(checked),true)</visible>\n        </control>\n        <control type="image">\n          <left>825</left>\n          <top>22</top>\n          <width>44</width>\n          <height>44</height>\n          <texture>unchecked.png</texture>\n          <visible>!String.IsEqual(ListItem.Property(checked),true)</visible>\n        </control>\n      </itemlayout>\n      <focusedlayout height="115" width="900">\n        <control type="image">\n          <left>0</left>\n          <top>0</top>\n          <width>900</width>\n          <height>88</height>\n          <texture>button.png</texture>\n        </control>\n        <control type="image">\n          <left>0</left>\n          <top>0</top>\n          <width>900</width>\n          <height>88</height>\n          <texture colordiffuse="__THEME__">focus.png</texture>\n          <visible>Control.HasFocus(740)</visible>\n        </control>\n        <control type="label">\n          <left>25</left>\n          <top>0</top>\n          <width>740</width>\n          <height>88</height>\n          <font>font13</font>\n          <textcolor>FFFFFFFF</textcolor>\n          <aligny>center</aligny>\n          <label>$INFO[ListItem.Label]</label>\n          <focusedcolor>FFFFFFFF</focusedcolor>\n          <disabledcolor>FF888888</disabledcolor>\n        </control>\n        <control type="image">\n          <left>825</left>\n          <top>22</top>\n          <width>44</width>\n          <height>44</height>\n          <texture>checked.png</texture>\n          <visible>String.IsEqual(ListItem.Property(checked),true)</visible>\n        </control>\n        <control type="image">\n          <left>825</left>\n          <top>22</top>\n          <width>44</width>\n          <height>44</height>\n          <texture>unchecked.png</texture>\n          <visible>!String.IsEqual(ListItem.Property(checked),true)</visible>\n        </control>\n      </focusedlayout>\n    </control>\n    <control type="image" id="741">\n      <left>1335</left>\n      <top>415</top>\n      <width>340</width>\n      <height>290</height>\n      <texture>$INFO[Container(740).ListItem.Property(menu_icon)]</texture>\n      <aspectratio>keep</aspectratio>\n    </control>\n    <control type="label" id="742">\n      <left>1290</left>\n      <top>720</top>\n      <width>430</width>\n      <height>55</height>\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <align>center</align>\n      <label>$INFO[Container(740).ListItem.Label]</label>\n    </control>\n  <control type="button" id="306">\n      <left>720</left>\n      <top>830</top>\n      <width>460</width>\n      <height>88</height>\n      <label>View Status</label>\n      <font>font13</font>\n      <textcolor>FFFFFFFF</textcolor>\n      <disabledcolor>FF777777</disabledcolor>\n      <aligny>center</aligny>\n      <textoffsetx>25</textoffsetx>\n      <texturefocus colordiffuse="__THEME__">focus.png</texturefocus>\n      <texturenofocus>button.png</texturenofocus>\n      <onup>700</onup>\n      <ondown>700</ondown>\n      <onleft>301</onleft>\n      <onright>304</onright>\n    </control>\n    <control type="list" id="750">\n      <left>330</left>\n      <top>400</top>\n      <width>900</width>\n      <height>345</height>\n      <onup>301</onup>\n      <ondown>300</ondown>\n      <onleft>600</onleft>\n      <onright>300</onright>\n      <scrolltime>150</scrolltime>\n      <itemlayout height="115" width="900">\n        <control type="image">\n          <left>0</left>\n          <top>0</top>\n          <width>900</width>\n          <height>88</height>\n          <texture>button.png</texture>\n        </control>\n        <control type="label">\n          <left>25</left>\n          <top>0</top>\n          <width>595</width>\n          <height>88</height>\n          <font>font13</font>\n          <textcolor>FFFFFFFF</textcolor>\n          <aligny>center</aligny>\n          <label>$INFO[ListItem.Label]</label>\n          <focusedcolor>FFFFFFFF</focusedcolor>\n          <disabledcolor>FF888888</disabledcolor>\n        </control>\n        <control type="image">\n          <left>825</left>\n          <top>22</top>\n          <width>44</width>\n          <height>44</height>\n          <texture>checked.png</texture>\n          <visible>String.IsEqual(ListItem.Property(checked),true)</visible>\n        </control>\n        <control type="image">\n          <left>825</left>\n          <top>22</top>\n          <width>44</width>\n          <height>44</height>\n          <texture>unchecked.png</texture>\n          <visible>!String.IsEqual(ListItem.Property(checked),true)</visible>\n        </control>\n      <control type="label"><left>625</left><top>0</top><width>180</width><height>88</height><font>font13</font><textcolor>FFFFFFFF</textcolor><align>right</align><aligny>center</aligny><label>Installed</label><visible>String.IsEqual(ListItem.Property(installed),true)</visible></control></itemlayout>\n      <focusedlayout height="115" width="900">\n        <control type="image">\n          <left>0</left>\n          <top>0</top>\n          <width>900</width>\n          <height>88</height>\n          <texture>button.png</texture>\n        </control>\n        <control type="image">\n          <left>0</left>\n          <top>0</top>\n          <width>900</width>\n          <height>88</height>\n          <texture colordiffuse="__THEME__">focus.png</texture>\n          <visible>Control.HasFocus(750)</visible>\n        </control>\n        <control type="label">\n          <left>25</left>\n          <top>0</top>\n          <width>595</width>\n          <height>88</height>\n          <font>font13</font>\n          <textcolor>FFFFFFFF</textcolor>\n          <aligny>center</aligny>\n          <label>$INFO[ListItem.Label]</label>\n          <focusedcolor>FFFFFFFF</focusedcolor>\n          <disabledcolor>FF888888</disabledcolor>\n        </control>\n        <control type="image">\n          <left>825</left>\n          <top>22</top>\n          <width>44</width>\n          <height>44</height>\n          <texture>checked.png</texture>\n          <visible>String.IsEqual(ListItem.Property(checked),true)</visible>\n        </control>\n        <control type="image">\n          <left>825</left>\n          <top>22</top>\n          <width>44</width>\n          <height>44</height>\n          <texture>unchecked.png</texture>\n          <visible>!String.IsEqual(ListItem.Property(checked),true)</visible>\n        </control>\n      <control type="label"><left>625</left><top>0</top><width>180</width><height>88</height><font>font13</font><textcolor>FFFFFFFF</textcolor><align>right</align><aligny>center</aligny><label>Installed</label><visible>String.IsEqual(ListItem.Property(installed),true)</visible></control></focusedlayout>\n    </control>\n    </controls>\n</window>'
TEXTURES = {'panel.png': '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', 'button.png': 'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAEklEQVR4nGNQ0rb8jw8zjAwFANRHYUGGq8KiAAAAAElFTkSuQmCC', 'check.png': 'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAE0lEQVR4nGN4u8vpPz7MMDIUAAD22boBX8tOXAAAAABJRU5ErkJggg==', 'focus.png': 'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAFklEQVR4nGP8//9/MQMewIRPcvgoAACNLwOAJ4iGvwAAAABJRU5ErkJggg==', 'accent.png': 'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAFklEQVR4nGP8////fwY8gAmf5PBRAAAbbgQMid1tCwAAAABJRU5ErkJggg==', 'unchecked.png': 'iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAACJ0lEQVR4nO3XMU7jUBRA0c9ULCA9I1Gw/+VQIEGfBdAx7TQTf8eOk9E9pyUykd/97ytjAAAAABVPt3jo1/n75xbPZYyX0/OuM9vtYYZ+vD1i2PwAg7+/LSH82vKPDf8xbJnDVeUY/ONauw1WbwDDf2xr57PpCuD/t2pdzNb19vr7fN3XYcn7x+dp5nOzV8F0ADPDN/jjzIQwE8FuV4DhH2uv9z0VwNLpN/z7WHrvM1t78wYw/Pva+v79CohbDODSGnH6H8OlOSxdAzZAnADiBBAngDgBxAkgTgBxAogTQJwA4gQQJ4A4AcQJIE4AcQKIE0CcAOIEECeAOAHECSBOAHECiBNAnADiBBAngDgBxAkgTgBxAogTQJwA4gQQJ4A4AcQJIE4AcQKIE0CcAOIEECeAOAHECSBOAHECiBNAnADiBBAngDgBxAkgTgBxAogTQJwA4gQQJ4A4AcQJIE4AcQKIE0CcAOIEECeAOAHECSBOAHECiBNAnADiBBAngDgBxAkgTgBxAogTQJwA4gQQJ4A4AcQJIG4xgJfT89O//vb+8Xna9+twjUtzuDS/MWyAvM0B2AL3tfX9TwWwtEZEcB9L731pbmPseAWI4Fh7ve/FQv72df7+mfnc2+vv83VfhyWzg585/WOsDGCM+Qi4n9nhj+FXQN7qANbUxfHWzmfTMF0Hj+Pag7npCrANHsOWOew2QNvgeHscwJucYDHcjq0LAADABn8AIlp42C+KGmsAAAAASUVORK5CYII=', 'checked.png': 'iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAADjUlEQVR4nO2cvW4bMRAGPwcpnC6FmlQ24MLv/zguDNhVGhXp4s4pDMHxn0geyd3l7Uxr4SRwhqTuTmcJAAAAAAAAALJwMeOgj8en5xnHBenqcDnU2bCDId2eETF0HwDx/vSE8K3njZEfgx4Pm8pBfFxaV4PmFQD5sWn107UFwPo0LRe1dd3eXB+3fRwocXf/cKh5Xe1WUB1AjXzE21ETQk0Ew7YA5NsyaryrAijNfuT7UBr3mlW7ewVAvi+9489ZQHKKAZxbRpj9MTjnobQNsAIkhwCSQwDJIYDkEEByCCA5BJAcAkgOASSHAJJDAMkhgOQQgCN///yu+nnXTAjAiZN87wgIwIH30j0jIABjvpLtFQEBGFKS7BEBARhRK9c6AgIwoFWqZQQEEBSrCAhgMj0iLSIggIn0Cvzx89f0X10TwCRWkC8RwBRWkS8RwHBWki8RwFBWky8RwDBWlC8RwBC87+j1QACdjJDvNfslAuhidfkSAWxmD/IlAnAjgnyJADax6jf+zyCARvYkXyKAJvYmXyKAavYoXyKAKvYqXyKAInuWLxHAWfYuXwoUQLTr6dE+zyxCBBDlMakTe7nKV4N7AJEekxr1/qvIl5wDiPaYVDb5kmMA0R6Tyihfcgog6mNSPawoX3IIIOJjUhlO977CNICtAz0zgszyJcMAegd6RgTZ5UuGAYwYrJERIP8F0y0gSgTIf8X8S6B3BMh/i8tpoFcEyP+I24Ug6whWuqZgieulYKsIsl7lq8H9ZtDsCJB/HvcApHkRIL9MiAAk/7ODz9i7fClQANLYCPjGX0eoAKQYK0EW+VLAACRfAZnkS0EDkHxEZJMvBQ5AshWSUb4UPADJRkxW+dICAUhzBWWWLy0SgISoWSwTgDQ+AqJaLABpnDTkv7BcAFK/POS/smQA0naJyH/LsgFI7TKR/5GlA5DqpSL/c757f4ARnOS+vwmE9DK7COAEwttZfguAPgggOQSQHAJIDgEkhwCSQwDJIYDkEEByCCA5BJAcAkgOASSnGMDV4fLiq7/d3T/wXzcCcM7DOX8SK0B6ugNgFfCld/yrAigtI0TgQ2ncS96kgVsAEdgyaryLhfzP4/HpueZ1tzfX/DRrErXia2a/1BiAVB8B+FErX+IsID3NAbTUBfa0+umSyXYQh60Ts2sLYDWIQY+HYQJZDewZMQGnzGBimAerLgAAAAAAAHTwDy79rRkV4Fi1AAAAAElFTkSuQmCC', 'circuit.png': 'iVBORw0KGgoAAAANSUhEUgAAB4AAAAQ4CAYAAADo08FDAAAkHUlEQVR4nO3dQVLcSBRFUSfBotgD62UPtavsgaMDNcZ2tZSZX3o6Z1ZM9CcwubzSjx8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAwESt+gD+q/f+qL5hptbaW/UNAAAAAAAAFXrvD62E2V6qD+Cn3vsjPf4CAAAAAADc1b8dSA9iNgEYAAAAAAAAJvoafUVgZhKAAQAAAAAAYKLvvvZZBGYW7wA+ia+/5L7/HQAAAAAAIMt30VcTYjQLYAAAAAAAAFjAEpgVBGAAAAAAAABYRARmNgEYAAAAAAAAFhKBmUkABgAAAAAAgMVEYGYRgAEAAAAAAKCACMwMAjAAAAAAAAAUEYEZTQAGAAAAAACAQiIwIwnAAAAAAAAAUEwEZhQBGAAAAAAAAE5ABGYEARgAAAAAAABOQgTmKAEYAAAAAAAATkQE5ggBGAAAAAAAAE5GBGYvARgAAAAAAABO6LsIDH8jAAMAAAAAAACEEIABAAAAAAAAQgjAAAAAAAAAACEEYAAAAAAAAIAQAjAAAAAAAABACAEYAAAAAAAAIIQADAAAAAAAABBCAAYAAAAAAAAIIQADAAAAAAAAhBCAAQAAAAAAAEIIwAAAAAAAAAAhBGAAAAAAAACAEAIwAAAAAAAAQAgBGAAAAAAAACCEAAwAAAAAAAAQQgAGAAAAAAAACCEAAwAAAAAAAIQQgAEAAAAAAABCCMAAAAAAAAAAIQRgAAAAAAAAgBACMAAAAAAAAEAIARgAAAAAAAAghAAMAAAAAAAAEEIABgAAAAAAAAghAAMAAAAAAACEEIABAAAAAAAAQgjAAAAAAAAAACEEYAAAAAAAAIAQAjAAAAAAAABACAEYAAAAAAAAIIQADAAAAAAAABBCAAYAAAAAAAAIIQADAAAAAAAAhBCAAQAAAAAAAEIIwAAAAAAAAAAhBGAAAAAAAACAEAIwAAAAAAAAQAgBGAAAAAAAACCEAAwAAAAAAAAQ4rX6AH5qrb1V3wAAAAAAAABcmwUwAAAAAAAAQAgBGAAAAAAAACCEAAwAAAAAAAAQQgAGAAAAAAAACCEAAwAAAAAAAIQQgAEAAAAAAABCCMAAAAAAAAAAIQRgAAAAAAAAgBACMAAAAAAAAEAIARgAAAAAAAAghAAMAAAAAAAAEEIABgAAAAAAAAghAAMAAAAAAACEEIABAAAAAAAAQgjAAAAAAAAAACEEYAAAAAAAAIAQAjAAAAAAAABACAEYAAAAAAAAIIQADAAAAAAAABBCAAYAAAAAAAAIIQADAAAAAAAAhBCAAQAAAAAAAEIIwAAAAAAAAAAhBGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACSteoDmKv3/l75/NbaR+XzAQAAAAAA4E5eqg8gW3WABgAAAAAAgDuxAGaabfy1BAYAAAAAAID5LICZZht9LYEBAAAAAABgPgGYqURgAAAAAAAAWEcAZjoRGAAAAAAAANYQgFlCBAYAAAAAAID5BGCWEYEBAAAAAABgLgGYpURgAAAAAAAAmEcAZjkRGAAAAAAAAOYQgCkhAgMAAAAAAMB4AjBlRGAAAAAAAAAYSwCmlAgMAAAAAAAA4wjAlBOBAQAAAAAAYAwBmFMQgQEAAAAAAOC4Vn0AbF0l/m6DNQAAAAAAAJyFBTCnIqwCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACs0aoPAAAAAAAA4Jje+3vl81trH5XPBz69VB8AAAAAAADAtVUHaOCTBTAAAAAAAAC7beOvJTDUswAGAAAAAABgt230tQSGegIwAAAAAAAAh4jAcB4CMAAAAAAAAIeJwHAOAjAAAAAAAABDiMBQTwAGAAAAAABgGBEYagnAAAAAAAAADCUCQx0BGAAAAAAAgOFEYKghAAMAAAAAADCFCAzrCcAAAAAAAABMIwLDWgIwAAAAAAAAU4nAsI4ADAAAAAAAwHQiMKwhAAMAAAAAALCECAzzteoDAAAAAAAAuJerxN9tsIarsAAGAAAAAABgKWEVAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA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AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAXEWrPoBPvffH9nNr7a3qFgAAAAAAAOB6XqoPAAAAAAAAAGAMARgAAAAAAAAghAAMAAAAAAAAEEIABgAAAAAAAAghAAMAAAAAAACEEIABAAAAAAAAQgjAAAAAAAAAACEEYAAAAAAAAIAQAjAAAAAAAABACAEYAAAAAAAAIIQADAAAAAAAABBCAAYAAAAAAAAIIQADAAAAAAAAhBCAAQAAAAAAAEIIwAAAAAAAAAAhBGAAAAAAAACAEAIwAAAAAAAAQAgBGAAAAAAAACCEAAwAAAAAAAAQ4rX6AAAAAAAAAOBXvffH9nNr7a3qFq7DAhgAAAAAAAAghAAMAAAAAAAAEEIABgAAAAAAAAghAAMAAAAAAACEEIABAAAAAAAAQgjAAAAAAAAAACEEYAAAAAAAAIAQAjAAAAAAAABACAEYAAAAAAAAIIQADAAAAAAAABBCAAYAAAAAAAAIIQADAAAAAAAAhBCAAQAAAAAAAEIIwAAAAAAAAAAhBGAAAAAAAACAEAIwAAAAAAAAQAgBGAAAAAAAACCEAAwAAAAAAAAQQgAGAAAAAAAACCEAAwAAAAAAAIQQgAEAAAAAAABCCMAAAAAAAAAAIQRgAAAAAAAAgBACMAAAAAAAAEAIARgAAAAAAAAghAAMAAAAAAAAEEIABgAAAAAAAAghAAMAAAAAAACEEIABAAAAAAAAQgjAAAAAAAAAACEEYAAAAAAAAIAQAjAAAAAAAABACAEYAAAAAAAAIIQADAAAAAAAABBCAAYAAAAAAAAIIQADAAAAAAAAhBCAAQAAAAAAAEIIwAAAAAAAAAAhBGAAAAAAAACAEALwifXeH733R/UdAAAAAAAAwDUIwCfSWnv77udCMAAAAAAAAPCM1+oDeN42Av8uFgMAAAAAAAD31aoP4PeeXf2KwQAAAAAAAHm+tiJNiGcIwBchBgMAAAAAANyLAMwe3gF8Ea21t2d+qb0vGAAAAAAAAO7LAvjCrIIBAAAAAAByWQCzhwAcQgwGAAAAAADIIgCzhwAcSAwGAAAAAAC4PgGYPbwDOJD3BQMAAAAAAMA9WQDfhFUwAAAAAADAtVgAs4cAfENiMAAAAAAAwPkJwOwhAN+cGAwAAAAAAHBOAjB7eAfwzXlfMAAAAAAAAOSwAOYXVsEAAAAAAAD1LIDZQwDmj8RgAAAAAACAGgIwewjAPE0MBgAAAAAAWEcAZg/vAOZp3hcMAAAAAAAA52YBzCFWwQAAAAAAAHNYALOHAMwwYjAAAAAAAHCEbxj9M42FZ7xWH0CO7R8df6ABAAAAAABgPe8AZorfvS/Yf6YAAAAAAAD8fxoLz7IAZiqrYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOOAf2ZAJLn0ENJYAAAAASUVORK5CYII=', 'placeholder.png': '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', 'arrow_up.png': 'iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAABoUlEQVR4nO3aS26DQBQFUZP975mMWkKRYpl+v3txnVEGNtCvsBUwrxcAAAAAAAAAAAAAAAAAAE9yTB9AxHme5/r7OA7Ltdgd9HXo/3GK8TN9AHd8Mvw7r1NgE+DuUF0iWATYHaZDBPkA0SGqR5AOkDU85QiyAbKHphpBMkDVsBQjSAb4JnIBqs9StU+BVICd4exc9SpFkAkQGb5zBIkAGWe+a4TxAJlfO44RRgNUfOe7RRgLMH3m/TV1PCMBdhf76dm9+3vARIT2ANXD33390h2hNUDX8KPv64zQFqB7+NH3d0VoCTA1/Oh2OiKUB5gefnR71RFKA6gMP7rdyghlAdSGH91+VYTxWxFXXc/zKD03VBKg67ZyhMoti/QADsOP7Dc7QmoAp+FH9p8ZIS2A4/CXyQgpAZyHv0xFCAd4wvCXiQihAGr39KdE5rAdQPVCK6r7Qm07wM6Bqg9/6Vxb6Cvozk5dhr90rS1tKO8+gm7Dv6peV9p1QOajIkqq15V6JZzxsJQiu3U99d/Tp64LAAAAAAAAAAAAAAAAAAAAAOJ+AaitCEcBvJccAAAAAElFTkSuQmCC', 'arrow_down.png': 'iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAABrUlEQVR4nO3aYW7CMBBE4Zfe/87pL6QKqQISr3e2fd8BwJ6Jk9gAkiRJkiRJkiRJkiRJkiRJkiTlOs/z7B7DSlXz+ar40Mdg/0oJlfNZXsDzIKeXUD2fpQX8NripJeyYz7HiQ94d0HEcS75vh11zur0CPrkapqyEnXO6VcCVL08vYfecbhVwdfmllnB1XHduQ7dvQZPu6xXanwFXB5G2Cq6MZ8XFt+w1dHIJXeHD4n3AxBI6w4eCnfCkErrDh6KzoAklJIQPRQVAdgkp4UNhAVdVl9D9zHlWWkDaRq1jo/VK+QpIKSExfNh0C+ouITV82PgM6CohOXzY/BDeXUJ6+NDwFrSrhAnhQ9NraHUJU8KHxn1AVQmTwofmjVjKbwmd42jfCa88skg6YnhXewGwpoSJ4UNIAXCvhKnhw6L/Ba2047AsJXwIWgEP1eEkhQ+BBUBdSGnhQ2gB/0lsAauv1sSrH4ILgHWhpYYP4QXA/fCSw4cBBcD1ENPDhyEFwOdhTggfBhUA74c6JXwYVgC8DndS+BB4FPGJn8cW04KXJEmSJEmSJEmSJEmSJBX5BgCoAFPOW2xlAAAAAElFTkSuQmCC'}


def prepare_ui():
    layout_dir = os.path.join(ROOT, 'resources', 'skins', 'Default', '1080i')
    media_dir = os.path.join(ROOT, 'resources', 'skins', 'Default', 'media')
    os.makedirs(layout_dir, exist_ok=True)
    os.makedirs(media_dir, exist_ok=True)
    # Xenon's ThemeLabelColor setting is the source used by its theme variable.
    color = xbmc.getInfoLabel('Skin.String(ThemeLabelColor)').strip()
    if not color or color.lower() == 'none':
        color = 'FF6DB9E5'  # Same default as Xenon 2's IncludesVariables.xml.
    from xml.sax.saxutils import escape
    layout = LAYOUT.replace('__THEME__', escape(color, {'"': '&quot;'}))
    for name, data in TEXTURES.items():
        texture_path = os.path.join(media_dir, name)
        with open(texture_path, 'wb') as stream:
            stream.write(base64.b64decode(data))
        # Absolute paths avoid depending on active-skin texture lookup behavior.
        from xml.sax.saxutils import escape
        layout = layout.replace('>' + name + '<', '>' + escape(texture_path) + '<')
    with open(os.path.join(layout_dir, 'wizard.xml'), 'w', encoding='utf-8') as stream:
        stream.write(layout)


BACK = (9, 10, 92, 216, 247)


def rpc(method, params):
    result = json.loads(xbmc.executeJSONRPC(json.dumps({
        'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})))
    if 'error' in result:
        raise RuntimeError(str(result['error']))
    return result.get('result', {})


def status(addon_id):
    try:
        return rpc('Addons.GetAddonDetails', {
            'addonid': addon_id, 'properties': ['enabled']}).get('addon')
    except RuntimeError:
        return None


def install_confirmation_matches(heading, body, addon_name=None):
    """Match Kodi's localized install prompt; catalog labels may differ."""
    def plain(value):
        return ' '.join(re.sub(r'\[(?:/?(?:B|I|UPPERCASE|LOWERCASE)|/?COLOR[^\]]*)\]', '', value or '', flags=re.I).casefold().split())
    heading, body = plain(heading), plain(body)
    title = plain(xbmc.getLocalizedString(24076))
    before = plain(xbmc.getLocalizedString(24100))
    after = plain(xbmc.getLocalizedString(24101))
    return bool(title and before and after and heading == title
                and before in body and after in body)


def read_install_dialog():
    window = xbmcgui.Window(10100)
    values = []
    for cid, method in ((1, 'getLabel'), (9, 'getText')):
        value = ''
        try:
            value = getattr(window.getControl(cid), method)()
        except Exception:
            pass
        # Query Kodi's foreground control labels when native control access fails.
        if not value:
            value = xbmc.getInfoLabel('Control.GetLabel(%d)' % cid)
        values.append(value)
    return values


def watch_install_confirmation(token, timeout):
    home = xbmcgui.Window(10000)
    key = 'Xenon2.Setup.InstallConfirm.' + token
    monitor = xbmc.Monitor()
    deadline = time.monotonic() + timeout
    home.setProperty(key + '.Ready', 'true')
    last_error = None
    try:
        while home.getProperty(key) == 'active' and not monitor.abortRequested() and time.monotonic() < deadline:
            try:
                if xbmcgui.getCurrentWindowDialogId() == 10100:
                    heading, body = read_install_dialog()
                    if install_confirmation_matches(heading, body):
                        # This helper owns only the first standard install prompt
                        # after the caller arms it for one pending addon.
                        if home.getProperty(key) != 'active':
                            return
                        xbmc.executebuiltin('SendClick(10100,11)')
                        xbmc.log('Xenon Setup: sent Yes to Add-on required confirmation', xbmc.LOGINFO)
                        # Verify closure; try direct focus/select once if necessary.
                        if monitor.waitForAbort(0.8):
                            return
                        if home.getProperty(key) == 'active' and xbmcgui.getCurrentWindowDialogId() == 10100:
                            h, b = read_install_dialog()
                            if install_confirmation_matches(h, b):
                                xbmcgui.Window(10100).setFocusId(11)
                                xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1,
                                    'method': 'Input.ExecuteAction', 'params': {'action': 'select'}}))
                        return
                    if not last_error:
                        xbmc.log('Xenon Setup: install dialog not matched; heading=%r, body_read=%s' % (heading, bool(body)), xbmc.LOGWARNING)
                        last_error = 'unmatched'
            except Exception as exc:
                if not last_error:
                    xbmc.log('Xenon Setup: confirmation helper: %s' % type(exc).__name__, xbmc.LOGWARNING)
                    last_error = type(exc).__name__
            if monitor.waitForAbort(0.1):
                return
    finally:
        home.clearProperty(key + '.Ready')


INSTALL_CONFIRMATION_HELPER = 'import json\nimport re\nimport sys\nimport time\nimport xbmc\nimport xbmcgui\n\ndef install_confirmation_matches(heading, body, addon_name=None):\n    """Match Kodi\'s localized install prompt; catalog labels may differ."""\n    def plain(value):\n        return \' \'.join(re.sub(r\'\\[(?:/?(?:B|I|UPPERCASE|LOWERCASE)|/?COLOR[^\\]]*)\\]\', \'\', value or \'\', flags=re.I).casefold().split())\n    heading, body = plain(heading), plain(body)\n    title = plain(xbmc.getLocalizedString(24076))\n    before = plain(xbmc.getLocalizedString(24100))\n    after = plain(xbmc.getLocalizedString(24101))\n    return bool(title and before and after and heading == title\n                and before in body and after in body)\n\ndef read_install_dialog():\n    window = xbmcgui.Window(10100)\n    values = []\n    for cid, method in ((1, \'getLabel\'), (9, \'getText\')):\n        value = \'\'\n        try:\n            value = getattr(window.getControl(cid), method)()\n        except Exception:\n            pass\n        # Query Kodi\'s foreground control labels when native control access fails.\n        if not value:\n            value = xbmc.getInfoLabel(\'Control.GetLabel(%d)\' % cid)\n        values.append(value)\n    return values\n\ndef watch_install_confirmation(token, timeout):\n    home = xbmcgui.Window(10000)\n    key = \'Xenon2.Setup.InstallConfirm.\' + token\n    monitor = xbmc.Monitor()\n    deadline = time.monotonic() + timeout\n    home.setProperty(key + \'.Ready\', \'true\')\n    last_error = None\n    try:\n        while home.getProperty(key) == \'active\' and not monitor.abortRequested() and time.monotonic() < deadline:\n            try:\n                if xbmcgui.getCurrentWindowDialogId() == 10100:\n                    heading, body = read_install_dialog()\n                    if install_confirmation_matches(heading, body):\n                        # This helper owns only the first standard install prompt\n                        # after the caller arms it for one pending addon.\n                        if home.getProperty(key) != \'active\':\n                            return\n                        xbmc.executebuiltin(\'SendClick(10100,11)\')\n                        xbmc.log(\'Xenon Setup: sent Yes to Add-on required confirmation\', xbmc.LOGINFO)\n                        # Verify closure; try direct focus/select once if necessary.\n                        if monitor.waitForAbort(0.8):\n                            return\n                        if home.getProperty(key) == \'active\' and xbmcgui.getCurrentWindowDialogId() == 10100:\n                            h, b = read_install_dialog()\n                            if install_confirmation_matches(h, b):\n                                xbmcgui.Window(10100).setFocusId(11)\n                                xbmc.executeJSONRPC(json.dumps({\'jsonrpc\': \'2.0\', \'id\': 1,\n                                    \'method\': \'Input.ExecuteAction\', \'params\': {\'action\': \'select\'}}))\n                        return\n                    if not last_error:\n                        xbmc.log(\'Xenon Setup: install dialog not matched; heading=%r, body_read=%s\' % (heading, bool(body)), xbmc.LOGWARNING)\n                        last_error = \'unmatched\'\n            except Exception as exc:\n                if not last_error:\n                    xbmc.log(\'Xenon Setup: confirmation helper: %s\' % type(exc).__name__, xbmc.LOGWARNING)\n                    last_error = type(exc).__name__\n            if monitor.waitForAbort(0.1):\n                return\n    finally:\n        home.clearProperty(key + \'.Ready\')\n\nwatch_install_confirmation(sys.argv[1], int(sys.argv[2]))\n'

class InstallConfirmation:
    """Independent Python invocation continues while InstallAddon is waiting."""
    def __init__(self, addon_name, monitor, timeout):
        self.monitor, self.timeout = monitor, timeout
        self.token = uuid.uuid4().hex
        self.key = 'Xenon2.Setup.InstallConfirm.' + self.token
        self.home = xbmcgui.Window(10000)

    def start(self):
        if xbmcgui.getCurrentWindowDialogId() == 10100:
            return
        self.home.setProperty(self.key, 'active')
        os.makedirs(PROFILE, exist_ok=True)
        helper_path = os.path.join(PROFILE, 'install_confirmation.py')
        with open(helper_path, 'w', encoding='utf-8') as stream:
            stream.write(INSTALL_CONFIRMATION_HELPER)
        xbmc.executebuiltin('RunScript("%s",%s,%d)' % (helper_path, self.token, self.timeout))
        deadline = time.monotonic() + 5
        while not self.home.getProperty(self.key + '.Ready') and time.monotonic() < deadline:
            if self.monitor.waitForAbort(0.1):
                break
        if not self.home.getProperty(self.key + '.Ready'):
            self.home.clearProperty(self.key)
            xbmc.log('Xenon Setup: install confirmation helper did not start; use manual confirmation', xbmc.LOGWARNING)

    def finish(self):
        self.home.clearProperty(self.key)


def install_one(addon_id, monitor, timeout=180, addon_name=None):
    """Return a verified outcome; a timeout never means confirmed failure."""
    if not re.fullmatch(r'plugin\.video\.[a-z0-9_.-]+', addon_id):
        raise ValueError('Invalid add-on ID')
    details = status(addon_id)
    if details and details.get('enabled'):
        return 'Already enabled'
    if not details:
        confirmation = InstallConfirmation(addon_name, monitor, timeout)
        confirmation.start()
        try:
            xbmc.executebuiltin('InstallAddon(%s)' % addon_id)
            deadline = time.monotonic() + timeout
            while not monitor.abortRequested():
                details = status(addon_id)
                if details:
                    break
                if time.monotonic() >= deadline:
                    return 'Not confirmed (cancelled, unavailable, failed, or still installing)'
                if monitor.waitForAbort(0.5):
                    return 'Interrupted'
            if monitor.abortRequested():
                return 'Interrupted'
        finally:
            confirmation.finish()
    if details and not details.get('enabled'):
        try:
            rpc('Addons.SetAddonEnabled', {'addonid': addon_id, 'enabled': True})
        except RuntimeError:
            return 'Installed; could not enable'
    details = status(addon_id)
    return 'Ready' if details and details.get('enabled') else 'Installed; not enabled'


def initial_choices(catalog):
    return {branch: [entry['id'] for entry in entries
                     if status(entry['id']) is not None]
            for branch, entries in catalog.items()}


def pending_addons(entries, selected_ids):
    """Only checked add-ons absent from Kodi belong in the install queue."""
    return [entry for entry in entries
            if entry['id'] in selected_ids and status(entry['id']) is None]


def flavors_for(mode):
    return FREE_FLAVORS if mode == 'free' else FLAVORS


def show_step(window, visible):
    for id in [750, 306, 100, 101, 200, 201, 202, 300, 301, 400, 401, 500, 501, 502, 600, 602, 601, 603, 303, 304, 700, 710, 711, 305, 720, 721, 722, 740, 741, 742]:
        window.getControl(id).setVisible(id in visible)


class Wizard(xbmcgui.WindowXMLDialog):
    def configure(self, stage, mode, choices, catalog):
        self.stage, self.mode = stage, mode
        self.choices, self.catalog = choices, catalog
        self.result = 'exit'
        self.focused_row = 0

    def onInit(self):
        choosing = self.stage == 'source'
        visible = {100, 101, 301} if choosing else {750, 300, 301, 400, 401, 600, 601, 602, 603, 303 if self.mode == 'debrid' else 305}
        show_step(self, visible)
        self.getControl(10).setLabel('Xenon Setup')
        self.getControl(11).setLabel('Step 1 - Choose your links' if choosing else 'Step 2 - Choose %s add-ons' % self.mode.upper())
        self.getControl(12).setLabel('Do you have a paid Debrid account, or would you like to use Free links?' if choosing else 'Select any add-ons below. Scroll for more. Your existing repositories will be used.')
        self.getControl(301).setLabel('Exit' if choosing else 'Back')
        self.getControl(300).setWidth(580)
        if choosing:
            self.getControl(301).controlUp(self.getControl(100))
            self.getControl(301).controlDown(self.getControl(100))
            self.getControl(301).controlLeft(self.getControl(101))
            self.getControl(301).controlRight(self.getControl(100))
        else:
            listing = self.getControl(750)
            self.update_addon_list(0)
            next_button = self.getControl(303 if self.mode == 'debrid' else 305)
            self.getControl(301).controlRight(next_button)
            for cid in (300, 301, 303 if self.mode == 'debrid' else 305):
                self.getControl(cid).controlUp(listing)
                self.getControl(cid).controlDown(listing)
            for cid in (600, 601):
                self.getControl(cid).controlRight(listing)
            self.refresh()
        self.setFocusId(100 if choosing else (750 if self.catalog[self.mode] else 301))

    def update_addon_list(self, selected):
        listing = self.getControl(750)
        listing.reset()
        for entry in self.catalog[self.mode]:
            item = xbmcgui.ListItem(label=entry['name'])
            item.setProperty('checked', 'true' if entry['id'] in self.choices[self.mode] else 'false')
            item.setProperty('installed', 'true' if status(entry['id']) is not None else 'false')
            item.setProperty('addon_icon', addon_icon(entry))
            listing.addItem(item)
        if self.catalog[self.mode]:
            listing.selectItem(max(0, min(selected, len(self.catalog[self.mode]) - 1)))

    def onFocus(self, control_id):
        show = self.stage == 'addons' and control_id in (750, 600, 601)
        self.getControl(400).setVisible(show)
        self.getControl(401).setVisible(show)

    def refresh(self):
        count = len(pending_addons(self.catalog[self.mode], self.choices[self.mode]))
        self.getControl(300).setLabel('Install (%d) add-ons' % count)
        self.getControl(300).setEnabled(count > 0)

    def onClick(self, cid):
        if cid in (600, 601) and self.stage == 'addons':
            listing = self.getControl(750)
            if self.catalog[self.mode]:
                index = max(0, min(len(self.catalog[self.mode]) - 1,
                                  listing.getSelectedPosition() + (-1 if cid == 600 else 1)))
                listing.selectItem(index)
                self.setFocusId(750)
        elif cid in (100, 101):
            self.mode = 'free' if cid == 100 else 'debrid'
            self.result = 'next'
            self.close()
        elif cid == 750 and self.stage == 'addons':
            index = self.getControl(750).getSelectedPosition()
            if not 0 <= index < len(self.catalog[self.mode]):
                return
            entry = self.catalog[self.mode][index]
            selected = self.choices[self.mode]
            if entry['id'] in selected:
                selected.remove(entry['id'])
            else:
                selected.append(entry['id'])
            self.getControl(750).getListItem(index).setProperty('checked', 'true' if entry['id'] in selected else 'false')
            self.refresh()
        elif cid == 305 and self.mode == 'free':
            self.result = 'flavor'
            self.close()
        elif cid == 303 and self.mode == 'debrid':
            self.result = 'authorize'
            self.close()
        elif cid in (300, 301):
            self.result = 'install' if cid == 300 else ('back' if self.stage != 'source' else 'exit')
            self.close()

    def onAction(self, action):
        if action.getId() in BACK:
            self.result = 'back' if self.stage != 'source' else 'exit'
            self.close()


def addon_icon(entry):
    icon = entry.get('icon', '')
    if icon and xbmcvfs.exists(icon):
        return icon
    try:
        icon = xbmcaddon.Addon(entry['id']).getAddonInfo('icon')
        if icon and xbmcvfs.exists(icon):
            return icon
    except Exception:
        pass
    return os.path.join(ROOT, 'resources', 'skins', 'Default', 'media', 'placeholder.png')


def service_icon(entry):
    icon = entry.get('icon', '')
    if icon and xbmcvfs.exists(icon):
        return icon
    try:
        path = xbmcvfs.translatePath('special://skin/resources/scripts/reauthorize/main/')
        icon = os.path.join(path, 'resources', 'icons', entry['id'] + '.png')
        if xbmcvfs.exists(icon):
            return icon
    except Exception:
        pass
    return os.path.join(ROOT, 'resources', 'skins', 'Default', 'media', 'placeholder.png')


def reauthorize_ready(start_service=True):
    path = 'special://skin/resources/scripts/reauthorize/entry.py'
    if not xbmcvfs.exists(path):
        xbmcgui.Dialog().ok('ReAuthorize required', 'The embedded ReAuthorize files are missing from the skin scripts folder.')
        return False
    if xbmc.getCondVisibility('System.AddonIsEnabled(script.module.reauthorize)'):
        xbmcgui.Dialog().ok('Embedded ReAuthorize', 'Disable the standalone ReAuthorize add-on before using this version. Your saved sign-ins are kept.')
        return False
    if start_service:
        xbmc.executebuiltin('RunScript(%s,service=true)' % path)
    return True


def launch_authorization(entry, monitor, timeout=1800):
    """Await the embedded action's completion, without opening add-on settings."""
    if entry['action'] not in ({service['action'] for service in SERVICES + TRACKING_SERVICES} | {'wizardRestore', 'wizardStatus'}):
        raise ValueError('Unknown authorization action')
    job = str(time.time_ns())
    window = xbmcgui.Window(10000)
    name = 'Xenon.ReAuthorize.Job.' + job
    window.clearProperty(name)
    xbmc.executebuiltin('RunScript(special://skin/resources/scripts/reauthorize/entry.py,action=%s,job=%s,wizard=true)' % (entry['action'], job))
    deadline = time.monotonic() + timeout
    try:
        while not monitor.abortRequested() and time.monotonic() < deadline:
            state = window.getProperty(name)
            if state in ('done', 'error'):
                if state == 'error':
                    xbmcgui.Dialog().ok('ReAuthorize', 'The authorization action could not finish. Check the Kodi log. No success has been assumed.')
                return state == 'done'
            if monitor.waitForAbort(0.25):
                return False
        return False
    finally:
        window.clearProperty(name)


SERVICE_CREDENTIALS = {
    'realdebrid': ('realdebrid.token',), 'premiumize': ('premiumize.token',),
    'alldebrid': ('alldebrid.token',), 'torbox': ('torbox.token',),
    'easydebrid': ('easydebrid.token',), 'offcloud': ('offcloud.token',),
    'debridlink': ('debridlink.token',),
    'linksnappy': ('linksnappy.username', 'linksnappy.password'),
    'easynews': ('easynews.username', 'easynews.password'),
    'filepursuit': ('filepursuit.api.key',), 'trakt': ('trakt.token',),
    'simkl': ('simkl.token',), 'mdblist': ('mdblist.oauth.token',),
}

def authorization_status(service_id):
    path = xbmcvfs.translatePath('special://profile/addon_data/script.module.reauthorize/settings.xml')
    try:
        root = ET.parse(path).getroot()
        values = {row.get('id'): row.get('value', row.text or '') for row in root.iter('setting')}
    except (OSError, ET.ParseError):
        return False
    keys = SERVICE_CREDENTIALS.get(service_id, ())
    return bool(keys) and all(values.get(key, '').strip() for key in keys)

def check_saved_logins(monitor):
    if not reauthorize_ready(start_service=False):
        return False
    progress = xbmcgui.DialogProgressBG()
    progress.create('Saved login check', 'Checking backups and sending saved logins to installed add-ons')
    try:
        result = launch_authorization({'action': 'wizardRestore'}, monitor)
    finally:
        progress.close()
    if not result and not monitor.abortRequested():
        xbmcgui.Dialog().ok('Saved login check', 'The backup check did not complete. Returning to add-on selections; no successful restore has been assumed.')
    if result:
        reauthorize_ready()  # Resume normal renewal/new-add-on monitoring.
    return result


class AuthorizationWizard(Wizard):
    entries = SERVICES
    def onInit(self):
        show_step(self, {710, 711, 301, 304, 306, 600, 601, 602, 603, 700})
        self.getControl(10).setLabel('Xenon Setup')
        self.getControl(11).setLabel('Final Step - Authorize Your Tracking Service' if self.stage == 'tracking' else 'Step 3 - Authorize Debrid')
        self.getControl(12).setLabel('Your Home menus are saved. Choose a tracking service to authorize with ReAuthorize.' if self.stage == 'tracking' else 'Choose a service to authorize with ReAuthorize. If It shows Authorized, then you do not need to authorize again..')
        for cid in (100, 101, 200, 201, 202, 300, 303, 305, 400, 401, 500, 501, 502, 720, 721, 722):
            self.getControl(cid).setVisible(False)
        for cid in (301, 304, 306, 600, 601, 602, 603, 700, 710, 711):
            self.getControl(cid).setVisible(True)
        self.getControl(301).setLabel('Back')
        self.getControl(304).setLabel('Finish' if self.stage == 'tracking' else 'Select Xenon Flavor')
        listing = self.getControl(700)
        listing.reset()
        for entry in self.entries:
            item = xbmcgui.ListItem(label=entry['name'])
            item.setProperty('service_icon', service_icon(entry))
            authorized = authorization_status(entry['id'])
            item.setProperty('auth_status', 'Authorized' if authorized else 'Not Authorized')
            item.setProperty('authorized', 'true' if authorized else 'false')
            listing.addItem(item)
        listing.selectItem(self.auth_index)
        self.getControl(301).controlRight(self.getControl(306))
        self.getControl(301).controlUp(listing)
        for cid in (600, 601):
            self.getControl(cid).controlRight(listing)
        self.setFocusId(700)

    def onFocus(self, control_id):
        # Service image and name are bound directly to Container(700).ListItem.
        pass

    def onClick(self, cid):
        listing = self.getControl(700)
        if cid in (600, 601):
            index = max(0, min(len(self.entries) - 1,
                              listing.getSelectedPosition() + (-1 if cid == 600 else 1)))
            listing.selectItem(index)
            self.setFocusId(700)
        elif cid == 700:
            if reauthorize_ready():
                self.auth_index = listing.getSelectedPosition()
                self.result = 'service'
                self.close()
        elif cid == 306:
            if reauthorize_ready():
                self.auth_index = listing.getSelectedPosition()
                self.result = 'view_status'
                self.close()
        elif cid in (301, 304):
            self.result = 'back' if cid == 301 else ('finish' if self.stage == 'tracking' else 'flavor')
            self.close()


def flavor_directory(flavor):
    folder = flavor.get('folder', flavor['id'])
    if not re.fullmatch(r'[a-z0-9_-]+', folder):
        raise ValueError('Invalid flavor folder name')
    return os.path.join(xbmcvfs.translatePath(FLAVOR_ROOT), folder, 'script.skinshortcuts')


def profile_entries(data, flavor):
    root = ET.fromstring(data)
    if root.tag != 'shortcuts':
        raise ValueError('The flavor main menu must have a shortcuts root.')
    grouped = {}
    for entry in root.findall('shortcut'):
        label = entry.findtext('label', '').strip()
        if not label:
            raise ValueError('Every flavor Home menu entry needs a label.')
        grouped.setdefault(label, []).append(entry)
    for label in flavor['always_labels']:
        if label not in grouped:
            raise ValueError('Missing always-on label in flavor: ' + label)
    if set(flavor['always_labels']) & set(DISABLED_SETUP_LABELS):
        raise ValueError('An always-on label is also configured as a setup label.')
    return root, grouped


def read_flavor_menu(flavor):
    path = os.path.join(flavor_directory(flavor), 'skin.xenon2-mainmenu.DATA.xml')
    with open(path, 'rb') as stream:
        data = stream.read()
    profile_entries(data, flavor)
    return data


def display_menu_label(label):
    return {'1036': 'Favourites', '24001': 'Add-ons', '4': 'Live TV'}.get(label, label)


def plan_home_menus(original, flavor, selected_labels):
    root, grouped = profile_entries(original, flavor)
    unknown = set(selected_labels) - set(grouped)
    if unknown:
        raise ValueError('Selected menu labels are missing from this flavor: ' + ', '.join(sorted(unknown)))
    enabled = (set(selected_labels) | set(flavor['always_labels'])) - set(DISABLED_SETUP_LABELS)
    for label, entries in grouped.items():
        for entry in entries:
            for disabled in list(entry.findall('disabled')):
                entry.remove(disabled)
            if label not in enabled:
                ET.SubElement(entry, 'disabled').text = 'True'
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def directory_manifest(path):
    """Validate source files and detect concurrent live-profile edits."""
    if not os.path.exists(path):
        return None
    if not os.path.isdir(path) or os.path.islink(path):
        raise ValueError('Expected a real Skin Shortcuts directory.')
    files = {}
    for parent, directories, names in os.walk(path):
        for name in directories + names:
            if os.path.islink(os.path.join(parent, name)):
                raise ValueError('Flavor/profile folders must not contain symlinks.')
        for name in names:
            full = os.path.join(parent, name)
            with open(full, 'rb') as stream:
                files[os.path.relpath(full, path)] = hashlib.sha256(stream.read()).hexdigest()
    return files


def apply_flavor(flavor, menu_ids=None, refresh=True):
    source = flavor_directory(flavor)
    source_manifest = directory_manifest(source)
    if source_manifest is None:
        raise ValueError('Flavor folder not found: ' + source)
    original_menu = read_flavor_menu(flavor)
    updated = plan_home_menus(original_menu, flavor, menu_ids or [])
    # Validate every supplied menu/submenu file before touching the live folder.
    for relative in source_manifest:
        if relative.endswith('.DATA.xml'):
            ET.parse(os.path.join(source, relative))
    live = os.path.dirname(xbmcvfs.translatePath(MENU_FILE))
    source_path, live_path = os.path.realpath(source), os.path.realpath(live)
    try:
        common = os.path.commonpath([source_path, live_path])
    except ValueError:
        common = None  # Source and profile can be on different Windows drives.
    if common in (source_path, live_path):
        raise ValueError('Flavor source and live profile must be separate directories.')
    os.makedirs(os.path.dirname(live), exist_ok=True)
    live_manifest = directory_manifest(live)
    stage = tempfile.mkdtemp(prefix='.xenon-shortcuts-stage-', dir=os.path.dirname(live))
    rollback = live + '.wizard-rollback-' + str(time.time_ns()) if live_manifest is not None else None
    moved_original = False
    try:
        shutil.copytree(source, stage, dirs_exist_ok=True)
        if directory_manifest(stage) != source_manifest or directory_manifest(source) != source_manifest:
            raise ValueError('The flavor source changed while copying. No live changes made.')
        with open(os.path.join(stage, 'skin.xenon2-mainmenu.DATA.xml'), 'wb') as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        if directory_manifest(live) != live_manifest:
            raise ValueError('The current Skin Shortcuts profile changed while saving. Please try again.')
        if rollback:
            os.replace(live, rollback)
            moved_original = True
        try:
            os.replace(stage, live)
        except Exception:
            if moved_original:
                os.replace(rollback, live)
                moved_original = False
            raise
    finally:
        if os.path.isdir(stage):
            shutil.rmtree(stage)
    # Rollback exists only for the swap; successful installs retain no history.
    if moved_original and rollback and os.path.isdir(rollback):
        try:
            shutil.rmtree(rollback)
        except OSError as exc:
            xbmc.log('Xenon Setup: could not remove temporary rollback folder %s: %s' % (rollback, exc), xbmc.LOGWARNING)
    xbmc.executebuiltin('Skin.SetString(Xenon2.Setup.Flavor,%s)' % flavor['id'])
    if refresh:
        xbmc.executebuiltin('RunScript(script.skinshortcuts,type=buildxml&mainmenuID=9000&levels=2&group=mainmenu|buttonmenu)')
    return None


def flavor_icon(entry):
    icon = entry.get('icon', '')
    if icon and xbmcvfs.exists(icon):
        return icon
    try:
        icon = xbmcaddon.Addon(entry['addon']).getAddonInfo('icon')
        if icon and xbmcvfs.exists(icon):
            return icon
    except Exception:
        pass
    return os.path.join(ROOT, 'resources', 'skins', 'Default', 'media', 'placeholder.png')


class FlavorWizard(Wizard):
    def onInit(self):
        show_step(self, {301, 304, 721, 722, 720, 600, 601, 602, 603})
        self.getControl(10).setLabel('Xenon Setup')
        self.getControl(11).setLabel('Step 4 - Select Xenon Flavor')
        self.getControl(12).setLabel('What is your favorite Free addon?' if self.mode == 'free' else 'What is your favorite addon?')
        for cid in (100, 101, 200, 201, 202, 300, 303, 305, 400, 401, 500, 501, 502, 700, 710, 711):
            self.getControl(cid).setVisible(False)
        for cid in (301, 304, 600, 601, 602, 603, 720, 721, 722):
            self.getControl(cid).setVisible(True)
        self.getControl(301).setLabel('Back')
        self.getControl(304).setLabel('Choose Home Menus')
        listing = self.getControl(720)
        listing.reset()
        for entry in flavors_for(self.mode):
            item = xbmcgui.ListItem(label=entry['name'])
            item.setProperty('flavor_icon', flavor_icon(entry))
            listing.addItem(item)
        listing.selectItem(self.flavor_index)
        self.getControl(301).controlRight(self.getControl(306))
        self.getControl(301).controlUp(listing)
        self.getControl(304).controlUp(listing)
        self.getControl(304).controlDown(listing)
        for cid in (600, 601):
            self.getControl(cid).controlRight(listing)
        self.setFocusId(720)

    def onFocus(self, control_id):
        pass

    def onClick(self, cid):
        listing = self.getControl(720)
        if cid in (600, 601):
            index = max(0, min(len(flavors_for(self.mode)) - 1,
                              listing.getSelectedPosition() + (-1 if cid == 600 else 1)))
            listing.selectItem(index)
            self.setFocusId(720)
        elif cid in (720, 304):
            self.flavor_index = listing.getSelectedPosition()
            self.result = 'menus'
            self.close()
        elif cid == 301:
            self.result = 'back'
            self.close()


class TrackingWizard(AuthorizationWizard):
    entries = TRACKING_SERVICES


class HomeMenusWizard(Wizard):
    def onInit(self):
        show_step(self, {740, 741, 742, 301, 304, 600, 601, 602, 603})
        self.getControl(10).setLabel('Xenon Setup')
        self.getControl(11).setLabel('Choose Your Home Menus')
        self.getControl(12).setLabel('Add-ons, Favourites and Xenon are always enabled. Xenon Setup is disabled when you save.')
        self.getControl(301).setLabel('Back')
        self.getControl(304).setLabel('Save & Continue')
        flavor = flavors_for(self.mode)[self.flavor_index]
        try:
            root, grouped = profile_entries(read_flavor_menu(flavor), flavor)
        except (OSError, ValueError, ET.ParseError) as exc:
            xbmcgui.Dialog().ok('Flavor folder unavailable', str(exc))
            self.result = 'back'
            self.close()
            return
        self.options = [{'id': label, 'name': display_menu_label(label),
                         'icon': 'special://skin/media/setup/menus/' + re.sub(r'[^a-z0-9_-]+', '_', label.lower()) + '.png'}
                        for label in grouped if label not in flavor['always_labels'] and label not in DISABLED_SETUP_LABELS]
        self.available = {o['id']: True for o in self.options}
        if flavor['id'] not in self.menu_choices:
            self.menu_choices[flavor['id']] = [o['id'] for o in self.options if
                all(entry.findtext('disabled', 'False') != 'True' for entry in grouped[o['id']])]
        self.menu_choices[flavor['id']] = [label for label in self.menu_choices[flavor['id']] if label in self.available]
        self.update_list(0)
        listing = self.getControl(740)
        self.getControl(301).controlRight(self.getControl(306))
        self.getControl(301).controlUp(listing)
        self.getControl(304).controlUp(listing)
        self.getControl(304).controlDown(listing)
        for cid in (600, 601):
            self.getControl(cid).controlRight(listing)
        self.setFocusId(740 if self.options else 304)

    def update_list(self, selected):
        listing = self.getControl(740)
        listing.reset()
        flavor = flavors_for(self.mode)[self.flavor_index]
        checked = self.menu_choices[flavor['id']]
        for option in self.options:
            available = self.available[option['id']]
            item = xbmcgui.ListItem(label=option['name'] if available else '[COLOR FF888888]' + option['name'] + '[/COLOR]')
            item.setProperty('checked', 'true' if option['id'] in checked else 'false')
            icon = option.get('icon', '')
            item.setProperty('menu_icon', icon if icon and xbmcvfs.exists(icon) else flavor_icon(flavor))
            listing.addItem(item)
        if self.options:
            listing.selectItem(selected)

    def onFocus(self, control_id):
        pass

    def onClick(self, cid):
        listing = self.getControl(740)
        index = listing.getSelectedPosition()
        if cid in (600, 601) and self.options:
            listing.selectItem(max(0, min(len(self.options) - 1, index + (-1 if cid == 600 else 1))))
            self.setFocusId(740)
        elif cid == 740 and self.options:
            option = self.options[index]
            if not self.available[option['id']]:
                xbmcgui.Dialog().ok('Menu unavailable', 'This label is no longer present in the selected flavor.')
                return
            selected = self.menu_choices[flavors_for(self.mode)[self.flavor_index]['id']]
            if option['id'] in selected:
                selected.remove(option['id'])
            else:
                selected.append(option['id'])
            self.update_list(index)
        elif cid == 306:
            if reauthorize_ready():
                self.auth_index = listing.getSelectedPosition()
                self.result = 'view_status'
                self.close()
        elif cid in (301, 304):
            self.result = 'back' if cid == 301 else 'tracking'
            self.close()


def save_state(mode, choices, outcomes=None):
    path = PROFILE
    xbmcvfs.mkdirs(path)
    with open(os.path.join(path, 'wizard.json'), 'w', encoding='utf-8') as stream:
        json.dump({'mode': mode, 'choices': choices, 'outcomes': outcomes or []}, stream, indent=2)


RESUME_HELPER = 'import json\nimport os\nimport time\nimport xbmc\nimport xbmcgui\n\nmonitor = xbmc.Monitor()\nhome = xbmcgui.Window(10000)\n# The saving invocation must release its lock before rebuilding the skin.\nlimit = time.monotonic() + 30\nwhile home.getProperty(\'Xenon2.Setup.Running\') and time.monotonic() < limit:\n    if monitor.waitForAbort(0.2):\n        raise SystemExit\nif home.getProperty(\'Xenon2.Setup.Running\'):\n    raise SystemExit\ntry:\n    request = {\'jsonrpc\': \'2.0\', \'id\': 1, \'method\': \'Addons.ExecuteAddon\',\n               \'params\': {\'addonid\': \'script.skinshortcuts\',\n                          \'params\': [\'type=buildxml&mainmenuID=9000&levels=2&group=mainmenu|buttonmenu\'],\n                          \'wait\': True}}\n    result = json.loads(xbmc.executeJSONRPC(json.dumps(request)))\n    if \'error\' in result:\n        raise RuntimeError(str(result[\'error\']))\n    # The build script has ended. Allow the skin reload and modal animations to settle.\n    if monitor.waitForAbort(1):\n        raise SystemExit\n    quiet_since = None\n    limit = time.monotonic() + 120\n    while time.monotonic() < limit and not monitor.abortRequested():\n        if xbmc.getCondVisibility(\'System.HasActiveModalDialog\'):\n            quiet_since = None\n        elif quiet_since is None:\n            quiet_since = time.monotonic()\n        elif time.monotonic() - quiet_since >= 2:\n            xbmc.executebuiltin(\'RunScript("\' + WIZARD_PATH + \'",resume_tracking)\')\n            break\n        if monitor.waitForAbort(0.2):\n            break\nexcept Exception as exc:\n    xbmc.log(\'Xenon 2 tracking handoff: \' + str(exc), xbmc.LOGERROR)\n    xbmcgui.Dialog().notification(\'Xenon 2 Setup\', \'Menus saved. Could not reopen tracking setup; see Kodi log.\')\n'


def schedule_tracking_resume(mode, choices, flavor_index, menu_choices):
    os.makedirs(PROFILE, exist_ok=True)
    checkpoint = os.path.join(PROFILE, 'tracking-handoff.json')
    with open(checkpoint + '.tmp', 'w', encoding='utf-8') as stream:
        json.dump({'mode': mode, 'choices': choices, 'flavor_index': flavor_index,
                   'menu_choices': menu_choices}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(checkpoint + '.tmp', checkpoint)
    helper_path = os.path.join(PROFILE, 'resume_tracking.py')
    with open(helper_path, 'w', encoding='utf-8') as stream:
        stream.write('WIZARD_PATH = ' + repr(os.path.abspath(__file__)) + '\n')
        stream.write(RESUME_HELPER)
    xbmc.executebuiltin('RunScript("%s")' % helper_path)


def load_tracking_resume():
    if 'resume_tracking' not in sys.argv[1:]:
        return None
    checkpoint = os.path.join(PROFILE, 'tracking-handoff.json')
    with open(checkpoint, encoding='utf-8') as stream:
        data = json.load(stream)
    if data.get('mode') not in ('free', 'debrid') or not 0 <= data.get('flavor_index', -1) < len(flavors_for(data['mode'])):
        raise ValueError('Invalid tracking handoff checkpoint')
    os.remove(checkpoint)  # Consume once; normal launches still start at Step 1.
    return data


def run():
    home = xbmcgui.Window(10000)
    lock = 'Xenon2.Setup.Running'
    if home.getProperty(lock):
        return
    home.setProperty(lock, 'true')
    try:
        prepare_ui()
        catalog = CATALOG
        choices = {'free': [], 'debrid': []}
        mode, stage = 'free', 'source'
        # A new session reflects actual installed add-ons, never saved selections.
        # Disabled add-ons are installed too; installation can enable them later.
        choices = initial_choices(catalog)
        monitor = xbmc.Monitor()
        auth_index = 0
        flavor_index = 0
        tracking_index = 0
        menu_choices = {}
        recovery_checked = False
        resume = load_tracking_resume()
        if resume:
            mode, stage = resume['mode'], 'tracking'
            choices = resume['choices']
            flavor_index = resume['flavor_index']
            menu_choices = resume['menu_choices']
        while not monitor.abortRequested():
            window_type = {'flavor': FlavorWizard, 'authorize': AuthorizationWizard, 'menus': HomeMenusWizard, 'tracking': TrackingWizard}.get(stage, Wizard)
            window = window_type('wizard.xml', ROOT, 'Default', '1080i')
            window.configure(stage, mode, choices, catalog)
            window.auth_index = tracking_index if stage == 'tracking' else auth_index
            window.flavor_index = flavor_index
            window.menu_choices = menu_choices
            window.doModal()
            result, mode = window.result, window.mode
            if stage == 'tracking':
                tracking_index = window.auth_index
            else:
                auth_index = window.auth_index
            flavor_index = window.flavor_index
            del window
            save_state(mode, choices)
            if result == 'exit':
                break
            if result == 'back':
                stage = {'tracking': 'menus', 'menus': 'flavor', 'flavor': 'authorize' if mode == 'debrid' else 'addons', 'authorize': 'addons', 'addons': 'source'}.get(stage, 'source')
            elif result == 'flavor':
                if stage == 'addons' and not recovery_checked:
                    recovery_checked = check_saved_logins(monitor)
                    if not recovery_checked:
                        continue
                stage = 'flavor'
            elif result == 'menus':
                stage = 'menus'
            elif result == 'tracking':
                # Commit the flavor before any tracking action can restart Kodi.
                try:
                    apply_flavor(flavors_for(mode)[flavor_index], menu_choices.get(flavors_for(mode)[flavor_index]['id'], []), refresh=False)
                except (OSError, ValueError, ET.ParseError) as exc:
                    xbmcgui.Dialog().ok('Could not apply Home menus', str(exc))
                    stage = 'menus'
                    continue
                # A separate script owns the refresh and reopens only the final page.
                schedule_tracking_resume(mode, choices, flavor_index, menu_choices)
                break
            elif result == 'authorize':
                if not recovery_checked:
                    recovery_checked = check_saved_logins(monitor)
                    if not recovery_checked:
                        continue
                stage = 'authorize'
            elif result == 'view_status':
                if not launch_authorization({'action': 'wizardStatus'}, monitor):
                    break
            elif result == 'service':
                entry = TRACKING_SERVICES[tracking_index] if stage == 'tracking' else SERVICES[auth_index]
                if not launch_authorization(entry, monitor):
                    break
                # Keep the current authorization page after returning.
            elif result == 'finish':
                break
            elif result == 'next':
                stage = 'addons'
            elif result == 'install':
                selected = pending_addons(catalog[mode], choices[mode])
                if not selected:
                    recovery_checked = check_saved_logins(monitor)
                    stage = ('authorize' if mode == 'debrid' else 'flavor') if recovery_checked else 'addons'
                    continue
                outcomes = []
                progress = xbmcgui.DialogProgressBG()
                progress.create('Xenon 2 Setup', 'Preparing selected add-ons')
                try:
                    for i, entry in enumerate(selected):
                        if monitor.abortRequested():
                            break
                        progress.update(int(100 * i / len(selected)), 'Xenon 2 Setup',
                                        '%d/%d: Installing %s' % (i + 1, len(selected), entry['name']))
                        outcome = install_one(entry['id'], monitor, addon_name=entry['name'])
                        outcomes.append({'id': entry['id'], 'name': entry['name'], 'status': outcome})
                finally:
                    progress.close()
                save_state(mode, choices, outcomes)
                if monitor.abortRequested():
                    break
                all_ready = len(outcomes) == len(selected) and all(
                    o['status'] in ('Ready', 'Already enabled') for o in outcomes)
                text = '\n'.join('%s: %s' % (o['name'], o['status']) for o in outcomes)
                if mode == 'debrid':
                    text += '\n\nContinue to authorize your services with ReAuthorize.'
                if all_ready:
                    xbmc.executebuiltin('Skin.SetString(Xenon2.Setup.LinkMode,%s)' % mode)
                    xbmc.executebuiltin('Skin.SetBool(Xenon2.Setup.AddonsComplete)')
                    # Add-on installation completion is separate from service authorization.
                    xbmcgui.Dialog().ok('Add-on setup complete', text)
                    recovery_checked = check_saved_logins(monitor)
                    if not recovery_checked:
                        stage = 'addons'
                        continue
                    if mode == 'debrid':
                        stage = 'authorize'
                        continue
                    stage = 'flavor'
                    continue
                xbmcgui.Dialog().ok('Review installation results', text + '\n\nReturning to your selections. Check repositories or retry. An unconfirmed installation may still finish in Kodi.')
    except Exception as exc:
        xbmc.log('Xenon 2 Setup: %s' % exc, xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Xenon 2 Setup', 'The wizard could not finish. See the Kodi log for details.')
    finally:
        home.clearProperty(lock)


if __name__ == '__main__':
    run()
