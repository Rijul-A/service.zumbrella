import os

from kodi_six import xbmc, xbmcaddon

import common
from main_monitor import MainMonitor
from bluetooth_service import BluetoothService
from still_there_service import StillThereService
from upnext_service import UpNextService

class Player(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.log('Instantiating monitor')
        self.avStartedAction = kwargs.get('avStartedAction')
        self.onPlayBackPausedAction = kwargs.get('onPlayBackPaused')
        self.onPlayBackResumedAction = kwargs.get('onPlayBackResumed')

    def onAVStarted(self):
        if self.avStartedAction:
            self.avStartedAction()

    def onPlayBackPaused(self):
        if self.onPlayBackPausedAction:
            self.onPlayBackPausedAction()

    def onPlayBackResumed(self):
        if self.onPlayBackResumedAction:
            self.onPlayBackResumedAction()

    def log(self, msg):
        common.log(self.__class__.__name__, msg)

class MainService:
    __SETTING_LOG_MODE_BOOL__ = "debug"
    __SETTING_CHECK_TIME__ = 'check_time'

    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.monitor = MainMonitor(reloadAction = self.onSettingsChanged, screensaverAction = self.onScreensaverActivated)
        self.player = Player(avStartedAction = self.onAVStarted, onPlayBackPaused = self.onPlayBackPaused, onPlayBackResumed = self.onPlayBackResumed)
        self.bluetooth_service = BluetoothService(self.addon)
        self.still_there_service = StillThereService(self.addon, self.monitor, 'still_there.xml')
        self.upnext_service = UpNextService(self.addon, self.monitor, 'up_next.xml')
        self.refresh_settings()

    def onPlayBackPaused(self):
        self.upnext_service.onPlayBackPaused()

    def onPlayBackResumed(self):
        self.still_there_service.onPlayBackResumed()
        self.upnext_service.onPlayBackResumed()

    def onSettingsChanged(self):
        common.logMode = xbmc.LOGINFO #activate debug mode
        self.log('Received notification to reload settings, doing so now')
        self.__init__()

    def onScreensaverActivated(self):
        self.log('Received screensaver notification')
        self.bluetooth_service.onScreensaverActivated()
        self.still_there_service.onScreensaverActivated()
        self.upnext_service.onScreensaverActivated()

    def onAVStarted(self):
        self.log('Received playback started notification')
        if xbmc.getCondVisibility('Player.HasVideo'):
            self.log('Detected that it is video')
            self.player.showSubtitles(True)

    def sleep(self, duration = None):
        if duration is None:
            duration = self.check_time
        self.log('Waiting {} seconds for next check'.format(duration))
        if self.monitor.waitForAbort(duration):
            exit()

    def refresh_settings(self):
        self.log('Reading settings')
        self.bluetooth_service.refresh_settings()
        self.still_there_service.refresh_settings()
        self.upnext_service.refresh_settings()
        self.check_time = common.read_int_setting(self.addon, MainService.__SETTING_CHECK_TIME__)
        debugMode = self.addon.getSetting(MainService.__SETTING_LOG_MODE_BOOL__) == 'true'
        self.log('debugMode: {}'.format(debugMode))
        if not debugMode:
            self.log('Addon going quiet due to debugMode')
        common.logMode = xbmc.LOGINFO if debugMode else xbmc.LOGDEBUG #now go quiet if needed

    def do_checks(self):
        self.sleep()
        inactivity_seconds = xbmc.getGlobalIdleTime()
        self.log('Inactive time is {} seconds'.format(inactivity_seconds))
        self.bluetooth_service.do_check(inactivity_seconds)
        self.still_there_service.do_check(inactivity_seconds)
        self.upnext_service.do_check()  #no need to pass as it is None

    def log(self, msg):
        common.log(self.__class__.__name__, msg)

if __name__ == '__main__':
    common.log(os.path.basename(__file__), 'Creating object')
    object = MainService()
    while not object.monitor.abortRequested():
        object.do_checks()   #do not kill the service because keeping it loaded in memory is needed to reload settings
    else:
        object.log('No eligible devices to disconnect, disabling service')
