# Xenon embedded integration; GPL-3.0-or-later.
"""Xenon-styled management window. Authorization actions run after it closes."""
import os
import xml.etree.ElementTree as ET
import xbmcgui
import embedded as engine

BACK_ACTIONS = (9, 10, 92, 216, 247)


def describe(row, section):
    label = engine.text_label(row.get('label'))
    if row.get('help'):
        return engine.text_label(row.get('help'))
    lower = label.lower()
    if 'authorize' in lower or 'sign in' in lower:
        return 'Connect this service using its sign-in instructions. ReAuthorize sends a changed sign-in to supported installed add-ons.'
    if 'revoke' in lower or 'sign out' in lower:
        return 'Remove this service authorization using ReAuthorize. Read the confirmation before proceeding.'
    if 'sync' in lower:
        return 'Send the saved service settings to supported installed add-ons.'
    if 'view authorization' in lower:
        return 'View the installed add-ons using this service.'
    if row.get('type') == 'bool':
        return 'Select to turn this setting on or off. Changes save immediately.'
    if row.get('enable', '').lower() == 'false':
        return 'Account information maintained by ReAuthorize. ' + (section or label)
    if row.get('type') in ('folder', 'file'):
        return 'Select to choose a location. Changes save immediately.'
    if row.get('type') in ('sep', 'lsep'):
        return label
    return (section + ' - ' if section and section != label else '') + label


def interactive(row):
    return bool(row['enabled'] and row['kind'] != 'heading' and
                (row['xml'].get('action') or row['xml'].get('id')))


def selectable_index(rows, start, direction=1):
    for index in range(start, len(rows) if direction > 0 else -1, direction):
        if 0 <= index < len(rows) and interactive(rows[index]):
            return index
    return None


def build_rows(category, addon):
    definitions = list(category.findall('setting'))
    result = []
    section = ''
    for index, row in enumerate(definitions):
        if not row.get('label') or not engine.setting_condition(row.get('visible'), definitions, index, addon):
            continue
        label = engine.text_label(row.get('label'))
        kind = row.get('type', 'text')
        if kind == 'sep':
            continue
        if kind == 'lsep':
            section = label
            result.append({'xml': row, 'kind': 'heading', 'label': label, 'value': '',
                           'enabled': False, 'help': label, 'key': 'heading:' + label})
            continue
        enabled = engine.setting_condition(row.get('enable'), definitions, index, addon)
        value = addon.getSetting(row.get('id')) if row.get('id') else ''
        if 'hidden' in row.get('option', ''):
            value = '********' if value else ''
        elif kind == 'bool':
            value = 'On' if addon.getSettingBool(row.get('id')) else 'Off'
        elif row.get('action'):
            value = ''
        if not enabled:
            label = '[COLOR FF9DA8B4]' + label + '[/COLOR]'
        result.append({'xml': row, 'kind': kind, 'label': label, 'value': value,
                       'enabled': enabled, 'help': describe(row, section),
                       'key': row.get('id') or row.get('action') or label})
    return result


def edit_setting(row, addon):
    key = row.get('id')
    if not key:
        return
    kind, current = row.get('type'), addon.getSetting(key)
    dialog = xbmcgui.Dialog()
    label = engine.text_label(row.get('label'))
    if kind == 'bool':
        addon.setSetting(key, current.lower() != 'true')
    elif kind in ('select', 'enum', 'labelenum'):
        values = row.get('values', '').split('|')
        if row.get('lvalues'):
            values = [addon.getLocalizedString(int(v)) for v in row.get('lvalues').split('|')]
        choice = dialog.select(label, values)
        if choice >= 0:
            addon.setSetting(key, str(choice) if kind == 'enum' else values[choice])
    elif kind in ('folder', 'file'):
        value = dialog.browseSingle(0 if kind == 'folder' else 1, label, 'files', defaultt=current)
        if value:
            addon.setSetting(key, value)
    else:
        option = xbmcgui.ALPHANUM_HIDE_INPUT if 'hidden' in row.get('option', '') else 0
        value = dialog.input(label, current, option=option)
        if value != '':
            addon.setSetting(key, value)


