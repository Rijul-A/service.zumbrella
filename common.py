import xbmc
import subprocess
import json

__PLUGIN_ID__ = 'service.bluetooth.watcher'
__PLUGIN_VERSION__ = 'v0.0.1'

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

__SETTING_DEVICES_TO_DISCONNECT_ID__ = 'devices_to_disconnect'
__SETTING_CHECK_TIME__ = 'check_time'
__SETTING_INACTIVITY_TIME__ = 'inactivity_time'
__SETTING_MIN_CONNECTION_TIME__ = 'min_connection_time'
__SETTING_NOTIFY__ = "notify"
__SETTING_NOTIFY_SOUND__ = "notify_sound"
__SETTING_NOTIFY_SOUND_PLAYING__ = "notify_sound_playing"
__SETTING_USE_SCREENSAVER__ = "use_screensaver"
__SETTING_LOG_MODE_BOOL__ = "debug"
__SETTING_DISCONNECT_NOW__ = "disconnect_now"

__LOG_DEVICE_CONNECTED__ = 'Register - new joystick device registered on addon->peripheral.joystick'

logMode = xbmc.LOGNOTICE

def uniquify(mylist):
    dups = {}
    for i, val in enumerate(mylist):
        if val not in dups:
            # Store index of first occurrence and occurrence value
            dups[val] = [i, 1]
        else:
            # Special case for first occurrence
            if dups[val][1] == 1:
                mylist[dups[val][0]] += str(dups[val][1])
            # Increment occurrence value, index value doesn't matter anymore
            dups[val][1] += 1
            # Use stored occurrence value
            mylist[i] += str(dups[val][1])
    return mylist

def get_devices_dict():
    #k, v = device_name, device_mac
    log('Creating dictionary of devies')
    command_output = subprocess.check_output(__GET_DEVICES__, shell = True).decode('utf-8')[:-1]
    devices_dict = dict(zip(uniquify([element[25:] for element in command_output.split('\n')]), [element.split(' ')[1] for element in command_output.split('\n')]))
    log('Created devices dictionary {}'.format(json.dumps(devices_dict)))
    return devices_dict

def log(msg, mode = None):
    global logMode
    mode = None or logMode
    xbmc.log("[{}_{}]: {}".format(__PLUGIN_ID__, __PLUGIN_VERSION__, str(msg)), mode)
