from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import blueman.bluez as bluez
from blueman.Functions import *
from blueman.main.SignalTracker import SignalTracker
from blueman.main.Device import Device
from blueman.gui.Notification import Notification
from blueman.plugins.AppletPlugin import AppletPlugin

class DeviceNotifications(AppletPlugin):
    __description__ = "Displays a notification when Bluetooth device is connected or disconnected"
    __author__ = "Rijul-Ahuja"
    __icon__ = "dialog-information"

    def on_load(self, applet):
        self.signals = SignalTracker()
        self.signals.Handle("bluez", bluez.Device(), self.on_device_property_changed, "PropertyChanged", path_keyword="path")

    def on_unload(self):
        self.signals.DisconnectAll()

    def on_device_property_changed(self, key, is_connected, path):
        if key == 'Connected':
            dprint('Found change in device property: Connected')
            device = Device(path)
            alias = device.Alias
            dprint('Device alias is {}'.format(alias))
            game_icon = False
            props = device.get_properties()
            if 'Icon' in props:
                game_icon = props['Icon'] == 'input-gaming'
                dprint('Attempted to determine game_icon: {}'.format(game_icon))
            else:
                dprint('Could not determine game_icon')
            self.show_notification(alias, is_connected, game_icon)

    def show_notification(self, alias, is_connected, game_icon):
        title = alias
        msg = 'Device connected' if is_connected else 'Device disconnected'
        Notification(title, msg,
                     pixbuf=get_icon('input-gaming' if game_icon else 'audio-headphones', 48))
