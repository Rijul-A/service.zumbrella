import json

from kodi_six import xbmc

__PLUGIN_ID__ = 'service.zumbrella'
__PLUGIN_VERSION__ = 'v0.0.4-matrix'

__SETTING_SHOW_GUI__ = 'show_gui'

logMode = xbmc.LOGINFO


def log( file_name, msg, mode = None ):
    global logMode
    mode = None or logMode
    xbmc.log(
        "[{}_{}]: {} - {}".format(
            __PLUGIN_ID__,
            __PLUGIN_VERSION__,
            file_name,
            msg
        ),
        mode
    )


def read_float_setting( addon, setting_id ):
    return float( addon.getSetting( setting_id ) )


def read_int_setting( addon, setting_id, minutes_to_seconds = True ):
    var = int( addon.getSetting( setting_id )
              ) * ( 60 if minutes_to_seconds else 1 )
    if minutes_to_seconds and var == 0:
        var = 15
    return var


def read_bool_setting( addon, setting_id ):
    return addon.getSetting( setting_id ) == 'true'


def json_rpc( **kwargs ):
    if kwargs.get( 'id' ) is None:
        kwargs.update( id = 0 )
    if kwargs.get( 'jsonrpc' ) is None:
        kwargs.update( jsonrpc = '2.0' )
    return json.loads( xbmc.executeJSONRPC( json.dumps( kwargs ) ) )
