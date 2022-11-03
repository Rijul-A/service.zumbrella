import subprocess
import codecs
import json
import datetime as dt
import re
import six

from kodi_six import xbmc, xbmcgui

from common import ( read_bool_setting, read_int_setting )
from logger import Logger


class BluetoothService( Logger ):
    __DISCONNECTION_ELIGIBILITY_THRESHOLD_NOT_ELAPSED__ = -2
    __DISCONNECTION_ELIGIBILITY_NO_NEW_DEVICE__ = -1
    __DISCONNECTION_ELIGIBILITY_YES__ = 1

    __SETTING_INACTIVITY_THRESHOLD__ = 'inactivity_threshold'
    __SETTING_USE_NO_MEDIA_THRESHOLD__ = 'use_no_media_threshold'
    __SETTING_INACTIVITY_THRESHOLD_NO_MEDIA__ = 'inactivity_threshold_no_media'
    __SETTING_USE_PAUSED_MEDIA_THRESHOLD__ = 'use_paused_media_threshold'
    __SETTING_INACTIVITY_THRESHOLD_PAUSED_MEDIA__ = 'inactivity_threshold_paused_media'
    __SETTING_MIN_CONNECTION_THRESHOLD__ = 'min_connection_threshold'
    __SETTING_NOTIFY__ = "notify"
    __SETTING_NOTIFY_SOUND__ = "notify_sound"
    __SETTING_NOTIFY_SOUND_PLAYING__ = "notify_sound_playing"
    __SETTING_USE_SCREENSAVER__ = "use_screensaver"
    __SETTING_DEVICES_TO_DISCONNECT__ = 'devices_to_disconnect'
    __SETTING_DISCONNECT_NOW__ = "disconnect_now"

    __GET_DEVICES__ = 'bluetoothctl devices'
    __GET_DEVICE_INFO__ = 'bluetoothctl info {}'
    __IS_DEVICE_CONNECTED__ = 'Connected: yes'
    __DISCONNECT_DEVICE__ = 'bluetoothctl disconnect {}'
    __DISCONNECT_DEVICE_SUCCESSFUL__ = 'Successful'

    __STRING_PLUGIN_NAME_ID__ = 32000
    __STRING_DEVICE_DISCONNECTED_INACTIVITY_ID__ = 32005
    __STRING_DEVICE_DISCONNECTED_DEMAND_ID__ = 32013
    __STRING_DEVICES_TO_DISCONNECT_ID__ = 32003
    __STRING_NO_DEVICE_DISCONNECTED_ID__ = 32014

    __LOG_DEVICE_CONNECTED__ = 'Register - new joystick device registered on addon->peripheral.joystick'

    def __init__( self, addon ):
        self.log( 'Creating object' )
        self.dialog = xbmcgui.Dialog()
        self.addon = addon
        self.logFile = codecs.open(
            xbmc.translatePath( r'special://logpath/kodi.log' ),
            'r',
            encoding = 'utf-8',
            errors = 'ignore'
        )
        # for first run, read from top
        self.logFileLastSize = 0

    def onScreensaverActivated( self ):
        if self.use_screensaver:
            self.log( 'Screensaver detected, turning off devices if eligible' )
            self.disconnect_possible_devices()
        else:
            self.log(
                'Screensaver detected but not turning off eligible devices because setting is off'
            )

    def refresh_settings( self ):
        self.log( 'Reading settings' )
        self.inactivity_threshold = read_int_setting(
            self.addon,
            BluetoothService.__SETTING_INACTIVITY_THRESHOLD__
        )
        self.use_no_media_threshold = read_bool_setting(
            self.addon,
            BluetoothService.__SETTING_USE_NO_MEDIA_THRESHOLD__
        )
        self.inactivity_threshold_no_media = read_int_setting(
            self.addon,
            BluetoothService.__SETTING_INACTIVITY_THRESHOLD_NO_MEDIA__
        )
        self.use_paused_media_threshold = read_bool_setting(
            self.addon,
            BluetoothService.__SETTING_USE_PAUSED_MEDIA_THRESHOLD__
        )
        self.inactivity_threshold_paused_media = read_int_setting(
            self.addon,
            BluetoothService.__SETTING_INACTIVITY_THRESHOLD_PAUSED_MEDIA__
        )
        self.min_connection_threshold = read_int_setting(
            self.addon,
            BluetoothService.__SETTING_MIN_CONNECTION_THRESHOLD__
        )
        self.use_screensaver = read_bool_setting(
            self.addon,
            BluetoothService.__SETTING_USE_SCREENSAVER__
        )
        self.notify = read_bool_setting(
            self.addon,
            BluetoothService.__SETTING_NOTIFY__
        )
        self.notify_sound = read_bool_setting(
            self.addon,
            BluetoothService.__SETTING_NOTIFY_SOUND__
        )
        self.notify_sound_playing = read_bool_setting(
            self.addon,
            BluetoothService.__SETTING_NOTIFY_SOUND_PLAYING__
        )
        self.devices_to_disconnect = json.loads(
            self.addon.getSettingString(
                BluetoothService.__SETTING_DEVICES_TO_DISCONNECT__
            )
        )
        self.log( 'Loaded settings' )
        self.log(
            'inactivity_threshold: {}'.format( self.inactivity_threshold )
        )
        self.log(
            'use_no_media_threshold: {}'.format( self.use_no_media_threshold )
        )
        self.log(
            'inactivity_threshold_no_media: {}'.format(
                self.inactivity_threshold_no_media
            )
        )
        self.log(
            'use_paused_media_threshold: {}'.format(
                self.use_paused_media_threshold
            )
        )
        self.log(
            'inactivity_threshold_paused_media: {}'.format(
                self.inactivity_threshold_paused_media
            )
        )
        self.log(
            'min_connection_threshold: {}'.format(
                self.min_connection_threshold
            )
        )
        self.log( 'use_screensaver: {}'.format( self.use_screensaver ) )
        self.log( 'notify: {}'.format( self.notify ) )
        self.log( 'notify_sound: {}'.format( self.notify_sound ) )
        self.log(
            'notify_sound_playing: {}'.format( self.notify_sound_playing )
        )
        self.log(
            'devices_to_disconnect: {}'.format( self.devices_to_disconnect )
        )

    def disconnect_device( self, device_mac ):
        try:
            command_output = subprocess.check_output(
                BluetoothService.__DISCONNECT_DEVICE__.format( device_mac ),
                shell = True
            ).decode( 'utf-8' )
            return BluetoothService.__DISCONNECT_DEVICE_SUCCESSFUL__ in command_output
        except subprocess.CalledProcessError:
            return True  # assume success

    def device_connected( self, device_mac ):
        try:
            command_output = subprocess.check_output(
                BluetoothService.__GET_DEVICE_INFO__.format( device_mac ),
                shell = True
            ).decode( 'utf-8' )
            return BluetoothService.__IS_DEVICE_CONNECTED__ in command_output
        except subprocess.CalledProcessError:
            return False  # avoid further calls until this is resolved

    def notify_function( self, title, message, sound ):
        self.dialog.notification( title, message, sound = sound )

    def notify_disconnection_success( self, device_name, device_mac ):
        if self.notify:
            self.log( 'Notifying for disconnection success' )
            sound = False
            self.log( 'Determining if sound is to be played' )
            if self.notify_sound:
                self.log( 'Sound was requested, checking further conditions' )
                if self.notify_sound_playing:
                    self.log( 'Sound only requested if playing media' )
                    sound = xbmc.Player().isPlaying()  # if media is active
                else:
                    self.log( 'Sound requested always' )
                    sound = True
            self.log( 'Notification sound status: {}'.format( sound ) )
            self.notify_function(
                self.addon.getLocalizedString(
                    BluetoothService.__STRING_PLUGIN_NAME_ID__
                ),
                "{}: {} ({})".format(
                    self.addon.getLocalizedString(
                        BluetoothService
                        .__STRING_DEVICE_DISCONNECTED_INACTIVITY_ID__
                    ),
                    device_name,
                    device_mac
                ),
                sound
            )

    def notify_disconnection_failure( self, *_ ):
        # have not seen this happening
        pass

    def check_duration_eligibility( self ):
        disconnectionLineFound = False
        self.logFile.seek( 0, 2 )  # EOF
        logFileNewSize = self.logFile.tell()
        if ( logFileNewSize > self.logFileLastSize ):
            self.log(
                'Contents of the log file have changed since last run, '
                'checking for device connection log line'
            )
            self.logFile.seek(
                self.logFileLastSize,
                0
            )  # go back to last check
            lines = self.logFile.readlines()
            for line in lines:
                if BluetoothService.__LOG_DEVICE_CONNECTED__ in line:
                    disconnectionLineFound = True
                    self.log(
                        'Found device connection notification in logs, '
                        'checking for eligibility'
                    )
                    deviceConnectedTime = dt.datetime(
                        *[
                            int( x ) for x in re.findall( r'\d+',
                                                          line )[ 0 : 7 ]
                        ]
                    )
                    timeSinceLastConnection = dt.datetime.now(
                    ) - deviceConnectedTime
                    if timeSinceLastConnection.seconds >= self.min_connection_threshold:
                        self.log(
                            'Devices are eligible for disconnection because '
                            'connection was made {} seconds ago, which is >= '
                            'the minimum required connection duration of {} seconds'
                            .format(
                                timeSinceLastConnection.seconds,
                                self.min_connection_threshold
                            )
                        )
                        self.logFileLastSize = logFileNewSize
                        return BluetoothService.__DISCONNECTION_ELIGIBILITY_YES__
        else:
            self.log(
                'No change in log files => no new devices were '
                'connected since last check; ineligible'
            )
            return BluetoothService.__DISCONNECTION_ELIGIBILITY_NO_NEW_DEVICE__
        if not disconnectionLineFound:
            self.log(
                'No new device was connected since '
                'last check (because line not found); ineligible'
            )
            return BluetoothService.__DISCONNECTION_ELIGIBILITY_NO_NEW_DEVICE__
        else:
            self.log(
                'Devices are ineligible for disconnection because '
                'connection was made {} seconds ago, which is < the '
                'minimum required connection duration of {} seconds'.format(
                    timeSinceLastConnection.seconds,
                    self.min_connection_threshold
                )
            )
            return BluetoothService.__DISCONNECTION_ELIGIBILITY_THRESHOLD_NOT_ELAPSED__

    def has_devices_to_disconnect( self ):
        return len( self.devices_to_disconnect ) != 0

    def disconnect_possible_devices( self, force = False ):
        self.log( 'In the disconnect_possible_devices function' )
        if force or (
            self.check_duration_eligibility()
            == BluetoothService.__DISCONNECTION_ELIGIBILITY_YES__
        ):
            oneDeviceDisconnected = False
            for device_name, device_mac in six.iteritems(self.devices_to_disconnect):
                self.log(
                    'Checking for device {} ({})'.format(
                        device_name,
                        device_mac
                    )
                )
                if self.device_connected( device_mac ):
                    self.log(
                        'Device {} ({}) was connected, disconnecting it now'
                        .format( device_name,
                                 device_mac )
                    )
                    if self.disconnect_device( device_mac ):
                        self.log(
                            'Device {} ({}) disconnected successfully, notifying'
                            .format( device_name,
                                     device_mac )
                        )
                        oneDeviceDisconnected = True
                        if force:
                            # # done via the OS
                            # self.notify_function(
                            #     self.addon.getLocalizedString(
                            #         BluetoothService.__STRING_PLUGIN_NAME_ID__
                            #     ),
                            #     "{}: {} ({})".format(
                            #         self.addon.getLocalizedString(
                            #             BluetoothService.
                            #             __STRING_DEVICE_DISCONNECTED_DEMAND_ID__
                            #         ),
                            #         device_name,
                            #         device_mac
                            #     ),
                            #     True
                            # )
                            pass
                        else:
                            self.notify_disconnection_success(
                                device_name,
                                device_mac
                            )
                    else:
                        self.log(
                            'Device {} ({}) could not be disconnected, notifying'
                            .format( device_name,
                                     device_mac )
                        )
                        self.notify_disconnection_failure(
                            device_name,
                            device_mac
                        )
                else:
                    self.log(
                        'Device {} ({}) was not connected, nothing to do'
                        .format( device_name,
                                 device_mac )
                    )
            if not oneDeviceDisconnected:
                if force:
                    self.notify_function(
                        self.addon.getLocalizedString(
                            BluetoothService.__STRING_PLUGIN_NAME_ID__
                        ),
                        self.addon.getLocalizedString(
                            BluetoothService
                            .__STRING_NO_DEVICE_DISCONNECTED_ID__
                        ),
                        True
                    )
            return oneDeviceDisconnected
        else:
            return False

    def do_check( self, inactivity_seconds ):
        if self.has_devices_to_disconnect():
            self.log( 'Calculating inactivity threshold' )
            if xbmc.getCondVisibility( 'Player.HasMedia' ):
                self.log( 'Player has media' )
                if xbmc.getCondVisibility( 'Player.Playing' ):
                    self.log(
                        'Player is playing, using default threshold of {} seconds'
                        .format( self.inactivity_threshold )
                    )
                    threshold = self.inactivity_threshold
                else:
                    self.log( 'Player is paused' )
                    if self.use_paused_media_threshold:
                        self.log(
                            'use_paused_media_threshold is True, using '
                            'paused-media threshold of {} seconds'.format(
                                self.inactivity_threshold_paused_media
                            )
                        )
                        threshold = self.inactivity_threshold_paused_media
                    else:
                        self.log(
                            'use_paused_media_threshold is False, using '
                            'default threshold of {} seconds'.format(
                                self.inactivity_threshold
                            )
                        )
                        threshold = self.inactivity_threshold
            else:
                self.log( 'Player has no media' )
                if self.use_no_media_threshold:
                    self.log(
                        'use_no_media_threshold is True, using '
                        'no-media threshold of {} seconds'.format(
                            self.inactivity_threshold_no_media
                        )
                    )
                    threshold = self.inactivity_threshold_no_media
                else:
                    self.log(
                        'use_no_media_threshold is False, using '
                        'default threshold of {} seconds'.format(
                            self.inactivity_threshold
                        )
                    )
                    threshold = self.inactivity_threshold
            if inactivity_seconds >= threshold:
                self.log(
                    'Inactive time of {} seconds is >= the threshold '
                    'of {} seconds, calling disconnect_possible_devices'.format(
                        inactivity_seconds,
                        threshold
                    )
                )
                self.disconnect_possible_devices()
            else:
                self.log(
                    'Inactive_time of {} seconds is < the threshold of '
                    '{} seconds, not doing anything'.format(
                        inactivity_seconds,
                        threshold
                    )
                )
        else:
            self.log( 'No eligible devices to disconnect, doing nothing' )
