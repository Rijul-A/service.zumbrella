#!/usr/bin/env bash

KODI_PID=$(pgrep -x "kodi.bin")
PEGASUS_PID=$(pgrep -x "pegasus-fe")

if [ -n "$KODI_PID" ]; then
    kill -9 "$KODI_PID"
elif [ -n "$PEGASUS_PID" ]; then
    kill -9 "$PEGASUS_PID"
else
    pegasus-fe --disable-menu-shutdown --disable-menu-suspend &
fi
