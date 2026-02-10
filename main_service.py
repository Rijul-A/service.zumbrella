import os

import xbmc, xbmcaddon

from common import ( get_player_id, json_rpc, KodiJSONRPCError )
from logger import Logger
from monitor import Monitor
from player import Player
from webhook_service import WebhookControl


class MainService( Logger ):
    __SETTING_LOG_MODE_BOOL__ = "debug"
    __SETTING_PREFERRED_LANGUAGE__ = "preferred_language"
    __SETTING_WEBHOOK_URL__ = "webhook_url"

    def __init__( self ):
        try:
            self.addon = xbmcaddon.Addon()
            self.monitor = Monitor(
                reloadAction = self.onSettingsChanged,
                screensaverAction = self.onScreensaverActivated,
                descreensaverAction = self.onScreensaverDeactivated,
                notificationAction = self.onNotification
            )
            self.player = Player(
                avStartedAction = self.onAVStarted,
                playBackPausedAction = self.onPlayBackPaused,
                playBackResumedAction = self.onPlayBackResumed,
                playBackEndedAction = self.onPlayBackEnded,
                playbackErrorAction = self.onPlayBackError,
                playBackStoppedAction = self.onPlayBackStopped,
            )
            webhook_settings_valid = self.refresh_settings()
            if webhook_settings_valid:
                self.webhook_control = WebhookControl( self.webhook_url )
            else:
                self.webhook_control = None
                self.log(
                    'Webhook settings not configured, Webhook control disabled',
                    xbmc.LOGWARNING
                )
        except Exception as e:
            self.log(
                'Failed to initialize MainService: %s' % str( e ),
                xbmc.LOGERROR
            )
            raise

    def onNotification( self, sender, method, data ):
        if sender == 'service.zumbrella':
            if self.webhook_control is None:
                self.log(
                    'Webhook control not available (settings not configured)',
                    xbmc.LOGDEBUG
                )
                return
            # For some reason, the method is prefixed with "Other."
            method = method.replace( 'Other.', '' )
            self.webhook_control.run( method, data )

    def onAVStarted( self ):
        self.log( 'onAVStarted' )
        try:
            self.change_audio_stream()
        except Exception as e:
            self.log(
                'Error in change_audio_stream: %s' % str( e ),
                xbmc.LOGERROR
            )
        try:
            self.activate_subtitles()
        except Exception as e:
            self.log(
                'Error in activate_subtitles: %s' % str( e ),
                xbmc.LOGERROR
            )

    def onPlayBackPaused( self ):
        self.log( 'onPlayBackPaused' )

    def onPlayBackResumed( self ):
        self.log( 'onPlayBackResumed' )

    def onPlayBackEnded( self ):
        self.log( 'onPlayBackEnded' )

    def onPlayBackError( self ):
        self.log( 'onPlayBackError' )

    def onPlayBackStopped( self ):
        self.log( 'onPlayBackStopped' )

    def onScreensaverActivated( self ):
        self.log( 'onScreensaverActivated' )
        if self.webhook_control is not None:
            # we use `_off` to indicate turn off; for some reason,
            # this event is fired multiple times after the screensaver
            # is first activated. we only want to turn off the TV once.
            self.webhook_control.run( 'onScreensaverActivated' )

    def onScreensaverDeactivated( self ):
        self.log( 'onScreensaverDeactivated' )
        if self.webhook_control is not None:
            self.webhook_control.run( 'onScreensaverDeactivated' )

    def onSettingsChanged( self ):
        Logger.set_log_mode( xbmc.LOGINFO )
        self.log( 'Received notification to reload settings, doing so now' )
        webhook_settings_valid = self.refresh_settings()
        # Recreate bravia_control if settings changed
        if webhook_settings_valid:
            try:
                self.webhook_control = WebhookControl( self.webhook_url )
                self.log( 'Webhook control reinitialized with new settings' )
            except Exception as e:
                self.log(
                    'Failed to reinitialize Webhook control: %s' % str( e ),
                    xbmc.LOGERROR
                )
                self.webhook_control = None
        else:
            self.webhook_control = None
            self.log( 'Webhook control disabled due to invalid settings' )

    def refresh_settings( self ):
        try:
            self.log( 'Reading settings' )
            debugMode = self.addon.getSetting(
                MainService.__SETTING_LOG_MODE_BOOL__
            ) == 'true'
            self.log( 'debugMode: {}'.format( debugMode ) )
            self.webhook_url = self.addon.getSetting(
                MainService.__SETTING_WEBHOOK_URL__
            )
            self.log( 'webhook_url: {}'.format( self.webhook_url ) )
            # Validate Webhook settings (non-critical - service can still run)
            webhook_settings_valid = self.webhook_url and self.webhook_url.strip(
            ),
            if not webhook_settings_valid:
                self.log(
                    'Webhook URL is not set in settings. Webhook control disabled.',
                    xbmc.LOGWARNING
                )
                xbmc.executebuiltin(
                    'Notification(Zumbrella Warning, Webhook settings not configured, 5000)'
                )
            if not debugMode:
                self.log( 'Addon going quiet due to debugMode disabled' )
            # When debug mode is ON, use LOGDEBUG (verbose), otherwise LOGINFO (normal)
            Logger.set_log_mode( xbmc.LOGDEBUG if debugMode else xbmc.LOGINFO )
            return webhook_settings_valid
        except Exception as e:
            self.log( 'Error reading settings: %s' % str( e ), xbmc.LOGERROR )
            # Default to INFO level if settings can't be read
            Logger.set_log_mode( xbmc.LOGINFO )
            return False

    def activate_subtitles( self, lang = None ):
        try:
            if lang is None:
                lang = self.addon.getSetting(
                    MainService.__SETTING_PREFERRED_LANGUAGE__
                ) or 'eng'
            self.log(
                'Activating subtitles with language preference: %s' % lang
            )
            if not xbmc.getCondVisibility( 'VideoPlayer.HasSubtitles' ):
                self.log( 'No subtitles available, doing nothing' )
                return
            subtitles = self.get_player_properties( 'subtitles' )
            if subtitles is None:
                self.log( 'Could not get subtitle properties, doing nothing' )
                return
            if not isinstance( subtitles, list ):
                self.log( 'Invalid subtitle data format, doing nothing' )
                return
            # drop the forced subtitles which contain only certain translations
            # and aren't full subtitles
            self.log( 'Dropping forced subtitles' )
            subtitles = [
                subtitle for subtitle in subtitles if not (
                    subtitle.get( 'isforced', False ) or
                    'forced' in subtitle.get( 'name', '' ).lower()
                )
            ]
            if len( subtitles ) == 0:
                self.log( 'No subtitle available after filtering, cancelled' )
                return
            index = None
            if len( subtitles ) == 1:
                self.log( 'Only one subtitle available, picking it' )
                index = subtitles[ 0 ].get( 'index' )
            else:
                self.log( 'Choosing appropriate subtitle' )
                # our order of preference is:
                # 1. internal subtitle with matching language
                # 2. any subtitle with matching language
                # 3. default subtitle
                # 4. internal subtitle without any language
                # 5. any subtitle without any language
                constraints = {
                    "internal with language": lambda x: x.get( 'language', '' )
                    == lang and 'external' not in x.get( 'name', '' ).lower(),
                    "any with language": lambda x: x.get( 'language', ''
                                                         ) == lang,
                    "prefer default": lambda x: x.get( 'isdefault', False ),
                    "internal without language": lambda x: x.get(
                        'language', ''
                    ) == '' and 'external' not in x.get( 'name', '' ).lower(),
                    "any without language": lambda x: x.get( 'language', ''
                                                            ) == '',
                }
                index = self.pick_appropriate( subtitles, constraints )
            if index is None:
                self.log( 'No appropriate subtitle found' )
                return
            self.log( 'Setting subtitle stream to index %d' % index )
            self.player.setSubtitleStream( index )
            self.log( 'Showing subtitle' )
            self.player.showSubtitles( True )
        except KodiJSONRPCError as e:
            self.log(
                'RPC/Player error in activate_subtitles: %s' % str( e ),
                xbmc.LOGWARNING
            )
        except Exception as e:
            self.log(
                'Unexpected error in activate_subtitles: %s' % str( e ),
                xbmc.LOGERROR
            )

    def change_audio_stream( self, lang = None ):
        try:
            if lang is None:
                lang = self.addon.getSetting(
                    MainService.__SETTING_PREFERRED_LANGUAGE__
                ) or 'eng'
            # do not change audio stream if there is no video
            self.log(
                'Changing audio stream with language preference: %s' % lang
            )
            audio_streams = self.get_player_properties( 'audiostreams' )
            if audio_streams is None:
                self.log(
                    'Could not get audio stream properties, doing nothing'
                )
                return
            if not isinstance( audio_streams, list ):
                self.log( 'Invalid audio stream data format, doing nothing' )
                return
            if len( audio_streams ) == 0:
                self.log( 'No audio stream available, cancelled' )
                return
            index = None
            if len( audio_streams ) == 1:
                self.log( 'Only one audio stream available, picking it' )
                index = audio_streams[ 0 ].get( 'index' )
            else:
                self.log( 'Choosing appropriate audio stream' )
                constraints = {
                    "any with language": lambda x: x.get( 'language', ''
                                                         ) == lang,
                    "any without language": lambda x: x.get( 'language', '' ) ==
                    '',
                    "prefer default": lambda x: x.get( 'isdefault', False ),
                }
                index = self.pick_appropriate( audio_streams, constraints )
            if index is None:
                self.log( 'No appropriate audio stream found' )
                return
            self.log( 'Setting audio stream to index %d' % index )
            self.player.setAudioStream( index )
        except KodiJSONRPCError as e:
            self.log(
                'RPC/Player error in change_audio_stream: %s' % str( e ),
                xbmc.LOGWARNING
            )
        except Exception as e:
            self.log(
                'Unexpected error in change_audio_stream: %s' % str( e ),
                xbmc.LOGERROR
            )

    def get_player_properties( self, which_property ):
        try:
            if not xbmc.getCondVisibility( 'Player.HasVideo' ):
                self.log( 'No video, doing nothing' )
                return None
            player_id = get_player_id()
            if player_id == -1:
                self.log( 'No player_id, cancelled' )
                return None
            result = json_rpc(
                method = 'Player.GetProperties',
                params = dict(
                    playerid = player_id,
                    properties = [ which_property ],
                )
            )
            return result.get( which_property, [] )
        except KodiJSONRPCError as e:
            self.log(
                'JSON-RPC error getting player properties: %s' % str( e ),
                xbmc.LOGWARNING
            )
            return None
        except Exception as e:
            self.log(
                'Unexpected error getting player properties: %s' % str( e ),
                xbmc.LOGERROR
            )
            return None

    def pick_appropriate( self, items, constraints ):
        # apply these one by one
        try:
            for description, constraint in constraints.items():
                result = next(
                    ( item for item in items if constraint( item ) ),
                    {}
                )
                if result:
                    index = result.get( 'index' )
                    if index is not None:
                        self.log(
                            'Matched constraint %s; picking stream #%d' %
                            ( description,
                              index )
                        )
                        return index
            return None
        except Exception as e:
            self.log(
                'Error in pick_appropriate: %s' % str( e ),
                xbmc.LOGERROR
            )
            return None


if __name__ == '__main__':
    main_logger = Logger( os.path.basename( __file__ ) )
    main_logger.log( 'Starting zUmbrella Service' )
    try:
        service = MainService()
        main_logger.log( 'Service initialized successfully' )
        while not service.monitor.abortRequested():
            service.monitor.waitForAbort( 10 )
    except Exception as e:
        main_logger.log(
            'Fatal error in service: %s' % str( e ),
            xbmc.LOGERROR
        )
        raise
    finally:
        main_logger.log( 'Service shutting down' )
