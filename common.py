import json
import os

import xbmc

from logger import Logger


class KodiJSONRPCError( Exception ):
    """Raised when a Kodi JSON-RPC call fails."""
    def __init__( self, message, error_data = None ):
        super( KodiJSONRPCError, self ).__init__( message )
        self.error_data = error_data


def json_rpc( **kwargs ):
    logger = Logger( os.path.basename( __file__ ) )
    try:
        if kwargs.get( 'id' ) is None:
            kwargs.update( id = 1 )
        if kwargs.get( 'jsonrpc' ) is None:
            kwargs.update( jsonrpc = '2.0' )
        payload = json.dumps( kwargs )
        # only show if debug mode
        logger.log( 'JSON-RPC execute %s' % payload, xbmc.LOGDEBUG )
        # Execute RPC call
        response_str = xbmc.executeJSONRPC( payload )
        if not response_str:
            logger.log( 'Empty response from JSON-RPC', xbmc.LOGERROR )
            raise KodiJSONRPCError( 'Empty response from JSON-RPC' )
        try:
            output = json.loads( response_str )
        except ValueError as e:
            logger.log( 'Failed to parse JSON-RPC response: %s' % str( e ), xbmc.LOGERROR )
            logger.log( 'Response was: %s' % response_str, xbmc.LOGERROR )
            raise KodiJSONRPCError( 'Invalid JSON in RPC response: %s' % str( e ) )
        if 'error' in output:
            error_info = output[ 'error' ]
            error_msg = 'JSON-RPC error: %s (code: %s)' % (
                error_info.get( 'message', 'Unknown error' ),
                error_info.get( 'code', 'Unknown' )
            )
            logger.log( error_msg, xbmc.LOGERROR )
            logger.log( 'Full error: %s' % error_info, xbmc.LOGERROR )
            raise KodiJSONRPCError( error_msg, error_info )
        result = output.get( 'result', {} )
        return result
    except KodiJSONRPCError:
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        # Catch any other unexpected errors
        logger.log( 'Unexpected error in json_rpc: %s' % str( e ), xbmc.LOGERROR )
        raise KodiJSONRPCError( 'Unexpected error in JSON-RPC call: %s' % str( e ) )


__MAX_TRIES__ = 5  # Reduced from 100 - no need for blocking retries


def get_player_id():
    """
    Get the active player ID without blocking the Kodi thread.
    Uses immediate retries instead of time.sleep() to avoid UI freezing.
    """
    logger = Logger( os.path.basename( __file__ ) )
    tries = 0
    while tries < __MAX_TRIES__:
        try:
            logger.log( 'Trying to obtain active player (attempt %d/%d)' % ( tries + 1, __MAX_TRIES__ ) )
            result = json_rpc( method = 'Player.GetActivePlayers' )
            # Handle both list and dict responses
            if isinstance( result, list ):
                players = result
            elif isinstance( result, dict ):
                players = result.get( 'players', [] )
            else:
                players = []
            if len( players ) > 0:
                player_id = players[ 0 ].get( 'playerid', -1 )
                if player_id != -1:
                    logger.log( 'Found active player with ID: %d' % player_id )
                    return player_id
            # If no player found, try again immediately (no blocking sleep)
            tries = tries + 1
        except KodiJSONRPCError as e:
            logger.log( 'JSON-RPC error while getting player ID: %s' % str( e ), xbmc.LOGWARNING )
            tries = tries + 1
        except Exception as e:
            logger.log( 'Unexpected error while getting player ID: %s' % str( e ), xbmc.LOGERROR )
            tries = tries + 1
    logger.log( 'Did not find any active players after %d attempts' % __MAX_TRIES__, xbmc.LOGWARNING )
    return -1
