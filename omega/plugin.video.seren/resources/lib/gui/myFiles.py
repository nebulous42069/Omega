import abc
import os
from functools import cached_property

import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib.common import tools
from resources.lib.modules.globals import g


class Menus:
    def __init__(self):
        # Ordered list: (key, label, WalkerClass) — order defines menu display order
        self.providers = []
        self.providers.append(('local_downloads', 'Local Downloads', LocalFileWalker))
        if g.premiumize_enabled():
            self.providers.append(('premiumize', 'Premiumize', PremiumizeWalker))
        if g.real_debrid_enabled():
            self.providers.append(('real_debrid', 'Real-Debrid', RealDebridWalker))
        if g.all_debrid_enabled():
            self.providers.append(('all_debrid', 'AllDebrid', AllDebridWalker))
        if g.torbox_enabled():
            self.providers.append(('torbox', 'TorBox', TorBoxWalker))
        if g.debridlink_enabled():
            self.providers.append(('debrid_link', 'Debrid-Link', DebridLinkWalker))
        # Key → WalkerClass lookup used by my_files_folder / my_files_play
        self._walker = {key: walker for key, _label, walker in self.providers}

    def home(self):
        for key, label, walker in self.providers:
            args = {'debrid_provider': key, 'id': None}
            g.add_directory_item(
                label,
                action='myFilesFolder',
                action_args=args,
                menu_item=g.create_icon_dict(key, g.ICONS_PATH),
            )
        g.close_directory(g.CONTENT_MENU)

    def my_files_folder(self, args):
        if args.get('id', args.get('path')) is None:
            self._walker[args['debrid_provider']]().get_init_list()
        else:
            self._walker[args['debrid_provider']]().get_folder(args)
        g.close_directory(g.CONTENT_MENU, sort='title')

    def my_files_play(self, args):
        self._walker[args['debrid_provider']]().play_item(args)


class BaseDebridWalker:
    provider = ''

    @abc.abstractmethod
    def get_init_list(self):
        """
        Return initial listing for menu
        :return:
        """
        pass

    @abc.abstractmethod
    def _is_folder(self, list_item):
        """
        Returns True if item is a folder
        Returns False if items is a playable file_path
        :param list_item:
        :return:
        """
        pass

    @abc.abstractmethod
    def get_folder(self, list_item):
        """
        Creates new Kodi menu list from list_item
        :param list_item:
        :return:
        """
        pass

    def play_item(self, args):
        resolved_link = self.resolve_link(args)
        item = xbmcgui.ListItem(path=resolved_link)
        xbmcplugin.setResolvedUrl(g.PLUGIN_HANDLE, True, item)

    def _format_items(self, items):
        for i in items:
            i.update({'debrid_provider': self.provider})
            if self._is_folder(i):
                name = i['name']
                is_playable = False
                is_folder = True
                action = 'myFilesFolder'
            else:
                name = f"{i['name']}  ({tools.bytes_size_display(i['size'])})" if i.get("size") else i['name']
                is_folder = False
                is_playable = True
                action = 'myFilesPlay'

            i.pop('links', None)  # De-clutter our action args a bit

            g.add_directory_item(
                name,
                action=action,
                is_playable=is_playable,
                is_folder=is_folder,
                action_args=tools.construct_action_args(i),
                menu_item=g.create_icon_dict(self.provider, g.ICONS_PATH),
            )

    @abc.abstractmethod
    def resolve_link(self, args):
        """
        Returns playable link from arguments
        :param args:
        :return:
        """


class PremiumizeWalker(BaseDebridWalker):
    provider = 'premiumize'

    @cached_property
    def premiumize(self):
        from resources.lib.debrid.premiumize import Premiumize

        return Premiumize()

    def get_init_list(self):
        items = self.premiumize.list_folder('')
        self._format_items(items)

    def _is_folder(self, list_item):
        return list_item['type'] == 'folder'

    def get_folder(self, list_item):
        items = self.premiumize.list_folder(list_item['id'])
        self._format_items(items)

    def resolve_link(self, list_item):
        return list_item['link']