class SettingsWindow(xbmcgui.WindowXMLDialog):
    def configure(self, categories, state):
        self.categories = categories
        self.state = state
        self.category = -1
        self.rows = []
        self.request = None
        self.addon = engine.Addon()

    def onInit(self):
        self.getControl(20).setLabel('ReAuthorize')
        listing = self.getControl(100)
        listing.reset()
        for category in self.categories:
            listing.addItem(xbmcgui.ListItem(label=engine.text_label(category.get('label'))))
        index = max(0, min(len(self.categories) - 1, self.state.get('category', 0)))
        listing.selectItem(index)
        self.load_category(index, self.state.get('row', 0), self.state.get('key'))
        self.setFocusId(200 if self.state.get('focus') == 'settings' and self.rows else 100)

    def load_category(self, index, row_index=0, key=None):
        if not 0 <= index < len(self.categories):
            return
        self.category = index
        self.getControl(22).setLabel(engine.text_label(self.categories[index].get('label')))
        self.rows = build_rows(self.categories[index], self.addon)
        listing = self.getControl(200)
        listing.reset()
        for row in self.rows:
            item = xbmcgui.ListItem(label=row['label'], label2=row['value'])
            item.setProperty('kind', row['kind'])
            item.setProperty('interactive', 'true' if interactive(row) else 'false')
            item.setProperty('wide', 'true' if row['xml'].get('action') or not row['value'] else 'false')
            item.setProperty('focus_label', engine.text_label(row['xml'].get('label')))
            item.setProperty('help', row['help'])
            item.setProperty('checked', 'true' if row['kind'] == 'bool' and self.addon.getSettingBool(row['xml'].get('id')) else 'false')
            listing.addItem(item)
        if key:
            row_index = next((i for i, row in enumerate(self.rows) if row['key'] == key), row_index)
        if self.rows:
            start = max(0, min(len(self.rows) - 1, row_index))
            selected = selectable_index(self.rows, start)
            if selected is None:
                selected = selectable_index(self.rows, start, -1)
            listing.selectItem(selected if selected is not None else 0)
        self.getControl(23).setLabel('%d settings' % sum(r['kind'] != 'heading' for r in self.rows))

    def remember(self):
        row_index = self.getControl(200).getSelectedPosition() if self.rows else 0
        self.state.update(category=max(0, self.category), row=max(0, row_index), focus='settings' if self.getFocusId() in (200, 210) else 'categories')
        self.state['key'] = self.rows[row_index]['key'] if 0 <= row_index < len(self.rows) else None

    def sync_category(self):
        index = self.getControl(100).getSelectedPosition()
        if index != self.category:
            self.load_category(index)

    def ensure_interactive(self, direction=1, leave_boundary=False):
        listing = self.getControl(200)
        start = max(0, listing.getSelectedPosition())
        selected = selectable_index(self.rows, start, direction)
        if selected is None and not leave_boundary:
            selected = selectable_index(self.rows, start, -direction)
        if selected is None:
            self.setFocusId(900 if direction > 0 else 100)
        elif selected != start:
            listing.selectItem(selected)

    def onFocus(self, control_id):
        if control_id in (100, 200):
            self.sync_category()

    def onAction(self, action):
        if action.getId() in BACK_ACTIONS:
            if self.getFocusId() in (200, 210):
                self.setFocusId(100)
            else:
                self.remember()
                self.close()
            return
        # Kodi sends mouse movement/hover actions too. Never reposition its
        # selection for those: doing so fights the hovered row every frame.
        action_id = action.getId()
        if self.getFocusId() == 100:
            self.sync_category()
        elif self.getFocusId() == 200 and action_id in (3, 4, 5, 6, 104, 105):
            direction = -1 if action_id in (3, 5, 104) else 1
            self.ensure_interactive(direction, leave_boundary=True)

    def onClick(self, control_id):
        if control_id in (900, 901):
            self.remember()
            self.close()
        elif control_id == 100:
            self.sync_category()
            if self.rows:
                self.setFocusId(200)
        elif control_id == 200 and self.rows:
            index = self.getControl(200).getSelectedPosition()
            if not 0 <= index < len(self.rows):
                return
            row = self.rows[index]
            if not interactive(row):
                return
            self.remember()
            if row['xml'].get('action'):
                # Upstream actions close modal windows before opening their own.
                self.request = row['xml'].get('action')
                self.close()
            else:
                edit_setting(row['xml'], self.addon)
                self.load_category(self.category, index, row['key'])
