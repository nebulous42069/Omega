import xbmcaddon

def main():
    addon = xbmcaddon.Addon()
    if addon.getSettingBool('auto_clean_cache_bool'):
        from resources.lib import Utils
        Utils.db_delete_expired(connection=Utils.db_con)


if __name__ == '__main__':
    main()
