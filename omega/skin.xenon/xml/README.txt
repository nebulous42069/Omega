Xenon LanguageInvoker workaround - content gate, preserve widget selector

Copy the files in this zip over the matching files in your skin's xml folder.

Changes from the previous content-gate build:
- Removed SetProperty(WidgetSet,noop,Home).
- Removed the XenonReprimePluginWidgets alarm that rewrote WidgetSet.
- SafeCustomWidgetContent now uses Container(9000).ListItem.Property(WidgetSet), matching the skin's original widget-selection model.
- The suspend timer remains 8 seconds and still clears Skin.HasSetting(SuspendPluginWidgets).

Goal:
Keep plugin:// widget content blocked briefly after returning from plugin directories without clearing/resetting the current selected widget used by the widget selector.
