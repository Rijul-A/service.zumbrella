import inspect
import os

import xbmc, xbmcaddon

from bluetooth_service import BluetoothService
from common import ( get_player_id, json_rpc, read_int_setting )
from logger import Logger
from monitor import Monitor
from player import Player
from still_there_service import StillThereService
from tv_service import TvService
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
            'still_there.xml',
            self
        )
        self.tv_service = TvService( self.addon )
        self.upnext_service = UpNextService(
            self.addon,
            self.monitor,
            'up_next.xml',
            # UpNext inherits from StillThere, so this needs to be supplied
            None
        )
        self.services = [
            self.bluetooth_service,
            self.still_there_service,
            self.tv_service,
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
        self.change_audio_stream()
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
        self.log( 'onScreensaverActivated' )
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
        self.log( 'Activating subtitles' )
        if not xbmc.getCondVisibility( 'VideoPlayer.HasSubtitles' ):
            self.log( 'No subtitles available, doing nothing' )
            return
        subtitles = self.get_player_properties( 'subtitles' )
        if subtitles is None:
            self.log( 'Doing nothing' )
            return
        # drop the forced subtitles which contain only certain translations
        # and aren't full subtitles
        self.log( 'Dropping forced subtitles' )
        subtitles = [
            subtitle for subtitle in subtitles if not (
                subtitle[ 'isforced' ] or 'forced' in subtitle[ 'name' ].lower()
            )
        ]
        if len( subtitles ) == 0:
            self.log( 'No subtitle available, cancelled' )
            return
        index = None
        if len( subtitles ) == 1:
            self.log( 'Only one subtitle available, picking it' )
            index = subtitles[ 0 ][ 'index' ]
        else:
            self.log( 'Choosing appropriate subtitle' )
            constraints = {
                "prefer default": lambda x: x[ 'isdefault' ],
                "internal with language": lambda x: x[ 'language' ] == lang and
                'external' not in x[ 'name' ].lower(),
                "internal without language": lambda x: x[ 'language' ] == '' and
                'external' not in x[ 'name' ].lower(),
                "any with language": lambda x: x[ 'language' ] == lang,
                "any without language": lambda x: x[ 'language' ] == '',
            }
            index = self.pick_appropriate( subtitles, constraints )
        if index is None:
            return
        self.log( 'Setting subtitle stream' )
        self.player.setSubtitleStream( index )
        self.log( 'Showing subtitle' )
        self.player.showSubtitles( True )

    def change_audio_stream( self, lang = 'eng' ):
        # do not change audio stream if there is no video
        self.log( 'Changing audio stream' )
        audio_streams = self.get_player_properties( 'audiostreams' )
        if audio_streams is None:
            self.log( 'Doing nothing' )
            return
        if len( audio_streams ) == 0:
            self.log( 'No audio stream available, cancelled' )
            return
        index = None
        if len( audio_streams ) == 1:
            self.log( 'Only one audio stream available, picking it' )
            index = audio_streams[ 0 ][ 'index' ]
        else:
            self.log( 'Choosing appropriate audio stream' )
            constraints = {
                "any with language": lambda x: x[ 'language' ] == lang,
                "any without language": lambda x: x[ 'language' ] == '',
                "prefer default": lambda x: x[ 'isdefault' ],
            }
            index = self.pick_appropriate( audio_streams, constraints )
        if index is None:
            return
        self.log( 'Setting audio stream' )
        self.player.setAudioStream( index )

    def get_player_properties( self, which_property ):
        if not xbmc.getCondVisibility( 'Player.HasVideo' ):
            self.log( 'No video, doing nothing' )
            return
        player_id = get_player_id()
        if player_id == -1:
            self.log( 'No player_id, cancelled' )
            return
        return json_rpc(
            method = 'Player.GetProperties',
            params = dict(
                playerid = player_id,
                properties = [ which_property ],
            )
        ).get( which_property,
               [] )

    def pick_appropriate( self, items, constraints ):
        # apply these one by one
        for description, constraint in constraints.items():
            result = next(
                ( item for item in items if constraint( item ) ),
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
