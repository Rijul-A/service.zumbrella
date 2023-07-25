from threading import Timer

import xbmc

from common import ( json_rpc, read_float_setting )
from custom_dialog import CustomDialog
from logger import Logger
from still_there_service import StillThereService


class UpNextService( StillThereService, Logger ):
    __SETTING_MIN_VIDEO_COMPLETION_PERCENTAGE__ = "min_video_completion_percentage"

    def onAVStarted( self ):
        self.onPlayBackResumed()

    def onPlayBackPaused( self ):
        self.custom_dialog.set_left_button_text(
            self.addon.getLocalizedString( CustomDialog.__STRING_PLAY__ )
        )

    def onPlayBackResumed( self ):
        self.custom_dialog.set_left_button_text(
            self.addon.getLocalizedString( CustomDialog.__STRING_PAUSE__ )
        )

    def refresh_settings( self ):
        self.deactivated_file = None
        self.log( 'Reading settings' )
        self.min_video_completion_percentage = read_float_setting(
            self.addon,
            UpNextService.__SETTING_MIN_VIDEO_COMPLETION_PERCENTAGE__
        ) / 100.0
        self.log( 'Loaded settings' )
        self.log(
            'min_video_completion_percentage: {}'.format(
                self.min_video_completion_percentage
            )
        )

    def update_progress( self ):
        if not self.custom_dialog.visible:
            return False
        try:
            current_time = xbmc.Player().getTime()
        except RuntimeError:
            self.log(
                'Could not fetch current_time, likely that media finished'
            )
            self.custom_dialog.close()
            return False
        new_position, has_next_item = self.has_next_item()
        if new_position != self.old_position:
            # next one is already playing
            self.custom_dialog.close()
            return False
        if not has_next_item:
            # unlikely to occur
            self.custom_dialog.close()
            return False
        video_completion_percentage = current_time / self.total_time
        if video_completion_percentage >= 1.:
            # unlikely to occur
            self.custom_dialog.close()
            return False
        self.time_remaining = self.total_time * (
            1 - video_completion_percentage
        )
        percent = self.time_remaining / self.max_time_remaining
        self.custom_dialog.update_progress( percent )
        return True

    def onCustomDialogClick( self, controlId ):
        if ( controlId == CustomDialog.__LEFT_BUTTON_ID__ ):
            self.log( 'Play/Pause' )
            xbmc.Player().pause()
        elif (
            self.custom_dialog.lastControlClicked ==
            CustomDialog.__MIDDLE_BUTTON_ID__
        ):
            self.custom_dialog.close()
            self.log( 'Next episode' )
            xbmc.Player().playnext()
        elif ( controlId == CustomDialog.__RIGHT_BUTTON_ID__ ):
            self.custom_dialog.close()
            self.log( 'Setting deactivated_file, UI close was requested' )
            self.deactivated_file = xbmc.Player().getPlayingFile()
            # in the event that the user closes the dialog and
            # pauses the video when last 5% is time_remaining
            # show the dialog when they come back by resetting this param
            self.timer = Timer(
                self.time_remaining,
                self.reset_deactivated_file
            )
            self.timer.start()

    def get_position( self ):
        playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
        position = playlist.getposition()
        return playlist, position

    def has_next_item( self ):
        playlist, position = self.get_position()
        if playlist.size() > 1:
            if position < ( playlist.size() - 1 ):
                return position, True
        return position, False

    def get_next_item( self ):
        self.log( 'Getting position of current item in playlist' )
        position, has_next_item = self.has_next_item()
        self.log( 'Current position is {}'.format( position ) )
        if has_next_item:
            self.log( 'There are more entries in the playlist' )
            properties = [ 'showtitle', 'season', 'episode', 'title' ]
            params = dict(
                playlistid = 1,
                limits = dict( start = position + 1,
                               end = position + 2 ),
                properties = properties
            )
            return json_rpc( method = 'Playlist.GetItems',
                             params = params ).get( 'items',
                                                    [ None ] )[ 0 ]
        else:
            self.log( 'No more entries in the playlist' )

    def get_item( self ):
        return self.get_next_item()

    def reset_deactivated_file( self ):
        self.log( 'Resetting deactivated_file' )
        self.deactivated_file = None
        try:
            self.timer.cancel()
            self.timer = None
        except AttributeError:
            pass

    def do_check( self, inactivity_seconds ):
        if not xbmc.getCondVisibility( 'Player.HasVideo' ):
            self.log( 'Not playing videos, doing nothing' )
            return
        if not xbmc.getCondVisibility( 'Player.Playing' ):
            self.log( 'Media is not playing, not doing anything' )
            return
        self.old_position, has_next_item = self.has_next_item()
        if not has_next_item:
            self.log( 'We are alone in this playlist, no UpNext needed' )
            return
        try:
            playing_file = xbmc.Player().getPlayingFile()
            if self.deactivated_file is not None:
                if self.deactivated_file == playing_file:
                    self.log(
                        'File {} which is playing is deactivated'
                        .format( playing_file )
                    )
                    return
                else:
                    self.log(
                        'File {} is new, turning off old deactivated_file {}'
                        .format( playing_file,
                                 self.deactivated_file )
                    )
                    self.deactivated_file = None
            else:
                self.log(
                    'No file deactivated, currently playing {}'
                    .format( playing_file )
                )
        except RuntimeError:
            self.log( 'Could not fetch name of file, doing nothing' )
            return
        try:
            self.total_time = xbmc.Player().getTotalTime()
        except RuntimeError:
            self.log( 'Could not fetch video total time, doing nothing' )
            return
        if self.total_time == 0:
            self.log( 'Total time is 0, doing nothing' )
            return
        try:
            current_time = xbmc.Player().getTime()
        except RuntimeError:
            self.log( 'Could not fetch video current time, doing nothing' )
            return
        video_completion_percentage = current_time / self.total_time
        if video_completion_percentage >= self.min_video_completion_percentage:
            self.max_time_remaining = self.total_time * (
                1 - video_completion_percentage
            )  # don't use max here, use the discovery point value
            self.log(
                'Showing UpNext as video_completion_percentage ({}) is >= min_video_completion_percentage ({})'
                .format(
                    video_completion_percentage,
                    self.min_video_completion_percentage
                )
            )
            self.update_label()
            self.custom_dialog.update_progress( 1.0 )
            self.custom_dialog.show()
            self.onPlayBackResumed()
            self.sleep( 0.01, self.update_progress )
        else:
            self.log(
                'Notification is not needed as video_completion_percentage of {} is < min_video_completion_percentage of {}'
                .format(
                    video_completion_percentage,
                    self.min_video_completion_percentage
                )
            )
