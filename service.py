import xbmc, xbmcgui, xbmcaddon

import subprocess
import json
import codecs
import re
import datetime as dt

import common

class Monitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.reloadAction = kwargs['reloadAction']
        self.screensaverAction = kwargs['screensaverAction']

    def onSettingsChanged(self):
        self.reloadAction()

    def onScreensaverActivated(self):
        self.screensaverAction()

class WatcherService:
    __DISCONNECTION_ELIGIBILITY_TIME_NOT_ELAPSED__ = -2
    __DISCONNECTION_ELIGIBILITY_NO_NEW_DEVICE__ = -1
    __DISCONNECTION_ELIGIBILITY_YES__ = 1

    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.dialog = xbmcgui.Dialog()
        self.monitor = Monitor(reloadAction = self.onSettingsChanged, screensaverAction = self.onScreensaverActivated)
        self.logFile = codecs.open(xbmc.translatePath(r'special://logpath/kodi.log'), 'r', encoding = 'utf-8', errors = 'ignore')
        self.logFileLastSize = 0    #for first run, read from top
        self.refresh_settings()

    def onSettingsChanged(self):
        common.logMode = xbmc.LOGNOTICE #activate debug mode
        self.log('Received notification to reload settings, doing so now')
        self.__init__()

    def onScreensaverActivated(self):
        self.log('Received screensaver notification')
        if self.use_screensaver:
            self.log('Disconnecting possible devices')
            self.disconnect_possible_devices()

    def disconnect_possible_devices(self, force = False):
        self.log('In the disconnect_possible_devices function')
        if (self.check_duration_eligibility() == WatcherService.__DISCONNECTION_ELIGIBILITY_YES__) or force:
            oneDeviceDisconnected = False
            for device_name, device_mac in self.devices_to_disconnect.iteritems():
                self.log('Checking for device {} ({})'.format(device_name, device_mac))
                if self.device_connected(device_mac):
                    self.log('Device {} ({}) was connected, disconnecting it now'.format(device_name, device_mac))
                    if self.disconnect_device(device_mac):
                        self.log('Device {} ({}) disconnected successfully, notifying'.format(device_name, device_mac))
                        oneDeviceDisconnected = True
                        if force:
                            self.notify_function(self.addon.getLocalizedString(common.__STRING_PLUGIN_NAME_ID__), "{}: {} ({})".format(self.addon.getLocalizedString(common.__STRING_DEVICE_DISCONNECTED_DEMAND_ID__), device_name, device_mac), True)
                        else:
                            self.notify_disconnection_success(device_name, device_mac)
                    else:
                        self.log('Device {} ({}) could not be disconnected, notifying'.format(device_name, device_mac))
                        self.notify_disconnection_failure(device_name, device_mac)
                else:
                    self.log('Device {} ({}) was not connected, nothing to do'.format(device_name, device_mac))
            if not oneDeviceDisconnected:
                if force:
                    self.notify_function(self.addon.getLocalizedString(common.__STRING_PLUGIN_NAME_ID__), self.addon.getLocalizedString(common.__STRING_NO_DEVICE_DISCONNECTED_ID__), True)
            return oneDeviceDisconnected
        else:
            return False

    def refresh_settings(self):
        self.log('Reading settings')
        self.check_time = int(self.addon.getSetting(common.__SETTING_CHECK_TIME__)) * 60
        self.inactivity_threshold = int(self.addon.getSetting(common.__SETTING_INACTIVITY_TIME__)) * 60
        self.min_connection_time = int(self.addon.getSetting(common.__SETTING_MIN_CONNECTION_TIME__)) * 60
        self.use_screensaver = self.addon.getSetting(common.__SETTING_USE_SCREENSAVER__) == 'true'
        self.notify = self.addon.getSetting(common.__SETTING_NOTIFY__) == 'true'
        self.notify_sound = self.addon.getSetting(common.__SETTING_NOTIFY_SOUND__) == 'true'
        self.notify_sound_playing = self.addon.getSetting(common.__SETTING_NOTIFY_SOUND_PLAYING__) == 'true'
        try:
            self.devices_to_disconnect = json.loads(self.addon.getSettingString(common.__SETTING_DEVICES_TO_DISCONNECT_ID__))
        except ValueError:
            self.devices_to_disconnect = {}
        debugMode = self.addon.getSetting(common.__SETTING_LOG_MODE_BOOL__) == 'true'
        self.log('Loaded settings')
        self.log('check_time: {}'.format(self.check_time))
        self.log('inactivity_threshold: {}'.format(self.inactivity_threshold))
        self.log('min_connection_time: {}'.format(self.min_connection_time))
        self.log('use_screensaver: {}'.format(self.use_screensaver))
        self.log('notify: {}'.format(self.notify))
        self.log('notify_sound: {}'.format(self.notify_sound))
        self.log('notify_sound_playing: {}'.format(self.notify_sound_playing))
        self.log('devices_to_disconnect: {}'.format(self.devices_to_disconnect))
        self.log('debugMode: {}'.format(debugMode))
        if not debugMode:
            self.log('Addon going quiet due to debugMode')
        common.logMode = xbmc.LOGNOTICE if debugMode else xbmc.LOGDEBUG #now go quiet if needed

    def disconnect_device(self, device_mac):
        command_output = subprocess.check_output(common.__DISCONNECT_DEVICE__.format(device_mac), shell = True).decode('utf-8')
        return common.__DISCONNECT_DEVICE_SUCCESSFUL__ in command_output

    def device_connected(self, device_mac):
        command_output = subprocess.check_output(common.__GET_DEVICE_INFO__.format(device_mac), shell = True).decode('utf-8')
        return common.__IS_DEVICE_CONNECTED__ in command_output

    def sleep(self, duration = None):
        if duration is None:
            duration = self.check_time
        self.log('Waiting {} seconds for next check'.format(duration))
        if self.monitor.waitForAbort(duration):
            exit()

    def notify_function(self, title, message, sound):
        self.dialog.notification(title, message, sound = sound)

    def notify_disconnection_success(self, device_name, device_mac):
        if self.notify:
            self.log('Notifying for disconnection success')
            sound = False
            self.log('Determining if sound is to be played')
            if self.notify_sound:
                self.log('Sound was requested, checking further conditions')
                if self.notify_sound_playing:
                    self.log('Sound only requested if playing media')
                    sound = xbmc.Player().isPlaying()
                else:
                    self.log('Sound requested always')
                    sound = True
            self.log('Notification sound status: {}'.format(sound))
            self.notify_function(self.addon.getLocalizedString(common.__STRING_PLUGIN_NAME_ID__), "{}: {} ({})".format(self.addon.getLocalizedString(common.__STRING_DEVICE_DISCONNECTED_INACTIVITY_ID__), device_name, device_mac))

    def notify_disconnection_failure(self, device_name, device_mac):
        pass

    def has_devices_to_disconnect(self):
        return len(self.devices_to_disconnect) != 0

    def check_duration_eligibility(self):
        disconnectionLineFound = False
        self.logFile.seek(0, 2) #EOF
        logFileNewSize = self.logFile.tell()
        if (logFileNewSize > self.logFileLastSize):
            self.log('Contents of the log file have changed since last run, checking for device connection log line')
            self.logFile.seek(self.logFileLastSize, 0)  #go back to last check
            lines = self.logFile.readlines()
            for line in lines:
                if common.__LOG_DEVICE_CONNECTED__ in line:
                    disconnectionLineFound = True
                    self.log('Found device connection notification in logs, checking for eligibility')
                    deviceConnectedTime = dt.datetime(*[int(x) for x in re.findall(r'\d+', line)[0:7]])
                    timeSinceLastConnection = dt.datetime.now() - deviceConnectedTime
                    if timeSinceLastConnection.seconds >= self.min_connection_time:
                        self.log('Devices are eligible for disconnection because connection was made {} seconds ago, which is >= the minimum required connection duration of {} seconds'.format(timeSinceLastConnection.seconds, self.min_connection_time))
                        self.logFileLastSize = logFileNewSize
                        return WatcherService.__DISCONNECTION_ELIGIBILITY_YES__
        else:
            self.log('No change in log files => no new devices were connected since last check; ineligible')
            return WatcherService.__DISCONNECTION_ELIGIBILITY_NO_NEW_DEVICE__
        if not disconnectionLineFound:
            self.log('No new device was connected since last check (because line not found); ineligible')
            return WatcherService. __DISCONNECTION_ELIGIBILITY_NO_NEW_DEVICE__
        else:
            self.log('Devices are ineligible for disconnection because connection was made {} seconds ago, which is < the minimum required connection duration of {} seconds'.format(timeSinceLastConnection.seconds, self.min_connection_time))
            return WatcherService.__DISCONNECTION_ELIGIBILITY_TIME_NOT_ELAPSED__

    def check_for_inactivity(self):
        self.sleep()
        if self.has_devices_to_disconnect():
            self.log('Checking for inactivity')
            inactivity_seconds = xbmc.getGlobalIdleTime()
            self.log('Inactive time is {} seconds'.format(inactivity_seconds))
            if inactivity_seconds >= self.inactivity_threshold:
                self.log('This is >= the threshold of {} seconds, calling disconnect_possible_devices'.format(self.inactivity_threshold))
                self.disconnect_possible_devices()
            else:
                self.log('This is < the threshold of {} seconds, not doing anything'.format(self.inactivity_threshold))
        else:
            self.log('No eligible devices to disconnect, doing nothing')

    def log(self, msg):
        common.log("service.py: {}".format(msg))

if __name__ == '__main__':
    common.log('service.py: main, creating object')
    object = WatcherService()
    if object.has_devices_to_disconnect():
        while not xbmc.Monitor().abortRequested():
            object.check_for_inactivity()
    else:
        object.log('No eligible devices to disconnect, disabling service')
