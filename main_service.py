import os

from kodi_six import xbmc, xbmcaddon

import common
from player import Player
from monitor import Monitor
from bluetooth_service import BluetoothService
from still_there_service import StillThereService
from upnext_service import UpNextService


class MainService:
    __SETTING_LOG_MODE_BOOL__ = "debug"
    __SETTING_CHECK_TIME__ = 'check_time'

    def __init__( self ):
        self.addon = xbmcaddon.Addon()
        self.monitor = Monitor(
            reloadAction = self.onSettingsChanged,
            screensaverAction = self.onScreensaverActivated
        )
        self.player = Player(
            avStartedAction = self.onAVStarted,
            playBackPausedAction = self.onPlayBackPaused,
            playBackResumedAction = self.onPlayBackResumed,
            playBackEndedAction = self.onPlayBackEnded,
            playbackErrorAction = self.onPlayBackError,
            playBackStoppedAction = self.onPlayBackStopped,
        )
        self.bluetooth_service = BluetoothService( self.addon )
        self.still_there_service = StillThereService(
            self.addon,
            self.monitor,
            'still_there.xml'
        )
        self.upnext_service = UpNextService(
            self.addon,
            self.monitor,
            'up_next.xml'
        )
        self.services = [
            self.bluetooth_service,
            self.still_there_service,
            self.upnext_service
        ]
        self.refresh_settings()

    def onAVStarted( self ):
        self.log( 'Received AC started notification' )
        if xbmc.getCondVisibility( 'Player.HasVideo' ):
            self.log( 'Detected that it is video' )
            self.player.showSubtitles( True )
        for service in self.services:
            if hasattr( service, 'onAVStarted' ):
                service.onAVStarted()

    def onPlayBackPaused( self ):
        self.log( 'Received playback paused notification' )
        for service in self.services:
            if hasattr( service, 'onPlayBackPaused' ):
                service.onPlayBackPaused()

    def onPlayBackResumed( self ):
        self.log( 'Received playback resumed notification' )
        for service in self.services:
            if hasattr( service, 'onPlayBackResumed' ):
                service.onPlayBackResumed()

    def onPlayBackEnded( self ):
        self.log( 'Received playback ended notification' )
        for service in self.services:
            if hasattr( service, 'onPlayBackEnded' ):
                service.onPlayBackEnded()

    def onPlayBackError( self ):
        self.log( 'Received playback error notification' )
        for service in self.services:
            if hasattr( service, 'onPlayBackError' ):
                service.onPlayBackError()

    def onPlayBackStopped( self ):
        self.log( 'Received playback stopped notification' )
        for service in self.services:
            if hasattr( service, 'onPlayBackStopped' ):
                service.onPlayBackStopped()

    def onScreensaverActivated( self ):
        self.log( 'Received screensaver started notification' )
        for service in self.services:
            if hasattr( service, 'onScreensaverActivated' ):
                service.onScreensaverActivated()

    def onSettingsChanged( self ):
        common.logMode = xbmc.LOGINFO  # activate debug mode
        self.log( 'Received notification to reload settings, doing so now' )
        self.__init__()

    def refresh_settings( self ):
        self.log( 'Reading settings' )
        for service in self.services:
            service.refresh_settings()
        self.check_time = common.read_int_setting(
            self.addon,
            MainService.__SETTING_CHECK_TIME__
        )
        debugMode = self.addon.getSetting(
            MainService.__SETTING_LOG_MODE_BOOL__
        ) == 'true'
        self.log( 'debugMode: {}'.format( debugMode ) )
        if not debugMode:
            self.log( 'Addon going quiet due to debugMode' )
        common.logMode = xbmc.LOGINFO if debugMode else xbmc.LOGDEBUG

    def do_checks( self ):
        self.sleep()
        inactivity_seconds = xbmc.getGlobalIdleTime()
        self.log( 'Inactive time is {} seconds'.format( inactivity_seconds ) )
        for service in self.services:
            service.do_check( inactivity_seconds )

    def sleep( self, duration = None ):
        duration = duration or self.check_time
        self.log( 'Waiting {} seconds for next check'.format( duration ) )
        if self.monitor.waitForAbort( duration ):
            exit()

    def log( self, msg ):
        common.log( self.__class__.__name__, msg )


if __name__ == '__main__':
    common.log( os.path.basename( __file__ ), 'Creating object' )
    object = MainService()
    while not object.monitor.abortRequested():
        object.do_checks()
