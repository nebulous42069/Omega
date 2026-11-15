"""Standalone Kodi entry point for Diggz Account Manager and wizard jobs."""
import os
import sys

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


def run(arguments=None, *, is_service=False):
    params = parse_args(sys.argv[1:] if arguments is None else arguments)
    job = params.pop('job', '')
    if job and not job.isalnum():
        raise ValueError('Invalid job identifier')
    params.pop('service', None)  # Kodi owns the background service lifecycle.
    wizard = params.pop('wizard', '') == 'true'
    window = embedded.GUI.Window(10000)
    property_name = 'Xenon.ReAuthorize.Job.' + job
    if job:
        window.setProperty(property_name, 'running')
    try:
        if is_service:
            try:
                with embedded.file_lock(os.path.join(embedded.profile(), 'embedded-service.lock'), blocking=False):
                    embedded.install(suppress_settings=True)
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
            embedded.GUI.Dialog().ok('Diggz Account Manager', 'The action could not finish. Check the Kodi log.')


if __name__ == '__main__':
    run()
