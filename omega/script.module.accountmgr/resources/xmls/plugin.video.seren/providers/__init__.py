import os
from resources.lib.modules.globals import g
from resources.lib.database.providerCache import ProviderCache


def _is_valid_provider_dir(name):
    dir_path = os.path.join(data_path, name)
    try:
        if not os.path.isdir(dir_path):
            return False
        if name.startswith('__'):
            return False

        return True

    except Exception:
        return False


data_path = os.path.join(g.ADDON_USERDATA_PATH, 'providers')
provider_packages = [name for name in os.listdir(data_path) if _is_valid_provider_dir(name)]
providerCache = ProviderCache()

provider_types = (
    ('hosters', 'get_hosters'),
    ('torrent', 'get_torrent'),
    ('adaptive', 'get_adaptive'),
    ('direct', 'get_direct'),
)


def _is_provider_enabled(provider_name, package, statuses):
    return True if len(
        [i for i in statuses if i['provider_name'] == provider_name and i['package'] == package]) else False


def _get_providers(language, status=False):
    provider_store = {
        'hosters': [],
        'torrent': [],
        'adaptive': [],
        'direct': [],
    }
    for package in provider_packages:
        providers_path = 'providers.%s.%s' % (package, language)
        provider_list = __import__(providers_path, fromlist=[''])
        for provider_type in provider_types:
            for i in getattr(provider_list, provider_type[1], lambda: [])():
                if status is not False and not _is_provider_enabled(i, package, status):
                    continue

                provider_store[provider_type[0]].append(('{}.{}'.format(providers_path, provider_type[0]), i, package))

    return provider_store


def get_relevant(language):
    # Get enabled providers
    provider_status = [i for i in providerCache.get_providers() if i['country'] == language]
    provider_status = [i for i in provider_status if i['status'] == 'enabled']

    return _get_providers(language, provider_status)


def get_all(language):
    return _get_providers(language)
