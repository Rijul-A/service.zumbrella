import json
import os

import xbmc

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


__MAX_TRIES__ = 100
VIDEO_WINDOW_IDS = [ 10147, 12005 ]


def get_player_id():
    logger = Logger( os.path.basename( __file__ ) )
    result = []
    tries = 0
    while len( result ) == 0 \
    and tries < __MAX_TRIES__:
        logger.log( 'Trying to obtain active player' )
        result = json_rpc( method = 'Player.GetActivePlayers' )
        tries = tries + 1
    if len( result ) == 0:
        logger.log( 'Did not find any active players' )
        return -1
    return result[ 0 ].get( 'playerid', -1 )
