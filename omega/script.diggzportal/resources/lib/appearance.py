import xbmcaddon


def apply_focus_appearance(window):
    """Apply the same user-selected highlight to each Portal window."""
    addon = xbmcaddon.Addon()
    colors = {'White':'FFFFFFFF','Silver':'FFAAAAAA','Red':'FFE50914','Blue':'FF2196F3','Cyan':'FF00BCD4','Green':'FF4CAF50','Gold':'FFD4AF37','Purple':'FF9C27B0','Orange':'FFFF9800','None':'00000000'}
    color = addon.getSetting('poster_border_color') or 'White'
    window.setProperty('PortalFocusGlowColor', colors.get(color, 'FFFFFFFF'))
    window.setProperty('PortalFocusGlowEnabled', 'false' if color == 'None' else 'true')
    # Buttons retain a visible navigation cue even when artwork glow is disabled.
    window.setProperty('PortalButtonGlowColor', colors.get(color, 'FFFFFFFF') if color != 'None' else 'FFFFFFFF')
    window.setProperty('PortalGlassTexture', 'thumbs/thumb_glass_noreflect.png' if addon.getSetting('poster_glass') != 'false' else 'thumbs/portal_clear.png')


TOUCH_SETTING = 'mouse_touch_support'


def touch_enabled():
    return xbmcaddon.Addon().getSettingBool(TOUCH_SETTING)


def portal_layout(filename):
    """Keep the original layout intact when optional pointer controls are disabled."""
    if touch_enabled():
        return filename.replace('script.diggzportal-', 'script.diggzportal-touch-', 1)
    return filename


def choose_touch_support():
    """Root menu shortcut to the same persistent Boolean as General settings."""
    import xbmcgui
    addon = xbmcaddon.Addon()
    current = addon.getSettingBool(TOUCH_SETTING)
    choice = xbmcgui.Dialog().select('Mouse / Touchscreen Support',
        ['Disabled (classic layout)', 'Enabled (mouse / touch controls)'],
        preselect=int(current))
    if choice not in (0, 1):
        return current
    enabled = bool(choice)
    if enabled != current:
        addon.setSettingBool(TOUCH_SETTING, enabled)
        xbmcgui.Dialog().notification('Diggz Portal',
            'Mouse / touchscreen support %s. Reopen Portal windows to apply.' %
            ('enabled' if enabled else 'disabled'), xbmcgui.NOTIFICATION_INFO)
    return enabled
