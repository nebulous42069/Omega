from functools import cached_property

from resources.lib.common import tools
from resources.lib.modules.globals import g


class Menus:
    def __init__(self):
        self.view_type = g.CONTENT_MENU

    @cached_property
    def torrent_assist(self):
        from resources.lib.database.torrentAssist import TorrentAssist

        return TorrentAssist()

    def home(self):
        g.add_directory_item(
            g.get_language_string(30219),
            action='cacheAssistStatus',
            menu_item=g.create_icon_dict("cloud_files", g.ICONS_PATH),
        )
        if g.get_bool_setting('premiumize.enabled'):
            g.add_directory_item(
                g.get_language_string(30220),
                action='premiumize_transfers',
                menu_item=g.create_icon_dict("premiumize", g.ICONS_PATH),
            )
        if g.get_bool_setting('realdebrid.enabled'):
            g.add_directory_item(
                g.get_language_string(30221),
                action='realdebridTransfers',
                menu_item=g.create_icon_dict("real_debrid", g.ICONS_PATH),
            )
        if g.get_bool_setting('alldebrid.enabled'):
            g.add_directory_item(
                "Current AllDebrid Transfers",
                action='alldebridTransfers',
                menu_item=g.create_icon_dict("all_debrid", g.ICONS_PATH),
            )
        if g.get_bool_setting('torbox.enabled'):
            g.add_directory_item(
                "Current TorBox Transfers",
                action='torboxTransfers',
                menu_item=g.create_icon_dict("torbox", g.ICONS_PATH),
            )
        if g.get_bool_setting('debridlink.enabled'):
            g.add_directory_item(
                "Current Debrid-Link Transfers",
                action='debridlinkTransfers',
                menu_item=g.create_icon_dict("cloud", g.ICONS_PATH),
            )
        if g.get_bool_setting('offcloud.enabled'):
            g.add_directory_item(
                "Current Offcloud Transfers",
                action='offcloudTransfers',
                menu_item=g.create_icon_dict("offcloud", g.ICONS_PATH),
            )
        g.add_directory_item(
            "Clear All Debrid Transfers",
            action='clearAllDebridTransfers',
            menu_item=g.create_icon_dict("clear", g.ICONS_PATH),
        )
        g.add_directory_item(
            "Clear All Debrid Cloud Files",
            action='clearAllDebridCloudFiles',
            menu_item=g.create_icon_dict("clear", g.ICONS_PATH),
        )
        g.close_directory(self.view_type)

    def get_assist_torrents(self):
        g.add_directory_item(g.get_language_string(30222), action='nonActiveAssistClear')
        torrent_list = self.torrent_assist.get_assist_torrents()
        if torrent_list is not None:

            for i in torrent_list:
                debrid = tools.shortened_debrid(i['provider'])
                title = g.color_string(f"{debrid} - {i['status'].title()} - {i['progress']}% : {i['release_title']}")
                g.add_directory_item(title, is_playable=False, is_folder=False)

        g.close_directory(self.view_type)

    def assist_non_active_clear(self):
        import xbmcplugin
        self.torrent_assist.clear_non_active_assist()
        xbmcplugin.endOfDirectory(g.PLUGIN_HANDLE, succeeded=False, cacheToDisc=False)

    def list_premiumize_transfers(self):
        from resources.lib.debrid import premiumize

        transfer_list = premiumize.Premiumize().list_transfers()
        if len(transfer_list['transfers']) == 0 or "transfers" not in transfer_list:
            g.close_directory(self.view_type)
            return
        for i in transfer_list['transfers']:
            title = "{} - {}% : {}".format(  # sourcery skip: use-fstring-for-formatting
                g.color_string(i['status'].title().title()),
                str(i['progress'] * 100),
                f"{i['name'][:50]}..." if len(i['name']) > 50 else i['name'],
            )
            g.add_directory_item(
                title, is_playable=False, is_folder=False, menu_item=g.create_icon_dict("premiumize", g.ICONS_PATH)
            )
        g.close_directory(self.view_type)

    def list_rd_transfers(self):
        from resources.lib.debrid import real_debrid

        transfer_list = real_debrid.RealDebrid().list_torrents()
        if len(transfer_list) == 0:
            g.close_directory(self.view_type)
            return
        for i in transfer_list:
            title = "{} - {}% : {}".format(  # sourcery skip: use-fstring-for-formatting
                g.color_string(i['status'].title()),
                str(i['progress']),
                f"{i['filename'][:50]}..." if len(i['filename']) > 50 else i['filename'],
            )
            g.add_directory_item(
                title, is_playable=False, is_folder=False, menu_item=g.create_icon_dict("real_debrid", g.ICONS_PATH)
            )
        g.close_directory(self.view_type)

    def list_ad_transfers(self):
        from resources.lib.debrid import all_debrid

        transfer_list = all_debrid.AllDebrid().saved_magnets()
        if not isinstance(transfer_list, list) or len(transfer_list) == 0:
            g.close_directory(self.view_type)
            return
        for i in transfer_list:
            status = i.get('status', 'Unknown')
            progress = i.get('downloaded', 0)
            size = i.get('size', 0)
            if size and size > 0:
                progress = min(int((progress / size) * 100), 100)
            else:
                progress = 100 if status == 'Ready' else 0
            name = i.get('filename', i.get('hash', 'Unknown'))
            title = "{} - {}% : {}".format(
                g.color_string(str(status).title()),
                str(progress),
                f"{name[:50]}..." if len(name) > 50 else name,
            )
            g.add_directory_item(
                title, is_playable=False, is_folder=False,
                menu_item=g.create_icon_dict("all_debrid", g.ICONS_PATH)
            )
        g.close_directory(self.view_type)

    def list_tb_transfers(self):
        from resources.lib.debrid import torbox

        transfer_list = torbox.TorBox().list_torrents()
        if not isinstance(transfer_list, list) or len(transfer_list) == 0:
            g.close_directory(self.view_type)
            return
        for i in transfer_list:
            progress = int(i.get('progress', 0) * 100)
            name = i.get('name', 'Unknown')
            title = "{} - {}% : {}".format(
                g.color_string(i.get('download_state', '').title()),
                str(progress),
                f"{name[:50]}..." if len(name) > 50 else name,
            )
            g.add_directory_item(title, is_playable=False, is_folder=False,
                                 menu_item=g.create_icon_dict("torbox", g.ICONS_PATH))
        g.close_directory(self.view_type)

    def list_dl_transfers(self):
        from resources.lib.debrid import debrid_link

        transfer_list = debrid_link.DebridLink().list_torrents()
        if not isinstance(transfer_list, list) or len(transfer_list) == 0:
            g.close_directory(self.view_type)
            return
        for i in transfer_list:
            status = i.get('status', 0)
            # Debrid-Link uses numeric status: 100 = completed
            if isinstance(status, (int, float)):
                progress = min(int(status), 100)
                status_label = "Completed" if status >= 100 else "Downloading"
            else:
                progress = 100 if status == "downloaded" else 0
                status_label = str(status).title()
            name = i.get('name', 'Unknown')
            title = "{} - {}% : {}".format(
                g.color_string(status_label),
                str(progress),
                f"{name[:50]}..." if len(name) > 50 else name,
            )
            g.add_directory_item(title, is_playable=False, is_folder=False,
                                 menu_item=g.create_icon_dict("cloud", g.ICONS_PATH))
        g.close_directory(self.view_type)

    def clear_all_transfers(self):
        """Delete all transfers/torrents across all enabled debrid services."""
        import xbmcgui
        import xbmcplugin

        try:
            if not xbmcgui.Dialog().yesno(
                g.ADDON_NAME,
                "Delete ALL transfers from ALL enabled debrid services?\n\n"
                "This cannot be undone.",
            ):
                return

            progress = xbmcgui.DialogProgress()
            progress.create(g.ADDON_NAME, "Clearing debrid transfers...")
            total_deleted = 0
            errors = []

            services = []
            if g.get_bool_setting('premiumize.enabled'):
                services.append(('Premiumize', self._clear_pm_transfers))
            if g.get_bool_setting('realdebrid.enabled'):
                services.append(('Real-Debrid', self._clear_rd_transfers))
            if g.get_bool_setting('alldebrid.enabled'):
                services.append(('AllDebrid', self._clear_ad_transfers))
            if g.get_bool_setting('torbox.enabled'):
                services.append(('TorBox', self._clear_tb_transfers))
            if g.get_bool_setting('debridlink.enabled'):
                services.append(('Debrid-Link', self._clear_dl_transfers))
            if g.get_bool_setting('offcloud.enabled'):
                services.append(('Offcloud', self._clear_oc_transfers))

            for idx, (name, func) in enumerate(services):
                if progress.iscanceled():
                    break
                pct = int((idx / max(len(services), 1)) * 100)
                progress.update(pct, f"Clearing {name} transfers...")
                try:
                    count = func()
                    total_deleted += count
                    g.log(f"Cleared {count} transfers from {name}", "info")
                except Exception as e:
                    errors.append(f"{name}: {e}")
                    g.log(f"Error clearing {name} transfers: {e}", "error")

            progress.close()
            msg = f"Deleted {total_deleted} transfers."
            if errors:
                msg += f"\n\nErrors: {', '.join(errors)}"
            xbmcgui.Dialog().ok(g.ADDON_NAME, msg)
        finally:
            xbmcplugin.endOfDirectory(g.PLUGIN_HANDLE, succeeded=False, cacheToDisc=False)

    def clear_all_cloud_files(self):
        """Delete all cloud files/items across all enabled debrid services."""
        import xbmcgui
        import xbmcplugin

        try:
            if not xbmcgui.Dialog().yesno(
                g.ADDON_NAME,
                "Delete ALL cloud files from ALL enabled debrid services?\n\n"
                "This includes torrents, downloads, and saved links.\n"
                "This cannot be undone.",
            ):
                return

            progress = xbmcgui.DialogProgress()
            progress.create(g.ADDON_NAME, "Clearing debrid cloud files...")
            total_deleted = 0
            errors = []

            services = []
            if g.get_bool_setting('premiumize.enabled'):
                services.append(('Premiumize', self._clear_pm_cloud))
            if g.get_bool_setting('realdebrid.enabled'):
                services.append(('Real-Debrid', self._clear_rd_cloud))
            if g.get_bool_setting('alldebrid.enabled'):
                services.append(('AllDebrid', self._clear_ad_cloud))
            if g.get_bool_setting('torbox.enabled'):
                services.append(('TorBox', self._clear_tb_cloud))
            if g.get_bool_setting('debridlink.enabled'):
                services.append(('Debrid-Link', self._clear_dl_cloud))
            if g.get_bool_setting('offcloud.enabled'):
                services.append(('Offcloud', self._clear_oc_cloud))

            for idx, (name, func) in enumerate(services):
                if progress.iscanceled():
                    break
                pct = int((idx / max(len(services), 1)) * 100)
                progress.update(pct, f"Clearing {name} cloud files...")
                try:
                    count = func()
                    total_deleted += count
                    g.log(f"Cleared {count} cloud files from {name}", "info")
                except Exception as e:
                    errors.append(f"{name}: {e}")
                    g.log(f"Error clearing {name} cloud files: {e}", "error")

            progress.close()
            msg = f"Deleted {total_deleted} cloud files."
            if errors:
                msg += f"\n\nErrors: {', '.join(errors)}"
            xbmcgui.Dialog().ok(g.ADDON_NAME, msg)
        finally:
            xbmcplugin.endOfDirectory(g.PLUGIN_HANDLE, succeeded=False, cacheToDisc=False)

    # ── Per-service transfer clear ────────────────────────────────────────

    @staticmethod
    def _clear_pm_transfers():
        from resources.lib.debrid.premiumize import Premiumize
        pm = Premiumize()
        transfers = pm.list_transfers().get('transfers', [])
        for t in transfers:
            pm.delete_transfer(t['id'])
        return len(transfers)

    @staticmethod
    def _clear_rd_transfers():
        from resources.lib.debrid.real_debrid import RealDebrid
        rd = RealDebrid()
        torrents = rd.list_torrents() or []
        for t in torrents:
            rd.delete_torrent(t['id'])
        return len(torrents)

    @staticmethod
    def _clear_ad_transfers():
        from resources.lib.debrid.all_debrid import AllDebrid
        ad = AllDebrid()
        magnets = ad.saved_magnets()
        for m in magnets:
            ad.delete_magnet(m.get('id'))
        return len(magnets)

    @staticmethod
    def _clear_tb_transfers():
        from resources.lib.debrid.torbox import TorBox
        tb = TorBox()
        torrents = tb.list_torrents() or []
        for t in torrents:
            tb.delete_torrent(t.get('id'))
        return len(torrents)

    @staticmethod
    def _clear_dl_transfers():
        from resources.lib.debrid.debrid_link import DebridLink
        dl = DebridLink()
        torrents = dl.list_torrents() or []
        for t in torrents:
            dl.delete_torrent(t.get('id'))
        return len(torrents)

    # ── Per-service cloud file clear ──────────────────────────────────────

    @staticmethod
    def _clear_pm_cloud():
        from resources.lib.debrid.premiumize import Premiumize
        pm = Premiumize()
        files = pm.list_folder_all()
        for f in files:
            pm.delete_item(f['id'])
        return len(files)

    @staticmethod
    def _clear_rd_cloud():
        from resources.lib.debrid.real_debrid import RealDebrid
        rd = RealDebrid()
        count = 0
        # Delete all torrents (cloud storage)
        torrents = rd.list_torrents() or []
        for t in torrents:
            rd.delete_torrent(t['id'])
        count += len(torrents)
        # Delete all downloads (unrestricted links)
        downloads = rd.list_downloads()
        for d in downloads:
            rd.delete_download(d['id'])
        count += len(downloads)
        return count

    @staticmethod
    def _clear_ad_cloud():
        from resources.lib.debrid.all_debrid import AllDebrid
        ad = AllDebrid()
        count = 0
        # Delete all magnets
        magnets = ad.saved_magnets()
        for m in magnets:
            ad.delete_magnet(m.get('id'))
        count += len(magnets)
        # Delete all saved links
        links_data = ad.saved_links()
        links = links_data.get('links', []) if isinstance(links_data, dict) else []
        for link in links:
            link_url = link.get('link', '')
            if link_url:
                ad.delete_link(link_url)
        count += len(links)
        return count

    @staticmethod
    def _clear_tb_cloud():
        from resources.lib.debrid.torbox import TorBox
        tb = TorBox()
        count = 0
        # Torrents
        torrents = tb.list_torrents() or []
        for t in torrents:
            tb.delete_torrent(t.get('id'))
        count += len(torrents)
        return count

    @staticmethod
    def _clear_dl_cloud():
        from resources.lib.debrid.debrid_link import DebridLink
        dl = DebridLink()
        torrents = dl.list_torrents() or []
        for t in torrents:
            dl.delete_torrent(t.get('id'))
        return len(torrents)

    def list_oc_transfers(self):
        from resources.lib.debrid.offcloud import OffCloud

        items = OffCloud().list_torrents()
        if not isinstance(items, list) or not items:
            g.close_directory(self.view_type)
            return
        for i in items:
            status = i.get('status', 'unknown')
            name = i.get('fileName', 'Unknown')
            title = "{} | [I]{}[/I]".format(
                g.color_string(status.title()),
                f"{name[:50]}..." if len(name) > 50 else name,
            )
            g.add_directory_item(
                title, is_playable=False, is_folder=False,
                menu_item=g.create_icon_dict("offcloud", g.ICONS_PATH),
            )
        g.close_directory(self.view_type)

    @staticmethod
    def _clear_oc_transfers():
        from resources.lib.debrid.offcloud import OffCloud
        oc = OffCloud()
        items = oc.list_torrents() or []
        for i in items:
            oc.delete_torrent(i.get('requestId', ''))
        return len(items)

    @staticmethod
    def _clear_oc_cloud():
        from resources.lib.debrid.offcloud import OffCloud
        oc = OffCloud()
        items = oc.list_torrents() or []
        for i in items:
            oc.delete_torrent(i.get('requestId', ''))
        return len(items)
