import json
import sys
import requests

import xbmc
import xbmcaddon

from logger import Logger
from monitor import Monitor

REQUEST_TIMEOUT = 3
TV_WAKE_DELAY_SECONDS = 1
PLAYBACK_STOP_DELAY_SECONDS = 1
POWER_STATUS_REQUEST_ID = 50


# Load settings from settings.xml only in main
def load_settings():
    try:
        addon_id = 'service.zumbrella'
        addon = xbmcaddon.Addon( id = addon_id )
        if addon.getSetting( 'debug' ) == 'true':
            Logger.set_log_mode( xbmc.LOGDEBUG )
        else:
            Logger.set_log_mode( xbmc.LOGINFO )
        tv_ip = addon.getSetting( 'tv_ip' )
        tv_psk = addon.getSetting( 'tv_password' )
        tv_hdmi_port = addon.getSetting( 'tv_hdmi_port' )
        tv_mac = addon.getSetting( 'tv_mac_address' )
        # Validate settings before constructing endpoint
        if not all(
            [
                tv_ip and tv_ip.strip(),
                tv_psk and tv_psk.strip(),
                tv_hdmi_port and tv_hdmi_port.strip(),
                tv_mac and tv_mac.strip()
            ]
        ):
            xbmc.executebuiltin(
                'Notification(Zumbrella Error, Check add-on settings, 5000)'
            )
            raise ValueError(
                "TV IP, PSK, HDMI Port, or MAC is not set in settings"
            )
        tv_endpoint = f"http://{tv_ip}/sony/"
        return tv_ip, tv_psk, tv_hdmi_port, tv_mac, tv_endpoint
    except Exception as e:
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
        self.log( "Getting power status...", xbmc.LOGDEBUG )
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
                    self.log( f"TV power status is: {status}", xbmc.LOGDEBUG )
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
        self.log( "Getting current playing content...", xbmc.LOGDEBUG )
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
    TV control class for Bravia TVs.
    Requires TV settings as constructor parameters.
    When used as standalone script (__main__), settings are loaded via load_settings().
    When imported, caller must provide all required parameters.
    """
    def __init__( self, tv_ip, tv_psk, tv_hdmi_port, tv_mac, tv_endpoint ):
        super().__init__( tag = "BraviaControl" )
        self.log( "Script initiated.", mode = xbmc.LOGDEBUG )
        self.monitor = Monitor()
        self.tv_ip = tv_ip
        self.tv_psk = tv_psk
        self.tv_hdmi_port = tv_hdmi_port
        self.tv_mac = tv_mac
        self.tv_endpoint = tv_endpoint
        self.bravia = Bravia(
            'Bravia',
            self.tv_ip,
            self.tv_endpoint,
            self.tv_psk
        )

    def check_input( self ):
        """Check if the TV is on the correct input."""
        content_info = self.bravia.getPlayingContentInfo()
        if content_info is None:
            return False
        current_title = content_info.get( 'title', '' )
        target_title = f"HDMI {self.tv_hdmi_port}"
        return current_title.startswith( target_title )

    def power_control( self, action = None ):
        """Main execution logic"""
        current_status = self.bravia.getPowerStatus()
        if current_status == "active":
            if action == "on":
                self.log(
                    "TV is already on. Not turning it on.",
                    mode = xbmc.LOGDEBUG
                )
                return
            self.log(
                "TV is ON. Checking if it is on the correct input.",
                xbmc.LOGDEBUG
            )
            if not self.check_input():
                self.log(
                    "TV is on another input, not turning off.",
                    mode = xbmc.LOGDEBUG
                )
                return
            self.log(
                "TV is ON and on the correct input. Stopping playback and turning TV OFF.",
                mode = xbmc.LOGDEBUG
            )
            if xbmc.Player().isPlaying():
                self.log( "Stopping Kodi playback.", mode = xbmc.LOGDEBUG )
                xbmc.Player().stop()
                self.monitor.waitForAbort( PLAYBACK_STOP_DELAY_SECONDS )
            self.log( "Turning off TV.", mode = xbmc.LOGDEBUG )
            self.bravia.setPower( False )
        else:
            if action == "off":
                self.log(
                    "TV is already off. Not turning it on.",
                    mode = xbmc.LOGDEBUG
                )
                return
            # TV IS OFF (or in standby): Turn it ON.
            self.log(
                "TV is OFF. Sending Wake-on-LAN and switching input.",
                mode = xbmc.LOGDEBUG
            )
            self.log(
                f"Sending WakeOnLan command to {self.tv_mac}",
                mode = xbmc.LOGDEBUG
            )
            xbmc.executebuiltin( f'WakeOnLan("{self.tv_mac}")' )
            self.bravia.setPower( True )
            self.log(
                f"Waiting {TV_WAKE_DELAY_SECONDS}s for TV to wake...",
                mode = xbmc.LOGDEBUG
            )
            self.monitor.waitForAbort( TV_WAKE_DELAY_SECONDS )
            if self.check_input():
                self.log(
                    "TV is already on the correct input.",
                    mode = xbmc.LOGDEBUG
                )
                return
            self.log(
                f"Switching to HDMI {self.tv_hdmi_port}.",
                mode = xbmc.LOGDEBUG
            )
            self.bravia.setExtInput( 'hdmi', str( self.tv_hdmi_port ) )

    def run( self, action ):
        if action.startswith( "power_control" ):
            self.log( f"Performing power control: {action}", xbmc.LOGDEBUG )
            if action == "power_control_off":
                self.power_control( 'off' )
            elif action == "power_control_on":
                self.power_control( 'on' )
            else:
                self.power_control()
        elif self.check_input():
            self.log(
                "TV is on the correct input. Performing volume action.",
                xbmc.LOGDEBUG
            )
            if action == "vol_mute":
                self.bravia.mute()
            elif action == "vol_down":
                self.bravia.vol_down()
            elif action == "vol_up":
                self.bravia.vol_up()
        else:
            self.log(
                "TV is not on the correct input. Not performing action.",
                xbmc.LOGDEBUG
            )


if __name__ == "__main__":
    if len( sys.argv ) != 2:
        xbmc.log(
            "Usage: RunScript(special://home/addons/service.zumbrella/tv_service.py, <action>)",
            mode = xbmc.LOGERROR
        )
        sys.exit( 1 )
    action = sys.argv[ 1 ]
    try:
        tv_ip, tv_psk, tv_hdmi_port, tv_mac, tv_endpoint = load_settings()
        control = BraviaControl(
            tv_ip,
            tv_psk,
            tv_hdmi_port,
            tv_mac,
            tv_endpoint
        )
        control.run( action )
    except SystemExit:
        pass
    except Exception as e:
        fatal_logger = Logger( "FATAL_ERROR" )
        fatal_logger.log( f"Fatal script error: {e}", mode = xbmc.LOGERROR )
        xbmc.executebuiltin( f'Notification(Zumbrella Error, {e}, 5000)' )
