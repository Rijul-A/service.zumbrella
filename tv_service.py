import json
import requests

import xbmc
import xbmcaddon

from logger import Logger
from monitor import Monitor

REQUEST_TIMEOUT = 3
TV_WAKE_DELAY_SECONDS = 1
PLAYBACK_STOP_DELAY_SECONDS = 1
POWER_STATUS_REQUEST_ID = 50

try:
    ADDON_ID = 'service.zumbrella'
    ADDON = xbmcaddon.Addon( id = ADDON_ID )
    if ADDON.getSetting( 'debug' ) == 'true':
        Logger.set_log_mode( xbmc.LOGDEBUG )
    else:
        Logger.set_log_mode( xbmc.LOGINFO )
    TV_IP = ADDON.getSetting( 'tv_ip' )
    TV_PSK = ADDON.getSetting( 'tv_password' )
    TV_HDMI_PORT = ADDON.getSetting( 'tv_hdmi_port' )
    TV_MAC = ADDON.getSetting( 'tv_mac_address' )
    TV_ENDPOINT = f"http://{TV_IP}/sony/"
except Exception as e:
    # Use safe fallback if ADDON_ID wasn't set
    try:
        addon_id = ADDON_ID
    except NameError:
        addon_id = 'service.zumbrella'
    xbmc.log(
        f"[{addon_id}] CRITICAL ERROR: Could not read settings: {e}",
        mode = xbmc.LOGERROR
    )
    raise SystemExit( f"Failed to load settings: {e}" )


class TV( Logger ):
    def __init__( self, name, ip_address, endpoint, security_token ):
        super().__init__( tag = name )
        self.name = name
        self.ip_address = ip_address
        self.endpoint = endpoint
        self.security_token = security_token


