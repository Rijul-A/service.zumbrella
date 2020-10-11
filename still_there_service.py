import os

import xbmc

import common
from custom_dialog import CustomDialog

class StillThereService:
    __SETTING_NOTIFICATION_DURATION__ = "notification_duration"
    __SETTING_ENABLE_VIDEO_SUPERVISION__ = "enable_video_supervision"
    __SETTING_VIDEO_INACTIVITY_THRESHOLD__ = "video_inactivity_threshold"
    __SETTING_ENABLE_AUDIO_SUPERVISION__ = "enable_audio_supervision"
    __SETTING_AUDIO_INACTIVITY_THRESHOLD__ = "audio_inactivity_threshold"

    __MAX_TRIES__ = 100

    def __init__(self, addon, monitor, xmlname):
        self.log('Creating object')
        self.addon = addon  #to load settings
        self.monitor = monitor  #to sleep
        self.custom_dialog = CustomDialog(xmlname, self.addon.getAddonInfo('path').decode('utf-8'), 'default', '1080i')

    def refresh_settings(self):
        self.log('Reading settings')
        self.notification_duration = common.read_int_setting(self.addon, StillThereService.__SETTING_NOTIFICATION_DURATION__, False)  #in seconds already, will not be 0 so False
        self.enable_video_supervision = common.read_bool_setting(self.addon, StillThereService.__SETTING_ENABLE_VIDEO_SUPERVISION__)
        self.video_inactivity_threshold = common.read_int_setting(self.addon, StillThereService.__SETTING_VIDEO_INACTIVITY_THRESHOLD__)
        self.enable_audio_supervision = common.read_bool_setting(self.addon, StillThereService.__SETTING_ENABLE_AUDIO_SUPERVISION__)
        self.audio_inactivity_threshold = common.read_int_setting(self.addon, StillThereService.__SETTING_AUDIO_INACTIVITY_THRESHOLD__)
        self.log('Loaded settings')
        self.log('notification_duration: {}'.format(self.notification_duration))
        self.log('enable_video_supervision: {}'.format(self.enable_audio_supervision))
        self.log('video_inactivity_threshold: {}'.format(self.video_inactivity_threshold))
        self.log('enable_audio_supervision: {}'.format(self.enable_audio_supervision))
        self.log('audio_inactivity_threshold: {}'.format(self.audio_inactivity_threshold))

    def sleep(self, duration):
        if self.monitor.waitForAbort(duration):
            exit()

    def get_player_id(self):
        result = {}
        tries = 0
        while not result.get('result') and tries < StillThereService.__MAX_TRIES__:
            self.log('Trying to obtain active player')
            result = common.json_rpc(method='Player.GetActivePlayers')
            tries = tries + 1
        if not result.get('result'):
            self.log('Did not found any active players')
            return
        return result.get('result')[0].get('playerid')

    def get_current_item(self):
        playerid = self.get_player_id()
        if playerid is None:
            return
        self.log('Found active player with id: {}'.format(playerid))
        if xbmc.getCondVisibility('Player.HasAudio'):
            properties = ['title', 'album', 'artist']
            id = 'AudioGetItem'
        else:
            properties = ['showtitle', 'season', 'episode', 'title']
            id = 'VideoGetItem'
        requested_params = dict(playerid = playerid, properties = properties)
        result = common.json_rpc(method = 'Player.GetItem', params = requested_params, id = id)
        item = result.get('result').get('item')
        return item

    def get_item(self):
        return self.get_current_item()

    def update_label(self):
        item = self.get_item()
        if item is None:
            self.log('Setting no title on the dialog')
            self.custom_dialog.set_label('')
            return
        if 'showtitle' in item:
            showtitle = item.get('showtitle').encode('utf-8')
            title     = item.get('title').encode('utf-8')
            if showtitle:
                season    = "%02d" % int(item.get('season'))
                episode   = "%02d" % int(item.get('episode'))
                label     = '{0} {1} S{2}E{3} {1} {4}'.format(showtitle, u"\u2022", season, episode, title)
            else:
                label = title
        elif 'artist' in item:   #music
            title     = item.get('title').encode('utf-8')
            artist    = item.get('artist').encode('utf-8')
            album     = item.get('album').encode('utf-8')
            label     = '{0} {1} {2} {1} {3}'.format(title, u"\u2022", artist, album)
        else:                   #item type will be file, movie, musicvideo, livetv
            label     = item.get('title').encode('utf-8')
        self.custom_dialog.set_label(label)
        self.log('Successfully set title on the dialog')

    def do_check(self, inactivity_seconds = None):
        threshold = None
        if not xbmc.getCondVisibility('Player.HasMedia'):
            self.log('No media, not doing anything in check_for_media_inactivity')
            return
        self.log('We have media, checking if it is playing and if we are supervising')
        if xbmc.getCondVisibility('Player.Playing'):    #means has media which is not (paused, rewinding, or forwarding)
            self.log('It is playing')
            if xbmc.getCondVisibility('Player.HasAudio'):
                self.log('It is audio')
                if self.enable_audio_supervision:
                    threshold = self.audio_inactivity_threshold
                    self.log('We are supervising it')
                else:
                    self.log('We are not supervising it')
            elif xbmc.getCondVisibility('Player.HasVideo'):
                self.log('It is video')
                if self.enable_video_supervision:
                    threshold = self.video_inactivity_threshold
                    self.log('We are supervising it')
                else:
                    self.log('We are not supervising it')
            else:
                self.log('It is something unsupported by this addon')
                return
            if threshold is not None:
                if inactivity_seconds >= threshold:
                    self.log('Inactive time of {} seconds is >= than the threshold of {} seconds, showing the GUI'.format(inactivity_seconds, threshold))
                    self.update_label()
                    self.custom_dialog.show()
                    elapsed_time = 0.0    #starts at 0 because we sleep immediately on enterting the loop, and add 1 after
                    while((elapsed_time < self.notification_duration) and (self.custom_dialog.lastControlClicked == CustomDialog.__INVALID_BUTTON_ID__) and xbmc.getCondVisibility('Player.Playing')):
                        self.sleep(0.01)   #0.01 second
                        elapsed_time = elapsed_time + 0.01   #add 0.01 second to it and keep adding till you reach the level
                        percent = 1 - (elapsed_time / float(self.notification_duration))
                        self.log('Percentage of {} seconds remaning is {}'.format(self.notification_duration, round(percent*100, 2)))
                        self.custom_dialog.update_progress(percent)
                    if self.custom_dialog.lastControlClicked == CustomDialog.__LEFT_BUTTON_ID__:
                        self.log('Continue was pressed, which means do nothing')
                    elif self.custom_dialog.lastControlClicked == CustomDialog.__RIGHT_BUTTON_ID__:
                        self.log('Pause was requested')
                        xbmc.Player().pause()
                        self.log('Paused media')
                    elif self.custom_dialog.lastControlClicked == CustomDialog.__INVALID_BUTTON_ID__:
                        self.log('No response, closing dialog and pausing')
                        self.custom_dialog.close()
                        if xbmc.getCondVisibility('Player.Playing'):
                            xbmc.Player().pause()
                            self.log('Paused media')
                        else:
                            self.log('Media was paused externally, not doing anything')
                    self.custom_dialog.reset()
                else:
                    self.log('Inactive time of {} seconds is < than the threshold of {} seconds, not doing anything'.format(inactivity_seconds, threshold))
            else:
                self.log('Nothing to supervise, skipping')
        else:
            self.log('It is not playing')

    def log(self, msg):
        common.log(self.__class__.__name__, msg)
