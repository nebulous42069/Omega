screensaver.arctic.mirage

## Package a widget path

1. Put the full widget URL on a single line in `resources/widget-path.txt` and save it as UTF-8. Use **Show saved widget path** to read the exact URL from a working installation.
2. Increase the add-on version in `addon.xml` and package the `screensaver.arctic.mirage` folder as a ZIP.
3. Publish the ZIP through your Kodi add-on repository or update channel. Kodi uses the bundled URL the next time the screensaver starts.

Both the widget picker and **View or edit widget path** write to this file when the installed add-on folder is writable. Older saved paths remain available as a fallback when the file is empty or missing.

Each update ships its own copy of the file and can replace a path entered on the device. Include the path you want devices to use in each release.
