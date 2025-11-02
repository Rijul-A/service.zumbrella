import six
import subprocess
import time

import xbmc, xbmcgui

from common import (
    get_player_id,
    json_rpc,
    read_bool_setting,
    read_int_setting,
    VIDEO_WINDOW_IDS
)
from custom_dialog import CustomDialog
from logger import Logger


class StillThereService( Logger ):
    __SETTING_NOTIFICATION_DURATION__ = "notification_duration"
    __SETTING_ENABLE_VIDEO_SUPERVISION__ = "enable_video_supervision"
    __SETTING_VIDEO_INACTIVITY_THRESHOLD__ = "video_inactivity_threshold"
    __SETTING_ENABLE_AUDIO_SUPERVISION__ = "enable_audio_supervision"
    __SETTING_AUDIO_INACTIVITY_THRESHOLD__ = "audio_inactivity_threshold"

    def __init__( self, addon, monitor, xmlname, main_service ):
        self.log( 'Creating object' )
        self.addon = addon  # to load settings
        self.monitor = monitor  # to sleep
        self.custom_dialog = CustomDialog(
            xmlname,
            self.addon.getAddonInfo( 'path' ),
            'default',
            '1080i',
            onClick = self.onCustomDialogClick
        )
        self.last_continue_click_time = None
        self.main_service = main_service

    def onAVStarted( self ):
        pass

    def onPlayBackPaused( self ):
        pass

    def onPlayBackResumed( self ):
        self.log( 'Playback resumed, saving the time' )
        self.last_continue_click_time = time.time()

    def onPlayBackEnded( self ):
        pass

    def onPlayBackError( self ):
        pass

    def onPlayBackStopped( self ):
        pass

    def onScreensaverActivated( self ):
        pass

    def refresh_settings( self ):
        self.log( 'Reading settings' )
        self.notification_duration = read_int_setting(
            self.addon,
            StillThereService.__SETTING_NOTIFICATION_DURATION__,
            False
        )  # in seconds already, will not be 0 so False
        self.enable_video_supervision = read_bool_setting(
            self.addon,
            StillThereService.__SETTING_ENABLE_VIDEO_SUPERVISION__
        )
        self.video_inactivity_threshold = read_int_setting(
            self.addon,
            StillThereService.__SETTING_VIDEO_INACTIVITY_THRESHOLD__
        )
        self.enable_audio_supervision = read_bool_setting(
            self.addon,
            StillThereService.__SETTING_ENABLE_AUDIO_SUPERVISION__
        )
        self.audio_inactivity_threshold = read_int_setting(
            self.addon,
            StillThereService.__SETTING_AUDIO_INACTIVITY_THRESHOLD__
        )
        self.log( 'Loaded settings' )
        self.log(
            'notification_duration: {}'.format( self.notification_duration )
        )
        self.log(
            'enable_video_supervision: {}'.format(
                self.enable_audio_supervision
            )
        )
        self.log(
            'video_inactivity_threshold: {}'.format(
                self.video_inactivity_threshold
            )
        )
        self.log(
            'enable_audio_supervision: {}'.format(
                self.enable_audio_supervision
            )
        )
        self.log(
            'audio_inactivity_threshold: {}'.format(
                self.audio_inactivity_threshold
            )
        )

    def update_progress( self ):
        elapsed_time = time.time() - self.start_time
        # for a maximum of 90 seconds this will be shown
        if elapsed_time < self.notification_duration and self.custom_dialog.visible:
            percent = 1 - ( elapsed_time / float( self.notification_duration ) )
            self.log(
                'Percentage of {} seconds remaning is {}'.format(
                    self.notification_duration,
                    round( percent * 100,
                           2 )
                )
            )
            self.custom_dialog.update_progress( percent )
            return True
        # we ran out of time while it was visible
        elif self.custom_dialog.visible:
            self.custom_dialog.close()
            self.log( 'No response, closing dialog and pausing' )
            if xbmc.getCondVisibility( 'Player.Playing' ):
                xbmc.Player().pause()
                self.log( 'Paused media' )
            else:
                self.log( 'Media was paused externally, not doing anything' )
        return False

    def onCustomDialogClick( self, controlId ):
        if controlId == CustomDialog.__LEFT_BUTTON_ID__:
            self.custom_dialog.close()
            self.log( 'Continue was pressed, which means note down this time' )
            self.last_continue_click_time = time.time()
        elif controlId == CustomDialog.__RIGHT_BUTTON_ID__:
            self.custom_dialog.close()
            self.log( 'Pause was requested' )
            xbmc.Player().pause()
            self.log( 'Paused media' )

    def get_current_item( self ):
        playerid = get_player_id()
        if playerid == -1:
            return
        self.log( 'Found active player with id: {}'.format( playerid ) )
        if xbmc.getCondVisibility( 'Player.HasAudio' ):
            properties = [ 'title', 'album', 'artist', 'file' ]
        else:
            properties = [ 'showtitle', 'season', 'episode', 'title', 'file' ]
        requested_params = dict( playerid = playerid, properties = properties )
        return json_rpc( method = 'Player.GetItem',
                         params = requested_params ).get( 'item' )

    def get_item( self ):
        return self.get_current_item()

    def update_label( self ):
        item = self.get_item()
        if item is None:
            self.log( 'Setting no title on the dialog' )
            self.custom_dialog.set_label( '' )
            return
        if 'showtitle' in item:  # TV show
            showtitle = item.get( 'showtitle' ) if six.PY3 else item.get(
                'showtitle'
            ).encode( 'utf-8' )
            title = item.get( 'title' ) if six.PY3 else item.get(
                'title'
            ).encode( 'utf-8' )
            if showtitle:
                season = "%02d" % int( item.get( 'season' ) )
                episode = "%02d" % int( item.get( 'episode' ) )
                label = '{0} {1} S{2}E{3} {1} {4}'.format(
                    showtitle,
                    u"\u2022",
                    season,
                    episode,
                    title
                )
            else:
                label = title
        elif 'artist' in item:  # music
            title = item.get( 'title' ) if six.PY3 else item.get(
                'title'
            ).encode( 'utf-8' )
            artist = item.get( 'artist' ) if six.PY3 else item.get(
                'artist'
            ).encode( 'utf-8' )
            album = item.get( 'album' ) if six.PY3 else item.get(
                'album'
            ).encode( 'utf-8' )
            label = '{0} {1} {2} {1} {3}'.format(
                title,
                u"\u2022",
                artist,
                album
            )
        elif 'title' in item:  # item type will be movie, musicvideo, livetv
            label = item.get( 'title' ) if six.PY3 else item.get(
                'title'
            ).encode( 'utf-8' )
        else:  # playing a file
            label = item.get( 'file' ) if six.PY3 else item.get(
                'file'
            ).encode( 'utf-8' )
        self.custom_dialog.set_label( label )
        self.log( 'Successfully set title on the dialog' )

    def do_check( self, inactivity_seconds = None ):
        threshold = None
        if not xbmc.getCondVisibility( 'Player.HasMedia' ):
            self.log(
                'No media, not doing anything in check_for_media_inactivity'
            )
            return
        self.log( 'We have media, checking if we are supervising' )
        if xbmc.getCondVisibility( 'Player.HasAudio' ):
            self.log( 'It is audio' )
            if self.enable_audio_supervision:
                threshold = self.audio_inactivity_threshold
                self.log( 'We are supervising it' )
            else:
                self.log( 'We are not supervising it' )
        elif xbmc.getCondVisibility( 'Player.HasVideo' ):
            self.log( 'It is video' )
            if self.enable_video_supervision:
                threshold = self.video_inactivity_threshold
                self.log( 'We are supervising it' )
            else:
                self.log( 'We are not supervising it' )
        else:
            self.log( 'It is something unsupported by this addon' )
            return
        if threshold is not None:
            condition = inactivity_seconds >= threshold and \
                        ((self.last_continue_click_time is None) or \
                            (self.last_continue_click_time is not None and \
                            time.time() - self.last_continue_click_time >= threshold / 2))
            current_window_id = xbmcgui.getCurrentWindowId()
            if current_window_id not in VIDEO_WINDOW_IDS:
                self.log( 'Current window is not a video window' )
                return
            if condition:
                if xbmc.getCondVisibility( 'Player.Playing' ):
                    self.log(
                        'Inactive time of {} seconds is >= than the '
                        'threshold of {} seconds, showing the GUI'.format(
                            inactivity_seconds,
                            threshold
                        )
                    )
                    self.update_label()
                    self.custom_dialog.update_progress( 1.0 )
                    self.start_time = time.time()
                    self.custom_dialog.show()
                    self.sleep( 0.01, self.update_progress )
                else:
                    self.log(
                        'Exceeded idle time, stopping media and'
                        'turning off the TV'
                    )
                    xbmc.Player().stop()
                    # use the main service to request tv turn off
                    # self.main_service.tv_service.power( False )
            else:
                self.log(
                    'Inactive time of {} seconds is < than the '
                    'threshold of {} seconds, not doing anything'.format(
                        inactivity_seconds,
                        threshold
                    )
                )
        else:
            self.log( 'Nothing to supervise, skipping' )

    def sleep( self, duration, callback = None ):
        if self.monitor.waitForAbort( duration ):
            exit()
        if callback:
            while ( callback() ):
                self.sleep( duration )
