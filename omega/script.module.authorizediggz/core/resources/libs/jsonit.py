import xbmc, xbmcaddon
import xbmcvfs
import json
import os
import tempfile
from libs.common import var

########################################################################
########################################################################
############################ Realizer RD ##############################

###################### Restore Realizer RD ######################
def realizer_rst():
    if os.path.exists(os.path.join(var.rd_backup_realx)) and os.path.exists(os.path.join(var.realx_path)):
        try:
            xbmcvfs.copy(os.path.join(var.rd_backup_realx), os.path.join(var.realx_json_path))
        except:
            xbmc.log('%s: Jsonit_db Restore Realizer RD Failed!' % var.amgr, xbmc.LOGINFO)
            pass

def write_realizer_auth(values):
    path = var.realx_json_path
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    if os.path.isfile(path):
        try:
            with open(path, encoding='utf-8') as stream:
                if json.load(stream) == values:
                    return
        except ValueError:
            pass
    fd, temporary = tempfile.mkstemp(prefix='.reauthorize-', dir=folder)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(values, stream)
        os.replace(temporary, path)
        with open(path, encoding='utf-8') as stream:
            if json.load(stream) != values:
                raise IOError('RealizerX credentials did not save')
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def realizer_rvk():
    if os.path.exists(var.realx_json_path):
        write_realizer_auth(dict.fromkeys(
            ('client_id', 'client_secret', 'token', 'refresh_token', 'added'), ''))


###################### Backup Realizer RD ######################
def realizer_bk():
    if os.path.exists(os.path.join(var.realx_json_path)) and os.path.exists(os.path.join(var.rd_backup)):
        try:
            xbmcvfs.copy(os.path.join(var.realx_json_path), os.path.join(var.rd_backup_realx))
        except:
            xbmc.log('%s: Jsonit_db Backup Realizer RD Failed!' % var.amgr, xbmc.LOGINFO)
            pass

##################### Delete Realizer RD Backup #####################
#def realizer_rm():
#    if os.path.exists(os.path.join(var.rd_backup_realx)):
#        try:
#            os.unlink(os.path.join(var.rd_backup_realx))
#        except OSError:
#            xbmc.log('%s: Jsonit_db Delete Realizer RD Failed!' % var.amgr, xbmc.LOGINFO)
#            pass