class Bravia( TV ):
    # IRCC (Infrared Remote Control Command) codes for TV control
    IRCC_CODES = {
        "mute": "AAAAAQAAAAEAAAAUAw==",
        "vol_down": "AAAAAQAAAAEAAAATAw==",
        "vol_up": "AAAAAQAAAAEAAAASAw==",
    }

    def send( self, service, method, params, request_id = 1 ):
        """Send a request to the TV API."""
        self.log(
            f"Sending command: service={service}, method={method}",
            xbmc.LOGDEBUG
        )
        headers = {
            'X-Auth-PSK': self.security_token
        }
        body = {
            "method": method,
            "version": "1.0",
            "id": request_id,
            "params": [ params ] if params is not None else []
        }
        try:
            response = requests.post(
                self.endpoint + service,
                data = json.dumps( body ),
                headers = headers,
                timeout = REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self.log(
                f"HTTP Request failed for {method}: {e}",
                mode = xbmc.LOGERROR
            )
            return None

    def send_ircc_code( self, ircc_code ):
        url = self.endpoint + 'ircc'
        payload = (
            '<?xml version="1.0"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            '<s:Body>'
            '<u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1">'
            '<IRCCCode>%s</IRCCCode>'
            '</u:X_SendIRCC>'
            '</s:Body>'
            '</s:Envelope>'
        ) % ircc_code
        headers = {
            'X-Auth-PSK': self.security_token,
            'SOAPAction': '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"'
        }
        try:
            response = requests.post(
                url,
                data = payload,
                headers = headers,
                timeout = REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self.log( f"Failed to send IRCC code: {e}", mode = xbmc.LOGERROR )
            return None

    def setPower( self, val ):
        """Set TV power status."""
        self.send( 'system',
                   'setPowerStatus',
                   {
                       "status": val
                   } )

    def setExtInput( self, kind, port ):
        """Switch TV input to specified HDMI port."""
        uri = f"extInput:{kind}?port={port}"
        self.send( 'avContent',
                   'setPlayContent',
                   {
                       "uri": uri
                   } )

    def getPowerStatus( self ):
        """Get current TV power status. Returns 'active' or 'standby'."""
        self.log( "Getting power status..." )
        try:
            response = self.send(
                'system',
                'getPowerStatus',
                None,
                POWER_STATUS_REQUEST_ID
            )
            if response is None or response.status_code != 200:
                status_code = response.status_code if response else "No response"
                self.log(
                    f"Power status response unexpected or failed. Assuming 'standby'. Status: {status_code}",
                    mode = xbmc.LOGWARNING
                )
                return "standby"
            try:
                js = response.json()
                if 'result' in js and js.get( 'result' ):
                    status = js[ 'result' ][ 0 ].get( 'status', 'standby' )
                    self.log( f"TV power status is: {status}" )
                    return status
            except ( ValueError, KeyError, IndexError ) as e:
                self.log(
                    f"Failed to parse power status JSON: {e}",
                    mode = xbmc.LOGWARNING
                )
            self.log(
                "Power status response missing result, assuming 'standby'",
                mode = xbmc.LOGWARNING
            )
            return "standby"
        except Exception as e:
            self.log(
                f"Failed to get power status (likely standby). Error: {e}",
                mode = xbmc.LOGWARNING
            )
            return "standby"

    def getPlayingContentInfo( self ):
        """Get information about currently playing content on TV."""
        self.log( "Getting current playing content..." )
        try:
            response = self.send( 'avContent', 'getPlayingContentInfo', None )
            if response is None or response.status_code != 200:
                status_code = response.status_code if response else "No response"
                self.log(
                    f"Failed to get content info. Status Code: {status_code}",
                    mode = xbmc.LOGWARNING
                )
                return None
            try:
                js = response.json()
                if 'error' in js:
                    self.log(
                        f"Error in content info response (TV may be on wrong input): {js.get('error')}",
                        mode = xbmc.LOGWARNING
                    )
                    return None
                result = js.get( 'result', [] )
                if result:
                    return result[ 0 ]
                return None
            except ( ValueError, KeyError, IndexError ) as e:
                self.log(
                    f"Failed to parse content info response: {e}",
                    mode = xbmc.LOGERROR
                )
                return None
        except Exception as e:
            self.log(
                f"Failed to get content info. Error: {e}",
                mode = xbmc.LOGERROR
            )
            return None

    def mute( self ):
        self.send_ircc_code( self.IRCC_CODES[ "mute" ] )

    def vol_down( self ):
        self.send_ircc_code( self.IRCC_CODES[ "vol_down" ] )

    def vol_up( self ):
        self.send_ircc_code( self.IRCC_CODES[ "vol_up" ] )


class BraviaControl( Logger ):
    """
    Called by the keymap to run once and exit.
    """
    def __init__( self ):
        super().__init__( tag = "BraviaControl" )
        self.log( "Script initiated." )
        self.monitor = Monitor()
        if not all(
            [
                TV_IP and TV_IP.strip(),
                TV_PSK and TV_PSK.strip(),
                TV_HDMI_PORT and TV_HDMI_PORT.strip(),
                TV_MAC and TV_MAC.strip()
            ]
        ):
            self.log(
                "TV IP, PSK, HDMI Port, or MAC is not set in settings. Aborting.",
                mode = xbmc.LOGERROR
            )
            xbmc.executebuiltin(
                'Notification(Zumbrella Error, Check add-on settings, 5000)'
            )
            raise SystemExit( "Invalid Settings" )
        self.bravia = Bravia( 'Bravia', TV_IP, TV_ENDPOINT, TV_PSK )

    def check_input( self ):
        """Check if the TV is on the correct input."""
        content_info = self.bravia.getPlayingContentInfo()
        if content_info is None:
            return False
        current_title = content_info.get( 'title', '' )
        target_title = f"HDMI {TV_HDMI_PORT}"
        return current_title.startswith( target_title )

    def power_control( self ):
        """Main execution logic"""
        current_status = self.bravia.getPowerStatus()
        if current_status == "active":
            # TV IS ON: Turn it OFF.
            self.log( "TV is ON. Stopping playback and turning TV OFF." )
            if xbmc.Player().isPlaying():
                self.log( "Stopping Kodi playback." )
                xbmc.Player().stop()
                self.monitor.waitForAbort( PLAYBACK_STOP_DELAY_SECONDS )
            # check if the TV is on the correct input
            if not self.check_input():
                self.log( "TV is on another input, not turning off." )
                return
            self.log( "Turning off TV." )
            self.bravia.setPower( False )
        else:
            # TV IS OFF (or in standby): Turn it ON.
            self.log( "TV is OFF. Sending Wake-on-LAN and switching input." )
            self.log( f"Sending WakeOnLan command to {TV_MAC}" )
            xbmc.executebuiltin( f'WakeOnLan("{TV_MAC}")' )
            self.bravia.setPower( True )
            self.log( f"Waiting {TV_WAKE_DELAY_SECONDS}s for TV to wake..." )
            self.monitor.waitForAbort( TV_WAKE_DELAY_SECONDS )
            # check if the TV is on the correct input
            if self.check_input():
                self.log( "TV is already on the correct input." )
                return
            self.log( f"Switching to HDMI {TV_HDMI_PORT}." )
            self.bravia.setExtInput( 'hdmi', str( TV_HDMI_PORT ) )

    def run( self, action ):
        if action == "power_control":
            self.power_control()
        elif action == "vol_mute":
            self.bravia.mute()
        elif action == "vol_down":
            self.bravia.vol_down()
        elif action == "vol_up":
            self.bravia.vol_up()


if __name__ == "__main__":
    if len( sys.argv ) != 2:
        xbmc.log(
            "Usage: RunScript(special://home/addons/service.zumbrella/tv_service.py, <action>)",
            mode = xbmc.LOGERROR
        )
        sys.exit( 1 )
    action = sys.argv[ 1 ]
    try:
        control = BraviaControl()
        control.run( action )
    except SystemExit:
        pass
    except Exception as e:
        fatal_logger = Logger( "FATAL_ERROR" )
        fatal_logger.log( f"Fatal script error: {e}", mode = xbmc.LOGERROR )
        xbmc.executebuiltin( f'Notification(Zumbrella Error, {e}, 5000)' )
