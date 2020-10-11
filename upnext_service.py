import os
from threading import Timer

import xbmc

from still_there_service import StillThereService
from custom_dialog import CustomDialog
import common

class Player(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.log('Instantiating monitor')
        self.playerMonitorAction = kwargs['playerMonitorAction']

    def onPlayBackEnded(self):
        if self.playerMonitorAction:
            self.playerMonitorAction()

    def onPlayBackStopped(self):
        self.onPlayBackEnded()

    def onPlayBackError(self):
        self.onPlayBackEnded()

    def log(self, msg):
        common.log(self.__class__.__name__, msg)

class UpNextService(StillThereService):
    __SETTING_LAST_X_MINUTES__ = "last_x_minutes"

    #overriden
    def refresh_settings(self):
        self.deactivated_file = None
        self.player = Player(playerMonitorAction = self.reset_deactivated_file)
        self.log('Reading settings')
        self.max_time_remaining = common.read_int_setting(self.addon, UpNextService.__SETTING_LAST_X_MINUTES__)
        self.log('Loaded settings')
        self.log('max_time_remaining: {}'.format(self.max_time_remaining))

    def get_position(self):
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        position = playlist.getposition()
        return playlist, position

    #overriden to return next item in the playlist
    def get_item(self):
        self.log('Getting position of current item in playlist')
        playlist, position = self.get_position()
        self.log('Current position is {}'.format(position))
        if playlist.size() > 1:
            if position < (playlist.size() - 1):
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

    def reset_deactivated_file(self):
        self.log('Resetting deactivated_file')
        self.deactivated_file = None

    #overriden for %age check
    def do_check(self, inactivity_seconds = None):
        if not xbmc.getCondVisibility('Player.HasVideo'):
            self.log('Not playing videos, doing nothing')
            return
        if not xbmc.getCondVisibility('Player.Playing'):
            self.log('Media is not playing, not doing anything')
            return
        try:
            playing_file = xbmc.Player().getPlayingFile()
            if self.deactivated_file is not None:
                if self.deactivated_file == playing_file:
                    self.log('File {} which is playing is deactivated'.format(playing_file))
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
            self.log('Could not fetch video time, doing nothing')
            return
        current_time = xbmc.Player().getTime()
        time_remaining = total_time - current_time
        if time_remaining <= self.max_time_remaining:
            _, old_position = self.get_position()
            self.log('Notification is needed as time_remaining of {} seconds is <= max_time_remaining of {} seconds'.format(time_remaining, self.max_time_remaining))
            self.update_label()
            self.custom_dialog.show()
            while((self.custom_dialog.lastControlClicked == CustomDialog.__INVALID_BUTTON_ID__) and (time_remaining > 0) and (old_position == self.get_position()[1]) and xbmc.getCondVisibility('Player.HasVideo')):
                self.sleep(0.01)
                try:
                    current_time   = xbmc.Player().getTime()
                except RuntimeError:
                    self.log('Could not fetch current_time, likely that media finished')
                    break
                time_remaining = total_time - current_time
                percent        = float(time_remaining) / float(self.max_time_remaining)
                self.log('Percentage of max_time_remaining is {}'.format(round(percent*100, 2)))
                self.custom_dialog.update_progress(percent)
            if (self.custom_dialog.lastControlClicked == CustomDialog.__LEFT_BUTTON_ID__):
                self.log('Watching next episode now')
                xbmc.Player().seekTime(total_time)    #seek to end, watch now
            elif (self.custom_dialog.lastControlClicked == CustomDialog.__RIGHT_BUTTON_ID__):
                self.log('Terminating playback')
                xbmc.Player().stop()                                    #clicked on stop
            elif (self.custom_dialog.lastControlClicked == CustomDialog.__MIDDLE_BUTTON_ID__):
                self.log('Setting deactivated_file, UI close was requested')
                self.deactivated_file = playing_file
                Timer(self.max_time_remaining, self.reset_deactivated_file)
            else:
                self.log('Media finished as expected, closing dialog')
                self.custom_dialog.close()
            self.custom_dialog.reset()
        else:
            self.log('Notification is not needed as time_remaining of {} seconds is > max_time_remaining of {} seconds'.format(time_remaining, self.max_time_remaining))

    #overriden for the __file__ var
    def log(self, msg):
        common.log(self.__class__.__name__, msg)
