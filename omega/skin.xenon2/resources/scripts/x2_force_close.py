"""Immediately terminate this Kodi process. No wizard dependency.

Install in skin.xenon2/resources/scripts and launch with:
RunScript(special://skin/resources/scripts/x2_force_close.py)
Unsaved settings and in-progress writes are not preserved.
"""
import os

import xbmc
import xbmcgui


def terminate_windows(pid):
    import ctypes
    from ctypes import wintypes
    import subprocess
    try:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.argtypes = []
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel.TerminateProcess.restype = wintypes.BOOL
        if kernel.TerminateProcess(kernel.GetCurrentProcess(), 1):
            return
        raise ctypes.WinError(ctypes.get_last_error())
    except Exception as error:
        xbmc.log('[X2 Force Close] TerminateProcess failed: %s' % error, xbmc.LOGERROR)

    # PID only: do not kill other Kodi instances or their child processes.
    try:
        system_root = os.environ.get('SystemRoot', r'C:\Windows')
        command = [os.path.join(system_root, 'System32', 'taskkill.exe'),
                   '/F', '/PID', str(pid)]
        result = subprocess.run(command, shell=False, capture_output=True,
                                timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        raise RuntimeError('taskkill returned %d; Kodi is still running' % result.returncode)
    except Exception as error:
        xbmc.log('[X2 Force Close] PID fallback failed: %s' % error, xbmc.LOGERROR)


def main():
    pid = os.getpid()
    xbmc.log('[X2 Force Close] Terminating current Kodi PID %d (%s)' %
             (pid, os.name), xbmc.LOGINFO)
    if os.name == 'nt':
        terminate_windows(pid)
    elif os.name == 'posix':
        # Android, Linux/LibreELEC/CoreELEC, macOS and iOS/tvOS.
        # Killing our own process needs no root access or shell utility.
        try:
            import signal
            os.kill(pid, signal.SIGKILL)
            return
        except Exception as error:
            xbmc.log('[X2 Force Close] SIGKILL failed: %s' % error, xbmc.LOGERROR)

    # Last resort if the native termination method failed or OS is unknown.
    try:
        os._exit(1)
    except Exception as error:
        xbmc.log('[X2 Force Close] Immediate exit failed: %s' % error, xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Force Close Kodi',
                            'Could not terminate Kodi. See the Kodi log for details.')


if __name__ == '__main__':
    main()