class RealDebridWalker(BaseDebridWalker):
    provider = 'real_debrid'

    @cached_property
    def real_debrid(self):
        from resources.lib.debrid.real_debrid import RealDebrid

        return RealDebrid()

    def get_init_list(self):
        root = self.real_debrid.list_torrents()
        items = []

        for i in root:
            if i['status'] != 'downloaded':
                continue
            item = {
                "id": i['id'],
                "name": i['filename'],
            }
            if len(i['links']) > 1:
                item['links'] = i['links']
            else:
                item['link'] = i['links'][0]
                item['size'] = i['bytes']
            items.append(item)

        self._format_items(items)

    def _is_folder(self, list_item):
        return bool(list_item.get('links'))

    def get_folder(self, list_item):
        folder = self.real_debrid.torrent_info(list_item['id'])
        files = [file for file in folder.get("files", []) if file.get("selected") == 1]
        items = []

        for p, i in enumerate(files):
            if i['selected'] != 1:
                continue
            item = {
                "name": i['path'].split('/')[-1] if i['path'].startswith('/') else i['path'],
                "link": folder['links'][p],
                "size": i.get("bytes", 0),
            }
            items.append(item)

        self._format_items(items)

    def resolve_link(self, list_item):
        return self.real_debrid.resolve_hoster(list_item['link'])


class AllDebridWalker(BaseDebridWalker):
    provider = 'all_debrid'

    @cached_property
    def all_debrid(self):
        from resources.lib.debrid.all_debrid import AllDebrid

        return AllDebrid()

    def get_init_list(self):
        root = self.all_debrid.magnet_status(None).get("magnets", [])
        if not isinstance(root, list):
            root = []
        items = []

        for i in root:
            if not (isinstance(i, dict) and i.get('status') == "Ready"):
                continue
            item = {
                "id": i.get('id'),
                "name": i.get('filename', 'Unknown'),
                "links": sorted(
                    [
                        link
                        for link in i.get('links', [])
                        if (
                            len(filenames := self._get_lowest_level_filename_for_link_files(link.get("files", []))) == 1
                            and filenames[0].endswith(g.common_video_extensions)
                        )
                    ],
                    key=lambda x: x.get('filename', ''),
                ),
            }
            if item.get("links"):
                items.append(item)

        self._format_items(items)

    def _is_folder(self, list_item):
        return bool(list_item.get("links"))

    def get_folder(self, list_item):
        status = self.all_debrid.magnet_status(list_item['id']).get("magnets", {})
        links = status.get("links", []) if isinstance(status, dict) else []
        items = []

        for l in links:
            filenames = self._get_lowest_level_filename_for_link_files(l.get("files", []))
            if not (len(filenames) == 1 and filenames[0].endswith(tuple(g.common_video_extensions))):
                continue
            item = {"name": filenames[0], "link": l.get("link"), "size": l.get("size", 0)}
            items.append(item)

        self._format_items(sorted(items, key=lambda x: x['name']))

    def _get_lowest_level_filename_for_link_files(self, files_item):
        files = []
        for file in files_item if isinstance(files_item, list) else [files_item]:
            if entities := file.get("e"):
                files.extend(self._get_lowest_level_filename_for_link_files(entities))
            else:
                files.append(file.get("n"))
        return files

    def resolve_link(self, list_item):
        return self.all_debrid.resolve_hoster(list_item['link'])


