import sys
import json
import subprocess
import six

import xbmcgui, xbmcaddon

from bluetooth_service import BluetoothService
from common import json_rpc
from logger import Logger

__SETTING_SHOW_GUI__ = 'show_gui'


class GuiLogger( Logger ):
    pass


def uniquify( mylist ):
    dups = {}
    for i, val in enumerate( mylist ):
        if val not in dups:
            # Store index of first occurrence and occurrence value
            dups[ val ] = [ i, 1 ]
        else:
            # Special case for first occurrence
            if dups[ val ][ 1 ] == 1:
                mylist[ dups[ val ][ 0 ] ] += str( dups[ val ][ 1 ] )
            # Increment occurrence value, index value doesn't matter anymore
            dups[ val ][ 1 ] += 1
            # Use stored occurrence value
            mylist[ i ] += str( dups[ val ][ 1 ] )
    return mylist


def get_devices_dict():
    logger = GuiLogger()
    # k, v = device_name, device_mac
    logger.log( 'Creating dictionary of devices' )
    try:
        command_output = subprocess.check_output(
            BluetoothService.__GET_DEVICES__,
            shell = True
        ).decode( 'utf-8' )[ :-1 ]
    except subprocess.CalledProcessError:
        return {}  # blank dictionary because bluez is not available
    devices_dict = dict(
        zip(
            uniquify(
                [ element[ 25 : ] for element in command_output.split( '\n' ) ]
            ),
            [
                element.split( ' ' )[ 1 ]
                for element in command_output.split( '\n' )
            ]
        )
    )
    logger.log(
        'Created devices dictionary {}'.format( json.dumps( devices_dict ) )
    )
    return devices_dict


def show_gui( thisAddon ):
    logger = GuiLogger()
    logger.log( 'Loaded thisAddon object' )
    dialog = xbmcgui.Dialog()
    logger.log( 'Created dialog object' )
    saved_devices_to_disconnect = json.loads(
        thisAddon.getSettingString(
            BluetoothService.__SETTING_DEVICES_TO_DISCONNECT__
        )
    )
    logger.log(
        'Loaded saved_devices_to_disconnect {}'
        .format( saved_devices_to_disconnect )
    )
    possible_devices_to_disconnect = get_devices_dict()
    logger.log(
        'Loaded possible_devices_to_disconnect {}'
        .format( possible_devices_to_disconnect )
    )
    # remove items which were saved but are now no longer paired
    saved_devices_to_disconnect_final = {}
    for device_name, device_mac in six.iteritems( saved_devices_to_disconnect ):
        if device_mac not in six.itervalues( possible_devices_to_disconnect ):
            logger.log(
                'Found unpaired device {}, removing it from saved devices'
                .format( device_mac )
            )
        else:
            saved_devices_to_disconnect_final[ device_name ] = device_mac
    saved_devices_to_disconnect = saved_devices_to_disconnect_final
    # create preselect array
    logger.log( 'Creating preselect array' )
    preselect = []
    i = -1
    for device_name, device_mac in six.iteritems(possible_devices_to_disconnect):
        i = i + 1
        if device_mac in six.itervalues( saved_devices_to_disconnect ):
            logger.log( 'Found pre-selected device {}'.format( device_mac ) )
            preselect.append( i )
    # show dialog with multiselect and preselect
    logger.log( 'Displaying multiselect dialog' )
    returned_devices_to_disconnect = dialog.multiselect(
        thisAddon.getLocalizedString(
            BluetoothService.__STRING_DEVICES_TO_DISCONNECT_ID__
        ),
        [
            xbmcgui.ListItem( "{} ({})".format( device_name,
                                                device_mac ) ) for device_name,
            device_mac in six.iteritems( possible_devices_to_disconnect )
        ],
        preselect = preselect
    )
    if returned_devices_to_disconnect is None:
        logger.log(
            'Multiselect dialog was canceled, saving old config {}'
            .format( saved_devices_to_disconnect )
        )
        thisAddon.setSettingString(
            BluetoothService.__SETTING_DEVICES_TO_DISCONNECT__,
            json.dumps( saved_devices_to_disconnect )
        )
    else:
        to_save_devices = {
            list( six.iterkeys( possible_devices_to_disconnect ) )[ element ]: list(
                six.itervalues( possible_devices_to_disconnect )
            )[ element ]
            for element in returned_devices_to_disconnect
        }
        logger.log( 'Saving new config {}'.format( to_save_devices ) )
        thisAddon.setSettingString(
            BluetoothService.__SETTING_DEVICES_TO_DISCONNECT__,
            json.dumps( to_save_devices )
        )


def disconnect_now( thisAddon ):
    object = BluetoothService( thisAddon )
    object.refresh_settings()
    object.disconnect_possible_devices( True )


def main():
    logger = GuiLogger()
    thisAddon = xbmcaddon.Addon()
    logger.log( 'GUI.py - main function' )
    try:
        arg = sys.argv[ 1 ].lower()
    except IndexError:
        arg = None
    # log(str(arg))
    if arg is not None:
        if BluetoothService.__SETTING_DISCONNECT_NOW__ in arg:
            disconnect_now( thisAddon )
            if 'back' in arg:
                json_rpc( method = "Input.Back" )
        elif arg == __SETTING_SHOW_GUI__:
            show_gui( thisAddon )
        else:
            logger.log( 'arg: {}'.format( arg ) )
            disconnect_now( thisAddon )
    else:
        disconnect_now( thisAddon )


if ( __name__ == '__main__' ):
    main()
