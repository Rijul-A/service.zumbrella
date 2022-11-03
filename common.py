import json
import os

from kodi_six import xbmc

from logger import Logger


def read_float_setting( addon, setting_id ):
    return float( addon.getSetting( setting_id ) )


def read_int_setting( addon, setting_id, minutes_to_seconds = True ):
    var = int( addon.getSetting( setting_id )
              ) * ( 60 if minutes_to_seconds else 1 )
    if minutes_to_seconds and var == 0:
        var = 15
    return var


def read_bool_setting( addon, setting_id ):
    return addon.getSetting( setting_id ).lower() == 'true'


def json_rpc( **kwargs ):
    logger = Logger( os.path.basename( __file__ ) )
    if kwargs.get( 'id' ) is None:
        kwargs.update( id = 1 )
    if kwargs.get( 'jsonrpc' ) is None:
        kwargs.update( jsonrpc = '2.0' )
    payload = json.dumps( kwargs )
    # only show if debug mode
    logger.log( 'JSON-RPC execute %s' % payload, xbmc.LOGDEBUG )
    output = json.loads( xbmc.executeJSONRPC( payload ) )
    if 'error' in output:
        # always show
        logger.log( output, xbmc.LOGERROR )
        raise RuntimeError( 'Invalid RPC reponse' )
    return output.get( 'result',
                       {} )
