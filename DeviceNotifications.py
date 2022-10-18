from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import blueman.bluez as bluez
from blueman.Functions import *
# from blueman.main.SignalTracker import SignalTracker
# from blueman.main.Device import Device
from blueman.gui.Notification import Notification
from blueman.plugins.AppletPlugin import AppletPlugin
import logging


class DeviceNotifications( AppletPlugin ):
    __description__ = "Displays a notification when Bluetooth device is connected or disconnected"
    __author__ = "Rijul-Ahuja"
    __icon__ = "dialog-information"

    def on_load( self ):
        pass
        # self.signals = SignalTracker()
        # self.signals.Handle("bluez", bluez.Device(), self.on_device_property_changed, "PropertyChanged", path_keyword="path")

    def on_unload( self ):
        pass
        # self.signals.DisconnectAll()

    def on_device_property_changed( self, path, key, value ):
        if key == 'Connected':
            logging.info( 'Found change in device property: Connected' )
            device = bluez.Device( path )
            alias = device[ 'Alias' ]
            logging.info( 'Device alias is {}'.format( alias ) )
            game_icon = False
            props = device.get_properties()
            if 'Icon' in props:
                game_icon = props[ 'Icon' ] == 'input-gaming'
                logging.info(
                    'Attempted to determine game_icon: {}'.format( game_icon )
                )
            else:
                logging.info( 'No icon in props' )
            self.show_notification( alias, value, game_icon )

    def show_notification( self, alias, is_connected, game_icon ):
        title = alias
        msg = 'Device connected' if is_connected else 'Device disconnected'
        icon_name = 'input-gaming' if game_icon else 'audio-headphones'
        logging.info( '{}, {}, {}'.format( title, msg, icon_name ) )
        Notification( title, msg, icon_name = 'input-gaming' ).show()
