import xbmc
import xbmcgui
import xbmcaddon

import sys
import json

import common
import service

def show_gui():
    thisAddon = xbmcaddon.Addon()
    common.log('Loaded thisAddon object')
    dialog = xbmcgui.Dialog()
    common.log('Created dialog object')
    try:
        saved_devices_to_disconnect = json.loads(thisAddon.getSettingString(common.__SETTING_DEVICES_TO_DISCONNECT_ID__))
    except ValueError:
        saved_devices_to_disconnect = {}
    common.log('Loaded saved_devices_to_disconnect {}'.format(saved_devices_to_disconnect))
    possible_devices_to_disconnect = common.get_devices_dict()
    common.log('Loaded possible_devices_to_disconnect {}'.format(possible_devices_to_disconnect))
    #remove items which were saved but are now no longer paired
    for device_name, device_mac in saved_devices_to_disconnect.iteritems():
        if device_mac not in possible_devices_to_disconnect.values():
            common.log('Found unpaired device {}, removing it from saved devices'.format(device_mac))
            saved_devices_to_disconnect.pop(device_name)
    #create preselect array
    common.log('Creating preselect array')
    preselect = []
    i = -1
    for device_name, device_mac in possible_devices_to_disconnect.iteritems():
        i = i + 1
        if device_mac in saved_devices_to_disconnect.values():
            common.log('Found pre-selected device {}'.format(device_mac))
            preselect.append(i)
    #show dialog with multiselect and preselect
    common.log('Displaying multiselect dialog')
    returned_devices_to_disconnect = dialog.multiselect(thisAddon.getLocalizedString(common.__STRING_DEVICES_TO_DISCONNECT_ID__),
        [xbmcgui.ListItem("{} ({})".format(device_name, device_mac)) for device_name, device_mac in possible_devices_to_disconnect.iteritems()], preselect = preselect)
    if returned_devices_to_disconnect is None:
        common.log('Multiselect dialog was canceled, saving old config {}'.format(saved_devices_to_disconnect))
        thisAddon.setSettingString(common.__SETTING_DEVICES_TO_DISCONNECT_ID__, json.dumps(saved_devices_to_disconnect))
    else:
        to_save_devices = {list(possible_devices_to_disconnect.keys())[element]: list(possible_devices_to_disconnect.values())[element] for element in returned_devices_to_disconnect}
        common.log('Saving new config {}'.format(to_save_devices))
        thisAddon.setSettingString(common.__SETTING_DEVICES_TO_DISCONNECT_ID__, json.dumps(to_save_devices))

def disconnect_now():
    object = service.WatcherService()
    object.disconnect_possible_devices(True)
    del object  #to prevent two services at the same time

if (__name__ == '__main__'):
    common.log('GUI.py - main function')
    try:
        arg = sys.argv[1].lower()
    except IndexError:
        arg = None
    #common.log(str(arg))
    if arg is not None:
        if common.__SETTING_DISCONNECT_NOW__ in arg:
            disconnect_now()
            if 'back' in arg:
                back_json = {"jsonrpc": "2.0", "method": "Input.Back", "id": 1}
                xbmc.executeJSONRPC(json.dumps(back_json))
        elif arg == common.__SETTING_SHOW_GUI__:
            show_gui()
        else:
            common.log('arg: {}'.format(arg))
            disconnect_now()
    else:
        disconnect_now()
