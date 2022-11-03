import inspect
import os

from kodi_six import xbmc, xbmcaddon

from bluetooth_service import BluetoothService
from common import ( json_rpc, read_int_setting )
from logger import Logger
from monitor import Monitor
from player import Player
from still_there_service import StillThereService
from upnext_service import UpNextService


class MainService( Logger ):
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

    def call_on_all_services( self, name, **kwargs ):
        self.log( 'Received notification %s' % name )
        for service in self.services:
            if hasattr( service, name ):
                getattr( service, name )( **kwargs )

    def onAVStarted( self ):
        self.call_on_all_services( inspect.currentframe().f_code.co_name )
        self.activate_subtitles()

    def onPlayBackPaused( self ):
        self.call_on_all_services( inspect.currentframe().f_code.co_name )

    def onPlayBackResumed( self ):
        self.call_on_all_services( inspect.currentframe().f_code.co_name )

    def onPlayBackEnded( self ):
        self.call_on_all_services( inspect.currentframe().f_code.co_name )

    def onPlayBackError( self ):
        self.call_on_all_services( inspect.currentframe().f_code.co_name )

    def onPlayBackStopped( self ):
        self.call_on_all_services( inspect.currentframe().f_code.co_name )

    def onScreensaverActivated( self ):
        self.call_on_all_services( inspect.currentframe().f_code.co_name )

    def onSettingsChanged( self ):
        Logger.set_log_mode( xbmc.LOGINFO )
        self.log( 'Received notification to reload settings, doing so now' )
        self.__init__()

    def refresh_settings( self ):
        self.log( 'Reading settings' )
        self.call_on_all_services( inspect.currentframe().f_code.co_name )
        self.check_time = read_int_setting(
            self.addon,
            MainService.__SETTING_CHECK_TIME__
        )
        debugMode = self.addon.getSetting(
            MainService.__SETTING_LOG_MODE_BOOL__
        ) == 'true'
        self.log( 'debugMode: {}'.format( debugMode ) )
        if not debugMode:
            self.log( 'Addon going quiet due to debugMode' )
        Logger.set_log_mode( xbmc.LOGINFO if debugMode else xbmc.LOGDEBUG )

    def do_checks( self ):
        self.sleep()
        inactivity_seconds = xbmc.getGlobalIdleTime()
        self.log( 'Inactive time is {} seconds'.format( inactivity_seconds ) )
        self.call_on_all_services(
            inspect.currentframe().f_code.co_name[ :-1 ],
            inactivity_seconds = inactivity_seconds
        )

    def sleep( self, duration = None ):
        duration = duration or self.check_time
        self.log( 'Waiting {} seconds for next check'.format( duration ) )
        if self.monitor.waitForAbort( duration ):
            exit()

    def activate_subtitles( self, lang = 'eng' ):
        if not( xbmc.getCondVisibility( 'Player.HasVideo' ) \
        and xbmc.getCondVisibility( 'VideoPlayer.HasSubtitles' ) ):
            return
        self.log( 'Activating subtitles' )
        player_id = self.still_there_service.get_player_id()
        if player_id == -1:
            self.log( 'No player_id, cancelled' )
            return
        subtitles = json_rpc(
            method = 'Player.GetProperties',
            params = dict( playerid = player_id,
                           properties = [ 'subtitles' ] )
        ).get( 'subtitles',
               [] )
        # drop the forced subtitles
        self.log( 'Dropping forced subtitles' )
        subtitles = [
            subtitle for subtitle in subtitles if not subtitle[ 'isforced' ]
        ]
        if len( subtitles ) == 0:
            self.log( 'No subtitle available, cancelled' )
            return
        if len( subtitles ) == 1:
            self.log( 'Only one subtitle available, picking it' )
            index = subtitles[ 0 ][ 'index' ]
        else:
            self.log( 'Choosing appropriate subtitle' )
            index = self.pick_appropriate_subtitle( subtitles, lang )
        if not index:
            return
        self.log( 'Setting subtitle stream' )
        self.player.setSubtitleStream( index )
        self.log( 'Showing subtitle' )
        self.player.showSubtitles( True )

    def pick_appropriate_subtitle( self, subtitles, lang ):
        # apply these one by one
        constraints = {
            "prefer default": lambda x: x[ 'isdefault' ],
            "internal with language": lambda x: x[
                'language' ] == lang and 'external' not in x[ 'name' ].lower(),
            "internal without language": lambda x: x[ 'language' ] == '' and
            'external' not in x[ 'name' ].lower(),
            "any with language": lambda x: x[ 'language' ] == lang,
            "any without language": lambda x: x[ 'language' ] == ''
        }
        for description, constraint in constraints.items():
            result = next(
                (
                    subtitle for subtitle in subtitles
                    if constraint( subtitle )
                ),
                {}
            )
            if result:
                self.log(
                    'Matched constraint %s; picking stream #%d' %
                    ( description,
                      result[ 'index' ] )
                )
                return result[ 'index' ]


if __name__ == '__main__':
    Logger( os.path.basename( __file__ ) ).log( 'Creating object' )
    object = MainService()
    while not object.monitor.abortRequested():
        object.do_checks()
