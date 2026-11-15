from reauthorize.modules.sync import salts_sync


class Auth:
    def debridlink_auth(self):
        return salts_sync.send('debridlink')
