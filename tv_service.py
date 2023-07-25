from sony_bravia_api import Bravia
from wakeonlan import send_magic_packet

from common import ( read_int_setting, )
from logger import Logger


class TvService( Logger ):
    __SETTING_IP_ADDRESS__ = "tv_ip_address"
    __SETTING_PASSWORD__ = "tv_password"
    __SETTING_MAC_ADDRESS__ = "tv_mac_address"
    __SETTING_HDMI_PORT__ = "tv_hdmi_port"

    def __init__( self, addon ):
        self.log( 'Creating object' )
        self.addon = addon  # to load settings

    def onAVStarted( self ):
        pass

    def onPlayBackPaused( self ):
        pass

    def onPlayBackResumed( self ):
        pass

    def onPlayBackEnded( self ):
        pass

    def onPlayBackError( self ):
        pass

    def onPlayBackStopped( self ):
        pass

    def refresh_settings( self ):
        self.log( 'Reading settings' )
        self.ip_address = self.addon.getSetting(
            TvService.__SETTING_IP_ADDRESS__,
        )
        self.password = self.addon.getSetting( TvService.__SETTING_PASSWORD__, )
        self.mac_address = self.addon.getSetting(
            TvService.__SETTING_MAC_ADDRESS__,
        )
        # used to check if TV is on this port
        self.hdmi_port = read_int_setting(
            self.addon,
            TvService.__SETTING_HDMI_PORT__,
            False,
        )
        self.log( 'Loaded settings' )
        self.log( 'ip_address: {}'.format( self.ip_address ) )
        self.log( 'mac_address: {}'.format( self.mac_address ) )
        self.log( 'hdmi_port: {}'.format( self.hdmi_port ) )
        self.bravia = Bravia(
            'TV',
            self.ip_address,
            'http://{}/sony/'.format( self.ip_address ),
            self.password,
        )

    def power( self, on = False ):
        self.log(
            'Received request for power {}'.format(
                'on' if on else 'off',
            )
        )
        # wake it up for responsiveness
        # not very useful right now since we only turn off in this addon
        send_magic_packet( self.mac_address )
        # request to turn off, check we are on the correct port
        if not on:
            response = self.bravia.send(
                'avContent',
                'getPlayingContentInfo',
                []
            ).json()
            # non HDMI playing
            if 'error' in response:
                self.log( 'Playing from non-HDMI source, not doing anything' )
                return
            result = response.get( 'result',
                                   [ {} ] )[ 0 ].get( 'title',
                                                      '' )
            # some other port
            if result != "HDMI {}".format( self.hdmi_port ):
                self.log(
                    'Playing from different HDMI source, not doing anything'
                )
                return
        # now turn it off or on
        self.bravia.setPower( on )

    def onScreensaverActivated( self ):
        self.log( 'Turning off TV because screensaver activated' )
        self.power( False )
