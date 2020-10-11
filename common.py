import json

import xbmc

__PLUGIN_ID__ = 'service.zumbrella'
__PLUGIN_VERSION__ = 'v0.0.2'

__SETTING_SHOW_GUI__ = 'show_gui'

logMode = xbmc.LOGNOTICE

def log(file_name, msg, mode = None):
    global logMode
    mode = None or logMode
    xbmc.log("[{}_{}]: {} - {}".format(__PLUGIN_ID__, __PLUGIN_VERSION__, file_name, msg), mode)

def read_int_setting(addon, setting_id, reset = True):
    var = int(addon.getSetting(setting_id)) * (60 if reset else 1)
    if reset and var == 0:
        var = 60
    return var

def read_bool_setting(addon, setting_id):
    return addon.getSetting(setting_id) == 'true'

def json_rpc(**kwargs):
    if kwargs.get('id') is None:
        kwargs.update(id = 0)
    if kwargs.get('jsonrpc') is None:
        kwargs.update(jsonrpc = '2.0')
    return json.loads(xbmc.executeJSONRPC(json.dumps(kwargs)))
