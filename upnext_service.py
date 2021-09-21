import os
from threading import Timer

from kodi_six import xbmc

from still_there_service import StillThereService
from custom_dialog import CustomDialog
import common

class Player(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.log('Instantiating monitor')
        self.playerMonitorAction = kwargs['playerMonitorAction']

    #the below callbacks are used because they are called when kodi moves on to the next file
    #we aren't using onPlayBackPaused because that is a legitimate concern, and long pauses should be taken care of by the Timer
    def onPlayBackEnded(self):
        self.log('Calling playerMonitorAction')
        if self.playerMonitorAction:
            self.playerMonitorAction()

    def onPlayBackStopped(self):
        self.onPlayBackEnded()

    def onPlayBackError(self):
        self.onPlayBackEnded()

    def log(self, msg):
        common.log(self.__class__.__name__, msg)

class UpNextService(StillThereService):
    __SETTING_MIN_VIDEO_COMPLETION_PERCENTAGE__ = "min_video_completion_percentage"

    #overriden
    def refresh_settings(self):
        self.deactivated_file = None
        self.player = Player(playerMonitorAction = self.reset_deactivated_file)
        self.log('Reading settings')
        self.min_video_completion_percentage = common.read_float_setting(self.addon, UpNextService.__SETTING_MIN_VIDEO_COMPLETION_PERCENTAGE__) / 100.0
        self.log('Loaded settings')
        self.log('min_video_completion_percentage: {}'.format(self.min_video_completion_percentage))

    def get_position(self):
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        position = playlist.getposition()
        return playlist, position

    def has_next_item(self):
        playlist, position = self.get_position()
        if playlist.size() > 1:
            if position < (playlist.size() - 1):
                return position, True
        return position, False

    def get_next_item(self):
        self.log('Getting position of current item in playlist')
        position, has_next_item = self.has_next_item()
        self.log('Current position is {}'.format(position))
        if has_next_item:
            self.log('There are more entries in the playlist')
            properties = ['showtitle', 'season', 'episode', 'title']
            params = dict(playlistid = 1, limits = dict(start = position + 1, end = position + 2), properties = properties)
            result = common.json_rpc(method = 'Playlist.GetItems', params = params)
            if result:
                self.log('Got result from playlist')
                items = result.get('result', {}).get('items')
                if items:
                    self.log('Got items from result')
                    return items[0]
        else:
            self.log('No more entries in the playlist')

    #overriden to return next item in the playlist
    def get_item(self):
        return self.get_next_item()

    def reset_deactivated_file(self):
        self.log('Resetting deactivated_file')
        self.deactivated_file = None
        try:
            self.timer.cancel() #kill old timer
            self.timer = None
        except AttributeError:
            pass

    #overriden for %age check
    def do_check(self, inactivity_seconds = None):
        if not xbmc.getCondVisibility('Player.HasVideo'):
            self.log('Not playing videos, doing nothing')
            return
        if not xbmc.getCondVisibility('Player.Playing'):
            self.log('Media is not playing, not doing anything')
            return
        old_position, has_next_item = self.has_next_item()
        if not has_next_item:
            self.log('We are alone in this playlist, no UpNext needed')
            return
        try:
            playing_file = xbmc.Player().getPlayingFile()
            if self.deactivated_file is not None:
                if self.deactivated_file == playing_file:
                    self.log('File {} which is playing is deactivated'.format(playing_file))
                    return
                else:
                    self.log('File {} is new, turning off old deactivated_file {}'.format(playing_file, self.deactivated_file))
                    self.deactivated_file = None
            else:
                self.log('No file deactivated, currently playing {}'.format(playing_file))
        except RuntimeError:
            self.log('Could not fetch name of file, doing nothing')
            return
        try:
            total_time   = xbmc.Player().getTotalTime()
        except RuntimeError:
            self.log('Could not fetch video total time, doing nothing')
            return
        if total_time == 0:
            self.log('Total time is 0, doing nothing')
            return
        try:
            current_time = xbmc.Player().getTime()
        except RuntimeError:
            self.log('Could not fetch video current time, doing nothing')
            return
        video_completion_percentage = current_time / total_time
        if video_completion_percentage >= self.min_video_completion_percentage:
            max_time_remaining = total_time * (1 - video_completion_percentage) #don't use max here, use the discovery point value
            self.log('Showing UpNext as video_completion_percentage ({}) is >= min_video_completion_percentage ({})'.format(video_completion_percentage, self.min_video_completion_percentage))
            self.update_label()
            self.custom_dialog.update_progress(1.0)
            self.custom_dialog.show()
            new_position, has_next_item = self.has_next_item()
            while((self.custom_dialog.lastControlClicked == CustomDialog.__INVALID_BUTTON_ID__) and (video_completion_percentage < 1.) and (old_position == new_position) and xbmc.getCondVisibility('Player.HasVideo') and (has_next_item)):
                self.sleep(0.01)
                try:
                    current_time   = xbmc.Player().getTime()
                except RuntimeError:
                    self.log('Could not fetch current_time, likely that media finished')
                    break
                video_completion_percentage = current_time / total_time
                time_remaining = total_time * (1 - video_completion_percentage)
                percent        = time_remaining / max_time_remaining
                self.log('Percentage for dialog is {}'.format(round(percent*100, 2)))
                self.custom_dialog.update_progress(percent)
                new_position, has_next_item = self.has_next_item()
            if (self.custom_dialog.lastControlClicked == CustomDialog.__LEFT_BUTTON_ID__):
                self.log('Watching next episode now')
                xbmc.Player().seekTime(total_time)    #seek to end, watch now
            elif (self.custom_dialog.lastControlClicked == CustomDialog.__RIGHT_BUTTON_ID__):
                self.log('Terminating playback')
                xbmc.Player().stop()                                    #clicked on stop
            elif (self.custom_dialog.lastControlClicked == CustomDialog.__MIDDLE_BUTTON_ID__):
                self.log('Setting deactivated_file, UI close was requested')
                self.deactivated_file = playing_file
                #in the event that the user closes the dialog and pauses the video when last 5% is time_remaining
                #show the dialog when they come back by resetting this param
                self.timer = Timer(time_remaining, self.reset_deactivated_file)
                self.timer.start()
            else:
                self.log('Media finished as expected, closing dialog')
                self.custom_dialog.close()
            self.custom_dialog.reset()
        else:
            self.log('Notification is not needed as video_completion_percentage of {} is < min_video_completion_percentage of {}'.format(video_completion_percentage, self.min_video_completion_percentage))

    #overriden for the __file__ var
    def log(self, msg):
        common.log(self.__class__.__name__, msg)
