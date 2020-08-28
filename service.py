import xbmc
import xbmcgui
import xbmcaddon
import subprocess
import common
import json

class Monitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.reloadAction = kwargs['reloadAction']
        self.screensaverAction = kwargs['screensaverAction']

    def onSettingsChanged(self):
        self.reloadAction()

    def onScreensaverActivated(self):
        self.screensaverAction()

class BluetoothService:
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.dialog = xbmcgui.Dialog()
        self.monitor = Monitor(reloadAction = self.onSettingsChanged, screensaverAction = self.onScreensaverActivated)
        self.last_turned_off_time = None
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

    def disconnect_possible_devices(self, inactivity_seconds = None):
        self.log('In the disconnect_possible_devices function')
        if inactivity_seconds is None:
            self.log('Request received from screensaver, skipping time check#2')
        elif self.last_turned_off_time is not None and (inactivity_seconds - self.last_turned_off_time <= self.check_time):
            self.log('Inactivity_time ({0}) less last_turned_off_time ({1}) is less than the check_time ({2}), doing nothing'.format(inactivity_seconds, self.last_turned_off_time, self.check_time))
            self.last_turned_off_time = self.check_time #only apply this extra layer of checks once
            return
        else:
            self.log('Time check#2 passed')
        oneDeviceDisconnected = False
        for device_name, device_mac in self.devices_to_disconnect.iteritems():
            self.log('Checking for device {0} ({1})'.format(device_name, device_mac))
            if self.device_connected(device_mac):
                self.log('Device {0} ({1}) was connected, disconnecting it now'.format(device_name, device_mac))
                if self.disconnect_device(device_mac):
                    self.log('Device {0} ({1}) disconnected successfully, notifying'.format(device_name, device_mac))
                    oneDeviceDisconnected = True
                    self.notify_disconnection_success(device_name, device_mac)
                else:
                    self.log('Device {0} ({1}) could not be disconnected, notifying'.format(device_name, device_mac))
                    self.notify_disconnection_failure(device_name, device_mac)
            else:
                self.log('Device {0} ({1}) was not connected, nothing to do'.format(device_name, device_mac))
        if oneDeviceDisconnected:   #only set the time if a device was actually disconnected
            self.last_turned_off_time = xbmc.getGlobalIdleTime()
            self.log('Set last_turned_off_time: {}'.format(str(self.last_turned_off_time)))

    def refresh_settings(self):
        self.log('Reading settings')
        self.check_time = int(self.addon.getSetting(common.__SETTING_CHECK_TIME__)) * 60
        self.inactivity_threshold = int(self.addon.getSetting(common.__SETTING_INACTIVITY_TIME__)) * 60
        if self.inactivity_threshold == 0:
            self.inactivity_threshold = 60
        self.use_screensaver = self.addon.getSetting(common.__SETTING_USE_SCREENSAVER__) == 'true'
        self.notify = self.addon.getSetting(common.__SETTING_NOTIFY__) == 'true'
        try:
            self.devices_to_disconnect = json.loads(self.addon.getSettingString(common.__SETTING_DEVICES_TO_DISCONNECT_ID__))
        except ValueError:
            self.devices_to_disconnect = {}
        debugMode = self.addon.getSetting(common.__SETTING_LOG_MODE_BOOL__) == 'true'
        self.log('Loaded settings')
        self.log('check_time: {0}'.format(str(self.check_time)))
        self.log('inactivity_threshold: {0}'.format(str(self.inactivity_threshold)))
        self.log('use_screensaver: {0}'.format(str(self.use_screensaver)))
        self.log('notify: {0}'.format(str(self.notify)))
        self.log('devices_to_disconnect: {0}'.format(json.dumps(self.devices_to_disconnect)))
        self.log('debugMode: {}'.format(str(debugMode)))
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
        self.log('Waiting {0} seconds for next check'.format(str(duration)))
        if self.monitor.waitForAbort(duration):
            exit()

    def notify_disconnection_success(self, device_name, device_mac):
        if self.notify:
            self.dialog.notification(self.addon.getLocalizedString(common.__STRING_PLUGIN_NAME_ID__), self.addon.getLocalizedString(common.__STRING_DEVICE_DISCONNECTED_ID__) + " {0} ({1})".format(device_name, device_mac), sound = True)

    def notify_disconnection_failure(self, device_name, device_mac):
        pass

    def has_devices_to_disconnect(self):
        return len(self.devices_to_disconnect) != 0

    def check_for_inactivity(self):
        self.sleep()
        if self.has_devices_to_disconnect():
            self.log('Checking for inactivity')
            inactivity_seconds = xbmc.getGlobalIdleTime()
            self.log('Inactive time is {0} seconds'.format(str(inactivity_seconds)))
            if inactivity_seconds >= self.inactivity_threshold:
                self.log('This is more than the threshold of {0} seconds, checking for devices'.format(self.inactivity_threshold))
                self.disconnect_possible_devices(inactivity_seconds)
            else:
                self.log('This is less than the threshold of {0} seconds, not doing anything'.format(self.inactivity_threshold))
        else:
            self.log('No eligible devices to disconnect, doing nothing')

    def log(self, msg):
        common.log("service.py: {0}".format(msg))

if __name__ == '__main__':
    common.log('service.py: main, creating object')
    object = BluetoothService()
    if object.has_devices_to_disconnect():
        while not object.monitor.abortRequested():
            object.check_for_inactivity()
    else:
        object.log('No eligible devices to disconnect, disabling service')
