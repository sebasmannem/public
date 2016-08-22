#!/bin/sh
mount | awk '/LogVol/{print $3}' | while read FS; do touch "$FS/blaat" 2>&1 && rm -f "$FS/blaat"; done | grep -iqE 'read.only.file.system' && { echo "ROFS. Rebooting." ; reboot ; }