class TorBoxWalker(BaseDebridWalker):
    provider = 'torbox'

    @cached_property
    def torbox(self):
        from resources.lib.debrid.torbox import TorBox

        return TorBox()

    def get_init_list(self):
        """Show three top-level categories: Torrents, Usenet, WebDL."""
        categories = [
            {"id": "cat_torrents", "name": "Torrents", "files": True, "tb_type": "torrent"},
            {"id": "cat_usenet", "name": "Usenet", "files": True, "tb_type": "usenet"},
            {"id": "cat_webdl", "name": "Web Downloads", "files": True, "tb_type": "webdl"},
        ]
        self._format_items(categories)

    def _is_folder(self, list_item):
        return bool(list_item.get("files"))

    def get_folder(self, list_item):
        item_id = str(list_item.get("id", ""))
        tb_type = list_item.get("tb_type", "torrent")

        # Category root — list all items for this type
        if item_id == "cat_torrents":
            self._list_category(self.torbox.list_torrents(), "torrent")
        elif item_id == "cat_usenet":
            self._list_category(self.torbox.list_usenet(), "usenet")
        elif item_id == "cat_webdl":
            self._list_category(self.torbox.list_webdl(), "webdl")
        else:
            # Specific item — show its files
            self._list_files(item_id, tb_type)

    def _list_category(self, cloud_list, tb_type):
        """List completed items for a given cloud type."""
        if not isinstance(cloud_list, list):
            return
        items = []
        for t in cloud_list:
            if not t.get("download_finished"):
                continue
            item = {
                "id": t["id"],
                "name": t.get("name", "Unknown"),
                "tb_type": tb_type,
            }
            files = t.get("files", [])
            if len(files) > 1:
                item["files"] = True  # marks as folder
            elif len(files) == 1:
                f = files[0]
                item["link"] = f"{t['id']},{f['id']}"
                item["size"] = f.get("size", 0)
                item["tb_type"] = tb_type
            else:
                continue
            items.append(item)
        self._format_items(items)

    def _list_files(self, item_id, tb_type):
        """List files inside a specific torrent/usenet/webdl item."""
        if tb_type == "usenet":
            info = self.torbox.usenet_info(item_id)
        elif tb_type == "webdl":
            info = self.torbox.webdl_info(item_id)
        else:
            info = self.torbox.torrent_info(item_id)
        if not info or "files" not in info:
            return
        items = []
        for f in info["files"]:
            item = {
                "name": f.get("short_name", f.get("name", "")),
                "link": f"{item_id},{f['id']}",
                "size": f.get("size", 0),
                "tb_type": tb_type,
            }
            items.append(item)
        self._format_items(items)

    def resolve_link(self, list_item):
        tb_type = list_item.get("tb_type", "torrent")
        return self.torbox.resolve_by_type(list_item["link"], tb_type)


class DebridLinkWalker(BaseDebridWalker):
    provider = 'debrid_link'

    @cached_property
    def debrid_link(self):
        from resources.lib.debrid.debrid_link import DebridLink

        return DebridLink()

    def get_init_list(self):
        root = self.debrid_link.list_torrents()
        if not isinstance(root, list):
            return
        items = []
        for t in root:
            # Debrid-Link status: 100 = completed
            status = t.get("status")
            if not (isinstance(status, (int, float)) and status >= 100):
                if status not in ("100", "downloaded"):
                    continue
            files = t.get("files", [])
            item = {
                "id": t.get("id"),
                "name": t.get("name", "Unknown"),
            }
            if len(files) > 1:
                item["files"] = True  # marks as folder
            elif len(files) == 1:
                f = files[0]
                item["link"] = f.get("downloadUrl", "")
                item["size"] = f.get("size", 0)
            else:
                continue
            items.append(item)
        self._format_items(items)

    def _is_folder(self, list_item):
        return bool(list_item.get("files"))

    def get_folder(self, list_item):
        info = self.debrid_link.torrent_info(list_item["id"])
        if not info:
            # Fallback: re-list and find matching torrent
            torrents = self.debrid_link.list_torrents()
            if isinstance(torrents, list):
                info = next((t for t in torrents if str(t.get("id")) == str(list_item["id"])), None)
        if not info or "files" not in info:
            return
        items = []
        for f in info.get("files", []):
            item = {
                "name": f.get("name", ""),
                "link": f.get("downloadUrl", ""),
                "size": f.get("size", 0),
            }
            items.append(item)
        self._format_items(items)

    def resolve_link(self, list_item):
        return list_item.get("link", "")


class LocalFileWalker(BaseDebridWalker):
    provider = "local_downloads"
    downloads_folder = g.get_setting("download.location")

    def _get_folder_list(self, path):
        directory_listing = xbmcvfs.listdir(path)
        contents = [tools.ensure_path_is_dir(i) for i in directory_listing[0]] + list(directory_listing[1])

        return [
            {
                "name": i[:-1] if i.endswith(("\\", "/")) else i,
                "path": os.path.join(path, i),
                "size": xbmcvfs.Stat(os.path.join(path, i)).st_size(),
            }
            for i in contents
        ]

    def get_init_list(self):
        self._format_items(self._get_folder_list(self.downloads_folder))

    def _is_folder(self, list_item):
        return list_item['path'].endswith(('\\', '/'))

    def get_folder(self, list_item):
        self._format_items(self._get_folder_list(list_item['path']))

    def resolve_link(self, list_item):
        return list_item['path']
