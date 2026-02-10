#!/usr/bin/env python
import os
import json
import socket
import struct
import logging
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from requests.auth import HTTPBasicAuth

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger( "BraviaServer" )


def get_env_strict( key ):
    value = os.environ.get( key )
    if not value or not value.strip():
        logger.error( f"FATAL: Missing mandatory environment variable '{key}'" )
        raise RuntimeError(
            f"The environment variable '{key}' is required but was not found."
        )
    return value


# Strict Configuration - No defaults, no startup without these
try:
    TV_IP = get_env_strict( 'TV_IP' )
    TV_PSK = get_env_strict( 'TV_PSK' )
    TV_MAC = get_env_strict( 'TV_MAC' )
    TV_HDMI_PORT = get_env_strict( 'TV_HDMI_PORT' )
    KODI_HOST = get_env_strict( 'KODI_HOST' )
    KODI_PORT = get_env_strict( 'KODI_PORT' )
    KODI_USER = get_env_strict( 'KODI_USER' )
    KODI_PASS = get_env_strict( 'KODI_PASS' )
    SERVER_PORT = int( get_env_strict( 'SERVER_PORT' ) )
except ( RuntimeError, ValueError ) as e:
    import sys
    print( f"Server failed to start: {e}", file = sys.stderr )
    sys.exit( 1 )

REQUEST_TIMEOUT = 3


class BraviaTVError( Exception ):
    """Raised when the TV request fails (HTTP error or invalid JSON)."""
    pass


def wake_on_lan( mac ):
    add_oct = mac.replace( ':', '' ).replace( '-', '' )
    data = b'FFFFFFFFFFFF' + ( add_oct * 16 ).encode()
    send_data = b''
    for i in range( 0, len( data ), 2 ):
        send_data += struct.pack( 'B', int( data[ i : i + 2 ], 16 ) )
    with socket.socket( socket.AF_INET, socket.SOCK_DGRAM ) as sock:
        sock.setsockopt( socket.SOL_SOCKET, socket.SO_BROADCAST, 1 )
        sock.sendto( send_data, ( '255.255.255.255', 9 ) )


class MediaController:
    def __init__( self ):
        self.tv_url = f"http://{TV_IP}/sony/"
        self.kodi_url = f"http://{KODI_HOST}:{KODI_PORT}/jsonrpc"
        self.kodi_auth = HTTPBasicAuth( KODI_USER, KODI_PASS )

    def kodi_stop( self ):
        """Authenticates and stops any active Kodi player."""
        logger.info( "Sending authenticated stop command to Kodi..." )
        payload = {
            "jsonrpc": "2.0",
            "method": "Player.GetActivePlayers",
            "id": 1
        }
        try:
            r = requests.post(
                self.kodi_url,
                json = payload,
                auth = self.kodi_auth,
                timeout = 2
            ).json()
            for player in r.get( 'result', [] ):
                p_id = player[ 'playerid' ]
                requests.post(
                    self.kodi_url,
                    json = {
                        "jsonrpc": "2.0",
                        "method": "Player.Stop",
                        "params": {
                            "playerid": p_id
                        },
                        "id": 1
                    },
                    auth = self.kodi_auth,
                    timeout = 2
                )
                logger.info( f"Kodi: Stopped Player ID {p_id}" )
        except Exception as e:
            logger.warning( f"Kodi connection failed: {e}" )

    def tv_req( self, service, method, params = None ):
        headers = {
            'X-Auth-PSK': TV_PSK
        }
        body = {
            "method": method,
            "version": "1.0",
            "id": 1,
            "params": [ params ] if params else []
        }
        r = requests.post(
            self.tv_url + service,
            json = body,
            headers = headers,
            timeout = REQUEST_TIMEOUT
        )
        if not r.ok:
            raise BraviaTVError(
                f"TV returned {r.status_code}: {r.text[:200]}"
            )
        try:
            return r.json()
        except ValueError:
            raise BraviaTVError( "TV returned invalid JSON" )

    def tv_ircc( self, code_key ):
        codes = {
            "vol_up": "AAAAAQAAAAEAAAASAw==",
            "vol_down": "AAAAAQAAAAEAAAATAw==",
            "vol_mute": "AAAAAQAAAAEAAAAUAw=="
        }
        headers = {
            'X-Auth-PSK': TV_PSK,
            'SOAPAction': '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"'
        }
        payload = f'<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1"><IRCCCode>{codes[code_key]}</IRCCCode></u:X_SendIRCC></s:Body></s:Envelope>'
        try:
            r = requests.post(
                self.tv_url + 'ircc',
                data = payload,
                headers = headers,
                timeout = REQUEST_TIMEOUT
            )
            return r.json() if r.text.strip() else {}
        except ( ValueError, requests.RequestException ):
            return {}


class BraviaHandler( BaseHTTPRequestHandler ):
    def _send_json( self, code, body ):
        self.send_response( code )
        self.send_header( "Content-Type", "application/json" )
        self.end_headers()
        self.wfile.write( json.dumps( body ).encode() )

    def do_GET( self ):
        slug = self.path.strip( "/" ).replace( ".", "" ).casefold()
        ctrl = MediaController()
        try:
            if slug == "tvpowercontrol":
                status_resp = ctrl.tv_req( 'system', 'getPowerStatus' )
                status = ( status_resp or
                           {} ).get( 'result',
                                     [ {} ] )[ 0 ].get( 'status' )
                body = {}
                if status == 'active':
                    logger.info( "TV power: turning off (was active)" )
                    ctrl.kodi_stop()
                    body = ctrl.tv_req(
                        'system',
                        'setPowerStatus',
                        {
                            "status": False
                        }
                    )
                else:
                    logger.info( "TV power: turning on (was standby)" )
                    wake_on_lan( TV_MAC )
                    body = ctrl.tv_req(
                        'system',
                        'setPowerStatus',
                        {
                            "status": True
                        }
                    )
                    hdmi_resp = ctrl.tv_req(
                        'avContent',
                        'setPlayContent',
                        {
                            "uri": f"extInput:hdmi?port={TV_HDMI_PORT}"
                        }
                    )
                    body[ 'hdmi_resp' ] = hdmi_resp
                body[ 'prev_status' ] = status
                self._send_json( 200, body )
            elif slug in [ "tvvolumeup", "tvvolumedown", "tvvolumemute" ]:
                action_map = {
                    "tvvolumeup": "vol_up",
                    "tvvolumedown": "vol_down",
                    "tvvolumemute": "vol_mute"
                }
                key = action_map[ slug ]
                logger.info( f"TV volume: {key}" )
                body = ctrl.tv_ircc( key )
                self._send_json( 200, body )
            elif slug == "onscreensaveractivated":
                logger.info( "OnScreenSaver activated: sending TV power-off" )
                body = ctrl.tv_req(
                    'system',
                    'setPowerStatus',
                    {
                        "status": False
                    }
                )
                self._send_json( 200, body )
            else:
                self.send_response( 404 )
                self.end_headers()
        except ( BraviaTVError, requests.RequestException ) as e:
            logger.warning( f"TV request failed: {e}" )
            self._send_json( 502,
                             {
                                 "error": str( e )
                             } )


if __name__ == "__main__":
    server = HTTPServer( ( '0.0.0.0', SERVER_PORT ), BraviaHandler )
    logger.info( f"Bravia-Kodi API Server listening on port {SERVER_PORT}" )
    server.serve_forever()
