"""Embedded ReAuthorize launcher. Runs inside Xenon 2; no ReAuthorize add-on registration."""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'runtime'))
import embedded


def parse_args(arguments):
    params = {}
    for argument in arguments:
        for piece in argument.split('&'):
            key, sep, value = piece.partition('=')
            if sep:
                params[key.strip()] = value
            elif piece:
                params[piece] = 'true'
    return params


def run():
    params = parse_args(sys.argv[1:])
    job = params.pop('job', '')
    if job and not job.isalnum():
        raise ValueError('Invalid job identifier')
    is_service = params.pop('service', '') == 'true'
    wizard = params.pop('wizard', '') == 'true'
    window = embedded.GUI.Window(10000)
    property_name = 'Xenon.ReAuthorize.Job.' + job
    if job:
        window.setProperty(property_name, 'running')
    try:
        # Two credential renewal services sharing one profile must not run together.
        if embedded.REAL_XBMC.getCondVisibility('System.AddonIsEnabled(script.module.reauthorize)'):
            if not is_service:
                embedded.GUI.Dialog().ok('Embedded ReAuthorize',
                    'Disable the standalone ReAuthorize add-on before using the embedded version. Your saved sign-ins are kept.')
            raise RuntimeError('Standalone ReAuthorize is still enabled')
        if is_service:
            try:
                with embedded.file_lock(os.path.join(embedded.profile(), 'embedded-service.lock'), blocking=False):
                    embedded.install(suppress_settings=True, service=True)
                    import runpy
                    runpy.run_path(os.path.join(embedded.OWN[embedded.MAIN_ID], 'lib', 'startup.py'), run_name='__main__')
            except (BlockingIOError, PermissionError):
                pass
        else:
            embedded.install(suppress_settings=wizard)
            # Serialize authorizations and management actions, without blocking renewals.
            with embedded.file_lock(os.path.join(embedded.profile(), 'embedded-action.lock')):
                if 'core_query' in params:
                    embedded.run_core(params['core_query'])
                else:
                    embedded.run_main(['%s=%s' % pair for pair in params.items()])
        if job:
            window.setProperty(property_name, 'done')
    except SystemExit as exc:
        if job:
            window.setProperty(property_name, 'done' if exc.code in (None, 0) else 'error')
    except Exception as exc:
        # No credential values or request URLs in adapter diagnostics.
        embedded.report_error(exc, 'launcher')
        if job:
            window.setProperty(property_name, 'error')
        elif not is_service:
            embedded.GUI.Dialog().ok('Embedded ReAuthorize', 'The action could not finish. Check the Kodi log.')


if __name__ == '__main__':
    run()
