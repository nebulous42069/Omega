import abc
import json

import xbmcgui

from . import set_info_properties
from resources.lib.common import tools
from resources.lib.common.source_utils import INFO_STRUCT
from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules.globals import g

# Quality → Color mapping for color-coded quality tags
# Colors chosen to complement Seren's dark UI theme:
#   4K:    gold       — premium, stands out
#   1080p: limegreen  — high quality, positive
#   720p:  deepskyblue — decent, matches Seren accent
#   SD:    darkgray   — low priority, de-emphasized
QUALITY_COLORS = {
    "4K": "gold",
    "1080p": "limegreen",
    "720p": "deepskyblue",
    "SD": "darkgray",
}


def _get_quality_color(quality):
    """Return the color name for a given quality string.
    Falls back to the user's accent color if quality colors are disabled
    or the quality is unknown."""
    if not g.get_bool_setting("general.qualityColors", True):
        return g.get_user_text_color()
    return QUALITY_COLORS.get(quality, g.get_user_text_color())


class SourceWindow(BaseWindow):
    """
    Common window class for source selection type windows.
    """

    def __init__(self, xml_file, location, item_information=None, sources=None):
        super().__init__(xml_file, location, item_information=item_information)
        self.sources = sources or []
        self.item_information = item_information
        self.display_list = None
        self._all_sources = None
        self._filter_applied = False
        self._remember_filter = g.get_bool_setting("general.rememberfilter", False)

    def onInit(self):
        self.display_list = self.getControlList(1000)
        if self._all_sources is None:
            self._all_sources = list(self.sources)

        # Auto-apply remembered filter if enabled
        if self._remember_filter and not self._filter_applied:
            self._restore_last_filter()

        self.populate_sources_list()
        self._update_filter_label()

        self.set_default_focus(self.display_list, 2999, control_list_reset=True)
        super().onInit()

    def populate_sources_list(self):
        self.display_list.reset()

        for i in self.sources:
            menu_item = xbmcgui.ListItem(label=f"{i['release_title']}")
            provider_imports = i.get("provider_imports", [])
            source_icon = self.provider_class.get_icon(provider_imports)
            if source_icon is not None:
                menu_item.setProperty("source.icon", source_icon)

            for info in i:
                try:
                    if info == "info":
                        continue
                    value = i[info]
                    if info == "size":
                        value = tools.source_size_display(value)
                    menu_item.setProperty(info, str(value).replace("_", " "))
                except UnicodeEncodeError:
                    menu_item.setProperty(info, i[info])

            # Ensure "(Local Cache)" label is displayed for sources from local torrent cache.
            # This is the final safety net — no threading or overwrites can affect it here.
            if i.get("_from_local_cache"):
                provider = i.get("provider", "")
                if "(Local Cache)" not in provider:
                    provider = f"{provider} (Local Cache)"
                menu_item.setProperty("provider", str(provider).replace("_", " "))

            # Append sub-provider label if present (e.g. scraper sets a sub_label
            # to distinguish an underlying indexer or source within a scraper).
            if i.get("sub_label") and not i.get("_from_local_cache"):
                provider = i.get("provider", "")
                sub = i["sub_label"]
                if f"({sub})" not in provider:
                    provider = f"{provider} ({sub})"
                menu_item.setProperty("provider", str(provider).replace("_", " "))

            # Quality color tag
            menu_item.setProperty("quality_color", _get_quality_color(i.get("quality", "SD")))

            # Inject source type tags (CACHED, SEASON, SHOW) into info set for display
            display_info = set(i.get("info", set()))
            if i.get("type") == "torrent" and i.get("debrid_provider"):
                display_info.add("CACHED")
            package = i.get("package", "single")
            if package == "season":
                display_info.add("SEASON")
            elif package == "show":
                display_info.add("SHOW")

            set_info_properties(display_info, menu_item)
            self.display_list.addItem(menu_item)

    # ── Interactive Source Filtering ──────────────────────────────────

    def _update_filter_label(self):
        """Update the filter button label based on current filter state."""
        if self._filter_applied:
            label = f"{g.get_language_string(30694)} ({len(self.sources)}/{len(self._all_sources)})"
        else:
            label = g.get_language_string(30693)
        self.setProperty("filter.label", label)

    def filter_results(self):
        """Show interactive filter dialog and apply selected filter to the source list."""
        categories = [
            (g.get_language_string(30695), "quality"),
            (g.get_language_string(30696), "provider"),
            (g.get_language_string(30697), "keyword"),
            (g.get_language_string(30698), "extra_info"),
        ]

        category_choice = xbmcgui.Dialog().contextmenu([c[0] for c in categories])
        if category_choice < 0:
            return

        filter_type = categories[category_choice][1]
        working_sources = self._all_sources if self._filter_applied else self.sources

        if filter_type == "quality":
            filtered = self._filter_by_multiselect(
                working_sources,
                lambda s: s.get("quality", "Unknown"),
                g.get_language_string(30695),
                sort_order=["4K", "1080p", "720p", "SD"],
            )
        elif filter_type == "provider":
            filtered = self._filter_by_multiselect(
                working_sources,
                lambda s: str(s.get("debrid_provider", s.get("provider", "Unknown"))).replace("_", " ").title(),
                g.get_language_string(30696),
            )
        elif filter_type == "keyword":
            filtered = self._filter_by_keyword(working_sources)
        elif filter_type == "extra_info":
            filtered = self._filter_by_extra_info(working_sources)
        else:
            return

        if filtered is None:
            return

        if not filtered:
            xbmcgui.Dialog().notification(
                g.ADDON_NAME,
                g.get_language_string(30699),
                time=2000,
            )
            return

        self._apply_filter(filtered)

    def _filter_by_multiselect(self, sources, key_func, heading, sort_order=None):
        """Filter sources by multi-selecting from unique values of a key function."""
        unique_values = []
        seen = set()
        for s in sources:
            val = key_func(s)
            if val and val not in seen:
                seen.add(val)
                unique_values.append(val)

        if sort_order:
            def sort_key(v):
                try:
                    return sort_order.index(v)
                except ValueError:
                    return len(sort_order)
            unique_values.sort(key=sort_key)
        else:
            unique_values.sort()

        if not unique_values:
            return None

        selected = xbmcgui.Dialog().multiselect(heading, unique_values)
        if selected is None:
            return None

        chosen = {unique_values[i] for i in selected}
        return [s for s in sources if key_func(s) in chosen]

    def _filter_by_keyword(self, sources):
        """Filter sources by user-entered keywords in the release title."""
        keywords = xbmcgui.Dialog().input(g.get_language_string(30700))
        if not keywords:
            return None

        keyword_list = [kw.strip().lower() for kw in keywords.split(",") if kw.strip()]
        if not keyword_list:
            return None

        return [
            s for s in sources
            if all(kw in s.get("release_title", "").lower() for kw in keyword_list)
        ]

    def _filter_by_extra_info(self, sources):
        """Filter sources by multi-selecting from available info tags."""
        all_tags = set()
        for s in sources:
            info = s.get("info", set())
            if isinstance(info, set):
                all_tags.update(info)

        if not all_tags:
            return None

        # Group by INFO_STRUCT category and sort
        ordered_tags = []
        for category in ["audiolang", "sublang", "hdrcodec", "videocodec", "misc", "audiocodec", "audiochannels"]:
            category_tags = sorted(all_tags & INFO_STRUCT.get(category, set()))
            ordered_tags.extend(category_tags)
        # Add any tags not in INFO_STRUCT
        remaining = sorted(all_tags - set(ordered_tags))
        ordered_tags.extend(remaining)

        if not ordered_tags:
            return None

        selected = xbmcgui.Dialog().multiselect(g.get_language_string(30698), ordered_tags)
        if selected is None:
            return None

        chosen = {ordered_tags[i] for i in selected}
        return [
            s for s in sources
            if chosen.issubset(s.get("info", set()))
        ]

    def _apply_filter(self, filtered_sources):
        """Apply a filtered source list, updating the display and tracking state."""
        self.sources = filtered_sources
        self._filter_applied = True
        self.populate_sources_list()
        self._update_filter_label()
        self.set_default_focus(self.display_list, 2999, control_list_reset=True)

        # Save filter state for "Remember Last Filter"
        if self._remember_filter:
            self._save_filter_state()

    def clear_filter(self):
        """Restore the full unfiltered source list."""
        if self._all_sources is not None:
            self.sources = list(self._all_sources)
        self._filter_applied = False
        self.populate_sources_list()
        self._update_filter_label()
        self.set_default_focus(self.display_list, 2999, control_list_reset=True)

        # Clear remembered filter
        if self._remember_filter:
            g.clear_runtime_setting("last_filter_state")

    def toggle_filter(self):
        """Toggle between filter and clear based on current state."""
        if self._filter_applied:
            self.clear_filter()
        else:
            self.filter_results()

    # ── Remember Last Filter ─────────────────────────────────────────

    def _save_filter_state(self):
        """Save the current filter criteria to runtime settings for next scrape."""
        try:
            # Reconstruct what the filter criteria were by comparing filtered vs all
            # Store the release titles of filtered sources as a hash set for fast restore
            filtered_titles = {s.get("release_title", "") for s in self.sources}
            state = {
                "count": len(self.sources),
                "total": len(self._all_sources) if self._all_sources else 0,
                "titles": list(filtered_titles),
            }
            g.set_runtime_setting("last_filter_state", json.dumps(state))
            g.log(
                f"Filter state saved: {state['count']}/{state['total']} sources",
                "debug",
            )
        except Exception as e:
            g.log(f"Failed to save filter state: {e}", "warning")

    def _restore_last_filter(self):
        """Restore the last filter from runtime settings if available."""
        try:
            state_json = g.get_runtime_setting("last_filter_state")
            if not state_json:
                return

            state = json.loads(state_json)
            saved_titles = set(state.get("titles", []))
            if not saved_titles:
                return

            # Apply the saved filter — keep sources whose titles match
            filtered = [s for s in self.sources if s.get("release_title", "") in saved_titles]

            if filtered and len(filtered) < len(self.sources):
                self.sources = filtered
                self._filter_applied = True
                g.log(
                    f"Restored last filter: {len(filtered)}/{len(self._all_sources)} sources",
                    "info",
                )
            else:
                # Saved filter doesn't match current sources — clear it
                g.clear_runtime_setting("last_filter_state")
        except Exception as e:
            g.log(f"Failed to restore filter state: {e}", "warning")
            g.clear_runtime_setting("last_filter_state")

    @abc.abstractmethod
    def handle_action(self, action_id, control_id=None):
        pass
